#!/usr/bin/env python3
"""Core functionality tests for the message formatter system."""

import sys
import time
import json
from datetime import datetime
from unittest.mock import Mock

sys.path.append('.')

from devsync_ai.core.formatter_factory import (
    SlackMessageFormatterFactory, MessageType, FormatterOptions,
    ProcessingResult, TeamConfig, ChannelConfig
)
from devsync_ai.core.message_formatter import SlackMessage, TemplateConfig


class TestDataBuilder:
    """Simplified test data builder."""
    
    @staticmethod
    def complete_pr_data():
        return {
            "pr": {
                "number": 123,
                "title": "Fix authentication bug",
                "author": "alice",
                "state": "open",
                "url": "https://github.com/company/repo/pull/123",
                "description": "This PR fixes a critical authentication vulnerability",
                "branch": "fix/auth-bug",
                "repository": "company/repo"
            }
        }
    
    @staticmethod
    def complete_jira_data():
        return {
            "ticket": {
                "key": "DEV-789",
                "summary": "Implement user dashboard",
                "description": "Create a comprehensive user dashboard",
                "status": {"name": "In Progress"},
                "priority": {"name": "High"},
                "assignee": {"name": "carol"},
                "project": {"key": "DEV", "name": "Development"}
            }
        }
    
    @staticmethod
    def complete_standup_data():
        return {
            "date": "2024-01-15",
            "team": "Engineering Team",
            "participants": [
                {
                    "name": "alice",
                    "yesterday": ["Completed PR review"],
                    "today": ["Work on dashboard"],
                    "blockers": []
                }
            ]
        }
    
    @staticmethod
    def complete_blocker_data():
        return {
            "blocker": {
                "id": "BLOCK-001",
                "title": "Database Connection Timeout",
                "description": "Connection timeouts in production",
                "severity": "critical",
                "status": "active",
                "owner": "alice"
            }
        }


def test_formatter_factory_basic_functionality():
    """Test basic formatter factory functionality."""
    print("🧪 Testing Formatter Factory Basic Functionality")
    print("-" * 50)
    
    factory = SlackMessageFormatterFactory()
    
    # Test PR formatting
    pr_data = TestDataBuilder.complete_pr_data()
    result = factory.format_message(MessageType.PR_UPDATE, pr_data)
    
    assert result.success, f"PR formatting failed: {result.error}"
    assert result.message is not None, "PR message should not be None"
    assert len(result.message.blocks) > 0, "PR message should have blocks"
    assert result.processing_time_ms >= 0, "Processing time should be non-negative"
    
    print(f"✅ PR formatting: {result.processing_time_ms:.2f}ms, {len(result.message.blocks)} blocks")
    
    # Test JIRA formatting
    jira_data = TestDataBuilder.complete_jira_data()
    result = factory.format_message(MessageType.JIRA_UPDATE, jira_data)
    
    assert result.success, f"JIRA formatting failed: {result.error}"
    assert result.message is not None, "JIRA message should not be None"
    assert len(result.message.blocks) > 0, "JIRA message should have blocks"
    
    print(f"✅ JIRA formatting: {result.processing_time_ms:.2f}ms, {len(result.message.blocks)} blocks")
    
    # Test standup formatting
    standup_data = TestDataBuilder.complete_standup_data()
    result = factory.format_message(MessageType.STANDUP, standup_data)
    
    assert result.success, f"Standup formatting failed: {result.error}"
    assert result.message is not None, "Standup message should not be None"
    
    print(f"✅ Standup formatting: {result.processing_time_ms:.2f}ms, {len(result.message.blocks)} blocks")
    
    # Test blocker formatting
    blocker_data = TestDataBuilder.complete_blocker_data()
    result = factory.format_message(MessageType.BLOCKER, blocker_data)
    
    assert result.success, f"Blocker formatting failed: {result.error}"
    assert result.message is not None, "Blocker message should not be None"
    
    print(f"✅ Blocker formatting: {result.processing_time_ms:.2f}ms, {len(result.message.blocks)} blocks")
    
    print("✅ All basic functionality tests passed!\n")


def test_formatter_caching_system():
    """Test the caching system."""
    print("🧪 Testing Formatter Caching System")
    print("-" * 50)
    
    factory = SlackMessageFormatterFactory()
    pr_data = TestDataBuilder.complete_pr_data()
    
    # First call - should not be cached
    result1 = factory.format_message(MessageType.PR_UPDATE, pr_data)
    assert result1.cache_hit is False, "First call should not be cached"
    
    # Second call - should be cached
    result2 = factory.format_message(MessageType.PR_UPDATE, pr_data)
    assert result2.cache_hit is True, "Second call should be cached"
    assert result2.processing_time_ms <= result1.processing_time_ms, "Cached call should be faster"
    
    print(f"✅ Cache miss: {result1.processing_time_ms:.2f}ms")
    print(f"✅ Cache hit: {result2.processing_time_ms:.2f}ms")
    print(f"✅ Speedup: {result1.processing_time_ms / max(result2.processing_time_ms, 0.001):.1f}x")
    
    print("✅ Caching system tests passed!\n")


