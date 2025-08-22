"""
System Health Monitor for DevSync AI Hook System.

This module provides comprehensive health monitoring, diagnostic tools,
and system status tracking for the JIRA Agent Hooks system.
"""

import asyncio
import logging
import psutil
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import json

from devsync_ai.hooks.hook_registry_manager import get_hook_registry_manager
from devsync_ai.analytics.hook_analytics_engine import HookAnalyticsEngine, HealthStatus
from devsync_ai.analytics.analytics_data_manager import get_analytics_data_manager
from devsync_ai.core.agent_hooks import HookStatus

logger = logging.getLogger(__name__)


class ComponentStatus(Enum):
    """Component status levels."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class DiagnosticLevel(Enum):
    """Diagnostic check levels."""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


@dataclass
class ComponentHealth:
    """Health status for a system component."""
    component_name: str
    status: ComponentStatus
    response_time_ms: float
    last_check: datetime
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemDiagnostics:
    """Comprehensive system diagnostic information."""
    timestamp: datetime
    overall_status: HealthStatus
    components: Dict[str, ComponentHealth]
    performance_metrics: Dict[str, float]
    resource_usage: Dict[str, float]
    active_issues: List[str]
    recommendations: List[str]
    diagnostic_level: DiagnosticLevel


@dataclass
class PerformanceAlert:
    """Performance-based alert."""
    alert_id: str
    component: str
    metric_name: str
    current_value: float
    threshold_value: float
    severity: str
    message: str
    triggered_at: datetime
    auto_resolve: bool = True


class SystemHealthMonitor:
    """
    Comprehensive system health monitoring for the hook system.
    
    Provides health checks, performance monitoring, diagnostics,
    and alerting capabilities.
    """
    
    def __init__(self):
        """Initialize the system health monitor."""
        self.component_health: Dict[str, ComponentHealth] = {}
        self.performance_history: List[Dict[str, Any]] = []
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        
        # Performance thresholds
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 90.0,
            'memory_warning': 80.0,
            'memory_critical': 95.0,
            'disk_warning': 85.0,
            'disk_critical': 95.0,
            'response_time_warning': 1000.0,  # ms
            'response_time_critical': 3000.0,  # ms
            'hook_success_rate_warning': 0.95,
            'hook_success_rate_critical': 0.85,
            'database_connection_timeout': 5000.0,  # ms
            'webhook_processing_time_warning': 2000.0,  # ms
            'webhook_processing_time_critical': 5000.0  # ms
        }
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._last_health_check = datetime.min
        
        # Component check intervals (seconds)
        self.check_intervals = {
            'hook_registry': 30,
            'database': 60,
            'analytics_engine': 45,
            'webhook_handler': 30,
            'notification_system': 60
        }
    
    async def start_monitoring(self):
        """Start the health monitoring system."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("System health monitoring started")
    
    async def stop_monitoring(self):
        """Stop the health monitoring system."""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("System health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._monitoring_active:
            try:
                # Perform health checks
                await self._perform_health_checks()
                
                # Check performance metrics
                await self._check_performance_metrics()
                
                # Update performance history
                await self._update_performance_history()
                
                # Check for alerts
                await self._check_alert_conditions()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _perform_health_checks(self):
        """Perform health checks on all system components."""
        # Check hook registry
        await self._check_hook_registry_health()
        
        # Check database connectivity
        await self._check_database_health()
        
        # Check analytics engine
        await self._check_analytics_engine_health()
        
        # Check webhook handler
        await self._check_webhook_handler_health()
        
        # Check notification system
        await self._check_notification_system_health()
        
        self._last_health_check = datetime.now(timezone.utc)
    
    async def _check_hook_registry_health(self):
        """Check hook registry health."""
        start_time = time.time()
        
        try:
            registry_manager = await get_hook_registry_manager()
            
            if registry_manager:
                # Test basic operations
                hook_statuses = await registry_manager.get_all_hook_statuses()
                system_health = await registry_manager.get_system_health()
                
                response_time = (time.time() - start_time) * 1000
                
                # Determine status based on response time and functionality
                if response_time > self.thresholds['response_time_critical']:
                    status = ComponentStatus.DEGRADED
                    error_msg = f"High response time: {response_time:.1f}ms"
                elif response_time > self.thresholds['response_time_warning']:
                    status = ComponentStatus.DEGRADED
                    error_msg = f"Elevated response time: {response_time:.1f}ms"
                else:
                    status = ComponentStatus.OPERATIONAL
                    error_msg = None
                
                self.component_health['hook_registry'] = ComponentHealth(
                    component_name='hook_registry',
                    status=status,
                    response_time_ms=response_time,
                    last_check=datetime.now(timezone.utc),
                    error_message=error_msg,
                    metadata={
                        'total_hooks': len(hook_statuses),
                        'system_health': system_health.__dict__ if system_health else None
                    }
                )
            else:
                self.component_health['hook_registry'] = ComponentHealth(
                    component_name='hook_registry',
                    status=ComponentStatus.UNAVAILABLE,
                    response_time_ms=0.0,
                    last_check=datetime.now(timezone.utc),
                    error_message="Hook registry manager not available"
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.component_health['hook_registry'] = ComponentHealth(
                component_name='hook_registry',
                status=ComponentStatus.ERROR,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                error_message=str(e)
            )
    
    async def _check_database_health(self):
        """Check database connectivity and performance."""
        start_time = time.time()
        
        try:
            data_manager = await get_analytics_data_manager()
            
            if data_manager:
                # Test database connection with a simple query
                test_query_start = time.time()
                
                # Try to query recent records
                end_time = datetime.now(timezone.utc)
                start_time_query = end_time - timedelta(minutes=5)
                
                records = await data_manager.query_records(
                    record_type="hook_execution",
                    start_time=start_time_query,
                    end_time=end_time
                )
                
                query_time = (time.time() - test_query_start) * 1000
                response_time = (time.time() - start_time) * 1000
                
                # Determine status based on query performance
                if query_time > self.thresholds['database_connection_timeout']:
                    status = ComponentStatus.DEGRADED
                    error_msg = f"Slow database queries: {query_time:.1f}ms"
                elif query_time > self.thresholds['database_connection_timeout'] / 2:
                    status = ComponentStatus.DEGRADED
                    error_msg = f"Elevated database response time: {query_time:.1f}ms"
                else:
                    status = ComponentStatus.OPERATIONAL
                    error_msg = None
                
                self.component_health['database'] = ComponentHealth(
                    component_name='database',
                    status=status,
                    response_time_ms=response_time,
                    last_check=datetime.now(timezone.utc),
                    error_message=error_msg,
                    metadata={
                        'query_time_ms': query_time,
                        'recent_records_count': len(records)
                    }
                )
            else:
                self.component_health['database'] = ComponentHealth(
                    component_name='database',
                    status=ComponentStatus.UNAVAILABLE,
                    response_time_ms=0.0,
                    last_check=datetime.now(timezone.utc),
                    error_message="Analytics data manager not available"
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.component_health['database'] = ComponentHealth(
                component_name='database',
                status=ComponentStatus.ERROR,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                error_message=str(e)
            )
    
    async def _check_analytics_engine_health(self):
        """Check analytics engine health."""
        start_time = time.time()
        
        try:
            # Create a test analytics engine instance
            analytics_engine = HookAnalyticsEngine()
            
            # Test basic functionality
            system_health = await analytics_engine.get_system_health_metrics()
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on system health
            if system_health.health_status == HealthStatus.CRITICAL:
                status = ComponentStatus.DEGRADED
                error_msg = "Analytics engine reports critical system health"
            elif system_health.health_status == HealthStatus.WARNING:
                status = ComponentStatus.DEGRADED
                error_msg = "Analytics engine reports warning system health"
            else:
                status = ComponentStatus.OPERATIONAL
                error_msg = None
            
            self.component_health['analytics_engine'] = ComponentHealth(
                component_name='analytics_engine',
                status=status,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                error_message=error_msg,
                metadata={
                    'system_health': system_health.__dict__,
                    'active_alerts': len(analytics_engine.active_alerts)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.component_health['analytics_engine'] = ComponentHealth(
                component_name='analytics_engine',
                status=ComponentStatus.ERROR,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                error_message=str(e)
            )
    
    async def _check_webhook_handler_health(self):
        """Check webhook handler health."""
        start_time = time.time()
        
        try:
            # This would typically test webhook endpoint availability
            # For now, we'll do a basic check
            
            response_time = (time.time() - start_time) * 1000
            
            # Mock webhook health check (would be actual endpoint test)
            status = ComponentStatus.OPERATIONAL
            error_msg = None
            
            self.component_health['webhook_handler'] = ComponentHealth(
                component_name='webhook_handler',
                status=status,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                error_message=error_msg,
                metadata={
                    'endpoint_status': 'available'
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.component_health['webhook_handler'] = ComponentHealth(
                component_name='webhook_handler',
                status=ComponentStatus.ERROR,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                error_message=str(e)
            )
    
    async def _check_notification_system_health(self):
        """Check notification system health."""
        start_time = time.time()
        
        try:
            # Mock notification system health check
            # In a real implementation, this would test Slack API connectivity
            
            response_time = (time.time() - start_time) * 1000
            
            status = ComponentStatus.OPERATIONAL
            error_msg = None
            
            self.component_health['notification_system'] = ComponentHealth(
                component_name='notification_system',
                status=status,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                error_message=error_msg,
                metadata={
                    'slack_api_status': 'available'
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.component_health['notification_system'] = ComponentHealth(
                component_name='notification_system',
                status=ComponentStatus.ERROR,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                error_message=str(e)
            )
    
    async def _check_performance_metrics(self):
        """Check system performance metrics."""
        try:
            # Get system resource usage
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Check thresholds and create alerts if needed
            await self._check_resource_thresholds(cpu_usage, memory.percent, disk.percent)
            
        except Exception as e:
            logger.error(f"Failed to check performance metrics: {e}", exc_info=True)
    
    async def _check_resource_thresholds(self, cpu_usage: float, memory_usage: float, disk_usage: float):
        """Check resource usage against thresholds."""
        # CPU usage alerts
        if cpu_usage > self.thresholds['cpu_critical']:
            await self._create_performance_alert(
                'system_cpu_critical',
                'system',
                'cpu_usage',
                cpu_usage,
                self.thresholds['cpu_critical'],
                'critical',
                f"Critical CPU usage: {cpu_usage:.1f}%"
            )
        elif cpu_usage > self.thresholds['cpu_warning']:
            await self._create_performance_alert(
                'system_cpu_warning',
                'system',
                'cpu_usage',
                cpu_usage,
                self.thresholds['cpu_warning'],
                'warning',
                f"High CPU usage: {cpu_usage:.1f}%"
            )
        
        # Memory usage alerts
        if memory_usage > self.thresholds['memory_critical']:
            await self._create_performance_alert(
                'system_memory_critical',
                'system',
                'memory_usage',
                memory_usage,
                self.thresholds['memory_critical'],
                'critical',
                f"Critical memory usage: {memory_usage:.1f}%"
            )
        elif memory_usage > self.thresholds['memory_warning']:
            await self._create_performance_alert(
                'system_memory_warning',
                'system',
                'memory_usage',
                memory_usage,
                self.thresholds['memory_warning'],
                'warning',
                f"High memory usage: {memory_usage:.1f}%"
            )
        
        # Disk usage alerts
        if disk_usage > self.thresholds['disk_critical']:
            await self._create_performance_alert(
                'system_disk_critical',
                'system',
                'disk_usage',
                disk_usage,
                self.thresholds['disk_critical'],
                'critical',
                f"Critical disk usage: {disk_usage:.1f}%"
            )
        elif disk_usage > self.thresholds['disk_warning']:
            await self._create_performance_alert(
                'system_disk_warning',
                'system',
                'disk_usage',
                disk_usage,
                self.thresholds['disk_warning'],
                'warning',
                f"High disk usage: {disk_usage:.1f}%"
            )
    
    async def _create_performance_alert(
        self,
        alert_id: str,
        component: str,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        severity: str,
        message: str
    ):
        """Create or update a performance alert."""
        if alert_id in self.active_alerts:
            # Update existing alert
            alert = self.active_alerts[alert_id]
            alert.current_value = current_value
            alert.triggered_at = datetime.now(timezone.utc)
        else:
            # Create new alert
            alert = PerformanceAlert(
                alert_id=alert_id,
                component=component,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=threshold_value,
                severity=severity,
                message=message,
                triggered_at=datetime.now(timezone.utc)
            )
            self.active_alerts[alert_id] = alert
            logger.warning(f"Performance alert triggered: {message}")
    
    async def _update_performance_history(self):
        """Update performance history."""
        try:
            # Get current system metrics
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get component response times
            component_response_times = {
                name: health.response_time_ms
                for name, health in self.component_health.items()
            }
            
            performance_snapshot = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'cpu_usage': cpu_usage,
                'memory_usage': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_usage': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'component_response_times': component_response_times,
                'active_alerts_count': len(self.active_alerts)
            }
            
            self.performance_history.append(performance_snapshot)
            
            # Keep only last 24 hours of history (assuming 30-second intervals)
            max_entries = 24 * 60 * 2  # 2880 entries
            if len(self.performance_history) > max_entries:
                self.performance_history = self.performance_history[-max_entries:]
                
        except Exception as e:
            logger.error(f"Failed to update performance history: {e}", exc_info=True)
    
    async def _check_alert_conditions(self):
        """Check for alert resolution conditions."""
        resolved_alerts = []
        
        for alert_id, alert in self.active_alerts.items():
            if alert.auto_resolve:
                # Check if alert condition is resolved
                if await self._is_alert_resolved(alert):
                    resolved_alerts.append(alert_id)
                    logger.info(f"Performance alert resolved: {alert.message}")
        
        # Remove resolved alerts
        for alert_id in resolved_alerts:
            del self.active_alerts[alert_id]
    
    async def _is_alert_resolved(self, alert: PerformanceAlert) -> bool:
        """Check if an alert condition is resolved."""
        try:
            if alert.component == 'system':
                if alert.metric_name == 'cpu_usage':
                    current_value = psutil.cpu_percent()
                elif alert.metric_name == 'memory_usage':
                    current_value = psutil.virtual_memory().percent
                elif alert.metric_name == 'disk_usage':
                    current_value = psutil.disk_usage('/').percent
                else:
                    return False
                
                # Check if value is below threshold (with some hysteresis)
                hysteresis_factor = 0.9  # 10% hysteresis
                return current_value < (alert.threshold_value * hysteresis_factor)
            
            return False
            
        except Exception:
            return False
    
    async def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        # Clean up performance history older than 24 hours
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        self.performance_history = [
            entry for entry in self.performance_history
            if datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00')) > cutoff_time
        ]
    
    # Public API methods
    async def get_system_health_status(self) -> Dict[str, Any]:
        """Get overall system health status."""
        # Determine overall status
        component_statuses = [health.status for health in self.component_health.values()]
        
        if ComponentStatus.ERROR in component_statuses:
            overall_status = HealthStatus.ERROR
        elif ComponentStatus.UNAVAILABLE in component_statuses:
            overall_status = HealthStatus.CRITICAL
        elif ComponentStatus.DEGRADED in component_statuses:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Get system resource usage
        try:
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
        except Exception:
            cpu_usage = 0.0
            memory = type('obj', (object,), {'percent': 0.0, 'available': 0})()
            disk = type('obj', (object,), {'percent': 0.0, 'free': 0})()
        
        return {
            'overall_status': overall_status.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'last_health_check': self._last_health_check.isoformat(),
            'components': {
                name: {
                    'status': health.status.value,
                    'response_time_ms': health.response_time_ms,
                    'last_check': health.last_check.isoformat(),
                    'error_message': health.error_message,
                    'metadata': health.metadata
                }
                for name, health in self.component_health.items()
            },
            'system_resources': {
                'cpu_usage': cpu_usage,
                'memory_usage': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_usage': disk.percent,
                'disk_free_gb': disk.free / (1024**3)
            },
            'active_alerts': len(self.active_alerts),
            'monitoring_active': self._monitoring_active
        }
    
    async def get_detailed_diagnostics(self, level: DiagnosticLevel = DiagnosticLevel.DETAILED) -> SystemDiagnostics:
        """Get detailed system diagnostics."""
        # Perform fresh health checks if needed
        if (datetime.now(timezone.utc) - self._last_health_check).total_seconds() > 300:  # 5 minutes
            await self._perform_health_checks()
        
        # Collect performance metrics
        performance_metrics = {}
        resource_usage = {}
        
        try:
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            performance_metrics.update({
                'avg_component_response_time': statistics.mean([
                    h.response_time_ms for h in self.component_health.values()
                ]) if self.component_health else 0.0,
                'max_component_response_time': max([
                    h.response_time_ms for h in self.component_health.values()
                ]) if self.component_health else 0.0
            })
            
            resource_usage.update({
                'cpu_usage': cpu_usage,
                'memory_usage': memory.percent,
                'disk_usage': disk.percent
            })
            
        except Exception as e:
            logger.error(f"Failed to collect diagnostics: {e}")
        
        # Identify active issues
        active_issues = []
        for health in self.component_health.values():
            if health.status in [ComponentStatus.ERROR, ComponentStatus.UNAVAILABLE]:
                active_issues.append(f"{health.component_name}: {health.error_message or 'Unknown error'}")
        
        for alert in self.active_alerts.values():
            active_issues.append(f"{alert.component}: {alert.message}")
        
        # Generate recommendations
        recommendations = await self._generate_recommendations()
        
        # Determine overall status
        if active_issues:
            if any('critical' in issue.lower() or 'error' in issue.lower() for issue in active_issues):
                overall_status = HealthStatus.CRITICAL
            else:
                overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY
        
        return SystemDiagnostics(
            timestamp=datetime.now(timezone.utc),
            overall_status=overall_status,
            components=self.component_health,
            performance_metrics=performance_metrics,
            resource_usage=resource_usage,
            active_issues=active_issues,
            recommendations=recommendations,
            diagnostic_level=level
        )
    
    async def _generate_recommendations(self) -> List[str]:
        """Generate system optimization recommendations."""
        recommendations = []
        
        try:
            # CPU recommendations
            cpu_usage = psutil.cpu_percent()
            if cpu_usage > self.thresholds['cpu_warning']:
                recommendations.append(
                    f"High CPU usage detected ({cpu_usage:.1f}%). Consider scaling up resources or optimizing hook execution."
                )
            
            # Memory recommendations
            memory = psutil.virtual_memory()
            if memory.percent > self.thresholds['memory_warning']:
                recommendations.append(
                    f"High memory usage detected ({memory.percent:.1f}%). Consider increasing memory allocation or optimizing data caching."
                )
            
            # Component-specific recommendations
            for name, health in self.component_health.items():
                if health.response_time_ms > self.thresholds['response_time_warning']:
                    recommendations.append(
                        f"{name} has high response time ({health.response_time_ms:.1f}ms). Consider performance optimization."
                    )
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            recommendations.append("Unable to generate recommendations due to system error.")
        
        return recommendations
    
    async def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get list of active performance alerts."""
        return list(self.active_alerts.values())
    
    async def get_performance_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get performance history for the specified number of hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [
            entry for entry in self.performance_history
            if datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00')) > cutoff_time
        ]
    
    async def get_component_health_history(self, component_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get health history for a specific component."""
        history = await self.get_performance_history(hours)
        
        component_history = []
        for entry in history:
            if 'component_response_times' in entry and component_name in entry['component_response_times']:
                component_history.append({
                    'timestamp': entry['timestamp'],
                    'response_time_ms': entry['component_response_times'][component_name],
                    'status': 'operational' if entry['component_response_times'][component_name] < self.thresholds['response_time_warning'] else 'degraded'
                })
        
        return component_history


# Global health monitor instance
_health_monitor: Optional[SystemHealthMonitor] = None


async def get_health_monitor() -> SystemHealthMonitor:
    """Get the global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = SystemHealthMonitor()
        await _health_monitor.start_monitoring()
    return _health_monitortion."
                    )
                
                if health.status == ComponentStatus.DEGRADED:
                    recommendations.append(
                        f"{name} is degraded. Check logs and consider restarting the component."
                    )
            
            # Alert-based recommendations
            if len(self.active_alerts) > 5:
                recommendations.append(
                    "Multiple active alerts detected. Review system configuration and consider scaling resources."
                )
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            recommendations.append("Unable to generate recommendations due to system error.")
        
        return recommendations
    
    async def get_performance_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get performance history for the specified time range."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [
            entry for entry in self.performance_history
            if datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00')) > cutoff_time
        ]
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active performance alerts."""
        return [
            {
                'alert_id': alert.alert_id,
                'component': alert.component,
                'metric_name': alert.metric_name,
                'current_value': alert.current_value,
                'threshold_value': alert.threshold_value,
                'severity': alert.severity,
                'message': alert.message,
                'triggered_at': alert.triggered_at.isoformat(),
                'auto_resolve': alert.auto_resolve
            }
            for alert in self.active_alerts.values()
        ]
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve a performance alert."""
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
            logger.info(f"Performance alert {alert_id} manually resolved")
            return True
        return False
    
    async def update_thresholds(self, new_thresholds: Dict[str, float]) -> bool:
        """Update performance thresholds."""
        try:
            # Validate threshold keys
            valid_keys = set(self.thresholds.keys())
            provided_keys = set(new_thresholds.keys())
            
            if not provided_keys.issubset(valid_keys):
                invalid_keys = provided_keys - valid_keys
                logger.error(f"Invalid threshold keys: {invalid_keys}")
                return False
            
            # Update thresholds
            self.thresholds.update(new_thresholds)
            logger.info(f"Performance thresholds updated: {new_thresholds}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update thresholds: {e}")
            return False


# Global health monitor instance
_health_monitor: Optional[SystemHealthMonitor] = None


async def get_health_monitor() -> SystemHealthMonitor:
    """Get the global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = SystemHealthMonitor()
        await _health_monitor.start_monitoring()
    return _health_monitor


async def shutdown_health_monitor():
    """Shutdown the global health monitor instance."""
    global _health_monitor
    if _health_monitor:
        await _health_monitor.stop_monitoring()
        _health_monitor = None