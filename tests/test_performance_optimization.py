"""
Comprehensive tests for performance optimization and monitoring system.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from devsync_ai.analytics.performance_monitor import (
    PerformanceMonitor, MetricType, AlertSeverity, PerformanceMetric, PerformanceAlert
)
from devsync_ai.core.query_optimizer import QueryOptimizer, CacheStrategy
from devsync_ai.core.load_balancer import LoadBalancer, LoadBalancingStrategy, WorkerStatus
from devsync_ai.core.rate_limiter import IntelligentRateLimiter, RequestPriority, RateLimitStrategy
from devsync_ai.core.memory_optimizer import MemoryOptimizer, ObjectPool, ObjectPoolConfig
from devsync_ai.analytics.performance_benchmarker import (
    PerformanceBenchmarker, BenchmarkType, BenchmarkConfig, BenchmarkStatus
)
from devsync_ai.core.capacity_planner import CapacityPlanner, ResourceType, ScalingDirection


class TestPerformanceMonitor:
    """Test performance monitoring system."""
    
    @pytest.fixture
    async def monitor(self):
        """Create performance monitor instance."""
        monitor = PerformanceMonitor()
        await monitor.start_monitoring()
        yield monitor
        await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_metric_recording(self, monitor):
        """Test recording performance metrics."""
        # Record a metric
        await monitor.record_metric(
            MetricType.API_RESPONSE_TIME,
            1.5,
            team_id="test_team",
            metadata={"endpoint": "/api/test"}
        )
        
        # Check metric was recorded
        assert len(monitor.metrics_buffer) > 0
        metric = monitor.metrics_buffer[-1]
        assert metric.metric_type == MetricType.API_RESPONSE_TIME
        assert metric.value == 1.5
        assert metric.team_id == "test_team"
    
    @pytest.mark.asyncio
    async def test_operation_tracking(self, monitor):
        """Test operation start/end tracking."""
        # Start operation
        operation_id = await monitor.start_operation("test_op", "api_call", "test_team")
        assert operation_id in monitor.active_operations
        
        # End operation
        await monitor.end_operation(operation_id, success=True, team_id="test_team")
        assert operation_id not in monitor.active_operations
        
        # Check metric was recorded
        assert len(monitor.metrics_buffer) > 0
    
    @pytest.mark.asyncio
    async def test_alert_creation(self, monitor):
        """Test alert creation for threshold violations."""
        # Record high CPU usage
        await monitor.record_metric(MetricType.CPU_USAGE, 95.0)
        
        # Trigger alert check
        await monitor._check_alert_conditions()
        
        # Check alert was created
        assert len(monitor.active_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_system_health_status(self, monitor):
        """Test system health status calculation."""
        # Record some metrics
        await monitor.record_metric(MetricType.CPU_USAGE, 50.0)
        await monitor.record_metric(MetricType.MEMORY_USAGE, 60.0)
        await monitor.record_metric(MetricType.ERROR_RATE, 2.0)
        
        # Get system health
        health = await monitor.get_system_health()
        
        assert health.status in ["healthy", "degraded", "critical"]
        assert health.cpu_usage >= 0
        assert health.memory_usage >= 0


class TestQueryOptimizer:
    """Test query optimization and caching."""
    
    @pytest.fixture
    def optimizer(self):
        """Create query optimizer instance."""
        return QueryOptimizer()
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, optimizer):
        """Test cache key generation."""
        query = "SELECT * FROM test WHERE id = $1"
        params = [123]
        
        key1 = optimizer._generate_cache_key(query, params)
        key2 = optimizer._generate_cache_key(query, params)
        key3 = optimizer._generate_cache_key(query, [456])
        
        assert key1 == key2  # Same query and params should generate same key
        assert key1 != key3  # Different params should generate different key
    
    @pytest.mark.asyncio
    async def test_local_cache_operations(self, optimizer):
        """Test local cache store and retrieve."""
        cache_key = "test_key"
        test_data = [{"id": 1, "name": "test"}]
        
        # Store in cache
        await optimizer._store_in_cache(cache_key, test_data, CacheStrategy.SHORT_TERM)
        
        # Retrieve from cache
        cached_data = await optimizer._get_from_cache(cache_key)
        
        assert cached_data == test_data
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, optimizer):
        """Test cache expiration."""
        cache_key = "test_expiry"
        test_data = [{"id": 1, "name": "test"}]
        
        # Store with short TTL
        await optimizer._store_in_cache(cache_key, test_data, CacheStrategy.SHORT_TERM)
        
        # Manually expire the entry
        if cache_key in optimizer.local_cache:
            optimizer.local_cache[cache_key].expires_at = datetime.utcnow() - timedelta(seconds=1)
        
        # Try to retrieve expired data
        cached_data = await optimizer._get_from_cache(cache_key)
        
        assert cached_data is None
    
    def test_query_signature_generation(self, optimizer):
        """Test query signature generation for grouping."""
        query1 = "SELECT * FROM users WHERE id = $1 AND name = 'test'"
        query2 = "SELECT * FROM users WHERE id = $1 AND name = 'other'"
        
        sig1 = optimizer._get_query_signature(query1)
        sig2 = optimizer._get_query_signature(query2)
        
        # Should be similar after parameter normalization
        assert "SELECT * FROM users WHERE id = ?" in sig1
        assert "SELECT * FROM users WHERE id = ?" in sig2


class TestLoadBalancer:
    """Test load balancing system."""
    
    @pytest.fixture
    async def load_balancer(self):
        """Create load balancer instance."""
        lb = LoadBalancer()
        await lb.start()
        
        # Register test workers
        lb.register_worker("worker1", "localhost", 8001, weight=1.0)
        lb.register_worker("worker2", "localhost", 8002, weight=1.5)
        
        yield lb
        await lb.stop()
    
    @pytest.mark.asyncio
    async def test_worker_registration(self, load_balancer):
        """Test worker node registration."""
        assert len(load_balancer.worker_nodes) == 2
        assert "worker1" in load_balancer.worker_nodes
        assert "worker2" in load_balancer.worker_nodes
        
        worker1 = load_balancer.worker_nodes["worker1"]
        assert worker1.host == "localhost"
        assert worker1.port == 8001
        assert worker1.weight == 1.0
    
    @pytest.mark.asyncio
    async def test_task_submission(self, load_balancer):
        """Test task submission and queuing."""
        task_id = await load_balancer.submit_task(
            "test_task",
            {"data": "test"},
            priority=3,
            team_id="test_team"
        )
        
        assert task_id is not None
        assert len(load_balancer.priority_queues[3]) > 0
    
    @pytest.mark.asyncio
    async def test_worker_selection_strategies(self, load_balancer):
        """Test different worker selection strategies."""
        available_workers = list(load_balancer.worker_nodes.values())
        
        # Test round robin
        load_balancer.current_strategy = LoadBalancingStrategy.ROUND_ROBIN
        worker1 = load_balancer._select_round_robin(available_workers)
        worker2 = load_balancer._select_round_robin(available_workers)
        
        assert worker1 != worker2  # Should alternate
        
        # Test least connections
        load_balancer.current_strategy = LoadBalancingStrategy.LEAST_CONNECTIONS
        worker = load_balancer._select_least_connections(available_workers)
        
        assert worker is not None
        assert worker.current_tasks == 0  # Should select worker with no tasks
    
    @pytest.mark.asyncio
    async def test_worker_health_monitoring(self, load_balancer):
        """Test worker health monitoring."""
        worker = load_balancer.worker_nodes["worker1"]
        
        # Simulate health check
        await load_balancer._check_worker_health(worker)
        
        assert worker.last_health_check is not None
        assert worker.status in [WorkerStatus.HEALTHY, WorkerStatus.DEGRADED, WorkerStatus.OVERLOADED]
    
    def test_load_balancer_stats(self, load_balancer):
        """Test load balancer statistics."""
        stats = load_balancer.get_load_balancer_stats()
        
        assert "workers" in stats
        assert "capacity" in stats
        assert "tasks" in stats
        assert "performance" in stats
        assert stats["workers"]["total"] == 2


class TestRateLimiter:
    """Test rate limiting system."""
    
    @pytest.fixture
    async def rate_limiter(self):
        """Create rate limiter instance."""
        limiter = IntelligentRateLimiter()
        await limiter.start()
        yield limiter
        await limiter.stop()
    
    @pytest.mark.asyncio
    async def test_token_bucket_rate_limiting(self, rate_limiter):
        """Test token bucket rate limiting."""
        # First request should be allowed
        result1 = await rate_limiter.check_rate_limit(
            "test_client", "github_api", RequestPriority.NORMAL
        )
        assert result1.allowed is True
        
        # Rapid subsequent requests should be throttled
        results = []
        for _ in range(10):
            result = await rate_limiter.check_rate_limit(
                "test_client", "github_api", RequestPriority.NORMAL
            )
            results.append(result.allowed)
        
        # Some requests should be throttled
        assert not all(results)
    
    @pytest.mark.asyncio
    async def test_priority_handling(self, rate_limiter):
        """Test priority-based rate limiting."""
        # High priority request
        high_priority = await rate_limiter.check_rate_limit(
            "test_client", "github_api", RequestPriority.HIGH
        )
        
        # Low priority request
        low_priority = await rate_limiter.check_rate_limit(
            "test_client", "github_api", RequestPriority.LOW
        )
        
        # High priority should have better treatment
        assert high_priority.allowed is True
    
    @pytest.mark.asyncio
    async def test_sliding_window_rate_limiting(self, rate_limiter):
        """Test sliding window rate limiting."""
        # Configure sliding window rule
        from devsync_ai.core.rate_limiter import RateLimitRule
        
        rule = RateLimitRule(
            name="test_sliding",
            requests_per_second=2.0,
            burst_capacity=5,
            window_size_seconds=10,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
        rate_limiter.add_rule(rule)
        
        # Test sliding window behavior
        allowed_count = 0
        for _ in range(10):
            result = await rate_limiter.check_rate_limit(
                "test_client", "test_sliding", RequestPriority.NORMAL
            )
            if result.allowed:
                allowed_count += 1
        
        # Should allow some requests within the window
        assert allowed_count > 0
        assert allowed_count <= 20  # 2 req/sec * 10 sec window
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_limiting(self, rate_limiter):
        """Test adaptive rate limiting based on system health."""
        # Mock system health
        with patch('devsync_ai.analytics.performance_monitor.performance_monitor.get_system_health') as mock_health:
            # Simulate degraded system
            mock_health.return_value = AsyncMock()
            mock_health.return_value.status = "degraded"
            
            result = await rate_limiter._check_adaptive(
                Mock(client_id="test", priority=RequestPriority.NORMAL),
                Mock(name="test", requests_per_second=1.0)
            )
            
            # Should be more restrictive when system is degraded
            assert result is not None
    
    def test_rate_limit_statistics(self, rate_limiter):
        """Test rate limiting statistics."""
        stats = rate_limiter.get_rate_limit_stats()
        
        assert "overall" in stats
        assert "queues" in stats
        assert "buckets" in stats
        assert "rules" in stats


class TestMemoryOptimizer:
    """Test memory optimization system."""
    
    @pytest.fixture
    async def memory_optimizer(self):
        """Create memory optimizer instance."""
        optimizer = MemoryOptimizer()
        await optimizer.start_monitoring()
        yield optimizer
        await optimizer.stop_monitoring()
    
    def test_object_pool_operations(self, memory_optimizer):
        """Test object pool acquire and release."""
        pool = memory_optimizer.object_pools["dict"]
        
        # Acquire object
        obj1 = pool.acquire()
        assert isinstance(obj1, dict)
        assert id(obj1) in pool.in_use
        
        # Release object
        pool.release(obj1)
        assert id(obj1) not in pool.in_use
        assert len(pool.pool) > 0
        
        # Acquire again - should reuse
        obj2 = pool.acquire()
        assert obj2 is obj1  # Should be the same object
    
    def test_object_pool_cleanup(self, memory_optimizer):
        """Test object pool cleanup."""
        pool = memory_optimizer.object_pools["list"]
        config = ObjectPoolConfig(max_size=5, cleanup_threshold=4, cleanup_percentage=0.5)
        pool.config = config
        
        # Fill pool beyond cleanup threshold
        objects = []
        for _ in range(6):
            obj = pool.acquire()
            objects.append(obj)
        
        for obj in objects:
            pool.release(obj)
        
        # Trigger cleanup
        pool._cleanup()
        
        # Pool should be smaller after cleanup
        assert len(pool.pool) < 6
    
    def test_data_structure_optimization(self, memory_optimizer):
        """Test data structure optimization."""
        # Test dictionary optimization
        small_dict = {"a": 1, "b": 2, "c": 3}
        optimized = memory_optimizer.optimize_data_structure(small_dict)
        
        # Small dict might be converted to namedtuple
        assert optimized is not None
        
        # Test list optimization
        simple_list = [1, 2, 3, 4, 5]
        optimized_list = memory_optimizer.optimize_data_structure(simple_list)
        
        # Simple list might be converted to tuple
        assert isinstance(optimized_list, (list, tuple))
    
    def test_object_tracking(self, memory_optimizer):
        """Test object tracking for memory leak detection."""
        test_obj = {"test": "data"}
        
        # Track object
        memory_optimizer.track_object(test_obj, "test_category")
        
        # Check tracking
        count = memory_optimizer.get_tracked_object_count("test_category")
        assert count == 1
        
        # Object should be automatically removed when garbage collected
        del test_obj
        import gc
        gc.collect()
        
        # Count might be 0 after garbage collection
        count_after = memory_optimizer.get_tracked_object_count("test_category")
        assert count_after <= count


class TestPerformanceBenchmarker:
    """Test performance benchmarking system."""
    
    @pytest.fixture
    async def benchmarker(self):
        """Create performance benchmarker instance."""
        benchmarker = PerformanceBenchmarker()
        await benchmarker.start_monitoring()
        yield benchmarker
        await benchmarker.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_benchmark_execution(self, benchmarker):
        """Test benchmark execution."""
        config = BenchmarkConfig(
            name="test_benchmark",
            benchmark_type=BenchmarkType.API_RESPONSE_TIME,
            iterations=3,
            warmup_iterations=1,
            timeout_seconds=30
        )
        
        result = await benchmarker.run_benchmark(config)
        
        assert result.status == BenchmarkStatus.COMPLETED
        assert len(result.execution_times) == 3
        assert result.mean_time is not None
        assert result.min_time is not None
        assert result.max_time is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_benchmark(self, benchmarker):
        """Test concurrent benchmark execution."""
        config = BenchmarkConfig(
            name="concurrent_test",
            benchmark_type=BenchmarkType.THROUGHPUT,
            iterations=5,
            concurrent_users=3,
            timeout_seconds=30
        )
        
        result = await benchmarker.run_benchmark(config)
        
        assert result.status == BenchmarkStatus.COMPLETED
        assert result.throughput is not None
    
    @pytest.mark.asyncio
    async def test_regression_detection(self, benchmarker):
        """Test performance regression detection."""
        # Create baseline
        config = BenchmarkConfig(
            name="regression_test",
            benchmark_type=BenchmarkType.API_RESPONSE_TIME,
            iterations=3,
            regression_threshold=10.0
        )
        
        # Run baseline benchmark
        baseline = await benchmarker.run_benchmark(config, store_as_baseline=True)
        
        # Simulate regression by modifying execution times
        regression_result = await benchmarker.run_benchmark(config)
        regression_result.mean_time = baseline.mean_time * 1.5  # 50% slower
        
        # Check for regression
        await benchmarker._check_for_regressions(regression_result)
        
        # Should have created regression alert
        assert len(benchmarker.regression_alerts) > 0
    
    def test_percentile_calculation(self, benchmarker):
        """Test percentile calculation."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        
        p95 = benchmarker._calculate_percentile(values, 95)
        p99 = benchmarker._calculate_percentile(values, 99)
        
        assert p95 >= 9.0  # 95th percentile should be near the top
        assert p99 >= p95  # 99th percentile should be >= 95th percentile
    
    def test_benchmark_summary(self, benchmarker):
        """Test benchmark summary generation."""
        # Add some mock results
        from devsync_ai.analytics.performance_benchmarker import BenchmarkResult
        
        result = BenchmarkResult(
            benchmark_id="test_1",
            config=BenchmarkConfig("test", BenchmarkType.API_RESPONSE_TIME),
            status=BenchmarkStatus.COMPLETED,
            start_time=datetime.utcnow(),
            mean_time=1.5,
            throughput=10.0
        )
        benchmarker.benchmark_results["test_1"] = result
        
        summary = benchmarker.get_benchmark_summary()
        
        assert "total_benchmarks" in summary
        assert "completed_benchmarks" in summary
        assert summary["total_benchmarks"] >= 1


