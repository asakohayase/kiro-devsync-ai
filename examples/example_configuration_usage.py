#!/usr/bin/env python3
"""Example usage of flexible configuration system."""

import sys
import os
from datetime import datetime
sys.path.append('.')

from devsync_ai.core.config_manager import (
    FlexibleConfigurationManager, TeamSettings, VisualStyling, 
    MessageContentPreferences, InteractiveElementSettings,
    ChannelSpecificFormatting, UserPersonalPreferences, MessageTemplateConfig,
    EmojiStyle, MessageDensity, FormattingStyle, default_config_manager
)


def example_basic_configuration_usage():
    """Example: Basic configuration loading and usage."""
    print("📋 Basic Configuration Usage Example")
    print("=" * 50)
    
    # Load configuration (will use defaults if no config file exists)
    config_manager = FlexibleConfigurationManager(
        config_dir="config",
        environment="production"
    )
    
    config = config_manager.load_configuration()
    
    print(f"✅ Configuration loaded:")
    print(f"   Team: {config.team_settings.team_name} ({config.team_settings.team_id})")
    print(f"   Version: {config.version}")
    print(f"   Environment: {config.environment}")
    print(f"   Brand color: {config.team_settings.visual_styling.brand_color}")
    print(f"   Emoji style: {config.team_settings.visual_styling.emoji_style.value}")
    print(f"   Interactive mode: {config.team_settings.interactive_settings.interactive_mode}")
    
    return config


def example_team_customization():
    """Example: Team-specific customization."""
    print("\n🎨 Team Customization Example")
    print("=" * 50)
    
    config_manager = FlexibleConfigurationManager(
        config_dir="config",
        environment="development"
    )
    
    # Create custom team settings
    visual_styling = VisualStyling(
        brand_color="#4caf50",           # Green theme
        secondary_color="#8bc34a",
        success_color="#2e7d32",
        warning_color="#ff9800",
        error_color="#f44336",
        emoji_style=EmojiStyle.CUSTOM,
        custom_emojis={
            "success": ":heavy_check_mark:",
            "warning": ":warning:",
            "error": ":x:",
            "pr_new": ":new:",
            "pr_merged": ":white_check_mark:",
            "bug": ":bug:",
            "feature": ":sparkles:"
        },
        message_density=MessageDensity.DETAILED,
        show_avatars=True,
        compact_mode=False
    )
    
    content_preferences = MessageContentPreferences(
        show_technical_details=True,
        show_file_changes=True,
        show_ci_status=True,
        max_description_length=400,
        highlight_breaking_changes=True,
        show_deployment_status=True
    )
    
    interactive_settings = InteractiveElementSettings(
        interactive_mode=True,
        show_action_buttons=True,
        enable_quick_actions=True,
        confirmation_level="detailed"
    )
    
    team_settings = TeamSettings(
        team_id="frontend-team",
        team_name="Frontend Engineering Team",
        visual_styling=visual_styling,
        content_preferences=content_preferences,
        interactive_settings=interactive_settings,
        default_formatting=FormattingStyle.RICH,
        timezone="America/Los_Angeles"
    )
    
    # Update team settings
    success = config_manager.update_team_settings(team_settings)
    
    print(f"✅ Team customization applied: {success}")
    print(f"   Team: {team_settings.team_name}")
    print(f"   Theme: Green with custom emojis")
    print(f"   Max description: {team_settings.content_preferences.max_description_length}")
    print(f"   Interactive: {team_settings.interactive_settings.interactive_mode}")
    
    return team_settings


