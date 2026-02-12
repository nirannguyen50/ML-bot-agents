import pandas as pd
import os

def test_features():
    """Test the calculated features"""
    
    features_file = "workspace/eurusd_features.csv"
    
    if not os.path.exists(features_file):
        print(f"ERROR: Features file not found: {features_file}")
        return False
    
    print(f"Loading features from: {features_file}")
    df = pd.read_csv(features_file)
    
    print(f"\n=== FEATURES VALIDATION ===")
    print(f"Data shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # Check required features exist
    required_features = ['SMA_20', 'SMA_50', 'RSI_14', 'MACD_line', 'MACD_signal', 'MACD_histogram']
    missing_features = [feat for feat in required_features if feat not in df.columns]
    
    if missing_features:
        print(f"ERROR: Missing features: {missing_features}")
        return False
    
    print(f"\n✓ All required features present")
    
    # Check data quality
    print("\n=== DATA QUALITY CHECK ===")
    
    # Check for NaN values
    nan_counts = df[required_features].isna().sum()
    total_rows = len(df)
    
    print("NaN counts per feature:")
    for feature in required_features:
        nan_count = nan_counts[feature]
        nan_pct = (nan_count / total_rows) * 100
        print(f"  - {feature}: {nan_count} NaN ({nan_pct:.1f}%)")
    
    # Check SMA values
    print("\n=== SMA VALIDATION ===")
    print(f"SMA_20 range: {df['SMA_20'].min():.5f} to {df['SMA_20'].max():.5f}")
    print(f"SMA_50 range: {df['SMA_50'].min():.5f} to {df['SMA_50'].max():.5f}")
    
    # Check RSI values (should be between 0-100)
    print("\n=== RSI VALIDATION ===")
    print(f"RSI_14 range: {df['RSI_14'].min():.2f} to {df['RSI_14'].max():.2f}")
    rsi_out_of_bounds = df[(df['RSI_14'] < 0) | (df['RSI_14'] > 100)]
    print(f"Rows with RSI out of bounds (0-100): {len(rsi_out_of_bounds)}")
    
    # Check MACD
    print("\n=== MACD VALIDATION ===")
    print(f"MACD_line range: {df['MACD_line'].min():.5f} to {df['MACD_line'].max():.5f}")
    print(f"MACD_signal range: {df['MACD_signal'].min():.5f} to {df['MACD_signal'].max():.5f}")
    
    # Statistical summary
    print("\n=== STATISTICAL SUMMARY ===")
    stats = df[required_features].describe()
    print(stats)
    
    # Save sample for inspection
    sample_file = "workspace/features_sample.csv"
    df.head(20).to_csv(sample_file, index=False)
    print(f"\nSample saved to: {sample_file}")
    
    return True

if __name__ == "__main__":
    success = test_features()
    if success:
        print("\n✅ FEATURES VALIDATION PASSED")
    else:
        print("\n❌ FEATURES VALIDATION FAILED")