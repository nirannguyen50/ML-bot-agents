"""
Parallel Backtesting System
Engineer: ML Trading Bot Team
"""
from .core import ParallelBacktestEngine
from .strategies import StrategyRegistry
from .distributor import TaskDistributor
from .results import ResultsAggregator

__version__ = "1.0.0"
__all__ = ['ParallelBacktestEngine', 'StrategyRegistry', 'TaskDistributor', 'ResultsAggregator']