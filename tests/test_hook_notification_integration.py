"""
Integration tests for Agent Hook notification processing.

Tests the integration between Agent Hooks and the Enhanced Notification Handler,
including context creation, routing, urgency mapping, and batching integration.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from devsync_ai.core.hook_notification_integration import (
    HookNotificationMapper,
    HookNotificationIntegrator,
    HookNotificationContext,
    HookNotificationType,
    default_hook_notification_integrator
)
from devsync_ai.core.agent_hooks import (
    EnrichedEvent,
    HookExecutionResult,
    HookStatus,
    EventCategory,
    UrgencyLevel,
    SignificanceLevel,
    EventClassification,
    Stakeholder,
    ProcessedEvent
)
from devsync_ai.core.enhanced_notification_handler import (
    NotificationContext,
    ProcessingResult,
    ProcessingDecision,
    EnhancedNotificationHandler
)
from devsync_ai.core.channel_router import NotificationType, NotificationUrgency


class TestHookNotificationMapper:
    """Test the HookNotificationMapper class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = HookNotificationMapper()
        
        # Create test event
        self.test_event = EnrichedEvent(
            event_id="test-event-123",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={"issue": {"key": "TEST-123"}},
            ticket_key="TEST-123",
            project_key="TEST",
            raw_payload={"webhookEvent": "jira:issue_updated"},
            ticket_details={
                "summary": "Test ticket summary",
                "description": "Test ticket description",
                "priority": "High",
                "status": "In Progress",
                "assignee": {"displayName": "John Doe", "name": "jdoe"},
                "reporter": {"displayName": "Jane Smith", "name": "jsmith"}
            },
            stakeholders=[
                Stakeholder(
                    user_id="jdoe",
                    display_name="John Doe",
                    email="john.doe@example.com",
                    role="assignee",
                    team_id="dev-team",
                    slack_user_id="U123456"
                )
            ],
            classification=EventClassification(
                category=EventCategory.STATUS_CHANGE,
                urgency=UrgencyLevel.HIGH,
                significance=SignificanceLevel.MAJOR,
                affected_teams=["dev-team"],
                routing_hints={"priority": "high"},
                keywords=["status", "change"]
            ),
            context_data={
                "team_id": "dev-team",
                "author": "Jane Smith",
                "processor_data": {
                    "field_changes": [],
                    "is_blocked": False
                }
            }
        )
        
        # Create test execution result
        self.test_execution_result = HookExecutionResult(
            hook_id="test-hook-123",
            execution_id="exec-456",
            hook_type="StatusChangeHook",
            event_id="test-event-123",
            status=HookStatus.SUCCESS,
            execution_time_ms=150.5,
            notification_sent=False,
            metadata={
                "transition_type": "forward",
                "sprint_impact": False,
                "workload_impact": False
            }
        )
    
    def test_create_notification_context_basic(self):
        """Test basic notification context creation."""
        hook_context = HookNotificationContext(
            hook_id="test-hook-123",
            hook_type="StatusChangeHook",
            event=self.test_event,
            execution_result=self.test_execution_result,
            notification_type=HookNotificationType.JIRA_STATUS_CHANGE
        )
        
        context = self.mapper.create_notification_context(hook_context)
        
        assert isinstance(context, NotificationContext)
        assert context.notification_type == NotificationType.JIRA_STATUS
        assert context.event_type == "jira:issue_updated"
        assert context.team_id == "dev-team"
        assert context.author == "Jane Smith"
        assert context.data["ticket_key"] == "TEST-123"
        assert context.data["summary"] == "Test ticket summary"
        assert context.data["priority"] == "High"
        assert context.metadata["hook_id"] == "test-hook-123"
        assert context.metadata["hook_type"] == "StatusChangeHook"
    
    def test_create_notification_context_with_overrides(self):
        """Test notification context creation with overrides."""
        hook_context = HookNotificationContext(
            hook_id="test-hook-123",
            hook_type="StatusChangeHook",
            event=self.test_event,
            execution_result=self.test_execution_result,
            notification_type=HookNotificationType.JIRA_BLOCKER_DETECTED,
            urgency_override=UrgencyLevel.CRITICAL,
            channel_override="#critical-alerts",
            metadata={"custom_field": "custom_value"}
        )
        
        context = self.mapper.create_notification_context(hook_context)
        
        assert context.notification_type == NotificationType.JIRA_BLOCKER
        assert context.channel_override == "#critical-alerts"
        assert context.priority_override == "critical"
        assert context.metadata["custom_field"] == "custom_value"
    
    def test_determine_notification_type_from_category(self):
        """Test notification type determination from event category."""
        # Test different event categories
        test_cases = [
            (EventCategory.STATUS_CHANGE, HookNotificationType.JIRA_STATUS_CHANGE),
            (EventCategory.ASSIGNMENT, HookNotificationType.JIRA_ASSIGNMENT),
            (EventCategory.COMMENT, HookNotificationType.JIRA_COMMENT_PRIORITY),
            (EventCategory.BLOCKER, HookNotificationType.JIRA_BLOCKER_DETECTED),
            (EventCategory.PRIORITY_CHANGE, HookNotificationType.JIRA_PRIORITY_CHANGE),
        ]
        
        for category, expected_type in test_cases:
            event = self.test_event
            event.classification.category = category
            
            hook_context = HookNotificationContext(
                hook_id="test-hook",
                hook_type="TestHook",
                event=event,
                execution_result=self.test_execution_result,
                notification_type=None  # Let it be determined
            )
            
            result_type = self.mapper._determine_notification_type(hook_context)
            assert result_type == expected_type
    
    def test_determine_notification_type_from_hook_type(self):
        """Test notification type determination from hook type."""
        test_cases = [
            ("StatusChangeHook", HookNotificationType.JIRA_STATUS_CHANGE),
            ("AssignmentHook", HookNotificationType.JIRA_ASSIGNMENT),
            ("CommentHook", HookNotificationType.JIRA_COMMENT_PRIORITY),
            ("BlockerHook", HookNotificationType.JIRA_BLOCKER_DETECTED),
            ("UnknownHook", HookNotificationType.JIRA_STATUS_CHANGE),  # Default
        ]
        
        # Create event without classification to test hook type logic
        event_no_classification = EnrichedEvent(
            event_id="test-event-123",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={"issue": {"key": "TEST-123"}},
            ticket_key="TEST-123",
            project_key="TEST",
            raw_payload={"webhookEvent": "jira:issue_updated"},
            classification=None  # No classification to test hook type logic
        )
        
        for hook_type, expected_type in test_cases:
            hook_context = HookNotificationContext(
                hook_id="test-hook",
                hook_type=hook_type,
                event=event_no_classification,
                execution_result=self.test_execution_result,
                notification_type=None
            )
            
            result_type = self.mapper._determine_notification_type(hook_context)
            assert result_type == expected_type
    
    def test_create_notification_data_comprehensive(self):
        """Test comprehensive notification data creation."""
        hook_context = HookNotificationContext(
            hook_id="test-hook-123",
            hook_type="StatusChangeHook",
            event=self.test_event,
            execution_result=self.test_execution_result,
            notification_type=HookNotificationType.JIRA_STATUS_CHANGE
        )
        
        data = self.mapper._create_notification_data(hook_context)
        
        # Check basic ticket data
        assert data["ticket_key"] == "TEST-123"
        assert data["project_key"] == "TEST"
        assert data["summary"] == "Test ticket summary"
        assert data["priority"] == "High"
        assert data["status"] == "In Progress"
        assert data["assignee"] == "John Doe"
        assert data["reporter"] == "Jane Smith"
        
        # Check hook execution data
        assert data["hook_execution"]["hook_id"] == "test-hook-123"
        assert data["hook_execution"]["hook_type"] == "StatusChangeHook"
        assert data["hook_execution"]["execution_time_ms"] == 150.5
        
        # Check classification data
        assert data["classification"]["category"] == "status_change"
        assert data["classification"]["urgency"] == "high"
        assert data["classification"]["significance"] == "major"
        assert data["classification"]["affected_teams"] == ["dev-team"]
        
        # Check stakeholder data
        assert len(data["stakeholders"]) == 1
        assert data["stakeholders"][0]["display_name"] == "John Doe"
        assert data["stakeholders"][0]["team_id"] == "dev-team"
        
        # Check context data
        assert data["context"]["team_id"] == "dev-team"
        assert data["context"]["author"] == "Jane Smith"
    
    def test_determine_team_id_priority(self):
        """Test team ID determination priority."""
        # Test with classification teams
        event_with_teams = self.test_event
        event_with_teams.classification.affected_teams = ["team1", "team2"]
        
        team_id = self.mapper._determine_team_id(event_with_teams)
        assert team_id == "team1"  # First team in list
        
        # Test with stakeholder team
        event_no_classification = EnrichedEvent(
            event_id="test",
            event_type="test",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={},
            ticket_key="TEST-123",
            project_key="TEST",
            raw_payload={},
            stakeholders=[
                Stakeholder(
                    user_id="user1",
                    display_name="User 1",
                    team_id="stakeholder-team"
                )
            ],
            classification=None
        )
        
        team_id = self.mapper._determine_team_id(event_no_classification)
        assert team_id == "stakeholder-team"
        
        # Test with project key fallback
        event_minimal = EnrichedEvent(
            event_id="test",
            event_type="test",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={},
            ticket_key="TEST-123",
            project_key="MYPROJECT",
            raw_payload={},
            stakeholders=[],
            classification=None
        )
        
        team_id = self.mapper._determine_team_id(event_minimal)
        assert team_id == "myproject"  # Lowercased project key
    
    def test_determine_channel_override(self):
        """Test channel override determination."""
        # Test with explicit override
        hook_context = HookNotificationContext(
            hook_id="test-hook",
            hook_type="StatusChangeHook",
            event=self.test_event,
            execution_result=self.test_execution_result,
            notification_type=HookNotificationType.JIRA_STATUS_CHANGE,
            channel_override="#explicit-channel"
        )
        
        channel = self.mapper._determine_channel_override(hook_context)
        assert channel == "#explicit-channel"
        
        # Test with urgency-based routing
        hook_context_high = HookNotificationContext(
            hook_id="test-hook",
            hook_type="StatusChangeHook",
            event=self.test_event,
            execution_result=self.test_execution_result,
            notification_type=HookNotificationType.JIRA_STATUS_CHANGE,
            urgency_override=UrgencyLevel.HIGH
        )
        
        channel = self.mapper._determine_channel_override(hook_context_high)
        assert channel == "#dev-updates"  # First channel for StatusChangeHook + HIGH urgency


