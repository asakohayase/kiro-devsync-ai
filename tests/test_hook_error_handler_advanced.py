"""
Advanced tests for the Hook Error Handler system.

This module tests advanced error handling scenarios, edge cases,
and comprehensive integration scenarios for Agent Hooks.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from devsync_ai.core.hook_error_handler import (
    HookErrorHandler, HookError, HookErrorCategory, HookErrorSeverity,
    RetryConfig, CircuitBreakerConfig, FallbackConfig, RetryStrategy,
    CircuitBreaker, CircuitBreakerState, HookErrorMetrics,
    NotificationQueueConfig, WebhookValidationConfig, QueuedNotification
)
from devsync_ai.core.agent_hooks import (
    HookExecutionResult, HookStatus, EnrichedEvent, AgentHook,
    HookConfiguration, EventCategory, UrgencyLevel, ProcessedEvent
)
from devsync_ai.core.exceptions import (
    SlackAPIError, RateLimitError, NetworkError, ConfigurationError,
    DataValidationError, FormattingError
)


class MockAgentHook(AgentHook):
    """Mock Agent Hook for testing."""
    
    def __init__(self, hook_id: str = "test_hook", fail_count: int = 0):
        config = HookConfiguration(
            hook_id=hook_id,
            hook_type="MockHook",
            team_id="test_team"
        )
        super().__init__(hook_id, config)
        self.fail_count = fail_count
        self.call_count = 0
    
    async def can_handle(self, event: EnrichedEvent) -> bool:
        return True
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        self.call_count += 1
        
        if self.call_count <= self.fail_count:
            raise Exception(f"Mock failure {self.call_count}")
        
        return HookExecutionResult(
            hook_id=self.hook_id,
            execution_id=f"exec_{self.call_count}",
            hook_type=self.hook_type,
            event_id=event.event_id,
            status=HookStatus.SUCCESS,
            execution_time_ms=100.0
        )


@pytest.fixture
def mock_event():
    """Create a mock enriched event for testing."""
    return EnrichedEvent(
        event_id="test_event_123",
        event_type="jira:issue_updated",
        timestamp=datetime.now(),
        jira_event_data={"issue": {"key": "TEST-123"}},
        ticket_key="TEST-123",
        project_key="TEST",
        raw_payload={"webhookEvent": "jira:issue_updated"}
    )


class TestAdvancedErrorScenarios:
    """Test advanced error handling scenarios and edge cases."""
    
    @pytest.mark.asyncio
    async def test_concurrent_hook_executions_with_circuit_breaker(self, mock_event):
        """Test concurrent hook executions with circuit breaker protection."""
        error_handler = HookErrorHandler(
            circuit_breaker_config=CircuitBreakerConfig(failure_threshold=2, timeout_seconds=1)
        )
        
        async def failing_operation(event):
            raise SlackAPIError("Service down", status_code=503)
        
        failing_operation.__name__ = "slack_api_call"
        
        # Execute multiple hooks concurrently
        hooks = [MockAgentHook(f"concurrent_hook_{i}") for i in range(5)]
        
        with patch('asyncio.sleep'):
            tasks = [
                error_handler.execute_with_retry(failing_operation, hook, mock_event)
                for hook in hooks
            ]
            results = await asyncio.gather(*tasks)
        
        # All should fail, but circuit breaker should protect against excessive calls
        assert all(r.status == HookStatus.FAILED for r in results)
        
        # Circuit breaker should be open
        cb_status = error_handler.get_circuit_breaker_status()
        assert cb_status['slack_api']['state'] == 'open'
    
    @pytest.mark.asyncio
    async def test_error_recovery_with_metrics_tracking(self, mock_event):
        """Test error recovery with detailed metrics tracking."""
        error_handler = HookErrorHandler()
        call_count = 0
        
        async def intermittent_failure(event):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise NetworkError("Temporary network issue")
            return "success"
        
        hook = MockAgentHook("recovery_hook")
        
        with patch('asyncio.sleep'):
            result = await error_handler.execute_with_retry(
                intermittent_failure, hook, mock_event
            )
        
        assert result.status == HookStatus.SUCCESS
        assert call_count == 3
        
        # Check recovery metrics
        metrics = error_handler.get_error_metrics()
        assert metrics['recovery_success_rate'] > 0
        assert metrics['average_recovery_time'] > 0
    
    @pytest.mark.asyncio
    async def test_queue_overflow_handling(self, mock_event):
        """Test notification queue overflow handling."""
        queue_config = NotificationQueueConfig(
            enable_queuing=True,
            max_queue_size=3  # Small queue for testing
        )
        error_handler = HookErrorHandler(notification_queue_config=queue_config)
        
        # Queue more notifications than the limit
        queue_ids = []
        for i in range(5):
            queue_id = await error_handler.queue_notification_for_later_delivery(
                f"hook_{i}", f"event_{i}", {"message": f"Notification {i}"}
            )
            queue_ids.append(queue_id)
        
        # Queue should not exceed max size
        queue_status = error_handler.get_queue_status()
        assert queue_status["queue_size"] <= queue_config.max_queue_size
    
    @pytest.mark.asyncio
    async def test_webhook_payload_size_limit(self):
        """Test webhook payload size limit validation."""
        error_handler = HookErrorHandler()
        
        # Create a large payload that exceeds the limit
        large_description = "x" * (10 * 1024 * 1024)  # 10MB of text
        large_payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "description": large_description
                }
            },
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        is_valid, error_msg = error_handler.validate_webhook_payload(large_payload)
        assert is_valid is False
        assert "exceeds limit" in error_msg
        
        # Check that validation failure was recorded
        metrics = error_handler.get_error_metrics()
        assert metrics['payload_validation_failures'] > 0
    
    @pytest.mark.asyncio
    async def test_malformed_webhook_payload_handling(self):
        """Test handling of malformed webhook payloads."""
        error_handler = HookErrorHandler()
        
        malformed_payloads = [
            {},  # Empty payload
            {"webhookEvent": "jira:issue_updated"},  # Missing required fields
            {"webhookEvent": "jira:issue_updated", "issue": "not_a_dict"},  # Invalid structure
            {"webhookEvent": "jira:issue_updated", "issue": {"key": "TEST-123"}},  # Missing fields
        ]
        
        validation_failures = 0
        for payload in malformed_payloads:
            is_valid, error_msg = error_handler.validate_webhook_payload(payload)
            if not is_valid:
                validation_failures += 1
        
        assert validation_failures == len(malformed_payloads)
    
    @pytest.mark.asyncio
    async def test_error_handler_cleanup(self, mock_event):
        """Test proper cleanup of error handler resources."""
        error_handler = HookErrorHandler(
            notification_queue_config=NotificationQueueConfig(enable_queuing=True)
        )
        
        # Queue a notification to start background processing
        await error_handler.queue_notification_for_later_delivery(
            "test_hook", "test_event", {"message": "test"}
        )
        
        # Verify background task is running
        assert error_handler._queue_cleanup_task is not None
        
        # Stop queue processing
        error_handler.stop_queue_processing()
        
        # Verify cleanup
        assert error_handler._queue_cleanup_task is None or error_handler._queue_cleanup_task.cancelled()
    
    def test_error_classification_edge_cases(self, mock_event):
        """Test error classification for edge cases."""
        error_handler = HookErrorHandler()
        hook = MockAgentHook("edge_case_hook")
        
        # Test error with custom message patterns
        edge_case_errors = [
            Exception("webhook processing failed"),
            Exception("timeout occurred during operation"),
            Exception("unknown service error"),
            ConnectionError("network unreachable"),
            ValueError("invalid webhook data")
        ]
        
        for error in edge_case_errors:
            classified = error_handler._classify_hook_error(error, hook, mock_event)
            
            # Should always produce a valid classification
            assert classified.category is not None
            assert classified.severity is not None
            assert isinstance(classified.recoverable, bool)
            assert classified.hook_id == hook.hook_id
            assert classified.event_id == mock_event.event_id
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_behavior(self, mock_event):
        """Test detailed circuit breaker half-open state behavior."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=2,
            timeout_seconds=0.1,
            half_open_max_calls=2
        )
        error_handler = HookErrorHandler(circuit_breaker_config=config)
        
        async def failing_operation(event):
            raise SlackAPIError("Service down", status_code=503)
        
        async def success_operation(event):
            return "success"
        
        failing_operation.__name__ = "slack_api_call"
        success_operation.__name__ = "slack_api_call"
        
        hook = MockAgentHook("half_open_test_hook")
        
        # Trigger circuit breaker to open
        result1 = await error_handler.execute_with_retry(failing_operation, hook, mock_event)
        assert result1.status == HookStatus.FAILED
        
        # Wait for timeout to transition to half-open
        await asyncio.sleep(0.2)
        
        # Test half-open behavior with success
        result2 = await error_handler.execute_with_retry(success_operation, hook, mock_event)
        result3 = await error_handler.execute_with_retry(success_operation, hook, mock_event)
        
        # Circuit breaker should close after success threshold
        cb_status = error_handler.get_circuit_breaker_status()
        assert cb_status['slack_api']['state'] == 'closed'


