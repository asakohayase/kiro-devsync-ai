"""Message threading support for related Slack notifications."""

import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import logging

from .message_formatter import SlackMessage


class ThreadingStrategy(Enum):
    """Strategies for message threading."""
    CONTENT_BASED = "content_based"  # Thread by content similarity
    TEMPORAL = "temporal"  # Thread by time proximity
    ENTITY_BASED = "entity_based"  # Thread by entity (PR, ticket, etc.)
    CONVERSATION = "conversation"  # Thread by conversation context
    WORKFLOW = "workflow"  # Thread by workflow stage


class ThreadType(Enum):
    """Types of message threads."""
    PR_LIFECYCLE = "pr_lifecycle"  # PR creation -> review -> merge
    JIRA_UPDATES = "jira_updates"  # Ticket status changes
    ALERT_SEQUENCE = "alert_sequence"  # Related alerts
    STANDUP_FOLLOWUP = "standup_followup"  # Standup discussion
    DEPLOYMENT_PIPELINE = "deployment_pipeline"  # Deployment stages
    INCIDENT_RESPONSE = "incident_response"  # Incident handling
    CUSTOM = "custom"


@dataclass
class ThreadContext:
    """Context information for message threading."""
    thread_id: str
    thread_type: ThreadType
    parent_message_ts: str
    entity_id: Optional[str] = None  # PR number, ticket key, etc.
    entity_type: Optional[str] = None  # "pr", "jira", "alert", etc.
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    participants: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_participant(self, user_id: str) -> None:
        """Add participant to thread."""
        self.participants.add(user_id)
    
    def update_activity(self) -> None:
        """Update thread activity timestamp."""
        self.last_updated = datetime.now()
        self.message_count += 1
    
    def is_expired(self, max_age_hours: int = 24) -> bool:
        """Check if thread context has expired."""
        age = datetime.now() - self.last_updated
        return age.total_seconds() > (max_age_hours * 3600)


@dataclass
class ThreadingConfig:
    """Configuration for message threading."""
    enabled: bool = True
    max_thread_age_hours: int = 24
    max_messages_per_thread: int = 50
    auto_thread_similar_content: bool = True
    thread_similarity_threshold: float = 0.8
    temporal_window_minutes: int = 30
    enable_cross_channel_threading: bool = False
    strategies: List[ThreadingStrategy] = field(default_factory=lambda: [
        ThreadingStrategy.ENTITY_BASED,
        ThreadingStrategy.CONTENT_BASED,
        ThreadingStrategy.TEMPORAL
    ])
    thread_types_enabled: List[ThreadType] = field(default_factory=lambda: [
        ThreadType.PR_LIFECYCLE,
        ThreadType.JIRA_UPDATES,
        ThreadType.ALERT_SEQUENCE,
        ThreadType.DEPLOYMENT_PIPELINE
    ])


