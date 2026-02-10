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
        """Assign initial real-world tasks to agents"""
        logger.info("Assigning initial tasks...")
        
        # 1. Data Scientist: Download Market Data
        if 'data_scientist' in self.agents:
            ds_agent = self.agents['data_scientist']
            ds_id = self.agent_ids.get('data_scientist')
            
            # Manager Instruction
            instruction = "We need a utility script to calculate SMA. Please write and test it immediately."
            log_agent_message(
                from_agent=self.my_id,
                to_agent=ds_id,
                message=f"Task Assignment: {instruction}",
                message_type="task"
            )
            
            # Execute Task
            # We explicitly trigger a memory test task here
            task_payload = {
                'type': 'memory_test',
                'description': 'Please learn that "The project started in 2026". Then recall this fact to confirm you remember it.'
            }
            
            # Agent confirms receipt
            confirm_msg = await ds_agent.think(f"Project Manager assigned task: {instruction}", "Confirm you are starting the download.")
            log_agent_message(ds_id, self.my_id, confirm_msg, "status")
            
            # Agent executes
            # Force a manual LEARN command to ensure it works
            logger.info("Forcing manual LEARN command...")
            learn_cmd = '[JSON_CMD: {"tool": "LEARN", "args": {"key": "project_start_date", "value": "2026-02-11"}}]'
            await ds_agent.act(learn_cmd)
            
            result = await ds_agent.execute_task(task_payload)
            
            # Agent reports completion
            if result.get('status') == 'success':
                report_msg = f"Task Complete: {result.get('output')}"
                log_agent_message(ds_id, self.my_id, report_msg, "status")
            else:
                error_msg = f"Task Failed: {result.get('error')}"
                log_agent_message(ds_id, self.my_id, error_msg, "error")


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
