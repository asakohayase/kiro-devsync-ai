"""Examples demonstrating smart message batching and threading features."""

from datetime import datetime, timedelta
from typing import Dict, Any

from devsync_ai.core.smart_message_batcher import (
    SmartMessageBatcher, SpamPreventionConfig, TimingConfig,
    SpamPreventionStrategy, TimingMode
)
from devsync_ai.core.message_batcher import BatchableMessage, ContentType, BatchConfig
from devsync_ai.core.message_threading import (
    MessageThreadingManager, ThreadingConfig, ThreadingStrategy, ThreadType
)
from devsync_ai.core.threaded_message_formatter import ThreadedMessageFormatter
from devsync_ai.core.batching_config import BatchingConfigManager


def example_smart_batching():
    """Example of smart message batching with spam prevention."""
    print("=== Smart Message Batching Example ===")
    
    # Configure spam prevention
    spam_config = SpamPreventionConfig(
        enabled=True,
        max_messages_per_minute=5,
        max_messages_per_hour=50,
        burst_threshold=3,
        burst_window_seconds=30,
        cooldown_after_burst_minutes=2,
        duplicate_content_window_minutes=10,
        quiet_hours_enabled=True,
        quiet_hours_start=22,  # 10 PM
        quiet_hours_end=8,     # 8 AM
        strategies=[
            SpamPreventionStrategy.RATE_LIMITING,
            SpamPreventionStrategy.ADAPTIVE_TIMING,
            SpamPreventionStrategy.CONTENT_DEDUPLICATION
        ]
    )
    
    # Configure smart timing
    timing_config = TimingConfig(
        mode=TimingMode.ADAPTIVE,
        base_interval_minutes=5,
        max_interval_minutes=30,
        adaptive_factor=1.5,
        priority_timing_overrides={
            'critical': 0,  # Immediate
            'high': 1,      # Max 1 minute
            'medium': 5,    # Max 5 minutes
            'low': 15,      # Max 15 minutes
        }
    )
    
    # Create smart batcher
    batcher = SmartMessageBatcher(
        spam_config=spam_config,
        timing_config=timing_config
    )
    
    # Example messages
    messages = [
        BatchableMessage(
            id="msg_1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="developer1",
            priority="high",
            data={
                "title": "Critical bug fix PR",
                "number": 123,
                "repository": "main-app"
            }
        ),
        BatchableMessage(
            id="msg_2",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now() + timedelta(seconds=30),
            author="developer1",
            priority="medium",
            data={
                "title": "Update documentation",
                "number": 124,
                "repository": "main-app"
            }
        ),
        BatchableMessage(
            id="msg_3",
            content_type=ContentType.ALERT,
            timestamp=datetime.now() + timedelta(minutes=1),
            author="system",
            priority="critical",
            data={
                "title": "Service outage detected",
                "service": "auth-service",
                "severity": "critical"
            }
        )
    ]
    
    # Process messages
    channel_id = "dev-updates"
    for message in messages:
        result = batcher.add_message(message, channel_id)
        if result:
            print(f"Batched message ready: {len(result.blocks)} blocks")
        else:
            print(f"Message queued for batching: {message.id}")
    
    # Get statistics
    stats = batcher.get_spam_prevention_stats()
    print(f"Spam prevention stats: {stats}")
    
    # Get channel activity summary
    activity = batcher.get_channel_activity_summary(channel_id)
    print(f"Channel activity: {activity}")
    
    print()


