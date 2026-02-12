```python
"""
Enhanced Metrics Collector with ML-ready data export
Version: 2.0 - Predictive Monitoring Foundation
"""

import psutil
import time
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

class PredictiveMetricsCollector:
    def __init__(self, data_dir="data/metrics"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # ML features configuration
        self.features = {
            'system': ['cpu_percent', 'ram_percent', 'disk_io_read', 'disk_io_write'],
            'trading': ['order_latency_ms', 'api_response_ms', 'queue_size'],
            'network': ['latency_ms', 'packet_loss']
        }
        
        self.history_file = self.data_dir / "metrics_history.csv"
        self.load_historical_data()
    
    def load_historical_data(self):
        """Load existing metrics for ML training"""
        if self.history_file.exists():
            self.historical_df = pd.read_csv(self.history_file, parse_dates=['timestamp'])
            print(f"Loaded {len(self.historical_df)} historical records")
        else:
            self.historical_df = pd.DataFrame()
    
    def collect_system_metrics(self):
        """Collect comprehensive system metrics"""
        metrics = {
            'timestamp': datetime.now(),
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'ram_percent': psutil.virtual_memory().percent,
            'ram_available_gb': psutil.virtual_memory().available / 1e9,
            'disk_usage_percent': psutil.disk_usage('/').percent,
            'disk_io_read': psutil.disk_io_counters().read_bytes if psutil.disk_io_counters() else 0,
            'disk_io_write': psutil.disk_io_counters().write_bytes if psutil.disk_io_counters() else 0,
            'network_sent_mb': psutil.net_io_counters().bytes_sent / 1e6,
            'network_recv_mb': psutil.net_io_counters().bytes_recv / 1e6,
            'process_count': len(psutil.pids()),
            'load_avg_1min': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
        }
        return metrics
    
    def collect_trading_metrics(self):
        """Simulated trading metrics - to be integrated with actual trading system"""
        # Placeholder - replace with actual trading system integration
        return {
            'order_latency_ms': np.random.normal(50, 10),  # Simulated latency
            'api_response_ms': np.random.normal(30, 5),
            'queue_size': np.random.randint(0, 100),
            'active_strategies': 3,
            'errors_last_hour': 0
        }
    
    def collect_all_metrics(self):
        """Collect all metrics and save to history"""
        system_metrics = self.collect_system_metrics()
        trading_metrics = self.collect_trading_metrics()
        
        all_metrics = {**system_metrics, **trading_metrics}
        
        # Append to historical data
        new_row = pd.DataFrame([all_metrics])
        self.historical_df = pd.concat([self.historical_df, new_row], ignore_index=True)
        
        # Keep last 90 days for ML training
        cutoff = datetime.now() - timedelta(days=90)
        self.historical_df = self.historical_df[self.historical_df['timestamp'] > cutoff]
        
        # Save to CSV
        self.historical_df.to_csv(self.history_file, index=False)
        
        return all_metrics
    
    def export_ml_dataset(self, window_hours=24):
        """Export formatted dataset for ML training"""
        if len(self.historical_df) < 100:  # Minimum records
            print("Insufficient data for ML training")
            return None
        
        # Create rolling features
        df = self.historical_df.copy()
        df.set_index('timestamp', inplace=True)
        
        # Rolling statistics for anomaly detection
        for col in ['cpu_percent', 'ram_percent', 'order_latency_ms']:
            df[f'{col}_rolling_mean_1h'] = df[col].rolling('1h').mean()
            df[f'{col}_rolling_std_1h'] = df[col].rolling('1h').std()
            df[f'{col}_zscore'] = (df[col] - df[f'{col}_rolling_mean_1h']) / df[f'{col}_rolling_std_1h'].replace(0, 1)
        
        # Label anomalies (simple threshold for now)
        df['anomaly_label'] = ((df['cpu_percent'] > 85) | 
                               (df['ram_percent'] > 90) | 
                               (df['order_latency_ms'] > 100)).astype(int)
        
        # Export for ML
        ml_file = self.data_dir / "ml_ready_dataset.csv"
        df.reset_index().to_csv(ml_file, index=False)
        print(f"Exported ML dataset to {ml_file} with {len(df)} records")
        
        return ml_file
    
    def run_continuous_collection(self, interval_seconds=5):
        """Continuous metrics collection (for daemon)"""
        print("Starting continuous metrics collection...")
        try:
            while True:
                metrics = self.collect_all_metrics()
                print(f"Collected metrics at {datetime.now():%H:%M:%S}: CPU {metrics['cpu_percent']:.1f}%, RAM {metrics['ram_percent']:.1f}%")
                
                # Export ML dataset every hour
                if datetime.now().minute == 0:  # On the hour
                    self.export_ml_dataset()
                
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("Metrics collection stopped")
            self.export_ml_dataset()

if __name__ == "__main__":
    collector = PredictiveMetricsCollector()
    # Test collection
    test_metrics = collector.collect_all_metrics()
    print(f"Test metrics collected: {json.dumps(test_metrics, default=str, indent=2)}")
    collector.export_ml_dataset()
```