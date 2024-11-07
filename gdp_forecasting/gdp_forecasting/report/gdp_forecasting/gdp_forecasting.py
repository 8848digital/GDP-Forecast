# Copyright (c) 2024, gopal@8848digital.com and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    columns, data = [], []

    if filters and filters.get("forecast_type"):
        forecast_type = filters["forecast_type"]
        
        table_name = None
        if forecast_type == "Annual":
            table_name = "tabHolt Winters Annual"
        elif forecast_type == "Quarterly":
            table_name = "holt_winters_quarterly"

        if table_name:
            column_query = f"DESCRIBE `{table_name}`"
            columns_result = frappe.db.sql(column_query, as_dict=True)

            columns = [{"label": column['Field'], "fieldname": column['Field'], "fieldtype": 'Data', "width": 250} for column in columns_result[1:]]

            data_query = f"SELECT * FROM `{table_name}`"
            data = frappe.db.sql(data_query, as_dict=True)

    return columns, data
