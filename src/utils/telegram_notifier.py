"""
Telegram Notifier — Feature 2
Sends real-time reports from PM to Telegram chat.
"""

import logging
import os
import asyncio

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    requests = None


class TelegramNotifier:
    """Send notifications to Telegram chat"""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        # Load from env vars first
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        
        # Fallback: load from .env file
        if not self.bot_token or not self.chat_id:
            env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('TELEGRAM_BOT_TOKEN=') and not self.bot_token:
                            self.bot_token = line.split('=', 1)[1].strip('"').strip("'")
                        elif line.startswith('TELEGRAM_CHAT_ID=') and not self.chat_id:
                            self.chat_id = line.split('=', 1)[1].strip('"').strip("'")
        
        self.enabled = bool(self.bot_token and self.chat_id)
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""
        
        if self.enabled:
            logger.info(f"✅ Telegram notifications enabled (chat_id: {self.chat_id})")
        else:
            logger.info("Telegram notifications disabled (no token/chat_id configured)")
    
    def send_message(self, text: str, parse_mode: str = None) -> bool:
        """Send a text message to Telegram"""
        if not self.enabled or not requests:
            return False
        
        try:
            # Truncate long messages (Telegram limit: 4096 chars)
            if len(text) > 4000:
                text = text[:4000] + "\n..."
            
            # Use GET with params (more reliable across network configs)
            params = {
                "chat_id": self.chat_id,
                "text": text,
            }
            if parse_mode:
                params["parse_mode"] = parse_mode
            
            response = requests.get(
                f"{self.base_url}/sendMessage",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.warning(f"Telegram send failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"Telegram error: {e}")
            return False
    
    def send_cycle_start(self, cycle_num: int):
        """Notify cycle start"""
        self.send_message(f"🔄 *Autonomous Cycle #{cycle_num}* started!")
    
    def send_task_complete(self, task_title: str, agent: str, rounds: int):
        """Notify task completion"""
        self.send_message(f"✅ *{task_title}*\n👤 Agent: `{agent}`\n🔁 Rounds: {rounds}")
    
    def send_pipeline_done(self, total_tasks: int, cycle_num: int):
        """Notify pipeline completion"""
        self.send_message(f"🎉 *Pipeline Complete!*\n📋 {total_tasks} tasks done\n🔄 Cycle #{cycle_num}")
    
    def send_auto_plan(self, new_tasks: list):
        """Notify auto-planned tasks"""
        task_list = "\n".join(f"• {t}" for t in new_tasks[:5])
        self.send_message(f"🧠 *PM Auto-Plan:*\n{task_list}")
    
    def send_cost_report(self, cost_summary: str):
        """Notify cost report"""
        self.send_message(f"💰 *Cost Report:*\n`{cost_summary}`")
    
    def send_error(self, error_msg: str):
        """Notify critical error"""
        self.send_message(f"🚨 *ERROR:*\n```\n{error_msg[:500]}\n```")
    
    def send_vote_result(self, proposal: str, result: str):
        """Notify vote result"""
        self.send_message(f"🗳️ *Vote Result:*\n📝 {proposal}\n📊 {result}")
