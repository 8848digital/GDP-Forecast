// Copyright (c) 2024, gopal@8848digital.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('GDP Forecasting', {
    upload: function(frm) {
        frappe.call({
            method: "gdp_forecasting.gdp_forecasting.doctype.gdp_forecasting.gdp_forecasting.upload_file",
            args: {
                file: frm.doc.file,
				dataset_type: frm.doc.dataset_type
            },
            callback: function(response) {
                // Handle the response from the server-side function here
                if (response.message) {
                    // frappe.msgprint("Upload successful and Python function executed.");
                }
            },
            error: function(err) {
                frappe.msgprint("There was an error in processing the upload.");
                console.error(err);
            }
        });
    },
    run: function(frm) {
        frappe.call({
            method: "gdp_forecasting.gdp_forecasting.doctype.gdp_forecasting.gdp_forecasting.run_forecast_script",
            args: {
				forecast_type: frm.doc.forecast_type
            },
            callback: function(response) {
                // Handle the response from the server-side function here
                if (response.message) {
                    frappe.msgprint("Upload successful and Python function executed.");
                }
            },
            error: function(err) {
                frappe.msgprint("There was an error in processing the upload.");
                console.error(err);
            }
        });
    },
    upload_base: function(frm) {
        // Function to replace undefined with null
        function handleUndefined(value) {
            return value === undefined ? null : value;
        }
    
        frappe.call({
            method: "gdp_forecasting.gdp_forecasting.doctype.gdp_forecasting.gdp_forecasting.upload_base_datasets",
            args: {
                gdp_dataset: handleUndefined(frm.doc.gdp_dataset),
                workforce_dataset: handleUndefined(frm.doc.workforce_dataset),
                annual_growth_rates_dataset: handleUndefined(frm.doc.annual_growth_rates_dataset),
                quarterly_growth_rates_dataset: handleUndefined(frm.doc.quarterly_growth_rates_dataset),
                use_existing_gdp_file: handleUndefined(frm.doc.use_existing_gdp_file),
                use_existing_workforce_file: handleUndefined(frm.doc.use_existing_workforce_file),
                use_existing_annual_growth_file: handleUndefined(frm.doc.use_existing_annual_growth_file),
                use_existing_quarterly_growth_file: handleUndefined(frm.doc.use_existing_quarterly_growth_file)
            },
            callback: function(response) {
                if (response.message) {
                    frappe.msgprint("Upload successful and Python function executed.");
                }
            },
            error: function(err) {
                frappe.msgprint("There was an error in processing the upload.");
                console.error(err);
            }
        });
    },
    refresh: function(frm) {
        frm.add_custom_button(__('GDP Report'), function() {
            frappe.set_route('query-report', 'GDP Forecasting');
        });
    }
    
});

