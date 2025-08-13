#!/usr/bin/env python3
"""Test script for Block Kit component builders."""

import json
from datetime import datetime
from devsync_ai.core.block_kit_builders import (
    BlockKitBuilder, HeaderConfig, SectionConfig, ContextConfig, 
    ActionButton, ButtonStyle, HeaderSize
)


def test_header_builder():
    """Test header builder with various configurations."""
    print("🧪 Testing Header Builder")
    print("=" * 40)
    
    builder = BlockKitBuilder()
    
    # Test comprehensive header
    header_config = HeaderConfig(
        title="Pull Request #123",
        status="ready_for_review",
        status_context="pr",
        timestamp=datetime(2025, 8, 12, 10, 30, 0),
        subtitle="Add user authentication system",
        description="This PR implements JWT-based authentication with role-based access control and comprehensive security measures.",
        actions=[
            ActionButton(
                label="👀 View PR",
                url="https://github.com/company/repo/pull/123",
                style=ButtonStyle.PRIMARY
            ),
            ActionButton(
                label="✅ Approve",
                action_id="approve_pr",
                value="123"
            ),
            ActionButton(
                label="❌ Request Changes",
                action_id="request_changes",
                value="123",
                style=ButtonStyle.DANGER,
                confirm={
                    "title": {"type": "plain_text", "text": "Request Changes"},
                    "text": {"type": "mrkdwn", "text": "Are you sure you want to request changes?"},
                    "confirm": {"type": "plain_text", "text": "Yes"},
                    "deny": {"type": "plain_text", "text": "Cancel"}
                }
            )
        ]
    )
    
    header_blocks = builder.build_header(header_config)
    
    print(f"✅ Header built with {len(header_blocks)} blocks")
    for i, block in enumerate(header_blocks):
        print(f"   Block {i+1}: {block['type']}")
        if block['type'] == 'header':
            print(f"      Title: {block['text']['text']}")
        elif block['type'] == 'actions':
            print(f"      Actions: {len(block['elements'])} buttons")
    
    print()


def test_section_builder():
    """Test section builder with rich text and fields."""
    print("🧪 Testing Section Builder")
    print("=" * 40)
    
    builder = BlockKitBuilder()
    
    # Rich text section
    rich_text = builder.build_rich_text_section(
        "This PR adds *authentication* to our system with `JWT tokens` and includes:\n"
        "• Role-based access control\n"
        "• Session management\n"
        "• Password hashing with bcrypt",
        mentions=["alice", "bob"],
        links={"https://jwt.io": "JWT documentation"}
    )
    
    print("✅ Rich text section created")
    print(f"   Content preview: {rich_text['text']['text'][:80]}...")
    
    # Field group section
    fields = {
        "Author": "@alice",
        "Reviewers": "@bob, @charlie",
        "Status": "Ready for Review",
        "Priority": "High",
        "Checks": "5 passed, 0 failed",
        "Branch": "feature/auth → main"
    }
    
    field_section = builder.build_field_group(fields)
    print(f"✅ Field group created with {len(field_section['fields'])} fields")
    
    print()


def test_action_buttons():
    """Test action button builder."""
    print("🧪 Testing Action Button Builder")
    print("=" * 40)
    
    builder = BlockKitBuilder()
    
    actions = [
        ActionButton(
            label="🚀 Deploy to Staging",
            action_id="deploy_staging",
            value="pr-123",
            style=ButtonStyle.PRIMARY
        ),
        ActionButton(
            label="🗑️ Delete Branch",
            action_id="delete_branch",
            value="feature/auth",
            style=ButtonStyle.DANGER,
            confirm=builder.create_confirmation_dialog(
                title="Delete Branch",
                text="Are you sure you want to delete the `feature/auth` branch? This action cannot be undone.",
                confirm_text="Delete",
                deny_text="Keep"
            )
        ),
        ActionButton(
            label="📊 View Metrics",
            url="https://metrics.company.com/pr/123"
        )
    ]
    
    action_block = builder.build_action_buttons(actions)
    print(f"✅ Action block created with {len(action_block['elements'])} buttons")
    
    for i, element in enumerate(action_block['elements']):
        button_text = element['text']['text']
        has_confirm = 'confirm' in element
        has_url = 'url' in element
        print(f"   Button {i+1}: {button_text} (confirm: {has_confirm}, url: {has_url})")
    
    print()


def test_context_builder():
    """Test context builder with metadata."""
    print("🧪 Testing Context Builder")
    print("=" * 40)
    
    builder = BlockKitBuilder()
    
    # Timestamp context
    timestamp_context = builder.build_timestamp_context(
        timestamp=datetime(2025, 8, 12, 15, 45, 30),
        author="alice",
        additional_info=["PR #123", "feature/auth branch", "2 files changed"]
    )
    
    print("✅ Timestamp context created")
    print(f"   Elements: {len(timestamp_context['elements'])}")
    
    # Custom context with images
    custom_context = builder.build_context(ContextConfig(
        elements=[
            "🔍 Code Review",
            "📈 +150 lines, -23 lines",
            "🧪 All tests passing"
        ],
        images=[
            {"url": "https://github.com/alice.png", "alt_text": "Alice's avatar"}
        ]
    ))
    
    print("✅ Custom context created with images")
    print(f"   Elements: {len(custom_context['elements'])}")
    
    print()


