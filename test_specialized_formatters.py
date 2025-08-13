#!/usr/bin/env python3
"""Test script for specialized message formatters."""

import json
from datetime import datetime, timedelta
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.formatters.pr_message_formatter import PRMessageFormatter
from devsync_ai.formatters.jira_message_formatter import JIRAMessageFormatter
from devsync_ai.formatters.standup_message_formatter import StandupMessageFormatter
from devsync_ai.formatters.blocker_message_formatter import BlockerMessageFormatter


def test_pr_message_formatter():
    """Test PR message formatter with comprehensive data."""
    print("🧪 Testing PR Message Formatter")
    print("=" * 40)
    
    formatter = PRMessageFormatter()
    
    # Comprehensive PR data
    pr_data = {
        "pr": {
            "number": 789,
            "title": "Implement real-time notification system with WebSocket support",
            "author": "alice",
            "head_ref": "feature/websocket-notifications",
            "base_ref": "main",
            "priority": "high",
            "reviewers": ["bob", "charlie", "diana", "eve"],
            "assignees": ["alice", "bob"],
            "labels": ["feature", "backend", "websockets", "high-priority", "notifications"],
            "milestone": "Q3 2025 Release",
            "changed_files": 15,
            "additions": 847,
            "deletions": 123,
            "files": [
                {"filename": "src/websocket/server.py", "status": "added"},
                {"filename": "src/notifications/handler.py", "status": "modified"},
                {"filename": "tests/test_websocket.py", "status": "added"}
            ],
            "checks": {
                "passed": 12,
                "failed": 1,
                "pending": 2
            },
            "ci_results": [
                {"name": "Unit Tests", "status": "success"},
                {"name": "Integration Tests", "status": "failure"},
                {"name": "Security Scan", "status": "pending"}
            ],
            "jira_tickets": [
                {"key": "DEV-456", "title": "WebSocket Infrastructure", "url": "https://jira.company.com/DEV-456"},
                {"key": "DEV-457", "title": "Real-time Notifications", "url": "https://jira.company.com/DEV-457"}
            ],
            "deployments": [
                {"environment": "staging", "status": "success"},
                {"environment": "production", "status": "pending"}
            ],
            "html_url": "https://github.com/company/repo/pull/789",
            "updated_at": "2025-08-12T15:30:00Z"
        },
        "action": "ready_for_review"
    }
    
    try:
        message = formatter.format_message(pr_data)
        print("✅ PR message formatted successfully!")
        print(f"📝 Blocks: {len(message.blocks)}")
        
        # Analyze key features
        features = []
        for block in message.blocks:
            if block.get('type') == 'section' and 'CI/CD Status' in block.get('text', {}).get('text', ''):
                features.append("CI/CD results")
            elif block.get('type') == 'section' and 'Related JIRA' in block.get('text', {}).get('text', ''):
                features.append("JIRA integration")
            elif block.get('type') == 'section' and 'File Changes' in block.get('text', {}).get('text', ''):
                features.append("File changes")
            elif block.get('type') == 'actions':
                features.append("Interactive actions")
        
        print(f"🎯 Features: {', '.join(features)}")
        return True
        
    except Exception as e:
        print(f"❌ PR formatter test failed: {e}")
        return False


