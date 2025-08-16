"""
Channel routing system for intelligent notification routing.
Routes notifications to appropriate channels based on content, urgency, and team configuration.
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .message_formatter import SlackMessage
from .smart_message_batcher import BatchableMessage


class NotificationUrgency(Enum):
    """Urgency levels for notifications."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NotificationType(Enum):
    """Types of notifications for routing."""
    PR_NEW = "pr_new"
    PR_READY = "pr_ready"
    PR_APPROVED = "pr_approved"
    PR_CONFLICTS = "pr_conflicts"
    PR_MERGED = "pr_merged"
    PR_CLOSED = "pr_closed"
    JIRA_STATUS = "jira_status"
    JIRA_PRIORITY = "jira_priority"
    JIRA_ASSIGNMENT = "jira_assignment"
    JIRA_COMMENT = "jira_comment"
    JIRA_BLOCKER = "jira_blocker"
    JIRA_SPRINT = "jira_sprint"
    ALERT_BUILD = "alert_build"
    ALERT_DEPLOYMENT = "alert_deployment"
    ALERT_SECURITY = "alert_security"
    ALERT_OUTAGE = "alert_outage"
    ALERT_BUG = "alert_bug"
    STANDUP_DAILY = "standup_daily"
    STANDUP_SUMMARY = "standup_summary"


@dataclass
class RoutingRule:
    """Rule for routing notifications to channels."""
    notification_type: NotificationType
    default_channel: str
    urgency_overrides: Dict[NotificationUrgency, str] = field(default_factory=dict)
    content_filters: Dict[str, str] = field(default_factory=dict)  # filter_key -> channel
    team_overrides: Dict[str, str] = field(default_factory=dict)  # team_id -> channel
    enabled: bool = True


@dataclass
class ChannelConfig:
    """Configuration for a specific channel."""
    channel_id: str
    name: str
    description: str = ""
    max_messages_per_hour: int = 100
    allowed_urgencies: Set[NotificationUrgency] = field(default_factory=lambda: set(NotificationUrgency))
    allowed_types: Set[NotificationType] = field(default_factory=lambda: set(NotificationType))
    team_restrictions: Set[str] = field(default_factory=set)  # If set, only these teams can use
    active_hours: Optional[Tuple[int, int]] = None  # (start_hour, end_hour) in 24h format
    enabled: bool = True


