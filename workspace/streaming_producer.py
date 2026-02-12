#!/usr/bin/env python3
"""
Kafka Producer for Market Data
Latency target: < 5ms per message
"""
import json
import time
import asyncio
from datetime import datetime
from kafka import KafkaProducer
import pandas as pd
from typing import Dict, Any

class MarketDataProducer:
    def __init__(self, bootstrap_servers='localhost:9092'):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',  # Ensure message durability
            retries=3,
            max_in_flight_requests_per_connection=1,
            compression_type='snappy'  # Reduce network latency
        )
        self.topic = 'market_data'
        self.metrics = {
            'messages_sent': 0,
            'total_latency': 0,
            'last_latency': 0
        }
        
    def produce_tick(self, symbol: str, price: float, volume: float) -> float:
        """Produce a single market tick with latency measurement"""
        start_time = time.perf_counter_ns()
        
        message = {
            'symbol': symbol,
            'price': price,
            'volume': volume,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'kafka_producer'
        }
        
        future = self.producer.send(self.topic, message)
        # Wait for acknowledgment (async in production)
        metadata = future.get(timeout=10)
        
        end_time = time.perf_counter_ns()
        latency_ms = (end_time - start_time) / 1_000_000
        
        # Update metrics
        self.metrics['messages_sent'] += 1
        self.metrics['total_latency'] += latency_ms
        self.metrics['last_latency'] = latency_ms
        
        if latency_ms > 5:
            print(f"⚠️ High producer latency: {latency_ms:.2f}ms")
            
        return latency_ms
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get producer performance metrics"""
        avg_latency = (self.metrics['total_latency'] / self.metrics['messages_sent'] 
                      if self.metrics['messages_sent'] > 0 else 0)
        return {
            **self.metrics,
            'avg_latency_ms': avg_latency,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def close(self):
        self.producer.flush()
        self.producer.close()

if __name__ == "__main__":
    # Test producer
    producer = MarketDataProducer()
    try:
        for i in range(10):
            latency = producer.produce_tick('AAPL', 150.0 + i*0.1, 1000)
            print(f"Message {i+1}: {latency:.2f}ms")
            time.sleep(0.1)
    finally:
        producer.close()
        print(f"\n📊 Final metrics: {producer.get_metrics()}")