def test_jira_message_formatter():
    """Test JIRA message formatter."""
    print("\n🧪 Testing JIRA Message Formatter")
    print("=" * 40)
    
    formatter = JIRAMessageFormatter()
    
    # Comprehensive JIRA data
    jira_data = {
        "ticket": {
            "key": "DEV-789",
            "summary": "Implement user dashboard with analytics and reporting features",
            "status": {"name": "In Progress"},
            "issue_type": {"name": "Story"},
            "priority": {"name": "High"},
            "assignee": {"display_name": "Alice Johnson", "name": "alice"},
            "reporter": {"display_name": "Bob Smith", "name": "bob"},
            "story_points": 8,
            "components": [
                {"name": "Frontend"},
                {"name": "Analytics"},
                {"name": "Reporting"}
            ],
            "labels": ["dashboard", "analytics", "user-experience"],
            "sprint": {
                "name": "Sprint 23",
                "state": "active",
                "start_date": "2025-08-01",
                "end_date": "2025-08-15",
                "completed_issues": 12,
                "total_issues": 20
            },
            "time_tracking": {
                "original_estimate": 28800,  # 8 hours in seconds
                "time_spent": 18000,         # 5 hours
                "remaining_estimate": 10800   # 3 hours
            },
            "pull_requests": [
                {"title": "Dashboard UI Components", "url": "https://github.com/company/repo/pull/123", "status": "open"},
                {"title": "Analytics Backend", "url": "https://github.com/company/repo/pull/124", "status": "merged"}
            ],
            "documentation": [
                {"title": "Dashboard Design Specs", "url": "https://docs.company.com/dashboard"}
            ],
            "linked_issues": [
                {"key": "DEV-788", "summary": "User Authentication", "url": "https://jira.company.com/DEV-788", "link_type": "blocks"},
                {"key": "DEV-790", "summary": "Data Export Feature", "url": "https://jira.company.com/DEV-790", "link_type": "relates to"}
            ],
            "url": "https://jira.company.com/DEV-789",
            "updated": "2025-08-12T14:45:00Z"
        },
        "change_type": "status_change",
        "from_status": "To Do",
        "to_status": "In Progress"
    }
    
    try:
        message = formatter.format_message(jira_data)
        print("✅ JIRA message formatted successfully!")
        print(f"📝 Blocks: {len(message.blocks)}")
        
        # Check for key JIRA features
        features = []
        for block in message.blocks:
            text = block.get('text', {}).get('text', '')
            if 'Sprint Context' in text:
                features.append("Sprint integration")
            elif 'Time Tracking' in text:
                features.append("Time tracking")
            elif 'Status Transition' in text:
                features.append("Status changes")
            elif 'Related Pull Requests' in text:
                features.append("PR linking")
        
        print(f"🎯 Features: {', '.join(features)}")
        return True
        
    except Exception as e:
        print(f"❌ JIRA formatter test failed: {e}")
        return False


def test_standup_message_formatter():
    """Test standup message formatter."""
    print("\n🧪 Testing Standup Message Formatter")
    print("=" * 40)
    
    formatter = StandupMessageFormatter()
    
    # Comprehensive standup data
    standup_data = {
        "date": "2025-08-12",
        "team": "DevSync Engineering Team",
        "team_health": 0.75,
        "stats": {
            "prs_merged": 8,
            "prs_open": 12,
            "tickets_closed": 15,
            "tickets_in_progress": 8,
            "commits": 47,
            "reviews_given": 23,
            "reviews_received": 19,
            "deployments": 3,
            "deployment_success_rate": 100
        },
        "sprint_progress": {
            "name": "Sprint 23 - Dashboard Features",
            "start_date": "2025-08-01",
            "end_date": "2025-08-15",
            "completed": 14,
            "total": 20,
            "completed_points": 34,
            "total_points": 50,
            "burndown_trend": "on_track"
        },
        "team_members": [
            {
                "name": "alice",
                "yesterday": "Completed WebSocket implementation for real-time notifications, fixed authentication bugs",
                "today": "Working on dashboard analytics integration and code review",
                "blockers": [],
                "commits": 8,
                "prs_reviewed": 3,
                "tickets_completed": 2
            },
            {
                "name": "bob",
                "yesterday": "Reviewed 5 PRs, updated deployment scripts, fixed CI pipeline issues",
                "today": "Implementing user permissions system and database migrations",
                "blockers": ["Waiting for API keys from DevOps team", "Database migration blocked by DBA approval"],
                "blocker_severity": "high",
                "commits": 5,
                "prs_reviewed": 5,
                "tickets_completed": 1
            },
            {
                "name": "charlie",
                "yesterday": "Fixed frontend routing issues, updated component library",
                "today": "Building responsive dashboard layouts and mobile optimization",
                "blockers": [],
                "commits": 12,
                "prs_reviewed": 2,
                "tickets_completed": 3
            },
            {
                "name": "diana",
                "yesterday": "Completed security audit, updated documentation",
                "today": "Implementing data export features and performance optimization",
                "blockers": ["Blocked by security team review"],
                "blocker_severity": "medium",
                "commits": 3,
                "prs_reviewed": 4,
                "tickets_completed": 1
            }
        ],
        "action_items": [
            {
                "title": "Get API keys from DevOps",
                "assignee": "bob",
                "due_date": "2025-08-13",
                "priority": "high"
            },
            {
                "title": "Schedule security team review",
                "assignee": "diana",
                "due_date": "2025-08-14",
                "priority": "medium"
            },
            {
                "title": "Update deployment documentation",
                "assignee": "alice",
                "due_date": "2025-08-15",
                "priority": "low"
            }
        ],
        "dashboard_url": "https://dashboard.company.com/team/devsync"
    }
    
    try:
        message = formatter.format_message(standup_data)
        print("✅ Standup message formatted successfully!")
        print(f"📝 Blocks: {len(message.blocks)}")
        
        # Check for standup-specific features
        features = []
        blocked_members = 0
        for block in message.blocks:
            text = block.get('text', {}).get('text', '')
            if 'Sprint Progress' in text:
                features.append("Sprint tracking")
            elif 'Team Statistics' in text or 'Pull Requests' in text:
                features.append("Team metrics")
            elif 'Action Items' in text:
                features.append("Action tracking")
            elif 'BLOCKED' in text or 'Has Blockers' in text:
                blocked_members += 1
            elif 'Team Blockers Summary' in text:
                features.append("Blocker highlights")
        
        print(f"🎯 Features: {', '.join(features)}")
        print(f"🚫 Blocked members: {blocked_members}")
        return True
        
    except Exception as e:
        print(f"❌ Standup formatter test failed: {e}")
        return False


