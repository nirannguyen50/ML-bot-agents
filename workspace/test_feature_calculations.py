"""
Unit tests for feature calculations
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

class TestFeatureCalculations:
    """Test suite for feature engineering functions"""
    
    def test_moving_average(self):
        """Test moving average calculation"""
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        
        # Calculate SMA
        sma_3 = data.rolling(window=3).mean()
        
        assert len(sma_3) == 10
        assert pd.isna(sma_3.iloc[0])  # First two should be NaN
        assert pd.isna(sma_3.iloc[1])
        assert sma_3.iloc[2] == 2.0  # (1+2+3)/3
        assert sma_3.iloc[9] == 9.0  # (8+9+10)/3
    
    def test_rsi_calculation(self):
        """Test RSI calculation logic"""
        prices = [100, 102, 101, 103, 105, 104, 106, 107, 105, 108]
        price_series = pd.Series(prices)
        
        # Calculate price changes
        deltas = price_series.diff()
        
        # Separate gains and losses
        gains = deltas.where(deltas > 0, 0)
        losses = -deltas.where(deltas < 0, 0)
        
        assert len(gains) == len(prices)
        assert len(losses) == len(prices)
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        data = pd.Series(np.random.randn(100).cumsum() + 100)
        
        # Calculate Bollinger Bands
        window = 20
        sma = data.rolling(window=window).mean()
        std = data.rolling(window=window).std()
        
        upper_band = sma + (std * 2)
        lower_band = sma - (std * 2)
        
        assert len(upper_band) == len(data)
        assert len(lower_band) == len(data)
        assert all(upper_band >= lower_band)
    
    def test_volume_indicators(self):
        """Test volume-based indicators"""
        prices = pd.Series([100, 105, 103, 108, 110])
        volumes = pd.Series([1000, 1500, 1200, 2000, 1800])
        
        # Calculate volume-weighted average price (VWAP)
        typical_price = (prices * volumes).sum() / volumes.sum()
        
        assert isinstance(typical_price, float)
        assert typical_price > 0
    
    def test_feature_consistency(self):
        """Test that features maintain consistent dimensions"""
        n_samples = 50
        data = pd.DataFrame({
            'price': np.random.randn(n_samples).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, n_samples)
        })
        
        # Calculate multiple features
        data['sma_10'] = data['price'].rolling(10).mean()
        data['returns'] = data['price'].pct_change()
        data['volatility'] = data['returns'].rolling(20).std()
        
        assert data.shape[0] == n_samples
        assert data.shape[1] == 5  # price, volume, sma_10, returns, volatility

if __name__ == "__main__":
    pytest.main([__file__, "-v"])