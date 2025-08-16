"""
Tests for the Event Classification Engine.

This module tests the EventClassificationEngine's ability to accurately
classify JIRA events, determine urgency and significance, extract stakeholders,
and handle various edge cases.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from devsync_ai.core.event_classification_engine import (
    EventClassificationEngine,
    ClassificationMetrics,
    BlockerPattern
)
from devsync_ai.core.agent_hooks import (
    ProcessedEvent,
    EventCategory,
    UrgencyLevel,
    SignificanceLevel,
    Stakeholder
)


# Fixtures at module level
@pytest.fixture
def engine():
    """Create an EventClassificationEngine instance."""
    return EventClassificationEngine()

@pytest.fixture
def sample_processed_event():
    """Create a sample ProcessedEvent for testing."""
    return ProcessedEvent(
        event_id="test-event-123",
        event_type="jira:issue_updated",
        timestamp=datetime.now(timezone.utc),
        jira_event_data={
            "key": "TEST-123",
            "fields": {
                "summary": "Test issue summary",
                "description": "Test issue description",
                "status": {"name": "In Progress", "id": "3"},
                "priority": {"name": "High", "id": "2"},
                "issuetype": {"name": "Bug", "subtask": False, "id": "1"},
                "assignee": {
                    "accountId": "user123",
                    "displayName": "John Doe",
                    "emailAddress": "john@example.com"
                },
                "reporter": {
                    "accountId": "user456",
                    "displayName": "Jane Smith",
                    "emailAddress": "jane@example.com"
                },
                "labels": ["backend", "urgent"],
                "components": [{"name": "API", "id": "1"}]
            }
        },
        ticket_key="TEST-123",
        project_key="TEST",
        raw_payload={}
    )

@pytest.fixture
def blocker_event():
    """Create a blocker event for testing."""
    return ProcessedEvent(
        event_id="blocker-event-123",
        event_type="jira:issue_updated",
        timestamp=datetime.now(timezone.utc),
        jira_event_data={
            "key": "TEST-456",
            "fields": {
                "summary": "System is blocked and cannot proceed",
                "description": "Critical blocker preventing deployment",
                "status": {"name": "Blocked", "id": "4"},
                "priority": {"name": "Critical", "id": "1"},
                "issuetype": {"name": "Bug", "subtask": False, "id": "1"},
                "labels": ["blocker", "production"]
            }
        },
        ticket_key="TEST-456",
        project_key="TEST",
        raw_payload={}
    )

@pytest.fixture
def comment_event():
    """Create a comment event for testing."""
    return ProcessedEvent(
        event_id="comment-event-123",
        event_type="jira:issue_commented",
        timestamp=datetime.now(timezone.utc),
        jira_event_data={
            "key": "TEST-789",
            "fields": {
                "summary": "Regular issue",
                "priority": {"name": "Medium", "id": "3"},
                "status": {"name": "In Progress", "id": "3"}
            }
        },
        ticket_key="TEST-789",
        project_key="TEST",
        raw_payload={
            "comment": {
                "body": "This is urgent! Production is down and we need immediate help!",
                "author": {
                    "accountId": "commenter123",
                    "displayName": "Emergency User",
                    "emailAddress": "emergency@example.com"
                }
            }
        }
    )

@pytest.fixture
def assignment_event():
    """Create an assignment event for testing."""
    return ProcessedEvent(
        event_id="assignment-event-123",
        event_type="jira:issue_assigned",
        timestamp=datetime.now(timezone.utc),
        jira_event_data={
            "key": "TEST-101",
            "fields": {
                "summary": "New feature implementation",
                "priority": {"name": "Medium", "id": "3"},
                "assignee": {
                    "accountId": "newuser123",
                    "displayName": "New Developer",
                    "emailAddress": "newdev@example.com"
                }
            }
        },
        ticket_key="TEST-101",
        project_key="TEST",
        raw_payload={
            "changelog": {
                "items": [{
                    "field": "assignee",
                    "from": "olduser456",
                    "fromString": "Old Developer",
                    "to": "newuser123",
                    "toString": "New Developer"
                }]
            }
        }
    )


class TestEventClassificationEngine:
    """Test suite for EventClassificationEngine."""


class TestEventCategoryClassification:
    """Test event category classification."""
    
    @pytest.mark.asyncio
    async def test_classify_blocker_event(self, engine, blocker_event):
        """Test classification of blocker events."""
        classification = await engine.classify_event(blocker_event)
        
        assert classification.category == EventCategory.BLOCKER
        assert classification.urgency == UrgencyLevel.CRITICAL
        assert classification.significance == SignificanceLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_classify_assignment_event(self, engine, assignment_event):
        """Test classification of assignment events."""
        classification = await engine.classify_event(assignment_event)
        
        assert classification.category == EventCategory.ASSIGNMENT
        assert classification.urgency == UrgencyLevel.MEDIUM
        assert classification.significance == SignificanceLevel.MODERATE
    
    @pytest.mark.asyncio
    async def test_classify_comment_event(self, engine, comment_event):
        """Test classification of comment events."""
        classification = await engine.classify_event(comment_event)
        
        assert classification.category == EventCategory.COMMENT
        # Should be high urgency due to urgent keywords in comment
        assert classification.urgency == UrgencyLevel.HIGH
        assert classification.significance == SignificanceLevel.MAJOR
    
    @pytest.mark.asyncio
    async def test_classify_status_change_event(self, engine, sample_processed_event):
        """Test classification of status change events."""
        classification = await engine.classify_event(sample_processed_event)
        
        # Should not be blocker despite high priority
        assert classification.category == EventCategory.STATUS_CHANGE
        assert classification.urgency == UrgencyLevel.HIGH
        assert classification.significance == SignificanceLevel.MAJOR


class TestUrgencyDetermination:
    """Test urgency level determination."""
    
    @pytest.mark.asyncio
    async def test_critical_priority_urgency(self, engine):
        """Test critical priority results in critical urgency."""
        event = ProcessedEvent(
            event_id="test",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "fields": {
                    "priority": {"name": "Critical", "id": "1"},
                    "summary": "Test issue"
                }
            },
            ticket_key="TEST-1",
            project_key="TEST",
            raw_payload={}
        )
        
        classification = await engine.classify_event(event)
        assert classification.urgency == UrgencyLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_urgent_keywords_increase_urgency(self, engine):
        """Test that urgent keywords increase urgency level."""
        event = ProcessedEvent(
            event_id="test",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "fields": {
                    "priority": {"name": "Low", "id": "4"},
                    "summary": "URGENT: Critical system failure",
                    "description": "Emergency situation requiring immediate attention"
                }
            },
            ticket_key="TEST-1",
            project_key="TEST",
            raw_payload={}
        )
        
        classification = await engine.classify_event(event)
        # Should be high despite low priority due to urgent keywords
        assert classification.urgency == UrgencyLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_production_keywords_increase_urgency(self, engine):
        """Test that production-related keywords increase urgency."""
        event = ProcessedEvent(
            event_id="test",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "fields": {
                    "priority": {"name": "Medium", "id": "3"},
                    "summary": "Production deployment issue",
                    "description": "Customer-facing feature is broken"
                }
            },
            ticket_key="TEST-1",
            project_key="TEST",
            raw_payload={}
        )
        
        classification = await engine.classify_event(event)
        assert classification.urgency == UrgencyLevel.HIGH


class TestStakeholderExtraction:
    """Test stakeholder extraction functionality."""
    
    @pytest.mark.asyncio
    async def test_extract_assignee_and_reporter(self, engine, sample_processed_event):
        """Test extraction of assignee and reporter stakeholders."""
        classification = await engine.classify_event(sample_processed_event)
        
        stakeholders = await engine._extract_stakeholders(sample_processed_event)
        
        assert len(stakeholders) == 2
        
        assignee = next((s for s in stakeholders if s.role == 'assignee'), None)
        assert assignee is not None
        assert assignee.user_id == "user123"
        assert assignee.display_name == "John Doe"
        assert assignee.email == "john@example.com"
        
        reporter = next((s for s in stakeholders if s.role == 'reporter'), None)
        assert reporter is not None
        assert reporter.user_id == "user456"
        assert reporter.display_name == "Jane Smith"
    
    @pytest.mark.asyncio
    async def test_extract_comment_author(self, engine, comment_event):
        """Test extraction of comment author as stakeholder."""
        stakeholders = await engine._extract_stakeholders(comment_event)
        
        commenter = next((s for s in stakeholders if s.role == 'commenter'), None)
        assert commenter is not None
        assert commenter.user_id == "commenter123"
        assert commenter.display_name == "Emergency User"
    
    @pytest.mark.asyncio
    async def test_extract_previous_assignee(self, engine, assignment_event):
        """Test extraction of previous assignee in assignment events."""
        stakeholders = await engine._extract_stakeholders(assignment_event)
        
        # Should have both new assignee and previous assignee
        assignee = next((s for s in stakeholders if s.role == 'assignee'), None)
        assert assignee is not None
        assert assignee.user_id == "newuser123"
        
        prev_assignee = next((s for s in stakeholders if s.role == 'previous_assignee'), None)
        assert prev_assignee is not None
        assert prev_assignee.user_id == "olduser456"


class TestTeamDetermination:
    """Test affected team determination."""
    
    @pytest.mark.asyncio
    async def test_determine_teams_from_project(self, engine, sample_processed_event):
        """Test team determination from project key."""
        teams = await engine._determine_affected_teams(sample_processed_event)
        
        assert "test" in teams  # Project key lowercased
    
    @pytest.mark.asyncio
    async def test_determine_teams_from_components(self, engine, sample_processed_event):
        """Test team determination from components."""
        teams = await engine._determine_affected_teams(sample_processed_event)
        
        assert "api" in teams  # Component name lowercased
    
    @pytest.mark.asyncio
    async def test_determine_teams_from_labels(self, engine):
        """Test team determination from team labels."""
        event = ProcessedEvent(
            event_id="test",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "fields": {
                    "labels": ["team-backend", "squad-api", "frontend"],
                    "summary": "Test issue"
                }
            },
            ticket_key="TEST-1",
            project_key="TEST",
            raw_payload={}
        )
        
        teams = await engine._determine_affected_teams(event)
        
        assert "backend" in teams  # From team-backend label
        assert "api" in teams      # From squad-api label
        assert "test" in teams     # From project key


class TestKeywordExtraction:
    """Test keyword extraction functionality."""
    
    @pytest.mark.asyncio
    async def test_extract_keywords_from_summary(self, engine, sample_processed_event):
        """Test keyword extraction from issue summary."""
        keywords = await engine._extract_keywords(sample_processed_event)
        
        assert "issue" in keywords
        assert "summary" in keywords
    
    @pytest.mark.asyncio
    async def test_extract_keywords_from_labels(self, engine, sample_processed_event):
        """Test keyword extraction from labels."""
        keywords = await engine._extract_keywords(sample_processed_event)
        
        assert "backend" in keywords
        assert "urgent" in keywords
    
    @pytest.mark.asyncio
    async def test_extract_keywords_from_status_priority(self, engine, sample_processed_event):
        """Test keyword extraction from status and priority."""
        keywords = await engine._extract_keywords(sample_processed_event)
        
        assert "in_progress" in keywords  # Status with spaces replaced
        assert "high" in keywords         # Priority
    
    @pytest.mark.asyncio
    async def test_keyword_filtering(self, engine):
        """Test that stop words are filtered out."""
        event = ProcessedEvent(
            event_id="test",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "fields": {
                    "summary": "This is a test with many common words that should be filtered",
                    "labels": []
                }
            },
            ticket_key="TEST-1",
            project_key="TEST",
            raw_payload={}
        )
        
        keywords = await engine._extract_keywords(event)
        
        # Stop words should be filtered out
        stop_words = {"this", "that", "with", "many", "should"}
        for stop_word in stop_words:
            assert stop_word not in keywords
        
        # Meaningful words should remain
        assert "test" in keywords
        assert "filtered" in keywords


class TestBlockerDetection:
    """Test blocker pattern detection."""
    
    @pytest.mark.asyncio
    async def test_detect_status_blocker(self, engine):
        """Test detection of status-based blockers."""
        event = ProcessedEvent(
            event_id="test",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "fields": {
                    "status": {"name": "Blocked", "id": "4"},
                    "summary": "Test issue"
                }
            },
            ticket_key="TEST-1",
            project_key="TEST",
            raw_payload={}
        )
        
        patterns = await engine.detect_blocker_patterns(event)
        
        status_blocker = next((p for p in patterns if p.pattern_type == 'status_blocker'), None)
        assert status_blocker is not None
        assert status_blocker.confidence == 0.9
        assert "Status: Blocked" in status_blocker.evidence[0]
    
    @pytest.mark.asyncio
    async def test_detect_keyword_blocker_in_summary(self, engine):
        """Test detection of keyword-based blockers in summary."""
        event = ProcessedEvent(
            event_id="test",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "fields": {
                    "summary": "Cannot proceed due to blocker",
                    "description": "Normal description"
                }
            },
            ticket_key="TEST-1",
            project_key="TEST",
            raw_payload={}
        )
        
        patterns = await engine.detect_blocker_patterns(event)
        
        keyword_blockers = [p for p in patterns if p.pattern_type == 'keyword_blocker']
        assert len(keyword_blockers) >= 1
        
        # Should find both "cannot proceed" and "blocker"
        evidence_text = " ".join([p.evidence[0] for p in keyword_blockers])
        assert "cannot proceed" in evidence_text or "blocker" in evidence_text
    
    @pytest.mark.asyncio
    async def test_detect_label_blocker(self, engine):
        """Test detection of blocker keywords in labels."""
        event = ProcessedEvent(
            event_id="test",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "fields": {
                    "summary": "Test issue",
                    "labels": ["blocked-by-dependency", "urgent"]
                }
            },
            ticket_key="TEST-1",
            project_key="TEST",
            raw_payload={}
        )
        
        patterns = await engine.detect_blocker_patterns(event)
        
        label_blocker = next((p for p in patterns if p.pattern_type == 'label_blocker'), None)
        assert label_blocker is not None
        assert label_blocker.confidence == 0.8


class TestRoutingHints:
    """Test routing hint generation."""
    
    @pytest.mark.asyncio
    async def test_generate_basic_routing_hints(self, engine, sample_processed_event):
        """Test generation of basic routing hints."""
        hints = await engine._generate_routing_hints(
            sample_processed_event, 
            EventCategory.STATUS_CHANGE, 
            UrgencyLevel.HIGH
        )
        
        assert hints['project'] == 'TEST'
        assert hints['ticket_key'] == 'TEST-123'
        assert hints['event_type'] == 'jira:issue_updated'
        assert hints['category'] == 'status_change'
        assert hints['urgency'] == 'high'
        assert hints['issue_type'] == 'Bug'
        assert hints['priority'] == 'High'
        assert hints['status'] == 'In Progress'
        assert hints['assignee'] == 'John Doe'
    
    @pytest.mark.asyncio
    async def test_generate_blocker_routing_hints(self, engine, blocker_event):
        """Test generation of routing hints for blocker events."""
        hints = await engine._generate_routing_hints(
            blocker_event, 
            EventCategory.BLOCKER, 
            UrgencyLevel.CRITICAL
        )
        
        assert hints['requires_immediate_attention'] is True
        assert hints['escalation_required'] is True
    
    @pytest.mark.asyncio
    async def test_generate_comment_routing_hints(self, engine, comment_event):
        """Test generation of routing hints for comment events."""
        hints = await engine._generate_routing_hints(
            comment_event, 
            EventCategory.COMMENT, 
            UrgencyLevel.HIGH
        )
        
        assert hints['comment_author'] == 'Emergency User'
        assert hints['comment_length'] > 0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_handle_missing_fields(self, engine):
        """Test handling of events with missing fields."""
        event = ProcessedEvent(
            event_id="test",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "fields": {}  # Empty fields
            },
            ticket_key="TEST-1",
            project_key="TEST",
            raw_payload={}
        )
        
        classification = await engine.classify_event(event)
        
        # Should not crash and provide default classification
        assert classification.category == EventCategory.STATUS_CHANGE
        assert classification.urgency == UrgencyLevel.LOW
        assert classification.significance == SignificanceLevel.MINOR
    
    @pytest.mark.asyncio
    async def test_handle_malformed_data(self, engine):
        """Test handling of malformed event data."""
        event = ProcessedEvent(
            event_id="test",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "fields": {
                    "status": "not_a_dict",  # Should be dict
                    "priority": None,        # Null value
                    "assignee": {"accountId": None}  # Null account ID
                }
            },
            ticket_key="TEST-1",
            project_key="TEST",
            raw_payload={}
        )
        
        classification = await engine.classify_event(event)
        
        # Should handle gracefully
        assert classification is not None
        assert isinstance(classification.category, EventCategory)
    
    @pytest.mark.asyncio
    async def test_handle_unknown_event_type(self, engine):
        """Test handling of unknown event types."""
        event = ProcessedEvent(
            event_id="test",
            event_type="jira:unknown_event",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "fields": {
                    "summary": "Test issue",
                    "priority": {"name": "Medium"}
                }
            },
            ticket_key="TEST-1",
            project_key="TEST",
            raw_payload={}
        )
        
        classification = await engine.classify_event(event)
        
        # Should default to STATUS_CHANGE for unknown events
        assert classification.category == EventCategory.STATUS_CHANGE
    
    @pytest.mark.asyncio
    async def test_handle_empty_stakeholders(self, engine):
        """Test handling when no stakeholders can be extracted."""
        event = ProcessedEvent(
            event_id="test",
            event_type="jira:issue_updated",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={
                "fields": {
                    "summary": "Test issue",
                    "assignee": None,
                    "reporter": None
                }
            },
            ticket_key="TEST-1",
            project_key="TEST",
            raw_payload={}
        )
        
        stakeholders = await engine._extract_stakeholders(event)
        
        # Should return empty list without crashing
        assert isinstance(stakeholders, list)
        assert len(stakeholders) == 0


class TestMetrics:
    """Test metrics collection and reporting."""
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, engine, sample_processed_event):
        """Test that metrics are collected during classification."""
        initial_count = engine.metrics.events_classified
        
        await engine.classify_event(sample_processed_event)
        
        assert engine.metrics.events_classified == initial_count + 1
        assert engine.metrics.classification_time_ms > 0
        assert 'high' in engine.metrics.urgency_distribution
        assert 'status_change' in engine.metrics.category_distribution
    
    def test_metrics_reset(self, engine):
        """Test metrics reset functionality."""
        # Set some metrics
        engine.metrics.events_classified = 10
        engine.metrics.urgency_distribution['high'] = 5
        
        engine.reset_metrics()
        
        assert engine.metrics.events_classified == 0
        assert len(engine.metrics.urgency_distribution) == 0
        assert len(engine.metrics.category_distribution) == 0
    
    def test_get_metrics(self, engine):
        """Test metrics retrieval."""
        metrics = engine.get_metrics()
        
        assert isinstance(metrics, ClassificationMetrics)
        assert hasattr(metrics, 'events_classified')
        assert hasattr(metrics, 'urgency_distribution')


class TestWorkloadAnalysis:
    """Test workload impact analysis."""
    
    @pytest.mark.asyncio
    async def test_workload_analysis_for_assignment(self, engine, assignment_event):
        """Test workload analysis for assignment events."""
        analysis = await engine.analyze_workload_impact(assignment_event)
        
        assert 'assignee_id' in analysis
        assert 'assignee_name' in analysis
        assert analysis['assignee_id'] == 'newuser123'
        assert analysis['assignee_name'] == 'New Developer'
        assert 'workload_level' in analysis
        assert 'recommendation' in analysis
    
    @pytest.mark.asyncio
    async def test_workload_analysis_for_non_assignment(self, engine, sample_processed_event):
        """Test workload analysis returns empty for non-assignment events."""
        analysis = await engine.analyze_workload_impact(sample_processed_event)
        
        assert analysis == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])