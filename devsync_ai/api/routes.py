"""API routes for DevSync AI."""

import os
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


# GitHub Webhook Handlers for JIRA Integration


@api_router.post("/webhooks/github")
async def github_webhook_handler(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Handle GitHub webhook events for JIRA integration."""
    try:
        from devsync_ai.services.jira import JiraService

        # Extract event type and action
        event_type = payload.get("action", "unknown")

        # Handle pull request events
        if "pull_request" in payload:
            return await handle_pr_webhook(payload, event_type)

        # Handle pull request review events
        elif "review" in payload:
            return await handle_pr_review_webhook(payload, event_type)

        else:
            return {"message": f"Unhandled webhook event type: {event_type}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process GitHub webhook: {str(e)}")


async def handle_pr_webhook(payload: Dict[str, Any], action: str) -> Dict[str, Any]:
    """Handle GitHub pull request webhook events."""
    try:
        from devsync_ai.services.jira import JiraService

        pr_data = payload["pull_request"]
        pr_number = pr_data["number"]

        jira_service = JiraService()

        if action == "opened":
            # Create JIRA ticket for new PR
            project_key = settings.jira_project_key

            ticket_key = await jira_service.create_ticket_from_pr(pr_data, project_key=project_key)

            return {
                "message": f"Created JIRA ticket {ticket_key} for PR #{pr_number}",
                "ticket_key": ticket_key,
                "pr_number": pr_number,
                "action": action,
            }

        elif action in ["closed", "reopened"]:
            # Update JIRA ticket status based on PR state
            success = await jira_service.update_ticket_from_pr_status(pr_data, action)

            return {
                "message": f"Updated JIRA ticket for PR #{pr_number}",
                "success": success,
                "pr_number": pr_number,
                "action": action,
            }

        elif action == "ready_for_review":
            # Update JIRA ticket when PR is ready for review
            success = await jira_service.update_ticket_from_pr_status(pr_data, action)

            return {
                "message": f"Updated JIRA ticket for PR #{pr_number} - ready for review",
                "success": success,
                "pr_number": pr_number,
                "action": action,
            }

        else:
            return {
                "message": f"No action taken for PR event: {action}",
                "pr_number": pr_number,
                "action": action,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to handle PR webhook: {str(e)}")


async def handle_pr_review_webhook(payload: Dict[str, Any], action: str) -> Dict[str, Any]:
    """Handle GitHub pull request review webhook events."""
    try:
        from devsync_ai.services.jira import JiraService

        pr_data = payload["pull_request"]
        review_data = payload["review"]
        pr_number = pr_data["number"]

        jira_service = JiraService()

        if action == "submitted":
            # Update JIRA ticket based on review state
            success = await jira_service.update_ticket_from_pr_review(pr_data, review_data)

            return {
                "message": f"Updated JIRA ticket for PR #{pr_number} review",
                "success": success,
                "pr_number": pr_number,
                "review_state": review_data.get("state", "unknown"),
                "reviewer": review_data.get("user", {}).get("login", "unknown"),
            }

        else:
            return {
                "message": f"No action taken for review event: {action}",
                "pr_number": pr_number,
                "action": action,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to handle PR review webhook: {str(e)}")


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
