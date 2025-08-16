#!/usr/bin/env python3
"""
Hook Data Storage Migration Script

This script applies the hook data storage migration to create the necessary
database tables and functions for JIRA Agent Hook data storage.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from devsync_ai.database.connection import get_database
from devsync_ai.database.migrations.runner import MigrationRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_database_connection():
    """Check if database connection is working."""
    try:
        db = await get_database()
        healthy = await db.health_check()
        if healthy:
            logger.info("✓ Database connection successful")
            return True
        else:
            logger.error("✗ Database connection failed health check")
            return False
    except Exception as e:
        logger.error(f"✗ Database connection error: {e}")
        return False


async def check_existing_tables():
    """Check if hook data storage tables already exist."""
    try:
        db = await get_database()
        
        # Check for hook_executions table
        result = await db.select(
            "information_schema.tables",
            filters={
                "table_schema": "public",
                "table_name": "hook_executions"
            },
            limit=1
        )
        
        if result:
            logger.info("✓ Hook data storage tables already exist")
            return True
        else:
            logger.info("ℹ Hook data storage tables do not exist yet")
            return False
    except Exception as e:
        logger.error(f"✗ Error checking existing tables: {e}")
        return False


async def verify_migration_success():
    """Verify that the migration was successful."""
    try:
        db = await get_database()
        
        # Check that all expected tables exist
        expected_tables = [
            "hook_executions",
            "team_hook_configurations", 
            "hook_performance_metrics"
        ]
        
        for table_name in expected_tables:
            result = await db.select(
                "information_schema.tables",
                filters={
                    "table_schema": "public",
                    "table_name": table_name
                },
                limit=1
            )
            
            if not result:
                logger.error(f"✗ Table {table_name} was not created")
                return False
            else:
                logger.info(f"✓ Table {table_name} exists")
        
        # Check that functions exist
        expected_functions = [
            "validate_team_hook_configuration",
            "get_team_hook_configuration",
            "get_hook_performance_summary",
            "aggregate_hook_performance_metrics"
        ]
        
        for function_name in expected_functions:
            result = await db.select(
                "information_schema.routines",
                filters={
                    "routine_schema": "public",
                    "routine_name": function_name
                },
                limit=1
            )
            
            if not result:
                logger.error(f"✗ Function {function_name} was not created")
                return False
            else:
                logger.info(f"✓ Function {function_name} exists")
        
        logger.info("✓ Migration verification successful")
        return True
        
    except Exception as e:
        logger.error(f"✗ Migration verification failed: {e}")
        return False


async def test_basic_operations():
    """Test basic database operations with the new schema."""
    try:
        from devsync_ai.database.hook_data_manager import get_hook_data_manager
        
        hook_data_manager = await get_hook_data_manager()
        
        # Test health check
        health = await hook_data_manager.health_check()
        if not health["database_healthy"]:
            logger.error("✗ Hook data manager health check failed")
            return False
        
        logger.info("✓ Hook data manager health check passed")
        
        # Test team configuration operations
        test_config = {
            "team_name": "Migration Test Team",
            "default_channels": {"general": "#migration-test"},
            "rules": [],
            "metadata": {}
        }
        
        success = await hook_data_manager.save_team_configuration(
            "migration_test", test_config
        )
        
        if not success:
            logger.error("✗ Failed to save test team configuration")
            return False
        
        logger.info("✓ Team configuration operations working")
        
        # Test hook execution operations
        execution_id = await hook_data_manager.create_hook_execution(
            hook_id="migration_test_hook",
            hook_type="StatusChangeHook",
            team_id="migration_test",
            event_type="jira:test_event"
        )
        
        if not execution_id:
            logger.error("✗ Failed to create test hook execution")
            return False
        
        logger.info("✓ Hook execution operations working")
        
        # Update the execution
        update_success = await hook_data_manager.update_hook_execution(
            execution_id=execution_id,
            status="SUCCESS",
            execution_time_ms=100.0
        )
        
        if not update_success:
            logger.error("✗ Failed to update test hook execution")
            return False
        
        logger.info("✓ Hook execution update operations working")
        
        logger.info("✓ Basic operations test successful")
        return True
        
    except Exception as e:
        logger.error(f"✗ Basic operations test failed: {e}")
        return False


def print_migration_instructions():
    """Print instructions for manual migration execution."""
    migration_file = project_root / "devsync_ai" / "database" / "migrations" / "002_hook_data_storage.sql"
    
    print("\n" + "=" * 80)
    print("HOOK DATA STORAGE MIGRATION INSTRUCTIONS")
    print("=" * 80)
    print()
    print("To apply the hook data storage migration:")
    print()
    print("1. Log into your Supabase dashboard at https://app.supabase.com")
    print("2. Navigate to your project and go to the SQL Editor")
    print("3. Copy the contents of the following file:")
    print(f"   {migration_file}")
    print("4. Paste the SQL into the SQL Editor")
    print("5. Click 'Run' to execute the migration")
    print("6. Run this script again to verify the migration")
    print()
    print("Migration file location:")
    print(f"  {migration_file}")
    print()
    print("After running the migration, you can test it with:")
    print(f"  python {__file__} --test")
    print("=" * 80)
    print()


async def main():
    """Main migration function."""
    print("Hook Data Storage Migration Script")
    print("=" * 40)
    
    # Check command line arguments
    test_only = "--test" in sys.argv
    force = "--force" in sys.argv
    
    # Check database connection
    if not await check_database_connection():
        print("\n✗ Cannot proceed without database connection")
        sys.exit(1)
    
    # Check if tables already exist
    tables_exist = await check_existing_tables()
    
    if tables_exist and not force and not test_only:
        print("\n✓ Hook data storage tables already exist")
        print("Use --force to run verification anyway")
        print("Use --test to run basic operations test")
        return
    
    if test_only:
        print("\nRunning basic operations test...")
        if await test_basic_operations():
            print("\n✓ All tests passed!")
        else:
            print("\n✗ Some tests failed")
            sys.exit(1)
        return
    
    # Since we can't execute SQL directly through the Python client,
    # provide instructions for manual execution
    print("\nThis script cannot execute SQL migrations directly.")
    print("Please follow the manual migration instructions below.")
    
    print_migration_instructions()
    
    # Ask user to confirm they've run the migration
    if not force:
        response = input("\nHave you executed the migration in Supabase? (y/N): ")
        if response.lower() != 'y':
            print("Please run the migration first, then run this script again.")
            return
    
    # Verify migration
    print("\nVerifying migration...")
    if await verify_migration_success():
        print("\n✓ Migration verification successful!")
        
        # Run basic operations test
        print("\nTesting basic operations...")
        if await test_basic_operations():
            print("\n✓ Hook data storage migration completed successfully!")
        else:
            print("\n⚠ Migration completed but basic operations test failed")
            print("Please check the logs for details")
    else:
        print("\n✗ Migration verification failed")
        print("Please check that the migration was executed correctly")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())