#!/usr/bin/env python3
"""
Validation script for Hook Error Handler implementation.

This script validates that all requirements for task 11 are properly implemented:
- Error categorization (8.1)
- Exponential backoff retry logic (8.2)
- Circuit breaker pattern (8.3)
- Fallback notification mechanisms (8.4)
- Comprehensive error handling and recovery (8.5)
"""

import asyncio
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any

from devsync_ai.core.hook_error_handler import (
    HookErrorHandler, HookError, HookErrorCategory, HookErrorSeverity,
    RetryConfig, CircuitBreakerConfig, FallbackConfig, RetryStrategy,
    NotificationQueueConfig, WebhookValidationConfig
)
from devsync_ai.core.agent_hooks import (
    AgentHook, HookConfiguration, HookExecutionResult, HookStatus,
    EnrichedEvent
)
from devsync_ai.core.exceptions import (
    SlackAPIError, RateLimitError, NetworkError, ConfigurationError
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ValidationHook(AgentHook):
    """Hook for validation testing."""
    
    def __init__(self, hook_id: str, behavior: str = "success"):
        config = HookConfiguration(
            hook_id=hook_id,
            hook_type="ValidationHook",
            team_id="validation_team"
        )
        super().__init__(hook_id, config)
        self.behavior = behavior
        self.call_count = 0
    
    async def can_handle(self, event: EnrichedEvent) -> bool:
        return True
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        self.call_count += 1
        
        if self.behavior == "fail_twice_then_succeed" and self.call_count <= 2:
            raise NetworkError("Simulated network failure")
        elif self.behavior == "always_fail":
            raise SlackAPIError("Simulated Slack API failure", status_code=503)
        elif self.behavior == "rate_limit":
            raise RateLimitError("Rate limit exceeded", retry_after=1)
        elif self.behavior == "auth_error":
            raise SlackAPIError("Invalid token", status_code=401)
        
        return HookExecutionResult(
            hook_id=self.hook_id,
            execution_id=f"validation_exec_{self.call_count}",
            hook_type=self.hook_type,
            event_id=event.event_id,
            status=HookStatus.SUCCESS,
            execution_time_ms=100.0
        )


def create_test_event() -> EnrichedEvent:
    """Create a test event for validation."""
    return EnrichedEvent(
        event_id="validation_event_123",
        event_type="jira:issue_updated",
        timestamp=datetime.now(),
        jira_event_data={"issue": {"key": "VAL-123"}},
        ticket_key="VAL-123",
        project_key="VAL",
        raw_payload={"webhookEvent": "jira:issue_updated"}
    )


async def validate_requirement_8_1_error_categorization() -> bool:
    """Validate requirement 8.1: Error categorization."""
    logger.info("🔍 Validating Requirement 8.1: Error categorization")
    
    error_handler = HookErrorHandler()
    hook = ValidationHook("categorization_hook")
    event = create_test_event()
    
    # Test different error types and their categorization
    test_errors = [
        (SlackAPIError("Invalid token", status_code=401), HookErrorCategory.NOTIFICATION_DELIVERY, HookErrorSeverity.CRITICAL),
        (RateLimitError("Rate limited", retry_after=30), HookErrorCategory.RATE_LIMIT, HookErrorSeverity.MEDIUM),
        (NetworkError("Connection failed"), HookErrorCategory.EXTERNAL_SERVICE, HookErrorSeverity.HIGH),
        (TimeoutError("Request timeout"), HookErrorCategory.TIMEOUT, HookErrorSeverity.HIGH),
        (ConfigurationError("Invalid config"), HookErrorCategory.CONFIGURATION_ERROR, HookErrorSeverity.HIGH),
        (ValueError("Unknown error"), HookErrorCategory.HOOK_EXECUTION, HookErrorSeverity.MEDIUM)
    ]
    
    all_correct = True
    for error, expected_category, expected_severity in test_errors:
        classified = error_handler._classify_hook_error(error, hook, event)
        
        if classified.category != expected_category:
            logger.error(f"❌ Error categorization failed for {type(error).__name__}: "
                        f"expected {expected_category}, got {classified.category}")
            all_correct = False
        
        if classified.severity != expected_severity:
            logger.error(f"❌ Error severity failed for {type(error).__name__}: "
                        f"expected {expected_severity}, got {classified.severity}")
            all_correct = False
    
    if all_correct:
        logger.info("✅ Requirement 8.1: Error categorization - PASSED")
    else:
        logger.error("❌ Requirement 8.1: Error categorization - FAILED")
    
    return all_correct


async def validate_requirement_8_2_exponential_backoff() -> bool:
    """Validate requirement 8.2: Exponential backoff retry logic."""
    logger.info("🔍 Validating Requirement 8.2: Exponential backoff retry logic")
    
    retry_config = RetryConfig(
        max_attempts=4,
        base_delay=1.0,
        backoff_multiplier=2.0,
        jitter=False,  # Disable for predictable testing
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF
    )
    error_handler = HookErrorHandler(retry_config=retry_config)
    
    # Test exponential backoff calculation
    test_error = HookError("Test error", HookErrorCategory.HOOK_EXECUTION, HookErrorSeverity.MEDIUM)
    expected_delays = [1.0, 2.0, 4.0, 8.0]
    
    all_correct = True
    for attempt, expected_delay in enumerate(expected_delays):
        actual_delay = error_handler._calculate_retry_delay(attempt, test_error)
        if abs(actual_delay - expected_delay) > 0.01:  # Allow small floating point differences
            logger.error(f"❌ Exponential backoff failed for attempt {attempt}: "
                        f"expected {expected_delay}, got {actual_delay}")
            all_correct = False
    
    # Test actual retry behavior with recovery
    hook = ValidationHook("retry_hook", "fail_twice_then_succeed")
    event = create_test_event()
    
    import time
    start_time = time.time()
    result = await error_handler.execute_with_retry(hook.execute, hook, event)
    end_time = time.time()
    
    if result.status != HookStatus.SUCCESS:
        logger.error("❌ Exponential backoff retry did not result in eventual success")
        all_correct = False
    
    if hook.call_count != 3:  # Should fail twice, succeed on third
        logger.error(f"❌ Expected 3 attempts, got {hook.call_count}")
        all_correct = False
    
    # Should have taken some time due to delays (even with mocked sleep, the logic should be there)
    if len(result.errors) != 2:  # Should have 2 errors from failed attempts
        logger.error(f"❌ Expected 2 errors in result, got {len(result.errors)}")
        all_correct = False
    
    if all_correct:
        logger.info("✅ Requirement 8.2: Exponential backoff retry logic - PASSED")
    else:
        logger.error("❌ Requirement 8.2: Exponential backoff retry logic - FAILED")
    
    return all_correct


async def validate_requirement_8_3_circuit_breaker() -> bool:
    """Validate requirement 8.3: Circuit breaker pattern."""
    logger.info("🔍 Validating Requirement 8.3: Circuit breaker pattern")
    
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=2,
        success_threshold=2,
        timeout_seconds=1,
        half_open_max_calls=2
    )
    error_handler = HookErrorHandler(circuit_breaker_config=circuit_breaker_config)
    
    async def failing_slack_operation(event):
        raise SlackAPIError("Service unavailable", status_code=503)
    
    # Mock operation name to trigger slack circuit breaker
    failing_slack_operation.__name__ = "slack_api_call"
    
    hook = ValidationHook("circuit_breaker_hook")
    event = create_test_event()
    
    all_correct = True
    
    # Test circuit breaker opening after failures
    result1 = await error_handler.execute_with_retry(failing_slack_operation, hook, event)
    result2 = await error_handler.execute_with_retry(failing_slack_operation, hook, event)
    
    # Check circuit breaker state
    cb_status = error_handler.get_circuit_breaker_status()
    if cb_status['slack_api']['state'] != 'open':
        logger.error(f"❌ Circuit breaker should be open, but is {cb_status['slack_api']['state']}")
        all_correct = False
    
    # Test that subsequent calls are rejected quickly
    result3 = await error_handler.execute_with_retry(failing_slack_operation, hook, event)
    if "Circuit breaker is OPEN" not in str(result3.errors):
        logger.error("❌ Circuit breaker should reject calls when open")
        all_correct = False
    
    # Test circuit breaker reset functionality
    success = error_handler.reset_circuit_breaker('slack_api')
    if not success:
        logger.error("❌ Circuit breaker reset failed")
        all_correct = False
    
    cb_status_after_reset = error_handler.get_circuit_breaker_status()
    if cb_status_after_reset['slack_api']['state'] != 'closed':
        logger.error("❌ Circuit breaker should be closed after reset")
        all_correct = False
    
    if all_correct:
        logger.info("✅ Requirement 8.3: Circuit breaker pattern - PASSED")
    else:
        logger.error("❌ Requirement 8.3: Circuit breaker pattern - FAILED")
    
    return all_correct


