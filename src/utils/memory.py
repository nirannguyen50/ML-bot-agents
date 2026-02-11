"""
Agent Memory Module
Handles persistent long-term memory for agents using JSON files.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class AgentMemory:
    """Persistent memory for an agent"""
    
    def __init__(self, agent_name: str, memory_dir: str = "memory"):
        self.agent_name = agent_name
        self.memory_dir = memory_dir
        self.memory_file = os.path.join(memory_dir, f"{agent_name}.json")
        self.data = {}
        
        # Ensure directory exists
        os.makedirs(memory_dir, exist_ok=True)
        
        # Load existing memory
        self.load()
        
    def load(self):
        """Load memory from file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                logger.info(f"Loaded memory for {self.agent_name}")
            else:
                self.data = {"facts": {}, "experiences": []}
                self.save()
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
            self.data = {"facts": {}, "experiences": []}

    def save(self):
        """Save memory to file"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def remember_fact(self, key: str, value: str) -> str:
        """Store a fact"""
        self.data["facts"][key] = value
        self.save()
        return f"Fact stored: {key} = {value}"

    def recall_fact(self, key: str) -> str:
        """Retrieve a fact"""
        value = self.data["facts"].get(key)
        if value:
            return f"Recalled: {key} = {value}"
        return f"I don't remember anything about '{key}'."

    def get_all_facts(self) -> str:
        """Get summary of all facts"""
        if not self.data["facts"]:
            return "My memory is empty."
        
        summary = "Known Facts:\n"
        for k, v in self.data["facts"].items():
            summary += f"- {k}: {v}\n"
        return summary

    def remember_failure(self, task_title: str, error: str, round_failed: int = 0):
        """Feature 11: Store a failure to learn from"""
        if "failures" not in self.data:
            self.data["failures"] = []
        
        self.data["failures"].append({
            "task": task_title,
            "error": error[:500],
            "round": round_failed,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        })
        # Keep last 30 failures
        self.data["failures"] = self.data["failures"][-30:]
        self.save()
    
    def get_failure_history(self, keyword: str = None) -> str:
        """Feature 11: Get past failures, optionally filtered by keyword"""
        failures = self.data.get("failures", [])
        if not failures:
            return ""
        
        if keyword:
            failures = [f for f in failures if keyword.lower() in f.get("task", "").lower()]
        
        if not failures:
            return ""
        
        lines = ["=== PAST FAILURES (learn from these) ==="]
        for f in failures[-5:]:  # Last 5 relevant
            lines.append(f"• Task: {f['task']}")
            lines.append(f"  Error: {f['error'][:200]}")
            lines.append(f"  Failed at round: {f['round']}")
        
        return "\n".join(lines)
