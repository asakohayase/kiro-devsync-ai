"""
Examples demonstrating the enhanced MessageTemplateFactory.
Shows advanced features like caching, A/B testing, performance monitoring, and more.
"""

import json
import time
from datetime import datetime
from devsync_ai.services.template_factory import (
    MessageTemplateFactory, TemplateConfig, TemplateVersion
)
from devsync_ai.core.base_template import (
    SlackMessageTemplate, MessageMetadata, TeamBranding,
    ChannelConfig, UserPreferences, AccessibilityOptions,
    MessagePriority, EmojiConstants,
    create_team_branding, create_channel_config,
    create_user_preferences, create_accessibility_options
)


class CustomNotificationTemplate(SlackMessageTemplate):
    """Custom notification template using the base template system."""
    
    def _validate_data(self) -> None:
        """Validate notification data."""
        if not self.data.get('message'):
            raise ValueError("Message is required")
    
    def _build_message_content(self) -> None:
        """Build notification content."""
        message = self.data.get('message')
        priority = self.data.get('priority', 'normal')
        details = self.data.get('details')
        
        # Add priority indicator
        if priority == 'high':
            emoji = EmojiConstants.WARNING
        elif priority == 'urgent':
            emoji = EmojiConstants.ERROR
        else:
            emoji = EmojiConstants.INFO
        
        self.add_section_block(f"{emoji} {message}")
        
        if details:
            self.add_section_block(f"*Details:* {details}")
        
        # Add action buttons
        buttons = [
            self.create_button("Acknowledge", "ack_notification", 
                             style="primary", emoji="✅"),
            self.create_button("View Details", "view_details", 
                             emoji="👀")
        ]
        self.add_actions_block(buttons)
    
    def _get_header_text(self) -> str:
        """Get header text."""
        return "System Notification"
    
    def _get_header_emoji(self) -> str:
        """Get header emoji."""
        priority = self.data.get('priority', 'normal')
        if priority == 'urgent':
            return EmojiConstants.ERROR
        elif priority == 'high':
            return EmojiConstants.WARNING
        return EmojiConstants.INFO


def example_basic_factory_usage():
    """Example basic factory usage."""
    print("=== Basic Factory Usage Example ===")
    
    # Create factory
    factory = MessageTemplateFactory()
    
    # Create a simple standup message
    standup_data = {
        "date": "2025-08-12",
        "team": "Engineering Team",
        "stats": {
            "prs_merged": 5,
            "prs_open": 8,
            "tickets_completed": 12,
            "tickets_in_progress": 15,
            "commits": 47
        },
        "team_members": [
            {
                "name": "Alice",
                "status": "active",
                "yesterday": ["Completed OAuth integration"],
                "today": ["Start dashboard redesign"],
                "blockers": []
            }
        ],
        "action_items": ["Deploy to staging", "Update documentation"]
    }
    
    # Get template and render
    template = factory.get_template("standup", standup_data)
    message = template.render()
    
    print(f"Generated standup message with {len(message['blocks'])} blocks")
    print(f"Fallback text: {template.get_fallback_text()}")
    
    return message


def example_enhanced_context():
    """Example using enhanced context features."""
    print("\n=== Enhanced Context Example ===")
    
    factory = MessageTemplateFactory()
    
    # Create team branding
    team_branding = create_team_branding(
        "DevOps Team",
        primary_color="#ff6b35",
        footer_text="DevOps Team • Keeping systems running 24/7",
        custom_emojis={"success": ":white_check_mark:"},
        date_format="%B %d, %Y at %I:%M %p"
    )
    
    # Create channel configuration
    channel_config = create_channel_config(
        "C1234567890",
        "devops-alerts",
        compact_mode=False,
        threading_enabled=True,
        max_blocks=25
    )
    
    # Create user preferences
    user_preferences = create_user_preferences(
        "U0987654321",
        timezone="America/New_York",
        date_format="%m/%d/%Y %I:%M %p",
        notification_level="detailed"
    )
    
    # Create accessibility options
    accessibility = create_accessibility_options(
        screen_reader_optimized=True,
        high_contrast=False,
        alt_text_required=True
    )
    
    # Set global branding
    factory.set_global_branding(team_branding)
    factory.set_global_accessibility(accessibility)
    
    # Create alert with enhanced context
    alert_data = {
        "alert": {
            "id": "ALERT-001",
            "type": "deployment_issue",
            "severity": "high",
            "title": "Production Deployment Failed",
            "description": "Deployment to production failed during database migration",
            "affected_systems": ["Production", "Database"],
            "impact": "Service degraded for 25% of users",
            "assigned_to": "devops-team"
        }
    }
    
    template = factory.get_template(
        "alert",
        alert_data,
        user_id="U0987654321",
        channel_config=channel_config,
        user_preferences=user_preferences
    )
    
    message = template.render()
    analytics = template.get_analytics_data()
    
    print(f"Generated alert with enhanced context: {len(message['blocks'])} blocks")
    print(f"Template: {analytics.get('template_name')}")
    print(f"User: {analytics.get('user_id')}")
    print(f"Has errors: {template.has_errors()}")
    
    return message


