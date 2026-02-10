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
        self.repo_dir = os.path.abspath(os.path.join(workspace_dir, '..'))
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
        # Security: Whitelist allowed commands
        allowed_cmds = ["python", "dir", "ls", "pip", "git"]
        if not any(command.strip().startswith(cmd) for cmd in allowed_cmds):
            return "Error: Command not allowed. Only python, dir, ls, pip, git are permitted."
        
        # Security: Block dangerous patterns
        blocked_patterns = ["rm -rf", "del /s", "format", "shutdown", "&&", "||", "|", ">>", "curl", "wget", "powershell", "cmd /c"]
        cmd_lower = command.lower()
        for pattern in blocked_patterns:
            if pattern in cmd_lower:
                return f"Error: Blocked pattern '{pattern}' detected in command."
            
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

    def git_status(self) -> str:
        """Check git status of the repo"""
        try:
            result = subprocess.run(
                "git status --short",
                cwd=self.repo_dir, shell=True,
                capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip() or "Working tree clean."
        except Exception as e:
            return f"Error: {e}"

    def git_commit(self, message: str) -> str:
        """Stage all changes and commit"""
        try:
            subprocess.run("git add -A", cwd=self.repo_dir, shell=True, capture_output=True, timeout=10)
            result = subprocess.run(
                f'git commit -m "{message}"',
                cwd=self.repo_dir, shell=True,
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout + result.stderr
            return output.strip() or "Nothing to commit."
        except Exception as e:
            return f"Error: {e}"

    def git_push(self) -> str:
        """Push commits to origin/main"""
        try:
            result = subprocess.run(
                "git push origin main",
                cwd=self.repo_dir, shell=True,
                capture_output=True, text=True, timeout=30
            )
            output = result.stdout + result.stderr
            return output.strip() or "Push completed."
        except Exception as e:
            return f"Error: {e}"