class TestComprehensiveIntegrationScenarios:
    """Test comprehensive integration scenarios with all features."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_error_handling_workflow(self, mock_event):
        """Test complete end-to-end error handling workflow."""
        # Configure comprehensive error handler
        retry_config = RetryConfig(max_attempts=3, base_delay=0.1)
        circuit_breaker_config = CircuitBreakerConfig(failure_threshold=2, timeout_seconds=1)
        fallback_config = FallbackConfig(enable_fallbacks=True)
        queue_config = NotificationQueueConfig(enable_queuing=True)
        validation_config = WebhookValidationConfig(enable_validation=True, sanitize_html=True)
        
        error_handler = HookErrorHandler(
            retry_config=retry_config,
            circuit_breaker_config=circuit_breaker_config,
            fallback_config=fallback_config,
            notification_queue_config=queue_config,
            webhook_validation_config=validation_config
        )
        
        # Test webhook validation and sanitization
        test_payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "description": "<script>alert('test')</script>Clean content"
                }
            },
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        is_valid, _ = error_handler.validate_webhook_payload(test_payload)
        assert is_valid is True
        
        sanitized = error_handler.sanitize_webhook_payload(test_payload)
        assert "<script>" not in str(sanitized)
        
        # Test hook execution with comprehensive error handling
        hook = MockAgentHook("comprehensive_hook", fail_count=5)  # Always fail
        
        with patch('asyncio.sleep'):  # Speed up test
            result = await error_handler.execute_with_retry(
                hook.execute, hook, mock_event
            )
        
        assert result.status == HookStatus.FAILED
        assert result.metadata.get('fallback_applied') is True
        
        # Check comprehensive metrics
        metrics = error_handler.get_error_metrics()
        assert metrics['total_errors'] >= 1
        assert metrics['fallback_activations'] >= 1
        
        # Verify all components are working
        assert 'circuit_breaker_states' in metrics
        assert 'queue_status' in metrics
        assert metrics['payload_validation_failures'] == 0  # No validation failures in this test
    
    @pytest.mark.asyncio
    async def test_mixed_error_types_with_different_strategies(self, mock_event):
        """Test handling of mixed error types with different retry strategies."""
        error_handler = HookErrorHandler(
            retry_config=RetryConfig(max_attempts=4, base_delay=0.1)
        )
        
        call_count = 0
        errors_to_raise = [
            NetworkError("Network timeout"),
            RateLimitError("Rate limited", retry_after=0.1),  # Short retry for testing
            SlackAPIError("Service unavailable", status_code=503),
            None  # Success on 4th attempt
        ]
        
        async def mixed_error_operation(event):
            nonlocal call_count
            if call_count < len(errors_to_raise) - 1:
                error = errors_to_raise[call_count]
                call_count += 1
                if error:
                    raise error
            call_count += 1
            return "success"
        
        hook = MockAgentHook("mixed_error_hook")
        
        with patch('asyncio.sleep'):  # Speed up test
            result = await error_handler.execute_with_retry(
                mixed_error_operation, hook, mock_event
            )
        
        assert result.status == HookStatus.SUCCESS
        assert call_count == 4  # 3 failures + 1 success
        assert len(result.errors) == 3  # All error types should be recorded
        
        # Check that different error types were handled appropriately
        error_messages = ' '.join(result.errors)
        assert 'network' in error_messages.lower()
        assert 'rate' in error_messages.lower()
        assert 'service' in error_messages.lower()
    
    @pytest.mark.asyncio
    async def test_high_volume_error_handling(self, mock_event):
        """Test error handling under high volume scenarios."""
        error_handler = HookErrorHandler(
            retry_config=RetryConfig(max_attempts=2, base_delay=0.01),
            circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5, timeout_seconds=1)
        )
        
        # Simulate high volume of hook executions
        hooks = [MockAgentHook(f"volume_hook_{i}", fail_count=1) for i in range(20)]
        
        with patch('asyncio.sleep'):
            tasks = [
                error_handler.execute_with_retry(hook.execute, hook, mock_event)
                for hook in hooks
            ]
            results = await asyncio.gather(*tasks)
        
        # Most should succeed after retry
        successful_results = [r for r in results if r.status == HookStatus.SUCCESS]
        assert len(successful_results) >= 15  # Allow for some failures due to concurrency
        
        # Check metrics for high volume handling
        metrics = error_handler.get_error_metrics()
        assert metrics['total_errors'] >= 20  # At least one error per hook
        assert metrics['recovery_success_rate'] > 0.7  # Good recovery rate
    
    @pytest.mark.asyncio
    async def test_notification_queue_with_expiration(self, mock_event):
        """Test notification queue with expiration handling."""
        queue_config = NotificationQueueConfig(
            enable_queuing=True,
            queue_retention_hours=0.001,  # Very short retention for testing (3.6 seconds)
            retry_interval_minutes=0.001,  # Very short interval for testing
            max_retry_attempts=2
        )
        error_handler = HookErrorHandler(notification_queue_config=queue_config)
        
        # Queue a notification
        queue_id = await error_handler.queue_notification_for_later_delivery(
            "expiration_hook", "expiration_event", {"message": "Test notification"}
        )
        
        # Wait for expiration
        await asyncio.sleep(0.1)  # Wait longer than retention period
        
        # Process queue - should remove expired notification
        delivered_count = await error_handler.process_notification_queue()
        
        # Should be 0 because notification expired
        queue_status = error_handler.get_queue_status()
        assert queue_status["queue_size"] == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_cycle(self, mock_event):
        """Test complete circuit breaker recovery cycle."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            timeout_seconds=0.1,
            half_open_max_calls=3
        )
        error_handler = HookErrorHandler(circuit_breaker_config=config)
        
        call_count = 0
        
        async def adaptive_operation(event):
            nonlocal call_count
            call_count += 1
            
            # Fail for first few calls, then succeed
            if call_count <= 4:
                raise SlackAPIError("Service down", status_code=503)
            return "success"
        
        adaptive_operation.__name__ = "slack_api_call"
        hook = MockAgentHook("recovery_cycle_hook")
        
        # Phase 1: Trigger circuit breaker to open
        result1 = await error_handler.execute_with_retry(adaptive_operation, hook, mock_event)
        result2 = await error_handler.execute_with_retry(adaptive_operation, hook, mock_event)
        
        cb_status = error_handler.get_circuit_breaker_status()
        assert cb_status['slack_api']['state'] == 'open'
        
        # Phase 2: Wait for half-open transition
        await asyncio.sleep(0.2)
        
        # Phase 3: Test recovery with successful calls
        result3 = await error_handler.execute_with_retry(adaptive_operation, hook, mock_event)
        result4 = await error_handler.execute_with_retry(adaptive_operation, hook, mock_event)
        
        # Circuit breaker should be closed now
        cb_status = error_handler.get_circuit_breaker_status()
        assert cb_status['slack_api']['state'] == 'closed'
        
        # Verify final successful execution
        result5 = await error_handler.execute_with_retry(adaptive_operation, hook, mock_event)
        assert result5.status == HookStatus.SUCCESS


