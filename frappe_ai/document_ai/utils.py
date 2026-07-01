# Copyright (c) 2026, Sambhav Saxena and contributors
# For license information, please see license.txt

import frappe


def resolve_file_path(file_path: str) -> str:
	if not file_path:
		return file_path
	if file_path.startswith("/private/files/"):
		return frappe.utils.get_files_path(file_path[len("/private/files/"):], is_private=True)
	if file_path.startswith("/files/"):
		return frappe.utils.get_files_path(file_path[len("/files/"):])
	return file_path


def mark_ocr_failed(ocr_process):
	traceback = frappe.get_traceback()
	frappe.log_error("OCR Processing Error", traceback)
	frappe.db.set_value(
		"OCR Process",
		ocr_process.name,
		{"status": "Failed", "error_log": traceback},
	)
	frappe.db.commit()
