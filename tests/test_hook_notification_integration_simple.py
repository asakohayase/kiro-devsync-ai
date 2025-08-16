"""
Simple integration test for Agent Hook notification processing.

Tests the integration layer without importing complex hook implementations
that have configuration dependencies.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from devsync_ai.core.agent_hooks import (
    AgentHook,
    EnrichedEvent,
    HookExecutionResult,
    HookStatus,
    EventCategory,
    UrgencyLevel,
    SignificanceLevel,
    EventClassification,
    Stakeholder,
    HookConfiguration
)
from devsync_ai.core.hook_notification_integration import (
    HookNotificationIntegrator,
    HookNotificationMapper,
    HookNotificationType,
    default_hook_notification_integrator
)
from devsync_ai.core.enhanced_notification_handler import (
    ProcessingResult,
    ProcessingDecision,
    EnhancedNotificationHandler
)


class MockStatusChangeHook(AgentHook):
    """Mock implementation of StatusChangeHook for testing."""
    
    async def can_handle(self, event: EnrichedEvent) -> bool:
        """Check if this hook can handle the event."""
        return (event.classification and 
                event.classification.category == EventCategory.STATUS_CHANGE)
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """Execute the hook with integration."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Simulate hook processing
            await asyncio.sleep(0.01)  # Simulate processing time
            
            # Create execution result
            execution_result = HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="mock-exec-123",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.SUCCESS,
                execution_time_ms=10.0,
                notification_sent=False,
                metadata={
                    "transition_type": "forward",
                    "sprint_impact": False,
                    "workload_impact": False
                }
            )
            
            # Process through integration layer
            notification_result = await default_hook_notification_integrator.process_hook_notification(
                hook_id=self.hook_id,
                hook_type=self.hook_type,
                event=event,
                execution_result=execution_result,
                notification_type=HookNotificationType.JIRA_STATUS_CHANGE,
                urgency_override=event.classification.urgency if event.classification else None
            )
            
            # Update execution result based on notification result
            execution_result.notification_sent = notification_result.decision.value in [
                "send_immediately", "batch_and_send"
            ]
            execution_result.notification_result = {
                "decision": notification_result.decision.value,
                "channel": notification_result.channel,
                "processing_time_ms": notification_result.processing_time_ms
            }
            
            return execution_result
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            result = HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="mock-exec-123",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.FAILED,
                execution_time_ms=execution_time,
                notification_sent=False
            )
            result.add_error(str(e))
            return result


