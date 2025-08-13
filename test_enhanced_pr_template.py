#!/usr/bin/env python3
"""Test the enhanced PR template with Block Kit builders."""

import json
from datetime import datetime
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.templates.enhanced_pr_template import EnhancedPRTemplate


def test_enhanced_pr_template():
    """Test enhanced PR template with comprehensive data."""
    print("🧪 Testing Enhanced PR Template with Block Kit Builders")
    print("=" * 60)
    
    config = TemplateConfig(
        team_id="engineering",
        branding={"team_name": "Engineering Team", "logo_emoji": "⚙️"},
        interactive_elements=True
    )
    
    template = EnhancedPRTemplate(config=config)
    
    # Comprehensive PR data
    pr_data = {
        "pr": {
            "number": 456,
            "title": "Implement advanced user dashboard with real-time analytics",
            "author": "alice",
            "head_branch": "feature/dashboard-analytics",
            "base_branch": "main",
            "priority": "high",
            "description": "This PR implements a comprehensive user dashboard with real-time analytics, including user activity tracking, performance metrics visualization, custom widget support, and responsive design for mobile devices. The implementation includes extensive unit tests and integration tests to ensure reliability.",
            "reviewers": ["bob", "charlie", "diana"],
            "labels": ["feature", "frontend", "analytics", "high-priority"],
            "files_changed": 23,
            "additions": 1247,
            "deletions": 89,
            "checks": {
                "passed": 8,
                "failed": 1,
                "pending": 2
            },
            "created_at": "2025-08-12T14:30:00Z",
            "url": "https://github.com/company/repo/pull/456"
        },
        "action": "ready_for_review"
    }
    
    try:
        message = template.format_message(pr_data)
        
        print("✅ Enhanced PR template formatted successfully!")
        print(f"📝 Fallback text preview: {message.text[:100]}...")
        print(f"🧱 Total blocks: {len(message.blocks)}")
        
        # Analyze block structure
        print("\n🏗️ Block Structure Analysis:")
        print("-" * 40)
        
        for i, block in enumerate(message.blocks):
            block_type = block.get('type', 'unknown')
            print(f"Block {i+1:2d}: {block_type}")
            
            if block_type == 'header':
                print(f"         Title: {block['text']['text']}")
            elif block_type == 'section':
                if 'text' in block:
                    text_preview = block['text']['text'][:60].replace('\n', ' ')
                    print(f"         Text: {text_preview}...")
                if 'fields' in block:
                    print(f"         Fields: {len(block['fields'])} items")
            elif block_type == 'actions':
                button_count = len(block.get('elements', []))
                button_labels = [elem['text']['text'] for elem in block.get('elements', [])]
                print(f"         Buttons: {button_count} ({', '.join(button_labels)})")
            elif block_type == 'context':
                element_count = len(block.get('elements', []))
                print(f"         Elements: {element_count} context items")
        
        # Show some specific block details
        print("\n🎨 Block Kit Features Demonstrated:")
        print("-" * 40)
        
        # Find header block
        header_blocks = [b for b in message.blocks if b.get('type') == 'header']
        if header_blocks:
            header_text = header_blocks[0]['text']['text']
            print(f"✅ Status-aware header: {header_text}")
        
        # Find field sections
        field_blocks = [b for b in message.blocks if b.get('type') == 'section' and 'fields' in b]
        if field_blocks:
            field_count = len(field_blocks[0]['fields'])
            print(f"✅ Structured fields: {field_count} field pairs")
        
        # Find action blocks
        action_blocks = [b for b in message.blocks if b.get('type') == 'actions']
        if action_blocks:
            total_buttons = sum(len(b.get('elements', [])) for b in action_blocks)
            print(f"✅ Interactive buttons: {total_buttons} total actions")
        
        # Check for confirmation dialogs
        has_confirmations = any(
            'confirm' in elem 
            for block in action_blocks 
            for elem in block.get('elements', [])
        )
        print(f"✅ Confirmation dialogs: {'Yes' if has_confirmations else 'No'}")
        
        # Check for rich text formatting
        rich_text_blocks = [
            b for b in message.blocks 
            if b.get('type') == 'section' and 
            b.get('text', {}).get('type') == 'mrkdwn' and
            ('*' in b.get('text', {}).get('text', '') or '`' in b.get('text', {}).get('text', ''))
        ]
        print(f"✅ Rich text formatting: {len(rich_text_blocks)} blocks with markdown")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced PR template test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_different_pr_statuses():
    """Test enhanced template with different PR statuses."""
    print("\n🧪 Testing Different PR Status Scenarios")
    print("=" * 50)
    
    template = EnhancedPRTemplate()
    
    # Test scenarios for different statuses
    scenarios = [
        {
            "name": "Draft PR",
            "action": "draft",
            "expected_features": ["draft status", "limited actions"]
        },
        {
            "name": "PR with Conflicts",
            "action": "conflicts",
            "expected_features": ["conflict warning", "resolve actions"]
        },
        {
            "name": "Approved PR",
            "action": "approved",
            "expected_features": ["merge button", "confirmation dialog"]
        },
        {
            "name": "Merged PR",
            "action": "merged",
            "expected_features": ["celebration message", "cleanup actions"]
        }
    ]
    
    base_pr_data = {
        "pr": {
            "number": 789,
            "title": "Test PR for status scenarios",
            "author": "test-user",
            "url": "https://github.com/test/repo/pull/789"
        }
    }
    
    success_count = 0
    
    for scenario in scenarios:
        print(f"\n📋 Testing: {scenario['name']}")
        print("-" * 30)
        
        test_data = {**base_pr_data, "action": scenario["action"]}
        
        try:
            message = template.format_message(test_data)
            print(f"✅ {scenario['name']} formatted successfully")
            print(f"   Blocks: {len(message.blocks)}")
            
            # Check for action buttons
            action_blocks = [b for b in message.blocks if b.get('type') == 'actions']
            if action_blocks:
                button_count = sum(len(b.get('elements', [])) for b in action_blocks)
                print(f"   Actions: {button_count} buttons available")
            
            success_count += 1
            
        except Exception as e:
            print(f"❌ {scenario['name']} failed: {e}")
    
    print(f"\n📊 Status scenarios: {success_count}/{len(scenarios)} passed")
    return success_count == len(scenarios)


