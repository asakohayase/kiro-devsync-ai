"""
Hook Configuration Manager for team settings and rule management.

This module provides comprehensive configuration management for Agent Hooks,
including team-specific rules, validation, database storage, and runtime updates.
"""

import asyncio
import logging
import os
import yaml
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path

from devsync_ai.database.connection import get_database
from devsync_ai.core.exceptions import ConfigurationError, ValidationError


logger = logging.getLogger(__name__)


@dataclass
class TeamConfiguration:
    """Team-specific hook configuration."""
    team_id: str
    team_name: str
    enabled: bool
    version: str
    default_channels: Dict[str, str]
    notification_preferences: Dict[str, Any]
    business_hours: Dict[str, Any]
    escalation_rules: List[Dict[str, Any]]
    rules: List[Dict[str, Any]]
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HookSettings:
    """Hook-specific settings for a team."""
    hook_type: str
    enabled: bool
    execution_conditions: List[Dict[str, Any]]
    notification_channels: List[str]
    rate_limits: Dict[str, Any]
    retry_policy: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ConfigurationUpdateResult:
    """Result of configuration update operation."""
    success: bool
    team_id: str
    updated_fields: List[str] = field(default_factory=list)
    validation_result: Optional[ValidationResult] = None
    error_message: Optional[str] = None


