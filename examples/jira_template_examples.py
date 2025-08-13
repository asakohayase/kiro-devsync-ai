"""
Example usage of JIRA message templates for DevSync AI.
Demonstrates how to create and send different types of JIRA notifications.
"""

import json
from datetime import datetime, timedelta
from devsync_ai.services.jira_templates import (
    create_jira_message,
    create_status_change_message,
    create_priority_change_message,
    create_assignment_change_message,
    create_comment_message,
    create_blocker_message,
    create_sprint_change_message
)


def example_status_change():
    """Example JIRA status change notification."""
    print("=== JIRA Status Change Example ===")
    
    data = {
        "ticket": {
            "key": "DEVSYNC-456",
            "summary": "Implement user profile management system",
            "description": "Create comprehensive user profile management with avatar upload, privacy settings, and validation.",
            "status": {
                "from": "To Do",
                "to": "In Progress"
            },
            "priority": "High",
            "assignee": "alice.johnson",
            "reporter": "product.manager",
            "sprint": "Sprint 5 - User Features",
            "epic": "User Management Epic",
            "story_points": 8,
            "time_spent": "0h",
            "time_remaining": "16h",
            "created": (datetime.now() - timedelta(days=2)).isoformat() + "Z",
            "updated": datetime.now().isoformat() + "Z",
            "comments": [
                {
                    "author": "alice.johnson",
                    "text": "Starting work on this now. Will begin with the profile creation flow.",
                    "created": datetime.now().isoformat() + "Z"
                }
            ]
        },
        "change_type": "status_change"
    }
    
    message = create_status_change_message(data)
    print(json.dumps(message, indent=2))
    return message


def example_priority_change():
    """Example JIRA priority change notification."""
    print("\n=== JIRA Priority Change Example ===")
    
    data = {
        "ticket": {
            "key": "DEVSYNC-789",
            "summary": "Critical security vulnerability in authentication",
            "description": "SQL injection vulnerability discovered in login endpoint. Needs immediate attention.",
            "priority_change": {
                "from": "Medium",
                "to": "Blocker"
            },
            "priority": "Blocker",
            "assignee": "security.team",
            "reporter": "qa.engineer",
            "sprint": "Current Sprint",
            "epic": "Security Hardening",
            "story_points": 5,
            "time_spent": "2h",
            "time_remaining": "6h",
            "created": (datetime.now() - timedelta(days=1)).isoformat() + "Z",
            "updated": datetime.now().isoformat() + "Z",
            "comments": [
                {
                    "author": "security.lead",
                    "text": "Escalating to blocker priority. This needs to be fixed before next release.",
                    "created": datetime.now().isoformat() + "Z"
                }
            ]
        },
        "change_type": "priority_change"
    }
    
    message = create_priority_change_message(data)
    print(json.dumps(message, indent=2))
    return message


def example_assignment_change():
    """Example JIRA assignment change notification."""
    print("\n=== JIRA Assignment Change Example ===")
    
    data = {
        "ticket": {
            "key": "DEVSYNC-321",
            "summary": "Optimize database query performance",
            "description": "Several queries are running slowly in production. Need to analyze and optimize.",
            "assignment_change": {
                "from": "junior.dev",
                "to": "senior.dba"
            },
            "assignee": "senior.dba",
            "reporter": "performance.team",
            "priority": "High",
            "sprint": "Performance Sprint",
            "epic": "Database Optimization",
            "story_points": 13,
            "time_spent": "4h",
            "time_remaining": "20h",
            "created": (datetime.now() - timedelta(days=3)).isoformat() + "Z",
            "updated": datetime.now().isoformat() + "Z",
            "comments": [
                {
                    "author": "tech.lead",
                    "text": "Reassigning to DBA team as this requires deep database expertise.",
                    "created": datetime.now().isoformat() + "Z"
                }
            ]
        },
        "change_type": "assignment_change"
    }
    
    message = create_assignment_change_message(data)
    print(json.dumps(message, indent=2))
    return message


