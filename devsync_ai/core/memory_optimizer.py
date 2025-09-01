"""
Memory optimization with efficient data structures and garbage collection tuning.
"""

import gc
import sys
import psutil
import logging
import weakref
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..analytics.performance_monitor import performance_monitor, MetricType


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    total_memory_mb: float
    available_memory_mb: float
    used_memory_mb: float
    memory_percent: float
    process_memory_mb: float
    gc_collections: Dict[int, int]
    object_counts: Dict[str, int]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ObjectPoolConfig:
    """Configuration for object pooling."""
    max_size: int = 1000
    cleanup_threshold: int = 800
    cleanup_percentage: float = 0.2
    ttl_seconds: int = 3600


class ObjectPool:
    """Generic object pool for memory optimization."""
    
    def __init__(self, factory: callable, config: ObjectPoolConfig):
        self.factory = factory
        self.config = config
        self.pool: deque = deque()
        self.in_use: Set[int] = set()
        self.created_count = 0
        self.reused_count = 0
        self.lock = threading.Lock()
        self.last_cleanup = datetime.utcnow()
    
    def acquire(self):
        """Acquire an object from the pool."""
        with self.lock:
            if self.pool:
                obj = self.pool.popleft()
                self.in_use.add(id(obj))
                self.reused_count += 1
                return obj
            else:
                obj = self.factory()
                self.in_use.add(id(obj))
                self.created_count += 1
                return obj
    
    def release(self, obj):
        """Release an object back to the pool."""
        with self.lock:
            obj_id = id(obj)
            if obj_id in self.in_use:
                self.in_use.remove(obj_id)
                
                if len(self.pool) < self.config.max_size:
                    # Reset object state if it has a reset method
                    if hasattr(obj, 'reset'):
                        obj.reset()
                    self.pool.append(obj)
                
                # Cleanup if needed
                if len(self.pool) > self.config.cleanup_threshold:
                    self._cleanup()
    
    def _cleanup(self):
        """Clean up old objects from the pool."""
        if datetime.utcnow() - self.last_cleanup < timedelta(seconds=300):
            return  # Don't cleanup too frequently
        
        cleanup_count = int(len(self.pool) * self.config.cleanup_percentage)
        for _ in range(cleanup_count):
            if self.pool:
                self.pool.popleft()
        
        self.last_cleanup = datetime.utcnow()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self.lock:
            return {
                "pool_size": len(self.pool),
                "in_use": len(self.in_use),
                "created_count": self.created_count,
                "reused_count": self.reused_count,
                "reuse_rate": (self.reused_count / (self.created_count + self.reused_count) * 100)
                if (self.created_count + self.reused_count) > 0 else 0
            }


