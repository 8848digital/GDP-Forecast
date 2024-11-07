# Copyright (c) 2024, gopal@8848digital.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime
import csv
import os
import subprocess
from frappe.model.document import Document

class GDPForecasting(Document):
	pass

@frappe.whitelist()
def upload_file(file, dataset_type):
    file = frappe.get_site_path(file.split('/')[-3], "files", file.split('/')[-1])

    # Check if the file exists before attempting to read it
    if not os.path.exists(file):
        raise FileNotFoundError(f"No such file or directory: '{file}'")

    success = handle_uploaded_file(file, dataset_type)
    if success:
        frappe.msgprint(_("Data uploaded successfully!"), indicator="green")
        return {"status": "success"}
    else:
        frappe.throw(_("Failed to upload data. Please try again."), title="Upload Error")


def handle_uploaded_file(file, dataset_type):
    success = False
    timestamp = datetime.now()
    # Check and create the "annual_dataset" table if it does not exist
    if dataset_type == 'Annual':
        frappe.db.sql("""
            CREATE TABLE IF NOT EXISTS `tabAnnual Dataset` (
                `sector` VARCHAR(255),
                `sub_sector` VARCHAR(255),
                `year` INT,
                `gdp` FLOAT,
                `upload_timestamp` DATETIME
            )
        """)

        try:
            # Clear existing records
            frappe.db.sql("TRUNCATE TABLE `tabAnnual Dataset`")

            # Process and insert data
            processed_data = process_annual_file(file)
            for sector, sub_sector, year, gdp in processed_data:
                frappe.db.sql("""
                INSERT INTO `tabAnnual Dataset` (sector, sub_sector, year, gdp, upload_timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """, (sector, sub_sector, year, gdp, timestamp))
            
            frappe.db.commit()
            frappe.msgprint("Annual data uploaded successfully!", indicator="green")
            success = True
        except Exception as e:
            frappe.log_error(f"Error processing annual file: {e}", "Annual File Upload Error")
            frappe.throw("Failed to upload annual data.")
            success = False

    # Check and create the "quarterly_dataset" table if it does not exist
    elif dataset_type == 'Quarterly':
        frappe.db.sql("""
            CREATE TABLE IF NOT EXISTS `tabQuarterly Dataset` (
                `sector` VARCHAR(255),
                `year` INT,
                `quarter` INT,
                `gdp` FLOAT,
                `upload_timestamp` DATETIME
            )
        """)

        try:
            # Clear existing records
            frappe.db.sql("TRUNCATE TABLE `tabQuarterly Dataset`")

            # Process and insert data
            processed_data = process_quarterly_file(file)
            for sector, year, quarter, gdp in processed_data:
                frappe.db.sql("""
                INSERT INTO `tabQuarterly Dataset` (sector, year, quarter, gdp, upload_timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """, (sector, year, quarter, gdp, timestamp))

            frappe.db.commit()
            frappe.msgprint("Quarterly data uploaded successfully!", indicator="green", alert=True)
            success = True
        except Exception as e:
            frappe.log_error(f"Error processing quarterly file: {e}", "Quarterly File Upload Error")
            frappe.throw("Failed to upload quarterly data.")
            success = False

    return success


def process_annual_file(file_path):
    processed_data = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        
        # Read the header
        headers = next(reader)
        
        # Verify headers
        if headers[0] != 'Sector':
            raise ValueError("CSV file format is incorrect. Expected headers starting with 'Sector' and year columns starting from '2015'.")
        
        # Process each row
        for row in reader:
            sector = row[0]
            sub_sector = row[1]
            for year, gdp in zip(headers[2:], row[2:]):
                try:
                    year = int(row[2])  # Use the header year for each column
                    gdp = float(row[3].replace(',', ''))
                    processed_data.append((sector, sub_sector, year, gdp))
                except ValueError as err:
                    print(f"Skipping row due to error: {err}")
                    continue  # Skip rows with invalid data

    return processed_data