def example_custom_template_registration():
    """Example registering custom templates."""
    print("\n=== Custom Template Registration Example ===")
    
    factory = MessageTemplateFactory()
    
    # Register custom template with enhanced configuration
    config = TemplateConfig(
        name="custom_notification_v2",
        template_class=CustomNotificationTemplate,
        version=TemplateVersion.BETA,
        enabled=True,
        weight=100,
        priority=MessagePriority.HIGH,
        cache_ttl=1800,  # 30 minutes
        performance_threshold=0.5,  # 500ms
        team_branding=create_team_branding(
            "Notifications Team",
            primary_color="#9b59b6",
            footer_text="Notifications Team"
        )
    )
    
    factory.register_template("custom_notification", config)
    
    # Use the custom template
    notification_data = {
        "message": "System maintenance scheduled",
        "priority": "high",
        "details": "Maintenance window: 2:00 AM - 4:00 AM EST"
    }
    
    template = factory.get_template("custom_notification", notification_data)
    message = template.render()
    
    print(f"Custom template generated: {len(message['blocks'])} blocks")
    
    # Check registered templates
    registered = factory.get_registered_templates()
    custom_templates = registered.get("custom_notification", [])
    print(f"Registered custom templates: {len(custom_templates)}")
    
    return message


def example_ab_testing():
    """Example A/B testing different template versions."""
    print("\n=== A/B Testing Example ===")
    
    factory = MessageTemplateFactory()
    
    # Register two variants of a notification template
    def create_variant_a(data):
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📢 *Variant A*: {data.get('message', 'No message')}"
                    }
                }
            ],
            "text": f"Variant A: {data.get('message', 'No message')}"
        }
    
    def create_variant_b(data):
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚀 Enhanced Notification",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Variant B*: {data.get('message', 'No message')}"
                    }
                }
            ],
            "text": f"Variant B: {data.get('message', 'No message')}"
        }
    
    # Register variants with different weights
    config_a = TemplateConfig(
        name="notification_variant_a",
        factory_function=create_variant_a,
        weight=30  # 30% of users
    )
    
    config_b = TemplateConfig(
        name="notification_variant_b", 
        factory_function=create_variant_b,
        weight=70  # 70% of users
    )
    
    factory.register_template("ab_notification", config_a)
    factory.register_template("ab_notification", config_b)
    
    # Test with different users
    data = {"message": "Welcome to our new feature!"}
    
    user_variants = {}
    for i in range(10):
        user_id = f"user_{i}"
        template = factory.get_template("ab_notification", data, user_id=user_id, use_cache=False)
        result = template.render()
        
        # Determine which variant the user got
        if "Variant A" in result["text"]:
            user_variants[user_id] = "A"
        else:
            user_variants[user_id] = "B"
    
    variant_a_count = sum(1 for v in user_variants.values() if v == "A")
    variant_b_count = sum(1 for v in user_variants.values() if v == "B")
    
    print(f"A/B Test Results: Variant A: {variant_a_count}, Variant B: {variant_b_count}")
    
    # Test consistency - same user should get same variant
    user_1_first = factory.get_template("ab_notification", data, user_id="user_1", use_cache=False)
    user_1_second = factory.get_template("ab_notification", data, user_id="user_1", use_cache=False)
    
    assert user_1_first.render()["text"] == user_1_second.render()["text"], "A/B testing not consistent!"
    print("✅ A/B testing is consistent for same user")
    
    return user_variants


