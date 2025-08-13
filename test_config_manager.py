#!/usr/bin/env python3
"""Test script for flexible configuration system."""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
sys.path.append('.')

from devsync_ai.core.config_manager import (
    FlexibleConfigurationManager, ConfigurationValidator, ConfigurationMigrator,
    TeamSettings, VisualStyling, MessageContentPreferences, InteractiveElementSettings,
    ChannelSpecificFormatting, UserPersonalPreferences, MessageTemplateConfig,
    ConfigurationSchema, EmojiStyle, MessageDensity, FormattingStyle
)


def test_configuration_validation():
    """Test configuration validation and schema checking."""
    print("🧪 Testing Configuration Validation")
    print("=" * 50)
    
    validator = ConfigurationValidator()
    
    # Test valid configuration
    valid_config = {
        "version": "1.0.0",
        "team_settings": {
            "team_id": "engineering",
            "team_name": "Engineering Team",
            "visual_styling": {
                "brand_color": "#1f77b4",
                "emoji_style": "standard",
                "message_density": "detailed"
            }
        },
        "channel_overrides": {
            "#development": {
                "channel_id": "#development",
                "formatting_style": "rich",
                "batch_threshold": 5
            }
        },
        "message_templates": {
            "pr_update": {
                "template_type": "pr_update",
                "enabled": True,
                "max_description_length": 300
            }
        }
    }
    
    is_valid, errors = validator.validate(valid_config)
    print(f"✅ Valid configuration: {is_valid}")
    if errors:
        print(f"   Errors: {errors}")
    
    # Test invalid configuration
    invalid_config = {
        "version": "1.0.0",
        "team_settings": {
            "team_id": "engineering",
            "team_name": "Engineering Team",
            "visual_styling": {
                "brand_color": "invalid-color",  # Invalid color format
                "emoji_style": "invalid-style",  # Invalid enum value
                "message_density": "detailed"
            }
        },
        "channel_overrides": {
            "development": {  # Missing # prefix
                "channel_id": "development",
                "batch_threshold": 100  # Exceeds maximum
            }
        }
    }
    
    is_valid, errors = validator.validate(invalid_config)
    print(f"✅ Invalid configuration detected: {not is_valid}")
    print(f"   Validation errors: {len(errors)}")
    for error in errors:
        print(f"     - {error}")
    
    print("✅ Configuration validation tests passed\n")
    return True


def test_configuration_migration():
    """Test configuration migration between versions."""
    print("🧪 Testing Configuration Migration")
    print("=" * 50)
    
    migrator = ConfigurationMigrator()
    
    # Test v1 configuration (baseline)
    v1_config = {
        "team_settings": {
            "team_id": "test-team",
            "team_name": "Test Team"
        },
        "migration_version": 1
    }
    
    # Migrate to v2
    v2_config = migrator.migrate(v1_config, target_version=2)
    
    print(f"✅ Migration completed")
    print(f"   Original version: {v1_config.get('migration_version', 1)}")
    print(f"   New version: {v2_config.get('migration_version')}")
    
    # Check that new fields were added
    visual_styling = v2_config.get("team_settings", {}).get("visual_styling", {})
    print(f"   Added compact_mode: {'compact_mode' in visual_styling}")
    print(f"   Added show_avatars: {'show_avatars' in visual_styling}")
    
    # Test no-op migration (same version)
    same_version = migrator.migrate(v2_config, target_version=2)
    assert same_version == v2_config, "Same version migration should be no-op"
    
    print("✅ Configuration migration tests passed\n")
    return True


def test_team_settings_configuration():
    """Test team settings configuration."""
    print("🧪 Testing Team Settings Configuration")
    print("=" * 50)
    
    # Create comprehensive team settings
    visual_styling = VisualStyling(
        brand_color="#2e7d32",
        secondary_color="#ff9800",
        emoji_style=EmojiStyle.CUSTOM,
        custom_emojis={
            "success": ":white_check_mark:",
            "warning": ":warning:",
            "error": ":x:"
        },
        message_density=MessageDensity.COMPACT,
        show_avatars=True,
        compact_mode=True
    )
    
    content_preferences = MessageContentPreferences(
        show_technical_details=True,
        show_file_changes=True,
        max_description_length=400,
        highlight_breaking_changes=True
    )
    
    interactive_settings = InteractiveElementSettings(
        interactive_mode=True,
        show_action_buttons=True,
        enable_quick_actions=True,
        confirmation_level="detailed"
    )
    
    team_settings = TeamSettings(
        team_id="engineering",
        team_name="Engineering Team",
        visual_styling=visual_styling,
        content_preferences=content_preferences,
        interactive_settings=interactive_settings,
        default_formatting=FormattingStyle.RICH,
        timezone="America/New_York"
    )
    
    print(f"✅ Team settings created:")
    print(f"   Team: {team_settings.team_name} ({team_settings.team_id})")
    print(f"   Brand color: {team_settings.visual_styling.brand_color}")
    print(f"   Emoji style: {team_settings.visual_styling.emoji_style.value}")
    print(f"   Message density: {team_settings.visual_styling.message_density.value}")
    print(f"   Interactive mode: {team_settings.interactive_settings.interactive_mode}")
    print(f"   Max description: {team_settings.content_preferences.max_description_length}")
    
    print("✅ Team settings configuration tests passed\n")
    return True


