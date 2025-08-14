#!/usr/bin/env python3
"""Example usage of comprehensive error handling system."""

import sys
import time
from datetime import datetime
sys.path.append('.')

from devsync_ai.core.error_handler import (
    ComprehensiveErrorHandler, ErrorHandlerConfig, RetryConfig, FallbackConfig,
    FallbackLevel, RetryStrategy, default_error_handler
)
from devsync_ai.core.exceptions import (
    DataValidationError, FormattingError, BlockKitError, SlackAPIError,
    NetworkError, RateLimitError
)


def example_basic_error_recovery():
    """Example: Basic error recovery with retries."""
    print("🔄 Basic Error Recovery Example")
    print("=" * 50)
    
    # Configure error handler
    config = ErrorHandlerConfig(
        retry_config=RetryConfig(
            max_attempts=3,
            base_delay=0.5,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        ),
        fallback_config=FallbackConfig(
            enable_fallbacks=True,
            notify_users_of_degradation=True
        )
    )
    
    handler = ComprehensiveErrorHandler(config)
    
    # Mock operation that fails twice then succeeds
    attempt_count = 0
    def unreliable_operation(data):
        nonlocal attempt_count
        attempt_count += 1
        
        if attempt_count <= 2:
            raise NetworkError(f"Network timeout on attempt {attempt_count}")
        
        # Success on third attempt
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ Successfully processed: {data.get('title', 'Unknown')}"
                    }
                }
            ],
            "text": f"Success: {data.get('title', 'Unknown')}",
            "metadata": {"success": True, "attempts": attempt_count}
        }
    
    # Test data
    test_data = {
        "title": "Important System Update",
        "description": "Critical system maintenance notification",
        "author": "system"
    }
    
    print(f"🚀 Processing operation with unreliable service...")
    start_time = time.time()
    
    result = handler.handle_with_recovery(unreliable_operation, test_data, "system_update")
    
    end_time = time.time()
    
    print(f"✅ Operation completed in {end_time - start_time:.2f}s")
    print(f"   Attempts made: {attempt_count}")
    print(f"   Result type: {type(result).__name__}")
    print(f"   Success: {result.metadata.get('success', False) if hasattr(result, 'metadata') else 'N/A'}")
    
    # Show metrics
    metrics = handler.get_error_metrics()
    print(f"📊 Error metrics: {metrics['total_errors']} errors recorded")
    
    return result


def example_progressive_fallbacks():
    """Example: Progressive fallback strategies."""
    print("\n🎯 Progressive Fallback Example")
    print("=" * 50)
    
    # Configure with different fallback levels
    configs = [
        ("Rich Formatting", FallbackLevel.SIMPLE_BLOCKS),
        ("Simple Blocks", FallbackLevel.PLAIN_TEXT),
        ("Plain Text", FallbackLevel.MINIMAL_MESSAGE),
        ("Minimal", FallbackLevel.ERROR_MESSAGE)
    ]
    
    test_data = {
        "title": "PR #123: Fix authentication bug",
        "description": "This PR addresses a critical security vulnerability in the authentication system",
        "author": "alice",
        "pr": {
            "number": 123,
            "state": "open",
            "url": "https://github.com/company/repo/pull/123"
        }
    }
    
    for config_name, max_level in configs:
        print(f"\n🔧 Testing {config_name} → {max_level.value}")
        
        fallback_config = FallbackConfig(
            max_fallback_level=max_level,
            notify_users_of_degradation=True,
            include_error_details=False
        )
        
        config = ErrorHandlerConfig(fallback_config=fallback_config)
        handler = ComprehensiveErrorHandler(config)
        
        # Mock operation that always fails
        def always_failing_operation(data):
            raise BlockKitError("Block validation failed - invalid structure")
        
        result = handler.handle_with_recovery(always_failing_operation, test_data, "pr_template")
        
        print(f"   Blocks: {len(result.blocks)}")
        print(f"   Text: {result.text[:60]}...")
        print(f"   Degraded: {result.metadata.get('degraded', False)}")
        print(f"   Fallback level: {result.metadata.get('fallback_level', 'N/A')}")