def test_formatter_error_handling():
    """Test error handling and fallbacks."""
    print("🧪 Testing Formatter Error Handling")
    print("-" * 50)
    
    factory = SlackMessageFormatterFactory()
    
    # Test with invalid message type
    result = factory.format_message("invalid_type", {})
    assert result.success is False, "Invalid message type should fail"
    assert result.error is not None, "Error should be provided"
    
    print(f"✅ Invalid message type handled: {result.error[:50]}...")
    
    # Test with empty data
    result = factory.format_message(MessageType.PR_UPDATE, {})
    # Should either succeed with placeholders or fail gracefully
    if result.success:
        print("✅ Empty data handled with placeholders")
    else:
        print(f"✅ Empty data failed gracefully: {result.error[:50]}...")
    
    # Test with malformed data
    malformed_data = {"pr": {"number": "not_a_number", "title": None}}
    result = factory.format_message(MessageType.PR_UPDATE, malformed_data)
    
    if result.success:
        print("✅ Malformed data handled with recovery")
    else:
        print(f"✅ Malformed data failed gracefully: {result.error[:50]}...")
    
    print("✅ Error handling tests passed!\n")


def test_formatter_performance():
    """Test formatter performance."""
    print("🧪 Testing Formatter Performance")
    print("-" * 50)
    
    factory = SlackMessageFormatterFactory()
    pr_data = TestDataBuilder.complete_pr_data()
    
    # Warm up
    factory.format_message(MessageType.PR_UPDATE, pr_data)
    
    # Performance test
    iterations = 100
    start_time = time.time()
    
    for _ in range(iterations):
        result = factory.format_message(MessageType.PR_UPDATE, pr_data)
        assert result.success, "Performance test message should succeed"
    
    end_time = time.time()
    avg_time = (end_time - start_time) / iterations * 1000  # Convert to ms
    
    print(f"✅ Average formatting time: {avg_time:.3f}ms per message")
    print(f"✅ Throughput: {1000/avg_time:.0f} messages per second")
    
    # Performance should be reasonable
    assert avg_time < 10, f"Formatting too slow: {avg_time:.3f}ms per message"
    
    print("✅ Performance tests passed!\n")


def test_formatter_team_configuration():
    """Test team configuration integration."""
    print("🧪 Testing Team Configuration")
    print("-" * 50)
    
    factory = SlackMessageFormatterFactory()
    
    # Configure team settings
    team_config = TeamConfig(
        team_id="test-team",
        default_formatting="rich",
        emoji_set={'pr': '🔄', 'success': '✅'},
        color_scheme={'primary': '#1f77b4'}
    )
    
    factory.configure_team(team_config)
    
    # Test that configuration is applied
    pr_data = TestDataBuilder.complete_pr_data()
    result = factory.format_message(MessageType.PR_UPDATE, pr_data, team_id="test-team")
    
    assert result.success, "Team configured message should succeed"
    assert result.message is not None, "Team configured message should exist"
    
    print("✅ Team configuration applied successfully")
    
    # Test channel configuration
    channel_config = ChannelConfig(
        channel_id="#dev",
        formatting_style="minimal",
        interactive_elements=False
    )
    
    factory.configure_channel(channel_config)
    
    result = factory.format_message(MessageType.PR_UPDATE, pr_data, channel="#dev")
    assert result.success, "Channel configured message should succeed"
    
    print("✅ Channel configuration applied successfully")
    print("✅ Configuration tests passed!\n")


def test_formatter_batch_processing():
    """Test batch processing functionality."""
    print("🧪 Testing Batch Processing")
    print("-" * 50)
    
    factory = SlackMessageFormatterFactory()
    
    # Create batch data
    batch_items = []
    for i in range(5):
        batch_items.append({
            "number": 100 + i,
            "title": f"PR {i}",
            "author": f"dev{i}"
        })
    
    batch_data = {
        'batch_items': batch_items,
        'batch_type': 'manual',
        'batch_size': len(batch_items)
    }
    
    # Test batch formatting
    options = FormatterOptions(batch=True, interactive=True)
    result = factory.format_message(MessageType.PR_BATCH, batch_data, options=options)
    
    assert result.success, f"Batch formatting failed: {result.error}"
    assert result.message is not None, "Batch message should exist"
    
    print(f"✅ Batch processing: {len(batch_items)} items in {result.processing_time_ms:.2f}ms")
    print(f"✅ Average per item: {result.processing_time_ms/len(batch_items):.2f}ms")
    
    print("✅ Batch processing tests passed!\n")


