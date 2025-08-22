"""
FastAPI endpoints for the DevSync AI Analytics Dashboard.

This module provides REST API endpoints and WebSocket support for the
comprehensive monitoring and analytics system.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
import uvicorn

from devsync_ai.analytics.hook_monitoring_dashboard import get_dashboard, HookMonitoringDashboard
from devsync_ai.analytics.productivity_analytics_engine import ProductivityAnalyticsEngine
from devsync_ai.analytics.intelligence_engine import IntelligenceEngine
from devsync_ai.analytics.hook_optimization_engine import HookOptimizationEngine
from devsync_ai.analytics.monitoring_dashboard import get_monitoring_dashboard
from devsync_ai.hooks.hook_registry_manager import get_hook_registry_manager

logger = logging.getLogger(__name__)

# Initialize analytics engines
productivity_engine = ProductivityAnalyticsEngine()
intelligence_engine = IntelligenceEngine()
optimization_engine = HookOptimizationEngine()

# FastAPI app for analytics dashboard
analytics_app = FastAPI(
    title="DevSync AI Analytics Dashboard",
    description="Comprehensive monitoring and analytics for JIRA Agent Hooks",
    version="1.0.0"
)

# Add CORS middleware
analytics_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
analytics_app.mount("/static", StaticFiles(directory="devsync_ai/analytics/static"), name="static")
templates = Jinja2Templates(directory="devsync_ai/analytics/templates")


@analytics_app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Serve the main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@analytics_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    dashboard = await get_dashboard()
    await dashboard.connect_websocket(websocket)
    
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle client requests
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message.get("type") == "request_data":
                # Send current dashboard data
                dashboard_data = await dashboard.get_dashboard_data()
                await websocket.send_text(json.dumps({
                    "type": "dashboard_data",
                    "data": dashboard_data
                }))
                
    except WebSocketDisconnect:
        dashboard.disconnect_websocket(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        dashboard.disconnect_websocket(websocket)


# System Metrics Endpoints
@analytics_app.get("/api/metrics/system")
async def get_system_metrics():
    """Get current system metrics."""
    dashboard = await get_dashboard()
    return await dashboard.get_current_metrics()


@analytics_app.get("/api/metrics/system/history")
async def get_system_metrics_history(
    hours: int = Query(1, ge=1, le=168),  # 1 hour to 1 week
    team_filter: Optional[str] = Query(None),
    hook_type_filter: Optional[str] = Query(None)
):
    """Get historical system metrics."""
    dashboard = await get_dashboard()
    return await dashboard.get_dashboard_data(
        time_range=f"{hours}h",
        team_filter=team_filter,
        hook_type_filter=hook_type_filter
    )


# Hook Performance Endpoints
@analytics_app.get("/api/hooks/metrics")
async def get_hook_metrics(
    team_id: Optional[str] = Query(None),
    hook_type: Optional[str] = Query(None)
):
    """Get hook execution metrics."""
    dashboard = await get_dashboard()
    return await dashboard.get_hook_metrics(hook_type=hook_type, team_id=team_id)


@analytics_app.get("/api/hooks/{hook_id}/performance")
async def get_hook_performance(hook_id: str):
    """Get detailed performance metrics for a specific hook."""
    # Get configuration effectiveness
    effectiveness = await optimization_engine.analyze_configuration_effectiveness(hook_id)
    
    # Get user engagement metrics
    engagement = await optimization_engine.analyze_user_engagement(hook_id)
    
    # Get performance benchmarks
    benchmarks = await optimization_engine.benchmark_performance(hook_id)
    
    # Get anomaly detection results
    anomalies = await optimization_engine.detect_performance_anomalies(hook_id)
    
    return {
        "hook_id": hook_id,
        "effectiveness": effectiveness,
        "engagement": engagement.__dict__ if engagement else None,
        "benchmarks": [b.__dict__ for b in benchmarks],
        "anomalies": anomalies
    }


@analytics_app.get("/api/hooks/{hook_id}/optimization")
async def get_hook_optimization_recommendations(
    hook_id: str,
    focus_areas: Optional[List[str]] = Query(None)
):
    """Get optimization recommendations for a hook."""
    recommendations = await optimization_engine.generate_optimization_recommendations(
        hook_id, focus_areas
    )
    
    return {
        "hook_id": hook_id,
        "recommendations": [r.__dict__ for r in recommendations]
    }


# Team Analytics Endpoints
@analytics_app.get("/api/teams/{team_id}/productivity")
async def get_team_productivity(
    team_id: str,
    days: int = Query(30, ge=1, le=90)
):
    """Get team productivity analytics."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    time_range = (start_date, end_date)
    
    # Get sprint analytics
    sprint_analytics = await productivity_engine.analyze_sprint_performance(
        team_id, f"current_sprint_{team_id}", time_range
    )
    
    # Get blocker analytics
    blocker_analytics = await productivity_engine.analyze_blocker_patterns(team_id, time_range)
    
    # Get collaboration metrics
    collaboration_metrics = await productivity_engine.analyze_team_collaboration(team_id, time_range)
    
    # Get productivity insights
    insights = await productivity_engine.generate_productivity_insights(team_id)
    
    return {
        "team_id": team_id,
        "sprint_analytics": sprint_analytics.__dict__,
        "blocker_analytics": [b.__dict__ for b in blocker_analytics],
        "collaboration_metrics": collaboration_metrics.__dict__,
        "insights": [i.__dict__ for i in insights]
    }


