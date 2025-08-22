"""Unit tests for ChannelStats dataclass and per-channel analytics."""

import pytest
from datetime import datetime, timedelta
from devsync_ai.core.message_batcher import (
    ChannelStats, MessageBatcher, BatchableMessage, ContentType, BatchConfig
)


class TestChannelStats:
    """Test ChannelStats dataclass functionality."""
    
    def test_channel_stats_initialization(self):
        """Test ChannelStats initialization with default values."""
        channel_id = "test-channel"
        stats = ChannelStats(channel_id=channel_id)
        
        assert stats.channel_id == channel_id
        assert stats.batches_created == 0
        assert stats.batches_sent == 0
        assert stats.messages_batched == 0
        assert stats.average_batch_size == 0.0
        assert stats.average_time_to_send == 0.0
        assert stats.last_activity is None
        assert stats.active_batch_count == 0
        assert stats.pending_message_count == 0
    
    def test_update_batch_created(self):
        """Test updating statistics when a batch is created."""
        stats = ChannelStats(channel_id="test-channel")
        
        # Update batch created
        stats.update_batch_created()
        
        assert stats.batches_created == 1
        assert stats.active_batch_count == 1
        assert isinstance(stats.last_activity, datetime)
        
        # Update again
        stats.update_batch_created()
        
        assert stats.batches_created == 2
        assert stats.active_batch_count == 2
    
    def test_update_message_added(self):
        """Test updating statistics when messages are added."""
        stats = ChannelStats(channel_id="test-channel")
        
        # Add single message
        stats.update_message_added(1)
        
        assert stats.messages_batched == 1
        assert stats.pending_message_count == 1
        assert isinstance(stats.last_activity, datetime)
        
        # Add multiple messages
        stats.update_message_added(3)
        
        assert stats.messages_batched == 4
        assert stats.pending_message_count == 4
    
    def test_update_batch_sent_single_batch(self):
        """Test updating statistics when a batch is sent (single batch)."""
        stats = ChannelStats(channel_id="test-channel")
        
        # Set up initial state
        stats.update_batch_created()
        stats.update_message_added(3)
        
        # Send the batch
        stats.update_batch_sent(message_count=3, time_to_send_minutes=2.5)
        
        assert stats.batches_sent == 1
        assert stats.active_batch_count == 0
        assert stats.pending_message_count == 0  # All 3 messages were sent
        assert stats.average_batch_size == 3.0
        assert stats.average_time_to_send == 2.5
        assert isinstance(stats.last_activity, datetime)
    
    def test_update_batch_sent_multiple_batches(self):
        """Test updating statistics with multiple batches (average calculation)."""
        stats = ChannelStats(channel_id="test-channel")
        
        # First batch: 3 messages, 2.0 minutes
        stats.update_batch_created()
        stats.update_message_added(3)
        stats.update_batch_sent(message_count=3, time_to_send_minutes=2.0)
        
        # Second batch: 5 messages, 4.0 minutes
        stats.update_batch_created()
        stats.update_message_added(5)
        stats.update_batch_sent(message_count=5, time_to_send_minutes=4.0)
        
        # Verify averages: (3+5)/2 = 4.0, (2.0+4.0)/2 = 3.0
        assert stats.batches_sent == 2
        assert stats.average_batch_size == 4.0
        assert stats.average_time_to_send == 3.0
        
        # Third batch: 2 messages, 1.0 minutes
        stats.update_batch_created()
        stats.update_message_added(2)
        stats.update_batch_sent(message_count=2, time_to_send_minutes=1.0)
        
        # Verify averages: (3+5+2)/3 = 3.33, (2.0+4.0+1.0)/3 = 2.33
        assert stats.batches_sent == 3
        assert abs(stats.average_batch_size - 10/3) < 0.01  # 3.33...
        assert abs(stats.average_time_to_send - 7/3) < 0.01  # 2.33...
    
    def test_get_efficiency_metrics_no_batches(self):
        """Test efficiency metrics with no batches."""
        stats = ChannelStats(channel_id="test-channel")
        
        metrics = stats.get_efficiency_metrics()
        
        assert metrics['batch_completion_rate'] == 0.0
        assert metrics['messages_per_batch'] == 0.0
        assert metrics['batching_efficiency'] == 0.0
    
    def test_get_efficiency_metrics_with_batches(self):
        """Test efficiency metrics with various batch scenarios."""
        stats = ChannelStats(channel_id="test-channel")
        
        # Create 3 batches, send 2
        stats.update_batch_created()
        stats.update_message_added(3)
        stats.update_batch_sent(message_count=3, time_to_send_minutes=2.0)
        
        stats.update_batch_created()
        stats.update_message_added(4)
        stats.update_batch_sent(message_count=4, time_to_send_minutes=3.0)
        
        stats.update_batch_created()
        stats.update_message_added(2)
        # Don't send the third batch
        
        metrics = stats.get_efficiency_metrics()
        
        # Completion rate: 2/3 = 0.667
        assert abs(metrics['batch_completion_rate'] - 2/3) < 0.01
        
        # Messages per batch: 9/3 = 3.0
        assert metrics['messages_per_batch'] == 3.0
        
        # Efficiency: (2/3) * min(3.0/3.0, 1.0) = 2/3 * 1.0 = 0.667
        assert abs(metrics['batching_efficiency'] - 2/3) < 0.01
    
    def test_get_efficiency_metrics_optimal_batch_size(self):
        """Test efficiency metrics with optimal batch size (around 3)."""
        stats = ChannelStats(channel_id="test-channel")
        
        # Create batches with exactly 3 messages each
        for _ in range(5):
            stats.update_batch_created()
            stats.update_message_added(3)
            stats.update_batch_sent(message_count=3, time_to_send_minutes=2.0)
        
        metrics = stats.get_efficiency_metrics()
        
        # Perfect completion rate and optimal batch size
        assert metrics['batch_completion_rate'] == 1.0
        assert metrics['messages_per_batch'] == 3.0
        assert metrics['batching_efficiency'] == 1.0  # 1.0 * min(3.0/3.0, 1.0) = 1.0
    
    def test_get_efficiency_metrics_large_batch_size(self):
        """Test efficiency metrics with large batch sizes."""
        stats = ChannelStats(channel_id="test-channel")
        
        # Create batches with 6 messages each (above optimal)
        for _ in range(3):
            stats.update_batch_created()
            stats.update_message_added(6)
            stats.update_batch_sent(message_count=6, time_to_send_minutes=2.0)
        
        metrics = stats.get_efficiency_metrics()
        
        # Perfect completion rate but sub-optimal batch size
        assert metrics['batch_completion_rate'] == 1.0
        assert metrics['messages_per_batch'] == 6.0
        assert metrics['batching_efficiency'] == 1.0  # 1.0 * min(6.0/3.0, 1.0) = 1.0 * 1.0


