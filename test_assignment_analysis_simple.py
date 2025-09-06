#!/usr/bin/env python3
"""
Simple test script for JIRA Assignment Analysis System

This script demonstrates the assignment analysis functionality without
requiring full environment setup.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any


def create_sample_assignment_webhook() -> Dict[str, Any]:
    """Create a sample JIRA assignment webhook payload."""
    return {
        "timestamp": int(datetime.utcnow().timestamp() * 1000),
        "webhookEvent": "jira:issue_updated",
        "issue_event_type_name": "issue_updated",
        "user": {
            "displayName": "Administrator"
        },
        "issue": {
            "id": "12345",
            "key": "PROJ-123",
            "fields": {
                "summary": "Implement user authentication system",
                "status": {
                    "name": "In Progress"
                },
                "priority": {
                    "name": "High"
                },
                "assignee": {
                    "displayName": "John Doe"
                },
                "reporter": {
                    "displayName": "Jane Smith"
                },
                "issuetype": {
                    "name": "Story"
                },
                "project": {
                    "key": "PROJ",
                    "name": "Sample Project"
                },
                "customfield_10016": 8,  # Story points
                "customfield_10020": [
                    {
                        "name": "Sprint 10",
                        "state": "active"
                    }
                ],
                "duedate": (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d"),
                "labels": [
                    {"name": "backend"},
                    {"name": "security"}
                ],
                "components": [
                    {
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


def analyze_assignment_change_type(payload: Dict[str, Any]) -> str:
    """Analyze the type of assignment change."""
    changelog = payload.get("changelog", {})
    if "items" in changelog:
        for item in changelog["items"]:
            if item.get("field") == "assignee":
                previous = item.get("fromString")
                new = item.get("toString")
                
                if not previous and new:
                    return "NEW_ASSIGNMENT"
                elif previous and not new:
                    return "UNASSIGNMENT"
                elif previous and new and previous != new:
                    return "REASSIGNMENT"
                elif previous == new:
                    return "SELF_ASSIGNMENT"
    
    return "UNKNOWN"


def extract_assignment_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract assignment data from webhook payload."""
    issue = payload.get("issue", {})
    fields = issue.get("fields", {})
    changelog = payload.get("changelog", {})
    
    # Extract assignee information
    previous_assignee = None
    new_assignee = None
    
    current_assignee = fields.get("assignee")
    if current_assignee:
        new_assignee = current_assignee.get("displayName")
    
    if "items" in changelog:
        for item in changelog["items"]:
            if item.get("field") == "assignee":
                previous_assignee = item.get("fromString")
                if not new_assignee:
                    new_assignee = item.get("toString")
                break
    
    # Extract sprint information
    sprint = None
    sprint_field = fields.get("customfield_10020")
    if sprint_field and isinstance(sprint_field, list) and sprint_field:
        sprint = sprint_field[0].get("name")
    
    return {
        "ticket_key": issue.get("key"),
        "title": fields.get("summary"),
        "previous_assignee": previous_assignee,
        "new_assignee": new_assignee,
        "priority": fields.get("priority", {}).get("name"),
        "status": fields.get("status", {}).get("name"),
        "story_points": fields.get("customfield_10016"),
        "sprint": sprint,
        "reporter": fields.get("reporter", {}).get("displayName"),
        "project_key": fields.get("project", {}).get("key"),
        "issue_type": fields.get("issuetype", {}).get("name"),
        "due_date": fields.get("duedate"),
        "labels": [label.get("name") for label in fields.get("labels", [])],
        "components": [comp.get("name") for comp in fields.get("components", [])]
    }


def calculate_workload_risk(ticket_count: int, story_points: int, high_priority_count: int) -> str:
    """Calculate workload risk level."""
    risk_score = 0
    
    # Ticket count risk
    if ticket_count > 12:
        risk_score += 3
    elif ticket_count > 8:
        risk_score += 2
    elif ticket_count > 6:
        risk_score += 1
    
    # Story points risk
    if story_points > 30:
        risk_score += 3
    elif story_points > 20:
        risk_score += 2
    elif story_points > 15:
        risk_score += 1
    
    # High priority risk
    if high_priority_count > 4:
        risk_score += 3
    elif high_priority_count > 2:
        risk_score += 2
    elif high_priority_count > 1:
        risk_score += 1
    
    # Determine risk level
    if risk_score >= 8:
        return "CRITICAL"
    elif risk_score >= 5:
        return "HIGH"
    elif risk_score >= 3:
        return "MODERATE"
    else:
        return "LOW"


