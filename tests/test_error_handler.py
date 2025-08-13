#!/usr/bin/env python3
"""Test script for comprehensive error handling system."""

import sys
import time
from datetime import datetime
sys.path.append('.')

from devsync_ai.core.error_handler import (
    ComprehensiveErrorHandler, ErrorHandlerConfig, RetryConfig, FallbackConfig,
    FallbackLevel, RetryStrategy, CircuitBreaker, CircuitBreakerState
)
from devsync_ai.core.exceptions import (
    DataValidationError, FormattingError, BlockKitError, SlackAPIError,
    NetworkError, RateLimitError, ErrorSeverity, ErrorCategory
)


def test_error_classification():
    """Test error classification and enhancement."""
    print("🧪 Testing Error Classification")
    print("=" * 50)
    
    handler = ComprehensiveErrorHandler()
    
    # Test different error types
    test_cases = [
        (ValueError("Missing required field 'title'"), DataValidationError),
        (KeyError("Invalid block structure"), BlockKitError),
        (ConnectionError("Network timeout"), NetworkError),
        (Exception("Rate limit exceeded"), RateLimitError),
        (RuntimeError("Template rendering failed"), FormattingError)
    ]
    
    for original_error, expected_type in test_cases:
        classified = handler._classify_error(original_error, "test_template")
        
        print(f"✅ {type(original_error).__name__} → {type(classified).__name__}")
        print(f"   Category: {classified.category.value}")
        print(f"   Severity: {classified.severity.value}")
        print(f"   Recoverable: {classified.recoverable}")
        
        assert isinstance(classified, expected_type), f"Expected {expected_type}, got {type(classified)}"
    
    print("✅ Error classification tests passed\n")
    return True


def test_retry_mechanisms():
    """Test retry mechanisms with different strategies."""
    print("🧪 Testing Retry Mechanisms")
    print("=" * 50)
    
    # Test exponential backoff
    retry_config = RetryConfig(
        max_attempts=3,
        base_delay=0.1,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        jitter=False  # Disable for predictable testing
    )
    
    config = ErrorHandlerConfig(retry_config=retry_config)
    handler = ComprehensiveErrorHandler(config)
    
    # Mock operation that fails twice then succeeds
    call_count = 0
    def failing_operation(data):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ValueError(f"Attempt {call_count} failed")
        return {"success": True, "attempt": call_count}
    
    # Test successful retry
    start_time = time.time()
    result = handler.handle_with_recovery(failing_operation, {"test": "data"})
    end_time = time.time()
    
    print(f"✅ Operation succeeded after {call_count} attempts")
    print(f"   Total time: {end_time - start_time:.2f}s")
    print(f"   Result type: {type(result).__name__}")
    
    # Test retry delay calculation
    error = DataValidationError("Test error")
    delays = []
    for attempt in range(3):
        delay = handler._calculate_retry_delay(attempt, error)
        delays.append(delay)
    
    print(f"✅ Retry delays: {[f'{d:.2f}s' for d in delays]}")
    
    # Verify exponential backoff
    assert delays[1] > delays[0], "Second delay should be larger"
    assert delays[2] > delays[1], "Third delay should be larger"
    
    print("✅ Retry mechanism tests passed\n")
    return True


def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("🧪 Testing Circuit Breaker")
    print("=" * 50)
    
    # Create circuit breaker with low threshold for testing
    breaker = CircuitBreaker(failure_threshold=2, timeout=1)
    
    # Test normal operation (CLOSED state)
    def successful_operation():
        return "success"
    
    result = breaker.call(successful_operation)
    print(f"✅ Normal operation: {result}")
    assert breaker.state == CircuitBreakerState.CLOSED
    
    # Test failures to trigger OPEN state
    def failing_operation():
        raise ValueError("Operation failed")
    
    failure_count = 0
    for i in range(3):
        try:
            breaker.call(failing_operation)
        except ValueError:
            failure_count += 1
            print(f"   Failure {failure_count}: Circuit breaker state = {breaker.state.value}")
    
    # Should be OPEN after 2 failures
    assert breaker.state == CircuitBreakerState.OPEN
    print("✅ Circuit breaker opened after failures")
    
    # Test that calls are rejected when OPEN
    rejected = False
    try:
        breaker.call(successful_operation)
    except SlackAPIError as e:
        rejected = True
        print(f"✅ Calls rejected when OPEN: {e}")
    
    assert rejected, "Should have rejected call when OPEN"
    
    # Test recovery by manually setting to HALF_OPEN and succeeding
    breaker.state = CircuitBreakerState.HALF_OPEN
    result = breaker.call(successful_operation)
    print(f"✅ Recovery successful: {result}")
    assert breaker.state == CircuitBreakerState.CLOSED
    
    print("✅ Circuit breaker tests passed\n")
    return True