@analytics_app.get("/api/teams/{team_id}/health")
async def get_team_health(team_id: str):
    """Get team health insights."""
    health_insight = await intelligence_engine.analyze_team_communication_health(team_id)
    return health_insight.__dict__


@analytics_app.get("/api/teams/{team_id}/sprint-risk")
async def get_sprint_risk_assessment(
    team_id: str,
    sprint_id: Optional[str] = Query(None)
):
    """Get sprint risk assessment."""
    if not sprint_id:
        sprint_id = f"current_sprint_{team_id}"
    
    # Mock sprint data (would come from JIRA integration)
    sprint_data = {
        "planned_story_points": 30,
        "completed_story_points": 18,
        "days_remaining": 5,
        "active_blockers": 2
    }
    
    risk_assessment = await intelligence_engine.assess_sprint_risk(
        sprint_id, team_id, sprint_data
    )
    
    return risk_assessment.__dict__


# AI Insights Endpoints
@analytics_app.get("/api/insights/predictive")
async def get_predictive_insights(
    team_id: Optional[str] = Query(None),
    prediction_type: Optional[str] = Query(None)
):
    """Get AI-powered predictive insights."""
    insights = intelligence_engine.predictive_insights
    
    # Filter by team_id if provided
    if team_id:
        insights = [i for i in insights if i.team_id == team_id]
    
    # Filter by prediction type if provided
    if prediction_type:
        insights = [i for i in insights if i.prediction_type.value == prediction_type]
    
    return [i.__dict__ for i in insights]


@analytics_app.post("/api/insights/blocker-risk")
async def predict_blocker_risk(
    ticket_key: str,
    team_id: str,
    ticket_data: Dict[str, Any]
):
    """Predict blocker risk for a ticket."""
    insight = await intelligence_engine.predict_blocker_risk(ticket_key, team_id, ticket_data)
    return insight.__dict__


@analytics_app.post("/api/insights/assignment-recommendation")
async def get_assignment_recommendation(
    ticket_key: str,
    team_id: str,
    ticket_data: Dict[str, Any],
    available_assignees: List[str]
):
    """Get AI-powered assignment recommendation."""
    recommendation = await intelligence_engine.recommend_optimal_assignment(
        ticket_key, team_id, ticket_data, available_assignees
    )
    return recommendation.__dict__


# A/B Testing Endpoints
@analytics_app.post("/api/ab-tests")
async def create_ab_test(
    hook_type: str,
    team_id: str,
    variant_a_config: Dict[str, Any],
    variant_b_config: Dict[str, Any],
    metric_type: str,
    test_duration_days: int = 7
):
    """Create a new A/B test."""
    from devsync_ai.analytics.hook_optimization_engine import OptimizationMetric
    
    metric_enum = OptimizationMetric(metric_type)
    
    ab_test_result = await optimization_engine.run_ab_test(
        hook_type, team_id, variant_a_config, variant_b_config, metric_enum, test_duration_days
    )
    
    return ab_test_result.__dict__


