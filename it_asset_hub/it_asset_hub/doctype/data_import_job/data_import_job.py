# Copyright (c) 2025, yugendran@usistech.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import pandas as pd
import os
import io
from frappe.utils.file_manager import save_file
from frappe.utils import now

class DataImportJob(Document):
    pass

def safe_get(val):
    """Convert NaN to None to avoid DB issues"""
    if pd.isna(val):
        return None
    return val

@frappe.whitelist()
def process_uploaded_file(job_id):
    EXPECTED_COLUMNS = [
    "Date", "EMPL code", "EMPL Name", "Vouch No", "Ledger account",
    "Account Name", "Remarks", "Dr Amt (AED)", "Cr Amt (AED)", "Balance"
    ]

    doc = frappe.get_doc("Data Import Job", job_id)
    print(doc)

    if not doc.upload_file:
        frappe.throw("No file attached.")

    # Clean file path
    file_path = frappe.get_site_path("public", "files", doc.upload_file.split("/files/")[-1])

    print("File path:", file_path)
    if not os.path.exists(file_path):
        file_path = frappe.get_site_path("private", "files", doc.upload_file.split("/files/")[-1])


    if not os.path.exists(file_path):
        frappe.throw("File not found at: " + file_path)

    # Read CSV or Excel file
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)


        actual_columns = df.columns.tolist()
        missing_columns = [col for col in EXPECTED_COLUMNS if col not in actual_columns]
        extra_columns = [col for col in actual_columns if col not in EXPECTED_COLUMNS]
        if missing_columns or extra_columns:
            doc.status = "Failed"
            doc.save()
            frappe.db.commit()
            error_parts = []
            if missing_columns:
                error_parts.append(f"Missing columns: {', '.join(missing_columns)}")
            if extra_columns:
                error_parts.append(f"Unexpected columns: {', '.join(extra_columns)}")

            #frappe.throw(f"The uploaded file is missing required columns: {', '.join(missing_columns)}")
            error_message = "Invalid file format.<br>" + "<br>".join(error_parts)
            frappe.throw("Invalid file format. Please upload a file using the correct template.")

    except Exception as e:
        doc.status = "Failed"
        doc.save()
        frappe.db.commit()
        frappe.throw(f"Error reading file: {e}")

    total = len(df)
    success = 0
    failed = 0
    error_message=""
    failed_rows = []

    for i, row in df.iterrows():
        try:
            frappe.get_doc({
                "doctype": "Extracted Data",
                "date":parse_date(safe_get(row.get("Date"))),
                "emplcode": safe_get(row.get("EMPL code")),
                "emplname": safe_get(row.get("EMPL Name")),
                "vouch_no": safe_get(row.get("Vouch No")),
                "ledger_account": safe_get(row.get("Ledger account")),
                "account_name": safe_get(row.get("Account Name")),
                "remarks": safe_get(row.get("Remarks")),
                "dr_amt_aed": safe_get(row.get("Dr Amt (AED)")),
                "cr_amt_aed": safe_get(row.get("Cr Amt (AED)")),
                "balance": safe_get(row.get("Balance")),
                "job_id": job_id
            }).insert(ignore_permissions=True)
            success += 1
        except Exception as e:
            failed += 1
            failed_rows.append({**row.to_dict(), "Error": str(e)})
            error_message=str(e)

    # Save failed rows to file
    if failed_rows:
        failed_df = pd.DataFrame(failed_rows)
        buf = io.StringIO()
        failed_df.to_csv(buf, index=False)
        content = buf.getvalue()
        filename = f"Failed_Rows_{job_id.replace(' ', '_')}_{now()}.csv"
        uploaded_file = save_file(filename, content, "Data Import Job", doc.name, is_private=0)
        doc.failed_file = uploaded_file.file_url  # Make sure this field exists

    # Update job status and metrics
    doc.total_record = total
    doc.inserted_record = success
    doc.failed_record = failed
    doc.status = "Completed" if failed == 0 else "Failed"
    doc.save()
    current_user = frappe.session.user
    if doc.status != "Failed":
        frappe.get_doc({
			"doctype":"Comment",
			"reference_name":job_id,
			"reference_doctype":"Data Import Job",
			"comment_type":"Info",
			"reference_owner":current_user,
			"content":f"Total Records Fetch from Doument {total}. Total Records Inserted Successfully {success}. ",
		}).insert()
    else:
        frappe.get_doc({
			"doctype":"Comment",
			"reference_doctype":"Data Import Job",
			"comment_type":"Info",
            "reference_name":job_id,
			"reference_owner":current_user,
			"content":f"Total Faild Records {failed} and Faild Record Reason {error_message}. Total Failed Records {error_message}",
		}).insert()


    return "Processed"

