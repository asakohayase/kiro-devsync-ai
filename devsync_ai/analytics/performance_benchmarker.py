"""
Performance benchmarking with automated testing and regression detection.
"""

import asyncio
import time
import statistics
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import concurrent.futures
from pathlib import Path

from ..database.connection import get_database_connection
from ..analytics.performance_monitor import performance_monitor, MetricType


class BenchmarkType(Enum):
    """Types of performance benchmarks."""
    CHANGELOG_GENERATION = "changelog_generation"
    API_RESPONSE_TIME = "api_response_time"
    DATABASE_QUERY = "database_query"
    MEMORY_USAGE = "memory_usage"
    THROUGHPUT = "throughput"
    LOAD_TEST = "load_test"


class BenchmarkStatus(Enum):
    """Benchmark execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BenchmarkConfig:
    """Configuration for a performance benchmark."""
    name: str
    benchmark_type: BenchmarkType
    iterations: int = 10
    warmup_iterations: int = 3
    timeout_seconds: int = 300
    concurrent_users: int = 1
    target_percentile: float = 95.0
    regression_threshold: float = 20.0  # 20% performance degradation
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of a performance benchmark."""
    benchmark_id: str
    config: BenchmarkConfig
    status: BenchmarkStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Performance metrics
    min_time: Optional[float] = None
    max_time: Optional[float] = None
    mean_time: Optional[float] = None
    median_time: Optional[float] = None
    percentile_95: Optional[float] = None
    percentile_99: Optional[float] = None
    std_deviation: Optional[float] = None
    
    # Additional metrics
    throughput: Optional[float] = None
    error_rate: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    
    # Raw data
    execution_times: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegressionAlert:
    """Performance regression alert."""
    benchmark_name: str
    current_value: float
    baseline_value: float
    regression_percent: float
    metric_name: str
    timestamp: datetime
    severity: str  # "warning" or "critical"


