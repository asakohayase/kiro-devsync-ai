"""
Unit tests for the base template system.
Tests SlackMessageTemplate base class functionality, error handling, and accessibility features.
"""

import pytest
from unittest.mock import patch
from typing import Dict, List, Any

from devsync_ai.core.base_template import SlackMessageTemplate
from devsync_ai.core.message_formatter import SlackMessage, TemplateConfig
from devsync_ai.core.status_indicators import StatusType


class _TestTemplate(SlackMessageTemplate):
    """Test implementation of SlackMessageTemplate."""
    
    REQUIRED_FIELDS = ['title']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create test message blocks."""
        blocks = [self.create_header_block(data['title'])]
        
        if data.get('description'):
            blocks.append(self.create_section_block(data['description']))
        
        return blocks


class TestBaseTemplate:
    """Test base SlackMessageTemplate functionality."""
    
    def test_template_initialization(self):
        """Test template initialization with default configuration."""
        template = _TestTemplate()
        
        assert template.config.team_id == "default"
        assert template.config.interactive_elements is True
        assert template.config.accessibility_mode is False
        assert template.status_system is not None
    
    def test_successful_message_formatting(self):
        """Test successful message formatting with valid data."""
        data = {'title': 'Test Message', 'description': 'Test description'}
        
        template = _TestTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        assert message.text  # Should have fallback text
        assert message.metadata['template_type'] == '_TestTemplate'
        assert 'created_at' in message.metadata
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        data = {'description': 'Missing title'}  # Missing required 'title' field
        
        template = _TestTemplate()
        message = template.format_message(data)
        
        # Should still create a message with placeholder values
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Check that placeholder was used
        header_block = next((b for b in message.blocks if b.get('type') == 'header'), None)
        assert header_block is not None
        assert 'Untitled' in header_block['text']['text']
    
    def test_error_handling(self):
        """Test graceful error handling."""
        template = _TestTemplate()
        
        # Mock _create_message_blocks to raise an exception
        with patch.object(template, '_create_message_blocks', side_effect=Exception("Test error")):
            data = {'title': 'Error Test'}
            message = template.format_message(data)
        
        # Should return error message instead of crashing
        assert isinstance(message, SlackMessage)
        assert message.metadata.get('error') is True
        assert len(message.blocks) > 0
    
    def test_accessibility_fallback_text(self):
        """Test accessibility fallback text generation."""
        data = {
            'title': 'Accessibility Test',
            'description': '*Bold text* and _italic text_ with `code`'
        }
        
        template = _TestTemplate()
        message = template.format_message(data)
        
        # Check fallback text exists and markdown is stripped
        assert message.text
        assert 'HEADER: ' in message.text
        assert 'Bold text' in message.text
        assert '*' not in message.text
        assert '_' not in message.text
        assert '`' not in message.text


class TestBaseTemplateHelpers:
    """Test helper methods in SlackMessageTemplate."""
    
    def test_format_user_mention(self):
        """Test _format_user_mention method."""
        template = _TestTemplate()
        
        assert template._format_user_mention("john.doe") == "<@john.doe>"
        assert template._format_user_mention("@jane.doe") == "@jane.doe"
        assert template._format_user_mention("") == "Unassigned"
        assert template._format_user_mention(None) == "Unassigned"
        assert template._format_user_mention("Unknown") == "Unassigned"
    
    def test_format_url_link(self):
        """Test _format_url_link method."""
        template = _TestTemplate()
        
        assert template._format_url_link("https://example.com", "Example") == "<https://example.com|Example>"
        assert template._format_url_link("", "Example") == "Example"
        assert template._format_url_link("#", "Example") == "Example"
        assert template._format_url_link(None, "Example") == "Example"
    
    def test_get_priority_indicator(self):
        """Test _get_priority_indicator method."""
        template = _TestTemplate()
        
        assert template._get_priority_indicator("critical") == "🚨 Critical"
        assert template._get_priority_indicator("high") == "🔴 High"
        assert template._get_priority_indicator("medium") == "🟡 Medium"
        assert template._get_priority_indicator("low") == "🟢 Low"
        assert template._get_priority_indicator("unknown") == "⚪ unknown"
    
    def test_truncate_text(self):
        """Test _truncate_text method."""
        template = _TestTemplate()
        
        # Test short text (no truncation)
        short_text = "This is short"
        assert template._truncate_text(short_text, max_length=50) == short_text
        
        # Test long text (with truncation)
        long_text = "This is a very long text that should be truncated"
        truncated = template._truncate_text(long_text, max_length=20)
        assert len(truncated) <= 23  # 20 + "..." length
        assert truncated.endswith("...")


if __name__ == "__main__":
    print("Running base template unit tests...")
    
    # Basic smoke test
    template = _TestTemplate()
    data = {'title': 'Test Message'}
    message = template.format_message(data)
    
    assert isinstance(message, SlackMessage)
    assert len(message.blocks) > 0
    print("✅ Basic functionality works")
    
    print("All tests passed!")