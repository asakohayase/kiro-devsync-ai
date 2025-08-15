"""Template customization features for color schemes, visual indicators, and accessibility."""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from copy import deepcopy

from .template_config_manager import (
    TemplateType,
    TemplateCustomization,
    BrandingConfig,
    EmojiSetConfig
)


class ColorScheme(Enum):
    """Predefined color schemes."""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    HIGH_CONTRAST = "high_contrast"
    COLORBLIND_FRIENDLY = "colorblind_friendly"
    CUSTOM = "custom"


class AccessibilityMode(Enum):
    """Accessibility mode options."""
    STANDARD = "standard"
    HIGH_CONTRAST = "high_contrast"
    SCREEN_READER = "screen_reader"
    REDUCED_MOTION = "reduced_motion"
    FULL_ACCESSIBILITY = "full_accessibility"


@dataclass
class ColorSchemeConfig:
    """Color scheme configuration."""
    name: str
    primary: str
    secondary: str
    success: str
    warning: str
    error: str
    info: str
    background: str = "#ffffff"
    text: str = "#000000"
    muted: str = "#6c757d"
    accent: str = "#007bff"
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ColorSchemeConfig':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class VisualIndicatorConfig:
    """Visual indicator configuration."""
    success_indicator: str = "✅"
    warning_indicator: str = "⚠️"
    error_indicator: str = "❌"
    info_indicator: str = "ℹ️"
    pending_indicator: str = "⏳"
    blocked_indicator: str = "🚫"
    
    # Health indicators
    healthy_indicator: str = "🟢"
    degraded_indicator: str = "🟡"
    critical_indicator: str = "🔴"
    unknown_indicator: str = "⚪"
    
    # Progress indicators
    progress_full: str = "█"
    progress_partial: str = "▓"
    progress_empty: str = "░"
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'VisualIndicatorConfig':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class InteractiveElementConfig:
    """Interactive element configuration."""
    enable_buttons: bool = True
    enable_menus: bool = True
    enable_modals: bool = True
    enable_threading: bool = True
    enable_reactions: bool = True
    
    # Button styles
    primary_button_style: str = "primary"  # primary, danger, default
    secondary_button_style: str = "default"
    
    # Confirmation levels
    confirmation_level: str = "standard"  # none, standard, detailed
    
    # Quick actions
    enable_quick_actions: bool = True
    max_quick_actions: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InteractiveElementConfig':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class AccessibilityConfig:
    """Accessibility configuration."""
    mode: AccessibilityMode = AccessibilityMode.STANDARD
    
    # Text alternatives
    provide_alt_text: bool = True
    include_fallback_text: bool = True
    verbose_descriptions: bool = False
    
    # Visual accessibility
    high_contrast_colors: bool = False
    large_text_mode: bool = False
    reduce_animations: bool = False
    
    # Screen reader support
    semantic_markup: bool = True
    aria_labels: bool = True
    skip_decorative_elements: bool = False
    
    # Color accessibility
    colorblind_friendly: bool = False
    use_patterns_with_colors: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccessibilityConfig':
        """Create from dictionary."""
        # Handle enum conversion
        if 'mode' in data and isinstance(data['mode'], str):
            data['mode'] = AccessibilityMode(data['mode'])
        return cls(**data)


