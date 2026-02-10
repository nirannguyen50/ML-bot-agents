"""
Data Scientist Agent
Responsible for data pipeline, feature engineering, and model training
"""

import asyncio
from typing import Dict, Any, List
import logging
from datetime import datetime
import os
import pandas as pd
try:
    import yfinance as yf
except ImportError:
    yf = None

from .base_agent import BaseAgent


class DataScientist(BaseAgent):
    """Data Scientist Agent for ML Trading Bot"""
    
    def __init__(self, config: Dict[str, Any], api_key: str = None):
        super().__init__(config, "data_scientist", api_key)
        
        self.role_instruction = """
You are the Data Scientist of the ML Trading Bot team. Your expertise covers:

1. DATA PIPELINE:
   - Collect market data (OHLCV, orderbook, sentiment) from Yahoo Finance, Binance, etc.
   - Clean & validate data: handle missing values, outliers, corporate actions
   - Store data in structured formats (CSV, Parquet, database)

2. FEATURE ENGINEERING:
   - Technical indicators: SMA, EMA, RSI, MACD, Bollinger Bands, ATR
   - Statistical features: returns, volatility, skewness, kurtosis
   - Market microstructure: spread, volume profile, VWAP
   - Lag features, rolling windows, cross-asset correlations

3. ML MODEL LIFECYCLE:
   - Train models: LSTM, XGBoost, RandomForest, Reinforcement Learning
   - Evaluate: accuracy, precision, recall, F1, Sharpe of predictions
   - Prevent overfitting: cross-validation, walk-forward analysis
   - Model versioning & experiment tracking

4. DATA QUALITY:
   - Monitor data freshness & completeness
   - Detect anomalies & distribution shifts
   - Report data health metrics to the team

COMMUNICATION: When reporting results, always include specific numbers (accuracy %, row counts, date ranges).
Always collaborate with Quant Analyst for feature validation and Engineer for data pipeline integration.
"""
        
        self.status['performance'] = {
            'models_trained': 0,
            'features_engineered': 0,
            'data_processed_gb': 0
        }
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw')
        os.makedirs(self.data_dir, exist_ok=True)
    
    async def initialize(self) -> bool:
        """Initialize Data Scientist agent"""
        try:
            await self.log_activity("Initializing Data Scientist agent...")
            
            # Use LLM to plan initialization
            plan = await self.think("System startup", "Check data pipelines and prepare for model training.")
            await self.log_activity(f"Initialization Plan: {plan}")
            
            self.is_initialized = True
            self.status['state'] = 'ready'
            await self.log_activity("Data Scientist agent initialized successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False
            
    async def download_market_data(self, symbol: str, period: str = "1mo", interval: str = "1d") -> str:
        """
        Download market data from Yahoo Finance
        """
        if yf is None:
            return "Error: yfinance library not installed."
            
        try:
            await self.log_activity(f"Starting download for {symbol} ({period})...")
            
            # Run blocking call in executor
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: yf.download(symbol, period=period, interval=interval, progress=False))
            
            if df.empty:
                return f"No data found for {symbol}."
            
            # Save to CSV
            filename = f"{symbol}_{datetime.now().strftime('%Y%m%d')}.csv"
            filepath = os.path.join(self.data_dir, filename)
            df.to_csv(filepath)
            
            msg = f"Successfully downloaded {len(df)} rows for {symbol}. Saved to {filename}."
            await self.log_activity(msg)
            return msg
            
        except Exception as e:
            error_msg = f"Failed to download data for {symbol}: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data science task"""
        task_type = task.get('type', 'unknown')
        
        try:
            await self.log_activity(f"Executing task: {task_type}")
            
            if task_type == 'download_data':
                symbol = task.get('symbol', 'EURUSD=X')
                period = task.get('period', '1mo')
                result_str = await self.download_market_data(symbol, period)
            else:
                # Use LLM to execute generic task with potential tool use
                initial_thought = await self.think(f"Task: {task_type}", f"Params: {task}")
                
                # Check for actions
                tool_result = await self.act(initial_thought)
                
                if tool_result:
                    # If action taken, think again with result
                    final_response = await self.think(f"I performed actions.", f"Tool Output: {tool_result}. Now summarize what I did.")
                    result_str = f"{initial_thought}\n\n--> ACTION OUTPUT:\n{tool_result}\n\n--> FINAL:\n{final_response}"
                else:
                    result_str = initial_thought
                    
                # Special handling for memory test to ensure double-check
                if task_type == 'memory_test' and 'LEARN' in tool_result:
                     recall_check = await self.act(f"[JSON_CMD: {{'tool': 'RECALL', 'args': {{'key': 'project_start_date'}}}}]") # Basic check
            
            await self.log_activity(f"Task {task_type} completed.")
            return {'status': 'success', 'output': result_str}
            
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            return {'error': str(e)}