def process_quarterly_file(file):
    processed_data = []
    with open(file, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
    
        # Read the header
        headers = next(reader)
        
        # Verify headers
        if headers[0] != 'Sector':
            raise ValueError("CSV file format is incorrect. Expected headers starting with 'Sector' and '2015'.")
        
        # Parse the data rows
        for row in reader:
            sector = row[0]
            year = 2015  # Start year
            quarter_index = 1
            for gdp in row[1:]:
                try:
                    gdp = float(gdp.replace(',', ''))
                    processed_data.append((sector, year, quarter_index, gdp))
                    quarter_index += 1
                    if quarter_index > 4:
                        quarter_index = 1
                        year += 1
                except ValueError:
                    continue  # Skip rows with invalid data
    
    return processed_data

@frappe.whitelist()
def run_forecast_script(forecast_type):
    from gdp_forecasting.forecast_scripts.holt_winters_quarterly import main
    from gdp_forecasting.forecast_scripts.holt_winters_annual import main_annual
    
    if forecast_type == 'annual_arima':
        script_path = os.path.join(os.path.dirname(__file__), 'forecast_scripts', 'arima_annual.py')
    elif forecast_type == 'quarterly_arima':
        script_path = os.path.join(os.path.dirname(__file__), 'forecast_scripts', 'arima_quarterly.py')
    elif forecast_type == 'Annual Forecast (Holt-Winters Exponential Smoothing)':
        main_annual()
    elif forecast_type == 'Quarterly Forecast (Holt-Winters Exponential Smoothing)':
        main()
    else:
        frappe.throw('Invalid forecast type selected.', title='Error')  # Show error message
    
    try:
        # Running the forecast script using subprocess
        # subprocess.run(['python3', script_path], check=True)
        frappe.msgprint('Forecast script executed successfully.')  # Show success message
    except subprocess.CalledProcessError as e:
        # If subprocess fails, raise error and log to Frappe's error log
        error_message = f"Error executing the forecast script: {str(e)}"
        frappe.log_error(message=error_message, title="Forecast Script Error")
        frappe.throw(f"An error occurred while running the forecast script. Please try again later.", title='Error')

    return 'forecast_success'

@frappe.whitelist()
def upload_base_datasets(gdp_dataset, workforce_dataset, annual_growth_rates_dataset, 
                          quarterly_growth_rates_dataset, use_existing_gdp_file, 
                          use_existing_workforce_file, use_existing_annual_growth_file, 
                          use_existing_quarterly_growth_file):
    base_path = frappe.get_app_path('gdp_forecasting', 'base_datasets')

    default_gdp_file = os.path.join(base_path, 'gdp.csv')
    default_workforce_file = os.path.join(base_path, 'workforce.csv')
    default_annual_growth_file = os.path.join(base_path, 'Annual_GrowthRates.csv')
    default_quarterly_growth_file = os.path.join(base_path, 'Quarterly_GrowthRates.csv')
    # Determine which files to use: new uploads or existing
    gdp_file = gdp_dataset if gdp_dataset else default_gdp_file
    workforce_file = workforce_dataset if workforce_dataset else default_workforce_file
    annual_growth_file = annual_growth_rates_dataset if annual_growth_rates_dataset else default_annual_growth_file
    quarterly_growth_file = quarterly_growth_rates_dataset if quarterly_growth_rates_dataset else default_quarterly_growth_file
    
    # Open database connection
    table_creation_commands = {
            "gdp": """
                CREATE TABLE IF NOT EXISTS gdp (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    Region VARCHAR(255),
                    Quarter VARCHAR(50),
                    Value FLOAT
                );
            """,
            "workforce": """
                CREATE TABLE IF NOT EXISTS workforce (
                    id INT PRIMARY KEY,
                    GOSI_classification VARCHAR(255),
                    Output_Classification VARCHAR(255),
                    Quarter VARCHAR(50),
                    Region VARCHAR(255),
                    Value FLOAT
                );
            """,
            "Annual_GrowthRates": """
                CREATE TABLE IF NOT EXISTS Annual_GrowthRates (
                    Sector VARCHAR(255),
                    GrowthRate VARCHAR(50),
                    Year INT,
                    Value FLOAT
                );
            """,
            "Quarterly_GrowthRates": """
                CREATE TABLE IF NOT EXISTS Quarterly_GrowthRates (
                    Sector VARCHAR(255),
                    GrowthRate VARCHAR(50),
                    YearQuarter VARCHAR(50),
                    Value FLOAT
                );
            """
        }

    # Execute table creation commands
    for command in table_creation_commands.values():
        frappe.db.sql(command)

    # Define tables to truncate and associated CSV files
    tables_and_files = {
        'gdp': frappe.get_site_path("private", "files", gdp_file.split('/')[-1]),
        'workforce': workforce_file,
        'Annual_GrowthRates': annual_growth_file,
        'Quarterly_GrowthRates': quarterly_growth_file
    }

    # Truncate tables and upload new data
    for table, file_obj in tables_and_files.items():
        frappe.db.sql(f"DELETE FROM `{table}`")

        if isinstance(file_obj, str):  # It's the path to the default file
            with open(file_obj, 'r') as file:
                reader = csv.reader(file)
                next(reader)  # Skip header row
                insert_data(table, reader)
        else:  # It's an uploaded file
            reader = csv.reader(file_obj.read().decode('utf-8').splitlines())
            next(reader)  # Skip header row
            insert_data(table, reader)

    return 'upload_success'


def insert_data(table, reader):
    for row in reader:
        if table == 'gdp':
            # Insert data for the 'gdp' table
            frappe.db.sql("""
                INSERT INTO `gdp` (Region, Quarter, Value)
                VALUES (%s, %s, %s)
            """, [row[1], row[2], float(row[3])])
        elif table == 'workforce':
            # Insert data for the 'workforce' table
            frappe.db.sql("""
                INSERT INTO `workforce` (id, GOSI_classification, Output_Classification, Quarter, Region, Value)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [int(row[0]), row[1], row[2], row[3], row[4], float(row[5])])
        elif table == 'Annual_GrowthRates':
            # Insert data for the 'Annual_GrowthRates' table
            frappe.db.sql("""
                INSERT INTO `Annual_GrowthRates` (Sector, GrowthRate, Year, Value)
                VALUES (%s, %s, %s, %s)
            """, [row[0], row[1], int(row[2]), float(row[3])])
        elif table == 'Quarterly_GrowthRates':
            # Insert data for the 'Quarterly_GrowthRates' table
            frappe.db.sql("""
                INSERT INTO `Quarterly_GrowthRates` (Sector, GrowthRate, YearQuarter, Value)
                VALUES (%s, %s, %s, %s)
            """, [row[0], row[1], row[2], float(row[3])])