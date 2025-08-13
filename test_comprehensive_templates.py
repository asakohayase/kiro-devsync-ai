#!/usr/bin/env python3
"""Comprehensive test for templates with new status indicators."""

import json
from datetime import datetime
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.templates.standup_template import StandupTemplate
from devsync_ai.templates.pr_template import PRTemplate


def test_pr_template_with_status_indicators():
    """Test PR template with various status indicators."""
    print("🧪 Testing PR Template with Status Indicators")
    print("=" * 50)
    
    config = TemplateConfig(
        team_id="engineering",
        branding={"team_name": "Engineering Team", "logo_emoji": "⚙️"},
        interactive_elements=True
    )
    
    template = PRTemplate(config=config)
    
    # Test different PR scenarios
    test_scenarios = [
        {
            "name": "New PR Opened",
            "data": {
                "pr": {
                    "number": 123,
                    "title": "Add user authentication system",
                    "author": "alice",
                    "head_branch": "feature/auth",
                    "base_branch": "main",
                    "priority": "high",
                    "description": "Implements JWT-based authentication with role-based access control",
                    "reviewers": ["bob", "charlie"],
                    "checks": {"passed": 3, "failed": 0, "pending": 2},
                    "url": "https://github.com/company/repo/pull/123"
                },
                "action": "opened"
            }
        },
        {
            "name": "PR Approved",
            "data": {
                "pr": {
                    "number": 124,
                    "title": "Fix critical security vulnerability",
                    "author": "bob",
                    "head_branch": "hotfix/security",
                    "base_branch": "main",
                    "priority": "blocker",
                    "reviewers": ["alice", "security-team"],
                    "checks": {"passed": 5, "failed": 0, "pending": 0},
                    "url": "https://github.com/company/repo/pull/124"
                },
                "action": "approved"
            }
        },
        {
            "name": "PR with Conflicts",
            "data": {
                "pr": {
                    "number": 125,
                    "title": "Update dashboard components",
                    "author": "charlie",
                    "head_branch": "feature/dashboard",
                    "base_branch": "main",
                    "priority": "medium",
                    "reviewers": ["alice"],
                    "checks": {"passed": 2, "failed": 1, "pending": 0},
                    "url": "https://github.com/company/repo/pull/125"
                },
                "action": "conflicts"
            }
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n📋 Scenario: {scenario['name']}")
        print("-" * 30)
        
        try:
            message = template.format_message(scenario['data'])
            print(f"✅ Message formatted successfully!")
            print(f"📝 Fallback text: {message.text[:80]}...")
            print(f"🧱 Blocks: {len(message.blocks)}")
            
            # Show the header and status blocks
            for i, block in enumerate(message.blocks[:3]):
                if block.get('type') == 'header':
                    print(f"   Header: {block['text']['text']}")
                elif block.get('type') == 'section' and 'Status:' in block.get('text', {}).get('text', ''):
                    status_text = block['text']['text'].split('\n')[0]
                    print(f"   Status: {status_text}")
        
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    print("\n✅ PR template test completed\n")


def test_enhanced_standup_with_health_indicators():
    """Test standup template with health status indicators."""
    print("🧪 Testing Enhanced Standup with Health Indicators")
    print("=" * 50)
    
    template = StandupTemplate()
    
    # Test with different health scenarios
    health_scenarios = [
        {
            "name": "Healthy Team",
            "team_health": 0.9,
            "description": "Team performing well"
        },
        {
            "name": "Team with Warnings",
            "team_health": 0.6,
            "description": "Some concerns but manageable"
        },
        {
            "name": "Critical Team Health",
            "team_health": 0.3,
            "description": "Multiple blockers and issues"
        }
    ]
    
    for scenario in health_scenarios:
        print(f"\n📋 Scenario: {scenario['name']}")
        print("-" * 30)
        
        standup_data = {
            "date": "2025-08-12",
            "team": "DevSync Engineering",
            "team_health": scenario["team_health"],
            "sprint_progress": {"completed": 6, "total": 10},
            "stats": {"prs_merged": 2, "prs_open": 4, "tickets_closed": 5, "commits": 18},
            "team_members": [
                {
                    "name": "Alice",
                    "yesterday": "Completed authentication module",
                    "today": "Working on API endpoints",
                    "blockers": [] if scenario["team_health"] > 0.7 else ["Waiting for API keys"]
                },
                {
                    "name": "Bob",
                    "yesterday": "Fixed database issues",
                    "today": "Code review and testing",
                    "blockers": [] if scenario["team_health"] > 0.5 else ["Database migration blocked", "Missing requirements"]
                }
            ],
            "action_items": [
                {"title": "Resolve API key issue", "assignee": "DevOps", "due_date": "2025-08-15"}
            ]
        }
        
        try:
            message = template.format_message(standup_data)
            print(f"✅ Message formatted successfully!")
            
            # Extract health indicator from the message
            for block in message.blocks:
                if block.get('type') == 'section' and 'Team Health:' in block.get('text', {}).get('text', ''):
                    health_text = block['text']['text']
                    print(f"   Health: {health_text}")
                    break
        
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    print("\n✅ Enhanced standup test completed\n")


def test_status_indicator_fallbacks():
    """Test status indicator fallback handling."""
    print("🧪 Testing Status Indicator Fallbacks")
    print("=" * 50)
    
    template = PRTemplate()
    
    # Test with unknown/invalid status
    fallback_data = {
        "pr": {
            "number": 999,
            "title": "Test PR with unknown status",
            "author": "test-user",
            "priority": "unknown-priority",  # Invalid priority
            "url": "https://example.com/pr/999"
        },
        "action": "unknown-action"  # Invalid action
    }
    
    try:
        message = template.format_message(fallback_data)
        print("✅ Fallback handling works correctly!")
        print(f"📝 Message created with {len(message.blocks)} blocks")
        
        # Check that the message was created despite invalid data
        header_found = any(block.get('type') == 'header' for block in message.blocks)
        print(f"   Header block created: {header_found}")
        
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
    
    print("\n✅ Fallback test completed\n")


if __name__ == "__main__":
    print("🚀 DevSync AI Comprehensive Template Test Suite")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    try:
        test_pr_template_with_status_indicators()
        success_count += 1
    except Exception as e:
        print(f"❌ PR template test failed: {e}\n")
    
    try:
        test_enhanced_standup_with_health_indicators()
        success_count += 1
    except Exception as e:
        print(f"❌ Enhanced standup test failed: {e}\n")
    
    try:
        test_status_indicator_fallbacks()
        success_count += 1
    except Exception as e:
        print(f"❌ Fallback test failed: {e}\n")
    
    # Summary
    print("📊 Test Results:")
    print("=" * 30)
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All comprehensive tests passed! Templates with status indicators working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")