async def validate_requirement_8_4_fallback_mechanisms() -> bool:
    """Validate requirement 8.4: Fallback notification mechanisms."""
    logger.info("🔍 Validating Requirement 8.4: Fallback notification mechanisms")
    
    fallback_config = FallbackConfig(
        enable_fallbacks=True,
        fallback_channels=["#fallback-alerts"],
        notify_admins=True,
        admin_channels=["#admin-alerts"],
        include_error_details=True
    )
    
    queue_config = NotificationQueueConfig(
        enable_queuing=True,
        max_queue_size=100,
        retry_interval_minutes=1,
        max_retry_attempts=3
    )
    
    error_handler = HookErrorHandler(
        fallback_config=fallback_config,
        notification_queue_config=queue_config
    )
    
    hook = ValidationHook("fallback_hook", "auth_error")  # Non-recoverable error
    event = create_test_event()
    
    all_correct = True
    
    # Test fallback mechanism activation
    result = await error_handler.execute_with_retry(hook.execute, hook, event)
    
    if result.status != HookStatus.FAILED:
        logger.error("❌ Hook should fail with non-recoverable error")
        all_correct = False
    
    if not result.metadata.get('fallback_applied'):
        logger.error("❌ Fallback mechanisms should be applied")
        all_correct = False
    
    # Test notification queuing for Slack unavailability
    hook_slack_error = ValidationHook("slack_unavailable_hook", "always_fail")
    result_queue = await error_handler.execute_with_retry(hook_slack_error.execute, hook_slack_error, event)
    
    if 'queued_notification_id' not in result_queue.metadata:
        logger.error("❌ Notification should be queued when Slack API is unavailable")
        all_correct = False
    
    # Test queue processing
    queue_status_before = error_handler.get_queue_status()
    delivered_count = await error_handler.process_notification_queue()
    queue_status_after = error_handler.get_queue_status()
    
    if queue_status_before['queue_size'] == 0:
        logger.error("❌ Queue should have notifications before processing")
        all_correct = False
    
    # Test queue status reporting
    queue_status = error_handler.get_queue_status()
    required_keys = ['queue_size', 'max_queue_size', 'queued_notifications', 'successful_deliveries']
    for key in required_keys:
        if key not in queue_status:
            logger.error(f"❌ Queue status missing key: {key}")
            all_correct = False
    
    if all_correct:
        logger.info("✅ Requirement 8.4: Fallback notification mechanisms - PASSED")
    else:
        logger.error("❌ Requirement 8.4: Fallback notification mechanisms - FAILED")
    
    return all_correct


