"""
Hook Analytics Engine for DevSync AI.

This module provides comprehensive analytics, monitoring, and reporting
for JIRA Agent Hooks with performance tracking, health monitoring, and
intelligent alerting capabilities.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import json

from devsync_ai.analytics.analytics_data_manager import get_analytics_data_manager, AnalyticsRecord
from devsync_ai.hooks.hook_registry_manager import get_hook_registry_manager
from devsync_ai.core.agent_hooks import HookExecutionResult, HookStatus


logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"


class HealthStatus(Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"


@dataclass
class HookPerformanceMetrics:
    """Performance metrics for a specific hook."""
    hook_id: str
    hook_type: str
    team_id: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_execution_time_ms: float
    min_execution_time_ms: float
    max_execution_time_ms: float
    success_rate: float
    error_rate: float
    last_execution: Optional[datetime]
    executions_per_hour: float
    health_status: HealthStatus


@dataclass
class SystemHealthMetrics:
    """System-wide health metrics."""
    timestamp: datetime
    total_hooks: int
    active_hooks: int
    total_executions: int
    overall_success_rate: float
    average_execution_time_ms: float
    executions_per_minute: float
    error_count_last_hour: int
    health_status: HealthStatus
    alerts_count: int


@dataclass
class AlertRule:
    """Alert rule configuration."""
    rule_id: str
    name: str
    description: str
    metric_type: str
    threshold_value: float
    comparison_operator: str  # "gt", "lt", "eq", "gte", "lte"
    severity: AlertSeverity
    enabled: bool
    team_filter: Optional[str] = None
    hook_type_filter: Optional[str] = None


@dataclass
class Alert:
    """Generated alert."""
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
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceTrend:
    """Performance trend analysis."""
    metric_name: str
    time_period: str
    trend_direction: str  # "improving", "declining", "stable"
    trend_strength: float  # 0-1
    current_value: float
    previous_value: float
    change_percentage: float
    statistical_significance: float


class HookAnalyticsEngine:
    """
    Comprehensive analytics engine for JIRA Agent Hooks.
    
    Provides execution tracking, performance metrics collection,
    health monitoring, alerting, and data aggregation capabilities.
    """
    
    def __init__(self):
        """Initialize the analytics engine."""
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.performance_cache: Dict[str, HookPerformanceMetrics] = {}
        self.system_health_history: List[SystemHealthMetrics] = []
        
        # Performance thresholds
        self.performance_thresholds = {
            'execution_time_warning_ms': 2000.0,
            'execution_time_critical_ms': 5000.0,
            'success_rate_warning': 0.95,
            'success_rate_critical': 0.85,
            'error_rate_warning': 0.05,
            'error_rate_critical': 0.15,
            'executions_per_hour_min': 1.0
        }
        
        # Initialize default alert rules
        self._initialize_default_alert_rules()
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._aggregation_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self):
        """Initialize the analytics engine."""
        await self._start_background_tasks()
        logger.info("Hook Analytics Engine initialized")
    
    async def shutdown(self):
        """Shutdown the analytics engine."""
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._aggregation_task:
            self._aggregation_task.cancel()
        
        logger.info("Hook Analytics Engine shutdown")
    
    def _initialize_default_alert_rules(self):
        """Initialize default alert rules."""
        default_rules = [
            AlertRule(
                rule_id="execution_time_warning",
                name="High Execution Time",
                description="Hook execution time exceeds warning threshold",
                metric_type="average_execution_time_ms",
                threshold_value=self.performance_thresholds['execution_time_warning_ms'],
                comparison_operator="gt",
                severity=AlertSeverity.WARNING,
                enabled=True
            ),
            AlertRule(
                rule_id="execution_time_critical",
                name="Critical Execution Time",
                description="Hook execution time exceeds critical threshold",
                metric_type="average_execution_time_ms",
                threshold_value=self.performance_thresholds['execution_time_critical_ms'],
                comparison_operator="gt",
                severity=AlertSeverity.CRITICAL,
                enabled=True
            ),
            AlertRule(
                rule_id="success_rate_warning",
                name="Low Success Rate",
                description="Hook success rate below warning threshold",
                metric_type="success_rate",
                threshold_value=self.performance_thresholds['success_rate_warning'],
                comparison_operator="lt",
                severity=AlertSeverity.WARNING,
                enabled=True
            ),
            AlertRule(
                rule_id="success_rate_critical",
                name="Critical Success Rate",
                description="Hook success rate below critical threshold",
                metric_type="success_rate",
                threshold_value=self.performance_thresholds['success_rate_critical'],
                comparison_operator="lt",
                severity=AlertSeverity.CRITICAL,
                enabled=True
            ),
            AlertRule(
                rule_id="error_rate_warning",
                name="High Error Rate",
                description="Hook error rate exceeds warning threshold",
                metric_type="error_rate",
                threshold_value=self.performance_thresholds['error_rate_warning'],
                comparison_operator="gt",
                severity=AlertSeverity.WARNING,
                enabled=True
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.rule_id] = rule
    
    async def record_hook_execution(self, execution_result: HookExecutionResult) -> bool:
        """
        Record hook execution for analytics tracking.
        
        Args:
            execution_result: Hook execution result
            
        Returns:
            Success status
        """
        try:
            data_manager = await get_analytics_data_manager()
            
            # Create analytics record
            record = AnalyticsRecord(
                id=None,  # Will be auto-generated
                timestamp=datetime.now(timezone.utc),
                record_type="hook_execution",
                team_id=execution_result.metadata.get('team_id', 'unknown'),
                data={
                    'hook_id': execution_result.hook_id,
                    'execution_id': execution_result.execution_id,
                    'success': execution_result.status == HookStatus.SUCCESS,
                    'execution_time_ms': execution_result.execution_time_ms,
                    'notification_sent': execution_result.notification_sent,
                    'hook_type': execution_result.hook_type,
                    'event_type': execution_result.metadata.get('event_type', 'unknown'),
                    'event_id': execution_result.event_id
                },
                metadata={
                    'errors': execution_result.errors,
                    'notification_result': execution_result.notification_result,
                    'additional_metadata': execution_result.metadata,
                    'status': execution_result.status.value,
                    'started_at': execution_result.started_at.isoformat(),
                    'completed_at': execution_result.completed_at.isoformat() if execution_result.completed_at else None
                }
            )
            
            # Store the record
            await data_manager.store_record(record)
            
            # Update performance cache
            await self._update_performance_cache(execution_result)
            
            # Check for alerts
            await self._check_execution_alerts(execution_result)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record hook execution: {e}", exc_info=True)
            return False
    
    async def get_hook_performance_metrics(
        self,
        hook_id: str,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Optional[HookPerformanceMetrics]:
        """
        Get performance metrics for a specific hook.
        
        Args:
            hook_id: Hook identifier
            time_range: Time range for metrics calculation
            
        Returns:
            Hook performance metrics
        """
        if not time_range:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=24)
            time_range = (start_time, end_time)
        
        try:
            data_manager = await get_analytics_data_manager()
            
            # Query execution records
            records = await data_manager.query_records(
                record_type="hook_execution",
                start_time=time_range[0],
                end_time=time_range[1]
            )
            
            # Filter records for specific hook
            hook_records = [r for r in records if r.data.get('hook_id') == hook_id]
            
            if not hook_records:
                return None
            
            # Calculate metrics
            total_executions = len(hook_records)
            successful_executions = len([r for r in hook_records if r.data.get('success', False)])
            failed_executions = total_executions - successful_executions
            
            execution_times = [r.data.get('execution_time_ms', 0) for r in hook_records]
            average_execution_time = statistics.mean(execution_times) if execution_times else 0.0
            min_execution_time = min(execution_times) if execution_times else 0.0
            max_execution_time = max(execution_times) if execution_times else 0.0
            
            success_rate = successful_executions / total_executions if total_executions > 0 else 0.0
            error_rate = 1.0 - success_rate
            
            # Calculate executions per hour
            time_span_hours = (time_range[1] - time_range[0]).total_seconds() / 3600
            executions_per_hour = total_executions / time_span_hours if time_span_hours > 0 else 0.0
            
            # Get last execution time
            last_execution = max([r.timestamp for r in hook_records]) if hook_records else None
            
            # Determine health status
            health_status = self._determine_hook_health_status(
                success_rate, average_execution_time, executions_per_hour
            )
            
            # Get hook metadata
            hook_type = hook_records[0].data.get('hook_type', 'unknown')
            team_id = hook_records[0].team_id
            
            metrics = HookPerformanceMetrics(
                hook_id=hook_id,
                hook_type=hook_type,
                team_id=team_id,
                total_executions=total_executions,
                successful_executions=successful_executions,
                failed_executions=failed_executions,
                average_execution_time_ms=average_execution_time,
                min_execution_time_ms=min_execution_time,
                max_execution_time_ms=max_execution_time,
                success_rate=success_rate,
                error_rate=error_rate,
                last_execution=last_execution,
                executions_per_hour=executions_per_hour,
                health_status=health_status
            )
            
            # Cache the metrics
            self.performance_cache[hook_id] = metrics
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get hook performance metrics: {e}", exc_info=True)
            return None
    
    async def get_system_health_metrics(self) -> SystemHealthMetrics:
        """
        Get system-wide health metrics.
        
        Returns:
            System health metrics
        """
        try:
            registry_manager = await get_hook_registry_manager()
            data_manager = await get_analytics_data_manager()
            
            # Get current time
            now = datetime.now(timezone.utc)
            one_hour_ago = now - timedelta(hours=1)
            
            # Get hook registry data
            total_hooks = 0
            active_hooks = 0
            
            if registry_manager:
                hook_statuses = await registry_manager.get_all_hook_statuses()
                total_hooks = len(hook_statuses)
                
                # Count active hooks (executed in last hour)
                for status in hook_statuses:
                    last_exec = status['statistics'].get('last_execution')
                    if last_exec:
                        last_exec_time = datetime.fromisoformat(last_exec)
                        if last_exec_time > one_hour_ago:
                            active_hooks += 1
            
            # Get execution records from last hour
            records = await data_manager.query_records(
                record_type="hook_execution",
                start_time=one_hour_ago,
                end_time=now
            )
            
            total_executions = len(records)
            successful_executions = len([r for r in records if r.data.get('success', False)])
            overall_success_rate = successful_executions / total_executions if total_executions > 0 else 1.0
            
            # Calculate average execution time
            execution_times = [r.data.get('execution_time_ms', 0) for r in records]
            average_execution_time = statistics.mean(execution_times) if execution_times else 0.0
            
            # Calculate executions per minute
            executions_per_minute = total_executions / 60.0
            
            # Count errors
            error_count = len([r for r in records if not r.data.get('success', False)])
            
            # Count active alerts
            alerts_count = len([a for a in self.active_alerts.values() if not a.resolved_at])
            
            # Determine overall health status
            health_status = self._determine_system_health_status(
                overall_success_rate, average_execution_time, error_count, alerts_count
            )
            
            metrics = SystemHealthMetrics(
                timestamp=now,
                total_hooks=total_hooks,
                active_hooks=active_hooks,
                total_executions=total_executions,
                overall_success_rate=overall_success_rate,
                average_execution_time_ms=average_execution_time,
                executions_per_minute=executions_per_minute,
                error_count_last_hour=error_count,
                health_status=health_status,
                alerts_count=alerts_count
            )
            
            # Store in history
            self.system_health_history.append(metrics)
            
            # Keep only last 24 hours of history
            cutoff_time = now - timedelta(hours=24)
            self.system_health_history = [
                m for m in self.system_health_history if m.timestamp > cutoff_time
            ]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get system health metrics: {e}", exc_info=True)
            return SystemHealthMetrics(
                timestamp=datetime.now(timezone.utc),
                total_hooks=0,
                active_hooks=0,
                total_executions=0,
                overall_success_rate=0.0,
                average_execution_time_ms=0.0,
                executions_per_minute=0.0,
                error_count_last_hour=0,
                health_status=HealthStatus.ERROR,
                alerts_count=0
            )
    
    async def generate_performance_report(
        self,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        team_filter: Optional[str] = None,
        hook_type_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        
        Args:
            time_range: Time range for report
            team_filter: Filter by team ID
            hook_type_filter: Filter by hook type
            
        Returns:
            Performance report data
        """
        if not time_range:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=7)
            time_range = (start_time, end_time)
        
        try:
            data_manager = await get_analytics_data_manager()
            
            # Get execution records
            records = await data_manager.query_records(
                record_type="hook_execution",
                team_id=team_filter,
                start_time=time_range[0],
                end_time=time_range[1]
            )
            
            # Filter by hook type if specified
            if hook_type_filter:
                records = [r for r in records if r.data.get('hook_type') == hook_type_filter]
            
            if not records:
                return {"error": "No data available for the specified criteria"}
            
            # Aggregate data by hook
            hook_data = {}
            for record in records:
                hook_id = record.data.get('hook_id')
                if hook_id not in hook_data:
                    hook_data[hook_id] = []
                hook_data[hook_id].append(record)
            
            # Generate hook-level metrics
            hook_metrics = []
            for hook_id, hook_records in hook_data.items():
                metrics = await self._calculate_hook_metrics(hook_records)
                metrics['hook_id'] = hook_id
                hook_metrics.append(metrics)
            
            # Calculate overall statistics
            total_executions = len(records)
            successful_executions = len([r for r in records if r.data.get('success', False)])
            overall_success_rate = successful_executions / total_executions if total_executions > 0 else 0.0
            
            execution_times = [r.data.get('execution_time_ms', 0) for r in records]
            average_execution_time = statistics.mean(execution_times) if execution_times else 0.0
            
            # Generate trends
            trends = await self._calculate_performance_trends(records, time_range)
            
            # Get top performers and underperformers
            sorted_hooks = sorted(hook_metrics, key=lambda x: x['success_rate'], reverse=True)
            top_performers = sorted_hooks[:5]
            underperformers = sorted_hooks[-5:]
            
            report = {
                'report_generated_at': datetime.now(timezone.utc).isoformat(),
                'time_range': {
                    'start': time_range[0].isoformat(),
                    'end': time_range[1].isoformat()
                },
                'filters': {
                    'team_filter': team_filter,
                    'hook_type_filter': hook_type_filter
                },
                'summary': {
                    'total_hooks': len(hook_data),
                    'total_executions': total_executions,
                    'successful_executions': successful_executions,
                    'overall_success_rate': overall_success_rate,
                    'average_execution_time_ms': average_execution_time,
                    'unique_teams': len(set(r.team_id for r in records)),
                    'unique_hook_types': len(set(r.data.get('hook_type', 'unknown') for r in records))
                },
                'hook_metrics': hook_metrics,
                'performance_trends': trends,
                'top_performers': top_performers,
                'underperformers': underperformers,
                'alerts_summary': {
                    'total_alerts': len(self.active_alerts),
                    'critical_alerts': len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.CRITICAL]),
                    'warning_alerts': len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.WARNING])
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}", exc_info=True)
            return {"error": f"Failed to generate report: {str(e)}"}
    
    async def get_active_alerts(
        self,
        severity_filter: Optional[AlertSeverity] = None,
        team_filter: Optional[str] = None
    ) -> List[Alert]:
        """
        Get active alerts with optional filtering.
        
        Args:
            severity_filter: Filter by alert severity
            team_filter: Filter by team ID
            
        Returns:
            List of active alerts
        """
        alerts = [a for a in self.active_alerts.values() if not a.resolved_at]
        
        if severity_filter:
            alerts = [a for a in alerts if a.severity == severity_filter]
        
        if team_filter:
            alerts = [a for a in alerts if a.team_id == team_filter]
        
        return sorted(alerts, key=lambda x: x.triggered_at, reverse=True)
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert identifier
            
        Returns:
            Success status
        """
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info(f"Alert {alert_id} acknowledged")
            return True
        return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert.
        
        Args:
            alert_id: Alert identifier
            
        Returns:
            Success status
        """
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved_at = datetime.now(timezone.utc)
            logger.info(f"Alert {alert_id} resolved")
            return True
        return False
    
    # Helper methods
    async def _update_performance_cache(self, execution_result: HookExecutionResult):
        """Update performance cache with new execution result."""
        hook_id = execution_result.hook_id
        
        # Determine if execution was successful
        is_success = execution_result.status == HookStatus.SUCCESS
        
        # Get or create cached metrics
        if hook_id not in self.performance_cache:
            # Initialize with current execution
            self.performance_cache[hook_id] = HookPerformanceMetrics(
                hook_id=hook_id,
                hook_type=execution_result.hook_type,
                team_id=execution_result.metadata.get('team_id', 'unknown'),
                total_executions=1,
                successful_executions=1 if is_success else 0,
                failed_executions=0 if is_success else 1,
                average_execution_time_ms=execution_result.execution_time_ms,
                min_execution_time_ms=execution_result.execution_time_ms,
                max_execution_time_ms=execution_result.execution_time_ms,
                success_rate=1.0 if is_success else 0.0,
                error_rate=0.0 if is_success else 1.0,
                last_execution=datetime.now(timezone.utc),
                executions_per_hour=0.0,  # Will be calculated later
                health_status=HealthStatus.HEALTHY
            )
        else:
            # Update existing metrics
            cached = self.performance_cache[hook_id]
            cached.total_executions += 1
            if is_success:
                cached.successful_executions += 1
            else:
                cached.failed_executions += 1
            
            # Update execution time statistics
            cached.average_execution_time_ms = (
                (cached.average_execution_time_ms * (cached.total_executions - 1) + 
                 execution_result.execution_time_ms) / cached.total_executions
            )
            cached.min_execution_time_ms = min(cached.min_execution_time_ms, execution_result.execution_time_ms)
            cached.max_execution_time_ms = max(cached.max_execution_time_ms, execution_result.execution_time_ms)
            
            # Update rates
            cached.success_rate = cached.successful_executions / cached.total_executions
            cached.error_rate = 1.0 - cached.success_rate
            
            cached.last_execution = datetime.now(timezone.utc)
            
            # Update health status
            cached.health_status = self._determine_hook_health_status(
                cached.success_rate, cached.average_execution_time_ms, cached.executions_per_hour
            )
    
    async def _check_execution_alerts(self, execution_result: HookExecutionResult):
        """Check if execution result triggers any alerts."""
        hook_id = execution_result.hook_id
        team_id = execution_result.metadata.get('team_id', 'unknown')
        
        # Get current metrics for the hook
        metrics = self.performance_cache.get(hook_id)
        if not metrics:
            return
        
        # Check each alert rule
        for rule in self.alert_rules.values():
            if not rule.enabled:
                continue
            
            # Apply filters
            if rule.team_filter and rule.team_filter != team_id:
                continue
            
            if rule.hook_type_filter and rule.hook_type_filter != metrics.hook_type:
                continue
            
            # Get metric value
            metric_value = self._get_metric_value(metrics, rule.metric_type)
            if metric_value is None:
                continue
            
            # Check threshold
            if self._check_threshold(metric_value, rule.threshold_value, rule.comparison_operator):
                await self._trigger_alert(rule, hook_id, team_id, metric_value)
    
    def _get_metric_value(self, metrics: HookPerformanceMetrics, metric_type: str) -> Optional[float]:
        """Get metric value from performance metrics."""
        metric_map = {
            'average_execution_time_ms': metrics.average_execution_time_ms,
            'success_rate': metrics.success_rate,
            'error_rate': metrics.error_rate,
            'executions_per_hour': metrics.executions_per_hour,
            'total_executions': float(metrics.total_executions)
        }
        return metric_map.get(metric_type)
    
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
    
    async def _trigger_alert(self, rule: AlertRule, hook_id: str, team_id: str, metric_value: float):
        """Trigger an alert based on rule violation."""
        alert_id = f"{rule.rule_id}_{hook_id}_{int(datetime.now().timestamp())}"
        
        # Check if similar alert already exists
        existing_alert = None
        for alert in self.active_alerts.values():
            if (alert.rule_id == rule.rule_id and 
                alert.hook_id == hook_id and 
                not alert.resolved_at):
                existing_alert = alert
                break
        
        if existing_alert:
            # Update existing alert
            existing_alert.metric_value = metric_value
            existing_alert.triggered_at = datetime.now(timezone.utc)
        else:
            # Create new alert
            alert = Alert(
                alert_id=alert_id,
                rule_id=rule.rule_id,
                hook_id=hook_id,
                team_id=team_id,
                severity=rule.severity,
                title=rule.name,
                description=f"{rule.description}. Current value: {metric_value:.2f}, Threshold: {rule.threshold_value:.2f}",
                metric_value=metric_value,
                threshold_value=rule.threshold_value,
                triggered_at=datetime.now(timezone.utc),
                metadata={
                    'metric_type': rule.metric_type,
                    'comparison_operator': rule.comparison_operator
                }
            )
            
            self.active_alerts[alert_id] = alert
            logger.warning(f"Alert triggered: {alert.title} for hook {hook_id}")
    
    def _determine_hook_health_status(
        self, 
        success_rate: float, 
        avg_execution_time: float, 
        executions_per_hour: float
    ) -> HealthStatus:
        """Determine health status for a hook."""
        if (success_rate < self.performance_thresholds['success_rate_critical'] or
            avg_execution_time > self.performance_thresholds['execution_time_critical_ms']):
            return HealthStatus.CRITICAL
        
        if (success_rate < self.performance_thresholds['success_rate_warning'] or
            avg_execution_time > self.performance_thresholds['execution_time_warning_ms']):
            return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    def _determine_system_health_status(
        self,
        success_rate: float,
        avg_execution_time: float,
        error_count: int,
        alerts_count: int
    ) -> HealthStatus:
        """Determine overall system health status."""
        critical_alerts = len([a for a in self.active_alerts.values() 
                              if a.severity == AlertSeverity.CRITICAL and not a.resolved_at])
        
        if (success_rate < 0.8 or 
            avg_execution_time > 5000 or 
            error_count > 50 or 
            critical_alerts > 0):
            return HealthStatus.CRITICAL
        
        if (success_rate < 0.9 or 
            avg_execution_time > 2000 or 
            error_count > 10 or 
            alerts_count > 5):
            return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    async def _calculate_hook_metrics(self, records: List[AnalyticsRecord]) -> Dict[str, Any]:
        """Calculate metrics for a set of hook records."""
        if not records:
            return {}
        
        total_executions = len(records)
        successful_executions = len([r for r in records if r.data.get('success', False)])
        success_rate = successful_executions / total_executions
        
        execution_times = [r.data.get('execution_time_ms', 0) for r in records]
        avg_execution_time = statistics.mean(execution_times) if execution_times else 0.0
        
        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': success_rate,
            'average_execution_time_ms': avg_execution_time,
            'hook_type': records[0].data.get('hook_type', 'unknown'),
            'team_id': records[0].team_id
        }
    
    async def _calculate_performance_trends(
        self, 
        records: List[AnalyticsRecord], 
        time_range: Tuple[datetime, datetime]
    ) -> List[PerformanceTrend]:
        """Calculate performance trends from records."""
        trends = []
        
        # Split time range into two halves for comparison
        mid_point = time_range[0] + (time_range[1] - time_range[0]) / 2
        
        first_half = [r for r in records if r.timestamp <= mid_point]
        second_half = [r for r in records if r.timestamp > mid_point]
        
        if not first_half or not second_half:
            return trends
        
        # Calculate success rate trend
        first_success_rate = len([r for r in first_half if r.data.get('success', False)]) / len(first_half)
        second_success_rate = len([r for r in second_half if r.data.get('success', False)]) / len(second_half)
        
        success_rate_change = (second_success_rate - first_success_rate) / first_success_rate if first_success_rate > 0 else 0
        
        trends.append(PerformanceTrend(
            metric_name="success_rate",
            time_period=f"{time_range[0].strftime('%Y-%m-%d')} to {time_range[1].strftime('%Y-%m-%d')}",
            trend_direction="improving" if success_rate_change > 0.05 else "declining" if success_rate_change < -0.05 else "stable",
            trend_strength=abs(success_rate_change),
            current_value=second_success_rate,
            previous_value=first_success_rate,
            change_percentage=success_rate_change * 100,
            statistical_significance=0.8  # Mock value
        ))
        
        # Calculate execution time trend
        first_avg_time = statistics.mean([r.data.get('execution_time_ms', 0) for r in first_half])
        second_avg_time = statistics.mean([r.data.get('execution_time_ms', 0) for r in second_half])
        
        time_change = (second_avg_time - first_avg_time) / first_avg_time if first_avg_time > 0 else 0
        
        trends.append(PerformanceTrend(
            metric_name="execution_time",
            time_period=f"{time_range[0].strftime('%Y-%m-%d')} to {time_range[1].strftime('%Y-%m-%d')}",
            trend_direction="declining" if time_change > 0.1 else "improving" if time_change < -0.1 else "stable",
            trend_strength=abs(time_change),
            current_value=second_avg_time,
            previous_value=first_avg_time,
            change_percentage=time_change * 100,
            statistical_significance=0.8  # Mock value
        ))
        
        return trends
    
    async def _start_background_tasks(self):
        """Start background monitoring and aggregation tasks."""
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._aggregation_task = asyncio.create_task(self._aggregation_loop())
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while self._running:
            try:
                # Update system health metrics
                await self.get_system_health_metrics()
                
                # Check for alert conditions
                await self._check_system_alerts()
                
                # Clean up old resolved alerts
                await self._cleanup_old_alerts()
                
                await asyncio.sleep(60)  # Run every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    async def _aggregation_loop(self):
        """Background aggregation loop."""
        while self._running:
            try:
                # Perform data aggregation for reporting
                await self._aggregate_performance_data()
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in aggregation loop: {e}", exc_info=True)
                await asyncio.sleep(300)
    
    async def _check_system_alerts(self):
        """Check for system-level alert conditions."""
        # This would check system-wide metrics and trigger alerts
        # Implementation would depend on specific system-level thresholds
        pass
    
    async def _cleanup_old_alerts(self):
        """Clean up old resolved alerts."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
        
        alerts_to_remove = []
        for alert_id, alert in self.active_alerts.items():
            if alert.resolved_at and alert.resolved_at < cutoff_time:
                alerts_to_remove.append(alert_id)
        
        for alert_id in alerts_to_remove:
            del self.active_alerts[alert_id]
    
    async def _aggregate_performance_data(self):
        """Aggregate performance data for efficient reporting."""
        # This would create pre-aggregated data for common queries
        # to improve dashboard and reporting performance
        pass


# Global analytics engine instance
_analytics_engine: Optional[HookAnalyticsEngine] = None


async def get_hook_analytics_engine() -> HookAnalyticsEngine:
    """Get the global hook analytics engine instance."""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = HookAnalyticsEngine()
        await _analytics_engine.initialize()
    return _analytics_engine


async def shutdown_hook_analytics_engine():
    """Shutdown the global hook analytics engine."""
    global _analytics_engine
    if _analytics_engine:
        await _analytics_engine.shutdown()
        _analytics_engine = None