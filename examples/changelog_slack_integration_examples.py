"""
Examples demonstrating the Advanced Changelog Slack Integration.

This module provides comprehensive examples of how to use the ChangelogSlackIntegration
for distributing weekly changelogs with interactive elements, thread management,
feedback collection, and intelligent channel routing.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

from devsync_ai.services.slack import SlackService
from devsync_ai.core.changelog_slack_integration import (
    ChangelogSlackIntegration,
    ChannelType,
    ChangelogPriority,
    FeedbackSentiment
)


async def example_basic_changelog_distribution():
    """
    Example: Basic changelog distribution to multiple channels.
    """
    print("🚀 Example: Basic Changelog Distribution")
    print("=" * 50)
    
    # Initialize Slack service
    slack_service = SlackService()
    
    if not slack_service.client:
        print("❌ Slack not configured - skipping example")
        return
    
    # Sample changelog data
    changelog_data = {
        "week_start": "2025-08-12",
        "week_end": "2025-08-18",
        "team_name": "DevSync Engineering",
        "summary": {
            "total_commits": 67,
            "total_prs": 15,
            "active_contributors": 9,
            "lines_added": 2340,
            "lines_removed": 890
        },
        "executive_summary": {
            "overview": "Exceptional week with major authentication system launch and significant performance improvements.",
            "key_achievements": [
                "Successfully launched OAuth2 authentication system",
                "Improved API response times by 45%",
                "Resolved 18 critical bugs",
                "Completed security audit with zero findings"
            ],
            "risks": [
                "Database migration scheduled for next week",
                "Technical debt in legacy modules increasing"
            ],
            "business_impact": {
                "user_satisfaction": 0.92,
                "performance_improvement": 0.45,
                "security_score": 0.98
            }
        },
        "sections": {
            "features": [
                {
                    "title": "OAuth2 Authentication System",
                    "description": "Complete OAuth2 implementation with Google, GitHub, and Microsoft providers",
                    "impact_score": 9,
                    "pr_numbers": ["#234", "#235", "#236"],
                    "contributors": ["alice", "bob"],
                    "business_value": "Enables enterprise SSO integration"
                },
                {
                    "title": "Real-time Notification Engine",
                    "description": "WebSocket-based notification system with offline support",
                    "impact_score": 8,
                    "pr_numbers": ["#237", "#238"],
                    "contributors": ["carol", "dave"],
                    "business_value": "Improves user engagement by 30%"
                },
                {
                    "title": "Advanced Search Functionality",
                    "description": "Elasticsearch-powered search with faceted filtering",
                    "impact_score": 7,
                    "pr_numbers": ["#239"],
                    "contributors": ["eve"],
                    "business_value": "Reduces user search time by 60%"
                }
            ],
            "bug_fixes": [
                {
                    "title": "Fixed critical memory leak in data processor",
                    "severity": "critical",
                    "pr_numbers": ["#240"],
                    "impact": "Prevents server crashes under high load"
                },
                {
                    "title": "Resolved race condition in user session management",
                    "severity": "high",
                    "pr_numbers": ["#241"],
                    "impact": "Eliminates duplicate login issues"
                },
                {
                    "title": "Fixed UI rendering issues on mobile devices",
                    "severity": "medium",
                    "pr_numbers": ["#242", "#243"],
                    "impact": "Improves mobile user experience"
                }
            ],
            "technical": {
                "performance": [
                    {
                        "description": "Optimized database queries reducing response time by 45%",
                        "metrics": {"before": "850ms", "after": "467ms"}
                    },
                    {
                        "description": "Implemented Redis caching for frequently accessed data",
                        "metrics": {"cache_hit_rate": "89%"}
                    }
                ],
                "infrastructure": [
                    {
                        "description": "Migrated to Kubernetes for better scalability",
                        "impact": "Supports 10x traffic increase"
                    },
                    {
                        "description": "Implemented automated backup system",
                        "impact": "99.9% data durability guarantee"
                    }
                ],
                "code_quality": {
                    "score": 8.7,
                    "test_coverage": 0.94,
                    "technical_debt_hours": 23,
                    "code_duplication": 0.03
                }
            }
        },
        "metrics": {
            "velocity": {
                "current": 48,
                "previous": 42,
                "trend": "increasing"
            },
            "code_review": {
                "avg_review_time_hours": 3.8,
                "approval_rate": 0.96,
                "participation_rate": 0.89
            },
            "deployment": {
                "frequency": 12,
                "success_rate": 0.97,
                "rollback_rate": 0.03,
                "avg_deployment_time": "8.5 minutes"
            },
            "quality": {
                "bug_discovery_rate": 0.12,
                "customer_satisfaction": 0.91,
                "performance_score": 0.88
            }
        },
        "contributors": {
            "top_contributors": [
                {
                    "name": "Alice Johnson",
                    "total_contributions": 18,
                    "commits": 12,
                    "prs": 4,
                    "reviews": 8,
                    "expertise": ["authentication", "security"]
                },
                {
                    "name": "Bob Smith",
                    "total_contributions": 15,
                    "commits": 10,
                    "prs": 3,
                    "reviews": 6,
                    "expertise": ["backend", "performance"]
                },
                {
                    "name": "Carol Davis",
                    "total_contributions": 13,
                    "commits": 8,
                    "prs": 2,
                    "reviews": 9,
                    "expertise": ["frontend", "ux"]
                }
            ],
            "special_recognitions": [
                {
                    "name": "Alice Johnson",
                    "achievement": "Security Champion - Led OAuth2 implementation",
                    "impact": "Enabled enterprise customer onboarding"
                },
                {
                    "name": "Dave Wilson",
                    "achievement": "Performance Hero - 45% response time improvement",
                    "impact": "Significantly improved user experience"
                }
            ],
            "team_growth": {
                "new_contributors": 2,
                "skill_development": [
                    "3 team members completed Kubernetes certification",
                    "2 team members advanced in security practices"
                ]
            }
        },
        "dashboard_url": "https://dashboard.devsync.ai/changelog/2025-08-12",
        "repository_urls": [
            "https://github.com/company/main-app",
            "https://github.com/company/api-service"
        ]
    }
    
    # Distribution configuration
    distribution_config = {
        "channels": ["#engineering", "#product", "#general"],
        "audience_optimization": True,
        "interactive_elements": True,
        "feedback_collection": True,
        "mention_targeting": True,
        "fallback_enabled": True
    }
    
    try:
        # Distribute changelog
        result = await slack_service.send_changelog_notification(
            changelog_data, distribution_config
        )
        
        print(f"📊 Distribution Results:")
        print(f"   Total channels: {result.get('total_channels', 0)}")
        print(f"   Successful: {result.get('successful_deliveries', 0)}")
        print(f"   Failed: {result.get('failed_deliveries', 0)}")
        
        if result.get("delivery_details"):
            print(f"   Delivery details:")
            for detail in result["delivery_details"]:
                status = "✅" if detail.get("success") else "❌"
                print(f"     {status} {detail.get('channel', 'Unknown')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def example_channel_specific_optimization():
    """
    Example: Channel-specific content optimization.
    """
    print("\n🎯 Example: Channel-Specific Optimization")
    print("=" * 50)
    
    slack_service = SlackService()
    
    if not slack_service.changelog_integration:
        print("❌ Changelog integration not available")
        return
    
    # Sample changelog data (simplified)
    changelog_data = {
        "week_start": "2025-08-12",
        "week_end": "2025-08-18",
        "team_name": "DevSync Team",
        "summary": {"total_commits": 45, "total_prs": 12, "active_contributors": 8},
        "executive_summary": {
            "overview": "Strong performance with key feature releases",
            "key_achievements": ["OAuth2 launch", "Performance improvements"],
            "business_impact": {"user_satisfaction": 0.92}
        },
        "sections": {
            "features": [{"title": "OAuth2 System", "impact_score": 9}],
            "technical": {"code_quality": {"score": 8.5}}
        },
        "metrics": {"velocity": {"current": 42}},
        "contributors": {"top_contributors": [{"name": "Alice", "total_contributions": 15}]}
    }
    
    # Test different channel types
    channel_types = [
        (ChannelType.ENGINEERING, "Engineering team - technical focus"),
        (ChannelType.PRODUCT, "Product team - feature focus"),
        (ChannelType.EXECUTIVE, "Executive team - business impact focus")
    ]
    
    for channel_type, description in channel_types:
        print(f"\n📋 {description}")
        
        try:
            message = await slack_service.changelog_integration.create_interactive_changelog_message(
                changelog_data, channel_type, {"optimize_for_audience": True}
            )
            
            print(f"   Blocks generated: {len(message.get('blocks', []))}")
            print(f"   Fallback text: {message.get('text', 'N/A')[:100]}...")
            
            # Count interactive elements
            action_blocks = [b for b in message.get('blocks', []) if b.get('type') == 'actions']
            interactive_count = sum(len(b.get('elements', [])) for b in action_blocks)
            print(f"   Interactive elements: {interactive_count}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def example_interactive_callback_handling():
    """
    Example: Handling interactive callbacks from Slack.
    """
    print("\n🔄 Example: Interactive Callback Handling")
    print("=" * 50)
    
    slack_service = SlackService()
    
    if not slack_service.changelog_integration:
        print("❌ Changelog integration not available")
        return
    
    # Sample interaction payloads
    sample_payloads = [
        {
            "type": "block_actions",
            "actions": [{"action_id": "changelog_view_dashboard", "value": "dashboard_123"}],
            "user": {"id": "U1234567890", "name": "alice"},
            "channel": {"id": "C1234567890", "name": "engineering"},
            "message": {"ts": "1234567890.123456"}
        },
        {
            "type": "block_actions",
            "actions": [{"action_id": "feedback_positive", "value": "helpful"}],
            "user": {"id": "U0987654321", "name": "bob"},
            "channel": {"id": "C0987654321", "name": "product"},
            "message": {"ts": "1234567890.123457"}
        },
        {
            "type": "block_actions",
            "actions": [{"action_id": "changelog_start_discussion", "value": "discuss"}],
            "user": {"id": "U1122334455", "name": "carol"},
            "channel": {"id": "C1122334455", "name": "general"},
            "message": {"ts": "1234567890.123458"}
        }
    ]
    
    for i, payload in enumerate(sample_payloads, 1):
        action_id = payload["actions"][0]["action_id"]
        user_name = payload["user"]["name"]
        
        print(f"\n{i}. Handling {action_id} from {user_name}")
        
        try:
            response = await slack_service.handle_changelog_interaction(payload)
            
            print(f"   Response type: {response.get('response_type', 'N/A')}")
            print(f"   Message: {response.get('text', 'N/A')[:100]}...")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def example_feedback_collection_and_analysis():
    """
    Example: Collecting and analyzing feedback from changelog messages.
    """
    print("\n💭 Example: Feedback Collection and Analysis")
    print("=" * 50)
    
    slack_service = SlackService()
    
    if not slack_service.client:
        print("❌ Slack not configured - using mock data")
        
        # Mock feedback analysis results
        mock_feedback = {
            "success": True,
            "feedback_summary": {
                "total_reactions": 15,
                "total_replies": 8,
                "total_interactions": 12,
                "sentiment": {
                    "overall_sentiment": FeedbackSentiment.POSITIVE,
                    "sentiment_score": 0.82,
                    "positive_count": 12,
                    "negative_count": 1,
                    "neutral_count": 2
                },
                "action_items": [
                    "Follow up on deployment pipeline improvements",
                    "Schedule technical debt review session",
                    "Create documentation for OAuth2 implementation"
                ],
                "insights": {
                    "engagement_level": "high",
                    "key_topics": ["authentication", "performance", "documentation"],
                    "recommendations": [
                        "Continue focus on performance improvements",
                        "Address technical debt concerns",
                        "Provide more technical details in future changelogs"
                    ]
                }
            }
        }
        
        print("📊 Mock Feedback Analysis Results:")
        summary = mock_feedback["feedback_summary"]
        print(f"   Total engagement: {summary['total_reactions'] + summary['total_replies'] + summary['total_interactions']}")
        print(f"   Sentiment: {summary['sentiment']['overall_sentiment'].value} ({summary['sentiment']['sentiment_score']:.2f})")
        print(f"   Action items: {len(summary['action_items'])}")
        print(f"   Key topics: {', '.join(summary['insights']['key_topics'])}")
        
        return mock_feedback
    
    # Real feedback collection (requires actual message)
    sample_message_ts = "1234567890.123456"
    sample_channel_id = "C1234567890"
    
    try:
        result = await slack_service.collect_changelog_feedback(
            sample_message_ts, sample_channel_id, time_window_hours=24
        )
        
        if result.get("success"):
            summary = result["feedback_summary"]
            print(f"📊 Feedback Analysis Results:")
            print(f"   Reactions: {summary['total_reactions']}")
            print(f"   Replies: {summary['total_replies']}")
            print(f"   Interactions: {summary['total_interactions']}")
            print(f"   Sentiment: {summary['sentiment']['overall_sentiment']}")
            print(f"   Action items: {len(summary['action_items'])}")
        else:
            print(f"❌ Failed to collect feedback: {result.get('error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def example_fallback_mechanism_setup():
    """
    Example: Setting up fallback mechanisms for reliable delivery.
    """
    print("\n🛡️ Example: Fallback Mechanism Setup")
    print("=" * 50)
    
    slack_service = SlackService()
    
    if not slack_service.changelog_integration:
        print("❌ Changelog integration not available")
        return
    
    # Primary channels
    primary_channels = ["#engineering", "#product", "#executive"]
    
    # Fallback configuration
    fallback_config = {
        "email_enabled": True,
        "webhook_enabled": True,
        "alternative_channels": ["#general", "#announcements"],
        "degraded_mode": False,
        "retry_attempts": 3,
        "retry_delay_seconds": 30
    }
    
    try:
        result = await slack_service.setup_changelog_fallbacks(
            primary_channels, fallback_config
        )
        
        if result.get("success"):
            print("✅ Fallback mechanisms configured successfully")
            
            mechanisms = result["fallback_mechanisms"]
            print(f"   Email fallback: {'✅' if mechanisms['email_fallback'] else '❌'}")
            print(f"   Webhook fallback: {'✅' if mechanisms['webhook_fallback'] else '❌'}")
            print(f"   Alternative channels: {len(mechanisms['alternative_channels'])}")
            
            print(f"\n📊 Channel Status:")
            for channel, status in result["channel_status"].items():
                status_icon = "✅" if status == "available" else "❌"
                print(f"   {status_icon} {channel}: {status}")
        else:
            print(f"❌ Failed to setup fallbacks: {result.get('error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def example_thread_management():
    """
    Example: Managing discussion threads for changelog messages.
    """
    print("\n🧵 Example: Thread Management")
    print("=" * 50)
    
    slack_service = SlackService()
    
    if not slack_service.changelog_integration:
        print("❌ Changelog integration not available")
        return
    
    # Sample thread operations
    sample_message_ts = "1234567890.123456"
    sample_channel_id = "C1234567890"
    
    thread_operations = [
        ("create", {"topic": "OAuth2 Implementation Discussion", "priority": "high"}),
        ("update", {"participants": ["U1", "U2", "U3"], "status": "active"}),
        ("resolve", {"resolution": "Implementation approved", "next_steps": ["Deploy to staging"]})
    ]
    
    for operation, context in thread_operations:
        print(f"\n🔄 {operation.title()} thread operation")
        
        try:
            result = await slack_service.changelog_integration.manage_changelog_thread(
                sample_message_ts, sample_channel_id, operation, context
            )
            
            if result.get("success"):
                print(f"   ✅ {operation.title()} successful")
                if "thread_ts" in result:
                    print(f"   Thread ID: {result['thread_ts']}")
                if "participants" in result:
                    print(f"   Participants: {len(result['participants'])}")
            else:
                print(f"   ❌ {operation.title()} failed: {result.get('error')}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def example_comprehensive_workflow():
    """
    Example: Complete workflow from distribution to feedback analysis.
    """
    print("\n🔄 Example: Comprehensive Changelog Workflow")
    print("=" * 60)
    
    # Step 1: Distribute changelog
    print("1️⃣ Distributing changelog...")
    distribution_result = await example_basic_changelog_distribution()
    
    if not distribution_result or not distribution_result.get("successful_deliveries"):
        print("❌ Distribution failed - stopping workflow")
        return
    
    # Step 2: Setup fallback mechanisms
    print("\n2️⃣ Setting up fallback mechanisms...")
    await example_fallback_mechanism_setup()
    
    # Step 3: Simulate user interactions (in real scenario, these would come from Slack)
    print("\n3️⃣ Handling user interactions...")
    await example_interactive_callback_handling()
    
    # Step 4: Collect and analyze feedback
    print("\n4️⃣ Collecting feedback...")
    feedback_result = await example_feedback_collection_and_analysis()
    
    # Step 5: Generate insights and recommendations
    print("\n5️⃣ Generating insights...")
    if feedback_result and feedback_result.get("success"):
        insights = feedback_result["feedback_summary"]["insights"]
        print(f"   📈 Engagement level: {insights['engagement_level']}")
        print(f"   🏷️ Key topics: {', '.join(insights['key_topics'])}")
        print(f"   💡 Recommendations:")
        for rec in insights["recommendations"]:
            print(f"      • {rec}")
    
    print("\n✅ Comprehensive workflow completed!")


def print_configuration_example():
    """
    Print example configuration for changelog Slack integration.
    """
    print("\n⚙️ Example Configuration")
    print("=" * 50)
    
    config_example = {
        "changelog_slack_integration": {
            "enabled": True,
            "default_channels": ["#engineering", "#product"],
            "channel_routing": {
                "engineering": {
                    "content_filters": ["technical", "code", "deployment", "bug"],
                    "priority_threshold": "low",
                    "stakeholder_groups": ["developers", "tech_leads"]
                },
                "product": {
                    "content_filters": ["feature", "user", "product", "release"],
                    "priority_threshold": "medium",
                    "stakeholder_groups": ["product_managers", "designers"]
                },
                "executive": {
                    "content_filters": ["milestone", "critical", "business"],
                    "priority_threshold": "high",
                    "stakeholder_groups": ["executives", "directors"]
                }
            },
            "interactive_elements": {
                "enabled": True,
                "feedback_collection": True,
                "thread_management": True,
                "mention_targeting": True
            },
            "fallback_mechanisms": {
                "email_enabled": True,
                "webhook_enabled": True,
                "alternative_channels": ["#general"],
                "retry_attempts": 3,
                "retry_delay_seconds": 30
            },
            "analytics": {
                "engagement_tracking": True,
                "sentiment_analysis": True,
                "action_item_extraction": True
            }
        }
    }
    
    print("📄 Configuration (YAML format):")
    print("```yaml")
    import yaml
    print(yaml.dump(config_example, default_flow_style=False, indent=2))
    print("```")


async def main():
    """
    Run all examples.
    """
    print("🚀 Advanced Changelog Slack Integration Examples")
    print("=" * 60)
    
    # Print configuration example
    print_configuration_example()
    
    # Run examples
    await example_basic_changelog_distribution()
    await example_channel_specific_optimization()
    await example_interactive_callback_handling()
    await example_feedback_collection_and_analysis()
    await example_fallback_mechanism_setup()
    await example_thread_management()
    
    # Run comprehensive workflow
    await example_comprehensive_workflow()
    
    print("\n🎉 All examples completed!")


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())