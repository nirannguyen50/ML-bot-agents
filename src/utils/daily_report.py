"""
Daily Summary Report — Feature 23
End-of-day summary sent via Telegram:
- Tasks completed
- Cost spent
- Best strategy
- Agent performance
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DailyReporter:
    """Generates and sends daily summary reports via Telegram"""
    
    def __init__(self, telegram_notifier=None):
        self.telegram = telegram_notifier
        self.daily_stats = self._initial_stats()
    
    def _initial_stats(self) -> Dict:
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "cycles_run": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "total_api_calls": 0,
            "strategies_created": 0,
            "code_reviews": 0,
            "votes_cast": 0,
            "errors": [],
            "highlights": []
        }
    
    def record_cycle(self, cycle_num: int):
        """Record a completed cycle"""
        self._check_date_reset()
        self.daily_stats["cycles_run"] += 1
    
    def record_task(self, task_title: str, success: bool):
        self._check_date_reset()
        if success:
            self.daily_stats["tasks_completed"] += 1
        else:
            self.daily_stats["tasks_failed"] += 1
    
    def record_cost(self, cost_usd: float, tokens: int, api_calls: int):
        self._check_date_reset()
        self.daily_stats["total_cost_usd"] += cost_usd
        self.daily_stats["total_tokens"] += tokens
        self.daily_stats["total_api_calls"] += api_calls
    
    def record_error(self, error: str):
        self._check_date_reset()
        self.daily_stats["errors"].append(error[:200])
        self.daily_stats["errors"] = self.daily_stats["errors"][-10:]
    
    def add_highlight(self, highlight: str):
        self._check_date_reset()
        self.daily_stats["highlights"].append(highlight)
    
    def _check_date_reset(self):
        """Reset stats if it's a new day"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.daily_stats["date"] != today:
            self.daily_stats = self._initial_stats()
    
    def generate_report(self, agent_health_text: str = "",
                        leaderboard_text: str = "",
                        paper_trading_text: str = "",
                        recovery_text: str = "") -> str:
        """Generate the daily summary report text"""
        s = self.daily_stats
        
        report = f"""📋 BÁO CÁO NGÀY {s['date']}

🔄 Cycles: {s['cycles_run']}
✅ Tasks Done: {s['tasks_completed']} | ❌ Failed: {s['tasks_failed']}
💰 Chi phí API: ${s['total_cost_usd']:.4f}
📊 API Calls: {s['total_api_calls']:,} | Tokens: {s['total_tokens']:,}"""
        
        if s['highlights']:
            report += "\n\n⭐ Highlights:"
            for h in s['highlights'][-5:]:
                report += f"\n  • {h}"
        
        if agent_health_text:
            report += f"\n\n{agent_health_text}"
        
        if leaderboard_text:
            report += f"\n\n{leaderboard_text}"
        
        if paper_trading_text:
            report += f"\n\n{paper_trading_text}"
        
        if recovery_text:
            report += f"\n\n{recovery_text}"
        
        if s['errors']:
            report += f"\n\n🚨 Errors ({len(s['errors'])}):"
            for e in s['errors'][-3:]:
                report += f"\n  • {e[:100]}"
        
        return report
    
    def send_report(self, **kwargs) -> bool:
        """Generate and send report via Telegram"""
        report = self.generate_report(**kwargs)
        
        # Also save to file
        report_file = f"reports/daily_report_{self.daily_stats['date']}.txt"
        os.makedirs("reports", exist_ok=True)
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
        except:
            pass
        
        # Send via Telegram
        if self.telegram:
            return self.telegram.send_message(report)
        
        logger.info(f"Daily report:\n{report}")
        return True
