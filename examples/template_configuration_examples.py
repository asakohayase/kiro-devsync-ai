"""Examples demonstrating the template configuration and customization system."""

import logging
from pathlib import Path

from devsync_ai.core.template_config_manager import (
    TemplateConfigurationManager,
    TemplateType,
    TemplateCustomization,
    BrandingConfig,
    EmojiSetConfig
)
from devsync_ai.core.template_config_loader import (
    ConfigurationLoader,
    create_example_team_config
)
from devsync_ai.core.template_customizer import (
    TemplateCustomizer,
    ColorScheme,
    AccessibilityMode,
    apply_color_scheme_to_template,
    create_high_contrast_customization
)
from devsync_ai.core.template_fallback_handler import (
    TemplateFallbackHandler,
    FallbackLevel,
    create_fallback_handler
)
from devsync_ai.core.template_config_validator import (
    validate_template_configuration,
    validate_branding_configuration
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_configuration():
    """Example: Basic configuration management."""
    print("\n=== Basic Configuration Management ===")
    
    # Create configuration manager
    manager = TemplateConfigurationManager()
    
    # Load template configuration
    standup_config = manager.load_template_config(TemplateType.STANDUP)
    print(f"Loaded standup config: enabled={standup_config.enabled}")
    print(f"Color scheme: {standup_config.color_scheme}")
    print(f"Interactive elements: {standup_config.interactive_elements}")
    
    # Get branding configuration
    branding = manager.get_branding_config()
    print(f"Team branding: {branding.team_name} ({branding.primary_color})")
    
    # Get emoji configuration
    emoji_config = manager.get_emoji_config()
    success_emoji = emoji_config.get_emoji('success')
    error_emoji = emoji_config.get_emoji('error')
    print(f"Emojis: success={success_emoji}, error={error_emoji}")


def example_template_customization():
    """Example: Template customization features."""
    print("\n=== Template Customization ===")
    
    # Create customizer
    customizer = TemplateCustomizer()
    
    # Create base customization
    base_customization = TemplateCustomization(
        template_type=TemplateType.STANDUP,
        enabled=True,
        color_scheme={},
        emoji_overrides={},
        interactive_elements=True
    )
    
    print("Available color schemes:", customizer.get_available_color_schemes())
    
    # Apply dark color scheme
    dark_customization = customizer.apply_color_scheme(base_customization, ColorScheme.DARK)
    print(f"Dark theme colors: {dark_customization.color_scheme}")
    
    # Apply high contrast accessibility
    accessible_customization = customizer.apply_accessibility_mode(
        base_customization, 
        AccessibilityMode.HIGH_CONTRAST
    )
    print(f"High contrast mode: {accessible_customization.accessibility_mode}")
    print(f"Accessibility config: {accessible_customization.custom_fields.get('accessibility_config', {})}")
    
    # Create custom color scheme
    custom_colors = {
        "primary": "#ff6b6b",
        "secondary": "#4ecdc4", 
        "success": "#45b7d1",
        "warning": "#f9ca24",
        "error": "#f0932b",
        "info": "#6c5ce7"
    }
    
    custom_scheme = customizer.create_custom_color_scheme("vibrant", custom_colors)
    print(f"Created custom scheme: {custom_scheme.name}")
    
    # Apply custom scheme
    vibrant_customization = customizer.apply_color_scheme(base_customization, custom_scheme)
    print(f"Vibrant colors: {vibrant_customization.color_scheme}")


def example_configuration_validation():
    """Example: Configuration validation."""
    print("\n=== Configuration Validation ===")
    
    # Valid customization
    valid_customization = TemplateCustomization(
        template_type=TemplateType.PR_UPDATE,
        enabled=True,
        color_scheme={"primary": "#1f77b4", "success": "#2ca02c"},
        emoji_overrides={"success": "✅", "error": "❌"},
        interactive_elements=True
    )
    
    is_valid, messages = validate_template_configuration(TemplateType.PR_UPDATE, valid_customization)
    print(f"Valid customization: {is_valid}")
    if messages:
        for msg in messages:
            print(f"  {msg.severity.value}: {msg.message}")
    
    # Invalid customization (bad color format)
    invalid_customization = TemplateCustomization(
        template_type=TemplateType.PR_UPDATE,
        enabled=True,
        color_scheme={"primary": "not-a-color", "success": "#invalid"},
        emoji_overrides={},
        interactive_elements=True
    )
    
    is_valid, messages = validate_template_configuration(TemplateType.PR_UPDATE, invalid_customization)
    print(f"Invalid customization: {is_valid}")
    for msg in messages:
        print(f"  {msg.severity.value}: {msg.field_path} - {msg.message}")
    
    # Validate branding
    branding = BrandingConfig(
        team_name="Example Team",
        primary_color="#1f77b4",
        logo_emoji=":rocket:"
    )
    
    is_valid, messages = validate_branding_configuration(branding)
    print(f"Branding validation: {is_valid}")


def example_fallback_handling():
    """Example: Fallback behavior handling."""
    print("\n=== Fallback Handling ===")
    
    # Create fallback handler with different levels
    graceful_handler = create_fallback_handler(FallbackLevel.GRACEFUL)
    safe_handler = create_fallback_handler(FallbackLevel.SAFE_MODE)
    
    # Problematic customization
    problematic_customization = TemplateCustomization(
        template_type=TemplateType.ALERT,
        enabled=True,
        color_scheme={},  # Empty - will trigger fallback
        visual_indicators={},  # Empty - will trigger fallback
        interactive_elements=True
    )
    
    # Simulate error
    error = ValueError("Configuration processing failed")
    
    # Handle with graceful fallback
    graceful_result = graceful_handler.handle_customization_error(
        problematic_customization, error, "graceful test"
    )
    print(f"Graceful fallback - colors: {len(graceful_result.color_scheme)} indicators: {len(graceful_result.visual_indicators)}")
    print(f"Interactive elements still enabled: {graceful_result.interactive_elements}")
    
    # Handle with safe mode fallback
    safe_result = safe_handler.handle_customization_error(
        problematic_customization, error, "safe mode test"
    )
    print(f"Safe mode fallback - colors: {len(safe_result.color_scheme)} indicators: {len(safe_result.visual_indicators)}")
    print(f"Interactive elements disabled: {not safe_result.interactive_elements}")
    print(f"Accessibility mode enabled: {safe_result.accessibility_mode}")
    
    # Create fallback message
    original_data = {
        "alert": {"type": "build_failure", "severity": "high"},
        "affected_systems": ["CI/CD", "Deployment"]
    }
    
    fallback_message = graceful_handler.create_fallback_message(
        original_data, error, TemplateType.ALERT
    )
    print(f"Fallback message created with {len(fallback_message.get('blocks', []))} blocks")


def example_configuration_loading():
    """Example: Configuration file loading."""
    print("\n=== Configuration Loading ===")
    
    # Create example configuration
    success = create_example_team_config("demo_team", "development")
    print(f"Example config created: {success}")
    
    if success:
        # Load the configuration
        loader = ConfigurationLoader()
        config_data = loader.load_team_config("demo_team", "development")
        
        print(f"Loaded config for team: {config_data['team_settings']['team_name']}")
        print(f"Environment: {config_data.get('environment', 'unknown')}")
        print(f"Available templates: {list(config_data.get('message_templates', {}).keys())}")
        
        # Load template customizations
        customizations = loader.load_template_customizations("demo_team", "development")
        print(f"Loaded {len(customizations)} template customizations")
        
        for template_type, customization in customizations.items():
            print(f"  {template_type.value}: enabled={customization.enabled}")


def example_utility_functions():
    """Example: Using utility functions."""
    print("\n=== Utility Functions ===")
    
    # Create base customization
    base_customization = TemplateCustomization(
        template_type=TemplateType.JIRA_UPDATE,
        enabled=True
    )
    
    # Apply color scheme using utility function
    dark_customization = apply_color_scheme_to_template(base_customization, "dark")
    print(f"Applied dark scheme: {dark_customization.color_scheme.get('primary', 'N/A')}")
    
    # Create high contrast version using utility function
    high_contrast_customization = create_high_contrast_customization(base_customization)
    print(f"High contrast colors: {high_contrast_customization.color_scheme}")
    print(f"High contrast indicators: {high_contrast_customization.visual_indicators}")
    print(f"Accessibility enabled: {high_contrast_customization.accessibility_mode}")


def example_effective_configuration():
    """Example: Getting effective configuration with overrides."""
    print("\n=== Effective Configuration ===")
    
    manager = TemplateConfigurationManager()
    
    # Get effective configuration for different contexts
    base_config = manager.get_effective_template_config(TemplateType.STANDUP)
    print(f"Base standup config: {base_config.get('template_enabled', 'unknown')}")
    
    # Simulate channel-specific config
    channel_config = manager.get_effective_template_config(
        TemplateType.STANDUP,
        channel_id="#development"
    )
    print(f"Development channel config: {channel_config.get('template_enabled', 'unknown')}")
    
    # Simulate user-specific config
    user_config = manager.get_effective_template_config(
        TemplateType.STANDUP,
        channel_id="#development",
        user_id="alice"
    )
    print(f"Alice's config in #development: {user_config.get('template_enabled', 'unknown')}")


def main():
    """Run all examples."""
    print("Template Configuration and Customization System Examples")
    print("=" * 60)
    
    try:
        example_basic_configuration()
        example_template_customization()
        example_configuration_validation()
        example_fallback_handling()
        example_configuration_loading()
        example_utility_functions()
        example_effective_configuration()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise


if __name__ == "__main__":
    main()