@dataclass
class RoutingContext:
    """Context information for routing decisions."""
    notification_type: NotificationType
    urgency: NotificationUrgency
    team_id: str
    content_data: Dict[str, Any]
    author: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChannelRouter:
    """Intelligent channel routing system for notifications."""
    
    def __init__(self):
        """Initialize channel router with default routing rules."""
        self.logger = logging.getLogger(__name__)
        
        # Channel configurations
        self._channels: Dict[str, ChannelConfig] = {}
        
        # Routing rules
        self._routing_rules: Dict[NotificationType, RoutingRule] = {}
        
        # Fallback channel
        self._fallback_channel = "#general"
        
        # Team-specific channel mappings
        self._team_channels: Dict[str, Dict[str, str]] = {}  # team_id -> {type -> channel}
        
        # Channel usage statistics
        self._channel_stats: Dict[str, Dict[str, int]] = {}
        
        # Initialize default configuration
        self._setup_default_configuration()
        
        self.logger.info("ChannelRouter initialized with default configuration")
    
    def _setup_default_configuration(self) -> None:
        """Set up default channel configurations and routing rules."""
        
        # Default channel configurations
        default_channels = [
            ChannelConfig(
                channel_id="#development",
                name="Development",
                description="General development updates and PR notifications",
                max_messages_per_hour=50,
                allowed_types={NotificationType.PR_NEW, NotificationType.PR_MERGED, NotificationType.PR_CLOSED}
            ),
            ChannelConfig(
                channel_id="#project-updates",
                name="Project Updates",
                description="JIRA ticket updates and project management notifications",
                max_messages_per_hour=40,
                allowed_types={
                    NotificationType.JIRA_STATUS, NotificationType.JIRA_PRIORITY,
                    NotificationType.JIRA_ASSIGNMENT, NotificationType.JIRA_COMMENT,
                    NotificationType.JIRA_SPRINT
                }
            ),
            ChannelConfig(
                channel_id="#standup",
                name="Standup",
                description="Daily standup summaries and team updates",
                max_messages_per_hour=20,
                allowed_types={NotificationType.STANDUP_DAILY, NotificationType.STANDUP_SUMMARY}
            ),
            ChannelConfig(
                channel_id="#alerts",
                name="Alerts",
                description="General alerts and blocker notifications",
                max_messages_per_hour=30,
                allowed_types={NotificationType.JIRA_BLOCKER, NotificationType.ALERT_BUG}
            ),
            ChannelConfig(
                channel_id="#dev-alerts",
                name="Development Alerts",
                description="Development-specific alerts and urgent PR issues",
                max_messages_per_hour=25,
                allowed_urgencies={NotificationUrgency.HIGH, NotificationUrgency.CRITICAL},
                allowed_types={NotificationType.PR_CONFLICTS, NotificationType.ALERT_BUILD}
            ),
            ChannelConfig(
                channel_id="#code-review",
                name="Code Review",
                description="PR review requests and approvals",
                max_messages_per_hour=35,
                allowed_types={NotificationType.PR_READY, NotificationType.PR_APPROVED}
            ),
            ChannelConfig(
                channel_id="#project-alerts",
                name="Project Alerts",
                description="Critical project and JIRA alerts",
                max_messages_per_hour=20,
                allowed_urgencies={NotificationUrgency.HIGH, NotificationUrgency.CRITICAL},
                allowed_types={NotificationType.JIRA_BLOCKER}
            ),
            ChannelConfig(
                channel_id="#critical-alerts",
                name="Critical Alerts",
                description="Critical system alerts requiring immediate attention",
                max_messages_per_hour=15,
                allowed_urgencies={NotificationUrgency.CRITICAL},
                allowed_types={
                    NotificationType.ALERT_SECURITY, NotificationType.ALERT_OUTAGE,
                    NotificationType.ALERT_DEPLOYMENT
                }
            ),
            ChannelConfig(
                channel_id="#general",
                name="General",
                description="Fallback channel for all notifications",
                max_messages_per_hour=100
            )
        ]
        
        for channel in default_channels:
            self._channels[channel.channel_id] = channel
        
        # Default routing rules
        self._routing_rules = {
            # PR routing rules
            NotificationType.PR_NEW: RoutingRule(
                notification_type=NotificationType.PR_NEW,
                default_channel="#development"
            ),
            NotificationType.PR_READY: RoutingRule(
                notification_type=NotificationType.PR_READY,
                default_channel="#code-review"
            ),
            NotificationType.PR_APPROVED: RoutingRule(
                notification_type=NotificationType.PR_APPROVED,
                default_channel="#code-review"
            ),
            NotificationType.PR_CONFLICTS: RoutingRule(
                notification_type=NotificationType.PR_CONFLICTS,
                default_channel="#dev-alerts",
                urgency_overrides={
                    NotificationUrgency.CRITICAL: "#critical-alerts"
                }
            ),
            NotificationType.PR_MERGED: RoutingRule(
                notification_type=NotificationType.PR_MERGED,
                default_channel="#development"
            ),
            NotificationType.PR_CLOSED: RoutingRule(
                notification_type=NotificationType.PR_CLOSED,
                default_channel="#development"
            ),
            
            # JIRA routing rules
            NotificationType.JIRA_STATUS: RoutingRule(
                notification_type=NotificationType.JIRA_STATUS,
                default_channel="#project-updates"
            ),
            NotificationType.JIRA_PRIORITY: RoutingRule(
                notification_type=NotificationType.JIRA_PRIORITY,
                default_channel="#project-updates",
                urgency_overrides={
                    NotificationUrgency.CRITICAL: "#project-alerts"
                }
            ),
            NotificationType.JIRA_ASSIGNMENT: RoutingRule(
                notification_type=NotificationType.JIRA_ASSIGNMENT,
                default_channel="#project-updates"
            ),
            NotificationType.JIRA_COMMENT: RoutingRule(
                notification_type=NotificationType.JIRA_COMMENT,
                default_channel="#project-updates"
            ),
            NotificationType.JIRA_BLOCKER: RoutingRule(
                notification_type=NotificationType.JIRA_BLOCKER,
                default_channel="#project-alerts",
                urgency_overrides={
                    NotificationUrgency.CRITICAL: "#critical-alerts"
                }
            ),
            NotificationType.JIRA_SPRINT: RoutingRule(
                notification_type=NotificationType.JIRA_SPRINT,
                default_channel="#project-updates"
            ),
            
            # Alert routing rules
            NotificationType.ALERT_BUILD: RoutingRule(
                notification_type=NotificationType.ALERT_BUILD,
                default_channel="#dev-alerts",
                urgency_overrides={
                    NotificationUrgency.CRITICAL: "#critical-alerts"
                }
            ),
            NotificationType.ALERT_DEPLOYMENT: RoutingRule(
                notification_type=NotificationType.ALERT_DEPLOYMENT,
                default_channel="#critical-alerts"
            ),
            NotificationType.ALERT_SECURITY: RoutingRule(
                notification_type=NotificationType.ALERT_SECURITY,
                default_channel="#critical-alerts"
            ),
            NotificationType.ALERT_OUTAGE: RoutingRule(
                notification_type=NotificationType.ALERT_OUTAGE,
                default_channel="#critical-alerts"
            ),
            NotificationType.ALERT_BUG: RoutingRule(
                notification_type=NotificationType.ALERT_BUG,
                default_channel="#alerts",
                urgency_overrides={
                    NotificationUrgency.CRITICAL: "#critical-alerts"
                }
            ),
            
            # Standup routing rules
            NotificationType.STANDUP_DAILY: RoutingRule(
                notification_type=NotificationType.STANDUP_DAILY,
                default_channel="#standup"
            ),
            NotificationType.STANDUP_SUMMARY: RoutingRule(
                notification_type=NotificationType.STANDUP_SUMMARY,
                default_channel="#standup"
            )
        }
    
    def route_notification(self, context: RoutingContext, 
                          channel_override: Optional[str] = None) -> str:
        """Route notification to appropriate channel based on context."""
        
        # Use channel override if provided and valid
        if channel_override and self._is_valid_channel(channel_override, context):
            self._record_routing_decision(channel_override, context, "override")
            return channel_override
        
        # Check team-specific routing
        team_channel = self._get_team_specific_channel(context)
        if team_channel:
            self._record_routing_decision(team_channel, context, "team_specific")
            return team_channel
        
        # Apply routing rules
        routed_channel = self._apply_routing_rules(context)
        if routed_channel and self._is_valid_channel(routed_channel, context):
            self._record_routing_decision(routed_channel, context, "rule_based")
            return routed_channel
        
        # Fallback to default channel
        self._record_routing_decision(self._fallback_channel, context, "fallback")
        return self._fallback_channel
    
    def _apply_routing_rules(self, context: RoutingContext) -> Optional[str]:
        """Apply routing rules to determine target channel."""
        rule = self._routing_rules.get(context.notification_type)
        if not rule or not rule.enabled:
            return None
        
        # Check urgency overrides first
        if context.urgency in rule.urgency_overrides:
            return rule.urgency_overrides[context.urgency]
        
        # Check content filters
        for filter_key, channel in rule.content_filters.items():
            if self._matches_content_filter(context.content_data, filter_key):
                return channel
        
        # Return default channel for this notification type
        return rule.default_channel
    
    def _matches_content_filter(self, content_data: Dict[str, Any], filter_key: str) -> bool:
        """Check if content matches a specific filter."""
        # Example filters:
        # - "repository:critical-service" -> matches if repository contains "critical-service"
        # - "priority:high" -> matches if priority is high
        # - "label:security" -> matches if labels contain "security"
        
        if ":" not in filter_key:
            return False
        
        field, value = filter_key.split(":", 1)
        
        if field == "repository":
            repo = content_data.get("repository", "").lower()
            return value.lower() in repo
        
        elif field == "priority":
            priority = content_data.get("priority", "").lower()
            return priority == value.lower()
        
        elif field == "label":
            labels = content_data.get("labels", [])
            if isinstance(labels, list):
                return any(value.lower() in str(label).lower() for label in labels)
        
        elif field == "component":
            components = content_data.get("components", [])
            if isinstance(components, list):
                return any(value.lower() in str(comp).lower() for comp in components)
        
        elif field == "author":
            author = content_data.get("author", "").lower()
            return value.lower() in author
        
        return False
    
    def _get_team_specific_channel(self, context: RoutingContext) -> Optional[str]:
        """Get team-specific channel mapping if available."""
        team_mappings = self._team_channels.get(context.team_id)
        if not team_mappings:
            return None
        
        # Check for specific notification type mapping
        type_key = context.notification_type.value
        if type_key in team_mappings:
            return team_mappings[type_key]
        
        # Check for general category mappings
        category_mappings = {
            "pr": [nt for nt in NotificationType if nt.value.startswith("pr_")],
            "jira": [nt for nt in NotificationType if nt.value.startswith("jira_")],
            "alert": [nt for nt in NotificationType if nt.value.startswith("alert_")],
            "standup": [nt for nt in NotificationType if nt.value.startswith("standup_")]
        }
        
        for category, types in category_mappings.items():
            if context.notification_type in types and category in team_mappings:
                return team_mappings[category]
        
        return None
    
    def _is_valid_channel(self, channel: str, context: RoutingContext) -> bool:
        """Check if channel is valid for the given context."""
        channel_config = self._channels.get(channel)
        if not channel_config or not channel_config.enabled:
            return False
        
        # Check urgency restrictions
        if (channel_config.allowed_urgencies and 
            context.urgency not in channel_config.allowed_urgencies):
            return False
        
        # Check notification type restrictions
        if (channel_config.allowed_types and 
            context.notification_type not in channel_config.allowed_types):
            return False
        
        # Check team restrictions
        if (channel_config.team_restrictions and 
            context.team_id not in channel_config.team_restrictions):
            return False
        
        # Check active hours
        if channel_config.active_hours:
            current_hour = context.timestamp.hour
            start_hour, end_hour = channel_config.active_hours
            
            if start_hour <= end_hour:  # Same day
                if not (start_hour <= current_hour < end_hour):
                    return False
            else:  # Spans midnight
                if not (current_hour >= start_hour or current_hour < end_hour):
                    return False
        
        # Check rate limits
        if not self._check_channel_rate_limit(channel, context):
            return False
        
        return True
    
    def _check_channel_rate_limit(self, channel: str, context: RoutingContext) -> bool:
        """Check if channel has exceeded rate limits."""
        channel_config = self._channels.get(channel)
        if not channel_config:
            return True
        
        # Get current hour stats
        current_hour = context.timestamp.strftime("%Y-%m-%d-%H")
        channel_stats = self._channel_stats.setdefault(channel, {})
        current_count = channel_stats.get(current_hour, 0)
        
        return current_count < channel_config.max_messages_per_hour
    
    def _record_routing_decision(self, channel: str, context: RoutingContext, reason: str) -> None:
        """Record routing decision for analytics."""
        # Update channel usage statistics
        current_hour = context.timestamp.strftime("%Y-%m-%d-%H")
        channel_stats = self._channel_stats.setdefault(channel, {})
        channel_stats[current_hour] = channel_stats.get(current_hour, 0) + 1
        
        # Log routing decision
        self.logger.debug(
            f"Routed {context.notification_type.value} notification to {channel} "
            f"(reason: {reason}, urgency: {context.urgency.value}, team: {context.team_id})"
        )
    
    def analyze_urgency(self, message_data: Dict[str, Any], 
                       notification_type: NotificationType) -> NotificationUrgency:
        """Analyze notification content to determine urgency level."""
        
        # Critical urgency indicators
        critical_keywords = [
            "critical", "urgent", "emergency", "outage", "down", "security",
            "vulnerability", "breach", "failure", "error", "broken"
        ]
        
        # High urgency indicators
        high_keywords = [
            "blocker", "blocked", "conflict", "failed", "timeout", "issue",
            "problem", "alert", "warning"
        ]
        
        # Extract text content for analysis
        text_content = []
        
        # Add title/summary
        if "title" in message_data:
            text_content.append(str(message_data["title"]).lower())
        if "summary" in message_data:
            text_content.append(str(message_data["summary"]).lower())
        if "description" in message_data:
            text_content.append(str(message_data["description"]).lower())
        
        # Add labels/tags
        if "labels" in message_data:
            labels = message_data["labels"]
            if isinstance(labels, list):
                text_content.extend([str(label).lower() for label in labels])
        
        # Combine all text
        combined_text = " ".join(text_content)
        
        # Check for critical indicators
        if any(keyword in combined_text for keyword in critical_keywords):
            return NotificationUrgency.CRITICAL
        
        # Check for high urgency indicators
        if any(keyword in combined_text for keyword in high_keywords):
            return NotificationUrgency.HIGH
        
        # Type-specific urgency rules
        if notification_type in [NotificationType.ALERT_SECURITY, NotificationType.ALERT_OUTAGE]:
            return NotificationUrgency.CRITICAL
        
        if notification_type in [NotificationType.PR_CONFLICTS, NotificationType.JIRA_BLOCKER]:
            return NotificationUrgency.HIGH
        
        # Check priority field
        priority = message_data.get("priority", "").lower()
        if priority in ["critical", "blocker", "highest"]:
            return NotificationUrgency.CRITICAL
        elif priority in ["high", "major"]:
            return NotificationUrgency.HIGH
        elif priority in ["low", "minor", "trivial"]:
            return NotificationUrgency.LOW
        
        # Default to medium urgency
        return NotificationUrgency.MEDIUM
    
    def add_team_channel_mapping(self, team_id: str, mappings: Dict[str, str]) -> None:
        """Add team-specific channel mappings."""
        self._team_channels[team_id] = mappings
        self.logger.info(f"Added team channel mappings for {team_id}: {mappings}")
    
    def add_routing_rule(self, rule: RoutingRule) -> None:
        """Add or update a routing rule."""
        self._routing_rules[rule.notification_type] = rule
        self.logger.info(f"Added routing rule for {rule.notification_type.value}")
    
    def add_channel_config(self, config: ChannelConfig) -> None:
        """Add or update channel configuration."""
        self._channels[config.channel_id] = config
        self.logger.info(f"Added channel configuration for {config.channel_id}")
    
    def set_fallback_channel(self, channel: str) -> None:
        """Set the fallback channel for routing."""
        self._fallback_channel = channel
        self.logger.info(f"Set fallback channel to {channel}")
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics and analytics."""
        total_messages = sum(
            sum(hour_counts.values()) for hour_counts in self._channel_stats.values()
        )
        
        channel_usage = {}
        for channel, hour_counts in self._channel_stats.items():
            channel_total = sum(hour_counts.values())
            channel_usage[channel] = {
                "total_messages": channel_total,
                "percentage": (channel_total / total_messages * 100) if total_messages > 0 else 0,
                "recent_hours": dict(list(hour_counts.items())[-24:])  # Last 24 hours
            }
        
        return {
            "total_messages_routed": total_messages,
            "active_channels": len([c for c in self._channels.values() if c.enabled]),
            "total_channels": len(self._channels),
            "team_mappings": len(self._team_channels),
            "routing_rules": len(self._routing_rules),
            "channel_usage": channel_usage,
            "fallback_channel": self._fallback_channel
        }
    
    def cleanup_old_stats(self, hours_to_keep: int = 168) -> int:
        """Clean up old routing statistics (default: keep 1 week)."""
        cutoff_time = datetime.now() - timedelta(hours=hours_to_keep)
        cutoff_key = cutoff_time.strftime("%Y-%m-%d-%H")
        
        removed_count = 0
        for channel in self._channel_stats:
            keys_to_remove = [
                key for key in self._channel_stats[channel]
                if key < cutoff_key
            ]
            for key in keys_to_remove:
                del self._channel_stats[channel][key]
                removed_count += 1
        
        self.logger.info(f"Cleaned up {removed_count} old routing statistics")
        return removed_count


# Global router instance
default_channel_router = ChannelRouter()