// Copyright (c) 2025, yugendran@usistech.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset Request", {
	refresh(frm) {
      if(!frm.doc.created_by){
       frm.set_value('created_by',frappe.session.user);
    }
	},
});
