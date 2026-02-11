"""
Web Dashboard — Feature 7
Real-time browser UI showing agents, tasks, pipeline status, and costs.
Run as background thread alongside the pipeline.
"""

import json
import os
import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from flask import Flask, jsonify, render_template_string
except ImportError:
    Flask = None
    logger.info("Flask not installed — dashboard disabled. Run: pip install flask")


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ML Bot Agents — Dashboard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: #0f0f23;
    color: #e0e0e0;
    min-height: 100vh;
}
.header {
    background: linear-gradient(135deg, #1a1a3e 0%, #0f0f23 100%);
    border-bottom: 1px solid #2a2a4a;
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.header h1 { 
    font-size: 20px;
    background: linear-gradient(90deg, #00d4ff, #7b68ee);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.header .status { color: #00ff88; font-size: 14px; }
.grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    padding: 20px;
    max-width: 1400px;
    margin: 0 auto;
}
.card {
    background: #1a1a3e;
    border: 1px solid #2a2a4a;
    border-radius: 12px;
    padding: 20px;
    transition: border-color 0.3s;
}
.card:hover { border-color: #7b68ee; }
.card h2 {
    font-size: 16px;
    color: #7b68ee;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.agent-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.agent-card {
    background: #12122a;
    border-radius: 8px;
    padding: 12px;
    border-left: 3px solid #7b68ee;
}
.agent-card .name { font-weight: 600; font-size: 14px; color: #00d4ff; }
.agent-card .role { font-size: 12px; color: #888; margin-top: 2px; }
.agent-card.active { border-left-color: #00ff88; }
.task-list { max-height: 300px; overflow-y: auto; }
.task-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    margin-bottom: 6px;
    background: #12122a;
    border-radius: 6px;
    font-size: 13px;
}
.task-item .badge {
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
}
.badge.done { background: #00ff8820; color: #00ff88; }
.badge.todo { background: #ffaa0020; color: #ffaa00; }
.badge.in_progress { background: #00d4ff20; color: #00d4ff; }
.badge.blocked { background: #ff444420; color: #ff4444; }
.progress-bar {
    width: 100%;
    height: 8px;
    background: #12122a;
    border-radius: 4px;
    overflow: hidden;
    margin: 12px 0;
}
.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #00d4ff, #00ff88);
    border-radius: 4px;
    transition: width 0.5s;
}
.cost-display {
    font-size: 28px;
    font-weight: 700;
    color: #00ff88;
    text-align: center;
    padding: 20px 0;
}
.cost-detail { 
    display: grid; 
    grid-template-columns: 1fr 1fr; 
    gap: 8px;
    font-size: 13px;
}
.cost-detail .label { color: #888; }
.cost-detail .value { color: #e0e0e0; text-align: right; }
.log-area {
    background: #0a0a1a;
    border-radius: 8px;
    padding: 12px;
    font-family: 'Cascadia Code', monospace;
    font-size: 12px;
    max-height: 250px;
    overflow-y: auto;
    line-height: 1.6;
}
.log-area .log-line { color: #888; }
.log-area .log-line.info { color: #00d4ff; }
.log-area .log-line.success { color: #00ff88; }
.log-area .log-line.error { color: #ff4444; }
.log-area .log-line.warning { color: #ffaa00; }
.full-width { grid-column: 1 / -1; }
.vote-item {
    background: #12122a;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
}
.vote-item .title { font-weight: 600; color: #00d4ff; }
.vote-item .meta { font-size: 12px; color: #888; margin-top: 4px; }
.refresh-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #00ff88;
    display: inline-block;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}
</style>
</head>
<body>
<div class="header">
    <h1>🤖 ML Bot Agents Dashboard</h1>
    <div class="status"><span class="refresh-indicator"></span> Live — Auto-refresh 5s</div>
</div>

<div class="grid">
    <!-- Agents -->
    <div class="card">
        <h2>👥 Agents</h2>
        <div class="agent-grid" id="agents">Loading...</div>
    </div>
    
    <!-- Cost Tracker -->
    <div class="card">
        <h2>💰 Cost Tracker</h2>
        <div class="cost-display" id="total-cost">$0.0000</div>
        <div class="cost-detail" id="cost-detail">
            <span class="label">Total Calls:</span><span class="value" id="total-calls">0</span>
            <span class="label">Total Tokens:</span><span class="value" id="total-tokens">0</span>
            <span class="label">Avg/Call:</span><span class="value" id="avg-cost">$0.0000</span>
        </div>
    </div>
    
    <!-- Tasks -->
    <div class="card">
        <h2>📋 Backlog</h2>
        <div class="progress-bar"><div class="progress-fill" id="progress" style="width: 0%"></div></div>
        <div id="progress-text" style="font-size: 13px; color: #888; margin-bottom: 10px;">0/0 tasks</div>
        <div class="task-list" id="tasks">Loading...</div>
    </div>
    
    <!-- Votes -->
    <div class="card">
        <h2>🗳️ Votes</h2>
        <div id="votes">No proposals yet</div>
    </div>
    
    <!-- Logs -->
    <div class="card full-width">
        <h2>📝 Live Logs</h2>
        <div class="log-area" id="logs">Waiting for data...</div>
    </div>
</div>

<script>
async function refresh() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        // Agents
        const agentsHtml = Object.entries(data.agents || {}).map(([name, info]) => 
            `<div class="agent-card active">
                <div class="name">${name}</div>
                <div class="role">${info.status || 'active'}</div>
            </div>`
        ).join('');
        document.getElementById('agents').innerHTML = agentsHtml || '<div>No agents</div>';
        
        // Tasks
        const tasks = data.backlog || [];
        const done = tasks.filter(t => t.status === 'done').length;
        const total = tasks.length;
        const pct = total > 0 ? (done / total * 100) : 0;
        
        document.getElementById('progress').style.width = pct + '%';
        document.getElementById('progress-text').textContent = `${done}/${total} tasks (${pct.toFixed(0)}%)`;
        
        const tasksHtml = tasks.map(t => 
            `<div class="task-item">
                <span>#${t.id} ${t.title} → ${t.assigned_to}</span>
                <span class="badge ${t.status}">${t.status}</span>
            </div>`
        ).join('');
        document.getElementById('tasks').innerHTML = tasksHtml || 'No tasks';
        
        // Cost
        const cost = data.cost || {};
        document.getElementById('total-cost').textContent = `$${(cost.total_cost_usd || 0).toFixed(4)}`;
        document.getElementById('total-calls').textContent = cost.total_calls || 0;
        document.getElementById('total-tokens').textContent = (cost.total_tokens || 0).toLocaleString();
        document.getElementById('avg-cost').textContent = `$${(cost.avg_cost_per_call || 0).toFixed(6)}`;
        
        // Votes
        const votes = data.votes || [];
        const votesHtml = votes.map(v => 
            `<div class="vote-item">
                <div class="title">${v.title}</div>
                <div class="meta">By: ${v.proposer} | Status: ${v.status} | ${v.result || 'Pending'}</div>
            </div>`
        ).join('');
        document.getElementById('votes').innerHTML = votesHtml || 'No proposals yet';
        
        // Logs
        const logs = data.logs || [];
        const logsHtml = logs.slice(-20).map(l => {
            let cls = 'log-line';
            if (l.includes('ERROR')) cls += ' error';
            else if (l.includes('WARNING')) cls += ' warning';
            else if (l.includes('✅') || l.includes('COMPLETE')) cls += ' success';
            else cls += ' info';
            return `<div class="${cls}">${l}</div>`;
        }).join('');
        document.getElementById('logs').innerHTML = logsHtml || 'Waiting...';
        
        // Auto-scroll logs
        const logArea = document.getElementById('logs');
        logArea.scrollTop = logArea.scrollHeight;
        
    } catch (e) {
        console.error('Refresh error:', e);
    }
}

setInterval(refresh, 5000);
refresh();
</script>
</body>
</html>
"""


class Dashboard:
    """Web dashboard for ML Bot Agents"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.data = {
            "agents": {},
            "backlog": [],
            "cost": {},
            "votes": [],
            "logs": [],
            "cycle": 0,
            "pipeline_status": "idle"
        }
        self.app = None
        self.thread = None
        
        if Flask is None:
            logger.warning("Dashboard disabled — Flask not installed")
            return
        
        self.app = Flask(__name__)
        self.app.logger.setLevel(logging.WARNING)  # Suppress Flask logs
        
        @self.app.route('/')
        def index():
            return render_template_string(DASHBOARD_HTML)
        
        @self.app.route('/api/status')
        def api_status():
            return jsonify(self.data)
    
    def start(self):
        """Start dashboard in background thread"""
        if not self.app:
            return
        
        self.thread = threading.Thread(
            target=self.app.run,
            kwargs={"host": "0.0.0.0", "port": self.port, "debug": False, "use_reloader": False},
            daemon=True
        )
        self.thread.start()
        logger.info(f"📊 Dashboard running at http://localhost:{self.port}")
    
    def update_agents(self, agents: dict):
        """Update agent status"""
        self.data["agents"] = {
            name: {"status": "active", "name": name}
            for name in agents.keys()
        }
    
    def update_backlog(self, tasks: list):
        """Update backlog tasks"""
        self.data["backlog"] = tasks
    
    def update_cost(self, cost_report: dict):
        """Update cost information"""
        self.data["cost"] = cost_report
    
    def update_votes(self, proposals: list):
        """Update voting proposals"""
        self.data["votes"] = proposals
    
    def add_log(self, message: str):
        """Add a log entry"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.data["logs"].append(f"[{timestamp}] {message}")
        # Keep last 100 logs
        if len(self.data["logs"]) > 100:
            self.data["logs"] = self.data["logs"][-100:]
    
    def set_cycle(self, cycle: int):
        """Set current cycle number"""
        self.data["cycle"] = cycle
    
    def set_pipeline_status(self, status: str):
        """Set pipeline status"""
        self.data["pipeline_status"] = status
