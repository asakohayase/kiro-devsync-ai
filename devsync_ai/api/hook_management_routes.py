"""
Hook Management API Routes.

This module provides comprehensive REST API endpoints for hook management,
including configuration, status monitoring, health checks, execution history,
and analytics for JIRA Agent Hooks.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from devsync_ai.core.hook_configuration_manager import (
    HookConfigurationManager,
    TeamConfiguration,
    HookSettings,
    ValidationResult,
    ConfigurationUpdateResult
)
from devsync_ai.analytics.hook_analytics_engine import (
    HookAnalyticsEngine,
    HookPerformanceMetrics,
    SystemHealthMetrics,
    Alert,
    AlertSeverity,
    HealthStatus
)
from devsync_ai.database.hook_data_manager import HookDataManager
from devsync_ai.hooks.hook_registry_manager import get_hook_registry_manager
from devsync_ai.core.exceptions import ConfigurationError, ValidationError


logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1/hooks", tags=["Hook Management"])

# Global instances
_config_manager: Optional[HookConfigurationManager] = None
_analytics_engine: Optional[HookAnalyticsEngine] = None
_data_manager: Optional[HookDataManager] = None


def get_config_manager() -> HookConfigurationManager:
    """Get or create configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = HookConfigurationManager()
    return _config_manager


def get_analytics_engine() -> HookAnalyticsEngine:
    """Get or create analytics engine instance."""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = HookAnalyticsEngine()
    return _analytics_engine


def get_data_manager() -> HookDataManager:
    """Get or create data manager instance."""
    global _data_manager
    if _data_manager is None:
        _data_manager = HookDataManager()
    return _data_manager


# Pydantic models for API responses
class HookStatusResponse(BaseModel):
    """Response model for hook status."""
    hook_id: str
    hook_type: str
    team_id: str
    status: str
    enabled: bool
    last_execution: Optional[datetime] = None
    total_executions: int = 0
    success_rate: float = 0.0
    average_execution_time_ms: float = 0.0
    health_status: str = "unknown"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SystemHealthResponse(BaseModel):
    """Response model for system health."""
    timestamp: datetime
    overall_status: str
    total_hooks: int
    active_hooks: int
    total_executions: int
    overall_success_rate: float
    average_execution_time_ms: float
    executions_per_minute: float
    error_count_last_hour: int
    alerts_count: int
    details: Dict[str, Any] = Field(default_factory=dict)


class HookExecutionResponse(BaseModel):
    """Response model for hook execution."""
    execution_id: str
    hook_id: str
    hook_type: str
    team_id: str
    event_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[float] = None
    notification_sent: bool = False
    success: bool = False
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertResponse(BaseModel):
    """Response model for alerts."""
    alert_id: str
    rule_id: str
    hook_id: Optional[str] = None
    team_id: Optional[str] = None
    severity: str
    title: str
    description: str
    metric_value: float
    threshold_value: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PerformanceReportResponse(BaseModel):
    """Response model for performance reports."""
    report_generated_at: datetime
    time_range: Dict[str, str]
    filters: Dict[str, Any]
    summary: Dict[str, Any]
    hook_metrics: List[Dict[str, Any]]
    performance_trends: List[Dict[str, Any]]
    top_performers: List[Dict[str, Any]]
    underperformers: List[Dict[str, Any]]
    alerts_summary: Dict[str, Any]


# Hook Status and Health Endpoints

