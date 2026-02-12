import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

# Calculate date range: last 6 months from today
end_date = datetime.now()
start_date = end_date - timedelta(days=180)

print(f"Downloading EURUSD data from {start_date.date()} to {end_date.date()}...")

# Download data
ticker = "EURUSD=X"
data = yf.download(ticker, start=start_date, end=end_date, interval="1d")

# Check if data was downloaded
if data.empty:
    print("ERROR: No data downloaded. Check ticker symbol or internet connection.")
    exit(1)

# Reset index to get Date as column
data = data.reset_index()

# Rename columns to match required format
data.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']

# Select required columns (excluding Adj Close)
data = data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

# Save to CSV
output_path = "workspace/eurusd_data.csv"
data.to_csv(output_path, index=False)
print(f"Data saved to {output_path}")
print(f"Shape: {data.shape}")
print(f"Date range: {data['Date'].min()} to {data['Date'].max()}")

# Calculate basic statistics
print("\n=== BASIC STATISTICS ===")
numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
stats = data[numeric_cols].agg(['mean', 'std', 'min', 'max'])

# Round for readability
stats = stats.round(5)

print(stats)

# Display additional info
print(f"\n=== ADDITIONAL INFO ===")
print(f"Total trading days: {len(data)}")
print(f"Missing values: {data.isnull().sum().sum()}")

# Save statistics to file for reference
stats_path = "workspace/eurusd_stats.txt"
with open(stats_path, 'w') as f:
    f.write(f"EURUSD Statistics Report\n")
    f.write(f"Period: {start_date.date()} to {end_date.date()}\n")
    f.write(f"Total records: {len(data)}\n\n")
    f.write(stats.to_string())
print(f"Statistics saved to {stats_path}")