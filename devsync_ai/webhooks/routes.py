"""Webhook routes for external service integrations."""

from fastapi import APIRouter, Request, HTTPException, Header, Form
from typing import Dict, Any, Optional
import hmac
import hashlib
import logging
import asyncio

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


async def handle_pr_webhook(payload: Dict[str, Any], action: str) -> Dict[str, Any]:
    """Handle GitHub pull request webhook events."""
    try:
        from devsync_ai.services.jira import JiraService

        pr_data = payload["pull_request"]
        pr_number = pr_data["number"]

        jira_service = JiraService()

        if action == "opened":
            # Create JIRA ticket for new PR - this needs to be synchronous to return ticket_key
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
            # Update JIRA ticket status - process in background for speed
            asyncio.create_task(
                process_jira_update_background(
                    f"update_pr_status_{pr_number}_{action}",
                    jira_service.update_ticket_from_pr_status,
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


@webhook_router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    payload: Optional[str] = Form(None),
) -> Dict[str, Any]:
    """Handle GitHub webhook events for JIRA integration."""
    try:
        from devsync_ai.services.jira import JiraService
        import json

        logger.info(f"Received GitHub webhook event: {x_github_event}")

        # Get payload - GitHub can send either JSON or form-encoded
        if payload:
            # Form-encoded data (Content-Type: application/x-www-form-urlencoded)
            logger.info("Parsing form-encoded payload")
            raw_payload = payload.encode()
            webhook_data = json.loads(payload)
        else:
            # JSON body (Content-Type: application/json)
            logger.info("Parsing JSON body")
            raw_payload = await request.body()
            webhook_data = json.loads(raw_payload.decode())

        # Verify signature
        if not x_hub_signature_256 or not verify_github_signature(raw_payload, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid signature")

        logger.info(f"Parsed payload keys: {list(webhook_data.keys())}")

        # Extract event type and action
        event_type = webhook_data.get("action", "unknown")
        logger.info(f"GitHub event: {x_github_event}, Action: {event_type}")

        # Handle pull request review events FIRST (they also contain pull_request data)
        if "review" in webhook_data and x_github_event == "pull_request_review":
            return await handle_pr_review_webhook(webhook_data, event_type)

        # Handle pull request events
        elif "pull_request" in webhook_data and x_github_event == "pull_request":
            return await handle_pr_webhook(webhook_data, event_type)

        else:
            # Return success for unhandled events to prevent retries
            return {
                "message": f"Unhandled webhook event type: {x_github_event}.{event_type}",
                "github_event": x_github_event,
                "action": event_type,
                "status": "ignored",
            }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return {"message": "Invalid JSON payload", "status": "error"}
    except Exception as e:
        logger.error(f"Unexpected error in webhook handler: {e}")
        # Return 200 with error message instead of raising HTTPException
        # This prevents GitHub from retrying the webhook
        return {"message": f"Error processing webhook: {str(e)}", "status": "error"}


@webhook_router.post("/jira")
async def jira_webhook(request: Request) -> Dict[str, str]:
    """Handle JIRA webhook events."""
    payload = await request.json()

    logger.info(f"Received JIRA webhook event: {payload.get('webhookEvent', 'unknown')}")

    # TODO: Implement event processing in task 7.2
    # - Validate JIRA webhook payload
    # - Process ticket updates
    # - Trigger blocker detection if needed

    return {"message": "JIRA event received"}


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
