"""
Advanced Configuration Management for Weekly Changelog Generation System.

This module provides comprehensive configuration management for the changelog system,
extending existing DevSync AI configuration patterns with changelog-specific features
including runtime updates, team customization, versioning, and validation.
"""

import asyncio
import logging
import os
import yaml
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
from copy import deepcopy
import hashlib

from devsync_ai.core.config_manager import FlexibleConfigurationManager, ConfigurationSchema
from devsync_ai.core.hook_configuration_manager import HookConfigurationManager, ValidationResult
from devsync_ai.database.connection import get_database
from devsync_ai.core.exceptions import ConfigurationError, ValidationError


logger = logging.getLogger(__name__)


class TemplateStyle(Enum):
    """Changelog template styles."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"


class AudienceType(Enum):
    """Target audience types."""
    TECHNICAL = "technical"
    BUSINESS = "business"
    MIXED = "mixed"
    EXECUTIVE = "executive"


class AnalysisDepth(Enum):
    """Data analysis depth levels."""
    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"


@dataclass
class DataSourceConfig:
    """Configuration for data sources."""
    enabled: bool = True
    rate_limit_buffer: int = 100
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD
    timeout_seconds: int = 60
    retry_attempts: int = 3
    cache_ttl_minutes: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduleConfig:
    """Changelog generation schedule configuration."""
    enabled: bool = True
    day: str = "friday"  # Day of week
    time: str = "17:00"  # Time in HH:MM format
    timezone: str = "UTC"
    manual_trigger_enabled: bool = True
    skip_holidays: bool = True
    holiday_calendar: Optional[str] = None
    retry_on_failure: bool = True
    max_retry_attempts: int = 3
    retry_delay_minutes: int = 30


@dataclass
class ContentConfig:
    """Content generation configuration."""
    template_style: TemplateStyle = TemplateStyle.PROFESSIONAL
    audience_type: AudienceType = AudienceType.TECHNICAL
    include_metrics: bool = True
    include_contributor_recognition: bool = True
    include_risk_analysis: bool = True
    include_performance_analysis: bool = True
    max_commits_displayed: int = 20
    max_tickets_displayed: int = 15
    max_contributors_highlighted: int = 10
    focus_areas: List[str] = field(default_factory=list)
    custom_sections: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DistributionConfig:
    """Distribution configuration."""
    primary_channel: str
    secondary_channels: List[str] = field(default_factory=list)
    channel_specific_formatting: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    email_distribution: bool = False
    email_recipients: List[str] = field(default_factory=list)
    webhook_urls: List[str] = field(default_factory=list)
    rss_feed_enabled: bool = False
    export_formats: List[str] = field(default_factory=lambda: ["slack", "markdown"])
    delivery_confirmation: bool = True
    retry_failed_deliveries: bool = True


@dataclass
class InteractiveConfig:
    """Interactive features configuration."""
    enable_feedback_buttons: bool = True
    enable_drill_down: bool = True
    enable_export_options: bool = True
    enable_threading: bool = True
    feedback_timeout_hours: int = 48
    quick_actions_enabled: bool = True
    custom_actions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class NotificationConfig:
    """Notification settings."""
    notify_on_generation: bool = True
    notify_on_failure: bool = True
    notify_on_success: bool = False
    escalation_channels: List[str] = field(default_factory=list)
    quiet_hours_enabled: bool = True
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    weekend_notifications: bool = False


@dataclass
class TeamChangelogConfig:
    """Complete team changelog configuration."""
    team_id: str
    team_name: str
    enabled: bool = True
    version: str = "1.0.0"
    
    # Core configuration sections
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    data_sources: Dict[str, DataSourceConfig] = field(default_factory=dict)
    content: ContentConfig = field(default_factory=ContentConfig)
    distribution: DistributionConfig = field(default_factory=lambda: DistributionConfig(primary_channel="#general"))
    interactive: InteractiveConfig = field(default_factory=InteractiveConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    
    # Metadata and tracking
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_generated: Optional[datetime] = None
    generation_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GlobalChangelogConfig:
    """Global changelog system configuration."""
    enabled: bool = True
    debug_mode: bool = False
    version: str = "1.0.0"
    
    # Global settings
    default_schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    default_data_sources: Dict[str, DataSourceConfig] = field(default_factory=dict)
    
    # Performance settings
    max_concurrent_generations: int = 5
    generation_timeout_minutes: int = 10
    cache_ttl_minutes: int = 60
    
    # Storage settings
    enable_history: bool = True
    retention_days: int = 365
    enable_analytics: bool = True
    enable_export: bool = True
    
    # Security settings
    require_authentication: bool = True
    team_isolation: bool = True
    audit_logging: bool = True
    encrypt_sensitive_data: bool = True
    
    # Monitoring settings
    health_checks_enabled: bool = True
    performance_monitoring: bool = True
    alert_on_failures: bool = True
    
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ConfigurationVersion:
    """Configuration version tracking."""
    version_id: str
    team_id: str
    config_hash: str
    created_at: datetime
    created_by: str
    description: str
    is_active: bool = False
    rollback_available: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigurationTemplate:
    """Configuration template for guided setup."""
    template_id: str
    name: str
    description: str
    category: str  # e.g., "engineering", "product", "qa"
    template_config: TeamChangelogConfig
    setup_wizard_steps: List[Dict[str, Any]] = field(default_factory=list)
    validation_rules: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChangelogConfigurationManager:
    """
    Advanced configuration manager for the changelog system.
    
    Extends existing DevSync AI configuration patterns with changelog-specific
    features including runtime updates, team customization, versioning, and validation.
    """
    
    def __init__(self, config_directory: Optional[str] = None, environment: str = "production"):
        """
        Initialize changelog configuration manager.
        
        Args:
            config_directory: Directory containing configuration files
            environment: Environment name (production, staging, development)
        """
        self.config_directory = Path(config_directory or "config")
        self.environment = environment
        self.logger = logging.getLogger(__name__)
        
        # Initialize base configuration managers
        self.base_config_manager = FlexibleConfigurationManager(
            config_dir=str(self.config_directory),
            environment=environment
        )
        self.hook_config_manager = HookConfigurationManager(str(self.config_directory))
        
        # Configuration cache
        self._global_config_cache: Optional[GlobalChangelogConfig] = None
        self._team_config_cache: Dict[str, TeamChangelogConfig] = {}
        self._template_cache: Dict[str, ConfigurationTemplate] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)
        
        # Change listeners
        self._change_listeners: List[Callable[[str, TeamChangelogConfig], None]] = []
        self._global_change_listeners: List[Callable[[GlobalChangelogConfig], None]] = []
        
        # Configuration validation
        self._validation_rules: Dict[str, List[Callable]] = {}
        self._setup_default_validation_rules()
        
        # Ensure directories exist
        self.config_directory.mkdir(parents=True, exist_ok=True)
        (self.config_directory / "changelog").mkdir(parents=True, exist_ok=True)
        (self.config_directory / "templates").mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"ChangelogConfigurationManager initialized for environment: {environment}")
    
    async def load_global_configuration(self, force_reload: bool = False) -> GlobalChangelogConfig:
        """
        Load global changelog configuration.
        
        Args:
            force_reload: Force reload from storage
            
        Returns:
            GlobalChangelogConfig object
        """
        cache_key = "global"
        
        if not force_reload and self._is_cache_valid(cache_key):
            return self._global_config_cache
        
        try:
            # Try loading from database first
            config = await self._load_global_config_from_database()
            
            if not config:
                # Fall back to file-based configuration
                config = await self._load_global_config_from_file()
            
            if not config:
                # Use default configuration
                config = self._get_default_global_config()
            
            # Cache the configuration
            self._global_config_cache = config
            self._cache_timestamps[cache_key] = datetime.now(timezone.utc)
            
            self.logger.info("Global changelog configuration loaded successfully")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load global changelog configuration: {e}")
            return self._get_default_global_config()
    
    async def load_team_configuration(self, team_id: str, force_reload: bool = False) -> TeamChangelogConfig:
        """
        Load team-specific changelog configuration.
        
        Args:
            team_id: Team identifier
            force_reload: Force reload from storage
            
        Returns:
            TeamChangelogConfig object
        """
        cache_key = f"team_{team_id}"
        
        if not force_reload and self._is_cache_valid(cache_key):
            return self._team_config_cache[team_id]
        
        try:
            # Try loading from database first
            config = await self._load_team_config_from_database(team_id)
            
            if not config:
                # Fall back to file-based configuration
                config = await self._load_team_config_from_file(team_id)
            
            if not config:
                # Create default configuration for team
                config = await self._create_default_team_config(team_id)
            
            # Cache the configuration
            self._team_config_cache[team_id] = config
            self._cache_timestamps[cache_key] = datetime.now(timezone.utc)
            
            self.logger.info(f"Team changelog configuration loaded for {team_id}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load team configuration for {team_id}: {e}")
            return await self._create_default_team_config(team_id)
    
    async def save_global_configuration(self, config: GlobalChangelogConfig) -> bool:
        """
        Save global changelog configuration.
        
        Args:
            config: Global configuration to save
            
        Returns:
            True if saved successfully
        """
        try:
            # Validate configuration
            validation_result = await self.validate_global_configuration(config)
            if not validation_result.valid:
                self.logger.error(f"Cannot save invalid global configuration: {validation_result.errors}")
                return False
            
            # Update timestamp
            config.last_updated = datetime.now(timezone.utc)
            
            # Save to database
            await self._save_global_config_to_database(config)
            
            # Save to file as backup
            await self._save_global_config_to_file(config)
            
            # Update cache
            self._global_config_cache = config
            self._cache_timestamps["global"] = datetime.now(timezone.utc)
            
            # Notify listeners
            for listener in self._global_change_listeners:
                try:
                    listener(config)
                except Exception as e:
                    self.logger.error(f"Error in global change listener: {e}")
            
            self.logger.info("Global changelog configuration saved successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save global configuration: {e}")
            return False
    
    async def save_team_configuration(self, team_id: str, config: TeamChangelogConfig) -> bool:
        """
        Save team-specific changelog configuration.
        
        Args:
            team_id: Team identifier
            config: Team configuration to save
            
        Returns:
            True if saved successfully
        """
        try:
            # Ensure team_id matches
            config.team_id = team_id
            
            # Validate configuration
            validation_result = await self.validate_team_configuration(config)
            if not validation_result.valid:
                self.logger.error(f"Cannot save invalid team configuration for {team_id}: {validation_result.errors}")
                return False
            
            # Update timestamp
            config.last_updated = datetime.now(timezone.utc)
            
            # Create version snapshot
            await self._create_configuration_version(config)
            
            # Save to database
            await self._save_team_config_to_database(config)
            
            # Save to file as backup
            await self._save_team_config_to_file(config)
            
            # Update cache
            self._team_config_cache[team_id] = config
            self._cache_timestamps[f"team_{team_id}"] = datetime.now(timezone.utc)
            
            # Notify listeners
            for listener in self._change_listeners:
                try:
                    listener(team_id, config)
                except Exception as e:
                    self.logger.error(f"Error in team change listener: {e}")
            
            self.logger.info(f"Team changelog configuration saved for {team_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save team configuration for {team_id}: {e}")
            return False
    
    async def update_team_configuration(
        self, 
        team_id: str, 
        updates: Dict[str, Any],
        create_version: bool = True
    ) -> ValidationResult:
        """
        Update team configuration with runtime changes.
        
        Args:
            team_id: Team identifier
            updates: Dictionary of configuration updates
            create_version: Whether to create a version snapshot
            
        Returns:
            ValidationResult indicating success/failure
        """
        try:
            # Load current configuration
            current_config = await self.load_team_configuration(team_id)
            
            # Apply updates
            updated_config = self._apply_configuration_updates(current_config, updates)
            
            # Validate updated configuration
            validation_result = await self.validate_team_configuration(updated_config)
            if not validation_result.valid:
                return validation_result
            
            # Save updated configuration
            success = await self.save_team_configuration(team_id, updated_config)
            
            if success:
                return ValidationResult(
                    valid=True,
                    suggestions=[f"Configuration updated successfully for team {team_id}"]
                )
            else:
                return ValidationResult(
                    valid=False,
                    errors=["Failed to save updated configuration"]
                )
                
        except Exception as e:
            self.logger.error(f"Failed to update team configuration for {team_id}: {e}")
            return ValidationResult(
                valid=False,
                errors=[f"Update failed: {str(e)}"]
            )
    
    async def create_team_from_template(
        self, 
        team_id: str, 
        template_id: str,
        customizations: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Create team configuration from template.
        
        Args:
            team_id: Team identifier
            template_id: Template identifier
            customizations: Optional customizations to apply
            
        Returns:
            ValidationResult indicating success/failure
        """
        try:
            # Load template
            template = await self.load_configuration_template(template_id)
            if not template:
                return ValidationResult(
                    valid=False,
                    errors=[f"Template {template_id} not found"]
                )
            
            # Create configuration from template
            config = deepcopy(template.template_config)
            config.team_id = team_id
            config.created_at = datetime.now(timezone.utc)
            config.last_updated = datetime.now(timezone.utc)
            
            # Apply customizations
            if customizations:
                config = self._apply_configuration_updates(config, customizations)
            
            # Validate configuration
            validation_result = await self.validate_team_configuration(config)
            if not validation_result.valid:
                return validation_result
            
            # Save configuration
            success = await self.save_team_configuration(team_id, config)
            
            if success:
                return ValidationResult(
                    valid=True,
                    suggestions=[f"Team configuration created from template {template_id}"]
                )
            else:
                return ValidationResult(
                    valid=False,
                    errors=["Failed to save team configuration"]
                )
                
        except Exception as e:
            self.logger.error(f"Failed to create team from template: {e}")
            return ValidationResult(
                valid=False,
                errors=[f"Template creation failed: {str(e)}"]
            )
    
    async def rollback_team_configuration(self, team_id: str, version_id: str) -> ValidationResult:
        """
        Rollback team configuration to a previous version.
        
        Args:
            team_id: Team identifier
            version_id: Version identifier to rollback to
            
        Returns:
            ValidationResult indicating success/failure
        """
        try:
            # Load version
            version_config = await self._load_configuration_version(team_id, version_id)
            if not version_config:
                return ValidationResult(
                    valid=False,
                    errors=[f"Version {version_id} not found for team {team_id}"]
                )
            
            # Validate version configuration
            validation_result = await self.validate_team_configuration(version_config)
            if not validation_result.valid:
                return ValidationResult(
                    valid=False,
                    errors=["Cannot rollback to invalid configuration version"]
                )
            
            # Update timestamps for rollback
            version_config.last_updated = datetime.now(timezone.utc)
            
            # Save as current configuration
            success = await self.save_team_configuration(team_id, version_config)
            
            if success:
                return ValidationResult(
                    valid=True,
                    suggestions=[f"Configuration rolled back to version {version_id}"]
                )
            else:
                return ValidationResult(
                    valid=False,
                    errors=["Failed to save rolled back configuration"]
                )
                
        except Exception as e:
            self.logger.error(f"Failed to rollback configuration for {team_id}: {e}")
            return ValidationResult(
                valid=False,
                errors=[f"Rollback failed: {str(e)}"]
            )
    
    async def validate_global_configuration(self, config: GlobalChangelogConfig) -> ValidationResult:
        """
        Validate global changelog configuration.
        
        Args:
            config: Global configuration to validate
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # Validate basic fields
            if not config.version:
                errors.append("Version is required")
            
            # Validate performance settings
            if config.max_concurrent_generations < 1 or config.max_concurrent_generations > 20:
                errors.append("max_concurrent_generations must be between 1 and 20")
            
            if config.generation_timeout_minutes < 1 or config.generation_timeout_minutes > 60:
                errors.append("generation_timeout_minutes must be between 1 and 60")
            
            if config.cache_ttl_minutes < 1 or config.cache_ttl_minutes > 1440:
                errors.append("cache_ttl_minutes must be between 1 and 1440 (24 hours)")
            
            # Validate retention settings
            if config.retention_days < 1 or config.retention_days > 3650:
                warnings.append("retention_days should be between 1 and 3650 (10 years)")
            
            # Validate default schedule
            if config.default_schedule:
                schedule_validation = self._validate_schedule_config(config.default_schedule)
                errors.extend(schedule_validation.errors)
                warnings.extend(schedule_validation.warnings)
            
            # Validate default data sources
            for source_name, source_config in config.default_data_sources.items():
                source_validation = self._validate_data_source_config(source_config, source_name)
                errors.extend(source_validation.errors)
                warnings.extend(source_validation.warnings)
            
            # Performance recommendations
            if config.max_concurrent_generations > 10:
                suggestions.append("Consider reducing max_concurrent_generations for better resource management")
            
            if config.generation_timeout_minutes < 5:
                suggestions.append("Consider increasing generation_timeout_minutes for complex analyses")
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    async def validate_team_configuration(self, config: TeamChangelogConfig) -> ValidationResult:
        """
        Validate team changelog configuration.
        
        Args:
            config: Team configuration to validate
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # Validate basic fields
            if not config.team_id:
                errors.append("Team ID is required")
            
            if not config.team_name:
                warnings.append("Team name is not set")
            
            # Validate schedule configuration
            if config.schedule:
                schedule_validation = self._validate_schedule_config(config.schedule)
                errors.extend(schedule_validation.errors)
                warnings.extend(schedule_validation.warnings)
                suggestions.extend(schedule_validation.suggestions)
            
            # Validate data sources
            for source_name, source_config in config.data_sources.items():
                source_validation = self._validate_data_source_config(source_config, source_name)
                errors.extend(source_validation.errors)
                warnings.extend(source_validation.warnings)
            
            # Validate content configuration
            if config.content:
                content_validation = self._validate_content_config(config.content)
                errors.extend(content_validation.errors)
                warnings.extend(content_validation.warnings)
                suggestions.extend(content_validation.suggestions)
            
            # Validate distribution configuration
            if config.distribution:
                dist_validation = self._validate_distribution_config(config.distribution)
                errors.extend(dist_validation.errors)
                warnings.extend(dist_validation.warnings)
                suggestions.extend(dist_validation.suggestions)
            
            # Validate notification configuration
            if config.notifications:
                notif_validation = self._validate_notification_config(config.notifications)
                errors.extend(notif_validation.errors)
                warnings.extend(notif_validation.warnings)
            
            # Run custom validation rules
            if config.team_id in self._validation_rules:
                for rule in self._validation_rules[config.team_id]:
                    try:
                        rule_result = rule(config)
                        if isinstance(rule_result, ValidationResult):
                            errors.extend(rule_result.errors)
                            warnings.extend(rule_result.warnings)
                            suggestions.extend(rule_result.suggestions)
                    except Exception as e:
                        warnings.append(f"Custom validation rule failed: {str(e)}")
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_schedule_config(self, schedule: ScheduleConfig) -> ValidationResult:
        """Validate schedule configuration."""
        errors = []
        warnings = []
        suggestions = []
        
        # Validate day of week
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if schedule.day.lower() not in valid_days:
            errors.append(f"Invalid schedule day: {schedule.day}")
        
        # Validate time format
        if not self._is_valid_time_format(schedule.time):
            errors.append(f"Invalid time format: {schedule.time}")
        
        # Validate timezone
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(schedule.timezone)
        except Exception:
            warnings.append(f"Timezone may not be valid: {schedule.timezone}")
        
        # Validate retry settings
        if schedule.max_retry_attempts < 0 or schedule.max_retry_attempts > 10:
            errors.append("max_retry_attempts must be between 0 and 10")
        
        if schedule.retry_delay_minutes < 1 or schedule.retry_delay_minutes > 1440:
            errors.append("retry_delay_minutes must be between 1 and 1440")
        
        # Suggestions
        if schedule.day.lower() in ["saturday", "sunday"]:
            suggestions.append("Consider scheduling on weekdays for better team visibility")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_data_source_config(self, config: DataSourceConfig, source_name: str) -> ValidationResult:
        """Validate data source configuration."""
        errors = []
        warnings = []
        
        # Validate timeout
        if config.timeout_seconds < 10 or config.timeout_seconds > 300:
            errors.append(f"{source_name}: timeout_seconds must be between 10 and 300")
        
        # Validate retry attempts
        if config.retry_attempts < 0 or config.retry_attempts > 10:
            errors.append(f"{source_name}: retry_attempts must be between 0 and 10")
        
        # Validate cache TTL
        if config.cache_ttl_minutes < 1 or config.cache_ttl_minutes > 1440:
            errors.append(f"{source_name}: cache_ttl_minutes must be between 1 and 1440")
        
        # Validate rate limit buffer
        if config.rate_limit_buffer < 0 or config.rate_limit_buffer > 1000:
            warnings.append(f"{source_name}: rate_limit_buffer should be between 0 and 1000")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_content_config(self, config: ContentConfig) -> ValidationResult:
        """Validate content configuration."""
        errors = []
        warnings = []
        suggestions = []
        
        # Validate display limits
        if config.max_commits_displayed < 1 or config.max_commits_displayed > 100:
            errors.append("max_commits_displayed must be between 1 and 100")
        
        if config.max_tickets_displayed < 1 or config.max_tickets_displayed > 100:
            errors.append("max_tickets_displayed must be between 1 and 100")
        
        if config.max_contributors_highlighted < 1 or config.max_contributors_highlighted > 50:
            errors.append("max_contributors_highlighted must be between 1 and 50")
        
        # Suggestions for better content
        if not config.include_metrics:
            suggestions.append("Consider enabling metrics for better insights")
        
        if not config.include_contributor_recognition:
            suggestions.append("Consider enabling contributor recognition for team morale")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_distribution_config(self, config: DistributionConfig) -> ValidationResult:
        """Validate distribution configuration."""
        errors = []
        warnings = []
        suggestions = []
        
        # Validate primary channel
        if not config.primary_channel:
            errors.append("Primary channel is required")
        elif not config.primary_channel.startswith('#'):
            warnings.append("Primary channel should start with '#'")
        
        # Validate secondary channels
        for channel in config.secondary_channels:
            if not channel.startswith('#'):
                warnings.append(f"Secondary channel '{channel}' should start with '#'")
        
        # Validate email recipients
        if config.email_distribution and not config.email_recipients:
            warnings.append("Email distribution enabled but no recipients specified")
        
        # Validate webhook URLs
        for url in config.webhook_urls:
            if not url.startswith(('http://', 'https://')):
                errors.append(f"Invalid webhook URL: {url}")
        
        # Suggestions
        if len(config.secondary_channels) > 5:
            suggestions.append("Consider limiting secondary channels to avoid notification fatigue")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_notification_config(self, config: NotificationConfig) -> ValidationResult:
        """Validate notification configuration."""
        errors = []
        warnings = []
        
        # Validate quiet hours
        if config.quiet_hours_enabled:
            if not self._is_valid_time_format(config.quiet_hours_start):
                errors.append(f"Invalid quiet hours start time: {config.quiet_hours_start}")
            
            if not self._is_valid_time_format(config.quiet_hours_end):
                errors.append(f"Invalid quiet hours end time: {config.quiet_hours_end}")
        
        # Validate escalation channels
        for channel in config.escalation_channels:
            if not channel.startswith('#'):
                warnings.append(f"Escalation channel '{channel}' should start with '#'")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _is_valid_time_format(self, time_str: str) -> bool:
        """Check if time string is in valid HH:MM format."""
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                return False
            
            hour, minute = int(parts[0]), int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, AttributeError):
            return False
    
    async def _load_global_config_from_database(self) -> Optional[GlobalChangelogConfig]:
        """Load global configuration from database."""
        try:
            db = await get_database()
            
            results = await db.select(
                'changelog_global_config',
                filters={'environment': self.environment},
                limit=1
            )
            
            if results:
                config_data = results[0]['configuration']
                return self._parse_global_config_data(config_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load global config from database: {e}")
            return None
    
    async def _load_team_config_from_database(self, team_id: str) -> Optional[TeamChangelogConfig]:
        """Load team configuration from database."""
        try:
            db = await get_database()
            
            results = await db.select(
                'changelog_team_configs',
                filters={'team_id': team_id, 'enabled': True},
                limit=1
            )
            
            if results:
                config_data = results[0]['configuration']
                return self._parse_team_config_data(config_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load team config from database for {team_id}: {e}")
            return None
    
    async def _load_global_config_from_file(self) -> Optional[GlobalChangelogConfig]:
        """Load global configuration from file."""
        config_files = [
            self.config_directory / f"changelog_global_{self.environment}.yaml",
            self.config_directory / "changelog" / f"global_{self.environment}.yaml",
            self.config_directory / "changelog_global.yaml"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        config_data = yaml.safe_load(f)
                    
                    if config_data:
                        return self._parse_global_config_data(config_data)
                        
                except Exception as e:
                    self.logger.error(f"Failed to load global config from {config_file}: {e}")
        
        return None
    
    async def _load_team_config_from_file(self, team_id: str) -> Optional[TeamChangelogConfig]:
        """Load team configuration from file."""
        config_files = [
            self.config_directory / f"changelog_{team_id}_{self.environment}.yaml",
            self.config_directory / "changelog" / f"{team_id}_{self.environment}.yaml",
            self.config_directory / f"changelog_{team_id}.yaml",
            self.config_directory / "changelog" / f"{team_id}.yaml"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        config_data = yaml.safe_load(f)
                    
                    if config_data:
                        return self._parse_team_config_data(config_data)
                        
                except Exception as e:
                    self.logger.error(f"Failed to load team config from {config_file}: {e}")
        
        return None
    
    def _parse_global_config_data(self, config_data: Dict[str, Any]) -> GlobalChangelogConfig:
        """Parse global configuration data."""
        # This is a simplified parser - in production you'd want more robust handling
        return GlobalChangelogConfig(
            enabled=config_data.get('enabled', True),
            debug_mode=config_data.get('debug_mode', False),
            version=config_data.get('version', '1.0.0'),
            max_concurrent_generations=config_data.get('max_concurrent_generations', 5),
            generation_timeout_minutes=config_data.get('generation_timeout_minutes', 10),
            cache_ttl_minutes=config_data.get('cache_ttl_minutes', 60),
            enable_history=config_data.get('enable_history', True),
            retention_days=config_data.get('retention_days', 365),
            enable_analytics=config_data.get('enable_analytics', True),
            enable_export=config_data.get('enable_export', True),
            require_authentication=config_data.get('require_authentication', True),
            team_isolation=config_data.get('team_isolation', True),
            audit_logging=config_data.get('audit_logging', True),
            encrypt_sensitive_data=config_data.get('encrypt_sensitive_data', True),
            health_checks_enabled=config_data.get('health_checks_enabled', True),
            performance_monitoring=config_data.get('performance_monitoring', True),
            alert_on_failures=config_data.get('alert_on_failures', True)
        )
    
    def _parse_team_config_data(self, config_data: Dict[str, Any]) -> TeamChangelogConfig:
        """Parse team configuration data."""
        # Parse schedule config
        schedule_data = config_data.get('schedule', {})
        schedule = ScheduleConfig(
            enabled=schedule_data.get('enabled', True),
            day=schedule_data.get('day', 'friday'),
            time=schedule_data.get('time', '17:00'),
            timezone=schedule_data.get('timezone', 'UTC'),
            manual_trigger_enabled=schedule_data.get('manual_trigger_enabled', True),
            skip_holidays=schedule_data.get('skip_holidays', True),
            retry_on_failure=schedule_data.get('retry_on_failure', True),
            max_retry_attempts=schedule_data.get('max_retry_attempts', 3),
            retry_delay_minutes=schedule_data.get('retry_delay_minutes', 30)
        )
        
        # Parse data sources
        data_sources = {}
        for source_name, source_data in config_data.get('data_sources', {}).items():
            if isinstance(source_data, dict):
                analysis_depth_str = source_data.get('analysis_depth', 'standard')
                analysis_depth = AnalysisDepth(analysis_depth_str) if isinstance(analysis_depth_str, str) else analysis_depth_str
                
                data_sources[source_name] = DataSourceConfig(
                    enabled=source_data.get('enabled', True),
                    rate_limit_buffer=source_data.get('rate_limit_buffer', 100),
                    analysis_depth=analysis_depth,
                    timeout_seconds=source_data.get('timeout_seconds', 60),
                    retry_attempts=source_data.get('retry_attempts', 3),
                    cache_ttl_minutes=source_data.get('cache_ttl_minutes', 30),
                    metadata=source_data.get('metadata', {})
                )
        
        # Parse content config
        content_data = config_data.get('content', {})
        template_style_str = content_data.get('template_style', 'professional')
        template_style = TemplateStyle(template_style_str) if isinstance(template_style_str, str) else template_style_str
        
        audience_type_str = content_data.get('audience_type', 'technical')
        audience_type = AudienceType(audience_type_str) if isinstance(audience_type_str, str) else audience_type_str
        
        content = ContentConfig(
            template_style=template_style,
            audience_type=audience_type,
            include_metrics=content_data.get('include_metrics', True),
            include_contributor_recognition=content_data.get('include_contributor_recognition', True),
            include_risk_analysis=content_data.get('include_risk_analysis', True),
            include_performance_analysis=content_data.get('include_performance_analysis', True),
            max_commits_displayed=content_data.get('max_commits_displayed', 20),
            max_tickets_displayed=content_data.get('max_tickets_displayed', 15),
            max_contributors_highlighted=content_data.get('max_contributors_highlighted', 10),
            focus_areas=content_data.get('focus_areas', []),
            custom_sections=content_data.get('custom_sections', {})
        )
        
        # Parse distribution config
        dist_data = config_data.get('distribution', {})
        distribution = DistributionConfig(
            primary_channel=dist_data.get('primary_channel', '#general'),
            secondary_channels=dist_data.get('secondary_channels', []),
            channel_specific_formatting=dist_data.get('channel_specific_formatting', {}),
            email_distribution=dist_data.get('email_distribution', False),
            email_recipients=dist_data.get('email_recipients', []),
            webhook_urls=dist_data.get('webhook_urls', []),
            rss_feed_enabled=dist_data.get('rss_feed_enabled', False),
            export_formats=dist_data.get('export_formats', ['slack', 'markdown']),
            delivery_confirmation=dist_data.get('delivery_confirmation', True),
            retry_failed_deliveries=dist_data.get('retry_failed_deliveries', True)
        )
        
        # Parse interactive config
        interactive_data = config_data.get('interactive', {})
        interactive = InteractiveConfig(
            enable_feedback_buttons=interactive_data.get('enable_feedback_buttons', True),
            enable_drill_down=interactive_data.get('enable_drill_down', True),
            enable_export_options=interactive_data.get('enable_export_options', True),
            enable_threading=interactive_data.get('enable_threading', True),
            feedback_timeout_hours=interactive_data.get('feedback_timeout_hours', 48),
            quick_actions_enabled=interactive_data.get('quick_actions_enabled', True),
            custom_actions=interactive_data.get('custom_actions', [])
        )
        
        # Parse notifications config
        notif_data = config_data.get('notifications', {})
        notifications = NotificationConfig(
            notify_on_generation=notif_data.get('notify_on_generation', True),
            notify_on_failure=notif_data.get('notify_on_failure', True),
            notify_on_success=notif_data.get('notify_on_success', False),
            escalation_channels=notif_data.get('escalation_channels', []),
            quiet_hours_enabled=notif_data.get('quiet_hours_enabled', True),
            quiet_hours_start=notif_data.get('quiet_hours_start', '22:00'),
            quiet_hours_end=notif_data.get('quiet_hours_end', '08:00'),
            weekend_notifications=notif_data.get('weekend_notifications', False)
        )
        
        return TeamChangelogConfig(
            team_id=config_data.get('team_id', 'unknown'),
            team_name=config_data.get('team_name', 'Unknown Team'),
            enabled=config_data.get('enabled', True),
            version=config_data.get('version', '1.0.0'),
            schedule=schedule,
            data_sources=data_sources,
            content=content,
            distribution=distribution,
            interactive=interactive,
            notifications=notifications,
            created_at=datetime.fromisoformat(config_data['created_at']) if 'created_at' in config_data else datetime.now(timezone.utc),
            last_updated=datetime.fromisoformat(config_data['last_updated']) if 'last_updated' in config_data else datetime.now(timezone.utc),
            last_generated=datetime.fromisoformat(config_data['last_generated']) if config_data.get('last_generated') else None,
            generation_count=config_data.get('generation_count', 0),
            metadata=config_data.get('metadata', {})
        )
    
    def _get_default_global_config(self) -> GlobalChangelogConfig:
        """Get default global configuration."""
        return GlobalChangelogConfig()
    
    async def _create_default_team_config(self, team_id: str) -> TeamChangelogConfig:
        """Create default team configuration."""
        # Try to get team name from existing hook configuration
        team_name = team_id.title()
        try:
            hook_config = await self.hook_config_manager.load_team_configuration(team_id)
            team_name = hook_config.team_name
        except Exception:
            pass
        
        return TeamChangelogConfig(
            team_id=team_id,
            team_name=team_name,
            distribution=DistributionConfig(primary_channel=f"#{team_id}-updates"),
            data_sources={
                'github': DataSourceConfig(enabled=True),
                'jira': DataSourceConfig(enabled=True),
                'team_metrics': DataSourceConfig(enabled=True)
            }
        )
    
    async def _save_global_config_to_database(self, config: GlobalChangelogConfig):
        """Save global configuration to database."""
        try:
            db = await get_database()
            
            config_data = asdict(config)
            
            await db.upsert(
                'changelog_global_config',
                {
                    'environment': self.environment,
                    'configuration': config_data,
                    'version': config.version,
                    'updated_at': config.last_updated.isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to save global config to database: {e}")
            raise
    
    async def _save_team_config_to_database(self, config: TeamChangelogConfig):
        """Save team configuration to database."""
        try:
            db = await get_database()
            
            config_data = asdict(config)
            
            await db.upsert(
                'changelog_team_configs',
                {
                    'team_id': config.team_id,
                    'configuration': config_data,
                    'enabled': config.enabled,
                    'version': config.version,
                    'updated_at': config.last_updated.isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to save team config to database: {e}")
            raise
    
    async def _save_global_config_to_file(self, config: GlobalChangelogConfig):
        """Save global configuration to file."""
        try:
            config_file = self.config_directory / "changelog" / f"global_{self.environment}.yaml"
            config_data = asdict(config)
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save global config to file: {e}")
    
    async def _save_team_config_to_file(self, config: TeamChangelogConfig):
        """Save team configuration to file."""
        try:
            config_file = self.config_directory / "changelog" / f"{config.team_id}_{self.environment}.yaml"
            config_data = self._serialize_config_for_export(asdict(config))
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save team config to file: {e}")
    
    async def _create_configuration_version(self, config: TeamChangelogConfig):
        """Create a version snapshot of the configuration."""
        try:
            db = await get_database()
            
            # Generate version ID and hash
            config_json = json.dumps(asdict(config), sort_keys=True)
            config_hash = hashlib.sha256(config_json.encode()).hexdigest()
            version_id = f"{config.team_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            
            # Store version
            await db.insert(
                'changelog_config_versions',
                {
                    'version_id': version_id,
                    'team_id': config.team_id,
                    'config_hash': config_hash,
                    'configuration': asdict(config),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'created_by': 'system',  # Could be enhanced to track actual user
                    'description': 'Automatic version snapshot',
                    'is_active': True
                }
            )
            
            # Mark previous versions as inactive
            await db.update(
                'changelog_config_versions',
                {'is_active': False},
                filters={'team_id': config.team_id, 'version_id': {'!=': version_id}}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create configuration version: {e}")
    
    async def _load_configuration_version(self, team_id: str, version_id: str) -> Optional[TeamChangelogConfig]:
        """Load a specific configuration version."""
        try:
            db = await get_database()
            
            results = await db.select(
                'changelog_config_versions',
                filters={'team_id': team_id, 'version_id': version_id},
                limit=1
            )
            
            if results:
                config_data = results[0]['configuration']
                return self._parse_team_config_data(config_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration version: {e}")
            return None
    
    def _apply_configuration_updates(self, config: TeamChangelogConfig, updates: Dict[str, Any]) -> TeamChangelogConfig:
        """Apply updates to configuration object."""
        updated_config = deepcopy(config)
        
        for key, value in updates.items():
            if hasattr(updated_config, key):
                setattr(updated_config, key, value)
            else:
                # Handle nested updates
                if '.' in key:
                    parts = key.split('.')
                    obj = updated_config
                    for part in parts[:-1]:
                        if hasattr(obj, part):
                            obj = getattr(obj, part)
                        else:
                            break
                    else:
                        if hasattr(obj, parts[-1]):
                            setattr(obj, parts[-1], value)
        
        return updated_config
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached configuration is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        age = datetime.now(timezone.utc) - self._cache_timestamps[cache_key]
        return age < self._cache_ttl
    
    def _setup_default_validation_rules(self):
        """Setup default validation rules."""
        # This can be extended with custom validation rules per team
        pass
    
    def _serialize_config_for_export(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize configuration data for export, converting enums to strings."""
        def convert_enums(obj):
            if isinstance(obj, dict):
                return {key: convert_enums(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_enums(item) for item in obj]
            elif hasattr(obj, 'value'):  # Enum
                return obj.value
            else:
                return obj
        
        return convert_enums(config_data)
    
    async def load_configuration_template(self, template_id: str) -> Optional[ConfigurationTemplate]:
        """Load configuration template."""
        # Implementation for loading templates
        # This would load from database or files
        return None
    
    def add_change_listener(self, listener: Callable[[str, TeamChangelogConfig], None]):
        """Add configuration change listener."""
        self._change_listeners.append(listener)
    
    def add_global_change_listener(self, listener: Callable[[GlobalChangelogConfig], None]):
        """Add global configuration change listener."""
        self._global_change_listeners.append(listener)
    
    async def get_all_team_configurations(self) -> List[TeamChangelogConfig]:
        """Get all team configurations."""
        try:
            db = await get_database()
            
            results = await db.select(
                'changelog_team_configs',
                filters={'enabled': True},
                order_by='team_id'
            )
            
            configurations = []
            for result in results:
                config_data = result['configuration']
                configurations.append(self._parse_team_config_data(config_data))
            
            return configurations
            
        except Exception as e:
            self.logger.error(f"Failed to get all team configurations: {e}")
            return []
    
    async def export_team_configuration(self, team_id: str, format: str = "yaml") -> Optional[str]:
        """Export team configuration in specified format."""
        try:
            config = await self.load_team_configuration(team_id)
            config_data = self._serialize_config_for_export(asdict(config))
            
            if format.lower() == "json":
                return json.dumps(config_data, indent=2, default=str)
            else:  # yaml
                return yaml.dump(config_data, default_flow_style=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to export configuration for {team_id}: {e}")
            return None
    
    async def import_team_configuration(self, team_id: str, config_data: str, format: str = "yaml") -> ValidationResult:
        """Import team configuration from string data."""
        try:
            if format.lower() == "json":
                data = json.loads(config_data)
            else:  # yaml
                data = yaml.safe_load(config_data)
            
            config = self._parse_team_config_data(data)
            config.team_id = team_id  # Ensure team_id matches
            
            # Validate and save
            validation_result = await self.validate_team_configuration(config)
            if validation_result.valid:
                success = await self.save_team_configuration(team_id, config)
                if success:
                    return ValidationResult(
                        valid=True,
                        suggestions=["Configuration imported successfully"]
                    )
                else:
                    return ValidationResult(
                        valid=False,
                        errors=["Failed to save imported configuration"]
                    )
            else:
                return validation_result
                
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Import failed: {str(e)}"]
            )


# Global configuration manager instance
default_changelog_config_manager = ChangelogConfigurationManager()