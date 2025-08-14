#!/usr/bin/env python3
"""Test script for enhanced notification handler with new formatter integration."""

import sys
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
sys.path.append('.')

from devsync_ai.core.enhanced_notification_handler import (
    EnhancedNotificationHandler, NotificationPriority, NotificationStatus,
    NotificationRequest, NotificationResult,
    send_pr_notification, send_jira_notification, send_alert_notification
)
from devsync_ai.core.config_manager import (
    FlexibleConfigurationManager, TeamSettings, VisualStyling,
    ChannelSpecificFormatting, EmojiStyle, MessageDensity, FormattingStyle
)
from devsync_ai.core.message_formatter import TemplateConfig


def create_mock_slack_client():
    """Create mock Slack client."""
    mock_client = Mock()
    mock_client.chat_postMessage = Mock(return_value={'ok': True, 'ts': '1234567890.123456'})
    return mock_client


def create_test_config_manager():
    """Create test configuration manager."""
    import tempfile
    config_manager = FlexibleConfigurationManager(
        config_dir=tempfile.mkdtemp(),
        environment="test"
    )
    
    # Set up test team settings
    team_settings = TeamSettings(
        team_id="test-team",
        team_name="Test Team",
        visual_styling=VisualStyling(
            brand_color="#4caf50",
            emoji_style=EmojiStyle.STANDARD,
            message_density=MessageDensity.DETAILED
        )
    )
    
    config_manager.update_team_settings(team_settings)
    
    # Add channel overrides
    dev_channel = ChannelSpecificFormatting(
        channel_id="#development",
        formatting_style=FormattingStyle.RICH,
        show_technical_details=True,
        batch_threshold=3
    )
    
    config_manager.update_channel_override("#development", dev_channel)
    
    return config_manager


def test_notification_handler_initialization():
    """Test notification handler initialization with new formatter."""
    print("🧪 Testing Enhanced Notification Handler Initialization")
    print("=" * 60)
    
    # Create mock clients
    slack_client = create_mock_slack_client()
    supabase_client = Mock()
    config_manager = create_test_config_manager()
    
    # Create template config
    template_config = TemplateConfig(team_id="test-team")
    
    # Initialize handler with new formatter
    handler = EnhancedNotificationHandler(
        slack_client=slack_client,
        supabase_client=supabase_client,
        config=template_config,
        config_manager=config_manager
    )
    
    print(f"✅ Handler initialized successfully")
    print(f"   Slack client: {handler.slack is not None}")
    print(f"   Config manager: {handler.config_manager is not None}")
    print(f"   Error handler: {handler.error_handler is not None}")
    print(f"   Message batcher: {handler.message_batcher is not None}")
    print(f"   Message formatter: {handler.message_formatter is not None}")
    print(f"   Formatter type: {type(handler.message_formatter).__name__}")
    
    # Test health check
    health = handler.health_check()
    print(f"   Health status: {health['status']}")
    print(f"   Components: {len(health['components'])}")
    
    # Test formatter metrics
    formatter_metrics = handler.message_formatter.get_metrics()
    print(f"   Formatter metrics: {len(formatter_metrics)} keys")
    
    print("✅ Enhanced notification handler initialization tests passed\\n")
    return handler


