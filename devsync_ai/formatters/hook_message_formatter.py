"""
Hook message formatter for Agent Hook notifications.

This formatter integrates Agent Hooks with the existing SlackMessageFormatterFactory
to provide specialized formatting for hook events while maintaining consistency
with the overall template system.
"""

import logging
from typing import Dict, List, Any, Optional, Type
from datetime import datetime
from enum import Enum

from ..core.message_formatter import MessageFormatter, SlackMessage, TemplateConfig
from ..core.exceptions import FormattingError, DataValidationError
from ..core.agent_hooks import EnrichedEvent, HookExecutionResult, EventCategory
from ..templates.hook_templates import (
    HookStatusChangeTemplate,
    HookBlockerTemplate, 
    HookAssignmentTemplate,
    HookCommentTemplate,
    HookEventType
)


logger = logging.getLogger(__name__)


class HookMessageType(Enum):
    """Message types for hook notifications."""
    STATUS_CHANGE = "hook_status_change"
    BLOCKER_DETECTED = "hook_blocker_detected"
    BLOCKER_RESOLVED = "hook_blocker_resolved"
    ASSIGNMENT = "hook_assignment"
    COMMENT = "hook_comment"
    PRIORITY_CHANGE = "hook_priority_change"
    WORKLOAD_ALERT = "hook_workload_alert"
    SPRINT_UPDATE = "hook_sprint_update"


