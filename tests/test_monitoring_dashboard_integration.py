"""
Integration tests for the monitoring dashboard and health check system.

Tests the complete monitoring infrastructure including health checks,
performance monitoring, alerting, and dashboard functionality.
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json

from devsync_ai.analytics.system_health_monitor import (
    SystemHealthMonitor, 
    get_health_monitor,
    ComponentStatus,
    DiagnosticLevel
)
from devsync_ai.analytics.monitoring_dashboard import (
    MonitoringDashboard,
    get_monitoring_dashboard,
    DashboardMetricType
)
from devsync_ai.analytics.hook_analytics_engine import HookAnalyticsEngine, HealthStatus
from devsync_ai.core.agent_hooks import HookExecutionResult, HookStatus


class TestSystemHealthMonitor:
    """Test system health monitoring functionality."""
    
    @pytest.fixture
    def health_monitor(self):
        """Create a health monitor instance for testing."""
        return SystemHealthMonitor()
    
    @pytest.mark.asyncio
    async def test_health_monitor_initialization(self, health_monitor):
        """Test health monitor initialization."""
        assert health_monitor is not None
        assert not health_monitor._monitoring_active
        assert len(health_monitor.component_health) == 0
        assert len(health_monitor.thresholds) > 0
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, health_monitor):
        """Test starting and stopping monitoring."""
        # Start monitoring
        await health_monitor.start_monitoring()
        assert health_monitor._monitoring_active
        assert health_monitor._monitoring_task is not None
        
        # Stop monitoring
        await health_monitor.stop_monitoring()
        assert not health_monitor._monitoring_active
    
    @pytest.mark.asyncio
    async def test_component_health_checks(self, health_monitor):
        """Test individual component health checks."""
        # Mock dependencies
        with patch('devsync_ai.analytics.system_health_monitor.get_hook_registry_manager') as mock_registry:
            mock_registry.return_value = Mock()
            mock_registry.return_value.get_all_hook_statuses = AsyncMock(return_value=[])
            mock_registry.return_value.get_system_health = AsyncMock(return_value=Mock())
            
            with patch('devsync_ai.analytics.system_health_monitor.get_analytics_data_manager') as mock_data_manager:
                mock_data_manager.return_value = Mock()
                mock_data_manager.return_value.query_records = AsyncMock(return_value=[])
                
                # Perform health checks
                await health_monitor._perform_health_checks()
                
                # Verify components were checked
                assert 'hook_registry' in health_monitor.component_health
                assert 'database' in health_monitor.component_health
                assert 'analytics_engine' in health_monitor.component_health
                
                # Check component health structure
                hook_registry_health = health_monitor.component_health['hook_registry']
                assert hook_registry_health.component_name == 'hook_registry'
                assert isinstance(hook_registry_health.status, ComponentStatus)
                assert isinstance(hook_registry_health.response_time_ms, float)
                assert isinstance(hook_registry_health.last_check, datetime)
    
    @pytest.mark.asyncio
    async def test_performance_alert_creation(self, health_monitor):
        """Test performance alert creation and management."""
        # Create a test alert
        await health_monitor._create_performance_alert(
            alert_id="test_alert",
            component="test_component",
            metric_name="test_metric",
            current_value=95.0,
            threshold_value=90.0,
            severity="warning",
            message="Test alert message"
        )
        
        # Verify alert was created
        assert "test_alert" in health_monitor.active_alerts
        alert = health_monitor.active_alerts["test_alert"]
        assert alert.component == "test_component"
        assert alert.current_value == 95.0
        assert alert.severity == "warning"
    
    @pytest.mark.asyncio
    async def test_system_health_status(self, health_monitor):
        """Test system health status retrieval."""
        # Mock psutil for system metrics
        with patch('psutil.cpu_percent', return_value=50.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 60.0
                mock_memory.return_value.available = 4 * 1024**3  # 4GB
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 70.0
                    mock_disk.return_value.free = 100 * 1024**3  # 100GB
                    
                    # Get health status
                    status = await health_monitor.get_system_health_status()
                    
                    # Verify status structure
                    assert 'overall_status' in status
                    assert 'timestamp' in status
                    assert 'components' in status
                    assert 'system_resources' in status
                    assert 'active_alerts' in status
                    
                    # Verify system resources
                    resources = status['system_resources']
                    assert resources['cpu_usage'] == 50.0
                    assert resources['memory_usage'] == 60.0
                    assert resources['disk_usage'] == 70.0
    
    @pytest.mark.asyncio
    async def test_detailed_diagnostics(self, health_monitor):
        """Test detailed system diagnostics."""
        # Mock system components
        with patch('psutil.cpu_percent', return_value=45.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 55.0
                mock_memory.return_value.available = 8 * 1024**3
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 65.0
                    mock_disk.return_value.free = 200 * 1024**3
                    
                    # Get detailed diagnostics
                    diagnostics = await health_monitor.get_detailed_diagnostics(DiagnosticLevel.DETAILED)
                    
                    # Verify diagnostics structure
                    assert diagnostics.overall_status in [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL]
                    assert isinstance(diagnostics.components, dict)
                    assert isinstance(diagnostics.performance_metrics, dict)
                    assert isinstance(diagnostics.resource_usage, dict)
                    assert isinstance(diagnostics.active_issues, list)
                    assert isinstance(diagnostics.recommendations, list)
                    assert diagnostics.diagnostic_level == DiagnosticLevel.DETAILED
    
    @pytest.mark.asyncio
    async def test_threshold_updates(self, health_monitor):
        """Test updating performance thresholds."""
        # Get original thresholds
        original_cpu_warning = health_monitor.thresholds['cpu_warning']
        
        # Update thresholds
        new_thresholds = {'cpu_warning': 80.0, 'memory_warning': 85.0}
        success = await health_monitor.update_thresholds(new_thresholds)
        
        # Verify update
        assert success
        assert health_monitor.thresholds['cpu_warning'] == 80.0
        assert health_monitor.thresholds['memory_warning'] == 85.0
        
        # Test invalid threshold keys
        invalid_thresholds = {'invalid_key': 50.0}
        success = await health_monitor.update_thresholds(invalid_thresholds)
        assert not success


class TestMonitoringDashboard:
    """Test monitoring dashboard functionality."""
    
    @pytest.fixture
    def monitoring_dashboard(self):
        """Create a monitoring dashboard instance for testing."""
        return MonitoringDashboard()
    
    @pytest.mark.asyncio
    async def test_dashboard_initialization(self, monitoring_dashboard):
        """Test dashboard initialization."""
        assert monitoring_dashboard is not None
        assert len(monitoring_dashboard.layouts) > 0
        assert 'system_overview' in monitoring_dashboard.layouts
        assert 'hook_performance' in monitoring_dashboard.layouts
        assert 'team_analytics' in monitoring_dashboard.layouts
    
    @pytest.mark.asyncio
    async def test_get_available_layouts(self, monitoring_dashboard):
        """Test getting available dashboard layouts."""
        layouts = await monitoring_dashboard.get_available_layouts()
        
        assert isinstance(layouts, list)
        assert len(layouts) >= 3  # At least the default layouts
        
        # Check layout structure
        for layout in layouts:
            assert 'layout_id' in layout
            assert 'name' in layout
            assert 'description' in layout
            assert 'widget_count' in layout
            assert 'created_at' in layout
            assert 'updated_at' in layout
    
    @pytest.mark.asyncio
    async def test_get_dashboard_layout(self, monitoring_dashboard):
        """Test getting a specific dashboard layout."""
        layout = await monitoring_dashboard.get_dashboard_layout('system_overview')
        
        assert layout is not None
        assert layout.layout_id == 'system_overview'
        assert layout.name == 'System Overview'
        assert len(layout.widgets) > 0
        
        # Test non-existent layout
        layout = await monitoring_dashboard.get_dashboard_layout('non_existent')
        assert layout is None
    
    @pytest.mark.asyncio
    async def test_widget_data_generation(self, monitoring_dashboard):
        """Test widget data generation."""
        # Mock metrics cache
        monitoring_dashboard.metrics_cache = {
            'system_health': {
                'overall_status': 'healthy',
                'components': {},
                'active_alerts': 0,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'system_resources': {
                    'cpu_usage': 45.0,
                    'memory_usage': 60.0,
                    'disk_usage': 70.0
                }
            },
            'hook_statuses': [
                {
                    'hook_id': 'test_hook_1',
                    'hook_type': 'status_change',
                    'team_id': 'team_a',
                    'statistics': {
                        'success_rate': 0.95,
                        'average_execution_time_ms': 150.0,
                        'total_executions': 100
                    }
                }
            ]
        }
        
        # Test system health widget
        widget_data = await monitoring_dashboard.get_widget_data('system_health_status', 'system_overview')
        
        assert 'widget_id' in widget_data
        assert 'data' in widget_data
        assert widget_data['data']['overall_status'] == 'healthy'
        
        # Test resource usage widget
        widget_data = await monitoring_dashboard.get_widget_data('resource_usage_chart', 'system_overview')
        
        assert 'data' in widget_data
        assert 'current' in widget_data['data']
        assert widget_data['data']['current']['cpu_usage'] == 45.0
    
    @pytest.mark.asyncio
    async def test_dashboard_summary(self, monitoring_dashboard):
        """Test dashboard summary generation."""
        # Mock metrics cache
        monitoring_dashboard.metrics_cache = {
            'system_health': {
                'overall_status': 'healthy',
                'active_alerts': 2,
                'monitoring_active': True
            },
            'hook_statuses': [
                {
                    'statistics': {
                        'success_rate': 0.95,
                        'total_executions': 50
                    }
                },
                {
                    'statistics': {
                        'success_rate': 0.90,
                        'total_executions': 30
                    }
                }
            ]
        }
        monitoring_dashboard.last_update = datetime.now(timezone.utc)
        
        summary = await monitoring_dashboard.get_dashboard_summary()
        
        assert 'system_status' in summary
        assert 'total_hooks' in summary
        assert 'active_hooks' in summary
        assert 'overall_success_rate' in summary
        assert 'active_alerts' in summary
        assert 'last_update' in summary
        
        # Verify calculations
        assert summary['total_hooks'] == 2
        assert summary['active_hooks'] == 2  # Both have executions > 0
        assert summary['overall_success_rate'] == 0.925  # Average of 0.95 and 0.90
        assert summary['active_alerts'] == 2


class TestMonitoringIntegration:
    """Test integration between monitoring components."""
    
    @pytest.mark.asyncio
    async def test_health_monitor_dashboard_integration(self):
        """Test integration between health monitor and dashboard."""
        # Create instances
        health_monitor = SystemHealthMonitor()
        monitoring_dashboard = MonitoringDashboard()
        
        try:
            # Mock initialization
            with patch.object(monitoring_dashboard, '_start_data_collection'):
                await monitoring_dashboard.initialize()
            
            # Mock health monitor data
            health_monitor.component_health = {
                'test_component': Mock(
                    component_name='test_component',
                    status=ComponentStatus.OPERATIONAL,
                    response_time_ms=100.0,
                    last_check=datetime.now(timezone.utc),
                    error_message=None,
                    metadata={}
                )
            }
            
            # Test health status retrieval
            with patch('psutil.cpu_percent', return_value=50.0):
                with patch('psutil.virtual_memory') as mock_memory:
                    mock_memory.return_value.percent = 60.0
                    mock_memory.return_value.available = 4 * 1024**3
                    
                    with patch('psutil.disk_usage') as mock_disk:
                        mock_disk.return_value.percent = 70.0
                        mock_disk.return_value.free = 100 * 1024**3
                        
                        status = await health_monitor.get_system_health_status()
                        
                        # Verify integration data
                        assert 'components' in status
                        assert 'test_component' in status['components']
                        assert status['components']['test_component']['status'] == 'operational'
        
        finally:
            await health_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_analytics_engine_integration(self):
        """Test integration with analytics engine."""
        analytics_engine = HookAnalyticsEngine()
        
        # Create mock execution result
        execution_result = HookExecutionResult(
            hook_id="test_hook",
            execution_id="exec_123",
            status=HookStatus.SUCCESS,
            execution_time_ms=150.0,
            notification_sent=True,
            hook_type="status_change",
            event_id="event_123",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            metadata={'team_id': 'test_team'}
        )
        
        # Mock data manager
        with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_data_manager:
            mock_data_manager.return_value = Mock()
            mock_data_manager.return_value.store_record = AsyncMock(return_value=True)
            
            # Record execution
            success = await analytics_engine.record_hook_execution(execution_result)
            assert success
            
            # Verify performance cache was updated
            assert "test_hook" in analytics_engine.performance_cache
            cached_metrics = analytics_engine.performance_cache["test_hook"]
            assert cached_metrics.hook_id == "test_hook"
            assert cached_metrics.total_executions == 1
            assert cached_metrics.successful_executions == 1
    
    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_flow(self):
        """Test complete end-to-end monitoring flow."""
        # This test simulates a complete monitoring scenario
        
        # 1. Initialize monitoring components
        health_monitor = SystemHealthMonitor()
        analytics_engine = HookAnalyticsEngine()
        
        try:
            # 2. Start monitoring
            await health_monitor.start_monitoring()
            
            # 3. Simulate hook execution
            execution_result = HookExecutionResult(
                hook_id="integration_test_hook",
                execution_id="exec_integration_123",
                status=HookStatus.SUCCESS,
                execution_time_ms=200.0,
                notification_sent=True,
                hook_type="assignment",
                event_id="event_integration_123",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                metadata={'team_id': 'integration_team'}
            )
            
            # Mock data manager for analytics
            with patch('devsync_ai.analytics.hook_analytics_engine.get_analytics_data_manager') as mock_data_manager:
                mock_data_manager.return_value = Mock()
                mock_data_manager.return_value.store_record = AsyncMock(return_value=True)
                
                # Record execution in analytics
                await analytics_engine.record_hook_execution(execution_result)
            
            # 4. Check system health
            with patch('psutil.cpu_percent', return_value=75.0):  # High CPU to trigger alert
                with patch('psutil.virtual_memory') as mock_memory:
                    mock_memory.return_value.percent = 85.0  # High memory
                    mock_memory.return_value.available = 2 * 1024**3
                    
                    with patch('psutil.disk_usage') as mock_disk:
                        mock_disk.return_value.percent = 60.0
                        mock_disk.return_value.free = 100 * 1024**3
                        
                        # Trigger performance checks
                        await health_monitor._check_performance_metrics()
                        
                        # Verify alerts were created
                        assert len(health_monitor.active_alerts) > 0
                        
                        # Get system health status
                        status = await health_monitor.get_system_health_status()
                        
                        # Verify high resource usage is reflected
                        assert status['system_resources']['cpu_usage'] == 75.0
                        assert status['system_resources']['memory_usage'] == 85.0
                        assert status['active_alerts'] > 0
            
            # 5. Verify analytics data
            assert "integration_test_hook" in analytics_engine.performance_cache
            metrics = analytics_engine.performance_cache["integration_test_hook"]
            assert metrics.total_executions == 1
            assert metrics.success_rate == 1.0
            assert metrics.average_execution_time_ms == 200.0
        
        finally:
            await health_monitor.stop_monitoring()


@pytest.mark.asyncio
async def test_monitoring_api_endpoints():
    """Test monitoring API endpoints."""
    from fastapi.testclient import TestClient
    from devsync_ai.analytics.dashboard_api import analytics_app
    
    client = TestClient(analytics_app)
    
    # Test basic health check
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "components" in data
    
    # Test dashboard layouts endpoint
    with patch('devsync_ai.analytics.dashboard_api.get_monitoring_dashboard') as mock_dashboard:
        mock_dashboard.return_value = Mock()
        mock_dashboard.return_value.get_available_layouts = AsyncMock(return_value=[
            {
                "layout_id": "test_layout",
                "name": "Test Layout",
                "description": "Test description",
                "widget_count": 3,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ])
        
        response = client.get("/api/dashboard/layouts")
        assert response.status_code == 200
        data = response.json()
        assert "layouts" in data
        assert len(data["layouts"]) == 1
        assert data["layouts"][0]["layout_id"] == "test_layout"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])