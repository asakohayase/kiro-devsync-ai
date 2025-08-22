"""
Health Check API Routes for DevSync AI Hook System.

This module provides REST API endpoints for system health monitoring,
diagnostics, and status checks.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from enum import Enum

from devsync_ai.analytics.system_health_monitor import get_health_monitor, DiagnosticLevel
from devsync_ai.analytics.monitoring_dashboard import get_monitoring_dashboard
from devsync_ai.analytics.diagnostic_tools import SystemDiagnosticTools, DiagnosticCategory
from devsync_ai.hooks.hook_registry_manager import get_hook_registry_manager
from devsync_ai.analytics.hook_analytics_engine import HookAnalyticsEngine

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/health", tags=["health"])


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"


class ComponentStatus(str, Enum):
    """Component status levels."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: HealthStatus
    timestamp: datetime
    components: Dict[str, Dict[str, Any]]
    system_resources: Dict[str, float]
    active_alerts: int
    monitoring_active: bool
    uptime_seconds: Optional[float] = None


class DiagnosticResponse(BaseModel):
    """Diagnostic response model."""
    report_id: str
    generated_at: datetime
    overall_health_score: float
    issues_count: int
    critical_issues: int
    warning_issues: int
    recommendations_count: int


class ComponentHealthResponse(BaseModel):
    """Component health response model."""
    component_name: str
    status: ComponentStatus
    response_time_ms: float
    last_check: datetime
    error_message: Optional[str] = None
    metadata: Dict[str, Any]


