"""Tests for template configuration and customization system."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch

from devsync_ai.core.template_config_manager import (
    TemplateConfigurationManager,
    TemplateType,
    TemplateCustomization,
    BrandingConfig,
    EmojiSetConfig
)
from devsync_ai.core.template_config_validator import (
    TemplateConfigValidator,
    ValidationSeverity,
    validate_template_configuration
)
from devsync_ai.core.template_config_loader import (
    ConfigurationLoader,
    ConfigurationLoadError
)
from devsync_ai.core.template_customizer import (
    TemplateCustomizer,
    ColorScheme,
    AccessibilityMode,
    apply_color_scheme_to_template
)
from devsync_ai.core.template_fallback_handler import (
    TemplateFallbackHandler,
    FallbackLevel,
    FallbackConfig
)


class TestTemplateConfigurationManager:
    """Test template configuration manager."""
    
    def test_load_template_config(self):
        """Test loading template configuration."""
        manager = TemplateConfigurationManager()
        
        # Test loading standup template config
        config = manager.load_template_config(TemplateType.STANDUP)
        
        assert config is not None
        assert config.template_type == TemplateType.STANDUP
        assert isinstance(config.enabled, bool)
        assert isinstance(config.color_scheme, dict)
        assert isinstance(config.emoji_overrides, dict)
        assert isinstance(config.visual_indicators, dict)
    
    def test_get_branding_config(self):
        """Test getting branding configuration."""
        manager = TemplateConfigurationManager()
        
        branding = manager.get_branding_config()
        
        assert branding is not None
        assert branding.team_name
        assert branding.primary_color.startswith('#')
        assert len(branding.primary_color) == 7  # Hex color format
    
    def test_get_emoji_config(self):
        """Test getting emoji configuration."""
        manager = TemplateConfigurationManager()
        
        emoji_config = manager.get_emoji_config()
        
        assert emoji_config is not None
        assert hasattr(emoji_config, 'style')
        assert isinstance(emoji_config.custom_mappings, dict)
        
        # Test getting emoji
        success_emoji = emoji_config.get_emoji('success')
        assert success_emoji  # Should return some emoji or text
    
    def test_update_template_config(self):
        """Test updating template configuration."""
        manager = TemplateConfigurationManager()
        
        # Create test customization
        customization = TemplateCustomization(
            template_type=TemplateType.STANDUP,
            enabled=True,
            color_scheme={"primary": "#ff0000"},
            emoji_overrides={"success": "✓"},
            interactive_elements=True
        )
        
        # Update should not fail (may not persist in test environment)
        result = manager.update_template_config(TemplateType.STANDUP, customization)
        assert isinstance(result, bool)


class TestTemplateConfigValidator:
    """Test template configuration validator."""
    
    def test_validate_template_config(self):
        """Test template configuration validation."""
        validator = TemplateConfigValidator()
        
        # Valid customization
        customization = TemplateCustomization(
            template_type=TemplateType.STANDUP,
            enabled=True,
            color_scheme={"primary": "#1f77b4"},
            emoji_overrides={"success": "✅"},
            interactive_elements=True
        )
        
        messages = validator.validate_template_config(TemplateType.STANDUP, customization)
        
        # Should have no errors
        errors = [msg for msg in messages if msg.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0
    
    def test_validate_invalid_color(self):
        """Test validation of invalid colors."""
        validator = TemplateConfigValidator()
        
        # Invalid color format
        customization = TemplateCustomization(
            template_type=TemplateType.STANDUP,
            enabled=True,
            color_scheme={"primary": "invalid-color"},
            interactive_elements=True
        )
        
        messages = validator.validate_template_config(TemplateType.STANDUP, customization)
        
        # Should have color format error
        errors = [msg for msg in messages if msg.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0
        assert any("color format" in msg.message.lower() for msg in errors)
    
    def test_validate_branding_config(self):
        """Test branding configuration validation."""
        validator = TemplateConfigValidator()
        
        # Valid branding
        branding = BrandingConfig(
            team_name="Test Team",
            primary_color="#1f77b4",
            logo_emoji=":gear:"
        )
        
        messages = validator.validate_branding_config(branding)
        
        # Should have no errors
        errors = [msg for msg in messages if msg.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0
    
    def test_validate_empty_team_name(self):
        """Test validation of empty team name."""
        validator = TemplateConfigValidator()
        
        # Empty team name
        branding = BrandingConfig(
            team_name="",
            primary_color="#1f77b4"
        )
        
        messages = validator.validate_branding_config(branding)
        
        # Should have team name error
        errors = [msg for msg in messages if msg.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0
        assert any("team name" in msg.message.lower() for msg in errors)


class TestConfigurationLoader:
    """Test configuration loader."""
    
    def test_create_example_config(self):
        """Test creating example configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            loader = ConfigurationLoader(temp_dir)
            
            # Create example config
            success = loader.create_example_config("test_team", "development")
            assert success
            
            # Verify file was created
            config_file = Path(temp_dir) / "team_config_development.yaml"
            assert config_file.exists()
            
            # Verify content is valid YAML
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            assert config_data is not None
            assert "team_settings" in config_data
            assert config_data["team_settings"]["team_id"] == "test_team"
    
    def test_load_nonexistent_config(self):
        """Test loading non-existent configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            loader = ConfigurationLoader(temp_dir)
            
            # Should return default config without error
            config_data = loader.load_team_config("nonexistent_team")
            
            assert config_data is not None
            assert "team_settings" in config_data
            assert config_data["team_settings"]["team_id"] == "default"


class TestTemplateCustomizer:
    """Test template customizer."""
    
    def test_apply_color_scheme(self):
        """Test applying color scheme."""
        customizer = TemplateCustomizer()
        
        # Create base customization
        customization = TemplateCustomization(
            template_type=TemplateType.STANDUP,
            enabled=True
        )
        
        # Apply dark color scheme
        updated = customizer.apply_color_scheme(customization, ColorScheme.DARK)
        
        assert updated.color_scheme
        assert "primary" in updated.color_scheme
        assert updated.color_scheme["primary"] != customization.color_scheme.get("primary", "")
    
    def test_apply_accessibility_mode(self):
        """Test applying accessibility mode."""
        customizer = TemplateCustomizer()
        
        # Create base customization
        customization = TemplateCustomization(
            template_type=TemplateType.STANDUP,
            enabled=True
        )
        
        # Apply high contrast accessibility
        updated = customizer.apply_accessibility_mode(customization, AccessibilityMode.HIGH_CONTRAST)
        
        assert updated.accessibility_mode
        assert "accessibility_config" in updated.custom_fields
    
    def test_get_available_schemes(self):
        """Test getting available color schemes."""
        customizer = TemplateCustomizer()
        
        schemes = customizer.get_available_color_schemes()
        
        assert isinstance(schemes, list)
        assert len(schemes) > 0
        assert "default" in schemes
        assert "dark" in schemes
        assert "high_contrast" in schemes
    
    def test_create_custom_color_scheme(self):
        """Test creating custom color scheme."""
        customizer = TemplateCustomizer()
        
        custom_colors = {
            "primary": "#ff0000",
            "secondary": "#00ff00",
            "success": "#0000ff",
            "warning": "#ffff00",
            "error": "#ff00ff",
            "info": "#00ffff"
        }
        
        scheme = customizer.create_custom_color_scheme("test_scheme", custom_colors)
        
        assert scheme.name == "test_scheme"
        assert scheme.primary == "#ff0000"
        
        # Should be available in schemes list
        schemes = customizer.get_available_color_schemes()
        assert "test_scheme" in schemes


class TestTemplateFallbackHandler:
    """Test template fallback handler."""
    
    def test_handle_customization_error(self):
        """Test handling customization errors."""
        handler = TemplateFallbackHandler()
        
        # Create customization with potential issues
        customization = TemplateCustomization(
            template_type=TemplateType.STANDUP,
            enabled=True,
            color_scheme={},  # Empty color scheme
            visual_indicators={}  # Empty indicators
        )
        
        # Simulate error
        error = ValueError("Test error")
        
        # Handle error
        result = handler.handle_customization_error(customization, error, "test")
        
        assert result is not None
        assert result.template_type == TemplateType.STANDUP
        # Should have fallback colors and indicators
        assert len(result.color_scheme) > 0
        assert len(result.visual_indicators) > 0
    
    def test_create_fallback_message(self):
        """Test creating fallback message."""
        handler = TemplateFallbackHandler()
        
        # Test data
        original_data = {
            "team": "Test Team",
            "date": "2024-01-01"
        }
        
        error = ValueError("Template processing failed")
        
        # Create fallback message
        message = handler.create_fallback_message(original_data, error, TemplateType.STANDUP)
        
        assert message is not None
        assert "blocks" in message
        assert len(message["blocks"]) > 0
        
        # Should contain team information
        text_content = str(message)
        assert "Test Team" in text_content
    
    def test_different_fallback_levels(self):
        """Test different fallback levels."""
        # Test minimal fallback
        minimal_config = FallbackConfig(level=FallbackLevel.MINIMAL)
        minimal_handler = TemplateFallbackHandler(minimal_config)
        
        # Test safe mode fallback
        safe_config = FallbackConfig(level=FallbackLevel.SAFE_MODE)
        safe_handler = TemplateFallbackHandler(safe_config)
        
        customization = TemplateCustomization(
            template_type=TemplateType.STANDUP,
            enabled=True
        )
        
        error = ValueError("Test error")
        
        minimal_result = minimal_handler.handle_customization_error(customization, error)
        safe_result = safe_handler.handle_customization_error(customization, error)
        
        # Safe mode should be more conservative
        assert not safe_result.interactive_elements  # Should disable interactions
        assert safe_result.accessibility_mode  # Should enable accessibility


class TestIntegration:
    """Integration tests for the configuration system."""
    
    def test_end_to_end_configuration(self):
        """Test end-to-end configuration workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create loader and manager
            loader = ConfigurationLoader(temp_dir)
            manager = TemplateConfigurationManager()
            customizer = TemplateCustomizer()
            
            # Create example config
            success = loader.create_example_config("integration_test", "test")
            assert success
            
            # Load template customizations
            customizations = loader.load_template_customizations("integration_test", "test")
            assert isinstance(customizations, dict)
            
            # Apply customizations
            if TemplateType.STANDUP in customizations:
                standup_config = customizations[TemplateType.STANDUP]
                
                # Apply color scheme
                updated_config = customizer.apply_color_scheme(standup_config, ColorScheme.DARK)
                
                # Validate result
                is_valid, messages = validate_template_configuration(TemplateType.STANDUP, updated_config)
                assert is_valid or len([m for m in messages if m.severity == ValidationSeverity.ERROR]) == 0
    
    def test_utility_functions(self):
        """Test utility functions."""
        # Test color scheme application utility
        customization = TemplateCustomization(
            template_type=TemplateType.STANDUP,
            enabled=True
        )
        
        updated = apply_color_scheme_to_template(customization, "dark")
        
        assert updated.color_scheme
        assert len(updated.color_scheme) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])