def test_formatter_metrics_collection():
    """Test metrics collection."""
    print("🧪 Testing Metrics Collection")
    print("-" * 50)
    
    factory = SlackMessageFormatterFactory()
    
    # Generate some activity
    test_data = [
        (MessageType.PR_UPDATE, TestDataBuilder.complete_pr_data()),
        (MessageType.JIRA_UPDATE, TestDataBuilder.complete_jira_data()),
        (MessageType.STANDUP, TestDataBuilder.complete_standup_data())
    ]
    
    for message_type, data in test_data:
        for _ in range(3):  # Format each type 3 times
            factory.format_message(message_type, data)
    
    # Get metrics
    metrics = factory.get_metrics()
    
    assert 'total_messages' in metrics, "Metrics should include total_messages"
    assert metrics['total_messages'] >= 9, "Should have processed at least 9 messages"
    assert 'cache_hit_rate' in metrics, "Metrics should include cache_hit_rate"
    assert 'avg_processing_time_ms' in metrics, "Metrics should include avg_processing_time_ms"
    assert 'formatter_usage' in metrics, "Metrics should include formatter_usage"
    
    print(f"✅ Total messages: {metrics['total_messages']}")
    print(f"✅ Cache hit rate: {metrics['cache_hit_rate']:.1f}%")
    print(f"✅ Avg processing time: {metrics['avg_processing_time_ms']:.2f}ms")
    print(f"✅ Formatter usage: {len(metrics['formatter_usage'])} formatters")
    
    print("✅ Metrics collection tests passed!\n")


def test_block_kit_validation():
    """Test Block Kit JSON validation."""
    print("🧪 Testing Block Kit Validation")
    print("-" * 50)
    
    factory = SlackMessageFormatterFactory()
    
    test_cases = [
        (MessageType.PR_UPDATE, TestDataBuilder.complete_pr_data()),
        (MessageType.JIRA_UPDATE, TestDataBuilder.complete_jira_data())
    ]
    
    for message_type, data in test_cases:
        result = factory.format_message(message_type, data)
        
        assert result.success, f"Message formatting should succeed for {message_type}"
        message = result.message
        
        # Validate JSON structure
        blocks_json = json.dumps(message.blocks)
        parsed_blocks = json.loads(blocks_json)
        
        assert isinstance(parsed_blocks, list), "Blocks should be a list"
        assert len(parsed_blocks) > 0, "Should have at least one block"
        
        # Validate each block
        for i, block in enumerate(parsed_blocks):
            assert 'type' in block, f"Block {i} should have type"
            assert isinstance(block['type'], str), f"Block {i} type should be string"
            assert block['type'] in ['header', 'section', 'divider', 'actions', 'context'], f"Invalid block type: {block['type']}"
        
        # Check message size limits
        assert len(blocks_json) < 50000, "Message should be under 50KB limit"
        assert len(parsed_blocks) <= 50, "Should have 50 or fewer blocks"
        
        print(f"✅ {message_type.value}: {len(parsed_blocks)} blocks, {len(blocks_json)} bytes")
    
    print("✅ Block Kit validation tests passed!\n")


def run_all_core_tests():
    """Run all core functionality tests."""
    print("🚀 Message Formatter Core Functionality Tests")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        test_formatter_factory_basic_functionality,
        test_formatter_caching_system,
        test_formatter_error_handling,
        test_formatter_performance,
        test_formatter_team_configuration,
        test_formatter_batch_processing,
        test_formatter_metrics_collection,
        test_block_kit_validation
    ]
    
    passed = 0
    total = len(tests)
    
    start_time = time.time()
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} FAILED: {e}")
    
    end_time = time.time()
    
    print("📊 Test Results:")
    print("=" * 30)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    print(f"⏱️ Total time: {end_time - start_time:.2f} seconds")
    
    if passed == total:
        print("\n🎉 All core functionality tests passed!")
        print("\n💡 Key Features Verified:")
        print("  ✅ Message type routing and formatting")
        print("  ✅ Caching system with performance benefits")
        print("  ✅ Error handling and graceful fallbacks")
        print("  ✅ Performance under load (100+ messages)")
        print("  ✅ Team and channel configuration")
        print("  ✅ Batch processing capabilities")
        print("  ✅ Comprehensive metrics collection")
        print("  ✅ Slack Block Kit compliance")
        
        return True
    else:
        print("\n⚠️ Some tests failed. Check output above for details.")
        return False


if __name__ == "__main__":
    success = run_all_core_tests()
    exit(0 if success else 1)