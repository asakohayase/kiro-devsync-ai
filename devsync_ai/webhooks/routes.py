"""Webhook routes for external service integrations."""

from fastapi import APIRouter, Request, HTTPException, Header, Form
from typing import Dict, Any, Optional
import hmac
import hashlib
import logging
import asyncio
import json
from datetime import datetime

from devsync_ai.config import settings


logger = logging.getLogger(__name__)

# Webhook router
webhook_router = APIRouter()


def verify_github_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature."""
    if not signature.startswith("sha256="):
        return False

    expected_signature = hmac.new(
        settings.github_webhook_secret.encode(), payload, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected_signature}", signature)


def verify_slack_signature(payload: bytes, timestamp: str, signature: str) -> bool:
    """Verify Slack webhook signature."""
    if not timestamp or not signature:
        return False

    sig_basestring = f"v0:{timestamp}:{payload.decode()}"
    expected_signature = (
        "v0="
        + hmac.new(
            settings.slack_signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(expected_signature, signature)


async def process_jira_update_background(task_name: str, task_func, *args, **kwargs):
    """Process JIRA updates in the background with error handling."""
    try:
        logger = logging.getLogger(__name__)
        logger.info(f"Starting background task: {task_name}")

        result = await task_func(*args, **kwargs)

        logger.info(f"✅ Background task completed: {task_name} - Result: {result}")
        return result

    except Exception as e:
        logger.error(f"❌ Background task failed: {task_name} - Error: {str(e)}")
        # You could add additional error handling here like:
        # - Send to error tracking service
        # - Store failed tasks for retry
        # - Send notifications
        return None


async def process_jira_and_database_update_background(
    task_name: str, pr_data: Dict[str, Any], action: str
):
    """Update both JIRA ticket and local database to avoid duplication."""
    try:
        from devsync_ai.services.jira import JiraService
        from devsync_ai.database.connection import get_database

        logger.info(f"Starting combined JIRA+DB update: {task_name}")

        jira_service = JiraService()
        pr_number = pr_data["number"]

        # 1. Update JIRA ticket
        await jira_service.update_ticket_from_pr_status(pr_data, action)

        # 2. Get the linked JIRA ticket key
        db = await get_database()
        pr_mapping = await db.select(
            table="pr_ticket_mappings", filters={"pr_number": pr_number}, select_fields="ticket_key"
        )

        if pr_mapping and pr_mapping.get("data"):
            ticket_key = pr_mapping["data"][0]["ticket_key"]

            # 3. Update local jira_tickets table with fresh data
            try:
                # Get fresh ticket data from JIRA
                ticket_details = await jira_service.get_ticket_details(ticket_key)

                if ticket_details:
                    # Convert to database format
                    ticket_data = {
                        "key": ticket_details.key,
                        "summary": ticket_details.summary,
                        "status": ticket_details.status,
                        "assignee": ticket_details.assignee,
                        "priority": ticket_details.priority,
                        "story_points": ticket_details.story_points,
                        "sprint": ticket_details.sprint,
                        "blocked": ticket_details.blocked,
                        "last_updated": ticket_details.last_updated,
                        "time_in_status_seconds": int(
                            ticket_details.time_in_status.total_seconds()
                        ),
                    }

                    # Update database
                    await db.update(
                        table="jira_tickets", data=ticket_data, filters={"key": ticket_key}
                    )

                    logger.info(f"✅ Updated both JIRA and database for ticket {ticket_key}")

            except Exception as e:
                logger.error(f"Failed to update local database for {ticket_key}: {e}")
                # JIRA update succeeded, database update failed - not critical

        # 4. Update pull_requests table
        pr_update_data = {
            "id": str(pr_data["id"]),
            "repository": pr_data["base"]["repo"]["full_name"],
            "title": pr_data["title"],
            "author": pr_data["user"]["login"],
            "status": "merged" if action == "closed" and pr_data.get("merged") else action,
            "merge_conflicts": False,  # Could be enhanced
            "created_at": pr_data["created_at"],
            "updated_at": pr_data["updated_at"],
            "reviewers": [],  # Could be enhanced
            "labels": [label["name"] for label in pr_data.get("labels", [])],
            "data": pr_data,
        }

        # Upsert PR data
        existing_pr = await db.select(
            table="pull_requests", filters={"id": str(pr_data["id"])}, select_fields="id"
        )

        if existing_pr:
            await db.update(
                table="pull_requests", data=pr_update_data, filters={"id": str(pr_data["id"])}
            )
        else:
            await db.insert(table="pull_requests", data=pr_update_data)

        logger.info(f"✅ Combined update completed: {task_name}")
        return {"status": "success", "updated": ["jira", "database", "pull_requests"]}

    except Exception as e:
        logger.error(f"❌ Combined update failed: {task_name} - Error: {str(e)}")
        return {"status": "error", "error": str(e)}


async def handle_pr_webhook(payload: Dict[str, Any], action: str) -> Dict[str, Any]:
    """Handle GitHub pull request webhook events."""
    try:
        from devsync_ai.services.jira import JiraService

        pr_data = payload["pull_request"]
        pr_number = pr_data["number"]

        jira_service = JiraService()

        if action == "opened":
            # Create JIRA ticket for new PR - this needs to be synchronous to return ticket_key
            from devsync_ai.config import settings

            project_key = settings.jira_project_key

            # For PR creation, we still do it synchronously but with a shorter timeout
            try:
                ticket_key = await asyncio.wait_for(
                    jira_service.create_ticket_from_pr(pr_data, project_key=project_key),
                    timeout=8.0,  # 8 seconds max to leave buffer for GitHub's 10s timeout
                )

                return {
                    "message": f"Created JIRA ticket {ticket_key} for PR #{pr_number}",
                    "ticket_key": ticket_key,
                    "pr_number": pr_number,
                    "action": action,
                }
            except asyncio.TimeoutError:
                # If ticket creation times out, process in background
                asyncio.create_task(
                    process_jira_update_background(
                        f"create_ticket_pr_{pr_number}",
                        jira_service.create_ticket_from_pr,
                        pr_data,
                        project_key=project_key,
                    )
                )

                return {
                    "message": f"PR #{pr_number} received, creating JIRA ticket in background",
                    "pr_number": pr_number,
                    "action": action,
                    "status": "processing_background",
                }

        elif action in ["closed", "reopened", "ready_for_review"]:
            # Update both JIRA ticket AND local database - process in background for speed
            asyncio.create_task(
                process_jira_and_database_update_background(
                    f"update_pr_status_{pr_number}_{action}",
                    pr_data,
                    action,
                )
            )

            return {
                "message": f"PR #{pr_number} {action}, updating JIRA ticket in background",
                "pr_number": pr_number,
                "action": action,
                "status": "processing_background",
            }

        else:
            return {
                "message": f"No action taken for PR event: {action}",
                "pr_number": pr_number,
                "action": action,
            }

    except Exception as e:
        # Log the error but don't raise HTTPException to avoid webhook retries
        logger = logging.getLogger(__name__)
        logger.error(f"Error in PR webhook handler: {str(e)}")

        return {
            "message": f"Error processing PR #{payload.get('pull_request', {}).get('number', 'unknown')}: {str(e)}",
            "action": action,
            "status": "error",
        }


async def handle_pr_review_webhook(payload: Dict[str, Any], action: str) -> Dict[str, Any]:
    """Handle GitHub pull request review webhook events."""
    try:
        from devsync_ai.services.jira import JiraService

        pr_data = payload["pull_request"]
        review_data = payload["review"]
        pr_number = pr_data["number"]
        reviewer = review_data.get("user", {}).get("login", "unknown")
        review_state = review_data.get("state", "unknown")

        jira_service = JiraService()

        if action == "submitted":
            # Update JIRA ticket based on review state - process in background
            asyncio.create_task(
                process_jira_update_background(
                    f"update_pr_review_{pr_number}_{review_state}",
                    jira_service.update_ticket_from_pr_review,
                    pr_data,
                    review_data,
                )
            )

            return {
                "message": f"PR #{pr_number} review by {reviewer} ({review_state}), updating JIRA ticket in background",
                "pr_number": pr_number,
                "review_state": review_state,
                "reviewer": reviewer,
                "action": action,
                "status": "processing_background",
            }

        else:
            return {
                "message": f"No action taken for review event: {action}",
                "pr_number": pr_number,
                "action": action,
            }

    except Exception as e:
        # Log the error but don't raise HTTPException to avoid webhook retries
        logger = logging.getLogger(__name__)
        logger.error(f"Error in PR review webhook handler: {str(e)}")

        return {
            "message": f"Error processing PR #{payload.get('pull_request', {}).get('number', 'unknown')} review: {str(e)}",
            "action": action,
            "status": "error",
        }


@webhook_router.get("/")
async def webhook_root():
    """Root endpoint for webhooks."""
    return {
        "message": "DevSync AI Webhook Server",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "github": "/webhooks/github",
            "slack": "/webhooks/slack"
        }
    }


@webhook_router.get("/health")
async def webhook_health_check():
    """Health check endpoint for webhooks."""
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": ["github", "slack", "jira"]
    }
    
    # Test Slack connection if available
    try:
        from devsync_ai.services.slack import SlackService
        slack_service = SlackService()
        if slack_service.client:
            auth_result = await slack_service.test_connection()
            status["slack_connection"] = "ok" if auth_result.get("ok") else "error"
            status["bot_name"] = auth_result.get("user", "unknown")
    except Exception as e:
        status["slack_connection"] = "error"
        status["slack_error"] = str(e)
    
    return status


async def send_slack_notification(pr_data: Dict[str, Any], action: str) -> bool:
    """Send Slack notification for PR events."""
    try:
        from devsync_ai.services.slack import SlackService
        
        slack_service = SlackService()
        if not slack_service.client:
            logger.warning("⚠️ Slack client not available - cannot send notifications")
            return False
        
        # Use the service's PR notification method
        result = await slack_service.send_pr_notification(pr_data, action)
        
        if result.get("ok"):
            logger.info(f"✅ Slack notification sent for PR #{pr_data.get('number', 'unknown')}")
            return True
        else:
            logger.error(f"❌ Slack notification failed: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error sending Slack notification: {str(e)}", exc_info=True)
        return False



@webhook_router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Handle GitHub webhook events for JIRA integration and Slack notifications."""
    try:
        from devsync_ai.services.jira import JiraService

        logger.info(f"🚀 Received GitHub webhook: {x_github_event} (ID: {x_github_delivery})")

        # Get raw payload for signature verification
        raw_payload = await request.body()
        logger.info(f"📦 Raw body preview (first 200 chars): {raw_payload[:200]}")

        # Verify signature if webhook secret is configured
        if settings.github_webhook_secret:
            if not x_hub_signature_256 or not verify_github_signature(raw_payload, x_hub_signature_256):
                raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse JSON payload
        try:
            webhook_data = json.loads(raw_payload.decode())
            logger.info(f"✅ Successfully parsed JSON payload")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON payload: {e}")
            logger.error(f"❌ Raw body that failed: {raw_payload}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")

        # Extract event type and action
        event_type = webhook_data.get("action", "unknown")
        logger.info(f"📋 Event: {x_github_event}.{event_type}")

        # Handle ping events (GitHub webhook test)
        if x_github_event == "ping":
            logger.info("🏓 Ping event received - webhook is connected!")
            return {
                "status": "pong",
                "message": "DevSync AI webhook is working!",
                "delivery_id": x_github_delivery
            }

        # Handle pull request events
        elif x_github_event == "pull_request" and "pull_request" in webhook_data:
            # Send Slack notification in background
            pr_data = webhook_data["pull_request"]
            asyncio.create_task(send_slack_notification(pr_data, event_type))
            
            # Handle JIRA integration
            return await handle_pr_webhook(webhook_data, event_type)

        # Handle pull request review events FIRST (they also contain pull_request data)
        elif x_github_event == "pull_request_review" and "review" in webhook_data:
            return await handle_pr_review_webhook(webhook_data, event_type)

        else:
            # Return success for unhandled events to prevent retries
            logger.info(f"ℹ️ Event {x_github_event} received but not processed")
            return {
                "message": f"Event {x_github_event} received",
                "github_event": x_github_event,
                "action": event_type,
                "status": "acknowledged",
                "delivery_id": x_github_delivery
            }

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return {"message": "Invalid JSON payload", "status": "error"}
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {str(e)}", exc_info=True)
        # Return 200 with error message instead of raising HTTPException
        # This prevents GitHub from retrying the webhook
        return {"message": f"Error processing webhook: {str(e)}", "status": "error"}


