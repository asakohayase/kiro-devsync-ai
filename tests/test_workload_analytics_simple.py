"""
Simple tests for Workload Analytics Engine without full application dependencies.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from devsync_ai.analytics.workload_analytics_engine import (
    WorkloadAnalyticsEngine,
    WorkloadStatus,
    CapacityAlert,
    TeamMemberCapacity,
    AssignmentImpactAnalysis
)


class TestWorkloadAnalyticsSimple:
    """Simple test suite for WorkloadAnalyticsEngine core functionality."""
    
    @pytest.fixture
    def engine(self):
        """Create a workload analytics engine for testing."""
        return WorkloadAnalyticsEngine()
    
    @pytest.fixture
    def sample_team_member_capacity(self):
        """Sample team member capacity for testing."""
        return TeamMemberCapacity(
            user_id="user123",
            display_name="John Doe",
            email="john.doe@company.com",
            team_id="team1",
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
            skill_areas=["backend", "frontend"],
            preferred_ticket_types=["story", "task"],
            last_updated=datetime.now(timezone.utc)
        )
    
    def test_determine_workload_status(self, engine):
        """Test workload status determination."""
        assert engine._determine_workload_status(1.3) == WorkloadStatus.CRITICAL
        assert engine._determine_workload_status(1.1) == WorkloadStatus.OVERLOADED
        assert engine._determine_workload_status(0.9) == WorkloadStatus.HIGH
        assert engine._determine_workload_status(0.6) == WorkloadStatus.OPTIMAL
        assert engine._determine_workload_status(0.3) == WorkloadStatus.UNDERUTILIZED
    
    def test_generate_member_alerts(self, engine):
        """Test generating member alerts."""
        # Test over capacity
        alerts = engine._generate_member_alerts(1.1, 6, 5)
        assert CapacityAlert.OVER_CAPACITY in alerts
        
        # Test approaching limit
        alerts = engine._generate_member_alerts(0.95, 4, 5)
        assert CapacityAlert.APPROACHING_LIMIT in alerts
        
        # Test normal capacity
        alerts = engine._generate_member_alerts(0.7, 3, 5)
        assert len(alerts) == 0
    
    def test_assess_impact_severity(self, engine, sample_team_member_capacity):
        """Test impact severity assessment."""
        # Critical status
        severity = engine._assess_impact_severity(
            sample_team_member_capacity, 1.3, WorkloadStatus.CRITICAL
        )
        assert severity == "critical"
        
        # Overloaded status
        severity = engine._assess_impact_severity(
            sample_team_member_capacity, 1.1, WorkloadStatus.OVERLOADED
        )
        assert severity == "high"
        
        # High utilization
        severity = engine._assess_impact_severity(
            sample_team_member_capacity, 0.95, WorkloadStatus.HIGH
        )
        assert severity == "medium"
        
        # Normal utilization
        severity = engine._assess_impact_severity(
            sample_team_member_capacity, 0.7, WorkloadStatus.OPTIMAL
        )
        assert severity == "low"
    
    def test_generate_assignment_recommendation(self, engine):
        """Test assignment recommendation generation."""
        # Critical status should reject
        recommendation = engine._generate_assignment_recommendation(
            "critical", 0.8, WorkloadStatus.CRITICAL
        )
        assert recommendation == "reject"
        
        # Overloaded status should reassign
        recommendation = engine._generate_assignment_recommendation(
            "high", 0.8, WorkloadStatus.OVERLOADED
        )
        assert recommendation == "reassign"
        
        # High impact with low skill match should caution
        recommendation = engine._generate_assignment_recommendation(
            "high", 0.4, WorkloadStatus.HIGH
        )
        assert recommendation == "caution"
        
        # Good skill match with low impact should approve
        recommendation = engine._generate_assignment_recommendation(
            "low", 0.9, WorkloadStatus.OPTIMAL
        )
        assert recommendation == "approve"
    
    def test_generate_capacity_warnings(self, engine, sample_team_member_capacity):
        """Test capacity warning generation."""
        # Critical overload
        warnings = engine._generate_capacity_warnings(
            sample_team_member_capacity, 1.3, WorkloadStatus.CRITICAL
        )
        assert len(warnings) > 0
        assert any("critical overload" in w.lower() for w in warnings)
        
        # Overload
        warnings = engine._generate_capacity_warnings(
            sample_team_member_capacity, 1.1, WorkloadStatus.OVERLOADED
        )
        assert len(warnings) > 0
        assert any("overload" in w.lower() for w in warnings)
        
        # High utilization
        warnings = engine._generate_capacity_warnings(
            sample_team_member_capacity, 0.95, WorkloadStatus.HIGH
        )
        assert len(warnings) > 0
        assert any("close to capacity" in w.lower() for w in warnings)
        
        # Normal utilization
        warnings = engine._generate_capacity_warnings(
            sample_team_member_capacity, 0.7, WorkloadStatus.OPTIMAL
        )
        assert len(warnings) == 0
    
    @pytest.mark.asyncio
    async def test_calculate_skill_match(self, engine, sample_team_member_capacity):
        """Test skill match calculation."""
        # Perfect match
        ticket_metadata = {
            "required_skills": ["backend", "frontend"],
            "ticket_type": "story",
            "components": ["api", "ui"]
        }
        
        score = await engine._calculate_skill_match(sample_team_member_capacity, ticket_metadata)
        assert score > 0.8  # Should be high match
        
        # No match
        ticket_metadata = {
            "required_skills": ["mobile", "ios"],
            "ticket_type": "bug",
            "components": ["mobile-app"]
        }
        
        score = await engine._calculate_skill_match(sample_team_member_capacity, ticket_metadata)
        assert score < 0.5  # Should be low match
        
        # Empty metadata
        score = await engine._calculate_skill_match(sample_team_member_capacity, {})
        assert score == 0.7  # Default moderate match
    
    @pytest.mark.asyncio
    async def test_calculate_projected_utilization(self, engine, sample_team_member_capacity):
        """Test projected utilization calculation."""
        projected = await engine._calculate_projected_utilization(
            sample_team_member_capacity, 3, 12.0
        )
        
        # Should be higher than current utilization
        assert projected > sample_team_member_capacity.capacity_utilization
        
        # Should account for both ticket count and hours
        assert projected > 0.8  # Current is 0.8, adding more should increase
    
    @pytest.mark.asyncio
    async def test_estimate_completion_date(self, engine, sample_team_member_capacity):
        """Test completion date estimation."""
        completion_date = await engine._estimate_completion_date(
            sample_team_member_capacity, 5, 20.0
        )
        
        # Should be in the future
        assert completion_date > datetime.now(timezone.utc)
        
        # Should be reasonable (within a few weeks)
        max_expected = datetime.now(timezone.utc) + timedelta(weeks=8)
        assert completion_date < max_expected
    
    @pytest.mark.asyncio
    async def test_update_member_workload_cache_invalidation(self, engine):
        """Test that updating workload invalidates cache."""
        # Setup cache
        cache_key = "user123_team1"
        engine._capacity_cache[cache_key] = "cached_data"
        
        with patch.object(engine, '_update_workload_database', return_value=None):
            result = await engine.update_member_workload(
                user_id="user123",
                team_id="team1",
                ticket_key="PROJ-123",
                action="assigned",
                story_points=5,
                estimated_hours=20.0
            )
            
            assert result is True
            # Cache should be invalidated
            assert cache_key not in engine._capacity_cache
    
    def test_cache_validity_check(self, engine):
        """Test cache validity checking."""
        cache_key = "test_key"
        
        # No cache entry
        assert not engine._is_cache_valid(cache_key)
        
        # Fresh cache entry
        engine._last_cache_update[cache_key] = datetime.now(timezone.utc)
        assert engine._is_cache_valid(cache_key)
        
        # Expired cache entry
        engine._last_cache_update[cache_key] = datetime.now(timezone.utc) - timedelta(minutes=10)
        assert not engine._is_cache_valid(cache_key)
    
    @pytest.mark.asyncio
    async def test_create_default_capacity(self, engine):
        """Test creating default capacity for unknown members."""
        capacity = await engine._create_default_capacity("unknown_user", "team1")
        
        assert capacity.user_id == "unknown_user"
        assert capacity.team_id == "team1"
        assert capacity.active_tickets == 0
        assert capacity.workload_status == WorkloadStatus.OPTIMAL
        assert capacity.capacity_utilization == 0.0
    
    def test_workload_status_enum_values(self):
        """Test that WorkloadStatus enum has expected values."""
        expected_values = ["underutilized", "optimal", "high", "overloaded", "critical"]
        actual_values = [status.value for status in WorkloadStatus]
        
        for expected in expected_values:
            assert expected in actual_values
    
    def test_capacity_alert_enum_values(self):
        """Test that CapacityAlert enum has expected values."""
        expected_values = [
            "approaching_limit", "over_capacity", "skill_mismatch", 
            "velocity_drop", "deadline_risk"
        ]
        actual_values = [alert.value for alert in CapacityAlert]
        
        for expected in expected_values:
            assert expected in actual_values
    
    def test_assignment_impact_analysis_creation(self):
        """Test creating AssignmentImpactAnalysis objects."""
        current_capacity = TeamMemberCapacity(
            user_id="user123",
            display_name="John Doe",
            email="john.doe@company.com",
            team_id="team1",
            active_tickets=3,
            total_story_points=15,
            estimated_hours=60.0,
            max_concurrent_tickets=5,
            weekly_capacity_hours=40.0,
            capacity_utilization=0.75,
            recent_velocity=8.0,
            average_completion_time=4.0,
            quality_score=0.85,
            workload_status=WorkloadStatus.OPTIMAL,
            alerts=[],
            estimated_completion_date=None,
            projected_capacity_date=None,
            skill_areas=["backend"],
            preferred_ticket_types=["story"],
            last_updated=datetime.now(timezone.utc)
        )
        
        analysis = AssignmentImpactAnalysis(
            assignee_id="user123",
            ticket_key="PROJ-123",
            story_points=5,
            estimated_hours=20.0,
            current_workload=current_capacity,
            projected_utilization=0.9,
            projected_completion_date=datetime.now(timezone.utc) + timedelta(days=10),
            projected_workload_status=WorkloadStatus.HIGH,
            impact_severity="medium",
            capacity_warnings=["Approaching capacity limit"],
            skill_match_score=0.8,
            assignment_recommendation="approve",
            alternative_assignees=[("user456", 0.7)],
            team_impact={"impact": "low"},
            created_at=datetime.now(timezone.utc)
        )
        
        assert analysis.assignee_id == "user123"
        assert analysis.impact_severity == "medium"
        assert analysis.assignment_recommendation == "approve"
        assert len(analysis.alternative_assignees) == 1


if __name__ == "__main__":
    pytest.main([__file__])