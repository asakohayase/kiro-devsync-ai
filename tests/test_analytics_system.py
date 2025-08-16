"""
Comprehensive test suite for DevSync AI Analytics System.

Tests all components of the monitoring and analytics system including
dashboard, data management, intelligence engine, and optimization.
"""

import asyncio
import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from devsync_ai.analytics.hook_monitoring_dashboard import HookMonitoringDashboard
from devsync_ai.analytics.productivity_analytics_engine import ProductivityAnalyticsEngine
from devsync_ai.analytics.intelligence_engine import IntelligenceEngine
from devsync_ai.analytics.hook_optimization_engine import HookOptimizationEngine
from devsync_ai.analytics.analytics_data_manager import AnalyticsDataManager, AnalyticsRecord
from devsync_ai.analytics.dashboard_api import analytics_app


class TestHookMonitoringDashboard:
    """Test suite for Hook Monitoring Dashboard."""
    
    @pytest.fixture
    async def dashboard(self):
        """Create dashboard instance for testing."""
        dashboard = HookMonitoringDashboard()
        await dashboard.start_monitoring()
        yield dashboard
        await dashboard.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_dashboard_initialization(self, dashboard):
        """Test dashboard initialization."""
        assert dashboard._monitoring_active is True
        assert dashboard._monitoring_task is not None
        assert len(dashboard.metrics_history) >= 0
    
    @pytest.mark.asyncio
    async def test_system_metrics_collection(self, dashboard):
        """Test system metrics collection."""
        with patch('psutil.cpu_percent', return_value=45.0), \
             patch('psutil.virtual_memory') as mock_memory:
            
            mock_memory.return_value.percent = 60.0
            mock_memory.return_value.available = 4 * 1024 * 1024 * 1024  # 4GB
            mock_memory.return_value.total = 8 * 1024 * 1024 * 1024  # 8GB
            mock_memory.return_value.used = 4 * 1024 * 1024 * 1024  # 4GB
            
            metrics = await dashboard._collect_system_metrics()
            
            assert metrics.cpu_usage == 45.0
            assert metrics.memory_usage == 60.0
            assert metrics.health_status.value in ['healthy', 'warning', 'critical']
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, dashboard):
        """Test WebSocket connection handling."""
        mock_websocket = AsyncMock()
        
        await dashboard.connect_websocket(mock_websocket)
        assert mock_websocket in dashboard.active_connections
        
        dashboard.disconnect_websocket(mock_websocket)
        assert mock_websocket not in dashboard.active_connections
    
    @pytest.mark.asyncio
    async def test_alert_generation(self, dashboard):
        """Test alert generation for threshold violations."""
        # Create metrics that should trigger alerts
        from devsync_ai.analytics.hook_monitoring_dashboard import SystemMetrics, HealthStatus
        
        critical_metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu_usage=95.0,  # Above critical threshold
            memory_usage=98.0,  # Above critical threshold
            memory_available=0.5,
            active_connections=10,
            queue_depth=100,
            processing_rate=5.0,
            average_response_time=8000.0,  # Above critical threshold
            error_rate=20.0,  # Above critical threshold
            health_status=HealthStatus.CRITICAL
        )
        
        await dashboard._check_alert_conditions(critical_metrics)
        
        # Should have generated multiple alerts
        assert len(dashboard.real_time_events) > 0
        
        # Check for specific alert types
        alert_types = [event.data.get('type') for event in dashboard.real_time_events if event.event_type == 'alert']
        assert 'cpu_critical' in alert_types
        assert 'memory_critical' in alert_types


