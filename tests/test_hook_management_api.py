"""
Tests for Hook Management API endpoints.

This module provides comprehensive tests for the hook management API,
including configuration, status monitoring, health checks, execution history,
and analytics endpoints.
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Set required environment variables for testing
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("JIRA_SERVER_URL", "https://test.atlassian.net")
os.environ.setdefault("JIRA_USERNAME", "test@example.com")
os.environ.setdefault("JIRA_API_TOKEN", "test-token")
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test-token")
os.environ.setdefault("GITHUB_TOKEN", "ghp_test-token")

from devsync_ai.api.hook_management_routes import router
from devsync_ai.core.hook_configuration_manager import TeamConfiguration
from devsync_ai.analytics.hook_analytics_engine import (
    HookPerformanceMetrics,
    SystemHealthMetrics,
    Alert,
    AlertSeverity,
    HealthStatus
)


# Test fixtures
@pytest.fixture
def app():
    """Create FastAPI app with hook management routes."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_config_manager():
    """Mock configuration manager."""
    manager = AsyncMock()
    
    # Mock team configuration
    team_config = TeamConfiguration(
        team_id="test-team",
        team_name="Test Team",
        enabled=True,
        version="1.0.0",
        default_channels={"general": "#test-general"},
        notification_preferences={"urgency_threshold": "high"},
        business_hours={"start": "09:00", "end": "17:00"},
        escalation_rules=[],
        rules=[
            {
                "id": "rule-1",
                "name": "Status Change Rule",
                "enabled": True,
                "hook_types": ["StatusChangeHook"],
                "conditions": [{"field": "priority", "operator": "in", "values": ["High", "Critical"]}]
            }
        ],
        last_updated=datetime.now(timezone.utc),
        metadata={}
    )
    
    manager.get_all_team_configurations.return_value = [team_config]
    manager.load_team_configuration.return_value = team_config
    
    return manager


@pytest.fixture
def mock_analytics_engine():
    """Mock analytics engine."""
    engine = AsyncMock()
    
    # Mock performance metrics
    performance_metrics = HookPerformanceMetrics(
        hook_id="test-hook-1",
        hook_type="StatusChangeHook",
        team_id="test-team",
        total_executions=100,
        successful_executions=95,
        failed_executions=5,
        average_execution_time_ms=1500.0,
        min_execution_time_ms=500.0,
        max_execution_time_ms=3000.0,
        success_rate=0.95,
        error_rate=0.05,
        last_execution=datetime.now(timezone.utc),
        executions_per_hour=10.0,
        health_status=HealthStatus.HEALTHY
    )
    
    # Mock system health metrics
    system_health = SystemHealthMetrics(
        timestamp=datetime.now(timezone.utc),
        total_hooks=5,
        active_hooks=4,
        total_executions=500,
        overall_success_rate=0.96,
        average_execution_time_ms=1200.0,
        executions_per_minute=2.5,
        error_count_last_hour=3,
        health_status=HealthStatus.HEALTHY,
        alerts_count=1
    )
    
    # Mock alert
    alert = Alert(
        alert_id="alert-1",
        rule_id="execution_time_warning",
        hook_id="test-hook-1",
        team_id="test-team",
        severity=AlertSeverity.WARNING,
        title="High Execution Time",
        description="Hook execution time exceeds warning threshold",
        metric_value=2500.0,
        threshold_value=2000.0,
        triggered_at=datetime.now(timezone.utc),
        resolved_at=None,
        acknowledged=False,
        metadata={}
    )
    
    engine.get_hook_performance_metrics.return_value = performance_metrics
    engine.get_system_health_metrics.return_value = system_health
    engine.get_active_alerts.return_value = [alert]
    engine.acknowledge_alert.return_value = True
    engine.resolve_alert.return_value = True
    engine.generate_performance_report.return_value = {
        "report_generated_at": datetime.now(timezone.utc),
        "time_range": {
            "start": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            "end": datetime.now(timezone.utc).isoformat()
        },
        "filters": {},
        "summary": {
            "total_hooks": 5,
            "total_executions": 500,
            "successful_executions": 480,
            "overall_success_rate": 0.96,
            "average_execution_time_ms": 1200.0,
            "unique_teams": 3,
            "unique_hook_types": 4
        },
        "hook_metrics": [],
        "performance_trends": [],
        "top_performers": [],
        "underperformers": [],
        "alerts_summary": {
            "total_alerts": 1,
            "critical_alerts": 0,
            "warning_alerts": 1
        }
    }
    
    return engine


