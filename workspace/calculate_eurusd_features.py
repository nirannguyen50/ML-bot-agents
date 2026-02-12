import pandas as pd
import numpy as np
from datetime import datetime
import logging
import warnings
import sys
import os
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/feature_calculation_eurusd.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_data_quality_checks(df: pd.DataFrame) -> pd.DataFrame:
    """Perform data quality checks and handle missing values"""
    logger.info("Starting data quality checks...")
    
    original_shape = df.shape
    logger.info(f"Original data shape: {original_shape}")
    
    # Check for missing values
    missing_counts = df.isnull().sum()
    missing_pct = (missing_counts / len(df)) * 100
    
    logger.info("Missing values per column:")
    for col in df.columns:
        if missing_counts[col] > 0:
            logger.warning(f"  {col}: {missing_counts[col]} missing ({missing_pct[col]:.2f}%)")
    
    # Handle missing values in price columns
    price_cols = ['open', 'high', 'low', 'close']
    for col in price_cols:
        if col in df.columns:
            # Forward fill then backward fill for price data
            df[col] = df[col].ffill().bfill()
            logger.info(f"  Applied forward/backward fill to {col}")
    
    # Handle missing volume (if exists)
    if 'volume' in df.columns:
        df['volume'] = df['volume'].fillna(0)
        logger.info("  Filled missing Volume with 0")
    
    # Remove rows where essential data is still missing
    essential_cols = ['close']
    df_clean = df.dropna(subset=essential_cols)
    
    rows_removed = original_shape[0] - df_clean.shape[0]
    if rows_removed > 0:
        logger.warning(f"Removed {rows_removed} rows with missing essential data")
    
    logger.info(f"Clean data shape: {df_clean.shape}")
    return df_clean

def calculate_sma_optimized(data: pd.Series, window: int) -> pd.Series:
    """Optimized SMA calculation using rolling mean"""
    return data.rolling(window=window, min_periods=max(1, window//2)).mean()

def calculate_rsi_optimized(data: pd.Series, window: int = 14) -> pd.Series:
    """Optimized RSI calculation using vectorized operations"""
    delta = data.diff()
    
    # Vectorized gain/loss calculation
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Use EMA for smoother RSI
    avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Clip values to 0-100 range
    rsi = rsi.clip(0, 100)
    
    return rsi

def calculate_macd_optimized(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    """Optimized MACD calculation"""
    exp1 = data.ewm(span=fast, adjust=False).mean()
    exp2 = data.ewm(span=slow, adjust=False).mean()
    
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(data: pd.Series, window: int = 20, num_std: float = 2.0) -> tuple:
    """Calculate Bollinger Bands"""
    sma = data.rolling(window=window, min_periods=window//2).mean()
    std = data.rolling(window=window, min_periods=window//2).std()
    
    upper_band = sma + (std * num_std)
    lower_band = sma - (std * num_std)
    
    return upper_band, sma, lower_band

def calculate_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window, min_periods=window//2).mean()
    
    return atr

def calculate_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate technical features for the given DataFrame.
    Assumes df has columns: 'date', 'open', 'high', 'low', 'close', 'volume'
    """
    logger.info("Calculating technical indicators...")
    
    # Ensure date is datetime and sort
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
    
    # Data quality checks
    df = setup_data_quality_checks(df)
    
    if len(df) == 0:
        logger.error("No valid data after quality checks")
        return df
    
    close_series = df['close']
    
    # Moving Averages
    df['sma_20'] = calculate_sma_optimized(close_series, 20)
    df['sma_50'] = calculate_sma_optimized(close_series, 50)
    df['ema_12'] = close_series.ewm(span=12, adjust=False).mean()
    df['ema_26'] = close_series.ewm(span=26, adjust=False).mean()
    
    # RSI
    df['rsi_14'] = calculate_rsi_optimized(close_series, 14)
    
    # MACD
    macd_line, signal_line, histogram = calculate_macd_optimized(close_series)
    df['macd_line'] = macd_line
    df['macd_signal'] = signal_line
    df['macd_histogram'] = histogram
    
    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(close_series, 20, 2.0)
    df['bb_upper'] = bb_upper
    df['bb_middle'] = bb_middle
    df['bb_lower'] = bb_lower
    df['bb_width'] = (bb_upper - bb_lower) / bb_middle
    df['bb_position'] = (close_series - bb_lower) / (bb_upper - bb_lower)
    
    # ATR
    if all(col in df.columns for col in ['high', 'low']):
        df['atr_14'] = calculate_atr(df, 14)
    
    # Returns and volatility
    df['returns'] = close_series.pct_change()
    df['log_returns'] = np.log(close_series / close_series.shift(1))
    df['volatility_20'] = df['returns'].rolling(window=20, min_periods=10).std() * np.sqrt(252)
    
    if 'volume' in df.columns:
        df['volume_ma_20'] = df['volume'].rolling(window=20, min_periods=10).mean()
    
    # SMA crossover features
    df['sma_crossover_signal'] = np.where(df['sma_20'] > df['sma_50'], 1, -1)
    df['price_vs_sma20_pct'] = (close_series - df['sma_20']) / df['sma_20'] * 100
    df['price_vs_sma50_pct'] = (close_series - df['sma_50']) / df['sma_50'] * 100
    
    # Momentum
    df['momentum_10'] = close_series.pct_change(10)
    df['roc_10'] = ((close_series - close_series.shift(10)) / close_series.shift(10)) * 100
    
    # Additional features for ML
    df['sma_ratio'] = df['sma_20'] / df['sma_50']
    df['ema_ratio'] = df['ema_12'] / df['ema_26']
    df['macd_diff'] = df['macd_line'] - df['macd_signal']
    
    logger.info(f"Calculated {len(df.columns)} features in total")
    return df

def main():
    """Main function to calculate features for EURUSD data"""
    raw_data_path = "data/raw/eurusd_raw.csv"
    output_path = "workspace/eurusd_features.csv"
    
    if not os.path.exists(raw_data_path):
        logger.error(f"Raw data file not found: {raw_data_path}")
        print("Please run download_eurusd_data.py first.")
        return
    
    logger.info(f"Loading raw data from {raw_data_path}")
    df = pd.read_csv(raw_data_path)
    
    logger.info(f"Raw data shape: {df.shape}")
    logger.info(f"Columns: {list(df.columns)}")
    
    features_df = calculate_features(df)
    
    if len(features_df) == 0:
        logger.error("Feature calculation failed.")
        return
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    features_df.to_csv(output_path, index=False)
    logger.info(f"Features saved to {output_path}")
    
    # Print summary
    print("\n=== FEATURE CALCULATION SUMMARY ===")
    print(f"Total rows: {len(features_df)}")
    print(f"Date range: {features_df['date'].min()} to {features_df['date'].max()}")
    print(f"Total features: {len(features_df.columns)}")
    
    # Show first few rows
    print("\nFirst 5 rows of features:")
    print(features_df[['date', 'close', 'sma_20', 'sma_50', 'sma_crossover_signal', 'rsi_14']].head())
    
    # Check for missing values
    missing = features_df.isnull().sum().sum()
    print(f"Total missing values in features: {missing}")
    
    return features_df

if __name__ == "__main__":
    main()