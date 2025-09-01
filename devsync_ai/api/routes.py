"""API routes for DevSync AI."""

import os
import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional

from devsync_ai.config import settings


# Security scheme for API authentication
security = HTTPBearer(auto_error=False)

# Main API router
api_router = APIRouter()

# Import hook management routes
from devsync_ai.api.hook_management_routes import router as hook_management_router
from devsync_ai.api.hook_configuration_routes import router as hook_config_router

# Import changelog routes
from devsync_ai.api.changelog_routes import router as changelog_router

# Include hook management routes
api_router.include_router(hook_management_router)
api_router.include_router(hook_config_router)

# Include changelog routes
api_router.include_router(changelog_router, prefix="/changelog", tags=["changelog"])


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> bool:
    """Verify API key authentication."""
    if not settings.api_key:
        return True  # No API key required

    if not credentials:
        raise HTTPException(status_code=401, detail="API key required")

    if credentials.credentials != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


@api_router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@api_router.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with basic API information."""
    return {
        "message": f"Welcome to {settings.app_name} API",
        "version": settings.app_version,
        "docs": ("/docs" if settings.debug else "Documentation not available in production"),
    }


# ========================================
# GITHUB API ENDPOINTS
# ========================================


# Get GitHub pull request summaries and analysis
@api_router.get("/github/prs")
async def get_github_prs(
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, Any]:
    """Get GitHub pull request summaries."""
    try:
        from devsync_ai.services.github import GitHubService

        service = GitHubService()
        summary = await service.get_default_pr_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch GitHub PRs: {str(e)}")


# Test GitHub API authentication and credentials
@api_router.get("/github/test")
async def test_github_auth(
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, Any]:
    """Test GitHub authentication."""
    try:
        from devsync_ai.services.github import GitHubService

        service = GitHubService()
        auth_info = await service.test_authentication()
        return auth_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub authentication failed: {str(e)}")


# Generate changelog from recent commits
@api_router.get("/github/changelog")
async def generate_changelog(
    authenticated: bool = Depends(verify_api_key), days: int = 7, format: str = "json"
) -> Dict[str, Any]:
    """Generate changelog from recent commits."""
    try:
        from devsync_ai.services.github import GitHubService
        from datetime import datetime, timedelta

        service = GitHubService()
        since_date = datetime.now() - timedelta(days=days)

        changelog_data = await service.generate_changelog_data(
            service.get_default_repository(), since_date
        )

        if format.lower() == "markdown":
            markdown = await service.format_changelog_markdown(changelog_data)
            return {"format": "markdown", "content": markdown}
        else:
            return {"format": "json", "data": changelog_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate changelog: {str(e)}")


# Get recent commits with categorization and analysis
@api_router.get("/github/commits")
async def get_recent_commits(
    authenticated: bool = Depends(verify_api_key), days: int = 7
) -> Dict[str, Any]:
    """Get recent commits with analysis."""
    try:
        from devsync_ai.services.github import GitHubService
        from datetime import datetime, timedelta

        service = GitHubService()
        since_date = datetime.now() - timedelta(days=days)

        commits = await service.get_commits_since(service.get_default_repository(), since_date)

        # Convert CommitInfo objects to dictionaries
        commit_data = []
        for commit in commits:
            commit_data.append(
                {
                    "sha": commit.sha,
                    "message": commit.message,
                    "author": commit.author,
                    "date": commit.date.isoformat(),
                    "category": commit.category,
                    "description": commit.description,
                    "breaking_change": commit.breaking_change,
                    "pr_number": commit.pr_number,
                }
            )

        return {
            "repository": service.get_default_repository(),
            "period_days": days,
            "total_commits": len(commits),
            "commits": commit_data,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get commits: {str(e)}")


# ========================================
# JIRA API ENDPOINTS
# ========================================


# Get JIRA ticket summaries and status from synced database
@api_router.get("/jira/tickets")
async def get_jira_tickets(
    authenticated: bool = Depends(verify_api_key),
    project_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get JIRA ticket summaries and status."""
    try:
        from devsync_ai.services.jira import JiraService

        jira_service = JiraService()

        # Get tickets from database (synced data)
        tickets = await jira_service.get_tickets_from_database(project_key=project_key)

        # Get summary statistics
        total_tickets = len(tickets)
        tickets_by_status = {}
        blocked_count = 0

        for ticket in tickets:
            status = ticket.get("status", "Unknown")
            tickets_by_status[status] = tickets_by_status.get(status, 0) + 1

            if ticket.get("is_blocked", False):
                blocked_count += 1

        return {
            "total_tickets": total_tickets,
            "blocked_tickets": blocked_count,
            "tickets_by_status": tickets_by_status,
            "tickets": tickets[:50],  # Limit to first 50 for performance
            "project_key": project_key or "all",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get JIRA tickets: {str(e)}")


# Manual JIRA data refresh (for debugging/initial setup only)
@api_router.post("/jira/refresh")
async def refresh_jira_data(
    authenticated: bool = Depends(verify_api_key),
    project_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Manual JIRA data refresh for debugging/initial setup. Use webhooks for real-time updates."""
    try:
        from devsync_ai.services.jira import JiraService
        from datetime import datetime, timedelta

        jira_service = JiraService()

        # Only sync recent tickets for manual refresh (last 7 days)
        updated_since = datetime.now() - timedelta(days=7)

        # Perform one-time sync for debugging/setup
        result = await jira_service.sync_and_store_tickets(
            project_key=project_key, updated_since=updated_since
        )

        return {
            "status": "success",
            "refresh_completed_at": datetime.now().isoformat(),
            "note": "This is for debugging only. Real-time updates come from JIRA webhooks.",
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JIRA refresh failed: {str(e)}")


# Get blocked JIRA tickets for bottleneck analysis
@api_router.get("/jira/blocked")
async def get_blocked_tickets(
    authenticated: bool = Depends(verify_api_key),
    project_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get blocked JIRA tickets and bottlenecks."""
    try:
        from devsync_ai.services.jira import JiraService

        jira_service = JiraService()

        # Get tickets from database
        tickets = await jira_service.get_tickets_from_database(project_key=project_key)

        # Filter for blocked tickets
        blocked_tickets = [ticket for ticket in tickets if ticket.get("is_blocked", False)]

        # Categorize by severity
        high_severity = [t for t in blocked_tickets if t.get("blocker_severity") == "high"]
        medium_severity = [t for t in blocked_tickets if t.get("blocker_severity") == "medium"]

        return {
            "total_blocked": len(blocked_tickets),
            "high_severity": len(high_severity),
            "medium_severity": len(medium_severity),
            "blocked_tickets": blocked_tickets,
            "project_key": project_key or "all",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get blocked tickets: {str(e)}")


# ========================================
# SLACK API ENDPOINTS
# ========================================


# Send custom notifications to Slack channels (TODO: Not implemented)
@api_router.post("/slack/notify")
async def send_slack_notification(
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, str]:
    """Send custom Slack notifications."""
    # TODO: Implement in task 5.3
    return {"message": "Slack notification endpoint - to be implemented"}


# ========================================
# ANALYTICS API ENDPOINTS
# ========================================


# Analyze team performance and identify bottlenecks (TODO: Not implemented)
@api_router.get("/analytics/bottlenecks")
async def get_bottlenecks(
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, str]:
    """Get team analytics and bottlenecks."""
    # TODO: Implement in task 6.2
    return {"message": "Analytics bottlenecks endpoint - to be implemented"}


# ========================================
# CHANGELOG API ENDPOINTS
# ========================================


# Generate automated weekly changelog reports (TODO: Not implemented)
@api_router.get("/changelog/weekly")
async def get_weekly_changelog(
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, str]:
    """Generate weekly changelog."""
    # TODO: Implement in task 8.2
    return {"message": "Weekly changelog endpoint - to be implemented"}


# Get blocked JIRA tickets for bottleneck analysis
@api_router.get("/jira/blocked")
async def get_blocked_tickets(
    authenticated: bool = Depends(verify_api_key),
    project_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get blocked JIRA tickets and bottlenecks."""
    try:
        from devsync_ai.services.jira import JiraService

        jira_service = JiraService()

        # Get tickets from database
        tickets = await jira_service.get_tickets_from_database(project_key=project_key)

        # Filter for blocked tickets
        blocked_tickets = [ticket for ticket in tickets if ticket.get("is_blocked", False)]

        # Categorize by severity
        high_severity = [t for t in blocked_tickets if t.get("blocker_severity") == "high"]
        medium_severity = [t for t in blocked_tickets if t.get("blocker_severity") == "medium"]

        return {
            "total_blocked": len(blocked_tickets),
            "high_severity": len(high_severity),
            "medium_severity": len(medium_severity),
            "blocked_tickets": blocked_tickets,
            "project_key": project_key or "all",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get blocked tickets: {str(e)}")


# Get PR to JIRA ticket mappings for debugging/reporting
@api_router.get("/jira/pr-mappings")
async def get_pr_ticket_mappings(
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, Any]:
    """Get PR to JIRA ticket mappings."""
    try:
        from devsync_ai.services.jira import JiraService

        jira_service = JiraService()
        mappings = await jira_service.get_pr_ticket_mappings()

        return {"total_mappings": len(mappings), "mappings": mappings}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get PR-ticket mappings: {str(e)}")


# Test database schema and check if tables exist
@api_router.get("/database/schema")
async def check_database_schema(
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, Any]:
    """Check database schema and table existence."""
    try:
        from devsync_ai.database.connection import get_database

        db = await get_database()

        # Check if required tables exist
        tables_to_check = ["jira_tickets", "bottlenecks", "pull_requests", "team_members"]
        schema_status = {}

        for table in tables_to_check:
            try:
                # Try to query the table (limit 0 to just check existence)
                result = await db.select(table, limit=0)
                schema_status[table] = {"exists": True, "accessible": True}
            except Exception as e:
                schema_status[table] = {"exists": False, "error": str(e)}

        # Check database health
        health = await db.health_check()

        return {
            "database_healthy": health,
            "tables": schema_status,
            "migration_needed": any(not t.get("exists", False) for t in schema_status.values()),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database schema check failed: {str(e)}")


# Test JIRA API authentication and credentials
@api_router.get("/jira/test")
async def test_jira_auth(
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, Any]:
    """Test JIRA authentication."""
    try:
        from devsync_ai.services.jira import JiraService

        jira_service = JiraService()
        connection_info = await jira_service.test_authentication()

        return {
            "server_url": connection_info.server_url,
            "username": connection_info.username,
            "authenticated": connection_info.authenticated,
            "server_info": connection_info.server_info,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JIRA authentication failed: {str(e)}")
