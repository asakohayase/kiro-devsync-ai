"""
JIRA Agent Hooks Integration Example.

This example demonstrates how to integrate and use the JIRA Agent Hooks
system with DevSync AI for intelligent Slack notifications.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from devsync_ai.webhooks.jira_webhook_handler import initialize_dispatcher, shutdown_dispatcher
from devsync_ai.hooks.hook_registry_manager import get_hook_registry_manager
from devsync_ai.core.agent_hooks import EnrichedEvent, EventClassification, EventCategory, UrgencyLevel, SignificanceLevel


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_status_change_hook():
    """Demonstrate StatusChangeHook with a sample status transition."""
    logger.info("🔄 Demonstrating Status Change Hook")
    
    # Sample JIRA webhook payload for status change
    sample_payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "DEMO-123",
            "fields": {
                "summary": "Implement user authentication system",
                "status": {"name": "In Progress"},
                "priority": {"name": "High"},
                "assignee": {
                    "displayName": "Alice Developer",
                    "accountId": "alice123"
                },
                "issuetype": {"name": "Story"},
                "components": [{"name": "Backend"}],
                "customfield_10020": [{  # Sprint field
                    "id": 1,
                    "name": "Sprint 23",
                    "state": "active"
                }]
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
    
    # Get dispatcher and send webhook
    dispatcher = await initialize_dispatcher()
    result = await dispatcher.dispatch_webhook_event(sample_payload)
    
    logger.info(f"✅ Status change processed: {result.successful_hooks} hooks executed")
    return result


async def demonstrate_blocker_detection_hook():
    """Demonstrate BlockerHook with a blocked ticket."""
    logger.info("🚫 Demonstrating Blocker Detection Hook")
    
    # Sample blocked ticket payload
    sample_payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "DEMO-456",
            "fields": {
                "summary": "Critical API endpoint failing in production",
                "status": {"name": "Blocked"},
                "priority": {"name": "Critical"},
                "assignee": {
                    "displayName": "Bob DevOps",
                    "accountId": "bob456"
                },
                "issuetype": {"name": "Bug"},
                "description": "Production API endpoint returning 500 errors, blocked by infrastructure issue"
            }
        },
        "changelog": {
            "items": [{
                "field": "status",
                "fromString": "In Progress",
                "toString": "Blocked"
            }]
        }
    }
    
    dispatcher = await initialize_dispatcher()
    result = await dispatcher.dispatch_webhook_event(sample_payload)
    
    logger.info(f"🚨 Blocker detected and processed: {result.successful_hooks} hooks executed")
    return result


async def demonstrate_assignment_hook():
    """Demonstrate AssignmentChangeHook with ticket assignment."""
    logger.info("👤 Demonstrating Assignment Change Hook")
    
    # Sample assignment change payload
    sample_payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "DEMO-789",
            "fields": {
                "summary": "Implement mobile app push notifications",
                "status": {"name": "To Do"},
                "priority": {"name": "Medium"},
                "assignee": {
                    "displayName": "Carol Mobile",
                    "accountId": "carol789"
                },
                "issuetype": {"name": "Feature"},
                "customfield_10016": 8,  # Story points
                "duedate": "2024-02-15"
            }
        },
        "changelog": {
            "items": [{
                "field": "assignee",
                "from": None,
                "to": "carol789",
                "fromString": None,
                "toString": "Carol Mobile"
            }]
        }
    }
    
    dispatcher = await initialize_dispatcher()
    result = await dispatcher.dispatch_webhook_event(sample_payload)
    
    logger.info(f"👥 Assignment processed: {result.successful_hooks} hooks executed")
    return result


async def demonstrate_critical_update_hook():
    """Demonstrate CriticalUpdateHook with high-priority incident."""
    logger.info("🚨 Demonstrating Critical Update Hook")
    
    # Sample critical incident payload
    sample_payload = {
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": "INCIDENT-001",
            "fields": {
                "summary": "Production database outage - immediate action required",
                "status": {"name": "Open"},
                "priority": {"name": "Critical"},
                "assignee": {
                    "displayName": "Emergency Response Team",
                    "accountId": "emergency123"
                },
                "issuetype": {"name": "Incident"},
                "description": "Production database cluster is down, affecting all user services. Estimated impact: 100% of users.",
                "labels": ["production", "outage", "database"]
            }
        }
    }
    
    dispatcher = await initialize_dispatcher()
    result = await dispatcher.dispatch_webhook_event(sample_payload)
    
    logger.info(f"🔥 Critical incident processed: {result.successful_hooks} hooks executed")
    return result


async def demonstrate_comment_hook():
    """Demonstrate CommentHook with significant comment."""
    logger.info("💬 Demonstrating Comment Activity Hook")
    
    # Sample comment payload
    sample_payload = {
        "webhookEvent": "jira:issue_commented",
        "issue": {
            "key": "DEMO-999",
            "fields": {
                "summary": "Implement OAuth integration",
                "status": {"name": "In Review"},
                "priority": {"name": "High"},
                "assignee": {
                    "displayName": "Dave Backend",
                    "accountId": "dave999"
                }
            }
        },
        "comment": {
            "id": "comment123",
            "author": {
                "displayName": "Tech Lead",
                "accountId": "techlead456"
            },
            "body": "This implementation is blocked by security review. @dave999 please coordinate with security team for approval. This is urgent for the upcoming release.",
            "created": "2024-01-15T10:30:00.000Z"
        }
    }
    
    dispatcher = await initialize_dispatcher()
    result = await dispatcher.dispatch_webhook_event(sample_payload)
    
    logger.info(f"💭 Comment processed: {result.successful_hooks} hooks executed")
    return result


async def demonstrate_hook_management():
    """Demonstrate hook management capabilities."""
    logger.info("⚙️ Demonstrating Hook Management")
    
    registry_manager = await get_hook_registry_manager()
    if not registry_manager:
        logger.error("Hook registry not available")
        return
    
    # Get system health
    health = await registry_manager.get_system_health()
    logger.info(f"📊 System Health: {health.enabled_hooks}/{health.total_hooks} hooks enabled")
    logger.info(f"📈 Success Rate: {health.success_rate:.1%}")
    logger.info(f"⏱️ Avg Execution Time: {health.average_execution_time_ms:.1f}ms")
    
    if health.issues:
        logger.warning(f"⚠️ Issues detected: {health.issues}")
    
    # Get all hook statuses
    hook_statuses = await registry_manager.get_all_hook_statuses()
    logger.info(f"🔧 Active Hooks:")
    for hook_status in hook_statuses:
        status_emoji = "✅" if hook_status['enabled'] else "❌"
        logger.info(f"  {status_emoji} {hook_status['hook_id']} ({hook_status['hook_type']})")
        logger.info(f"    Team: {hook_status['team_id']}")
        logger.info(f"    Channels: {hook_status['configuration']['channels']}")
        
        stats = hook_status['statistics']
        if stats['total_executions'] > 0:
            logger.info(f"    Executions: {stats['total_executions']} (Success: {stats['success_rate']:.1%})")


async def demonstrate_configuration_management():
    """Demonstrate configuration management."""
    logger.info("📋 Demonstrating Configuration Management")
    
    registry_manager = await get_hook_registry_manager()
    if not registry_manager:
        logger.error("Hook registry not available")
        return
    
    # Get team configuration
    team_config = await registry_manager.config_manager.get_team_configuration("default")
    logger.info("🏢 Default Team Configuration:")
    
    for hook_type, config in team_config.items():
        enabled_emoji = "✅" if config.get('enabled', False) else "❌"
        logger.info(f"  {enabled_emoji} {hook_type}:")
        logger.info(f"    Channels: {config.get('channels', [])}")
        
        if 'conditions' in config:
            logger.info(f"    Conditions: {len(config['conditions'])} rules")
    
    # Demonstrate configuration validation
    validation_errors = await registry_manager.config_manager.validate_configuration({
        'agent_hooks': {
            'teams': {
                'test_team': {
                    'invalid_hook': {'enabled': True}  # This should cause validation error
                }
            }
        }
    })
    
    if validation_errors:
        logger.info(f"🔍 Configuration Validation Errors: {validation_errors}")


async def run_comprehensive_demo():
    """Run comprehensive demonstration of all JIRA Agent Hooks."""
    logger.info("🚀 Starting JIRA Agent Hooks Comprehensive Demo")
    
    try:
        # Initialize the system
        await initialize_dispatcher()
        
        # Demonstrate each hook type
        await demonstrate_status_change_hook()
        await asyncio.sleep(1)  # Brief pause between demos
        
        await demonstrate_blocker_detection_hook()
        await asyncio.sleep(1)
        
        await demonstrate_assignment_hook()
        await asyncio.sleep(1)
        
        await demonstrate_critical_update_hook()
        await asyncio.sleep(1)
        
        await demonstrate_comment_hook()
        await asyncio.sleep(1)
        
        # Demonstrate management capabilities
        await demonstrate_hook_management()
        await demonstrate_configuration_management()
        
        logger.info("✅ Demo completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}", exc_info=True)
        
    finally:
        # Cleanup
        await shutdown_dispatcher()
        logger.info("🧹 System shutdown completed")


async def simulate_real_world_scenario():
    """Simulate a real-world development scenario with multiple events."""
    logger.info("🌍 Simulating Real-World Development Scenario")
    
    try:
        await initialize_dispatcher()
        
        # Scenario: Sprint planning and execution
        logger.info("📅 Scenario: Sprint Planning and Execution")
        
        # 1. New ticket assigned to developer
        logger.info("1️⃣ New feature assigned to developer")
        assignment_payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "FEAT-101",
                "fields": {
                    "summary": "Add real-time chat feature",
                    "status": {"name": "To Do"},
                    "priority": {"name": "High"},
                    "assignee": {"displayName": "Sarah Frontend", "accountId": "sarah101"},
                    "customfield_10016": 13  # Story points
                }
            },
            "changelog": {
                "items": [{"field": "assignee", "toString": "Sarah Frontend"}]
            }
        }
        
        dispatcher = await initialize_dispatcher()
        await dispatcher.dispatch_webhook_event(assignment_payload)
        await asyncio.sleep(2)
        
        # 2. Developer starts work
        logger.info("2️⃣ Developer starts working on feature")
        status_change_payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "FEAT-101",
                "fields": {
                    "summary": "Add real-time chat feature",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "High"},
                    "assignee": {"displayName": "Sarah Frontend", "accountId": "sarah101"}
                }
            },
            "changelog": {
                "items": [{"field": "status", "fromString": "To Do", "toString": "In Progress"}]
            }
        }
        
        await dispatcher.dispatch_webhook_event(status_change_payload)
        await asyncio.sleep(2)
        
        # 3. Blocker discovered
        logger.info("3️⃣ Blocker discovered during development")
        blocker_payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "FEAT-101",
                "fields": {
                    "summary": "Add real-time chat feature",
                    "status": {"name": "Blocked"},
                    "priority": {"name": "High"},
                    "assignee": {"displayName": "Sarah Frontend", "accountId": "sarah101"},
                    "description": "Blocked by missing WebSocket API endpoints from backend team"
                }
            },
            "changelog": {
                "items": [{"field": "status", "fromString": "In Progress", "toString": "Blocked"}]
            }
        }
        
        await dispatcher.dispatch_webhook_event(blocker_payload)
        await asyncio.sleep(2)
        
        # 4. Tech lead adds comment with solution
        logger.info("4️⃣ Tech lead provides solution in comment")
        comment_payload = {
            "webhookEvent": "jira:issue_commented",
            "issue": {
                "key": "FEAT-101",
                "fields": {
                    "summary": "Add real-time chat feature",
                    "status": {"name": "Blocked"},
                    "priority": {"name": "High"}
                }
            },
            "comment": {
                "author": {"displayName": "Tech Lead", "accountId": "techlead"},
                "body": "I've coordinated with backend team. @sarah101 you can use the mock WebSocket service for now. Backend APIs will be ready by end of week. Decision: proceed with mocks for testing."
            }
        }
        
        await dispatcher.dispatch_webhook_event(comment_payload)
        await asyncio.sleep(2)
        
        # 5. Blocker resolved, work continues
        logger.info("5️⃣ Blocker resolved, development continues")
        unblock_payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "FEAT-101",
                "fields": {
                    "summary": "Add real-time chat feature",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "High"},
                    "assignee": {"displayName": "Sarah Frontend", "accountId": "sarah101"}
                }
            },
            "changelog": {
                "items": [{"field": "status", "fromString": "Blocked", "toString": "In Progress"}]
            }
        }
        
        await dispatcher.dispatch_webhook_event(unblock_payload)
        await asyncio.sleep(2)
        
        # 6. Feature completed
        logger.info("6️⃣ Feature development completed")
        completion_payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "FEAT-101",
                "fields": {
                    "summary": "Add real-time chat feature",
                    "status": {"name": "Done"},
                    "priority": {"name": "High"},
                    "assignee": {"displayName": "Sarah Frontend", "accountId": "sarah101"}
                }
            },
            "changelog": {
                "items": [{"field": "status", "fromString": "In Progress", "toString": "Done"}]
            }
        }
        
        await dispatcher.dispatch_webhook_event(completion_payload)
        
        logger.info("🎉 Real-world scenario simulation completed!")
        
        # Show final statistics
        registry_manager = await get_hook_registry_manager()
        if registry_manager:
            health = await registry_manager.get_system_health()
            logger.info(f"📊 Final Statistics:")
            logger.info(f"  Total Hook Executions: {sum(h['statistics']['total_executions'] for h in await registry_manager.get_all_hook_statuses())}")
            logger.info(f"  Overall Success Rate: {health.success_rate:.1%}")
            logger.info(f"  Average Response Time: {health.average_execution_time_ms:.1f}ms")
        
    except Exception as e:
        logger.error(f"❌ Scenario simulation failed: {e}", exc_info=True)
        
    finally:
        await shutdown_dispatcher()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="JIRA Agent Hooks Integration Demo")
    parser.add_argument("--demo", choices=["comprehensive", "scenario"], 
                       default="comprehensive", help="Type of demo to run")
    
    args = parser.parse_args()
    
    if args.demo == "comprehensive":
        asyncio.run(run_comprehensive_demo())
    elif args.demo == "scenario":
        asyncio.run(simulate_real_world_scenario())