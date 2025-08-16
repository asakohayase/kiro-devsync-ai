"""
Tests for the Hook Error Handler system.

This module tests comprehensive error handling, retry mechanisms,
circuit breaker patterns, and fallback notification mechanisms
for Agent Hooks.
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


@pytest.fixture
def retry_config():
    """Create retry configuration for testing."""
    return RetryConfig(
        max_attempts=3,
        base_delay=0.1,  # Short delay for testing
        max_delay=1.0,
        backoff_multiplier=2.0,
        jitter=False,  # Disable jitter for predictable tests
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF
    )


@pytest.fixture
def circuit_breaker_config():
    """Create circuit breaker configuration for testing."""
    return CircuitBreakerConfig(
        failure_threshold=2,
        success_threshold=2,
        timeout_seconds=1,
        half_open_max_calls=2
    )


@pytest.fixture
def fallback_config():
    """Create fallback configuration for testing."""
    return FallbackConfig(
        enable_fallbacks=True,
        fallback_channels=["#fallback"],
        notify_admins=True,
        admin_channels=["#admin"],
        include_error_details=True
    )


@pytest.fixture
def error_handler(retry_config, circuit_breaker_config, fallback_config):
    """Create error handler for testing."""
    return HookErrorHandler(
        retry_config=retry_config,
        circuit_breaker_config=circuit_breaker_config,
        fallback_config=fallback_config
    )


class TestHookError:
    """Test HookError class."""
    
    def test_hook_error_creation(self):
        """Test creating a HookError."""
        error = HookError(
            message="Test error",
            category=HookErrorCategory.HOOK_EXECUTION,
            severity=HookErrorSeverity.HIGH,
            hook_id="test_hook",
            event_id="test_event"
        )
        
        assert str(error) == "[hook_execution] Test error"
        assert error.category == HookErrorCategory.HOOK_EXECUTION
        assert error.severity == HookErrorSeverity.HIGH
        assert error.hook_id == "test_hook"
        assert error.event_id == "test_event"
        assert error.recoverable is True
    
    def test_hook_error_with_context(self):
        """Test HookError with additional context."""
        original_error = ValueError("Original error")
        error = HookError(
            message="Wrapper error",
            category=HookErrorCategory.EXTERNAL_SERVICE,
            severity=HookErrorSeverity.CRITICAL,
            context={"key": "value"},
            original_error=original_error
        )
        
        assert error.context == {"key": "value"}
        assert error.original_error == original_error


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout_seconds=1)
        breaker = CircuitBreaker(config)
        
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self):
        """Test successful calls through circuit breaker."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout_seconds=1)
        breaker = CircuitBreaker(config)
        
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_threshold(self):
        """Test circuit breaker opening after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout_seconds=1)
        breaker = CircuitBreaker(config)
        
        async def failing_func():
            raise Exception("Test failure")
        
        # First failure
        with pytest.raises(Exception):
            await breaker.call(failing_func)
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 1
        
        # Second failure - should open circuit
        with pytest.raises(Exception):
            await breaker.call(failing_func)
        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.failure_count == 2
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state(self):
        """Test circuit breaker rejecting calls in open state."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=1)
        breaker = CircuitBreaker(config)
        
        async def failing_func():
            raise Exception("Test failure")
        
        # Trigger circuit breaker to open
        with pytest.raises(Exception):
            await breaker.call(failing_func)
        assert breaker.state == CircuitBreakerState.OPEN
        
        # Should reject subsequent calls
        with pytest.raises(HookError) as exc_info:
            await breaker.call(failing_func)
        assert "Circuit breaker is OPEN" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery through half-open state."""
        config = CircuitBreakerConfig(
            failure_threshold=1, 
            success_threshold=2, 
            timeout_seconds=0.1,
            half_open_max_calls=3
        )
        breaker = CircuitBreaker(config)
        
        async def failing_func():
            raise Exception("Test failure")
        
        async def success_func():
            return "success"
        
        # Open the circuit
        with pytest.raises(Exception):
            await breaker.call(failing_func)
        assert breaker.state == CircuitBreakerState.OPEN
        
        # Wait for timeout
        await asyncio.sleep(0.2)
        
        # Should transition to half-open and allow calls
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitBreakerState.HALF_OPEN
        
        # Another success should close the circuit
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitBreakerState.CLOSED


class TestHookErrorHandler:
    """Test HookErrorHandler functionality."""
    
    @pytest.mark.asyncio
    async def test_successful_execution(self, error_handler, mock_event):
        """Test successful hook execution without errors."""
        hook = MockAgentHook("success_hook", fail_count=0)
        
        result = await error_handler.execute_with_retry(
            hook.execute, hook, mock_event
        )
        
        assert result.status == HookStatus.SUCCESS
        assert result.hook_id == "success_hook"
        assert result.event_id == "test_event_123"
        assert len(result.errors) == 0
        assert result.metadata['attempt'] == 1
    
    @pytest.mark.asyncio
    async def test_retry_with_recovery(self, error_handler, mock_event):
        """Test retry mechanism with eventual success."""
        hook = MockAgentHook("retry_hook", fail_count=2)  # Fail first 2 attempts
        
        result = await error_handler.execute_with_retry(
            hook.execute, hook, mock_event
        )
        
        assert result.status == HookStatus.SUCCESS
        assert hook.call_count == 3  # 2 failures + 1 success
        assert result.metadata['attempt'] == 3
        assert len(result.errors) == 2  # Errors from failed attempts
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, error_handler, mock_event):
        """Test retry exhaustion with persistent failures."""
        hook = MockAgentHook("failing_hook", fail_count=5)  # Always fail
        
        result = await error_handler.execute_with_retry(
            hook.execute, hook, mock_event
        )
        
        assert result.status == HookStatus.FAILED
        assert hook.call_count == 3  # Max attempts
        assert result.metadata['attempt'] == 3
        assert len(result.errors) == 3
    
    @pytest.mark.asyncio
    async def test_non_recoverable_error(self, error_handler, mock_event):
        """Test handling of non-recoverable errors."""
        async def non_recoverable_operation(event):
            raise ConfigurationError("Invalid configuration")
        
        hook = MockAgentHook("config_error_hook")
        
        result = await error_handler.execute_with_retry(
            non_recoverable_operation, hook, mock_event
        )
        
        assert result.status == HookStatus.FAILED
        assert len(result.errors) == 1
        assert "configuration" in result.errors[0].lower()
        assert result.metadata['last_error_category'] == 'configuration_error'
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, error_handler, mock_event):
        """Test handling of rate limit errors with retry delay."""
        # Increase max delay for this test
        error_handler.retry_config.max_delay = 100.0
        
        async def rate_limited_operation(event):
            raise RateLimitError("Rate limit exceeded", retry_after=60)
        
        hook = MockAgentHook("rate_limit_hook")
        
        # Mock sleep to avoid actual delays in tests
        with patch('asyncio.sleep') as mock_sleep:
            result = await error_handler.execute_with_retry(
                rate_limited_operation, hook, mock_event
            )
            
            # Should have attempted retries with proper delays
            assert mock_sleep.call_count >= 1
            # First retry should use the rate limit retry_after value
            mock_sleep.assert_any_call(60.0)
    
    @pytest.mark.asyncio
    async def test_slack_api_error_classification(self, error_handler, mock_event):
        """Test classification of Slack API errors."""
        async def slack_error_operation(event):
            raise SlackAPIError("Invalid token", status_code=401)
        
        hook = MockAgentHook("slack_error_hook")
        
        result = await error_handler.execute_with_retry(
            slack_error_operation, hook, mock_event
        )
        
        assert result.status == HookStatus.FAILED
        assert result.metadata['last_error_category'] == 'notification_delivery'
        assert result.metadata['last_error_severity'] == 'critical'
    
    @pytest.mark.asyncio
    async def test_network_error_classification(self, error_handler, mock_event):
        """Test classification of network errors."""
        async def network_error_operation(event):
            raise ConnectionError("Connection failed")
        
        hook = MockAgentHook("network_error_hook")
        
        result = await error_handler.execute_with_retry(
            network_error_operation, hook, mock_event
        )
        
        assert result.status == HookStatus.FAILED
        assert result.metadata['last_error_category'] == 'external_service'
        assert result.metadata['last_error_severity'] == 'high'
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, error_handler, mock_event):
        """Test circuit breaker integration with hook execution."""
        call_count = 0
        
        async def failing_slack_operation(event):
            nonlocal call_count
            call_count += 1
            raise SlackAPIError("Service unavailable", status_code=503)
        
        # Mock the operation name to trigger slack circuit breaker
        failing_slack_operation.__name__ = "slack_notification_send"
        
        hook = MockAgentHook("circuit_breaker_hook")
        
        # First few calls should fail normally
        result1 = await error_handler.execute_with_retry(
            failing_slack_operation, hook, mock_event
        )
        assert result1.status == HookStatus.FAILED
        
        result2 = await error_handler.execute_with_retry(
            failing_slack_operation, hook, mock_event
        )
        assert result2.status == HookStatus.FAILED
        
        # Circuit breaker should now be open, rejecting calls immediately
        result3 = await error_handler.execute_with_retry(
            failing_slack_operation, hook, mock_event
        )
        assert result3.status == HookStatus.FAILED
        # Should have fewer actual calls due to circuit breaker
        assert "Circuit breaker is OPEN" in str(result3.errors)
    
    @pytest.mark.asyncio
    async def test_fallback_mechanisms(self, error_handler, mock_event):
        """Test fallback notification mechanisms."""
        async def always_failing_operation(event):
            raise Exception("Persistent failure")
        
        hook = MockAgentHook("fallback_hook")
        
        with patch.object(error_handler, '_send_fallback_notification') as mock_fallback, \
             patch.object(error_handler, '_send_admin_notification') as mock_admin:
            
            result = await error_handler.execute_with_retry(
                always_failing_operation, hook, mock_event
            )
            
            assert result.status == HookStatus.FAILED
            assert result.metadata.get('fallback_applied') is True
            
            # Should have called fallback mechanisms
            mock_fallback.assert_called_once()
            mock_admin.assert_called_once()
    
    def test_error_metrics_tracking(self, error_handler):
        """Test error metrics collection and tracking."""
        # Create some test errors
        error1 = HookError(
            "Test error 1",
            category=HookErrorCategory.HOOK_EXECUTION,
            severity=HookErrorSeverity.MEDIUM,
            hook_id="hook1"
        )
        error2 = HookError(
            "Test error 2",
            category=HookErrorCategory.NOTIFICATION_DELIVERY,
            severity=HookErrorSeverity.HIGH,
            hook_id="hook2"
        )
        
        # Add errors to metrics
        error_handler.metrics.add_error(error1)
        error_handler.metrics.add_error(error2, recovery_time=1.5)
        
        metrics = error_handler.get_error_metrics()
        
        assert metrics['total_errors'] == 2
        assert metrics['errors_by_category']['hook_execution'] == 1
        assert metrics['errors_by_category']['notification_delivery'] == 1
        assert metrics['errors_by_severity']['medium'] == 1
        assert metrics['errors_by_severity']['high'] == 1
        assert metrics['errors_by_hook_type']['hook1'] == 1
        assert metrics['errors_by_hook_type']['hook2'] == 1
        assert metrics['recovery_success_rate'] == 0.5  # 1 out of 2 recovered
    
    def test_retry_delay_calculation(self, error_handler):
        """Test retry delay calculation for different strategies."""
        error = HookError(
            "Test error",
            category=HookErrorCategory.HOOK_EXECUTION,
            severity=HookErrorSeverity.MEDIUM
        )
        
        # Test exponential backoff
        error_handler.retry_config.strategy = RetryStrategy.EXPONENTIAL_BACKOFF
        error_handler.retry_config.base_delay = 1.0
        error_handler.retry_config.backoff_multiplier = 2.0
        error_handler.retry_config.max_delay = 10.0  # Increase max delay
        error_handler.retry_config.jitter = False
        
        delay0 = error_handler._calculate_retry_delay(0, error)
        delay1 = error_handler._calculate_retry_delay(1, error)
        delay2 = error_handler._calculate_retry_delay(2, error)
        
        assert delay0 == 1.0  # 1.0 * 2^0
        assert delay1 == 2.0  # 1.0 * 2^1
        assert delay2 == 4.0  # 1.0 * 2^2
        
        # Test linear backoff
        error_handler.retry_config.strategy = RetryStrategy.LINEAR_BACKOFF
        
        delay0 = error_handler._calculate_retry_delay(0, error)
        delay1 = error_handler._calculate_retry_delay(1, error)
        delay2 = error_handler._calculate_retry_delay(2, error)
        
        assert delay0 == 1.0  # 1.0 * (0 + 1)
        assert delay1 == 2.0  # 1.0 * (1 + 1)
        assert delay2 == 3.0  # 1.0 * (2 + 1)
        
        # Test fixed delay
        error_handler.retry_config.strategy = RetryStrategy.FIXED_DELAY
        
        delay0 = error_handler._calculate_retry_delay(0, error)
        delay1 = error_handler._calculate_retry_delay(1, error)
        delay2 = error_handler._calculate_retry_delay(2, error)
        
        assert delay0 == 1.0
        assert delay1 == 1.0
        assert delay2 == 1.0
        
        # Test no retry
        error_handler.retry_config.strategy = RetryStrategy.NO_RETRY
        
        delay0 = error_handler._calculate_retry_delay(0, error)
        assert delay0 == 0
    
    def test_retry_delay_with_error_specific_delay(self, error_handler):
        """Test retry delay using error-specific retry_after value."""
        # Increase max delay for this test
        error_handler.retry_config.max_delay = 100.0
        
        error = HookError(
            "Rate limited",
            category=HookErrorCategory.RATE_LIMIT,
            severity=HookErrorSeverity.MEDIUM,
            retry_after=30.0
        )
        
        delay = error_handler._calculate_retry_delay(0, error)
        assert delay == 30.0
        
        # Test max delay constraint
        error.retry_after = 500.0  # Exceeds max_delay
        delay = error_handler._calculate_retry_delay(0, error)
        assert delay == error_handler.retry_config.max_delay
    
    def test_circuit_breaker_status(self, error_handler):
        """Test circuit breaker status reporting."""
        status = error_handler.get_circuit_breaker_status()
        
        assert 'jira_api' in status
        assert 'slack_api' in status
        assert 'database' in status
        assert 'webhook_processing' in status
        
        for service_status in status.values():
            assert 'state' in service_status
            assert 'failure_count' in service_status
            assert 'success_count' in service_status
            assert service_status['state'] == 'closed'  # Initial state
    
    def test_circuit_breaker_reset(self, error_handler):
        """Test circuit breaker reset functionality."""
        # Manually set a circuit breaker to open state
        breaker = error_handler.circuit_breakers['slack_api']
        breaker.state = CircuitBreakerState.OPEN
        breaker.failure_count = 5
        
        # Reset specific circuit breaker
        success = error_handler.reset_circuit_breaker('slack_api')
        assert success is True
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0
        
        # Test invalid service name
        success = error_handler.reset_circuit_breaker('invalid_service')
        assert success is False
    
    def test_reset_all_circuit_breakers(self, error_handler):
        """Test resetting all circuit breakers."""
        # Set all breakers to open state
        for breaker in error_handler.circuit_breakers.values():
            breaker.state = CircuitBreakerState.OPEN
            breaker.failure_count = 5
        
        error_handler.reset_all_circuit_breakers()
        
        # All should be reset
        for breaker in error_handler.circuit_breakers.values():
            assert breaker.state == CircuitBreakerState.CLOSED
            assert breaker.failure_count == 0
    
    def test_metrics_reset(self, error_handler):
        """Test metrics reset functionality."""
        # Add some errors to metrics
        error = HookError(
            "Test error",
            category=HookErrorCategory.HOOK_EXECUTION,
            severity=HookErrorSeverity.MEDIUM
        )
        error_handler.metrics.add_error(error)
        error_handler.metrics.fallback_activations = 5
        
        assert error_handler.metrics.total_errors == 1
        assert error_handler.metrics.fallback_activations == 5
        
        # Reset metrics
        error_handler.reset_metrics()
        
        assert error_handler.metrics.total_errors == 0
        assert error_handler.metrics.fallback_activations == 0
        assert len(error_handler.metrics.recent_errors) == 0


class TestErrorClassification:
    """Test error classification functionality."""
    
    def test_classify_slack_api_error(self, error_handler, mock_event):
        """Test classification of Slack API errors."""
        hook = MockAgentHook("test_hook")
        
        # Test 401 error (non-recoverable)
        slack_error_401 = SlackAPIError("Invalid token", status_code=401)
        classified = error_handler._classify_hook_error(slack_error_401, hook, mock_event)
        
        assert classified.category == HookErrorCategory.NOTIFICATION_DELIVERY
        assert classified.severity == HookErrorSeverity.CRITICAL
        assert classified.recoverable is False
        
        # Test 503 error (recoverable)
        slack_error_503 = SlackAPIError("Service unavailable", status_code=503)
        classified = error_handler._classify_hook_error(slack_error_503, hook, mock_event)
        
        assert classified.category == HookErrorCategory.NOTIFICATION_DELIVERY
        assert classified.severity == HookErrorSeverity.HIGH
        assert classified.recoverable is True
    
    def test_classify_rate_limit_error(self, error_handler, mock_event):
        """Test classification of rate limit errors."""
        hook = MockAgentHook("test_hook")
        rate_error = RateLimitError("Rate limit exceeded", retry_after=60)
        
        classified = error_handler._classify_hook_error(rate_error, hook, mock_event)
        
        assert classified.category == HookErrorCategory.RATE_LIMIT
        assert classified.severity == HookErrorSeverity.MEDIUM
        assert classified.recoverable is True
        assert classified.retry_after == 60
    
    def test_classify_network_error(self, error_handler, mock_event):
        """Test classification of network errors."""
        hook = MockAgentHook("test_hook")
        network_error = ConnectionError("Connection failed")
        
        classified = error_handler._classify_hook_error(network_error, hook, mock_event)
        
        assert classified.category == HookErrorCategory.EXTERNAL_SERVICE
        assert classified.severity == HookErrorSeverity.HIGH
        assert classified.recoverable is True
        assert classified.retry_after == 30.0
    
    def test_classify_configuration_error(self, error_handler, mock_event):
        """Test classification of configuration errors."""
        hook = MockAgentHook("test_hook")
        config_error = ConfigurationError("Invalid configuration")
        
        classified = error_handler._classify_hook_error(config_error, hook, mock_event)
        
        assert classified.category == HookErrorCategory.CONFIGURATION_ERROR
        assert classified.severity == HookErrorSeverity.HIGH
        assert classified.recoverable is False
    
    def test_classify_timeout_error(self, error_handler, mock_event):
        """Test classification of timeout errors."""
        hook = MockAgentHook("test_hook")
        timeout_error = TimeoutError("Operation timed out")
        
        classified = error_handler._classify_hook_error(timeout_error, hook, mock_event)
        
        assert classified.category == HookErrorCategory.TIMEOUT
        assert classified.severity == HookErrorSeverity.HIGH
        assert classified.recoverable is True
        assert classified.retry_after == 60.0
    
    def test_classify_unknown_error(self, error_handler, mock_event):
        """Test classification of unknown errors."""
        hook = MockAgentHook("test_hook")
        unknown_error = ValueError("Unknown error")
        
        classified = error_handler._classify_hook_error(unknown_error, hook, mock_event)
        
        assert classified.category == HookErrorCategory.HOOK_EXECUTION
        assert classified.severity == HookErrorSeverity.MEDIUM
        assert classified.recoverable is True
        assert classified.original_error == unknown_error


class TestIntegrationScenarios:
    """Test complex integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_failure_recovery_cycle(self, error_handler, mock_event):
        """Test complete failure and recovery cycle."""
        call_count = 0
        
        async def intermittent_failure_operation(event):
            nonlocal call_count
            call_count += 1
            
            if call_count <= 2:
                raise SlackAPIError("Service temporarily unavailable", status_code=503)
            else:
                # Success case - just return something, the error handler will create the result
                return "success"
        
        hook = MockAgentHook("integration_hook")
        
        with patch('asyncio.sleep'):  # Mock sleep to speed up test
            result = await error_handler.execute_with_retry(
                intermittent_failure_operation, hook, mock_event
            )
        
        assert result.status == HookStatus.SUCCESS
        assert call_count == 3  # 2 service errors + 1 success
        assert len(result.errors) == 2  # Errors from failed attempts
    
    @pytest.mark.asyncio
    async def test_cascading_failure_with_circuit_breaker(self, error_handler, mock_event):
        """Test cascading failures triggering circuit breaker."""
        async def cascading_failure_operation(event):
            raise SlackAPIError("Service down", status_code=503)
        
        # Mock the operation name to trigger slack circuit breaker
        cascading_failure_operation.__name__ = "slack_api_call"
        
        hook = MockAgentHook("cascading_hook")
        
        # Execute multiple times to trigger circuit breaker
        results = []
        for i in range(5):
            result = await error_handler.execute_with_retry(
                cascading_failure_operation, hook, mock_event
            )
            results.append(result)
        
        # All should fail, but later ones should fail faster due to circuit breaker
        assert all(r.status == HookStatus.FAILED for r in results)
        
        # Check circuit breaker state
        cb_status = error_handler.get_circuit_breaker_status()
        assert cb_status['slack_api']['state'] == 'open'
    
    @pytest.mark.asyncio
    async def test_mixed_error_types_handling(self, error_handler, mock_event):
        """Test handling of mixed error types in sequence."""
        call_count = 0
        errors_to_raise = [
            NetworkError("Network timeout"),
            DataValidationError("Invalid data"),
            RateLimitError("Rate limited", retry_after=30),
            SlackAPIError("Auth error", status_code=401)  # Non-recoverable
        ]
        
        async def mixed_error_operation(event):
            nonlocal call_count
            if call_count < len(errors_to_raise):
                error = errors_to_raise[call_count]
                call_count += 1
                raise error
            return "success"
        
        hook = MockAgentHook("mixed_error_hook")
        
        with patch('asyncio.sleep'):  # Mock sleep to speed up test
            result = await error_handler.execute_with_retry(
                mixed_error_operation, hook, mock_event
            )
        
        # Should fail after max attempts (3)
        assert result.status == HookStatus.FAILED
        assert call_count == 3  # Max attempts reached
        assert len(result.errors) == 3
        
        # Check that the last error was classified correctly (rate limit error)
        assert result.metadata['last_error_category'] == 'rate_limit'
        assert result.metadata['last_error_severity'] == 'medium'


