"""
Data Pipeline Extension: Download Multiple Forex Pairs
Data Scientist: ML Trading Bot Team
Date: 2024

Downloads historical data for multiple forex pairs from Yahoo Finance.
Saves raw data to data/raw/ directory.
"""

import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta
import logging
from typing import List, Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ForexDataDownloader:
    """Downloader for multiple forex pairs from Yahoo Finance."""
    
    def __init__(self, data_dir: str = "data/raw"):
        """
        Initialize downloader with data directory.
        
        Args:
            data_dir: Directory to save raw data files
        """
        self.data_dir = data_dir
        self._ensure_data_directory()
        
    def _ensure_data_directory(self) -> None:
        """Ensure data directory exists."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"Created data directory: {self.data_dir}")
    
    def get_yahoo_symbol(self, forex_pair: str) -> str:
        """
        Convert forex pair to Yahoo Finance symbol.
        
        Args:
            forex_pair: Forex pair like 'GBP/USD', 'USD/JPY', 'AUD/USD'
            
        Returns:
            Yahoo Finance symbol like 'GBPUSD=X'
        """
        # Remove slash and add =X suffix for Yahoo Finance forex
        symbol = forex_pair.replace("/", "") + "=X"
        return symbol
    
    def download_forex_data(self, forex_pairs: List[str], 
                           start_date: str = "2023-01-01",
                           end_date: str = None,
                           interval: str = "1d") -> Dict[str, pd.DataFrame]:
        """
        Download historical data for multiple forex pairs.
        
        Args:
            forex_pairs: List of forex pairs like ['GBP/USD', 'USD/JPY', 'AUD/USD']
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format (default: today)
            interval: Data interval ('1d', '1h', '1wk', '1mo')
            
        Returns:
            Dictionary with forex pair as key and DataFrame as value
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        results = {}
        
        for forex_pair in forex_pairs:
            try:
                symbol = self.get_yahoo_symbol(forex_pair)
                logger.info(f"Downloading {forex_pair} ({symbol}) from {start_date} to {end_date}")
                
                # Download data
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start_date, end=end_date, interval=interval)
                
                if df.empty:
                    logger.warning(f"No data downloaded for {forex_pair}")
                    continue
                
                # Add forex pair as column for identification
                df['forex_pair'] = forex_pair
                df['symbol'] = symbol
                
                # Ensure OHLCV columns are lowercase
                df.columns = [col.lower() for col in df.columns]
                
                # Rename columns if needed (yfinance uses 'close' not 'close')
                if 'close' in df.columns and 'close' not in df.columns:
                    df = df.rename(columns={'close': 'close'})
                
                results[forex_pair] = df
                logger.info(f"Downloaded {len(df)} rows for {forex_pair}")
                
            except Exception as e:
                logger.error(f"Error downloading {forex_pair}: {str(e)}")
        
        return results
    
    def save_raw_data(self, data_dict: Dict[str, pd.DataFrame]) -> None:
        """
        Save raw data to CSV files in data/raw/ directory.
        
        Args:
            data_dict: Dictionary with forex pair as key and DataFrame as value
        """
        saved_files = []
        
        for forex_pair, df in data_dict.items():
            try:
                # Create filename
                filename = f"{forex_pair.replace('/', '_')}_raw.csv"
                filepath = os.path.join(self.data_dir, filename)
                
                # Save to CSV
                df.to_csv(filepath)
                saved_files.append(filepath)
                
                logger.info(f"Saved raw data for {forex_pair} to {filepath} ({len(df)} rows)")
                
            except Exception as e:
                logger.error(f"Error saving data for {forex_pair}: {str(e)}")
        
        return saved_files
    
    def load_raw_data(self, forex_pair: str) -> pd.DataFrame:
        """
        Load raw data from CSV file.
        
        Args:
            forex_pair: Forex pair like 'GBP/USD'
            
        Returns:
            DataFrame with loaded data
        """
        filename = f"{forex_pair.replace('/', '_')}_raw.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Raw data file not found: {filepath}")
        
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        logger.info(f"Loaded raw data for {forex_pair} from {filepath} ({len(df)} rows)")
        
        return df


def main():
    """Main execution function."""
    print("=== Forex Data Pipeline Extension ===")
    print("Downloading data for 3 major forex pairs...")
    
    # Define forex pairs to download
    forex_pairs = ['GBP/USD', 'USD/JPY', 'AUD/USD']
    
    # Create downloader instance
    downloader = ForexDataDownloader(data_dir="data/raw")
    
    # Download data for all pairs (last 6 months for efficiency)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    
    print(f"\nDownloading data from {start_date} to {end_date}")
    
    data_dict = downloader.download_forex_data(
        forex_pairs=forex_pairs,
        start_date=start_date,
        end_date=end_date,
        interval="1d"
    )
    
    # Save raw data
    if data_dict:
        saved_files = downloader.save_raw_data(data_dict)
        
        print("\n=== DOWNLOAD SUMMARY ===")
        print(f"Total pairs attempted: {len(forex_pairs)}")
        print(f"Successfully downloaded: {len(data_dict)}")
        
        for forex_pair, df in data_dict.items():
            print(f"\n{forex_pair}:")
            print(f"  Rows: {len(df)}")
            print(f"  Date range: {df.index[0].date()} to {df.index[-1].date()}")
            print(f"  Columns: {list(df.columns)}")
            print(f"  Close price sample: {df['close'].iloc[-1]:.5f}")
            
        print(f"\nRaw data saved to: {saved_files}")
        return True
    else:
        print("No data downloaded. Check internet connection or symbols.")
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Forex data download completed successfully!")
    else:
        print("\n❌ Forex data download failed.")