class HookConfigurationManager:
    """
    Comprehensive hook configuration manager with database storage,
    team-specific rules, and validation capabilities.
    """
    
    def __init__(self, config_directory: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_directory: Directory containing team configuration files
        """
        self.config_directory = Path(config_directory or "config")
        self._config_cache: Dict[str, TeamConfiguration] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)
    
    async def load_team_configuration(self, team_id: str) -> TeamConfiguration:
        """
        Load team configuration from cache, database, or file.
        
        Args:
            team_id: Team identifier
            
        Returns:
            TeamConfiguration object
            
        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        # Check cache first
        if self._is_cache_valid(team_id):
            return self._config_cache[team_id]
        
        try:
            # Try loading from database first
            config = await self._load_from_database(team_id)
            
            if not config:
                # Fall back to file-based configuration
                config = await self._load_from_file(team_id)
            
            if not config:
                # Use default configuration
                config = self._get_default_team_configuration(team_id)
            
            # Cache the configuration
            self._config_cache[team_id] = config
            self._cache_expiry[team_id] = datetime.now(timezone.utc) + self._cache_ttl
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration for team {team_id}: {e}")
            raise ConfigurationError(f"Cannot load configuration for team {team_id}: {e}")
    
    async def _load_from_database(self, team_id: str) -> Optional[TeamConfiguration]:
        """Load team configuration from database."""
        try:
            db = await get_database()
            
            results = await db.select(
                'team_hook_configurations',
                filters={'team_id': team_id, 'enabled': True},
                limit=1
            )
            
            if results:
                result = results[0]
                config_data = result['configuration']
                config_data['team_id'] = team_id
                config_data['enabled'] = result['enabled']
                config_data['version'] = result['version']
                config_data['last_updated'] = result['updated_at']
                
                return self._parse_configuration_data(config_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load configuration from database for team {team_id}: {e}")
            return None
    
    async def _load_from_file(self, team_id: str) -> Optional[TeamConfiguration]:
        """Load team configuration from YAML file."""
        config_file = self.config_directory / f"team_{team_id}_hooks.yaml"
        
        if not config_file.exists():
            # Try alternative naming patterns
            alternative_files = [
                self.config_directory / f"team_{team_id}.yaml",
                self.config_directory / f"{team_id}_hooks.yaml",
                self.config_directory / f"{team_id}.yaml"
            ]
            
            for alt_file in alternative_files:
                if alt_file.exists():
                    config_file = alt_file
                    break
            else:
                return None
        
        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                return None
            
            # Ensure team_id is set
            config_data['team_id'] = team_id
            
            return self._parse_configuration_data(config_data)
            
        except Exception as e:
            logger.error(f"Failed to load configuration from file {config_file}: {e}")
            return None
    
    def _parse_configuration_data(self, config_data: Dict[str, Any]) -> TeamConfiguration:
        """Parse configuration data into TeamConfiguration object."""
        return TeamConfiguration(
            team_id=config_data.get('team_id', 'unknown'),
            team_name=config_data.get('team_name', 'Unknown Team'),
            enabled=config_data.get('enabled', True),
            version=config_data.get('version', '1.0.0'),
            default_channels=config_data.get('default_channels', {}),
            notification_preferences=config_data.get('notification_preferences', {}),
            business_hours=config_data.get('business_hours', {}),
            escalation_rules=config_data.get('escalation_rules', []),
            rules=config_data.get('rules', []),
            last_updated=config_data.get('last_updated', datetime.now(timezone.utc)),
            metadata=config_data.get('metadata', {})
        )
    
    def _get_default_team_configuration(self, team_id: str) -> TeamConfiguration:
        """Get default configuration for a team."""
        return TeamConfiguration(
            team_id=team_id,
            team_name=f"{team_id.title()} Team",
            enabled=True,
            version="1.0.0",
            default_channels={
                "status_change": f"#{team_id}-updates",
                "assignment": f"#{team_id}-assignments",
                "comment": f"#{team_id}-discussions",
                "blocker": f"#{team_id}-alerts",
                "general": f"#{team_id}"
            },
            notification_preferences={
                "batch_threshold": 3,
                "batch_timeout_minutes": 5,
                "quiet_hours": {
                    "enabled": True,
                    "start": "22:00",
                    "end": "08:00"
                },
                "weekend_notifications": False
            },
            business_hours={
                "start": "09:00",
                "end": "17:00",
                "timezone": "UTC",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
            },
            escalation_rules=[],
            rules=[
                {
                    "rule_id": f"default_{team_id}_rule",
                    "name": f"Default {team_id.title()} Updates",
                    "description": f"Default rule for {team_id} team issues",
                    "hook_types": ["StatusChangeHook", "AssignmentHook", "CommentHook"],
                    "enabled": True,
                    "priority": 10,
                    "conditions": {
                        "logic": "and",
                        "conditions": [
                            {
                                "field": "event.classification.affected_teams",
                                "operator": "contains",
                                "value": team_id
                            }
                        ]
                    },
                    "metadata": {
                        "channels": [f"#{team_id}"]
                    }
                }
            ],
            last_updated=datetime.now(timezone.utc)
        )
    
    def _is_cache_valid(self, team_id: str) -> bool:
        """Check if cached configuration is still valid."""
        if team_id not in self._config_cache:
            return False
        
        if team_id not in self._cache_expiry:
            return False
        
        return datetime.now(timezone.utc) < self._cache_expiry[team_id]
    
    async def update_team_rules(
        self, 
        team_id: str, 
        rules: List[Dict[str, Any]]
    ) -> ConfigurationUpdateResult:
        """
        Update team-specific rules.
        
        Args:
            team_id: Team identifier
            rules: List of rule configurations
            
        Returns:
            ConfigurationUpdateResult
        """
        try:
            # Load current configuration
            current_config = await self.load_team_configuration(team_id)
            
            # Validate new rules
            validation_result = await self.validate_rules(rules)
            if not validation_result.valid:
                return ConfigurationUpdateResult(
                    success=False,
                    team_id=team_id,
                    validation_result=validation_result,
                    error_message="Rule validation failed"
                )
            
            # Update rules
            current_config.rules = rules
            current_config.last_updated = datetime.now(timezone.utc)
            
            # Save to database
            await self._save_to_database(current_config)
            
            # Invalidate cache
            self._invalidate_cache(team_id)
            
            return ConfigurationUpdateResult(
                success=True,
                team_id=team_id,
                updated_fields=["rules"],
                validation_result=validation_result
            )
            
        except Exception as e:
            logger.error(f"Failed to update rules for team {team_id}: {e}")
            return ConfigurationUpdateResult(
                success=False,
                team_id=team_id,
                error_message=str(e)
            )
    
    async def update_team_configuration(
        self, 
        team_id: str, 
        config_updates: Dict[str, Any]
    ) -> ConfigurationUpdateResult:
        """
        Update team configuration.
        
        Args:
            team_id: Team identifier
            config_updates: Dictionary of configuration updates
            
        Returns:
            ConfigurationUpdateResult
        """
        try:
            # Load current configuration
            current_config = await self.load_team_configuration(team_id)
            
            # Apply updates
            updated_fields = []
            
            for field, value in config_updates.items():
                if hasattr(current_config, field):
                    setattr(current_config, field, value)
                    updated_fields.append(field)
                else:
                    current_config.metadata[field] = value
                    updated_fields.append(f"metadata.{field}")
            
            current_config.last_updated = datetime.now(timezone.utc)
            
            # Validate updated configuration
            validation_result = await self.validate_configuration(current_config)
            if not validation_result.valid:
                return ConfigurationUpdateResult(
                    success=False,
                    team_id=team_id,
                    validation_result=validation_result,
                    error_message="Configuration validation failed"
                )
            
            # Save to database
            await self._save_to_database(current_config)
            
            # Invalidate cache
            self._invalidate_cache(team_id)
            
            return ConfigurationUpdateResult(
                success=True,
                team_id=team_id,
                updated_fields=updated_fields,
                validation_result=validation_result
            )
            
        except Exception as e:
            logger.error(f"Failed to update configuration for team {team_id}: {e}")
            return ConfigurationUpdateResult(
                success=False,
                team_id=team_id,
                error_message=str(e)
            )
    
    async def _save_to_database(self, config: TeamConfiguration):
        """Save team configuration to database."""
        try:
            db = await get_database()
            
            # Convert configuration to JSON
            config_data = {
                'team_name': config.team_name,
                'default_channels': config.default_channels,
                'notification_preferences': config.notification_preferences,
                'business_hours': config.business_hours,
                'escalation_rules': config.escalation_rules,
                'rules': config.rules,
                'metadata': config.metadata
            }
            
            # Upsert configuration
            await db.upsert(
                'team_hook_configurations',
                {
                    'team_id': config.team_id,
                    'configuration': config_data,
                    'enabled': config.enabled,
                    'version': config.version,
                    'updated_at': config.last_updated.isoformat()
                }
            )
            
            logger.info(f"Saved configuration for team {config.team_id} to database")
            
        except Exception as e:
            logger.error(f"Failed to save configuration to database: {e}")
            raise
    
    def _invalidate_cache(self, team_id: str):
        """Invalidate cached configuration for a team."""
        if team_id in self._config_cache:
            del self._config_cache[team_id]
        if team_id in self._cache_expiry:
            del self._cache_expiry[team_id]
    
    async def get_hook_settings(self, hook_type: str, team_id: str) -> HookSettings:
        """
        Get hook-specific settings for a team.
        
        Args:
            hook_type: Type of hook (e.g., 'StatusChangeHook')
            team_id: Team identifier
            
        Returns:
            HookSettings object
        """
        config = await self.load_team_configuration(team_id)
        
        # Find rules that apply to this hook type
        applicable_rules = [
            rule for rule in config.rules
            if hook_type in rule.get('hook_types', [])
        ]
        
        # Extract settings from rules and configuration
        execution_conditions = []
        notification_channels = set()
        
        for rule in applicable_rules:
            if rule.get('enabled', True):
                execution_conditions.append(rule.get('conditions', {}))
                rule_channels = rule.get('metadata', {}).get('channels', [])
                notification_channels.update(rule_channels)
        
        # Add default channels if no specific channels found
        if not notification_channels:
            default_channel_key = hook_type.lower().replace('hook', '')
            default_channel = config.default_channels.get(default_channel_key)
            if default_channel:
                notification_channels.add(default_channel)
        
        return HookSettings(
            hook_type=hook_type,
            enabled=config.enabled and len(applicable_rules) > 0,
            execution_conditions=execution_conditions,
            notification_channels=list(notification_channels),
            rate_limits={
                'max_executions_per_hour': 100,
                'max_notifications_per_hour': 50
            },
            retry_policy={
                'max_attempts': 3,
                'backoff_multiplier': 2,
                'max_delay_seconds': 300
            }
        )
    
    async def validate_configuration(self, config: TeamConfiguration) -> ValidationResult:
        """
        Validate team configuration.
        
        Args:
            config: TeamConfiguration to validate
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        suggestions = []
        
        # Validate basic fields
        if not config.team_id:
            errors.append("Team ID is required")
        
        if not config.team_name:
            warnings.append("Team name is not set")
        
        # Validate default channels
        if not config.default_channels:
            warnings.append("No default channels configured")
        else:
            for channel_type, channel in config.default_channels.items():
                if not channel.startswith('#'):
                    warnings.append(f"Channel '{channel}' for {channel_type} should start with '#'")
        
        # Validate notification preferences
        if config.notification_preferences:
            batch_threshold = config.notification_preferences.get('batch_threshold')
            if batch_threshold and (batch_threshold < 1 or batch_threshold > 100):
                errors.append("Batch threshold must be between 1 and 100")
            
            batch_timeout = config.notification_preferences.get('batch_timeout_minutes')
            if batch_timeout and (batch_timeout < 1 or batch_timeout > 60):
                errors.append("Batch timeout must be between 1 and 60 minutes")
        
        # Validate business hours
        if config.business_hours:
            start_time = config.business_hours.get('start')
            end_time = config.business_hours.get('end')
            
            if start_time and not self._is_valid_time_format(start_time):
                errors.append(f"Invalid start time format: {start_time}")
            
            if end_time and not self._is_valid_time_format(end_time):
                errors.append(f"Invalid end time format: {end_time}")
        
        # Validate rules
        rule_validation = await self.validate_rules(config.rules)
        errors.extend(rule_validation.errors)
        warnings.extend(rule_validation.warnings)
        suggestions.extend(rule_validation.suggestions)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    async def validate_rules(self, rules: List[Dict[str, Any]]) -> ValidationResult:
        """
        Validate hook rules.
        
        Args:
            rules: List of rule configurations
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        suggestions = []
        
        rule_ids = set()
        
        for i, rule in enumerate(rules):
            rule_prefix = f"Rule {i + 1}"
            
            # Validate required fields
            if 'rule_id' not in rule:
                errors.append(f"{rule_prefix}: Missing rule_id")
            else:
                rule_id = rule['rule_id']
                if rule_id in rule_ids:
                    errors.append(f"{rule_prefix}: Duplicate rule_id '{rule_id}'")
                rule_ids.add(rule_id)
            
            if 'name' not in rule:
                errors.append(f"{rule_prefix}: Missing name")
            
            if 'hook_types' not in rule:
                errors.append(f"{rule_prefix}: Missing hook_types")
            elif not isinstance(rule['hook_types'], list):
                errors.append(f"{rule_prefix}: hook_types must be a list")
            
            # Validate priority
            priority = rule.get('priority')
            if priority is not None:
                if not isinstance(priority, int) or priority < 1 or priority > 100:
                    errors.append(f"{rule_prefix}: Priority must be an integer between 1 and 100")
            
            # Validate conditions
            if 'conditions' in rule:
                condition_validation = self._validate_rule_conditions(rule['conditions'], rule_prefix)
                errors.extend(condition_validation.errors)
                warnings.extend(condition_validation.warnings)
            
            # Validate metadata
            if 'metadata' in rule:
                metadata = rule['metadata']
                if 'channels' in metadata:
                    channels = metadata['channels']
                    if not isinstance(channels, list):
                        errors.append(f"{rule_prefix}: metadata.channels must be a list")
                    else:
                        for channel in channels:
                            if not isinstance(channel, str) or not channel.startswith('#'):
                                warnings.append(f"{rule_prefix}: Channel '{channel}' should start with '#'")
        
        # Check for rule coverage
        if not rules:
            warnings.append("No rules defined - team will not receive notifications")
        
        # Suggest priority ordering
        priorities = [rule.get('priority', 50) for rule in rules if 'priority' in rule]
        if len(set(priorities)) != len(priorities):
            suggestions.append("Consider using unique priorities for better rule ordering")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_rule_conditions(self, conditions: Dict[str, Any], rule_prefix: str) -> ValidationResult:
        """Validate rule conditions structure."""
        errors = []
        warnings = []
        
        if not isinstance(conditions, dict):
            errors.append(f"{rule_prefix}: Conditions must be a dictionary")
            return ValidationResult(valid=False, errors=errors)
        
        # Validate logic operator
        logic = conditions.get('logic', 'and')
        if logic not in ['and', 'or']:
            errors.append(f"{rule_prefix}: Logic must be 'and' or 'or'")
        
        # Validate conditions list
        condition_list = conditions.get('conditions', [])
        if not isinstance(condition_list, list):
            errors.append(f"{rule_prefix}: Conditions must contain a list of conditions")
        else:
            for j, condition in enumerate(condition_list):
                cond_prefix = f"{rule_prefix}, condition {j + 1}"
                
                if not isinstance(condition, dict):
                    errors.append(f"{cond_prefix}: Must be a dictionary")
                    continue
                
                # Check for nested logic
                if 'logic' in condition:
                    nested_validation = self._validate_rule_conditions(condition, cond_prefix)
                    errors.extend(nested_validation.errors)
                    warnings.extend(nested_validation.warnings)
                else:
                    # Validate field condition
                    if 'field' not in condition:
                        errors.append(f"{cond_prefix}: Missing 'field'")
                    
                    if 'operator' not in condition:
                        errors.append(f"{cond_prefix}: Missing 'operator'")
                    else:
                        operator = condition['operator']
                        valid_operators = [
                            'equals', 'not_equals', 'contains', 'not_contains',
                            'in', 'not_in', 'regex', 'greater_than', 'less_than'
                        ]
                        if operator not in valid_operators:
                            errors.append(f"{cond_prefix}: Invalid operator '{operator}'")
                    
                    if 'value' not in condition:
                        errors.append(f"{cond_prefix}: Missing 'value'")
        
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
    
    async def get_all_team_configurations(self) -> List[TeamConfiguration]:
        """Get configurations for all teams."""
        try:
            db = await get_database()
            
            results = await db.select(
                'team_hook_configurations',
                filters={'enabled': True},
                order_by='team_id'
            )
            
            configurations = []
            for result in results:
                config_data = result['configuration']
                config_data['team_id'] = result['team_id']
                config_data['enabled'] = result['enabled']
                config_data['version'] = result['version']
                config_data['last_updated'] = result['updated_at']
                
                configurations.append(self._parse_configuration_data(config_data))
            
            return configurations
            
        except Exception as e:
            logger.error(f"Failed to get all team configurations: {e}")
            return []
    
    async def delete_team_configuration(self, team_id: str) -> bool:
        """
        Delete team configuration.
        
        Args:
            team_id: Team identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            db = await get_database()
            
            result = await db.delete(
                'team_hook_configurations',
                filters={'team_id': team_id}
            )
            
            # Invalidate cache
            self._invalidate_cache(team_id)
            
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"Failed to delete configuration for team {team_id}: {e}")
            return False
    
    async def export_team_configuration(self, team_id: str) -> Optional[Dict[str, Any]]:
        """
        Export team configuration as dictionary.
        
        Args:
            team_id: Team identifier
            
        Returns:
            Configuration dictionary or None if not found
        """
        try:
            config = await self.load_team_configuration(team_id)
            
            return {
                'team_id': config.team_id,
                'team_name': config.team_name,
                'enabled': config.enabled,
                'version': config.version,
                'default_channels': config.default_channels,
                'notification_preferences': config.notification_preferences,
                'business_hours': config.business_hours,
                'escalation_rules': config.escalation_rules,
                'rules': config.rules,
                'last_updated': config.last_updated.isoformat(),
                'metadata': config.metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to export configuration for team {team_id}: {e}")
            return None
    
    async def import_team_configuration(
        self, 
        team_id: str, 
        config_data: Dict[str, Any]
    ) -> ConfigurationUpdateResult:
        """
        Import team configuration from dictionary.
        
        Args:
            team_id: Team identifier
            config_data: Configuration dictionary
            
        Returns:
            ConfigurationUpdateResult
        """
        try:
            # Ensure team_id matches
            config_data['team_id'] = team_id
            
            # Parse configuration
            config = self._parse_configuration_data(config_data)
            
            # Validate configuration
            validation_result = await self.validate_configuration(config)
            if not validation_result.valid:
                return ConfigurationUpdateResult(
                    success=False,
                    team_id=team_id,
                    validation_result=validation_result,
                    error_message="Configuration validation failed"
                )
            
            # Save to database
            await self._save_to_database(config)
            
            # Invalidate cache
            self._invalidate_cache(team_id)
            
            return ConfigurationUpdateResult(
                success=True,
                team_id=team_id,
                updated_fields=["all"],
                validation_result=validation_result
            )
            
        except Exception as e:
            logger.error(f"Failed to import configuration for team {team_id}: {e}")
            return ConfigurationUpdateResult(
                success=False,
                team_id=team_id,
                error_message=str(e)
            )