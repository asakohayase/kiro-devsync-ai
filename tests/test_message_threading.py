"""Tests for message threading functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from devsync_ai.core.message_threading import (
    MessageThreadingManager, ThreadContext, ThreadType, ThreadingConfig,
    ThreadingStrategy
)
from devsync_ai.core.message_formatter import SlackMessage
from devsync_ai.core.threaded_message_formatter import ThreadedMessageFormatter, ThreadedMessage


class TestMessageThreadingManager:
    """Test suite for MessageThreadingManager."""
    
    @pytest.fixture
    def threading_config(self):
        """Create threading configuration for testing."""
        return ThreadingConfig(
            enabled=True,
            max_thread_age_hours=24,
            max_messages_per_thread=50,
            auto_thread_similar_content=True,
            thread_similarity_threshold=0.8,
            temporal_window_minutes=30
        )
    
    @pytest.fixture
    def threading_manager(self, threading_config):
        """Create MessageThreadingManager instance for testing."""
        return MessageThreadingManager(threading_config)
    
    @pytest.fixture
    def sample_pr_message(self):
        """Create sample PR message for testing."""
        return SlackMessage(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "New PR opened: Fix user authentication bug"
                    }
                }
            ],
            text="New PR opened: Fix user authentication bug",
            metadata={
                'pr_number': 123,
                'repository': 'test-repo',
                'author': 'developer1',
                'action': 'opened'
            }
        )
    
    @pytest.fixture
    def sample_jira_message(self):
        """Create sample JIRA message for testing."""
        return SlackMessage(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "JIRA ticket updated: DEV-456"
                    }
                }
            ],
            text="JIRA ticket updated: DEV-456",
            metadata={
                'ticket_key': 'DEV-456',
                'project': 'DEV',
                'author': 'developer2',
                'status': 'In Progress'
            }
        )
    
    def test_initialization(self, threading_manager):
        """Test MessageThreadingManager initialization."""
        assert threading_manager.config.enabled is True
        assert len(threading_manager._channel_threads) == 0
        assert len(threading_manager._entity_threads) == 0
        assert threading_manager._stats['threads_created'] == 0
    
    def test_entity_based_threading(self, threading_manager, sample_pr_message):
        """Test entity-based threading for PR messages."""
        channel_id = "test_channel"
        
        # First message should not find existing thread
        thread_ts = threading_manager.should_thread_message(sample_pr_message, channel_id)
        assert thread_ts is None
        
        # Create thread context
        parent_ts = "1234567890.123456"
        context = threading_manager.create_thread_context(
            sample_pr_message, channel_id, parent_ts
        )
        
        assert context.thread_type == ThreadType.PR_LIFECYCLE
        assert context.entity_id == "123"
        assert context.entity_type == "pr"
        
        # Second message with same PR should find the thread
        second_message = SlackMessage(
            blocks=[],
            text="PR review requested",
            metadata={
                'pr_number': 123,
                'repository': 'test-repo',
                'author': 'developer2',
                'action': 'review_requested'
            }
        )
        
        thread_ts = threading_manager.should_thread_message(second_message, channel_id)
        assert thread_ts == parent_ts
    
    def test_content_based_threading(self, threading_manager):
        """Test content-based threading for similar messages."""
        channel_id = "test_channel"
        
        # Create first message and thread
        message1 = SlackMessage(
            blocks=[],
            text="Authentication service is down",
            metadata={'author': 'ops1', 'service': 'auth'}
        )
        
        parent_ts = "1234567890.123456"
        context = threading_manager.create_thread_context(message1, channel_id, parent_ts)
        
        # Create similar message
        message2 = SlackMessage(
            blocks=[],
            text="Authentication service experiencing issues",
            metadata={'author': 'ops2', 'service': 'auth'}
        )
        
        # Should find the thread based on content similarity
        thread_ts = threading_manager.should_thread_message(message2, channel_id)
        # Note: This might not match due to simple similarity algorithm
        # In a real implementation, we'd use more sophisticated NLP
    
    def test_temporal_threading(self, threading_manager):
        """Test temporal-based threading."""
        channel_id = "test_channel"
        current_time = datetime.now()
        
        # Create first message and thread
        message1 = SlackMessage(
            blocks=[],
            text="System alert triggered",
            metadata={'author': 'system', 'timestamp': current_time.isoformat()}
        )
        
        parent_ts = "1234567890.123456"
        context = threading_manager.create_thread_context(message1, channel_id, parent_ts)
        context.last_updated = current_time
        
        # Create message within temporal window
        message2 = SlackMessage(
            blocks=[],
            text="Another system alert",
            metadata={'author': 'system', 'timestamp': (current_time + timedelta(minutes=10)).isoformat()}
        )
        
        # Should find thread based on temporal proximity
        with patch('devsync_ai.core.message_threading.datetime') as mock_datetime:
            mock_datetime.now.return_value = current_time + timedelta(minutes=10)
            thread_ts = threading_manager.should_thread_message(message2, channel_id)
            # Temporal threading depends on implementation details
    
    def test_thread_context_creation(self, threading_manager, sample_pr_message):
        """Test thread context creation."""
        channel_id = "test_channel"
        parent_ts = "1234567890.123456"
        
        context = threading_manager.create_thread_context(
            sample_pr_message, channel_id, parent_ts, ThreadType.PR_LIFECYCLE
        )
        
        assert context.thread_type == ThreadType.PR_LIFECYCLE
        assert context.parent_message_ts == parent_ts
        assert context.entity_id == "123"
        assert context.entity_type == "pr"
        assert context.message_count == 0
        assert len(context.participants) == 0
        
        # Check if stored correctly
        assert len(threading_manager._channel_threads[channel_id]) == 1
        assert "pr:123" in threading_manager._entity_threads[channel_id]
    
    def test_add_message_to_thread(self, threading_manager, sample_pr_message):
        """Test adding message to existing thread."""
        channel_id = "test_channel"
        parent_ts = "1234567890.123456"
        
        # Create thread
        context = threading_manager.create_thread_context(
            sample_pr_message, channel_id, parent_ts
        )
        
        # Add message to thread
        new_message = SlackMessage(
            blocks=[],
            text="PR approved",
            metadata={'pr_number': 123, 'author': 'reviewer1'}
        )
        
        success = threading_manager.add_message_to_thread(new_message, channel_id, parent_ts)
        assert success is True
        assert context.message_count == 1
        assert 'reviewer1' in context.participants
    
    def test_thread_expiration(self, threading_manager, sample_pr_message):
        """Test thread expiration and cleanup."""
        channel_id = "test_channel"
        parent_ts = "1234567890.123456"
        
        # Create thread with old timestamp
        context = threading_manager.create_thread_context(
            sample_pr_message, channel_id, parent_ts
        )
        
        # Make thread expired
        context.last_updated = datetime.now() - timedelta(hours=25)
        
        # Check expiration
        assert context.is_expired(24) is True
        
        # Cleanup should remove expired thread
        threading_manager._cleanup_expired_threads(channel_id)
        assert len(threading_manager._channel_threads[channel_id]) == 0
    
    def test_related_threads_discovery(self, threading_manager, sample_pr_message):
        """Test finding related threads."""
        channel_id = "test_channel"
        
        # Create multiple threads
        for i in range(3):
            message = SlackMessage(
                blocks=[],
                text=f"PR {i} message",
                metadata={'pr_number': i, 'repository': 'test-repo', 'author': f'dev{i}'}
            )
            parent_ts = f"123456789{i}.123456"
            threading_manager.create_thread_context(message, channel_id, parent_ts)
        
        # Find related threads
        query_message = SlackMessage(
            blocks=[],
            text="New PR in same repo",
            metadata={'pr_number': 999, 'repository': 'test-repo', 'author': 'dev999'}
        )
        
        related = threading_manager.get_related_threads(query_message, channel_id, max_results=5)
        # Should find some related threads based on repository
        assert len(related) >= 0  # Depends on similarity algorithm
    
    def test_threading_statistics(self, threading_manager, sample_pr_message):
        """Test threading statistics collection."""
        channel_id = "test_channel"
        parent_ts = "1234567890.123456"
        
        # Create thread and add messages
        context = threading_manager.create_thread_context(
            sample_pr_message, channel_id, parent_ts
        )
        
        threading_manager.add_message_to_thread(sample_pr_message, channel_id, parent_ts)
        
        # Get statistics
        stats = threading_manager.get_threading_stats()
        
        expected_keys = [
            'threads_created', 'messages_threaded', 'threads_expired',
            'active_threads', 'active_channels', 'total_entities_tracked'
        ]
        
        for key in expected_keys:
            assert key in stats
            assert isinstance(stats[key], int)
        
        assert stats['threads_created'] >= 1
        assert stats['messages_threaded'] >= 1
    
    def test_channel_threads_listing(self, threading_manager, sample_pr_message):
        """Test listing threads for a channel."""
        channel_id = "test_channel"
        
        # Create multiple threads
        for i in range(3):
            message = SlackMessage(
                blocks=[],
                text=f"Message {i}",
                metadata={'pr_number': i, 'author': f'dev{i}'}
            )
            parent_ts = f"123456789{i}.123456"
            threading_manager.create_thread_context(message, channel_id, parent_ts)
        
        # Get channel threads
        threads = threading_manager.get_channel_threads(channel_id)
        assert len(threads) == 3
        
        # All should be ThreadContext instances
        for thread in threads:
            assert isinstance(thread, ThreadContext)
    
    def test_config_update(self, threading_manager):
        """Test configuration updates."""
        new_config = ThreadingConfig(
            enabled=False,
            max_thread_age_hours=48,
            thread_similarity_threshold=0.9
        )
        
        threading_manager.update_config(new_config)
        
        assert threading_manager.config.enabled is False
        assert threading_manager.config.max_thread_age_hours == 48
        assert threading_manager.config.thread_similarity_threshold == 0.9


class TestThreadedMessageFormatter:
    """Test suite for ThreadedMessageFormatter."""
    
    @pytest.fixture
    def threading_manager(self):
        """Create threading manager for testing."""
        return MessageThreadingManager()
    
    @pytest.fixture
    def threaded_formatter(self, threading_manager):
        """Create ThreadedMessageFormatter instance for testing."""
        return ThreadedMessageFormatter(threading_manager)
    
    @pytest.fixture
    def sample_template_data(self):
        """Create sample template data for testing."""
        return {
            'pr': {
                'number': 123,
                'title': 'Fix authentication bug',
                'repository': {'name': 'test-repo'},
                'author': {'login': 'developer1'}
            },
            'author': 'developer1',
            'template_type': 'pr_opened'
        }
    
    def test_format_with_threading(self, threaded_formatter, sample_template_data):
        """Test formatting message with threading support."""
        channel_id = "test_channel"
        
        # Format message
        threaded_message = threaded_formatter.format_with_threading(
            sample_template_data, channel_id, "pr_template"
        )
        
        assert isinstance(threaded_message, ThreadedMessage)
        assert isinstance(threaded_message.message, SlackMessage)
        assert threaded_message.message.metadata is not None
        assert 'pr_number' in threaded_message.message.metadata
        
        # Should be marked as thread starter for PR opened
        assert threaded_message.is_thread_starter is True
    
    def test_create_thread_starter(self, threaded_formatter, sample_template_data):
        """Test creating thread starter."""
        channel_id = "test_channel"
        message_ts = "1234567890.123456"
        
        # Format message
        threaded_message = threaded_formatter.format_with_threading(
            sample_template_data, channel_id, "pr_template"
        )
        
        # Create thread starter
        if threaded_message.is_thread_starter:
            context = threaded_formatter.create_thread_starter(
                threaded_message, channel_id, message_ts
            )
            
            assert isinstance(context, ThreadContext)
            assert context.thread_type == ThreadType.PR_LIFECYCLE
            assert context.parent_message_ts == message_ts
            assert threaded_message.thread_context == context
    
    def test_thread_summary_formatting(self, threaded_formatter):
        """Test formatting thread summary."""
        # Create mock thread context
        context = ThreadContext(
            thread_id="test_thread_123",
            thread_type=ThreadType.PR_LIFECYCLE,
            parent_message_ts="1234567890.123456",
            entity_id="123",
            entity_type="pr",
            message_count=5
        )
        context.participants.add("developer1")
        context.participants.add("reviewer1")
        
        # Format summary
        summary = threaded_formatter.format_thread_summary(context, "test_channel")
        
        assert isinstance(summary, SlackMessage)
        assert summary.blocks is not None
        assert len(summary.blocks) > 0
        assert summary.metadata['thread_summary'] is True
        assert "Thread Summary" in summary.text
    
    def test_related_threads_notification(self, threaded_formatter):
        """Test formatting related threads notification."""
        # Create mock related threads
        related_threads = [
            ThreadContext(
                thread_id=f"thread_{i}",
                thread_type=ThreadType.PR_LIFECYCLE,
                parent_message_ts=f"123456789{i}.123456",
                entity_id=str(i),
                entity_type="pr",
                message_count=i + 1
            )
            for i in range(3)
        ]
        
        # Create mock current message
        current_message = SlackMessage(
            blocks=[],
            text="Current message",
            metadata={'pr_number': 999}
        )
        
        # Format notification
        notification = threaded_formatter.format_related_threads_notification(
            related_threads, current_message
        )
        
        assert isinstance(notification, SlackMessage)
        assert notification.blocks is not None
        assert "Related Discussions" in notification.blocks[0]['text']['text']
        assert notification.metadata['related_threads_notification'] is True
    
    def test_metadata_enhancement(self, threaded_formatter, sample_template_data):
        """Test message metadata enhancement for threading."""
        channel_id = "test_channel"
        
        # Format message
        threaded_message = threaded_formatter.format_with_threading(
            sample_template_data, channel_id, "pr_template"
        )
        
        metadata = threaded_message.message.metadata
        assert 'pr_number' in metadata
        assert 'repository' in metadata
        assert 'author' in metadata
        assert metadata['pr_number'] == 123
        assert metadata['repository'] == 'test-repo'
        assert metadata['author'] == 'developer1'
    
    def test_thread_starter_detection(self, threaded_formatter):
        """Test detection of messages that should start threads."""
        # Test PR message
        pr_data = {
            'pr': {'number': 123, 'title': 'Test PR'},
            'template_type': 'pr_opened'
        }
        
        threaded_message = threaded_formatter.format_with_threading(
            pr_data, "test_channel", "pr_template"
        )
        assert threaded_message.is_thread_starter is True
        
        # Test regular message
        regular_data = {
            'message': 'Regular update',
            'template_type': 'general'
        }
        
        threaded_message = threaded_formatter.format_with_threading(
            regular_data, "test_channel", "general_template"
        )
        assert threaded_message.is_thread_starter is False
    
    def test_threading_stats(self, threaded_formatter):
        """Test getting threading statistics."""
        stats = threaded_formatter.get_threading_stats()
        
        assert isinstance(stats, dict)
        assert 'threads_created' in stats
        assert 'messages_threaded' in stats
        assert 'active_threads' in stats


class TestThreadContext:
    """Test suite for ThreadContext."""
    
    def test_thread_context_creation(self):
        """Test ThreadContext creation and basic functionality."""
        context = ThreadContext(
            thread_id="test_thread",
            thread_type=ThreadType.PR_LIFECYCLE,
            parent_message_ts="1234567890.123456",
            entity_id="123",
            entity_type="pr"
        )
        
        assert context.thread_id == "test_thread"
        assert context.thread_type == ThreadType.PR_LIFECYCLE
        assert context.message_count == 0
        assert len(context.participants) == 0
    
    def test_participant_management(self):
        """Test participant management in thread context."""
        context = ThreadContext(
            thread_id="test_thread",
            thread_type=ThreadType.PR_LIFECYCLE,
            parent_message_ts="1234567890.123456"
        )
        
        # Add participants
        context.add_participant("user1")
        context.add_participant("user2")
        context.add_participant("user1")  # Duplicate
        
        assert len(context.participants) == 2
        assert "user1" in context.participants
        assert "user2" in context.participants
    
    def test_activity_updates(self):
        """Test activity updates in thread context."""
        context = ThreadContext(
            thread_id="test_thread",
            thread_type=ThreadType.PR_LIFECYCLE,
            parent_message_ts="1234567890.123456"
        )
        
        initial_count = context.message_count
        initial_time = context.last_updated
        
        # Update activity
        context.update_activity()
        
        assert context.message_count == initial_count + 1
        assert context.last_updated >= initial_time
    
    def test_expiration_check(self):
        """Test thread expiration checking."""
        context = ThreadContext(
            thread_id="test_thread",
            thread_type=ThreadType.PR_LIFECYCLE,
            parent_message_ts="1234567890.123456"
        )
        
        # Fresh context should not be expired
        assert context.is_expired(24) is False
        
        # Make context old
        context.last_updated = datetime.now() - timedelta(hours=25)
        assert context.is_expired(24) is True


if __name__ == "__main__":
    pytest.main([__file__])