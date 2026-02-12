"""
DeepSeek LLM Client
Wrapper for OpenAI-compatible DeepSeek API with cost tracking,
multi-model routing, and rate limit protection.
"""

import os
import time
import logging
import threading
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

# Feature 12: Keywords that trigger the stronger model
COMPLEX_KEYWORDS = [
    "backtest", "optimize", "risk analysis", "strategy design",
    "portfolio", "walk-forward", "monte carlo", "regression",
    "architecture", "refactor", "security review", "debug complex"
]


class RateLimiter:
    """Feature 20: Token bucket rate limiter"""
    
    def __init__(self, max_calls_per_minute: int = 60, max_tokens_per_minute: int = 500000):
        self.max_calls = max_calls_per_minute
        self.max_tokens = max_tokens_per_minute
        self.calls = []  # timestamps of recent calls
        self.tokens_used = []  # (timestamp, tokens) pairs
        self.lock = threading.Lock()
        self.total_waits = 0
        self.total_wait_seconds = 0.0
    
    def wait_if_needed(self, estimated_tokens: int = 1000):
        """Block until rate limit allows the call"""
        with self.lock:
            now = time.time()
            window = 60.0  # 1 minute window
            
            # Clean old entries
            self.calls = [t for t in self.calls if now - t < window]
            self.tokens_used = [(t, tk) for t, tk in self.tokens_used if now - t < window]
            
            # Check call limit
            if len(self.calls) >= self.max_calls:
                wait_time = self.calls[0] + window - now + 0.1
                if wait_time > 0:
                    logger.warning(f"⏳ Rate limit: {len(self.calls)} calls/min. Waiting {wait_time:.1f}s...")
                    self.total_waits += 1
                    self.total_wait_seconds += wait_time
                    time.sleep(wait_time)
            
            # Check token limit
            current_tokens = sum(tk for _, tk in self.tokens_used)
            if current_tokens + estimated_tokens > self.max_tokens:
                wait_time = self.tokens_used[0][0] + window - now + 0.1 if self.tokens_used else 1
                if wait_time > 0:
                    logger.warning(f"⏳ Token limit: {current_tokens:,} tokens/min. Waiting {wait_time:.1f}s...")
                    self.total_waits += 1
                    self.total_wait_seconds += wait_time
                    time.sleep(wait_time)
            
            self.calls.append(time.time())
    
    def record_tokens(self, tokens: int):
        """Record actual tokens used"""
        with self.lock:
            self.tokens_used.append((time.time(), tokens))
    
    def get_stats(self) -> Dict:
        return {
            "total_waits": self.total_waits,
            "total_wait_seconds": round(self.total_wait_seconds, 1)
        }


class DeepSeekClient:
    """Client for interacting with DeepSeek API with cost tracking, multi-model routing, and rate limiting"""
    
    def __init__(self, api_key: str, model: str = "deepseek-chat",
                 enable_auto_routing: bool = True,
                 rate_limit_calls: int = 60,
                 rate_limit_tokens: int = 500000):
        if OpenAI is None:
            logger.error("openai package not installed. Please run: pip install openai")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com",
                timeout=120.0  # 120s timeout to prevent indefinite hangs
            )
            
        self.model = model
        self.enable_auto_routing = enable_auto_routing  # Feature 12
        
        # Cost tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_calls = 0
        self.total_cost_usd = 0.0
        self.calls_per_model = {}  # Feature 12: track per-model usage
        
        # Feature 20: Rate limiter
        self.rate_limiter = RateLimiter(rate_limit_calls, rate_limit_tokens)
    
    def _select_model(self, messages: List[Dict[str, str]]) -> str:
        """Feature 12: Auto-select model based on task complexity"""
        if not self.enable_auto_routing:
            return self.model
        
        # Check message content for complex keywords
        full_text = " ".join(m.get("content", "") for m in messages).lower()
        
        for keyword in COMPLEX_KEYWORDS:
            if keyword in full_text:
                selected = "deepseek-reasoner"
                logger.debug(f"🧠 Auto-routing to {selected} (keyword: {keyword})")
                return selected
        
        return self.model  # Default to cheaper model
    
    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7,
                        model_override: str = None) -> str:
        """Get chat completion from DeepSeek with cost tracking, auto-routing, and rate limiting"""
        if self.client is None:
            return "Error: LLM client not initialized (missing openai package)"
            
        if not any(m['role'] == 'system' for m in messages):
            messages.insert(0, {"role": "system", "content": "You are a helpful AI assistant. Always respond in Vietnamese unless asked otherwise."})
        
        # Feature 12: Select model
        selected_model = model_override or self._select_model(messages)
        
        # Feature 20: Rate limiting
        self.rate_limiter.wait_if_needed()
        
        try:
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=temperature,
                max_tokens=4000,
                stream=False,
                timeout=60.0  # Per-request timeout
            )
            
            # Track token usage
            if response.usage:
                prompt_tokens = response.usage.prompt_tokens or 0
                completion_tokens = response.usage.completion_tokens or 0
                total_tokens = prompt_tokens + completion_tokens
                
                self.total_prompt_tokens += prompt_tokens
                self.total_completion_tokens += completion_tokens
                self.total_calls += 1
                
                # Feature 12: Per-model tracking
                self.calls_per_model[selected_model] = self.calls_per_model.get(selected_model, 0) + 1
                
                # Feature 20: Record actual tokens used
                self.rate_limiter.record_tokens(total_tokens)
                
                # Calculate cost
                pricing = PRICING.get(selected_model, PRICING["deepseek-chat"])
                call_cost = (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1_000_000
                self.total_cost_usd += call_cost
            
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e)
            if "rate_limit" in error_str.lower() or "429" in error_str:
                logger.warning("🚫 API rate limit hit! Waiting 10s...")
                time.sleep(10)
                return self.chat_completion(messages, temperature, model_override)
            logger.error(f"DeepSeek API Error: {e}")
            return f"Error communicating with AI: {error_str}"

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
            "model": self.model,
            "calls_per_model": self.calls_per_model,
            "rate_limiter": self.rate_limiter.get_stats()
        }
    
    def get_cost_summary(self) -> str:
        """Get formatted cost summary string"""
        r = self.get_usage_report()
        model_info = " | ".join(f"{m}:{c}" for m, c in self.calls_per_model.items()) if self.calls_per_model else self.model
        return (
            f"💰 API Cost: ${r['total_cost_usd']:.4f} | "
            f"Calls: {r['total_calls']} | "
            f"Tokens: {r['total_tokens']:,} "
            f"(in:{r['prompt_tokens']:,} out:{r['completion_tokens']:,}) | "
            f"Models: {model_info}"
        )
