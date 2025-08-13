"""
Example usage of Slack message templates for DevSync AI.
Demonstrates how to create and send different types of notifications.
"""

import json
from datetime import datetime, timedelta
from devsync_ai.services.slack_templates import create_standup_message, create_pr_status_message
from devsync_ai.services.pr_status_templates import create_pr_message_by_action


def example_daily_standup():
    """Example daily standup message."""
    print("=== Daily Standup Example ===")
    
    data = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "team": "DevSync Engineering Team",
        "stats": {
            "prs_merged": 4,
            "prs_open": 8,
            "tickets_completed": 12,
            "tickets_in_progress": 15,
            "commits": 47
        },
        "team_members": [
            {
                "name": "Alice Johnson",
                "status": "active",
                "yesterday": [
                    "Completed OAuth2 integration",
                    "Fixed critical bug in payment processing",
                    "Code review for 3 PRs"
                ],
                "today": [
                    "Start work on user dashboard redesign",
                    "Meeting with product team at 2 PM",
                    "Deploy hotfix to production"
                ],
                "blockers": []
            },
            {
                "name": "Bob Smith",
                "status": "active",
                "yesterday": [
                    "Database performance optimization",
                    "Updated API documentation"
                ],
                "today": [
                    "Implement new search functionality",
                    "Write unit tests for recent changes"
                ],
                "blockers": [
                    "Waiting for design approval on search UI"
                ]
            },
            {
                "name": "Carol Davis",
                "status": "active",
                "yesterday": [
                    "Set up CI/CD pipeline improvements",
                    "Investigated production monitoring alerts"
                ],
                "today": [
                    "Deploy new monitoring dashboards",
                    "Team retrospective at 4 PM"
                ],
                "blockers": []
            },
            {
                "name": "David Wilson",
                "status": "away",
                "yesterday": [],
                "today": [],
                "blockers": []
            }
        ],
        "action_items": [
            "Deploy staging environment updates by EOD",
            "Update security documentation",
            "Schedule architecture review meeting",
            "Review and merge pending dependency updates"
        ]
    }
    
    message = create_standup_message(data)
    print(json.dumps(message, indent=2))
    return message


def example_new_pr():
    """Example new PR notification."""
    print("\n=== New PR Example ===")
    
    data = {
        "pr": {
            "id": 1247,
            "title": "Implement user profile management system",
            "description": "This PR adds a comprehensive user profile management system with the following features:\n\n- User profile creation and editing\n- Avatar upload functionality\n- Privacy settings management\n- Profile validation and error handling\n\nIncludes full test coverage and updated documentation.",
            "author": "alice.johnson",
            "status": "open",
            "draft": False,
            "reviewers": ["bob.smith", "carol.davis"],
            "approved_by": [],
            "changes_requested_by": [],
            "has_conflicts": False,
            "files_changed": 23,
            "additions": 1247,
            "deletions": 89,
            "created_at": datetime.now().isoformat() + "Z",
            "updated_at": datetime.now().isoformat() + "Z",
            "jira_tickets": ["DEVSYNC-456", "DEVSYNC-457"],
            "ci_status": "pending"
        },
        "action": "opened"
    }
    
    message = create_pr_message_by_action(data)
    print(json.dumps(message, indent=2))
    return message


def example_pr_ready_for_review():
    """Example PR ready for review notification."""
    print("\n=== PR Ready for Review Example ===")
    
    data = {
        "pr": {
            "id": 1248,
            "title": "Add real-time notifications system",
            "description": "Implements WebSocket-based real-time notifications for user actions, system events, and team updates.",
            "author": "bob.smith",
            "status": "open",
            "draft": False,
            "reviewers": ["alice.johnson", "carol.davis", "david.wilson"],
            "approved_by": [],
            "changes_requested_by": [],
            "has_conflicts": False,
            "files_changed": 15,
            "additions": 892,
            "deletions": 34,
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat() + "Z",
            "updated_at": datetime.now().isoformat() + "Z",
            "jira_tickets": ["DEVSYNC-501"],
            "ci_status": "passing"
        },
        "action": "ready_for_review"
    }
    
    message = create_pr_message_by_action(data)
    print(json.dumps(message, indent=2))
    return message


def example_pr_approved():
    """Example PR approved notification."""
    print("\n=== PR Approved Example ===")
    
    data = {
        "pr": {
            "id": 1249,
            "title": "Fix memory leak in background job processor",
            "description": "Resolves memory leak issue that was causing performance degradation in production.",
            "author": "carol.davis",
            "status": "open",
            "draft": False,
            "reviewers": ["alice.johnson", "bob.smith"],
            "approved_by": ["alice.johnson", "bob.smith"],
            "changes_requested_by": [],
            "has_conflicts": False,
            "files_changed": 8,
            "additions": 156,
            "deletions": 203,
            "created_at": (datetime.now() - timedelta(days=1)).isoformat() + "Z",
            "updated_at": (datetime.now() - timedelta(minutes=15)).isoformat() + "Z",
            "jira_tickets": ["DEVSYNC-502"],
            "ci_status": "passing",
            "required_approvals": 2
        },
        "action": "approved"
    }
    
    message = create_pr_message_by_action(data)
    print(json.dumps(message, indent=2))
    return message


