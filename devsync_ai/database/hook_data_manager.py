"""
Hook Data Manager for JIRA Agent Hook database operations.

This module provides high-level database operations for hook executions,
team configurations, and performance metrics.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from devsync_ai.database.connection import get_database

logger = logging.getLogger(__name__)


class HookDataManager:
    """Manages database operations for hook data storage."""

    def __init__(self):
        """Initialize the hook data manager."""
        self.db = None

    async def _get_db(self):
        """Get database connection."""
        if self.db is None:
            self.db = await get_database()
        return self.db

    # Hook Execution Operations

    async def create_hook_execution(
        self,
        hook_id: str,
        hook_type: str,
        team_id: str,
        event_type: str,
        event_id: Optional[str] = None,
        ticket_key: Optional[str] = None,
        project_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new hook execution record.
        
        Args:
            hook_id: Unique identifier for the hook
            hook_type: Type of hook (StatusChangeHook, AssignmentHook, etc.)
            team_id: Team identifier
            event_type: Type of JIRA event
            event_id: Optional event identifier
            ticket_key: Optional JIRA ticket key
            project_key: Optional JIRA project key
            metadata: Optional additional metadata
            
        Returns:
            execution_id: Unique execution identifier
        """
        db = await self._get_db()
        execution_id = str(uuid.uuid4())
        
        execution_data = {
            "hook_id": hook_id,
            "execution_id": execution_id,
            "hook_type": hook_type,
            "team_id": team_id,
            "event_type": event_type,
            "event_id": event_id,
            "ticket_key": ticket_key,
            "project_key": project_key,
            "status": "STARTED",
            "started_at": datetime.utcnow().isoformat(),
            "notification_sent": False,
            "metadata": metadata or {},
        }
        
        try:
            await db.insert("hook_executions", execution_data)
            logger.info(f"Created hook execution: {execution_id}")
            return execution_id
        except Exception as e:
            logger.error(f"Failed to create hook execution: {e}")
            raise

    async def update_hook_execution(
        self,
        execution_id: str,
        status: str,
        execution_time_ms: Optional[float] = None,
        notification_sent: Optional[bool] = None,
        notification_result: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update an existing hook execution record.
        
        Args:
            execution_id: Unique execution identifier
            status: Execution status (SUCCESS, FAILED, TIMEOUT, CANCELLED)
            execution_time_ms: Execution time in milliseconds
            notification_sent: Whether notification was sent
            notification_result: Result of notification delivery
            errors: List of error messages
            metadata: Additional metadata to merge
            
        Returns:
            bool: True if update was successful
        """
        db = await self._get_db()
        
        update_data = {
            "status": status,
            "completed_at": datetime.utcnow().isoformat(),
        }
        
        if execution_time_ms is not None:
            update_data["execution_time_ms"] = execution_time_ms
        if notification_sent is not None:
            update_data["notification_sent"] = notification_sent
        if notification_result is not None:
            update_data["notification_result"] = notification_result
        if errors is not None:
            update_data["errors"] = errors
        if metadata is not None:
            # Merge with existing metadata
            existing = await self.get_hook_execution(execution_id)
            if existing and existing.get("metadata"):
                merged_metadata = existing["metadata"].copy()
                merged_metadata.update(metadata)
                update_data["metadata"] = merged_metadata
            else:
                update_data["metadata"] = metadata
        
        try:
            result = await db.update(
                "hook_executions",
                update_data,
                {"execution_id": execution_id}
            )
            logger.info(f"Updated hook execution: {execution_id}")
            return len(result) > 0
        except Exception as e:
            logger.error(f"Failed to update hook execution {execution_id}: {e}")
            raise

    async def get_hook_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a hook execution by ID.
        
        Args:
            execution_id: Unique execution identifier
            
        Returns:
            Hook execution data or None if not found
        """
        db = await self._get_db()
        
        try:
            result = await db.select(
                "hook_executions",
                filters={"execution_id": execution_id},
                limit=1
            )
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get hook execution {execution_id}: {e}")
            raise

    async def get_hook_executions(
        self,
        hook_id: Optional[str] = None,
        team_id: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get hook executions with filtering.
        
        Args:
            hook_id: Filter by hook ID
            team_id: Filter by team ID
            status: Filter by execution status
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of hook execution records
        """
        db = await self._get_db()
        
        filters = {}
        if hook_id:
            filters["hook_id"] = hook_id
        if team_id:
            filters["team_id"] = team_id
        if status:
            filters["status"] = status
        if start_time:
            filters["started_at"] = {"gte": start_time.isoformat()}
        if end_time:
            if "started_at" in filters:
                # Handle range query
                filters["started_at"] = {
                    "gte": start_time.isoformat(),
                    "lte": end_time.isoformat()
                }
            else:
                filters["started_at"] = {"lte": end_time.isoformat()}
        
        try:
            return await db.select(
                "hook_executions",
                filters=filters,
                limit=limit,
                offset=offset,
                order_by="started_at",
                order_desc=True
            )
        except Exception as e:
            logger.error(f"Failed to get hook executions: {e}")
            raise

    # Team Configuration Operations

    async def get_team_configuration(self, team_id: str) -> Dict[str, Any]:
        """
        Get team hook configuration with fallback to default.
        
        Args:
            team_id: Team identifier
            
        Returns:
            Team configuration data
        """
        db = await self._get_db()
        
        try:
            # Use the database function that handles fallback
            result = await db.execute_rpc(
                "get_team_hook_configuration",
                {"team_id_param": team_id}
            )
            return result if result else {}
        except Exception as e:
            logger.error(f"Failed to get team configuration for {team_id}: {e}")
            # Return minimal default configuration
            return {
                "team_name": f"{team_id} Team",
                "default_channels": {
                    "general": f"#{team_id}"
                },
                "rules": []
            }

    async def save_team_configuration(
        self,
        team_id: str,
        configuration: Dict[str, Any],
        enabled: bool = True,
        version: str = "1.0.0",
    ) -> bool:
        """
        Save team hook configuration.
        
        Args:
            team_id: Team identifier
            configuration: Configuration data
            enabled: Whether configuration is enabled
            version: Configuration version
            
        Returns:
            bool: True if save was successful
        """
        db = await self._get_db()
        
        config_data = {
            "team_id": team_id,
            "configuration": configuration,
            "enabled": enabled,
            "version": version,
        }
        
        try:
            # Try to update existing configuration
            result = await db.update(
                "team_hook_configurations",
                config_data,
                {"team_id": team_id}
            )
            
            # If no rows updated, insert new configuration
            if not result:
                await db.insert("team_hook_configurations", config_data)
            
            logger.info(f"Saved team configuration for {team_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save team configuration for {team_id}: {e}")
            raise

    async def get_all_team_configurations(
        self, enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all team configurations.
        
        Args:
            enabled_only: Whether to return only enabled configurations
            
        Returns:
            List of team configuration records
        """
        db = await self._get_db()
        
        filters = {}
        if enabled_only:
            filters["enabled"] = True
        
        try:
            return await db.select(
                "team_hook_configurations",
                filters=filters,
                order_by="team_id"
            )
        except Exception as e:
            logger.error(f"Failed to get team configurations: {e}")
            raise

    # Performance Metrics Operations

    async def get_hook_performance_summary(
        self,
        hook_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[Dict[str, Any]]:
        """
        Get performance summary for a specific hook.
        
        Args:
            hook_id: Hook identifier
            start_time: Start time for analysis
            end_time: End time for analysis
            
        Returns:
            Performance summary data or None
        """
        db = await self._get_db()
        
        try:
            result = await db.execute_rpc(
                "get_hook_performance_summary",
                {
                    "hook_id_param": hook_id,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                }
            )
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get performance summary for {hook_id}: {e}")
            raise

    async def aggregate_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        """
        Aggregate performance metrics for the given time range.
        
        Args:
            start_time: Start time for aggregation
            end_time: End time for aggregation
            
        Returns:
            Number of metrics processed
        """
        db = await self._get_db()
        
        try:
            result = await db.execute_rpc(
                "aggregate_hook_performance_metrics",
                {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                }
            )
            return result if isinstance(result, int) else 0
        except Exception as e:
            logger.error(f"Failed to aggregate performance metrics: {e}")
            raise

    async def get_performance_metrics(
        self,
        hook_id: Optional[str] = None,
        team_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get performance metrics with filtering.
        
        Args:
            hook_id: Filter by hook ID
            team_id: Filter by team ID
            start_time: Filter by time bucket start
            end_time: Filter by time bucket end
            limit: Maximum number of results
            
        Returns:
            List of performance metric records
        """
        db = await self._get_db()
        
        filters = {}
        if hook_id:
            filters["hook_id"] = hook_id
        if team_id:
            filters["team_id"] = team_id
        if start_time:
            filters["time_bucket"] = {"gte": start_time.isoformat()}
        if end_time:
            if "time_bucket" in filters:
                filters["time_bucket"] = {
                    "gte": start_time.isoformat(),
                    "lte": end_time.isoformat()
                }
            else:
                filters["time_bucket"] = {"lte": end_time.isoformat()}
        
        try:
            return await db.select(
                "hook_performance_metrics",
                filters=filters,
                limit=limit,
                order_by="time_bucket",
                order_desc=True
            )
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            raise

    # Utility Methods

    async def get_execution_statistics(
        self,
        team_id: Optional[str] = None,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get execution statistics for the last N hours.
        
        Args:
            team_id: Optional team filter
            hours: Number of hours to look back
            
        Returns:
            Dictionary with execution statistics
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        end_time = datetime.utcnow()
        
        executions = await self.get_hook_executions(
            team_id=team_id,
            start_time=start_time,
            end_time=end_time,
            limit=10000  # Get all executions in the time range
        )
        
        total = len(executions)
        successful = len([e for e in executions if e["status"] == "SUCCESS"])
        failed = len([e for e in executions if e["status"] in ["FAILED", "TIMEOUT", "CANCELLED"]])
        
        # Calculate average execution time
        execution_times = [
            e["execution_time_ms"] for e in executions 
            if e.get("execution_time_ms") is not None
        ]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Count by hook type
        hook_type_counts = {}
        for execution in executions:
            hook_type = execution["hook_type"]
            hook_type_counts[hook_type] = hook_type_counts.get(hook_type, 0) + 1
        
        return {
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": successful / total if total > 0 else 0,
            "avg_execution_time_ms": avg_execution_time,
            "hook_type_distribution": hook_type_counts,
            "time_range_hours": hours,
        }

    async def cleanup_old_executions(self, days: int = 90) -> int:
        """
        Clean up old hook execution records.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of records deleted
        """
        db = await self._get_db()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        try:
            result = await db.delete(
                "hook_executions",
                {"created_at": {"lt": cutoff_date.isoformat()}}
            )
            deleted_count = len(result) if result else 0
            logger.info(f"Cleaned up {deleted_count} old hook execution records")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old executions: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the hook data storage.
        
        Returns:
            Health check results
        """
        db = await self._get_db()
        
        try:
            # Test basic connectivity
            db_healthy = await db.health_check()
            
            # Count recent executions
            recent_executions = await self.get_hook_executions(
                start_time=datetime.utcnow() - timedelta(hours=1),
                limit=1
            )
            
            # Count team configurations
            team_configs = await self.get_all_team_configurations()
            
            return {
                "database_healthy": db_healthy,
                "recent_executions_count": len(recent_executions),
                "team_configurations_count": len(team_configs),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "database_healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


# Global instance
_hook_data_manager: Optional[HookDataManager] = None


async def get_hook_data_manager() -> HookDataManager:
    """Get the global hook data manager instance."""
    global _hook_data_manager
    if _hook_data_manager is None:
        _hook_data_manager = HookDataManager()
    return _hook_data_manager