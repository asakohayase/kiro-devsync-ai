"""
Hook Rule Engine for team-specific filtering.

This module provides the HookRuleEngine class that evaluates team-specific rules
and conditions to determine if Agent Hooks should execute for given JIRA events.
It supports complex rule evaluation, team configuration loading, and caching.
"""

import logging
import re
import yaml
from datetime import datetime, timezone, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .agent_hooks import (
    EnrichedEvent,
    EventCategory,
    UrgencyLevel,
    SignificanceLevel,
    EventClassification,
    Stakeholder
)


logger = logging.getLogger(__name__)


class RuleOperator(Enum):
    """Operators for rule conditions."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"


class RuleLogic(Enum):
    """Logic operators for combining rule conditions."""
    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class RuleCondition:
    """Represents a single rule condition."""
    field: str
    operator: RuleOperator
    value: Union[str, int, float, List[Any]]
    case_sensitive: bool = True
    
    def __post_init__(self):
        """Validate condition after initialization."""
        if isinstance(self.operator, str):
            self.operator = RuleOperator(self.operator)


@dataclass
class RuleGroup:
    """Represents a group of conditions with logic operators."""
    conditions: List[Union[RuleCondition, 'RuleGroup']]
    logic: RuleLogic = RuleLogic.AND
    
    def __post_init__(self):
        """Validate rule group after initialization."""
        if isinstance(self.logic, str):
            self.logic = RuleLogic(self.logic)


@dataclass
class HookRule:
    """Represents a complete hook rule with metadata."""
    rule_id: str
    name: str
    description: str
    hook_types: List[str]
    conditions: RuleGroup
    enabled: bool = True
    priority: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TeamRuleSet:
    """Represents a complete set of rules for a team."""
    team_id: str
    team_name: str
    rules: List[HookRule]
    default_channels: Dict[str, str] = field(default_factory=dict)
    notification_preferences: Dict[str, Any] = field(default_factory=dict)
    escalation_rules: List[Dict[str, Any]] = field(default_factory=list)
    business_hours: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    version: str = "1.0.0"
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RuleEvaluationResult:
    """Result of rule evaluation."""
    matched: bool
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    hook_types: List[str] = field(default_factory=list)
    channels: List[str] = field(default_factory=list)
    urgency_override: Optional[UrgencyLevel] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    evaluation_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of rule validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class HookRuleEngine:
    """
    Engine for evaluating team-specific hook rules and filtering events.
    
    Provides comprehensive rule evaluation, team configuration management,
    and caching for optimal performance.
    """
    
    # Supported field paths for rule conditions
    SUPPORTED_FIELDS = {
        'event.event_type',
        'event.ticket_key',
        'event.project_key',
        'event.classification.category',
        'event.classification.urgency',
        'event.classification.significance',
        'event.classification.keywords',
        'event.classification.affected_teams',
        'ticket.summary',
        'ticket.description',
        'ticket.status.name',
        'ticket.status.category',
        'ticket.priority.name',
        'ticket.issue_type.name',
        'ticket.assignee.display_name',
        'ticket.assignee.user_id',
        'ticket.reporter.display_name',
        'ticket.reporter.user_id',
        'ticket.labels',
        'ticket.components',
        'ticket.fix_versions',
        'stakeholders.roles',
        'stakeholders.user_ids',
        'stakeholders.display_names',
        'context.processed_at',
        'context.event_source',
        'routing_hints.priority',
        'routing_hints.status',
        'routing_hints.assignee'
    }
    
    # Time-based field patterns
    TIME_FIELDS = {
        'context.processed_at',
        'event.timestamp',
        'ticket.created',
        'ticket.updated'
    }
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the Hook Rule Engine.
        
        Args:
            config_dir: Directory containing team configuration files
        """
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self._team_rules_cache: Dict[str, TeamRuleSet] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Metrics tracking
        self._evaluations_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._validation_errors = 0
        
        logger.info(f"HookRuleEngine initialized with config_dir: {self.config_dir}")
    
    async def evaluate_rules(
        self, 
        event: EnrichedEvent, 
        team_id: str,
        hook_types: Optional[List[str]] = None
    ) -> RuleEvaluationResult:
        """
        Evaluate team rules against an enriched event.
        
        Args:
            event: The enriched JIRA event to evaluate
            team_id: Team identifier for rule lookup
            hook_types: Optional list of hook types to filter rules
            
        Returns:
            Rule evaluation result with match status and metadata
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Load team rules
            team_rules = await self.load_team_rules(team_id)
            if not team_rules or not team_rules.enabled:
                return RuleEvaluationResult(
                    matched=False,
                    errors=[f"No rules found or team disabled for team: {team_id}"]
                )
            
            # Filter rules by hook types if specified
            applicable_rules = team_rules.rules
            if hook_types:
                applicable_rules = [
                    rule for rule in team_rules.rules
                    if any(hook_type in rule.hook_types for hook_type in hook_types)
                ]
            
            # Evaluate rules in priority order
            applicable_rules.sort(key=lambda r: r.priority, reverse=True)
            
            evaluation_errors = []
            
            for rule in applicable_rules:
                if not rule.enabled:
                    continue
                
                try:
                    if await self._evaluate_rule_group(rule.conditions, event):
                        # Rule matched - prepare result
                        channels = self._determine_channels(rule, team_rules, event)
                        urgency_override = self._determine_urgency_override(rule, event)
                        
                        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                        self._evaluations_count += 1
                        
                        logger.debug(
                            f"Rule matched: {rule.rule_id} for event {event.event_id} "
                            f"in {processing_time:.2f}ms"
                        )
                        
                        return RuleEvaluationResult(
                            matched=True,
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            hook_types=rule.hook_types,
                            channels=channels,
                            urgency_override=urgency_override,
                            metadata={
                                'rule_priority': rule.priority,
                                'rule_description': rule.description,
                                'team_id': team_id,
                                'evaluation_order': applicable_rules.index(rule)
                            },
                            evaluation_time_ms=processing_time
                        )
                
                except Exception as e:
                    error_msg = f"Error evaluating rule {rule.rule_id}: {e}"
                    logger.error(error_msg)
                    evaluation_errors.append(error_msg)
                    continue
            
            # No rules matched
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self._evaluations_count += 1
            
            return RuleEvaluationResult(
                matched=False,
                metadata={'evaluated_rules': len(applicable_rules)},
                evaluation_time_ms=processing_time,
                errors=evaluation_errors
            )
            
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.error(f"Error evaluating rules for team {team_id}: {e}", exc_info=True)
            
            return RuleEvaluationResult(
                matched=False,
                errors=[f"Rule evaluation error: {str(e)}"],
                evaluation_time_ms=processing_time
            )
    
    async def load_team_rules(self, team_id: str) -> Optional[TeamRuleSet]:
        """
        Load team rules from configuration, with caching.
        
        Args:
            team_id: Team identifier
            
        Returns:
            Team rule set or None if not found
        """
        # Check cache first
        if self._is_cache_valid(team_id):
            self._cache_hits += 1
            return self._team_rules_cache.get(team_id)
        
        self._cache_misses += 1
        
        try:
            # Try to load from YAML file
            config_file = self.config_dir / f"team_{team_id}_hooks.yaml"
            if not config_file.exists():
                # Try alternative naming
                config_file = self.config_dir / f"{team_id}_hook_config.yaml"
                if not config_file.exists():
                    logger.warning(f"No hook configuration found for team: {team_id}")
                    return None
            
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Parse configuration into TeamRuleSet
            team_rules = await self._parse_team_configuration(team_id, config_data)
            
            # Cache the result
            self._team_rules_cache[team_id] = team_rules
            self._cache_timestamps[team_id] = datetime.now(timezone.utc)
            
            logger.debug(f"Loaded {len(team_rules.rules)} rules for team: {team_id}")
            return team_rules
            
        except Exception as e:
            logger.error(f"Error loading team rules for {team_id}: {e}", exc_info=True)
            return None
    
    async def validate_rule_syntax(self, rules: Dict[str, Any]) -> ValidationResult:
        """
        Validate rule syntax and structure.
        
        Args:
            rules: Rule configuration dictionary
            
        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []
        
        try:
            # Validate top-level structure
            if not isinstance(rules, dict):
                errors.append("Rules must be a dictionary")
                return ValidationResult(valid=False, errors=errors)
            
            # Validate team information
            if 'team_id' not in rules:
                errors.append("Missing required field: team_id")
            elif not isinstance(rules['team_id'], str):
                errors.append("team_id must be a string")
            
            if 'team_name' not in rules:
                warnings.append("Missing team_name field")
            
            # Validate rules array
            if 'rules' not in rules:
                errors.append("Missing required field: rules")
                return ValidationResult(valid=False, errors=errors, warnings=warnings)
            
            if not isinstance(rules['rules'], list):
                errors.append("rules must be a list")
                return ValidationResult(valid=False, errors=errors, warnings=warnings)
            
            # Validate individual rules
            for i, rule in enumerate(rules['rules']):
                rule_errors = await self._validate_single_rule(rule, f"rules[{i}]")
                errors.extend(rule_errors)
            
            # Validate optional fields
            if 'default_channels' in rules and not isinstance(rules['default_channels'], dict):
                warnings.append("default_channels should be a dictionary")
            
            if 'business_hours' in rules:
                business_hours_errors = self._validate_business_hours(rules['business_hours'])
                warnings.extend(business_hours_errors)
            
            is_valid = len(errors) == 0
            
            logger.debug(
                f"Rule validation completed: valid={is_valid}, "
                f"errors={len(errors)}, warnings={len(warnings)}"
            )
            
            return ValidationResult(
                valid=is_valid,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error during rule validation: {e}", exc_info=True)
            return ValidationResult(
                valid=False,
                errors=[f"Validation error: {str(e)}"]
            )
    
    async def _evaluate_rule_group(self, rule_group: RuleGroup, event: EnrichedEvent) -> bool:
        """
        Evaluate a rule group against an event.
        
        Args:
            rule_group: The rule group to evaluate
            event: The event to evaluate against
            
        Returns:
            True if the rule group matches, False otherwise
        """
        if not rule_group.conditions:
            return True  # Empty conditions always match
        
        results = []
        
        for condition in rule_group.conditions:
            if isinstance(condition, RuleCondition):
                result = await self._evaluate_condition(condition, event)
            elif isinstance(condition, RuleGroup):
                result = await self._evaluate_rule_group(condition, event)
            else:
                logger.warning(f"Unknown condition type: {type(condition)}")
                result = False
            
            results.append(result)
        
        # Apply logic operator
        if rule_group.logic == RuleLogic.AND:
            return all(results)
        elif rule_group.logic == RuleLogic.OR:
            return any(results)
        elif rule_group.logic == RuleLogic.NOT:
            # NOT logic applies to the first condition only
            return not results[0] if results else True
        
        return False
    
    async def _evaluate_condition(self, condition: RuleCondition, event: EnrichedEvent) -> bool:
        """
        Evaluate a single condition against an event.
        
        Args:
            condition: The condition to evaluate
            event: The event to evaluate against
            
        Returns:
            True if the condition matches, False otherwise
        """
        try:
            # Extract field value from event
            field_value = self._extract_field_value(condition.field, event)
            
            # Handle None values
            if field_value is None:
                return condition.operator in [RuleOperator.NOT_EQUALS, RuleOperator.NOT_IN, RuleOperator.NOT_CONTAINS]
            
            # Apply operator
            return self._apply_operator(condition.operator, field_value, condition.value, condition.case_sensitive)
            
        except Exception as e:
            logger.error(f"Error evaluating condition {condition.field}: {e}")
            # Re-raise the exception to be caught at the rule level
            raise
    
    def _extract_field_value(self, field_path: str, event: EnrichedEvent) -> Any:
        """
        Extract field value from event using dot notation.
        
        Args:
            field_path: Dot-separated field path (e.g., 'ticket.status.name')
            event: The event to extract from
            
        Returns:
            The extracted field value or None if not found
        """
        try:
            # Build context object for field extraction
            context = {
                'event': {
                    'event_id': event.event_id,
                    'event_type': event.event_type,
                    'timestamp': event.timestamp,
                    'ticket_key': event.ticket_key,
                    'project_key': event.project_key,
                    'classification': {
                        'category': event.classification.category.value if event.classification else None,
                        'urgency': event.classification.urgency.value if event.classification else None,
                        'significance': event.classification.significance.value if event.classification else None,
                        'keywords': event.classification.keywords if event.classification else [],
                        'affected_teams': event.classification.affected_teams if event.classification else []
                    }
                },
                'ticket': event.ticket_details or {},
                'stakeholders': {
                    'roles': [s.role for s in event.stakeholders],
                    'user_ids': [s.user_id for s in event.stakeholders],
                    'display_names': [s.display_name for s in event.stakeholders]
                },
                'context': event.context_data,
                'routing_hints': event.classification.routing_hints if event.classification else {}
            }
            
            # Navigate through the field path
            current_value = context
            for part in field_path.split('.'):
                if isinstance(current_value, dict):
                    current_value = current_value.get(part)
                elif isinstance(current_value, list) and part.isdigit():
                    index = int(part)
                    current_value = current_value[index] if 0 <= index < len(current_value) else None
                else:
                    return None
                
                if current_value is None:
                    break
            
            return current_value
            
        except Exception as e:
            logger.error(f"Error extracting field {field_path}: {e}")
            return None
    
    def _apply_operator(
        self, 
        operator: RuleOperator, 
        field_value: Any, 
        condition_value: Any,
        case_sensitive: bool = True
    ) -> bool:
        """
        Apply operator to compare field value with condition value.
        
        Args:
            operator: The comparison operator
            field_value: Value from the event
            condition_value: Value from the condition
            case_sensitive: Whether string comparisons should be case sensitive
            
        Returns:
            True if the comparison matches, False otherwise
        """
        try:
            # Handle string case sensitivity
            if isinstance(field_value, str) and isinstance(condition_value, str) and not case_sensitive:
                field_value = field_value.lower()
                condition_value = condition_value.lower()
            elif isinstance(field_value, str) and isinstance(condition_value, list) and not case_sensitive:
                field_value = field_value.lower()
                condition_value = [v.lower() if isinstance(v, str) else v for v in condition_value]
            
            # Apply operators
            if operator == RuleOperator.EQUALS:
                return field_value == condition_value
            
            elif operator == RuleOperator.NOT_EQUALS:
                return field_value != condition_value
            
            elif operator == RuleOperator.IN:
                if not isinstance(condition_value, list):
                    condition_value = [condition_value]
                return field_value in condition_value
            
            elif operator == RuleOperator.NOT_IN:
                if not isinstance(condition_value, list):
                    condition_value = [condition_value]
                return field_value not in condition_value
            
            elif operator == RuleOperator.CONTAINS:
                if isinstance(field_value, str):
                    return str(condition_value) in field_value
                elif isinstance(field_value, list):
                    return condition_value in field_value
                return False
            
            elif operator == RuleOperator.NOT_CONTAINS:
                if isinstance(field_value, str):
                    return str(condition_value) not in field_value
                elif isinstance(field_value, list):
                    return condition_value not in field_value
                return True
            
            elif operator == RuleOperator.STARTS_WITH:
                return isinstance(field_value, str) and field_value.startswith(str(condition_value))
            
            elif operator == RuleOperator.ENDS_WITH:
                return isinstance(field_value, str) and field_value.endswith(str(condition_value))
            
            elif operator == RuleOperator.REGEX:
                if not isinstance(field_value, str):
                    return False
                pattern = re.compile(str(condition_value), re.IGNORECASE if not case_sensitive else 0)
                return bool(pattern.search(field_value))
            
            elif operator == RuleOperator.GREATER_THAN:
                return self._numeric_compare(field_value, condition_value, lambda a, b: a > b)
            
            elif operator == RuleOperator.LESS_THAN:
                return self._numeric_compare(field_value, condition_value, lambda a, b: a < b)
            
            elif operator == RuleOperator.GREATER_EQUAL:
                return self._numeric_compare(field_value, condition_value, lambda a, b: a >= b)
            
            elif operator == RuleOperator.LESS_EQUAL:
                return self._numeric_compare(field_value, condition_value, lambda a, b: a <= b)
            
            return False
            
        except Exception as e:
            logger.error(f"Error applying operator {operator}: {e}")
            return False
    
    def _numeric_compare(self, field_value: Any, condition_value: Any, comparator) -> bool:
        """Helper method for numeric comparisons."""
        try:
            # Convert to numbers if possible
            if isinstance(field_value, str) and field_value.isdigit():
                field_value = float(field_value)
            if isinstance(condition_value, str) and condition_value.isdigit():
                condition_value = float(condition_value)
            
            if not isinstance(field_value, (int, float)) or not isinstance(condition_value, (int, float)):
                return False
            
            return comparator(field_value, condition_value)
            
        except (ValueError, TypeError):
            return False
    
    async def _parse_team_configuration(self, team_id: str, config_data: Dict[str, Any]) -> TeamRuleSet:
        """
        Parse team configuration data into TeamRuleSet.
        
        Args:
            team_id: Team identifier
            config_data: Raw configuration data
            
        Returns:
            Parsed team rule set
        """
        rules = []
        
        # Parse rules
        for rule_data in config_data.get('rules', []):
            rule = await self._parse_rule(rule_data)
            if rule:
                rules.append(rule)
        
        return TeamRuleSet(
            team_id=team_id,
            team_name=config_data.get('team_name', team_id),
            rules=rules,
            default_channels=config_data.get('default_channels', {}),
            notification_preferences=config_data.get('notification_preferences', {}),
            escalation_rules=config_data.get('escalation_rules', []),
            business_hours=config_data.get('business_hours', {}),
            enabled=config_data.get('enabled', True),
            version=config_data.get('version', '1.0.0')
        )
    
    async def _parse_rule(self, rule_data: Dict[str, Any]) -> Optional[HookRule]:
        """
        Parse a single rule from configuration data.
        
        Args:
            rule_data: Raw rule data
            
        Returns:
            Parsed hook rule or None if invalid
        """
        try:
            conditions = await self._parse_rule_group(rule_data.get('conditions', {}))
            
            return HookRule(
                rule_id=rule_data.get('rule_id', f"rule_{hash(str(rule_data))}"),
                name=rule_data.get('name', 'Unnamed Rule'),
                description=rule_data.get('description', ''),
                hook_types=rule_data.get('hook_types', []),
                conditions=conditions,
                enabled=rule_data.get('enabled', True),
                priority=rule_data.get('priority', 0),
                metadata=rule_data.get('metadata', {})
            )
            
        except Exception as e:
            logger.error(f"Error parsing rule: {e}")
            return None
    
    async def _parse_rule_group(self, group_data: Dict[str, Any]) -> RuleGroup:
        """
        Parse rule group from configuration data.
        
        Args:
            group_data: Raw rule group data
            
        Returns:
            Parsed rule group
        """
        conditions = []
        
        # Handle different condition formats
        if 'conditions' in group_data:
            for condition_data in group_data['conditions']:
                if 'field' in condition_data:
                    # Single condition
                    condition = RuleCondition(
                        field=condition_data['field'],
                        operator=RuleOperator(condition_data.get('operator', 'equals')),
                        value=condition_data['value'],
                        case_sensitive=condition_data.get('case_sensitive', True)
                    )
                    conditions.append(condition)
                else:
                    # Nested rule group
                    nested_group = await self._parse_rule_group(condition_data)
                    conditions.append(nested_group)
        
        # Handle direct field conditions (simplified format)
        for key, value in group_data.items():
            if key not in ['logic', 'conditions'] and key in self.SUPPORTED_FIELDS:
                condition = RuleCondition(
                    field=key,
                    operator=RuleOperator.EQUALS,
                    value=value
                )
                conditions.append(condition)
        
        return RuleGroup(
            conditions=conditions,
            logic=RuleLogic(group_data.get('logic', 'and'))
        )
    
    async def _validate_single_rule(self, rule: Dict[str, Any], context: str) -> List[str]:
        """
        Validate a single rule configuration.
        
        Args:
            rule: Rule configuration
            context: Context for error messages
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Required fields
        if 'name' not in rule:
            errors.append(f"{context}: Missing required field 'name'")
        
        if 'hook_types' not in rule:
            errors.append(f"{context}: Missing required field 'hook_types'")
        elif not isinstance(rule['hook_types'], list):
            errors.append(f"{context}: 'hook_types' must be a list")
        
        # Validate conditions
        if 'conditions' in rule:
            condition_errors = await self._validate_conditions(rule['conditions'], f"{context}.conditions")
            errors.extend(condition_errors)
        
        # Validate optional fields
        if 'priority' in rule and not isinstance(rule['priority'], int):
            errors.append(f"{context}: 'priority' must be an integer")
        
        if 'enabled' in rule and not isinstance(rule['enabled'], bool):
            errors.append(f"{context}: 'enabled' must be a boolean")
        
        return errors
    
    async def _validate_conditions(self, conditions: Dict[str, Any], context: str) -> List[str]:
        """
        Validate rule conditions.
        
        Args:
            conditions: Conditions configuration
            context: Context for error messages
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not isinstance(conditions, dict):
            errors.append(f"{context}: Conditions must be a dictionary")
            return errors
        
        # Validate logic operator
        if 'logic' in conditions:
            try:
                RuleLogic(conditions['logic'])
            except ValueError:
                errors.append(f"{context}: Invalid logic operator '{conditions['logic']}'")
        
        # Validate individual conditions
        if 'conditions' in conditions:
            if not isinstance(conditions['conditions'], list):
                errors.append(f"{context}: 'conditions' must be a list")
            else:
                for i, condition in enumerate(conditions['conditions']):
                    if 'field' in condition:
                        # Single condition
                        field_errors = self._validate_condition_field(condition, f"{context}[{i}]")
                        errors.extend(field_errors)
                    else:
                        # Nested conditions
                        nested_errors = await self._validate_conditions(condition, f"{context}[{i}]")
                        errors.extend(nested_errors)
        
        return errors
    
    def _validate_condition_field(self, condition: Dict[str, Any], context: str) -> List[str]:
        """
        Validate a single condition field.
        
        Args:
            condition: Condition configuration
            context: Context for error messages
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Required fields
        if 'field' not in condition:
            errors.append(f"{context}: Missing required field 'field'")
        elif condition['field'] not in self.SUPPORTED_FIELDS:
            errors.append(f"{context}: Unsupported field '{condition['field']}'")
        
        if 'value' not in condition:
            errors.append(f"{context}: Missing required field 'value'")
        
        # Validate operator
        if 'operator' in condition:
            try:
                RuleOperator(condition['operator'])
            except ValueError:
                errors.append(f"{context}: Invalid operator '{condition['operator']}'")
        
        return errors
    
    def _validate_business_hours(self, business_hours: Dict[str, Any]) -> List[str]:
        """
        Validate business hours configuration.
        
        Args:
            business_hours: Business hours configuration
            
        Returns:
            List of validation warnings
        """
        warnings = []
        
        if not isinstance(business_hours, dict):
            warnings.append("business_hours should be a dictionary")
            return warnings
        
        # Validate time format
        for time_field in ['start', 'end']:
            if time_field in business_hours:
                try:
                    time.fromisoformat(business_hours[time_field])
                except ValueError:
                    warnings.append(f"Invalid time format for {time_field}: {business_hours[time_field]}")
        
        # Validate days
        if 'days' in business_hours:
            if not isinstance(business_hours['days'], list):
                warnings.append("business_hours.days should be a list")
            else:
                valid_days = {'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'}
                for day in business_hours['days']:
                    if day.lower() not in valid_days:
                        warnings.append(f"Invalid day: {day}")
        
        return warnings
    
    def _determine_channels(self, rule: HookRule, team_rules: TeamRuleSet, event: EnrichedEvent) -> List[str]:
        """
        Determine notification channels for a matched rule.
        
        Args:
            rule: The matched rule
            team_rules: Team rule set
            event: The event being processed
            
        Returns:
            List of channel identifiers
        """
        channels = []
        
        # Rule-specific channels
        if 'channels' in rule.metadata:
            channels.extend(rule.metadata['channels'])
        
        # Team default channels
        for hook_type in rule.hook_types:
            if hook_type in team_rules.default_channels:
                channels.append(team_rules.default_channels[hook_type])
        
        # Fallback to general channel
        if not channels and 'general' in team_rules.default_channels:
            channels.append(team_rules.default_channels['general'])
        
        return list(set(channels))  # Remove duplicates
    
    def _determine_urgency_override(self, rule: HookRule, event: EnrichedEvent) -> Optional[UrgencyLevel]:
        """
        Determine if rule should override event urgency.
        
        Args:
            rule: The matched rule
            event: The event being processed
            
        Returns:
            Urgency level override or None
        """
        if 'urgency_override' in rule.metadata:
            try:
                return UrgencyLevel(rule.metadata['urgency_override'])
            except ValueError:
                logger.warning(f"Invalid urgency override in rule {rule.rule_id}")
        
        return None
    
    def _is_cache_valid(self, team_id: str) -> bool:
        """Check if cached team rules are still valid."""
        if team_id not in self._cache_timestamps:
            return False
        
        cache_age = datetime.now(timezone.utc) - self._cache_timestamps[team_id]
        return cache_age.total_seconds() < self._cache_ttl
    
    def clear_cache(self, team_id: Optional[str] = None):
        """
        Clear rule cache.
        
        Args:
            team_id: Specific team to clear, or None to clear all
        """
        if team_id:
            self._team_rules_cache.pop(team_id, None)
            self._cache_timestamps.pop(team_id, None)
        else:
            self._team_rules_cache.clear()
            self._cache_timestamps.clear()
        
        logger.debug(f"Cleared rule cache for team: {team_id or 'all'}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get rule engine metrics."""
        return {
            'evaluations_count': self._evaluations_count,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate': self._cache_hits / max(self._cache_hits + self._cache_misses, 1),
            'validation_errors': self._validation_errors,
            'cached_teams': len(self._team_rules_cache)
        }
    
    def reset_metrics(self):
        """Reset rule engine metrics."""
        self._evaluations_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._validation_errors = 0