"""
Simple tests for notification system components without complex dependencies.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

# Test the core components individually
from devsync_ai.core.channel_router import (
    ChannelRouter, RoutingContext, NotificationType, NotificationUrgency
)


class TestChannelRouterBasic:
    """Basic tests for channel router without external dependencies."""
    
    def test_router_initialization(self):
        """Test router initializes with default configuration."""
        router = ChannelRouter()
        
        # Should have default channels
        assert len(router._channels) > 0
        assert "#general" in router._channels
        assert "#development" in router._channels
        assert "#project-updates" in router._channels
        
        # Should have routing rules
        assert len(router._routing_rules) > 0
        assert NotificationType.PR_NEW in router._routing_rules
        assert NotificationType.JIRA_STATUS in router._routing_rules
        
        # Should have fallback channel
        assert router._fallback_channel == "#general"
    
    def test_basic_routing_rules(self):
        """Test basic routing rules work correctly."""
        router = ChannelRouter()
        
        # Test PR routing
        pr_context = RoutingContext(
            notification_type=NotificationType.PR_NEW,
            urgency=NotificationUrgency.MEDIUM,
            team_id="test_team",
            content_data={"title": "Test PR"}
        )
        
        channel = router.route_notification(pr_context)
        assert channel == "#development"
        
        # Test JIRA routing
        jira_context = RoutingContext(
            notification_type=NotificationType.JIRA_STATUS,
            urgency=NotificationUrgency.MEDIUM,
            team_id="test_team",
            content_data={"key": "TEST-123"}
        )
        
        channel = router.route_notification(jira_context)
        assert channel == "#project-updates"
        
        # Test alert routing
        alert_context = RoutingContext(
            notification_type=NotificationType.ALERT_SECURITY,
            urgency=NotificationUrgency.CRITICAL,
            team_id="test_team",
            content_data={"title": "Security alert"}
        )
        
        channel = router.route_notification(alert_context)
        assert channel == "#critical-alerts"
    
    def test_urgency_analysis(self):
        """Test urgency analysis from content."""
        router = ChannelRouter()
        
        # Test critical keywords
        critical_data = {
            "title": "CRITICAL: Database outage",
            "description": "Emergency response needed"
        }
        urgency = router.analyze_urgency(critical_data, NotificationType.ALERT_OUTAGE)
        assert urgency == NotificationUrgency.CRITICAL
        
        # Test high priority keywords
        high_data = {
            "title": "Build failed on main",
            "labels": ["blocker"]
        }
        urgency = router.analyze_urgency(high_data, NotificationType.ALERT_BUILD)
        assert urgency == NotificationUrgency.HIGH
        
        # Test priority field
        priority_data = {
            "title": "Regular update",
            "priority": "high"
        }
        urgency = router.analyze_urgency(priority_data, NotificationType.PR_NEW)
        assert urgency == NotificationUrgency.HIGH
        
        # Test default medium
        normal_data = {
            "title": "Update documentation"
        }
        urgency = router.analyze_urgency(normal_data, NotificationType.PR_NEW)
        assert urgency == NotificationUrgency.MEDIUM
    
    def test_team_specific_routing(self):
        """Test team-specific channel mappings."""
        router = ChannelRouter()
        
        # Add team mapping
        router.add_team_channel_mapping("frontend_team", {
            "pr_new": "#frontend-prs",
            "jira_status": "#frontend-tickets"
        })
        
        # Test team-specific routing
        context = RoutingContext(
            notification_type=NotificationType.PR_NEW,
            urgency=NotificationUrgency.MEDIUM,
            team_id="frontend_team",
            content_data={"title": "Frontend PR"}
        )
        
        channel = router.route_notification(context)
        assert channel == "#frontend-prs"
        
        # Test different team uses default
        context.team_id = "backend_team"
        channel = router.route_notification(context)
        assert channel == "#development"  # Default for PR_NEW
    
    def test_channel_override(self):
        """Test channel override functionality."""
        router = ChannelRouter()
        
        context = RoutingContext(
            notification_type=NotificationType.PR_NEW,
            urgency=NotificationUrgency.MEDIUM,
            team_id="test_team",
            content_data={"title": "Test PR"}
        )
        
        # Test override with existing channel
        channel = router.route_notification(context, "#general")
        assert channel == "#general"
        
        # Test that invalid override falls back to routing rules
        channel = router.route_notification(context, "#invalid-channel")
        assert channel == "#development"  # Should fall back to default routing
    
    def test_routing_statistics(self):
        """Test routing statistics collection."""
        router = ChannelRouter()
        
        context = RoutingContext(
            notification_type=NotificationType.PR_NEW,
            urgency=NotificationUrgency.MEDIUM,
            team_id="test_team",
            content_data={"title": "Test PR"}
        )
        
        # Route several notifications
        for i in range(3):
            router.route_notification(context)
        
        stats = router.get_routing_stats()
        assert stats["total_messages_routed"] == 3
        assert "#development" in stats["channel_usage"]
        assert stats["channel_usage"]["#development"]["total_messages"] == 3


class TestNotificationTypes:
    """Test notification type enums and mappings."""
    
    def test_notification_types_exist(self):
        """Test that all expected notification types exist."""
        expected_types = [
            "pr_new", "pr_ready", "pr_approved", "pr_conflicts", "pr_merged", "pr_closed",
            "jira_status", "jira_priority", "jira_assignment", "jira_comment", "jira_blocker", "jira_sprint",
            "alert_build", "alert_deployment", "alert_security", "alert_outage", "alert_bug",
            "standup_daily", "standup_summary"
        ]
        
        for type_str in expected_types:
            # Should be able to create NotificationType from string
            notification_type = NotificationType(type_str)
            assert notification_type.value == type_str
    
    def test_urgency_levels(self):
        """Test urgency level enum."""
        urgencies = ["critical", "high", "medium", "low"]
        
        for urgency_str in urgencies:
            urgency = NotificationUrgency(urgency_str)
            assert urgency.value == urgency_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])