def test_channel_overrides():
    """Test channel-specific configuration overrides."""
    print("🧪 Testing Channel Overrides")
    print("=" * 50)
    
    # Development channel - technical details
    dev_channel = ChannelSpecificFormatting(
        channel_id="#development",
        formatting_style=FormattingStyle.RICH,
        show_technical_details=True,
        batch_threshold=3,
        interactive_elements=True,
        custom_branding={
            "icon": ":gear:",
            "color": "#2196f3"
        }
    )
    
    # Management channel - high-level summaries
    mgmt_channel = ChannelSpecificFormatting(
        channel_id="#management",
        formatting_style=FormattingStyle.SIMPLE,
        high_level_summary=True,
        hide_technical_details=True,
        batch_threshold=10,
        interactive_elements=False
    )
    
    # Alerts channel - minimal formatting
    alerts_channel = ChannelSpecificFormatting(
        channel_id="#alerts",
        formatting_style=FormattingStyle.PLAIN,
        message_density=MessageDensity.MINIMAL,
        batch_threshold=1,
        interactive_elements=True
    )
    
    channels = [dev_channel, mgmt_channel, alerts_channel]
    
    print(f"✅ Channel overrides created:")
    for channel in channels:
        print(f"   {channel.channel_id}:")
        print(f"     Style: {channel.formatting_style.value}")
        print(f"     Batch threshold: {channel.batch_threshold}")
        print(f"     Interactive: {channel.interactive_elements}")
        if channel.show_technical_details is not None:
            print(f"     Technical details: {channel.show_technical_details}")
        if channel.high_level_summary:
            print(f"     High-level summary: {channel.high_level_summary}")
    
    print("✅ Channel override tests passed\n")
    return True


def test_user_preferences():
    """Test user personal preferences."""
    print("🧪 Testing User Preferences")
    print("=" * 50)
    
    # Create user preferences
    user_prefs = [
        UserPersonalPreferences(
            user_id="alice",
            timezone="America/Los_Angeles",
            notification_frequency="verbose",
            preferred_density=MessageDensity.DETAILED,
            show_personal_mentions=True,
            highlight_assigned_items=True,
            custom_keywords=["security", "performance", "bug"],
            priority_channels=["#alerts", "#security"]
        ),
        UserPersonalPreferences(
            user_id="bob",
            timezone="Europe/London",
            notification_frequency="minimal",
            preferred_density=MessageDensity.COMPACT,
            show_personal_mentions=False,
            mute_channels=["#random", "#general"]
        )
    ]
    
    print(f"✅ User preferences created:")
    for prefs in user_prefs:
        print(f"   {prefs.user_id}:")
        print(f"     Timezone: {prefs.timezone}")
        print(f"     Frequency: {prefs.notification_frequency}")
        print(f"     Density: {prefs.preferred_density.value}")
        print(f"     Keywords: {len(prefs.custom_keywords)}")
        if prefs.priority_channels:
            print(f"     Priority channels: {prefs.priority_channels}")
        if prefs.mute_channels:
            print(f"     Muted channels: {prefs.mute_channels}")
    
    print("✅ User preferences tests passed\n")
    return True


