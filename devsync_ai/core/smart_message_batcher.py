"""Enhanced message batching system with smart timing controls and anti-spam features."""

import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import logging

from .message_batcher import (
    MessageBatcher, BatchableMessage, BatchGroup, BatchConfig, 
    BatchType, BatchStrategy, ContentType
)
from .message_formatter import SlackMessage


class SpamPreventionStrategy(Enum):
    """Strategies for preventing notification spam."""
    RATE_LIMITING = "rate_limiting"
    ADAPTIVE_TIMING = "adaptive_timing"
    CONTENT_DEDUPLICATION = "content_deduplication"
    USER_ACTIVITY_AWARE = "user_activity_aware"
    PRIORITY_THROTTLING = "priority_throttling"


class TimingMode(Enum):
    """Timing modes for message batching."""
    IMMEDIATE = "immediate"  # Send immediately, no batching
    FIXED_INTERVAL = "fixed_interval"  # Fixed time intervals
    ADAPTIVE = "adaptive"  # Adapt based on activity patterns
    SMART_BURST = "smart_burst"  # Handle bursts intelligently
    QUIET_HOURS = "quiet_hours"  # Respect quiet hours


@dataclass
class SpamPreventionConfig:
    """Configuration for spam prevention features."""
    enabled: bool = True
    max_messages_per_minute: int = 10
    max_messages_per_hour: int = 100
    burst_threshold: int = 5  # Messages in burst_window_seconds
    burst_window_seconds: int = 30
    cooldown_after_burst_minutes: int = 5
    duplicate_content_window_minutes: int = 15
    priority_rate_limits: Dict[str, int] = field(default_factory=lambda: {
        'critical': 20,  # per hour
        'high': 15,
        'medium': 10,
        'low': 5,
        'lowest': 2
    })
    quiet_hours_start: int = 22  # 10 PM
    quiet_hours_end: int = 8     # 8 AM
    quiet_hours_enabled: bool = True
    strategies: List[SpamPreventionStrategy] = field(default_factory=lambda: [
        SpamPreventionStrategy.RATE_LIMITING,
        SpamPreventionStrategy.ADAPTIVE_TIMING,
        SpamPreventionStrategy.CONTENT_DEDUPLICATION
    ])


@dataclass
class TimingConfig:
    """Configuration for smart timing controls."""
    mode: TimingMode = TimingMode.ADAPTIVE
    base_interval_minutes: int = 5
    max_interval_minutes: int = 30
    min_interval_minutes: int = 1
    adaptive_factor: float = 1.5  # Multiplier for adaptive timing
    burst_detection_enabled: bool = True
    user_activity_tracking: bool = True
    priority_timing_overrides: Dict[str, int] = field(default_factory=lambda: {
        'critical': 0,  # Immediate
        'high': 1,      # 1 minute max
        'medium': 5,    # 5 minutes max
        'low': 15,      # 15 minutes max
        'lowest': 30    # 30 minutes max
    })


@dataclass
class ActivityMetrics:
    """Metrics for tracking activity patterns."""
    message_timestamps: deque = field(default_factory=lambda: deque(maxlen=1000))
    hourly_counts: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    daily_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    burst_events: List[datetime] = field(default_factory=list)
    last_message_time: Optional[datetime] = None
    current_burst_size: int = 0
    in_cooldown: bool = False
    cooldown_until: Optional[datetime] = None