async def validate_requirement_8_5_comprehensive_error_handling() -> bool:
    """Validate requirement 8.5: Comprehensive error handling and recovery."""
    logger.info("🔍 Validating Requirement 8.5: Comprehensive error handling and recovery")
    
    # Test webhook payload validation and sanitization
    validation_config = WebhookValidationConfig(
        enable_validation=True,
        required_fields=["webhookEvent", "issue", "timestamp"],
        max_payload_size_mb=1.0,
        sanitize_html=True
    )
    
    error_handler = HookErrorHandler(webhook_validation_config=validation_config)
    
    all_correct = True
    
    # Test payload validation
    valid_payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {"key": "TEST-123", "fields": {}},
        "timestamp": "2023-01-01T00:00:00Z"
    }
    
    is_valid, error_msg = error_handler.validate_webhook_payload(valid_payload)
    if not is_valid:
        logger.error(f"❌ Valid payload should pass validation: {error_msg}")
        all_correct = False
    
    # Test payload sanitization
    malicious_payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "TEST-123",
            "fields": {
                "description": "<script>alert('xss')</script>Clean content"
            }
        },
        "timestamp": "2023-01-01T00:00:00Z"
    }
    
    sanitized = error_handler.sanitize_webhook_payload(malicious_payload)
    if "<script>" in str(sanitized):
        logger.error("❌ Malicious content should be sanitized")
        all_correct = False
    
    # Test comprehensive error metrics
    metrics = error_handler.get_error_metrics()
    required_metrics = [
        'total_errors', 'errors_by_category', 'errors_by_severity',
        'recovery_success_rate', 'circuit_breaker_states', 'queue_status'
    ]
    
    for metric in required_metrics:
        if metric not in metrics:
            logger.error(f"❌ Missing error metric: {metric}")
            all_correct = False
    
    # Test error logging and monitoring
    hook = ValidationHook("monitoring_hook", "fail_twice_then_succeed")
    event = create_test_event()
    
    result = await error_handler.execute_with_retry(hook.execute, hook, event)
    
    # Check that errors were properly logged and tracked
    updated_metrics = error_handler.get_error_metrics()
    if updated_metrics['total_errors'] == 0:
        logger.error("❌ Errors should be tracked in metrics")
        all_correct = False
    
    if updated_metrics['recovery_success_rate'] == 0:
        logger.error("❌ Recovery should be tracked in metrics")
        all_correct = False
    
    # Test metrics reset functionality
    error_handler.reset_metrics()
    reset_metrics = error_handler.get_error_metrics()
    if reset_metrics['total_errors'] != 0:
        logger.error("❌ Metrics should be reset to zero")
        all_correct = False
    
    if all_correct:
        logger.info("✅ Requirement 8.5: Comprehensive error handling and recovery - PASSED")
    else:
        logger.error("❌ Requirement 8.5: Comprehensive error handling and recovery - FAILED")
    
    return all_correct


