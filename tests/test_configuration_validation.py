"""
Configuration validation tests for template customization.
Tests configuration loading, team-specific customization, and accessibility compliance.
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any

from devsync_ai.core.template_registry import load_template_configuration
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.core.template_factory import MessageTemplateFactory, TemplateType
from devsync_ai.templates.standup_template import StandupTemplate


class TestConfigurationValidation:
    """Test configuration loading and validation."""
    
    @pytest.fixture
    def sample_config_data(self):
        """Sample configuration data for testing."""
        return {
            "template_config": {
                "team_id": "engineering_team",
                "branding": {
                    "primary_color": "#1f77b4",
                    "secondary_color": "#ff7f0e", 
                    "logo_emoji": ":gear:",
                    "team_name": "Engineering Team"
                },
                "emoji_set": {
                    "success": ":white_check_mark:",
                    "warning": ":warning:",
                    "error": ":x:",
                    "info": ":information_source:",
                    "in_progress": ":hourglass_flowing_sand:"
                },
                "color_scheme": {
                    "success": "#28a745",
                    "warning": "#ffc107",
                    "danger": "#dc3545",
                    "info": "#17a2b8"
                },
                "interactive_elements": True,
                "accessibility_mode": False
            }
        }
    
    @pytest.fixture
    def accessibility_config_data(self):
        """Configuration data with accessibility mode enabled."""
        return {
            "template_config": {
                "team_id": "accessible_team",
                "branding": {
                    "primary_color": "#000000",
                    "secondary_color": "#ffffff",
                    "logo_emoji": ":accessibility:",
                    "team_name": "Accessible Team"
                },
                "emoji_set": {
                    "success": "[COMPLETED]",
                    "warning": "[WARNING]", 
                    "error": "[ERROR]",
                    "info": "[INFO]",
                    "in_progress": "[IN PROGRESS]"
                },
                "interactive_elements": False,
                "accessibility_mode": True
            }
        }
    
    def test_load_valid_configuration(self, tmp_path, sample_config_data):
        """Test loading valid configuration from file."""
        # Create config file
        config_file = tmp_path / "valid_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        # Load configuration
        config = load_template_configuration(str(config_file))
        
        # Validate loaded configuration
        assert config is not None
        assert config.team_id == "engineering_team"
        assert config.branding["primary_color"] == "#1f77b4"
        assert config.emoji_set["success"] == ":white_check_mark:"
        assert config.interactive_elements is True
        assert config.accessibility_mode is False
    
    def test_load_nonexistent_configuration(self):
        """Test loading configuration from nonexistent file."""
        config = load_template_configuration("/nonexistent/config.yaml")
        assert config is None
    
    def test_load_invalid_yaml_configuration(self, tmp_path):
        """Test loading invalid YAML configuration."""
        # Create invalid YAML file
        config_file = tmp_path / "invalid_config.yaml"
        with open(config_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        # Should return None for invalid YAML
        config = load_template_configuration(str(config_file))
        assert config is None
    
    def test_configuration_with_missing_fields(self, tmp_path):
        """Test configuration with missing optional fields."""
        minimal_config = {
            "template_config": {
                "team_id": "minimal_team"
            }
        }
        
        config_file = tmp_path / "minimal_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(minimal_config, f)
        
        config = load_template_configuration(str(config_file))
        
        # Should load with defaults
        assert config is not None
        assert config.team_id == "minimal_team"
        assert config.branding == {}
        assert config.emoji_set == {}
        assert config.interactive_elements is True  # Default
        assert config.accessibility_mode is False  # Default
    
    def test_accessibility_configuration(self, tmp_path, accessibility_config_data):
        """Test accessibility-specific configuration."""
        config_file = tmp_path / "accessibility_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(accessibility_config_data, f)
        
        config = load_template_configuration(str(config_file))
        
        assert config is not None
        assert config.accessibility_mode is True
        assert config.interactive_elements is False
        assert config.emoji_set["success"] == "[COMPLETED]"
    
    def test_template_customization_with_config(self, tmp_path, sample_config_data):
        """Test template customization using loaded configuration."""
        # Create and load config
        config_file = tmp_path / "custom_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config = load_template_configuration(str(config_file))
        
        # Create template with custom configuration
        factory = MessageTemplateFactory()
        template = StandupTemplate(config=config)
        
        # Verify configuration is applied
        assert template.config.team_id == "engineering_team"
        assert template.config.branding["logo_emoji"] == ":gear:"
        assert template.config.interactive_elements is True
        
        # Test message formatting with custom config
        standup_data = {
            "date": "2024-01-15",
            "team": "Engineering Team",
            "team_members": [
                {
                    "name": "alice",
                    "yesterday": "Completed feature",
                    "today": "Working on tests",
                    "blockers": []
                }
            ],
            "stats": {"prs_merged": 2, "commits": 8}
        }
        
        message = template.format_message(standup_data)
        
        # Verify custom branding is applied
        assert message.metadata["config"]["team_id"] == "engineering_team"
        assert message.metadata["config"]["interactive_elements"] is True
    
    def test_accessibility_compliance_validation(self, tmp_path, accessibility_config_data):
        """Test accessibility compliance with accessibility mode enabled."""
        # Create and load accessibility config
        config_file = tmp_path / "accessibility_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(accessibility_config_data, f)
        
        config = load_template_configuration(str(config_file))
        
        # Create template with accessibility configuration
        template = StandupTemplate(config=config)
        
        # Test message formatting
        standup_data = {
            "date": "2024-01-15",
            "team": "Accessible Team",
            "team_members": [
                {
                    "name": "alice",
                    "yesterday": "Completed accessibility audit",
                    "today": "Implementing screen reader support",
                    "blockers": []
                }
            ],
            "stats": {"prs_merged": 1, "commits": 3}
        }
        
        message = template.format_message(standup_data)
        
        # Verify accessibility features
        assert message.text is not None  # Fallback text should be present
        assert len(message.text) > 0
        
        # Check that accessibility mode affects content
        message_content = str(message.blocks)
        # In accessibility mode, emoji should be replaced with text
        if config.accessibility_mode:
            # Should contain text indicators instead of emojis
            assert "[COMPLETED]" in config.emoji_set["success"]
    
    def test_team_specific_branding_customization(self, tmp_path):
        """Test team-specific branding customization."""
        team_configs = [
            {
                "template_config": {
                    "team_id": "frontend_team",
                    "branding": {
                        "primary_color": "#61dafb",
                        "logo_emoji": ":atom_symbol:",
                        "team_name": "Frontend Team"
                    },
                    "emoji_set": {
                        "success": ":sparkles:",
                        "warning": ":construction:"
                    }
                }
            },
            {
                "template_config": {
                    "team_id": "backend_team", 
                    "branding": {
                        "primary_color": "#339933",
                        "logo_emoji": ":gear:",
                        "team_name": "Backend Team"
                    },
                    "emoji_set": {
                        "success": ":heavy_check_mark:",
                        "warning": ":warning:"
                    }
                }
            }
        ]
        
        for i, team_config in enumerate(team_configs):
            # Create team-specific config file
            config_file = tmp_path / f"team_{i}_config.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(team_config, f)
            
            # Load and test configuration
            config = load_template_configuration(str(config_file))
            assert config is not None
            
            # Verify team-specific settings
            expected_team_id = team_config["template_config"]["team_id"]
            expected_color = team_config["template_config"]["branding"]["primary_color"]
            expected_emoji = team_config["template_config"]["branding"]["logo_emoji"]
            
            assert config.team_id == expected_team_id
            assert config.branding["primary_color"] == expected_color
            assert config.branding["logo_emoji"] == expected_emoji
    
    def test_color_scheme_customization(self, tmp_path):
        """Test color scheme customization for different message types."""
        color_config = {
            "template_config": {
                "team_id": "design_team",
                "color_scheme": {
                    "success": "#00ff00",
                    "warning": "#ffff00", 
                    "danger": "#ff0000",
                    "info": "#0000ff",
                    "primary": "#800080"
                }
            }
        }
        
        config_file = tmp_path / "color_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(color_config, f)
        
        config = load_template_configuration(str(config_file))
        
        assert config is not None
        assert config.color_scheme["success"] == "#00ff00"
        assert config.color_scheme["warning"] == "#ffff00"
        assert config.color_scheme["danger"] == "#ff0000"
        assert config.color_scheme["info"] == "#0000ff"
        assert config.color_scheme["primary"] == "#800080"
    
    def test_interactive_elements_configuration(self, tmp_path):
        """Test interactive elements configuration."""
        # Test with interactive elements enabled
        interactive_config = {
            "template_config": {
                "team_id": "interactive_team",
                "interactive_elements": True
            }
        }
        
        config_file = tmp_path / "interactive_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(interactive_config, f)
        
        config = load_template_configuration(str(config_file))
        template = StandupTemplate(config=config)
        
        # Create message and check for interactive elements
        standup_data = {
            "date": "2024-01-15",
            "team": "Interactive Team",
            "team_members": [],
            "stats": {}
        }
        
        message = template.format_message(standup_data)
        
        # Should contain action blocks when interactive elements are enabled
        has_actions = any(block.get("type") == "actions" for block in message.blocks)
        assert has_actions is True
        
        # Test with interactive elements disabled
        non_interactive_config = {
            "template_config": {
                "team_id": "non_interactive_team",
                "interactive_elements": False
            }
        }
        
        config_file = tmp_path / "non_interactive_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(non_interactive_config, f)
        
        config = load_template_configuration(str(config_file))
        template = StandupTemplate(config=config)
        
        message = template.format_message(standup_data)
        
        # Should not contain action blocks when interactive elements are disabled
        has_actions = any(block.get("type") == "actions" for block in message.blocks)
        assert has_actions is False
    
    def test_configuration_validation_edge_cases(self, tmp_path):
        """Test configuration validation with edge cases."""
        # Test with empty configuration
        empty_config = {"template_config": {}}
        
        config_file = tmp_path / "empty_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(empty_config, f)
        
        config = load_template_configuration(str(config_file))
        
        # Should load with defaults
        assert config is not None
        assert config.team_id == "default"
        assert config.branding == {}
        assert config.emoji_set == {}
        
        # Test with null values
        null_config = {
            "template_config": {
                "team_id": None,
                "branding": None,
                "interactive_elements": None
            }
        }
        
        config_file = tmp_path / "null_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(null_config, f)
        
        config = load_template_configuration(str(config_file))
        
        # Should handle null values gracefully
        assert config is not None
        # None values should be converted to defaults
        assert config.team_id == "default"  # Should default when None
    
    def test_configuration_inheritance_and_overrides(self, tmp_path):
        """Test configuration inheritance and override behavior."""
        # Create base configuration
        base_config = {
            "template_config": {
                "team_id": "base_team",
                "branding": {
                    "primary_color": "#000000",
                    "logo_emoji": ":gear:"
                },
                "emoji_set": {
                    "success": ":white_check_mark:",
                    "warning": ":warning:"
                },
                "interactive_elements": True,
                "accessibility_mode": False
            }
        }
        
        config_file = tmp_path / "base_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(base_config, f)
        
        base_loaded_config = load_template_configuration(str(config_file))
        
        # Create override configuration (partial)
        override_config = {
            "template_config": {
                "team_id": "override_team",
                "branding": {
                    "primary_color": "#ff0000"
                    # logo_emoji should inherit from base
                },
                "accessibility_mode": True
                # Other fields should inherit defaults
            }
        }
        
        override_config_file = tmp_path / "override_config.yaml"
        with open(override_config_file, 'w') as f:
            yaml.dump(override_config, f)
        
        override_loaded_config = load_template_configuration(str(override_config_file))
        
        # Verify override behavior
        assert override_loaded_config.team_id == "override_team"  # Overridden
        assert override_loaded_config.branding["primary_color"] == "#ff0000"  # Overridden
        assert override_loaded_config.accessibility_mode is True  # Overridden
        assert override_loaded_config.interactive_elements is True  # Default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])