def example_message_threading():
    """Example of message threading for related notifications."""
    print("=== Message Threading Example ===")
    
    # Configure threading
    threading_config = ThreadingConfig(
        enabled=True,
        max_thread_age_hours=24,
        auto_thread_similar_content=True,
        thread_similarity_threshold=0.8,
        temporal_window_minutes=30,
        strategies=[
            ThreadingStrategy.ENTITY_BASED,
            ThreadingStrategy.CONTENT_BASED,
            ThreadingStrategy.TEMPORAL
        ]
    )
    
    # Create threading manager
    threading_manager = MessageThreadingManager(threading_config)
    
    # Create threaded formatter
    formatter = ThreadedMessageFormatter(threading_manager)
    
    # Example PR lifecycle messages
    pr_messages = [
        {
            'pr': {
                'number': 123,
                'title': 'Fix authentication bug',
                'repository': {'name': 'main-app'},
                'author': {'login': 'developer1'}
            },
            'author': 'developer1',
            'template_type': 'pr_opened',
            'text': 'New PR opened: Fix authentication bug'
        },
        {
            'pr': {
                'number': 123,
                'title': 'Fix authentication bug',
                'repository': {'name': 'main-app'},
                'author': {'login': 'developer1'}
            },
            'author': 'reviewer1',
            'template_type': 'pr_review_requested',
            'text': 'PR review requested: Fix authentication bug'
        },
        {
            'pr': {
                'number': 123,
                'title': 'Fix authentication bug',
                'repository': {'name': 'main-app'},
                'author': {'login': 'developer1'}
            },
            'author': 'reviewer1',
            'template_type': 'pr_approved',
            'text': 'PR approved: Fix authentication bug'
        }
    ]
    
    channel_id = "dev-updates"
    thread_contexts = []
    
    # Process PR lifecycle messages
    for i, template_data in enumerate(pr_messages):
        threaded_message = formatter.format_with_threading(
            template_data, channel_id, "pr_template"
        )
        
        print(f"Message {i+1}:")
        print(f"  Thread TS: {threaded_message.thread_ts}")
        print(f"  Is thread starter: {threaded_message.is_thread_starter}")
        print(f"  Related threads: {len(threaded_message.related_threads)}")
        
        # Simulate message being sent and getting timestamp
        if threaded_message.is_thread_starter:
            message_ts = f"1234567890.{i:06d}"
            context = formatter.create_thread_starter(
                threaded_message, channel_id, message_ts
            )
            thread_contexts.append(context)
            print(f"  Created thread: {context.thread_id} ({context.thread_type.value})")
        
        print()
    
    # Get threading statistics
    stats = threading_manager.get_threading_stats()
    print(f"Threading stats: {stats}")
    
    # Get channel threads
    threads = threading_manager.get_channel_threads(channel_id)
    print(f"Active threads in channel: {len(threads)}")
    
    # Format thread summary
    if thread_contexts:
        summary = formatter.format_thread_summary(thread_contexts[0], channel_id)
        print(f"Thread summary blocks: {len(summary.blocks)}")
    
    print()


def example_configuration_management():
    """Example of configuration management for batching and threading."""
    print("=== Configuration Management Example ===")
    
    # Create config manager
    config_manager = BatchingConfigManager()
    
    # Load team configuration
    team_config = config_manager.load_team_config("engineering")
    print(f"Loaded config for team: {team_config.team_id}")
    print(f"Spam prevention enabled: {team_config.spam_prevention.enabled}")
    print(f"Timing mode: {team_config.timing.mode.value}")
    
    # Apply channel-specific overrides
    alerts_config = config_manager.apply_channel_overrides(team_config, "alerts")
    print(f"Alerts channel config: {alerts_config.spam_prevention.max_messages_per_minute} msgs/min")
    
    # Validate configuration
    errors = config_manager.validate_config(team_config)
    if errors:
        print(f"Configuration errors: {errors}")
    else:
        print("Configuration is valid")
    
    # Create batcher with team config
    batcher = SmartMessageBatcher(
        spam_config=team_config.spam_prevention,
        timing_config=team_config.timing
    )
    
    print(f"Batcher created with {len(team_config.spam_prevention.strategies)} spam prevention strategies")
    print()