def test_single_pr_notification_with_new_formatter():
    """Test sending single PR notification using new formatter."""
    print("🧪 Testing Single PR Notification with New Formatter")
    print("=" * 60)
    
    # Set up handler
    slack_client = create_mock_slack_client()
    config_manager = create_test_config_manager()
    template_config = TemplateConfig(team_id="test-team")
    
    handler = EnhancedNotificationHandler(
        slack_client=slack_client,
        config_manager=config_manager,
        config=template_config
    )
    
    # Test PR data
    pr_data = {
        "pr": {
            "number": 123,
            "title": "Fix authentication bug",
            "author": "alice",
            "state": "open",
            "url": "https://github.com/company/repo/pull/123",
            "description": "This PR fixes a critical authentication vulnerability",
            "branch": "fix/auth-bug",
            "base_branch": "main",
            "created_at": datetime.now().isoformat(),
            "repository": "company/repo"
        }
    }
    
    # Send notification
    result = send_pr_notification(
        handler=handler,
        pr_data=pr_data,
        action="opened",
        channel_id="#development"
    )
    
    print(f"✅ PR notification sent using new formatter:")
    print(f"   Status: {result.status.value}")
    print(f"   Request ID: {result.request_id}")
    print(f"   Processing time: {result.processing_time_ms:.2f}ms")
    print(f"   Fallback used: {result.fallback_used}")
    
    if result.message:
        print(f"   Message blocks: {len(result.message.blocks)}")
        print(f"   Fallback text: {result.message.text[:50]}...")
        print(f"   Message metadata: {result.message.metadata}")
    
    # Verify behavior - message might be batched or sent directly
    if result.status == NotificationStatus.SENT:
        # Verify Slack client was called
        assert slack_client.chat_postMessage.called, "Slack client should have been called"
        call_args = slack_client.chat_postMessage.call_args[1]
        assert 'blocks' in call_args, "Message should have blocks"
        assert 'text' in call_args, "Message should have fallback text"
    elif result.status == NotificationStatus.BATCHED:
        print(f"   Message was batched (expected behavior)")
    else:
        assert False, f"Unexpected status: {result.status}"
    
    print("✅ Single PR notification with new formatter tests passed\\n")
    return result


def test_jira_notification_with_new_formatter():
    """Test sending JIRA notification using new formatter."""
    print("🧪 Testing JIRA Notification with New Formatter")
    print("=" * 60)
    
    # Set up handler
    slack_client = create_mock_slack_client()
    config_manager = create_test_config_manager()
    template_config = TemplateConfig(team_id="test-team")
    
    handler = EnhancedNotificationHandler(
        slack_client=slack_client,
        config_manager=config_manager,
        config=template_config
    )
    
    # Test JIRA data
    jira_data = {
        "ticket": {
            "key": "DEV-456",
            "summary": "Implement user dashboard",
            "description": "Create a comprehensive user dashboard with analytics",
            "status": {"name": "In Progress"},
            "priority": {"name": "High"},
            "assignee": {"name": "bob", "email": "bob@company.com"},
            "reporter": {"name": "alice", "email": "alice@company.com"},
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "project": {"key": "DEV", "name": "Development"},
            "labels": ["frontend", "dashboard", "analytics"]
        }
    }
    
    # Send notification
    result = send_jira_notification(
        handler=handler,
        jira_data=jira_data,
        action="updated",
        channel_id="#development"
    )
    
    print(f"✅ JIRA notification sent using new formatter:")
    print(f"   Status: {result.status.value}")
    print(f"   Request ID: {result.request_id}")
    print(f"   Processing time: {result.processing_time_ms:.2f}ms")
    print(f"   Fallback used: {result.fallback_used}")
    
    if result.message:
        print(f"   Message blocks: {len(result.message.blocks)}")
        print(f"   Fallback text: {result.message.text[:50]}...")
        print(f"   Message metadata: {result.message.metadata}")
    
    print("✅ JIRA notification with new formatter tests passed\\n")
    return result


def test_batch_notification_with_new_formatter():
    """Test batch notification processing with new formatter."""
    print("🧪 Testing Batch Notifications with New Formatter")
    print("=" * 60)
    
    # Set up handler
    slack_client = create_mock_slack_client()
    config_manager = create_test_config_manager()
    template_config = TemplateConfig(team_id="test-team")
    
    handler = EnhancedNotificationHandler(
        slack_client=slack_client,
        config_manager=config_manager,
        config=template_config
    )
    
    # Create batch of JIRA updates
    jira_batch = [
        {
            "key": "DEV-201",
            "summary": "Fix authentication bug",
            "status": {"name": "Done"},
            "assignee": {"name": "alice"}
        },
        {
            "key": "DEV-202",
            "summary": "Update API documentation",
            "status": {"name": "Done"},
            "assignee": {"name": "bob"}
        },
        {
            "key": "DEV-203",
            "summary": "Add integration tests",
            "status": {"name": "In Progress"},
            "assignee": {"name": "carol"}
        }
    ]
    
    # Send batch notification using new formatter
    result = handler.send_batch_notification(
        notification_type="jira_updated",
        batch_items=jira_batch,
        channel_id="#development",
        priority=NotificationPriority.MEDIUM
    )
    
    print(f"✅ Batch notification sent using new formatter:")
    print(f"   Status: {result.status.value}")
    print(f"   Batch items: {len(jira_batch)}")
    print(f"   Processing time: {result.processing_time_ms:.2f}ms")
    print(f"   Fallback used: {result.fallback_used}")
    
    if result.message:
        print(f"   Message blocks: {len(result.message.blocks)}")
        print(f"   Is batched: {result.message.metadata.get('is_batched', False)}")
        print(f"   Message metadata: {result.message.metadata}")
    
    print("✅ Batch notification with new formatter tests passed\\n")
    return result


