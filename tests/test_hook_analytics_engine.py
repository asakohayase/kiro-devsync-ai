"""
Tests for Hook Analytics Engine.

This module tests the comprehensive analytics, monitoring, and reporting
capabilities of the JIRA Agent Hooks analytics engine.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

from devsync_ai.analytics.hook_analytics_engine import (
    HookAnalyticsEngine,
    HookPerformanceMetrics,
    SystemHealthMetrics,
    Alert,
    AlertRule,
    AlertSeverity,
    HealthStatus,
    PerformanceTrend,
    get_hook_analytics_engine,
    shutdown_hook_analytics_engine
)
from devsync_ai.core.agent_hooks import HookExecutionResult
from devsync_ai.analytics.analytics_data_manager import AnalyticsRecord


class TestHookAnalyticsEngine:
    """Test cases for HookAnalyticsEngine."""
    
    @pytest.fixture
    def analytics_engine(self):
        """Create analytics engine for testing."""
        return HookAnalyticsEngine()
    
    @pytest.fixture
    def sample_execution_result(self):
        """Create sample hook execution result."""
        from devsync_ai.core.agent_hooks import HookStatus
        return HookExecutionResult(
            hook_id="test_hook_1",
            execution_id="exec_123",
            hook_type="status_change",
            event_id="event_123",
            status=HookStatus.SUCCESS,
            execution_time_ms=1500.0,
            notification_sent=True,
            notification_result=None,
            errors=[],
            metadata={
                'team_id': 'team_alpha',
                'event_type': 'jira:issue_updated'
            }
        )
    
    @pytest.fixture
    def sample_analytics_records(self):
        """Create sample analytics records."""
        base_time = datetime.now(timezone.utc)
        records = []
        
        for i in range(10):
            from devsync_ai.core.agent_hooks import HookStatus
            record = AnalyticsRecord(
                id=f"record_{i}",
                timestamp=base_time - timedelta(minutes=i * 10),
                record_type="hook_execution",
                team_id="team_alpha",
                data={
                    'hook_id': 'test_hook_1',
                    'execution_id': f'exec_{i}',
                    'success': i < 8,  # 80% success rate
                    'execution_time_ms': 1000.0 + (i * 100),
                    'notification_sent': True,
                    'hook_type': 'status_change',
                    'event_type': 'jira:issue_updated'
                },
                metadata={
                    'errors': [] if i < 8 else ['Test error'],
                    'additional_metadata': {}
                }
            )
            records.append(record)
        
        return records
    
    @pytest.mark.asyncio
    async def test_initialization(self, analytics_engine):
        """Test analytics engine initialization."""
        await analytics_engine.initialize()
        assert analytics_engine is not None
        assert len(analytics_engine.alert_rules) > 0
        assert analytics_engine._running is True
        
        # Check default alert rules
        assert "execution_time_warning" in analytics_engine.alert_rules
        assert "success_rate_critical" in analytics_engine.alert_rules
        
        await analytics_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_record_hook_execution(self, analytics_engine, sample_execution_result):
        """Test recording hook execution."""
        await analytics_engine.initialize()
        
        with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.store_record.return_value = "record_id_123"
            
            result = await analytics_engine.record_hook_execution(sample_execution_result)
            
            assert result is True
            mock_manager.store_record.assert_called_once()
            
            # Check that performance cache was updated
            assert sample_execution_result.hook_id in analytics_engine.performance_cache
            cached_metrics = analytics_engine.performance_cache[sample_execution_result.hook_id]
            assert cached_metrics.total_executions == 1
            assert cached_metrics.successful_executions == 1
            assert cached_metrics.success_rate == 1.0
        
        await analytics_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_record_failed_execution(self, analytics_engine):
        """Test recording failed hook execution."""
        from devsync_ai.core.agent_hooks import HookStatus
        failed_result = HookExecutionResult(
            hook_id="test_hook_2",
            execution_id="exec_failed",
            hook_type="assignment",
            event_id="event_failed",
            status=HookStatus.FAILED,
            execution_time_ms=5000.0,
            notification_sent=False,
            notification_result=None,
            errors=["Connection timeout", "Retry failed"],
            metadata={
                'team_id': 'team_beta',
                'event_type': 'jira:issue_assigned'
            }
        )
        
        await analytics_engine.initialize()
        
        with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.store_record.return_value = "record_id_456"
            
            result = await analytics_engine.record_hook_execution(failed_result)
            
            assert result is True
            
            # Check performance cache
            cached_metrics = analytics_engine.performance_cache[failed_result.hook_id]
            assert cached_metrics.total_executions == 1
            assert cached_metrics.successful_executions == 0
            assert cached_metrics.failed_executions == 1
            assert cached_metrics.success_rate == 0.0
            assert cached_metrics.error_rate == 1.0
        
        await analytics_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_hook_performance_metrics(self, analytics_engine, sample_analytics_records):
        """Test getting hook performance metrics."""
        await analytics_engine.initialize()
        
        with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.query_records.return_value = sample_analytics_records
            
            metrics = await analytics_engine.get_hook_performance_metrics("test_hook_1")
            
            assert metrics is not None
            assert metrics.hook_id == "test_hook_1"
            assert metrics.total_executions == 10
            assert metrics.successful_executions == 8
            assert metrics.failed_executions == 2
            assert metrics.success_rate == 0.8
            assert metrics.error_rate == 0.2
            assert metrics.average_execution_time_ms == 1450.0  # Average of 1000 + i*100
            assert metrics.min_execution_time_ms == 1000.0
            assert metrics.max_execution_time_ms == 1900.0
        
        await analytics_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_hook_performance_metrics_no_data(self, analytics_engine):
        """Test getting metrics when no data exists."""
        await analytics_engine.initialize()
        
        with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.query_records.return_value = []
            
            metrics = await analytics_engine.get_hook_performance_metrics("nonexistent_hook")
            
            assert metrics is None
        
        await analytics_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_system_health_metrics(self, analytics_engine):
        """Test getting system health metrics."""
        with patch('devsync_ai.analytics.hook_analytics_engine.get_hook_registry_manager') as mock_get_registry:
            with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_get_manager:
                # Mock registry manager
                mock_registry = AsyncMock()
                mock_get_registry.return_value = mock_registry
                mock_registry.get_all_hook_statuses.return_value = [
                    {
                        'hook_id': 'hook_1',
                        'statistics': {
                            'last_execution': (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
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
                mock_manager = AsyncMock()
                mock_get_manager.return_value = mock_manager
                mock_manager.query_records.return_value = [
                    AnalyticsRecord(
                        id="r1",
                        timestamp=datetime.now(timezone.utc),
                        record_type="hook_execution",
                        team_id="team1",
                        data={'success': True, 'execution_time_ms': 1000},
                        metadata={}
                    ),
                    AnalyticsRecord(
                        id="r2",
                        timestamp=datetime.now(timezone.utc),
                        record_type="hook_execution",
                        team_id="team1",
                        data={'success': False, 'execution_time_ms': 2000},
                        metadata={}
                    )
                ]
                
                metrics = await analytics_engine.get_system_health_metrics()
                
                assert metrics is not None
                assert metrics.total_hooks == 2
                assert metrics.active_hooks == 1  # Only one executed in last hour
                assert metrics.total_executions == 2
                assert metrics.overall_success_rate == 0.5
                assert metrics.average_execution_time_ms == 1500.0
                assert metrics.error_count_last_hour == 1
    
    @pytest.mark.asyncio
    async def test_generate_performance_report(self, analytics_engine, sample_analytics_records):
        """Test generating performance report."""
        with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.query_records.return_value = sample_analytics_records
            
            report = await analytics_engine.generate_performance_report()
            
            assert "error" not in report
            assert "summary" in report
            assert "hook_metrics" in report
            assert "performance_trends" in report
            assert "top_performers" in report
            assert "underperformers" in report
            
            # Check summary
            summary = report["summary"]
            assert summary["total_hooks"] == 1
            assert summary["total_executions"] == 10
            assert summary["successful_executions"] == 8
            assert summary["overall_success_rate"] == 0.8
    
    @pytest.mark.asyncio
    async def test_alert_triggering(self, analytics_engine):
        """Test alert triggering based on performance thresholds."""
        # Create execution result that should trigger alerts
        slow_failed_result = HookExecutionResult(
            hook_id="slow_hook",
            execution_id="exec_slow",
            success=False,
            execution_time_ms=6000.0,  # Above critical threshold
            notification_sent=False,
            notification_result=None,
            errors=["Timeout error"],
            metadata={
                'hook_type': 'comment',
                'team_id': 'team_gamma',
                'event_type': 'jira:issue_commented'
            }
        )
        
        with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.store_record.return_value = "record_id"
            
            # Record multiple failed executions to trigger success rate alert
            for i in range(5):
                await analytics_engine.record_hook_execution(slow_failed_result)
            
            # Check that alerts were triggered
            active_alerts = await analytics_engine.get_active_alerts()
            assert len(active_alerts) > 0
            
            # Should have both execution time and success rate alerts
            alert_types = [alert.rule_id for alert in active_alerts]
            assert "execution_time_critical" in alert_types
            assert "success_rate_critical" in alert_types
    
    @pytest.mark.asyncio
    async def test_alert_filtering(self, analytics_engine):
        """Test alert filtering by severity and team."""
        # Create some test alerts
        critical_alert = Alert(
            alert_id="alert_1",
            rule_id="test_rule",
            hook_id="hook_1",
            team_id="team_alpha",
            severity=AlertSeverity.CRITICAL,
            title="Critical Alert",
            description="Test critical alert",
            metric_value=0.5,
            threshold_value=0.8,
            triggered_at=datetime.now(timezone.utc)
        )
        
        warning_alert = Alert(
            alert_id="alert_2",
            rule_id="test_rule",
            hook_id="hook_2",
            team_id="team_beta",
            severity=AlertSeverity.WARNING,
            title="Warning Alert",
            description="Test warning alert",
            metric_value=0.9,
            threshold_value=0.95,
            triggered_at=datetime.now(timezone.utc)
        )
        
        analytics_engine.active_alerts["alert_1"] = critical_alert
        analytics_engine.active_alerts["alert_2"] = warning_alert
        
        # Test severity filtering
        critical_alerts = await analytics_engine.get_active_alerts(severity_filter=AlertSeverity.CRITICAL)
        assert len(critical_alerts) == 1
        assert critical_alerts[0].severity == AlertSeverity.CRITICAL
        
        # Test team filtering
        team_alpha_alerts = await analytics_engine.get_active_alerts(team_filter="team_alpha")
        assert len(team_alpha_alerts) == 1
        assert team_alpha_alerts[0].team_id == "team_alpha"
        
        # Test combined filtering
        combined_alerts = await analytics_engine.get_active_alerts(
            severity_filter=AlertSeverity.WARNING,
            team_filter="team_beta"
        )
        assert len(combined_alerts) == 1
        assert combined_alerts[0].severity == AlertSeverity.WARNING
        assert combined_alerts[0].team_id == "team_beta"
    
    @pytest.mark.asyncio
    async def test_alert_acknowledgment_and_resolution(self, analytics_engine):
        """Test alert acknowledgment and resolution."""
        # Create test alert
        alert = Alert(
            alert_id="test_alert",
            rule_id="test_rule",
            hook_id="hook_1",
            team_id="team_alpha",
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            description="Test alert for acknowledgment",
            metric_value=0.9,
            threshold_value=0.95,
            triggered_at=datetime.now(timezone.utc)
        )
        
        analytics_engine.active_alerts["test_alert"] = alert
        
        # Test acknowledgment
        result = await analytics_engine.acknowledge_alert("test_alert")
        assert result is True
        assert analytics_engine.active_alerts["test_alert"].acknowledged is True
        
        # Test resolution
        result = await analytics_engine.resolve_alert("test_alert")
        assert result is True
        assert analytics_engine.active_alerts["test_alert"].resolved_at is not None
        
        # Test non-existent alert
        result = await analytics_engine.acknowledge_alert("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_health_status_determination(self, analytics_engine):
        """Test health status determination logic."""
        # Test healthy status
        healthy_status = analytics_engine._determine_hook_health_status(
            success_rate=0.98,
            avg_execution_time=1000.0,
            executions_per_hour=10.0
        )
        assert healthy_status == HealthStatus.HEALTHY
        
        # Test warning status
        warning_status = analytics_engine._determine_hook_health_status(
            success_rate=0.92,  # Below warning threshold
            avg_execution_time=1000.0,
            executions_per_hour=10.0
        )
        assert warning_status == HealthStatus.WARNING
        
        # Test critical status
        critical_status = analytics_engine._determine_hook_health_status(
            success_rate=0.80,  # Below critical threshold
            avg_execution_time=1000.0,
            executions_per_hour=10.0
        )
        assert critical_status == HealthStatus.CRITICAL
        
        # Test critical status due to execution time
        critical_time_status = analytics_engine._determine_hook_health_status(
            success_rate=0.98,
            avg_execution_time=6000.0,  # Above critical threshold
            executions_per_hour=10.0
        )
        assert critical_time_status == HealthStatus.CRITICAL
    
    @pytest.mark.asyncio
    async def test_performance_cache_updates(self, analytics_engine):
        """Test performance cache updates with multiple executions."""
        hook_id = "cache_test_hook"
        
        with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.store_record.return_value = "record_id"
            
            # Record multiple executions
            execution_times = [1000, 1500, 2000, 1200, 1800]
            successes = [True, True, False, True, True]
            
            for i, (exec_time, success) in enumerate(zip(execution_times, successes)):
                result = HookExecutionResult(
                    hook_id=hook_id,
                    execution_id=f"exec_{i}",
                    success=success,
                    execution_time_ms=exec_time,
                    notification_sent=success,
                    notification_result=None,
                    errors=[] if success else ["Test error"],
                    metadata={
                        'hook_type': 'test',
                        'team_id': 'test_team',
                        'event_type': 'test_event'
                    }
                )
                await analytics_engine.record_hook_execution(result)
            
            # Check cached metrics
            cached_metrics = analytics_engine.performance_cache[hook_id]
            assert cached_metrics.total_executions == 5
            assert cached_metrics.successful_executions == 4
            assert cached_metrics.failed_executions == 1
            assert cached_metrics.success_rate == 0.8
            assert cached_metrics.error_rate == 0.2
            assert cached_metrics.average_execution_time_ms == 1500.0  # Average of execution times
            assert cached_metrics.min_execution_time_ms == 1000.0
            assert cached_metrics.max_execution_time_ms == 2000.0
    
    @pytest.mark.asyncio
    async def test_metric_value_extraction(self, analytics_engine):
        """Test metric value extraction from performance metrics."""
        metrics = HookPerformanceMetrics(
            hook_id="test_hook",
            hook_type="test",
            team_id="test_team",
            total_executions=100,
            successful_executions=95,
            failed_executions=5,
            average_execution_time_ms=1500.0,
            min_execution_time_ms=800.0,
            max_execution_time_ms=3000.0,
            success_rate=0.95,
            error_rate=0.05,
            last_execution=datetime.now(timezone.utc),
            executions_per_hour=10.0,
            health_status=HealthStatus.HEALTHY
        )
        
        # Test various metric extractions
        assert analytics_engine._get_metric_value(metrics, "average_execution_time_ms") == 1500.0
        assert analytics_engine._get_metric_value(metrics, "success_rate") == 0.95
        assert analytics_engine._get_metric_value(metrics, "error_rate") == 0.05
        assert analytics_engine._get_metric_value(metrics, "executions_per_hour") == 10.0
        assert analytics_engine._get_metric_value(metrics, "total_executions") == 100.0
        assert analytics_engine._get_metric_value(metrics, "nonexistent_metric") is None
    
    @pytest.mark.asyncio
    async def test_threshold_checking(self, analytics_engine):
        """Test threshold checking logic."""
        # Test greater than
        assert analytics_engine._check_threshold(10.0, 5.0, "gt") is True
        assert analytics_engine._check_threshold(3.0, 5.0, "gt") is False
        
        # Test less than
        assert analytics_engine._check_threshold(3.0, 5.0, "lt") is True
        assert analytics_engine._check_threshold(7.0, 5.0, "lt") is False
        
        # Test greater than or equal
        assert analytics_engine._check_threshold(5.0, 5.0, "gte") is True
        assert analytics_engine._check_threshold(6.0, 5.0, "gte") is True
        assert analytics_engine._check_threshold(4.0, 5.0, "gte") is False
        
        # Test less than or equal
        assert analytics_engine._check_threshold(5.0, 5.0, "lte") is True
        assert analytics_engine._check_threshold(4.0, 5.0, "lte") is True
        assert analytics_engine._check_threshold(6.0, 5.0, "lte") is False
        
        # Test equal
        assert analytics_engine._check_threshold(5.0, 5.0, "eq") is True
        assert analytics_engine._check_threshold(4.0, 5.0, "eq") is False
    
    @pytest.mark.asyncio
    async def test_error_handling(self, analytics_engine):
        """Test error handling in various scenarios."""
        # Test recording execution with data manager error
        with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.store_record.side_effect = Exception("Database error")
            
            result = HookExecutionResult(
                hook_id="error_test_hook",
                execution_id="exec_error",
                success=True,
                execution_time_ms=1000.0,
                notification_sent=True,
                notification_result=None,
                errors=[],
                metadata={'hook_type': 'test', 'team_id': 'test_team'}
            )
            
            success = await analytics_engine.record_hook_execution(result)
            assert success is False  # Should handle error gracefully
        
        # Test getting metrics with data manager error
        with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager
            mock_manager.query_records.side_effect = Exception("Query error")
            
            metrics = await analytics_engine.get_hook_performance_metrics("test_hook")
            assert metrics is None  # Should handle error gracefully


class TestGlobalAnalyticsEngine:
    """Test global analytics engine management."""
    
    @pytest.mark.asyncio
    async def test_get_global_engine(self):
        """Test getting global analytics engine instance."""
        # Clean up any existing instance
        await shutdown_hook_analytics_engine()
        
        engine1 = await get_hook_analytics_engine()
        engine2 = await get_hook_analytics_engine()
        
        # Should return the same instance
        assert engine1 is engine2
        assert engine1._running is True
        
        # Clean up
        await shutdown_hook_analytics_engine()
    
    @pytest.mark.asyncio
    async def test_shutdown_global_engine(self):
        """Test shutting down global analytics engine."""
        engine = await get_hook_analytics_engine()
        assert engine._running is True
        
        await shutdown_hook_analytics_engine()
        
        # Engine should be shut down
        assert engine._running is False
        
        # Getting engine again should create new instance
        new_engine = await get_hook_analytics_engine()
        assert new_engine is not engine
        
        # Clean up
        await shutdown_hook_analytics_engine()


class TestPerformanceTrends:
    """Test performance trend analysis."""
    
    @pytest.mark.asyncio
    async def test_trend_calculation(self):
        """Test performance trend calculation."""
        engine = HookAnalyticsEngine()
        
        # Create sample records spanning two time periods
        base_time = datetime.now(timezone.utc)
        time_range = (base_time - timedelta(hours=2), base_time)
        mid_point = time_range[0] + (time_range[1] - time_range[0]) / 2
        
        records = []
        
        # First half - lower performance
        for i in range(5):
            record = AnalyticsRecord(
                id=f"record_first_{i}",
                timestamp=time_range[0] + timedelta(minutes=i * 10),
                record_type="hook_execution",
                team_id="test_team",
                data={
                    'success': i < 3,  # 60% success rate
                    'execution_time_ms': 2000.0 + (i * 100)
                },
                metadata={}
            )
            records.append(record)
        
        # Second half - better performance
        for i in range(5):
            record = AnalyticsRecord(
                id=f"record_second_{i}",
                timestamp=mid_point + timedelta(minutes=i * 10),
                record_type="hook_execution",
                team_id="test_team",
                data={
                    'success': i < 4,  # 80% success rate
                    'execution_time_ms': 1500.0 + (i * 50)
                },
                metadata={}
            )
            records.append(record)
        
        trends = await engine._calculate_performance_trends(records, time_range)
        
        assert len(trends) == 2
        
        # Check success rate trend
        success_trend = next(t for t in trends if t.metric_name == "success_rate")
        assert success_trend.trend_direction == "improving"
        assert success_trend.current_value == 0.8
        assert success_trend.previous_value == 0.6
        
        # Check execution time trend
        time_trend = next(t for t in trends if t.metric_name == "execution_time")
        assert time_trend.trend_direction == "improving"  # Lower execution time is better
        assert time_trend.current_value < time_trend.previous_value


if __name__ == "__main__":
    pytest.main([__file__])