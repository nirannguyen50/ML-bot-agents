"""
Core parallel execution engine for backtesting
"""
import multiprocessing as mp
from typing import List, Dict, Any, Callable
import concurrent.futures
import logging
from dataclasses import dataclass
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BacktestJob:
    """Represents a single backtest job"""
    strategy_id: str
    strategy_config: Dict[str, Any]
    timeframe: str
    start_date: str
    end_date: str
    data_source: str
    job_id: str = None
    
    def __post_init__(self):
        if not self.job_id:
            self.job_id = f"{self.strategy_id}_{self.timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


@dataclass
class BacktestResult:
    """Results from a single backtest"""
    job_id: str
    strategy_id: str
    timeframe: str
    metrics: Dict[str, Any]
    execution_time: float
    status: str  # 'success', 'failed', 'partial'
    error_message: str = None


class ParallelBacktestEngine:
    """
    Main engine for parallel backtest execution
    Supports both multiprocessing and distributed computing
    """
    
    def __init__(self, max_workers: int = None, use_distributed: bool = False):
        """
        Initialize parallel backtest engine
        
        Args:
            max_workers: Maximum number of parallel workers
            use_distributed: Whether to use distributed computing (future enhancement)
        """
        self.max_workers = max_workers or mp.cpu_count() - 1
        self.use_distributed = use_distributed
        self.results: List[BacktestResult] = []
        self.logger = logger
        
    def run_single_backtest(self, job: BacktestJob) -> BacktestResult:
        """
        Execute a single backtest job
        This will integrate with the existing backtest engine
        """
        from workspace.backtest_engine import BacktestEngine  # Import existing engine
        
        try:
            self.logger.info(f"Starting backtest job {job.job_id}")
            start_time = datetime.now()
            
            # Create and run backtest using existing engine
            engine = BacktestEngine(
                strategy_config=job.strategy_config,
                timeframe=job.timeframe,
                start_date=job.start_date,
                end_date=job.end_date,
                data_source=job.data_source
            )
            
            # Run backtest (this should call the existing engine)
            results = engine.run()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return BacktestResult(
                job_id=job.job_id,
                strategy_id=job.strategy_id,
                timeframe=job.timeframe,
                metrics=results,
                execution_time=execution_time,
                status='success'
            )
            
        except Exception as e:
            self.logger.error(f"Backtest job {job.job_id} failed: {str(e)}")
            return BacktestResult(
                job_id=job.job_id,
                strategy_id=job.strategy_id,
                timeframe=job.timeframe,
                metrics={},
                execution_time=0,
                status='failed',
                error_message=str(e)
            )
    
    def run_parallel(self, jobs: List[BacktestJob]) -> List[BacktestResult]:
        """
        Execute multiple backtest jobs in parallel
        
        Args:
            jobs: List of backtest jobs to execute
            
        Returns:
            List of backtest results
        """
        self.logger.info(f"Starting parallel execution of {len(jobs)} jobs with {self.max_workers} workers")
        
        results = []
        
        # Using ThreadPoolExecutor for I/O bound or ProcessPoolExecutor for CPU bound
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs
            future_to_job = {
                executor.submit(self.run_single_backtest, job): job 
                for job in jobs
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    result = future.result(timeout=300)  # 5-minute timeout
                    results.append(result)
                    self.logger.info(f"Completed job {job.job_id} in {result.execution_time:.2f}s")
                except concurrent.futures.TimeoutError:
                    self.logger.error(f"Job {job.job_id} timed out")
                    results.append(BacktestResult(
                        job_id=job.job_id,
                        strategy_id=job.strategy_id,
                        timeframe=job.timeframe,
                        metrics={},
                        execution_time=300,
                        status='failed',
                        error_message='Execution timeout'
                    ))
                except Exception as e:
                    self.logger.error(f"Job {job.job_id} failed with exception: {str(e)}")
                    results.append(BacktestResult(
                        job_id=job.job_id,
                        strategy_id=job.strategy_id,
                        timeframe=job.timeframe,
                        metrics={},
                        execution_time=0,
                        status='failed',
                        error_message=str(e)
                    ))
        
        self.results = results
        return results
    
    def generate_comparison_report(self) -> Dict[str, Any]:
        """
        Generate a comparison report from all results
        Suitable for dashboard integration
        """
        report = {
            'total_jobs': len(self.results),
            'successful_jobs': len([r for r in self.results if r.status == 'success']),
            'failed_jobs': len([r for r in self.results if r.status == 'failed']),
            'total_execution_time': sum(r.execution_time for r in self.results),
            'results_by_strategy': {},
            'results_by_timeframe': {},
            'performance_summary': {}
        }
        
        # Organize results by strategy
        for result in self.results:
            if result.status == 'success':
                if result.strategy_id not in report['results_by_strategy']:
                    report['results_by_strategy'][result.strategy_id] = []
                report['results_by_strategy'][result.strategy_id].append({
                    'timeframe': result.timeframe,
                    'metrics': result.metrics,
                    'execution_time': result.execution_time
                })
                
                # Organize by timeframe
                if result.timeframe not in report['results_by_timeframe']:
                    report['results_by_timeframe'][result.timeframe] = []
                report['results_by_timeframe'][result.timeframe].append({
                    'strategy_id': result.strategy_id,
                    'metrics': result.metrics
                })
        
        # Calculate performance summary
        if report['successful_jobs'] > 0:
            report['performance_summary'] = {
                'avg_execution_time': report['total_execution_time'] / report['successful_jobs'],
                'success_rate': report['successful_jobs'] / report['total_jobs'] * 100
            }
        
        return report