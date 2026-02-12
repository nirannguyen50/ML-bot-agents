import smtplib
import json
import requests
import logging
from typing import Dict, Any, List
from datetime import datetime
import os

class AlertManager:
    """Unified alerting system for trading bot monitoring"""
    
    def __init__(self, config_path: str = "config/alert_config.json"):
        self.config = self._load_config(config_path)
        self.setup_logging()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load alert configuration"""
        default_config = {
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "",
                "sender_password": "",
                "recipients": []
            },
            "slack": {
                "enabled": False,
                "webhook_url": "",
                "channel": "#trading-alerts"
            },
            "thresholds": {
                "sharpe_ratio": 1.0,
                "max_drawdown": 0.15,
                "cpu_usage": 0.8,
                "memory_usage": 0.85
            }
        }
        
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                # Merge configurations
                for key in default_config:
                    if key in user_config:
                        default_config[key].update(user_config[key])
                return default_config
        except FileNotFoundError:
            print(f"Config file {config_path} not found, using defaults")
            return default_config
    
    def setup_logging(self):
        """Setup alert logging"""
        logging.basicConfig(
            filename='logs/alert.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def send_alert(self, alert_type: str, message: str, data: Dict[str, Any] = None):
        """Send alert through all enabled channels"""
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "message": message,
            "data": data or {}
        }
        
        # Log all alerts
        self.logger.info(f"{alert_type}: {message}")
        
        # Send to enabled channels
        if self.config["email"]["enabled"]:
            self._send_email_alert(alert_data)
        
        if self.config["slack"]["enabled"]:
            self._send_slack_alert(alert_data)
        
        return alert_data
    
    def _send_email_alert(self, alert_data: Dict[str, Any]):
        """Send alert via email"""
        try:
            config = self.config["email"]
            
            subject = f"[TRADING BOT ALERT] {alert_data['type']}"
            body = f"""
            Trading Bot Alert Notification
            ==============================
            
            Time: {alert_data['timestamp']}
            Alert Type: {alert_data['type']}
            Message: {alert_data['message']}
            
            Data:
            {json.dumps(alert_data['data'], indent=2)}
            
            ---
            Automated Alert System
            """
            
            with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
                server.starttls()
                server.login(config["sender_email"], config["sender_password"])
                
                for recipient in config["recipients"]:
                    email_msg = f"Subject: {subject}\n\n{body}"
                    server.sendmail(config["sender_email"], recipient, email_msg)
            
            self.logger.info(f"Email alert sent to {len(config['recipients'])} recipients")
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {str(e)}")
    
    def _send_slack_alert(self, alert_data: Dict[str, Any]):
        """Send alert via Slack webhook"""
        try:
            config = self.config["slack"]
            
            # Determine color based on alert type
            color_map = {
                "CRITICAL": "#FF0000",     # Red
                "WARNING": "#FFA500",      # Orange
                "INFO": "#36A64F",         # Green
                "HEALTH": "#1E90FF"        # Blue
            }
            
            color = color_map.get(alert_data["type"].split("_")[0], "#808080")
            
            slack_payload = {
                "channel": config["channel"],
                "username": "Trading Bot Monitor",
                "icon_emoji": ":robot_face:",
                "attachments": [{
                    "color": color,
                    "title": f"Alert: {alert_data['type']}",
                    "text": alert_data["message"],
                    "fields": [
                        {
                            "title": "Timestamp",
                            "value": alert_data["timestamp"],
                            "short": True
                        }
                    ],
                    "footer": "ML Trading Bot System"
                }]
            }
            
            # Add data fields if present
            if alert_data["data"]:
                for key, value in alert_data["data"].items():
                    slack_payload["attachments"][0]["fields"].append({
                        "title": key,
                        "value": str(value),
                        "short": True
                    })
            
            response = requests.post(
                config["webhook_url"],
                json=slack_payload,
                timeout=10
            )
            
            if response.status_code != 200:
                self.logger.error(f"Slack API error: {response.text}")
            else:
                self.logger.info("Slack alert sent successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {str(e)}")
    
    def check_backtest_metrics(self, metrics: Dict[str, float]):
        """Check backtest metrics against thresholds"""
        alerts = []
        
        # Check Sharpe ratio
        sharpe = metrics.get("sharpe_ratio", 0)
        if sharpe < self.config["thresholds"]["sharpe_ratio"]:
            alerts.append({
                "type": "CRITICAL_BACKTEST",
                "message": f"Sharpe ratio {sharpe:.2f} below threshold {self.config['thresholds']['sharpe_ratio']}",
                "data": metrics
            })
        
        # Check maximum drawdown
        drawdown = abs(metrics.get("max_drawdown", 0))
        if drawdown > self.config["thresholds"]["max_drawdown"]:
            alerts.append({
                "type": "CRITICAL_BACKTEST",
                "message": f"Drawdown {drawdown:.1%} exceeds limit {self.config['thresholds']['max_drawdown']:.1%}",
                "data": metrics
            })
        
        return alerts
    
    def check_health_metrics(self, metrics: Dict[str, float]):
        """Check system health metrics"""
        alerts = []
        
        # Check CPU usage
        cpu = metrics.get("cpu_percent", 0)
        if cpu > self.config["thresholds"]["cpu_usage"] * 100:
            alerts.append({
                "type": "WARNING_HEALTH",
                "message": f"CPU usage {cpu:.1f}% exceeds {self.config['thresholds']['cpu_usage']*100:.0f}% threshold",
                "data": metrics
            })
        
        # Check memory usage
        memory = metrics.get("memory_percent", 0)
        if memory > self.config["thresholds"]["memory_usage"] * 100:
            alerts.append({
                "type": "WARNING_HEALTH",
                "message": f"Memory usage {memory:.1f}% exceeds {self.config['thresholds']['memory_usage']*100:.0f}% threshold",
                "data": metrics
            })
        
        return alerts

# Singleton instance for easy import
alert_manager = AlertManager()