def example_channel_specific_configuration():
    """Example: Channel-specific configuration."""
    print("\n📺 Channel-Specific Configuration Example")
    print("=" * 50)
    
    config_manager = FlexibleConfigurationManager(
        config_dir="config",
        environment="production"
    )
    
    # Configure different channels for different purposes
    channels = {
        "#development": ChannelSpecificFormatting(
            channel_id="#development",
            formatting_style=FormattingStyle.RICH,
            show_technical_details=True,
            batch_threshold=3,
            interactive_elements=True,
            custom_branding={
                "icon": ":gear:",
                "color": "#2196f3",
                "theme": "technical"
            },
            notification_preferences={
                "priority": "high",
                "frequency": "all",
                "include_code_snippets": True
            }
        ),
        
        "#management": ChannelSpecificFormatting(
            channel_id="#management",
            formatting_style=FormattingStyle.SIMPLE,
            high_level_summary=True,
            hide_technical_details=True,
            batch_threshold=10,
            interactive_elements=False,
            custom_branding={
                "icon": ":chart_with_upwards_trend:",
                "color": "#4caf50",
                "theme": "executive"
            },
            notification_preferences={
                "priority": "medium",
                "frequency": "summary",
                "focus_on_metrics": True
            }
        ),
        
        "#alerts": ChannelSpecificFormatting(
            channel_id="#alerts",
            formatting_style=FormattingStyle.PLAIN,
            message_density=MessageDensity.MINIMAL,
            batch_threshold=1,
            interactive_elements=True,
            notification_preferences={
                "priority": "critical",
                "frequency": "immediate",
                "escalation_enabled": True
            }
        )
    }
    
    # Apply channel configurations
    for channel_id, channel_config in channels.items():
        success = config_manager.update_channel_override(channel_id, channel_config)
        print(f"✅ {channel_id} configured: {success}")
        print(f"   Style: {channel_config.formatting_style.value}")
        print(f"   Batch threshold: {channel_config.batch_threshold}")
        print(f"   Interactive: {channel_config.interactive_elements}")
        if channel_config.show_technical_details is not None:
            print(f"   Technical details: {channel_config.show_technical_details}")
    
    return channels


def example_user_personalization():
    """Example: User personal preferences."""
    print("\n👤 User Personalization Example")
    print("=" * 50)
    
    config_manager = FlexibleConfigurationManager(
        config_dir="config",
        environment="production"
    )
    
    # Create personalized settings for different users
    users = {
        "alice": UserPersonalPreferences(
            user_id="alice",
            timezone="America/Los_Angeles",
            date_format="%Y-%m-%d",
            time_format="%I:%M %p",  # 12-hour format
            notification_frequency="verbose",
            preferred_density=MessageDensity.DETAILED,
            show_personal_mentions=True,
            highlight_assigned_items=True,
            custom_keywords=["security", "performance", "critical", "urgent"],
            priority_channels=["#alerts", "#security", "#incidents"],
            mute_channels=[]
        ),
        
        "bob": UserPersonalPreferences(
            user_id="bob",
            timezone="Europe/London",
            date_format="%d/%m/%Y",
            time_format="%H:%M",  # 24-hour format
            notification_frequency="minimal",
            preferred_density=MessageDensity.COMPACT,
            show_personal_mentions=False,
            highlight_assigned_items=True,
            custom_keywords=["deployment", "release", "production"],
            priority_channels=["#releases", "#deployments"],
            mute_channels=["#random", "#general", "#social"]
        ),
        
        "carol": UserPersonalPreferences(
            user_id="carol",
            timezone="Asia/Tokyo",
            date_format="%Y年%m月%d日",
            time_format="%H:%M",
            notification_frequency="normal",
            preferred_density=MessageDensity.DETAILED,
            show_personal_mentions=True,
            highlight_assigned_items=True,
            custom_keywords=["frontend", "ui", "ux", "design"],
            priority_channels=["#frontend", "#design", "#user-experience"],
            mute_channels=["#backend"]
        )
    }
    
    # Apply user preferences
    for user_id, preferences in users.items():
        success = config_manager.update_user_preferences(user_id, preferences)
        print(f"✅ {user_id} preferences set: {success}")
        print(f"   Timezone: {preferences.timezone}")
        print(f"   Frequency: {preferences.notification_frequency}")
        print(f"   Density: {preferences.preferred_density.value}")
        print(f"   Keywords: {len(preferences.custom_keywords)}")
        print(f"   Priority channels: {len(preferences.priority_channels)}")
    
    return users


