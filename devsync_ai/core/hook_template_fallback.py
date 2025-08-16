"""
Template fallback mechanisms for Agent Hook message formatting.

This module provides robust fallback mechanisms when hook-specific templates
fail, ensuring that notifications are always delivered even if specialized
formatting encounters errors.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .message_formatter import SlackMessage, TemplateConfig
from .formatter_factory import ProcessingResult
from .agent_hooks import EnrichedEvent, HookExecutionResult


logger = logging.getLogger(__name__)


class FallbackStrategy(Enum):
    """Strategies for template fallback."""
    SIMPLE_TEXT = "simple_text"
    BASIC_BLOCKS = "basic_blocks"
    JIRA_TEMPLATE = "jira_template"
    GENERIC_HOOK = "generic_hook"
    EMERGENCY_MINIMAL = "emergency_minimal"


class FallbackTrigger(Enum):
    """Triggers that activate fallback mechanisms."""
    TEMPLATE_ERROR = "template_error"
    MISSING_DATA = "missing_data"
    FORMATTING_TIMEOUT = "formatting_timeout"
    INVALID_BLOCKS = "invalid_blocks"
    SIZE_LIMIT_EXCEEDED = "size_limit_exceeded"


@dataclass
class FallbackContext:
    """Context for fallback template selection."""
    original_error: Optional[Exception] = None
    trigger: Optional[FallbackTrigger] = None
    hook_type: Optional[str] = None
    event_type: Optional[str] = None
    data_available: Dict[str, bool] = field(default_factory=dict)
    urgency_level: str = "medium"
    team_id: Optional[str] = None
    channel_id: Optional[str] = None


class HookTemplateFallbackHandler:
    """
    Handles template fallback mechanisms for Agent Hook notifications.
    
    This class provides multiple levels of fallback to ensure that hook
    notifications are always delivered, even when specialized templates fail.
    """
    
    def __init__(self, config: Optional[TemplateConfig] = None):
        """
        Initialize the fallback handler.
        
        Args:
            config: Template configuration
        """
        self.config = config or TemplateConfig(team_id="default")
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Fallback strategy chain (ordered by preference)
        self.fallback_chain = [
            FallbackStrategy.BASIC_BLOCKS,
            FallbackStrategy.JIRA_TEMPLATE,
            FallbackStrategy.GENERIC_HOOK,
            FallbackStrategy.SIMPLE_TEXT,
            FallbackStrategy.EMERGENCY_MINIMAL
        ]
        
        # Custom fallback handlers
        self.custom_handlers: Dict[FallbackStrategy, Callable] = {}
        
        # Fallback statistics
        self.fallback_stats = {
            'total_fallbacks': 0,
            'strategy_usage': {},
            'trigger_counts': {},
            'success_rates': {}
        }
    
    def handle_formatting_failure(self, 
                                 original_data: Dict[str, Any],
                                 context: FallbackContext) -> ProcessingResult:
        """
        Handle a formatting failure by applying fallback strategies.
        
        Args:
            original_data: The original data that failed to format
            context: Context for fallback selection
            
        Returns:
            ProcessingResult with fallback formatted message
        """
        self.fallback_stats['total_fallbacks'] += 1
        
        if context.trigger:
            trigger_key = context.trigger.value
            self.fallback_stats['trigger_counts'][trigger_key] = (
                self.fallback_stats['trigger_counts'].get(trigger_key, 0) + 1
            )
        
        self.logger.warning(
            f"Applying fallback for hook {context.hook_type}, "
            f"trigger: {context.trigger.value if context.trigger else 'unknown'}"
        )
        
        # Try each fallback strategy in order
        for strategy in self.fallback_chain:
            try:
                result = self._apply_fallback_strategy(strategy, original_data, context)
                
                if result.success:
                    self._update_fallback_stats(strategy, True)
                    self.logger.info(f"Fallback successful using strategy: {strategy.value}")
                    
                    # Add fallback metadata
                    if result.message:
                        result.message.metadata.update({
                            'fallback_used': True,
                            'fallback_strategy': strategy.value,
                            'original_error': str(context.original_error) if context.original_error else None,
                            'fallback_trigger': context.trigger.value if context.trigger else None
                        })
                    
                    return result
                
                self.logger.debug(f"Fallback strategy {strategy.value} failed: {result.error}")
                
            except Exception as e:
                self.logger.warning(f"Fallback strategy {strategy.value} raised exception: {e}")
                self._update_fallback_stats(strategy, False)
        
        # All fallback strategies failed
        self.logger.error("All fallback strategies failed")
        return ProcessingResult(
            success=False,
            error="All fallback strategies failed",
            formatter_used="HookTemplateFallbackHandler"
        )
    
    def _apply_fallback_strategy(self, 
                               strategy: FallbackStrategy,
                               data: Dict[str, Any],
                               context: FallbackContext) -> ProcessingResult:
        """Apply a specific fallback strategy."""
        
        # Check for custom handler first
        if strategy in self.custom_handlers:
            return self.custom_handlers[strategy](data, context)
        
        # Apply built-in strategies
        if strategy == FallbackStrategy.BASIC_BLOCKS:
            return self._create_basic_blocks_fallback(data, context)
        elif strategy == FallbackStrategy.JIRA_TEMPLATE:
            return self._create_jira_template_fallback(data, context)
        elif strategy == FallbackStrategy.GENERIC_HOOK:
            return self._create_generic_hook_fallback(data, context)
        elif strategy == FallbackStrategy.SIMPLE_TEXT:
            return self._create_simple_text_fallback(data, context)
        elif strategy == FallbackStrategy.EMERGENCY_MINIMAL:
            return self._create_emergency_minimal_fallback(data, context)
        
        return ProcessingResult(
            success=False,
            error=f"Unknown fallback strategy: {strategy.value}",
            formatter_used="HookTemplateFallbackHandler"
        )
    
    def _create_basic_blocks_fallback(self, 
                                    data: Dict[str, Any],
                                    context: FallbackContext) -> ProcessingResult:
        """Create a basic blocks fallback message."""
        try:
            blocks = []
            
            # Header
            hook_type = context.hook_type or "Unknown Hook"
            title = f"🔄 {hook_type} Notification"
            
            blocks.append({
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title,
                    "emoji": True
                }
            })
            
            # Extract key information
            info_parts = []
            
            # Event information
            event = data.get('event', {})
            if event:
                ticket_key = event.get('ticket_key', 'UNKNOWN')
                info_parts.append(f"*Ticket:* {ticket_key}")
                
                event_type = event.get('event_type', 'unknown')
                info_parts.append(f"*Event:* {event_type}")
            
            # Execution result information
            execution_result = data.get('execution_result', {})
            if execution_result:
                status = execution_result.get('status', 'unknown')
                info_parts.append(f"*Status:* {status}")
                
                execution_time = execution_result.get('execution_time_ms')
                if execution_time:
                    info_parts.append(f"*Duration:* {execution_time:.0f}ms")
            
            if info_parts:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "\n".join(info_parts)
                    }
                })
            
            # Add error context if available
            if context.original_error:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"⚠️ Fallback formatting used due to: {str(context.original_error)[:100]}"
                        }
                    ]
                })
            
            # Create fallback text
            fallback_text = f"{hook_type} notification"
            if event:
                ticket_key = event.get('ticket_key')
                if ticket_key:
                    fallback_text += f" for {ticket_key}"
            
            message = SlackMessage(
                blocks=blocks,
                text=fallback_text,
                metadata={
                    'fallback_strategy': 'basic_blocks',
                    'hook_type': context.hook_type
                }
            )
            
            return ProcessingResult(
                success=True,
                message=message,
                formatter_used="BasicBlocksFallback"
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error=str(e),
                formatter_used="BasicBlocksFallback"
            )
    
    def _create_jira_template_fallback(self, 
                                     data: Dict[str, Any],
                                     context: FallbackContext) -> ProcessingResult:
        """Create a fallback using standard JIRA templates."""
        try:
            # Try to use existing JIRA formatter
            from ..formatters.jira_message_formatter import JIRAMessageFormatter
            
            # Extract ticket data
            event = data.get('event', {})
            ticket_details = event.get('ticket_details', {})
            
            if not ticket_details:
                # Can't use JIRA template without ticket data
                return ProcessingResult(
                    success=False,
                    error="No ticket data available for JIRA template fallback",
                    formatter_used="JIRATemplateFallback"
                )
            
            # Prepare JIRA formatter data
            jira_data = {
                'ticket': ticket_details,
                'change_type': self._determine_change_type(data, context)
            }
            
            # Add change-specific data
            execution_result = data.get('execution_result', {})
            if execution_result:
                metadata = execution_result.get('metadata', {})
                
                # Add transition data if available
                if 'transition_analysis' in metadata:
                    transition = metadata['transition_analysis']
                    jira_data['from_status'] = transition.get('from_status')
                    jira_data['to_status'] = transition.get('to_status')
                
                # Add assignment data if available
                if 'assignment_data' in metadata:
                    assignment = metadata['assignment_data']
                    jira_data['from_assignee'] = assignment.get('from_assignee')
                    jira_data['to_assignee'] = assignment.get('to_assignee')
            
            # Create JIRA formatter and format message
            jira_formatter = JIRAMessageFormatter(config=self.config)
            message = jira_formatter.format_message(jira_data)
            
            return ProcessingResult(
                success=True,
                message=message,
                formatter_used="JIRATemplateFallback"
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error=str(e),
                formatter_used="JIRATemplateFallback"
            )
    
    def _create_generic_hook_fallback(self, 
                                    data: Dict[str, Any],
                                    context: FallbackContext) -> ProcessingResult:
        """Create a generic hook notification fallback."""
        try:
            blocks = []
            
            # Header with hook type
            hook_type = context.hook_type or "Agent Hook"
            urgency_indicator = self._get_urgency_indicator(context.urgency_level)
            
            title = f"{urgency_indicator} {hook_type} Executed"
            
            blocks.append({
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title,
                    "emoji": True
                }
            })
            
            # Execution summary
            execution_result = data.get('execution_result', {})
            if execution_result:
                status = execution_result.get('status', 'unknown')
                execution_time = execution_result.get('execution_time_ms', 0)
                
                status_emoji = {
                    'success': '✅',
                    'failed': '❌',
                    'pending': '⏳',
                    'running': '🔄'
                }.get(status, '❓')
                
                summary_text = (
                    f"*Execution Summary:*\n"
                    f"{status_emoji} Status: {status.title()}\n"
                    f"⏱️ Duration: {execution_time:.0f}ms"
                )
                
                # Add error information if failed
                errors = execution_result.get('errors', [])
                if errors:
                    summary_text += f"\n❌ Error: {errors[0]}"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": summary_text
                    }
                })
            
            # Event context
            event = data.get('event', {})
            if event:
                context_parts = []
                
                ticket_key = event.get('ticket_key')
                if ticket_key:
                    context_parts.append(f"🎫 Ticket: {ticket_key}")
                
                event_type = event.get('event_type')
                if event_type:
                    context_parts.append(f"📋 Event: {event_type}")
                
                timestamp = event.get('timestamp')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%H:%M:%S')
                        context_parts.append(f"🕐 Time: {time_str}")
                    except (ValueError, AttributeError):
                        pass
                
                if context_parts:
                    blocks.append({
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": " | ".join(context_parts)
                            }
                        ]
                    })
            
            # Create fallback text
            fallback_text = f"{hook_type} executed"
            if execution_result:
                status = execution_result.get('status', 'unknown')
                fallback_text += f" - {status}"
            
            message = SlackMessage(
                blocks=blocks,
                text=fallback_text,
                metadata={
                    'fallback_strategy': 'generic_hook',
                    'hook_type': context.hook_type
                }
            )
            
            return ProcessingResult(
                success=True,
                message=message,
                formatter_used="GenericHookFallback"
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error=str(e),
                formatter_used="GenericHookFallback"
            )
    
    def _create_simple_text_fallback(self, 
                                   data: Dict[str, Any],
                                   context: FallbackContext) -> ProcessingResult:
        """Create a simple text-only fallback message."""
        try:
            # Build simple text message
            text_parts = []
            
            # Hook type
            hook_type = context.hook_type or "Agent Hook"
            text_parts.append(f"🔄 {hook_type} Notification")
            
            # Event information
            event = data.get('event', {})
            if event:
                ticket_key = event.get('ticket_key')
                if ticket_key:
                    text_parts.append(f"Ticket: {ticket_key}")
                
                event_type = event.get('event_type')
                if event_type:
                    text_parts.append(f"Event: {event_type}")
            
            # Execution result
            execution_result = data.get('execution_result', {})
            if execution_result:
                status = execution_result.get('status', 'unknown')
                text_parts.append(f"Status: {status}")
            
            # Join parts
            message_text = "\n".join(text_parts)
            
            # Create simple block structure
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message_text
                    }
                }
            ]
            
            message = SlackMessage(
                blocks=blocks,
                text=message_text,
                metadata={
                    'fallback_strategy': 'simple_text',
                    'hook_type': context.hook_type
                }
            )
            
            return ProcessingResult(
                success=True,
                message=message,
                formatter_used="SimpleTextFallback"
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error=str(e),
                formatter_used="SimpleTextFallback"
            )
    
    def _create_emergency_minimal_fallback(self, 
                                         data: Dict[str, Any],
                                         context: FallbackContext) -> ProcessingResult:
        """Create an emergency minimal fallback message."""
        try:
            # Absolute minimal message
            hook_type = context.hook_type or "Hook"
            message_text = f"⚠️ {hook_type} notification (fallback formatting)"
            
            # Single block with minimal information
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": message_text,
                        "emoji": True
                    }
                }
            ]
            
            message = SlackMessage(
                blocks=blocks,
                text=message_text,
                metadata={
                    'fallback_strategy': 'emergency_minimal',
                    'hook_type': context.hook_type,
                    'emergency_fallback': True
                }
            )
            
            return ProcessingResult(
                success=True,
                message=message,
                formatter_used="EmergencyMinimalFallback"
            )
            
        except Exception as e:
            # This should never fail, but just in case
            return ProcessingResult(
                success=False,
                error=str(e),
                formatter_used="EmergencyMinimalFallback"
            )
    
    def _determine_change_type(self, data: Dict[str, Any], context: FallbackContext) -> str:
        """Determine the change type for JIRA template fallback."""
        execution_result = data.get('execution_result', {})
        if execution_result:
            metadata = execution_result.get('metadata', {})
            
            if 'transition_analysis' in metadata:
                return 'status_change'
            elif 'assignment_data' in metadata:
                return 'assignment_change'
            elif 'comment_data' in metadata:
                return 'comment_added'
            elif 'blocker_analysis' in metadata:
                return 'blocker_detected'
        
        # Fallback based on hook type
        hook_type = context.hook_type or ""
        if 'status' in hook_type.lower():
            return 'status_change'
        elif 'assignment' in hook_type.lower():
            return 'assignment_change'
        elif 'comment' in hook_type.lower():
            return 'comment_added'
        elif 'blocker' in hook_type.lower():
            return 'blocker_detected'
        
        return 'updated'
    
    def _get_urgency_indicator(self, urgency_level: str) -> str:
        """Get urgency indicator emoji."""
        indicators = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'critical': '🔴'
        }
        return indicators.get(urgency_level.lower(), '🟡')
    
    def _update_fallback_stats(self, strategy: FallbackStrategy, success: bool) -> None:
        """Update fallback statistics."""
        strategy_key = strategy.value
        
        if strategy_key not in self.fallback_stats['strategy_usage']:
            self.fallback_stats['strategy_usage'][strategy_key] = 0
        
        self.fallback_stats['strategy_usage'][strategy_key] += 1
        
        if strategy_key not in self.fallback_stats['success_rates']:
            self.fallback_stats['success_rates'][strategy_key] = {'success': 0, 'total': 0}
        
        self.fallback_stats['success_rates'][strategy_key]['total'] += 1
        if success:
            self.fallback_stats['success_rates'][strategy_key]['success'] += 1
    
    def register_custom_fallback(self, 
                                strategy: FallbackStrategy,
                                handler: Callable[[Dict[str, Any], FallbackContext], ProcessingResult]) -> None:
        """Register a custom fallback handler."""
        self.custom_handlers[strategy] = handler
        self.logger.info(f"Registered custom fallback handler for strategy: {strategy.value}")
    
    def get_fallback_statistics(self) -> Dict[str, Any]:
        """Get fallback usage statistics."""
        stats = self.fallback_stats.copy()
        
        # Calculate success rates
        for strategy, rates in stats['success_rates'].items():
            if rates['total'] > 0:
                rates['rate'] = rates['success'] / rates['total']
            else:
                rates['rate'] = 0.0
        
        return stats
    
    def reset_statistics(self) -> None:
        """Reset fallback statistics."""
        self.fallback_stats = {
            'total_fallbacks': 0,
            'strategy_usage': {},
            'trigger_counts': {},
            'success_rates': {}
        }
        self.logger.info("Fallback statistics reset")


# Global fallback handler instance
_fallback_handler: Optional[HookTemplateFallbackHandler] = None


def get_fallback_handler(config: Optional[TemplateConfig] = None) -> HookTemplateFallbackHandler:
    """
    Get the global fallback handler instance.
    
    Args:
        config: Optional template configuration
        
    Returns:
        HookTemplateFallbackHandler instance
    """
    global _fallback_handler
    
    if _fallback_handler is None:
        _fallback_handler = HookTemplateFallbackHandler(config)
    
    return _fallback_handler