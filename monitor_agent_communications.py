import http.server
import socketserver
import json
import os
from pathlib import Path
from agent_communication_logger import _logger

PORT = 8080
LOG_DIR = Path("logs/agent_communications")

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/messages":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            messages = []
            try:
                log_file = _logger.log_file
                if log_file.exists():
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            messages.append(json.loads(line))
            except Exception as e:
                print(f"Error reading logs: {e}")
                
            self.wfile.write(json.dumps(messages).encode())
            return
            
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>Agent Monitor</title>
    <style>
        body { font-family: sans-serif; background: #1e1e1e; color: #fff; padding: 20px; }
        .message { background: #2d2d2d; margin: 10px 0; padding: 10px; border-radius: 5px; border-left: 4px solid #007acc; }
        .manager { border-left-color: #ffaa00; }
        .timestamp { color: #888; font-size: 0.8em; }
        .sender { font-weight: bold; color: #4ec9b0; }
    </style>
    <script>
        async function fetchMessages() {
            const res = await fetch('/api/messages');
            const msgs = await res.json();
            const container = document.getElementById('messages');
            container.innerHTML = msgs.map(m => `
                <div class="message ${m.from.includes('Manager') ? 'manager' : ''}">
                    <div class="timestamp">${m.vn_time || ''}</div>
                    <div class="sender">${(m.from || '').replace(/</g,'&lt;')} -> ${(m.to || '').replace(/</g,'&lt;')}</div>
                    <div class="content">${(m.message || '').replace(/</g,'&lt;').replace(/\\n/g,'<br>')}</div>
                </div>
            `).reverse().join('');
        }
        setInterval(fetchMessages, 3000);
        window.onload = fetchMessages;
    </script>
</head>
<body>
    <h1>Agent Communications (AI Powered)</h1>
    <div id="messages">Loading...</div>
</body>
</html>
            """
            self.wfile.write(html.encode("utf-8"))
            return
            
        super().do_GET()

if __name__ == "__main__":
    os.makedirs(LOG_DIR, exist_ok=True)
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()
