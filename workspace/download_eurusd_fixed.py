import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

def download_eurusd_data():
    """Download 6 months of EURUSD daily OHLCV data"""
    print("Starting EURUSD data download...")
    
    # Calculate date range: last 6 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    # Download data
    ticker = "EURUSD=X"
    print(f"Downloading {ticker} from {start_date.date()} to {end_date.date()}")
    
    try:
        data = yf.download(ticker, start=start_date, end=end_date, interval="1d")
        
        if data.empty:
            print("ERROR: No data downloaded!")
            return False
            
        print(f"Downloaded {len(data)} rows of data")
        print(f"Date range: {data.index.min()} to {data.index.max()}")
        
        # Reset index to make Date a column
        data = data.reset_index()
        
        # Rename columns to match requirements
        data = data.rename(columns={
            'Date': 'Date',
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'Adj Close': 'Adj Close',
            'Volume': 'Volume'
        })
        
        # Select required columns
        required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        data = data[required_cols]
        
        # Save to CSV
        output_path = "workspace/eurusd_data.csv"
        data.to_csv(output_path, index=False)
        print(f"Data saved to {output_path}")
        
        # Calculate basic statistics
        print("\n=== BASIC STATISTICS ===")
        stats = data[['Open', 'High', 'Low', 'Close']].describe()
        print(stats)
        
        # Additional statistics
        print("\n=== DETAILED STATISTICS ===")
        for col in ['Open', 'High', 'Low', 'Close']:
            print(f"\n{col}:")
            print(f"  Mean:   {data[col].mean():.5f}")
            print(f"  Std:    {data[col].std():.5f}")
            print(f"  Min:    {data[col].min():.5f}")
            print(f"  Max:    {data[col].max():.5f}")
            print(f"  Range:  {data[col].max() - data[col].min():.5f}")
        
        print(f"\nVolume Statistics:")
        print(f"  Total Volume: {data['Volume'].sum():,.0f}")
        print(f"  Mean Volume:  {data['Volume'].mean():,.0f}")
        print(f"  Max Volume:   {data['Volume'].max():,.0f}")
        
        return True
        
    except Exception as e:
        print(f"ERROR during download: {e}")
        return False

if __name__ == "__main__":
    success = download_eurusd_data()
    if success:
        print("\n✓ Data download completed successfully!")
    else:
        print("\n✗ Data download failed!")