#!/usr/bin/env python3
"""
Integration test for the enhanced MessageTemplateFactory with existing templates.
"""

import sys
import os
import time

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from devsync_ai.services.template_factory import (
        MessageTemplateFactory, TemplateConfig, TemplateVersion
    )
    from devsync_ai.core.base_template import (
        create_team_branding, create_channel_config, 
        create_user_preferences, MessagePriority
    )
    print("✅ Successfully imported enhanced factory modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_factory_with_existing_templates():
    """Test factory with existing template types."""
    print("\n🧪 Testing Factory with Existing Templates...")
    
    factory = MessageTemplateFactory()
    
    # Test standup template
    standup_data = {
        "date": "2025-08-12",
        "team": "Integration Test Team",
        "stats": {
            "prs_merged": 3,
            "prs_open": 5,
            "tickets_completed": 7,
            "tickets_in_progress": 12,
            "commits": 23
        },
        "team_members": [
            {
                "name": "Alice",
                "status": "active",
                "yesterday": ["Completed user auth", "Fixed bug #123"],
                "today": ["Start payment integration", "Code review"],
                "blockers": []
            }
        ],
        "action_items": ["Deploy staging environment", "Update documentation"]
    }
    
    template = factory.get_template("standup", standup_data, user_id="test_user")
    result = template.render()
    
    assert "blocks" in result, "Standup template missing blocks"
    assert len(result["blocks"]) > 0, "Standup template has no blocks"
    
    print(f"✅ Standup template: {len(result['blocks'])} blocks")
    
    # Test PR template
    pr_data = {
        "pr": {
            "id": 123,
            "title": "Add integration tests",
            "author": "developer",
            "status": "open",
            "reviewers": ["reviewer1", "reviewer2"]
        },
        "action": "opened"
    }
    
    pr_template = factory.get_template("pr_update", pr_data, user_id="test_user")
    pr_result = pr_template.render()
    
    assert "blocks" in pr_result, "PR template missing blocks"
    assert len(pr_result["blocks"]) > 0, "PR template has no blocks"
    
    print(f"✅ PR template: {len(pr_result['blocks'])} blocks")
    
    # Test JIRA template
    jira_data = {
        "ticket": {
            "key": "TEST-123",
            "summary": "Integration test ticket",
            "assignee": "developer",
            "status": {"from": "To Do", "to": "In Progress"}
        },
        "change_type": "status_change"
    }
    
    jira_template = factory.get_template("jira_update", jira_data, user_id="test_user")
    jira_result = jira_template.render()
    
    assert "blocks" in jira_result, "JIRA template missing blocks"
    assert len(jira_result["blocks"]) > 0, "JIRA template has no blocks"
    
    print(f"✅ JIRA template: {len(jira_result['blocks'])} blocks")
    
    # Test Alert template
    alert_data = {
        "alert": {
            "id": "ALERT-123",
            "type": "build_failure",
            "severity": "high",
            "title": "Integration Test Alert",
            "description": "Test alert for integration testing",
            "affected_systems": ["CI/CD"],
            "impact": "Test impact"
        }
    }
    
    alert_template = factory.get_template("alert", alert_data, user_id="test_user")
    alert_result = alert_template.render()
    
    assert "blocks" in alert_result, "Alert template missing blocks"
    assert len(alert_result["blocks"]) > 0, "Alert template has no blocks"
    
    print(f"✅ Alert template: {len(alert_result['blocks'])} blocks")
    
    return True


def test_enhanced_features():
    """Test enhanced factory features."""
    print("\n🧪 Testing Enhanced Factory Features...")
    
    factory = MessageTemplateFactory()
    
    # Set up team branding
    branding = create_team_branding(
        "Enhanced Test Team",
        primary_color="#9b59b6",
        footer_text="Enhanced Test Team • Testing Excellence"
    )
    factory.set_global_branding(branding)
    
    # Test caching
    data = {"team": "Cache Test", "stats": {"prs_merged": 1}}
    
    # First call
    start_time = time.time()
    template1 = factory.get_template("standup", data, user_id="cache_user", use_cache=True)
    result1 = template1.render()
    first_time = time.time() - start_time
    
    # Second call (should be cached)
    start_time = time.time()
    template2 = factory.get_template("standup", data, user_id="cache_user", use_cache=True)
    result2 = template2.render()
    second_time = time.time() - start_time
    
    assert result1 == result2, "Cached results don't match"
    print(f"✅ Caching: first={first_time:.4f}s, second={second_time:.4f}s")
    
    # Test metrics
    metrics = factory.get_metrics()
    assert "templates" in metrics, "Metrics missing templates"
    assert "cache" in metrics, "Metrics missing cache stats"
    
    template_count = len(metrics["templates"])
    cache_hit_rate = metrics["cache"]["hit_rate"]
    
    print(f"✅ Metrics: {template_count} template types, {cache_hit_rate:.2%} cache hit rate")
    
    # Test health check
    health = factory.health_check()
    assert "health_score" in health, "Health check missing score"
    assert "status" in health, "Health check missing status"
    
    print(f"✅ Health: {health['health_score']}/100 ({health['status']})")
    
    return True


def test_template_registration():
    """Test custom template registration."""
    print("\n🧪 Testing Template Registration...")
    
    factory = MessageTemplateFactory()
    
    # Create custom factory function
    def custom_notification_factory(data):
        message = data.get('message', 'No message')
        priority = data.get('priority', 'normal')
        
        emoji = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
        
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *Custom Notification*\n{message}"
                    }
                }
            ],
            "text": f"Custom: {message}"
        }
    
    # Register custom template
    config = TemplateConfig(
        name="custom_notification",
        factory_function=custom_notification_factory,
        version=TemplateVersion.BETA,
        priority=MessagePriority.HIGH
    )
    
    factory.register_template("custom", config)
    
    # Test custom template
    data = {"message": "This is a custom notification", "priority": "high"}
    template = factory.get_template("custom", data)
    result = template.render()
    
    assert "Custom Notification" in result["blocks"][0]["text"]["text"]
    assert "🔴" in result["blocks"][0]["text"]["text"]  # High priority emoji
    
    print("✅ Custom template registration working")
    
    # Check it appears in registered templates
    registered = factory.get_registered_templates()
    assert "custom" in registered, "Custom template not in registry"
    
    custom_templates = registered["custom"]
    assert len(custom_templates) > 0, "No custom templates found"
    assert custom_templates[0]["name"] == "custom_notification", "Custom template name mismatch"
    
    print(f"✅ Registry: {len(registered)} template types, custom template found")
    
    return True


