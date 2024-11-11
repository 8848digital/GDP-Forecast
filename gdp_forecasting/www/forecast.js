var selectedForecast = "";

function selectForecast(forecast) {
    document.getElementById('dropdownMenuButton').textContent = forecast;
    selectedForecast = forecast;
}

function runFunction() {
    if (!selectedForecast) {
        frappe.msgprint("Please select a forecast type before running.");
        return;
    }

    frappe.call({
        method: "gdp_forecasting.gdp_forecasting.gdp_forecasting.run_forecast_script",
        args: {
            forecast_type: selectedForecast 
        },
        callback: function(response) {
            if (response.message) {
                setTimeout(function() {
                    window.location.href = '/app/query-report/GDP%20Forecasting'
                }, 1000);
            }
        },
        error: function(err) {
            frappe.msgprint("There was an error in processing the upload.");
            console.error(err);
        }
    });
}