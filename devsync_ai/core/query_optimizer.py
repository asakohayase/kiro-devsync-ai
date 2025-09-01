"""
Database query optimization and caching strategies for changelog generation.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import redis
from contextlib import asynccontextmanager

from ..database.connection import get_database_connection


class CacheStrategy(Enum):
    """Cache strategy types."""
    NO_CACHE = "no_cache"
    SHORT_TERM = "short_term"  # 5 minutes
    MEDIUM_TERM = "medium_term"  # 1 hour
    LONG_TERM = "long_term"  # 24 hours
    PERSISTENT = "persistent"  # Until manually invalidated


@dataclass
class QueryPlan:
    """Database query execution plan."""
    query: str
    params: List[Any]
    cache_strategy: CacheStrategy
    cache_key: Optional[str] = None
    estimated_cost: Optional[float] = None
    indexes_used: List[str] = None


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    created_at: datetime
    expires_at: Optional[datetime]
    hit_count: int = 0
    size_bytes: int = 0


class QueryOptimizer:
    """
    Database query optimizer with intelligent caching and performance monitoring.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.redis_client = None
        self.local_cache: Dict[str, CacheEntry] = {}
        self.query_stats: Dict[str, Dict[str, Any]] = {}
        
        # Cache TTL settings (in seconds)
        self.cache_ttl = {
            CacheStrategy.SHORT_TERM: 300,      # 5 minutes
            CacheStrategy.MEDIUM_TERM: 3600,    # 1 hour
            CacheStrategy.LONG_TERM: 86400,     # 24 hours
            CacheStrategy.PERSISTENT: None      # No expiration
        }
        
        # Initialize Redis if URL provided
        if redis_url:
            try:
                import redis.asyncio as aioredis
                self.redis_client = aioredis.from_url(redis_url)
            except ImportError:
                self.logger.warning("Redis not available, using local cache only")
    
    async def execute_optimized_query(
        self,
        query: str,
        params: List[Any] = None,
        cache_strategy: CacheStrategy = CacheStrategy.MEDIUM_TERM,
        cache_key_suffix: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Execute a database query with optimization and caching.
        """
        params = params or []
        
        # Generate cache key
        cache_key = self._generate_cache_key(query, params, cache_key_suffix)
        
        # Try to get from cache first
        if cache_strategy != CacheStrategy.NO_CACHE:
            cached_result = await self._get_from_cache(cache_key)
            if cached_result is not None:
                await self._update_query_stats(query, "cache_hit", 0)
                return cached_result
        
        # Execute query with performance monitoring
        start_time = datetime.utcnow()
        
        try:
            async with get_database_connection() as conn:
                # Get query plan for optimization insights
                plan = await self._analyze_query_plan(conn, query, params)
                
                # Execute the actual query
                rows = await conn.fetch(query, *params)
                result = [dict(row) for row in rows]
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Cache the result if strategy allows
                if cache_strategy != CacheStrategy.NO_CACHE:
                    await self._store_in_cache(cache_key, result, cache_strategy)
                
                # Update statistics
                await self._update_query_stats(query, "cache_miss", execution_time, plan)
                
                return result
                
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            await self._update_query_stats(query, "error", execution_time)
            self.logger.error(f"Query execution failed: {e}")
            raise
    
    def _generate_cache_key(self, query: str, params: List[Any], suffix: str = "") -> str:
        """Generate a unique cache key for the query and parameters."""
        # Create a hash of the query and parameters
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        params_hash = hashlib.md5(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:8]
        
        cache_key = f"query:{query_hash}:{params_hash}"
        if suffix:
            cache_key += f":{suffix}"
        
        return cache_key
    
    async def _get_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve data from cache (Redis or local)."""
        try:
            # Try Redis first if available
            if self.redis_client:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            
            # Fall back to local cache
            if cache_key in self.local_cache:
                entry = self.local_cache[cache_key]
                
                # Check if entry has expired
                if entry.expires_at and datetime.utcnow() > entry.expires_at:
                    del self.local_cache[cache_key]
                    return None
                
                # Update hit count
                entry.hit_count += 1
                return entry.data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving from cache: {e}")
            return None
    
    async def _store_in_cache(
        self,
        cache_key: str,
        data: List[Dict[str, Any]],
        strategy: CacheStrategy
    ):
        """Store data in cache with appropriate TTL."""
        try:
            ttl = self.cache_ttl.get(strategy)
            expires_at = datetime.utcnow() + timedelta(seconds=ttl) if ttl else None
            
            # Store in Redis if available
            if self.redis_client and ttl:
                await self.redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(data, default=str)
                )
            
            # Store in local cache
            data_size = len(json.dumps(data, default=str).encode())
            entry = CacheEntry(
                data=data,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                size_bytes=data_size
            )
            
            self.local_cache[cache_key] = entry
            
            # Prevent local cache from growing too large
            await self._cleanup_local_cache()
            
        except Exception as e:
            self.logger.error(f"Error storing in cache: {e}")
    
    async def _cleanup_local_cache(self, max_entries: int = 1000):
        """Clean up local cache to prevent memory issues."""
        if len(self.local_cache) <= max_entries:
            return
        
        # Remove expired entries first
        current_time = datetime.utcnow()
        expired_keys = [
            key for key, entry in self.local_cache.items()
            if entry.expires_at and current_time > entry.expires_at
        ]
        
        for key in expired_keys:
            del self.local_cache[key]
        
        # If still too many entries, remove least recently used
        if len(self.local_cache) > max_entries:
            # Sort by hit count (ascending) and creation time
            sorted_entries = sorted(
                self.local_cache.items(),
                key=lambda x: (x[1].hit_count, x[1].created_at)
            )
            
            # Remove oldest, least used entries
            entries_to_remove = len(self.local_cache) - max_entries
            for key, _ in sorted_entries[:entries_to_remove]:
                del self.local_cache[key]
    
    async def _analyze_query_plan(
        self,
        conn,
        query: str,
        params: List[Any]
    ) -> Optional[Dict[str, Any]]:
        """Analyze query execution plan for optimization insights."""
        try:
            # Get query plan
            explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS) {query}"
            plan_result = await conn.fetchval(explain_query, *params)
            
            if plan_result:
                plan_data = plan_result[0] if isinstance(plan_result, list) else plan_result
                
                return {
                    "total_cost": plan_data.get("Plan", {}).get("Total Cost", 0),
                    "execution_time": plan_data.get("Execution Time", 0),
                    "planning_time": plan_data.get("Planning Time", 0),
                    "node_type": plan_data.get("Plan", {}).get("Node Type", "Unknown")
                }
            
        except Exception as e:
            self.logger.debug(f"Could not analyze query plan: {e}")
        
        return None
    
    async def _update_query_stats(
        self,
        query: str,
        result_type: str,
        execution_time: float,
        plan: Optional[Dict[str, Any]] = None
    ):
        """Update query execution statistics."""
        # Create a simplified query signature for grouping
        query_signature = self._get_query_signature(query)
        
        if query_signature not in self.query_stats:
            self.query_stats[query_signature] = {
                "total_executions": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "errors": 0,
                "total_execution_time": 0,
                "avg_execution_time": 0,
                "max_execution_time": 0,
                "min_execution_time": float('inf')
            }
        
        stats = self.query_stats[query_signature]
        stats["total_executions"] += 1
        
        if result_type == "cache_hit":
            stats["cache_hits"] += 1
        elif result_type == "cache_miss":
            stats["cache_misses"] += 1
            stats["total_execution_time"] += execution_time
            stats["max_execution_time"] = max(stats["max_execution_time"], execution_time)
            stats["min_execution_time"] = min(stats["min_execution_time"], execution_time)
            stats["avg_execution_time"] = stats["total_execution_time"] / stats["cache_misses"]
        elif result_type == "error":
            stats["errors"] += 1
        
        # Store plan information if available
        if plan:
            stats["last_plan_cost"] = plan.get("total_cost", 0)
            stats["last_planning_time"] = plan.get("planning_time", 0)
    
    def _get_query_signature(self, query: str) -> str:
        """Generate a signature for query grouping (removes specific values)."""
        # Simple approach: remove common parameter patterns
        import re
        
        # Replace parameter placeholders
        signature = re.sub(r'\$\d+', '?', query)
        
        # Replace quoted strings and numbers
        signature = re.sub(r"'[^']*'", "'?'", signature)
        signature = re.sub(r'\b\d+\b', '?', signature)
        
        # Normalize whitespace
        signature = ' '.join(signature.split())
        
        return signature[:200]  # Limit length
    
    async def invalidate_cache(self, pattern: str = None, team_id: str = None):
        """Invalidate cache entries matching the pattern."""
        try:
            if pattern:
                # Invalidate Redis cache
                if self.redis_client:
                    keys = await self.redis_client.keys(f"*{pattern}*")
                    if keys:
                        await self.redis_client.delete(*keys)
                
                # Invalidate local cache
                keys_to_remove = [
                    key for key in self.local_cache.keys()
                    if pattern in key
                ]
                for key in keys_to_remove:
                    del self.local_cache[key]
            
            if team_id:
                # Invalidate team-specific cache entries
                team_pattern = f"team:{team_id}"
                await self.invalidate_cache(team_pattern)
            
            self.logger.info(f"Cache invalidated for pattern: {pattern}")
            
        except Exception as e:
            self.logger.error(f"Error invalidating cache: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_entries = len(self.local_cache)
        total_size = sum(entry.size_bytes for entry in self.local_cache.values())
        total_hits = sum(entry.hit_count for entry in self.local_cache.values())
        
        # Calculate hit rates from query stats
        total_cache_hits = sum(stats["cache_hits"] for stats in self.query_stats.values())
        total_cache_misses = sum(stats["cache_misses"] for stats in self.query_stats.values())
        total_requests = total_cache_hits + total_cache_misses
        
        hit_rate = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "local_cache": {
                "entries": total_entries,
                "size_mb": round(total_size / (1024 * 1024), 2),
                "total_hits": total_hits
            },
            "overall_performance": {
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests,
                "cache_hits": total_cache_hits,
                "cache_misses": total_cache_misses
            },
            "query_performance": self._get_top_queries()
        }
    
    def _get_top_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top queries by execution time and frequency."""
        sorted_queries = sorted(
            self.query_stats.items(),
            key=lambda x: x[1]["avg_execution_time"],
            reverse=True
        )
        
        return [
            {
                "query_signature": query[:100] + "..." if len(query) > 100 else query,
                "avg_execution_time": round(stats["avg_execution_time"], 3),
                "total_executions": stats["total_executions"],
                "cache_hit_rate": round(
                    (stats["cache_hits"] / stats["total_executions"] * 100)
                    if stats["total_executions"] > 0 else 0,
                    2
                )
            }
            for query, stats in sorted_queries[:limit]
        ]
    
    async def create_database_indexes(self):
        """Create optimized database indexes for changelog queries."""
        indexes = [
            # Performance metrics indexes
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_metrics_type_timestamp
            ON performance_metrics(metric_type, timestamp DESC)
            """,
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_metrics_team_timestamp
            ON performance_metrics(team_id, timestamp DESC)
            WHERE team_id IS NOT NULL
            """,
            
            # Changelog entries indexes
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_entries_team_date
            ON changelog_entries(team_id, week_start_date DESC)
            """,
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_entries_status_date
            ON changelog_entries(status, generated_at DESC)
            """,
            
            # Distribution tracking indexes
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_distributions_status
            ON changelog_distributions(distribution_status, delivered_at DESC)
            """,
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_distributions_changelog
            ON changelog_distributions(changelog_id, channel_type)
            """,
            
            # Analytics indexes
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_analytics_type_date
            ON changelog_analytics(metric_type, recorded_at DESC)
            """,
            
            # Performance alerts indexes
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_alerts_severity_timestamp
            ON performance_alerts(severity, timestamp DESC)
            WHERE resolved = false
            """
        ]
        
        try:
            async with get_database_connection() as conn:
                for index_sql in indexes:
                    try:
                        await conn.execute(index_sql)
                        self.logger.info(f"Created index: {index_sql.split('idx_')[1].split()[0]}")
                    except Exception as e:
                        self.logger.warning(f"Could not create index: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error creating database indexes: {e}")


# Global query optimizer instance
query_optimizer = QueryOptimizer()