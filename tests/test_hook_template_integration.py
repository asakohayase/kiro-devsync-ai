"""
Tests for hook template integration with the existing template system.

This module tests the integration between Agent Hooks and the SlackMessageFormatterFactory,
ensuring that hook-specific templates work correctly and fallback mechanisms function properly.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from devsync_ai.core.hook_template_integration import (
    HookTemplateIntegrator,
    HookFormattingContext,
    get_hook_template_integrator,
    format_hook_message
)
from devsync_ai.core.hook_template_fallback import (
    HookTemplateFallbackHandler,
    FallbackContext,
    FallbackStrategy,
    FallbackTrigger
)
from devsync_ai.core.formatter_factory import (
    SlackMessageFormatterFactory,
    FormatterOptions,
    ProcessingResult
)
from devsync_ai.core.message_formatter import SlackMessage, TemplateConfig
from devsync_ai.core.agent_hooks import (
    EnrichedEvent,
    HookExecutionResult,
    HookStatus,
    EventCategory,
    UrgencyLevel,
    EventClassification
)
from devsync_ai.formatters.hook_message_formatter import HookMessageFormatter
from devsync_ai.templates.hook_templates import HookStatusChangeTemplate


class TestHookTemplateIntegrator:
    """Test the HookTemplateIntegrator class."""
    
    @pytest.fixture
    def formatter_factory(self):
        """Create a mock formatter factory."""
        return Mock(spec=SlackMessageFormatterFactory)
    
    @pytest.fixture
    def integrator(self, formatter_factory):
        """Create a HookTemplateIntegrator instance."""
        return HookTemplateIntegrator(formatter_factory)
    
    @pytest.fixture
    def sample_event(self):
        """Create a sample enriched event."""
        classification = EventClassification(
            category=EventCategory.STATUS_CHANGE,
            urgency=UrgencyLevel.MEDIUM,
            significance=UrgencyLevel.MEDIUM,
            affected_teams=['dev-team'],
            routing_hints={'channel': '#dev-updates'}
        )
        
        return EnrichedEvent(
            event_id="test-event-123",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={'issue': {'key': 'TEST-123'}},
            ticket_key="TEST-123",
            project_key="TEST",
            raw_payload={},
            ticket_details={
                'key': 'TEST-123',
                'summary': 'Test ticket summary',
                'status': 'In Progress',
                'priority': 'Medium',
                'assignee': 'john.doe'
            },
            classification=classification,
            context_data={
                'processor_data': {
                    'field_changes': [
                        Mock(field_name='status', old_value='To Do', new_value='In Progress')
                    ]
                }
            }
        )
    
    @pytest.fixture
    def sample_execution_result(self):
        """Create a sample hook execution result."""
        return HookExecutionResult(
            hook_id="status-change-hook-1",
            execution_id="exec-123",
            hook_type="StatusChangeHook",
            event_id="test-event-123",
            status=HookStatus.SUCCESS,
            execution_time_ms=150.0,
            notification_sent=True,
            metadata={
                'transition_type': 'forward',
                'from_status': 'To Do',
                'to_status': 'In Progress',
                'urgency': 'medium'
            }
        )
    
    def test_integrator_initialization(self, formatter_factory):
        """Test integrator initialization."""
        integrator = HookTemplateIntegrator(formatter_factory)
        
        assert integrator.formatter_factory == formatter_factory
        assert isinstance(integrator.hook_formatter, HookMessageFormatter)
        assert integrator.enable_fallback is True
        assert integrator.fallback_to_jira_templates is True
    
    def test_format_hook_message_success(self, integrator, sample_event, sample_execution_result):
        """Test successful hook message formatting."""
        context = HookFormattingContext(
            hook_type="StatusChangeHook",
            event=sample_event,
            execution_result=sample_execution_result
        )
        
        with patch.object(integrator, '_format_with_hook_templates') as mock_format:
            mock_format.return_value = ProcessingResult(
                success=True,
                message=SlackMessage(
                    blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Test message"}}],
                    text="Test message"
                ),
                formatter_used="HookMessageFormatter"
            )
            
            result = integrator.format_hook_message(context)
            
            assert result.success is True
            assert result.message is not None
            assert result.formatter_used == "HookMessageFormatter"
            mock_format.assert_called_once()
    
    def test_format_hook_message_with_fallback(self, integrator, sample_event, sample_execution_result):
        """Test hook message formatting with fallback."""
        context = HookFormattingContext(
            hook_type="StatusChangeHook",
            event=sample_event,
            execution_result=sample_execution_result
        )
        
        # Mock hook template failure
        with patch.object(integrator, '_format_with_hook_templates') as mock_hook_format:
            mock_hook_format.return_value = ProcessingResult(
                success=False,
                error="Hook template failed"
            )
            
            # Mock successful fallback
            with patch.object(integrator, '_format_with_fallback') as mock_fallback:
                mock_fallback.return_value = ProcessingResult(
                    success=True,
                    message=SlackMessage(
                        blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Fallback message"}}],
                        text="Fallback message"
                    ),
                    formatter_used="fallback"
                )
                
                result = integrator.format_hook_message(context)
                
                assert result.success is True
                assert result.message is not None
                assert result.formatter_used == "fallback"
                mock_hook_format.assert_called_once()
                mock_fallback.assert_called_once()
    
    def test_format_hook_execution_result(self, integrator, sample_event, sample_execution_result):
        """Test formatting hook execution result."""
        with patch.object(integrator, 'format_hook_message') as mock_format:
            mock_format.return_value = ProcessingResult(success=True)
            
            result = integrator.format_hook_execution_result(
                "StatusChangeHook",
                sample_event,
                sample_execution_result
            )
            
            assert mock_format.called
            call_args = mock_format.call_args[0][0]  # First argument (HookFormattingContext)
            assert call_args.hook_type == "StatusChangeHook"
            assert call_args.event == sample_event
            assert call_args.execution_result == sample_execution_result
    
    def test_format_batch_hook_results(self, integrator):
        """Test formatting batch hook results."""
        hook_results = [
            {
                'hook_type': 'StatusChangeHook',
                'execution_result': {
                    'status': 'success',
                    'execution_time_ms': 100.0
                }
            },
            {
                'hook_type': 'AssignmentHook',
                'execution_result': {
                    'status': 'failed',
                    'execution_time_ms': 50.0,
                    'errors': ['Assignment failed']
                }
            }
        ]
        
        with patch.object(integrator.hook_formatter, 'format_batch_hook_results') as mock_batch:
            mock_batch.return_value = SlackMessage(
                blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Batch results"}}],
                text="Batch results"
            )
            
            result = integrator.format_batch_hook_results(hook_results)
            
            assert result.success is True
            assert result.message is not None
            mock_batch.assert_called_once_with(hook_results, None)
    
    def test_determine_hook_message_type(self, integrator):
        """Test hook message type determination."""
        # Test status change hook
        context = HookFormattingContext(hook_type="StatusChangeHook")
        message_type = integrator._determine_hook_message_type(context)
        assert message_type == "hook_status_change"
        
        # Test blocker hook
        context = HookFormattingContext(hook_type="BlockerHook")
        message_type = integrator._determine_hook_message_type(context)
        assert message_type == "hook_blocker_detected"
        
        # Test with execution result metadata
        execution_result = Mock()
        execution_result.metadata = {'blocker_resolved': True}
        context = HookFormattingContext(
            hook_type="BlockerHook",
            execution_result=execution_result
        )
        message_type = integrator._determine_hook_message_type(context)
        assert message_type == "hook_blocker_resolved"
    
    def test_prepare_formatting_data(self, integrator, sample_event, sample_execution_result):
        """Test formatting data preparation."""
        context = HookFormattingContext(
            hook_type="StatusChangeHook",
            event=sample_event,
            execution_result=sample_execution_result,
            additional_context={'test_key': 'test_value'}
        )
        
        data = integrator._prepare_formatting_data(context)
        
        assert data['hook_type'] == "StatusChangeHook"
        assert 'event' in data
        assert 'execution_result' in data
        assert data['additional_context']['test_key'] == 'test_value'
    
    def test_register_hook_message_types(self, integrator, formatter_factory):
        """Test registration of hook message types."""
        integrator._register_hook_message_types()
        
        # Verify that register_custom_formatter was called
        assert formatter_factory.register_custom_formatter.call_count >= 4
        
        # Check some of the registered types
        calls = formatter_factory.register_custom_formatter.call_args_list
        registered_types = [call[0][0] for call in calls]
        
        assert "hook_status_change" in registered_types
        assert "hook_blocker_detected" in registered_types
        assert "hook_assignment" in registered_types
        assert "hook_comment" in registered_types


class TestHookTemplateFallbackHandler:
    """Test the HookTemplateFallbackHandler class."""
    
    @pytest.fixture
    def fallback_handler(self):
        """Create a fallback handler instance."""
        return HookTemplateFallbackHandler()
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for fallback testing."""
        return {
            'hook_type': 'StatusChangeHook',
            'event': {
                'event_id': 'test-123',
                'ticket_key': 'TEST-123',
                'event_type': 'jira:issue_updated',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'ticket_details': {
                    'key': 'TEST-123',
                    'summary': 'Test ticket',
                    'status': 'In Progress'
                }
            },
            'execution_result': {
                'status': 'success',
                'execution_time_ms': 100.0,
                'metadata': {
                    'transition_type': 'forward'
                }
            }
        }
    
    @pytest.fixture
    def fallback_context(self):
        """Create a fallback context."""
        return FallbackContext(
            original_error=Exception("Template formatting failed"),
            trigger=FallbackTrigger.TEMPLATE_ERROR,
            hook_type="StatusChangeHook",
            urgency_level="medium"
        )
    
    def test_fallback_handler_initialization(self):
        """Test fallback handler initialization."""
        handler = HookTemplateFallbackHandler()
        
        assert len(handler.fallback_chain) == 5
        assert FallbackStrategy.BASIC_BLOCKS in handler.fallback_chain
        assert FallbackStrategy.EMERGENCY_MINIMAL in handler.fallback_chain
        assert handler.fallback_stats['total_fallbacks'] == 0
    
    def test_handle_formatting_failure_success(self, fallback_handler, sample_data, fallback_context):
        """Test successful fallback handling."""
        result = fallback_handler.handle_formatting_failure(sample_data, fallback_context)
        
        assert result.success is True
        assert result.message is not None
        assert result.message.metadata.get('fallback_used') is True
        assert fallback_handler.fallback_stats['total_fallbacks'] == 1
    
    def test_basic_blocks_fallback(self, fallback_handler, sample_data, fallback_context):
        """Test basic blocks fallback strategy."""
        result = fallback_handler._create_basic_blocks_fallback(sample_data, fallback_context)
        
        assert result.success is True
        assert result.message is not None
        assert len(result.message.blocks) >= 2  # Header + content
        assert result.message.blocks[0]['type'] == 'header'
        assert result.formatter_used == "BasicBlocksFallback"
    
    def test_jira_template_fallback(self, fallback_handler, sample_data, fallback_context):
        """Test JIRA template fallback strategy."""
        with patch('devsync_ai.formatters.jira_message_formatter.JIRAMessageFormatter') as mock_formatter_class:
            mock_formatter = Mock()
            mock_formatter.format_message.return_value = SlackMessage(
                blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "JIRA fallback"}}],
                text="JIRA fallback"
            )
            mock_formatter_class.return_value = mock_formatter
            
            result = fallback_handler._create_jira_template_fallback(sample_data, fallback_context)
            
            assert result.success is True
            assert result.formatter_used == "JIRATemplateFallback"
            mock_formatter.format_message.assert_called_once()
    
    def test_generic_hook_fallback(self, fallback_handler, sample_data, fallback_context):
        """Test generic hook fallback strategy."""
        result = fallback_handler._create_generic_hook_fallback(sample_data, fallback_context)
        
        assert result.success is True
        assert result.message is not None
        assert result.formatter_used == "GenericHookFallback"
        
        # Check that execution summary is included
        blocks = result.message.blocks
        assert any('Execution Summary' in str(block) for block in blocks)
    
    def test_simple_text_fallback(self, fallback_handler, sample_data, fallback_context):
        """Test simple text fallback strategy."""
        result = fallback_handler._create_simple_text_fallback(sample_data, fallback_context)
        
        assert result.success is True
        assert result.message is not None
        assert result.formatter_used == "SimpleTextFallback"
        assert len(result.message.blocks) == 1
        assert result.message.blocks[0]['type'] == 'section'
    
    def test_emergency_minimal_fallback(self, fallback_handler, sample_data, fallback_context):
        """Test emergency minimal fallback strategy."""
        result = fallback_handler._create_emergency_minimal_fallback(sample_data, fallback_context)
        
        assert result.success is True
        assert result.message is not None
        assert result.formatter_used == "EmergencyMinimalFallback"
        assert result.message.metadata.get('emergency_fallback') is True
    
    def test_fallback_chain_execution(self, fallback_handler, sample_data, fallback_context):
        """Test that fallback chain executes in order."""
        # Mock all strategies to fail except the last one
        with patch.object(fallback_handler, '_create_basic_blocks_fallback') as mock_basic:
            mock_basic.return_value = ProcessingResult(success=False, error="Basic blocks failed")
            
            with patch.object(fallback_handler, '_create_jira_template_fallback') as mock_jira:
                mock_jira.return_value = ProcessingResult(success=False, error="JIRA template failed")
                
                with patch.object(fallback_handler, '_create_generic_hook_fallback') as mock_generic:
                    mock_generic.return_value = ProcessingResult(success=False, error="Generic hook failed")
                    
                    with patch.object(fallback_handler, '_create_simple_text_fallback') as mock_simple:
                        mock_simple.return_value = ProcessingResult(success=False, error="Simple text failed")
                        
                        # Emergency minimal should succeed
                        result = fallback_handler.handle_formatting_failure(sample_data, fallback_context)
                        
                        assert result.success is True
                        assert result.formatter_used == "EmergencyMinimalFallback"
                        
                        # Verify all strategies were tried
                        mock_basic.assert_called_once()
                        mock_jira.assert_called_once()
                        mock_generic.assert_called_once()
                        mock_simple.assert_called_once()
    
    def test_custom_fallback_registration(self, fallback_handler):
        """Test registration of custom fallback handlers."""
        def custom_handler(data, context):
            return ProcessingResult(
                success=True,
                message=SlackMessage(
                    blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Custom fallback"}}],
                    text="Custom fallback"
                ),
                formatter_used="CustomFallback"
            )
        
        fallback_handler.register_custom_fallback(FallbackStrategy.BASIC_BLOCKS, custom_handler)
        
        assert FallbackStrategy.BASIC_BLOCKS in fallback_handler.custom_handlers
        
        # Test that custom handler is used
        sample_data = {'hook_type': 'TestHook'}
        context = FallbackContext(hook_type="TestHook")
        
        result = fallback_handler._apply_fallback_strategy(
            FallbackStrategy.BASIC_BLOCKS, sample_data, context
        )
        
        assert result.success is True
        assert result.formatter_used == "CustomFallback"
    
    def test_fallback_statistics(self, fallback_handler, sample_data, fallback_context):
        """Test fallback statistics tracking."""
        # Trigger some fallbacks
        fallback_handler.handle_formatting_failure(sample_data, fallback_context)
        fallback_handler.handle_formatting_failure(sample_data, fallback_context)
        
        stats = fallback_handler.get_fallback_statistics()
        
        assert stats['total_fallbacks'] == 2
        assert 'basic_blocks' in stats['strategy_usage']
        assert stats['trigger_counts']['template_error'] == 2
        
        # Test statistics reset
        fallback_handler.reset_statistics()
        stats = fallback_handler.get_fallback_statistics()
        assert stats['total_fallbacks'] == 0


