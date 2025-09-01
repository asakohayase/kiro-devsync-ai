"""
Tests for Changelog Configuration Backup System.

Tests cover backup creation, validation, restore, and integrity checking.
"""

import pytest
import asyncio
import json
import yaml
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import asdict

from devsync_ai.core.changelog_configuration_backup import (
    ChangelogConfigurationBackup,
    BackupType,
    BackupStatus,
    BackupMetadata,
    RestoreResult,
    BackupValidationResult
)
from devsync_ai.core.changelog_configuration_manager import (
    ChangelogConfigurationManager,
    TeamChangelogConfig,
    GlobalChangelogConfig,
    DistributionConfig
)


class TestChangelogConfigurationBackup:
    """Test suite for ChangelogConfigurationBackup."""
    
    @pytest.fixture
    def temp_backup_dir(self, tmp_path):
        """Create temporary backup directory."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        return backup_dir
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create mock configuration manager."""
        manager = Mock(spec=ChangelogConfigurationManager)
        manager.load_team_configuration = AsyncMock()
        manager.load_global_configuration = AsyncMock()
        manager.save_team_configuration = AsyncMock(return_value=True)
        manager.save_global_configuration = AsyncMock(return_value=True)
        manager.validate_team_configuration = AsyncMock()
        manager.validate_global_configuration = AsyncMock()
        manager.get_all_team_configurations = AsyncMock(return_value=[])
        return manager
    
    @pytest.fixture
    def backup_system(self, mock_config_manager, temp_backup_dir):
        """Create backup system with mocked dependencies."""
        return ChangelogConfigurationBackup(
            config_manager=mock_config_manager,
            backup_directory=str(temp_backup_dir)
        )
    
    @pytest.fixture
    def sample_team_config(self):
        """Sample team configuration for testing."""
        return TeamChangelogConfig(
            team_id="test_team",
            team_name="Test Team",
            enabled=True,
            distribution=DistributionConfig(primary_channel="#test-updates")
        )
    
    @pytest.fixture
    def sample_global_config(self):
        """Sample global configuration for testing."""
        return GlobalChangelogConfig(
            enabled=True,
            version="1.0.0",
            max_concurrent_generations=5
        )

    @pytest.mark.asyncio
    async def test_create_team_backup(self, backup_system, mock_config_manager, sample_team_config):
        """Test creating team configuration backup."""
        mock_config_manager.load_team_configuration.return_value = sample_team_config
        
        with patch.object(backup_system, '_store_backup_metadata') as mock_store:
            with patch.object(backup_system, 'validate_backup') as mock_validate:
                mock_validate.return_value = BackupValidationResult(valid=True, backup_id="test")
                
                metadata = await backup_system.create_backup(
                    team_id="test_team",
                    backup_type=BackupType.MANUAL,
                    description="Test backup",
                    created_by="test_user"
                )
                
                assert metadata is not None
                assert metadata.team_id == "test_team"
                assert metadata.backup_type == BackupType.MANUAL
                assert metadata.created_by == "test_user"
                mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_global_backup(self, backup_system, mock_config_manager, sample_global_config):
        """Test creating global configuration backup."""
        mock_config_manager.load_global_configuration.return_value = sample_global_config
        
        with patch.object(backup_system, '_store_backup_metadata') as mock_store:
            with patch.object(backup_system, 'validate_backup') as mock_validate:
                mock_validate.return_value = BackupValidationResult(valid=True, backup_id="test")
                
                metadata = await backup_system.create_backup(
                    team_id=None,
                    backup_type=BackupType.AUTOMATIC,
                    description="Global backup"
                )
                
                assert metadata is not None
                assert metadata.team_id is None
                assert metadata.backup_type == BackupType.AUTOMATIC
                mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_backup_file_creation(self, backup_system, mock_config_manager, sample_team_config, temp_backup_dir):
        """Test that backup files are created correctly."""
        mock_config_manager.load_team_configuration.return_value = sample_team_config
        
        with patch.object(backup_system, '_store_backup_metadata'):
            with patch.object(backup_system, 'validate_backup') as mock_validate:
                mock_validate.return_value = BackupValidationResult(valid=True, backup_id="test")
                
                metadata = await backup_system.create_backup(
                    team_id="test_team",
                    backup_type=BackupType.MANUAL
                )
                
                # Check that backup file was created
                backup_file = temp_backup_dir / f"{metadata.backup_id}.yaml"
                assert backup_file.exists()
                
                # Verify backup content
                with open(backup_file, 'r') as f:
                    backup_content = yaml.safe_load(f)
                
                assert "backup_metadata" in backup_content
                assert "configuration" in backup_content
                assert backup_content["backup_metadata"]["team_id"] == "test_team"
    
    @pytest.mark.asyncio
    async def test_validate_backup_success(self, backup_system, temp_backup_dir):
        """Test successful backup validation."""
        # Create test backup file
        backup_id = "test_backup_20240816_120000"
        backup_content = {
            "backup_metadata": {
                "backup_id": backup_id,
                "team_id": "test_team",
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            "configuration": {
                "team_id": "test_team",
                "team_name": "Test Team",
                "enabled": True
            }
        }
        
        backup_file = temp_backup_dir / f"{backup_id}.yaml"
        with open(backup_file, 'w') as f:
            yaml.dump(backup_content, f)
        
        # Create metadata
        config_json = json.dumps(backup_content["configuration"], sort_keys=True)
        config_hash = hashlib.sha256(config_json.encode()).hexdigest()
        
        metadata = BackupMetadata(
            backup_id=backup_id,
            team_id="test_team",
            backup_type=BackupType.MANUAL,
            created_at=datetime.now(timezone.utc),
            created_by="test",
            description="Test",
            file_size=backup_file.stat().st_size,
            config_hash=config_hash
        )
        
        with patch.object(backup_system, '_load_backup_metadata', return_value=metadata):
            with patch.object(backup_system.config_manager, 'validate_team_configuration') as mock_validate:
                from devsync_ai.core.hook_configuration_manager import ValidationResult
                mock_validate.return_value = ValidationResult(valid=True)
                
                result = await backup_system.validate_backup(backup_id)
                
                assert result.valid is True
                assert result.integrity_check is True
                assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_backup_corrupted(self, backup_system, temp_backup_dir):
        """Test validation of corrupted backup."""
        backup_id = "corrupted_backup_20240816_120000"
        
        # Create metadata with wrong hash
        metadata = BackupMetadata(
            backup_id=backup_id,
            team_id="test_team",
            backup_type=BackupType.MANUAL,
            created_at=datetime.now(timezone.utc),
            created_by="test",
            description="Test",
            file_size=100,
            config_hash="wrong_hash"
        )
        
        # Create backup file with different content
        backup_content = {
            "backup_metadata": {"backup_id": backup_id},
            "configuration": {"team_id": "different_team"}
        }
        
        backup_file = temp_backup_dir / f"{backup_id}.yaml"
        with open(backup_file, 'w') as f:
            yaml.dump(backup_content, f)
        
        with patch.object(backup_system, '_load_backup_metadata', return_value=metadata):
            result = await backup_system.validate_backup(backup_id)
            
            assert result.valid is False
            assert result.integrity_check is False
            assert any("hash mismatch" in error.lower() for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_restore_backup_success(self, backup_system, mock_config_manager, temp_backup_dir):
        """Test successful backup restore."""
        backup_id = "restore_test_20240816_120000"
        
        # Create backup file
        backup_content = {
            "backup_metadata": {
                "backup_id": backup_id,
                "team_id": "test_team"
            },
            "configuration": {
                "team_id": "test_team",
                "team_name": "Test Team",
                "enabled": True
            }
        }
        
        backup_file = temp_backup_dir / f"{backup_id}.yaml"
        with open(backup_file, 'w') as f:
            yaml.dump(backup_content, f)
        
        # Create metadata
        metadata = BackupMetadata(
            backup_id=backup_id,
            team_id="test_team",
            backup_type=BackupType.MANUAL,
            created_at=datetime.now(timezone.utc),
            created_by="test",
            description="Test",
            file_size=100,
            config_hash="test_hash"
        )
        
        with patch.object(backup_system, '_load_backup_metadata', return_value=metadata):
            with patch.object(backup_system, 'validate_backup') as mock_validate:
                mock_validate.return_value = BackupValidationResult(valid=True, backup_id=backup_id)
                
                with patch.object(backup_system, '_update_backup_restore_info'):
                    from devsync_ai.core.hook_configuration_manager import ValidationResult
                    mock_config_manager.validate_team_configuration.return_value = ValidationResult(valid=True)
                    
                    result = await backup_system.restore_backup(backup_id)
                    
                    assert result.success is True
                    assert result.backup_id == backup_id
                    assert result.team_id == "test_team"
                    mock_config_manager.save_team_configuration.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_restore_backup_validation_failure(self, backup_system):
        """Test restore failure due to validation."""
        backup_id = "invalid_backup_20240816_120000"
        
        metadata = BackupMetadata(
            backup_id=backup_id,
            team_id="test_team",
            backup_type=BackupType.MANUAL,
            created_at=datetime.now(timezone.utc),
            created_by="test",
            description="Test",
            file_size=100,
            config_hash="test_hash"
        )
        
        with patch.object(backup_system, '_load_backup_metadata', return_value=metadata):
            with patch.object(backup_system, 'validate_backup') as mock_validate:
                mock_validate.return_value = BackupValidationResult(
                    valid=False,
                    backup_id=backup_id,
                    errors=["Backup is corrupted"]
                )
                
                result = await backup_system.restore_backup(backup_id)
                
                assert result.success is False
                assert "validation failed" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_list_backups(self, backup_system):
        """Test listing backups with filters."""
        # Mock database results
        mock_results = [
            {
                'backup_id': 'backup1',
                'team_id': 'team1',
                'backup_type': 'manual',
                'created_at': datetime.now(timezone.utc),
                'created_by': 'user1',
                'description': 'Test backup 1',
                'file_size': 100,
                'config_hash': 'hash1',
                'validation_status': 'validated',
                'restore_count': 0,
                'last_restored': None,
                'tags': ['test'],
                'metadata': {}
            },
            {
                'backup_id': 'backup2',
                'team_id': 'team2',
                'backup_type': 'automatic',
                'created_at': datetime.now(timezone.utc),
                'created_by': 'system',
                'description': 'Test backup 2',
                'file_size': 200,
                'config_hash': 'hash2',
                'validation_status': 'created',
                'restore_count': 1,
                'last_restored': datetime.now(timezone.utc),
                'tags': [],
                'metadata': {}
            }
        ]
        
        with patch('devsync_ai.database.connection.get_database') as mock_db:
            mock_db_instance = AsyncMock()
            mock_db.return_value = mock_db_instance
            mock_db_instance.select.return_value = mock_results
            
            backups = await backup_system.list_backups(team_id="team1", limit=10)
            
            assert len(backups) == 2
            assert backups[0].backup_id == 'backup1'
            assert backups[0].team_id == 'team1'
            assert backups[1].backup_id == 'backup2'
    
    @pytest.mark.asyncio
    async def test_delete_backup(self, backup_system, temp_backup_dir):
        """Test backup deletion."""
        backup_id = "delete_test_20240816_120000"
        
        # Create backup file
        backup_file = temp_backup_dir / f"{backup_id}.yaml"
        backup_file.write_text("test content")
        
        with patch('devsync_ai.database.connection.get_database') as mock_db:
            mock_db_instance = AsyncMock()
            mock_db.return_value = mock_db_instance
            
            result = await backup_system.delete_backup(backup_id)
            
            assert result is True
            assert not backup_file.exists()
            mock_db_instance.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_backup(self, backup_system, temp_backup_dir):
        """Test backup export."""
        backup_id = "export_test_20240816_120000"
        
        backup_content = {
            "backup_metadata": {"backup_id": backup_id},
            "configuration": {"team_id": "test_team"}
        }
        
        backup_file = temp_backup_dir / f"{backup_id}.yaml"
        with open(backup_file, 'w') as f:
            yaml.dump(backup_content, f)
        
        # Test YAML export
        yaml_export = await backup_system.export_backup(backup_id, "yaml")
        assert yaml_export is not None
        assert "backup_metadata" in yaml_export
        
        # Test JSON export
        json_export = await backup_system.export_backup(backup_id, "json")
        assert json_export is not None
        parsed_json = json.loads(json_export)
        assert "backup_metadata" in parsed_json
    
    @pytest.mark.asyncio
    async def test_import_backup(self, backup_system, temp_backup_dir):
        """Test backup import."""
        backup_content = {
            "backup_metadata": {
                "team_id": "imported_team",
                "description": "Imported backup",
                "tags": ["imported"]
            },
            "configuration": {
                "team_id": "imported_team",
                "team_name": "Imported Team",
                "enabled": True
            }
        }
        
        content_yaml = yaml.dump(backup_content)
        
        with patch.object(backup_system, '_store_backup_metadata'):
            with patch.object(backup_system, 'validate_backup') as mock_validate:
                mock_validate.return_value = BackupValidationResult(valid=True, backup_id="test")
                
                metadata = await backup_system.import_backup(
                    content_yaml,
                    format="yaml",
                    created_by="test_user"
                )
                
                assert metadata is not None
                assert metadata.team_id == "imported_team"
                assert metadata.created_by == "test_user"
                assert "imported" in metadata.tags
    
    @pytest.mark.asyncio
    async def test_scheduled_backups(self, backup_system, mock_config_manager):
        """Test scheduled backup creation."""
        # Mock team configurations
        team_configs = [
            TeamChangelogConfig(
                team_id="team1",
                team_name="Team 1",
                distribution=DistributionConfig(primary_channel="#team1")
            ),
            TeamChangelogConfig(
                team_id="team2",
                team_name="Team 2",
                distribution=DistributionConfig(primary_channel="#team2")
            )
        ]
        
        mock_config_manager.get_all_team_configurations.return_value = team_configs
        
        with patch.object(backup_system, 'create_backup') as mock_create:
            mock_create.return_value = BackupMetadata(
                backup_id="test",
                team_id="test",
                backup_type=BackupType.SCHEDULED,
                created_at=datetime.now(timezone.utc),
                created_by="scheduler",
                description="Test",
                file_size=100,
                config_hash="hash"
            )
            
            await backup_system.create_scheduled_backups()
            
            # Should create backups for each team plus global
            assert mock_create.call_count == 3  # 2 teams + 1 global
    
    @pytest.mark.asyncio
    async def test_backup_integrity_test(self, backup_system):
        """Test backup system integrity testing."""
        # Mock backup list
        mock_backups = [
            BackupMetadata(
                backup_id="backup1",
                team_id="team1",
                backup_type=BackupType.MANUAL,
                created_at=datetime.now(timezone.utc),
                created_by="user",
                description="Test",
                file_size=100,
                config_hash="hash1"
            ),
            BackupMetadata(
                backup_id="backup2",
                team_id="team2",
                backup_type=BackupType.AUTOMATIC,
                created_at=datetime.now(timezone.utc),
                created_by="system",
                description="Test",
                file_size=200,
                config_hash="hash2"
            )
        ]
        
        with patch.object(backup_system, 'list_backups', return_value=mock_backups):
            with patch.object(backup_system, 'validate_backup') as mock_validate:
                # First backup valid, second corrupted
                mock_validate.side_effect = [
                    BackupValidationResult(valid=True, backup_id="backup1", integrity_check=True),
                    BackupValidationResult(
                        valid=False,
                        backup_id="backup2",
                        integrity_check=False,
                        errors=["Corrupted"]
                    )
                ]
                
                results = await backup_system.test_backup_integrity()
                
                assert results["total_backups"] == 2
                assert results["valid_backups"] == 1
                assert results["corrupted_backups"] == 1
                assert results["missing_files"] == 1
                assert results["test_passed"] is False
                assert len(results["validation_errors"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])