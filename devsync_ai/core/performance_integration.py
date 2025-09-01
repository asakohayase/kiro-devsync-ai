"""
Performance optimization integration module that coordinates all performance components.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..analytics.performance_monitor import performance_monitor, MetricType
from ..core.query_optimizer import query_optimizer
from ..core.load_balancer import load_balancer
from ..core.rate_limiter import rate_limiter
from ..core.memory_optimizer import memory_optimizer
from ..analytics.performance_benchmarker import performance_benchmarker, BenchmarkType, BenchmarkConfig
from ..core.capacity_planner import capacity_planner


@dataclass
class PerformanceConfiguration:
    """Configuration for performance optimization system."""
    monitoring_enabled: bool = True
    query_optimization_enabled: bool = True
    load_balancing_enabled: bool = True
    rate_limiting_enabled: bool = True
    memory_optimization_enabled: bool = True
    benchmarking_enabled: bool = True
    capacity_planning_enabled: bool = True
    
    # Performance targets
    max_response_time_ms: float = 2000.0
    max_memory_usage_percent: float = 80.0
    max_cpu_usage_percent: float = 80.0
    target_throughput_rps: float = 100.0
    
    # Optimization intervals
    optimization_check_interval_minutes: int = 5
    benchmark_interval_hours: int = 24
    capacity_review_interval_hours: int = 6


class PerformanceIntegration:
    """
    Central coordinator for all performance optimization components.
    """
    
    def __init__(self, config: Optional[PerformanceConfiguration] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or PerformanceConfiguration()
        
        # Component status tracking
        self.component_status: Dict[str, bool] = {}
        self.last_optimization_check: Optional[datetime] = None
        self.last_benchmark_run: Optional[datetime] = None
        self.last_capacity_review: Optional[datetime] = None
        
        # Performance metrics aggregation
        self.performance_summary: Dict[str, Any] = {}
        
        # Background tasks
        self._coordinator_task: Optional[asyncio.Task] = None
        self._optimization_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize all performance optimization components."""
        self.logger.info("Initializing performance optimization system")
        
        try:
            # Initialize performance monitoring
            if self.config.monitoring_enabled:
                await performance_monitor.start_monitoring()
                self.component_status["performance_monitor"] = True
                self.logger.info("Performance monitoring initialized")
            
            # Initialize query optimizer
            if self.config.query_optimization_enabled:
                await query_optimizer.create_database_indexes()
                self.component_status["query_optimizer"] = True
                self.logger.info("Query optimizer initialized")
            
            # Initialize load balancer
            if self.config.load_balancing_enabled:
                await load_balancer.start()
                self.component_status["load_balancer"] = True
                self.logger.info("Load balancer initialized")
            
            # Initialize rate limiter
            if self.config.rate_limiting_enabled:
                await rate_limiter.start()
                self.component_status["rate_limiter"] = True
                self.logger.info("Rate limiter initialized")
            
            # Initialize memory optimizer
            if self.config.memory_optimization_enabled:
                await memory_optimizer.start_monitoring()
                self.component_status["memory_optimizer"] = True
                self.logger.info("Memory optimizer initialized")
            
            # Initialize performance benchmarker
            if self.config.benchmarking_enabled:
                await performance_benchmarker.start_monitoring()
                self.component_status["performance_benchmarker"] = True
                self.logger.info("Performance benchmarker initialized")
            
            # Initialize capacity planner
            if self.config.capacity_planning_enabled:
                await capacity_planner.start_planning()
                self.component_status["capacity_planner"] = True
                self.logger.info("Capacity planner initialized")
            
            # Start coordination tasks
            self._coordinator_task = asyncio.create_task(self._coordination_loop())
            self._optimization_task = asyncio.create_task(self._optimization_loop())
            
            self.logger.info("Performance optimization system fully initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize performance optimization system: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self):
        """Shutdown all performance optimization components."""
        self.logger.info("Shutting down performance optimization system")
        
        # Cancel background tasks
        if self._coordinator_task:
            self._coordinator_task.cancel()
        if self._optimization_task:
            self._optimization_task.cancel()
        
        try:
            if self._coordinator_task:
                await self._coordinator_task
            if self._optimization_task:
                await self._optimization_task
        except asyncio.CancelledError:
            pass
        
        # Shutdown components
        shutdown_tasks = []
        
        if self.component_status.get("performance_monitor"):
            shutdown_tasks.append(performance_monitor.stop_monitoring())
        
        if self.component_status.get("load_balancer"):
            shutdown_tasks.append(load_balancer.stop())
        
        if self.component_status.get("rate_limiter"):
            shutdown_tasks.append(rate_limiter.stop())
        
        if self.component_status.get("memory_optimizer"):
            shutdown_tasks.append(memory_optimizer.stop_monitoring())
        
        if self.component_status.get("performance_benchmarker"):
            shutdown_tasks.append(performance_benchmarker.stop_monitoring())
        
        if self.component_status.get("capacity_planner"):
            shutdown_tasks.append(capacity_planner.stop_planning())
        
        # Wait for all shutdowns to complete
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        self.component_status.clear()
        self.logger.info("Performance optimization system shutdown complete")
    
    async def _coordination_loop(self):
        """Main coordination loop for performance optimization."""
        try:
            while True:
                await self._update_performance_summary()
                await self._check_component_health()
                await self._coordinate_optimizations()
                await asyncio.sleep(60)  # Run every minute
        except asyncio.CancelledError:
            self.logger.info("Performance coordination loop cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in performance coordination loop: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _optimization_loop(self):
        """Background optimization loop."""
        try:
            while True:
                current_time = datetime.utcnow()
                
                # Check if optimization review is needed
                if (not self.last_optimization_check or 
                    current_time - self.last_optimization_check >= 
                    timedelta(minutes=self.config.optimization_check_interval_minutes)):
                    
                    await self._perform_optimization_review()
                    self.last_optimization_check = current_time
                
                # Check if benchmark run is needed
                if (not self.last_benchmark_run or 
                    current_time - self.last_benchmark_run >= 
                    timedelta(hours=self.config.benchmark_interval_hours)):
                    
                    await self._run_scheduled_benchmarks()
                    self.last_benchmark_run = current_time
                
                # Check if capacity review is needed
                if (not self.last_capacity_review or 
                    current_time - self.last_capacity_review >= 
                    timedelta(hours=self.config.capacity_review_interval_hours)):
                    
                    await self._perform_capacity_review()
                    self.last_capacity_review = current_time
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
        except asyncio.CancelledError:
            self.logger.info("Performance optimization loop cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in performance optimization loop: {e}")
            await asyncio.sleep(600)  # Wait 10 minutes before retrying
    
    async def _update_performance_summary(self):
        """Update aggregated performance summary."""
        try:
            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "system_health": {},
                "component_status": self.component_status.copy(),
                "performance_metrics": {},
                "optimization_recommendations": []
            }
            
            # Get system health
            if self.component_status.get("performance_monitor"):
                system_health = await performance_monitor.get_system_health()
                summary["system_health"] = {
                    "status": system_health.status,
                    "cpu_usage": system_health.cpu_usage,
                    "memory_usage": system_health.memory_usage,
                    "active_operations": system_health.active_operations,
                    "error_rate": system_health.error_rate,
                    "avg_response_time": system_health.avg_response_time
                }
            
            # Get performance metrics
            if self.component_status.get("performance_monitor"):
                perf_summary = await performance_monitor.get_performance_summary()
                summary["performance_metrics"] = perf_summary
            
            # Get load balancer stats
            if self.component_status.get("load_balancer"):
                lb_stats = load_balancer.get_load_balancer_stats()
                summary["load_balancer"] = lb_stats
            
            # Get rate limiter stats
            if self.component_status.get("rate_limiter"):
                rl_stats = rate_limiter.get_rate_limit_stats()
                summary["rate_limiter"] = rl_stats
            
            # Get memory stats
            if self.component_status.get("memory_optimizer"):
                memory_stats = memory_optimizer.get_memory_stats()
                summary["memory_optimizer"] = memory_stats
            
            # Get capacity summary
            if self.component_status.get("capacity_planner"):
                capacity_summary = capacity_planner.get_capacity_summary()
                summary["capacity_planner"] = capacity_summary
            
            self.performance_summary = summary
            
        except Exception as e:
            self.logger.error(f"Error updating performance summary: {e}")
    
    async def _check_component_health(self):
        """Check health of all performance components."""
        try:
            # Check if any components have failed
            failed_components = []
            
            for component, status in self.component_status.items():
                if not status:
                    failed_components.append(component)
            
            if failed_components:
                self.logger.warning(f"Failed performance components detected: {failed_components}")
                
                # Attempt to restart failed components
                for component in failed_components:
                    await self._restart_component(component)
            
        except Exception as e:
            self.logger.error(f"Error checking component health: {e}")
    
    async def _restart_component(self, component_name: str):
        """Restart a failed performance component."""
        try:
            self.logger.info(f"Attempting to restart component: {component_name}")
            
            if component_name == "performance_monitor":
                await performance_monitor.start_monitoring()
            elif component_name == "load_balancer":
                await load_balancer.start()
            elif component_name == "rate_limiter":
                await rate_limiter.start()
            elif component_name == "memory_optimizer":
                await memory_optimizer.start_monitoring()
            elif component_name == "performance_benchmarker":
                await performance_benchmarker.start_monitoring()
            elif component_name == "capacity_planner":
                await capacity_planner.start_planning()
            
            self.component_status[component_name] = True
            self.logger.info(f"Successfully restarted component: {component_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to restart component {component_name}: {e}")
    
    async def _coordinate_optimizations(self):
        """Coordinate optimizations between components."""
        try:
            # Get current system state
            if not self.performance_summary:
                return
            
            system_health = self.performance_summary.get("system_health", {})
            
            # Coordinate memory optimization
            if (system_health.get("memory_usage", 0) > self.config.max_memory_usage_percent and
                self.component_status.get("memory_optimizer")):
                
                # Trigger aggressive memory cleanup
                await memory_optimizer._emergency_cleanup()
                self.logger.info("Triggered emergency memory cleanup due to high usage")
            
            # Coordinate load balancing
            if (system_health.get("avg_response_time", 0) > self.config.max_response_time_ms / 1000 and
                self.component_status.get("load_balancer")):
                
                # Check if scaling is needed
                lb_stats = self.performance_summary.get("load_balancer", {})
                utilization = lb_stats.get("capacity", {}).get("utilization_percent", 0)
                
                if utilization > 80:
                    # Trigger scale up
                    await load_balancer._scale_up()
                    self.logger.info("Triggered load balancer scale up due to high response times")
            
            # Coordinate rate limiting
            if (system_health.get("error_rate", 0) > 10 and
                self.component_status.get("rate_limiter")):
                
                # Make rate limiting more aggressive
                for rule in rate_limiter.rules.values():
                    rule.requests_per_second *= 0.8  # Reduce by 20%
                
                self.logger.info("Made rate limiting more aggressive due to high error rate")
            
        except Exception as e:
            self.logger.error(f"Error coordinating optimizations: {e}")
    
    async def _perform_optimization_review(self):
        """Perform comprehensive optimization review."""
        try:
            self.logger.info("Performing optimization review")
            
            recommendations = []
            
            # Memory optimization recommendations
            if self.component_status.get("memory_optimizer"):
                memory_suggestions = memory_optimizer.suggest_optimizations()
                recommendations.extend([f"Memory: {s}" for s in memory_suggestions])
            
            # Query optimization recommendations
            if self.component_status.get("query_optimizer"):
                cache_stats = await query_optimizer.get_cache_stats()
                hit_rate = cache_stats.get("overall_performance", {}).get("hit_rate_percent", 0)
                
                if hit_rate < 70:
                    recommendations.append("Query: Consider increasing cache TTL or reviewing query patterns")
            
            # Load balancer optimization recommendations
            if self.component_status.get("load_balancer"):
                lb_stats = load_balancer.get_load_balancer_stats()
                avg_response_time = lb_stats.get("performance", {}).get("avg_response_time_ms", 0)
                
                if avg_response_time > self.config.max_response_time_ms:
                    recommendations.append("Load Balancer: Consider adding more workers or optimizing task distribution")
            
            # Store recommendations
            if recommendations:
                self.performance_summary["optimization_recommendations"] = recommendations
                self.logger.info(f"Generated {len(recommendations)} optimization recommendations")
            
        except Exception as e:
            self.logger.error(f"Error performing optimization review: {e}")
    
    async def _run_scheduled_benchmarks(self):
        """Run scheduled performance benchmarks."""
        try:
            if not self.component_status.get("performance_benchmarker"):
                return
            
            self.logger.info("Running scheduled performance benchmarks")
            
            # Run key benchmarks
            benchmark_configs = [
                BenchmarkConfig(
                    name="scheduled_api_response",
                    benchmark_type=BenchmarkType.API_RESPONSE_TIME,
                    iterations=10
                ),
                BenchmarkConfig(
                    name="scheduled_throughput",
                    benchmark_type=BenchmarkType.THROUGHPUT,
                    iterations=5,
                    concurrent_users=10
                ),
                BenchmarkConfig(
                    name="scheduled_memory",
                    benchmark_type=BenchmarkType.MEMORY_USAGE,
                    iterations=5
                )
            ]
            
            for config in benchmark_configs:
                try:
                    result = await performance_benchmarker.run_benchmark(config)
                    self.logger.info(f"Completed benchmark {config.name}: {result.status.value}")
                except Exception as e:
                    self.logger.error(f"Benchmark {config.name} failed: {e}")
            
        except Exception as e:
            self.logger.error(f"Error running scheduled benchmarks: {e}")
    
    async def _perform_capacity_review(self):
        """Perform capacity planning review."""
        try:
            if not self.component_status.get("capacity_planner"):
                return
            
            self.logger.info("Performing capacity review")
            
            # Get capacity summary
            capacity_summary = capacity_planner.get_capacity_summary()
            
            # Check for capacity issues
            current_utilization = capacity_summary.get("current_utilization", {})
            
            for resource, metrics in current_utilization.items():
                utilization = metrics.get("utilization_percent", 0)
                
                if utilization > 80:
                    self.logger.warning(f"High {resource} utilization detected: {utilization:.1f}%")
                elif utilization < 20:
                    self.logger.info(f"Low {resource} utilization detected: {utilization:.1f}% - consider scaling down")
            
        except Exception as e:
            self.logger.error(f"Error performing capacity review: {e}")
    
    def get_performance_status(self) -> Dict[str, Any]:
        """Get comprehensive performance status."""
        return {
            "component_status": self.component_status,
            "configuration": {
                "monitoring_enabled": self.config.monitoring_enabled,
                "query_optimization_enabled": self.config.query_optimization_enabled,
                "load_balancing_enabled": self.config.load_balancing_enabled,
                "rate_limiting_enabled": self.config.rate_limiting_enabled,
                "memory_optimization_enabled": self.config.memory_optimization_enabled,
                "benchmarking_enabled": self.config.benchmarking_enabled,
                "capacity_planning_enabled": self.config.capacity_planning_enabled
            },
            "last_checks": {
                "optimization_check": self.last_optimization_check.isoformat() if self.last_optimization_check else None,
                "benchmark_run": self.last_benchmark_run.isoformat() if self.last_benchmark_run else None,
                "capacity_review": self.last_capacity_review.isoformat() if self.last_capacity_review else None
            },
            "performance_summary": self.performance_summary
        }
    
    async def trigger_optimization(self, optimization_type: str = "all"):
        """Manually trigger specific optimizations."""
        try:
            if optimization_type in ["all", "memory"]:
                if self.component_status.get("memory_optimizer"):
                    await memory_optimizer._proactive_optimization()
                    self.logger.info("Triggered memory optimization")
            
            if optimization_type in ["all", "cache"]:
                if self.component_status.get("query_optimizer"):
                    await query_optimizer._cleanup_local_cache()
                    self.logger.info("Triggered cache cleanup")
            
            if optimization_type in ["all", "benchmark"]:
                if self.component_status.get("performance_benchmarker"):
                    await self._run_scheduled_benchmarks()
                    self.logger.info("Triggered benchmark run")
            
            if optimization_type in ["all", "capacity"]:
                if self.component_status.get("capacity_planner"):
                    await self._perform_capacity_review()
                    self.logger.info("Triggered capacity review")
            
        except Exception as e:
            self.logger.error(f"Error triggering optimization {optimization_type}: {e}")
            raise


# Global performance integration instance
performance_integration = PerformanceIntegration()