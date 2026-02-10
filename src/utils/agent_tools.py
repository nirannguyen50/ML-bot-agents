"""
Agent Tools Library
Provides capabilities for agents to interact with the file system and terminal.
"""

import os
import subprocess
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class AgentTools:
    """Collection of tools for autonomous agents"""
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        os.makedirs(self.workspace_dir, exist_ok=True)
        
    def _get_safe_path(self, filename: str) -> str:
        """Ensure file access is restricted to workspace"""
        # Remove any directory traversal attempts
        filename = os.path.basename(filename) 
        return os.path.join(self.workspace_dir, filename)

    def write_file(self, filename: str, content: str) -> str:
        """
        Write content to a file in the workspace
        
        Args:
            filename: Name of the file
            content: Content to write
            
        Returns:
            Success message or error
        """
        try:
            filepath = self._get_safe_path(filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote to {filename}"
        except Exception as e:
            return f"Error writing file: {e}"

    def read_file(self, filename: str) -> str:
        """
        Read content from a file
        
        Args:
            filename: Name of the file
            
        Returns:
            File content or error
        """
        try:
            filepath = self._get_safe_path(filename)
            if not os.path.exists(filepath):
                return f"Error: File {filename} does not exist"
                
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"
            
    def run_command(self, command: str) -> str:
        """
        Run a shell command
        
        Args:
            command: Command string (e.g., 'python script.py')
            
        Returns:
            Combined stdout/stderr output
        """
        # Security: Allow only python execution or listing dir for now
        allowed_cmds = ["python", "dir", "ls", "pip"]
        if not any(command.strip().startswith(cmd) for cmd in allowed_cmds):
            return "Error: Command not allowed. Only python, dir, ls, pip are permitted."
            
        try:
            # Run in workspace dir
            result = subprocess.run(
                command,
                cwd=self.workspace_dir,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout
            if result.stderr:
                output += f"\nErrors:\n{result.stderr}"
            return output if output.strip() else "Command executed with no output."
        except subprocess.TimeoutExpired:
            return "Error: Command timed out."
        except Exception as e:
            return f"Error running command: {e}"
