"""
Analytics Data Manager for DevSync AI.

This module provides efficient storage, retrieval, and management of analytics data
with data retention policies, aggregation, and integrity checking.
"""

import asyncio
import logging
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import aiosqlite
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsRecord:
    """Base analytics record structure."""
    id: Optional[str]
    timestamp: datetime
    record_type: str
    team_id: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class DataRetentionPolicy:
    """Data retention policy configuration."""
    record_type: str
    retention_days: int
    aggregation_interval: str  # 'hourly', 'daily', 'weekly'
    compression_enabled: bool


class AnalyticsDataManager:
    """
    Comprehensive data manager for analytics storage and retrieval.
    
    Provides efficient storage, querying, aggregation, and data lifecycle
    management for all analytics data types.
    """
    
    def __init__(self, db_path: str = "analytics.db"):
        """Initialize the analytics data manager."""
        self.db_path = db_path
        self.retention_policies = {
            'hook_execution': DataRetentionPolicy('hook_execution', 90, 'hourly', True),
            'system_metrics': DataRetentionPolicy('system_metrics', 30, 'hourly', True),
            'team_productivity': DataRetentionPolicy('team_productivity', 180, 'daily', True),
            'user_engagement': DataRetentionPolicy('user_engagement', 60, 'daily', False),
            'ab_test_results': DataRetentionPolicy('ab_test_results', 365, 'none', False),
            'predictive_insights': DataRetentionPolicy('predictive_insights', 120, 'daily', False)
        }
        
        # Aggregation cache
        self.aggregation_cache: Dict[str, Tuple[datetime, Any]] = {}
        self.cache_ttl = timedelta(minutes=15)
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._aggregation_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self):
        """Initialize the database and start background tasks."""
        await self._create_tables()
        await self._start_background_tasks()
        logger.info("Analytics data manager initialized")
    
    async def shutdown(self):
        """Shutdown the data manager and cleanup resources."""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._aggregation_task:
            self._aggregation_task.cancel()
        
        logger.info("Analytics data manager shutdown")
    
    async def _create_tables(self):
        """Create database tables for analytics data."""
        async with aiosqlite.connect(self.db_path) as db:
            # Main analytics records table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS analytics_records (
                    id TEXT PRIMARY KEY,
                    timestamp DATETIME NOT NULL,
                    record_type TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Aggregated data table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS aggregated_data (
                    id TEXT PRIMARY KEY,
                    record_type TEXT NOT NULL,
                    team_id TEXT,
                    aggregation_period TEXT NOT NULL,
                    period_start DATETIME NOT NULL,
                    period_end DATETIME NOT NULL,
                    aggregated_data TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Data integrity checksums
            await db.execute("""
                CREATE TABLE IF NOT EXISTS data_integrity (
                    table_name TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    record_count INTEGER NOT NULL,
                    last_verified DATETIME NOT NULL,
                    PRIMARY KEY (table_name)
                )
            """)
            
            # Create indexes for performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_records_timestamp ON analytics_records(timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_records_type_team ON analytics_records(record_type, team_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_aggregated_period ON aggregated_data(aggregation_period, period_start)")
            
            await db.commit()
    
    async def store_record(self, record: AnalyticsRecord) -> str:
        """
        Store an analytics record.
        
        Args:
            record: Analytics record to store
            
        Returns:
            Record ID
        """
        if not record.id:
            record.id = f"{record.record_type}_{record.team_id}_{int(record.timestamp.timestamp())}"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO analytics_records 
                (id, timestamp, record_type, team_id, data, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.timestamp.isoformat(),
                record.record_type,
                record.team_id,
                json.dumps(record.data),
                json.dumps(record.metadata)
            ))
            await db.commit()
        
        return record.id
    
    async def store_batch_records(self, records: List[AnalyticsRecord]) -> List[str]:
        """
        Store multiple analytics records efficiently.
        
        Args:
            records: List of analytics records
            
        Returns:
            List of record IDs
        """
        record_ids = []
        
        async with aiosqlite.connect(self.db_path) as db:
            for record in records:
                if not record.id:
                    record.id = f"{record.record_type}_{record.team_id}_{int(record.timestamp.timestamp())}"
                record_ids.append(record.id)
            
            await db.executemany("""
                INSERT OR REPLACE INTO analytics_records 
                (id, timestamp, record_type, team_id, data, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                (
                    record.id,
                    record.timestamp.isoformat(),
                    record.record_type,
                    record.team_id,
                    json.dumps(record.data),
                    json.dumps(record.metadata)
                )
                for record in records
            ])
            await db.commit()
        
        return record_ids
    
    async def query_records(
        self,
        record_type: Optional[str] = None,
        team_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[AnalyticsRecord]:
        """
        Query analytics records with filtering.
        
        Args:
            record_type: Filter by record type
            team_id: Filter by team ID
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum number of records
            offset: Offset for pagination
            
        Returns:
            List of analytics records
        """
        query = "SELECT * FROM analytics_records WHERE 1=1"
        params = []
        
        if record_type:
            query += " AND record_type = ?"
            params.append(record_type)
        
        if team_id:
            query += " AND team_id = ?"
            params.append(team_id)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        if offset:
            query += " OFFSET ?"
            params.append(offset)
        
        records = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    records.append(AnalyticsRecord(
                        id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        record_type=row[2],
                        team_id=row[3],
                        data=json.loads(row[4]),
                        metadata=json.loads(row[5])
                    ))
        
        return records
    
    async def aggregate_data(
        self,
        record_type: str,
        aggregation_period: str,
        team_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Aggregate analytics data for reporting.
        
        Args:
            record_type: Type of records to aggregate
            aggregation_period: 'hourly', 'daily', 'weekly', 'monthly'
            team_id: Optional team filter
            start_time: Start time for aggregation
            end_time: End time for aggregation
            
        Returns:
            Aggregated data
        """
        cache_key = f"{record_type}_{aggregation_period}_{team_id}_{start_time}_{end_time}"
        
        # Check cache
        if cache_key in self.aggregation_cache:
            cached_time, cached_data = self.aggregation_cache[cache_key]
            if datetime.now(timezone.utc) - cached_time < self.cache_ttl:
                return cached_data
        
        # Query raw data
        records = await self.query_records(
            record_type=record_type,
            team_id=team_id,
            start_time=start_time,
            end_time=end_time
        )
        
        if not records:
            return {"aggregated_data": {}, "record_count": 0}
        
        # Perform aggregation based on record type
        aggregated_data = await self._perform_aggregation(records, aggregation_period)
        
        # Cache result
        self.aggregation_cache[cache_key] = (datetime.now(timezone.utc), aggregated_data)
        
        return aggregated_data
    
    async def _perform_aggregation(
        self,
        records: List[AnalyticsRecord],
        aggregation_period: str
    ) -> Dict[str, Any]:
        """Perform data aggregation based on period."""
        if not records:
            return {"aggregated_data": {}, "record_count": 0}
        
        # Group records by time period
        period_groups = {}
        
        for record in records:
            period_key = self._get_period_key(record.timestamp, aggregation_period)
            if period_key not in period_groups:
                period_groups[period_key] = []
            period_groups[period_key].append(record)
        
        # Aggregate each period
        aggregated_periods = {}
        
        for period_key, period_records in period_groups.items():
            aggregated_periods[period_key] = await self._aggregate_period_records(period_records)
        
        return {
            "aggregated_data": aggregated_periods,
            "record_count": len(records),
            "period_count": len(period_groups),
            "aggregation_period": aggregation_period
        }
    
    def _get_period_key(self, timestamp: datetime, period: str) -> str:
        """Get period key for grouping."""
        if period == 'hourly':
            return timestamp.strftime('%Y-%m-%d %H:00')
        elif period == 'daily':
            return timestamp.strftime('%Y-%m-%d')
        elif period == 'weekly':
            # Get Monday of the week
            monday = timestamp - timedelta(days=timestamp.weekday())
            return monday.strftime('%Y-%m-%d')
        elif period == 'monthly':
            return timestamp.strftime('%Y-%m')
        else:
            return timestamp.isoformat()
    
    async def _aggregate_period_records(self, records: List[AnalyticsRecord]) -> Dict[str, Any]:
        """Aggregate records within a time period."""
        if not records:
            return {}
        
        record_type = records[0].record_type
        
        if record_type == 'hook_execution':
            return await self._aggregate_hook_executions(records)
        elif record_type == 'system_metrics':
            return await self._aggregate_system_metrics(records)
        elif record_type == 'team_productivity':
            return await self._aggregate_team_productivity(records)
        else:
            # Generic aggregation
            return {
                "count": len(records),
                "first_timestamp": records[0].timestamp.isoformat(),
                "last_timestamp": records[-1].timestamp.isoformat()
            }
    
    async def _aggregate_hook_executions(self, records: List[AnalyticsRecord]) -> Dict[str, Any]:
        """Aggregate hook execution records."""
        total_executions = len(records)
        successful_executions = sum(1 for r in records if r.data.get('success', False))
        
        execution_times = [r.data.get('execution_time_ms', 0) for r in records if 'execution_time_ms' in r.data]
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "average_execution_time_ms": sum(execution_times) / len(execution_times) if execution_times else 0,
            "min_execution_time_ms": min(execution_times) if execution_times else 0,
            "max_execution_time_ms": max(execution_times) if execution_times else 0
        }
    
    async def _aggregate_system_metrics(self, records: List[AnalyticsRecord]) -> Dict[str, Any]:
        """Aggregate system metrics records."""
        cpu_values = [r.data.get('cpu_usage', 0) for r in records if 'cpu_usage' in r.data]
        memory_values = [r.data.get('memory_usage', 0) for r in records if 'memory_usage' in r.data]
        
        return {
            "record_count": len(records),
            "average_cpu_usage": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            "max_cpu_usage": max(cpu_values) if cpu_values else 0,
            "average_memory_usage": sum(memory_values) / len(memory_values) if memory_values else 0,
            "max_memory_usage": max(memory_values) if memory_values else 0
        }
    
    async def _aggregate_team_productivity(self, records: List[AnalyticsRecord]) -> Dict[str, Any]:
        """Aggregate team productivity records."""
        productivity_scores = [r.data.get('productivity_score', 0) for r in records if 'productivity_score' in r.data]
        
        return {
            "record_count": len(records),
            "average_productivity_score": sum(productivity_scores) / len(productivity_scores) if productivity_scores else 0,
            "max_productivity_score": max(productivity_scores) if productivity_scores else 0,
            "min_productivity_score": min(productivity_scores) if productivity_scores else 0
        }
    
    async def export_data(
        self,
        record_type: Optional[str] = None,
        team_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        format: str = 'json'
    ) -> str:
        """
        Export analytics data in specified format.
        
        Args:
            record_type: Filter by record type
            team_id: Filter by team ID
            start_time: Start time filter
            end_time: End time filter
            format: Export format ('json', 'csv')
            
        Returns:
            Exported data as string
        """
        records = await self.query_records(
            record_type=record_type,
            team_id=team_id,
            start_time=start_time,
            end_time=end_time
        )
        
        if format == 'json':
            return json.dumps([asdict(record) for record in records], indent=2, default=str)
        elif format == 'csv':
            return await self._export_to_csv(records)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def _export_to_csv(self, records: List[AnalyticsRecord]) -> str:
        """Export records to CSV format."""
        if not records:
            return ""
        
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['id', 'timestamp', 'record_type', 'team_id', 'data', 'metadata'])
        
        # Write records
        for record in records:
            writer.writerow([
                record.id,
                record.timestamp.isoformat(),
                record.record_type,
                record.team_id,
                json.dumps(record.data),
                json.dumps(record.metadata)
            ])
        
        return output.getvalue()
    
    async def verify_data_integrity(self) -> Dict[str, Any]:
        """Verify data integrity and return status."""
        integrity_results = {}
        
        async with aiosqlite.connect(self.db_path) as db:
            # Check analytics_records table
            async with db.execute("SELECT COUNT(*) FROM analytics_records") as cursor:
                count = (await cursor.fetchone())[0]
            
            # Simple checksum based on count and latest timestamp
            async with db.execute("SELECT MAX(timestamp) FROM analytics_records") as cursor:
                latest_timestamp = (await cursor.fetchone())[0]
            
            checksum = f"{count}_{latest_timestamp}"
            
            integrity_results['analytics_records'] = {
                'record_count': count,
                'latest_timestamp': latest_timestamp,
                'checksum': checksum,
                'status': 'healthy'
            }
            
            # Update integrity table
            await db.execute("""
                INSERT OR REPLACE INTO data_integrity 
                (table_name, checksum, record_count, last_verified)
                VALUES (?, ?, ?, ?)
            """, ('analytics_records', checksum, count, datetime.now(timezone.utc).isoformat()))
            
            await db.commit()
        
        return integrity_results
    
    async def _start_background_tasks(self):
        """Start background maintenance tasks."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._aggregation_task = asyncio.create_task(self._aggregation_loop())
    
    async def _cleanup_loop(self):
        """Background task for data cleanup based on retention policies."""
        while self._running:
            try:
                await self._cleanup_expired_data()
                await asyncio.sleep(3600)  # Run every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _aggregation_loop(self):
        """Background task for data aggregation."""
        while self._running:
            try:
                await self._create_aggregations()
                await asyncio.sleep(1800)  # Run every 30 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Aggregation loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _cleanup_expired_data(self):
        """Clean up expired data based on retention policies."""
        async with aiosqlite.connect(self.db_path) as db:
            for record_type, policy in self.retention_policies.items():
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
                
                # Delete expired records
                result = await db.execute("""
                    DELETE FROM analytics_records 
                    WHERE record_type = ? AND timestamp < ?
                """, (record_type, cutoff_date.isoformat()))
                
                deleted_count = result.rowcount
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} expired {record_type} records")
            
            await db.commit()
    
    async def _create_aggregations(self):
        """Create aggregated data for reporting."""
        # This would create pre-aggregated data for common queries
        # to improve dashboard performance
        
        for record_type, policy in self.retention_policies.items():
            if policy.aggregation_interval == 'none':
                continue
            
            try:
                # Create aggregations for the last 24 hours
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(hours=24)
                
                aggregated = await self.aggregate_data(
                    record_type=record_type,
                    aggregation_period=policy.aggregation_interval,
                    start_time=start_time,
                    end_time=end_time
                )
                
                # Store aggregated data
                await self._store_aggregated_data(
                    record_type, policy.aggregation_interval, 
                    start_time, end_time, aggregated
                )
                
            except Exception as e:
                logger.error(f"Failed to create aggregation for {record_type}: {e}")
    
    async def _store_aggregated_data(
        self,
        record_type: str,
        aggregation_period: str,
        start_time: datetime,
        end_time: datetime,
        aggregated_data: Dict[str, Any]
    ):
        """Store aggregated data in the database."""
        aggregation_id = f"{record_type}_{aggregation_period}_{int(start_time.timestamp())}"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO aggregated_data
                (id, record_type, aggregation_period, period_start, period_end, aggregated_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                aggregation_id,
                record_type,
                aggregation_period,
                start_time.isoformat(),
                end_time.isoformat(),
                json.dumps(aggregated_data)
            ))
            await db.commit()


# Global data manager instance
_data_manager: Optional[AnalyticsDataManager] = None


async def get_analytics_data_manager() -> AnalyticsDataManager:
    """Get the global analytics data manager instance."""
    global _data_manager
    if _data_manager is None:
        _data_manager = AnalyticsDataManager()
        await _data_manager.initialize()
    return _data_manager


async def shutdown_analytics_data_manager():
    """Shutdown the global analytics data manager."""
    global _data_manager
    if _data_manager:
        await _data_manager.shutdown()
        _data_manager = None