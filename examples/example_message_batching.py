#!/usr/bin/env python3
"""Example usage of sophisticated message batching system."""

import sys
from datetime import datetime, timedelta
sys.path.append('.')

from devsync_ai.core.message_batcher import (
    MessageBatcher, BatchableMessage, BatchConfig, BatchType, 
    BatchStrategy, ContentType, default_message_batcher
)


def example_daily_development_summary():
    """Example: Create a daily development summary batch."""
    print("📊 Daily Development Summary Example")
    print("=" * 50)
    
    # Configure batcher for daily summaries
    config = BatchConfig(
        strategies=[BatchStrategy.MIXED],
        max_batch_size=10,
        max_batch_age_minutes=60,  # 1 hour batching window
        enable_pagination=True,
        items_per_page=5,
        priority_ordering=True
    )
    
    batcher = MessageBatcher(config)
    
    # Simulate development activity throughout the day
    base_time = datetime.now() - timedelta(hours=8)  # Start 8 hours ago
    
    # Morning PR activity
    pr_messages = [
        BatchableMessage(
            id="morning_pr_1",
            content_type=ContentType.PR_UPDATE,
            timestamp=base_time + timedelta(hours=1),
            author="alice",
            priority="high",
            data={
                "repository": "main-app",
                "number": 501,
                "title": "Fix critical authentication bug",
                "action": "ready_for_review"
            }
        ),
        BatchableMessage(
            id="morning_pr_2", 
            content_type=ContentType.PR_UPDATE,
            timestamp=base_time + timedelta(hours=2),
            author="bob",
            priority="medium",
            data={
                "repository": "main-app",
                "number": 502,
                "title": "Update API documentation",
                "action": "merged"
            }
        ),
        BatchableMessage(
            id="morning_pr_3",
            content_type=ContentType.PR_UPDATE,
            timestamp=base_time + timedelta(hours=2, minutes=30),
            author="carol",
            priority="medium",
            data={
                "repository": "main-app",
                "number": 503,
                "title": "Add comprehensive unit tests",
                "action": "merged"
            }
        )
    ]
    
    # Afternoon JIRA activity
    jira_messages = [
        BatchableMessage(
            id="afternoon_jira_1",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=base_time + timedelta(hours=4),
            author="alice",
            priority="medium",
            data={
                "project": "DEV",
                "key": "DEV-401",
                "summary": "User authentication improvements",
                "status": {"name": "Done"}
            }
        ),
        BatchableMessage(
            id="afternoon_jira_2",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=base_time + timedelta(hours=5),
            author="dave",
            priority="low",
            data={
                "project": "DEV",
                "key": "DEV-402",
                "summary": "Update API documentation",
                "status": {"name": "Done"}
            }
        )
    ]
    
    # Late afternoon blocker
    blocker_message = BatchableMessage(
        id="afternoon_blocker",
        content_type=ContentType.ALERT,
        timestamp=base_time + timedelta(hours=6),
        author="system",
        priority="critical",
        data={
            "type": "blocker",
            "severity": "critical",
            "description": "Database connection timeout affecting production"
        }
    )
    
    # Add all messages to batcher
    all_messages = pr_messages + jira_messages + [blocker_message]
    
    print(f"Adding {len(all_messages)} development activities...")
    for message in all_messages:
        result = batcher.add_message(message)
        if result:
            print(f"  ⚡ Batch triggered: {result.metadata.get('batch_type')}")
    
    # Get current statistics
    stats = batcher.get_batch_stats()
    print(f"\n📈 Batching Statistics:")
    print(f"  Active batches: {stats['active_batches']}")
    print(f"  Messages batched: {stats['messages_batched']}")
    print(f"  Pending messages: {stats['pending_messages']}")
    
    # Flush all batches to create daily summary
    print(f"\n🔄 Generating daily summary...")
    batched_messages = batcher.flush_all_batches()
    
    print(f"\n✅ Generated {len(batched_messages)} summary messages:")
    
    for i, message in enumerate(batched_messages, 1):
        batch_type = message.metadata.get('batch_type')
        message_count = message.metadata.get('message_count')
        
        print(f"\n📋 Summary {i}: {batch_type.replace('_', ' ').title()}")
        print(f"   Messages: {message_count}")
        print(f"   Blocks: {len(message.blocks)}")
        
        # Show the summary header
        for block in message.blocks:
            if block.get('type') == 'header':
                print(f"   Header: {block['text']['text']}")
                break
        
        # Show fallback text (for accessibility)
        print(f"   Fallback: {message.text[:100]}...")
    
    return batched_messages


