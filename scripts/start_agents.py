#!/usr/bin/env python3
"""
Start ML Trading Bot Agents
This script initializes and coordinates all project agents using DeepSeek LLM
"""

import asyncio
import logging
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
    
    def __init__(self, config_path: str = '../config/settings.yaml'):
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
            
            for agent_name, agent_class in agents_to_start.items():
                await self.start_agent(agent_name, agent_class)
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
        """Execute a single task with self-correction and agent handoff"""
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
        
        # Use multi-round self-correction
        result = await agent.execute_with_retry(task['description'], max_rounds=max_retries)
        
        rounds_used = result.get('rounds', 1)
        
        if result.get('status') in ('success', 'partial'):
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
            backlog.update_status(task_id, "blocked")
            error = f"❌ Task #{task_id} Failed after {rounds_used} rounds: {result.get('error', 'Unknown')}"
            log_agent_message(agent_id, self.my_id, error, "error")
            logger.error(error)
    
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
                    # Send to the next agent
                    next_agent.send_message("project_manager", f"Ready for task: {task['title']}")
                    await next_agent.receive_message("project_manager", handoff_msg)
                    
                    log_agent_message(
                        self.my_id,
                        self.agent_ids.get(next_agent_name),
                        handoff_msg,
                        "task"
                    )
                    logger.info(f"🔗 Handoff: {completed_task['assigned_to']} → {next_agent_name}")


async def main():
    """Main entry point"""
    project_manager = ProjectManager()
    
    try:
        # Start all agents
        await project_manager.start_all_agents()
        
        # Run initial standup
        await project_manager.run_daily_standup()
        
        # Wait for agents to settle
        logger.info("Waiting for agents to initialize...")
        await asyncio.sleep(3)
        
        # Populate backlog
        await project_manager.assign_initial_tasks()
        
        # Start monitoring in background
        monitor_task = asyncio.create_task(project_manager.monitor_agents_intelligent())
        
        # Run continuous pipeline (replaces one-shot execution)
        logger.info("\n🚀 Starting Continuous Pipeline...")
        await project_manager.run_continuous_pipeline()
        
        # Pipeline complete — keep monitoring
        logger.info("\nML Trading Bot Agents — Pipeline complete! Monitoring active.")
        logger.info("Press Ctrl+C to shutdown gracefully\n")
        
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await project_manager.shutdown()
        logger.info("ML Trading Bot shutdown complete")


if __name__ == "__main__":
    os.makedirs('logs', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    asyncio.run(main())