class TestHookMessageFormatter:
    """Test the HookMessageFormatter class."""
    
    @pytest.fixture
    def formatter(self):
        """Create a hook message formatter."""
        return HookMessageFormatter()
    
    @pytest.fixture
    def sample_hook_data(self):
        """Create sample hook data."""
        return {
            'hook_type': 'StatusChangeHook',
            'event': {
                'event_id': 'test-123',
                'ticket_key': 'TEST-123',
                'ticket_details': {
                    'key': 'TEST-123',
                    'summary': 'Test ticket',
                    'status': 'In Progress'
                },
                'classification': {
                    'category': 'status_change',
                    'urgency': 'medium'
                }
            },
            'execution_result': {
                'status': 'success',
                'execution_time_ms': 100.0,
                'metadata': {
                    'transition_type': 'forward'
                }
            }
        }
    
    def test_formatter_initialization(self):
        """Test formatter initialization."""
        formatter = HookMessageFormatter()
        
        assert formatter._template_registry is not None
        assert len(formatter._template_registry) > 0
        assert formatter._template_instances == {}
    
    def test_format_message_success(self, formatter, sample_hook_data):
        """Test successful message formatting."""
        with patch.object(formatter, '_get_template_for_event_type') as mock_get_template:
            mock_template = Mock()
            mock_template.format_message.return_value = SlackMessage(
                blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Test message"}}],
                text="Test message"
            )
            mock_get_template.return_value = mock_template
            
            result = formatter.format_message(sample_hook_data)
            
            assert isinstance(result, SlackMessage)
            assert result.metadata['formatted_by'] == 'HookMessageFormatter'
            assert result.metadata['hook_type'] == 'StatusChangeHook'
    
    def test_format_hook_execution_result(self, formatter):
        """Test formatting hook execution result."""
        event = Mock(spec=EnrichedEvent)
        event.event_id = "test-123"
        event.ticket_key = "TEST-123"
        event.event_type = "jira:issue_updated"
        event.timestamp = datetime.now(timezone.utc)
        event.project_key = "TEST"
        event.raw_payload = {}
        event.ticket_details = {}
        event.classification = None
        event.context_data = {}
        
        execution_result = Mock(spec=HookExecutionResult)
        execution_result.hook_id = "hook-1"
        execution_result.status = HookStatus.SUCCESS
        execution_result.execution_id = "exec-123"
        execution_result.hook_type = "StatusChangeHook"
        execution_result.event_id = "test-123"
        execution_result.execution_time_ms = 100.0
        execution_result.notification_sent = True
        execution_result.errors = []
        execution_result.metadata = {}
        execution_result.started_at = datetime.now(timezone.utc)
        execution_result.completed_at = None
        
        with patch.object(formatter, 'format_message') as mock_format:
            mock_format.return_value = SlackMessage(
                blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}],
                text="Test"
            )
            
            result = formatter.format_hook_execution_result(
                "StatusChangeHook", event, execution_result
            )
            
            assert isinstance(result, SlackMessage)
            mock_format.assert_called_once()
    
    def test_determine_hook_event_type(self, formatter):
        """Test hook event type determination."""
        # Test status change hook
        data = {'hook_type': 'StatusChangeHook'}
        event_type = formatter._determine_hook_event_type(data)
        assert event_type.value == 'status_change'
        
        # Test blocker hook
        data = {'hook_type': 'BlockerHook'}
        event_type = formatter._determine_hook_event_type(data)
        assert event_type.value == 'blocker_detected'
        
        # Test with execution result metadata
        data = {
            'hook_type': 'BlockerHook',
            'execution_result': {
                'metadata': {'blocker_resolved': True}
            }
        }
        event_type = formatter._determine_hook_event_type(data)
        assert event_type.value == 'blocker_resolved'
    
    def test_validate_hook_data(self, formatter):
        """Test hook data validation."""
        # Valid data
        valid_data = {
            'hook_type': 'StatusChangeHook',
            'event': {'event_id': 'test-123'}
        }
        formatter._validate_hook_data(valid_data)  # Should not raise
        
        # Missing hook_type
        with pytest.raises(Exception):
            formatter._validate_hook_data({'event': {'event_id': 'test-123'}})
        
        # Missing event and execution_result
        with pytest.raises(Exception):
            formatter._validate_hook_data({'hook_type': 'StatusChangeHook'})
    
    def test_format_batch_hook_results(self, formatter):
        """Test batch hook results formatting."""
        hook_results = [
            {
                'hook_type': 'StatusChangeHook',
                'execution_result': {'status': 'success', 'execution_time_ms': 100.0}
            },
            {
                'hook_type': 'AssignmentHook',
                'execution_result': {'status': 'failed', 'errors': ['Test error']}
            }
        ]
        
        result = formatter.format_batch_hook_results(hook_results)
        
        assert isinstance(result, SlackMessage)
        assert result.metadata['message_type'] == 'hook_batch'
        assert result.metadata['total_hooks'] == 2
        assert result.metadata['successful_hooks'] == 1
        assert result.metadata['failed_hooks'] == 1


class TestIntegrationFunctions:
    """Test integration utility functions."""
    
    def test_get_hook_template_integrator(self):
        """Test getting the global integrator instance."""
        # Clear any existing instance
        import devsync_ai.core.hook_template_integration
        devsync_ai.core.hook_template_integration._hook_template_integrator = None
        
        integrator1 = get_hook_template_integrator()
        integrator2 = get_hook_template_integrator()
        
        assert integrator1 is integrator2  # Should be the same instance
        assert isinstance(integrator1, HookTemplateIntegrator)
    
    def test_format_hook_message_function(self):
        """Test the format_hook_message convenience function."""
        context = HookFormattingContext(hook_type="StatusChangeHook")
        
        with patch('devsync_ai.core.hook_template_integration.get_hook_template_integrator') as mock_get:
            mock_integrator = Mock()
            mock_integrator.format_hook_message.return_value = ProcessingResult(success=True)
            mock_get.return_value = mock_integrator
            
            result = format_hook_message(context)
            
            assert result.success is True
            mock_integrator.format_hook_message.assert_called_once_with(context, None)


if __name__ == '__main__':
    pytest.main([__file__])