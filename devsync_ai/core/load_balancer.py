"""
Load balancing and horizontal scaling for changelog generation system.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict, deque

from ..analytics.performance_monitor import performance_monitor, MetricType


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RESOURCE_BASED = "resource_based"
    RESPONSE_TIME_BASED = "response_time_based"


class WorkerStatus(Enum):
    """Worker node status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OVERLOADED = "overloaded"
    OFFLINE = "offline"


@dataclass
class WorkerNode:
    """Represents a worker node in the load balancing pool."""
    node_id: str
    host: str
    port: int
    weight: float = 1.0
    max_concurrent_tasks: int = 10
    current_tasks: int = 0
    status: WorkerStatus = WorkerStatus.HEALTHY
    last_health_check: Optional[datetime] = None
    avg_response_time: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadBalancingTask:
    """Task to be distributed across worker nodes."""
    task_id: str
    task_type: str
    priority: int = 1  # 1 = low, 5 = high
    estimated_duration: Optional[float] = None
    team_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    assigned_node: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class LoadBalancer:
    """
    Intelligent load balancer with horizontal scaling and resource optimization.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.worker_nodes: Dict[str, WorkerNode] = {}
        self.task_queue: deque = deque()
        self.priority_queues: Dict[int, deque] = defaultdict(deque)
        self.active_tasks: Dict[str, LoadBalancingTask] = {}
        self.completed_tasks: deque = deque(maxlen=1000)
        
        # Load balancing state
        self.current_strategy = LoadBalancingStrategy.RESOURCE_BASED
        self.round_robin_index = 0
        
        # Scaling configuration
        self.min_workers = 2
        self.max_workers = 20
        self.scale_up_threshold = 0.8  # 80% capacity
        self.scale_down_threshold = 0.3  # 30% capacity
        self.scale_cooldown = timedelta(minutes=5)
        self.last_scale_action: Optional[datetime] = None
        
        # Health monitoring
        self.health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        self._task_processor_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the load balancer and background tasks."""
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._task_processor_task = asyncio.create_task(self._task_processor_loop())
        self.logger.info("Load balancer started")
    
    async def stop(self):
        """Stop the load balancer and cleanup."""
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._task_processor_task:
            self._task_processor_task.cancel()
        
        # Wait for tasks to complete
        try:
            if self._health_check_task:
                await self._health_check_task
            if self._task_processor_task:
                await self._task_processor_task
        except asyncio.CancelledError:
            pass
        
        self.logger.info("Load balancer stopped")
    
    def register_worker(
        self,
        node_id: str,
        host: str,
        port: int,
        weight: float = 1.0,
        max_concurrent_tasks: int = 10,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WorkerNode:
        """Register a new worker node."""
        worker = WorkerNode(
            node_id=node_id,
            host=host,
            port=port,
            weight=weight,
            max_concurrent_tasks=max_concurrent_tasks,
            metadata=metadata or {}
        )
        
        self.worker_nodes[node_id] = worker
        self.logger.info(f"Registered worker node: {node_id} at {host}:{port}")
        
        return worker
    
    def unregister_worker(self, node_id: str):
        """Unregister a worker node."""
        if node_id in self.worker_nodes:
            worker = self.worker_nodes[node_id]
            worker.status = WorkerStatus.OFFLINE
            
            # Reassign active tasks from this worker
            tasks_to_reassign = [
                task for task in self.active_tasks.values()
                if task.assigned_node == node_id
            ]
            
            for task in tasks_to_reassign:
                task.assigned_node = None
                self.priority_queues[task.priority].appendleft(task)
                del self.active_tasks[task.task_id]
            
            del self.worker_nodes[node_id]
            self.logger.info(f"Unregistered worker node: {node_id}")
    
    async def submit_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: int = 1,
        team_id: Optional[str] = None,
        estimated_duration: Optional[float] = None
    ) -> str:
        """Submit a task for load-balanced execution."""
        task_id = f"{task_type}_{int(datetime.utcnow().timestamp())}_{random.randint(1000, 9999)}"
        
        task = LoadBalancingTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            estimated_duration=estimated_duration,
            team_id=team_id,
            payload=payload
        )
        
        # Add to appropriate priority queue
        self.priority_queues[priority].append(task)
        
        self.logger.debug(f"Submitted task {task_id} with priority {priority}")
        
        # Record task submission metric
        await performance_monitor.record_metric(
            MetricType.CONCURRENT_OPERATIONS,
            len(self.active_tasks) + sum(len(q) for q in self.priority_queues.values()),
            team_id=team_id,
            metadata={"task_type": task_type}
        )
        
        return task_id
    
    async def _task_processor_loop(self):
        """Main task processing loop."""
        try:
            while True:
                await self._process_pending_tasks()
                await self._check_scaling_needs()
                await asyncio.sleep(1)  # Process tasks every second
        except asyncio.CancelledError:
            self.logger.info("Task processor loop cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in task processor loop: {e}")
            await asyncio.sleep(5)
    
    async def _process_pending_tasks(self):
        """Process pending tasks by assigning them to available workers."""
        # Process tasks by priority (highest first)
        for priority in sorted(self.priority_queues.keys(), reverse=True):
            queue = self.priority_queues[priority]
            
            while queue:
                # Find available worker
                worker = await self._select_worker()
                if not worker:
                    break  # No available workers
                
                task = queue.popleft()
                await self._assign_task_to_worker(task, worker)
    
    async def _select_worker(self) -> Optional[WorkerNode]:
        """Select the best available worker based on the current strategy."""
        available_workers = [
            worker for worker in self.worker_nodes.values()
            if (worker.status in [WorkerStatus.HEALTHY, WorkerStatus.DEGRADED] and
                worker.current_tasks < worker.max_concurrent_tasks)
        ]
        
        if not available_workers:
            return None
        
        if self.current_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._select_round_robin(available_workers)
        elif self.current_strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._select_least_connections(available_workers)
        elif self.current_strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._select_weighted_round_robin(available_workers)
        elif self.current_strategy == LoadBalancingStrategy.RESOURCE_BASED:
            return self._select_resource_based(available_workers)
        elif self.current_strategy == LoadBalancingStrategy.RESPONSE_TIME_BASED:
            return self._select_response_time_based(available_workers)
        else:
            return available_workers[0]  # Fallback
    
    def _select_round_robin(self, workers: List[WorkerNode]) -> WorkerNode:
        """Select worker using round-robin strategy."""
        worker = workers[self.round_robin_index % len(workers)]
        self.round_robin_index += 1
        return worker
    
    def _select_least_connections(self, workers: List[WorkerNode]) -> WorkerNode:
        """Select worker with least active connections."""
        return min(workers, key=lambda w: w.current_tasks)
    
    def _select_weighted_round_robin(self, workers: List[WorkerNode]) -> WorkerNode:
        """Select worker using weighted round-robin strategy."""
        # Create weighted list
        weighted_workers = []
        for worker in workers:
            weight_count = max(1, int(worker.weight * 10))
            weighted_workers.extend([worker] * weight_count)
        
        if weighted_workers:
            worker = weighted_workers[self.round_robin_index % len(weighted_workers)]
            self.round_robin_index += 1
            return worker
        
        return workers[0]
    
    def _select_resource_based(self, workers: List[WorkerNode]) -> WorkerNode:
        """Select worker based on resource utilization."""
        def resource_score(worker: WorkerNode) -> float:
            # Lower score is better
            cpu_score = worker.cpu_usage / 100.0
            memory_score = worker.memory_usage / 100.0
            task_score = worker.current_tasks / worker.max_concurrent_tasks
            
            # Weighted combination
            return (cpu_score * 0.4 + memory_score * 0.3 + task_score * 0.3) / worker.weight
        
        return min(workers, key=resource_score)
    
    def _select_response_time_based(self, workers: List[WorkerNode]) -> WorkerNode:
        """Select worker based on average response time."""
        def response_time_score(worker: WorkerNode) -> float:
            # Consider both response time and current load
            base_score = worker.avg_response_time
            load_penalty = worker.current_tasks / worker.max_concurrent_tasks * 1000  # ms
            return (base_score + load_penalty) / worker.weight
        
        return min(workers, key=response_time_score)
    
    async def _assign_task_to_worker(self, task: LoadBalancingTask, worker: WorkerNode):
        """Assign a task to a specific worker."""
        task.assigned_node = worker.node_id
        task.started_at = datetime.utcnow()
        
        worker.current_tasks += 1
        self.active_tasks[task.task_id] = task
        
        self.logger.debug(f"Assigned task {task.task_id} to worker {worker.node_id}")
        
        # Start task execution (this would typically make an HTTP request to the worker)
        asyncio.create_task(self._execute_task_on_worker(task, worker))
    
    async def _execute_task_on_worker(self, task: LoadBalancingTask, worker: WorkerNode):
        """Execute a task on a worker node (simulated)."""
        operation_id = await performance_monitor.start_operation(
            f"task_{task.task_id}",
            task.task_type,
            task.team_id
        )
        
        try:
            # Simulate task execution
            # In a real implementation, this would make an HTTP request to the worker
            execution_time = task.estimated_duration or random.uniform(1, 30)
            await asyncio.sleep(execution_time)
            
            # Task completed successfully
            await self._complete_task(task, worker, True)
            await performance_monitor.end_operation(operation_id, True, task.team_id)
            
        except Exception as e:
            self.logger.error(f"Task {task.task_id} failed on worker {worker.node_id}: {e}")
            await self._complete_task(task, worker, False)
            await performance_monitor.end_operation(operation_id, False, task.team_id)
    
    async def _complete_task(self, task: LoadBalancingTask, worker: WorkerNode, success: bool):
        """Mark a task as completed and update worker statistics."""
        task.completed_at = datetime.utcnow()
        
        # Update worker statistics
        worker.current_tasks -= 1
        worker.total_requests += 1
        
        if not success:
            worker.failed_requests += 1
        
        # Calculate response time
        if task.started_at:
            response_time = (task.completed_at - task.started_at).total_seconds() * 1000  # ms
            
            # Update average response time (exponential moving average)
            if worker.avg_response_time == 0:
                worker.avg_response_time = response_time
            else:
                worker.avg_response_time = (worker.avg_response_time * 0.9) + (response_time * 0.1)
        
        # Move task from active to completed
        if task.task_id in self.active_tasks:
            del self.active_tasks[task.task_id]
        
        self.completed_tasks.append(task)
        
        self.logger.debug(f"Completed task {task.task_id} on worker {worker.node_id}")
    
    async def _health_check_loop(self):
        """Periodic health check for all worker nodes."""
        try:
            while True:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
        except asyncio.CancelledError:
            self.logger.info("Health check loop cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in health check loop: {e}")
            await asyncio.sleep(30)
    
    async def _perform_health_checks(self):
        """Perform health checks on all worker nodes."""
        for worker in self.worker_nodes.values():
            try:
                # Simulate health check (in real implementation, this would be an HTTP request)
                await self._check_worker_health(worker)
                
            except Exception as e:
                self.logger.error(f"Health check failed for worker {worker.node_id}: {e}")
                worker.status = WorkerStatus.OFFLINE
    
    async def _check_worker_health(self, worker: WorkerNode):
        """Check the health of a specific worker node."""
        # Simulate health check response
        worker.last_health_check = datetime.utcnow()
        
        # Simulate resource usage (in real implementation, this would come from the worker)
        worker.cpu_usage = random.uniform(10, 90)
        worker.memory_usage = random.uniform(20, 80)
        
        # Determine worker status based on resource usage and error rate
        error_rate = (worker.failed_requests / max(worker.total_requests, 1)) * 100
        
        if worker.cpu_usage > 95 or worker.memory_usage > 95 or error_rate > 20:
            worker.status = WorkerStatus.OVERLOADED
        elif worker.cpu_usage > 80 or worker.memory_usage > 80 or error_rate > 10:
            worker.status = WorkerStatus.DEGRADED
        else:
            worker.status = WorkerStatus.HEALTHY
        
        # Record worker metrics
        await performance_monitor.record_metric(
            MetricType.CPU_USAGE,
            worker.cpu_usage,
            metadata={"worker_id": worker.node_id}
        )
        
        await performance_monitor.record_metric(
            MetricType.MEMORY_USAGE,
            worker.memory_usage,
            metadata={"worker_id": worker.node_id}
        )
    
    async def _check_scaling_needs(self):
        """Check if scaling up or down is needed."""
        if self.last_scale_action and datetime.utcnow() - self.last_scale_action < self.scale_cooldown:
            return  # Still in cooldown period
        
        healthy_workers = [
            w for w in self.worker_nodes.values()
            if w.status in [WorkerStatus.HEALTHY, WorkerStatus.DEGRADED]
        ]
        
        if not healthy_workers:
            return
        
        # Calculate overall capacity utilization
        total_capacity = sum(w.max_concurrent_tasks for w in healthy_workers)
        total_active = sum(w.current_tasks for w in healthy_workers)
        utilization = total_active / total_capacity if total_capacity > 0 else 0
        
        # Check for scale up
        if (utilization > self.scale_up_threshold and 
            len(healthy_workers) < self.max_workers and
            sum(len(q) for q in self.priority_queues.values()) > 0):
            
            await self._scale_up()
        
        # Check for scale down
        elif (utilization < self.scale_down_threshold and 
              len(healthy_workers) > self.min_workers):
            
            await self._scale_down()
    
    async def _scale_up(self):
        """Scale up by adding a new worker node."""
        try:
            # In a real implementation, this would provision a new worker instance
            new_node_id = f"worker_{len(self.worker_nodes) + 1}_{int(datetime.utcnow().timestamp())}"
            
            self.register_worker(
                node_id=new_node_id,
                host="localhost",  # Would be actual host in real implementation
                port=8000 + len(self.worker_nodes),
                weight=1.0,
                max_concurrent_tasks=10
            )
            
            self.last_scale_action = datetime.utcnow()
            self.logger.info(f"Scaled up: Added worker {new_node_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to scale up: {e}")
    
    async def _scale_down(self):
        """Scale down by removing an underutilized worker node."""
        try:
            # Find the worker with the least load
            healthy_workers = [
                w for w in self.worker_nodes.values()
                if w.status in [WorkerStatus.HEALTHY, WorkerStatus.DEGRADED]
            ]
            
            if len(healthy_workers) <= self.min_workers:
                return
            
            # Select worker with least current tasks
            worker_to_remove = min(healthy_workers, key=lambda w: w.current_tasks)
            
            # Only remove if it has no active tasks
            if worker_to_remove.current_tasks == 0:
                self.unregister_worker(worker_to_remove.node_id)
                self.last_scale_action = datetime.utcnow()
                self.logger.info(f"Scaled down: Removed worker {worker_to_remove.node_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to scale down: {e}")
    
    def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get comprehensive load balancer statistics."""
        healthy_workers = [w for w in self.worker_nodes.values() if w.status == WorkerStatus.HEALTHY]
        degraded_workers = [w for w in self.worker_nodes.values() if w.status == WorkerStatus.DEGRADED]
        overloaded_workers = [w for w in self.worker_nodes.values() if w.status == WorkerStatus.OVERLOADED]
        offline_workers = [w for w in self.worker_nodes.values() if w.status == WorkerStatus.OFFLINE]
        
        total_capacity = sum(w.max_concurrent_tasks for w in self.worker_nodes.values())
        total_active = sum(w.current_tasks for w in self.worker_nodes.values())
        
        pending_tasks = sum(len(q) for q in self.priority_queues.values())
        
        return {
            "workers": {
                "total": len(self.worker_nodes),
                "healthy": len(healthy_workers),
                "degraded": len(degraded_workers),
                "overloaded": len(overloaded_workers),
                "offline": len(offline_workers)
            },
            "capacity": {
                "total_slots": total_capacity,
                "active_tasks": total_active,
                "utilization_percent": round((total_active / total_capacity * 100) if total_capacity > 0 else 0, 2)
            },
            "tasks": {
                "pending": pending_tasks,
                "active": len(self.active_tasks),
                "completed": len(self.completed_tasks)
            },
            "performance": {
                "avg_response_time_ms": round(
                    sum(w.avg_response_time for w in self.worker_nodes.values()) / len(self.worker_nodes)
                    if self.worker_nodes else 0,
                    2
                ),
                "total_requests": sum(w.total_requests for w in self.worker_nodes.values()),
                "total_failures": sum(w.failed_requests for w in self.worker_nodes.values())
            },
            "configuration": {
                "strategy": self.current_strategy.value,
                "min_workers": self.min_workers,
                "max_workers": self.max_workers,
                "scale_up_threshold": self.scale_up_threshold,
                "scale_down_threshold": self.scale_down_threshold
            }
        }


# Global load balancer instance
load_balancer = LoadBalancer()