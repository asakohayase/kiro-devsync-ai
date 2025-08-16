"""
Tests for Hook Event Processor.

This module contains comprehensive tests for the HookEventProcessor class,
covering event parsing, validation, classification, and enrichment scenarios.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from devsync_ai.core.hook_event_processor import (
    HookEventProcessor,
    EventTypeClassifier,
    EventValidationResult,
    EventEnrichmentResult
)
from devsync_ai.core.agent_hooks import (
    ProcessedEvent,
    EnrichedEvent,
    EventCategory,
    UrgencyLevel,
    SignificanceLevel,
    EventClassification,
    Stakeholder
)
from devsync_ai.services.jira import JiraService, JiraAPIError
from devsync_ai.models.core import JiraTicket


class TestEventTypeClassifier:
    """Test cases for EventTypeClassifier."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = EventTypeClassifier()
    
    def test_classify_event_category_direct_mapping(self):
        """Test direct event type mapping."""
        test_cases = [
            ('jira:issue_created', {}, EventCategory.CREATION),
            ('jira:issue_assigned', {}, EventCategory.ASSIGNMENT),
            ('jira:issue_commented', {}, EventCategory.COMMENT),
            ('jira:issue_transitioned', {}, EventCategory.TRANSITION),
            ('jira:issue_priority_changed', {}, EventCategory.PRIORITY_CHANGE),
        ]
        
        for event_type, issue_data, expected_category in test_cases:
            result = self.classifier.classify_event_category(event_type, issue_data)
            assert result == expected_category
    
    def test_classify_blocker_event_by_status(self):
        """Test blocker event classification by status."""
        issue_data = {
            'fields': {
                'status': {'name': 'Blocked'},
                'priority': {'name': 'Medium'}
            }
        }
        
        result = self.classifier.classify_event_category('jira:issue_updated', issue_data)
        assert result == EventCategory.BLOCKER
    
    def test_classify_blocker_event_by_labels(self):
        """Test blocker event classification by labels."""
        issue_data = {
            'fields': {
                'status': {'name': 'In Progress'},
                'labels': ['blocker', 'urgent'],
                'priority': {'name': 'Medium'}
            }
        }
        
        result = self.classifier.classify_event_category('jira:issue_updated', issue_data)
        assert result == EventCategory.BLOCKER
    
    def test_classify_blocker_event_by_summary(self):
        """Test blocker event classification by summary keywords."""
        issue_data = {
            'fields': {
                'status': {'name': 'In Progress'},
                'summary': 'Cannot proceed due to dependency issue',
                'priority': {'name': 'Medium'}
            }
        }
        
        result = self.classifier.classify_event_category('jira:issue_updated', issue_data)
        assert result == EventCategory.BLOCKER
    
    def test_determine_urgency_by_priority(self):
        """Test urgency determination by priority field."""
        test_cases = [
            ({'fields': {'priority': {'name': 'Critical'}}}, UrgencyLevel.CRITICAL),
            ({'fields': {'priority': {'name': 'Highest'}}}, UrgencyLevel.CRITICAL),
            ({'fields': {'priority': {'name': 'High'}}}, UrgencyLevel.HIGH),
            ({'fields': {'priority': {'name': 'Medium'}}}, UrgencyLevel.MEDIUM),
            ({'fields': {'priority': {'name': 'Low'}}}, UrgencyLevel.LOW),
            ({'fields': {}}, UrgencyLevel.LOW),  # No priority field
        ]
        
        for issue_data, expected_urgency in test_cases:
            result = self.classifier.determine_urgency(issue_data, EventCategory.STATUS_CHANGE)
            assert result == expected_urgency
    
    def test_determine_urgency_blocker_always_critical(self):
        """Test that blocker events are always critical urgency."""
        issue_data = {'fields': {'priority': {'name': 'Low'}}}
        
        result = self.classifier.determine_urgency(issue_data, EventCategory.BLOCKER)
        assert result == UrgencyLevel.CRITICAL
    
    def test_determine_significance_mapping(self):
        """Test significance determination based on category and urgency."""
        test_cases = [
            (EventCategory.BLOCKER, UrgencyLevel.LOW, SignificanceLevel.CRITICAL),
            (EventCategory.ASSIGNMENT, UrgencyLevel.HIGH, SignificanceLevel.MAJOR),
            (EventCategory.ASSIGNMENT, UrgencyLevel.MEDIUM, SignificanceLevel.MODERATE),
            (EventCategory.ASSIGNMENT, UrgencyLevel.LOW, SignificanceLevel.MINOR),
            (EventCategory.COMMENT, UrgencyLevel.HIGH, SignificanceLevel.MAJOR),
            (EventCategory.STATUS_CHANGE, UrgencyLevel.HIGH, SignificanceLevel.MAJOR),
            (EventCategory.STATUS_CHANGE, UrgencyLevel.MEDIUM, SignificanceLevel.MODERATE),
        ]
        
        for category, urgency, expected_significance in test_cases:
            result = self.classifier.determine_significance(category, urgency)
            assert result == expected_significance


