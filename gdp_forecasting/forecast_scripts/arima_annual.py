import numpy as np
import pandas as pd
from pmdarima import auto_arima
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.stattools import adfuller
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

# Function to load and clean data from SQL Server
def load_and_clean_data_from_sql_server():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM annual_dataset")
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        df = pd.DataFrame(rows, columns=columns)

    # Keep only relevant columns and aggregate GDP values for the same sector and year
    df = df[['sector', 'year', 'gdp']].groupby(['sector', 'year']).sum().reset_index()
    relevant_sectors = [
        'Agriculture, Forestry & Fishing', 'Mining & Quarrying', 'Manufacturing',
        'Electricity, Gas and Water', 'Construction', 'Wholesale & Retail Trade, Restaurants & hotels',
        'Transport, Storage & Communication', 'Finance, Insurance, Real Estate & Business Services',
        'Community, Social & Personal Services', 'Government Activities', 'Gross Domestic Product', 'Total Riyadh GDP'
    ]
    df = df[df['sector'].isin(relevant_sectors)]

    # Pivot the dataset to have years as columns
    df_pivot = df.pivot(index='sector', columns='year', values='gdp').reset_index()

    # Fill NaN values with 0 (or use any other method to handle missing data)
    df_pivot = df_pivot.fillna(0)

    return df_pivot

# Function to check for stationarity and make series stationary if needed
def make_stationary(series):
    result = adfuller(series)
    if result[1] > 0.05:
        series = np.diff(series)
    return series

# Function to forecast GDP using AUTO ARIMA and calculate accuracy metrics
def forecast_gdp_auto_arima(data, start_year, end_year):
    forecast_years = np.arange(start_year, end_year + 1)
    forecasts = {}
    metrics = {}
    total_mae = []
    total_mse = []
    total_rmse = []

    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE arima_annual")

        for sector in data['sector']:
            series = data.loc[data['sector'] == sector, 2015:2023].values.flatten()
            series = make_stationary(series)  # Make the series stationary if needed
            model = auto_arima(series, seasonal=True, stepwise=True, suppress_warnings=True)
            forecast = model.predict(n_periods=len(forecast_years))
            forecasts[sector] = forecast

            # Calculate metrics
            train_predictions = model.predict_in_sample()
            mse = mean_squared_error(series, train_predictions)
            rmse = np.sqrt(mse)
            total_mse.append(mse)
            total_rmse.append(rmse)
            total_mae.append(mean_absolute_error(series, train_predictions))
            for year, gdp in zip(forecast_years, forecast):
                cursor.execute(
                    "INSERT INTO arima_annual (sector, year, gdp, rmse) VALUES (%s, %s, %s, %s)",
                    (sector, int(year), float(gdp), float(rmse))
                )

    metrics['mae'] = np.mean(total_mae)
    metrics['mse'] = np.mean(total_mse)
    metrics['rmse'] = np.mean(total_rmse)

    return forecasts, metrics

# Main function to run the entire forecasting process
def main():
    data = load_and_clean_data_from_sql_server()
    start_year = 2024
    end_year = 2030
    forecasts, metrics = forecast_gdp_auto_arima(data, start_year, end_year)
    print(forecasts)
    print(metrics)

if __name__ == "__main__":
    main()
