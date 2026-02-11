"""
Performance Leaderboard — Feature 16
Ranks strategies by Sharpe ratio, max drawdown, win rate.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Leaderboard:
    """Strategy performance leaderboard"""
    
    def __init__(self, leaderboard_file: str = "leaderboard.json"):
        self.leaderboard_file = leaderboard_file
        self._ensure_file()
    
    def _ensure_file(self):
        if not os.path.exists(self.leaderboard_file):
            self._save({"strategies": [], "last_updated": None})
    
    def _load(self) -> Dict:
        try:
            with open(self.leaderboard_file, 'r') as f:
                return json.load(f)
        except:
            return {"strategies": [], "last_updated": None}
    
    def _save(self, data: Dict):
        data["last_updated"] = datetime.now().isoformat()
        with open(self.leaderboard_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def add_strategy(self, name: str, metrics: Dict):
        """Add or update a strategy on the leaderboard"""
        data = self._load()
        
        entry = {
            "name": name,
            "sharpe_ratio": metrics.get("sharpe_ratio", 0),
            "total_return_pct": metrics.get("total_return_pct", 0),
            "max_drawdown_pct": metrics.get("max_drawdown_pct", 0),
            "win_rate": metrics.get("win_rate", 0),
            "total_trades": metrics.get("total_trades", 0),
            "profit_factor": metrics.get("profit_factor", 0),
            "created_by": metrics.get("created_by", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
        
        # Update if exists, else add
        found = False
        for i, s in enumerate(data["strategies"]):
            if s["name"] == name:
                data["strategies"][i] = entry
                found = True
                break
        
        if not found:
            data["strategies"].append(entry)
        
        self._save(data)
        logger.info(f"🏆 Leaderboard updated: {name} (Sharpe: {entry['sharpe_ratio']})")
    
    def get_rankings(self, sort_by: str = "sharpe_ratio", top_n: int = 10) -> List[Dict]:
        """Get strategies ranked by metric"""
        data = self._load()
        strategies = data.get("strategies", [])
        
        strategies.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
        
        # Add rank
        for i, s in enumerate(strategies[:top_n]):
            s["rank"] = i + 1
        
        return strategies[:top_n]
    
    def get_best_strategy(self) -> Optional[Dict]:
        rankings = self.get_rankings()
        return rankings[0] if rankings else None
    
    def get_leaderboard_text(self) -> str:
        """Formatted leaderboard for display"""
        rankings = self.get_rankings()
        if not rankings:
            return "🏆 Leaderboard: No strategies yet"
        
        lines = ["🏆 Strategy Leaderboard:"]
        medals = ["🥇", "🥈", "🥉"]
        
        for s in rankings[:5]:
            rank = s["rank"]
            medal = medals[rank - 1] if rank <= 3 else f"#{rank}"
            lines.append(
                f"  {medal} {s['name']}: "
                f"Sharpe={s['sharpe_ratio']:.2f} | "
                f"Return={s['total_return_pct']:+.1f}% | "
                f"DD={s['max_drawdown_pct']:.1f}% | "
                f"WR={s['win_rate']:.0f}%"
            )
        
        return "\n".join(lines)
    
    def remove_strategy(self, name: str):
        data = self._load()
        data["strategies"] = [s for s in data["strategies"] if s["name"] != name]
        self._save(data)
