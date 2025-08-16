"""
Example usage of the Hook Error Handler system.

This example demonstrates how to use the comprehensive error handling
and retry mechanisms for Agent Hooks, including configuration options,
error classification, circuit breaker patterns, and fallback mechanisms.
"""

import asyncio
import logging
from datetime import datetime

from devsync_ai.core.hook_error_handler import (
    HookErrorHandler, HookError, HookErrorCategory, HookErrorSeverity,
    RetryConfig, CircuitBreakerConfig, FallbackConfig, RetryStrategy,
    NotificationQueueConfig, WebhookValidationConfig
)
from devsync_ai.core.agent_hooks import (
    AgentHook, HookConfiguration, HookExecutionResult, HookStatus,
    EnrichedEvent, ProcessedEvent, EventCategory, UrgencyLevel
)
from devsync_ai.core.exceptions import SlackAPIError, RateLimitError, NetworkError


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExampleStatusChangeHook(AgentHook):
    """Example status change hook that demonstrates error handling."""
    
    def __init__(self, hook_id: str, fail_mode: str = "none"):
        config = HookConfiguration(
            hook_id=hook_id,
            hook_type="StatusChangeHook",
            team_id="example_team",
            retry_attempts=3,
            timeout_seconds=30
        )
        super().__init__(hook_id, config)
        self.fail_mode = fail_mode
        self.call_count = 0
    
    async def can_handle(self, event: EnrichedEvent) -> bool:
        """Check if this hook can handle the event."""
        return event.event_type == "jira:issue_updated"
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """Execute the hook with potential failures for demonstration."""
        self.call_count += 1
        
        # Simulate different failure modes for demonstration
        if self.fail_mode == "network_error" and self.call_count <= 2:
            raise NetworkError("Connection timeout to Slack API")
        elif self.fail_mode == "rate_limit" and self.call_count <= 1:
            raise RateLimitError("Rate limit exceeded", retry_after=30)
        elif self.fail_mode == "slack_error" and self.call_count <= 2:
            raise SlackAPIError("Service temporarily unavailable", status_code=503)
        elif self.fail_mode == "auth_error":
            raise SlackAPIError("Invalid token", status_code=401)
        
        # Success case
        return HookExecutionResult(
            hook_id=self.hook_id,
            execution_id=f"exec_{self.call_count}",
            hook_type=self.hook_type,
            event_id=event.event_id,
            status=HookStatus.SUCCESS,
            execution_time_ms=150.0,
            notification_sent=True
        )


def create_sample_event() -> EnrichedEvent:
    """Create a sample enriched event for testing."""
    return EnrichedEvent(
        event_id="sample_event_123",
        event_type="jira:issue_updated",
        timestamp=datetime.now(),
        jira_event_data={
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "status": {"name": "In Progress"},
                    "priority": {"name": "High"},
                    "assignee": {"displayName": "John Doe"}
                }
            }
        },
        ticket_key="PROJ-123",
        project_key="PROJ",
        raw_payload={"webhookEvent": "jira:issue_updated"}
    )


async def example_basic_error_handling():
    """Example of basic error handling with default configuration."""
    print("\n=== Basic Error Handling Example ===")
    
    # Create error handler with default configuration
    error_handler = HookErrorHandler()
    
    # Create a hook that will succeed immediately
    hook = ExampleStatusChangeHook("basic_hook", fail_mode="none")
    event = create_sample_event()
    
    # Execute with error handling
    result = await error_handler.execute_with_retry(
        hook.execute, hook, event
    )
    
    print(f"Execution result: {result.status}")
    print(f"Execution time: {result.execution_time_ms:.2f}ms")
    print(f"Errors: {len(result.errors)}")
    
    return result


async def example_retry_with_recovery():
    """Example of retry mechanism with eventual recovery."""
    print("\n=== Retry with Recovery Example ===")
    
    # Configure retry behavior
    retry_config = RetryConfig(
        max_attempts=4,
        base_delay=0.5,
        max_delay=10.0,
        backoff_multiplier=2.0,
        jitter=True,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF
    )
    
    error_handler = HookErrorHandler(retry_config=retry_config)
    
    # Create a hook that fails twice then succeeds
    hook = ExampleStatusChangeHook("retry_hook", fail_mode="network_error")
    event = create_sample_event()
    
    print("Executing hook that will fail twice then succeed...")
    result = await error_handler.execute_with_retry(
        hook.execute, hook, event
    )
    
    print(f"Final status: {result.status}")
    print(f"Total attempts: {result.metadata.get('attempt', 'unknown')}")
    print(f"Errors encountered: {len(result.errors)}")
    print(f"Hook call count: {hook.call_count}")
    
    if result.errors:
        print("Errors during execution:")
        for i, error in enumerate(result.errors, 1):
            print(f"  {i}. {error}")
    
    return result