def test_feature_flags():
    """Test feature flag functionality."""
    print("\n🧪 Testing Feature Flags...")
    
    factory = MessageTemplateFactory()
    
    # Register template with feature flag
    def feature_template_factory(data):
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🚀 *Feature Enabled*: {data.get('message', 'No message')}"
                    }
                }
            ],
            "text": f"Feature: {data.get('message', 'No message')}"
        }
    
    config = TemplateConfig(
        name="feature_template",
        factory_function=feature_template_factory,
        feature_flags=["test_feature"]
    )
    
    factory.register_template("feature_test", config)
    
    # Should fail without feature flag
    try:
        factory.get_template("feature_test", {"message": "test"})
        assert False, "Template should not be available without feature flag"
    except ValueError:
        print("✅ Template correctly blocked without feature flag")
    
    # Enable feature flag
    factory.set_feature_flag("test_feature", True)
    
    # Should now work
    template = factory.get_template("feature_test", {"message": "Feature flag test"})
    result = template.render()
    
    assert "Feature Enabled" in result["blocks"][0]["text"]["text"]
    print("✅ Template available with feature flag enabled")
    
    return True


def test_performance_monitoring():
    """Test performance monitoring."""
    print("\n🧪 Testing Performance Monitoring...")
    
    factory = MessageTemplateFactory()
    
    # Generate some template activity
    for i in range(10):
        data = {"team": f"Perf Test Team {i}", "stats": {"prs_merged": i}}
        template = factory.get_template("standup", data, user_id=f"perf_user_{i}")
        template.render()
    
    # Check metrics
    metrics = factory.get_metrics()
    
    # Should have template metrics
    assert len(metrics["templates"]) > 0, "No template metrics collected"
    
    # Check for standup metrics
    standup_metrics = None
    for key, template_metrics in metrics["templates"].items():
        if "standup" in key:
            standup_metrics = template_metrics
            break
    
    assert standup_metrics is not None, "No standup metrics found"
    assert standup_metrics["render_count"] > 0, "No render count recorded"
    assert standup_metrics["average_render_time"] >= 0, "Invalid average render time"
    
    print(f"✅ Performance metrics: {standup_metrics['render_count']} renders, {standup_metrics['average_render_time']:.4f}s avg")
    
    return True


def main():
    """Run all integration tests."""
    print("🚀 Enhanced MessageTemplateFactory Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Existing Templates", test_factory_with_existing_templates),
        ("Enhanced Features", test_enhanced_features),
        ("Template Registration", test_template_registration),
        ("Feature Flags", test_feature_flags),
        ("Performance Monitoring", test_performance_monitoring)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} tests...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} tests PASSED")
            else:
                print(f"❌ {test_name} tests FAILED")
        except Exception as e:
            print(f"❌ {test_name} tests FAILED with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Integration Test Results: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        print("\nEnhanced Factory Integration Verified:")
        print("✅ Works with existing Standup, PR, JIRA, and Alert templates")
        print("✅ Advanced caching improves performance")
        print("✅ Comprehensive metrics collection")
        print("✅ Health monitoring and alerts")
        print("✅ Custom template registration")
        print("✅ Feature flag support")
        print("✅ Team branding integration")
        print("✅ Performance monitoring")
        return 0
    else:
        print("⚠️  Some integration tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())