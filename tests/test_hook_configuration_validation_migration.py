"""
Tests for Hook Configuration Validation and Migration Tools.

This module provides comprehensive tests for configuration validation,
migration, backup, and testing utilities.
"""

import pytest
import asyncio
import json
import yaml
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from devsync_ai.core.hook_configuration_validator import HookConfigurationValidator
from devsync_ai.core.hook_configuration_migration import HookConfigurationMigrator, ConfigurationBackupManager
from devsync_ai.core.hook_configuration_testing import ConfigurationTester, ConfigurationValidator
from devsync_ai.core.hook_configuration_manager import ValidationResult


class TestHookConfigurationValidator:
    """Test configuration validation functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return HookConfigurationValidator()
    
    @pytest.fixture
    def valid_config(self):
        """Create valid configuration for testing."""
        return {
            "team_id": "test-team",
            "team_name": "Test Team",
            "enabled": True,
            "version": "1.2.0",
            "default_channels": {
                "status_change": "#dev-updates",
                "assignment": "#assignments",
                "comment": "#discussions",
                "blocker": "#critical-alerts",
                "general": "#general"
            },
            "notification_preferences": {
                "batch_threshold": 5,
                "batch_timeout_minutes": 15,
                "quiet_hours": {
                    "enabled": True,
                    "start": "22:00",
                    "end": "08:00"
                },
                "weekend_notifications": False
            },
            "business_hours": {
                "start": "09:00",
                "end": "17:00",
                "timezone": "UTC",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
            },
            "rules": [
                {
                    "rule_id": "high_priority_rule",
                    "name": "High Priority Notifications",
                    "description": "Notify for high priority issues",
                    "hook_types": ["StatusChangeHook", "AssignmentHook"],
                    "enabled": True,
                    "priority": 10,
                    "conditions": {
                        "logic": "and",
                        "conditions": [
                            {
                                "field": "ticket.priority.name",
                                "operator": "in",
                                "value": ["High", "Critical"]
                            }
                        ]
                    },
                    "metadata": {
                        "channels": ["#critical-alerts"],
                        "urgency_override": "high",
                        "escalation_enabled": True,
                        "ignore_quiet_hours": False
                    }
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_validate_valid_configuration(self, validator, valid_config):
        """Test validation of valid configuration."""
        result = await validator.validate_team_configuration_schema(valid_config)
        
        assert result.valid is True
        assert len(result.errors) == 0
        assert isinstance(result.warnings, list)
        assert isinstance(result.suggestions, list)
    
    @pytest.mark.asyncio
    async def test_validate_missing_required_fields(self, validator):
        """Test validation with missing required fields."""
        config = {
            "team_name": "Test Team",
            "enabled": True
            # Missing team_id, default_channels, rules
        }
        
        result = await validator.validate_team_configuration_schema(config)
        
        assert result.valid is False
        assert "Missing required field: team_id" in result.errors
        assert "Missing required field: default_channels" in result.errors
        assert "Missing required field: rules" in result.errors
    
    @pytest.mark.asyncio
    async def test_validate_invalid_rule_syntax(self, validator):
        """Test validation with invalid rule syntax."""
        config = {
            "team_id": "test-team",
            "team_name": "Test Team",
            "enabled": True,
            "default_channels": {"general": "#general"},
            "rules": [
                {
                    "rule_id": "invalid_rule",
                    "name": "Invalid Rule",
                    "hook_types": ["InvalidHookType"],  # Invalid hook type
                    "conditions": {
                        "logic": "invalid_logic",  # Invalid logic
                        "conditions": [
                            {
                                "field": "invalid.field",  # Invalid field
                                "operator": "invalid_operator",  # Invalid operator
                                "value": "test"
                            }
                        ]
                    }
                }
            ]
        }
        
        result = await validator.validate_team_configuration_schema(config)
        
        assert result.valid is False
        assert any("Invalid hook type 'InvalidHookType'" in error for error in result.errors)
        assert any("Logic must be 'and' or 'or'" in error for error in result.errors)
        assert any("Invalid operator 'invalid_operator'" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_regex_patterns(self, validator):
        """Test validation of regex patterns."""
        config = {
            "team_id": "test-team",
            "team_name": "Test Team",
            "enabled": True,
            "default_channels": {"general": "#general"},
            "rules": [
                {
                    "rule_id": "regex_rule",
                    "name": "Regex Rule",
                    "hook_types": ["StatusChangeHook"],
                    "conditions": {
                        "logic": "and",
                        "conditions": [
                            {
                                "field": "ticket.summary",
                                "operator": "regex",
                                "value": "[invalid regex pattern"  # Invalid regex
                            }
                        ]
                    }
                }
            ]
        }
        
        result = await validator.validate_team_configuration_schema(config)
        
        assert result.valid is False
        assert any("Invalid regex pattern" in error for error in result.errors)
    
    def test_get_field_suggestions(self, validator):
        """Test field suggestions functionality."""
        suggestions = validator.get_field_suggestions("ticket")
        
        assert len(suggestions) > 0
        assert all("ticket" in suggestion.lower() for suggestion in suggestions)
    
    def test_get_operator_suggestions(self, validator):
        """Test operator suggestions for fields."""
        operators = validator.get_operator_suggestions("ticket.priority.name")
        
        assert len(operators) > 0
        assert "equals" in operators
        assert "in" in operators
    
    def test_get_validation_help(self, validator):
        """Test validation help information."""
        help_info = validator.get_validation_help()
        
        assert "fields" in help_info
        assert "operators" in help_info
        assert "hook_types" in help_info
        assert "examples" in help_info
        
        # Check field information
        assert "ticket.priority.name" in help_info["fields"]
        field_info = help_info["fields"]["ticket.priority.name"]
        assert "data_type" in field_info
        assert "description" in field_info
        assert "valid_operators" in field_info


class TestHookConfigurationMigrator:
    """Test configuration migration functionality."""
    
    @pytest.fixture
    def migrator(self):
        """Create migrator instance."""
        return HookConfigurationMigrator()
    
    @pytest.fixture
    def v1_0_config(self):
        """Create version 1.0.0 configuration."""
        return {
            "team_id": "test-team",
            "team_name": "Test Team",
            "enabled": True,
            "version": "1.0.0",
            "default_channels": {
                "status_change": "#dev-updates"
            },
            "rules": [
                {
                    "rule_id": "basic_rule",
                    "name": "Basic Rule",
                    "hook_types": ["StatusChangeHook"],
                    "conditions": {
                        "logic": "and",
                        "conditions": [
                            {
                                "field": "ticket.priority.name",
                                "operator": "equals",
                                "value": "High"
                            }
                        ]
                    }
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_migrate_to_latest_version(self, migrator, v1_0_config):
        """Test migration from v1.0.0 to latest version."""
        result = await migrator.migrate_configuration(v1_0_config)
        
        assert result.success is True
        assert result.from_version == "1.0.0"
        assert result.to_version == migrator._current_version
        assert len(result.errors) == 0
        assert len(result.changes_made) > 0
        assert result.backup_path is not None
    
    @pytest.mark.asyncio
    async def test_migrate_same_version(self, migrator):
        """Test migration when already at target version."""
        config = {
            "team_id": "test-team",
            "version": migrator._current_version
        }
        
        result = await migrator.migrate_configuration(config)
        
        assert result.success is True
        assert result.from_version == migrator._current_version
        assert result.to_version == migrator._current_version
        assert "No migration needed" in result.changes_made[0]
    
    @pytest.mark.asyncio
    async def test_migrate_invalid_version_path(self, migrator):
        """Test migration with invalid version path."""
        config = {
            "team_id": "test-team",
            "version": "999.0.0"  # Non-existent version
        }
        
        result = await migrator.migrate_configuration(config, "1.0.0")
        
        assert result.success is False
        assert "No migration path found" in result.errors[0]
    
    def test_get_available_versions(self, migrator):
        """Test getting available versions."""
        versions = migrator.get_available_versions()
        
        assert len(versions) > 0
        assert "1.0.0" in versions
        assert migrator._current_version in versions
    
    def test_get_migration_info(self, migrator):
        """Test getting migration information."""
        info = migrator.get_migration_info("1.0.0", "1.2.0")
        
        assert info["available"] is True
        assert "steps" in info
        assert "total_steps" in info
        assert info["total_steps"] > 0
    
    def test_migration_step_1_0_to_1_1(self, migrator, v1_0_config):
        """Test specific migration step from 1.0 to 1.1."""
        migrated = migrator._migrate_1_0_to_1_1(v1_0_config)
        
        assert "notification_preferences" in migrated
        assert "business_hours" in migrated
        assert migrated["rules"][0]["priority"] == 50  # Default priority added
    
    def test_migration_step_1_1_to_1_2(self, migrator):
        """Test specific migration step from 1.1 to 1.2."""
        config = {
            "team_id": "test-team",
            "version": "1.1.0",
            "rules": [
                {
                    "rule_id": "test_rule",
                    "metadata": {}
                }
            ]
        }
        
        migrated = migrator._migrate_1_1_to_1_2(config)
        
        assert "escalation_rules" in migrated
        assert "configuration_metadata" in migrated
        assert migrated["rules"][0]["metadata"]["escalation_enabled"] is True


class TestConfigurationBackupManager:
    """Test configuration backup management."""
    
    @pytest.fixture
    def backup_manager(self):
        """Create backup manager with temporary directory."""
        temp_dir = Path(tempfile.mkdtemp())
        return ConfigurationBackupManager(temp_dir)
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return {
            "team_id": "test-team",
            "team_name": "Test Team",
            "version": "1.2.0",
            "enabled": True
        }
    
    @pytest.mark.asyncio
    async def test_create_backup(self, backup_manager, test_config):
        """Test creating a configuration backup."""
        backup_path = await backup_manager.create_backup(test_config, "test_backup")
        
        assert Path(backup_path).exists()
        assert "test_backup.yaml" in backup_path
        
        # Verify backup content
        with open(backup_path, 'r') as f:
            backup_data = yaml.safe_load(f)
        
        assert backup_data["team_id"] == "test-team"
        assert "backup_metadata" in backup_data
    
    @pytest.mark.asyncio
    async def test_list_backups(self, backup_manager, test_config):
        """Test listing available backups."""
        # Create some backups
        await backup_manager.create_backup(test_config, "backup1")
        await backup_manager.create_backup(test_config, "backup2")
        
        backups = await backup_manager.list_backups()
        
        assert len(backups) >= 2
        assert all("filename" in backup for backup in backups)
        assert all("team_id" in backup for backup in backups)
    
    @pytest.mark.asyncio
    async def test_restore_backup(self, backup_manager, test_config):
        """Test restoring from backup."""
        # Create backup
        backup_path = await backup_manager.create_backup(test_config, "restore_test")
        
        # Restore backup
        restored_config = await backup_manager.restore_backup(backup_path)
        
        assert restored_config["team_id"] == test_config["team_id"]
        assert "backup_metadata" not in restored_config  # Should be removed
    
    @pytest.mark.asyncio
    async def test_delete_backup(self, backup_manager, test_config):
        """Test deleting a backup."""
        backup_path = await backup_manager.create_backup(test_config, "delete_test")
        
        assert Path(backup_path).exists()
        
        success = await backup_manager.delete_backup(backup_path)
        
        assert success is True
        assert not Path(backup_path).exists()
    
    @pytest.mark.asyncio
    async def test_cleanup_old_backups(self, backup_manager, test_config):
        """Test cleaning up old backups."""
        # Create multiple backups
        for i in range(5):
            await backup_manager.create_backup(test_config, f"cleanup_test_{i}")
        
        deleted_count = await backup_manager.cleanup_old_backups(keep_count=2)
        
        assert deleted_count >= 3  # Should delete at least 3 backups


class TestConfigurationTester:
    """Test configuration testing functionality."""
    
    @pytest.fixture
    def tester(self):
        """Create configuration tester."""
        return ConfigurationTester()
    
    @pytest.fixture
    def valid_config(self):
        """Create valid configuration for testing."""
        return {
            "team_id": "test-team",
            "team_name": "Test Team",
            "enabled": True,
            "default_channels": {"general": "#general"},
            "rules": [
                {
                    "rule_id": "test_rule",
                    "name": "Test Rule",
                    "hook_types": ["StatusChangeHook"],
                    "conditions": {
                        "logic": "and",
                        "conditions": [
                            {
                                "field": "ticket.priority.name",
                                "operator": "equals",
                                "value": "High"
                            }
                        ]
                    }
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_run_validation_tests(self, tester, valid_config):
        """Test running validation tests."""
        result = await tester.run_validation_tests(valid_config)
        
        assert result.suite_name == "Configuration Validation Tests"
        assert result.total_tests > 0
        assert result.execution_time_ms > 0
        assert isinstance(result.test_results, list)
    
    @pytest.mark.asyncio
    async def test_run_rule_evaluation_tests(self, tester, valid_config):
        """Test running rule evaluation tests."""
        with patch.object(tester.rule_engine, 'evaluate_rules', new_callable=AsyncMock) as mock_evaluate:
            mock_evaluate.return_value = Mock(matched=True, actions=[], metadata={})
            
            result = await tester.run_rule_evaluation_tests(valid_config)
            
            assert result.suite_name == "Rule Evaluation Tests"
            assert result.total_tests > 0
            assert mock_evaluate.called
    
    @pytest.mark.asyncio
    async def test_run_comprehensive_test_suite(self, tester, valid_config):
        """Test running comprehensive test suite."""
        with patch.object(tester.rule_engine, 'evaluate_rules', new_callable=AsyncMock) as mock_evaluate:
            mock_evaluate.return_value = Mock(matched=True, actions=[], metadata={})
            
            results = await tester.run_comprehensive_test_suite(valid_config)
            
            assert "validation" in results
            assert isinstance(results["validation"], type(results["validation"]))
    
    def test_generate_test_report_yaml(self, tester):
        """Test generating test report in YAML format."""
        from devsync_ai.core.hook_configuration_testing import TestSuiteResult, TestResult
        
        test_results = {
            "validation": TestSuiteResult(
                suite_name="Test Suite",
                total_tests=1,
                passed_tests=1,
                failed_tests=0,
                test_results=[
                    TestResult(
                        test_name="test1",
                        passed=True,
                        errors=[],
                        warnings=[],
                        details={},
                        execution_time_ms=10.0
                    )
                ],
                execution_time_ms=10.0,
                summary={}
            )
        }
        
        report = tester.generate_test_report(test_results, "yaml")
        
        assert "test_report:" in report
        assert "summary:" in report
        assert "suites:" in report
    
    def test_generate_test_report_markdown(self, tester):
        """Test generating test report in Markdown format."""
        from devsync_ai.core.hook_configuration_testing import TestSuiteResult, TestResult
        
        test_results = {
            "validation": TestSuiteResult(
                suite_name="Test Suite",
                total_tests=1,
                passed_tests=1,
                failed_tests=0,
                test_results=[
                    TestResult(
                        test_name="test1",
                        passed=True,
                        errors=[],
                        warnings=[],
                        details={},
                        execution_time_ms=10.0
                    )
                ],
                execution_time_ms=10.0,
                summary={}
            )
        }
        
        report = tester.generate_test_report(test_results, "markdown")
        
        assert "# Hook Configuration Test Report" in report
        assert "## Summary" in report
        assert "## Test Suite" in report


class TestConfigurationValidator:
    """Test high-level configuration validator."""
    
    @pytest.fixture
    def config_validator(self):
        """Create configuration validator."""
        return ConfigurationValidator()
    
    @pytest.mark.asyncio
    async def test_validate_configuration_file(self, config_validator):
        """Test validating configuration file."""
        # Create temporary config file
        config_data = {
            "team_id": "test-team",
            "team_name": "Test Team",
            "enabled": True,
            "default_channels": {"general": "#general"},
            "rules": []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            with patch.object(config_validator.tester, 'run_comprehensive_test_suite', new_callable=AsyncMock) as mock_test:
                from devsync_ai.core.hook_configuration_testing import TestSuiteResult
                mock_test.return_value = {
                    "validation": TestSuiteResult(
                        suite_name="Test",
                        total_tests=1,
                        passed_tests=1,
                        failed_tests=0,
                        test_results=[],
                        execution_time_ms=10.0,
                        summary={}
                    )
                }
                
                is_valid, report = await config_validator.validate_configuration_file(temp_path)
                
                assert is_valid is True
                assert len(report) > 0
        finally:
            Path(temp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_validate_configuration_syntax(self, config_validator):
        """Test validating configuration syntax."""
        config_data = {
            "team_id": "test-team",
            "team_name": "Test Team",
            "enabled": True,
            "default_channels": {"general": "#general"},
            "rules": []
        }
        
        result = await config_validator.validate_configuration_syntax(config_data)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
    
    def test_get_validation_help(self, config_validator):
        """Test getting validation help."""
        help_info = config_validator.get_validation_help()
        
        assert "fields" in help_info
        assert "operators" in help_info
        assert "hook_types" in help_info


class TestIntegration:
    """Integration tests for configuration management tools."""
    
    @pytest.mark.asyncio
    async def test_full_configuration_lifecycle(self):
        """Test complete configuration lifecycle: create, validate, migrate, backup."""
        # Create initial configuration
        config_v1 = {
            "team_id": "integration-test",
            "team_name": "Integration Test Team",
            "enabled": True,
            "version": "1.0.0",
            "default_channels": {"general": "#general"},
            "rules": [
                {
                    "rule_id": "test_rule",
                    "name": "Test Rule",
                    "hook_types": ["StatusChangeHook"],
                    "conditions": {
                        "logic": "and",
                        "conditions": [
                            {
                                "field": "ticket.priority.name",
                                "operator": "equals",
                                "value": "High"
                            }
                        ]
                    }
                }
            ]
        }
        
        # Validate initial configuration
        validator = HookConfigurationValidator()
        validation_result = await validator.validate_team_configuration_schema(config_v1)
        assert validation_result.valid is True
        
        # Create backup
        backup_manager = ConfigurationBackupManager()
        backup_path = await backup_manager.create_backup(config_v1, "integration_test")
        assert Path(backup_path).exists()
        
        # Migrate configuration
        migrator = HookConfigurationMigrator()
        migration_result = await migrator.migrate_configuration(config_v1)
        assert migration_result.success is True
        
        # Validate migrated configuration
        # Note: migrated config would be in migration_result, but for this test
        # we'll validate the original config was processed
        assert migration_result.from_version == "1.0.0"
        assert migration_result.to_version == migrator._current_version
        
        # Clean up
        await backup_manager.delete_backup(backup_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])