class TestHookNotificationIntegrator:
    """Test the HookNotificationIntegrator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_handler = Mock(spec=EnhancedNotificationHandler)
        self.mock_mapper = Mock(spec=HookNotificationMapper)
        
        self.integrator = HookNotificationIntegrator(
            notification_handler=self.mock_handler,
            mapper=self.mock_mapper
        )
        
        # Create test fixtures
        self.test_event = EnrichedEvent(
            event_id="test-event-123",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={"issue": {"key": "TEST-123"}},
            ticket_key="TEST-123",
            project_key="TEST",
            raw_payload={},
            classification=EventClassification(
                category=EventCategory.STATUS_CHANGE,
                urgency=UrgencyLevel.HIGH,
                significance=SignificanceLevel.MAJOR,
                affected_teams=["dev-team"]
            )
        )
        
        self.test_execution_result = HookExecutionResult(
            hook_id="test-hook-123",
            execution_id="exec-456",
            hook_type="StatusChangeHook",
            event_id="test-event-123",
            status=HookStatus.SUCCESS,
            execution_time_ms=150.5
        )
    
    @pytest.mark.asyncio
    async def test_process_hook_notification_success(self):
        """Test successful hook notification processing."""
        # Mock the mapper
        mock_context = NotificationContext(
            notification_type=NotificationType.JIRA_STATUS,
            event_type="jira:issue_updated",
            data={"ticket_key": "TEST-123"},
            team_id="dev-team"
        )
        self.mock_mapper.create_notification_context.return_value = mock_context
        
        # Mock the handler
        mock_result = ProcessingResult(
            decision=ProcessingDecision.SEND_IMMEDIATELY,
            channel="#dev-updates",
            processing_time_ms=50.0
        )
        self.mock_handler.process_notification = AsyncMock(return_value=mock_result)
        
        # Process notification
        result = await self.integrator.process_hook_notification(
            hook_id="test-hook-123",
            hook_type="StatusChangeHook",
            event=self.test_event,
            execution_result=self.test_execution_result,
            notification_type=HookNotificationType.JIRA_STATUS_CHANGE
        )
        
        # Verify calls
        self.mock_mapper.create_notification_context.assert_called_once()
        self.mock_handler.process_notification.assert_called_once_with(mock_context)
        
        # Verify result
        assert result == mock_result
        
        # Verify statistics
        stats = self.integrator.get_integration_stats()
        assert stats["notifications_processed"] == 1
        assert stats["notifications_sent"] == 1
        assert stats["success_rate"] == 100.0
    
    @pytest.mark.asyncio
    async def test_process_hook_notification_batched(self):
        """Test hook notification that gets batched."""
        # Mock the mapper
        mock_context = NotificationContext(
            notification_type=NotificationType.JIRA_STATUS,
            event_type="jira:issue_updated",
            data={"ticket_key": "TEST-123"},
            team_id="dev-team"
        )
        self.mock_mapper.create_notification_context.return_value = mock_context
        
        # Mock the handler to return batched decision
        mock_result = ProcessingResult(
            decision=ProcessingDecision.BATCH_AND_SEND,
            channel="#dev-updates",
            processing_time_ms=25.0
        )
        self.mock_handler.process_notification = AsyncMock(return_value=mock_result)
        
        # Process notification
        result = await self.integrator.process_hook_notification(
            hook_id="test-hook-123",
            hook_type="StatusChangeHook",
            event=self.test_event,
            execution_result=self.test_execution_result
        )
        
        # Verify result
        assert result.decision == ProcessingDecision.BATCH_AND_SEND
        
        # Verify statistics
        stats = self.integrator.get_integration_stats()
        assert stats["notifications_batched"] == 1
        assert stats["batched_rate"] == 100.0
    
    @pytest.mark.asyncio
    async def test_process_hook_notification_filtered(self):
        """Test hook notification that gets filtered out."""
        # Mock the mapper
        mock_context = NotificationContext(
            notification_type=NotificationType.JIRA_STATUS,
            event_type="jira:issue_updated",
            data={"ticket_key": "TEST-123"},
            team_id="dev-team"
        )
        self.mock_mapper.create_notification_context.return_value = mock_context
        
        # Mock the handler to return filtered decision
        mock_result = ProcessingResult(
            decision=ProcessingDecision.FILTER_OUT,
            reason="filtered_by_rules",
            processing_time_ms=10.0
        )
        self.mock_handler.process_notification = AsyncMock(return_value=mock_result)
        
        # Process notification
        result = await self.integrator.process_hook_notification(
            hook_id="test-hook-123",
            hook_type="StatusChangeHook",
            event=self.test_event,
            execution_result=self.test_execution_result
        )
        
        # Verify result
        assert result.decision == ProcessingDecision.FILTER_OUT
        
        # Verify statistics
        stats = self.integrator.get_integration_stats()
        assert stats["notifications_filtered"] == 1
    
    @pytest.mark.asyncio
    async def test_process_hook_notification_error(self):
        """Test hook notification processing with error."""
        # Mock the mapper to raise an exception
        self.mock_mapper.create_notification_context.side_effect = Exception("Mapping error")
        
        # Process notification and expect exception
        with pytest.raises(Exception, match="Mapping error"):
            await self.integrator.process_hook_notification(
                hook_id="test-hook-123",
                hook_type="StatusChangeHook",
                event=self.test_event,
                execution_result=self.test_execution_result
            )
        
        # Verify error statistics
        stats = self.integrator.get_integration_stats()
        assert stats["errors"] == 1
        assert stats["success_rate"] == 0.0
    
    @pytest.mark.asyncio
    async def test_send_hook_notification_directly(self):
        """Test sending hook notification directly without event context."""
        # Mock the handler
        mock_result = ProcessingResult(
            decision=ProcessingDecision.SEND_IMMEDIATELY,
            channel="#dev-updates",
            processing_time_ms=30.0
        )
        self.mock_handler.process_notification = AsyncMock(return_value=mock_result)
        
        # Send direct notification
        result = await self.integrator.send_hook_notification_directly(
            hook_id="test-hook-123",
            hook_type="StatusChangeHook",
            notification_type=HookNotificationType.JIRA_STATUS_CHANGE,
            data={"ticket_key": "TEST-123", "summary": "Test summary"},
            team_id="dev-team",
            author="John Doe",
            urgency=UrgencyLevel.HIGH
        )
        
        # Verify handler was called
        self.mock_handler.process_notification.assert_called_once()
        call_args = self.mock_handler.process_notification.call_args[0][0]
        
        assert call_args.notification_type == NotificationType.JIRA_STATUS
        assert call_args.team_id == "dev-team"
        assert call_args.author == "John Doe"
        assert call_args.priority_override == "high"
        assert call_args.data["hook_id"] == "test-hook-123"
        assert call_args.data["hook_type"] == "StatusChangeHook"
        assert call_args.metadata["source"] == "hook_direct"
        
        # Verify result
        assert result == mock_result
    
    def test_get_integration_stats(self):
        """Test integration statistics calculation."""
        # Simulate some processing
        self.integrator._stats = {
            "notifications_processed": 10,
            "notifications_sent": 6,
            "notifications_batched": 2,
            "notifications_scheduled": 1,
            "notifications_filtered": 1,
            "errors": 0,
        }
        
        stats = self.integrator.get_integration_stats()
        
        assert stats["notifications_processed"] == 10
        assert stats["notifications_sent"] == 6
        assert stats["notifications_batched"] == 2
        assert stats["success_rate"] == 100.0  # No errors
        assert stats["sent_rate"] == 60.0  # 6/10
        assert stats["batched_rate"] == 20.0  # 2/10
    
    def test_reset_stats(self):
        """Test statistics reset."""
        # Set some stats
        self.integrator._stats["notifications_processed"] = 5
        self.integrator._stats["errors"] = 2
        
        # Reset
        self.integrator.reset_stats()
        
        # Verify all stats are zero
        for value in self.integrator._stats.values():
            assert value == 0


class TestHookNotificationIntegrationEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_status_change_hook_integration_flow(self):
        """Test complete flow from status change hook to notification."""
        # This would be a more comprehensive test that actually creates
        # real instances and tests the full integration flow
        
        # Create real mapper and integrator
        mapper = HookNotificationMapper()
        
        # Mock the notification handler for testing
        mock_handler = Mock(spec=EnhancedNotificationHandler)
        mock_result = ProcessingResult(
            decision=ProcessingDecision.SEND_IMMEDIATELY,
            channel="#dev-updates",
            processing_time_ms=75.0
        )
        mock_handler.process_notification = AsyncMock(return_value=mock_result)
        
        integrator = HookNotificationIntegrator(
            notification_handler=mock_handler,
            mapper=mapper
        )
        
        # Create realistic test data
        event = EnrichedEvent(
            event_id="jira-event-789",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "issue": {
                    "key": "DEV-456",
                    "fields": {
                        "summary": "Fix critical bug in payment processing",
                        "priority": {"name": "Critical"},
                        "status": {"name": "In Progress"},
                        "assignee": {"displayName": "Alice Johnson"},
                        "reporter": {"displayName": "Bob Wilson"}
                    }
                }
            },
            ticket_key="DEV-456",
            project_key="DEV",
            raw_payload={"webhookEvent": "jira:issue_updated"},
            ticket_details={
                "summary": "Fix critical bug in payment processing",
                "priority": "Critical",
                "status": "In Progress",
                "assignee": {"displayName": "Alice Johnson"},
                "reporter": {"displayName": "Bob Wilson"}
            },
            stakeholders=[
                Stakeholder(
                    user_id="ajohnson",
                    display_name="Alice Johnson",
                    email="alice.johnson@company.com",
                    role="assignee",
                    team_id="payments-team"
                )
            ],
            classification=EventClassification(
                category=EventCategory.STATUS_CHANGE,
                urgency=UrgencyLevel.CRITICAL,
                significance=SignificanceLevel.CRITICAL,
                affected_teams=["payments-team"],
                routing_hints={"priority": "critical", "component": "payments"},
                keywords=["critical", "bug", "payment"]
            ),
            context_data={
                "processor_data": {
                    "field_changes": [
                        {"field_name": "status", "old_value": "To Do", "new_value": "In Progress"}
                    ],
                    "is_blocked": False
                },
                "sprint_context": {"sprint_name": "Sprint 23"},
                "assignee_info": {"assignee_name": "Alice Johnson"}
            }
        )
        
        execution_result = HookExecutionResult(
            hook_id="status-hook-001",
            execution_id="exec-789",
            hook_type="StatusChangeHook",
            event_id="jira-event-789",
            status=HookStatus.SUCCESS,
            execution_time_ms=125.0,
            metadata={
                "transition_type": "forward",
                "sprint_impact": False,
                "workload_impact": True
            }
        )
        
        # Process the notification
        result = await integrator.process_hook_notification(
            hook_id="status-hook-001",
            hook_type="StatusChangeHook",
            event=event,
            execution_result=execution_result,
            notification_type=HookNotificationType.JIRA_STATUS_CHANGE,
            urgency_override=UrgencyLevel.CRITICAL
        )
        
        # Verify the handler was called with correct context
        mock_handler.process_notification.assert_called_once()
        context = mock_handler.process_notification.call_args[0][0]
        
        assert context.notification_type == NotificationType.JIRA_STATUS
        assert context.team_id == "payments-team"
        assert context.author == "Bob Wilson"
        assert context.priority_override == "critical"
        assert context.data["ticket_key"] == "DEV-456"
        assert context.data["summary"] == "Fix critical bug in payment processing"
        assert context.data["priority"] == "Critical"
        assert context.data["classification"]["urgency"] == "critical"
        assert context.metadata["hook_id"] == "status-hook-001"
        assert context.metadata["hook_type"] == "StatusChangeHook"
        
        # Verify result
        assert result.decision == ProcessingDecision.SEND_IMMEDIATELY
        assert result.channel == "#dev-updates"
        
        # Verify statistics
        stats = integrator.get_integration_stats()
        assert stats["notifications_processed"] == 1
        assert stats["notifications_sent"] == 1
        assert stats["success_rate"] == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])