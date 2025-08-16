"""
Tests for Assignment Hook Workload Analysis Integration.

This module tests the integration between the AssignmentChangeHook and the
WorkloadAnalyticsEngine for comprehensive workload tracking and analysis.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from devsync_ai.hooks.jira_agent_hooks import AssignmentChangeHook
from devsync_ai.core.agent_hooks import (
    EnrichedEvent, EventCategory, UrgencyLevel, SignificanceLevel, EventClassification
)
from devsync_ai.analytics.workload_analytics_engine import (
    AssignmentImpactAnalysis, WorkloadStatus, TeamMemberCapacity
)


class TestAssignmentHookWorkloadAnalysis:
    """Test suite for Assignment Hook workload analysis integration."""
    
    @pytest.fixture
    def assignment_hook(self):
        """Create an assignment hook for testing."""
        hook = AssignmentChangeHook()
        hook.hook_id = "assignment_test"
        hook.hook_type = "assignment_change"
        return hook
    
    @pytest.fixture
    def sample_assignment_event(self):
        """Create a sample assignment event."""
        classification = EventClassification(
            category=EventCategory.ASSIGNMENT,
            urgency=UrgencyLevel.MEDIUM,
            significance=SignificanceLevel.MEDIUM,
            affected_teams=["engineering"],
            routing_hints={}
        )
        
        event = EnrichedEvent(
            event_id="evt_123",
            event_type="jira:issue_assigned",
            timestamp=datetime.now(timezone.utc),
            jira_event_data={},
            ticket_key="PROJ-123",
            project_key="PROJ",
            raw_payload={},
            ticket_details={
                "summary": "Implement user authentication API",
                "priority": "High",
                "issuetype": {"name": "Story"},
                "assignee": {
                    "accountId": "user123",
                    "displayName": "John Doe"
                },
                "customFields": {
                    "story_points": 5
                },
                "components": [{"name": "backend"}],
                "labels": ["api", "security"]
            },
            stakeholders=[],
            classification=classification,
            context_data={
                "processor_data": {
                    "assignment_info": {
                        "assignment_type": "assigned",
                        "new_assignee_id": "user123",
                        "new_assignee_name": "John Doe"
                    }
                }
            }
        )
        
        return event
    
    @pytest.fixture
    def sample_impact_analysis(self):
        """Create a sample assignment impact analysis."""
        current_capacity = TeamMemberCapacity(
            user_id="user123",
            display_name="John Doe",
            email="john.doe@company.com",
            team_id="engineering",
            active_tickets=4,
            total_story_points=20,
            estimated_hours=80.0,
            max_concurrent_tickets=5,
            weekly_capacity_hours=40.0,
            capacity_utilization=0.8,
            recent_velocity=8.0,
            average_completion_time=4.0,
            quality_score=0.85,
            workload_status=WorkloadStatus.HIGH,
            alerts=[],
            estimated_completion_date=datetime.now(timezone.utc) + timedelta(days=10),
            projected_capacity_date=datetime.now(timezone.utc) + timedelta(days=5),
            skill_areas=["backend", "api"],
            preferred_ticket_types=["story", "task"],
            last_updated=datetime.now(timezone.utc)
        )
        
        return AssignmentImpactAnalysis(
            assignee_id="user123",
            ticket_key="PROJ-123",
            story_points=5,
            estimated_hours=20.0,
            current_workload=current_capacity,
            projected_utilization=0.9,
            projected_completion_date=datetime.now(timezone.utc) + timedelta(days=12),
            projected_workload_status=WorkloadStatus.HIGH,
            impact_severity="medium",
            capacity_warnings=["Approaching capacity limit"],
            skill_match_score=0.8,
            assignment_recommendation="approve",
            alternative_assignees=[("user456", 0.7), ("user789", 0.6)],
            team_impact={"impact": "low", "reasons": []},
            created_at=datetime.now(timezone.utc)
        )
    
    @pytest.mark.asyncio
    async def test_assignment_hook_with_workload_analysis(
        self, 
        assignment_hook, 
        sample_assignment_event, 
        sample_impact_analysis
    ):
        """Test assignment hook execution with comprehensive workload analysis."""
        
        with patch('devsync_ai.analytics.workload_analytics_engine.default_workload_analytics_engine') as mock_engine:
            mock_engine.analyze_assignment_impact.return_value = sample_impact_analysis
            mock_engine.update_member_workload.return_value = True
            
            with patch.object(assignment_hook, '_send_assignment_notifications_via_integration') as mock_notify:
                mock_result = MagicMock()
                mock_result.decision.value = "send_immediately"
                mock_notify.return_value = mock_result
                
                with patch.object(assignment_hook, '_generate_capacity_alerts') as mock_alerts:
                    with patch.object(assignment_hook, '_update_capacity_dashboard_enhanced') as mock_dashboard:
                        
                        result = await assignment_hook.execute(sample_assignment_event)
                        
                        # Verify workload analysis was called
                        mock_engine.analyze_assignment_impact.assert_called_once_with(
                            assignee_id="user123",
                            team_id="engineering",
                            ticket_key="PROJ-123",
                            story_points=5,
                            estimated_hours=20.0,
                            ticket_metadata={
                                'story_points': 5,
                                'priority': 'High',
                                'ticket_type': 'Story',
                                'components': ['backend'],
                                'labels': ['api', 'security'],
                                'estimated_hours': 20.0,
                                'required_skills': ['backend']
                            }
                        )
                        
                        # Verify workload update was called
                        mock_engine.update_member_workload.assert_called_once_with(
                            user_id="user123",
                            team_id="engineering",
                            ticket_key="PROJ-123",
                            action="assigned",
                            story_points=5,
                            estimated_hours=20.0
                        )
                        
                        # Verify notification was sent
                        mock_notify.assert_called_once()
                        
                        # Verify result metadata includes workload information
                        assert result.metadata["overload_warning"] is False
                        assert result.metadata["skill_match_score"] == 0.8
                        assert result.metadata["impact_severity"] == "medium"
                        assert result.metadata["assignment_recommendation"] == "approve"
                        assert result.metadata["capacity_utilization"] == 0.9
                        assert result.metadata["alternative_assignees_count"] == 2
    
    @pytest.mark.asyncio
    async def test_assignment_hook_with_overload_warning(
        self, 
        assignment_hook, 
        sample_assignment_event, 
        sample_impact_analysis
    ):
        """Test assignment hook with overload warning scenario."""
        
        # Modify impact analysis to show overload
        sample_impact_analysis.projected_workload_status = WorkloadStatus.OVERLOADED
        sample_impact_analysis.impact_severity = "high"
        sample_impact_analysis.assignment_recommendation = "caution"
        sample_impact_analysis.capacity_warnings = [
            "Assignment will overload member beyond capacity",
            "Member already at maximum concurrent ticket limit"
        ]
        
        with patch('devsync_ai.analytics.workload_analytics_engine.default_workload_analytics_engine') as mock_engine:
            mock_engine.analyze_assignment_impact.return_value = sample_impact_analysis
            mock_engine.update_member_workload.return_value = True
            
            with patch.object(assignment_hook, '_send_assignment_notifications_via_integration') as mock_notify:
                mock_result = MagicMock()
                mock_result.decision.value = "send_immediately"
                mock_notify.return_value = mock_result
                
                with patch.object(assignment_hook, '_generate_capacity_alerts') as mock_alerts:
                    with patch.object(assignment_hook, '_update_capacity_dashboard_enhanced') as mock_dashboard:
                        
                        result = await assignment_hook.execute(sample_assignment_event)
                        
                        # Verify capacity alerts were generated for high impact
                        mock_alerts.assert_called_once_with(sample_impact_analysis, sample_assignment_event)
                        
                        # Verify result shows overload warning
                        assert result.metadata["overload_warning"] is True
                        assert result.metadata["impact_severity"] == "high"
                        assert result.metadata["assignment_recommendation"] == "caution"
    
    @pytest.mark.asyncio
    async def test_assignment_hook_critical_assignment(
        self, 
        assignment_hook, 
        sample_assignment_event, 
        sample_impact_analysis
    ):
        """Test assignment hook with critical assignment scenario."""
        
        # Modify impact analysis to show critical status
        sample_impact_analysis.projected_workload_status = WorkloadStatus.CRITICAL
        sample_impact_analysis.impact_severity = "critical"
        sample_impact_analysis.assignment_recommendation = "reject"
        sample_impact_analysis.capacity_warnings = [
            "Assignment will put member in critical overload state"
        ]
        sample_impact_analysis.alternative_assignees = [
            ("user456", 0.9), ("user789", 0.8), ("user101", 0.7)
        ]
        
        with patch('devsync_ai.analytics.workload_analytics_engine.default_workload_analytics_engine') as mock_engine:
            mock_engine.analyze_assignment_impact.return_value = sample_impact_analysis
            mock_engine.update_member_workload.return_value = True
            
            with patch.object(assignment_hook, '_send_assignment_notifications_via_integration') as mock_notify:
                mock_result = MagicMock()
                mock_result.decision.value = "send_immediately"
                mock_notify.return_value = mock_result
                
                with patch.object(assignment_hook, '_generate_capacity_alerts') as mock_alerts:
                    with patch.object(assignment_hook, '_update_capacity_dashboard_enhanced') as mock_dashboard:
                        
                        result = await assignment_hook.execute(sample_assignment_event)
                        
                        # Verify critical assignment handling
                        assert result.metadata["impact_severity"] == "critical"
                        assert result.metadata["assignment_recommendation"] == "reject"
                        assert result.metadata["alternative_assignees_count"] == 3
                        
                        # Verify capacity alerts were generated
                        mock_alerts.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_ticket_metadata(self, assignment_hook, sample_assignment_event):
        """Test ticket metadata extraction for workload analysis."""
        
        metadata = await assignment_hook._extract_ticket_metadata(sample_assignment_event)
        
        assert metadata["story_points"] == 5
        assert metadata["priority"] == "High"
        assert metadata["ticket_type"] == "Story"
        assert metadata["components"] == ["backend"]
        assert metadata["labels"] == ["api", "security"]
        assert metadata["estimated_hours"] == 25.0  # 5 points * 5.0 hours (high priority)
        assert "backend" in metadata["required_skills"]
    
    @pytest.mark.asyncio
    async def test_create_enhanced_assignment_message(
        self, 
        assignment_hook, 
        sample_assignment_event, 
        sample_impact_analysis
    ):
        """Test creation of enhanced assignment message with workload information."""
        
        assignment_analysis = {
            "type": "assigned",
            "new_assignee": "John Doe",
            "assignee_id": "user123"
        }
        
        skill_analysis = {
            "primary_skill": "backend",
            "score": 0.8,
            "quality": "good"
        }
        
        message_data = await assignment_hook._create_enhanced_assignment_message(
            sample_assignment_event, assignment_analysis, sample_impact_analysis, skill_analysis
        )
        
        # Verify message structure
        assert "blocks" in message_data
        assert len(message_data["blocks"]) >= 4  # Header, details, workload, recommendation, actions
        
        # Verify workload information is included
        workload_block = None
        for block in message_data["blocks"]:
            if "Workload Impact Analysis" in block.get("text", {}).get("text", ""):
                workload_block = block
                break
        
        assert workload_block is not None
        workload_text = workload_block["text"]["text"]
        assert "Current Load: 4 tickets" in workload_text
        assert "Projected Utilization: 90%" in workload_text
        assert "Status: High" in workload_text
        
        # Verify recommendation block
        recommendation_block = None
        for block in message_data["blocks"]:
            if "Assignment Recommendation" in block.get("text", {}).get("text", ""):
                recommendation_block = block
                break
        
        assert recommendation_block is not None
        recommendation_text = recommendation_block["text"]["text"]
        assert "Recommendation: Approve" in recommendation_text
        assert "Impact Severity: Medium" in recommendation_text
        assert "Skill Match: 80%" in recommendation_text
    
    @pytest.mark.asyncio
    async def test_determine_assignment_channels_enhanced(
        self, 
        assignment_hook, 
        sample_assignment_event, 
        sample_impact_analysis
    ):
        """Test enhanced channel determination based on workload impact."""
        
        # Test normal assignment
        channels = await assignment_hook._determine_assignment_channels_enhanced(
            sample_assignment_event, sample_impact_analysis
        )
        
        expected_channels = ["#team-assignments", "#engineering-assignments"]
        for channel in expected_channels:
            assert channel in channels
        
        # Test critical assignment
        sample_impact_analysis.impact_severity = "critical"
        sample_impact_analysis.projected_workload_status = WorkloadStatus.CRITICAL
        
        channels = await assignment_hook._determine_assignment_channels_enhanced(
            sample_assignment_event, sample_impact_analysis
        )
        
        assert "#management" in channels
        assert "#capacity-alerts" in channels
        
        # Test high impact assignment
        sample_impact_analysis.impact_severity = "high"
        sample_impact_analysis.projected_workload_status = WorkloadStatus.OVERLOADED
        
        channels = await assignment_hook._determine_assignment_channels_enhanced(
            sample_assignment_event, sample_impact_analysis
        )
        
        assert "#team-leads" in channels
        assert "#capacity-alerts" in channels
    
    @pytest.mark.asyncio
    async def test_generate_capacity_alerts(
        self, 
        assignment_hook, 
        sample_assignment_event, 
        sample_impact_analysis
    ):
        """Test capacity alert generation for high-impact assignments."""
        
        # Test high impact assignment
        sample_impact_analysis.impact_severity = "high"
        
        with patch('devsync_ai.hooks.jira_agent_hooks.logger') as mock_logger:
            await assignment_hook._generate_capacity_alerts(
                sample_impact_analysis, sample_assignment_event
            )
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Capacity alert generated for user123" in warning_call
        
        # Test critical impact assignment
        sample_impact_analysis.impact_severity = "critical"
        
        with patch('devsync_ai.hooks.jira_agent_hooks.logger') as mock_logger:
            await assignment_hook._generate_capacity_alerts(
                sample_impact_analysis, sample_assignment_event
            )
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
    
    def test_get_workload_indicator(self, assignment_hook, sample_impact_analysis):
        """Test workload status indicator generation."""
        
        # Test normal status
        indicator = assignment_hook._get_workload_indicator(sample_impact_analysis)
        assert indicator == "🟡"  # HIGH status
        
        # Test overloaded status
        sample_impact_analysis.projected_workload_status = WorkloadStatus.OVERLOADED
        indicator = assignment_hook._get_workload_indicator(sample_impact_analysis)
        assert indicator == "⚠️"
        
        # Test critical status
        sample_impact_analysis.projected_workload_status = WorkloadStatus.CRITICAL
        indicator = assignment_hook._get_workload_indicator(sample_impact_analysis)
        assert indicator == "🚨"
        
        # Test optimal status
        sample_impact_analysis.projected_workload_status = WorkloadStatus.OPTIMAL
        indicator = assignment_hook._get_workload_indicator(sample_impact_analysis)
        assert indicator == "👤"
        
        # Test no analysis
        indicator = assignment_hook._get_workload_indicator(None)
        assert indicator == "👤"
    
    @pytest.mark.asyncio
    async def test_assignment_hook_error_handling(
        self, 
        assignment_hook, 
        sample_assignment_event
    ):
        """Test error handling in assignment hook with workload analysis."""
        
        with patch('devsync_ai.analytics.workload_analytics_engine.default_workload_analytics_engine') as mock_engine:
            # Simulate workload analysis failure
            mock_engine.analyze_assignment_impact.side_effect = Exception("Database connection failed")
            
            result = await assignment_hook.execute(sample_assignment_event)
            
            # Verify hook handles error gracefully
            assert result.status.value == "failed"
            assert len(result.errors) > 0
            assert "Database connection failed" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_assignment_hook_without_assignee(self, assignment_hook, sample_assignment_event):
        """Test assignment hook behavior when no assignee is present."""
        
        # Remove assignee information
        sample_assignment_event.context_data["processor_data"]["assignment_info"]["assignment_type"] = "unassigned"
        sample_assignment_event.context_data["processor_data"]["assignment_info"]["new_assignee_id"] = None
        sample_assignment_event.context_data["processor_data"]["assignment_info"]["new_assignee_name"] = None
        
        with patch.object(assignment_hook, '_send_assignment_notifications_via_integration') as mock_notify:
            mock_result = MagicMock()
            mock_result.decision.value = "send_immediately"
            mock_notify.return_value = mock_result
            
            result = await assignment_hook.execute(sample_assignment_event)
            
            # Verify hook executes without workload analysis
            assert result.status.value == "success"
            assert result.metadata["impact_severity"] == "low"  # Default when no analysis
            assert result.metadata["assignment_recommendation"] == "approve"  # Default


if __name__ == "__main__":
    pytest.main([__file__])