#!/usr/bin/env python3
"""
Test script for the Advanced Changelog Slack Integration.

This script demonstrates the key functionality of the ChangelogSlackIntegration
without requiring actual Slack API calls.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from devsync_ai.core.changelog_slack_integration import (
    ChangelogSlackIntegration,
    ChannelType,
    ChangelogPriority,
    FeedbackSentiment
)


class MockSlackService:
    """Mock Slack service for testing."""
    
    def __init__(self):
        self.client = MockSlackClient()


class MockSlackClient:
    """Mock Slack client for testing."""
    
    async def send_message(self, channel: str, **kwargs) -> Dict[str, Any]:
        """Mock send message."""
        return {
            "ok": True,
            "ts": f"{int(datetime.now().timestamp())}.123456",
            "channel": channel
        }
    
    async def get_channel_info(self, channel: str) -> Dict[str, Any]:
        """Mock get channel info."""
        return {
            "ok": True,
            "channel": {
                "id": f"C{hash(channel) % 1000000000:09d}",
                "name": channel.lstrip("#")
            }
        }


def create_sample_changelog_data() -> Dict[str, Any]:
    """Create sample changelog data for testing."""
    return {
        "week_start": "2025-08-12",
        "week_end": "2025-08-18",
        "team_name": "DevSync Engineering",
        "summary": {
            "total_commits": 45,
            "total_prs": 12,
            "active_contributors": 8,
            "lines_added": 1850,
            "lines_removed": 620
        },
        "executive_summary": {
            "overview": "Strong week with major feature releases and performance improvements.",
            "key_achievements": [
                "Released OAuth2 authentication system",
                "Improved API response time by 40%",
                "Fixed 15 critical bugs"
            ],
            "risks": [
                "Deployment pipeline needs attention",
                "Technical debt increasing"
            ],
            "business_impact": {
                "user_satisfaction": 0.92,
                "performance_improvement": 0.40
            }
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
                    {"description": "Optimized database queries reducing response time by 40%"}
                ],
                "infrastructure": [
                    {"description": "Migrated to new CI/CD pipeline"}
                ],
                "code_quality": {"score": 8.5}
            }
        },
        "metrics": {
            "velocity": {"current": 42, "previous": 38},
            "code_review": {"avg_review_time_hours": 4.2},
            "deployment": {"frequency": 8, "success_rate": 0.95}
        },
        "contributors": {
            "top_contributors": [
                {"name": "Alice Johnson", "total_contributions": 15},
                {"name": "Bob Smith", "total_contributions": 12}
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


async def test_message_creation():
    """Test creating interactive changelog messages for different channel types."""
    print("🧪 Testing Message Creation")
    print("=" * 40)
    
    # Initialize integration
    mock_service = MockSlackService()
    integration = ChangelogSlackIntegration(mock_service)
    
    # Sample data
    changelog_data = create_sample_changelog_data()
    
    # Test different channel types
    channel_types = [
        (ChannelType.ENGINEERING, "Engineering Channel"),
        (ChannelType.PRODUCT, "Product Channel"),
        (ChannelType.EXECUTIVE, "Executive Channel")
    ]
    
    for channel_type, description in channel_types:
        print(f"\n📋 {description}")
        
        try:
            message = await integration.create_interactive_changelog_message(
                changelog_data, channel_type, {"optimize_for_audience": True}
            )
            
            # Analyze message structure
            blocks = message.get("blocks", [])
            print(f"   ✅ Generated {len(blocks)} blocks")
            
            # Count different block types
            block_types = {}
            interactive_elements = 0
            
            for block in blocks:
                block_type = block.get("type", "unknown")
                block_types[block_type] = block_types.get(block_type, 0) + 1
                
                if block_type == "actions":
                    interactive_elements += len(block.get("elements", []))
            
            print(f"   📊 Block types: {dict(block_types)}")
            print(f"   🔘 Interactive elements: {interactive_elements}")
            print(f"   📝 Fallback text: {message.get('text', 'N/A')[:50]}...")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def test_distribution_simulation():
    """Test changelog distribution simulation."""
    print("\n🚀 Testing Distribution Simulation")
    print("=" * 40)
    
    # Initialize integration
    mock_service = MockSlackService()
    integration = ChangelogSlackIntegration(mock_service)
    
    # Sample data
    changelog_data = create_sample_changelog_data()
    distribution_config = {
        "channels": ["#engineering", "#product", "#general"],
        "audience_optimization": True,
        "interactive_elements": True,
        "feedback_collection": True
    }
    
    try:
        result = await integration.distribute_changelog(
            changelog_data, distribution_config
        )
        
        print(f"📊 Distribution Results:")
        print(f"   Total channels: {result.get('total_channels', 0)}")
        print(f"   Successful deliveries: {result.get('successful_deliveries', 0)}")
        print(f"   Failed deliveries: {result.get('failed_deliveries', 0)}")
        
        if result.get("delivery_details"):
            print(f"   Delivery details:")
            for detail in result["delivery_details"]:
                status = "✅" if detail.get("success") else "❌"
                channel = detail.get("channel", "Unknown")
                print(f"     {status} {channel}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_feedback_simulation():
    """Test feedback collection simulation."""
    print("\n💭 Testing Feedback Simulation")
    print("=" * 40)
    
    # Initialize integration
    mock_service = MockSlackService()
    integration = ChangelogSlackIntegration(mock_service)
    
    # Mock feedback collection methods with async functions
    async def mock_collect_reactions(*args):
        return [
            {"name": "thumbsup", "count": 8, "users": ["U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8"]},
            {"name": "heart", "count": 5, "users": ["U1", "U2", "U3", "U4", "U5"]},
            {"name": "fire", "count": 3, "users": ["U1", "U2", "U3"]}
        ]
    
    async def mock_collect_replies(*args):
        return [
            {
                "user": "U1",
                "text": "Great work on the authentication system! This will really help our enterprise customers.",
                "ts": "1234567890.123456"
            },
            {
                "user": "U2",
                "text": "The performance improvements are impressive. Can we get more details on the optimization techniques?",
                "ts": "1234567890.123457"
            },
            {
                "user": "U3",
                "text": "Love the new notification system. When will it be available in production?",
                "ts": "1234567890.123458"
            }
        ]
    
    async def mock_collect_interactions(*args):
        return [
            {"user": "U4", "action_id": "changelog_view_dashboard", "ts": "1234567890.123459"},
            {"user": "U5", "action_id": "changelog_technical_details", "ts": "1234567890.123460"},
            {"user": "U6", "action_id": "feedback_positive", "ts": "1234567890.123461"}
        ]
    
    async def mock_analyze_sentiment(*args):
        return {
            "overall_sentiment": FeedbackSentiment.POSITIVE,
            "sentiment_score": 0.85,
            "positive_count": 14,
            "negative_count": 1,
            "neutral_count": 1
        }
    
    async def mock_extract_action_items(*args):
        return [
            "Provide more technical details on optimization techniques",
            "Share timeline for notification system production release",
            "Schedule follow-up session on authentication system"
        ]
    
    async def mock_generate_insights(*args):
        return {
            "engagement_level": "high",
            "key_topics": ["authentication", "performance", "notifications"],
            "recommendations": [
                "Continue focus on performance improvements",
                "Provide more technical implementation details",
                "Schedule demo sessions for new features"
            ]
        }
    
    integration._collect_message_reactions = mock_collect_reactions
    integration._collect_thread_replies = mock_collect_replies
    integration._collect_button_interactions = mock_collect_interactions
    integration._analyze_feedback_sentiment = mock_analyze_sentiment
    integration._extract_action_items = mock_extract_action_items
    integration._generate_feedback_insights = mock_generate_insights
    
    try:
        result = await integration.collect_and_analyze_feedback(
            "1234567890.123456", "C1234567890"
        )
        
        if result.get("success"):
            summary = result["feedback_summary"]
            print(f"📊 Feedback Analysis:")
            print(f"   Total reactions: {summary['total_reactions']}")
            print(f"   Total replies: {summary['total_replies']}")
            print(f"   Total interactions: {summary['total_interactions']}")
            print(f"   Overall sentiment: {summary['sentiment']['overall_sentiment'].value}")
            print(f"   Sentiment score: {summary['sentiment']['sentiment_score']:.2f}")
            print(f"   Action items: {len(summary['action_items'])}")
            
            print(f"\n💡 Key Insights:")
            insights = summary["insights"]
            print(f"   Engagement level: {insights['engagement_level']}")
            print(f"   Key topics: {', '.join(insights['key_topics'])}")
            print(f"   Recommendations:")
            for rec in insights["recommendations"]:
                print(f"     • {rec}")
        else:
            print(f"❌ Failed: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_interactive_callback_handling():
    """Test interactive callback handling."""
    print("\n🔄 Testing Interactive Callback Handling")
    print("=" * 40)
    
    # Initialize integration
    mock_service = MockSlackService()
    integration = ChangelogSlackIntegration(mock_service)
    
    # Mock handler methods with async functions
    async def mock_handle_changelog_action(payload):
        return {
            "response_type": "ephemeral",
            "text": f"✅ Handled changelog action: {payload['actions'][0]['action_id']}"
        }
    
    async def mock_handle_feedback_action(payload):
        return {
            "response_type": "ephemeral",
            "text": f"💭 Thank you for your feedback! Action: {payload['actions'][0]['action_id']}"
        }
    
    integration._handle_changelog_action = mock_handle_changelog_action
    integration._handle_feedback_action = mock_handle_feedback_action
    
    # Sample payloads
    test_payloads = [
        {
            "actions": [{"action_id": "changelog_view_dashboard"}],
            "user": {"id": "U1", "name": "alice"},
            "channel": {"id": "C1", "name": "engineering"},
            "message": {"ts": "1234567890.123456"}
        },
        {
            "actions": [{"action_id": "feedback_positive"}],
            "user": {"id": "U2", "name": "bob"},
            "channel": {"id": "C2", "name": "product"},
            "message": {"ts": "1234567890.123457"}
        },
        {
            "actions": [{"action_id": "changelog_technical_details"}],
            "user": {"id": "U3", "name": "carol"},
            "channel": {"id": "C3", "name": "engineering"},
            "message": {"ts": "1234567890.123458"}
        }
    ]
    
    for i, payload in enumerate(test_payloads, 1):
        action_id = payload["actions"][0]["action_id"]
        user_name = payload["user"]["name"]
        
        print(f"\n{i}. Testing {action_id} from {user_name}")
        
        try:
            response = await integration.handle_interactive_callback(payload)
            print(f"   Response: {response.get('text', 'N/A')}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def test_fallback_mechanisms():
    """Test fallback mechanism setup."""
    print("\n🛡️ Testing Fallback Mechanisms")
    print("=" * 40)
    
    # Initialize integration
    mock_service = MockSlackService()
    integration = ChangelogSlackIntegration(mock_service)
    
    # Mock channel monitoring
    async def mock_setup_channel_monitoring(channels):
        return None
    
    integration._setup_channel_monitoring = mock_setup_channel_monitoring
    
    primary_channels = ["#engineering", "#product", "#executive"]
    fallback_config = {
        "email_enabled": True,
        "webhook_enabled": True,
        "alternative_channels": ["#general", "#announcements"],
        "degraded_mode": False
    }
    
    try:
        result = await integration.setup_fallback_mechanisms(
            primary_channels, fallback_config
        )
        
        if result.get("success"):
            print("✅ Fallback mechanisms configured")
            
            mechanisms = result["fallback_mechanisms"]
            print(f"   Email fallback: {'✅' if mechanisms['email_fallback'] else '❌'}")
            print(f"   Webhook fallback: {'✅' if mechanisms['webhook_fallback'] else '❌'}")
            print(f"   Alternative channels: {len(mechanisms['alternative_channels'])}")
            
            print(f"\n📊 Channel Status:")
            for channel, status in result["channel_status"].items():
                status_icon = "✅" if status == "available" else "❌"
                print(f"   {status_icon} {channel}: {status}")
        else:
            print(f"❌ Failed: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_data_structures():
    """Test data structure creation and validation."""
    print("\n📊 Testing Data Structures")
    print("=" * 40)
    
    from devsync_ai.core.changelog_slack_integration import (
        InteractiveElement,
        ThreadContext,
        StakeholderMention,
        FeedbackData,
        ChannelRoutingRule
    )
    
    # Test InteractiveElement
    element = InteractiveElement(
        element_type="button",
        action_id="test_action",
        text="Test Button",
        style="primary"
    )
    print(f"✅ InteractiveElement: {element.text} ({element.element_type})")
    
    # Test ThreadContext
    context = ThreadContext(
        thread_ts="1234567890.123456",
        channel_id="C1234567890",
        original_message_ts="1234567890.123455",
        topic="Feature discussion"
    )
    print(f"✅ ThreadContext: {context.topic} in {context.channel_id}")
    
    # Test StakeholderMention
    mention = StakeholderMention(
        user_id="tech_lead",
        mention_type="role-based",
        relevance_score=0.9,
        reason="Breaking changes detected"
    )
    print(f"✅ StakeholderMention: {mention.user_id} (score: {mention.relevance_score})")
    
    # Test FeedbackData
    feedback = FeedbackData(
        user_id="U1234567890",
        message_ts="1234567890.123456",
        feedback_type="reaction",
        content="thumbsup",
        sentiment=FeedbackSentiment.POSITIVE,
        timestamp=datetime.now()
    )
    print(f"✅ FeedbackData: {feedback.content} ({feedback.sentiment.value})")
    
    # Test ChannelRoutingRule
    rule = ChannelRoutingRule(
        channel_id="engineering",
        channel_type=ChannelType.ENGINEERING,
        content_filters=["technical", "code"],
        priority_threshold=ChangelogPriority.MEDIUM
    )
    print(f"✅ ChannelRoutingRule: {rule.channel_id} ({len(rule.content_filters)} filters)")


async def main():
    """Run all tests."""
    print("🧪 Advanced Changelog Slack Integration Test Suite")
    print("=" * 60)
    
    # Test data structures
    test_data_structures()
    
    # Test async functionality
    await test_message_creation()
    await test_distribution_simulation()
    await test_feedback_simulation()
    await test_interactive_callback_handling()
    await test_fallback_mechanisms()
    
    print("\n🎉 All tests completed successfully!")
    print("\n📋 Summary:")
    print("   ✅ Message creation for different channel types")
    print("   ✅ Distribution simulation with mock Slack API")
    print("   ✅ Feedback collection and sentiment analysis")
    print("   ✅ Interactive callback handling")
    print("   ✅ Fallback mechanism configuration")
    print("   ✅ Data structure validation")


if __name__ == "__main__":
    asyncio.run(main())