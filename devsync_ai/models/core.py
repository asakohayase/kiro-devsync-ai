"""
Core Pydantic models for DevSync AI application.

This module contains all the core data models used throughout the application
for representing GitHub PRs, JIRA tickets, Slack messages, team members, and bottlenecks.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class PRStatus(str, Enum):
    """Enumeration of possible pull request statuses."""

    OPEN = "open"
    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    MERGED = "merged"
    CLOSED = "closed"


class MessageType(str, Enum):
    """Enumeration of Slack message types."""

    STANDUP = "standup"
    NOTIFICATION = "notification"
    CHANGELOG = "changelog"


class BottleneckType(str, Enum):
    """Enumeration of bottleneck types."""

    PR_REVIEW = "pr_review"
    TICKET_BLOCKED = "ticket_blocked"
    INACTIVE_MEMBER = "inactive_member"


class Severity(str, Enum):
    """Enumeration of severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PullRequest(BaseModel):
    """Model representing a GitHub pull request."""

    id: str = Field(..., description="Unique identifier for the pull request")
    repository: str = Field(..., description="Repository name where the PR exists")
    title: str = Field(..., description="Title of the pull request")
    author: str = Field(..., description="GitHub username of the PR author")
    status: PRStatus = Field(..., description="Current status of the pull request")
    merge_conflicts: bool = Field(default=False, description="Whether the PR has merge conflicts")
    created_at: datetime = Field(..., description="When the PR was created")
    updated_at: datetime = Field(..., description="When the PR was last updated")
    reviewers: List[str] = Field(default_factory=list, description="List of assigned reviewers")
    labels: List[str] = Field(default_factory=list, description="List of PR labels")

    @validator("repository")
    def validate_repository(cls, v):
        """Validate repository name format."""
        if not v or "/" not in v:
            raise ValueError('Repository must be in format "owner/repo"')
        return v

    @validator("title")
    def validate_title(cls, v):
        """Validate PR title is not empty."""
        if not v or not v.strip():
            raise ValueError("PR title cannot be empty")
        return v.strip()

    @validator("updated_at")
    def validate_updated_at(cls, v, values):
        """Ensure updated_at is not before created_at."""
        if "created_at" in values and v < values["created_at"]:
            raise ValueError("updated_at cannot be before created_at")
        return v

    class Config:
        """Pydantic model configuration."""

        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class JiraTicket(BaseModel):
    """Model representing a JIRA ticket."""

    key: str = Field(..., description="JIRA ticket key (e.g., PROJ-123)")
    summary: str = Field(..., description="Ticket summary/title")
    status: str = Field(..., description="Current ticket status")
    assignee: Optional[str] = Field(None, description="Assigned team member")
    priority: str = Field(..., description="Ticket priority level")
    story_points: Optional[int] = Field(None, description="Story points assigned to ticket")
    sprint: Optional[str] = Field(None, description="Current sprint name")
    blocked: bool = Field(default=False, description="Whether the ticket is blocked")
    last_updated: datetime = Field(..., description="When the ticket was last updated")
    time_in_status: timedelta = Field(..., description="How long ticket has been in current status")

    @validator("key")
    def validate_key(cls, v):
        """Validate JIRA key format."""
        if not v or "-" not in v:
            raise ValueError('JIRA key must be in format "PROJECT-123"')
        return v.upper()

    @validator("summary")
    def validate_summary(cls, v):
        """Validate ticket summary is not empty."""
        if not v or not v.strip():
            raise ValueError("Ticket summary cannot be empty")
        return v.strip()

    @validator("story_points")
    def validate_story_points(cls, v):
        """Validate story points are positive."""
        if v is not None and v < 0:
            raise ValueError("Story points must be positive")
        return v

    class Config:
        """Pydantic model configuration."""

        json_encoders = {datetime: lambda v: v.isoformat(), timedelta: lambda v: v.total_seconds()}


class SlackMessage(BaseModel):
    """Model representing a Slack message."""

    channel: str = Field(..., description="Slack channel ID or name")
    message_type: MessageType = Field(..., description="Type of message being sent")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When message was sent"
    )
    thread_ts: Optional[str] = Field(None, description="Thread timestamp for threaded messages")

    @validator("channel")
    def validate_channel(cls, v):
        """Validate channel format."""
        if not v or not v.strip():
            raise ValueError("Channel cannot be empty")
        return v.strip()

    @validator("content")
    def validate_content(cls, v):
        """Validate message content is not empty."""
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        return v.strip()

    class Config:
        """Pydantic model configuration."""

        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class TeamMember(BaseModel):
    """Model representing a team member."""

    username: str = Field(..., description="Primary username/identifier")
    github_handle: str = Field(..., description="GitHub username")
    jira_account: str = Field(..., description="JIRA account identifier")
    slack_user_id: str = Field(..., description="Slack user ID")
    role: str = Field(..., description="Team role (e.g., developer, lead, manager)")
    active: bool = Field(default=True, description="Whether the team member is active")

    @validator("username", "github_handle", "jira_account", "slack_user_id")
    def validate_identifiers(cls, v):
        """Validate identifiers are not empty."""
        if not v or not v.strip():
            raise ValueError("Identifier cannot be empty")
        return v.strip()

    @validator("role")
    def validate_role(cls, v):
        """Validate role is not empty."""
        if not v or not v.strip():
            raise ValueError("Role cannot be empty")
        return v.strip().lower()

    class Config:
        """Pydantic model configuration."""

        pass


class Bottleneck(BaseModel):
    """Model representing a detected bottleneck."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the bottleneck")
    type: BottleneckType = Field(..., description="Type of bottleneck detected")
    severity: Severity = Field(..., description="Severity level of the bottleneck")
    description: str = Field(..., description="Human-readable description of the bottleneck")
    affected_items: List[str] = Field(
        default_factory=list, description="List of affected items (PR IDs, ticket keys, etc.)"
    )
    detected_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the bottleneck was detected"
    )
    resolved: bool = Field(default=False, description="Whether the bottleneck has been resolved")
    resolved_at: Optional[datetime] = Field(None, description="When the bottleneck was resolved")

    @validator("description")
    def validate_description(cls, v):
        """Validate description is not empty."""
        if not v or not v.strip():
            raise ValueError("Description cannot be empty")
        return v.strip()

    @validator("resolved_at", always=True)
    def validate_resolved_at(cls, v, values):
        """Ensure resolved_at is set only when resolved is True."""
        if v is not None and not values.get("resolved", False):
            raise ValueError("resolved_at can only be set when resolved is True")
        if values.get("resolved", False) and v is None:
            # Auto-set resolved_at if resolved is True but resolved_at is None
            return datetime.utcnow()
        return v

    class Config:
        """Pydantic model configuration."""

        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
