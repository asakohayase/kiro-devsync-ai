"""Unit tests for enhanced BatchGroup functionality."""

import pytest
from datetime import datetime, timedelta
from devsync_ai.core.message_batcher import (
    BatchGroup, BatchableMessage, BatchType, ContentType
)


class TestEnhancedBatchGroup:
    """Test enhanced BatchGroup with channel awareness."""
    
    def test_batch_group_creation_with_channel_id(self):
        """Test BatchGroup creation with channel_id field."""
        channel_id = "test-channel"
        batch_group = BatchGroup(
            id="test-batch",
            channel_id=channel_id,
            batch_type=BatchType.DAILY_SUMMARY
        )
        
        assert batch_group.channel_id == channel_id
        assert batch_group.id == "test-batch"
        assert batch_group.batch_type == BatchType.DAILY_SUMMARY
        assert isinstance(batch_group.last_activity, datetime)
        assert len(batch_group.messages) == 0
    
    def test_last_activity_field_initialization(self):
        """Test that last_activity field is properly initialized."""
        batch_group = BatchGroup(
            id="test-batch",
            channel_id="test-channel",
            batch_type=BatchType.PR_ACTIVITY
        )
        
        # Should be initialized to current time
        assert isinstance(batch_group.last_activity, datetime)
        # Should be very recent (within last second)
        time_diff = datetime.now() - batch_group.last_activity
        assert time_diff.total_seconds() < 1.0
    
    def test_add_message_updates_last_activity(self):
        """Test that adding a message updates last_activity timestamp."""
        batch_group = BatchGroup(
            id="test-batch",
            channel_id="test-channel",
            batch_type=BatchType.JIRA_ACTIVITY
        )
        
        # Record initial last_activity
        initial_activity = batch_group.last_activity
        
        # Wait a small amount to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        # Add a message
        message = BatchableMessage(
            id="msg-1",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=datetime.now(),
            author="test-user"
        )
        batch_group.add_message(message)
        
        # Verify last_activity was updated
        assert batch_group.last_activity > initial_activity
        assert len(batch_group.messages) == 1
    
    def test_should_flush_with_configurable_max_size_default_5(self):
        """Test should_flush method with default max_size of 5."""
        batch_group = BatchGroup(
            id="test-batch",
            channel_id="test-channel",
            batch_type=BatchType.ALERT_DIGEST
        )
        
        # Add messages up to the default limit (5)
        for i in range(4):
            message = BatchableMessage(
                id=f"msg-{i}",
                content_type=ContentType.ALERT,
                timestamp=datetime.now(),
                author="test-user"
            )
            batch_group.add_message(message)
        
        # Should not flush with 4 messages
        assert not batch_group.should_flush()
        
        # Add 5th message - should trigger flush
        message = BatchableMessage(
            id="msg-5",
            content_type=ContentType.ALERT,
            timestamp=datetime.now(),
            author="test-user"
        )
        batch_group.add_message(message)
        
        # Should flush with 5 messages (default max_size)
        assert batch_group.should_flush()
    
    def test_should_flush_with_custom_max_size(self):
        """Test should_flush method with custom max_size parameter."""
        batch_group = BatchGroup(
            id="test-batch",
            channel_id="test-channel",
            batch_type=BatchType.PR_ACTIVITY
        )
        
        # Add 3 messages
        for i in range(3):
            message = BatchableMessage(
                id=f"msg-{i}",
                content_type=ContentType.PR_UPDATE,
                timestamp=datetime.now(),
                author="test-user"
            )
            batch_group.add_message(message)
        
        # Should not flush with custom max_size=5
        assert not batch_group.should_flush(max_size=5)
        
        # Should flush with custom max_size=3
        assert batch_group.should_flush(max_size=3)
        
        # Should flush with custom max_size=2
        assert batch_group.should_flush(max_size=2)
    
    def test_should_flush_with_time_limit(self):
        """Test should_flush method with time-based flushing."""
        # Create batch group with past creation time
        past_time = datetime.now() - timedelta(minutes=6)
        batch_group = BatchGroup(
            id="test-batch",
            channel_id="test-channel",
            batch_type=BatchType.TEAM_ACTIVITY,
            created_at=past_time
        )
        
        # Add one message
        message = BatchableMessage(
            id="msg-1",
            content_type=ContentType.STANDUP,
            timestamp=datetime.now(),
            author="test-user"
        )
        batch_group.add_message(message)
        
        # Should flush due to age (6 minutes > 5 minute default)
        assert batch_group.should_flush()
        
        # Should not flush with custom max_age_minutes=10
        assert not batch_group.should_flush(max_age_minutes=10)
    
    def test_should_flush_with_expires_at(self):
        """Test should_flush method with expires_at timestamp."""
        batch_group = BatchGroup(
            id="test-batch",
            channel_id="test-channel",
            batch_type=BatchType.WEEKLY_CHANGELOG,
            expires_at=datetime.now() - timedelta(minutes=1)  # Expired 1 minute ago
        )
        
        # Should flush due to expiration
        assert batch_group.should_flush()
        
        # Test with future expiration
        batch_group.expires_at = datetime.now() + timedelta(minutes=5)
        assert not batch_group.should_flush()
    
    def test_should_flush_multiple_conditions(self):
        """Test should_flush method with multiple conditions."""
        batch_group = BatchGroup(
            id="test-batch",
            channel_id="test-channel",
            batch_type=BatchType.CUSTOM
        )
        
        # Add messages just under the limit
        for i in range(4):
            message = BatchableMessage(
                id=f"msg-{i}",
                content_type=ContentType.DEPLOYMENT,
                timestamp=datetime.now(),
                author="test-user"
            )
            batch_group.add_message(message)
        
        # Should not flush (4 < 5 messages, recent creation)
        assert not batch_group.should_flush()
        
        # Add one more message to hit the limit
        message = BatchableMessage(
            id="msg-5",
            content_type=ContentType.DEPLOYMENT,
            timestamp=datetime.now(),
            author="test-user"
        )
        batch_group.add_message(message)
        
        # Should flush due to size limit
        assert batch_group.should_flush()
    
    def test_batch_group_metadata_without_channel_id_duplication(self):
        """Test that channel_id is not duplicated in metadata."""
        channel_id = "production-alerts"
        batch_group = BatchGroup(
            id="test-batch",
            channel_id=channel_id,
            batch_type=BatchType.ALERT_DIGEST,
            metadata={
                'primary_content_type': 'alert',
                'primary_author': 'system',
                'created_by_strategy': 'time_based'
            }
        )
        
        # Channel ID should be in the field, not duplicated in metadata
        assert batch_group.channel_id == channel_id
        assert 'channel_id' not in batch_group.metadata
        assert batch_group.metadata['primary_content_type'] == 'alert'
    
    def test_get_summary_stats_includes_channel_context(self):
        """Test that summary stats work correctly with channel-aware batch groups."""
        batch_group = BatchGroup(
            id="test-batch",
            channel_id="dev-team",
            batch_type=BatchType.SPRINT_UPDATE
        )
        
        # Add diverse messages
        messages = [
            BatchableMessage(
                id="msg-1",
                content_type=ContentType.PR_UPDATE,
                timestamp=datetime.now(),
                author="alice",
                priority="high"
            ),
            BatchableMessage(
                id="msg-2",
                content_type=ContentType.JIRA_UPDATE,
                timestamp=datetime.now() + timedelta(minutes=1),
                author="bob",
                priority="medium"
            ),
            BatchableMessage(
                id="msg-3",
                content_type=ContentType.PR_UPDATE,
                timestamp=datetime.now() + timedelta(minutes=2),
                author="alice",
                priority="low"
            )
        ]
        
        for message in messages:
            batch_group.add_message(message)
        
        stats = batch_group.get_summary_stats()
        
        # Verify stats are calculated correctly
        assert stats['total_count'] == 3
        assert stats['content_types']['pr_update'] == 2
        assert stats['content_types']['jira_update'] == 1
        assert set(stats['authors']) == {'alice', 'bob'}
        assert stats['priority_counts']['high'] == 1
        assert stats['priority_counts']['medium'] == 1
        assert stats['priority_counts']['low'] == 1
        
        # Verify time range
        assert stats['time_range']['start'] == messages[0].timestamp
        assert stats['time_range']['end'] == messages[2].timestamp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])