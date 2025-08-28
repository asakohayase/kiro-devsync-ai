"""
Comprehensive tests for Team Productivity Intelligence System.

This module provides extensive test coverage for the TeamProductivityAnalyzer
including mock data generators, edge cases, and integration scenarios.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any, Tuple
import statistics

from devsync_ai.analytics.team_productivity_analyzer import (
    TeamProductivityAnalyzer,
    ReviewMetrics,
    CollaborationMetrics,
    DeploymentMetrics,
    BugAnalysisMetrics,
    MeetingEfficiencyMetrics,
    CapacityUtilizationMetrics,
    ProductivityTrends,
    ProductivityTrend,
    BurnoutRisk,
    CollaborationLevel
)
from devsync_ai.services.github import GitHubService
from devsync_ai.services.jira import JiraService


class MockDataGenerator:
    """Mock data generator for testing team productivity analytics."""

    @staticmethod
    def generate_pull_requests(count: int = 10) -> List[Dict[str, Any]]:
        """Generate mock pull request data."""
        prs = []
        base_date = datetime.now(timezone.utc) - timedelta(days=7)
        
        for i in range(count):
            pr = {
                "id": f"pr-{i}",
                "title": f"Feature {i}",
                "author": f"developer-{i % 3}",
                "created_at": base_date + timedelta(hours=i * 2),
                "merged_at": base_date + timedelta(hours=i * 2 + 4) if i % 4 != 0 else None,
                "reviews": [
                    {
                        "reviewer": f"reviewer-{j}",
                        "submitted_at": base_date + timedelta(hours=i * 2 + j),
                        "state": "approved" if j % 2 == 0 else "changes_requested",
                        "comments": j * 2 + 1
                    }
                    for j in range(1, 4)
                ],
                "files_changed": (i % 10) + 1,
                "additions": (i % 50) * 10,
                "deletions": (i % 30) * 5,
                "complexity_score": 50 + (i % 40)
            }
            prs.append(pr)
        
        return prs

    @staticmethod
    def generate_deployment_data(count: int = 5) -> List[Dict[str, Any]]:
        """Generate mock deployment data."""
        deployments = []
        base_date = datetime.now(timezone.utc) - timedelta(days=7)
        
        for i in range(count):
            deployment = {
                "id": f"deploy-{i}",
                "timestamp": base_date + timedelta(days=i),
                "success": i % 4 != 0,  # 75% success rate
                "rollback": i % 4 == 0,  # 25% rollback rate
                "lead_time_hours": 2.0 + (i % 5) * 0.5,
                "recovery_time_hours": 0.5 if i % 4 == 0 else 0,
                "change_count": 10 + (i % 20),
                "team_id": "test-team",
                "environment": "production"
            }
            deployments.append(deployment)
        
        return deployments

    @staticmethod
    def generate_bug_data(count: int = 15) -> List[Dict[str, Any]]:
        """Generate mock bug data."""
        bugs = []
        base_date = datetime.now(timezone.utc) - timedelta(days=14)
        severities = ["low", "medium", "high", "critical"]
        
        for i in range(count):
            created_date = base_date + timedelta(hours=i * 8)
            resolved_date = created_date + timedelta(hours=24 + (i % 72)) if i % 3 != 0 else None
            
            bug = {
                "id": f"bug-{i}",
                "key": f"BUG-{i}",
                "created_date": created_date,
                "resolved_date": resolved_date,
                "severity": severities[i % len(severities)],
                "component": f"component-{i % 5}",
                "assignee": f"developer-{i % 3}",
                "reporter": f"tester-{i % 2}",
                "resolution_time_hours": (resolved_date - created_date).total_seconds() / 3600 if resolved_date else None
            }
            bugs.append(bug)
        
        return bugs

    @staticmethod
    def generate_meeting_data(count: int = 8) -> List[Dict[str, Any]]:
        """Generate mock meeting data."""
        meetings = []
        base_date = datetime.now(timezone.utc) - timedelta(days=7)
        meeting_types = ["standup", "planning", "retrospective", "review", "technical"]
        
        for i in range(count):
            meeting = {
                "id": f"meeting-{i}",
                "title": f"{meeting_types[i % len(meeting_types)].title()} Meeting {i}",
                "start_time": base_date + timedelta(days=i % 5, hours=9 + (i % 8)),
                "duration_hours": 0.5 + (i % 4) * 0.5,
                "attendees": [f"member-{j}" for j in range(3 + (i % 5))],
                "has_outcomes": i % 3 != 0,  # 67% have outcomes
                "decisions_made": (i % 3) if i % 3 != 0 else 0,
                "action_items": [
                    {"action": f"action-{i}-{j}", "assignee": f"member-{j}", "completed": j % 2 == 0}
                    for j in range(i % 4)
                ],
                "meeting_type": meeting_types[i % len(meeting_types)]
            }
            meetings.append(meeting)
        
        return meetings

    @staticmethod
    def generate_team_capacity_data() -> Dict[str, Any]:
        """Generate mock team capacity data."""
        return {
            "team_id": "test-team",
            "total_capacity_hours": 200,  # 5 members * 40 hours
            "available_capacity_hours": 180,  # accounting for meetings, etc.
            "members": {
                "member-1": {"capacity": 40, "utilization": 38},
                "member-2": {"capacity": 40, "utilization": 35},
                "member-3": {"capacity": 40, "utilization": 42},
                "member-4": {"capacity": 40, "utilization": 36},
                "member-5": {"capacity": 40, "utilization": 39}
            },
            "overtime_hours": {
                "member-1": 2,
                "member-2": 0,
                "member-3": 8,
                "member-4": 1,
                "member-5": 4
            }
        }

    @staticmethod
    def generate_historical_productivity_data() -> Dict[str, Any]:
        """Generate mock historical productivity data."""
        return {
            "velocity": [8, 10, 12, 11, 13, 12, 14],  # story points per sprint
            "quality": [82, 85, 87, 86, 88, 87, 89],  # quality score
            "collaboration": [70, 72, 75, 73, 76, 78, 80],  # collaboration score
            "satisfaction": [75, 77, 78, 76, 79, 81, 82],  # team satisfaction
            "bug_rate": [5, 4, 3, 4, 2, 3, 2],  # bugs per sprint
            "cycle_time": [3.5, 3.2, 2.8, 3.0, 2.5, 2.7, 2.3],  # days
            "deployment_frequency": [2, 3, 3, 4, 4, 5, 5]  # per week
        }


@pytest.fixture
def mock_github_service():
    """Create a mock GitHub service."""
    service = AsyncMock(spec=GitHubService)
    service.get_pull_requests_in_range = AsyncMock(return_value=MockDataGenerator.generate_pull_requests())
    return service


@pytest.fixture
def mock_jira_service():
    """Create a mock JIRA service."""
    service = AsyncMock(spec=JiraService)
    return service


@pytest.fixture
def mock_analytics_manager():
    """Create a mock analytics data manager."""
    manager = AsyncMock()
    manager.store_analytics_record = AsyncMock()
    return manager


@pytest.fixture
def team_productivity_analyzer(mock_github_service, mock_jira_service):
    """Create a TeamProductivityAnalyzer instance with mocked dependencies."""
    analyzer = TeamProductivityAnalyzer(mock_github_service, mock_jira_service)
    return analyzer


@pytest.fixture
def date_range():
    """Create a standard date range for testing."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=7)
    return (start_date, end_date)