class TestProductivityAnalyticsEngine:
    """Test suite for Productivity Analytics Engine."""
    
    @pytest.fixture
    def analytics_engine(self):
        """Create analytics engine for testing."""
        return ProductivityAnalyticsEngine()
    
    @pytest.mark.asyncio
    async def test_sprint_performance_analysis(self, analytics_engine):
        """Test sprint performance analysis."""
        team_id = "test-team"
        sprint_id = "test-sprint"
        time_range = (
            datetime.now(timezone.utc) - timedelta(days=14),
            datetime.now(timezone.utc)
        )
        
        with patch('devsync_ai.hooks.hook_registry_manager.get_hook_registry_manager') as mock_registry:
            mock_registry.return_value = Mock()
            mock_registry.return_value.get_all_hook_statuses.return_value = [
                {
                    'team_id': team_id,
                    'hook_type': 'status_change',
                    'statistics': {
                        'total_executions': 50,
                        'success_rate': 0.96
                    }
                }
            ]
            
            analytics = await analytics_engine.analyze_sprint_performance(team_id, sprint_id, time_range)
            
            assert analytics.team_id == team_id
            assert analytics.sprint_id == sprint_id
            assert analytics.velocity > 0
            assert 0 <= analytics.completion_rate <= 1
            assert 0 <= analytics.automation_impact_score <= 100
    
    @pytest.mark.asyncio
    async def test_blocker_pattern_analysis(self, analytics_engine):
        """Test blocker pattern analysis."""
        team_id = "test-team"
        time_range = (
            datetime.now(timezone.utc) - timedelta(days=30),
            datetime.now(timezone.utc)
        )
        
        blocker_analytics = await analytics_engine.analyze_blocker_patterns(team_id, time_range)
        
        assert isinstance(blocker_analytics, list)
        for blocker in blocker_analytics:
            assert blocker.team_id == team_id
            assert blocker.blocker_type in ['dependency', 'technical', 'resource', 'external']
            assert blocker.severity in ['low', 'medium', 'high', 'critical']
    
    @pytest.mark.asyncio
    async def test_team_collaboration_analysis(self, analytics_engine):
        """Test team collaboration analysis."""
        team_id = "test-team"
        
        with patch('devsync_ai.hooks.hook_registry_manager.get_hook_registry_manager') as mock_registry:
            mock_registry.return_value = Mock()
            mock_registry.return_value.get_all_hook_statuses.return_value = [
                {
                    'team_id': team_id,
                    'statistics': {
                        'total_executions': 100
                    }
                }
            ]
            
            collaboration = await analytics_engine.analyze_team_collaboration(team_id)
            
            assert collaboration.team_id == team_id
            assert collaboration.total_interactions >= 0
            assert collaboration.automated_notifications >= 0
            assert 0 <= collaboration.collaboration_efficiency_score <= 100
    
    @pytest.mark.asyncio
    async def test_productivity_insights_generation(self, analytics_engine):
        """Test productivity insights generation."""
        team_id = "test-team"
        
        # Add some historical data
        analytics_engine.historical_velocity[team_id] = [20, 25, 30, 35]  # Improving trend
        analytics_engine.historical_blocker_times[team_id] = [48, 36, 24, 18]  # Improving trend
        
        insights = await analytics_engine.generate_productivity_insights(team_id)
        
        assert isinstance(insights, list)
        for insight in insights:
            assert insight.team_id == team_id
            assert 0 <= insight.confidence_score <= 1
            assert insight.impact_level in ['low', 'medium', 'high']
            assert len(insight.actionable_recommendations) > 0


