// Copyright (c) 2025, yugendran@usistech.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Data Import Job', {
    refresh(frm) {
		setTimeout(() => {
            $('.menu-btn-group').hide();
        }, 100);
		setTimeout(() => {
            $('.page-icon-group').hide();
        }, 100);
		// Process file Button
        if (frm.doc.status === "Draft" ||frm.doc.status==="Failed") {
            frm.add_custom_button("Process File", function () {
                frappe.call({
                    method: "it_asset_hub.it_asset_hub.doctype.data_import_job.data_import_job.process_uploaded_file",
                    args: {
                        job_id: frm.doc.name
                    },
                    callback(r) {
                        frappe.msgprint("Processing completed.");
                        frm.reload_doc();
                    }
                });
            });
			setTimeout(function(){
				$('button:contains("Process File")')
				.css({
					'background-color':'black',
					'color':'white',
					'border':'1px solid #000'
				});
			},100);

        }

		//Extract Data button
		if (frm.doc.status === "Completed") {
			frm.set_df_property('upload_file','read_only',1);
			frm.disable_save();
		    frm.add_custom_button("View Extracted Data", function () {
                // Set filter before navigating to the list
                frappe.route_options = {
                    job_id: frm.doc.name
                };
                frappe.set_route("List", "Extracted Data");
            });
			setTimeout(function(){
				 $('button:contains("View Extracted Data")')
                    .css({
                        'background-color': 'black',
                        'color': 'white',
                        'border': '1px solid #000'
                    });
            }, 100);

		}

		//Transform the data button
		if (frm.doc.status === "Completed") {
			frm.set_df_property('upload_file','read_only',1);
			frm.disable_save();
			frm.add_custom_button("Transform the Data", function () {
                frappe.call({
                    method: "it_asset_hub.it_asset_hub.doctype.data_import_job.data_import_job.transform_data",
                    args: {
                        job_id: frm.doc.name
                    },
                    callback(r) {
						console.log(r)
						if(r.message==="Completed"){
                        frappe.msgprint("Transform completed.");
                        frm.reload_doc();
							}
						else{
								frappe.msgprint("Failed");
							}
						}

                });
            });
			setTimeout(function(){
				 $('button:contains("Transform the Data")')
                    .css({
                        'background-color': 'black',
                        'color': 'white',
                        'border': '1px solid #000'
                    });
            }, 100);

		}
        console.log(frm.doc.ttd)
		console.log(frm.doc.itd)


		//This For After insertion of transformaion hide the Transformation button and create new button for view thta data transformation view
		if(frm.doc.ttd === frm.doc.itd && frm.doc.ttd !=0 && frm.doc.itd!=0){
			setTimeout(function(){
				 $('button:contains("Transform the Data")')
                    .css({
                        'display': 'none'
                    });
            }, 100);

       frm.add_custom_button("View Transformed Data", function () {
                // Set filter before navigating to the list
                frappe.route_options = {
                    job_id: frm.doc.name
                };
                frappe.set_route("List", "Transformed Data");
            });
			setTimeout(function(){
				 $('button:contains("View Transformed Data")')
                    .css({
                        'background-color': 'black',
                        'color': 'white',
                        'border': '1px solid #000'
                    });
            }, 100);


		}


		//TOP bar Status

		//File Uploaded Status
		let file_uploaded = frm.doc.upload_file ? "✅" : "❌";
        let extract_status;
		let Trnasfrmated_Data;

		//Extract Status
		if(frm.doc.total_record===frm.doc.inserted_record && frm.doc.failed_record === 0 && frm.doc.total_record!=0 && frm.doc.inserted_record!=0 ){
         extract_status=format_status("Completed");
		}
		else if(frm.doc.failed_record!=0) {
        extract_status=format_status("Failed");
		}
		else{
			 extract_status=format_status("Draft");
		}

        //Data Transform Status
		if(frm.doc.ttd===frm.doc.itd && frm.doc.ttd !=0 && frm.doc.itd!=0){
            Trnasfrmated_Data=format_status("Completed");
		}
		else if(frm.doc.ttd!=frm.doc.itd){
          Trnasfrmated_Data=format_status("Failed");
		}
		else{
			Trnasfrmated_Data=format_status("Draft");
		}
		
        //let insert_status = format_status(frm.doc.failed_record > 0 ? "Failed" : frm.doc.inserted_record > 0 ? "Completed" : "Draft");

        let html = `
             <b>File Upload:</b> ${file_uploaded} &nbsp;&nbsp;&nbsp;
             <b>Extract:</b> ${extract_status} &nbsp;&nbsp;&nbsp;
			 <b>Data Transform:</b> ${Trnasfrmated_Data} &nbsp;&nbsp;&nbsp;

        `;

        frm.dashboard.clear_headline();
        frm.dashboard.set_headline(html);
    }

});
function format_status(status) {
    if (status === "Completed") return "✅ Completed";
    if (status === "Failed") return "❌ Failed";
    if (status === "Draft") return  "⚪ Not Started";
    return "⚪ Not Started";
}

