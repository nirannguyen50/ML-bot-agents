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
        """Assign tasks from backlog to agents in a pipeline"""
        logger.info("=" * 50)
        logger.info("STARTING BACKLOG-DRIVEN TASK PIPELINE")
        logger.info("=" * 50)
        
        from utils.backlog_manager import BacklogManager
        backlog = BacklogManager()
        
        # Pre-populate backlog with trading strategy pipeline
        if not backlog.get_all_tasks():
            logger.info("Populating backlog with trading strategy tasks...")
            
            # Stage 1: Data Scientist — Get data
            t1 = backlog.add_task(
                title="Download EURUSD market data",
                description="Download 3 months of EURUSD daily data using yfinance. Save as CSV. Report row count and date range.",
                assigned_to="data_scientist",
                priority="critical"
            )
            
            # Stage 2: Data Scientist — Feature engineering
            t2 = backlog.add_task(
                title="Calculate technical indicators",
                description="Write a Python script that reads the EURUSD CSV and calculates: SMA(20), SMA(50), RSI(14), MACD. Save results to eurusd_features.csv.",
                assigned_to="data_scientist",
                priority="high",
                depends_on=t1["id"]
            )
            
            # Stage 3: Quant Analyst — Strategy design
            t3 = backlog.add_task(
                title="Design SMA crossover strategy",
                description="Write a trading strategy document: entry when SMA20 crosses above SMA50, exit when crosses below. Define position sizing (1% risk per trade), stop loss (ATR-based), and expected Sharpe ratio. Save as strategy_sma_crossover.py.",
                assigned_to="quant_analyst",
                priority="high",
                depends_on=t2["id"]
            )
            
            # Stage 4: Engineer — Backtest
            t4 = backlog.add_task(
                title="Write backtest engine",
                description="Write a Python backtest script (backtest_sma.py) that reads eurusd_features.csv and tests the SMA crossover strategy. Output: total trades, win rate, profit factor, max drawdown.",
                assigned_to="engineer",
                priority="high",
                depends_on=t3["id"]
            )
            
            # Stage 5: DevOps — Monitoring
            t5 = backlog.add_task(
                title="Create system health monitor",
                description="Write a health_check.py script that checks: disk space, memory usage, data freshness (last CSV modified time), and number of agent log files. Output a JSON health report.",
                assigned_to="devops",
                priority="medium",
                depends_on=None  # Can run independently
            )
            
            log_agent_message(self.my_id, "ALL", f"Backlog loaded: {backlog.get_summary()}", "task")

        # PM evaluates backlog state with AI
        pm_analysis = self.pm_think(
            "Review current backlog and decide task priorities",
            f"Backlog: {backlog.get_summary()}"
        )
        log_agent_message(self.my_id, "ALL", f"📊 PM Analysis: {pm_analysis}", "status")

        # Process backlog — assign tasks to each agent
        for agent_name, agent in self.agents.items():
            task = backlog.get_next_task(agent_name)
            if not task:
                logger.info(f"No pending tasks for {agent_name}")
                continue
            
            task_id = task["id"]
            agent_id = self.agent_ids.get(agent_name)
            
            # PM announces task
            logger.info(f"Assigning task #{task_id} to {agent_name}: {task['title']}")
            log_agent_message(
                self.my_id, agent_id,
                f"📋 Task #{task_id}: {task['title']}\n{task['description']}",
                "task"
            )
            
            # Mark as in progress
            backlog.update_status(task_id, "in_progress")
            
            # Agent thinks about the task
            thought = await agent.think(
                f"You have been assigned task #{task_id}: {task['title']}",
                task['description']
            )
            log_agent_message(agent_id, self.my_id, thought, "status")
            
            # Agent acts on its thought
            action_result = await agent.act(thought)
            if action_result:
                log_agent_message(agent_id, self.my_id, f"Action result: {action_result[:500]}", "status")
            
            # Execute the task
            result = await agent.execute_task({
                'type': task['title'],
                'description': task['description']
            })
            
            if result.get('status') == 'success':
                backlog.update_status(task_id, "done")
                report = f"✅ Task #{task_id} Complete: {result.get('output', '')[:300]}"
                log_agent_message(agent_id, self.my_id, report, "status")
                
                # Agent learns what it did
                if agent.memory:
                    agent.memory.remember_fact(
                        f"task_{task_id}_result",
                        f"Completed: {task['title']}"
                    )
            else:
                backlog.update_status(task_id, "blocked")
                error = f"❌ Task #{task_id} Failed: {result.get('error', 'Unknown error')}"
                log_agent_message(agent_id, self.my_id, error, "error")
            
            logger.info(f"Task #{task_id} result: {result.get('status', 'unknown')}")
        
        # Git commit after all tasks
        logger.info("Committing task results to git...")
        if 'engineer' in self.agents and self.agents['engineer'].tools:
            commit_result = self.agents['engineer'].tools.git_commit(
                f"feat: backlog tasks completed at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            logger.info(f"Git commit: {commit_result}")
            push_result = self.agents['engineer'].tools.git_push()
            logger.info(f"Git push: {push_result}")
        
        log_agent_message(self.my_id, "ALL", f"Pipeline complete. {backlog.get_summary()}", "status")


async def main():
    """Main entry point"""
    project_manager = ProjectManager()
    
    try:
        # Start all agents
        await project_manager.start_all_agents()
        
        # Run initial standup
        await project_manager.run_daily_standup()
        
        # Wait for agents to settle
        logger.info("Waiting for agents to initialize memory...")
        await asyncio.sleep(5)
        
        # Assign initial real tasks
        await project_manager.assign_initial_tasks()
        
        # Start monitoring in background
        monitor_task = asyncio.create_task(project_manager.monitor_agents_intelligent())
        
        # Keep running until interrupted
        logger.info("\nML Trading Bot Agents are now running! (AI Mode)")
        logger.info("Press Ctrl+C to shutdown gracefully\n")
        
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await project_manager.shutdown()
        logger.info("ML Trading Bot shutdown complete")


if __name__ == "__main__":
    os.makedirs('logs', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    asyncio.run(main())
