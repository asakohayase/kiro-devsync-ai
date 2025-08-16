"""
Hook Configuration Validator.

This module provides comprehensive validation utilities for hook configurations,
including rule syntax validation, condition checking, and schema validation.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union, Set
from dataclasses import dataclass
from datetime import datetime

from devsync_ai.core.hook_configuration_manager import ValidationResult


logger = logging.getLogger(__name__)


@dataclass
class FieldDefinition:
    """Definition of a valid field for rule conditions."""
    name: str
    data_type: str  # 'string', 'number', 'boolean', 'array', 'object'
    description: str
    valid_operators: List[str]
    example_values: List[Any]


@dataclass
class OperatorDefinition:
    """Definition of a valid operator for rule conditions."""
    name: str
    description: str
    valid_types: List[str]  # Data types this operator can work with
    requires_value: bool
    example: str


class HookConfigurationValidator:
    """
    Comprehensive validator for hook configurations with schema validation,
    rule syntax checking, and semantic validation.
    """
    
    def __init__(self):
        """Initialize the validator with field and operator definitions."""
        self._field_definitions = self._get_field_definitions()
        self._operator_definitions = self._get_operator_definitions()
        self._valid_hook_types = self._get_valid_hook_types()
        self._valid_channels = set()  # Will be populated from Slack API
    
    def _get_field_definitions(self) -> Dict[str, FieldDefinition]:
        """Get definitions of valid fields for rule conditions."""
        return {
            # Event fields
            'event.event_type': FieldDefinition(
                name='event.event_type',
                data_type='string',
                description='Type of JIRA event',
                valid_operators=['equals', 'not_equals', 'in', 'not_in', 'regex'],
                example_values=['jira:issue_updated', 'jira:issue_assigned', 'jira:issue_commented']
            ),
            'event.project_key': FieldDefinition(
                name='event.project_key',
                data_type='string',
                description='JIRA project key',
                valid_operators=['equals', 'not_equals', 'in', 'not_in', 'regex'],
                example_values=['ENG', 'DEV', 'TECH']
            ),
            'event.classification.category': FieldDefinition(
                name='event.classification.category',
                data_type='string',
                description='Event classification category',
                valid_operators=['equals', 'not_equals', 'in', 'not_in'],
                example_values=['blocker', 'critical', 'assignment', 'status_transition']
            ),
            'event.classification.urgency': FieldDefinition(
                name='event.classification.urgency',
                data_type='string',
                description='Event urgency level',
                valid_operators=['equals', 'not_equals', 'in', 'not_in'],
                example_values=['critical', 'high', 'medium', 'low']
            ),
            'event.classification.significance': FieldDefinition(
                name='event.classification.significance',
                data_type='string',
                description='Event significance level',
                valid_operators=['equals', 'not_equals', 'in', 'not_in'],
                example_values=['major', 'moderate', 'minor']
            ),
            'event.classification.affected_teams': FieldDefinition(
                name='event.classification.affected_teams',
                data_type='array',
                description='Teams affected by the event',
                valid_operators=['contains', 'not_contains', 'in', 'not_in'],
                example_values=['engineering', 'qa', 'product']
            ),
            'event.classification.keywords': FieldDefinition(
                name='event.classification.keywords',
                data_type='array',
                description='Keywords extracted from event',
                valid_operators=['contains', 'not_contains', 'in', 'not_in'],
                example_values=['blocked', 'urgent', 'critical']
            ),
            
            # Ticket fields
            'ticket.key': FieldDefinition(
                name='ticket.key',
                data_type='string',
                description='JIRA ticket key',
                valid_operators=['equals', 'not_equals', 'regex'],
                example_values=['ENG-123', 'DEV-456']
            ),
            'ticket.summary': FieldDefinition(
                name='ticket.summary',
                data_type='string',
                description='Ticket summary/title',
                valid_operators=['contains', 'not_contains', 'regex'],
                example_values=['Fix critical bug', 'Implement new feature']
            ),
            'ticket.description': FieldDefinition(
                name='ticket.description',
                data_type='string',
                description='Ticket description',
                valid_operators=['contains', 'not_contains', 'regex'],
                example_values=['This ticket addresses...']
            ),
            'ticket.priority.name': FieldDefinition(
                name='ticket.priority.name',
                data_type='string',
                description='Ticket priority name',
                valid_operators=['equals', 'not_equals', 'in', 'not_in'],
                example_values=['Critical', 'High', 'Medium', 'Low', 'Blocker']
            ),
            'ticket.status.name': FieldDefinition(
                name='ticket.status.name',
                data_type='string',
                description='Ticket status name',
                valid_operators=['equals', 'not_equals', 'in', 'not_in', 'contains'],
                example_values=['To Do', 'In Progress', 'Done', 'Blocked']
            ),
            'ticket.issue_type.name': FieldDefinition(
                name='ticket.issue_type.name',
                data_type='string',
                description='Issue type name',
                valid_operators=['equals', 'not_equals', 'in', 'not_in'],
                example_values=['Bug', 'Story', 'Task', 'Epic']
            ),
            'ticket.assignee.display_name': FieldDefinition(
                name='ticket.assignee.display_name',
                data_type='string',
                description='Assignee display name',
                valid_operators=['equals', 'not_equals', 'contains', 'regex'],
                example_values=['John Doe', 'Jane Smith']
            ),
            'ticket.labels': FieldDefinition(
                name='ticket.labels',
                data_type='array',
                description='Ticket labels',
                valid_operators=['contains', 'not_contains', 'in', 'not_in'],
                example_values=['production', 'security', 'performance']
            ),
            'ticket.components': FieldDefinition(
                name='ticket.components',
                data_type='array',
                description='Ticket components',
                valid_operators=['contains', 'not_contains', 'in', 'not_in'],
                example_values=['frontend', 'backend', 'database']
            ),
            'ticket.fix_versions': FieldDefinition(
                name='ticket.fix_versions',
                data_type='array',
                description='Fix versions',
                valid_operators=['contains', 'not_contains', 'regex'],
                example_values=['1.0.0', '2.1.0']
            ),
            
            # Stakeholder fields
            'stakeholders.display_names': FieldDefinition(
                name='stakeholders.display_names',
                data_type='array',
                description='Display names of stakeholders',
                valid_operators=['contains', 'not_contains', 'regex'],
                example_values=['Senior Engineer', 'Lead Developer']
            ),
            'stakeholders.account_ids': FieldDefinition(
                name='stakeholders.account_ids',
                data_type='array',
                description='Account IDs of stakeholders',
                valid_operators=['contains', 'not_contains', 'in', 'not_in'],
                example_values=['user123', 'user456']
            )
        }
    
    def _get_operator_definitions(self) -> Dict[str, OperatorDefinition]:
        """Get definitions of valid operators."""
        return {
            'equals': OperatorDefinition(
                name='equals',
                description='Exact match',
                valid_types=['string', 'number', 'boolean'],
                requires_value=True,
                example='field equals "value"'
            ),
            'not_equals': OperatorDefinition(
                name='not_equals',
                description='Not equal to',
                valid_types=['string', 'number', 'boolean'],
                requires_value=True,
                example='field not_equals "value"'
            ),
            'contains': OperatorDefinition(
                name='contains',
                description='Contains substring or array element',
                valid_types=['string', 'array'],
                requires_value=True,
                example='field contains "substring"'
            ),
            'not_contains': OperatorDefinition(
                name='not_contains',
                description='Does not contain substring or array element',
                valid_types=['string', 'array'],
                requires_value=True,
                example='field not_contains "substring"'
            ),
            'in': OperatorDefinition(
                name='in',
                description='Value is in list',
                valid_types=['string', 'number'],
                requires_value=True,
                example='field in ["value1", "value2"]'
            ),
            'not_in': OperatorDefinition(
                name='not_in',
                description='Value is not in list',
                valid_types=['string', 'number'],
                requires_value=True,
                example='field not_in ["value1", "value2"]'
            ),
            'regex': OperatorDefinition(
                name='regex',
                description='Matches regular expression',
                valid_types=['string'],
                requires_value=True,
                example='field regex "\\\\b(urgent|critical)\\\\b"'
            ),
            'greater_than': OperatorDefinition(
                name='greater_than',
                description='Greater than numeric value',
                valid_types=['number'],
                requires_value=True,
                example='field greater_than 10'
            ),
            'less_than': OperatorDefinition(
                name='less_than',
                description='Less than numeric value',
                valid_types=['number'],
                requires_value=True,
                example='field less_than 100'
            ),
            'exists': OperatorDefinition(
                name='exists',
                description='Field exists and is not null',
                valid_types=['string', 'number', 'boolean', 'array', 'object'],
                requires_value=False,
                example='field exists'
            ),
            'not_exists': OperatorDefinition(
                name='not_exists',
                description='Field does not exist or is null',
                valid_types=['string', 'number', 'boolean', 'array', 'object'],
                requires_value=False,
                example='field not_exists'
            )
        }
    
    def _get_valid_hook_types(self) -> Set[str]:
        """Get valid hook types."""
        return {
            'StatusChangeHook',
            'AssignmentHook',
            'CommentHook',
            'BlockerHook',
            'PriorityChangeHook',
            'CreationHook'
        }
    
    async def validate_team_configuration_schema(self, config_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate team configuration against schema.
        
        Args:
            config_data: Configuration data to validate
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        suggestions = []
        
        # Required fields
        required_fields = ['team_id', 'team_name', 'enabled', 'default_channels', 'rules']
        for field in required_fields:
            if field not in config_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate team_id
        if 'team_id' in config_data:
            team_id = config_data['team_id']
            if not isinstance(team_id, str) or not team_id.strip():
                errors.append("team_id must be a non-empty string")
            elif not re.match(r'^[a-zA-Z0-9_-]+$', team_id):
                errors.append("team_id must contain only alphanumeric characters, underscores, and hyphens")
        
        # Validate team_name
        if 'team_name' in config_data:
            team_name = config_data['team_name']
            if not isinstance(team_name, str) or not team_name.strip():
                warnings.append("team_name should be a non-empty string")
        
        # Validate enabled
        if 'enabled' in config_data:
            if not isinstance(config_data['enabled'], bool):
                errors.append("enabled must be a boolean value")
        
        # Validate version
        if 'version' in config_data:
            version = config_data['version']
            if not isinstance(version, str):
                warnings.append("version should be a string")
            elif not re.match(r'^\d+\.\d+\.\d+$', version):
                warnings.append("version should follow semantic versioning (e.g., '1.0.0')")
        
        # Validate default_channels
        if 'default_channels' in config_data:
            channels_result = self._validate_default_channels(config_data['default_channels'])
            errors.extend(channels_result.errors)
            warnings.extend(channels_result.warnings)
            suggestions.extend(channels_result.suggestions)
        
        # Validate notification_preferences
        if 'notification_preferences' in config_data:
            prefs_result = self._validate_notification_preferences(config_data['notification_preferences'])
            errors.extend(prefs_result.errors)
            warnings.extend(prefs_result.warnings)
        
        # Validate business_hours
        if 'business_hours' in config_data:
            hours_result = self._validate_business_hours(config_data['business_hours'])
            errors.extend(hours_result.errors)
            warnings.extend(hours_result.warnings)
        
        # Validate escalation_rules
        if 'escalation_rules' in config_data:
            escalation_result = self._validate_escalation_rules(config_data['escalation_rules'])
            errors.extend(escalation_result.errors)
            warnings.extend(escalation_result.warnings)
        
        # Validate rules
        if 'rules' in config_data:
            rules_result = await self.validate_hook_rules(config_data['rules'])
            errors.extend(rules_result.errors)
            warnings.extend(rules_result.warnings)
            suggestions.extend(rules_result.suggestions)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_default_channels(self, channels: Any) -> ValidationResult:
        """Validate default channels configuration."""
        errors = []
        warnings = []
        suggestions = []
        
        if not isinstance(channels, dict):
            errors.append("default_channels must be a dictionary")
            return ValidationResult(valid=False, errors=errors)
        
        expected_channel_types = {
            'status_change', 'assignment', 'comment', 'blocker', 'general'
        }
        
        for channel_type, channel_name in channels.items():
            if not isinstance(channel_name, str):
                errors.append(f"Channel name for '{channel_type}' must be a string")
                continue
            
            if not channel_name.startswith('#'):
                warnings.append(f"Channel '{channel_name}' for '{channel_type}' should start with '#'")
            
            if len(channel_name) < 2:
                errors.append(f"Channel name '{channel_name}' for '{channel_type}' is too short")
            
            # Check for valid Slack channel name format
            if not re.match(r'^#[a-z0-9_-]+$', channel_name.lower()):
                warnings.append(f"Channel '{channel_name}' may not be a valid Slack channel name")
        
        # Check for missing standard channel types
        missing_types = expected_channel_types - set(channels.keys())
        if missing_types:
            suggestions.append(f"Consider adding channels for: {', '.join(missing_types)}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_notification_preferences(self, prefs: Any) -> ValidationResult:
        """Validate notification preferences."""
        errors = []
        warnings = []
        
        if not isinstance(prefs, dict):
            errors.append("notification_preferences must be a dictionary")
            return ValidationResult(valid=False, errors=errors)
        
        # Validate batch_threshold
        if 'batch_threshold' in prefs:
            threshold = prefs['batch_threshold']
            if not isinstance(threshold, int) or threshold < 1 or threshold > 100:
                errors.append("batch_threshold must be an integer between 1 and 100")
        
        # Validate batch_timeout_minutes
        if 'batch_timeout_minutes' in prefs:
            timeout = prefs['batch_timeout_minutes']
            if not isinstance(timeout, int) or timeout < 1 or timeout > 60:
                errors.append("batch_timeout_minutes must be an integer between 1 and 60")
        
        # Validate quiet_hours
        if 'quiet_hours' in prefs:
            quiet_hours = prefs['quiet_hours']
            if not isinstance(quiet_hours, dict):
                errors.append("quiet_hours must be a dictionary")
            else:
                if 'enabled' in quiet_hours and not isinstance(quiet_hours['enabled'], bool):
                    errors.append("quiet_hours.enabled must be a boolean")
                
                for time_field in ['start', 'end']:
                    if time_field in quiet_hours:
                        time_value = quiet_hours[time_field]
                        if not isinstance(time_value, str):
                            errors.append(f"quiet_hours.{time_field} must be a string")
                        elif not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time_value):
                            errors.append(f"quiet_hours.{time_field} must be in HH:MM format")
        
        # Validate weekend_notifications
        if 'weekend_notifications' in prefs:
            if not isinstance(prefs['weekend_notifications'], bool):
                errors.append("weekend_notifications must be a boolean")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_business_hours(self, hours: Any) -> ValidationResult:
        """Validate business hours configuration."""
        errors = []
        warnings = []
        
        if not isinstance(hours, dict):
            errors.append("business_hours must be a dictionary")
            return ValidationResult(valid=False, errors=errors)
        
        # Validate start and end times
        for time_field in ['start', 'end']:
            if time_field in hours:
                time_value = hours[time_field]
                if not isinstance(time_value, str):
                    errors.append(f"business_hours.{time_field} must be a string")
                elif not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time_value):
                    errors.append(f"business_hours.{time_field} must be in HH:MM format")
        
        # Validate timezone
        if 'timezone' in hours:
            timezone = hours['timezone']
            if not isinstance(timezone, str):
                errors.append("business_hours.timezone must be a string")
            # Note: Full timezone validation would require pytz or similar
        
        # Validate days
        if 'days' in hours:
            days = hours['days']
            if not isinstance(days, list):
                errors.append("business_hours.days must be a list")
            else:
                valid_days = {
                    'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                    'saturday', 'sunday'
                }
                for day in days:
                    if not isinstance(day, str) or day.lower() not in valid_days:
                        errors.append(f"Invalid day '{day}' in business_hours.days")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_escalation_rules(self, rules: Any) -> ValidationResult:
        """Validate escalation rules."""
        errors = []
        warnings = []
        
        if not isinstance(rules, list):
            errors.append("escalation_rules must be a list")
            return ValidationResult(valid=False, errors=errors)
        
        for i, rule in enumerate(rules):
            rule_prefix = f"Escalation rule {i + 1}"
            
            if not isinstance(rule, dict):
                errors.append(f"{rule_prefix}: Must be a dictionary")
                continue
            
            # Validate condition
            if 'condition' not in rule:
                errors.append(f"{rule_prefix}: Missing 'condition' field")
            elif not isinstance(rule['condition'], str):
                errors.append(f"{rule_prefix}: 'condition' must be a string")
            
            # Validate escalate_after_minutes
            if 'escalate_after_minutes' not in rule:
                errors.append(f"{rule_prefix}: Missing 'escalate_after_minutes' field")
            else:
                minutes = rule['escalate_after_minutes']
                if not isinstance(minutes, int) or minutes < 1:
                    errors.append(f"{rule_prefix}: 'escalate_after_minutes' must be a positive integer")
            
            # Validate escalate_to
            if 'escalate_to' not in rule:
                errors.append(f"{rule_prefix}: Missing 'escalate_to' field")
            else:
                escalate_to = rule['escalate_to']
                if not isinstance(escalate_to, list):
                    errors.append(f"{rule_prefix}: 'escalate_to' must be a list")
                elif not escalate_to:
                    warnings.append(f"{rule_prefix}: 'escalate_to' list is empty")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def validate_hook_rules(self, rules: List[Dict[str, Any]]) -> ValidationResult:
        """
        Validate hook rules with comprehensive checks.
        
        Args:
            rules: List of rule configurations
            
        Returns:
            ValidationResult with detailed validation information
        """
        errors = []
        warnings = []
        suggestions = []
        
        if not isinstance(rules, list):
            errors.append("Rules must be a list")
            return ValidationResult(valid=False, errors=errors)
        
        rule_ids = set()
        priorities = []
        
        for i, rule in enumerate(rules):
            rule_prefix = f"Rule {i + 1}"
            
            if not isinstance(rule, dict):
                errors.append(f"{rule_prefix}: Must be a dictionary")
                continue
            
            # Validate rule_id
            if 'rule_id' not in rule:
                errors.append(f"{rule_prefix}: Missing 'rule_id'")
            else:
                rule_id = rule['rule_id']
                if not isinstance(rule_id, str) or not rule_id.strip():
                    errors.append(f"{rule_prefix}: 'rule_id' must be a non-empty string")
                elif rule_id in rule_ids:
                    errors.append(f"{rule_prefix}: Duplicate 'rule_id' '{rule_id}'")
                else:
                    rule_ids.add(rule_id)
                    
                    # Validate rule_id format
                    if not re.match(r'^[a-zA-Z0-9_-]+$', rule_id):
                        warnings.append(f"{rule_prefix}: 'rule_id' should contain only alphanumeric characters, underscores, and hyphens")
            
            # Validate name
            if 'name' not in rule:
                errors.append(f"{rule_prefix}: Missing 'name'")
            elif not isinstance(rule['name'], str) or not rule['name'].strip():
                errors.append(f"{rule_prefix}: 'name' must be a non-empty string")
            
            # Validate description
            if 'description' in rule and not isinstance(rule['description'], str):
                warnings.append(f"{rule_prefix}: 'description' should be a string")
            
            # Validate hook_types
            if 'hook_types' not in rule:
                errors.append(f"{rule_prefix}: Missing 'hook_types'")
            else:
                hook_types_result = self._validate_hook_types(rule['hook_types'], rule_prefix)
                errors.extend(hook_types_result.errors)
                warnings.extend(hook_types_result.warnings)
            
            # Validate enabled
            if 'enabled' in rule and not isinstance(rule['enabled'], bool):
                errors.append(f"{rule_prefix}: 'enabled' must be a boolean")
            
            # Validate priority
            if 'priority' in rule:
                priority = rule['priority']
                if not isinstance(priority, int) or priority < 1 or priority > 100:
                    errors.append(f"{rule_prefix}: 'priority' must be an integer between 1 and 100")
                else:
                    priorities.append(priority)
            
            # Validate conditions
            if 'conditions' in rule:
                conditions_result = await self.validate_rule_conditions(rule['conditions'], rule_prefix)
                errors.extend(conditions_result.errors)
                warnings.extend(conditions_result.warnings)
                suggestions.extend(conditions_result.suggestions)
            
            # Validate metadata
            if 'metadata' in rule:
                metadata_result = self._validate_rule_metadata(rule['metadata'], rule_prefix)
                errors.extend(metadata_result.errors)
                warnings.extend(metadata_result.warnings)
        
        # Check for duplicate priorities
        if len(priorities) != len(set(priorities)):
            suggestions.append("Consider using unique priorities for better rule ordering")
        
        # Check for rule coverage
        if not rules:
            warnings.append("No rules defined - team will not receive notifications")
        elif all(not rule.get('enabled', True) for rule in rules):
            warnings.append("All rules are disabled - team will not receive notifications")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_hook_types(self, hook_types: Any, rule_prefix: str) -> ValidationResult:
        """Validate hook types in a rule."""
        errors = []
        warnings = []
        
        if not isinstance(hook_types, list):
            errors.append(f"{rule_prefix}: 'hook_types' must be a list")
            return ValidationResult(valid=False, errors=errors)
        
        if not hook_types:
            errors.append(f"{rule_prefix}: 'hook_types' cannot be empty")
            return ValidationResult(valid=False, errors=errors)
        
        for hook_type in hook_types:
            if not isinstance(hook_type, str):
                errors.append(f"{rule_prefix}: Hook type must be a string, got {type(hook_type)}")
            elif hook_type not in self._valid_hook_types:
                errors.append(f"{rule_prefix}: Invalid hook type '{hook_type}'. Valid types: {', '.join(sorted(self._valid_hook_types))}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def validate_rule_conditions(self, conditions: Dict[str, Any], rule_prefix: str) -> ValidationResult:
        """
        Validate rule conditions with comprehensive field and operator checking.
        
        Args:
            conditions: Conditions dictionary to validate
            rule_prefix: Prefix for error messages
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        suggestions = []
        
        if not isinstance(conditions, dict):
            errors.append(f"{rule_prefix}: Conditions must be a dictionary")
            return ValidationResult(valid=False, errors=errors)
        
        # Validate logic operator
        logic = conditions.get('logic', 'and')
        if logic not in ['and', 'or']:
            errors.append(f"{rule_prefix}: Logic must be 'and' or 'or', got '{logic}'")
        
        # Validate conditions list
        condition_list = conditions.get('conditions', [])
        if not isinstance(condition_list, list):
            errors.append(f"{rule_prefix}: 'conditions' must be a list")
            return ValidationResult(valid=False, errors=errors)
        
        if not condition_list:
            errors.append(f"{rule_prefix}: 'conditions' list cannot be empty")
            return ValidationResult(valid=False, errors=errors)
        
        for j, condition in enumerate(condition_list):
            cond_prefix = f"{rule_prefix}, condition {j + 1}"
            
            if not isinstance(condition, dict):
                errors.append(f"{cond_prefix}: Must be a dictionary")
                continue
            
            # Check for nested logic
            if 'logic' in condition:
                nested_result = await self.validate_rule_conditions(condition, cond_prefix)
                errors.extend(nested_result.errors)
                warnings.extend(nested_result.warnings)
                suggestions.extend(nested_result.suggestions)
            else:
                # Validate field condition
                field_result = self._validate_field_condition(condition, cond_prefix)
                errors.extend(field_result.errors)
                warnings.extend(field_result.warnings)
                suggestions.extend(field_result.suggestions)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_field_condition(self, condition: Dict[str, Any], cond_prefix: str) -> ValidationResult:
        """Validate a single field condition."""
        errors = []
        warnings = []
        suggestions = []
        
        # Validate field
        if 'field' not in condition:
            errors.append(f"{cond_prefix}: Missing 'field'")
            return ValidationResult(valid=False, errors=errors)
        
        field = condition['field']
        if not isinstance(field, str):
            errors.append(f"{cond_prefix}: 'field' must be a string")
            return ValidationResult(valid=False, errors=errors)
        
        # Check if field is defined
        if field not in self._field_definitions:
            warnings.append(f"{cond_prefix}: Unknown field '{field}'. This may cause runtime errors.")
            suggestions.append(f"Available fields: {', '.join(sorted(self._field_definitions.keys()))}")
        else:
            field_def = self._field_definitions[field]
            
            # Validate operator
            if 'operator' not in condition:
                errors.append(f"{cond_prefix}: Missing 'operator'")
            else:
                operator = condition['operator']
                if not isinstance(operator, str):
                    errors.append(f"{cond_prefix}: 'operator' must be a string")
                elif operator not in self._operator_definitions:
                    errors.append(f"{cond_prefix}: Invalid operator '{operator}'. Valid operators: {', '.join(sorted(self._operator_definitions.keys()))}")
                elif operator not in field_def.valid_operators:
                    errors.append(f"{cond_prefix}: Operator '{operator}' is not valid for field '{field}'. Valid operators: {', '.join(field_def.valid_operators)}")
                else:
                    operator_def = self._operator_definitions[operator]
                    
                    # Validate value requirement
                    if operator_def.requires_value and 'value' not in condition:
                        errors.append(f"{cond_prefix}: Operator '{operator}' requires a 'value'")
                    elif not operator_def.requires_value and 'value' in condition:
                        warnings.append(f"{cond_prefix}: Operator '{operator}' does not require a 'value'")
                    
                    # Validate value type compatibility
                    if 'value' in condition:
                        value_result = self._validate_condition_value(
                            condition['value'], field_def, operator_def, cond_prefix
                        )
                        errors.extend(value_result.errors)
                        warnings.extend(value_result.warnings)
                        suggestions.extend(value_result.suggestions)
        
        # Validate case_sensitive option
        if 'case_sensitive' in condition:
            if not isinstance(condition['case_sensitive'], bool):
                errors.append(f"{cond_prefix}: 'case_sensitive' must be a boolean")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_condition_value(
        self, 
        value: Any, 
        field_def: FieldDefinition, 
        operator_def: OperatorDefinition, 
        cond_prefix: str
    ) -> ValidationResult:
        """Validate condition value against field and operator definitions."""
        errors = []
        warnings = []
        suggestions = []
        
        # Check if operator supports field type
        if field_def.data_type not in operator_def.valid_types:
            errors.append(f"{cond_prefix}: Operator '{operator_def.name}' does not support field type '{field_def.data_type}'")
            return ValidationResult(valid=False, errors=errors)
        
        # Validate value based on operator
        if operator_def.name in ['in', 'not_in']:
            if not isinstance(value, list):
                errors.append(f"{cond_prefix}: Value for '{operator_def.name}' operator must be a list")
            elif not value:
                warnings.append(f"{cond_prefix}: Empty list for '{operator_def.name}' operator")
        
        elif operator_def.name == 'regex':
            if not isinstance(value, str):
                errors.append(f"{cond_prefix}: Value for 'regex' operator must be a string")
            else:
                # Validate regex syntax
                try:
                    re.compile(value)
                except re.error as e:
                    errors.append(f"{cond_prefix}: Invalid regex pattern: {e}")
        
        elif operator_def.name in ['greater_than', 'less_than']:
            if not isinstance(value, (int, float)):
                errors.append(f"{cond_prefix}: Value for '{operator_def.name}' operator must be a number")
        
        # Provide suggestions based on field examples
        if field_def.example_values and isinstance(value, str):
            if value not in field_def.example_values and not any(example in str(value) for example in field_def.example_values):
                suggestions.append(f"{cond_prefix}: Consider using example values: {', '.join(map(str, field_def.example_values))}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_rule_metadata(self, metadata: Any, rule_prefix: str) -> ValidationResult:
        """Validate rule metadata."""
        errors = []
        warnings = []
        
        if not isinstance(metadata, dict):
            errors.append(f"{rule_prefix}: 'metadata' must be a dictionary")
            return ValidationResult(valid=False, errors=errors)
        
        # Validate channels
        if 'channels' in metadata:
            channels = metadata['channels']
            if not isinstance(channels, list):
                errors.append(f"{rule_prefix}: 'metadata.channels' must be a list")
            else:
                for channel in channels:
                    if not isinstance(channel, str):
                        errors.append(f"{rule_prefix}: Channel must be a string, got {type(channel)}")
                    elif not channel.startswith('#'):
                        warnings.append(f"{rule_prefix}: Channel '{channel}' should start with '#'")
                    elif not re.match(r'^#[a-z0-9_-]+$', channel.lower()):
                        warnings.append(f"{rule_prefix}: Channel '{channel}' may not be a valid Slack channel name")
        
        # Validate urgency_override
        if 'urgency_override' in metadata:
            urgency = metadata['urgency_override']
            valid_urgencies = ['critical', 'high', 'medium', 'low']
            if urgency not in valid_urgencies:
                errors.append(f"{rule_prefix}: Invalid 'urgency_override' '{urgency}'. Valid values: {', '.join(valid_urgencies)}")
        
        # Validate escalation_enabled
        if 'escalation_enabled' in metadata:
            if not isinstance(metadata['escalation_enabled'], bool):
                errors.append(f"{rule_prefix}: 'escalation_enabled' must be a boolean")
        
        # Validate ignore_quiet_hours
        if 'ignore_quiet_hours' in metadata:
            if not isinstance(metadata['ignore_quiet_hours'], bool):
                errors.append(f"{rule_prefix}: 'ignore_quiet_hours' must be a boolean")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def get_field_suggestions(self, partial_field: str) -> List[str]:
        """Get field suggestions based on partial input."""
        partial_lower = partial_field.lower()
        suggestions = []
        
        for field_name in self._field_definitions:
            if partial_lower in field_name.lower():
                suggestions.append(field_name)
        
        return sorted(suggestions)
    
    def get_operator_suggestions(self, field_name: str) -> List[str]:
        """Get valid operators for a specific field."""
        if field_name in self._field_definitions:
            return self._field_definitions[field_name].valid_operators
        return list(self._operator_definitions.keys())
    
    def get_validation_help(self) -> Dict[str, Any]:
        """Get comprehensive validation help information."""
        return {
            'fields': {
                name: {
                    'data_type': field_def.data_type,
                    'description': field_def.description,
                    'valid_operators': field_def.valid_operators,
                    'example_values': field_def.example_values
                }
                for name, field_def in self._field_definitions.items()
            },
            'operators': {
                name: {
                    'description': op_def.description,
                    'valid_types': op_def.valid_types,
                    'requires_value': op_def.requires_value,
                    'example': op_def.example
                }
                for name, op_def in self._operator_definitions.items()
            },
            'hook_types': list(self._valid_hook_types),
            'examples': {
                'simple_condition': {
                    'field': 'ticket.priority.name',
                    'operator': 'equals',
                    'value': 'High'
                },
                'list_condition': {
                    'field': 'ticket.priority.name',
                    'operator': 'in',
                    'value': ['High', 'Critical']
                },
                'regex_condition': {
                    'field': 'ticket.summary',
                    'operator': 'regex',
                    'value': '\\b(urgent|critical)\\b',
                    'case_sensitive': False
                },
                'nested_conditions': {
                    'logic': 'and',
                    'conditions': [
                        {
                            'field': 'ticket.priority.name',
                            'operator': 'equals',
                            'value': 'High'
                        },
                        {
                            'logic': 'or',
                            'conditions': [
                                {
                                    'field': 'ticket.status.name',
                                    'operator': 'equals',
                                    'value': 'Blocked'
                                },
                                {
                                    'field': 'ticket.labels',
                                    'operator': 'contains',
                                    'value': 'urgent'
                                }
                            ]
                        }
                    ]
                }
            }
        }