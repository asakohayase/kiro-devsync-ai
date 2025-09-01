"""
JIRA Assignment Webhook Handler

Handles JIRA assignment change webhooks and triggers the assignment hook
for intelligent workload analysis and notifications.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException

from devsync_ai.hooks.jira_assignment_hook import JiraAssignmentHook
from devsync_ai.core.agent_hook_dispatcher import default_hook_dispatcher
from devsync_ai.core.event_classification_engine import EventClassificationEngine, EventCategory, UrgencyLevel
from devsync_ai.core.enhanced_notification_handler import EnrichedEvent
from devsync_ai.webhooks.secure_webhook_handler import secure_webhook_handler


logger = logging.getLogger(__name__)

# Create router for JIRA assignment webhooks
jira_assignment_router = APIRouter()

# Initialize assignment hook
assignment_hook = JiraAssignmentHook()


async def initialize_assignment_hook():
    """Initialize the JIRA assignment hook."""
    try:
        await assignment_hook.initialize()
        
        # Register the hook with the dispatcher
        default_hook_dispatcher.register_hook("jira:assignment_change", assignment_hook)
        
        logger.info("✅ JIRA Assignment Hook initialized and registered")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize JIRA Assignment Hook: {e}")
        raise


async def shutdown_assignment_hook():
    """Shutdown the JIRA assignment hook."""
    try:
        # Unregister the hook
        default_hook_dispatcher.unregister_hook("jira:assignment_change")
        
        logger.info("✅ JIRA Assignment Hook shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Error during JIRA Assignment Hook shutdown: {e}")


def is_assignment_change_event(webhook_data: Dict[str, Any]) -> bool:
    """
    Check if the webhook event is an assignment change.
    
    Args:
        webhook_data: JIRA webhook payload
        
    Returns:
        True if this is an assignment change event
    """
    try:
        # Check webhook event type
        webhook_event = webhook_data.get("webhookEvent", "")
        if webhook_event != "jira:issue_updated":
            return False
        
        # Check if assignee field changed in changelog
        changelog = webhook_data.get("changelog", {})
        if "items" in changelog:
            for item in changelog["items"]:
                if item.get("field") == "assignee":
                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error checking assignment change event: {e}")
        return False


def extract_assignment_change_details(webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract assignment change details from webhook payload.
    
    Args:
        webhook_data: JIRA webhook payload
        
    Returns:
        Assignment change details or None if extraction fails
    """
    try:
        issue_data = webhook_data.get("issue", {})
        changelog = webhook_data.get("changelog", {})
        
        if not issue_data or not changelog:
            return None
        
        # Find assignee change in changelog
        assignee_change = None
        if "items" in changelog:
            for item in changelog["items"]:
                if item.get("field") == "assignee":
                    assignee_change = item
                    break
        
        if not assignee_change:
            return None
        
        # Extract basic issue information
        fields = issue_data.get("fields", {})
        
        details = {
            "ticket_key": issue_data.get("key"),
            "title": fields.get("summary", ""),
            "previous_assignee": assignee_change.get("fromString"),
            "new_assignee": assignee_change.get("toString"),
            "priority": fields.get("priority", {}).get("name", "Medium"),
            "status": fields.get("status", {}).get("name", "Unknown"),
            "story_points": fields.get("customfield_10016"),  # Common story points field
            "reporter": fields.get("reporter", {}).get("displayName", "Unknown"),
            "project_key": issue_data.get("key", "").split("-")[0] if issue_data.get("key") else "",
            "issue_type": fields.get("issuetype", {}).get("name", "Task"),
            "labels": [label["name"] for label in fields.get("labels", [])],
            "components": [comp["name"] for comp in fields.get("components", [])],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Extract sprint information
        sprint_field = fields.get("customfield_10020")  # Common sprint field
        if sprint_field and isinstance(sprint_field, list) and sprint_field:
            sprint_data = sprint_field[0]
            if isinstance(sprint_data, dict):
                details["sprint"] = sprint_data.get("name")
            elif isinstance(sprint_data, str):
                # Parse sprint string format
                import re
                match = re.search(r'name=([^,\]]+)', sprint_data)
                if match:
                    details["sprint"] = match.group(1)
        
        # Extract due date
        due_date = fields.get("duedate")
        if due_date:
            try:
                details["due_date"] = datetime.fromisoformat(due_date.replace("Z", "+00:00")).isoformat()
            except:
                pass
        
        return details
        
    except Exception as e:
        logger.error(f"❌ Error extracting assignment change details: {e}")
        return None


def determine_assignment_urgency(assignment_details: Dict[str, Any]) -> UrgencyLevel:
    """
    Determine urgency level for assignment change.
    
    Args:
        assignment_details: Assignment change details
        
    Returns:
        Urgency level for the assignment change
    """
    try:
        priority = assignment_details.get("priority", "Medium").lower()
        new_assignee = assignment_details.get("new_assignee")
        
        # High urgency for critical/high priority assignments
        if priority in ["critical", "blocker", "highest"]:
            return UrgencyLevel.HIGH
        elif priority == "high":
            return UrgencyLevel.MEDIUM
        elif not new_assignee:  # Unassignment
            return UrgencyLevel.MEDIUM
        else:
            return UrgencyLevel.LOW
            
    except Exception as e:
        logger.error(f"❌ Error determining assignment urgency: {e}")
        return UrgencyLevel.LOW


async def process_assignment_change_webhook(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process JIRA assignment change webhook.
    
    Args:
        webhook_data: JIRA webhook payload
        
    Returns:
        Processing result
    """
    try:
        logger.info("🎯 Processing JIRA assignment change webhook")
        
        # Extract assignment change details
        assignment_details = extract_assignment_change_details(webhook_data)
        if not assignment_details:
            return {
                "success": False,
                "message": "Could not extract assignment change details",
                "status": "invalid_payload"
            }
        
        ticket_key = assignment_details.get("ticket_key")
        previous_assignee = assignment_details.get("previous_assignee")
        new_assignee = assignment_details.get("new_assignee")
        
        logger.info(f"📋 Assignment change for {ticket_key}: {previous_assignee} → {new_assignee}")
        
        # Determine urgency and category
        urgency = determine_assignment_urgency(assignment_details)
        
        # Create enriched event
        enriched_event = EnrichedEvent(
            event_id=f"jira_assignment_{ticket_key}_{datetime.utcnow().timestamp()}",
            source="jira",
            event_type="jira:assignment_change",
            category=EventCategory.ASSIGNMENT,
            urgency=urgency,
            data=assignment_details,
            timestamp=datetime.utcnow(),
            team_id=assignment_details.get("project_key", "default"),
            user_id=new_assignee or "unassigned"
        )
        
        # Classify and enrich the event
        classification_engine = EventClassificationEngine()
        enriched_event = await classification_engine.classify_and_enrich(enriched_event)
        
        # Execute the assignment hook
        if assignment_hook.should_execute(enriched_event):
            result = await assignment_hook.execute(enriched_event)
            
            if result.success:
                logger.info(f"✅ Assignment hook executed successfully for {ticket_key}")
                return {
                    "success": True,
                    "message": f"Assignment change processed for {ticket_key}",
                    "ticket_key": ticket_key,
                    "assignment_change": f"{previous_assignee} → {new_assignee}",
                    "hook_result": result.metadata,
                    "status": "processed"
                }
            else:
                logger.error(f"❌ Assignment hook execution failed for {ticket_key}: {result.message}")
                return {
                    "success": False,
                    "message": f"Assignment hook execution failed: {result.message}",
                    "ticket_key": ticket_key,
                    "status": "hook_failed"
                }
        else:
            logger.info(f"ℹ️ Assignment hook skipped for {ticket_key} (should_execute returned False)")
            return {
                "success": True,
                "message": f"Assignment change acknowledged but not processed by hook",
                "ticket_key": ticket_key,
                "status": "skipped"
            }
        
    except Exception as e:
        logger.error(f"❌ Error processing assignment change webhook: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error processing assignment change: {str(e)}",
            "status": "error"
        }


@jira_assignment_router.post("/jira/assignment")
async def jira_assignment_webhook(request: Request) -> Dict[str, Any]:
    """
    Handle JIRA assignment change webhooks with security validation.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Webhook processing result
    """
    async def process_assignment_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process the assignment webhook payload."""
        try:
            # Check if this is an assignment change event
            if not is_assignment_change_event(payload):
                return {
                    "success": True,
                    "message": "Not an assignment change event",
                    "status": "ignored"
                }
            
            # Process the assignment change
            return await process_assignment_change_webhook(payload)
            
        except Exception as e:
            logger.error(f"❌ Assignment webhook processing error: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Assignment webhook processing failed: {str(e)}",
                "status": "error"
            }
    
    # Use secure webhook handler for comprehensive security
    return await secure_webhook_handler.process_webhook_with_security(
        request=request,
        webhook_source="jira",
        event_type="assignment_change",
        processor_func=process_assignment_webhook,
        team_id="default"  # Could be extracted from payload
    )


@jira_assignment_router.get("/jira/assignment/health")
async def assignment_webhook_health():
    """Health check for JIRA assignment webhook handler."""
    try:
        # Check if assignment hook is initialized
        hook_initialized = assignment_hook.jira_service is not None
        
        # Check if hook is registered
        hook_registered = "jira:assignment_change" in default_hook_dispatcher._hooks
        
        status = {
            "status": "healthy" if hook_initialized and hook_registered else "degraded",
            "assignment_hook_initialized": hook_initialized,
            "assignment_hook_registered": hook_registered,
            "timestamp": datetime.utcnow().isoformat(),
            "endpoints": {
                "webhook": "/jira/assignment",
                "health": "/jira/assignment/health",
                "test": "/jira/assignment/test"
            }
        }
        
        return status
        
    except Exception as e:
        logger.error(f"❌ Assignment webhook health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@jira_assignment_router.post("/jira/assignment/test")
async def test_assignment_webhook():
    """Test endpoint for JIRA assignment webhook processing."""
    try:
        # Create test assignment change payload
        test_payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "summary": "Test assignment change",
                    "assignee": {
                        "displayName": "Test User",
                        "name": "testuser"
                    },
                    "priority": {
                        "name": "High"
                    },
                    "status": {
                        "name": "In Progress"
                    },
                    "issuetype": {
                        "name": "Task"
                    },
                    "reporter": {
                        "displayName": "Test Reporter"
                    },
                    "customfield_10016": 5,  # Story points
                    "labels": [{"name": "test"}],
                    "components": []
                }
            },
            "changelog": {
                "items": [
                    {
                        "field": "assignee",
                        "fromString": "Previous User",
                        "toString": "Test User"
                    }
                ]
            }
        }
        
        # Process the test payload
        result = await process_assignment_change_webhook(test_payload)
        
        return {
            "test_status": "completed",
            "test_payload": test_payload,
            "processing_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Assignment webhook test failed: {e}")
        return {
            "test_status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }