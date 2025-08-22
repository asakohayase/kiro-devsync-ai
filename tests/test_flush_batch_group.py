"""Tests for _flush_batch_group method with proper cleanup."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from devsync_ai.core.message_batcher import (
    MessageBatcher, BatchableMessage, ContentType, BatchStrategy, BatchConfig, BatchGroup, BatchType
)


class TestFlushBatchGroup:
    """Test enhanced batch group flushing with proper cleanup."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = BatchConfig(
            max_batch_size=5,
            max_batch_age_minutes=5,
            similarity_threshold=0.7,
            strategies=[BatchStrategy.TIME_BASED, BatchStrategy.CONTENT_SIMILARITY]
        )
        self.batcher = MessageBatcher(config=self.config)
        
        # Create test messages
        self.base_time = datetime.now()
        self.message1 = BatchableMessage(
            id="msg1",
            content_type=ContentType.PR_UPDATE,
            timestamp=self.base_time,
            author="alice",
            data={"repository": "test-repo", "number": 123}
        )
        self.message2 = BatchableMessage(
            id="msg2",
            content_type=ContentType.PR_UPDATE,
            timestamp=self.base_time + timedelta(minutes=1),
            author="alice",
            data={"repository": "test-repo", "number": 124}
        )
    
    def test_flush_empty_batch_group(self):
        """Test flushing empty batch group returns None."""
        channel_id = "test-channel"
        
        # Create empty batch group
        batch_group = BatchGroup(
            id="empty_batch",
            channel_id=channel_id,
            batch_type=BatchType.PR_ACTIVITY
        )
        
        result = self.batcher._flush_batch_group(batch_group, channel_id)
        assert result is None
    
    def test_successful_batch_flush_with_cleanup(self):
        """Test successful batch flush with proper cleanup."""
        channel_id = "test-channel"
        
        # Add messages through the batcher to properly update statistics
        self.batcher.add_message(self.message1, channel_id)
        self.batcher.add_message(self.message2, channel_id)
        
        # Get the batch group that was created
        batch_group = list(self.batcher._channel_batch_groups[channel_id].values())[0]
        
        # Store initial state
        initial_batch_count = len(self.batcher._channel_batch_groups[channel_id])
        initial_stats = self.batcher._stats['batches_flushed']
        
        # Flush the batch
        result = self.batcher._flush_batch_group(batch_group, channel_id)
        
        # Verify successful flush
        assert result is not None
        assert hasattr(result, 'blocks')
        assert hasattr(result, 'text')
        
        # Verify cleanup - batch should be removed from storage
        storage_key = batch_group.metadata.get('storage_key')
        assert storage_key not in self.batcher._channel_batch_groups[channel_id]
        
        # Verify statistics updated
        assert self.batcher._stats['batches_flushed'] == initial_stats + 1
        
        # Verify channel stats updated
        channel_stats = self.batcher.get_channel_stats(channel_id)
        assert channel_stats.batches_sent == 1
        assert channel_stats.messages_batched == 2
    
    def test_batch_flush_removes_empty_channel_dictionary(self):
        """Test that empty channel dictionaries are cleaned up."""
        channel_id = "test-channel"
        
        # Create and add batch group (only one in the channel)
        batch_group = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        batch_group.add_message(self.message1)
        
        # Verify channel exists
        assert channel_id in self.batcher._channel_batch_groups
        
        # Flush the batch
        result = self.batcher._flush_batch_group(batch_group, channel_id)
        
        # Verify successful flush
        assert result is not None
        
        # Verify empty channel dictionary is cleaned up
        assert channel_id not in self.batcher._channel_batch_groups
        
        # Verify channels_active count decreased
        assert self.batcher._stats['channels_active'] == 0
    
    def test_batch_flush_preserves_other_batches_in_channel(self):
        """Test that flushing one batch doesn't affect others in the same channel."""
        channel_id = "test-channel"
        
        # Create two different batch groups in same channel
        batch_group1 = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        batch_group1.add_message(self.message1)
        
        # Create a different message that will create a separate batch
        different_message = BatchableMessage(
            id="msg3",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=self.base_time,
            author="bob",
            data={"project": "TEST", "key": "TEST-456"}
        )
        batch_group2 = self.batcher._find_or_create_batch_group(different_message, channel_id)
        batch_group2.add_message(different_message)
        
        # Verify both batches exist
        assert len(self.batcher._channel_batch_groups[channel_id]) == 2
        
        # Flush first batch
        result = self.batcher._flush_batch_group(batch_group1, channel_id)
        
        # Verify first batch flushed successfully
        assert result is not None
        
        # Verify second batch still exists
        assert len(self.batcher._channel_batch_groups[channel_id]) == 1
        storage_key2 = batch_group2.metadata.get('storage_key')
        assert storage_key2 in self.batcher._channel_batch_groups[channel_id]
        
        # Verify channel dictionary not cleaned up
        assert channel_id in self.batcher._channel_batch_groups
    
    def test_batch_flush_updates_global_statistics(self):
        """Test that global statistics are properly updated."""
        channel_id = "test-channel"
        
        # Create and add batch group
        batch_group = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        batch_group.add_message(self.message1)
        batch_group.add_message(self.message2)
        
        # Store initial statistics
        initial_batches_flushed = self.batcher._stats['batches_flushed']
        initial_channel_count = self.batcher._stats['batches_by_channel'][channel_id]
        initial_type_count = self.batcher._stats['batches_by_type'][BatchType.PR_ACTIVITY.value]
        
        # Flush the batch
        result = self.batcher._flush_batch_group(batch_group, channel_id)
        
        # Verify statistics updated
        assert result is not None
        assert self.batcher._stats['batches_flushed'] == initial_batches_flushed + 1
        
        # Note: batches_by_channel and batches_by_type should decrease when batch is flushed
        assert self.batcher._stats['batches_by_channel'][channel_id] == max(0, initial_channel_count - 1)
        assert self.batcher._stats['batches_by_type'][BatchType.PR_ACTIVITY.value] == max(0, initial_type_count - 1)
    
    def test_batch_flush_memory_cleanup(self):
        """Test that memory cleanup is performed."""
        channel_id = "test-channel"
        
        # Add messages through the batcher to properly update statistics
        self.batcher.add_message(self.message1, channel_id)
        self.batcher.add_message(self.message2, channel_id)
        
        # Get the batch group that was created
        batch_group = list(self.batcher._channel_batch_groups[channel_id].values())[0]
        
        # Verify batch has data before flush
        assert len(batch_group.messages) == 2
        assert len(batch_group.metadata) > 0
        
        # Flush the batch
        result = self.batcher._flush_batch_group(batch_group, channel_id)
        
        # Verify successful flush
        assert result is not None
        
        # Verify memory cleanup - messages and metadata should be cleared
        assert len(batch_group.messages) == 0
        assert len(batch_group.metadata) == 0
        assert batch_group.expires_at is None
    
    def test_batch_flush_error_handling_with_recovery(self):
        """Test error handling and recovery mechanisms."""
        channel_id = "test-channel"
        
        # Create and add batch group
        batch_group = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        batch_group.add_message(self.message1)
        
        # Mock _create_batched_message to raise an exception
        with patch.object(self.batcher, '_create_batched_message', side_effect=Exception("Test error")):
            result = self.batcher._flush_batch_group(batch_group, channel_id)
            
            # Should return None on error
            assert result is None
            
            # Batch should be restored to storage after failure
            storage_key = batch_group.metadata.get('storage_key')
            assert storage_key in self.batcher._channel_batch_groups[channel_id]
    
    def test_batch_flush_handles_missing_storage_key(self):
        """Test handling of batch groups without storage keys."""
        channel_id = "test-channel"
        
        # Create batch group without storage key
        batch_group = BatchGroup(
            id="test_batch",
            channel_id=channel_id,
            batch_type=BatchType.PR_ACTIVITY,
            metadata={}  # No storage_key
        )
        batch_group.add_message(self.message1)
        
        # Should handle gracefully
        result = self.batcher._flush_batch_group(batch_group, channel_id)
        
        # Should still create message despite missing storage key
        assert result is not None
    
    def test_batch_flush_handles_missing_channel(self):
        """Test handling of batch groups for non-existent channels."""
        channel_id = "non-existent-channel"
        
        # Create batch group for non-existent channel
        batch_group = BatchGroup(
            id="test_batch",
            channel_id=channel_id,
            batch_type=BatchType.PR_ACTIVITY,
            metadata={'storage_key': 'test_key'}
        )
        batch_group.add_message(self.message1)
        
        # Should handle gracefully
        result = self.batcher._flush_batch_group(batch_group, channel_id)
        
        # Should still create message despite missing channel
        assert result is not None
    
    def test_batch_flush_statistics_error_handling(self):
        """Test that statistics errors don't fail the entire operation."""
        channel_id = "test-channel"
        
        # Create and add batch group
        batch_group = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        batch_group.add_message(self.message1)
        
        # Mock channel stats to raise an exception
        with patch.object(self.batcher._channel_stats[channel_id], 'update_batch_sent', side_effect=Exception("Stats error")):
            result = self.batcher._flush_batch_group(batch_group, channel_id)
            
            # Should still succeed despite statistics error
            assert result is not None
            
            # Batch should still be removed from storage
            storage_key = batch_group.metadata.get('storage_key')
            assert storage_key not in self.batcher._channel_batch_groups[channel_id]
    
    def test_batch_flush_cleanup_error_handling(self):
        """Test that cleanup errors don't fail the entire operation."""
        channel_id = "test-channel"
        
        # Create and add batch group
        batch_group = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        batch_group.add_message(self.message1)
        
        # Replace the messages list with a mock that raises an exception on clear
        original_messages = batch_group.messages
        mock_messages = MagicMock()
        mock_messages.__len__ = lambda self: len(original_messages)
        mock_messages.__iter__ = lambda self: iter(original_messages)
        mock_messages.__getitem__ = lambda self, key: original_messages[key]
        mock_messages.clear.side_effect = Exception("Cleanup error")
        batch_group.messages = mock_messages
        
        result = self.batcher._flush_batch_group(batch_group, channel_id)
        
        # Should still succeed despite cleanup error
        assert result is not None
        
        # Batch should still be removed from storage
        storage_key = batch_group.metadata.get('storage_key')
        assert storage_key not in self.batcher._channel_batch_groups[channel_id]
    
    def test_flush_channel_batches_error_handling(self):
        """Test error handling in flush_channel_batches method."""
        channel_id = "test-channel"
        
        # Create multiple batch groups
        batch_group1 = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        batch_group1.add_message(self.message1)
        
        different_message = BatchableMessage(
            id="msg3",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=self.base_time,
            author="bob",
            data={"project": "TEST", "key": "TEST-456"}
        )
        batch_group2 = self.batcher._find_or_create_batch_group(different_message, channel_id)
        batch_group2.add_message(different_message)
        
        # Mock _flush_batch_group to fail for first batch but succeed for second
        original_flush = self.batcher._flush_batch_group
        call_count = 0
        
        def mock_flush(batch_group, channel_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # Simulate failure
            return original_flush(batch_group, channel_id)
        
        with patch.object(self.batcher, '_flush_batch_group', side_effect=mock_flush):
            results = self.batcher.flush_channel_batches(channel_id)
            
            # Should get one successful result despite one failure
            assert len(results) == 1
            assert results[0] is not None
    
    def test_flush_expired_batches_error_handling(self):
        """Test error handling in flush_expired_batches method."""
        channel_id = "test-channel"
        
        # Create expired batch group
        batch_group = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        batch_group.add_message(self.message1)
        
        # Make it expired
        batch_group.created_at = datetime.now() - timedelta(minutes=10)
        
        # Mock _flush_batch_group to fail
        with patch.object(self.batcher, '_flush_batch_group', return_value=None):
            results = self.batcher.flush_expired_batches()
            
            # Should handle failure gracefully
            assert len(results) == 0