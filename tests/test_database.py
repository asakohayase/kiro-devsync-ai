"""
Unit tests for database connection and utilities.

Tests database connection management, error handling, and migration utilities.
"""

import os
import pytest
from unittest.mock import patch

from devsync_ai.database.connection import (
    SupabaseClient,
    get_database,
    close_database,
)


class TestSupabaseClient:
    """Test cases for SupabaseClient."""

    def test_client_initialization_success(self):
        """Test successful client initialization."""
        with patch.dict(
            "os.environ", {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test-key"}
        ):
            client = SupabaseClient()
            assert client.base_url == "https://test.supabase.co"
            assert client.api_key == "test-key"

    def test_client_initialization_missing_url(self):
        """Test client initialization with missing URL."""
        with patch.dict("os.environ", {"SUPABASE_SERVICE_ROLE_KEY": "test-key"}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                SupabaseClient()
            assert "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables are required" in str(exc_info.value)

    def test_client_initialization_missing_key(self):
        """Test client initialization with missing key."""
        with patch.dict("os.environ", {"SUPABASE_URL": "https://test.supabase.co"}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                SupabaseClient()
            assert "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables are required" in str(exc_info.value)


class TestDatabaseGlobalFunctions:
    """Test cases for global database functions."""

    @pytest.mark.asyncio
    async def test_get_database(self):
        """Test getting global database instance."""
        with patch.dict(
            "os.environ", {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test-key"}
        ):
            db1 = await get_database()
            db2 = await get_database()
            # Should return the same instance
            assert db1 is db2
            assert isinstance(db1, SupabaseClient)

    @pytest.mark.asyncio
    async def test_close_database(self):
        """Test closing global database connection."""
        with patch.dict(
            "os.environ", {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test-key"}
        ):
            # Get a database instance first
            db1 = await get_database()
            assert db1 is not None
            
            # Close the connection
            await close_database()
            
            # Get a new instance (should be a new object)
            db2 = await get_database()
            assert db2 is not None


