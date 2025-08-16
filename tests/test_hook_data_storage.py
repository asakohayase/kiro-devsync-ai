"""
Tests for hook data storage and database integration.

This module tests the database schema, migrations, and data operations
for JIRA Agent Hook data storage.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

from devsync_ai.database.hook_data_manager import HookDataManager, get_hook_data_manager
from devsync_ai.database.connection import get_database


class TestHookDataStorage:
    """Test suite for hook data storage functionality."""

    @pytest.fixture
    async def hook_data_manager(self):
        """Get hook data manager instance."""
        return await get_hook_data_manager()

    @pytest.fixture
    async def sample_team_config(self):
        """Sample team configuration for testing."""
        return {
            "team_name": "Test Team",
            "default_channels": {
                "status_change": "#test-updates",
                "assignment": "#test-assignments",
                "comment": "#test-discussions",
                "blocker": "#test-alerts",
                "general": "#test"
            },
            "notification_preferences": {
                "batch_threshold": 3,
                "batch_timeout_minutes": 5,
                "quiet_hours": {
                    "enabled": True,
                    "start": "22:00",
                    "end": "08:00"
                },
                "weekend_notifications": False
            },
            "business_hours": {
                "start": "09:00",
                "end": "17:00",
                "timezone": "UTC",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
            },
            "escalation_rules": [],
            "rules": [
                {
                    "rule_id": "test_rule_1",
                    "name": "Test Status Changes",
                    "description": "Test rule for status changes",
                    "hook_types": ["StatusChangeHook"],
                    "enabled": True,
                    "priority": 10,
                    "conditions": {
                        "logic": "and",
                        "conditions": [
                            {
                                "field": "event.classification.affected_teams",
                                "operator": "contains",
                                "value": "test"
                            }
                        ]
                    },
                    "metadata": {
                        "channels": ["#test"]
                    }
                }
            ],
            "metadata": {}
        }

    async def test_database_connection(self):
        """Test basic database connectivity."""
        db = await get_database()
        assert db is not None
        
        # Test health check
        healthy = await db.health_check()
        assert healthy is True

    async def test_hook_execution_lifecycle(self, hook_data_manager):
        """Test complete hook execution lifecycle."""
        # Create hook execution
        hook_id = f"test_hook_{uuid.uuid4().hex[:8]}"
        execution_id = await hook_data_manager.create_hook_execution(
            hook_id=hook_id,
            hook_type="StatusChangeHook",
            team_id="test_team",
            event_type="jira:issue_updated",
            event_id="event_123",
            ticket_key="TEST-123",
            project_key="TEST",
            metadata={"test": "data"}
        )
        
        assert execution_id is not None
        assert isinstance(execution_id, str)
        
        # Get hook execution
        execution = await hook_data_manager.get_hook_execution(execution_id)
        assert execution is not None
        assert execution["hook_id"] == hook_id
        assert execution["hook_type"] == "StatusChangeHook"
        assert execution["team_id"] == "test_team"
        assert execution["event_type"] == "jira:issue_updated"
        assert execution["ticket_key"] == "TEST-123"
        assert execution["status"] == "STARTED"
        assert execution["metadata"]["test"] == "data"
        
        # Update hook execution
        success = await hook_data_manager.update_hook_execution(
            execution_id=execution_id,
            status="SUCCESS",
            execution_time_ms=150.5,
            notification_sent=True,
            notification_result={"channel": "#test", "message_id": "msg_123"},
            metadata={"additional": "info"}
        )
        
        assert success is True
        
        # Verify update
        updated_execution = await hook_data_manager.get_hook_execution(execution_id)
        assert updated_execution["status"] == "SUCCESS"
        assert updated_execution["execution_time_ms"] == 150.5
        assert updated_execution["notification_sent"] is True
        assert updated_execution["notification_result"]["channel"] == "#test"
        assert updated_execution["metadata"]["test"] == "data"  # Original metadata preserved
        assert updated_execution["metadata"]["additional"] == "info"  # New metadata added
        assert updated_execution["completed_at"] is not None

    async def test_hook_execution_queries(self, hook_data_manager):
        """Test hook execution query functionality."""
        # Create multiple test executions
        hook_id = f"query_test_hook_{uuid.uuid4().hex[:8]}"
        execution_ids = []
        
        for i in range(5):
            execution_id = await hook_data_manager.create_hook_execution(
                hook_id=hook_id,
                hook_type="AssignmentHook",
                team_id="query_test_team",
                event_type="jira:issue_assigned",
                ticket_key=f"QUERY-{i}",
                metadata={"index": i}
            )
            execution_ids.append(execution_id)
            
            # Update some executions to SUCCESS, others to FAILED
            status = "SUCCESS" if i % 2 == 0 else "FAILED"
            await hook_data_manager.update_hook_execution(
                execution_id=execution_id,
                status=status,
                execution_time_ms=100.0 + i * 10
            )
        
        # Test filtering by hook_id
        hook_executions = await hook_data_manager.get_hook_executions(hook_id=hook_id)
        assert len(hook_executions) == 5
        
        # Test filtering by team_id
        team_executions = await hook_data_manager.get_hook_executions(team_id="query_test_team")
        assert len(team_executions) >= 5  # May include other test executions
        
        # Test filtering by status
        success_executions = await hook_data_manager.get_hook_executions(
            hook_id=hook_id, status="SUCCESS"
        )
        assert len(success_executions) == 3  # Indices 0, 2, 4
        
        failed_executions = await hook_data_manager.get_hook_executions(
            hook_id=hook_id, status="FAILED"
        )
        assert len(failed_executions) == 2  # Indices 1, 3
        
        # Test time-based filtering
        now = datetime.utcnow()
        recent_executions = await hook_data_manager.get_hook_executions(
            hook_id=hook_id,
            start_time=now - timedelta(minutes=5),
            end_time=now + timedelta(minutes=5)
        )
        assert len(recent_executions) == 5
        
        # Test pagination
        page1 = await hook_data_manager.get_hook_executions(hook_id=hook_id, limit=2, offset=0)
        page2 = await hook_data_manager.get_hook_executions(hook_id=hook_id, limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0]["execution_id"] != page2[0]["execution_id"]

    async def test_team_configuration_operations(self, hook_data_manager, sample_team_config):
        """Test team configuration CRUD operations."""
        team_id = f"test_team_{uuid.uuid4().hex[:8]}"
        
        # Test getting non-existent configuration (should return default)
        config = await hook_data_manager.get_team_configuration(team_id)
        assert config is not None
        assert config["team_name"] == f"{team_id} Team"
        assert "default_channels" in config
        assert "rules" in config
        
        # Save team configuration
        success = await hook_data_manager.save_team_configuration(
            team_id=team_id,
            configuration=sample_team_config,
            enabled=True,
            version="1.0.0"
        )
        assert success is True
        
        # Get saved configuration
        saved_config = await hook_data_manager.get_team_configuration(team_id)
        assert saved_config["team_name"] == "Test Team"
        assert saved_config["default_channels"]["status_change"] == "#test-updates"
        assert len(saved_config["rules"]) == 1
        assert saved_config["rules"][0]["rule_id"] == "test_rule_1"
        
        # Update configuration
        updated_config = sample_team_config.copy()
        updated_config["team_name"] = "Updated Test Team"
        updated_config["rules"].append({
            "rule_id": "test_rule_2",
            "name": "Test Assignments",
            "description": "Test rule for assignments",
            "hook_types": ["AssignmentHook"],
            "enabled": True,
            "priority": 20,
            "conditions": {"logic": "or", "conditions": []},
            "metadata": {"channels": ["#test-assignments"]}
        })
        
        success = await hook_data_manager.save_team_configuration(
            team_id=team_id,
            configuration=updated_config,
            version="1.1.0"
        )
        assert success is True
        
        # Verify update
        final_config = await hook_data_manager.get_team_configuration(team_id)
        assert final_config["team_name"] == "Updated Test Team"
        assert len(final_config["rules"]) == 2
        
        # Test getting all configurations
        all_configs = await hook_data_manager.get_all_team_configurations()
        team_config_found = any(config["team_id"] == team_id for config in all_configs)
        assert team_config_found is True

    async def test_performance_metrics(self, hook_data_manager):
        """Test performance metrics functionality."""
        hook_id = f"perf_test_hook_{uuid.uuid4().hex[:8]}"
        
        # Create multiple executions with different performance characteristics
        execution_times = [50.0, 100.0, 150.0, 200.0, 500.0]  # Mix of fast and slow executions
        
        for i, exec_time in enumerate(execution_times):
            execution_id = await hook_data_manager.create_hook_execution(
                hook_id=hook_id,
                hook_type="CommentHook",
                team_id="perf_test_team",
                event_type="jira:issue_commented",
                ticket_key=f"PERF-{i}"
            )
            
            # Update with performance data
            status = "SUCCESS" if exec_time < 300 else "FAILED"  # Slow executions fail
            await hook_data_manager.update_hook_execution(
                execution_id=execution_id,
                status=status,
                execution_time_ms=exec_time,
                notification_sent=status == "SUCCESS"
            )
        
        # Test performance summary
        start_time = datetime.utcnow() - timedelta(minutes=5)
        end_time = datetime.utcnow() + timedelta(minutes=5)
        
        summary = await hook_data_manager.get_hook_performance_summary(
            hook_id=hook_id,
            start_time=start_time,
            end_time=end_time
        )
        
        assert summary is not None
        assert summary["hook_id"] == hook_id
        assert summary["hook_type"] == "CommentHook"
        assert summary["team_id"] == "perf_test_team"
        assert summary["total_executions"] == 5
        assert summary["successful_executions"] == 4  # exec_time < 300
        assert summary["failed_executions"] == 1  # exec_time >= 300
        assert summary["success_rate"] == 0.8  # 4/5
        assert summary["avg_execution_time_ms"] == 200.0  # Average of execution_times
        assert summary["last_execution"] is not None
        
        # Test aggregation
        processed_count = await hook_data_manager.aggregate_performance_metrics(
            start_time=start_time,
            end_time=end_time
        )
        assert processed_count >= 0  # Should process at least our test data
        
        # Test getting performance metrics
        metrics = await hook_data_manager.get_performance_metrics(
            hook_id=hook_id,
            start_time=start_time,
            end_time=end_time
        )
        # Metrics may be empty if aggregation hasn't run yet, but should not error
        assert isinstance(metrics, list)

    async def test_execution_statistics(self, hook_data_manager):
        """Test execution statistics functionality."""
        team_id = f"stats_test_team_{uuid.uuid4().hex[:8]}"
        
        # Create executions with different hook types and statuses
        test_data = [
            ("StatusChangeHook", "SUCCESS", 100.0),
            ("StatusChangeHook", "SUCCESS", 120.0),
            ("StatusChangeHook", "FAILED", 200.0),
            ("AssignmentHook", "SUCCESS", 80.0),
            ("AssignmentHook", "SUCCESS", 90.0),
            ("CommentHook", "TIMEOUT", 5000.0),
        ]
        
        for hook_type, status, exec_time in test_data:
            execution_id = await hook_data_manager.create_hook_execution(
                hook_id=f"stats_hook_{hook_type.lower()}",
                hook_type=hook_type,
                team_id=team_id,
                event_type="jira:test_event"
            )
            
            await hook_data_manager.update_hook_execution(
                execution_id=execution_id,
                status=status,
                execution_time_ms=exec_time
            )
        
        # Get statistics
        stats = await hook_data_manager.get_execution_statistics(team_id=team_id, hours=1)
        
        assert stats["total_executions"] == 6
        assert stats["successful_executions"] == 4
        assert stats["failed_executions"] == 2  # FAILED + TIMEOUT
        assert stats["success_rate"] == 4/6
        assert stats["avg_execution_time_ms"] > 0
        assert "StatusChangeHook" in stats["hook_type_distribution"]
        assert "AssignmentHook" in stats["hook_type_distribution"]
        assert "CommentHook" in stats["hook_type_distribution"]
        assert stats["hook_type_distribution"]["StatusChangeHook"] == 3
        assert stats["hook_type_distribution"]["AssignmentHook"] == 2
        assert stats["hook_type_distribution"]["CommentHook"] == 1

    async def test_health_check(self, hook_data_manager):
        """Test health check functionality."""
        health = await hook_data_manager.health_check()
        
        assert "database_healthy" in health
        assert "recent_executions_count" in health
        assert "team_configurations_count" in health
        assert "timestamp" in health
        
        # Database should be healthy in test environment
        assert health["database_healthy"] is True
        assert isinstance(health["recent_executions_count"], int)
        assert isinstance(health["team_configurations_count"], int)

    async def test_cleanup_operations(self, hook_data_manager):
        """Test cleanup operations."""
        # Create an old execution (simulate by creating and then manually updating timestamp)
        execution_id = await hook_data_manager.create_hook_execution(
            hook_id="cleanup_test_hook",
            hook_type="StatusChangeHook",
            team_id="cleanup_test_team",
            event_type="jira:test_event"
        )
        
        # Note: In a real test environment, we would need to manually update the created_at
        # timestamp to be older than the cleanup threshold. For this test, we'll just
        # verify the cleanup function runs without error.
        
        # Test cleanup (should not delete recent records)
        deleted_count = await hook_data_manager.cleanup_old_executions(days=1)
        assert isinstance(deleted_count, int)
        assert deleted_count >= 0
        
        # Verify our recent execution still exists
        execution = await hook_data_manager.get_hook_execution(execution_id)
        assert execution is not None

    async def test_error_handling(self, hook_data_manager):
        """Test error handling in database operations."""
        # Test getting non-existent execution
        non_existent = await hook_data_manager.get_hook_execution("non-existent-id")
        assert non_existent is None
        
        # Test updating non-existent execution
        success = await hook_data_manager.update_hook_execution(
            execution_id="non-existent-id",
            status="SUCCESS"
        )
        assert success is False
        
        # Test invalid team configuration (should be handled by database constraints)
        with pytest.raises(Exception):
            await hook_data_manager.save_team_configuration(
                team_id="invalid_test",
                configuration={"invalid": "config"}  # Missing required fields
            )

    async def test_concurrent_operations(self, hook_data_manager):
        """Test concurrent database operations."""
        hook_id = f"concurrent_test_hook_{uuid.uuid4().hex[:8]}"
        
        # Create multiple executions concurrently
        async def create_execution(index):
            execution_id = await hook_data_manager.create_hook_execution(
                hook_id=hook_id,
                hook_type="StatusChangeHook",
                team_id="concurrent_test_team",
                event_type="jira:test_event",
                metadata={"index": index}
            )
            
            # Update execution
            await hook_data_manager.update_hook_execution(
                execution_id=execution_id,
                status="SUCCESS",
                execution_time_ms=100.0 + index
            )
            
            return execution_id
        
        # Run 10 concurrent operations
        tasks = [create_execution(i) for i in range(10)]
        execution_ids = await asyncio.gather(*tasks)
        
        assert len(execution_ids) == 10
        assert len(set(execution_ids)) == 10  # All unique
        
        # Verify all executions were created
        executions = await hook_data_manager.get_hook_executions(hook_id=hook_id)
        assert len(executions) == 10
        
        # Verify all have SUCCESS status
        success_count = len([e for e in executions if e["status"] == "SUCCESS"])
        assert success_count == 10


@pytest.mark.asyncio
class TestHookDataStorageIntegration:
    """Integration tests for hook data storage with real database operations."""

    async def test_full_integration_workflow(self):
        """Test complete integration workflow."""
        hook_data_manager = await get_hook_data_manager()
        
        # 1. Setup team configuration
        team_id = f"integration_team_{uuid.uuid4().hex[:8]}"
        config = {
            "team_name": "Integration Test Team",
            "default_channels": {"general": "#integration-test"},
            "rules": [{
                "rule_id": "integration_rule",
                "name": "Integration Test Rule",
                "description": "Test rule for integration",
                "hook_types": ["StatusChangeHook", "AssignmentHook"],
                "enabled": True,
                "priority": 10,
                "conditions": {"logic": "and", "conditions": []},
                "metadata": {"channels": ["#integration-test"]}
            }],
            "metadata": {}
        }
        
        await hook_data_manager.save_team_configuration(team_id, config)
        
        # 2. Create and execute hooks
        hook_executions = []
        for i in range(5):
            execution_id = await hook_data_manager.create_hook_execution(
                hook_id=f"integration_hook_{i}",
                hook_type="StatusChangeHook",
                team_id=team_id,
                event_type="jira:issue_updated",
                ticket_key=f"INT-{i}",
                metadata={"integration_test": True}
            )
            
            await hook_data_manager.update_hook_execution(
                execution_id=execution_id,
                status="SUCCESS",
                execution_time_ms=150.0 + i * 10,
                notification_sent=True,
                notification_result={"success": True}
            )
            
            hook_executions.append(execution_id)
        
        # 3. Verify data integrity
        saved_config = await hook_data_manager.get_team_configuration(team_id)
        assert saved_config["team_name"] == "Integration Test Team"
        
        executions = await hook_data_manager.get_hook_executions(team_id=team_id)
        assert len(executions) >= 5
        
        # 4. Generate performance metrics
        start_time = datetime.utcnow() - timedelta(minutes=5)
        end_time = datetime.utcnow() + timedelta(minutes=5)
        
        processed = await hook_data_manager.aggregate_performance_metrics(start_time, end_time)
        assert processed >= 0
        
        # 5. Get statistics
        stats = await hook_data_manager.get_execution_statistics(team_id=team_id)
        assert stats["total_executions"] >= 5
        assert stats["success_rate"] == 1.0  # All should be successful
        
        # 6. Health check
        health = await hook_data_manager.health_check()
        assert health["database_healthy"] is True


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])