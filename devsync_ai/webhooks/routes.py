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
from devsync_ai.webhooks.jira_webhook_handler import jira_webhook_router, initialize_dispatcher, shutdown_dispatcher
from devsync_ai.webhooks.secure_webhook_handler import secure_webhook_handler


logger = logging.getLogger(__name__)

# Webhook router
webhook_router = APIRouter()

# Include JIRA webhook router
webhook_router.include_router(jira_webhook_router)


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
        "services": ["github", "slack", "jira", "enhanced_notifications", "security"]
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
    
    # Test enhanced notification system
    try:
        from devsync_ai.core.notification_integration import default_notification_system
        
        # Get health status
        notification_health = await default_notification_system.get_health_status()
        status["enhanced_notifications"] = {
            "status": notification_health["status"],
            "components": notification_health["components"],
            "initialized": default_notification_system._initialized,
            "running": default_notification_system._running
        }
        
        # Update overall status based on notification system health
        if notification_health["status"] == "unhealthy":
            status["status"] = "degraded"
        
    except Exception as e:
        status["enhanced_notifications"] = {
            "status": "error",
            "error": str(e)
        }
        status["status"] = "degraded"
    
    # Test security system
    try:
        security_status = await secure_webhook_handler.get_security_status()
        status["security"] = security_status
        
        # Check if any security components have errors
        if "error" in security_status:
            status["status"] = "degraded"
            
    except Exception as e:
        status["security"] = {
            "status": "error",
            "error": str(e)
        }
        status["status"] = "degraded"
    
    return status


