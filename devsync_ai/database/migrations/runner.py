"""
Database migration runner.

This module provides utilities for running database migrations against Supabase.
Since Supabase doesn't support direct SQL execution through the Python client,
this module provides instructions and utilities for manual migration execution.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Handles database migration execution and tracking."""

    def __init__(self, migrations_dir: str = None):
        """Initialize migration runner."""
        if migrations_dir is None:
            migrations_dir = Path(__file__).parent
        self.migrations_dir = Path(migrations_dir)

    def get_migration_files(self) -> List[Path]:
        """Get all migration files in order."""
        migration_files = []
        for file_path in self.migrations_dir.glob("*.sql"):
            if file_path.name.startswith(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
                migration_files.append(file_path)

        # Sort by filename to ensure proper order
        migration_files.sort(key=lambda x: x.name)
        return migration_files

    def read_migration_content(self, migration_file: Path) -> str:
        """Read the content of a migration file."""
        try:
            with open(migration_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read migration file {migration_file}: {e}")
            raise

    def validate_migration_syntax(self, content: str) -> bool:
        """Basic validation of SQL migration syntax."""
        # Check for common SQL injection patterns and syntax issues
        dangerous_patterns = [
            "DROP DATABASE",
            "DROP SCHEMA",
            "TRUNCATE",
            "--",  # SQL comments that might hide malicious code
        ]

        content_upper = content.upper()
        for pattern in dangerous_patterns:
            if pattern in content_upper and not content_upper.startswith("--"):
                logger.warning(f"Potentially dangerous pattern found: {pattern}")
                return False

        return True

    def generate_migration_instructions(self) -> Dict[str, Any]:
        """Generate instructions for manual migration execution."""
        migration_files = self.get_migration_files()
        instructions = {
            "total_migrations": len(migration_files),
            "migrations": [],
            "execution_instructions": self._get_execution_instructions(),
        }

        for migration_file in migration_files:
            try:
                content = self.read_migration_content(migration_file)
                is_valid = self.validate_migration_syntax(content)

                instructions["migrations"].append(
                    {
                        "filename": migration_file.name,
                        "path": str(migration_file),
                        "valid": is_valid,
                        "content_preview": content[:200] + "..." if len(content) > 200 else content,
                        "size_bytes": len(content.encode("utf-8")),
                    }
                )
            except Exception as e:
                instructions["migrations"].append(
                    {
                        "filename": migration_file.name,
                        "path": str(migration_file),
                        "valid": False,
                        "error": str(e),
                    }
                )

        return instructions

    def _get_execution_instructions(self) -> List[str]:
        """Get step-by-step instructions for running migrations."""
        return [
            "1. Log into your Supabase dashboard at https://app.supabase.com",
            "2. Navigate to your project and go to the SQL Editor",
            "3. Execute each migration file in numerical order:",
            "   - Copy the content of each .sql file",
            "   - Paste it into the SQL Editor",
            "   - Click 'Run' to execute the migration",
            "4. Verify that all tables and indexes were created successfully",
            "5. Check the 'Table Editor' to confirm the schema matches expectations",
            "6. Test the database connection using the health check endpoint",
        ]

    def create_migration_script(self, output_file: str = "run_migrations.sql") -> str:
        """Create a single SQL file with all migrations for easy execution."""
        migration_files = self.get_migration_files()
        output_path = self.migrations_dir / output_file

        try:
            with open(output_path, "w", encoding="utf-8") as output:
                output.write("-- DevSync AI Database Migrations\n")
                output.write("-- Generated automatically - execute in Supabase SQL Editor\n")
                output.write("-- \n\n")

                for migration_file in migration_files:
                    content = self.read_migration_content(migration_file)
                    output.write(f"-- Migration: {migration_file.name}\n")
                    output.write(f"-- File: {migration_file}\n")
                    output.write("-- " + "=" * 50 + "\n\n")
                    output.write(content)
                    output.write("\n\n")

                output.write("-- End of migrations\n")

            logger.info(f"Combined migration script created: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to create migration script: {e}")
            raise

    def print_migration_summary(self):
        """Print a summary of available migrations."""
        instructions = self.generate_migration_instructions()

        print("\n" + "=" * 60)
        print("DATABASE MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Total migrations found: {instructions['total_migrations']}")
        print()

        for migration in instructions["migrations"]:
            status = "✓ Valid" if migration.get("valid", False) else "✗ Invalid"
            print(f"  {migration['filename']}: {status}")
            if "error" in migration:
                print(f"    Error: {migration['error']}")

        print("\nEXECUTION INSTRUCTIONS:")
        print("-" * 30)
        for instruction in instructions["execution_instructions"]:
            print(instruction)

        print(f"\nTo create a combined migration file, run:")
        print(f"  python -m devsync_ai.database.migrations.runner")
        print("=" * 60 + "\n")


def main():
    """Main function for running migration utilities."""
    runner = MigrationRunner()

    # Print summary
    runner.print_migration_summary()

    # Create combined migration script
    try:
        script_path = runner.create_migration_script()
        print(f"✓ Combined migration script created: {script_path}")
        print("  Execute this file in your Supabase SQL Editor")
    except Exception as e:
        print(f"✗ Failed to create migration script: {e}")


if __name__ == "__main__":
    main()
