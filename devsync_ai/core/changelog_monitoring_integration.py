"""
Changelog Error Handler Integration with Existing Monitoring Infrastructure

This module provides seamless integration between the changelog error handling system
and DevSync AI's existing monitoring, alerting, and analytics infrastructure.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from devsync_ai.analytics.monitoring_data_manager import MonitoringDataManager
from devsync_ai.analytics.real_time_monitoring import RealTimeMonitor
from devsync_ai.analytics.alerting_system import AlertingSystem
from devsync_ai.core.changelog_error_handler import (
    ChangelogErrorHandler,
    ErrorContext,
    ErrorSeverity,
    RecoveryResult
)


@dataclass
class ChangelogMonitoringConfig:
    """Configuration for changelog monitoring integration"""
    enable_real_time_monitoring: bool = True
    enable_alerting: bool = True
    enable_analytics: bool = True
    alert_channels: List[str] = None
    monitoring_interval_seconds: int = 60
    error_threshold_percentage: float = 5.0
    performance_threshold_seconds: float = 180.0
    
    def __post_init__(self):
        if self.alert_channels is None:
            self.alert_channels = ["#devsync-alerts", "#changelog-monitoring"]


class ChangelogMonitoringIntegration:
    """
    Integration layer between changelog error handling and existing monitoring systems.
    
    Provides:
    - Real-time error monitoring and alerting
    - Integration with existing analytics infrastructure
    - Performance monitoring and optimization recommendations
    - Automated escalation and incident management
    """
    
    def __init__(self, 
                 config: Optional[ChangelogMonitoringConfig] = None,
                 monitoring_data_manager: Optional[MonitoringDataManager] = None,
                 real_time_monitor: Optional[RealTimeMonitor] = None,
                 alerting_system: Optional[AlertingSystem] = None):
        
        self.config = config or ChangelogMonitoringConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize monitoring components
        self.monitoring_data_manager = monitoring_data_manager or MonitoringDataManager()
        self.real_time_monitor = real_time_monitor or RealTimeMonitor()
        self.alerting_system = alerting_system or AlertingSystem()
        
        # Initialize error handler with monitoring callbacks
        self.error_handler = ChangelogErrorHandler(
            monitoring_callback=self._monitoring_callback,
            alerting_callback=self._alerting_callback
        )
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
    async def start_monitoring(self):
        """Start real-time monitoring of changelog error handling"""
        if self._monitoring_active:
            self.logger.warning("Monitoring already active")
            return
        
        self._monitoring_active = True
        
        if self.config.enable_real_time_monitoring:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.logger.info("Started changelog error monitoring")
    
    async def stop_monitoring(self):
        """Stop real-time monitoring"""
        self._monitoring_active = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        self.logger.info("Stopped changelog error monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for real-time error tracking"""
        while self._monitoring_active:
            try:
                await self._collect_monitoring_data()
                await self._check_system_health()
                await self._generate_optimization_recommendations()
                
                await asyncio.sleep(self.config.monitoring_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as error:
                self.logger.error(f"Error in monitoring loop: {error}")
                await asyncio.sleep(self.config.monitoring_interval_seconds)
    
    async def _collect_monitoring_data(self):
        """Collect and store monitoring data"""
        try:
            # Get error statistics
            error_stats = self.error_handler.get_error_statistics(
                time_window=timedelta(hours=1)
            )
            
            # Get performance statistics
            perf_stats = self.error_handler.get_performance_statistics(
                time_window=timedelta(hours=1)
            )
            
            # Store in monitoring data manager
            monitoring_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "component": "changelog_error_handler",
                "error_statistics": error_stats,
                "performance_statistics": perf_stats,
                "circuit_breaker_states": {
                    service: breaker.state.value
                    for service, breaker in self.error_handler.circuit_breakers.items()
                }
            }
            
            if self.config.enable_analytics:
                await self.monitoring_data_manager.store_monitoring_data(
                    "changelog_errors",
                    monitoring_data
                )
            
        except Exception as error:
            self.logger.error(f"Failed to collect monitoring data: {error}")
    
    async def _check_system_health(self):
        """Check system health and trigger alerts if necessary"""
        try:
            health_data = await self.error_handler.health_check()
            
            # Check error rate threshold
            error_stats = health_data.get("error_statistics", {})
            error_rate = error_stats.get("error_rate", 0)
            
            if error_rate > self.config.error_threshold_percentage:
                await self._send_health_alert(
                    "high_error_rate",
                    f"Changelog error rate ({error_rate:.1f}%) exceeds threshold ({self.config.error_threshold_percentage}%)",
                    "high",
                    {
                        "error_rate": error_rate,
                        "threshold": self.config.error_threshold_percentage,
                        "error_breakdown": error_stats.get("errors_by_category", {})
                    }
                )
            
            # Check performance thresholds
            perf_stats = health_data.get("performance_statistics", {})
            avg_duration = perf_stats.get("average_duration", 0)
            
            if avg_duration > self.config.performance_threshold_seconds:
                await self._send_health_alert(
                    "performance_degradation",
                    f"Average changelog generation time ({avg_duration:.1f}s) exceeds threshold ({self.config.performance_threshold_seconds}s)",
                    "medium",
                    {
                        "average_duration": avg_duration,
                        "threshold": self.config.performance_threshold_seconds,
                        "max_duration": perf_stats.get("max_duration", 0)
                    }
                )
            
            # Check circuit breaker states
            circuit_breakers = health_data.get("circuit_breakers", {})
            open_breakers = [
                service for service, state in circuit_breakers.items()
                if state.get("state") == "open"
            ]
            
            if open_breakers:
                await self._send_health_alert(
                    "circuit_breakers_open",
                    f"Circuit breakers open for services: {', '.join(open_breakers)}",
                    "high",
                    {
                        "open_services": open_breakers,
                        "circuit_breaker_details": circuit_breakers
                    }
                )
            
        except Exception as error:
            self.logger.error(f"Failed to check system health: {error}")
    
    async def _generate_optimization_recommendations(self):
        """Generate and store optimization recommendations"""
        try:
            recommendations = self.error_handler.get_optimization_recommendations()
            
            if recommendations:
                # Store recommendations in analytics system
                if self.config.enable_analytics:
                    await self.monitoring_data_manager.store_monitoring_data(
                        "changelog_optimization_recommendations",
                        {
                            "timestamp": datetime.utcnow().isoformat(),
                            "recommendations": recommendations
                        }
                    )
                
                # Send high-priority recommendations as alerts
                high_priority_recs = [
                    rec for rec in recommendations 
                    if rec.get("priority") == "high"
                ]
                
                if high_priority_recs:
                    await self._send_optimization_alert(high_priority_recs)
            
        except Exception as error:
            self.logger.error(f"Failed to generate optimization recommendations: {error}")
    
    async def _monitoring_callback(self, metrics_data: Dict[str, Any]):
        """Callback for monitoring metrics from error handler"""
        try:
            # Enhance metrics with additional context
            enhanced_metrics = {
                **metrics_data,
                "component": "changelog_error_handler",
                "monitoring_timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to real-time monitor
            if self.config.enable_real_time_monitoring:
                await self.real_time_monitor.record_metric(
                    "changelog_error_metrics",
                    enhanced_metrics
                )
            
            # Store in monitoring data manager
            if self.config.enable_analytics:
                await self.monitoring_data_manager.store_monitoring_data(
                    "changelog_error_metrics",
                    enhanced_metrics
                )
            
        except Exception as error:
            self.logger.error(f"Failed to process monitoring callback: {error}")
    
    async def _alerting_callback(self, alert_data: Dict[str, Any]):
        """Callback for alerts from error handler"""
        try:
            # Determine alert severity and channels
            severity = alert_data.get("severity", "medium")
            alert_type = alert_data.get("type", "error")
            
            # Create alert message
            if alert_type == "performance_threshold_exceeded":
                title = f"🚨 Changelog Performance Alert"
                message = self._format_performance_alert(alert_data)
            else:
                title = f"🔥 Changelog Error Alert"
                message = self._format_error_alert(alert_data)
            
            # Send alert through alerting system
            if self.config.enable_alerting:
                await self.alerting_system.send_alert(
                    title=title,
                    message=message,
                    severity=severity,
                    channels=self.config.alert_channels,
                    metadata=alert_data
                )
            
        except Exception as error:
            self.logger.error(f"Failed to process alerting callback: {error}")
    
    async def _send_health_alert(self, 
                               alert_type: str, 
                               message: str, 
                               severity: str, 
                               metadata: Dict[str, Any]):
        """Send system health alert"""
        if not self.config.enable_alerting:
            return
        
        try:
            title = f"🏥 Changelog System Health Alert"
            
            await self.alerting_system.send_alert(
                title=title,
                message=message,
                severity=severity,
                channels=self.config.alert_channels,
                metadata={
                    "alert_type": alert_type,
                    "component": "changelog_error_handler",
                    **metadata
                }
            )
            
        except Exception as error:
            self.logger.error(f"Failed to send health alert: {error}")
    
    async def _send_optimization_alert(self, recommendations: List[Dict[str, Any]]):
        """Send optimization recommendations alert"""
        if not self.config.enable_alerting:
            return
        
        try:
            title = "🔧 Changelog Optimization Recommendations"
            
            message_parts = ["High-priority optimization recommendations:"]
            for rec in recommendations:
                message_parts.append(
                    f"• **{rec['type'].title()}**: {rec['description']}\n"
                    f"  *Recommendation*: {rec['recommendation']}"
                )
            
            message = "\n\n".join(message_parts)
            
            await self.alerting_system.send_alert(
                title=title,
                message=message,
                severity="medium",
                channels=self.config.alert_channels,
                metadata={
                    "alert_type": "optimization_recommendations",
                    "component": "changelog_error_handler",
                    "recommendations": recommendations
                }
            )
            
        except Exception as error:
            self.logger.error(f"Failed to send optimization alert: {error}")
    
    def _format_error_alert(self, alert_data: Dict[str, Any]) -> str:
        """Format error alert message"""
        severity = alert_data.get("severity", "unknown")
        category = alert_data.get("category", "unknown")
        service = alert_data.get("service", "unknown")
        error_message = alert_data.get("error_message", "No details available")
        recovery_success = alert_data.get("recovery_success", False)
        recovery_action = alert_data.get("recovery_action", "unknown")
        
        status_emoji = "✅" if recovery_success else "❌"
        
        message = f"""
**Severity**: {severity.upper()}
**Category**: {category}
**Service**: {service}
**Error**: {error_message}

**Recovery Status**: {status_emoji} {'Successful' if recovery_success else 'Failed'}
**Recovery Action**: {recovery_action}

**Escalation Required**: {'Yes' if alert_data.get('escalation_required') else 'No'}
**Team**: {alert_data.get('team_id', 'Unknown')}
**Timestamp**: {alert_data.get('timestamp', 'Unknown')}
        """.strip()
        
        return message
    
    def _format_performance_alert(self, alert_data: Dict[str, Any]) -> str:
        """Format performance alert message"""
        metric = alert_data.get("metric", "unknown")
        value = alert_data.get("value", 0)
        threshold = alert_data.get("threshold", 0)
        operation = alert_data.get("operation", "unknown")
        
        message = f"""
**Performance Issue Detected**

**Metric**: {metric}
**Current Value**: {value}
**Threshold**: {threshold}
**Operation**: {operation}

**Recommendation**: Review system performance and consider optimization measures.
        """.strip()
        
        return message
    
    async def get_monitoring_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive monitoring dashboard data"""
        try:
            # Get current health status
            health_data = await self.error_handler.health_check()
            
            # Get recent monitoring data
            recent_data = await self.monitoring_data_manager.get_recent_data(
                "changelog_errors",
                time_window=timedelta(hours=24)
            )
            
            # Get optimization recommendations
            recommendations = self.error_handler.get_optimization_recommendations()
            
            return {
                "status": "healthy" if health_data.get("error_statistics", {}).get("error_rate", 0) < self.config.error_threshold_percentage else "degraded",
                "last_updated": datetime.utcnow().isoformat(),
                "health_data": health_data,
                "recent_monitoring_data": recent_data,
                "optimization_recommendations": recommendations,
                "monitoring_config": {
                    "error_threshold": self.config.error_threshold_percentage,
                    "performance_threshold": self.config.performance_threshold_seconds,
                    "monitoring_interval": self.config.monitoring_interval_seconds,
                    "alerting_enabled": self.config.enable_alerting,
                    "real_time_monitoring_enabled": self.config.enable_real_time_monitoring
                }
            }
            
        except Exception as error:
            self.logger.error(f"Failed to get monitoring dashboard data: {error}")
            return {
                "status": "error",
                "error": str(error),
                "last_updated": datetime.utcnow().isoformat()
            }
    
    async def handle_changelog_error(self, 
                                   error: Exception, 
                                   context: Dict[str, Any]) -> RecoveryResult:
        """Main entry point for handling changelog errors with full monitoring integration"""
        return await self.error_handler.handle_error(error, context)
    
    def register_fallback_data_source(self, service: str, callback):
        """Register fallback data source for a service"""
        self.error_handler.register_fallback_data_source(service, callback)
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_monitoring()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop_monitoring()


# Global monitoring integration instance
changelog_monitoring = ChangelogMonitoringIntegration()