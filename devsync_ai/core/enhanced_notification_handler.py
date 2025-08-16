"""
Enhanced notification handler that orchestrates all notification processing components.
Integrates filtering, deduplication, routing, batching, and scheduling.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
from enum import Enum

from .channel_router import ChannelRouter, RoutingContext, NotificationType, NotificationUrgency
from .notification_deduplicator import NotificationDeduplicator, DeduplicationResult
from .smart_message_batcher import SmartMessageBatcher, BatchableMessage, ContentType
from .template_registry import create_end_to_end_message
from .message_formatter import TemplateConfig, SlackMessage


class ProcessingDecision(Enum):
    """Decisions for notification processing."""
    SEND_IMMEDIATELY = "send_immediately"
    BATCH_AND_SEND = "batch_and_send"
    SCHEDULE_FOR_WORK_HOURS = "schedule_for_work_hours"
    FILTER_OUT = "filter_out"
    DUPLICATE_SKIP = "duplicate_skip"
    RATE_LIMITED = "rate_limited"
    ERROR_FALLBACK = "error_fallback"


@dataclass
class WorkHoursConfig:
    """Configuration for work hours."""
    enabled: bool = True
    start_hour: int = 9  # 9 AM
    end_hour: int = 17   # 5 PM
    timezone: str = "UTC"
    work_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Mon-Fri
    urgent_bypass: bool = True  # Allow urgent notifications outside work hours


@dataclass
class FilterConfig:
    """Configuration for notification filtering."""
    enabled: bool = True
    min_priority_level: str = "low"  # low, medium, high, critical
    blocked_authors: List[str] = field(default_factory=list)
    blocked_repositories: List[str] = field(default_factory=list)
    blocked_projects: List[str] = field(default_factory=list)
    allowed_notification_types: Optional[List[NotificationType]] = None
    custom_filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationContext:
    """Context for notification processing."""
    notification_type: NotificationType
    event_type: str
    data: Dict[str, Any]
    team_id: str
    author: Optional[str] = None
    channel_override: Optional[str] = None
    priority_override: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """Result of notification processing."""
    decision: ProcessingDecision
    channel: Optional[str] = None
    message: Optional[SlackMessage] = None
    scheduled_for: Optional[datetime] = None
    reason: str = ""
    deduplication_result: Optional[DeduplicationResult] = None
    routing_context: Optional[RoutingContext] = None
    processing_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)


class EnhancedNotificationHandler:
    """Main handler that orchestrates all notification processing components."""
    
    def __init__(self,
                 router: Optional[ChannelRouter] = None,
                 deduplicator: Optional[NotificationDeduplicator] = None,
                 batcher: Optional[SmartMessageBatcher] = None,
                 work_hours_config: Optional[WorkHoursConfig] = None,
                 filter_config: Optional[FilterConfig] = None,
                 template_config: Optional[TemplateConfig] = None,
                 supabase_client=None):
        """Initialize enhanced notification handler."""
        
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.router = router or ChannelRouter()
        self.deduplicator = deduplicator or NotificationDeduplicator(supabase_client)
        self.batcher = batcher or SmartMessageBatcher()
        
        # Configuration
        self.work_hours_config = work_hours_config or WorkHoursConfig()
        self.filter_config = filter_config or FilterConfig()
        self.template_config = template_config or TemplateConfig(team_id="default")
        
        # Database client
        self.supabase = supabase_client
        
        # Processing statistics
        self._stats = {
            "total_processed": 0,
            "sent_immediately": 0,
            "batched": 0,
            "scheduled": 0,
            "filtered_out": 0,
            "duplicates_skipped": 0,
            "rate_limited": 0,
            "errors": 0,
            "processing_time_total_ms": 0.0
        }
        
        # Error tracking
        self._recent_errors: List[Dict[str, Any]] = []
        
        self.logger.info("EnhancedNotificationHandler initialized")
    
    async def process_notification(self, context: NotificationContext) -> ProcessingResult:
        """Process a notification through the complete pipeline."""
        
        start_time = datetime.now()
        result = ProcessingResult(decision=ProcessingDecision.ERROR_FALLBACK)
        
        try:
            self._stats["total_processed"] += 1
            
            # Step 1: Apply filters
            if not self._should_process_notification(context):
                result.decision = ProcessingDecision.FILTER_OUT
                result.reason = "filtered_by_rules"
                self._stats["filtered_out"] += 1
                return result
            
            # Step 2: Check for duplicates
            dedup_result = await self.deduplicator.check_duplicate(
                notification_type=context.notification_type,
                data=context.data,
                channel=context.channel_override or "unknown",
                team_id=context.team_id,
                author=context.author
            )
            
            result.deduplication_result = dedup_result
            
            if dedup_result.is_duplicate:
                result.decision = ProcessingDecision.DUPLICATE_SKIP
                result.reason = f"duplicate: {dedup_result.reason}"
                self._stats["duplicates_skipped"] += 1
                return result
            
            # Step 3: Determine routing
            urgency = self.router.analyze_urgency(context.data, context.notification_type)
            
            routing_context = RoutingContext(
                notification_type=context.notification_type,
                urgency=urgency,
                team_id=context.team_id,
                content_data=context.data,
                author=context.author,
                timestamp=context.timestamp,
                metadata=context.metadata
            )
            
            result.routing_context = routing_context
            
            target_channel = self.router.route_notification(
                routing_context, 
                context.channel_override
            )
            result.channel = target_channel
            
            # Step 4: Check work hours and urgency
            if not self._is_work_hours(context.timestamp) and not self._is_urgent(urgency):
                # Schedule for next work hours
                scheduled_time = self._calculate_next_work_hours(context.timestamp)
                result.decision = ProcessingDecision.SCHEDULE_FOR_WORK_HOURS
                result.scheduled_for = scheduled_time
                result.reason = f"scheduled_for_work_hours: {scheduled_time}"
                
                # Store in database for scheduling
                await self._store_scheduled_notification(context, target_channel, scheduled_time)
                self._stats["scheduled"] += 1
                return result
            
            # Step 5: Create message
            try:
                message_dict = create_end_to_end_message(
                    context.event_type,
                    context.data,
                    self.template_config
                )
                
                # Convert to SlackMessage if needed
                if isinstance(message_dict, dict):
                    message = SlackMessage(
                        blocks=message_dict.get("blocks", []),
                        text=message_dict.get("text", ""),
                        metadata=message_dict.get("metadata", {})
                    )
                else:
                    message = message_dict
                
                result.message = message
                
            except Exception as e:
                self.logger.error(f"Error creating message: {e}")
                result.errors.append(f"message_creation_error: {e}")
                # Continue with fallback message
                message = self._create_fallback_message(context)
                result.message = message
            
            # Step 6: Decide on immediate vs batched sending
            if self._should_send_immediately(urgency, context.notification_type):
                result.decision = ProcessingDecision.SEND_IMMEDIATELY
                result.reason = "urgent_or_critical"
                self._stats["sent_immediately"] += 1
                
                # Record notification to prevent duplicates
                await self.deduplicator.record_notification(
                    notification_type=context.notification_type,
                    data=context.data,
                    channel=target_channel,
                    team_id=context.team_id,
                    notification_hash=dedup_result.hash_value,
                    author=context.author
                )
                
            else:
                # Add to batch
                batchable_message = BatchableMessage(
                    content_type=self._map_notification_to_content_type(context.notification_type),
                    data=context.data,
                    author=context.author or "unknown",
                    priority=urgency.value,
                    timestamp=context.timestamp,
                    metadata={
                        "notification_type": context.notification_type.value,
                        "team_id": context.team_id,
                        "dedup_hash": dedup_result.hash_value
                    }
                )
                
                batched_message = self.batcher.add_message(batchable_message, target_channel)
                
                if batched_message:
                    # Batch was flushed, message was sent
                    result.decision = ProcessingDecision.SEND_IMMEDIATELY
                    result.reason = "batch_flushed"
                    result.message = batched_message
                    self._stats["sent_immediately"] += 1
                else:
                    # Message added to batch
                    result.decision = ProcessingDecision.BATCH_AND_SEND
                    result.reason = "added_to_batch"
                    self._stats["batched"] += 1
                
                # Record notification to prevent duplicates
                await self.deduplicator.record_notification(
                    notification_type=context.notification_type,
                    data=context.data,
                    channel=target_channel,
                    team_id=context.team_id,
                    notification_hash=dedup_result.hash_value,
                    author=context.author
                )
            
        except Exception as e:
            self.logger.error(f"Error processing notification: {e}")
            result.decision = ProcessingDecision.ERROR_FALLBACK
            result.reason = f"processing_error: {e}"
            result.errors.append(str(e))
            self._stats["errors"] += 1
            
            # Track recent errors
            self._recent_errors.append({
                "timestamp": datetime.now(),
                "error": str(e),
                "context": {
                    "notification_type": context.notification_type.value,
                    "team_id": context.team_id,
                    "author": context.author
                }
            })
            
            # Keep only recent errors (last 100)
            if len(self._recent_errors) > 100:
                self._recent_errors = self._recent_errors[-100:]
        
        finally:
            # Record processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            result.processing_time_ms = processing_time
            self._stats["processing_time_total_ms"] += processing_time
        
        return result
    
    def _should_process_notification(self, context: NotificationContext) -> bool:
        """Check if notification should be processed based on filters."""
        
        if not self.filter_config.enabled:
            return True
        
        # Check priority level
        priority_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        min_level = priority_levels.get(self.filter_config.min_priority_level, 1)
        
        current_priority = context.data.get("priority", "medium").lower()
        current_level = priority_levels.get(current_priority, 2)
        
        if current_level < min_level:
            return False
        
        # Check blocked authors
        if context.author and context.author in self.filter_config.blocked_authors:
            return False
        
        # Check blocked repositories
        repository = context.data.get("repository", "").lower()
        if repository and any(blocked.lower() in repository for blocked in self.filter_config.blocked_repositories):
            return False
        
        # Check blocked projects
        project = context.data.get("project", "").lower()
        if project and any(blocked.lower() in project for blocked in self.filter_config.blocked_projects):
            return False
        
        # Check allowed notification types
        if (self.filter_config.allowed_notification_types and 
            context.notification_type not in self.filter_config.allowed_notification_types):
            return False
        
        # Apply custom filters
        for filter_name, filter_config in self.filter_config.custom_filters.items():
            if not self._apply_custom_filter(context, filter_name, filter_config):
                return False
        
        return True
    
    def _apply_custom_filter(self, context: NotificationContext, 
                           filter_name: str, filter_config: Any) -> bool:
        """Apply custom filter logic."""
        # This can be extended for specific custom filtering needs
        # For now, implement basic keyword filtering
        
        if isinstance(filter_config, dict):
            if "blocked_keywords" in filter_config:
                text_content = " ".join([
                    str(context.data.get("title", "")),
                    str(context.data.get("summary", "")),
                    str(context.data.get("description", ""))
                ]).lower()
                
                blocked_keywords = filter_config["blocked_keywords"]
                if any(keyword.lower() in text_content for keyword in blocked_keywords):
                    return False
        
        return True
    
    def _is_work_hours(self, timestamp: datetime) -> bool:
        """Check if timestamp is within work hours."""
        
        if not self.work_hours_config.enabled:
            return True
        
        # Check if it's a work day
        if timestamp.weekday() not in self.work_hours_config.work_days:
            return False
        
        # Check if it's within work hours
        current_hour = timestamp.hour
        return self.work_hours_config.start_hour <= current_hour < self.work_hours_config.end_hour
    
    def _is_urgent(self, urgency: NotificationUrgency) -> bool:
        """Check if notification is urgent enough to bypass work hours."""
        
        if not self.work_hours_config.urgent_bypass:
            return False
        
        return urgency in [NotificationUrgency.HIGH, NotificationUrgency.CRITICAL]
    
    def _calculate_next_work_hours(self, current_time: datetime) -> datetime:
        """Calculate next work hours start time."""
        
        # Start with next day
        next_day = current_time.replace(
            hour=self.work_hours_config.start_hour,
            minute=0,
            second=0,
            microsecond=0
        ) + timedelta(days=1)
        
        # Find next work day
        while next_day.weekday() not in self.work_hours_config.work_days:
            next_day += timedelta(days=1)
        
        return next_day
    
    def _should_send_immediately(self, urgency: NotificationUrgency, 
                               notification_type: NotificationType) -> bool:
        """Determine if notification should be sent immediately vs batched."""
        
        # Critical and high urgency always send immediately
        if urgency in [NotificationUrgency.CRITICAL, NotificationUrgency.HIGH]:
            return True
        
        # Certain notification types always send immediately
        immediate_types = [
            NotificationType.ALERT_SECURITY,
            NotificationType.ALERT_OUTAGE,
            NotificationType.JIRA_BLOCKER
        ]
        
        if notification_type in immediate_types:
            return True
        
        return False
    
    def _map_notification_to_content_type(self, notification_type: NotificationType) -> ContentType:
        """Map notification type to content type for batching."""
        
        if notification_type.value.startswith("pr_"):
            return ContentType.PULL_REQUEST
        elif notification_type.value.startswith("jira_"):
            return ContentType.JIRA_TICKET
        elif notification_type.value.startswith("alert_"):
            return ContentType.ALERT
        elif notification_type.value.startswith("standup_"):
            return ContentType.STANDUP
        else:
            return ContentType.GENERAL
    
    def _create_fallback_message(self, context: NotificationContext) -> SlackMessage:
        """Create a simple fallback message when template creation fails."""
        
        title = context.data.get("title", context.data.get("summary", "Notification"))
        author = context.author or "Unknown"
        
        fallback_text = f"{context.notification_type.value.replace('_', ' ').title()}: {title}"
        if author != "Unknown":
            fallback_text += f" (by {author})"
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": fallback_text
                }
            }
        ]
        
        return SlackMessage(
            blocks=blocks,
            text=fallback_text,
            metadata={
                "template_type": "fallback",
                "notification_type": context.notification_type.value,
                "created_at": datetime.now().isoformat()
            }
        )
    
    async def _store_scheduled_notification(self, context: NotificationContext,
                                          channel: str, scheduled_for: datetime) -> bool:
        """Store notification for later scheduling."""
        
        if not self.supabase:
            self.logger.warning("No database client available for scheduling")
            return False
        
        try:
            self.supabase.table("scheduled_notifications").insert({
                "notification_type": context.notification_type.value,
                "event_type": context.event_type,
                "data": context.data,
                "channel": channel,
                "team_id": context.team_id,
                "author": context.author,
                "scheduled_for": scheduled_for.isoformat(),
                "sent": False,
                "created_at": datetime.now().isoformat(),
                "metadata": context.metadata
            }).execute()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing scheduled notification: {e}")
            return False
    
    async def flush_batches(self, channel: Optional[str] = None) -> Dict[str, List[SlackMessage]]:
        """Manually flush batches for immediate sending."""
        
        if channel:
            messages = self.batcher.flush_channel_batches(channel)
            return {channel: messages}
        else:
            return self.batcher.flush_all_batches()
    
    async def process_scheduled_notifications(self) -> Dict[str, Any]:
        """Process notifications that are scheduled to be sent now."""
        
        if not self.supabase:
            return {"error": "No database client available"}
        
        try:
            current_time = datetime.now()
            
            # Get notifications due to be sent
            response = self.supabase.table("scheduled_notifications").select("*").eq(
                "sent", False
            ).lte(
                "scheduled_for", current_time.isoformat()
            ).execute()
            
            results = {
                "processed": 0,
                "sent": 0,
                "errors": 0,
                "notifications": []
            }
            
            for notification_data in response.data:
                results["processed"] += 1
                
                try:
                    # Recreate notification context
                    context = NotificationContext(
                        notification_type=NotificationType(notification_data["notification_type"]),
                        event_type=notification_data["event_type"],
                        data=notification_data["data"],
                        team_id=notification_data["team_id"],
                        author=notification_data.get("author"),
                        channel_override=notification_data["channel"],
                        timestamp=datetime.fromisoformat(notification_data["created_at"]),
                        metadata=notification_data.get("metadata", {})
                    )
                    
                    # Process the notification
                    result = await self.process_notification(context)
                    
                    if result.decision in [ProcessingDecision.SEND_IMMEDIATELY, ProcessingDecision.BATCH_AND_SEND]:
                        results["sent"] += 1
                        
                        # Mark as sent in database
                        self.supabase.table("scheduled_notifications").update({
                            "sent": True,
                            "sent_at": current_time.isoformat()
                        }).eq("id", notification_data["id"]).execute()
                    
                    results["notifications"].append({
                        "id": notification_data["id"],
                        "decision": result.decision.value,
                        "reason": result.reason
                    })
                    
                except Exception as e:
                    results["errors"] += 1
                    self.logger.error(f"Error processing scheduled notification {notification_data['id']}: {e}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing scheduled notifications: {e}")
            return {"error": str(e)}
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics."""
        
        total_processed = self._stats["total_processed"]
        avg_processing_time = (
            self._stats["processing_time_total_ms"] / total_processed 
            if total_processed > 0 else 0
        )
        
        return {
            **self._stats,
            "average_processing_time_ms": avg_processing_time,
            "recent_errors_count": len(self._recent_errors),
            "router_stats": self.router.get_routing_stats(),
            "deduplication_stats": self.deduplicator.get_deduplication_stats(),
            "batcher_stats": self.batcher.get_batch_stats(),
            "spam_prevention_stats": self.batcher.get_spam_prevention_stats()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status."""
        
        total_processed = self._stats["total_processed"]
        error_rate = (self._stats["errors"] / total_processed * 100) if total_processed > 0 else 0
        
        # Determine health status
        if error_rate > 10:
            health_status = "unhealthy"
        elif error_rate > 5:
            health_status = "degraded"
        else:
            health_status = "healthy"
        
        return {
            "status": health_status,
            "error_rate_percent": error_rate,
            "total_processed": total_processed,
            "recent_errors": self._recent_errors[-5:],  # Last 5 errors
            "components": {
                "router": "healthy",  # Could add health checks to components
                "deduplicator": "healthy",
                "batcher": "healthy",
                "database": "healthy" if self.supabase else "unavailable"
            }
        }
    
    def update_configuration(self, 
                           work_hours_config: Optional[WorkHoursConfig] = None,
                           filter_config: Optional[FilterConfig] = None,
                           template_config: Optional[TemplateConfig] = None) -> None:
        """Update handler configuration."""
        
        if work_hours_config:
            self.work_hours_config = work_hours_config
            self.logger.info("Updated work hours configuration")
        
        if filter_config:
            self.filter_config = filter_config
            self.logger.info("Updated filter configuration")
        
        if template_config:
            self.template_config = template_config
            self.logger.info("Updated template configuration")


# Global handler instance
default_notification_handler = EnhancedNotificationHandler()