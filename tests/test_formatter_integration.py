"""Unit tests for MessageBatcher formatter factory integration."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, Any, Optional

from devsync_ai.core.message_batcher import (
    MessageBatcher, BatchConfig, BatchableMessage, BatchGroup, BatchType, ContentType,
    BatchFormatterContext
)
from devsync_ai.core.formatter_factory import (
    SlackMessageFormatterFactory, MessageType, FormatterOptions, ProcessingResult
)
from devsync_ai.core.message_formatter import SlackMessage


class TestBatchFormatterContext:
    """Test BatchFormatterContext functionality."""
    
    def test_batch_formatter_context_creation(self):
        """Test creating BatchFormatterContext with proper data."""
        # Create test batch group
        batch_group = BatchGroup(
            id="test_batch_1",
            channel_id="test_channel",
            batch_type=BatchType.PR_ACTIVITY
        )
        
        # Add test messages
        message1 = BatchableMessage(
            id="msg1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="user1",
            data={"pr": {"number": 123, "title": "Test PR"}}
        )
        batch_group.add_message(message1)
        
        # Create context
        context = BatchFormatterContext(
            batch_group=batch_group,
            channel_id="test_channel",
            message_count=1,
            content_types={"pr_update": 1},
            authors=["user1"],
            time_range={"start": datetime.now(), "end": datetime.now()}
        )
        
        assert context.batch_group == batch_group
        assert context.channel_id == "test_channel"
        assert context.message_count == 1
        assert context.content_types == {"pr_update": 1}
        assert context.authors == ["user1"]
    
    def test_get_message_type_pr_batch(self):
        """Test message type detection for PR batch."""
        batch_group = BatchGroup(
            id="test_batch_1",
            channel_id="test_channel",
            batch_type=BatchType.PR_ACTIVITY
        )
        
        context = BatchFormatterContext(
            batch_group=batch_group,
            channel_id="test_channel",
            message_count=2,
            content_types={"pr_update": 2},
            authors=["user1"],
            time_range={"start": datetime.now(), "end": datetime.now()}
        )
        
        assert context.get_message_type() == MessageType.PR_BATCH
    
    def test_get_message_type_jira_batch(self):
        """Test message type detection for JIRA batch."""
        batch_group = BatchGroup(
            id="test_batch_1",
            channel_id="test_channel",
            batch_type=BatchType.JIRA_ACTIVITY
        )
        
        context = BatchFormatterContext(
            batch_group=batch_group,
            channel_id="test_channel",
            message_count=2,
            content_types={"jira_update": 2},
            authors=["user1"],
            time_range={"start": datetime.now(), "end": datetime.now()}
        )
        
        assert context.get_message_type() == MessageType.JIRA_BATCH
    
    def test_get_message_type_mixed_content(self):
        """Test message type detection for mixed content."""
        batch_group = BatchGroup(
            id="test_batch_1",
            channel_id="test_channel",
            batch_type=BatchType.TEAM_ACTIVITY
        )
        
        context = BatchFormatterContext(
            batch_group=batch_group,
            channel_id="test_channel",
            message_count=3,
            content_types={"pr_update": 1, "jira_update": 2},
            authors=["user1", "user2"],
            time_range={"start": datetime.now(), "end": datetime.now()}
        )
        
        assert context.get_message_type() == MessageType.CUSTOM
    
    def test_get_formatter_data(self):
        """Test formatter data generation."""
        # Create batch group with messages
        batch_group = BatchGroup(
            id="test_batch_1",
            channel_id="test_channel",
            batch_type=BatchType.PR_ACTIVITY
        )
        
        message1 = BatchableMessage(
            id="msg1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="user1",
            data={"pr": {"number": 123}},
            metadata={"test": "data"}
        )
        batch_group.add_message(message1)
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=5)
        
        context = BatchFormatterContext(
            batch_group=batch_group,
            channel_id="test_channel",
            message_count=1,
            content_types={"pr_update": 1},
            authors=["user1"],
            time_range={"start": start_time, "end": end_time}
        )
        
        formatter_data = context.get_formatter_data()
        
        assert formatter_data["batch_id"] == "test_batch_1"
        assert formatter_data["batch_type"] == "pr_activity"
        assert formatter_data["channel_id"] == "test_channel"
        assert formatter_data["message_count"] == 1
        assert formatter_data["content_types"] == {"pr_update": 1}
        assert formatter_data["authors"] == ["user1"]
        assert len(formatter_data["messages"]) == 1
        assert formatter_data["messages"][0]["id"] == "msg1"
        assert formatter_data["messages"][0]["content_type"] == "pr_update"
        assert formatter_data["messages"][0]["author"] == "user1"


class TestMessageBatcherFormatterIntegration:
    """Test MessageBatcher formatter factory integration."""
    
    def test_initialization_with_formatter_factory(self):
        """Test MessageBatcher initialization with formatter factory."""
        mock_factory = Mock(spec=SlackMessageFormatterFactory)
        config = BatchConfig(enable_formatter_integration=True)
        
        batcher = MessageBatcher(config=config, formatter_factory=mock_factory)
        
        assert batcher._formatter_factory == mock_factory
        assert batcher.config.enable_formatter_integration is True
        assert "formatter_used_count" in batcher._formatter_stats
        assert "fallback_used_count" in batcher._formatter_stats
        assert "formatter_errors" in batcher._formatter_stats
    
    def test_initialization_without_formatter_factory(self):
        """Test MessageBatcher initialization without formatter factory."""
        config = BatchConfig(enable_formatter_integration=False)
        
        batcher = MessageBatcher(config=config)
        
        assert batcher._formatter_factory is None
        assert batcher.config.enable_formatter_integration is False
    
    def test_create_batched_message_with_formatter_success(self):
        """Test successful message creation using formatter factory."""
        # Setup mock formatter factory
        mock_factory = Mock(spec=SlackMessageFormatterFactory)
        mock_result = ProcessingResult(
            success=True,
            message=SlackMessage(
                blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Test message"}}],
                text="Test fallback",
                metadata={}
            ),
            formatter_used="TestFormatter",
            processing_time_ms=50.0
        )
        mock_factory.format_message.return_value = mock_result
        
        # Setup batcher
        config = BatchConfig(enable_formatter_integration=True)
        batcher = MessageBatcher(config=config, formatter_factory=mock_factory)
        
        # Create batch group
        batch_group = BatchGroup(
            id="test_batch_1",
            channel_id="test_channel",
            batch_type=BatchType.PR_ACTIVITY
        )
        
        message1 = BatchableMessage(
            id="msg1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="user1"
        )
        batch_group.add_message(message1)
        
        # Test message creation
        result = batcher._create_batched_message(batch_group)
        
        assert result is not None
        assert result.metadata["is_batched"] is True
        assert result.metadata["formatter_used"] == "TestFormatter"
        assert result.metadata["processing_time_ms"] == 50.0
        assert batcher._formatter_stats["formatter_used_count"] == 1
        assert batcher._formatter_stats["fallback_used_count"] == 0
        
        # Verify formatter was called correctly
        mock_factory.format_message.assert_called_once()
        call_args = mock_factory.format_message.call_args
        assert call_args[1]["channel"] == "test_channel"
        assert call_args[1]["options"].batch is True
    
    def test_create_batched_message_formatter_failure_with_fallback(self):
        """Test message creation when formatter fails but fallback is enabled."""
        # Setup mock formatter factory that fails
        mock_factory = Mock(spec=SlackMessageFormatterFactory)
        mock_factory.format_message.side_effect = Exception("Formatter error")
        
        # Setup batcher with fallback enabled
        config = BatchConfig(
            enable_formatter_integration=True,
            fallback_formatting=True
        )
        batcher = MessageBatcher(config=config, formatter_factory=mock_factory)
        
        # Create batch group
        batch_group = BatchGroup(
            id="test_batch_1",
            channel_id="test_channel",
            batch_type=BatchType.PR_ACTIVITY
        )
        
        message1 = BatchableMessage(
            id="msg1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="user1"
        )
        batch_group.add_message(message1)
        
        # Test message creation - should fall back to default formatting
        result = batcher._create_batched_message(batch_group)
        
        assert result is not None
        assert result.metadata["formatter_used"] == "fallback"
        assert batcher._formatter_stats["formatter_errors"] == 1
        assert batcher._formatter_stats["fallback_used_count"] == 1
        assert batcher._formatter_stats["formatter_used_count"] == 0
    
    def test_create_batched_message_formatter_failure_without_fallback(self):
        """Test message creation when formatter fails and fallback is disabled."""
        # Setup mock formatter factory that fails
        mock_factory = Mock(spec=SlackMessageFormatterFactory)
        mock_factory.format_message.side_effect = Exception("Formatter error")
        
        # Setup batcher with fallback disabled
        config = BatchConfig(
            enable_formatter_integration=True,
            fallback_formatting=False
        )
        batcher = MessageBatcher(config=config, formatter_factory=mock_factory)
        
        # Create batch group
        batch_group = BatchGroup(
            id="test_batch_1",
            channel_id="test_channel",
            batch_type=BatchType.PR_ACTIVITY
        )
        
        message1 = BatchableMessage(
            id="msg1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="user1"
        )
        batch_group.add_message(message1)
        
        # Test message creation - should raise exception
        with pytest.raises(Exception, match="Formatter error"):
            batcher._create_batched_message(batch_group)
        
        assert batcher._formatter_stats["formatter_errors"] == 1
        assert batcher._formatter_stats["fallback_used_count"] == 0
    
    def test_create_batched_message_formatter_disabled(self):
        """Test message creation when formatter integration is disabled."""
        mock_factory = Mock(spec=SlackMessageFormatterFactory)
        
        # Setup batcher with formatter integration disabled
        config = BatchConfig(enable_formatter_integration=False)
        batcher = MessageBatcher(config=config, formatter_factory=mock_factory)
        
        # Create batch group
        batch_group = BatchGroup(
            id="test_batch_1",
            channel_id="test_channel",
            batch_type=BatchType.PR_ACTIVITY
        )
        
        message1 = BatchableMessage(
            id="msg1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="user1"
        )
        batch_group.add_message(message1)
        
        # Test message creation - should use fallback without trying formatter
        result = batcher._create_batched_message(batch_group)
        
        assert result is not None
        assert result.metadata["formatter_used"] == "fallback"
        assert batcher._formatter_stats["fallback_used_count"] == 1
        assert batcher._formatter_stats["formatter_used_count"] == 0
        
        # Verify formatter was not called
        mock_factory.format_message.assert_not_called()
    
    def test_create_batched_message_no_formatter_factory(self):
        """Test message creation when no formatter factory is provided."""
        # Setup batcher without formatter factory
        config = BatchConfig(enable_formatter_integration=True)
        batcher = MessageBatcher(config=config, formatter_factory=None)
        
        # Create batch group
        batch_group = BatchGroup(
            id="test_batch_1",
            channel_id="test_channel",
            batch_type=BatchType.PR_ACTIVITY
        )
        
        message1 = BatchableMessage(
            id="msg1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="user1"
        )
        batch_group.add_message(message1)
        
        # Test message creation - should use fallback
        result = batcher._create_batched_message(batch_group)
        
        assert result is not None
        assert result.metadata["formatter_used"] == "fallback"
        assert batcher._formatter_stats["fallback_used_count"] == 1
    
    def test_comprehensive_fallback_text_generation(self):
        """Test comprehensive fallback text generation for accessibility."""
        config = BatchConfig()
        batcher = MessageBatcher(config=config)
        
        # Create batch group with multiple messages
        batch_group = BatchGroup(
            id="test_batch_1",
            channel_id="test_channel",
            batch_type=BatchType.TEAM_ACTIVITY
        )
        
        # Add messages with different priorities and types
        message1 = BatchableMessage(
            id="msg1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="user1",
            priority="high"
        )
        message2 = BatchableMessage(
            id="msg2",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=datetime.now() + timedelta(minutes=2),
            author="user2",
            priority="medium"
        )
        
        batch_group.add_message(message1)
        batch_group.add_message(message2)
        
        stats = batch_group.get_summary_stats()
        fallback_text = batcher._create_comprehensive_fallback_text(batch_group, stats)
        
        assert "📦 Activity Summary - 2 updates" in fallback_text
        assert "Pull Request update" in fallback_text
        assert "JIRA Ticket update" in fallback_text
        assert "Contributors: user1, user2" in fallback_text
        assert "Priority distribution:" in fallback_text
        assert "1 high, 1 medium" in fallback_text
        assert f"Batch ID: {batch_group.id}" in fallback_text
        assert "Created:" in fallback_text
    
    def test_get_formatter_stats(self):
        """Test getting formatter integration statistics."""
        mock_factory = Mock(spec=SlackMessageFormatterFactory)
        mock_factory.get_metrics.return_value = {
            "total_messages": 10,
            "cache_hit_rate": 25.0,
            "avg_processing_time_ms": 45.5
        }
        
        config = BatchConfig(
            enable_formatter_integration=True,
            fallback_formatting=True
        )
        batcher = MessageBatcher(config=config, formatter_factory=mock_factory)
        
        # Simulate some usage
        batcher._formatter_stats["formatter_used_count"] = 8
        batcher._formatter_stats["formatter_errors"] = 2
        batcher._formatter_stats["fallback_used_count"] = 3
        batcher._formatter_stats["formatter_success_rate"] = 0.8
        
        stats = batcher.get_formatter_stats()
        
        assert stats["formatter_used_count"] == 8
        assert stats["formatter_errors"] == 2
        assert stats["fallback_used_count"] == 3
        assert stats["formatter_success_rate"] == 0.8
        assert stats["total_formatting_attempts"] == 10
        assert stats["formatter_factory_available"] is True
        assert stats["formatter_integration_enabled"] is True
        assert stats["fallback_formatting_enabled"] is True
        assert stats["formatter_factory_metrics"]["total_messages"] == 10
    
    def test_batch_stats_include_formatter_metrics(self):
        """Test that batch stats include formatter integration metrics."""
        mock_factory = Mock(spec=SlackMessageFormatterFactory)
        config = BatchConfig(enable_formatter_integration=True)
        batcher = MessageBatcher(config=config, formatter_factory=mock_factory)
        
        # Simulate some usage
        batcher._formatter_stats["formatter_used_count"] = 5
        batcher._formatter_stats["fallback_used_count"] = 2
        
        stats = batcher.get_batch_stats()
        
        assert "formatter_integration" in stats
        formatter_stats = stats["formatter_integration"]
        assert formatter_stats["formatter_used_count"] == 5
        assert formatter_stats["fallback_used_count"] == 2
        assert formatter_stats["formatter_factory_available"] is True
        assert formatter_stats["formatter_integration_enabled"] is True


if __name__ == "__main__":
    pytest.main([__file__])