@analytics_app.get("/api/ab-tests")
async def get_ab_tests(
    team_id: Optional[str] = Query(None),
    hook_type: Optional[str] = Query(None)
):
    """Get A/B test results."""
    tests = list(optimization_engine.ab_tests.values())
    
    # Filter by team_id if provided
    if team_id:
        tests = [t for t in tests if t.team_id == team_id]
    
    # Filter by hook_type if provided
    if hook_type:
        tests = [t for t in tests if t.hook_type == hook_type]
    
    return [t.__dict__ for t in tests]


@analytics_app.get("/api/ab-tests/{test_id}")
async def get_ab_test(test_id: str):
    """Get specific A/B test results."""
    test = optimization_engine.ab_tests.get(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")
    
    return test.__dict__


# Alerts and Notifications Endpoints
@analytics_app.get("/api/alerts")
async def get_alerts(
    severity: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None)
):
    """Get system alerts."""
    dashboard = await get_dashboard()
    return await dashboard.get_alerts(severity=severity, resolved=resolved)


@analytics_app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Mark an alert as resolved."""
    dashboard = await get_dashboard()
    success = await dashboard.resolve_alert(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert resolved successfully"}


# Export and Reporting Endpoints
@analytics_app.get("/api/reports/productivity")
async def generate_productivity_report(
    team_id: str,
    start_date: datetime,
    end_date: datetime,
    format: str = Query("json", regex="^(json|csv|pdf)$")
):
    """Generate comprehensive productivity report."""
    time_range = (start_date, end_date)
    
    # Gather all analytics data
    sprint_analytics = await productivity_engine.analyze_sprint_performance(
        team_id, f"report_sprint_{team_id}", time_range
    )
    blocker_analytics = await productivity_engine.analyze_blocker_patterns(team_id, time_range)
    collaboration_metrics = await productivity_engine.analyze_team_collaboration(team_id, time_range)
    insights = await productivity_engine.generate_productivity_insights(team_id)
    health_insight = await intelligence_engine.analyze_team_communication_health(team_id, time_range)
    
    report_data = {
        "team_id": team_id,
        "report_period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "sprint_performance": sprint_analytics.__dict__,
        "blocker_analysis": [b.__dict__ for b in blocker_analytics],
        "collaboration_metrics": collaboration_metrics.__dict__,
        "productivity_insights": [i.__dict__ for i in insights],
        "team_health": health_insight.__dict__,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if format == "json":
        return report_data
    elif format == "csv":
        # Convert to CSV format (simplified)
        return {"message": "CSV export not implemented yet", "data": report_data}
    elif format == "pdf":
        # Generate PDF report (would use a PDF library)
        return {"message": "PDF export not implemented yet", "data": report_data}


@analytics_app.get("/api/reports/system-health")
async def generate_system_health_report():
    """Generate system health report."""
    dashboard = await get_dashboard()
    
    # Get current system metrics
    system_metrics = await dashboard.get_current_metrics()
    
    # Get all hook metrics
    hook_metrics = await dashboard.get_hook_metrics()
    
    # Get recent alerts
    alerts = await dashboard.get_alerts()
    
    # Get webhook stats
    webhook_stats = await dashboard.get_webhook_stats()
    
    return {
        "report_type": "system_health",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_metrics": system_metrics,
        "hook_metrics": hook_metrics,
        "recent_alerts": alerts[:10],  # Last 10 alerts
        "webhook_statistics": webhook_stats,
        "overall_health_status": system_metrics.get("health_status", "unknown")
    }


# Configuration and Management Endpoints
@analytics_app.get("/api/config/thresholds")
async def get_alert_thresholds():
    """Get current alert thresholds."""
    dashboard = await get_dashboard()
    return dashboard.thresholds


@analytics_app.put("/api/config/thresholds")
async def update_alert_thresholds(thresholds: Dict[str, float]):
    """Update alert thresholds."""
    dashboard = await get_dashboard()
    
    # Validate thresholds
    valid_keys = set(dashboard.thresholds.keys())
    provided_keys = set(thresholds.keys())
    
    if not provided_keys.issubset(valid_keys):
        invalid_keys = provided_keys - valid_keys
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid threshold keys: {list(invalid_keys)}"
        )
    
    # Update thresholds
    dashboard.thresholds.update(thresholds)
    
    return {"message": "Thresholds updated successfully", "thresholds": dashboard.thresholds}


# Health Check and Monitoring Endpoints
@analytics_app.get("/api/health")
async def health_check():
    """Basic health check endpoint."""
    try:
        dashboard = await get_dashboard()
        registry_manager = await get_hook_registry_manager()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                "dashboard": "operational",
                "hook_registry": "operational" if registry_manager else "unavailable",
                "analytics_engines": "operational"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


@analytics_app.get("/api/health/detailed")
async def detailed_health_check():
    """Detailed health check with component diagnostics."""
    from devsync_ai.analytics.system_health_monitor import get_health_monitor
    
    try:
        health_monitor = await get_health_monitor()
        health_status = await health_monitor.get_system_health_status()
        
        return {
            "status": health_status["overall_status"],
            "timestamp": health_status["timestamp"],
            "last_check": health_status["last_health_check"],
            "components": health_status["components"],
            "system_resources": health_status["system_resources"],
            "active_alerts": health_status["active_alerts"],
            "monitoring_active": health_status["monitoring_active"]
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


@analytics_app.get("/api/health/diagnostics")
async def system_diagnostics(
    level: str = Query("detailed", regex="^(basic|detailed|comprehensive)$")
):
    """Comprehensive system diagnostics."""
    from devsync_ai.analytics.system_health_monitor import get_health_monitor, DiagnosticLevel
    
    try:
        health_monitor = await get_health_monitor()
        diagnostic_level = DiagnosticLevel(level)
        diagnostics = await health_monitor.get_detailed_diagnostics(diagnostic_level)
        
        return {
            "timestamp": diagnostics.timestamp.isoformat(),
            "overall_status": diagnostics.overall_status.value,
            "diagnostic_level": diagnostics.diagnostic_level.value,
            "components": {
                name: {
                    "status": health.status.value,
                    "response_time_ms": health.response_time_ms,
                    "last_check": health.last_check.isoformat(),
                    "error_message": health.error_message,
                    "metadata": health.metadata
                }
                for name, health in diagnostics.components.items()
            },
            "performance_metrics": diagnostics.performance_metrics,
            "resource_usage": diagnostics.resource_usage,
            "active_issues": diagnostics.active_issues,
            "recommendations": diagnostics.recommendations
        }
    except Exception as e:
        logger.error(f"System diagnostics failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


@analytics_app.get("/api/monitoring/performance")
async def get_performance_monitoring(
    hours: int = Query(1, ge=1, le=24)
):
    """Get performance monitoring data."""
    from devsync_ai.analytics.system_health_monitor import get_health_monitor
    
    try:
        health_monitor = await get_health_monitor()
        performance_history = await health_monitor.get_performance_history(hours)
        
        return {
            "time_range_hours": hours,
            "data_points": len(performance_history),
            "performance_history": performance_history
        }
    except Exception as e:
        logger.error(f"Performance monitoring failed: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@analytics_app.get("/api/monitoring/alerts")
async def get_monitoring_alerts():
    """Get active monitoring alerts."""
    from devsync_ai.analytics.system_health_monitor import get_health_monitor
    
    try:
        health_monitor = await get_health_monitor()
        alerts = await health_monitor.get_active_alerts()
        
        return {
            "total_alerts": len(alerts),
            "alerts": alerts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get monitoring alerts: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@analytics_app.post("/api/monitoring/alerts/{alert_id}/resolve")
async def resolve_monitoring_alert(alert_id: str):
    """Resolve a monitoring alert."""
    from devsync_ai.analytics.system_health_monitor import get_health_monitor
    
    try:
        health_monitor = await get_health_monitor()
        success = await health_monitor.resolve_alert(alert_id)
        
        if success:
            return {
                "message": f"Alert {alert_id} resolved successfully",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@analytics_app.get("/api/monitoring/thresholds")
async def get_monitoring_thresholds():
    """Get current monitoring thresholds."""
    from devsync_ai.analytics.system_health_monitor import get_health_monitor
    
    try:
        health_monitor = await get_health_monitor()
        return {
            "thresholds": health_monitor.thresholds,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get thresholds: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@analytics_app.put("/api/monitoring/thresholds")
async def update_monitoring_thresholds(thresholds: Dict[str, float]):
    """Update monitoring thresholds."""
    from devsync_ai.analytics.system_health_monitor import get_health_monitor
    
    try:
        health_monitor = await get_health_monitor()
        success = await health_monitor.update_thresholds(thresholds)
        
        if success:
            return {
                "message": "Thresholds updated successfully",
                "updated_thresholds": thresholds,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid threshold configuration")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Monitoring Dashboard Endpoints
@analytics_app.get("/api/dashboard/layouts")
async def get_dashboard_layouts():
    """Get available dashboard layouts."""
    try:
        monitoring_dashboard = await get_monitoring_dashboard()
        layouts = await monitoring_dashboard.get_available_layouts()
        
        return {
            "layouts": layouts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard layouts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@analytics_app.get("/api/dashboard/layouts/{layout_id}")
async def get_dashboard_layout(layout_id: str):
    """Get a specific dashboard layout."""
    try:
        monitoring_dashboard = await get_monitoring_dashboard()
        layout = await monitoring_dashboard.get_dashboard_layout(layout_id)
        
        if not layout:
            raise HTTPException(status_code=404, detail="Layout not found")
        
        return {
            "layout_id": layout.layout_id,
            "name": layout.name,
            "description": layout.description,
            "widgets": [
                {
                    "widget_id": w.widget_id,
                    "widget_type": w.widget_type,
                    "title": w.title,
                    "metric_type": w.metric_type.value,
                    "refresh_interval_seconds": w.refresh_interval_seconds,
                    "configuration": w.configuration,
                    "position": w.position
                }
                for w in layout.widgets
            ],
            "created_at": layout.created_at.isoformat(),
            "updated_at": layout.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard layout: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@analytics_app.get("/api/dashboard/widgets/{layout_id}/{widget_id}")
async def get_widget_data(layout_id: str, widget_id: str):
    """Get data for a specific dashboard widget."""
    try:
        monitoring_dashboard = await get_monitoring_dashboard()
        widget_data = await monitoring_dashboard.get_widget_data(widget_id, layout_id)
        
        if "error" in widget_data:
            raise HTTPException(status_code=404, detail=widget_data["error"])
        
        return widget_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get widget data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@analytics_app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """Get overall dashboard summary."""
    try:
        monitoring_dashboard = await get_monitoring_dashboard()
        summary = await monitoring_dashboard.get_dashboard_summary()
        
        return summary
    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Diagnostic Tools Endpoints
@analytics_app.get("/api/diagnostics/run")
async def run_system_diagnostics(
    categories: Optional[List[str]] = Query(None),
    format: str = Query("json", regex="^(json|text)$")
):
    """Run comprehensive system diagnostics."""
    from devsync_ai.analytics.diagnostic_tools import get_diagnostic_tools, DiagnosticCategory
    
    try:
        diagnostic_tools = get_diagnostic_tools()
        
        # Parse categories if provided
        diagnostic_categories = None
        if categories:
            diagnostic_categories = []
            for cat in categories:
                try:
                    diagnostic_categories.append(DiagnosticCategory(cat))
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid diagnostic category: {cat}")
        
        # Run diagnostics
        report = await diagnostic_tools.run_comprehensive_diagnostics(diagnostic_categories)
        
        if format == "text":
            report_text = await diagnostic_tools.export_diagnostic_report(report, "text")
            return {"report": report_text, "format": "text"}
        else:
            return {
                "report_id": report.report_id,
                "generated_at": report.generated_at.isoformat(),
                "system_info": report.system_info,
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
                "recommendations": report.recommendations,
                "overall_health_score": report.overall_health_score
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"System diagnostics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@analytics_app.get("/api/diagnostics/categories")
async def get_diagnostic_categories():
    """Get available diagnostic categories."""
    from devsync_ai.analytics.diagnostic_tools import DiagnosticCategory
    
    return {
        "categories": [
            {
                "value": category.value,
                "name": category.value.replace("_", " ").title(),
                "description": f"Check {category.value.replace('_', ' ')}"
            }
            for category in DiagnosticCategory
        ]
    }


@analytics_app.get("/api/diagnostics/quick-check")
async def quick_system_check():
    """Perform a quick system health check."""
    from devsync_ai.analytics.diagnostic_tools import get_diagnostic_tools, DiagnosticCategory
    
    try:
        diagnostic_tools = get_diagnostic_tools()
        
        # Run only critical checks for quick assessment
        quick_categories = [
            DiagnosticCategory.SYSTEM_RESOURCES,
            DiagnosticCategory.HOOK_PERFORMANCE,
            DiagnosticCategory.DATABASE_CONNECTIVITY
        ]
        
        report = await diagnostic_tools.run_comprehensive_diagnostics(quick_categories)
        
        # Return simplified response
        critical_issues = [i for i in report.issues if i.severity.value == "critical"]
        error_issues = [i for i in report.issues if i.severity.value == "error"]
        
        status = "healthy"
        if critical_issues:
            status = "critical"
        elif error_issues:
            status = "error"
        elif report.overall_health_score < 80:
            status = "warning"
        
        return {
            "status": status,
            "health_score": report.overall_health_score,
            "critical_issues": len(critical_issues),
            "error_issues": len(error_issues),
            "total_issues": len(report.issues),
            "top_recommendations": report.recommendations[:3],
            "timestamp": report.generated_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Quick system check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Voice Command Integration (Mock Implementation)
@analytics_app.post("/api/voice/query")
async def process_voice_query(query: str):
    """Process voice-activated status queries."""
    query_lower = query.lower()
    
    if "sprint" in query_lower and "health" in query_lower:
        # Extract team from query (simplified)
        team_id = "default_team"  # Would parse from query
        
        sprint_data = {
            "planned_story_points": 30,
            "completed_story_points": 20,
            "days_remaining": 4,
            "active_blockers": 1
        }
        
        risk_assessment = await intelligence_engine.assess_sprint_risk(
            f"current_sprint_{team_id}", team_id, sprint_data
        )
        
        response_text = f"Current sprint is {risk_assessment.risk_level} risk with {risk_assessment.completion_probability:.0%} completion probability."
        
        return {
            "query": query,
            "response": response_text,
            "data": risk_assessment.__dict__
        }
    
    elif "team" in query_lower and "productivity" in query_lower:
        team_id = "default_team"
        insights = await productivity_engine.generate_productivity_insights(team_id)
        
        if insights:
            latest_insight = insights[-1]
            response_text = f"Team productivity: {latest_insight.insight_text}"
        else:
            response_text = "No recent productivity insights available."
        
        return {
            "query": query,
            "response": response_text,
            "data": [i.__dict__ for i in insights]
        }
    
    else:
        return {
            "query": query,
            "response": "I didn't understand that query. Try asking about sprint health or team productivity.",
            "data": None
        }


# Demo Data Generation Endpoint
@analytics_app.post("/api/demo/generate-data")
async def generate_demo_data(background_tasks: BackgroundTasks):
    """Generate realistic demo data for hackathon demonstration."""
    
    async def generate_data():
        """Background task to generate demo data."""
        try:
            # Generate mock hook executions
            registry_manager = await get_hook_registry_manager()
            if registry_manager:
                # This would generate realistic demo scenarios
                logger.info("Demo data generation started")
                
                # Simulate various team scenarios
                teams = ["frontend-team", "backend-team", "devops-team"]
                
                for team_id in teams:
                    # Generate productivity metrics
                    await productivity_engine.record_metric({
                        "team_id": team_id,
                        "metric_type": "sprint_velocity",
                        "value": 25 + (hash(team_id) % 10),
                        "timestamp": datetime.now(timezone.utc)
                    })
                
                logger.info("Demo data generation completed")
        except Exception as e:
            logger.error(f"Demo data generation failed: {e}")
    
    background_tasks.add_task(generate_data)
    
    return {"message": "Demo data generation started in background"}


if __name__ == "__main__":
    uvicorn.run(
        "devsync_ai.analytics.dashboard_api:analytics_app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )