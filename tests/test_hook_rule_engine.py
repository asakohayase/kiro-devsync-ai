"""
Tests for Hook Rule Engine.

This module provides comprehensive tests for the HookRuleEngine class,
covering rule evaluation, team configuration loading, validation,
and edge cases.
"""

import pytest
import yaml
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from devsync_ai.core.hook_rule_engine import (
    HookRuleEngine,
    RuleOperator,
    RuleLogic,
    RuleCondition,
    RuleGroup,
    HookRule,
    TeamRuleSet,
    RuleEvaluationResult,
    ValidationResult
)
from devsync_ai.core.agent_hooks import (
    EnrichedEvent,
    ProcessedEvent,
    EventCategory,
    UrgencyLevel,
    SignificanceLevel,
    EventClassification,
    Stakeholder
)


class TestHookRuleEngine:
    """Test cases for HookRuleEngine."""
    
    @pytest.fixture
    def sample_event(self):
        """Create a sample enriched event for testing."""
        classification = EventClassification(
            category=EventCategory.STATUS_CHANGE,
            urgency=UrgencyLevel.HIGH,
            significance=SignificanceLevel.MAJOR,
            affected_teams=['engineering'],
            routing_hints={'priority': 'High', 'status': 'In Progress'},
            keywords=['bug', 'critical']
        )
        
        stakeholders = [
            Stakeholder(
                user_id='user123',
                display_name='John Doe',
                email='john@example.com',
                role='assignee',
                team_id='engineering'
            )
        ]
        
        ticket_details = {
            'key': 'PROJ-123',
            'summary': 'Critical bug in payment system',
            'status': {'name': 'In Progress', 'category': 'In Progress'},
            'priority': {'name': 'High'},
            'issue_type': {'name': 'Bug'},
            'assignee': {'display_name': 'John Doe', 'user_id': 'user123'},
            'labels': ['critical', 'payment'],
            'components': ['payment-service']
        }
        
        return EnrichedEvent(
            event_id='event123',
            event_type='jira:issue_updated',
            timestamp=datetime.now(timezone.utc),
            jira_event_data={'fields': ticket_details},
            ticket_key='PROJ-123',
            project_key='PROJ',
            raw_payload={'issue': {'fields': ticket_details}},
            ticket_details=ticket_details,
            stakeholders=stakeholders,
            classification=classification,
            context_data={'processed_at': datetime.now(timezone.utc).isoformat()}
        )
    
    @pytest.fixture
    def sample_team_config(self):
        """Create a sample team configuration."""
        return {
            'team_id': 'engineering',
            'team_name': 'Engineering Team',
            'enabled': True,
            'version': '1.0.0',
            'default_channels': {
                'status_change': '#dev-updates',
                'assignment': '#assignments',
                'general': '#general'
            },
            'rules': [
                {
                    'rule_id': 'high_priority_rule',
                    'name': 'High Priority Issues',
                    'description': 'Route high priority issues to alerts channel',
                    'hook_types': ['StatusChangeHook', 'AssignmentHook'],
                    'enabled': True,
                    'priority': 10,
                    'conditions': {
                        'logic': 'and',
                        'conditions': [
                            {
                                'field': 'ticket.priority.name',
                                'operator': 'in',
                                'value': ['High', 'Critical']
                            },
                            {
                                'field': 'event.classification.urgency',
                                'operator': 'equals',
                                'value': 'high'
                            }
                        ]
                    },
                    'metadata': {
                        'channels': ['#alerts'],
                        'urgency_override': 'critical'
                    }
                },
                {
                    'rule_id': 'bug_rule',
                    'name': 'Bug Issues',
                    'description': 'Route bug issues to bug channel',
                    'hook_types': ['StatusChangeHook'],
                    'enabled': True,
                    'priority': 5,
                    'conditions': {
                        'logic': 'and',
                        'conditions': [
                            {
                                'field': 'ticket.issue_type.name',
                                'operator': 'equals',
                                'value': 'Bug'
                            },
                            {
                                'field': 'ticket.priority.name',
                                'operator': 'in',
                                'value': ['Medium', 'High', 'Critical']
                            }
                        ]
                    },
                    'metadata': {
                        'channels': ['#bugs']
                    }
                }
            ]
        }
    
    @pytest.fixture
    def temp_config_dir(self, sample_team_config):
        """Create a temporary configuration directory with sample config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            
            # Write sample team config
            team_config_file = config_path / 'team_engineering_hooks.yaml'
            with open(team_config_file, 'w') as f:
                yaml.dump(sample_team_config, f)
            
            yield str(config_path)
    
    @pytest.fixture
    def rule_engine(self, temp_config_dir):
        """Create a HookRuleEngine instance with temporary config."""
        return HookRuleEngine(config_dir=temp_config_dir)
    
    @pytest.mark.asyncio
    async def test_evaluate_rules_match(self, rule_engine, sample_event):
        """Test rule evaluation with matching conditions."""
        result = await rule_engine.evaluate_rules(
            event=sample_event,
            team_id='engineering',
            hook_types=['StatusChangeHook']
        )
        
        assert result.matched is True
        assert result.rule_id == 'high_priority_rule'
        assert result.rule_name == 'High Priority Issues'
        assert 'StatusChangeHook' in result.hook_types
        assert '#alerts' in result.channels
        assert result.urgency_override == UrgencyLevel.CRITICAL
        assert result.evaluation_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_evaluate_rules_no_match(self, rule_engine, sample_event):
        """Test rule evaluation with no matching conditions."""
        # Modify event to not match any rules
        sample_event.ticket_details['priority']['name'] = 'Low'
        sample_event.classification.urgency = UrgencyLevel.LOW
        
        result = await rule_engine.evaluate_rules(
            event=sample_event,
            team_id='engineering',
            hook_types=['StatusChangeHook']
        )
        
        assert result.matched is False
        assert result.rule_id is None
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_evaluate_rules_priority_order(self, rule_engine, sample_event):
        """Test that rules are evaluated in priority order."""
        # Both rules should match, but high priority rule should win
        result = await rule_engine.evaluate_rules(
            event=sample_event,
            team_id='engineering',
            hook_types=['StatusChangeHook']
        )
        
        assert result.matched is True
        assert result.rule_id == 'high_priority_rule'  # Higher priority (10 vs 5)
        assert result.metadata['rule_priority'] == 10
    
    @pytest.mark.asyncio
    async def test_evaluate_rules_hook_type_filter(self, rule_engine, sample_event):
        """Test filtering rules by hook types."""
        result = await rule_engine.evaluate_rules(
            event=sample_event,
            team_id='engineering',
            hook_types=['CommentHook']  # No rules match this hook type
        )
        
        assert result.matched is False
    
    @pytest.mark.asyncio
    async def test_load_team_rules_success(self, rule_engine):
        """Test successful team rules loading."""
        team_rules = await rule_engine.load_team_rules('engineering')
        
        assert team_rules is not None
        assert team_rules.team_id == 'engineering'
        assert team_rules.team_name == 'Engineering Team'
        assert len(team_rules.rules) == 2
        assert team_rules.enabled is True
        assert '#dev-updates' in team_rules.default_channels.values()
    
    @pytest.mark.asyncio
    async def test_load_team_rules_not_found(self, rule_engine):
        """Test loading rules for non-existent team."""
        team_rules = await rule_engine.load_team_rules('nonexistent')
        
        assert team_rules is None
    
    @pytest.mark.asyncio
    async def test_load_team_rules_caching(self, rule_engine):
        """Test that team rules are cached properly."""
        # First load
        team_rules1 = await rule_engine.load_team_rules('engineering')
        assert rule_engine._cache_misses == 1
        assert rule_engine._cache_hits == 0
        
        # Second load should hit cache
        team_rules2 = await rule_engine.load_team_rules('engineering')
        assert rule_engine._cache_misses == 1
        assert rule_engine._cache_hits == 1
        
        assert team_rules1 is team_rules2
    
    @pytest.mark.asyncio
    async def test_validate_rule_syntax_valid(self, rule_engine, sample_team_config):
        """Test validation of valid rule syntax."""
        result = await rule_engine.validate_rule_syntax(sample_team_config)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_rule_syntax_missing_team_id(self, rule_engine, sample_team_config):
        """Test validation with missing team_id."""
        del sample_team_config['team_id']
        
        result = await rule_engine.validate_rule_syntax(sample_team_config)
        
        assert result.valid is False
        assert any('team_id' in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_rule_syntax_invalid_rules(self, rule_engine, sample_team_config):
        """Test validation with invalid rules."""
        # Remove required field from rule
        del sample_team_config['rules'][0]['name']
        
        result = await rule_engine.validate_rule_syntax(sample_team_config)
        
        assert result.valid is False
        assert any('name' in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_rule_syntax_invalid_operator(self, rule_engine, sample_team_config):
        """Test validation with invalid operator."""
        sample_team_config['rules'][0]['conditions']['conditions'][0]['operator'] = 'invalid_op'
        
        result = await rule_engine.validate_rule_syntax(sample_team_config)
        
        assert result.valid is False
        assert any('Invalid operator' in error for error in result.errors)
    
    def test_extract_field_value_simple(self, rule_engine, sample_event):
        """Test extracting simple field values."""
        # Test event fields
        assert rule_engine._extract_field_value('event.event_type', sample_event) == 'jira:issue_updated'
        assert rule_engine._extract_field_value('event.ticket_key', sample_event) == 'PROJ-123'
        
        # Test ticket fields
        assert rule_engine._extract_field_value('ticket.summary', sample_event) == 'Critical bug in payment system'
        assert rule_engine._extract_field_value('ticket.priority.name', sample_event) == 'High'
    
    def test_extract_field_value_nested(self, rule_engine, sample_event):
        """Test extracting nested field values."""
        assert rule_engine._extract_field_value('event.classification.category', sample_event) == 'status_change'
        assert rule_engine._extract_field_value('event.classification.urgency', sample_event) == 'high'
        assert rule_engine._extract_field_value('stakeholders.roles', sample_event) == ['assignee']
    
    def test_extract_field_value_nonexistent(self, rule_engine, sample_event):
        """Test extracting non-existent field values."""
        assert rule_engine._extract_field_value('nonexistent.field', sample_event) is None
        assert rule_engine._extract_field_value('ticket.nonexistent', sample_event) is None
    
    def test_apply_operator_equals(self, rule_engine):
        """Test EQUALS operator."""
        assert rule_engine._apply_operator(RuleOperator.EQUALS, 'test', 'test') is True
        assert rule_engine._apply_operator(RuleOperator.EQUALS, 'test', 'other') is False
        assert rule_engine._apply_operator(RuleOperator.EQUALS, 123, 123) is True
    
    def test_apply_operator_in(self, rule_engine):
        """Test IN operator."""
        assert rule_engine._apply_operator(RuleOperator.IN, 'test', ['test', 'other']) is True
        assert rule_engine._apply_operator(RuleOperator.IN, 'missing', ['test', 'other']) is False
        assert rule_engine._apply_operator(RuleOperator.IN, 'test', 'test') is True  # Single value
    
    def test_apply_operator_contains(self, rule_engine):
        """Test CONTAINS operator."""
        assert rule_engine._apply_operator(RuleOperator.CONTAINS, 'hello world', 'world') is True
        assert rule_engine._apply_operator(RuleOperator.CONTAINS, 'hello world', 'missing') is False
        assert rule_engine._apply_operator(RuleOperator.CONTAINS, ['a', 'b', 'c'], 'b') is True
    
    def test_apply_operator_regex(self, rule_engine):
        """Test REGEX operator."""
        assert rule_engine._apply_operator(RuleOperator.REGEX, 'test123', r'\d+') is True
        assert rule_engine._apply_operator(RuleOperator.REGEX, 'testABC', r'\d+') is False
        assert rule_engine._apply_operator(RuleOperator.REGEX, 'Test', r'test', case_sensitive=False) is True
    
    def test_apply_operator_numeric(self, rule_engine):
        """Test numeric operators."""
        assert rule_engine._apply_operator(RuleOperator.GREATER_THAN, 10, 5) is True
        assert rule_engine._apply_operator(RuleOperator.GREATER_THAN, 5, 10) is False
        assert rule_engine._apply_operator(RuleOperator.LESS_THAN, 5, 10) is True
        assert rule_engine._apply_operator(RuleOperator.GREATER_EQUAL, 10, 10) is True
    
    def test_apply_operator_case_sensitivity(self, rule_engine):
        """Test case sensitivity in operators."""
        # Case sensitive (default)
        assert rule_engine._apply_operator(RuleOperator.EQUALS, 'Test', 'test', case_sensitive=True) is False
        
        # Case insensitive
        assert rule_engine._apply_operator(RuleOperator.EQUALS, 'Test', 'test', case_sensitive=False) is True
        assert rule_engine._apply_operator(RuleOperator.IN, 'Test', ['test', 'other'], case_sensitive=False) is True
    
    @pytest.mark.asyncio
    async def test_evaluate_condition_simple(self, rule_engine, sample_event):
        """Test evaluating simple conditions."""
        condition = RuleCondition(
            field='event.event_type',
            operator=RuleOperator.EQUALS,
            value='jira:issue_updated'
        )
        
        result = await rule_engine._evaluate_condition(condition, sample_event)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_evaluate_condition_complex(self, rule_engine, sample_event):
        """Test evaluating complex conditions."""
        condition = RuleCondition(
            field='ticket.priority.name',
            operator=RuleOperator.IN,
            value=['High', 'Critical']
        )
        
        result = await rule_engine._evaluate_condition(condition, sample_event)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_evaluate_rule_group_and(self, rule_engine, sample_event):
        """Test evaluating rule group with AND logic."""
        conditions = [
            RuleCondition('event.event_type', RuleOperator.EQUALS, 'jira:issue_updated'),
            RuleCondition('ticket.priority.name', RuleOperator.EQUALS, 'High')
        ]
        
        rule_group = RuleGroup(conditions=conditions, logic=RuleLogic.AND)
        result = await rule_engine._evaluate_rule_group(rule_group, sample_event)
        assert result is True
        
        # Change one condition to make it fail
        conditions[1].value = 'Low'
        result = await rule_engine._evaluate_rule_group(rule_group, sample_event)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_evaluate_rule_group_or(self, rule_engine, sample_event):
        """Test evaluating rule group with OR logic."""
        conditions = [
            RuleCondition('event.event_type', RuleOperator.EQUALS, 'jira:issue_updated'),
            RuleCondition('ticket.priority.name', RuleOperator.EQUALS, 'Low')  # This will fail
        ]
        
        rule_group = RuleGroup(conditions=conditions, logic=RuleLogic.OR)
        result = await rule_engine._evaluate_rule_group(rule_group, sample_event)
        assert result is True  # First condition passes
    
    @pytest.mark.asyncio
    async def test_evaluate_rule_group_not(self, rule_engine, sample_event):
        """Test evaluating rule group with NOT logic."""
        conditions = [
            RuleCondition('ticket.priority.name', RuleOperator.EQUALS, 'Low')  # This will fail
        ]
        
        rule_group = RuleGroup(conditions=conditions, logic=RuleLogic.NOT)
        result = await rule_engine._evaluate_rule_group(rule_group, sample_event)
        assert result is True  # NOT of false is true
    
    @pytest.mark.asyncio
    async def test_evaluate_rule_group_nested(self, rule_engine, sample_event):
        """Test evaluating nested rule groups."""
        inner_group = RuleGroup(
            conditions=[
                RuleCondition('ticket.priority.name', RuleOperator.EQUALS, 'High'),
                RuleCondition('ticket.issue_type.name', RuleOperator.EQUALS, 'Bug')
            ],
            logic=RuleLogic.AND
        )
        
        outer_group = RuleGroup(
            conditions=[
                RuleCondition('event.event_type', RuleOperator.EQUALS, 'jira:issue_updated'),
                inner_group
            ],
            logic=RuleLogic.AND
        )
        
        result = await rule_engine._evaluate_rule_group(outer_group, sample_event)
        assert result is True
    
    def test_determine_channels(self, rule_engine, sample_event):
        """Test channel determination for matched rules."""
        rule = HookRule(
            rule_id='test_rule',
            name='Test Rule',
            description='Test',
            hook_types=['StatusChangeHook'],
            conditions=RuleGroup(conditions=[]),
            metadata={'channels': ['#custom-channel']}
        )
        
        team_rules = TeamRuleSet(
            team_id='engineering',
            team_name='Engineering',
            rules=[rule],
            default_channels={'StatusChangeHook': '#default-status', 'general': '#general'}
        )
        
        channels = rule_engine._determine_channels(rule, team_rules, sample_event)
        assert '#custom-channel' in channels
    
    def test_determine_urgency_override(self, rule_engine, sample_event):
        """Test urgency override determination."""
        rule = HookRule(
            rule_id='test_rule',
            name='Test Rule',
            description='Test',
            hook_types=['StatusChangeHook'],
            conditions=RuleGroup(conditions=[]),
            metadata={'urgency_override': 'critical'}
        )
        
        override = rule_engine._determine_urgency_override(rule, sample_event)
        assert override == UrgencyLevel.CRITICAL
    
    def test_cache_management(self, rule_engine):
        """Test cache management functionality."""
        # Test cache validity
        assert rule_engine._is_cache_valid('nonexistent') is False
        
        # Add to cache
        team_rules = TeamRuleSet(
            team_id='test',
            team_name='Test',
            rules=[]
        )
        rule_engine._team_rules_cache['test'] = team_rules
        rule_engine._cache_timestamps['test'] = datetime.now(timezone.utc)
        
        assert rule_engine._is_cache_valid('test') is True
        
        # Clear specific cache
        rule_engine.clear_cache('test')
        assert 'test' not in rule_engine._team_rules_cache
        assert 'test' not in rule_engine._cache_timestamps
    
    def test_metrics(self, rule_engine):
        """Test metrics collection."""
        # Initial metrics
        metrics = rule_engine.get_metrics()
        assert metrics['evaluations_count'] == 0
        assert metrics['cache_hits'] == 0
        assert metrics['cache_misses'] == 0
        
        # Simulate some activity
        rule_engine._evaluations_count = 10
        rule_engine._cache_hits = 5
        rule_engine._cache_misses = 3
        
        metrics = rule_engine.get_metrics()
        assert metrics['evaluations_count'] == 10
        assert metrics['cache_hits'] == 5
        assert metrics['cache_misses'] == 3
        assert metrics['cache_hit_rate'] == 5/8
        
        # Reset metrics
        rule_engine.reset_metrics()
        metrics = rule_engine.get_metrics()
        assert metrics['evaluations_count'] == 0
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_config(self, temp_config_dir):
        """Test error handling with invalid configuration."""
        # Write invalid YAML
        config_path = Path(temp_config_dir)
        invalid_config_file = config_path / 'team_invalid_hooks.yaml'
        with open(invalid_config_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        rule_engine = HookRuleEngine(config_dir=temp_config_dir)
        team_rules = await rule_engine.load_team_rules('invalid')
        
        assert team_rules is None
    
    @pytest.mark.asyncio
    async def test_error_handling_evaluation_exception(self, rule_engine, sample_event):
        """Test error handling during rule evaluation."""
        # Mock an exception during field extraction
        with patch.object(rule_engine, '_extract_field_value', side_effect=Exception("Test error")):
            result = await rule_engine.evaluate_rules(sample_event, 'engineering')
            
            # Should not crash, but return no match
            assert result.matched is False
            assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_business_hours_validation(self, rule_engine):
        """Test business hours validation."""
        config = {
            'team_id': 'test',
            'rules': [],
            'business_hours': {
                'start': '09:00',
                'end': '17:00',
                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
            }
        }
        
        result = await rule_engine.validate_rule_syntax(config)
        assert result.valid is True
        
        # Test invalid time format
        config['business_hours']['start'] = 'invalid-time'
        result = await rule_engine.validate_rule_syntax(config)
        assert len(result.warnings) > 0
    
    @pytest.mark.asyncio
    async def test_complex_rule_scenario(self, rule_engine, sample_event):
        """Test complex rule scenario with multiple conditions and nested groups."""
        # Create a complex rule configuration
        complex_config = {
            'team_id': 'engineering',
            'team_name': 'Engineering Team',
            'enabled': True,
            'rules': [
                {
                    'rule_id': 'complex_rule',
                    'name': 'Complex Rule',
                    'description': 'Complex rule with nested conditions',
                    'hook_types': ['StatusChangeHook'],
                    'enabled': True,
                    'priority': 10,
                    'conditions': {
                        'logic': 'and',
                        'conditions': [
                            {
                                'field': 'event.event_type',
                                'operator': 'equals',
                                'value': 'jira:issue_updated'
                            },
                            {
                                'logic': 'or',
                                'conditions': [
                                    {
                                        'field': 'ticket.priority.name',
                                        'operator': 'in',
                                        'value': ['High', 'Critical']
                                    },
                                    {
                                        'field': 'event.classification.keywords',
                                        'operator': 'contains',
                                        'value': 'critical'
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }
        
        # Write complex config to temp file
        config_path = Path(rule_engine.config_dir)
        complex_config_file = config_path / 'team_complex_hooks.yaml'
        with open(complex_config_file, 'w') as f:
            yaml.dump(complex_config, f)
        
        # Clear cache to force reload
        rule_engine.clear_cache('complex')
        
        # Test evaluation
        result = await rule_engine.evaluate_rules(sample_event, 'complex')
        assert result.matched is True
        assert result.rule_id == 'complex_rule'


class TestRuleDataClasses:
    """Test rule-related data classes."""
    
    def test_rule_condition_creation(self):
        """Test RuleCondition creation and validation."""
        condition = RuleCondition(
            field='test.field',
            operator='equals',
            value='test_value'
        )
        
        assert condition.field == 'test.field'
        assert condition.operator == RuleOperator.EQUALS
        assert condition.value == 'test_value'
        assert condition.case_sensitive is True
    
    def test_rule_group_creation(self):
        """Test RuleGroup creation and validation."""
        conditions = [
            RuleCondition('field1', RuleOperator.EQUALS, 'value1'),
            RuleCondition('field2', RuleOperator.IN, ['value2', 'value3'])
        ]
        
        group = RuleGroup(conditions=conditions, logic='and')
        
        assert len(group.conditions) == 2
        assert group.logic == RuleLogic.AND
    
    def test_hook_rule_creation(self):
        """Test HookRule creation."""
        conditions = RuleGroup(
            conditions=[RuleCondition('field', RuleOperator.EQUALS, 'value')]
        )
        
        rule = HookRule(
            rule_id='test_rule',
            name='Test Rule',
            description='Test description',
            hook_types=['TestHook'],
            conditions=conditions,
            priority=5
        )
        
        assert rule.rule_id == 'test_rule'
        assert rule.name == 'Test Rule'
        assert rule.enabled is True
        assert rule.priority == 5
        assert isinstance(rule.created_at, datetime)
    
    def test_team_rule_set_creation(self):
        """Test TeamRuleSet creation."""
        rules = [
            HookRule(
                rule_id='rule1',
                name='Rule 1',
                description='Test',
                hook_types=['TestHook'],
                conditions=RuleGroup(conditions=[])
            )
        ]
        
        team_rules = TeamRuleSet(
            team_id='test_team',
            team_name='Test Team',
            rules=rules,
            default_channels={'general': '#general'}
        )
        
        assert team_rules.team_id == 'test_team'
        assert team_rules.team_name == 'Test Team'
        assert len(team_rules.rules) == 1
        assert team_rules.enabled is True
        assert isinstance(team_rules.last_updated, datetime)
    
    def test_rule_evaluation_result_creation(self):
        """Test RuleEvaluationResult creation."""
        result = RuleEvaluationResult(
            matched=True,
            rule_id='test_rule',
            rule_name='Test Rule',
            hook_types=['TestHook'],
            channels=['#test'],
            evaluation_time_ms=10.5
        )
        
        assert result.matched is True
        assert result.rule_id == 'test_rule'
        assert result.evaluation_time_ms == 10.5
        assert len(result.errors) == 0
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation."""
        result = ValidationResult(
            valid=False,
            errors=['Error 1', 'Error 2'],
            warnings=['Warning 1']
        )
        
        assert result.valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])