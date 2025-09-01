"""
Changelog Migration Runner

Extends the existing migration system to handle changelog-specific
database schema changes while maintaining compatibility.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from devsync_ai.database.migrations.runner import MigrationRunner
from devsync_ai.database.connection import get_database


logger = logging.getLogger(__name__)


class ChangelogMigrationRunner(MigrationRunner):
    """
    Migration runner specifically for changelog service integration.
    Extends the base migration runner with changelog-specific functionality.
    """
    
    def __init__(self):
        """Initialize the changelog migration runner."""
        super().__init__()
        self.changelog_migrations_path = os.path.join(
            os.path.dirname(__file__), 
            "migrations"
        )
        
    async def run_changelog_migrations(self) -> Dict[str, Any]:
        """Run all changelog-specific migrations."""
        logger.info("Starting changelog service migration process")
        
        try:
            # Ensure base migrations are run first
            base_result = await self.run_pending_migrations()
            
            # Run changelog-specific migrations
            changelog_result = await self._run_changelog_specific_migrations()
            
            # Verify changelog schema
            verification_result = await self._verify_changelog_schema()
            
            result = {
                "success": True,
                "base_migrations": base_result,
                "changelog_migrations": changelog_result,
                "schema_verification": verification_result,
                "completed_at": datetime.now().isoformat()
            }
            
            logger.info("Changelog service migrations completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Changelog migration failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }
    
    async def _run_changelog_specific_migrations(self) -> Dict[str, Any]:
        """Run changelog-specific migration files."""
        changelog_migrations = [
            "003_changelog_history_schema.sql",
            "004_changelog_service_integration.sql"
        ]
        
        results = []
        
        for migration_file in changelog_migrations:
            try:
                migration_path = os.path.join(self.changelog_migrations_path, migration_file)
                
                if not os.path.exists(migration_path):
                    logger.warning(f"Migration file not found: {migration_path}")
                    continue
                
                # Check if migration already applied
                if await self._is_migration_applied(migration_file):
                    logger.info(f"Migration {migration_file} already applied, skipping")
                    results.append({
                        "migration": migration_file,
                        "status": "skipped",
                        "reason": "already_applied"
                    })
                    continue
                
                # Run the migration
                result = await self._execute_migration_file(migration_path, migration_file)
                results.append(result)
                
                # Record migration as applied
                await self._record_migration_applied(migration_file)
                
            except Exception as e:
                logger.error(f"Failed to run migration {migration_file}: {e}")
                results.append({
                    "migration": migration_file,
                    "status": "failed",
                    "error": str(e)
                })
                # Don't continue with remaining migrations if one fails
                break
        
        return {
            "migrations_run": len([r for r in results if r["status"] == "success"]),
            "migrations_skipped": len([r for r in results if r["status"] == "skipped"]),
            "migrations_failed": len([r for r in results if r["status"] == "failed"]),
            "details": results
        }
    
    async def _execute_migration_file(self, migration_path: str, migration_name: str) -> Dict[str, Any]:
        """Execute a single migration file."""
        logger.info(f"Executing migration: {migration_name}")
        
        try:
            # Read migration file
            with open(migration_path, 'r') as f:
                migration_sql = f.read()
            
            # Execute migration
            db = await get_database()
            
            # Split migration into individual statements
            statements = self._split_sql_statements(migration_sql)
            
            executed_statements = 0
            for statement in statements:
                if statement.strip():
                    await db.execute_raw(statement)
                    executed_statements += 1
            
            logger.info(f"Migration {migration_name} completed successfully ({executed_statements} statements)")
            
            return {
                "migration": migration_name,
                "status": "success",
                "statements_executed": executed_statements,
                "executed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Migration {migration_name} failed: {e}")
            return {
                "migration": migration_name,
                "status": "failed",
                "error": str(e),
                "executed_at": datetime.now().isoformat()
            }
    
    async def _is_migration_applied(self, migration_name: str) -> bool:
        """Check if a migration has already been applied."""
        try:
            db = await get_database()
            
            # Check if migration tracking table exists
            result = await db.execute_raw("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'schema_migrations'
                )
            """)
            
            if not result[0][0]:
                # Create migration tracking table if it doesn't exist
                await self._create_migration_tracking_table()
                return False
            
            # Check if this specific migration is recorded
            result = await db.execute_raw(
                "SELECT EXISTS (SELECT 1 FROM schema_migrations WHERE version = %s)",
                (migration_name,)
            )
            
            return result[0][0] if result else False
            
        except Exception as e:
            logger.error(f"Failed to check migration status: {e}")
            return False
    
    async def _record_migration_applied(self, migration_name: str):
        """Record that a migration has been applied."""
        try:
            db = await get_database()
            
            await db.execute_raw(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (%s, %s)",
                (migration_name, datetime.now())
            )
            
            logger.info(f"Recorded migration {migration_name} as applied")
            
        except Exception as e:
            logger.error(f"Failed to record migration: {e}")
            raise
    
    async def _create_migration_tracking_table(self):
        """Create the migration tracking table if it doesn't exist."""
        try:
            db = await get_database()
            
            await db.execute_raw("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            logger.info("Created schema_migrations tracking table")
            
        except Exception as e:
            logger.error(f"Failed to create migration tracking table: {e}")
            raise
    
    async def _verify_changelog_schema(self) -> Dict[str, Any]:
        """Verify that all changelog tables and functions exist."""
        logger.info("Verifying changelog schema")
        
        try:
            db = await get_database()
            
            # Tables to verify
            required_tables = [
                "changelog_entries",
                "changelog_audit_trail",
                "changelog_distributions",
                "changelog_analytics",
                "changelog_export_jobs",
                "changelog_retention_policies",
                "changelog_backups",
                "changelog_generation_jobs",
                "changelog_service_health",
                "changelog_api_usage",
                "changelog_config_audit"
            ]
            
            # Functions to verify
            required_functions = [
                "create_changelog_generation_job",
                "update_changelog_job_status",
                "record_service_health_check",
                "record_api_usage",
                "audit_config_change"
            ]
            
            # Views to verify
            required_views = [
                "changelog_entries_with_stats",
                "team_changelog_analytics",
                "active_changelog_jobs",
                "changelog_service_health_summary",
                "changelog_api_usage_summary"
            ]
            
            verification_results = {
                "tables": {},
                "functions": {},
                "views": {},
                "overall_status": "success"
            }
            
            # Verify tables
            for table in required_tables:
                exists = await self._table_exists(db, table)
                verification_results["tables"][table] = {
                    "exists": exists,
                    "status": "ok" if exists else "missing"
                }
                if not exists:
                    verification_results["overall_status"] = "incomplete"
            
            # Verify functions
            for function in required_functions:
                exists = await self._function_exists(db, function)
                verification_results["functions"][function] = {
                    "exists": exists,
                    "status": "ok" if exists else "missing"
                }
                if not exists:
                    verification_results["overall_status"] = "incomplete"
            
            # Verify views
            for view in required_views:
                exists = await self._view_exists(db, view)
                verification_results["views"][view] = {
                    "exists": exists,
                    "status": "ok" if exists else "missing"
                }
                if not exists:
                    verification_results["overall_status"] = "incomplete"
            
            logger.info(f"Schema verification completed: {verification_results['overall_status']}")
            return verification_results
            
        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            return {
                "overall_status": "error",
                "error": str(e)
            }
    
    async def _table_exists(self, db, table_name: str) -> bool:
        """Check if a table exists."""
        try:
            result = await db.execute_raw("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table_name,))
            
            return result[0][0] if result else False
            
        except Exception:
            return False
    
    async def _function_exists(self, db, function_name: str) -> bool:
        """Check if a function exists."""
        try:
            result = await db.execute_raw("""
                SELECT EXISTS (
                    SELECT FROM information_schema.routines 
                    WHERE routine_name = %s AND routine_type = 'FUNCTION'
                )
            """, (function_name,))
            
            return result[0][0] if result else False
            
        except Exception:
            return False
    
    async def _view_exists(self, db, view_name: str) -> bool:
        """Check if a view exists."""
        try:
            result = await db.execute_raw("""
                SELECT EXISTS (
                    SELECT FROM information_schema.views 
                    WHERE table_name = %s
                )
            """, (view_name,))
            
            return result[0][0] if result else False
            
        except Exception:
            return False
    
    def _split_sql_statements(self, sql: str) -> List[str]:
        """Split SQL file into individual statements."""
        # Simple statement splitting - could be enhanced for more complex cases
        statements = []
        current_statement = ""
        
        for line in sql.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('--'):
                continue
            
            current_statement += line + '\n'
            
            # Check if statement ends with semicolon
            if line.endswith(';'):
                statements.append(current_statement.strip())
                current_statement = ""
        
        # Add any remaining statement
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements
    
    async def rollback_changelog_migrations(self) -> Dict[str, Any]:
        """Rollback changelog migrations (for development/testing)."""
        logger.warning("Rolling back changelog migrations")
        
        try:
            db = await get_database()
            
            # Drop changelog-specific tables in reverse order
            tables_to_drop = [
                "changelog_config_audit",
                "changelog_api_usage", 
                "changelog_service_health",
                "changelog_generation_jobs",
                "changelog_backups",
                "changelog_retention_policies",
                "changelog_export_jobs",
                "changelog_analytics",
                "changelog_distributions",
                "changelog_audit_trail",
                "changelog_entries"
            ]
            
            dropped_tables = []
            for table in tables_to_drop:
                try:
                    await db.execute_raw(f"DROP TABLE IF EXISTS {table} CASCADE")
                    dropped_tables.append(table)
                    logger.info(f"Dropped table: {table}")
                except Exception as e:
                    logger.error(f"Failed to drop table {table}: {e}")
            
            # Drop changelog-specific functions
            functions_to_drop = [
                "create_changelog_generation_job",
                "update_changelog_job_status", 
                "record_service_health_check",
                "record_api_usage",
                "audit_config_change"
            ]
            
            dropped_functions = []
            for function in functions_to_drop:
                try:
                    await db.execute_raw(f"DROP FUNCTION IF EXISTS {function} CASCADE")
                    dropped_functions.append(function)
                    logger.info(f"Dropped function: {function}")
                except Exception as e:
                    logger.error(f"Failed to drop function {function}: {e}")
            
            # Remove migration records
            migration_files = [
                "003_changelog_history_schema.sql",
                "004_changelog_service_integration.sql"
            ]
            
            for migration in migration_files:
                try:
                    await db.execute_raw(
                        "DELETE FROM schema_migrations WHERE version = %s",
                        (migration,)
                    )
                except Exception as e:
                    logger.error(f"Failed to remove migration record {migration}: {e}")
            
            return {
                "success": True,
                "dropped_tables": dropped_tables,
                "dropped_functions": dropped_functions,
                "completed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get the current status of changelog migrations."""
        try:
            db = await get_database()
            
            # Get applied migrations
            try:
                result = await db.execute_raw(
                    "SELECT version, applied_at FROM schema_migrations WHERE version LIKE '%changelog%' ORDER BY applied_at"
                )
                applied_migrations = [
                    {"version": row[0], "applied_at": row[1].isoformat()}
                    for row in result
                ]
            except Exception:
                applied_migrations = []
            
            # Check schema status
            schema_verification = await self._verify_changelog_schema()
            
            return {
                "applied_migrations": applied_migrations,
                "schema_status": schema_verification,
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }