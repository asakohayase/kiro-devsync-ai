"""
Simplified tests for Hook Analytics Engine.

This module tests the core functionality of the JIRA Agent Hooks analytics engine
with minimal mocking and setup complexity.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from devsync_ai.analytics.hook_analytics_engine import (
    HookAnalyticsEngine,
    HookPerformanceMetrics,
    SystemHealthMetrics,
    Alert,
    AlertRule,
    AlertSeverity,
    HealthStatus,
    get_hook_analytics_engine,
    shutdown_hook_analytics_engine
)
from devsync_ai.core.agent_hooks import HookExecutionResult, HookStatus


class TestHookAnalyticsEngineCore:
    """Test core functionality of HookAnalyticsEngine."""
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self):
        """Test basic engine initialization."""
        engine = HookAnalyticsEngine()
        
        # Check initial state
        assert engine is not None
        assert len(engine.alert_rules) > 0
        assert engine._running is False
        
        # Initialize
        await engine.initialize()
        assert engine._running is True
        
        # Shutdown
        await engine.shutdown()
        assert engine._running is False
    
    @pytest.mark.asyncio
    async def test_default_alert_rules(self):
        """Test that default alert rules are created."""
        engine = HookAnalyticsEngine()
        
        # Check default rules exist
        assert "execution_time_warning" in engine.alert_rules
        assert "execution_time_critical" in engine.alert_rules
        assert "success_rate_warning" in engine.alert_rules
        assert "success_rate_critical" in engine.alert_rules
        assert "error_rate_warning" in engine.alert_rules
        
        # Check rule properties
        warning_rule = engine.alert_rules["execution_time_warning"]
        assert warning_rule.severity == AlertSeverity.WARNING
        assert warning_rule.enabled is True
        assert warning_rule.metric_type == "average_execution_time_ms"
    
    @pytest.mark.asyncio
    async def test_health_status_determination(self):
        """Test health status determination logic."""
        engine = HookAnalyticsEngine()
        
        # Test healthy status
        healthy_status = engine._determine_hook_health_status(
            success_rate=0.98,
            avg_execution_time=1000.0,
            executions_per_hour=10.0
        )
        assert healthy_status == HealthStatus.HEALTHY
        
        # Test warning status
        warning_status = engine._determine_hook_health_status(
            success_rate=0.92,  # Below warning threshold
            avg_execution_time=1000.0,
            executions_per_hour=10.0
        )
        assert warning_status == HealthStatus.WARNING
        
        # Test critical status
        critical_status = engine._determine_hook_health_status(
            success_rate=0.80,  # Below critical threshold
            avg_execution_time=1000.0,
            executions_per_hour=10.0
        )
        assert critical_status == HealthStatus.CRITICAL
        
        # Test critical status due to execution time
        critical_time_status = engine._determine_hook_health_status(
            success_rate=0.98,
            avg_execution_time=6000.0,  # Above critical threshold
            executions_per_hour=10.0
        )
        assert critical_time_status == HealthStatus.CRITICAL
    
    @pytest.mark.asyncio
    async def test_metric_value_extraction(self):
        """Test metric value extraction from performance metrics."""
        engine = HookAnalyticsEngine()
        
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
        assert engine._get_metric_value(metrics, "average_execution_time_ms") == 1500.0
        assert engine._get_metric_value(metrics, "success_rate") == 0.95
        assert engine._get_metric_value(metrics, "error_rate") == 0.05
        assert engine._get_metric_value(metrics, "executions_per_hour") == 10.0
        assert engine._get_metric_value(metrics, "total_executions") == 100.0
        assert engine._get_metric_value(metrics, "nonexistent_metric") is None
    
    @pytest.mark.asyncio
    async def test_threshold_checking(self):
        """Test threshold checking logic."""
        engine = HookAnalyticsEngine()
        
        # Test greater than
        assert engine._check_threshold(10.0, 5.0, "gt") is True
        assert engine._check_threshold(3.0, 5.0, "gt") is False
        
        # Test less than
        assert engine._check_threshold(3.0, 5.0, "lt") is True
        assert engine._check_threshold(7.0, 5.0, "lt") is False
        
        # Test greater than or equal
        assert engine._check_threshold(5.0, 5.0, "gte") is True
        assert engine._check_threshold(6.0, 5.0, "gte") is True
        assert engine._check_threshold(4.0, 5.0, "gte") is False
        
        # Test less than or equal
        assert engine._check_threshold(5.0, 5.0, "lte") is True
        assert engine._check_threshold(4.0, 5.0, "lte") is True
        assert engine._check_threshold(6.0, 5.0, "lte") is False
        
        # Test equal
        assert engine._check_threshold(5.0, 5.0, "eq") is True
        assert engine._check_threshold(4.0, 5.0, "eq") is False
    
    @pytest.mark.asyncio
    async def test_alert_management(self):
        """Test alert acknowledgment and resolution."""
        engine = HookAnalyticsEngine()
        
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
        
        engine.active_alerts["test_alert"] = alert
        
        # Test acknowledgment
        result = await engine.acknowledge_alert("test_alert")
        assert result is True
        assert engine.active_alerts["test_alert"].acknowledged is True
        
        # Test resolution
        result = await engine.resolve_alert("test_alert")
        assert result is True
        assert engine.active_alerts["test_alert"].resolved_at is not None
        
        # Test non-existent alert
        result = await engine.acknowledge_alert("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_alert_filtering(self):
        """Test alert filtering by severity and team."""
        engine = HookAnalyticsEngine()
        
        # Create test alerts
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
        
        engine.active_alerts["alert_1"] = critical_alert
        engine.active_alerts["alert_2"] = warning_alert
        
        # Test severity filtering
        critical_alerts = await engine.get_active_alerts(severity_filter=AlertSeverity.CRITICAL)
        assert len(critical_alerts) == 1
        assert critical_alerts[0].severity == AlertSeverity.CRITICAL
        
        # Test team filtering
        team_alpha_alerts = await engine.get_active_alerts(team_filter="team_alpha")
        assert len(team_alpha_alerts) == 1
        assert team_alpha_alerts[0].team_id == "team_alpha"
        
        # Test combined filtering
        combined_alerts = await engine.get_active_alerts(
            severity_filter=AlertSeverity.WARNING,
            team_filter="team_beta"
        )
        assert len(combined_alerts) == 1
        assert combined_alerts[0].severity == AlertSeverity.WARNING
        assert combined_alerts[0].team_id == "team_beta"
    
    @pytest.mark.asyncio
    async def test_performance_cache_update(self):
        """Test performance cache updates."""
        engine = HookAnalyticsEngine()
        
        # Create test execution result
        execution_result = HookExecutionResult(
            hook_id="test_hook",
            execution_id="exec_1",
            hook_type="test_type",
            event_id="event_1",
            status=HookStatus.SUCCESS,
            execution_time_ms=1500.0,
            notification_sent=True,
            metadata={'team_id': 'test_team'}
        )
        
        # Update cache
        await engine._update_performance_cache(execution_result)
        
        # Check cache
        assert "test_hook" in engine.performance_cache
        cached_metrics = engine.performance_cache["test_hook"]
        assert cached_metrics.total_executions == 1
        assert cached_metrics.successful_executions == 1
        assert cached_metrics.success_rate == 1.0
        assert cached_metrics.average_execution_time_ms == 1500.0
        
        # Add another execution
        execution_result2 = HookExecutionResult(
            hook_id="test_hook",
            execution_id="exec_2",
            hook_type="test_type",
            event_id="event_2",
            status=HookStatus.FAILED,
            execution_time_ms=2000.0,
            notification_sent=False,
            metadata={'team_id': 'test_team'}
        )
        
        await engine._update_performance_cache(execution_result2)
        
        # Check updated cache
        cached_metrics = engine.performance_cache["test_hook"]
        assert cached_metrics.total_executions == 2
        assert cached_metrics.successful_executions == 1
        assert cached_metrics.failed_executions == 1
        assert cached_metrics.success_rate == 0.5
        assert cached_metrics.average_execution_time_ms == 1750.0  # (1500 + 2000) / 2


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


if __name__ == "__main__":
    pytest.main([__file__])