async def example_rate_limit_handling():
    """Example of rate limit error handling."""
    print("\n=== Rate Limit Handling Example ===")
    
    # Configure with higher max delay for rate limits
    retry_config = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=60.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF
    )
    
    error_handler = HookErrorHandler(retry_config=retry_config)
    
    # Create a hook that hits rate limits
    hook = ExampleStatusChangeHook("rate_limit_hook", fail_mode="rate_limit")
    event = create_sample_event()
    
    print("Executing hook that will hit rate limits...")
    result = await error_handler.execute_with_retry(
        hook.execute, hook, event
    )
    
    print(f"Final status: {result.status}")
    print(f"Rate limit handling: {'Success' if result.status == HookStatus.SUCCESS else 'Failed'}")
    
    return result


async def example_circuit_breaker():
    """Example of circuit breaker functionality."""
    print("\n=== Circuit Breaker Example ===")
    
    # Configure circuit breaker with low thresholds for demo
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=2,
        success_threshold=2,
        timeout_seconds=5,
        half_open_max_calls=2
    )
    
    error_handler = HookErrorHandler(circuit_breaker_config=circuit_breaker_config)
    
    # Create a hook that always fails with Slack errors
    hook = ExampleStatusChangeHook("circuit_breaker_hook", fail_mode="slack_error")
    event = create_sample_event()
    
    # Mock the operation name to trigger slack circuit breaker
    async def slack_operation(event):
        return await hook.execute(event)
    slack_operation.__name__ = "slack_notification_send"
    
    print("Executing multiple failing operations to trigger circuit breaker...")
    
    results = []
    for i in range(5):
        print(f"\nAttempt {i + 1}:")
        result = await error_handler.execute_with_retry(
            slack_operation, hook, event
        )
        results.append(result)
        print(f"  Status: {result.status}")
        
        # Check circuit breaker status
        cb_status = error_handler.get_circuit_breaker_status()
        slack_cb = cb_status.get('slack_api', {})
        print(f"  Circuit breaker state: {slack_cb.get('state', 'unknown')}")
        
        if slack_cb.get('state') == 'open':
            print("  Circuit breaker is now OPEN - subsequent calls will be rejected")
    
    return results


async def example_non_recoverable_error():
    """Example of handling non-recoverable errors."""
    print("\n=== Non-Recoverable Error Example ===")
    
    error_handler = HookErrorHandler()
    
    # Create a hook that fails with authentication error (non-recoverable)
    hook = ExampleStatusChangeHook("auth_error_hook", fail_mode="auth_error")
    event = create_sample_event()
    
    print("Executing hook with non-recoverable authentication error...")
    result = await error_handler.execute_with_retry(
        hook.execute, hook, event
    )
    
    print(f"Final status: {result.status}")
    print(f"Attempts made: {result.metadata.get('attempt', 'unknown')}")
    print(f"Error category: {result.metadata.get('last_error_category', 'unknown')}")
    print(f"Error severity: {result.metadata.get('last_error_severity', 'unknown')}")
    print(f"Fallback applied: {result.metadata.get('fallback_applied', False)}")
    
    return result


async def example_fallback_mechanisms():
    """Example of fallback notification mechanisms."""
    print("\n=== Fallback Mechanisms Example ===")
    
    # Configure fallback behavior
    fallback_config = FallbackConfig(
        enable_fallbacks=True,
        fallback_channels=["#system-alerts"],
        notify_admins=True,
        admin_channels=["#admin-alerts"],
        include_error_details=True
    )
    
    error_handler = HookErrorHandler(fallback_config=fallback_config)
    
    # Create a hook that always fails
    hook = ExampleStatusChangeHook("fallback_hook", fail_mode="auth_error")
    event = create_sample_event()
    
    print("Executing hook that will trigger fallback mechanisms...")
    result = await error_handler.execute_with_retry(
        hook.execute, hook, event
    )
    
    print(f"Final status: {result.status}")
    print(f"Fallback applied: {result.metadata.get('fallback_applied', False)}")
    
    # Show error metrics
    metrics = error_handler.get_error_metrics()
    print(f"Total errors: {metrics['total_errors']}")
    print(f"Fallback activations: {metrics['fallback_activations']}")
    
    return result


