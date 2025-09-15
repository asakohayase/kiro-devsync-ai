#!/usr/bin/env python3
"""
Hook Data Storage Test Runner

This script runs the database integration tests for hook data storage.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_environment():
    """Check if the test environment is properly configured."""
    required_env_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    missing_vars = []
    
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables before running tests")
        return False
    
    logger.info("✓ Environment variables configured")
    return True


async def run_database_tests():
    """Run the database integration tests."""
    try:
        # Import test modules
        from tests.test_hook_data_storage import TestHookDataStorage, TestHookDataStorageIntegration
        from devsync_ai.database.connection import get_database
        
        # Check database connection first
        logger.info("Checking database connection...")
        db = await get_database()
        healthy = await db.health_check()
        
        if not healthy:
            logger.error("✗ Database connection failed")
            return False
        
        logger.info("✓ Database connection successful")
        
        # Run basic tests
        logger.info("Running hook data storage tests...")
        
        test_instance = TestHookDataStorage()
        
        # Test database connection
        await test_instance.test_database_connection()
        logger.info("✓ Database connection test passed")
        
        # Test hook execution lifecycle
        from devsync_ai.database.hook_data_manager import get_hook_data_manager
        hook_data_manager = await get_hook_data_manager()
        
        await test_instance.test_hook_execution_lifecycle(hook_data_manager)
        logger.info("✓ Hook execution lifecycle test passed")
        
        # Test team configuration operations
        sample_config = {
            "team_name": "Test Team",
            "default_channels": {"general": "#test"},
            "rules": [],
            "metadata": {}
        }
        await test_instance.test_team_configuration_operations(hook_data_manager, sample_config)
        logger.info("✓ Team configuration operations test passed")
        
        # Test health check
        await test_instance.test_health_check(hook_data_manager)
        logger.info("✓ Health check test passed")
        
        # Run integration test
        logger.info("Running integration tests...")
        integration_test = TestHookDataStorageIntegration()
        await integration_test.test_full_integration_workflow()
        logger.info("✓ Integration test passed")
        
        logger.info("✓ All database tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Database tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_performance_tests():
    """Run performance-related tests."""
    try:
        from tests.test_hook_data_storage import TestHookDataStorage
        from devsync_ai.database.hook_data_manager import get_hook_data_manager
        
        logger.info("Running performance tests...")
        
        test_instance = TestHookDataStorage()
        hook_data_manager = await get_hook_data_manager()
        
        # Test performance metrics
        await test_instance.test_performance_metrics(hook_data_manager)
        logger.info("✓ Performance metrics test passed")
        
        # Test execution statistics
        await test_instance.test_execution_statistics(hook_data_manager)
        logger.info("✓ Execution statistics test passed")
        
        # Test concurrent operations
        await test_instance.test_concurrent_operations(hook_data_manager)
        logger.info("✓ Concurrent operations test passed")
        
        logger.info("✓ All performance tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Performance tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_error_handling_tests():
    """Run error handling tests."""
    try:
        from tests.test_hook_data_storage import TestHookDataStorage
        from devsync_ai.database.hook_data_manager import get_hook_data_manager
        
        logger.info("Running error handling tests...")
        
        test_instance = TestHookDataStorage()
        hook_data_manager = await get_hook_data_manager()
        
        # Test error handling
        await test_instance.test_error_handling(hook_data_manager)
        logger.info("✓ Error handling test passed")
        
        # Test cleanup operations
        await test_instance.test_cleanup_operations(hook_data_manager)
        logger.info("✓ Cleanup operations test passed")
        
        logger.info("✓ All error handling tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error handling tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_usage():
    """Print usage information."""
    print("Hook Data Storage Test Runner")
    print("=" * 40)
    print()
    print("Usage:")
    print(f"  python {__file__} [options]")
    print()
    print("Options:")
    print("  --basic      Run basic database tests only")
    print("  --performance Run performance tests only")
    print("  --errors     Run error handling tests only")
    print("  --all        Run all tests (default)")
    print("  --help       Show this help message")
    print()
    print("Environment Variables Required:")
    print("  SUPABASE_URL  - Your Supabase project URL")
    print("  SUPABASE_SERVICE_ROLE_KEY  - Your Supabase service role key")
    print()


async def main():
    """Main test runner function."""
    # Parse command line arguments
    args = sys.argv[1:]
    
    if "--help" in args:
        print_usage()
        return
    
    # Check environment
    if not await check_environment():
        sys.exit(1)
    
    # Determine which tests to run
    run_basic = "--basic" in args or "--all" in args or not args
    run_performance = "--performance" in args or "--all" in args or not args
    run_errors = "--errors" in args or "--all" in args or not args
    
    print("Hook Data Storage Test Runner")
    print("=" * 40)
    
    all_passed = True
    
    if run_basic:
        print("\n🧪 Running basic database tests...")
        if not await run_database_tests():
            all_passed = False
    
    if run_performance:
        print("\n⚡ Running performance tests...")
        if not await run_performance_tests():
            all_passed = False
    
    if run_errors:
        print("\n🚨 Running error handling tests...")
        if not await run_error_handling_tests():
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("✅ All tests passed successfully!")
        print("\nHook data storage is working correctly.")
    else:
        print("❌ Some tests failed!")
        print("\nPlease check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())