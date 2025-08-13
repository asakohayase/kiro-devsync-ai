"""Sophisticated message batching system for grouped notifications."""

import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import logging

from .message_formatter import SlackMessage, TemplateConfig
from .interactive_elements import InteractiveElementBuilder, default_interactive_builder


class BatchType(Enum):
    """Types of message batches."""
    DAILY_SUMMARY = "daily_summary"
    SPRINT_UPDATE = "sprint_update"
    PR_ACTIVITY = "pr_activity"
    JIRA_ACTIVITY = "jira_activity"
    ALERT_DIGEST = "alert_digest"
    WEEKLY_CHANGELOG = "weekly_changelog"
    TEAM_ACTIVITY = "team_activity"
    CUSTOM = "custom"


class BatchStrategy(Enum):
    """Batching strategies."""
    TIME_BASED = "time_based"
    CONTENT_SIMILARITY = "content_similarity"
    AUTHOR_BASED = "author_based"
    PRIORITY_BASED = "priority_based"
    MIXED = "mixed"


class ContentType(Enum):
    """Content types for similarity detection."""
    PR_UPDATE = "pr_update"
    JIRA_UPDATE = "jira_update"
    ALERT = "alert"
    STANDUP = "standup"
    DEPLOYMENT = "deployment"
    BLOCKER = "blocker"


@dataclass
class BatchableMessage:
    """A message that can be batched with others."""
    id: str
    content_type: ContentType
    timestamp: datetime
    author: Optional[str] = None
    priority: str = "medium"
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_similarity_key(self) -> str:
        """Generate key for content similarity grouping."""
        key_parts = [
            self.content_type.value,
            self.author or "unknown",
            self.data.get('repository', ''),
            self.data.get('project', ''),
            self.data.get('team', '')
        ]
        return ":".join(str(part).lower() for part in key_parts)
    
    def get_priority_score(self) -> int:
        """Get numeric priority score for ordering."""
        priority_scores = {
            'critical': 100,
            'high': 75,
            'medium': 50,
            'low': 25,
            'lowest': 10
        }
        return priority_scores.get(self.priority.lower(), 50)


