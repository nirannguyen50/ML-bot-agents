#!/usr/bin/env python3
"""
Start ML Trading Bot Agents
This script initializes and coordinates all project agents using DeepSeek LLM
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List
import yaml
import sys
import os
import random

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
# Add parent directory to path to find agent_communication_logger
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from agent_communication_logger import log_agent_message
except ImportError:
    # Fallback if module not found
    def log_agent_message(*args, **kwargs): pass

try:
    from src.utils.llm_client import DeepSeekClient
except ImportError:
    # Fallback path if run from scripts/
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'utils'))
        from llm_client import DeepSeekClient
    except ImportError:
        DeepSeekClient = None

# Feature 2: Telegram Notifier
try:
    from utils.telegram_notifier import TelegramNotifier
except ImportError:
    TelegramNotifier = None

# Feature 7: Web Dashboard
try:
    from utils.dashboard import Dashboard
except ImportError:
    Dashboard = None

# Feature 8: Voting System
try:
    from utils.voting import VotingSystem
except ImportError:
    VotingSystem = None

# Feature 9: Shared Memory
try:
    from utils.shared_memory import SharedMemory
except ImportError:
    SharedMemory = None

# Feature 13: Walk-Forward Optimization
try:
    from utils.walk_forward import WalkForwardOptimizer
except ImportError:
    WalkForwardOptimizer = None

# Feature 15: Paper Trading
try:
    from utils.paper_trading import PaperTrader
except ImportError:
    PaperTrader = None

# Feature 16: Performance Leaderboard
try:
    from utils.leaderboard import Leaderboard
except ImportError:
    Leaderboard = None

# Feature 17: Auto-Recovery
try:
    from utils.auto_recovery import AutoRecovery
except ImportError:
    AutoRecovery = None

# Feature 18: Agent Health Monitor
try:
    from utils.agent_health import AgentHealthMonitor
except ImportError:
    AgentHealthMonitor = None

# Feature 23: Daily Summary Report
try:
    from utils.daily_report import DailyReporter
except ImportError:
    DailyReporter = None

# Configure logging
# Configure logging with UTF-8
sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agents_startup.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# DeepSeek API Key - load from environment variable
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not API_KEY:
    # Try loading from .env file
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip().startswith('DEEPSEEK_API_KEY='):
                    API_KEY = line.strip().split('=', 1)[1].strip('"').strip("'")
    if not API_KEY:
        logger.warning("DEEPSEEK_API_KEY not set! Agents will run without LLM.")

class ProjectManager:
    """Project Manager Agent - Coordinates all other agents"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.yaml')
        self.config = self.load_config(config_path)
        self.agents = {}
        self.project_status = {
            'phase': 'initialization',
            'start_time': datetime.now(),
            'agents_active': 0,
            'last_checkin': None
        }
        
        # Session ID mapping for logger
        self.agent_ids = {
            "project_manager": "agent:main:subagent:12b2e050-8ff9-4f2a-af19-5f362ae546fb",
            "data_scientist": "agent:main:subagent:6a1a837e-d912-4889-abd8-3127c8f4d42a",
            "quant_analyst": "agent:main:subagent:003e337a-e6fe-4035-b8e5-0d754a447f6c",
            "engineer": "agent:main:subagent:875988ba-7250-4c5b-883b-7b226735e4e0",
            "devops": "agent:main:subagent:9bd475bd-9f19-4bff-83b7-b1ee2ab962be",
            "risk_manager": "agent:main:subagent:f4a12b3c-7890-4def-abcd-1234567890ab",
            "trading_assistant": "agent:main:subagent:88c8ab35-081f-4567-8f12-cd92dafaa755",
            "main_system": "agent:main:main"
        }
        
        self.my_id = self.agent_ids["project_manager"]
        self.api_key = API_KEY
        if DeepSeekClient:
            self.llm = DeepSeekClient(api_key=API_KEY)
        else:
            self.llm = None
        
        # Load project context
        self.project_context = ""
        context_path = os.path.join(os.path.dirname(__file__), '..', 'project_context.md')
        if os.path.exists(context_path):
            try:
                with open(context_path, 'r', encoding='utf-8') as f:
                    self.project_context = f.read()
                logger.info(f"PM loaded project context ({len(self.project_context)} chars)")
            except Exception:
                pass
        
        # Feature 2: Telegram Notifier
        self.telegram = TelegramNotifier() if TelegramNotifier else None
        
        # Feature 7: Web Dashboard
        self.dashboard = Dashboard(port=self.config.get('dashboard', {}).get('port', 8080)) if Dashboard else None
        
        # Feature 8: Voting System
        self.voting = VotingSystem() if VotingSystem else None
        
        # Feature 9: Shared Memory
        self.shared_memory = SharedMemory() if SharedMemory else None
        
        # Feature 13: Walk-Forward Optimizer
        self.walk_forward = WalkForwardOptimizer() if WalkForwardOptimizer else None
        
        # Feature 15: Paper Trading
        self.paper_trader = PaperTrader() if PaperTrader else None
        
        # Feature 16: Performance Leaderboard
        self.leaderboard = Leaderboard() if Leaderboard else None
        
        # Feature 17: Auto-Recovery
        self.recovery = AutoRecovery() if AutoRecovery else None
        
        # Feature 18: Agent Health Monitor
        self.health_monitor = AgentHealthMonitor() if AgentHealthMonitor else None
        
        # Feature 23: Daily Summary Report
        self.daily_reporter = DailyReporter(telegram_notifier=self.telegram) if DailyReporter else None
    
    def pm_think(self, task: str, context: str = "") -> str:
        """PM uses LLM to make decisions with full project awareness"""
        if not self.llm:
            return "PM thinking unavailable (no LLM)."
        try:
            prompt = [
                {"role": "system", "content": f"""You are the Project Manager of an AI Trading Bot team.
                You coordinate 4 agents: Data Scientist, Quant Analyst, Engineer, DevOps.
                
                {self.project_context}
                
                Your responsibilities:
                - Assign tasks based on backlog priority and dependencies
                - Monitor progress and resolve blockers
                - Make decisions about project direction
                - Ensure quality and deadlines are met
                
                Reply in Vietnamese. Be concise and action-oriented."""},
                {"role": "user", "content": f"Context: {context}\n\nTask: {task}"}
            ]
            return self.llm.chat_completion(prompt)
        except Exception as e:
            return f"Error: {e}"
        
    def load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    async def start_agent(self, agent_name: str, agent_class):
        """Start a specific agent"""
        try:
            logger.info(f"Starting {agent_name} agent...")
            
            # Log to communication system
            agent_id = self.agent_ids.get(agent_name, "unknown")
            log_agent_message(
                from_agent=self.my_id,
                to_agent=agent_id,
                message=f"Initializing {agent_name} agent...",
                message_type="task"
            )
            
            # Instantiate with API Key
            agent = agent_class(self.config, api_key=self.api_key)
            await agent.initialize()
            self.agents[agent_name] = agent
            self.project_status['agents_active'] += 1
            logger.info(f"{agent_name} agent started successfully")
            
            # Log success
            log_agent_message(
                from_agent=agent_id,
                to_agent=self.my_id,
                message=f"{agent_name} online and ready.",
                message_type="status"
            )
            
            return agent
        except Exception as e:
            logger.error(f"Failed to start {agent_name} agent: {e}")
            return None
    
    async def start_all_agents(self):
        """Start all project agents"""
        logger.info("=" * 60)
        logger.info("ML TRADING BOT - AGENTS STARTUP (AI POWERED)")
        logger.info("=" * 60)
        
        # Announce system start
        log_agent_message(
            from_agent=self.agent_ids["main_system"],
            to_agent=self.my_id,
            message="System startup sequence initiated.",
            message_type="system"
        )
        
        # Load agent modules
        try:
            from src.agents.data_scientist import DataScientist
            from src.agents.quant_analyst import QuantAnalyst
            from src.agents.engineer import Engineer
            from src.agents.devops import DevOps
            
            agents_to_start = {
                'data_scientist': DataScientist,
                'quant_analyst': QuantAnalyst,
                'engineer': Engineer,
                'devops': DevOps
            }
            
            # Feature 14: Risk Manager Agent
            try:
                from src.agents.risk_manager import RiskManagerAgent
                agents_to_start['risk_manager'] = RiskManagerAgent
            except ImportError:
                logger.warning("Risk Manager agent not available")
            
            for agent_name, agent_class in agents_to_start.items():
                await self.start_agent(agent_name, agent_class)
                # Feature 18: Register agent in health monitor
                if self.health_monitor:
                    self.health_monitor.register_agent(agent_name)
                await asyncio.sleep(1)
            
        except ImportError as e:
            logger.warning(f"Agent modules check failed: {e}")
        
        logger.info(f"All agents started: {self.project_status['agents_active']} active")
    
    async def run_daily_standup(self):
        """Run daily standup meeting using LLM"""
        logger.info("\n" + "=" * 60)
        logger.info("DAILY STANDUP MEETING")
        logger.info("=" * 60)
        
        # Notify start of standup
        log_agent_message(
            from_agent=self.my_id,
            to_agent="agent:main:main",
            message="Starting Daily Standup Meeting. All agents report status.",
            message_type="alert"
        )
        
        standup_report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'agents': {}
        }
        
        for agent_name, agent in self.agents.items():
            try:
                # Ask agent to report status via LLM
                report = await agent.think("It is the Daily Standup.", "Report your status, yesterday's work, today's plan, and blockers.")
                
                status_entry = {
                    'yesterday': "See log detail",
                    'today': "See log detail",
                    'blockers': "None" if "blocker" not in report.lower() else "Possible blockers"
                }
                standup_report['agents'][agent_name] = status_entry
                logger.info(f"{agent_name}: Evaluated status")
                
                # Send chat message
                agent_id = self.agent_ids.get(agent_name)
                if agent_id:
                    log_agent_message(
                        from_agent=agent_id,
                        to_agent=self.my_id,
                        message=report,
                        message_type="status"
                    )
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.warning(f"{agent_name} status unavailable: {e}")
        
        # Save standup report
        self.save_report('daily_standup', standup_report)
        logger.info("Daily standup completed")
        
        # End standup
        log_agent_message(
            from_agent=self.my_id,
            to_agent="agent:main:main",
            message="Daily Standup concluded. Agents proceed with tasks.",
            message_type="task"
        )
    
    def save_report(self, report_type: str, data: Dict):
        """Save report to file"""
        reports_dir = 'reports'
        os.makedirs(reports_dir, exist_ok=True)
        filename = f"{reports_dir}/{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
        try:
            with open(filename, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            logger.info(f"Report saved: {filename}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
    
    async def monitor_agents_intelligent(self):
        """Monitor agent status with intelligent interaction"""
        logger.info("Starting intelligent agent monitoring...")
        
        # Manager context
        manager_ctx = "You are overseeing a team of AI agents (Data Scientist, Quant Analyst, Engineer, DevOps). Maintain high standards and ensure collaboration."
        
        while True:
            self.project_status['last_checkin'] = datetime.now()
            logger.info(f"Agent status: {self.project_status['agents_active']} active")
            
            # Simulate Manager checking in or initiating discussion
            if random.random() < 0.3 and self.llm: # 30% chance every cycle
                prompt = "Ask a random team member for a status update, assign a small task, or start a technical discussion relevant to ML trading."
                manager_msg = self.llm.chat_completion([
                    {"role": "system", "content": manager_ctx},
                    {"role": "user", "content": prompt}
                ])
                
                # Determine recipient (random for now)
                target = random.choice(list(self.agents.keys()))
                target_agent = self.agents[target]
                target_id = self.agent_ids.get(target)
                
                log_agent_message(self.my_id, target_id, manager_msg, "direct")
                
                # Target responds
                await asyncio.sleep(2)
                response = await target_agent.think(f"Project Manager says: {manager_msg}", "Reply professionally and appropriately to the manager.")
                log_agent_message(target_id, self.my_id, response, "direct")
            
            # Chance for peer-to-peer chatter
            elif random.random() < 0.3 and len(self.agents) > 1:
                agents_list = list(self.agents.keys())
                sender_name = random.choice(agents_list)
                receiver_name = random.choice([a for a in agents_list if a != sender_name])
                
                sender = self.agents[sender_name]
                receiver = self.agents[receiver_name]
                sender_id = self.agent_ids.get(sender_name)
                receiver_id = self.agent_ids.get(receiver_name)
                
                # Sender initiates
                init_msg = await sender.think(f"You want to discuss something with {receiver_name}.", "Start a technical conversation relevant to your roles.")
                log_agent_message(sender_id, receiver_id, init_msg, "direct")
                
                await asyncio.sleep(2)
                
                # Receiver responds
                reply_msg = await receiver.think(f"{sender_name} said: {init_msg}", "Reply to the colleague.")
                log_agent_message(receiver_id, sender_id, reply_msg, "direct")

            await asyncio.sleep(15)  # Check every 15 seconds
    
    async def shutdown(self):
        """Graceful shutdown of all agents"""
        logger.info("Shutting down agents...")
        log_agent_message(
            from_agent=self.my_id,
            to_agent="agent:main:main",
            message="Initiating system shutdown protocol.",
            message_type="alert"
        )
        for agent_name, agent in self.agents.items():
            try:
                if hasattr(agent, 'shutdown'):
                    await agent.shutdown()
                logger.info(f"{agent_name} agent shut down")
            except Exception as e:
                logger.error(f"Error shutting down {agent_name}: {e}")
        logger.info("All agents shut down")

    async def assign_initial_tasks(self):
        """Populate backlog if empty"""
        from utils.backlog_manager import BacklogManager
        backlog = BacklogManager()
        
        if not backlog.get_all_tasks():
            logger.info("Populating backlog with trading strategy tasks...")
            
            t1 = backlog.add_task(
                title="Download EURUSD market data",
                description="Download 3 months of EURUSD daily data using yfinance. Save as CSV in workspace/. Report row count and date range.",
                assigned_to="data_scientist",
                priority="critical"
            )
            t2 = backlog.add_task(
                title="Calculate technical indicators",
                description="Write a Python script (calculate_features.py) that reads the EURUSD CSV and calculates: SMA(20), SMA(50), RSI(14), MACD. Save results to eurusd_features.csv in workspace/.",
                assigned_to="data_scientist",
                priority="high",
                depends_on=t1["id"]
            )
            t3 = backlog.add_task(
                title="Design SMA crossover strategy",
                description="Write a trading strategy (strategy_sma_crossover.py) in workspace/: entry when SMA20 crosses above SMA50, exit when crosses below. Define position sizing (1% risk), stop loss (ATR-based), expected Sharpe ratio.",
                assigned_to="quant_analyst",
                priority="high",
                depends_on=t2["id"]
            )
            t4 = backlog.add_task(
                title="Write backtest engine",
                description="Write backtest_sma.py in workspace/ that reads eurusd_features.csv and tests the SMA crossover strategy. Output: total trades, win rate, profit factor, max drawdown.",
                assigned_to="engineer",
                priority="high",
                depends_on=t3["id"]
            )
            t5 = backlog.add_task(
                title="Create system health monitor",
                description="Write health_check.py in workspace/ that checks: disk space, memory usage, data freshness, log files count. Output a JSON report.",
                assigned_to="devops",
                priority="medium",
                depends_on=None
            )
            
            log_agent_message(self.my_id, "ALL", f"Backlog loaded: {backlog.get_summary()}", "task")
    
    async def run_continuous_pipeline(self):
        """
        Continuous pipeline: keep processing backlog until all tasks are done.
        Handles dependency chains and agent-to-agent handoffs.
        """
        from utils.backlog_manager import BacklogManager
        backlog = BacklogManager()
        
        logger.info("=" * 60)
        logger.info("CONTINUOUS PIPELINE STARTED")
        logger.info("=" * 60)
        
        # PM analyzes the backlog first
        pm_analysis = self.pm_think(
            "Review current backlog and plan execution order",
            f"Backlog: {backlog.get_summary()}\nTasks: {[t['title'] + ' (' + t['status'] + ')' for t in backlog.get_all_tasks()]}"
        )
        log_agent_message(self.my_id, "ALL", f"📊 PM Strategy: {pm_analysis}", "status")
        
        max_pipeline_rounds = 10  # Safety limit
        
        for pipeline_round in range(1, max_pipeline_rounds + 1):
            # Check if all tasks are done
            tasks = backlog.get_all_tasks()
            pending = [t for t in tasks if t["status"] in ("todo", "in_progress")]
            done = [t for t in tasks if t["status"] == "done"]
            
            if not pending:
                logger.info(f"🎉 ALL TASKS COMPLETE! ({len(done)}/{len(tasks)} done)")
                log_agent_message(self.my_id, "ALL", f"🎉 Pipeline complete! All {len(done)} tasks finished!", "status")
                break
            
            logger.info(f"\n--- Pipeline Round {pipeline_round} | {len(done)}/{len(tasks)} done, {len(pending)} pending ---")
            
            # Find tasks that can be executed NOW (deps satisfied)
            executed_any = False
            for agent_name, agent in self.agents.items():
                task = backlog.get_next_task(agent_name)
                if not task:
                    continue
                
                executed_any = True
                await self._execute_agent_task(agent, agent_name, task, backlog)
                await asyncio.sleep(self.config.get('pipeline', {}).get('pause_between_tasks', 3))
            
            if not executed_any:
                blocked_tasks = [t for t in pending if t["status"] == "todo"]
                if blocked_tasks:
                    logger.info(f"All remaining tasks blocked by dependencies. Waiting...")
                    # Check if we're stuck (all remaining have unmet deps)
                    all_blocked = True
                    for t in blocked_tasks:
                        if not t.get("depends_on"):
                            all_blocked = False
                    if all_blocked:
                        logger.warning("Pipeline deadlocked — all remaining tasks have unmet dependencies")
                        break
                await asyncio.sleep(5)
            
            # Auto git commit after each round
            if self.config.get('pipeline', {}).get('auto_git_commit', True):
                tools = None
                for a in self.agents.values():
                    if a.tools:
                        tools = a.tools
                        break
                if tools:
                    tools.git_commit(f"pipeline round {pipeline_round}: {backlog.get_summary()}")
        
        # Final git push
        if self.config.get('pipeline', {}).get('auto_git_push', True):
            for a in self.agents.values():
                if a.tools:
                    push_result = a.tools.git_push()
                    logger.info(f"Final push: {push_result}")
                    break
    
    async def _execute_agent_task(self, agent, agent_name: str, task: Dict, backlog):
        """Execute a single task with self-correction, error escalation, and notifications"""
        from utils.backlog_manager import BacklogManager
        
        task_id = task["id"]
        agent_id = self.agent_ids.get(agent_name)
        max_retries = self.config.get('agents', {}).get(agent_name, {}).get('max_retries', 3)
        
        # PM announces task
        logger.info(f"📋 Assigning task #{task_id} to {agent_name}: {task['title']}")
        log_agent_message(
            self.my_id, agent_id,
            f"📋 Task #{task_id}: {task['title']}\n{task['description']}",
            "task"
        )
        backlog.update_status(task_id, "in_progress")
        
        # Dashboard update
        if self.dashboard:
            self.dashboard.add_log(f"📋 Task #{task_id} → {agent_name}: {task['title']}")
            self.dashboard.update_backlog(backlog.get_all_tasks())
        
        # Feature 18: Health monitor — task started
        if self.health_monitor:
            self.health_monitor.task_started(agent_name, task['title'])
        
        # Feature 17: Auto-Recovery checkpoint
        if self.recovery:
            self.recovery.task_completed(task_id, task['title'])  # checkpoint before execution
        
        # Use multi-round self-correction (Feature 1: code auto-run built into this)
        result = await agent.execute_with_retry(task['description'], max_rounds=max_retries)
        
        rounds_used = result.get('rounds', 1)
        task_success = result.get('status') in ('success', 'partial')
        
        # Feature 18: Health monitor — task completed
        if self.health_monitor:
            self.health_monitor.task_completed(agent_name, success=task_success)
        
        # Feature 23: Daily report tracking
        if self.daily_reporter:
            self.daily_reporter.record_task(task['title'], task_success)
        
        if task_success:
            backlog.update_status(task_id, "done")
            
            status_emoji = "✅" if result['status'] == 'success' else "⚠️"
            report = f"{status_emoji} Task #{task_id} ({task['title']}) — {result['status']} in {rounds_used} round(s)"
            log_agent_message(agent_id, self.my_id, report, "status")
            
            # Agent learns the result
            if agent.memory:
                agent.memory.remember_fact(
                    f"task_{task_id}_result",
                    f"Completed: {task['title']} in {rounds_used} rounds"
                )
            
            # Feature 9: Share insights via shared memory
            if self.shared_memory and result.get('output'):
                self.shared_memory.share_insight(
                    agent_name,
                    f"task_{task_id}_{task['title'][:30]}",
                    result.get('output', '')[:300]
                )
            
            # Feature 2: Telegram notification
            if self.telegram:
                self.telegram.send_task_complete(task['title'], agent_name, rounds_used)
            
            # Feature 7: Dashboard update
            if self.dashboard:
                self.dashboard.add_log(report)
                self.dashboard.update_backlog(backlog.get_all_tasks())
            
            # Feature 5: Auto-run backtest if task is a backtest task
            if 'backtest' in task['title'].lower() and agent.tools:
                await self._run_backtest(agent, task)
            
            # Agent-to-Agent handoff: notify the next agent in the chain
            await self._notify_next_agent(task, backlog)
            
            # PM reviews the result with AI
            if rounds_used > 1:
                pm_review = self.pm_think(
                    f"Agent {agent_name} completed task '{task['title']}' but needed {rounds_used} retries. Assess quality.",
                    f"Result: {result.get('output', '')[:300]}"
                )
                log_agent_message(self.my_id, agent_id, f"📝 PM Review: {pm_review}", "status")
        else:
            # Feature 23: Record error
            if self.daily_reporter:
                self.daily_reporter.record_error(f"Task #{task_id} ({task['title']}) failed: {result.get('error', '')[:100]}")
            
            # Feature 6: Error Escalation — PM decides what to do
            await self._escalate_failure(agent, agent_name, task, backlog, result)
    
    async def _notify_next_agent(self, completed_task: Dict, backlog):
        """Find and notify agents whose tasks depend on the completed task"""
        completed_id = completed_task["id"]
        
        for task in backlog.get_all_tasks():
            if task.get("depends_on") == completed_id and task["status"] == "todo":
                next_agent_name = task["assigned_to"]
                next_agent = self.agents.get(next_agent_name)
                
                if next_agent:
                    handoff_msg = (
                        f"🔔 Dependency satisfied! Task #{completed_task['id']} ({completed_task['title']}) "
                        f"is DONE. Your task #{task['id']} ({task['title']}) is now READY."
                    )
                    next_agent.send_message("project_manager", f"Ready for task: {task['title']}")
                    await next_agent.receive_message("project_manager", handoff_msg)
                    
                    log_agent_message(
                        self.my_id,
                        self.agent_ids.get(next_agent_name),
                        handoff_msg,
                        "task"
                    )
                    logger.info(f"🔗 Handoff: {completed_task['assigned_to']} → {next_agent_name}")

    async def _escalate_failure(self, agent, agent_name: str, task: Dict, backlog, result: Dict):
        """
        Feature 6: Error Escalation — PM uses AI to decide: skip / reassign / split
        """
        task_id = task["id"]
        error = result.get('error', 'Unknown error')
        rounds_used = result.get('rounds', 0)
        
        logger.warning(f"🚨 Task #{task_id} failed after {rounds_used} rounds. Escalating to PM...")
        
        if self.dashboard:
            self.dashboard.add_log(f"🚨 ESCALATION: Task #{task_id} ({task['title']}) failed")
        
        if self.telegram:
            self.telegram.send_error(f"Task #{task_id} ({task['title']}) failed: {error[:200]}")
        
        # Ask PM to decide
        pm_decision = self.pm_think(
            "A task has FAILED after all retries. Decide what to do.",
            f"""Task: #{task_id} — {task['title']}
Agent: {agent_name}
Error: {error[:500]}
Rounds attempted: {rounds_used}

OPTIONS (reply with ONE keyword only):
1. SKIP — Mark as blocked and continue to next task
2. REASSIGN — Give the task to a different agent
3. SPLIT — Break into 2 smaller sub-tasks

Reply with: SKIP, REASSIGN, or SPLIT"""
        )
        
        decision = "SKIP"  # Default
        for keyword in ["REASSIGN", "SPLIT", "SKIP"]:
            if keyword in pm_decision.upper():
                decision = keyword
                break
        
        logger.info(f"📋 PM Decision for task #{task_id}: {decision}")
        log_agent_message(self.my_id, "ALL", f"📋 PM Escalation: Task #{task_id} → {decision}", "status")
        
        if decision == "SKIP":
            backlog.update_status(task_id, "blocked")
            logger.info(f"⏭️ Task #{task_id} skipped (blocked)")
            
        elif decision == "REASSIGN":
            # Find a different agent
            available_agents = [name for name in self.agents.keys() if name != agent_name]
            if available_agents:
                new_agent = random.choice(available_agents)
                backlog.update_status(task_id, "blocked")
                # Create a new reassigned task
                from utils.backlog_manager import BacklogManager
                bm = BacklogManager()
                bm.add_task(
                    title=f"[REASSIGNED] {task['title']}",
                    description=f"[Reassigned from {agent_name}] {task['description']}",
                    assigned_to=new_agent,
                    priority="high"
                )
                logger.info(f"🔄 Task #{task_id} reassigned to {new_agent}")
            else:
                backlog.update_status(task_id, "blocked")
                
        elif decision == "SPLIT":
            backlog.update_status(task_id, "blocked")
            # PM generates subtasks using AI
            split_response = self.pm_think(
                "Split this failed task into 2 smaller, simpler sub-tasks.",
                f"Task: {task['title']}\nDescription: {task['description']}\nAssigned to: {agent_name}\n\nReply with JSON: [{{\"title\": \"...\", \"description\": \"...\"}}]"
            )
            import re as escalation_re
            try:
                match = escalation_re.search(r'\[[\s\S]*\]', split_response)
                if match:
                    subtasks = json.loads(match.group())
                    from utils.backlog_manager import BacklogManager
                    bm = BacklogManager()
                    for st in subtasks[:2]:
                        bm.add_task(
                            title=st.get("title", "Subtask"),
                            description=st.get("description", task['description']),
                            assigned_to=agent_name,
                            priority="high"
                        )
                    logger.info(f"✂️ Task #{task_id} split into {len(subtasks[:2])} subtasks")
            except Exception as e:
                logger.error(f"Failed to split task: {e}")

    async def _run_backtest(self, agent, task: Dict):
        """Feature 5: Auto-run backtest scripts and capture real results"""
        import subprocess
        
        workspace_dir = os.path.join(os.path.dirname(__file__), '..', 'workspace')
        backtest_files = [f for f in os.listdir(workspace_dir) if 'backtest' in f.lower() and f.endswith('.py')]
        
        for bf in backtest_files:
            filepath = os.path.join(workspace_dir, bf)
            logger.info(f"📊 Running backtest: {bf}...")
            
            try:
                result = subprocess.run(
                    ["python", filepath],
                    capture_output=True, text=True, timeout=60,
                    cwd=workspace_dir
                )
                
                output = result.stdout[:2000] if result.stdout else "No output"
                errors = result.stderr[:500] if result.stderr else ""
                
                if result.returncode == 0:
                    logger.info(f"📊 Backtest {bf} completed:\n{output[:300]}")
                    log_agent_message(self.my_id, "ALL", f"📊 Backtest results:\n{output[:500]}", "status")
                    
                    if agent.memory:
                        agent.memory.remember_fact(f"backtest_{bf}", output[:500])
                    
                    if self.dashboard:
                        self.dashboard.add_log(f"📊 Backtest {bf}: SUCCESS")
                    
                    if self.telegram:
                        self.telegram.send_message(f"📊 *Backtest {bf}:*\n```\n{output[:300]}\n```")
                else:
                    logger.warning(f"📊 Backtest {bf} failed: {errors[:200]}")
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"📊 Backtest {bf} timeout (60s)")
            except Exception as e:
                logger.error(f"📊 Backtest error: {e}")

    async def _run_code_reviews(self):
        """Feature 4: Engineer reviews all workspace Python files"""
        engineer = self.agents.get("engineer")
        if not engineer:
            return
        
        workspace_dir = os.path.join(os.path.dirname(__file__), '..', 'workspace')
        if not os.path.exists(workspace_dir):
            return
        
        py_files = [f for f in os.listdir(workspace_dir) if f.endswith('.py')]
        if not py_files:
            return
        
        logger.info(f"🔍 Code Review Phase: {len(py_files)} files to review")
        
        for pyfile in py_files[:5]:  # Max 5 reviews per cycle
            filepath = os.path.join(workspace_dir, pyfile)
            review = await engineer.review_code(filepath)
            
            if review.get("reviewed"):
                logger.info(f"🔍 Review of {pyfile}: {review['review'][:150]}...")
                log_agent_message(
                    self.agent_ids.get("engineer"), self.my_id,
                    f"🔍 Code Review — {pyfile}:\n{review['review'][:300]}",
                    "status"
                )
                if self.dashboard:
                    self.dashboard.add_log(f"🔍 Code review: {pyfile} ✅")
                
                # Feature 10: Auto-Fix from Code Review
                review_text = review.get('review', '').lower()
                has_bugs = any(word in review_text for word in ['bug', 'error', 'lỗi', 'fix', 'critical', 'security'])
                if has_bugs:
                    from utils.backlog_manager import BacklogManager
                    fix_backlog = BacklogManager()
                    fix_backlog.add_task(
                        title=f"Auto-Fix: {pyfile}",
                        description=f"Fix issues found in code review of {pyfile}:\n{review['review'][:500]}",
                        assigned_to="engineer",
                        priority=2
                    )
                    logger.info(f"🔧 Feature 10: Auto-created fix task for {pyfile}")
                    if self.telegram:
                        self.telegram.send_message(f"🔧 Auto-Fix: Code review found issues in {pyfile}, fix task created")

    async def _run_voting_phase(self, backlog):
        """Feature 8: QA proposes strategy and agents vote"""
        if not self.voting:
            return
        
        quant = self.agents.get("quant_analyst")
        if not quant or not quant.llm:
            return
        
        # Check if there are strategy-related completed tasks
        tasks = backlog.get_all_tasks()
        strategy_tasks = [t for t in tasks if 'strategy' in t['title'].lower() and t['status'] == 'done']
        
        if not strategy_tasks:
            return
        
        # QA proposes deploying the strategy
        latest_strategy = strategy_tasks[-1]
        proposal_title = f"Deploy strategy: {latest_strategy['title']}"
        
        # Check if already voted on this
        existing = self.voting.get_open_proposals()
        if any(p['title'] == proposal_title for p in existing):
            return
        
        logger.info(f"🗳️ Voting Phase: QA proposes — {proposal_title}")
        
        proposal = self.voting.propose(
            title=proposal_title,
            description=f"Should we deploy {latest_strategy['title']}?",
            proposer="quant_analyst",
            voters=["data_scientist", "engineer", "devops"]
        )
        
        # Each agent votes using AI
        for voter_name in ["data_scientist", "engineer", "devops"]:
            voter = self.agents.get(voter_name)
            if voter and voter.llm:
                vote_thought = await voter.think(
                    f"Should we deploy this trading strategy? Consider quality, risk, and readiness.",
                    f"Proposal: {proposal_title}\nYour expertise: {voter_name}\nReply with ONLY: approve or reject"
                )
                
                decision = "approve" if "approve" in (vote_thought or "").lower() else "reject"
                self.voting.vote(proposal['id'], voter_name, decision, vote_thought[:100] if vote_thought else "")
        
        # Tally
        result = self.voting.tally(proposal['id'])
        logger.info(f"🗳️ Vote result: {result}")
        log_agent_message(self.my_id, "ALL", f"🗳️ {result}", "status")
        
        if self.telegram:
            self.telegram.send_vote_result(proposal_title, result)
        
        if self.dashboard:
            self.dashboard.update_votes(self.voting._load().get("proposals", []))
            self.dashboard.add_log(f"🗳️ {result}")

    async def pm_auto_plan(self) -> int:
        """
        PM Auto-Planning: Analyze completed tasks and generate next wave of work.
        Returns number of new tasks created.
        """
        from utils.backlog_manager import BacklogManager
        backlog = BacklogManager()
        
        tasks = backlog.get_all_tasks()
        done_tasks = [t for t in tasks if t["status"] == "done"]
        pending_tasks = [t for t in tasks if t["status"] in ("todo", "in_progress")]
        
        if pending_tasks:
            logger.info(f"Auto-plan skipped: {len(pending_tasks)} tasks still pending")
            return 0
        
        logger.info("\n" + "=" * 60)
        logger.info("🧠 PM AUTO-PLANNING: Generating next wave of tasks...")
        logger.info("=" * 60)
        
        # Gather context: completed tasks + workspace files
        workspace_files = []
        workspace_dir = os.path.join(os.path.dirname(__file__), '..', 'workspace')
        if os.path.exists(workspace_dir):
            for f in os.listdir(workspace_dir):
                filepath = os.path.join(workspace_dir, f)
                if os.path.isfile(filepath):
                    size = os.path.getsize(filepath)
                    workspace_files.append(f"{f} ({size} bytes)")
        
        # Gather agent memories
        agent_knowledge = {}
        for agent_name, agent in self.agents.items():
            if agent.memory:
                facts = agent.memory.recall_fact("all")
                agent_knowledge[agent_name] = facts if facts else "No memory"
        
        # Ask PM AI to plan next tasks
        planning_prompt = f"""Analyze completed work and plan the NEXT wave of tasks.

COMPLETED TASKS ({len(done_tasks)}):
{chr(10).join(f"- #{t['id']} [{t['assigned_to']}]: {t['title']}" for t in done_tasks)}

WORKSPACE FILES:
{chr(10).join(f"- {f}" for f in workspace_files) if workspace_files else "No files yet"}

AGENT KNOWLEDGE:
{json.dumps(agent_knowledge, indent=2, default=str)[:1000]}

AVAILABLE AGENTS:
- data_scientist: Data analysis, ML, feature engineering
- quant_analyst: Strategy design, risk analysis, backtesting rules
- engineer: Code quality, system architecture, optimization
- devops: Monitoring, deployment, CI/CD

RULES:
1. Create 3-5 NEW tasks that build on completed work
2. Each task MUST be actionable and specific
3. Assign to the most appropriate agent
4. Set correct dependencies (use task IDs from completed tasks)
5. Focus on IMPROVING the existing trading system

RESPOND IN THIS EXACT JSON FORMAT ONLY:
[
  {{"title": "task title", "description": "detailed description of what to do", "assigned_to": "agent_name", "priority": "high", "depends_on": null}},
  ...
]"""

        ai_response = self.pm_think("Generate next wave of tasks", planning_prompt)
        
        # Parse AI response to extract tasks
        new_tasks = self._parse_planned_tasks(ai_response)
        
        if not new_tasks:
            logger.warning("PM could not generate new tasks. Using fallback plan.")
            new_tasks = self._fallback_tasks(done_tasks)
        
        # Add tasks to backlog
        created_count = 0
        last_task_id = max(t["id"] for t in done_tasks) if done_tasks else 0
        
        for task_spec in new_tasks:
            try:
                # Resolve depends_on
                dep = task_spec.get("depends_on")
                
                new_task = backlog.add_task(
                    title=task_spec["title"],
                    description=task_spec.get("description", task_spec["title"]),
                    assigned_to=task_spec["assigned_to"],
                    priority=task_spec.get("priority", "medium"),
                    depends_on=dep
                )
                created_count += 1
                log_agent_message(
                    self.my_id, "ALL",
                    f"📝 New task #{new_task['id']}: {new_task['title']} → {new_task['assigned_to']}",
                    "task"
                )
            except Exception as e:
                logger.error(f"Failed to create task: {e}")
        
        logger.info(f"✅ PM Auto-Plan complete: {created_count} new tasks created")
        log_agent_message(self.my_id, "ALL", f"🧠 Auto-planned {created_count} new tasks. {backlog.get_summary()}", "status")
        
        return created_count
    
    def _parse_planned_tasks(self, ai_response: str) -> List[Dict]:
        """Parse AI-generated task list from PM response"""
        import re
        
        # Try to extract JSON array from response
        try:
            # Find JSON array in response
            match = re.search(r'\[[\s\S]*\]', ai_response)
            if match:
                tasks = json.loads(match.group())
                valid_agents = {"data_scientist", "quant_analyst", "engineer", "devops"}
                valid_tasks = []
                for t in tasks:
                    if isinstance(t, dict) and "title" in t and "assigned_to" in t:
                        if t["assigned_to"] in valid_agents:
                            valid_tasks.append(t)
                if valid_tasks:
                    return valid_tasks[:5]  # Max 5 tasks per wave
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse AI tasks: {e}")
        
        return []
    
    def _fallback_tasks(self, done_tasks: List[Dict]) -> List[Dict]:
        """Generate fallback tasks if AI planning fails"""
        done_titles = {t["title"].lower() for t in done_tasks}
        
        fallback_pool = [
            {
                "title": "Optimize strategy parameters",
                "description": "Use grid search to find optimal SMA periods and RSI thresholds. Test SMA(10,30), SMA(15,45), SMA(20,50) combinations. Report best Sharpe ratio.",
                "assigned_to": "quant_analyst",
                "priority": "high"
            },
            {
                "title": "Add risk management module",
                "description": "Write risk_manager.py in workspace/: implement position sizing (Kelly criterion), drawdown limits (max 5%), and portfolio heat tracking.",
                "assigned_to": "engineer",
                "priority": "high"
            },
            {
                "title": "Download additional currency pairs",
                "description": "Download 3 months data for GBPUSD, USDJPY, AUDUSD using yfinance. Save each as CSV in workspace/. Report statistics.",
                "assigned_to": "data_scientist",
                "priority": "medium"
            },
            {
                "title": "Create performance report generator",
                "description": "Write report_generator.py in workspace/: read backtest results and generate a summary report with equity curve data, drawdown chart data, and monthly returns.",
                "assigned_to": "data_scientist",
                "priority": "medium"
            },
            {
                "title": "Setup automated deployment script",
                "description": "Write deploy.py in workspace/: automated deployment script that validates all workspace files, runs health checks, and generates deployment report.",
                "assigned_to": "devops",
                "priority": "medium"
            }
        ]
        
        # Filter out already completed tasks
        new_tasks = [t for t in fallback_pool if t["title"].lower() not in done_titles]
        return new_tasks[:4]


async def main():
    """Main entry point — Fully autonomous scheduler with all v2 features"""
    project_manager = ProjectManager()
    cycle_interval = project_manager.config.get('pipeline', {}).get('cycle_interval', 60)
    max_cycles = project_manager.config.get('pipeline', {}).get('max_cycles', 0)  # 0 = infinite
    
    try:
        # Feature 17: Check for crash recovery
        if project_manager.recovery and project_manager.recovery.should_resume():
            resume = project_manager.recovery.get_resume_info()
            logger.info(f"🔄 RESUMING from checkpoint: cycle={resume['cycle']}, phase={resume['phase']}, crashes={resume['crash_count']}")
            if project_manager.telegram:
                project_manager.telegram.send_message(
                    f"🔄 Auto-Recovery: Resuming from cycle {resume['cycle']}, phase {resume['phase']}\n"
                    f"Crash count: {resume['crash_count']}"
                )
        
        # Start all agents (now includes risk_manager — Feature 14)
        await project_manager.start_all_agents()
        
        # Run initial standup
        await project_manager.run_daily_standup()
        
        # Wait for agents to settle
        logger.info("Waiting for agents to initialize...")
        await asyncio.sleep(3)
        
        # Feature 7: Start Dashboard
        if project_manager.dashboard:
            project_manager.dashboard.start()
            project_manager.dashboard.update_agents(project_manager.agents)
        
        # Populate initial backlog
        await project_manager.assign_initial_tasks()
        
        # Start monitoring in background
        monitor_task = asyncio.create_task(project_manager.monitor_agents_intelligent())
        
        # ============================================
        # AUTONOMOUS CYCLE LOOP (v2 — 9 Phases)
        # ============================================
        cycle = 0
        while True:
            cycle += 1
            if max_cycles > 0 and cycle > max_cycles:
                logger.info(f"Reached max cycles ({max_cycles}). Stopping.")
                break
            
            logger.info(f"\n{'🔄' * 20}")
            logger.info(f"AUTONOMOUS CYCLE #{cycle}")
            logger.info(f"{'🔄' * 20}\n")
            
            # Feature 17: Checkpoint cycle start
            if project_manager.recovery:
                project_manager.recovery.start_cycle(cycle)
            
            # Feature 23: Record cycle
            if project_manager.daily_reporter:
                project_manager.daily_reporter.record_cycle(cycle)
            
            # Feature 2: Telegram cycle start
            if project_manager.telegram:
                project_manager.telegram.send_cycle_start(cycle)
            
            # Feature 7: Dashboard cycle update
            if project_manager.dashboard:
                project_manager.dashboard.set_cycle(cycle)
                project_manager.dashboard.set_pipeline_status("running")
            
            # Feature 19: Git branch per cycle
            import subprocess
            branch_name = f"cycle-{cycle}"
            try:
                subprocess.run(["git", "checkout", "-b", branch_name], capture_output=True,
                            cwd=os.path.join(os.path.dirname(__file__), '..'), timeout=10)
                logger.info(f"🌿 Created branch: {branch_name}")
            except:
                pass
            
            # ---- Phase 1: Pipeline ----
            logger.info("📌 Phase 1: Running pipeline...")
            if project_manager.recovery:
                project_manager.recovery.set_phase("pipeline")
            await project_manager.run_continuous_pipeline()
            
            # ---- Phase 2: Code Review (Feature 4) ----
            logger.info("📌 Phase 2: Code Review...")
            if project_manager.recovery:
                project_manager.recovery.set_phase("code_review")
            await project_manager._run_code_reviews()
            
            # ---- Phase 3: Voting (Feature 8) ----
            logger.info("📌 Phase 3: Voting Phase...")
            if project_manager.recovery:
                project_manager.recovery.set_phase("voting")
            from utils.backlog_manager import BacklogManager
            backlog_for_vote = BacklogManager()
            await project_manager._run_voting_phase(backlog_for_vote)
            
            # ---- Phase 4: PM Auto-Planning ----
            logger.info("📌 Phase 4: PM Auto-Planning...")
            if project_manager.recovery:
                project_manager.recovery.set_phase("planning")
            new_tasks = await project_manager.pm_auto_plan()
            
            # ---- Phase 5: Cost Report (Feature 3) ----
            if project_manager.llm:
                cost_summary = project_manager.llm.get_cost_summary()
                logger.info(f"📌 Phase 5: {cost_summary}")
                
                # Feature 23: Record cost
                if project_manager.daily_reporter:
                    usage = project_manager.llm.get_usage_report()
                    project_manager.daily_reporter.record_cost(
                        usage.get('total_cost_usd', 0),
                        usage.get('total_tokens', 0),
                        usage.get('total_calls', 0)
                    )
                
                if project_manager.dashboard:
                    project_manager.dashboard.update_cost(project_manager.llm.get_usage_report())
                    project_manager.dashboard.add_log(cost_summary)
                
                if project_manager.telegram:
                    project_manager.telegram.send_cost_report(cost_summary)
            
            # ---- Phase 6: Health Check (Feature 18) ----
            if project_manager.health_monitor:
                logger.info("📌 Phase 6: Agent Health Check...")
                warnings = project_manager.health_monitor.check_health()
                for w in warnings:
                    logger.warning(w["message"])
                    if project_manager.telegram and w.get("severity") == "high":
                        project_manager.telegram.send_error(w["message"])
                logger.info(project_manager.health_monitor.get_summary_text())
            
            # ---- Phase 7: Leaderboard Update (Feature 16) ----
            if project_manager.leaderboard:
                logger.info(f"📌 Phase 7: {project_manager.leaderboard.get_leaderboard_text()}")
            
            # ---- Phase 8: Telegram pipeline done + notifications ----
            if project_manager.telegram:
                backlog_summary = BacklogManager()
                done_count = len([t for t in backlog_summary.get_all_tasks() if t['status'] == 'done'])
                project_manager.telegram.send_pipeline_done(done_count, cycle)
                
                if new_tasks > 0:
                    task_titles = [t['title'] for t in backlog_summary.get_all_tasks() if t['status'] == 'todo'][:5]
                    project_manager.telegram.send_auto_plan(task_titles)
            
            if new_tasks == 0:
                logger.info(f"No new tasks generated. Cooldown {cycle_interval}s before retry...")
                log_agent_message(
                    project_manager.my_id, "ALL",
                    f"💤 Cycle #{cycle} complete. No new tasks. Cooling down {cycle_interval}s...",
                    "status"
                )
            else:
                logger.info(f"🚀 {new_tasks} new tasks planned! Starting next pipeline immediately...")
                log_agent_message(
                    project_manager.my_id, "ALL",
                    f"🚀 Cycle #{cycle} complete. {new_tasks} new tasks → starting next cycle!",
                    "status"
                )
            
            # Feature 19: Merge branch back to main
            try:
                subprocess.run(["git", "add", "-A"], capture_output=True,
                            cwd=os.path.join(os.path.dirname(__file__), '..'), timeout=10)
                subprocess.run(["git", "commit", "-m", f"Cycle #{cycle} complete"],
                            capture_output=True, cwd=os.path.join(os.path.dirname(__file__), '..'), timeout=10)
                subprocess.run(["git", "checkout", "main"], capture_output=True,
                            cwd=os.path.join(os.path.dirname(__file__), '..'), timeout=10)
                subprocess.run(["git", "merge", branch_name, "--no-edit"], capture_output=True,
                            cwd=os.path.join(os.path.dirname(__file__), '..'), timeout=10)
                logger.info(f"🌿 Merged {branch_name} → main")
            except:
                pass
            
            # Feature 7: Dashboard cooldown
            if project_manager.dashboard:
                project_manager.dashboard.set_pipeline_status("cooldown")
            
            # Feature 17: Checkpoint before cooldown
            if project_manager.recovery:
                project_manager.recovery.set_phase("cooldown")
            
            # ---- Phase 9: Daily Report (Feature 23) ----
            # Send daily report every 5 cycles or on demand
            if project_manager.daily_reporter and cycle % 5 == 0:
                logger.info("📌 Phase 9: Sending Daily Report...")
                project_manager.daily_reporter.send_report(
                    agent_health_text=project_manager.health_monitor.get_summary_text() if project_manager.health_monitor else "",
                    leaderboard_text=project_manager.leaderboard.get_leaderboard_text() if project_manager.leaderboard else "",
                    paper_trading_text=project_manager.paper_trader.get_summary_text() if project_manager.paper_trader else "",
                    recovery_text=project_manager.recovery.get_status_text() if project_manager.recovery else ""
                )
            
            # Cooldown
            logger.info(f"⏳ Cooldown: {cycle_interval} seconds until next cycle...")
            await asyncio.sleep(cycle_interval)
            
    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        
        # Feature 17: Record crash for recovery
        if hasattr(project_manager, 'recovery') and project_manager.recovery:
            project_manager.recovery.record_crash(str(e)[:500])
        
        if hasattr(project_manager, 'telegram') and project_manager.telegram:
            project_manager.telegram.send_error(f"System crash: {str(e)[:300]}")
    finally:
        # Feature 23: Send final daily report
        if hasattr(project_manager, 'daily_reporter') and project_manager.daily_reporter:
            project_manager.daily_reporter.send_report(
                agent_health_text=project_manager.health_monitor.get_summary_text() if project_manager.health_monitor else "",
                leaderboard_text=project_manager.leaderboard.get_leaderboard_text() if project_manager.leaderboard else "",
                recovery_text=project_manager.recovery.get_status_text() if project_manager.recovery else ""
            )
        
        # Final cost report
        if project_manager.llm:
            logger.info(f"📊 FINAL {project_manager.llm.get_cost_summary()}")
        await project_manager.shutdown()
        logger.info("ML Trading Bot shutdown complete")


if __name__ == "__main__":
    os.makedirs('logs', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    asyncio.run(main())


