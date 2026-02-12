"""
Technical Feature Calculator for EURUSD Trading Data
Engineer: ML Trading Bot Team
Date: 2024
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Dict, Optional
import logging
import warnings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')


class TechnicalIndicators:
    """Class for calculating technical indicators with proper error handling"""
    
    @staticmethod
    def calculate_sma(data: pd.DataFrame, window: int, price_col: str = 'Close') -> pd.Series:
        """
        Calculate Simple Moving Average with proper window validation
        
        Parameters:
        -----------
        data : pd.DataFrame
            Input dataframe with price data
        window : int
            SMA window size
        price_col : str
            Name of price column
        
        Returns:
        --------
        pd.Series: SMA values
        """
        if len(data) < window:
            logger.warning(f"Insufficient data for SMA{window}. Have {len(data)} rows, need {window}")
            # Return NaN series with same index
            return pd.Series([np.nan] * len(data), index=data.index)
        
        # Use min_periods=window to ensure proper calculation
        return data[price_col].rolling(window=window, min_periods=window).mean()
    
    @staticmethod
    def calculate_rsi(data: pd.DataFrame, window: int = 14, price_col: str = 'Close') -> pd.Series:
        """
        Calculate Relative Strength Index with NaN handling
        
        Parameters:
        -----------
        data : pd.DataFrame
            Input dataframe with price data
        window : int
            RSI window size
        price_col : str
            Name of price column
        
        Returns:
        --------
        pd.Series: RSI values
        """
        if len(data) < window + 1:
            logger.warning(f"Insufficient data for RSI{window}. Need at least {window + 1} rows")
            return pd.Series([np.nan] * len(data), index=data.index)
        
        delta = data[price_col].diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss
        avg_gain = gain.rolling(window=window, min_periods=window).mean()
        avg_loss = loss.rolling(window=window, min_periods=window).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        data: pd.DataFrame, 
        fast: int = 12, 
        slow: int = 26, 
        signal: int = 9,
        price_col: str = 'Close'
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD indicator with proper initialization
        
        Parameters:
        -----------
        data : pd.DataFrame
            Input dataframe with price data
        fast : int
            Fast EMA period
        slow : int
            Slow EMA period
        signal : int
            Signal line period
        price_col : str
            Name of price column
        
        Returns:
        --------
        Tuple[pd.Series, pd.Series, pd.Series]: MACD line, signal line, histogram
        """
        # Ensure enough data for slowest EMA
        max_period = max(fast, slow, signal)
        if len(data) < max_period:
            logger.warning(f"Insufficient data for MACD. Need at least {max_period} rows")
            nan_series = pd.Series([np.nan] * len(data), index=data.index)
            return nan_series, nan_series, nan_series
        
        # Calculate EMAs
        exp_fast = data[price_col].ewm(span=fast, adjust=False, min_periods=fast).mean()
        exp_slow = data[price_col].ewm(span=slow, adjust=False, min_periods=slow).mean()
        
        # MACD line
        macd_line = exp_fast - exp_slow
        
        # Signal line
        signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
        
        # Histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram


def validate_dataframe(df: pd.DataFrame, required_columns: list) -> Tuple[bool, str]:
    """
    Validate dataframe structure and required columns
    
    Parameters:
    -----------
    df : pd.DataFrame
        Dataframe to validate
    required_columns : list
        List of required column names
    
    Returns:
    --------
    Tuple[bool, str]: (is_valid, error_message)
    """
    if df.empty:
        return False, "Dataframe is empty"
    
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        return False, f"Missing required columns: {missing_cols}"
    
    # Check for NaN in required columns
    for col in required_columns:
        if df[col].isna().all():
            return False, f"Column '{col}' contains only NaN values"
    
    return True, ""


def handle_nan_values(df: pd.DataFrame, strategy: str = 'forward_fill') -> pd.DataFrame:
    """
    Handle NaN values in the dataframe
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    strategy : str
        NaN handling strategy: 'forward_fill', 'backward_fill', or 'drop'
    
    Returns:
    --------
    pd.DataFrame: Dataframe with NaN handled
    """
    df_clean = df.copy()
    
    # Identify technical indicator columns (excluding price and date columns)
    price_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    date_cols = ['Date']
    tech_cols = [col for col in df.columns if col not in price_cols + date_cols]
    
    logger.info(f"Handling NaN values for {len(tech_cols)} technical indicator columns")
    
    if strategy == 'forward_fill':
        # Forward fill for technical indicators, but not for price data
        for col in tech_cols:
            df_clean[col] = df_clean[col].ffill()
        
        # For initial NaN values that can't be forward filled, use backward fill
        for col in tech_cols:
            df_clean[col] = df_clean[col].bfill()
            
    elif strategy == 'drop':
        # Drop rows where all technical indicators are NaN
        tech_nan_mask = df_clean[tech_cols].isna().all(axis=1)
        df_clean = df_clean[~tech_nan_mask].reset_index(drop=True)
        logger.info(f"Dropped {tech_nan_mask.sum()} rows with all NaN technical indicators")
    
    # Count remaining NaN values
    nan_count = df_clean[tech_cols].isna().sum().sum()
    if nan_count > 0:
        logger.warning(f"Still have {nan_count} NaN values in technical indicators after handling")
    
    return df_clean


