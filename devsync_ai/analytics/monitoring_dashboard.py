"""
Monitoring Dashboard for DevSync AI Hook System.

This module provides a comprehensive monitoring dashboard with real-time
metrics visualization, alerting, and system status tracking.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json

from devsync_ai.analytics.system_health_monitor import get_health_monitor, SystemHealthMonitor
from devsync_ai.analytics.hook_analytics_engine import HookAnalyticsEngine
from devsync_ai.analytics.hook_monitoring_dashboard import get_dashboard, HookMonitoringDashboard
from devsync_ai.hooks.hook_registry_manager import get_hook_registry_manager

logger = logging.getLogger(__name__)


class DashboardMetricType(Enum):
    """Types of dashboard metrics."""
    SYSTEM_HEALTH = "system_health"
    HOOK_PERFORMANCE = "hook_performance"
    RESOURCE_USAGE = "resource_usage"
    ALERT_STATUS = "alert_status"
    THROUGHPUT = "throughput"
    ERROR_RATES = "error_rates"


@dataclass
class DashboardWidget:
    """Dashboard widget configuration."""
    widget_id: str
    widget_type: str
    title: str
    metric_type: DashboardMetricType
    refresh_interval_seconds: int
    configuration: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=dict)


@dataclass
class DashboardLayout:
    """Dashboard layout configuration."""
    layout_id: str
    name: str
    description: str
    widgets: List[DashboardWidget]
    created_at: datetime
    updated_at: datetime


class MonitoringDashboard:
    """
    Comprehensive monitoring dashboard for the hook system.
    
    Provides real-time metrics visualization, alerting, and
    system status monitoring capabilities.
    """
    
    def __init__(self):
        """Initialize the monitoring dashboard."""
        self.health_monitor: Optional[SystemHealthMonitor] = None
        self.analytics_engine: Optional[HookAnalyticsEngine] = None
        self.hook_dashboard: Optional[HookMonitoringDashboard] = None
        
        # Dashboard layouts
        self.layouts: Dict[str, DashboardLayout] = {}
        
        # Real-time data cache
        self.metrics_cache: Dict[str, Any] = {}
        self.last_update: datetime = datetime.min
        
        # Initialize default layouts
        self._initialize_default_layouts()
    
    async def initialize(self):
        """Initialize the monitoring dashboard."""
        try:
            # Initialize monitoring components
            self.health_monitor = await get_health_monitor()
            self.analytics_engine = HookAnalyticsEngine()
            self.hook_dashboard = await get_dashboard()
            
            # Start background data collection
            await self._start_data_collection()
            
            logger.info("Monitoring dashboard initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring dashboard: {e}", exc_info=True)
            raise
    
    def _initialize_default_layouts(self):
        """Initialize default dashboard layouts."""
        # System Overview Layout
        system_overview_widgets = [
            DashboardWidget(
                widget_id="system_health_status",
                widget_type="status_indicator",
                title="System Health",
                metric_type=DashboardMetricType.SYSTEM_HEALTH,
                refresh_interval_seconds=30,
                position={"x": 0, "y": 0, "width": 4, "height": 2}
            ),
            DashboardWidget(
                widget_id="resource_usage_chart",
                widget_type="line_chart",
                title="Resource Usage",
                metric_type=DashboardMetricType.RESOURCE_USAGE,
                refresh_interval_seconds=15,
                configuration={
                    "metrics": ["cpu_usage", "memory_usage", "disk_usage"],
                    "time_range": "1h"
                },
                position={"x": 4, "y": 0, "width": 8, "height": 4}
            ),
            DashboardWidget(
                widget_id="active_alerts",
                widget_type="alert_list",
                title="Active Alerts",
                metric_type=DashboardMetricType.ALERT_STATUS,
                refresh_interval_seconds=10,
                position={"x": 0, "y": 2, "width": 4, "height": 4}
            ),
            DashboardWidget(
                widget_id="hook_throughput",
                widget_type="gauge",
                title="Hook Throughput",
                metric_type=DashboardMetricType.THROUGHPUT,
                refresh_interval_seconds=30,
                configuration={
                    "unit": "executions/min",
                    "max_value": 100
                },
                position={"x": 0, "y": 6, "width": 3, "height": 3}
            ),
            DashboardWidget(
                widget_id="error_rate",
                widget_type="gauge",
                title="Error Rate",
                metric_type=DashboardMetricType.ERROR_RATES,
                refresh_interval_seconds=30,
                configuration={
                    "unit": "%",
                    "max_value": 100,
                    "warning_threshold": 5,
                    "critical_threshold": 15
                },
                position={"x": 3, "y": 6, "width": 3, "height": 3}
            )
        ]
        
        self.layouts["system_overview"] = DashboardLayout(
            layout_id="system_overview",
            name="System Overview",
            description="High-level system health and performance metrics",
            widgets=system_overview_widgets,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Hook Performance Layout
        hook_performance_widgets = [
            DashboardWidget(
                widget_id="hook_execution_timeline",
                widget_type="timeline_chart",
                title="Hook Execution Timeline",
                metric_type=DashboardMetricType.HOOK_PERFORMANCE,
                refresh_interval_seconds=15,
                configuration={
                    "time_range": "1h",
                    "group_by": "hook_type"
                },
                position={"x": 0, "y": 0, "width": 12, "height": 4}
            ),
            DashboardWidget(
                widget_id="hook_success_rates",
                widget_type="bar_chart",
                title="Hook Success Rates",
                metric_type=DashboardMetricType.HOOK_PERFORMANCE,
                refresh_interval_seconds=60,
                configuration={
                    "group_by": "hook_type",
                    "metric": "success_rate"
                },
                position={"x": 0, "y": 4, "width": 6, "height": 4}
            ),
            DashboardWidget(
                widget_id="hook_response_times",
                widget_type="bar_chart",
                title="Average Response Times",
                metric_type=DashboardMetricType.HOOK_PERFORMANCE,
                refresh_interval_seconds=60,
                configuration={
                    "group_by": "hook_type",
                    "metric": "average_execution_time_ms"
                },
                position={"x": 6, "y": 4, "width": 6, "height": 4}
            )
        ]
        
        self.layouts["hook_performance"] = DashboardLayout(
            layout_id="hook_performance",
            name="Hook Performance",
            description="Detailed hook execution performance and metrics",
            widgets=hook_performance_widgets,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Team Analytics Layout
        team_analytics_widgets = [
            DashboardWidget(
                widget_id="team_productivity_scores",
                widget_type="scorecard",
                title="Team Productivity Scores",
                metric_type=DashboardMetricType.HOOK_PERFORMANCE,
                refresh_interval_seconds=300,  # 5 minutes
                configuration={
                    "group_by": "team_id",
                    "metric": "productivity_score"
                },
                position={"x": 0, "y": 0, "width": 12, "height": 3}
            ),
            DashboardWidget(
                widget_id="team_hook_usage",
                widget_type="pie_chart",
                title="Hook Usage by Team",
                metric_type=DashboardMetricType.HOOK_PERFORMANCE,
                refresh_interval_seconds=120,
                configuration={
                    "group_by": "team_id",
                    "metric": "total_executions"
                },
                position={"x": 0, "y": 3, "width": 6, "height": 4}
            ),
            DashboardWidget(
                widget_id="team_response_times",
                widget_type="heatmap",
                title="Response Time Heatmap",
                metric_type=DashboardMetricType.HOOK_PERFORMANCE,
                refresh_interval_seconds=120,
                configuration={
                    "x_axis": "team_id",
                    "y_axis": "hook_type",
                    "metric": "average_execution_time_ms"
                },
                position={"x": 6, "y": 3, "width": 6, "height": 4}
            )
        ]
        
        self.layouts["team_analytics"] = DashboardLayout(
            layout_id="team_analytics",
            name="Team Analytics",
            description="Team-specific performance and productivity metrics",
            widgets=team_analytics_widgets,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    async def _start_data_collection(self):
        """Start background data collection for dashboard metrics."""
        asyncio.create_task(self._data_collection_loop())
    
    async def _data_collection_loop(self):
        """Background loop for collecting dashboard metrics."""
        while True:
            try:
                await self._collect_dashboard_metrics()
                await asyncio.sleep(15)  # Collect every 15 seconds
            except Exception as e:
                logger.error(f"Error in data collection loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _collect_dashboard_metrics(self):
        """Collect metrics for dashboard widgets."""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Collect system health metrics
            if self.health_monitor:
                system_health = await self.health_monitor.get_system_health_status()
                self.metrics_cache["system_health"] = system_health
            
            # Collect hook performance metrics
            if self.analytics_engine:
                system_metrics = await self.analytics_engine.get_system_health_metrics()
                self.metrics_cache["hook_system_metrics"] = system_metrics.__dict__
            
            # Collect hook dashboard metrics
            if self.hook_dashboard:
                dashboard_data = await self.hook_dashboard.get_dashboard_data()
                self.metrics_cache["hook_dashboard"] = dashboard_data
            
            # Collect registry metrics
            registry_manager = await get_hook_registry_manager()
            if registry_manager:
                hook_statuses = await registry_manager.get_all_hook_statuses()
                self.metrics_cache["hook_statuses"] = hook_statuses
            
            self.last_update = current_time
            
        except Exception as e:
            logger.error(f"Failed to collect dashboard metrics: {e}", exc_info=True)
    
    async def get_dashboard_layout(self, layout_id: str) -> Optional[DashboardLayout]:
        """Get a dashboard layout by ID."""
        return self.layouts.get(layout_id)
    
    async def get_available_layouts(self) -> List[Dict[str, Any]]:
        """Get list of available dashboard layouts."""
        return [
            {
                "layout_id": layout.layout_id,
                "name": layout.name,
                "description": layout.description,
                "widget_count": len(layout.widgets),
                "created_at": layout.created_at.isoformat(),
                "updated_at": layout.updated_at.isoformat()
            }
            for layout in self.layouts.values()
        ]
    
    async def get_widget_data(self, widget_id: str, layout_id: str) -> Dict[str, Any]:
        """Get data for a specific dashboard widget."""
        layout = self.layouts.get(layout_id)
        if not layout:
            return {"error": "Layout not found"}
        
        widget = next((w for w in layout.widgets if w.widget_id == widget_id), None)
        if not widget:
            return {"error": "Widget not found"}
        
        try:
            return await self._generate_widget_data(widget)
        except Exception as e:
            logger.error(f"Failed to generate widget data: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _generate_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Generate data for a specific widget."""
        if widget.metric_type == DashboardMetricType.SYSTEM_HEALTH:
            return await self._get_system_health_data(widget)
        elif widget.metric_type == DashboardMetricType.RESOURCE_USAGE:
            return await self._get_resource_usage_data(widget)
        elif widget.metric_type == DashboardMetricType.ALERT_STATUS:
            return await self._get_alert_status_data(widget)
        elif widget.metric_type == DashboardMetricType.HOOK_PERFORMANCE:
            return await self._get_hook_performance_data(widget)
        elif widget.metric_type == DashboardMetricType.THROUGHPUT:
            return await self._get_throughput_data(widget)
        elif widget.metric_type == DashboardMetricType.ERROR_RATES:
            return await self._get_error_rates_data(widget)
        else:
            return {"error": "Unknown metric type"}
    
    async def _get_system_health_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get system health data for widget."""
        system_health = self.metrics_cache.get("system_health", {})
        
        return {
            "widget_id": widget.widget_id,
            "widget_type": widget.widget_type,
            "title": widget.title,
            "data": {
                "overall_status": system_health.get("overall_status", "unknown"),
                "components": system_health.get("components", {}),
                "active_alerts": system_health.get("active_alerts", 0),
                "last_update": system_health.get("timestamp", "")
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _get_resource_usage_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get resource usage data for widget."""
        system_health = self.metrics_cache.get("system_health", {})
        resources = system_health.get("system_resources", {})
        
        # Get historical data if available
        if self.health_monitor:
            time_range = widget.configuration.get("time_range", "1h")
            hours = int(time_range.rstrip('h'))
            history = await self.health_monitor.get_performance_history(hours)
        else:
            history = []
        
        return {
            "widget_id": widget.widget_id,
            "widget_type": widget.widget_type,
            "title": widget.title,
            "data": {
                "current": {
                    "cpu_usage": resources.get("cpu_usage", 0),
                    "memory_usage": resources.get("memory_usage", 0),
                    "disk_usage": resources.get("disk_usage", 0)
                },
                "history": history,
                "metrics": widget.configuration.get("metrics", ["cpu_usage", "memory_usage"])
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _get_alert_status_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get alert status data for widget."""
        alerts = []
        
        # Get system alerts
        if self.health_monitor:
            system_alerts = await self.health_monitor.get_active_alerts()
            alerts.extend(system_alerts)
        
        # Get analytics alerts
        if self.analytics_engine:
            analytics_alerts = await self.analytics_engine.get_active_alerts()
            for alert in analytics_alerts:
                alerts.append({
                    "alert_id": alert.alert_id,
                    "component": "analytics",
                    "severity": alert.severity.value,
                    "message": alert.title,
                    "triggered_at": alert.triggered_at.isoformat()
                })
        
        return {
            "widget_id": widget.widget_id,
            "widget_type": widget.widget_type,
            "title": widget.title,
            "data": {
                "total_alerts": len(alerts),
                "alerts": alerts[:10],  # Show top 10 alerts
                "severity_counts": self._count_alerts_by_severity(alerts)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _get_hook_performance_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get hook performance data for widget."""
        hook_statuses = self.metrics_cache.get("hook_statuses", [])
        
        # Process data based on widget configuration
        group_by = widget.configuration.get("group_by", "hook_type")
        metric = widget.configuration.get("metric", "success_rate")
        
        grouped_data = {}
        for status in hook_statuses:
            key = status.get(group_by, "unknown")
            if key not in grouped_data:
                grouped_data[key] = []
            grouped_data[key].append(status)
        
        # Calculate aggregated metrics
        chart_data = []
        for key, statuses in grouped_data.items():
            if metric == "success_rate":
                values = [s["statistics"]["success_rate"] for s in statuses]
                value = sum(values) / len(values) if values else 0
            elif metric == "average_execution_time_ms":
                values = [s["statistics"]["average_execution_time_ms"] for s in statuses]
                value = sum(values) / len(values) if values else 0
            elif metric == "total_executions":
                value = sum(s["statistics"]["total_executions"] for s in statuses)
            else:
                value = 0
            
            chart_data.append({
                "label": key,
                "value": value,
                "count": len(statuses)
            })
        
        return {
            "widget_id": widget.widget_id,
            "widget_type": widget.widget_type,
            "title": widget.title,
            "data": {
                "chart_data": chart_data,
                "metric": metric,
                "group_by": group_by,
                "total_hooks": len(hook_statuses)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _get_throughput_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get throughput data for widget."""
        hook_metrics = self.metrics_cache.get("hook_system_metrics", {})
        
        throughput = hook_metrics.get("executions_per_minute", 0)
        max_value = widget.configuration.get("max_value", 100)
        
        return {
            "widget_id": widget.widget_id,
            "widget_type": widget.widget_type,
            "title": widget.title,
            "data": {
                "current_value": throughput,
                "max_value": max_value,
                "percentage": min(100, (throughput / max_value) * 100),
                "unit": widget.configuration.get("unit", "executions/min")
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _get_error_rates_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get error rates data for widget."""
        hook_metrics = self.metrics_cache.get("hook_system_metrics", {})
        
        error_rate = hook_metrics.get("error_count_last_hour", 0)
        total_executions = hook_metrics.get("total_executions", 1)
        error_percentage = (error_rate / total_executions) * 100 if total_executions > 0 else 0
        
        warning_threshold = widget.configuration.get("warning_threshold", 5)
        critical_threshold = widget.configuration.get("critical_threshold", 15)
        
        # Determine status
        if error_percentage >= critical_threshold:
            status = "critical"
        elif error_percentage >= warning_threshold:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "widget_id": widget.widget_id,
            "widget_type": widget.widget_type,
            "title": widget.title,
            "data": {
                "current_value": error_percentage,
                "max_value": 100,
                "status": status,
                "warning_threshold": warning_threshold,
                "critical_threshold": critical_threshold,
                "unit": widget.configuration.get("unit", "%")
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _count_alerts_by_severity(self, alerts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count alerts by severity level."""
        counts = {"critical": 0, "warning": 0, "info": 0}
        
        for alert in alerts:
            severity = alert.get("severity", "info").lower()
            if severity in counts:
                counts[severity] += 1
        
        return counts
    
    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get overall dashboard summary."""
        system_health = self.metrics_cache.get("system_health", {})
        hook_metrics = self.metrics_cache.get("hook_system_metrics", {})
        hook_statuses = self.metrics_cache.get("hook_statuses", [])
        
        # Calculate summary statistics
        total_hooks = len(hook_statuses)
        active_hooks = len([s for s in hook_statuses if s["statistics"]["total_executions"] > 0])
        
        overall_success_rate = 0
        if hook_statuses:
            success_rates = [s["statistics"]["success_rate"] for s in hook_statuses]
            overall_success_rate = sum(success_rates) / len(success_rates)
        
        return {
            "system_status": system_health.get("overall_status", "unknown"),
            "total_hooks": total_hooks,
            "active_hooks": active_hooks,
            "overall_success_rate": overall_success_rate,
            "active_alerts": system_health.get("active_alerts", 0),
            "last_update": self.last_update.isoformat(),
            "available_layouts": len(self.layouts),
            "monitoring_active": system_health.get("monitoring_active", False)
        }


# Global monitoring dashboard instance
_monitoring_dashboard: Optional[MonitoringDashboard] = None


async def get_monitoring_dashboard() -> MonitoringDashboard:
    """Get the global monitoring dashboard instance."""
    global _monitoring_dashboard
    if _monitoring_dashboard is None:
        _monitoring_dashboard = MonitoringDashboard()
        await _monitoring_dashboard.initialize()
    return _monitoring_dashboard