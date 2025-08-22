#!/usr/bin/env python3
"""
Hook Configuration Management CLI Tool.

Provides command-line utilities for validating, migrating, and managing
hook configurations with comprehensive testing and backup capabilities.
"""

import asyncio
import argparse
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from devsync_ai.core.hook_configuration_validator import HookConfigurationValidator
from devsync_ai.core.hook_configuration_migration import HookConfigurationMigrator, ConfigurationBackupManager
from devsync_ai.core.hook_configuration_testing import ConfigurationValidator, ConfigurationTester


class HookConfigManager:
    """Main configuration management interface."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.validator = HookConfigurationValidator()
        self.migrator = HookConfigurationMigrator()
        self.backup_manager = ConfigurationBackupManager()
        self.config_validator = ConfigurationValidator()
        self.tester = ConfigurationTester()
    
    async def validate_config(self, config_path: str, output_format: str = "yaml") -> None:
        """Validate a configuration file."""
        print(f"Validating configuration: {config_path}")
        
        is_valid, report = await self.config_validator.validate_configuration_file(
            config_path, output_format
        )
        
        if is_valid:
            print("✅ Configuration is valid!")
        else:
            print("❌ Configuration validation failed!")
        
        print("\n" + "="*50)
        print("VALIDATION REPORT")
        print("="*50)
        print(report)
        
        sys.exit(0 if is_valid else 1)
    
    async def test_config(self, config_path: str, output_path: Optional[str] = None) -> None:
        """Run comprehensive tests on a configuration."""
        print(f"Testing configuration: {config_path}")
        
        try:
            # Load configuration
            with open(config_path, 'r') as f:
                if config_path.endswith('.json'):
                    config_data = json.load(f)
                else:
                    config_data = yaml.safe_load(f)
            
            # Run tests
            test_results = await self.tester.run_comprehensive_test_suite(config_data)
            
            # Generate report
            report = self.tester.generate_test_report(test_results, "markdown")
            
            # Output report
            if output_path:
                with open(output_path, 'w') as f:
                    f.write(report)
                print(f"Test report saved to: {output_path}")
            else:
                print("\n" + "="*50)
                print("TEST REPORT")
                print("="*50)
                print(report)
            
            # Summary
            total_tests = sum(suite.total_tests for suite in test_results.values())
            total_passed = sum(suite.passed_tests for suite in test_results.values())
            pass_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
            
            print(f"\nTest Summary: {total_passed}/{total_tests} passed ({pass_rate:.1f}%)")
            
            if total_passed == total_tests:
                print("✅ All tests passed!")
                sys.exit(0)
            else:
                print("❌ Some tests failed!")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Testing failed: {e}")
            sys.exit(1)
    
    async def migrate_config(
        self, 
        config_path: str, 
        target_version: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> None:
        """Migrate a configuration to a target version."""
        print(f"Migrating configuration: {config_path}")
        
        try:
            # Load configuration
            with open(config_path, 'r') as f:
                if config_path.endswith('.json'):
                    config_data = json.load(f)
                else:
                    config_data = yaml.safe_load(f)
            
            current_version = config_data.get("version", "1.0.0")
            target_version = target_version or self.migrator._current_version
            
            print(f"Current version: {current_version}")
            print(f"Target version: {target_version}")
            
            # Check migration path
            migration_info = self.migrator.get_migration_info(current_version, target_version)
            if not migration_info["available"]:
                print(f"❌ {migration_info['reason']}")
                sys.exit(1)
            
            print(f"Migration steps required: {migration_info['total_steps']}")
            for step in migration_info["steps"]:
                print(f"  - {step['from_version']} → {step['to_version']}: {step['description']}")
            
            # Perform migration
            result = await self.migrator.migrate_configuration(config_data, target_version)
            
            if result.success:
                print("✅ Migration completed successfully!")
                print(f"Backup created: {result.backup_path}")
                
                for change in result.changes_made:
                    print(f"  - {change}")
                
                # Save migrated configuration
                output_file = output_path or config_path
                with open(output_file, 'w') as f:
                    if output_file.endswith('.json'):
                        json.dump(config_data, f, indent=2)
                    else:
                        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
                
                print(f"Migrated configuration saved to: {output_file}")
                
            else:
                print("❌ Migration failed!")
                for error in result.errors:
                    print(f"  - {error}")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            sys.exit(1)
    
    async def backup_config(self, config_path: str, backup_name: Optional[str] = None) -> None:
        """Create a backup of a configuration."""
        print(f"Creating backup of: {config_path}")
        
        try:
            # Load configuration
            with open(config_path, 'r') as f:
                if config_path.endswith('.json'):
                    config_data = json.load(f)
                else:
                    config_data = yaml.safe_load(f)
            
            # Create backup
            backup_path = await self.backup_manager.create_backup(config_data, backup_name)
            print(f"✅ Backup created: {backup_path}")
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            sys.exit(1)
    
    async def list_backups(self, team_id: Optional[str] = None) -> None:
        """List available backups."""
        print("Available backups:")
        
        try:
            backups = await self.backup_manager.list_backups(team_id)
            
            if not backups:
                print("No backups found.")
                return
            
            print(f"{'Filename':<40} {'Team ID':<15} {'Version':<10} {'Created':<20} {'Size':<10}")
            print("-" * 100)
            
            for backup in backups:
                size_kb = backup["size_bytes"] / 1024
                created = backup["created_at"] or "Unknown"
                if len(created) > 19:
                    created = created[:19]
                
                print(f"{backup['filename']:<40} {backup['team_id']:<15} {backup['version']:<10} {created:<20} {size_kb:.1f}KB")
            
        except Exception as e:
            print(f"❌ Failed to list backups: {e}")
            sys.exit(1)
    
    async def restore_backup(self, backup_path: str, output_path: str) -> None:
        """Restore a configuration from backup."""
        print(f"Restoring backup: {backup_path}")
        
        try:
            # Restore configuration
            config_data = await self.backup_manager.restore_backup(backup_path)
            
            # Save restored configuration
            with open(output_path, 'w') as f:
                if output_path.endswith('.json'):
                    json.dump(config_data, f, indent=2)
                else:
                    yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            
            print(f"✅ Configuration restored to: {output_path}")
            
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            sys.exit(1)
    
    async def cleanup_backups(self, keep_count: int = 10) -> None:
        """Clean up old backups."""
        print(f"Cleaning up old backups (keeping {keep_count} per team)...")
        
        try:
            deleted_count = await self.backup_manager.cleanup_old_backups(keep_count)
            print(f"✅ Deleted {deleted_count} old backup(s)")
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            sys.exit(1)
    
    def show_help(self) -> None:
        """Show validation help and examples."""
        help_info = self.validator.get_validation_help()
        
        print("Hook Configuration Validation Help")
        print("=" * 50)
        
        print("\nAvailable Fields:")
        for field_name, field_info in help_info["fields"].items():
            print(f"  {field_name}")
            print(f"    Type: {field_info['data_type']}")
            print(f"    Description: {field_info['description']}")
            print(f"    Valid Operators: {', '.join(field_info['valid_operators'])}")
            if field_info['example_values']:
                print(f"    Example Values: {', '.join(map(str, field_info['example_values'][:3]))}")
            print()
        
        print("\nAvailable Operators:")
        for op_name, op_info in help_info["operators"].items():
            print(f"  {op_name}")
            print(f"    Description: {op_info['description']}")
            print(f"    Valid Types: {', '.join(op_info['valid_types'])}")
            print(f"    Requires Value: {op_info['requires_value']}")
            print(f"    Example: {op_info['example']}")
            print()
        
        print(f"\nValid Hook Types: {', '.join(help_info['hook_types'])}")
        
        print("\nExample Configurations:")
        for example_name, example_data in help_info["examples"].items():
            print(f"\n{example_name}:")
            print(yaml.dump(example_data, default_flow_style=False, indent=2))
    
    def show_versions(self) -> None:
        """Show available configuration versions."""
        versions = self.migrator.get_available_versions()
        current = self.migrator._current_version
        
        print("Available Configuration Versions:")
        print("-" * 40)
        
        for version in versions:
            marker = " (current)" if version == current else ""
            print(f"  {version}{marker}")
        
        print(f"\nLatest version: {current}")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Hook Configuration Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a configuration file
  python hook_config_manager.py validate config/team_config.yaml
  
  # Run comprehensive tests
  python hook_config_manager.py test config/team_config.yaml --output report.md
  
  # Migrate configuration to latest version
  python hook_config_manager.py migrate config/team_config.yaml
  
  # Create a backup
  python hook_config_manager.py backup config/team_config.yaml --name "before_changes"
  
  # List available backups
  python hook_config_manager.py list-backups
  
  # Restore from backup
  python hook_config_manager.py restore backups/backup_file.yaml config/restored_config.yaml
  
  # Show validation help
  python hook_config_manager.py help
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate configuration file")
    validate_parser.add_argument("config_path", help="Path to configuration file")
    validate_parser.add_argument("--format", choices=["yaml", "json", "markdown"], 
                               default="yaml", help="Output format")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run comprehensive tests")
    test_parser.add_argument("config_path", help="Path to configuration file")
    test_parser.add_argument("--output", help="Output path for test report")
    
    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate configuration")
    migrate_parser.add_argument("config_path", help="Path to configuration file")
    migrate_parser.add_argument("--version", help="Target version (defaults to latest)")
    migrate_parser.add_argument("--output", help="Output path (defaults to input path)")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create configuration backup")
    backup_parser.add_argument("config_path", help="Path to configuration file")
    backup_parser.add_argument("--name", help="Custom backup name")
    
    # List backups command
    list_parser = subparsers.add_parser("list-backups", help="List available backups")
    list_parser.add_argument("--team", help="Filter by team ID")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_path", help="Path to backup file")
    restore_parser.add_argument("output_path", help="Output path for restored config")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old backups")
    cleanup_parser.add_argument("--keep", type=int, default=10, 
                               help="Number of backups to keep per team")
    
    # Help command
    subparsers.add_parser("help", help="Show validation help and examples")
    
    # Versions command
    subparsers.add_parser("versions", help="Show available configuration versions")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = HookConfigManager()
    
    try:
        if args.command == "validate":
            await manager.validate_config(args.config_path, args.format)
        elif args.command == "test":
            await manager.test_config(args.config_path, args.output)
        elif args.command == "migrate":
            await manager.migrate_config(args.config_path, args.version, args.output)
        elif args.command == "backup":
            await manager.backup_config(args.config_path, args.name)
        elif args.command == "list-backups":
            await manager.list_backups(args.team)
        elif args.command == "restore":
            await manager.restore_backup(args.backup_path, args.output_path)
        elif args.command == "cleanup":
            await manager.cleanup_backups(args.keep)
        elif args.command == "help":
            manager.show_help()
        elif args.command == "versions":
            manager.show_versions()
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())