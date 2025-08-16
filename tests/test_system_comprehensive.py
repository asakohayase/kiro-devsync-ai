"""
Comprehensive system tests for the enhanced notification system.
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

from devsync_ai.core.channel_router import (
    ChannelRouter, RoutingContext, NotificationType, NotificationUrgency
)
from devsync_ai.templates.pr_templates import NewPRTemplate
from devsync_ai.templates.jira_templates import StatusChangeTemplate
from devsync_ai.templates.alert_templates import BuildFailureTemplate
from devsync_ai.templates.standup_template import StandupTemplate
from devsync_ai.core.template_factory import MessageTemplateFactory, TemplateConfig
from devsync_ai.core.smart_message_batcher import SmartMessageBatcher, BatchableMessage, ContentType


class TestSystemComprehensive:
    """Comprehensive system tests."""
    
    def test_core_components_initialization(self):
        """Test that all core components can be initialized."""
        # Channel Router
        router = ChannelRouter()
        assert router is not None
        
        # Template Factory
        factory = MessageTemplateFactory()
        assert factory is not None
        
        # Message Batcher
        batcher = SmartMessageBatcher()
        assert batcher is not None
        
        # Template Config
        config = TemplateConfig(team_id="test_team")
        assert config is not None
    
    def test_template_system_functionality(self):
        """Test template system functionality."""
        # Test PR Template
        pr_template = NewPRTemplate()
        pr_data = {
            "pr": {
                "number": 123,
                "title": "Test PR",
                "user": {"login": "test-user"},
                "html_url": "https://github.com/test/repo/pull/123",
                "draft": False,
                "mergeable": True
            }
        }
        
        pr_message = pr_template.format_message(pr_data)
        assert pr_message is not None
        assert pr_message.blocks is not None
        assert len(pr_message.blocks) > 0
        
        # Test JIRA Template
        jira_template = StatusChangeTemplate()
        jira_data = {
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "summary": "Test issue",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "High"}
                }
            },
            "changelog": {
                "items": [{
                    "field": "status",
                    "fromString": "To Do",
                    "toString": "In Progress"
                }]
            }
        }
        
        jira_message = jira_template.format_message(jira_data)
        assert jira_message is not None
        assert jira_message.blocks is not None
        assert len(jira_message.blocks) > 0
        
        # Test Alert Template
        alert_template = BuildFailureTemplate()
        alert_data = {
            "alert": {
                "title": "Build Failed",
                "severity": "high",
                "timestamp": datetime.now().isoformat(),
                "description": "Build failed on main branch"
            },
            "build": {
                "branch": "main",
                "commit": "abc123",
                "job_name": "CI Pipeline"
            }
        }
        
        alert_message = alert_template.format_message(alert_data)
        assert alert_message is not None
        assert alert_message.blocks is not None
        assert len(alert_message.blocks) > 0
        
        # Test Standup Template
        standup_template = StandupTemplate()
        standup_data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "team": "Development Team",
            "team_members": [
                {
                    "name": "Alice",
                    "yesterday": ["Completed feature A"],
                    "today": ["Working on feature B"],
                    "blockers": []
                },
                {
                    "name": "Bob", 
                    "yesterday": ["Fixed bug #123"],
                    "today": ["Code review"],
                    "blockers": ["Waiting for API access"]
                }
            ]
        }
        
        standup_message = standup_template.format_message(standup_data)
        assert standup_message is not None
        assert standup_message.blocks is not None
        assert len(standup_message.blocks) > 0
    
    def test_channel_routing_functionality(self):
        """Test channel routing functionality."""
        router = ChannelRouter()
        
        # Test PR routing
        pr_context = RoutingContext(
            notification_type=NotificationType.PR_NEW,
            urgency=NotificationUrgency.MEDIUM,
            team_id="test_team",
            content_data={"title": "Test PR"}
        )
        
        channel = router.route_notification(pr_context)
        assert channel is not None
        assert isinstance(channel, str)
        assert channel.startswith("#")
        
        # Test JIRA routing
        jira_context = RoutingContext(
            notification_type=NotificationType.JIRA_STATUS,
            urgency=NotificationUrgency.HIGH,
            team_id="test_team",
            content_data={"key": "TEST-123"}
        )
        
        channel = router.route_notification(jira_context)
        assert channel is not None
        assert isinstance(channel, str)
        assert channel.startswith("#")
        
        # Test urgency analysis
        critical_data = {
            "title": "CRITICAL: System outage",
            "severity": "critical"
        }
        
        urgency = router.analyze_urgency(critical_data, NotificationType.ALERT_OUTAGE)
        assert urgency == NotificationUrgency.CRITICAL
    
    def test_message_batching_functionality(self):
        """Test message batching functionality."""
        batcher = SmartMessageBatcher()
        
        # Test adding messages
        message1 = BatchableMessage(
            id="msg_1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="test_user",
            priority="medium",
            data={"title": "PR 1"}
        )
        
        message2 = BatchableMessage(
            id="msg_2", 
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="test_user",
            priority="medium",
            data={"title": "PR 2"}
        )
        
        result1 = batcher.add_message(message1, "test_channel")
        result2 = batcher.add_message(message2, "test_channel")
        
        # Should batch similar messages
        assert result1.should_batch or result2.should_batch
        
        # Test getting pending batches
        pending = batcher.get_pending_batches()
        assert isinstance(pending, dict)
        
        # Test activity metrics
        metrics = batcher.get_activity_metrics()
        assert "total_messages" in metrics
        assert "channels_active" in metrics
    
    def test_template_configuration_system(self):
        """Test template configuration system."""
        config = TemplateConfig(
            team_id="test_team",
            branding={
                "team_name": "Test Team",
                "logo_url": "https://example.com/logo.png"
            },
            color_scheme={
                "primary": "#007bff",
                "success": "#28a745",
                "warning": "#ffc107",
                "danger": "#dc3545"
            },
            interactive_elements=True,
            accessibility_mode=False
        )
        
        assert config.team_id == "test_team"
        assert config.branding["team_name"] == "Test Team"
        assert config.color_scheme["primary"] == "#007bff"
        assert config.interactive_elements is True
        assert config.accessibility_mode is False
    
    def test_error_handling_robustness(self):
        """Test error handling across components."""
        # Test template with missing data
        pr_template = NewPRTemplate()
        
        # Should handle missing data gracefully
        try:
            message = pr_template.format_message({})
            # Should not crash, might return fallback message
            assert message is not None
        except Exception as e:
            # If it throws, should be a specific template error
            assert "required" in str(e).lower() or "missing" in str(e).lower()
        
        # Test router with invalid data
        router = ChannelRouter()
        
        try:
            context = RoutingContext(
                notification_type=NotificationType.PR_NEW,
                urgency=NotificationUrgency.MEDIUM,
                team_id="",  # Empty team ID
                content_data={}
            )
            channel = router.route_notification(context)
            # Should return a default channel
            assert channel is not None
        except Exception:
            # Should handle gracefully
            pass
        
        # Test batcher with invalid message
        batcher = SmartMessageBatcher()
        
        try:
            invalid_message = BatchableMessage(
                id="",  # Empty ID
                content_type=ContentType.PR_UPDATE,
                timestamp=datetime.now(),
                author="",
                priority="invalid_priority",
                data={}
            )
            result = batcher.add_message(invalid_message, "test_channel")
            # Should handle gracefully
            assert result is not None
        except Exception:
            # Should handle validation errors
            pass
    
    def test_performance_characteristics(self):
        """Test basic performance characteristics."""
        import time
        
        # Test template rendering performance
        pr_template = NewPRTemplate()
        pr_data = {
            "pr": {
                "number": 123,
                "title": "Test PR",
                "user": {"login": "test-user"},
                "html_url": "https://github.com/test/repo/pull/123"
            }
        }
        
        start_time = time.time()
        for _ in range(100):
            message = pr_template.format_message(pr_data)
        end_time = time.time()
        
        # Should render 100 messages in reasonable time (< 1 second)
        assert (end_time - start_time) < 1.0
        
        # Test routing performance
        router = ChannelRouter()
        context = RoutingContext(
            notification_type=NotificationType.PR_NEW,
            urgency=NotificationUrgency.MEDIUM,
            team_id="test_team",
            content_data={"title": "Test PR"}
        )
        
        start_time = time.time()
        for _ in range(1000):
            channel = router.route_notification(context)
        end_time = time.time()
        
        # Should route 1000 notifications in reasonable time (< 1 second)
        assert (end_time - start_time) < 1.0
    
    def test_integration_workflow(self):
        """Test end-to-end integration workflow."""
        # Initialize components
        router = ChannelRouter()
        batcher = SmartMessageBatcher()
        pr_template = NewPRTemplate()
        
        # Simulate PR notification workflow
        pr_data = {
            "pr": {
                "number": 123,
                "title": "Add new feature",
                "user": {"login": "developer"},
                "html_url": "https://github.com/test/repo/pull/123",
                "draft": False
            }
        }
        
        # 1. Route the notification
        context = RoutingContext(
            notification_type=NotificationType.PR_NEW,
            urgency=NotificationUrgency.MEDIUM,
            team_id="dev_team",
            content_data=pr_data["pr"]
        )
        
        channel = router.route_notification(context)
        assert channel is not None
        
        # 2. Format the message
        message = pr_template.format_message(pr_data)
        assert message is not None
        assert message.blocks is not None
        
        # 3. Add to batcher
        batchable_message = BatchableMessage(
            id="pr_123",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="developer",
            priority="medium",
            data=pr_data["pr"]
        )
        
        batch_result = batcher.add_message(batchable_message, channel)
        assert batch_result is not None
        
        # 4. Verify the workflow completed
        stats = batcher.get_activity_metrics()
        assert stats["total_messages"] >= 1
        
        routing_stats = router.get_routing_statistics()
        assert routing_stats["total_routed"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])