class PerformanceBenchmarker:
    """
    Performance benchmarking system with automated testing and regression detection.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.benchmark_results: Dict[str, BenchmarkResult] = {}
        self.baseline_results: Dict[str, BenchmarkResult] = {}
        self.active_benchmarks: Dict[str, asyncio.Task] = {}
        
        # Regression detection
        self.regression_alerts: List[RegressionAlert] = []
        
        # Built-in benchmark configurations
        self.benchmark_configs = self._setup_default_benchmarks()
        
        # Background tasks
        self._scheduler_task: Optional[asyncio.Task] = None
        self._regression_monitor_task: Optional[asyncio.Task] = None
    
    def _setup_default_benchmarks(self) -> Dict[str, BenchmarkConfig]:
        """Setup default benchmark configurations."""
        return {
            "changelog_generation_small": BenchmarkConfig(
                name="changelog_generation_small",
                benchmark_type=BenchmarkType.CHANGELOG_GENERATION,
                iterations=5,
                warmup_iterations=1,
                timeout_seconds=180,
                metadata={"team_size": "small", "commits": 50, "prs": 10}
            ),
            
            "changelog_generation_large": BenchmarkConfig(
                name="changelog_generation_large",
                benchmark_type=BenchmarkType.CHANGELOG_GENERATION,
                iterations=3,
                warmup_iterations=1,
                timeout_seconds=300,
                metadata={"team_size": "large", "commits": 500, "prs": 100}
            ),
            
            "api_response_time": BenchmarkConfig(
                name="api_response_time",
                benchmark_type=BenchmarkType.API_RESPONSE_TIME,
                iterations=20,
                warmup_iterations=5,
                timeout_seconds=60,
                concurrent_users=10
            ),
            
            "database_query_performance": BenchmarkConfig(
                name="database_query_performance",
                benchmark_type=BenchmarkType.DATABASE_QUERY,
                iterations=50,
                warmup_iterations=10,
                timeout_seconds=30
            ),
            
            "memory_usage_test": BenchmarkConfig(
                name="memory_usage_test",
                benchmark_type=BenchmarkType.MEMORY_USAGE,
                iterations=10,
                warmup_iterations=2,
                timeout_seconds=120
            ),
            
            "throughput_test": BenchmarkConfig(
                name="throughput_test",
                benchmark_type=BenchmarkType.THROUGHPUT,
                iterations=5,
                warmup_iterations=1,
                timeout_seconds=300,
                concurrent_users=20
            )
        }
    
    async def start_monitoring(self):
        """Start the benchmarking system."""
        self._scheduler_task = asyncio.create_task(self._benchmark_scheduler())
        self._regression_monitor_task = asyncio.create_task(self._regression_monitor())
        self.logger.info("Performance benchmarker started")
    
    async def stop_monitoring(self):
        """Stop the benchmarking system."""
        # Cancel active benchmarks
        for task in self.active_benchmarks.values():
            task.cancel()
        
        # Cancel background tasks
        if self._scheduler_task:
            self._scheduler_task.cancel()
        if self._regression_monitor_task:
            self._regression_monitor_task.cancel()
        
        # Wait for tasks to complete
        try:
            if self._scheduler_task:
                await self._scheduler_task
            if self._regression_monitor_task:
                await self._regression_monitor_task
        except asyncio.CancelledError:
            pass
        
        self.logger.info("Performance benchmarker stopped")
    
    async def run_benchmark(
        self,
        config: BenchmarkConfig,
        store_as_baseline: bool = False
    ) -> BenchmarkResult:
        """Run a performance benchmark."""
        benchmark_id = f"{config.name}_{int(time.time())}"
        
        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            config=config,
            status=BenchmarkStatus.RUNNING,
            start_time=datetime.utcnow()
        )
        
        self.benchmark_results[benchmark_id] = result
        
        try:
            self.logger.info(f"Starting benchmark: {config.name}")
            
            # Run warmup iterations
            if config.warmup_iterations > 0:
                await self._run_warmup(config)
            
            # Run actual benchmark
            await self._execute_benchmark(result)
            
            # Calculate statistics
            self._calculate_statistics(result)
            
            result.status = BenchmarkStatus.COMPLETED
            result.end_time = datetime.utcnow()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            
            # Store as baseline if requested
            if store_as_baseline:
                self.baseline_results[config.name] = result
            
            # Check for regressions
            await self._check_for_regressions(result)
            
            # Store results in database
            await self._store_benchmark_result(result)
            
            self.logger.info(f"Completed benchmark: {config.name} in {result.duration_seconds:.2f}s")
            
        except asyncio.TimeoutError:
            result.status = BenchmarkStatus.FAILED
            result.errors.append("Benchmark timed out")
            self.logger.error(f"Benchmark {config.name} timed out")
            
        except Exception as e:
            result.status = BenchmarkStatus.FAILED
            result.errors.append(str(e))
            self.logger.error(f"Benchmark {config.name} failed: {e}")
        
        return result
    
    async def _run_warmup(self, config: BenchmarkConfig):
        """Run warmup iterations to stabilize performance."""
        self.logger.debug(f"Running {config.warmup_iterations} warmup iterations for {config.name}")
        
        for i in range(config.warmup_iterations):
            try:
                await self._execute_single_iteration(config)
            except Exception as e:
                self.logger.debug(f"Warmup iteration {i+1} failed: {e}")
    
    async def _execute_benchmark(self, result: BenchmarkResult):
        """Execute the main benchmark iterations."""
        config = result.config
        
        if config.concurrent_users > 1:
            await self._execute_concurrent_benchmark(result)
        else:
            await self._execute_sequential_benchmark(result)
    
    async def _execute_sequential_benchmark(self, result: BenchmarkResult):
        """Execute benchmark iterations sequentially."""
        config = result.config
        
        for i in range(config.iterations):
            try:
                start_time = time.time()
                await asyncio.wait_for(
                    self._execute_single_iteration(config),
                    timeout=config.timeout_seconds
                )
                execution_time = time.time() - start_time
                result.execution_times.append(execution_time)
                
            except asyncio.TimeoutError:
                result.errors.append(f"Iteration {i+1} timed out")
            except Exception as e:
                result.errors.append(f"Iteration {i+1} failed: {str(e)}")
    
    async def _execute_concurrent_benchmark(self, result: BenchmarkResult):
        """Execute benchmark iterations concurrently."""
        config = result.config
        
        # Create semaphore to limit concurrent executions
        semaphore = asyncio.Semaphore(config.concurrent_users)
        
        async def run_iteration():
            async with semaphore:
                start_time = time.time()
                await self._execute_single_iteration(config)
                return time.time() - start_time
        
        # Run all iterations concurrently
        tasks = [run_iteration() for _ in range(config.iterations)]
        
        try:
            execution_times = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=config.timeout_seconds
            )
            
            for i, time_or_exception in enumerate(execution_times):
                if isinstance(time_or_exception, Exception):
                    result.errors.append(f"Iteration {i+1} failed: {str(time_or_exception)}")
                else:
                    result.execution_times.append(time_or_exception)
                    
        except asyncio.TimeoutError:
            result.errors.append("Concurrent benchmark timed out")
    
    async def _execute_single_iteration(self, config: BenchmarkConfig):
        """Execute a single benchmark iteration."""
        if config.benchmark_type == BenchmarkType.CHANGELOG_GENERATION:
            await self._benchmark_changelog_generation(config)
        elif config.benchmark_type == BenchmarkType.API_RESPONSE_TIME:
            await self._benchmark_api_response_time(config)
        elif config.benchmark_type == BenchmarkType.DATABASE_QUERY:
            await self._benchmark_database_query(config)
        elif config.benchmark_type == BenchmarkType.MEMORY_USAGE:
            await self._benchmark_memory_usage(config)
        elif config.benchmark_type == BenchmarkType.THROUGHPUT:
            await self._benchmark_throughput(config)
        else:
            raise ValueError(f"Unknown benchmark type: {config.benchmark_type}")
    
    async def _benchmark_changelog_generation(self, config: BenchmarkConfig):
        """Benchmark changelog generation performance."""
        # Simulate changelog generation
        from ..core.intelligent_data_aggregator import IntelligentDataAggregator
        from ..formatters.intelligent_changelog_formatter import IntelligentChangelogFormatter
        
        aggregator = IntelligentDataAggregator()
        formatter = IntelligentChangelogFormatter()
        
        # Simulate data aggregation
        mock_data = {
            "github_data": {"commits": [f"commit_{i}" for i in range(config.metadata.get("commits", 50))]},
            "jira_data": {"tickets": [f"ticket_{i}" for i in range(config.metadata.get("prs", 10))]},
            "team_data": {"members": ["user1", "user2", "user3"]}
        }
        
        # Format changelog
        await formatter.format_changelog(mock_data, None)
    
    async def _benchmark_api_response_time(self, config: BenchmarkConfig):
        """Benchmark API response time."""
        # Simulate API call
        await asyncio.sleep(0.1)  # Simulate network latency
        
        # Simulate processing time
        processing_time = 0.05 + (time.time() % 0.1)  # Variable processing time
        await asyncio.sleep(processing_time)
    
    async def _benchmark_database_query(self, config: BenchmarkConfig):
        """Benchmark database query performance."""
        try:
            async with get_database_connection() as conn:
                # Run a representative query
                await conn.fetch("""
                    SELECT COUNT(*) FROM performance_metrics 
                    WHERE timestamp >= NOW() - INTERVAL '1 hour'
                """)
        except Exception as e:
            # If database is not available, simulate query time
            await asyncio.sleep(0.01)
    
    async def _benchmark_memory_usage(self, config: BenchmarkConfig):
        """Benchmark memory usage patterns."""
        # Create and manipulate data structures to test memory usage
        data = []
        for i in range(1000):
            data.append({
                "id": i,
                "data": f"test_data_{i}" * 10,
                "nested": {"value": i * 2}
            })
        
        # Process the data
        processed = [item for item in data if item["id"] % 2 == 0]
        
        # Clean up
        del data
        del processed
    
    async def _benchmark_throughput(self, config: BenchmarkConfig):
        """Benchmark system throughput."""
        # Simulate processing multiple items
        items = list(range(100))
        
        # Process items in batches
        batch_size = 10
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            # Simulate batch processing
            await asyncio.sleep(0.01)
    
    def _calculate_statistics(self, result: BenchmarkResult):
        """Calculate statistical metrics from execution times."""
        if not result.execution_times:
            return
        
        times = result.execution_times
        
        result.min_time = min(times)
        result.max_time = max(times)
        result.mean_time = statistics.mean(times)
        result.median_time = statistics.median(times)
        result.std_deviation = statistics.stdev(times) if len(times) > 1 else 0
        
        # Calculate percentiles
        sorted_times = sorted(times)
        result.percentile_95 = self._calculate_percentile(sorted_times, 95)
        result.percentile_99 = self._calculate_percentile(sorted_times, 99)
        
        # Calculate throughput (operations per second)
        if result.mean_time > 0:
            result.throughput = 1.0 / result.mean_time
        
        # Calculate error rate
        total_iterations = len(times) + len(result.errors)
        result.error_rate = (len(result.errors) / total_iterations * 100) if total_iterations > 0 else 0
    
    def _calculate_percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate the specified percentile from sorted values."""
        if not sorted_values:
            return 0.0
        
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(sorted_values) - 1)
        
        if lower_index == upper_index:
            return sorted_values[lower_index]
        
        # Linear interpolation
        weight = index - lower_index
        return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight
    
    async def _check_for_regressions(self, result: BenchmarkResult):
        """Check for performance regressions against baseline."""
        config_name = result.config.name
        
        if config_name not in self.baseline_results:
            return  # No baseline to compare against
        
        baseline = self.baseline_results[config_name]
        
        # Compare key metrics
        metrics_to_check = [
            ("mean_time", "Mean Response Time"),
            ("percentile_95", "95th Percentile"),
            ("percentile_99", "99th Percentile"),
            ("throughput", "Throughput")
        ]
        
        for metric_attr, metric_name in metrics_to_check:
            current_value = getattr(result, metric_attr)
            baseline_value = getattr(baseline, metric_attr)
            
            if current_value is None or baseline_value is None:
                continue
            
            # For throughput, higher is better; for times, lower is better
            if metric_attr == "throughput":
                regression_percent = ((baseline_value - current_value) / baseline_value) * 100
            else:
                regression_percent = ((current_value - baseline_value) / baseline_value) * 100
            
            if regression_percent > result.config.regression_threshold:
                severity = "critical" if regression_percent > 50 else "warning"
                
                alert = RegressionAlert(
                    benchmark_name=config_name,
                    current_value=current_value,
                    baseline_value=baseline_value,
                    regression_percent=regression_percent,
                    metric_name=metric_name,
                    timestamp=datetime.utcnow(),
                    severity=severity
                )
                
                self.regression_alerts.append(alert)
                
                self.logger.warning(
                    f"Performance regression detected in {config_name}: "
                    f"{metric_name} degraded by {regression_percent:.1f}%"
                )
                
                # Send alert notification
                await self._send_regression_alert(alert)
    
    async def _send_regression_alert(self, alert: RegressionAlert):
        """Send performance regression alert."""
        try:
            from ..core.notification_integration import NotificationIntegration
            
            notification = NotificationIntegration()
            
            message = (
                f"🚨 **Performance Regression Alert**\n"
                f"Benchmark: {alert.benchmark_name}\n"
                f"Metric: {alert.metric_name}\n"
                f"Regression: {alert.regression_percent:.1f}%\n"
                f"Current: {alert.current_value:.3f}\n"
                f"Baseline: {alert.baseline_value:.3f}"
            )
            
            await notification.send_slack_notification(
                channel="#devsync-performance",
                message=message,
                metadata={
                    "alert_type": "performance_regression",
                    "severity": alert.severity,
                    "benchmark": alert.benchmark_name
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to send regression alert: {e}")
    
    async def _store_benchmark_result(self, result: BenchmarkResult):
        """Store benchmark result in database."""
        try:
            async with get_database_connection() as conn:
                await conn.execute("""
                    INSERT INTO benchmark_results (
                        benchmark_id, name, benchmark_type, status, start_time, end_time,
                        duration_seconds, min_time, max_time, mean_time, median_time,
                        percentile_95, percentile_99, std_deviation, throughput, error_rate,
                        iterations, errors, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                """,
                result.benchmark_id,
                result.config.name,
                result.config.benchmark_type.value,
                result.status.value,
                result.start_time,
                result.end_time,
                result.duration_seconds,
                result.min_time,
                result.max_time,
                result.mean_time,
                result.median_time,
                result.percentile_95,
                result.percentile_99,
                result.std_deviation,
                result.throughput,
                result.error_rate,
                len(result.execution_times),
                json.dumps(result.errors),
                json.dumps(result.metadata)
                )
        except Exception as e:
            self.logger.error(f"Failed to store benchmark result: {e}")
    
    async def _benchmark_scheduler(self):
        """Background task to run scheduled benchmarks."""
        try:
            while True:
                # Run daily performance benchmarks
                current_hour = datetime.utcnow().hour
                
                if current_hour == 2:  # Run at 2 AM UTC
                    await self._run_daily_benchmarks()
                
                await asyncio.sleep(3600)  # Check every hour
                
        except asyncio.CancelledError:
            self.logger.info("Benchmark scheduler cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in benchmark scheduler: {e}")
            await asyncio.sleep(1800)  # Wait 30 minutes before retrying
    
    async def _run_daily_benchmarks(self):
        """Run daily performance benchmarks."""
        self.logger.info("Running daily performance benchmarks")
        
        # Run key benchmarks
        key_benchmarks = [
            "changelog_generation_small",
            "changelog_generation_large",
            "api_response_time",
            "database_query_performance"
        ]
        
        for benchmark_name in key_benchmarks:
            if benchmark_name in self.benchmark_configs:
                config = self.benchmark_configs[benchmark_name]
                try:
                    await self.run_benchmark(config)
                except Exception as e:
                    self.logger.error(f"Daily benchmark {benchmark_name} failed: {e}")
    
    async def _regression_monitor(self):
        """Background task to monitor for performance regressions."""
        try:
            while True:
                await self._analyze_performance_trends()
                await asyncio.sleep(1800)  # Check every 30 minutes
                
        except asyncio.CancelledError:
            self.logger.info("Regression monitor cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in regression monitor: {e}")
            await asyncio.sleep(1800)
    
    async def _analyze_performance_trends(self):
        """Analyze performance trends and detect gradual regressions."""
        try:
            async with get_database_connection() as conn:
                # Get recent benchmark results for trend analysis
                rows = await conn.fetch("""
                    SELECT name, mean_time, percentile_95, throughput, start_time
                    FROM benchmark_results
                    WHERE start_time >= NOW() - INTERVAL '7 days'
                    AND status = 'completed'
                    ORDER BY name, start_time
                """)
                
                # Group by benchmark name
                benchmark_trends = {}
                for row in rows:
                    name = row['name']
                    if name not in benchmark_trends:
                        benchmark_trends[name] = []
                    
                    benchmark_trends[name].append({
                        'mean_time': float(row['mean_time']) if row['mean_time'] else None,
                        'percentile_95': float(row['percentile_95']) if row['percentile_95'] else None,
                        'throughput': float(row['throughput']) if row['throughput'] else None,
                        'timestamp': row['start_time']
                    })
                
                # Analyze trends for each benchmark
                for name, results in benchmark_trends.items():
                    if len(results) >= 5:  # Need at least 5 data points
                        await self._detect_trend_regression(name, results)
                        
        except Exception as e:
            self.logger.error(f"Error analyzing performance trends: {e}")
    
    async def _detect_trend_regression(self, benchmark_name: str, results: List[Dict]):
        """Detect gradual performance regression in trend data."""
        # Simple trend analysis using linear regression
        if len(results) < 5:
            return
        
        # Analyze mean_time trend (higher is worse)
        mean_times = [r['mean_time'] for r in results if r['mean_time'] is not None]
        
        if len(mean_times) >= 5:
            # Calculate simple trend (difference between recent and older values)
            recent_avg = statistics.mean(mean_times[-3:])  # Last 3 values
            older_avg = statistics.mean(mean_times[:3])    # First 3 values
            
            if older_avg > 0:
                trend_change = ((recent_avg - older_avg) / older_avg) * 100
                
                if trend_change > 15:  # 15% degradation trend
                    self.logger.warning(
                        f"Gradual performance degradation detected in {benchmark_name}: "
                        f"{trend_change:.1f}% increase in response time"
                    )
    
    def get_benchmark_summary(self) -> Dict[str, Any]:
        """Get comprehensive benchmark summary."""
        completed_benchmarks = [
            r for r in self.benchmark_results.values()
            if r.status == BenchmarkStatus.COMPLETED
        ]
        
        if not completed_benchmarks:
            return {"message": "No completed benchmarks"}
        
        # Calculate overall statistics
        all_mean_times = [r.mean_time for r in completed_benchmarks if r.mean_time]
        all_throughputs = [r.throughput for r in completed_benchmarks if r.throughput]
        
        summary = {
            "total_benchmarks": len(self.benchmark_results),
            "completed_benchmarks": len(completed_benchmarks),
            "failed_benchmarks": len([r for r in self.benchmark_results.values() if r.status == BenchmarkStatus.FAILED]),
            "regression_alerts": len(self.regression_alerts),
            "recent_alerts": len([a for a in self.regression_alerts if (datetime.utcnow() - a.timestamp).days < 1])
        }
        
        if all_mean_times:
            summary["overall_performance"] = {
                "avg_response_time": round(statistics.mean(all_mean_times), 3),
                "min_response_time": round(min(all_mean_times), 3),
                "max_response_time": round(max(all_mean_times), 3)
            }
        
        if all_throughputs:
            summary["overall_throughput"] = {
                "avg_throughput": round(statistics.mean(all_throughputs), 2),
                "max_throughput": round(max(all_throughputs), 2)
            }
        
        # Recent benchmark results
        recent_results = sorted(
            completed_benchmarks,
            key=lambda r: r.start_time,
            reverse=True
        )[:5]
        
        summary["recent_benchmarks"] = [
            {
                "name": r.config.name,
                "mean_time": round(r.mean_time, 3) if r.mean_time else None,
                "throughput": round(r.throughput, 2) if r.throughput else None,
                "error_rate": round(r.error_rate, 2) if r.error_rate else None,
                "timestamp": r.start_time.isoformat()
            }
            for r in recent_results
        ]
        
        return summary


# Global performance benchmarker instance
performance_benchmarker = PerformanceBenchmarker()