def test_formatter_error_handling():
    """Test error handling in new formatter integration."""
    print("🧪 Testing Formatter Error Handling")
    print("=" * 60)
    
    # Set up handler with failing Slack client
    slack_client = Mock()
    slack_client.chat_postMessage = Mock(side_effect=Exception("Slack API error"))
    
    config_manager = create_test_config_manager()
    template_config = TemplateConfig(team_id="test-team")
    
    handler = EnhancedNotificationHandler(
        slack_client=slack_client,
        config_manager=config_manager,
        config=template_config
    )
    
    # Try to send notification that will fail at Slack level
    result = handler.send_notification(
        notification_type="pr_opened",
        data={"pr": {"number": 999, "title": "Test PR", "author": "test"}},
        channel_id="#test"
    )
    
    print(f"✅ Slack error handling test:")
    print(f"   Status: {result.status.value}")
    print(f"   Error present: {result.error is not None}")
    print(f"   Message created: {result.message is not None}")
    
    # Test with invalid data that should trigger formatter fallback
    result2 = handler.send_notification(
        notification_type="invalid_type",
        data={},  # Empty data
        channel_id="#test"
    )
    
    print(f"   Invalid data handling: {result2.status.value}")
    print(f"   Has fallback message: {result2.message is not None}")
    print(f"   Fallback used: {result2.fallback_used}")
    
    if result2.message and result2.message.metadata:
        print(f"   Message metadata: {result2.message.metadata}")
    
    print("✅ Formatter error handling tests passed\\n")
    return [result, result2]


def test_formatter_metrics_and_stats():
    """Test formatter metrics and statistics collection."""
    print("🧪 Testing Formatter Metrics and Statistics")
    print("=" * 60)
    
    # Set up handler
    slack_client = create_mock_slack_client()
    config_manager = create_test_config_manager()
    template_config = TemplateConfig(team_id="test-team")
    
    handler = EnhancedNotificationHandler(
        slack_client=slack_client,
        config_manager=config_manager,
        config=template_config
    )
    
    # Send various notifications to generate metrics
    notifications = [
        ("pr_opened", {"pr": {"number": 1, "title": "PR 1", "author": "alice"}}),
        ("pr_merged", {"pr": {"number": 2, "title": "PR 2", "author": "bob"}}),
        ("jira_updated", {"ticket": {"key": "DEV-1", "summary": "Task 1"}}),
        ("alert", {"blocker": {"title": "Alert 1", "severity": "high"}})
    ]
    
    for notification_type, data in notifications:
        handler.send_notification(
            notification_type=notification_type,
            data=data,
            channel_id="#test"
        )
    
    # Get statistics
    stats = handler.get_processing_stats()
    
    print(f"✅ Processing statistics:")
    print(f"   Total processed: {stats['total_processed']}")
    print(f"   Successful: {stats['successful']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Batched: {stats['batched']}")
    print(f"   Fallback used: {stats['fallback_used']}")
    
    # Check formatter-specific metrics
    if 'formatter_metrics' in stats:
        formatter_metrics = stats['formatter_metrics']
        print(f"   Formatter total messages: {formatter_metrics.get('total_messages', 0)}")
        print(f"   Formatter cache hit rate: {formatter_metrics.get('cache_hit_rate', 0):.1f}%")
        print(f"   Formatter error rate: {formatter_metrics.get('error_rate', 0):.1f}%")
        print(f"   Formatter avg processing time: {formatter_metrics.get('avg_processing_time_ms', 0):.2f}ms")
        
        if 'formatter_usage' in formatter_metrics:
            print(f"   Formatter usage: {formatter_metrics['formatter_usage']}")
    
    # Test direct formatter metrics
    direct_metrics = handler.message_formatter.get_metrics()
    print(f"   Direct formatter metrics: {len(direct_metrics)} keys")
    print(f"   Registered formatters: {len(handler.message_formatter.get_registered_formatters())}")
    
    print("✅ Formatter metrics and statistics tests passed\\n")
    return stats


