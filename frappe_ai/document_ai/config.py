# Copyright (c) 2026, Sambhav Saxena and contributors
# For license information, please see license.txt


import json

import frappe
from google.cloud import documentai_v1 as documentai
from google.cloud import storage
from google.oauth2 import service_account


VALID_MIME_TYPES = {
	".pdf": "application/pdf",
	".jpg": "image/jpeg",
	".jpeg": "image/jpeg",
	".png": "image/png",
}


def get_settings():
    settings = frappe.get_single("Document AI Settings")
    missing = [field for field in ("project_id", "location", "processor_id", "cloud_storage_bucket") if not settings.get(field)]
    if missing:
        frappe.throw("Document AI Not Configured", f"Document AI Settings is incomplete. Missing: {', '.join(missing)}")

    return settings


def get_credentials(settings):
    key = json.loads(settings.get("service_account"))
    return service_account.Credentials.from_service_account_info(key)


def get_google_storage_client():
    settings = get_settings()
    return storage.Client(credentials=get_credentials(settings))


def get_document_ai_client():
    settings = get_settings()
    location = settings.get("location")
    return documentai.DocumentProcessorServiceClient(
        credentials=get_credentials(settings),
        client_options={"api_endpoint": f"{location}-documentai.googleapis.com"},
    )
