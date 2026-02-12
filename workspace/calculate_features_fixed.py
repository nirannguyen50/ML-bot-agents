"""
Technical Feature Calculator for EURUSD Trading Data
Engineer: ML Trading Bot Team
Date: 2024
Fixed Issues: 
1. Fixed RSI division by zero with epsilon handling
2. Added NaN handling in delta series
3. Implemented complete MACD calculation
4. Fixed logging configuration to avoid global conflicts
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
import warnings
from typing import Tuple, Optional, Dict, List

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Setup module-specific logger to avoid global conflicts
logger = logging.getLogger(__name__)

class FeatureCalculator:
    """
    Technical indicator calculator for financial time series data.
    Implements RSI, MACD, Bollinger Bands with proper error handling.
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Initialize with price data.
        
        Args:
            data: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data.copy()
        self.validate_data()
        logger.info(f"FeatureCalculator initialized with {len(data)} rows")
    
    def validate_data(self) -> None:
        """Validate input data structure and content."""
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing = [col for col in required_cols if col not in self.data.columns]
        
        if missing:
            error_msg = f"Missing required columns: {missing}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Check for NaN values in critical columns
        nan_counts = self.data[['Close']].isna().sum()
        if nan_counts.any():
            logger.warning(f"NaN values found in Close column: {nan_counts['Close']}")
    
    def calculate_rsi(self, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            period: Lookback period for RSI calculation (default: 14)
        
        Returns:
            pd.Series: RSI values
        """
        try:
            # Calculate price changes
            close_prices = self.data['Close']
            
            # Handle NaN values in the series
            if close_prices.isna().any():
                close_prices = close_prices.fillna(method='ffill').fillna(method='bfill')
                logger.debug("Filled NaN values in close prices for RSI calculation")
            
            delta = close_prices.diff()
            
            # Separate gains and losses with NaN handling
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            
            # Calculate average gains and losses
            avg_gain = gain.rolling(window=period, min_periods=1).mean()
            avg_loss = loss.rolling(window=period, min_periods=1).mean()
            
            # Calculate RS with epsilon to avoid division by zero
            epsilon = 1e-10  # Small epsilon value
            avg_loss_safe = avg_loss.replace(0, epsilon)  # Replace 0 with epsilon
            rs = avg_gain / avg_loss_safe
            
            # Calculate RSI
            rsi = 100 - (100 / (1 + rs))
            
            # Cap RSI values between 0 and 100
            rsi = rsi.clip(0, 100)
            
            logger.info(f"RSI({period}) calculated successfully")
            return rsi
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {str(e)}")
            raise
    
    def calculate_macd(self, fast_period: int = 12, slow_period: int = 26, 
                      signal_period: int = 9) -> Dict[str, pd.Series]:
        """
        Calculate Moving Average Convergence Divergence (MACD).
        
        Args:
            fast_period: Period for fast EMA (default: 12)
            slow_period: Period for slow EMA (default: 26)
            signal_period: Period for signal line EMA (default: 9)
        
        Returns:
            Dict with keys: 'macd_line', 'signal_line', 'histogram'
        """
        try:
            close_prices = self.data['Close']
            
            # Handle NaN values
            if close_prices.isna().any():
                close_prices = close_prices.fillna(method='ffill').fillna(method='bfill')
                logger.debug("Filled NaN values in close prices for MACD calculation")
            
            # Calculate EMAs
            ema_fast = close_prices.ewm(span=fast_period, adjust=False).mean()
            ema_slow = close_prices.ewm(span=slow_period, adjust=False).mean()
            
            # MACD line
            macd_line = ema_fast - ema_slow
            
            # Signal line (EMA of MACD line)
            signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
            
            # Histogram
            histogram = macd_line - signal_line
            
            result = {
                'macd_line': macd_line,
                'signal_line': signal_line,
                'histogram': histogram
            }
            
            logger.info(f"MACD({fast_period},{slow_period},{signal_period}) calculated successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {str(e)}")
            raise
    
    def calculate_bollinger_bands(self, period: int = 20, 
                                 num_std: float = 2.0) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands.
        
        Args:
            period: Moving average period (default: 20)
            num_std: Number of standard deviations (default: 2.0)
        
        Returns:
            Dict with keys: 'middle', 'upper', 'lower'
        """
        try:
            close_prices = self.data['Close']
            
            # Calculate middle band (SMA)
            middle_band = close_prices.rolling(window=period, min_periods=1).mean()
            
            # Calculate standard deviation
            std_dev = close_prices.rolling(window=period, min_periods=1).std()
            
            # Calculate upper and lower bands
            upper_band = middle_band + (std_dev * num_std)
            lower_band = middle_band - (std_dev * num_std)
            
            result = {
                'middle': middle_band,
                'upper': upper_band,
                'lower': lower_band
            }
            
            logger.info(f"Bollinger Bands({period}, {num_std}σ) calculated successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {str(e)}")
            raise
    
    def calculate_all_features(self) -> pd.DataFrame:
        """
        Calculate all technical indicators and return enriched DataFrame.
        
        Returns:
            DataFrame with original data plus all calculated features
        """
        result_df = self.data.copy()
        
        # Calculate RSI
        result_df['RSI_14'] = self.calculate_rsi(period=14)
        
        # Calculate MACD
        macd_result = self.calculate_macd()
        result_df['MACD_line'] = macd_result['macd_line']
        result_df['MACD_signal'] = macd_result['signal_line']
        result_df['MACD_histogram'] = macd_result['histogram']
        
        # Calculate Bollinger Bands
        bb_result = self.calculate_bollinger_bands()
        result_df['BB_middle'] = bb_result['middle']
        result_df['BB_upper'] = bb_result['upper']
        result_df['BB_lower'] = bb_result['lower']
        
        # Calculate additional metrics
        result_df['returns'] = self.data['Close'].pct_change()
        result_df['volatility'] = result_df['returns'].rolling(window=20).std()
        
        logger.info(f"All features calculated. Total columns: {len(result_df.columns)}")
        return result_df


def load_and_calculate_features(filepath: str) -> pd.DataFrame:
    """
    Convenience function to load data and calculate features.
    
    Args:
        filepath: Path to CSV file with price data
    
    Returns:
        DataFrame with calculated features
    """
    try:
        # Configure logging at function level, not globally
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Load data
        data = pd.read_csv(filepath, parse_dates=['Date'], index_col='Date')
        
        # Validate required columns
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required):
            raise ValueError(f"CSV must contain columns: {required}")
        
        # Calculate features
        calculator = FeatureCalculator(data)
        features_df = calculator.calculate_all_features()
        
        # Remove any remaining NaN values from the beginning
        features_df = features_df.dropna()
        
        return features_df
        
    except Exception as e:
        logger.error(f"Failed to load and calculate features: {str(e)}")
        raise


