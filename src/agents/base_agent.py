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
    from utils.shared_memory import SharedMemory
except ImportError:
    DeepSeekClient = None
    AgentTools = None
    AgentMemory = None
    SharedMemory = None
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
        self.project_context = ""  # Loaded from project_context.md
        
        # Load project context
        context_path = os.path.join(os.path.dirname(__file__), '..', '..', 'project_context.md')
        if os.path.exists(context_path):
            try:
                with open(context_path, 'r', encoding='utf-8') as f:
                    self.project_context = f.read()
                self.logger.info(f"Loaded project context ({len(self.project_context)} chars)")
            except Exception as e:
                self.logger.warning(f"Failed to load project context: {e}")
        
        if AgentTools:
            self.tools = AgentTools(workspace_dir=os.path.join(os.path.dirname(__file__), '..', '..', 'workspace'))

        if AgentMemory:
            self.memory = AgentMemory(agent_name=agent_name, memory_dir=os.path.join(os.path.dirname(__file__), '..', '..', 'memory'))
        
        # Feature 9: Shared memory
        self.shared_memory = None
        if SharedMemory:
            self.shared_memory = SharedMemory(os.path.join(os.path.dirname(__file__), '..', '..', 'shared_memory.json'))
            
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
            project_ctx = f"\n\nPROJECT CONTEXT:\n{self.project_context}" if self.project_context else ""
            
            # Feature 9: Inject shared memory context
            shared_ctx = ""
            if self.shared_memory:
                shared_ctx = self.shared_memory.get_context_for_agent(self.name)
                if shared_ctx:
                    shared_ctx = f"\n\nSHARED KNOWLEDGE FROM OTHER AGENTS:\n{shared_ctx}"
            
            prompt = [
                {"role": "system", "content": f"""You are the {self.name} of an advanced AI Trading System. 
                Your role is detailed, professional, and proactive. Respond as if you are a real expert in your field.
                {role_context}
                {project_ctx}
                {shared_ctx}
                
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
                
                6. GIT_COMMIT: Stage and commit all changes to git.
                   Usage: [JSON_CMD: {{"tool": "GIT_COMMIT", "args": {{"message": "commit message"}}}}]
                   
                7. GIT_PUSH: Push commits to GitHub.
                   Usage: [JSON_CMD: {{"tool": "GIT_PUSH", "args": {{}}}}]
                   
                8. GIT_STATUS: Check current git status.
                   Usage: [JSON_CMD: {{"tool": "GIT_STATUS", "args": {{}}}}]
                
                CRITICAL: When assigned a task to "learn" or "remember" something, you MUST use the LEARN tool immediately.
                When asked to "recall" or "check" if you know something, use the RECALL tool.
                After completing significant work, use GIT_COMMIT to save your changes.
                
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
                
            elif cmd_name == "GIT_COMMIT":
                message = args.get('message', 'Auto-commit by agent')
                return self.tools.git_commit(message)
                
            elif cmd_name == "GIT_PUSH":
                return self.tools.git_push()
                
            elif cmd_name == "GIT_STATUS":
                return self.tools.git_status()
                
            else:
                return f"Error: Unknown command {cmd_name}"
                
        except Exception as e:
            return f"Error executing {cmd_name}: {e}"

    async def execute_with_retry(self, task_description: str, max_rounds: int = 3) -> Dict[str, Any]:
        """
        Multi-round execution loop with self-correction.
        Think → Act → Auto-Run Code → Verify → Fix (if error) → Retry
        """
        last_error = None
        all_outputs = []
        
        # Feature 11: Inject failure history
        failure_context = ""
        if self.memory:
            keywords = task_description.split()[:3]
            for kw in keywords:
                fh = self.memory.get_failure_history(kw)
                if fh:
                    failure_context = f"\n\n{fh}"
                    break
        
        for round_num in range(1, max_rounds + 1):
            self.logger.info(f"{self.name}: Round {round_num}/{max_rounds} for: {task_description[:60]}...")
            
            # Build context with error history
            context = task_description + failure_context
            if last_error:
                context += f"\n\nPREVIOUS ATTEMPT FAILED with error:\n{last_error}\nPlease fix the issue and try again."
            
            # Think
            thought = await self.think(context, task_description)
            if not thought or "Error thinking" in thought:
                last_error = f"Thinking failed: {thought}"
                continue
            
            # Act (write files, execute commands)
            action_result = await self.act(thought)
            if action_result:
                all_outputs.append(action_result)
            
            # Check for errors in action results
            if action_result and "Error" in action_result:
                last_error = action_result
                self.logger.warning(f"{self.name}: Round {round_num} had errors, retrying...")
                continue
            
            # Auto-run any Python files that were written
            code_run_result = await self._auto_run_code(action_result)
            if code_run_result:
                all_outputs.append(code_run_result)
                if "Error" in code_run_result or "Traceback" in code_run_result:
                    last_error = f"Code execution failed:\n{code_run_result}"
                    self.logger.warning(f"{self.name}: Code run failed, retrying...")
                    continue
            
            # Validate — check if expected files were created
            validation = await self.validate_output(thought, action_result)
            if validation["valid"]:
                return {
                    "status": "success",
                    "output": "\n".join(all_outputs) if all_outputs else thought[:500],
                    "rounds": round_num
                }
            else:
                last_error = validation["reason"]
                self.logger.warning(f"{self.name}: Validation failed: {last_error}")
                continue
        
        # All rounds exhausted
        # Feature 11: Remember this failure
        if self.memory and last_error:
            self.memory.remember_failure(task_description[:100], last_error[:300], max_rounds)
        
        return {
            "status": "partial",
            "output": "\n".join(all_outputs) if all_outputs else f"Completed with issues after {max_rounds} rounds",
            "error": last_error,
            "rounds": max_rounds
        }
    
    async def validate_output(self, thought: str, action_result: str) -> Dict:
        """Verify that expected output files were actually created"""
        import re
        
        # Extract filenames mentioned in thought
        file_patterns = re.findall(r'[\w_]+\.(?:py|csv|json|txt|yaml|md)', thought or "")
        
        if not file_patterns or not self.tools:
            return {"valid": True, "reason": "No files to validate"}
        
        missing = []
        for filename in set(file_patterns):
            filepath = self.tools._get_safe_path(filename)
            if not os.path.exists(filepath):
                # Also check repo root
                root_path = os.path.join(self.tools.repo_dir, filename)
                if not os.path.exists(root_path):
                    missing.append(filename)
        
        if missing:
            return {"valid": False, "reason": f"Expected files not found: {', '.join(missing)}"}
        return {"valid": True, "reason": "All expected files exist"}
    
    async def _auto_run_code(self, action_result: str) -> Optional[str]:
        """
        Feature 1: Auto-run Python files that were just written.
        Returns execution output or None if no files to run.
        """
        if not action_result or not self.tools:
            return None
        
        # Extract filenames from WRITE_FILE results
        written_files = re.findall(r'WRITE_FILE.*?(?:workspace[/\\])?(\w+\.py)', action_result)
        if not written_files:
            return None
        
        results = []
        for filename in set(written_files):
            filepath = self.tools._get_safe_path(filename)
            if not os.path.exists(filepath):
                # Check repo root too
                filepath = os.path.join(self.tools.repo_dir, filename)
            
            if not os.path.exists(filepath):
                continue
            
            self.logger.info(f"{self.name}: Auto-running {filename}...")
            try:
                import subprocess
                result = subprocess.run(
                    ["python", filepath],
                    capture_output=True, text=True, timeout=30,
                    cwd=self.tools.workspace_dir if self.tools else None
                )
                
                output = result.stdout[:1000] if result.stdout else ""
                errors = result.stderr[:1000] if result.stderr else ""
                
                if result.returncode != 0:
                    results.append(f"❌ {filename} FAILED (exit {result.returncode}):\n{errors}")
                    self.logger.warning(f"{self.name}: {filename} execution failed")
                else:
                    results.append(f"✅ {filename} OK: {output[:200]}")
                    self.logger.info(f"{self.name}: {filename} executed successfully")
                    
            except subprocess.TimeoutExpired:
                results.append(f"⏰ {filename} TIMEOUT (30s)")
            except Exception as e:
                results.append(f"❌ {filename} Error: {str(e)[:200]}")
        
        return "\n".join(results) if results else None
    
    async def review_code(self, filepath: str) -> Dict[str, Any]:
        """
        Feature 4: Cross-agent code review using LLM.
        Reads a file and asks LLM to review code quality.
        """
        if not self.tools or not self.llm:
            return {"reviewed": False, "reason": "Tools/LLM not available"}
        
        # Read the file
        try:
            if not os.path.isabs(filepath):
                filepath = self.tools._get_safe_path(filepath)
            
            if not os.path.exists(filepath):
                return {"reviewed": False, "reason": f"File not found: {filepath}"}
            
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            return {"reviewed": False, "reason": str(e)}
        
        filename = os.path.basename(filepath)
        
        review_prompt = [
            {"role": "system", "content": f"""You are a senior code reviewer for an AI Trading System.
Review the code and provide:
1. QUALITY SCORE (1-10)
2. BUGS or ISSUES found
3. SUGGESTIONS for improvement
4. SECURITY concerns
Be concise. Reply in Vietnamese."""},
            {"role": "user", "content": f"Review this file ({filename}):\n```python\n{code[:3000]}\n```"}
        ]
        
        try:
            review = self.llm.chat_completion(review_prompt)
            self.logger.info(f"{self.name}: Code review completed for {filename}")
            return {
                "reviewed": True,
                "file": filename,
                "review": review,
                "code_length": len(code)
            }
        except Exception as e:
            return {"reviewed": False, "reason": str(e)}


    
    def send_message(self, to_agent: str, message: str, msg_type: str = "message"):
        """Send a direct message to another agent"""
        to_id = self.agent_ids.get(to_agent, to_agent)
        try:
            log_agent_message(
                from_agent=self.my_id,
                to_agent=to_id,
                message=message,
                message_type=msg_type
            )
            self.logger.info(f"{self.name} -> {to_agent}: {message[:80]}...")
        except Exception as e:
            self.logger.error(f"Failed to send message to {to_agent}: {e}")

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
