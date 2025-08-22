"""
Tests for monitoring dashboard and health check endpoints.

This module tests the comprehensive monitoring system including
health checks, diagnostics, and dashboard functionality.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from devsync_ai.api.health_check_routes import router
from devsync_ai.analytics.system_health_monitor import SystemHealthMonitor, ComponentStatus, DiagnosticLevel
from devsync_ai.analytics.monitoring_dashboard import MonitoringDashboard
from devsync_ai.analytics.diagnostic_tools import SystemDiagnosticTools, DiagnosticCategory


# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestHealthCheckEndpoints:
    """Test health check API endpoints."""
    
    @pytest.fixture
    def mock_health_monitor(self):
        """Mock health monitor."""
        monitor = Mock(spec=SystemHealthMonitor)
        monitor.get_system_health_status = AsyncMock(return_value={
            "overall_status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "last_health_check": datetime.now(timezone.utc).isoformat(),
            "components": {
                "hook_registry": {
                    "status": "operational",
                    "response_time_ms": 150.0,
                    "last_check": datetime.now(timezone.utc).isoformat(),
                    "error_message": None,
                    "metadata": {"total_hooks": 5}
                },
                "database": {
                    "status": "operational",
                    "response_time_ms": 200.0,
                    "last_check": datetime.now(timezone.utc).isoformat(),
                    "error_message": None,
                    "metadata": {"query_time_ms": 180.0}
                }
            },
            "system_resources": {
                "cpu_usage": 45.2,
                "memory_usage": 62.1,
                "memory_available_gb": 4.2,
                "disk_usage": 35.8,
                "disk_free_gb": 120.5
            },
            "active_alerts": 0,
            "monitoring_active": True
        })
        monitor.get_active_alerts = AsyncMock(return_value=[])
        monitor.get_component_health_history = AsyncMock(return_value=[])
        monitor.start_monitoring = AsyncMock()
        monitor.stop_monitoring = AsyncMock()
        return monitor
    
    @pytest.fixture
    def mock_registry_manager(self):
        """Mock hook registry manager."""
        manager = Mock()
        manager.get_all_hook_statuses = AsyncMock(return_value=[
            {
                "hook_id": "status_change_hook",
                "hook_type": "StatusChangeHook",
                "status": "active",
                "statistics": {
                    "total_executions": 150,
                    "successful_executions": 145,
                    "failed_executions": 5,
                    "success_rate": 0.967,
                    "average_execution_time_ms": 250.5,
                    "last_execution": datetime.now(timezone.utc).isoformat()
                }
            },
            {
                "hook_id": "assignment_hook",
                "hook_type": "AssignmentHook",
                "status": "active",
                "statistics": {
                    "total_executions": 89,
                    "successful_executions": 87,
                    "failed_executions": 2,
                    "success_rate": 0.978,
                    "average_execution_time_ms": 180.2,
                    "last_execution": datetime.now(timezone.utc).isoformat()
                }
            }
        ])
        manager.get_system_health = AsyncMock(return_value=Mock(
            health_status=Mock(value="healthy"),
            total_executions=239,
            successful_executions=232,
            failed_executions=7,
            average_execution_time_ms=220.1,
            executions_per_minute=12.5
        ))
        manager.get_hook_status = AsyncMock(return_value={
            "hook_id": "status_change_hook",
            "status": "active",
            "statistics": {"success_rate": 0.967}
        })
        return manager
    
    @patch('devsync_ai.api.health_check_routes.get_health_monitor')
    def test_get_system_health_success(self, mock_get_monitor, mock_health_monitor):
        """Test successful system health check."""
        mock_get_monitor.return_value = mock_health_monitor
        
        response = client.get("/api/health/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "components" in data
        assert "system_resources" in data
        assert data["active_alerts"] == 0
        assert data["monitoring_active"] is True
        
        # Check components
        assert "hook_registry" in data["components"]
        assert "database" in data["components"]
        
        # Check system resources
        resources = data["system_resources"]
        assert "cpu_usage" in resources
        assert "memory_usage" in resources
        assert "disk_usage" in resources
    
    @patch('devsync_ai.api.health_check_routes.get_health_monitor')
    def test_get_component_health_success(self, mock_get_monitor, mock_health_monitor):
        """Test successful component health check."""
        mock_get_monitor.return_value = mock_health_monitor
        
        response = client.get("/api/health/components")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 2
        
        # Check first component
        component = data[0]
        assert "component_name" in component
        assert "status" in component
        assert "response_time_ms" in component
        assert "last_check" in component
        assert "metadata" in component
    
    @patch('devsync_ai.api.health_check_routes.get_health_monitor')
    def test_get_component_health_detail_success(self, mock_get_monitor, mock_health_monitor):
        """Test successful component health detail check."""
        mock_get_monitor.return_value = mock_health_monitor
        
        response = client.get("/api/health/components/hook_registry")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["component_name"] == "hook_registry"
        assert data["status"] == "operational"
        assert "response_time_ms" in data
        assert "last_check" in data
        assert "metadata" in data
        assert "health_history" in data
    
    @patch('devsync_ai.api.health_check_routes.get_health_monitor')
    def test_get_component_health_detail_not_found(self, mock_get_monitor, mock_health_monitor):
        """Test component health detail for non-existent component."""
        mock_get_monitor.return_value = mock_health_monitor
        
        response = client.get("/api/health/components/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @patch('devsync_ai.api.health_check_routes.SystemDiagnosticTools')
    def test_run_system_diagnostics_success(self, mock_diagnostic_tools):
        """Test successful system diagnostics."""
        # Mock diagnostic report
        mock_report = Mock()
        mock_report.report_id = "diag_123456"
        mock_report.generated_at = datetime.now(timezone.utc)
        mock_report.overall_health_score = 85.5
        mock_report.issues = [Mock(severity=Mock(value="warning")), Mock(severity=Mock(value="critical"))]
        mock_report.recommendations = ["Recommendation 1", "Recommendation 2"]
        
        mock_tools = Mock()
        mock_tools.run_comprehensive_diagnostics = AsyncMock(return_value=mock_report)
        mock_diagnostic_tools.return_value = mock_tools
        
        response = client.get("/api/health/diagnostics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["report_id"] == "diag_123456"
        assert data["overall_health_score"] == 85.5
        assert data["issues_count"] == 2
        assert data["critical_issues"] == 1
        assert data["warning_issues"] == 1
        assert data["recommendations_count"] == 2
    
    @patch('devsync_ai.api.health_check_routes.get_hook_registry_manager')
    def test_get_hook_system_health_success(self, mock_get_registry, mock_registry_manager):
        """Test successful hook system health check."""
        mock_get_registry.return_value = mock_registry_manager
        
        response = client.get("/api/health/hooks")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "summary" in data
        assert "hooks" in data
        assert "system_metrics" in data
        
        # Check summary
        summary = data["summary"]
        assert summary["total_hooks"] == 2
        assert summary["active_hooks"] == 2
        assert summary["inactive_hooks"] == 0
        assert "average_success_rate" in summary
        assert "average_response_time_ms" in summary
    
    @patch('devsync_ai.api.health_check_routes.get_hook_registry_manager')
    def test_get_hook_system_health_unavailable(self, mock_get_registry):
        """Test hook system health when registry is unavailable."""
        mock_get_registry.return_value = None
        
        response = client.get("/api/health/hooks")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unavailable"
        assert "not available" in data["message"]
    
    @patch('devsync_ai.api.health_check_routes.get_hook_registry_manager')
    @patch('devsync_ai.api.health_check_routes.HookAnalyticsEngine')
    def test_get_hook_health_detail_success(self, mock_analytics_engine, mock_get_registry, mock_registry_manager):
        """Test successful hook health detail check."""
        mock_get_registry.return_value = mock_registry_manager
        
        mock_engine = Mock()
        mock_engine.get_hook_performance_metrics = AsyncMock(return_value=Mock(
            success_rate=0.967,
            average_execution_time_ms=250.5
        ))
        mock_analytics_engine.return_value = mock_engine
        
        response = client.get("/api/health/hooks/status_change_hook")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["hook_id"] == "status_change_hook"
        assert "status" in data
        assert "performance_metrics" in data
        assert "timestamp" in data
    
    @patch('devsync_ai.api.health_check_routes.get_hook_registry_manager')
    def test_get_hook_health_detail_not_found(self, mock_get_registry, mock_registry_manager):
        """Test hook health detail for non-existent hook."""
        mock_registry_manager.get_hook_status = AsyncMock(return_value=None)
        mock_get_registry.return_value = mock_registry_manager
        
        response = client.get("/api/health/hooks/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @patch('devsync_ai.api.health_check_routes.get_health_monitor')
    @patch('devsync_ai.api.health_check_routes.HookAnalyticsEngine')
    def test_get_active_alerts_success(self, mock_analytics_engine, mock_get_monitor, mock_health_monitor):
        """Test successful active alerts retrieval."""
        # Mock system alerts
        system_alert = Mock()
        system_alert.alert_id = "sys_alert_1"
        system_alert.component = "system"
        system_alert.severity = "warning"
        system_alert.message = "High CPU usage"
        system_alert.triggered_at = datetime.now(timezone.utc)
        
        mock_health_monitor.get_active_alerts = AsyncMock(return_value=[system_alert])
        mock_get_monitor.return_value = mock_health_monitor
        
        # Mock analytics alerts
        analytics_alert = Mock()
        analytics_alert.alert_id = "analytics_alert_1"
        analytics_alert.severity = Mock(value="critical")
        analytics_alert.title = "Hook failure rate high"
        analytics_alert.triggered_at = datetime.now(timezone.utc)
        
        mock_engine = Mock()
        mock_engine.get_active_alerts = AsyncMock(return_value=[analytics_alert])
        mock_analytics_engine.return_value = mock_engine
        
        response = client.get("/api/health/alerts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_alerts"] == 2
        assert len(data["alerts"]) == 2
        
        # Check alert structure
        alert = data["alerts"][0]
        assert "alert_id" in alert
        assert "component" in alert
        assert "severity" in alert
        assert "message" in alert
        assert "triggered_at" in alert
        assert "source" in alert
    
    @patch('devsync_ai.api.health_check_routes.get_health_monitor')
    @patch('devsync_ai.api.health_check_routes.get_hook_registry_manager')
    def test_get_system_metrics_success(self, mock_get_registry, mock_get_monitor, mock_registry_manager, mock_health_monitor):
        """Test successful system metrics retrieval."""
        mock_get_monitor.return_value = mock_health_monitor
        mock_get_registry.return_value = mock_registry_manager
        
        response = client.get("/api/health/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "timestamp" in data
        assert "system_resources" in data
        assert "hook_metrics" in data
        assert "component_response_times" in data
        assert "monitoring_active" in data
        
        # Check hook metrics
        hook_metrics = data["hook_metrics"]
        assert "total_executions" in hook_metrics
        assert "successful_executions" in hook_metrics
        assert "failed_executions" in hook_metrics
        assert "average_execution_time_ms" in hook_metrics
        assert "executions_per_minute" in hook_metrics
    
    @patch('devsync_ai.api.health_check_routes.get_health_monitor')
    def test_start_monitoring_success(self, mock_get_monitor, mock_health_monitor):
        """Test successful monitoring start."""
        mock_get_monitor.return_value = mock_health_monitor
        
        response = client.post("/api/health/monitoring/start")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "started"
        assert "successfully" in data["message"]
        assert "timestamp" in data
        
        mock_health_monitor.start_monitoring.assert_called_once()
    
    @patch('devsync_ai.api.health_check_routes.get_health_monitor')
    def test_stop_monitoring_success(self, mock_get_monitor, mock_health_monitor):
        """Test successful monitoring stop."""
        mock_get_monitor.return_value = mock_health_monitor
        
        response = client.post("/api/health/monitoring/stop")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "stopped"
        assert "successfully" in data["message"]
        assert "timestamp" in data
        
        mock_health_monitor.stop_monitoring.assert_called_once()


class TestMonitoringDashboardEndpoints:
    """Test monitoring dashboard API endpoints."""
    
    @pytest.fixture
    def mock_dashboard(self):
        """Mock monitoring dashboard."""
        dashboard = Mock(spec=MonitoringDashboard)
        dashboard.get_available_layouts = AsyncMock(return_value=[
            {
                "layout_id": "system_overview",
                "name": "System Overview",
                "description": "High-level system health metrics",
                "widget_count": 5,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ])
        
        # Mock layout
        mock_layout = Mock()
        mock_layout.layout_id = "system_overview"
        mock_layout.name = "System Overview"
        mock_layout.description = "High-level system health metrics"
        mock_layout.widgets = [
            Mock(
                widget_id="system_health_status",
                widget_type="status_indicator",
                title="System Health",
                metric_type=Mock(value="system_health"),
                refresh_interval_seconds=30,
                configuration={},
                position={"x": 0, "y": 0, "width": 4, "height": 2}
            )
        ]
        mock_layout.created_at = datetime.now(timezone.utc)
        mock_layout.updated_at = datetime.now(timezone.utc)
        
        dashboard.get_dashboard_layout = AsyncMock(return_value=mock_layout)
        dashboard.get_widget_data = AsyncMock(return_value={
            "widget_id": "system_health_status",
            "widget_type": "status_indicator",
            "title": "System Health",
            "data": {"overall_status": "healthy"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return dashboard
    
    @patch('devsync_ai.api.health_check_routes.get_monitoring_dashboard')
    def test_get_dashboard_layouts_success(self, mock_get_dashboard, mock_dashboard):
        """Test successful dashboard layouts retrieval."""
        mock_get_dashboard.return_value = mock_dashboard
        
        response = client.get("/api/health/dashboard/layouts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "layouts" in data
        assert "timestamp" in data
        assert len(data["layouts"]) == 1
        
        layout = data["layouts"][0]
        assert layout["layout_id"] == "system_overview"
        assert layout["name"] == "System Overview"
        assert layout["widget_count"] == 5
    
    @patch('devsync_ai.api.health_check_routes.get_monitoring_dashboard')
    def test_get_dashboard_layout_success(self, mock_get_dashboard, mock_dashboard):
        """Test successful dashboard layout retrieval."""
        mock_get_dashboard.return_value = mock_dashboard
        
        response = client.get("/api/health/dashboard/system_overview")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["layout_id"] == "system_overview"
        assert data["name"] == "System Overview"
        assert "widgets" in data
        assert len(data["widgets"]) == 1
        
        widget = data["widgets"][0]
        assert widget["widget_id"] == "system_health_status"
        assert widget["widget_type"] == "status_indicator"
        assert widget["title"] == "System Health"
        assert "data" in widget
    
    @patch('devsync_ai.api.health_check_routes.get_monitoring_dashboard')
    def test_get_dashboard_layout_not_found(self, mock_get_dashboard, mock_dashboard):
        """Test dashboard layout retrieval for non-existent layout."""
        mock_dashboard.get_dashboard_layout = AsyncMock(return_value=None)
        mock_get_dashboard.return_value = mock_dashboard
        
        response = client.get("/api/health/dashboard/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @patch('devsync_ai.api.health_check_routes.get_monitoring_dashboard')
    def test_get_widget_data_success(self, mock_get_dashboard, mock_dashboard):
        """Test successful widget data retrieval."""
        mock_get_dashboard.return_value = mock_dashboard
        
        response = client.get("/api/health/dashboard/system_overview/widgets/system_health_status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["widget_id"] == "system_health_status"
        assert data["widget_type"] == "status_indicator"
        assert data["title"] == "System Health"
        assert "data" in data
        assert "timestamp" in data


class TestHealthCheckIntegration:
    """Integration tests for health check system."""
    
    @pytest.mark.asyncio
    async def test_system_health_monitor_integration(self):
        """Test system health monitor integration."""
        monitor = SystemHealthMonitor()
        
        # Test health status retrieval
        health_status = await monitor.get_system_health_status()
        
        assert "overall_status" in health_status
        assert "timestamp" in health_status
        assert "components" in health_status
        assert "system_resources" in health_status
        assert "monitoring_active" in health_status
    
    @pytest.mark.asyncio
    async def test_diagnostic_tools_integration(self):
        """Test diagnostic tools integration."""
        diagnostic_tools = SystemDiagnosticTools()
        
        # Test basic diagnostics
        report = await diagnostic_tools.run_comprehensive_diagnostics([
            DiagnosticCategory.SYSTEM_RESOURCES
        ])
        
        assert report.report_id is not None
        assert report.generated_at is not None
        assert isinstance(report.overall_health_score, float)
        assert 0 <= report.overall_health_score <= 100
        assert isinstance(report.issues, list)
        assert isinstance(report.recommendations, list)
    
    @pytest.mark.asyncio
    async def test_monitoring_dashboard_integration(self):
        """Test monitoring dashboard integration."""
        dashboard = MonitoringDashboard()
        await dashboard.initialize()
        
        # Test layout retrieval
        layouts = await dashboard.get_available_layouts()
        assert isinstance(layouts, list)
        assert len(layouts) > 0
        
        # Test layout detail
        layout = await dashboard.get_dashboard_layout("system_overview")
        assert layout is not None
        assert layout.layout_id == "system_overview"
        assert len(layout.widgets) > 0
    
    @pytest.mark.asyncio
    async def test_end_to_end_health_check_flow(self):
        """Test complete end-to-end health check flow."""
        # Initialize components
        monitor = SystemHealthMonitor()
        dashboard = MonitoringDashboard()
        await dashboard.initialize()
        
        # Get system health
        health_status = await monitor.get_system_health_status()
        assert health_status["overall_status"] in ["healthy", "warning", "critical", "error"]
        
        # Get dashboard data
        layouts = await dashboard.get_available_layouts()
        assert len(layouts) > 0
        
        # Get widget data for first layout
        first_layout = layouts[0]
        layout_detail = await dashboard.get_dashboard_layout(first_layout["layout_id"])
        assert layout_detail is not None
        
        if layout_detail.widgets:
            widget_data = await dashboard.get_widget_data(
                layout_detail.widgets[0].widget_id,
                layout_detail.layout_id
            )
            assert "widget_id" in widget_data
            assert "data" in widget_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])