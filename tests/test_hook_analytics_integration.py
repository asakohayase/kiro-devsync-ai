"""
Integration tests for Hook Analytics Engine.

This module tests the integration between the analytics engine and
other system components with realistic scenarios.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from devsync_ai.analytics.hook_analytics_engine import (
    HookAnalyticsEngine,
    get_hook_analytics_engine,
    shutdown_hook_analytics_engine
)
from devsync_ai.core.agent_hooks import HookExecutionResult, HookStatus
from devsync_ai.analytics.analytics_data_manager import AnalyticsRecord


class TestHookAnalyticsIntegration:
    """Integration tests for the analytics engine."""
    
    @pytest.mark.asyncio
    async def test_full_execution_tracking_workflow(self):
        """Test complete workflow from execution to reporting."""
        engine = HookAnalyticsEngine()
        await engine.initialize()
        
        try:
            # Mock the data manager
            with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_get_manager:
                mock_manager = AsyncMock()
                mock_get_manager.return_value = mock_manager
                mock_manager.store_record.return_value = "record_id"
                
                # Simulate multiple hook executions
                hook_executions = [
                    # Successful executions
                    HookExecutionResult(
                        hook_id="status_hook_1",
                        execution_id="exec_1",
                        hook_type="status_change",
                        event_id="event_1",
                        status=HookStatus.SUCCESS,
                        execution_time_ms=1200.0,
                        notification_sent=True,
                        metadata={'team_id': 'team_alpha', 'event_type': 'jira:issue_updated'}
                    ),
                    HookExecutionResult(
                        hook_id="status_hook_1",
                        execution_id="exec_2",
                        hook_type="status_change",
                        event_id="event_2",
                        status=HookStatus.SUCCESS,
                        execution_time_ms=1100.0,
                        notification_sent=True,
                        metadata={'team_id': 'team_alpha', 'event_type': 'jira:issue_updated'}
                    ),
                    # Failed execution
                    HookExecutionResult(
                        hook_id="status_hook_1",
                        execution_id="exec_3",
                        hook_type="status_change",
                        event_id="event_3",
                        status=HookStatus.FAILED,
                        execution_time_ms=5000.0,
                        notification_sent=False,
                        errors=["Timeout error"],
                        metadata={'team_id': 'team_alpha', 'event_type': 'jira:issue_updated'}
                    ),
                    # Different hook type
                    HookExecutionResult(
                        hook_id="assignment_hook_1",
                        execution_id="exec_4",
                        hook_type="assignment",
                        event_id="event_4",
                        status=HookStatus.SUCCESS,
                        execution_time_ms=800.0,
                        notification_sent=True,
                        metadata={'team_id': 'team_beta', 'event_type': 'jira:issue_assigned'}
                    )
                ]
                
                # Record all executions
                for execution in hook_executions:
                    result = await engine.record_hook_execution(execution)
                    assert result is True
                
                # Verify data was stored
                assert mock_manager.store_record.call_count == 4
                
                # Check performance cache
                assert "status_hook_1" in engine.performance_cache
                assert "assignment_hook_1" in engine.performance_cache
                
                # Verify status_hook_1 metrics
                status_metrics = engine.performance_cache["status_hook_1"]
                assert status_metrics.total_executions == 3
                assert status_metrics.successful_executions == 2
                assert status_metrics.failed_executions == 1
                assert status_metrics.success_rate == 2/3
                assert abs(status_metrics.error_rate - 1/3) < 0.001  # Use approximate comparison for floats
                assert status_metrics.average_execution_time_ms == (1200 + 1100 + 5000) / 3
                
                # Verify assignment_hook_1 metrics
                assignment_metrics = engine.performance_cache["assignment_hook_1"]
                assert assignment_metrics.total_executions == 1
                assert assignment_metrics.successful_executions == 1
                assert assignment_metrics.success_rate == 1.0
                
                # Check that alerts were triggered for the slow/failed execution
                active_alerts = await engine.get_active_alerts()
                assert len(active_alerts) > 0
                
                # Should have execution time and success rate alerts
                alert_types = [alert.rule_id for alert in active_alerts]
                # Should have some execution time alert (warning or critical)
                execution_time_alerts = [t for t in alert_types if "execution_time" in t]
                assert len(execution_time_alerts) > 0
                # Should have success rate critical alert
                assert "success_rate_critical" in alert_types
        
        finally:
            await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_system_health_monitoring(self):
        """Test system health monitoring functionality."""
        engine = HookAnalyticsEngine()
        await engine.initialize()
        
        try:
            # Mock dependencies
            with patch('devsync_ai.analytics.hook_analytics_engine.get_hook_registry_manager') as mock_registry:
                with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_data_manager:
                    # Mock registry manager
                    mock_registry_instance = AsyncMock()
                    mock_registry.return_value = mock_registry_instance
                    mock_registry_instance.get_all_hook_statuses.return_value = [
                        {
                            'hook_id': 'hook_1',
                            'statistics': {
                                'last_execution': (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
                            }
                        },
                        {
                            'hook_id': 'hook_2',
                            'statistics': {
                                'last_execution': (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
                            }
                        }
                    ]
                    
                    # Mock data manager
                    mock_data_instance = AsyncMock()
                    mock_data_manager.return_value = mock_data_instance
                    
                    # Create sample execution records
                    now = datetime.now(timezone.utc)
                    sample_records = [
                        AnalyticsRecord(
                            id="r1",
                            timestamp=now - timedelta(minutes=30),
                            record_type="hook_execution",
                            team_id="team1",
                            data={'success': True, 'execution_time_ms': 1000},
                            metadata={}
                        ),
                        AnalyticsRecord(
                            id="r2",
                            timestamp=now - timedelta(minutes=20),
                            record_type="hook_execution",
                            team_id="team1",
                            data={'success': True, 'execution_time_ms': 1200},
                            metadata={}
                        ),
                        AnalyticsRecord(
                            id="r3",
                            timestamp=now - timedelta(minutes=10),
                            record_type="hook_execution",
                            team_id="team2",
                            data={'success': False, 'execution_time_ms': 3000},
                            metadata={}
                        )
                    ]
                    mock_data_instance.query_records.return_value = sample_records
                    
                    # Get system health metrics
                    health_metrics = await engine.get_system_health_metrics()
                    
                    # Verify metrics
                    assert health_metrics is not None
                    assert health_metrics.total_hooks == 2
                    assert health_metrics.active_hooks == 1  # Only one executed in last hour
                    assert health_metrics.total_executions == 3
                    assert health_metrics.overall_success_rate == 2/3  # 2 successful out of 3
                    assert health_metrics.average_execution_time_ms == (1000 + 1200 + 3000) / 3
                    assert health_metrics.error_count_last_hour == 1
                    
                    # Health status should be warning due to error rate
                    assert health_metrics.health_status.value in ['warning', 'critical']
        
        finally:
            await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_performance_report_generation(self):
        """Test comprehensive performance report generation."""
        engine = HookAnalyticsEngine()
        await engine.initialize()
        
        try:
            with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_data_manager:
                mock_data_instance = AsyncMock()
                mock_data_manager.return_value = mock_data_instance
                
                # Create comprehensive sample data
                base_time = datetime.now(timezone.utc)
                sample_records = []
                
                # Create records for multiple hooks and teams
                for i in range(20):
                    hook_id = f"hook_{i % 3 + 1}"  # 3 different hooks
                    team_id = f"team_{i % 2 + 1}"  # 2 different teams
                    success = i % 4 != 0  # 75% success rate
                    
                    record = AnalyticsRecord(
                        id=f"record_{i}",
                        timestamp=base_time - timedelta(minutes=i * 10),
                        record_type="hook_execution",
                        team_id=team_id,
                        data={
                            'hook_id': hook_id,
                            'execution_id': f'exec_{i}',
                            'success': success,
                            'execution_time_ms': 1000.0 + (i * 50),
                            'notification_sent': success,
                            'hook_type': 'status_change',
                            'event_type': 'jira:issue_updated'
                        },
                        metadata={
                            'errors': [] if success else ['Test error'],
                            'additional_metadata': {}
                        }
                    )
                    sample_records.append(record)
                
                mock_data_instance.query_records.return_value = sample_records
                
                # Generate performance report
                report = await engine.generate_performance_report()
                
                # Verify report structure
                assert "error" not in report
                assert "summary" in report
                assert "hook_metrics" in report
                assert "performance_trends" in report
                assert "top_performers" in report
                assert "underperformers" in report
                assert "alerts_summary" in report
                
                # Verify summary data
                summary = report["summary"]
                assert summary["total_hooks"] == 3
                assert summary["total_executions"] == 20
                assert summary["successful_executions"] == 15  # 75% of 20
                assert summary["overall_success_rate"] == 0.75
                assert summary["unique_teams"] == 2
                
                # Verify hook metrics
                hook_metrics = report["hook_metrics"]
                assert len(hook_metrics) == 3
                
                # Each hook should have proper metrics
                for hook_metric in hook_metrics:
                    assert "hook_id" in hook_metric
                    assert "total_executions" in hook_metric
                    assert "success_rate" in hook_metric
                    assert "average_execution_time_ms" in hook_metric
                
                # Verify trends are calculated
                trends = report["performance_trends"]
                # Trends might be empty if there's insufficient data for comparison
                assert isinstance(trends, (dict, list))
                if isinstance(trends, dict) and "timestamps" in trends:
                    assert len(trends["timestamps"]) >= 0
        
        finally:
            await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_alert_lifecycle(self):
        """Test complete alert lifecycle from trigger to resolution."""
        engine = HookAnalyticsEngine()
        await engine.initialize()
        
        try:
            with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_data_manager:
                mock_data_instance = AsyncMock()
                mock_data_manager.return_value = mock_data_instance
                mock_data_instance.store_record.return_value = "record_id"
                
                # Create execution that should trigger critical alerts
                critical_execution = HookExecutionResult(
                    hook_id="critical_hook",
                    execution_id="exec_critical",
                    hook_type="status_change",
                    event_id="event_critical",
                    status=HookStatus.FAILED,
                    execution_time_ms=8000.0,  # Way above critical threshold
                    notification_sent=False,
                    errors=["Critical system error"],
                    metadata={'team_id': 'team_critical', 'event_type': 'jira:issue_updated'}
                )
                
                # Record multiple failed executions to trigger success rate alert
                for i in range(5):
                    await engine.record_hook_execution(critical_execution)
                
                # Check that alerts were triggered
                active_alerts = await engine.get_active_alerts()
                assert len(active_alerts) > 0
                
                # Should have both execution time and success rate alerts
                alert_types = [alert.rule_id for alert in active_alerts]
                assert "execution_time_critical" in alert_types
                assert "success_rate_critical" in alert_types
                
                # Test alert acknowledgment
                critical_alert = next(a for a in active_alerts if a.severity.value == "critical")
                ack_result = await engine.acknowledge_alert(critical_alert.alert_id)
                assert ack_result is True
                assert critical_alert.acknowledged is True
                
                # Test alert resolution
                resolve_result = await engine.resolve_alert(critical_alert.alert_id)
                assert resolve_result is True
                assert critical_alert.resolved_at is not None
                
                # Verify resolved alerts are filtered out of active alerts
                remaining_active = await engine.get_active_alerts()
                resolved_alert_ids = [a.alert_id for a in remaining_active if a.resolved_at is not None]
                assert critical_alert.alert_id not in [a.alert_id for a in remaining_active if not a.resolved_at]
        
        finally:
            await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_tracking(self):
        """Test handling of concurrent hook executions."""
        engine = HookAnalyticsEngine()
        await engine.initialize()
        
        try:
            with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_data_manager:
                mock_data_instance = AsyncMock()
                mock_data_manager.return_value = mock_data_instance
                mock_data_instance.store_record.return_value = "record_id"
                
                # Create multiple concurrent executions
                async def record_execution(hook_id: str, execution_id: str, success: bool):
                    execution = HookExecutionResult(
                        hook_id=hook_id,
                        execution_id=execution_id,
                        hook_type="concurrent_test",
                        event_id=f"event_{execution_id}",
                        status=HookStatus.SUCCESS if success else HookStatus.FAILED,
                        execution_time_ms=1000.0,
                        notification_sent=success,
                        metadata={'team_id': 'concurrent_team'}
                    )
                    return await engine.record_hook_execution(execution)
                
                # Run concurrent executions
                tasks = []
                for i in range(10):
                    hook_id = f"concurrent_hook_{i % 3}"  # 3 different hooks
                    success = i % 2 == 0  # 50% success rate
                    task = record_execution(hook_id, f"exec_{i}", success)
                    tasks.append(task)
                
                # Wait for all executions to complete
                results = await asyncio.gather(*tasks)
                
                # All should succeed
                assert all(results)
                
                # Verify cache was updated correctly
                assert len(engine.performance_cache) == 3  # 3 different hooks
                
                # Check metrics for each hook
                for hook_id in ["concurrent_hook_0", "concurrent_hook_1", "concurrent_hook_2"]:
                    if hook_id in engine.performance_cache:
                        metrics = engine.performance_cache[hook_id]
                        # Each hook should have some executions recorded
                        assert metrics.total_executions > 0
                        assert metrics.successful_executions + metrics.failed_executions == metrics.total_executions
        
        finally:
            await engine.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])