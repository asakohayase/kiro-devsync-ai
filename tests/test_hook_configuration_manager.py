"""
Tests for Hook Configuration Manager.

This module tests the comprehensive hook configuration management system
including team-specific rules, validation, database storage, and APIs.
"""

import pytest
import asyncio
import tempfile
import yaml
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from devsync_ai.core.hook_configuration_manager import (
    HookConfigurationManager,
    TeamConfiguration,
    HookSettings,
    ValidationResult,
    ConfigurationUpdateResult
)
from devsync_ai.core.exceptions import ConfigurationError


@pytest.fixture
def temp_config_dir():
    """Create temporary configuration directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_team_config():
    """Sample team configuration data."""
    return {
        'team_id': 'engineering',
        'team_name': 'Engineering Team',
        'enabled': True,
        'version': '1.0.0',
        'default_channels': {
            'status_change': '#dev-updates',
            'assignment': '#assignments',
            'comment': '#discussions',
            'blocker': '#alerts',
            'general': '#engineering'
        },
        'notification_preferences': {
            'batch_threshold': 3,
            'batch_timeout_minutes': 5,
            'quiet_hours': {
                'enabled': True,
                'start': '22:00',
                'end': '08:00'
            },
            'weekend_notifications': False
        },
        'business_hours': {
            'start': '09:00',
            'end': '17:00',
            'timezone': 'America/New_York',
            'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        },
        'escalation_rules': [
            {
                'condition': 'urgency == "critical"',
                'escalate_after_minutes': 15,
                'escalate_to': ['#alerts', '#management']
            }
        ],
        'rules': [
            {
                'rule_id': 'critical_blocker_rule',
                'name': 'Critical and Blocker Issues',
                'description': 'Immediately route critical and blocker issues',
                'hook_types': ['StatusChangeHook', 'AssignmentHook', 'CommentHook'],
                'enabled': True,
                'priority': 100,
                'conditions': {
                    'logic': 'or',
                    'conditions': [
                        {
                            'field': 'ticket.priority.name',
                            'operator': 'in',
                            'value': ['Critical', 'Blocker', 'Highest']
                        },
                        {
                            'field': 'event.classification.urgency',
                            'operator': 'equals',
                            'value': 'critical'
                        }
                    ]
                },
                'metadata': {
                    'channels': ['#alerts', '#engineering'],
                    'urgency_override': 'critical'
                }
            }
        ],
        'last_updated': datetime.now(timezone.utc),
        'metadata': {}
    }


class TestHookConfigurationManager:
    """Test cases for HookConfigurationManager."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, temp_config_dir):
        """Test configuration manager initialization."""
        manager = HookConfigurationManager(str(temp_config_dir))
        
        assert manager.config_directory == temp_config_dir
        assert manager._config_cache == {}
        assert manager._cache_expiry == {}
    
    @pytest.mark.asyncio
    async def test_load_from_file(self, temp_config_dir, sample_team_config):
        """Test loading configuration from YAML file."""
        # Create test configuration file
        config_file = temp_config_dir / "team_engineering_hooks.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_team_config, f)
        
        manager = HookConfigurationManager(str(temp_config_dir))
        
        with patch('devsync_ai.core.hook_configuration_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_conn.select.return_value = []  # No database config
            mock_db.return_value = mock_conn
            
            config = await manager.load_team_configuration('engineering')
            
            assert config.team_id == 'engineering'
            assert config.team_name == 'Engineering Team'
            assert config.enabled is True
            assert len(config.rules) == 1
            assert config.rules[0]['rule_id'] == 'critical_blocker_rule'
    
    @pytest.mark.asyncio
    async def test_load_from_database(self, temp_config_dir, sample_team_config):
        """Test loading configuration from database."""
        manager = HookConfigurationManager(str(temp_config_dir))
        
        with patch('devsync_ai.core.hook_configuration_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_conn.select.return_value = [{
                'configuration': sample_team_config,
                'enabled': True,
                'version': '1.0.0',
                'updated_at': datetime.now(timezone.utc)
            }]
            mock_db.return_value = mock_conn
            
            config = await manager.load_team_configuration('engineering')
            
            assert config.team_id == 'engineering'
            assert config.team_name == 'Engineering Team'
            assert config.enabled is True
    
    @pytest.mark.asyncio
    async def test_default_configuration(self, temp_config_dir):
        """Test default configuration generation."""
        manager = HookConfigurationManager(str(temp_config_dir))
        
        with patch('devsync_ai.core.hook_configuration_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_conn.select.return_value = []  # No database config
            mock_db.return_value = mock_conn
            
            config = await manager.load_team_configuration('test_team')
            
            assert config.team_id == 'test_team'
            assert config.team_name == 'Test_Team Team'
            assert config.enabled is True
            assert '#test_team-updates' in config.default_channels['status_change']
            assert len(config.rules) == 1  # Default rule
    
    @pytest.mark.asyncio
    async def test_configuration_caching(self, temp_config_dir, sample_team_config):
        """Test configuration caching mechanism."""
        config_file = temp_config_dir / "team_engineering_hooks.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_team_config, f)
        
        manager = HookConfigurationManager(str(temp_config_dir))
        
        with patch('devsync_ai.core.hook_configuration_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_conn.select.return_value = []
            mock_db.return_value = mock_conn
            
            # First load
            config1 = await manager.load_team_configuration('engineering')
            
            # Second load should use cache
            config2 = await manager.load_team_configuration('engineering')
            
            assert config1 is config2  # Same object from cache
            assert 'engineering' in manager._config_cache
    
    @pytest.mark.asyncio
    async def test_update_team_rules(self, temp_config_dir, sample_team_config):
        """Test updating team rules."""
        manager = HookConfigurationManager(str(temp_config_dir))
        
        new_rules = [
            {
                'rule_id': 'new_rule',
                'name': 'New Rule',
                'description': 'A new test rule',
                'hook_types': ['StatusChangeHook'],
                'enabled': True,
                'priority': 50,
                'conditions': {
                    'logic': 'and',
                    'conditions': [
                        {
                            'field': 'ticket.priority.name',
                            'operator': 'equals',
                            'value': 'High'
                        }
                    ]
                },
                'metadata': {
                    'channels': ['#test']
                }
            }
        ]
        
        with patch('devsync_ai.core.hook_configuration_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_conn.select.return_value = [{
                'configuration': sample_team_config,
                'enabled': True,
                'version': '1.0.0',
                'updated_at': datetime.now(timezone.utc)
            }]
            mock_conn.upsert = AsyncMock()
            mock_db.return_value = mock_conn
            
            result = await manager.update_team_rules('engineering', new_rules)
            
            assert result.success is True
            assert result.team_id == 'engineering'
            assert 'rules' in result.updated_fields
            assert result.validation_result.valid is True
    
    @pytest.mark.asyncio
    async def test_update_team_configuration(self, temp_config_dir, sample_team_config):
        """Test updating team configuration."""
        manager = HookConfigurationManager(str(temp_config_dir))
        
        updates = {
            'team_name': 'Updated Engineering Team',
            'enabled': False,
            'notification_preferences': {
                'batch_threshold': 5,
                'batch_timeout_minutes': 10
            }
        }
        
        with patch('devsync_ai.core.hook_configuration_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_conn.select.return_value = [{
                'configuration': sample_team_config,
                'enabled': True,
                'version': '1.0.0',
                'updated_at': datetime.now(timezone.utc)
            }]
            mock_conn.upsert = AsyncMock()
            mock_db.return_value = mock_conn
            
            result = await manager.update_team_configuration('engineering', updates)
            
            assert result.success is True
            assert result.team_id == 'engineering'
            assert 'team_name' in result.updated_fields
            assert 'enabled' in result.updated_fields
    
    @pytest.mark.asyncio
    async def test_get_hook_settings(self, temp_config_dir, sample_team_config):
        """Test getting hook-specific settings."""
        manager = HookConfigurationManager(str(temp_config_dir))
        
        with patch('devsync_ai.core.hook_configuration_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_conn.select.return_value = [{
                'configuration': sample_team_config,
                'enabled': True,
                'version': '1.0.0',
                'updated_at': datetime.now(timezone.utc)
            }]
            mock_db.return_value = mock_conn
            
            settings = await manager.get_hook_settings('StatusChangeHook', 'engineering')
            
            assert settings.hook_type == 'StatusChangeHook'
            assert settings.enabled is True
            assert len(settings.execution_conditions) > 0
            assert '#alerts' in settings.notification_channels
    
    @pytest.mark.asyncio
    async def test_validate_configuration_valid(self, sample_team_config):
        """Test configuration validation with valid config."""
        manager = HookConfigurationManager()
        config = manager._parse_configuration_data(sample_team_config)
        
        result = await manager.validate_configuration(config)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_configuration_invalid(self):
        """Test configuration validation with invalid config."""
        manager = HookConfigurationManager()
        
        invalid_config_data = {
            'team_id': '',  # Empty team_id
            'team_name': 'Test Team',
            'enabled': True,
            'version': '1.0.0',
            'default_channels': {
                'status_change': 'invalid-channel'  # Missing #
            },
            'notification_preferences': {
                'batch_threshold': 150  # Invalid threshold
            },
            'business_hours': {
                'start': '25:00',  # Invalid time
                'end': '17:00'
            },
            'escalation_rules': [],
            'rules': [],
            'last_updated': datetime.now(timezone.utc),
            'metadata': {}
        }
        
        config = manager._parse_configuration_data(invalid_config_data)
        result = await manager.validate_configuration(config)
        
        assert result.valid is False
        assert len(result.errors) > 0
        assert any('Team ID is required' in error for error in result.errors)
        assert any('Invalid start time format' in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_rules_valid(self):
        """Test rule validation with valid rules."""
        manager = HookConfigurationManager()
        
        valid_rules = [
            {
                'rule_id': 'test_rule',
                'name': 'Test Rule',
                'hook_types': ['StatusChangeHook'],
                'priority': 50,
                'conditions': {
                    'logic': 'and',
                    'conditions': [
                        {
                            'field': 'ticket.priority.name',
                            'operator': 'equals',
                            'value': 'High'
                        }
                    ]
                },
                'metadata': {
                    'channels': ['#test']
                }
            }
        ]
        
        result = await manager.validate_rules(valid_rules)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_rules_invalid(self):
        """Test rule validation with invalid rules."""
        manager = HookConfigurationManager()
        
        invalid_rules = [
            {
                # Missing rule_id
                'name': 'Test Rule',
                'hook_types': 'not_a_list',  # Should be list
                'priority': 150,  # Invalid priority
                'conditions': {
                    'logic': 'invalid',  # Invalid logic
                    'conditions': [
                        {
                            # Missing field
                            'operator': 'invalid_operator',  # Invalid operator
                            'value': 'High'
                        }
                    ]
                },
                'metadata': {
                    'channels': 'not_a_list'  # Should be list
                }
            }
        ]
        
        result = await manager.validate_rules(invalid_rules)
        
        assert result.valid is False
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_export_team_configuration(self, temp_config_dir, sample_team_config):
        """Test exporting team configuration."""
        manager = HookConfigurationManager(str(temp_config_dir))
        
        with patch('devsync_ai.core.hook_configuration_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_conn.select.return_value = [{
                'configuration': sample_team_config,
                'enabled': True,
                'version': '1.0.0',
                'updated_at': datetime.now(timezone.utc)
            }]
            mock_db.return_value = mock_conn
            
            exported = await manager.export_team_configuration('engineering')
            
            assert exported is not None
            assert exported['team_id'] == 'engineering'
            assert exported['team_name'] == 'Engineering Team'
            assert 'rules' in exported
            assert 'default_channels' in exported
    
    @pytest.mark.asyncio
    async def test_import_team_configuration(self, temp_config_dir, sample_team_config):
        """Test importing team configuration."""
        manager = HookConfigurationManager(str(temp_config_dir))
        
        with patch('devsync_ai.core.hook_configuration_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_conn.upsert = AsyncMock()
            mock_db.return_value = mock_conn
            
            result = await manager.import_team_configuration('engineering', sample_team_config)
            
            assert result.success is True
            assert result.team_id == 'engineering'
            assert 'all' in result.updated_fields
    
    @pytest.mark.asyncio
    async def test_delete_team_configuration(self, temp_config_dir):
        """Test deleting team configuration."""
        manager = HookConfigurationManager(str(temp_config_dir))
        
        with patch('devsync_ai.core.hook_configuration_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_conn.delete.return_value = [{'team_id': 'engineering'}]
            mock_db.return_value = mock_conn
            
            result = await manager.delete_team_configuration('engineering')
            
            assert result is True
            mock_conn.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_all_team_configurations(self, temp_config_dir, sample_team_config):
        """Test getting all team configurations."""
        manager = HookConfigurationManager(str(temp_config_dir))
        
        with patch('devsync_ai.core.hook_configuration_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_conn.select.return_value = [
                {
                    'team_id': 'engineering',
                    'configuration': sample_team_config,
                    'enabled': True,
                    'version': '1.0.0',
                    'updated_at': datetime.now(timezone.utc)
                }
            ]
            mock_db.return_value = mock_conn
            
            configs = await manager.get_all_team_configurations()
            
            assert len(configs) == 1
            assert configs[0].team_id == 'engineering'
    
    def test_time_format_validation(self):
        """Test time format validation."""
        manager = HookConfigurationManager()
        
        assert manager._is_valid_time_format('09:00') is True
        assert manager._is_valid_time_format('23:59') is True
        assert manager._is_valid_time_format('00:00') is True
        
        assert manager._is_valid_time_format('25:00') is False
        assert manager._is_valid_time_format('12:60') is False
        assert manager._is_valid_time_format('invalid') is False
        assert manager._is_valid_time_format('9:00') is True  # Single digit hour
    
    @pytest.mark.asyncio
    async def test_configuration_error_handling(self, temp_config_dir):
        """Test error handling in configuration loading."""
        manager = HookConfigurationManager(str(temp_config_dir))
        
        with patch('devsync_ai.core.hook_configuration_manager.get_database') as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            # Should fall back to default configuration
            config = await manager.load_team_configuration('test_team')
            
            assert config.team_id == 'test_team'
            assert config.team_name == 'Test_Team Team'
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, temp_config_dir, sample_team_config):
        """Test cache invalidation after updates."""
        manager = HookConfigurationManager(str(temp_config_dir))
        
        with patch('devsync_ai.core.hook_configuration_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_conn.select.return_value = [{
                'configuration': sample_team_config,
                'enabled': True,
                'version': '1.0.0',
                'updated_at': datetime.now(timezone.utc)
            }]
            mock_conn.upsert = AsyncMock()
            mock_db.return_value = mock_conn
            
            # Load configuration to cache it
            await manager.load_team_configuration('engineering')
            assert 'engineering' in manager._config_cache
            
            # Update configuration should invalidate cache
            await manager.update_team_configuration('engineering', {'team_name': 'Updated'})
            assert 'engineering' not in manager._config_cache
    
    @pytest.mark.asyncio
    async def test_nested_condition_validation(self):
        """Test validation of nested rule conditions."""
        manager = HookConfigurationManager()
        
        nested_conditions = {
            'logic': 'and',
            'conditions': [
                {
                    'field': 'ticket.priority.name',
                    'operator': 'equals',
                    'value': 'High'
                },
                {
                    'logic': 'or',
                    'conditions': [
                        {
                            'field': 'ticket.status.name',
                            'operator': 'equals',
                            'value': 'In Progress'
                        },
                        {
                            'field': 'ticket.status.name',
                            'operator': 'equals',
                            'value': 'Blocked'
                        }
                    ]
                }
            ]
        }
        
        result = manager._validate_rule_conditions(nested_conditions, "Test Rule")
        
        assert result.valid is True
        assert len(result.errors) == 0


