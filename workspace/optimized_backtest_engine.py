"""
HIGH-PERFORMANCE VECTORIZED BACKTEST ENGINE
Engineer: ML Trading Bot Team
Optimization Target: 50%+ reduction in backtest time for 10+ forex pairs

ARCHITECTURE:
1. Parallel Data Loading: Concurrent CSV loading for all pairs
2. Vectorized Signal Calculation: Batch compute SMA, signals, returns
3. Multiprocessing Execution: Parallel backtest execution
4. Memory-efficient Aggregation: Reduce memory footprint
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
import warnings
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
import os
from dataclasses import dataclass
import logging

warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig:
    """Configuration for backtest parameters"""
    fast_sma: int = 20
    slow_sma: int = 50
    threshold: float = 0.001
    initial_capital: float = 10000.0
    commission: float = 0.001  # 0.1% commission

class VectorizedBacktestEngine:
    """
    High-performance backtest engine using vectorized operations
    and parallel processing for multiple forex pairs
    """
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.results = {}
        
    def load_data_batch(self, file_paths: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Parallel loading of multiple CSV files
        Returns: Dictionary of {symbol: dataframe}
        """
        def load_single(path):
            symbol = os.path.basename(path).replace('.csv', '')
            try:
                df = pd.read_csv(path, index_col=0, parse_dates=True)
                df.columns = [col.lower() for col in df.columns]
                return symbol, df
            except Exception as e:
                logger.error(f"Failed to load {path}: {e}")
                return symbol, None
        
        # Use ProcessPoolExecutor for parallel I/O
        with ProcessPoolExecutor(max_workers=min(len(file_paths), mp.cpu_count())) as executor:
            futures = {executor.submit(load_single, path): path for path in file_paths}
            
        data = {}
        for future in as_completed(futures):
            symbol, df = future.result()
            if df is not None:
                data[symbol] = df
                
        return data
    
    def calculate_signals_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Vectorized signal calculation for a single symbol
        All operations are batch-processed without loops
        """
        # Ensure we have required columns
        required_cols = ['open', 'high', 'low', 'close']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")
        
        # Vectorized SMA calculation
        df['fast_sma'] = df['close'].rolling(window=self.config.fast_sma).mean()
        df['slow_sma'] = df['close'].rolling(window=self.config.slow_sma).mean()
        
        # Vectorized signal generation
        df['sma_diff'] = df['fast_sma'] - df['slow_sma']
        df['signal'] = 0
        
        # Buy signal: fast crosses above slow with threshold
        buy_mask = (df['sma_diff'] > self.config.threshold) & (df['sma_diff'].shift(1) <= self.config.threshold)
        df.loc[buy_mask, 'signal'] = 1
        
        # Sell signal: fast crosses below slow with negative threshold
        sell_mask = (df['sma_diff'] < -self.config.threshold) & (df['sma_diff'].shift(1) >= -self.config.threshold)
        df.loc[sell_mask, 'signal'] = -1
        
        # Forward fill NaN values
        df[['fast_sma', 'slow_sma']] = df[['fast_sma', 'slow_sma']].ffill()
        df['signal'] = df['signal'].ffill().fillna(0)
        
        return df
    
    def run_backtest_single(self, symbol: str, df: pd.DataFrame) -> Dict:
        """
        Run backtest for a single symbol with vectorized operations
        """
        try:
            # Calculate signals
            df = self.calculate_signals_vectorized(df.copy())
            
            # Vectorized position calculation
            df['position'] = df['signal'].shift(1).fillna(0)
            
            # Vectorized returns calculation
            df['returns'] = df['close'].pct_change()
            df['strategy_returns'] = df['position'] * df['returns']
            
            # Vectorized commission calculation
            df['position_changes'] = df['position'].diff().abs()
            df['commission_cost'] = df['position_changes'] * self.config.commission
            
            # Net strategy returns
            df['net_strategy_returns'] = df['strategy_returns'] - df['commission_cost']
            
            # Cumulative returns (vectorized)
            df['cumulative_returns'] = (1 + df['net_strategy_returns']).cumprod()
            df['cumulative_benchmark'] = (1 + df['returns']).cumprod()
            
            # Calculate metrics
            total_trades = (df['position'].diff() != 0).sum()
            winning_trades = ((df['strategy_returns'] > 0) & (df['position'].diff() != 0)).sum()
            
            # Performance metrics
            total_return = df['cumulative_returns'].iloc[-1] - 1 if len(df) > 0 else 0
            sharpe_ratio = self._calculate_sharpe_ratio(df['net_strategy_returns'])
            max_drawdown = self._calculate_max_drawdown(df['cumulative_returns'])
            
            return {
                'symbol': symbol,
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'total_trades': int(total_trades),
                'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
                'data_points': len(df),
                'final_equity': self.config.initial_capital * (1 + total_return)
            }
            
        except Exception as e:
            logger.error(f"Backtest failed for {symbol}: {e}")
            return None
    
    def run_backtest_parallel(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """
        Parallel execution of backtests for multiple symbols
        """
        results = {}
        
        with ProcessPoolExecutor(max_workers=mp.cpu_count()) as executor:
            # Submit all backtests
            future_to_symbol = {
                executor.submit(self.run_backtest_single, symbol, df): symbol 
                for symbol, df in data.items()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result:
                        results[symbol] = result
                        logger.info(f"Completed backtest for {symbol}")
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
        
        return results
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Vectorized Sharpe ratio calculation"""
        if len(returns) < 2:
            return 0
        excess_returns = returns - (risk_free_rate / 252)
        return np.sqrt(252) * excess_returns.mean() / returns.std() if returns.std() > 0 else 0
    
    def _calculate_max_drawdown(self, cumulative_returns: pd.Series) -> float:
        """Vectorized max drawdown calculation"""
        if len(cumulative_returns) == 0:
            return 0
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        return drawdown.min()
    
    def generate_summary_report(self, results: Dict[str, Dict]) -> pd.DataFrame:
        """Generate aggregated performance report"""
        df = pd.DataFrame(results).T
        if len(df) == 0:
            return df
        
        # Add summary statistics
        summary = {
            'Average Return': df['total_return'].mean(),
            'Average Sharpe': df['sharpe_ratio'].mean(),
            'Average Max DD': df['max_drawdown'].mean(),
            'Total Trades': df['total_trades'].sum(),
            'Average Win Rate': df['win_rate'].mean()
        }
        
        df.loc['SUMMARY'] = summary
        return df

