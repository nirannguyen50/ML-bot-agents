"""
Shared Memory — Feature 9
Cross-agent knowledge sharing via a shared JSON store.
Any agent can write insights, and other agents can read them.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class SharedMemory:
    """Thread-safe shared memory for cross-agent knowledge sharing"""
    
    def __init__(self, memory_file: str = "shared_memory.json"):
        self.memory_file = memory_file
        self.lock = threading.Lock()
        self._ensure_file()
    
    def _ensure_file(self):
        if not os.path.exists(self.memory_file):
            self._save({"insights": {}, "patterns": [], "strategies": {}, "warnings": []})
    
    def _load(self) -> Dict:
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"insights": {}, "patterns": [], "strategies": {}, "warnings": []}
    
    def _save(self, data: Dict):
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    def share_insight(self, agent_name: str, key: str, value: str):
        """Agent shares a discovery/insight that other agents can use"""
        with self.lock:
            data = self._load()
            data["insights"][key] = {
                "value": value,
                "author": agent_name,
                "timestamp": datetime.now().isoformat()
            }
            self._save(data)
            logger.info(f"📡 {agent_name} shared insight: {key}")
    
    def get_insight(self, key: str) -> Optional[str]:
        """Get a specific insight by key"""
        data = self._load()
        insight = data["insights"].get(key)
        return insight["value"] if insight else None
    
    def get_all_insights(self) -> Dict:
        """Get all shared insights"""
        return self._load().get("insights", {})
    
    def share_pattern(self, agent_name: str, pattern: str, confidence: float = 0.5):
        """Share a discovered market pattern"""
        with self.lock:
            data = self._load()
            data["patterns"].append({
                "pattern": pattern,
                "confidence": confidence,
                "author": agent_name,
                "timestamp": datetime.now().isoformat()
            })
            # Keep last 50 patterns
            data["patterns"] = data["patterns"][-50:]
            self._save(data)
    
    def get_patterns(self, min_confidence: float = 0.0) -> List[Dict]:
        """Get patterns above confidence threshold"""
        data = self._load()
        return [p for p in data.get("patterns", []) if p.get("confidence", 0) >= min_confidence]
    
    def share_strategy_result(self, strategy_name: str, metrics: Dict):
        """Share strategy performance results"""
        with self.lock:
            data = self._load()
            data["strategies"][strategy_name] = {
                **metrics,
                "timestamp": datetime.now().isoformat()
            }
            self._save(data)
    
    def get_best_strategy(self) -> Optional[Dict]:
        """Get the best performing strategy"""
        data = self._load()
        strategies = data.get("strategies", {})
        if not strategies:
            return None
        return max(strategies.items(), key=lambda x: x[1].get("sharpe_ratio", 0))
    
    def add_warning(self, agent_name: str, warning: str):
        """Add a system-wide warning"""
        with self.lock:
            data = self._load()
            data["warnings"].append({
                "warning": warning,
                "author": agent_name,
                "timestamp": datetime.now().isoformat()
            })
            data["warnings"] = data["warnings"][-20:]
            self._save(data)
    
    def get_context_for_agent(self, agent_name: str) -> str:
        """Get a formatted context string for an agent to use in prompts"""
        data = self._load()
        
        parts = []
        
        # Recent insights from other agents
        insights = data.get("insights", {})
        other_insights = {k: v for k, v in insights.items() if v.get("author") != agent_name}
        if other_insights:
            parts.append("=== SHARED KNOWLEDGE ===")
            for key, val in list(other_insights.items())[-5:]:
                parts.append(f"• {key} (by {val['author']}): {val['value'][:200]}")
        
        # Recent patterns
        patterns = data.get("patterns", [])[-5:]
        if patterns:
            parts.append("\n=== DISCOVERED PATTERNS ===")
            for p in patterns:
                parts.append(f"• [{p['confidence']:.0%}] {p['pattern'][:150]} (by {p['author']})")
        
        # Strategy results
        strategies = data.get("strategies", {})
        if strategies:
            parts.append("\n=== STRATEGY RESULTS ===")
            for name, metrics in list(strategies.items())[-3:]:
                sr = metrics.get("sharpe_ratio", "N/A")
                dd = metrics.get("max_drawdown", "N/A")
                parts.append(f"• {name}: Sharpe={sr}, MaxDD={dd}")
        
        # Warnings
        warnings = data.get("warnings", [])[-3:]
        if warnings:
            parts.append("\n=== WARNINGS ===")
            for w in warnings:
                parts.append(f"⚠️ {w['warning']} (by {w['author']})")
        
        return "\n".join(parts) if parts else ""
