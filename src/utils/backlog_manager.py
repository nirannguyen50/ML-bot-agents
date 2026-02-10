"""
Backlog Manager
Manages the project task queue for agent collaboration.
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

BACKLOG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'backlog.json')


class BacklogManager:
    """Manages project backlog for agent task assignment"""
    
    def __init__(self):
        self.backlog_path = os.path.abspath(BACKLOG_PATH)
        self._ensure_backlog()
    
    def _ensure_backlog(self):
        """Create backlog file if it doesn't exist"""
        if not os.path.exists(self.backlog_path):
            self._save({"tasks": [], "next_id": 1})
    
    def _load(self) -> Dict:
        with open(self.backlog_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save(self, data: Dict):
        with open(self.backlog_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_task(self, title: str, assigned_to: str, priority: str = "medium",
                 description: str = "", depends_on: int = None) -> Dict:
        """Add a task to the backlog"""
        data = self._load()
        task = {
            "id": data["next_id"],
            "title": title,
            "description": description,
            "assigned_to": assigned_to,
            "status": "todo",
            "priority": priority,
            "depends_on": depends_on,
            "created_at": datetime.now().isoformat(),
            "completed_at": None
        }
        data["tasks"].append(task)
        data["next_id"] += 1
        self._save(data)
        logger.info(f"Added task #{task['id']}: {title} -> {assigned_to}")
        return task
    
    def get_next_task(self, agent_name: str) -> Optional[Dict]:
        """Get the highest priority pending task for an agent"""
        data = self._load()
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        
        candidates = []
        for task in data["tasks"]:
            if task["assigned_to"] == agent_name and task["status"] == "todo":
                # Check dependencies
                if task["depends_on"]:
                    dep = next((t for t in data["tasks"] if t["id"] == task["depends_on"]), None)
                    if dep and dep["status"] != "done":
                        continue  # Skip — dependency not completed
                candidates.append(task)
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda t: priority_order.get(t["priority"], 2))
        return candidates[0]
    
    def update_status(self, task_id: int, status: str) -> str:
        """Update task status: todo, in_progress, done, blocked"""
        data = self._load()
        for task in data["tasks"]:
            if task["id"] == task_id:
                task["status"] = status
                if status == "done":
                    task["completed_at"] = datetime.now().isoformat()
                self._save(data)
                return f"Task #{task_id} status -> {status}"
        return f"Task #{task_id} not found."
    
    def get_all_tasks(self) -> List[Dict]:
        """Get all tasks"""
        return self._load()["tasks"]
    
    def get_summary(self) -> str:
        """Get backlog summary"""
        tasks = self.get_all_tasks()
        total = len(tasks)
        done = sum(1 for t in tasks if t["status"] == "done")
        in_progress = sum(1 for t in tasks if t["status"] == "in_progress")
        todo = sum(1 for t in tasks if t["status"] == "todo")
        return f"Backlog: {total} total | {done} done | {in_progress} in progress | {todo} todo"
