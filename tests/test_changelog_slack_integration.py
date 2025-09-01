"""
Tests for the Advanced Changelog Slack Integration.

This module provides comprehensive tests for the ChangelogSlackIntegration class,
including interactive elements, thread management, feedback collection, and fallback mechanisms.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from devsync_ai.core.changelog_slack_integration import (
    ChangelogSlackIntegration,
    ChangelogPriority,
    FeedbackSentiment,
    ChannelType,
    InteractiveElement,
    ThreadContext,
    StakeholderMention,
    FeedbackData,
    ChannelRoutingRule
)


class TestChangelogSlackIntegration:
    """Test suite for ChangelogSlackIntegration."""
    
    @pytest.fixture
    def mock_slack_service(self):
        """Create a mock Slack service."""
        service = MagicMock()
        service.client = AsyncMock()
        return service
    
    @pytest.fixture
    def changelog_integration(self, mock_slack_service):
        """Create a ChangelogSlackIntegration instance."""
        return ChangelogSlackIntegration(mock_slack_service)
    
    @pytest.fixture
    def sample_changelog_data(self):
        """Sample changelog data for testing."""
        return {
            "week_start": "2025-08-12",
            "week_end": "2025-08-18",
            "team_name": "DevSync Team",
            "summary": {
                "total_commits": 45,
                "total_prs": 12,
                "active_contributors": 8
            },
            "executive_summary": {
                "overview": "Strong week with major feature releases and performance improvements.",
                "key_achievements": [
                    "Released user authentication system",
                    "Improved API response time by 40%",
                    "Fixed 15 critical bugs"
                ],
                "risks": [
                    "Deployment pipeline needs attention",
                    "Technical debt increasing"
                ]
            },
            "sections": {
                "features": [
                    {
                        "title": "OAuth2 Authentication",
                        "description": "Complete OAuth2 implementation with Google and GitHub",
                        "impact_score": 9,
                        "pr_numbers": ["#123", "#124"]
                    },
                    {
                        "title": "Real-time Notifications",
                        "description": "WebSocket-based notification system",
                        "impact_score": 7,
                        "pr_numbers": ["#125"]
                    }
                ],
                "bug_fixes": [
                    {
                        "title": "Fixed memory leak in data processor",
                        "severity": "critical",
                        "pr_numbers": ["#126"]
                    },
                    {
                        "title": "Resolved UI rendering issues",
                        "severity": "medium",
                        "pr_numbers": ["#127"]
                    }
                ],
                "technical": {
                    "performance": [
                        {
                            "description": "Optimized database queries reducing response time by 40%"
                        }
                    ],
                    "infrastructure": [
                        {
                            "description": "Migrated to new CI/CD pipeline"
                        }
                    ],
                    "code_quality": {
                        "score": 8.5
                    }
                }
            },
            "metrics": {
                "velocity": {
                    "current": 42,
                    "previous": 38
                },
                "code_review": {
                    "avg_review_time_hours": 4.2
                },
                "deployment": {
                    "frequency": 8,
                    "success_rate": 0.95
                }
            },
            "contributors": {
                "top_contributors": [
                    {
                        "name": "Alice Johnson",
                        "total_contributions": 15
                    },
                    {
                        "name": "Bob Smith",
                        "total_contributions": 12
                    }
                ],
                "special_recognitions": [
                    {
                        "name": "Carol Davis",
                        "achievement": "Outstanding code review participation"
                    }
                ]
            },
            "dashboard_url": "https://dashboard.example.com/changelog/2025-08-12"
        }
    
    @pytest.fixture
    def sample_distribution_config(self):
        """Sample distribution configuration."""
        return {
            "channels": ["#engineering", "#product", "#general"],
            "audience_optimization": True,
            "interactive_elements": True,
            "feedback_collection": True,
            "mention_targeting": True
        }
    
    @pytest.mark.asyncio
    async def test_distribute_changelog_success(self, changelog_integration, sample_changelog_data, sample_distribution_config):
        """Test successful changelog distribution."""
        # Mock successful API responses
        changelog_integration.client.send_message = AsyncMock(return_value={
            "ok": True,
            "ts": "1234567890.123456"
        })
        changelog_integration.client.get_channel_info = AsyncMock(return_value={
            "ok": True,
            "channel": {"id": "C1234567890", "name": "engineering"}
        })
        
        # Mock internal methods
        changelog_integration._determine_target_channels = AsyncMock(return_value=[
            {"id": "#engineering", "type": ChannelType.ENGINEERING, "priority": ChangelogPriority.MEDIUM, "stakeholders": []},
            {"id": "#product", "type": ChannelType.PRODUCT, "priority": ChangelogPriority.MEDIUM, "stakeholders": []}
        ])
        changelog_integration._initialize_engagement_tracking = AsyncMock()
        
        result = await changelog_integration.distribute_changelog(
            sample_changelog_data, sample_distribution_config
        )
        
        assert result["total_channels"] == 2
        assert result["successful_deliveries"] == 2
        assert result["failed_deliveries"] == 0
        assert len(result["delivery_details"]) == 2
    
    @pytest.mark.asyncio
    async def test_distribute_changelog_partial_failure(self, changelog_integration, sample_changelog_data, sample_distribution_config):
        """Test changelog distribution with partial failures."""
        # Mock mixed API responses
        def mock_send_message(channel, **kwargs):
            if channel == "#engineering":
                return {"ok": True, "ts": "1234567890.123456"}
            else:
                return {"ok": False, "error": "channel_not_found"}
        
        changelog_integration.client.send_message = AsyncMock(side_effect=mock_send_message)
        changelog_integration._determine_target_channels = AsyncMock(return_value=[
            {"id": "#engineering", "type": ChannelType.ENGINEERING, "priority": ChangelogPriority.MEDIUM, "stakeholders": []},
            {"id": "#nonexistent", "type": ChannelType.GENERAL, "priority": ChangelogPriority.MEDIUM, "stakeholders": []}
        ])
        changelog_integration._initialize_engagement_tracking = AsyncMock()
        
        result = await changelog_integration.distribute_changelog(
            sample_changelog_data, sample_distribution_config
        )
        
        assert result["total_channels"] == 2
        assert result["successful_deliveries"] == 1
        assert result["failed_deliveries"] == 1
    
    @pytest.mark.asyncio
    async def test_create_interactive_changelog_message_engineering(self, changelog_integration, sample_changelog_data):
        """Test creating interactive message for engineering channel."""
        # Mock internal methods
        changelog_integration._generate_intelligent_mentions = AsyncMock(return_value=[
            StakeholderMention(
                user_id="tech_lead",
                mention_type="role-based",
                relevance_score=0.9,
                reason="Breaking changes require review"
            )
        ])
        
        message = await changelog_integration.create_interactive_changelog_message(
            sample_changelog_data,
            ChannelType.ENGINEERING,
            {"technical_details": True}
        )
        
        assert "blocks" in message
        assert "text" in message
        assert len(message["blocks"]) > 0
        
        # Check for header block
        header_block = next((block for block in message["blocks"] if block["type"] == "header"), None)
        assert header_block is not None
        assert "Weekly Changelog" in header_block["text"]["text"]
        
        # Check for interactive elements
        action_blocks = [block for block in message["blocks"] if block["type"] == "actions"]
        assert len(action_blocks) > 0
    
    @pytest.mark.asyncio
    async def test_create_interactive_changelog_message_executive(self, changelog_integration, sample_changelog_data):
        """Test creating interactive message for executive channel."""
        changelog_integration._generate_intelligent_mentions = AsyncMock(return_value=[])
        
        message = await changelog_integration.create_interactive_changelog_message(
            sample_changelog_data,
            ChannelType.EXECUTIVE,
            {"executive_summary": True}
        )
        
        assert "blocks" in message
        
        # Check for executive summary
        summary_blocks = [
            block for block in message["blocks"] 
            if block["type"] == "section" and "Executive Summary" in block.get("text", {}).get("text", "")
        ]
        assert len(summary_blocks) > 0
    
    @pytest.mark.asyncio
    async def test_manage_changelog_thread_create(self, changelog_integration):
        """Test creating a discussion thread."""
        changelog_integration._create_discussion_thread = AsyncMock(return_value={
            "success": True,
            "thread_ts": "1234567890.123456",
            "participants": []
        })
        
        result = await changelog_integration.manage_changelog_thread(
            "1234567890.123456",
            "C1234567890",
            "create",
            {"topic": "Feature discussion"}
        )
        
        assert result["success"] is True
        assert "thread_ts" in result
    
    @pytest.mark.asyncio
    async def test_manage_changelog_thread_invalid_action(self, changelog_integration):
        """Test thread management with invalid action."""
        result = await changelog_integration.manage_changelog_thread(
            "1234567890.123456",
            "C1234567890",
            "invalid_action"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_collect_and_analyze_feedback_success(self, changelog_integration):
        """Test successful feedback collection and analysis."""
        # Mock feedback collection methods
        changelog_integration._collect_message_reactions = AsyncMock(return_value=[
            {"name": "thumbsup", "count": 5, "users": ["U1", "U2", "U3", "U4", "U5"]},
            {"name": "heart", "count": 3, "users": ["U1", "U2", "U3"]}
        ])
        
        changelog_integration._collect_thread_replies = AsyncMock(return_value=[
            {
                "user": "U1",
                "text": "Great work on the authentication system!",
                "ts": "1234567890.123456"
            },
            {
                "user": "U2", 
                "text": "The performance improvements are impressive.",
                "ts": "1234567890.123457"
            }
        ])
        
        changelog_integration._collect_button_interactions = AsyncMock(return_value=[
            {
                "user": "U3",
                "action_id": "changelog_view_dashboard",
                "ts": "1234567890.123458"
            }
        ])
        
        changelog_integration._analyze_feedback_sentiment = AsyncMock(return_value={
            "overall_sentiment": FeedbackSentiment.POSITIVE,
            "sentiment_score": 0.8,
            "positive_count": 8,
            "negative_count": 0,
            "neutral_count": 2
        })
        
        changelog_integration._extract_action_items = AsyncMock(return_value=[
            "Follow up on deployment pipeline improvements",
            "Schedule technical debt review"
        ])
        
        changelog_integration._generate_feedback_insights = AsyncMock(return_value={
            "engagement_level": "high",
            "key_topics": ["authentication", "performance"],
            "recommendations": ["Continue focus on performance", "Address technical debt"]
        })
        
        result = await changelog_integration.collect_and_analyze_feedback(
            "1234567890.123456",
            "C1234567890"
        )
        
        assert result["success"] is True
        assert "feedback_summary" in result
        assert result["feedback_summary"]["total_reactions"] == 2
        assert result["feedback_summary"]["total_replies"] == 2
        assert result["feedback_summary"]["total_interactions"] == 1
        assert result["feedback_summary"]["sentiment"]["overall_sentiment"] == FeedbackSentiment.POSITIVE
        assert len(result["feedback_summary"]["action_items"]) == 2
    
    @pytest.mark.asyncio
    async def test_collect_and_analyze_feedback_error(self, changelog_integration):
        """Test feedback collection with error."""
        changelog_integration._collect_message_reactions = AsyncMock(side_effect=Exception("API Error"))
        
        result = await changelog_integration.collect_and_analyze_feedback(
            "1234567890.123456",
            "C1234567890"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_handle_interactive_callback_changelog_action(self, changelog_integration):
        """Test handling changelog-specific interactive callbacks."""
        payload = {
            "actions": [{"action_id": "changelog_view_dashboard"}],
            "user": {"id": "U1234567890"},
            "channel": {"id": "C1234567890"},
            "message": {"ts": "1234567890.123456"}
        }
        
        changelog_integration._handle_changelog_action = AsyncMock(return_value={
            "response_type": "ephemeral",
            "text": "Opening dashboard..."
        })
        
        result = await changelog_integration.handle_interactive_callback(payload)
        
        assert result["response_type"] == "ephemeral"
        assert "dashboard" in result["text"].lower()
    
    @pytest.mark.asyncio
    async def test_handle_interactive_callback_feedback_action(self, changelog_integration):
        """Test handling feedback interactive callbacks."""
        payload = {
            "actions": [{"action_id": "feedback_positive"}],
            "user": {"id": "U1234567890"},
            "channel": {"id": "C1234567890"},
            "message": {"ts": "1234567890.123456"}
        }
        
        changelog_integration._handle_feedback_action = AsyncMock(return_value={
            "response_type": "ephemeral",
            "text": "Thank you for your feedback!"
        })
        
        result = await changelog_integration.handle_interactive_callback(payload)
        
        assert result["response_type"] == "ephemeral"
        assert "feedback" in result["text"].lower()
    
    @pytest.mark.asyncio
    async def test_handle_interactive_callback_error(self, changelog_integration):
        """Test handling interactive callback with error."""
        payload = {
            "actions": [{"action_id": "changelog_view_dashboard"}],
            "user": {"id": "U1234567890"},
            "channel": {"id": "C1234567890"},
            "message": {"ts": "1234567890.123456"}
        }
        
        changelog_integration._handle_changelog_action = AsyncMock(side_effect=Exception("Processing error"))
        
        result = await changelog_integration.handle_interactive_callback(payload)
        
        assert result["response_type"] == "ephemeral"
        assert "Error processing" in result["text"]
    
    @pytest.mark.asyncio
    async def test_setup_fallback_mechanisms_success(self, changelog_integration):
        """Test successful fallback mechanism setup."""
        primary_channels = ["#engineering", "#product"]
        fallback_config = {
            "email_enabled": True,
            "webhook_enabled": True,
            "alternative_channels": ["#general"],
            "degraded_mode": False
        }
        
        changelog_integration.client.get_channel_info = AsyncMock(return_value={
            "ok": True,
            "channel": {"id": "C1234567890", "name": "engineering"}
        })
        changelog_integration._setup_channel_monitoring = AsyncMock()
        
        result = await changelog_integration.setup_fallback_mechanisms(
            primary_channels, fallback_config
        )
        
        assert result["success"] is True
        assert "fallback_mechanisms" in result
        assert result["fallback_mechanisms"]["email_fallback"] is True
        assert result["fallback_mechanisms"]["webhook_fallback"] is True
        assert len(result["channel_status"]) == 2
        assert all(status == "available" for status in result["channel_status"].values())
    
    @pytest.mark.asyncio
    async def test_setup_fallback_mechanisms_channel_unavailable(self, changelog_integration):
        """Test fallback setup with unavailable channels."""
        primary_channels = ["#engineering", "#nonexistent"]
        fallback_config = {
            "email_enabled": True,
            "alternative_channels": ["#general"]
        }
        
        def mock_get_channel_info(channel):
            if channel == "#engineering":
                return {"ok": True, "channel": {"id": "C1234567890", "name": "engineering"}}
            else:
                raise Exception("channel_not_found")
        
        changelog_integration.client.get_channel_info = AsyncMock(side_effect=mock_get_channel_info)
        changelog_integration._setup_channel_monitoring = AsyncMock()
        
        result = await changelog_integration.setup_fallback_mechanisms(
            primary_channels, fallback_config
        )
        
        assert result["success"] is True
        assert result["channel_status"]["#engineering"] == "available"
        assert "unavailable" in result["channel_status"]["#nonexistent"]
    
    def test_initialize_default_routing_rules(self, changelog_integration):
        """Test initialization of default routing rules."""
        assert len(changelog_integration.routing_rules) > 0
        
        # Check for engineering rule
        engineering_rule = next(
            (rule for rule in changelog_integration.routing_rules 
             if rule.channel_type == ChannelType.ENGINEERING), None
        )
        assert engineering_rule is not None
        assert "technical" in engineering_rule.content_filters
        
        # Check for product rule
        product_rule = next(
            (rule for rule in changelog_integration.routing_rules 
             if rule.channel_type == ChannelType.PRODUCT), None
        )
        assert product_rule is not None
        assert "feature" in product_rule.content_filters
    
    def test_initialize_feedback_handlers(self, changelog_integration):
        """Test initialization of feedback handlers."""
        assert len(changelog_integration.feedback_handlers) > 0
        assert "positive_reaction" in changelog_integration.feedback_handlers
        assert "negative_reaction" in changelog_integration.feedback_handlers
        assert callable(changelog_integration.feedback_handlers["positive_reaction"])
    
    def test_generate_fallback_text(self, changelog_integration, sample_changelog_data):
        """Test fallback text generation."""
        fallback_text = changelog_integration._generate_fallback_text(sample_changelog_data)
        
        assert "Weekly Changelog" in fallback_text
        assert "DevSync Team" in fallback_text
        assert "2025-08-12" in fallback_text
        assert "45 commits" in fallback_text
        assert "12 PRs" in fallback_text
    
    @pytest.mark.asyncio
    async def test_add_interactive_header(self, changelog_integration, sample_changelog_data):
        """Test adding interactive header to message."""
        message = {"blocks": []}
        
        await changelog_integration._add_interactive_header(
            message, sample_changelog_data, ChannelType.ENGINEERING
        )
        
        assert len(message["blocks"]) >= 2
        
        # Check header block
        header_block = message["blocks"][0]
        assert header_block["type"] == "header"
        assert "Weekly Changelog" in header_block["text"]["text"]
        
        # Check stats section
        stats_block = message["blocks"][1]
        assert stats_block["type"] == "section"
        assert "45 commits" in stats_block["text"]["text"]
        assert "accessory" in stats_block  # Dashboard button
    
    @pytest.mark.asyncio
    async def test_add_executive_summary(self, changelog_integration, sample_changelog_data):
        """Test adding executive summary section."""
        message = {"blocks": []}
        
        await changelog_integration._add_executive_summary(message, sample_changelog_data)
        
        # Should add divider and summary section
        assert len(message["blocks"]) >= 2
        
        # Check for divider
        divider_block = message["blocks"][0]
        assert divider_block["type"] == "divider"
        
        # Check for summary content
        summary_block = message["blocks"][1]
        assert summary_block["type"] == "section"
        assert "Executive Summary" in summary_block["text"]["text"]
        assert "Strong week" in summary_block["text"]["text"]
    
    @pytest.mark.asyncio
    async def test_add_features_section(self, changelog_integration):
        """Test adding features section."""
        message = {"blocks": []}
        features = [
            {
                "title": "OAuth2 Authentication",
                "description": "Complete OAuth2 implementation",
                "impact_score": 9
            },
            {
                "title": "Real-time Notifications", 
                "description": "WebSocket-based notifications",
                "impact_score": 7
            }
        ]
        
        await changelog_integration._add_features_section(message, features)
        
        assert len(message["blocks"]) >= 1
        
        features_block = message["blocks"][0]
        assert features_block["type"] == "section"
        assert "New Features" in features_block["text"]["text"]
        assert "OAuth2 Authentication" in features_block["text"]["text"]
        assert "🔥" in features_block["text"]["text"]  # High impact emoji
    
    @pytest.mark.asyncio
    async def test_add_features_section_many_features(self, changelog_integration):
        """Test adding features section with many features."""
        message = {"blocks": []}
        features = [{"title": f"Feature {i}", "impact_score": 5} for i in range(10)]
        
        await changelog_integration._add_features_section(message, features)
        
        # Should limit to 5 features and add "View All" button
        assert len(message["blocks"]) >= 2
        
        # Check for "View All" button
        action_block = message["blocks"][1]
        assert action_block["type"] == "actions"
        assert "View All 10 Features" in action_block["elements"][0]["text"]["text"]
    
    @pytest.mark.asyncio
    async def test_add_metrics_section(self, changelog_integration, sample_changelog_data):
        """Test adding metrics section."""
        message = {"blocks": []}
        
        await changelog_integration._add_metrics_section(
            message, sample_changelog_data, ChannelType.ENGINEERING
        )
        
        assert len(message["blocks"]) >= 2
        
        # Check for divider
        divider_block = message["blocks"][0]
        assert divider_block["type"] == "divider"
        
        # Check metrics content
        metrics_block = message["blocks"][1]
        assert metrics_block["type"] == "section"
        assert "Team Metrics" in metrics_block["text"]["text"]
        assert "42 SP" in metrics_block["text"]["text"]  # Velocity
        assert "4.2h" in metrics_block["text"]["text"]  # Review time
        assert "accessory" in metrics_block  # Detailed metrics button
    
    @pytest.mark.asyncio
    async def test_add_contributor_section(self, changelog_integration, sample_changelog_data):
        """Test adding contributor recognition section."""
        message = {"blocks": []}
        
        await changelog_integration._add_contributor_section(message, sample_changelog_data)
        
        assert len(message["blocks"]) >= 3  # Divider + top contributors + special recognition
        
        # Check for divider
        divider_block = message["blocks"][0]
        assert divider_block["type"] == "divider"
        
        # Check top contributors
        contributors_block = message["blocks"][1]
        assert contributors_block["type"] == "section"
        assert "Top Contributors" in contributors_block["text"]["text"]
        assert "Alice Johnson" in contributors_block["text"]["text"]
        assert "🥇" in contributors_block["text"]["text"]  # Gold medal for #1
        
        # Check special recognition
        recognition_block = message["blocks"][2]
        assert recognition_block["type"] == "section"
        assert "Special Recognition" in recognition_block["text"]["text"]
        assert "Carol Davis" in recognition_block["text"]["text"]
    
    @pytest.mark.asyncio
    async def test_add_interactive_actions_engineering(self, changelog_integration, sample_changelog_data):
        """Test adding interactive actions for engineering channel."""
        message = {"blocks": []}
        
        await changelog_integration._add_interactive_actions(
            message, sample_changelog_data, ChannelType.ENGINEERING
        )
        
        assert len(message["blocks"]) >= 3  # Divider + primary actions + secondary actions
        
        # Check for engineering-specific button
        primary_actions = message["blocks"][1]
        assert primary_actions["type"] == "actions"
        
        # Look for technical details button
        technical_button = next(
            (element for element in primary_actions["elements"] 
             if "Technical Details" in element["text"]["text"]), None
        )
        assert technical_button is not None
    
    @pytest.mark.asyncio
    async def test_add_interactive_actions_executive(self, changelog_integration, sample_changelog_data):
        """Test adding interactive actions for executive channel."""
        message = {"blocks": []}
        
        await changelog_integration._add_interactive_actions(
            message, sample_changelog_data, ChannelType.EXECUTIVE
        )
        
        # Check for executive-specific button
        primary_actions = message["blocks"][1]
        business_button = next(
            (element for element in primary_actions["elements"] 
             if "Business Impact" in element["text"]["text"]), None
        )
        assert business_button is not None
    
    @pytest.mark.asyncio
    async def test_add_feedback_elements(self, changelog_integration, sample_changelog_data):
        """Test adding feedback collection elements."""
        message = {"blocks": []}
        
        await changelog_integration._add_feedback_elements(message, sample_changelog_data)
        
        assert len(message["blocks"]) >= 2  # Feedback text + feedback buttons
        
        # Check feedback text
        feedback_text_block = message["blocks"][0]
        assert feedback_text_block["type"] == "section"
        assert "Your Feedback Matters" in feedback_text_block["text"]["text"]
        
        # Check feedback buttons
        feedback_actions = message["blocks"][1]
        assert feedback_actions["type"] == "actions"
        assert len(feedback_actions["elements"]) == 3  # Helpful, Not Helpful, Suggest
        
        # Check button action IDs
        action_ids = [element["action_id"] for element in feedback_actions["elements"]]
        assert "feedback_positive" in action_ids
        assert "feedback_negative" in action_ids
        assert "feedback_suggestion" in action_ids


class TestDataClasses:
    """Test the data classes used in the integration."""
    
    def test_interactive_element_creation(self):
        """Test InteractiveElement creation."""
        element = InteractiveElement(
            element_type="button",
            action_id="test_action",
            text="Test Button",
            value="test_value",
            style="primary"
        )
        
        assert element.element_type == "button"
        assert element.action_id == "test_action"
        assert element.text == "Test Button"
        assert element.value == "test_value"
        assert element.style == "primary"
        assert element.emoji is True  # Default value
    
    def test_thread_context_creation(self):
        """Test ThreadContext creation."""
        context = ThreadContext(
            thread_ts="1234567890.123456",
            channel_id="C1234567890",
            original_message_ts="1234567890.123455",
            participants=["U1", "U2"],
            topic="Feature discussion"
        )
        
        assert context.thread_ts == "1234567890.123456"
        assert context.channel_id == "C1234567890"
        assert len(context.participants) == 2
        assert context.topic == "Feature discussion"
        assert context.is_resolved is False  # Default value
    
    def test_stakeholder_mention_creation(self):
        """Test StakeholderMention creation."""
        mention = StakeholderMention(
            user_id="tech_lead",
            mention_type="role-based",
            relevance_score=0.9,
            reason="Breaking changes detected",
            context="breaking_changes"
        )
        
        assert mention.user_id == "tech_lead"
        assert mention.mention_type == "role-based"
        assert mention.relevance_score == 0.9
        assert mention.reason == "Breaking changes detected"
        assert mention.context == "breaking_changes"
    
    def test_feedback_data_creation(self):
        """Test FeedbackData creation."""
        feedback = FeedbackData(
            user_id="U1234567890",
            message_ts="1234567890.123456",
            feedback_type="reaction",
            content="thumbsup",
            sentiment=FeedbackSentiment.POSITIVE,
            timestamp=datetime.now(),
            action_items=["Follow up on feature"],
            metadata={"reaction_count": 5}
        )
        
        assert feedback.user_id == "U1234567890"
        assert feedback.feedback_type == "reaction"
        assert feedback.sentiment == FeedbackSentiment.POSITIVE
        assert len(feedback.action_items) == 1
        assert feedback.metadata["reaction_count"] == 5
    
    def test_channel_routing_rule_creation(self):
        """Test ChannelRoutingRule creation."""
        rule = ChannelRoutingRule(
            channel_id="engineering",
            channel_type=ChannelType.ENGINEERING,
            content_filters=["technical", "code"],
            priority_threshold=ChangelogPriority.MEDIUM,
            stakeholder_groups=["developers", "tech_leads"]
        )
        
        assert rule.channel_id == "engineering"
        assert rule.channel_type == ChannelType.ENGINEERING
        assert len(rule.content_filters) == 2
        assert rule.priority_threshold == ChangelogPriority.MEDIUM
        assert len(rule.stakeholder_groups) == 2


class TestEnums:
    """Test the enums used in the integration."""
    
    def test_changelog_priority_enum(self):
        """Test ChangelogPriority enum."""
        assert ChangelogPriority.LOW.value == "low"
        assert ChangelogPriority.MEDIUM.value == "medium"
        assert ChangelogPriority.HIGH.value == "high"
        assert ChangelogPriority.CRITICAL.value == "critical"
    
    def test_feedback_sentiment_enum(self):
        """Test FeedbackSentiment enum."""
        assert FeedbackSentiment.POSITIVE.value == "positive"
        assert FeedbackSentiment.NEUTRAL.value == "neutral"
        assert FeedbackSentiment.NEGATIVE.value == "negative"
        assert FeedbackSentiment.MIXED.value == "mixed"
    
    def test_channel_type_enum(self):
        """Test ChannelType enum."""
        assert ChannelType.ENGINEERING.value == "engineering"
        assert ChannelType.PRODUCT.value == "product"
        assert ChannelType.EXECUTIVE.value == "executive"
        assert ChannelType.GENERAL.value == "general"
        assert ChannelType.ANNOUNCEMENTS.value == "announcements"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])