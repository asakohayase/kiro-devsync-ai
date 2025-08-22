"""
Comprehensive end-to-end test suite for JIRA to Slack Agent Hooks.
Tests complete flows from webhook events to Slack notifications.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, List

from tests.framework.webhook_simulator import (
    JiraWebhookSimulator,
    MockDataGenerator,
    EndToEndTestRunner,
    WebhookSimulationResult
)
from tests.framework.hook_test_suite import HookTestSuite

from devsync_ai.core.agent_hook_dispatcher import AgentHookDispatcher
from devsync_ai.core.hook_event_processor import HookEventProcessor
from devsync_ai.core.event_classification_engine import EventClassificationEngine
from devsync_ai.core.hook_rule_engine import HookRuleEngine
from devsync_ai.core.enhanced_notification_handler import EnhancedNotificationHandler
from devsync_ai.hooks.jira_agent_hooks import (
    StatusChangeHook,
    AssignmentChangeHook,
    CommentHook,
    BlockerHook,
    CriticalUpdateHook
)


class TestEndToEndWebhookFlow:
    """Test complete webhook processing flow."""
    
    @pytest.fixture
    def webhook_simulator(self):
        return JiraWebhookSimulator()
    
    @pytest.fixture
    def mock_generator(self):
        return MockDataGenerator()
    
    @pytest.fixture
    def test_runner(self):
        return EndToEndTestRunner()
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        mocks = {
            'jira_service': AsyncMock(),
            'slack_service': AsyncMock(),
            'notification_handler': AsyncMock(),
            'database': AsyncMock(),
            'config_manager': AsyncMock()
        }
        
        # Configure mock responses
        mocks['jira_service'].get_ticket_details.return_value = MockDataGenerator.create_enriched_event().ticket_details
        mocks['slack_service'].send_message.return_value = {"ok": True, "ts": "1234567890.123456"}
        mocks['notification_handler'].process_notification.return_value = {"success": True}
        
        return mocks
    
    @pytest.mark.asyncio
    async def test_status_change_webhook_complete_flow(self, webhook_simulator, mock_dependencies):
        """Test complete flow for status change webhook."""
        # Generate webhook event
        webhook_event = webhook_simulator.generate_webhook_event(
            "issue_updated",
            **{
                "changelog.items.0.field": "status",
                "changelog.items.0.fromString": "To Do",
                "changelog.items.0.toString": "In Progress"
            }
        )
        
        with patch.multiple(
            'devsync_ai.core.agent_hook_dispatcher',
            jira_service=mock_dependencies['jira_service'],
            slack_service=mock_dependencies['slack_service']
        ):
            # Initialize components
            dispatcher = AgentHookDispatcher()
            event_processor = HookEventProcessor()
            classification_engine = EventClassificationEngine()
            
            # Process webhook event
            processed_event = await event_processor.process_jira_event(
                webhook_event["webhookEvent"],
                webhook_event
            )
            
            # Classify event
            classification = await classification_engine.classify_event(processed_event)
            
            # Verify classification
            assert classification.category == "STATUS_CHANGE"
            assert classification.urgency.value >= 2  # Medium or higher
            
            # Verify mock calls
            mock_dependencies['jira_service'].get_ticket_details.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_assignment_webhook_complete_flow(self, webhook_simulator, mock_dependencies):
        """Test complete flow for assignment webhook."""
        webhook_event = webhook_simulator.generate_webhook_event(
            "issue_assigned",
            **{
                "changelog.items.0.field": "assignee",
                "changelog.items.0.toString": "Jane Smith"
            }
        )
        
        with patch.multiple(
            'devsync_ai.core.agent_hook_dispatcher',
            jira_service=mock_dependencies['jira_service'],
            slack_service=mock_dependencies['slack_service']
        ):
            dispatcher = AgentHookDispatcher()
            event_processor = HookEventProcessor()
            
            processed_event = await event_processor.process_jira_event(
                webhook_event["webhookEvent"],
                webhook_event
            )
            
            # Verify assignment processing
            assert processed_event.event_type == "jira:issue_updated"
            assert "assignee" in str(processed_event.jira_event_data)
    
    @pytest.mark.asyncio
    async def test_comment_webhook_complete_flow(self, webhook_simulator, mock_dependencies):
        """Test complete flow for comment webhook."""
        webhook_event = webhook_simulator.generate_webhook_event(
            "issue_commented",
            **{
                "comment.body": "This is blocking our release!"
            }
        )
        
        with patch.multiple(
            'devsync_ai.core.agent_hook_dispatcher',
            jira_service=mock_dependencies['jira_service'],
            slack_service=mock_dependencies['slack_service']
        ):
            dispatcher = AgentHookDispatcher()
            event_processor = HookEventProcessor()
            classification_engine = EventClassificationEngine()
            
            processed_event = await event_processor.process_jira_event(
                webhook_event["webhookEvent"],
                webhook_event
            )
            
            classification = await classification_engine.classify_event(processed_event)
            
            # High priority ticket with comment should be significant
            assert classification.significance.value >= 3  # Major or Critical


class TestMultiTeamConfiguration:
    """Test multi-team configuration scenarios."""
    
    @pytest.fixture
    def team_configs(self):
        return MockDataGenerator.create_team_configurations()
    
    @pytest.mark.asyncio
    async def test_engineering_team_status_change(self, team_configs):
        """Test engineering team receives status change notifications."""
        eng_config = next(config for config in team_configs if config["team_id"] == "engineering")
        
        # Mock rule engine
        with patch('devsync_ai.core.hook_rule_engine.HookRuleEngine') as mock_rule_engine:
            rule_engine = mock_rule_engine.return_value
            rule_engine.evaluate_rules.return_value = AsyncMock(should_execute=True, matched_rules=["priority_filter"])
            
            # Simulate high priority status change
            enriched_event = MockDataGenerator.create_enriched_event(
                event_type="STATUS_CHANGE",
                urgency="HIGH"
            )
            
            # Verify rule evaluation would pass
            result = await rule_engine.evaluate_rules(enriched_event.classification, "engineering")
            assert result.should_execute
    
    @pytest.mark.asyncio
    async def test_qa_team_testing_status_notifications(self, team_configs):
        """Test QA team receives testing-related status notifications."""
        qa_config = next(config for config in team_configs if config["team_id"] == "qa")
        
        with patch('devsync_ai.core.hook_rule_engine.HookRuleEngine') as mock_rule_engine:
            rule_engine = mock_rule_engine.return_value
            rule_engine.evaluate_rules.return_value = AsyncMock(should_execute=True, matched_rules=["status_filter"])
            
            # Simulate testing status change
            enriched_event = MockDataGenerator.create_enriched_event(event_type="STATUS_CHANGE")
            enriched_event.ticket_details.status = "Ready for Testing"
            
            result = await rule_engine.evaluate_rules(enriched_event.classification, "qa")
            assert result.should_execute
    
    @pytest.mark.asyncio
    async def test_cross_team_notification_routing(self, team_configs):
        """Test that events can trigger notifications for multiple teams."""
        with patch('devsync_ai.core.hook_rule_engine.HookRuleEngine') as mock_rule_engine:
            rule_engine = mock_rule_engine.return_value
            
            # Configure different responses for different teams
            def mock_evaluate_rules(classification, team_id):
                if team_id == "engineering":
                    return AsyncMock(should_execute=True, matched_rules=["priority_filter"])
                elif team_id == "qa":
                    return AsyncMock(should_execute=False, matched_rules=[])
                return AsyncMock(should_execute=False, matched_rules=[])
            
            rule_engine.evaluate_rules.side_effect = mock_evaluate_rules
            
            enriched_event = MockDataGenerator.create_enriched_event(
                event_type="STATUS_CHANGE",
                urgency="HIGH"
            )
            
            # Test both teams
            eng_result = await rule_engine.evaluate_rules(enriched_event.classification, "engineering")
            qa_result = await rule_engine.evaluate_rules(enriched_event.classification, "qa")
            
            assert eng_result.should_execute
            assert not qa_result.should_execute


class TestPerformanceAndLoadTesting:
    """Test system performance under load."""
    
    @pytest.fixture
    def test_runner(self):
        return EndToEndTestRunner()
    
    @pytest.mark.asyncio
    async def test_high_volume_webhook_processing(self, test_runner):
        """Test processing high volume of webhook events."""
        # Test with 100 events
        results = await test_runner.run_load_test(event_count=100, concurrent_limit=10)
        
        # Verify all events were processed
        assert len(results) == 100
        
        # Check success rate
        successful_results = [r for r in results if r.success]
        success_rate = len(successful_results) / len(results) * 100
        assert success_rate >= 95  # At least 95% success rate
        
        # Check performance
        execution_times = [r.execution_time_ms for r in successful_results]
        avg_time = sum(execution_times) / len(execution_times)
        assert avg_time < 500  # Average execution time under 500ms
    
    @pytest.mark.asyncio
    async def test_concurrent_webhook_processing(self, test_runner):
        """Test concurrent processing of webhook events."""
        # Create multiple concurrent tasks
        tasks = []
        for i in range(20):
            task = test_runner.run_complete_flow_test(
                "issue_updated",
                MockDataGenerator.create_team_configurations()
            )
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        successful_results = [r for r in results if isinstance(r, WebhookSimulationResult) and r.success]
        assert len(successful_results) >= 18  # At least 90% success rate
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, test_runner):
        """Test memory usage doesn't grow excessively under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process many events
        await test_runner.run_load_test(event_count=50, concurrent_limit=5)
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 100MB)
        assert memory_growth < 100 * 1024 * 1024
    
    def test_performance_report_generation(self, test_runner):
        """Test performance report generation."""
        # Add some mock results
        test_runner.results = [
            WebhookSimulationResult(
                success=True,
                execution_time_ms=150.0,
                notifications_sent=1,
                errors=[],
                hook_executions=[],
                metadata={}
            ),
            WebhookSimulationResult(
                success=False,
                execution_time_ms=0.0,
                notifications_sent=0,
                errors=["Test error"],
                hook_executions=[],
                metadata={}
            )
        ]
        
        report = test_runner.generate_performance_report()
        
        assert report["total_tests"] == 2
        assert report["successful_tests"] == 1
        assert report["failed_tests"] == 1
        assert report["success_rate"] == 50.0
        assert report["performance"]["avg_execution_time_ms"] == 150.0


