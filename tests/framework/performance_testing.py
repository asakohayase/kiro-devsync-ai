"""
Performance testing utilities for JIRA to Slack Agent Hooks.
"""

import asyncio
import time
import statistics
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import os
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
from concurrent.futures import ThreadPoolExecutor
import json

from tests.framework.webhook_simulator import JiraWebhookSimulator, MockDataGenerator


@dataclass
class PerformanceMetrics:
    """Performance metrics for load testing."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    requests_per_second: float
    total_duration_seconds: float
    memory_usage_mb: float
    cpu_usage_percent: float
    errors: List[str]


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    total_requests: int = 100
    concurrent_users: int = 10
    ramp_up_time_seconds: int = 10
    test_duration_seconds: Optional[int] = None
    request_delay_ms: int = 0
    event_types: List[str] = None
    
    def __post_init__(self):
        if self.event_types is None:
            self.event_types = ["issue_updated", "issue_assigned", "issue_commented"]


class PerformanceTestRunner:
    """Runs performance and load tests for the hook system."""
    
    def __init__(self):
        self.webhook_simulator = JiraWebhookSimulator()
        self.mock_generator = MockDataGenerator()
        if PSUTIL_AVAILABLE:
            self.process = psutil.Process(os.getpid())
        else:
            self.process = None
    
    async def run_load_test(
        self,
        test_function: Callable,
        config: LoadTestConfig
    ) -> PerformanceMetrics:
        """Run a load test with the specified configuration."""
        print(f"Starting load test with {config.total_requests} requests, {config.concurrent_users} concurrent users")
        
        # Record initial system state
        if self.process:
            initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            initial_cpu = self.process.cpu_percent()
        else:
            initial_memory = 0
            initial_cpu = 0
        
        start_time = time.time()
        response_times = []
        errors = []
        successful_requests = 0
        failed_requests = 0
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(config.concurrent_users)
        
        async def execute_request(request_id: int) -> Dict[str, Any]:
            """Execute a single request with timing."""
            async with semaphore:
                request_start = time.time()
                
                try:
                    # Add ramp-up delay
                    if config.ramp_up_time_seconds > 0:
                        delay = (request_id / config.total_requests) * config.ramp_up_time_seconds
                        await asyncio.sleep(delay)
                    
                    # Add request delay if specified
                    if config.request_delay_ms > 0:
                        await asyncio.sleep(config.request_delay_ms / 1000)
                    
                    # Execute the test function
                    result = await test_function(request_id)
                    
                    request_end = time.time()
                    response_time = (request_end - request_start) * 1000  # ms
                    
                    return {
                        "success": True,
                        "response_time_ms": response_time,
                        "result": result,
                        "error": None
                    }
                    
                except Exception as e:
                    request_end = time.time()
                    response_time = (request_end - request_start) * 1000  # ms
                    
                    return {
                        "success": False,
                        "response_time_ms": response_time,
                        "result": None,
                        "error": str(e)
                    }
        
        # Execute all requests
        tasks = [execute_request(i) for i in range(config.total_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Process results
        for result in results:
            if isinstance(result, dict):
                response_times.append(result["response_time_ms"])
                if result["success"]:
                    successful_requests += 1
                else:
                    failed_requests += 1
                    if result["error"]:
                        errors.append(result["error"])
            else:
                failed_requests += 1
                errors.append(str(result))
        
        # Calculate final system state
        if self.process:
            final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            final_cpu = self.process.cpu_percent()
        else:
            final_memory = initial_memory
            final_cpu = initial_cpu
        
        # Calculate metrics
        success_rate = (successful_requests / config.total_requests) * 100 if config.total_requests > 0 else 0
        avg_response_time = statistics.mean(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # Calculate percentiles
        sorted_times = sorted(response_times) if response_times else [0]
        p95_response_time = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
        p99_response_time = sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0
        
        requests_per_second = config.total_requests / total_duration if total_duration > 0 else 0
        
        return PerformanceMetrics(
            total_requests=config.total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=success_rate,
            avg_response_time_ms=avg_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            requests_per_second=requests_per_second,
            total_duration_seconds=total_duration,
            memory_usage_mb=final_memory - initial_memory,
            cpu_usage_percent=final_cpu,
            errors=errors[:10]  # Limit to first 10 errors
        )
    
    async def webhook_processing_load_test(self, config: LoadTestConfig) -> PerformanceMetrics:
        """Load test for webhook processing."""
        async def process_webhook(request_id: int):
            """Process a single webhook event."""
            event_type = config.event_types[request_id % len(config.event_types)]
            webhook_event = self.webhook_simulator.generate_webhook_event(
                event_type,
                **{
                    "issue.id": f"load-{request_id}",
                    "issue.key": f"LOAD-{request_id}",
                    "issue.fields.summary": f"Load Test Issue {request_id}"
                }
            )
            
            # Simulate processing time
            await asyncio.sleep(0.01)  # 10ms processing time
            
            return {"processed": True, "event_id": request_id}
        
        return await self.run_load_test(process_webhook, config)
    
    async def hook_execution_load_test(self, config: LoadTestConfig) -> PerformanceMetrics:
        """Load test for hook execution."""
        async def execute_hook(request_id: int):
            """Execute a single hook."""
            enriched_event = self.mock_generator.create_enriched_event(
                event_type=config.event_types[request_id % len(config.event_types)]
            )
            
            # Simulate hook execution
            await asyncio.sleep(0.05)  # 50ms execution time
            
            return {
                "hook_executed": True,
                "event_id": request_id,
                "event_type": enriched_event.event_type
            }
        
        return await self.run_load_test(execute_hook, config)
    
    async def notification_delivery_load_test(self, config: LoadTestConfig) -> PerformanceMetrics:
        """Load test for notification delivery."""
        async def send_notification(request_id: int):
            """Send a single notification."""
            # Simulate notification formatting and sending
            await asyncio.sleep(0.02)  # 20ms for formatting
            await asyncio.sleep(0.03)  # 30ms for API call
            
            return {
                "notification_sent": True,
                "message_id": f"msg-{request_id}",
                "timestamp": datetime.now().isoformat()
            }
        
        return await self.run_load_test(send_notification, config)
    
    async def end_to_end_load_test(self, config: LoadTestConfig) -> PerformanceMetrics:
        """End-to-end load test from webhook to notification."""
        async def process_end_to_end(request_id: int):
            """Process complete end-to-end flow."""
            # Generate webhook event
            event_type = config.event_types[request_id % len(config.event_types)]
            webhook_event = self.webhook_simulator.generate_webhook_event(event_type)
            
            # Simulate complete processing pipeline
            await asyncio.sleep(0.01)  # Webhook processing
            await asyncio.sleep(0.02)  # Event classification
            await asyncio.sleep(0.01)  # Rule evaluation
            await asyncio.sleep(0.05)  # Hook execution
            await asyncio.sleep(0.03)  # Notification formatting
            await asyncio.sleep(0.03)  # Notification sending
            
            return {
                "end_to_end_complete": True,
                "event_id": request_id,
                "processing_steps": 6,
                "total_time_ms": 150  # Simulated total time
            }
        
        return await self.run_load_test(process_end_to_end, config)
    
    def generate_performance_report(self, metrics: PerformanceMetrics) -> str:
        """Generate a formatted performance report."""
        report = f"""
