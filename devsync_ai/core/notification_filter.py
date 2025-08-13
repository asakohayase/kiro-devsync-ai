"""Intelligent notification filtering system for DevSync AI."""

import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from ..models.core import PullRequest, JiraTicket, PRStatus, Severity


logger = logging.getLogger(__name__)


class UrgencyLevel(str, Enum):
    """Notification urgency levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RelevanceScore(str, Enum):
    """User relevance scoring."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DIRECT = "direct"


class FilterAction(str, Enum):
    """Filter actions."""
    ALLOW = "allow"
    BLOCK = "block"
    DOWNGRADE = "downgrade"
    BATCH = "batch"


@dataclass
class NotificationEvent:
    """Normalized notification event from various sources."""
    id: str
    source: str  # 'github', 'jira', 'manual'
    event_type: str  # 'pr_opened', 'issue_updated', etc.
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM
    content_hash: str = ""
    similarity_hash: str = ""


@dataclass
class FilterContext:
    """Context information for filtering decisions."""
    team_id: str
    channel_id: Optional[str] = None
    user_id: Optional[str] = None
    time_of_day: Optional[str] = None
    day_of_week: Optional[str] = None
    recent_activity: List[str] = field(default_factory=list)


@dataclass
class FilterDecision:
    """Result of filtering evaluation."""
    should_process: bool
    action: FilterAction
    reason: str
    confidence: float
    applied_rules: List[str] = field(default_factory=list)
    urgency_override: Optional[UrgencyLevel] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FilterRule:
    """Configurable filtering rule."""
    id: str
    name: str
    condition: Dict[str, Any]  # JSON-based rule condition
    action: FilterAction
    priority: int
    team_id: Optional[str] = None
    channel_id: Optional[str] = None
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class NotificationFilter:
    """Intelligent notification filtering system."""
    
    def __init__(self, config_manager=None):
        """Initialize notification filter."""
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Filter rules storage
        self._filter_rules: Dict[str, List[FilterRule]] = {}
        
        # Activity tracking for noise reduction
        self._recent_notifications: Dict[str, List[datetime]] = {}
        self._notification_frequency: Dict[str, int] = {}
        
        # Significant PR events that should always be processed
        self.significant_pr_events = {
            'pr_opened',
            'pr_merged', 
            'pr_closed',
            'pr_ready_for_review',
            'pr_conflicts_detected',
            'pr_approved',
            'pr_changes_requested'
        }
        
        # Important JIRA status transitions
        self.important_jira_transitions = {
            ('To Do', 'In Progress'),
            ('In Progress', 'Done'),
            ('In Progress', 'Blocked'),
            ('Blocked', 'In Progress'),
            ('Done', 'In Progress'),  # Reopened
            ('Open', 'In Progress'),
            ('In Review', 'Done'),
            ('Testing', 'Done'),
            ('Testing', 'Failed'),
        }
        
        # High priority JIRA priorities that should always notify
        self.high_priority_jira = {'High', 'Critical', 'Blocker'}
        
        # Load default filter rules
        self._load_default_rules()
        
        self.logger.info("NotificationFilter initialized")
    
    def _load_default_rules(self):
        """Load default filtering rules."""
        default_rules = [
            # Always allow blocker notifications
            FilterRule(
                id="allow_blockers",
                name="Always Allow Blocker Notifications",
                condition={"event_type": "blocker", "severity": ["high", "critical"]},
                action=FilterAction.ALLOW,
                priority=1000
            ),
            
            # Filter out draft PR updates unless significant
            FilterRule(
                id="filter_draft_prs",
                name="Filter Draft PR Minor Updates",
                condition={
                    "source": "github",
                    "event_type": ["pr_updated", "pr_synchronize"],
                    "pr_status": "draft"
                },
                action=FilterAction.BLOCK,
                priority=800
            ),
            
            # Filter out minor JIRA field updates
            FilterRule(
                id="filter_minor_jira_updates",
                name="Filter Minor JIRA Updates",
                condition={
                    "source": "jira",
                    "event_type": "issue_updated",
                    "changed_fields": ["description", "labels", "components", "fixVersions"]
                },
                action=FilterAction.DOWNGRADE,
                priority=700
            ),
            
            # Batch similar PR events
            FilterRule(
                id="batch_pr_updates",
                name="Batch Similar PR Updates",
                condition={
                    "source": "github",
                    "event_type": ["pr_updated", "pr_synchronize"],
                    "frequency": "high"
                },
                action=FilterAction.BATCH,
                priority=600
            )
        ]
        
        for rule in default_rules:
            team_key = rule.team_id or "default"
            if team_key not in self._filter_rules:
                self._filter_rules[team_key] = []
            self._filter_rules[team_key].append(rule)
    
    def should_process(self, event: NotificationEvent, context: FilterContext) -> FilterDecision:
        """Determine if notification should be processed."""
        try:
            # Always allow critical blockers
            if self._is_critical_blocker(event):
                return FilterDecision(
                    should_process=True,
                    action=FilterAction.ALLOW,
                    reason="Critical blocker notification",
                    confidence=1.0,
                    applied_rules=["critical_blocker_override"],
                    urgency_override=UrgencyLevel.CRITICAL
                )
            
            # Apply custom filter rules first (highest priority)
            rule_decision = self._apply_filter_rules(event, context)
            if rule_decision:
                return rule_decision
            
            # Check for noise patterns
            noise_decision = self._check_noise_patterns(event, context)
            if noise_decision.action == FilterAction.BLOCK:
                return noise_decision
            
            # Check PR filtering
            if event.source == "github":
                return self._filter_pr_notification(event, context)
            
            # Check JIRA filtering
            elif event.source == "jira":
                return self._filter_jira_notification(event, context)
            
            # Check user relevance
            relevance_decision = self._check_user_relevance(event, context)
            if relevance_decision.action == FilterAction.BLOCK:
                return relevance_decision
            
            # Default: allow with medium urgency
            return FilterDecision(
                should_process=True,
                action=FilterAction.ALLOW,
                reason="Default allow - no blocking rules matched",
                confidence=0.5,
                applied_rules=["default_allow"]
            )
            
        except Exception as e:
            self.logger.error(f"Error in should_process: {e}")
            # Fail open - allow notification if filtering fails
            return FilterDecision(
                should_process=True,
                action=FilterAction.ALLOW,
                reason=f"Filter error - failing open: {str(e)}",
                confidence=0.0,
                applied_rules=["error_fallback"]
            )
    
    def _is_critical_blocker(self, event: NotificationEvent) -> bool:
        """Check if event is a critical blocker that should always be processed."""
        if event.event_type == "blocker":
            severity = event.payload.get("severity", "").lower()
            return severity in ["critical", "high"]
        
        # Check for security alerts
        if "security" in event.event_type.lower():
            return True
        
        # Check for production incidents
        if any(keyword in event.event_type.lower() for keyword in ["incident", "outage", "down"]):
            return True
        
        return False
    
    def _filter_pr_notification(self, event: NotificationEvent, context: FilterContext) -> FilterDecision:
        """Filter PR notifications for significant changes only."""
        try:
            # Always allow significant PR events
            if event.event_type in self.significant_pr_events:
                urgency = self._evaluate_pr_urgency(event)
                return FilterDecision(
                    should_process=True,
                    action=FilterAction.ALLOW,
                    reason=f"Significant PR event: {event.event_type}",
                    confidence=0.9,
                    applied_rules=["significant_pr_events"],
                    urgency_override=urgency
                )
            
            # Check if PR is draft and event is minor
            pr_data = event.payload.get("pull_request", {})
            if pr_data.get("draft", False) and event.event_type in ["pr_updated", "pr_synchronize"]:
                return FilterDecision(
                    should_process=False,
                    action=FilterAction.BLOCK,
                    reason="Draft PR minor update filtered",
                    confidence=0.8,
                    applied_rules=["filter_draft_updates"]
                )
            
            # Check for merge conflicts
            if pr_data.get("mergeable", True) is False:
                return FilterDecision(
                    should_process=True,
                    action=FilterAction.ALLOW,
                    reason="PR has merge conflicts - important",
                    confidence=0.9,
                    applied_rules=["pr_conflicts"],
                    urgency_override=UrgencyLevel.HIGH
                )
            
            # Check user involvement
            relevance = self._check_pr_user_relevance(event, context)
            if relevance == RelevanceScore.DIRECT:
                return FilterDecision(
                    should_process=True,
                    action=FilterAction.ALLOW,
                    reason="User directly involved in PR",
                    confidence=0.9,
                    applied_rules=["pr_user_relevance"]
                )
            elif relevance == RelevanceScore.NONE:
                return FilterDecision(
                    should_process=False,
                    action=FilterAction.BLOCK,
                    reason="User not involved in PR",
                    confidence=0.7,
                    applied_rules=["pr_user_irrelevance"]
                )
            
            # Default for PR events
            return FilterDecision(
                should_process=True,
                action=FilterAction.ALLOW,
                reason="PR event allowed by default",
                confidence=0.6,
                applied_rules=["pr_default_allow"]
            )
            
        except Exception as e:
            self.logger.error(f"Error filtering PR notification: {e}")
            return FilterDecision(
                should_process=True,
                action=FilterAction.ALLOW,
                reason=f"PR filter error - failing open: {str(e)}",
                confidence=0.0,
                applied_rules=["pr_filter_error"]
            )
    
    def _filter_jira_notification(self, event: NotificationEvent, context: FilterContext) -> FilterDecision:
        """Filter JIRA notifications for important status transitions."""
        try:
            issue_data = event.payload.get("issue", {})
            
            # Always allow high priority tickets
            priority = issue_data.get("fields", {}).get("priority", {}).get("name", "")
            if priority in self.high_priority_jira:
                return FilterDecision(
                    should_process=True,
                    action=FilterAction.ALLOW,
                    reason=f"High priority JIRA ticket: {priority}",
                    confidence=0.9,
                    applied_rules=["jira_high_priority"],
                    urgency_override=UrgencyLevel.HIGH
                )
            
            # Check for important status transitions
            if event.event_type == "issue_updated":
                changelog = event.payload.get("changelog", {})
                if self._is_important_jira_transition(changelog):
                    return FilterDecision(
                        should_process=True,
                        action=FilterAction.ALLOW,
                        reason="Important JIRA status transition",
                        confidence=0.8,
                        applied_rules=["jira_important_transition"]
                    )
            
            # Check if user is assignee or reporter
            relevance = self._check_jira_user_relevance(event, context)
            if relevance == RelevanceScore.DIRECT:
                return FilterDecision(
                    should_process=True,
                    action=FilterAction.ALLOW,
                    reason="User directly involved in JIRA ticket",
                    confidence=0.8,
                    applied_rules=["jira_user_relevance"]
                )
            
            # Filter out minor field updates
            if self._is_minor_jira_update(event):
                return FilterDecision(
                    should_process=False,
                    action=FilterAction.BLOCK,
                    reason="Minor JIRA field update filtered",
                    confidence=0.7,
                    applied_rules=["jira_minor_update_filter"]
                )
            
            # Default for JIRA events
            return FilterDecision(
                should_process=True,
                action=FilterAction.ALLOW,
                reason="JIRA event allowed by default",
                confidence=0.5,
                applied_rules=["jira_default_allow"]
            )
            
        except Exception as e:
            self.logger.error(f"Error filtering JIRA notification: {e}")
            return FilterDecision(
                should_process=True,
                action=FilterAction.ALLOW,
                reason=f"JIRA filter error - failing open: {str(e)}",
                confidence=0.0,
                applied_rules=["jira_filter_error"]
            )
    
    def _evaluate_pr_urgency(self, event: NotificationEvent) -> UrgencyLevel:
        """Evaluate urgency level for PR events."""
        pr_data = event.payload.get("pull_request", {})
        
        # Critical: Security fixes, hotfixes
        if any(keyword in pr_data.get("title", "").lower() 
               for keyword in ["security", "hotfix", "critical", "urgent"]):
            return UrgencyLevel.CRITICAL
        
        # High: Merge conflicts, ready for review
        if (pr_data.get("mergeable", True) is False or 
            event.event_type == "pr_ready_for_review"):
            return UrgencyLevel.HIGH
        
        # Medium: Most other PR events
        return UrgencyLevel.MEDIUM
    
    def _check_pr_user_relevance(self, event: NotificationEvent, context: FilterContext) -> RelevanceScore:
        """Check user relevance for PR notifications."""
        if not context.user_id:
            return RelevanceScore.MEDIUM
        
        pr_data = event.payload.get("pull_request", {})
        
        # Direct involvement
        if (pr_data.get("user", {}).get("login") == context.user_id or
            context.user_id in pr_data.get("requested_reviewers", []) or
            context.user_id in [r.get("login") for r in pr_data.get("assignees", [])]):
            return RelevanceScore.DIRECT
        
        # Team involvement (if we have team data)
        # This would need team membership data to implement fully
        
        return RelevanceScore.LOW
    
    def _is_important_jira_transition(self, changelog: Dict[str, Any]) -> bool:
        """Check if JIRA changelog contains important status transitions."""
        items = changelog.get("items", [])
        
        for item in items:
            if item.get("field") == "status":
                from_status = item.get("fromString", "")
                to_status = item.get("toString", "")
                
                if (from_status, to_status) in self.important_jira_transitions:
                    return True
        
        return False
    
    def _check_jira_user_relevance(self, event: NotificationEvent, context: FilterContext) -> RelevanceScore:
        """Check user relevance for JIRA notifications."""
        if not context.user_id:
            return RelevanceScore.MEDIUM
        
        issue_data = event.payload.get("issue", {}).get("fields", {})
        
        # Direct involvement
        assignee = issue_data.get("assignee", {})
        reporter = issue_data.get("reporter", {})
        
        if (assignee.get("name") == context.user_id or
            assignee.get("emailAddress") == context.user_id or
            reporter.get("name") == context.user_id or
            reporter.get("emailAddress") == context.user_id):
            return RelevanceScore.DIRECT
        
        return RelevanceScore.LOW
    
    def _is_minor_jira_update(self, event: NotificationEvent) -> bool:
        """Check if JIRA update is minor (description, labels, etc.)."""
        if event.event_type != "issue_updated":
            return False
        
        changelog = event.payload.get("changelog", {})
        items = changelog.get("items", [])
        
        if not items:
            return False
        
        minor_fields = {"description", "labels", "components", "fixVersions", "comment"}
        
        # If only minor fields were changed, consider it minor
        changed_fields = {item.get("field") for item in items}
        return len(changed_fields) > 0 and changed_fields.issubset(minor_fields)
    
    def _check_noise_patterns(self, event: NotificationEvent, context: FilterContext) -> FilterDecision:
        """Check for known noise patterns."""
        # Check notification frequency
        event_key = f"{event.source}:{event.event_type}"
        now = datetime.now()
        
        # Track recent notifications
        if event_key not in self._recent_notifications:
            self._recent_notifications[event_key] = []
        
        # Clean old notifications (older than 1 hour)
        self._recent_notifications[event_key] = [
            ts for ts in self._recent_notifications[event_key]
            if now - ts < timedelta(hours=1)
        ]
        
        # Add current notification
        self._recent_notifications[event_key].append(now)
        
        # Check if too frequent (more than 10 in last hour)
        if len(self._recent_notifications[event_key]) > 10:
            return FilterDecision(
                should_process=False,
                action=FilterAction.BLOCK,
                reason=f"High frequency noise pattern detected: {event_key}",
                confidence=0.8,
                applied_rules=["noise_frequency_filter"]
            )
        
        # Check for bot activity patterns
        if self._is_bot_activity(event):
            return FilterDecision(
                should_process=True,  # Changed to True but downgraded
                action=FilterAction.DOWNGRADE,
                reason="Bot activity detected",
                confidence=0.7,
                applied_rules=["bot_activity_filter"]
            )
        
        return FilterDecision(
            should_process=True,
            action=FilterAction.ALLOW,
            reason="No noise patterns detected",
            confidence=0.6,
            applied_rules=["noise_check_passed"]
        )
    
    def _is_bot_activity(self, event: NotificationEvent) -> bool:
        """Check if event is from bot activity."""
        # Check for common bot usernames
        bot_indicators = ["bot", "automated", "dependabot", "renovate", "github-actions"]
        
        if event.source == "github":
            pr_data = event.payload.get("pull_request", {})
            author = pr_data.get("user", {}).get("login", "").lower()
            return any(indicator in author for indicator in bot_indicators)
        
        elif event.source == "jira":
            issue_data = event.payload.get("issue", {}).get("fields", {})
            reporter = issue_data.get("reporter", {}).get("name", "").lower()
            return any(indicator in reporter for indicator in bot_indicators)
        
        return False
    
    def _check_user_relevance(self, event: NotificationEvent, context: FilterContext) -> FilterDecision:
        """Check overall user relevance for the notification."""
        if not context.user_id:
            return FilterDecision(
                should_process=True,
                action=FilterAction.ALLOW,
                reason="No user context - allowing",
                confidence=0.5,
                applied_rules=["no_user_context"]
            )
        
        # This is a placeholder for more sophisticated relevance checking
        # In a full implementation, this would check:
        # - Team membership
        # - Project involvement
        # - Historical interaction patterns
        # - Subscription preferences
        
        return FilterDecision(
            should_process=True,
            action=FilterAction.ALLOW,
            reason="User relevance check passed",
            confidence=0.6,
            applied_rules=["user_relevance_check"]
        )
    
    def _apply_filter_rules(self, event: NotificationEvent, context: FilterContext) -> Optional[FilterDecision]:
        """Apply custom filter rules."""
        team_key = context.team_id
        rules = self._filter_rules.get(team_key, []) + self._filter_rules.get("default", [])
        
        # Sort rules by priority (higher priority first)
        rules.sort(key=lambda r: r.priority, reverse=True)
        
        for rule in rules:
            if not rule.active:
                continue
            
            if self._rule_matches(rule, event, context):
                should_process = rule.action != FilterAction.BLOCK
                return FilterDecision(
                    should_process=should_process,
                    action=rule.action,
                    reason=f"Matched rule: {rule.name}",
                    confidence=0.9,
                    applied_rules=[rule.id]
                )
        
        return None
    
    def _rule_matches(self, rule: FilterRule, event: NotificationEvent, context: FilterContext) -> bool:
        """Check if a filter rule matches the current event."""
        condition = rule.condition
        
        # Check source
        if "source" in condition:
            if event.source not in self._ensure_list(condition["source"]):
                return False
        
        # Check event type
        if "event_type" in condition:
            if event.event_type not in self._ensure_list(condition["event_type"]):
                return False
        
        # Check channel
        if "channel_id" in condition and context.channel_id:
            if context.channel_id not in self._ensure_list(condition["channel_id"]):
                return False
        
        # Check PR status
        if "pr_status" in condition and event.source == "github":
            pr_data = event.payload.get("pull_request", {})
            pr_draft = pr_data.get("draft", False)
            if condition["pr_status"] == "draft" and not pr_draft:
                return False
        
        # Check changed fields for JIRA
        if "changed_fields" in condition and event.source == "jira":
            changelog = event.payload.get("changelog", {})
            items = changelog.get("items", [])
            changed_fields = {item.get("field") for item in items}
            required_fields = set(self._ensure_list(condition["changed_fields"]))
            if not changed_fields.intersection(required_fields):
                return False
        
        return True
    
    def _ensure_list(self, value) -> List[str]:
        """Ensure value is a list."""
        if isinstance(value, str):
            return [value]
        elif isinstance(value, list):
            return value
        else:
            return [str(value)]
    
    def apply_noise_reduction(self, event: NotificationEvent) -> bool:
        """Apply noise reduction algorithms."""
        # Check for minimum activity threshold for daily summaries
        if event.event_type == "daily_summary":
            activity_count = event.payload.get("activity_count", 0)
            min_threshold = 5  # Configurable minimum activity threshold
            
            if activity_count < min_threshold:
                self.logger.info(f"Daily summary filtered: activity count {activity_count} below threshold {min_threshold}")
                return False
        
        return True
    
    def check_user_relevance(self, event: NotificationEvent, user: str) -> RelevanceScore:
        """Check user relevance for a notification."""
        context = FilterContext(team_id="default", user_id=user)
        
        if event.source == "github":
            return self._check_pr_user_relevance(event, context)
        elif event.source == "jira":
            return self._check_jira_user_relevance(event, context)
        
        return RelevanceScore.MEDIUM
    
    def evaluate_urgency(self, event: NotificationEvent) -> UrgencyLevel:
        """Evaluate urgency level of a notification."""
        if self._is_critical_blocker(event):
            return UrgencyLevel.CRITICAL
        
        if event.source == "github":
            return self._evaluate_pr_urgency(event)
        
        elif event.source == "jira":
            issue_data = event.payload.get("issue", {})
            priority = issue_data.get("fields", {}).get("priority", {}).get("name", "")
            
            if priority in ["Critical", "Blocker"]:
                return UrgencyLevel.CRITICAL
            elif priority == "High":
                return UrgencyLevel.HIGH
            elif priority == "Medium":
                return UrgencyLevel.MEDIUM
            else:
                return UrgencyLevel.LOW
        
        return UrgencyLevel.MEDIUM
    
    def get_filter_rules(self, team_id: str, channel_id: Optional[str] = None) -> List[FilterRule]:
        """Get filter rules for a team and optionally a channel."""
        rules = self._filter_rules.get(team_id, []).copy()
        
        # Add default rules
        rules.extend(self._filter_rules.get("default", []))
        
        # Filter by channel if specified
        if channel_id:
            rules = [r for r in rules if not r.channel_id or r.channel_id == channel_id]
        
        return sorted(rules, key=lambda r: r.priority, reverse=True)
    
    def add_filter_rule(self, rule: FilterRule) -> None:
        """Add a new filter rule."""
        team_key = rule.team_id or "default"
        
        if team_key not in self._filter_rules:
            self._filter_rules[team_key] = []
        
        self._filter_rules[team_key].append(rule)
        self.logger.info(f"Added filter rule: {rule.name} for team {team_key}")
    
    def remove_filter_rule(self, rule_id: str, team_id: Optional[str] = None) -> bool:
        """Remove a filter rule."""
        team_key = team_id or "default"
        
        if team_key in self._filter_rules:
            original_count = len(self._filter_rules[team_key])
            self._filter_rules[team_key] = [r for r in self._filter_rules[team_key] if r.id != rule_id]
            
            if len(self._filter_rules[team_key]) < original_count:
                self.logger.info(f"Removed filter rule: {rule_id} from team {team_key}")
                return True
        
        return False
    
    def get_filtering_stats(self) -> Dict[str, Any]:
        """Get filtering statistics for analytics."""
        return {
            "total_rules": sum(len(rules) for rules in self._filter_rules.values()),
            "rules_by_team": {team: len(rules) for team, rules in self._filter_rules.items()},
            "recent_activity": dict(self._notification_frequency),
            "noise_patterns_detected": len([
                key for key, notifications in self._recent_notifications.items()
                if len(notifications) > 5
            ])
        }
    
    def log_filtering_decision(self, event: NotificationEvent, decision: FilterDecision, context: FilterContext) -> None:
        """Log filtering decision for analytics."""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event_id": event.id,
            "event_type": event.event_type,
            "source": event.source,
            "team_id": context.team_id,
            "channel_id": context.channel_id,
            "user_id": context.user_id,
            "decision": decision.action.value,
            "should_process": decision.should_process,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "applied_rules": decision.applied_rules,
            "urgency": decision.urgency_override.value if decision.urgency_override else None
        }
        
        # Log at appropriate level based on decision
        if decision.action == FilterAction.BLOCK:
            self.logger.info(f"Notification filtered: {json.dumps(log_data)}")
        elif decision.action == FilterAction.ALLOW:
            self.logger.debug(f"Notification allowed: {json.dumps(log_data)}")
        else:
            self.logger.info(f"Notification processed: {json.dumps(log_data)}")