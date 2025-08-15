"""Template configuration validation utilities."""

import re
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from .template_config_manager import (
    TemplateType, 
    TemplateCustomization, 
    BrandingConfig, 
    EmojiSetConfig
)


class ValidationSeverity(Enum):
    """Validation message severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationMessage:
    """Validation message with context."""
    severity: ValidationSeverity
    message: str
    field_path: str
    suggested_fix: Optional[str] = None
    error_code: Optional[str] = None


class TemplateConfigValidator:
    """Comprehensive template configuration validator."""
    
    def __init__(self):
        """Initialize validator."""
        self.logger = logging.getLogger(__name__)
        
        # Validation rules
        self._color_pattern = re.compile(r'^#[0-9a-fA-F]{6}$')
        self._emoji_pattern = re.compile(r'^:[a-zA-Z0-9_+-]+:$|^[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\u2600-\u26FF\u2700-\u27BF]+$')
        
        # Known emoji keys for validation
        self._known_emoji_keys = {
            "success", "warning", "error", "info", "pending", "blocked",
            "healthy", "degraded", "critical", "unknown",
            "pr_new", "pr_review", "pr_approved", "pr_merged", "pr_conflict", "pr_closed",
            "ticket_open", "ticket_progress", "ticket_done", "ticket_blocked",
            "priority_high", "priority_medium", "priority_low",
            "alert_critical", "alert_warning", "alert_info",
            "build_failed", "deployment_issue", "security_alert",
            "team", "user", "time", "link", "action"
        }
        
        # Template-specific required fields
        self._template_required_fields = {
            TemplateType.STANDUP: ["show_team_health", "show_progress_bars"],
            TemplateType.PR_UPDATE: ["show_diff_stats", "show_ci_status"],
            TemplateType.JIRA_UPDATE: ["show_story_points", "show_epic_link"],
            TemplateType.ALERT: ["escalation_enabled", "show_severity"]
        }
    
    def validate_template_config(self, template_type: TemplateType,
                               customization: TemplateCustomization) -> List[ValidationMessage]:
        """Validate complete template configuration."""
        messages = []
        
        try:
            # Basic validation
            messages.extend(self._validate_basic_fields(customization))
            
            # Color scheme validation
            messages.extend(self._validate_color_scheme(customization.color_scheme))
            
            # Emoji validation
            messages.extend(self._validate_emoji_overrides(customization.emoji_overrides))
            
            # Visual indicators validation
            messages.extend(self._validate_visual_indicators(customization.visual_indicators))
            
            # Template-specific validation
            messages.extend(self._validate_template_specific(template_type, customization))
            
            # Custom fields validation
            messages.extend(self._validate_custom_fields(template_type, customization.custom_fields))
            
            self.logger.debug(f"Validated {template_type.value} config: {len(messages)} messages")
            
        except Exception as e:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                message=f"Validation failed: {str(e)}",
                field_path="root",
                error_code="VALIDATION_EXCEPTION"
            ))
        
        return messages
    
    def validate_branding_config(self, branding: BrandingConfig) -> List[ValidationMessage]:
        """Validate branding configuration."""
        messages = []
        
        try:
            # Team name validation
            if not branding.team_name or not branding.team_name.strip():
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message="Team name cannot be empty",
                    field_path="team_name",
                    suggested_fix="Provide a valid team name",
                    error_code="EMPTY_TEAM_NAME"
                ))
            elif len(branding.team_name) > 100:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    message="Team name is very long and may be truncated",
                    field_path="team_name",
                    suggested_fix="Consider shortening the team name"
                ))
            
            # Color validation
            color_fields = [
                ("primary_color", branding.primary_color),
                ("secondary_color", branding.secondary_color),
                ("success_color", branding.success_color),
                ("warning_color", branding.warning_color),
                ("error_color", branding.error_color)
            ]
            
            for field_name, color_value in color_fields:
                if not self._is_valid_color(color_value):
                    messages.append(ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid color format: {color_value}",
                        field_path=field_name,
                        suggested_fix="Use hex format like #1f77b4",
                        error_code="INVALID_COLOR_FORMAT"
                    ))
            
            # Logo emoji validation
            if branding.logo_emoji and not self._is_valid_emoji(branding.logo_emoji):
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    message=f"Logo emoji may not be valid: {branding.logo_emoji}",
                    field_path="logo_emoji",
                    suggested_fix="Use standard Slack emoji format like :gear:"
                ))
            
            # Header style validation
            valid_header_styles = ["standard", "minimal", "branded"]
            if branding.header_style not in valid_header_styles:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid header style: {branding.header_style}",
                    field_path="header_style",
                    suggested_fix=f"Use one of: {', '.join(valid_header_styles)}",
                    error_code="INVALID_HEADER_STYLE"
                ))
            
        except Exception as e:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                message=f"Branding validation failed: {str(e)}",
                field_path="root",
                error_code="BRANDING_VALIDATION_EXCEPTION"
            ))
        
        return messages
    
    def validate_emoji_config(self, emoji_config: EmojiSetConfig) -> List[ValidationMessage]:
        """Validate emoji configuration."""
        messages = []
        
        try:
            # Custom mappings validation
            for emoji_key, emoji_value in emoji_config.custom_mappings.items():
                # Check if key is known
                if emoji_key not in self._known_emoji_keys:
                    messages.append(ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        message=f"Unknown emoji key: {emoji_key}",
                        field_path=f"custom_mappings.{emoji_key}",
                        suggested_fix="Check if this is a custom key or typo"
                    ))
                
                # Check if emoji value is valid
                if not self._is_valid_emoji(emoji_value):
                    messages.append(ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        message=f"Emoji value may not be valid: {emoji_value}",
                        field_path=f"custom_mappings.{emoji_key}",
                        suggested_fix="Use standard emoji or Slack emoji format"
                    ))
            
            # Check for missing critical emojis
            critical_emojis = ["success", "error", "warning", "healthy", "critical"]
            for critical_emoji in critical_emojis:
                if (critical_emoji not in emoji_config.custom_mappings and 
                    emoji_config.style == emoji_config.style.CUSTOM):
                    messages.append(ValidationMessage(
                        severity=ValidationSeverity.INFO,
                        message=f"Consider defining custom emoji for: {critical_emoji}",
                        field_path=f"custom_mappings.{critical_emoji}",
                        suggested_fix="Add custom mapping for better consistency"
                    ))
            
        except Exception as e:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                message=f"Emoji validation failed: {str(e)}",
                field_path="root",
                error_code="EMOJI_VALIDATION_EXCEPTION"
            ))
        
        return messages
    
    def validate_yaml_config_file(self, config_path: str) -> List[ValidationMessage]:
        """Validate YAML configuration file."""
        messages = []
        
        try:
            import yaml
            from pathlib import Path
            
            config_file = Path(config_path)
            
            # Check if file exists
            if not config_file.exists():
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"Configuration file not found: {config_path}",
                    field_path="file",
                    error_code="FILE_NOT_FOUND"
                ))
                return messages
            
            # Check file permissions
            if not config_file.is_file():
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"Path is not a file: {config_path}",
                    field_path="file",
                    error_code="NOT_A_FILE"
                ))
                return messages
            
            # Try to parse YAML
            try:
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                
                if config_data is None:
                    messages.append(ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        message="Configuration file is empty",
                        field_path="file",
                        suggested_fix="Add configuration content"
                    ))
                    return messages
                
                # Validate structure
                messages.extend(self._validate_config_structure(config_data))
                
            except yaml.YAMLError as e:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid YAML syntax: {str(e)}",
                    field_path="file",
                    suggested_fix="Fix YAML syntax errors",
                    error_code="INVALID_YAML"
                ))
            
        except Exception as e:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                message=f"File validation failed: {str(e)}",
                field_path="file",
                error_code="FILE_VALIDATION_EXCEPTION"
            ))
        
        return messages
    
    def get_validation_summary(self, messages: List[ValidationMessage]) -> Dict[str, Any]:
        """Get validation summary statistics."""
        summary = {
            "total_messages": len(messages),
            "errors": len([m for m in messages if m.severity == ValidationSeverity.ERROR]),
            "warnings": len([m for m in messages if m.severity == ValidationSeverity.WARNING]),
            "info": len([m for m in messages if m.severity == ValidationSeverity.INFO]),
            "is_valid": len([m for m in messages if m.severity == ValidationSeverity.ERROR]) == 0,
            "error_codes": list(set([m.error_code for m in messages if m.error_code])),
            "affected_fields": list(set([m.field_path for m in messages]))
        }
        
        return summary
    
    def _validate_basic_fields(self, customization: TemplateCustomization) -> List[ValidationMessage]:
        """Validate basic template fields."""
        messages = []
        
        # Template type validation
        if not isinstance(customization.template_type, TemplateType):
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                message="Invalid template type",
                field_path="template_type",
                error_code="INVALID_TEMPLATE_TYPE"
            ))
        
        # Enabled field validation
        if not isinstance(customization.enabled, bool):
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                message="Enabled field must be boolean",
                field_path="enabled",
                error_code="INVALID_ENABLED_TYPE"
            ))
        
        # Interactive elements validation
        if not isinstance(customization.interactive_elements, bool):
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                message="Interactive elements field must be boolean",
                field_path="interactive_elements",
                error_code="INVALID_INTERACTIVE_TYPE"
            ))
        
        # Accessibility mode validation
        if not isinstance(customization.accessibility_mode, bool):
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                message="Accessibility mode field must be boolean",
                field_path="accessibility_mode",
                error_code="INVALID_ACCESSIBILITY_TYPE"
            ))
        
        return messages
    
    def _validate_color_scheme(self, color_scheme: Dict[str, str]) -> List[ValidationMessage]:
        """Validate color scheme configuration."""
        messages = []
        
        for color_key, color_value in color_scheme.items():
            if not self._is_valid_color(color_value):
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid color format: {color_value}",
                    field_path=f"color_scheme.{color_key}",
                    suggested_fix="Use hex format like #1f77b4",
                    error_code="INVALID_COLOR_FORMAT"
                ))
        
        return messages
    
    def _validate_emoji_overrides(self, emoji_overrides: Dict[str, str]) -> List[ValidationMessage]:
        """Validate emoji overrides."""
        messages = []
        
        for emoji_key, emoji_value in emoji_overrides.items():
            # Check if key is known
            if emoji_key not in self._known_emoji_keys:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    message=f"Unknown emoji key: {emoji_key}",
                    field_path=f"emoji_overrides.{emoji_key}",
                    suggested_fix="Check if this is a custom key or typo"
                ))
            
            # Check if emoji value is valid
            if not self._is_valid_emoji(emoji_value):
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    message=f"Emoji value may not be valid: {emoji_value}",
                    field_path=f"emoji_overrides.{emoji_key}",
                    suggested_fix="Use standard emoji or Slack emoji format"
                ))
        
        return messages
    
    def _validate_visual_indicators(self, visual_indicators: Dict[str, str]) -> List[ValidationMessage]:
        """Validate visual indicators."""
        messages = []
        
        for indicator_key, indicator_value in visual_indicators.items():
            # Check if indicator value is reasonable
            if len(indicator_value) > 10:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    message=f"Visual indicator is very long: {indicator_value}",
                    field_path=f"visual_indicators.{indicator_key}",
                    suggested_fix="Consider using shorter indicators"
                ))
        
        return messages
    
    def _validate_template_specific(self, template_type: TemplateType,
                                  customization: TemplateCustomization) -> List[ValidationMessage]:
        """Validate template-specific requirements."""
        messages = []
        
        # Check for required fields based on template type
        required_fields = self._template_required_fields.get(template_type, [])
        
        for required_field in required_fields:
            if required_field not in customization.custom_fields:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.INFO,
                    message=f"Consider adding {required_field} for {template_type.value} template",
                    field_path=f"custom_fields.{required_field}",
                    suggested_fix=f"Add {required_field} configuration"
                ))
        
        return messages
    
    def _validate_custom_fields(self, template_type: TemplateType,
                              custom_fields: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate custom fields based on template type."""
        messages = []
        
        # Template-specific custom field validation
        if template_type == TemplateType.STANDUP:
            messages.extend(self._validate_standup_custom_fields(custom_fields))
        elif template_type == TemplateType.PR_UPDATE:
            messages.extend(self._validate_pr_custom_fields(custom_fields))
        elif template_type == TemplateType.JIRA_UPDATE:
            messages.extend(self._validate_jira_custom_fields(custom_fields))
        elif template_type == TemplateType.ALERT:
            messages.extend(self._validate_alert_custom_fields(custom_fields))
        
        return messages
    
    def _validate_standup_custom_fields(self, custom_fields: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate standup-specific custom fields."""
        messages = []
        
        boolean_fields = ["show_team_health", "show_progress_bars", "show_velocity", "show_burndown"]
        
        for field in boolean_fields:
            if field in custom_fields and not isinstance(custom_fields[field], bool):
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"{field} must be boolean",
                    field_path=f"custom_fields.{field}",
                    error_code="INVALID_BOOLEAN_FIELD"
                ))
        
        return messages
    
    def _validate_pr_custom_fields(self, custom_fields: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate PR-specific custom fields."""
        messages = []
        
        boolean_fields = ["show_diff_stats", "show_ci_status", "highlight_conflicts", "show_deployment_status"]
        
        for field in boolean_fields:
            if field in custom_fields and not isinstance(custom_fields[field], bool):
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"{field} must be boolean",
                    field_path=f"custom_fields.{field}",
                    error_code="INVALID_BOOLEAN_FIELD"
                ))
        
        return messages
    
    def _validate_jira_custom_fields(self, custom_fields: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate JIRA-specific custom fields."""
        messages = []
        
        boolean_fields = ["show_story_points", "show_epic_link", "show_sprint_info", "highlight_blockers"]
        
        for field in boolean_fields:
            if field in custom_fields and not isinstance(custom_fields[field], bool):
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"{field} must be boolean",
                    field_path=f"custom_fields.{field}",
                    error_code="INVALID_BOOLEAN_FIELD"
                ))
        
        return messages
    
    def _validate_alert_custom_fields(self, custom_fields: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate alert-specific custom fields."""
        messages = []
        
        boolean_fields = ["escalation_enabled", "show_severity", "show_affected_systems", "include_metrics"]
        
        for field in boolean_fields:
            if field in custom_fields and not isinstance(custom_fields[field], bool):
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"{field} must be boolean",
                    field_path=f"custom_fields.{field}",
                    error_code="INVALID_BOOLEAN_FIELD"
                ))
        
        return messages
    
    def _validate_config_structure(self, config_data: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate overall configuration structure."""
        messages = []
        
        # Check for required top-level fields
        required_fields = ["version", "team_settings"]
        
        for field in required_fields:
            if field not in config_data:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    message=f"Missing required field: {field}",
                    field_path=field,
                    error_code="MISSING_REQUIRED_FIELD"
                ))
        
        # Validate version format
        if "version" in config_data:
            version = config_data["version"]
            if not isinstance(version, str) or not re.match(r'^\d+\.\d+\.\d+$', version):
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    message=f"Version format should be semantic (x.y.z): {version}",
                    field_path="version",
                    suggested_fix="Use semantic versioning format"
                ))
        
        return messages
    
    def _is_valid_color(self, color: str) -> bool:
        """Check if color is valid hex format."""
        return bool(self._color_pattern.match(color))
    
    def _is_valid_emoji(self, emoji: str) -> bool:
        """Check if emoji is in valid format."""
        return bool(self._emoji_pattern.match(emoji))


# Utility functions for validation
def validate_template_configuration(template_type: TemplateType,
                                  customization: TemplateCustomization) -> Tuple[bool, List[ValidationMessage]]:
    """Validate template configuration and return results."""
    validator = TemplateConfigValidator()
    messages = validator.validate_template_config(template_type, customization)
    
    # Check if there are any errors
    has_errors = any(msg.severity == ValidationSeverity.ERROR for msg in messages)
    
    return not has_errors, messages


def validate_branding_configuration(branding: BrandingConfig) -> Tuple[bool, List[ValidationMessage]]:
    """Validate branding configuration and return results."""
    validator = TemplateConfigValidator()
    messages = validator.validate_branding_config(branding)
    
    # Check if there are any errors
    has_errors = any(msg.severity == ValidationSeverity.ERROR for msg in messages)
    
    return not has_errors, messages


def validate_config_file(config_path: str) -> Tuple[bool, List[ValidationMessage]]:
    """Validate configuration file and return results."""
    validator = TemplateConfigValidator()
    messages = validator.validate_yaml_config_file(config_path)
    
    # Check if there are any errors
    has_errors = any(msg.severity == ValidationSeverity.ERROR for msg in messages)
    
    return not has_errors, messages