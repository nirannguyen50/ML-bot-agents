"""
Simple Moving Average (SMA) Calculator

This module provides a robust function for calculating Simple Moving Average
with proper input validation, error handling, and documentation.

Author: ML Trading Bot Team - Engineer
Date: 2024
"""

import logging
import numpy as np
from typing import Union, List, Optional
from numbers import Number

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def calculate_sma(data: Union[List[float], np.ndarray], window: int) -> np.ndarray:
    """
    Calculate Simple Moving Average (SMA) for given data.
    
    The SMA is calculated as the average of the last 'window' data points.
    The first (window-1) elements will be NaN since there's not enough data.
    
    Args:
        data: Input data as a list or numpy array of numerical values.
            Must contain at least 'window' elements.
        window: The moving average window size (positive integer).
    
    Returns:
        numpy.ndarray: Array of SMA values with same length as input data.
            First (window-1) elements are NaN.
    
    Raises:
        TypeError: If data is not a list or numpy array, or contains non-numeric values.
        ValueError: If window is not positive, or data length is less than window.
        Exception: For any unexpected errors during calculation.
    
    Examples:
        >>> calculate_sma([1, 2, 3, 4, 5], 3)
        array([nan, nan, 2., 3., 4.])
    """
    try:
        # Input validation and logging
        logger.info(f"Calculating SMA with window={window} for data of length={len(data) if hasattr(data, '__len__') else 'unknown'}")
        
        # 1. Validate window parameter
        if not isinstance(window, int):
            raise TypeError(f"Window must be an integer, got {type(window).__name__}")
        
        if window <= 0:
            raise ValueError(f"Window must be positive, got {window}")
        
        # 2. Validate data parameter
        if not isinstance(data, (list, np.ndarray)):
            raise TypeError(f"Data must be a list or numpy array, got {type(data).__name__}")
        
        # Convert to numpy array for consistent processing
        data_array = np.array(data, dtype=np.float64)
        
        # Check for non-numeric values
        if not np.issubdtype(data_array.dtype, np.number):
            raise TypeError("Data must contain only numeric values")
        
        # 3. Check data length
        if len(data_array) < window:
            raise ValueError(
                f"Data length ({len(data_array)}) is less than window size ({window}). "
                f"Need at least {window} data points to calculate SMA."
            )
        
        # 4. Calculate SMA
        # Create result array initialized with NaN
        sma = np.full_like(data_array, np.nan, dtype=np.float64)
        
        # Calculate moving average using convolution for efficiency
        # This is mathematically equivalent to: sma[i] = mean(data[i-window+1:i+1])
        for i in range(window - 1, len(data_array)):
            sma[i] = np.mean(data_array[i - window + 1:i + 1])
        
        # 5. Log success
        logger.info(f"SMA calculation completed successfully. "
                   f"Result: {len(sma)} values, {np.sum(np.isnan(sma))} NaN entries")
        
        return sma
        
    except (TypeError, ValueError) as e:
        # Re-raise validation errors with clear messages
        logger.error(f"Input validation failed: {str(e)}")
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error in calculate_sma: {str(e)}", exc_info=True)
        raise RuntimeError(f"Failed to calculate SMA: {str(e)}") from e


def calculate_sma_with_validation(data: Union[List[float], np.ndarray], window: int, 
                                 fill_method: Optional[str] = None) -> np.ndarray:
    """
    Enhanced SMA calculation with additional options for handling edge cases.
    
    Args:
        data: Input data as a list or numpy array of numerical values.
        window: The moving average window size (positive integer).
        fill_method: Method to handle initial NaN values:
            - None: Keep NaN (default)
            - 'forward': Forward fill with first valid SMA value
            - 'zero': Replace NaN with 0
            - 'none': Keep NaN (same as None)
    
    Returns:
        numpy.ndarray: Array of SMA values.
    
    Raises:
        ValueError: If fill_method is invalid.
    """
    # Calculate base SMA
    sma = calculate_sma(data, window)
    
    # Handle fill method if specified
    if fill_method and fill_method != 'none':
        valid_start = window - 1  # Index of first non-NaN value
        
        if fill_method == 'forward':
            # Forward fill: fill initial NaN values with first valid SMA
            if valid_start < len(sma) and not np.isnan(sma[valid_start]):
                fill_value = sma[valid_start]
                sma[:valid_start] = fill_value
                
        elif fill_method == 'zero':
            # Replace NaN with 0
            sma[np.isnan(sma)] = 0
            
        else:
            raise ValueError(f"Invalid fill_method: {fill_method}. "
                           f"Valid options: None, 'forward', 'zero', 'none'")
    
    return sma


