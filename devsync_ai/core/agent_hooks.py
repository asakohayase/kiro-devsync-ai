"""
Core Agent Hook infrastructure for JIRA-Slack automation.

This module provides the base classes and interfaces for implementing
Agent Hooks that respond to JIRA webhook events and trigger intelligent
Slack notifications.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid


class EventCategory(Enum):
    """Categories for JIRA event classification."""
    STATUS_CHANGE = "status_change"
    ASSIGNMENT = "assignment"
    COMMENT = "comment"
    PRIORITY_CHANGE = "priority_change"
    BLOCKER = "blocker"
    CREATION = "creation"
    TRANSITION = "transition"


class UrgencyLevel(Enum):
    """Urgency levels for event processing."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SignificanceLevel(Enum):
    """Significance levels for event impact assessment."""
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


class HookStatus(Enum):
    """Status of hook execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class Stakeholder:
    """Represents a stakeholder affected by a JIRA event."""
    user_id: str
    display_name: str
    email: Optional[str] = None
    role: Optional[str] = None
    team_id: Optional[str] = None
    slack_user_id: Optional[str] = None


@dataclass
class ProcessedEvent:
    """Represents a processed JIRA webhook event."""
    event_id: str
    event_type: str
    timestamp: datetime
    jira_event_data: Dict[str, Any]
    ticket_key: str
    project_key: str
    raw_payload: Dict[str, Any]
    
    def __post_init__(self):
        """Ensure event_id is set."""
        if not self.event_id:
            self.event_id = str(uuid.uuid4())


@dataclass
class EventClassification:
    """Classification result for a JIRA event."""
    category: EventCategory
    urgency: UrgencyLevel
    significance: SignificanceLevel
    affected_teams: List[str] = field(default_factory=list)
    routing_hints: Dict[str, Any] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)


@dataclass
class EnrichedEvent(ProcessedEvent):
    """Enhanced event with additional context and classification."""
    ticket_details: Optional[Dict[str, Any]] = None
    stakeholders: List[Stakeholder] = field(default_factory=list)
    classification: Optional[EventClassification] = None
    context_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HookExecutionResult:
    """Result of a hook execution."""
    hook_id: str
    execution_id: str
    hook_type: str
    event_id: str
    status: HookStatus
    execution_time_ms: float
    notification_sent: bool = False
    notification_result: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Ensure execution_id is set."""
        if not self.execution_id:
            self.execution_id = str(uuid.uuid4())
    
    def mark_completed(self, status: HookStatus = HookStatus.SUCCESS):
        """Mark the execution as completed."""
        self.status = status
        self.completed_at = datetime.now(timezone.utc)
    
    def add_error(self, error: str):
        """Add an error to the execution result."""
        self.errors.append(error)
        if self.status not in [HookStatus.FAILED, HookStatus.CANCELLED]:
            self.status = HookStatus.FAILED


