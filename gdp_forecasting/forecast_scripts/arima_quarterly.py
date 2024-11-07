import pandas as pd
import numpy as np
from pmdarima import auto_arima
from sklearn.metrics import mean_squared_error
from pathlib import Path
import os
from dotenv import load_dotenv
from django.db import connection
from django.conf import settings
import django

# Initialize Django settings
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR.parent / '.env'
load_dotenv(dotenv_path=env_path)

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

settings.configure(
    DATABASES={
        'default': {
            'ENGINE': 'sql_server.pyodbc',
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
            'OPTIONS': {
                'driver': 'ODBC Driver 17 for SQL Server',
                'extra_params': 'TrustServerCertificate=yes;',
            },
        }
    },
    INSTALLED_APPS=[
        'django.contrib.contenttypes',
    ],
    USE_TZ=True,
    TIME_ZONE='UTC+3',
)

django.setup()

# Custom parser for quarterly data
def custom_quarterly_parser(year_q):
    year, quarter = year_q.split()
    quarter_number = int(quarter[1])  # Extract the quarter number from 'Qx'
    month = (quarter_number - 1) * 3 + 1  # Calculate the starting month of the quarter
    return f"{year}-{month:02d}-01"  # Return the first day of the starting month

# Convert date to 'YYYY-QQ' format
def date_to_quarter_string(date):
    year = date.year
    quarter = (date.month - 1) // 3 + 1
    return f"{year}-Q{quarter}"

# Load and prepare data from SQL Server
def load_and_prepare_data_from_sql_server():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM quarterly_dataset")
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        df = pd.DataFrame(rows, columns=columns)

    # Create a column for time periods
    df['Year_Quarter'] = df['year'].astype(str) + ' Q' + df['quarter'].astype(str)
    
    # Parse dates
    df['Date'] = df['Year_Quarter'].apply(custom_quarterly_parser)
    df.index = pd.to_datetime(df['Date'])
    df.sort_index(inplace=True)
    
    return df

# Apply AUTO ARIMA model to all sectors
def apply_auto_arima_to_all_sectors(data, start_period, end_period):
    forecast_results = pd.DataFrame()
    sectors = data['sector'].unique()

    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE arima_quarterly")

        for sector in sectors:
            sector_data = data[data['sector'] == sector]['gdp']
            log_sector_data = np.log1p(sector_data)  # Log-transform the data
            model = auto_arima(log_sector_data, seasonal=True, m=4, stepwise=True, suppress_warnings=True)
            forecast_steps = (end_period - start_period + 1) * 4  # Quarterly data
            forecast = model.predict(n_periods=forecast_steps)
            forecast_df = pd.DataFrame({'mean': forecast, 'Quarter': pd.date_range(start=sector_data.index[-1], periods=forecast_steps + 1, freq='Q')[1:]})
            forecast_df['Sector'] = sector
            forecast_df['mean'] = np.expm1(forecast_df['mean'])  # Reverse log-transform
            forecast_df['mean'] = forecast_df['mean'].clip(lower=0)  # Ensure non-negative values

            min_gdp = sector_data[sector_data > 0].min()  # Find minimum positive GDP value
            forecast_df.loc[forecast_df['mean'] < 0, 'mean'] = min_gdp  # Replace negative values with minimum positive GDP value

            forecast_df['RMSE'] = np.sqrt(mean_squared_error(sector_data, np.expm1(model.predict_in_sample())))
            forecast_df['Quarter'] = forecast_df['Quarter'].apply(date_to_quarter_string)
            
            for date, gdp in zip(forecast_df['Quarter'], forecast_df['mean']):
                cursor.execute(
                    "INSERT INTO arima_quarterly (sector, year_quarter, gdp, rmse) VALUES (%s, %s, %s, %s)",
                    (sector, date, float(gdp), float(forecast_df['RMSE'][0]))
                )

            forecast_results = pd.concat([forecast_results, forecast_df[['Sector', 'Quarter', 'mean', 'RMSE']]])
    
    return forecast_results

# Save forecasts to a single CSV
def save_forecasts(forecasts, output_file):
    forecasts.to_csv(output_file, index=False)

# Main function to run the entire forecasting process
def main():
    data = load_and_prepare_data_from_sql_server()
    forecasts = apply_auto_arima_to_all_sectors(data, 2024, 2030)
    # save_forecasts(forecasts, output_file)

# # Parameters
# output_file = 'Consolidated_GDP_Forecast_2024-2030_auto_arima.csv'

# Run the script
main()