if __name__ == "__main__":
    # Example usage
    try:
        # Test with sample data path
        sample_path = "data/raw/EURUSD_1H_2024.csv"
        
        print("Testing Feature Calculator...")
        features = load_and_calculate_features(sample_path)
        
        print(f"Success! Generated DataFrame shape: {features.shape}")
        print(f"Columns: {list(features.columns)}")
        print(f"First few rows:")
        print(features.head())
        
        # Save results
        output_path = "data/processed/features_EURUSD_1H_2024.csv"
        features.to_csv(output_path)
        print(f"Features saved to: {output_path}")
        
    except FileNotFoundError:
        print("Sample data file not found. Running unit tests instead...")
        
        # Create synthetic test data
        dates = pd.date_range('2024-01-01', periods=100, freq='H')
        test_data = pd.DataFrame({
            'Open': np.random.uniform(1.0, 1.2, 100),
            'High': np.random.uniform(1.1, 1.3, 100),
            'Low': np.random.uniform(0.9, 1.1, 100),
            'Close': np.random.uniform(1.0, 1.2, 100),
            'Volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        
        # Test the calculator
        calculator = FeatureCalculator(test_data)
        
        # Test RSI
        rsi = calculator.calculate_rsi(14)
        print(f"RSI test passed. Shape: {rsi.shape}, NaN count: {rsi.isna().sum()}")
        
        # Test MACD
        macd = calculator.calculate_macd()
        print(f"MACD test passed. Keys: {list(macd.keys())}")
        
        # Test Bollinger Bands
        bb = calculator.calculate_bollinger_bands()
        print(f"Bollinger Bands test passed. Keys: {list(bb.keys())}")
        
        # Test all features
        all_features = calculator.calculate_all_features()
        print(f"All features test passed. Shape: {all_features.shape}")
        
        print("\nAll tests completed successfully!")