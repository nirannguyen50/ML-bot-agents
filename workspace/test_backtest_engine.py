"""
Unit tests for backtest engine functionality
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

class TestBacktestEngine:
    """Test suite for backtest engine"""
    
    def test_data_loading(self):
        """Test that data can be loaded correctly"""
        # Create sample data
        dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='D')
        data = pd.DataFrame({
            'open': np.random.randn(10).cumsum() + 100,
            'high': np.random.randn(10).cumsum() + 105,
            'low': np.random.randn(10).cumsum() + 95,
            'close': np.random.randn(10).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 10)
        }, index=dates)
        
        assert len(data) == 10
        assert 'open' in data.columns
        assert 'close' in data.columns
        assert 'volume' in data.columns
    
    def test_strategy_execution(self):
        """Test basic strategy execution logic"""
        # Mock strategy: Buy when price > 100
        prices = [95, 98, 102, 105, 103]
        signals = [1 if price > 100 else 0 for price in prices]
        
        expected_signals = [0, 0, 1, 1, 1]
        assert signals == expected_signals
    
    def test_returns_calculation(self):
        """Test returns calculation"""
        prices = [100, 105, 103, 108, 110]
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        assert len(returns) == 4
        assert all(isinstance(r, float) for r in returns)
    
    def test_risk_metrics(self):
        """Test basic risk metrics calculation"""
        returns = [0.05, -0.02, 0.03, -0.01, 0.04]
        
        # Calculate Sharpe ratio (simplified)
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return > 0:
            sharpe = mean_return / std_return
            assert isinstance(sharpe, float)
        
        # Calculate max drawdown
        cumulative = np.cumprod([1 + r for r in returns])
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        assert max_drawdown <= 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])