# Test function to verify implementation
def test_calculate_sma():
    """Test suite for SMA calculation."""
    print("Running SMA tests...")
    
    # Test 1: Basic functionality
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    window = 3
    result = calculate_sma(data, window)
    expected_nan_count = window - 1
    actual_nan_count = np.sum(np.isnan(result))
    
    print(f"Test 1 - Basic: data={data[:5]}..., window={window}")
    print(f"  Result shape: {result.shape}, NaN count: {actual_nan_count}")
    print(f"  First non-NaN value (index {window-1}): {result[window-1]}")
    print(f"  Expected SMA at index 2: (1+2+3)/3 = 2.0")
    print(f"  Got: {result[2]}")
    assert actual_nan_count == expected_nan_count, f"Expected {expected_nan_count} NaN values, got {actual_nan_count}"
    assert np.isclose(result[2], 2.0), f"Expected 2.0, got {result[2]}"
    assert np.isclose(result[5], 5.0), f"Expected 5.0, got {result[5]}"  # (4+5+6)/3 = 5.0
    print("  ✓ Passed")
    
    # Test 2: Edge case - window equals data length
    print("\nTest 2 - Window equals data length:")
    result = calculate_sma([1, 2, 3, 4], 4)
    print(f"  Result: {result}")
    assert np.isnan(result[0]) and np.isnan(result[1]) and np.isnan(result[2])
    assert np.isclose(result[3], 2.5)  # (1+2+3+4)/4 = 2.5
    print("  ✓ Passed")
    
    # Test 3: Error handling - window too large
    print("\nTest 3 - Error handling (window too large):")
    try:
        calculate_sma([1, 2, 3], 5)
        print("  ✗ Should have raised ValueError")
        assert False
    except ValueError as e:
        print(f"  ✓ Correctly raised ValueError: {str(e)[:50]}...")
    
    # Test 4: Error handling - invalid data type
    print("\nTest 4 - Error handling (invalid data):")
    try:
        calculate_sma(["a", "b", "c"], 2)
        print("  ✗ Should have raised TypeError")
        assert False
    except (TypeError, RuntimeError) as e:
        print(f"  ✓ Correctly raised error: {type(e).__name__}")
    
    # Test 5: Enhanced version with fill
    print("\nTest 5 - Enhanced version with forward fill:")
    data = [1, 2, 3, 4, 5]
    result = calculate_sma_with_validation(data, 3, fill_method='forward')
    print(f"  Data: {data}")
    print(f"  Result with forward fill: {result}")
    assert not np.any(np.isnan(result)), "Should not have NaN values with forward fill"
    assert np.isclose(result[0], 2.0), f"First value should be 2.0, got {result[0]}"
    print("  ✓ Passed")
    
    print("\nAll tests passed! ✅")


if __name__ == "__main__":
    # Run tests when script is executed directly
    test_calculate_sma()
    
    # Example usage
    print("\n" + "="*50)
    print("EXAMPLE USAGE:")
    print("="*50)
    
    sample_data = [10, 12, 15, 14, 16, 18, 17, 19, 21, 20]
    sample_window = 3
    
    print(f"Sample data: {sample_data}")
    print(f"Window size: {sample_window}")
    
    sma_result = calculate_sma(sample_data, sample_window)
    print(f"\nSMA result (first 5 values): {sma_result[:5]}")
    print(f"Complete result: {sma_result}")
    
    # Calculate some specific values for verification
    print(f"\nVerification:")
    print(f"SMA[2] = ({sample_data[0]} + {sample_data[1]} + {sample_data[2]}) / {sample_window} = {sma_result[2]:.2f}")
    print(f"SMA[5] = ({sample_data[3]} + {sample_data[4]} + {sample_data[5]}) / {sample_window} = {sma_result[5]:.2f}")