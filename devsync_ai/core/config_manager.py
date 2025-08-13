"""Flexible configuration system for team customization."""

import os
import json
import yaml
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
from copy import deepcopy

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


class ConfigFormat(Enum):
    """Supported configuration formats."""
    JSON = "json"
    YAML = "yaml"
    ENVIRONMENT = "environment"


class MessageDensity(Enum):
    """Message density options."""
    COMPACT = "compact"
    DETAILED = "detailed"
    MINIMAL = "minimal"


class EmojiStyle(Enum):
    """Emoji style options."""
    STANDARD = "standard"
    CUSTOM = "custom"
    MINIMAL = "minimal"
    NONE = "none"


class FormattingStyle(Enum):
    """Formatting style options."""
    RICH = "rich"
    SIMPLE = "simple"
    PLAIN = "plain"


@dataclass
class VisualStyling:
    """Visual styling configuration."""
    brand_color: str = "#1f77b4"
    secondary_color: str = "#ff7f0e"
    success_color: str = "#2ca02c"
    warning_color: str = "#ff7f0e"
    error_color: str = "#d62728"
    emoji_style: EmojiStyle = EmojiStyle.STANDARD
    custom_emojis: Dict[str, str] = field(default_factory=dict)
    font_family: str = "default"
    message_density: MessageDensity = MessageDensity.DETAILED
    show_avatars: bool = True
    show_timestamps: bool = True
    compact_mode: bool = False


@dataclass
class MessageContentPreferences:
    """Message content preferences."""
    show_technical_details: bool = True
    show_file_changes: bool = True
    show_ci_status: bool = True
    show_review_comments: bool = True
    max_description_length: int = 500
    max_commit_messages: int = 5
    include_diff_stats: bool = True
    show_branch_info: bool = True
    highlight_breaking_changes: bool = True
    show_deployment_status: bool = True


@dataclass
class InteractiveElementSettings:
    """Interactive element settings."""
    interactive_mode: bool = True
    show_action_buttons: bool = True
    enable_quick_actions: bool = True
    show_expandable_sections: bool = True
    enable_threading: bool = True
    show_external_links: bool = True
    confirmation_level: str = "standard"  # none, standard, detailed
    button_style: str = "default"  # default, minimal, prominent


@dataclass
class ChannelSpecificFormatting:
    """Channel-specific formatting overrides."""
    channel_id: str
    formatting_style: FormattingStyle = FormattingStyle.RICH
    message_density: Optional[MessageDensity] = None
    show_technical_details: Optional[bool] = None
    hide_technical_details: Optional[bool] = None
    high_level_summary: Optional[bool] = None
    batch_threshold: Optional[int] = None
    interactive_elements: Optional[bool] = None
    custom_branding: Dict[str, Any] = field(default_factory=dict)
    notification_preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserPersonalPreferences:
    """User personal preferences."""
    user_id: str
    timezone: str = "UTC"
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M:%S"
    notification_frequency: str = "normal"  # minimal, normal, verbose
    preferred_density: MessageDensity = MessageDensity.DETAILED
    show_personal_mentions: bool = True
    highlight_assigned_items: bool = True
    custom_keywords: List[str] = field(default_factory=list)
    mute_channels: List[str] = field(default_factory=list)
    priority_channels: List[str] = field(default_factory=list)


