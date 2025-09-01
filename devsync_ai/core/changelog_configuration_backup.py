"""
Configuration Backup and Restore System for Changelog Configuration Manager.

This module provides automated backup creation, validation, and restore
capabilities for changelog configurations with comprehensive testing
and validation.
"""

import asyncio
import logging
import json
import yaml
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from devsync_ai.core.changelog_configuration_manager import (
    ChangelogConfigurationManager,
    TeamChangelogConfig,
    GlobalChangelogConfig,
    ValidationResult
)
from devsync_ai.database.connection import get_database
from devsync_ai.core.exceptions import ConfigurationError


logger = logging.getLogger(__name__)


class BackupType(Enum):
    """Backup type enumeration."""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    PRE_UPDATE = "pre_update"
    SCHEDULED = "scheduled"


class BackupStatus(Enum):
    """Backup status enumeration."""
    CREATED = "created"
    VALIDATED = "validated"
    CORRUPTED = "corrupted"
    RESTORED = "restored"


@dataclass
class BackupMetadata:
    """Backup metadata information."""
    backup_id: str
    team_id: Optional[str]
    backup_type: BackupType
    created_at: datetime
    created_by: str
    description: str
    file_size: int
    config_hash: str
    validation_status: BackupStatus = BackupStatus.CREATED
    restore_count: int = 0
    last_restored: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RestoreResult:
    """Result of configuration restore operation."""
    success: bool
    backup_id: str
    team_id: Optional[str]
    restored_at: datetime
    validation_result: Optional[ValidationResult] = None
    error_message: Optional[str] = None
    rollback_available: bool = True


@dataclass
class BackupValidationResult:
    """Result of backup validation."""
    valid: bool
    backup_id: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    integrity_check: bool = True
    config_validation: Optional[ValidationResult] = None