def example_sprint_update_batch():
    """Example: Create a sprint update batch."""
    print("\n🏃 Sprint Update Batch Example")
    print("=" * 50)
    
    # Use default batcher with sprint-focused config
    config = BatchConfig(
        strategies=[BatchStrategy.CONTENT_SIMILARITY, BatchStrategy.TIME_BASED],
        max_batch_size=15,
        similarity_threshold=0.8,
        enable_threading=True
    )
    
    batcher = MessageBatcher(config)
    
    # Sprint ticket updates
    sprint_updates = [
        BatchableMessage(
            id="sprint_ticket_1",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=datetime.now(),
            author="alice",
            data={
                "project": "SPRINT",
                "key": "SPRINT-101",
                "summary": "Implement user dashboard",
                "status": {"name": "In Progress"},
                "sprint": "Sprint 23"
            }
        ),
        BatchableMessage(
            id="sprint_ticket_2",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=datetime.now() + timedelta(minutes=5),
            author="bob",
            data={
                "project": "SPRINT",
                "key": "SPRINT-102", 
                "summary": "Add authentication middleware",
                "status": {"name": "Done"},
                "sprint": "Sprint 23"
            }
        ),
        BatchableMessage(
            id="sprint_ticket_3",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=datetime.now() + timedelta(minutes=10),
            author="carol",
            data={
                "project": "SPRINT",
                "key": "SPRINT-103",
                "summary": "Write integration tests",
                "status": {"name": "Done"},
                "sprint": "Sprint 23"
            }
        )
    ]
    
    # Add sprint updates
    for update in sprint_updates:
        batcher.add_message(update)
    
    # Force flush for demonstration
    sprint_batches = batcher.flush_all_batches()
    
    print(f"✅ Generated {len(sprint_batches)} sprint update batches")
    
    for batch in sprint_batches:
        print(f"\n📊 Sprint Batch:")
        print(f"   Type: {batch.metadata.get('batch_type')}")
        print(f"   Messages: {batch.metadata.get('message_count')}")
        
        # Show summary content
        for block in batch.blocks:
            if block.get('type') == 'section' and 'text' in block:
                text = block['text']['text']
                if '├──' in text or '└──' in text:
                    print(f"   Content: {text}")
                    break
    
    return sprint_batches


def example_real_time_batching():
    """Example: Real-time batching with automatic flushing."""
    print("\n⚡ Real-Time Batching Example")
    print("=" * 50)
    
    # Configure for real-time batching
    config = BatchConfig(
        max_batch_size=3,  # Small batches for quick delivery
        max_batch_age_minutes=2,  # Quick expiration
        strategies=[BatchStrategy.TIME_BASED]
    )
    
    batcher = MessageBatcher(config)
    
    # Simulate real-time events
    events = [
        ("PR opened", ContentType.PR_UPDATE, "alice", {"action": "opened", "number": 601}),
        ("JIRA updated", ContentType.JIRA_UPDATE, "bob", {"status": {"name": "In Progress"}, "key": "DEV-601"}),
        ("PR approved", ContentType.PR_UPDATE, "carol", {"action": "approved", "number": 602}),
        ("Alert triggered", ContentType.ALERT, "system", {"severity": "high", "type": "performance"}),
    ]
    
    batched_count = 0
    
    for i, (event_name, content_type, author, data) in enumerate(events):
        print(f"\n🔔 Event {i+1}: {event_name} by {author}")
        
        message = BatchableMessage(
            id=f"realtime_{i}",
            content_type=content_type,
            timestamp=datetime.now(),
            author=author,
            data=data
        )
        
        # Add message and check for immediate batching
        result = batcher.add_message(message)
        
        if result:
            batched_count += 1
            print(f"  ⚡ Immediate batch created!")
            print(f"     Type: {result.metadata.get('batch_type')}")
            print(f"     Messages: {result.metadata.get('message_count')}")
        else:
            print(f"  ⏳ Added to pending batch...")
    
    # Flush any remaining batches
    remaining = batcher.flush_all_batches()
    batched_count += len(remaining)
    
    print(f"\n✅ Total batches created: {batched_count}")
    print(f"📊 Final statistics: {batcher.get_batch_stats()}")
    
    return batched_count


if __name__ == "__main__":
    print("🚀 Sophisticated Message Batching Examples")
    print("=" * 60)
    
    # Run examples
    daily_batches = example_daily_development_summary()
    sprint_batches = example_sprint_update_batch()
    realtime_count = example_real_time_batching()
    
    print(f"\n🎉 Examples Complete!")
    print(f"📊 Summary:")
    print(f"  Daily summary batches: {len(daily_batches)}")
    print(f"  Sprint update batches: {len(sprint_batches)}")
    print(f"  Real-time batches: {realtime_count}")
    
    print(f"\n💡 Key Features Demonstrated:")
    print(f"  ✅ Time-based grouping (5-minute windows)")
    print(f"  ✅ Content similarity detection")
    print(f"  ✅ Priority-based ordering")
    print(f"  ✅ Smart batching strategies")
    print(f"  ✅ Pagination for large batches")
    print(f"  ✅ Interactive elements (buttons, threading)")
    print(f"  ✅ Comprehensive statistics and monitoring")
    
    print(f"\n📋 Example Output Format:")
    print(f"📊 Daily Development Summary - 8 updates")
    print(f"├── 🔄 3 PRs ready for review (@alice, @bob)")
    print(f"├── ✅ 2 PRs merged (@carol, @dave)")
    print(f"├── 📋 2 JIRA tickets moved to Done")
    print(f"└── ⚠️ 1 blocker identified")
    print(f"[View Details] [Thread Discussion]")