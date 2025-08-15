"""Template fallback behavior handling for graceful degradation."""

import logging
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum

from .template_config_manager import (
    TemplateType,
    TemplateCustomization,
    BrandingConfig,
    EmojiSetConfig
)
from .template_customizer import (
    ColorSchemeConfig,
    VisualIndicatorConfig,
    AccessibilityConfig,
    InteractiveElementConfig
)


class FallbackLevel(Enum):
    """Fallback severity levels."""
    NONE = "none"           # No fallback, fail fast
    MINIMAL = "minimal"     # Basic fallbacks only
    GRACEFUL = "graceful"   # Comprehensive fallbacks
    SAFE_MODE = "safe_mode" # Maximum compatibility


@dataclass
class FallbackConfig:
    """Fallback behavior configuration."""
    level: FallbackLevel = FallbackLevel.GRACEFUL
    
    # Color fallbacks
    use_default_colors_on_error: bool = True
    fallback_to_monochrome: bool = False
    
    # Visual indicator fallbacks
    use_text_indicators_on_emoji_fail: bool = True
    fallback_to_ascii_only: bool = False
    
    # Interactive element fallbacks
    disable_interactions_on_error: bool = False
    fallback_to_plain_text: bool = False
    
    # Accessibility fallbacks
    always_include_alt_text: bool = True
    force_high_contrast_on_error: bool = False
    
    # Template fallbacks
    use_basic_template_on_error: bool = True
    fallback_template_type: Optional[TemplateType] = None