@dataclass
class MessageTemplateConfig:
    """Message template-specific configuration."""
    template_type: str
    enabled: bool = True
    show_file_changes: bool = True
    show_ci_status: bool = True
    show_review_status: bool = True
    max_description_length: int = 200
    include_author_info: bool = True
    show_labels: bool = True
    show_milestone: bool = True
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TeamSettings:
    """Team-wide settings."""
    team_id: str
    team_name: str
    visual_styling: VisualStyling = field(default_factory=VisualStyling)
    content_preferences: MessageContentPreferences = field(default_factory=MessageContentPreferences)
    interactive_settings: InteractiveElementSettings = field(default_factory=InteractiveElementSettings)
    default_formatting: FormattingStyle = FormattingStyle.RICH
    timezone: str = "UTC"
    business_hours: Dict[str, str] = field(default_factory=lambda: {
        "start": "09:00",
        "end": "17:00",
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
    })
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigurationSchema:
    """Complete configuration schema."""
    version: str = "1.0.0"
    team_settings: TeamSettings = field(default_factory=lambda: TeamSettings(team_id="default", team_name="Default Team"))
    channel_overrides: Dict[str, ChannelSpecificFormatting] = field(default_factory=dict)
    user_preferences: Dict[str, UserPersonalPreferences] = field(default_factory=dict)
    message_templates: Dict[str, MessageTemplateConfig] = field(default_factory=dict)
    environment: str = "production"
    last_updated: datetime = field(default_factory=datetime.now)
    migration_version: int = 1


