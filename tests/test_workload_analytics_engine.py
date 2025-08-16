"""
Tests for Workload Analytics Engine.

This module tests the comprehensive workload tracking, analysis, and reporting
capabilities for team members and assignment hooks.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from devsync_ai.analytics.workload_analytics_engine import (
    WorkloadAnalyticsEngine,
    WorkloadStatus,
    CapacityAlert,
    TeamMemberCapacity,
    WorkloadDistribution,
    AssignmentImpactAnalysis,
    default_workload_analytics_engine
)


class TestWorkloadAnalyticsEngine:
    """Test suite for WorkloadAnalyticsEngine."""
    
    @pytest.fixture
    def engine(self):
        """Create a workload analytics engine for testing."""
        return WorkloadAnalyticsEngine()
    
    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock()
        mock_conn.fetch = AsyncMock()
        mock_conn.execute = AsyncMock()
        return mock_conn
    
    @pytest.fixture
    def sample_workload_data(self):
        """Sample workload data for testing."""
        return {
            "user_id": "user123",
            "team_id": "team1",
            "active_tickets": 4,
            "total_story_points": 20,
            "estimated_hours": 80.0,
            "avg_story_points": 5.0,
            "display_name": "John Doe",
            "email": "john.doe@company.com"
        }
    
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
    
    @pytest.mark.asyncio
    async def test_initialize(self, engine, mock_db_connection):
        """Test engine initialization."""
        with patch('devsync_ai.analytics.workload_analytics_engine.get_database_connection', 
                   return_value=mock_db_connection):
            await engine.initialize()
            assert engine.db_connection == mock_db_connection
    
    @pytest.mark.asyncio
    async def test_get_team_member_capacity_from_cache(self, engine, sample_team_member_capacity):
        """Test getting team member capacity from cache."""
        # Setup cache
        cache_key = "user123_team1"
        engine._capacity_cache[cache_key] = sample_team_member_capacity
        engine._last_cache_update[cache_key] = datetime.now(timezone.utc)
        
        result = await engine.get_team_member_capacity("user123", "team1")
        
        assert result == sample_team_member_capacity
        assert result.user_id == "user123"
        assert result.workload_status == WorkloadStatus.HIGH
    
    @pytest.mark.asyncio
    async def test_get_team_member_capacity_from_database(
        self, 
        engine, 
        mock_db_connection, 
        sample_workload_data
    ):
        """Test getting team member capacity from database."""
        engine.db_connection = mock_db_connection
        mock_db_connection.fetchrow.return_value = sample_workload_data
        
        with patch.object(engine, '_calculate_member_capacity') as mock_calculate:
            mock_capacity = TeamMemberCapacity(
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
                estimated_completion_date=None,
                projected_capacity_date=None,
                skill_areas=["backend"],
                preferred_ticket_types=["story"],
                last_updated=datetime.now(timezone.utc)
            )
            mock_calculate.return_value = mock_capacity
            
            result = await engine.get_team_member_capacity("user123", "team1")
            
            assert result == mock_capacity
            mock_calculate.assert_called_once_with(sample_workload_data)
    
    @pytest.mark.asyncio
    async def test_analyze_assignment_impact_approve(self, engine, sample_team_member_capacity):
        """Test assignment impact analysis with approve recommendation."""
        with patch.object(engine, 'get_team_member_capacity', return_value=sample_team_member_capacity):
            with patch.object(engine, '_calculate_projected_utilization', return_value=0.85):
                with patch.object(engine, '_estimate_completion_date', 
                                return_value=datetime.now(timezone.utc) + timedelta(days=12)):
                    with patch.object(engine, '_calculate_skill_match', return_value=0.8):
                        with patch.object(engine, '_find_alternative_assignees', return_value=[]):
                            with patch.object(engine, '_analyze_team_impact', 
                                            return_value={"impact": "low", "reasons": []}):
                                
                                result = await engine.analyze_assignment_impact(
                                    assignee_id="user123",
                                    team_id="team1",
                                    ticket_key="PROJ-123",
                                    story_points=3,
                                    estimated_hours=12.0
                                )
                                
                                assert isinstance(result, AssignmentImpactAnalysis)
                                assert result.assignee_id == "user123"
                                assert result.ticket_key == "PROJ-123"
                                assert result.story_points == 3
                                assert result.estimated_hours == 12.0
                                assert result.projected_utilization == 0.85
                                assert result.skill_match_score == 0.8
                                assert result.assignment_recommendation == "approve"
    
    @pytest.mark.asyncio
    async def test_analyze_assignment_impact_overload_warning(self, engine, sample_team_member_capacity):
        """Test assignment impact analysis with overload warning."""
        # Modify capacity to be near overload
        overloaded_capacity = sample_team_member_capacity
        overloaded_capacity.capacity_utilization = 0.95
        overloaded_capacity.workload_status = WorkloadStatus.HIGH
        
        with patch.object(engine, 'get_team_member_capacity', return_value=overloaded_capacity):
            with patch.object(engine, '_calculate_projected_utilization', return_value=1.1):
                with patch.object(engine, '_estimate_completion_date', 
                                return_value=datetime.now(timezone.utc) + timedelta(days=15)):
                    with patch.object(engine, '_calculate_skill_match', return_value=0.6):
                        with patch.object(engine, '_find_alternative_assignees', 
                                        return_value=[("user456", 0.8), ("user789", 0.7)]):
                            with patch.object(engine, '_analyze_team_impact', 
                                            return_value={"impact": "medium", "reasons": ["High utilization"]}):
                                
                                result = await engine.analyze_assignment_impact(
                                    assignee_id="user123",
                                    team_id="team1",
                                    ticket_key="PROJ-124",
                                    story_points=5,
                                    estimated_hours=20.0
                                )
                                
                                assert result.projected_workload_status == WorkloadStatus.OVERLOADED
                                assert result.impact_severity == "high"
                                assert result.assignment_recommendation == "reassign"
                                assert len(result.alternative_assignees) == 2
                                assert len(result.capacity_warnings) > 0
    
    @pytest.mark.asyncio
    async def test_get_team_workload_distribution(self, engine, sample_team_member_capacity):
        """Test getting team workload distribution."""
        team_members = ["user123", "user456", "user789"]
        
        # Create different capacity levels for team members
        member_capacities = [
            sample_team_member_capacity,  # High utilization
            TeamMemberCapacity(
                user_id="user456",
                display_name="Jane Smith",
                email="jane.smith@company.com",
                team_id="team1",
                active_tickets=2,
                total_story_points=8,
                estimated_hours=32.0,
                max_concurrent_tickets=5,
                weekly_capacity_hours=40.0,
                capacity_utilization=0.4,
                recent_velocity=6.0,
                average_completion_time=4.0,
                quality_score=0.9,
                workload_status=WorkloadStatus.UNDERUTILIZED,
                alerts=[],
                estimated_completion_date=None,
                projected_capacity_date=datetime.now(timezone.utc),
                skill_areas=["frontend"],
                preferred_ticket_types=["story"],
                last_updated=datetime.now(timezone.utc)
            ),
            TeamMemberCapacity(
                user_id="user789",
                display_name="Bob Johnson",
                email="bob.johnson@company.com",
                team_id="team1",
                active_tickets=6,
                total_story_points=30,
                estimated_hours=120.0,
                max_concurrent_tickets=5,
                weekly_capacity_hours=40.0,
                capacity_utilization=1.2,
                recent_velocity=10.0,
                average_completion_time=4.0,
                quality_score=0.75,
                workload_status=WorkloadStatus.OVERLOADED,
                alerts=[CapacityAlert.OVER_CAPACITY],
                estimated_completion_date=datetime.now(timezone.utc) + timedelta(days=15),
                projected_capacity_date=datetime.now(timezone.utc) + timedelta(days=10),
                skill_areas=["backend", "devops"],
                preferred_ticket_types=["story", "task"],
                last_updated=datetime.now(timezone.utc)
            )
        ]
        
        with patch.object(engine, '_get_team_members', return_value=team_members):
            with patch.object(engine, 'get_team_member_capacity', side_effect=member_capacities):
                with patch.object(engine, '_generate_rebalancing_suggestions', return_value=[]):
                    with patch.object(engine, '_calculate_velocity_trend', return_value="stable"):
                        with patch.object(engine, '_calculate_capacity_trend', return_value="stable"):
                            
                            result = await engine.get_team_workload_distribution("team1")
                            
                            assert isinstance(result, WorkloadDistribution)
                            assert result.team_id == "team1"
                            assert result.total_active_tickets == 12  # 4 + 2 + 6
                            assert result.total_story_points == 58  # 20 + 8 + 30
                            assert len(result.members) == 3
                            assert len(result.overloaded_members) == 1  # user789
                            assert len(result.underutilized_members) == 1  # user456
                            assert result.utilization_average > 0
                            assert result.workload_variance > 0
    
    @pytest.mark.asyncio
    async def test_generate_capacity_alerts(self, engine):
        """Test generating capacity alerts."""
        # Mock distribution with overloaded members
        mock_distribution = WorkloadDistribution(
            team_id="team1",
            total_active_tickets=15,
            total_story_points=75,
            total_estimated_hours=300.0,
            workload_variance=8.0,  # High variance
            utilization_average=0.85,
            utilization_std_dev=0.3,
            members=[],
            overloaded_members=["user789"],
            underutilized_members=["user456"],
            distribution_alerts=[],
            rebalancing_suggestions=[],
            velocity_trend="decreasing",
            capacity_trend="stable",
            last_updated=datetime.now(timezone.utc)
        )
        
        # Add member details for overloaded member
        overloaded_member = TeamMemberCapacity(
            user_id="user789",
            display_name="Bob Johnson",
            email="bob.johnson@company.com",
            team_id="team1",
            active_tickets=6,
            total_story_points=30,
            estimated_hours=120.0,
            max_concurrent_tickets=5,
            weekly_capacity_hours=40.0,
            capacity_utilization=1.2,
            recent_velocity=10.0,
            average_completion_time=4.0,
            quality_score=0.75,
            workload_status=WorkloadStatus.OVERLOADED,
            alerts=[CapacityAlert.OVER_CAPACITY],
            estimated_completion_date=None,
            projected_capacity_date=None,
            skill_areas=["backend"],
            preferred_ticket_types=["story"],
            last_updated=datetime.now(timezone.utc)
        )
        mock_distribution.members = [overloaded_member]
        
        with patch.object(engine, 'get_team_workload_distribution', return_value=mock_distribution):
            alerts = await engine.generate_capacity_alerts("team1")
            
            assert len(alerts) >= 3  # Overload, variance, velocity decline
            
            # Check for overload alert
            overload_alerts = [a for a in alerts if a["type"] == "overload_warning"]
            assert len(overload_alerts) == 1
            assert overload_alerts[0]["member_id"] == "user789"
            assert overload_alerts[0]["severity"] == "high"
            
            # Check for distribution alert
            distribution_alerts = [a for a in alerts if a["type"] == "uneven_distribution"]
            assert len(distribution_alerts) == 1
            
            # Check for velocity alert
            velocity_alerts = [a for a in alerts if a["type"] == "velocity_decline"]
            assert len(velocity_alerts) == 1
    
    @pytest.mark.asyncio
    async def test_update_member_workload(self, engine, mock_db_connection):
        """Test updating member workload."""
        engine.db_connection = mock_db_connection
        
        result = await engine.update_member_workload(
            user_id="user123",
            team_id="team1",
            ticket_key="PROJ-123",
            action="assigned",
            story_points=5,
            estimated_hours=20.0
        )
        
        assert result is True
        mock_db_connection.execute.assert_called_once()
        
        # Check that cache was invalidated
        cache_key = "user123_team1"
        assert cache_key not in engine._capacity_cache
    
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


class TestWorkloadAnalyticsIntegration:
    """Integration tests for workload analytics with other components."""
    
    @pytest.mark.asyncio
    async def test_assignment_hook_integration(self):
        """Test integration with assignment hooks."""
        # This would test the full integration with the AssignmentChangeHook
        # For now, we'll test that the engine can be imported and used
        from devsync_ai.analytics.workload_analytics_engine import default_workload_analytics_engine
        
        assert default_workload_analytics_engine is not None
        assert isinstance(default_workload_analytics_engine, WorkloadAnalyticsEngine)
    
    @pytest.mark.asyncio
    async def test_database_integration(self):
        """Test database integration."""
        # This would test actual database operations
        # For now, we'll test the query structure
        engine = WorkloadAnalyticsEngine()
        
        # Test that the engine has the expected methods
        assert hasattr(engine, '_query_member_workload')
        assert hasattr(engine, '_update_workload_database')
        assert hasattr(engine, '_get_team_members')
    
    @pytest.mark.asyncio
    async def test_notification_integration(self):
        """Test integration with notification system."""
        # This would test integration with the notification system
        # For now, we'll test that the required data structures exist
        from devsync_ai.analytics.workload_analytics_engine import AssignmentImpactAnalysis
        
        # Test that AssignmentImpactAnalysis has all required fields
        required_fields = [
            'assignee_id', 'ticket_key', 'story_points', 'estimated_hours',
            'current_workload', 'projected_utilization', 'projected_completion_date',
            'projected_workload_status', 'impact_severity', 'capacity_warnings',
            'skill_match_score', 'assignment_recommendation', 'alternative_assignees',
            'team_impact', 'created_at'
        ]
        
        for field in required_fields:
            assert hasattr(AssignmentImpactAnalysis, '__dataclass_fields__')
            assert field in AssignmentImpactAnalysis.__dataclass_fields__


if __name__ == "__main__":
    pytest.main([__file__])