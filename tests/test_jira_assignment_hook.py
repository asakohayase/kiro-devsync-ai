"""
Comprehensive tests for JIRA Assignment Hook.

Tests cover assignment change detection, workload analysis, notification generation,
and integration with existing systems.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from devsync_ai.hooks.jira_assignment_hook import (
    JiraAssignmentHook,
    AssignmentChangeType,
    WorkloadRiskLevel,
    AssignmentChangeData,
    WorkloadAnalysis,
    NotificationTarget
)
from devsync_ai.core.agent_hooks import EnrichedEvent
from devsync_ai.core.event_classification_engine import EventCategory, UrgencyLevel
from devsync_ai.core.agent_hooks import HookExecutionResult


class TestJiraAssignmentHook:
    """Test suite for JiraAssignmentHook."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        mock_jira = AsyncMock()
        mock_slack = AsyncMock()
        mock_workload = AsyncMock()
        mock_notification = AsyncMock()
        
        return {
            "jira": mock_jira,
            "slack": mock_slack,
            "workload": mock_workload,
            "notification": mock_notification
        }

    @pytest.fixture
    def assignment_hook(self, mock_services):
        """Create JiraAssignmentHook instance with mocked dependencies."""
        hook = JiraAssignmentHook()
        hook.jira_service = mock_services["jira"]
        hook.slack_service = mock_services["slack"]
        hook.workload_engine = mock_services["workload"]
        hook.notification_integration = mock_services["notification"]
        return hook

    @pytest.fixture
    def sample_assignment_event(self):
        """Create sample assignment change event."""
        return EnrichedEvent(
            event_id="test_assignment_123",
            source="jira",
            event_type="jira:assignment_change",
            category=EventCategory.ASSIGNMENT,
            urgency=UrgencyLevel.MEDIUM,
            data={
                "issue": {
                    "key": "TEST-123",
                    "fields": {
                        "summary": "Test assignment change",
                        "assignee": {
                            "displayName": "John Doe",
                            "name": "john.doe"
                        },
                        "priority": {"name": "High"},
                        "status": {"name": "In Progress"},
                        "issuetype": {"name": "Task"},
                        "reporter": {"displayName": "Jane Smith"},
                        "customfield_10016": 5,  # Story points
                        "labels": [{"name": "backend"}],
                        "components": []
                    }
                },
                "changelog": {
                    "items": [
                        {
                            "field": "assignee",
                            "fromString": "Previous User",
                            "toString": "John Doe"
                        }
                    ]
                }
            },
            timestamp=datetime.utcnow(),
            team_id="engineering",
            user_id="john.doe"
        )

    @pytest.fixture
    def sample_workload_analysis(self):
        """Create sample workload analysis."""
        return WorkloadAnalysis(
            assignee="John Doe",
            current_ticket_count=8,
            current_story_points=25,
            high_priority_count=2,
            overdue_count=1,
            sprint_capacity_utilization=0.85,
            risk_level=WorkloadRiskLevel.MODERATE,
            recommendations=[
                "Consider prioritizing high-priority items",
                "Monitor workload for potential overload"
            ],
            conflicts=["Multiple high-priority tickets competing for attention"],
            workload_trend="increasing"
        )

    def test_should_execute_assignment_change(self, assignment_hook, sample_assignment_event):
        """Test that hook correctly identifies assignment change events."""
        # Should execute for assignment events
        assert assignment_hook.should_execute(sample_assignment_event)
        
        # Should not execute for non-JIRA events
        non_jira_event = sample_assignment_event
        non_jira_event.source = "github"
        assert not assignment_hook.should_execute(non_jira_event)
        
        # Should not execute for events without assignee changes
        no_assignee_event = sample_assignment_event
        no_assignee_event.data["changelog"]["items"] = [
            {"field": "status", "fromString": "To Do", "toString": "In Progress"}
        ]
        assert not assignment_hook.should_execute(no_assignee_event)

    @pytest.mark.asyncio
    async def test_parse_assignment_change_new_assignment(self, assignment_hook, sample_assignment_event):
        """Test parsing of new assignment change."""
        assignment_data = await assignment_hook._parse_assignment_change(sample_assignment_event)
        
        assert assignment_data is not None
        assert assignment_data.ticket_key == "TEST-123"
        assert assignment_data.title == "Test assignment change"
        assert assignment_data.previous_assignee == "Previous User"
        assert assignment_data.new_assignee == "John Doe"
        assert assignment_data.priority == "High"
        assert assignment_data.status == "In Progress"
        assert assignment_data.story_points == 5
        assert assignment_data.change_type == AssignmentChangeType.REASSIGNMENT

    @pytest.mark.asyncio
    async def test_parse_assignment_change_unassignment(self, assignment_hook):
        """Test parsing of unassignment change."""
        unassignment_event = EnrichedEvent(
            event_id="test_unassignment",
            source="jira",
            event_type="jira:assignment_change",
            category=EventCategory.ASSIGNMENT,
            urgency=UrgencyLevel.MEDIUM,
            data={
                "issue": {
                    "key": "TEST-456",
                    "fields": {
                        "summary": "Test unassignment",
                        "assignee": None,
                        "priority": {"name": "Medium"},
                        "status": {"name": "To Do"},
                        "issuetype": {"name": "Bug"},
                        "reporter": {"displayName": "Test Reporter"}
                    }
                },
                "changelog": {
                    "items": [
                        {
                            "field": "assignee",
                            "fromString": "Previous User",
                            "toString": None
                        }
                    ]
                }
            },
            timestamp=datetime.utcnow(),
            team_id="engineering",
            user_id="unassigned"
        )
        
        assignment_data = await assignment_hook._parse_assignment_change(unassignment_event)
        
        assert assignment_data is not None
        assert assignment_data.change_type == AssignmentChangeType.UNASSIGNMENT
        assert assignment_data.previous_assignee == "Previous User"
        assert assignment_data.new_assignee is None

    def test_determine_change_type(self, assignment_hook):
        """Test assignment change type determination."""
        # New assignment
        assert assignment_hook._determine_change_type(None, "John Doe") == AssignmentChangeType.NEW_ASSIGNMENT
        
        # Reassignment
        assert assignment_hook._determine_change_type("Jane Smith", "John Doe") == AssignmentChangeType.REASSIGNMENT
        
        # Unassignment
        assert assignment_hook._determine_change_type("John Doe", None) == AssignmentChangeType.UNASSIGNMENT
        
        # Self assignment (no change)
        assert assignment_hook._determine_change_type("John Doe", "John Doe") == AssignmentChangeType.SELF_ASSIGNMENT

    @pytest.mark.asyncio
    async def test_analyze_workload_impact(self, assignment_hook, mock_services):
        """Test workload impact analysis."""
        assignment_data = AssignmentChangeData(
            ticket_key="TEST-123",
            title="Test ticket",
            previous_assignee="Previous User",
            new_assignee="John Doe",
            priority="High",
            status="In Progress",
            story_points=5,
            sprint="Sprint 10",
            reporter="Test Reporter",
            timestamp=datetime.utcnow(),
            change_type=AssignmentChangeType.REASSIGNMENT,
            project_key="TEST",
            issue_type="Task"
        )
        
        # Mock workload analysis
        with patch.object(assignment_hook, '_analyze_assignee_workload') as mock_analyze:
            mock_analysis = WorkloadAnalysis(
                assignee="John Doe",
                current_ticket_count=5,
                current_story_points=20,
                high_priority_count=1,
                overdue_count=0,
                sprint_capacity_utilization=0.75,
                risk_level=WorkloadRiskLevel.MODERATE,
                recommendations=[],
                conflicts=[],
                workload_trend="stable"
            )
            mock_analyze.return_value = mock_analysis
            
            analyses = await assignment_hook._analyze_workload_impact(assignment_data)
            
            assert "John Doe" in analyses
            assert analyses["John Doe"].current_ticket_count == 5
            assert analyses["John Doe"].risk_level == WorkloadRiskLevel.MODERATE

    def test_calculate_workload_risk(self, assignment_hook):
        """Test workload risk calculation."""
        # Low risk scenario
        risk = assignment_hook._calculate_workload_risk(
            ticket_count=3,
            story_points=10,
            high_priority_count=0,
            overdue_count=0,
            sprint_capacity_utilization=0.6
        )
        assert risk == WorkloadRiskLevel.LOW
        
        # High risk scenario
        risk = assignment_hook._calculate_workload_risk(
            ticket_count=15,
            story_points=45,
            high_priority_count=6,
            overdue_count=4,
            sprint_capacity_utilization=1.3
        )
        assert risk == WorkloadRiskLevel.CRITICAL
        
        # Moderate risk scenario
        risk = assignment_hook._calculate_workload_risk(
            ticket_count=8,
            story_points=25,
            high_priority_count=2,
            overdue_count=1,
            sprint_capacity_utilization=0.9
        )
        assert risk == WorkloadRiskLevel.MODERATE

    def test_generate_workload_recommendations(self, assignment_hook):
        """Test workload recommendation generation."""
        recommendations = assignment_hook._generate_workload_recommendations(
            assignee="John Doe",
            ticket_count=12,
            story_points=35,
            high_priority_count=4,
            overdue_count=2,
            sprint_capacity_utilization=1.1,
            risk_level=WorkloadRiskLevel.HIGH
        )
        
        assert len(recommendations) > 0
        assert any("HIGH RISK" in rec for rec in recommendations)
        assert any("overdue" in rec for rec in recommendations)
        assert any("high-priority" in rec for rec in recommendations)
        assert any("over-capacity" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_determine_notification_targets(self, assignment_hook, sample_workload_analysis):
        """Test notification target determination."""
        assignment_data = AssignmentChangeData(
            ticket_key="TEST-123",
            title="Test ticket",
            previous_assignee="Previous User",
            new_assignee="John Doe",
            priority="High",
            status="In Progress",
            story_points=5,
            sprint="Sprint 10",
            reporter="Test Reporter",
            timestamp=datetime.utcnow(),
            change_type=AssignmentChangeType.REASSIGNMENT,
            project_key="TEST",
            issue_type="Task"
        )
        
        workload_analyses = {"John Doe": sample_workload_analysis}
        
        with patch.object(assignment_hook, '_get_team_channel', return_value="#test-team"):
            with patch.object(assignment_hook, '_get_project_manager', return_value=None):
                targets = await assignment_hook._determine_notification_targets(
                    assignment_data, workload_analyses
                )
        
        assert len(targets) >= 2  # At least new assignee and team channel
        
        # Check new assignee target
        assignee_targets = [t for t in targets if t.user_id == "John Doe"]
        assert len(assignee_targets) == 1
        assert assignee_targets[0].channel == "direct"
        assert assignee_targets[0].mention_type == "direct"
        
        # Check team channel target
        team_targets = [t for t in targets if t.user_id == "team"]
        assert len(team_targets) == 1
        assert team_targets[0].channel == "#test-team"

    @pytest.mark.asyncio
    async def test_send_notifications(self, assignment_hook, mock_services):
        """Test notification sending."""
        assignment_data = AssignmentChangeData(
            ticket_key="TEST-123",
            title="Test ticket",
            previous_assignee="Previous User",
            new_assignee="John Doe",
            priority="High",
            status="In Progress",
            story_points=5,
            sprint="Sprint 10",
            reporter="Test Reporter",
            timestamp=datetime.utcnow(),
            change_type=AssignmentChangeType.REASSIGNMENT,
            project_key="TEST",
            issue_type="Task"
        )
        
        workload_analyses = {}
        targets = [
            NotificationTarget(
                user_id="John Doe",
                channel="direct",
                mention_type="direct",
                urgency=UrgencyLevel.MEDIUM,
                context={"type": "new_assignment"}
            )
        ]
        
        # Mock Slack service response
        mock_services["slack"].send_message.return_value = {"ok": True, "ts": "1234567890.123"}
        
        with patch.object(assignment_hook, '_generate_notification_message') as mock_generate:
            mock_generate.return_value = {
                "text": "Test notification",
                "blocks": []
            }
            
            results = await assignment_hook._send_notifications(
                assignment_data, workload_analyses, targets
            )
        
        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["target"] == "John Doe"
        
        # Verify Slack service was called
        mock_services["slack"].send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_new_assignment_message(self, assignment_hook, sample_workload_analysis):
        """Test new assignment message generation."""
        assignment_data = AssignmentChangeData(
            ticket_key="TEST-123",
            title="Implement new feature",
            previous_assignee=None,
            new_assignee="John Doe",
            priority="High",
            status="To Do",
            story_points=8,
            sprint="Sprint 10",
            reporter="Product Owner",
            timestamp=datetime.utcnow(),
            change_type=AssignmentChangeType.NEW_ASSIGNMENT,
            project_key="TEST",
            issue_type="Story"
        )
        
        workload_analyses = {"John Doe": sample_workload_analysis}
        target = NotificationTarget(
            user_id="John Doe",
            channel="direct",
            mention_type="direct",
            urgency=UrgencyLevel.MEDIUM,
            context={"type": "new_assignment", "workload_analysis": sample_workload_analysis}
        )
        
        message = await assignment_hook._generate_new_assignment_message(
            assignment_data, workload_analyses, target
        )
        
        assert "text" in message
        assert "blocks" in message
        assert "TEST-123" in message["text"]
        assert "John Doe" in message["text"]
        assert "🎯" in message["text"]  # New assignment emoji
        
        # Check blocks structure
        blocks = message["blocks"]
        assert len(blocks) >= 3  # Header, details, actions
        
        # Check for workload information
        workload_blocks = [b for b in blocks if "Current Workload" in str(b)]
        assert len(workload_blocks) > 0

    @pytest.mark.asyncio
    async def test_generate_workload_concern_message(self, assignment_hook):
        """Test workload concern message generation."""
        assignment_data = AssignmentChangeData(
            ticket_key="TEST-123",
            title="Critical bug fix",
            previous_assignee=None,
            new_assignee="John Doe",
            priority="Critical",
            status="To Do",
            story_points=3,
            sprint="Sprint 10",
            reporter="QA Team",
            timestamp=datetime.utcnow(),
            change_type=AssignmentChangeType.NEW_ASSIGNMENT,
            project_key="TEST",
            issue_type="Bug"
        )
        
        critical_workload = WorkloadAnalysis(
            assignee="John Doe",
            current_ticket_count=15,
            current_story_points=45,
            high_priority_count=6,
            overdue_count=3,
            sprint_capacity_utilization=1.2,
            risk_level=WorkloadRiskLevel.CRITICAL,
            recommendations=[
                "🚨 CRITICAL: Immediate workload redistribution needed",
                "Consider reassigning lower-priority tickets"
            ],
            conflicts=["Sprint over-capacity", "Multiple critical items"],
            workload_trend="increasing"
        )
        
        workload_analyses = {"John Doe": critical_workload}
        target = NotificationTarget(
            user_id="project.manager",
            channel="direct",
            mention_type="direct",
            urgency=UrgencyLevel.HIGH,
            context={"type": "workload_concern", "workload_analysis": critical_workload}
        )
        
        message = await assignment_hook._generate_workload_concern_message(
            assignment_data, workload_analyses, target
        )
        
        assert "🚨 Workload Alert" in message["text"]
        assert "overloaded" in message["text"]
        
        # Check for critical indicators
        blocks = message["blocks"]
        workload_text = str(blocks)
        assert "CRITICAL" in workload_text
        assert "15 tickets" in workload_text
        assert "45 story points" in workload_text

    @pytest.mark.asyncio
    async def test_execute_hook_success(self, assignment_hook, sample_assignment_event, mock_services):
        """Test successful hook execution."""
        # Mock all the internal methods
        with patch.object(assignment_hook, '_parse_assignment_change') as mock_parse:
            with patch.object(assignment_hook, '_analyze_workload_impact') as mock_analyze:
                with patch.object(assignment_hook, '_determine_notification_targets') as mock_targets:
                    with patch.object(assignment_hook, '_send_notifications') as mock_send:
                        with patch.object(assignment_hook, '_store_assignment_analytics') as mock_store:
                            
                            # Setup mock returns
                            mock_parse.return_value = AssignmentChangeData(
                                ticket_key="TEST-123",
                                title="Test ticket",
                                previous_assignee=None,
                                new_assignee="John Doe",
                                priority="High",
                                status="To Do",
                                story_points=5,
                                sprint="Sprint 10",
                                reporter="Test Reporter",
                                timestamp=datetime.utcnow(),
                                change_type=AssignmentChangeType.NEW_ASSIGNMENT,
                                project_key="TEST",
                                issue_type="Task"
                            )
                            
                            mock_analyze.return_value = {"John Doe": WorkloadAnalysis(
                                assignee="John Doe",
                                current_ticket_count=5,
                                current_story_points=20,
                                high_priority_count=1,
                                overdue_count=0,
                                sprint_capacity_utilization=0.75,
                                risk_level=WorkloadRiskLevel.LOW,
                                recommendations=[],
                                conflicts=[],
                                workload_trend="stable"
                            )}
                            
                            mock_targets.return_value = [
                                NotificationTarget(
                                    user_id="John Doe",
                                    channel="direct",
                                    mention_type="direct",
                                    urgency=UrgencyLevel.MEDIUM,
                                    context={"type": "new_assignment"}
                                )
                            ]
                            
                            mock_send.return_value = [{"success": True, "target": "John Doe"}]
                            
                            # Execute the hook
                            result = await assignment_hook.execute(sample_assignment_event)
                            
                            # Verify result
                            assert result.success is True
                            assert "Assignment change processed" in result.message
                            assert result.metadata["ticket_key"] == "TEST-123"
                            assert result.metadata["notifications_sent"] == 1

    @pytest.mark.asyncio
    async def test_execute_hook_parse_failure(self, assignment_hook, sample_assignment_event):
        """Test hook execution with parse failure."""
        with patch.object(assignment_hook, '_parse_assignment_change', return_value=None):
            result = await assignment_hook.execute(sample_assignment_event)
            
            assert result.success is False
            assert "Failed to parse assignment change data" in result.message

    @pytest.mark.asyncio
    async def test_execute_hook_exception_handling(self, assignment_hook, sample_assignment_event):
        """Test hook execution with exception handling."""
        with patch.object(assignment_hook, '_parse_assignment_change', side_effect=Exception("Test error")):
            result = await assignment_hook.execute(sample_assignment_event)
            
            assert result.success is False
            assert "Assignment hook execution failed" in result.message

    @pytest.mark.asyncio
    async def test_identify_workload_conflicts(self, assignment_hook):
        """Test workload conflict identification."""
        assignment_data = AssignmentChangeData(
            ticket_key="TEST-123",
            title="High priority task",
            previous_assignee=None,
            new_assignee="John Doe",
            priority="High",
            status="To Do",
            story_points=8,
            sprint="Sprint 10",
            reporter="Test Reporter",
            timestamp=datetime.utcnow(),
            change_type=AssignmentChangeType.NEW_ASSIGNMENT,
            project_key="TEST",
            issue_type="Task",
            due_date=datetime.utcnow() + timedelta(days=2)
        )
        
        # Mock current tickets with conflicts
        current_tickets = [
            Mock(priority="High", story_points=5, sprint="Sprint 10", 
                 due_date=datetime.utcnow() + timedelta(days=1)),
            Mock(priority="Critical", story_points=8, sprint="Sprint 10", 
                 due_date=datetime.utcnow() + timedelta(days=3)),
            Mock(priority="Medium", story_points=3, sprint="Sprint 9")
        ]
        
        conflicts = await assignment_hook._identify_workload_conflicts(
            "John Doe", assignment_data, current_tickets
        )
        
        assert len(conflicts) > 0
        assert any("high-priority" in conflict.lower() for conflict in conflicts)
        assert any("capacity" in conflict.lower() for conflict in conflicts)

    def test_edge_case_empty_changelog(self, assignment_hook):
        """Test handling of empty changelog."""
        event_with_empty_changelog = EnrichedEvent(
            event_id="test_empty",
            source="jira",
            event_type="jira:issue_updated",
            category=EventCategory.STATUS_CHANGE,
            urgency=UrgencyLevel.LOW,
            data={
                "issue": {"key": "TEST-123"},
                "changelog": {"items": []}
            },
            timestamp=datetime.utcnow(),
            team_id="test",
            user_id="test"
        )
        
        # Should not execute for empty changelog
        assert not assignment_hook.should_execute(event_with_empty_changelog)

    def test_edge_case_malformed_data(self, assignment_hook):
        """Test handling of malformed webhook data."""
        malformed_event = EnrichedEvent(
            event_id="test_malformed",
            source="jira",
            event_type="jira:assignment_change",
            category=EventCategory.ASSIGNMENT,
            urgency=UrgencyLevel.LOW,
            data={
                "issue": None,  # Malformed data
                "changelog": None
            },
            timestamp=datetime.utcnow(),
            team_id="test",
            user_id="test"
        )
        
        # Should handle gracefully
        assert assignment_hook.should_execute(malformed_event)  # Based on event type


class TestJiraAssignmentHookIntegration:
    """Integration tests for JIRA Assignment Hook."""

    @pytest.mark.asyncio
    async def test_end_to_end_assignment_processing(self):
        """Test complete end-to-end assignment processing."""
        # This would be an integration test with actual services
        # Skipped in unit tests but important for full system validation
        pytest.skip("Integration test - requires actual service connections")

    @pytest.mark.asyncio
    async def test_performance_with_large_workload(self):
        """Test performance with large workload datasets."""
        # Test hook performance with large numbers of tickets
        pytest.skip("Performance test - requires load testing setup")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])