from datetime import datetime
def parse_date(date_str):
    if not date_str:
        return None
    try:
        # Convert from 'DD-MM-YYYY' to 'YYYY-MM-DD'
        return datetime.strptime(date_str, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None

@frappe.whitelist()
def transform_data(job_id):
   Success=0
   Failed=0
   error_message=""
   result = frappe.db.sql("""
    SELECT
        emplcode AS `Employee Number`,
        SUBSTRING_INDEX(ledger_account, '-', -1) AS `Loan Component`,
        COUNT(SUBSTRING_INDEX(ledger_account, '-', -1)) AS `Loan Period`,
        SUM(dr_amt_aed) AS `Loan Amount`,
        0 AS `Rate of Interset`,
        DATE_FORMAT(`date`,'01-%%m-%%Y') AS `Start Date`,
        'Flat Interest' AS `Loan Type`
    FROM `tabExtracted Data`
    WHERE job_id = %s
      AND DATE_FORMAT(`date`, '%%Y-%%m') = (
          SELECT DATE_FORMAT(MAX(`date`), '%%Y-%%m')
          FROM `tabExtracted Data`
          WHERE job_id = %s
      )
    GROUP BY emplcode, SUBSTRING_INDEX(ledger_account, '-', -1)
	""", (job_id, job_id), as_dict=True)

   for row in result:
        try:
             doc = frappe.get_doc({
                 "doctype": "Transformed Data",  # change to your target Doctype
                 "employee_number": safe_get(row.get("Employee Number")),
                 "loan_component": safe_get(row.get("Loan Component")),
                 "loan_period": safe_get(row.get("Loan Period")),
                 "loan_amount": safe_get(row.get("Loan Amount")),
                 "rate_of_interest": safe_get(row.get("Rate of Interset")),
                 "start_date": parse_date(safe_get(row.get("Start Date"))),
                 "loan_type":safe_get(row.get("Loan Type")),
                 "job_id":job_id
                 })
             doc.insert(ignore_permissions=True)
             Success += 1
        except Exception as e:
            Failed += 1
            error_message = str(e)



   total=len(result)
   frappe.db.set_value("Data Import Job",job_id,{
       "ttd":total,
       "itd":Success
   })
   current_user = frappe.session.user
#    frappe.get_doc({
#         "doctype":"Comment",
#         "reference_doctype":"Data Import Job",
#         "comment_type":"Info",
#         "reference_owner":current_user,
#         "content":f"Total Data Transformed Records {total}. Total Data Transformed Records Inserted Successfully {Success}.",
# 	}).insert()

   if(Success==total):
       frappe.get_doc({
        "doctype":"Comment",
        "reference_doctype":"Data Import Job",
        "comment_type":"Info",
        "reference_name":job_id,
        "reference_owner":current_user,
        "content":f"Total Data Transformed Records {total}. Total Data Transformed Records Inserted Successfully {Success}.",
	}).insert()
       return "Completed"
   else:
       frappe.get_doc({
        "doctype":"Comment",
        "reference_doctype":"Data Import Job",
        "comment_type":"Info",
        "reference_name":job_id,
        "reference_owner":current_user,
        "content":f"Total Data Transformed Records {Failed}. Total Data Transformed Records Inserted Successfully {error_message}.",
	}).insert()
       return "Failed"



