"""
JIRA Assignment Webhook Processor

This module processes JIRA assignment change webhooks and triggers
intelligent workload analysis and notifications.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from devsync_ai.services.jira_assignment_analyzer import JiraAssignmentAnalyzer
from devsync_ai.core.webhook_security import secure_webhook_handler


logger = logging.getLogger(__name__)


class JiraAssignmentWebhookProcessor:
    """
    Processes JIRA assignment change webhooks with comprehensive analysis.
    
    Features:
    - Validates webhook signatures for security
    - Detects assignment changes from webhook payloads
    - Triggers workload analysis and notifications
    - Provides detailed processing results
    """
    
    def __init__(self):
        """Initialize the webhook processor."""
        self.assignment_analyzer = JiraAssignmentAnalyzer()
    
    async def process_webhook(self, payload: Dict[str, Any], headers: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Process a JIRA webhook for assignment changes.
        
        Args:
            payload: JIRA webhook payload
            headers: HTTP headers from the webhook request
            
        Returns:
            Processing result with status and details
        """
        try:
            logger.info("🎯 Processing JIRA assignment webhook")
            
            # Validate webhook payload
            if not self._is_assignment_change(payload):
                return {
                    "success": True,
                    "message": "Webhook processed but no assignment change detected",
                    "action": "ignored"
                }
            
            # Extract basic info for logging
            issue_key = payload.get("issue", {}).get("key", "unknown")
            webhook_event = payload.get("webhookEvent", "unknown")
            
            logger.info(f"📋 Assignment change detected for {issue_key} (event: {webhook_event})")
            
            # Analyze assignment change
            analysis_result = await self.assignment_analyzer.analyze_assignment_change(payload)
            
            if analysis_result.get("success"):
                logger.info(f"✅ Assignment analysis completed for {issue_key}")
                return {
                    "success": True,
                    "message": f"Assignment change processed for {issue_key}",
                    "issue_key": issue_key,
                    "webhook_event": webhook_event,
                    "analysis": analysis_result,
                    "processed_at": datetime.utcnow().isoformat()
                }
            else:
                logger.error(f"❌ Assignment analysis failed for {issue_key}: {analysis_result.get('error')}")
                return {
                    "success": False,
                    "message": f"Assignment analysis failed for {issue_key}",
                    "issue_key": issue_key,
                    "error": analysis_result.get("error"),
                    "processed_at": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            logger.error(f"❌ Error processing JIRA assignment webhook: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Webhook processing failed: {str(e)}",
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    def _is_assignment_change(self, payload: Dict[str, Any]) -> bool:
        """
        Check if the webhook payload represents an assignment change.
        
        Args:
            payload: JIRA webhook payload
            
        Returns:
            True if this is an assignment change event
        """
        try:
            # Check webhook event type
            webhook_event = payload.get("webhookEvent", "")
            if webhook_event not in ["jira:issue_updated", "jira:issue_created"]:
                return False
            
            # For issue creation, check if there's an assignee
            if webhook_event == "jira:issue_created":
                issue = payload.get("issue", {})
                fields = issue.get("fields", {})
                return fields.get("assignee") is not None
            
            # For issue updates, check if assignee field changed
            changelog = payload.get("changelog", {})
            if "items" in changelog:
                for item in changelog["items"]:
                    if item.get("field") == "assignee":
                        return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking assignment change: {e}")
            return False
    
    async def process_secure_webhook(
        self, 
        payload: Dict[str, Any], 
        headers: Dict[str, str],
        signature_header: str = "X-Hub-Signature-256"
    ) -> Dict[str, Any]:
        """
        Process webhook with security validation.
        
        Args:
            payload: JIRA webhook payload
            headers: HTTP headers
            signature_header: Header containing webhook signature
            
        Returns:
            Processing result with security validation
        """
        try:
            # Validate webhook signature
            signature = headers.get(signature_header)
            if signature:
                is_valid = await secure_webhook_handler.validate_webhook_signature(
                    payload, signature, "jira"
                )
                if not is_valid:
                    logger.warning("❌ Invalid webhook signature")
                    return {
                        "success": False,
                        "message": "Invalid webhook signature",
                        "error": "security_validation_failed"
                    }
            
            # Process the webhook
            return await self.process_webhook(payload, headers)
            
        except Exception as e:
            logger.error(f"❌ Error in secure webhook processing: {e}")
            return {
                "success": False,
                "message": f"Secure webhook processing failed: {str(e)}",
                "error": str(e)
            }


# Global instance for use in webhook routes
jira_assignment_processor = JiraAssignmentWebhookProcessor()


async def process_jira_assignment_webhook(payload: Dict[str, Any], headers: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Convenience function to process JIRA assignment webhooks.
    
    Args:
        payload: JIRA webhook payload
        headers: HTTP headers (optional)
        
    Returns:
        Processing result
    """
    return await jira_assignment_processor.process_webhook(payload, headers)


async def process_secure_jira_assignment_webhook(
    payload: Dict[str, Any], 
    headers: Dict[str, str],
    signature_header: str = "X-Hub-Signature-256"
) -> Dict[str, Any]:
    """
    Convenience function to process JIRA assignment webhooks with security validation.
    
    Args:
        payload: JIRA webhook payload
        headers: HTTP headers
        signature_header: Header containing webhook signature
        
    Returns:
        Processing result with security validation
    """
    return await jira_assignment_processor.process_secure_webhook(payload, headers, signature_header)