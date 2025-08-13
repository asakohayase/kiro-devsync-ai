"""
Tests for the base message template system.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from devsync_ai.core.base_template import (
    SlackMessageTemplate,
    MessageMetadata,
    TeamBranding,
    ChannelConfig,
    UserPreferences,
    AccessibilityOptions,
    MessagePriority,
    ColorScheme,
    EmojiConstants,
    IconConstants,
    create_team_branding,
    create_channel_config,
    create_user_preferences,
    create_accessibility_options
)


class TestSlackMessageTemplate(SlackMessageTemplate):
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


class TestMessageMetadata:
    """Test MessageMetadata dataclass."""
    
    def test_metadata_creation(self):
        """Test metadata creation with defaults."""
        metadata = MessageMetadata(template_name="test_template")
        
        assert metadata.template_name == "test_template"
        assert metadata.template_version == "1.0"
        assert isinstance(metadata.created_at, datetime)
        assert metadata.priority == MessagePriority.NORMAL
        assert metadata.tags == []
        assert metadata.custom_data == {}
    
    def test_metadata_with_custom_values(self):
        """Test metadata with custom values."""
        custom_time = datetime(2025, 8, 12, 10, 30)
        metadata = MessageMetadata(
            template_name="custom_template",
            template_version="2.0",
            created_at=custom_time,
            user_id="user123",
            priority=MessagePriority.HIGH,
            tags=["urgent", "test"],
            custom_data={"key": "value"}
        )
        
        assert metadata.template_name == "custom_template"
        assert metadata.template_version == "2.0"
        assert metadata.created_at == custom_time
        assert metadata.user_id == "user123"
        assert metadata.priority == MessagePriority.HIGH
        assert metadata.tags == ["urgent", "test"]
        assert metadata.custom_data == {"key": "value"}


class TestTeamBranding:
    """Test TeamBranding dataclass."""
    
    def test_team_branding_defaults(self):
        """Test team branding with defaults."""
        branding = TeamBranding(team_name="Test Team")
        
        assert branding.team_name == "Test Team"
        assert branding.primary_color == ColorScheme.PRIMARY.value
        assert branding.logo_url is None
        assert branding.footer_text is None
        assert branding.custom_emojis == {}
        assert branding.timezone == "UTC"
        assert branding.date_format == "%Y-%m-%d %H:%M"
    
    def test_team_branding_custom(self):
        """Test team branding with custom values."""
        branding = TeamBranding(
            team_name="Custom Team",
            primary_color="#ff0000",
            logo_url="https://example.com/logo.png",
            footer_text="Custom Footer",
            custom_emojis={"success": ":custom_success:"},
            timezone="America/New_York",
            date_format="%m/%d/%Y %I:%M %p"
        )
        
        assert branding.team_name == "Custom Team"
        assert branding.primary_color == "#ff0000"
        assert branding.logo_url == "https://example.com/logo.png"
        assert branding.footer_text == "Custom Footer"
        assert branding.custom_emojis == {"success": ":custom_success:"}
        assert branding.timezone == "America/New_York"
        assert branding.date_format == "%m/%d/%Y %I:%M %p"


class TestSlackMessageTemplateBase:
    """Test base SlackMessageTemplate functionality."""
    
    def test_basic_template_creation(self):
        """Test basic template creation."""
        data = {"title": "Test Message", "description": "Test description"}
        template = TestSlackMessageTemplate(data)
        
        assert not template.has_errors()
        assert len(template.blocks) > 0
        
        message = template.get_message()
        assert "blocks" in message
        assert "text" in message
        assert len(message["blocks"]) > 0
    
    def test_template_with_validation_error(self):
        """Test template with validation error."""
        data = {}  # Missing required title
        template = TestSlackMessageTemplate(data)
        
        assert template.has_errors()
        assert "Title is required" in template.get_errors()
        
        # Should still create error message
        message = template.get_message()
        assert "blocks" in message
        assert len(message["blocks"]) > 0
    
    def test_template_with_team_branding(self):
        """Test template with team branding."""
        data = {"title": "Branded Message"}
        branding = TeamBranding(
            team_name="Custom Team",
            primary_color="#ff0000",
            footer_text="Custom Footer"
        )
        
        template = TestSlackMessageTemplate(data, team_branding=branding)
        
        assert not template.has_errors()
        message = template.get_message()
        
        # Check if footer contains custom text
        footer_found = False
        for block in message["blocks"]:
            if block.get("type") == "context":
                for element in block.get("elements", []):
                    if "Custom Footer" in element.get("text", ""):
                        footer_found = True
        
        assert footer_found, "Custom footer text not found"
    
    def test_template_with_channel_config(self):
        """Test template with channel configuration."""
        data = {"title": "Channel Message"}
        channel_config = ChannelConfig(
            channel_id="C123456",
            channel_name="test-channel",
            compact_mode=True,
            max_blocks=10
        )
        
        template = TestSlackMessageTemplate(data, channel_config=channel_config)
        
        assert not template.has_errors()
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
    
    def test_template_with_user_preferences(self):
        """Test template with user preferences."""
        data = {"title": "User Message"}
        user_prefs = UserPreferences(
            user_id="user123",
            compact_mode=True,
            date_format="%m/%d/%Y"
        )
        
        template = TestSlackMessageTemplate(data, user_preferences=user_prefs)
        
        assert not template.has_errors()
        # Compact mode should affect header/footer visibility
        message = template.get_message()
        
        header_found = False
        for block in message["blocks"]:
            if block.get("type") == "header":
                header_found = True
        
        assert not header_found, "Header should be hidden with user compact mode"
    
    def test_template_with_accessibility_options(self):
        """Test template with accessibility options."""
        data = {"title": "Accessible Message"}
        accessibility = AccessibilityOptions(
            screen_reader_optimized=True,
            high_contrast=True,
            alt_text_required=True
        )
        
        template = TestSlackMessageTemplate(data, accessibility_options=accessibility)
        
        assert not template.has_errors()
        message = template.get_message()
        
        # Check if accessibility features are applied
        header_found = False
        for block in message["blocks"]:
            if block.get("type") == "header":
                text = block.get("text", {}).get("text", "")
                if text.startswith("Heading:"):
                    header_found = True
        
        assert header_found, "Screen reader optimization not applied"
    
    def test_block_validation(self):
        """Test block validation."""
        data = {"title": "Block Test"}
        template = TestSlackMessageTemplate(data)
        
        # Test valid block
        valid_block = {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "Valid block"}
        }
        assert template._validate_block(valid_block)
        
        # Test invalid block
        invalid_block = {"type": "section"}  # Missing text or fields
        assert not template._validate_block(invalid_block)
        
        # Test block without type
        no_type_block = {"text": {"type": "mrkdwn", "text": "No type"}}
        assert not template._validate_block(no_type_block)
    
    def test_block_limit_enforcement(self):
        """Test block limit enforcement."""
        data = {"title": "Block Limit Test"}
        channel_config = ChannelConfig(
            channel_id="C123456",
            channel_name="test-channel",
            max_blocks=3
        )
        
        template = TestSlackMessageTemplate(data, channel_config=channel_config)
        
        # Try to add more blocks than the limit
        for i in range(10):
            template.add_section_block(f"Block {i}")
        
        # Should not exceed the limit
        assert len(template.blocks) <= 3
        assert template.has_warnings()
        assert any("Block limit" in warning for warning in template.get_warnings())
    
    def test_progress_bar_creation(self):
        """Test progress bar creation."""
        data = {"title": "Progress Test"}
        template = TestSlackMessageTemplate(data)
        
        # Test normal progress bar
        progress = template._create_progress_bar(7, 10)
        assert "7/10" in progress
        assert "70%" in progress
        
        # Test with zero total
        progress_zero = template._create_progress_bar(0, 0)
        assert "No progress data" in progress_zero
        
        # Test with high contrast
        accessibility = AccessibilityOptions(high_contrast=True)
        template_hc = TestSlackMessageTemplate(data, accessibility_options=accessibility)
        progress_hc = template_hc._create_progress_bar(5, 10)
        assert "█" in progress_hc or "░" in progress_hc
    
    def test_text_formatting_helpers(self):
        """Test text formatting helper methods."""
        data = {"title": "Format Test"}
        template = TestSlackMessageTemplate(data)
        
        # Test text truncation
        long_text = "This is a very long text that should be truncated"
        truncated = template._truncate_text(long_text, max_length=20)
        assert len(truncated) <= 23  # 20 + "..." length
        assert truncated.endswith("...")
        
        # Test list formatting
        items = ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5", "Item 6"]
        formatted = template._format_list(items, max_items=3)
        assert "Item 1" in formatted
        assert "Item 2" in formatted
        assert "Item 3" in formatted
        assert "and 3 more" in formatted
        
        # Test empty list
        empty_formatted = template._format_list([])
        assert empty_formatted == "None"
    
    def test_fallback_text_generation(self):
        """Test fallback text generation."""
        data = {"title": "Fallback Test", "description": "Test description"}
        template = TestSlackMessageTemplate(data)
        
        message = template.get_message()
        assert message["text"]  # Should have fallback text
        assert "Fallback Test" in message["text"] or "Test description" in message["text"]
    
    def test_markdown_cleaning(self):
        """Test markdown cleaning for fallback text."""
        data = {"title": "Markdown Test"}
        template = TestSlackMessageTemplate(data)
        
        # Test various markdown formats
        markdown_text = "*bold* _italic_ `code` <https://example.com|link> <https://example.com>"
        cleaned = template._clean_markdown(markdown_text)
        
        assert "*" not in cleaned
        assert "_" not in cleaned
        assert "`" not in cleaned
        assert "bold" in cleaned
        assert "italic" in cleaned
        assert "code" in cleaned
        assert "link" in cleaned
    
    def test_threading_support(self):
        """Test threading support."""
        data = {"title": "Thread Test"}
        template = TestSlackMessageTemplate(data)
        
        # Initially not threaded
        assert not template.is_threaded_message()
        
        # Set thread timestamp
        template.set_thread_ts("1234567890.123456")
        assert template.is_threaded_message()
        assert template.metadata.thread_ts == "1234567890.123456"
        
        # Check message includes thread_ts
        message = template.get_message()
        assert message.get("thread_ts") == "1234567890.123456"
    
    def test_analytics_data(self):
        """Test analytics data collection."""
        data = {"title": "Analytics Test"}
        template = TestSlackMessageTemplate(data)
        
        # Add custom analytics data
        template.add_analytics_data("test_key", "test_value")
        template.add_analytics_data("user_action", "button_click")
        
        analytics = template.get_analytics_data()
        
        assert analytics["template_name"] == "TestSlackMessageTemplate"
        assert analytics["template_version"] == "1.0"
        assert "created_at" in analytics
        assert analytics["priority"] == "normal"
        assert analytics["block_count"] > 0
        assert analytics["custom_data"]["test_key"] == "test_value"
        assert analytics["custom_data"]["user_action"] == "button_click"
    
    def test_button_creation(self):
        """Test button creation helper."""
        data = {"title": "Button Test"}
        template = TestSlackMessageTemplate(data)
        
        # Test basic button
        button = template.create_button("Test Button", "test_action", "test_value")
        assert button["type"] == "button"
        assert button["text"]["text"] == "Test Button"
        assert button["action_id"] == "test_action"
        assert button["value"] == "test_value"
        
        # Test button with URL
        url_button = template.create_button("URL Button", "url_action", url="https://example.com")
        assert url_button["url"] == "https://example.com"
        
        # Test button with style and emoji
        styled_button = template.create_button("Styled", "styled_action", style="primary", emoji="🚀")
        assert styled_button["style"] == "primary"
        assert "🚀" in styled_button["text"]["text"]
    
    def test_image_block_with_accessibility(self):
        """Test image block with accessibility features."""
        data = {"title": "Image Test"}
        accessibility = AccessibilityOptions(alt_text_required=True)
        template = TestSlackMessageTemplate(data, accessibility_options=accessibility)
        
        # Add image without alt text
        template.add_image_block("https://example.com/image.png", "", "Test Image")
        
        # Should have warning about missing alt text
        assert template.has_warnings()
        
        # Check that default alt text was added
        image_blocks = [b for b in template.blocks if b.get("type") == "image"]
        assert len(image_blocks) > 0
        assert image_blocks[0].get("alt_text") == "Image content"
    
    def test_template_string_representations(self):
        """Test string representations of template."""
        data = {"title": "String Test"}
        template = TestSlackMessageTemplate(data)
        
        # Test __str__
        str_repr = str(template)
        assert "TestSlackMessageTemplate" in str_repr
        assert "blocks=" in str_repr
        assert "errors=" in str_repr
        
        # Test __repr__
        repr_str = repr(template)
        assert "TestSlackMessageTemplate" in repr_str
        assert "template_name=" in repr_str
        assert "blocks=" in repr_str
        assert "errors=" in repr_str
        assert "warnings=" in repr_str
    
    def test_json_serialization(self):
        """Test JSON serialization."""
        data = {"title": "JSON Test"}
        template = TestSlackMessageTemplate(data)
        
        json_str = template.to_json()
        assert isinstance(json_str, str)
        
        # Should be valid JSON
        import json
        parsed = json.loads(json_str)
        assert "blocks" in parsed
        assert "text" in parsed


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_team_branding(self):
        """Test create_team_branding utility."""
        branding = create_team_branding(
            "Test Team",
            primary_color="#ff0000",
            footer_text="Custom Footer"
        )
        
        assert isinstance(branding, TeamBranding)
        assert branding.team_name == "Test Team"
        assert branding.primary_color == "#ff0000"
        assert branding.footer_text == "Custom Footer"
    
    def test_create_channel_config(self):
        """Test create_channel_config utility."""
        config = create_channel_config(
            "C123456",
            "test-channel",
            compact_mode=True,
            max_blocks=20
        )
        
        assert isinstance(config, ChannelConfig)
        assert config.channel_id == "C123456"
        assert config.channel_name == "test-channel"
        assert config.compact_mode is True
        assert config.max_blocks == 20
    
    def test_create_user_preferences(self):
        """Test create_user_preferences utility."""
        prefs = create_user_preferences(
            "user123",
            timezone="America/New_York",
            compact_mode=True
        )
        
        assert isinstance(prefs, UserPreferences)
        assert prefs.user_id == "user123"
        assert prefs.timezone == "America/New_York"
        assert prefs.compact_mode is True
    
    def test_create_accessibility_options(self):
        """Test create_accessibility_options utility."""
        options = create_accessibility_options(
            high_contrast=True,
            screen_reader_optimized=True
        )
        
        assert isinstance(options, AccessibilityOptions)
        assert options.high_contrast is True
        assert options.screen_reader_optimized is True


class TestConstants:
    """Test constant definitions."""
    
    def test_emoji_constants(self):
        """Test emoji constants are defined."""
        assert EmojiConstants.SUCCESS == "✅"
        assert EmojiConstants.WARNING == "⚠️"
        assert EmojiConstants.ERROR == "❌"
        assert EmojiConstants.PERSON == "👤"
        assert EmojiConstants.TEAM == "👥"
    
    def test_icon_constants(self):
        """Test icon constants are defined."""
        assert IconConstants.SUCCESS_ICON == ":white_check_mark:"
        assert IconConstants.WARNING_ICON == ":warning:"
        assert IconConstants.ERROR_ICON == ":x:"
    
    def test_color_scheme(self):
        """Test color scheme enum."""
        assert ColorScheme.PRIMARY.value == "#1f77b4"
        assert ColorScheme.SUCCESS.value == "#2ca02c"
        assert ColorScheme.WARNING.value == "#ff7f0e"
        assert ColorScheme.DANGER.value == "#d62728"
    
    def test_message_priority(self):
        """Test message priority enum."""
        assert MessagePriority.LOW.value == "low"
        assert MessagePriority.NORMAL.value == "normal"
        assert MessagePriority.HIGH.value == "high"
        assert MessagePriority.URGENT.value == "urgent"


if __name__ == "__main__":
    # Run some basic tests
    print("Testing Base Template System...")
    
    # Test basic template creation
    data = {"title": "Test Message", "description": "Test description"}
    template = TestSlackMessageTemplate(data)
    
    assert not template.has_errors()
    print(f"✅ Basic template created with {len(template.blocks)} blocks")
    
    # Test with team branding
    branding = create_team_branding("Test Team", primary_color="#ff0000")
    branded_template = TestSlackMessageTemplate(data, team_branding=branding)
    
    assert not branded_template.has_errors()
    print("✅ Template with team branding created")
    
    # Test with accessibility options
    accessibility = create_accessibility_options(screen_reader_optimized=True)
    accessible_template = TestSlackMessageTemplate(data, accessibility_options=accessibility)
    
    assert not accessible_template.has_errors()
    print("✅ Template with accessibility options created")
    
    # Test error handling
    error_template = TestSlackMessageTemplate({})  # Missing required title
    assert error_template.has_errors()
    print("✅ Error handling works correctly")
    
    # Test message generation
    message = template.get_message()
    assert "blocks" in message
    assert "text" in message
    print("✅ Message generation works correctly")
    
    # Test analytics
    template.add_analytics_data("test_metric", "test_value")
    analytics = template.get_analytics_data()
    assert "test_metric" in analytics["custom_data"]
    print("✅ Analytics data collection works")
    
    print("All base template tests completed successfully!")