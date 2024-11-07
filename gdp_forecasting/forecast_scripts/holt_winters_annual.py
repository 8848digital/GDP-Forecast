import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.metrics import mean_squared_error
from math import sqrt
from itertools import product
import frappe

def main_annual():
    # Function to load data from the database
    def load_data_from_db():
        query = "SELECT * FROM `tabAnnual Dataset`"
        query = frappe.db.sql(query, as_dict=True)
        if query:
            try:
                # Replace None with empty strings or another placeholder
                cleaned_data = [
                    {k: (v if v is not None else "") for k, v in record.items()}
                    for record in query
                ]
                df = pd.DataFrame(cleaned_data)
                print(df.head())  # Check the DataFrame output
            except Exception as e:
                print("Error creating DataFrame:", e)
        else:
            print("No data found in `tabQuarterly Dataset`.")
        relevant_sectors = [
            'Agriculture, Forestry & Fishing', 'Mining & Quarrying', 'Manufacturing',
            'Electricity, Gas and Water', 'Construction', 'Wholesale & Retail Trade, Restaurants & hotels',
            'Transport, Storage & Communication', 'Finance, Insurance and Business services',
            'Community, Social & Personal Services', 'Government Activities', 'Total Riyadh GDP'
        ]
        df = df[df['sector'].isin(relevant_sectors)]
        return df

    # Function to insert predictions and historical data into the database
    def insert_predictions_to_db(predictions, rmse_values):
        # Create table if it doesn't exist
        frappe.db.sql("""
            CREATE TABLE IF NOT EXISTS `tabHolt Winters Annual` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `name` VARCHAR(255) UNIQUE,
                `sector` VARCHAR(255),
                `year` INT,
                `gdp` FLOAT,
                `rmse` FLOAT
            )
        """)

        # Clear existing data in the table
        frappe.db.sql("TRUNCATE TABLE `tabHolt Winters Annual`")

        # Load the dataset from the database to avoid re-reading if already loaded
        df = load_data_from_db()

        # Insert historical data
        for sector in df['sector'].unique():
            sector_data = df[df['sector'] == sector]
            for index, row in sector_data.iterrows():
                # Check if the record already exists in the table
                existing_record = frappe.db.sql("""
                    SELECT COUNT(*) FROM `tabHolt Winters Annual`
                    WHERE name = %s
                """, (f"{row['sector']}-{row['year']}",))

                if existing_record[0][0] == 0:  # If no record exists
                    frappe.db.sql(
                        """
                        INSERT INTO `tabHolt Winters Annual` (name, sector, year, gdp, rmse)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (f"{row['sector']}-{row['year']}", row['sector'], int(row['year']), float(row['gdp']), 0)  # 0 for RMSE in historical data
                    )

        # Insert forecast data
        for sector, forecast in predictions.items():
            rmse = rmse_values.get(sector, 0)  # Default RMSE to 0 if not found
            for year, gdp in zip(prediction_years, forecast):
                # Check if the record already exists in the table
                existing_record = frappe.db.sql("""
                    SELECT COUNT(*) FROM `tabHolt Winters Annual`
                    WHERE name = %s
                """, (f"{sector}-{year}",))

                if existing_record[0][0] == 0:  # If no record exists
                    frappe.db.sql(
                        """
                        INSERT INTO `tabHolt Winters Annual` (name, sector, year, gdp, rmse)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (f"{sector}-{year}", sector, int(year), float(gdp), float(rmse))
                    )


    # Pivoting the DataFrame
    def calculate_rmse(actual, predicted):
        return sqrt(mean_squared_error(actual, predicted))

    # Initialize a dictionary to store RMSE values
    def grid_search(train, test):
        best_rmse = float('inf')
        best_params = None
        trend_options = ['add', 'mul', None]
        seasonal_options = ['add', 'mul', None]
        seasonal_periods_options = [3, 4, 5, 6]

        for trend, seasonal, seasonal_periods in product(trend_options, seasonal_options, seasonal_periods_options):
            if seasonal is None and trend is None:
                continue  # skip invalid combination
            try:
                model = ExponentialSmoothing(train, trend=trend, seasonal=seasonal, seasonal_periods=seasonal_periods)
                fit = model.fit()
                forecast = fit.forecast(steps=len(test))
                rmse = calculate_rmse(test, forecast)
                if rmse < best_rmse:
                    best_rmse = rmse
                    best_params = (trend, seasonal, seasonal_periods)
            except:
                continue

        return best_rmse, best_params

    df = load_data_from_db()
    print("Data loaded from the database.")
    print(df.head())

    # Pivot the DataFrame
    pivot_df = df.pivot_table(index='sector', columns='year', values='gdp', aggfunc='sum')
    print("Pivoted DataFrame:")
    print(pivot_df.head())

    # Fill NaN values with zeros
    pivot_df = pivot_df.fillna(0)

    relevant_sectors = [
        'Agriculture, Forestry & Fishing', 'Mining & Quarrying', 'Manufacturing',
        'Electricity, Gas and Water', 'Construction', 'Wholesale & Retail Trade, Restaurants & hotels',
        'Transport, Storage & Communication', 'Finance, Insurance and Business services',
        'Community, Social & Personal Services', 'Government Activities', 'Total Riyadh GDP'
    ]
    pivot_df = pivot_df[pivot_df.index.isin(relevant_sectors)]

    # Calculate RMSE for each sector
    rmse_values = {}
    for sector in pivot_df.index:
        ts = pivot_df.loc[sector].values
        train_size = int(len(ts) * 0.8)
        train, test = ts[:train_size], ts[train_size:]

        # Initialize and fit the model on the training set
        model = ExponentialSmoothing(train, trend='add', seasonal='add', seasonal_periods=3)
        fit = model.fit()
        forecast = fit.forecast(steps=len(test))

        # Calculate RMSE for the sector
        rmse = calculate_rmse(test, forecast)
        rmse_values[sector] = rmse

    # Define best parameters for each sector
    best_params_dict = {
        'Agriculture, Forestry & Fishing': ('mul', 'add', 3),
        'Mining & Quarrying': ('mul', 'add', 3),
        'Manufacturing': ('add', None, 3),
        'Electricity, Gas and Water': ('mul', None, 3),
        'Construction': ('mul', None, 3),
        'Wholesale & Retail Trade, Restaurants & hotels': ('mul', 'mul', 3),
        'Transport, Storage & Communication': ('mul', 'mul', 3),
        'Finance, Insurance and Business services': ('mul', 'mul', 3),
        'Community, Social & Personal Services': ('mul', 'mul', 3),
        'Government Activities': ('mul', 'mul', 3),
        # 'Total Riyadh GDP': ('mul', None, 3),
    }

    # Generate predictions using the fine-tuned parameters
    prediction_years = list(range(2024, 2031))
    fine_tuned_predictions = {}
    rmse_values = {}

    for sector, params in best_params_dict.items():
        trend, seasonal, seasonal_periods = params

        # Extract the time series data for the sector
        ts = pivot_df.loc[sector].values

        # Initialize and fit the model with the best parameters
        model = ExponentialSmoothing(ts, trend=trend, seasonal=seasonal, seasonal_periods=seasonal_periods)
        fit = model.fit()

        # Forecast the GDP for the years 2024 to 2030
        forecast = fit.forecast(steps=len(prediction_years))

        # Store the predictions
        fine_tuned_predictions[sector] = forecast

    # Insert the predictions into the database
    insert_predictions_to_db(fine_tuned_predictions, rmse_values)
    print("Predictions and RMSE values inserted into the database.")