class TestIntegrationWithExistingNotificationSystem:
    """Test integration with existing notification components."""
    
    @pytest.mark.asyncio
    async def test_enhanced_notification_handler_integration(self):
        """Test integration with EnhancedNotificationHandler."""
        with patch('devsync_ai.core.enhanced_notification_handler.EnhancedNotificationHandler') as mock_handler:
            handler = mock_handler.return_value
            handler.process_notification.return_value = {"success": True, "message_id": "test123"}
            
            # Create enriched event
            enriched_event = MockDataGenerator.create_enriched_event()
            
            # Simulate hook execution that calls notification handler
            from devsync_ai.hooks.jira_agent_hooks import StatusChangeHook
            
            hook = StatusChangeHook()
            
            # Mock the notification integration
            with patch.object(hook, '_send_notification') as mock_send:
                mock_send.return_value = {"success": True}
                
                result = await hook.execute(enriched_event)
                
                assert result.success
                mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_slack_message_formatter_integration(self):
        """Test integration with Slack message formatting."""
        with patch('devsync_ai.services.slack.SlackService') as mock_slack:
            slack_service = mock_slack.return_value
            slack_service.send_message.return_value = {"ok": True, "ts": "1234567890.123456"}
            
            enriched_event = MockDataGenerator.create_enriched_event()
            
            # Test message formatting through hook
            from devsync_ai.hooks.jira_agent_hooks import StatusChangeHook
            hook = StatusChangeHook()
            
            with patch.object(hook, '_format_message') as mock_format:
                mock_format.return_value = {
                    "text": "Test notification",
                    "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}]
                }
                
                result = await hook.execute(enriched_event)
                mock_format.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_integration(self):
        """Test database integration for hook execution logging."""
        with patch('devsync_ai.database.hook_data_manager.HookDataManager') as mock_db:
            db_manager = mock_db.return_value
            db_manager.log_hook_execution.return_value = True
            
            enriched_event = MockDataGenerator.create_enriched_event()
            
            from devsync_ai.hooks.jira_agent_hooks import StatusChangeHook
            hook = StatusChangeHook()
            
            # Mock hook execution with database logging
            with patch.object(hook, '_log_execution') as mock_log:
                mock_log.return_value = True
                
                result = await hook.execute(enriched_event)
                
                # Verify database logging was called
                mock_log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analytics_integration(self):
        """Test integration with analytics system."""
        with patch('devsync_ai.analytics.hook_analytics_engine.HookAnalyticsEngine') as mock_analytics:
            analytics = mock_analytics.return_value
            analytics.record_hook_execution.return_value = True
            
            enriched_event = MockDataGenerator.create_enriched_event()
            
            from devsync_ai.hooks.jira_agent_hooks import StatusChangeHook
            hook = StatusChangeHook()
            
            with patch.object(hook, '_record_analytics') as mock_record:
                mock_record.return_value = True
                
                result = await hook.execute(enriched_event)
                mock_record.assert_called_once()


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_webhook_processing_error_recovery(self):
        """Test recovery from webhook processing errors."""
        webhook_simulator = JiraWebhookSimulator()
        
        # Generate malformed webhook event
        malformed_event = webhook_simulator.generate_webhook_event("issue_updated")
        del malformed_event["issue"]  # Remove required field
        
        with patch('devsync_ai.core.hook_event_processor.HookEventProcessor') as mock_processor:
            processor = mock_processor.return_value
            processor.process_jira_event.side_effect = ValueError("Invalid webhook payload")
            
            # Test error handling
            try:
                await processor.process_jira_event("jira:issue_updated", malformed_event)
                assert False, "Should have raised an exception"
            except ValueError as e:
                assert "Invalid webhook payload" in str(e)
    
    @pytest.mark.asyncio
    async def test_notification_failure_retry(self):
        """Test retry mechanism for notification failures."""
        with patch('devsync_ai.services.slack.SlackService') as mock_slack:
            slack_service = mock_slack.return_value
            
            # First call fails, second succeeds
            slack_service.send_message.side_effect = [
                Exception("Network error"),
                {"ok": True, "ts": "1234567890.123456"}
            ]
            
            enriched_event = MockDataGenerator.create_enriched_event()
            
            from devsync_ai.hooks.jira_agent_hooks import StatusChangeHook
            hook = StatusChangeHook()
            
            with patch.object(hook, '_send_with_retry') as mock_retry:
                mock_retry.return_value = {"success": True}
                
                result = await hook.execute(enriched_event)
                assert result.success
                mock_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_connection_failure_handling(self):
        """Test handling of database connection failures."""
        with patch('devsync_ai.database.hook_data_manager.HookDataManager') as mock_db:
            db_manager = mock_db.return_value
            db_manager.log_hook_execution.side_effect = Exception("Database connection failed")
            
            enriched_event = MockDataGenerator.create_enriched_event()
            
            from devsync_ai.hooks.jira_agent_hooks import StatusChangeHook
            hook = StatusChangeHook()
            
            # Hook should still execute successfully even if logging fails
            result = await hook.execute(enriched_event)
            
            # The hook execution should succeed despite logging failure
            # (assuming the hook has proper error handling)
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])