def example_integration_workflow():
    """Example of complete integration workflow with batching and threading."""
    print("=== Complete Integration Workflow ===")
    
    # Load configuration
    config_manager = BatchingConfigManager()
    team_config = config_manager.load_team_config("default")
    
    # Create components
    threading_manager = MessageThreadingManager()
    batcher = SmartMessageBatcher(
        spam_config=team_config.spam_prevention,
        timing_config=team_config.timing
    )
    formatter = ThreadedMessageFormatter(threading_manager, batcher)
    
    # Simulate webhook events
    webhook_events = [
        {
            'type': 'pr_opened',
            'data': {
                'pr': {
                    'number': 456,
                    'title': 'Add new feature',
                    'repository': {'name': 'feature-app'},
                    'author': {'login': 'developer2'}
                },
                'author': 'developer2',
                'template_type': 'pr_opened',
                'text': 'New PR opened: Add new feature'
            }
        },
        {
            'type': 'jira_updated',
            'data': {
                'ticket': {
                    'key': 'FEAT-123',
                    'summary': 'Implement new feature',
                    'status': {'name': 'In Progress'},
                    'assignee': {'displayName': 'developer2'}
                },
                'author': 'developer2',
                'template_type': 'jira_status_change',
                'text': 'JIRA ticket updated: FEAT-123'
            }
        },
        {
            'type': 'alert_triggered',
            'data': {
                'alert': {
                    'id': 'alert_789',
                    'title': 'High CPU usage',
                    'severity': 'high',
                    'service': 'feature-app'
                },
                'author': 'monitoring',
                'template_type': 'alert_triggered',
                'text': 'Alert triggered: High CPU usage'
            }
        }
    ]
    
    channel_id = "team-notifications"
    processed_messages = []
    
    # Process each event
    for event in webhook_events:
        print(f"Processing {event['type']} event...")
        
        # Format with threading
        threaded_message = formatter.format_with_threading(
            event['data'], channel_id, event['type']
        )
        
        # Check if should be batched
        if batcher:
            # Convert to batchable message
            batchable = BatchableMessage(
                id=f"event_{len(processed_messages)}",
                content_type=ContentType.PR_UPDATE if 'pr' in event['data'] else ContentType.ALERT,
                timestamp=datetime.now(),
                author=event['data'].get('author', 'unknown'),
                priority=event['data'].get('priority', 'medium'),
                data=event['data']
            )
            
            batched_result = batcher.add_message(batchable, channel_id)
            if batched_result:
                print(f"  Message batched with {len(batched_result.blocks)} blocks")
            else:
                print(f"  Message queued for batching")
        
        processed_messages.append(threaded_message)
        
        # Simulate thread creation if needed
        if threaded_message.is_thread_starter:
            message_ts = f"1234567890.{len(processed_messages):06d}"
            context = formatter.create_thread_starter(
                threaded_message, channel_id, message_ts
            )
            print(f"  Created thread: {context.thread_type.value}")
        elif threaded_message.thread_ts:
            print(f"  Added to existing thread: {threaded_message.thread_ts}")
        
        print()
    
    # Final statistics
    print("Final Statistics:")
    print(f"  Processed messages: {len(processed_messages)}")
    print(f"  Threading stats: {threading_manager.get_threading_stats()}")
    print(f"  Batching stats: {batcher.get_spam_prevention_stats()}")
    print()


