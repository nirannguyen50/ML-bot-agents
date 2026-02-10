"""
DeepSeek LLM Client
Wrapper for OpenAI-compatible DeepSeek API
"""

import os
import logging
from typing import List, Dict, Any, Optional
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

class DeepSeekClient:
    """Client for interacting with DeepSeek API"""
    
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        """
        Initialize DeepSeek client
        
        Args:
            api_key: DeepSeek API Key
            model: Model to use (default: deepseek-chat)
        """
        if OpenAI is None:
            logger.error("openai package not installed. Please run: pip install openai")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            
        self.model = model
    
    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """
        Get chat completion from DeepSeek
        """
        if self.client is None:
            return "Error: LLM client not initialized (missing openai package)"
            
        # Add system prompt for Vietnamese if not present
        if not any(m['role'] == 'system' for m in messages):
            messages.insert(0, {"role": "system", "content": "You are a helpful AI assistant. Always respond in Vietnamese unless asked otherwise."})
            
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=4000,
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek API Error: {e}")
            return f"Error communicating with AI: {str(e)}"

    async def chat_completion_async(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """
        Async version of chat completion
        """
        return self.chat_completion(messages, temperature)