class ChangelogConfigurationBackup:
    """
    Configuration backup and restore system.
    
    Provides automated backup creation, validation, and restore capabilities
    for changelog configurations with comprehensive testing and validation.
    """
    
    def __init__(self, config_manager: ChangelogConfigurationManager, backup_directory: Optional[str] = None):
        """
        Initialize backup system.
        
        Args:
            config_manager: Configuration manager instance
            backup_directory: Directory for backup files
        """
        self.config_manager = config_manager
        self.backup_directory = Path(backup_directory or "config/backups")
        self.logger = logging.getLogger(__name__)
        
        # Ensure backup directory exists
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        
        # Backup retention settings
        self.max_backups_per_team = 50
        self.backup_retention_days = 90
        self.automatic_cleanup_enabled = True
        
        self.logger.info(f"Configuration backup system initialized with directory: {self.backup_directory}")
    
    async def create_backup(
        self,
        team_id: Optional[str] = None,
        backup_type: BackupType = BackupType.MANUAL,
        description: str = "",
        created_by: str = "system",
        tags: Optional[List[str]] = None
    ) -> Optional[BackupMetadata]:
        """
        Create configuration backup.
        
        Args:
            team_id: Team ID for team-specific backup, None for global backup
            backup_type: Type of backup being created
            description: Description of the backup
            created_by: User or system creating the backup
            tags: Optional tags for categorizing backups
            
        Returns:
            BackupMetadata if successful, None otherwise
        """
        try:
            # Generate backup ID
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_id = f"{team_id or 'global'}_{backup_type.value}_{timestamp}"
            
            # Load configuration to backup
            if team_id:
                config = await self.config_manager.load_team_configuration(team_id)
                config_data = asdict(config)
            else:
                config = await self.config_manager.load_global_configuration()
                config_data = asdict(config)
            
            # Serialize config data for JSON compatibility
            serialized_config_data = self._serialize_config_for_backup(config_data)
            
            # Create backup content
            backup_content = {
                "backup_metadata": {
                    "backup_id": backup_id,
                    "team_id": team_id,
                    "backup_type": backup_type.value,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "created_by": created_by,
                    "description": description,
                    "tags": tags or [],
                    "version": "1.0.0"
                },
                "configuration": serialized_config_data
            }
            
            # Calculate hash for integrity checking
            config_json = json.dumps(serialized_config_data, sort_keys=True)
            config_hash = hashlib.sha256(config_json.encode()).hexdigest()
            
            # Save backup to file
            backup_file = self.backup_directory / f"{backup_id}.yaml"
            with open(backup_file, 'w') as f:
                yaml.dump(backup_content, f, default_flow_style=False, indent=2)
            
            # Get file size
            file_size = backup_file.stat().st_size
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                team_id=team_id,
                backup_type=backup_type,
                created_at=datetime.now(timezone.utc),
                created_by=created_by,
                description=description,
                file_size=file_size,
                config_hash=config_hash,
                tags=tags or []
            )
            
            # Store metadata in database
            await self._store_backup_metadata(metadata)
            
            # Validate backup
            validation_result = await self.validate_backup(backup_id)
            if validation_result.valid:
                metadata.validation_status = BackupStatus.VALIDATED
                await self._update_backup_status(backup_id, BackupStatus.VALIDATED)
            else:
                metadata.validation_status = BackupStatus.CORRUPTED
                await self._update_backup_status(backup_id, BackupStatus.CORRUPTED)
                self.logger.warning(f"Backup {backup_id} failed validation: {validation_result.errors}")
            
            # Cleanup old backups if enabled
            if self.automatic_cleanup_enabled:
                await self._cleanup_old_backups(team_id)
            
            self.logger.info(f"Created backup {backup_id} for {'team ' + team_id if team_id else 'global config'}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None
    
    async def restore_backup(
        self,
        backup_id: str,
        validate_before_restore: bool = True,
        create_pre_restore_backup: bool = True
    ) -> RestoreResult:
        """
        Restore configuration from backup.
        
        Args:
            backup_id: Backup identifier
            validate_before_restore: Whether to validate backup before restoring
            create_pre_restore_backup: Whether to create backup before restore
            
        Returns:
            RestoreResult indicating success/failure
        """
        try:
            # Load backup metadata
            metadata = await self._load_backup_metadata(backup_id)
            if not metadata:
                return RestoreResult(
                    success=False,
                    backup_id=backup_id,
                    team_id=None,
                    restored_at=datetime.now(timezone.utc),
                    error_message=f"Backup {backup_id} not found"
                )
            
            # Validate backup if requested
            if validate_before_restore:
                validation_result = await self.validate_backup(backup_id)
                if not validation_result.valid:
                    return RestoreResult(
                        success=False,
                        backup_id=backup_id,
                        team_id=metadata.team_id,
                        restored_at=datetime.now(timezone.utc),
                        validation_result=validation_result,
                        error_message="Backup validation failed"
                    )
            
            # Create pre-restore backup if requested
            if create_pre_restore_backup:
                pre_restore_backup = await self.create_backup(
                    team_id=metadata.team_id,
                    backup_type=BackupType.PRE_UPDATE,
                    description=f"Pre-restore backup before restoring {backup_id}",
                    created_by="system",
                    tags=["pre_restore"]
                )
                if not pre_restore_backup:
                    self.logger.warning("Failed to create pre-restore backup, continuing with restore")
            
            # Load backup content
            backup_content = await self._load_backup_content(backup_id)
            if not backup_content:
                return RestoreResult(
                    success=False,
                    backup_id=backup_id,
                    team_id=metadata.team_id,
                    restored_at=datetime.now(timezone.utc),
                    error_message="Failed to load backup content"
                )
            
            # Parse configuration from backup
            config_data = backup_content.get("configuration", {})
            
            # Restore configuration
            if metadata.team_id:
                # Restore team configuration
                config = self.config_manager._parse_team_config_data(config_data)
                config.team_id = metadata.team_id  # Ensure team_id is correct
                
                # Validate restored configuration
                validation_result = await self.config_manager.validate_team_configuration(config)
                if not validation_result.valid:
                    return RestoreResult(
                        success=False,
                        backup_id=backup_id,
                        team_id=metadata.team_id,
                        restored_at=datetime.now(timezone.utc),
                        validation_result=validation_result,
                        error_message="Restored configuration is invalid"
                    )
                
                # Save restored configuration
                success = await self.config_manager.save_team_configuration(metadata.team_id, config)
            else:
                # Restore global configuration
                config = self.config_manager._parse_global_config_data(config_data)
                
                # Validate restored configuration
                validation_result = await self.config_manager.validate_global_configuration(config)
                if not validation_result.valid:
                    return RestoreResult(
                        success=False,
                        backup_id=backup_id,
                        team_id=None,
                        restored_at=datetime.now(timezone.utc),
                        validation_result=validation_result,
                        error_message="Restored global configuration is invalid"
                    )
                
                # Save restored configuration
                success = await self.config_manager.save_global_configuration(config)
            
            if success:
                # Update backup metadata
                await self._update_backup_restore_info(backup_id)
                
                return RestoreResult(
                    success=True,
                    backup_id=backup_id,
                    team_id=metadata.team_id,
                    restored_at=datetime.now(timezone.utc),
                    validation_result=validation_result
                )
            else:
                return RestoreResult(
                    success=False,
                    backup_id=backup_id,
                    team_id=metadata.team_id,
                    restored_at=datetime.now(timezone.utc),
                    error_message="Failed to save restored configuration"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to restore backup {backup_id}: {e}")
            return RestoreResult(
                success=False,
                backup_id=backup_id,
                team_id=None,
                restored_at=datetime.now(timezone.utc),
                error_message=str(e)
            )
    
    async def validate_backup(self, backup_id: str) -> BackupValidationResult:
        """
        Validate backup integrity and configuration.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            BackupValidationResult
        """
        errors = []
        warnings = []
        
        try:
            # Load backup metadata
            metadata = await self._load_backup_metadata(backup_id)
            if not metadata:
                return BackupValidationResult(
                    valid=False,
                    backup_id=backup_id,
                    errors=["Backup metadata not found"],
                    integrity_check=False
                )
            
            # Check if backup file exists
            backup_file = self.backup_directory / f"{backup_id}.yaml"
            if not backup_file.exists():
                errors.append("Backup file not found")
                return BackupValidationResult(
                    valid=False,
                    backup_id=backup_id,
                    errors=errors,
                    integrity_check=False
                )
            
            # Load backup content
            backup_content = await self._load_backup_content(backup_id)
            if not backup_content:
                errors.append("Failed to load backup content")
                return BackupValidationResult(
                    valid=False,
                    backup_id=backup_id,
                    errors=errors,
                    integrity_check=False
                )
            
            # Verify backup structure
            if "backup_metadata" not in backup_content:
                errors.append("Missing backup metadata in backup file")
            
            if "configuration" not in backup_content:
                errors.append("Missing configuration data in backup file")
            
            # Verify hash integrity
            config_data = backup_content.get("configuration", {})
            config_json = json.dumps(config_data, sort_keys=True)
            calculated_hash = hashlib.sha256(config_json.encode()).hexdigest()
            
            if calculated_hash != metadata.config_hash:
                errors.append("Configuration hash mismatch - backup may be corrupted")
            
            # Validate configuration content
            config_validation = None
            if metadata.team_id:
                # Validate team configuration
                try:
                    config = self.config_manager._parse_team_config_data(config_data)
                    config_validation = await self.config_manager.validate_team_configuration(config)
                except Exception as e:
                    errors.append(f"Failed to parse team configuration: {str(e)}")
            else:
                # Validate global configuration
                try:
                    config = self.config_manager._parse_global_config_data(config_data)
                    config_validation = await self.config_manager.validate_global_configuration(config)
                except Exception as e:
                    errors.append(f"Failed to parse global configuration: {str(e)}")
            
            # Check configuration validation results
            if config_validation and not config_validation.valid:
                warnings.extend([f"Config validation: {error}" for error in config_validation.errors])
            
            # Check file size consistency
            current_file_size = backup_file.stat().st_size
            if current_file_size != metadata.file_size:
                warnings.append(f"File size mismatch: expected {metadata.file_size}, got {current_file_size}")
            
            return BackupValidationResult(
                valid=len(errors) == 0,
                backup_id=backup_id,
                errors=errors,
                warnings=warnings,
                integrity_check=calculated_hash == metadata.config_hash,
                config_validation=config_validation
            )
            
        except Exception as e:
            self.logger.error(f"Failed to validate backup {backup_id}: {e}")
            return BackupValidationResult(
                valid=False,
                backup_id=backup_id,
                errors=[f"Validation error: {str(e)}"],
                integrity_check=False
            )
    
    async def list_backups(
        self,
        team_id: Optional[str] = None,
        backup_type: Optional[BackupType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[BackupMetadata]:
        """
        List available backups.
        
        Args:
            team_id: Filter by team ID (None for global backups)
            backup_type: Filter by backup type
            limit: Maximum number of backups to return
            offset: Offset for pagination
            
        Returns:
            List of backup metadata
        """
        try:
            db = await get_database()
            
            # Build filters
            filters = {}
            if team_id is not None:
                filters['team_id'] = team_id
            if backup_type:
                filters['backup_type'] = backup_type.value
            
            # Query backups
            results = await db.select(
                'changelog_config_backups',
                filters=filters,
                order_by='created_at DESC',
                limit=limit,
                offset=offset
            )
            
            # Convert to metadata objects
            backups = []
            for result in results:
                metadata = BackupMetadata(
                    backup_id=result['backup_id'],
                    team_id=result.get('team_id'),
                    backup_type=BackupType(result['backup_type']),
                    created_at=result['created_at'],
                    created_by=result['created_by'],
                    description=result.get('description', ''),
                    file_size=result.get('file_size', 0),
                    config_hash=result.get('config_hash', ''),
                    validation_status=BackupStatus(result.get('validation_status', 'created')),
                    restore_count=result.get('restore_count', 0),
                    last_restored=result.get('last_restored'),
                    tags=result.get('tags', []),
                    metadata=result.get('metadata', {})
                )
                backups.append(metadata)
            
            return backups
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            return []
    
    async def delete_backup(self, backup_id: str) -> bool:
        """
        Delete backup and its metadata.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            # Delete backup file
            backup_file = self.backup_directory / f"{backup_id}.yaml"
            if backup_file.exists():
                backup_file.unlink()
            
            # Delete metadata from database
            db = await get_database()
            await db.delete(
                'changelog_config_backups',
                filters={'backup_id': backup_id}
            )
            
            self.logger.info(f"Deleted backup {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False
    
    async def export_backup(self, backup_id: str, format: str = "yaml") -> Optional[str]:
        """
        Export backup content in specified format.
        
        Args:
            backup_id: Backup identifier
            format: Export format (yaml, json)
            
        Returns:
            Backup content as string, None if failed
        """
        try:
            backup_content = await self._load_backup_content(backup_id)
            if not backup_content:
                return None
            
            if format.lower() == "json":
                return json.dumps(backup_content, indent=2, default=str)
            else:  # yaml
                return yaml.dump(backup_content, default_flow_style=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to export backup {backup_id}: {e}")
            return None
    
    async def import_backup(
        self,
        backup_content: str,
        format: str = "yaml",
        backup_type: BackupType = BackupType.MANUAL,
        created_by: str = "system"
    ) -> Optional[BackupMetadata]:
        """
        Import backup from content string.
        
        Args:
            backup_content: Backup content as string
            format: Content format (yaml, json)
            backup_type: Type of backup
            created_by: User importing the backup
            
        Returns:
            BackupMetadata if successful, None otherwise
        """
        try:
            # Parse content
            if format.lower() == "json":
                data = json.loads(backup_content)
            else:  # yaml
                data = yaml.safe_load(backup_content)
            
            # Extract metadata and configuration
            backup_metadata = data.get("backup_metadata", {})
            configuration = data.get("configuration", {})
            
            # Generate new backup ID
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            team_id = backup_metadata.get("team_id")
            new_backup_id = f"{team_id or 'global'}_imported_{timestamp}"
            
            # Update backup metadata
            backup_metadata["backup_id"] = new_backup_id
            backup_metadata["backup_type"] = backup_type.value
            backup_metadata["created_by"] = created_by
            backup_metadata["created_at"] = datetime.now(timezone.utc).isoformat()
            
            # Create new backup content
            new_backup_content = {
                "backup_metadata": backup_metadata,
                "configuration": configuration
            }
            
            # Save backup file
            backup_file = self.backup_directory / f"{new_backup_id}.yaml"
            with open(backup_file, 'w') as f:
                yaml.dump(new_backup_content, f, default_flow_style=False, indent=2)
            
            # Calculate hash and file size
            config_json = json.dumps(configuration, sort_keys=True)
            config_hash = hashlib.sha256(config_json.encode()).hexdigest()
            file_size = backup_file.stat().st_size
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=new_backup_id,
                team_id=team_id,
                backup_type=backup_type,
                created_at=datetime.now(timezone.utc),
                created_by=created_by,
                description=backup_metadata.get("description", "Imported backup"),
                file_size=file_size,
                config_hash=config_hash,
                tags=backup_metadata.get("tags", [])
            )
            
            # Store metadata
            await self._store_backup_metadata(metadata)
            
            # Validate imported backup
            validation_result = await self.validate_backup(new_backup_id)
            if validation_result.valid:
                metadata.validation_status = BackupStatus.VALIDATED
                await self._update_backup_status(new_backup_id, BackupStatus.VALIDATED)
            else:
                metadata.validation_status = BackupStatus.CORRUPTED
                await self._update_backup_status(new_backup_id, BackupStatus.CORRUPTED)
            
            self.logger.info(f"Imported backup as {new_backup_id}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to import backup: {e}")
            return None
    
    async def _store_backup_metadata(self, metadata: BackupMetadata):
        """Store backup metadata in database."""
        try:
            db = await get_database()
            
            await db.insert(
                'changelog_config_backups',
                {
                    'backup_id': metadata.backup_id,
                    'team_id': metadata.team_id,
                    'backup_type': metadata.backup_type.value,
                    'created_at': metadata.created_at.isoformat(),
                    'created_by': metadata.created_by,
                    'description': metadata.description,
                    'file_size': metadata.file_size,
                    'config_hash': metadata.config_hash,
                    'validation_status': metadata.validation_status.value,
                    'restore_count': metadata.restore_count,
                    'last_restored': metadata.last_restored.isoformat() if metadata.last_restored else None,
                    'tags': metadata.tags,
                    'metadata': metadata.metadata
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store backup metadata: {e}")
            raise
    
    async def _load_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """Load backup metadata from database."""
        try:
            db = await get_database()
            
            results = await db.select(
                'changelog_config_backups',
                filters={'backup_id': backup_id},
                limit=1
            )
            
            if not results:
                return None
            
            result = results[0]
            return BackupMetadata(
                backup_id=result['backup_id'],
                team_id=result.get('team_id'),
                backup_type=BackupType(result['backup_type']),
                created_at=result['created_at'],
                created_by=result['created_by'],
                description=result.get('description', ''),
                file_size=result.get('file_size', 0),
                config_hash=result.get('config_hash', ''),
                validation_status=BackupStatus(result.get('validation_status', 'created')),
                restore_count=result.get('restore_count', 0),
                last_restored=result.get('last_restored'),
                tags=result.get('tags', []),
                metadata=result.get('metadata', {})
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load backup metadata: {e}")
            return None
    
    async def _load_backup_content(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Load backup content from file."""
        try:
            backup_file = self.backup_directory / f"{backup_id}.yaml"
            if not backup_file.exists():
                return None
            
            with open(backup_file, 'r') as f:
                return yaml.safe_load(f)
                
        except Exception as e:
            self.logger.error(f"Failed to load backup content: {e}")
            return None
    
    async def _update_backup_status(self, backup_id: str, status: BackupStatus):
        """Update backup validation status."""
        try:
            db = await get_database()
            
            await db.update(
                'changelog_config_backups',
                {'validation_status': status.value},
                filters={'backup_id': backup_id}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update backup status: {e}")
    
    async def _update_backup_restore_info(self, backup_id: str):
        """Update backup restore information."""
        try:
            db = await get_database()
            
            # Get current restore count
            results = await db.select(
                'changelog_config_backups',
                filters={'backup_id': backup_id},
                limit=1
            )
            
            if results:
                current_count = results[0].get('restore_count', 0)
                await db.update(
                    'changelog_config_backups',
                    {
                        'restore_count': current_count + 1,
                        'last_restored': datetime.now(timezone.utc).isoformat()
                    },
                    filters={'backup_id': backup_id}
                )
            
        except Exception as e:
            self.logger.error(f"Failed to update backup restore info: {e}")
    
    async def _cleanup_old_backups(self, team_id: Optional[str]):
        """Clean up old backups based on retention policy."""
        try:
            # Get backups for team/global
            backups = await self.list_backups(team_id=team_id, limit=1000)
            
            # Sort by creation date (newest first)
            backups.sort(key=lambda x: x.created_at, reverse=True)
            
            # Keep only the most recent backups
            backups_to_delete = backups[self.max_backups_per_team:]
            
            # Also delete backups older than retention period
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.backup_retention_days)
            old_backups = [b for b in backups if b.created_at < cutoff_date]
            
            # Combine lists and remove duplicates
            all_to_delete = list(set(backups_to_delete + old_backups))
            
            # Delete old backups
            for backup in all_to_delete:
                await self.delete_backup(backup.backup_id)
                self.logger.info(f"Cleaned up old backup {backup.backup_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")
    
    async def create_scheduled_backups(self):
        """Create scheduled backups for all teams."""
        try:
            # Get all team configurations
            teams = await self.config_manager.get_all_team_configurations()
            
            # Create backup for each team
            for team_config in teams:
                await self.create_backup(
                    team_id=team_config.team_id,
                    backup_type=BackupType.SCHEDULED,
                    description=f"Scheduled backup for {team_config.team_name}",
                    created_by="scheduler",
                    tags=["scheduled", "automatic"]
                )
            
            # Create global backup
            await self.create_backup(
                team_id=None,
                backup_type=BackupType.SCHEDULED,
                description="Scheduled global configuration backup",
                created_by="scheduler",
                tags=["scheduled", "automatic", "global"]
            )
            
            self.logger.info("Completed scheduled backup creation")
            
        except Exception as e:
            self.logger.error(f"Failed to create scheduled backups: {e}")
    
    async def test_backup_integrity(self) -> Dict[str, Any]:
        """
        Test backup system integrity.
        
        Returns:
            Dictionary with test results
        """
        results = {
            "total_backups": 0,
            "valid_backups": 0,
            "corrupted_backups": 0,
            "missing_files": 0,
            "validation_errors": [],
            "test_passed": True
        }
        
        try:
            # Get all backups
            all_backups = await self.list_backups(limit=1000)
            results["total_backups"] = len(all_backups)
            
            # Validate each backup
            for backup in all_backups:
                validation_result = await self.validate_backup(backup.backup_id)
                
                if validation_result.valid:
                    results["valid_backups"] += 1
                else:
                    results["corrupted_backups"] += 1
                    results["validation_errors"].append({
                        "backup_id": backup.backup_id,
                        "errors": validation_result.errors
                    })
                
                if not validation_result.integrity_check:
                    results["missing_files"] += 1
            
            # Test passed if no corrupted backups
            results["test_passed"] = results["corrupted_backups"] == 0
            
            self.logger.info(f"Backup integrity test completed: {results['valid_backups']}/{results['total_backups']} valid")
            
        except Exception as e:
            self.logger.error(f"Backup integrity test failed: {e}")
            results["test_passed"] = False
            results["validation_errors"].append({"error": str(e)})
        
        return results
    
    def _serialize_config_for_backup(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize configuration data for backup, converting enums and datetime objects to strings."""
        def convert_objects(obj):
            if isinstance(obj, dict):
                return {key: convert_objects(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_objects(item) for item in obj]
            elif hasattr(obj, 'value'):  # Enum
                return obj.value
            elif isinstance(obj, datetime):
                return obj.isoformat()
            else:
                return obj
        
        return convert_objects(config_data)