"""Tests for _find_or_create_batch_group method with channel support."""

import pytest
from datetime import datetime, timedelta
from devsync_ai.core.message_batcher import (
    MessageBatcher, BatchableMessage, ContentType, BatchStrategy, BatchConfig
)


class TestFindOrCreateBatchGroup:
    """Test channel-aware batch group creation and retrieval."""
    
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
        self.message3 = BatchableMessage(
            id="msg3",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=self.base_time + timedelta(minutes=2),
            author="bob",
            data={"project": "TEST", "key": "TEST-456"}
        )
    
    def test_create_new_batch_group_for_channel(self):
        """Test creating new batch group for specific channel."""
        channel_id = "test-channel"
        
        # Find or create batch group (should create new one)
        batch_group = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        
        assert batch_group is not None
        assert batch_group.channel_id == channel_id
        assert len(batch_group.messages) == 0  # Message not added yet
        assert batch_group.id.startswith("pr_activity_")
        
        # Verify it's stored in correct channel dictionary using the storage key
        assert channel_id in self.batcher._channel_batch_groups
        storage_key = batch_group.metadata.get('storage_key')
        assert storage_key is not None
        assert storage_key in self.batcher._channel_batch_groups[channel_id]
        assert self.batcher._channel_batch_groups[channel_id][storage_key] == batch_group
    
    def test_find_existing_batch_group_in_same_channel(self):
        """Test finding existing batch group in the same channel."""
        channel_id = "test-channel"
        
        # Create first batch group
        batch_group1 = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        batch_group1.add_message(self.message1)
        
        # Find batch group for similar message in same channel
        batch_group2 = self.batcher._find_or_create_batch_group(self.message2, channel_id)
        
        # Should return the same batch group due to similarity
        assert batch_group1.id == batch_group2.id
        assert batch_group2.channel_id == channel_id
    
    def test_separate_batch_groups_for_different_channels(self):
        """Test that different channels get separate batch groups."""
        channel1 = "channel-1"
        channel2 = "channel-2"
        
        # Create batch groups in different channels with similar messages
        batch_group1 = self.batcher._find_or_create_batch_group(self.message1, channel1)
        batch_group2 = self.batcher._find_or_create_batch_group(self.message1, channel2)
        
        # Should be different batch groups
        assert batch_group1.id != batch_group2.id
        assert batch_group1.channel_id == channel1
        assert batch_group2.channel_id == channel2
        
        # Verify stored in correct channel dictionaries using storage keys
        storage_key1 = batch_group1.metadata.get('storage_key')
        storage_key2 = batch_group2.metadata.get('storage_key')
        
        assert storage_key1 is not None and storage_key1 in self.batcher._channel_batch_groups[channel1]
        assert storage_key2 is not None and storage_key2 in self.batcher._channel_batch_groups[channel2]
        assert storage_key1 not in self.batcher._channel_batch_groups[channel2]
        assert storage_key2 not in self.batcher._channel_batch_groups[channel1]
    
    def test_group_key_includes_channel_context(self):
        """Test that group keys include channel context for isolation."""
        channel1 = "channel-1"
        channel2 = "channel-2"
        
        # Generate group keys for same message in different channels
        key1 = self.batcher._get_group_key(self.message1, BatchStrategy.TIME_BASED, channel1)
        key2 = self.batcher._get_group_key(self.message1, BatchStrategy.TIME_BASED, channel2)
        
        # Keys should be different due to channel prefix
        assert key1 != key2
        assert f"ch_{channel1}" in key1
        assert f"ch_{channel2}" in key2
        assert "time_" in key1
        assert "time_" in key2
    
    def test_similarity_detection_within_channel_boundaries(self):
        """Test that similarity detection works within channel boundaries."""
        channel_id = "test-channel"
        
        # Create batch group with first message
        batch_group = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        batch_group.add_message(self.message1)
        
        # Test similarity for related message
        can_add = self.batcher._can_add_to_group(self.message2, batch_group, BatchStrategy.CONTENT_SIMILARITY)
        assert can_add is True  # Similar PR updates from same author/repo
        
        # Test similarity for unrelated message
        can_add_unrelated = self.batcher._can_add_to_group(self.message3, batch_group, BatchStrategy.CONTENT_SIMILARITY)
        assert can_add_unrelated is False  # Different content type and author
    
    def test_time_based_grouping_within_channel(self):
        """Test time-based grouping within channel boundaries."""
        channel_id = "test-channel"
        
        # Create batch group with first message
        batch_group = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        batch_group.add_message(self.message1)
        
        # Test time-based grouping for message within time window
        can_add = self.batcher._can_add_to_group(self.message2, batch_group, BatchStrategy.TIME_BASED)
        assert can_add is True  # Within 5-minute window
        
        # Test message outside time window
        old_message = BatchableMessage(
            id="old_msg",
            content_type=ContentType.PR_UPDATE,
            timestamp=self.base_time - timedelta(minutes=10),
            author="alice"
        )
        can_add_old = self.batcher._can_add_to_group(old_message, batch_group, BatchStrategy.TIME_BASED)
        assert can_add_old is False  # Outside time window
    
    def test_author_based_grouping_within_channel(self):
        """Test author-based grouping within channel boundaries."""
        channel_id = "test-channel"
        
        # Create batch group with first message
        batch_group = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        batch_group.add_message(self.message1)
        
        # Test same author and content type
        can_add = self.batcher._can_add_to_group(self.message2, batch_group, BatchStrategy.AUTHOR_BASED)
        assert can_add is True  # Same author and content type
        
        # Test different author
        can_add_different = self.batcher._can_add_to_group(self.message3, batch_group, BatchStrategy.AUTHOR_BASED)
        assert can_add_different is False  # Different author and content type
    
    def test_priority_based_grouping_within_channel(self):
        """Test priority-based grouping within channel boundaries."""
        channel_id = "test-channel"
        
        # Create messages with same priority
        high_priority_msg1 = BatchableMessage(
            id="high1",
            content_type=ContentType.ALERT,
            timestamp=self.base_time,
            priority="high"
        )
        high_priority_msg2 = BatchableMessage(
            id="high2",
            content_type=ContentType.ALERT,
            timestamp=self.base_time + timedelta(minutes=1),
            priority="high"
        )
        low_priority_msg = BatchableMessage(
            id="low1",
            content_type=ContentType.ALERT,
            timestamp=self.base_time + timedelta(minutes=2),
            priority="low"
        )
        
        # Create batch group with high priority message
        batch_group = self.batcher._find_or_create_batch_group(high_priority_msg1, channel_id)
        batch_group.add_message(high_priority_msg1)
        
        # Test same priority and content type
        can_add_same = self.batcher._can_add_to_group(high_priority_msg2, batch_group, BatchStrategy.PRIORITY_BASED)
        assert can_add_same is True
        
        # Test different priority
        can_add_different = self.batcher._can_add_to_group(low_priority_msg, batch_group, BatchStrategy.PRIORITY_BASED)
        assert can_add_different is False
    
    def test_batch_size_limit_enforcement(self):
        """Test that batch size limits are enforced within channels."""
        channel_id = "test-channel"
        
        # Create batch group and fill to capacity
        batch_group = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        
        # Add messages up to the limit
        for i in range(self.config.max_batch_size):
            msg = BatchableMessage(
                id=f"msg_{i}",
                content_type=ContentType.PR_UPDATE,
                timestamp=self.base_time + timedelta(seconds=i),
                author="alice"
            )
            batch_group.add_message(msg)
        
        # Try to add one more message
        extra_message = BatchableMessage(
            id="extra",
            content_type=ContentType.PR_UPDATE,
            timestamp=self.base_time + timedelta(minutes=1),
            author="alice"
        )
        
        can_add = self.batcher._can_add_to_group(extra_message, batch_group, BatchStrategy.CONTENT_SIMILARITY)
        assert can_add is False  # Should reject due to size limit
    
    def test_age_limit_enforcement(self):
        """Test that age limits are enforced within channels."""
        channel_id = "test-channel"
        
        # Create batch group with old timestamp
        old_time = self.base_time - timedelta(minutes=10)
        old_batch_group = self.batcher._find_or_create_batch_group(self.message1, channel_id)
        old_batch_group.created_at = old_time
        old_batch_group.add_message(self.message1)
        
        # Try to add new message to old batch
        can_add = self.batcher._can_add_to_group(self.message2, old_batch_group, BatchStrategy.TIME_BASED)
        assert can_add is False  # Should reject due to age limit
    
    def test_multiple_strategies_channel_isolation(self):
        """Test that multiple strategies work with channel isolation."""
        channel1 = "channel-1"
        channel2 = "channel-2"
        
        # Configure batcher with multiple strategies
        self.batcher.config.strategies = [BatchStrategy.TIME_BASED, BatchStrategy.CONTENT_SIMILARITY, BatchStrategy.AUTHOR_BASED]
        
        # Create batch groups in different channels
        batch_group1 = self.batcher._find_or_create_batch_group(self.message1, channel1)
        batch_group2 = self.batcher._find_or_create_batch_group(self.message1, channel2)
        
        # Should create separate groups despite same message
        assert batch_group1.id != batch_group2.id
        assert batch_group1.channel_id == channel1
        assert batch_group2.channel_id == channel2
        
        # Verify channel isolation in storage
        assert len(self.batcher._channel_batch_groups) == 2
        assert channel1 in self.batcher._channel_batch_groups
        assert channel2 in self.batcher._channel_batch_groups