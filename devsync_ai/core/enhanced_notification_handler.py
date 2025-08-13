"""Enhanced notification handler with integrated formatter system."""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .formatter_factory import (
    SlackMessageFormatterFactory, MessageType, FormatterOptions,
    ProcessingResult, TeamConfig, ChannelConfig
)
from .config_manager import (
    FlexibleConfigurationManager, default_config_manager
)
from .error_handler import (
    ComprehensiveErrorHandler, default_error_handler
)
from .message_batcher import (
    MessageBatcher, BatchableMessage, ContentType, default_message_batcher
)
from .interactive_elements import (
    InteractiveElementBuilder, default_interactive_builder
)
from .message_formatter import SlackMessage, TemplateConfig


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(Enum):
    """Notification processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    BATCHED = "batched"
    RETRYING = "retrying"


@dataclass
class NotificationRequest:
    """Notification request with metadata."""
    id: str
    notification_type: str
    data: Dict[str, Any]
    channel_id: Optional[str] = None
    user_id: Optional[str] = None
    priority: NotificationPriority = NotificationPriority.MEDIUM
    batch_eligible: bool = True
    interactive: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationResult:
    """Result of notification processing."""
    request_id: str
    status: NotificationStatus
    message: Optional[SlackMessage] = None
    error: Optional[str] = None
    sent_at: Optional[datetime] = None
    batch_id: Optional[str] = None
    processing_time_ms: float = 0.0
    fallback_used: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnhancedNotificationHandler:
    """Enhanced notification handler with integrated formatter system."""
    
    def __init__(self, 
                 slack_client,
                 supabase_client=None,
                 config: Optional[TemplateConfig] = None,
                 config_manager: Optional[FlexibleConfigurationManager] = None,
                 error_handler: Optional[ComprehensiveErrorHandler] = None,
                 message_batcher: Optional[MessageBatcher] = None):
        """Initialize enhanced notification handler."""
        
        # Core clients
        self.slack = slack_client
        self.supabase = supabase_client
        
        # Integrated systems
        self.config_manager = config_manager or default_config_manager
        self.error_handler = error_handler or default_error_handler
        self.message_batcher = message_batcher or default_message_batcher
        
        # Add the new formatter
        self.message_formatter = SlackMessageFormatterFactory(config)
        
        # Interactive elements builder
        self.interactive_builder = default_interactive_builder
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Notification tracking
        self._pending_notifications: Dict[str, NotificationRequest] = {}
        self._processing_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'batched': 0,
            'fallback_used': 0
        }
        
        # Configure formatter with team settings
        self._configure_formatter()
        
        self.logger.info("EnhancedNotificationHandler initialized")
    
    def _configure_formatter(self):
        """Configure formatter with current team settings."""
        try:
            config = self.config_manager.load_configuration()
            
            # Configure team settings
            team_config = TeamConfig(
                team_id=config.team_settings.team_id,
                default_formatting=config.team_settings.default_formatting.value,
                emoji_set={
                    'success': '✅',
                    'warning': '⚠️',
                    'error': '❌',
                    'info': 'ℹ️',
                    'pr': '🔄',
                    'jira': '📋',
                    'alert': '🚨'
                },
                color_scheme={
                    'primary': config.team_settings.visual_styling.brand_color,
                    'success': '#28a745',
                    'warning': '#ffc107',
                    'danger': '#dc3545',
                    'info': '#17a2b8'
                },
                branding={
                    'team_name': config.team_settings.team_name,
                    'brand_color': config.team_settings.visual_styling.brand_color,
                    'emoji_style': config.team_settings.visual_styling.emoji_style.value,
                    'message_density': config.team_settings.visual_styling.message_density.value
                }
            )
            
            self.message_formatter.configure_team(team_config)
            
            # Configure channel overrides
            for channel_id, channel_override in config.channel_overrides.items():
                channel_config = ChannelConfig(
                    channel_id=channel_id,
                    formatting_style=channel_override.formatting_style.value,
                    interactive_elements=channel_override.interactive_elements,
                    threading_enabled=True,
                    custom_branding=channel_override.custom_branding or {}
                )
                self.message_formatter.configure_channel(channel_config)
            
            self.logger.info("Formatter configured with team settings")
            
        except Exception as e:
            self.logger.warning(f"Failed to configure formatter: {e}")
    
    def send_notification(self, 
                         notification_type: str,
                         data: Dict[str, Any],
                         channel_id: Optional[str] = None,
                         user_id: Optional[str] = None,
                         priority: NotificationPriority = NotificationPriority.MEDIUM,
                         batch_eligible: bool = True,
                         interactive: bool = True) -> NotificationResult:
        """Send a single notification."""
        
        # Create notification request
        request = NotificationRequest(
            id=f"{notification_type}_{int(datetime.now().timestamp())}_{len(self._pending_notifications)}",
            notification_type=notification_type,
            data=data,
            channel_id=channel_id,
            user_id=user_id,
            priority=priority,
            batch_eligible=batch_eligible,
            interactive=interactive
        )
        
        return self._process_notification(request)
    
    def send_batch_notification(self,
                               notification_type: str,
                               batch_items: List[Dict[str, Any]],
                               channel_id: Optional[str] = None,
                               user_id: Optional[str] = None,
                               priority: NotificationPriority = NotificationPriority.MEDIUM) -> NotificationResult:
        """Send a batch notification."""
        
        # Create batch notification request
        request = NotificationRequest(
            id=f"batch_{notification_type}_{int(datetime.now().timestamp())}",
            notification_type=notification_type,
            data={'batch_items': batch_items, 'batch_type': 'manual'},
            channel_id=channel_id,
            user_id=user_id,
            priority=priority,
            batch_eligible=False,  # Already batched
            interactive=True
        )
        
        return self._process_batch_notification(request)
    
    def _process_notification(self, request: NotificationRequest) -> NotificationResult:
        """Process a single notification with error handling."""
        start_time = datetime.now()
        
        try:
            # Check if notification should be batched
            if request.batch_eligible and self._should_batch_notification(request):
                return self._add_to_batch(request)
            
            # Format single message using new formatter
            result = self._format_single_message(request.notification_type, request.data, request)
            
            if result.status == NotificationStatus.SENT:
                self._processing_stats['successful'] += 1
            else:
                self._processing_stats['failed'] += 1
            
            if result.fallback_used:
                self._processing_stats['fallback_used'] += 1
            
            self._processing_stats['total_processed'] += 1
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            result.processing_time_ms = processing_time
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process notification {request.id}: {e}")
            return NotificationResult(
                request_id=request.id,
                status=NotificationStatus.FAILED,
                error=str(e),
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def _process_batch_notification(self, request: NotificationRequest) -> NotificationResult:
        """Process a batch notification."""
        start_time = datetime.now()
        
        try:
            # Format batch message using new formatter
            result = self._format_batch_message(request.notification_type, request.data['batch_items'], request)
            
            if result.status == NotificationStatus.SENT:
                self._processing_stats['successful'] += 1
                self._processing_stats['batched'] += 1
            else:
                self._processing_stats['failed'] += 1
            
            if result.fallback_used:
                self._processing_stats['fallback_used'] += 1
            
            self._processing_stats['total_processed'] += 1
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            result.processing_time_ms = processing_time
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process batch notification {request.id}: {e}")
            return NotificationResult(
                request_id=request.id,
                status=NotificationStatus.FAILED,
                error=str(e),
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def _format_single_message(self, notification_type: str, data: Dict[str, Any], request: NotificationRequest) -> NotificationResult:
        """Replace existing formatting logic with new formatter."""
        
        def format_operation(data):
            # Map notification type to message type
            message_type = self._map_notification_to_message_type(notification_type)
            
            # Create formatter options
            options = FormatterOptions(
                batch=False,
                interactive=request.interactive,
                accessibility_mode=False,
                threading_enabled=True,
                experimental_features=False
            )
            
            # Format message using new formatter
            processing_result = self.message_formatter.format_message(
                message_type=message_type,
                data=data,
                channel=request.channel_id,
                team_id=None,  # Will be determined from config
                options=options
            )
            
            if not processing_result.success:
                raise Exception(processing_result.error)
            
            return processing_result.message
        
        # Use error handler for robust processing
        try:
            message = self.error_handler.handle_with_recovery(
                format_operation,
                data,
                template_type=notification_type
            )
            
            # Send message
            success = self._send_slack_message(message, request.channel_id)
            
            return NotificationResult(
                request_id=request.id,
                status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
                message=message,
                sent_at=datetime.now() if success else None,
                fallback_used=message.metadata.get('degraded', False) or message.metadata.get('error', False)
            )
            
        except Exception as e:
            return NotificationResult(
                request_id=request.id,
                status=NotificationStatus.FAILED,
                error=str(e)
            )
    
    def _format_batch_message(self, notification_type: str, batch_items: List[Dict[str, Any]], request: NotificationRequest) -> NotificationResult:
        """Replace existing batch formatting with new formatter."""
        
        def format_batch_operation(batch_data):
            # Map notification type to message type
            message_type = self._map_notification_to_message_type(notification_type)
            
            # Create formatter options
            options = FormatterOptions(
                batch=True,
                interactive=request.interactive,
                accessibility_mode=False,
                threading_enabled=True,
                experimental_features=False
            )
            
            # Format batch message using new formatter
            processing_result = self.message_formatter.format_message(
                message_type=message_type,
                data=batch_data,
                channel=request.channel_id,
                team_id=None,  # Will be determined from config
                options=options
            )
            
            if not processing_result.success:
                raise Exception(processing_result.error)
            
            return processing_result.message
        
        # Prepare batch data
        batch_data = {
            'batch_items': batch_items,
            'batch_type': 'manual',
            'batch_size': len(batch_items)
        }
        
        # Use error handler for robust processing
        try:
            message = self.error_handler.handle_with_recovery(
                format_batch_operation,
                batch_data,
                template_type=notification_type
            )
            
            # Send message
            success = self._send_slack_message(message, request.channel_id)
            
            return NotificationResult(
                request_id=request.id,
                status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
                message=message,
                sent_at=datetime.now() if success else None,
                batch_id=request.data.get('batch_id'),
                fallback_used=message.metadata.get('degraded', False) or message.metadata.get('error', False)
            )
            
        except Exception as e:
            return NotificationResult(
                request_id=request.id,
                status=NotificationStatus.FAILED,
                error=str(e)
            )
    
    def _should_batch_notification(self, request: NotificationRequest) -> bool:
        """Determine if notification should be batched."""
        # Check configuration for batching settings
        effective_config = self.config_manager.get_effective_config(
            channel_id=request.channel_id,
            user_id=request.user_id,
            template_type=request.notification_type
        )
        
        # Don't batch critical notifications
        if request.priority == NotificationPriority.CRITICAL:
            return False
        
        # Check channel-specific batch threshold
        batch_threshold = effective_config.get('batch_threshold', 5)
        
        # Simple batching logic - in production you'd want more sophisticated logic
        return batch_threshold > 1
    
    def _add_to_batch(self, request: NotificationRequest) -> NotificationResult:
        """Add notification to batch processing."""
        try:
            # Convert to batchable message
            content_type = self._map_notification_to_content_type(request.notification_type)
            
            batchable_message = BatchableMessage(
                id=request.id,
                content_type=content_type,
                timestamp=request.created_at,
                author=request.data.get('author', request.data.get('user', {}).get('name')),
                priority=request.priority.value,
                data=request.data,
                metadata=request.metadata
            )
            
            # Add to batcher
            batched_message = self.message_batcher.add_message(batchable_message)
            
            if batched_message:
                # Batch was triggered, send it
                success = self._send_slack_message(batched_message, request.channel_id)
                
                return NotificationResult(
                    request_id=request.id,
                    status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
                    message=batched_message,
                    sent_at=datetime.now() if success else None,
                    batch_id=batched_message.metadata.get('batch_id')
                )
            else:
                # Added to pending batch
                return NotificationResult(
                    request_id=request.id,
                    status=NotificationStatus.BATCHED
                )
                
        except Exception as e:
            self.logger.error(f"Failed to add notification to batch: {e}")
            # Fall back to single message
            return self._format_single_message(request.notification_type, request.data, request)
    
    def _map_notification_to_message_type(self, notification_type: str) -> MessageType:
        """Map notification type to message type."""
        mapping = {
            'pr_opened': MessageType.PR_UPDATE,
            'pr_merged': MessageType.PR_UPDATE,
            'pr_closed': MessageType.PR_UPDATE,
            'pr_ready_for_review': MessageType.PR_UPDATE,
            'pr_approved': MessageType.PR_UPDATE,
            'pr_batch': MessageType.PR_BATCH,
            'jira_created': MessageType.JIRA_UPDATE,
            'jira_updated': MessageType.JIRA_UPDATE,
            'jira_resolved': MessageType.JIRA_UPDATE,
            'jira_batch': MessageType.JIRA_BATCH,
            'standup': MessageType.STANDUP,
            'blocker': MessageType.BLOCKER,
            'alert': MessageType.BLOCKER,  # Alerts as blockers
            'deployment': MessageType.PR_UPDATE,  # Deployments as PR updates
        }
        
        return mapping.get(notification_type, MessageType.PR_UPDATE)
    
    def _map_notification_to_content_type(self, notification_type: str) -> ContentType:
        """Map notification type to content type for batching."""
        mapping = {
            'pr_opened': ContentType.PR_UPDATE,
            'pr_merged': ContentType.PR_UPDATE,
            'pr_closed': ContentType.PR_UPDATE,
            'pr_ready_for_review': ContentType.PR_UPDATE,
            'pr_approved': ContentType.PR_UPDATE,
            'jira_created': ContentType.JIRA_UPDATE,
            'jira_updated': ContentType.JIRA_UPDATE,
            'jira_resolved': ContentType.JIRA_UPDATE,
            'standup': ContentType.STANDUP,
            'blocker': ContentType.BLOCKER,
            'alert': ContentType.ALERT,
            'deployment': ContentType.DEPLOYMENT,
        }
        
        return mapping.get(notification_type, ContentType.PR_UPDATE)
    
    def _send_slack_message(self, message: SlackMessage, channel_id: Optional[str] = None) -> bool:
        """Send message to Slack."""
        try:
            # Prepare message payload
            payload = {
                'blocks': message.blocks,
                'text': message.text
            }
            
            if channel_id:
                payload['channel'] = channel_id
            
            if message.thread_ts:
                payload['thread_ts'] = message.thread_ts
            
            # Send via Slack client
            response = self.slack.chat_postMessage(**payload)
            
            if response.get('ok'):
                self.logger.info(f"Message sent successfully to {channel_id or 'default channel'}")
                return True
            else:
                self.logger.error(f"Failed to send message: {response.get('error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending Slack message: {e}")
            return False
    
    def flush_pending_batches(self) -> List[NotificationResult]:
        """Flush all pending batches."""
        results = []
        
        try:
            batched_messages = self.message_batcher.flush_all_batches()
            
            for batched_message in batched_messages:
                # Determine channel from batch metadata or use default
                channel_id = batched_message.metadata.get('channel_id')
                
                success = self._send_slack_message(batched_message, channel_id)
                
                result = NotificationResult(
                    request_id=f"batch_{batched_message.metadata.get('batch_id', 'unknown')}",
                    status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
                    message=batched_message,
                    sent_at=datetime.now() if success else None,
                    batch_id=batched_message.metadata.get('batch_id')
                )
                
                results.append(result)
                
                if success:
                    self._processing_stats['successful'] += 1
                    self._processing_stats['batched'] += 1
                else:
                    self._processing_stats['failed'] += 1
            
            self.logger.info(f"Flushed {len(batched_messages)} pending batches")
            
        except Exception as e:
            self.logger.error(f"Error flushing pending batches: {e}")
        
        return results
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get notification processing statistics."""
        stats = self._processing_stats.copy()
        
        # Add error handler stats
        error_stats = self.error_handler.get_error_metrics()
        stats['error_metrics'] = error_stats
        
        # Add batcher stats
        batch_stats = self.message_batcher.get_batch_stats()
        stats['batch_metrics'] = batch_stats
        
        # Add formatter stats
        formatter_stats = self.message_formatter.get_metrics()
        stats['formatter_metrics'] = formatter_stats
        
        return stats
    
    def update_configuration(self):
        """Update configuration from config manager."""
        try:
            self._configure_formatter()
            self.logger.info("Configuration updated successfully")
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components."""
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        try:
            # Check Slack client
            health['components']['slack'] = {
                'status': 'healthy' if self.slack else 'unavailable'
            }
            
            # Check configuration manager
            config = self.config_manager.load_configuration()
            health['components']['config_manager'] = {
                'status': 'healthy',
                'team_id': config.team_settings.team_id
            }
            
            # Check error handler
            error_metrics = self.error_handler.get_error_metrics()
            health['components']['error_handler'] = {
                'status': 'healthy',
                'total_errors': error_metrics['total_errors']
            }
            
            # Check message batcher
            batch_stats = self.message_batcher.get_batch_stats()
            health['components']['message_batcher'] = {
                'status': 'healthy',
                'active_batches': batch_stats['active_batches']
            }
            
            # Check message formatter
            formatter_metrics = self.message_formatter.get_metrics()
            health['components']['message_formatter'] = {
                'status': 'healthy',
                'total_messages': formatter_metrics['total_messages']
            }
            
        except Exception as e:
            health['status'] = 'degraded'
            health['error'] = str(e)
        
        return health


# Convenience functions for common notification types
def send_pr_notification(handler: EnhancedNotificationHandler,
                        pr_data: Dict[str, Any],
                        action: str,
                        channel_id: Optional[str] = None) -> NotificationResult:
    """Send PR notification."""
    notification_type = f"pr_{action}"
    return handler.send_notification(
        notification_type=notification_type,
        data=pr_data,
        channel_id=channel_id,
        priority=NotificationPriority.MEDIUM,
        interactive=True
    )


def send_jira_notification(handler: EnhancedNotificationHandler,
                          jira_data: Dict[str, Any],
                          action: str,
                          channel_id: Optional[str] = None) -> NotificationResult:
    """Send JIRA notification."""
    notification_type = f"jira_{action}"
    return handler.send_notification(
        notification_type=notification_type,
        data=jira_data,
        channel_id=channel_id,
        priority=NotificationPriority.MEDIUM,
        interactive=True
    )


def send_alert_notification(handler: EnhancedNotificationHandler,
                           alert_data: Dict[str, Any],
                           channel_id: Optional[str] = None,
                           priority: NotificationPriority = NotificationPriority.HIGH) -> NotificationResult:
    """Send alert notification."""
    return handler.send_notification(
        notification_type="alert",
        data=alert_data,
        channel_id=channel_id,
        priority=priority,
        batch_eligible=priority != NotificationPriority.CRITICAL,
        interactive=True
    )