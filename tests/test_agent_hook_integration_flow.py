"""
Integration test for the complete Agent Hook to Notification flow.

Tests the end-to-end integration between JIRA Agent Hooks and the Enhanced
Notification Handler through the hook notification integration layer.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from devsync_ai.core.agent_hooks import (
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
# Import will be done with mocking to avoid config dependencies
from devsync_ai.core.hook_notification_integration import (
    default_hook_notification_integrator,
    HookNotificationType
)
from devsync_ai.core.enhanced_notification_handler import (
    ProcessingResult,
    ProcessingDecision
)


class TestAgentHookIntegrationFlow:
    """Test the complete flow from Agent Hook execution to notification processing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create test hook configuration
        self.hook_config = HookConfiguration(
            hook_id="test-status-hook",
            hook_type="StatusChangeHook",
            team_id="dev-team",
            enabled=True,
            conditions=[],
            notification_channels=["#dev-updates"],
            rate_limit_per_hour=100,
            retry_attempts=3,
            timeout_seconds=30
        )
        
        # Create test event with status change
        self.status_change_event = EnrichedEvent(
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
        
        # Create blocker event
        self.blocker_event = EnrichedEvent(
            event_id="jira-event-789",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "issue": {
                    "key": "DEV-789",
                    "fields": {
                        "summary": "Critical payment processing issue",
                        "priority": {"name": "Critical"},
                        "status": {"name": "Blocked"},
                        "assignee": {"displayName": "Charlie Brown"},
                        "reporter": {"displayName": "Diana Prince"}
                    }
                }
            },
            ticket_key="DEV-789",
            project_key="DEV",
            raw_payload={"webhookEvent": "jira:issue_updated"},
            ticket_details={
                "summary": "Critical payment processing issue",
                "priority": "Critical",
                "status": "Blocked",
                "assignee": {"displayName": "Charlie Brown"},
                "reporter": {"displayName": "Diana Prince"}
            },
            stakeholders=[
                Stakeholder(
                    user_id="cbrown",
                    display_name="Charlie Brown",
                    email="charlie.brown@company.com",
                    role="assignee",
                    team_id="payments-team"
                )
            ],
            classification=EventClassification(
                category=EventCategory.BLOCKER,
                urgency=UrgencyLevel.CRITICAL,
                significance=SignificanceLevel.CRITICAL,
                affected_teams=["payments-team"],
                routing_hints={"priority": "critical", "component": "payments"},
                keywords=["blocker", "critical", "payment"]
            ),
            context_data={
                "processor_data": {
                    "field_changes": [
                        {"field_name": "status", "old_value": "In Progress", "new_value": "Blocked"}
                    ],
                    "is_blocked": True
                },
                "sprint_context": {"sprint_name": "Sprint 24"},
                "assignee_info": {"assignee_name": "Charlie Brown"}
            }
        )
    
    @pytest.mark.asyncio
    async def test_status_change_hook_integration(self):
        """Test StatusChangeHook integration with notification system."""
        
        # Mock the hook imports to avoid config dependencies
        with patch.dict('sys.modules', {
            'devsync_ai.services.slack': Mock(),
            'devsync_ai.config': Mock(),
            'devsync_ai.templates.jira_templates': Mock()
        }):
            from devsync_ai.hooks.jira_agent_hooks import StatusChangeHook
            
            # Create status change hook
            status_hook = StatusChangeHook("test-status-hook", self.hook_config)
        
        # Mock the notification integrator to capture the call
        with patch.object(default_hook_notification_integrator, 'process_hook_notification') as mock_process:
            mock_result = ProcessingResult(
                decision=ProcessingDecision.SEND_IMMEDIATELY,
                channel="#dev-updates",
                processing_time_ms=85.0
            )
            mock_process.return_value = mock_result
            
            # Execute the hook
            result = await status_hook.execute(self.status_change_event)
            
            # Verify hook execution was successful
            assert result.status == HookStatus.SUCCESS
            assert result.hook_type == "StatusChangeHook"
            assert result.event_id == "jira-event-456"
            assert result.notification_sent == True
            
            # Verify the integration was called
            mock_process.assert_called_once()
            call_args = mock_process.call_args
            
            # Check the arguments passed to the integrator
            assert call_args[1]["hook_id"] == "test-status-hook"
            assert call_args[1]["hook_type"] == "StatusChangeHook"
            assert call_args[1]["event"] == self.status_change_event
            assert call_args[1]["notification_type"] == HookNotificationType.JIRA_STATUS_CHANGE
            
            # Check execution result metadata
            execution_result = call_args[1]["execution_result"]
            assert "transition_type" in execution_result.metadata
            assert "sprint_impact" in execution_result.metadata
            assert "workload_impact" in execution_result.metadata
    
    @pytest.mark.asyncio
    async def test_blocker_hook_integration(self):
        """Test BlockerHook integration with notification system."""
        
        # Create blocker hook
        blocker_config = HookConfiguration(
            hook_id="test-blocker-hook",
            hook_type="BlockerHook",
            team_id="payments-team",
            enabled=True,
            conditions=[],
            notification_channels=["#blockers", "#critical-alerts"],
            rate_limit_per_hour=50,
            retry_attempts=5,
            timeout_seconds=60
        )
        blocker_hook = BlockerHook("test-blocker-hook", blocker_config)
        
        # Mock the notification integrator
        with patch.object(default_hook_notification_integrator, 'process_hook_notification') as mock_process:
            mock_result = ProcessingResult(
                decision=ProcessingDecision.SEND_IMMEDIATELY,
                channel="#critical-alerts",
                processing_time_ms=120.0
            )
            mock_process.return_value = mock_result
            
            # Execute the hook
            result = await blocker_hook.execute(self.blocker_event)
            
            # Verify hook execution was successful
            assert result.status == HookStatus.SUCCESS
            assert result.hook_type == "BlockerHook"
            assert result.event_id == "jira-event-789"
            assert result.notification_sent == True
            
            # Verify the integration was called
            mock_process.assert_called_once()
            call_args = mock_process.call_args
            
            # Check the arguments passed to the integrator
            assert call_args[1]["hook_id"] == "test-blocker-hook"
            assert call_args[1]["hook_type"] == "BlockerHook"
            assert call_args[1]["event"] == self.blocker_event
            assert call_args[1]["notification_type"] == HookNotificationType.JIRA_BLOCKER_DETECTED
            assert call_args[1]["urgency_override"] == UrgencyLevel.CRITICAL
            
            # Check execution result metadata
            execution_result = call_args[1]["execution_result"]
            assert "blocker_type" in execution_result.metadata
            assert "severity" in execution_result.metadata
            assert "escalation_required" in execution_result.metadata
            assert "sprint_risk" in execution_result.metadata
    
    @pytest.mark.asyncio
    async def test_hook_integration_with_batching(self):
        """Test hook integration when notification gets batched."""
        
        # Create status change hook
        status_hook = StatusChangeHook("test-status-hook", self.hook_config)
        
        # Mock the notification integrator to return batched decision
        with patch.object(default_hook_notification_integrator, 'process_hook_notification') as mock_process:
            mock_result = ProcessingResult(
                decision=ProcessingDecision.BATCH_AND_SEND,
                channel="#dev-updates",
                processing_time_ms=45.0,
                reason="added_to_batch"
            )
            mock_process.return_value = mock_result
            
            # Execute the hook
            result = await status_hook.execute(self.status_change_event)
            
            # Verify hook execution was successful but notification was batched
            assert result.status == HookStatus.SUCCESS
            assert result.notification_sent == True  # Batched still counts as sent
            
            # Verify the integration was called
            mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_hook_integration_with_filtering(self):
        """Test hook integration when notification gets filtered out."""
        
        # Create status change hook
        status_hook = StatusChangeHook("test-status-hook", self.hook_config)
        
        # Mock the notification integrator to return filtered decision
        with patch.object(default_hook_notification_integrator, 'process_hook_notification') as mock_process:
            mock_result = ProcessingResult(
                decision=ProcessingDecision.FILTER_OUT,
                reason="filtered_by_rules",
                processing_time_ms=15.0
            )
            mock_process.return_value = mock_result
            
            # Execute the hook
            result = await status_hook.execute(self.status_change_event)
            
            # Verify hook execution was successful but notification was filtered
            assert result.status == HookStatus.SUCCESS
            assert result.notification_sent == False  # Filtered notifications don't count as sent
            
            # Verify the integration was called
            mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_hook_integration_fallback_on_error(self):
        """Test hook integration fallback when integration layer fails."""
        
        # Create status change hook
        status_hook = StatusChangeHook("test-status-hook", self.hook_config)
        
        # Mock the notification integrator to raise an exception
        with patch.object(default_hook_notification_integrator, 'process_hook_notification') as mock_process:
            mock_process.side_effect = Exception("Integration layer error")
            
            # Mock the fallback notification system
            with patch('devsync_ai.hooks.jira_agent_hooks.default_notification_system') as mock_fallback:
                mock_fallback_result = ProcessingResult(
                    decision=ProcessingDecision.SEND_IMMEDIATELY,
                    channel="#dev-updates",
                    processing_time_ms=200.0
                )
                mock_fallback.handler.process_notification.return_value = mock_fallback_result
                
                # Execute the hook
                result = await status_hook.execute(self.status_change_event)
                
                # Verify hook execution was successful using fallback
                assert result.status == HookStatus.SUCCESS
                assert result.notification_sent == True
                
                # Verify both integration and fallback were called
                mock_process.assert_called_once()
                mock_fallback.handler.process_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_hook_can_handle_logic(self):
        """Test hook can_handle logic for different event types."""
        
        # Create hooks
        status_hook = StatusChangeHook("status-hook", self.hook_config)
        blocker_hook = BlockerHook("blocker-hook", self.hook_config)
        
        # Test status change hook
        assert await status_hook.can_handle(self.status_change_event) == True
        assert await status_hook.can_handle(self.blocker_event) == False  # Blocker is not status change
        
        # Test blocker hook
        assert await blocker_hook.can_handle(self.blocker_event) == True
        assert await blocker_hook.can_handle(self.status_change_event) == False  # Status change is not blocker
    
    @pytest.mark.asyncio
    async def test_hook_integration_metadata_propagation(self):
        """Test that hook metadata is properly propagated through the integration."""
        
        # Create status change hook
        status_hook = StatusChangeHook("test-status-hook", self.hook_config)
        
        # Mock the notification integrator to capture metadata
        with patch.object(default_hook_notification_integrator, 'process_hook_notification') as mock_process:
            mock_result = ProcessingResult(
                decision=ProcessingDecision.SEND_IMMEDIATELY,
                channel="#dev-updates",
                processing_time_ms=75.0
            )
            mock_process.return_value = mock_result
            
            # Execute the hook
            await status_hook.execute(self.status_change_event)
            
            # Verify metadata was passed correctly
            call_args = mock_process.call_args
            metadata = call_args[1]["metadata"]
            
            # Check that hook-specific metadata is included
            assert "transition_indicator" in metadata
            assert "channels_suggested" in metadata
            
            # Check execution result metadata
            execution_result = call_args[1]["execution_result"]
            assert execution_result.metadata["transition_type"] is not None
            assert "sprint_impact" in execution_result.metadata
            assert "workload_impact" in execution_result.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])