class TestHookNotificationIntegrationSimple:
    """Test the hook notification integration with mock hooks."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create test hook configuration
        self.hook_config = HookConfiguration(
            hook_id="test-status-hook",
            hook_type="MockStatusChangeHook",
            team_id="dev-team",
            enabled=True,
            conditions=[],
            notification_channels=["#dev-updates"],
            rate_limit_per_hour=100,
            retry_attempts=3,
            timeout_seconds=30
        )
        
        # Create test event
        self.test_event = EnrichedEvent(
            event_id="jira-event-456",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "issue": {
                    "key": "DEV-456",
                    "fields": {
                        "summary": "Fix authentication bug",
                        "priority": {"name": "High"},
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
                "summary": "Fix authentication bug",
                "priority": "High",
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
                    team_id="dev-team"
                )
            ],
            classification=EventClassification(
                category=EventCategory.STATUS_CHANGE,
                urgency=UrgencyLevel.HIGH,
                significance=SignificanceLevel.MAJOR,
                affected_teams=["dev-team"],
                routing_hints={"priority": "high"},
                keywords=["status", "change", "authentication"]
            ),
            context_data={
                "processor_data": {
                    "field_changes": [
                        {"field_name": "status", "old_value": "To Do", "new_value": "In Progress"}
                    ],
                    "is_blocked": False
                },
                "sprint_context": {"sprint_name": "Sprint 24"},
                "assignee_info": {"assignee_name": "Alice Johnson"}
            }
        )
    
    @pytest.mark.asyncio
    async def test_mock_hook_integration_success(self):
        """Test successful integration with mock hook."""
        
        # Create mock hook
        mock_hook = MockStatusChangeHook("test-status-hook", self.hook_config)
        
        # Mock the notification handler
        with patch.object(default_hook_notification_integrator, 'notification_handler') as mock_handler:
            mock_result = ProcessingResult(
                decision=ProcessingDecision.SEND_IMMEDIATELY,
                channel="#dev-updates",
                processing_time_ms=75.0
            )
            mock_handler.process_notification = AsyncMock(return_value=mock_result)
            
            # Execute the hook
            result = await mock_hook.execute(self.test_event)
            
            # Verify hook execution was successful
            assert result.status == HookStatus.SUCCESS
            assert result.hook_type == "MockStatusChangeHook"
            assert result.event_id == "jira-event-456"
            assert result.notification_sent == True
            
            # Verify notification result was captured
            assert result.notification_result is not None
            assert result.notification_result["decision"] == "send_immediately"
            assert result.notification_result["channel"] == "#dev-updates"
            
            # Verify the notification handler was called
            mock_handler.process_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mock_hook_integration_batched(self):
        """Test integration when notification gets batched."""
        
        # Create mock hook
        mock_hook = MockStatusChangeHook("test-status-hook", self.hook_config)
        
        # Mock the notification handler to return batched decision
        with patch.object(default_hook_notification_integrator, 'notification_handler') as mock_handler:
            mock_result = ProcessingResult(
                decision=ProcessingDecision.BATCH_AND_SEND,
                channel="#dev-updates",
                processing_time_ms=45.0,
                reason="added_to_batch"
            )
            mock_handler.process_notification = AsyncMock(return_value=mock_result)
            
            # Execute the hook
            result = await mock_hook.execute(self.test_event)
            
            # Verify hook execution was successful and notification was batched
            assert result.status == HookStatus.SUCCESS
            assert result.notification_sent == True  # Batched still counts as sent
            assert result.notification_result["decision"] == "batch_and_send"
    
    @pytest.mark.asyncio
    async def test_mock_hook_integration_filtered(self):
        """Test integration when notification gets filtered out."""
        
        # Create mock hook
        mock_hook = MockStatusChangeHook("test-status-hook", self.hook_config)
        
        # Mock the notification handler to return filtered decision
        with patch.object(default_hook_notification_integrator, 'notification_handler') as mock_handler:
            mock_result = ProcessingResult(
                decision=ProcessingDecision.FILTER_OUT,
                reason="filtered_by_rules",
                processing_time_ms=15.0
            )
            mock_handler.process_notification = AsyncMock(return_value=mock_result)
            
            # Execute the hook
            result = await mock_hook.execute(self.test_event)
            
            # Verify hook execution was successful but notification was filtered
            assert result.status == HookStatus.SUCCESS
            assert result.notification_sent == False  # Filtered notifications don't count as sent
            assert result.notification_result["decision"] == "filter_out"
    
    @pytest.mark.asyncio
    async def test_mock_hook_can_handle_logic(self):
        """Test hook can_handle logic."""
        
        # Create mock hook
        mock_hook = MockStatusChangeHook("test-status-hook", self.hook_config)
        
        # Test with status change event
        assert await mock_hook.can_handle(self.test_event) == True
        
        # Test with non-status change event
        non_status_event = self.test_event
        non_status_event.classification.category = EventCategory.COMMENT
        assert await mock_hook.can_handle(non_status_event) == False
    
    @pytest.mark.asyncio
    async def test_integration_statistics_tracking(self):
        """Test that integration statistics are properly tracked."""
        
        # Reset integrator stats
        default_hook_notification_integrator.reset_stats()
        
        # Create mock hook
        mock_hook = MockStatusChangeHook("test-status-hook", self.hook_config)
        
        # Mock the notification handler
        with patch.object(default_hook_notification_integrator, 'notification_handler') as mock_handler:
            mock_result = ProcessingResult(
                decision=ProcessingDecision.SEND_IMMEDIATELY,
                channel="#dev-updates",
                processing_time_ms=75.0
            )
            mock_handler.process_notification = AsyncMock(return_value=mock_result)
            
            # Execute the hook multiple times
            for i in range(3):
                await mock_hook.execute(self.test_event)
            
            # Check integration statistics
            stats = default_hook_notification_integrator.get_integration_stats()
            assert stats["notifications_processed"] == 3
            assert stats["notifications_sent"] == 3
            assert stats["success_rate"] == 100.0
            assert stats["sent_rate"] == 100.0
    
    @pytest.mark.asyncio
    async def test_integration_error_handling(self):
        """Test integration error handling."""
        
        # Create mock hook
        mock_hook = MockStatusChangeHook("test-status-hook", self.hook_config)
        
        # Mock the notification handler to raise an exception
        with patch.object(default_hook_notification_integrator, 'notification_handler') as mock_handler:
            mock_handler.process_notification = AsyncMock(side_effect=Exception("Integration error"))
            
            # Execute the hook
            result = await mock_hook.execute(self.test_event)
            
            # Verify hook execution failed due to integration error
            assert result.status == HookStatus.FAILED
            assert result.notification_sent == False
            assert len(result.errors) > 0
            assert "Integration error" in result.errors[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])