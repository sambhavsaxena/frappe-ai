# Copyright (c) 2026, Sambhav Saxena and contributors
# For license information, please see license.txt


import json

import frappe

from frappe_ai.document_ai.config import get_settings, get_google_storage_client
from frappe_ai.document_ai.ocr import check_operation_progress
from frappe_ai.document_ai.storage import extract_process_output


def check_ocr_process_status():
	ocr_processes = frappe.get_all("OCR Process", filters={"status": ["in", ["Queued", "Processing"]]}, fields=["name", "status", "process_name"])
	for ocr_process in ocr_processes:
		try:
			status = check_operation_progress(ocr_process.process_name)
			if not status.done:
				continue
			doc = frappe.get_doc("OCR Process", ocr_process.name)
			if not status.success:
				doc.status = "Failed"
				doc.error_log = json.dumps(status.error)
				doc.save(ignore_permissions=True)
				continue
			extracted_data = extract_process_output(doc)
			doc.raw_response = json.dumps(extracted_data)
			doc.status = "Completed"
			doc.completed_at = frappe.utils.now()
			doc.save(ignore_permissions=True)
		except Exception:
			frappe.log_error("OCR Status Check Failed", frappe.get_traceback())


def delete_processed_ocr_data_from_gcs():
	processes = frappe.get_all("OCR Process", filters={"status": ["in", ["Failed", "Completed"]]}, fields=["name", "process_name", "gcs_input_uri", "gcs_output_uri"])
	settings = get_settings()
	bucket_name = settings.get("cloud_storage_bucket")
	client = get_google_storage_client()
	bucket = client.bucket(bucket_name)
	for p in processes:
		try:
			if p.process_name and p.gcs_output_uri:
				operation_id = p.process_name.split("/")[-1]
				output_prefix = f"{p.gcs_output_uri.removeprefix(f'gs://{bucket_name}/')}{operation_id}/"
				for blob in bucket.list_blobs(prefix=output_prefix):
					blob.delete()
			if p.gcs_input_uri:
				input_path = p.gcs_input_uri.removeprefix(f"gs://{bucket_name}/")
				bucket.blob(input_path).delete()
		except Exception:
			frappe.log_error(f"OCR Job Cleanup Failed: {p.name}", frappe.get_traceback())