class MessageThreadingManager:
    """Manager for message threading and conversation context."""
    
    def __init__(self, config: Optional[ThreadingConfig] = None):
        """Initialize message threading manager."""
        self.config = config or ThreadingConfig()
        self.logger = logging.getLogger(__name__)
        
        # Thread context storage by channel
        self._channel_threads: Dict[str, Dict[str, ThreadContext]] = defaultdict(dict)
        
        # Entity to thread mapping for quick lookups
        self._entity_threads: Dict[str, Dict[str, str]] = defaultdict(dict)  # channel -> entity_key -> thread_id
        
        # Content similarity tracking
        self._content_vectors: Dict[str, Dict[str, Any]] = defaultdict(dict)  # channel -> thread_id -> content_info
        
        # Threading statistics
        self._stats = {
            'threads_created': 0,
            'messages_threaded': 0,
            'threads_expired': 0,
            'cross_channel_threads': 0,
            'similarity_matches': 0,
            'entity_matches': 0,
            'temporal_matches': 0
        }
        
        self.logger.info("MessageThreadingManager initialized")
    
    def should_thread_message(self, message: SlackMessage, channel_id: str) -> Optional[str]:
        """Determine if message should be threaded and return parent thread_ts."""
        if not self.config.enabled:
            return None
        
        # Clean up expired threads first
        self._cleanup_expired_threads(channel_id)
        
        # Try different threading strategies
        for strategy in self.config.strategies:
            thread_ts = self._find_thread_by_strategy(message, channel_id, strategy)
            if thread_ts:
                self._stats[f'{strategy.value}_matches'] = self._stats.get(f'{strategy.value}_matches', 0) + 1
                return thread_ts
        
        return None
    
    def create_thread_context(self, 
                            message: SlackMessage, 
                            channel_id: str, 
                            parent_ts: str,
                            thread_type: Optional[ThreadType] = None) -> ThreadContext:
        """Create new thread context for a message."""
        # Generate thread ID
        thread_id = self._generate_thread_id(message, channel_id, parent_ts)
        
        # Determine thread type if not provided
        if thread_type is None:
            thread_type = self._determine_thread_type(message)
        
        # Extract entity information
        entity_id, entity_type = self._extract_entity_info(message)
        
        # Create thread context
        context = ThreadContext(
            thread_id=thread_id,
            thread_type=thread_type,
            parent_message_ts=parent_ts,
            entity_id=entity_id,
            entity_type=entity_type,
            metadata=message.metadata.copy() if message.metadata else {}
        )
        
        # Store thread context
        self._channel_threads[channel_id][thread_id] = context
        
        # Update entity mapping if applicable
        if entity_id and entity_type:
            entity_key = f"{entity_type}:{entity_id}"
            self._entity_threads[channel_id][entity_key] = thread_id
        
        # Update content vectors for similarity matching
        self._update_content_vectors(message, channel_id, thread_id)
        
        self._stats['threads_created'] += 1
        self.logger.info(f"Created thread context {thread_id} for {thread_type.value} in channel {channel_id}")
        
        return context
    
    def add_message_to_thread(self, 
                            message: SlackMessage, 
                            channel_id: str, 
                            thread_ts: str) -> bool:
        """Add message to existing thread."""
        # Find thread context
        thread_context = self._find_thread_context(channel_id, thread_ts)
        if not thread_context:
            self.logger.warning(f"Thread context not found for {thread_ts} in channel {channel_id}")
            return False
        
        # Check thread limits
        if thread_context.message_count >= self.config.max_messages_per_thread:
            self.logger.warning(f"Thread {thread_context.thread_id} has reached message limit")
            return False
        
        # Update thread context
        thread_context.update_activity()
        
        # Add participant if available
        author = message.metadata.get('author') if message.metadata else None
        if author:
            thread_context.add_participant(author)
        
        # Update content vectors
        self._update_content_vectors(message, channel_id, thread_context.thread_id)
        
        self._stats['messages_threaded'] += 1
        self.logger.debug(f"Added message to thread {thread_context.thread_id}")
        
        return True
    
    def get_thread_context(self, channel_id: str, thread_ts: str) -> Optional[ThreadContext]:
        """Get thread context for a specific thread."""
        return self._find_thread_context(channel_id, thread_ts)
    
    def get_related_threads(self, 
                          message: SlackMessage, 
                          channel_id: str, 
                          max_results: int = 5) -> List[ThreadContext]:
        """Get related threads for a message."""
        related_threads = []
        
        # Get entity-based related threads
        entity_id, entity_type = self._extract_entity_info(message)
        if entity_id and entity_type:
            entity_key = f"{entity_type}:{entity_id}"
            if entity_key in self._entity_threads[channel_id]:
                thread_id = self._entity_threads[channel_id][entity_key]
                if thread_id in self._channel_threads[channel_id]:
                    related_threads.append(self._channel_threads[channel_id][thread_id])
        
        # Get content-based related threads
        if len(related_threads) < max_results:
            content_related = self._find_content_related_threads(message, channel_id, max_results - len(related_threads))
            related_threads.extend(content_related)
        
        # Sort by relevance (most recent activity first)
        related_threads.sort(key=lambda t: t.last_updated, reverse=True)
        
        return related_threads[:max_results]
    
    def _find_thread_by_strategy(self, 
                               message: SlackMessage, 
                               channel_id: str, 
                               strategy: ThreadingStrategy) -> Optional[str]:
        """Find thread using specific strategy."""
        if strategy == ThreadingStrategy.ENTITY_BASED:
            return self._find_entity_based_thread(message, channel_id)
        elif strategy == ThreadingStrategy.CONTENT_BASED:
            return self._find_content_based_thread(message, channel_id)
        elif strategy == ThreadingStrategy.TEMPORAL:
            return self._find_temporal_thread(message, channel_id)
        elif strategy == ThreadingStrategy.WORKFLOW:
            return self._find_workflow_thread(message, channel_id)
        
        return None
    
    def _find_entity_based_thread(self, message: SlackMessage, channel_id: str) -> Optional[str]:
        """Find thread based on entity (PR, ticket, etc.)."""
        entity_id, entity_type = self._extract_entity_info(message)
        if not entity_id or not entity_type:
            return None
        
        entity_key = f"{entity_type}:{entity_id}"
        if entity_key in self._entity_threads[channel_id]:
            thread_id = self._entity_threads[channel_id][entity_key]
            if thread_id in self._channel_threads[channel_id]:
                context = self._channel_threads[channel_id][thread_id]
                if not context.is_expired(self.config.max_thread_age_hours):
                    return context.parent_message_ts
        
        return None
    
    def _find_content_based_thread(self, message: SlackMessage, channel_id: str) -> Optional[str]:
        """Find thread based on content similarity."""
        if not self.config.auto_thread_similar_content:
            return None
        
        message_content = self._extract_message_content(message)
        if not message_content:
            return None
        
        best_match_thread = None
        best_similarity = 0.0
        
        for thread_id, content_info in self._content_vectors[channel_id].items():
            if thread_id not in self._channel_threads[channel_id]:
                continue
            
            context = self._channel_threads[channel_id][thread_id]
            if context.is_expired(self.config.max_thread_age_hours):
                continue
            
            similarity = self._calculate_content_similarity(message_content, content_info)
            if similarity > best_similarity and similarity >= self.config.thread_similarity_threshold:
                best_similarity = similarity
                best_match_thread = context
        
        if best_match_thread:
            self._stats['similarity_matches'] += 1
            return best_match_thread.parent_message_ts
        
        return None
    
    def _find_temporal_thread(self, message: SlackMessage, channel_id: str) -> Optional[str]:
        """Find thread based on temporal proximity."""
        message_time = datetime.now()  # In real implementation, extract from message
        window = timedelta(minutes=self.config.temporal_window_minutes)
        
        recent_threads = []
        for context in self._channel_threads[channel_id].values():
            if context.is_expired(self.config.max_thread_age_hours):
                continue
            
            time_diff = abs(message_time - context.last_updated)
            if time_diff <= window:
                recent_threads.append((context, time_diff))
        
        if recent_threads:
            # Return the most recent thread
            recent_threads.sort(key=lambda x: x[1])
            self._stats['temporal_matches'] += 1
            return recent_threads[0][0].parent_message_ts
        
        return None
    
    def _find_workflow_thread(self, message: SlackMessage, channel_id: str) -> Optional[str]:
        """Find thread based on workflow stage."""
        # Extract workflow information from message
        workflow_stage = self._extract_workflow_stage(message)
        if not workflow_stage:
            return None
        
        # Look for threads with related workflow stages
        for context in self._channel_threads[channel_id].values():
            if context.is_expired(self.config.max_thread_age_hours):
                continue
            
            if self._is_related_workflow_stage(workflow_stage, context):
                return context.parent_message_ts
        
        return None
    
    def _find_content_related_threads(self, 
                                    message: SlackMessage, 
                                    channel_id: str, 
                                    max_results: int) -> List[ThreadContext]:
        """Find threads related by content similarity."""
        message_content = self._extract_message_content(message)
        if not message_content:
            return []
        
        related_threads = []
        
        for thread_id, content_info in self._content_vectors[channel_id].items():
            if thread_id not in self._channel_threads[channel_id]:
                continue
            
            context = self._channel_threads[channel_id][thread_id]
            if context.is_expired(self.config.max_thread_age_hours):
                continue
            
            similarity = self._calculate_content_similarity(message_content, content_info)
            if similarity >= 0.5:  # Lower threshold for related threads
                related_threads.append((context, similarity))
        
        # Sort by similarity and return top results
        related_threads.sort(key=lambda x: x[1], reverse=True)
        return [context for context, _ in related_threads[:max_results]]
    
    def _extract_entity_info(self, message: SlackMessage) -> Tuple[Optional[str], Optional[str]]:
        """Extract entity ID and type from message."""
        if not message.metadata:
            return None, None
        
        # Check for PR information
        if 'pr_number' in message.metadata:
            return str(message.metadata['pr_number']), 'pr'
        
        # Check for JIRA ticket information
        if 'ticket_key' in message.metadata:
            return message.metadata['ticket_key'], 'jira'
        
        # Check for alert information
        if 'alert_id' in message.metadata:
            return str(message.metadata['alert_id']), 'alert'
        
        # Check for deployment information
        if 'deployment_id' in message.metadata:
            return str(message.metadata['deployment_id']), 'deployment'
        
        return None, None
    
    def _determine_thread_type(self, message: SlackMessage) -> ThreadType:
        """Determine thread type based on message content."""
        if not message.metadata:
            return ThreadType.CUSTOM
        
        # Check metadata for type hints
        if 'pr_number' in message.metadata:
            return ThreadType.PR_LIFECYCLE
        elif 'ticket_key' in message.metadata:
            return ThreadType.JIRA_UPDATES
        elif 'alert_id' in message.metadata or 'severity' in message.metadata:
            return ThreadType.ALERT_SEQUENCE
        elif 'deployment_id' in message.metadata:
            return ThreadType.DEPLOYMENT_PIPELINE
        elif 'standup' in message.metadata:
            return ThreadType.STANDUP_FOLLOWUP
        
        return ThreadType.CUSTOM
    
    def _extract_message_content(self, message: SlackMessage) -> Dict[str, Any]:
        """Extract content features for similarity comparison."""
        content = {
            'text': message.text or '',
            'blocks': len(message.blocks) if message.blocks else 0,
            'metadata_keys': list(message.metadata.keys()) if message.metadata else []
        }
        
        # Extract key terms from blocks
        if message.blocks:
            text_content = []
            for block in message.blocks:
                if isinstance(block, dict) and 'text' in block:
                    if isinstance(block['text'], dict) and 'text' in block['text']:
                        text_content.append(block['text']['text'])
            content['block_text'] = ' '.join(text_content)
        
        return content
    
    def _calculate_content_similarity(self, content1: Dict[str, Any], content2: Dict[str, Any]) -> float:
        """Calculate similarity between two content dictionaries."""
        similarity = 0.0
        
        # Text similarity (simple word overlap)
        text1 = content1.get('text', '').lower().split()
        text2 = content2.get('text', '').lower().split()
        
        if text1 and text2:
            common_words = set(text1) & set(text2)
            total_words = set(text1) | set(text2)
            if total_words:
                similarity += 0.4 * (len(common_words) / len(total_words))
        
        # Metadata key similarity
        keys1 = set(content1.get('metadata_keys', []))
        keys2 = set(content2.get('metadata_keys', []))
        
        if keys1 or keys2:
            common_keys = keys1 & keys2
            total_keys = keys1 | keys2
            if total_keys:
                similarity += 0.3 * (len(common_keys) / len(total_keys))
        
        # Block structure similarity
        blocks1 = content1.get('blocks', 0)
        blocks2 = content2.get('blocks', 0)
        
        if blocks1 > 0 or blocks2 > 0:
            max_blocks = max(blocks1, blocks2)
            min_blocks = min(blocks1, blocks2)
            similarity += 0.3 * (min_blocks / max_blocks if max_blocks > 0 else 0)
        
        return min(similarity, 1.0)
    
    def _extract_workflow_stage(self, message: SlackMessage) -> Optional[str]:
        """Extract workflow stage from message."""
        if not message.metadata:
            return None
        
        # Common workflow stages
        workflow_indicators = {
            'opened': 'creation',
            'review_requested': 'review',
            'approved': 'approval',
            'merged': 'completion',
            'closed': 'completion',
            'in_progress': 'active',
            'done': 'completion',
            'blocked': 'blocked'
        }
        
        for key, stage in workflow_indicators.items():
            if key in message.metadata or (message.text and key in message.text.lower()):
                return stage
        
        return None
    
    def _is_related_workflow_stage(self, stage: str, context: ThreadContext) -> bool:
        """Check if workflow stage is related to thread context."""
        # Define related workflow stages
        related_stages = {
            'creation': ['review', 'approval'],
            'review': ['approval', 'completion'],
            'approval': ['completion'],
            'active': ['completion', 'blocked'],
            'blocked': ['active', 'completion']
        }
        
        context_stage = context.metadata.get('workflow_stage')
        if not context_stage:
            return False
        
        return stage in related_stages.get(context_stage, [])
    
    def _update_content_vectors(self, message: SlackMessage, channel_id: str, thread_id: str) -> None:
        """Update content vectors for similarity matching."""
        content = self._extract_message_content(message)
        
        if thread_id in self._content_vectors[channel_id]:
            # Merge with existing content
            existing = self._content_vectors[channel_id][thread_id]
            
            # Combine text
            existing_text = existing.get('text', '')
            new_text = content.get('text', '')
            content['text'] = f"{existing_text} {new_text}".strip()
            
            # Combine metadata keys
            existing_keys = set(existing.get('metadata_keys', []))
            new_keys = set(content.get('metadata_keys', []))
            content['metadata_keys'] = list(existing_keys | new_keys)
            
            # Update block count
            content['blocks'] = existing.get('blocks', 0) + content.get('blocks', 0)
        
        self._content_vectors[channel_id][thread_id] = content
    
    def _find_thread_context(self, channel_id: str, thread_ts: str) -> Optional[ThreadContext]:
        """Find thread context by thread timestamp."""
        for context in self._channel_threads[channel_id].values():
            if context.parent_message_ts == thread_ts:
                return context
        return None
    
    def _generate_thread_id(self, message: SlackMessage, channel_id: str, parent_ts: str) -> str:
        """Generate unique thread ID."""
        components = [
            channel_id,
            parent_ts,
            str(int(time.time())),
            str(hash(str(message.metadata)) % 10000) if message.metadata else '0'
        ]
        return hashlib.md5('|'.join(components).encode()).hexdigest()[:12]
    
    def _cleanup_expired_threads(self, channel_id: str) -> None:
        """Clean up expired thread contexts."""
        expired_threads = []
        
        for thread_id, context in self._channel_threads[channel_id].items():
            if context.is_expired(self.config.max_thread_age_hours):
                expired_threads.append(thread_id)
        
        for thread_id in expired_threads:
            del self._channel_threads[channel_id][thread_id]
            
            # Clean up content vectors
            if thread_id in self._content_vectors[channel_id]:
                del self._content_vectors[channel_id][thread_id]
            
            # Clean up entity mappings
            for entity_key, mapped_thread_id in list(self._entity_threads[channel_id].items()):
                if mapped_thread_id == thread_id:
                    del self._entity_threads[channel_id][entity_key]
        
        if expired_threads:
            self._stats['threads_expired'] += len(expired_threads)
            self.logger.info(f"Cleaned up {len(expired_threads)} expired threads in channel {channel_id}")
    
    def get_threading_stats(self) -> Dict[str, Any]:
        """Get threading statistics."""
        active_threads = sum(len(threads) for threads in self._channel_threads.values())
        
        return {
            **self._stats,
            'active_threads': active_threads,
            'active_channels': len(self._channel_threads),
            'total_entities_tracked': sum(len(entities) for entities in self._entity_threads.values()),
            'content_vectors_stored': sum(len(vectors) for vectors in self._content_vectors.values())
        }
    
    def get_channel_threads(self, channel_id: str) -> List[ThreadContext]:
        """Get all active threads for a channel."""
        self._cleanup_expired_threads(channel_id)
        return list(self._channel_threads[channel_id].values())
    
    def update_config(self, new_config: ThreadingConfig) -> None:
        """Update threading configuration."""
        self.config = new_config
        self.logger.info("Threading configuration updated")


# Global threading manager instance
default_threading_manager = MessageThreadingManager()