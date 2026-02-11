"""
Backend API Server (Flask) for Dashboard
Serves real-time data from JSON files.
"""

import os
import json
import logging
from flask import Flask, jsonify, request, Response

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Data paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # ML-bot-agents/
HEALTH_FILE = os.path.join(BASE_DIR, "agent_health.json")
BACKLOG_FILE = os.path.join(BASE_DIR, "backlog.json")
TRADING_FILE = os.path.join(BASE_DIR, "paper_trading.json")
SHARED_MEMORY_FILE = os.path.join(BASE_DIR, "shared_memory.json")
LOG_FILE = os.path.join(BASE_DIR, "logs", "agents_startup.log")

def read_json_safe(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return {"error": str(e)}
    return {"error": "File not found", "path": filepath}

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get active agents status"""
    return jsonify(read_json_safe(HEALTH_FILE))

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    """Get paper trading portfolio"""
    return jsonify(read_json_safe(TRADING_FILE))

@app.route('/api/backlog', methods=['GET'])
def get_backlog():
    """Get task backlog"""
    return jsonify(read_json_safe(BACKLOG_FILE))

@app.route('/api/memory', methods=['GET'])
def get_memory():
    """Get shared memory insights"""
    return jsonify(read_json_safe(SHARED_MEMORY_FILE))

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get last 50 lines of logs"""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-50:]
            return jsonify({"logs": lines})
        except:
            return jsonify({"logs": ["Error reading logs"]})
    return jsonify({"logs": []})

@app.route('/api/control', methods=['POST'])
def control_system():
    """Control system (placeholder)"""
    action = request.json.get('action')
    # Connect to command pipe or signal in real implementation
    return jsonify({"status": "ok", "action": action})

if __name__ == '__main__':
    print(f"🚀 API Server running on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)