def example_rate_limit_handling():
    """Example: Rate limit error handling."""
    print("\n⏱️ Rate Limit Handling Example")
    print("=" * 50)
    
    # Configure for rate limit scenarios
    config = ErrorHandlerConfig(
        retry_config=RetryConfig(
            max_attempts=2,
            base_delay=0.2,
            max_delay=2.0
        )
    )
    
    handler = ComprehensiveErrorHandler(config)
    
    # Mock rate-limited API
    def rate_limited_api(data):
        raise RateLimitError(
            "API rate limit exceeded - too many requests",
            retry_after=3  # Slack says wait 3 seconds
        )
    
    test_data = {
        "title": "Urgent: Production Alert",
        "description": "Critical system alert requiring immediate attention",
        "severity": "critical"
    }
    
    print("🚨 Attempting to send urgent alert...")
    start_time = time.time()
    
    result = handler.handle_with_recovery(rate_limited_api, test_data, "alert_template")
    
    end_time = time.time()
    
    print(f"✅ Alert processed in {end_time - start_time:.2f}s")
    print(f"   Fallback used: {result.metadata.get('error', False) or result.metadata.get('degraded', False)}")
    print(f"   Message delivered: {len(result.blocks)} blocks")
    
    # In production, you might queue the message for later retry
    if result.metadata.get('error'):
        print("   📝 Note: Message queued for retry after rate limit expires")


def example_comprehensive_monitoring():
    """Example: Comprehensive error monitoring."""
    print("\n📊 Comprehensive Monitoring Example")
    print("=" * 50)
    
    # Configure with monitoring enabled
    config = ErrorHandlerConfig(
        enable_monitoring=True,
        enable_alerting=True,
        alert_threshold_errors_per_minute=3
    )
    
    handler = ComprehensiveErrorHandler(config)
    
    # Simulate various error scenarios
    error_scenarios = [
        ("Data validation", lambda d: DataValidationError("Missing required field 'title'")),
        ("Block Kit validation", lambda d: BlockKitError("Invalid block structure")),
        ("Network timeout", lambda d: NetworkError("Connection timeout after 30s")),
        ("Slack API error", lambda d: SlackAPIError("API call failed", status_code=500)),
        ("Rate limiting", lambda d: RateLimitError("Rate limit exceeded", retry_after=60))
    ]
    
    test_data = {"title": "Test Message", "author": "system"}
    
    print("🔄 Simulating various error scenarios...")
    
    for scenario_name, error_func in error_scenarios:
        print(f"\n   {scenario_name}:")
        
        def failing_operation(data):
            raise error_func(data)
        
        result = handler.handle_with_recovery(failing_operation, test_data, "test_template")
        
        print(f"     Handled: {type(result).__name__}")
        print(f"     Blocks: {len(result.blocks)}")
    
    # Get comprehensive metrics
    metrics = handler.get_error_metrics()
    
    print(f"\n📈 Final Metrics:")
    print(f"   Total errors: {metrics['total_errors']}")
    print(f"   By category: {metrics['errors_by_category']}")
    print(f"   By severity: {metrics['errors_by_severity']}")
    print(f"   Recovery rate: {metrics['recovery_success_rate']:.1%}")
    print(f"   Avg recovery time: {metrics['average_recovery_time']:.2f}s")
    
    # Check if alerting threshold is exceeded
    should_alert = handler.should_alert()
    print(f"   Should alert: {should_alert}")
    
    if should_alert:
        print("   🚨 Alert: Error rate exceeds threshold!")
        print("   📧 Notification sent to operations team")


