#!/usr/bin/env python3
"""
Performance Benchmarking Script for Intelligent Data Aggregator

This script provides comprehensive performance testing and benchmarking
for the IntelligentDataAggregator system, including:
- Load testing with concurrent requests
- Scalability testing with increasing data volumes
- Cache performance analysis
- Circuit breaker behavior testing
- Memory and CPU usage monitoring
"""

import asyncio
import time
import statistics
import psutil
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

from devsync_ai.core.intelligent_data_aggregator import (
    IntelligentDataAggregator,
    DataCollectionConfig,
    DataSourceType,
    PerformanceBenchmark
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemMonitor:
    """Monitor system resources during benchmarking."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.monitoring = False
        self.metrics = []
    
    async def start_monitoring(self, interval: float = 1.0):
        """Start monitoring system resources."""
        self.monitoring = True
        self.metrics = []
        
        while self.monitoring:
            try:
                cpu_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                self.metrics.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_mb,
                    'threads': self.process.num_threads()
                })
                
                await asyncio.sleep(interval)
            except Exception as e:
                logger.warning(f"Monitoring error: {e}")
                break
    
    def stop_monitoring(self):
        """Stop monitoring and return collected metrics."""
        self.monitoring = False
        return self.metrics
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of collected metrics."""
        if not self.metrics:
            return {}
        
        cpu_values = [m['cpu_percent'] for m in self.metrics]
        memory_values = [m['memory_mb'] for m in self.metrics]
        
        return {
            'cpu_stats': {
                'avg': statistics.mean(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values),
                'stdev': statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
            },
            'memory_stats': {
                'avg': statistics.mean(memory_values),
                'max': max(memory_values),
                'min': min(memory_values),
                'stdev': statistics.stdev(memory_values) if len(memory_values) > 1 else 0
            },
            'sample_count': len(self.metrics)
        }


class MockDataGenerator:
    """Generate mock data for testing different scenarios."""
    
    @staticmethod
    def generate_github_data(commit_count: int = 50, pr_count: int = 10) -> Dict[str, Any]:
        """Generate mock GitHub data with specified volume."""
        commits = []
        for i in range(commit_count):
            commits.append({
                'sha': f"{'a' * 39}{i:01d}",
                'message': f"Commit {i}: Implement feature X",
                'author': f"user{i % 5}",
                'timestamp': (datetime.utcnow() - timedelta(hours=i)).isoformat()
            })
        
        pull_requests = []
        for i in range(pr_count):
            pull_requests.append({
                'number': i + 1,
                'title': f"PR {i + 1}: Add new functionality",
                'state': 'merged' if i % 3 == 0 else 'open',
                'author': f"user{i % 3}",
                'created_at': (datetime.utcnow() - timedelta(days=i)).isoformat()
            })
        
        return {
            'commits': commits,
            'pull_requests': pull_requests,
            'contributors': [f"user{i}" for i in range(5)],
            'repository_health': {
                'code_quality': 0.85,
                'test_coverage': 0.78,
                'technical_debt': 0.23
            }
        }
    
    @staticmethod
    def generate_jira_data(issue_count: int = 30) -> Dict[str, Any]:
        """Generate mock JIRA data with specified volume."""
        issues = []
        statuses = ['To Do', 'In Progress', 'Done', 'Blocked']
        types = ['Story', 'Bug', 'Task', 'Epic']
        
        for i in range(issue_count):
            issues.append({
                'key': f"PROJ-{i + 100}",
                'summary': f"Issue {i + 1}: Implement feature Y",
                'status': statuses[i % len(statuses)],
                'type': types[i % len(types)],
                'assignee': f"user{i % 4}",
                'created': (datetime.utcnow() - timedelta(days=i)).isoformat()
            })
        
        return {
            'issues': issues,
            'sprint_info': {
                'name': 'Sprint 15',
                'state': 'active',
                'velocity': 28,
                'capacity': 35
            },
            'velocity_metrics': {
                'average_velocity': 25.5,
                'velocity_trend': 'increasing',
                'completion_rate': 0.87
            }
        }
    
    @staticmethod
    def generate_team_metrics() -> Dict[str, Any]:
        """Generate mock team productivity metrics."""
        return {
            'productivity_metrics': {
                'velocity': 26.5,
                'cycle_time': 4.2,
                'lead_time': 8.7,
                'deployment_frequency': 2.3
            },
            'collaboration_metrics': {
                'review_participation': 0.89,
                'cross_team_work': 0.34,
                'knowledge_sharing': 0.67,
                'meeting_efficiency': 0.72
            },
            'deployment_metrics': {
                'success_rate': 0.94,
                'rollback_rate': 0.06,
                'mttr': 1.2,
                'change_failure_rate': 0.08
            }
        }


class BenchmarkSuite:
    """Comprehensive benchmarking suite for the data aggregator."""
    
    def __init__(self, config: DataCollectionConfig = None):
        self.config = config or DataCollectionConfig()
        self.aggregator = None
        self.monitor = SystemMonitor()
        self.results = {}
    
    async def setup(self):
        """Set up the benchmarking environment."""
        logger.info("Setting up benchmark environment...")
        
        self.aggregator = IntelligentDataAggregator(self.config)
        
        # Register mock services with data generators
        await self._register_mock_services()
        
        logger.info("Benchmark environment ready")
    
    async def _register_mock_services(self):
        """Register mock services for testing."""
        from unittest.mock import AsyncMock
        
        # Mock GitHub service
        mock_github = AsyncMock()
        self.aggregator.register_data_source(
            DataSourceType.GITHUB, "benchmark", mock_github
        )
        
        # Mock JIRA service
        mock_jira = AsyncMock()
        self.aggregator.register_data_source(
            DataSourceType.JIRA, "benchmark", mock_jira
        )
        
        # Mock team metrics service
        mock_team = AsyncMock()
        self.aggregator.register_data_source(
            DataSourceType.TEAM_METRICS, "benchmark", mock_team
        )
        
        # Patch collection methods with mock data generators
        async def mock_github_collect(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate API delay
            return MockDataGenerator.generate_github_data()
        
        async def mock_jira_collect(*args, **kwargs):
            await asyncio.sleep(0.15)  # Simulate API delay
            return MockDataGenerator.generate_jira_data()
        
        async def mock_team_collect(*args, **kwargs):
            await asyncio.sleep(0.05)  # Simulate processing delay
            return MockDataGenerator.generate_team_metrics()
        
        # Monkey patch the collection methods
        self.aggregator._collect_github_data = mock_github_collect
        self.aggregator._collect_jira_data = mock_jira_collect
        self.aggregator._collect_team_metrics = mock_team_collect
    
    async def run_load_test(self, concurrent_requests: int = 10, 
                          duration_seconds: int = 30) -> Dict[str, Any]:
        """Run load testing with concurrent requests."""
        logger.info(f"Starting load test: {concurrent_requests} concurrent requests for {duration_seconds}s")
        
        # Start system monitoring
        monitor_task = asyncio.create_task(self.monitor.start_monitoring(0.5))
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        request_count = 0
        successful_requests = 0
        failed_requests = 0
        response_times = []
        
        async def make_request():
            nonlocal request_count, successful_requests, failed_requests
            
            team_id = f"team_{request_count % 5}"  # Rotate between 5 teams
            date_range = (
                datetime.utcnow() - timedelta(days=7),
                datetime.utcnow()
            )
            
            request_start = time.time()
            try:
                result = await self.aggregator.aggregate_data(team_id, date_range)
                request_time = time.time() - request_start
                response_times.append(request_time)
                successful_requests += 1
                return result
            except Exception as e:
                logger.warning(f"Request failed: {e}")
                failed_requests += 1
                return None
        
        # Run concurrent requests for the specified duration
        while time.time() < end_time:
            # Create batch of concurrent requests
            tasks = []
            for _ in range(concurrent_requests):
                if time.time() >= end_time:
                    break
                tasks.append(asyncio.create_task(make_request()))
                request_count += 1
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        await monitor_task
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        load_test_results = {
            'test_type': 'load_test',
            'duration_seconds': total_time,
            'concurrent_requests': concurrent_requests,
            'total_requests': request_count,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': successful_requests / max(request_count, 1),
            'requests_per_second': request_count / total_time,
            'successful_rps': successful_requests / total_time,
            'response_time_stats': {
                'avg': statistics.mean(response_times) if response_times else 0,
                'median': statistics.median(response_times) if response_times else 0,
                'p95': self._percentile(response_times, 95) if response_times else 0,
                'p99': self._percentile(response_times, 99) if response_times else 0,
                'min': min(response_times) if response_times else 0,
                'max': max(response_times) if response_times else 0
            },
            'system_resources': self.monitor.get_summary()
        }
        
        logger.info(f"Load test completed: {successful_requests}/{request_count} successful "
                   f"({load_test_results['success_rate']:.2%}), "
                   f"{load_test_results['successful_rps']:.2f} RPS")
        
        return load_test_results
    
    async def run_scalability_test(self, team_counts: List[int] = None) -> Dict[str, Any]:
        """Test scalability with increasing number of teams."""
        if team_counts is None:
            team_counts = [1, 5, 10, 20, 50]
        
        logger.info(f"Starting scalability test with team counts: {team_counts}")
        
        scalability_results = {
            'test_type': 'scalability_test',
            'team_counts': team_counts,
            'results': []
        }
        
        date_range = (datetime.utcnow() - timedelta(days=7), datetime.utcnow())
        
        for team_count in team_counts:
            logger.info(f"Testing with {team_count} teams...")
            
            # Generate team IDs
            team_ids = [f"team_{i}" for i in range(team_count)]
            
            # Start monitoring
            monitor_task = asyncio.create_task(self.monitor.start_monitoring(0.5))
            
            # Run benchmark
            start_time = time.time()
            
            benchmark_result = await PerformanceBenchmark.benchmark_parallel_collection(
                self.aggregator, team_ids, date_range, iterations=3
            )
            
            total_time = time.time() - start_time
            
            # Stop monitoring
            self.monitor.stop_monitoring()
            await monitor_task
            
            # Add system resource data
            benchmark_result['system_resources'] = self.monitor.get_summary()
            benchmark_result['total_benchmark_time'] = total_time
            
            scalability_results['results'].append(benchmark_result)
            
            logger.info(f"Team count {team_count}: {benchmark_result['avg_collection_time']:.2f}s avg, "
                       f"{benchmark_result['avg_success_rate']:.2%} success rate")
        
        return scalability_results
    
    async def run_cache_performance_test(self) -> Dict[str, Any]:
        """Test cache performance and hit rates."""
        logger.info("Starting cache performance test...")
        
        cache_results = {
            'test_type': 'cache_performance_test',
            'phases': []
        }
        
        team_id = "cache_test_team"
        date_range = (datetime.utcnow() - timedelta(days=7), datetime.utcnow())
        
        # Phase 1: Cold cache (first requests)
        logger.info("Phase 1: Cold cache performance")
        cold_start = time.time()
        cold_results = []
        
        for i in range(5):
            start_time = time.time()
            await self.aggregator.aggregate_data(team_id, date_range)
            request_time = time.time() - start_time
            cold_results.append(request_time)
        
        cold_phase = {
            'phase': 'cold_cache',
            'request_count': len(cold_results),
            'avg_response_time': statistics.mean(cold_results),
            'total_time': time.time() - cold_start
        }
        cache_results['phases'].append(cold_phase)
        
        # Phase 2: Warm cache (repeated requests)
        logger.info("Phase 2: Warm cache performance")
        warm_start = time.time()
        warm_results = []
        
        for i in range(10):
            start_time = time.time()
            await self.aggregator.aggregate_data(team_id, date_range)
            request_time = time.time() - start_time
            warm_results.append(request_time)
        
        warm_phase = {
            'phase': 'warm_cache',
            'request_count': len(warm_results),
            'avg_response_time': statistics.mean(warm_results),
            'total_time': time.time() - warm_start
        }
        cache_results['phases'].append(warm_phase)
        
        # Calculate cache efficiency
        cache_speedup = cold_phase['avg_response_time'] / warm_phase['avg_response_time']
        cache_results['cache_speedup_factor'] = cache_speedup
        cache_results['cache_efficiency'] = (cache_speedup - 1) / cache_speedup
        
        logger.info(f"Cache performance: {cache_speedup:.2f}x speedup, "
                   f"{cache_results['cache_efficiency']:.2%} efficiency")
        
        return cache_results
    
    async def run_circuit_breaker_test(self) -> Dict[str, Any]:
        """Test circuit breaker behavior under failure conditions."""
        logger.info("Starting circuit breaker test...")
        
        # Create a separate aggregator for this test
        test_config = DataCollectionConfig(
            circuit_breaker_failure_threshold=3,
            circuit_breaker_recovery_timeout=5,
            max_retries=1
        )
        test_aggregator = IntelligentDataAggregator(test_config)
        
        # Register a mock service that will fail
        from unittest.mock import AsyncMock
        
        mock_service = AsyncMock()
        test_aggregator.register_data_source(
            DataSourceType.CUSTOM, "failing_service", mock_service
        )
        
        failure_count = 0
        
        async def failing_collect(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 5:  # Fail first 5 attempts
                raise Exception(f"Simulated failure #{failure_count}")
            # Succeed after 5 failures
            return {"recovered": True, "attempt": failure_count}
        
        # Patch the collection method
        test_aggregator._collect_single_source = failing_collect
        
        circuit_breaker_results = {
            'test_type': 'circuit_breaker_test',
            'attempts': []
        }
        
        team_id = "circuit_test_team"
        date_range = (datetime.utcnow() - timedelta(days=7), datetime.utcnow())
        
        # Make multiple attempts to trigger circuit breaker
        for attempt in range(10):
            start_time = time.time()
            try:
                result = await test_aggregator.aggregate_data(team_id, date_range)
                success = True
                error = None
            except Exception as e:
                success = False
                error = str(e)
                result = None
            
            attempt_time = time.time() - start_time
            
            # Get circuit breaker state
            health_status = await test_aggregator.get_health_status()
            
            attempt_result = {
                'attempt': attempt + 1,
                'success': success,
                'error': error,
                'response_time': attempt_time,
                'circuit_breaker_states': {
                    source_key: source_health.get('circuit_breaker_state', 'unknown')
                    for source_key, source_health in health_status.get('data_sources', {}).items()
                }
            }
            
            circuit_breaker_results['attempts'].append(attempt_result)
            
            logger.info(f"Attempt {attempt + 1}: {'SUCCESS' if success else 'FAILED'} "
                       f"({attempt_time:.3f}s)")
            
            # Small delay between attempts
            await asyncio.sleep(0.5)
        
        # Calculate summary statistics
        successful_attempts = sum(1 for a in circuit_breaker_results['attempts'] if a['success'])
        circuit_breaker_results['total_attempts'] = len(circuit_breaker_results['attempts'])
        circuit_breaker_results['successful_attempts'] = successful_attempts
        circuit_breaker_results['failure_rate'] = 1 - (successful_attempts / len(circuit_breaker_results['attempts']))
        
        await test_aggregator.cleanup()
        
        logger.info(f"Circuit breaker test completed: {successful_attempts}/{len(circuit_breaker_results['attempts'])} successful")
        
        return circuit_breaker_results
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    async def run_full_benchmark_suite(self) -> Dict[str, Any]:
        """Run the complete benchmark suite."""
        logger.info("Starting full benchmark suite...")
        
        full_results = {
            'benchmark_suite': 'intelligent_data_aggregator',
            'timestamp': datetime.utcnow().isoformat(),
            'configuration': {
                'max_retries': self.config.max_retries,
                'retry_delay': self.config.retry_delay,
                'timeout_seconds': self.config.timeout_seconds,
                'parallel_workers': self.config.parallel_workers,
                'cache_ttl_seconds': self.config.cache_ttl_seconds
            },
            'tests': {}
        }
        
        try:
            # Run load test
            full_results['tests']['load_test'] = await self.run_load_test(
                concurrent_requests=5, duration_seconds=20
            )
            
            # Run scalability test
            full_results['tests']['scalability_test'] = await self.run_scalability_test(
                team_counts=[1, 5, 10, 20]
            )
            
            # Run cache performance test
            full_results['tests']['cache_performance_test'] = await self.run_cache_performance_test()
            
            # Run circuit breaker test
            full_results['tests']['circuit_breaker_test'] = await self.run_circuit_breaker_test()
            
            logger.info("Full benchmark suite completed successfully")
            
        except Exception as e:
            logger.error(f"Benchmark suite failed: {e}")
            full_results['error'] = str(e)
        
        return full_results
    
    async def cleanup(self):
        """Clean up benchmark resources."""
        if self.aggregator:
            await self.aggregator.cleanup()
        logger.info("Benchmark cleanup completed")


async def main():
    """Main benchmark execution function."""
    parser = argparse.ArgumentParser(description="Benchmark the Intelligent Data Aggregator")
    parser.add_argument("--test", choices=['load', 'scalability', 'cache', 'circuit_breaker', 'full'],
                       default='full', help="Type of test to run")
    parser.add_argument("--concurrent", type=int, default=10,
                       help="Number of concurrent requests for load test")
    parser.add_argument("--duration", type=int, default=30,
                       help="Duration in seconds for load test")
    parser.add_argument("--output", type=str, help="Output file for results (JSON)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create benchmark configuration
    config = DataCollectionConfig(
        max_retries=3,
        retry_delay=0.5,
        timeout_seconds=30,
        parallel_workers=4,
        cache_ttl_seconds=300
    )
    
    # Initialize benchmark suite
    benchmark = BenchmarkSuite(config)
    
    try:
        await benchmark.setup()
        
        # Run selected test
        if args.test == 'load':
            results = await benchmark.run_load_test(args.concurrent, args.duration)
        elif args.test == 'scalability':
            results = await benchmark.run_scalability_test()
        elif args.test == 'cache':
            results = await benchmark.run_cache_performance_test()
        elif args.test == 'circuit_breaker':
            results = await benchmark.run_circuit_breaker_test()
        else:  # full
            results = await benchmark.run_full_benchmark_suite()
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Results saved to {args.output}")
        else:
            print(json.dumps(results, indent=2, default=str))
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        return 1
    
    finally:
        await benchmark.cleanup()
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))