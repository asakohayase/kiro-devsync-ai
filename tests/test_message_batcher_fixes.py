#!/usr/bin/env python3
"""Test the MessageBatcher implementation consistency fixes."""

import pytest
from datetime import datetime
from devsync_ai.core.message_batcher import MessageBatcher, BatchableMessage, ContentType, BatchConfig


def test_channel_specific_data_structures():
    """Test that all methods consistently use _channel_batch_groups."""
    batcher = MessageBatcher()
    
    # Create test messages for different channels
    msg1 = BatchableMessage(
        id="msg1",
        content_type=ContentType.PR_UPDATE,
        timestamp=datetime.now(),
        author="user1",
        data={"repository": "test-repo", "action": "opened"}
    )
    
    msg2 = BatchableMessage(
        id="msg2", 
        content_type=ContentType.JIRA_UPDATE,
        timestamp=datetime.now(),
        author="user2",
        data={"key": "TEST-123", "summary": "Test ticket"}
    )
    
    # Add messages to different channels
    batcher.add_message(msg1, "channel1")
    batcher.add_message(msg2, "channel2")
    
    # Verify channel-specific storage
    assert "channel1" in batcher._channel_batch_groups
    assert "channel2" in batcher._channel_batch_groups
    assert len(batcher._channel_batch_groups["channel1"]) == 1
    assert len(batcher._channel_batch_groups["channel2"]) == 1


def test_statistics_accuracy():
    """Test that get_batch_stats() accurately reflects current state."""
    batcher = MessageBatcher()
    
    # Initial state
    stats = batcher.get_batch_stats()
    assert stats['active_batches'] == 0
    assert stats['pending_messages'] == 0
    assert stats['channels_active'] == 0
    
    # Add messages to different channels
    msg1 = BatchableMessage(
        id="msg1",
        content_type=ContentType.PR_UPDATE,
        timestamp=datetime.now(),
        author="user1"
    )
    
    msg2 = BatchableMessage(
        id="msg2",
        content_type=ContentType.JIRA_UPDATE,
        timestamp=datetime.now(),
        author="user2"
    )
    
    batcher.add_message(msg1, "channel1")
    batcher.add_message(msg2, "channel2")
    
    # Check statistics after adding messages
    stats = batcher.get_batch_stats()
    assert stats['active_batches'] == 2
    assert stats['pending_messages'] == 2
    assert stats['messages_batched'] == 2
    assert stats['batches_created'] == 2
    assert stats['channels_active'] == 2
    
    # Flush one channel
    flushed = batcher.flush_channel_batches("channel1")
    assert len(flushed) == 1
    
    # Check statistics after flushing
    stats = batcher.get_batch_stats()
    assert stats['active_batches'] == 1
    assert stats['pending_messages'] == 1
    assert stats['batches_flushed'] == 1
    assert stats['channels_active'] == 1


def test_resource_cleanup():
    """Test that resources are properly cleaned up when batches are flushed."""
    batcher = MessageBatcher()
    
    # Add message to create batch
    msg = BatchableMessage(
        id="msg1",
        content_type=ContentType.PR_UPDATE,
        timestamp=datetime.now(),
        author="user1"
    )
    
    batcher.add_message(msg, "test_channel")
    
    # Verify batch exists
    assert "test_channel" in batcher._channel_batch_groups
    assert len(batcher._channel_batch_groups["test_channel"]) == 1
    
    # Flush the channel
    flushed = batcher.flush_channel_batches("test_channel")
    assert len(flushed) == 1
    
    # Verify cleanup - channel should be removed when empty
    assert "test_channel" not in batcher._channel_batch_groups
    
    # Verify statistics reflect cleanup
    stats = batcher.get_batch_stats()
    assert stats['active_batches'] == 0
    assert stats['pending_messages'] == 0
    assert stats['channels_active'] == 0


def test_multi_channel_independence():
    """Test that different channels operate independently."""
    batcher = MessageBatcher()
    
    # Add messages to different channels
    for i in range(3):
        msg = BatchableMessage(
            id=f"msg_ch1_{i}",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author=f"user{i}"
        )
        batcher.add_message(msg, "channel1")
    
    for i in range(2):
        msg = BatchableMessage(
            id=f"msg_ch2_{i}",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=datetime.now(),
            author=f"user{i}"
        )
        batcher.add_message(msg, "channel2")
    
    # Verify independent storage
    assert len(batcher._channel_batch_groups["channel1"]) >= 1
    assert len(batcher._channel_batch_groups["channel2"]) >= 1
    
    # Get messages from channel1 batch
    ch1_batch = list(batcher._channel_batch_groups["channel1"].values())[0]
    ch1_messages = ch1_batch.messages
    
    # Get messages from channel2 batch  
    ch2_batch = list(batcher._channel_batch_groups["channel2"].values())[0]
    ch2_messages = ch2_batch.messages
    
    # Verify messages are in correct channels
    assert all(msg.id.startswith("msg_ch1_") for msg in ch1_messages)
    assert all(msg.id.startswith("msg_ch2_") for msg in ch2_messages)
    
    # Flush only channel1
    flushed_ch1 = batcher.flush_channel_batches("channel1")
    assert len(flushed_ch1) >= 1
    
    # Verify channel2 is unaffected
    assert "channel2" in batcher._channel_batch_groups
    assert len(batcher._channel_batch_groups["channel2"]) >= 1
    
    # Verify channel1 is cleaned up
    assert "channel1" not in batcher._channel_batch_groups


def test_no_batch_groups_attribute_references():
    """Test that no methods reference the non-existent _batch_groups attribute."""
    batcher = MessageBatcher()
    
    # Verify _batch_groups doesn't exist
    assert not hasattr(batcher, '_batch_groups')
    
    # Add a message and verify all operations work
    msg = BatchableMessage(
        id="test_msg",
        content_type=ContentType.PR_UPDATE,
        timestamp=datetime.now(),
        author="test_user"
    )
    
    # These operations should all work without referencing _batch_groups
    result = batcher.add_message(msg, "test_channel")
    stats = batcher.get_batch_stats()
    flushed = batcher.flush_all_batches()
    
    # All operations should complete successfully
    assert stats is not None
    assert isinstance(stats, dict)
    assert 'active_batches' in stats
    assert 'pending_messages' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])