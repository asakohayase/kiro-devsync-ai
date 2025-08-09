"""
Unit tests for core Pydantic models.

Tests validation rules, serialization, and edge cases for all core models.
"""

import pytest
from datetime import datetime, timedelta
from uuid import UUID

from pydantic import ValidationError

from devsync_ai.models.core import (
    PullRequest,
    JiraTicket,
    SlackMessage,
    TeamMember,
    Bottleneck,
    PRStatus,
    MessageType,
    BottleneckType,
    Severity,
)


class TestPullRequest:
    """Test cases for PullRequest model."""

    def test_valid_pull_request(self):
        """Test creating a valid pull request."""
        created_at = datetime.utcnow()
        updated_at = created_at + timedelta(hours=1)

        pr = PullRequest(
            id="123",
            repository="owner/repo",
            title="Add new feature",
            author="developer",
            status=PRStatus.OPEN,
            created_at=created_at,
            updated_at=updated_at,
            reviewers=["reviewer1", "reviewer2"],
            labels=["feature", "backend"],
        )

        assert pr.id == "123"
        assert pr.repository == "owner/repo"
        assert pr.title == "Add new feature"
        assert pr.author == "developer"
        assert pr.status == PRStatus.OPEN
        assert pr.merge_conflicts is False
        assert pr.created_at == created_at
        assert pr.updated_at == updated_at
        assert pr.reviewers == ["reviewer1", "reviewer2"]
        assert pr.labels == ["feature", "backend"]

    def test_invalid_repository_format(self):
        """Test validation error for invalid repository format."""
        with pytest.raises(ValidationError) as exc_info:
            PullRequest(
                id="123",
                repository="invalid-repo",
                title="Test PR",
                author="developer",
                status=PRStatus.OPEN,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

        assert "Repository must be in format" in str(exc_info.value)

    def test_empty_title_validation(self):
        """Test validation error for empty title."""
        with pytest.raises(ValidationError) as exc_info:
            PullRequest(
                id="123",
                repository="owner/repo",
                title="   ",
                author="developer",
                status=PRStatus.OPEN,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

        assert "PR title cannot be empty" in str(exc_info.value)

    def test_updated_at_before_created_at(self):
        """Test validation error when updated_at is before created_at."""
        created_at = datetime.utcnow()
        updated_at = created_at - timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            PullRequest(
                id="123",
                repository="owner/repo",
                title="Test PR",
                author="developer",
                status=PRStatus.OPEN,
                created_at=created_at,
                updated_at=updated_at,
            )

        assert "updated_at cannot be before created_at" in str(exc_info.value)

    def test_serialization(self):
        """Test JSON serialization of PullRequest."""
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        updated_at = datetime(2024, 1, 1, 13, 0, 0)

        pr = PullRequest(
            id="123",
            repository="owner/repo",
            title="Test PR",
            author="developer",
            status=PRStatus.OPEN,
            created_at=created_at,
            updated_at=updated_at,
        )

        json_data = pr.dict()
        assert json_data["status"] == "open"
        assert isinstance(json_data["created_at"], datetime)


class TestJiraTicket:
    """Test cases for JiraTicket model."""

    def test_valid_jira_ticket(self):
        """Test creating a valid JIRA ticket."""
        last_updated = datetime.utcnow()
        time_in_status = timedelta(days=2)

        ticket = JiraTicket(
            key="PROJ-123",
            summary="Implement user authentication",
            status="In Progress",
            assignee="developer",
            priority="High",
            story_points=5,
            sprint="Sprint 1",
            last_updated=last_updated,
            time_in_status=time_in_status,
        )

        assert ticket.key == "PROJ-123"
        assert ticket.summary == "Implement user authentication"
        assert ticket.status == "In Progress"
        assert ticket.assignee == "developer"
        assert ticket.priority == "High"
        assert ticket.story_points == 5
        assert ticket.sprint == "Sprint 1"
        assert ticket.blocked is False
        assert ticket.last_updated == last_updated
        assert ticket.time_in_status == time_in_status

    def test_invalid_jira_key_format(self):
        """Test validation error for invalid JIRA key format."""
        with pytest.raises(ValidationError) as exc_info:
            JiraTicket(
                key="INVALID",
                summary="Test ticket",
                status="Open",
                priority="Medium",
                last_updated=datetime.utcnow(),
                time_in_status=timedelta(days=1),
            )

        assert "JIRA key must be in format" in str(exc_info.value)

    def test_jira_key_uppercase_conversion(self):
        """Test that JIRA key is converted to uppercase."""
        ticket = JiraTicket(
            key="proj-123",
            summary="Test ticket",
            status="Open",
            priority="Medium",
            last_updated=datetime.utcnow(),
            time_in_status=timedelta(days=1),
        )

        assert ticket.key == "PROJ-123"

    def test_empty_summary_validation(self):
        """Test validation error for empty summary."""
        with pytest.raises(ValidationError) as exc_info:
            JiraTicket(
                key="PROJ-123",
                summary="",
                status="Open",
                priority="Medium",
                last_updated=datetime.utcnow(),
                time_in_status=timedelta(days=1),
            )

        assert "Ticket summary cannot be empty" in str(exc_info.value)

    def test_negative_story_points_validation(self):
        """Test validation error for negative story points."""
        with pytest.raises(ValidationError) as exc_info:
            JiraTicket(
                key="PROJ-123",
                summary="Test ticket",
                status="Open",
                priority="Medium",
                story_points=-1,
                last_updated=datetime.utcnow(),
                time_in_status=timedelta(days=1),
            )

        assert "Story points must be positive" in str(exc_info.value)


class TestSlackMessage:
    """Test cases for SlackMessage model."""

    def test_valid_slack_message(self):
        """Test creating a valid Slack message."""
        timestamp = datetime.utcnow()

        message = SlackMessage(
            channel="#general",
            message_type=MessageType.STANDUP,
            content="Daily standup summary",
            timestamp=timestamp,
            thread_ts="1234567890.123456",
        )

        assert message.channel == "#general"
        assert message.message_type == MessageType.STANDUP
        assert message.content == "Daily standup summary"
        assert message.timestamp == timestamp
        assert message.thread_ts == "1234567890.123456"

    def test_empty_channel_validation(self):
        """Test validation error for empty channel."""
        with pytest.raises(ValidationError) as exc_info:
            SlackMessage(channel="", message_type=MessageType.NOTIFICATION, content="Test message")

        assert "Channel cannot be empty" in str(exc_info.value)

    def test_empty_content_validation(self):
        """Test validation error for empty content."""
        with pytest.raises(ValidationError) as exc_info:
            SlackMessage(channel="#general", message_type=MessageType.NOTIFICATION, content="   ")

        assert "Message content cannot be empty" in str(exc_info.value)

    def test_default_timestamp(self):
        """Test that timestamp defaults to current time."""
        message = SlackMessage(
            channel="#general", message_type=MessageType.NOTIFICATION, content="Test message"
        )

        # Should be set to approximately now
        assert isinstance(message.timestamp, datetime)
        assert (datetime.utcnow() - message.timestamp).total_seconds() < 1


class TestTeamMember:
    """Test cases for TeamMember model."""

    def test_valid_team_member(self):
        """Test creating a valid team member."""
        member = TeamMember(
            username="john_doe",
            github_handle="johndoe",
            jira_account="john.doe@company.com",
            slack_user_id="U1234567890",
            role="Senior Developer",
        )

        assert member.username == "john_doe"
        assert member.github_handle == "johndoe"
        assert member.jira_account == "john.doe@company.com"
        assert member.slack_user_id == "U1234567890"
        assert member.role == "senior developer"  # Should be lowercased
        assert member.active is True

    def test_empty_identifier_validation(self):
        """Test validation error for empty identifiers."""
        with pytest.raises(ValidationError) as exc_info:
            TeamMember(
                username="",
                github_handle="johndoe",
                jira_account="john.doe@company.com",
                slack_user_id="U1234567890",
                role="Developer",
            )

        assert "Identifier cannot be empty" in str(exc_info.value)

    def test_empty_role_validation(self):
        """Test validation error for empty role."""
        with pytest.raises(ValidationError) as exc_info:
            TeamMember(
                username="john_doe",
                github_handle="johndoe",
                jira_account="john.doe@company.com",
                slack_user_id="U1234567890",
                role="   ",
            )

        assert "Role cannot be empty" in str(exc_info.value)


class TestBottleneck:
    """Test cases for Bottleneck model."""

    def test_valid_bottleneck(self):
        """Test creating a valid bottleneck."""
        detected_at = datetime.utcnow()

        bottleneck = Bottleneck(
            type=BottleneckType.PR_REVIEW,
            severity=Severity.HIGH,
            description="PR has been waiting for review for 5 days",
            affected_items=["PR-123", "PR-456"],
            detected_at=detected_at,
        )

        assert isinstance(bottleneck.id, UUID)
        assert bottleneck.type == BottleneckType.PR_REVIEW
        assert bottleneck.severity == Severity.HIGH
        assert bottleneck.description == "PR has been waiting for review for 5 days"
        assert bottleneck.affected_items == ["PR-123", "PR-456"]
        assert bottleneck.detected_at == detected_at
        assert bottleneck.resolved is False
        assert bottleneck.resolved_at is None

    def test_empty_description_validation(self):
        """Test validation error for empty description."""
        with pytest.raises(ValidationError) as exc_info:
            Bottleneck(
                type=BottleneckType.PR_REVIEW,
                severity=Severity.HIGH,
                description="",
                affected_items=["PR-123"],
            )

        assert "Description cannot be empty" in str(exc_info.value)

    def test_resolved_at_validation(self):
        """Test validation of resolved_at field."""
        # Test that resolved_at cannot be set when resolved is False
        with pytest.raises(ValidationError) as exc_info:
            Bottleneck(
                type=BottleneckType.PR_REVIEW,
                severity=Severity.HIGH,
                description="Test bottleneck",
                resolved=False,
                resolved_at=datetime.utcnow(),
            )

        assert "resolved_at can only be set when resolved is True" in str(exc_info.value)

    def test_auto_set_resolved_at(self):
        """Test that resolved_at is auto-set when resolved is True."""
        bottleneck = Bottleneck(
            type=BottleneckType.PR_REVIEW,
            severity=Severity.HIGH,
            description="Test bottleneck",
            resolved=True,
        )

        assert bottleneck.resolved_at is not None
        assert isinstance(bottleneck.resolved_at, datetime)

    def test_default_detected_at(self):
        """Test that detected_at defaults to current time."""
        bottleneck = Bottleneck(
            type=BottleneckType.PR_REVIEW, severity=Severity.HIGH, description="Test bottleneck"
        )

        # Should be set to approximately now
        assert isinstance(bottleneck.detected_at, datetime)
        assert (datetime.utcnow() - bottleneck.detected_at).total_seconds() < 1

    def test_serialization_with_uuid(self):
        """Test JSON serialization includes UUID as string."""
        bottleneck = Bottleneck(
            type=BottleneckType.PR_REVIEW, severity=Severity.HIGH, description="Test bottleneck"
        )

        json_data = bottleneck.dict()
        assert isinstance(json_data["id"], UUID)
        assert json_data["type"] == "pr_review"
        assert json_data["severity"] == "high"