class ConfigurationValidator:
    """Configuration validation and schema checking."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._schema = self._create_json_schema()
    
    def _create_json_schema(self) -> Dict[str, Any]:
        """Create JSON schema for configuration validation."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "team_settings": {
                    "type": "object",
                    "properties": {
                        "team_id": {"type": "string"},
                        "team_name": {"type": "string"},
                        "visual_styling": {
                            "type": "object",
                            "properties": {
                                "brand_color": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
                                "emoji_style": {"type": "string", "enum": ["standard", "custom", "minimal", "none"]},
                                "message_density": {"type": "string", "enum": ["compact", "detailed", "minimal"]}
                            }
                        }
                    },
                    "required": ["team_id", "team_name"]
                },
                "channel_overrides": {
                    "type": "object",
                    "patternProperties": {
                        "^#.*": {
                            "type": "object",
                            "properties": {
                                "channel_id": {"type": "string"},
                                "formatting_style": {"type": "string", "enum": ["rich", "simple", "plain"]},
                                "batch_threshold": {"type": "integer", "minimum": 1, "maximum": 50}
                            }
                        }
                    }
                },
                "message_templates": {
                    "type": "object",
                    "patternProperties": {
                        ".*": {
                            "type": "object",
                            "properties": {
                                "template_type": {"type": "string"},
                                "enabled": {"type": "boolean"},
                                "max_description_length": {"type": "integer", "minimum": 50, "maximum": 2000}
                            }
                        }
                    }
                }
            },
            "required": ["version", "team_settings"]
        }
    
    def validate(self, config_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate configuration against schema."""
        errors = []
        
        try:
            if HAS_JSONSCHEMA:
                jsonschema.validate(config_data, self._schema)
            else:
                # Basic validation without jsonschema
                errors.extend(self._basic_validation(config_data))
            
            # Additional custom validations
            errors.extend(self._validate_colors(config_data))
            errors.extend(self._validate_channels(config_data))
            errors.extend(self._validate_templates(config_data))
            
            return len(errors) == 0, errors
            
        except Exception as e:
            if HAS_JSONSCHEMA and "ValidationError" in str(type(e)):
                errors.append(f"Schema validation error: {e.message}")
            else:
                errors.append(f"Validation error: {str(e)}")
            return False, errors
    
    def _validate_colors(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate color values."""
        errors = []
        
        team_settings = config_data.get("team_settings", {})
        visual_styling = team_settings.get("visual_styling", {})
        
        color_fields = ["brand_color", "secondary_color", "success_color", "warning_color", "error_color"]
        
        for field in color_fields:
            color = visual_styling.get(field)
            if color and not self._is_valid_color(color):
                errors.append(f"Invalid color format for {field}: {color}")
        
        return errors
    
    def _is_valid_color(self, color: str) -> bool:
        """Check if color is valid hex format."""
        import re
        return bool(re.match(r'^#[0-9a-fA-F]{6}$', color))
    
    def _validate_channels(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate channel configurations."""
        errors = []
        
        channel_overrides = config_data.get("channel_overrides", {})
        
        for channel_id, config in channel_overrides.items():
            if not channel_id.startswith("#"):
                errors.append(f"Channel ID must start with #: {channel_id}")
            
            batch_threshold = config.get("batch_threshold")
            if batch_threshold and (batch_threshold < 1 or batch_threshold > 50):
                errors.append(f"Invalid batch_threshold for {channel_id}: {batch_threshold}")
        
        return errors
    
    def _validate_templates(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate template configurations."""
        errors = []
        
        message_templates = config_data.get("message_templates", {})
        
        for template_name, config in message_templates.items():
            max_length = config.get("max_description_length")
            if max_length and (max_length < 50 or max_length > 2000):
                errors.append(f"Invalid max_description_length for {template_name}: {max_length}")
        
        return errors
    
    def _basic_validation(self, config_data: Dict[str, Any]) -> List[str]:
        """Basic validation without jsonschema."""
        errors = []
        
        # Check required fields
        if "team_settings" not in config_data:
            errors.append("Missing required field: team_settings")
        else:
            team_settings = config_data["team_settings"]
            if "team_id" not in team_settings:
                errors.append("Missing required field: team_settings.team_id")
            if "team_name" not in team_settings:
                errors.append("Missing required field: team_settings.team_name")
        
        return errors


class ConfigurationMigrator:
    """Handle configuration migrations between versions."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._migrations = {
            1: self._migrate_to_v1,
            2: self._migrate_to_v2,
        }
    
    def migrate(self, config_data: Dict[str, Any], target_version: int) -> Dict[str, Any]:
        """Migrate configuration to target version."""
        current_version = config_data.get("migration_version", 1)
        
        if current_version == target_version:
            return config_data
        
        self.logger.info(f"Migrating configuration from v{current_version} to v{target_version}")
        
        migrated_config = deepcopy(config_data)
        
        for version in range(current_version + 1, target_version + 1):
            if version in self._migrations:
                migrated_config = self._migrations[version](migrated_config)
                migrated_config["migration_version"] = version
                self.logger.info(f"Applied migration to v{version}")
        
        return migrated_config
    
    def _migrate_to_v1(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate to version 1 (baseline)."""
        # Add any missing required fields
        if "team_settings" not in config_data:
            config_data["team_settings"] = {
                "team_id": "default",
                "team_name": "Default Team"
            }
        
        return config_data
    
    def _migrate_to_v2(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate to version 2 (add new fields)."""
        # Add new visual styling options
        team_settings = config_data.get("team_settings", {})
        visual_styling = team_settings.get("visual_styling", {})
        
        if "compact_mode" not in visual_styling:
            visual_styling["compact_mode"] = False
        
        if "show_avatars" not in visual_styling:
            visual_styling["show_avatars"] = True
        
        team_settings["visual_styling"] = visual_styling
        config_data["team_settings"] = team_settings
        
        return config_data


class FlexibleConfigurationManager:
    """Comprehensive configuration management system."""
    
    def __init__(self, config_dir: str = "config", environment: str = "production"):
        """Initialize configuration manager."""
        self.config_dir = Path(config_dir)
        self.environment = environment
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.validator = ConfigurationValidator()
        self.migrator = ConfigurationMigrator()
        
        # Configuration cache
        self._config_cache: Optional[ConfigurationSchema] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 300  # 5 minutes
        
        # Change listeners
        self._change_listeners: List[Callable[[ConfigurationSchema], None]] = []
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"ConfigurationManager initialized for environment: {environment}")
    
    def load_configuration(self, force_reload: bool = False) -> ConfigurationSchema:
        """Load configuration with caching."""
        
        # Check cache first
        if not force_reload and self._is_cache_valid():
            return self._config_cache
        
        try:
            # Load base configuration
            config_data = self._load_base_config()
            
            # Apply environment overrides
            config_data = self._apply_environment_overrides(config_data)
            
            # Apply runtime overrides
            config_data = self._apply_runtime_overrides(config_data)
            
            # Validate configuration
            is_valid, errors = self.validator.validate(config_data)
            if not is_valid:
                self.logger.warning(f"Configuration validation errors: {errors}")
                # Continue with warnings, don't fail completely
            
            # Migrate if needed
            config_data = self.migrator.migrate(config_data, target_version=2)
            
            # Convert to schema object
            config_schema = self._dict_to_schema(config_data)
            
            # Update cache
            self._config_cache = config_schema
            self._cache_timestamp = datetime.now()
            
            self.logger.info("Configuration loaded successfully")
            return config_schema
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            # Return default configuration as fallback
            return self._get_default_configuration()
    
    def save_configuration(self, config: ConfigurationSchema) -> bool:
        """Save configuration to file."""
        try:
            config_data = asdict(config)
            config_data["last_updated"] = datetime.now().isoformat()
            
            # Validate before saving
            is_valid, errors = self.validator.validate(config_data)
            if not is_valid:
                self.logger.error(f"Cannot save invalid configuration: {errors}")
                return False
            
            # Save to file
            config_file = self.config_dir / f"team_config_{self.environment}.yaml"
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
            # Update cache
            self._config_cache = config
            self._cache_timestamp = datetime.now()
            
            # Notify listeners
            self._notify_change_listeners(config)
            
            self.logger.info(f"Configuration saved to {config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def update_team_settings(self, team_settings: TeamSettings) -> bool:
        """Update team settings."""
        config = self.load_configuration()
        config.team_settings = team_settings
        return self.save_configuration(config)
    
    def update_channel_override(self, channel_id: str, channel_config: ChannelSpecificFormatting) -> bool:
        """Update channel-specific configuration."""
        config = self.load_configuration()
        config.channel_overrides[channel_id] = channel_config
        return self.save_configuration(config)
    
    def update_user_preferences(self, user_id: str, preferences: UserPersonalPreferences) -> bool:
        """Update user personal preferences."""
        config = self.load_configuration()
        config.user_preferences[user_id] = preferences
        return self.save_configuration(config)
    
    def update_template_config(self, template_type: str, template_config: MessageTemplateConfig) -> bool:
        """Update message template configuration."""
        config = self.load_configuration()
        config.message_templates[template_type] = template_config
        return self.save_configuration(config)
    
    def get_effective_config(self, 
                           channel_id: Optional[str] = None, 
                           user_id: Optional[str] = None,
                           template_type: Optional[str] = None) -> Dict[str, Any]:
        """Get effective configuration with all overrides applied."""
        config = self.load_configuration()
        
        # Start with team settings
        effective_config = {
            "team_settings": asdict(config.team_settings),
            "visual_styling": asdict(config.team_settings.visual_styling),
            "content_preferences": asdict(config.team_settings.content_preferences),
            "interactive_settings": asdict(config.team_settings.interactive_settings)
        }
        
        # Apply channel overrides
        if channel_id and channel_id in config.channel_overrides:
            channel_override = asdict(config.channel_overrides[channel_id])
            effective_config["channel_override"] = channel_override
            
            # Merge specific overrides
            for key, value in channel_override.items():
                if value is not None and key != "channel_id":
                    effective_config[key] = value
        
        # Apply user preferences
        if user_id and user_id in config.user_preferences:
            user_prefs = asdict(config.user_preferences[user_id])
            effective_config["user_preferences"] = user_prefs
            
            # Apply user-specific overrides
            if "preferred_density" in user_prefs:
                effective_config["message_density"] = user_prefs["preferred_density"]
        
        # Apply template-specific config
        if template_type and template_type in config.message_templates:
            template_config = asdict(config.message_templates[template_type])
            effective_config["template_config"] = template_config
        
        return effective_config
    
    def add_change_listener(self, listener: Callable[[ConfigurationSchema], None]):
        """Add configuration change listener."""
        self._change_listeners.append(listener)
    
    def remove_change_listener(self, listener: Callable[[ConfigurationSchema], None]):
        """Remove configuration change listener."""
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)
    
    def _load_base_config(self) -> Dict[str, Any]:
        """Load base configuration from file."""
        config_files = [
            self.config_dir / f"team_config_{self.environment}.yaml",
            self.config_dir / f"team_config_{self.environment}.json",
            self.config_dir / "team_config.yaml",
            self.config_dir / "team_config.json"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                return self._load_config_file(config_file)
        
        # No config file found, return default
        self.logger.warning("No configuration file found, using defaults")
        return self._get_default_config_dict()
    
    def _load_config_file(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration from specific file."""
        try:
            with open(config_file, 'r') as f:
                if config_file.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"Failed to load config file {config_file}: {e}")
            return {}
    
    def _apply_environment_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment-specific overrides."""
        env_overrides = {}
        
        # Load from environment variables
        env_prefix = "DEVSYNC_"
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                config_key = key[len(env_prefix):].lower()
                env_overrides[config_key] = self._parse_env_value(value)
        
        # Apply overrides
        if env_overrides:
            config_data = self._deep_merge(config_data, env_overrides)
            self.logger.info(f"Applied {len(env_overrides)} environment overrides")
        
        return config_data
    
    def _apply_runtime_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply runtime configuration overrides."""
        # This could be extended to support runtime configuration updates
        # from admin interfaces, feature flags, etc.
        return config_data
    
    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type."""
        # Try to parse as JSON first
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        
        # Try boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _dict_to_schema(self, config_data: Dict[str, Any]) -> ConfigurationSchema:
        """Convert dictionary to configuration schema object."""
        # This is a simplified conversion - in production you'd want more robust handling
        try:
            # Handle nested objects
            team_settings_data = config_data.get("team_settings", {})
            
            # Create visual styling
            visual_data = team_settings_data.get("visual_styling", {})
            visual_styling = VisualStyling(
                brand_color=visual_data.get("brand_color", "#1f77b4"),
                emoji_style=EmojiStyle(visual_data.get("emoji_style", "standard")),
                message_density=MessageDensity(visual_data.get("message_density", "detailed")),
                **{k: v for k, v in visual_data.items() if k not in ["brand_color", "emoji_style", "message_density"]}
            )
            
            # Create team settings
            team_settings = TeamSettings(
                team_id=team_settings_data.get("team_id", "default"),
                team_name=team_settings_data.get("team_name", "Default Team"),
                visual_styling=visual_styling
            )
            
            # Create configuration schema
            return ConfigurationSchema(
                version=config_data.get("version", "1.0.0"),
                team_settings=team_settings,
                environment=config_data.get("environment", self.environment),
                migration_version=config_data.get("migration_version", 1)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert config to schema: {e}")
            return self._get_default_configuration()
    
    def _get_default_configuration(self) -> ConfigurationSchema:
        """Get default configuration."""
        return ConfigurationSchema(
            team_settings=TeamSettings(
                team_id="default",
                team_name="Default Team"
            )
        )
    
    def _get_default_config_dict(self) -> Dict[str, Any]:
        """Get default configuration as dictionary."""
        return asdict(self._get_default_configuration())
    
    def _is_cache_valid(self) -> bool:
        """Check if configuration cache is valid."""
        if not self._config_cache or not self._cache_timestamp:
            return False
        
        age = (datetime.now() - self._cache_timestamp).total_seconds()
        return age < self._cache_ttl
    
    def _notify_change_listeners(self, config: ConfigurationSchema):
        """Notify all change listeners."""
        for listener in self._change_listeners:
            try:
                listener(config)
            except Exception as e:
                self.logger.error(f"Error in change listener: {e}")


# Global configuration manager instance
default_config_manager = FlexibleConfigurationManager()