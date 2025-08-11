"""
Full-featured Supabase database connection using HTTP API.

This module provides a complete Supabase client implementation using direct HTTP requests
to the PostgREST API, avoiding dependency issues with the official Supabase Python client.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union
import httpx

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Full-featured Supabase client using direct HTTP requests with PostgREST API."""

    def __init__(self):
        self.base_url = os.getenv("SUPABASE_URL")
        self.api_key = os.getenv("SUPABASE_KEY")

        if not self.base_url or not self.api_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")

        self.headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def insert(
        self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Insert data into a table."""
        url = f"{self.base_url}/rest/v1/{table}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=self.headers, json=data, timeout=30.0)

                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    logger.error(f"Insert failed: {response.status_code} - {response.text}")
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

            except Exception as e:
                logger.error(f"Insert error: {e}")
                raise

    async def select(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        select_fields: str = "*",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        range_start: Optional[int] = None,
        range_end: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Select data from a table with full PostgREST query capabilities.

        Args:
            table: Table name
            filters: Dictionary of column filters (supports eq, neq, gt, gte, lt, lte, like, ilike, in, is)
            select_fields: Comma-separated list of fields to select
            limit: Maximum number of rows to return
            offset: Number of rows to skip
            order_by: Column to order by
            order_desc: Whether to order in descending order
            range_start: Start of range for pagination (alternative to offset)
            range_end: End of range for pagination

        Returns:
            List of dictionaries representing rows
        """
        url = f"{self.base_url}/rest/v1/{table}"
        headers = self.headers.copy()
        params = {"select": select_fields}

        # Add filters with proper PostgREST operators
        if filters:
            for key, value in filters.items():
                if isinstance(value, dict):
                    # Handle complex filters like {"gt": 10} or {"in": ["a", "b"]}
                    for op, val in value.items():
                        if op == "in" and isinstance(val, list):
                            params[key] = f"in.({','.join(map(str, val))})"
                        else:
                            params[key] = f"{op}.{val}"
                else:
                    # Simple equality filter
                    params[key] = f"eq.{value}"

        # Add limit
        if limit:
            params["limit"] = str(limit)

        # Add offset
        if offset:
            params["offset"] = str(offset)

        # Add ordering
        if order_by:
            order_param = f"{order_by}.{'desc' if order_desc else 'asc'}"
            params["order"] = order_param

        # Add range headers for pagination
        if range_start is not None and range_end is not None:
            headers["Range"] = f"{range_start}-{range_end}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params, timeout=30.0)

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Select failed: {response.status_code} - {response.text}")
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

            except Exception as e:
                logger.error(f"Select error: {e}")
                raise

    async def update(
        self, table: str, data: Dict[str, Any], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Update data in a table."""
        url = f"{self.base_url}/rest/v1/{table}"

        params = {}
        for key, value in filters.items():
            if isinstance(value, dict):
                for op, val in value.items():
                    params[key] = f"{op}.{val}"
            else:
                params[key] = f"eq.{value}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.patch(
                    url, headers=self.headers, params=params, json=data, timeout=30.0
                )

                if response.status_code in [200, 204]:
                    return response.json() if response.content else []
                else:
                    logger.error(f"Update failed: {response.status_code} - {response.text}")
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

            except Exception as e:
                logger.error(f"Update error: {e}")
                raise

    async def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete data from a table."""
        url = f"{self.base_url}/rest/v1/{table}"

        params = {}
        for key, value in filters.items():
            if isinstance(value, dict):
                for op, val in value.items():
                    params[key] = f"{op}.{val}"
            else:
                params[key] = f"eq.{value}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    url, headers=self.headers, params=params, timeout=30.0
                )

                if response.status_code in [200, 204]:
                    return response.json() if response.content else []
                else:
                    logger.error(f"Delete failed: {response.status_code} - {response.text}")
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

            except Exception as e:
                logger.error(f"Delete error: {e}")
                raise

    async def upsert(
        self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]], on_conflict: str = None
    ) -> List[Dict[str, Any]]:
        """Insert or update data (upsert)."""
        url = f"{self.base_url}/rest/v1/{table}"
        headers = self.headers.copy()

        if on_conflict:
            headers["Prefer"] = f"resolution=merge-duplicates,return=representation"
        else:
            headers["Prefer"] = "return=representation"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=data, timeout=30.0)

                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    logger.error(f"Upsert failed: {response.status_code} - {response.text}")
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

            except Exception as e:
                logger.error(f"Upsert error: {e}")
                raise

    async def count(self, table: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count rows in a table."""
        url = f"{self.base_url}/rest/v1/{table}"
        headers = self.headers.copy()
        headers["Prefer"] = "count=exact"

        params = {"select": "count"}

        if filters:
            for key, value in filters.items():
                if isinstance(value, dict):
                    for op, val in value.items():
                        params[key] = f"{op}.{val}"
                else:
                    params[key] = f"eq.{value}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.head(url, headers=headers, params=params, timeout=30.0)

                if response.status_code == 200:
                    content_range = response.headers.get("content-range", "")
                    if content_range:
                        # Parse "0-24/25" format
                        total = content_range.split("/")[-1]
                        return int(total) if total != "*" else 0
                    return 0
                else:
                    logger.error(f"Count failed: {response.status_code}")
                    raise Exception(f"HTTP {response.status_code}")

            except Exception as e:
                logger.error(f"Count error: {e}")
                raise

    async def execute_rpc(self, function_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a stored procedure/function."""
        url = f"{self.base_url}/rest/v1/rpc/{function_name}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, headers=self.headers, json=params or {}, timeout=30.0
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"RPC failed: {response.status_code} - {response.text}")
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

            except Exception as e:
                logger.error(f"RPC error: {e}")
                raise

    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            # Simple query to test connection
            result = await self.select(
                "information_schema.tables", filters={"table_schema": "public"}, limit=1
            )
            return len(result) >= 0  # Even empty result means connection works
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database connection instance
_db_client: Optional[SupabaseClient] = None


async def get_database() -> SupabaseClient:
    """Get the global database client instance."""
    global _db_client
    if _db_client is None:
        _db_client = SupabaseClient()
    return _db_client


async def close_database():
    """Close the global database connection."""
    global _db_client
    if _db_client:
        _db_client = None