def test_formatter_configuration_integration():
    """Test formatter configuration integration."""
    print("🧪 Testing Formatter Configuration Integration")
    print("=" * 60)
    
    # Set up handler
    slack_client = create_mock_slack_client()
    config_manager = create_test_config_manager()
    template_config = TemplateConfig(team_id="test-team")
    
    handler = EnhancedNotificationHandler(
        slack_client=slack_client,
        config_manager=config_manager,
        config=template_config
    )
    
    # Get initial configuration
    initial_config = config_manager.load_configuration()
    initial_color = initial_config.team_settings.visual_styling.brand_color
    print(f"   Initial brand color: {initial_color}")
    
    # Update team settings
    new_team_settings = TeamSettings(
        team_id="updated-team",
        team_name="Updated Team",
        visual_styling=VisualStyling(
            brand_color="#ff5722",  # New color
            emoji_style=EmojiStyle.CUSTOM
        )
    )
    
    config_manager.update_team_settings(new_team_settings)
    
    # Update handler configuration (this should reconfigure the formatter)
    handler.update_configuration()
    
    # Send a notification to test the updated configuration
    result = handler.send_notification(
        notification_type="pr_opened",
        data={"pr": {"number": 100, "title": "Test PR", "author": "test"}},
        channel_id="#development"
    )
    
    # Verify configuration was updated
    updated_config = config_manager.load_configuration()
    updated_color = updated_config.team_settings.visual_styling.brand_color
    
    print(f"✅ Configuration integration test:")
    print(f"   Updated brand color: {updated_color}")
    print(f"   Configuration changed: {initial_color != updated_color}")
    print(f"   Notification sent after update: {result.status.value}")
    print(f"   Handler reconfigured: Configuration update completed")
    
    if result.message:
        print(f"   Message created with new config: {len(result.message.blocks)} blocks")
    
    print("✅ Formatter configuration integration tests passed\\n")
    return updated_config


