"""
Tests for JIRA Agent Hooks.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from devsync_ai.hooks.jira_agent_hooks import (
    StatusChangeHook,
    BlockerHook,
    AssignmentChangeHook,
    CriticalUpdateHook,
    CommentHook,
    TransitionType,
    BlockerSeverity,
    SprintMetrics,
    WorkloadAnalysis,
    BlockerAnalysis
)
from devsync_ai.core.agent_hooks import (
    HookConfiguration,
    EnrichedEvent,
    ProcessedEvent,
    EventClassification,
    EventCategory,
    UrgencyLevel,
    SignificanceLevel,
    Stakeholder
)

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def sample_hook_configuration():
    """Create sample hook configuration."""
    return HookConfiguration(
        hook_id="test-hook",
        hook_type="TestHook",
        team_id="test-team",
        enabled=True,
        notification_channels=["#test-channel"],
        rate_limit_per_hour=50,
        retry_attempts=2,
        timeout_seconds=30
    )


@pytest.fixture
def sample_enriched_event():
    """Create sample enriched event."""
    processed_event = ProcessedEvent(
        event_id="test-event-123",
        event_type="jira:issue_updated",
        timestamp=datetime.now(timezone.utc),
        jira_event_data={"key": "TEST-123"},
        ticket_key="TEST-123",
        project_key="TEST",
        raw_payload={"webhookEvent": "jira:issue_updated"}
    )
    
    classification = EventClassification(
        category=EventCategory.STATUS_CHANGE,
        urgency=UrgencyLevel.MEDIUM,
        significance=SignificanceLevel.MODERATE,
        affected_teams=["test-team"]
    )
    
    return EnrichedEvent(
        **processed_event.__dict__,
        ticket_details={
            "summary": "Test ticket",
            "status": "In Progress",
            "priority": "Medium",
            "assignee": "Test User"
        },
        stakeholders=[
            Stakeholder(
                user_id="user123",
                display_name="Test User",
                email="test@example.com",
                role="assignee"
            )
        ],
        classification=classification,
        context_data={
            "processor_data": {
                "field_changes": [],
                "is_blocked": False
            }
        }
    )


class TestStatusChangeHook:
    """Test StatusChangeHook functionality."""
    
    async def test_can_handle_status_change(self, sample_hook_configuration, sample_enriched_event):
        """Test hook can handle status change events."""
        hook = StatusChangeHook("test-hook", sample_hook_configuration)
        
        # Test with status change event
        sample_enriched_event.classification.category = EventCategory.STATUS_CHANGE
        assert await hook.can_handle(sample_enriched_event) is True
        
        # Test with transition event
        sample_enriched_event.classification.category = EventCategory.TRANSITION
        assert await hook.can_handle(sample_enriched_event) is True
        
        # Test with other event types
        sample_enriched_event.classification.category = EventCategory.COMMENT
        assert await hook.can_handle(sample_enriched_event) is False
    
    async def test_execute_status_change(self, sample_hook_configuration, sample_enriched_event):
        """Test status change hook execution."""
        hook = StatusChangeHook("test-hook", sample_hook_configuration)
        
        with patch.object(hook, '_send_notifications', return_value=True):
            result = await hook.execute(sample_enriched_event)
            
            assert result.status.value == "success"
            assert result.hook_id == "test-hook"
            assert result.event_id == sample_enriched_event.event_id
            assert result.notification_sent is True


class TestBlockerHook:
    """Test BlockerHook functionality."""
    
    async def test_can_handle_blocked_status(self, sample_hook_configuration, sample_enriched_event):
        """Test hook can handle blocked status events."""
        hook = BlockerHook("test-hook", sample_hook_configuration)
        
        # Test with blocked status
        sample_enriched_event.context_data['processor_data']['is_blocked'] = True
        assert await hook.can_handle(sample_enriched_event) is True
        
        # Test without blocked status
        sample_enriched_event.context_data['processor_data']['is_blocked'] = False
        assert await hook.can_handle(sample_enriched_event) is False
    
    async def test_analyze_blocker(self, sample_hook_configuration, sample_enriched_event):
        """Test blocker analysis."""
        hook = BlockerHook("test-hook", sample_hook_configuration)
        
        # Set up high priority ticket
        sample_enriched_event.ticket_details['priority'] = 'Critical'
        sample_enriched_event.classification.urgency = UrgencyLevel.CRITICAL
        
        analysis = await hook._analyze_blocker(sample_enriched_event)
        
        assert isinstance(analysis, BlockerAnalysis)
        assert analysis.severity == BlockerSeverity.CRITICAL
        assert analysis.escalation_required is True
        assert len(analysis.resolution_suggestions) > 0


# Additional test classes would follow the same pattern...