def main():
    """Main execution for performance comparison"""
    import time
    
    # Configuration
    config = BacktestConfig(
        fast_sma=20,
        slow_sma=50,
        threshold=0.001,
        initial_capital=10000.0,
        commission=0.001
    )
    
    # Find forex pair data files
    data_dir = "data/raw"
    if not os.path.exists(data_dir):
        logger.error(f"Data directory not found: {data_dir}")
        return
    
    forex_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) 
                  if f.endswith('.csv') and f.startswith('forex_')]
    
    if len(forex_files) < 10:
        logger.warning(f"Found only {len(forex_files)} forex files. Need at least 10 for optimal benchmarking.")
    
    # Initialize engines
    old_engine = None  # Would be the original backtest_sma engine
    new_engine = VectorizedBacktestEngine(config)
    
    # Load data once
    logger.info(f"Loading {len(forex_files)} forex pairs...")
    data = new_engine.load_data_batch(forex_files[:15])  # Test with up to 15 pairs
    
    if not data:
        logger.error("No data loaded")
        return
    
    # Run parallel backtest
    logger.info(f"Running parallel backtest on {len(data)} pairs...")
    start_time = time.time()
    results = new_engine.run_backtest_parallel(data)
    parallel_time = time.time() - start_time
    
    # Generate report
    report = new_engine.generate_summary_report(results)
    
    logger.info(f"\n{'='*60}")
    logger.info("PERFORMANCE REPORT")
    logger.info(f"{'='*60}")
    logger.info(f"Pairs Processed: {len(data)}")
    logger.info(f"Parallel Execution Time: {parallel_time:.2f} seconds")
    logger.info(f"Average Time per Pair: {parallel_time/len(data):.2f} seconds")
    logger.info(f"\nPerformance Summary:\n{report}")
    
    # Save results
    report.to_csv('workspace/optimized_backtest_results.csv')
    logger.info("Results saved to workspace/optimized_backtest_results.csv")

if __name__ == "__main__":
    main()