async def validate_all_requirements() -> bool:
    """Validate all requirements for task 11."""
    logger.info("🚀 Starting comprehensive validation of Hook Error Handler implementation")
    logger.info("=" * 80)
    
    validation_results = []
    
    # Validate each requirement
    validation_results.append(await validate_requirement_8_1_error_categorization())
    validation_results.append(await validate_requirement_8_2_exponential_backoff())
    validation_results.append(await validate_requirement_8_3_circuit_breaker())
    validation_results.append(await validate_requirement_8_4_fallback_mechanisms())
    validation_results.append(await validate_requirement_8_5_comprehensive_error_handling())
    
    logger.info("=" * 80)
    
    # Summary
    passed_count = sum(validation_results)
    total_count = len(validation_results)
    
    if all(validation_results):
        logger.info(f"🎉 ALL REQUIREMENTS PASSED ({passed_count}/{total_count})")
        logger.info("✅ Hook Error Handler implementation is complete and meets all requirements!")
        return True
    else:
        logger.error(f"❌ SOME REQUIREMENTS FAILED ({passed_count}/{total_count})")
        logger.error("🔧 Please review and fix the failing requirements.")
        return False


async def main():
    """Main validation function."""
    try:
        success = await validate_all_requirements()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"💥 Validation failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())