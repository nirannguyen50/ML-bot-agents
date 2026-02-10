import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio
import sys
import os
import json

# Add parent directory to path to find agent_communication_logger
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    from agent_communication_logger import log_agent_message
except ImportError:
    # Fallback if module not found
    def log_agent_message(*args, **kwargs): pass

# Import DeepSeek Client
try:
    # Try importing assuming run from scripts/
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from utils.llm_client import DeepSeekClient
    from utils.agent_tools import AgentTools
    from utils.memory import AgentMemory
except ImportError:
    DeepSeekClient = None
    AgentTools = None
    AgentMemory = None
import re


class BaseAgent(ABC):
    """Base class for all ML Trading Bot agents"""
    
    def __init__(self, config: Dict[str, Any], agent_name: str, api_key: str = None):
        """
        Initialize base agent
        
        Args:
            config: Project configuration dictionary
            agent_name: Name of the agent
            api_key: DeepSeek API Key (optional)
        """
        self.config = config
        self.name = agent_name
        self.logger = logging.getLogger(f"agent.{agent_name}")
        self.is_initialized = False
        self.tasks = []
        
        # Initialize LLM Client
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.llm = None
        self.tools = None
        self.memory = None
        self.role_instruction = ""  # Override in subclass for role-specific behavior
        
        if AgentTools:
            self.tools = AgentTools(workspace_dir=os.path.join(os.path.dirname(__file__), '..', '..', 'workspace'))

        if AgentMemory:
            self.memory = AgentMemory(agent_name=agent_name, memory_dir=os.path.join(os.path.dirname(__file__), '..', '..', 'memory'))
            
        if self.api_key and DeepSeekClient:
            try:
                self.llm = DeepSeekClient(api_key=self.api_key)
                self.logger.info(f"LLM Client initialized for {agent_name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize LLM: {e}")
        else:
            self.logger.warning(f"LLM Client NOT initialized for {agent_name} (Missing API Key or Client)")
        
        # Agent status
        self.status = {
            'state': 'created',
            'last_activity': None,
            'errors': [],
            'performance': {}
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
        
        # Get my ID
        self.my_id = self.agent_ids.get(agent_name, f"agent:main:{agent_name}")
        
        # Conversation history for context
        self.conversation_history = []
        
    @abstractmethod
    async def initialize(self) -> bool:
        pass
    
    @abstractmethod
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def think(self, context: str, task: str = None) -> str:
        """
        Use LLM to think about the current situation
        """
        if not self.llm:
            return "Thinking... (LLM not available)"
            
        try:
            role_context = f"\n\nYOUR ROLE INSTRUCTIONS:\n{self.role_instruction}" if self.role_instruction else ""
            
            prompt = [
                {"role": "system", "content": f"""You are the {self.name} of an advanced AI Trading System. 
                Your role is detailed, professional, and proactive. Respond as if you are a real expert in your field.
                {role_context}
                
                You have access to the following TOOLS to perform actions.
                IMPORTANT: To use a tool, you MUST use the following JSON format:
                [JSON_CMD: {{"tool": "TOOL_NAME", "args": {{"key": "value"}}}}]
                
                Available Tools:
                1. WRITE_FILE: Create or overwrite a file.
                   Usage: 
                   [WRITE_FILE: filename.py]
                   def hello():
                       print("World")
                   [END_WRITE_FILE]
                   IMPORTANT: Provide ONLY the code block when writing files. No conversational filler.
                   
                2. READ_FILE: Read a file's content.
                   Usage: [JSON_CMD: {{"tool": "READ_FILE", "args": {{"target": "filename.py"}}}}]
                   
                3. EXECUTE: Run a terminal command (python, dir, etc).
                   Usage: [JSON_CMD: {{"tool": "EXECUTE", "args": {{"target": "python filename.py"}}}}]
                   
                4. LEARN: Store knowledge in long-term memory.
                   Usage: [JSON_CMD: {{"tool": "LEARN", "args": {{"key": "concept_name", "value": "description"}}}}]
                   
                5. RECALL: Retrieve knowledge from long-term memory.
                   Usage: [JSON_CMD: {{"tool": "RECALL", "args": {{"key": "concept_name"}}}}]
                
                CRITICAL: When assigned a task to "learn" or "remember" something, you MUST use the LEARN tool immediately.
                When asked to "recall" or "check" if you know something, use the RECALL tool.
                
                When you need to perform an action, include the command in your response.
                Reply in Vietnamese mainly, but use English for code and technical terms."""},
                {"role": "user", "content": f"Here is the context: {context}\n\nTask/Question: {task}\n\nProvide a professional response."}
            ]
            
            response = self.llm.chat_completion(prompt)
            return response
        except Exception as e:
            self.logger.error(f"Thinking error: {e}")
            return f"Error thinking: {e}"
            return f"Error thinking: {e}"

    async def act(self, thought: str) -> str:
        """
        Parse thought for commands and execute them
        Format: [JSON_CMD: {"tool": "TOOL_NAME", "args": {...}}]
        Also supports legacy: [CMD: NAME key='val']
        """
        if not self.tools:
            return "Error: Tools not initialized."
            
        results = []
        # 0. Try CODE_BLOCK Format (Best for writing files)
        # [WRITE_FILE: filename.py]
        # content
        # [END_WRITE_FILE]
        block_pattern = r"\[WRITE_FILE:\s*(.*?)\](.*?)\[END_WRITE_FILE\]"
        block_matches = re.findall(block_pattern, thought, re.DOTALL)
        
        for filename, content in block_matches:
            filename = filename.strip()
            content = content.strip()
            result = self.tools.write_file(filename, content)
            results.append(f"BLOCK_CMD WRITE_FILE: {result}")

        # 1. Try JSON Format (Preferred for other tools)
        # Regex to capture JSON content. \s* allows for newlines/spaces before the closing ]
        json_pattern = r"\[JSON_CMD:\s*({.*?})\s*\]"
        json_matches = re.findall(json_pattern, thought, re.DOTALL)
        
        for json_str in json_matches:
            try:
                cmd_data = json.loads(json_str)
                cmd_name = cmd_data.get('tool', '').upper()
                args = cmd_data.get('args', {})
                
                result = self._execute_tool(cmd_name, args)
                results.append(f"JSON_CMD {cmd_name}: {result}")
            except json.JSONDecodeError as e:
                results.append(f"Error parsing JSON_CMD: {e}")
                
        # 2. Try Legacy Regex Format (Fallback)
        if not results:
            cmd_pattern = r"\[CMD:\s*(\w+)\s*(.*?)\]"
            matches = re.findall(cmd_pattern, thought, re.DOTALL)
            
            for cmd_name, args_str in matches:
                cmd_name = cmd_name.upper()
                arg_pattern = r"(\w+)=(?:'([^']*)'|\"([^\"]*)\")"
                args_matches = re.findall(arg_pattern, args_str, re.DOTALL)
                
                args = {}
                for key, val_single, val_double in args_matches:
                    val = val_single if val_single else val_double
                    args[key] = val
                
                result = self._execute_tool(cmd_name, args)
                results.append(f"CMD {cmd_name}: {result}")
            
        return "\n".join(results) if results else None

    def _execute_tool(self, cmd_name: str, args: Dict[str, Any]) -> str:
        """Execute a single tool command"""
        try:
            if cmd_name == "WRITE_FILE":
                filename = args.get('target') or args.get('filename')
                content = args.get('content')
                if filename and content:
                    return self.tools.write_file(filename, content)
                return "Error: Missing target or content."
                    
            elif cmd_name == "READ_FILE":
                filename = args.get('target') or args.get('filename')
                if filename:
                    return self.tools.read_file(filename)
                return "Error: Missing target."
                    
            elif cmd_name == "EXECUTE" or cmd_name == "RUN":
                cmd = args.get('target') or args.get('command')
                if cmd:
                    return self.tools.run_command(cmd)
                return "Error: Missing command."
                
            elif cmd_name == "LEARN":
                key = args.get('key')
                value = args.get('value')
                if self.memory and key and value:
                    return self.memory.remember_fact(key, value)
                return "Error: Memory not initialized or missing key/value."
                
            elif cmd_name == "RECALL":
                key = args.get('key')
                if self.memory:
                    if key:
                        return self.memory.recall_fact(key)
                    else:
                        return self.memory.get_all_facts()
                return "Error: Memory not initialized."
                
            else:
                return f"Error: Unknown command {cmd_name}"
                
        except Exception as e:
            return f"Error executing {cmd_name}: {e}"
        return {
            'agent_name': self.name,
            'is_initialized': self.is_initialized,
            'status': self.status,
            'active_tasks': len(self.tasks),
            'config_section': self.config.get(self.name, {})
        }
    
    async def log_activity(self, activity: str, level: str = "INFO"):
        # 1. Standard file logging
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(f"{self.name}: {activity}")
        
        self.status['last_activity'] = activity
        
        # 2. Agent communication logging (Chat)
        try:
            msg_type = "status"
            if level == "ERROR":
                msg_type = "error"
            elif level == "WARNING":
                msg_type = "alert"
                
            log_agent_message(
                from_agent=self.my_id,
                to_agent=self.agent_ids["project_manager"],
                message=activity,
                message_type=msg_type
            )
        except Exception as e:
            self.logger.debug(f"Failed to log to comms system: {e}")
            
    async def receive_message(self, from_agent: str, message: str):
        self.conversation_history.append(f"{from_agent}: {message}")
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