class TestTeamProductivityAnalyzer:
    """Test suite for TeamProductivityAnalyzer."""

    @pytest.mark.asyncio
    async def test_analyze_code_review_participation_success(self, team_productivity_analyzer, date_range):
        """Test successful code review participation analysis."""
        team_id = "test-team"
        
        # Mock the private methods
        with patch.object(team_productivity_analyzer, '_get_team_repositories', return_value=["repo1", "repo2"]):
            with patch.object(team_productivity_analyzer, '_get_team_members', return_value=["member-1", "member-2"]):
                with patch.object(team_productivity_analyzer, '_calculate_review_metrics') as mock_calc:
                    mock_calc.return_value = ReviewMetrics(
                        reviewer_id="member-1",
                        reviews_completed=10,
                        reviews_requested=12,
                        average_review_time_hours=4.5,
                        review_quality_score=85.0,
                        mentoring_impact_score=75.0,
                        review_velocity=2.5,
                        approval_rate=90.0,
                        feedback_depth_score=80.0,
                        knowledge_sharing_score=70.0
                    )
                    with patch.object(team_productivity_analyzer, '_store_review_analytics'):
                        result = await team_productivity_analyzer.analyze_code_review_participation(team_id, date_range)
        
        assert isinstance(result, dict)
        assert len(result) == 2  # Two team members
        assert "member-1" in result
        assert "member-2" in result
        assert isinstance(result["member-1"], ReviewMetrics)
        assert result["member-1"].review_quality_score == 85.0

    @pytest.mark.asyncio
    async def test_calculate_collaboration_score_success(self, team_productivity_analyzer, date_range):
        """Test successful collaboration score calculation."""
        team_id = "test-team"
        
        # Mock all the private methods
        with patch.object(team_productivity_analyzer, '_analyze_cross_team_interactions', return_value=[{"type": "review"}]):
            with patch.object(team_productivity_analyzer, '_track_team_dependencies', return_value=[{"dep": "api"}]):
                with patch.object(team_productivity_analyzer, '_analyze_knowledge_sharing', return_value=[{"session": "tech_talk"}]):
                    with patch.object(team_productivity_analyzer, '_calculate_collaboration_effectiveness', return_value=75.0):
                        with patch.object(team_productivity_analyzer, '_identify_collaboration_bottlenecks', return_value=["delays"]):
                            with patch.object(team_productivity_analyzer, '_identify_knowledge_silos', return_value=["db_knowledge"]):
                                with patch.object(team_productivity_analyzer, '_calculate_network_centrality', return_value=0.65):
                                    with patch.object(team_productivity_analyzer, '_store_collaboration_analytics'):
                                        result = await team_productivity_analyzer.calculate_collaboration_score(team_id, date_range)
        
        assert isinstance(result, CollaborationMetrics)
        assert result.team_id == team_id
        assert result.collaboration_effectiveness == 75.0
        assert result.cross_team_interactions == 1
        assert result.dependency_count == 1
        assert "delays" in result.bottleneck_indicators
        assert "db_knowledge" in result.knowledge_silos

    @pytest.mark.asyncio
    async def test_analyze_deployment_frequency_success(self, team_productivity_analyzer, date_range):
        """Test successful deployment frequency analysis."""
        team_id = "test-team"
        mock_deployments = MockDataGenerator.generate_deployment_data()
        
        with patch.object(team_productivity_analyzer, '_get_deployment_data', return_value=mock_deployments):
            with patch.object(team_productivity_analyzer, '_calculate_quality_correlation', return_value=0.78):
                with patch.object(team_productivity_analyzer, '_store_deployment_analytics'):
                    result = await team_productivity_analyzer.analyze_deployment_frequency(team_id, date_range)
        
        assert isinstance(result, DeploymentMetrics)
        assert result.team_id == team_id
        assert result.deployment_frequency > 0
        assert 0 <= result.success_rate <= 1
        assert 0 <= result.rollback_rate <= 1
        assert result.quality_correlation == 0.78

    @pytest.mark.asyncio
    async def test_analyze_bug_patterns_success(self, team_productivity_analyzer, date_range):
        """Test successful bug pattern analysis."""
        team_id = "test-team"
        mock_bugs = MockDataGenerator.generate_bug_data()
        
        with patch.object(team_productivity_analyzer, '_get_bug_data', return_value=mock_bugs):
            with patch.object(team_productivity_analyzer, '_identify_recurring_bug_patterns', return_value=["null_pointer"]):
                with patch.object(team_productivity_analyzer, '_calculate_prevention_effectiveness', return_value=72.0):
                    with patch.object(team_productivity_analyzer, '_predict_bug_trends', return_value=ProductivityTrend.STABLE):
                        with patch.object(team_productivity_analyzer, '_store_bug_analytics'):
                            result = await team_productivity_analyzer.analyze_bug_patterns(team_id, date_range)
        
        assert isinstance(result, BugAnalysisMetrics)
        assert result.team_id == team_id
        assert result.bugs_discovered >= 0
        assert result.bugs_resolved >= 0
        assert result.prevention_effectiveness == 72.0
        assert result.trend_prediction == ProductivityTrend.STABLE
        assert "null_pointer" in result.recurring_bug_patterns

    @pytest.mark.asyncio
    async def test_analyze_meeting_efficiency_success(self, team_productivity_analyzer, date_range):
        """Test successful meeting efficiency analysis."""
        team_id = "test-team"
        mock_meetings = MockDataGenerator.generate_meeting_data()
        
        with patch.object(team_productivity_analyzer, '_get_meeting_data', return_value=mock_meetings):
            with patch.object(team_productivity_analyzer, '_calculate_total_work_hours', return_value=200.0):
                with patch.object(team_productivity_analyzer, '_get_team_deliverables', return_value=[{"deliverable": "feature"}]):
                    with patch.object(team_productivity_analyzer, '_get_meeting_action_items', return_value=[{"action": "task", "completed": True}]):
                        with patch.object(team_productivity_analyzer, '_calculate_meeting_productivity_impact', return_value=15.0):
                            with patch.object(team_productivity_analyzer, '_store_meeting_analytics'):
                                result = await team_productivity_analyzer.analyze_meeting_efficiency(team_id, date_range)
        
        assert isinstance(result, MeetingEfficiencyMetrics)
        assert result.team_id == team_id
        assert result.total_meeting_hours >= 0
        assert 0 <= result.meeting_efficiency_score <= 100
        assert 0 <= result.focus_time_percentage <= 100
        assert result.meeting_overhead_impact == 15.0

    @pytest.mark.asyncio
    async def test_analyze_capacity_utilization_success(self, team_productivity_analyzer, date_range):
        """Test successful capacity utilization analysis."""
        team_id = "test-team"
        
        with patch.object(team_productivity_analyzer, '_get_team_capacity', return_value=200.0):
            with patch.object(team_productivity_analyzer, '_get_actual_workload', return_value=170.0):
                with patch.object(team_productivity_analyzer, '_get_individual_workloads', return_value={"member-1": 40, "member-2": 35}):
                    with patch.object(team_productivity_analyzer, '_calculate_overtime_hours', return_value=25.0):
                        with patch.object(team_productivity_analyzer, '_assess_burnout_risk', return_value=BurnoutRisk.MODERATE):
                            with patch.object(team_productivity_analyzer, '_identify_stress_indicators', return_value=["high_workload"]):
                                with patch.object(team_productivity_analyzer, '_calculate_workload_balance_score', return_value=75.0):
                                    with patch.object(team_productivity_analyzer, '_calculate_sustainable_pace_indicator', return_value=78.0):
                                        with patch.object(team_productivity_analyzer, '_calculate_velocity_stability', return_value=82.0):
                                            with patch.object(team_productivity_analyzer, '_store_capacity_analytics'):
                                                result = await team_productivity_analyzer.analyze_capacity_utilization(team_id, date_range)
        
        assert isinstance(result, CapacityUtilizationMetrics)
        assert result.team_id == team_id
        assert result.capacity_utilization == 85.0  # 170/200 * 100
        assert result.burnout_risk_level == BurnoutRisk.MODERATE
        assert "high_workload" in result.stress_indicators
        assert result.workload_balance_score == 75.0

    @pytest.mark.asyncio
    async def test_detect_productivity_trends_success(self, team_productivity_analyzer, date_range):
        """Test successful productivity trend detection."""
        team_id = "test-team"
        mock_historical_data = MockDataGenerator.generate_historical_productivity_data()
        
        with patch.object(team_productivity_analyzer, '_get_historical_productivity_data', return_value=mock_historical_data):
            with patch.object(team_productivity_analyzer, '_analyze_overall_productivity_trend', return_value=ProductivityTrend.IMPROVING):
                with patch.object(team_productivity_analyzer, '_analyze_velocity_trend', return_value=ProductivityTrend.STABLE):
                    with patch.object(team_productivity_analyzer, '_analyze_quality_trend', return_value=ProductivityTrend.IMPROVING):
                        with patch.object(team_productivity_analyzer, '_analyze_collaboration_trend', return_value=ProductivityTrend.STABLE):
                            with patch.object(team_productivity_analyzer, '_analyze_satisfaction_trend', return_value=ProductivityTrend.IMPROVING):
                                with patch.object(team_productivity_analyzer, '_generate_predictive_insights', return_value=["insight1"]):
                                    with patch.object(team_productivity_analyzer, '_generate_improvement_recommendations', return_value=["recommendation1"]):
                                        with patch.object(team_productivity_analyzer, '_identify_productivity_risk_factors', return_value=["risk1"]):
                                            with patch.object(team_productivity_analyzer, '_store_trend_analytics'):
                                                result = await team_productivity_analyzer.detect_productivity_trends(team_id, date_range)
        
        assert isinstance(result, ProductivityTrends)
        assert result.team_id == team_id
        assert result.overall_trend == ProductivityTrend.IMPROVING
        assert result.velocity_trend == ProductivityTrend.STABLE
        assert "insight1" in result.predictive_insights
        assert "recommendation1" in result.improvement_recommendations
        assert "risk1" in result.risk_factors

    @pytest.mark.asyncio
    async def test_error_handling_in_analysis(self, team_productivity_analyzer, date_range):
        """Test error handling in analysis methods."""
        team_id = "test-team"
        
        # Test error in code review analysis
        with patch.object(team_productivity_analyzer, '_get_team_repositories', side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                await team_productivity_analyzer.analyze_code_review_participation(team_id, date_range)
        
        # Test error in collaboration analysis
        with patch.object(team_productivity_analyzer, '_analyze_cross_team_interactions', side_effect=Exception("Network Error")):
            with pytest.raises(Exception, match="Network Error"):
                await team_productivity_analyzer.calculate_collaboration_score(team_id, date_range)

    @pytest.mark.asyncio
    async def test_edge_case_empty_data(self, team_productivity_analyzer, date_range):
        """Test handling of empty data sets."""
        team_id = "test-team"
        
        # Test with empty deployment data
        with patch.object(team_productivity_analyzer, '_get_deployment_data', return_value=[]):
            with patch.object(team_productivity_analyzer, '_calculate_quality_correlation', return_value=0.0):
                with patch.object(team_productivity_analyzer, '_store_deployment_analytics'):
                    result = await team_productivity_analyzer.analyze_deployment_frequency(team_id, date_range)
        
        assert isinstance(result, DeploymentMetrics)
        assert result.deployment_frequency == 0
        assert result.success_rate == 0
        assert result.rollback_rate == 0

    @pytest.mark.asyncio
    async def test_edge_case_single_data_point(self, team_productivity_analyzer, date_range):
        """Test handling of single data points."""
        team_id = "test-team"
        single_deployment = [MockDataGenerator.generate_deployment_data(1)[0]]
        
        with patch.object(team_productivity_analyzer, '_get_deployment_data', return_value=single_deployment):
            with patch.object(team_productivity_analyzer, '_calculate_quality_correlation', return_value=0.5):
                with patch.object(team_productivity_analyzer, '_store_deployment_analytics'):
                    result = await team_productivity_analyzer.analyze_deployment_frequency(team_id, date_range)
        
        assert isinstance(result, DeploymentMetrics)
        assert result.deployment_frequency > 0

    @pytest.mark.asyncio
    async def test_burnout_risk_assessment_edge_cases(self, team_productivity_analyzer, date_range):
        """Test burnout risk assessment with various scenarios."""
        team_id = "test-team"
        
        # Test critical burnout risk
        with patch.object(team_productivity_analyzer, '_get_team_capacity', return_value=100.0):
            with patch.object(team_productivity_analyzer, '_get_actual_workload', return_value=98.0):  # 98% utilization
                with patch.object(team_productivity_analyzer, '_get_individual_workloads', return_value={"member-1": 50}):
                    with patch.object(team_productivity_analyzer, '_calculate_overtime_hours', return_value=45.0):  # High overtime
                        with patch.object(team_productivity_analyzer, '_identify_stress_indicators', return_value=["burnout_signs"]):
                            with patch.object(team_productivity_analyzer, '_calculate_workload_balance_score', return_value=30.0):
                                with patch.object(team_productivity_analyzer, '_calculate_sustainable_pace_indicator', return_value=25.0):
                                    with patch.object(team_productivity_analyzer, '_calculate_velocity_stability', return_value=40.0):
                                        with patch.object(team_productivity_analyzer, '_store_capacity_analytics'):
                                            result = await team_productivity_analyzer.analyze_capacity_utilization(team_id, date_range)
        
        assert result.burnout_risk_level == BurnoutRisk.CRITICAL
        assert result.capacity_utilization == 98.0
        assert result.overtime_hours == 45.0

    @pytest.mark.asyncio
    async def test_meeting_efficiency_zero_meetings(self, team_productivity_analyzer, date_range):
        """Test meeting efficiency analysis with zero meetings."""
        team_id = "test-team"
        
        with patch.object(team_productivity_analyzer, '_get_meeting_data', return_value=[]):
            with patch.object(team_productivity_analyzer, '_calculate_total_work_hours', return_value=200.0):
                with patch.object(team_productivity_analyzer, '_get_team_deliverables', return_value=[{"deliverable": "feature"}]):
                    with patch.object(team_productivity_analyzer, '_get_meeting_action_items', return_value=[]):
                        with patch.object(team_productivity_analyzer, '_calculate_meeting_productivity_impact', return_value=0.0):
                            with patch.object(team_productivity_analyzer, '_store_meeting_analytics'):
                                result = await team_productivity_analyzer.analyze_meeting_efficiency(team_id, date_range)
        
        assert result.total_meeting_hours == 0
        assert result.meeting_efficiency_score == 0
        assert result.focus_time_percentage == 100.0  # All time is focus time

    @pytest.mark.asyncio
    async def test_bug_analysis_no_resolved_bugs(self, team_productivity_analyzer, date_range):
        """Test bug analysis with no resolved bugs."""
        team_id = "test-team"
        unresolved_bugs = [
            {"created_date": date_range[0], "resolved_date": None, "severity": "high"},
            {"created_date": date_range[0] + timedelta(days=1), "resolved_date": None, "severity": "medium"}
        ]
        
        with patch.object(team_productivity_analyzer, '_get_bug_data', return_value=unresolved_bugs):
            with patch.object(team_productivity_analyzer, '_identify_recurring_bug_patterns', return_value=[]):
                with patch.object(team_productivity_analyzer, '_calculate_prevention_effectiveness', return_value=50.0):
                    with patch.object(team_productivity_analyzer, '_predict_bug_trends', return_value=ProductivityTrend.DECLINING):
                        with patch.object(team_productivity_analyzer, '_store_bug_analytics'):
                            result = await team_productivity_analyzer.analyze_bug_patterns(team_id, date_range)
        
        assert result.bugs_discovered == 2
        assert result.bugs_resolved == 0
        assert result.average_resolution_time_hours == 0
        assert result.resolution_velocity == 0

    def test_productivity_trend_enum_values(self):
        """Test ProductivityTrend enum values."""
        assert ProductivityTrend.IMPROVING.value == "improving"
        assert ProductivityTrend.STABLE.value == "stable"
        assert ProductivityTrend.DECLINING.value == "declining"
        assert ProductivityTrend.VOLATILE.value == "volatile"

    def test_burnout_risk_enum_values(self):
        """Test BurnoutRisk enum values."""
        assert BurnoutRisk.LOW.value == "low"
        assert BurnoutRisk.MODERATE.value == "moderate"
        assert BurnoutRisk.HIGH.value == "high"
        assert BurnoutRisk.CRITICAL.value == "critical"

    def test_collaboration_level_enum_values(self):
        """Test CollaborationLevel enum values."""
        assert CollaborationLevel.MINIMAL.value == "minimal"
        assert CollaborationLevel.MODERATE.value == "moderate"
        assert CollaborationLevel.HIGH.value == "high"
        assert CollaborationLevel.EXTENSIVE.value == "extensive"

    def test_review_metrics_dataclass(self):
        """Test ReviewMetrics dataclass creation and attributes."""
        metrics = ReviewMetrics(
            reviewer_id="test-reviewer",
            reviews_completed=10,
            reviews_requested=12,
            average_review_time_hours=4.5,
            review_quality_score=85.0,
            mentoring_impact_score=75.0,
            review_velocity=2.5,
            approval_rate=90.0,
            feedback_depth_score=80.0,
            knowledge_sharing_score=70.0
        )
        
        assert metrics.reviewer_id == "test-reviewer"
        assert metrics.reviews_completed == 10
        assert metrics.review_quality_score == 85.0

    def test_collaboration_metrics_dataclass(self):
        """Test CollaborationMetrics dataclass creation and attributes."""
        metrics = CollaborationMetrics(
            team_id="test-team",
            cross_team_interactions=5,
            dependency_count=3,
            knowledge_sharing_sessions=2,
            communication_frequency=10.5,
            collaboration_effectiveness=75.0,
            bottleneck_indicators=["delays"],
            knowledge_silos=["db_knowledge"],
            collaboration_network_centrality=0.65
        )
        
        assert metrics.team_id == "test-team"
        assert metrics.cross_team_interactions == 5
        assert metrics.collaboration_effectiveness == 75.0
        assert "delays" in metrics.bottleneck_indicators

    @pytest.mark.asyncio
    async def test_concurrent_analysis_operations(self, team_productivity_analyzer, date_range):
        """Test concurrent execution of multiple analysis operations."""
        team_id = "test-team"
        
        # Mock all required methods
        with patch.object(team_productivity_analyzer, '_get_team_repositories', return_value=["repo1"]):
            with patch.object(team_productivity_analyzer, '_get_team_members', return_value=["member-1"]):
                with patch.object(team_productivity_analyzer, '_calculate_review_metrics') as mock_review:
                    with patch.object(team_productivity_analyzer, '_get_deployment_data', return_value=MockDataGenerator.generate_deployment_data()):
                        with patch.object(team_productivity_analyzer, '_calculate_quality_correlation', return_value=0.8):
                            with patch.object(team_productivity_analyzer, '_store_review_analytics'):
                                with patch.object(team_productivity_analyzer, '_store_deployment_analytics'):
                                    mock_review.return_value = ReviewMetrics(
                                        reviewer_id="member-1",
                                        reviews_completed=5,
                                        reviews_requested=6,
                                        average_review_time_hours=3.0,
                                        review_quality_score=80.0,
                                        mentoring_impact_score=70.0,
                                        review_velocity=2.0,
                                        approval_rate=85.0,
                                        feedback_depth_score=75.0,
                                        knowledge_sharing_score=65.0
                                    )
                                    
                                    # Run multiple analyses concurrently
                                    tasks = [
                                        team_productivity_analyzer.analyze_code_review_participation(team_id, date_range),
                                        team_productivity_analyzer.analyze_deployment_frequency(team_id, date_range)
                                    ]
                                    
                                    results = await asyncio.gather(*tasks)
        
        assert len(results) == 2
        assert isinstance(results[0], dict)  # Review metrics
        assert isinstance(results[1], DeploymentMetrics)  # Deployment metrics

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, team_productivity_analyzer, date_range):
        """Test performance with large datasets."""
        team_id = "test-team"
        large_pr_dataset = MockDataGenerator.generate_pull_requests(100)  # Large dataset
        
        with patch.object(team_productivity_analyzer, '_get_team_repositories', return_value=["repo1"]):
            with patch.object(team_productivity_analyzer, '_get_team_members', return_value=[f"member-{i}" for i in range(20)]):  # Large team
                with patch.object(team_productivity_analyzer.github_service, 'get_pull_requests_in_range', return_value=large_pr_dataset):
                    with patch.object(team_productivity_analyzer, '_calculate_review_metrics') as mock_calc:
                        with patch.object(team_productivity_analyzer, '_store_review_analytics'):
                            mock_calc.return_value = ReviewMetrics(
                                reviewer_id="member-1",
                                reviews_completed=50,
                                reviews_requested=60,
                                average_review_time_hours=2.5,
                                review_quality_score=88.0,
                                mentoring_impact_score=82.0,
                                review_velocity=5.0,
                                approval_rate=92.0,
                                feedback_depth_score=85.0,
                                knowledge_sharing_score=78.0
                            )
                            
                            import time
                            start_time = time.time()
                            result = await team_productivity_analyzer.analyze_code_review_participation(team_id, date_range)
                            end_time = time.time()
        
        # Verify the analysis completed and returned results
        assert isinstance(result, dict)
        assert len(result) == 20  # All team members analyzed
        
        # Performance should be reasonable (less than 5 seconds for this test)
        execution_time = end_time - start_time
        assert execution_time < 5.0, f"Analysis took too long: {execution_time} seconds"