def generate_notification_message(assignment_data: Dict[str, Any], change_type: str) -> str:
    """Generate notification message based on assignment data."""
    ticket_key = assignment_data["ticket_key"]
    title = assignment_data["title"]
    new_assignee = assignment_data["new_assignee"]
    previous_assignee = assignment_data["previous_assignee"]
    priority = assignment_data["priority"]
    story_points = assignment_data["story_points"]
    sprint = assignment_data["sprint"]
    due_date = assignment_data["due_date"]
    
    if change_type == "NEW_ASSIGNMENT":
        message = f"🎯 @{new_assignee} you've been assigned **{ticket_key}**: {title}"
    elif change_type == "REASSIGNMENT":
        message = f"🔄 **{ticket_key}** reassigned from @{previous_assignee} to @{new_assignee}"
    elif change_type == "UNASSIGNMENT":
        message = f"❓ **{ticket_key}** is now unassigned and needs an owner"
    else:
        message = f"📋 **{ticket_key}** assignment updated"
    
    message += f"\nTitle: {title}"
    
    if priority and priority != "Medium":
        message += f"\nPriority: **{priority}**"
    
    if story_points:
        message += f"\nEffort: {story_points} story points"
    
    if sprint:
        message += f"\nSprint: {sprint}"
    
    if due_date:
        message += f"\nDue: {due_date}"
    
    # Simulate workload analysis
    current_tickets = 7  # Simulated current workload
    current_points = 28  # Simulated current story points
    high_priority = 2   # Simulated high priority tickets
    
    if change_type in ["NEW_ASSIGNMENT", "REASSIGNMENT"] and new_assignee:
        # Add new assignment to workload
        current_tickets += 1
        current_points += story_points or 0
        if priority in ["High", "Highest", "Critical"]:
            high_priority += 1
        
        risk_level = calculate_workload_risk(current_tickets, current_points, high_priority)
        
        if risk_level in ["HIGH", "CRITICAL"]:
            message += f"\n⚠️ **Workload Alert**: {new_assignee} now has {current_tickets} active tickets"
            
            if risk_level == "CRITICAL":
                message += "\n🚨 **CRITICAL**: Immediate workload redistribution needed"
            elif risk_level == "HIGH":
                message += "\n⚠️ **HIGH RISK**: Monitor workload closely"
    
    message += f"\n🔗 [View in JIRA](https://company.atlassian.net/browse/{ticket_key})"
    
    return message


def demonstrate_scenarios():
    """Demonstrate different assignment scenarios."""
    print("🎯 JIRA Assignment Analysis System - Demonstration")
    print("=" * 60)
    
    # Test scenarios
    scenarios = [
        {
            "name": "New Assignment",
            "description": "Ticket assigned to someone for the first time",
            "webhook": create_sample_assignment_webhook()
        },
        {
            "name": "Reassignment", 
            "description": "Ticket moved from one assignee to another",
            "webhook": create_sample_assignment_webhook()
        },
        {
            "name": "High Priority Assignment",
            "description": "Critical priority assignment with workload concerns",
            "webhook": create_sample_assignment_webhook()
        }
    ]
    
    # Modify scenarios
    scenarios[0]["webhook"]["changelog"]["items"][0]["from"] = None
    scenarios[0]["webhook"]["changelog"]["items"][0]["fromString"] = None
    
    scenarios[2]["webhook"]["issue"]["fields"]["priority"]["name"] = "Critical"
    scenarios[2]["webhook"]["issue"]["fields"]["customfield_10016"] = 13
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print("-" * 40)
        
        try:
            # Analyze assignment change
            change_type = analyze_assignment_change_type(scenario["webhook"])
            assignment_data = extract_assignment_data(scenario["webhook"])
            
            print(f"✅ Analysis Results:")
            print(f"   Change Type: {change_type}")
            print(f"   Ticket: {assignment_data['ticket_key']}")
            print(f"   Title: {assignment_data['title']}")
            print(f"   New Assignee: {assignment_data['new_assignee']}")
            print(f"   Previous Assignee: {assignment_data['previous_assignee']}")
            print(f"   Priority: {assignment_data['priority']}")
            print(f"   Story Points: {assignment_data['story_points']}")
            print(f"   Sprint: {assignment_data['sprint']}")
            
            # Generate notification message
            message = generate_notification_message(assignment_data, change_type)
            print(f"\n📢 Generated Notification:")
            print("   " + message.replace("\n", "\n   "))
            
        except Exception as e:
            print(f"❌ Error in scenario analysis: {e}")
    
    print(f"\n🏁 Demonstration completed successfully!")
    print("\nKey Features Demonstrated:")
    print("✅ Assignment data parsing from JIRA webhooks")
    print("✅ Change type detection (new, reassign, unassign)")
    print("✅ Workload risk assessment")
    print("✅ Contextual notification generation")
    print("✅ Rich message formatting with actionable information")


def show_workload_analysis():
    """Demonstrate workload analysis capabilities."""
    print("\n⚖️ Workload Analysis Demonstration")
    print("=" * 60)
    
    workload_scenarios = [
        {"name": "Normal Workload", "tickets": 5, "points": 18, "high_priority": 1},
        {"name": "High Workload", "tickets": 9, "points": 32, "high_priority": 3},
        {"name": "Critical Overload", "tickets": 14, "points": 48, "high_priority": 6}
    ]
    
    for scenario in workload_scenarios:
        risk_level = calculate_workload_risk(
            scenario["tickets"], 
            scenario["points"], 
            scenario["high_priority"]
        )
        
        print(f"\n📊 {scenario['name']}:")
        print(f"   Tickets: {scenario['tickets']}")
        print(f"   Story Points: {scenario['points']}")
        print(f"   High Priority: {scenario['high_priority']}")
        print(f"   Risk Level: {risk_level}")
        
        if risk_level == "CRITICAL":
            print("   🚨 Immediate workload redistribution needed")
        elif risk_level == "HIGH":
            print("   ⚠️ Monitor workload closely")
        elif risk_level == "MODERATE":
            print("   📊 Approaching capacity limits")
        else:
            print("   ✅ Normal workload within capacity")


def main():
    """Run the demonstration."""
    try:
        demonstrate_scenarios()
        show_workload_analysis()
        
        print("\n" + "=" * 60)
        print("🎉 JIRA Assignment Analysis System Ready!")
        print("=" * 60)
        print("\nThe system provides:")
        print("• Intelligent assignment change detection")
        print("• Comprehensive workload impact analysis")
        print("• Contextual notification generation")
        print("• Proactive capacity monitoring")
        print("• Integration with Slack and existing systems")
        print("\nTo integrate with your JIRA instance:")
        print("1. Configure JIRA webhook to send events to /webhooks/jira")
        print("2. Set up team configurations in config file")
        print("3. Configure Slack bot token and channels")
        print("4. Test with actual webhook payloads")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")


if __name__ == "__main__":
    main()