def calculate_features(
    input_file: str, 
    output_file: str,
    nan_handling: str = 'forward_fill'
) -> Optional[pd.DataFrame]:
    """
    Main function to calculate technical indicators from EURUSD data
    
    Parameters:
    -----------
    input_file : str
        Path to input CSV file
    output_file : str
        Path to output CSV file with features
    nan_handling : str
        Strategy for handling NaN values: 'forward_fill' or 'drop'
    
    Returns:
    --------
    pd.DataFrame or None: Dataframe with calculated features
    
    Raises:
    -------
    ValueError: If input validation fails
    FileNotFoundError: If input file doesn't exist
    """
    
    logger.info(f"Starting feature calculation from: {input_file}")
    
    try:
        # Read the CSV file
        logger.info(f"Reading data from {input_file}")
        df = pd.read_csv(input_file)
        
        logger.info(f"Data loaded successfully. Shape: {df.shape}")
        logger.info(f"Columns: {list(df.columns)}")
        
        # Validate required columns
        required_columns = ['Date', 'Close']
        is_valid, error_msg = validate_dataframe(df, required_columns)
        if not is_valid:
            logger.error(f"Data validation failed: {error_msg}")
            raise ValueError(f"Input data validation failed: {error_msg}")
        
        # Ensure Date column is datetime
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # Check for invalid dates
        invalid_dates = df['Date'].isna().sum()
        if invalid_dates > 0:
            logger.warning(f"Found {invalid_dates} invalid dates, they will be set to NaT")
        
        # Sort by date
        df = df.sort_values('Date').reset_index(drop=True)
        
        # Log date range
        valid_dates = df['Date'].dropna()
        if len(valid_dates) > 0:
            logger.info(f"Date range: {valid_dates.min()} to {valid_dates.max()}")
        
        # Initialize indicator calculator
        calculator = TechnicalIndicators()
        
        # Calculate technical indicators
        logger.info("Calculating technical indicators...")
        
        # SMA indicators
        df['SMA_20'] = calculator.calculate_sma(df, 20)
        df['SMA_50'] = calculator.calculate_sma(df, 50)
        
        # RSI
        df['RSI_14'] = calculator.calculate_rsi(df, 14)
        
        # MACD
        macd_line, signal_line, histogram = calculator.calculate_macd(df)
        df['MACD_line'] = macd_line
        df['MACD_signal'] = signal_line
        df['MACD_histogram'] = histogram
        
        # Calculate SMA crossover signal (only when both SMAs are valid)
        sma_valid_mask = df['SMA_20'].notna() & df['SMA_50'].notna()
        df['SMA_crossover'] = 0  # Default to 0 (no signal)
        df.loc[sma_valid_mask, 'SMA_crossover'] = np.where(
            df.loc[sma_valid_mask, 'SMA_20'] > df.loc[sma_valid_mask, 'SMA_50'], 1, -1
        )
        
        # Calculate price position relative to SMAs (as percentage)
        for sma_col in ['SMA_20', 'SMA_50']:
            price_vs_col = f'Price_vs_{sma_col}'
            valid_mask = df[sma_col].notna() & (df[sma_col] != 0)
            df[price_vs_col] = np.nan
            df.loc[valid_mask, price_vs_col] = (
                (df.loc[valid_mask, 'Close'] - df.loc[valid_mask, sma_col]) / 
                df.loc[valid_mask, sma_col] * 100
            )
        
        # Calculate returns
        df['Returns'] = df['Close'].pct_change()
        
        # Handle NaN values in technical indicators
        logger.info(f"Applying NaN handling strategy: {nan_handling}")
        df = handle_nan_values(df, strategy=nan_handling)
        
        # Add metadata
        df['Feature_Calculated_At'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df['Feature_Version'] = '2.0'
        df['NaN_Handling_Strategy'] = nan_handling
        
        # Save to CSV
        logger.info(f"Saving features to: {output_file}")
        df.to_csv(output_file, index=False)
        
        # Generate comprehensive summary
        logger.info("=== FEATURE CALCULATION SUMMARY ===")
        logger.info(f"Total rows processed: {len(df)}")
        
        if 'Date' in df.columns and df['Date'].notna().any():
            valid_dates = df['Date'].dropna()
            logger.info(f"Date range: {valid_dates.min()} to {valid_dates.max()}")
        
        # Count feature columns
        base_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        feature_cols = [col for col in df.columns if col not in base_cols]
        logger.info(f"Features calculated: {len(feature_cols)}")
        
        logger.info("\nFeature columns statistics:")
        for col in feature_cols:
            non_null = df[col].notna().sum()
            null_pct = (df[col].isna().sum() / len(df)) * 100
            if null_pct > 0:
                logger.warning(f"  - {col}: {non_null} non-null ({null_pct:.1f}% null)")
            else:
                logger.info(f"  - {col}: {non_null} non-null ({null_pct:.1f}% null)")
        
        # Log sample data
        logger.info("\nSample of calculated features (last 3 rows):")
        sample_cols = ['Date', 'Close', 'SMA_20', 'SMA_50', 'RSI_14', 'MACD_line', 'SMA_crossover']
        available_cols = [col for col in sample_cols if col in df.columns]
        if available_cols:
            logger.info(f"\n{df[available_cols].tail(3).to_string()}")
        
        logger.info(f"\nFeatures successfully saved to {output_file}")
        
        return df
        
    except FileNotFoundError:
        logger.error(f"Input file not found: {input_file}")
        raise
    except pd.errors.EmptyDataError:
        logger.error(f"Input file is empty: {input_file}")
        raise
    except Exception as e:
        logger.error(f"Error calculating features: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    # Define file paths
    input_file = "data/raw/eurusd_1h.csv"
    output_file = "workspace/eurusd_features_v2.csv"
    
    # Calculate features with improved error handling
    try:
        features_df = calculate_features(
            input_file=input_file,
            output_file=output_file,
            nan_handling='forward_fill'
        )
        print("Feature calculation completed successfully!")
        
    except Exception as e:
        print(f"Feature calculation failed: {e}")
        exit(1)