def example_real_world_integration():
    """Example: Real-world integration pattern."""
    print("\n🌍 Real-World Integration Example")
    print("=" * 50)
    
    # Production-like configuration
    config = ErrorHandlerConfig(
        retry_config=RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter=True
        ),
        fallback_config=FallbackConfig(
            enable_fallbacks=True,
            max_fallback_level=FallbackLevel.PLAIN_TEXT,
            notify_users_of_degradation=False,  # Don't confuse users
            include_error_details=False  # Don't expose internals
        ),
        enable_monitoring=True,
        enable_circuit_breaker=True
    )
    
    handler = ComprehensiveErrorHandler(config)
    
    # Simulate real message formatting pipeline
    def format_pr_notification(data):
        """Simulate complex PR notification formatting."""
        
        # Simulate various potential failures
        import random
        failure_type = random.choice([
            "success",
            "data_validation", 
            "block_kit",
            "network",
            "success"  # Higher chance of success
        ])
        
        if failure_type == "data_validation":
            raise DataValidationError("Missing PR data", missing_fields=["number", "title"])
        elif failure_type == "block_kit":
            raise BlockKitError("Block exceeds size limit")
        elif failure_type == "network":
            raise NetworkError("GitHub API timeout")
        
        # Success case - return SlackMessage object
        from devsync_ai.core.message_formatter import SlackMessage
        
        return SlackMessage(
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🔄 PR #{data['pr']['number']}: {data['title']}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Author:* {data['author']}\n*Status:* {data['pr']['state']}"
                    }
                }
            ],
            text=f"PR #{data['pr']['number']}: {data['title']} by {data['author']}",
            metadata={"template_type": "pr_notification", "success": True}
        )
    
    # Test with multiple PR notifications
    pr_notifications = [
        {
            "title": "Fix authentication vulnerability",
            "author": "alice",
            "pr": {"number": 101, "state": "ready_for_review"}
        },
        {
            "title": "Update API documentation", 
            "author": "bob",
            "pr": {"number": 102, "state": "approved"}
        },
        {
            "title": "Add comprehensive tests",
            "author": "carol", 
            "pr": {"number": 103, "state": "merged"}
        }
    ]
    
    print("🔄 Processing PR notifications with error handling...")
    
    successful = 0
    degraded = 0
    failed = 0
    
    for i, pr_data in enumerate(pr_notifications, 1):
        print(f"\n   PR {i}: {pr_data['title']}")
        
        result = handler.handle_with_recovery(format_pr_notification, pr_data, "pr_template")
        
        if result.metadata.get('success'):
            successful += 1
            print(f"     ✅ Success: Rich formatting")
        elif result.metadata.get('degraded'):
            degraded += 1
            print(f"     ⚠️ Degraded: Fallback formatting")
        else:
            failed += 1
            print(f"     ❌ Failed: Error message")
    
    print(f"\n📊 Processing Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ⚠️ Degraded: {degraded}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Success rate: {(successful + degraded) / len(pr_notifications):.1%}")
    
    # Final metrics
    final_metrics = handler.get_error_metrics()
    print(f"\n📈 System Health:")
    print(f"   Total errors handled: {final_metrics['total_errors']}")
    print(f"   Recovery success rate: {final_metrics['recovery_success_rate']:.1%}")
    print(f"   Circuit breaker states: {final_metrics['circuit_breaker_states']}")


if __name__ == "__main__":
    print("🚀 Comprehensive Error Handling Examples")
    print("=" * 60)
    
    # Run examples
    example_basic_error_recovery()
    example_progressive_fallbacks()
    example_rate_limit_handling()
    example_comprehensive_monitoring()
    example_real_world_integration()
    
    print(f"\n🎉 Examples Complete!")
    
    print(f"\n💡 Key Error Handling Features Demonstrated:")
    print(f"  ✅ Automatic retry with exponential backoff")
    print(f"  ✅ Progressive fallback strategies")
    print(f"  ✅ Rate limit handling with proper delays")
    print(f"  ✅ Comprehensive error classification")
    print(f"  ✅ Circuit breaker protection")
    print(f"  ✅ Error metrics and monitoring")
    print(f"  ✅ Alerting thresholds")
    print(f"  ✅ Real-world integration patterns")
    
    print(f"\n📋 Error Recovery Pattern:")
    print(f"  try:")
    print(f"      rich_message = create_rich_blocks(data)")
    print(f"      return validate_and_format(rich_message)")
    print(f"  except BlockKitError:")
    print(f"      return create_simple_message(data)")
    print(f"  except DataValidationError:")
    print(f"      return create_error_message(data, error)")
    print(f"  except Exception as e:")
    print(f"      logger.error(f'Formatting error: {{e}}')")
    print(f"      return create_minimal_fallback(data)")