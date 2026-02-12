import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, List, Optional, Tuple

# Thêm đường dẫn để import backtest engine
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

st.set_page_config(
    page_title="ML Trading Bot Backtest Dashboard",
    page_icon="📈",
    layout="wide"
)

# Title and description
st.title("📊 ML Trading Bot - Backtest Dashboard")
st.markdown("""
Interactive dashboard for testing trading strategies with various parameters.
Compare performance metrics and visualize results.
""")

# Sidebar configuration
st.sidebar.header("⚙️ Backtest Configuration")

# Strategy selection
strategy_options = {
    "SMA Crossover": "sma_crossover",
    "Mean Reversion": "mean_reversion", 
    "ML Signal": "ml_signal"
}

selected_strategy = st.sidebar.selectbox(
    "Trading Strategy",
    list(strategy_options.keys())
)

# Date range
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("Start Date", datetime.now() - timedelta(days=365))
with col2:
    end_date = st.date_input("End Date", datetime.now())

# Strategy parameters
st.sidebar.subheader("Strategy Parameters")

if selected_strategy == "SMA Crossover":
    fast_window = st.sidebar.slider("Fast SMA Window", 5, 50, 20)
    slow_window = st.sidebar.slider("Slow SMA Window", 20, 200, 50)
    params = {"fast_window": fast_window, "slow_window": slow_window}
    
elif selected_strategy == "Mean Reversion":
    lookback = st.sidebar.slider("Lookback Period", 10, 100, 20)
    std_dev = st.sidebar.slider("Standard Deviations", 1.0, 3.0, 2.0)
    params = {"lookback": lookback, "std_dev": std_dev}
    
else:  # ML Signal
    confidence_threshold = st.sidebar.slider("Confidence Threshold", 0.5, 0.95, 0.7)
    params = {"confidence_threshold": confidence_threshold}

# Risk management
st.sidebar.subheader("Risk Management")
initial_capital = st.sidebar.number_input("Initial Capital ($)", 10000, 1000000, 100000)
position_size = st.sidebar.slider("Position Size (%)", 1, 100, 10)
stop_loss = st.sidebar.slider("Stop Loss (%)", 1, 20, 5)

# Run backtest button
run_backtest = st.sidebar.button("🚀 Run Backtest", type="primary")

# Mock backtest engine (will integrate with actual engine)
class MockBacktestEngine:
    """Mock backtest engine for demonstration"""
    
    @staticmethod
    def run_backtest(strategy: str, params: Dict, 
                    start_date: datetime, end_date: datetime,
                    initial_capital: float) -> Dict:
        """Run backtest and return results"""
        
        # Generate mock data
        dates = pd.date_range(start_date, end_date, freq='D')
        n_days = len(dates)
        
        # Mock price data
        np.random.seed(42)
        base_price = 100
        returns = np.random.normal(0.0005, 0.02, n_days)
        prices = base_price * np.exp(np.cumsum(returns))
        
        # Generate mock signals based on strategy
        if strategy == "sma_crossover":
            fast_sma = pd.Series(prices).rolling(params["fast_window"]).mean()
            slow_sma = pd.Series(prices).rolling(params["slow_window"]).mean()
            signals = np.where(fast_sma > slow_sma, 1, -1)
        elif strategy == "mean_reversion":
            zscore = (prices - pd.Series(prices).rolling(params["lookback"]).mean()) / \
                     pd.Series(prices).rolling(params["lookback"]).std()
            signals = np.where(zscore < -params["std_dev"], 1, 
                             np.where(zscore > params["std_dev"], -1, 0))
        else:
            signals = np.random.choice([-1, 0, 1], size=n_days, p=[0.3, 0.4, 0.3])
        
        # Calculate equity curve
        position = np.zeros(n_days)
        equity = np.zeros(n_days)
        equity[0] = initial_capital
        
        for i in range(1, n_days):
            if signals[i] != 0:
                position_size_pct = position_size / 100
                position_value = equity[i-1] * position_size_pct * signals[i]
                position[i] = position_value / prices[i]
            else:
                position[i] = 0
            
            # Calculate equity with position
            equity[i] = equity[i-1] + position[i-1] * (prices[i] - prices[i-1])
        
        # Calculate metrics
        returns_series = pd.Series(equity).pct_change().dropna()
        sharpe_ratio = np.sqrt(252) * returns_series.mean() / returns_series.std() if returns_series.std() > 0 else 0
        
        # Max drawdown
        cumulative = pd.Series(equity)
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Total return
        total_return = (equity[-1] - initial_capital) / initial_capital
        
        return {
            "dates": dates,
            "prices": prices,
            "equity": equity,
            "signals": signals,
            "position": position,
            "metrics": {
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "total_return": total_return,
                "final_equity": equity[-1],
                "volatility": returns_series.std() * np.sqrt(252)
            },
            "parameters": params
        }