def example_new_comment():
    """Example JIRA new comment notification."""
    print("\n=== JIRA New Comment Example ===")
    
    data = {
        "ticket": {
            "key": "DEVSYNC-654",
            "summary": "Implement real-time chat feature",
            "description": "Add real-time chat functionality using WebSockets for team collaboration.",
            "assignee": "frontend.dev",
            "reporter": "product.owner",
            "priority": "Medium",
            "sprint": "Communication Features Sprint",
            "epic": "Team Collaboration",
            "story_points": 21,
            "time_spent": "12h",
            "time_remaining": "24h",
            "created": (datetime.now() - timedelta(weeks=1)).isoformat() + "Z",
            "updated": datetime.now().isoformat() + "Z",
            "comments": [
                {
                    "author": "backend.dev",
                    "text": "I've set up the WebSocket server infrastructure. The endpoints are ready for frontend integration. Here are the connection details:\n\n- WebSocket URL: wss://api.devsync.com/chat\n- Authentication: Bearer token in header\n- Message format: JSON with 'type' and 'payload' fields\n\nLet me know if you need any clarification on the API!",
                    "created": datetime.now().isoformat() + "Z"
                },
                {
                    "author": "frontend.dev",
                    "text": "Thanks! I'll start integrating this today.",
                    "created": (datetime.now() - timedelta(hours=2)).isoformat() + "Z"
                }
            ]
        },
        "change_type": "comment_added"
    }
    
    message = create_comment_message(data)
    print(json.dumps(message, indent=2))
    return message


def example_blocker_identified():
    """Example JIRA blocker identified notification."""
    print("\n=== JIRA Blocker Identified Example ===")
    
    data = {
        "ticket": {
            "key": "DEVSYNC-987",
            "summary": "Integrate with third-party payment processor",
            "description": "Implement Stripe payment integration for subscription billing.",
            "assignee": "payments.dev",
            "reporter": "business.analyst",
            "priority": "High",
            "sprint": "Billing Sprint",
            "epic": "Payment System",
            "story_points": 8,
            "time_spent": "6h",
            "time_remaining": "10h",
            "created": (datetime.now() - timedelta(days=4)).isoformat() + "Z",
            "updated": datetime.now().isoformat() + "Z",
            "comments": [
                {
                    "author": "payments.dev",
                    "text": "Blocked on getting API credentials from Stripe. Business team needs to complete the merchant verification process first.",
                    "created": datetime.now().isoformat() + "Z"
                }
            ]
        },
        "blocker": {
            "type": "identified",
            "description": "Waiting for Stripe merchant verification and API credentials from business team. Cannot proceed with integration without proper API access."
        },
        "change_type": "blocker_identified"
    }
    
    message = create_blocker_message(data, "identified")
    print(json.dumps(message, indent=2))
    return message


def example_blocker_resolved():
    """Example JIRA blocker resolved notification."""
    print("\n=== JIRA Blocker Resolved Example ===")
    
    data = {
        "ticket": {
            "key": "DEVSYNC-987",
            "summary": "Integrate with third-party payment processor",
            "description": "Implement Stripe payment integration for subscription billing.",
            "assignee": "payments.dev",
            "reporter": "business.analyst",
            "priority": "High",
            "sprint": "Billing Sprint",
            "epic": "Payment System",
            "story_points": 8,
            "time_spent": "6h",
            "time_remaining": "8h",
            "created": (datetime.now() - timedelta(days=4)).isoformat() + "Z",
            "updated": datetime.now().isoformat() + "Z",
            "comments": [
                {
                    "author": "business.analyst",
                    "text": "Great news! Stripe verification is complete and API credentials have been provided. You can now proceed with the integration.",
                    "created": datetime.now().isoformat() + "Z"
                }
            ]
        },
        "blocker": {
            "type": "resolved",
            "description": "Stripe merchant verification completed successfully. API credentials received and integration can now proceed."
        },
        "change_type": "blocker_resolved"
    }
    
    message = create_blocker_message(data, "resolved")
    print(json.dumps(message, indent=2))
    return message