class TestIntelligenceEngine:
    """Test suite for Intelligence Engine."""
    
    @pytest.fixture
    def intelligence_engine(self):
        """Create intelligence engine for testing."""
        return IntelligenceEngine()
    
    @pytest.mark.asyncio
    async def test_blocker_risk_prediction(self, intelligence_engine):
        """Test blocker risk prediction."""
        ticket_key = "TEST-123"
        team_id = "test-team"
        ticket_data = {
            "summary": "Integrate with external API service",
            "description": "This task requires integration with third party service",
            "priority": "high",
            "assignee": {"displayName": "John Doe"}
        }
        
        insight = await intelligence_engine.predict_blocker_risk(ticket_key, team_id, ticket_data)
        
        assert insight.ticket_key == ticket_key
        assert insight.team_id == team_id
        assert 0 <= insight.probability <= 1
        assert 0 <= insight.confidence_score <= 1
        assert insight.risk_level in ['low', 'medium', 'high']
        assert len(insight.mitigation_strategies) > 0
    
    @pytest.mark.asyncio
    async def test_assignment_recommendation(self, intelligence_engine):
        """Test assignment recommendation."""
        ticket_key = "TEST-124"
        team_id = "test-team"
        ticket_data = {
            "summary": "Fix frontend bug in React component",
            "story_points": 3
        }
        available_assignees = ["alice", "bob", "charlie"]
        
        recommendation = await intelligence_engine.recommend_optimal_assignment(
            ticket_key, team_id, ticket_data, available_assignees
        )
        
        assert recommendation.ticket_key == ticket_key
        assert recommendation.recommended_assignee in available_assignees
        assert 0 <= recommendation.confidence_score <= 1
        assert 0 <= recommendation.skill_match_score <= 1
        assert len(recommendation.reasoning) > 0
    
    @pytest.mark.asyncio
    async def test_sprint_risk_assessment(self, intelligence_engine):
        """Test sprint risk assessment."""
        sprint_id = "test-sprint"
        team_id = "test-team"
        sprint_data = {
            "planned_story_points": 30,
            "completed_story_points": 15,
            "days_remaining": 5,
            "active_blockers": 2
        }
        
        assessment = await intelligence_engine.assess_sprint_risk(sprint_id, team_id, sprint_data)
        
        assert assessment.sprint_id == sprint_id
        assert assessment.team_id == team_id
        assert 0 <= assessment.overall_risk_score <= 100
        assert assessment.risk_level in ['low', 'medium', 'high', 'critical']
        assert 0 <= assessment.completion_probability <= 1
        assert len(assessment.mitigation_recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_team_health_analysis(self, intelligence_engine):
        """Test team communication health analysis."""
        team_id = "test-team"
        
        with patch.object(intelligence_engine.productivity_engine, 'analyze_team_collaboration') as mock_collab:
            mock_collab.return_value = Mock(
                collaboration_efficiency_score=85.0,
                cross_team_communications=25,
                automated_notifications=100,
                manual_status_updates=20,
                response_time_improvement=0.3,
                communication_patterns={'peak_hours': [10, 14, 16]}
            )
            
            health_insight = await intelligence_engine.analyze_team_communication_health(team_id)
            
            assert health_insight.team_id == team_id
            assert 0 <= health_insight.health_score <= 100
            assert 0 <= health_insight.communication_efficiency <= 1
            assert 0 <= health_insight.burnout_risk <= 1
            assert len(health_insight.recommendations) >= 0


class TestHookOptimizationEngine:
    """Test suite for Hook Optimization Engine."""
    
    @pytest.fixture
    def optimization_engine(self):
        """Create optimization engine for testing."""
        return HookOptimizationEngine()
    
    @pytest.mark.asyncio
    async def test_configuration_effectiveness_analysis(self, optimization_engine):
        """Test configuration effectiveness analysis."""
        hook_id = "test-hook"
        
        with patch('devsync_ai.hooks.hook_registry_manager.get_hook_registry_manager') as mock_registry:
            mock_registry.return_value = Mock()
            mock_registry.return_value.get_hook_status.return_value = {
                'configuration': {
                    'channels': ['#general', '#dev'],
                    'timeout_seconds': 30
                },
                'statistics': {
                    'average_execution_time_ms': 1200,
                    'success_rate': 0.95,
                    'total_executions': 100
                }
            }
            
            effectiveness = await optimization_engine.analyze_configuration_effectiveness(hook_id)
            
            assert effectiveness['hook_id'] == hook_id
            assert 'overall_effectiveness' in effectiveness
            assert 'component_scores' in effectiveness
            assert 'improvement_suggestions' in effectiveness
    
    @pytest.mark.asyncio
    async def test_ab_test_execution(self, optimization_engine):
        """Test A/B test execution."""
        from devsync_ai.analytics.hook_optimization_engine import OptimizationMetric
        
        hook_type = "status_change"
        team_id = "test-team"
        variant_a = {"timeout": 30, "retries": 3}
        variant_b = {"timeout": 15, "retries": 5}
        metric_type = OptimizationMetric.EXECUTION_TIME
        
        ab_test = await optimization_engine.run_ab_test(
            hook_type, team_id, variant_a, variant_b, metric_type
        )
        
        assert ab_test.hook_type == hook_type
        assert ab_test.team_id == team_id
        assert ab_test.variant_a == variant_a
        assert ab_test.variant_b == variant_b
        assert ab_test.winner in ['A', 'B', 'inconclusive']
        assert 0 <= ab_test.statistical_significance <= 1
    
    @pytest.mark.asyncio
    async def test_user_engagement_analysis(self, optimization_engine):
        """Test user engagement analysis."""
        hook_id = "test-hook"
        
        with patch('devsync_ai.hooks.hook_registry_manager.get_hook_registry_manager') as mock_registry:
            mock_registry.return_value = Mock()
            mock_registry.return_value.get_hook_status.return_value = {
                'team_id': 'test-team',
                'statistics': {'total_executions': 150}
            }
            
            engagement = await optimization_engine.analyze_user_engagement(hook_id)
            
            assert engagement.hook_id == hook_id
            assert engagement.total_notifications > 0
            assert 0 <= engagement.open_rate <= 1
            assert 0 <= engagement.click_through_rate <= 1
            assert 0 <= engagement.completion_rate <= 1
            assert 0 <= engagement.engagement_score <= 100
    
    @pytest.mark.asyncio
    async def test_performance_benchmarking(self, optimization_engine):
        """Test performance benchmarking."""
        hook_id = "test-hook"
        
        with patch('devsync_ai.hooks.hook_registry_manager.get_hook_registry_manager') as mock_registry:
            mock_registry.return_value = Mock()
            mock_registry.return_value.get_hook_status.return_value = {
                'statistics': {
                    'average_execution_time_ms': 1800,
                    'success_rate': 0.92
                }
            }
            
            benchmarks = await optimization_engine.benchmark_performance(hook_id)
            
            assert isinstance(benchmarks, list)
            for benchmark in benchmarks:
                assert benchmark.metric_name in ['execution_time', 'success_rate', 'user_engagement']
                assert benchmark.current_value >= 0
                assert benchmark.industry_average > 0
                assert 0 <= benchmark.benchmark_score <= 100
                assert benchmark.performance_level in ['Excellent', 'Good', 'Average', 'Below Average']


class TestAnalyticsDataManager:
    """Test suite for Analytics Data Manager."""
    
    @pytest.fixture
    async def data_manager(self):
        """Create data manager for testing."""
        manager = AnalyticsDataManager(db_path=":memory:")  # Use in-memory database
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_record_storage_and_retrieval(self, data_manager):
        """Test storing and retrieving analytics records."""
        record = AnalyticsRecord(
            id=None,
            timestamp=datetime.now(timezone.utc),
            record_type="test_record",
            team_id="test-team",
            data={"metric": "value", "count": 42},
            metadata={"source": "test"}
        )
        
        # Store record
        record_id = await data_manager.store_record(record)
        assert record_id is not None
        
        # Retrieve records
        retrieved_records = await data_manager.query_records(
            record_type="test_record",
            team_id="test-team"
        )
        
        assert len(retrieved_records) == 1
        assert retrieved_records[0].record_type == "test_record"
        assert retrieved_records[0].team_id == "test-team"
        assert retrieved_records[0].data["count"] == 42
    
    @pytest.mark.asyncio
    async def test_batch_record_storage(self, data_manager):
        """Test batch record storage."""
        records = [
            AnalyticsRecord(
                id=None,
                timestamp=datetime.now(timezone.utc),
                record_type="batch_test",
                team_id="test-team",
                data={"value": i},
                metadata={}
            )
            for i in range(10)
        ]
        
        record_ids = await data_manager.store_batch_records(records)
        assert len(record_ids) == 10
        
        # Verify all records were stored
        retrieved_records = await data_manager.query_records(record_type="batch_test")
        assert len(retrieved_records) == 10
    
    @pytest.mark.asyncio
    async def test_data_aggregation(self, data_manager):
        """Test data aggregation functionality."""
        # Store some hook execution records
        base_time = datetime.now(timezone.utc)
        records = []
        
        for i in range(24):  # 24 hours of data
            record = AnalyticsRecord(
                id=None,
                timestamp=base_time - timedelta(hours=i),
                record_type="hook_execution",
                team_id="test-team",
                data={
                    "success": i % 4 != 0,  # 75% success rate
                    "execution_time_ms": 1000 + (i * 50)
                },
                metadata={}
            )
            records.append(record)
        
        await data_manager.store_batch_records(records)
        
        # Test aggregation
        aggregated = await data_manager.aggregate_data(
            record_type="hook_execution",
            aggregation_period="hourly",
            team_id="test-team"
        )
        
        assert "aggregated_data" in aggregated
        assert aggregated["record_count"] == 24
        assert aggregated["aggregation_period"] == "hourly"
    
    @pytest.mark.asyncio
    async def test_data_export(self, data_manager):
        """Test data export functionality."""
        # Store test records
        records = [
            AnalyticsRecord(
                id=None,
                timestamp=datetime.now(timezone.utc),
                record_type="export_test",
                team_id="test-team",
                data={"test": "data"},
                metadata={"export": True}
            )
            for _ in range(5)
        ]
        
        await data_manager.store_batch_records(records)
        
        # Test JSON export
        json_export = await data_manager.export_data(
            record_type="export_test",
            format="json"
        )
        
        exported_data = json.loads(json_export)
        assert len(exported_data) == 5
        assert all(record["record_type"] == "export_test" for record in exported_data)
        
        # Test CSV export
        csv_export = await data_manager.export_data(
            record_type="export_test",
            format="csv"
        )
        
        assert "id,timestamp,record_type,team_id,data,metadata" in csv_export
        assert csv_export.count('\n') == 6  # Header + 5 records
    
    @pytest.mark.asyncio
    async def test_data_integrity_verification(self, data_manager):
        """Test data integrity verification."""
        # Store some test data
        record = AnalyticsRecord(
            id=None,
            timestamp=datetime.now(timezone.utc),
            record_type="integrity_test",
            team_id="test-team",
            data={"test": "integrity"},
            metadata={}
        )
        
        await data_manager.store_record(record)
        
        # Verify integrity
        integrity_results = await data_manager.verify_data_integrity()
        
        assert "analytics_records" in integrity_results
        assert integrity_results["analytics_records"]["record_count"] >= 1
        assert integrity_results["analytics_records"]["status"] == "healthy"


class TestDashboardAPI:
    """Test suite for Dashboard API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client for API testing."""
        return TestClient(analytics_app)
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
    
    def test_dashboard_home_page(self, client):
        """Test dashboard home page."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    @patch('devsync_ai.analytics.dashboard_api.get_dashboard')
    def test_system_metrics_endpoint(self, mock_get_dashboard, client):
        """Test system metrics API endpoint."""
        mock_dashboard = AsyncMock()
        mock_dashboard.get_current_metrics.return_value = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_metrics": {
                "cpu_usage_percent": 45.0,
                "memory_usage_percent": 60.0,
                "health_status": "healthy"
            }
        }
        mock_get_dashboard.return_value = mock_dashboard
        
        response = client.get("/api/metrics/system")
        assert response.status_code == 200
        
        data = response.json()
        assert "system_metrics" in data
        assert data["system_metrics"]["cpu_usage_percent"] == 45.0
    
    def test_voice_query_endpoint(self, client):
        """Test voice query processing endpoint."""
        response = client.post(
            "/api/voice/query",
            json={"query": "How is our current sprint health?"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "query" in data
        assert "response" in data
        assert data["query"] == "How is our current sprint health?"


@pytest.mark.integration
class TestAnalyticsSystemIntegration:
    """Integration tests for the complete analytics system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_analytics_flow(self):
        """Test complete analytics flow from data collection to insights."""
        # Initialize components
        data_manager = AnalyticsDataManager(db_path=":memory:")
        await data_manager.initialize()
        
        dashboard = HookMonitoringDashboard()
        await dashboard.start_monitoring()
        
        try:
            # Simulate hook execution data
            execution_records = []
            base_time = datetime.now(timezone.utc)
            
            for i in range(50):
                record = AnalyticsRecord(
                    id=None,
                    timestamp=base_time - timedelta(minutes=i),
                    record_type="hook_execution",
                    team_id="integration-test-team",
                    data={
                        "hook_id": f"hook_{i % 5}",
                        "hook_type": "status_change",
                        "success": i % 10 != 0,  # 90% success rate
                        "execution_time_ms": 800 + (i * 20)
                    },
                    metadata={"test": "integration"}
                )
                execution_records.append(record)
            
            # Store execution data
            await data_manager.store_batch_records(execution_records)
            
            # Verify data was stored
            stored_records = await data_manager.query_records(
                record_type="hook_execution",
                team_id="integration-test-team"
            )
            assert len(stored_records) == 50
            
            # Test aggregation
            aggregated = await data_manager.aggregate_data(
                record_type="hook_execution",
                aggregation_period="hourly",
                team_id="integration-test-team"
            )
            assert aggregated["record_count"] == 50
            
            # Test analytics engines
            productivity_engine = ProductivityAnalyticsEngine()
            intelligence_engine = IntelligenceEngine()
            
            # Generate insights
            insights = await productivity_engine.generate_productivity_insights("integration-test-team")
            assert isinstance(insights, list)
            
            # Test predictive capabilities
            ticket_data = {
                "summary": "Integration test ticket",
                "priority": "medium"
            }
            
            blocker_prediction = await intelligence_engine.predict_blocker_risk(
                "INT-123", "integration-test-team", ticket_data
            )
            assert blocker_prediction.team_id == "integration-test-team"
            
        finally:
            # Cleanup
            await dashboard.stop_monitoring()
            await data_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_dashboard_real_time_updates(self):
        """Test real-time dashboard updates via WebSocket."""
        dashboard = HookMonitoringDashboard()
        await dashboard.start_monitoring()
        
        try:
            # Mock WebSocket connection
            mock_websocket = AsyncMock()
            await dashboard.connect_websocket(mock_websocket)
            
            # Wait for initial data to be sent
            await asyncio.sleep(1)
            
            # Verify WebSocket was called
            assert mock_websocket.send_text.called
            
            # Check that initial data was sent
            call_args = mock_websocket.send_text.call_args_list
            assert len(call_args) > 0
            
            # Verify message format
            message_data = json.loads(call_args[0][0][0])
            assert "type" in message_data
            assert message_data["type"] == "initial_data"
            
        finally:
            await dashboard.stop_monitoring()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])