def example_caching_performance():
    """Example demonstrating caching and performance monitoring."""
    print("\n=== Caching and Performance Example ===")
    
    # Create factory with custom cache configuration
    cache_config = {"max_size": 100, "default_ttl": 600}  # 10 minutes
    factory = MessageTemplateFactory(cache_config=cache_config)
    
    # Create some test data
    pr_data = {
        "pr": {
            "id": 123,
            "title": "Add caching support",
            "author": "developer",
            "status": "open",
            "reviewers": ["reviewer1", "reviewer2"]
        },
        "action": "opened"
    }
    
    # First call - cache miss
    start_time = time.time()
    template1 = factory.get_template("pr_update", pr_data, user_id="cache_test_user")
    result1 = template1.render()
    first_call_time = time.time() - start_time
    
    # Second call - cache hit
    start_time = time.time()
    template2 = factory.get_template("pr_update", pr_data, user_id="cache_test_user")
    result2 = template2.render()
    second_call_time = time.time() - start_time
    
    print(f"First call (cache miss): {first_call_time:.4f}s")
    print(f"Second call (cache hit): {second_call_time:.4f}s")
    print(f"Performance improvement: {((first_call_time - second_call_time) / first_call_time * 100):.1f}%")
    
    # Get cache statistics
    metrics = factory.get_metrics()
    cache_stats = metrics["cache"]
    
    print(f"Cache hit rate: {cache_stats['hit_rate']:.2%}")
    print(f"Cache size: {cache_stats['size']}/{cache_stats['max_size']}")
    
    return cache_stats