class TestMockDataGenerator:
    """Test suite for MockDataGenerator utility class."""

    def test_generate_pull_requests(self):
        """Test pull request data generation."""
        prs = MockDataGenerator.generate_pull_requests(5)
        
        assert len(prs) == 5
        assert all("id" in pr for pr in prs)
        assert all("reviews" in pr for pr in prs)
        assert all(isinstance(pr["reviews"], list) for pr in prs)

    def test_generate_deployment_data(self):
        """Test deployment data generation."""
        deployments = MockDataGenerator.generate_deployment_data(3)
        
        assert len(deployments) == 3
        assert all("success" in deploy for deploy in deployments)
        assert all("lead_time_hours" in deploy for deploy in deployments)
        assert all(isinstance(deploy["success"], bool) for deploy in deployments)

    def test_generate_bug_data(self):
        """Test bug data generation."""
        bugs = MockDataGenerator.generate_bug_data(10)
        
        assert len(bugs) == 10
        assert all("severity" in bug for bug in bugs)
        assert all("created_date" in bug for bug in bugs)
        assert all(bug["severity"] in ["low", "medium", "high", "critical"] for bug in bugs)

    def test_generate_meeting_data(self):
        """Test meeting data generation."""
        meetings = MockDataGenerator.generate_meeting_data(4)
        
        assert len(meetings) == 4
        assert all("duration_hours" in meeting for meeting in meetings)
        assert all("has_outcomes" in meeting for meeting in meetings)
        assert all(isinstance(meeting["has_outcomes"], bool) for meeting in meetings)

    def test_generate_team_capacity_data(self):
        """Test team capacity data generation."""
        capacity_data = MockDataGenerator.generate_team_capacity_data()
        
        assert "team_id" in capacity_data
        assert "total_capacity_hours" in capacity_data
        assert "members" in capacity_data
        assert isinstance(capacity_data["members"], dict)

    def test_generate_historical_productivity_data(self):
        """Test historical productivity data generation."""
        historical_data = MockDataGenerator.generate_historical_productivity_data()
        
        assert "velocity" in historical_data
        assert "quality" in historical_data
        assert "collaboration" in historical_data
        assert isinstance(historical_data["velocity"], list)
        assert len(historical_data["velocity"]) == 7  # 7 data points


if __name__ == "__main__":
    pytest.main([__file__, "-v"])