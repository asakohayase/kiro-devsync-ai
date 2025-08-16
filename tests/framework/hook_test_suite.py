"""
Hook Behavior Testing Suite.

Comprehensive testing suite that covers individual hook trigger conditions,
execution logic, data transformation, error handling, and performance.
"""

import asyncio
import pytest
import time
import random
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from unittest.mock import Mock, AsyncMock, patch
from contextlib import asynccontextmanager

from devsync_ai.core.agent_hooks import (
    AgentHook, HookExecutionResult, HookConfiguration, 
    HookStatus, EnrichedEvent, EventClassification, 
    EventCategory, UrgencyLevel, SignificanceLevel
)
from devsync_ai.hooks.jira_agent_hooks import (
    StatusChangeHook, AssignmentHook, CommentHook, 
    PriorityChangeHook, BlockerHook
)


@dataclass
class TestScenario:
    """Test scenario configuration."""
    name: str
    description: str
    event_data: Dict[str, Any]
    expected_trigger: bool
    expected_notification: bool
    expected_execution_time_ms: Optional[float] = None
    expected_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceBenchmark:
    """Performance benchmark configuration."""
    name: str
    max_execution_time_ms: float
    max_memory_usage_mb: float
    min_success_rate: float
    max_error_rate: float


class JIRAEventGenerator:
    """Generates realistic JIRA event payloads for testing."""
    
    def __init__(self):
        self.issue_types = ['Bug', 'Story', 'Task', 'Epic', 'Subtask']
        self.priorities = ['Lowest', 'Low', 'Medium', 'High', 'Highest']
        self.statuses = ['To Do', 'In Progress', 'Code Review', 'Testing', 'Done']
        self.projects = ['PROJ', 'TEST', 'DEMO', 'HACK']
        self.users = [
            {'accountId': 'user1', 'displayName': 'John Doe', 'emailAddress': 'john@example.com'},
            {'accountId': 'user2', 'displayName': 'Jane Smith', 'emailAddress': 'jane@example.com'},
            {'accountId': 'user3', 'displayName': 'Bob Wilson', 'emailAddress': 'bob@example.com'}
        ]
    
    def generate_issue_updated_event(
        self, 
        issue_key: Optional[str] = None,
        from_status: Optional[str] = None,
        to_status: Optional[str] = None,
        assignee_change: bool = False,
        priority_change: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a realistic JIRA issue updated event."""
        if not issue_key:
            project = random.choice(self.projects)
            issue_key = f"{project}-{random.randint(1, 9999)}"
        
        if not from_status:
            from_status = random.choice(self.statuses[:-1])
        if not to_status:
            to_status = random.choice([s for s in self.statuses if s != from_status])
        
        old_assignee = random.choice(self.users) if assignee_change else None
        new_assignee = random.choice([u for u in self.users if u != old_assignee]) if assignee_change else old_assignee
        
        old_priority = random.choice(self.priorities) if priority_change else 'Medium'
        new_priority = random.choice([p for p in self.priorities if p != old_priority]) if priority_change else old_priority
        
        event = {
            'timestamp': int(time.time() * 1000),
            'webhookEvent': 'jira:issue_updated',
            'issue_event_type_name': 'issue_updated',
            'user': random.choice(self.users),
            'issue': {
                'id': str(random.randint(10000, 99999)),
                'key': issue_key,
                'fields': {
                    'summary': f'Test issue {issue_key}',
                    'description': 'This is a test issue for hook testing',
                    'issuetype': {
                        'name': random.choice(self.issue_types),
                        'id': str(random.randint(1, 10))
                    },
                    'project': {
                        'key': issue_key.split('-')[0],
                        'name': f'Test Project {issue_key.split("-")[0]}'
                    },
                    'status': {
                        'name': to_status,
                        'id': str(self.statuses.index(to_status) + 1)
                    },
                    'priority': {
                        'name': new_priority,
                        'id': str(self.priorities.index(new_priority) + 1)
                    },
                    'assignee': new_assignee,
                    'reporter': random.choice(self.users),
                    'created': (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))).isoformat(),
                    'updated': datetime.now(timezone.utc).isoformat()
                }
            },
            'changelog': {
                'id': str(random.randint(10000, 99999)),
                'items': []
            }
        }
        
        # Add changelog items
        if from_status != to_status:
            event['changelog']['items'].append({
                'field': 'status',
                'fieldtype': 'jira',
                'from': str(self.statuses.index(from_status) + 1),
                'fromString': from_status,
                'to': str(self.statuses.index(to_status) + 1),
                'toString': to_status
            })
        
        if assignee_change:
            event['changelog']['items'].append({
                'field': 'assignee',
                'fieldtype': 'jira',
                'from': old_assignee['accountId'] if old_assignee else None,
                'fromString': old_assignee['displayName'] if old_assignee else None,
                'to': new_assignee['accountId'] if new_assignee else None,
                'toString': new_assignee['displayName'] if new_assignee else None
            })
        
        if priority_change:
            event['changelog']['items'].append({
                'field': 'priority',
                'fieldtype': 'jira',
                'from': str(self.priorities.index(old_priority) + 1),
                'fromString': old_priority,
                'to': str(self.priorities.index(new_priority) + 1),
                'toString': new_priority
            })
        
        # Apply any custom overrides
        for key, value in kwargs.items():
            if '.' in key:
                # Handle nested keys like 'issue.fields.summary'
                parts = key.split('.')
                current = event
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                event[key] = value
        
        return event
    
    def generate_comment_added_event(self, issue_key: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate a JIRA comment added event."""
        if not issue_key:
            project = random.choice(self.projects)
            issue_key = f"{project}-{random.randint(1, 9999)}"
        
        event = {
            'timestamp': int(time.time() * 1000),
            'webhookEvent': 'jira:issue_updated',
            'issue_event_type_name': 'issue_commented',
            'user': random.choice(self.users),
            'issue': {
                'id': str(random.randint(10000, 99999)),
                'key': issue_key,
                'fields': {
                    'summary': f'Test issue {issue_key}',
                    'issuetype': {'name': random.choice(self.issue_types)},
                    'project': {'key': issue_key.split('-')[0]},
                    'status': {'name': random.choice(self.statuses)},
                    'assignee': random.choice(self.users)
                }
            },
            'comment': {
                'id': str(random.randint(10000, 99999)),
                'body': 'This is a test comment for hook testing',
                'author': random.choice(self.users),
                'created': datetime.now(timezone.utc).isoformat(),
                'updated': datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Apply custom overrides
        for key, value in kwargs.items():
            if '.' in key:
                parts = key.split('.')
                current = event
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                event[key] = value
        
        return event
    
    def generate_edge_case_events(self) -> List[Dict[str, Any]]:
        """Generate edge case events for robust testing."""
        edge_cases = []
        
        # Missing required fields
        edge_cases.append({
            'name': 'missing_issue_key',
            'event': self.generate_issue_updated_event(),
            'modifications': lambda e: e['issue'].pop('key', None)
        })
        
        # Null/empty values
        edge_cases.append({
            'name': 'null_assignee',
            'event': self.generate_issue_updated_event(assignee_change=True),
            'modifications': lambda e: e['issue']['fields'].update({'assignee': None})
        })
        
        # Very long text fields
        edge_cases.append({
            'name': 'long_summary',
            'event': self.generate_issue_updated_event(),
            'modifications': lambda e: e['issue']['fields'].update({
                'summary': 'A' * 1000  # Very long summary
            })
        })
        
        # Unicode and special characters
        edge_cases.append({
            'name': 'unicode_content',
            'event': self.generate_issue_updated_event(),
            'modifications': lambda e: e['issue']['fields'].update({
                'summary': '🚀 Test with émojis and spëcial chars 中文 العربية'
            })
        })
        
        # Malformed timestamps
        edge_cases.append({
            'name': 'invalid_timestamp',
            'event': self.generate_issue_updated_event(),
            'modifications': lambda e: e.update({'timestamp': 'invalid-timestamp'})
        })
        
        # Apply modifications and return events
        result = []
        for case in edge_cases:
            event = case['event'].copy()
            case['modifications'](event)
            result.append({
                'name': case['name'],
                'event': event
            })
        
        return result


class HookAssertionHelpers:
    """Helper methods for complex hook execution validation."""
    
    @staticmethod
    def assert_hook_triggered(result: HookExecutionResult, expected: bool = True):
        """Assert that hook was triggered as expected."""
        if expected:
            assert result.status in [HookStatus.SUCCESS, HookStatus.FAILED], \
                f"Expected hook to be triggered, but status was {result.status}"
        else:
            assert result.status == HookStatus.CANCELLED, \
                f"Expected hook not to be triggered, but status was {result.status}"
    
    @staticmethod
    def assert_notification_sent(result: HookExecutionResult, expected: bool = True):
        """Assert that notification was sent as expected."""
        assert result.notification_sent == expected, \
            f"Expected notification_sent={expected}, got {result.notification_sent}"
    
    @staticmethod
    def assert_execution_time_within_bounds(result: HookExecutionResult, max_time_ms: float):
        """Assert that execution time is within acceptable bounds."""
        assert result.execution_time_ms <= max_time_ms, \
            f"Execution time {result.execution_time_ms}ms exceeded maximum {max_time_ms}ms"
    
    @staticmethod
    def assert_no_errors(result: HookExecutionResult):
        """Assert that no errors occurred during execution."""
        assert len(result.errors) == 0, f"Expected no errors, but got: {result.errors}"
    
    @staticmethod
    def assert_specific_errors(result: HookExecutionResult, expected_errors: List[str]):
        """Assert that specific errors occurred."""
        for expected_error in expected_errors:
            assert any(expected_error in error for error in result.errors), \
                f"Expected error containing '{expected_error}' not found in {result.errors}"
    
    @staticmethod
    def assert_metadata_contains(result: HookExecutionResult, expected_metadata: Dict[str, Any]):
        """Assert that result metadata contains expected values."""
        for key, expected_value in expected_metadata.items():
            assert key in result.metadata, f"Expected metadata key '{key}' not found"
            assert result.metadata[key] == expected_value, \
                f"Expected metadata[{key}]={expected_value}, got {result.metadata[key]}"


class HookTestSuite:
    """
    Comprehensive testing suite for JIRA Agent Hooks.
    
    Provides parameterized tests for all hook types with realistic scenarios,
    edge cases, performance benchmarks, and error handling validation.
    """
    
    def __init__(self):
        self.event_generator = JIRAEventGenerator()
        self.assertion_helpers = HookAssertionHelpers()
        self.performance_benchmarks = self._create_performance_benchmarks()
        self.test_scenarios = self._create_test_scenarios()
    
    def _create_performance_benchmarks(self) -> Dict[str, PerformanceBenchmark]:
        """Create performance benchmarks for different hook types."""
        return {
            'status_change': PerformanceBenchmark(
                name='Status Change Hook',
                max_execution_time_ms=500.0,
                max_memory_usage_mb=50.0,
                min_success_rate=0.99,
                max_error_rate=0.01
            ),
            'assignment': PerformanceBenchmark(
                name='Assignment Hook',
                max_execution_time_ms=300.0,
                max_memory_usage_mb=30.0,
                min_success_rate=0.99,
                max_error_rate=0.01
            ),
            'comment': PerformanceBenchmark(
                name='Comment Hook',
                max_execution_time_ms=400.0,
                max_memory_usage_mb=40.0,
                min_success_rate=0.98,
                max_error_rate=0.02
            ),
            'priority_change': PerformanceBenchmark(
                name='Priority Change Hook',
                max_execution_time_ms=350.0,
                max_memory_usage_mb=35.0,
                min_success_rate=0.99,
                max_error_rate=0.01
            ),
            'blocker': PerformanceBenchmark(
                name='Blocker Hook',
                max_execution_time_ms=600.0,
                max_memory_usage_mb=60.0,
                min_success_rate=0.97,
                max_error_rate=0.03
            )
        }
    
    def _create_test_scenarios(self) -> Dict[str, List[TestScenario]]:
        """Create comprehensive test scenarios for all hook types."""
        scenarios = {}
        
        # Status Change Hook Scenarios
        scenarios['status_change'] = [
            TestScenario(
                name='basic_status_change',
                description='Basic status change from To Do to In Progress',
                event_data=self.event_generator.generate_issue_updated_event(
                    from_status='To Do', to_status='In Progress'
                ),
                expected_trigger=True,
                expected_notification=True
            ),
            TestScenario(
                name='status_to_done',
                description='Status change to Done (completion)',
                event_data=self.event_generator.generate_issue_updated_event(
                    from_status='In Progress', to_status='Done'
                ),
                expected_trigger=True,
                expected_notification=True,
                metadata={'completion': True}
            ),
            TestScenario(
                name='no_status_change',
                description='Issue update without status change',
                event_data=self.event_generator.generate_issue_updated_event(
                    from_status='In Progress', to_status='In Progress'
                ),
                expected_trigger=False,
                expected_notification=False
            )
        ]
        
        # Assignment Hook Scenarios
        scenarios['assignment'] = [
            TestScenario(
                name='basic_assignment',
                description='Basic issue assignment to user',
                event_data=self.event_generator.generate_issue_updated_event(
                    assignee_change=True
                ),
                expected_trigger=True,
                expected_notification=True
            ),
            TestScenario(
                name='unassignment',
                description='Issue unassignment (assignee set to null)',
                event_data=self.event_generator.generate_issue_updated_event(
                    assignee_change=True
                ),
                expected_trigger=True,
                expected_notification=True
            ),
            TestScenario(
                name='self_assignment',
                description='User assigns issue to themselves',
                event_data=self.event_generator.generate_issue_updated_event(
                    assignee_change=True
                ),
                expected_trigger=True,
                expected_notification=False,  # Usually don't notify self-assignments
                metadata={'self_assignment': True}
            )
        ]
        
        # Comment Hook Scenarios
        scenarios['comment'] = [
            TestScenario(
                name='basic_comment',
                description='Basic comment added to issue',
                event_data=self.event_generator.generate_comment_added_event(),
                expected_trigger=True,
                expected_notification=True
            ),
            TestScenario(
                name='mention_comment',
                description='Comment with user mentions',
                event_data=self.event_generator.generate_comment_added_event(
                    **{'comment.body': 'Hey [~user1], can you review this?'}
                ),
                expected_trigger=True,
                expected_notification=True,
                metadata={'mentions': ['user1']}
            ),
            TestScenario(
                name='long_comment',
                description='Very long comment',
                event_data=self.event_generator.generate_comment_added_event(
                    **{'comment.body': 'A' * 2000}
                ),
                expected_trigger=True,
                expected_notification=True
            )
        ]
        
        # Priority Change Hook Scenarios
        scenarios['priority_change'] = [
            TestScenario(
                name='priority_increase',
                description='Priority increased to High',
                event_data=self.event_generator.generate_issue_updated_event(
                    priority_change=True
                ),
                expected_trigger=True,
                expected_notification=True
            ),
            TestScenario(
                name='priority_to_critical',
                description='Priority changed to Highest (critical)',
                event_data=self.event_generator.generate_issue_updated_event(
                    priority_change=True
                ),
                expected_trigger=True,
                expected_notification=True,
                metadata={'critical_priority': True}
            )
        ]
        
        # Blocker Hook Scenarios
        scenarios['blocker'] = [
            TestScenario(
                name='blocker_detected',
                description='Issue marked as blocker',
                event_data=self.event_generator.generate_issue_updated_event(
                    **{'issue.fields.labels': ['blocker']}
                ),
                expected_trigger=True,
                expected_notification=True,
                metadata={'blocker_type': 'label'}
            ),
            TestScenario(
                name='dependency_blocker',
                description='Issue blocked by dependency',
                event_data=self.event_generator.generate_issue_updated_event(
                    **{'issue.fields.issuelinks': [
                        {'type': {'name': 'Blocks'}, 'outwardIssue': {'key': 'PROJ-123'}}
                    ]}
                ),
                expected_trigger=True,
                expected_notification=True,
                metadata={'blocker_type': 'dependency'}
            )
        ]
        
        return scenarios
    
    @pytest.mark.parametrize("hook_type,scenario", [
        (hook_type, scenario)
        for hook_type, scenarios in scenarios.items()
        for scenario in scenarios
    ] if 'scenarios' in locals() else [])
    async def test_hook_trigger_conditions(self, hook_type: str, scenario: TestScenario):
        """Test hook trigger conditions with various scenarios."""
        hook = self._create_hook(hook_type)
        enriched_event = self._create_enriched_event(scenario.event_data)
        
        # Test can_handle method
        can_handle = await hook.can_handle(enriched_event)
        assert can_handle == scenario.expected_trigger, \
            f"Hook {hook_type} trigger condition failed for scenario {scenario.name}"
        
        if can_handle:
            # Test execution
            with patch('devsync_ai.services.slack.SlackService') as mock_slack:
                mock_slack.return_value.send_message = AsyncMock(return_value={'ok': True})
                
                result = await hook.execute(enriched_event)
                
                # Validate execution result
                self.assertion_helpers.assert_hook_triggered(result, True)
                self.assertion_helpers.assert_notification_sent(result, scenario.expected_notification)
                
                if scenario.expected_execution_time_ms:
                    self.assertion_helpers.assert_execution_time_within_bounds(
                        result, scenario.expected_execution_time_ms
                    )
                
                if scenario.expected_errors:
                    self.assertion_helpers.assert_specific_errors(result, scenario.expected_errors)
                else:
                    self.assertion_helpers.assert_no_errors(result)
                
                if scenario.metadata:
                    self.assertion_helpers.assert_metadata_contains(result, scenario.metadata)
    
    async def test_edge_cases(self):
        """Test hook behavior with edge case events."""
        edge_cases = self.event_generator.generate_edge_case_events()
        
        for hook_type in ['status_change', 'assignment', 'comment']:
            hook = self._create_hook(hook_type)
            
            for edge_case in edge_cases:
                enriched_event = self._create_enriched_event(edge_case['event'])
                
                try:
                    # Should not crash on edge cases
                    can_handle = await hook.can_handle(enriched_event)
                    
                    if can_handle:
                        result = await hook.execute(enriched_event)
                        # Should complete execution even with edge case data
                        assert result.status in [HookStatus.SUCCESS, HookStatus.FAILED]
                        
                except Exception as e:
                    pytest.fail(f"Hook {hook_type} crashed on edge case {edge_case['name']}: {e}")
    
    async def test_performance_benchmarks(self):
        """Test hook performance against defined benchmarks."""
        for hook_type, benchmark in self.performance_benchmarks.items():
            hook = self._create_hook(hook_type)
            scenarios = self.test_scenarios.get(hook_type, [])
            
            if not scenarios:
                continue
            
            execution_times = []
            success_count = 0
            error_count = 0
            
            # Run multiple iterations for statistical significance
            for _ in range(50):
                scenario = random.choice(scenarios)
                enriched_event = self._create_enriched_event(scenario.event_data)
                
                start_time = time.time()
                
                try:
                    if await hook.can_handle(enriched_event):
                        with patch('devsync_ai.services.slack.SlackService') as mock_slack:
                            mock_slack.return_value.send_message = AsyncMock(return_value={'ok': True})
                            
                            result = await hook.execute(enriched_event)
                            
                            execution_time_ms = (time.time() - start_time) * 1000
                            execution_times.append(execution_time_ms)
                            
                            if result.status == HookStatus.SUCCESS:
                                success_count += 1
                            else:
                                error_count += 1
                
                except Exception:
                    error_count += 1
            
            if execution_times:
                # Validate performance metrics
                avg_execution_time = sum(execution_times) / len(execution_times)
                max_execution_time = max(execution_times)
                success_rate = success_count / (success_count + error_count) if (success_count + error_count) > 0 else 0
                error_rate = error_count / (success_count + error_count) if (success_count + error_count) > 0 else 0
                
                assert avg_execution_time <= benchmark.max_execution_time_ms, \
                    f"Average execution time {avg_execution_time:.2f}ms exceeded benchmark {benchmark.max_execution_time_ms}ms for {hook_type}"
                
                assert success_rate >= benchmark.min_success_rate, \
                    f"Success rate {success_rate:.3f} below benchmark {benchmark.min_success_rate} for {hook_type}"
                
                assert error_rate <= benchmark.max_error_rate, \
                    f"Error rate {error_rate:.3f} exceeded benchmark {benchmark.max_error_rate} for {hook_type}"
    
    async def test_configuration_validation(self):
        """Test hook configuration validation with various scenarios."""
        test_configs = [
            # Valid configuration
            {
                'name': 'valid_config',
                'config': HookConfiguration(
                    hook_id='test_hook_1',
                    hook_type='status_change',
                    team_id='team_alpha',
                    enabled=True,
                    notification_channels=['#general'],
                    rate_limit_per_hour=100,
                    retry_attempts=3,
                    timeout_seconds=30
                ),
                'should_be_valid': True
            },
            # Missing required fields
            {
                'name': 'missing_hook_id',
                'config': HookConfiguration(
                    hook_id='',
                    hook_type='status_change',
                    team_id='team_alpha'
                ),
                'should_be_valid': False,
                'expected_errors': ['Hook ID is required']
            },
            # Invalid rate limit
            {
                'name': 'invalid_rate_limit',
                'config': HookConfiguration(
                    hook_id='test_hook_2',
                    hook_type='status_change',
                    team_id='team_alpha',
                    rate_limit_per_hour=-1
                ),
                'should_be_valid': False,
                'expected_errors': ['Rate limit must be positive']
            },
            # Invalid timeout
            {
                'name': 'invalid_timeout',
                'config': HookConfiguration(
                    hook_id='test_hook_3',
                    hook_type='status_change',
                    team_id='team_alpha',
                    timeout_seconds=0
                ),
                'should_be_valid': False,
                'expected_errors': ['Timeout must be positive']
            }
        ]
        
        for test_config in test_configs:
            hook = StatusChangeHook('test_hook', test_config['config'])
            validation_errors = await hook.validate_configuration()
            
            if test_config['should_be_valid']:
                assert len(validation_errors) == 0, \
                    f"Expected valid configuration {test_config['name']}, but got errors: {validation_errors}"
            else:
                assert len(validation_errors) > 0, \
                    f"Expected invalid configuration {test_config['name']}, but no errors found"
                
                if 'expected_errors' in test_config:
                    for expected_error in test_config['expected_errors']:
                        assert any(expected_error in error for error in validation_errors), \
                            f"Expected error '{expected_error}' not found in {validation_errors}"
    
    async def test_error_handling_and_recovery(self):
        """Test error handling and graceful degradation."""
        hook = self._create_hook('status_change')
        event = self._create_enriched_event(
            self.event_generator.generate_issue_updated_event()
        )
        
        # Test Slack service failure
        with patch('devsync_ai.services.slack.SlackService') as mock_slack:
            mock_slack.return_value.send_message = AsyncMock(
                side_effect=Exception("Slack API error")
            )
            
            result = await hook.execute(event)
            
            # Should handle error gracefully
            assert result.status == HookStatus.FAILED
            assert len(result.errors) > 0
            assert any("Slack API error" in error for error in result.errors)
        
        # Test timeout handling
        with patch('devsync_ai.services.slack.SlackService') as mock_slack:
            async def slow_send_message(*args, **kwargs):
                await asyncio.sleep(2)  # Simulate slow response
                return {'ok': True}
            
            mock_slack.return_value.send_message = slow_send_message
            
            # Configure short timeout
            hook.configuration.timeout_seconds = 1
            
            result = await hook.execute(event)
            
            # Should timeout and handle gracefully
            assert result.status == HookStatus.FAILED
            assert any("timeout" in error.lower() for error in result.errors)
    
    def _create_hook(self, hook_type: str) -> AgentHook:
        """Create a hook instance for testing."""
        config = HookConfiguration(
            hook_id=f'test_{hook_type}_hook',
            hook_type=hook_type,
            team_id='test_team',
            enabled=True,
            notification_channels=['#test'],
            rate_limit_per_hour=100,
            retry_attempts=3,
            timeout_seconds=30
        )
        
        hook_classes = {
            'status_change': StatusChangeHook,
            'assignment': AssignmentHook,
            'comment': CommentHook,
            'priority_change': PriorityChangeHook,
            'blocker': BlockerHook
        }
        
        hook_class = hook_classes.get(hook_type, StatusChangeHook)
        return hook_class(config.hook_id, config)
    
    def _create_enriched_event(self, event_data: Dict[str, Any]) -> EnrichedEvent:
        """Create an enriched event for testing."""
        from devsync_ai.core.agent_hooks import ProcessedEvent, Stakeholder
        
        # Create base processed event
        processed_event = ProcessedEvent(
            event_id=str(random.randint(10000, 99999)),
            event_type=event_data.get('webhookEvent', 'jira:issue_updated'),
            timestamp=datetime.now(timezone.utc),
            jira_event_data=event_data,
            ticket_key=event_data.get('issue', {}).get('key', 'TEST-123'),
            project_key=event_data.get('issue', {}).get('fields', {}).get('project', {}).get('key', 'TEST'),
            raw_payload=event_data
        )
        
        # Create stakeholders
        stakeholders = []
        if 'issue' in event_data and 'fields' in event_data['issue']:
            fields = event_data['issue']['fields']
            
            if fields.get('assignee'):
                stakeholders.append(Stakeholder(
                    user_id=fields['assignee']['accountId'],
                    display_name=fields['assignee']['displayName'],
                    email=fields['assignee'].get('emailAddress'),
                    role='assignee'
                ))
            
            if fields.get('reporter'):
                stakeholders.append(Stakeholder(
                    user_id=fields['reporter']['accountId'],
                    display_name=fields['reporter']['displayName'],
                    email=fields['reporter'].get('emailAddress'),
                    role='reporter'
                ))
        
        # Create classification
        classification = EventClassification(
            category=EventCategory.STATUS_CHANGE,
            urgency=UrgencyLevel.MEDIUM,
            significance=SignificanceLevel.MODERATE,
            affected_teams=['test_team'],
            routing_hints={'channel': '#test'},
            keywords=['test', 'hook']
        )
        
        # Create enriched event
        enriched_event = EnrichedEvent(
            event_id=processed_event.event_id,
            event_type=processed_event.event_type,
            timestamp=processed_event.timestamp,
            jira_event_data=processed_event.jira_event_data,
            ticket_key=processed_event.ticket_key,
            project_key=processed_event.project_key,
            raw_payload=processed_event.raw_payload,
            ticket_details=event_data.get('issue'),
            stakeholders=stakeholders,
            classification=classification,
            context_data={'test': True}
        )
        
        return enriched_event


# Pytest fixtures for the test suite
@pytest.fixture
def hook_test_suite():
    """Fixture providing a configured HookTestSuite instance."""
    return HookTestSuite()


@pytest.fixture
def jira_event_generator():
    """Fixture providing a JIRA event generator."""
    return JIRAEventGenerator()


@pytest.fixture
def hook_assertion_helpers():
    """Fixture providing hook assertion helpers."""
    return HookAssertionHelpers()