def test_block_kit_features():
    """Test specific Block Kit features."""
    print("\n🧪 Testing Block Kit Feature Integration")
    print("=" * 50)
    
    template = EnhancedPRTemplate()
    
    # PR data with comprehensive features
    feature_test_data = {
        "pr": {
            "number": 999,
            "title": "Feature-rich PR for Block Kit testing",
            "author": "feature-tester",
            "head_branch": "feature/block-kit-test",
            "base_branch": "develop",
            "priority": "blocker",
            "description": "A" * 200,  # Long description to test truncation
            "reviewers": ["reviewer1", "reviewer2", "reviewer3", "reviewer4"],  # More than 3 reviewers
            "labels": ["urgent", "feature", "backend", "security", "testing"],  # More than 3 labels
            "files_changed": 42,
            "additions": 2500,
            "deletions": 150,
            "checks": {
                "passed": 12,
                "failed": 2,
                "pending": 1
            },
            "url": "https://github.com/test/feature-repo/pull/999"
        },
        "action": "approved"
    }
    
    try:
        message = template.format_message(feature_test_data)
        
        print("✅ Feature-rich PR formatted successfully")
        
        # Test specific features
        features_tested = []
        
        # Check for truncated reviewer list
        field_blocks = [b for b in message.blocks if b.get('type') == 'section' and 'fields' in b]
        if field_blocks:
            for field in field_blocks[0]['fields']:
                if 'Reviewers' in field['text'] and '+' in field['text']:
                    features_tested.append("Reviewer truncation")
                if 'Labels' in field['text'] and '+' in field['text']:
                    features_tested.append("Label truncation")
                if 'Priority' in field['text'] and '🚨' in field['text']:
                    features_tested.append("Blocker priority indicator")
        
        # Check for description handling
        description_blocks = [
            b for b in message.blocks 
            if b.get('type') == 'section' and 
            'Description:' in b.get('text', {}).get('text', '')
        ]
        if description_blocks:
            features_tested.append("Long description handling")
        
        # Check for checks section
        checks_blocks = [
            b for b in message.blocks 
            if b.get('type') == 'section' and 
            'Checks:' in b.get('text', {}).get('text', '')
        ]
        if checks_blocks:
            features_tested.append("Checks status display")
        
        # Check for confirmation dialogs
        action_blocks = [b for b in message.blocks if b.get('type') == 'actions']
        has_confirmations = any(
            'confirm' in elem 
            for block in action_blocks 
            for elem in block.get('elements', [])
        )
        if has_confirmations:
            features_tested.append("Confirmation dialogs")
        
        print(f"🎯 Block Kit features tested: {len(features_tested)}")
        for feature in features_tested:
            print(f"   ✅ {feature}")
        
        return len(features_tested) >= 4  # Expect at least 4 features
        
    except Exception as e:
        print(f"❌ Block Kit features test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Enhanced PR Template with Block Kit Builders Test Suite")
    print("=" * 70)
    
    success_count = 0
    total_tests = 3
    
    if test_enhanced_pr_template():
        success_count += 1
    
    if test_different_pr_statuses():
        success_count += 1
    
    if test_block_kit_features():
        success_count += 1
    
    # Summary
    print("\n📊 Test Results:")
    print("=" * 30)
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All enhanced PR template tests passed!")
        print("🏗️ Block Kit builders are working perfectly!")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")