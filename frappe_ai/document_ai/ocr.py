# Copyright (c) 2026, Sambhav Saxena and contributors
# For license information, please see license.txt


import json
import os
from pathlib import Path
from io import BytesIO
from dataclasses import dataclass

import frappe
from pypdf import PdfReader
from google.cloud import documentai_v1 as documentai
from google.longrunning.operations_pb2 import GetOperationRequest

from frappe_ai.document_ai.config import VALID_MIME_TYPES, get_document_ai_client, get_settings
from frappe_ai.document_ai.storage import upload_to_gc_bucket
from frappe_ai.document_ai.utils import mark_ocr_failed, resolve_file_path


@dataclass
class OperationStatus:
	done: bool
	success: bool
	error: dict | None = None


def process_async_ocr_job(ocr_process_name: str):
	ocr_process = frappe.get_doc("OCR Process", ocr_process_name)
	try:
		ocr_process.started_at = frappe.utils.now()	# completes inside cron
		file_path = resolve_file_path(ocr_process.file_path)
		if not os.path.exists(file_path):
			frappe.throw("Invalid file path")

		# namespace GCS paths by the OCR Process name, since the GCP operation name
		# is only known after the request is submitted
		filename = Path(file_path).name
		settings = get_settings()
		project_id = settings.get("project_id")
		location = settings.get("location")
		processor_id = settings.get("processor_id")
		input_prefix = settings.get("input_prefix")
		output_prefix = settings.get("output_prefix")
		bucket = settings.get("cloud_storage_bucket")

		gcs_input_path = f"{input_prefix}/{ocr_process.name}/{filename}"
		gcs_output_uri = f"gs://{bucket}/{output_prefix}/{ocr_process.name}/"
		gcs_input_uri, mime_type = upload_to_gc_bucket(file_path, gcs_input_path, bucket)

		if mime_type not in VALID_MIME_TYPES.values():
			frappe.throw(f"Unsupported file type: {mime_type}")

		client = get_document_ai_client()
		processor_name = client.processor_path(project_id, location, processor_id)

		request = documentai.BatchProcessRequest(
			name=processor_name,
			input_documents=documentai.BatchDocumentsInputConfig(
				gcs_documents=documentai.GcsDocuments(
					documents=[documentai.GcsDocument(gcs_uri=gcs_input_uri, mime_type=mime_type)]
				)
			),
			document_output_config=documentai.DocumentOutputConfig(
				gcs_output_config=documentai.DocumentOutputConfig.GcsOutputConfig(gcs_uri=gcs_output_uri)
			),
		)

		operation = client.batch_process_documents(request=request)

		ocr_process.process_name = operation.operation.name
		ocr_process.gcs_input_uri = gcs_input_uri
		ocr_process.gcs_output_uri = gcs_output_uri
		ocr_process.status = "Processing"
		ocr_process.save(ignore_permissions=True)
		ocr_process.reload()
	except Exception:
		mark_ocr_failed(ocr_process)


def check_operation_progress(process_name):
	client = get_document_ai_client()
	operation = client.get_operation(GetOperationRequest(name=process_name))
	if not operation.done:
		return OperationStatus(done=False, success=False)
	if operation.error and operation.error.code:
		return OperationStatus(done=True, success=False, error={ "code": operation.error.code, "message": operation.error.message })
	return OperationStatus(done=True, success=True)


def process_sync_ocr_job(ocr_process):
	try:
		ocr_process.started_at = frappe.utils.now()
		file_path = resolve_file_path(ocr_process.file_path)
		if not os.path.exists(file_path):
			frappe.throw("Invalid file path")

		with open(file_path, 'rb') as f:
			file_content = f.read()

		ext = os.path.splitext(file_path)[1].lower()
		mime_type = VALID_MIME_TYPES.get(ext)
		if not mime_type:
			frappe.throw(f"Unsupported file type: {ext}")

		if mime_type == "application/pdf":
			reader = PdfReader(BytesIO(file_content))
			if len(reader.pages) > 3:
				frappe.throw("PDFs in Synchronous mode cannot have more than 3 pages, please choose Asynchronous mode for large files.")

		client = get_document_ai_client()
		settings = get_settings()
		project_id = settings.get("project_id")
		location = settings.get("location")
		processor_id = settings.get("processor_id")
		processor_name = client.processor_path(project_id, location, processor_id)
		raw_document = documentai.RawDocument(content=file_content, mime_type=mime_type)
		request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)
		result = client.process_document(request=request)
		doc_json = documentai.Document.to_dict(result.document)
		ocr_process.raw_response = json.dumps(doc_json)
		ocr_process.status = "Completed"
		ocr_process.completed_at = frappe.utils.now()
		ocr_process.save(ignore_permissions=True)
		ocr_process.reload()

	except Exception:
		mark_ocr_failed(ocr_process)
		raise