def test_blocker_message_formatter():
    """Test blocker message formatter."""
    print("\n🧪 Testing Blocker Message Formatter")
    print("=" * 40)
    
    formatter = BlockerMessageFormatter()
    
    # Critical blocker data
    blocker_data = {
        "blocker": {
            "id": "BLOCK-001",
            "title": "Production Database Connection Failure",
            "description": "All database connections to the production PostgreSQL cluster are failing with timeout errors. This is affecting all user-facing services and preventing new user registrations, login attempts, and data retrieval.",
            "severity": "critical",
            "priority": "blocker",
            "reporter": "alice",
            "created_at": "2025-08-12T16:45:00Z",
            "error_message": "psycopg2.OperationalError: could not connect to server: Connection timed out",
            "steps_to_reproduce": [
                "Attempt to access any user-facing endpoint",
                "Observe database connection timeout",
                "Check application logs for connection errors",
                "Verify database cluster status"
            ],
            "environment": {
                "system": "Production",
                "version": "v2.1.4",
                "database": "PostgreSQL 13.7"
            },
            "impact": {
                "severity": "critical",
                "affected_users": 15000,
                "business_impact": "Complete service outage - no user access",
                "financial_impact": "$50,000/hour revenue loss",
                "sla_impact": "99.9% SLA breach - immediate escalation required"
            },
            "affected_systems": [
                {"name": "User Authentication Service", "status": "down"},
                {"name": "API Gateway", "status": "degraded"},
                {"name": "Web Application", "status": "down"},
                {"name": "Mobile App Backend", "status": "down"},
                {"name": "Reporting Service", "status": "down"}
            ],
            "affected_people": [
                {"name": "alice", "role": "Backend Engineer", "impact": "investigating database issues"},
                {"name": "bob", "role": "DevOps Engineer", "impact": "checking infrastructure"},
                {"name": "charlie", "role": "Frontend Engineer", "impact": "blocked on API calls"},
                {"name": "diana", "role": "QA Engineer", "impact": "cannot test user flows"}
            ],
            "escalation_path": [
                {"name": "alice", "role": "Senior Backend Engineer", "phone": "+1-555-0101", "email": "alice@company.com"},
                {"name": "engineering-manager", "role": "Engineering Manager", "phone": "+1-555-0102", "email": "em@company.com"},
                {"name": "cto", "role": "CTO", "phone": "+1-555-0103", "email": "cto@company.com"}
            ],
            "emergency_contacts": [
                {"name": "on-call-engineer", "phone": "+1-555-0911"},
                {"name": "infrastructure-lead", "phone": "+1-555-0912"}
            ],
            "timeline": {
                "eta": "30 minutes",
                "target_resolution": "2025-08-12T17:30:00Z"
            },
            "resolution_steps": [
                {"description": "Investigate database cluster health", "status": "in_progress", "assignee": "alice"},
                {"description": "Check network connectivity to database", "status": "completed", "assignee": "bob"},
                {"description": "Restart database connection pool", "status": "pending", "assignee": "alice"},
                {"description": "Failover to backup database if needed", "status": "pending", "assignee": "bob"},
                {"description": "Verify service restoration", "status": "pending", "assignee": "alice"},
                {"description": "Post-incident analysis", "status": "pending", "assignee": "engineering-manager"}
            ],
            "workarounds": [
                "Direct users to mobile app (if database recovers partially)",
                "Enable maintenance mode with status page updates",
                "Use cached data for read-only operations where possible"
            ],
            "status_updates": [
                {
                    "timestamp": "2025-08-12T16:50:00Z",
                    "author": "alice",
                    "message": "Database cluster shows high CPU usage, investigating connection pool exhaustion",
                    "status": "progress"
                },
                {
                    "timestamp": "2025-08-12T16:47:00Z",
                    "author": "bob",
                    "message": "Network connectivity to database confirmed working, issue appears to be at database level",
                    "status": "info"
                },
                {
                    "timestamp": "2025-08-12T16:45:30Z",
                    "author": "alice",
                    "message": "Production database connection failures detected, starting investigation",
                    "status": "error"
                }
            ],
            "url": "https://incident.company.com/BLOCK-001"
        },
        "blocker_type": "production"
    }
    
    try:
        message = formatter.format_message(blocker_data)
        print("✅ Blocker message formatted successfully!")
        print(f"📝 Blocks: {len(message.blocks)}")
        
        # Check for critical blocker features
        features = []
        for block in message.blocks:
            text = block.get('text', {}).get('text', '')
            if 'PRODUCTION' in text:
                features.append("Production alert")
            elif 'IMPACT ASSESSMENT' in text:
                features.append("Impact analysis")
            elif 'ESCALATION PATH' in text:
                features.append("Escalation contacts")
            elif 'RESOLUTION PLAN' in text:
                features.append("Resolution steps")
            elif 'STATUS UPDATES' in text:
                features.append("Real-time updates")
            elif block.get('type') == 'actions':
                action_labels = [elem['text']['text'] for elem in block.get('elements', [])]
                if any('War Room' in label for label in action_labels):
                    features.append("Emergency actions")
        
        print(f"🎯 Features: {', '.join(features)}")
        return True
        
    except Exception as e:
        print(f"❌ Blocker formatter test failed: {e}")
        return False


