"""
Agent Health Monitor — Feature 18
Tracks per-agent metrics and detects stuck/unhealthy agents.
"""

import time
import logging
import threading
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentHealthMonitor:
    """Monitors agent health: tracks task times, token usage, error rates"""
    
    def __init__(self, max_task_time_seconds: int = 300,
                 max_consecutive_errors: int = 5,
                 max_tokens_per_task: int = 50000):
        self.max_task_time = max_task_time_seconds  # 5 min per task default
        self.max_errors = max_consecutive_errors
        self.max_tokens = max_tokens_per_task
        self.lock = threading.Lock()
        
        # Per-agent metrics
        self.agents: Dict[str, Dict] = {}
    
    def register_agent(self, agent_name: str):
        """Register an agent for monitoring"""
        with self.lock:
            self.agents[agent_name] = {
                "status": "idle",
                "task_start": None,
                "current_task": None,
                "tasks_completed": 0,
                "tasks_failed": 0,
                "consecutive_errors": 0,
                "total_time": 0.0,
                "avg_task_time": 0.0,
                "token_usage": 0,
                "last_activity": datetime.now().isoformat(),
                "warnings": [],
                "restarts": 0
            }
    
    def _save_state(self):
        """Save current health state to JSON for dashboard"""
        try:
            with open("agent_health.json", "w") as f:
                import json
                json.dump(self.get_status_all(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save agent health: {e}")

    def task_started(self, agent_name: str, task_title: str):
        """Mark that an agent has started a task"""
        with self.lock:
            if agent_name not in self.agents:
                self.register_agent(agent_name)
            
            self.agents[agent_name]["status"] = "working"
            self.agents[agent_name]["task_start"] = time.time()
            self.agents[agent_name]["current_task"] = task_title
            self.agents[agent_name]["last_activity"] = datetime.now().isoformat()
            self._save_state()
    
    def task_completed(self, agent_name: str, success: bool = True, tokens_used: int = 0):
        """Mark that an agent has completed a task"""
        with self.lock:
            if agent_name not in self.agents:
                return
            
            agent = self.agents[agent_name]
            elapsed = time.time() - (agent["task_start"] or time.time())
            
            agent["status"] = "idle"
            agent["current_task"] = None
            agent["task_start"] = None
            agent["token_usage"] += tokens_used
            agent["total_time"] += elapsed
            agent["last_activity"] = datetime.now().isoformat()
            
            if success:
                agent["tasks_completed"] += 1
                agent["consecutive_errors"] = 0
            else:
                agent["tasks_failed"] += 1
                agent["consecutive_errors"] += 1
            
            total = agent["tasks_completed"] + agent["tasks_failed"]
            agent["avg_task_time"] = agent["total_time"] / max(total, 1)
            self._save_state()
    
    def check_health(self) -> List[Dict]:
        """Check all agents for health issues. Returns list of warnings."""
        warnings = []
        
        with self.lock:
            for name, agent in self.agents.items():
                # Check if stuck (task running too long)
                if agent["status"] == "working" and agent["task_start"]:
                    elapsed = time.time() - agent["task_start"]
                    if elapsed > self.max_task_time:
                        warnings.append({
                            "agent": name,
                            "type": "stuck",
                            "message": f"🚨 {name} stuck for {elapsed:.0f}s on: {agent['current_task'][:50]}",
                            "severity": "high"
                        })
                
                # Check consecutive errors
                if agent["consecutive_errors"] >= self.max_errors:
                    warnings.append({
                        "agent": name,
                        "type": "error_streak",
                        "message": f"🚨 {name} has {agent['consecutive_errors']} consecutive errors",
                        "severity": "high"
                    })
                
                # Check token usage (warning if approaching limit)
                if agent["token_usage"] > self.max_tokens * 0.8:
                    warnings.append({
                        "agent": name,
                        "type": "high_token_usage",
                        "message": f"⚠️ {name} high token usage: {agent['token_usage']:,}",
                        "severity": "medium"
                    })
        
        return warnings
    
    def get_status_all(self) -> Dict:
        """Get health status of all agents"""
        with self.lock:
            return {
                name: {
                    "status": a["status"],
                    "tasks_done": a["tasks_completed"],
                    "tasks_failed": a["tasks_failed"],
                    "avg_time": round(a["avg_task_time"], 1),
                    "tokens": a["token_usage"],
                    "errors_streak": a["consecutive_errors"],
                    "restarts": a["restarts"]
                }
                for name, a in self.agents.items()
            }
    
    def mark_restart(self, agent_name: str):
        """Record an agent restart"""
        with self.lock:
            if agent_name in self.agents:
                self.agents[agent_name]["restarts"] += 1
                self.agents[agent_name]["consecutive_errors"] = 0
                self.agents[agent_name]["status"] = "restarting"
                self.agents[agent_name]["last_activity"] = datetime.now().isoformat()
    
    def get_summary_text(self) -> str:
        """Formatted health summary"""
        status = self.get_status_all()
        if not status:
            return "🏥 No agents registered"
        
        lines = ["🏥 Agent Health:"]
        for name, s in status.items():
            icon = "🟢" if s["errors_streak"] == 0 else "🔴" if s["errors_streak"] >= 3 else "🟡"
            lines.append(
                f"  {icon} {name}: {s['status']} | "
                f"Done:{s['tasks_done']} Fail:{s['tasks_failed']} | "
                f"Avg:{s['avg_time']:.0f}s | Tokens:{s['tokens']:,}"
            )
        
        return "\n".join(lines)
