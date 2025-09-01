"""
JIRA Assignment Hook Integration Examples

This module demonstrates how to integrate and use the JIRA Assignment Hook
for intelligent workload management and assignment change notifications.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from devsync_ai.hooks.jira_assignment_hook import (
    JiraAssignmentHook,
    AssignmentChangeType,
    WorkloadRiskLevel,
    AssignmentChangeData,
    WorkloadAnalysis
)
from devsync_ai.webhooks.jira_assignment_webhook_handler import (
    initialize_assignment_hook,
    process_assignment_change_webhook
)
from devsync_ai.core.enhanced_notification_handler import EnrichedEvent
from devsync_ai.core.event_classification_engine import EventCategory, UrgencyLevel


logger = logging.getLogger(__name__)


async def example_basic_assignment_hook_usage():
    """
    Example 1: Basic JIRA Assignment Hook Usage
    
    Demonstrates how to initialize and use the assignment hook for
    processing assignment changes.
    """
    print("🎯 Example 1: Basic Assignment Hook Usage")
    print("=" * 50)
    
    # Initialize the assignment hook
    assignment_hook = JiraAssignmentHook()
    
    # In a real application, you would initialize with actual services
    # await assignment_hook.initialize()
    
    # Create a sample assignment change event
    assignment_event = EnrichedEvent(
        event_id="example_assignment_001",
        source="jira",
        event_type="jira:assignment_change",
        category=EventCategory.ASSIGNMENT,
        urgency=UrgencyLevel.MEDIUM,
        data={
            "issue": {
                "key": "EXAMPLE-123",
                "fields": {
                    "summary": "Implement user authentication system",
                    "assignee": {
                        "displayName": "Alice Johnson",
                        "name": "alice.johnson"
                    },
                    "priority": {"name": "High"},
                    "status": {"name": "To Do"},
                    "issuetype": {"name": "Story"},
                    "reporter": {"displayName": "Product Manager"},
                    "customfield_10016": 8,  # Story points
                    "customfield_10020": [{   # Sprint
                        "name": "Sprint 15",
                        "state": "active"
                    }]
                }
            },
            "changelog": {
                "items": [
                    {
                        "field": "assignee",
                        "fromString": None,
                        "toString": "Alice Johnson"
                    }
                ]
            }
        },
        timestamp=datetime.utcnow(),
        team_id="engineering",
        user_id="alice.johnson"
    )
    
    # Check if the hook should execute for this event
    should_execute = assignment_hook.should_execute(assignment_event)
    print(f"Should execute hook: {should_execute}")
    
    # Demonstrate assignment change type determination
    change_type = assignment_hook._determine_change_type(None, "Alice Johnson")
    print(f"Assignment change type: {change_type.value}")
    
    # Demonstrate workload risk calculation
    risk_level = assignment_hook._calculate_workload_risk(
        ticket_count=5,
        story_points=20,
        high_priority_count=2,
        overdue_count=0,
        sprint_capacity_utilization=0.8
    )
    print(f"Workload risk level: {risk_level.value}")
    
    # Generate workload recommendations
    recommendations = assignment_hook._generate_workload_recommendations(
        assignee="Alice Johnson",
        ticket_count=5,
        story_points=20,
        high_priority_count=2,
        overdue_count=0,
        sprint_capacity_utilization=0.8,
        risk_level=risk_level
    )
    print(f"Workload recommendations: {recommendations}")
    
    print("✅ Basic assignment hook usage completed!\n")


async def example_webhook_processing():
    """
    Example 2: Webhook Processing
    
    Demonstrates how to process JIRA assignment webhooks and
    trigger the assignment hook.
    """
    print("🔗 Example 2: Webhook Processing")
    print("=" * 50)
    
    # Sample JIRA assignment webhook payload
    webhook_payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "BACKEND-456",
            "fields": {
                "summary": "Optimize database query performance",
                "assignee": {
                    "displayName": "Bob Smith",
                    "name": "bob.smith"
                },
                "priority": {"name": "Critical"},
                "status": {"name": "In Progress"},
                "issuetype": {"name": "Bug"},
                "reporter": {"displayName": "QA Team"},
                "customfield_10016": 5,  # Story points
                "customfield_10020": [{   # Sprint
                    "name": "Sprint 15",
                    "state": "active"
                }],
                "labels": [{"name": "performance"}, {"name": "database"}],
                "components": [{"name": "Backend API"}],
                "duedate": (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%d")
            }
        },
        "changelog": {
            "items": [
                {
                    "field": "assignee",
                    "fromString": "Previous Developer",
                    "toString": "Bob Smith"
                }
            ]
        },
        "user": {
            "displayName": "System User",
            "name": "system"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print("Processing webhook payload...")
    print(f"Ticket: {webhook_payload['issue']['key']}")
    print(f"Assignee: {webhook_payload['issue']['fields']['assignee']['displayName']}")
    print(f"Priority: {webhook_payload['issue']['fields']['priority']['name']}")
    
    try:
        # Process the webhook payload
        result = await process_assignment_change_webhook(webhook_payload)
        
        print(f"Processing result: {result}")
        
        if result.get("success"):
            print("✅ Webhook processed successfully!")
        else:
            print(f"⚠️ Webhook processing completed with issues: {result.get('message')}")
            
    except Exception as e:
        print(f"❌ Webhook processing failed: {e}")
        print("ℹ️ This is expected in example environment without full service setup")
    
    print("✅ Webhook processing example completed!\n")


async def example_workload_analysis():
    """
    Example 3: Advanced Workload Analysis
    
    Demonstrates comprehensive workload analysis including risk assessment,
    conflict detection, and recommendation generation.
    """
    print("📊 Example 3: Advanced Workload Analysis")
    print("=" * 50)
    
    # Create sample assignment data
    assignment_data = AssignmentChangeData(
        ticket_key="FRONTEND-789",
        title="Implement responsive design for mobile",
        previous_assignee="Charlie Brown",
        new_assignee="Diana Prince",
        priority="High",
        status="To Do",
        story_points=13,
        sprint="Sprint 15",
        reporter="UX Designer",
        timestamp=datetime.utcnow(),
        change_type=AssignmentChangeType.REASSIGNMENT,
        project_key="FRONTEND",
        issue_type="Story",
        due_date=datetime.utcnow() + timedelta(days=10),
        labels=["ui", "mobile", "responsive"],
        components=["Frontend Components"]
    )
    
    print(f"Analyzing assignment: {assignment_data.ticket_key}")
    print(f"Change type: {assignment_data.change_type.value}")
    print(f"New assignee: {assignment_data.new_assignee}")
    print(f"Priority: {assignment_data.priority}")
    print(f"Story points: {assignment_data.story_points}")
    
    # Create sample workload analysis
    workload_analysis = WorkloadAnalysis(
        assignee="Diana Prince",
        current_ticket_count=12,
        current_story_points=38,
        high_priority_count=4,
        overdue_count=1,
        sprint_capacity_utilization=1.15,  # Over capacity
        risk_level=WorkloadRiskLevel.HIGH,
        recommendations=[
            "⚠️ HIGH RISK: Monitor workload closely",
            "📊 Sprint over-capacity (115%) - review commitments",
            "🔥 4 high-priority tickets - consider prioritization review",
            "📅 1 overdue ticket needs immediate attention"
        ],
        conflicts=[
            "Sprint capacity may be exceeded (51 points)",
            "Multiple high-priority tickets competing for attention"
        ],
        workload_trend="increasing"
    )
    
    print(f"\nWorkload Analysis for {workload_analysis.assignee}:")
    print(f"  Current tickets: {workload_analysis.current_ticket_count}")
    print(f"  Story points: {workload_analysis.current_story_points}")
    print(f"  High priority: {workload_analysis.high_priority_count}")
    print(f"  Overdue: {workload_analysis.overdue_count}")
    print(f"  Sprint utilization: {workload_analysis.sprint_capacity_utilization:.1%}")
    print(f"  Risk level: {workload_analysis.risk_level.value.upper()}")
    print(f"  Trend: {workload_analysis.workload_trend}")
    
    print(f"\nRecommendations:")
    for rec in workload_analysis.recommendations:
        print(f"  • {rec}")
    
    print(f"\nConflicts:")
    for conflict in workload_analysis.conflicts:
        print(f"  • {conflict}")
    
    print("✅ Workload analysis example completed!\n")


async def example_notification_formatting():
    """
    Example 4: Notification Message Formatting
    
    Demonstrates how to format assignment change notifications
    with workload information and recommendations.
    """
    print("💬 Example 4: Notification Message Formatting")
    print("=" * 50)
    
    from devsync_ai.templates.jira_templates import JiraAssignmentTemplate
    
    # Initialize the assignment template
    template = JiraAssignmentTemplate()
    
    # Example 1: New assignment with moderate workload
    print("📋 New Assignment Notification:")
    
    new_assignment_message = template.format_assignment_notification(
        ticket_key="API-101",
        title="Implement OAuth 2.0 authentication",
        assignee="Alex Developer",
        change_type="new_assignment",
        priority="High",
        status="To Do",
        story_points=8,
        sprint="Sprint 16",
        workload_info={
            "current_ticket_count": 6,
            "current_story_points": 22,
            "risk_level": "moderate",
            "high_priority_count": 2
        },
        recommendations=[
            "Consider prioritizing high-priority items",
            "Monitor workload for potential overload"
        ]
    )
    
    print(f"Text: {new_assignment_message['text']}")
    print(f"Blocks: {len(new_assignment_message['blocks'])} blocks")
    
    # Example 2: Critical workload warning
    print("\n🚨 Critical Workload Warning:")
    
    critical_workload_message = template.format_assignment_notification(
        ticket_key="URGENT-202",
        title="Fix critical production bug",
        assignee="Emergency Responder",
        change_type="new_assignment",
        priority="Critical",
        status="To Do",
        story_points=3,
        sprint="Sprint 16",
        workload_info={
            "current_ticket_count": 15,
            "current_story_points": 45,
            "risk_level": "critical",
            "high_priority_count": 6
        },
        recommendations=[
            "🚨 CRITICAL: Immediate workload redistribution needed",
            "Consider reassigning lower-priority tickets",
            "Schedule urgent discussion with team lead"
        ]
    )
    
    print(f"Text: {critical_workload_message['text']}")
    
    # Example 3: Unassignment notification
    print("\n❓ Unassignment Notification:")
    
    unassignment_message = template.format_assignment_notification(
        ticket_key="SUPPORT-303",
        title="Investigate customer reported issue",
        assignee="",  # Unassigned
        change_type="unassignment",
        priority="Medium",
        status="To Do",
        story_points=5,
        sprint="Sprint 16"
    )
    
    print(f"Text: {unassignment_message['text']}")
    
    print("✅ Notification formatting example completed!\n")


async def example_team_configuration():
    """
    Example 5: Team Configuration and Customization
    
    Demonstrates how to configure team-specific settings for
    workload limits, notification preferences, and channel mappings.
    """
    print("⚙️ Example 5: Team Configuration")
    print("=" * 50)
    
    # Example team configurations
    team_configs = {
        "engineering": {
            "project_keys": ["ENG", "BACKEND", "FRONTEND", "API"],
            "slack_channels": {
                "primary": "#engineering",
                "alerts": "#eng-alerts",
                "standup": "#eng-standup"
            },
            "project_manager": "eng.manager",
            "workload_limits": {
                "max_tickets_per_person": 12,
                "max_story_points_per_person": 30,
                "max_high_priority_per_person": 4,
                "sprint_capacity_warning_threshold": 0.9
            },
            "notification_preferences": {
                "new_assignment_urgency": "MEDIUM",
                "workload_warning_threshold": "HIGH",
                "include_workload_analysis": True,
                "include_recommendations": True
            }
        },
        "qa": {
            "project_keys": ["QA", "TEST", "BUG"],
            "slack_channels": {
                "primary": "#qa-team",
                "alerts": "#qa-alerts"
            },
            "project_manager": "qa.lead",
            "workload_limits": {
                "max_tickets_per_person": 15,
                "max_story_points_per_person": 25,
                "max_high_priority_per_person": 5,
                "sprint_capacity_warning_threshold": 0.85
            },
            "notification_preferences": {
                "new_assignment_urgency": "LOW",
                "workload_warning_threshold": "MODERATE",
                "include_workload_analysis": True,
                "include_recommendations": False
            }
        },
        "product": {
            "project_keys": ["PROD", "FEATURE", "EPIC"],
            "slack_channels": {
                "primary": "#product-team",
                "alerts": "#product-alerts"
            },
            "project_manager": "product.manager",
            "workload_limits": {
                "max_tickets_per_person": 8,
                "max_story_points_per_person": 20,
                "max_high_priority_per_person": 3,
                "sprint_capacity_warning_threshold": 0.8
            },
            "notification_preferences": {
                "new_assignment_urgency": "HIGH",
                "workload_warning_threshold": "MODERATE",
                "include_workload_analysis": True,
                "include_recommendations": True
            }
        }
    }
    
    print("Team Configurations:")
    for team_name, config in team_configs.items():
        print(f"\n{team_name.upper()} Team:")
        print(f"  Project Keys: {', '.join(config['project_keys'])}")
        print(f"  Primary Channel: {config['slack_channels']['primary']}")
        print(f"  Max Tickets/Person: {config['workload_limits']['max_tickets_per_person']}")
        print(f"  Max Story Points/Person: {config['workload_limits']['max_story_points_per_person']}")
        print(f"  Workload Warning Threshold: {config['workload_limits']['sprint_capacity_warning_threshold']:.0%}")
    
    # Example of using team configuration for workload assessment
    def assess_workload_for_team(team_name: str, assignee_workload: Dict[str, Any]) -> Dict[str, Any]:
        """Assess workload against team-specific limits."""
        if team_name not in team_configs:
            return {"status": "unknown_team"}
        
        config = team_configs[team_name]
        limits = config["workload_limits"]
        
        assessment = {
            "team": team_name,
            "within_limits": True,
            "warnings": [],
            "recommendations": []
        }
        
        # Check ticket count
        if assignee_workload["ticket_count"] > limits["max_tickets_per_person"]:
            assessment["within_limits"] = False
            assessment["warnings"].append(f"Ticket count ({assignee_workload['ticket_count']}) exceeds limit ({limits['max_tickets_per_person']})")
        
        # Check story points
        if assignee_workload["story_points"] > limits["max_story_points_per_person"]:
            assessment["within_limits"] = False
            assessment["warnings"].append(f"Story points ({assignee_workload['story_points']}) exceed limit ({limits['max_story_points_per_person']})")
        
        # Check high priority count
        if assignee_workload["high_priority_count"] > limits["max_high_priority_per_person"]:
            assessment["within_limits"] = False
            assessment["warnings"].append(f"High priority tickets ({assignee_workload['high_priority_count']}) exceed limit ({limits['max_high_priority_per_person']})")
        
        return assessment
    
    # Example workload assessment
    sample_workload = {
        "ticket_count": 14,
        "story_points": 35,
        "high_priority_count": 5
    }
    
    print(f"\nWorkload Assessment Example:")
    print(f"Sample workload: {sample_workload}")
    
    for team_name in team_configs.keys():
        assessment = assess_workload_for_team(team_name, sample_workload)
        status = "✅ Within limits" if assessment["within_limits"] else "⚠️ Exceeds limits"
        print(f"  {team_name}: {status}")
        for warning in assessment["warnings"]:
            print(f"    - {warning}")
    
    print("✅ Team configuration example completed!\n")


async def example_performance_monitoring():
    """
    Example 6: Performance Monitoring and Analytics
    
    Demonstrates how to monitor assignment hook performance
    and collect analytics for optimization.
    """
    print("📈 Example 6: Performance Monitoring")
    print("=" * 50)
    
    import time
    from collections import defaultdict
    
    # Simulate performance metrics collection
    performance_metrics = {
        "assignment_changes_processed": 1247,
        "average_processing_time_ms": 145,
        "workload_risk_alerts_sent": 23,
        "notification_delivery_success_rate": 0.987,
        "cache_hit_rate": 0.92,
        "error_rate": 0.003
    }
    
    print("Performance Metrics:")
    for metric, value in performance_metrics.items():
        if isinstance(value, float) and value < 1:
            print(f"  {metric}: {value:.1%}")
        elif "time" in metric:
            print(f"  {metric}: {value}ms")
        else:
            print(f"  {metric}: {value}")
    
    # Simulate workload distribution analytics
    workload_distribution = {
        "Alice Johnson": {"tickets": 8, "points": 25, "risk": "moderate"},
        "Bob Smith": {"tickets": 12, "points": 35, "risk": "high"},
        "Charlie Brown": {"tickets": 6, "points": 18, "risk": "low"},
        "Diana Prince": {"tickets": 15, "points": 42, "risk": "critical"},
        "Eve Wilson": {"tickets": 9, "points": 28, "risk": "moderate"}
    }
    
    print(f"\nWorkload Distribution:")
    for assignee, workload in workload_distribution.items():
        risk_emoji = {
            "low": "🟢",
            "moderate": "🟡", 
            "high": "🟠",
            "critical": "🔴"
        }[workload["risk"]]
        
        print(f"  {assignee}: {workload['tickets']} tickets, {workload['points']} points {risk_emoji}")
    
    # Simulate assignment change trends
    assignment_trends = {
        "daily_assignments": [12, 15, 8, 22, 18, 14, 19],
        "workload_alerts": [2, 3, 1, 5, 4, 2, 3],
        "team_distribution": {
            "engineering": 45,
            "qa": 28,
            "product": 15,
            "design": 12
        }
    }
    
    print(f"\nAssignment Trends (Last 7 Days):")
    print(f"  Daily assignments: {assignment_trends['daily_assignments']}")
    print(f"  Workload alerts: {assignment_trends['workload_alerts']}")
    print(f"  Team distribution: {assignment_trends['team_distribution']}")
    
    # Performance optimization recommendations
    optimization_recommendations = [
        "Consider increasing cache TTL for user workload data",
        "Implement batch processing for multiple simultaneous assignments",
        "Add database indexing for faster workload queries",
        "Optimize Slack API calls with connection pooling"
    ]
    
    print(f"\nOptimization Recommendations:")
    for i, rec in enumerate(optimization_recommendations, 1):
        print(f"  {i}. {rec}")
    
    print("✅ Performance monitoring example completed!\n")


async def main():
    """Run all integration examples."""
    print("🚀 JIRA Assignment Hook Integration Examples")
    print("=" * 60)
    print()
    
    try:
        # Run all examples
        await example_basic_assignment_hook_usage()
        await example_webhook_processing()
        await example_workload_analysis()
        await example_notification_formatting()
        await example_team_configuration()
        await example_performance_monitoring()
        
        print("=" * 60)
        print("🎉 All integration examples completed successfully!")
        print()
        print("Next Steps:")
        print("1. Configure your JIRA webhook to point to /webhooks/jira/assignment")
        print("2. Set up team configurations in config/jira_assignment_hook_config.yaml")
        print("3. Configure Slack bot permissions and channel mappings")
        print("4. Test with real JIRA assignment changes")
        print("5. Monitor performance and adjust thresholds as needed")
        
    except Exception as e:
        logger.error(f"❌ Integration example failed: {e}", exc_info=True)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run examples
    asyncio.run(main())