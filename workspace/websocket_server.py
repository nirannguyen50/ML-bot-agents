"""
WebSocket Server for Real-time Trading Metrics
DevOps: ML Trading Bot Team
Purpose: Stream live P&L, Sharpe ratio, drawdowns, execution metrics
"""

import asyncio
import websockets
import json
import time
from typing import Dict, Any
import threading
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingMetricsWebSocket:
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.metrics = {
            "pnl": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "current_drawdown": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "avg_trade_duration": 0.0,
            "order_execution_latency": 0.0,
            "timestamp": datetime.now().isoformat()
        }
        self.server = None
        
    def update_metrics(self, new_metrics: Dict[str, Any]):
        """Update metrics from paper trading system"""
        self.metrics.update(new_metrics)
        self.metrics["timestamp"] = datetime.now().isoformat()
        logger.info(f"Metrics updated: {new_metrics}")
        
    async def handler(self, websocket, path):
        """Handle WebSocket connections"""
        self.clients.add(websocket)
        logger.info(f"New WebSocket client connected. Total clients: {len(self.clients)}")
        
        try:
            # Send initial metrics
            await websocket.send(json.dumps(self.metrics))
            
            # Keep connection alive and broadcast updates
            while True:
                # Simulate receiving updates from paper trading system
                # In production, this would connect to actual trading system
                await asyncio.sleep(3)  # Update every 3 seconds
                
                # Broadcast to all connected clients
                if self.clients:
                    message = json.dumps(self.metrics)
                    await asyncio.gather(
                        *[client.send(message) for client in self.clients]
                    )
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        finally:
            self.clients.remove(websocket)
            
    async def start_server(self):
        """Start WebSocket server"""
        self.server = await websockets.serve(self.handler, self.host, self.port)
        logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
        await self.server.wait_closed()
        
    def run(self):
        """Run server in background thread"""
        asyncio.run(self.start_server())
        
    def start_in_thread(self):
        """Start WebSocket server in separate thread"""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        logger.info("WebSocket server started in background thread")
        return thread

# Singleton instance
websocket_server = TradingMetricsWebSocket()

def start_websocket_server():
    """Start the WebSocket server"""
    return websocket_server.start_in_thread()

def update_trading_metrics(metrics: Dict[str, Any]):
    """Update metrics from paper trading system (call this from trading engine)"""
    websocket_server.update_metrics(metrics)

if __name__ == "__main__":
    # For testing
    server = TradingMetricsWebSocket()
    server.start_in_thread()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down WebSocket server")