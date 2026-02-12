import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Create sample EURUSD data for testing
def create_sample_data():
    dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='D')
    n = len(dates)
    
    # Generate realistic EURUSD prices
    np.random.seed(42)
    base_price = 1.1000
    returns = np.random.normal(0.0001, 0.005, n)
    prices = base_price * (1 + returns).cumprod()
    
    # Create OHLCV data
    df = pd.DataFrame({
        'Date': dates,
        'Open': prices * (1 + np.random.normal(0, 0.001, n)),
        'High': prices * (1 + np.abs(np.random.normal(0.002, 0.001, n))),
        'Low': prices * (1 - np.abs(np.random.normal(0.002, 0.001, n))),
        'Close': prices,
        'Volume': np.random.randint(1000000, 5000000, n)
    })
    
    return df

# Test the feature calculation functions
def test_feature_calculations():
    print("Creating sample EURUSD data for testing...")
    df = create_sample_data()
    
    print(f"Sample data shape: {df.shape}")
    print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
    
    # Save sample data
    df.to_csv("workspace/sample_eurusd.csv", index=False)
    print("Sample data saved to workspace/sample_eurusd.csv")
    
    # Test feature calculation
    from calculate_features import calculate_sma, calculate_rsi, calculate_macd
    
    # Test SMA
    sma_20 = calculate_sma(df, 20)
    sma_50 = calculate_sma(df, 50)
    print(f"\nSMA_20 calculated: {len(sma_20.dropna())} valid values")
    print(f"SMA_50 calculated: {len(sma_50.dropna())} valid values")
    
    # Test RSI
    rsi_14 = calculate_rsi(df, 14)
    print(f"RSI_14 calculated: {len(rsi_14.dropna())} valid values")
    print(f"RSI range: {rsi_14.min():.2f} to {rsi_14.max():.2f}")
    
    # Test MACD
    macd_line, signal_line, histogram = calculate_macd(df)
    print(f"MACD line calculated: {len(macd_line.dropna())} valid values")
    
    # Test full pipeline
    from calculate_features import calculate_features
    
    print("\n--- Testing full feature calculation pipeline ---")
    result_df = calculate_features("workspace/sample_eurusd.csv", "workspace/test_features.csv")
    
    if result_df is not None:
        print("\nTest completed successfully!")
        print(f"Output columns: {list(result_df.columns)}")
        
        # Verify calculations
        assert 'SMA_20' in result_df.columns, "SMA_20 not calculated"
        assert 'SMA_50' in result_df.columns, "SMA_50 not calculated"
        assert 'RSI_14' in result_df.columns, "RSI_14 not calculated"
        assert 'MACD_line' in result_df.columns, "MACD_line not calculated"
        
        print("All required features verified successfully!")
        
        # Show feature summary
        print("\nFeature Summary Statistics:")
        feature_cols = ['SMA_20', 'SMA_50', 'RSI_14', 'MACD_line']
        for col in feature_cols:
            if col in result_df.columns:
                valid_count = result_df[col].count()
                print(f"{col}: {valid_count} valid values, Mean={result_df[col].mean():.5f}")

if __name__ == "__main__":
    test_feature_calculations()