@dataclass
class BatchGroup:
    """A group of related messages to be batched."""
    id: str
    batch_type: BatchType
    messages: List[BatchableMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, message: BatchableMessage) -> None:
        """Add message to batch group."""
        self.messages.append(message)
        # Update expiration based on newest message
        if not self.expires_at or message.timestamp > self.expires_at:
            self.expires_at = message.timestamp + timedelta(minutes=5)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the batch."""
        stats = {
            'total_count': len(self.messages),
            'content_types': defaultdict(int),
            'authors': set(),
            'priority_counts': defaultdict(int),
            'time_range': {
                'start': min(msg.timestamp for msg in self.messages) if self.messages else None,
                'end': max(msg.timestamp for msg in self.messages) if self.messages else None
            }
        }
        
        for msg in self.messages:
            stats['content_types'][msg.content_type.value] += 1
            if msg.author:
                stats['authors'].add(msg.author)
            stats['priority_counts'][msg.priority] += 1
        
        stats['authors'] = list(stats['authors'])
        return stats
    
    def should_flush(self, max_age_minutes: int = 5, max_size: int = 10) -> bool:
        """Check if batch should be flushed."""
        if len(self.messages) >= max_size:
            return True
        
        if self.expires_at and datetime.now() >= self.expires_at:
            return True
        
        age_minutes = (datetime.now() - self.created_at).total_seconds() / 60
        return age_minutes >= max_age_minutes


@dataclass
class BatchConfig:
    """Configuration for message batching."""
    enabled: bool = True
    max_batch_size: int = 10
    max_batch_age_minutes: int = 5
    similarity_threshold: float = 0.7
    enable_pagination: bool = True
    items_per_page: int = 5
    enable_threading: bool = True
    priority_ordering: bool = True
    strategies: List[BatchStrategy] = field(default_factory=lambda: [BatchStrategy.TIME_BASED, BatchStrategy.CONTENT_SIMILARITY])


class MessageBatcher:
    """Sophisticated message batching system."""
    
    def __init__(self, config: Optional[BatchConfig] = None):
        """Initialize message batcher."""
        self.config = config or BatchConfig()
        self.logger = logging.getLogger(__name__)
        
        # Active batch groups
        self._batch_groups: Dict[str, BatchGroup] = {}
        
        # Batch statistics
        self._stats = {
            'batches_created': 0,
            'messages_batched': 0,
            'batches_flushed': 0,
            'similarity_matches': 0
        }
        
        # Interactive element builder for batch messages
        self._interactive_builder = default_interactive_builder
        
        self.logger.info("MessageBatcher initialized")
    
    def add_message(self, message: BatchableMessage) -> Optional[SlackMessage]:
        """Add message to batching system. Returns batched message if ready."""
        if not self.config.enabled:
            return None
        
        # Find or create appropriate batch group
        batch_group = self._find_or_create_batch_group(message)
        batch_group.add_message(message)
        
        self._stats['messages_batched'] += 1
        
        # Check if batch should be flushed
        if batch_group.should_flush(self.config.max_batch_age_minutes, self.config.max_batch_size):
            return self._flush_batch_group(batch_group)
        
        return None
    
    def flush_all_batches(self) -> List[SlackMessage]:
        """Flush all pending batch groups."""
        batched_messages = []
        
        for group_id in list(self._batch_groups.keys()):
            batch_group = self._batch_groups[group_id]
            if batch_group.messages:  # Only flush non-empty batches
                batched_message = self._flush_batch_group(batch_group)
                if batched_message:
                    batched_messages.append(batched_message)
        
        return batched_messages
    
    def flush_expired_batches(self) -> List[SlackMessage]:
        """Flush only expired batch groups."""
        batched_messages = []
        current_time = datetime.now()
        
        for group_id in list(self._batch_groups.keys()):
            batch_group = self._batch_groups[group_id]
            if batch_group.should_flush(self.config.max_batch_age_minutes, self.config.max_batch_size):
                batched_message = self._flush_batch_group(batch_group)
                if batched_message:
                    batched_messages.append(batched_message)
        
        return batched_messages
    
    def get_batch_stats(self) -> Dict[str, Any]:
        """Get batching statistics."""
        return {
            **self._stats,
            'active_batches': len(self._batch_groups),
            'pending_messages': sum(len(group.messages) for group in self._batch_groups.values())
        }
    
    def _find_or_create_batch_group(self, message: BatchableMessage) -> BatchGroup:
        """Find existing batch group or create new one for message."""
        # Try different strategies to find matching batch
        for strategy in self.config.strategies:
            group_key = self._get_group_key(message, strategy)
            
            if group_key in self._batch_groups:
                existing_group = self._batch_groups[group_key]
                
                # Check if message fits in existing group
                if self._can_add_to_group(message, existing_group, strategy):
                    return existing_group
        
        # Create new batch group
        return self._create_new_batch_group(message)
    
    def _get_group_key(self, message: BatchableMessage, strategy: BatchStrategy) -> str:
        """Generate group key based on batching strategy."""
        if strategy == BatchStrategy.TIME_BASED:
            # Group by 5-minute time windows
            time_window = int(message.timestamp.timestamp() // 300) * 300
            return f"time_{time_window}_{message.content_type.value}"
        
        elif strategy == BatchStrategy.CONTENT_SIMILARITY:
            return f"similarity_{message.get_similarity_key()}"
        
        elif strategy == BatchStrategy.AUTHOR_BASED:
            author = message.author or "unknown"
            return f"author_{author}_{message.content_type.value}"
        
        elif strategy == BatchStrategy.PRIORITY_BASED:
            return f"priority_{message.priority}_{message.content_type.value}"
        
        else:  # MIXED strategy
            similarity_key = message.get_similarity_key()
            time_window = int(message.timestamp.timestamp() // 300) * 300
            return f"mixed_{similarity_key}_{time_window}"
    
    def _can_add_to_group(self, message: BatchableMessage, group: BatchGroup, strategy: BatchStrategy) -> bool:
        """Check if message can be added to existing group."""
        # Check size limit
        if len(group.messages) >= self.config.max_batch_size:
            return False
        
        # Check age limit
        age_minutes = (datetime.now() - group.created_at).total_seconds() / 60
        if age_minutes >= self.config.max_batch_age_minutes:
            return False
        
        # Strategy-specific checks
        if strategy == BatchStrategy.CONTENT_SIMILARITY:
            return self._calculate_similarity(message, group) >= self.config.similarity_threshold
        
        return True
    
    def _calculate_similarity(self, message: BatchableMessage, group: BatchGroup) -> float:
        """Calculate content similarity between message and group."""
        if not group.messages:
            return 1.0
        
        # Simple similarity based on content type, author, and project
        similarities = []
        
        for existing_msg in group.messages:
            similarity = 0.0
            
            # Content type match (40% weight)
            if message.content_type == existing_msg.content_type:
                similarity += 0.4
            
            # Author match (30% weight)
            if message.author and message.author == existing_msg.author:
                similarity += 0.3
            
            # Project/repository match (30% weight)
            msg_project = message.data.get('repository') or message.data.get('project', '')
            existing_project = existing_msg.data.get('repository') or existing_msg.data.get('project', '')
            if msg_project and msg_project == existing_project:
                similarity += 0.3
            
            similarities.append(similarity)
        
        return max(similarities) if similarities else 0.0
    
    def _create_new_batch_group(self, message: BatchableMessage) -> BatchGroup:
        """Create new batch group for message."""
        # Determine batch type based on content
        batch_type = self._determine_batch_type(message)
        
        # Generate unique group ID
        group_id = f"{batch_type.value}_{int(time.time())}_{len(self._batch_groups)}"
        
        batch_group = BatchGroup(
            id=group_id,
            batch_type=batch_type,
            metadata={
                'primary_content_type': message.content_type.value,
                'primary_author': message.author,
                'created_by_strategy': self.config.strategies[0].value if self.config.strategies else 'default'
            }
        )
        
        self._batch_groups[group_id] = batch_group
        self._stats['batches_created'] += 1
        
        return batch_group
    
    def _determine_batch_type(self, message: BatchableMessage) -> BatchType:
        """Determine appropriate batch type for message."""
        content_type_mapping = {
            ContentType.PR_UPDATE: BatchType.PR_ACTIVITY,
            ContentType.JIRA_UPDATE: BatchType.JIRA_ACTIVITY,
            ContentType.ALERT: BatchType.ALERT_DIGEST,
            ContentType.STANDUP: BatchType.DAILY_SUMMARY,
            ContentType.DEPLOYMENT: BatchType.DAILY_SUMMARY,
            ContentType.BLOCKER: BatchType.ALERT_DIGEST
        }
        
        return content_type_mapping.get(message.content_type, BatchType.DAILY_SUMMARY)
    
    def _flush_batch_group(self, batch_group: BatchGroup) -> Optional[SlackMessage]:
        """Flush batch group and create batched message."""
        if not batch_group.messages:
            return None
        
        try:
            # Remove from active batches
            if batch_group.id in self._batch_groups:
                del self._batch_groups[batch_group.id]
            
            # Create batched message
            batched_message = self._create_batched_message(batch_group)
            
            self._stats['batches_flushed'] += 1
            self.logger.info(f"Flushed batch group {batch_group.id} with {len(batch_group.messages)} messages")
            
            return batched_message
            
        except Exception as e:
            self.logger.error(f"Failed to flush batch group {batch_group.id}: {e}")
            return None
    
    def _create_batched_message(self, batch_group: BatchGroup) -> SlackMessage:
        """Create Slack message from batch group."""
        stats = batch_group.get_summary_stats()
        
        # Create summary header
        header_text = self._create_summary_header(batch_group, stats)
        
        # Create message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header_text,
                    "emoji": True
                }
            }
        ]
        
        # Add summary statistics
        blocks.extend(self._create_summary_blocks(batch_group, stats))
        
        # Add expandable details (with pagination if needed)
        blocks.extend(self._create_detail_blocks(batch_group))
        
        # Add navigation/action buttons
        blocks.extend(self._create_action_blocks(batch_group))
        
        # Create fallback text
        fallback_text = self._create_fallback_text(batch_group, stats)
        
        return SlackMessage(
            blocks=blocks,
            text=fallback_text,
            metadata={
                'batch_type': batch_group.batch_type.value,
                'message_count': len(batch_group.messages),
                'batch_id': batch_group.id,
                'created_at': batch_group.created_at.isoformat(),
                'is_batched': True
            }
        )
    
    def _create_summary_header(self, batch_group: BatchGroup, stats: Dict[str, Any]) -> str:
        """Create summary header text."""
        total_count = stats['total_count']
        
        if batch_group.batch_type == BatchType.DAILY_SUMMARY:
            return f"📊 Daily Development Summary - {total_count} updates"
        elif batch_group.batch_type == BatchType.PR_ACTIVITY:
            return f"🔄 PR Activity Summary - {total_count} updates"
        elif batch_group.batch_type == BatchType.JIRA_ACTIVITY:
            return f"📋 JIRA Activity Summary - {total_count} updates"
        elif batch_group.batch_type == BatchType.ALERT_DIGEST:
            return f"⚠️ Alert Digest - {total_count} alerts"
        elif batch_group.batch_type == BatchType.SPRINT_UPDATE:
            return f"🏃 Sprint Update - {total_count} changes"
        elif batch_group.batch_type == BatchType.WEEKLY_CHANGELOG:
            return f"📝 Weekly Changelog - {total_count} items"
        else:
            return f"📦 Activity Summary - {total_count} updates"
    
    def _create_summary_blocks(self, batch_group: BatchGroup, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create summary statistics blocks."""
        blocks = []
        
        # Content type breakdown
        content_summary = []
        content_icons = {
            'pr_update': '🔄',
            'jira_update': '📋',
            'alert': '⚠️',
            'standup': '👥',
            'deployment': '🚀',
            'blocker': '🚫'
        }
        
        for content_type, count in stats['content_types'].items():
            icon = content_icons.get(content_type, '📄')
            content_summary.append(f"{icon} {count} {content_type.replace('_', ' ').title()}")
        
        if content_summary:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join([f"├── {item}" for item in content_summary[:-1]] + [f"└── {content_summary[-1]}"])
                }
            })
        
        # Author summary
        if stats['authors']:
            author_list = ", ".join(f"@{author}" for author in stats['authors'][:5])
            if len(stats['authors']) > 5:
                author_list += f" and {len(stats['authors']) - 5} others"
            
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"👥 *Contributors:* {author_list}"
                    }
                ]
            })
        
        return blocks
    
    def _create_detail_blocks(self, batch_group: BatchGroup) -> List[Dict[str, Any]]:
        """Create expandable detail blocks with pagination."""
        blocks = []
        
        if not self.config.enable_pagination or len(batch_group.messages) <= self.config.items_per_page:
            # Show all items without pagination
            blocks.extend(self._create_message_list_blocks(batch_group.messages))
        else:
            # Show first page with pagination controls
            first_page = batch_group.messages[:self.config.items_per_page]
            blocks.extend(self._create_message_list_blocks(first_page))
            
            # Add pagination info
            remaining = len(batch_group.messages) - self.config.items_per_page
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📄 Showing {len(first_page)} of {len(batch_group.messages)} items ({remaining} more)"
                    }
                ]
            })
        
        return blocks
    
    def _create_message_list_blocks(self, messages: List[BatchableMessage]) -> List[Dict[str, Any]]:
        """Create blocks for list of messages."""
        blocks = []
        
        # Sort messages by priority and timestamp
        if self.config.priority_ordering:
            sorted_messages = sorted(messages, key=lambda m: (-m.get_priority_score(), m.timestamp))
        else:
            sorted_messages = sorted(messages, key=lambda m: m.timestamp)
        
        for message in sorted_messages:
            block = self._create_message_item_block(message)
            if block:
                blocks.append(block)
        
        return blocks
    
    def _create_message_item_block(self, message: BatchableMessage) -> Optional[Dict[str, Any]]:
        """Create block for individual message item."""
        # Get appropriate icon and format based on content type
        if message.content_type == ContentType.PR_UPDATE:
            return self._create_pr_item_block(message)
        elif message.content_type == ContentType.JIRA_UPDATE:
            return self._create_jira_item_block(message)
        elif message.content_type == ContentType.ALERT:
            return self._create_alert_item_block(message)
        else:
            return self._create_generic_item_block(message)
    
    def _create_pr_item_block(self, message: BatchableMessage) -> Dict[str, Any]:
        """Create block for PR update item."""
        pr_data = message.data
        action = pr_data.get('action', 'updated')
        pr_number = pr_data.get('number', 'Unknown')
        title = pr_data.get('title', 'Untitled PR')
        author = message.author or 'Unknown'
        
        action_icons = {
            'opened': '🆕',
            'merged': '✅',
            'closed': '❌',
            'approved': '👍',
            'ready_for_review': '👀',
            'conflicts': '⚠️'
        }
        
        icon = action_icons.get(action, '🔄')
        text = f"{icon} PR #{pr_number}: {title} ({action} by @{author})"
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text
            }
        }
    
    def _create_jira_item_block(self, message: BatchableMessage) -> Dict[str, Any]:
        """Create block for JIRA update item."""
        jira_data = message.data
        ticket_key = jira_data.get('key', 'Unknown')
        summary = jira_data.get('summary', 'Untitled ticket')
        status = jira_data.get('status', {}).get('name', 'Unknown')
        author = message.author or 'Unknown'
        
        status_icons = {
            'To Do': '📋',
            'In Progress': '🔄',
            'In Review': '👀',
            'Done': '✅',
            'Blocked': '🚫'
        }
        
        icon = status_icons.get(status, '📄')
        text = f"{icon} {ticket_key}: {summary} → {status} (@{author})"
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text
            }
        }
    
    def _create_alert_item_block(self, message: BatchableMessage) -> Dict[str, Any]:
        """Create block for alert item."""
        alert_data = message.data
        alert_type = alert_data.get('type', 'alert')
        severity = alert_data.get('severity', 'medium')
        description = alert_data.get('description', 'Alert triggered')
        
        severity_icons = {
            'critical': '🚨',
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢'
        }
        
        icon = severity_icons.get(severity, '⚠️')
        text = f"{icon} {alert_type.title()}: {description} ({severity} priority)"
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text
            }
        }
    
    def _create_generic_item_block(self, message: BatchableMessage) -> Dict[str, Any]:
        """Create block for generic message item."""
        title = message.data.get('title', 'Update')
        author = message.author or 'Unknown'
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📄 {title} (@{author})"
            }
        }
    
    def _create_action_blocks(self, batch_group: BatchGroup) -> List[Dict[str, Any]]:
        """Create action buttons for batch message."""
        blocks = []
        
        # Create action buttons
        buttons = []
        
        # View Details button (expandable)
        if len(batch_group.messages) > self.config.items_per_page:
            details_btn = self._interactive_builder.create_show_details_button(
                batch_group.id, "batch"
            )
            buttons.append(details_btn)
        
        # Thread Discussion button
        if self.config.enable_threading:
            from .interactive_elements import ActionType
            thread_btn = self._interactive_builder.create_button(
                text="💬 Thread Discussion",
                action_type=ActionType.CUSTOM_ACTION,
                resource_id=batch_group.id,
                metadata={"action": "start_thread"}
            )
            buttons.append(thread_btn)
        
        if buttons:
            blocks.append({
                "type": "actions",
                "elements": buttons
            })
        
        return blocks
    
    def _create_fallback_text(self, batch_group: BatchGroup, stats: Dict[str, Any]) -> str:
        """Create fallback text for accessibility."""
        header = self._create_summary_header(batch_group, stats)
        
        content_summary = []
        for content_type, count in stats['content_types'].items():
            content_summary.append(f"{count} {content_type.replace('_', ' ')}")
        
        fallback_parts = [
            header,
            f"Content: {', '.join(content_summary)}",
            f"Contributors: {', '.join(stats['authors']) if stats['authors'] else 'None'}"
        ]
        
        return "\n".join(fallback_parts)


# Global batcher instance
default_message_batcher = MessageBatcher()