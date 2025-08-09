#!/usr/bin/env python3
"""
Database health check script for DevSync AI.

This script verifies that the Supabase database connection is working correctly
and that all required tables exist.
"""

import asyncio
import sys
from typing import List, Dict, Any

from devsync_ai.database.connection import get_database, DatabaseConnectionError


async def check_connection() -> bool:
    """Test basic database connectivity."""
    try:
        db = await get_database()

        # Check if we have valid-looking credentials
        if (
            db.settings.supabase_url == "https://your-project.supabase.co"
            or db.settings.supabase_key == "your-supabase-anon-key"
        ):
            print("✗ Database connection failed: Using example credentials")
            print("  Please update SUPABASE_URL and SUPABASE_KEY in your .env file")
            print("  See docs/database-setup.md for instructions")
            return False

        healthy = await db.health_check()
        if healthy:
            print("✓ Database connection successful")
            return True
        else:
            print("✗ Database connection failed - health check returned False")
            return False
    except DatabaseConnectionError as e:
        error_msg = str(e)
        if "Invalid API key" in error_msg:
            print("✗ Database connection failed: Invalid Supabase API key")
            print("  Please check your SUPABASE_KEY in .env file")
        elif "Invalid URL" in error_msg:
            print("✗ Database connection failed: Invalid Supabase URL")
            print("  Please check your SUPABASE_URL in .env file")
        else:
            print(f"✗ Database connection failed: {e}")
        return False
    except Exception as e:
        error_msg = str(e)
        if "unexpected keyword argument" in error_msg:
            print("✗ Database connection failed: Invalid credentials format")
            print("  Please verify your SUPABASE_URL and SUPABASE_KEY are correct")
        else:
            print(f"✗ Unexpected error during connection test: {e}")
        return False


async def check_tables() -> bool:
    """Verify that all required tables exist."""
    required_tables = [
        "pull_requests",
        "jira_tickets",
        "team_members",
        "bottlenecks",
        "slack_messages",
    ]

    try:
        db = await get_database()

        # Query information_schema to get list of tables
        result = await db.execute_query(
            table="information_schema.tables",
            operation="select",
            select_fields="table_name",
            filters={"table_schema": "public"},
        )

        if not result["success"]:
            print(f"✗ Failed to query table information: {result.get('error', 'Unknown error')}")
            return False

        existing_tables = [row["table_name"] for row in result["data"]]
        missing_tables = [table for table in required_tables if table not in existing_tables]

        if missing_tables:
            print(f"✗ Missing required tables: {', '.join(missing_tables)}")
            print("  Run the database migrations to create missing tables.")
            return False
        else:
            print(f"✓ All required tables exist: {', '.join(required_tables)}")
            return True

    except Exception as e:
        print(f"✗ Error checking tables: {e}")
        return False


async def check_table_structure() -> bool:
    """Verify that tables have the expected structure."""
    try:
        db = await get_database()

        # Test inserting and querying a simple record in each table
        test_cases = [
            {
                "table": "team_members",
                "data": {
                    "username": "test_user",
                    "github_handle": "test_github",
                    "jira_account": "test@example.com",
                    "slack_user_id": "U123456789",
                    "role": "developer",
                },
            }
        ]

        for test_case in test_cases:
            # Try to insert test data
            insert_result = await db.execute_query(
                table=test_case["table"], operation="insert", data=test_case["data"]
            )

            if not insert_result["success"]:
                print(
                    f"✗ Failed to insert test data into {test_case['table']}: {insert_result.get('error')}"
                )
                return False

            # Clean up test data
            delete_result = await db.execute_query(
                table=test_case["table"],
                operation="delete",
                filters={"username": test_case["data"]["username"]},
            )

            if not delete_result["success"]:
                print(f"⚠ Warning: Failed to clean up test data from {test_case['table']}")

        print("✓ Table structure validation passed")
        return True

    except Exception as e:
        print(f"✗ Error validating table structure: {e}")
        return False


async def main():
    """Run all database checks."""
    print("DevSync AI Database Health Check")
    print("=" * 40)

    checks = [
        ("Database Connection", check_connection),
        ("Required Tables", check_tables),
        ("Table Structure", check_table_structure),
    ]

    all_passed = True

    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        try:
            passed = await check_func()
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"✗ {check_name} failed with exception: {e}")
            all_passed = False

    print("\n" + "=" * 40)
    if all_passed:
        print("✓ All database checks passed!")
        print("\nYour database is ready for DevSync AI.")
        sys.exit(0)
    else:
        print("✗ Some database checks failed.")
        print("\nPlease review the errors above and:")
        print("1. Verify your SUPABASE_URL and SUPABASE_KEY in .env")
        print("2. Run database migrations if tables are missing")
        print("3. Check the database setup guide in docs/database-setup.md")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
