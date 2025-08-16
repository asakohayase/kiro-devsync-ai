"""
Hook Template Integration for Agent Hooks.

This module provides the integration layer between Agent Hooks and the existing
SlackMessageFormatterFactory, enabling hook-specific message formatting while
maintaining compatibility with the existing template system.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from .formatter_factory import SlackMessageFormatterFactory, MessageType, FormatterOptions, ProcessingResult
from .message_formatter import SlackMessage, TemplateConfig
from .agent_hooks import EnrichedEvent, HookExecutionResult
from ..formatters.hook_message_formatter import HookMessageFormatter, HookMessageType


logger = logging.getLogger(__name__)


class HookTemplateSelectionStrategy(Enum):
    """Strategies for selecting hook templates."""
    EVENT_TYPE_BASED = "event_type_based"
    HOOK_TYPE_BASED = "hook_type_based"
    DYNAMIC_CLASSIFICATION = "dynamic_classification"
    FALLBACK_CHAIN = "fallback_chain"


@dataclass
class HookFormattingContext:
    """Context for hook message formatting."""
    hook_type: str
    event: Optional[EnrichedEvent] = None
    execution_result: Optional[HookExecutionResult] = None
    additional_context: Optional[Dict[str, Any]] = None
    urgency_override: Optional[str] = None
    channel_context: Optional[str] = None
    team_context: Optional[str] = None


class HookTemplateIntegrator:
    """
    Integrates Agent Hook formatting with the existing template system.
    
    This class provides seamless integration between Agent Hooks and the
    SlackMessageFormatterFactory, enabling hook-specific templates while
    maintaining compatibility with existing formatting infrastructure.
    """
    
    def __init__(self, formatter_factory: SlackMessageFormatterFactory):
        """
        Initialize the hook template integrator.
        
        Args:
            formatter_factory: The main SlackMessageFormatterFactory instance
        """
        self.formatter_factory = formatter_factory
        self.hook_formatter = HookMessageFormatter()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Template selection strategy
        self.selection_strategy = HookTemplateSelectionStrategy.DYNAMIC_CLASSIFICATION
        
        # Fallback configuration
        self.enable_fallback = True
        self.fallback_to_jira_templates = True
        
        # Register hook message types with the factory
        self._register_hook_message_types()
    
    def format_hook_message(self, 
                          formatting_context: HookFormattingContext,
                          options: Optional[FormatterOptions] = None) -> ProcessingResult:
        """
        Format a hook message using the integrated template system.
        
        Args:
            formatting_context: Context for hook message formatting
            options: Formatting options
            
        Returns:
            ProcessingResult with formatted message or error information
        """
        try:
            self.logger.info(f"Formatting hook message for {formatting_context.hook_type}")
            
            # Determine message type
            message_type = self._determine_hook_message_type(formatting_context)
            
            # Prepare data for formatting
            formatting_data = self._prepare_formatting_data(formatting_context)
            
            # Try hook-specific formatting first
            try:
                hook_result = self._format_with_hook_templates(formatting_data, options)
                if hook_result.success:
                    return hook_result
                
                self.logger.warning(f"Hook template formatting failed: {hook_result.error}")
                
            except Exception as e:
                self.logger.warning(f"Hook template formatting error: {e}")
            
            # Fallback to standard templates if enabled
            if self.enable_fallback:
                return self._format_with_fallback(message_type, formatting_data, options)
            
            # Return error result
            return ProcessingResult(
                success=False,
                error="Hook template formatting failed and fallback disabled",
                formatter_used="HookTemplateIntegrator"
            )
            
        except Exception as e:
            self.logger.error(f"Hook message formatting failed: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                error=str(e),
                formatter_used="HookTemplateIntegrator"
            )
    
    def format_hook_execution_result(self,
                                   hook_type: str,
                                   event: EnrichedEvent,
                                   execution_result: HookExecutionResult,
                                   options: Optional[FormatterOptions] = None) -> ProcessingResult:
        """
        Format a hook execution result.
        
        Args:
            hook_type: Type of hook that executed
            event: The enriched event
            execution_result: Result of hook execution
            options: Formatting options
            
        Returns:
            ProcessingResult with formatted message
        """
        context = HookFormattingContext(
            hook_type=hook_type,
            event=event,
            execution_result=execution_result
        )
        
        return self.format_hook_message(context, options)
    
    def format_batch_hook_results(self,
                                hook_results: List[Dict[str, Any]],
                                batch_context: Optional[Dict[str, Any]] = None,
                                options: Optional[FormatterOptions] = None) -> ProcessingResult:
        """
        Format multiple hook execution results as a batch.
        
        Args:
            hook_results: List of hook execution results
            batch_context: Context for the batch operation
            options: Formatting options
            
        Returns:
            ProcessingResult with batch formatted message
        """
        try:
            # Use hook formatter for batch processing
            message = self.hook_formatter.format_batch_hook_results(
                hook_results, batch_context
            )
            
            return ProcessingResult(
                success=True,
                message=message,
                formatter_used="HookMessageFormatter",
                processing_time_ms=0.0  # Would be calculated in real implementation
            )
            
        except Exception as e:
            self.logger.error(f"Batch hook formatting failed: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                error=str(e),
                formatter_used="HookTemplateIntegrator"
            )
    
    def register_hook_template_fallback(self, 
                                      hook_type: str, 
                                      fallback_message_type: MessageType) -> None:
        """
        Register a fallback message type for a specific hook type.
        
        Args:
            hook_type: The hook type to configure fallback for
            fallback_message_type: The message type to fall back to
        """
        # This would be implemented to configure fallback mappings
        self.logger.info(f"Registered fallback for {hook_type} to {fallback_message_type.value}")
    
    def _register_hook_message_types(self) -> None:
        """Register hook message types with the formatter factory."""
        try:
            # Register hook formatter as a custom formatter
            self.formatter_factory.register_custom_formatter(
                "hook_status_change", 
                HookMessageFormatter
            )
            self.formatter_factory.register_custom_formatter(
                "hook_blocker_detected", 
                HookMessageFormatter
            )
            self.formatter_factory.register_custom_formatter(
                "hook_assignment", 
                HookMessageFormatter
            )
            self.formatter_factory.register_custom_formatter(
                "hook_comment", 
                HookMessageFormatter
            )
            
            self.logger.info("Registered hook message types with formatter factory")
            
        except Exception as e:
            self.logger.warning(f"Failed to register hook message types: {e}")
    
    def _determine_hook_message_type(self, context: HookFormattingContext) -> str:
        """Determine the appropriate message type for the hook context."""
        hook_type_lower = context.hook_type.lower()
        
        # Map hook types to message types
        hook_message_mapping = {
            'statuschangehook': 'hook_status_change',
            'status_change_hook': 'hook_status_change',
            'blockerhook': 'hook_blocker_detected',
            'blocker_hook': 'hook_blocker_detected',
            'assignmenthook': 'hook_assignment',
            'assignment_hook': 'hook_assignment',
            'commenthook': 'hook_comment',
            'comment_hook': 'hook_comment',
        }
        
        # Check execution result for more specific type
        if context.execution_result:
            metadata = context.execution_result.metadata
            
            # Check for blocker resolution
            if metadata.get('blocker_resolved'):
                return 'hook_blocker_resolved'
            
            # Check for specific transition types
            transition_type = metadata.get('transition_type')
            if transition_type == 'blocked':
                return 'hook_blocker_detected'
        
        # Check event classification
        if context.event and context.event.classification:
            category = context.event.classification.category
            category_value = category.value if hasattr(category, 'value') else str(category)
            
            category_mapping = {
                'status_change': 'hook_status_change',
                'assignment': 'hook_assignment',
                'comment': 'hook_comment',
                'blocker': 'hook_blocker_detected',
            }
            
            if category_value in category_mapping:
                return category_mapping[category_value]
        
        # Fallback to hook type mapping
        return hook_message_mapping.get(hook_type_lower, 'hook_status_change')
    
    def _prepare_formatting_data(self, context: HookFormattingContext) -> Dict[str, Any]:
        """Prepare data for message formatting."""
        data = {
            'hook_type': context.hook_type,
            'additional_context': context.additional_context or {}
        }
        
        # Add event data
        if context.event:
            data['event'] = self._serialize_event_for_formatting(context.event)
        
        # Add execution result data
        if context.execution_result:
            data['execution_result'] = self._serialize_execution_result_for_formatting(
                context.execution_result
            )
        
        # Add context overrides
        if context.urgency_override:
            data['urgency_override'] = context.urgency_override
        
        if context.channel_context:
            data['channel_context'] = context.channel_context
        
        if context.team_context:
            data['team_context'] = context.team_context
        
        return data
    
    def _format_with_hook_templates(self, 
                                  data: Dict[str, Any], 
                                  options: Optional[FormatterOptions]) -> ProcessingResult:
        """Format message using hook-specific templates."""
        try:
            # Configure hook formatter with options
            if options:
                config = self._create_template_config_from_options(options)
                self.hook_formatter.config = config
            
            # Format message
            message = self.hook_formatter.format_message(data)
            
            return ProcessingResult(
                success=True,
                message=message,
                formatter_used="HookMessageFormatter",
                processing_time_ms=0.0  # Would be calculated in real implementation
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error=str(e),
                formatter_used="HookMessageFormatter"
            )
    
    def _format_with_fallback(self, 
                            message_type: str,
                            data: Dict[str, Any], 
                            options: Optional[FormatterOptions]) -> ProcessingResult:
        """Format message using fallback templates."""
        try:
            # Map hook message types to standard message types
            fallback_mapping = {
                'hook_status_change': MessageType.JIRA_UPDATE,
                'hook_blocker_detected': MessageType.JIRA_UPDATE,
                'hook_assignment': MessageType.JIRA_UPDATE,
                'hook_comment': MessageType.JIRA_UPDATE,
            }
            
            fallback_type = fallback_mapping.get(message_type, MessageType.JIRA_UPDATE)
            
            # Prepare data for standard formatter
            fallback_data = self._prepare_fallback_data(data)
            
            # Use standard formatter factory
            return self.formatter_factory.format_message(
                message_type=fallback_type,
                data=fallback_data,
                options=options
            )
            
        except Exception as e:
            self.logger.error(f"Fallback formatting failed: {e}")
            return ProcessingResult(
                success=False,
                error=f"Both hook and fallback formatting failed: {e}",
                formatter_used="fallback"
            )
    
    def _prepare_fallback_data(self, hook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare hook data for fallback formatting."""
        fallback_data = {}
        
        # Extract event data
        event = hook_data.get('event', {})
        if event:
            ticket_details = event.get('ticket_details', {})
            if ticket_details:
                fallback_data['ticket'] = ticket_details
        
        # Extract execution result metadata
        execution_result = hook_data.get('execution_result', {})
        if execution_result:
            metadata = execution_result.get('metadata', {})
            
            # Map hook-specific data to standard JIRA data
            if 'transition_analysis' in metadata:
                transition = metadata['transition_analysis']
                fallback_data['change_type'] = 'status_change'
                fallback_data['from_status'] = transition.get('from_status')
                fallback_data['to_status'] = transition.get('to_status')
            
            if 'assignment_data' in metadata:
                assignment = metadata['assignment_data']
                fallback_data['change_type'] = 'assignment_change'
                fallback_data['from_assignee'] = assignment.get('from_assignee')
                fallback_data['to_assignee'] = assignment.get('to_assignee')
        
        # Add additional context
        additional_context = hook_data.get('additional_context', {})
        fallback_data.update(additional_context)
        
        return fallback_data
    
    def _serialize_event_for_formatting(self, event: EnrichedEvent) -> Dict[str, Any]:
        """Serialize event for formatting."""
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
    
    def _serialize_execution_result_for_formatting(self, result: HookExecutionResult) -> Dict[str, Any]:
        """Serialize execution result for formatting."""
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
        """Serialize event classification."""
        return {
            'category': classification.category.value if hasattr(classification.category, 'value') else str(classification.category),
            'urgency': classification.urgency.value if hasattr(classification.urgency, 'value') else str(classification.urgency),
            'significance': classification.significance.value if hasattr(classification.significance, 'value') else str(classification.significance),
            'affected_teams': classification.affected_teams,
            'routing_hints': classification.routing_hints,
            'keywords': getattr(classification, 'keywords', [])
        }
    
    def _create_template_config_from_options(self, options: FormatterOptions) -> TemplateConfig:
        """Create template config from formatter options."""
        return TemplateConfig(
            team_id="default",  # Would be extracted from options in real implementation
            interactive_elements=options.interactive,
            accessibility_mode=options.accessibility_mode,
            threading_enabled=options.threading_enabled,
            branding=options.custom_config.get('branding', {}),
            emoji_set=options.custom_config.get('emoji_set', {}),
            color_scheme=options.custom_config.get('color_scheme', {})
        )
    
    def get_formatting_statistics(self) -> Dict[str, Any]:
        """Get formatting statistics for monitoring."""
        return {
            'hook_formatter_available': self.hook_formatter is not None,
            'fallback_enabled': self.enable_fallback,
            'selection_strategy': self.selection_strategy.value,
            'supported_hook_types': self.hook_formatter.get_supported_event_types() if self.hook_formatter else []
        }


# Global integrator instance
_hook_template_integrator: Optional[HookTemplateIntegrator] = None


def get_hook_template_integrator(formatter_factory: Optional[SlackMessageFormatterFactory] = None) -> HookTemplateIntegrator:
    """
    Get the global hook template integrator instance.
    
    Args:
        formatter_factory: Optional formatter factory to use
        
    Returns:
        HookTemplateIntegrator instance
    """
    global _hook_template_integrator
    
    if _hook_template_integrator is None:
        if formatter_factory is None:
            # Create a default formatter factory if none provided
            formatter_factory = SlackMessageFormatterFactory()
        
        _hook_template_integrator = HookTemplateIntegrator(formatter_factory)
    
    return _hook_template_integrator


def format_hook_message(formatting_context: HookFormattingContext,
                       options: Optional[FormatterOptions] = None) -> ProcessingResult:
    """
    Convenience function to format a hook message.
    
    Args:
        formatting_context: Context for hook message formatting
        options: Formatting options
        
    Returns:
        ProcessingResult with formatted message
    """
    integrator = get_hook_template_integrator()
    return integrator.format_hook_message(formatting_context, options)