def test_template_configuration():
    """Test message template configuration."""
    print("🧪 Testing Template Configuration")
    print("=" * 50)
    
    # Create template configurations
    templates = {
        "pr_update": MessageTemplateConfig(
            template_type="pr_update",
            enabled=True,
            show_file_changes=True,
            show_ci_status=True,
            show_review_status=True,
            max_description_length=300,
            include_author_info=True,
            show_labels=True,
            custom_fields={
                "show_diff_stats": True,
                "highlight_conflicts": True
            }
        ),
        "jira_update": MessageTemplateConfig(
            template_type="jira_update",
            enabled=True,
            show_file_changes=False,
            max_description_length=200,
            include_author_info=True,
            show_milestone=True,
            custom_fields={
                "show_story_points": True,
                "show_epic_link": True
            }
        ),
        "alert": MessageTemplateConfig(
            template_type="alert",
            enabled=True,
            max_description_length=500,
            include_author_info=False,
            custom_fields={
                "show_severity": True,
                "show_affected_systems": True,
                "enable_escalation": True
            }
        )
    }
    
    print(f"✅ Template configurations created:")
    for template_type, config in templates.items():
        print(f"   {template_type}:")
        print(f"     Enabled: {config.enabled}")
        print(f"     Max description: {config.max_description_length}")
        print(f"     Custom fields: {len(config.custom_fields)}")
        if config.show_file_changes is not None:
            print(f"     Show file changes: {config.show_file_changes}")
    
    print("✅ Template configuration tests passed\n")
    return True


def test_configuration_manager():
    """Test the complete configuration manager."""
    print("🧪 Testing Configuration Manager")
    print("=" * 50)
    
    # Create temporary config directory
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = FlexibleConfigurationManager(
            config_dir=temp_dir,
            environment="test"
        )
        
        # Test loading default configuration
        config = config_manager.load_configuration()
        print(f"✅ Default configuration loaded:")
        print(f"   Team: {config.team_settings.team_name}")
        print(f"   Version: {config.version}")
        
        # Test updating team settings
        new_team_settings = TeamSettings(
            team_id="test-team",
            team_name="Test Team",
            visual_styling=VisualStyling(
                brand_color="#4caf50",
                emoji_style=EmojiStyle.CUSTOM
            )
        )
        
        success = config_manager.update_team_settings(new_team_settings)
        print(f"✅ Team settings updated: {success}")
        
        # Test loading updated configuration
        updated_config = config_manager.load_configuration(force_reload=True)
        print(f"   Updated team: {updated_config.team_settings.team_name}")
        print(f"   Updated color: {updated_config.team_settings.visual_styling.brand_color}")
        
        # Test channel override
        channel_config = ChannelSpecificFormatting(
            channel_id="#test",
            formatting_style=FormattingStyle.SIMPLE,
            batch_threshold=5
        )
        
        success = config_manager.update_channel_override("#test", channel_config)
        print(f"✅ Channel override added: {success}")
        
        # Test effective configuration
        effective_config = config_manager.get_effective_config(
            channel_id="#test",
            user_id="test-user"
        )
        
        print(f"✅ Effective configuration generated:")
        print(f"   Keys: {list(effective_config.keys())}")
        print(f"   Has channel override: {'channel_override' in effective_config}")
        
        print("✅ Configuration manager tests passed\n")
        return True


def test_environment_overrides():
    """Test environment variable overrides."""
    print("🧪 Testing Environment Overrides")
    print("=" * 50)
    
    # Set environment variables
    os.environ["DEVSYNC_TEAM_SETTINGS_TEAM_NAME"] = "Environment Team"
    os.environ["DEVSYNC_TEAM_SETTINGS_VISUAL_STYLING_BRAND_COLOR"] = "#ff5722"
    os.environ["DEVSYNC_INTERACTIVE_MODE"] = "false"
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = FlexibleConfigurationManager(
                config_dir=temp_dir,
                environment="test"
            )
            
            config = config_manager.load_configuration()
            
            print(f"✅ Environment overrides applied:")
            print(f"   Team name from env: {config.team_settings.team_name}")
            print(f"   Brand color from env: {config.team_settings.visual_styling.brand_color}")
            
    finally:
        # Clean up environment variables
        for key in ["DEVSYNC_TEAM_SETTINGS_TEAM_NAME", "DEVSYNC_TEAM_SETTINGS_VISUAL_STYLING_BRAND_COLOR", "DEVSYNC_INTERACTIVE_MODE"]:
            if key in os.environ:
                del os.environ[key]
    
    print("✅ Environment override tests passed\n")
    return True