@dataclass
class HookConfiguration:
    """Configuration for an Agent Hook."""
    hook_id: str
    hook_type: str
    team_id: str
    enabled: bool = True
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    notification_channels: List[str] = field(default_factory=list)
    rate_limit_per_hour: int = 100
    retry_attempts: int = 3
    timeout_seconds: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentHook(ABC):
    """
    Abstract base class for all Agent Hooks.
    
    Agent Hooks are event-driven automation components that respond to
    JIRA webhook events and trigger appropriate actions, typically
    Slack notifications.
    """
    
    def __init__(self, hook_id: str, configuration: HookConfiguration):
        """
        Initialize the Agent Hook.
        
        Args:
            hook_id: Unique identifier for this hook instance
            configuration: Hook configuration settings
        """
        self.hook_id = hook_id
        self.configuration = configuration
        self._enabled = configuration.enabled
    
    @property
    def hook_type(self) -> str:
        """Return the hook type identifier."""
        return self.__class__.__name__
    
    @property
    def enabled(self) -> bool:
        """Check if the hook is enabled."""
        return self._enabled and self.configuration.enabled
    
    def enable(self):
        """Enable the hook."""
        self._enabled = True
    
    def disable(self):
        """Disable the hook."""
        self._enabled = False
    
    @abstractmethod
    async def can_handle(self, event: EnrichedEvent) -> bool:
        """
        Determine if this hook can handle the given event.
        
        Args:
            event: The enriched JIRA event to evaluate
            
        Returns:
            True if this hook should process the event, False otherwise
        """
        pass
    
    @abstractmethod
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """
        Execute the hook logic for the given event.
        
        Args:
            event: The enriched JIRA event to process
            
        Returns:
            Result of the hook execution including success status and metadata
        """
        pass
    
    async def validate_configuration(self) -> List[str]:
        """
        Validate the hook configuration.
        
        Returns:
            List of validation errors, empty if configuration is valid
        """
        errors = []
        
        if not self.configuration.hook_id:
            errors.append("Hook ID is required")
        
        if not self.configuration.team_id:
            errors.append("Team ID is required")
        
        if self.configuration.rate_limit_per_hour <= 0:
            errors.append("Rate limit must be positive")
        
        if self.configuration.retry_attempts < 0:
            errors.append("Retry attempts cannot be negative")
        
        if self.configuration.timeout_seconds <= 0:
            errors.append("Timeout must be positive")
        
        return errors
    
    def should_retry(self, execution_result: HookExecutionResult) -> bool:
        """
        Determine if a failed execution should be retried.
        
        Args:
            execution_result: The failed execution result
            
        Returns:
            True if the execution should be retried, False otherwise
        """
        if execution_result.status != HookStatus.FAILED:
            return False
        
        # Check if we've exceeded retry attempts
        retry_count = execution_result.metadata.get('retry_count', 0)
        return retry_count < self.configuration.retry_attempts
    
    def get_retry_delay(self, retry_count: int) -> float:
        """
        Calculate the delay before retrying a failed execution.
        
        Args:
            retry_count: Number of retries already attempted
            
        Returns:
            Delay in seconds before next retry
        """
        # Exponential backoff: 2^retry_count seconds, max 300 seconds (5 minutes)
        delay = min(2 ** retry_count, 300)
        return float(delay)


class HookRegistry:
    """Registry for managing Agent Hook instances."""
    
    def __init__(self):
        """Initialize the hook registry."""
        self._hooks: Dict[str, AgentHook] = {}
        self._hooks_by_type: Dict[str, List[AgentHook]] = {}
    
    def register_hook(self, hook: AgentHook) -> bool:
        """
        Register a hook in the registry.
        
        Args:
            hook: The hook to register
            
        Returns:
            True if registration was successful, False if hook already exists
        """
        if hook.hook_id in self._hooks:
            return False
        
        self._hooks[hook.hook_id] = hook
        
        hook_type = hook.hook_type
        if hook_type not in self._hooks_by_type:
            self._hooks_by_type[hook_type] = []
        self._hooks_by_type[hook_type].append(hook)
        
        return True
    
    def unregister_hook(self, hook_id: str) -> bool:
        """
        Unregister a hook from the registry.
        
        Args:
            hook_id: ID of the hook to unregister
            
        Returns:
            True if unregistration was successful, False if hook not found
        """
        if hook_id not in self._hooks:
            return False
        
        hook = self._hooks[hook_id]
        hook_type = hook.hook_type
        
        del self._hooks[hook_id]
        
        if hook_type in self._hooks_by_type:
            self._hooks_by_type[hook_type] = [
                h for h in self._hooks_by_type[hook_type] 
                if h.hook_id != hook_id
            ]
            if not self._hooks_by_type[hook_type]:
                del self._hooks_by_type[hook_type]
        
        return True
    
    def get_hook(self, hook_id: str) -> Optional[AgentHook]:
        """
        Get a hook by its ID.
        
        Args:
            hook_id: ID of the hook to retrieve
            
        Returns:
            The hook instance or None if not found
        """
        return self._hooks.get(hook_id)
    
    def get_hooks_by_type(self, hook_type: str) -> List[AgentHook]:
        """
        Get all hooks of a specific type.
        
        Args:
            hook_type: Type of hooks to retrieve
            
        Returns:
            List of hooks of the specified type
        """
        return self._hooks_by_type.get(hook_type, []).copy()
    
    def get_all_hooks(self) -> List[AgentHook]:
        """
        Get all registered hooks.
        
        Returns:
            List of all registered hooks
        """
        return list(self._hooks.values())
    
    def get_enabled_hooks(self) -> List[AgentHook]:
        """
        Get all enabled hooks.
        
        Returns:
            List of all enabled hooks
        """
        return [hook for hook in self._hooks.values() if hook.enabled]
    
    def clear(self):
        """Clear all registered hooks."""
        self._hooks.clear()
        self._hooks_by_type.clear()