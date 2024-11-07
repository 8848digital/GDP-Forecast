import frappe
import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.metrics import mean_squared_error
from math import sqrt
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Custom parser for quarterly data
def custom_quarterly_parser(year_q):
    year, quarter = year_q.split()
    quarter_number = int(quarter[1])  # Extract the quarter number from 'Qx'
    month = (quarter_number - 1) * 3 + 1  # Calculate the starting month of the quarter
    return f"{year}-Q{quarter_number}"

# Convert date to 'YYYY-QQ' format
def date_to_quarter_string(date):
    year = date.year
    quarter = (date.month - 1) // 3 + 1
    return f"{year}-Q{quarter}"

# Load and prepare data from Frappe table
def load_and_prepare_data_from_frappe():
    # Create `holt_winters_quarterly` table if it doesn’t exist
    frappe.db.sql("""
        CREATE TABLE IF NOT EXISTS `holt_winters_quarterly` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `sector` VARCHAR(255),
            `year_quarter` VARCHAR(50),
            `gdp` FLOAT,
            `rmse` FLOAT
        );
    """)
    
    # Load data from `quarterly_dataset` table
    query_result = frappe.db.sql("SELECT * FROM `tabQuarterly Dataset`", as_dict=True)
    if query_result:
        try:
            # Replace None with empty strings or another placeholder
            cleaned_data = [
                {k: (v if v is not None else "") for k, v in record.items()}
                for record in query_result
            ]
            df = pd.DataFrame(cleaned_data)
        except Exception as e:
            print("Error creating DataFrame:", e)
    else:
        print("No data found in `tabQuarterly Dataset`.")
    # Create a column for time periods
    df['Year_Quarter'] = df['year'].astype(str) + ' Q' + df['quarter'].astype(str)
    
    # Parse dates
    df['Date'] = df['Year_Quarter'].apply(custom_quarterly_parser)
    df.index = pd.to_datetime(df['Date'])
    df.sort_index(inplace=True)

    # Clear existing data in `holt_winters_quarterly`
    frappe.db.sql("TRUNCATE TABLE `holt_winters_quarterly`")

    # Insert initial data
    for index, row in df.iterrows():
        frappe.db.sql("""
            INSERT INTO `holt_winters_quarterly` (sector, year_quarter, gdp, rmse)
            VALUES (%s, %s, %s, %s)
        """, (row['sector'], row['Date'], row['gdp'], 0))
    
    return df

# Define a function to calculate RMSE
def calculate_rmse(actual, predicted):
    return sqrt(mean_squared_error(actual, predicted))

# Apply the Exponential Smoothing model to all sectors
def apply_exponential_smoothing_to_all_sectors(data, start_period, end_period):
    forecast_results = pd.DataFrame()
    sectors = data['sector'].unique()
    quarters = ["Q1", "Q2", "Q3", "Q4"]

    for sector in sectors:
        sector_data = data[data['sector'] == sector]['gdp']
        model = ExponentialSmoothing(sector_data, trend='add', seasonal='add', seasonal_periods=4)
        model_fit = model.fit()

        # Forecasting the required number of steps (quarters)
        forecast_steps = (end_period - start_period + 1) * 4  # Quarterly data
        forecast = model_fit.forecast(steps=forecast_steps)
        forecast_df = pd.DataFrame(forecast, columns=['mean'])
        forecast_df['Sector'] = sector

        # Generate sequential quarters based on start and end period
        forecast_df['Quarter'] = [
            f"{year}-{quarter}"
            for year in range(start_period, end_period + 1)
            for quarter in quarters
        ][:forecast_steps]  # Truncate if overestimated

        forecast_df['mean'] = forecast_df['mean'].clip(lower=0)  # Ensure non-negative values

        # Calculate RMSE for each sector
        rmse = calculate_rmse(sector_data, model_fit.fittedvalues)
        forecast_df['RMSE'] = rmse
        forecast_results = pd.concat([forecast_results, forecast_df[['Sector', 'Quarter', 'mean', 'RMSE']]])

        # Insert forecast data into database
        for date, gdp in zip(forecast_df['Quarter'], forecast_df['mean']):
            frappe.db.sql("""
                INSERT INTO `holt_winters_quarterly` (sector, year_quarter, gdp, rmse)
                VALUES (%s, %s, %s, %s)
            """, (sector, date, float(gdp), float(rmse)))

    return forecast_results

# Save forecasts to a single CSV
def save_forecasts(forecasts, output_file):
    forecasts.to_csv(output_file, index=False)

# Main function to run the entire forecasting process
def main():
    data = load_and_prepare_data_from_frappe()
    forecasts = apply_exponential_smoothing_to_all_sectors(data, 2024, 2030)
