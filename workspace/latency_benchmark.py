**
```python
"""
Benchmark latency from data ingestion to order placement.
Measures each component in the trading pipeline.
"""
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, Tuple, List
import warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LatencyBenchmark:
    """Benchmark trading pipeline latency"""
    
    def __init__(self):
        self.results = {}
        self.mock_data_size = 10000  # 10k rows
        
    def generate_mock_data(self) -> pd.DataFrame:
        """Generate synthetic market data for testing"""
        start_time = time.time()
        
        dates = pd.date_range(start='2024-01-01', periods=self.mock_data_size, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(100, 200, self.mock_data_size),
            'high': np.random.uniform(100, 210, self.mock_data_size),
            'low': np.random.uniform(90, 200, self.mock_data_size),
            'close': np.random.uniform(95, 205, self.mock_data_size),
            'volume': np.random.randint(1000, 100000, self.mock_data_size)
        })
        
        latency = time.time() - start_time
        self.results['data_generation'] = latency
        logger.info(f"Data generation latency: {latency:.4f}s")
        return data
    
    def mock_data_ingestion(self, data: pd.DataFrame) -> pd.DataFrame:
        """Simulate data ingestion from CSV/API"""
        start_time = time.time()
        
        # Simulate reading from file/API
        time.sleep(0.01)  # Network/disk latency
        ingested_data = data.copy()
        
        latency = time.time() - start_time
        self.results['data_ingestion'] = latency
        logger.info(f"Data ingestion latency: {latency:.4f}s")
        return ingested_data
    
    def calculate_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators (bottleneck candidate)"""
        start_time = time.time()
        
        df = data.copy()
        
        # Simple moving averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        latency = time.time() - start_time
        self.results['feature_calculation'] = latency
        logger.info(f"Feature calculation latency: {latency:.4f}s")
        return df.dropna()
    
    def execute_strategy(self, data: pd.DataFrame) -> List[Dict]:
        """Execute trading strategy on prepared data"""
        start_time = time.time()
        
        signals = []
        
        for i in range(len(data)):
            if i < 50:  # Need enough data for indicators
                continue
                
            row = data.iloc[i]
            signal = {'timestamp': row['timestamp'], 'action': 'HOLD'}
            
            # Simple strategy: SMA crossover
            if row['sma_20'] > row['sma_50'] and data.iloc[i-1]['sma_20'] <= data.iloc[i-1]['sma_50']:
                signal['action'] = 'BUY'
                signal['price'] = row['close']
            elif row['sma_20'] < row['sma_50'] and data.iloc[i-1]['sma_20'] >= data.iloc[i-1]['sma_50']:
                signal['action'] = 'SELL'
                signal['price'] = row['close']
            
            signals.append(signal)
            time.sleep(0.0001)  # Simulate strategy logic overhead
        
        latency = time.time() - start_time
        self.results['strategy_execution'] = latency
        logger.info(f"Strategy execution latency: {latency:.4f}s")
        return signals
    
    def mock_order_placement(self, signals: List[Dict]) -> Dict:
        """Simulate order placement latency"""
        start_time = time.time()
        
        placed_orders = []
        for signal in signals[:10]:  # Limit to 10 orders for demo
            if signal['action'] != 'HOLD':
                # Simulate API call to broker
                time.sleep(0.005)  # Network latency
                order = {
                    'order_id': f"ORD_{int(time.time()*1000)}",
                    'action': signal['action'],
                    'price': signal.get('price', 0),
                    'timestamp': datetime.now()
                }
                placed_orders.append(order)
        
        latency = time.time() - start_time
        self.results['order_placement'] = latency
        logger.info(f"Order placement latency: {latency:.4f}s")
        
        return {
            'orders_placed': len(placed_orders),
            'sample_orders': placed_orders[:3] if placed_orders else []
        }
    
    def run_full_pipeline(self) -> Dict:
        """Run complete pipeline and measure latencies"""
        logger.info("=" * 60)
        logger.info("RUNNING LATENCY BENCHMARK")
        logger.info("=" * 60)
        
        total_start = time.time()
        
        # Step 1: Data generation
        data = self.generate_mock_data()
        
        # Step 2: Data ingestion
        ingested_data = self.mock_data_ingestion(data)
        
        # Step 3: Feature calculation
        featured_data = self.calculate_features(ingested_data)
        
        # Step 4: Strategy execution
        signals = self.execute_strategy(featured_data)
        
        # Step 5: Order placement
        order_result = self.mock_order_placement(signals)
        
        # Total latency
        total_latency = time.time() - total_start
        self.results['total_pipeline'] = total_latency
        
        # Calculate bottlenecks
        self._analyze_bottlenecks()
        
        return {
            'latencies': self.results,
            'data_shape': featured_data.shape,
            'signals_generated': len(signals),
            'orders_placed': order_result['orders_placed'],
            'bottleneck_analysis': self.bottleneck_analysis
        }
    
    def _analyze_bottlenecks(self):
        """Identify performance bottlenecks"""
        total = self.results['total_pipeline']
        self.bottleneck_analysis = {}
        
        for stage, latency in self.results.items():
            if stage != 'total_pipeline':
                percentage = (latency / total) * 100
                self.bottleneck_analysis[stage] = {
                    'latency_seconds': latency,
                    'percentage_of_total': percentage
                }
        
        # Sort by latency impact
        self.bottleneck_analysis = dict(sorted(
            self.bottleneck_analysis.items(),
            key=lambda x: x[1]['percentage_of_total'],
            reverse=True
        ))

def main():
    """Run benchmark and display results"""
    benchmark = LatencyBenchmark()
    results = benchmark.run_full_pipeline()
    
    print("\n" + "=" * 60)
    print("LATENCY BENCHMARK RESULTS")
    print("=" * 60)
    
    print(f"\nTotal pipeline latency: {results['latencies']['total_pipeline']:.4f}s")
    print(f"Data processed: {results['data_shape'][0]} rows")
    print(f"Signals generated: {results['signals_generated']}")
    print(f"Orders placed: {results['orders_placed']}")
    
    print("\n--- Stage-by-Stage Latencies ---")
    for stage, latency in results['latencies'].items():
        if stage != 'total_pipeline':
            print(f"{stage:25}: {latency:.4f}s")
    
    print("\n--- BOTTLENECK ANALYSIS ---")
    for stage, analysis in results['bottleneck_analysis'].items():
        print(f"{stage:25}: {analysis['latency_seconds']:.4f}s ({analysis['percentage_of_total']:.1f}%)")
    
    # Identify optimization opportunities
    print("\n--- OPTIMIZATION RECOMMENDATIONS ---")
    bottlenecks = list(results['bottleneck_analysis'].items())
    
    if bottlenecks:
        top_bottleneck = bottlenecks[0]
        print(f"1. TOP BOTTLENECK: {top_bottleneck[0]} ({top_bottleneck[1]['percentage_of_total']:.1f}% of total)")
        
        if 'feature_calculation' in [b[0] for b in bottlenecks[:2]]:
            print("2. Feature Calculation: Implement caching and parallel processing")
        
        if 'strategy_execution' in [b[0] for b in bottlenecks[:2]]:
            print("3. Strategy Execution: Vectorize operations, reduce loops")
        
        if 'order_placement' in [b[0] for b in bottlenecks[:2]]:
            print("4. Order Placement: Use async I/O, connection pooling")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
```
**