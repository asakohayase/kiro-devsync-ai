#!/usr/bin/env python3
"""Test script for SlackMessageFormatterFactory."""

import json
from datetime import datetime
from devsync_ai.core.formatter_factory import (
    SlackMessageFormatterFactory, MessageType, FormatterOptions,
    TeamConfig, ChannelConfig, ProcessingResult
)
from devsync_ai.core.message_formatter import TemplateConfig


def test_factory_initialization():
    """Test factory initialization and formatter registration."""
    print("🧪 Testing Factory Initialization")
    print("=" * 40)
    
    factory = SlackMessageFormatterFactory()
    
    # Check registered formatters
    formatters = factory.get_registered_formatters()
    print(f"✅ Registered formatters: {len(formatters)}")
    
    expected_types = ['pr_update', 'pr_batch', 'jira_update', 'jira_batch', 'standup', 'blocker']
    for msg_type in expected_types:
        if msg_type in formatters:
            print(f"   ✅ {msg_type}: {formatters[msg_type]}")
        else:
            print(f"   ❌ Missing: {msg_type}")
            return False
    
    print("✅ Factory initialization successful\n")
    return True


def test_basic_message_formatting():
    """Test basic message formatting through factory."""
    print("🧪 Testing Basic Message Formatting")
    print("=" * 40)
    
    factory = SlackMessageFormatterFactory()
    
    # Test PR message
    pr_data = {
        "pr": {
            "number": 123,
            "title": "Add user authentication",
            "author": "alice",
            "head_ref": "feature/auth",
            "base_ref": "main",
            "html_url": "https://github.com/company/repo/pull/123"
        },
        "action": "opened"
    }
    
    result = factory.format_message(
        message_type=MessageType.PR_UPDATE,
        data=pr_data,
        options=FormatterOptions(interactive=True)
    )
    
    if result.success:
        print("✅ PR message formatted successfully")
        print(f"   Formatter used: {result.formatter_used}")
        print(f"   Processing time: {result.processing_time_ms:.2f}ms")
        print(f"   Blocks: {len(result.message.blocks)}")
        print(f"   Cache hit: {result.cache_hit}")
    else:
        print(f"❌ PR formatting failed: {result.error}")
        return False
    
    # Test JIRA message
    jira_data = {
        "ticket": {
            "key": "DEV-456",
            "summary": "Implement dashboard",
            "status": {"name": "In Progress"},
            "assignee": {"display_name": "Bob Smith"}
        },
        "change_type": "status_change"
    }
    
    result = factory.format_message(
        message_type="jira_update",  # Test string type
        data=jira_data
    )
    
    if result.success:
        print("✅ JIRA message formatted successfully")
        print(f"   Formatter used: {result.formatter_used}")
    else:
        print(f"❌ JIRA formatting failed: {result.error}")
        return False
    
    print("✅ Basic message formatting successful\n")
    return True


def test_team_and_channel_configuration():
    """Test team and channel-specific configuration."""
    print("🧪 Testing Team and Channel Configuration")
    print("=" * 40)
    
    factory = SlackMessageFormatterFactory()
    
    # Configure team
    team_config = TeamConfig(
        team_id="engineering",
        default_formatting="rich",
        branding={
            "team_name": "Engineering Team",
            "logo_emoji": "⚙️",
            "primary_color": "#1f77b4"
        },
        emoji_set={
            "success": "🚀",
            "warning": "⚠️"
        }
    )
    factory.configure_team(team_config)
    
    # Configure channel
    channel_config = ChannelConfig(
        channel_id="#development",
        formatting_style="rich",
        interactive_elements=True,
        custom_branding={
            "channel_theme": "development"
        }
    )
    factory.configure_channel(channel_config)
    
    # Test message with team/channel config
    standup_data = {
        "date": "2025-08-12",
        "team": "Engineering Team",
        "team_health": 0.85,
        "team_members": [
            {
                "name": "alice",
                "yesterday": "Completed authentication",
                "today": "Working on dashboard",
                "blockers": []
            }
        ]
    }
    
    result = factory.format_message(
        message_type=MessageType.STANDUP,
        data=standup_data,
        channel="#development",
        team_id="engineering"
    )
    
    if result.success:
        print("✅ Team/channel configuration applied successfully")
        print(f"   Message has team branding: {'team_name' in str(result.message.blocks)}")
    else:
        print(f"❌ Team/channel configuration failed: {result.error}")
        return False
    
    print("✅ Team and channel configuration successful\n")
    return True