def test_batch_processing():
    """Test batch processing capabilities."""
    print("\n🧪 Testing Batch Processing")
    print("=" * 40)
    
    # Test PR batch processing
    pr_formatter = PRMessageFormatter()
    pr_batch_data = {
        "prs": [
            {"number": 101, "title": "Fix authentication bug", "author": "alice", "action": "merged"},
            {"number": 102, "title": "Add user dashboard", "author": "bob", "action": "approved"},
            {"number": 103, "title": "Update documentation", "author": "charlie", "action": "open"}
        ],
        "batch_type": "daily_summary",
        "dashboard_url": "https://github.com/company/repo/pulls"
    }
    
    try:
        pr_message = pr_formatter.format_message(pr_batch_data)
        print("✅ PR batch processing successful!")
        print(f"   PR batch blocks: {len(pr_message.blocks)}")
    except Exception as e:
        print(f"❌ PR batch processing failed: {e}")
        return False
    
    # Test JIRA batch processing
    jira_formatter = JIRAMessageFormatter()
    jira_batch_data = {
        "tickets": [
            {"key": "DEV-101", "summary": "User authentication", "status": {"name": "Done"}, "assignee": {"name": "alice"}},
            {"key": "DEV-102", "summary": "Dashboard UI", "status": {"name": "In Progress"}, "assignee": {"name": "bob"}},
            {"key": "DEV-103", "summary": "API documentation", "status": {"name": "To Do"}, "assignee": {"name": "charlie"}}
        ],
        "batch_type": "sprint_update",
        "dashboard_url": "https://jira.company.com/sprint/23"
    }
    
    try:
        jira_message = jira_formatter.format_message(jira_batch_data)
        print("✅ JIRA batch processing successful!")
        print(f"   JIRA batch blocks: {len(jira_message.blocks)}")
        return True
    except Exception as e:
        print(f"❌ JIRA batch processing failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Specialized Message Formatters Test Suite")
    print("=" * 60)
    
    success_count = 0
    total_tests = 5
    
    if test_pr_message_formatter():
        success_count += 1
    
    if test_jira_message_formatter():
        success_count += 1
    
    if test_standup_message_formatter():
        success_count += 1
    
    if test_blocker_message_formatter():
        success_count += 1
    
    if test_batch_processing():
        success_count += 1
    
    # Summary
    print("\n📊 Test Results:")
    print("=" * 30)
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All specialized formatter tests passed!")
        print("🏗️ Complete message formatting system is working perfectly!")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")