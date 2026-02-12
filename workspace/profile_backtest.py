import cProfile
import pstats
import io
import time
import pandas as pd
import numpy as np
from backtest_sma import SMABacktestEngine

def profile_backtest():
    """Profile the backtest engine to identify bottlenecks."""
    print("🔍 PROFILING SMA BACKTEST ENGINE")
    print("=" * 60)
    
    # Initialize engine
    engine = SMABacktestEngine(fast_period=10, slow_period=30)
    
    # Create sample data for profiling
    print("\n📊 Generating sample data...")
    dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='H')  # 4 years hourly
    n = len(dates)
    np.random.seed(42)
    
    # Generate synthetic OHLC data
    base_price = 1.1000
    trend = np.linspace(0, 0.2, n)
    noise = np.random.normal(0, 0.005, n)
    
    data = pd.DataFrame({
        'Date': dates,
        'Open': base_price + trend + noise,
        'High': base_price + trend + noise + np.random.uniform(0, 0.002, n),
        'Low': base_price + trend + noise - np.random.uniform(0, 0.002, n),
        'Close': base_price + trend + noise,
        'Volume': np.random.randint(1000000, 5000000, n)
    })
    
    # Save to CSV for engine to load
    data.to_csv("workspace/profile_data.csv", index=False)
    print(f"  Created {n:,} rows of synthetic data")
    
    # Profile data loading
    print("\n📈 Profiling data loading...")
    pr = cProfile.Profile()
    pr.enable()
    
    engine.load_data("workspace/profile_data.csv")
    
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(10)
    print("Top 10 functions by cumulative time:")
    print(s.getvalue()[:1000])
    
    # Profile signal calculation
    print("\n📊 Profiling signal calculation...")
    pr = cProfile.Profile()
    pr.enable()
    
    engine.calculate_sma_signals()
    
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(10)
    print("Top 10 functions by cumulative time:")
    print(s.getvalue()[:1000])
    
    # Profile backtest execution
    print("\n⚡ Profiling backtest execution...")
    pr = cProfile.Profile()
    pr.enable()
    
    metrics = engine.execute_backtest(initial_capital=10000.0)
    
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(15)
    print("Top 15 functions by cumulative time:")
    print(s.getvalue()[:1500])
    
    # Memory usage analysis
    print("\n💾 Memory usage analysis:")
    import sys
    
    # Check memory of key objects
    data_memory = sys.getsizeof(engine.data) / 1024 / 1024
    print(f"  Data DataFrame: {data_memory:.2f} MB")
    
    if hasattr(engine.data, 'memory_usage'):
        mem_usage = engine.data.memory_usage(deep=True).sum() / 1024 / 1024
        print(f"  Deep memory usage: {mem_usage:.2f} MB")
    
    # Column-wise memory
    print("\n  Column memory usage (MB):")
    for col in engine.data.columns:
        col_mem = sys.getsizeof(engine.data[col]) / 1024 / 1024
        print(f"    {col}: {col_mem:.4f} MB")
    
    return metrics

def analyze_bottlenecks():
    """Analyze specific bottlenecks in the current implementation."""
    print("\n🔬 BOTTLENECK ANALYSIS")
    print("=" * 60)
    
    bottlenecks = [
        {
            "name": "Loop-based trade simulation",
            "location": "execute_backtest() method",
            "issue": "Uses Python for-loop over DataFrame rows (O(n) with Python overhead)",
            "impact": "High - Main performance bottleneck for large datasets",
            "solution": "Vectorize with pandas/numpy operations"
        },
        {
            "name": "Rolling window calculations",
            "location": "calculate_sma_signals() method",
            "issue": "pandas rolling() creates intermediate Series objects",
            "impact": "Medium - Memory overhead from window calculations",
            "solution": "Use optimized rolling functions or pre-compute"
        },
        {
            "name": "Trade tracking in list",
            "location": "execute_backtest() method",
            "issue": "List append and dictionary updates in loop",
            "impact": "Medium - Python object overhead",
            "solution": "Use numpy arrays or pandas DataFrames"
        },
        {
            "name": "Multiple .loc assignments",
            "location": "calculate_sma_signals() method",
            "issue": "Separate .loc calls for buy/sell signals",
            "impact": "Low - Can be combined into single vectorized operation",
            "solution": "Use np.where() or vectorized assignment"
        },
        {
            "name": "Data copying",
            "location": "execute_backtest() method",
            "issue": "df = self.data.copy() creates full DataFrame copy",
            "impact": "Medium - Doubles memory usage during backtest",
            "solution": "Use in-place operations or views"
        }
    ]
    
    print("\n📋 Identified Bottlenecks:")
    for i, bottleneck in enumerate(bottlenecks, 1):
        print(f"\n{i}. {bottleneck['name']}")
        print(f"   Location: {bottleneck['location']}")
        print(f"   Issue: {bottleneck['issue']}")
        print(f"   Impact: {bottleneck['impact']}")
        print(f"   Solution: {bottleneck['solution']}")
    
    return bottlenecks

if __name__ == "__main__":
    print("🚀 Starting backtest profiling...")
    start_time = time.time()
    
    metrics = profile_backtest()
    bottlenecks = analyze_bottlenecks()
    
    elapsed = time.time() - start_time
    print(f"\n✅ Profiling completed in {elapsed:.2f} seconds")
    print(f"📊 Total trades executed: {metrics.get('total_trades', 0)}")