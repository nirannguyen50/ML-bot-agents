**
```bash
#!/bin/bash
# DevOps: Trading Bot Monitoring Startup Script

echo "🔧 Starting ML Trading Bot Monitoring System"
echo "============================================"

# Check Python dependencies
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Install monitoring dependencies
echo "📦 Installing dashboard dependencies..."
pip install -r requirements_monitoring.txt

# Start WebSocket mock server (if paper trading not running)
echo "🌐 Starting WebSocket mock server..."
python3 -c "
import asyncio
import websockets
import json
from datetime import datetime
import random

async def mock_paper_trading(websocket):
    '''Mock paper trading WebSocket server'''
    print('Paper trading WebSocket running on ws://localhost:8765')
    while True:
        data = {
            'timestamp': datetime.now().isoformat(),
            'pnl': random.uniform(-50, 200),
            'sharpe': random.uniform(-0.5, 2.5),
            'drawdown': random.uniform(0, 20),
            'trade_count': random.randint(0, 10),
            'execution_latency': random.uniform(10, 200),
            'win_rate': random.uniform(45, 85)
        }
        await websocket.send(json.dumps(data))
        await asyncio.sleep(1)

async def main():
    async with websockets.serve(mock_paper_trading, 'localhost', 8765):
        await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(main())
" &

# Start real-time dashboard
echo "📊 Launching monitoring dashboard on http://localhost:8050"
cd src/monitoring
python3 dashboard.py

# Monitor process health
echo "✅ Monitoring system started"
echo "📈 Access dashboard: http://localhost:8050"
echo "📡 WebSocket stream: ws://localhost:8765"
```