class TestWebhookValidation:
    """Test webhook payload validation functionality."""
    
    def test_valid_payload_validation(self, error_handler):
        """Test validation of valid webhook payload."""
        valid_payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "status": {"name": "In Progress"}
                }
            },
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        is_valid, error_msg = error_handler.validate_webhook_payload(valid_payload)
        assert is_valid is True
        assert error_msg is None
    
    def test_missing_required_field_validation(self, error_handler):
        """Test validation failure for missing required fields."""
        invalid_payload = {
            "webhookEvent": "jira:issue_updated",
            # Missing 'issue' field
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        is_valid, error_msg = error_handler.validate_webhook_payload(invalid_payload)
        assert is_valid is False
        assert "Required field 'issue' is missing" in error_msg
    
    def test_payload_size_limit_validation(self, error_handler):
        """Test validation failure for oversized payload."""
        # Create a large payload that exceeds the size limit
        large_data = "x" * (1024 * 1024 * 11)  # 11MB of data
        oversized_payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "TEST-123",
                "fields": {"description": large_data}
            },
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        is_valid, error_msg = error_handler.validate_webhook_payload(oversized_payload)
        assert is_valid is False
        assert "exceeds limit" in error_msg
    
    def test_payload_sanitization(self, error_handler):
        """Test payload sanitization removes harmful content."""
        malicious_payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "description": "<script>alert('xss')</script>Normal text",
                    "summary": "javascript:void(0)"
                }
            },
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        sanitized = error_handler.sanitize_webhook_payload(malicious_payload)
        
        # Check that harmful content was removed
        assert "<script>" not in sanitized["issue"]["fields"]["description"]
        assert "alert('xss')" not in sanitized["issue"]["fields"]["description"]
        assert "Normal text" in sanitized["issue"]["fields"]["description"]
        assert "javascript:" not in sanitized["issue"]["fields"]["summary"]
    
    def test_validation_disabled(self):
        """Test that validation can be disabled."""
        from devsync_ai.core.hook_error_handler import WebhookValidationConfig
        
        config = WebhookValidationConfig(enable_validation=False)
        error_handler = HookErrorHandler(webhook_validation_config=config)
        
        # Even invalid payload should pass when validation is disabled
        invalid_payload = {"invalid": "payload"}
        is_valid, error_msg = error_handler.validate_webhook_payload(invalid_payload)
        assert is_valid is True
        assert error_msg is None