def example_sprint_change():
    """Example JIRA sprint change notification."""
    print("\n=== JIRA Sprint Change Example ===")
    
    data = {
        "ticket": {
            "key": "DEVSYNC-147",
            "summary": "Implement advanced search filters",
            "description": "Add advanced filtering options to the main search functionality including date ranges, categories, and custom fields.",
            "assignee": "search.specialist",
            "reporter": "ux.designer",
            "priority": "Medium",
            "sprint_change": {
                "from": "Search Sprint 1",
                "to": "Search Sprint 2",
                "type": "moved"
            },
            "sprint": "Search Sprint 2",
            "epic": "Search Enhancement",
            "story_points": 13,
            "time_spent": "8h",
            "time_remaining": "18h",
            "created": (datetime.now() - timedelta(weeks=2)).isoformat() + "Z",
            "updated": datetime.now().isoformat() + "Z",
            "comments": [
                {
                    "author": "scrum.master",
                    "text": "Moving to next sprint due to dependency on search infrastructure changes that are still in progress.",
                    "created": datetime.now().isoformat() + "Z"
                }
            ]
        },
        "sprint_info": {
            "name": "Search Sprint 2",
            "start_date": "2025-08-19",
            "end_date": "2025-09-02",
            "capacity": 80,
            "committed_points": 65
        },
        "change_type": "sprint_change"
    }
    
    message = create_sprint_change_message(data)
    print(json.dumps(message, indent=2))
    return message


def example_complex_ticket_update():
    """Example of a complex ticket with multiple updates."""
    print("\n=== Complex JIRA Ticket Example ===")
    
    data = {
        "ticket": {
            "key": "DEVSYNC-555",
            "summary": "Migrate legacy user authentication system",
            "description": "Migrate from custom authentication to OAuth2 with backward compatibility. This is a critical infrastructure change affecting all users.",
            "status": {
                "from": "In Progress",
                "to": "Code Review"
            },
            "priority": "Critical",
            "assignee": "auth.architect",
            "reporter": "security.lead",
            "sprint": "Security Migration Sprint",
            "epic": "Authentication Overhaul",
            "story_points": 34,
            "time_spent": "45h 30m",
            "time_remaining": "12h",
            "created": (datetime.now() - timedelta(weeks=3)).isoformat() + "Z",
            "updated": datetime.now().isoformat() + "Z",
            "comments": [
                {
                    "author": "auth.architect",
                    "text": "Migration is complete! All tests are passing and backward compatibility is maintained. Ready for code review.",
                    "created": datetime.now().isoformat() + "Z"
                },
                {
                    "author": "qa.lead",
                    "text": "I'll start the security review process immediately.",
                    "created": (datetime.now() - timedelta(minutes=15)).isoformat() + "Z"
                },
                {
                    "author": "security.lead",
                    "text": "Excellent work! This was a complex migration. Please ensure all edge cases are covered in the test suite.",
                    "created": (datetime.now() - timedelta(minutes=30)).isoformat() + "Z"
                }
            ]
        },
        "change_type": "status_change"
    }
    
    message = create_status_change_message(data)
    print(json.dumps(message, indent=2))
    return message


def example_batch_jira_notifications():
    """Example of creating multiple JIRA notifications for a workflow."""
    print("\n=== Batch JIRA Notifications Example ===")
    
    notifications = []
    
    # Status change
    status_change = example_status_change()
    notifications.append(("status_change", status_change))
    
    # Priority escalation
    priority_change = example_priority_change()
    notifications.append(("priority_change", priority_change))
    
    # Assignment change
    assignment_change = example_assignment_change()
    notifications.append(("assignment_change", assignment_change))
    
    # New comment
    new_comment = example_new_comment()
    notifications.append(("comment_added", new_comment))
    
    # Blocker identified
    blocker_identified = example_blocker_identified()
    notifications.append(("blocker_identified", blocker_identified))
    
    # Blocker resolved
    blocker_resolved = example_blocker_resolved()
    notifications.append(("blocker_resolved", blocker_resolved))
    
    # Sprint change
    sprint_change = example_sprint_change()
    notifications.append(("sprint_change", sprint_change))
    
    print(f"\nGenerated {len(notifications)} JIRA notifications")
    return notifications