@router.get("/status", response_model=List[HookStatusResponse])
async def get_all_hook_statuses(
    team_filter: Optional[str] = Query(None, description="Filter by team ID"),
    hook_type_filter: Optional[str] = Query(None, description="Filter by hook type"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    analytics_engine: HookAnalyticsEngine = Depends(get_analytics_engine)
):
    """
    Get status of all hooks with optional filtering.
    
    Args:
        team_filter: Filter by team ID
        hook_type_filter: Filter by hook type
        status_filter: Filter by status
        
    Returns:
        List of hook statuses
    """
    try:
        registry_manager = await get_hook_registry_manager()
        if not registry_manager:
            raise HTTPException(status_code=503, detail="Hook registry not available")
        
        # Get all hook statuses from registry
        hook_statuses = await registry_manager.get_all_hook_statuses()
        
        # Apply filters
        filtered_statuses = []
        for status in hook_statuses:
            if team_filter and status.get('team_id') != team_filter:
                continue
            if hook_type_filter and status.get('hook_type') != hook_type_filter:
                continue
            if status_filter and status.get('status') != status_filter:
                continue
            
            # Get performance metrics for each hook
            hook_id = status.get('hook_id')
            metrics = await analytics_engine.get_hook_performance_metrics(hook_id)
            
            hook_response = HookStatusResponse(
                hook_id=hook_id,
                hook_type=status.get('hook_type', 'unknown'),
                team_id=status.get('team_id', 'unknown'),
                status=status.get('status', 'unknown'),
                enabled=status.get('enabled', False),
                last_execution=status.get('last_execution'),
                total_executions=metrics.total_executions if metrics else 0,
                success_rate=metrics.success_rate if metrics else 0.0,
                average_execution_time_ms=metrics.average_execution_time_ms if metrics else 0.0,
                health_status=metrics.health_status.value if metrics else "unknown",
                metadata=status.get('metadata', {})
            )
            filtered_statuses.append(hook_response)
        
        return filtered_statuses
        
    except Exception as e:
        logger.error(f"Failed to get hook statuses: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve hook statuses")


@router.get("/status/{hook_id}", response_model=HookStatusResponse)
async def get_hook_status(
    hook_id: str = Path(..., description="Hook identifier"),
    analytics_engine: HookAnalyticsEngine = Depends(get_analytics_engine)
):
    """
    Get status of a specific hook.
    
    Args:
        hook_id: Hook identifier
        
    Returns:
        Hook status
    """
    try:
        registry_manager = await get_hook_registry_manager()
        if not registry_manager:
            raise HTTPException(status_code=503, detail="Hook registry not available")
        
        # Get hook status from registry
        status = await registry_manager.get_hook_status(hook_id)
        if not status:
            raise HTTPException(status_code=404, detail="Hook not found")
        
        # Get performance metrics
        metrics = await analytics_engine.get_hook_performance_metrics(hook_id)
        
        return HookStatusResponse(
            hook_id=hook_id,
            hook_type=status.get('hook_type', 'unknown'),
            team_id=status.get('team_id', 'unknown'),
            status=status.get('status', 'unknown'),
            enabled=status.get('enabled', False),
            last_execution=status.get('last_execution'),
            total_executions=metrics.total_executions if metrics else 0,
            success_rate=metrics.success_rate if metrics else 0.0,
            average_execution_time_ms=metrics.average_execution_time_ms if metrics else 0.0,
            health_status=metrics.health_status.value if metrics else "unknown",
            metadata=status.get('metadata', {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get hook status for {hook_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve hook status")


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    analytics_engine: HookAnalyticsEngine = Depends(get_analytics_engine)
):
    """
    Get overall system health status.
    
    Returns:
        System health metrics
    """
    try:
        health_metrics = await analytics_engine.get_system_health_metrics()
        
        return SystemHealthResponse(
            timestamp=health_metrics.timestamp,
            overall_status=health_metrics.health_status.value,
            total_hooks=health_metrics.total_hooks,
            active_hooks=health_metrics.active_hooks,
            total_executions=health_metrics.total_executions,
            overall_success_rate=health_metrics.overall_success_rate,
            average_execution_time_ms=health_metrics.average_execution_time_ms,
            executions_per_minute=health_metrics.executions_per_minute,
            error_count_last_hour=health_metrics.error_count_last_hour,
            alerts_count=health_metrics.alerts_count,
            details={
                "inactive_hooks": health_metrics.total_hooks - health_metrics.active_hooks,
                "error_rate": 1.0 - health_metrics.overall_success_rate,
                "health_score": _calculate_health_score(health_metrics)
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system health")


# Hook Execution History Endpoints

@router.get("/executions", response_model=List[HookExecutionResponse])
async def get_hook_executions(
    hook_id: Optional[str] = Query(None, description="Filter by hook ID"),
    team_id: Optional[str] = Query(None, description="Filter by team ID"),
    status: Optional[str] = Query(None, description="Filter by execution status"),
    start_time: Optional[datetime] = Query(None, description="Start time for filtering"),
    end_time: Optional[datetime] = Query(None, description="End time for filtering"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    data_manager: HookDataManager = Depends(get_data_manager)
):
    """
    Get hook execution history with filtering and pagination.
    
    Args:
        hook_id: Filter by hook ID
        team_id: Filter by team ID
        status: Filter by execution status
        start_time: Start time for filtering
        end_time: End time for filtering
        limit: Maximum number of results
        offset: Offset for pagination
        
    Returns:
        List of hook executions
    """
    try:
        # Set default time range if not provided
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = end_time - timedelta(days=7)
        
        # Get executions from database
        executions = await data_manager.get_hook_executions(
            hook_id=hook_id,
            team_id=team_id,
            status=status,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )
        
        # Convert to response models
        execution_responses = []
        for execution in executions:
            execution_response = HookExecutionResponse(
                execution_id=execution['execution_id'],
                hook_id=execution['hook_id'],
                hook_type=execution['hook_type'],
                team_id=execution['team_id'],
                event_type=execution['event_type'],
                status=execution['status'],
                started_at=execution['started_at'],
                completed_at=execution.get('completed_at'),
                execution_time_ms=execution.get('execution_time_ms'),
                notification_sent=execution.get('notification_sent', False),
                success=execution.get('success', False),
                errors=execution.get('errors', []),
                metadata=execution.get('metadata', {})
            )
            execution_responses.append(execution_response)
        
        return execution_responses
        
    except Exception as e:
        logger.error(f"Failed to get hook executions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve hook executions")


@router.get("/executions/{execution_id}", response_model=HookExecutionResponse)
async def get_hook_execution(
    execution_id: str = Path(..., description="Execution identifier"),
    data_manager: HookDataManager = Depends(get_data_manager)
):
    """
    Get details of a specific hook execution.
    
    Args:
        execution_id: Execution identifier
        
    Returns:
        Hook execution details
    """
    try:
        execution = await data_manager.get_hook_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return HookExecutionResponse(
            execution_id=execution['execution_id'],
            hook_id=execution['hook_id'],
            hook_type=execution['hook_type'],
            team_id=execution['team_id'],
            event_type=execution['event_type'],
            status=execution['status'],
            started_at=execution['started_at'],
            completed_at=execution.get('completed_at'),
            execution_time_ms=execution.get('execution_time_ms'),
            notification_sent=execution.get('notification_sent', False),
            success=execution.get('success', False),
            errors=execution.get('errors', []),
            metadata=execution.get('metadata', {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get hook execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve hook execution")


# Analytics and Performance Endpoints

@router.get("/analytics/performance", response_model=PerformanceReportResponse)
async def get_performance_report(
    start_time: Optional[datetime] = Query(None, description="Start time for report"),
    end_time: Optional[datetime] = Query(None, description="End time for report"),
    team_filter: Optional[str] = Query(None, description="Filter by team ID"),
    hook_type_filter: Optional[str] = Query(None, description="Filter by hook type"),
    analytics_engine: HookAnalyticsEngine = Depends(get_analytics_engine)
):
    """
    Generate comprehensive performance report.
    
    Args:
        start_time: Start time for report
        end_time: End time for report
        team_filter: Filter by team ID
        hook_type_filter: Filter by hook type
        
    Returns:
        Performance report
    """
    try:
        # Set default time range if not provided
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = end_time - timedelta(days=7)
        
        time_range = (start_time, end_time)
        
        # Generate performance report
        report_data = await analytics_engine.generate_performance_report(
            time_range=time_range,
            team_filter=team_filter,
            hook_type_filter=hook_type_filter
        )
        
        if "error" in report_data:
            raise HTTPException(status_code=400, detail=report_data["error"])
        
        return PerformanceReportResponse(**report_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate performance report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate performance report")


@router.get("/analytics/metrics/{hook_id}")
async def get_hook_metrics(
    hook_id: str = Path(..., description="Hook identifier"),
    start_time: Optional[datetime] = Query(None, description="Start time for metrics"),
    end_time: Optional[datetime] = Query(None, description="End time for metrics"),
    analytics_engine: HookAnalyticsEngine = Depends(get_analytics_engine)
):
    """
    Get detailed performance metrics for a specific hook.
    
    Args:
        hook_id: Hook identifier
        start_time: Start time for metrics
        end_time: End time for metrics
        
    Returns:
        Hook performance metrics
    """
    try:
        # Set default time range if not provided
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = end_time - timedelta(days=1)
        
        time_range = (start_time, end_time)
        
        # Get performance metrics
        metrics = await analytics_engine.get_hook_performance_metrics(hook_id, time_range)
        if not metrics:
            raise HTTPException(status_code=404, detail="Hook metrics not found")
        
        return {
            "hook_id": metrics.hook_id,
            "hook_type": metrics.hook_type,
            "team_id": metrics.team_id,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "metrics": {
                "total_executions": metrics.total_executions,
                "successful_executions": metrics.successful_executions,
                "failed_executions": metrics.failed_executions,
                "success_rate": metrics.success_rate,
                "error_rate": metrics.error_rate,
                "average_execution_time_ms": metrics.average_execution_time_ms,
                "min_execution_time_ms": metrics.min_execution_time_ms,
                "max_execution_time_ms": metrics.max_execution_time_ms,
                "executions_per_hour": metrics.executions_per_hour,
                "last_execution": metrics.last_execution.isoformat() if metrics.last_execution else None,
                "health_status": metrics.health_status.value
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get hook metrics for {hook_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve hook metrics")


# Alert Management Endpoints

@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    team_filter: Optional[str] = Query(None, description="Filter by team ID"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    analytics_engine: HookAnalyticsEngine = Depends(get_analytics_engine)
):
    """
    Get alerts with optional filtering.
    
    Args:
        severity: Filter by alert severity
        team_filter: Filter by team ID
        resolved: Filter by resolution status
        
    Returns:
        List of alerts
    """
    try:
        # Convert severity string to enum if provided
        severity_filter = None
        if severity:
            try:
                severity_filter = AlertSeverity(severity.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        # Get alerts from analytics engine
        alerts = await analytics_engine.get_active_alerts(
            severity_filter=severity_filter,
            team_filter=team_filter
        )
        
        # Apply resolved filter if specified
        if resolved is not None:
            if resolved:
                alerts = [a for a in alerts if a.resolved_at is not None]
            else:
                alerts = [a for a in alerts if a.resolved_at is None]
        
        # Convert to response models
        alert_responses = []
        for alert in alerts:
            alert_response = AlertResponse(
                alert_id=alert.alert_id,
                rule_id=alert.rule_id,
                hook_id=alert.hook_id,
                team_id=alert.team_id,
                severity=alert.severity.value,
                title=alert.title,
                description=alert.description,
                metric_value=alert.metric_value,
                threshold_value=alert.threshold_value,
                triggered_at=alert.triggered_at,
                resolved_at=alert.resolved_at,
                acknowledged=alert.acknowledged,
                metadata=alert.metadata
            )
            alert_responses.append(alert_response)
        
        return alert_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str = Path(..., description="Alert identifier"),
    analytics_engine: HookAnalyticsEngine = Depends(get_analytics_engine)
):
    """
    Acknowledge an alert.
    
    Args:
        alert_id: Alert identifier
        
    Returns:
        Success status
    """
    try:
        success = await analytics_engine.acknowledge_alert(alert_id)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {"success": True, "message": f"Alert {alert_id} acknowledged"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str = Path(..., description="Alert identifier"),
    analytics_engine: HookAnalyticsEngine = Depends(get_analytics_engine)
):
    """
    Resolve an alert.
    
    Args:
        alert_id: Alert identifier
        
    Returns:
        Success status
    """
    try:
        success = await analytics_engine.resolve_alert(alert_id)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {"success": True, "message": f"Alert {alert_id} resolved"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve alert")


# Configuration Management Endpoints (delegated to existing hook_configuration_routes)

@router.get("/config/teams", response_model=List[str])
async def list_teams(
    config_manager: HookConfigurationManager = Depends(get_config_manager)
):
    """
    Get list of all configured teams.
    
    Returns:
        List of team IDs
    """
    try:
        configurations = await config_manager.get_all_team_configurations()
        return [config.team_id for config in configurations]
    except Exception as e:
        logger.error(f"Failed to list teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve team list")


@router.get("/config/teams/{team_id}")
async def get_team_configuration(
    team_id: str = Path(..., description="Team identifier"),
    config_manager: HookConfigurationManager = Depends(get_config_manager)
):
    """
    Get configuration for a specific team.
    
    Args:
        team_id: Team identifier
        
    Returns:
        Team configuration
    """
    try:
        config = await config_manager.load_team_configuration(team_id)
        
        return {
            "team_id": config.team_id,
            "team_name": config.team_name,
            "enabled": config.enabled,
            "version": config.version,
            "default_channels": config.default_channels,
            "notification_preferences": config.notification_preferences,
            "business_hours": config.business_hours,
            "escalation_rules": config.escalation_rules,
            "rules": config.rules,
            "last_updated": config.last_updated.isoformat(),
            "metadata": config.metadata
        }
    except ConfigurationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get team configuration for {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve team configuration")


# Utility Endpoints

@router.get("/stats")
async def get_hook_statistics(
    analytics_engine: HookAnalyticsEngine = Depends(get_analytics_engine),
    config_manager: HookConfigurationManager = Depends(get_config_manager)
):
    """
    Get comprehensive hook system statistics.
    
    Returns:
        Hook system statistics
    """
    try:
        # Get system health metrics
        health_metrics = await analytics_engine.get_system_health_metrics()
        
        # Get configuration statistics
        configurations = await config_manager.get_all_team_configurations()
        
        total_teams = len(configurations)
        enabled_teams = len([c for c in configurations if c.enabled])
        total_rules = sum(len(c.rules) for c in configurations)
        enabled_rules = sum(len([r for r in c.rules if r.get('enabled', True)]) for c in configurations)
        
        # Count hook types
        hook_type_counts = {}
        for config in configurations:
            for rule in config.rules:
                if rule.get('enabled', True):
                    for hook_type in rule.get('hook_types', []):
                        hook_type_counts[hook_type] = hook_type_counts.get(hook_type, 0) + 1
        
        return {
            "system_health": {
                "overall_status": health_metrics.health_status.value,
                "total_hooks": health_metrics.total_hooks,
                "active_hooks": health_metrics.active_hooks,
                "total_executions": health_metrics.total_executions,
                "overall_success_rate": health_metrics.overall_success_rate,
                "alerts_count": health_metrics.alerts_count
            },
            "configuration": {
                "total_teams": total_teams,
                "enabled_teams": enabled_teams,
                "disabled_teams": total_teams - enabled_teams,
                "total_rules": total_rules,
                "enabled_rules": enabled_rules,
                "disabled_rules": total_rules - enabled_rules,
                "avg_rules_per_team": total_rules / total_teams if total_teams > 0 else 0,
                "hook_type_distribution": hook_type_counts
            },
            "performance": {
                "average_execution_time_ms": health_metrics.average_execution_time_ms,
                "executions_per_minute": health_metrics.executions_per_minute,
                "error_count_last_hour": health_metrics.error_count_last_hour
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get hook statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve hook statistics")


# Helper functions

def _calculate_health_score(health_metrics: SystemHealthMetrics) -> float:
    """
    Calculate a health score based on system metrics.
    
    Args:
        health_metrics: System health metrics
        
    Returns:
        Health score (0.0 to 1.0)
    """
    score = 1.0
    
    # Penalize low success rate
    if health_metrics.overall_success_rate < 0.95:
        score -= (0.95 - health_metrics.overall_success_rate) * 2
    
    # Penalize high execution times
    if health_metrics.average_execution_time_ms > 2000:
        score -= min(0.3, (health_metrics.average_execution_time_ms - 2000) / 10000)
    
    # Penalize high error counts
    if health_metrics.error_count_last_hour > 10:
        score -= min(0.2, health_metrics.error_count_last_hour / 100)
    
    # Penalize active alerts
    if health_metrics.alerts_count > 0:
        score -= min(0.2, health_metrics.alerts_count / 20)
    
    return max(0.0, score)