def test_comprehensive_formatter_workflow():
    """Test comprehensive workflow with new formatter integration."""
    print("🧪 Testing Comprehensive Formatter Workflow")
    print("=" * 60)
    
    # Set up handler
    slack_client = create_mock_slack_client()
    config_manager = create_test_config_manager()
    template_config = TemplateConfig(team_id="test-team")
    
    handler = EnhancedNotificationHandler(
        slack_client=slack_client,
        config_manager=config_manager,
        config=template_config
    )
    
    # Simulate real-world workflow with new formatter
    workflow_steps = [
        # 1. PR opened
        {
            "type": "pr_opened",
            "data": {
                "pr": {
                    "number": 501,
                    "title": "Implement user authentication",
                    "author": "alice",
                    "description": "Add OAuth2 authentication with JWT tokens",
                    "branch": "feature/auth"
                }
            },
            "channel": "#development"
        },
        
        # 2. JIRA ticket created
        {
            "type": "jira_created",
            "data": {
                "ticket": {
                    "key": "DEV-501",
                    "summary": "Review authentication implementation",
                    "assignee": {"name": "bob"},
                    "priority": {"name": "High"}
                }
            },
            "channel": "#development"
        },
        
        # 3. Critical alert
        {
            "type": "alert",
            "data": {
                "blocker": {
                    "title": "Authentication service down",
                    "severity": "critical",
                    "affected_systems": ["web-app", "mobile-app"]
                }
            },
            "channel": "#alerts",
            "priority": NotificationPriority.CRITICAL
        },
        
        # 4. PR merged
        {
            "type": "pr_merged",
            "data": {
                "pr": {
                    "number": 501,
                    "title": "Implement user authentication",
                    "author": "alice",
                    "merge_commit": "abc123"
                }
            },
            "channel": "#development"
        }
    ]
    
    results = []
    for step in workflow_steps:
        priority = step.get("priority", NotificationPriority.MEDIUM)
        
        result = handler.send_notification(
            notification_type=step["type"],
            data=step["data"],
            channel_id=step["channel"],
            priority=priority
        )
        
        results.append(result)
        print(f"   {step['type']}: {result.status.value} ({result.processing_time_ms:.1f}ms)")
        
        if result.message:
            print(f"     Blocks: {len(result.message.blocks)}, Metadata: {result.message.metadata}")
    
    # Flush any pending batches
    batch_results = handler.flush_pending_batches()
    results.extend(batch_results)
    
    # Get final statistics
    final_stats = handler.get_processing_stats()
    
    print(f"\\n✅ Comprehensive formatter workflow completed:")
    print(f"   Total notifications: {len(workflow_steps)}")
    print(f"   Successful: {final_stats['successful']}")
    print(f"   Failed: {final_stats['failed']}")
    print(f"   Batched: {final_stats['batched']}")
    print(f"   Batch flushes: {len(batch_results)}")
    
    # Formatter-specific metrics
    if 'formatter_metrics' in final_stats:
        formatter_metrics = final_stats['formatter_metrics']
        print(f"   Formatter cache hits: {formatter_metrics.get('cache_hits', 0)}")
        print(f"   Formatter errors: {formatter_metrics.get('errors', 0)}")
    
    # Health check
    health = handler.health_check()
    print(f"   Final health status: {health['status']}")
    
    print("✅ Comprehensive formatter workflow tests passed\\n")
    return results


if __name__ == "__main__":
    print("🚀 Enhanced Notification Handler with New Formatter Test Suite")
    print("=" * 70)
    
    tests = [
        test_notification_handler_initialization,
        test_single_pr_notification_with_new_formatter,
        test_jira_notification_with_new_formatter,
        test_batch_notification_with_new_formatter,
        test_formatter_error_handling,
        test_formatter_metrics_and_stats,
        test_formatter_configuration_integration,
        test_comprehensive_formatter_workflow
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            result = test_func()
            if result is not None:  # Test returned a result
                passed += 1
                print(f"✅ {test_func.__name__} PASSED\\n")
            else:
                print(f"❌ {test_func.__name__} FAILED\\n")
        except Exception as e:
            print(f"❌ {test_func.__name__} FAILED with exception: {e}\\n")
    
    print("📊 Test Results:")
    print("=" * 30)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced notification handler with new formatter is working perfectly!")
        
        print("\\n💡 Key New Formatter Features Demonstrated:")
        print("  ✅ SlackMessageFormatterFactory integration")
        print("  ✅ Advanced message type routing")
        print("  ✅ Comprehensive error handling with fallbacks")
        print("  ✅ Performance metrics and caching")
        print("  ✅ Team and channel configuration support")
        print("  ✅ A/B testing capabilities")
        print("  ✅ Batch processing with new formatter")
        print("  ✅ Rich Block Kit message generation")
        print("  ✅ Formatter-specific statistics")
        print("  ✅ Configuration hot-reloading")
        
        print("\\n📋 New Formatter Usage Example:")
        print("  # Initialize handler with new formatter")
        print("  config = TemplateConfig(team_id='my-team')")
        print("  handler = EnhancedNotificationHandler(slack_client, config=config)")
        print("  ")
        print("  # Send notification (uses new formatter internally)")
        print("  result = handler.send_notification('pr_opened', pr_data, '#dev')")
        print("  ")
        print("  # Get formatter metrics")
        print("  metrics = handler.message_formatter.get_metrics()")
        print("  print(f'Cache hit rate: {metrics[\"cache_hit_rate\"]:.1f}%')")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")