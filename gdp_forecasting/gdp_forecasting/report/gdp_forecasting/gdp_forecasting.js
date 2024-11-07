// Copyright (c) 2024, gopal@8848digital.com and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GDP Forecasting"] = {
	"filters": [
        {
            "fieldname": "forecast_type",
            "label": __("Forecast Type"),
            "fieldtype": "Select",
            "options": [
                "Annual",
                "Quarterly"
            ],
            "default": "Annual"
        }
    ]
};