def example_template_customization():
    """Example: Message template customization."""
    print("\n📝 Template Customization Example")
    print("=" * 50)
    
    config_manager = FlexibleConfigurationManager(
        config_dir="config",
        environment="production"
    )
    
    # Customize templates for different message types
    templates = {
        "pr_update": MessageTemplateConfig(
            template_type="pr_update",
            enabled=True,
            show_file_changes=True,
            show_ci_status=True,
            show_review_status=True,
            max_description_length=350,
            include_author_info=True,
            show_labels=True,
            show_milestone=True,
            custom_fields={
                "show_diff_stats": True,
                "highlight_conflicts": True,
                "show_deployment_status": True,
                "include_test_coverage": True,
                "show_performance_impact": True
            }
        ),
        
        "jira_update": MessageTemplateConfig(
            template_type="jira_update",
            enabled=True,
            show_file_changes=False,
            show_ci_status=False,
            max_description_length=250,
            include_author_info=True,
            show_labels=True,
            show_milestone=True,
            custom_fields={
                "show_story_points": True,
                "show_epic_link": True,
                "show_sprint_info": True,
                "highlight_blockers": True,
                "show_acceptance_criteria": True
            }
        ),
        
        "alert": MessageTemplateConfig(
            template_type="alert",
            enabled=True,
            max_description_length=600,
            include_author_info=False,
            custom_fields={
                "show_severity": True,
                "show_affected_systems": True,
                "enable_escalation": True,
                "show_runbook_links": True,
                "include_metrics": True,
                "show_similar_incidents": True
            }
        )
    }
    
    # Apply template configurations
    for template_type, template_config in templates.items():
        success = config_manager.update_template_config(template_type, template_config)
        print(f"✅ {template_type} template configured: {success}")
        print(f"   Enabled: {template_config.enabled}")
        print(f"   Max description: {template_config.max_description_length}")
        print(f"   Custom fields: {len(template_config.custom_fields)}")
    
    return templates


