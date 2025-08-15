"""Tests for smart message batching with spam prevention and timing controls."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from collections import deque

from devsync_ai.core.smart_message_batcher import (
    SmartMessageBatcher, SpamPreventionConfig, TimingConfig,
    SpamPreventionStrategy, TimingMode, ActivityMetrics
)
from devsync_ai.core.message_batcher import BatchableMessage, ContentType, BatchConfig


class TestSmartMessageBatcher:
    """Test suite for SmartMessageBatcher."""
    
    @pytest.fixture
    def spam_config(self):
        """Create spam prevention configuration for testing."""
        return SpamPreventionConfig(
            enabled=True,
            max_messages_per_minute=5,
            max_messages_per_hour=50,
            burst_threshold=3,
            burst_window_seconds=30,
            cooldown_after_burst_minutes=2,
            duplicate_content_window_minutes=10,
            quiet_hours_start=22,
            quiet_hours_end=8,
            quiet_hours_enabled=True
        )
    
    @pytest.fixture
    def timing_config(self):
        """Create timing configuration for testing."""
        return TimingConfig(
            mode=TimingMode.ADAPTIVE,
            base_interval_minutes=2,
            max_interval_minutes=10,
            min_interval_minutes=1,
            adaptive_factor=1.5
        )
    
    @pytest.fixture
    def batch_config(self):
        """Create batch configuration for testing."""
        return BatchConfig(
            enabled=True,
            max_batch_size=5,
            max_batch_age_minutes=3
        )
    
    @pytest.fixture
    def batcher(self, batch_config, spam_config, timing_config):
        """Create SmartMessageBatcher instance for testing."""
        return SmartMessageBatcher(
            config=batch_config,
            spam_config=spam_config,
            timing_config=timing_config
        )
    
    @pytest.fixture
    def sample_message(self):
        """Create sample message for testing."""
        return BatchableMessage(
            id="test_msg_1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="test_user",
            priority="medium",
            data={
                "title": "Test PR",
                "number": 123,
                "repository": "test-repo"
            }
        )
    
    def test_initialization(self, batcher):
        """Test SmartMessageBatcher initialization."""
        assert batcher.spam_config.enabled is True
        assert batcher.timing_config.mode == TimingMode.ADAPTIVE
        assert len(batcher._channel_activity) == 0
        assert len(batcher._content_hashes) == 0
        assert batcher._spam_stats['messages_blocked'] == 0
    
    def test_rate_limiting(self, batcher, sample_message):
        """Test rate limiting functionality."""
        channel_id = "test_channel"
        
        # Send messages up to the limit
        for i in range(5):
            message = BatchableMessage(
                id=f"msg_{i}",
                content_type=ContentType.PR_UPDATE,
                timestamp=datetime.now(),
                author="test_user",
                priority="medium",
                data={"title": f"PR {i}"}
            )
            result = batcher.add_message(message, channel_id)
        
        # Next message should be rate limited
        excess_message = BatchableMessage(
            id="excess_msg",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="test_user",
            priority="medium",
            data={"title": "Excess PR"}
        )
        
        result = batcher.add_message(excess_message, channel_id)
        stats = batcher.get_spam_prevention_stats()
        assert stats['rate_limited'] > 0
    
    def test_content_deduplication(self, batcher):
        """Test content deduplication functionality."""
        channel_id = "test_channel"
        
        # Create identical messages
        message1 = BatchableMessage(
            id="msg_1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="test_user",
            priority="medium",
            data={"title": "Duplicate PR", "number": 123}
        )
        
        message2 = BatchableMessage(
            id="msg_2",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="test_user",
            priority="medium",
            data={"title": "Duplicate PR", "number": 123}
        )
        
        # First message should be processed
        result1 = batcher.add_message(message1, channel_id)
        
        # Second identical message should be filtered
        result2 = batcher.add_message(message2, channel_id)
        
        stats = batcher.get_spam_prevention_stats()
        assert stats['duplicates_filtered'] > 0
    
    def test_burst_detection(self, batcher):
        """Test burst detection and cooldown."""
        channel_id = "test_channel"
        current_time = datetime.now()
        
        # Send burst of messages rapidly to trigger burst detection
        for i in range(4):  # Exceeds burst_threshold of 3
            message = BatchableMessage(
                id=f"burst_msg_{i}",
                content_type=ContentType.ALERT,
                timestamp=current_time + timedelta(seconds=i),
                author="test_user",
                priority="high",
                data={"title": f"Alert {i}"}
            )
            # Manually update activity metrics to simulate burst
            batcher._update_activity_metrics(message, channel_id)
        
        # Check if cooldown is triggered
        activity = batcher._channel_activity[channel_id]
        # The burst detection should have triggered cooldown
        if activity.current_burst_size >= batcher.spam_config.burst_threshold:
            assert activity.in_cooldown is True
            assert activity.cooldown_until is not None
        
        # Test that a message during cooldown gets blocked
        cooldown_message = BatchableMessage(
            id="cooldown_msg",
            content_type=ContentType.ALERT,
            timestamp=current_time + timedelta(seconds=5),
            author="test_user",
            priority="medium",
            data={"title": "Cooldown Alert"}
        )
        
        # If in cooldown, message should be blocked
        if activity.in_cooldown:
            result = batcher.add_message(cooldown_message, channel_id)
            stats = batcher.get_spam_prevention_stats()
            assert stats['burst_cooldowns'] > 0
    
    @patch('devsync_ai.core.smart_message_batcher.datetime')
    def test_quiet_hours(self, mock_datetime, batcher):
        """Test quiet hours functionality."""
        # Mock current time to be during quiet hours (11 PM)
        quiet_time = datetime(2024, 1, 1, 23, 0, 0)
        mock_datetime.now.return_value = quiet_time
        
        channel_id = "test_channel"
        
        # Non-critical message during quiet hours should be delayed
        message = BatchableMessage(
            id="quiet_msg",
            content_type=ContentType.PR_UPDATE,
            timestamp=quiet_time,
            author="test_user",
            priority="medium",
            data={"title": "Quiet Hours PR"}
        )
        
        result = batcher.add_message(message, channel_id)
        stats = batcher.get_spam_prevention_stats()
        assert stats['quiet_hours_delayed'] > 0
        
        # Critical message should bypass quiet hours
        critical_message = BatchableMessage(
            id="critical_msg",
            content_type=ContentType.ALERT,
            timestamp=quiet_time,
            author="test_user",
            priority="critical",
            data={"title": "Critical Alert"}
        )
        
        # Reset mock to allow processing
        mock_datetime.now.return_value = quiet_time
        result = batcher.add_message(critical_message, channel_id)
        # Critical messages should not be blocked by quiet hours
    
    def test_adaptive_timing(self, batcher, sample_message):
        """Test adaptive timing calculation."""
        channel_id = "test_channel"
        
        # Add some activity to the channel
        for i in range(3):
            message = BatchableMessage(
                id=f"activity_msg_{i}",
                content_type=ContentType.PR_UPDATE,
                timestamp=datetime.now() - timedelta(minutes=i),
                author="test_user",
                priority="medium",
                data={"title": f"Activity PR {i}"}
            )
            batcher._update_activity_metrics(message, channel_id)
        
        # Calculate delay for new message
        delay = batcher._calculate_optimal_delay(sample_message, channel_id)
        
        # Should have some delay due to recent activity
        assert delay > 0
        assert delay <= batcher.timing_config.max_interval_minutes * 60
    
    def test_priority_timing_overrides(self, batcher):
        """Test priority-based timing overrides."""
        channel_id = "test_channel"
        
        # Critical message should have no delay
        critical_message = BatchableMessage(
            id="critical_msg",
            content_type=ContentType.ALERT,
            timestamp=datetime.now(),
            author="test_user",
            priority="critical",
            data={"title": "Critical Alert"}
        )
        
        delay = batcher._calculate_optimal_delay(critical_message, channel_id)
        assert delay == 0
        
        # Low priority message should have longer delay
        low_priority_message = BatchableMessage(
            id="low_msg",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="test_user",
            priority="low",
            data={"title": "Low Priority PR"}
        )
        
        delay = batcher._calculate_optimal_delay(low_priority_message, channel_id)
        assert delay > 0
    
    def test_content_hash_generation(self, batcher):
        """Test content hash generation for deduplication."""
        message1 = BatchableMessage(
            id="msg_1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="user1",
            priority="medium",
            data={"title": "Test PR", "number": 123, "repository": "repo1"}
        )
        
        message2 = BatchableMessage(
            id="msg_2",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="user1",
            priority="medium",
            data={"title": "Test PR", "number": 123, "repository": "repo1"}
        )
        
        message3 = BatchableMessage(
            id="msg_3",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="user1",
            priority="medium",
            data={"title": "Different PR", "number": 124, "repository": "repo1"}
        )
        
        hash1 = batcher._generate_content_hash(message1)
        hash2 = batcher._generate_content_hash(message2)
        hash3 = batcher._generate_content_hash(message3)
        
        # Identical messages should have same hash
        assert hash1 == hash2
        
        # Different messages should have different hashes
        assert hash1 != hash3
    
    def test_activity_metrics_tracking(self, batcher):
        """Test activity metrics tracking."""
        channel_id = "test_channel"
        current_time = datetime.now()
        
        message = BatchableMessage(
            id="metrics_msg",
            content_type=ContentType.PR_UPDATE,
            timestamp=current_time,
            author="test_user",
            priority="medium",
            data={"title": "Metrics PR"}
        )
        
        # Update activity metrics
        batcher._update_activity_metrics(message, channel_id)
        
        # Check metrics
        activity = batcher._channel_activity[channel_id]
        assert len(activity.message_timestamps) == 1
        # Allow for small time differences due to processing
        assert abs((activity.last_message_time - current_time).total_seconds()) < 1
        assert activity.hourly_counts[current_time.hour] == 1
        assert activity.daily_counts[current_time.strftime('%Y-%m-%d')] == 1
    
    def test_channel_activity_summary(self, batcher):
        """Test channel activity summary generation."""
        channel_id = "test_channel"
        current_time = datetime.now()
        
        # Add some activity
        for i in range(5):
            message = BatchableMessage(
                id=f"summary_msg_{i}",
                content_type=ContentType.PR_UPDATE,
                timestamp=current_time - timedelta(minutes=i * 10),
                author="test_user",
                priority="medium",
                data={"title": f"Summary PR {i}"}
            )
            batcher._update_activity_metrics(message, channel_id)
        
        # Get summary
        summary = batcher.get_channel_activity_summary(channel_id)
        
        assert summary['total_messages'] == 5
        assert summary['messages_last_hour'] >= 0
        assert summary['messages_last_day'] == 5
        assert 'last_message_time' in summary
        assert 'hourly_distribution' in summary
    
    def test_spam_prevention_stats(self, batcher):
        """Test spam prevention statistics."""
        stats = batcher.get_spam_prevention_stats()
        
        expected_keys = [
            'messages_blocked', 'duplicates_filtered', 'rate_limited',
            'burst_cooldowns', 'quiet_hours_delayed', 'adaptive_delays',
            'active_channels', 'channels_in_cooldown', 'total_content_hashes',
            'burst_events_last_hour'
        ]
        
        for key in expected_keys:
            assert key in stats
            assert isinstance(stats[key], (int, float))
    
    def test_config_updates(self, batcher):
        """Test configuration updates."""
        # Update spam config
        new_spam_config = SpamPreventionConfig(
            enabled=True,
            max_messages_per_minute=20,
            max_messages_per_hour=200
        )
        
        batcher.update_spam_config(new_spam_config)
        assert batcher.spam_config.max_messages_per_minute == 20
        
        # Update timing config
        new_timing_config = TimingConfig(
            mode=TimingMode.FIXED_INTERVAL,
            base_interval_minutes=10
        )
        
        batcher.update_timing_config(new_timing_config)
        assert batcher.timing_config.mode == TimingMode.FIXED_INTERVAL
        assert batcher.timing_config.base_interval_minutes == 10
    
    def test_channel_reset(self, batcher, sample_message):
        """Test channel activity reset."""
        channel_id = "test_channel"
        
        # Add some activity
        batcher.add_message(sample_message, channel_id)
        assert channel_id in batcher._channel_activity
        
        # Reset channel
        result = batcher.reset_channel_activity(channel_id)
        assert result is True
        assert channel_id not in batcher._channel_activity
        
        # Reset non-existent channel
        result = batcher.reset_channel_activity("non_existent")
        assert result is False


class TestSpamPreventionConfig:
    """Test suite for SpamPreventionConfig."""
    
    def test_default_config(self):
        """Test default spam prevention configuration."""
        config = SpamPreventionConfig()
        
        assert config.enabled is True
        assert config.max_messages_per_minute == 10
        assert config.max_messages_per_hour == 100
        assert config.burst_threshold == 5
        assert config.quiet_hours_enabled is True
        assert SpamPreventionStrategy.RATE_LIMITING in config.strategies
    
    def test_custom_config(self):
        """Test custom spam prevention configuration."""
        config = SpamPreventionConfig(
            enabled=False,
            max_messages_per_minute=20,
            burst_threshold=10,
            strategies=[SpamPreventionStrategy.CONTENT_DEDUPLICATION]
        )
        
        assert config.enabled is False
        assert config.max_messages_per_minute == 20
        assert config.burst_threshold == 10
        assert len(config.strategies) == 1
        assert SpamPreventionStrategy.CONTENT_DEDUPLICATION in config.strategies


class TestTimingConfig:
    """Test suite for TimingConfig."""
    
    def test_default_config(self):
        """Test default timing configuration."""
        config = TimingConfig()
        
        assert config.mode == TimingMode.ADAPTIVE
        assert config.base_interval_minutes == 5
        assert config.max_interval_minutes == 30
        assert config.adaptive_factor == 1.5
        assert config.burst_detection_enabled is True
    
    def test_custom_config(self):
        """Test custom timing configuration."""
        config = TimingConfig(
            mode=TimingMode.FIXED_INTERVAL,
            base_interval_minutes=10,
            max_interval_minutes=60,
            adaptive_factor=2.0
        )
        
        assert config.mode == TimingMode.FIXED_INTERVAL
        assert config.base_interval_minutes == 10
        assert config.max_interval_minutes == 60
        assert config.adaptive_factor == 2.0


if __name__ == "__main__":
    pytest.main([__file__])