@pytest.fixture
def mock_data_manager():
    """Mock data manager."""
    manager = AsyncMock()
    
    # Mock execution data
    execution = {
        "execution_id": "exec-1",
        "hook_id": "test-hook-1",
        "hook_type": "StatusChangeHook",
        "team_id": "test-team",
        "event_type": "jira:issue_updated",
        "status": "SUCCESS",
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
        "execution_time_ms": 1500.0,
        "notification_sent": True,
        "success": True,
        "errors": [],
        "metadata": {"event_id": "event-1"}
    }
    
    manager.get_hook_executions.return_value = [execution]
    manager.get_hook_execution.return_value = execution
    
    return manager


@pytest.fixture
def mock_registry_manager():
    """Mock hook registry manager."""
    manager = AsyncMock()
    
    hook_status = {
        "hook_id": "test-hook-1",
        "hook_type": "StatusChangeHook",
        "team_id": "test-team",
        "status": "active",
        "enabled": True,
        "last_execution": datetime.now(timezone.utc),
        "metadata": {}
    }
    
    manager.get_all_hook_statuses.return_value = [hook_status]
    manager.get_hook_status.return_value = hook_status
    
    return manager


class TestHookStatusEndpoints:
    """Test hook status and health endpoints."""
    
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    @patch('devsync_ai.api.hook_management_routes.get_hook_registry_manager')
    def test_get_all_hook_statuses(self, mock_get_registry, mock_get_analytics, client, mock_analytics_engine, mock_registry_manager):
        """Test getting all hook statuses."""
        # Configure the async mock to return the mock instances
        async def mock_registry():
            return mock_registry_manager
        
        async def mock_analytics():
            return mock_analytics_engine
            
        mock_get_registry.side_effect = mock_registry
        mock_get_analytics.side_effect = mock_analytics
        
        response = client.get("/api/v1/hooks/status")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["hook_id"] == "test-hook-1"
        assert data[0]["hook_type"] == "StatusChangeHook"
        assert data[0]["success_rate"] == 0.95
        assert data[0]["health_status"] == "healthy"
    
    @patch('devsync_ai.api.hook_management_routes.get_hook_registry_manager')
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_get_hook_status_with_filters(self, mock_get_analytics, mock_get_registry, client, mock_analytics_engine, mock_registry_manager):
        """Test getting hook statuses with filters."""
        mock_get_analytics.return_value = mock_analytics_engine
        mock_get_registry.return_value = mock_registry_manager
        
        response = client.get("/api/v1/hooks/status?team_filter=test-team&hook_type_filter=StatusChangeHook")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["team_id"] == "test-team"
        assert data[0]["hook_type"] == "StatusChangeHook"
    
    @patch('devsync_ai.api.hook_management_routes.get_hook_registry_manager')
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_get_specific_hook_status(self, mock_get_analytics, mock_get_registry, client, mock_analytics_engine, mock_registry_manager):
        """Test getting status of a specific hook."""
        mock_get_analytics.return_value = mock_analytics_engine
        mock_get_registry.return_value = mock_registry_manager
        
        response = client.get("/api/v1/hooks/status/test-hook-1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["hook_id"] == "test-hook-1"
        assert data["total_executions"] == 100
        assert data["success_rate"] == 0.95
    
    @patch('devsync_ai.api.hook_management_routes.get_hook_registry_manager')
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_get_hook_status_not_found(self, mock_get_analytics, mock_get_registry, client, mock_analytics_engine, mock_registry_manager):
        """Test getting status of non-existent hook."""
        mock_get_analytics.return_value = mock_analytics_engine
        mock_registry_manager.get_hook_status.return_value = None
        mock_get_registry.return_value = mock_registry_manager
        
        response = client.get("/api/v1/hooks/status/non-existent-hook")
        
        assert response.status_code == 404
        assert "Hook not found" in response.json()["detail"]
    
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_get_system_health(self, mock_get_analytics, client, mock_analytics_engine):
        """Test getting system health."""
        mock_get_analytics.return_value = mock_analytics_engine
        
        response = client.get("/api/v1/hooks/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "healthy"
        assert data["total_hooks"] == 5
        assert data["active_hooks"] == 4
        assert data["overall_success_rate"] == 0.96
        assert "details" in data
        assert "health_score" in data["details"]


class TestHookExecutionEndpoints:
    """Test hook execution history endpoints."""
    
    @patch('devsync_ai.api.hook_management_routes.get_data_manager')
    def test_get_hook_executions(self, mock_get_data, client, mock_data_manager):
        """Test getting hook executions."""
        mock_get_data.return_value = mock_data_manager
        
        response = client.get("/api/v1/hooks/executions")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["execution_id"] == "exec-1"
        assert data[0]["hook_id"] == "test-hook-1"
        assert data[0]["status"] == "SUCCESS"
        assert data[0]["success"] is True
    
    @patch('devsync_ai.api.hook_management_routes.get_data_manager')
    def test_get_hook_executions_with_filters(self, mock_get_data, client, mock_data_manager):
        """Test getting hook executions with filters."""
        mock_get_data.return_value = mock_data_manager
        
        response = client.get("/api/v1/hooks/executions?hook_id=test-hook-1&team_id=test-team&status=SUCCESS&limit=10")
        
        assert response.status_code == 200
        mock_data_manager.get_hook_executions.assert_called_once()
        call_args = mock_data_manager.get_hook_executions.call_args
        assert call_args.kwargs["hook_id"] == "test-hook-1"
        assert call_args.kwargs["team_id"] == "test-team"
        assert call_args.kwargs["status"] == "SUCCESS"
        assert call_args.kwargs["limit"] == 10
    
    @patch('devsync_ai.api.hook_management_routes.get_data_manager')
    def test_get_specific_hook_execution(self, mock_get_data, client, mock_data_manager):
        """Test getting a specific hook execution."""
        mock_get_data.return_value = mock_data_manager
        
        response = client.get("/api/v1/hooks/executions/exec-1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == "exec-1"
        assert data["hook_type"] == "StatusChangeHook"
        assert data["execution_time_ms"] == 1500.0
    
    @patch('devsync_ai.api.hook_management_routes.get_data_manager')
    def test_get_hook_execution_not_found(self, mock_get_data, client, mock_data_manager):
        """Test getting non-existent hook execution."""
        mock_data_manager.get_hook_execution.return_value = None
        mock_get_data.return_value = mock_data_manager
        
        response = client.get("/api/v1/hooks/executions/non-existent")
        
        assert response.status_code == 404
        assert "Execution not found" in response.json()["detail"]


class TestAnalyticsEndpoints:
    """Test analytics and performance endpoints."""
    
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_get_performance_report(self, mock_get_analytics, client, mock_analytics_engine):
        """Test getting performance report."""
        mock_get_analytics.return_value = mock_analytics_engine
        
        response = client.get("/api/v1/hooks/analytics/performance")
        
        assert response.status_code == 200
        data = response.json()
        assert "report_generated_at" in data
        assert "summary" in data
        assert data["summary"]["total_hooks"] == 5
        assert data["summary"]["overall_success_rate"] == 0.96
    
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_get_performance_report_with_filters(self, mock_get_analytics, client, mock_analytics_engine):
        """Test getting performance report with filters."""
        mock_get_analytics.return_value = mock_analytics_engine
        
        response = client.get("/api/v1/hooks/analytics/performance?team_filter=test-team&hook_type_filter=StatusChangeHook")
        
        assert response.status_code == 200
        mock_analytics_engine.generate_performance_report.assert_called_once()
        call_args = mock_analytics_engine.generate_performance_report.call_args
        assert call_args.kwargs["team_filter"] == "test-team"
        assert call_args.kwargs["hook_type_filter"] == "StatusChangeHook"
    
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_get_hook_metrics(self, mock_get_analytics, client, mock_analytics_engine):
        """Test getting hook metrics."""
        mock_get_analytics.return_value = mock_analytics_engine
        
        response = client.get("/api/v1/hooks/analytics/metrics/test-hook-1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["hook_id"] == "test-hook-1"
        assert "metrics" in data
        assert data["metrics"]["total_executions"] == 100
        assert data["metrics"]["success_rate"] == 0.95
    
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_get_hook_metrics_not_found(self, mock_get_analytics, client, mock_analytics_engine):
        """Test getting metrics for non-existent hook."""
        mock_analytics_engine.get_hook_performance_metrics.return_value = None
        mock_get_analytics.return_value = mock_analytics_engine
        
        response = client.get("/api/v1/hooks/analytics/metrics/non-existent")
        
        assert response.status_code == 404
        assert "Hook metrics not found" in response.json()["detail"]


class TestAlertEndpoints:
    """Test alert management endpoints."""
    
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_get_alerts(self, mock_get_analytics, client, mock_analytics_engine):
        """Test getting alerts."""
        mock_get_analytics.return_value = mock_analytics_engine
        
        response = client.get("/api/v1/hooks/alerts")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["alert_id"] == "alert-1"
        assert data[0]["severity"] == "warning"
        assert data[0]["acknowledged"] is False
    
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_get_alerts_with_filters(self, mock_get_analytics, client, mock_analytics_engine):
        """Test getting alerts with filters."""
        mock_get_analytics.return_value = mock_analytics_engine
        
        response = client.get("/api/v1/hooks/alerts?severity=warning&team_filter=test-team")
        
        assert response.status_code == 200
        mock_analytics_engine.get_active_alerts.assert_called_once()
        call_args = mock_analytics_engine.get_active_alerts.call_args
        assert call_args.kwargs["severity_filter"] == AlertSeverity.WARNING
        assert call_args.kwargs["team_filter"] == "test-team"
    
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_acknowledge_alert(self, mock_get_analytics, client, mock_analytics_engine):
        """Test acknowledging an alert."""
        mock_get_analytics.return_value = mock_analytics_engine
        
        response = client.post("/api/v1/hooks/alerts/alert-1/acknowledge")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "acknowledged" in data["message"]
        mock_analytics_engine.acknowledge_alert.assert_called_once_with("alert-1")
    
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_resolve_alert(self, mock_get_analytics, client, mock_analytics_engine):
        """Test resolving an alert."""
        mock_get_analytics.return_value = mock_analytics_engine
        
        response = client.post("/api/v1/hooks/alerts/alert-1/resolve")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "resolved" in data["message"]
        mock_analytics_engine.resolve_alert.assert_called_once_with("alert-1")
    
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_acknowledge_alert_not_found(self, mock_get_analytics, client, mock_analytics_engine):
        """Test acknowledging non-existent alert."""
        mock_analytics_engine.acknowledge_alert.return_value = False
        mock_get_analytics.return_value = mock_analytics_engine
        
        response = client.post("/api/v1/hooks/alerts/non-existent/acknowledge")
        
        assert response.status_code == 404
        assert "Alert not found" in response.json()["detail"]


class TestConfigurationEndpoints:
    """Test configuration management endpoints."""
    
    @patch('devsync_ai.api.hook_management_routes.get_config_manager')
    def test_list_teams(self, mock_get_config, client, mock_config_manager):
        """Test listing teams."""
        mock_get_config.return_value = mock_config_manager
        
        response = client.get("/api/v1/hooks/config/teams")
        
        assert response.status_code == 200
        data = response.json()
        assert data == ["test-team"]
    
    @patch('devsync_ai.api.hook_management_routes.get_config_manager')
    def test_get_team_configuration(self, mock_get_config, client, mock_config_manager):
        """Test getting team configuration."""
        mock_get_config.return_value = mock_config_manager
        
        response = client.get("/api/v1/hooks/config/teams/test-team")
        
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == "test-team"
        assert data["team_name"] == "Test Team"
        assert data["enabled"] is True
        assert len(data["rules"]) == 1


class TestUtilityEndpoints:
    """Test utility endpoints."""
    
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    @patch('devsync_ai.api.hook_management_routes.get_config_manager')
    def test_get_hook_statistics(self, mock_get_config, mock_get_analytics, client, mock_config_manager, mock_analytics_engine):
        """Test getting hook statistics."""
        mock_get_config.return_value = mock_config_manager
        mock_get_analytics.return_value = mock_analytics_engine
        
        response = client.get("/api/v1/hooks/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "system_health" in data
        assert "configuration" in data
        assert "performance" in data
        assert data["system_health"]["total_hooks"] == 5
        assert data["configuration"]["total_teams"] == 1


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @patch('devsync_ai.api.hook_management_routes.get_analytics_engine')
    def test_analytics_engine_error(self, mock_get_analytics, client):
        """Test handling analytics engine errors."""
        mock_engine = AsyncMock()
        mock_engine.get_system_health_metrics.side_effect = Exception("Database error")
        mock_get_analytics.return_value = mock_engine
        
        response = client.get("/api/v1/hooks/health")
        
        assert response.status_code == 500
        assert "Failed to retrieve system health" in response.json()["detail"]
    
    @patch('devsync_ai.api.hook_management_routes.get_data_manager')
    def test_data_manager_error(self, mock_get_data, client):
        """Test handling data manager errors."""
        mock_manager = AsyncMock()
        mock_manager.get_hook_executions.side_effect = Exception("Database error")
        mock_get_data.return_value = mock_manager
        
        response = client.get("/api/v1/hooks/executions")
        
        assert response.status_code == 500
        assert "Failed to retrieve hook executions" in response.json()["detail"]
    
    def test_invalid_alert_severity(self, client):
        """Test handling invalid alert severity."""
        response = client.get("/api/v1/hooks/alerts?severity=invalid")
        
        assert response.status_code == 400
        assert "Invalid severity" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])