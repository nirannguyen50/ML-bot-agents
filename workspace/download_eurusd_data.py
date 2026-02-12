import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_eurusd_data(start_date="2020-01-01", end_date=None, interval="1d"):
    """Download EUR/USD historical data from Yahoo Finance"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    symbol = "EURUSD=X"
    logger.info(f"Downloading {symbol} from {start_date} to {end_date} with interval {interval}")
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval=interval)
        
        if df.empty:
            logger.error("No data downloaded")
            return None
        
        # Rename columns to match our feature calculator
        df.columns = [col.lower() for col in df.columns]
        # Ensure 'close' column exists (yfinance uses 'close' not 'close')
        if 'close' in df.columns and 'close' not in df.columns:
            df = df.rename(columns={'close': 'close'})
        
        # Add date column if index is datetime
        df.reset_index(inplace=True)
        if 'Date' not in df.columns and 'Datetime' in df.columns:
            df.rename(columns={'Datetime': 'Date'}, inplace=True)
        
        logger.info(f"Downloaded {len(df)} rows of data")
        return df
    except Exception as e:
        logger.error(f"Error downloading data: {e}")
        return None

def save_raw_data(df, filepath="data/raw/eurusd_raw.csv"):
    """Save raw data to CSV"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False)
    logger.info(f"Raw data saved to {filepath}")
    return filepath

if __name__ == "__main__":
    # Download last 2 years of daily data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2 years
    df = download_eurusd_data(start_date=start_date.strftime("%Y-%m-%d"), 
                              end_date=end_date.strftime("%Y-%m-%d"),
                              interval="1d")
    if df is not None:
        saved_path = save_raw_data(df)
        print(f"Data saved to {saved_path}")
        print(df.head())
        print(f"Data shape: {df.shape}")