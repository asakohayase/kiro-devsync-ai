"""
Real-Time Hook Execution Dashboard for DevSync AI.

This module provides comprehensive monitoring and analytics for JIRA Agent Hooks
with real-time visualization and intelligent insights.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import statistics
import psutil
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from devsync_ai.hooks.hook_registry_manager import get_hook_registry_manager
from devsync_ai.core.agent_hooks import HookExecutionResult, HookStatus


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"


class MetricType(Enum):
    """Types of metrics tracked."""
    EXECUTION_TIME = "execution_time"
    SUCCESS_RATE = "success_rate"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    QUEUE_DEPTH = "queue_depth"
    RESOURCE_USAGE = "resource_usage"


@dataclass
class SystemMetrics:
    """System-wide performance metrics."""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    memory_available: float
    active_connections: int
    queue_depth: int
    processing_rate: float
    average_response_time: float
    error_rate: float
    health_status: HealthStatus


@dataclass
class HookMetrics:
    """Individual hook performance metrics."""
    hook_id: str
    hook_type: str
    team_id: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_execution_time: float
    last_execution: Optional[datetime]
    success_rate: float
    error_rate: float
    throughput_per_hour: float
    health_status: HealthStatus


@dataclass
class TeamMetrics:
    """Team-level analytics and productivity metrics."""
    team_id: str
    total_hooks: int
    active_hooks: int
    total_executions: int
    average_response_time: float
    productivity_score: float
    collaboration_index: float
    blocker_resolution_time: float
    sprint_velocity_improvement: float


@dataclass
class RealTimeEvent:
    """Real-time event for dashboard updates."""
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    severity: str = "info"


class HookMonitoringDashboard:
    """
    Real-time monitoring dashboard for JIRA Agent Hooks.
    
    Provides comprehensive analytics, performance monitoring, and
    intelligent insights for the hook system.
    """
    
    def __init__(self):
        """Initialize the monitoring dashboard."""
        self.active_connections: List[WebSocket] = []
        self.metrics_history: List[SystemMetrics] = []
        self.hook_metrics: Dict[str, HookMetrics] = {}
        self.team_metrics: Dict[str, TeamMetrics] = {}
        self.real_time_events: List[RealTimeEvent] = []
        
        # Performance thresholds
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 90.0,
            'memory_warning': 80.0,
            'memory_critical': 95.0,
            'response_time_warning': 2000.0,  # ms
            'response_time_critical': 5000.0,  # ms
            'error_rate_warning': 0.05,  # 5%
            'error_rate_critical': 0.15,  # 15%
            'success_rate_warning': 0.95,  # 95%
            'success_rate_critical': 0.85   # 85%
        }
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._last_metrics_update = datetime.min
        
        # Data retention (keep last 24 hours)
        self.max_history_hours = 24
    
    async def start_monitoring(self):
        """Start the monitoring system."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Hook monitoring dashboard started")
    
    async def stop_monitoring(self):
        """Stop the monitoring system."""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Close all WebSocket connections
        for connection in self.active_connections.copy():
            try:
                await connection.close()
            except Exception:
                pass
        
        logger.info("Hook monitoring dashboard stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._monitoring_active:
            try:
                # Collect system metrics
                system_metrics = await self._collect_system_metrics()
                self.metrics_history.append(system_metrics)
                
                # Collect hook metrics
                await self._collect_hook_metrics()
                
                # Collect team metrics
                await self._collect_team_metrics()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                # Broadcast updates to connected clients
                await self._broadcast_metrics_update()
                
                # Check for alerts
                await self._check_alert_conditions(system_metrics)
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Wait longer on error
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system-wide performance metrics."""
        # Get system resource usage
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        memory_available = memory.available / (1024 * 1024 * 1024)  # GB
        
        # Get hook system metrics
        registry_manager = await get_hook_registry_manager()
        queue_depth = 0
        processing_rate = 0.0
        average_response_time = 0.0
        error_rate = 0.0
        
        if registry_manager:
            health = await registry_manager.get_system_health()
            average_response_time = health.average_execution_time_ms
            error_rate = 1.0 - health.success_rate
            
            # Calculate processing rate (executions per minute)
            if len(self.metrics_history) > 0:
                recent_metrics = self.metrics_history[-12:]  # Last minute (5s intervals)
                if len(recent_metrics) > 1:
                    time_span = (recent_metrics[-1].timestamp - recent_metrics[0].timestamp).total_seconds()
                    if time_span > 0:
                        processing_rate = len(recent_metrics) / (time_span / 60)
        
        # Determine health status
        health_status = self._determine_health_status(
            cpu_usage, memory_usage, average_response_time, error_rate
        )
        
        return SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            memory_available=memory_available,
            active_connections=len(self.active_connections),
            queue_depth=queue_depth,
            processing_rate=processing_rate,
            average_response_time=average_response_time,
            error_rate=error_rate,
            health_status=health_status
        )
    
    async def _collect_hook_metrics(self):
        """Collect metrics for individual hooks."""
        registry_manager = await get_hook_registry_manager()
        if not registry_manager:
            return
        
        hook_statuses = await registry_manager.get_all_hook_statuses()
        
        for hook_status in hook_statuses:
            hook_id = hook_status['hook_id']
            stats = hook_status['statistics']
            
            # Calculate throughput (executions per hour)
            throughput = 0.0
            if stats['last_execution']:
                last_exec = datetime.fromisoformat(stats['last_execution'])
                hours_since = (datetime.now(timezone.utc) - last_exec).total_seconds() / 3600
                if hours_since > 0:
                    throughput = stats['total_executions'] / max(hours_since, 1)
            
            # Determine health status
            success_rate = stats['success_rate']
            avg_time = stats['average_execution_time_ms']
            
            if success_rate < self.thresholds['success_rate_critical'] or avg_time > self.thresholds['response_time_critical']:
                health_status = HealthStatus.CRITICAL
            elif success_rate < self.thresholds['success_rate_warning'] or avg_time > self.thresholds['response_time_warning']:
                health_status = HealthStatus.WARNING
            else:
                health_status = HealthStatus.HEALTHY
            
            self.hook_metrics[hook_id] = HookMetrics(
                hook_id=hook_id,
                hook_type=hook_status['hook_type'],
                team_id=hook_status['team_id'],
                total_executions=stats['total_executions'],
                successful_executions=int(stats['total_executions'] * stats['success_rate']),
                failed_executions=int(stats['total_executions'] * (1 - stats['success_rate'])),
                average_execution_time=stats['average_execution_time_ms'],
                last_execution=datetime.fromisoformat(stats['last_execution']) if stats['last_execution'] else None,
                success_rate=stats['success_rate'],
                error_rate=1.0 - stats['success_rate'],
                throughput_per_hour=throughput,
                health_status=health_status
            )
    
    async def _collect_team_metrics(self):
        """Collect team-level productivity metrics."""
        # Group hooks by team
        team_hooks = {}
        for hook_id, metrics in self.hook_metrics.items():
            team_id = metrics.team_id
            if team_id not in team_hooks:
                team_hooks[team_id] = []
            team_hooks[team_id].append(metrics)
        
        # Calculate team metrics
        for team_id, hooks in team_hooks.items():
            total_hooks = len(hooks)
            active_hooks = len([h for h in hooks if h.last_execution and 
                              (datetime.now(timezone.utc) - h.last_execution).total_seconds() < 3600])
            
            total_executions = sum(h.total_executions for h in hooks)
            avg_response_time = statistics.mean([h.average_execution_time for h in hooks]) if hooks else 0.0
            
            # Calculate productivity score (0-100)
            success_rates = [h.success_rate for h in hooks if h.total_executions > 0]
            avg_success_rate = statistics.mean(success_rates) if success_rates else 1.0
            productivity_score = min(100, avg_success_rate * 100 * (active_hooks / max(total_hooks, 1)))
            
            # Mock additional metrics (would be calculated from actual data)
            collaboration_index = min(100, productivity_score * 1.1)
            blocker_resolution_time = max(1.0, 24.0 - (productivity_score / 10))  # Hours
            sprint_velocity_improvement = max(0, (productivity_score - 70) / 3)  # Percentage
            
            self.team_metrics[team_id] = TeamMetrics(
                team_id=team_id,
                total_hooks=total_hooks,
                active_hooks=active_hooks,
                total_executions=total_executions,
                average_response_time=avg_response_time,
                productivity_score=productivity_score,
                collaboration_index=collaboration_index,
                blocker_resolution_time=blocker_resolution_time,
                sprint_velocity_improvement=sprint_velocity_improvement
            )
    
    def _determine_health_status(
        self, 
        cpu_usage: float, 
        memory_usage: float, 
        response_time: float, 
        error_rate: float
    ) -> HealthStatus:
        """Determine overall system health status."""
        if (cpu_usage > self.thresholds['cpu_critical'] or 
            memory_usage > self.thresholds['memory_critical'] or
            response_time > self.thresholds['response_time_critical'] or
            error_rate > self.thresholds['error_rate_critical']):
            return HealthStatus.CRITICAL
        
        if (cpu_usage > self.thresholds['cpu_warning'] or 
            memory_usage > self.thresholds['memory_warning'] or
            response_time > self.thresholds['response_time_warning'] or
            error_rate > self.thresholds['error_rate_warning']):
            return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    async def _cleanup_old_data(self):
        """Clean up old metrics data."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.max_history_hours)
        
        # Clean metrics history
        self.metrics_history = [
            m for m in self.metrics_history 
            if m.timestamp > cutoff_time
        ]
        
        # Clean real-time events
        self.real_time_events = [
            e for e in self.real_time_events 
            if e.timestamp > cutoff_time
        ]
    
    async def _broadcast_metrics_update(self):
        """Broadcast metrics update to all connected WebSocket clients."""
        if not self.active_connections:
            return
        
        # Prepare update data
        update_data = {
            "type": "metrics_update",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_metrics": self._serialize_system_metrics(),
            "hook_metrics": self._serialize_hook_metrics(),
            "team_metrics": self._serialize_team_metrics()
        }
        
        # Send to all connected clients
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(update_data))
            except Exception:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.active_connections.remove(connection)
    
    async def _check_alert_conditions(self, metrics: SystemMetrics):
        """Check for alert conditions and generate events."""
        alerts = []
        
        # CPU usage alerts
        if metrics.cpu_usage > self.thresholds['cpu_critical']:
            alerts.append({
                "type": "cpu_critical",
                "message": f"Critical CPU usage: {metrics.cpu_usage:.1f}%",
                "severity": "critical"
            })
        elif metrics.cpu_usage > self.thresholds['cpu_warning']:
            alerts.append({
                "type": "cpu_warning",
                "message": f"High CPU usage: {metrics.cpu_usage:.1f}%",
                "severity": "warning"
            })
        
        # Memory usage alerts
        if metrics.memory_usage > self.thresholds['memory_critical']:
            alerts.append({
                "type": "memory_critical",
                "message": f"Critical memory usage: {metrics.memory_usage:.1f}%",
                "severity": "critical"
            })
        elif metrics.memory_usage > self.thresholds['memory_warning']:
            alerts.append({
                "type": "memory_warning",
                "message": f"High memory usage: {metrics.memory_usage:.1f}%",
                "severity": "warning"
            })
        
        # Response time alerts
        if metrics.average_response_time > self.thresholds['response_time_critical']:
            alerts.append({
                "type": "response_time_critical",
                "message": f"Critical response time: {metrics.average_response_time:.1f}ms",
                "severity": "critical"
            })
        elif metrics.average_response_time > self.thresholds['response_time_warning']:
            alerts.append({
                "type": "response_time_warning",
                "message": f"High response time: {metrics.average_response_time:.1f}ms",
                "severity": "warning"
            })
        
        # Create real-time events for alerts
        for alert in alerts:
            event = RealTimeEvent(
                event_type="alert",
                timestamp=datetime.now(timezone.utc),
                data=alert,
                severity=alert["severity"]
            )
            self.real_time_events.append(event)
            
            # Broadcast alert immediately
            await self._broadcast_alert(alert)
    
    async def _broadcast_alert(self, alert: Dict[str, Any]):
        """Broadcast alert to connected clients."""
        alert_data = {
            "type": "alert",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alert": alert
        }
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(alert_data))
            except Exception:
                disconnected.append(connection)
        
        for connection in disconnected:
            self.active_connections.remove(connection)
    
    def _serialize_system_metrics(self) -> Dict[str, Any]:
        """Serialize system metrics for JSON transmission."""
        if not self.metrics_history:
            return {}
        
        latest = self.metrics_history[-1]
        return {
            "timestamp": latest.timestamp.isoformat(),
            "cpu_usage": latest.cpu_usage,
            "memory_usage": latest.memory_usage,
            "memory_available": latest.memory_available,
            "active_connections": latest.active_connections,
            "queue_depth": latest.queue_depth,
            "processing_rate": latest.processing_rate,
            "average_response_time": latest.average_response_time,
            "error_rate": latest.error_rate,
            "health_status": latest.health_status.value,
            "history": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "cpu_usage": m.cpu_usage,
                    "memory_usage": m.memory_usage,
                    "processing_rate": m.processing_rate,
                    "average_response_time": m.average_response_time,
                    "error_rate": m.error_rate
                }
                for m in self.metrics_history[-60:]  # Last 5 minutes
            ]
        }
    
    def _serialize_hook_metrics(self) -> List[Dict[str, Any]]:
        """Serialize hook metrics for JSON transmission."""
        return [
            {
                "hook_id": metrics.hook_id,
                "hook_type": metrics.hook_type,
                "team_id": metrics.team_id,
                "total_executions": metrics.total_executions,
                "successful_executions": metrics.successful_executions,
                "failed_executions": metrics.failed_executions,
                "average_execution_time": metrics.average_execution_time,
                "last_execution": metrics.last_execution.isoformat() if metrics.last_execution else None,
                "success_rate": metrics.success_rate,
                "error_rate": metrics.error_rate,
                "throughput_per_hour": metrics.throughput_per_hour,
                "health_status": metrics.health_status.value
            }
            for metrics in self.hook_metrics.values()
        ]
    
    def _serialize_team_metrics(self) -> List[Dict[str, Any]]:
        """Serialize team metrics for JSON transmission."""
        return [
            {
                "team_id": metrics.team_id,
                "total_hooks": metrics.total_hooks,
                "active_hooks": metrics.active_hooks,
                "total_executions": metrics.total_executions,
                "average_response_time": metrics.average_response_time,
                "productivity_score": metrics.productivity_score,
                "collaboration_index": metrics.collaboration_index,
                "blocker_resolution_time": metrics.blocker_resolution_time,
                "sprint_velocity_improvement": metrics.sprint_velocity_improvement
            }
            for metrics in self.team_metrics.values()
        ]
    
    async def connect_websocket(self, websocket: WebSocket):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Send initial data
        initial_data = {
            "type": "initial_data",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_metrics": self._serialize_system_metrics(),
            "hook_metrics": self._serialize_hook_metrics(),
            "team_metrics": self._serialize_team_metrics(),
            "recent_events": [
                {
                    "event_type": event.event_type,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data,
                    "severity": event.severity
                }
                for event in self.real_time_events[-50:]  # Last 50 events
            ]
        }
        
        try:
            await websocket.send_text(json.dumps(initial_data))
        except Exception as e:
            logger.error(f"Failed to send initial data: {e}")
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    async def disconnect_websocket(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    # API Methods for dashboard data
    async def get_dashboard_data(
        self,
        time_range: str = "1h",
        team_filter: Optional[str] = None,
        hook_type_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        # Parse time range
        if time_range == "1h":
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        elif time_range == "24h":
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        elif time_range == "7d":
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Filter metrics history
        filtered_history = [m for m in self.metrics_history if m.timestamp > cutoff]
        
        # Filter hook metrics
        filtered_hooks = self.hook_metrics.values()
        if team_filter:
            filtered_hooks = [h for h in filtered_hooks if h.team_id == team_filter]
        if hook_type_filter:
            filtered_hooks = [h for h in filtered_hooks if h.hook_type == hook_type_filter]
        
        return {
            "system_overview": self._serialize_system_metrics(),
            "hook_metrics": [
                {
                    "hook_id": h.hook_id,
                    "hook_type": h.hook_type,
                    "team_id": h.team_id,
                    "total_executions": h.total_executions,
                    "success_rate": h.success_rate,
                    "average_execution_time": h.average_execution_time,
                    "health_status": h.health_status.value
                }
                for h in filtered_hooks
            ],
            "team_metrics": self._serialize_team_metrics(),
            "performance_trends": {
                "timestamps": [m.timestamp.isoformat() for m in filtered_history],
                "cpu_usage": [m.cpu_usage for m in filtered_history],
                "memory_usage": [m.memory_usage for m in filtered_history],
                "response_times": [m.average_response_time for m in filtered_history],
                "error_rates": [m.error_rate for m in filtered_history],
                "processing_rates": [m.processing_rate for m in filtered_history]
            },
            "alerts": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "type": event.event_type,
                    "data": event.data,
                    "severity": event.severity
                }
                for event in self.real_time_events
                if event.event_type == "alert" and event.timestamp > cutoff
            ]
        }


# Global dashboard instance
_dashboard: Optional[HookMonitoringDashboard] = None


async def get_dashboard() -> HookMonitoringDashboard:
    """Get the global dashboard instance."""
    global _dashboard
    if _dashboard is None:
        _dashboard = HookMonitoringDashboard()
        await _dashboard.start_monitoring()
    return _dashboard


async def shutdown_dashboard():
    """Shutdown the global dashboard instance."""
    global _dashboard
    if _dashboard:
        await _dashboard.stop_monitoring()
        _dashboard = None