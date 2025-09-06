"""
Performance monitoring system for changelog generation with real-time metrics and alerting.
"""

import asyncio
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict, deque

from ..database.connection import get_database


class MetricType(Enum):
    """Types of performance metrics."""
    GENERATION_TIME = "generation_time"
    API_RESPONSE_TIME = "api_response_time"
    DATABASE_QUERY_TIME = "database_query_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    CONCURRENT_OPERATIONS = "concurrent_operations"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""
    metric_type: MetricType
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    team_id: Optional[str] = None
    operation_id: Optional[str] = None


@dataclass
class PerformanceAlert:
    """Performance alert information."""
    alert_id: str
    severity: AlertSeverity
    metric_type: MetricType
    threshold_value: float
    actual_value: float
    message: str
    timestamp: datetime
    team_id: Optional[str] = None
    resolved: bool = False


@dataclass
class SystemHealthStatus:
    """Overall system health status."""
    status: str  # healthy, degraded, critical
    cpu_usage: float
    memory_usage: float
    active_operations: int
    error_rate: float
    avg_response_time: float
    timestamp: datetime


class PerformanceMonitor:
    """
    Real-time performance monitoring system with metrics collection and alerting.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics_buffer: deque = deque(maxlen=10000)  # Ring buffer for metrics
        self.active_operations: Dict[str, datetime] = {}
        self.alert_thresholds = self._load_alert_thresholds()
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Performance counters
        self.operation_counters = defaultdict(int)
        self.error_counters = defaultdict(int)
        self.response_times = defaultdict(list)
        
    def _load_alert_thresholds(self) -> Dict[MetricType, Dict[str, float]]:
        """Load alert thresholds from configuration."""
        return {
            MetricType.GENERATION_TIME: {
                "warning": 180.0,  # 3 minutes
                "critical": 300.0  # 5 minutes
            },
            MetricType.API_RESPONSE_TIME: {
                "warning": 2.0,    # 2 seconds
                "critical": 10.0   # 10 seconds
            },
            MetricType.DATABASE_QUERY_TIME: {
                "warning": 1.0,    # 1 second
                "critical": 5.0    # 5 seconds
            },
            MetricType.MEMORY_USAGE: {
                "warning": 80.0,   # 80% memory usage
                "critical": 95.0   # 95% memory usage
            },
            MetricType.CPU_USAGE: {
                "warning": 80.0,   # 80% CPU usage
                "critical": 95.0   # 95% CPU usage
            },
            MetricType.ERROR_RATE: {
                "warning": 5.0,    # 5% error rate
                "critical": 15.0   # 15% error rate
            },
            MetricType.CONCURRENT_OPERATIONS: {
                "warning": 40.0,   # 40 concurrent operations
                "critical": 50.0   # 50 concurrent operations
            }
        }
    
    async def start_monitoring(self):
        """Start the performance monitoring system."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop the performance monitoring system."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop that collects system metrics."""
        try:
            while True:
                await self._collect_system_metrics()
                await self._check_alert_conditions()
                await self._cleanup_old_data()
                await asyncio.sleep(10)  # Collect metrics every 10 seconds
        except asyncio.CancelledError:
            self.logger.info("Monitoring loop cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in monitoring loop: {e}")
            await asyncio.sleep(30)  # Wait before retrying
    
    async def _collect_system_metrics(self):
        """Collect system-level performance metrics."""
        try:
            # CPU and memory metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            await self.record_metric(
                MetricType.CPU_USAGE,
                cpu_percent,
                metadata={"cores": psutil.cpu_count()}
            )
            
            await self.record_metric(
                MetricType.MEMORY_USAGE,
                memory.percent,
                metadata={
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2)
                }
            )
            
            # Active operations count
            await self.record_metric(
                MetricType.CONCURRENT_OPERATIONS,
                len(self.active_operations)
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    async def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        team_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a performance metric."""
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
            team_id=team_id,
            operation_id=operation_id
        )
        
        self.metrics_buffer.append(metric)
        
        # Store in database for persistence
        await self._store_metric_in_database(metric)
        
        # Update counters for real-time analysis
        self._update_counters(metric)
    
    async def _store_metric_in_database(self, metric: PerformanceMetric):
        """Store metric in database for historical analysis."""
        try:
            db = await get_database()
            await db.insert("performance_metrics", {
                "metric_type": metric.metric_type.value,
                "value": metric.value,
                "timestamp": metric.timestamp.isoformat(),
                "metadata": metric.metadata,
                "team_id": metric.team_id,
                "operation_id": metric.operation_id
            })
        except Exception as e:
            self.logger.error(f"Error storing metric in database: {e}")
    
    def _update_counters(self, metric: PerformanceMetric):
        """Update real-time counters for performance analysis."""
        key = f"{metric.metric_type.value}_{metric.team_id or 'global'}"
        
        if metric.metric_type in [MetricType.GENERATION_TIME, MetricType.API_RESPONSE_TIME, MetricType.DATABASE_QUERY_TIME]:
            self.response_times[key].append(metric.value)
            # Keep only last 100 measurements
            if len(self.response_times[key]) > 100:
                self.response_times[key] = self.response_times[key][-100:]
        
        self.operation_counters[key] += 1
    
    async def start_operation(self, operation_id: str, operation_type: str, team_id: Optional[str] = None) -> str:
        """Start tracking a performance-critical operation."""
        full_operation_id = f"{operation_type}_{operation_id}_{int(time.time())}"
        self.active_operations[full_operation_id] = datetime.utcnow()
        
        self.logger.debug(f"Started tracking operation: {full_operation_id}")
        return full_operation_id
    
    async def end_operation(
        self,
        operation_id: str,
        success: bool = True,
        team_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """End tracking of an operation and record performance metrics."""
        if operation_id not in self.active_operations:
            self.logger.warning(f"Operation {operation_id} not found in active operations")
            return
        
        start_time = self.active_operations.pop(operation_id)
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Determine metric type based on operation
        if "changelog_generation" in operation_id:
            metric_type = MetricType.GENERATION_TIME
        elif "api_" in operation_id:
            metric_type = MetricType.API_RESPONSE_TIME
        elif "db_" in operation_id:
            metric_type = MetricType.DATABASE_QUERY_TIME
        else:
            metric_type = MetricType.THROUGHPUT
        
        await self.record_metric(
            metric_type,
            duration,
            team_id=team_id,
            operation_id=operation_id,
            metadata={
                **(metadata or {}),
                "success": success,
                "operation_type": operation_id.split("_")[0]
            }
        )
        
        # Record error if operation failed
        if not success:
            await self.record_error(operation_id, team_id)
        
        self.logger.debug(f"Completed operation {operation_id} in {duration:.2f}s")
    
    async def record_error(self, operation_id: str, team_id: Optional[str] = None):
        """Record an error occurrence."""
        key = f"error_{team_id or 'global'}"
        self.error_counters[key] += 1
        
        # Calculate error rate
        total_ops = self.operation_counters.get(f"total_{team_id or 'global'}", 1)
        error_rate = (self.error_counters[key] / total_ops) * 100
        
        await self.record_metric(
            MetricType.ERROR_RATE,
            error_rate,
            team_id=team_id,
            metadata={"operation_id": operation_id}
        )
    
    async def _check_alert_conditions(self):
        """Check if any metrics exceed alert thresholds."""
        current_time = datetime.utcnow()
        
        # Check recent metrics for threshold violations
        recent_metrics = [
            m for m in self.metrics_buffer
            if (current_time - m.timestamp).total_seconds() < 300  # Last 5 minutes
        ]
        
        for metric_type, thresholds in self.alert_thresholds.items():
            relevant_metrics = [m for m in recent_metrics if m.metric_type == metric_type]
            
            if not relevant_metrics:
                continue
            
            # Get latest value for the metric type
            latest_metric = max(relevant_metrics, key=lambda x: x.timestamp)
            
            # Check thresholds
            if latest_metric.value >= thresholds["critical"]:
                await self._create_alert(
                    latest_metric,
                    AlertSeverity.CRITICAL,
                    thresholds["critical"]
                )
            elif latest_metric.value >= thresholds["warning"]:
                await self._create_alert(
                    latest_metric,
                    AlertSeverity.WARNING,
                    thresholds["warning"]
                )
    
    async def _create_alert(
        self,
        metric: PerformanceMetric,
        severity: AlertSeverity,
        threshold: float
    ):
        """Create a performance alert."""
        alert_id = f"{metric.metric_type.value}_{severity.value}_{int(time.time())}"
        
        # Don't create duplicate alerts
        existing_alert_key = f"{metric.metric_type.value}_{metric.team_id or 'global'}"
        if existing_alert_key in self.active_alerts:
            return
        
        alert = PerformanceAlert(
            alert_id=alert_id,
            severity=severity,
            metric_type=metric.metric_type,
            threshold_value=threshold,
            actual_value=metric.value,
            message=self._generate_alert_message(metric, severity, threshold),
            timestamp=datetime.utcnow(),
            team_id=metric.team_id
        )
        
        self.active_alerts[existing_alert_key] = alert
        
        # Store alert in database
        await self._store_alert_in_database(alert)
        
        # Send alert notification
        await self._send_alert_notification(alert)
        
        self.logger.warning(f"Performance alert created: {alert.message}")
    
    def _generate_alert_message(
        self,
        metric: PerformanceMetric,
        severity: AlertSeverity,
        threshold: float
    ) -> str:
        """Generate human-readable alert message."""
        metric_name = metric.metric_type.value.replace("_", " ").title()
        team_info = f" for team {metric.team_id}" if metric.team_id else ""
        
        if metric.metric_type in [MetricType.GENERATION_TIME, MetricType.API_RESPONSE_TIME, MetricType.DATABASE_QUERY_TIME]:
            return f"{severity.value.upper()}: {metric_name}{team_info} is {metric.value:.2f}s (threshold: {threshold}s)"
        elif metric.metric_type in [MetricType.MEMORY_USAGE, MetricType.CPU_USAGE, MetricType.ERROR_RATE]:
            return f"{severity.value.upper()}: {metric_name}{team_info} is {metric.value:.1f}% (threshold: {threshold}%)"
        else:
            return f"{severity.value.upper()}: {metric_name}{team_info} is {metric.value:.1f} (threshold: {threshold})"
    
    async def _store_alert_in_database(self, alert: PerformanceAlert):
        """Store alert in database."""
        try:
            db = await get_database()
            await db.insert("performance_alerts", {
                "alert_id": alert.alert_id,
                "severity": alert.severity.value,
                "metric_type": alert.metric_type.value,
                "threshold_value": alert.threshold_value,
                "actual_value": alert.actual_value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "team_id": alert.team_id,
                "resolved": alert.resolved
            })
        except Exception as e:
            self.logger.error(f"Error storing alert in database: {e}")
    
    async def _send_alert_notification(self, alert: PerformanceAlert):
        """Send alert notification to relevant channels."""
        try:
            # Import here to avoid circular imports
            from ..core.notification_integration import NotificationIntegration
            
            notification = NotificationIntegration()
            
            # Determine notification channels based on severity
            channels = ["#devsync-alerts"]
            if alert.severity == AlertSeverity.CRITICAL:
                channels.append("#devsync-critical")
            
            message = f"🚨 **Performance Alert**\n{alert.message}"
            
            for channel in channels:
                await notification.send_slack_notification(
                    channel=channel,
                    message=message,
                    metadata={
                        "alert_id": alert.alert_id,
                        "severity": alert.severity.value,
                        "metric_type": alert.metric_type.value
                    }
                )
        except Exception as e:
            self.logger.error(f"Error sending alert notification: {e}")
    
    async def get_system_health(self) -> SystemHealthStatus:
        """Get current system health status."""
        current_time = datetime.utcnow()
        
        # Get recent metrics
        recent_metrics = [
            m for m in self.metrics_buffer
            if (current_time - m.timestamp).total_seconds() < 60  # Last minute
        ]
        
        # Calculate averages
        cpu_metrics = [m.value for m in recent_metrics if m.metric_type == MetricType.CPU_USAGE]
        memory_metrics = [m.value for m in recent_metrics if m.metric_type == MetricType.MEMORY_USAGE]
        response_time_metrics = [
            m.value for m in recent_metrics
            if m.metric_type in [MetricType.API_RESPONSE_TIME, MetricType.GENERATION_TIME]
        ]
        error_rate_metrics = [m.value for m in recent_metrics if m.metric_type == MetricType.ERROR_RATE]
        
        avg_cpu = sum(cpu_metrics) / len(cpu_metrics) if cpu_metrics else 0
        avg_memory = sum(memory_metrics) / len(memory_metrics) if memory_metrics else 0
        avg_response_time = sum(response_time_metrics) / len(response_time_metrics) if response_time_metrics else 0
        avg_error_rate = sum(error_rate_metrics) / len(error_rate_metrics) if error_rate_metrics else 0
        
        # Determine overall status
        status = "healthy"
        if avg_cpu > 80 or avg_memory > 80 or avg_error_rate > 10:
            status = "degraded"
        if avg_cpu > 95 or avg_memory > 95 or avg_error_rate > 20:
            status = "critical"
        
        return SystemHealthStatus(
            status=status,
            cpu_usage=avg_cpu,
            memory_usage=avg_memory,
            active_operations=len(self.active_operations),
            error_rate=avg_error_rate,
            avg_response_time=avg_response_time,
            timestamp=current_time
        )
    
    async def get_performance_summary(
        self,
        team_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get performance summary for the specified time period."""
        try:
            # For now, return in-memory summary to avoid complex SQL queries
            # TODO: Implement proper database aggregation with Supabase client
            summary = {}
            
            # Calculate from in-memory metrics
            for metric_type, metrics in self.metrics.items():
                if metrics:
                    values = [m.value for m in metrics]
                    summary[metric_type.value] = {
                        'average': sum(values) / len(values),
                        'maximum': max(values),
                        'minimum': min(values),
                        'count': len(values)
                    }
            
            return summary
        except Exception as e:
            self.logger.error(f"Error getting performance summary: {e}")
            return {}
    
    async def _cleanup_old_data(self):
        """Clean up old performance data to prevent memory leaks."""
        try:
            # Clean up old metrics from database (keep last 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            try:
                db = await get_database()
                await db.delete("performance_metrics", {
                    "timestamp": {"lt": cutoff_date.isoformat()}
                })
                
                # Clean up resolved alerts older than 7 days
                alert_cutoff = datetime.utcnow() - timedelta(days=7)
                await db.delete("performance_alerts", {
                    "resolved": True,
                    "timestamp": {"lt": alert_cutoff.isoformat()}
                })
            except Exception as e:
                self.logger.error(f"Error cleaning up database: {e}")
            
            # Clean up in-memory data structures
            current_time = datetime.utcnow()
            
            # Remove old response times
            for key in list(self.response_times.keys()):
                if len(self.response_times[key]) > 1000:
                    self.response_times[key] = self.response_times[key][-500:]
            
            # Reset counters periodically (every hour)
            if current_time.minute == 0:
                self.operation_counters.clear()
                self.error_counters.clear()
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()