def test_fallback_strategies():
    """Test progressive fallback strategies."""
    print("🧪 Testing Fallback Strategies")
    print("=" * 50)
    
    fallback_config = FallbackConfig(
        enable_fallbacks=True,
        max_fallback_level=FallbackLevel.PLAIN_TEXT,
        notify_users_of_degradation=True,
        include_error_details=True
    )
    
    config = ErrorHandlerConfig(fallback_config=fallback_config)
    handler = ComprehensiveErrorHandler(config)
    
    # Test data
    test_data = {
        "title": "Test Message",
        "description": "This is a test message for fallback testing",
        "author": "test_user"
    }
    
    # Test different fallback levels
    fallback_levels = [
        FallbackLevel.SIMPLE_BLOCKS,
        FallbackLevel.PLAIN_TEXT,
        FallbackLevel.MINIMAL_MESSAGE
    ]
    
    for level in fallback_levels:
        error = FormattingError("Test formatting error")
        message = handler._create_fallback_message(level, error, test_data, "test_template")
        
        print(f"✅ {level.value} fallback:")
        print(f"   Blocks: {len(message.blocks)}")
        print(f"   Text: {message.text[:50]}...")
        print(f"   Degraded: {message.metadata.get('degraded', False)}")
        
        # Verify message structure
        assert len(message.blocks) > 0, "Should have at least one block"
        assert message.text, "Should have fallback text"
        assert message.metadata.get('fallback_level') == level.value
    
    print("✅ Fallback strategy tests passed\n")
    return True


def test_rate_limit_handling():
    """Test rate limit error handling."""
    print("🧪 Testing Rate Limit Handling")
    print("=" * 50)
    
    retry_config = RetryConfig(
        max_attempts=2,
        base_delay=0.1,
        max_delay=1.0
    )
    
    config = ErrorHandlerConfig(retry_config=retry_config)
    handler = ComprehensiveErrorHandler(config)
    
    # Mock rate limited operation
    def rate_limited_operation(data):
        raise RateLimitError("Rate limit exceeded", retry_after=2)
    
    # Test rate limit handling
    start_time = time.time()
    result = handler.handle_with_recovery(rate_limited_operation, {"test": "data"})
    end_time = time.time()
    
    print(f"✅ Rate limit handled with fallback")
    print(f"   Processing time: {end_time - start_time:.2f}s")
    print(f"   Result type: {type(result).__name__}")
    print(f"   Has error metadata: {'error' in result.metadata}")
    
    # Verify it's a fallback message
    assert result.metadata.get('error') or result.metadata.get('degraded')
    
    print("✅ Rate limit handling tests passed\n")
    return True


def test_error_metrics():
    """Test error metrics collection."""
    print("🧪 Testing Error Metrics")
    print("=" * 50)
    
    config = ErrorHandlerConfig(enable_monitoring=True)
    handler = ComprehensiveErrorHandler(config)
    
    # Generate different types of errors
    errors = [
        DataValidationError("Missing field", missing_fields=["title"]),
        FormattingError("Block creation failed"),
        SlackAPIError("API call failed", status_code=500),
        NetworkError("Connection timeout"),
        RateLimitError("Rate limit exceeded", retry_after=60)
    ]
    
    # Add errors to metrics
    for error in errors:
        handler.metrics.add_error(error, recovery_time=0.5 if error.recoverable else None)
    
    # Get metrics
    metrics = handler.get_error_metrics()
    
    print(f"✅ Error metrics collected:")
    print(f"   Total errors: {metrics['total_errors']}")
    print(f"   Errors by category: {metrics['errors_by_category']}")
    print(f"   Errors by severity: {metrics['errors_by_severity']}")
    print(f"   Recovery success rate: {metrics['recovery_success_rate']:.2%}")
    print(f"   Average recovery time: {metrics['average_recovery_time']:.2f}s")
    
    # Verify metrics
    assert metrics['total_errors'] == len(errors)
    assert len(metrics['errors_by_category']) > 0
    assert len(metrics['errors_by_severity']) > 0
    
    print("✅ Error metrics tests passed\n")
    return True


