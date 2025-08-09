"""API routes for DevSync AI."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any

from devsync_ai.config import settings


# Security scheme for API authentication
security = HTTPBearer(auto_error=False)

# Main API router
api_router = APIRouter()


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


# Placeholder routes for future implementation
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


@api_router.get("/jira/tickets")
async def get_jira_tickets(
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, str]:
    """Get JIRA ticket status."""
    # TODO: Implement in task 4.2
    return {"message": "JIRA tickets endpoint - to be implemented"}


@api_router.post("/slack/notify")
async def send_slack_notification(
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, str]:
    """Send custom Slack notifications."""
    # TODO: Implement in task 5.3
    return {"message": "Slack notification endpoint - to be implemented"}


@api_router.get("/analytics/bottlenecks")
async def get_bottlenecks(
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, str]:
    """Get team analytics and bottlenecks."""
    # TODO: Implement in task 6.2
    return {"message": "Analytics bottlenecks endpoint - to be implemented"}


@api_router.get("/changelog/weekly")
async def get_weekly_changelog(
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, str]:
    """Generate weekly changelog."""
    # TODO: Implement in task 8.2
    return {"message": "Weekly changelog endpoint - to be implemented"}