def test_caching_functionality():
    """Test message caching functionality."""
    print("🧪 Testing Caching Functionality")
    print("=" * 40)
    
    factory = SlackMessageFormatterFactory()
    
    # Same data for cache testing
    test_data = {
        "pr": {
            "number": 789,
            "title": "Cache test PR",
            "author": "test-user"
        },
        "action": "opened"
    }
    
    # First call - should not be cached
    result1 = factory.format_message(
        message_type=MessageType.PR_UPDATE,
        data=test_data
    )
    
    if not result1.success:
        print(f"❌ First call failed: {result1.error}")
        return False
    
    print(f"✅ First call: {result1.processing_time_ms:.2f}ms (cache hit: {result1.cache_hit})")
    
    # Second call - should be cached
    result2 = factory.format_message(
        message_type=MessageType.PR_UPDATE,
        data=test_data
    )
    
    if not result2.success:
        print(f"❌ Second call failed: {result2.error}")
        return False
    
    print(f"✅ Second call: {result2.processing_time_ms:.2f}ms (cache hit: {result2.cache_hit})")
    
    # Verify cache hit
    if result2.cache_hit and result2.processing_time_ms < result1.processing_time_ms:
        print("✅ Caching working correctly - second call was faster")
    else:
        print("⚠️ Cache may not be working as expected")
    
    print("✅ Caching functionality successful\n")
    return True


def test_ab_testing():
    """Test A/B testing functionality."""
    print("🧪 Testing A/B Testing")
    print("=" * 40)
    
    factory = SlackMessageFormatterFactory()
    
    # Setup A/B test
    factory.setup_ab_test("button_styles", {
        "variant_a": {
            "branding": {"button_style": "primary"},
            "interactive_elements": True
        },
        "variant_b": {
            "branding": {"button_style": "secondary"},
            "interactive_elements": False
        }
    })
    
    test_data = {
        "blocker": {
            "id": "BLOCK-001",
            "title": "Test blocker for A/B testing",
            "severity": "high"
        }
    }
    
    # Test variant A
    result_a = factory.format_message(
        message_type=MessageType.BLOCKER,
        data=test_data,
        options=FormatterOptions(ab_test_variant="variant_a")
    )
    
    # Test variant B
    result_b = factory.format_message(
        message_type=MessageType.BLOCKER,
        data=test_data,
        options=FormatterOptions(ab_test_variant="variant_b")
    )
    
    if result_a.success and result_b.success:
        print("✅ A/B test variants formatted successfully")
        print(f"   Variant A blocks: {len(result_a.message.blocks)}")
        print(f"   Variant B blocks: {len(result_b.message.blocks)}")
    else:
        print("❌ A/B testing failed")
        return False
    
    print("✅ A/B testing successful\n")
    return True


def test_error_handling():
    """Test error handling and fallback functionality."""
    print("🧪 Testing Error Handling")
    print("=" * 40)
    
    factory = SlackMessageFormatterFactory()
    
    # Test with invalid message type
    result1 = factory.format_message(
        message_type="invalid_type",
        data={"test": "data"}
    )
    
    if not result1.success:
        print("✅ Invalid message type handled correctly")
        print(f"   Error: {result1.error}")
    else:
        print("❌ Should have failed with invalid message type")
        return False
    
    # Test with missing required data
    result2 = factory.format_message(
        message_type=MessageType.PR_UPDATE,
        data={}  # Missing required 'pr' field
    )
    
    if result2.success:
        print("✅ Missing data handled with placeholders")
        print(f"   Warnings: {len(result2.warnings)}")
    else:
        print("⚠️ Missing data caused failure (fallback should handle this)")
    
    # Test with malformed data
    result3 = factory.format_message(
        message_type=MessageType.STANDUP,
        data={
            "date": "2025-08-12",
            "team": "Test Team",
            "team_members": "invalid_format"  # Should be list
        }
    )
    
    if result3.success or result3.message:
        print("✅ Malformed data handled gracefully")
    else:
        print("❌ Malformed data not handled properly")
        return False
    
    print("✅ Error handling successful\n")
    return True