def test_comprehensive_error_recovery():
    """Test comprehensive error recovery scenario."""
    print("🧪 Testing Comprehensive Error Recovery")
    print("=" * 50)
    
    # Configure for comprehensive testing
    retry_config = RetryConfig(max_attempts=3, base_delay=0.1)
    fallback_config = FallbackConfig(
        enable_fallbacks=True,
        notify_users_of_degradation=True,
        include_error_details=False  # Don't expose internal errors
    )
    
    config = ErrorHandlerConfig(
        retry_config=retry_config,
        fallback_config=fallback_config,
        enable_monitoring=True
    )
    
    handler = ComprehensiveErrorHandler(config)
    
    # Test data representing a PR notification
    pr_data = {
        "title": "Fix authentication bug",
        "description": "This PR fixes a critical authentication vulnerability",
        "author": "alice",
        "pr": {
            "number": 123,
            "state": "open",
            "url": "https://github.com/company/repo/pull/123"
        },
        "repository": "company/repo"
    }
    
    # Mock operation that always fails (to test fallback)
    def always_failing_operation(data):
        raise BlockKitError("Block validation failed", validation_errors=["Invalid block structure"])
    
    # Test comprehensive recovery
    start_time = time.time()
    result = handler.handle_with_recovery(always_failing_operation, pr_data, "pr_template")
    end_time = time.time()
    
    print(f"✅ Comprehensive recovery completed:")
    print(f"   Processing time: {end_time - start_time:.2f}s")
    print(f"   Result blocks: {len(result.blocks)}")
    print(f"   Fallback text: {result.text[:100]}...")
    print(f"   Metadata keys: {list(result.metadata.keys())}")
    
    # Verify recovery worked
    assert result.blocks, "Should have fallback blocks"
    assert result.text, "Should have fallback text"
    assert result.metadata.get('degraded') or result.metadata.get('error')
    
    # Check metrics were updated
    metrics = handler.get_error_metrics()
    print(f"   Errors recorded: {metrics['total_errors']}")
    assert metrics['total_errors'] > 0
    
    print("✅ Comprehensive error recovery tests passed\n")
    return True


def test_alerting_thresholds():
    """Test error alerting thresholds."""
    print("🧪 Testing Alerting Thresholds")
    print("=" * 50)
    
    config = ErrorHandlerConfig(
        enable_alerting=True,
        alert_threshold_errors_per_minute=3
    )
    
    handler = ComprehensiveErrorHandler(config)
    
    # Add errors below threshold
    for i in range(2):
        error = FormattingError(f"Error {i}")
        handler.metrics.add_error(error)
    
    should_alert_1 = handler.should_alert()
    print(f"✅ Below threshold (2 errors): Should alert = {should_alert_1}")
    assert not should_alert_1
    
    # Add more errors to exceed threshold
    for i in range(2, 5):
        error = FormattingError(f"Error {i}")
        handler.metrics.add_error(error)
    
    should_alert_2 = handler.should_alert()
    print(f"✅ Above threshold (5 errors): Should alert = {should_alert_2}")
    assert should_alert_2
    
    print("✅ Alerting threshold tests passed\n")
    return True


def test_configuration_validation():
    """Test configuration validation and edge cases."""
    print("🧪 Testing Configuration Validation")
    print("=" * 50)
    
    # Test with minimal configuration
    minimal_config = ErrorHandlerConfig()
    handler1 = ComprehensiveErrorHandler(minimal_config)
    print("✅ Minimal configuration accepted")
    
    # Test with custom configuration
    custom_config = ErrorHandlerConfig(
        retry_config=RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            strategy=RetryStrategy.LINEAR_BACKOFF
        ),
        fallback_config=FallbackConfig(
            max_fallback_level=FallbackLevel.ERROR_MESSAGE,
            preserve_interactive_elements=True
        )
    )
    
    handler2 = ComprehensiveErrorHandler(custom_config)
    print("✅ Custom configuration accepted")
    
    # Test configuration values are applied
    assert handler2.config.retry_config.max_attempts == 5
    assert handler2.config.fallback_config.preserve_interactive_elements == True
    
    print("✅ Configuration validation tests passed\n")
    return True


if __name__ == "__main__":
    print("🚀 Comprehensive Error Handler Test Suite")
    print("=" * 60)
    
    tests = [
        test_error_classification,
        test_retry_mechanisms,
        test_circuit_breaker,
        test_fallback_strategies,
        test_rate_limit_handling,
        test_error_metrics,
        test_comprehensive_error_recovery,
        test_alerting_thresholds,
        test_configuration_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_func.__name__} PASSED\n")
            else:
                print(f"❌ {test_func.__name__} FAILED\n")
        except Exception as e:
            print(f"❌ {test_func.__name__} FAILED with exception: {e}\n")
    
    print("📊 Test Results:")
    print("=" * 30)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Comprehensive error handling system is working perfectly!")
        print("\n💡 Key Features Demonstrated:")
        print("  ✅ Error classification and enhancement")
        print("  ✅ Exponential backoff retry mechanisms")
        print("  ✅ Circuit breaker protection")
        print("  ✅ Progressive fallback strategies")
        print("  ✅ Rate limit handling")
        print("  ✅ Comprehensive error metrics")
        print("  ✅ Alerting thresholds")
        print("  ✅ Configuration validation")
        
        print("\n📋 Error Recovery Pattern:")
        print("  try:")
        print("      rich_message = create_rich_blocks(data)")
        print("      return validate_and_format(rich_message)")
        print("  except BlockKitError:")
        print("      return create_simple_message(data)")
        print("  except DataValidationError:")
        print("      return create_error_message(data, error)")
        print("  except Exception as e:")
        print("      logger.error(f'Formatting error: {e}')")
        print("      return create_minimal_fallback(data)")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")