class TestHookSettings:
    """Test cases for HookSettings data class."""
    
    def test_hook_settings_creation(self):
        """Test HookSettings creation."""
        settings = HookSettings(
            hook_type='StatusChangeHook',
            enabled=True,
            execution_conditions=[{'field': 'test', 'operator': 'equals', 'value': 'test'}],
            notification_channels=['#test'],
            rate_limits={'max_per_hour': 100},
            retry_policy={'max_attempts': 3}
        )
        
        assert settings.hook_type == 'StatusChangeHook'
        assert settings.enabled is True
        assert len(settings.execution_conditions) == 1
        assert '#test' in settings.notification_channels


class TestValidationResult:
    """Test cases for ValidationResult data class."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation."""
        result = ValidationResult(
            valid=False,
            errors=['Error 1', 'Error 2'],
            warnings=['Warning 1'],
            suggestions=['Suggestion 1']
        )
        
        assert result.valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert len(result.suggestions) == 1


class TestConfigurationUpdateResult:
    """Test cases for ConfigurationUpdateResult data class."""
    
    def test_configuration_update_result_creation(self):
        """Test ConfigurationUpdateResult creation."""
        validation_result = ValidationResult(valid=True)
        
        result = ConfigurationUpdateResult(
            success=True,
            team_id='engineering',
            updated_fields=['rules', 'channels'],
            validation_result=validation_result
        )
        
        assert result.success is True
        assert result.team_id == 'engineering'
        assert len(result.updated_fields) == 2
        assert result.validation_result.valid is True


if __name__ == '__main__':
    pytest.main([__file__])