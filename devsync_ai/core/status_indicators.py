"""Status indicator system for Slack messages with emojis and colors."""

from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass


class StatusType(Enum):
    """Status types for different notification contexts."""
    SUCCESS = "success"
    WARNING = "warning" 
    ERROR = "error"
    INFO = "info"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    BLOCKED = "blocked"


class PRStatus(Enum):
    """PR status types with specific indicators."""
    DRAFT = "draft"
    OPEN = "open"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    MERGED = "merged"
    CLOSED = "closed"
    CONFLICTS = "conflicts"


class JIRAStatus(Enum):
    """JIRA ticket status types."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class Priority(Enum):
    """Priority levels for tickets and issues."""
    LOWEST = "lowest"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HIGHEST = "highest"
    BLOCKER = "blocker"


class HealthStatus(Enum):
    """Health status indicators."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class UrgencyLevel(Enum):
    """Urgency levels for prioritization."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class StatusIndicator:
    """Status indicator with emoji, color, and text."""
    emoji: str
    color: str
    text: str
    description: Optional[str] = None


class StatusIndicatorSystem:
    """Centralized system for managing status indicators."""
    
    # Default emoji mappings
    DEFAULT_EMOJIS = {
        StatusType.SUCCESS: "✅",
        StatusType.WARNING: "⚠️", 
        StatusType.ERROR: "❌",
        StatusType.INFO: "ℹ️",
        StatusType.IN_PROGRESS: "⏳",
        StatusType.PENDING: "⏸️",
        StatusType.BLOCKED: "🚫"
    }
    
    # PR Status Indicators
    PR_STATUS_EMOJIS = {
        PRStatus.DRAFT: "📝",
        PRStatus.OPEN: "🔄",
        PRStatus.READY_FOR_REVIEW: "👀",
        PRStatus.APPROVED: "✅",
        PRStatus.CHANGES_REQUESTED: "❌",
        PRStatus.MERGED: "🎉",
        PRStatus.CLOSED: "⛔",
        PRStatus.CONFLICTS: "⚠️"
    }
    
    PR_STATUS_COLORS = {
        PRStatus.DRAFT: "#808080",      # Gray
        PRStatus.OPEN: "#439fe0",       # Blue
        PRStatus.READY_FOR_REVIEW: "#ffcc00",  # Yellow
        PRStatus.APPROVED: "#36a64f",   # Green
        PRStatus.CHANGES_REQUESTED: "#ff0000",  # Red
        PRStatus.MERGED: "#800080",     # Purple
        PRStatus.CLOSED: "#808080",     # Gray
        PRStatus.CONFLICTS: "#ff9500"   # Orange
    }
    
    # JIRA Status Indicators
    JIRA_STATUS_EMOJIS = {
        JIRAStatus.TODO: "📋",
        JIRAStatus.IN_PROGRESS: "🔄",
        JIRAStatus.IN_REVIEW: "👀",
        JIRAStatus.DONE: "✅",
        JIRAStatus.BLOCKED: "🚫",
        JIRAStatus.CANCELLED: "⛔"
    }
    
    JIRA_STATUS_COLORS = {
        JIRAStatus.TODO: "#808080",         # Gray
        JIRAStatus.IN_PROGRESS: "#439fe0",  # Blue
        JIRAStatus.IN_REVIEW: "#ffcc00",    # Yellow
        JIRAStatus.DONE: "#36a64f",         # Green
        JIRAStatus.BLOCKED: "#ff0000",      # Red
        JIRAStatus.CANCELLED: "#808080"     # Gray
    }
    
    # Priority Indicators
    PRIORITY_EMOJIS = {
        Priority.LOWEST: "⬇️",
        Priority.LOW: "🔽",
        Priority.MEDIUM: "➡️",
        Priority.HIGH: "🔺",
        Priority.HIGHEST: "⚠️",
        Priority.BLOCKER: "🚨"
    }
    
    PRIORITY_COLORS = {
        Priority.LOWEST: "#808080",     # Gray
        Priority.LOW: "#439fe0",        # Blue
        Priority.MEDIUM: "#ffcc00",     # Yellow
        Priority.HIGH: "#ff9500",       # Orange
        Priority.HIGHEST: "#ff0000",    # Red
        Priority.BLOCKER: "#ff0000"     # Red (flashing effect in UI)
    }
    
    # Health Indicators
    HEALTH_EMOJIS = {
        HealthStatus.HEALTHY: "💚",
        HealthStatus.WARNING: "💛",
        HealthStatus.CRITICAL: "❤️",
        HealthStatus.UNKNOWN: "🤍"
    }
    
    HEALTH_COLORS = {
        HealthStatus.HEALTHY: "#36a64f",    # Green
        HealthStatus.WARNING: "#ffcc00",    # Yellow
        HealthStatus.CRITICAL: "#ff0000",   # Red
        HealthStatus.UNKNOWN: "#808080"     # Gray
    }
    
    # Default color schemes (Slack attachment colors)
    DEFAULT_COLORS = {
        StatusType.SUCCESS: "#36a64f",  # Green
        StatusType.WARNING: "#ff9500",  # Orange
        StatusType.ERROR: "#ff0000",    # Red
        StatusType.INFO: "#439fe0",     # Blue
        StatusType.IN_PROGRESS: "#ffcc00",  # Yellow
        StatusType.PENDING: "#808080",  # Gray
        StatusType.BLOCKED: "#800080"   # Purple
    }
    
    # Urgency level indicators
    URGENCY_EMOJIS = {
        UrgencyLevel.LOW: "🟢",
        UrgencyLevel.MEDIUM: "🟡", 
        UrgencyLevel.HIGH: "🔴",
        UrgencyLevel.CRITICAL: "🚨"
    }
    
    URGENCY_COLORS = {
        UrgencyLevel.LOW: "#36a64f",
        UrgencyLevel.MEDIUM: "#ffcc00",
        UrgencyLevel.HIGH: "#ff9500", 
        UrgencyLevel.CRITICAL: "#ff0000"
    }
    
    # Accessibility text alternatives
    ACCESSIBILITY_TEXT = {
        # PR Status
        PRStatus.DRAFT: "Draft PR",
        PRStatus.OPEN: "Open PR",
        PRStatus.READY_FOR_REVIEW: "Ready for Review",
        PRStatus.APPROVED: "Approved PR",
        PRStatus.CHANGES_REQUESTED: "Changes Requested",
        PRStatus.MERGED: "Merged PR",
        PRStatus.CLOSED: "Closed PR",
        PRStatus.CONFLICTS: "PR has Conflicts",
        
        # JIRA Status
        JIRAStatus.TODO: "To Do",
        JIRAStatus.IN_PROGRESS: "In Progress",
        JIRAStatus.IN_REVIEW: "In Review",
        JIRAStatus.DONE: "Done",
        JIRAStatus.BLOCKED: "Blocked",
        JIRAStatus.CANCELLED: "Cancelled",
        
        # Priority
        Priority.LOWEST: "Lowest Priority",
        Priority.LOW: "Low Priority",
        Priority.MEDIUM: "Medium Priority",
        Priority.HIGH: "High Priority",
        Priority.HIGHEST: "Highest Priority",
        Priority.BLOCKER: "Blocker Priority",
        
        # Health
        HealthStatus.HEALTHY: "Healthy Status",
        HealthStatus.WARNING: "Warning Status",
        HealthStatus.CRITICAL: "Critical Status",
        HealthStatus.UNKNOWN: "Unknown Status"
    }
    
    def __init__(self, custom_emojis: Optional[Dict] = None, custom_colors: Optional[Dict] = None):
        """Initialize with optional custom emoji and color mappings."""
        self.emojis = {**self.DEFAULT_EMOJIS, **(custom_emojis or {})}
        self.colors = {**self.DEFAULT_COLORS, **(custom_colors or {})}
        
        # Allow team-specific customization of specialized indicators
        self.pr_emojis = {**self.PR_STATUS_EMOJIS, **(custom_emojis or {}).get('pr', {})}
        self.pr_colors = {**self.PR_STATUS_COLORS, **(custom_colors or {}).get('pr', {})}
        
        self.jira_emojis = {**self.JIRA_STATUS_EMOJIS, **(custom_emojis or {}).get('jira', {})}
        self.jira_colors = {**self.JIRA_STATUS_COLORS, **(custom_colors or {}).get('jira', {})}
        
        self.priority_emojis = {**self.PRIORITY_EMOJIS, **(custom_emojis or {}).get('priority', {})}
        self.priority_colors = {**self.PRIORITY_COLORS, **(custom_colors or {}).get('priority', {})}
        
        self.health_emojis = {**self.HEALTH_EMOJIS, **(custom_emojis or {}).get('health', {})}
        self.health_colors = {**self.HEALTH_COLORS, **(custom_colors or {}).get('health', {})}
    
    def get_status_indicator(self, status: StatusType, text: str = "") -> StatusIndicator:
        """Get status indicator for a given status type."""
        return StatusIndicator(
            emoji=self.emojis.get(status, "⚪"),
            color=self.colors.get(status, "#808080"),
            text=text or status.value.replace("_", " ").title(),
            description=f"{status.value} status indicator"
        )
    
    def get_pr_status_indicator(self, status: PRStatus, text: str = "") -> StatusIndicator:
        """Get PR status indicator with specific styling."""
        return StatusIndicator(
            emoji=self.pr_emojis.get(status, "⚪"),
            color=self.pr_colors.get(status, "#808080"),
            text=text or self.ACCESSIBILITY_TEXT.get(status, status.value.replace("_", " ").title()),
            description=f"PR {status.value.replace('_', ' ')} status"
        )
    
    def get_jira_status_indicator(self, status: JIRAStatus, text: str = "") -> StatusIndicator:
        """Get JIRA status indicator with specific styling."""
        return StatusIndicator(
            emoji=self.jira_emojis.get(status, "⚪"),
            color=self.jira_colors.get(status, "#808080"),
            text=text or self.ACCESSIBILITY_TEXT.get(status, status.value.replace("_", " ").title()),
            description=f"JIRA {status.value.replace('_', ' ')} status"
        )
    
    def get_priority_indicator(self, priority: Priority, text: str = "") -> StatusIndicator:
        """Get priority indicator with urgency styling."""
        return StatusIndicator(
            emoji=self.priority_emojis.get(priority, "⚪"),
            color=self.priority_colors.get(priority, "#808080"),
            text=text or self.ACCESSIBILITY_TEXT.get(priority, priority.value.title()),
            description=f"{priority.value} priority level"
        )
    
    def get_health_status_indicator(self, health: HealthStatus, text: str = "") -> StatusIndicator:
        """Get health status indicator."""
        return StatusIndicator(
            emoji=self.health_emojis.get(health, "🤍"),
            color=self.health_colors.get(health, "#808080"),
            text=text or self.ACCESSIBILITY_TEXT.get(health, health.value.title()),
            description=f"{health.value} health status"
        )
    
    def get_urgency_indicator(self, urgency: UrgencyLevel, text: str = "") -> StatusIndicator:
        """Get urgency indicator for a given urgency level."""
        return StatusIndicator(
            emoji=self.URGENCY_EMOJIS.get(urgency, "⚪"),
            color=self.URGENCY_COLORS.get(urgency, "#808080"),
            text=text or urgency.value.title(),
            description=f"{urgency.value} urgency level"
        )
    
    def get_indicator_by_string(self, status_string: str, context: str = "general") -> StatusIndicator:
        """Get indicator by string value with context for fallback handling."""
        status_lower = status_string.lower().replace(" ", "_").replace("-", "_")
        
        # Try to match against different status types based on context
        if context == "pr":
            for pr_status in PRStatus:
                if pr_status.value == status_lower:
                    return self.get_pr_status_indicator(pr_status)
        elif context == "jira":
            for jira_status in JIRAStatus:
                if jira_status.value == status_lower:
                    return self.get_jira_status_indicator(jira_status)
        elif context == "priority":
            for priority in Priority:
                if priority.value == status_lower:
                    return self.get_priority_indicator(priority)
        elif context == "health":
            for health in HealthStatus:
                if health.value == status_lower:
                    return self.get_health_status_indicator(health)
        
        # Fallback to general status types
        for status_type in StatusType:
            if status_type.value == status_lower:
                return self.get_status_indicator(status_type)
        
        # Ultimate fallback for unknown statuses
        return StatusIndicator(
            emoji="⚪",
            color="#808080",
            text=status_string.title(),
            description=f"Unknown status: {status_string}"
        )
    
    def create_progress_indicator(self, completed: int, total: int) -> StatusIndicator:
        """Create a progress indicator with percentage and visual bar."""
        if total == 0:
            percentage = 0
        else:
            percentage = int((completed / total) * 100)
        
        # Create visual progress bar
        filled_blocks = int(percentage / 10)
        empty_blocks = 10 - filled_blocks
        progress_bar = "█" * filled_blocks + "░" * empty_blocks
        
        # Determine color based on progress
        if percentage >= 80:
            color = self.DEFAULT_COLORS[StatusType.SUCCESS]
            emoji = "🟢"
        elif percentage >= 50:
            color = self.DEFAULT_COLORS[StatusType.IN_PROGRESS] 
            emoji = "🟡"
        else:
            color = self.DEFAULT_COLORS[StatusType.WARNING]
            emoji = "🔴"
        
        return StatusIndicator(
            emoji=emoji,
            color=color,
            text=f"{percentage}% ({completed}/{total})",
            description=f"Progress: {progress_bar} {percentage}%"
        )
    
    def get_health_indicator(self, health_score: float) -> StatusIndicator:
        """Get team health indicator based on score (0.0 to 1.0)."""
        if health_score >= 0.8:
            return StatusIndicator("🟢", "#36a64f", "Healthy", "Team health is good")
        elif health_score >= 0.6:
            return StatusIndicator("🟡", "#ffcc00", "Fair", "Team health needs attention")
        elif health_score >= 0.4:
            return StatusIndicator("🟠", "#ff9500", "Poor", "Team health is concerning")
        else:
            return StatusIndicator("🔴", "#ff0000", "Critical", "Team health is critical")


# Global default instance
default_status_system = StatusIndicatorSystem()