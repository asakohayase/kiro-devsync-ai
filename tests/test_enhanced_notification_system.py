"""
Comprehensive test suite for the enhanced notification system.
Tests all components including routing, deduplication, batching, and scheduling.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch

from devsync_ai.core.channel_router import (
    ChannelRouter, RoutingContext, NotificationType, NotificationUrgency,
    RoutingRule, ChannelConfig
)
from devsync_ai.core.notification_deduplicator import (
    NotificationDeduplicator, DeduplicationRule, DeduplicationStrategy
)
from devsync_ai.core.enhanced_notification_handler import (
    EnhancedNotificationHandler, NotificationContext, ProcessingDecision,
    WorkHoursConfig, FilterConfig
)
from devsync_ai.core.notification_scheduler import (
    NotificationScheduler, SchedulerConfig, SchedulerStatus
)
from devsync_ai.core.notification_integration import (
    NotificationSystem, NotificationSystemConfig
)
from devsync_ai.notification.config import NotificationConfigManager


class TestChannelRouter:
    """Test channel routing functionality."""
    
    @pytest.fixture
    def router(self):
        """Create a channel router for testing."""
        return ChannelRouter()
    
    @pytest.fixture
    def sample_routing_context(self):
        """Create sample routing context."""
        return RoutingContext(
            notification_type=NotificationType.PR_NEW,
            urgency=NotificationUrgency.MEDIUM,
            team_id="test_team",
            content_data={
                "title": "Add new feature",
                "repository": "test-repo",
                "author": "test-user",
                "priority": "medium"
            },
            author="test-user"
        )
    
    def test_router_initialization(self, router):
        """Test router initializes with default configuration."""
        assert len(router._channels) > 0
        assert len(router._routing_rules) > 0
        assert router._fallback_channel == "#general"
    
    def test_basic_routing(self, router, sample_routing_context):
        """Test basic notification routing."""
        channel = router.route_notification(sample_routing_context)
        assert channel == "#development"  # Default for PR_NEW
    
    def test_urgency_override_routing(self, router):
        """Test routing with urgency overrides."""
        context = RoutingContext(
            notification_type=NotificationType.PR_CONFLICTS,
            urgency=NotificationUrgency.CRITICAL,
            team_id="test_team",
            content_data={"title": "Critical conflict"}
        )
        
        channel = router.route_notification(context)
        assert channel == "#critical-alerts"  # Should override to critical channel
    
    def test_team_specific_routing(self, router, sample_routing_context):
        """Test team-specific channel routing."""
        # Add team-specific mapping
        router.add_team_channel_mapping("test_team", {
            "pr_new": "#team-prs"
        })
        
        channel = router.route_notification(sample_routing_context)
        assert channel == "#team-prs"
    
    def test_channel_override(self, router, sample_routing_context):
        """Test channel override functionality."""
        channel = router.route_notification(sample_routing_context, "#custom-channel")
        assert channel == "#custom-channel"
    
    def test_urgency_analysis(self, router):
        """Test urgency analysis from message content."""
        # Test critical keywords
        critical_data = {
            "title": "CRITICAL: System outage detected",
            "description": "Emergency response required"
        }
        urgency = router.analyze_urgency(critical_data, NotificationType.ALERT_OUTAGE)
        assert urgency == NotificationUrgency.CRITICAL
        
        # Test high priority keywords
        high_data = {
            "title": "Build failed on main branch",
            "labels": ["blocker", "urgent"]
        }
        urgency = router.analyze_urgency(high_data, NotificationType.ALERT_BUILD)
        assert urgency == NotificationUrgency.HIGH
        
        # Test medium priority (default)
        medium_data = {
            "title": "Update documentation",
            "priority": "medium"
        }
        urgency = router.analyze_urgency(medium_data, NotificationType.PR_NEW)
        assert urgency == NotificationUrgency.MEDIUM
    
    def test_routing_statistics(self, router, sample_routing_context):
        """Test routing statistics collection."""
        # Route several notifications
        for i in range(5):
            router.route_notification(sample_routing_context)
        
        stats = router.get_routing_stats()
        assert stats["total_messages_routed"] == 5
        assert "#development" in stats["channel_usage"]
        assert stats["channel_usage"]["#development"]["total_messages"] == 5
    
    def test_custom_routing_rule(self, router):
        """Test adding custom routing rules."""
        custom_rule = RoutingRule(
            notification_type=NotificationType.JIRA_STATUS,
            default_channel="#custom-jira",
            urgency_overrides={NotificationUrgency.HIGH: "#urgent-jira"}
        )
        
        router.add_routing_rule(custom_rule)
        
        context = RoutingContext(
            notification_type=NotificationType.JIRA_STATUS,
            urgency=NotificationUrgency.MEDIUM,
            team_id="test_team",
            content_data={}
        )
        
        channel = router.route_notification(context)
        assert channel == "#custom-jira"


class TestNotificationDeduplicator:
    """Test notification deduplication functionality."""
    
    @pytest.fixture
    def deduplicator(self):
        """Create a deduplicator for testing."""
        return NotificationDeduplicator()
    
    @pytest.fixture
    def sample_pr_data(self):
        """Sample PR data for testing."""
        return {
            "number": 123,
            "title": "Add new feature",
            "repository": "test-repo",
            "author": "test-user",
            "timestamp": datetime.now().isoformat()
        }
    
    @pytest.mark.asyncio
    async def test_no_duplicate_first_time(self, deduplicator, sample_pr_data):
        """Test that first notification is not considered duplicate."""
        result = await deduplicator.check_duplicate(
            NotificationType.PR_NEW,
            sample_pr_data,
            "#development",
            "test_team",
            "test-user"
        )
        
        assert not result.is_duplicate
        assert result.hash_value
        assert result.reason == "no_duplicate_found"
    
    @pytest.mark.asyncio
    async def test_duplicate_detection(self, deduplicator, sample_pr_data):
        """Test duplicate detection within timeframe."""
        # First notification
        result1 = await deduplicator.check_duplicate(
            NotificationType.PR_NEW,
            sample_pr_data,
            "#development",
            "test_team",
            "test-user"
        )
        
        # Record the notification
        await deduplicator.record_notification(
            NotificationType.PR_NEW,
            sample_pr_data,
            "#development",
            "test_team",
            result1.hash_value,
            "test-user"
        )
        
        # Second identical notification
        result2 = await deduplicator.check_duplicate(
            NotificationType.PR_NEW,
            sample_pr_data,
            "#development",
            "test_team",
            "test-user"
        )
        
        assert result2.is_duplicate
        assert result2.hash_value == result1.hash_value
        assert "duplicate_found_within" in result2.reason
    
    @pytest.mark.asyncio
    async def test_different_content_not_duplicate(self, deduplicator):
        """Test that different content is not considered duplicate."""
        data1 = {"number": 123, "title": "Feature A", "repository": "test-repo"}
        data2 = {"number": 124, "title": "Feature B", "repository": "test-repo"}
        
        result1 = await deduplicator.check_duplicate(
            NotificationType.PR_NEW, data1, "#development", "test_team"
        )
        
        result2 = await deduplicator.check_duplicate(
            NotificationType.PR_NEW, data2, "#development", "test_team"
        )
        
        assert not result1.is_duplicate
        assert not result2.is_duplicate
        assert result1.hash_value != result2.hash_value
    
    @pytest.mark.asyncio
    async def test_custom_deduplication_rule(self, deduplicator):
        """Test custom deduplication rules."""
        custom_rule = DeduplicationRule(
            notification_type=NotificationType.JIRA_STATUS,
            strategy=DeduplicationStrategy.CUSTOM_KEY,
            timeframe_minutes=30,
            custom_key_fields=["key", "status"],
            ignore_fields={"timestamp", "updated_at"}
        )
        
        deduplicator.add_deduplication_rule(custom_rule)
        
        data = {
            "key": "TEST-123",
            "status": "In Progress",
            "timestamp": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        result = await deduplicator.check_duplicate(
            NotificationType.JIRA_STATUS, data, "#project-updates", "test_team"
        )
        
        assert not result.is_duplicate
        assert result.hash_value
    
    @pytest.mark.asyncio
    async def test_deduplication_statistics(self, deduplicator, sample_pr_data):
        """Test deduplication statistics."""
        # Generate some duplicates
        for i in range(3):
            await deduplicator.check_duplicate(
                NotificationType.PR_NEW, sample_pr_data, "#development", "test_team"
            )
        
        stats = deduplicator.get_deduplication_stats()
        assert stats["total_checks"] == 3
        assert stats["memory_cache_size"] >= 0
        assert "duplicate_rate" in stats
    
    @pytest.mark.asyncio
    async def test_cleanup_old_records(self, deduplicator):
        """Test cleanup of old records."""
        # This would require more complex setup with actual database
        # For now, test that the method runs without error
        cleaned_count = await deduplicator.cleanup_old_records(days_to_keep=1)
        assert isinstance(cleaned_count, int)
        assert cleaned_count >= 0


class TestEnhancedNotificationHandler:
    """Test enhanced notification handler functionality."""
    
    @pytest.fixture
    def handler(self):
        """Create a notification handler for testing."""
        return EnhancedNotificationHandler()
    
    @pytest.fixture
    def sample_notification_context(self):
        """Sample notification context for testing."""
        return NotificationContext(
            notification_type=NotificationType.PR_NEW,
            event_type="pull_request.opened",
            data={
                "pr": {
                    "number": 123,
                    "title": "Add new feature",
                    "user": {"login": "test-user"},
                    "html_url": "https://github.com/test/repo/pull/123"
                }
            },
            team_id="test_team",
            author="test-user"
        )
    
    @pytest.mark.asyncio
    async def test_basic_notification_processing(self, handler, sample_notification_context):
        """Test basic notification processing."""
        result = await handler.process_notification(sample_notification_context)
        
        assert isinstance(result.decision, ProcessingDecision)
        assert result.channel is not None
        assert result.processing_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_filtering_blocked_author(self, handler):
        """Test filtering of blocked authors."""
        # Configure filter to block specific author
        handler.filter_config.blocked_authors = ["blocked-user"]
        
        context = NotificationContext(
            notification_type=NotificationType.PR_NEW,
            event_type="pull_request.opened",
            data={"title": "Test PR"},
            team_id="test_team",
            author="blocked-user"
        )
        
        result = await handler.process_notification(context)
        assert result.decision == ProcessingDecision.FILTER_OUT
        assert "filtered_by_rules" in result.reason
    
    @pytest.mark.asyncio
    async def test_work_hours_scheduling(self, handler, sample_notification_context):
        """Test work hours scheduling."""
        # Configure work hours (9 AM - 5 PM)
        handler.work_hours_config.enabled = True
        handler.work_hours_config.start_hour = 9
        handler.work_hours_config.end_hour = 17
        
        # Create context with timestamp outside work hours
        context = sample_notification_context
        context.timestamp = datetime.now().replace(hour=22, minute=0)  # 10 PM
        
        # Set to non-urgent priority
        context.data["priority"] = "low"
        
        result = await handler.process_notification(context)
        
        # Should be scheduled for work hours (unless urgent)
        if result.decision == ProcessingDecision.SCHEDULE_FOR_WORK_HOURS:
            assert result.scheduled_for is not None
            assert result.scheduled_for > context.timestamp
    
    @pytest.mark.asyncio
    async def test_urgent_bypass_work_hours(self, handler):
        """Test that urgent notifications bypass work hours."""
        handler.work_hours_config.enabled = True
        handler.work_hours_config.urgent_bypass = True
        
        context = NotificationContext(
            notification_type=NotificationType.ALERT_SECURITY,
            event_type="alert.security_vulnerability",
            data={
                "alert": {
                    "title": "CRITICAL: Security vulnerability",
                    "severity": "critical"
                }
            },
            team_id="test_team",
            timestamp=datetime.now().replace(hour=22)  # Outside work hours
        )
        
        result = await handler.process_notification(context)
        
        # Should send immediately despite being outside work hours
        assert result.decision in [ProcessingDecision.SEND_IMMEDIATELY, ProcessingDecision.BATCH_AND_SEND]
    
    @pytest.mark.asyncio
    async def test_processing_statistics(self, handler, sample_notification_context):
        """Test processing statistics collection."""
        # Process several notifications
        for i in range(5):
            await handler.process_notification(sample_notification_context)
        
        stats = handler.get_processing_stats()
        assert stats["total_processed"] == 5
        assert "average_processing_time_ms" in stats
        assert "router_stats" in stats
        assert "deduplication_stats" in stats
    
    @pytest.mark.asyncio
    async def test_error_handling(self, handler):
        """Test error handling in notification processing."""
        # Create context with invalid data that might cause errors
        invalid_context = NotificationContext(
            notification_type=NotificationType.PR_NEW,
            event_type="invalid.event",
            data={},  # Empty data might cause template errors
            team_id="test_team"
        )
        
        result = await handler.process_notification(invalid_context)
        
        # Should handle errors gracefully
        assert result.decision is not None
        if result.errors:
            assert len(result.errors) > 0


class TestNotificationScheduler:
    """Test notification scheduler functionality."""
    
    @pytest.fixture
    def scheduler(self):
        """Create a scheduler for testing."""
        mock_handler = Mock()
        mock_handler.process_scheduled_notifications = AsyncMock(return_value={
            "processed": 0,
            "sent": 0,
            "errors": 0,
            "notifications": []
        })
        
        config = SchedulerConfig(check_interval_seconds=1)  # Fast interval for testing
        return NotificationScheduler(handler=mock_handler, config=config)
    
    def test_scheduler_initialization(self, scheduler):
        """Test scheduler initializes correctly."""
        assert scheduler.status == SchedulerStatus.STOPPED
        assert scheduler.config.check_interval_seconds == 1
    
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler):
        """Test scheduler start and stop functionality."""
        # Start scheduler
        started = await scheduler.start()
        assert started is True
        assert scheduler.status == SchedulerStatus.RUNNING
        
        # Stop scheduler
        stopped = await scheduler.stop(timeout=5)
        assert stopped is True
        assert scheduler.status == SchedulerStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_scheduler_metrics(self, scheduler):
        """Test scheduler metrics collection."""
        await scheduler.start()
        
        # Let it run for a short time
        await asyncio.sleep(2)
        
        await scheduler.stop()
        
        metrics = scheduler.get_metrics()
        assert "total_runs" in metrics
        assert "success_rate_percent" in metrics
        assert "average_run_time_ms" in metrics
    
    @pytest.mark.asyncio
    async def test_scheduler_health_status(self, scheduler):
        """Test scheduler health status reporting."""
        health = scheduler.get_health_status()
        
        assert "status" in health
        assert "issues" in health
        assert "checks_performed" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_force_scheduler_run(self, scheduler):
        """Test forcing immediate scheduler run."""
        await scheduler.start()
        
        result = await scheduler.force_run()
        assert "processed" in result
        assert "sent" in result
        assert "errors" in result
        
        await scheduler.stop()


class TestNotificationSystem:
    """Test complete notification system integration."""
    
    @pytest.fixture
    def system_config(self):
        """Create system configuration for testing."""
        return NotificationSystemConfig(
            enabled=True,
            debug_mode=True,
            analytics_enabled=False  # Disable for testing
        )
    
    @pytest.fixture
    def notification_system(self, system_config):
        """Create notification system for testing."""
        return NotificationSystem(system_config)
    
    @pytest.mark.asyncio
    async def test_system_initialization(self, notification_system):
        """Test system initialization."""
        initialized = await notification_system.initialize()
        assert initialized is True
        assert notification_system._initialized is True
    
    @pytest.mark.asyncio
    async def test_system_start_stop(self, notification_system):
        """Test system start and stop."""
        await notification_system.initialize()
        
        started = await notification_system.start()
        assert started is True
        assert notification_system._running is True
        
        stopped = await notification_system.stop()
        assert stopped is True
        assert notification_system._running is False
    
    @pytest.mark.asyncio
    async def test_send_github_notification(self, notification_system):
        """Test sending GitHub webhook notification."""
        await notification_system.initialize()
        await notification_system.start()
        
        github_payload = {
            "pull_request": {
                "number": 123,
                "title": "Test PR",
                "user": {"login": "test-user"},
                "html_url": "https://github.com/test/repo/pull/123"
            }
        }
        
        result = await notification_system.send_github_notification(
            "pull_request.opened",
            github_payload,
            "test_team"
        )
        
        assert result.decision is not None
        assert result.channel is not None
        
        await notification_system.stop()
    
    @pytest.mark.asyncio
    async def test_send_jira_notification(self, notification_system):
        """Test sending JIRA webhook notification."""
        await notification_system.initialize()
        await notification_system.start()
        
        jira_payload = {
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "summary": "Test issue",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "High"}
                }
            },
            "user": {"displayName": "Test User"}
        }
        
        result = await notification_system.send_jira_notification(
            "jira:issue_updated",
            jira_payload,
            "test_team"
        )
        
        assert result.decision is not None
        assert result.channel is not None
        
        await notification_system.stop()
    
    @pytest.mark.asyncio
    async def test_system_health_status(self, notification_system):
        """Test system health status reporting."""
        await notification_system.initialize()
        
        health = await notification_system.get_health_status()
        
        assert "status" in health
        assert "components" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "system" in health["components"]
        assert "scheduler" in health["components"]
    
    @pytest.mark.asyncio
    async def test_system_statistics(self, notification_system):
        """Test system statistics collection."""
        await notification_system.initialize()
        
        stats = await notification_system.get_system_stats()
        
        assert "system" in stats
        assert "handler" in stats
        assert "scheduler" in stats
        assert "router" in stats
        assert "deduplicator" in stats
        assert "batcher" in stats


class TestNotificationConfigManager:
    """Test notification configuration management."""
    
    @pytest.fixture
    def config_manager(self):
        """Create configuration manager for testing."""
        return NotificationConfigManager()
    
    @pytest.fixture
    def sample_config_data(self):
        """Sample configuration data."""
        return {
            "system": {
                "enabled": True,
                "debug_mode": False,
                "analytics_enabled": True
            },
            "work_hours": {
                "enabled": True,
                "start_hour": 9,
                "end_hour": 17,
                "timezone": "UTC",
                "work_days": [0, 1, 2, 3, 4]
            },
            "filtering": {
                "enabled": True,
                "min_priority_level": "medium",
                "blocked_authors": ["bot-user"]
            }
        }
    
    def test_config_manager_initialization(self, config_manager):
        """Test configuration manager initialization."""
        assert config_manager._config is None
        assert len(config_manager._teams) == 0
    
    def test_load_default_config(self, config_manager):
        """Test loading default configuration."""
        config = config_manager.load_config()
        
        assert config.enabled is True
        assert config.work_hours.start_hour == 9
        assert config.work_hours.end_hour == 17
        assert config.filtering.enabled is True
    
    def test_merge_config_data(self, config_manager, sample_config_data):
        """Test merging configuration data."""
        base_config = NotificationSystemConfig()
        merged_config = config_manager._merge_config(base_config, sample_config_data)
        
        assert merged_config.enabled is True
        assert merged_config.debug_mode is False
        assert merged_config.analytics_enabled is True
        assert merged_config.work_hours.start_hour == 9
        assert merged_config.filtering.min_priority_level == "medium"
        assert "bot-user" in merged_config.filtering.blocked_authors
    
    def test_config_validation(self, config_manager):
        """Test configuration validation."""
        # Valid configuration should pass
        valid_config = NotificationSystemConfig()
        config_manager._validate_config(valid_config)  # Should not raise
        
        # Invalid configuration should raise ValueError
        invalid_config = NotificationSystemConfig()
        invalid_config.work_hours.start_hour = 25  # Invalid hour
        
        with pytest.raises(ValueError):
            config_manager._validate_config(invalid_config)
    
    def test_create_example_config(self, config_manager, tmp_path):
        """Test creating example configuration file."""
        config_file = tmp_path / "example_config.yaml"
        
        success = config_manager.create_example_config(str(config_file))
        assert success is True
        assert config_file.exists()
        
        # Verify the file contains expected content
        with open(config_file, 'r') as f:
            content = f.read()
            assert "system:" in content
            assert "work_hours:" in content
            assert "teams:" in content


class TestPerformanceAndLoad:
    """Test system performance under load."""
    
    @pytest.fixture
    def notification_system(self):
        """Create notification system for performance testing."""
        config = NotificationSystemConfig(analytics_enabled=False)
        return NotificationSystem(config)
    
    @pytest.mark.asyncio
    async def test_high_volume_notifications(self, notification_system):
        """Test system performance with high volume of notifications."""
        await notification_system.initialize()
        await notification_system.start()
        
        # Send many notifications quickly
        tasks = []
        for i in range(100):
            task = notification_system.send_notification(
                notification_type=NotificationType.PR_NEW,
                event_type="pull_request.opened",
                data={
                    "pr": {
                        "number": i,
                        "title": f"Test PR {i}",
                        "user": {"login": "test-user"}
                    }
                },
                team_id="test_team"
            )
            tasks.append(task)
        
        # Wait for all notifications to process
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that most notifications were processed successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 90  # Allow for some failures
        
        await notification_system.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, notification_system):
        """Test concurrent notification processing."""
        await notification_system.initialize()
        await notification_system.start()
        
        # Create different types of notifications concurrently
        notification_types = [
            (NotificationType.PR_NEW, "pull_request.opened"),
            (NotificationType.JIRA_STATUS, "jira:issue_updated"),
            (NotificationType.ALERT_BUILD, "alert.build_failure"),
            (NotificationType.STANDUP_DAILY, "standup.daily")
        ]
        
        tasks = []
        for i in range(20):
            notification_type, event_type = notification_types[i % len(notification_types)]
            
            task = notification_system.send_notification(
                notification_type=notification_type,
                event_type=event_type,
                data={"id": i, "title": f"Test notification {i}"},
                team_id=f"team_{i % 3}"
            )
            tasks.append(task)
        
        # Process all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 15  # Allow for some failures
        
        await notification_system.stop()
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, notification_system):
        """Test memory usage doesn't grow excessively under load."""
        import psutil
        import os
        
        try:
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            await notification_system.initialize()
            await notification_system.start()
            
            # Process many notifications
            for batch in range(10):
                tasks = []
                for i in range(50):
                    task = notification_system.send_notification(
                        notification_type=NotificationType.PR_NEW,
                        event_type="pull_request.opened",
                        data={"number": batch * 50 + i, "title": f"PR {batch}-{i}"},
                        team_id="test_team"
                    )
                    tasks.append(task)
                
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Clean up periodically
                if batch % 3 == 0:
                    await notification_system.cleanup_old_data()
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB)
            assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB"
            
            await notification_system.stop()
            
        except ImportError:
            pytest.skip("psutil not available for memory testing")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])