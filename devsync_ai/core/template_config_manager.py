"""Template-specific configuration management utilities."""

import os
import yaml
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
from copy import deepcopy

from .config_manager import (
    FlexibleConfigurationManager, 
    ConfigurationSchema,
    TeamSettings,
    VisualStyling,
    MessageTemplateConfig,
    EmojiStyle,
    MessageDensity,
    FormattingStyle
)


class TemplateType(Enum):
    """Supported template types."""
    STANDUP = "standup"
    PR_UPDATE = "pr_update"
    JIRA_UPDATE = "jira_update"
    ALERT = "alert"
    DEPLOYMENT = "deployment"


@dataclass
class TemplateCustomization:
    """Template customization settings."""
    template_type: TemplateType
    enabled: bool = True
    color_scheme: Dict[str, str] = field(default_factory=dict)
    emoji_overrides: Dict[str, str] = field(default_factory=dict)
    visual_indicators: Dict[str, str] = field(default_factory=dict)
    interactive_elements: bool = True
    accessibility_mode: bool = False
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrandingConfig:
    """Team branding configuration."""
    team_name: str
    logo_emoji: str = ":gear:"
    primary_color: str = "#1f77b4"
    secondary_color: str = "#ff7f0e"
    success_color: str = "#2ca02c"
    warning_color: str = "#ff7f0e"
    error_color: str = "#d62728"
    footer_text: Optional[str] = None
    header_style: str = "standard"  # standard, minimal, branded


@dataclass
class EmojiSetConfig:
    """Emoji set configuration."""
    style: EmojiStyle = EmojiStyle.STANDARD
    custom_mappings: Dict[str, str] = field(default_factory=dict)
    fallback_enabled: bool = True
    
    def get_default_emoji_set(self) -> Dict[str, str]:
        """Get default emoji mappings."""
        return {
            # Status indicators
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "info": "ℹ️",
            "pending": "⏳",
            "blocked": "🚫",
            
            # Health indicators
            "healthy": "🟢",
            "degraded": "🟡",
            "critical": "🔴",
            "unknown": "⚪",
            
            # PR status
            "pr_new": "🆕",
            "pr_review": "👀",
            "pr_approved": "✅",
            "pr_merged": "🎉",
            "pr_conflict": "⚠️",
            "pr_closed": "❌",
            
            # JIRA status
            "ticket_open": "📋",
            "ticket_progress": "🔄",
            "ticket_done": "✅",
            "ticket_blocked": "🚫",
            "priority_high": "🔴",
            "priority_medium": "🟡",
            "priority_low": "🟢",
            
            # Alerts
            "alert_critical": "🚨",
            "alert_warning": "⚠️",
            "alert_info": "ℹ️",
            "build_failed": "💥",
            "deployment_issue": "🚀",
            "security_alert": "🔒",
            
            # General
            "team": "👥",
            "user": "👤",
            "time": "🕐",
            "link": "🔗",
            "action": "⚡"
        }
    
    def get_emoji(self, key: str) -> str:
        """Get emoji for a specific key."""
        # Check custom mappings first
        if key in self.custom_mappings:
            return self.custom_mappings[key]
        
        # Use default mappings
        default_set = self.get_default_emoji_set()
        if key in default_set:
            if self.style == EmojiStyle.NONE:
                return ""
            elif self.style == EmojiStyle.MINIMAL:
                # Return simplified versions for minimal style
                minimal_map = {
                    "success": "✓", "error": "✗", "warning": "!",
                    "healthy": "●", "degraded": "●", "critical": "●"
                }
                return minimal_map.get(key, default_set[key])
            else:
                return default_set[key]
        
        # Fallback
        return "●" if self.fallback_enabled else ""