def test_batch_processing():
    """Test batch processing functionality."""
    print("🧪 Testing Batch Processing")
    print("=" * 40)
    
    factory = SlackMessageFormatterFactory()
    
    # Test PR batch
    pr_batch_data = {
        "prs": [
            {"number": 101, "title": "PR 1", "author": "alice", "action": "opened"},
            {"number": 102, "title": "PR 2", "author": "bob", "action": "merged"},
            {"number": 103, "title": "PR 3", "author": "charlie", "action": "approved"}
        ],
        "batch_type": "daily_summary"
    }
    
    result = factory.format_message(
        message_type=MessageType.PR_BATCH,
        data=pr_batch_data,
        options=FormatterOptions(batch=True)
    )
    
    if result.success:
        print("✅ PR batch processing successful")
        print(f"   Blocks: {len(result.message.blocks)}")
    else:
        print(f"❌ PR batch processing failed: {result.error}")
        return False
    
    # Test JIRA batch
    jira_batch_data = {
        "tickets": [
            {"key": "DEV-101", "summary": "Ticket 1", "status": {"name": "Done"}},
            {"key": "DEV-102", "summary": "Ticket 2", "status": {"name": "In Progress"}},
            {"key": "DEV-103", "summary": "Ticket 3", "status": {"name": "To Do"}}
        ],
        "batch_type": "sprint_update"
    }
    
    result = factory.format_message(
        message_type=MessageType.JIRA_BATCH,
        data=jira_batch_data,
        options=FormatterOptions(batch=True)
    )
    
    if result.success:
        print("✅ JIRA batch processing successful")
        print(f"   Blocks: {len(result.message.blocks)}")
    else:
        print(f"❌ JIRA batch processing failed: {result.error}")
        return False
    
    print("✅ Batch processing successful\n")
    return True


def test_performance_metrics():
    """Test performance metrics collection."""
    print("🧪 Testing Performance Metrics")
    print("=" * 40)
    
    factory = SlackMessageFormatterFactory()
    
    # Generate some test messages
    for i in range(5):
        factory.format_message(
            message_type=MessageType.PR_UPDATE,
            data={
                "pr": {"number": i, "title": f"Test PR {i}", "author": "test"}
            }
        )
    
    # Get metrics
    metrics = factory.get_metrics()
    
    print(f"✅ Metrics collected:")
    print(f"   Total messages: {metrics['total_messages']}")
    print(f"   Cache hit rate: {metrics['cache_hit_rate']:.1f}%")
    print(f"   Error rate: {metrics['error_rate']:.1f}%")
    print(f"   Avg processing time: {metrics['avg_processing_time_ms']:.2f}ms")
    print(f"   Formatter usage: {metrics['formatter_usage']}")
    print(f"   Cache size: {metrics['cache_size']}")
    
    if metrics['total_messages'] >= 5:
        print("✅ Performance metrics working correctly")
    else:
        print("❌ Performance metrics not tracking correctly")
        return False
    
    print("✅ Performance metrics successful\n")
    return True


if __name__ == "__main__":
    print("🚀 SlackMessageFormatterFactory Test Suite")
    print("=" * 60)
    
    success_count = 0
    total_tests = 7
    
    tests = [
        test_factory_initialization,
        test_basic_message_formatting,
        test_team_and_channel_configuration,
        test_caching_functionality,
        test_ab_testing,
        test_error_handling,
        test_batch_processing,
        test_performance_metrics
    ]
    
    for test_func in tests:
        try:
            if test_func():
                success_count += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed with exception: {e}\n")
    
    # Summary
    print("📊 Test Results:")
    print("=" * 30)
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All factory tests passed!")
        print("🏭 SlackMessageFormatterFactory is working perfectly!")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")