# Main content area
if run_backtest:
    with st.spinner("Running backtest..."):
        # Initialize engine
        engine = MockBacktestEngine()
        
        # Run backtest
        results = engine.run_backtest(
            strategy=strategy_options[selected_strategy],
            params=params,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital
        )
        
        # Store in session state for comparison
        if "backtest_results" not in st.session_state:
            st.session_state.backtest_results = []
        
        result_entry = {
            "strategy": selected_strategy,
            "params": params,
            "results": results,
            "timestamp": datetime.now()
        }
        st.session_state.backtest_results.append(result_entry)
        
        st.success(f"Backtest completed! Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
    
    # Display metrics
    st.header("📊 Performance Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Sharpe Ratio", f"{results['metrics']['sharpe_ratio']:.2f}")
    with col2:
        st.metric("Max Drawdown", f"{results['metrics']['max_drawdown']:.2%}")
    with col3:
        st.metric("Total Return", f"{results['metrics']['total_return']:.2%}")
    with col4:
        st.metric("Final Equity", f"${results['metrics']['final_equity']:,.0f}")
    
    # Visualization
    st.header("📈 Charts")
    
    # Create tabs for different visualizations
    tab1, tab2, tab3 = st.tabs(["Equity Curve", "Drawdown", "Price & Signals"])
    
    with tab1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=results['dates'],
            y=results['equity'],
            mode='lines',
            name='Equity',
            line=dict(color='green', width=2)
        ))
        fig1.update_layout(
            title="Equity Curve",
            xaxis_title="Date",
            yaxis_title="Equity ($)",
            hovermode='x unified'
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with tab2:
        # Calculate drawdown
        cumulative = pd.Series(results['equity'])
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=results['dates'],
            y=drawdown,
            fill='tozeroy',
            mode='lines',
            name='Drawdown',
            line=dict(color='red', width=1)
        ))
        fig2.update_layout(
            title="Drawdown",
            xaxis_title="Date",
            yaxis_title="Drawdown (%)",
            yaxis_tickformat=".1%",
            hovermode='x unified'
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    with tab3:
        fig3 = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Price", "Signals"),
            vertical_spacing=0.1,
            row_heights=[0.7, 0.3]
        )
        
        # Price chart
        fig3.add_trace(
            go.Scatter(
                x=results['dates'],
                y=results['prices'],
                mode='lines',
                name='Price',
                line=dict(color='blue', width=1)
            ),
            row=1, col=1
        )
        
        # Signals chart
        fig3.add_trace(
            go.Scatter(
                x=results['dates'],
                y=results['signals'],
                mode='markers',
                name='Signals',
                marker=dict(
                    size=8,
                    color=results['signals'],
                    colorscale=['red', 'gray', 'green'],
                    showscale=True,
                    colorbar=dict(title="Signal")
                )
            ),
            row=2, col=1
        )
        
        fig3.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)
    
    # Display parameters
    st.header("⚙️ Backtest Parameters")
    st.json(params)

# Strategy comparison section
if "backtest_results" in st.session_state and len(st.session_state.backtest_results) > 1:
    st.header("📊 Strategy Comparison")
    
    # Create comparison table
    comparison_data = []
    for i, result in enumerate(st.session_state.backtest_results):
        comparison_data.append({
            "Strategy": result["strategy"],
            "Parameters": str(result["params"]),
            "Sharpe": f"{result['results']['metrics']['sharpe_ratio']:.2f}",
            "Max DD": f"{result['results']['metrics']['max_drawdown']:.2%}",
            "Total Return": f"{result['results']['metrics']['total_return']:.2%}",
            "Final Equity": f"${result['results']['metrics']['final_equity']:,.0f}"
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, use_container_width=True)
    
    # Comparison chart
    fig_compare = go.Figure()
    
    for i, result in enumerate(st.session_state.backtest_results):
        fig_compare.add_trace(go.Scatter(
            x=result['results']['dates'],
            y=result['results']['equity'],
            mode='lines',
            name=f"{result['strategy']} (Sharpe: {result['results']['metrics']['sharpe_ratio']:.2f})",
            opacity=0.7
        ))
    
    fig_compare.update_layout(
        title="Strategy Comparison - Equity Curves",
        xaxis_title="Date",
        yaxis_title="Equity ($)",
        hovermode='x unified',
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    st.plotly_chart(fig_compare, use_container_width=True)

# Instructions
st.sidebar.markdown("---")
st.sidebar.info("""
**Instructions:**
1. Select strategy and parameters
2. Configure risk management
3. Click 'Run Backtest'
4. Compare multiple strategies
""")

# Footer
st.markdown("---")
st.caption("ML Trading Bot Dashboard v1.0 | Data is simulated for demonstration")