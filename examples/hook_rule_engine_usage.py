"""
Hook Rule Engine Usage Examples
Demonstrates how to use the HookRuleEngine for team-specific filtering.
"""

import asyncio
import yaml
from datetime import datetime, timezone
from pathlib import Path

from devsync_ai.core.hook_rule_engine import (
    HookRuleEngine,
    RuleOperator,
    RuleLogic,
    RuleCondition,
    RuleGroup,
    HookRule,
    TeamRuleSet
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


class HookRuleEngineExamples:
    """Examples of using the Hook Rule Engine."""
    
    def __init__(self):
        """Initialize with sample data."""
        self.rule_engine = HookRuleEngine(config_dir="config")
    
    def create_sample_events(self):
        """Create sample events for testing."""
        events = []
        
        # Critical bug event
        critical_bug = self._create_event(
            event_type='jira:issue_updated',
            ticket_key='ENG-123',
            summary='Critical payment processing bug',
            priority='Critical',
            issue_type='Bug',
            status='In Progress',
            labels=['critical', 'payment', 'production'],
            urgency=UrgencyLevel.CRITICAL,
            category=EventCategory.STATUS_CHANGE
        )
        events.append(('Critical Bug', critical_bug))
        
        # High priority assignment
        assignment = self._create_event(
            event_type='jira:issue_assigned',
            ticket_key='ENG-124',
            summary='Implement new authentication system',
            priority='High',
            issue_type='Story',
            status='To Do',
            labels=['security', 'authentication'],
            urgency=UrgencyLevel.HIGH,
            category=EventCategory.ASSIGNMENT
        )
        events.append(('High Priority Assignment', assignment))
        
        # Test automation issue
        test_automation = self._create_event(
            event_type='jira:issue_updated',
            ticket_key='QA-456',
            summary='Fix flaky automation tests',
            priority='Medium',
            issue_type='Bug',
            status='In Progress',
            labels=['automation', 'flaky-tests'],
            urgency=UrgencyLevel.MEDIUM,
            category=EventCategory.STATUS_CHANGE
        )
        events.append(('Test Automation Issue', test_automation))
        
        # Blocked issue
        blocked_issue = self._create_event(
            event_type='jira:issue_transitioned',
            ticket_key='ENG-125',
            summary='Database migration blocked by infrastructure',
            priority='High',
            issue_type='Task',
            status='Blocked',
            labels=['blocked', 'infrastructure'],
            urgency=UrgencyLevel.HIGH,
            category=EventCategory.BLOCKER
        )
        events.append(('Blocked Issue', blocked_issue))
        
        # Comment on critical issue
        critical_comment = self._create_event(
            event_type='jira:issue_commented',
            ticket_key='ENG-126',
            summary='Production outage investigation',
            priority='Critical',
            issue_type='Incident',
            status='In Progress',
            labels=['production', 'outage'],
            urgency=UrgencyLevel.CRITICAL,
            category=EventCategory.COMMENT
        )
        events.append(('Critical Comment', critical_comment))
        
        return events
    
    def _create_event(self, event_type, ticket_key, summary, priority, issue_type, 
                     status, labels, urgency, category):
        """Helper to create enriched events."""
        classification = EventClassification(
            category=category,
            urgency=urgency,
            significance=SignificanceLevel.MAJOR,
            affected_teams=['engineering'] if ticket_key.startswith('ENG') else ['qa'],
            routing_hints={'priority': priority, 'status': status},
            keywords=labels
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
            'key': ticket_key,
            'summary': summary,
            'status': {'name': status, 'category': status},
            'priority': {'name': priority},
            'issue_type': {'name': issue_type},
            'assignee': {'display_name': 'John Doe', 'user_id': 'user123'},
            'labels': labels,
            'components': ['core-service']
        }
        
        return EnrichedEvent(
            event_id=f'event_{ticket_key}',
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            jira_event_data={'fields': ticket_details},
            ticket_key=ticket_key,
            project_key=ticket_key.split('-')[0],
            raw_payload={'issue': {'fields': ticket_details}},
            ticket_details=ticket_details,
            stakeholders=stakeholders,
            classification=classification,
            context_data={'processed_at': datetime.now(timezone.utc).isoformat()}
        )
    
    async def demonstrate_rule_evaluation(self):
        """Demonstrate rule evaluation for different events."""
        print("=== HOOK RULE ENGINE EVALUATION EXAMPLES ===\n")
        
        events = self.create_sample_events()
        teams = ['engineering', 'qa']
        
        for event_name, event in events:
            print(f"Event: {event_name}")
            print(f"  Ticket: {event.ticket_key}")
            print(f"  Type: {event.event_type}")
            print(f"  Priority: {event.ticket_details['priority']['name']}")
            print(f"  Urgency: {event.classification.urgency.value}")
            print(f"  Category: {event.classification.category.value}")
            print()
            
            for team_id in teams:
                result = await self.rule_engine.evaluate_rules(
                    event=event,
                    team_id=team_id,
                    hook_types=['StatusChangeHook', 'AssignmentHook', 'CommentHook', 'BlockerHook']
                )
                
                print(f"  Team: {team_id}")
                print(f"    Matched: {result.matched}")
                if result.matched:
                    print(f"    Rule: {result.rule_name} (ID: {result.rule_id})")
                    print(f"    Channels: {result.channels}")
                    print(f"    Hook Types: {result.hook_types}")
                    if result.urgency_override:
                        print(f"    Urgency Override: {result.urgency_override.value}")
                    print(f"    Evaluation Time: {result.evaluation_time_ms:.2f}ms")
                else:
                    if result.errors:
                        print(f"    Errors: {result.errors}")
                print()
            
            print("-" * 60)
            print()
    
    async def demonstrate_rule_validation(self):
        """Demonstrate rule validation functionality."""
        print("=== RULE VALIDATION EXAMPLES ===\n")
        
        # Valid configuration
        valid_config = {
            'team_id': 'test_team',
            'team_name': 'Test Team',
            'enabled': True,
            'rules': [
                {
                    'rule_id': 'test_rule',
                    'name': 'Test Rule',
                    'description': 'A test rule',
                    'hook_types': ['StatusChangeHook'],
                    'enabled': True,
                    'conditions': {
                        'logic': 'and',
                        'conditions': [
                            {
                                'field': 'ticket.priority.name',
                                'operator': 'equals',
                                'value': 'High'
                            }
                        ]
                    }
                }
            ]
        }
        
        print("Validating VALID configuration:")
        result = await self.rule_engine.validate_rule_syntax(valid_config)
        print(f"  Valid: {result.valid}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Warnings: {len(result.warnings)}")
        if result.errors:
            for error in result.errors:
                print(f"    Error: {error}")
        if result.warnings:
            for warning in result.warnings:
                print(f"    Warning: {warning}")
        print()
        
        # Invalid configuration - missing required fields
        invalid_config = {
            'team_name': 'Test Team',  # Missing team_id
            'rules': [
                {
                    # Missing name and hook_types
                    'rule_id': 'invalid_rule',
                    'conditions': {
                        'conditions': [
                            {
                                'field': 'invalid.field',  # Unsupported field
                                'operator': 'invalid_op',  # Invalid operator
                                'value': 'test'
                            }
                        ]
                    }
                }
            ]
        }
        
        print("Validating INVALID configuration:")
        result = await self.rule_engine.validate_rule_syntax(invalid_config)
        print(f"  Valid: {result.valid}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Warnings: {len(result.warnings)}")
        if result.errors:
            for error in result.errors:
                print(f"    Error: {error}")
        if result.warnings:
            for warning in result.warnings:
                print(f"    Warning: {warning}")
        print()
    
    async def demonstrate_complex_rules(self):
        """Demonstrate complex rule scenarios."""
        print("=== COMPLEX RULE SCENARIOS ===\n")
        
        # Create a complex rule programmatically
        complex_conditions = RuleGroup(
            logic=RuleLogic.AND,
            conditions=[
                RuleCondition(
                    field='event.event_type',
                    operator=RuleOperator.EQUALS,
                    value='jira:issue_updated'
                ),
                RuleGroup(
                    logic=RuleLogic.OR,
                    conditions=[
                        RuleCondition(
                            field='ticket.priority.name',
                            operator=RuleOperator.IN,
                            value=['High', 'Critical']
                        ),
                        RuleCondition(
                            field='event.classification.keywords',
                            operator=RuleOperator.CONTAINS,
                            value='critical'
                        )
                    ]
                ),
                RuleGroup(
                    logic=RuleLogic.NOT,
                    conditions=[
                        RuleCondition(
                            field='ticket.status.name',
                            operator=RuleOperator.EQUALS,
                            value='Closed'
                        )
                    ]
                )
            ]
        )
        
        complex_rule = HookRule(
            rule_id='complex_rule',
            name='Complex Rule Example',
            description='A complex rule with nested conditions',
            hook_types=['StatusChangeHook'],
            conditions=complex_conditions,
            priority=50
        )
        
        print("Complex Rule Structure:")
        print(f"  Rule: {complex_rule.name}")
        print(f"  Logic: {complex_rule.conditions.logic.value}")
        print(f"  Conditions: {len(complex_rule.conditions.conditions)}")
        print()
        
        # Test the complex rule against sample events
        events = self.create_sample_events()
        
        for event_name, event in events[:3]:  # Test first 3 events
            # Manually evaluate the complex rule
            try:
                matches = await self.rule_engine._evaluate_rule_group(
                    complex_rule.conditions, 
                    event
                )
                print(f"Event: {event_name}")
                print(f"  Matches Complex Rule: {matches}")
                print(f"  Event Type: {event.event_type}")
                print(f"  Priority: {event.ticket_details['priority']['name']}")
                print(f"  Status: {event.ticket_details['status']['name']}")
                print(f"  Keywords: {event.classification.keywords}")
                print()
            except Exception as e:
                print(f"Error evaluating complex rule for {event_name}: {e}")
                print()
    
    async def demonstrate_performance_metrics(self):
        """Demonstrate performance metrics collection."""
        print("=== PERFORMANCE METRICS ===\n")
        
        # Reset metrics
        self.rule_engine.reset_metrics()
        
        # Perform multiple evaluations
        events = self.create_sample_events()
        
        print("Performing multiple rule evaluations...")
        for i in range(10):
            for event_name, event in events:
                await self.rule_engine.evaluate_rules(
                    event=event,
                    team_id='engineering'
                )
        
        # Get metrics
        metrics = self.rule_engine.get_metrics()
        
        print("Performance Metrics:")
        print(f"  Total Evaluations: {metrics['evaluations_count']}")
        print(f"  Cache Hits: {metrics['cache_hits']}")
        print(f"  Cache Misses: {metrics['cache_misses']}")
        print(f"  Cache Hit Rate: {metrics['cache_hit_rate']:.2%}")
        print(f"  Cached Teams: {metrics['cached_teams']}")
        print(f"  Validation Errors: {metrics['validation_errors']}")
        print()
    
    async def demonstrate_field_extraction(self):
        """Demonstrate field value extraction."""
        print("=== FIELD EXTRACTION EXAMPLES ===\n")
        
        event = self.create_sample_events()[0][1]  # Use first event
        
        test_fields = [
            'event.event_type',
            'event.ticket_key',
            'event.project_key',
            'event.classification.category',
            'event.classification.urgency',
            'event.classification.keywords',
            'ticket.summary',
            'ticket.priority.name',
            'ticket.status.name',
            'ticket.issue_type.name',
            'ticket.labels',
            'stakeholders.roles',
            'stakeholders.display_names',
            'context.processed_at',
            'routing_hints.priority',
            'nonexistent.field'
        ]
        
        print("Field Extraction Results:")
        for field in test_fields:
            value = self.rule_engine._extract_field_value(field, event)
            print(f"  {field}: {value}")
        print()
    
    async def demonstrate_operator_testing(self):
        """Demonstrate different operators."""
        print("=== OPERATOR TESTING ===\n")
        
        test_cases = [
            # (operator, field_value, condition_value, case_sensitive, expected)
            (RuleOperator.EQUALS, 'test', 'test', True, True),
            (RuleOperator.EQUALS, 'Test', 'test', False, True),
            (RuleOperator.IN, 'high', ['high', 'critical'], True, True),
            (RuleOperator.CONTAINS, 'hello world', 'world', True, True),
            (RuleOperator.STARTS_WITH, 'hello world', 'hello', True, True),
            (RuleOperator.ENDS_WITH, 'hello world', 'world', True, True),
            (RuleOperator.REGEX, 'test123', r'\d+', True, True),
            (RuleOperator.GREATER_THAN, 10, 5, True, True),
            (RuleOperator.LESS_THAN, 5, 10, True, True),
            (RuleOperator.NOT_EQUALS, 'test', 'other', True, True),
            (RuleOperator.NOT_IN, 'low', ['high', 'critical'], True, True),
        ]
        
        print("Operator Test Results:")
        for operator, field_value, condition_value, case_sensitive, expected in test_cases:
            result = self.rule_engine._apply_operator(
                operator, field_value, condition_value, case_sensitive
            )
            status = "✅" if result == expected else "❌"
            print(f"  {status} {operator.value}: {field_value} vs {condition_value} = {result}")
        print()
    
    def create_custom_team_config(self):
        """Create a custom team configuration example."""
        print("=== CUSTOM TEAM CONFIGURATION ===\n")
        
        custom_config = {
            'team_id': 'custom_team',
            'team_name': 'Custom Team',
            'enabled': True,
            'version': '1.0.0',
            'default_channels': {
                'status_change': '#custom-updates',
                'assignment': '#custom-assignments',
                'general': '#custom-team'
            },
            'notification_preferences': {
                'batch_threshold': 2,
                'batch_timeout_minutes': 3,
                'quiet_hours': {
                    'enabled': True,
                    'start': '20:00',
                    'end': '08:00'
                }
            },
            'business_hours': {
                'start': '10:00',
                'end': '16:00',
                'timezone': 'America/Los_Angeles',
                'days': ['monday', 'tuesday', 'wednesday', 'thursday']
            },
            'rules': [
                {
                    'rule_id': 'custom_high_priority',
                    'name': 'Custom High Priority Rule',
                    'description': 'Route high priority items to alerts',
                    'hook_types': ['StatusChangeHook', 'AssignmentHook'],
                    'enabled': True,
                    'priority': 100,
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
                                'operator': 'not_equals',
                                'value': 'low'
                            }
                        ]
                    },
                    'metadata': {
                        'channels': ['#alerts'],
                        'urgency_override': 'high'
                    }
                },
                {
                    'rule_id': 'custom_keyword_filter',
                    'name': 'Custom Keyword Filter',
                    'description': 'Filter by custom keywords',
                    'hook_types': ['StatusChangeHook', 'CommentHook'],
                    'enabled': True,
                    'priority': 50,
                    'conditions': {
                        'logic': 'or',
                        'conditions': [
                            {
                                'field': 'ticket.summary',
                                'operator': 'regex',
                                'value': '\\b(urgent|asap|critical)\\b',
                                'case_sensitive': False
                            },
                            {
                                'field': 'event.classification.keywords',
                                'operator': 'contains',
                                'value': 'urgent'
                            }
                        ]
                    },
                    'metadata': {
                        'channels': ['#urgent']
                    }
                }
            ]
        }
        
        # Save to file
        config_path = Path('config/team_custom_hooks.yaml')
        with open(config_path, 'w') as f:
            yaml.dump(custom_config, f, default_flow_style=False, indent=2)
        
        print(f"Custom team configuration saved to: {config_path}")
        print("Configuration includes:")
        print(f"  - Team: {custom_config['team_name']}")
        print(f"  - Rules: {len(custom_config['rules'])}")
        print(f"  - Default Channels: {len(custom_config['default_channels'])}")
        print(f"  - Business Hours: {custom_config['business_hours']['start']} - {custom_config['business_hours']['end']}")
        print()


async def main():
    """Run Hook Rule Engine examples."""
    print("HOOK RULE ENGINE USAGE EXAMPLES")
    print("=" * 60)
    print()
    
    examples = HookRuleEngineExamples()
    
    try:
        await examples.demonstrate_rule_evaluation()
        await examples.demonstrate_rule_validation()
        await examples.demonstrate_complex_rules()
        await examples.demonstrate_performance_metrics()
        await examples.demonstrate_field_extraction()
        await examples.demonstrate_operator_testing()
        examples.create_custom_team_config()
        
        print("=" * 60)
        print("✅ Hook Rule Engine examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Examples failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())