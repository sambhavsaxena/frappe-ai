# Copyright (c) 2026, Sambhav Saxena and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document

from frappe_ai.document_ai.ocr import check_operation_progress, process_sync_ocr_job
from frappe_ai.document_ai.storage import extract_process_output


class OCRProcess(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		completed_at: DF.Datetime | None
		error_log: DF.LongText | None
		file_path: DF.Attach
		gcs_input_uri: DF.SmallText | None
		gcs_output_uri: DF.SmallText | None
		process_name: DF.Data | None
		processing_mode: DF.Literal["Synchronous", "Asynchronous"]
		raw_response: DF.JSON | None
		started_at: DF.Datetime | None
		status: DF.Literal["Draft", "Queued", "Processing", "Completed", "Failed"]
	# end: auto-generated types

	@frappe.whitelist()
	def start(self):
		if self.status in ("Queued", "Processing"):
			frappe.throw(_("This OCR Process is already running."))

		self.db_set("error_log", None)

		if self.processing_mode == "Synchronous":
			process_sync_ocr_job(self)
		elif self.processing_mode == "Asynchronous":
			self.db_set("status", "Queued")
			frappe.enqueue(
				"frappe_ai.document_ai.ocr.process_async_ocr_job",
				queue="long",
				timeout=300,
				ocr_process_name=self.name,
			)
		else:
			frappe.throw(_("Invalid processing mode."))

	@frappe.whitelist()
	def check_status(self):
		if not self.process_name:
			frappe.throw(_("No process name found for this OCR Process."))

		status = check_operation_progress(self.process_name)
		if not status.done:
			frappe.msgprint(_("The OCR process is still running."), alert=True, indicator="blue")
			return

		if not status.success:
			self.db_set("status", "Failed")
			self.db_set("error_log", json.dumps(status.error))
			return

		extracted_data = extract_process_output(self)
		self.db_set("raw_response", json.dumps(extracted_data))
		self.db_set("status", "Completed")
		self.db_set("completed_at", frappe.utils.now())
