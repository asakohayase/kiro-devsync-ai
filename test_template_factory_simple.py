#!/usr/bin/env python3
"""Simple test for template factory functionality."""

import sys
import time
sys.path.append('.')

from devsync_ai.core.template_factory import (
    MessageTemplateFactory, TemplateType, FactoryConfig
)
from devsync_ai.core.base_template import SlackMessageTemplate
from devsync_ai.core.message_formatter import TemplateConfig


class TestTemplate(SlackMessageTemplate):
    """Simple test template."""
    
    REQUIRED_FIELDS = ['title']
    
    def _create_message_blocks(self, data):
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Test message: {data.get('title', 'No title')}"
                }
            }
        ]


def test_basic_functionality():
    """Test basic template factory functionality."""
    print("🧪 Testing Template Factory Basic Functionality")
    print("=" * 50)
    
    # Create factory
    config = FactoryConfig(
        cache_ttl_seconds=60,
        max_cache_size=10,
        enable_metrics=True
    )
    factory = MessageTemplateFactory(config)
    print("✅ Factory created successfully")
    
    # Register template
    factory.register_template(
        name="test_template",
        template_class=TestTemplate,
        template_type=TemplateType.STANDUP,
        version="1.0.0",
        description="Test template for validation"
    )
    print("✅ Template registered successfully")
    
    # Create template by type
    template1 = factory.create_template(TemplateType.STANDUP)
    print("✅ Template created by type")
    
    # Create template by string
    template2 = factory.create_template("standup")
    print("✅ Template created by string")
    
    # Verify caching (should be same instance)
    assert template1 is template2, "Templates should be cached and identical"
    print("✅ Template caching working")
    
    # Test template usage
    test_data = {"title": "Test Message", "channel": "#test"}
    message = template1.format_message(test_data)
    print(f"✅ Message formatted: {len(message.blocks)} blocks")
    
    # Test metrics
    metrics = factory.get_template_metrics()
    print(f"✅ Metrics collected: {len(metrics)} template types")
    
    # Test cache stats
    cache_stats = factory.get_cache_stats()
    print(f"✅ Cache stats: {cache_stats['total_entries']} entries")
    
    # Test registered templates
    registered = factory.get_registered_templates()
    print(f"✅ Registered templates: {len(registered)} templates")
    
    return True


def test_performance():
    """Test template creation performance."""
    print("\n🧪 Testing Template Factory Performance")
    print("=" * 50)
    
    factory = MessageTemplateFactory()
    
    # Register template
    factory.register_template(
        name="perf_template",
        template_class=TestTemplate,
        template_type=TemplateType.PR_NEW
    )
    
    # Test creation performance
    start_time = time.time()
    
    # Create multiple templates (should use cache after first)
    templates = []
    for i in range(10):
        template = factory.create_template(TemplateType.PR_NEW)
        templates.append(template)
    
    end_time = time.time()
    creation_time = (end_time - start_time) * 1000  # Convert to ms
    
    print(f"✅ Created 10 templates in {creation_time:.2f}ms")
    
    # Verify all templates are the same instance (cached)
    all_same = all(t is templates[0] for t in templates[1:])
    assert all_same, "All templates should be the same cached instance"
    print("✅ All templates properly cached")
    
    # Test cache stats
    cache_stats = factory.get_cache_stats()
    print(f"✅ Cache utilization: {cache_stats['cache_utilization']:.2%}")
    
    return True


def test_error_handling():
    """Test error handling scenarios."""
    print("\n🧪 Testing Template Factory Error Handling")
    print("=" * 50)
    
    factory = MessageTemplateFactory()
    
    # Test unknown template type
    try:
        factory.create_template("unknown_template")
        assert False, "Should have raised error for unknown template"
    except Exception as e:
        print(f"✅ Properly handled unknown template: {type(e).__name__}")
    
    # Test unregistered template type
    try:
        factory.create_template(TemplateType.STANDUP)
        assert False, "Should have raised error for unregistered template"
    except Exception as e:
        print(f"✅ Properly handled unregistered template: {type(e).__name__}")
    
    # Test event type mapping
    try:
        factory.get_template_by_event_type("unknown.event", {})
        assert False, "Should have raised error for unknown event type"
    except Exception as e:
        print(f"✅ Properly handled unknown event type: {type(e).__name__}")
    
    return True


def test_cache_management():
    """Test cache management functionality."""
    print("\n🧪 Testing Template Factory Cache Management")
    print("=" * 50)
    
    # Create factory with small cache
    config = FactoryConfig(max_cache_size=2, cache_ttl_seconds=1)
    factory = MessageTemplateFactory(config)
    
    # Register multiple templates
    for i, template_type in enumerate([TemplateType.STANDUP, TemplateType.PR_NEW, TemplateType.JIRA_STATUS]):
        factory.register_template(
            name=f"template_{i}",
            template_class=TestTemplate,
            template_type=template_type
        )
    
    # Create templates (should trigger cache eviction)
    factory.create_template(TemplateType.STANDUP)
    factory.create_template(TemplateType.PR_NEW)
    factory.create_template(TemplateType.JIRA_STATUS)  # Should evict oldest
    
    cache_stats = factory.get_cache_stats()
    assert cache_stats['total_entries'] <= config.max_cache_size, "Cache should respect size limit"
    print(f"✅ Cache size limit respected: {cache_stats['total_entries']}/{config.max_cache_size}")
    
    # Test cache expiration
    time.sleep(1.1)  # Wait for expiration
    
    # Cleanup expired entries
    cleaned = factory.cleanup_expired_cache()
    print(f"✅ Cleaned up {cleaned} expired cache entries")
    
    # Test cache clearing
    factory.create_template(TemplateType.STANDUP)  # Add entry
    cleared = factory.clear_cache()
    print(f"✅ Cleared {cleared} cache entries")
    
    final_stats = factory.get_cache_stats()
    assert final_stats['total_entries'] == 0, "Cache should be empty after clearing"
    print("✅ Cache properly cleared")
    
    return True


if __name__ == "__main__":
    print("🚀 Template Factory Test Suite")
    print("=" * 60)
    
    tests = [
        test_basic_functionality,
        test_performance,
        test_error_handling,
        test_cache_management
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
        print("🎉 All tests passed! Template factory is working correctly!")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")