class MemoryOptimizer:
    """
    Memory optimization system with efficient data structures and GC tuning.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Object pools for common objects
        self.object_pools: Dict[str, ObjectPool] = {}
        
        # Weak reference tracking for memory leaks
        self.tracked_objects: Dict[str, weakref.WeakSet] = defaultdict(weakref.WeakSet)
        
        # Memory usage history
        self.memory_history: deque = deque(maxlen=1000)
        
        # GC tuning parameters
        self.gc_thresholds = (700, 10, 10)  # More aggressive than default
        self.gc_enabled = True
        
        # Memory monitoring
        self.memory_warning_threshold = 80.0  # 80% memory usage
        self.memory_critical_threshold = 95.0  # 95% memory usage
        
        # Background monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="memory_optimizer")
        
        # Initialize object pools
        self._setup_object_pools()
        
        # Configure garbage collection
        self._configure_gc()
    
    def _setup_object_pools(self):
        """Setup object pools for common data structures."""
        # Dictionary pool
        self.object_pools["dict"] = ObjectPool(
            factory=dict,
            config=ObjectPoolConfig(max_size=500, cleanup_threshold=400)
        )
        
        # List pool
        self.object_pools["list"] = ObjectPool(
            factory=list,
            config=ObjectPoolConfig(max_size=500, cleanup_threshold=400)
        )
        
        # Set pool
        self.object_pools["set"] = ObjectPool(
            factory=set,
            config=ObjectPoolConfig(max_size=200, cleanup_threshold=160)
        )
    
    def _configure_gc(self):
        """Configure garbage collection for optimal performance."""
        if self.gc_enabled:
            # Set more aggressive thresholds
            gc.set_threshold(*self.gc_thresholds)
            
            # Enable automatic garbage collection
            gc.enable()
            
            self.logger.info(f"Configured GC with thresholds: {self.gc_thresholds}")
        else:
            gc.disable()
            self.logger.info("Garbage collection disabled")
    
    async def start_monitoring(self):
        """Start memory monitoring."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.logger.info("Memory monitoring started")
    
    async def stop_monitoring(self):
        """Stop memory monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self._executor.shutdown(wait=True)
        self.logger.info("Memory monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main memory monitoring loop."""
        try:
            while True:
                await self._collect_memory_stats()
                await self._check_memory_pressure()
                await self._optimize_if_needed()
                await asyncio.sleep(30)  # Monitor every 30 seconds
        except asyncio.CancelledError:
            self.logger.info("Memory monitoring loop cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in memory monitoring loop: {e}")
            await asyncio.sleep(60)
    
    async def _collect_memory_stats(self):
        """Collect current memory statistics."""
        try:
            # Get system memory info
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Get GC statistics
            gc_stats = {}
            for i in range(3):
                gc_stats[i] = gc.get_count()[i]
            
            # Get object counts
            object_counts = {}
            for obj_type in [dict, list, set, str, int, float]:
                count = len(gc.get_objects())  # This is expensive, use sparingly
                object_counts[obj_type.__name__] = count
            
            stats = MemoryStats(
                total_memory_mb=memory.total / (1024 * 1024),
                available_memory_mb=memory.available / (1024 * 1024),
                used_memory_mb=memory.used / (1024 * 1024),
                memory_percent=memory.percent,
                process_memory_mb=process_memory.rss / (1024 * 1024),
                gc_collections=gc_stats,
                object_counts=object_counts
            )
            
            self.memory_history.append(stats)
            
            # Record metrics
            await performance_monitor.record_metric(
                MetricType.MEMORY_USAGE,
                stats.memory_percent,
                metadata={
                    "process_memory_mb": stats.process_memory_mb,
                    "available_memory_mb": stats.available_memory_mb
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting memory stats: {e}")
    
    async def _check_memory_pressure(self):
        """Check for memory pressure and take action if needed."""
        if not self.memory_history:
            return
        
        current_stats = self.memory_history[-1]
        
        if current_stats.memory_percent >= self.memory_critical_threshold:
            self.logger.warning(f"Critical memory usage: {current_stats.memory_percent:.1f}%")
            await self._emergency_cleanup()
            
        elif current_stats.memory_percent >= self.memory_warning_threshold:
            self.logger.info(f"High memory usage: {current_stats.memory_percent:.1f}%")
            await self._gentle_cleanup()
    
    async def _optimize_if_needed(self):
        """Perform optimization if memory usage patterns indicate it's needed."""
        if len(self.memory_history) < 10:
            return
        
        # Check for memory growth trend
        recent_stats = list(self.memory_history)[-10:]
        memory_trend = recent_stats[-1].memory_percent - recent_stats[0].memory_percent
        
        if memory_trend > 10:  # Memory increased by more than 10% in recent samples
            self.logger.info(f"Detected memory growth trend: +{memory_trend:.1f}%")
            await self._proactive_optimization()
    
    async def _emergency_cleanup(self):
        """Emergency memory cleanup when usage is critical."""
        self.logger.warning("Performing emergency memory cleanup")
        
        # Force garbage collection
        await self._run_in_executor(self._force_gc)
        
        # Clear object pools
        for pool in self.object_pools.values():
            pool.pool.clear()
        
        # Clear memory history (keep only recent entries)
        while len(self.memory_history) > 100:
            self.memory_history.popleft()
        
        # Clear weak reference tracking
        for obj_set in self.tracked_objects.values():
            obj_set.clear()
    
    async def _gentle_cleanup(self):
        """Gentle memory cleanup for high usage."""
        self.logger.info("Performing gentle memory cleanup")
        
        # Run garbage collection
        await self._run_in_executor(gc.collect)
        
        # Cleanup object pools
        for pool in self.object_pools.values():
            pool._cleanup()
    
    async def _proactive_optimization(self):
        """Proactive memory optimization based on usage patterns."""
        self.logger.info("Performing proactive memory optimization")
        
        # Analyze object pool usage and adjust sizes
        for name, pool in self.object_pools.items():
            stats = pool.get_stats()
            
            # If reuse rate is low, reduce pool size
            if stats["reuse_rate"] < 20 and pool.config.max_size > 100:
                pool.config.max_size = max(100, int(pool.config.max_size * 0.8))
                self.logger.debug(f"Reduced {name} pool size to {pool.config.max_size}")
            
            # If pool is frequently full, increase size
            elif stats["pool_size"] >= pool.config.max_size * 0.9:
                pool.config.max_size = min(2000, int(pool.config.max_size * 1.2))
                self.logger.debug(f"Increased {name} pool size to {pool.config.max_size}")
    
    async def _run_in_executor(self, func, *args):
        """Run a function in the thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func, *args)
    
    def _force_gc(self):
        """Force garbage collection in all generations."""
        collected = 0
        for generation in range(3):
            collected += gc.collect(generation)
        
        self.logger.debug(f"Forced GC collected {collected} objects")
        return collected
    
    def acquire_object(self, obj_type: str):
        """Acquire an object from the appropriate pool."""
        if obj_type in self.object_pools:
            return self.object_pools[obj_type].acquire()
        else:
            # Fallback to regular object creation
            if obj_type == "dict":
                return {}
            elif obj_type == "list":
                return []
            elif obj_type == "set":
                return set()
            else:
                raise ValueError(f"Unknown object type: {obj_type}")
    
    def release_object(self, obj, obj_type: str):
        """Release an object back to the appropriate pool."""
        if obj_type in self.object_pools:
            self.object_pools[obj_type].release(obj)
    
    def track_object(self, obj, category: str):
        """Track an object for memory leak detection."""
        self.tracked_objects[category].add(obj)
    
    def get_tracked_object_count(self, category: str) -> int:
        """Get the count of tracked objects in a category."""
        return len(self.tracked_objects[category])
    
    def optimize_data_structure(self, data: Any) -> Any:
        """Optimize a data structure for memory efficiency."""
        if isinstance(data, dict):
            return self._optimize_dict(data)
        elif isinstance(data, list):
            return self._optimize_list(data)
        elif isinstance(data, str):
            return self._optimize_string(data)
        else:
            return data
    
    def _optimize_dict(self, data: dict) -> dict:
        """Optimize dictionary for memory efficiency."""
        # Use __slots__ for objects if possible
        # Convert to more memory-efficient structures if appropriate
        
        # For small dictionaries, consider using namedtuple
        if len(data) <= 10 and all(isinstance(k, str) for k in data.keys()):
            try:
                from collections import namedtuple
                OptimizedDict = namedtuple('OptimizedDict', data.keys())
                return OptimizedDict(**data)
            except (ValueError, TypeError):
                pass  # Fall back to regular dict
        
        return data
    
    def _optimize_list(self, data: list) -> Union[list, tuple]:
        """Optimize list for memory efficiency."""
        # Convert to tuple if the list won't be modified
        # This saves memory as tuples are more compact
        if len(data) > 0 and all(isinstance(item, (str, int, float, bool, type(None))) for item in data):
            return tuple(data)
        
        return data
    
    def _optimize_string(self, data: str) -> str:
        """Optimize string for memory efficiency."""
        # Intern frequently used strings
        if len(data) < 100 and data.isidentifier():
            return sys.intern(data)
        
        return data
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        if not self.memory_history:
            return {}
        
        current_stats = self.memory_history[-1]
        
        # Calculate trends
        if len(self.memory_history) >= 2:
            previous_stats = self.memory_history[-2]
            memory_trend = current_stats.memory_percent - previous_stats.memory_percent
            process_trend = current_stats.process_memory_mb - previous_stats.process_memory_mb
        else:
            memory_trend = 0
            process_trend = 0
        
        # Object pool statistics
        pool_stats = {}
        for name, pool in self.object_pools.items():
            pool_stats[name] = pool.get_stats()
        
        # Tracked object statistics
        tracked_stats = {}
        for category, obj_set in self.tracked_objects.items():
            tracked_stats[category] = len(obj_set)
        
        return {
            "current": {
                "total_memory_mb": current_stats.total_memory_mb,
                "available_memory_mb": current_stats.available_memory_mb,
                "used_memory_mb": current_stats.used_memory_mb,
                "memory_percent": current_stats.memory_percent,
                "process_memory_mb": current_stats.process_memory_mb
            },
            "trends": {
                "memory_trend_percent": round(memory_trend, 2),
                "process_trend_mb": round(process_trend, 2)
            },
            "gc_stats": current_stats.gc_collections,
            "object_pools": pool_stats,
            "tracked_objects": tracked_stats,
            "thresholds": {
                "warning_percent": self.memory_warning_threshold,
                "critical_percent": self.memory_critical_threshold
            }
        }
    
    def suggest_optimizations(self) -> List[str]:
        """Suggest memory optimizations based on current usage patterns."""
        suggestions = []
        
        if not self.memory_history:
            return suggestions
        
        current_stats = self.memory_history[-1]
        
        # High memory usage suggestions
        if current_stats.memory_percent > self.memory_warning_threshold:
            suggestions.append("Consider reducing data retention periods")
            suggestions.append("Implement more aggressive caching eviction policies")
            suggestions.append("Review and optimize large data structures")
        
        # Object pool suggestions
        for name, pool in self.object_pools.items():
            stats = pool.get_stats()
            
            if stats["reuse_rate"] < 30:
                suggestions.append(f"Low reuse rate for {name} pool - consider reducing pool size")
            
            if stats["in_use"] > stats["pool_size"] * 2:
                suggestions.append(f"High demand for {name} objects - consider increasing pool size")
        
        # GC suggestions
        if len(self.memory_history) >= 10:
            recent_gc_counts = [stats.gc_collections for stats in list(self.memory_history)[-10:]]
            
            # Check if GC is running frequently
            total_collections = sum(sum(counts.values()) for counts in recent_gc_counts)
            if total_collections > 100:  # More than 10 collections per sample on average
                suggestions.append("High GC activity detected - consider optimizing object creation patterns")
        
        return suggestions


# Global memory optimizer instance
memory_optimizer = MemoryOptimizer()