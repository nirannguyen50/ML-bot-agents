"""
DeepSeek LLM Client
Wrapper for OpenAI-compatible DeepSeek API with cost tracking
"""

import os
import logging
from typing import List, Dict, Any, Optional
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

# DeepSeek pricing (USD per 1M tokens) — as of 2026
PRICING = {
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
}


class DeepSeekClient:
    """Client for interacting with DeepSeek API with cost tracking"""
    
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        if OpenAI is None:
            logger.error("openai package not installed. Please run: pip install openai")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            
        self.model = model
        
        # Cost tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_calls = 0
        self.total_cost_usd = 0.0
    
    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Get chat completion from DeepSeek with cost tracking"""
        if self.client is None:
            return "Error: LLM client not initialized (missing openai package)"
            
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
            
            # Track token usage
            if response.usage:
                prompt_tokens = response.usage.prompt_tokens or 0
                completion_tokens = response.usage.completion_tokens or 0
                
                self.total_prompt_tokens += prompt_tokens
                self.total_completion_tokens += completion_tokens
                self.total_calls += 1
                
                # Calculate cost
                pricing = PRICING.get(self.model, PRICING["deepseek-chat"])
                call_cost = (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1_000_000
                self.total_cost_usd += call_cost
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek API Error: {e}")
            return f"Error communicating with AI: {str(e)}"

    async def chat_completion_async(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Async version of chat completion"""
        return self.chat_completion(messages, temperature)
    
    def get_usage_report(self) -> Dict[str, Any]:
        """Get usage and cost report"""
        return {
            "total_calls": self.total_calls,
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "avg_cost_per_call": round(self.total_cost_usd / max(self.total_calls, 1), 6),
            "model": self.model
        }
    
    def get_cost_summary(self) -> str:
        """Get formatted cost summary string"""
        r = self.get_usage_report()
        return (
            f"💰 API Cost: ${r['total_cost_usd']:.4f} | "
            f"Calls: {r['total_calls']} | "
            f"Tokens: {r['total_tokens']:,} "
            f"(in:{r['prompt_tokens']:,} out:{r['completion_tokens']:,})"
        )