class TemplateCustomizer:
    """Template customization engine."""
    
    def __init__(self):
        """Initialize template customizer."""
        self.logger = logging.getLogger(__name__)
        
        # Predefined color schemes
        self._color_schemes = self._initialize_color_schemes()
        
        # Predefined visual indicator sets
        self._indicator_sets = self._initialize_indicator_sets()
        
        # Accessibility presets
        self._accessibility_presets = self._initialize_accessibility_presets()
        
        self.logger.info("TemplateCustomizer initialized")
    
    def apply_color_scheme(self, customization: TemplateCustomization,
                          scheme: Union[ColorScheme, str, ColorSchemeConfig]) -> TemplateCustomization:
        """Apply color scheme to template customization."""
        try:
            # Get color scheme config
            if isinstance(scheme, ColorSchemeConfig):
                color_config = scheme
            elif isinstance(scheme, (ColorScheme, str)):
                scheme_name = scheme.value if isinstance(scheme, ColorScheme) else scheme
                color_config = self._color_schemes.get(scheme_name)
                if not color_config:
                    raise ValueError(f"Unknown color scheme: {scheme_name}")
            else:
                raise ValueError(f"Invalid color scheme type: {type(scheme)}")
            
            # Apply colors to customization
            updated_customization = deepcopy(customization)
            color_dict = color_config.to_dict()
            # Remove non-color fields
            color_dict.pop('name', None)
            updated_customization.color_scheme.update(color_dict)
            
            self.logger.info(f"Applied color scheme {color_config.name} to {customization.template_type.value}")
            return updated_customization
            
        except Exception as e:
            self.logger.error(f"Failed to apply color scheme: {e}")
            return customization
    
    def apply_visual_indicators(self, customization: TemplateCustomization,
                              indicators: Union[str, VisualIndicatorConfig]) -> TemplateCustomization:
        """Apply visual indicators to template customization."""
        try:
            # Get indicator config
            if isinstance(indicators, VisualIndicatorConfig):
                indicator_config = indicators
            elif isinstance(indicators, str):
                indicator_config = self._indicator_sets.get(indicators)
                if not indicator_config:
                    raise ValueError(f"Unknown indicator set: {indicators}")
            else:
                raise ValueError(f"Invalid indicator type: {type(indicators)}")
            
            # Apply indicators to customization
            updated_customization = deepcopy(customization)
            updated_customization.visual_indicators.update(indicator_config.to_dict())
            
            self.logger.info(f"Applied visual indicators to {customization.template_type.value}")
            return updated_customization
            
        except Exception as e:
            self.logger.error(f"Failed to apply visual indicators: {e}")
            return customization
    
    def apply_interactive_elements(self, customization: TemplateCustomization,
                                 interactive_config: InteractiveElementConfig) -> TemplateCustomization:
        """Apply interactive element configuration."""
        try:
            updated_customization = deepcopy(customization)
            
            # Update interactive elements flag
            updated_customization.interactive_elements = interactive_config.enable_buttons
            
            # Store detailed interactive config in custom fields
            updated_customization.custom_fields["interactive_config"] = interactive_config.to_dict()
            
            self.logger.info(f"Applied interactive element config to {customization.template_type.value}")
            return updated_customization
            
        except Exception as e:
            self.logger.error(f"Failed to apply interactive elements: {e}")
            return customization
    
    def apply_accessibility_mode(self, customization: TemplateCustomization,
                               accessibility: Union[AccessibilityMode, str, AccessibilityConfig]) -> TemplateCustomization:
        """Apply accessibility configuration."""
        try:
            # Get accessibility config
            if isinstance(accessibility, AccessibilityConfig):
                accessibility_config = accessibility
            elif isinstance(accessibility, (AccessibilityMode, str)):
                mode_name = accessibility.value if isinstance(accessibility, AccessibilityMode) else accessibility
                accessibility_config = self._accessibility_presets.get(mode_name)
                if not accessibility_config:
                    raise ValueError(f"Unknown accessibility mode: {mode_name}")
            else:
                raise ValueError(f"Invalid accessibility type: {type(accessibility)}")
            
            # Apply accessibility settings
            updated_customization = deepcopy(customization)
            updated_customization.accessibility_mode = True
            updated_customization.custom_fields["accessibility_config"] = accessibility_config.to_dict()
            
            # Apply accessibility-specific color adjustments if needed
            if accessibility_config.high_contrast_colors:
                high_contrast_scheme = self._color_schemes["high_contrast"]
                updated_customization.color_scheme.update(high_contrast_scheme.to_dict())
            
            # Apply accessibility-specific visual indicators
            if accessibility_config.colorblind_friendly:
                colorblind_indicators = self._indicator_sets["colorblind_friendly"]
                updated_customization.visual_indicators.update(colorblind_indicators.to_dict())
            
            self.logger.info(f"Applied accessibility mode {accessibility_config.mode.value} to {customization.template_type.value}")
            return updated_customization
            
        except Exception as e:
            self.logger.error(f"Failed to apply accessibility mode: {e}")
            return customization
    
    def create_custom_color_scheme(self, name: str, colors: Dict[str, str]) -> ColorSchemeConfig:
        """Create a custom color scheme."""
        try:
            # Validate required colors
            required_colors = ["primary", "secondary", "success", "warning", "error", "info"]
            missing_colors = [color for color in required_colors if color not in colors]
            
            if missing_colors:
                # Fill missing colors with defaults
                default_scheme = self._color_schemes["default"]
                for color in missing_colors:
                    colors[color] = getattr(default_scheme, color)
                self.logger.warning(f"Missing colors filled with defaults: {missing_colors}")
            
            # Create color scheme
            color_scheme = ColorSchemeConfig(name=name, **colors)
            
            # Store in available schemes
            self._color_schemes[name] = color_scheme
            
            self.logger.info(f"Created custom color scheme: {name}")
            return color_scheme
            
        except Exception as e:
            self.logger.error(f"Failed to create custom color scheme: {e}")
            raise
    
    def create_custom_indicator_set(self, name: str, indicators: Dict[str, str]) -> VisualIndicatorConfig:
        """Create a custom visual indicator set."""
        try:
            # Create with defaults and override with provided indicators
            default_indicators = self._indicator_sets["default"]
            indicator_data = default_indicators.to_dict()
            indicator_data.update(indicators)
            
            # Create indicator config
            indicator_config = VisualIndicatorConfig.from_dict(indicator_data)
            
            # Store in available sets
            self._indicator_sets[name] = indicator_config
            
            self.logger.info(f"Created custom indicator set: {name}")
            return indicator_config
            
        except Exception as e:
            self.logger.error(f"Failed to create custom indicator set: {e}")
            raise
    
    def get_available_color_schemes(self) -> List[str]:
        """Get list of available color schemes."""
        return list(self._color_schemes.keys())
    
    def get_available_indicator_sets(self) -> List[str]:
        """Get list of available indicator sets."""
        return list(self._indicator_sets.keys())
    
    def get_available_accessibility_modes(self) -> List[str]:
        """Get list of available accessibility modes."""
        return list(self._accessibility_presets.keys())
    
    def get_color_scheme(self, name: str) -> Optional[ColorSchemeConfig]:
        """Get color scheme by name."""
        return self._color_schemes.get(name)
    
    def get_indicator_set(self, name: str) -> Optional[VisualIndicatorConfig]:
        """Get indicator set by name."""
        return self._indicator_sets.get(name)
    
    def get_accessibility_preset(self, name: str) -> Optional[AccessibilityConfig]:
        """Get accessibility preset by name."""
        return self._accessibility_presets.get(name)
    
    def validate_customization(self, customization: TemplateCustomization) -> Tuple[bool, List[str]]:
        """Validate template customization."""
        errors = []
        
        try:
            # Validate color scheme
            for color_key, color_value in customization.color_scheme.items():
                if not self._is_valid_color(color_value):
                    errors.append(f"Invalid color format for {color_key}: {color_value}")
            
            # Validate visual indicators
            for indicator_key, indicator_value in customization.visual_indicators.items():
                if not indicator_value or len(indicator_value) > 10:
                    errors.append(f"Invalid indicator for {indicator_key}: {indicator_value}")
            
            # Validate accessibility config
            if "accessibility_config" in customization.custom_fields:
                accessibility_data = customization.custom_fields["accessibility_config"]
                if not isinstance(accessibility_data, dict):
                    errors.append("Accessibility config must be a dictionary")
            
            # Validate interactive config
            if "interactive_config" in customization.custom_fields:
                interactive_data = customization.custom_fields["interactive_config"]
                if not isinstance(interactive_data, dict):
                    errors.append("Interactive config must be a dictionary")
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return len(errors) == 0, errors
    
    def _initialize_color_schemes(self) -> Dict[str, ColorSchemeConfig]:
        """Initialize predefined color schemes."""
        schemes = {}
        
        # Default scheme
        schemes["default"] = ColorSchemeConfig(
            name="default",
            primary="#1f77b4",
            secondary="#ff7f0e",
            success="#2ca02c",
            warning="#ff7f0e",
            error="#d62728",
            info="#17a2b8"
        )
        
        # Dark scheme
        schemes["dark"] = ColorSchemeConfig(
            name="dark",
            primary="#4dabf7",
            secondary="#ffa726",
            success="#66bb6a",
            warning="#ffb74d",
            error="#ef5350",
            info="#26c6da",
            background="#212529",
            text="#ffffff"
        )
        
        # Light scheme
        schemes["light"] = ColorSchemeConfig(
            name="light",
            primary="#0d6efd",
            secondary="#fd7e14",
            success="#198754",
            warning="#ffc107",
            error="#dc3545",
            info="#0dcaf0",
            background="#f8f9fa",
            text="#212529"
        )
        
        # High contrast scheme
        schemes["high_contrast"] = ColorSchemeConfig(
            name="high_contrast",
            primary="#000000",
            secondary="#ffffff",
            success="#00ff00",
            warning="#ffff00",
            error="#ff0000",
            info="#0000ff",
            background="#ffffff",
            text="#000000"
        )
        
        # Colorblind friendly scheme
        schemes["colorblind_friendly"] = ColorSchemeConfig(
            name="colorblind_friendly",
            primary="#1f77b4",
            secondary="#ff7f0e",
            success="#2ca02c",
            warning="#d62728",  # Use red instead of orange
            error="#9467bd",    # Use purple instead of red
            info="#17becf"
        )
        
        return schemes
    
    def _initialize_indicator_sets(self) -> Dict[str, VisualIndicatorConfig]:
        """Initialize predefined visual indicator sets."""
        sets = {}
        
        # Default set (emoji)
        sets["default"] = VisualIndicatorConfig()
        
        # Minimal set (text symbols)
        sets["minimal"] = VisualIndicatorConfig(
            success_indicator="✓",
            warning_indicator="!",
            error_indicator="✗",
            info_indicator="i",
            pending_indicator="...",
            blocked_indicator="X",
            healthy_indicator="●",
            degraded_indicator="●",
            critical_indicator="●",
            unknown_indicator="○"
        )
        
        # Colorblind friendly set (patterns + symbols)
        sets["colorblind_friendly"] = VisualIndicatorConfig(
            success_indicator="✓✓",
            warning_indicator="▲!",
            error_indicator="✗✗",
            info_indicator="(i)",
            pending_indicator="...",
            blocked_indicator="[X]",
            healthy_indicator="●●",
            degraded_indicator="▲●",
            critical_indicator="✗●",
            unknown_indicator="○?"
        )
        
        # High contrast set
        sets["high_contrast"] = VisualIndicatorConfig(
            success_indicator="[OK]",
            warning_indicator="[!]",
            error_indicator="[ERR]",
            info_indicator="[INFO]",
            pending_indicator="[...]",
            blocked_indicator="[BLOCK]",
            healthy_indicator="[GOOD]",
            degraded_indicator="[WARN]",
            critical_indicator="[CRIT]",
            unknown_indicator="[?]"
        )
        
        return sets
    
    def _initialize_accessibility_presets(self) -> Dict[str, AccessibilityConfig]:
        """Initialize accessibility presets."""
        presets = {}
        
        # Standard accessibility
        presets["standard"] = AccessibilityConfig(
            mode=AccessibilityMode.STANDARD
        )
        
        # High contrast mode
        presets["high_contrast"] = AccessibilityConfig(
            mode=AccessibilityMode.HIGH_CONTRAST,
            high_contrast_colors=True,
            large_text_mode=True,
            use_patterns_with_colors=True
        )
        
        # Screen reader optimized
        presets["screen_reader"] = AccessibilityConfig(
            mode=AccessibilityMode.SCREEN_READER,
            provide_alt_text=True,
            include_fallback_text=True,
            verbose_descriptions=True,
            semantic_markup=True,
            aria_labels=True,
            skip_decorative_elements=True
        )
        
        # Reduced motion
        presets["reduced_motion"] = AccessibilityConfig(
            mode=AccessibilityMode.REDUCED_MOTION,
            reduce_animations=True,
            provide_alt_text=True
        )
        
        # Full accessibility
        presets["full_accessibility"] = AccessibilityConfig(
            mode=AccessibilityMode.FULL_ACCESSIBILITY,
            provide_alt_text=True,
            include_fallback_text=True,
            verbose_descriptions=True,
            high_contrast_colors=True,
            large_text_mode=True,
            reduce_animations=True,
            semantic_markup=True,
            aria_labels=True,
            colorblind_friendly=True,
            use_patterns_with_colors=True
        )
        
        return presets
    
    def _is_valid_color(self, color: str) -> bool:
        """Check if color is valid hex format."""
        import re
        return bool(re.match(r'^#[0-9a-fA-F]{6}$', color))


# Utility functions for easy customization
def apply_color_scheme_to_template(customization: TemplateCustomization,
                                 scheme_name: str) -> TemplateCustomization:
    """Apply color scheme to template customization."""
    customizer = TemplateCustomizer()
    return customizer.apply_color_scheme(customization, scheme_name)


def apply_accessibility_mode_to_template(customization: TemplateCustomization,
                                       mode_name: str) -> TemplateCustomization:
    """Apply accessibility mode to template customization."""
    customizer = TemplateCustomizer()
    return customizer.apply_accessibility_mode(customization, mode_name)


def create_high_contrast_customization(base_customization: TemplateCustomization) -> TemplateCustomization:
    """Create high contrast version of template customization."""
    customizer = TemplateCustomizer()
    
    # Apply high contrast color scheme
    customization = customizer.apply_color_scheme(base_customization, "high_contrast")
    
    # Apply high contrast indicators
    customization = customizer.apply_visual_indicators(customization, "high_contrast")
    
    # Apply high contrast accessibility mode
    customization = customizer.apply_accessibility_mode(customization, "high_contrast")
    
    return customization


# Global template customizer instance
default_template_customizer = TemplateCustomizer()