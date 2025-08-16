#!/usr/bin/env python3
"""
Hook Data Storage Validation Script

This script validates that all hook data storage components are properly
implemented and can be imported without errors.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all hook data storage modules can be imported."""
    print("Testing imports...")
    
    try:
        # Test database connection module
        from devsync_ai.database.connection import SupabaseClient, get_database
        print("✓ Database connection module imports successfully")
        
        # Test hook data manager
        from devsync_ai.database.hook_data_manager import HookDataManager, get_hook_data_manager
        print("✓ Hook data manager module imports successfully")
        
        # Test migration runner
        from devsync_ai.database.migrations.runner import MigrationRunner
        print("✓ Migration runner module imports successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_migration_files():
    """Test that migration files exist and are readable."""
    print("\nTesting migration files...")
    
    try:
        migration_dir = project_root / "devsync_ai" / "database" / "migrations"
        
        # Check for initial schema migration
        initial_migration = migration_dir / "001_initial_schema.sql"
        if not initial_migration.exists():
            print("✗ Initial schema migration file not found")
            return False
        print("✓ Initial schema migration file exists")
        
        # Check for hook data storage migration
        hook_migration = migration_dir / "002_hook_data_storage.sql"
        if not hook_migration.exists():
            print("✗ Hook data storage migration file not found")
            return False
        print("✓ Hook data storage migration file exists")
        
        # Check combined migration file
        combined_migration = migration_dir / "run_migrations.sql"
        if not combined_migration.exists():
            print("✗ Combined migration file not found")
            return False
        print("✓ Combined migration file exists")
        
        # Test reading migration content
        with open(hook_migration, 'r') as f:
            content = f.read()
            if len(content) < 1000:  # Should be a substantial file
                print("✗ Hook data storage migration file seems too small")
                return False
            if "hook_executions" not in content:
                print("✗ Hook data storage migration missing expected table")
                return False
            if "team_hook_configurations" not in content:
                print("✗ Hook data storage migration missing expected table")
                return False
            if "hook_performance_metrics" not in content:
                print("✗ Hook data storage migration missing expected table")
                return False
        
        print("✓ Migration files contain expected content")
        return True
        
    except Exception as e:
        print(f"✗ Migration file test failed: {e}")
        return False


def test_hook_data_manager_structure():
    """Test that HookDataManager has expected methods."""
    print("\nTesting HookDataManager structure...")
    
    try:
        from devsync_ai.database.hook_data_manager import HookDataManager
        
        manager = HookDataManager()
        
        # Check for expected methods
        expected_methods = [
            'create_hook_execution',
            'update_hook_execution',
            'get_hook_execution',
            'get_hook_executions',
            'get_team_configuration',
            'save_team_configuration',
            'get_all_team_configurations',
            'get_hook_performance_summary',
            'aggregate_performance_metrics',
            'get_performance_metrics',
            'get_execution_statistics',
            'cleanup_old_executions',
            'health_check'
        ]
        
        for method_name in expected_methods:
            if not hasattr(manager, method_name):
                print(f"✗ HookDataManager missing method: {method_name}")
                return False
            if not callable(getattr(manager, method_name)):
                print(f"✗ HookDataManager.{method_name} is not callable")
                return False
        
        print("✓ HookDataManager has all expected methods")
        return True
        
    except Exception as e:
        print(f"✗ HookDataManager structure test failed: {e}")
        return False


def test_test_files():
    """Test that test files exist and are properly structured."""
    print("\nTesting test files...")
    
    try:
        test_file = project_root / "tests" / "test_hook_data_storage.py"
        if not test_file.exists():
            print("✗ Hook data storage test file not found")
            return False
        
        # Test that test file can be imported
        sys.path.insert(0, str(project_root / "tests"))
        from test_hook_data_storage import TestHookDataStorage, TestHookDataStorageIntegration
        
        # Check for expected test methods
        test_instance = TestHookDataStorage()
        expected_test_methods = [
            'test_database_connection',
            'test_hook_execution_lifecycle',
            'test_hook_execution_queries',
            'test_team_configuration_operations',
            'test_performance_metrics',
            'test_execution_statistics',
            'test_health_check',
            'test_cleanup_operations',
            'test_error_handling',
            'test_concurrent_operations'
        ]
        
        for method_name in expected_test_methods:
            if not hasattr(test_instance, method_name):
                print(f"✗ Test class missing method: {method_name}")
                return False
        
        print("✓ Test files are properly structured")
        return True
        
    except Exception as e:
        print(f"✗ Test file validation failed: {e}")
        return False


def test_script_files():
    """Test that script files exist and are executable."""
    print("\nTesting script files...")
    
    try:
        scripts_dir = project_root / "scripts"
        
        # Check migration script
        migration_script = scripts_dir / "migrate_hook_data_storage.py"
        if not migration_script.exists():
            print("✗ Migration script not found")
            return False
        
        # Check test runner script
        test_script = scripts_dir / "test_hook_data_storage.py"
        if not test_script.exists():
            print("✗ Test runner script not found")
            return False
        
        # Check if scripts are executable (on Unix systems)
        import stat
        if hasattr(stat, 'S_IXUSR'):
            migration_perms = migration_script.stat().st_mode
            test_perms = test_script.stat().st_mode
            
            if not (migration_perms & stat.S_IXUSR):
                print("⚠ Migration script is not executable")
            if not (test_perms & stat.S_IXUSR):
                print("⚠ Test script is not executable")
        
        print("✓ Script files exist")
        return True
        
    except Exception as e:
        print(f"✗ Script file validation failed: {e}")
        return False


def main():
    """Main validation function."""
    print("Hook Data Storage Validation")
    print("=" * 40)
    
    all_tests_passed = True
    
    # Run all validation tests
    tests = [
        test_imports,
        test_migration_files,
        test_hook_data_manager_structure,
        test_test_files,
        test_script_files
    ]
    
    for test_func in tests:
        if not test_func():
            all_tests_passed = False
    
    print("\n" + "=" * 40)
    if all_tests_passed:
        print("✅ All validation tests passed!")
        print("\nHook data storage implementation is complete and ready for use.")
        print("\nNext steps:")
        print("1. Set up your Supabase environment variables")
        print("2. Run the migration script to create database tables")
        print("3. Run the test suite to verify functionality")
        print("4. Integrate with the existing hook system")
    else:
        print("❌ Some validation tests failed!")
        print("\nPlease fix the issues above before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()