class TestHookEventProcessor:
    """Test cases for HookEventProcessor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_jira_service = AsyncMock(spec=JiraService)
        self.processor = HookEventProcessor(jira_service=self.mock_jira_service)
    
    def create_sample_webhook_data(self, event_type='jira:issue_updated', **overrides):
        """Create sample webhook data for testing."""
        base_data = {
            'webhookEvent': event_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'issue': {
                'key': 'TEST-123',
                'fields': {
                    'summary': 'Test issue summary',
                    'description': 'Test issue description',
                    'status': {'name': 'In Progress', 'id': '3'},
                    'priority': {'name': 'Medium', 'id': '3'},
                    'issuetype': {'name': 'Task', 'subtask': False, 'id': '10001'},
                    'assignee': {
                        'accountId': 'user123',
                        'displayName': 'John Doe',
                        'emailAddress': 'john.doe@example.com'
                    },
                    'reporter': {
                        'accountId': 'user456',
                        'displayName': 'Jane Smith',
                        'emailAddress': 'jane.smith@example.com'
                    },
                    'created': '2024-01-01T10:00:00.000Z',
                    'updated': '2024-01-01T12:00:00.000Z',
                    'labels': ['backend', 'urgent'],
                    'components': [{'name': 'API'}],
                    'fixVersions': [{'name': 'v1.2.0'}]
                }
            }
        }
        
        # Apply overrides
        for key, value in overrides.items():
            if '.' in key:
                # Handle nested keys like 'issue.fields.status.name'
                keys = key.split('.')
                target = base_data
                for k in keys[:-1]:
                    target = target[k]
                target[keys[-1]] = value
            else:
                base_data[key] = value
        
        return base_data
    
    @pytest.mark.asyncio
    async def test_process_webhook_event_success(self):
        """Test successful webhook event processing."""
        webhook_data = self.create_sample_webhook_data()
        
        processed_event, validation_result = await self.processor.process_webhook_event(webhook_data)
        
        assert validation_result.valid
        assert len(validation_result.errors) == 0
        assert processed_event.event_type == 'jira:issue_updated'
        assert processed_event.ticket_key == 'TEST-123'
        assert processed_event.project_key == 'TEST'
        assert processed_event.event_id  # Should be auto-generated
        assert processed_event.raw_payload == webhook_data
    
    @pytest.mark.asyncio
    async def test_process_webhook_event_validation_disabled(self):
        """Test webhook processing with validation disabled."""
        webhook_data = {'invalid': 'data'}
        
        processed_event, validation_result = await self.processor.process_webhook_event(
            webhook_data, validate_structure=False
        )
        
        assert validation_result.valid  # Validation was skipped
        assert processed_event.event_type == 'unknown'
        assert processed_event.ticket_key == 'UNKNOWN'
    
    @pytest.mark.asyncio
    async def test_validate_event_structure_valid(self):
        """Test validation of valid event structure."""
        webhook_data = self.create_sample_webhook_data()
        
        result = await self.processor.validate_event_structure(webhook_data)
        
        assert result.valid
        assert len(result.errors) == 0
        assert result.event_type == 'jira:issue_updated'
        assert result.ticket_key == 'TEST-123'
    
    @pytest.mark.asyncio
    async def test_validate_event_structure_missing_webhook_event(self):
        """Test validation with missing webhookEvent field."""
        webhook_data = {'issue': {'key': 'TEST-123', 'fields': {}}}
        
        result = await self.processor.validate_event_structure(webhook_data)
        
        assert not result.valid
        assert "Missing required field: 'webhookEvent'" in result.errors
    
    @pytest.mark.asyncio
    async def test_validate_event_structure_missing_issue_data(self):
        """Test validation with missing issue data for issue event."""
        webhook_data = {'webhookEvent': 'jira:issue_updated'}
        
        result = await self.processor.validate_event_structure(webhook_data)
        
        assert not result.valid
        assert "Missing 'issue' data for issue-related event" in result.errors
    
    @pytest.mark.asyncio
    async def test_validate_event_structure_invalid_issue_key(self):
        """Test validation with invalid issue key."""
        webhook_data = {
            'webhookEvent': 'jira:issue_updated',
            'issue': {'fields': {}}  # Missing key
        }
        
        result = await self.processor.validate_event_structure(webhook_data)
        
        assert not result.valid
        assert "Missing required field: 'issue.key'" in result.errors
    
    @pytest.mark.asyncio
    async def test_validate_event_structure_warnings(self):
        """Test validation that generates warnings."""
        webhook_data = {
            'webhookEvent': 'custom:event_type',  # Unusual format
            'issue': {
                'key': 'INVALIDKEY',  # No hyphen
                'fields': {}  # Missing summary, status, etc.
            }
        }
        
        result = await self.processor.validate_event_structure(webhook_data)
        
        assert result.valid  # Should still be valid despite warnings
        assert len(result.warnings) > 0
        assert any('Unexpected webhook event format' in w for w in result.warnings)
        assert any('Unusual ticket key format' in w for w in result.warnings)
        assert any('Missing issue summary' in w for w in result.warnings)
    
    @pytest.mark.asyncio
    async def test_validate_comment_event_structure(self):
        """Test validation of comment event structure."""
        webhook_data = {
            'webhookEvent': 'jira:issue_commented',
            'issue': {
                'key': 'TEST-123', 
                'fields': {
                    'summary': 'Test issue',
                    'status': {'name': 'Open'}
                }
            },
            'comment': {
                'id': '12345',
                'body': 'This is a test comment',
                'author': {'displayName': 'John Doe'}
            }
        }
        
        result = await self.processor.validate_event_structure(webhook_data)
        
        assert result.valid
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_comment_event_missing_comment(self):
        """Test validation of comment event with missing comment data."""
        webhook_data = {
            'webhookEvent': 'jira:issue_commented',
            'issue': {'key': 'TEST-123', 'fields': {}}
        }
        
        result = await self.processor.validate_event_structure(webhook_data)
        
        assert not result.valid
        assert "Missing comment data for comment event" in result.errors
    
    @pytest.mark.asyncio
    async def test_enrich_event_success(self):
        """Test successful event enrichment."""
        webhook_data = self.create_sample_webhook_data()
        processed_event, _ = await self.processor.process_webhook_event(webhook_data)
        
        # Mock JIRA service response
        mock_ticket = JiraTicket(
            key='TEST-123',
            summary='Test issue',
            status='In Progress',
            assignee='John Doe',
            priority='Medium',
            story_points=5,
            sprint='Sprint 1',
            blocked=False,
            last_updated=datetime.now(),
            time_in_status=timedelta(hours=2)
        )
        self.mock_jira_service.get_ticket_details.return_value = mock_ticket
        
        result = await self.processor.enrich_event(processed_event)
        
        assert result.success
        assert result.enriched_event is not None
        assert result.enriched_event.classification is not None
        assert len(result.enriched_event.stakeholders) > 0
        assert result.processing_time_ms > 0
        
        # Verify classification
        classification = result.enriched_event.classification
        assert classification.category == EventCategory.STATUS_CHANGE
        assert classification.urgency == UrgencyLevel.MEDIUM
        assert classification.significance == SignificanceLevel.MODERATE
        assert 'test' in classification.affected_teams
    
    @pytest.mark.asyncio
    async def test_enrich_event_blocker_classification(self):
        """Test enrichment of blocker event."""
        webhook_data = self.create_sample_webhook_data()
        webhook_data['issue']['fields']['status']['name'] = 'Blocked'
        webhook_data['issue']['fields']['priority']['name'] = 'High'
        
        processed_event, _ = await self.processor.process_webhook_event(webhook_data)
        result = await self.processor.enrich_event(processed_event)
        
        assert result.success
        classification = result.enriched_event.classification
        assert classification.category == EventCategory.BLOCKER
        assert classification.urgency == UrgencyLevel.CRITICAL
        assert classification.significance == SignificanceLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_enrich_event_stakeholder_extraction(self):
        """Test stakeholder extraction during enrichment."""
        webhook_data = self.create_sample_webhook_data()
        processed_event, _ = await self.processor.process_webhook_event(webhook_data)
        
        result = await self.processor.enrich_event(processed_event)
        
        assert result.success
        stakeholders = result.enriched_event.stakeholders
        assert len(stakeholders) == 2  # Assignee and reporter
        
        # Check assignee
        assignee = next((s for s in stakeholders if s.role == 'assignee'), None)
        assert assignee is not None
        assert assignee.display_name == 'John Doe'
        assert assignee.email == 'john.doe@example.com'
        assert assignee.team_id == 'test'
        
        # Check reporter
        reporter = next((s for s in stakeholders if s.role == 'reporter'), None)
        assert reporter is not None
        assert reporter.display_name == 'Jane Smith'
    
    @pytest.mark.asyncio
    async def test_enrich_event_comment_stakeholder(self):
        """Test stakeholder extraction for comment events."""
        webhook_data = self.create_sample_webhook_data('jira:issue_commented')
        webhook_data['comment'] = {
            'author': {
                'accountId': 'user789',
                'displayName': 'Bob Wilson',
                'emailAddress': 'bob.wilson@example.com'
            },
            'body': 'This is a comment'
        }
        
        processed_event, _ = await self.processor.process_webhook_event(webhook_data)
        result = await self.processor.enrich_event(processed_event)
        
        assert result.success
        stakeholders = result.enriched_event.stakeholders
        
        # Should have assignee, reporter, and commenter
        commenter = next((s for s in stakeholders if s.role == 'commenter'), None)
        assert commenter is not None
        assert commenter.display_name == 'Bob Wilson'
    
    @pytest.mark.asyncio
    async def test_enrich_event_team_determination(self):
        """Test team determination during enrichment."""
        webhook_data = self.create_sample_webhook_data()
        webhook_data['issue']['fields']['components'] = [
            {'name': 'Frontend Team'},
            {'name': 'Backend API'}
        ]
        webhook_data['issue']['fields']['labels'] = ['team-mobile', 'urgent']
        
        processed_event, _ = await self.processor.process_webhook_event(webhook_data)
        result = await self.processor.enrich_event(processed_event)
        
        assert result.success
        affected_teams = result.enriched_event.classification.affected_teams
        
        # Should include project team, component teams, and label teams
        assert 'test' in affected_teams  # From project key
        assert 'frontend-team' in affected_teams  # From component
        assert 'backend-api' in affected_teams  # From component
        assert 'mobile' in affected_teams  # From team- label
    
    @pytest.mark.asyncio
    async def test_enrich_event_routing_hints(self):
        """Test routing hints generation during enrichment."""
        webhook_data = self.create_sample_webhook_data()
        processed_event, _ = await self.processor.process_webhook_event(webhook_data)
        
        result = await self.processor.enrich_event(processed_event)
        
        assert result.success
        routing_hints = result.enriched_event.classification.routing_hints
        
        assert routing_hints['project'] == 'TEST'
        assert routing_hints['ticket_key'] == 'TEST-123'
        assert routing_hints['issue_type'] == 'Task'
        assert routing_hints['priority'] == 'Medium'
        assert routing_hints['status'] == 'In Progress'
        assert routing_hints['assignee'] == 'John Doe'
        assert 'API' in routing_hints['components']
        assert 'backend' in routing_hints['labels']
    
    @pytest.mark.asyncio
    async def test_enrich_event_keyword_extraction(self):
        """Test keyword extraction during enrichment."""
        webhook_data = self.create_sample_webhook_data()
        webhook_data['issue']['fields']['summary'] = 'Critical database performance issue'
        
        processed_event, _ = await self.processor.process_webhook_event(webhook_data)
        result = await self.processor.enrich_event(processed_event)
        
        assert result.success
        keywords = result.enriched_event.classification.keywords
        
        # Should include words from summary, status, priority, etc.
        assert 'critical' in keywords
        assert 'database' in keywords
        assert 'performance' in keywords
        assert 'issue' in keywords
        assert 'medium' in keywords  # From priority
        assert 'task' in keywords  # From issue type
    
    @pytest.mark.asyncio
    async def test_enrich_event_with_jira_service_integration(self):
        """Test enrichment with JIRA service integration."""
        webhook_data = self.create_sample_webhook_data()
        processed_event, _ = await self.processor.process_webhook_event(webhook_data)
        
        # Mock JIRA service response
        mock_ticket = JiraTicket(
            key='TEST-123',
            summary='Test issue',
            status='In Progress',
            assignee='John Doe',
            priority='Medium',
            story_points=8,
            sprint='Sprint 2',
            blocked=True,
            last_updated=datetime.now(),
            time_in_status=timedelta(hours=24)
        )
        self.mock_jira_service.get_ticket_details.return_value = mock_ticket
        
        result = await self.processor.enrich_event(processed_event)
        
        assert result.success
        ticket_details = result.enriched_event.ticket_details
        
        # Should include enhanced details from JIRA service
        assert ticket_details['story_points'] == 8
        assert ticket_details['sprint'] == 'Sprint 2'
        assert ticket_details['blocked'] is True
        assert ticket_details['time_in_status'] == 24 * 3600  # 24 hours in seconds
    
    @pytest.mark.asyncio
    async def test_enrich_event_jira_service_error(self):
        """Test enrichment when JIRA service fails."""
        webhook_data = self.create_sample_webhook_data()
        processed_event, _ = await self.processor.process_webhook_event(webhook_data)
        
        # Mock JIRA service to raise an error
        self.mock_jira_service.get_ticket_details.side_effect = JiraAPIError("API Error")
        
        result = await self.processor.enrich_event(processed_event)
        
        # Should still succeed even if JIRA service fails
        assert result.success
        assert result.enriched_event is not None
        
        # Should not have enhanced JIRA details
        ticket_details = result.enriched_event.ticket_details
        assert 'story_points' not in ticket_details or ticket_details['story_points'] is None
    
    @pytest.mark.asyncio
    async def test_enrich_event_error_handling(self):
        """Test error handling during enrichment."""
        # Create an invalid processed event that will cause errors
        processed_event = ProcessedEvent(
            event_id="test-id",
            event_type="invalid",
            timestamp=datetime.now(timezone.utc),
            jira_event_data=None,  # This will cause errors
            ticket_key="TEST-123",
            project_key="TEST",
            raw_payload={}
        )
        
        result = await self.processor.enrich_event(processed_event)
        
        assert not result.success
        assert len(result.errors) > 0
        assert result.enriched_event is None
        assert result.processing_time_ms > 0
    
    def test_get_metrics(self):
        """Test metrics collection."""
        # Simulate some processing
        self.processor._events_processed = 100
        self.processor._events_enriched = 95
        self.processor._validation_failures = 3
        self.processor._enrichment_failures = 2
        
        metrics = self.processor.get_metrics()
        
        assert metrics['events_processed'] == 100
        assert metrics['events_enriched'] == 95
        assert metrics['validation_failures'] == 3
        assert metrics['enrichment_failures'] == 2
        assert metrics['success_rate'] == 0.95
        assert metrics['validation_success_rate'] == 0.97
        assert metrics['enrichment_success_rate'] == 95/97  # enriched / (processed - validation_failures)
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check when everything is healthy."""
        # Mock JIRA service authentication
        self.mock_jira_service.test_authentication.return_value = AsyncMock()
        
        # Set good metrics
        self.processor._events_processed = 100
        self.processor._events_enriched = 95
        self.processor._validation_failures = 2
        
        health = await self.processor.health_check()
        
        assert health['status'] == 'healthy'
        assert health['jira_service_available'] is True
        assert 'metrics' in health
        assert health['components']['jira_service'] == 'ok'
    
    @pytest.mark.asyncio
    async def test_health_check_degraded_jira_service(self):
        """Test health check when JIRA service is unavailable."""
        # Mock JIRA service authentication failure
        self.mock_jira_service.test_authentication.side_effect = JiraAPIError("Auth failed")
        
        health = await self.processor.health_check()
        
        assert health['status'] == 'degraded'
        assert health['jira_service_available'] is False
        assert health['components']['jira_service'] == 'degraded'
    
    @pytest.mark.asyncio
    async def test_health_check_warning_low_success_rate(self):
        """Test health check with low validation success rate."""
        # Mock JIRA service as healthy
        self.mock_jira_service.test_authentication.return_value = AsyncMock()
        
        # Set poor validation metrics
        self.processor._events_processed = 100
        self.processor._validation_failures = 20  # 80% success rate
        
        health = await self.processor.health_check()
        
        assert health['status'] == 'warning'
        assert health['metrics']['validation_success_rate'] == 0.8


