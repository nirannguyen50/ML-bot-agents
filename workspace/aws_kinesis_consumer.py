import boto3
import json
from typing import Dict, Any
import asyncio

class KinesisDataFeed:
    def __init__(self, stream_name: str):
        self.client = boto3.client('kinesis', region_name='ap-southeast-1')
        self.stream_name = stream_name
        
    async def consume_market_data(self):
        """Consume real-time market data from Kinesis"""
        response = self.client.get_shard_iterator(
            StreamName=self.stream_name,
            ShardId='shardId-000000000000',
            ShardIteratorType='LATEST'
        )
        
        shard_iterator = response['ShardIterator']
        
        while True:
            try:
                response = self.client.get_records(ShardIterator=shard_iterator)
                records = response['Records']
                
                for record in records:
                    data = json.loads(record['Data'].decode('utf-8'))
                    # Process market data
                    print(f"Received: {data['symbol']} @ {data['price']}")
                    
                shard_iterator = response['NextShardIterator']
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Data feed error: {e}")
                await asyncio.sleep(1)