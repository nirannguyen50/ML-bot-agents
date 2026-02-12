#!/usr/bin/env python3
"""
Streaming Pipeline Setup for ML Trading Bot
Target: <100ms latency from ingestion to signal generation
"""

import time
import json
import asyncio
from datetime import datetime
import numpy as np
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import threading

class TradingStreamEngine:
    """Low-latency streaming engine for market data"""
    
    def __init__(self, bootstrap_servers='localhost:9092'):
        self.bootstrap_servers = bootstrap_servers
        self.latency_metrics = []
        self.producer = None
        self.consumer = None
        self.setup_kafka()
        
    def setup_kafka(self):
        """Initialize Kafka producer and consumer"""
        try:
            # Producer for market data
            self.producer = KafkaProducer(
                bootstrap_servers=[self.bootstrap_servers],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            
            # Consumer for signal processing
            self.consumer = KafkaConsumer(
                'market-data',
                bootstrap_servers=[self.bootstrap_servers],
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='trading-bot-group'
            )
            
            print("✅ Kafka streaming engine initialized")
            return True
        except KafkaError as e:
            print(f"❌ Kafka setup failed: {e}")
            return False
    
    def produce_market_data(self, symbol, price, volume, timestamp):
        """Produce market data with nanosecond precision"""
        start_time = time.time_ns()
        
        message = {
            'symbol': symbol,
            'price': float(price),
            'volume': int(volume),
            'timestamp': timestamp,
            'ingestion_time': start_time
        }
        
        future = self.producer.send('market-data', value=message)
        
        try:
            record_metadata = future.get(timeout=10)
            send_time = time.time_ns()
            send_latency = (send_time - start_time) / 1_000_000  # Convert to ms
            
            self.latency_metrics.append({
                'type': 'produce_latency',
                'value': send_latency,
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"📤 Produced to {record_metadata.topic}[{record_metadata.partition}] "
                  f"offset {record_metadata.offset} | Latency: {send_latency:.2f}ms")
            
            return True, send_latency
        except KafkaError as e:
            print(f"❌ Production failed: {e}")
            return False, None
    
    def consume_and_process(self):
        """Consume and process streaming data"""
        print("🚀 Starting streaming consumer...")
        
        for message in self.consumer:
            start_processing = time.time_ns()
            
            data = message.value
            ingestion_time = data.get('ingestion_time', start_processing)
            
            # Simulate signal generation
            signal = self.generate_trading_signal(data)
            
            end_processing = time.time_ns()
            
            # Calculate latencies
            processing_latency = (end_processing - start_processing) / 1_000_000
            total_latency = (end_processing - ingestion_time) / 1_000_000
            
            # Store metrics
            self.latency_metrics.append({
                'type': 'processing_latency',
                'value': processing_latency,
                'timestamp': datetime.now().isoformat()
            })
            
            self.latency_metrics.append({
                'type': 'end_to_end_latency',
                'value': total_latency,
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"📥 Processed {data['symbol']}: ${data['price']} | "
                  f"Processing: {processing_latency:.2f}ms | "
                  f"Total: {total_latency:.2f}ms | "
                  f"Signal: {signal}")
            
            # Alert if latency exceeds threshold
            if total_latency > 100:
                print(f"⚠️  LATENCY ALERT: {total_latency:.2f}ms > 100ms threshold!")
    
    def generate_trading_signal(self, data):
        """Generate trading signal from market data"""
        # Simple momentum signal for demo
        price = data['price']
        volume = data['volume']
        
        if volume > 1000 and price > 100:
            return 'BUY'
        elif volume > 1000 and price < 95:
            return 'SELL'
        else:
            return 'HOLD'
    
    def get_latency_stats(self):
        """Calculate latency statistics"""
        if not self.latency_metrics:
            return None
        
        end_to_end = [m['value'] for m in self.latency_metrics if m['type'] == 'end_to_end_latency']
        
        if not end_to_end:
            return None
        
        return {
            'avg_latency': np.mean(end_to_end),
            'p95_latency': np.percentile(end_to_end, 95),
            'p99_latency': np.percentile(end_to_end, 99),
            'max_latency': np.max(end_to_end),
            'min_latency': np.min(end_to_end),
            'sample_count': len(end_to_end)
        }

def performance_test():
    """Run latency performance test"""
    print("🔬 Running streaming performance test...")
    
    engine = TradingStreamEngine()
    
    if not engine.producer:
        print("❌ Cannot run test - Kafka not available")
        return
    
    # Start consumer in background thread
    consumer_thread = threading.Thread(target=engine.consume_and_process, daemon=True)
    consumer_thread.start()
    
    # Produce test messages
    test_messages = 100
    latencies = []
    
    for i in range(test_messages):
        success, latency = engine.produce_market_data(
            symbol='AAPL',
            price=150 + np.random.randn() * 5,
            volume=1000 + np.random.randint(-200, 200),
            timestamp=datetime.now().isoformat()
        )
        
        if success and latency:
            latencies.append(latency)
        
        time.sleep(0.01)  # 10ms between messages
    
    # Wait for processing
    time.sleep(2)
    
    # Get statistics
    stats = engine.get_latency_stats()
    
    print("\n" + "="*60)
    print("📊 STREAMING PERFORMANCE REPORT")
    print("="*60)
    
    if stats:
        print(f"✅ End-to-End Latency Statistics:")
        print(f"   Average: {stats['avg_latency']:.2f}ms")
        print(f"   P95: {stats['p95_latency']:.2f}ms")
        print(f"   P99: {stats['p99_latency']:.2f}ms")
        print(f"   Max: {stats['max_latency']:.2f}ms")
        print(f"   Min: {stats['min_latency']:.2f}ms")
        print(f"   Samples: {stats['sample_count']}")
        
        # Check if target achieved
        if stats['p95_latency'] <= 100:
            print(f"🎯 TARGET ACHIEVED: P95 latency < 100ms")
        else:
            print(f"⚠️  TARGET MISSED: P95 latency > 100ms")
    else:
        print("❌ No latency data collected")
    
    print("="*60)

if __name__ == "__main__":
    performance_test()