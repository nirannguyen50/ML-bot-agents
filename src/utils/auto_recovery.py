"""
Auto-Recovery — Feature 17
Saves checkpoint after each task. On crash, resumes from last checkpoint.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class AutoRecovery:
    """Checkpoint-based recovery system for autonomous pipeline"""
    
    def __init__(self, checkpoint_file: str = "checkpoint.json"):
        self.checkpoint_file = checkpoint_file
        self.state = self._load()
    
    def _load(self) -> Dict:
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                logger.info(f"🔄 Loaded checkpoint: cycle={data.get('cycle', 0)}, phase={data.get('phase', 'unknown')}")
                return data
        except Exception as e:
            logger.warning(f"Could not load checkpoint: {e}")
        return self._initial_state()
    
    def _initial_state(self) -> Dict:
        return {
            "cycle": 0,
            "phase": "startup",
            "completed_tasks": [],
            "pending_task_ids": [],
            "last_save": None,
            "crash_count": 0,
            "last_crash": None,
            "agent_states": {}
        }
    
    def save(self):
        """Save current checkpoint"""
        self.state["last_save"] = datetime.now().isoformat()
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def start_cycle(self, cycle_num: int):
        """Mark start of a new cycle"""
        self.state["cycle"] = cycle_num
        self.state["phase"] = "pipeline"
        self.state["completed_tasks"] = []
        self.save()
    
    def set_phase(self, phase: str):
        """Update current phase: pipeline, code_review, voting, planning, cooldown"""
        self.state["phase"] = phase
        self.save()
    
    def task_completed(self, task_id: int, task_title: str):
        """Record a completed task"""
        self.state["completed_tasks"].append({
            "id": task_id,
            "title": task_title,
            "completed_at": datetime.now().isoformat()
        })
        if task_id in self.state["pending_task_ids"]:
            self.state["pending_task_ids"].remove(task_id)
        self.save()
    
    def set_pending_tasks(self, task_ids: List[int]):
        """Set the list of pending task IDs"""
        self.state["pending_task_ids"] = task_ids
        self.save()
    
    def record_crash(self, error: str = ""):
        """Record a crash event"""
        self.state["crash_count"] = self.state.get("crash_count", 0) + 1
        self.state["last_crash"] = {
            "time": datetime.now().isoformat(),
            "error": error[:500],
            "phase": self.state.get("phase"),
            "cycle": self.state.get("cycle")
        }
        self.save()
    
    def save_agent_state(self, agent_name: str, state: Dict):
        """Save individual agent state for recovery"""
        self.state["agent_states"][agent_name] = {
            **state,
            "saved_at": datetime.now().isoformat()
        }
        self.save()
    
    def should_resume(self) -> bool:
        """Check if we should resume from a checkpoint"""
        return (
            self.state.get("phase") not in ["startup", "cooldown", None]
            and self.state.get("cycle", 0) > 0
        )
    
    def get_resume_info(self) -> Dict:
        """Get info needed to resume from checkpoint"""
        return {
            "cycle": self.state.get("cycle", 0),
            "phase": self.state.get("phase", "startup"),
            "completed_task_ids": [t["id"] for t in self.state.get("completed_tasks", [])],
            "pending_task_ids": self.state.get("pending_task_ids", []),
            "crash_count": self.state.get("crash_count", 0)
        }
    
    def get_status_text(self) -> str:
        crashes = self.state.get("crash_count", 0)
        completed = len(self.state.get("completed_tasks", []))
        return (
            f"🔄 Recovery: Cycle {self.state.get('cycle', 0)} | "
            f"Phase: {self.state.get('phase', 'N/A')} | "
            f"Done: {completed} tasks | "
            f"Crashes: {crashes}"
        )
