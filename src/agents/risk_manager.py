"""
Risk Manager Agent — Feature 14
5th agent specialized in risk management:
position sizing, max drawdown limits, correlation analysis, portfolio risk.
"""

import logging
from typing import Dict, Any
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class RiskManagerAgent(BaseAgent):
    """Risk Manager — guards the trading system against excessive risk"""
    
    def __init__(self, config: Dict[str, Any], api_key: str = None):
        super().__init__(config, "risk_manager", api_key)
        
        self.role_instruction = """You are the RISK MANAGER of a professional trading operation.
Your responsibilities:
1. Position Sizing: Calculate optimal position sizes based on Kelly criterion or fixed fractional
2. Drawdown Limits: Monitor and enforce maximum drawdown thresholds (e.g., 15% max)
3. Correlation Analysis: Identify correlated positions that amplify risk
4. Portfolio Risk: Calculate portfolio-level VaR, expected shortfall
5. Risk Alerts: Issue warnings when risk parameters are breached

Risk Rules:
- Max position size: 5% of capital per trade
- Max portfolio drawdown: 15%
- Max correlated exposure: 30% in same sector
- Stop-loss: Always required, max 2% of capital

When reviewing strategies, ALWAYS check:
- Does it have a stop-loss?
- What is the worst-case scenario?
- How does it behave in crashes?

Reply in Vietnamese."""

        # Default risk parameters
        self.risk_params = {
            "max_position_pct": 5.0,        # Max 5% of capital per trade
            "max_drawdown_pct": 15.0,        # Max 15% portfolio drawdown
            "max_correlation": 0.7,           # Max correlation between positions
            "required_sharpe": 0.5,           # Min Sharpe ratio for strategies
            "max_loss_per_trade_pct": 2.0,    # Max 2% loss per trade
        }
    
    async def initialize(self) -> bool:
        """Initialize risk manager with current system state"""
        self.logger.info(f"{self.name}: Initializing Risk Manager agent...")
        
        if self.llm:
            init_thought = await self.think(
                "You are initializing as the Risk Manager. Review current risk parameters and prepare for monitoring.",
                f"Risk Parameters: {self.risk_params}\n"
                f"Set up risk monitoring for the trading system."
            )
            self.logger.info(f"{self.name}: Risk Assessment: {init_thought[:200]}...")
        
        if self.memory:
            self.memory.remember_fact("risk_params", str(self.risk_params))
        
        self.is_initialized = True
        self.logger.info(f"{self.name}: Risk Manager agent initialized successfully")
        return True
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a risk management task"""
        try:
            task_type = self._classify_risk_task(task.get("title", ""))
            
            if task_type == "review":
                return await self._review_strategy_risk(task)
            elif task_type == "sizing":
                return await self._calculate_position_size(task)
            elif task_type == "monitor":
                return await self._monitor_risk(task)
            else:
                # General risk task
                result = await self.execute_with_retry(task["description"], max_rounds=3)
                return result
                
        except Exception as e:
            self.logger.error(f"Risk task error: {e}")
            return {"status": "error", "error": str(e)}
    
    def _classify_risk_task(self, title: str) -> str:
        title_lower = title.lower()
        if any(w in title_lower for w in ["review", "assess", "evaluate"]):
            return "review"
        elif any(w in title_lower for w in ["size", "position", "allocat"]):
            return "sizing"
        elif any(w in title_lower for w in ["monitor", "check", "alert"]):
            return "monitor"
        return "general"
    
    async def _review_strategy_risk(self, task: Dict) -> Dict:
        """Review a strategy for risk compliance"""
        result = await self.execute_with_retry(
            f"""Review this strategy for risk compliance:
{task['description']}

Check against these risk parameters:
{self.risk_params}

Evaluate: stop-loss, drawdown, position sizing, worst-case scenario.
Write a risk report to workspace/risk_report.py""",
            max_rounds=3
        )
        
        # Share risk assessment via shared memory
        if self.shared_memory and result.get("status") == "success":
            self.shared_memory.add_warning(
                self.name,
                f"Risk review for '{task['title']}': {result.get('output', '')[:200]}"
            )
        
        return result
    
    async def _calculate_position_size(self, task: Dict) -> Dict:
        return await self.execute_with_retry(
            f"""Calculate optimal position sizes:
{task['description']}

Use Kelly criterion or fixed fractional:
- Capital: (specify from task)
- Max risk per trade: {self.risk_params['max_loss_per_trade_pct']}%
- Max position: {self.risk_params['max_position_pct']}%

Write calculation to workspace/position_sizing.py""",
            max_rounds=3
        )
    
    async def _monitor_risk(self, task: Dict) -> Dict:
        return await self.execute_with_retry(
            f"""Monitor current risk levels:
{task['description']}

Check:
1. Current drawdown vs max allowed ({self.risk_params['max_drawdown_pct']}%)
2. Position concentration
3. Correlation between active strategies
4. Stop-loss placement

Write monitor script to workspace/risk_monitor.py""",
            max_rounds=3
        )
