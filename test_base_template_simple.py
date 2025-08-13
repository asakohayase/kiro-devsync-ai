#!/usr/bin/env python3
"""
Simple test script to verify base template system works correctly.
"""

import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from devsync_ai.core.base_template import (
        SlackMessageTemplate,
        MessageMetadata,
        TeamBranding,
        ChannelConfig,
        UserPreferences,
        AccessibilityOptions,
        MessagePriority,
        EmojiConstants,
        create_team_branding,
        create_channel_config,
        create_user_preferences,
        create_accessibility_options
    )
    print("✅ Successfully imported base template modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class TestTemplate(SlackMessageTemplate):
    """Test implementation of SlackMessageTemplate."""
    
    def _validate_data(self) -> None:
        """Validate test data."""
        if not self.data.get('title'):
            raise ValueError("Title is required")
    
    def _build_message_content(self) -> None:
        """Build test message content."""
        title = self.data.get('title', 'Test Message')
        description = self.data.get('description', '')
        
        self.add_section_block(f"*{title}*\n{description}")
        
        if self.data.get('show_fields'):
            fields = [
                {"type": "mrkdwn", "text": "*Field 1:* Value 1"},
                {"type": "mrkdwn", "text": "*Field 2:* Value 2"}
            ]
            self.add_fields_block(fields)
        
        if self.data.get('show_buttons'):
            buttons = [
                self.create_button("Test Button", "test_action", "test_value"),
                self.create_button("URL Button", "url_action", url="https://example.com")
            ]
            self.add_actions_block(buttons)
    
    def _get_header_text(self) -> str:
        """Get header text."""
        return "Test Template"
    
    def _get_header_emoji(self) -> str:
        """Get header emoji."""
        return EmojiConstants.INFO


def test_basic_template():
    """Test basic template creation."""
    print("\n🧪 Testing Basic Template Creation...")
    
    data = {"title": "Test Message", "description": "Test description"}
    template = TestTemplate(data)
    
    assert not template.has_errors(), f"Template has errors: {template.get_errors()}"
    assert len(template.blocks) > 0, "Template has no blocks"
    
    message = template.get_message()
    assert "blocks" in message, "Message missing 'blocks'"
    assert "text" in message, "Message missing 'text'"
    assert len(message["blocks"]) > 0, "Message has no blocks"
    
    print(f"✅ Basic template created with {len(template.blocks)} blocks")
    return True


def test_template_with_branding():
    """Test template with team branding."""
    print("\n🧪 Testing Template with Team Branding...")
    
    data = {"title": "Branded Message", "description": "Test with branding"}
    branding = create_team_branding(
        "Custom Team",
        primary_color="#ff0000",
        footer_text="Custom Footer"
    )
    
    template = TestTemplate(data, team_branding=branding)
    
    assert not template.has_errors(), f"Template has errors: {template.get_errors()}"
    message = template.get_message()
    
    # Check if footer contains custom text
    footer_found = False
    for block in message["blocks"]:
        if block.get("type") == "context":
            for element in block.get("elements", []):
                if "Custom Footer" in element.get("text", ""):
                    footer_found = True
    
    assert footer_found, "Custom footer text not found"
    print("✅ Template with team branding created successfully")
    return True


def test_template_with_accessibility():
    """Test template with accessibility options."""
    print("\n🧪 Testing Template with Accessibility Options...")
    
    data = {"title": "Accessible Message", "description": "Test accessibility"}
    accessibility = create_accessibility_options(
        screen_reader_optimized=True,
        high_contrast=True,
        alt_text_required=True
    )
    
    template = TestTemplate(data, accessibility_options=accessibility)
    
    assert not template.has_errors(), f"Template has errors: {template.get_errors()}"
    message = template.get_message()
    
    # Check if accessibility features are applied
    header_found = False
    for block in message["blocks"]:
        if block.get("type") == "header":
            text = block.get("text", {}).get("text", "")
            if text.startswith("Heading:"):
                header_found = True
    
    assert header_found, "Screen reader optimization not applied"
    print("✅ Template with accessibility options created successfully")
    return True


def test_template_with_compact_mode():
    """Test template with compact mode."""
    print("\n🧪 Testing Template with Compact Mode...")
    
    data = {"title": "Compact Message", "description": "Test compact mode"}
    channel_config = create_channel_config(
        "C123456",
        "test-channel",
        compact_mode=True,
        max_blocks=10
    )
    
    template = TestTemplate(data, channel_config=channel_config)
    
    assert not template.has_errors(), f"Template has errors: {template.get_errors()}"
    message = template.get_message()
    
    # In compact mode, header and footer should be hidden
    header_found = False
    footer_found = False
    
    for block in message["blocks"]:
        if block.get("type") == "header":
            header_found = True
        elif block.get("type") == "context":
            footer_found = True
    
    assert not header_found, "Header should be hidden in compact mode"
    assert not footer_found, "Footer should be hidden in compact mode"
    print("✅ Template with compact mode works correctly")
    return True


def test_error_handling():
    """Test error handling."""
    print("\n🧪 Testing Error Handling...")
    
    # Try to create template with missing required data
    invalid_data = {"description": "Missing title"}
    template = TestTemplate(invalid_data)
    
    assert template.has_errors(), "Template should have errors"
    assert "Title is required" in template.get_errors(), "Expected error message not found"
    
    # Should still create a message (error message)
    message = template.get_message()
    assert "blocks" in message, "Error message missing blocks"
    assert len(message["blocks"]) > 0, "Error message has no blocks"
    
    print("✅ Error handling works correctly")
    return True


def test_analytics_tracking():
    """Test analytics tracking."""
    print("\n🧪 Testing Analytics Tracking...")
    
    data = {"title": "Analytics Test", "description": "Test analytics"}
    
    # Create template with metadata
    metadata = MessageMetadata(
        template_name="test_template",
        template_version="2.0",
        user_id="U123456",
        priority=MessagePriority.HIGH,
        tags=["test", "analytics"]
    )
    
    template = TestTemplate(data, metadata=metadata)
    
    # Add custom analytics data
    template.add_analytics_data("test_key", "test_value")
    template.add_analytics_data("user_action", "button_click")
    
    analytics = template.get_analytics_data()
    
    assert analytics["template_name"] == "test_template"
    assert analytics["template_version"] == "2.0"
    assert analytics["priority"] == "high"
    assert analytics["tags"] == ["test", "analytics"]
    assert analytics["custom_data"]["test_key"] == "test_value"
    assert analytics["custom_data"]["user_action"] == "button_click"
    
    print("✅ Analytics tracking works correctly")
    return True


def test_helper_methods():
    """Test helper methods."""
    print("\n🧪 Testing Helper Methods...")
    
    data = {"title": "Helper Test", "description": "Test helpers"}
    template = TestTemplate(data)
    
    # Test progress bar
    progress = template._create_progress_bar(7, 10)
    assert "7/10" in progress, "Progress bar doesn't show correct values"
    assert "70%" in progress, "Progress bar doesn't show percentage"
    
    # Test text truncation
    long_text = "This is a very long text that should be truncated"
    truncated = template._truncate_text(long_text, max_length=20)
    assert len(truncated) <= 23, "Text not truncated properly"  # 20 + "..." length
    assert truncated.endswith("..."), "Truncated text doesn't end with ellipsis"
    
    # Test list formatting
    items = ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5", "Item 6"]
    formatted = template._format_list(items, max_items=3)
    assert "Item 1" in formatted, "First item not in formatted list"
    assert "and 3 more" in formatted, "Truncation message not found"
    
    print("✅ Helper methods work correctly")
    return True


def test_button_creation():
    """Test button creation."""
    print("\n🧪 Testing Button Creation...")
    
    data = {"title": "Button Test", "description": "Test buttons"}
    template = TestTemplate(data)
    
    # Test basic button
    button = template.create_button("Test Button", "test_action", "test_value")
    assert button["type"] == "button", "Button type incorrect"
    assert button["text"]["text"] == "Test Button", "Button text incorrect"
    assert button["action_id"] == "test_action", "Button action_id incorrect"
    assert button["value"] == "test_value", "Button value incorrect"
    
    # Test button with URL
    url_button = template.create_button("URL Button", "url_action", url="https://example.com")
    assert url_button["url"] == "https://example.com", "Button URL incorrect"
    
    # Test button with style and emoji
    styled_button = template.create_button("Styled", "styled_action", style="primary", emoji="🚀")
    assert styled_button["style"] == "primary", "Button style incorrect"
    assert "🚀" in styled_button["text"]["text"], "Button emoji not found"
    
    print("✅ Button creation works correctly")
    return True


def test_threading_support():
    """Test threading support."""
    print("\n🧪 Testing Threading Support...")
    
    data = {"title": "Thread Test", "description": "Test threading"}
    template = TestTemplate(data)
    
    # Initially not threaded
    assert not template.is_threaded_message(), "Template should not be threaded initially"
    
    # Set thread timestamp
    template.set_thread_ts("1234567890.123456")
    assert template.is_threaded_message(), "Template should be threaded after setting thread_ts"
    assert template.metadata.thread_ts == "1234567890.123456", "Thread timestamp not set correctly"
    
    # Check message includes thread_ts
    message = template.get_message()
    assert message.get("thread_ts") == "1234567890.123456", "Message doesn't include thread_ts"
    
    print("✅ Threading support works correctly")
    return True


def main():
    """Run all tests."""
    print("🚀 Base Template System Test Suite")
    print("=" * 50)
    
    tests = [
        ("Basic Template", test_basic_template),
        ("Team Branding", test_template_with_branding),
        ("Accessibility", test_template_with_accessibility),
        ("Compact Mode", test_template_with_compact_mode),
        ("Error Handling", test_error_handling),
        ("Analytics Tracking", test_analytics_tracking),
        ("Helper Methods", test_helper_methods),
        ("Button Creation", test_button_creation),
        ("Threading Support", test_threading_support)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} tests...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} tests PASSED")
            else:
                print(f"❌ {test_name} tests FAILED")
        except Exception as e:
            print(f"❌ {test_name} tests FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 All tests passed! Base template system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())