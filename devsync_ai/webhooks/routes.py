"""Webhook routes for external service integrations."""

from fastapi import APIRouter, Request, HTTPException, Header
from typing import Dict, Any, Optional
import hmac
import hashlib
import logging

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


@webhook_router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
) -> Dict[str, str]:
    """Handle GitHub webhook events."""
    payload = await request.body()

    # Verify signature
    if not x_hub_signature_256 or not verify_github_signature(
        payload, x_hub_signature_256
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    logger.info(f"Received GitHub webhook event: {x_github_event}")

    # TODO: Implement event processing in task 7.2
    # - Parse payload based on event type
    # - Trigger appropriate service methods
    # - Update database with new information

    return {"message": f"GitHub {x_github_event} event received"}


@webhook_router.post("/jira")
async def jira_webhook(request: Request) -> Dict[str, str]:
    """Handle JIRA webhook events."""
    payload = await request.json()

    logger.info(
        f"Received JIRA webhook event: {payload.get('webhookEvent', 'unknown')}"
    )

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