async def example_error_metrics():
    """Example of error metrics collection and analysis."""
    print("\n=== Error Metrics Example ===")
    
    error_handler = HookErrorHandler()
    
    # Execute several hooks with different error patterns
    hooks_and_modes = [
        ("metrics_hook_1", "network_error"),
        ("metrics_hook_2", "rate_limit"),
        ("metrics_hook_3", "slack_error"),
        ("metrics_hook_4", "none"),  # Success
        ("metrics_hook_5", "auth_error")  # Non-recoverable
    ]
    
    print("Executing multiple hooks to collect error metrics...")
    
    for hook_id, fail_mode in hooks_and_modes:
        hook = ExampleStatusChangeHook(hook_id, fail_mode)
        event = create_sample_event()
        
        result = await error_handler.execute_with_retry(
            hook.execute, hook, event
        )
        print(f"  {hook_id}: {result.status}")
    
    # Display comprehensive metrics
    metrics = error_handler.get_error_metrics()
    
    print("\n--- Error Metrics Summary ---")
    print(f"Total errors: {metrics['total_errors']}")
    print(f"Recovery success rate: {metrics['recovery_success_rate']:.2%}")
    print(f"Average recovery time: {metrics['average_recovery_time']:.2f}s")
    print(f"Circuit breaker trips: {metrics['circuit_breaker_trips']}")
    print(f"Fallback activations: {metrics['fallback_activations']}")
    
    print("\nErrors by category:")
    for category, count in metrics['errors_by_category'].items():
        print(f"  {category}: {count}")
    
    print("\nErrors by severity:")
    for severity, count in metrics['errors_by_severity'].items():
        print(f"  {severity}: {count}")
    
    print("\nCircuit breaker states:")
    for service, state in metrics['circuit_breaker_states'].items():
        print(f"  {service}: {state}")
    
    return metrics


async def example_custom_configuration():
    """Example of custom error handler configuration."""
    print("\n=== Custom Configuration Example ===")
    
    # Create custom configurations
    retry_config = RetryConfig(
        max_attempts=5,
        base_delay=0.2,
        max_delay=30.0,
        backoff_multiplier=1.5,
        jitter=True,
        strategy=RetryStrategy.LINEAR_BACKOFF
    )
    
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=10,
        half_open_max_calls=1
    )
    
    fallback_config = FallbackConfig(
        enable_fallbacks=True,
        fallback_channels=["#custom-fallback"],
        notify_admins=True,
        admin_channels=["#custom-admin"],
        include_error_details=False,
        max_fallback_attempts=3
    )
    
    # Create error handler with custom configuration
    error_handler = HookErrorHandler(
        retry_config=retry_config,
        circuit_breaker_config=circuit_breaker_config,
        fallback_config=fallback_config
    )
    
    print("Configuration applied:")
    print(f"  Max attempts: {retry_config.max_attempts}")
    print(f"  Retry strategy: {retry_config.strategy.value}")
    print(f"  Circuit breaker threshold: {circuit_breaker_config.failure_threshold}")
    print(f"  Fallbacks enabled: {fallback_config.enable_fallbacks}")
    
    # Test with custom configuration
    hook = ExampleStatusChangeHook("custom_config_hook", fail_mode="network_error")
    event = create_sample_event()
    
    result = await error_handler.execute_with_retry(
        hook.execute, hook, event
    )
    
    print(f"\nExecution result: {result.status}")
    print(f"Attempts made: {result.metadata.get('attempt', 'unknown')}")
    
    return result


