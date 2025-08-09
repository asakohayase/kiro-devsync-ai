"""
Supabase database connection management.

This module provides utilities for connecting to and managing the Supabase database.
Based on the official Supabase Python client documentation.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from supabase import create_client, Client
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    supabase_url: str
    supabase_key: str

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from .env file


class DatabaseConnection:
    """Manages Supabase database connections and operations."""

    def __init__(self, settings: Optional[DatabaseSettings] = None):
        """Initialize database connection manager."""
        self.settings = settings or DatabaseSettings()
        self._client: Optional[Client] = None
        self._connection_lock = asyncio.Lock()

    async def connect(self) -> Client:
        """Establish connection to Supabase."""
        async with self._connection_lock:
            if self._client is None:
                try:
                    # Create Supabase client with minimal options to avoid compatibility issues
                    self._client = create_client(
                        supabase_url=self.settings.supabase_url,
                        supabase_key=self.settings.supabase_key,
                    )
                    logger.info("Successfully connected to Supabase database")
                except Exception as e:
                    logger.error(f"Failed to connect to Supabase: {e}")
                    raise DatabaseConnectionError(f"Database connection failed: {e}")

            return self._client

    async def disconnect(self):
        """Close database connection."""
        async with self._connection_lock:
            if self._client:
                # Supabase client doesn't need explicit disconnection
                self._client = None
                logger.info("Disconnected from Supabase database")

    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            client = await self.connect()
            # Simple query to test connection
            result = (
                client.table("information_schema.tables").select("table_name").limit(1).execute()
            )
            return result.data is not None
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @asynccontextmanager
    async def get_client(self):
        """Context manager for database operations."""
        client = await self.connect()
        try:
            yield client
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise

    async def execute_query(
        self,
        table: str,
        operation: str,
        data: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        select_fields: str = "*",
    ) -> Dict[str, Any]:
        """Execute a database query with error handling."""
        async with self.get_client() as client:
            try:
                query = client.table(table)

                if operation == "select":
                    query = query.select(select_fields)
                    if filters:
                        for key, value in filters.items():
                            query = query.eq(key, value)
                    result = query.execute()

                elif operation == "insert":
                    if not data:
                        raise ValueError("Data required for insert operation")
                    result = query.insert(data).execute()

                elif operation == "update":
                    if not data or not filters:
                        raise ValueError("Data and filters required for update operation")
                    query = query.update(data)
                    for key, value in filters.items():
                        query = query.eq(key, value)
                    result = query.execute()

                elif operation == "delete":
                    if not filters:
                        raise ValueError("Filters required for delete operation")
                    for key, value in filters.items():
                        query = query.eq(key, value)
                    result = query.delete().execute()

                else:
                    raise ValueError(f"Unsupported operation: {operation}")

                return {"success": True, "data": result.data, "count": result.count}

            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                return {"success": False, "error": str(e), "data": None, "count": 0}

    async def execute_raw_sql(self, sql: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute raw SQL query (for migrations and complex operations)."""
        async with self.get_client() as client:
            try:
                # Note: Supabase Python client doesn't directly support raw SQL
                # This would typically be done through the REST API or a direct PostgreSQL connection
                # For now, we'll raise an error indicating this needs to be implemented
                raise NotImplementedError(
                    "Raw SQL execution requires direct PostgreSQL connection. "
                    "Use migration scripts or Supabase dashboard for schema changes."
                )
            except Exception as e:
                logger.error(f"Raw SQL execution failed: {e}")
                return {"success": False, "error": str(e), "data": None}


class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors."""

    pass


# Global database connection instance
_db_connection: Optional[DatabaseConnection] = None


async def get_database() -> DatabaseConnection:
    """Get the global database connection instance."""
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
    return _db_connection


async def close_database():
    """Close the global database connection."""
    global _db_connection
    if _db_connection:
        await _db_connection.disconnect()
        _db_connection = None
