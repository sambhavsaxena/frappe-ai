// Copyright (c) 2026, Sambhav Saxena and contributors
// For license information, please see license.txt

frappe.ui.form.on("OCR Process", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		if (["Draft", "Failed"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Start Processing"), () => start_processing(frm)).addClass("btn-primary");
		}
	},
	file_path(frm) {
        const file_url = frm.doc.file_path;
        if (!file_url) return;
        const allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png'];
        const extension = file_url.split('.').pop().toLowerCase();
        if (!allowed_extensions.includes(extension)) {
            frappe.msgprint(__("File type not supported. It must be one of the following: {0}", [allowed_extensions.join(', ')]));
            frm.set_value('file_path', '');
        }
    }
});

function start_processing(frm) {
	if (frm.doc.processing_mode === "Synchronous") {
		frm.call({
			method: "start",
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Extracting text from your document. This might take a few minutes depending on the size of your document."),
		}).then(() => frm.reload_doc());
		return;
	}
	else if (frm.doc.processing_mode === "Asynchronous") {
		frappe.show_alert({
			message: __("Document queued. The result will be fetched asynchronously by a background job."),
			indicator: "blue",
		});
		frm.call("start").then(() => frm.reload_doc());
	}
}
