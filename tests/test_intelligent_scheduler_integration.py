"""
Integration tests for the Intelligent Scheduling System
"""

import pytest
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
class TestIntelligentSchedulerIntegration:
    """Integration test suite for IntelligentScheduler"""

    async def test_full_scheduling_workflow(self):
        """Test complete scheduling workflow from config to execution"""
        # Create scheduler
        config_manager = Mock(spec=FlexibleConfigurationManager)
        scheduler = IntelligentScheduler(config_manager)
        
        # Create schedule configuration
        schedule_config = ScheduleConfig(
            team_id="integration-test",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="UTC",
            preferred_time=time(17, 0),
            retry_policy=RetryPolicy(max_attempts=3, base_delay=60),
            approval_workflow=ApprovalWorkflow(required=False)
        )
        
        # Mock all external dependencies for integration test
        with patch.object(scheduler, '_validate_schedule_config', new_callable=AsyncMock) as mock_validate:
            with patch.object(scheduler, 'optimize_timing_for_team', new_callable=AsyncMock) as mock_optimize:
                with patch.object(scheduler, '_detect_scheduling_conflicts', new_callable=AsyncMock) as mock_conflicts:
                    with patch.object(scheduler, '_persist_schedule', new_callable=AsyncMock) as mock_persist:
                        with patch.object(scheduler, '_schedule_execution', new_callable=AsyncMock) as mock_execute:
                            
                            # Setup mocks for successful flow
                            mock_validate.return_value = None  # No validation errors
                            
                            optimal_timing = OptimalTiming(
                                recommended_time=datetime.now() + timedelta(hours=1),
                                confidence_score=0.85,
                                reasoning="Optimal timing based on team patterns",
                                alternative_times=[],
                                team_availability=80.0,
                                workload_impact=0.3
                            )
                            mock_optimize.return_value = optimal_timing
                            mock_conflicts.return_value = []  # No conflicts
                            
                            # Execute the full workflow
                            result = await scheduler.schedule_changelog_generation(schedule_config)
                            
                            # Verify the workflow executed correctly
                            assert isinstance(result, ScheduleResult)
                            assert result.status == ScheduleStatus.PENDING
                            assert result.metadata["team_id"] == "integration-test"
                            assert result.metadata["confidence_score"] == 0.85
                            
                            # Verify all steps were called
                            mock_validate.assert_called_once()
                            mock_optimize.assert_called_once_with("integration-test")
                            mock_conflicts.assert_called_once()
                            mock_persist.assert_called_once()
                            mock_execute.assert_called_once()

    async def test_manual_trigger_workflow(self):
        """Test manual trigger workflow with approval"""
        scheduler = IntelligentScheduler()
        
        # Setup team configuration
        schedule_config = ScheduleConfig(
            team_id="manual-test",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="UTC",
            preferred_time=time(17, 0),
            approval_workflow=ApprovalWorkflow(
                required=True,
                approvers=["manager@example.com"],
                timeout_minutes=60
            )
        )
        scheduler._schedules["manual-test"] = schedule_config
        
        with patch.object(scheduler, '_start_approval_workflow', new_callable=AsyncMock) as mock_approval:
            with patch.object(scheduler, '_persist_schedule', new_callable=AsyncMock):
                with patch.object(scheduler, '_schedule_execution', new_callable=AsyncMock):
                    with patch.object(scheduler, '_audit_manual_trigger', new_callable=AsyncMock):
                        
                        # Mock approval success
                        class ApprovalResult:
                            approved = True
                        mock_approval.return_value = ApprovalResult()
                        
                        # Execute manual trigger
                        result = await scheduler.trigger_manual_generation(
                            team_id="manual-test",
                            requester_id="user@example.com",
                            reason="Urgent release"
                        )
                        
                        # Verify manual trigger succeeded
                        assert result.status == ScheduleStatus.PENDING
                        assert result.metadata["trigger_type"] == "manual"
                        assert result.metadata["requester_id"] == "user@example.com"
                        assert result.metadata["reason"] == "Urgent release"
                        assert result.metadata["approval_status"] == "approved"

    async def test_retry_workflow_with_failure_recovery(self):
        """Test retry workflow with eventual success"""
        scheduler = IntelligentScheduler()
        
        # Create failed job
        failed_job = ScheduleResult(
            schedule_id="retry-test",
            status=ScheduleStatus.FAILED,
            scheduled_time=datetime.now(),
            retry_count=0,
            error_message="Temporary failure",
            metadata={"team_id": "retry-team"}
        )
        
        # Setup retry policy
        retry_policy = RetryPolicy(max_attempts=3, base_delay=60)
        schedule_config = ScheduleConfig(
            team_id="retry-team",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="UTC",
            preferred_time=time(17, 0),
            retry_policy=retry_policy
        )
        scheduler._schedules["retry-team"] = schedule_config
        
        with patch.object(scheduler, '_persist_schedule', new_callable=AsyncMock):
            with patch.object(scheduler, '_schedule_execution', new_callable=AsyncMock):
                
                # Test first retry
                result1 = await scheduler.manage_retry_logic(failed_job)
                assert result1.status == ScheduleStatus.RETRYING
                assert result1.retry_count == 1
                
                # Test second retry
                result2 = await scheduler.manage_retry_logic(result1)
                assert result2.status == ScheduleStatus.RETRYING
                assert result2.retry_count == 2
                
                # Test final retry (should still retry)
                result3 = await scheduler.manage_retry_logic(result2)
                assert result3.status == ScheduleStatus.RETRYING
                assert result3.retry_count == 3
                
                # Test exhaustion (should fail permanently)
                result4 = await scheduler.manage_retry_logic(result3)
                assert result4.status == ScheduleStatus.FAILED
                assert "Maximum retry attempts exceeded" in result4.error_message

    async def test_global_team_coordination_workflow(self):
        """Test global team coordination workflow"""
        scheduler = IntelligentScheduler()
        
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
                                
                                # Execute global coordination
                                result = await scheduler.coordinate_global_teams(teams)
                                
                                # Verify global coordination
                                assert result.teams == teams
                                assert result.success_probability == 0.85
                                assert len(result.optimal_times) == len(teams)
                                assert result.coordination_window == (coordination_start, coordination_end)

    async def test_holiday_adjustment_workflow(self):
        """Test holiday adjustment workflow"""
        scheduler = IntelligentScheduler()
        
        # Create schedule on a holiday
        holiday_schedule = ScheduleResult(
            schedule_id="holiday-test",
            status=ScheduleStatus.PENDING,
            scheduled_time=datetime(2024, 12, 25, 17, 0),  # Christmas
            metadata={"team_id": "holiday-team"}
        )
        
        # Setup team config
        schedule_config = ScheduleConfig(
            team_id="holiday-team",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="UTC",
            preferred_time=time(17, 0),
            holiday_calendar="US"
        )
        scheduler._schedules["holiday-team"] = schedule_config
        
        with patch.object(scheduler, '_is_holiday', new_callable=AsyncMock) as mock_is_holiday:
            with patch.object(scheduler, '_find_next_available_time', new_callable=AsyncMock) as mock_next_time:
                with patch.object(scheduler, '_persist_schedule', new_callable=AsyncMock):
                    with patch.object(scheduler, '_notify_schedule_change', new_callable=AsyncMock):
                        
                        # Mock holiday detection
                        mock_is_holiday.return_value = True
                        adjusted_time = datetime(2024, 12, 26, 17, 0)  # Next day
                        mock_next_time.return_value = adjusted_time
                        
                        # Execute holiday adjustment
                        result = await scheduler.handle_holiday_adjustments(holiday_schedule)
                        
                        # Verify adjustment
                        assert result.scheduled_time == adjusted_time
                        assert result.metadata["holiday_detected"] is True
                        assert result.metadata["adjustment_reason"] == "holiday_adjustment"

    async def test_error_handling_and_fallbacks(self):
        """Test error handling and fallback mechanisms"""
        scheduler = IntelligentScheduler()
        
        # Test optimization failure fallback
        with patch.object(scheduler, '_get_team_availability', side_effect=Exception("API Error")):
            result = await scheduler.optimize_timing_for_team("error-team")
            
            # Should return fallback timing
            assert result.confidence_score == 0.3
            assert "Fallback timing due to optimization error" in result.reasoning
            assert isinstance(result.recommended_time, datetime)

    async def test_timezone_handling_workflow(self):
        """Test timezone handling across different regions"""
        scheduler = IntelligentScheduler()
        
        # Test different timezone configurations
        timezones = ["America/New_York", "Europe/London", "Asia/Tokyo"]
        
        for tz in timezones:
            config = ScheduleConfig(
                team_id=f"tz-test-{tz.replace('/', '-')}",
                frequency=ScheduleFrequency.WEEKLY,
                timezone=tz,
                preferred_time=time(17, 0)
            )
            
            # Validate timezone configuration
            try:
                await scheduler._validate_schedule_config(config)
                # If no exception, timezone is valid
                assert True
            except Exception as e:
                pytest.fail(f"Timezone validation failed for {tz}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])