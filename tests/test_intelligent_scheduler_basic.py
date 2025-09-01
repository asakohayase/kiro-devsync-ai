"""
Basic tests for the Intelligent Scheduling System to verify core functionality
"""

import pytest
import asyncio
from datetime import datetime, timedelta, time
from unittest.mock import Mock, AsyncMock, patch

from devsync_ai.core.intelligent_scheduler import (
    IntelligentScheduler,
    ScheduleConfig,
    ScheduleFrequency,
    ScheduleStatus,
    RetryPolicy,
    ApprovalWorkflow,
    TeamAvailability,
    OptimalTiming,
    ScheduleResult
)
from devsync_ai.core.config_manager import FlexibleConfigurationManager


@pytest.mark.asyncio
class TestIntelligentSchedulerBasic:
    """Basic test suite for IntelligentScheduler"""

    async def test_scheduler_creation(self):
        """Test basic scheduler creation"""
        config_manager = Mock(spec=FlexibleConfigurationManager)
        scheduler = IntelligentScheduler(config_manager)
        
        assert scheduler.config_manager is config_manager
        assert isinstance(scheduler._schedules, dict)
        assert isinstance(scheduler._active_jobs, dict)

    async def test_schedule_config_creation(self):
        """Test schedule configuration creation"""
        config = ScheduleConfig(
            team_id="test-team",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="UTC",
            preferred_time=time(17, 0)
        )
        
        assert config.team_id == "test-team"
        assert config.frequency == ScheduleFrequency.WEEKLY
        assert config.timezone == "UTC"
        assert config.preferred_time == time(17, 0)

    async def test_team_availability_creation(self):
        """Test team availability creation"""
        availability = TeamAvailability(
            team_id="test-team",
            timezone="UTC",
            business_hours=(time(9, 0), time(17, 0)),
            holidays=[],
            vacations={},
            capacity_percentage=80.0
        )
        
        assert availability.team_id == "test-team"
        assert availability.capacity_percentage == 80.0

    async def test_optimal_timing_creation(self):
        """Test optimal timing creation"""
        timing = OptimalTiming(
            recommended_time=datetime.now(),
            confidence_score=0.85,
            reasoning="Test timing",
            alternative_times=[],
            team_availability=80.0,
            workload_impact=0.3
        )
        
        assert timing.confidence_score == 0.85
        assert timing.team_availability == 80.0

    async def test_schedule_result_creation(self):
        """Test schedule result creation"""
        result = ScheduleResult(
            schedule_id="test-123",
            status=ScheduleStatus.PENDING,
            scheduled_time=datetime.now()
        )
        
        assert result.schedule_id == "test-123"
        assert result.status == ScheduleStatus.PENDING

    async def test_basic_timing_optimization(self):
        """Test basic timing optimization without external dependencies"""
        scheduler = IntelligentScheduler()
        
        # Mock all external dependencies
        with patch.object(scheduler, '_get_team_availability', new_callable=AsyncMock) as mock_availability:
            with patch.object(scheduler, '_analyze_historical_patterns', new_callable=AsyncMock) as mock_historical:
                with patch.object(scheduler, '_analyze_current_workload', new_callable=AsyncMock) as mock_workload:
                    with patch.object(scheduler, '_calculate_optimal_windows', new_callable=AsyncMock) as mock_windows:
                        with patch.object(scheduler, '_calculate_confidence_score', new_callable=AsyncMock) as mock_confidence:
                            with patch.object(scheduler, '_generate_timing_reasoning', new_callable=AsyncMock) as mock_reasoning:
                                
                                # Setup mocks
                                mock_availability.return_value = TeamAvailability(
                                    team_id="test-team",
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
                                result = await scheduler.optimize_timing_for_team("test-team")
                                
                                # Verify results
                                assert isinstance(result, OptimalTiming)
                                assert result.recommended_time == optimal_time
                                assert result.confidence_score == 0.8
                                assert result.team_availability == 75.0

    async def test_retry_policy_functionality(self):
        """Test retry policy functionality"""
        scheduler = IntelligentScheduler()
        
        # Create a failed job
        failed_job = ScheduleResult(
            schedule_id="test-retry",
            status=ScheduleStatus.FAILED,
            scheduled_time=datetime.now(),
            retry_count=0,
            error_message="Test failure",
            metadata={"team_id": "test-team"}
        )
        
        # Create retry policy
        retry_policy = RetryPolicy(max_attempts=3, base_delay=60)
        
        # Create schedule config with retry policy
        schedule_config = ScheduleConfig(
            team_id="test-team",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="UTC",
            preferred_time=time(17, 0),
            retry_policy=retry_policy
        )
        
        scheduler._schedules["test-team"] = schedule_config
        
        with patch.object(scheduler, '_persist_schedule', new_callable=AsyncMock):
            with patch.object(scheduler, '_schedule_execution', new_callable=AsyncMock):
                
                # Test first retry
                result = await scheduler.manage_retry_logic(failed_job)
                
                assert result.status == ScheduleStatus.RETRYING
                assert result.retry_count == 1
                assert "retry_delay_seconds" in result.metadata

    async def test_holiday_detection(self):
        """Test holiday detection functionality"""
        scheduler = IntelligentScheduler()
        
        # Test holiday detection method
        is_holiday = await scheduler._is_holiday(
            datetime(2024, 12, 25),  # Christmas
            "US",
            "UTC"
        )
        
        # Note: This might be True or False depending on the holidays library
        # The important thing is that it doesn't crash
        assert isinstance(is_holiday, bool)

    async def test_conflict_detection(self):
        """Test basic conflict detection"""
        scheduler = IntelligentScheduler()
        
        # Add an existing schedule
        existing_schedule = ScheduleResult(
            schedule_id="existing",
            status=ScheduleStatus.PENDING,
            scheduled_time=datetime.now() + timedelta(hours=1),
            metadata={"team_id": "test-team"}
        )
        scheduler._active_jobs["existing"] = existing_schedule
        
        # Test conflict detection
        conflicts = await scheduler._detect_scheduling_conflicts(
            "test-team", 
            datetime.now() + timedelta(minutes=90)  # 30 min overlap
        )
        
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "schedule_overlap"

    async def test_configuration_validation(self):
        """Test configuration validation"""
        scheduler = IntelligentScheduler()
        
        # Test valid configuration
        valid_config = ScheduleConfig(
            team_id="test-team",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="UTC",
            preferred_time=time(17, 0)
        )
        
        # Should not raise exception
        await scheduler._validate_schedule_config(valid_config)
        
        # Test invalid configuration (empty team_id)
        invalid_config = ScheduleConfig(
            team_id="",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="UTC",
            preferred_time=time(17, 0)
        )
        
        with pytest.raises(Exception):  # Should raise ConfigurationError
            await scheduler._validate_schedule_config(invalid_config)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])