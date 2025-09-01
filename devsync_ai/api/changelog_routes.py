"""
Changelog API Routes

Provides REST API endpoints for changelog generation, management,
and analytics while following existing API patterns.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from devsync_ai.api.routes import verify_api_key


logger = logging.getLogger(__name__)

# Create router for changelog endpoints
router = APIRouter()


# Pydantic models for request/response validation
class ChangelogGenerationRequest(BaseModel):
    """Request model for manual changelog generation."""
    team_id: str = Field(..., description="Team identifier")
    week_start_date: Optional[str] = Field(None, description="Week start date (ISO format)")
    week_end_date: Optional[str] = Field(None, description="Week end date (ISO format)")
    include_github: bool = Field(True, description="Include GitHub data")
    include_jira: bool = Field(True, description="Include JIRA data")
    include_team_metrics: bool = Field(True, description="Include team metrics")
    template_style: str = Field("professional", description="Template style")
    audience_type: str = Field("technical", description="Target audience")
    distribution_channels: Optional[List[str]] = Field(None, description="Distribution channels")


class ChangelogExportRequest(BaseModel):
    """Request model for changelog export."""
    team_id: Optional[str] = Field(None, description="Team identifier (optional)")
    start_date: Optional[str] = Field(None, description="Start date for export")
    end_date: Optional[str] = Field(None, description="End date for export")
    format: str = Field("json", description="Export format (json, csv, pdf)")
    include_analytics: bool = Field(False, description="Include analytics data")


class ChangelogConfigurationUpdate(BaseModel):
    """Request model for configuration updates."""
    team_id: str = Field(..., description="Team identifier")
    configuration: Dict[str, Any] = Field(..., description="Configuration updates")


# ========================================
# CHANGELOG GENERATION ENDPOINTS
# ========================================

@router.post("/generate")
async def generate_changelog(
    request: ChangelogGenerationRequest,
    authenticated: bool = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Manually trigger changelog generation for a team."""
    try:
        from devsync_ai.core.intelligent_data_aggregator import IntelligentDataAggregator
        from devsync_ai.formatters.intelligent_changelog_formatter import IntelligentChangelogFormatter
        from devsync_ai.core.intelligent_distributor import IntelligentDistributor
        from devsync_ai.database.changelog_migration_runner import ChangelogMigrationRunner
        
        # Parse dates if provided
        week_start = None
        week_end = None
        
        if request.week_start_date:
            week_start = datetime.fromisoformat(request.week_start_date)
        if request.week_end_date:
            week_end = datetime.fromisoformat(request.week_end_date)
        
        # Default to previous week if not specified
        if not week_start or not week_end:
            now = datetime.now()
            week_start = now - timedelta(days=now.weekday() + 7)  # Previous Monday
            week_end = week_start + timedelta(days=6)  # Previous Sunday
        
        # Create generation job record
        migration_runner = ChangelogMigrationRunner()
        
        # Aggregate data
        aggregator = IntelligentDataAggregator()
        aggregated_data = await aggregator.aggregate_weekly_data(
            team_id=request.team_id,
            week_start=week_start,
            week_end=week_end,
            include_github=request.include_github,
            include_jira=request.include_jira,
            include_team_metrics=request.include_team_metrics
        )
        
        # Format changelog
        formatter = IntelligentChangelogFormatter()
        formatted_changelog = await formatter.format_changelog(
            data=aggregated_data,
            team_id=request.team_id,
            template_style=request.template_style,
            audience_type=request.audience_type
        )
        
        # Distribute if channels specified
        distribution_result = None
        if request.distribution_channels:
            distributor = IntelligentDistributor()
            distribution_config = {
                "channels": request.distribution_channels,
                "team_id": request.team_id,
                "interactive_elements": True,
                "feedback_collection": True
            }
            
            distribution_result = await distributor.distribute_changelog(
                formatted_changelog, distribution_config
            )
        
        return {
            "success": True,
            "team_id": request.team_id,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "changelog": formatted_changelog,
            "distribution_result": distribution_result,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Changelog generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Changelog generation failed: {str(e)}")


@router.get("/status/{team_id}")
async def get_changelog_status(
    team_id: str,
    authenticated: bool = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Get changelog generation status for a team."""
    try:
        from devsync_ai.database.connection import get_database
        
        db = await get_database()
        
        # Get recent generation jobs
        recent_jobs = await db.execute_raw("""
            SELECT id, status, week_start_date, week_end_date, 
                   started_at, completed_at, execution_time_ms, error_details
            FROM changelog_generation_jobs 
            WHERE team_id = %s 
            ORDER BY created_at DESC 
            LIMIT 10
        """, (team_id,))
        
        jobs = []
        for job in recent_jobs:
            jobs.append({
                "id": str(job[0]),
                "status": job[1],
                "week_start": job[2].isoformat() if job[2] else None,
                "week_end": job[3].isoformat() if job[3] else None,
                "started_at": job[4].isoformat() if job[4] else None,
                "completed_at": job[5].isoformat() if job[5] else None,
                "execution_time_ms": job[6],
                "error_details": job[7]
            })
        
        # Get configuration status
        from devsync_ai.core.changelog_configuration_manager import ChangelogConfigurationManager
        config_manager = ChangelogConfigurationManager()
        team_config = await config_manager.get_team_configuration(team_id)
        
        return {
            "team_id": team_id,
            "configuration": {
                "enabled": team_config.enabled,
                "schedule_day": team_config.schedule.day,
                "schedule_time": team_config.schedule.time,
                "timezone": team_config.schedule.timezone,
                "primary_channel": team_config.distribution.primary_channel
            },
            "recent_jobs": jobs,
            "checked_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get changelog status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


# ========================================
# CHANGELOG HISTORY ENDPOINTS
# ========================================

@router.get("/history")
async def get_changelog_history(
    team_id: Optional[str] = Query(None, description="Team ID filter"),
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
    limit: int = Query(50, description="Maximum number of entries"),
    offset: int = Query(0, description="Offset for pagination"),
    authenticated: bool = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Get changelog history with filtering and pagination."""
    try:
        from devsync_ai.database.connection import get_database
        
        db = await get_database()
        
        # Build query with filters
        where_conditions = ["status != 'deleted'"]
        params = []
        
        if team_id:
            where_conditions.append("team_id = %s")
            params.append(team_id)
        
        if start_date:
            where_conditions.append("week_start_date >= %s")
            params.append(datetime.fromisoformat(start_date).date())
        
        if end_date:
            where_conditions.append("week_end_date <= %s")
            params.append(datetime.fromisoformat(end_date).date())
        
        where_clause = " AND ".join(where_conditions)
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM changelog_entries WHERE {where_clause}"
        count_result = await db.execute_raw(count_query, params)
        total_count = count_result[0][0] if count_result else 0
        
        # Get entries
        query = f"""
            SELECT id, team_id, week_start_date, week_end_date, version, status,
                   generated_at, published_at, created_by, tags
            FROM changelog_entries 
            WHERE {where_clause}
            ORDER BY week_start_date DESC, generated_at DESC
            LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        entries = await db.execute_raw(query, params)
        
        changelog_entries = []
        for entry in entries:
            changelog_entries.append({
                "id": str(entry[0]),
                "team_id": entry[1],
                "week_start_date": entry[2].isoformat() if entry[2] else None,
                "week_end_date": entry[3].isoformat() if entry[3] else None,
                "version": entry[4],
                "status": entry[5],
                "generated_at": entry[6].isoformat() if entry[6] else None,
                "published_at": entry[7].isoformat() if entry[7] else None,
                "created_by": entry[8],
                "tags": entry[9] or []
            })
        
        return {
            "total_count": total_count,
            "entries": changelog_entries,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(changelog_entries) < total_count
            },
            "filters": {
                "team_id": team_id,
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get changelog history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.get("/entry/{entry_id}")
async def get_changelog_entry(
    entry_id: str,
    authenticated: bool = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Get a specific changelog entry with full content."""
    try:
        from devsync_ai.database.connection import get_database
        
        db = await get_database()
        
        # Get changelog entry
        entry_result = await db.execute_raw("""
            SELECT id, team_id, week_start_date, week_end_date, version, status,
                   content, metadata, generated_at, published_at, created_by, tags
            FROM changelog_entries 
            WHERE id = %s
        """, (entry_id,))
        
        if not entry_result:
            raise HTTPException(status_code=404, detail="Changelog entry not found")
        
        entry = entry_result[0]
        
        # Get distribution information
        distributions = await db.execute_raw("""
            SELECT channel_type, channel_identifier, distribution_status, 
                   delivered_at, engagement_metrics
            FROM changelog_distributions 
            WHERE changelog_id = %s
        """, (entry_id,))
        
        distribution_info = []
        for dist in distributions:
            distribution_info.append({
                "channel_type": dist[0],
                "channel_identifier": dist[1],
                "status": dist[2],
                "delivered_at": dist[3].isoformat() if dist[3] else None,
                "engagement_metrics": dist[4] or {}
            })
        
        return {
            "id": str(entry[0]),
            "team_id": entry[1],
            "week_start_date": entry[2].isoformat() if entry[2] else None,
            "week_end_date": entry[3].isoformat() if entry[3] else None,
            "version": entry[4],
            "status": entry[5],
            "content": entry[6],
            "metadata": entry[7] or {},
            "generated_at": entry[8].isoformat() if entry[8] else None,
            "published_at": entry[9].isoformat() if entry[9] else None,
            "created_by": entry[10],
            "tags": entry[11] or [],
            "distributions": distribution_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get changelog entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get entry: {str(e)}")


# ========================================
# ANALYTICS ENDPOINTS
# ========================================

@router.get("/analytics")
async def get_changelog_analytics(
    team_id: Optional[str] = Query(None, description="Team ID filter"),
    days: int = Query(30, description="Number of days to analyze"),
    authenticated: bool = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Get changelog analytics and metrics."""
    try:
        from devsync_ai.database.connection import get_database
        
        db = await get_database()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Build team filter
        team_filter = ""
        params = [start_date, end_date]
        
        if team_id:
            team_filter = "AND team_id = %s"
            params.append(team_id)
        
        # Get generation statistics
        generation_stats = await db.execute_raw(f"""
            SELECT 
                COUNT(*) as total_generated,
                COUNT(*) FILTER (WHERE status = 'published') as published_count,
                AVG(EXTRACT(EPOCH FROM (completed_at - started_at))/60) as avg_generation_time_minutes,
                COUNT(DISTINCT team_id) as active_teams
            FROM changelog_generation_jobs 
            WHERE created_at >= %s AND created_at <= %s {team_filter}
        """, params)
        
        stats = generation_stats[0] if generation_stats else (0, 0, 0, 0)
        
        # Get distribution statistics
        distribution_stats = await db.execute_raw(f"""
            SELECT 
                cd.channel_type,
                COUNT(*) as total_distributions,
                COUNT(*) FILTER (WHERE cd.distribution_status = 'delivered') as successful_distributions,
                AVG(COALESCE((cd.engagement_metrics->>'views')::int, 0)) as avg_views
            FROM changelog_distributions cd
            JOIN changelog_entries ce ON cd.changelog_id = ce.id
            WHERE ce.generated_at >= %s AND ce.generated_at <= %s {team_filter}
            GROUP BY cd.channel_type
        """, params)
        
        distribution_breakdown = {}
        for dist_stat in distribution_stats:
            distribution_breakdown[dist_stat[0]] = {
                "total_distributions": dist_stat[1],
                "successful_distributions": dist_stat[2],
                "success_rate": dist_stat[2] / dist_stat[1] if dist_stat[1] > 0 else 0,
                "avg_views": float(dist_stat[3]) if dist_stat[3] else 0
            }
        
        # Get team-specific metrics if team_id provided
        team_metrics = None
        if team_id:
            team_stats = await db.execute_raw("""
                SELECT 
                    DATE_TRUNC('week', generated_at) as week,
                    COUNT(*) as changelogs_generated,
                    AVG(version) as avg_version
                FROM changelog_entries 
                WHERE team_id = %s AND generated_at >= %s AND generated_at <= %s
                GROUP BY DATE_TRUNC('week', generated_at)
                ORDER BY week DESC
            """, [team_id, start_date, end_date])
            
            team_metrics = []
            for week_stat in team_stats:
                team_metrics.append({
                    "week": week_stat[0].isoformat(),
                    "changelogs_generated": week_stat[1],
                    "avg_version": float(week_stat[2]) if week_stat[2] else 1.0
                })
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "generation_statistics": {
                "total_generated": stats[0],
                "published_count": stats[1],
                "avg_generation_time_minutes": float(stats[2]) if stats[2] else 0,
                "active_teams": stats[3]
            },
            "distribution_statistics": distribution_breakdown,
            "team_metrics": team_metrics,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


# ========================================
# CONFIGURATION ENDPOINTS
# ========================================

@router.get("/config/{team_id}")
async def get_team_configuration(
    team_id: str,
    authenticated: bool = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Get changelog configuration for a team."""
    try:
        from devsync_ai.core.changelog_configuration_manager import ChangelogConfigurationManager
        
        config_manager = ChangelogConfigurationManager()
        team_config = await config_manager.get_team_configuration(team_id)
        
        return {
            "team_id": team_config.team_id,
            "enabled": team_config.enabled,
            "schedule": {
                "day": team_config.schedule.day,
                "time": team_config.schedule.time,
                "timezone": team_config.schedule.timezone,
                "enabled": team_config.schedule.enabled
            },
            "data_sources": {
                "github_enabled": team_config.data_sources.github_enabled,
                "jira_enabled": team_config.data_sources.jira_enabled,
                "team_metrics_enabled": team_config.data_sources.team_metrics_enabled
            },
            "content": {
                "template_style": team_config.content.template_style,
                "audience_type": team_config.content.audience_type,
                "include_metrics": team_config.content.include_metrics,
                "include_contributor_recognition": team_config.content.include_contributor_recognition,
                "include_risk_analysis": team_config.content.include_risk_analysis
            },
            "distribution": {
                "primary_channel": team_config.distribution.primary_channel,
                "secondary_channels": team_config.distribution.secondary_channels,
                "channel_specific_formatting": team_config.distribution.channel_specific_formatting
            },
            "notifications": team_config.notifications,
            "interactive": team_config.interactive
        }
        
    except Exception as e:
        logger.error(f"Failed to get team configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")


@router.put("/config/{team_id}")
async def update_team_configuration(
    team_id: str,
    updates: Dict[str, Any] = Body(...),
    authenticated: bool = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Update changelog configuration for a team."""
    try:
        from devsync_ai.core.changelog_configuration_manager import ChangelogConfigurationManager
        
        config_manager = ChangelogConfigurationManager()
        
        # Validate the team exists or can be created
        validation_errors = await config_manager.validate_team_configuration(team_id)
        
        # Update configuration
        success = await config_manager.update_team_configuration(team_id, updates)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update configuration")
        
        # Return updated configuration
        updated_config = await config_manager.get_team_configuration(team_id)
        
        return {
            "success": True,
            "team_id": team_id,
            "updated_at": datetime.now().isoformat(),
            "configuration": {
                "enabled": updated_config.enabled,
                "schedule": {
                    "day": updated_config.schedule.day,
                    "time": updated_config.schedule.time,
                    "timezone": updated_config.schedule.timezone
                },
                "distribution": {
                    "primary_channel": updated_config.distribution.primary_channel,
                    "secondary_channels": updated_config.distribution.secondary_channels
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update team configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


# ========================================
# EXPORT ENDPOINTS
# ========================================

@router.post("/export")
async def export_changelog_data(
    request: ChangelogExportRequest,
    authenticated: bool = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Export changelog data in various formats."""
    try:
        from devsync_ai.database.connection import get_database
        
        db = await get_database()
        
        # Build query filters
        where_conditions = ["status != 'deleted'"]
        params = []
        
        if request.team_id:
            where_conditions.append("team_id = %s")
            params.append(request.team_id)
        
        if request.start_date:
            where_conditions.append("week_start_date >= %s")
            params.append(datetime.fromisoformat(request.start_date).date())
        
        if request.end_date:
            where_conditions.append("week_end_date <= %s")
            params.append(datetime.fromisoformat(request.end_date).date())
        
        where_clause = " AND ".join(where_conditions)
        
        # Get changelog entries
        query = f"""
            SELECT id, team_id, week_start_date, week_end_date, version, status,
                   content, metadata, generated_at, published_at, created_by, tags
            FROM changelog_entries 
            WHERE {where_clause}
            ORDER BY week_start_date DESC, generated_at DESC
        """
        
        entries = await db.execute_raw(query, params)
        
        # Format data based on requested format
        if request.format == "json":
            export_data = []
            for entry in entries:
                export_data.append({
                    "id": str(entry[0]),
                    "team_id": entry[1],
                    "week_start_date": entry[2].isoformat() if entry[2] else None,
                    "week_end_date": entry[3].isoformat() if entry[3] else None,
                    "version": entry[4],
                    "status": entry[5],
                    "content": entry[6],
                    "metadata": entry[7] or {},
                    "generated_at": entry[8].isoformat() if entry[8] else None,
                    "published_at": entry[9].isoformat() if entry[9] else None,
                    "created_by": entry[10],
                    "tags": entry[11] or []
                })
            
            return {
                "format": "json",
                "data": export_data,
                "total_entries": len(export_data),
                "exported_at": datetime.now().isoformat()
            }
        
        else:
            # For other formats, return a placeholder response
            # In a real implementation, you would generate CSV, PDF, etc.
            return {
                "format": request.format,
                "message": f"Export in {request.format} format is not yet implemented",
                "total_entries": len(entries),
                "exported_at": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# ========================================
# HEALTH CHECK ENDPOINTS
# ========================================

@router.get("/health")
async def changelog_health_check(
    authenticated: bool = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Get health status of changelog service components."""
    try:
        from devsync_ai.database.changelog_migration_runner import ChangelogMigrationRunner
        
        # Check database schema
        migration_runner = ChangelogMigrationRunner()
        migration_status = await migration_runner.get_migration_status()
        
        # Check service components
        components = {
            "database": "healthy" if migration_status.get("schema_status", {}).get("overall_status") == "success" else "unhealthy",
            "configuration": "healthy",  # Could add actual config validation
            "api": "healthy"  # If we're responding, API is healthy
        }
        
        overall_status = "healthy" if all(status == "healthy" for status in components.values()) else "degraded"
        
        return {
            "status": overall_status,
            "components": components,
            "migration_status": migration_status,
            "checked_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "checked_at": datetime.now().isoformat()
        }