@pytest.mark.asyncio
async def test_integration_full_event_processing():
    """Integration test for full event processing pipeline."""
    # Create processor without JIRA service for this test
    processor = HookEventProcessor()
    
    # Create a comprehensive webhook event
    webhook_data = {
        'webhookEvent': 'jira:issue_updated',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'issue': {
            'key': 'PROJ-456',
            'fields': {
                'summary': 'Critical production bug blocking deployment',
                'description': 'Database connection timeout causing service failures',
                'status': {'name': 'Blocked', 'id': '10001'},
                'priority': {'name': 'Critical', 'id': '1'},
                'issuetype': {'name': 'Bug', 'subtask': False, 'id': '10004'},
                'assignee': {
                    'accountId': 'dev123',
                    'displayName': 'Alice Developer',
                    'emailAddress': 'alice@company.com'
                },
                'reporter': {
                    'accountId': 'pm456',
                    'displayName': 'Bob Manager',
                    'emailAddress': 'bob@company.com'
                },
                'created': '2024-01-01T08:00:00.000Z',
                'updated': '2024-01-01T14:30:00.000Z',
                'labels': ['production', 'blocker', 'team-backend'],
                'components': [
                    {'name': 'Database Layer'},
                    {'name': 'API Gateway'}
                ],
                'fixVersions': [{'name': 'v2.1.0'}]
            }
        },
        'changelog': {
            'items': [
                {
                    'field': 'status',
                    'fromString': 'In Progress',
                    'toString': 'Blocked'
                }
            ]
        }
    }
    
    # Process the webhook event
    processed_event, validation_result = await processor.process_webhook_event(webhook_data)
    
    # Verify processing
    assert validation_result.valid
    assert processed_event.event_type == 'jira:issue_updated'
    assert processed_event.ticket_key == 'PROJ-456'
    assert processed_event.project_key == 'PROJ'
    
    # Enrich the event
    enrichment_result = await processor.enrich_event(processed_event)
    
    # Verify enrichment
    assert enrichment_result.success
    enriched_event = enrichment_result.enriched_event
    
    # Verify classification
    assert enriched_event.classification.category == EventCategory.BLOCKER
    assert enriched_event.classification.urgency == UrgencyLevel.CRITICAL
    assert enriched_event.classification.significance == SignificanceLevel.CRITICAL
    
    # Verify stakeholders
    assert len(enriched_event.stakeholders) == 2
    assignee = next((s for s in enriched_event.stakeholders if s.role == 'assignee'), None)
    assert assignee.display_name == 'Alice Developer'
    
    # Verify affected teams
    affected_teams = enriched_event.classification.affected_teams
    assert 'proj' in affected_teams  # From project
    assert 'backend' in affected_teams  # From team- label
    assert 'database-layer' in affected_teams  # From component
    
    # Verify routing hints
    routing_hints = enriched_event.classification.routing_hints
    assert routing_hints['priority'] == 'Critical'
    assert routing_hints['status'] == 'Blocked'
    assert 'production' in routing_hints['labels']
    
    # Verify keywords
    keywords = enriched_event.classification.keywords
    assert 'critical' in keywords
    assert 'production' in keywords
    assert 'blocker' in keywords
    assert 'blocked' in keywords


if __name__ == '__main__':
    pytest.main([__file__, '-v'])