@router.get("/", response_model=HealthCheckResponse)
async def get_system_health():
    """
    Get overall system health status.
    
    Returns comprehensive system health information including
    component status, resource usage, and active alerts.
    """
    try:
        health_monitor = await get_health_monitor()
        health_status = await health_monitor.get_system_health_status()
        
        # Map status to enum
        status_mapping = {
            "healthy": HealthStatus.HEALTHY,
            "warning": HealthStatus.WARNING,
            "critical": HealthStatus.CRITICAL,
            "error": HealthStatus.ERROR
        }
        
        return HealthCheckResponse(
            status=status_mapping.get(health_status["overall_status"], HealthStatus.ERROR),
            timestamp=datetime.fromisoformat(health_status["timestamp"]),
            components=health_status["components"],
            system_resources=health_status["system_resources"],
            active_alerts=health_status["active_alerts"],
            monitoring_active=health_status["monitoring_active"]
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/components", response_model=List[ComponentHealthResponse])
async def get_component_health():
    """
    Get detailed health status for all system components.
    
    Returns individual health status for each monitored component
    including response times and error information.
    """
    try:
        health_monitor = await get_health_monitor()
        health_status = await health_monitor.get_system_health_status()
        
        components = []
        for name, component_data in health_status["components"].items():
            components.append(ComponentHealthResponse(
                component_name=name,
                status=ComponentStatus(component_data["status"]),
                response_time_ms=component_data["response_time_ms"],
                last_check=datetime.fromisoformat(component_data["last_check"]),
                error_message=component_data.get("error_message"),
                metadata=component_data.get("metadata", {})
            ))
        
        return components
        
    except Exception as e:
        logger.error(f"Component health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Component health check failed: {str(e)}")


@router.get("/components/{component_name}")
async def get_component_health_detail(component_name: str):
    """
    Get detailed health information for a specific component.
    
    Args:
        component_name: Name of the component to check
        
    Returns:
        Detailed health information for the specified component
    """
    try:
        health_monitor = await get_health_monitor()
        health_status = await health_monitor.get_system_health_status()
        
        if component_name not in health_status["components"]:
            raise HTTPException(status_code=404, detail=f"Component '{component_name}' not found")
        
        component_data = health_status["components"][component_name]
        
        return {
            "component_name": component_name,
            "status": component_data["status"],
            "response_time_ms": component_data["response_time_ms"],
            "last_check": component_data["last_check"],
            "error_message": component_data.get("error_message"),
            "metadata": component_data.get("metadata", {}),
            "health_history": await health_monitor.get_component_health_history(component_name, hours=24)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Component detail check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Component detail check failed: {str(e)}")


@router.get("/diagnostics", response_model=DiagnosticResponse)
async def run_system_diagnostics(
    categories: Optional[List[str]] = Query(None, description="Diagnostic categories to check"),
    level: str = Query("detailed", description="Diagnostic level: basic, detailed, comprehensive")
):
    """
    Run comprehensive system diagnostics.
    
    Args:
        categories: Specific diagnostic categories to check
        level: Diagnostic detail level
        
    Returns:
        Comprehensive diagnostic report with issues and recommendations
    """
    try:
        diagnostic_tools = SystemDiagnosticTools()
        
        # Parse diagnostic level
        diagnostic_level = DiagnosticLevel.DETAILED
        if level.lower() == "basic":
            diagnostic_level = DiagnosticLevel.BASIC
        elif level.lower() == "comprehensive":
            diagnostic_level = DiagnosticLevel.COMPREHENSIVE
        
        # Parse categories
        diagnostic_categories = None
        if categories:
            diagnostic_categories = []
            for category in categories:
                try:
                    diagnostic_categories.append(DiagnosticCategory(category.lower()))
                except ValueError:
                    logger.warning(f"Unknown diagnostic category: {category}")
        
        # Run diagnostics
        report = await diagnostic_tools.run_comprehensive_diagnostics(diagnostic_categories)
        
        # Count issues by severity
        critical_issues = len([i for i in report.issues if i.severity.value == "critical"])
        warning_issues = len([i for i in report.issues if i.severity.value == "warning"])
        
        return DiagnosticResponse(
            report_id=report.report_id,
            generated_at=report.generated_at,
            overall_health_score=report.overall_health_score,
            issues_count=len(report.issues),
            critical_issues=critical_issues,
            warning_issues=warning_issues,
            recommendations_count=len(report.recommendations)
        )
        
    except Exception as e:
        logger.error(f"Diagnostics failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Diagnostics failed: {str(e)}")


@router.get("/diagnostics/{report_id}")
async def get_diagnostic_report(report_id: str):
    """
    Get detailed diagnostic report by ID.
    
    Args:
        report_id: ID of the diagnostic report
        
    Returns:
        Full diagnostic report with all issues and recommendations
    """
    try:
        # In a real implementation, this would retrieve from storage
        # For now, we'll run a fresh diagnostic
        diagnostic_tools = SystemDiagnosticTools()
        report = await diagnostic_tools.run_comprehensive_diagnostics()
        
        return {
            "report_id": report.report_id,
            "generated_at": report.generated_at.isoformat(),
            "system_info": report.system_info,
            "overall_health_score": report.overall_health_score,
            "issues": [
                {
                    "issue_id": issue.issue_id,
                    "category": issue.category.value,
                    "severity": issue.severity.value,
                    "title": issue.title,
                    "description": issue.description,
                    "affected_components": issue.affected_components,
                    "recommendations": issue.recommendations,
                    "metadata": issue.metadata,
                    "detected_at": issue.detected_at.isoformat()
                }
                for issue in report.issues
            ],
            "performance_summary": report.performance_summary,
            "recommendations": report.recommendations
        }
        
    except Exception as e:
        logger.error(f"Failed to get diagnostic report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get diagnostic report: {str(e)}")


@router.get("/hooks")
async def get_hook_system_health():
    """
    Get health status for the hook system.
    
    Returns:
        Hook system health information including registry status,
        hook performance metrics, and execution statistics
    """
    try:
        registry_manager = await get_hook_registry_manager()
        if not registry_manager:
            return {
                "status": "unavailable",
                "message": "Hook registry manager not available",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Get hook statuses
        hook_statuses = await registry_manager.get_all_hook_statuses()
        system_health = await registry_manager.get_system_health()
        
        # Calculate summary statistics
        total_hooks = len(hook_statuses)
        active_hooks = len([s for s in hook_statuses if s["statistics"]["total_executions"] > 0])
        
        success_rates = [s["statistics"]["success_rate"] for s in hook_statuses if s["statistics"]["total_executions"] > 0]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
        
        response_times = [s["statistics"]["average_execution_time_ms"] for s in hook_statuses if s["statistics"]["total_executions"] > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "status": system_health.health_status.value if system_health else "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_hooks": total_hooks,
                "active_hooks": active_hooks,
                "inactive_hooks": total_hooks - active_hooks,
                "average_success_rate": avg_success_rate,
                "average_response_time_ms": avg_response_time
            },
            "hooks": hook_statuses,
            "system_metrics": system_health.__dict__ if system_health else None
        }
        
    except Exception as e:
        logger.error(f"Hook system health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Hook system health check failed: {str(e)}")


@router.get("/hooks/{hook_id}")
async def get_hook_health_detail(hook_id: str):
    """
    Get detailed health information for a specific hook.
    
    Args:
        hook_id: ID of the hook to check
        
    Returns:
        Detailed health information for the specified hook
    """
    try:
        registry_manager = await get_hook_registry_manager()
        if not registry_manager:
            raise HTTPException(status_code=503, detail="Hook registry manager not available")
        
        hook_status = await registry_manager.get_hook_status(hook_id)
        if not hook_status:
            raise HTTPException(status_code=404, detail=f"Hook '{hook_id}' not found")
        
        # Get additional analytics
        analytics_engine = HookAnalyticsEngine()
        hook_metrics = await analytics_engine.get_hook_performance_metrics(hook_id)
        
        return {
            "hook_id": hook_id,
            "status": hook_status,
            "performance_metrics": hook_metrics.__dict__ if hook_metrics else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hook detail check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Hook detail check failed: {str(e)}")


@router.get("/alerts")
async def get_active_alerts():
    """
    Get all active system alerts.
    
    Returns:
        List of active alerts with severity and component information
    """
    try:
        health_monitor = await get_health_monitor()
        alerts = await health_monitor.get_active_alerts()
        
        # Get analytics alerts
        analytics_engine = HookAnalyticsEngine()
        analytics_alerts = await analytics_engine.get_active_alerts()
        
        all_alerts = []
        
        # Add system alerts
        for alert in alerts:
            all_alerts.append({
                "alert_id": alert.alert_id,
                "component": alert.component,
                "severity": alert.severity,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat(),
                "source": "system"
            })
        
        # Add analytics alerts
        for alert in analytics_alerts:
            all_alerts.append({
                "alert_id": alert.alert_id,
                "component": "analytics",
                "severity": alert.severity.value,
                "message": alert.title,
                "triggered_at": alert.triggered_at.isoformat(),
                "source": "analytics"
            })
        
        return {
            "total_alerts": len(all_alerts),
            "alerts": all_alerts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.get("/metrics")
async def get_system_metrics():
    """
    Get system performance metrics.
    
    Returns:
        Current system performance metrics including resource usage,
        throughput, and response times
    """
    try:
        health_monitor = await get_health_monitor()
        health_status = await health_monitor.get_system_health_status()
        
        # Get hook metrics
        registry_manager = await get_hook_registry_manager()
        hook_metrics = {}
        if registry_manager:
            system_health = await registry_manager.get_system_health()
            if system_health:
                hook_metrics = {
                    "total_executions": system_health.total_executions,
                    "successful_executions": system_health.successful_executions,
                    "failed_executions": system_health.failed_executions,
                    "average_execution_time_ms": system_health.average_execution_time_ms,
                    "executions_per_minute": system_health.executions_per_minute
                }
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_resources": health_status["system_resources"],
            "hook_metrics": hook_metrics,
            "component_response_times": {
                name: component["response_time_ms"]
                for name, component in health_status["components"].items()
            },
            "monitoring_active": health_status["monitoring_active"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.post("/monitoring/start")
async def start_monitoring():
    """
    Start the system health monitoring.
    
    Returns:
        Status of the monitoring system startup
    """
    try:
        health_monitor = await get_health_monitor()
        await health_monitor.start_monitoring()
        
        return {
            "status": "started",
            "message": "System health monitoring started successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


@router.post("/monitoring/stop")
async def stop_monitoring():
    """
    Stop the system health monitoring.
    
    Returns:
        Status of the monitoring system shutdown
    """
    try:
        health_monitor = await get_health_monitor()
        await health_monitor.stop_monitoring()
        
        return {
            "status": "stopped",
            "message": "System health monitoring stopped successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")


@router.get("/dashboard/layouts")
async def get_dashboard_layouts():
    """
    Get available dashboard layouts.
    
    Returns:
        List of available monitoring dashboard layouts
    """
    try:
        dashboard = await get_monitoring_dashboard()
        layouts = await dashboard.get_available_layouts()
        
        return {
            "layouts": layouts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard layouts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard layouts: {str(e)}")


@router.get("/dashboard/{layout_id}")
async def get_dashboard_layout(layout_id: str):
    """
    Get dashboard layout configuration.
    
    Args:
        layout_id: ID of the dashboard layout
        
    Returns:
        Dashboard layout configuration and widget data
    """
    try:
        dashboard = await get_monitoring_dashboard()
        layout = await dashboard.get_dashboard_layout(layout_id)
        
        if not layout:
            raise HTTPException(status_code=404, detail=f"Dashboard layout '{layout_id}' not found")
        
        # Get widget data for all widgets
        widget_data = {}
        for widget in layout.widgets:
            try:
                data = await dashboard.get_widget_data(widget.widget_id, layout_id)
                widget_data[widget.widget_id] = data
            except Exception as e:
                logger.error(f"Failed to get widget data for {widget.widget_id}: {e}")
                widget_data[widget.widget_id] = {"error": str(e)}
        
        return {
            "layout_id": layout.layout_id,
            "name": layout.name,
            "description": layout.description,
            "widgets": [
                {
                    "widget_id": widget.widget_id,
                    "widget_type": widget.widget_type,
                    "title": widget.title,
                    "metric_type": widget.metric_type.value,
                    "refresh_interval_seconds": widget.refresh_interval_seconds,
                    "configuration": widget.configuration,
                    "position": widget.position,
                    "data": widget_data.get(widget.widget_id, {})
                }
                for widget in layout.widgets
            ],
            "created_at": layout.created_at.isoformat(),
            "updated_at": layout.updated_at.isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard layout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard layout: {str(e)}")


@router.get("/dashboard/{layout_id}/widgets/{widget_id}")
async def get_widget_data(layout_id: str, widget_id: str):
    """
    Get data for a specific dashboard widget.
    
    Args:
        layout_id: ID of the dashboard layout
        widget_id: ID of the widget
        
    Returns:
        Widget data for rendering
    """
    try:
        dashboard = await get_monitoring_dashboard()
        data = await dashboard.get_widget_data(widget_id, layout_id)
        
        return data
        
    except Exception as e:
        logger.error(f"Failed to get widget data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get widget data: {str(e)}")