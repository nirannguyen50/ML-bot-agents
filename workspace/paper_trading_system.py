"""
Paper Trading System - Cloud Deployment Ready
Version: 2.0
Deployment: AWS/GCP with Auto-scaling
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import boto3
import pandas as pd
from decimal import Decimal
import aioboto3

class PaperTradingSystem:
    """Paper trading system with cloud-native architecture"""
    
    def __init__(self, region: str = 'ap-southeast-1'):
        self.region = region
        self.portfolio = {}
        self.open_positions = {}
        self.cash_balance = Decimal('100000.00')  # Starting capital
        self.trade_history = []
        
        # AWS clients
        self.kinesis_client = None
        self.dynamodb_client = None
        self.sqs_client = None
        
    async def initialize_aws_clients(self):
        """Initialize AWS service clients with async support"""
        session = aioboto3.Session()
        self.kinesis_client = session.client('kinesis', region_name=self.region)
        self.dynamodb_client = session.client('dynamodb', region_name=self.region)
        self.sqs_client = session.client('sqs', region_name=self.region)
        
    async def consume_market_data(self, stream_name: str = 'market-data-stream'):
        """Consume real-time market data from Kinesis"""
        try:
            response = await self.kinesis_client.describe_stream(StreamName=stream_name)
            shard_id = response['StreamDescription']['Shards'][0]['ShardId']
            
            shard_iterator_response = await self.kinesis_client.get_shard_iterator(
                StreamName=stream_name,
                ShardId=shard_id,
                ShardIteratorType='LATEST'
            )
            
            shard_iterator = shard_iterator_response['ShardIterator']
            
            while True:
                records_response = await self.kinesis_client.get_records(ShardIterator=shard_iterator)
                records = records_response['Records']
                
                for record in records:
                    market_data = json.loads(record['Data'].decode('utf-8'))
                    await self.process_market_data(market_data)
                
                shard_iterator = records_response['NextShardIterator']
                await asyncio.sleep(0.1)  # Prevent throttling
                
        except Exception as e:
            print(f"Error consuming market data: {e}")
            raise
    
    async def process_market_data(self, market_data: Dict):
        """Process incoming market data and execute paper trades"""
        symbol = market_data.get('symbol')
        price = Decimal(str(market_data.get('price', 0)))
        timestamp = market_data.get('timestamp')
        
        # Trading logic based on SMA strategy
        if symbol and price > 0:
            # Check for trading signals (simplified)
            signal = await self.generate_trading_signal(symbol, price)
            
            if signal == 'BUY' and self.cash_balance >= price * Decimal('10'):
                await self.execute_paper_trade(symbol, 'BUY', 10, price, timestamp)
            elif signal == 'SELL' and symbol in self.open_positions:
                await self.execute_paper_trade(symbol, 'SELL', 10, price, timestamp)
    
    async def generate_trading_signal(self, symbol: str, current_price: Decimal) -> str:
        """Generate trading signal based on strategy"""
        # Simplified signal generation
        # In production, integrate with ML models from other agents
        return 'BUY' if current_price % Decimal('2') == 0 else 'HOLD'
    
    async def execute_paper_trade(self, symbol: str, action: str, 
                                 quantity: int, price: Decimal, timestamp: str):
        """Execute paper trade and update portfolio"""
        trade_value = price * Decimal(str(quantity))
        
        if action == 'BUY':
            self.cash_balance -= trade_value
            if symbol in self.open_positions:
                self.open_positions[symbol]['quantity'] += quantity
                self.open_positions[symbol]['avg_price'] = (
                    (self.open_positions[symbol]['avg_price'] * 
                     self.open_positions[symbol]['quantity'] + trade_value) /
                    (self.open_positions[symbol]['quantity'] + quantity)
                )
            else:
                self.open_positions[symbol] = {
                    'quantity': quantity,
                    'avg_price': price,
                    'entry_time': timestamp
                }
        elif action == 'SELL':
            self.cash_balance += trade_value
            if symbol in self.open_positions:
                self.open_positions[symbol]['quantity'] -= quantity
                if self.open_positions[symbol]['quantity'] <= 0:
                    del self.open_positions[symbol]
        
        # Record trade
        trade_record = {
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': float(price),
            'timestamp': timestamp,
            'cash_balance': float(self.cash_balance),
            'portfolio_value': await self.calculate_portfolio_value(current_price=price)
        }
        
        self.trade_history.append(trade_record)
        
        # Send to SQS for async processing
        await self.send_to_monitoring(trade_record)
        
        print(f"Paper Trade Executed: {action} {quantity} {symbol} @ {price}")
    
    async def calculate_portfolio_value(self, current_price: Decimal = None) -> float:
        """Calculate total portfolio value"""
        positions_value = Decimal('0.00')
        for symbol, position in self.open_positions.items():
            if current_price and symbol == list(self.open_positions.keys())[0]:
                price = current_price
            else:
                price = position['avg_price']  # Fallback
            positions_value += Decimal(str(price)) * Decimal(str(position['quantity']))
        
        return float(self.cash_balance + positions_value)
    
    async def send_to_monitoring(self, trade_data: Dict):
        """Send trade data to monitoring system via SQS"""
        if self.sqs_client:
            queue_url = f"https://sqs.{self.region}.amazonaws.com/account-id/trade-monitoring-queue"
            
            await self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(trade_data),
                MessageAttributes={
                    'Service': {
                        'StringValue': 'PaperTrading',
                        'DataType': 'String'
                    }
                }
            )
    
    async def save_to_dynamodb(self, table_name: str = 'PaperTradingPortfolio'):
        """Save portfolio state to DynamoDB"""
        if self.dynamodb_client:
            item = {
                'timestamp': {'S': datetime.utcnow().isoformat()},
                'cash_balance': {'N': str(self.cash_balance)},
                'portfolio_value': {'N': str(await self.calculate_portfolio_value())},
                'open_positions': {'S': json.dumps(self.open_positions)},
                'trade_count': {'N': str(len(self.trade_history))}
            }
            
            await self.dynamodb_client.put_item(
                TableName=table_name,
                Item=item
            )

async def main():
    """Main entry point for paper trading system"""
    print("Starting Paper Trading System...")
    
    # Initialize system
    system = PaperTradingSystem(region='ap-southeast-1')
    await system.initialize_aws_clients()
    
    # Start consuming market data
    print("Connecting to real-time market data feed...")
    await system.consume_market_data()
    
    # Periodic portfolio save (every 5 minutes)
    async def periodic_save():
        while True:
            await system.save_to_dynamodb()
            print(f"Portfolio saved. Current value: {system.calculate_portfolio_value()}")
            await asyncio.sleep(300)  # 5 minutes
    
    # Run both tasks concurrently
    await asyncio.gather(
        system.consume_market_data(),
        periodic_save()
    )

if __name__ == "__main__":
    asyncio.run(main())