async def process_jira_ticket_update(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process JIRA ticket update webhook event."""
    try:
        from devsync_ai.services.jira import JiraService
        from devsync_ai.database.connection import get_database

        # Extract ticket data from webhook payload
        issue_data = payload.get("issue", {})
        ticket_key = issue_data.get("key")

        if not ticket_key:
            logger.warning("JIRA webhook missing ticket key")
            return {"message": "Missing ticket key", "status": "error"}

        # Get JIRA service to convert issue data
        jira_service = JiraService()

        # Create a mock JIRA issue object from webhook data for conversion
        # This is a simplified approach - in production you might want to fetch full data
        ticket_data = {
            "key": ticket_key,
            "summary": issue_data.get("fields", {}).get("summary", ""),
            "status": issue_data.get("fields", {}).get("status", {}).get("name", "Unknown"),
            "assignee": (
                issue_data.get("fields", {}).get("assignee", {}).get("displayName")
                if issue_data.get("fields", {}).get("assignee")
                else None
            ),
            "priority": issue_data.get("fields", {}).get("priority", {}).get("name", "None"),
            "story_points": issue_data.get("fields", {}).get("customfield_10016"),
            "blocked": False,  # Will be determined by blocker detection
            "last_updated": datetime.now(),
            "time_in_status_seconds": 0,  # Will be calculated
            "data": issue_data,  # Store full webhook data
        }

        # Update database
        db = await get_database()

        # Check if ticket exists
        existing = await db.select(
            table="jira_tickets", filters={"key": ticket_key}, select_fields="key"
        )

        if existing:
            # Update existing ticket
            result = await db.update(
                table="jira_tickets", data=ticket_data, filters={"key": ticket_key}
            )
            action = "updated"
        else:
            # Insert new ticket
            result = await db.insert(table="jira_tickets", data=ticket_data)
            action = "created"

        # Run blocker detection on this ticket
        await detect_and_store_blockers([ticket_data])

        logger.info(f"JIRA ticket {ticket_key} {action} via webhook")

        return {
            "message": f"JIRA ticket {ticket_key} {action}",
            "ticket_key": ticket_key,
            "action": action,
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Error processing JIRA ticket update: {e}", exc_info=True)
        return {"message": f"Error processing JIRA ticket update: {str(e)}", "status": "error"}


async def detect_and_store_blockers(tickets: list) -> None:
    """Detect and store blockers for given tickets."""
    try:
        from devsync_ai.services.jira import JiraService
        from devsync_ai.database.connection import get_database

        jira_service = JiraService()

        # Convert ticket data to JiraTicket objects for blocker detection
        jira_tickets = []
        for ticket_data in tickets:
            # This is a simplified conversion - you might want to enhance this
            from devsync_ai.models.core import JiraTicket
            from datetime import timedelta

            jira_ticket = JiraTicket(
                key=ticket_data["key"],
                summary=ticket_data["summary"],
                status=ticket_data["status"],
                assignee=ticket_data["assignee"],
                priority=ticket_data["priority"],
                story_points=ticket_data.get("story_points"),
                sprint=None,  # Extract from webhook if needed
                blocked=False,
                last_updated=ticket_data["last_updated"],
                time_in_status=timedelta(seconds=ticket_data.get("time_in_status_seconds", 0)),
            )
            jira_tickets.append(jira_ticket)

        # Detect blockers
        blocked_tickets = await jira_service.detect_blocked_tickets(jira_tickets)

        # Store blockers in database
        if blocked_tickets:
            await jira_service.store_blocked_tickets(blocked_tickets)
            logger.info(f"Detected and stored {len(blocked_tickets)} blockers from webhook")

    except Exception as e:
        logger.error(f"Error in blocker detection: {e}", exc_info=True)


# JIRA webhook endpoint removed - not needed in GitHub-first architecture
# GitHub webhooks handle all JIRA integration via API calls


@webhook_router.post("/slack")
async def slack_webhook(
    request: Request,
    x_slack_request_timestamp: Optional[str] = Header(None),
    x_slack_signature: Optional[str] = Header(None),
) -> Dict[str, str]:
    """Handle Slack webhook events and interactions."""
    payload = await request.body()

    # Verify signature
    if not verify_slack_signature(
        payload, x_slack_request_timestamp or "", x_slack_signature or ""
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    logger.info("Received Slack webhook event")

    # TODO: Implement event processing in task 7.2
    # - Parse Slack event payload
    # - Handle slash commands or interactive components
    # - Respond appropriately

    return {"message": "Slack event received"}