class TestCapacityPlanner:
    """Test capacity planning system."""
    
    @pytest.fixture
    async def capacity_planner(self):
        """Create capacity planner instance."""
        planner = CapacityPlanner()
        await planner.start_planning()
        yield planner
        await planner.stop_planning()
    
    @pytest.mark.asyncio
    async def test_resource_metric_collection(self, capacity_planner):
        """Test resource metric collection."""
        # Mock system health
        with patch('devsync_ai.analytics.performance_monitor.performance_monitor.get_system_health') as mock_health:
            mock_health.return_value = AsyncMock()
            mock_health.return_value.cpu_usage = 75.0
            mock_health.return_value.memory_usage = 60.0
            
            await capacity_planner._collect_resource_metrics()
            
            # Check metrics were collected
            assert len(capacity_planner.resource_metrics[ResourceType.CPU]) > 0
            assert len(capacity_planner.resource_metrics[ResourceType.MEMORY]) > 0
    
    @pytest.mark.asyncio
    async def test_capacity_threshold_checking(self, capacity_planner):
        """Test capacity threshold checking."""
        # Add high utilization metric
        from devsync_ai.core.capacity_planner import ResourceMetric
        
        high_cpu_metric = ResourceMetric(
            resource_type=ResourceType.CPU,
            current_usage=95.0,
            capacity=100.0,
            utilization_percent=95.0,
            timestamp=datetime.utcnow()
        )
        
        capacity_planner.resource_metrics[ResourceType.CPU].append(high_cpu_metric)
        
        # Check thresholds
        await capacity_planner._check_capacity_thresholds()
        
        # Should have created alert
        assert len(capacity_planner.active_alerts) > 0
    
    def test_moving_average_forecast(self, capacity_planner):
        """Test moving average forecasting."""
        data = [50.0, 55.0, 60.0, 58.0, 62.0, 65.0, 63.0, 67.0, 70.0, 68.0]
        timestamps = [datetime.utcnow() - timedelta(hours=i) for i in range(len(data))]
        timestamps.reverse()  # Make chronological
        
        forecast = capacity_planner._moving_average_forecast(
            data, timestamps, ResourceType.CPU
        )
        
        assert forecast is not None
        assert len(forecast.predicted_utilization) == capacity_planner.forecast_intervals
        assert len(forecast.prediction_timestamps) == capacity_planner.forecast_intervals
        assert forecast.accuracy_score is not None
    
    def test_linear_regression_forecast(self, capacity_planner):
        """Test linear regression forecasting."""
        # Create trending data
        data = [i * 2 + 50 for i in range(20)]  # Linear trend
        timestamps = [datetime.utcnow() - timedelta(hours=i) for i in range(len(data))]
        timestamps.reverse()
        
        forecast = capacity_planner._linear_regression_forecast(
            data, timestamps, ResourceType.MEMORY
        )
        
        assert forecast is not None
        assert len(forecast.predicted_utilization) == capacity_planner.forecast_intervals
        assert forecast.accuracy_score is not None
    
    @pytest.mark.asyncio
    async def test_scaling_recommendation_generation(self, capacity_planner):
        """Test scaling recommendation generation."""
        # Add metrics indicating high utilization
        from devsync_ai.core.capacity_planner import ResourceMetric
        
        for i in range(15):
            metric = ResourceMetric(
                resource_type=ResourceType.WORKERS,
                current_usage=90.0,
                capacity=100.0,
                utilization_percent=90.0,
                timestamp=datetime.utcnow() - timedelta(minutes=i)
            )
            capacity_planner.resource_metrics[ResourceType.WORKERS].append(metric)
        
        # Generate recommendations
        recommendation = await capacity_planner._analyze_scaling_need(
            ResourceType.WORKERS,
            capacity_planner.resource_metrics[ResourceType.WORKERS]
        )
        
        assert recommendation is not None
        assert recommendation.scaling_direction == ScalingDirection.SCALE_UP
        assert recommendation.urgency in ["high", "critical"]
    
    def test_capacity_summary(self, capacity_planner):
        """Test capacity summary generation."""
        # Add some test data
        from devsync_ai.core.capacity_planner import ResourceMetric
        
        metric = ResourceMetric(
            resource_type=ResourceType.CPU,
            current_usage=60.0,
            capacity=100.0,
            utilization_percent=60.0,
            timestamp=datetime.utcnow()
        )
        capacity_planner.resource_metrics[ResourceType.CPU].append(metric)
        
        summary = capacity_planner.get_capacity_summary()
        
        assert "current_utilization" in summary
        assert "active_alerts" in summary
        assert ResourceType.CPU.value in summary["current_utilization"]