def test_progress_and_status():
    """Test progress and status indicators."""
    print("🧪 Testing Progress and Status Indicators")
    print("=" * 40)
    
    builder = BlockKitBuilder()
    
    # Progress section
    progress_section = builder.build_progress_section(
        completed=7,
        total=10,
        label="Sprint Progress",
        show_bar=True
    )
    
    print("✅ Progress section created")
    print(f"   Text: {progress_section['text']['text'].split('`')[0].strip()}")
    
    # Status section
    status_section = builder.build_status_section(
        status="approved",
        context="pr",
        additional_text="🚀 This PR is ready to be merged!"
    )
    
    print("✅ Status section created")
    print(f"   Text: {status_section['text']['text'].split('\\n')[0]}")
    
    print()


def test_data_structure_input():
    """Test using data structure input format."""
    print("🧪 Testing Data Structure Input")
    print("=" * 40)
    
    builder = BlockKitBuilder()
    
    # Example data structure as specified
    header_data = {
        "title": "Pull Request #123",
        "status": "ready_for_review",
        "status_context": "pr",
        "timestamp": datetime.fromisoformat("2025-08-12T10:30:00"),
        "actions": [
            {"label": "View PR", "url": "https://github.com/company/repo/pull/123"},
            {"label": "Approve", "action_id": "approve_pr", "style": "primary"}
        ]
    }
    
    # Build header from data structure
    header_blocks = builder.build_header(header_data)
    
    print("✅ Header built from data structure")
    print(f"   Blocks created: {len(header_blocks)}")
    
    # Build complete message structure
    complete_message = []
    
    # Add header
    complete_message.extend(header_blocks)
    
    # Add content section
    complete_message.append(builder.build_section({
        "text": "This PR implements user authentication with the following features:",
        "fields": {
            "Security": "JWT tokens with refresh",
            "Authorization": "Role-based access control",
            "Validation": "Input sanitization",
            "Testing": "100% test coverage"
        }
    }))
    
    # Add divider
    complete_message.append(builder.build_divider())
    
    # Add context
    complete_message.append(builder.build_timestamp_context(
        author="alice",
        additional_info=["2 files changed", "+150 -23 lines"]
    ))
    
    print(f"✅ Complete message structure: {len(complete_message)} blocks")
    
    # Show block types
    block_types = [block['type'] for block in complete_message]
    print(f"   Block sequence: {' → '.join(block_types)}")
    
    print()


def test_formatting_helpers():
    """Test text formatting helper methods."""
    print("🧪 Testing Formatting Helpers")
    print("=" * 40)
    
    builder = BlockKitBuilder()
    
    # Test various formatting helpers
    user_mention = builder.build_user_mention("alice")
    channel_ref = builder.build_channel_reference("general")
    url_link = builder.build_url_link("https://github.com", "GitHub")
    code_block = builder.build_code_block("console.log('Hello');", "javascript")
    
    print(f"✅ User mention: {user_mention}")
    print(f"✅ Channel reference: {channel_ref}")
    print(f"✅ URL link: {url_link}")
    print(f"✅ Code block: {code_block}")
    
    print()


if __name__ == "__main__":
    print("🚀 DevSync AI Block Kit Builders Test Suite")
    print("=" * 60)
    
    success_count = 0
    total_tests = 6
    
    try:
        test_header_builder()
        success_count += 1
    except Exception as e:
        print(f"❌ Header builder test failed: {e}\n")
    
    try:
        test_section_builder()
        success_count += 1
    except Exception as e:
        print(f"❌ Section builder test failed: {e}\n")
    
    try:
        test_action_buttons()
        success_count += 1
    except Exception as e:
        print(f"❌ Action buttons test failed: {e}\n")
    
    try:
        test_context_builder()
        success_count += 1
    except Exception as e:
        print(f"❌ Context builder test failed: {e}\n")
    
    try:
        test_progress_and_status()
        success_count += 1
    except Exception as e:
        print(f"❌ Progress and status test failed: {e}\n")
    
    try:
        test_data_structure_input()
        success_count += 1
    except Exception as e:
        print(f"❌ Data structure input test failed: {e}\n")
    
    try:
        test_formatting_helpers()
        success_count += 1
    except Exception as e:
        print(f"❌ Formatting helpers test failed: {e}\n")
    
    # Summary
    print("📊 Test Results:")
    print("=" * 30)
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All Block Kit builder tests passed!")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")