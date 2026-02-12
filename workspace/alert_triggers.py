#!/usr/bin/env python3
"""
Alert Triggers for Trading Bot Monitoring
Integrates with CI/CD pipeline and monitoring system
"""

import sys
import json
import subprocess
from pathlib import Path
import psutil
import time

# Add workspace to path for imports
sys.path.append(str(Path(__file__).parent))

from alert_manager import alert_manager

class AlertTriggers:
    """Manage alert triggers for different events"""
    
    def __init__(self):
        self.alert_manager = alert_manager
    
    def trigger_backtest_alert(self, backtest_file: str):
        """Trigger alert based on backtest results"""
        try:
            with open(backtest_file, 'r') as f:
                results = json.load(f)
            
            # Check metrics against thresholds
            alerts = self.alert_manager.check_backtest_metrics(results)
            
            for alert in alerts:
                self.alert_manager.send_alert(
                    alert_type=alert["type"],
                    message=alert["message"],
                    data=alert["data"]
                )
            
            return len(alerts) > 0
            
        except Exception as e:
            self.alert_manager.send_alert(
                alert_type="ERROR_SYSTEM",
                message=f"Failed to process backtest alert: {str(e)}",
                data={"file": backtest_file}
            )
            return False
    
    def trigger_health_check(self):
        """Trigger health check alert"""
        try:
            # Collect system metrics
            metrics = {
                "timestamp": time.time(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "process_count": len(psutil.pids())
            }
            
            # Check for running agents
            agent_processes = []
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    if 'python' in proc.info['name'].lower():
                        cmdline = proc.info['cmdline']
                        if cmdline and any('agent' in arg.lower() for arg in cmdline):
                            agent_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            metrics["agents_running"] = len(agent_processes)
            
            # Check thresholds
            alerts = self.alert_manager.check_health_metrics(metrics)
            
            # Add process-level alerts
            if metrics["agents_running"] < 5:  # Assuming 5 agents should be running
                alerts.append({
                    "type": "CRITICAL_HEALTH",
                    "message": f"Only {metrics['agents_running']} agents running (expected 5)",
                    "data": metrics
                })
            
            # Send alerts
            for alert in alerts:
                self.alert_manager.send_alert(
                    alert_type=alert["type"],
                    message=alert["message"],
                    data=alert["data"]
                )
            
            # Always log health status
            if not alerts:
                self.alert_manager.send_alert(
                    alert_type="INFO_HEALTH",
                    message="System health check passed",
                    data=metrics
                )
            
            return metrics
            
        except Exception as e:
            self.alert_manager.send_alert(
                alert_type="ERROR_SYSTEM",
                message=f"Health check failed: {str(e)}",
                data={}
            )
            return None
    
    def trigger_ci_cd_alert(self, pipeline_stage: str, status: str, 
                           details: Dict[str, Any] = None):
        """Trigger CI/CD pipeline alerts"""
        status_colors = {
            "success": "good",
            "failure": "danger",
            "running": "#1E90FF",
            "deployed": "#36A64F"
        }
        
        alert_type = f"CI_CD_{status.upper()}"
        
        message = f"CI/CD Pipeline {pipeline_stage}: {status}"
        
        self.alert_manager.send_alert(
            alert_type=alert_type,
            message=message,
            data=details or {}
        )
        
        return True
    
    def trigger_custom_alert(self, condition: bool, alert_config: Dict[str, Any]):
        """Trigger custom alert based on condition"""
        if condition:
            self.alert_manager.send_alert(
                alert_type=alert_config.get("type", "CUSTOM_ALERT"),
                message=alert_config.get("message", "Custom condition triggered"),
                data=alert_config.get("data", {})
            )
            return True
        return False

# Command-line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Alert Triggers for Trading Bot")
    parser.add_argument("--backtest", help="Path to backtest results JSON")
    parser.add_argument("--health", action="store_true", help="Run health check")
    parser.add_argument("--ci-cd", help="CI/CD pipeline stage")
    parser.add_argument("--status", help="CI/CD status (success/failure)")
    
    args = parser.parse_args()
    triggers = AlertTriggers()
    
    if args.backtest:
        print(f"Checking backtest: {args.backtest}")
        triggered = triggers.trigger_backtest_alert(args.backtest)
        print(f"Alerts triggered: {triggered}")
    
    elif args.health:
        print("Running health check...")
        metrics = triggers.trigger_health_check()
        if metrics:
            print(f"Health metrics: {metrics}")
    
    elif args.ci_cd and args.status:
        print(f"CI/CD Alert: {args.ci_cd} - {args.status}")
        triggers.trigger_ci_cd_alert(args.ci_cd, args.status)
    
    else:
        print("No action specified. Use --help for usage.")