"""
Integration layer between Agent Hooks and Enhanced Notification Handler.

This module provides the bridge between JIRA Agent Hooks and the enhanced
notification system, handling context creation, routing, and urgency mapping.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .agent_hooks import (
    EnrichedEvent, HookExecutionResult, EventCategory, UrgencyLevel, SignificanceLevel
)
from .enhanced_notification_handler import (
    NotificationContext, ProcessingResult, EnhancedNotificationHandler
)
from .channel_router import NotificationType, NotificationUrgency
from .notification_integration import default_notification_system


logger = logging.getLogger(__name__)


class HookNotificationType(Enum):
    """Notification types specific to Agent Hooks."""
    JIRA_STATUS_CHANGE = "jira_status"
    JIRA_ASSIGNMENT = "jira_assignment"
    JIRA_ASSIGNMENT_CHANGE = "jira_assignment"
    JIRA_CRITICAL_ASSIGNMENT = "jira_assignment"
    JIRA_OVERLOAD_WARNING = "jira_assignment"
    JIRA_COMMENT_PRIORITY = "jira_comment"
    JIRA_BLOCKER_DETECTED = "jira_blocker"
    JIRA_BLOCKER_RESOLVED = "jira_blocker"
    JIRA_PRIORITY_CHANGE = "jira_priority"
    JIRA_SPRINT_RISK = "jira_sprint"
    JIRA_WORKLOAD_ALERT = "jira_status"


@dataclass
class HookNotificationContext:
    """Extended notification context for Agent Hook events."""
    hook_id: str
    hook_type: str
    event: EnrichedEvent
    execution_result: HookExecutionResult
    notification_type: HookNotificationType
    urgency_override: Optional[UrgencyLevel] = None
    channel_override: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class HookNotificationMapper:
    """Maps Agent Hook events to notification system contexts."""
    
    # Mapping from event categories to notification types
    CATEGORY_TO_NOTIFICATION_TYPE = {
        EventCategory.STATUS_CHANGE: HookNotificationType.JIRA_STATUS_CHANGE,
        EventCategory.ASSIGNMENT: HookNotificationType.JIRA_ASSIGNMENT,
        EventCategory.COMMENT: HookNotificationType.JIRA_COMMENT_PRIORITY,
        EventCategory.BLOCKER: HookNotificationType.JIRA_BLOCKER_DETECTED,
        EventCategory.PRIORITY_CHANGE: HookNotificationType.JIRA_PRIORITY_CHANGE,
    }
    
    # Mapping from hook urgency to notification urgency
    URGENCY_MAPPING = {
        UrgencyLevel.LOW: NotificationUrgency.LOW,
        UrgencyLevel.MEDIUM: NotificationUrgency.MEDIUM,
        UrgencyLevel.HIGH: NotificationUrgency.HIGH,
        UrgencyLevel.CRITICAL: NotificationUrgency.CRITICAL,
    }
    
    # Channel routing based on hook types and urgency
    HOOK_CHANNEL_ROUTING = {
        "StatusChangeHook": {
            UrgencyLevel.LOW: ["#dev-updates"],
            UrgencyLevel.MEDIUM: ["#dev-updates"],
            UrgencyLevel.HIGH: ["#dev-updates", "#team-alerts"],
            UrgencyLevel.CRITICAL: ["#dev-updates", "#team-alerts", "#critical-alerts"],
        },
        "AssignmentHook": {
            UrgencyLevel.LOW: ["#assignments"],
            UrgencyLevel.MEDIUM: ["#assignments", "#dev-updates"],
            UrgencyLevel.HIGH: ["#assignments", "#dev-updates", "#team-alerts"],
            UrgencyLevel.CRITICAL: ["#assignments", "#dev-updates", "#critical-alerts"],
        },
        "CommentHook": {
            UrgencyLevel.LOW: ["#ticket-discussions"],
            UrgencyLevel.MEDIUM: ["#ticket-discussions", "#dev-updates"],
            UrgencyLevel.HIGH: ["#ticket-discussions", "#dev-updates", "#team-alerts"],
            UrgencyLevel.CRITICAL: ["#ticket-discussions", "#critical-alerts"],
        },
        "BlockerHook": {
            UrgencyLevel.LOW: ["#blockers"],
            UrgencyLevel.MEDIUM: ["#blockers", "#dev-updates"],
            UrgencyLevel.HIGH: ["#blockers", "#dev-updates", "#team-alerts"],
            UrgencyLevel.CRITICAL: ["#blockers", "#critical-alerts", "#escalation"],
        },
    }
    
    def __init__(self):
        """Initialize the hook notification mapper."""
        self.logger = logging.getLogger(__name__)
    
    def create_notification_context(self, hook_context: HookNotificationContext) -> NotificationContext:
        """Create a notification context from a hook context."""
        
        event = hook_context.event
        execution_result = hook_context.execution_result
        
        # Determine notification type
        notification_type = self._determine_notification_type(hook_context)
        
        # Create notification data
        notification_data = self._create_notification_data(hook_context)
        
        # Determine team ID
        team_id = self._determine_team_id(event)
        
        # Determine author
        author = self._determine_author(event)
        
        # Determine channel override
        channel_override = self._determine_channel_override(hook_context)
        
        # Create notification context
        context = NotificationContext(
            notification_type=NotificationType(notification_type.value),
            event_type=event.event_type,
            data=notification_data,
            team_id=team_id,
            author=author,
            channel_override=channel_override,
            priority_override=hook_context.urgency_override.value if hook_context.urgency_override else None,
            timestamp=event.timestamp,
            metadata={
                **hook_context.metadata,
                "hook_id": hook_context.hook_id,
                "hook_type": hook_context.hook_type,
                "execution_id": execution_result.execution_id,
                "event_id": event.event_id,
                "ticket_key": event.ticket_key,
                "project_key": event.project_key,
            }
        )
        
        return context
    
    def _determine_notification_type(self, hook_context: HookNotificationContext) -> HookNotificationType:
        """Determine the notification type based on hook context."""
        
        # Use explicit notification type if provided
        if hook_context.notification_type:
            return hook_context.notification_type
        
        # Map from event category
        event = hook_context.event
        if event.classification and event.classification.category:
            return self.CATEGORY_TO_NOTIFICATION_TYPE.get(
                event.classification.category,
                HookNotificationType.JIRA_STATUS_CHANGE
            )
        
        # Default based on hook type
        hook_type = hook_context.hook_type
        if "Assignment" in hook_type:
            return HookNotificationType.JIRA_ASSIGNMENT
        elif "Comment" in hook_type:
            return HookNotificationType.JIRA_COMMENT_PRIORITY
        elif "Blocker" in hook_type:
            return HookNotificationType.JIRA_BLOCKER_DETECTED
        elif "Status" in hook_type or "StatusChange" in hook_type:
            return HookNotificationType.JIRA_STATUS_CHANGE
        else:
            return HookNotificationType.JIRA_STATUS_CHANGE
    
    def _create_notification_data(self, hook_context: HookNotificationContext) -> Dict[str, Any]:
        """Create notification data from hook context."""
        
        event = hook_context.event
        execution_result = hook_context.execution_result
        
        # Base notification data
        data = {
            "ticket_key": event.ticket_key,
            "project_key": event.project_key,
            "summary": event.ticket_details.get("summary", "No summary") if event.ticket_details else "No summary",
            "description": event.ticket_details.get("description", "") if event.ticket_details else "",
            "priority": event.ticket_details.get("priority", "Medium") if event.ticket_details else "Medium",
            "status": event.ticket_details.get("status", "Unknown") if event.ticket_details else "Unknown",
            "assignee": event.ticket_details.get("assignee", {}).get("displayName", "Unassigned") if event.ticket_details else "Unassigned",
            "reporter": event.ticket_details.get("reporter", {}).get("displayName", "Unknown") if event.ticket_details else "Unknown",
            "event_timestamp": event.timestamp.isoformat(),
            "hook_execution": {
                "hook_id": hook_context.hook_id,
                "hook_type": hook_context.hook_type,
                "execution_time_ms": execution_result.execution_time_ms,
                "notification_sent": execution_result.notification_sent,
                "metadata": execution_result.metadata,
            }
        }
        
        # Add classification data if available
        if event.classification:
            data["classification"] = {
                "category": event.classification.category.value,
                "urgency": event.classification.urgency.value,
                "significance": event.classification.significance.value,
                "affected_teams": event.classification.affected_teams,
                "routing_hints": event.classification.routing_hints,
                "keywords": event.classification.keywords,
            }
        
        # Add stakeholder information
        if event.stakeholders:
            data["stakeholders"] = [
                {
                    "user_id": s.user_id,
                    "display_name": s.display_name,
                    "email": s.email,
                    "role": s.role,
                    "team_id": s.team_id,
                    "slack_user_id": s.slack_user_id,
                }
                for s in event.stakeholders
            ]
        
        # Add context data
        if event.context_data:
            data["context"] = event.context_data
        
        # Add hook-specific data from execution result
        if execution_result.notification_result:
            data["hook_notification_result"] = execution_result.notification_result
        
        return data
    
    def _determine_team_id(self, event: EnrichedEvent) -> str:
        """Determine team ID from event."""
        
        # Check classification for affected teams
        if event.classification and event.classification.affected_teams:
            return event.classification.affected_teams[0]
        
        # Check stakeholders for team information
        for stakeholder in event.stakeholders:
            if stakeholder.team_id:
                return stakeholder.team_id
        
        # Check context data
        team_id = event.context_data.get("team_id")
        if team_id:
            return team_id
        
        # Default to project key as team identifier
        return event.project_key.lower() if event.project_key else "default"
    
    def _determine_author(self, event: EnrichedEvent) -> Optional[str]:
        """Determine author from event."""
        
        # Check ticket details for reporter
        if event.ticket_details and event.ticket_details.get("reporter"):
            reporter = event.ticket_details["reporter"]
            return reporter.get("displayName") or reporter.get("name")
        
        # Check stakeholders for reporter role
        for stakeholder in event.stakeholders:
            if stakeholder.role == "reporter":
                return stakeholder.display_name
        
        # Check context data
        return event.context_data.get("author")
    
    def _determine_channel_override(self, hook_context: HookNotificationContext) -> Optional[str]:
        """Determine channel override based on hook context."""
        
        # Use explicit channel override if provided
        if hook_context.channel_override:
            return hook_context.channel_override
        
        # Determine urgency level
        urgency = hook_context.urgency_override
        if not urgency and hook_context.event.classification:
            urgency = hook_context.event.classification.urgency
        if not urgency:
            urgency = UrgencyLevel.MEDIUM
        
        # Get channels for hook type and urgency
        hook_type = hook_context.hook_type
        channels = self.HOOK_CHANNEL_ROUTING.get(hook_type, {}).get(urgency, [])
        
        # Return first channel as override (router will handle multiple channels)
        return channels[0] if channels else None


class HookNotificationIntegrator:
    """Integrates Agent Hooks with the Enhanced Notification Handler."""
    
    def __init__(self, 
                 notification_handler: Optional[EnhancedNotificationHandler] = None,
                 mapper: Optional[HookNotificationMapper] = None):
        """Initialize the hook notification integrator."""
        
        self.logger = logging.getLogger(__name__)
        self.notification_handler = notification_handler or default_notification_system.handler
        self.mapper = mapper or HookNotificationMapper()
        
        # Statistics tracking
        self._stats = {
            "notifications_processed": 0,
            "notifications_sent": 0,
            "notifications_batched": 0,
            "notifications_scheduled": 0,
            "notifications_filtered": 0,
            "errors": 0,
        }
    
    async def process_hook_notification(self, 
                                      hook_id: str,
                                      hook_type: str,
                                      event: EnrichedEvent,
                                      execution_result: HookExecutionResult,
                                      notification_type: Optional[HookNotificationType] = None,
                                      urgency_override: Optional[UrgencyLevel] = None,
                                      channel_override: Optional[str] = None,
                                      metadata: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a hook notification through the enhanced notification system."""
        
        try:
            self._stats["notifications_processed"] += 1
            
            # Create hook notification context
            hook_context = HookNotificationContext(
                hook_id=hook_id,
                hook_type=hook_type,
                event=event,
                execution_result=execution_result,
                notification_type=notification_type,
                urgency_override=urgency_override,
                channel_override=channel_override,
                metadata=metadata or {}
            )
            
            # Map to notification context
            notification_context = self.mapper.create_notification_context(hook_context)
            
            # Process through enhanced notification handler
            result = await self.notification_handler.process_notification(notification_context)
            
            # Update statistics
            self._update_stats(result)
            
            # Log result
            self.logger.info(
                f"Hook notification processed: {hook_id} -> {result.decision.value} "
                f"(channel: {result.channel}, time: {result.processing_time_ms:.1f}ms)"
            )
            
            return result
            
        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"Error processing hook notification for {hook_id}: {e}", exc_info=True)
            raise
    
    def _update_stats(self, result: ProcessingResult) -> None:
        """Update statistics based on processing result."""
        
        decision = result.decision.value
        
        if decision == "send_immediately":
            self._stats["notifications_sent"] += 1
        elif decision == "batch_and_send":
            self._stats["notifications_batched"] += 1
        elif decision == "schedule_for_work_hours":
            self._stats["notifications_scheduled"] += 1
        elif decision in ["filter_out", "duplicate_skip", "rate_limited"]:
            self._stats["notifications_filtered"] += 1
    
    async def send_hook_notification_directly(self,
                                            hook_id: str,
                                            hook_type: str,
                                            notification_type: HookNotificationType,
                                            data: Dict[str, Any],
                                            team_id: str,
                                            author: Optional[str] = None,
                                            channel_override: Optional[str] = None,
                                            urgency: Optional[UrgencyLevel] = None) -> ProcessingResult:
        """Send a hook notification directly without an event context."""
        
        try:
            # Create notification context directly
            context = NotificationContext(
                notification_type=NotificationType(notification_type.value),
                event_type=f"hook.{hook_type.lower()}",
                data={
                    **data,
                    "hook_id": hook_id,
                    "hook_type": hook_type,
                },
                team_id=team_id,
                author=author,
                channel_override=channel_override,
                priority_override=urgency.value if urgency else None,
                metadata={
                    "source": "hook_direct",
                    "hook_id": hook_id,
                    "hook_type": hook_type,
                }
            )
            
            # Process through enhanced notification handler
            result = await self.notification_handler.process_notification(context)
            
            # Update statistics
            self._stats["notifications_processed"] += 1
            self._update_stats(result)
            
            return result
            
        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"Error sending direct hook notification for {hook_id}: {e}", exc_info=True)
            raise
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration statistics."""
        
        total_processed = self._stats["notifications_processed"]
        
        return {
            **self._stats,
            "success_rate": (
                (total_processed - self._stats["errors"]) / total_processed * 100
                if total_processed > 0 else 0
            ),
            "sent_rate": (
                self._stats["notifications_sent"] / total_processed * 100
                if total_processed > 0 else 0
            ),
            "batched_rate": (
                self._stats["notifications_batched"] / total_processed * 100
                if total_processed > 0 else 0
            ),
        }
    
    def reset_stats(self) -> None:
        """Reset integration statistics."""
        
        for key in self._stats:
            self._stats[key] = 0


# Global integrator instance
default_hook_notification_integrator = HookNotificationIntegrator()