def example_pr_conflicts():
    """Example PR with conflicts notification."""
    print("\n=== PR Conflicts Example ===")
    
    data = {
        "pr": {
            "id": 1250,
            "title": "Update authentication middleware",
            "description": "Updates authentication middleware to support new token format and improved security.",
            "author": "david.wilson",
            "status": "open",
            "draft": False,
            "reviewers": ["alice.johnson"],
            "approved_by": [],
            "changes_requested_by": [],
            "has_conflicts": True,
            "files_changed": 12,
            "additions": 345,
            "deletions": 123,
            "created_at": (datetime.now() - timedelta(days=2)).isoformat() + "Z",
            "updated_at": (datetime.now() - timedelta(hours=1)).isoformat() + "Z",
            "jira_tickets": ["DEVSYNC-503"],
            "ci_status": "failing"
        },
        "action": "has_conflicts"
    }
    
    message = create_pr_message_by_action(data)
    print(json.dumps(message, indent=2))
    return message


def example_pr_merged():
    """Example PR merged notification."""
    print("\n=== PR Merged Example ===")
    
    data = {
        "pr": {
            "id": 1251,
            "title": "Implement automated backup system",
            "description": "Adds automated daily backups with retention policies and monitoring.",
            "author": "alice.johnson",
            "status": "merged",
            "draft": False,
            "reviewers": ["bob.smith", "carol.davis"],
            "approved_by": ["bob.smith", "carol.davis"],
            "changes_requested_by": [],
            "has_conflicts": False,
            "files_changed": 18,
            "additions": 756,
            "deletions": 45,
            "created_at": (datetime.now() - timedelta(days=3)).isoformat() + "Z",
            "updated_at": datetime.now().isoformat() + "Z",
            "jira_tickets": ["DEVSYNC-504", "DEVSYNC-505"],
            "ci_status": "passing"
        },
        "action": "merged",
        "deployment_status": "deploying"
    }
    
    message = create_pr_message_by_action(data)
    print(json.dumps(message, indent=2))
    return message


def example_pr_closed():
    """Example PR closed notification."""
    print("\n=== PR Closed Example ===")
    
    data = {
        "pr": {
            "id": 1252,
            "title": "Experimental feature flag system",
            "description": "Prototype implementation of feature flag system for A/B testing.",
            "author": "bob.smith",
            "status": "closed",
            "draft": False,
            "reviewers": ["alice.johnson"],
            "approved_by": [],
            "changes_requested_by": ["alice.johnson"],
            "has_conflicts": False,
            "files_changed": 25,
            "additions": 1123,
            "deletions": 67,
            "created_at": (datetime.now() - timedelta(weeks=1)).isoformat() + "Z",
            "updated_at": datetime.now().isoformat() + "Z",
            "jira_tickets": ["DEVSYNC-506"],
            "ci_status": "passing"
        },
        "action": "closed",
        "close_reason": "Superseded by new architecture decision. Will be reimplemented in Q2."
    }
    
    message = create_pr_message_by_action(data)
    print(json.dumps(message, indent=2))
    return message


def example_batch_notifications():
    """Example of creating multiple notifications for a workflow."""
    print("\n=== Batch Notifications Example ===")
    
    # Simulate a day's worth of notifications
    notifications = []
    
    # Morning standup
    standup = example_daily_standup()
    notifications.append(("standup", standup))
    
    # New PR opened
    new_pr = example_new_pr()
    notifications.append(("new_pr", new_pr))
    
    # PR ready for review
    ready_pr = example_pr_ready_for_review()
    notifications.append(("ready_for_review", ready_pr))
    
    # PR approved
    approved_pr = example_pr_approved()
    notifications.append(("approved", approved_pr))
    
    # PR merged
    merged_pr = example_pr_merged()
    notifications.append(("merged", merged_pr))
    
    print(f"\nGenerated {len(notifications)} notifications for the day")
    return notifications


def example_custom_team_standup():
    """Example of customized standup for different team."""
    print("\n=== Custom Team Standup Example ===")
    
    data = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "team": "QA & Testing Team",
        "stats": {
            "prs_merged": 2,
            "prs_open": 3,
            "tickets_completed": 8,
            "tickets_in_progress": 6,
            "commits": 15
        },
        "team_members": [
            {
                "name": "Emma Thompson",
                "status": "active",
                "yesterday": [
                    "Completed regression testing for v2.1",
                    "Found and reported 3 critical bugs",
                    "Updated test automation scripts"
                ],
                "today": [
                    "Start testing new user onboarding flow",
                    "Review test coverage reports",
                    "Team planning meeting at 3 PM"
                ],
                "blockers": []
            },
            {
                "name": "Frank Rodriguez",
                "status": "active",
                "yesterday": [
                    "Set up performance testing environment",
                    "Analyzed load test results"
                ],
                "today": [
                    "Run stress tests on new API endpoints",
                    "Document performance benchmarks"
                ],
                "blockers": [
                    "Need production-like data for realistic testing"
                ]
            }
        ],
        "action_items": [
            "Set up automated smoke tests for staging",
            "Review and update test data management process",
            "Schedule cross-team testing coordination meeting"
        ]
    }
    
    message = create_standup_message(data)
    print(json.dumps(message, indent=2))
    return message


if __name__ == "__main__":
    print("DevSync AI Slack Template Examples")
    print("=" * 50)
    
    # Run all examples
    example_daily_standup()
    example_new_pr()
    example_pr_ready_for_review()
    example_pr_approved()
    example_pr_conflicts()
    example_pr_merged()
    example_pr_closed()
    example_custom_team_standup()
    
    # Generate batch notifications
    batch = example_batch_notifications()
    
    print("\n" + "=" * 50)
    print("All examples completed successfully!")
    print(f"Total messages generated: {len(batch) + 1}")  # +1 for custom team standup