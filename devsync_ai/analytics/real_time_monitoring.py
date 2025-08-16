"""
Real-Time Monitoring System for JIRA Agent Hooks.

This module provides comprehensive real-time monitoring, alerting, and
performance tracking for the hook system with WebSocket-based dashboards.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import statistics
import psutil
import time
import uuid
from collections import defaultdict, deque

from fastapi import WebSocket, WebSocketDisconnect
import websockets

from devsync_ai.analytics.monitoring_data_manager import (
    get_monitoring_data_manager,
    MonitoringDataManager,
    HookAlert,
    AlertSeverity,
    HealthStatus,
    SystemHealthSnapshot,
    WebhookProcessingStat
)
from devsync_ai.core.agent_hooks import HookExecutionResult, HookStatus


logger = logging.getLogger(__name__)


class EventType(Enum):
    """Real-time event types."""
    HOOK_EXECUTION = "hook_execution"
    PERFORMANCE_UPDATE = "performance_update"
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_RESOLVED = "alert_resolved"
    SYSTEM_HEALTH_UPDATE = "system_health_update"
    WEBHOOK_PROCESSED = "webhook_processed"
    METRIC_THRESHOLD_BREACH = "metric_threshold_breach"


@dataclass
class RealTimeEvent:
    """Real-time event for broadcasting."""
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    severity: str = "info"
    source: str = "system"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class PerformanceThresholds:
    """Performance thresholds for alerting."""
    execution_time_warning_ms: float = 2000.0
    execution_time_critical_ms: float = 5000.0
    success_rate_warning: float = 0.95
    success_rate_critical: float = 0.85
    error_rate_warning: float = 0.05
    error_rate_critical: float = 0.15
    cpu_warning: float = 70.0
    cpu_critical: float = 90.0
    memory_warning: float = 80.0
    memory_critical: float = 95.0
    response_time_warning_ms: float = 2000.0
    response_time_critical_ms: float = 5000.0


@dataclass
class AlertRule:
    """Alert rule configuration."""
    rule_id: str
    name: str
    description: str
    metric_path: str  # e.g., "hook.execution_time_ms", "system.cpu_usage"
    threshold_value: float
    comparison_operator: str  # "gt", "lt", "eq", "gte", "lte"
    severity: AlertSeverity
    enabled: bool = True
    team_filter: Optional[str] = None
    hook_type_filter: Optional[str] = None
    cooldown_minutes: int = 5  # Minimum time between alerts
    last_triggered: Optional[datetime] = None


@dataclass
class MetricSnapshot:
    """Snapshot of metrics at a point in time."""
    timestamp: datetime
    hook_metrics: Dict[str, Dict[str, Any]]
    system_metrics: Dict[str, Any]
    team_metrics: Dict[str, Dict[str, Any]]
    webhook_metrics: Dict[str, Dict[str, Any]]


class RealTimeMonitoringSystem:
    """
    Comprehensive real-time monitoring system for JIRA Agent Hooks.
    
    Provides real-time event streaming, performance monitoring, alerting,
    and dashboard data for WebSocket clients.
    """
    
    def __init__(self):
        """Initialize the real-time monitoring system."""
        self.active_connections: Set[WebSocket] = set()
        self.event_subscribers: Dict[EventType, Set[Callable]] = defaultdict(set)
        self.recent_events: deque = deque(maxlen=1000)  # Keep last 1000 events
        
        # Performance tracking
        self.performance_history: deque = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        self.hook_performance_cache: Dict[str, Dict[str, Any]] = {}
        self.team_performance_cache: Dict[str, Dict[str, Any]] = {}
        self.webhook_performance_cache: Dict[str, Dict[str, Any]] = {}
        
        # Alerting
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, HookAlert] = {}
        self.thresholds = PerformanceThresholds()
        
        # System state
        self.current_system_health: Optional[SystemHealthSnapshot] = None
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.data_manager: Optional[MonitoringDataManager] = None
        
        # Initialize default alert rules
        self._initialize_default_alert_rules()
    
    async def initialize(self):
        """Initialize the monitoring system."""
        if self.monitoring_active:
            return
        
        self.data_manager = await get_monitoring_data_manager()
        await self._start_monitoring()
        
        logger.info("Real-time monitoring system initialized")
    
    async def shutdown(self):
        """Shutdown the monitoring system."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Close all WebSocket connections
        for connection in self.active_connections.copy():
            try:
                await connection.close()
            except Exception:
                pass
        
        logger.info("Real-time monitoring system shutdown")
    
    def _initialize_default_alert_rules(self):
        """Initialize default alert rules."""
        default_rules = [
            AlertRule(
                rule_id="hook_execution_time_warning",
                name="High Hook Execution Time",
                description="Hook execution time exceeds warning threshold",
                metric_path="hook.execution_time_ms",
                threshold_value=self.thresholds.execution_time_warning_ms,
                comparison_operator="gt",
                severity=AlertSeverity.WARNING
            ),
            AlertRule(
                rule_id="hook_execution_time_critical",
                name="Critical Hook Execution Time",
                description="Hook execution time exceeds critical threshold",
                metric_path="hook.execution_time_ms",
                threshold_value=self.thresholds.execution_time_critical_ms,
                comparison_operator="gt",
                severity=AlertSeverity.CRITICAL
            ),
            AlertRule(
                rule_id="hook_success_rate_warning",
                name="Low Hook Success Rate",
                description="Hook success rate below warning threshold",
                metric_path="hook.success_rate",
                threshold_value=self.thresholds.success_rate_warning,
                comparison_operator="lt",
                severity=AlertSeverity.WARNING
            ),
            AlertRule(
                rule_id="hook_success_rate_critical",
                name="Critical Hook Success Rate",
                description="Hook success rate below critical threshold",
                metric_path="hook.success_rate",
                threshold_value=self.thresholds.success_rate_critical,
                comparison_operator="lt",
                severity=AlertSeverity.CRITICAL
            ),
            AlertRule(
                rule_id="system_cpu_warning",
                name="High CPU Usage",
                description="System CPU usage exceeds warning threshold",
                metric_path="system.cpu_usage",
                threshold_value=self.thresholds.cpu_warning,
                comparison_operator="gt",
                severity=AlertSeverity.WARNING
            ),
            AlertRule(
                rule_id="system_cpu_critical",
                name="Critical CPU Usage",
                description="System CPU usage exceeds critical threshold",
                metric_path="system.cpu_critical",
                threshold_value=self.thresholds.cpu_critical,
                comparison_operator="gt",
                severity=AlertSeverity.CRITICAL
            ),
            AlertRule(
                rule_id="system_memory_warning",
                name="High Memory Usage",
                description="System memory usage exceeds warning threshold",
                metric_path="system.memory_usage",
                threshold_value=self.thresholds.memory_warning,
                comparison_operator="gt",
                severity=AlertSeverity.WARNING
            ),
            AlertRule(
                rule_id="webhook_response_time_warning",
                name="Slow Webhook Processing",
                description="Webhook processing time exceeds warning threshold",
                metric_path="webhook.processing_time_ms",
                threshold_value=self.thresholds.response_time_warning_ms,
                comparison_operator="gt",
                severity=AlertSeverity.WARNING
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.rule_id] = rule
    
    async def _start_monitoring(self):
        """Start the monitoring background task."""
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Update performance caches
                await self._update_performance_caches()
                
                # Check alert conditions
                await self._check_alert_conditions()
                
                # Broadcast updates to connected clients
                await self._broadcast_system_update()
                
                # Clean up old data periodically
                if datetime.now().minute % 10 == 0:  # Every 10 minutes
                    await self._cleanup_old_data()
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Wait longer on error
    
    async def _collect_system_metrics(self):
        """Collect current system metrics."""
        try:
            # Get system health from data manager
            self.current_system_health = await self.data_manager.get_system_health_metrics()
            
            # Add system resource metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            self.current_system_health.cpu_usage = cpu_usage
            self.current_system_health.memory_usage = memory.percent
            
            # Store in history
            self.performance_history.append({
                'timestamp': self.current_system_health.timestamp,
                'cpu_usage': cpu_usage,
                'memory_usage': memory.percent,
                'executions_per_minute': self.current_system_health.executions_per_minute,
                'avg_execution_time_ms': self.current_system_health.avg_execution_time_ms,
                'success_rate': self.current_system_health.overall_success_rate,
                'error_count': self.current_system_health.error_count_last_hour,
                'health_status': self.current_system_health.health_status.value
            })
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}", exc_info=True)
    
    async def _update_performance_caches(self):
        """Update performance caches for hooks, teams, and webhooks."""
        try:
            now = datetime.now(timezone.utc)
            one_hour_ago = now - timedelta(hours=1)
            
            # Update webhook performance cache
            webhook_metrics = await self.data_manager.get_webhook_performance_metrics(
                one_hour_ago, now
            )
            
            for metric in webhook_metrics:
                self.webhook_performance_cache[metric['webhook_type']] = metric
            
        except Exception as e:
            logger.error(f"Failed to update performance caches: {e}", exc_info=True)
    
    async def _check_alert_conditions(self):
        """Check all alert rules against current metrics."""
        if not self.current_system_health:
            return
        
        try:
            current_time = datetime.now(timezone.utc)
            
            # Check system-level alerts
            system_metrics = {
                'cpu_usage': self.current_system_health.cpu_usage,
                'memory_usage': self.current_system_health.memory_usage,
                'avg_execution_time_ms': self.current_system_health.avg_execution_time_ms,
                'error_rate': 1.0 - self.current_system_health.overall_success_rate
            }
            
            for rule in self.alert_rules.values():
                if not rule.enabled:
                    continue
                
                # Check cooldown
                if (rule.last_triggered and 
                    (current_time - rule.last_triggered).total_seconds() < rule.cooldown_minutes * 60):
                    continue
                
                # Get metric value
                metric_value = self._get_metric_value(rule.metric_path, system_metrics)
                if metric_value is None:
                    continue
                
                # Check threshold
                if self._check_threshold(metric_value, rule.threshold_value, rule.comparison_operator):
                    await self._trigger_alert(rule, metric_value, current_time)
            
        except Exception as e:
            logger.error(f"Failed to check alert conditions: {e}", exc_info=True)
    
    def _get_metric_value(self, metric_path: str, metrics: Dict[str, Any]) -> Optional[float]:
        """Get metric value from metrics dictionary using dot notation."""
        try:
            parts = metric_path.split('.')
            value = metrics
            
            for part in parts[1:]:  # Skip the first part (system/hook/webhook)
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
            
            return float(value) if value is not None else None
            
        except (ValueError, TypeError, KeyError):
            return None
    
    def _check_threshold(self, value: float, threshold: float, operator: str) -> bool:
        """Check if value meets threshold condition."""
        if operator == "gt":
            return value > threshold
        elif operator == "lt":
            return value < threshold
        elif operator == "gte":
            return value >= threshold
        elif operator == "lte":
            return value <= threshold
        elif operator == "eq":
            return value == threshold
        return False
    
    async def _trigger_alert(self, rule: AlertRule, metric_value: float, current_time: datetime):
        """Trigger an alert based on rule violation."""
        try:
            alert_id = f"{rule.rule_id}_{int(current_time.timestamp())}"
            
            # Check if similar alert already exists
            existing_alert_key = f"{rule.rule_id}_{rule.hook_type_filter or 'system'}"
            if existing_alert_key in self.active_alerts:
                # Update existing alert
                existing_alert = self.active_alerts[existing_alert_key]
                existing_alert.metric_value = metric_value
                existing_alert.triggered_at = current_time
            else:
                # Create new alert
                alert = HookAlert(
                    alert_id=alert_id,
                    rule_id=rule.rule_id,
                    hook_id=None,  # System-level alert
                    team_id=rule.team_filter,
                    severity=rule.severity,
                    title=rule.name,
                    description=f"{rule.description}. Current value: {metric_value:.2f}, Threshold: {rule.threshold_value:.2f}",
                    metric_value=metric_value,
                    threshold_value=rule.threshold_value,
                    triggered_at=current_time
                )
                
                # Store in database
                await self.data_manager.create_alert(alert)
                
                # Cache the alert
                self.active_alerts[existing_alert_key] = alert
                
                # Broadcast alert event
                await self._broadcast_event(RealTimeEvent(
                    event_type=EventType.ALERT_TRIGGERED,
                    timestamp=current_time,
                    data={
                        'alert_id': alert_id,
                        'rule_id': rule.rule_id,
                        'severity': rule.severity.value,
                        'title': rule.name,
                        'description': alert.description,
                        'metric_value': metric_value,
                        'threshold_value': rule.threshold_value
                    },
                    severity=rule.severity.value.lower()
                ))
            
            # Update rule last triggered time
            rule.last_triggered = current_time
            
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}", exc_info=True)
    
    async def _broadcast_system_update(self):
        """Broadcast system update to all connected clients."""
        if not self.active_connections or not self.current_system_health:
            return
        
        try:
            # Prepare system update data
            update_data = {
                'type': 'system_update',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'system_health': {
                    'timestamp': self.current_system_health.timestamp.isoformat(),
                    'total_hooks': self.current_system_health.total_hooks,
                    'active_hooks': self.current_system_health.active_hooks,
                    'total_executions': self.current_system_health.total_executions,
                    'overall_success_rate': self.current_system_health.overall_success_rate,
                    'avg_execution_time_ms': self.current_system_health.avg_execution_time_ms,
                    'executions_per_minute': self.current_system_health.executions_per_minute,
                    'error_count_last_hour': self.current_system_health.error_count_last_hour,
                    'health_status': self.current_system_health.health_status.value,
                    'alerts_count': self.current_system_health.alerts_count,
                    'cpu_usage': self.current_system_health.cpu_usage,
                    'memory_usage': self.current_system_health.memory_usage,
                    'queue_depth': self.current_system_health.queue_depth
                },
                'performance_history': list(self.performance_history)[-60:],  # Last 5 minutes
                'webhook_metrics': dict(self.webhook_performance_cache),
                'active_alerts_count': len(self.active_alerts)
            }
            
            await self._broadcast_to_connections(update_data)
            
        except Exception as e:
            logger.error(f"Failed to broadcast system update: {e}", exc_info=True)
    
    async def _broadcast_event(self, event: RealTimeEvent):
        """Broadcast a real-time event to all subscribers."""
        try:
            # Add to recent events
            self.recent_events.append(event)
            
            # Notify event subscribers
            subscribers = self.event_subscribers.get(event.event_type, set())
            for subscriber in subscribers:
                try:
                    if asyncio.iscoroutinefunction(subscriber):
                        await subscriber(event)
                    else:
                        subscriber(event)
                except Exception as e:
                    logger.error(f"Error notifying event subscriber: {e}")
            
            # Broadcast to WebSocket connections
            event_data = {
                'type': 'event',
                'event_type': event.event_type.value,
                'timestamp': event.timestamp.isoformat(),
                'data': event.data,
                'severity': event.severity,
                'source': event.source,
                'event_id': event.event_id
            }
            
            await self._broadcast_to_connections(event_data)
            
        except Exception as e:
            logger.error(f"Failed to broadcast event: {e}", exc_info=True)
    
    async def _broadcast_to_connections(self, data: Dict[str, Any]):
        """Broadcast data to all WebSocket connections."""
        if not self.active_connections:
            return
        
        message = json.dumps(data)
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.add(connection)
        
        # Remove disconnected connections
        self.active_connections -= disconnected
    
    async def _cleanup_old_data(self):
        """Clean up old data periodically."""
        try:
            # Clean up resolved alerts older than 1 hour
            current_time = datetime.now(timezone.utc)
            one_hour_ago = current_time - timedelta(hours=1)
            
            alerts_to_remove = []
            for key, alert in self.active_alerts.items():
                if alert.resolved_at and alert.resolved_at < one_hour_ago:
                    alerts_to_remove.append(key)
            
            for key in alerts_to_remove:
                del self.active_alerts[key]
            
            logger.debug(f"Cleaned up {len(alerts_to_remove)} old alerts")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}", exc_info=True)
    
    # Public API methods
    
    async def record_hook_execution(self, execution_result: HookExecutionResult):
        """Record a hook execution and trigger real-time updates."""
        try:
            # Record in database
            await self.data_manager.record_hook_execution(execution_result)
            
            # Update hook performance cache
            hook_id = execution_result.hook_id
            if hook_id not in self.hook_performance_cache:
                self.hook_performance_cache[hook_id] = {
                    'hook_id': hook_id,
                    'hook_type': execution_result.hook_type,
                    'team_id': execution_result.metadata.get('team_id', 'unknown'),
                    'total_executions': 0,
                    'successful_executions': 0,
                    'failed_executions': 0,
                    'avg_execution_time_ms': 0.0,
                    'success_rate': 0.0,
                    'last_execution': None
                }
            
            cache = self.hook_performance_cache[hook_id]
            cache['total_executions'] += 1
            cache['last_execution'] = execution_result.started_at.isoformat()
            
            if execution_result.status == HookStatus.SUCCESS:
                cache['successful_executions'] += 1
            else:
                cache['failed_executions'] += 1
            
            cache['success_rate'] = cache['successful_executions'] / cache['total_executions']
            
            if execution_result.execution_time_ms:
                # Update average execution time
                current_avg = cache['avg_execution_time_ms']
                total = cache['total_executions']
                cache['avg_execution_time_ms'] = (
                    (current_avg * (total - 1) + execution_result.execution_time_ms) / total
                )
            
            # Broadcast hook execution event
            await self._broadcast_event(RealTimeEvent(
                event_type=EventType.HOOK_EXECUTION,
                timestamp=execution_result.started_at,
                data={
                    'hook_id': execution_result.hook_id,
                    'execution_id': execution_result.execution_id,
                    'hook_type': execution_result.hook_type,
                    'team_id': execution_result.metadata.get('team_id', 'unknown'),
                    'status': execution_result.status.value,
                    'execution_time_ms': execution_result.execution_time_ms,
                    'notification_sent': execution_result.notification_sent,
                    'event_type': execution_result.metadata.get('event_type', 'unknown')
                },
                severity="error" if execution_result.status != HookStatus.SUCCESS else "info"
            ))
            
        except Exception as e:
            logger.error(f"Failed to record hook execution: {e}", exc_info=True)
    
    async def record_webhook_processing(self, stat: WebhookProcessingStat):
        """Record webhook processing statistics."""
        try:
            # Record in database
            await self.data_manager.record_webhook_processing(stat)
            
            # Broadcast webhook processing event
            await self._broadcast_event(RealTimeEvent(
                event_type=EventType.WEBHOOK_PROCESSED,
                timestamp=stat.timestamp,
                data={
                    'webhook_type': stat.webhook_type,
                    'endpoint': stat.endpoint,
                    'method': stat.method,
                    'status_code': stat.status_code,
                    'processing_time_ms': stat.processing_time_ms,
                    'hook_triggered': stat.hook_triggered,
                    'hook_count': stat.hook_count,
                    'team_id': stat.team_id,
                    'event_type': stat.event_type
                },
                severity="error" if stat.status_code >= 400 else "info"
            ))
            
        except Exception as e:
            logger.error(f"Failed to record webhook processing: {e}", exc_info=True)
    
    async def connect_websocket(self, websocket: WebSocket):
        """Connect a new WebSocket client."""
        try:
            await websocket.accept()
            self.active_connections.add(websocket)
            
            # Send initial data
            initial_data = {
                'type': 'initial_data',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'system_health': asdict(self.current_system_health) if self.current_system_health else {},
                'hook_metrics': dict(self.hook_performance_cache),
                'webhook_metrics': dict(self.webhook_performance_cache),
                'recent_events': [
                    {
                        'event_type': event.event_type.value,
                        'timestamp': event.timestamp.isoformat(),
                        'data': event.data,
                        'severity': event.severity,
                        'event_id': event.event_id
                    }
                    for event in list(self.recent_events)[-50:]  # Last 50 events
                ],
                'active_alerts': [
                    asdict(alert) for alert in self.active_alerts.values()
                ]
            }
            
            await websocket.send_text(json.dumps(initial_data))
            
            logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket client: {e}")
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    async def disconnect_websocket(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")
    
    def subscribe_to_events(self, event_type: EventType, callback: Callable):
        """Subscribe to real-time events."""
        self.event_subscribers[event_type].add(callback)
    
    def unsubscribe_from_events(self, event_type: EventType, callback: Callable):
        """Unsubscribe from real-time events."""
        self.event_subscribers[event_type].discard(callback)
    
    async def get_dashboard_data(
        self,
        time_range: str = "1h",
        team_filter: Optional[str] = None,
        hook_type_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        try:
            # Parse time range
            if time_range == "1h":
                cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            elif time_range == "24h":
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            elif time_range == "7d":
                cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            else:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            
            # Filter performance history
            filtered_history = [
                h for h in self.performance_history 
                if h['timestamp'] > cutoff
            ]
            
            # Filter hook metrics
            filtered_hooks = dict(self.hook_performance_cache)
            if team_filter:
                filtered_hooks = {
                    k: v for k, v in filtered_hooks.items() 
                    if v.get('team_id') == team_filter
                }
            if hook_type_filter:
                filtered_hooks = {
                    k: v for k, v in filtered_hooks.items() 
                    if v.get('hook_type') == hook_type_filter
                }
            
            return {
                'system_overview': asdict(self.current_system_health) if self.current_system_health else {},
                'hook_metrics': filtered_hooks,
                'webhook_metrics': dict(self.webhook_performance_cache),
                'performance_trends': {
                    'timestamps': [h['timestamp'].isoformat() for h in filtered_history],
                    'cpu_usage': [h['cpu_usage'] for h in filtered_history],
                    'memory_usage': [h['memory_usage'] for h in filtered_history],
                    'executions_per_minute': [h['executions_per_minute'] for h in filtered_history],
                    'avg_execution_time_ms': [h['avg_execution_time_ms'] for h in filtered_history],
                    'success_rates': [h['success_rate'] for h in filtered_history],
                    'error_counts': [h['error_count'] for h in filtered_history]
                },
                'alerts': [
                    asdict(alert) for alert in self.active_alerts.values()
                    if not alert.resolved_at
                ],
                'recent_events': [
                    {
                        'event_type': event.event_type.value,
                        'timestamp': event.timestamp.isoformat(),
                        'data': event.data,
                        'severity': event.severity
                    }
                    for event in list(self.recent_events)
                    if event.timestamp > cutoff
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}", exc_info=True)
            return {'error': f'Failed to get dashboard data: {str(e)}'}


# Global monitoring system instance
_monitoring_system: Optional[RealTimeMonitoringSystem] = None


async def get_monitoring_system() -> RealTimeMonitoringSystem:
    """Get the global monitoring system instance."""
    global _monitoring_system
    if _monitoring_system is None:
        _monitoring_system = RealTimeMonitoringSystem()
        await _monitoring_system.initialize()
    return _monitoring_system


async def shutdown_monitoring_system():
    """Shutdown the global monitoring system instance."""
    global _monitoring_system
    if _monitoring_system:
        await _monitoring_system.shutdown()
        _monitoring_system = None