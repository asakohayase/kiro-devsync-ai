"""Enhanced message formatter with threading support."""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from .message_formatter import SlackMessage, MessageFormatter
from .message_threading import MessageThreadingManager, ThreadContext, ThreadType
from .smart_message_batcher import SmartMessageBatcher


@dataclass
class ThreadedMessage:
    """Message with threading information."""
    message: SlackMessage
    thread_ts: Optional[str] = None
    thread_context: Optional[ThreadContext] = None
    is_thread_starter: bool = False
    related_threads: List[ThreadContext] = None
    
    def __post_init__(self):
        if self.related_threads is None:
            self.related_threads = []


class ThreadedMessageFormatter(MessageFormatter):
    """Enhanced message formatter with threading support."""
    
    def __init__(self, 
                 threading_manager: Optional[MessageThreadingManager] = None,
                 batcher: Optional[SmartMessageBatcher] = None):
        """Initialize threaded message formatter."""
        super().__init__()
        self.threading_manager = threading_manager or MessageThreadingManager()
        self.batcher = batcher
        self.logger = logging.getLogger(__name__)
    
    def format_message(self, data: Dict[str, Any]) -> SlackMessage:
        """Format raw data into a Slack message (basic implementation)."""
        # Basic implementation - in practice, this would use specific templates
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": data.get('text', 'No content provided')
                }
            }
        ]
        
        return SlackMessage(
            blocks=blocks,
            text=data.get('text', 'No content provided'),
            metadata=data.get('metadata', {})
        )
    
    def format_with_threading(self, 
                            template_data: Dict[str, Any], 
                            channel_id: str,
                            template_type: str = "default") -> ThreadedMessage:
        """Format message with threading support."""
        # Create base message
        base_message = self.format_message(template_data)
        
        # Enhance message metadata for threading
        self._enhance_message_metadata(base_message, template_data)
        
        # Determine if message should be threaded
        thread_ts = self.threading_manager.should_thread_message(base_message, channel_id)
        
        thread_context = None
        is_thread_starter = False
        
        if thread_ts:
            # Add to existing thread
            success = self.threading_manager.add_message_to_thread(base_message, channel_id, thread_ts)
            if success:
                thread_context = self.threading_manager.get_thread_context(channel_id, thread_ts)
                self.logger.info(f"Message added to existing thread {thread_ts}")
            else:
                thread_ts = None
        else:
            # Check if this should start a new thread
            if self._should_start_new_thread(base_message, template_data):
                # This message will be the thread starter
                is_thread_starter = True
                # We'll set thread_ts after the message is sent and we get the timestamp
                self.logger.info("Message marked as thread starter")
        
        # Get related threads for context
        related_threads = self.threading_manager.get_related_threads(base_message, channel_id)
        
        # Enhance message with threading information
        if thread_context or related_threads:
            self._add_threading_context_to_message(base_message, thread_context, related_threads)
        
        return ThreadedMessage(
            message=base_message,
            thread_ts=thread_ts,
            thread_context=thread_context,
            is_thread_starter=is_thread_starter,
            related_threads=related_threads
        )
    
    def create_thread_starter(self, 
                            threaded_message: ThreadedMessage, 
                            channel_id: str,
                            message_ts: str) -> ThreadContext:
        """Create thread context for a thread starter message."""
        if not threaded_message.is_thread_starter:
            raise ValueError("Message is not marked as thread starter")
        
        # Determine thread type
        thread_type = self._determine_thread_type_from_message(threaded_message.message)
        
        # Create thread context
        thread_context = self.threading_manager.create_thread_context(
            threaded_message.message,
            channel_id,
            message_ts,
            thread_type
        )
        
        # Update the threaded message
        threaded_message.thread_context = thread_context
        threaded_message.thread_ts = message_ts
        threaded_message.is_thread_starter = False  # No longer a starter, now it's the parent
        
        return thread_context
    
    def format_thread_summary(self, 
                            thread_context: ThreadContext, 
                            channel_id: str) -> SlackMessage:
        """Format a summary message for a thread."""
        blocks = []
        
        # Thread header
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🧵 Thread Summary: {thread_context.thread_type.value.replace('_', ' ').title()}",
                "emoji": True
            }
        })
        
        # Thread statistics
        stats_text = []
        stats_text.append(f"📊 *Messages:* {thread_context.message_count}")
        stats_text.append(f"👥 *Participants:* {len(thread_context.participants)}")
        stats_text.append(f"⏰ *Duration:* {self._format_duration(thread_context.created_at, thread_context.last_updated)}")
        
        if thread_context.entity_id:
            stats_text.append(f"🔗 *Entity:* {thread_context.entity_type}:{thread_context.entity_id}")
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(stats_text)
            }
        })
        
        # Participants
        if thread_context.participants:
            participant_list = ", ".join(f"@{p}" for p in list(thread_context.participants)[:10])
            if len(thread_context.participants) > 10:
                participant_list += f" and {len(thread_context.participants) - 10} others"
            
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"👥 *Participants:* {participant_list}"
                    }
                ]
            })
        
        # Action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📋 View Full Thread",
                        "emoji": True
                    },
                    "action_id": "view_thread",
                    "value": thread_context.thread_id
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔗 Copy Thread Link",
                        "emoji": True
                    },
                    "action_id": "copy_thread_link",
                    "value": thread_context.parent_message_ts
                }
            ]
        })
        
        # Fallback text
        fallback_text = f"Thread Summary: {thread_context.thread_type.value} - {thread_context.message_count} messages from {len(thread_context.participants)} participants"
        
        return SlackMessage(
            blocks=blocks,
            text=fallback_text,
            metadata={
                'thread_summary': True,
                'thread_id': thread_context.thread_id,
                'thread_type': thread_context.thread_type.value,
                'message_count': thread_context.message_count
            }
        )
    
    def format_related_threads_notification(self, 
                                          related_threads: List[ThreadContext], 
                                          current_message: SlackMessage) -> SlackMessage:
        """Format notification about related threads."""
        if not related_threads:
            return None
        
        blocks = []
        
        # Header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🔗 *Related Discussions* ({len(related_threads)} found)"
            }
        })
        
        # List related threads
        for i, thread in enumerate(related_threads[:3]):  # Show max 3
            thread_text = f"• *{thread.thread_type.value.replace('_', ' ').title()}*"
            if thread.entity_id:
                thread_text += f" ({thread.entity_type}:{thread.entity_id})"
            thread_text += f" - {thread.message_count} messages"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": thread_text
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Thread",
                        "emoji": True
                    },
                    "action_id": "view_related_thread",
                    "value": thread.parent_message_ts
                }
            })
        
        if len(related_threads) > 3:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"... and {len(related_threads) - 3} more related discussions"
                    }
                ]
            })
        
        return SlackMessage(
            blocks=blocks,
            text=f"Found {len(related_threads)} related discussions",
            metadata={
                'related_threads_notification': True,
                'related_count': len(related_threads)
            }
        )
    
    def _enhance_message_metadata(self, message: SlackMessage, template_data: Dict[str, Any]) -> None:
        """Enhance message metadata for better threading."""
        if not message.metadata:
            message.metadata = {}
        
        # Extract common threading identifiers
        if 'pr' in template_data:
            pr_data = template_data['pr']
            message.metadata['pr_number'] = pr_data.get('number')
            message.metadata['repository'] = pr_data.get('repository', {}).get('name')
        
        if 'ticket' in template_data:
            ticket_data = template_data['ticket']
            message.metadata['ticket_key'] = ticket_data.get('key')
            message.metadata['project'] = ticket_data.get('project', {}).get('key')
        
        if 'alert' in template_data:
            alert_data = template_data['alert']
            message.metadata['alert_id'] = alert_data.get('id')
            message.metadata['severity'] = alert_data.get('severity')
        
        if 'deployment' in template_data:
            deployment_data = template_data['deployment']
            message.metadata['deployment_id'] = deployment_data.get('id')
            message.metadata['environment'] = deployment_data.get('environment')
        
        # Add author information
        if 'author' in template_data:
            message.metadata['author'] = template_data['author']
        elif 'user' in template_data:
            message.metadata['author'] = template_data['user']
    
    def _should_start_new_thread(self, message: SlackMessage, template_data: Dict[str, Any]) -> bool:
        """Determine if message should start a new thread."""
        # Check if message has threading-worthy content
        if not message.metadata:
            return False
        
        # PR lifecycle events should start threads
        if 'pr_number' in message.metadata:
            return True
        
        # JIRA ticket updates should start threads
        if 'ticket_key' in message.metadata:
            return True
        
        # Alerts should start threads
        if 'alert_id' in message.metadata:
            return True
        
        # Deployment events should start threads
        if 'deployment_id' in message.metadata:
            return True
        
        # Check for specific template types that should start threads
        thread_starting_types = [
            'pr_opened', 'pr_ready_for_review', 'ticket_created', 
            'alert_triggered', 'deployment_started', 'incident_created'
        ]
        
        template_type = template_data.get('template_type', '')
        return template_type in thread_starting_types
    
    def _determine_thread_type_from_message(self, message: SlackMessage) -> ThreadType:
        """Determine thread type from message content."""
        if not message.metadata:
            return ThreadType.CUSTOM
        
        if 'pr_number' in message.metadata:
            return ThreadType.PR_LIFECYCLE
        elif 'ticket_key' in message.metadata:
            return ThreadType.JIRA_UPDATES
        elif 'alert_id' in message.metadata:
            return ThreadType.ALERT_SEQUENCE
        elif 'deployment_id' in message.metadata:
            return ThreadType.DEPLOYMENT_PIPELINE
        elif 'standup' in message.metadata:
            return ThreadType.STANDUP_FOLLOWUP
        
        return ThreadType.CUSTOM
    
    def _add_threading_context_to_message(self, 
                                        message: SlackMessage, 
                                        thread_context: Optional[ThreadContext],
                                        related_threads: List[ThreadContext]) -> None:
        """Add threading context information to message blocks."""
        if not message.blocks:
            return
        
        # Add thread context information
        if thread_context and thread_context.message_count > 1:
            context_text = f"🧵 Part of ongoing discussion ({thread_context.message_count} messages)"
            
            # Add context block
            context_block = {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": context_text
                    }
                ]
            }
            
            # Insert at the beginning
            message.blocks.insert(0, context_block)
        
        # Add related threads information
        if related_threads and len(related_threads) > 0:
            related_text = f"🔗 {len(related_threads)} related discussion{'s' if len(related_threads) > 1 else ''} available"
            
            related_block = {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": related_text
                    }
                ]
            }
            
            # Add at the end
            message.blocks.append(related_block)
    
    def _format_duration(self, start_time, end_time) -> str:
        """Format duration between two timestamps."""
        duration = end_time - start_time
        
        if duration.days > 0:
            return f"{duration.days}d {duration.seconds // 3600}h"
        elif duration.seconds >= 3600:
            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        elif duration.seconds >= 60:
            minutes = duration.seconds // 60
            return f"{minutes}m"
        else:
            return "< 1m"
    
    def get_threading_stats(self) -> Dict[str, Any]:
        """Get threading statistics."""
        return self.threading_manager.get_threading_stats()
    
    def cleanup_expired_threads(self, channel_id: str) -> None:
        """Clean up expired threads for a channel."""
        self.threading_manager._cleanup_expired_threads(channel_id)


# Global threaded formatter instance
default_threaded_formatter = ThreadedMessageFormatter()