class TestErrorHandlerConfiguration:
    """Test error handler configuration and customization."""
    
    def test_custom_retry_strategies(self, mock_event):
        """Test different retry strategies with custom configurations."""
        strategies_and_expected = [
            (RetryStrategy.EXPONENTIAL_BACKOFF, [1.0, 2.0, 4.0]),
            (RetryStrategy.LINEAR_BACKOFF, [1.0, 2.0, 3.0]),
            (RetryStrategy.FIXED_DELAY, [1.0, 1.0, 1.0]),
            (RetryStrategy.IMMEDIATE, [0, 0, 0]),
            (RetryStrategy.NO_RETRY, [0, 0, 0])
        ]
        
        for strategy, expected_delays in strategies_and_expected:
            retry_config = RetryConfig(
                strategy=strategy,
                base_delay=1.0,
                backoff_multiplier=2.0,
                jitter=False  # Disable for predictable results
            )
            error_handler = HookErrorHandler(retry_config=retry_config)
            
            test_error = HookError(
                "Test error",
                HookErrorCategory.HOOK_EXECUTION,
                HookErrorSeverity.MEDIUM
            )
            
            actual_delays = [
                error_handler._calculate_retry_delay(i, test_error)
                for i in range(3)
            ]
            
            assert actual_delays == expected_delays, f"Strategy {strategy} failed"
    
    def test_webhook_validation_configuration(self):
        """Test webhook validation with different configurations."""
        # Test with validation disabled
        config_disabled = WebhookValidationConfig(enable_validation=False)
        error_handler_disabled = HookErrorHandler(webhook_validation_config=config_disabled)
        
        invalid_payload = {}  # Empty payload
        is_valid, error_msg = error_handler_disabled.validate_webhook_payload(invalid_payload)
        assert is_valid is True  # Should pass when validation is disabled
        
        # Test with custom required fields
        config_custom = WebhookValidationConfig(
            enable_validation=True,
            required_fields=["customField", "anotherField"]
        )
        error_handler_custom = HookErrorHandler(webhook_validation_config=config_custom)
        
        custom_payload = {"customField": "value", "anotherField": "value"}
        is_valid, error_msg = error_handler_custom.validate_webhook_payload(custom_payload)
        assert is_valid is True
        
        incomplete_payload = {"customField": "value"}  # Missing anotherField
        is_valid, error_msg = error_handler_custom.validate_webhook_payload(incomplete_payload)
        assert is_valid is False
        assert "anotherField" in error_msg
    
    def test_fallback_configuration_options(self):
        """Test different fallback configuration options."""
        # Test with fallbacks disabled
        config_disabled = FallbackConfig(enable_fallbacks=False)
        error_handler = HookErrorHandler(fallback_config=config_disabled)
        
        assert error_handler.fallback_config.enable_fallbacks is False
        
        # Test with custom channels and settings
        config_custom = FallbackConfig(
            enable_fallbacks=True,
            fallback_channels=["#custom-fallback", "#backup"],
            notify_admins=True,
            admin_channels=["#admin-alerts"],
            include_error_details=False,
            max_fallback_attempts=5
        )
        error_handler_custom = HookErrorHandler(fallback_config=config_custom)
        
        assert len(error_handler_custom.fallback_config.fallback_channels) == 2
        assert error_handler_custom.fallback_config.max_fallback_attempts == 5
        assert error_handler_custom.fallback_config.include_error_details is False
    
    def test_queue_configuration_validation(self):
        """Test notification queue configuration validation."""
        # Test with queuing disabled
        config_disabled = NotificationQueueConfig(enable_queuing=False)
        error_handler = HookErrorHandler(notification_queue_config=config_disabled)
        
        # Should raise error when trying to queue with queuing disabled
        with pytest.raises(HookError) as exc_info:
            asyncio.run(error_handler.queue_notification_for_later_delivery(
                "test", "test", {"message": "test"}
            ))
        assert "queuing is disabled" in str(exc_info.value).lower()
        
        # Test with custom queue settings
        config_custom = NotificationQueueConfig(
            enable_queuing=True,
            max_queue_size=50,
            queue_retention_hours=48,
            retry_interval_minutes=10,
            max_retry_attempts=5
        )
        error_handler_custom = HookErrorHandler(notification_queue_config=config_custom)
        
        assert error_handler_custom.notification_queue_config.max_queue_size == 50
        assert error_handler_custom.notification_queue_config.queue_retention_hours == 48