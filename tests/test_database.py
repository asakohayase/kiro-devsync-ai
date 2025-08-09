"""
Unit tests for database connection and utilities.

Tests database connection management, error handling, and migration utilities.
"""

import os
import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from devsync_ai.database.connection import (
    DatabaseConnection,
    DatabaseSettings,
    DatabaseConnectionError,
    get_database,
    close_database,
)
from devsync_ai.database.migrations.runner import MigrationRunner


class TestDatabaseSettings:
    """Test cases for DatabaseSettings."""

    def test_default_settings(self):
        """Test default database settings."""
        with patch.dict(
            "os.environ", {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_KEY": "test-key"}
        ):
            settings = DatabaseSettings()
            assert settings.supabase_url == "https://test.supabase.co"
            assert settings.supabase_key == "test-key"
            assert settings.max_connections == 10
            assert settings.connection_timeout == 30

    def test_custom_settings(self):
        """Test custom database settings."""
        settings = DatabaseSettings(
            supabase_url="https://custom.supabase.co",
            supabase_key="custom-key",
            max_connections=20,
            connection_timeout=60,
        )
        assert settings.supabase_url == "https://custom.supabase.co"
        assert settings.supabase_key == "custom-key"
        assert settings.max_connections == 20
        assert settings.connection_timeout == 60


class TestDatabaseConnection:
    """Test cases for DatabaseConnection."""

    @pytest.fixture
    def mock_settings(self):
        """Mock database settings."""
        return DatabaseSettings(supabase_url="https://test.supabase.co", supabase_key="test-key")

    @pytest.fixture
    def db_connection(self, mock_settings):
        """Create database connection instance."""
        return DatabaseConnection(mock_settings)

    @patch("devsync_ai.database.connection.create_client")
    @pytest.mark.asyncio
    async def test_connect_success(self, mock_create_client, db_connection):
        """Test successful database connection."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        client = await db_connection.connect()

        assert client == mock_client
        mock_create_client.assert_called_once_with("https://test.supabase.co", "test-key")

    @patch("devsync_ai.database.connection.create_client")
    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_create_client, db_connection):
        """Test database connection failure."""
        mock_create_client.side_effect = Exception("Connection failed")

        with pytest.raises(DatabaseConnectionError) as exc_info:
            await db_connection.connect()

        assert "Database connection failed" in str(exc_info.value)

    @patch("devsync_ai.database.connection.create_client")
    @pytest.mark.asyncio
    async def test_connect_reuse_existing(self, mock_create_client, db_connection):
        """Test that existing connection is reused."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # First connection
        client1 = await db_connection.connect()
        # Second connection should reuse the same client
        client2 = await db_connection.connect()

        assert client1 == client2
        mock_create_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, db_connection):
        """Test database disconnection."""
        # Set up a mock client
        db_connection._client = Mock()

        await db_connection.disconnect()

        assert db_connection._client is None

    @patch("devsync_ai.database.connection.create_client")
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_create_client, db_connection):
        """Test successful health check."""
        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_limit = Mock()

        mock_create_client.return_value = mock_client
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.limit.return_value = mock_limit
        mock_limit.execute.return_value = Mock(data=[{"table_name": "test"}])

        result = await db_connection.health_check()

        assert result is True
        mock_client.table.assert_called_once_with("information_schema.tables")

    @patch("devsync_ai.database.connection.create_client")
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_create_client, db_connection):
        """Test health check failure."""
        mock_create_client.side_effect = Exception("Connection failed")

        result = await db_connection.health_check()

        assert result is False

    @patch("devsync_ai.database.connection.create_client")
    @pytest.mark.asyncio
    async def test_execute_query_select(self, mock_create_client, db_connection):
        """Test execute_query with select operation."""
        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_eq = Mock()

        mock_create_client.return_value = mock_client
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = Mock(data=[{"id": "1"}], count=1)

        result = await db_connection.execute_query(
            table="test_table",
            operation="select",
            filters={"status": "active"},
            select_fields="id,name",
        )

        assert result["success"] is True
        assert result["data"] == [{"id": "1"}]
        assert result["count"] == 1
        mock_table.select.assert_called_once_with("id,name")
        mock_select.eq.assert_called_once_with("status", "active")

    @patch("devsync_ai.database.connection.create_client")
    @pytest.mark.asyncio
    async def test_execute_query_insert(self, mock_create_client, db_connection):
        """Test execute_query with insert operation."""
        mock_client = Mock()
        mock_table = Mock()
        mock_insert = Mock()

        mock_create_client.return_value = mock_client
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = Mock(data=[{"id": "1"}], count=1)

        result = await db_connection.execute_query(
            table="test_table", operation="insert", data={"name": "test", "status": "active"}
        )

        assert result["success"] is True
        assert result["data"] == [{"id": "1"}]
        mock_table.insert.assert_called_once_with({"name": "test", "status": "active"})

    @patch("devsync_ai.database.connection.create_client")
    @pytest.mark.asyncio
    async def test_execute_query_invalid_operation(self, mock_create_client, db_connection):
        """Test execute_query with invalid operation."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        result = await db_connection.execute_query(table="test_table", operation="invalid_op")

        assert result["success"] is False
        assert "Unsupported operation" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_raw_sql_not_implemented(self, db_connection):
        """Test that raw SQL execution raises NotImplementedError."""
        with patch("devsync_ai.database.connection.create_client"):
            result = await db_connection.execute_raw_sql("SELECT 1")

            assert result["success"] is False
            assert "Raw SQL execution requires direct PostgreSQL connection" in result["error"]


class TestGlobalDatabaseFunctions:
    """Test cases for global database functions."""

    @pytest.mark.asyncio
    async def test_get_database(self):
        """Test getting global database instance."""
        with patch.dict(
            "os.environ", {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_KEY": "test-key"}
        ):
            db1 = await get_database()
            db2 = await get_database()

            assert db1 is db2  # Should return the same instance
            assert isinstance(db1, DatabaseConnection)

    @pytest.mark.asyncio
    async def test_close_database(self):
        """Test closing global database connection."""
        with patch.dict(
            "os.environ", {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_KEY": "test-key"}
        ):
            # Get a database instance first
            db = await get_database()
            assert db is not None

            # Close it
            await close_database()

            # Getting database again should create a new instance
            new_db = await get_database()
        assert new_db is not db


class TestMigrationRunner:
    """Test cases for MigrationRunner."""

    @pytest.fixture
    def temp_migrations_dir(self, tmp_path):
        """Create temporary migrations directory with test files."""
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()

        # Create test migration files
        (migrations_dir / "001_initial.sql").write_text("CREATE TABLE test1;")
        (migrations_dir / "002_add_indexes.sql").write_text("CREATE INDEX idx_test ON test1(id);")
        (migrations_dir / "003_add_constraints.sql").write_text(
            "ALTER TABLE test1 ADD CONSTRAINT pk_test PRIMARY KEY (id);"
        )

        return migrations_dir

    def test_get_migration_files(self, temp_migrations_dir):
        """Test getting migration files in order."""
        runner = MigrationRunner(str(temp_migrations_dir))
        files = runner.get_migration_files()

        assert len(files) == 3
        assert files[0].name == "001_initial.sql"
        assert files[1].name == "002_add_indexes.sql"
        assert files[2].name == "003_add_constraints.sql"

    def test_read_migration_content(self, temp_migrations_dir):
        """Test reading migration file content."""
        runner = MigrationRunner(str(temp_migrations_dir))
        files = runner.get_migration_files()

        content = runner.read_migration_content(files[0])
        assert content == "CREATE TABLE test1;"

    def test_validate_migration_syntax_valid(self, temp_migrations_dir):
        """Test validation of valid SQL syntax."""
        runner = MigrationRunner(str(temp_migrations_dir))

        valid_sql = "CREATE TABLE test (id INTEGER PRIMARY KEY);"
        assert runner.validate_migration_syntax(valid_sql) is True

    def test_validate_migration_syntax_dangerous(self, temp_migrations_dir):
        """Test validation catches dangerous SQL patterns."""
        runner = MigrationRunner(str(temp_migrations_dir))

        dangerous_sql = "DROP DATABASE production;"
        assert runner.validate_migration_syntax(dangerous_sql) is False

    def test_generate_migration_instructions(self, temp_migrations_dir):
        """Test generating migration instructions."""
        runner = MigrationRunner(str(temp_migrations_dir))
        instructions = runner.generate_migration_instructions()

        assert instructions["total_migrations"] == 3
        assert len(instructions["migrations"]) == 3
        assert len(instructions["execution_instructions"]) > 0

        # Check first migration details
        first_migration = instructions["migrations"][0]
        assert first_migration["filename"] == "001_initial.sql"
        assert first_migration["valid"] is True
        assert "CREATE TABLE test1;" in first_migration["content_preview"]

    def test_create_migration_script(self, temp_migrations_dir):
        """Test creating combined migration script."""
        runner = MigrationRunner(str(temp_migrations_dir))
        output_file = "combined_migrations.sql"

        script_path = runner.create_migration_script(output_file)

        assert Path(script_path).exists()

        # Read the combined script
        with open(script_path, "r") as f:
            content = f.read()

        assert "CREATE TABLE test1;" in content
        assert "CREATE INDEX idx_test" in content
        assert "ALTER TABLE test1" in content
        assert "Migration: 001_initial.sql" in content
