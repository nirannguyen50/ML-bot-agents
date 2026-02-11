"""
Paper Trading Simulator — Feature 15
Simulated live trading with real-time price feeds.
Tracks virtual P&L without real money.
"""

import os
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
except ImportError:
    yf = None


class PaperTrader:
    """Virtual paper trading engine with real-time price feeds"""
    
    def __init__(self, initial_capital: float = 10000.0, 
                 state_file: str = "paper_trading.json"):
        self.initial_capital = initial_capital
        self.state_file = state_file
        self.lock = threading.Lock()
        
        # Load or initialize state
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return self._initial_state()
    
    def _initial_state(self) -> Dict:
        return {
            "capital": self.initial_capital,
            "positions": {},       # {symbol: {qty, entry_price, entry_time}}
            "closed_trades": [],   # [{symbol, entry, exit, pnl, ...}]
            "equity_curve": [],    # [{time, equity}]
            "total_pnl": 0.0,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "created": datetime.now().isoformat()
        }
    
    def _save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price via yfinance"""
        if not yf:
            return None
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
        except:
            pass
        return None
    
    def open_position(self, symbol: str, qty: float, price: float = None,
                      stop_loss: float = None, take_profit: float = None) -> Dict:
        """Open a new paper trade"""
        with self.lock:
            if symbol in self.state["positions"]:
                return {"error": f"Already have position in {symbol}"}
            
            if price is None:
                price = self.get_price(symbol)
                if price is None:
                    return {"error": f"Cannot get price for {symbol}"}
            
            cost = price * qty
            if cost > self.state["capital"]:
                return {"error": f"Insufficient capital: need ${cost:.2f}, have ${self.state['capital']:.2f}"}
            
            self.state["capital"] -= cost
            self.state["positions"][symbol] = {
                "qty": qty,
                "entry_price": price,
                "entry_time": datetime.now().isoformat(),
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "cost": cost
            }
            
            self._save_state()
            logger.info(f"📈 PAPER BUY: {qty} {symbol} @ {price:.4f} (cost: ${cost:.2f})")
            return {"ok": True, "symbol": symbol, "qty": qty, "price": price}
    
    def close_position(self, symbol: str, price: float = None) -> Dict:
        """Close a paper trade"""
        with self.lock:
            if symbol not in self.state["positions"]:
                return {"error": f"No position in {symbol}"}
            
            pos = self.state["positions"][symbol]
            
            if price is None:
                price = self.get_price(symbol)
                if price is None:
                    return {"error": f"Cannot get price for {symbol}"}
            
            pnl = (price - pos["entry_price"]) * pos["qty"]
            pnl_pct = (price / pos["entry_price"] - 1) * 100
            
            self.state["capital"] += price * pos["qty"]
            self.state["total_pnl"] += pnl
            self.state["total_trades"] += 1
            
            if pnl > 0:
                self.state["wins"] += 1
            else:
                self.state["losses"] += 1
            
            trade = {
                "symbol": symbol,
                "entry_price": pos["entry_price"],
                "exit_price": price,
                "qty": pos["qty"],
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "entry_time": pos["entry_time"],
                "exit_time": datetime.now().isoformat()
            }
            self.state["closed_trades"].append(trade)
            del self.state["positions"][symbol]
            
            self._save_state()
            emoji = "✅" if pnl > 0 else "❌"
            logger.info(f"{emoji} PAPER SELL: {symbol} @ {price:.4f} | PnL: ${pnl:.2f} ({pnl_pct:.1f}%)")
            return {"ok": True, **trade}
    
    def check_stops(self) -> List[Dict]:
        """Check stop-loss and take-profit levels"""
        triggered = []
        for symbol, pos in list(self.state["positions"].items()):
            price = self.get_price(symbol)
            if price is None:
                continue
            
            if pos.get("stop_loss") and price <= pos["stop_loss"]:
                result = self.close_position(symbol, price)
                result["trigger"] = "stop_loss"
                triggered.append(result)
            elif pos.get("take_profit") and price >= pos["take_profit"]:
                result = self.close_position(symbol, price)
                result["trigger"] = "take_profit"
                triggered.append(result)
        
        return triggered
    
    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio summary"""
        total_equity = self.state["capital"]
        positions_value = 0
        
        for symbol, pos in self.state["positions"].items():
            price = self.get_price(symbol) or pos["entry_price"]
            positions_value += price * pos["qty"]
        
        total_equity += positions_value
        total_return = (total_equity / self.initial_capital - 1) * 100
        win_rate = self.state["wins"] / max(self.state["total_trades"], 1) * 100
        
        return {
            "total_equity": round(total_equity, 2),
            "cash": round(self.state["capital"], 2),
            "positions_value": round(positions_value, 2),
            "open_positions": len(self.state["positions"]),
            "total_pnl": round(self.state["total_pnl"], 2),
            "total_return_pct": round(total_return, 2),
            "total_trades": self.state["total_trades"],
            "win_rate": round(win_rate, 1),
            "wins": self.state["wins"],
            "losses": self.state["losses"]
        }
    
    def get_summary_text(self) -> str:
        s = self.get_portfolio_summary()
        return (
            f"📊 Paper Trading Portfolio:\n"
            f"  💰 Equity: ${s['total_equity']:,.2f}\n"
            f"  📈 Return: {s['total_return_pct']:+.1f}%\n"
            f"  🎯 Win Rate: {s['win_rate']:.0f}% ({s['wins']}W/{s['losses']}L)\n"
            f"  📋 Trades: {s['total_trades']} | Open: {s['open_positions']}"
        )
