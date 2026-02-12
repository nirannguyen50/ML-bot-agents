import pandas as pd
import numpy as np
from datetime import datetime
import logging
import warnings
from typing import Tuple, Optional
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/feature_calculation.log'),
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
    price_cols = ['Open', 'High', 'Low', 'Close']
    for col in price_cols:
        if col in df.columns:
            # Forward fill then backward fill for price data
            df[col] = df[col].ffill().bfill()
            logger.info(f"  Applied forward/backward fill to {col}")
    
    # Handle missing volume (if exists)
    if 'Volume' in df.columns:
        df['Volume'] = df['Volume'].fillna(0)
        logger.info("  Filled missing Volume with 0")
    
    # Remove rows where essential data is still missing
    essential_cols = ['Close']
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

def calculate_macd_optimized(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Optimized MACD calculation"""
    exp1 = data.ewm(span=fast, adjust=False).mean()
    exp2 = data.ewm(span=slow, adjust=False).mean()
    
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(data: pd.Series, window: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands"""
    sma = data.rolling(window=window, min_periods=window//2).mean()
    std = data.rolling(window=window, min_periods=window//2).std()
    
    upper_band = sma + (std * num_std)
    lower_band = sma - (std * num_std)
    
    return upper_band, sma, lower_band

def calculate_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high = df['High']
    low = df['Low']
    close = df['Close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window, min_periods=window//2).mean()
    
    return atr

def calculate_features_optimized(input_file: str, output_file: str, 
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Optimized feature calculation with logging and data quality checks
    
    Parameters:
    -----------
    input_file : str
        Path to input CSV file
    output_file : str
        Path to output CSV file with features
    start_date : str, optional
        Start date for filtering data (format: YYYY-MM-DD)
    end_date : str, optional
        End date for filtering data (format: YYYY-MM-DD)
    """
    
    logger.info(f"Starting feature calculation from: {input_file}")
    start_time = datetime.now()
    
    try:
        # Read the CSV file
        logger.info(f"Reading data from {input_file}")
        df = pd.read_csv(input_file)
        
        logger.info(f"Data loaded successfully. Shape: {df.shape}")
        logger.info(f"Columns: {list(df.columns)}")
        
        # Ensure Date column is datetime
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            logger.info(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
            
            # Filter by date range if specified
            if start_date:
                start_date_dt = pd.to_datetime(start_date)
                df = df[df['Date'] >= start_date_dt]
                logger.info(f"Filtered data from {start_date}")
            
            if end_date:
                end_date_dt = pd.to_datetime(end_date)
                df = df[df['Date'] <= end_date_dt]
                logger.info(f"Filtered data to {end_date}")
        
        # Sort by date
        df = df.sort_values('Date').reset_index(drop=True)
        
        # Data quality checks and missing value handling
        df = setup_data_quality_checks(df)
        
        if len(df) == 0:
            logger.error("No valid data after quality checks")
            raise ValueError("No valid data available for feature calculation")
        
        # Calculate technical indicators
        logger.info("Calculating technical indicators...")
        
        # Price-based features
        close_series = df['Close']
        
        # Moving Averages
        df['SMA_20'] = calculate_sma_optimized(close_series, 20)
        df['SMA_50'] = calculate_sma_optimized(close_series, 50)
        df['EMA_12'] = close_series.ewm(span=12, adjust=False).mean()
        df['EMA_26'] = close_series.ewm(span=26, adjust=False).mean()
        
        # RSI
        df['RSI_14'] = calculate_rsi_optimized(close_series, 14)
        
        # MACD
        macd_line, signal_line, histogram = calculate_macd_optimized(close_series)
        df['MACD_line'] = macd_line
        df['MACD_signal'] = signal_line
        df['MACD_histogram'] = histogram
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(close_series, 20, 2.0)
        df['BB_upper'] = bb_upper
        df['BB_middle'] = bb_middle
        df['BB_lower'] = bb_lower
        df['BB_width'] = (bb_upper - bb_lower) / bb_middle
        df['BB_position'] = (close_series - bb_lower) / (bb_upper - bb_lower)
        
        # ATR (if High and Low available)
        if all(col in df.columns for col in ['High', 'Low']):
            df['ATR_14'] = calculate_atr(df, 14)
            logger.info("ATR calculated successfully")
        
        # Statistical features
        df['Returns'] = close_series.pct_change()
        df['Log_Returns'] = np.log(close_series / close_series.shift(1))
        
        # Rolling statistics
        df['Volatility_20'] = df['Returns'].rolling(window=20, min_periods=10).std() * np.sqrt(252)
        df['Volume_MA_20'] = df['Volume'].rolling(window=20, min_periods=10).mean() if 'Volume' in df.columns else np.nan
        
        # Derived features
        df['SMA_crossover'] = np.where(df['SMA_20'] > df['SMA_50'], 1, -1)
        df['Price_vs_SMA20_pct'] = (close_series - df['SMA_20']) / df['SMA_20'] * 100
        df['Price_vs_SMA50_pct'] = (close_series - df['SMA_50']) / df['SMA_50'] * 100
        
        # Momentum indicators
        df['Momentum_10'] = close_series.pct_change(10)
        df['ROC_10'] = ((close_series - close_series.shift(10)) / close_series.shift(10)) * 100
        
        # Add metadata
        df['Feature_Calculated_At'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df['Feature_Version'] = '2.0.0'
        
        # Save to CSV
        logger.info(f"Saving features to: {output_file}")
        df.to_csv(output_file, index=False)
        
        # Performance metrics
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Generate summary report
        logger.info("\n" + "="*60)
        logger.info("FEATURE CALCULATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total rows processed: {len(df):,}")
        logger.info(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
        logger.info(f"Processing time: {processing_time:.2f} seconds")
        logger.info(f"Rows per second: {len(df)/processing_time:.0f}")
        
        feature_cols = [col for col in df.columns if col not in 
                       ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 
                        'Feature_Calculated_At', 'Feature_Version']]
        logger.info(f"Total features calculated: {len(feature_cols)}")
        
        logger.info("\nFeature quality report:")
        for col in feature_cols[:10]:  # Show first 10 features
            non_null = df[col].notna().sum()
            null_pct = (df[col].isna().sum() / len(df)) * 100
            status = "✓" if null_pct < 5 else "⚠" if null_pct < 20 else "✗"
            logger.info(f"  {status} {col}: {non_null:,} non-null ({null_pct:.1f}% null)")
        
        if len(feature_cols) > 10:
            logger.info(f"  ... and {len(feature_cols) - 10} more features")
        
        logger.info(f"\nOutput file size: {output_file}")
        
        # Save summary statistics
        summary_stats = df[feature_cols].describe().T
        summary_file = output_file.replace('.csv', '_summary.csv')
        summary_stats.to_csv(summary_file)
        logger.info(f"Summary statistics saved to: {summary_file}")
        
        logger.info("="*60)
        logger.info("Feature calculation completed successfully!")
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculating features: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    # Define file paths
    input_file = "data/raw/eurusd_1h.csv"
    output_file = "workspace/eurusd_features_optimized.csv"
    
    # Calculate features with date filtering example
    features_df = calculate_features_optimized(
        input_file=input_file,
        output_file=output_file,
        start_date="2024-01-01",
        end_date="2024-12-31"
    )