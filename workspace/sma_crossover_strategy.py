import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

class SMACrossoverStrategy:
    """
    SMA Crossover Strategy with Risk Management
    - Fast SMA (10 periods) vs Slow SMA (30 periods)
    - Stop-loss, Take-profit, Position sizing
    - Risk per trade: 1-2% of capital
    """
    
    def __init__(self, initial_capital=10000, fast_period=10, slow_period=30, 
                 risk_per_trade=0.01, stop_loss_pct=0.02, take_profit_pct=0.04):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.risk_per_trade = risk_per_trade
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.position = 0
        self.entry_price = 0
        self.trades = []
        self.equity_curve = []
        
    def calculate_signals(self, data):
        """Calculate SMA crossover signals"""
        data = data.copy()
        data['fast_sma'] = data['Close'].rolling(window=self.fast_period).mean()
        data['slow_sma'] = data['Close'].rolling(window=self.slow_period).mean()
        
        # Generate signals
        data['signal'] = 0
        data.loc[data['fast_sma'] > data['slow_sma'], 'signal'] = 1  # Buy signal
        data.loc[data['fast_sma'] < data['slow_sma'], 'signal'] = -1  # Sell signal
        
        # Signal changes only
        data['position'] = data['signal'].diff()
        
        return data
    
    def calculate_position_size(self, current_price):
        """Calculate position size using Kelly criterion and risk management"""
        risk_amount = self.capital * self.risk_per_trade
        position_size = risk_amount / (current_price * self.stop_loss_pct)
        return int(position_size)  # Integer shares
    
    def execute_trade(self, signal_type, price, timestamp):
        """Execute a trade with risk management"""
        if signal_type == 'BUY' and self.position == 0:
            # Calculate position size
            shares = self.calculate_position_size(price)
            if shares > 0:
                cost = shares * price
                if cost <= self.capital:
                    self.position = shares
                    self.entry_price = price
                    self.capital -= cost
                    
                    # Set stop loss and take profit
                    stop_loss = price * (1 - self.stop_loss_pct)
                    take_profit = price * (1 + self.take_profit_pct)
                    
                    trade = {
                        'timestamp': timestamp,
                        'type': 'BUY',
                        'shares': shares,
                        'price': price,
                        'cost': cost,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'status': 'OPEN'
                    }
                    self.trades.append(trade)
                    print(f"[{timestamp}] BUY {shares} shares @ ${price:.4f}")
                    
        elif signal_type == 'SELL' and self.position > 0:
            # Close position
            proceeds = self.position * price
            self.capital += proceeds
            profit = (price - self.entry_price) * self.position
            
            # Update trade record
            for trade in self.trades:
                if trade['status'] == 'OPEN':
                    trade['exit_price'] = price
                    trade['exit_time'] = timestamp
                    trade['profit'] = profit
                    trade['return_pct'] = (price / trade['price'] - 1) * 100
                    trade['status'] = 'CLOSED'
                    break
            
            print(f"[{timestamp}] SELL {self.position} shares @ ${price:.4f}, Profit: ${profit:.2f}")
            self.position = 0
            self.entry_price = 0
    
    def check_exit_conditions(self, current_price, timestamp):
        """Check stop-loss and take-profit conditions"""
        if self.position > 0:
            current_pnl_pct = (current_price / self.entry_price - 1) * 100
            
            # Check stop loss
            if current_pnl_pct <= -self.stop_loss_pct * 100:
                self.execute_trade('SELL', current_price, timestamp)
                return 'STOP_LOSS'
            
            # Check take profit
            if current_pnl_pct >= self.take_profit_pct * 100:
                self.execute_trade('SELL', current_price, timestamp)
                return 'TAKE_PROFIT'
        
        return None
    
    def update_equity(self, current_price):
        """Update equity curve"""
        current_equity = self.capital + (self.position * current_price)
        self.equity_curve.append(current_equity)
        return current_equity
    
    def calculate_metrics(self):
        """Calculate performance metrics"""
        if len(self.trades) == 0:
            return {}
        
        closed_trades = [t for t in self.trades if t['status'] == 'CLOSED']
        
        if len(closed_trades) == 0:
            return {}
        
        profits = [t['profit'] for t in closed_trades]
        returns = [t['return_pct'] for t in closed_trades]
        
        total_profit = sum(profits)
        total_return_pct = (total_profit / self.initial_capital) * 100
        
        # Win rate
        winning_trades = sum(1 for p in profits if p > 0)
        win_rate = (winning_trades / len(profits)) * 100
        
        # Profit factor
        gross_profit = sum(p for p in profits if p > 0)
        gross_loss = abs(sum(p for p in profits if p < 0))
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        
        # Sharpe ratio (simplified)
        avg_return = np.mean(returns)
        std_return = np.std(returns) if len(returns) > 1 else 0
        sharpe_ratio = avg_return / std_return if std_return != 0 else 0
        
        # Max drawdown
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdowns = (equity_array - running_max) / running_max * 100
        max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
        
        metrics = {
            'total_trades': len(closed_trades),
            'total_profit': total_profit,
            'total_return_pct': total_return_pct,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_return_pct': np.mean(returns),
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown,
            'final_equity': self.equity_curve[-1] if self.equity_curve else self.initial_capital
        }
        
        return metrics
    
    def get_trade_summary(self):
        """Get detailed trade summary"""
        return pd.DataFrame(self.trades)