def example_feature_flags():
    """Example using feature flags."""
    print("\n=== Feature Flags Example ===")
    
    factory = MessageTemplateFactory()
    
    # Register template that requires feature flag
    def enhanced_standup_factory(data):
        # Enhanced version with additional metrics
        base_result = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚀 Enhanced Daily Standup",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Team:* {data.get('team', 'Unknown')}\n*Enhanced Features:* ✅ Enabled"
                    }
                }
            ],
            "text": f"Enhanced Standup - {data.get('team', 'Unknown')}"
        }
        
        # Add performance metrics if available
        if data.get('performance_metrics'):
            metrics = data['performance_metrics']
            base_result["blocks"].append({
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Deployment Success Rate:* {metrics.get('deploy_success_rate', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Average Build Time:* {metrics.get('avg_build_time', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Code Coverage:* {metrics.get('code_coverage', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Bug Fix Rate:* {metrics.get('bug_fix_rate', 'N/A')}"}
                ]
            })
        
        return base_result
    
    config = TemplateConfig(
        name="enhanced_standup",
        factory_function=enhanced_standup_factory,
        feature_flags=["enhanced_standups", "performance_metrics"]
    )
    
    factory.register_template("standup", config)
    
    # Test without feature flags
    standup_data = {
        "team": "Feature Flag Test Team",
        "performance_metrics": {
            "deploy_success_rate": "95%",
            "avg_build_time": "8.5 min",
            "code_coverage": "87%",
            "bug_fix_rate": "2.3 days"
        }
    }
    
    try:
        template = factory.get_template("standup", standup_data)
        print("❌ Template should not be available without feature flags")
    except ValueError as e:
        print(f"✅ Template correctly unavailable: {e}")
    
    # Enable feature flags
    factory.set_feature_flag("enhanced_standups", True)
    factory.set_feature_flag("performance_metrics", True)
    
    # Now it should work
    template = factory.get_template("standup", standup_data)
    result = template.render()
    
    print(f"✅ Enhanced template available with feature flags: {len(result['blocks'])} blocks")
    
    return result


def example_monitoring_and_health():
    """Example monitoring and health check."""
    print("\n=== Monitoring and Health Check Example ===")
    
    factory = MessageTemplateFactory()
    
    # Generate some activity to create metrics
    test_data = [
        ("standup", {"team": "Team A", "stats": {"prs_merged": 3}}),
        ("pr_update", {"pr": {"id": 1, "title": "Test PR", "author": "dev1"}, "action": "opened"}),
        ("jira_update", {"ticket": {"key": "TEST-1", "summary": "Test ticket"}, "change_type": "status_change"}),
        ("alert", {"alert": {"id": "ALERT-1", "type": "build_failure", "severity": "high", "title": "Build failed"}})
    ]
    
    # Create templates to generate metrics
    for i in range(20):
        template_type, data = test_data[i % len(test_data)]
        user_id = f"monitoring_user_{i % 5}"
        
        try:
            template = factory.get_template(template_type, data, user_id=user_id)
            template.render()
        except Exception as e:
            print(f"Error with {template_type}: {e}")
    
    # Get comprehensive metrics
    metrics = factory.get_metrics()
    
    print("📊 Template Metrics:")
    for template_key, template_metrics in metrics["templates"].items():
        print(f"  {template_key}:")
        print(f"    Renders: {template_metrics['render_count']}")
        print(f"    Avg Time: {template_metrics['average_render_time']:.4f}s")
        print(f"    Error Rate: {template_metrics['error_rate']:.2%}")
        print(f"    Cache Hit Rate: {template_metrics['cache_hit_rate']:.2%}")
    
    print(f"\n📈 Cache Statistics:")
    cache_stats = metrics["cache"]
    print(f"  Hit Rate: {cache_stats['hit_rate']:.2%}")
    print(f"  Size: {cache_stats['size']}/{cache_stats['max_size']}")
    print(f"  Hits: {cache_stats['hits']}, Misses: {cache_stats['misses']}")
    
    # Perform health check
    health = factory.health_check()
    print(f"\n🏥 Health Check:")
    print(f"  Score: {health['health_score']}/100")
    print(f"  Status: {health['status']}")
    print(f"  Total Renders: {health['total_renders']}")
    
    if health['issues']:
        print(f"  Issues: {', '.join(health['issues'])}")
    else:
        print("  No issues detected")
    
    return health


def example_configuration_management():
    """Example configuration management."""
    print("\n=== Configuration Management Example ===")
    
    # Create factory with environment-specific settings
    factory = MessageTemplateFactory()
    
    # Set environment and feature flags
    factory.set_environment("staging")
    factory.set_feature_flag("beta_features", True)
    factory.set_feature_flag("experimental_ui", False)
    factory.set_feature_flag("enhanced_analytics", True)
    
    # Register environment-specific template
    staging_config = TemplateConfig(
        name="staging_notification",
        factory_function=lambda data: {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🧪 *STAGING*: {data.get('message', 'No message')}"
                    }
                }
            ],
            "text": f"STAGING: {data.get('message', 'No message')}"
        },
        environment="staging",
        feature_flags=["beta_features"]
    )
    
    production_config = TemplateConfig(
        name="production_notification",
        factory_function=lambda data: {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🚀 *PRODUCTION*: {data.get('message', 'No message')}"
                    }
                }
            ],
            "text": f"PRODUCTION: {data.get('message', 'No message')}"
        },
        environment="production"
    )
    
    factory.register_template("env_notification", staging_config)
    factory.register_template("env_notification", production_config)
    
    # Test environment-specific template selection
    data = {"message": "Environment-specific notification"}
    template = factory.get_template("env_notification", data)
    result = template.render()
    
    print(f"Environment: {factory._environment}")
    print(f"Template result: {result['text']}")
    print(f"Feature flags: {factory._feature_flags}")
    
    # Show registered templates with their configurations
    registered = factory.get_registered_templates()
    env_templates = registered.get("env_notification", [])
    
    print(f"\nRegistered environment templates:")
    for template_config in env_templates:
        print(f"  {template_config['name']}: env={template_config['environment']}, flags={template_config['feature_flags']}")
    
    return result


if __name__ == "__main__":
    print("DevSync AI Enhanced MessageTemplateFactory Examples")
    print("=" * 60)
    
    # Run all examples
    example_basic_factory_usage()
    example_enhanced_context()
    example_custom_template_registration()
    example_ab_testing()
    example_caching_performance()
    example_feature_flags()
    example_monitoring_and_health()
    example_configuration_management()
    
    print("\n" + "=" * 60)
    print("All enhanced factory examples completed successfully!")
    print("\nEnhanced Factory Features Demonstrated:")
    print("✅ Basic template creation and rendering")
    print("✅ Enhanced context with branding and accessibility")
    print("✅ Custom template registration")
    print("✅ A/B testing with consistent user assignment")
    print("✅ Advanced caching with performance improvements")
    print("✅ Feature flag-based template selection")
    print("✅ Comprehensive monitoring and health checks")
    print("✅ Environment-specific configuration management")