@webhook_router.get("/notifications/health")
async def notification_system_health():
    """Detailed health check for the enhanced notification system."""
    try:
        from devsync_ai.core.notification_integration import default_notification_system
        
        # Ensure system is initialized
        if not default_notification_system._initialized:
            await default_notification_system.initialize()
        
        # Get comprehensive health status
        health_status = await default_notification_system.get_health_status()
        
        # Get system statistics
        system_stats = await default_notification_system.get_system_stats()
        
        return {
            "health": health_status,
            "statistics": system_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting notification system health: {e}")
        return {
            "health": {
                "status": "error",
                "error": str(e)
            },
            "timestamp": datetime.utcnow().isoformat()
        }


@webhook_router.get("/notifications/stats")
async def notification_system_stats():
    """Get detailed statistics for the enhanced notification system."""
    try:
        from devsync_ai.core.notification_integration import default_notification_system
        
        if not default_notification_system._initialized:
            return {"error": "Notification system not initialized"}
        
        stats = await default_notification_system.get_system_stats()
        return {
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting notification system stats: {e}")
        return {"error": str(e)}


@webhook_router.get("/security/status")
async def security_system_status():
    """Get comprehensive security system status."""
    try:
        status = await secure_webhook_handler.get_security_status()
        return status
        
    except Exception as e:
        logger.error(f"Error getting security system status: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@webhook_router.post("/notifications/flush")
async def flush_notification_batches():
    """Manually flush all pending notification batches."""
    try:
        from devsync_ai.core.notification_integration import default_notification_system
        
        if not default_notification_system._running:
            return {"error": "Notification system not running"}
        
        flushed_batches = await default_notification_system.flush_all_batches()
        
        total_messages = sum(len(messages) for messages in flushed_batches.values())
        
        return {
            "message": f"Flushed {total_messages} messages from {len(flushed_batches)} channels",
            "channels": list(flushed_batches.keys()),
            "total_messages": total_messages,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error flushing notification batches: {e}")
        return {"error": str(e)}


@webhook_router.post("/notifications/scheduler/run")
async def force_scheduler_run():
    """Force an immediate scheduler run for testing."""
    try:
        from devsync_ai.core.notification_integration import default_notification_system
        
        if not default_notification_system._running:
            return {"error": "Notification system not running"}
        
        result = await default_notification_system.force_scheduler_run()
        
        return {
            "message": "Scheduler run completed",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error forcing scheduler run: {e}")
        return {"error": str(e)}


async def send_enhanced_notification(event_type: str, payload: Dict[str, Any], team_id: str = "default") -> bool:
    """Send notification through the enhanced notification system."""
    try:
        from devsync_ai.core.notification_integration import default_notification_system
        
        # Ensure system is running
        if not default_notification_system._running:
            await default_notification_system.initialize()
            await default_notification_system.start()
        
        # Send notification based on event type
        if event_type.startswith("pull_request."):
            result = await default_notification_system.send_github_notification(
                event_type, payload, team_id
            )
        elif event_type.startswith("jira:"):
            result = await default_notification_system.send_jira_notification(
                event_type, payload, team_id
            )
        else:
            # Generic notification
            result = await default_notification_system.send_notification(
                notification_type=event_type,
                event_type=event_type,
                data=payload,
                team_id=team_id
            )
        
        if result.decision.value in ["send_immediately", "batch_and_send"]:
            logger.info(f"✅ Enhanced notification sent for {event_type} - Decision: {result.decision.value}")
            return True
        else:
            logger.info(f"📋 Enhanced notification processed for {event_type} - Decision: {result.decision.value}, Reason: {result.reason}")
            return True  # Still successful, just handled differently
    
    except Exception as e:
        logger.error(f"❌ Error sending enhanced notification: {str(e)}", exc_info=True)
        return False


async def send_slack_notification(pr_data: Dict[str, Any], action: str) -> bool:
    """Send Slack notification for PR events (legacy fallback)."""
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
    """Handle GitHub webhook events with comprehensive security."""
    
    async def process_github_webhook(payload: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Process GitHub webhook payload."""
        try:
            logger.info(f"🚀 Processing GitHub webhook: {x_github_event} (ID: {x_github_delivery})")
            
            # Extract event type and action
            event_type = payload.get("action", "unknown")
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
            elif x_github_event == "pull_request" and "pull_request" in payload:
                # Send enhanced notification in background
                pr_data = payload["pull_request"]
                event_name = f"pull_request.{event_type}"
                
                # Extract team ID from repository or use default
                team_id = payload.get("repository", {}).get("owner", {}).get("login", "default")
                
                # Send through enhanced notification system
                asyncio.create_task(send_enhanced_notification(event_name, payload, team_id))
                
                # Also send legacy Slack notification as fallback
                asyncio.create_task(send_slack_notification(pr_data, event_type))
                
                # Handle JIRA integration
                return await handle_pr_webhook(payload, event_type)

            # Handle pull request review events
            elif x_github_event == "pull_request_review" and "review" in payload:
                # Send enhanced notification for review events
                pr_data = payload["pull_request"]
                review_data = payload["review"]
                team_id = payload.get("repository", {}).get("owner", {}).get("login", "default")
                
                # Map review states to notification events
                review_state = review_data.get("state", "").lower()
                if review_state == "approved":
                    event_name = "pull_request.approved"
                elif review_state == "changes_requested":
                    event_name = "pull_request.changes_requested"
                else:
                    event_name = "pull_request.reviewed"
                
                asyncio.create_task(send_enhanced_notification(event_name, payload, team_id))
                
                return await handle_pr_review_webhook(payload, event_type)

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
                
        except Exception as e:
            logger.error(f"❌ GitHub webhook processing error: {str(e)}", exc_info=True)
            return {"message": f"Error processing webhook: {str(e)}", "status": "error"}
    
    # Use secure webhook handler for comprehensive security
    return await secure_webhook_handler.process_webhook_with_security(
        request=request,
        webhook_source="github",
        event_type=x_github_event or "unknown",
        processor_func=process_github_webhook,
        team_id="default"  # Could be extracted from payload
    )


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


@webhook_router.post("/jira")
async def jira_webhook(request: Request) -> Dict[str, Any]:
    """Handle JIRA webhook events for enhanced notifications."""
    try:
        logger.info("🚀 Received JIRA webhook")
        
        # Get raw payload
        raw_payload = await request.body()
        
        # Parse JSON payload
        try:
            webhook_data = json.loads(raw_payload.decode())
            logger.info("✅ Successfully parsed JIRA JSON payload")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JIRA JSON payload: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")
        
        # Extract event information
        webhook_event = webhook_data.get("webhookEvent", "unknown")
        issue_event_type = webhook_data.get("issue_event_type_name", "")
        
        logger.info(f"📋 JIRA Event: {webhook_event} - {issue_event_type}")
        
        # Map JIRA events to our notification system
        event_mapping = {
            "jira:issue_created": "jira:issue_created",
            "jira:issue_updated": "jira:issue_updated",
            "jira:issue_deleted": "jira:issue_deleted",
            "jira:issue_assigned": "jira:issue_assigned",
            "jira:issue_commented": "jira:issue_commented"
        }
        
        # Determine event type
        if webhook_event == "jira:issue_updated":
            # Check what was updated
            changelog = webhook_data.get("changelog", {})
            items = changelog.get("items", [])
            
            for item in items:
                field = item.get("field", "")
                if field == "status":
                    event_type = "jira:issue_updated"
                    break
                elif field == "priority":
                    event_type = "jira:issue_priority_changed"
                    break
                elif field == "assignee":
                    event_type = "jira:issue_assigned"
                    break
            else:
                event_type = "jira:issue_updated"
        else:
            event_type = event_mapping.get(webhook_event, webhook_event)
        
        # Extract team ID from project key or use default
        issue_data = webhook_data.get("issue", {})
        project_key = issue_data.get("fields", {}).get("project", {}).get("key", "default")
        team_id = f"project_{project_key.lower()}"
        
        # Send enhanced notification in background
        asyncio.create_task(send_enhanced_notification(event_type, webhook_data, team_id))
        
        # Process JIRA ticket update in background
        asyncio.create_task(
            process_jira_update_background(
                f"jira_webhook_{issue_data.get('key', 'unknown')}",
                process_jira_ticket_update,
                webhook_data
            )
        )
        
        return {
            "message": f"JIRA webhook {webhook_event} processed",
            "event_type": event_type,
            "issue_key": issue_data.get("key", "unknown"),
            "status": "processing_background"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ JIRA webhook processing error: {str(e)}", exc_info=True)
        return {"message": f"Error processing JIRA webhook: {str(e)}", "status": "error"}


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