class HookMessageFormatter(MessageFormatter):
    """
    Specialized formatter for Agent Hook notifications.
    
    This formatter provides hook-specific message formatting while integrating
    with the existing template system and SlackMessageFormatterFactory.
    """
    
    def __init__(self, config: Optional[TemplateConfig] = None):
        """Initialize hook message formatter."""
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Template registry for hook types
        self._template_registry: Dict[HookEventType, Type] = {
            HookEventType.STATUS_CHANGE: HookStatusChangeTemplate,
            HookEventType.BLOCKER_DETECTED: HookBlockerTemplate,
            HookEventType.BLOCKER_RESOLVED: HookBlockerTemplate,
            HookEventType.ASSIGNMENT: HookAssignmentTemplate,
            HookEventType.COMMENT: HookCommentTemplate,
        }
        
        # Template instances cache
        self._template_instances: Dict[str, Any] = {}
    
    def format_message(self, data: Dict[str, Any]) -> SlackMessage:
        """
        Format hook event data into a Slack message.
        
        Args:
            data: Hook event data containing event, execution result, and context
            
        Returns:
            Formatted SlackMessage
        """
        try:
            # Validate required fields
            self._validate_hook_data(data)
            
            # Determine hook event type
            hook_event_type = self._determine_hook_event_type(data)
            
            # Get appropriate template
            template = self._get_template_for_event_type(hook_event_type)
            
            # Prepare template data
            template_data = self._prepare_template_data(data, hook_event_type)
            
            # Format message using template
            message = template.format_message(template_data)
            
            # Add hook-specific metadata
            message.metadata.update({
                'hook_type': data.get('hook_type', 'unknown'),
                'hook_event_type': hook_event_type.value,
                'event_id': data.get('event', {}).get('event_id'),
                'execution_id': data.get('execution_result', {}).get('execution_id'),
                'formatted_by': 'HookMessageFormatter'
            })
            
            self.logger.info(f"Formatted hook message for event type: {hook_event_type.value}")
            return message
            
        except Exception as e:
            self.logger.error(f"Failed to format hook message: {e}", exc_info=True)
            return self.handle_formatting_error(e, data)
    
    def format_hook_execution_result(self, 
                                   hook_type: str,
                                   event: EnrichedEvent,
                                   execution_result: HookExecutionResult,
                                   additional_context: Optional[Dict[str, Any]] = None) -> SlackMessage:
        """
        Format a hook execution result into a Slack message.
        
        Args:
            hook_type: Type of hook that executed
            event: The enriched event that triggered the hook
            execution_result: Result of the hook execution
            additional_context: Additional context data
            
        Returns:
            Formatted SlackMessage
        """
        data = {
            'hook_type': hook_type,
            'event': self._serialize_event(event),
            'execution_result': self._serialize_execution_result(execution_result),
            'additional_context': additional_context or {}
        }
        
        return self.format_message(data)
    
    def format_batch_hook_results(self, 
                                hook_results: List[Dict[str, Any]],
                                batch_context: Optional[Dict[str, Any]] = None) -> SlackMessage:
        """
        Format multiple hook execution results into a batch message.
        
        Args:
            hook_results: List of hook execution results
            batch_context: Context for the batch operation
            
        Returns:
            Formatted SlackMessage for batch results
        """
        try:
            # Create batch summary
            batch_data = {
                'message_type': 'hook_batch',
                'hook_results': hook_results,
                'batch_context': batch_context or {},
                'total_hooks': len(hook_results),
                'successful_hooks': sum(1 for result in hook_results 
                                      if result.get('execution_result', {}).get('status') == 'success'),
                'failed_hooks': sum(1 for result in hook_results 
                                  if result.get('execution_result', {}).get('status') == 'failed')
            }
            
            # Create batch message blocks
            blocks = self._create_batch_message_blocks(batch_data)
            
            # Create fallback text
            fallback_text = (f"Hook Batch Results: {batch_data['successful_hooks']} successful, "
                           f"{batch_data['failed_hooks']} failed out of {batch_data['total_hooks']} total")
            
            return SlackMessage(
                blocks=blocks,
                text=fallback_text,
                metadata={
                    'message_type': 'hook_batch',
                    'total_hooks': batch_data['total_hooks'],
                    'successful_hooks': batch_data['successful_hooks'],
                    'failed_hooks': batch_data['failed_hooks'],
                    'formatted_by': 'HookMessageFormatter'
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to format batch hook results: {e}", exc_info=True)
            return self.handle_formatting_error(e, {'hook_results': hook_results})
    
    def _validate_hook_data(self, data: Dict[str, Any]) -> None:
        """Validate hook event data."""
        required_fields = ['hook_type']
        
        # Check for either event or execution_result
        if 'event' not in data and 'execution_result' not in data:
            raise DataValidationError("Hook data must contain either 'event' or 'execution_result'")
        
        # Validate required fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise DataValidationError(f"Missing required fields: {missing_fields}")
    
    def _determine_hook_event_type(self, data: Dict[str, Any]) -> HookEventType:
        """Determine the hook event type from the data."""
        hook_type = data.get('hook_type', '').lower()
        
        # Map hook types to event types
        hook_type_mapping = {
            'statuschangehook': HookEventType.STATUS_CHANGE,
            'status_change_hook': HookEventType.STATUS_CHANGE,
            'blockerhook': HookEventType.BLOCKER_DETECTED,
            'blocker_hook': HookEventType.BLOCKER_DETECTED,
            'assignmenthook': HookEventType.ASSIGNMENT,
            'assignment_hook': HookEventType.ASSIGNMENT,
            'commenthook': HookEventType.COMMENT,
            'comment_hook': HookEventType.COMMENT,
        }
        
        # Check execution result metadata for more specific type
        execution_result = data.get('execution_result', {})
        if execution_result:
            metadata = execution_result.get('metadata', {})
            
            # Check for blocker resolution
            if 'blocker_resolved' in metadata and metadata['blocker_resolved']:
                return HookEventType.BLOCKER_RESOLVED
            
            # Check for specific transition types
            transition_type = metadata.get('transition_type')
            if transition_type == 'blocked':
                return HookEventType.BLOCKER_DETECTED
            elif transition_type in ['forward', 'backward', 'completed', 'reopened']:
                return HookEventType.STATUS_CHANGE
        
        # Check event classification
        event = data.get('event', {})
        if event:
            classification = event.get('classification', {})
            if classification:
                category = classification.get('category')
                if hasattr(category, 'value'):
                    category_value = category.value
                elif isinstance(category, str):
                    category_value = category
                else:
                    category_value = str(category)
                
                category_mapping = {
                    'status_change': HookEventType.STATUS_CHANGE,
                    'assignment': HookEventType.ASSIGNMENT,
                    'comment': HookEventType.COMMENT,
                    'blocker': HookEventType.BLOCKER_DETECTED,
                }
                
                if category_value in category_mapping:
                    return category_mapping[category_value]
        
        # Fallback to hook type mapping
        return hook_type_mapping.get(hook_type, HookEventType.STATUS_CHANGE)
    
    def _get_template_for_event_type(self, event_type: HookEventType) -> Any:
        """Get template instance for the given event type."""
        template_class = self._template_registry.get(event_type)
        
        if not template_class:
            self.logger.warning(f"No template found for event type: {event_type.value}, using default")
            template_class = HookStatusChangeTemplate
        
        # Create or get cached template instance
        template_key = f"{template_class.__name__}_{hash(str(self.config.__dict__))}"
        
        if template_key not in self._template_instances:
            self._template_instances[template_key] = template_class(config=self.config)
        
        return self._template_instances[template_key]
    
    def _prepare_template_data(self, data: Dict[str, Any], event_type: HookEventType) -> Dict[str, Any]:
        """Prepare data for template formatting."""
        template_data = {}
        
        # Extract event data
        event = data.get('event', {})
        if event:
            template_data['event'] = event
            
            # Extract ticket data from event
            ticket_details = event.get('ticket_details', {})
            if ticket_details:
                template_data['ticket'] = ticket_details
        
        # Extract execution result data
        execution_result = data.get('execution_result', {})
        if execution_result:
            template_data['execution_result'] = execution_result
            
            # Extract metadata
            metadata = execution_result.get('metadata', {})
            template_data.update(metadata)
        
        # Add additional context
        additional_context = data.get('additional_context', {})
        template_data.update(additional_context)
        
        # Event-type specific data preparation
        if event_type == HookEventType.STATUS_CHANGE:
            template_data = self._prepare_status_change_data(template_data)
        elif event_type in [HookEventType.BLOCKER_DETECTED, HookEventType.BLOCKER_RESOLVED]:
            template_data = self._prepare_blocker_data(template_data)
        elif event_type == HookEventType.ASSIGNMENT:
            template_data = self._prepare_assignment_data(template_data)
        elif event_type == HookEventType.COMMENT:
            template_data = self._prepare_comment_data(template_data)
        
        return template_data
    
    def _prepare_status_change_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for status change template."""
        # Ensure transition_analysis exists
        if 'transition_analysis' not in data:
            data['transition_analysis'] = {
                'type': data.get('transition_type', 'forward'),
                'from_status': data.get('from_status', 'unknown'),
                'to_status': data.get('to_status', 'unknown'),
                'urgency': data.get('urgency', 'medium'),
                'is_significant': data.get('is_significant', False)
            }
        
        return data
    
    def _prepare_blocker_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for blocker template."""
        # Ensure blocker_analysis exists
        if 'blocker_analysis' not in data:
            data['blocker_analysis'] = {
                'blocker_type': data.get('blocker_type', 'unknown'),
                'severity': data.get('blocker_severity', 'medium'),
                'impact_assessment': data.get('impact_assessment', 'Impact assessment pending'),
                'resolution_suggestions': data.get('resolution_suggestions', []),
                'escalation_required': data.get('escalation_required', False)
            }
        
        return data
    
    def _prepare_assignment_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for assignment template."""
        # Ensure assignment_data exists
        if 'assignment_data' not in data:
            data['assignment_data'] = {
                'from_assignee': data.get('from_assignee', 'Unassigned'),
                'to_assignee': data.get('to_assignee', 'Unassigned'),
                'assignment_reason': data.get('assignment_reason', 'Manual assignment')
            }
        
        return data
    
    def _prepare_comment_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for comment template."""
        # Ensure comment_data exists
        if 'comment_data' not in data:
            data['comment_data'] = {
                'author': data.get('comment_author', 'Unknown'),
                'body': data.get('comment_body', 'No comment text'),
                'created': data.get('comment_created', datetime.now().isoformat())
            }
        
        return data
    
    def _serialize_event(self, event: EnrichedEvent) -> Dict[str, Any]:
        """Serialize EnrichedEvent to dictionary."""
        return {
            'event_id': event.event_id,
            'event_type': event.event_type,
            'timestamp': event.timestamp.isoformat() if event.timestamp else None,
            'ticket_key': event.ticket_key,
            'project_key': event.project_key,
            'ticket_details': event.ticket_details,
            'classification': self._serialize_classification(event.classification) if event.classification else None,
            'context_data': event.context_data
        }
    
    def _serialize_execution_result(self, result: HookExecutionResult) -> Dict[str, Any]:
        """Serialize HookExecutionResult to dictionary."""
        return {
            'hook_id': result.hook_id,
            'execution_id': result.execution_id,
            'hook_type': result.hook_type,
            'event_id': result.event_id,
            'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
            'execution_time_ms': result.execution_time_ms,
            'notification_sent': result.notification_sent,
            'errors': result.errors,
            'metadata': result.metadata,
            'started_at': result.started_at.isoformat() if result.started_at else None,
            'completed_at': result.completed_at.isoformat() if result.completed_at else None
        }
    
    def _serialize_classification(self, classification) -> Dict[str, Any]:
        """Serialize EventClassification to dictionary."""
        return {
            'category': classification.category.value if hasattr(classification.category, 'value') else str(classification.category),
            'urgency': classification.urgency.value if hasattr(classification.urgency, 'value') else str(classification.urgency),
            'significance': classification.significance.value if hasattr(classification.significance, 'value') else str(classification.significance),
            'affected_teams': classification.affected_teams,
            'routing_hints': classification.routing_hints,
            'keywords': getattr(classification, 'keywords', [])
        }
    
    def _create_batch_message_blocks(self, batch_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create message blocks for batch hook results."""
        blocks = []
        
        # Header
        total_hooks = batch_data['total_hooks']
        successful_hooks = batch_data['successful_hooks']
        failed_hooks = batch_data['failed_hooks']
        
        header_text = f"🔄 Hook Execution Batch Results"
        blocks.append(self.create_header_block(header_text))
        
        # Summary
        summary_text = (
            f"*Execution Summary:*\n"
            f"✅ Successful: {successful_hooks}\n"
            f"❌ Failed: {failed_hooks}\n"
            f"📊 Total: {total_hooks}"
        )
        blocks.append(self.create_section_block(summary_text))
        
        # Individual results (show first 5)
        hook_results = batch_data['hook_results']
        if hook_results:
            blocks.append(self.create_divider_block())
            
            for i, result in enumerate(hook_results[:5]):
                result_block = self._create_hook_result_summary(result, i + 1)
                blocks.append(result_block)
            
            if len(hook_results) > 5:
                remaining_text = f"... and {len(hook_results) - 5} more hook results"
                blocks.append(self.create_section_block(remaining_text))
        
        return blocks
    
    def _create_hook_result_summary(self, result: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Create summary block for individual hook result."""
        hook_type = result.get('hook_type', 'Unknown')
        execution_result = result.get('execution_result', {})
        status = execution_result.get('status', 'unknown')
        
        # Status indicator
        status_indicators = {
            'success': '✅',
            'failed': '❌',
            'pending': '⏳',
            'running': '🔄'
        }
        
        indicator = status_indicators.get(status, '❓')
        
        # Create summary text
        summary_text = f"{indicator} *{index}. {hook_type}*"
        
        # Add execution time if available
        execution_time = execution_result.get('execution_time_ms')
        if execution_time:
            summary_text += f" ({execution_time:.0f}ms)"
        
        # Add error info if failed
        if status == 'failed':
            errors = execution_result.get('errors', [])
            if errors:
                summary_text += f"\n   Error: {errors[0]}"
        
        return self.create_section_block(summary_text)
    
    def register_template(self, event_type: HookEventType, template_class: Type) -> None:
        """Register a custom template for a hook event type."""
        self._template_registry[event_type] = template_class
        self.logger.info(f"Registered template {template_class.__name__} for event type {event_type.value}")
    
    def get_supported_event_types(self) -> List[HookEventType]:
        """Get list of supported hook event types."""
        return list(self._template_registry.keys())