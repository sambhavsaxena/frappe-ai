# Copyright (c) 2026, Sambhav Saxena and contributors
# For license information, please see license.txt


import json

from frappe_ai.document_ai.config import get_settings, get_google_storage_client


def upload_to_gc_bucket(local_file, gcs_path, bucket_name):
	client = get_google_storage_client()
	bucket = client.bucket(bucket_name)
	blob = bucket.blob(gcs_path)
	blob.upload_from_filename(local_file)
	blob.reload()
	return f"gs://{bucket_name}/{gcs_path}", blob.content_type


def extract_process_output(ocr_process):
    client = get_google_storage_client()
    settings = get_settings()
    bucket = settings.get("cloud_storage_bucket")
    bucket_object = client.bucket(bucket)
    operation_id = ocr_process.process_name.split("/")[-1]
    output_path = ocr_process.gcs_output_uri.removeprefix(f"gs://{bucket}/")
    prefix = f"{output_path}{operation_id}/"
    results = []
    for blob in bucket_object.list_blobs(prefix=prefix):
        if blob.name.endswith(".json"):
            results.append(json.loads(blob.download_as_text()))
    return results