class SmartMessageBatcher(MessageBatcher):
    """Enhanced message batcher with smart timing controls and spam prevention."""
    
    def __init__(self, 
                 config: Optional[BatchConfig] = None,
                 spam_config: Optional[SpamPreventionConfig] = None,
                 timing_config: Optional[TimingConfig] = None,
                 formatter_factory=None):
        """Initialize smart message batcher."""
        super().__init__(config, formatter_factory)
        
        self.spam_config = spam_config or SpamPreventionConfig()
        self.timing_config = timing_config or TimingConfig()
        
        # Activity tracking per channel
        self._channel_activity: Dict[str, ActivityMetrics] = defaultdict(ActivityMetrics)
        
        # Content deduplication tracking
        self._content_hashes: Dict[str, Dict[str, datetime]] = defaultdict(dict)  # channel -> hash -> timestamp
        
        # Rate limiting tracking
        self._rate_limits: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=100)))
        
        # Enhanced statistics
        self._spam_stats = {
            'messages_blocked': 0,
            'duplicates_filtered': 0,
            'rate_limited': 0,
            'burst_cooldowns': 0,
            'quiet_hours_delayed': 0,
            'adaptive_delays': 0
        }
        
        self.logger.info("SmartMessageBatcher initialized with spam prevention and timing controls")
    
    def add_message(self, message: BatchableMessage, channel_id: str = "default") -> Optional[SlackMessage]:
        """Add message with smart timing controls and spam prevention."""
        if not self.config.enabled:
            return None
        
        # Apply spam prevention checks
        if not self._should_process_message(message, channel_id):
            return None
        
        # Update activity metrics
        self._update_activity_metrics(message, channel_id)
        
        # Determine optimal timing
        optimal_delay = self._calculate_optimal_delay(message, channel_id)
        
        # If immediate processing is required
        if optimal_delay == 0:
            return super().add_message(message, channel_id)
        
        # Schedule for delayed processing (in real implementation, this would use a scheduler)
        # For now, we'll add to batch with adjusted timing
        message.metadata['scheduled_delay'] = optimal_delay
        message.metadata['spam_prevention_applied'] = True
        
        return super().add_message(message, channel_id)
    
    def _should_process_message(self, message: BatchableMessage, channel_id: str) -> bool:
        """Check if message should be processed based on spam prevention rules."""
        current_time = datetime.now()
        
        # Check if in cooldown period
        activity = self._channel_activity[channel_id]
        if activity.in_cooldown and activity.cooldown_until and current_time < activity.cooldown_until:
            self._spam_stats['burst_cooldowns'] += 1
            self.logger.info(f"Message blocked due to cooldown period in channel {channel_id}")
            return False
        
        # Check rate limits
        if not self._check_rate_limits(message, channel_id):
            self._spam_stats['rate_limited'] += 1
            return False
        
        # Check for duplicate content
        if not self._check_content_deduplication(message, channel_id):
            self._spam_stats['duplicates_filtered'] += 1
            return False
        
        # Check quiet hours
        if not self._check_quiet_hours(message, current_time):
            self._spam_stats['quiet_hours_delayed'] += 1
            return False
        
        return True
    
    def _check_rate_limits(self, message: BatchableMessage, channel_id: str) -> bool:
        """Check if message exceeds rate limits."""
        if SpamPreventionStrategy.RATE_LIMITING not in self.spam_config.strategies:
            return True
        
        current_time = datetime.now()
        rate_tracker = self._rate_limits[channel_id]
        
        # Check per-minute limit
        minute_key = f"minute_{int(current_time.timestamp() // 60)}"
        minute_messages = rate_tracker[minute_key]
        minute_messages.append(current_time)
        
        if len(minute_messages) > self.spam_config.max_messages_per_minute:
            self.logger.warning(f"Rate limit exceeded: {len(minute_messages)} messages per minute in channel {channel_id}")
            return False
        
        # Check per-hour limit
        hour_key = f"hour_{int(current_time.timestamp() // 3600)}"
        hour_messages = rate_tracker[hour_key]
        hour_messages.append(current_time)
        
        if len(hour_messages) > self.spam_config.max_messages_per_hour:
            self.logger.warning(f"Rate limit exceeded: {len(hour_messages)} messages per hour in channel {channel_id}")
            return False
        
        # Check priority-specific limits
        priority = message.priority.lower()
        if priority in self.spam_config.priority_rate_limits:
            priority_key = f"priority_{priority}_{int(current_time.timestamp() // 3600)}"
            priority_messages = rate_tracker[priority_key]
            priority_messages.append(current_time)
            
            if len(priority_messages) > self.spam_config.priority_rate_limits[priority]:
                self.logger.warning(f"Priority rate limit exceeded for {priority} in channel {channel_id}")
                return False
        
        return True
    
    def _check_content_deduplication(self, message: BatchableMessage, channel_id: str) -> bool:
        """Check for duplicate content within the deduplication window."""
        if SpamPreventionStrategy.CONTENT_DEDUPLICATION not in self.spam_config.strategies:
            return True
        
        # Generate content hash
        content_hash = self._generate_content_hash(message)
        current_time = datetime.now()
        
        # Check if similar content was sent recently
        channel_hashes = self._content_hashes[channel_id]
        
        if content_hash in channel_hashes:
            last_sent = channel_hashes[content_hash]
            time_diff = (current_time - last_sent).total_seconds() / 60
            
            if time_diff < self.spam_config.duplicate_content_window_minutes:
                self.logger.info(f"Duplicate content filtered in channel {channel_id} (sent {time_diff:.1f} minutes ago)")
                return False
        
        # Update hash tracking
        channel_hashes[content_hash] = current_time
        
        # Clean up old hashes
        cutoff_time = current_time - timedelta(minutes=self.spam_config.duplicate_content_window_minutes * 2)
        expired_hashes = [h for h, t in channel_hashes.items() if t < cutoff_time]
        for h in expired_hashes:
            del channel_hashes[h]
        
        return True
    
    def _generate_content_hash(self, message: BatchableMessage) -> str:
        """Generate hash for content deduplication."""
        # Create hash based on content type, key data, and author
        hash_components = [
            message.content_type.value,
            str(message.author or ''),
            str(message.data.get('title', '')),
            str(message.data.get('key', '')),
            str(message.data.get('number', '')),
            str(message.data.get('repository', '')),
            str(message.data.get('project', ''))
        ]
        
        content_string = '|'.join(hash_components).lower()
        return hashlib.md5(content_string.encode()).hexdigest()
    
    def _check_quiet_hours(self, message: BatchableMessage, current_time: datetime) -> bool:
        """Check if message should be delayed due to quiet hours."""
        if not self.spam_config.quiet_hours_enabled:
            return True
        
        # Critical messages bypass quiet hours
        if message.priority.lower() == 'critical':
            return True
        
        current_hour = current_time.hour
        start_hour = self.spam_config.quiet_hours_start
        end_hour = self.spam_config.quiet_hours_end
        
        # Handle quiet hours that span midnight
        if start_hour > end_hour:  # e.g., 22:00 to 08:00
            in_quiet_hours = current_hour >= start_hour or current_hour < end_hour
        else:  # e.g., 01:00 to 06:00
            in_quiet_hours = start_hour <= current_hour < end_hour
        
        if in_quiet_hours:
            self.logger.info(f"Message delayed due to quiet hours ({start_hour}:00-{end_hour}:00)")
            return False
        
        return True
    
    def _update_activity_metrics(self, message: BatchableMessage, channel_id: str) -> None:
        """Update activity metrics for the channel."""
        current_time = datetime.now()
        activity = self._channel_activity[channel_id]
        
        # Update message timestamps
        activity.message_timestamps.append(current_time)
        
        # Update hourly and daily counts
        activity.hourly_counts[current_time.hour] += 1
        activity.daily_counts[current_time.strftime('%Y-%m-%d')] += 1
        
        # Check for burst activity
        if self.spam_config.burst_threshold > 0:
            self._check_burst_activity(activity, current_time, channel_id)
        
        activity.last_message_time = current_time
    
    def _check_burst_activity(self, activity: ActivityMetrics, current_time: datetime, channel_id: str) -> None:
        """Check and handle burst activity."""
        burst_window = timedelta(seconds=self.spam_config.burst_window_seconds)
        recent_messages = [
            ts for ts in activity.message_timestamps 
            if current_time - ts <= burst_window
        ]
        
        activity.current_burst_size = len(recent_messages)
        
        if activity.current_burst_size >= self.spam_config.burst_threshold:
            # Trigger cooldown
            activity.in_cooldown = True
            activity.cooldown_until = current_time + timedelta(minutes=self.spam_config.cooldown_after_burst_minutes)
            activity.burst_events.append(current_time)
            
            self.logger.warning(
                f"Burst detected in channel {channel_id}: {activity.current_burst_size} messages "
                f"in {self.spam_config.burst_window_seconds}s. Cooldown until {activity.cooldown_until}"
            )
        elif activity.in_cooldown and current_time >= (activity.cooldown_until or current_time):
            # End cooldown
            activity.in_cooldown = False
            activity.cooldown_until = None
            self.logger.info(f"Cooldown ended for channel {channel_id}")
    
    def _calculate_optimal_delay(self, message: BatchableMessage, channel_id: str) -> int:
        """Calculate optimal delay in seconds for message processing."""
        if self.timing_config.mode == TimingMode.IMMEDIATE:
            return 0
        
        # Priority-based timing overrides
        priority = message.priority.lower()
        if priority in self.timing_config.priority_timing_overrides:
            max_delay = self.timing_config.priority_timing_overrides[priority] * 60  # Convert to seconds
            if max_delay == 0:
                return 0
        else:
            max_delay = self.timing_config.max_interval_minutes * 60
        
        if self.timing_config.mode == TimingMode.FIXED_INTERVAL:
            return min(self.timing_config.base_interval_minutes * 60, max_delay)
        
        elif self.timing_config.mode == TimingMode.ADAPTIVE:
            return self._calculate_adaptive_delay(message, channel_id, max_delay)
        
        elif self.timing_config.mode == TimingMode.SMART_BURST:
            return self._calculate_burst_aware_delay(message, channel_id, max_delay)
        
        return self.timing_config.base_interval_minutes * 60
    
    def _calculate_adaptive_delay(self, message: BatchableMessage, channel_id: str, max_delay: int) -> int:
        """Calculate adaptive delay based on activity patterns."""
        activity = self._channel_activity[channel_id]
        
        # Base delay
        base_delay = self.timing_config.base_interval_minutes * 60
        
        # Adjust based on recent activity
        if len(activity.message_timestamps) > 0:
            recent_activity = len([
                ts for ts in activity.message_timestamps 
                if datetime.now() - ts <= timedelta(minutes=30)
            ])
            
            # More activity = longer delays to batch more messages
            activity_factor = min(recent_activity / 10.0, 3.0)  # Cap at 3x
            adaptive_delay = int(base_delay * (1 + activity_factor * self.timing_config.adaptive_factor))
            
            self._spam_stats['adaptive_delays'] += 1
            return min(adaptive_delay, max_delay)
        
        return base_delay
    
    def _calculate_burst_aware_delay(self, message: BatchableMessage, channel_id: str, max_delay: int) -> int:
        """Calculate delay that's aware of burst patterns."""
        activity = self._channel_activity[channel_id]
        
        # If in burst or recent burst, use longer delay
        if activity.in_cooldown or activity.current_burst_size > 2:
            return max_delay
        
        # If recent burst activity, use moderate delay
        recent_bursts = [
            burst for burst in activity.burst_events 
            if datetime.now() - burst <= timedelta(hours=1)
        ]
        
        if recent_bursts:
            return min(self.timing_config.base_interval_minutes * 60 * 2, max_delay)
        
        return self.timing_config.base_interval_minutes * 60
    
    def get_spam_prevention_stats(self) -> Dict[str, Any]:
        """Get spam prevention statistics."""
        return {
            **self._spam_stats,
            'active_channels': len(self._channel_activity),
            'channels_in_cooldown': sum(1 for a in self._channel_activity.values() if a.in_cooldown),
            'total_content_hashes': sum(len(hashes) for hashes in self._content_hashes.values()),
            'burst_events_last_hour': sum(
                len([b for b in activity.burst_events if datetime.now() - b <= timedelta(hours=1)])
                for activity in self._channel_activity.values()
            )
        }
    
    def get_channel_activity_summary(self, channel_id: str) -> Dict[str, Any]:
        """Get activity summary for a specific channel."""
        if channel_id not in self._channel_activity:
            return {'error': 'Channel not found'}
        
        activity = self._channel_activity[channel_id]
        current_time = datetime.now()
        
        return {
            'total_messages': len(activity.message_timestamps),
            'messages_last_hour': len([
                ts for ts in activity.message_timestamps 
                if current_time - ts <= timedelta(hours=1)
            ]),
            'messages_last_day': len([
                ts for ts in activity.message_timestamps 
                if current_time - ts <= timedelta(days=1)
            ]),
            'current_burst_size': activity.current_burst_size,
            'in_cooldown': activity.in_cooldown,
            'cooldown_until': activity.cooldown_until.isoformat() if activity.cooldown_until else None,
            'last_message_time': activity.last_message_time.isoformat() if activity.last_message_time else None,
            'burst_events_count': len(activity.burst_events),
            'hourly_distribution': dict(activity.hourly_counts)
        }
    
    def reset_channel_activity(self, channel_id: str) -> bool:
        """Reset activity tracking for a channel."""
        if channel_id in self._channel_activity:
            del self._channel_activity[channel_id]
            if channel_id in self._content_hashes:
                del self._content_hashes[channel_id]
            if channel_id in self._rate_limits:
                del self._rate_limits[channel_id]
            return True
        return False
    
    def update_spam_config(self, new_config: SpamPreventionConfig) -> None:
        """Update spam prevention configuration."""
        self.spam_config = new_config
        self.logger.info("Spam prevention configuration updated")
    
    def update_timing_config(self, new_config: TimingConfig) -> None:
        """Update timing configuration."""
        self.timing_config = new_config
        self.logger.info("Timing configuration updated")


# Global smart batcher instance
default_smart_batcher = SmartMessageBatcher()