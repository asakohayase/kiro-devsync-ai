"""
Integration tests for changelog service integration.

Tests the complete integration of changelog services with existing
DevSync AI infrastructure including services, hooks, and database.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from devsync_ai.hooks.changelog_agent_hook import ChangelogAgentHook, ChangelogGenerationConfig
from devsync_ai.core.agent_hooks import HookConfiguration, EnrichedEvent, EventCategory
from devsync_ai.core.changelog_configuration_manager import ChangelogConfigurationManager
from devsync_ai.core.changelog_health_monitor import ChangelogHealthMonitor
from devsync_ai.database.changelog_migration_runner import ChangelogMigrationRunner
from devsync_ai.api.changelog_routes import router as changelog_router


class TestChangelogServiceIntegration:
    """Test suite for changelog service integration."""
    
    @pytest.fixture
    async def mock_database(self):
        """Mock database connection."""
        mock_db = Mock()
        mock_db.execute_raw = AsyncMock()
        mock_db.select = AsyncMock()
        mock_db.insert = AsyncMock()
        mock_db.update = AsyncMock()
        
        with patch('devsync_ai.database.connection.get_database', return_value=mock_db):
            yield mock_db
    
    @pytest.fixture
    def sample_team_config(self):
        """Sample team configuration for testing."""
        return {
            "team_id": "test_team",
            "enabled": True,
            "schedule": {
                "day": "friday",
                "time": "17:00",
                "timezone": "UTC"
            },
            "data_sources": {
                "github": True,
                "jira": True,
                "team_metrics": True
            },
            "distribution": {
                "primary_channel": "#test-updates",
                "secondary_channels": ["#general"]
            }
        }
    
    @pytest.fixture
    def sample_hook_config(self):
        """Sample hook configuration for testing."""
        return HookConfiguration(
            hook_id="test_changelog_hook",
            hook_type="ChangelogAgentHook",
            team_id="test_team",
            enabled=True,
            notification_channels=["#test-updates"],
            metadata={
                "changelog": {
                    "enabled": True,
                    "schedule_day": "friday",
                    "schedule_time": "17:00",
                    "timezone": "UTC",
                    "include_github": True,
                    "include_jira": True,
                    "include_team_metrics": True,
                    "distribution_channels": ["#test-updates"],
                    "template_style": "professional",
                    "audience_type": "technical"
                }
            }
        )
    
    @pytest.fixture
    def sample_enriched_event(self):
        """Sample enriched event for testing."""
        return EnrichedEvent(
            event_id="test_event_123",
            event_type="changelog.scheduled_generation",
            timestamp=datetime.now(),
            jira_event_data={},
            ticket_key="",
            project_key="",
            raw_payload={},
            context_data={"team_id": "test_team"}
        )


class TestChangelogAgentHook(TestChangelogServiceIntegration):
    """Test changelog agent hook integration."""
    
    def test_hook_initialization(self, sample_hook_config):
        """Test changelog agent hook initialization."""
        hook = ChangelogAgentHook("test_hook", sample_hook_config)
        
        assert hook.hook_id == "test_hook"
        assert hook.hook_type == "ChangelogAgentHook"
        assert hook.configuration.team_id == "test_team"
        assert hook.changelog_config.enabled is True
        assert hook.changelog_config.schedule_day == "friday"
        assert hook.changelog_config.include_github is True
    
    async def test_hook_can_handle_scheduled_event(self, sample_hook_config, sample_enriched_event):
        """Test hook can handle scheduled generation events."""
        hook = ChangelogAgentHook("test_hook", sample_hook_config)
        
        # Test scheduled generation event
        sample_enriched_event.event_type = "changelog.scheduled_generation"
        can_handle = await hook.can_handle(sample_enriched_event)
        assert can_handle is True
        
        # Test manual trigger event
        sample_enriched_event.event_type = "changelog.manual_trigger"
        can_handle = await hook.can_handle(sample_enriched_event)
        assert can_handle is True
        
        # Test unrelated event
        sample_enriched_event.event_type = "jira.issue_updated"
        can_handle = await hook.can_handle(sample_enriched_event)
        assert can_handle is False
    
    async def test_hook_configuration_validation(self, sample_hook_config):
        """Test hook configuration validation."""
        hook = ChangelogAgentHook("test_hook", sample_hook_config)
        
        # Valid configuration should pass
        errors = await hook.validate_configuration()
        assert len(errors) == 0
        
        # Invalid schedule day should fail
        hook.changelog_config.schedule_day = "invalid_day"
        errors = await hook.validate_configuration()
        assert any("Invalid schedule_day" in error for error in errors)
        
        # Invalid template style should fail
        hook.changelog_config.template_style = "invalid_style"
        errors = await hook.validate_configuration()
        assert any("Invalid template_style" in error for error in errors)
    
    @patch('devsync_ai.core.intelligent_data_aggregator.IntelligentDataAggregator')
    @patch('devsync_ai.formatters.intelligent_changelog_formatter.IntelligentChangelogFormatter')
    @patch('devsync_ai.core.intelligent_distributor.IntelligentDistributor')
    async def test_hook_execution_scheduled_generation(
        self, 
        mock_distributor_class,
        mock_formatter_class,
        mock_aggregator_class,
        sample_hook_config, 
        sample_enriched_event,
        mock_database
    ):
        """Test hook execution for scheduled generation."""
        # Setup mocks
        mock_aggregator = Mock()
        mock_aggregator.aggregate_weekly_data = AsyncMock(return_value={"test": "data"})
        mock_aggregator_class.return_value = mock_aggregator
        
        mock_formatter = Mock()
        mock_formatter.format_changelog = AsyncMock(return_value={"formatted": "changelog"})
        mock_formatter_class.return_value = mock_formatter
        
        mock_distributor = Mock()
        mock_distributor.distribute_changelog = AsyncMock(return_value={"successful_deliveries": 1})
        mock_distributor_class.return_value = mock_distributor
        
        # Create and execute hook
        hook = ChangelogAgentHook("test_hook", sample_hook_config)
        sample_enriched_event.event_type = "changelog.scheduled_generation"
        
        result = await hook.execute(sample_enriched_event)
        
        # Verify execution
        assert result.status.value == "success"
        assert result.notification_sent is True
        assert "week_start" in result.metadata
        assert "week_end" in result.metadata
        
        # Verify mocks were called
        mock_aggregator.aggregate_weekly_data.assert_called_once()
        mock_formatter.format_changelog.assert_called_once()
        mock_distributor.distribute_changelog.assert_called_once()


class TestChangelogConfigurationManager(TestChangelogServiceIntegration):
    """Test changelog configuration manager integration."""
    
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('yaml.safe_load')
    async def test_configuration_loading(self, mock_yaml_load, mock_open, mock_exists):
        """Test configuration loading with fallback."""
        # Setup mocks
        mock_exists.return_value = True
        mock_yaml_load.return_value = {
            "changelog_system": {"enabled": True},
            "team_changelog_configs": {"test_team": {"enabled": True}}
        }
        
        config_manager = ChangelogConfigurationManager()
        config = await config_manager.load_configuration()
        
        assert config["changelog_system"]["enabled"] is True
        assert "test_team" in config["team_changelog_configs"]
    
    async def test_team_configuration_creation(self, sample_team_config):
        """Test team configuration creation and retrieval."""
        with patch.object(ChangelogConfigurationManager, 'load_configuration') as mock_load:
            mock_load.return_value = {
                "team_changelog_configs": {
                    "test_team": sample_team_config
                }
            }
            
            config_manager = ChangelogConfigurationManager()
            team_config = await config_manager.get_team_configuration("test_team")
            
            assert team_config.team_id == "test_team"
            assert team_config.enabled is True
            assert team_config.schedule.day == "friday"
            assert team_config.distribution.primary_channel == "#test-updates"
    
    async def test_hook_configuration_generation(self, sample_team_config):
        """Test hook configuration generation from team config."""
        with patch.object(ChangelogConfigurationManager, 'get_team_configuration') as mock_get_team:
            from devsync_ai.core.changelog_configuration_manager import TeamChangelogConfig, ChangelogScheduleConfig, ChangelogDistributionConfig
            
            team_config = TeamChangelogConfig(
                team_id="test_team",
                enabled=True,
                schedule=ChangelogScheduleConfig(day="friday", time="17:00"),
                distribution=ChangelogDistributionConfig(
                    primary_channel="#test-updates",
                    secondary_channels=["#general"]
                )
            )
            mock_get_team.return_value = team_config
            
            config_manager = ChangelogConfigurationManager()
            hook_config = await config_manager.create_hook_configuration("test_team")
            
            assert hook_config["hook_id"] == "test_team_changelog"
            assert hook_config["hook_type"] == "ChangelogAgentHook"
            assert hook_config["team_id"] == "test_team"
            assert hook_config["enabled"] is True
            assert "#test-updates" in hook_config["notification_channels"]


class TestChangelogMigrationRunner(TestChangelogServiceIntegration):
    """Test changelog migration runner integration."""
    
    async def test_migration_status_check(self, mock_database):
        """Test migration status checking."""
        # Mock migration table exists
        mock_database.execute_raw.side_effect = [
            [(True,)],  # Migration table exists
            [("003_changelog_history_schema.sql", datetime.now())],  # Applied migrations
            [(True,)],  # Table exists check
            [(True,)],  # Function exists check
            [(True,)]   # View exists check
        ]
        
        migration_runner = ChangelogMigrationRunner()
        status = await migration_runner.get_migration_status()
        
        assert "applied_migrations" in status
        assert "schema_status" in status
        assert len(status["applied_migrations"]) > 0
    
    async def test_schema_verification(self, mock_database):
        """Test schema verification process."""
        # Mock all required objects exist
        mock_database.execute_raw.return_value = [(True,)]
        
        migration_runner = ChangelogMigrationRunner()
        verification = await migration_runner._verify_changelog_schema()
        
        assert verification["overall_status"] in ["success", "incomplete"]
        assert "tables" in verification
        assert "functions" in verification
        assert "views" in verification


class TestChangelogHealthMonitor(TestChangelogServiceIntegration):
    """Test changelog health monitor integration."""
    
    async def test_health_monitor_initialization(self):
        """Test health monitor initialization."""
        health_monitor = ChangelogHealthMonitor()
        
        assert health_monitor.monitored_components
        assert "changelog_generation" in health_monitor.monitored_components
        assert "database_connectivity" in health_monitor.monitored_components
    
    @patch('devsync_ai.services.github.GitHubService')
    @patch('devsync_ai.services.jira.JiraService')
    async def test_external_apis_health_check(self, mock_jira_service, mock_github_service):
        """Test external APIs health checking."""
        # Setup mocks
        mock_github = Mock()
        mock_github.check_rate_limit = AsyncMock(return_value=Mock(remaining=1000, limit=5000, reset_time=datetime.now()))
        mock_github_service.return_value = mock_github
        
        mock_jira = Mock()
        mock_jira.test_authentication = AsyncMock(return_value=Mock(authenticated=True))
        mock_jira_service.return_value = mock_jira
        
        health_monitor = ChangelogHealthMonitor()
        component_health = await health_monitor._check_external_apis_health()
        
        assert component_health.component_name == "external_apis"
        assert component_health.status.value in ["healthy", "degraded", "unhealthy"]
    
    async def test_database_health_check(self, mock_database):
        """Test database health checking."""
        # Mock successful database operations
        mock_database.execute_raw.side_effect = [
            None,  # SELECT 1
            [(2,)],  # Table count check
        ]
        
        health_monitor = ChangelogHealthMonitor()
        component_health = await health_monitor._check_database_health()
        
        assert component_health.component_name == "database_connectivity"
        assert component_health.response_time_ms is not None
        assert component_health.status.value in ["healthy", "degraded", "unhealthy"]
    
    async def test_full_health_check(self, mock_database):
        """Test full health check process."""
        # Mock database operations for health recording
        mock_database.execute_raw.return_value = None
        
        health_monitor = ChangelogHealthMonitor()
        
        # Mock individual component checks to avoid external dependencies
        with patch.object(health_monitor, '_check_component_health') as mock_check:
            from devsync_ai.core.changelog_health_monitor import ComponentHealth, HealthStatus
            
            mock_check.return_value = ComponentHealth(
                component_name="test_component",
                status=HealthStatus.HEALTHY,
                last_check=datetime.now()
            )
            
            report = await health_monitor.perform_full_health_check()
            
            assert report.overall_status.value in ["healthy", "degraded", "unhealthy", "unknown"]
            assert len(report.components) > 0
            assert report.generated_at is not None


class TestChangelogAPIIntegration(TestChangelogServiceIntegration):
    """Test changelog API integration."""
    
    @pytest.fixture
    def mock_fastapi_client(self):
        """Mock FastAPI test client."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(changelog_router, prefix="/changelog")
        
        return TestClient(app)
    
    @patch('devsync_ai.api.routes.verify_api_key')
    async def test_health_endpoint(self, mock_verify_api_key, mock_fastapi_client, mock_database):
        """Test changelog health endpoint."""
        mock_verify_api_key.return_value = True
        
        # Mock migration runner
        with patch('devsync_ai.database.changelog_migration_runner.ChangelogMigrationRunner') as mock_runner_class:
            mock_runner = Mock()
            mock_runner.get_migration_status = AsyncMock(return_value={
                "schema_status": {"overall_status": "success"}
            })
            mock_runner_class.return_value = mock_runner
            
            response = mock_fastapi_client.get("/changelog/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "components" in data
    
    @patch('devsync_ai.api.routes.verify_api_key')
    async def test_configuration_endpoints(self, mock_verify_api_key, mock_fastapi_client):
        """Test configuration management endpoints."""
        mock_verify_api_key.return_value = True
        
        # Mock configuration manager
        with patch('devsync_ai.core.changelog_configuration_manager.ChangelogConfigurationManager') as mock_config_class:
            from devsync_ai.core.changelog_configuration_manager import TeamChangelogConfig, ChangelogScheduleConfig
            
            mock_config_manager = Mock()
            mock_config_manager.get_team_configuration = AsyncMock(return_value=TeamChangelogConfig(
                team_id="test_team",
                enabled=True,
                schedule=ChangelogScheduleConfig(day="friday", time="17:00")
            ))
            mock_config_class.return_value = mock_config_manager
            
            # Test GET configuration
            response = mock_fastapi_client.get("/changelog/config/test_team")
            assert response.status_code == 200
            
            data = response.json()
            assert data["team_id"] == "test_team"
            assert data["enabled"] is True


class TestServiceIntegrationFlow(TestChangelogServiceIntegration):
    """Test complete service integration flow."""
    
    @patch('devsync_ai.core.intelligent_data_aggregator.IntelligentDataAggregator')
    @patch('devsync_ai.formatters.intelligent_changelog_formatter.IntelligentChangelogFormatter')
    @patch('devsync_ai.core.intelligent_distributor.IntelligentDistributor')
    @patch('devsync_ai.services.github.GitHubService')
    @patch('devsync_ai.services.jira.JiraService')
    @patch('devsync_ai.services.slack.SlackService')
    async def test_end_to_end_changelog_generation(
        self,
        mock_slack_service,
        mock_jira_service,
        mock_github_service,
        mock_distributor_class,
        mock_formatter_class,
        mock_aggregator_class,
        mock_database
    ):
        """Test end-to-end changelog generation flow."""
        # Setup service mocks
        mock_github = Mock()
        mock_github.get_weekly_changelog_data = AsyncMock(return_value={"github_data": "test"})
        mock_github_service.return_value = mock_github
        
        mock_jira = Mock()
        mock_jira.get_weekly_changelog_data = AsyncMock(return_value={"jira_data": "test"})
        mock_jira_service.return_value = mock_jira
        
        mock_slack = Mock()
        mock_slack.send_changelog_notification = AsyncMock(return_value={"ok": True})
        mock_slack_service.return_value = mock_slack
        
        # Setup processing mocks
        mock_aggregator = Mock()
        mock_aggregator.aggregate_weekly_data = AsyncMock(return_value={"aggregated": "data"})
        mock_aggregator_class.return_value = mock_aggregator
        
        mock_formatter = Mock()
        mock_formatter.format_changelog = AsyncMock(return_value={"formatted": "changelog"})
        mock_formatter_class.return_value = mock_formatter
        
        mock_distributor = Mock()
        mock_distributor.distribute_changelog = AsyncMock(return_value={
            "successful_deliveries": 1,
            "failed_deliveries": 0
        })
        mock_distributor_class.return_value = mock_distributor
        
        # Create hook and execute
        hook_config = HookConfiguration(
            hook_id="test_hook",
            hook_type="ChangelogAgentHook",
            team_id="test_team",
            enabled=True,
            notification_channels=["#test"],
            metadata={
                "changelog": {
                    "enabled": True,
                    "include_github": True,
                    "include_jira": True,
                    "include_team_metrics": True,
                    "distribution_channels": ["#test"]
                }
            }
        )
        
        hook = ChangelogAgentHook("test_hook", hook_config)
        
        event = EnrichedEvent(
            event_id="test_event",
            event_type="changelog.scheduled_generation",
            timestamp=datetime.now(),
            jira_event_data={},
            ticket_key="",
            project_key="",
            raw_payload={},
            context_data={"team_id": "test_team"}
        )
        
        result = await hook.execute(event)
        
        # Verify complete flow
        assert result.status.value == "success"
        assert result.notification_sent is True
        
        # Verify all components were called
        mock_aggregator.aggregate_weekly_data.assert_called_once()
        mock_formatter.format_changelog.assert_called_once()
        mock_distributor.distribute_changelog.assert_called_once()
    
    async def test_configuration_to_hook_integration(self, sample_team_config):
        """Test configuration manager to hook integration."""
        with patch.object(ChangelogConfigurationManager, 'load_configuration') as mock_load:
            mock_load.return_value = {
                "team_changelog_configs": {
                    "test_team": sample_team_config
                }
            }
            
            # Create configuration manager
            config_manager = ChangelogConfigurationManager()
            
            # Get team configuration
            team_config = await config_manager.get_team_configuration("test_team")
            
            # Generate hook configuration
            hook_config_dict = await config_manager.create_hook_configuration("test_team")
            
            # Create hook configuration object
            hook_config = HookConfiguration(
                hook_id=hook_config_dict["hook_id"],
                hook_type=hook_config_dict["hook_type"],
                team_id=hook_config_dict["team_id"],
                enabled=hook_config_dict["enabled"],
                notification_channels=hook_config_dict["notification_channels"],
                metadata=hook_config_dict["metadata"]
            )
            
            # Create hook
            hook = ChangelogAgentHook(hook_config.hook_id, hook_config)
            
            # Verify integration
            assert hook.configuration.team_id == team_config.team_id
            assert hook.changelog_config.enabled == team_config.enabled
            assert hook.changelog_config.schedule_day == team_config.schedule.day
            assert hook.changelog_config.distribution_channels[0] == team_config.distribution.primary_channel


if __name__ == "__main__":
    pytest.main([__file__, "-v"])