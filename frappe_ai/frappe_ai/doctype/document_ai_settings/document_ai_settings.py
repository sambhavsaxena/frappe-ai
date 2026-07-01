# Copyright (c) 2026, Sambhav Saxena and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document


class DocumentAISettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cloud_storage_bucket: DF.Data | None
		input_prefix: DF.Data | None
		location: DF.Literal["us", "eu"]
		output_prefix: DF.Data | None
		processor_id: DF.Data | None
		project_id: DF.Data
		service_account: DF.JSON
	# end: auto-generated types

	_DOCTYPE_NAME = "Document AI Settings"
