#!/usr/bin/env python3
"""
Performance optimization system demonstration script.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def demonstrate_performance_monitoring():
    """Demonstrate performance monitoring capabilities."""
    logger.info("=== Performance Monitoring Demo ===")
    
    from devsync_ai.analytics.performance_monitor import performance_monitor, MetricType
    
    # Start monitoring
    await performance_monitor.start_monitoring()
    
    try:
        # Simulate various operations
        logger.info("Recording performance metrics...")
        
        # Record API response times
        for i in range(10):
            response_time = 0.1 + (i * 0.05)  # Increasing response times
            await performance_monitor.record_metric(
                MetricType.API_RESPONSE_TIME,
                response_time,
                team_id="demo_team",
                metadata={"endpoint": f"/api/endpoint_{i}"}
            )
        
        # Record memory usage
        for usage in [45.0, 55.0, 65.0, 75.0, 85.0]:  # Increasing memory usage
            await performance_monitor.record_metric(
                MetricType.MEMORY_USAGE,
                usage,
                metadata={"process": "changelog_generation"}
            )
        
        # Simulate operation tracking
        operation_id = await performance_monitor.start_operation(
            "demo_operation", "changelog_generation", "demo_team"
        )
        
        await asyncio.sleep(0.5)  # Simulate work
        
        await performance_monitor.end_operation(operation_id, success=True, team_id="demo_team")
        
        # Get system health
        health = await performance_monitor.get_system_health()
        logger.info(f"System Health: {health.status} (CPU: {health.cpu_usage:.1f}%, Memory: {health.memory_usage:.1f}%)")
        
        # Get performance summary
        summary = await performance_monitor.get_performance_summary(team_id="demo_team")
        logger.info(f"Performance Summary: {len(summary)} metric types recorded")
        
    finally:
        await performance_monitor.stop_monitoring()


async def demonstrate_query_optimization():
    """Demonstrate query optimization and caching."""
    logger.info("=== Query Optimization Demo ===")
    
    from devsync_ai.core.query_optimizer import query_optimizer, CacheStrategy
    
    # Simulate database queries with caching
    test_queries = [
        ("SELECT * FROM performance_metrics WHERE team_id = $1", ["demo_team"]),
        ("SELECT COUNT(*) FROM changelog_entries WHERE status = $1", ["completed"]),
        ("SELECT * FROM performance_metrics WHERE team_id = $1", ["demo_team"]),  # Duplicate for cache hit
    ]
    
    logger.info("Executing queries with caching...")
    
    for i, (query, params) in enumerate(test_queries):
        start_time = time.time()
        
        try:
            # Execute with caching
            result = await query_optimizer.execute_optimized_query(
                query, params, CacheStrategy.MEDIUM_TERM, f"demo_query_{i}"
            )
            
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"Query {i+1}: {execution_time:.2f}ms ({len(result)} rows)")
            
        except Exception as e:
            logger.warning(f"Query {i+1} failed (expected in demo): {e}")
    
    # Get cache statistics
    cache_stats = await query_optimizer.get_cache_stats()
    logger.info(f"Cache Stats: {cache_stats['overall_performance']['hit_rate_percent']:.1f}% hit rate")


async def demonstrate_load_balancing():
    """Demonstrate load balancing capabilities."""
    logger.info("=== Load Balancing Demo ===")
    
    from devsync_ai.core.load_balancer import load_balancer
    
    await load_balancer.start()
    
    try:
        # Register demo workers
        load_balancer.register_worker("demo_worker_1", "localhost", 8001, weight=1.0)
        load_balancer.register_worker("demo_worker_2", "localhost", 8002, weight=1.5)
        load_balancer.register_worker("demo_worker_3", "localhost", 8003, weight=0.8)
        
        logger.info(f"Registered {len(load_balancer.worker_nodes)} workers")
        
        # Submit tasks with different priorities
        task_ids = []
        for priority in [1, 2, 3, 4, 5]:
            for i in range(3):
                task_id = await load_balancer.submit_task(
                    f"demo_task_p{priority}",
                    {"data": f"test_data_{i}", "priority": priority},
                    priority=priority,
                    team_id="demo_team"
                )
                task_ids.append(task_id)
        
        logger.info(f"Submitted {len(task_ids)} tasks")
        
        # Wait for some processing
        await asyncio.sleep(2)
        
        # Get load balancer statistics
        stats = load_balancer.get_load_balancer_stats()
        logger.info(f"Load Balancer Stats:")
        logger.info(f"  Workers: {stats['workers']['healthy']} healthy, {stats['workers']['total']} total")
        logger.info(f"  Capacity: {stats['capacity']['utilization_percent']:.1f}% utilized")
        logger.info(f"  Tasks: {stats['tasks']['active']} active, {stats['tasks']['completed']} completed")
        
    finally:
        await load_balancer.stop()


async def demonstrate_rate_limiting():
    """Demonstrate rate limiting capabilities."""
    logger.info("=== Rate Limiting Demo ===")
    
    from devsync_ai.core.rate_limiter import rate_limiter, RequestPriority
    
    await rate_limiter.start()
    
    try:
        # Test rate limiting for different endpoints
        endpoints = ["github_api", "jira_api", "slack_api"]
        
        for endpoint in endpoints:
            logger.info(f"Testing rate limiting for {endpoint}...")
            
            allowed_count = 0
            throttled_count = 0
            
            # Make rapid requests
            for i in range(10):
                result = await rate_limiter.check_rate_limit(
                    "demo_client", endpoint, RequestPriority.NORMAL, "demo_team"
                )
                
                if result.allowed:
                    allowed_count += 1
                else:
                    throttled_count += 1
                
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            logger.info(f"  {endpoint}: {allowed_count} allowed, {throttled_count} throttled")
        
        # Test priority handling
        logger.info("Testing priority handling...")
        
        high_priority_result = await rate_limiter.check_rate_limit(
            "demo_client", "github_api", RequestPriority.HIGH, "demo_team"
        )
        
        low_priority_result = await rate_limiter.check_rate_limit(
            "demo_client", "github_api", RequestPriority.LOW, "demo_team"
        )
        
        logger.info(f"  High priority allowed: {high_priority_result.allowed}")
        logger.info(f"  Low priority allowed: {low_priority_result.allowed}")
        
        # Get rate limiting statistics
        stats = rate_limiter.get_rate_limit_stats()
        logger.info(f"Rate Limiting Stats:")
        logger.info(f"  Total requests: {stats['overall']['total_requests']}")
        logger.info(f"  Throttle rate: {stats['overall']['throttle_rate_percent']:.1f}%")
        
    finally:
        await rate_limiter.stop()


async def demonstrate_memory_optimization():
    """Demonstrate memory optimization capabilities."""
    logger.info("=== Memory Optimization Demo ===")
    
    from devsync_ai.core.memory_optimizer import memory_optimizer
    
    await memory_optimizer.start_monitoring()
    
    try:
        # Test object pooling
        logger.info("Testing object pooling...")
        
        # Acquire and release objects from pools
        objects = []
        for i in range(20):
            obj = memory_optimizer.acquire_object("dict")
            obj[f"key_{i}"] = f"value_{i}"
            objects.append(obj)
        
        # Release half the objects
        for i in range(0, 10):
            memory_optimizer.release_object(objects[i], "dict")
        
        # Test object tracking
        logger.info("Testing object tracking...")
        
        test_objects = []
        for i in range(5):
            obj = {"test_data": f"data_{i}"}
            memory_optimizer.track_object(obj, "demo_objects")
            test_objects.append(obj)
        
        tracked_count = memory_optimizer.get_tracked_object_count("demo_objects")
        logger.info(f"Tracking {tracked_count} demo objects")
        
        # Test data structure optimization
        logger.info("Testing data structure optimization...")
        
        test_dict = {"a": 1, "b": 2, "c": 3}
        optimized_dict = memory_optimizer.optimize_data_structure(test_dict)
        
        test_list = [1, 2, 3, 4, 5]
        optimized_list = memory_optimizer.optimize_data_structure(test_list)
        
        logger.info(f"Dict optimization: {type(test_dict).__name__} -> {type(optimized_dict).__name__}")
        logger.info(f"List optimization: {type(test_list).__name__} -> {type(optimized_list).__name__}")
        
        # Get memory statistics
        stats = memory_optimizer.get_memory_stats()
        if stats:
            current = stats.get("current", {})
            logger.info(f"Memory Stats:")
            logger.info(f"  Memory usage: {current.get('memory_percent', 0):.1f}%")
            logger.info(f"  Process memory: {current.get('process_memory_mb', 0):.1f} MB")
        
        # Get optimization suggestions
        suggestions = memory_optimizer.suggest_optimizations()
        if suggestions:
            logger.info(f"Optimization suggestions:")
            for suggestion in suggestions[:3]:  # Show first 3
                logger.info(f"  - {suggestion}")
        
    finally:
        await memory_optimizer.stop_monitoring()


async def demonstrate_performance_benchmarking():
    """Demonstrate performance benchmarking capabilities."""
    logger.info("=== Performance Benchmarking Demo ===")
    
    from devsync_ai.analytics.performance_benchmarker import (
        performance_benchmarker, BenchmarkConfig, BenchmarkType
    )
    
    await performance_benchmarker.start_monitoring()
    
    try:
        # Run different types of benchmarks
        benchmark_configs = [
            BenchmarkConfig(
                name="demo_api_benchmark",
                benchmark_type=BenchmarkType.API_RESPONSE_TIME,
                iterations=5,
                warmup_iterations=1,
                timeout_seconds=30
            ),
            BenchmarkConfig(
                name="demo_memory_benchmark",
                benchmark_type=BenchmarkType.MEMORY_USAGE,
                iterations=3,
                timeout_seconds=30
            ),
            BenchmarkConfig(
                name="demo_throughput_benchmark",
                benchmark_type=BenchmarkType.THROUGHPUT,
                iterations=3,
                concurrent_users=5,
                timeout_seconds=30
            )
        ]
        
        for config in benchmark_configs:
            logger.info(f"Running benchmark: {config.name}")
            
            result = await performance_benchmarker.run_benchmark(config)
            
            logger.info(f"  Status: {result.status.value}")
            if result.mean_time:
                logger.info(f"  Mean time: {result.mean_time:.3f}s")
            if result.throughput:
                logger.info(f"  Throughput: {result.throughput:.2f} ops/sec")
            if result.error_rate:
                logger.info(f"  Error rate: {result.error_rate:.1f}%")
        
        # Get benchmark summary
        summary = performance_benchmarker.get_benchmark_summary()
        logger.info(f"Benchmark Summary:")
        logger.info(f"  Total benchmarks: {summary['total_benchmarks']}")
        logger.info(f"  Completed: {summary['completed_benchmarks']}")
        logger.info(f"  Failed: {summary['failed_benchmarks']}")
        
    finally:
        await performance_benchmarker.stop_monitoring()


async def demonstrate_capacity_planning():
    """Demonstrate capacity planning capabilities."""
    logger.info("=== Capacity Planning Demo ===")
    
    from devsync_ai.core.capacity_planner import capacity_planner, ResourceType
    from devsync_ai.core.capacity_planner import ResourceMetric
    
    await capacity_planner.start_planning()
    
    try:
        # Simulate resource metrics over time
        logger.info("Simulating resource utilization data...")
        
        # Add CPU metrics with increasing trend
        for i in range(20):
            utilization = 40 + (i * 2) + (i % 3)  # Trending upward with some variation
            metric = ResourceMetric(
                resource_type=ResourceType.CPU,
                current_usage=utilization,
                capacity=100.0,
                utilization_percent=utilization,
                timestamp=datetime.utcnow() - timedelta(minutes=20-i)
            )
            capacity_planner.resource_metrics[ResourceType.CPU].append(metric)
        
        # Add memory metrics with seasonal pattern
        for i in range(20):
            base_usage = 50
            seasonal = 10 * (1 + 0.5 * (i % 4))  # Seasonal variation
            utilization = base_usage + seasonal
            metric = ResourceMetric(
                resource_type=ResourceType.MEMORY,
                current_usage=utilization,
                capacity=100.0,
                utilization_percent=utilization,
                timestamp=datetime.utcnow() - timedelta(minutes=20-i)
            )
            capacity_planner.resource_metrics[ResourceType.MEMORY].append(metric)
        
        # Generate capacity forecasts
        logger.info("Generating capacity forecasts...")
        await capacity_planner._generate_capacity_forecasts()
        
        # Check for scaling recommendations
        logger.info("Analyzing scaling needs...")
        
        for resource_type, metrics in capacity_planner.resource_metrics.items():
            if len(metrics) >= 10:
                recommendation = await capacity_planner._analyze_scaling_need(resource_type, metrics)
                if recommendation:
                    logger.info(f"Scaling recommendation for {resource_type.value}:")
                    logger.info(f"  Direction: {recommendation.scaling_direction.value}")
                    logger.info(f"  Urgency: {recommendation.urgency}")
                    logger.info(f"  Reasoning: {recommendation.reasoning}")
        
        # Get capacity summary
        summary = capacity_planner.get_capacity_summary()
        logger.info(f"Capacity Summary:")
        
        current_util = summary.get("current_utilization", {})
        for resource, metrics in current_util.items():
            logger.info(f"  {resource}: {metrics['utilization_percent']:.1f}% utilized")
        
        logger.info(f"  Active alerts: {summary['active_alerts']}")
        logger.info(f"  Scaling actions: {summary['scaling_history']}")
        
    finally:
        await capacity_planner.stop_planning()


async def demonstrate_integrated_system():
    """Demonstrate the integrated performance optimization system."""
    logger.info("=== Integrated Performance System Demo ===")
    
    from devsync_ai.core.performance_integration import performance_integration, PerformanceConfiguration
    
    # Configure the system
    config = PerformanceConfiguration(
        monitoring_enabled=True,
        query_optimization_enabled=True,
        load_balancing_enabled=True,
        rate_limiting_enabled=True,
        memory_optimization_enabled=True,
        benchmarking_enabled=True,
        capacity_planning_enabled=True,
        optimization_check_interval_minutes=1,  # Faster for demo
        benchmark_interval_hours=1,
        capacity_review_interval_hours=1
    )
    
    performance_integration.config = config
    
    # Initialize the integrated system
    await performance_integration.initialize()
    
    try:
        logger.info("Performance optimization system initialized")
        
        # Wait for system to collect some data
        await asyncio.sleep(5)
        
        # Get performance status
        status = performance_integration.get_performance_status()
        
        logger.info("System Status:")
        logger.info(f"  Active components: {sum(status['component_status'].values())}")
        
        # Trigger manual optimization
        logger.info("Triggering manual optimization...")
        await performance_integration.trigger_optimization("memory")
        
        # Wait a bit more
        await asyncio.sleep(3)
        
        # Get updated status
        final_status = performance_integration.get_performance_status()
        
        if final_status.get("performance_summary"):
            system_health = final_status["performance_summary"].get("system_health", {})
            logger.info(f"Final System Health: {system_health.get('status', 'unknown')}")
            
            recommendations = final_status["performance_summary"].get("optimization_recommendations", [])
            if recommendations:
                logger.info("Optimization Recommendations:")
                for rec in recommendations[:3]:  # Show first 3
                    logger.info(f"  - {rec}")
        
    finally:
        await performance_integration.shutdown()


async def main():
    """Run all performance optimization demonstrations."""
    logger.info("Starting Performance Optimization System Demo")
    logger.info("=" * 60)
    
    demos = [
        demonstrate_performance_monitoring,
        demonstrate_query_optimization,
        demonstrate_load_balancing,
        demonstrate_rate_limiting,
        demonstrate_memory_optimization,
        demonstrate_performance_benchmarking,
        demonstrate_capacity_planning,
        demonstrate_integrated_system
    ]
    
    for demo in demos:
        try:
            await demo()
            logger.info("")  # Add spacing between demos
        except Exception as e:
            logger.error(f"Demo {demo.__name__} failed: {e}")
            logger.info("")
    
    logger.info("Performance Optimization System Demo Complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())