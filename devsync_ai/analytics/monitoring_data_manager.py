"""
Monitoring Data Manager for JIRA Agent Hooks.

This module provides comprehensive data management for hook execution tracking,
performance metrics, business analytics, and system health monitoring.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from devsync_ai.database.connection import get_database
from devsync_ai.core.agent_hooks import HookExecutionResult, HookStatus


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """System health status levels."""
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"


@dataclass
class HookExecutionRecord:
    """Hook execution record for database storage."""
    hook_id: str
    execution_id: str
    hook_type: str
    team_id: str
    event_type: str
    event_id: Optional[str]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    execution_time_ms: Optional[float]
    notification_sent: bool
    notification_result: Optional[Dict[str, Any]]
    errors: List[str]
    metadata: Dict[str, Any]


@dataclass
class HookPerformanceMetrics:
    """Aggregated hook performance metrics."""
    hook_id: str
    hook_type: str
    team_id: str
    time_bucket: datetime
    total_executions: int
    successful_executions: int
    failed_executions: int
    avg_execution_time_ms: float
    min_execution_time_ms: float
    max_execution_time_ms: float
    p95_execution_time_ms: float
    success_rate: float
    error_rate: float
    throughput_per_hour: float


@dataclass
class BusinessMetric:
    """Business impact metric."""
    team_id: str
    metric_type: str
    metric_value: float
    time_bucket: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealthSnapshot:
    """System health snapshot."""
    timestamp: datetime
    total_hooks: int
    active_hooks: int
    total_executions: int
    overall_success_rate: float
    avg_execution_time_ms: float
    executions_per_minute: float
    error_count_last_hour: int
    health_status: HealthStatus
    alerts_count: int
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    queue_depth: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HookAlert:
    """Hook alert record."""
    alert_id: str
    rule_id: str
    hook_id: Optional[str]
    team_id: Optional[str]
    severity: AlertSeverity
    title: str
    description: str
    metric_value: float
    threshold_value: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebhookProcessingStat:
    """Webhook processing statistics."""
    webhook_type: str
    endpoint: str
    method: str
    status_code: int
    processing_time_ms: float
    payload_size_bytes: Optional[int]
    team_id: Optional[str]
    event_type: Optional[str]
    hook_triggered: bool
    hook_count: int
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class MonitoringDataManager:
    """
    Comprehensive data manager for hook monitoring and analytics.
    
    Provides methods for storing, retrieving, and analyzing hook execution data,
    performance metrics, business metrics, and system health information.
    """
    
    def __init__(self):
        """Initialize the monitoring data manager."""
        self._db = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the data manager."""
        if self._initialized:
            return
        
        self._db = await get_database()
        self._initialized = True
        logger.info("Monitoring Data Manager initialized")
    
    async def record_hook_execution(self, execution_result: HookExecutionResult) -> bool:
        """
        Record a hook execution in the database.
        
        Args:
            execution_result: Hook execution result
            
        Returns:
            Success status
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Prepare execution record
            record_data = {
                'hook_id': execution_result.hook_id,
                'execution_id': execution_result.execution_id,
                'hook_type': execution_result.hook_type,
                'team_id': execution_result.metadata.get('team_id', 'unknown'),
                'event_type': execution_result.metadata.get('event_type', 'unknown'),
                'event_id': execution_result.event_id,
                'status': execution_result.status.value,
                'started_at': execution_result.started_at.isoformat(),
                'completed_at': execution_result.completed_at.isoformat() if execution_result.completed_at else None,
                'execution_time_ms': execution_result.execution_time_ms,
                'notification_sent': execution_result.notification_sent,
                'notification_result': execution_result.notification_result,
                'errors': execution_result.errors,
                'metadata': execution_result.metadata
            }
            
            # Insert into database
            await self._db.insert('hook_executions', record_data)
            
            logger.debug(f"Recorded hook execution: {execution_result.execution_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record hook execution: {e}", exc_info=True)
            return False
    
    async def get_hook_performance_metrics(
        self,
        hook_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[HookPerformanceMetrics]:
        """
        Get performance metrics for a specific hook.
        
        Args:
            hook_id: Hook identifier
            start_time: Start time for metrics
            end_time: End time for metrics
            
        Returns:
            Hook performance metrics
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Use the database function to get performance summary
            result = await self._db.execute_rpc(
                'get_hook_performance_summary',
                {
                    'hook_id_param': hook_id,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat()
                }
            )
            
            if not result:
                return None
            
            data = result[0]
            
            return HookPerformanceMetrics(
                hook_id=data['hook_id'],
                hook_type=data['hook_type'],
                team_id=data['team_id'],
                time_bucket=start_time,  # Using start_time as representative bucket
                total_executions=data['total_executions'],
                successful_executions=data['successful_executions'],
                failed_executions=data['failed_executions'],
                avg_execution_time_ms=data['avg_execution_time_ms'] or 0.0,
                min_execution_time_ms=0.0,  # Would need separate query for min/max
                max_execution_time_ms=0.0,
                p95_execution_time_ms=data['p95_execution_time_ms'] or 0.0,
                success_rate=data['success_rate'] or 0.0,
                error_rate=1.0 - (data['success_rate'] or 0.0),
                throughput_per_hour=data['throughput_per_hour'] or 0.0
            )
            
        except Exception as e:
            logger.error(f"Failed to get hook performance metrics: {e}", exc_info=True)
            return None
    
    async def get_team_productivity_metrics(
        self,
        team_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Get productivity metrics for a team.
        
        Args:
            team_id: Team identifier
            start_time: Start time for metrics
            end_time: End time for metrics
            
        Returns:
            Team productivity metrics
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Use the database function to get team productivity metrics
            result = await self._db.execute_rpc(
                'get_team_productivity_metrics',
                {
                    'team_id_param': team_id,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat()
                }
            )
            
            if not result:
                return None
            
            data = result[0]
            
            return {
                'team_id': data['team_id'],
                'total_hooks': data['total_hooks'],
                'active_hooks': data['active_hooks'],
                'total_executions': data['total_executions'],
                'avg_response_time_ms': data['avg_response_time_ms'] or 0.0,
                'productivity_score': data['productivity_score'] or 0.0,
                'notification_delivery_rate': data['notification_delivery_rate'] or 0.0,
                'blocked_ticket_resolution_improvement': data['blocked_ticket_resolution_improvement'] or 0.0,
                'collaboration_index': min(100, (data['productivity_score'] or 0.0) * 1.1),
                'sprint_velocity_improvement': max(0, ((data['productivity_score'] or 0.0) - 70) / 3)
            }
            
        except Exception as e:
            logger.error(f"Failed to get team productivity metrics: {e}", exc_info=True)
            return None
    
    async def get_system_health_metrics(self) -> SystemHealthSnapshot:
        """
        Get current system health metrics.
        
        Returns:
            System health snapshot
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Use the database function to get current system health
            result = await self._db.execute_rpc('get_current_system_health')
            
            if not result:
                return self._create_empty_health_snapshot()
            
            data = result[0]
            
            # Determine health status
            health_status = HealthStatus(data['health_status'])
            
            # Get active alerts count
            alerts_result = await self._db.select(
                'hook_alerts',
                filters={'resolved_at': {'is': 'null'}},
                select_fields='count(*)'
            )
            alerts_count = len(alerts_result) if alerts_result else 0
            
            return SystemHealthSnapshot(
                timestamp=datetime.now(timezone.utc),
                total_hooks=data['total_hooks'] or 0,
                active_hooks=data['active_hooks'] or 0,
                total_executions=data['executions_last_hour'] or 0,
                overall_success_rate=data['success_rate_last_hour'] or 0.0,
                avg_execution_time_ms=data['avg_execution_time_ms'] or 0.0,
                executions_per_minute=(data['executions_last_hour'] or 0) / 60.0,
                error_count_last_hour=data['error_count_last_hour'] or 0,
                health_status=health_status,
                alerts_count=alerts_count
            )
            
        except Exception as e:
            logger.error(f"Failed to get system health metrics: {e}", exc_info=True)
            return self._create_empty_health_snapshot()
    
    def _create_empty_health_snapshot(self) -> SystemHealthSnapshot:
        """Create an empty health snapshot for error cases."""
        return SystemHealthSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_hooks=0,
            active_hooks=0,
            total_executions=0,
            overall_success_rate=0.0,
            avg_execution_time_ms=0.0,
            executions_per_minute=0.0,
            error_count_last_hour=0,
            health_status=HealthStatus.ERROR,
            alerts_count=0
        )
    
    async def store_business_metric(self, metric: BusinessMetric) -> bool:
        """
        Store a business metric.
        
        Args:
            metric: Business metric to store
            
        Returns:
            Success status
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            metric_data = {
                'team_id': metric.team_id,
                'metric_type': metric.metric_type,
                'metric_value': metric.metric_value,
                'time_bucket': metric.time_bucket.isoformat(),
                'metadata': metric.metadata
            }
            
            # Use upsert to handle duplicates
            await self._db.upsert('business_metrics', metric_data)
            
            logger.debug(f"Stored business metric: {metric.metric_type} for team {metric.team_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store business metric: {e}", exc_info=True)
            return False
    
    async def create_alert(self, alert: HookAlert) -> bool:
        """
        Create a new alert.
        
        Args:
            alert: Alert to create
            
        Returns:
            Success status
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            alert_data = {
                'alert_id': alert.alert_id,
                'rule_id': alert.rule_id,
                'hook_id': alert.hook_id,
                'team_id': alert.team_id,
                'severity': alert.severity.value,
                'title': alert.title,
                'description': alert.description,
                'metric_value': alert.metric_value,
                'threshold_value': alert.threshold_value,
                'triggered_at': alert.triggered_at.isoformat(),
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                'acknowledged': alert.acknowledged,
                'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                'acknowledged_by': alert.acknowledged_by,
                'metadata': alert.metadata
            }
            
            await self._db.insert('hook_alerts', alert_data)
            
            logger.info(f"Created alert: {alert.alert_id} - {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}", exc_info=True)
            return False
    
    async def get_active_alerts(
        self,
        severity_filter: Optional[AlertSeverity] = None,
        team_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[HookAlert]:
        """
        Get active alerts with optional filtering.
        
        Args:
            severity_filter: Filter by alert severity
            team_filter: Filter by team ID
            limit: Maximum number of alerts to return
            
        Returns:
            List of active alerts
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            filters = {'resolved_at': {'is': 'null'}}
            
            if severity_filter:
                filters['severity'] = severity_filter.value
            
            if team_filter:
                filters['team_id'] = team_filter
            
            results = await self._db.select(
                'hook_alerts',
                filters=filters,
                order_by='triggered_at',
                order_desc=True,
                limit=limit
            )
            
            alerts = []
            for result in results:
                alert = HookAlert(
                    alert_id=result['alert_id'],
                    rule_id=result['rule_id'],
                    hook_id=result['hook_id'],
                    team_id=result['team_id'],
                    severity=AlertSeverity(result['severity']),
                    title=result['title'],
                    description=result['description'],
                    metric_value=result['metric_value'],
                    threshold_value=result['threshold_value'],
                    triggered_at=datetime.fromisoformat(result['triggered_at']),
                    resolved_at=datetime.fromisoformat(result['resolved_at']) if result['resolved_at'] else None,
                    acknowledged=result['acknowledged'],
                    acknowledged_at=datetime.fromisoformat(result['acknowledged_at']) if result['acknowledged_at'] else None,
                    acknowledged_by=result['acknowledged_by'],
                    metadata=result['metadata'] or {}
                )
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}", exc_info=True)
            return []
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert identifier
            acknowledged_by: User who acknowledged the alert
            
        Returns:
            Success status
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            update_data = {
                'acknowledged': True,
                'acknowledged_at': datetime.now(timezone.utc).isoformat(),
                'acknowledged_by': acknowledged_by
            }
            
            await self._db.update(
                'hook_alerts',
                update_data,
                {'alert_id': alert_id}
            )
            
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}", exc_info=True)
            return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert.
        
        Args:
            alert_id: Alert identifier
            
        Returns:
            Success status
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            update_data = {
                'resolved_at': datetime.now(timezone.utc).isoformat()
            }
            
            await self._db.update(
                'hook_alerts',
                update_data,
                {'alert_id': alert_id}
            )
            
            logger.info(f"Alert {alert_id} resolved")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}", exc_info=True)
            return False
    
    async def record_webhook_processing(self, stat: WebhookProcessingStat) -> bool:
        """
        Record webhook processing statistics.
        
        Args:
            stat: Webhook processing statistics
            
        Returns:
            Success status
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            stat_data = {
                'webhook_type': stat.webhook_type,
                'endpoint': stat.endpoint,
                'method': stat.method,
                'status_code': stat.status_code,
                'processing_time_ms': stat.processing_time_ms,
                'payload_size_bytes': stat.payload_size_bytes,
                'team_id': stat.team_id,
                'event_type': stat.event_type,
                'hook_triggered': stat.hook_triggered,
                'hook_count': stat.hook_count,
                'timestamp': stat.timestamp.isoformat(),
                'metadata': stat.metadata
            }
            
            await self._db.insert('webhook_processing_stats', stat_data)
            
            logger.debug(f"Recorded webhook processing stat: {stat.webhook_type} - {stat.endpoint}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record webhook processing stat: {e}", exc_info=True)
            return False
    
    async def get_webhook_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        webhook_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get webhook performance metrics.
        
        Args:
            start_time: Start time for metrics
            end_time: End time for metrics
            webhook_type: Optional webhook type filter
            
        Returns:
            List of webhook performance metrics
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            filters = {
                'timestamp': {'gte': start_time.isoformat()},
                'timestamp': {'lte': end_time.isoformat()}
            }
            
            if webhook_type:
                filters['webhook_type'] = webhook_type
            
            results = await self._db.select(
                'webhook_processing_stats',
                filters=filters,
                order_by='timestamp',
                order_desc=True
            )
            
            # Group by webhook_type and calculate metrics
            metrics_by_type = {}
            
            for result in results:
                wh_type = result['webhook_type']
                if wh_type not in metrics_by_type:
                    metrics_by_type[wh_type] = {
                        'webhook_type': wh_type,
                        'total_requests': 0,
                        'successful_requests': 0,
                        'failed_requests': 0,
                        'avg_processing_time_ms': 0.0,
                        'hooks_triggered': 0,
                        'processing_times': []
                    }
                
                metrics = metrics_by_type[wh_type]
                metrics['total_requests'] += 1
                
                if 200 <= result['status_code'] < 300:
                    metrics['successful_requests'] += 1
                else:
                    metrics['failed_requests'] += 1
                
                if result['hook_triggered']:
                    metrics['hooks_triggered'] += result['hook_count']
                
                metrics['processing_times'].append(result['processing_time_ms'])
            
            # Calculate averages
            for metrics in metrics_by_type.values():
                if metrics['processing_times']:
                    metrics['avg_processing_time_ms'] = sum(metrics['processing_times']) / len(metrics['processing_times'])
                    metrics['success_rate'] = metrics['successful_requests'] / metrics['total_requests']
                    del metrics['processing_times']  # Remove raw data
            
            return list(metrics_by_type.values())
            
        except Exception as e:
            logger.error(f"Failed to get webhook performance metrics: {e}", exc_info=True)
            return []
    
    async def aggregate_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """
        Aggregate raw execution data into performance metrics.
        
        Args:
            start_time: Start time for aggregation
            end_time: End time for aggregation
            
        Returns:
            Number of metrics processed
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Use the database function to aggregate metrics
            result = await self._db.execute_rpc(
                'aggregate_hook_performance_metrics',
                {
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat()
                }
            )
            
            processed_count = result if isinstance(result, int) else 0
            
            logger.info(f"Aggregated {processed_count} performance metrics")
            return processed_count
            
        except Exception as e:
            logger.error(f"Failed to aggregate performance metrics: {e}", exc_info=True)
            return 0
    
    async def cleanup_old_data(self) -> Dict[str, int]:
        """
        Clean up old monitoring data.
        
        Returns:
            Dictionary of table names and records deleted
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Use the database function to cleanup old records
            results = await self._db.execute_rpc('cleanup_old_monitoring_records')
            
            cleanup_summary = {}
            for result in results:
                cleanup_summary[result['table_name']] = result['records_deleted']
            
            logger.info(f"Cleanup completed: {cleanup_summary}")
            return cleanup_summary
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}", exc_info=True)
            return {}


# Global monitoring data manager instance
_monitoring_data_manager: Optional[MonitoringDataManager] = None


async def get_monitoring_data_manager() -> MonitoringDataManager:
    """Get the global monitoring data manager instance."""
    global _monitoring_data_manager
    if _monitoring_data_manager is None:
        _monitoring_data_manager = MonitoringDataManager()
        await _monitoring_data_manager.initialize()
    return _monitoring_data_manager


async def close_monitoring_data_manager():
    """Close the global monitoring data manager instance."""
    global _monitoring_data_manager
    if _monitoring_data_manager:
        _monitoring_data_manager = None