def example_effective_configuration():
    """Example: Getting effective configuration with all overrides."""
    print("\n🎯 Effective Configuration Example")
    print("=" * 50)
    
    config_manager = FlexibleConfigurationManager(
        config_dir="config",
        environment="production"
    )
    
    # Test different scenarios
    scenarios = [
        {
            "name": "Development Channel + Alice",
            "channel_id": "#development",
            "user_id": "alice",
            "template_type": "pr_update"
        },
        {
            "name": "Management Channel + Bob",
            "channel_id": "#management", 
            "user_id": "bob",
            "template_type": "jira_update"
        },
        {
            "name": "Alerts Channel + Carol",
            "channel_id": "#alerts",
            "user_id": "carol",
            "template_type": "alert"
        },
        {
            "name": "Default (no overrides)",
            "channel_id": None,
            "user_id": None,
            "template_type": None
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📋 Scenario: {scenario['name']}")
        
        effective_config = config_manager.get_effective_config(
            channel_id=scenario["channel_id"],
            user_id=scenario["user_id"],
            template_type=scenario["template_type"]
        )
        
        print(f"   Configuration keys: {len(effective_config)}")
        print(f"   Has channel override: {'channel_override' in effective_config}")
        print(f"   Has user preferences: {'user_preferences' in effective_config}")
        print(f"   Has template config: {'template_config' in effective_config}")
        
        # Show some specific values
        if "visual_styling" in effective_config:
            styling = effective_config["visual_styling"]
            print(f"   Brand color: {styling.get('brand_color', 'default')}")
            print(f"   Message density: {styling.get('message_density', 'default')}")
        
        if "batch_threshold" in effective_config:
            print(f"   Batch threshold: {effective_config['batch_threshold']}")
    
    return scenarios


def example_environment_configuration():
    """Example: Environment-specific configuration."""
    print("\n🌍 Environment Configuration Example")
    print("=" * 50)
    
    # Set some environment variables for demonstration
    os.environ["DEVSYNC_TEAM_SETTINGS_TEAM_NAME"] = "Environment Override Team"
    os.environ["DEVSYNC_TEAM_SETTINGS_VISUAL_STYLING_BRAND_COLOR"] = "#e91e63"
    os.environ["DEVSYNC_INTERACTIVE_MODE"] = "false"
    
    try:
        config_manager = FlexibleConfigurationManager(
            config_dir="config",
            environment="development"
        )
        
        config = config_manager.load_configuration()
        
        print(f"✅ Environment overrides applied:")
        print(f"   Team name: {config.team_settings.team_name}")
        print(f"   Brand color: {config.team_settings.visual_styling.brand_color}")
        print(f"   Interactive mode: {config.team_settings.interactive_settings.interactive_mode}")
        
        print(f"\n📝 Environment variables used:")
        for key, value in os.environ.items():
            if key.startswith("DEVSYNC_"):
                print(f"   {key} = {value}")
        
    finally:
        # Clean up environment variables
        for key in list(os.environ.keys()):
            if key.startswith("DEVSYNC_"):
                del os.environ[key]
    
    return config


def example_configuration_change_listeners():
    """Example: Configuration change listeners."""
    print("\n🔔 Configuration Change Listeners Example")
    print("=" * 50)
    
    config_manager = FlexibleConfigurationManager(
        config_dir="config",
        environment="test"
    )
    
    # Track configuration changes
    change_log = []
    
    def log_config_changes(config):
        change_log.append({
            "timestamp": datetime.now(),
            "team_name": config.team_settings.team_name,
            "brand_color": config.team_settings.visual_styling.brand_color
        })
        print(f"   📝 Configuration changed: {config.team_settings.team_name}")
    
    # Add change listener
    config_manager.add_change_listener(log_config_changes)
    
    # Make some configuration changes
    changes = [
        ("Marketing Team", "#ff9800"),
        ("Sales Team", "#9c27b0"),
        ("Support Team", "#607d8b")
    ]
    
    for team_name, brand_color in changes:
        team_settings = TeamSettings(
            team_id=team_name.lower().replace(" ", "-"),
            team_name=team_name,
            visual_styling=VisualStyling(brand_color=brand_color)
        )
        
        config_manager.update_team_settings(team_settings)
    
    print(f"\n✅ Change tracking results:")
    print(f"   Total changes logged: {len(change_log)}")
    for i, change in enumerate(change_log, 1):
        print(f"   Change {i}: {change['team_name']} ({change['brand_color']})")
    
    # Remove listener
    config_manager.remove_change_listener(log_config_changes)
    print(f"   Change listener removed")
    
    return change_log


if __name__ == "__main__":
    print("🚀 Flexible Configuration System Usage Examples")
    print("=" * 60)
    
    # Run examples
    basic_config = example_basic_configuration_usage()
    team_settings = example_team_customization()
    channels = example_channel_specific_configuration()
    users = example_user_personalization()
    templates = example_template_customization()
    scenarios = example_effective_configuration()
    env_config = example_environment_configuration()
    change_log = example_configuration_change_listeners()
    
    print(f"\n🎉 Examples Complete!")
    
    print(f"\n💡 Key Configuration Features Demonstrated:")
    print(f"  ✅ Team-wide visual styling and branding")
    print(f"  ✅ Channel-specific formatting overrides")
    print(f"  ✅ User personal preferences and customization")
    print(f"  ✅ Message template configuration")
    print(f"  ✅ Environment variable overrides")
    print(f"  ✅ Effective configuration with inheritance")
    print(f"  ✅ Runtime configuration updates")
    print(f"  ✅ Change notification system")
    print(f"  ✅ YAML and JSON file format support")
    print(f"  ✅ Schema validation and migration")
    
    print(f"\n📊 Configuration Summary:")
    print(f"  🎨 Team customizations: {len([team_settings]) if team_settings else 0}")
    print(f"  📺 Channel overrides: {len(channels)}")
    print(f"  👤 User preferences: {len(users)}")
    print(f"  📝 Template configs: {len(templates)}")
    print(f"  🎯 Test scenarios: {len(scenarios)}")
    print(f"  🔔 Configuration changes: {len(change_log)}")
    
    print(f"\n📋 Example Configuration Usage:")
    print(f"  # Load configuration")
    print(f"  config = config_manager.load_configuration()")
    print(f"  ")
    print(f"  # Get effective config for specific context")
    print(f"  effective = config_manager.get_effective_config(")
    print(f"      channel_id='#development',")
    print(f"      user_id='alice',")
    print(f"      template_type='pr_update'")
    print(f"  )")
    print(f"  ")
    print(f"  # Use configuration in message formatting")
    print(f"  brand_color = effective['visual_styling']['brand_color']")
    print(f"  max_length = effective['template_config']['max_description_length']")
    print(f"  interactive = effective['interactive_settings']['interactive_mode']")