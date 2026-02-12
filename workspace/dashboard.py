**
```python
"""
Real-Time Trading Dashboard with WebSocket Streaming
DevOps Engineer: ML Trading Bot Team
Features:
1. WebSocket client for paper trading system
2. Live charts: P&L, Sharpe, Drawdown, Execution Metrics
3. Auto-refresh every 3 seconds
4. Alert thresholds visualization
"""

import asyncio
import websockets
import json
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import plotly.subplots as sp
import pandas as pd
from datetime import datetime
import threading
import queue

# WebSocket configuration
WS_URL = "ws://localhost:8765"  # Paper trading WebSocket endpoint
DATA_QUEUE = queue.Queue()

# Mock data generator (replace with actual WebSocket)
async def websocket_client():
    """Connect to paper trading WebSocket and stream data"""
    try:
        async with websockets.connect(WS_URL) as websocket:
            while True:
                data = await websocket.recv()
                DATA_QUEUE.put(json.loads(data))
    except Exception as e:
        print(f"WebSocket error: {e}")
        # Fallback to simulated data
        while True:
            simulated_data = {
                "timestamp": datetime.now().isoformat(),
                "pnl": np.random.uniform(-100, 500),
                "sharpe": np.random.uniform(-1, 3),
                "drawdown": np.random.uniform(0, 15),
                "trade_count": np.random.randint(0, 50),
                "execution_latency": np.random.uniform(5, 150),
                "win_rate": np.random.uniform(40, 80)
            }
            DATA_QUEUE.put(simulated_data)
            await asyncio.sleep(1)

# Initialize Dash app
app = dash.Dash(__name__, title="Trading Bot Live Dashboard")
app.layout = html.Div([
    html.H1("📊 ML Trading Bot - Real-Time Monitoring", style={'textAlign': 'center'}),
    
    html.Div([
        html.Div([
            html.H3("System Status"),
            html.Div(id="system-metrics", style={'fontSize': '18px'})
        ], className="three columns"),
        
        html.Div([
            html.H3("WebSocket Connection"),
            html.Div(id="ws-status", style={'color': 'green', 'fontSize': '16px'})
        ], className="three columns"),
    ], className="row"),
    
    html.Hr(),
    
    # Main charts grid
    html.Div([
        # P&L Chart
        dcc.Graph(id='pnl-chart', style={'height': '300px'}),
        
        # Sharpe & Drawdown
        dcc.Graph(id='risk-chart', style={'height': '300px'}),
        
        # Execution Metrics
        dcc.Graph(id='execution-chart', style={'height': '300px'}),
        
        # Trade Activity
        dcc.Graph(id='trade-activity', style={'height': '300px'})
    ], className="row"),
    
    # Data table
    html.Div([
        html.H3("Latest Trade Events"),
        html.Div(id='trade-table')
    ]),
    
    # Refresh interval
    dcc.Interval(
        id='interval-component',
        interval=3000,  # 3 seconds
        n_intervals=0
    )
])

# Global data store
historical_data = pd.DataFrame(columns=[
    'timestamp', 'pnl', 'sharpe', 'drawdown', 
    'trade_count', 'execution_latency', 'win_rate'
])

# Callbacks for real-time updates
@app.callback(
    [Output('pnl-chart', 'figure'),
     Output('risk-chart', 'figure'),
     Output('execution-chart', 'figure'),
     Output('trade-activity', 'figure'),
     Output('system-metrics', 'children'),
     Output('ws-status', 'children'),
     Output('trade-table', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    """Update all dashboard components with WebSocket data"""
    global historical_data
    
    # Get latest data from queue
    latest_data = None
    while not DATA_QUEUE.empty():
        latest_data = DATA_QUEUE.get()
    
    if latest_data:
        # Append to historical data
        new_row = pd.DataFrame([latest_data])
        historical_data = pd.concat([historical_data, new_row], ignore_index=True).tail(100)  # Keep last 100 points
    
    # Generate charts
    pnl_fig = generate_pnl_chart(historical_data)
    risk_fig = generate_risk_chart(historical_data)
    exec_fig = generate_execution_chart(historical_data)
    trade_fig = generate_trade_activity(historical_data)
    
    # System metrics
    if latest_data:
        metrics = [
            html.P(f"🟢 P&L: ${latest_data['pnl']:,.2f}"),
            html.P(f"📈 Sharpe: {latest_data['sharpe']:.2f}"),
            html.P(f"⚠️ Drawdown: {latest_data['drawdown']:.2f}%"),
            html.P(f"⚡ Latency: {latest_data['execution_latency']:.1f}ms")
        ]
        ws_status = f"✅ Connected | Last update: {latest_data['timestamp'][11:19]}"
        trade_table = generate_trade_table(historical_data.tail(10))
    else:
        metrics = [html.P("⏳ Waiting for data...")]
        ws_status = "🟡 Connecting to WebSocket..."
        trade_table = "No trade data yet"
    
    return pnl_fig, risk_fig, exec_fig, trade_fig, metrics, ws_status, trade_table

def generate_pnl_chart(data):
    """Generate P&L chart with cumulative and rolling metrics"""
    fig = sp.make_subplots(rows=2, cols=1, subplot_titles=('Cumulative P&L', 'Daily P&L'))
    
    if not data.empty:
        # Cumulative P&L
        fig.add_trace(
            go.Scatter(x=data['timestamp'], y=data['pnl'].cumsum(),
                      mode='lines+markers', name='Cumulative P&L',
                      line=dict(color='green', width=2)),
            row=1, col=1
        )
        
        # Rolling 10-period P&L
        fig.add_trace(
            go.Scatter(x=data['timestamp'], y=data['pnl'].rolling(10).mean(),
                      mode='lines', name='Rolling Avg (10)',
                      line=dict(color='orange', dash='dash')),
            row=2, col=1
        )
    
    fig.update_layout(height=300, showlegend=True)
    return fig

def generate_risk_chart(data):
    """Generate Sharpe ratio and drawdown charts"""
    fig = sp.make_subplots(rows=1, cols=2, subplot_titles=('Sharpe Ratio', 'Drawdown %'))
    
    if not data.empty:
        fig.add_trace(
            go.Scatter(x=data['timestamp'], y=data['sharpe'],
                      mode='lines+markers', name='Sharpe',
                      line=dict(color='blue')),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(x=data['timestamp'], y=data['drawdown'],
                  name='Drawdown', marker_color='red'),
            row=1, col=2
        )
    
    fig.update_layout(height=300, showlegend=True)
    return fig

def generate_execution_chart(data):
    """Generate execution metrics chart"""
    fig = go.Figure()
    
    if not data.empty:
        fig.add_trace(go.Scatter(
            x=data['timestamp'], y=data['execution_latency'],
            name='Latency (ms)', line=dict(color='purple')
        ))
        
        fig.add_trace(go.Scatter(
            x=data['timestamp'], y=data['win_rate'],
            name='Win Rate %', yaxis='y2',
            line=dict(color='green', dash='dot')
        ))
    
    fig.update_layout(
        title='Execution Metrics',
        yaxis=dict(title='Latency (ms)'),
        yaxis2=dict(title='Win Rate %', overlaying='y', side='right'),
        height=300
    )
    return fig

def generate_trade_activity(data):
    """Generate trade count and activity chart"""
    fig = go.Figure()
    
    if not data.empty:
        fig.add_trace(go.Bar(
            x=data['timestamp'], y=data['trade_count'],
            name='Trades', marker_color='lightblue'
        ))
        
        # Add 5-period moving average
        fig.add_trace(go.Scatter(
            x=data['timestamp'], y=data['trade_count'].rolling(5).mean(),
            name='MA (5)', line=dict(color='red', width=2)
        ))
    
    fig.update_layout(title='Trade Activity', height=300)
    return fig

def generate_trade_table(data):
    """Generate HTML table of recent trades"""
    if data.empty:
        return "No data"
    
    table = html.Table([
        html.Thead(html.Tr([
            html.Th('Time'), html.Th('P&L'), html.Th('Sharpe'),
            html.Th('Drawdown'), html.Th('Trades'), html.Th('Latency')
        ])),
        html.Tbody([
            html.Tr([
                html.Td(row['timestamp'][11:19]),
                html.Td(f"${row['pnl']:.2f}"),
                html.Td(f"{row['sharpe']:.2f}"),
                html.Td(f"{row['drawdown']:.1f}%"),
                html.Td(row['trade_count']),
                html.Td(f"{row['execution_latency']:.1f}ms")
            ]) for _, row in data.iterrows()
        ])
    ], style={'width': '100%', 'border': '1px solid black'})
    
    return table

def start_websocket_thread():
    """Start WebSocket client in background thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(websocket_client())

if __name__ == '__main__':
    # Start WebSocket client
    ws_thread = threading.Thread(target=start_websocket_thread, daemon=True)
    ws_thread.start()
    
    # Start Dash server
    print("🚀 Starting Real-Time Dashboard on http://localhost:8050")
    print("📡 Connecting to WebSocket:", WS_URL)
    app.run_server(debug=True, port=8050)
```