Performance Test Report
=======================

Test Summary:
- Total Requests: {metrics.total_requests}
- Successful Requests: {metrics.successful_requests}
- Failed Requests: {metrics.failed_requests}
- Success Rate: {metrics.success_rate:.2f}%

Response Times:
- Average: {metrics.avg_response_time_ms:.2f}ms
- Minimum: {metrics.min_response_time_ms:.2f}ms
- Maximum: {metrics.max_response_time_ms:.2f}ms
- 95th Percentile: {metrics.p95_response_time_ms:.2f}ms
- 99th Percentile: {metrics.p99_response_time_ms:.2f}ms

Throughput:
- Requests per Second: {metrics.requests_per_second:.2f}
- Total Duration: {metrics.total_duration_seconds:.2f}s

Resource Usage:
- Memory Usage: {metrics.memory_usage_mb:.2f}MB
- CPU Usage: {metrics.cpu_usage_percent:.2f}%

Errors ({len(metrics.errors)} total):
"""
        
        for i, error in enumerate(metrics.errors[:5], 1):
            report += f"  {i}. {error}\n"
        
        if len(metrics.errors) > 5:
            report += f"  ... and {len(metrics.errors) - 5} more errors\n"
        
        return report
    
    def save_metrics_to_file(self, metrics: PerformanceMetrics, filename: str):
        """Save performance metrics to a JSON file."""
        metrics_dict = {
            "timestamp": datetime.now().isoformat(),
            "total_requests": metrics.total_requests,
            "successful_requests": metrics.successful_requests,
            "failed_requests": metrics.failed_requests,
            "success_rate": metrics.success_rate,
            "avg_response_time_ms": metrics.avg_response_time_ms,
            "min_response_time_ms": metrics.min_response_time_ms,
            "max_response_time_ms": metrics.max_response_time_ms,
            "p95_response_time_ms": metrics.p95_response_time_ms,
            "p99_response_time_ms": metrics.p99_response_time_ms,
            "requests_per_second": metrics.requests_per_second,
            "total_duration_seconds": metrics.total_duration_seconds,
            "memory_usage_mb": metrics.memory_usage_mb,
            "cpu_usage_percent": metrics.cpu_usage_percent,
            "errors": metrics.errors
        }
        
        with open(filename, 'w') as f:
            json.dump(metrics_dict, f, indent=2)


class StressTestRunner:
    """Runs stress tests to find system limits."""
    
    def __init__(self):
        self.performance_runner = PerformanceTestRunner()
    
    async def find_breaking_point(
        self,
        test_function: Callable,
        initial_load: int = 10,
        max_load: int = 1000,
        step_size: int = 10,
        success_threshold: float = 95.0
    ) -> Dict[str, Any]:
        """Find the breaking point of the system."""
        results = []
        breaking_point = None
        
        current_load = initial_load
        
        while current_load <= max_load:
            print(f"Testing with {current_load} concurrent requests...")
            
            config = LoadTestConfig(
                total_requests=current_load,
                concurrent_users=min(current_load, 50),  # Cap concurrent users
                ramp_up_time_seconds=5
            )
            
            metrics = await self.performance_runner.run_load_test(test_function, config)
            
            results.append({
                "load": current_load,
                "success_rate": metrics.success_rate,
                "avg_response_time_ms": metrics.avg_response_time_ms,
                "requests_per_second": metrics.requests_per_second
            })
            
            # Check if we've hit the breaking point
            if metrics.success_rate < success_threshold:
                breaking_point = current_load
                print(f"Breaking point found at {current_load} requests (success rate: {metrics.success_rate:.2f}%)")
                break
            
            current_load += step_size
        
        return {
            "breaking_point": breaking_point,
            "max_tested_load": current_load - step_size,
            "results": results,
            "success_threshold": success_threshold
        }
    
    async def memory_leak_test(
        self,
        test_function: Callable,
        iterations: int = 10,
        requests_per_iteration: int = 100
    ) -> Dict[str, Any]:
        """Test for memory leaks over multiple iterations."""
        memory_usage = []
        if PSUTIL_AVAILABLE:
            process = psutil.Process(os.getpid())
        else:
            process = None
        
        for i in range(iterations):
            print(f"Memory leak test iteration {i + 1}/{iterations}")
            
            # Record memory before test
            if process:
                memory_before = process.memory_info().rss / 1024 / 1024  # MB
            else:
                memory_before = 0
            
            # Run test
            config = LoadTestConfig(
                total_requests=requests_per_iteration,
                concurrent_users=10
            )
            
            await self.performance_runner.run_load_test(test_function, config)
            
            # Record memory after test
            if process:
                memory_after = process.memory_info().rss / 1024 / 1024  # MB
            else:
                memory_after = memory_before
            
            memory_usage.append({
                "iteration": i + 1,
                "memory_before_mb": memory_before,
                "memory_after_mb": memory_after,
                "memory_growth_mb": memory_after - memory_before
            })
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Small delay between iterations
            await asyncio.sleep(1)
        
        # Analyze memory growth trend
        total_growth = memory_usage[-1]["memory_after_mb"] - memory_usage[0]["memory_before_mb"]
        avg_growth_per_iteration = total_growth / iterations
        
        return {
            "total_memory_growth_mb": total_growth,
            "avg_growth_per_iteration_mb": avg_growth_per_iteration,
            "memory_usage_by_iteration": memory_usage,
            "potential_memory_leak": avg_growth_per_iteration > 5.0  # Flag if growing > 5MB per iteration
        }