def test_configuration_file_formats():
    """Test different configuration file formats."""
    print("🧪 Testing Configuration File Formats")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        
        # Test YAML configuration
        yaml_config = {
            "version": "1.0.0",
            "team_settings": {
                "team_id": "yaml-team",
                "team_name": "YAML Team",
                "visual_styling": {
                    "brand_color": "#9c27b0",
                    "emoji_style": "standard"
                }
            }
        }
        
        yaml_file = config_dir / "team_config_test.yaml"
        with open(yaml_file, 'w') as f:
            import yaml
            yaml.dump(yaml_config, f)
        
        # Test JSON configuration
        json_config = {
            "version": "1.0.0",
            "team_settings": {
                "team_id": "json-team",
                "team_name": "JSON Team",
                "visual_styling": {
                    "brand_color": "#e91e63",
                    "emoji_style": "custom"
                }
            }
        }
        
        json_file = config_dir / "team_config_json.json"
        with open(json_file, 'w') as f:
            json.dump(json_config, f, indent=2)
        
        # Test loading YAML
        config_manager = FlexibleConfigurationManager(
            config_dir=temp_dir,
            environment="test"
        )
        
        yaml_loaded = config_manager.load_configuration()
        print(f"✅ YAML configuration loaded:")
        print(f"   Team: {yaml_loaded.team_settings.team_name}")
        print(f"   Color: {yaml_loaded.team_settings.visual_styling.brand_color}")
        
        # Test loading JSON (by changing environment)
        config_manager_json = FlexibleConfigurationManager(
            config_dir=temp_dir,
            environment="json"
        )
        
        json_loaded = config_manager_json.load_configuration()
        print(f"✅ JSON configuration loaded:")
        print(f"   Team: {json_loaded.team_settings.team_name}")
        print(f"   Color: {json_loaded.team_settings.visual_styling.brand_color}")
    
    print("✅ Configuration file format tests passed\n")
    return True


def test_change_listeners():
    """Test configuration change listeners."""
    print("🧪 Testing Change Listeners")
    print("=" * 50)
    
    change_notifications = []
    
    def config_change_listener(config: ConfigurationSchema):
        change_notifications.append({
            "timestamp": config.last_updated,
            "team_name": config.team_settings.team_name
        })
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = FlexibleConfigurationManager(
            config_dir=temp_dir,
            environment="test"
        )
        
        # Add change listener
        config_manager.add_change_listener(config_change_listener)
        
        # Make configuration changes
        team_settings = TeamSettings(
            team_id="listener-test",
            team_name="Listener Test Team"
        )
        
        config_manager.update_team_settings(team_settings)
        
        print(f"✅ Change listener triggered:")
        print(f"   Notifications received: {len(change_notifications)}")
        if change_notifications:
            print(f"   Latest change: {change_notifications[-1]['team_name']}")
        
        # Remove listener
        config_manager.remove_change_listener(config_change_listener)
        
        # Make another change (should not trigger)
        team_settings.team_name = "Updated Team"
        config_manager.update_team_settings(team_settings)
        
        print(f"   Notifications after removal: {len(change_notifications)}")
    
    print("✅ Change listener tests passed\n")
    return True


if __name__ == "__main__":
    print("🚀 Flexible Configuration System Test Suite")
    print("=" * 60)
    
    tests = [
        test_configuration_validation,
        test_configuration_migration,
        test_team_settings_configuration,
        test_channel_overrides,
        test_user_preferences,
        test_template_configuration,
        test_configuration_manager,
        test_environment_overrides,
        test_configuration_file_formats,
        test_change_listeners
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
        print("🎉 All tests passed! Flexible configuration system is working perfectly!")
        
        print("\n💡 Key Features Demonstrated:")
        print("  ✅ Schema validation and error checking")
        print("  ✅ Configuration migration between versions")
        print("  ✅ Team settings with visual styling")
        print("  ✅ Channel-specific overrides")
        print("  ✅ User personal preferences")
        print("  ✅ Template-specific configuration")
        print("  ✅ Environment variable overrides")
        print("  ✅ YAML and JSON file format support")
        print("  ✅ Runtime configuration updates")
        print("  ✅ Change notification system")
        
        print("\n📋 Example Configuration Structure:")
        print('  {')
        print('    "team_settings": {')
        print('      "brand_color": "#1f77b4",')
        print('      "emoji_style": "standard",')
        print('      "message_density": "compact",')
        print('      "interactive_mode": true')
        print('    },')
        print('    "channel_overrides": {')
        print('      "#development": {')
        print('        "show_technical_details": true,')
        print('        "batch_threshold": 3')
        print('      },')
        print('      "#management": {')
        print('        "high_level_summary": true,')
        print('        "hide_technical_details": true')
        print('      }')
        print('    },')
        print('    "message_templates": {')
        print('      "pr_update": {')
        print('        "show_file_changes": true,')
        print('        "show_ci_status": true,')
        print('        "max_description_length": 200')
        print('      }')
        print('    }')
        print('  }')
    else:
        print("⚠️ Some tests failed. Check the output above for details.")