class TemplateFallbackHandler:
    """Handles template fallback behaviors and graceful degradation."""
    
    def __init__(self, fallback_config: Optional[FallbackConfig] = None):
        """Initialize fallback handler."""
        self.config = fallback_config or FallbackConfig()
        self.logger = logging.getLogger(__name__)
        
        # Default fallback values
        self._default_colors = self._get_default_colors()
        self._default_indicators = self._get_default_indicators()
        self._default_accessibility = self._get_default_accessibility()
        
        # Fallback strategies by level
        self._fallback_strategies = {
            FallbackLevel.NONE: self._no_fallback,
            FallbackLevel.MINIMAL: self._minimal_fallback,
            FallbackLevel.GRACEFUL: self._graceful_fallback,
            FallbackLevel.SAFE_MODE: self._safe_mode_fallback
        }
        
        self.logger.info(f"TemplateFallbackHandler initialized with level: {self.config.level.value}")
    
    def handle_customization_error(self, customization: TemplateCustomization,
                                 error: Exception,
                                 context: str = "") -> TemplateCustomization:
        """Handle customization errors with appropriate fallback."""
        try:
            self.logger.warning(f"Customization error in {context}: {str(error)}")
            
            # Apply fallback strategy based on configuration
            fallback_strategy = self._fallback_strategies[self.config.level]
            return fallback_strategy(customization, error, context)
            
        except Exception as fallback_error:
            self.logger.error(f"Fallback handling failed: {fallback_error}")
            return self._create_safe_customization(customization.template_type)
    
    def handle_color_scheme_error(self, customization: TemplateCustomization,
                                error: Exception) -> TemplateCustomization:
        """Handle color scheme errors."""
        try:
            self.logger.warning(f"Color scheme error: {str(error)}")
            
            if self.config.use_default_colors_on_error:
                customization.color_scheme = self._default_colors.copy()
                self.logger.info("Applied default color scheme as fallback")
            
            if self.config.fallback_to_monochrome:
                customization.color_scheme = self._get_monochrome_colors()
                self.logger.info("Applied monochrome color scheme as fallback")
            
            return customization
            
        except Exception as e:
            self.logger.error(f"Color scheme fallback failed: {e}")
            return customization
    
    def handle_visual_indicator_error(self, customization: TemplateCustomization,
                                    error: Exception) -> TemplateCustomization:
        """Handle visual indicator errors."""
        try:
            self.logger.warning(f"Visual indicator error: {str(error)}")
            
            if self.config.use_text_indicators_on_emoji_fail:
                customization.visual_indicators = self._get_text_indicators()
                self.logger.info("Applied text indicators as fallback")
            
            if self.config.fallback_to_ascii_only:
                customization.visual_indicators = self._get_ascii_indicators()
                self.logger.info("Applied ASCII-only indicators as fallback")
            
            return customization
            
        except Exception as e:
            self.logger.error(f"Visual indicator fallback failed: {e}")
            return customization
    
    def handle_interactive_element_error(self, customization: TemplateCustomization,
                                       error: Exception) -> TemplateCustomization:
        """Handle interactive element errors."""
        try:
            self.logger.warning(f"Interactive element error: {str(error)}")
            
            if self.config.disable_interactions_on_error:
                customization.interactive_elements = False
                if "interactive_config" in customization.custom_fields:
                    del customization.custom_fields["interactive_config"]
                self.logger.info("Disabled interactive elements as fallback")
            
            if self.config.fallback_to_plain_text:
                customization.interactive_elements = False
                customization.custom_fields["force_plain_text"] = True
                self.logger.info("Forced plain text mode as fallback")
            
            return customization
            
        except Exception as e:
            self.logger.error(f"Interactive element fallback failed: {e}")
            return customization
    
    def handle_accessibility_error(self, customization: TemplateCustomization,
                                 error: Exception) -> TemplateCustomization:
        """Handle accessibility configuration errors."""
        try:
            self.logger.warning(f"Accessibility error: {str(error)}")
            
            if self.config.always_include_alt_text:
                customization.accessibility_mode = True
                if "accessibility_config" not in customization.custom_fields:
                    customization.custom_fields["accessibility_config"] = self._default_accessibility
                self.logger.info("Enabled basic accessibility as fallback")
            
            if self.config.force_high_contrast_on_error:
                customization.color_scheme = self._get_high_contrast_colors()
                customization.visual_indicators = self._get_high_contrast_indicators()
                self.logger.info("Applied high contrast mode as fallback")
            
            return customization
            
        except Exception as e:
            self.logger.error(f"Accessibility fallback failed: {e}")
            return customization
    
    def handle_template_error(self, template_type: TemplateType,
                            error: Exception) -> TemplateCustomization:
        """Handle template-level errors."""
        try:
            self.logger.warning(f"Template error for {template_type.value}: {str(error)}")
            
            if self.config.use_basic_template_on_error:
                return self._create_basic_customization(template_type)
            
            if self.config.fallback_template_type:
                return self._create_basic_customization(self.config.fallback_template_type)
            
            return self._create_safe_customization(template_type)
            
        except Exception as e:
            self.logger.error(f"Template fallback failed: {e}")
            return self._create_safe_customization(template_type)
    
    def create_fallback_message(self, original_data: Dict[str, Any],
                              error: Exception,
                              template_type: TemplateType) -> Dict[str, Any]:
        """Create a fallback message when template processing fails."""
        try:
            fallback_message = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": self._create_fallback_text(original_data, template_type)
                }
            }
            
            # Add error context if in debug mode
            if self.logger.isEnabledFor(logging.DEBUG):
                fallback_message["accessory"] = {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Debug Info"
                    },
                    "value": f"error:{str(error)[:100]}"
                }
            
            self.logger.info(f"Created fallback message for {template_type.value}")
            return {"blocks": [fallback_message]}
            
        except Exception as e:
            self.logger.error(f"Fallback message creation failed: {e}")
            return {
                "text": f"DevSync AI notification (fallback mode)",
                "blocks": [{
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "A notification was generated but could not be formatted properly."
                    }
                }]
            }
    
    def _no_fallback(self, customization: TemplateCustomization,
                    error: Exception, context: str) -> TemplateCustomization:
        """No fallback strategy - re-raise the error."""
        raise error
    
    def _minimal_fallback(self, customization: TemplateCustomization,
                         error: Exception, context: str) -> TemplateCustomization:
        """Minimal fallback strategy."""
        # Only fix critical issues
        if not customization.color_scheme:
            customization.color_scheme = self._default_colors.copy()
        
        if not customization.visual_indicators:
            customization.visual_indicators = self._default_indicators.copy()
        
        return customization
    
    def _graceful_fallback(self, customization: TemplateCustomization,
                          error: Exception, context: str) -> TemplateCustomization:
        """Graceful fallback strategy."""
        # Apply comprehensive fallbacks
        customization = self.handle_color_scheme_error(customization, error)
        customization = self.handle_visual_indicator_error(customization, error)
        customization = self.handle_accessibility_error(customization, error)
        
        return customization
    
    def _safe_mode_fallback(self, customization: TemplateCustomization,
                           error: Exception, context: str) -> TemplateCustomization:
        """Safe mode fallback strategy."""
        # Maximum compatibility mode
        return self._create_safe_customization(customization.template_type)
    
    def _create_basic_customization(self, template_type: TemplateType) -> TemplateCustomization:
        """Create basic customization with minimal features."""
        return TemplateCustomization(
            template_type=template_type,
            enabled=True,
            color_scheme=self._default_colors.copy(),
            visual_indicators=self._default_indicators.copy(),
            interactive_elements=True,
            accessibility_mode=False,
            custom_fields={}
        )
    
    def _create_safe_customization(self, template_type: TemplateType) -> TemplateCustomization:
        """Create safe customization with maximum compatibility."""
        return TemplateCustomization(
            template_type=template_type,
            enabled=True,
            color_scheme=self._get_monochrome_colors(),
            visual_indicators=self._get_ascii_indicators(),
            interactive_elements=False,
            accessibility_mode=True,
            custom_fields={
                "force_plain_text": True,
                "accessibility_config": self._default_accessibility
            }
        )
    
    def _create_fallback_text(self, original_data: Dict[str, Any],
                            template_type: TemplateType) -> str:
        """Create fallback text representation."""
        try:
            # Extract key information based on template type
            if template_type == TemplateType.STANDUP:
                return self._create_standup_fallback_text(original_data)
            elif template_type == TemplateType.PR_UPDATE:
                return self._create_pr_fallback_text(original_data)
            elif template_type == TemplateType.JIRA_UPDATE:
                return self._create_jira_fallback_text(original_data)
            elif template_type == TemplateType.ALERT:
                return self._create_alert_fallback_text(original_data)
            else:
                return f"DevSync AI {template_type.value} notification"
                
        except Exception as e:
            self.logger.error(f"Fallback text creation failed: {e}")
            return "DevSync AI notification (simplified)"
    
    def _create_standup_fallback_text(self, data: Dict[str, Any]) -> str:
        """Create fallback text for standup updates."""
        team = data.get("team", "Team")
        date = data.get("date", "Today")
        return f"*{team} Daily Standup - {date}*\n\nStandup information available in simplified format."
    
    def _create_pr_fallback_text(self, data: Dict[str, Any]) -> str:
        """Create fallback text for PR updates."""
        pr_title = data.get("pr", {}).get("title", "Pull Request")
        action = data.get("action", "updated")
        return f"*PR {action.title()}*\n{pr_title}"
    
    def _create_jira_fallback_text(self, data: Dict[str, Any]) -> str:
        """Create fallback text for JIRA updates."""
        ticket_key = data.get("ticket", {}).get("key", "TICKET")
        summary = data.get("ticket", {}).get("summary", "Issue updated")
        return f"*{ticket_key}*\n{summary}"
    
    def _create_alert_fallback_text(self, data: Dict[str, Any]) -> str:
        """Create fallback text for alerts."""
        alert_type = data.get("alert", {}).get("type", "Alert")
        severity = data.get("severity", "unknown")
        return f"*{alert_type.title()} ({severity.upper()})*\n\nAlert details available."
    
    def _get_default_colors(self) -> Dict[str, str]:
        """Get default color scheme."""
        return {
            "primary": "#1f77b4",
            "secondary": "#ff7f0e",
            "success": "#2ca02c",
            "warning": "#ff7f0e",
            "error": "#d62728",
            "info": "#17a2b8"
        }
    
    def _get_monochrome_colors(self) -> Dict[str, str]:
        """Get monochrome color scheme."""
        return {
            "primary": "#000000",
            "secondary": "#666666",
            "success": "#000000",
            "warning": "#000000",
            "error": "#000000",
            "info": "#000000"
        }
    
    def _get_high_contrast_colors(self) -> Dict[str, str]:
        """Get high contrast color scheme."""
        return {
            "primary": "#000000",
            "secondary": "#ffffff",
            "success": "#00ff00",
            "warning": "#ffff00",
            "error": "#ff0000",
            "info": "#0000ff"
        }
    
    def _get_default_indicators(self) -> Dict[str, str]:
        """Get default visual indicators."""
        return {
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "info": "ℹ️",
            "healthy": "🟢",
            "degraded": "🟡",
            "critical": "🔴"
        }
    
    def _get_text_indicators(self) -> Dict[str, str]:
        """Get text-based indicators."""
        return {
            "success": "[OK]",
            "warning": "[!]",
            "error": "[ERR]",
            "info": "[INFO]",
            "healthy": "[GOOD]",
            "degraded": "[WARN]",
            "critical": "[CRIT]"
        }
    
    def _get_ascii_indicators(self) -> Dict[str, str]:
        """Get ASCII-only indicators."""
        return {
            "success": "OK",
            "warning": "!",
            "error": "X",
            "info": "i",
            "healthy": "+",
            "degraded": "~",
            "critical": "-"
        }
    
    def _get_high_contrast_indicators(self) -> Dict[str, str]:
        """Get high contrast indicators."""
        return {
            "success": "[SUCCESS]",
            "warning": "[WARNING]",
            "error": "[ERROR]",
            "info": "[INFO]",
            "healthy": "[HEALTHY]",
            "degraded": "[DEGRADED]",
            "critical": "[CRITICAL]"
        }
    
    def _get_default_accessibility(self) -> Dict[str, Any]:
        """Get default accessibility configuration."""
        return {
            "provide_alt_text": True,
            "include_fallback_text": True,
            "semantic_markup": True,
            "aria_labels": True
        }


# Utility functions for fallback handling
def create_fallback_handler(level: FallbackLevel = FallbackLevel.GRACEFUL) -> TemplateFallbackHandler:
    """Create fallback handler with specified level."""
    config = FallbackConfig(level=level)
    return TemplateFallbackHandler(config)


def handle_template_error_with_fallback(customization: TemplateCustomization,
                                       error: Exception,
                                       fallback_level: FallbackLevel = FallbackLevel.GRACEFUL) -> TemplateCustomization:
    """Handle template error with fallback."""
    handler = create_fallback_handler(fallback_level)
    return handler.handle_customization_error(customization, error)


def create_safe_mode_customization(template_type: TemplateType) -> TemplateCustomization:
    """Create safe mode customization for maximum compatibility."""
    handler = create_fallback_handler(FallbackLevel.SAFE_MODE)
    return handler._create_safe_customization(template_type)


# Global fallback handler instance
default_fallback_handler = TemplateFallbackHandler()