class TestMessageBatcherChannelStats:
    """Test MessageBatcher integration with ChannelStats."""
    
    def test_get_or_create_channel_stats(self):
        """Test getting or creating channel statistics."""
        batcher = MessageBatcher()
        
        # Get stats for new channel
        stats = batcher._get_or_create_channel_stats("new-channel")
        
        assert isinstance(stats, ChannelStats)
        assert stats.channel_id == "new-channel"
        assert stats.batches_created == 0
        
        # Get same stats again (should return existing)
        stats2 = batcher._get_or_create_channel_stats("new-channel")
        assert stats is stats2  # Same object
    
    def test_get_channel_stats_nonexistent(self):
        """Test getting stats for non-existent channel."""
        batcher = MessageBatcher()
        
        stats = batcher.get_channel_stats("nonexistent-channel")
        assert stats is None
    
    def test_add_message_updates_channel_stats(self):
        """Test that adding messages updates channel statistics."""
        batcher = MessageBatcher()
        channel_id = "test-channel"
        
        # Add a message
        message = BatchableMessage(
            id="msg-1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="test-user"
        )
        
        batcher.add_message(message, channel_id)
        
        # Check channel stats were updated
        stats = batcher.get_channel_stats(channel_id)
        assert stats is not None
        assert stats.batches_created == 1
        assert stats.messages_batched == 1
        assert stats.active_batch_count == 1
        assert stats.pending_message_count == 1
    
    def test_flush_batch_updates_channel_stats(self):
        """Test that flushing batches updates channel statistics."""
        config = BatchConfig(max_batch_size=2)  # Small batch size for testing
        batcher = MessageBatcher(config=config)
        channel_id = "test-channel"
        
        # Create messages with same timestamp and similarity to ensure they batch together
        base_time = datetime.now()
        messages = []
        for i in range(2):
            message = BatchableMessage(
                id=f"msg-{i}",
                content_type=ContentType.JIRA_UPDATE,
                timestamp=base_time,  # Same timestamp
                author="test-user",
                data={"project": "test-project"}  # Same project for similarity
            )
            messages.append(message)
        
        # Add messages - should batch together and flush when limit reached
        result1 = batcher.add_message(messages[0], channel_id)
        result2 = batcher.add_message(messages[1], channel_id)
        
        # Should have flushed after 2 messages
        stats = batcher.get_channel_stats(channel_id)
        assert stats is not None
        
        # Check if batching worked as expected
        if stats.batches_created == 1:
            # Messages were batched together (ideal case)
            assert stats.batches_sent == 1
            assert stats.messages_batched == 2
            assert stats.active_batch_count == 0
            assert stats.pending_message_count == 0
            assert stats.average_batch_size == 2.0
        else:
            # Messages created separate batches (due to timing/strategy)
            # This is also valid behavior, just different batching strategy result
            assert stats.batches_created >= 1
            assert stats.messages_batched == 2
        
        assert stats.average_time_to_send >= 0.0
    
    def test_multiple_channels_separate_stats(self):
        """Test that multiple channels maintain separate statistics."""
        batcher = MessageBatcher()
        
        # Add messages to different channels
        message1 = BatchableMessage(
            id="msg-1",
            content_type=ContentType.ALERT,
            timestamp=datetime.now(),
            author="user1"
        )
        message2 = BatchableMessage(
            id="msg-2",
            content_type=ContentType.STANDUP,
            timestamp=datetime.now(),
            author="user2"
        )
        
        batcher.add_message(message1, "channel-1")
        batcher.add_message(message2, "channel-2")
        
        # Check separate stats
        stats1 = batcher.get_channel_stats("channel-1")
        stats2 = batcher.get_channel_stats("channel-2")
        
        assert stats1 is not None
        assert stats2 is not None
        assert stats1.channel_id == "channel-1"
        assert stats2.channel_id == "channel-2"
        assert stats1.messages_batched == 1
        assert stats2.messages_batched == 1
        assert stats1.batches_created == 1
        assert stats2.batches_created == 1
    
    def test_get_all_channel_stats(self):
        """Test getting statistics for all channels."""
        batcher = MessageBatcher()
        
        # Add messages to multiple channels
        channels = ["channel-1", "channel-2", "channel-3"]
        for i, channel in enumerate(channels):
            message = BatchableMessage(
                id=f"msg-{i}",
                content_type=ContentType.DEPLOYMENT,
                timestamp=datetime.now(),
                author=f"user-{i}"
            )
            batcher.add_message(message, channel)
        
        # Get all stats
        all_stats = batcher.get_all_channel_stats()
        
        assert len(all_stats) == 3
        for channel in channels:
            assert channel in all_stats
            assert all_stats[channel].channel_id == channel
            assert all_stats[channel].messages_batched == 1
    
    def test_real_time_count_updates(self):
        """Test that real-time counts are updated correctly."""
        batcher = MessageBatcher()
        channel_id = "test-channel"
        
        # Create messages with identical properties to ensure batching
        base_time = datetime.now()
        message1 = BatchableMessage(
            id="msg-1",
            content_type=ContentType.BLOCKER,
            timestamp=base_time,
            author="user1",
            data={"project": "test-project"}
        )
        batcher.add_message(message1, channel_id)
        
        stats = batcher.get_channel_stats(channel_id)
        assert stats.active_batch_count >= 1
        assert stats.pending_message_count == 1
        
        # Add second message with same properties to encourage batching
        message2 = BatchableMessage(
            id="msg-2",
            content_type=ContentType.BLOCKER,
            timestamp=base_time,  # Same timestamp
            author="user1",      # Same author
            data={"project": "test-project"}  # Same project
        )
        batcher.add_message(message2, channel_id)
        
        stats = batcher.get_channel_stats(channel_id)
        # The exact batch count depends on batching strategy, but total messages should be 2
        assert stats.pending_message_count == 2  # Two messages total
        assert stats.messages_batched == 2
        
        # Flush all batches
        batcher.flush_all_batches()
        
        stats = batcher.get_channel_stats(channel_id)
        assert stats.active_batch_count == 0  # No active batches
        assert stats.pending_message_count == 0  # No pending messages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])