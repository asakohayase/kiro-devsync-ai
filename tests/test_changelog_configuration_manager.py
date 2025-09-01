"""
Comprehensive tests for the Changelog Configuration Manager.

Tests cover configuration loading, validation, runtime updates, versioning,
templates, and all aspects of the advanced configuration management system.
"""

import pytest
import asyncio
import json
import yaml
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import asdict

from devsync_ai.core.changelog_configuration_manager import (
    ChangelogConfigurationManager,
    GlobalChangelogConfig,
    TeamChangelogConfig,
    ScheduleConfig,
    DataSourceConfig,
    ContentConfig,
    DistributionConfig,
    InteractiveConfig,
    NotificationConfig,
    ConfigurationVersion,
    ConfigurationTemplate,
    TemplateStyle,
    AudienceType,
    AnalysisDepth,
    ValidationResult
)
from devsync_ai.core.exceptions import ConfigurationError, ValidationError


class TestChangelogConfigurationManager:
    """Test suite for ChangelogConfigurationManager."""
    
    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary configuration directory."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "changelog").mkdir()
        (config_dir / "templates").mkdir()
        return config_dir
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create configuration manager with temporary directory."""
        return ChangelogConfigurationManager(
            config_directory=str(temp_config_dir),
            environment="test"
        )
    
    @pytest.fixture
    def sample_global_config(self):
        """Sample global configuration."""
        return GlobalChangelogConfig(
            enabled=True,
            debug_mode=False,
            version="1.0.0",
            max_concurrent_generations=5,
            generation_timeout_minutes=10,
            cache_ttl_minutes=60,
            enable_history=True,
            retention_days=365
        )
    
    @pytest.fixture
    def sample_team_config(self):
        """Sample team configuration."""
        return TeamChangelogConfig(
            team_id="engineering",
            team_name="Engineering Team",
            enabled=True,
            version="1.0.0",
            schedule=ScheduleConfig(
                enabled=True,
                day="friday",
                time="16:00",
                timezone="UTC"
            ),
            data_sources={
                "github": DataSourceConfig(enabled=True, analysis_depth=AnalysisDepth.COMPREHENSIVE),
                "jira": DataSourceConfig(enabled=True, analysis_depth=AnalysisDepth.STANDARD),
                "team_metrics": DataSourceConfig(enabled=True)
            },
            content=ContentConfig(
                template_style=TemplateStyle.TECHNICAL,
                audience_type=AudienceType.TECHNICAL,
                include_metrics=True,
                include_contributor_recognition=True,
                max_commits_displayed=20
            ),
            distribution=DistributionConfig(
                primary_channel="#engineering-updates",
                secondary_channels=["#general"],
                export_formats=["slack", "markdown"]
            ),
            interactive=InteractiveConfig(
                enable_feedback_buttons=True,
                enable_drill_down=True
            ),
            notifications=NotificationConfig(
                notify_on_generation=True,
                notify_on_failure=True,
                escalation_channels=["#alerts"]
            )
        )
    
    @pytest.mark.asyncio
    async def test_load_global_configuration_default(self, config_manager):
        """Test loading default global configuration."""
        with patch.object(config_manager, '_load_global_config_from_database', return_value=None):
            with patch.object(config_manager, '_load_global_config_from_file', return_value=None):
                config = await config_manager.load_global_configuration()
                
                assert isinstance(config, GlobalChangelogConfig)
                assert config.enabled is True
                assert config.version == "1.0.0"
                assert config.max_concurrent_generations == 5
    
    @pytest.mark.asyncio
    async def test_load_team_configuration_default(self, config_manager):
        """Test loading default team configuration."""
        team_id = "engineering"
        
        with patch.object(config_manager, '_load_team_config_from_database', return_value=None):
            with patch.object(config_manager, '_load_team_config_from_file', return_value=None):
                config = await config_manager.load_team_configuration(team_id)
                
                assert isinstance(config, TeamChangelogConfig)
                assert config.team_id == team_id
                assert config.enabled is True
                assert config.distribution.primary_channel == f"#{team_id}-updates"
    
    @pytest.mark.asyncio
    async def test_save_global_configuration(self, config_manager, sample_global_config):
        """Test saving global configuration."""
        with patch.object(config_manager, '_save_global_config_to_database') as mock_db_save:
            with patch.object(config_manager, '_save_global_config_to_file') as mock_file_save:
                result = await config_manager.save_global_configuration(sample_global_config)
                
                assert result is True
                mock_db_save.assert_called_once()
                mock_file_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_team_configuration(self, config_manager, sample_team_config):
        """Test saving team configuration."""
        with patch.object(config_manager, '_create_configuration_version') as mock_version:
            with patch.object(config_manager, '_save_team_config_to_database') as mock_db_save:
                with patch.object(config_manager, '_save_team_config_to_file') as mock_file_save:
                    result = await config_manager.save_team_configuration("engineering", sample_team_config)
                    
                    assert result is True
                    mock_version.assert_called_once()
                    mock_db_save.assert_called_once()
                    mock_file_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_team_configuration(self, config_manager, sample_team_config):
        """Test runtime configuration updates."""
        team_id = "engineering"
        updates = {
            "enabled": False,
            "schedule.day": "thursday",
            "content.max_commits_displayed": 30
        }
        
        with patch.object(config_manager, 'load_team_configuration', return_value=sample_team_config):
            with patch.object(config_manager, 'save_team_configuration', return_value=True):
                result = await config_manager.update_team_configuration(team_id, updates)
                
                assert result.valid is True
                assert "Configuration updated successfully" in result.suggestions[0]
    
    @pytest.mark.asyncio
    async def test_validate_global_configuration_valid(self, config_manager, sample_global_config):
        """Test validation of valid global configuration."""
        result = await config_manager.validate_global_configuration(sample_global_config)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_global_configuration_invalid(self, config_manager):
        """Test validation of invalid global configuration."""
        invalid_config = GlobalChangelogConfig(
            max_concurrent_generations=0,  # Invalid: must be >= 1
            generation_timeout_minutes=100,  # Invalid: must be <= 60
            cache_ttl_minutes=2000  # Invalid: must be <= 1440
        )
        
        result = await config_manager.validate_global_configuration(invalid_config)
        
        assert result.valid is False
        assert len(result.errors) >= 3
        assert any("max_concurrent_generations" in error for error in result.errors)
        assert any("generation_timeout_minutes" in error for error in result.errors)
        assert any("cache_ttl_minutes" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_team_configuration_valid(self, config_manager, sample_team_config):
        """Test validation of valid team configuration."""
        result = await config_manager.validate_team_configuration(sample_team_config)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_team_configuration_invalid(self, config_manager):
        """Test validation of invalid team configuration."""
        invalid_config = TeamChangelogConfig(
            team_id="",  # Invalid: empty team_id
            team_name="Test Team",
            schedule=ScheduleConfig(
                day="invalid_day",  # Invalid day
                time="25:00"  # Invalid time
            ),
            content=ContentConfig(
                max_commits_displayed=0  # Invalid: must be >= 1
            ),
            distribution=DistributionConfig(
                primary_channel="invalid_channel"  # Invalid: doesn't start with #
            )
        )
        
        result = await config_manager.validate_team_configuration(invalid_config)
        
        assert result.valid is False
        assert len(result.errors) >= 4
    
    def test_validate_schedule_config(self, config_manager):
        """Test schedule configuration validation."""
        # Valid schedule
        valid_schedule = ScheduleConfig(
            day="friday",
            time="16:00",
            timezone="UTC",
            max_retry_attempts=3,
            retry_delay_minutes=30
        )
        
        result = config_manager._validate_schedule_config(valid_schedule)
        assert result.valid is True
        
        # Invalid schedule
        invalid_schedule = ScheduleConfig(
            day="invalid_day",
            time="25:00",
            max_retry_attempts=20,  # Too high
            retry_delay_minutes=2000  # Too high
        )
        
        result = config_manager._validate_schedule_config(invalid_schedule)
        assert result.valid is False
        assert len(result.errors) >= 4
    
    def test_validate_data_source_config(self, config_manager):
        """Test data source configuration validation."""
        # Valid config
        valid_config = DataSourceConfig(
            enabled=True,
            timeout_seconds=60,
            retry_attempts=3,
            cache_ttl_minutes=30
        )
        
        result = config_manager._validate_data_source_config(valid_config, "github")
        assert result.valid is True
        
        # Invalid config
        invalid_config = DataSourceConfig(
            timeout_seconds=5,  # Too low
            retry_attempts=20,  # Too high
            cache_ttl_minutes=2000  # Too high
        )
        
        result = config_manager._validate_data_source_config(invalid_config, "github")
        assert result.valid is False
        assert len(result.errors) >= 3
    
    def test_validate_content_config(self, config_manager):
        """Test content configuration validation."""
        # Valid config
        valid_config = ContentConfig(
            max_commits_displayed=20,
            max_tickets_displayed=15,
            max_contributors_highlighted=10
        )
        
        result = config_manager._validate_content_config(valid_config)
        assert result.valid is True
        
        # Invalid config
        invalid_config = ContentConfig(
            max_commits_displayed=0,  # Too low
            max_tickets_displayed=200,  # Too high
            max_contributors_highlighted=100  # Too high
        )
        
        result = config_manager._validate_content_config(invalid_config)
        assert result.valid is False
        assert len(result.errors) >= 3
    
    def test_validate_distribution_config(self, config_manager):
        """Test distribution configuration validation."""
        # Valid config
        valid_config = DistributionConfig(
            primary_channel="#engineering-updates",
            secondary_channels=["#general", "#alerts"],
            webhook_urls=["https://example.com/webhook"]
        )
        
        result = config_manager._validate_distribution_config(valid_config)
        assert result.valid is True
        
        # Invalid config
        invalid_config = DistributionConfig(
            primary_channel="",  # Empty
            secondary_channels=["invalid_channel"],  # No #
            webhook_urls=["invalid_url"]  # Invalid URL
        )
        
        result = config_manager._validate_distribution_config(invalid_config)
        assert result.valid is False
        assert len(result.errors) >= 2
    
    def test_validate_notification_config(self, config_manager):
        """Test notification configuration validation."""
        # Valid config
        valid_config = NotificationConfig(
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
            escalation_channels=["#alerts"]
        )
        
        result = config_manager._validate_notification_config(valid_config)
        assert result.valid is True
        
        # Invalid config
        invalid_config = NotificationConfig(
            quiet_hours_enabled=True,
            quiet_hours_start="25:00",  # Invalid time
            quiet_hours_end="invalid",  # Invalid time
            escalation_channels=["invalid_channel"]  # No #
        )
        
        result = config_manager._validate_notification_config(invalid_config)
        assert result.valid is False
        assert len(result.errors) >= 2
    
    def test_is_valid_time_format(self, config_manager):
        """Test time format validation."""
        assert config_manager._is_valid_time_format("16:00") is True
        assert config_manager._is_valid_time_format("00:00") is True
        assert config_manager._is_valid_time_format("23:59") is True
        
        assert config_manager._is_valid_time_format("24:00") is False
        assert config_manager._is_valid_time_format("16:60") is False
        assert config_manager._is_valid_time_format("invalid") is False
        assert config_manager._is_valid_time_format("16") is False
    
    @pytest.mark.asyncio
    async def test_create_team_from_template(self, config_manager, sample_team_config):
        """Test creating team configuration from template."""
        template = ConfigurationTemplate(
            template_id="engineering_default",
            name="Engineering Default",
            description="Default engineering template",
            category="engineering",
            template_config=sample_team_config
        )
        
        with patch.object(config_manager, 'load_configuration_template', return_value=template):
            with patch.object(config_manager, 'save_team_configuration', return_value=True):
                result = await config_manager.create_team_from_template(
                    "new_team",
                    "engineering_default",
                    {"team_name": "New Team"}
                )
                
                assert result.valid is True
                assert "created from template" in result.suggestions[0]
    
    @pytest.mark.asyncio
    async def test_rollback_team_configuration(self, config_manager, sample_team_config):
        """Test configuration rollback."""
        version_id = "engineering_20240816_120000"
        
        with patch.object(config_manager, '_load_configuration_version', return_value=sample_team_config):
            with patch.object(config_manager, 'save_team_configuration', return_value=True):
                result = await config_manager.rollback_team_configuration("engineering", version_id)
                
                assert result.valid is True
                assert "rolled back to version" in result.suggestions[0]
    
    @pytest.mark.asyncio
    async def test_export_team_configuration_yaml(self, config_manager, sample_team_config):
        """Test exporting team configuration as YAML."""
        with patch.object(config_manager, 'load_team_configuration', return_value=sample_team_config):
            result = await config_manager.export_team_configuration("engineering", "yaml")
            
            assert result is not None
            assert isinstance(result, str)
            
            # Verify it's valid YAML
            parsed = yaml.safe_load(result)
            assert parsed['team_id'] == "engineering"
            assert parsed['team_name'] == "Engineering Team"
    
    @pytest.mark.asyncio
    async def test_export_team_configuration_json(self, config_manager, sample_team_config):
        """Test exporting team configuration as JSON."""
        with patch.object(config_manager, 'load_team_configuration', return_value=sample_team_config):
            result = await config_manager.export_team_configuration("engineering", "json")
            
            assert result is not None
            assert isinstance(result, str)
            
            # Verify it's valid JSON
            parsed = json.loads(result)
            assert parsed['team_id'] == "engineering"
            assert parsed['team_name'] == "Engineering Team"
    
    @pytest.mark.asyncio
    async def test_import_team_configuration_yaml(self, config_manager):
        """Test importing team configuration from YAML."""
        config_yaml = """
        team_id: imported_team
        team_name: Imported Team
        enabled: true
        version: "1.0.0"
        schedule:
          enabled: true
          day: friday
          time: "16:00"
          timezone: UTC
        distribution:
          primary_channel: "#imported-updates"
        """
        
        with patch.object(config_manager, 'save_team_configuration', return_value=True):
            result = await config_manager.import_team_configuration("imported_team", config_yaml, "yaml")
            
            assert result.valid is True
            assert "imported successfully" in result.suggestions[0]
    
    @pytest.mark.asyncio
    async def test_import_team_configuration_json(self, config_manager):
        """Test importing team configuration from JSON."""
        config_json = json.dumps({
            "team_id": "imported_team",
            "team_name": "Imported Team",
            "enabled": True,
            "version": "1.0.0",
            "schedule": {
                "enabled": True,
                "day": "friday",
                "time": "16:00",
                "timezone": "UTC"
            },
            "distribution": {
                "primary_channel": "#imported-updates"
            }
        })
        
        with patch.object(config_manager, 'save_team_configuration', return_value=True):
            result = await config_manager.import_team_configuration("imported_team", config_json, "json")
            
            assert result.valid is True
            assert "imported successfully" in result.suggestions[0]
    
    def test_apply_configuration_updates(self, config_manager, sample_team_config):
        """Test applying configuration updates."""
        updates = {
            "enabled": False,
            "team_name": "Updated Team Name",
            "schedule.day": "thursday",
            "content.max_commits_displayed": 30
        }
        
        updated_config = config_manager._apply_configuration_updates(sample_team_config, updates)
        
        assert updated_config.enabled is False
        assert updated_config.team_name == "Updated Team Name"
        # Note: Nested updates would need more sophisticated handling in the actual implementation
    
    def test_cache_functionality(self, config_manager):
        """Test configuration caching."""
        # Test cache validity
        assert config_manager._is_cache_valid("nonexistent") is False
        
        # Set cache timestamp
        config_manager._cache_timestamps["test"] = datetime.now(timezone.utc)
        assert config_manager._is_cache_valid("test") is True
        
        # Test expired cache
        config_manager._cache_timestamps["expired"] = datetime.now(timezone.utc) - timedelta(minutes=10)
        assert config_manager._is_cache_valid("expired") is False
    
    def test_change_listeners(self, config_manager, sample_team_config):
        """Test configuration change listeners."""
        listener_called = False
        
        def test_listener(team_id, config):
            nonlocal listener_called
            listener_called = True
            assert team_id == "engineering"
            assert isinstance(config, TeamChangelogConfig)
        
        config_manager.add_change_listener(test_listener)
        
        # Simulate configuration change
        for listener in config_manager._change_listeners:
            listener("engineering", sample_team_config)
        
        assert listener_called is True
    
    def test_global_change_listeners(self, config_manager, sample_global_config):
        """Test global configuration change listeners."""
        listener_called = False
        
        def test_listener(config):
            nonlocal listener_called
            listener_called = True
            assert isinstance(config, GlobalChangelogConfig)
        
        config_manager.add_global_change_listener(test_listener)
        
        # Simulate global configuration change
        for listener in config_manager._global_change_listeners:
            listener(sample_global_config)
        
        assert listener_called is True
    
    @pytest.mark.asyncio
    async def test_configuration_file_loading(self, config_manager, temp_config_dir, sample_team_config):
        """Test loading configuration from files."""
        # Create test configuration file
        config_file = temp_config_dir / "changelog" / "engineering_test.yaml"
        config_data = asdict(sample_team_config)
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Test loading
        loaded_config = await config_manager._load_team_config_from_file("engineering")
        
        assert loaded_config is not None
        assert loaded_config.team_id == "engineering"
        assert loaded_config.team_name == "Engineering Team"
    
    @pytest.mark.asyncio
    async def test_configuration_file_saving(self, config_manager, temp_config_dir, sample_team_config):
        """Test saving configuration to files."""
        await config_manager._save_team_config_to_file(sample_team_config)
        
        # Check if file was created
        config_file = temp_config_dir / "changelog" / "engineering_test.yaml"
        assert config_file.exists()
        
        # Verify content
        with open(config_file, 'r') as f:
            saved_data = yaml.safe_load(f)
        
        assert saved_data['team_id'] == "engineering"
        assert saved_data['team_name'] == "Engineering Team"
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_save(self, config_manager):
        """Test error handling for invalid configuration save."""
        invalid_config = TeamChangelogConfig(
            team_id="",  # Invalid empty team_id
            team_name="Test Team"
        )
        
        result = await config_manager.save_team_configuration("test", invalid_config)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_error_handling_database_failure(self, config_manager, sample_team_config):
        """Test error handling for database failures."""
        with patch.object(config_manager, '_save_team_config_to_database', side_effect=Exception("DB Error")):
            result = await config_manager.save_team_configuration("engineering", sample_team_config)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_configuration_versioning(self, config_manager, sample_team_config):
        """Test configuration versioning functionality."""
        with patch('devsync_ai.database.connection.get_database') as mock_db:
            mock_db_instance = AsyncMock()
            mock_db.return_value = mock_db_instance
            
            await config_manager._create_configuration_version(sample_team_config)
            
            # Verify database calls were made
            mock_db_instance.insert.assert_called_once()
            mock_db_instance.update.assert_called_once()
    
    def test_configuration_data_classes(self):
        """Test configuration data classes and their defaults."""
        # Test ScheduleConfig defaults
        schedule = ScheduleConfig()
        assert schedule.enabled is True
        assert schedule.day == "friday"
        assert schedule.time == "17:00"
        assert schedule.timezone == "UTC"
        
        # Test DataSourceConfig defaults
        data_source = DataSourceConfig()
        assert data_source.enabled is True
        assert data_source.analysis_depth == AnalysisDepth.STANDARD
        assert data_source.timeout_seconds == 60
        
        # Test ContentConfig defaults
        content = ContentConfig()
        assert content.template_style == TemplateStyle.PROFESSIONAL
        assert content.audience_type == AudienceType.TECHNICAL
        assert content.include_metrics is True
        
        # Test DistributionConfig
        distribution = DistributionConfig(primary_channel="#test")
        assert distribution.primary_channel == "#test"
        assert distribution.secondary_channels == []
        assert distribution.export_formats == ["slack", "markdown"]
        
        # Test InteractiveConfig defaults
        interactive = InteractiveConfig()
        assert interactive.enable_feedback_buttons is True
        assert interactive.enable_drill_down is True
        assert interactive.feedback_timeout_hours == 48
        
        # Test NotificationConfig defaults
        notifications = NotificationConfig()
        assert notifications.notify_on_generation is True
        assert notifications.notify_on_failure is True
        assert notifications.quiet_hours_enabled is True
    
    def test_enum_values(self):
        """Test enum values are correct."""
        # Test TemplateStyle enum
        assert TemplateStyle.PROFESSIONAL.value == "professional"
        assert TemplateStyle.TECHNICAL.value == "technical"
        assert TemplateStyle.EXECUTIVE.value == "executive"
        
        # Test AudienceType enum
        assert AudienceType.TECHNICAL.value == "technical"
        assert AudienceType.BUSINESS.value == "business"
        assert AudienceType.MIXED.value == "mixed"
        
        # Test AnalysisDepth enum
        assert AnalysisDepth.BASIC.value == "basic"
        assert AnalysisDepth.STANDARD.value == "standard"
        assert AnalysisDepth.COMPREHENSIVE.value == "comprehensive"


class TestConfigurationIntegration:
    """Integration tests for configuration management."""
    
    @pytest.fixture
    def config_manager(self, tmp_path):
        """Create configuration manager for integration tests."""
        return ChangelogConfigurationManager(
            config_directory=str(tmp_path / "config"),
            environment="integration_test"
        )
    
    @pytest.mark.asyncio
    async def test_full_configuration_lifecycle(self, config_manager):
        """Test complete configuration lifecycle."""
        team_id = "integration_test_team"
        
        # 1. Create initial configuration
        initial_config = TeamChangelogConfig(
            team_id=team_id,
            team_name="Integration Test Team",
            enabled=True,
            distribution=DistributionConfig(primary_channel="#test-updates")
        )
        
        with patch.object(config_manager, '_save_team_config_to_database'):
            with patch.object(config_manager, '_create_configuration_version'):
                # Save initial configuration
                result = await config_manager.save_team_configuration(team_id, initial_config)
                assert result is True
        
        # 2. Load configuration
        with patch.object(config_manager, '_load_team_config_from_database', return_value=initial_config):
            loaded_config = await config_manager.load_team_configuration(team_id)
            assert loaded_config.team_id == team_id
            assert loaded_config.team_name == "Integration Test Team"
        
        # 3. Update configuration
        updates = {
            "enabled": False,
            "team_name": "Updated Integration Test Team"
        }
        
        with patch.object(config_manager, 'load_team_configuration', return_value=initial_config):
            with patch.object(config_manager, 'save_team_configuration', return_value=True):
                update_result = await config_manager.update_team_configuration(team_id, updates)
                assert update_result.valid is True
        
        # 4. Export configuration
        with patch.object(config_manager, 'load_team_configuration', return_value=initial_config):
            exported_yaml = await config_manager.export_team_configuration(team_id, "yaml")
            assert exported_yaml is not None
            assert team_id in exported_yaml
        
        # 5. Import configuration
        with patch.object(config_manager, 'save_team_configuration', return_value=True):
            import_result = await config_manager.import_team_configuration(
                "imported_team", 
                exported_yaml, 
                "yaml"
            )
            assert import_result.valid is True
    
    @pytest.mark.asyncio
    async def test_configuration_validation_integration(self, config_manager):
        """Test integrated configuration validation."""
        # Test with various invalid configurations
        test_cases = [
            {
                "name": "Empty team_id",
                "config": TeamChangelogConfig(team_id="", team_name="Test"),
                "should_be_valid": False
            },
            {
                "name": "Invalid schedule",
                "config": TeamChangelogConfig(
                    team_id="test",
                    team_name="Test",
                    schedule=ScheduleConfig(day="invalid", time="25:00")
                ),
                "should_be_valid": False
            },
            {
                "name": "Valid configuration",
                "config": TeamChangelogConfig(
                    team_id="test",
                    team_name="Test Team",
                    distribution=DistributionConfig(primary_channel="#test")
                ),
                "should_be_valid": True
            }
        ]
        
        for case in test_cases:
            result = await config_manager.validate_team_configuration(case["config"])
            assert result.valid == case["should_be_valid"], f"Failed for case: {case['name']}"
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_fallbacks(self, config_manager):
        """Test error recovery and fallback mechanisms."""
        team_id = "error_test_team"
        
        # Test database failure fallback to file
        with patch.object(config_manager, '_load_team_config_from_database', side_effect=Exception("DB Error")):
            with patch.object(config_manager, '_load_team_config_from_file', return_value=None):
                config = await config_manager.load_team_configuration(team_id)
                
                # Should fall back to default configuration
                assert config.team_id == team_id
                assert config.enabled is True
        
        # Test file save failure
        with patch.object(config_manager, '_save_team_config_to_file', side_effect=Exception("File Error")):
            with patch.object(config_manager, '_save_team_config_to_database'):
                with patch.object(config_manager, '_create_configuration_version'):
                    # Should still succeed if database save works
                    test_config = TeamChangelogConfig(
                        team_id=team_id,
                        team_name="Test Team",
                        distribution=DistributionConfig(primary_channel="#test")
                    )
                    result = await config_manager.save_team_configuration(team_id, test_config)
                    # The save should still succeed despite file save failure
                    assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])