async def example_webhook_validation():
    """Example of webhook payload validation and sanitization."""
    print("\n=== Webhook Validation Example ===")
    
    # Configure webhook validation
    validation_config = WebhookValidationConfig(
        enable_validation=True,
        required_fields=["webhookEvent", "issue", "timestamp"],
        max_payload_size_mb=5.0,
        sanitize_html=True,
        validate_json_structure=True
    )
    
    error_handler = HookErrorHandler(webhook_validation_config=validation_config)
    
    # Test valid payload
    valid_payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "PROJ-123",
            "fields": {
                "status": {"name": "In Progress"},
                "description": "Normal description text"
            }
        },
        "timestamp": "2023-01-01T12:00:00Z"
    }
    
    print("Testing valid payload...")
    is_valid, error_msg = error_handler.validate_webhook_payload(valid_payload)
    print(f"  Valid: {is_valid}")
    if error_msg:
        print(f"  Error: {error_msg}")
    
    # Test payload with malicious content
    malicious_payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "PROJ-123",
            "fields": {
                "status": {"name": "In Progress"},
                "description": "<script>alert('XSS attack!')</script>Normal text with <b>HTML</b>"
            }
        },
        "timestamp": "2023-01-01T12:00:00Z"
    }
    
    print("\nTesting payload sanitization...")
    sanitized = error_handler.sanitize_webhook_payload(malicious_payload)
    original_desc = malicious_payload["issue"]["fields"]["description"]
    sanitized_desc = sanitized["issue"]["fields"]["description"]
    
    print(f"  Original: {original_desc}")
    print(f"  Sanitized: {sanitized_desc}")
    print(f"  Script removed: {'<script>' not in sanitized_desc}")
    
    # Test invalid payload
    invalid_payload = {
        "webhookEvent": "jira:issue_updated",
        # Missing required 'issue' field
        "timestamp": "2023-01-01T12:00:00Z"
    }
    
    print("\nTesting invalid payload...")
    is_valid, error_msg = error_handler.validate_webhook_payload(invalid_payload)
    print(f"  Valid: {is_valid}")
    print(f"  Error: {error_msg}")
    
    return error_handler


async def example_notification_queuing():
    """Example of notification queuing for later delivery."""
    print("\n=== Notification Queuing Example ===")
    
    # Configure notification queuing
    queue_config = NotificationQueueConfig(
        enable_queuing=True,
        max_queue_size=100,
        queue_retention_hours=24,
        retry_interval_minutes=1,  # Short interval for demo
        max_retry_attempts=3
    )
    
    error_handler = HookErrorHandler(notification_queue_config=queue_config)
    
    # Queue some notifications
    print("Queuing notifications for later delivery...")
    
    notification_data_1 = {
        "message": "High priority issue updated",
        "channel": "#dev-alerts",
        "priority": "high",
        "issue_key": "PROJ-123"
    }
    
    notification_data_2 = {
        "message": "Assignment notification",
        "channel": "#team-updates",
        "priority": "medium",
        "assignee": "john.doe"
    }
    
    queue_id_1 = await error_handler.queue_notification_for_later_delivery(
        "status_hook", "event_123", notification_data_1
    )
    queue_id_2 = await error_handler.queue_notification_for_later_delivery(
        "assignment_hook", "event_124", notification_data_2
    )
    
    print(f"  Queued notification 1: {queue_id_1}")
    print(f"  Queued notification 2: {queue_id_2}")
    
    # Check queue status
    status = error_handler.get_queue_status()
    print(f"\nQueue status:")
    print(f"  Queue size: {status['queue_size']}")
    print(f"  Max size: {status['max_queue_size']}")
    print(f"  Total queued: {status['queued_notifications']}")
    
    # Process queue (simulate delivery attempts)
    print("\nProcessing notification queue...")
    delivered_count = await error_handler.process_notification_queue()
    print(f"  Delivered: {delivered_count} notifications")
    
    # Check updated status
    status = error_handler.get_queue_status()
    print(f"  Remaining in queue: {status['queue_size']}")
    print(f"  Successful deliveries: {status['successful_deliveries']}")
    
    return error_handler


