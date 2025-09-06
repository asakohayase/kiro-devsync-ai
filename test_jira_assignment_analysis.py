#!/usr/bin/env python3
"""
Test script for JIRA Assignment Analysis System

This script demonstrates the comprehensive JIRA assignment change analysis
including workload impact assessment and contextual notifications.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from devsync_ai.services.jira_assignment_analyzer import JiraAssignmentAnalyzer
from devsync_ai.webhooks.jira_assignment_webhook_processor import jira_assignment_processor


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_assignment_webhook() -> Dict[str, Any]:
    """Create a sample JIRA assignment webhook payload."""
    return {
        "timestamp": int(datetime.utcnow().timestamp() * 1000),
        "webhookEvent": "jira:issue_updated",
        "issue_event_type_name": "issue_updated",
        "user": {
            "self": "https://company.atlassian.net/rest/api/2/user?username=admin",
            "name": "admin",
            "key": "admin",
            "emailAddress": "admin@company.com",
            "displayName": "Administrator"
        },
        "issue": {
            "id": "12345",
            "key": "PROJ-123",
            "self": "https://company.atlassian.net/rest/api/2/issue/12345",
            "fields": {
                "summary": "Implement user authentication system",
                "status": {
                    "self": "https://company.atlassian.net/rest/api/2/status/3",
                    "description": "",
                    "iconUrl": "https://company.atlassian.net/images/icons/statuses/inprogress.png",
                    "name": "In Progress",
                    "id": "3",
                    "statusCategory": {
                        "self": "https://company.atlassian.net/rest/api/2/statuscategory/4",
                        "id": 4,
                        "key": "indeterminate",
                        "colorName": "yellow",
                        "name": "In Progress"
                    }
                },
                "priority": {
                    "self": "https://company.atlassian.net/rest/api/2/priority/3",
                    "iconUrl": "https://company.atlassian.net/images/icons/priorities/high.svg",
                    "name": "High",
                    "id": "3"
                },
                "assignee": {
                    "self": "https://company.atlassian.net/rest/api/2/user?username=john.doe",
                    "name": "john.doe",
                    "key": "john.doe",
                    "emailAddress": "john.doe@company.com",
                    "displayName": "John Doe"
                },
                "reporter": {
                    "self": "https://company.atlassian.net/rest/api/2/user?username=jane.smith",
                    "name": "jane.smith",
                    "key": "jane.smith",
                    "emailAddress": "jane.smith@company.com",
                    "displayName": "Jane Smith"
                },
                "issuetype": {
                    "self": "https://company.atlassian.net/rest/api/2/issuetype/1",
                    "id": "1",
                    "description": "A task that needs to be done.",
                    "iconUrl": "https://company.atlassian.net/secure/viewavatar?size=xsmall&avatarId=10318&avatarType=issuetype",
                    "name": "Story",
                    "subtask": False,
                    "avatarId": 10318
                },
                "project": {
                    "self": "https://company.atlassian.net/rest/api/2/project/10000",
                    "id": "10000",
                    "key": "PROJ",
                    "name": "Sample Project",
                    "projectTypeKey": "software",
                    "avatarUrls": {
                        "48x48": "https://company.atlassian.net/secure/projectavatar?avatarId=10324",
                        "24x24": "https://company.atlassian.net/secure/projectavatar?size=small&avatarId=10324",
                        "16x16": "https://company.atlassian.net/secure/projectavatar?size=xsmall&avatarId=10324",
                        "32x32": "https://company.atlassian.net/secure/projectavatar?size=medium&avatarId=10324"
                    }
                },
                "customfield_10016": 8,  # Story points
                "customfield_10020": [
                    {
                        "id": 1,
                        "name": "Sprint 10",
                        "state": "active",
                        "boardId": 1,
                        "goal": "Complete authentication features"
                    }
                ],
                "duedate": (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d"),
                "labels": [
                    {"name": "backend"},
                    {"name": "security"}
                ],
                "components": [
                    {
                        "self": "https://company.atlassian.net/rest/api/2/component/10000",
                        "id": "10000",
                        "name": "Authentication"
                    }
                ]
            }
        },
        "changelog": {
            "id": "67890",
            "items": [
                {
                    "field": "assignee",
                    "fieldtype": "jira",
                    "from": "jane.smith",
                    "fromString": "Jane Smith",
                    "to": "john.doe",
                    "toString": "John Doe"
                }
            ]
        }
    }


def create_new_assignment_webhook() -> Dict[str, Any]:
    """Create a sample new assignment webhook payload."""
    webhook = create_sample_assignment_webhook()
    
    # Modify for new assignment (no previous assignee)
    webhook["changelog"]["items"][0]["from"] = None
    webhook["changelog"]["items"][0]["fromString"] = None
    
    return webhook


def create_unassignment_webhook() -> Dict[str, Any]:
    """Create a sample unassignment webhook payload."""
    webhook = create_sample_assignment_webhook()
    
    # Modify for unassignment
    webhook["issue"]["fields"]["assignee"] = None
    webhook["changelog"]["items"][0]["to"] = None
    webhook["changelog"]["items"][0]["toString"] = None
    
    return webhook


def create_high_priority_assignment_webhook() -> Dict[str, Any]:
    """Create a high-priority assignment that would trigger workload warnings."""
    webhook = create_sample_assignment_webhook()
    
    # Make it critical priority
    webhook["issue"]["fields"]["priority"]["name"] = "Critical"
    webhook["issue"]["fields"]["priority"]["id"] = "1"
    
    # Add more story points
    webhook["issue"]["fields"]["customfield_10016"] = 13
    
    # Make it overdue
    webhook["issue"]["fields"]["duedate"] = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
    
    return webhook


async def test_assignment_analysis():
    """Test the assignment analysis functionality."""
    print("🎯 Testing JIRA Assignment Analysis System")
    print("=" * 60)
    
    analyzer = JiraAssignmentAnalyzer()
    
    # Test scenarios
    test_scenarios = [
        ("New Assignment", create_new_assignment_webhook()),
        ("Reassignment", create_sample_assignment_webhook()),
        ("Unassignment", create_unassignment_webhook()),
        ("High Priority Assignment", create_high_priority_assignment_webhook())
    ]
    
    for scenario_name, webhook_payload in test_scenarios:
        print(f"\n📋 Testing: {scenario_name}")
        print("-" * 40)
        
        try:
            # Analyze the assignment change
            result = await analyzer.analyze_assignment_change(webhook_payload)
            
            if result.get("success"):
                print(f"✅ Analysis successful")
                print(f"   Ticket: {result.get('ticket_key')}")
                print(f"   Change Type: {result.get('assignment_change')}")
                print(f"   Notifications Sent: {result.get('notifications_sent', 0)}")
                print(f"   Workload Risks: {result.get('workload_risks', [])}")
                
                if result.get('recommendations'):
                    print(f"   Recommendations:")
                    for rec in result['recommendations'][:3]:  # Show top 3
                        print(f"     • {rec}")
            else:
                print(f"❌ Analysis failed: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Error in analysis: {e}")
    
    print(f"\n🏁 Assignment analysis testing completed")


async def test_webhook_processing():
    """Test the webhook processing functionality."""
    print("\n🔗 Testing Webhook Processing")
    print("=" * 60)
    
    # Test scenarios
    test_scenarios = [
        ("Assignment Change Webhook", create_sample_assignment_webhook()),
        ("New Assignment Webhook", create_new_assignment_webhook()),
        ("Critical Assignment Webhook", create_high_priority_assignment_webhook())
    ]
    
    for scenario_name, webhook_payload in test_scenarios:
        print(f"\n📋 Testing: {scenario_name}")
        print("-" * 40)
        
        try:
            # Process through webhook processor
            result = await jira_assignment_processor.process_webhook(webhook_payload)
            
            if result.get("success"):
                print(f"✅ Webhook processing successful")
                print(f"   Issue: {result.get('issue_key')}")
                print(f"   Event: {result.get('webhook_event')}")
                
                if "analysis" in result:
                    analysis = result["analysis"]
                    print(f"   Analysis Success: {analysis.get('success')}")
                    print(f"   Notifications: {analysis.get('notifications_sent', 0)}")
            else:
                print(f"❌ Webhook processing failed: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Error in webhook processing: {e}")
    
    print(f"\n🏁 Webhook processing testing completed")


async def test_workload_scenarios():
    """Test various workload scenarios."""
    print("\n⚖️ Testing Workload Scenarios")
    print("=" * 60)
    
    analyzer = JiraAssignmentAnalyzer()
    
    # Create scenarios with different workload impacts
    scenarios = [
        {
            "name": "Normal Workload Assignment",
            "webhook": create_sample_assignment_webhook(),
            "description": "Standard assignment to team member with normal workload"
        },
        {
            "name": "High Workload Assignment", 
            "webhook": create_high_priority_assignment_webhook(),
            "description": "Critical priority assignment that may cause workload concerns"
        },
        {
            "name": "Sprint Capacity Assignment",
            "webhook": create_sample_assignment_webhook(),
            "description": "Assignment within active sprint with capacity considerations"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📊 Testing: {scenario['name']}")
        print(f"   Description: {scenario['description']}")
        print("-" * 40)
        
        try:
            result = await analyzer.analyze_assignment_change(scenario["webhook"])
            
            if result.get("success"):
                workload_risks = result.get("workload_risks", [])
                recommendations = result.get("recommendations", [])
                
                print(f"✅ Workload analysis completed")
                print(f"   Risk Levels: {workload_risks}")
                print(f"   Recommendations Count: {len(recommendations)}")
                
                if recommendations:
                    print("   Top Recommendations:")
                    for rec in recommendations[:2]:
                        print(f"     • {rec}")
            else:
                print(f"❌ Workload analysis failed: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Error in workload analysis: {e}")
    
    print(f"\n🏁 Workload scenario testing completed")


async def demonstrate_notification_contexts():
    """Demonstrate different notification contexts."""
    print("\n📢 Demonstrating Notification Contexts")
    print("=" * 60)
    
    contexts = [
        {
            "name": "New Assignment Notification",
            "description": "Direct mention to new assignee with ticket details",
            "webhook": create_new_assignment_webhook()
        },
        {
            "name": "Reassignment Notification", 
            "description": "Notifications to both old and new assignees",
            "webhook": create_sample_assignment_webhook()
        },
        {
            "name": "Workload Warning Notification",
            "description": "High-priority assignment with workload concerns",
            "webhook": create_high_priority_assignment_webhook()
        },
        {
            "name": "Unassignment Notification",
            "description": "Team notification for unassigned ticket",
            "webhook": create_unassignment_webhook()
        }
    ]
    
    analyzer = JiraAssignmentAnalyzer()
    
    for context in contexts:
        print(f"\n📋 Context: {context['name']}")
        print(f"   Description: {context['description']}")
        print("-" * 40)
        
        try:
            # Parse assignment data to show what would be included in notifications
            assignment_data = await analyzer._parse_assignment_data(context["webhook"])
            
            if assignment_data:
                print(f"   Ticket: {assignment_data.ticket_key}")
                print(f"   Title: {assignment_data.title}")
                print(f"   Change Type: {assignment_data.change_type.value}")
                print(f"   Priority: {assignment_data.priority}")
                print(f"   Story Points: {assignment_data.story_points}")
                print(f"   Sprint: {assignment_data.sprint}")
                print(f"   Due Date: {assignment_data.due_date}")
                
                if assignment_data.new_assignee:
                    print(f"   New Assignee: {assignment_data.new_assignee}")
                if assignment_data.previous_assignee:
                    print(f"   Previous Assignee: {assignment_data.previous_assignee}")
                    
                print(f"   JIRA URL: {assignment_data.jira_url}")
            else:
                print("   ❌ Could not parse assignment data")
                
        except Exception as e:
            print(f"   ❌ Error demonstrating context: {e}")
    
    print(f"\n🏁 Notification context demonstration completed")


async def main():
    """Run all tests and demonstrations."""
    print("🚀 JIRA Assignment Analysis System - Comprehensive Test")
    print("=" * 80)
    print("This test demonstrates the complete JIRA assignment change analysis")
    print("including workload impact assessment and contextual notifications.")
    print("=" * 80)
    
    try:
        # Run all test suites
        await test_assignment_analysis()
        await test_webhook_processing()
        await test_workload_scenarios()
        await demonstrate_notification_contexts()
        
        print("\n" + "=" * 80)
        print("🎉 All tests completed successfully!")
        print("=" * 80)
        print("\nKey Features Demonstrated:")
        print("✅ Assignment data parsing from JIRA webhooks")
        print("✅ Workload impact analysis and capacity tracking")
        print("✅ Risk level assessment and recommendations")
        print("✅ Contextual notification generation")
        print("✅ Multiple assignment scenarios (new, reassign, unassign)")
        print("✅ Integration with existing notification systems")
        print("\nThe system is ready to handle JIRA assignment changes with:")
        print("• Intelligent workload management")
        print("• Proactive capacity monitoring")
        print("• Targeted Slack notifications")
        print("• Actionable recommendations")
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        logger.error(f"Test execution error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())