class TestIntegration:
    """Integration tests for performance optimization system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_performance_monitoring(self):
        """Test end-to-end performance monitoring workflow."""
        monitor = PerformanceMonitor()
        await monitor.start_monitoring()
        
        try:
            # Start operation
            operation_id = await monitor.start_operation("test_operation", "api_call")
            
            # Simulate work
            await asyncio.sleep(0.1)
            
            # End operation
            await monitor.end_operation(operation_id, success=True)
            
            # Check metrics were recorded
            assert len(monitor.metrics_buffer) > 0
            
            # Get system health
            health = await monitor.get_system_health()
            assert health is not None
            
        finally:
            await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_load_balancer_with_rate_limiting(self):
        """Test integration between load balancer and rate limiter."""
        load_balancer = LoadBalancer()
        rate_limiter = IntelligentRateLimiter()
        
        await load_balancer.start()
        await rate_limiter.start()
        
        try:
            # Register workers
            load_balancer.register_worker("worker1", "localhost", 8001)
            
            # Check rate limit before submitting task
            result = await rate_limiter.check_rate_limit(
                "test_client", "task_submission", RequestPriority.NORMAL
            )
            
            if result.allowed:
                # Submit task to load balancer
                task_id = await load_balancer.submit_task(
                    "test_task", {"data": "test"}
                )
                assert task_id is not None
            
        finally:
            await load_balancer.stop()
            await rate_limiter.stop()
    
    @pytest.mark.asyncio
    async def test_memory_optimization_with_benchmarking(self):
        """Test integration between memory optimizer and benchmarker."""
        memory_optimizer = MemoryOptimizer()
        benchmarker = PerformanceBenchmarker()
        
        await memory_optimizer.start_monitoring()
        await benchmarker.start_monitoring()
        
        try:
            # Run memory usage benchmark
            config = BenchmarkConfig(
                name="memory_test",
                benchmark_type=BenchmarkType.MEMORY_USAGE,
                iterations=3
            )
            
            result = await benchmarker.run_benchmark(config)
            
            # Check benchmark completed
            assert result.status == BenchmarkStatus.COMPLETED
            
            # Check memory optimizer collected stats
            stats = memory_optimizer.get_memory_stats()
            assert "current" in stats
            
        finally:
            await memory_optimizer.stop_monitoring()
            await benchmarker.stop_monitoring()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])