def example_advanced_features():
    """Example of advanced batching and threading features."""
    print("=== Advanced Features Example ===")
    
    # Advanced spam prevention with multiple strategies
    advanced_spam_config = SpamPreventionConfig(
        enabled=True,
        max_messages_per_minute=10,
        max_messages_per_hour=100,
        burst_threshold=5,
        burst_window_seconds=60,
        cooldown_after_burst_minutes=5,
        duplicate_content_window_minutes=20,
        priority_rate_limits={
            'critical': 30,
            'high': 20,
            'medium': 15,
            'low': 10,
            'lowest': 5
        },
        quiet_hours_enabled=True,
        quiet_hours_start=23,
        quiet_hours_end=7,
        strategies=[
            SpamPreventionStrategy.RATE_LIMITING,
            SpamPreventionStrategy.ADAPTIVE_TIMING,
            SpamPreventionStrategy.CONTENT_DEDUPLICATION,
            SpamPreventionStrategy.PRIORITY_THROTTLING
        ]
    )
    
    # Advanced timing with smart burst handling
    advanced_timing_config = TimingConfig(
        mode=TimingMode.SMART_BURST,
        base_interval_minutes=3,
        max_interval_minutes=45,
        min_interval_minutes=1,
        adaptive_factor=2.0,
        burst_detection_enabled=True,
        user_activity_tracking=True,
        priority_timing_overrides={
            'critical': 0,
            'high': 2,
            'medium': 10,
            'low': 30,
            'lowest': 60
        }
    )
    
    # Advanced threading with multiple strategies
    advanced_threading_config = ThreadingConfig(
        enabled=True,
        max_thread_age_hours=48,
        max_messages_per_thread=100,
        auto_thread_similar_content=True,
        thread_similarity_threshold=0.75,
        temporal_window_minutes=60,
        enable_cross_channel_threading=False,
        strategies=[
            ThreadingStrategy.ENTITY_BASED,
            ThreadingStrategy.CONTENT_BASED,
            ThreadingStrategy.TEMPORAL,
            ThreadingStrategy.WORKFLOW
        ],
        thread_types_enabled=[
            ThreadType.PR_LIFECYCLE,
            ThreadType.JIRA_UPDATES,
            ThreadType.ALERT_SEQUENCE,
            ThreadType.DEPLOYMENT_PIPELINE,
            ThreadType.STANDUP_FOLLOWUP,
            ThreadType.INCIDENT_RESPONSE
        ]
    )
    
    # Create advanced components
    batcher = SmartMessageBatcher(
        spam_config=advanced_spam_config,
        timing_config=advanced_timing_config
    )
    
    threading_manager = MessageThreadingManager(advanced_threading_config)
    formatter = ThreadedMessageFormatter(threading_manager, batcher)
    
    print("Advanced components created with:")
    print(f"  Spam prevention strategies: {len(advanced_spam_config.strategies)}")
    print(f"  Threading strategies: {len(advanced_threading_config.strategies)}")
    print(f"  Thread types enabled: {len(advanced_threading_config.thread_types_enabled)}")
    
    # Simulate complex workflow
    complex_events = [
        # Incident starts
        {
            'type': 'incident_created',
            'data': {
                'incident': {'id': 'INC-001', 'title': 'Database connection issues'},
                'severity': 'critical',
                'template_type': 'incident_created'
            }
        },
        # Related alerts
        {
            'type': 'alert_triggered',
            'data': {
                'alert': {'id': 'ALT-001', 'title': 'DB connection timeout'},
                'incident_id': 'INC-001',
                'severity': 'high',
                'template_type': 'alert_triggered'
            }
        },
        # PR to fix issue
        {
            'type': 'pr_opened',
            'data': {
                'pr': {'number': 789, 'title': 'Fix DB connection pool'},
                'incident_id': 'INC-001',
                'priority': 'critical',
                'template_type': 'pr_opened'
            }
        },
        # Deployment
        {
            'type': 'deployment_started',
            'data': {
                'deployment': {'id': 'DEP-001', 'environment': 'production'},
                'pr_number': 789,
                'incident_id': 'INC-001',
                'template_type': 'deployment_started'
            }
        }
    ]
    
    # Process complex workflow
    for event in complex_events:
        threaded_message = formatter.format_with_threading(
            event['data'], "incidents", event['type']
        )
        
        print(f"Processed {event['type']}:")
        print(f"  Threading: {threaded_message.thread_ts or 'New thread'}")
        print(f"  Related threads: {len(threaded_message.related_threads)}")
    
    print()
    print("Advanced workflow completed!")
    print()


if __name__ == "__main__":
    """Run all examples."""
    example_smart_batching()
    example_message_threading()
    example_configuration_management()
    example_integration_workflow()
    example_advanced_features()
    
    print("=== All Examples Completed ===")
    print("The batching and threading system provides:")
    print("✅ Smart spam prevention with multiple strategies")
    print("✅ Adaptive timing controls to prevent notification overload")
    print("✅ Intelligent message threading for related conversations")
    print("✅ Configurable team and channel-specific settings")
    print("✅ Comprehensive statistics and monitoring")
    print("✅ Integration with existing template system")