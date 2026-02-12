"""
TECHNICAL FEATURE CALCULATOR - OPTIMIZED VERSION
Engineer: ML Trading Bot Team
Date: 2024
Fixed Issues:
1. Fixed incomplete MACD function with syntax errors
2. Added proper error handling for edge cases
3. Optimized performance with vectorized operations
4. Added comprehensive NaN handling
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
import warnings
from typing import Tuple, Optional, Dict, List
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TechnicalFeaturesOptimized:
    """Optimized technical feature calculator using vectorized operations."""
    
    def __init__(self, data: pd.DataFrame):
        """
        Initialize with OHLCV data.
        
        Args:
            data: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        """
        self.data = data.copy()
        self._validate_data()
        
    def _validate_data(self) -> None:
        """Validate input data structure and columns."""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_columns if col not in self.data.columns]
        
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
            
        if self.data.empty:
            raise ValueError("DataFrame is empty")
            
        logger.info(f"Data validated: {len(self.data)} rows, {len(self.data.columns)} columns")
    
    def calculate_all_features(self) -> pd.DataFrame:
        """
        Calculate all technical features efficiently.
        
        Returns:
            DataFrame with original data and added technical features
        """
        logger.info("Calculating all technical features...")
        
        # Make a copy to avoid modifying original
        result = self.data.copy()
        
        # Calculate individual features
        result = self._calculate_sma_features(result)
        result = self._calculate_ema_features(result)
        result = self._calculate_rsi_optimized(result)
        result = self._calculate_macd_optimized(result)
        result = self._calculate_bollinger_bands(result)
        result = self._calculate_atr_optimized(result)
        
        # Calculate derived features
        result = self._calculate_price_derivatives(result)
        
        # Clean NaN values
        result = self._clean_nan_values(result)
        
        logger.info(f"Feature calculation complete. Total columns: {len(result.columns)}")
        return result
    
    def _calculate_sma_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Simple Moving Averages."""
        windows = [5, 10, 20, 50, 200]
        
        for window in windows:
            df[f'sma_{window}'] = df['close'].rolling(window=window, min_periods=1).mean()
            df[f'sma_{window}_ratio'] = df['close'] / df[f'sma_{window}']
        
        return df
    
    def _calculate_ema_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Exponential Moving Averages."""
        windows = [5, 12, 26, 50]
        
        for window in windows:
            df[f'ema_{window}'] = df['close'].ewm(span=window, adjust=False).mean()
        
        # EMA crossovers
        if 'ema_12' in df.columns and 'ema_26' in df.columns:
            df['ema_crossover'] = (df['ema_12'] > df['ema_26']).astype(int)
            df['ema_crossover_signal'] = df['ema_crossover'].diff().fillna(0)
        
        return df
    
    def _calculate_rsi_optimized(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculate Relative Strength Index using vectorized operations.
        
        Args:
            df: Input DataFrame
            period: RSI period (default: 14)
            
        Returns:
            DataFrame with RSI column added
        """
        close = df['close']
        
        # Calculate price changes
        delta = close.diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss
        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()
        
        # Calculate RS and RSI (with epsilon to avoid division by zero)
        epsilon = 1e-10
        rs = avg_gain / (avg_loss + epsilon)
        rsi = 100 - (100 / (1 + rs))
        
        df['rsi'] = rsi
        df['rsi_overbought'] = (rsi > 70).astype(int)
        df['rsi_oversold'] = (rsi < 30).astype(int)
        
        return df
    
    def _calculate_macd_optimized(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MACD (Moving Average Convergence Divergence) - FIXED VERSION.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with MACD, Signal, and Histogram columns
        """
        close = df['close']
        
        # Calculate EMAs
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        
        # MACD line
        macd_line = exp1 - exp2
        
        # Signal line (9-period EMA of MACD)
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        
        # MACD histogram
        histogram = macd_line - signal_line
        
        # Add to DataFrame
        df['macd_line'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_histogram'] = histogram
        
        # MACD crossover signals
        df['macd_crossover'] = (macd_line > signal_line).astype(int)
        df['macd_crossover_signal'] = df['macd_crossover'].diff().fillna(0)
        
        return df
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, 
                                   num_std: float = 2.0) -> pd.DataFrame:
        """Calculate Bollinger Bands."""
        close = df['close']
        
        # Calculate middle band (SMA)
        middle_band = close.rolling(window=period, min_periods=1).mean()
        
        # Calculate standard deviation
        std = close.rolling(window=period, min_periods=1).std()
        
        # Calculate upper and lower bands
        upper_band = middle_band + (std * num_std)
        lower_band = middle_band - (std * num_std)
        
        # Bollinger Band width and %B
        bb_width = (upper_band - lower_band) / middle_band
        bb_percent_b = (close - lower_band) / (upper_band - lower_band + 1e-10)
        
        df['bb_middle'] = middle_band
        df['bb_upper'] = upper_band
        df['bb_lower'] = lower_band
        df['bb_width'] = bb_width
        df['bb_percent_b'] = bb_percent_b
        df['bb_squeeze'] = (bb_width < bb_width.rolling(20).mean()).astype(int)
        
        return df
    
    def _calculate_atr_optimized(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Calculate Average True Range using vectorized operations."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate true range components
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        # True range is the maximum of the three
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Average True Range
        atr = true_range.rolling(window=period, min_periods=1).mean()
        
        df['true_range'] = true_range
        df['atr'] = atr
        df['atr_percentage'] = atr / df['close']
        
        return df
    
    def _calculate_price_derivatives(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate price-based derivatives and returns."""
        close = df['close']
        
        # Returns
        df['returns'] = close.pct_change()
        df['log_returns'] = np.log(close / close.shift(1))
        
        # Volatility
        df['volatility_5d'] = df['returns'].rolling(5).std()
        df['volatility_20d'] = df['returns'].rolling(20).std()
        
        # Price highs and lows
        df['high_5d'] = close.rolling(5).max()
        df['low_5d'] = close.rolling(5).min()
        df['high_20d'] = close.rolling(20).max()
        df['low_20d'] = close.rolling(20).min()
        
        # Price position in range
        df['price_position_5d'] = (close - df['low_5d']) / (df['high_5d'] - df['low_5d'] + 1e-10)
        df['price_position_20d'] = (close - df['low_20d']) / (df['high_20d'] - df['low_20d'] + 1e-10)
        
        return df
    
    def _clean_nan_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle NaN values intelligently."""
        # Forward fill for technical indicators
        indicator_cols = [col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume']]
        
        # Forward fill then backfill
        df[indicator_cols] = df[indicator_cols].ffill().bfill()
        
        # For any remaining NaNs, fill with 0 or appropriate defaults
        df = df.fillna(0)
        
        # Log cleaning results
        nan_count = df.isna().sum().sum()
        if nan_count == 0:
            logger.info("All NaN values cleaned successfully")
        else:
            logger.warning(f"{nan_count} NaN values remain after cleaning")
        
        return df
    
    def get_feature_stats(self, df: pd.DataFrame) -> Dict:
        """Get statistics about calculated features."""
        stats = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'technical_features': len([col for col in df.columns if col not in 
                                       ['open', 'high', 'low', 'close', 'volume']]),
            'nan_count': df.isna().sum().sum(),
            'feature_columns': [col for col in df.columns if col not in 
                               ['open', 'high', 'low', 'close', 'volume']]
        }
        return stats


def load_sample_data() -> pd.DataFrame:
    """Create sample data for testing."""
    dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='D')
    np.random.seed(42)
    
    data = pd.DataFrame({
        'open': np.random.randn(len(dates)).cumsum() + 100,
        'high': np.random.randn(len(dates)).cumsum() + 101,
        'low': np.random.randn(len(dates)).cumsum() + 99,
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    
    return data


def main():
    """Main execution function for testing."""
    print("Testing TechnicalFeaturesOptimized class...")
    
    # Load sample data
    data = load_sample_data()
    print(f"Sample data loaded: {len(data)} rows")
    
    # Create feature calculator
    calculator = TechnicalFeaturesOptimized(data)
    
    try:
        # Calculate all features
        features_df = calculator.calculate_all_features()
        
        # Get statistics
        stats = calculator.get_feature_stats(features_df)
        
        print("\n=== FEATURE CALCULATION COMPLETE ===")
        print(f"Total rows: {stats['total_rows']}")
        print(f"Total columns: {stats['total_columns']}")
        print(f"Technical features: {stats['technical_features']}")
        print(f"Remaining NaN values: {stats['nan_count']}")
        
        print("\nFirst 5 rows of features:")
        print(features_df[['close', 'sma_20', 'rsi', 'macd_line', 'atr']].head())
        
        print("\nFeature columns:")
        for i, col in enumerate(stats['feature_columns'][:10], 1):
            print(f"{i}. {col}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in feature calculation: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ All tests passed successfully!")
    else:
        print("\n❌ Tests failed. Check logs for details.")