class TestNotificationQueuing:
    """Test notification queuing functionality."""
    
    @pytest.mark.asyncio
    async def test_queue_notification_for_later_delivery(self, error_handler):
        """Test queuing notifications for later delivery."""
        notification_data = {
            "message": "Test notification",
            "channel": "#test",
            "priority": "high"
        }
        
        queue_id = await error_handler.queue_notification_for_later_delivery(
            "test_hook", "test_event", notification_data
        )
        
        assert queue_id is not None
        assert queue_id in error_handler.notification_queue
        
        queued = error_handler.notification_queue[queue_id]
        assert queued.hook_id == "test_hook"
        assert queued.event_id == "test_event"
        assert queued.notification_data == notification_data
        assert queued.retry_count == 0
    
    @pytest.mark.asyncio
    async def test_queue_size_limit(self):
        """Test that queue respects size limits."""
        from devsync_ai.core.hook_error_handler import NotificationQueueConfig
        
        config = NotificationQueueConfig(max_queue_size=2)
        error_handler = HookErrorHandler(notification_queue_config=config)
        
        # Add notifications up to the limit
        await error_handler.queue_notification_for_later_delivery(
            "hook1", "event1", {"data": "1"}
        )
        await error_handler.queue_notification_for_later_delivery(
            "hook2", "event2", {"data": "2"}
        )
        
        assert len(error_handler.notification_queue) == 2
        
        # Adding another should remove the oldest
        await error_handler.queue_notification_for_later_delivery(
            "hook3", "event3", {"data": "3"}
        )
        
        assert len(error_handler.notification_queue) == 2
        # Should contain the two most recent notifications
        hook_ids = [n.hook_id for n in error_handler.notification_queue.values()]
        assert "hook2" in hook_ids
        assert "hook3" in hook_ids
        assert "hook1" not in hook_ids
    
    @pytest.mark.asyncio
    async def test_process_notification_queue(self, error_handler):
        """Test processing of notification queue."""
        # Queue some notifications
        await error_handler.queue_notification_for_later_delivery(
            "test_hook1", "test_event1", {"data": "1"}
        )
        await error_handler.queue_notification_for_later_delivery(
            "test_hook2", "test_event2", {"data": "2"}
        )
        
        assert len(error_handler.notification_queue) == 2
        
        # Mock successful delivery
        with patch.object(error_handler, '_attempt_queued_notification_delivery', 
                         return_value=True) as mock_delivery:
            delivered_count = await error_handler.process_notification_queue()
            
            assert delivered_count == 2
            assert len(error_handler.notification_queue) == 0
            assert mock_delivery.call_count == 2
    
    @pytest.mark.asyncio
    async def test_queue_retry_logic(self, error_handler):
        """Test retry logic for queued notifications."""
        # Queue a notification
        queue_id = await error_handler.queue_notification_for_later_delivery(
            "test_hook", "test_event", {"data": "test"}
        )
        
        notification = error_handler.notification_queue[queue_id]
        
        # Mock failed delivery
        with patch.object(error_handler, '_attempt_queued_notification_delivery', 
                         return_value=False) as mock_delivery:
            delivered_count = await error_handler.process_notification_queue()
            
            assert delivered_count == 0
            assert len(error_handler.notification_queue) == 1
            assert notification.retry_count == 1
            assert notification.last_retry_at is not None
    
    @pytest.mark.asyncio
    async def test_queue_expiration(self):
        """Test that expired notifications are removed from queue."""
        from devsync_ai.core.hook_error_handler import NotificationQueueConfig
        
        config = NotificationQueueConfig(queue_retention_hours=0)  # Expire immediately
        error_handler = HookErrorHandler(notification_queue_config=config)
        
        # Queue a notification
        await error_handler.queue_notification_for_later_delivery(
            "test_hook", "test_event", {"data": "test"}
        )
        
        assert len(error_handler.notification_queue) == 1
        
        # Process queue - notification should be expired and removed
        delivered_count = await error_handler.process_notification_queue()
        
        assert delivered_count == 0
        assert len(error_handler.notification_queue) == 0
    
    def test_queue_status(self, error_handler):
        """Test queue status reporting."""
        status = error_handler.get_queue_status()
        
        assert "queue_size" in status
        assert "max_queue_size" in status
        assert "queued_notifications" in status
        assert "successful_deliveries" in status
        assert "queue_enabled" in status
        assert "notifications_by_retry_count" in status
        
        assert status["queue_size"] == 0
        assert status["queue_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_queuing_disabled(self):
        """Test behavior when queuing is disabled."""
        from devsync_ai.core.hook_error_handler import NotificationQueueConfig
        
        config = NotificationQueueConfig(enable_queuing=False)
        error_handler = HookErrorHandler(notification_queue_config=config)
        
        with pytest.raises(HookError) as exc_info:
            await error_handler.queue_notification_for_later_delivery(
                "test_hook", "test_event", {"data": "test"}
            )
        
        assert "queuing is disabled" in str(exc_info.value)


class TestEnhancedIntegrationScenarios:
    """Test enhanced integration scenarios with new features."""
    
    @pytest.mark.asyncio
    async def test_webhook_validation_integration(self, error_handler, mock_event):
        """Test integration of webhook validation with hook execution."""
        # Test with valid payload
        valid_payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "TEST-123", "fields": {}},
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        is_valid, error_msg = error_handler.validate_webhook_payload(valid_payload)
        assert is_valid is True
        
        # Test with invalid payload
        invalid_payload = {"invalid": "payload"}
        is_valid, error_msg = error_handler.validate_webhook_payload(invalid_payload)
        assert is_valid is False
        assert error_handler.metrics.payload_validation_failures == 1
    
    @pytest.mark.asyncio
    async def test_slack_unavailable_queuing_integration(self, error_handler, mock_event):
        """Test automatic queuing when Slack API is unavailable."""
        async def slack_unavailable_operation(event):
            raise SlackAPIError("Service unavailable", status_code=503)
        
        hook = MockAgentHook("slack_unavailable_hook")
        
        result = await error_handler.execute_with_retry(
            slack_unavailable_operation, hook, mock_event
        )
        
        assert result.status == HookStatus.FAILED
        assert 'queued_notification_id' in result.metadata
        assert len(error_handler.notification_queue) == 1
        assert error_handler.metrics.queued_notifications == 1
    
    @pytest.mark.asyncio
    async def test_complete_error_handling_workflow(self, error_handler, mock_event):
        """Test complete error handling workflow with all features."""
        # Test payload validation
        test_payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "description": "<script>alert('test')</script>Valid content"
                }
            },
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        # Validate payload
        is_valid, error_msg = error_handler.validate_webhook_payload(test_payload)
        assert is_valid is True
        
        # Sanitize payload
        sanitized = error_handler.sanitize_webhook_payload(test_payload)
        assert "<script>" not in sanitized["issue"]["fields"]["description"]
        assert "Valid content" in sanitized["issue"]["fields"]["description"]
        
        # Test hook execution with Slack failure and queuing
        async def failing_slack_operation(event):
            raise SlackAPIError("Service temporarily unavailable", status_code=503)
        
        hook = MockAgentHook("complete_workflow_hook")
        
        result = await error_handler.execute_with_retry(
            failing_slack_operation, hook, mock_event
        )
        
        # Verify complete workflow
        assert result.status == HookStatus.FAILED
        assert 'queued_notification_id' in result.metadata
        assert len(error_handler.notification_queue) == 1
        
        # Check metrics
        metrics = error_handler.get_error_metrics()
        assert metrics['total_errors'] > 0
        assert metrics['queued_notifications'] == 1
        assert 'queue_status' in metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])