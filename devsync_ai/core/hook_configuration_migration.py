"""
Hook Configuration Migration Tools.

This module provides comprehensive migration utilities for hook configurations,
including version migration, schema updates, and configuration transformation.
"""

import json
import yaml
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from copy import deepcopy

from devsync_ai.core.hook_configuration_manager import ValidationResult


logger = logging.getLogger(__name__)


@dataclass
class MigrationStep:
    """Represents a single migration step."""
    from_version: str
    to_version: str
    description: str
    migration_function: Callable[[Dict[str, Any]], Dict[str, Any]]
    required: bool = True
    backup_required: bool = True


@dataclass
class MigrationResult:
    """Result of a configuration migration."""
    success: bool
    from_version: str
    to_version: str
    errors: List[str]
    warnings: List[str]
    changes_made: List[str]
    backup_path: Optional[str] = None


class HookConfigurationMigrator:
    """
    Handles migration of hook configurations between versions.
    
    Provides version-aware migration with backup and rollback capabilities.
    """
    
    def __init__(self, backup_dir: Optional[Path] = None):
        """
        Initialize the migrator.
        
        Args:
            backup_dir: Directory for configuration backups
        """
        self.backup_dir = backup_dir or Path("config/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Define migration steps
        self._migration_steps = self._define_migration_steps()
        self._current_version = "1.2.0"  # Latest version
    
    def _define_migration_steps(self) -> List[MigrationStep]:
        """Define all available migration steps."""
        return [
            MigrationStep(
                from_version="1.0.0",
                to_version="1.1.0",
                description="Add notification preferences and business hours",
                migration_function=self._migrate_1_0_to_1_1
            ),
            MigrationStep(
                from_version="1.1.0",
                to_version="1.2.0",
                description="Add escalation rules and enhanced metadata",
                migration_function=self._migrate_1_1_to_1_2
            ),
        ]
    
    async def migrate_configuration(
        self, 
        config_data: Dict[str, Any], 
        target_version: Optional[str] = None
    ) -> MigrationResult:
        """
        Migrate configuration to target version.
        
        Args:
            config_data: Configuration data to migrate
            target_version: Target version (defaults to latest)
            
        Returns:
            MigrationResult with migration details
        """
        target_version = target_version or self._current_version
        current_version = config_data.get("version", "1.0.0")
        
        if current_version == target_version:
            return MigrationResult(
                success=True,
                from_version=current_version,
                to_version=target_version,
                errors=[],
                warnings=[],
                changes_made=["No migration needed - already at target version"]
            )
        
        # Create backup
        backup_path = None
        try:
            backup_path = await self._create_backup(config_data, current_version)
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return MigrationResult(
                success=False,
                from_version=current_version,
                to_version=target_version,
                errors=[f"Failed to create backup: {e}"],
                warnings=[],
                changes_made=[]
            )
        
        # Find migration path
        migration_path = self._find_migration_path(current_version, target_version)
        if not migration_path:
            return MigrationResult(
                success=False,
                from_version=current_version,
                to_version=target_version,
                errors=[f"No migration path found from {current_version} to {target_version}"],
                warnings=[],
                changes_made=[],
                backup_path=str(backup_path)
            )
        
        # Apply migrations
        migrated_config = deepcopy(config_data)
        errors = []
        warnings = []
        changes_made = []
        
        for step in migration_path:
            try:
                logger.info(f"Applying migration: {step.description}")
                migrated_config = step.migration_function(migrated_config)
                migrated_config["version"] = step.to_version
                migrated_config["migration_timestamp"] = datetime.utcnow().isoformat()
                changes_made.append(f"Applied migration to {step.to_version}: {step.description}")
            except Exception as e:
                error_msg = f"Migration failed at {step.to_version}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                break
        
        return MigrationResult(
            success=len(errors) == 0,
            from_version=current_version,
            to_version=migrated_config.get("version", current_version),
            errors=errors,
            warnings=warnings,
            changes_made=changes_made,
            backup_path=str(backup_path)
        )
    
    def _find_migration_path(self, from_version: str, to_version: str) -> List[MigrationStep]:
        """Find the migration path between versions."""
        # Simple linear migration path for now
        path = []
        current = from_version
        
        while current != to_version:
            found_step = None
            for step in self._migration_steps:
                if step.from_version == current:
                    found_step = step
                    break
            
            if not found_step:
                return []  # No path found
            
            path.append(found_step)
            current = found_step.to_version
            
            # Prevent infinite loops
            if len(path) > 10:
                return []
        
        return path
    
    async def _create_backup(self, config_data: Dict[str, Any], version: str) -> Path:
        """Create a backup of the configuration."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        team_id = config_data.get("team_id", "unknown")
        backup_filename = f"hook_config_{team_id}_{version}_{timestamp}.yaml"
        backup_path = self.backup_dir / backup_filename
        
        with open(backup_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Created configuration backup: {backup_path}")
        return backup_path
    
    def _migrate_1_0_to_1_1(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from version 1.0.0 to 1.1.0."""
        migrated = deepcopy(config_data)
        
        # Add notification preferences if missing
        if "notification_preferences" not in migrated:
            migrated["notification_preferences"] = {
                "batch_threshold": 5,
                "batch_timeout_minutes": 15,
                "quiet_hours": {
                    "enabled": True,
                    "start": "22:00",
                    "end": "08:00"
                },
                "weekend_notifications": False
            }
        
        # Add business hours if missing
        if "business_hours" not in migrated:
            migrated["business_hours"] = {
                "start": "09:00",
                "end": "17:00",
                "timezone": "UTC",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
            }
        
        # Update rule format if needed
        if "rules" in migrated:
            for rule in migrated["rules"]:
                # Add priority if missing
                if "priority" not in rule:
                    rule["priority"] = 50
                
                # Ensure metadata exists
                if "metadata" not in rule:
                    rule["metadata"] = {}
        
        return migrated
    
    def _migrate_1_1_to_1_2(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from version 1.1.0 to 1.2.0."""
        migrated = deepcopy(config_data)
        
        # Add escalation rules if missing
        if "escalation_rules" not in migrated:
            migrated["escalation_rules"] = [
                {
                    "condition": "urgency == 'critical'",
                    "escalate_after_minutes": 15,
                    "escalate_to": ["@channel"]
                },
                {
                    "condition": "urgency == 'high'",
                    "escalate_after_minutes": 60,
                    "escalate_to": ["team-leads"]
                }
            ]
        
        # Enhance rule metadata
        if "rules" in migrated:
            for rule in migrated["rules"]:
                metadata = rule.get("metadata", {})
                
                # Add escalation settings
                if "escalation_enabled" not in metadata:
                    metadata["escalation_enabled"] = True
                
                # Add quiet hours override
                if "ignore_quiet_hours" not in metadata:
                    metadata["ignore_quiet_hours"] = False
                
                rule["metadata"] = metadata
        
        # Add configuration metadata
        if "configuration_metadata" not in migrated:
            migrated["configuration_metadata"] = {
                "created_by": "system",
                "created_at": datetime.utcnow().isoformat(),
                "description": "Migrated configuration"
            }
        
        return migrated
    
    async def rollback_configuration(
        self, 
        backup_path: str, 
        target_config_path: str
    ) -> MigrationResult:
        """
        Rollback configuration from backup.
        
        Args:
            backup_path: Path to backup file
            target_config_path: Path to restore configuration to
            
        Returns:
            MigrationResult with rollback details
        """
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return MigrationResult(
                    success=False,
                    from_version="unknown",
                    to_version="unknown",
                    errors=[f"Backup file not found: {backup_path}"],
                    warnings=[],
                    changes_made=[]
                )
            
            # Load backup
            with open(backup_file, 'r') as f:
                backup_config = yaml.safe_load(f)
            
            # Save to target
            target_file = Path(target_config_path)
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(target_file, 'w') as f:
                yaml.dump(backup_config, f, default_flow_style=False, sort_keys=False)
            
            return MigrationResult(
                success=True,
                from_version="current",
                to_version=backup_config.get("version", "unknown"),
                errors=[],
                warnings=[],
                changes_made=[f"Restored configuration from backup: {backup_path}"]
            )
            
        except Exception as e:
            return MigrationResult(
                success=False,
                from_version="unknown",
                to_version="unknown",
                errors=[f"Rollback failed: {e}"],
                warnings=[],
                changes_made=[]
            )
    
    def get_available_versions(self) -> List[str]:
        """Get list of available configuration versions."""
        versions = set(["1.0.0"])  # Base version
        
        for step in self._migration_steps:
            versions.add(step.from_version)
            versions.add(step.to_version)
        
        return sorted(versions)
    
    def get_migration_info(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """Get information about a migration path."""
        path = self._find_migration_path(from_version, to_version)
        
        if not path:
            return {
                "available": False,
                "reason": f"No migration path from {from_version} to {to_version}"
            }
        
        return {
            "available": True,
            "steps": [
                {
                    "from_version": step.from_version,
                    "to_version": step.to_version,
                    "description": step.description,
                    "required": step.required,
                    "backup_required": step.backup_required
                }
                for step in path
            ],
            "total_steps": len(path)
        }


class ConfigurationBackupManager:
    """Manages configuration backups and restore operations."""
    
    def __init__(self, backup_dir: Optional[Path] = None):
        """Initialize backup manager."""
        self.backup_dir = backup_dir or Path("config/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_backup(
        self, 
        config_data: Dict[str, Any], 
        backup_name: Optional[str] = None
    ) -> str:
        """
        Create a configuration backup.
        
        Args:
            config_data: Configuration to backup
            backup_name: Optional custom backup name
            
        Returns:
            Path to created backup file
        """
        if backup_name:
            backup_filename = f"{backup_name}.yaml"
        else:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            team_id = config_data.get("team_id", "unknown")
            version = config_data.get("version", "unknown")
            backup_filename = f"backup_{team_id}_{version}_{timestamp}.yaml"
        
        backup_path = self.backup_dir / backup_filename
        
        # Add backup metadata
        backup_data = deepcopy(config_data)
        backup_data["backup_metadata"] = {
            "created_at": datetime.utcnow().isoformat(),
            "original_version": config_data.get("version", "unknown"),
            "backup_name": backup_name or "auto"
        }
        
        with open(backup_path, 'w') as f:
            yaml.dump(backup_data, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Created configuration backup: {backup_path}")
        return str(backup_path)
    
    async def list_backups(self, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available backups.
        
        Args:
            team_id: Optional team ID filter
            
        Returns:
            List of backup information
        """
        backups = []
        
        for backup_file in self.backup_dir.glob("*.yaml"):
            try:
                with open(backup_file, 'r') as f:
                    backup_data = yaml.safe_load(f)
                
                backup_team_id = backup_data.get("team_id", "unknown")
                
                # Filter by team_id if specified
                if team_id and backup_team_id != team_id:
                    continue
                
                backup_info = {
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "team_id": backup_team_id,
                    "version": backup_data.get("version", "unknown"),
                    "created_at": backup_data.get("backup_metadata", {}).get("created_at"),
                    "size_bytes": backup_file.stat().st_size,
                    "backup_name": backup_data.get("backup_metadata", {}).get("backup_name")
                }
                
                backups.append(backup_info)
                
            except Exception as e:
                logger.warning(f"Failed to read backup file {backup_file}: {e}")
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return backups
    
    async def restore_backup(self, backup_path: str) -> Dict[str, Any]:
        """
        Restore configuration from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Restored configuration data
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        with open(backup_file, 'r') as f:
            backup_data = yaml.safe_load(f)
        
        # Remove backup metadata from restored config
        restored_config = deepcopy(backup_data)
        restored_config.pop("backup_metadata", None)
        
        return restored_config
    
    async def delete_backup(self, backup_path: str) -> bool:
        """
        Delete a backup file.
        
        Args:
            backup_path: Path to backup file to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            backup_file = Path(backup_path)
            if backup_file.exists():
                backup_file.unlink()
                logger.info(f"Deleted backup: {backup_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_path}: {e}")
            return False
    
    async def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Clean up old backup files, keeping only the most recent ones.
        
        Args:
            keep_count: Number of backups to keep per team
            
        Returns:
            Number of backups deleted
        """
        backups_by_team = {}
        
        # Group backups by team
        for backup_file in self.backup_dir.glob("*.yaml"):
            try:
                with open(backup_file, 'r') as f:
                    backup_data = yaml.safe_load(f)
                
                team_id = backup_data.get("team_id", "unknown")
                if team_id not in backups_by_team:
                    backups_by_team[team_id] = []
                
                backups_by_team[team_id].append({
                    "path": backup_file,
                    "created_at": backup_data.get("backup_metadata", {}).get("created_at", "")
                })
                
            except Exception as e:
                logger.warning(f"Failed to read backup file {backup_file}: {e}")
        
        deleted_count = 0
        
        # Clean up old backups for each team
        for team_id, team_backups in backups_by_team.items():
            # Sort by creation time (newest first)
            team_backups.sort(key=lambda x: x["created_at"], reverse=True)
            
            # Delete old backups
            for backup in team_backups[keep_count:]:
                try:
                    backup["path"].unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {backup['path']}")
                except Exception as e:
                    logger.error(f"Failed to delete backup {backup['path']}: {e}")
        
        return deleted_count