class TemplateConfigurationManager:
    """Template-specific configuration management."""
    
    def __init__(self, base_config_manager: Optional[FlexibleConfigurationManager] = None):
        """Initialize template configuration manager."""
        self.base_config_manager = base_config_manager or FlexibleConfigurationManager()
        self.logger = logging.getLogger(__name__)
        
        # Template-specific cache
        self._template_configs: Dict[str, TemplateCustomization] = {}
        self._branding_config: Optional[BrandingConfig] = None
        self._emoji_config: Optional[EmojiSetConfig] = None
        
        self.logger.info("TemplateConfigurationManager initialized")
    
    def load_template_config(self, template_type: TemplateType, 
                           team_id: Optional[str] = None,
                           force_reload: bool = False) -> TemplateCustomization:
        """Load configuration for a specific template type."""
        cache_key = f"{template_type.value}_{team_id or 'default'}"
        
        if not force_reload and cache_key in self._template_configs:
            return self._template_configs[cache_key]
        
        try:
            # Load base configuration
            base_config = self.base_config_manager.load_configuration(force_reload)
            
            # Get template-specific config
            template_config_data = base_config.message_templates.get(
                template_type.value, 
                MessageTemplateConfig(template_type=template_type.value)
            )
            
            # Create template customization
            customization = self._create_template_customization(
                template_type, 
                template_config_data, 
                base_config
            )
            
            # Cache the result
            self._template_configs[cache_key] = customization
            
            self.logger.debug(f"Loaded template config for {template_type.value}")
            return customization
            
        except Exception as e:
            self.logger.error(f"Failed to load template config for {template_type.value}: {e}")
            return self._get_default_template_config(template_type)
    
    def get_branding_config(self, team_id: Optional[str] = None, 
                          force_reload: bool = False) -> BrandingConfig:
        """Get team branding configuration."""
        if not force_reload and self._branding_config:
            return self._branding_config
        
        try:
            base_config = self.base_config_manager.load_configuration(force_reload)
            team_settings = base_config.team_settings
            visual_styling = team_settings.visual_styling
            
            branding = BrandingConfig(
                team_name=team_settings.team_name,
                primary_color=visual_styling.brand_color,
                secondary_color=visual_styling.secondary_color,
                success_color=visual_styling.success_color,
                warning_color=visual_styling.warning_color,
                error_color=visual_styling.error_color,
                logo_emoji=team_settings.custom_fields.get("logo_emoji", ":gear:"),
                footer_text=team_settings.custom_fields.get("footer_text"),
                header_style=team_settings.custom_fields.get("header_style", "standard")
            )
            
            self._branding_config = branding
            return branding
            
        except Exception as e:
            self.logger.error(f"Failed to load branding config: {e}")
            return BrandingConfig(team_name="DevSync AI")
    
    def get_emoji_config(self, team_id: Optional[str] = None,
                        force_reload: bool = False) -> EmojiSetConfig:
        """Get emoji set configuration."""
        if not force_reload and self._emoji_config:
            return self._emoji_config
        
        try:
            base_config = self.base_config_manager.load_configuration(force_reload)
            visual_styling = base_config.team_settings.visual_styling
            
            emoji_config = EmojiSetConfig(
                style=visual_styling.emoji_style,
                custom_mappings=visual_styling.custom_emojis,
                fallback_enabled=True
            )
            
            self._emoji_config = emoji_config
            return emoji_config
            
        except Exception as e:
            self.logger.error(f"Failed to load emoji config: {e}")
            return EmojiSetConfig()
    
    def update_template_config(self, template_type: TemplateType,
                             customization: TemplateCustomization,
                             team_id: Optional[str] = None) -> bool:
        """Update template configuration."""
        try:
            # Convert to MessageTemplateConfig
            template_config = MessageTemplateConfig(
                template_type=template_type.value,
                enabled=customization.enabled,
                custom_fields={
                    "color_scheme": customization.color_scheme,
                    "emoji_overrides": customization.emoji_overrides,
                    "visual_indicators": customization.visual_indicators,
                    "interactive_elements": customization.interactive_elements,
                    "accessibility_mode": customization.accessibility_mode,
                    **customization.custom_fields
                }
            )
            
            # Update base configuration
            success = self.base_config_manager.update_template_config(
                template_type.value, 
                template_config
            )
            
            if success:
                # Update cache
                cache_key = f"{template_type.value}_{team_id or 'default'}"
                self._template_configs[cache_key] = customization
                self.logger.info(f"Updated template config for {template_type.value}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update template config: {e}")
            return False
    
    def update_branding_config(self, branding: BrandingConfig,
                             team_id: Optional[str] = None) -> bool:
        """Update branding configuration."""
        try:
            base_config = self.base_config_manager.load_configuration()
            
            # Update team settings
            team_settings = base_config.team_settings
            team_settings.team_name = branding.team_name
            
            # Update visual styling
            visual_styling = team_settings.visual_styling
            visual_styling.brand_color = branding.primary_color
            visual_styling.secondary_color = branding.secondary_color
            visual_styling.success_color = branding.success_color
            visual_styling.warning_color = branding.warning_color
            visual_styling.error_color = branding.error_color
            
            # Update custom fields
            team_settings.custom_fields.update({
                "logo_emoji": branding.logo_emoji,
                "footer_text": branding.footer_text,
                "header_style": branding.header_style
            })
            
            # Save configuration
            success = self.base_config_manager.update_team_settings(team_settings)
            
            if success:
                self._branding_config = branding
                self.logger.info("Updated branding configuration")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update branding config: {e}")
            return False
    
    def update_emoji_config(self, emoji_config: EmojiSetConfig,
                          team_id: Optional[str] = None) -> bool:
        """Update emoji configuration."""
        try:
            base_config = self.base_config_manager.load_configuration()
            
            # Update visual styling
            visual_styling = base_config.team_settings.visual_styling
            visual_styling.emoji_style = emoji_config.style
            visual_styling.custom_emojis = emoji_config.custom_mappings
            
            # Save configuration
            success = self.base_config_manager.update_team_settings(base_config.team_settings)
            
            if success:
                self._emoji_config = emoji_config
                self.logger.info("Updated emoji configuration")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update emoji config: {e}")
            return False
    
    def validate_template_config(self, template_type: TemplateType,
                               customization: TemplateCustomization) -> tuple[bool, List[str]]:
        """Validate template configuration."""
        errors = []
        
        try:
            # Validate color scheme
            for color_key, color_value in customization.color_scheme.items():
                if not self._is_valid_color(color_value):
                    errors.append(f"Invalid color format for {color_key}: {color_value}")
            
            # Validate emoji overrides
            emoji_config = self.get_emoji_config()
            default_emojis = emoji_config.get_default_emoji_set()
            
            for emoji_key in customization.emoji_overrides:
                if emoji_key not in default_emojis:
                    errors.append(f"Unknown emoji key: {emoji_key}")
            
            # Template-specific validations
            if template_type == TemplateType.STANDUP:
                errors.extend(self._validate_standup_config(customization))
            elif template_type == TemplateType.PR_UPDATE:
                errors.extend(self._validate_pr_config(customization))
            elif template_type == TemplateType.JIRA_UPDATE:
                errors.extend(self._validate_jira_config(customization))
            elif template_type == TemplateType.ALERT:
                errors.extend(self._validate_alert_config(customization))
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return False, errors
    
    def get_effective_template_config(self, template_type: TemplateType,
                                    channel_id: Optional[str] = None,
                                    user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get effective template configuration with all overrides applied."""
        # Load base template config
        template_config = self.load_template_config(template_type)
        
        # Get effective base config
        effective_config = self.base_config_manager.get_effective_config(
            channel_id=channel_id,
            user_id=user_id,
            template_type=template_type.value
        )
        
        # Merge template-specific settings
        effective_config.update({
            "template_type": template_type.value,
            "template_enabled": template_config.enabled,
            "color_scheme": template_config.color_scheme,
            "emoji_overrides": template_config.emoji_overrides,
            "visual_indicators": template_config.visual_indicators,
            "interactive_elements": template_config.interactive_elements,
            "accessibility_mode": template_config.accessibility_mode,
            "custom_fields": template_config.custom_fields
        })
        
        # Add branding and emoji configs
        effective_config["branding"] = asdict(self.get_branding_config())
        effective_config["emoji_config"] = asdict(self.get_emoji_config())
        
        return effective_config
    
    def clear_cache(self):
        """Clear configuration cache."""
        self._template_configs.clear()
        self._branding_config = None
        self._emoji_config = None
        self.logger.info("Template configuration cache cleared")
    
    def _create_template_customization(self, template_type: TemplateType,
                                     template_config: MessageTemplateConfig,
                                     base_config: ConfigurationSchema) -> TemplateCustomization:
        """Create template customization from base config."""
        custom_fields = template_config.custom_fields
        
        return TemplateCustomization(
            template_type=template_type,
            enabled=template_config.enabled,
            color_scheme=custom_fields.get("color_scheme", {}),
            emoji_overrides=custom_fields.get("emoji_overrides", {}),
            visual_indicators=custom_fields.get("visual_indicators", {}),
            interactive_elements=custom_fields.get("interactive_elements", True),
            accessibility_mode=custom_fields.get("accessibility_mode", False),
            custom_fields={k: v for k, v in custom_fields.items() 
                         if k not in ["color_scheme", "emoji_overrides", "visual_indicators", 
                                    "interactive_elements", "accessibility_mode"]}
        )
    
    def _get_default_template_config(self, template_type: TemplateType) -> TemplateCustomization:
        """Get default template configuration."""
        return TemplateCustomization(template_type=template_type)
    
    def _is_valid_color(self, color: str) -> bool:
        """Check if color is valid hex format."""
        import re
        return bool(re.match(r'^#[0-9a-fA-F]{6}$', color))
    
    def _validate_standup_config(self, customization: TemplateCustomization) -> List[str]:
        """Validate standup-specific configuration."""
        errors = []
        
        # Check for required standup fields
        required_indicators = ["healthy", "degraded", "critical"]
        for indicator in required_indicators:
            if indicator not in customization.visual_indicators:
                # This is a warning, not an error
                pass
        
        return errors
    
    def _validate_pr_config(self, customization: TemplateCustomization) -> List[str]:
        """Validate PR-specific configuration."""
        errors = []
        
        # Check for PR-specific settings
        if "show_diff_stats" in customization.custom_fields:
            if not isinstance(customization.custom_fields["show_diff_stats"], bool):
                errors.append("show_diff_stats must be a boolean")
        
        return errors
    
    def _validate_jira_config(self, customization: TemplateCustomization) -> List[str]:
        """Validate JIRA-specific configuration."""
        errors = []
        
        # Check for JIRA-specific settings
        if "show_story_points" in customization.custom_fields:
            if not isinstance(customization.custom_fields["show_story_points"], bool):
                errors.append("show_story_points must be a boolean")
        
        return errors
    
    def _validate_alert_config(self, customization: TemplateCustomization) -> List[str]:
        """Validate alert-specific configuration."""
        errors = []
        
        # Check for alert-specific settings
        if "escalation_enabled" in customization.custom_fields:
            if not isinstance(customization.custom_fields["escalation_enabled"], bool):
                errors.append("escalation_enabled must be a boolean")
        
        return errors


# Utility functions for configuration loading
def load_team_template_config(team_id: str, template_type: TemplateType) -> TemplateCustomization:
    """Load template configuration for a specific team."""
    manager = TemplateConfigurationManager()
    return manager.load_template_config(template_type, team_id)


def get_team_branding(team_id: str) -> BrandingConfig:
    """Get branding configuration for a specific team."""
    manager = TemplateConfigurationManager()
    return manager.get_branding_config(team_id)


def get_team_emoji_config(team_id: str) -> EmojiSetConfig:
    """Get emoji configuration for a specific team."""
    manager = TemplateConfigurationManager()
    return manager.get_emoji_config(team_id)


# Global template configuration manager instance
default_template_config_manager = TemplateConfigurationManager()