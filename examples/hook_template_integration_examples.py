"""
Examples demonstrating hook template integration with the existing template system.

This module shows how Agent Hooks integrate with the SlackMessageFormatterFactory
to provide specialized formatting while maintaining compatibility with existing templates.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from devsync_ai.core.hook_template_integration import (
    HookTemplateIntegrator,
    HookFormattingContext,
    get_hook_template_integrator,
    format_hook_message
)
from devsync_ai.core.hook_template_fallback import (
    HookTemplateFallbackHandler,
    FallbackContext,
    FallbackStrategy,
    FallbackTrigger
)
from devsync_ai.core.formatter_factory import (
    SlackMessageFormatterFactory,
    FormatterOptions
)
from devsync_ai.core.agent_hooks import (
    EnrichedEvent,
    HookExecutionResult,
    HookStatus,
    EventCategory,
    UrgencyLevel,
    EventClassification
)
from devsync_ai.formatters.hook_message_formatter import HookMessageFormatter


def create_sample_event() -> EnrichedEvent:
    """Create a sample enriched event for examples."""
    classification = EventClassification(
        category=EventCategory.STATUS_CHANGE,
        urgency=UrgencyLevel.HIGH,
        significance=UrgencyLevel.HIGH,
        affected_teams=['dev-team', 'qa-team'],
        routing_hints={'channel': '#dev-updates'},
        keywords=['blocked', 'urgent']
    )
    
    return EnrichedEvent(
        event_id="example-event-123",
        event_type="jira:issue_updated",
        timestamp=datetime.now(timezone.utc),
        jira_event_data={
            'issue': {
                'key': 'DEV-456',
                'fields': {
                    'status': {'name': 'Blocked'},
                    'priority': {'name': 'High'}
                }
            }
        },
        ticket_key="DEV-456",
        project_key="DEV",
        raw_payload={},
        ticket_details={
            'key': 'DEV-456',
            'summary': 'Critical bug in payment processing',
            'status': 'Blocked',
            'priority': 'High',
            'assignee': 'jane.smith',
            'reporter': 'john.doe',
            'story_points': 8,
            'components': ['Payment', 'API'],
            'labels': ['critical', 'security']
        },
        classification=classification,
        context_data={
            'processor_data': {
                'field_changes': [
                    type('FieldChange', (), {
                        'field_name': 'status',
                        'old_value': 'In Progress',
                        'new_value': 'Blocked'
                    })()
                ],
                'is_blocked': True
            },
            'sprint_context': {
                'sprint_name': 'Sprint 23',
                'days_remaining': 3
            },
            'assignee_info': {
                'assignee_name': 'jane.smith'
            }
        }
    )


def create_sample_execution_result() -> HookExecutionResult:
    """Create a sample hook execution result."""
    return HookExecutionResult(
        hook_id="blocker-hook-1",
        execution_id="exec-456",
        hook_type="BlockerHook",
        event_id="example-event-123",
        status=HookStatus.SUCCESS,
        execution_time_ms=250.0,
        notification_sent=True,
        metadata={
            'transition_type': 'blocked',
            'blocker_severity': 'high',
            'escalation_required': True,
            'sprint_impact': True,
            'blocker_analysis': {
                'blocker_type': 'dependency',
                'severity': 'high',
                'impact_assessment': 'Critical payment feature blocked, affecting sprint delivery',
                'resolution_suggestions': [
                    'Contact external API team for status update',
                    'Explore alternative payment provider integration',
                    'Escalate to technical lead for immediate attention'
                ],
                'escalation_required': True
            },
            'sprint_metrics': {
                'sprint_name': 'Sprint 23',
                'completion_percentage': 75.0,
                'at_risk': True,
                'days_remaining': 3
            }
        }
    )


def example_basic_hook_formatting():
    """Example of basic hook message formatting."""
    print("=== Basic Hook Message Formatting ===")
    
    # Create sample data
    event = create_sample_event()
    execution_result = create_sample_execution_result()
    
    # Create formatting context
    context = HookFormattingContext(
        hook_type="BlockerHook",
        event=event,
        execution_result=execution_result,
        urgency_override="critical",
        team_context="dev-team"
    )
    
    # Format message using the integrator
    integrator = get_hook_template_integrator()
    result = integrator.format_hook_message(context)
    
    if result.success:
        print("✅ Hook message formatted successfully!")
        print(f"Formatter used: {result.formatter_used}")
        print(f"Processing time: {result.processing_time_ms:.2f}ms")
        print(f"Message blocks: {len(result.message.blocks)}")
        print(f"Fallback text: {result.message.text}")
        
        # Print first block as example
        if result.message.blocks:
            print(f"First block: {result.message.blocks[0]}")
    else:
        print(f"❌ Formatting failed: {result.error}")


def example_hook_formatter_direct():
    """Example of using HookMessageFormatter directly."""
    print("\n=== Direct Hook Formatter Usage ===")
    
    # Create hook formatter
    formatter = HookMessageFormatter()
    
    # Prepare hook data
    hook_data = {
        'hook_type': 'StatusChangeHook',
        'event': {
            'event_id': 'direct-example-123',
            'ticket_key': 'DEV-789',
            'event_type': 'jira:issue_updated',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'ticket_details': {
                'key': 'DEV-789',
                'summary': 'Implement user authentication',
                'status': 'In Progress',
                'priority': 'Medium',
                'assignee': 'alice.johnson'
            },
            'classification': {
                'category': 'status_change',
                'urgency': 'medium',
                'significance': 'moderate'
            }
        },
        'execution_result': {
            'status': 'success',
            'execution_time_ms': 120.0,
            'metadata': {
                'transition_analysis': {
                    'type': 'forward',
                    'from_status': 'To Do',
                    'to_status': 'In Progress',
                    'urgency': 'medium',
                    'is_significant': True
                }
            }
        }
    }
    
    try:
        message = formatter.format_message(hook_data)
        print("✅ Direct formatting successful!")
        print(f"Message metadata: {message.metadata}")
        print(f"Number of blocks: {len(message.blocks)}")
    except Exception as e:
        print(f"❌ Direct formatting failed: {e}")


def example_batch_hook_formatting():
    """Example of batch hook results formatting."""
    print("\n=== Batch Hook Results Formatting ===")
    
    # Create multiple hook results
    hook_results = [
        {
            'hook_type': 'StatusChangeHook',
            'event': {'ticket_key': 'DEV-100'},
            'execution_result': {
                'status': 'success',
                'execution_time_ms': 95.0,
                'metadata': {'transition_type': 'completed'}
            }
        },
        {
            'hook_type': 'AssignmentHook',
            'event': {'ticket_key': 'DEV-101'},
            'execution_result': {
                'status': 'success',
                'execution_time_ms': 80.0,
                'metadata': {'assignment_type': 'new_assignment'}
            }
        },
        {
            'hook_type': 'BlockerHook',
            'event': {'ticket_key': 'DEV-102'},
            'execution_result': {
                'status': 'failed',
                'execution_time_ms': 200.0,
                'errors': ['Failed to detect blocker pattern'],
                'metadata': {'blocker_type': 'unknown'}
            }
        }
    ]
    
    batch_context = {
        'batch_id': 'batch-456',
        'triggered_by': 'webhook_batch',
        'team_id': 'dev-team'
    }
    
    # Format batch results
    integrator = get_hook_template_integrator()
    result = integrator.format_batch_hook_results(hook_results, batch_context)
    
    if result.success:
        print("✅ Batch formatting successful!")
        print(f"Total hooks: {result.message.metadata.get('total_hooks')}")
        print(f"Successful: {result.message.metadata.get('successful_hooks')}")
        print(f"Failed: {result.message.metadata.get('failed_hooks')}")
    else:
        print(f"❌ Batch formatting failed: {result.error}")


def example_fallback_mechanisms():
    """Example of template fallback mechanisms."""
    print("\n=== Template Fallback Mechanisms ===")
    
    # Create fallback handler
    fallback_handler = HookTemplateFallbackHandler()
    
    # Simulate formatting failure
    original_data = {
        'hook_type': 'CustomHook',
        'event': {
            'ticket_key': 'DEV-999',
            'ticket_details': {
                'key': 'DEV-999',
                'summary': 'Test fallback scenario'
            }
        },
        'execution_result': {
            'status': 'success',
            'execution_time_ms': 150.0
        }
    }
    
    fallback_context = FallbackContext(
        original_error=Exception("Custom template not found"),
        trigger=FallbackTrigger.TEMPLATE_ERROR,
        hook_type="CustomHook",
        urgency_level="high"
    )
    
    # Handle fallback
    result = fallback_handler.handle_formatting_failure(original_data, fallback_context)
    
    if result.success:
        print("✅ Fallback formatting successful!")
        print(f"Fallback strategy used: {result.message.metadata.get('fallback_strategy')}")
        print(f"Formatter used: {result.formatter_used}")
        
        # Show fallback statistics
        stats = fallback_handler.get_fallback_statistics()
        print(f"Total fallbacks: {stats['total_fallbacks']}")
        print(f"Strategy usage: {stats['strategy_usage']}")
    else:
        print(f"❌ All fallback strategies failed: {result.error}")


def example_custom_fallback_handler():
    """Example of registering custom fallback handlers."""
    print("\n=== Custom Fallback Handler ===")
    
    def custom_emergency_fallback(data: Dict[str, Any], context) -> Any:
        """Custom emergency fallback that creates a minimal alert."""
        from devsync_ai.core.formatter_factory import ProcessingResult
        from devsync_ai.core.message_formatter import SlackMessage
        
        hook_type = context.hook_type or "Unknown Hook"
        
        # Create ultra-minimal message
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {hook_type} Alert - Custom Emergency Fallback",
                    "emoji": True
                }
            }
        ]
        
        message = SlackMessage(
            blocks=blocks,
            text=f"{hook_type} Alert",
            metadata={
                'custom_fallback': True,
                'emergency_mode': True
            }
        )
        
        return ProcessingResult(
            success=True,
            message=message,
            formatter_used="CustomEmergencyFallback"
        )
    
    # Register custom fallback
    fallback_handler = HookTemplateFallbackHandler()
    fallback_handler.register_custom_fallback(
        FallbackStrategy.EMERGENCY_MINIMAL,
        custom_emergency_fallback
    )
    
    # Test custom fallback
    test_data = {'hook_type': 'TestHook'}
    test_context = FallbackContext(hook_type="TestHook")
    
    result = fallback_handler._apply_fallback_strategy(
        FallbackStrategy.EMERGENCY_MINIMAL,
        test_data,
        test_context
    )
    
    if result.success:
        print("✅ Custom fallback handler works!")
        print(f"Custom metadata: {result.message.metadata}")
    else:
        print(f"❌ Custom fallback failed: {result.error}")


def example_integration_with_formatter_factory():
    """Example of integration with existing SlackMessageFormatterFactory."""
    print("\n=== Integration with SlackMessageFormatterFactory ===")
    
    # Create formatter factory
    factory = SlackMessageFormatterFactory()
    
    # Create integrator with the factory
    integrator = HookTemplateIntegrator(factory)
    
    # Configure formatter options
    options = FormatterOptions(
        interactive=True,
        accessibility_mode=False,
        threading_enabled=True,
        custom_config={
            'branding': {'team_name': 'Development Team'},
            'emoji_set': {'success': '🎉', 'error': '🚨'}
        }
    )
    
    # Create formatting context
    event = create_sample_event()
    execution_result = create_sample_execution_result()
    
    context = HookFormattingContext(
        hook_type="BlockerHook",
        event=event,
        execution_result=execution_result
    )
    
    # Format with options
    result = integrator.format_hook_message(context, options)
    
    if result.success:
        print("✅ Integration with formatter factory successful!")
        print(f"Interactive elements enabled: {options.interactive}")
        print(f"Custom branding applied: {options.custom_config.get('branding')}")
        
        # Show integration statistics
        stats = integrator.get_formatting_statistics()
        print(f"Integration stats: {stats}")
    else:
        print(f"❌ Integration failed: {result.error}")


def example_dynamic_template_selection():
    """Example of dynamic template selection based on event classification."""
    print("\n=== Dynamic Template Selection ===")
    
    # Create different types of events
    events = [
        # Status change event
        {
            'hook_type': 'StatusChangeHook',
            'event_classification': EventCategory.STATUS_CHANGE,
            'description': 'Status change from To Do to In Progress'
        },
        # Blocker event
        {
            'hook_type': 'BlockerHook',
            'event_classification': EventCategory.BLOCKER,
            'description': 'Critical blocker detected'
        },
        # Assignment event
        {
            'hook_type': 'AssignmentHook',
            'event_classification': EventCategory.ASSIGNMENT,
            'description': 'Ticket assigned to new team member'
        },
        # Comment event
        {
            'hook_type': 'CommentHook',
            'event_classification': EventCategory.COMMENT,
            'description': 'High-priority comment added'
        }
    ]
    
    formatter = HookMessageFormatter()
    
    for event_info in events:
        # Create mock data for each event type
        mock_data = {
            'hook_type': event_info['hook_type'],
            'event': {
                'classification': {
                    'category': event_info['event_classification'].value
                }
            }
        }
        
        # Determine event type
        event_type = formatter._determine_hook_event_type(mock_data)
        
        print(f"Hook: {event_info['hook_type']}")
        print(f"  Classification: {event_info['event_classification'].value}")
        print(f"  Selected template: {event_type.value}")
        print(f"  Description: {event_info['description']}")
        print()


def main():
    """Run all examples."""
    print("🔄 Hook Template Integration Examples")
    print("=" * 50)
    
    try:
        example_basic_hook_formatting()
        example_hook_formatter_direct()
        example_batch_hook_formatting()
        example_fallback_mechanisms()
        example_custom_fallback_handler()
        example_integration_with_formatter_factory()
        example_dynamic_template_selection()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Example execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()