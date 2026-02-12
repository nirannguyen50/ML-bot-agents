#!/usr/bin/env python3
"""
Kafka Consumer for Real-time Signal Generation
Target: < 50ms processing latency
"""
import json
import time
from datetime import datetime
from kafka import KafkaConsumer
from typing import Dict, Any, List
import threading
from collections import deque

class SignalGeneratorConsumer:
    def __init__(self, bootstrap_servers='localhost:9092'):
        self.consumer = KafkaConsumer(
            'market_data',
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=True,
            max_poll_records=100,  # Batch processing for efficiency
            fetch_max_wait_ms=100,
            fetch_min_bytes=1
        )
        
        self.metrics = {
            'messages_processed': 0,
            'processing_latency_total': 0,
            'end_to_end_latency_total': 0,
            'signals_generated': 0,
            'window_size': 100  # For moving average calculation
        }
        
        self.price_window = deque(maxlen=100)
        self.monitoring_thread = None
        self.running = False
        
    def calculate_signal(self, tick_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading signal from market data"""
        start_process = time.perf_counter_ns()
        
        # Simple moving average strategy (replace with actual ML model)
        self.price_window.append(tick_data['price'])
        
        if len(self.price_window) >= 20:
            ma_short = sum(list(self.price_window)[-20:]) / 20
            ma_long = sum(list(self.price_window)[-50:]) / 50 if len(self.price_window) >= 50 else ma_short
            
            signal = 'BUY' if ma_short > ma_long else 'SELL'
            confidence = abs(ma_short - ma_long) / tick_data['price']
        else:
            signal = 'HOLD'
            confidence = 0.0
            
        processing_time = (time.perf_counter_ns() - start_process) / 1_000_000
        
        # Calculate end-to-end latency
        tick_time = datetime.fromisoformat(tick_data['timestamp'].replace('Z', '+00:00'))
        e2e_latency = (datetime.utcnow() - tick_time).total_seconds() * 1000
        
        signal_data = {
            'symbol': tick_data['symbol'],
            'price': tick_data['price'],
            'signal': signal,
            'confidence': confidence,
            'processing_latency_ms': processing_time,
            'e2e_latency_ms': e2e_latency,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Update metrics
        self.metrics['messages_processed'] += 1
        self.metrics['processing_latency_total'] += processing_time
        self.metrics['end_to_end_latency_total'] += e2e_latency
        self.metrics['signals_generated'] += 1
        
        if e2e_latency > 100:
            print(f"🚨 HIGH LATENCY ALERT: {e2e_latency:.2f}ms - Investigate immediately!")
            
        return signal_data
    
    def start_monitoring(self):
        """Start background monitoring thread"""
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitoring_thread.start()
        
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.running:
            time.sleep(5)
            metrics = self.get_metrics()
            print(f"\n📈 Stream Metrics: {json.dumps(metrics, indent=2)}")
            
    def consume_messages(self):
        """Main consumption loop"""
        print("🚀 Starting Kafka consumer for signal generation...")
        self.start_monitoring()
        
        try:
            for message in self.consumer:
                tick_data = message.value
                
                # Process and generate signal
                signal = self.calculate_signal(tick_data)
                
                # In production: send to execution engine
                print(f"📢 Signal: {signal['symbol']} {signal['signal']} "
                      f"(confidence: {signal['confidence']:.4f}, "
                      f"E2E: {signal['e2e_latency_ms']:.2f}ms)")
                
        except KeyboardInterrupt:
            print("\n🛑 Shutting down consumer...")
        finally:
            self.running = False
            self.consumer.close()
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get consumer performance metrics"""
        processed = self.metrics['messages_processed']
        return {
            'messages_processed': processed,
            'avg_processing_latency_ms': (self.metrics['processing_latency_total'] / processed 
                                         if processed > 0 else 0),
            'avg_e2e_latency_ms': (self.metrics['end_to_end_latency_total'] / processed 
                                  if processed > 0 else 0),
            'signals_generated': self.metrics['signals_generated'],
            'throughput_msg_sec': processed / 60 if processed > 0 else 0,
            'health_status': 'HEALTHY' if self.metrics['end_to_end_latency_total'] / max(1, processed) < 100 else 'WARNING',
            'timestamp': datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    consumer = SignalGeneratorConsumer()
    consumer.consume_messages()