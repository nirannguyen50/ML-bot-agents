"""
Simple Moving Average (SMA) Calculator - Fixed Version
Engineer: ML Trading Bot Team
Date: 2024
Fixed Issues:
1. Completed SMA calculation logic
2. Added proper NaN handling
3. Optimized logging levels
"""

import numpy as np
from typing import Union, List, Optional
import logging
import warnings

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def calculate_sma(
    data_array: Union[List[float], np.ndarray], 
    window: int,
    fill_method: str = 'forward',
    min_valid_data: float = 0.5
) -> np.ndarray:
    """
    Calculate Simple Moving Average (SMA) with robust NaN handling.
    
    Parameters:
    -----------
    data_array : Union[List[float], np.ndarray]
        Input price data series
    window : int
        Moving average window size (must be positive integer)
    fill_method : str, optional
        Method to handle NaN values: 'forward', 'backward', 'zero', or 'drop'
        Default: 'forward'
    min_valid_data : float, optional
        Minimum percentage of valid (non-NaN) data required in window
        Default: 0.5 (50%)
    
    Returns:
    --------
    np.ndarray
        SMA values with same length as input (NaNs for insufficient data)
    
    Raises:
    -------
    ValueError
        If window <= 0 or data_array is empty
    TypeError
        If input is not list or numpy array
    
    Examples:
    ---------
    >>> calculate_sma([1, 2, 3, 4, 5], window=3)
    array([nan, nan, 2., 3., 4.])
    """
    # Input validation
    if not isinstance(data_array, (list, np.ndarray)):
        raise TypeError(f"data_array must be list or numpy array, got {type(data_array)}")
    
    if len(data_array) == 0:
        raise ValueError("data_array cannot be empty")
    
    if not isinstance(window, int) or window <= 0:
        raise ValueError(f"window must be positive integer, got {window}")
    
    if window > len(data_array):
        logger.warning(f"Window size ({window}) exceeds data length ({len(data_array)})")
        return np.full(len(data_array), np.nan)
    
    # Convert to numpy array for efficient operations
    data = np.array(data_array, dtype=np.float64)
    
    # Log function call at DEBUG level (not INFO)
    logger.debug(f"calculate_sma called: data_length={len(data)}, window={window}, fill_method={fill_method}")
    
    # NaN handling strategy
    original_has_nan = np.isnan(data).any()
    data_clean = data.copy()
    
    if original_has_nan:
        logger.debug(f"Input contains NaN values: {np.isnan(data).sum()}/{len(data)}")
        
        # Handle NaN based on fill_method
        if fill_method == 'forward':
            # Forward fill (carry last valid observation forward)
            valid_idx = np.where(~np.isnan(data_clean))[0]
            if len(valid_idx) > 0:
                for i in range(1, len(data_clean)):
                    if np.isnan(data_clean[i]):
                        data_clean[i] = data_clean[i-1]
        
        elif fill_method == 'backward':
            # Backward fill (use next valid observation)
            valid_idx = np.where(~np.isnan(data_clean))[0]
            if len(valid_idx) > 0:
                for i in range(len(data_clean)-2, -1, -1):
                    if np.isnan(data_clean[i]):
                        data_clean[i] = data_clean[i+1]
        
        elif fill_method == 'zero':
            # Replace NaN with zeros
            data_clean[np.isnan(data_clean)] = 0.0
            
        elif fill_method == 'drop':
            # This method would change array length, not implemented here
            logger.warning("'drop' method not implemented, using 'forward' instead")
            valid_idx = np.where(~np.isnan(data_clean))[0]
            if len(valid_idx) > 0:
                for i in range(1, len(data_clean)):
                    if np.isnan(data_clean[i]):
                        data_clean[i] = data_clean[i-1]
        else:
            logger.warning(f"Unknown fill_method: {fill_method}, using 'forward'")
            valid_idx = np.where(~np.isnan(data_clean))[0]
            if len(valid_idx) > 0:
                for i in range(1, len(data_clean)):
                    if np.isnan(data_clean[i]):
                        data_clean[i] = data_clean[i-1]
    
    # Calculate moving average using convolution for efficiency
    # This is the previously missing implementation
    weights = np.ones(window) / window
    sma = np.convolve(data_clean, weights, mode='valid')
    
    # Pad beginning with NaN since SMA needs at least 'window' data points
    pad_length = window - 1
    sma_padded = np.full(len(data), np.nan)
    sma_padded[pad_length:] = sma
    
    # Apply minimum valid data check for each window
    for i in range(window - 1, len(data)):
        window_data = data[max(0, i - window + 1):i + 1]
        valid_count = np.sum(~np.isnan(window_data))
        
        if valid_count / window < min_valid_data:
            sma_padded[i] = np.nan
            logger.debug(f"Window at index {i} has insufficient valid data: {valid_count}/{window}")
    
    # Final validation
    if np.isnan(sma_padded).all():
        logger.warning("All SMA values are NaN - check input data and parameters")
    
    logger.debug(f"SMA calculation complete: {np.sum(~np.isnan(sma_padded))}/{len(sma_padded)} valid values")
    return sma_padded


def calculate_sma_dataframe(
    df: 'pd.DataFrame',
    price_column: str,
    window: int,
    new_column_name: Optional[str] = None,
    **kwargs
) -> 'pd.DataFrame':
    """
    Calculate SMA for a pandas DataFrame column.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input DataFrame with price data
    price_column : str
        Column name containing price data
    window : int
        Moving average window size
    new_column_name : str, optional
        Name for new SMA column. Default: f"SMA_{window}"
    **kwargs : dict
        Additional arguments passed to calculate_sma
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with new SMA column added
    """
    try:
        import pandas as pd
    except ImportError:
        logger.error("pandas is required for calculate_sma_dataframe")
        raise
    
    if price_column not in df.columns:
        raise ValueError(f"Column '{price_column}' not found in DataFrame")
    
    if new_column_name is None:
        new_column_name = f"SMA_{window}"
    
    # Extract price data
    price_data = df[price_column].values
    
    # Calculate SMA
    sma_values = calculate_sma(price_data, window, **kwargs)
    
    # Add to DataFrame
    result_df = df.copy()
    result_df[new_column_name] = sma_values
    
    logger.info(f"Added SMA column '{new_column_name}' to DataFrame (window={window})")
    return result_df


if __name__ == "__main__":
    # Test the implementation
    print("Testing calculate_sma function...")
    
    # Test case 1: Simple array
    test_data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    sma_3 = calculate_sma(test_data, window=3)
    print(f"Test 1 - SMA(3) of [1..10]: {sma_3}")
    print(f"  Expected: [nan, nan, 2, 3, 4, 5, 6, 7, 8, 9]")
    
    # Test case 2: With NaN values
    test_data_nan = [1.0, 2.0, np.nan, 4.0, 5.0, np.nan, 7.0, 8.0, 9.0, 10.0]
    sma_3_nan = calculate_sma(test_data_nan, window=3, fill_method='forward')
    print(f"\nTest 2 - SMA(3) with NaN (forward fill): {sma_3_nan}")
    
    # Test case 3: Error handling
    try:
        calculate_sma([], window=5)
    except ValueError as e:
        print(f"\nTest 3 - Empty array error (expected): {e}")
    
    print("\nAll tests completed!")