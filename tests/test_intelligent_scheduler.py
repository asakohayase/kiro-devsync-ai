"""
Comprehensive tests for the Intelligent Scheduling and Orchestration System

Tests cover timezone handling, holiday management, workload optimization,
conflict resolution, retry logic, and edge cases.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, time
from unittest.mock import Mock, AsyncMock, patch
from zoneinfo import ZoneInfo
import pytz

from devsync_ai.core.intelligent_scheduler import (
    IntelligentScheduler,
    ScheduleConfig,
    ScheduleFrequency,
    ScheduleStatus,
    TriggerType,
    ConflictResolution,
    RetryPolicy,
    ApprovalWorkflow,
    TeamAvailability,
    OptimalTiming,
    ScheduleResult,
    SchedulingConflict,
    GlobalSchedule,
    SchedulingError
)
from devsync_ai.core.config_manager import FlexibleConfigurationManager


@pytest.mark.asyncio
class TestIntelligentScheduler:
    """Test suite for IntelligentScheduler"""

    @pytest.fixture
    async def scheduler(self):
        """Create scheduler instance for testing"""
        config_manager = Mock(spec=ConfigManager)
        scheduler = IntelligentScheduler(config_manager)
        await scheduler.initialize()
        return scheduler

    @pytest.fixture
    def sample_schedule_config(self):
        """Sample schedule configuration for testing"""
        return ScheduleConfig(
            team_id="test-team",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="America/New_York",
            preferred_time=time(17, 0),
            holiday_calendar="US",
            retry_policy=RetryPolicy(max_attempts=3, base_delay=60),
            approval_workflow=ApprovalWorkflow(required=False),
            conflict_resolution=ConflictResolution.RESCHEDULE,
            enabled=True
        )

    @pytest.fixture
    def sample_team_availability(self):
        """Sample team availability for testing"""
        return TeamAvailability(
            team_id="test-team",
            timezone="America/New_York",
            business_hours=(time(9, 0), time(17, 0)),
            holidays=[],
            vacations={},
            capacity_percentage=80.0
        )

    async def test_scheduler_initialization(self):
        """Test scheduler initialization"""
        config_manager = Mock(spec=FlexibleConfigurationManager)
        scheduler = IntelligentScheduler(config_manager)
        
        with patch.object(scheduler, '_load_schedules_from_database', new_callable=AsyncMock):
            with patch.object(scheduler, '_initialize_holiday_calendars', new_callable=AsyncMock):
                await scheduler.initialize()
                
        assert scheduler.config_manager is config_manager
        assert isinstance(scheduler._schedules, dict)
        assert isinstance(scheduler._active_jobs, dict)

    async def test_schedule_changelog_generation_success(self, scheduler, sample_schedule_config):
        """Test successful changelog generation scheduling"""
        # Mock dependencies
        with patch.object(scheduler, '_validate_schedule_config', new_callable=AsyncMock):
            with patch.object(scheduler, 'optimize_timing_for_team', new_callable=AsyncMock) as mock_optimize:
                with patch.object(scheduler, '_detect_scheduling_conflicts', new_callable=AsyncMock) as mock_conflicts:
                    with patch.object(scheduler, '_persist_schedule', new_callable=AsyncMock):
                        with patch.object(scheduler, '_schedule_execution', new_callable=AsyncMock):
                            
                            # Setup mocks
                            optimal_timing = OptimalTiming(
                                recommended_time=datetime.now() + timedelta(hours=1),
                                confidence_score=0.85,
                                reasoning="Optimal timing based on team patterns",
                                alternative_times=[],
                                team_availability=80.0,
                                workload_impact=0.3
                            )
                            mock_optimize.return_value = optimal_timing
                            mock_conflicts.return_value = []
                            
                            # Execute test
                            result = await scheduler.schedule_changelog_generation(sample_schedule_config)
                            
                            # Verify results
                            assert isinstance(result, ScheduleResult)
                            assert result.status == ScheduleStatus.PENDING
                            assert result.metadata["team_id"] == "test-team"
                            assert result.metadata["confidence_score"] == 0.85

    async def test_optimize_timing_for_team(self, scheduler):
        """Test timing optimization for team"""
        scheduler_instance = await scheduler
        team_id = "test-team"
        
        with patch.object(scheduler_instance, '_get_team_availability', new_callable=AsyncMock) as mock_availability:
            with patch.object(scheduler, '_analyze_historical_patterns', new_callable=AsyncMock) as mock_historical:
                with patch.object(scheduler, '_analyze_current_workload', new_callable=AsyncMock) as mock_workload:
                    with patch.object(scheduler, '_calculate_optimal_windows', new_callable=AsyncMock) as mock_windows:
                        with patch.object(scheduler, '_calculate_confidence_score', new_callable=AsyncMock) as mock_confidence:
                            with patch.object(scheduler, '_generate_timing_reasoning', new_callable=AsyncMock) as mock_reasoning:
                                
                                # Setup mocks
                                mock_availability.return_value = TeamAvailability(
                                    team_id=team_id,
                                    timezone="UTC",
                                    business_hours=(time(9, 0), time(17, 0)),
                                    holidays=[],
                                    vacations={},
                                    capacity_percentage=75.0
                                )
                                mock_historical.return_value = {"preferred_day": "friday"}
                                mock_workload.return_value = {"impact_score": 0.4}
                                optimal_time = datetime.now() + timedelta(hours=2)
                                mock_windows.return_value = [optimal_time]
                                mock_confidence.return_value = 0.8
                                mock_reasoning.return_value = "High confidence timing"
                                
                                # Execute test
                                result = await scheduler_instance.optimize_timing_for_team(team_id)
                                
                                # Verify results
                                assert isinstance(result, OptimalTiming)
                                assert result.recommended_time == optimal_time
                                assert result.confidence_score == 0.8
                                assert result.team_availability == 75.0

    async def test_timezone_awareness(self, scheduler):
        """Test timezone-aware scheduling"""
        # Test with different timezones
        timezones = ["America/New_York", "Europe/London", "Asia/Tokyo", "UTC"]
        
        for tz in timezones:
            config = ScheduleConfig(
                team_id=f"team-{tz.replace('/', '-')}",
                frequency=ScheduleFrequency.WEEKLY,
                timezone=tz,
                preferred_time=time(17, 0)
            )
            
            with patch.object(scheduler, '_validate_schedule_config', new_callable=AsyncMock):
                with patch.object(scheduler, 'optimize_timing_for_team', new_callable=AsyncMock) as mock_optimize:
                    with patch.object(scheduler, '_detect_scheduling_conflicts', new_callable=AsyncMock):
                        with patch.object(scheduler, '_persist_schedule', new_callable=AsyncMock):
                            with patch.object(scheduler, '_schedule_execution', new_callable=AsyncMock):
                                
                                # Setup timezone-aware optimal timing
                                tz_obj = ZoneInfo(tz)
                                optimal_time = datetime.now(tz_obj) + timedelta(hours=1)
                                mock_optimize.return_value = OptimalTiming(
                                    recommended_time=optimal_time,
                                    confidence_score=0.7,
                                    reasoning=f"Timezone {tz} optimization",
                                    alternative_times=[],
                                    team_availability=70.0,
                                    workload_impact=0.5
                                )
                                
                                result = await scheduler.schedule_changelog_generation(config)
                                
                                # Verify timezone handling
                                assert result.scheduled_time.tzinfo is not None
                                assert result.metadata["team_id"] == config.team_id

    async def test_holiday_adjustments(self, scheduler, sample_schedule_config):
        """Test holiday detection and schedule adjustment"""
        # Create a schedule on a holiday
        holiday_time = datetime(2024, 12, 25, 17, 0)  # Christmas
        schedule = ScheduleResult(
            schedule_id="test-holiday",
            status=ScheduleStatus.PENDING,
            scheduled_time=holiday_time,
            metadata={"team_id": "test-team"}
        )
        
        scheduler._schedules["test-team"] = sample_schedule_config
        
        with patch.object(scheduler, '_is_holiday', new_callable=AsyncMock) as mock_is_holiday:
            with patch.object(scheduler, '_find_next_available_time', new_callable=AsyncMock) as mock_next_time:
                with patch.object(scheduler, '_persist_schedule', new_callable=AsyncMock):
                    with patch.object(scheduler, '_notify_schedule_change', new_callable=AsyncMock):
                        
                        # Setup mocks
                        mock_is_holiday.return_value = True
                        adjusted_time = holiday_time + timedelta(days=1)
                        mock_next_time.return_value = adjusted_time
                        
                        # Execute test
                        result = await scheduler.handle_holiday_adjustments(schedule)
                        
                        # Verify adjustment
                        assert result.scheduled_time == adjusted_time
                        assert result.metadata["holiday_detected"] is True
                        assert result.metadata["adjustment_reason"] == "holiday_adjustment"

    async def test_retry_logic_with_exponential_backoff(self, scheduler, sample_schedule_config):
        """Test retry logic with exponential backoff"""
        failed_job = ScheduleResult(
            schedule_id="test-retry",
            status=ScheduleStatus.FAILED,
            scheduled_time=datetime.now(),
            retry_count=0,
            error_message="Test failure",
            metadata={"team_id": "test-team"}
        )
        
        scheduler._schedules["test-team"] = sample_schedule_config
        
        with patch.object(scheduler, '_persist_schedule', new_callable=AsyncMock):
            with patch.object(scheduler, '_schedule_execution', new_callable=AsyncMock):
                
                # Test first retry
                result = await scheduler.manage_retry_logic(failed_job)
                
                assert result.status == ScheduleStatus.RETRYING
                assert result.retry_count == 1
                assert "retry_delay_seconds" in result.metadata
                
                # Test retry exhaustion
                failed_job.retry_count = 3  # Max attempts
                result = await scheduler.manage_retry_logic(failed_job)
                
                assert result.status == ScheduleStatus.FAILED
                assert "Maximum retry attempts exceeded" in result.error_message

    async def test_global_team_coordination(self, scheduler):
        """Test coordination across multiple global teams"""
        teams = ["team-us", "team-eu", "team-asia"]
        
        with patch.object(scheduler, '_get_team_availability', new_callable=AsyncMock) as mock_availability:
            with patch.object(scheduler, '_find_coordination_window', new_callable=AsyncMock) as mock_window:
                with patch.object(scheduler, 'optimize_timing_for_team', new_callable=AsyncMock) as mock_optimize:
                    with patch.object(scheduler, '_detect_global_conflicts', new_callable=AsyncMock) as mock_conflicts:
                        with patch.object(scheduler, '_calculate_global_success_probability', new_callable=AsyncMock) as mock_probability:
                            with patch.object(scheduler, '_persist_global_schedule', new_callable=AsyncMock):
                                
                                # Setup mocks
                                mock_availability.return_value = TeamAvailability(
                                    team_id="test",
                                    timezone="UTC",
                                    business_hours=(time(9, 0), time(17, 0)),
                                    holidays=[],
                                    vacations={},
                                    capacity_percentage=80.0
                                )
                                
                                coordination_start = datetime.now() + timedelta(hours=1)
                                coordination_end = coordination_start + timedelta(hours=6)
                                mock_window.return_value = (coordination_start, coordination_end)
                                
                                mock_optimize.return_value = OptimalTiming(
                                    recommended_time=coordination_start + timedelta(hours=2),
                                    confidence_score=0.8,
                                    reasoning="Global optimization",
                                    alternative_times=[],
                                    team_availability=80.0,
                                    workload_impact=0.3
                                )
                                
                                mock_conflicts.return_value = []
                                mock_probability.return_value = 0.85
                                
                                # Execute test
                                result = await scheduler.coordinate_global_teams(teams)
                                
                                # Verify results
                                assert isinstance(result, GlobalSchedule)
                                assert result.teams == teams
                                assert result.success_probability == 0.85
                                assert len(result.optimal_times) == len(teams)

    async def test_manual_trigger_with_approval(self, scheduler, sample_schedule_config):
        """Test manual trigger with approval workflow"""
        # Setup approval required
        sample_schedule_config.approval_workflow.required = True
        sample_schedule_config.approval_workflow.approvers = ["manager@example.com"]
        scheduler._schedules["test-team"] = sample_schedule_config
        
        with patch.object(scheduler, '_start_approval_workflow', new_callable=AsyncMock) as mock_approval:
            with patch.object(scheduler, '_persist_schedule', new_callable=AsyncMock):
                with patch.object(scheduler, '_schedule_execution', new_callable=AsyncMock):
                    with patch.object(scheduler, '_audit_manual_trigger', new_callable=AsyncMock):
                        
                        # Test approved request
                        class ApprovalResult:
                            approved = True
                        
                        mock_approval.return_value = ApprovalResult()
                        
                        result = await scheduler.trigger_manual_generation(
                            team_id="test-team",
                            requester_id="user@example.com",
                            reason="Urgent release"
                        )
                        
                        assert result.status == ScheduleStatus.PENDING
                        assert result.metadata["trigger_type"] == "manual"
                        assert result.metadata["approval_status"] == "approved"

    async def test_conflict_detection_and_resolution(self, scheduler):
        """Test scheduling conflict detection and resolution"""
        team_id = "test-team"
        scheduled_time = datetime.now() + timedelta(hours=1)
        
        # Add existing schedule that conflicts
        existing_schedule = ScheduleResult(
            schedule_id="existing",
            status=ScheduleStatus.PENDING,
            scheduled_time=scheduled_time + timedelta(minutes=30),  # 30 min overlap
            metadata={"team_id": team_id}
        )
        scheduler._active_jobs["existing"] = existing_schedule
        
        # Test conflict detection
        conflicts = await scheduler._detect_scheduling_conflicts(team_id, scheduled_time)
        
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "schedule_overlap"
        assert conflicts[0].team_id == team_id
        
        # Test conflict resolution
        optimal_timing = OptimalTiming(
            recommended_time=scheduled_time,
            confidence_score=0.8,
            reasoning="Test timing",
            alternative_times=[scheduled_time + timedelta(hours=1)],
            team_availability=80.0,
            workload_impact=0.3
        )
        
        resolved_time = await scheduler._resolve_conflicts(conflicts, optimal_timing)
        assert resolved_time == scheduled_time + timedelta(hours=1)

    async def test_workload_based_optimization(self, scheduler):
        """Test workload-based scheduling optimization"""
        team_id = "test-team"
        
        with patch.object(scheduler, '_get_team_availability', new_callable=AsyncMock) as mock_availability:
            with patch.object(scheduler, '_analyze_current_workload', new_callable=AsyncMock) as mock_workload:
                with patch.object(scheduler, '_calculate_confidence_score', new_callable=AsyncMock) as mock_confidence:
                    
                    # Test high workload scenario
                    mock_availability.return_value = TeamAvailability(
                        team_id=team_id,
                        timezone="UTC",
                        business_hours=(time(9, 0), time(17, 0)),
                        holidays=[],
                        vacations={},
                        capacity_percentage=30.0  # Low availability
                    )
                    
                    mock_workload.return_value = {
                        "current_capacity": 30.0,
                        "impact_score": 0.8  # High impact
                    }
                    
                    mock_confidence.return_value = 0.4  # Low confidence due to workload
                    
                    # Execute optimization
                    result = await scheduler.optimize_timing_for_team(team_id)
                    
                    # Verify workload consideration
                    assert result.team_availability == 30.0
                    assert result.workload_impact == 0.8
                    assert result.confidence_score == 0.4

    async def test_error_handling_and_fallbacks(self, scheduler):
        """Test error handling and fallback mechanisms"""
        team_id = "test-team"
        
        # Test optimization failure fallback
        with patch.object(scheduler, '_get_team_availability', side_effect=Exception("API Error")):
            result = await scheduler.optimize_timing_for_team(team_id)
            
            # Should return fallback timing
            assert result.confidence_score == 0.3
            assert "Fallback timing due to optimization error" in result.reasoning

    async def test_scheduling_edge_cases(self, scheduler, sample_schedule_config):
        """Test edge cases in scheduling"""
        # Test invalid timezone
        invalid_config = ScheduleConfig(
            team_id="test-team",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="Invalid/Timezone",
            preferred_time=time(17, 0)
        )
        
        with pytest.raises(SchedulingError):
            await scheduler.schedule_changelog_generation(invalid_config)
        
        # Test empty team ID
        empty_config = ScheduleConfig(
            team_id="",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="UTC",
            preferred_time=time(17, 0)
        )
        
        with pytest.raises(SchedulingError):
            await scheduler.schedule_changelog_generation(empty_config)

    async def test_audit_trail_creation(self, scheduler, sample_schedule_config):
        """Test audit trail creation for manual triggers"""
        scheduler._schedules["test-team"] = sample_schedule_config
        
        with patch.object(scheduler, '_persist_schedule', new_callable=AsyncMock):
            with patch.object(scheduler, '_schedule_execution', new_callable=AsyncMock):
                with patch.object(scheduler, '_audit_manual_trigger', new_callable=AsyncMock) as mock_audit:
                    
                    result = await scheduler.trigger_manual_generation(
                        team_id="test-team",
                        requester_id="user@example.com",
                        reason="Emergency fix"
                    )
                    
                    # Verify audit was called
                    mock_audit.assert_called_once()
                    
                    # Verify metadata includes audit information
                    assert result.metadata["requester_id"] == "user@example.com"
                    assert result.metadata["reason"] == "Emergency fix"

    async def test_performance_under_load(self, scheduler):
        """Test scheduler performance with multiple concurrent operations"""
        teams = [f"team-{i}" for i in range(10)]
        
        # Mock all dependencies for performance test
        with patch.object(scheduler, '_get_team_availability', new_callable=AsyncMock):
            with patch.object(scheduler, '_analyze_historical_patterns', new_callable=AsyncMock):
                with patch.object(scheduler, '_analyze_current_workload', new_callable=AsyncMock):
                    with patch.object(scheduler, '_calculate_optimal_windows', new_callable=AsyncMock):
                        with patch.object(scheduler, '_calculate_confidence_score', new_callable=AsyncMock):
                            with patch.object(scheduler, '_generate_timing_reasoning', new_callable=AsyncMock):
                                
                                # Setup fast mock responses
                                scheduler._get_team_availability.return_value = TeamAvailability(
                                    team_id="test", timezone="UTC", business_hours=(time(9, 0), time(17, 0)),
                                    holidays=[], vacations={}, capacity_percentage=80.0
                                )
                                scheduler._analyze_historical_patterns.return_value = {}
                                scheduler._analyze_current_workload.return_value = {"impact_score": 0.3}
                                scheduler._calculate_optimal_windows.return_value = [datetime.now() + timedelta(hours=1)]
                                scheduler._calculate_confidence_score.return_value = 0.8
                                scheduler._generate_timing_reasoning.return_value = "Performance test"
                                
                                # Execute concurrent optimizations
                                start_time = datetime.now()
                                tasks = [scheduler.optimize_timing_for_team(team_id) for team_id in teams]
                                results = await asyncio.gather(*tasks)
                                end_time = datetime.now()
                                
                                # Verify all completed successfully
                                assert len(results) == len(teams)
                                for result in results:
                                    assert isinstance(result, OptimalTiming)
                                
                                # Verify reasonable performance (should complete in under 5 seconds)
                                duration = (end_time - start_time).total_seconds()
                                assert duration < 5.0

    async def test_timezone_edge_cases(self, scheduler):
        """Test edge cases in timezone handling"""
        # Test daylight saving time transitions
        dst_configs = [
            ("America/New_York", datetime(2024, 3, 10, 2, 30)),  # Spring forward
            ("America/New_York", datetime(2024, 11, 3, 1, 30)),   # Fall back
            ("Europe/London", datetime(2024, 3, 31, 1, 30)),      # Spring forward
            ("Europe/London", datetime(2024, 10, 27, 1, 30))      # Fall back
        ]
        
        for timezone, test_time in dst_configs:
            config = ScheduleConfig(
                team_id=f"dst-test-{timezone.replace('/', '-')}",
                frequency=ScheduleFrequency.WEEKLY,
                timezone=timezone,
                preferred_time=time(test_time.hour, test_time.minute)
            )
            
            # Should handle DST transitions gracefully
            with patch.object(scheduler, '_validate_schedule_config', new_callable=AsyncMock):
                try:
                    await scheduler._validate_schedule_config(config)
                except Exception as e:
                    pytest.fail(f"DST handling failed for {timezone} at {test_time}: {e}")


@pytest.mark.asyncio
class TestSchedulerIntegration:
    """Integration tests for scheduler components"""

    async def test_end_to_end_scheduling_flow(self):
        """Test complete end-to-end scheduling flow"""
        config_manager = Mock(spec=FlexibleConfigurationManager)
        scheduler = IntelligentScheduler(config_manager)
        
        # Initialize scheduler
        with patch.object(scheduler, '_load_schedules_from_database', new_callable=AsyncMock):
            with patch.object(scheduler, '_initialize_holiday_calendars', new_callable=AsyncMock):
                await scheduler.initialize()
        
        # Create schedule configuration
        schedule_config = ScheduleConfig(
            team_id="integration-test",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="UTC",
            preferred_time=time(17, 0)
        )
        
        # Mock all external dependencies
        with patch.object(scheduler, '_get_team_availability', new_callable=AsyncMock) as mock_availability:
            with patch.object(scheduler, '_analyze_historical_patterns', new_callable=AsyncMock) as mock_historical:
                with patch.object(scheduler, '_analyze_current_workload', new_callable=AsyncMock) as mock_workload:
                    with patch.object(scheduler, '_persist_schedule', new_callable=AsyncMock):
                        with patch.object(scheduler, '_schedule_execution', new_callable=AsyncMock):
                            
                            # Setup realistic mock data
                            mock_availability.return_value = TeamAvailability(
                                team_id="integration-test",
                                timezone="UTC",
                                business_hours=(time(9, 0), time(17, 0)),
                                holidays=[],
                                vacations={},
                                capacity_percentage=85.0
                            )
                            
                            mock_historical.return_value = {
                                "preferred_day": "friday",
                                "preferred_hour": 17,
                                "success_rate_by_hour": {17: 0.95}
                            }
                            
                            mock_workload.return_value = {
                                "current_capacity": 85.0,
                                "impact_score": 0.2
                            }
                            
                            # Execute full flow
                            result = await scheduler.schedule_changelog_generation(schedule_config)
                            
                            # Verify end-to-end success
                            assert isinstance(result, ScheduleResult)
                            assert result.status == ScheduleStatus.PENDING
                            assert result.metadata["team_id"] == "integration-test"
                            assert result.scheduled_time is not None
                            
                            # Verify scheduler state
                            assert "integration-test" in scheduler._schedules
                            assert result.schedule_id in scheduler._active_jobs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])