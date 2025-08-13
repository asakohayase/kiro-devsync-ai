#!/usr/bin/env python3
"""Simple test script for the message formatter system."""

import json
from datetime import datetime
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.templates.standup_template import StandupTemplate


def test_standup_template():
    """Test the standup template with sample data."""
    print("🧪 Testing Standup Template")
    print("=" * 50)
    
    # Create template configuration
    config = TemplateConfig(
        team_id="engineering",
        branding={
            "team_name": "Engineering Team",
            "logo_emoji": "⚙️",
            "primary_color": "#1f77b4"
        },
        interactive_elements=True
    )
    
    # Create template instance
    template = StandupTemplate(config=config)
    
    # Sample standup data
    standup_data = {
        "date": "2025-08-12",
        "team": "DevSync Engineering",
        "team_health": 0.85,
        "sprint_progress": {
            "completed": 7,
            "total": 10
        },
        "stats": {
            "prs_merged": 3,
            "prs_open": 5,
            "tickets_closed": 8,
            "commits": 24
        },
        "team_members": [
            {
                "name": "Alice",
                "yesterday": "Completed user authentication module and fixed login bugs",
                "today": "Working on dashboard API endpoints",
                "blockers": []
            },
            {
                "name": "Bob", 
                "yesterday": "Reviewed PRs and updated documentation",
                "today": "Implementing notification system",
                "blockers": ["Waiting for API keys from DevOps"]
            },
            {
                "name": "Charlie",
                "yesterday": "Fixed database migration issues",
                "today": "Adding unit tests for new features",
                "blockers": []
            }
        ],
        "action_items": [
            {
                "title": "Set up staging environment",
                "assignee": "DevOps",
                "due_date": "2025-08-15"
            },
            {
                "title": "Review security audit findings",
                "assignee": "Alice",
                "due_date": "2025-08-14"
            }
        ]
    }
    
    try:
        # Format the message
        message = template.format_message(standup_data)
        
        print("✅ Message formatted successfully!")
        print(f"📝 Fallback text: {message.text[:100]}...")
        print(f"🧱 Number of blocks: {len(message.blocks)}")
        print(f"📊 Metadata: {json.dumps(message.metadata, indent=2)}")
        
        # Print formatted blocks for inspection
        print("\n🎨 Formatted Slack Blocks:")
        print("-" * 30)
        for i, block in enumerate(message.blocks):
            print(f"Block {i+1}: {block.get('type', 'unknown')}")
            if block.get('type') == 'header':
                print(f"  Header: {block['text']['text']}")
            elif block.get('type') == 'section':
                if 'text' in block:
                    text = block['text']['text'][:100]
                    print(f"  Text: {text}...")
                if 'fields' in block:
                    print(f"  Fields: {len(block['fields'])} items")
            elif block.get('type') == 'actions':
                print(f"  Actions: {len(block['elements'])} buttons")
        
        print("\n🎉 Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """Test error handling with missing data."""
    print("\n🧪 Testing Error Handling")
    print("=" * 50)
    
    template = StandupTemplate()
    
    # Test with minimal/missing data
    minimal_data = {
        "date": "2025-08-12"
        # Missing required 'team' and 'team_members'
    }
    
    try:
        message = template.format_message(minimal_data)
        print("✅ Error handling works - message created with placeholders")
        print(f"📝 Fallback text: {message.text[:100]}...")
        print(f"🧱 Number of blocks: {len(message.blocks)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 DevSync AI Message Formatter Test Suite")
    print("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    # Run tests
    if test_standup_template():
        success_count += 1
    
    if test_error_handling():
        success_count += 1
    
    # Summary
    print("\n📊 Test Results:")
    print("=" * 30)
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All tests passed! Message formatter is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")