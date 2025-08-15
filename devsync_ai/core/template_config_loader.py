"""Template configuration loading utilities with error handling."""

import os
import yaml
import json
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
from dataclasses import asdict
from datetime import datetime

from .template_config_manager import (
    TemplateConfigurationManager,
    TemplateType,
    TemplateCustomization,
    BrandingConfig,
    EmojiSetConfig
)
from .template_config_validator import (
    TemplateConfigValidator,
    ValidationMessage,
    ValidationSeverity
)


class ConfigurationLoadError(Exception):
    """Exception raised when configuration loading fails."""
    pass


class ConfigurationLoader:
    """Handles loading and parsing of template configuration files."""
    
    def __init__(self, config_dir: str = "config"):
        """Initialize configuration loader."""
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger(__name__)
        self.validator = TemplateConfigValidator()
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Supported file formats
        self._loaders = {
            '.yaml': self._load_yaml,
            '.yml': self._load_yaml,
            '.json': self._load_json
        }
        
        self.logger.info(f"ConfigurationLoader initialized with directory: {config_dir}")
    
    def load_team_config(self, team_id: str, environment: str = "production") -> Dict[str, Any]:
        """Load team configuration from file."""
        config_files = self._get_config_file_candidates(team_id, environment)
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    self.logger.info(f"Loading config from: {config_file}")
                    config_data = self._load_config_file(config_file)
                    
                    # Validate configuration
                    validation_messages = self.validator.validate_yaml_config_file(str(config_file))
                    
                    # Log validation results
                    self._log_validation_results(validation_messages, str(config_file))
                    
                    # Check for critical errors
                    has_errors = any(msg.severity == ValidationSeverity.ERROR for msg in validation_messages)
                    if has_errors:
                        error_messages = [msg.message for msg in validation_messages 
                                        if msg.severity == ValidationSeverity.ERROR]
                        raise ConfigurationLoadError(f"Configuration validation failed: {'; '.join(error_messages)}")
                    
                    return config_data
                    
                except Exception as e:
                    self.logger.error(f"Failed to load config from {config_file}: {e}")
                    if isinstance(e, ConfigurationLoadError):
                        raise
                    continue
        
        # No valid config file found
        self.logger.warning(f"No valid configuration file found for team {team_id}, environment {environment}")
        return self._get_default_config()
    
    def save_team_config(self, team_id: str, config_data: Dict[str, Any], 
                        environment: str = "production") -> bool:
        """Save team configuration to file."""
        try:
            # Validate before saving
            temp_file = self.config_dir / "temp_config.yaml"
            with open(temp_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
            validation_messages = self.validator.validate_yaml_config_file(str(temp_file))
            temp_file.unlink()  # Clean up temp file
            
            # Check for errors
            has_errors = any(msg.severity == ValidationSeverity.ERROR for msg in validation_messages)
            if has_errors:
                error_messages = [msg.message for msg in validation_messages 
                                if msg.severity == ValidationSeverity.ERROR]
                self.logger.error(f"Cannot save invalid configuration: {'; '.join(error_messages)}")
                return False
            
            # Save to actual file
            config_file = self.config_dir / f"team_config_{environment}.yaml"
            
            # Add metadata
            config_data["last_updated"] = datetime.now().isoformat()
            config_data["environment"] = environment
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to: {config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def load_template_customizations(self, team_id: str, 
                                   environment: str = "production") -> Dict[TemplateType, TemplateCustomization]:
        """Load all template customizations for a team."""
        config_data = self.load_team_config(team_id, environment)
        customizations = {}
        
        try:
            message_templates = config_data.get("message_templates", {})
            
            for template_name, template_config in message_templates.items():
                try:
                    # Map template name to TemplateType
                    template_type = self._map_template_name(template_name)
                    if template_type:
                        customization = self._create_customization_from_config(
                            template_type, template_config
                        )
                        customizations[template_type] = customization
                        
                except Exception as e:
                    self.logger.warning(f"Failed to load customization for {template_name}: {e}")
                    continue
            
            self.logger.info(f"Loaded {len(customizations)} template customizations for team {team_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to load template customizations: {e}")
        
        return customizations
    
    def save_template_customizations(self, team_id: str, 
                                   customizations: Dict[TemplateType, TemplateCustomization],
                                   environment: str = "production") -> bool:
        """Save template customizations to team config."""
        try:
            # Load existing config
            config_data = self.load_team_config(team_id, environment)
            
            # Update message templates section
            if "message_templates" not in config_data:
                config_data["message_templates"] = {}
            
            for template_type, customization in customizations.items():
                template_config = self._create_config_from_customization(customization)
                config_data["message_templates"][template_type.value] = template_config
            
            # Save updated config
            return self.save_team_config(team_id, config_data, environment)
            
        except Exception as e:
            self.logger.error(f"Failed to save template customizations: {e}")
            return False
    
    def load_branding_config(self, team_id: str, environment: str = "production") -> BrandingConfig:
        """Load branding configuration for a team."""
        config_data = self.load_team_config(team_id, environment)
        
        try:
            team_settings = config_data.get("team_settings", {})
            visual_styling = team_settings.get("visual_styling", {})
            
            branding = BrandingConfig(
                team_name=team_settings.get("team_name", "DevSync AI"),
                logo_emoji=team_settings.get("custom_fields", {}).get("logo_emoji", ":gear:"),
                primary_color=visual_styling.get("brand_color", "#1f77b4"),
                secondary_color=visual_styling.get("secondary_color", "#ff7f0e"),
                success_color=visual_styling.get("success_color", "#2ca02c"),
                warning_color=visual_styling.get("warning_color", "#ff7f0e"),
                error_color=visual_styling.get("error_color", "#d62728"),
                footer_text=team_settings.get("custom_fields", {}).get("footer_text"),
                header_style=team_settings.get("custom_fields", {}).get("header_style", "standard")
            )
            
            # Validate branding config
            validation_messages = self.validator.validate_branding_config(branding)
            self._log_validation_results(validation_messages, f"branding for team {team_id}")
            
            return branding
            
        except Exception as e:
            self.logger.error(f"Failed to load branding config: {e}")
            return BrandingConfig(team_name="DevSync AI")
    
    def save_branding_config(self, team_id: str, branding: BrandingConfig,
                           environment: str = "production") -> bool:
        """Save branding configuration for a team."""
        try:
            # Validate branding config
            validation_messages = self.validator.validate_branding_config(branding)
            has_errors = any(msg.severity == ValidationSeverity.ERROR for msg in validation_messages)
            
            if has_errors:
                error_messages = [msg.message for msg in validation_messages 
                                if msg.severity == ValidationSeverity.ERROR]
                self.logger.error(f"Cannot save invalid branding config: {'; '.join(error_messages)}")
                return False
            
            # Load existing config
            config_data = self.load_team_config(team_id, environment)
            
            # Update team settings
            if "team_settings" not in config_data:
                config_data["team_settings"] = {}
            
            team_settings = config_data["team_settings"]
            team_settings["team_name"] = branding.team_name
            
            # Update visual styling
            if "visual_styling" not in team_settings:
                team_settings["visual_styling"] = {}
            
            visual_styling = team_settings["visual_styling"]
            visual_styling.update({
                "brand_color": branding.primary_color,
                "secondary_color": branding.secondary_color,
                "success_color": branding.success_color,
                "warning_color": branding.warning_color,
                "error_color": branding.error_color
            })
            
            # Update custom fields
            if "custom_fields" not in team_settings:
                team_settings["custom_fields"] = {}
            
            team_settings["custom_fields"].update({
                "logo_emoji": branding.logo_emoji,
                "footer_text": branding.footer_text,
                "header_style": branding.header_style
            })
            
            # Save updated config
            return self.save_team_config(team_id, config_data, environment)
            
        except Exception as e:
            self.logger.error(f"Failed to save branding config: {e}")
            return False
    
    def load_emoji_config(self, team_id: str, environment: str = "production") -> EmojiSetConfig:
        """Load emoji configuration for a team."""
        config_data = self.load_team_config(team_id, environment)
        
        try:
            team_settings = config_data.get("team_settings", {})
            visual_styling = team_settings.get("visual_styling", {})
            
            from .config_manager import EmojiStyle
            
            emoji_style_str = visual_styling.get("emoji_style", "standard")
            emoji_style = EmojiStyle(emoji_style_str) if emoji_style_str in [e.value for e in EmojiStyle] else EmojiStyle.STANDARD
            
            emoji_config = EmojiSetConfig(
                style=emoji_style,
                custom_mappings=visual_styling.get("custom_emojis", {}),
                fallback_enabled=True
            )
            
            # Validate emoji config
            validation_messages = self.validator.validate_emoji_config(emoji_config)
            self._log_validation_results(validation_messages, f"emoji config for team {team_id}")
            
            return emoji_config
            
        except Exception as e:
            self.logger.error(f"Failed to load emoji config: {e}")
            return EmojiSetConfig()
    
    def create_example_config(self, team_id: str, environment: str = "development") -> bool:
        """Create an example configuration file for a team."""
        try:
            example_config = {
                "version": "1.0.0",
                "environment": environment,
                "migration_version": 2,
                "team_settings": {
                    "team_id": team_id,
                    "team_name": f"{team_id.title()} Team",
                    "timezone": "UTC",
                    "default_formatting": "rich",
                    "visual_styling": {
                        "brand_color": "#1f77b4",
                        "secondary_color": "#ff7f0e",
                        "success_color": "#2ca02c",
                        "warning_color": "#ff7f0e",
                        "error_color": "#d62728",
                        "emoji_style": "standard",
                        "message_density": "detailed",
                        "show_avatars": True,
                        "show_timestamps": True,
                        "compact_mode": False,
                        "custom_emojis": {
                            "success": "✅",
                            "warning": "⚠️",
                            "error": "❌"
                        }
                    },
                    "content_preferences": {
                        "show_technical_details": True,
                        "show_file_changes": True,
                        "show_ci_status": True,
                        "max_description_length": 500
                    },
                    "interactive_settings": {
                        "interactive_mode": True,
                        "show_action_buttons": True,
                        "enable_threading": True
                    },
                    "custom_fields": {
                        "logo_emoji": ":gear:",
                        "header_style": "standard"
                    }
                },
                "message_templates": {
                    "standup": {
                        "template_type": "standup",
                        "enabled": True,
                        "custom_fields": {
                            "show_team_health": True,
                            "show_progress_bars": True,
                            "show_velocity": True
                        }
                    },
                    "pr_update": {
                        "template_type": "pr_update",
                        "enabled": True,
                        "custom_fields": {
                            "show_diff_stats": True,
                            "show_ci_status": True,
                            "highlight_conflicts": True
                        }
                    },
                    "jira_update": {
                        "template_type": "jira_update",
                        "enabled": True,
                        "custom_fields": {
                            "show_story_points": True,
                            "show_epic_link": True,
                            "highlight_blockers": True
                        }
                    },
                    "alert": {
                        "template_type": "alert",
                        "enabled": True,
                        "custom_fields": {
                            "escalation_enabled": True,
                            "show_severity": True,
                            "show_affected_systems": True
                        }
                    }
                }
            }
            
            return self.save_team_config(team_id, example_config, environment)
            
        except Exception as e:
            self.logger.error(f"Failed to create example config: {e}")
            return False
    
    def _get_config_file_candidates(self, team_id: str, environment: str) -> List[Path]:
        """Get list of potential configuration files in order of preference."""
        candidates = [
            self.config_dir / f"team_config_{environment}.yaml",
            self.config_dir / f"team_config_{environment}.yml",
            self.config_dir / f"team_config_{environment}.json",
            self.config_dir / f"team_config_{team_id}_{environment}.yaml",
            self.config_dir / f"team_config_{team_id}_{environment}.yml",
            self.config_dir / f"team_config_{team_id}.yaml",
            self.config_dir / f"team_config_{team_id}.yml",
            self.config_dir / "team_config.yaml",
            self.config_dir / "team_config.yml",
            self.config_dir / "team_config.json"
        ]
        
        return candidates
    
    def _load_config_file(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration from a specific file."""
        suffix = config_file.suffix.lower()
        
        if suffix not in self._loaders:
            raise ConfigurationLoadError(f"Unsupported file format: {suffix}")
        
        try:
            return self._loaders[suffix](config_file)
        except Exception as e:
            raise ConfigurationLoadError(f"Failed to parse {config_file}: {str(e)}")
    
    def _load_yaml(self, config_file: Path) -> Dict[str, Any]:
        """Load YAML configuration file."""
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data if data is not None else {}
    
    def _load_json(self, config_file: Path) -> Dict[str, Any]:
        """Load JSON configuration file."""
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration when no file is found."""
        return {
            "version": "1.0.0",
            "environment": "production",
            "migration_version": 2,
            "team_settings": {
                "team_id": "default",
                "team_name": "Default Team",
                "visual_styling": {
                    "brand_color": "#1f77b4",
                    "emoji_style": "standard",
                    "message_density": "detailed"
                }
            },
            "message_templates": {}
        }
    
    def _map_template_name(self, template_name: str) -> Optional[TemplateType]:
        """Map template name string to TemplateType enum."""
        mapping = {
            "standup": TemplateType.STANDUP,
            "pr_update": TemplateType.PR_UPDATE,
            "jira_update": TemplateType.JIRA_UPDATE,
            "alert": TemplateType.ALERT,
            "deployment": TemplateType.DEPLOYMENT
        }
        
        return mapping.get(template_name)
    
    def _create_customization_from_config(self, template_type: TemplateType,
                                        template_config: Dict[str, Any]) -> TemplateCustomization:
        """Create TemplateCustomization from configuration dictionary."""
        custom_fields = template_config.get("custom_fields", {})
        
        return TemplateCustomization(
            template_type=template_type,
            enabled=template_config.get("enabled", True),
            color_scheme=custom_fields.get("color_scheme", {}),
            emoji_overrides=custom_fields.get("emoji_overrides", {}),
            visual_indicators=custom_fields.get("visual_indicators", {}),
            interactive_elements=custom_fields.get("interactive_elements", True),
            accessibility_mode=custom_fields.get("accessibility_mode", False),
            custom_fields={k: v for k, v in custom_fields.items() 
                         if k not in ["color_scheme", "emoji_overrides", "visual_indicators", 
                                    "interactive_elements", "accessibility_mode"]}
        )
    
    def _create_config_from_customization(self, customization: TemplateCustomization) -> Dict[str, Any]:
        """Create configuration dictionary from TemplateCustomization."""
        custom_fields = dict(customization.custom_fields)
        custom_fields.update({
            "color_scheme": customization.color_scheme,
            "emoji_overrides": customization.emoji_overrides,
            "visual_indicators": customization.visual_indicators,
            "interactive_elements": customization.interactive_elements,
            "accessibility_mode": customization.accessibility_mode
        })
        
        return {
            "template_type": customization.template_type.value,
            "enabled": customization.enabled,
            "custom_fields": custom_fields
        }
    
    def _log_validation_results(self, messages: List[ValidationMessage], context: str):
        """Log validation results with appropriate levels."""
        if not messages:
            return
        
        errors = [msg for msg in messages if msg.severity == ValidationSeverity.ERROR]
        warnings = [msg for msg in messages if msg.severity == ValidationSeverity.WARNING]
        infos = [msg for msg in messages if msg.severity == ValidationSeverity.INFO]
        
        if errors:
            self.logger.error(f"Configuration errors in {context}: {len(errors)} errors")
            for error in errors:
                self.logger.error(f"  {error.field_path}: {error.message}")
        
        if warnings:
            self.logger.warning(f"Configuration warnings in {context}: {len(warnings)} warnings")
            for warning in warnings:
                self.logger.warning(f"  {warning.field_path}: {warning.message}")
        
        if infos:
            self.logger.info(f"Configuration suggestions for {context}: {len(infos)} suggestions")
            for info in infos:
                self.logger.info(f"  {info.field_path}: {info.message}")


# Utility functions for easy access
def load_team_template_config(team_id: str, environment: str = "production") -> Dict[str, Any]:
    """Load team configuration using default loader."""
    loader = ConfigurationLoader()
    return loader.load_team_config(team_id, environment)


def create_example_team_config(team_id: str, environment: str = "development") -> bool:
    """Create example configuration for a team."""
    loader = ConfigurationLoader()
    return loader.create_example_config(team_id, environment)


def validate_team_config_file(config_path: str) -> bool:
    """Validate a team configuration file."""
    validator = TemplateConfigValidator()
    is_valid, messages = validator.validate_yaml_config_file(config_path)
    
    # Log results
    logger = logging.getLogger(__name__)
    if messages:
        for message in messages:
            if message.severity == ValidationSeverity.ERROR:
                logger.error(f"{message.field_path}: {message.message}")
            elif message.severity == ValidationSeverity.WARNING:
                logger.warning(f"{message.field_path}: {message.message}")
            else:
                logger.info(f"{message.field_path}: {message.message}")
    
    return is_valid