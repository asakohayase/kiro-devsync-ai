"""
Example usage of the HookEventProcessor for JIRA event handling.

This example demonstrates how to use the HookEventProcessor to process
JIRA webhook events, validate them, and enrich them with additional context.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any

from devsync_ai.core.hook_event_processor import HookEventProcessor
from devsync_ai.services.jira import JiraService


async def example_basic_event_processing():
    """Example of basic event processing without JIRA service integration."""
    print("=== Basic Event Processing Example ===")
    
    # Create processor without JIRA service
    processor = HookEventProcessor()
    
    # Sample JIRA webhook event
    webhook_data = {
        'webhookEvent': 'jira:issue_updated',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'issue': {
            'key': 'PROJ-123',
            'fields': {
                'summary': 'Fix critical database connection issue',
                'description': 'Database connections are timing out causing service failures',
                'status': {'name': 'In Progress', 'id': '3'},
                'priority': {'name': 'High', 'id': '2'},
                'issuetype': {'name': 'Bug', 'subtask': False, 'id': '10004'},
                'assignee': {
                    'accountId': 'user123',
                    'displayName': 'Alice Developer',
                    'emailAddress': 'alice@company.com'
                },
                'reporter': {
                    'accountId': 'user456',
                    'displayName': 'Bob Manager',
                    'emailAddress': 'bob@company.com'
                },
                'created': '2024-01-01T08:00:00.000Z',
                'updated': '2024-01-01T14:30:00.000Z',
                'labels': ['production', 'database'],
                'components': [{'name': 'Backend API'}],
                'fixVersions': [{'name': 'v1.2.1'}]
            }
        },
        'changelog': {
            'items': [
                {
                    'field': 'status',
                    'fromString': 'To Do',
                    'toString': 'In Progress'
                }
            ]
        }
    }
    
    # Process the webhook event
    processed_event, validation_result = await processor.process_webhook_event(webhook_data)
    
    print(f"✅ Event processed successfully:")
    print(f"   Event ID: {processed_event.event_id}")
    print(f"   Event Type: {processed_event.event_type}")
    print(f"   Ticket Key: {processed_event.ticket_key}")
    print(f"   Project Key: {processed_event.project_key}")
    print(f"   Validation: {'✅ Valid' if validation_result.valid else '❌ Invalid'}")
    
    if validation_result.warnings:
        print(f"   Warnings: {len(validation_result.warnings)}")
        for warning in validation_result.warnings:
            print(f"     - {warning}")
    
    # Enrich the event
    enrichment_result = await processor.enrich_event(processed_event)
    
    if enrichment_result.success:
        enriched_event = enrichment_result.enriched_event
        classification = enriched_event.classification
        
        print(f"\n✅ Event enriched successfully:")
        print(f"   Category: {classification.category.value}")
        print(f"   Urgency: {classification.urgency.value}")
        print(f"   Significance: {classification.significance.value}")
        print(f"   Affected Teams: {classification.affected_teams}")
        print(f"   Stakeholders: {len(enriched_event.stakeholders)}")
        
        for stakeholder in enriched_event.stakeholders:
            print(f"     - {stakeholder.display_name} ({stakeholder.role})")
        
        print(f"   Keywords: {classification.keywords[:5]}...")  # Show first 5 keywords
        print(f"   Processing Time: {enrichment_result.processing_time_ms:.2f}ms")
    else:
        print(f"❌ Event enrichment failed: {enrichment_result.errors}")
    
    return processed_event, enriched_event if enrichment_result.success else None


async def example_validation_scenarios():
    """Example of different validation scenarios."""
    print("\n=== Validation Scenarios Example ===")
    
    processor = HookEventProcessor()
    
    # Test cases with different validation outcomes
    test_cases = [
        {
            'name': 'Valid Event',
            'data': {
                'webhookEvent': 'jira:issue_created',
                'issue': {
                    'key': 'TEST-456',
                    'fields': {
                        'summary': 'New feature request',
                        'status': {'name': 'Open'},
                        'issuetype': {'name': 'Story'}
                    }
                }
            }
        },
        {
            'name': 'Missing Webhook Event',
            'data': {
                'issue': {
                    'key': 'TEST-789',
                    'fields': {'summary': 'Test issue'}
                }
            }
        },
        {
            'name': 'Invalid Issue Key',
            'data': {
                'webhookEvent': 'jira:issue_updated',
                'issue': {
                    'key': 'INVALIDKEY',  # No hyphen
                    'fields': {}
                }
            }
        },
        {
            'name': 'Comment Event',
            'data': {
                'webhookEvent': 'jira:issue_commented',
                'issue': {
                    'key': 'TEST-999',
                    'fields': {'summary': 'Test issue'}
                },
                'comment': {
                    'id': '12345',
                    'body': 'This looks good to me!',
                    'author': {'displayName': 'Reviewer'}
                }
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 Testing: {test_case['name']}")
        
        try:
            processed_event, validation_result = await processor.process_webhook_event(
                test_case['data']
            )
            
            if validation_result.valid:
                print(f"   ✅ Valid - Ticket: {processed_event.ticket_key}")
            else:
                print(f"   ❌ Invalid - Errors: {len(validation_result.errors)}")
                for error in validation_result.errors:
                    print(f"     - {error}")
            
            if validation_result.warnings:
                print(f"   ⚠️  Warnings: {len(validation_result.warnings)}")
                for warning in validation_result.warnings:
                    print(f"     - {warning}")
                    
        except Exception as e:
            print(f"   💥 Exception: {str(e)}")


async def example_event_classification():
    """Example of event classification for different scenarios."""
    print("\n=== Event Classification Example ===")
    
    processor = HookEventProcessor()
    
    # Different event scenarios
    scenarios = [
        {
            'name': 'Blocker Event',
            'data': {
                'webhookEvent': 'jira:issue_updated',
                'issue': {
                    'key': 'PROJ-001',
                    'fields': {
                        'summary': 'Cannot proceed due to API dependency',
                        'status': {'name': 'Blocked'},
                        'priority': {'name': 'High'},
                        'issuetype': {'name': 'Bug'},
                        'labels': ['blocker', 'api']
                    }
                }
            }
        },
        {
            'name': 'High Priority Assignment',
            'data': {
                'webhookEvent': 'jira:issue_assigned',
                'issue': {
                    'key': 'PROJ-002',
                    'fields': {
                        'summary': 'Critical security vulnerability fix',
                        'status': {'name': 'To Do'},
                        'priority': {'name': 'Critical'},
                        'issuetype': {'name': 'Bug'},
                        'assignee': {
                            'displayName': 'Security Team Lead',
                            'accountId': 'sec123'
                        }
                    }
                }
            }
        },
        {
            'name': 'Regular Comment',
            'data': {
                'webhookEvent': 'jira:issue_commented',
                'issue': {
                    'key': 'PROJ-003',
                    'fields': {
                        'summary': 'Update documentation',
                        'status': {'name': 'In Progress'},
                        'priority': {'name': 'Low'},
                        'issuetype': {'name': 'Task'}
                    }
                },
                'comment': {
                    'body': 'Added the new section as requested',
                    'author': {'displayName': 'Doc Writer'}
                }
            }
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📊 Scenario: {scenario['name']}")
        
        processed_event, _ = await processor.process_webhook_event(scenario['data'])
        enrichment_result = await processor.enrich_event(processed_event)
        
        if enrichment_result.success:
            classification = enrichment_result.enriched_event.classification
            print(f"   Category: {classification.category.value}")
            print(f"   Urgency: {classification.urgency.value}")
            print(f"   Significance: {classification.significance.value}")
            
            if classification.keywords:
                print(f"   Key Keywords: {', '.join(classification.keywords[:3])}")
        else:
            print(f"   ❌ Classification failed: {enrichment_result.errors}")


async def example_metrics_and_health():
    """Example of metrics collection and health monitoring."""
    print("\n=== Metrics and Health Example ===")
    
    processor = HookEventProcessor()
    
    # Process several events to generate metrics
    sample_events = [
        {'webhookEvent': 'jira:issue_created', 'issue': {'key': 'TEST-1', 'fields': {}}},
        {'webhookEvent': 'jira:issue_updated', 'issue': {'key': 'TEST-2', 'fields': {}}},
        {'invalid': 'data'},  # This will cause validation failure
        {'webhookEvent': 'jira:issue_commented', 'issue': {'key': 'TEST-3', 'fields': {}}, 'comment': {'body': 'test'}}
    ]
    
    print("Processing sample events...")
    for i, event_data in enumerate(sample_events, 1):
        try:
            processed_event, validation_result = await processor.process_webhook_event(event_data)
            if validation_result.valid:
                await processor.enrich_event(processed_event)
            print(f"   Event {i}: {'✅' if validation_result.valid else '❌'}")
        except Exception as e:
            print(f"   Event {i}: 💥 {str(e)}")
    
    # Get metrics
    metrics = processor.get_metrics()
    print(f"\n📈 Processor Metrics:")
    print(f"   Events Processed: {metrics['events_processed']}")
    print(f"   Events Enriched: {metrics['events_enriched']}")
    print(f"   Validation Failures: {metrics['validation_failures']}")
    print(f"   Enrichment Failures: {metrics['enrichment_failures']}")
    print(f"   Success Rate: {metrics['success_rate']:.2%}")
    print(f"   Validation Success Rate: {metrics['validation_success_rate']:.2%}")
    
    # Health check
    health = await processor.health_check()
    print(f"\n🏥 Health Status: {health['status']}")
    print(f"   JIRA Service Available: {health['jira_service_available']}")
    for component, status in health['components'].items():
        print(f"   {component}: {status}")


async def main():
    """Run all examples."""
    print("🚀 HookEventProcessor Usage Examples")
    print("=" * 50)
    
    try:
        # Run examples
        await example_basic_event_processing()
        await example_validation_scenarios()
        await example_event_classification()
        await example_metrics_and_health()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Example failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())