async def example_slack_unavailable_scenario():
    """Example of handling Slack API unavailability with automatic queuing."""
    print("\n=== Slack Unavailable Scenario Example ===")
    
    # Configure with queuing enabled
    queue_config = NotificationQueueConfig(enable_queuing=True)
    error_handler = HookErrorHandler(notification_queue_config=queue_config)
    
    # Create a hook that fails with Slack API error
    hook = ExampleStatusChangeHook("slack_unavailable_hook", fail_mode="slack_error")
    event = create_sample_event()
    
    print("Simulating Slack API unavailability...")
    result = await error_handler.execute_with_retry(
        hook.execute, hook, event
    )
    
    print(f"Hook execution status: {result.status}")
    print(f"Notification queued: {'queued_notification_id' in result.metadata}")
    
    if 'queued_notification_id' in result.metadata:
        queue_id = result.metadata['queued_notification_id']
        print(f"Queued notification ID: {queue_id}")
        
        # Show queue status
        status = error_handler.get_queue_status()
        print(f"Queue size: {status['queue_size']}")
        
        # Simulate Slack API recovery and process queue
        print("\nSimulating Slack API recovery...")
        # Reset circuit breaker to simulate recovery
        error_handler.reset_circuit_breaker('slack_api')
        
        delivered_count = await error_handler.process_notification_queue()
        print(f"Delivered {delivered_count} queued notifications")
    
    return result


async def example_comprehensive_error_handling():
    """Example demonstrating all error handling features together."""
    print("\n=== Comprehensive Error Handling Example ===")
    
    # Configure all features
    retry_config = RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF
    )
    
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=2,
        timeout_seconds=10
    )
    
    fallback_config = FallbackConfig(
        enable_fallbacks=True,
        fallback_channels=["#system-alerts"],
        notify_admins=True
    )
    
    queue_config = NotificationQueueConfig(
        enable_queuing=True,
        max_queue_size=50
    )
    
    validation_config = WebhookValidationConfig(
        enable_validation=True,
        sanitize_html=True
    )
    
    error_handler = HookErrorHandler(
        retry_config=retry_config,
        circuit_breaker_config=circuit_breaker_config,
        fallback_config=fallback_config,
        notification_queue_config=queue_config,
        webhook_validation_config=validation_config
    )
    
    print("Comprehensive error handler configured with all features:")
    print(f"  Retry attempts: {retry_config.max_attempts}")
    print(f"  Circuit breaker threshold: {circuit_breaker_config.failure_threshold}")
    print(f"  Fallbacks enabled: {fallback_config.enable_fallbacks}")
    print(f"  Queuing enabled: {queue_config.enable_queuing}")
    print(f"  Validation enabled: {validation_config.enable_validation}")
    
    # Test webhook validation
    test_payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "PROJ-123",
            "fields": {
                "description": "<script>alert('test')</script>Clean content"
            }
        },
        "timestamp": "2023-01-01T12:00:00Z"
    }
    
    print("\nValidating and sanitizing webhook payload...")
    is_valid, _ = error_handler.validate_webhook_payload(test_payload)
    sanitized = error_handler.sanitize_webhook_payload(test_payload)
    print(f"  Payload valid: {is_valid}")
    print(f"  Content sanitized: {'<script>' not in str(sanitized)}")
    
    # Test hook execution with failures
    hook = ExampleStatusChangeHook("comprehensive_hook", fail_mode="slack_error")
    event = create_sample_event()
    
    print("\nExecuting hook with comprehensive error handling...")
    result = await error_handler.execute_with_retry(
        hook.execute, hook, event
    )
    
    print(f"Final status: {result.status}")
    print(f"Fallback applied: {result.metadata.get('fallback_applied', False)}")
    print(f"Notification queued: {'queued_notification_id' in result.metadata}")
    
    # Show comprehensive metrics
    metrics = error_handler.get_error_metrics()
    print(f"\nComprehensive metrics:")
    print(f"  Total errors: {metrics['total_errors']}")
    print(f"  Fallback activations: {metrics['fallback_activations']}")
    print(f"  Queued notifications: {metrics['queued_notifications']}")
    print(f"  Validation failures: {metrics['payload_validation_failures']}")
    
    return error_handler


async def main():
    """Run all error handling examples."""
    print("Hook Error Handler Usage Examples")
    print("=" * 50)
    
    try:
        # Run all examples
        await example_basic_error_handling()
        await example_retry_with_recovery()
        await example_rate_limit_handling()
        await example_circuit_breaker()
        await example_non_recoverable_error()
        await example_fallback_mechanisms()
        await example_error_metrics()
        await example_custom_configuration()
        await example_webhook_validation()
        await example_notification_queuing()
        await example_slack_unavailable_scenario()
        await example_comprehensive_error_handling()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        
    except Exception as e:
        logger.error(f"Error running examples: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())