import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, Union
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedRiskManager:
    """Advanced risk management with ATR-based dynamic position sizing"""
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 risk_per_trade: float = 0.02,  # 2% risk per trade
                 max_portfolio_risk: float = 0.20,  # 20% max portfolio risk
                 sharpe_target: float = 1.5,
                 max_drawdown_limit: float = 0.15):
        
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.max_portfolio_risk = max_portfolio_risk
        self.sharpe_target = sharpe_target
        self.max_drawdown_limit = max_drawdown_limit
        
        # Performance tracking
        self.portfolio_history = []
        self.trade_history = []
        self.position_sizes = {}
        
    def calculate_atr_position_size(self,
                                   entry_price: float,
                                   stop_loss: float,
                                   atr: float,
                                   volatility_adjustment: bool = True) -> Tuple[int, float]:
        """
        Calculate position size using ATR-based volatility adjustment
        
        Formula: Position Size = (Risk Capital × Risk %) ÷ (ATR × Multiplier)
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            atr: Average True Range (volatility measure)
            volatility_adjustment: Whether to adjust for volatility
            
        Returns:
            Tuple of (position_size_in_units, risk_amount)
        """
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share <= 0 or atr <= 0:
            logger.warning(f"Invalid risk parameters: risk_per_share={risk_per_share}, ATR={atr}")
            return 0, 0
            
        # Calculate risk capital based on current equity
        risk_capital = self.current_capital * self.risk_per_trade
        
        # Base position size calculation
        base_position_size = risk_capital / risk_per_share
        
        # Apply ATR-based volatility adjustment
        if volatility_adjustment and atr > 0:
            # Normalize ATR to percentage of price
            atr_pct = atr / entry_price
            
            # Volatility scaling factor (inverse relationship)
            # Higher volatility → smaller position size
            volatility_factor = 1.0 / (1.0 + atr_pct * 3)  # Damping factor
            
            # Adjust position size
            adjusted_position_size = base_position_size * volatility_factor
        else:
            adjusted_position_size = base_position_size
            
        # Calculate Kelly criterion adjustment
        kelly_fraction = self.calculate_kelly_adjustment()
        final_position_size = adjusted_position_size * kelly_fraction
        
        # Round down to whole units
        position_units = int(final_position_size)
        
        # Calculate actual risk amount
        actual_risk = position_units * risk_per_share
        
        # Limit to max portfolio risk
        if actual_risk / self.current_capital > self.max_portfolio_risk:
            position_units = int((self.current_capital * self.max_portfolio_risk) / risk_per_share)
            actual_risk = position_units * risk_per_share
            
        logger.info(f"Position sizing: Entry=${entry_price:.4f}, Stop=${stop_loss:.4f}, "
                   f"ATR=${atr:.4f}, Units={position_units:,}, Risk=${actual_risk:,.2f}")
        
        return position_units, actual_risk
    
    def calculate_kelly_adjustment(self, win_rate: float = 0.45, avg_win_loss_ratio: float = 1.5) -> float:
        """
        Calculate fractional Kelly criterion for position sizing
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win_loss_ratio: Average win/loss ratio
            
        Returns:
            Fractional Kelly multiplier (0-1)
        """
        
        # Kelly criterion formula: f* = (p × b - q) / b
        # Where: p = win rate, q = loss rate (1-p), b = win/loss ratio
        
        if win_rate <= 0 or avg_win_loss_ratio <= 0:
            return 0.25  # Conservative default
            
        p = win_rate
        q = 1 - p
        b = avg_win_loss_ratio
        
        # Full Kelly
        kelly_full = (p * b - q) / b
        
        # Apply fractional Kelly (25% for risk management)
        kelly_fraction = max(0.1, min(0.5, kelly_full * 0.25))
        
        return kelly_fraction
    
    def calculate_stop_loss_atr(self, 
                               entry_price: float, 
                               atr: float, 
                               multiplier: float = 2.0,
                               is_long: bool = True) -> float:
        """
        Calculate ATR-based stop loss
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            multiplier: ATR multiplier for stop distance
            is_long: True for long position, False for short
            
        Returns:
            Stop loss price
        """
        
        if atr <= 0:
            # Fallback to percentage stop if ATR unavailable
            stop_pct = 0.02  # 2% stop
            if is_long:
                return entry_price * (1 - stop_pct)
            else:
                return entry_price * (1 + stop_pct)
                
        stop_distance = atr * multiplier
        
        if is_long:
            stop_loss = entry_price - stop_distance
            # Ensure stop is reasonable (not below certain threshold)
            min_stop = entry_price * 0.95  # Max 5% stop
            stop_loss = max(stop_loss, min_stop)
        else:
            stop_loss = entry_price + stop_distance
            max_stop = entry_price * 1.05  # Max 5% stop
            stop_loss = min(stop_loss, max_stop)
            
        return stop_loss
    
    def calculate_take_profit_atr(self,
                                 entry_price: float,
                                 stop_loss: float,
                                 atr: float,
                                 risk_reward_ratio: float = 2.0) -> float:
        """
        Calculate take profit based on ATR and risk-reward ratio
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            atr: Average True Range
            risk_reward_ratio: Desired R:R ratio
            
        Returns:
            Take profit price
        """
        
        risk_amount = abs(entry_price - stop_loss)
        reward_amount = risk_amount * risk_reward_ratio
        
        # Check if long or short
        if entry_price > stop_loss:  # Long position
            take_profit = entry_price + reward_amount
            # Add ATR-based buffer
            take_profit = take_profit + (atr * 0.5)
        else:  # Short position
            take_profit = entry_price - reward_amount
            # Add ATR-based buffer
            take_profit = take_profit - (atr * 0.5)
            
        return take_profit
    
    def update_portfolio_value(self, new_value: float, trade_pnl: float = 0):
        """
        Update current portfolio value and track performance
        
        Args:
            new_value: New portfolio value
            trade_pnl: P&L from recent trade
        """
        
        self.current_capital = new_value
        
        # Record portfolio snapshot
        snapshot = {
            'timestamp': pd.Timestamp.now(),
            'portfolio_value': new_value,
            'trade_pnl': trade_pnl,
            'return_pct': (new_value / self.initial_capital - 1) * 100
        }
        self.portfolio_history.append(snapshot)
        
        # Check drawdown limits
        self.check_risk_limits()
    
    def check_risk_limits(self) -> Dict[str, bool]:
        """
        Check if portfolio exceeds risk limits
        
        Returns:
            Dictionary of risk limit breaches
        """
        
        if not self.portfolio_history:
            return {}
            
        portfolio_values = [h['portfolio_value'] for h in self.portfolio_history]
        
        # Calculate drawdown
        peak = max(portfolio_values)
        current = portfolio_values[-1]
        drawdown = (peak - current) / peak if peak > 0 else 0
        
        # Calculate daily returns for Sharpe
        returns = []
        for i in range(1, len(portfolio_values)):
            daily_return = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]
            returns.append(daily_return)
        
        sharpe_ratio = 0
        if returns and np.std(returns) > 0:
            sharpe_ratio = (np.mean(returns) * 252) / (np.std(returns) * np.sqrt(252))
        
        # Check limits
        limits_breached = {
            'max_drawdown': drawdown > self.max_drawdown_limit,
            'sharpe_below_target': sharpe_ratio < self.sharpe_target,
            'capital_halved': current < (self.initial_capital * 0.5)
        }
        
        if any(limits_breached.values()):
            logger.warning(f"Risk limits breached: {limits_breached}")
            logger.warning(f"Drawdown: {drawdown:.2%}, Sharpe: {sharpe_ratio:.2f}")
            
        return limits_breached
    
    def calculate_var(self, confidence_level: float = 0.95, lookback_days: int = 252) -> float:
        """
        Calculate Value at Risk (VaR) using historical method
        
        Args:
            confidence_level: Confidence level (0.95 for 95%)
            lookback_days: Lookback period in trading days
            
        Returns:
            VaR as percentage of portfolio
        """
        
        if len(self.portfolio_history) < 2:
            return 0.05  # Default 5% VaR
            
        # Calculate daily returns
        returns = []
        portfolio_values = [h['portfolio_value'] for h in self.portfolio_history[-lookback_days:]]
        
        for i in range(1, len(portfolio_values)):
            daily_return = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]
            returns.append(daily_return)
        
        if not returns:
            return 0.05
            
        # Historical VaR
        var = np.percentile(returns, (1 - confidence_level) * 100)
        
        return abs(var)  # Return positive value
    
    def generate_risk_report(self) -> Dict:
        """
        Generate comprehensive risk report
        
        Returns:
            Dictionary with all risk metrics
        """
        
        if not self.portfolio_history:
            return {}
            
        portfolio_values = [h['portfolio_value'] for h in self.portfolio_history]
        trade_pnls = [h['trade_pnl'] for h in self.portfolio_history if h['trade_pnl'] != 0]
        
        # Basic metrics
        total_return = (portfolio_values[-1] / portfolio_values[0] - 1) * 100
        peak = max(portfolio_values)
        current = portfolio_values[-1]
        max_drawdown = (peak - min(portfolio_values)) / peak if peak > 0 else 0
        current_drawdown = (peak - current) / peak if peak > 0 else 0
        
        # Calculate returns for risk metrics
        returns = []
        for i in range(1, len(portfolio_values)):
            daily_return = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]
            returns.append(daily_return)
        
        # Risk metrics
        sharpe_ratio = 0
        sortino_ratio = 0
        if returns:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            
            # Sharpe Ratio (annualized)
            if std_return > 0:
                sharpe_ratio = (avg_return * 252) / (std_return * np.sqrt(252))
            
            # Sortino Ratio (downside deviation only)
            negative_returns = [r for r in returns if r < 0]
            if negative_returns:
                downside_std = np.std(negative_returns)
                if downside_std > 0:
                    sortino_ratio = (avg_return * 252) / (downside_std * np.sqrt(252))
        
        # Trade metrics
        win_rate = 0
        profit_factor = 0
        avg_rr_ratio = 0
        
        if trade_pnls:
            winning_trades = [p for p in trade_pnls if p > 0]
            losing_trades = [p for p in trade_pnls if p < 0]
            
            win_rate = len(winning_trades) / len(trade_pnls) if trade_pnls else 0
            
            total_profit = sum(winning_trades)
            total_loss = abs(sum(losing_trades))
            profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            
            # Average R:R ratio (simplified)
            if winning_trades and losing_trades:
                avg_win = np.mean(winning_trades)
                avg_loss = abs(np.mean(losing_trades))
                avg_rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # VaR calculation
        var_95 = self.calculate_var(confidence_level=0.95)
        var_99 = self.calculate_var(confidence_level=0.99)
        
        # Calmar Ratio
        calmar_ratio = (total_return / 100) / max_drawdown if max_drawdown > 0 else 0
        
        report = {
            'portfolio_value': current,
            'total_return_pct': total_return,
            'max_drawdown_pct': max_drawdown * 100,
            'current_drawdown_pct': current_drawdown * 100,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'var_95_pct': var_95 * 100,
            'var_99_pct': var_99 * 100,
            'win_rate_pct': win_rate * 100,
            'profit_factor': profit_factor,
            'avg_rr_ratio': avg_rr_ratio,
            'total_trades': len(trade_pnls),
            'winning_trades': len(winning_trades) if 'winning_trades' in locals() else 0,
            'losing_trades': len(losing_trades) if 'losing_trades' in locals() else 0,
            'risk_per_trade_pct': self.risk_per_trade * 100,
            'kelly_adjustment': self.calculate_kelly_adjustment(win_rate, avg_rr_ratio)
        }
        
        return report