def example_webhook_integration():
    """Example of webhook integration for JIRA events."""
    print("\n=== JIRA Webhook Integration Example ===")
    
    # Simulate JIRA webhook payload
    webhook_payload = {
        "webhookEvent": "jira:issue_updated",
        "issue_event_type_name": "issue_assigned",
        "issue": {
            "key": "DEVSYNC-999",
            "fields": {
                "summary": "Webhook integration test",
                "description": "Testing webhook integration with DevSync AI",
                "assignee": {
                    "displayName": "webhook.tester",
                    "emailAddress": "webhook@devsync.com"
                },
                "reporter": {
                    "displayName": "system.admin"
                },
                "priority": {
                    "name": "Medium"
                },
                "status": {
                    "name": "To Do"
                },
                "customfield_10020": "Sprint 10",  # Sprint field
                "customfield_10014": "Webhook Epic",  # Epic field
                "timetracking": {
                    "timeSpent": "2h",
                    "remainingEstimate": "6h"
                },
                "created": datetime.now().isoformat() + "Z",
                "updated": datetime.now().isoformat() + "Z"
            }
        },
        "changelog": {
            "items": [
                {
                    "field": "assignee",
                    "fromString": "old.assignee",
                    "toString": "webhook.tester"
                }
            ]
        }
    }
    
    # Convert webhook payload to our template format
    def convert_webhook_to_template_data(payload):
        """Convert JIRA webhook payload to template data format."""
        issue = payload["issue"]
        fields = issue["fields"]
        changelog = payload.get("changelog", {})
        
        # Determine change type from changelog
        change_type = "updated"
        assignment_change = None
        
        for item in changelog.get("items", []):
            if item["field"] == "assignee":
                change_type = "assignment_change"
                assignment_change = {
                    "from": item.get("fromString", "Unassigned"),
                    "to": item.get("toString", "Unassigned")
                }
        
        template_data = {
            "ticket": {
                "key": issue["key"],
                "summary": fields["summary"],
                "description": fields.get("description", ""),
                "assignee": fields.get("assignee", {}).get("displayName", "Unassigned"),
                "reporter": fields.get("reporter", {}).get("displayName", "Unknown"),
                "priority": fields.get("priority", {}).get("name", "Medium"),
                "sprint": fields.get("customfield_10020", ""),
                "epic": fields.get("customfield_10014", ""),
                "time_spent": fields.get("timetracking", {}).get("timeSpent", "0h"),
                "time_remaining": fields.get("timetracking", {}).get("remainingEstimate", "0h"),
                "created": fields["created"],
                "updated": fields["updated"]
            },
            "change_type": change_type
        }
        
        if assignment_change:
            template_data["ticket"]["assignment_change"] = assignment_change
        
        return template_data
    
    # Convert and create message
    template_data = convert_webhook_to_template_data(webhook_payload)
    message = create_jira_message(template_data)
    
    print("Webhook payload converted to template:")
    print(json.dumps(template_data, indent=2))
    print("\nGenerated Slack message:")
    print(json.dumps(message, indent=2))
    
    return message


if __name__ == "__main__":
    print("DevSync AI JIRA Template Examples")
    print("=" * 50)
    
    # Run all examples
    example_status_change()
    example_priority_change()
    example_assignment_change()
    example_new_comment()
    example_blocker_identified()
    example_blocker_resolved()
    example_sprint_change()
    example_complex_ticket_update()
    example_webhook_integration()
    
    # Generate batch notifications
    batch = example_batch_jira_notifications()
    
    print("\n" + "=" * 50)
    print("All JIRA examples completed successfully!")
    print(f"Total messages generated: {len(batch) + 2}")  # +2 for complex and webhook examples