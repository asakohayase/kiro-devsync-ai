#!/usr/bin/env python3
"""
Simple test script to verify Slack templates work correctly.
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from devsync_ai.services.slack_templates import create_standup_message, create_pr_status_message
    from devsync_ai.services.pr_status_templates import create_pr_message_by_action
    from devsync_ai.services.jira_templates import create_jira_message
    from devsync_ai.services.alert_templates import create_alert_message
    print("✅ Successfully imported all template modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_standup_template():
    """Test daily standup template."""
    print("\n🧪 Testing Daily Standup Template...")
    
    data = {
        "date": "2025-08-12",
        "team": "DevSync Team",
        "stats": {
            "prs_merged": 3,
            "prs_open": 5,
            "tickets_completed": 7,
            "tickets_in_progress": 12,
            "commits": 23
        },
        "team_members": [
            {
                "name": "Alice",
                "status": "active",
                "yesterday": ["Completed user auth", "Fixed bug #123"],
                "today": ["Start payment integration", "Code review"],
                "blockers": []
            },
            {
                "name": "Bob",
                "status": "active",
                "yesterday": ["Database optimization"],
                "today": ["API documentation"],
                "blockers": ["Waiting for design approval"]
            }
        ],
        "action_items": ["Deploy staging environment", "Update documentation"]
    }
    
    try:
        message = create_standup_message(data)
        
        # Validate message structure
        assert "blocks" in message, "Message missing 'blocks'"
        assert "text" in message, "Message missing 'text'"
        assert len(message["blocks"]) > 0, "Message has no blocks"
        
        # Check for header
        header_found = False
        for block in message["blocks"]:
            if block.get("type") == "header":
                header_found = True
                break
        
        assert header_found, "No header block found"
        
        print(f"✅ Standup template created successfully with {len(message['blocks'])} blocks")
        return True
        
    except Exception as e:
        print(f"❌ Standup template failed: {e}")
        return False


def test_pr_templates():
    """Test PR status templates."""
    print("\n🧪 Testing PR Status Templates...")
    
    base_pr_data = {
        "id": 123,
        "title": "Add user authentication",
        "description": "Implements OAuth2 login flow",
        "author": "alice",
        "status": "open",
        "reviewers": ["bob", "carol"],
        "approved_by": [],
        "files_changed": 12,
        "additions": 234,
        "deletions": 45,
        "created_at": "2025-08-12T10:00:00Z",
        "ci_status": "passing"
    }
    
    test_scenarios = [
        ("opened", "New PR"),
        ("ready_for_review", "Ready for Review"),
        ("approved", "Approved PR"),
        ("has_conflicts", "PR with Conflicts"),
        ("merged", "Merged PR"),
        ("closed", "Closed PR")
    ]
    
    success_count = 0
    
    for action, description in test_scenarios:
        try:
            # Customize data for specific scenarios
            pr_data = base_pr_data.copy()
            data = {"pr": pr_data, "action": action}
            
            if action == "approved":
                pr_data["approved_by"] = ["bob"]
            elif action == "has_conflicts":
                pr_data["has_conflicts"] = True
                pr_data["ci_status"] = "failing"
            elif action == "merged":
                pr_data["status"] = "merged"
                pr_data["approved_by"] = ["bob", "carol"]
                data["deployment_status"] = "deployed"
            elif action == "closed":
                pr_data["status"] = "closed"
                data["close_reason"] = "Superseded by another PR"
            
            message = create_pr_message_by_action(data)
            
            # Validate message structure
            assert "blocks" in message, f"{description}: Message missing 'blocks'"
            assert "text" in message, f"{description}: Message missing 'text'"
            assert len(message["blocks"]) > 0, f"{description}: Message has no blocks"
            
            print(f"✅ {description} template created with {len(message['blocks'])} blocks")
            success_count += 1
            
        except Exception as e:
            print(f"❌ {description} template failed: {e}")
    
    return success_count == len(test_scenarios)


def test_jira_templates():
    """Test JIRA status templates."""
    print("\n🧪 Testing JIRA Templates...")
    
    jira_scenarios = [
        ("status_change", "Status Change"),
        ("priority_change", "Priority Change"),
        ("assignment_change", "Assignment Change"),
        ("comment_added", "Comment Added"),
        ("blocker_identified", "Blocker Identified"),
        ("sprint_change", "Sprint Change")
    ]
    
    success_count = 0
    
    for change_type, description in jira_scenarios:
        try:
            # Base JIRA ticket data
            data = {
                "ticket": {
                    "key": "DP-123",
                    "summary": f"Test {description}",
                    "assignee": "alice",
                    "priority": "Medium"
                },
                "change_type": change_type
            }
            
            # Add specific data for each change type
            if change_type == "status_change":
                data["ticket"]["status"] = {"from": "To Do", "to": "In Progress"}
            elif change_type == "priority_change":
                data["ticket"]["priority_change"] = {"from": "Low", "to": "High"}
            elif change_type == "assignment_change":
                data["ticket"]["assignment_change"] = {"from": "alice", "to": "bob"}
            elif change_type == "comment_added":
                data["ticket"]["comments"] = [{"author": "alice", "text": "Test comment"}]
            elif change_type == "blocker_identified":
                data["blocker"] = {"type": "identified", "description": "Test blocker"}
            elif change_type == "sprint_change":
                data["ticket"]["sprint_change"] = {"from": "Sprint 1", "to": "Sprint 2"}
            
            message = create_jira_message(data)
            
            # Validate message structure
            assert "blocks" in message, f"{description}: Message missing 'blocks'"
            assert "text" in message, f"{description}: Message missing 'text'"
            assert len(message["blocks"]) > 0, f"{description}: Message has no blocks"
            
            print(f"✅ {description} template created with {len(message['blocks'])} blocks")
            success_count += 1
            
        except Exception as e:
            print(f"❌ {description} template failed: {e}")
    
    return success_count == len(jira_scenarios)


def test_alert_templates():
    """Test alert templates."""
    print("\n🧪 Testing Alert Templates...")
    
    alert_scenarios = [
        ("build_failure", "Build Failure"),
        ("deployment_issue", "Deployment Issue"),
        ("security_vulnerability", "Security Vulnerability"),
        ("service_outage", "Service Outage"),
        ("critical_bug", "Critical Bug"),
        ("team_blocker", "Team Blocker"),
        ("dependency_issue", "Dependency Issue")
    ]
    
    success_count = 0
    
    for alert_type, description in alert_scenarios:
        try:
            # Base alert data
            data = {
                "alert": {
                    "id": f"ALERT-{hash(alert_type) % 1000}",
                    "type": alert_type,
                    "severity": "high",
                    "title": f"Test {description}",
                    "description": f"Test {description} alert",
                    "affected_systems": ["Test System"],
                    "impact": "Test impact",
                    "assigned_to": "test-team"
                }
            }
            
            message = create_alert_message(data)
            
            # Validate message structure
            assert "blocks" in message, f"{description}: Message missing 'blocks'"
            assert "text" in message, f"{description}: Message missing 'text'"
            assert len(message["blocks"]) > 0, f"{description}: Message has no blocks"
            
            print(f"✅ {description} template created with {len(message['blocks'])} blocks")
            success_count += 1
            
        except Exception as e:
            print(f"❌ {description} template failed: {e}")
    
    return success_count == len(alert_scenarios)


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n🧪 Testing Edge Cases...")
    
    try:
        # Empty standup data
        empty_standup = create_standup_message({})
        assert "blocks" in empty_standup
        print("✅ Empty standup data handled correctly")
        
        # Minimal PR data
        minimal_pr = create_pr_status_message({"pr": {}, "action": "opened"})
        assert "blocks" in minimal_pr
        print("✅ Minimal PR data handled correctly")
        
        # PR without ID
        no_id_pr = create_pr_status_message({
            "pr": {"title": "Test PR", "author": "alice"},
            "action": "opened"
        })
        assert "blocks" in no_id_pr
        print("✅ PR without ID handled correctly")
        
        # Empty JIRA data
        empty_jira = create_jira_message({"ticket": {}, "change_type": "status_change"})
        assert "blocks" in empty_jira
        print("✅ Empty JIRA data handled correctly")
        
        # Empty alert data
        empty_alert = create_alert_message({"alert": {}})
        assert "blocks" in empty_alert
        print("✅ Empty alert data handled correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Edge case testing failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 DevSync AI Slack Templates Test Suite")
    print("=" * 50)
    
    tests = [
        ("Standup Template", test_standup_template),
        ("PR Templates", test_pr_templates),
        ("JIRA Templates", test_jira_templates),
        ("Alert Templates", test_alert_templates),
        ("Edge Cases", test_edge_cases)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} tests...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} tests PASSED")
        else:
            print(f"❌ {test_name} tests FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 All tests passed! Templates are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())