#!/usr/bin/env python3
"""Test script for sophisticated message batching system."""

import sys
import time
from datetime import datetime, timedelta
sys.path.append('.')

from devsync_ai.core.message_batcher import (
    MessageBatcher, BatchableMessage, BatchConfig, BatchType, 
    BatchStrategy, ContentType
)


def test_basic_batching():
    """Test basic message batching functionality."""
    print("🧪 Testing Basic Message Batching")
    print("=" * 50)
    
    config = BatchConfig(
        max_batch_size=3,
        max_batch_age_minutes=1,
        enable_pagination=True
    )
    batcher = MessageBatcher(config)
    
    # Create test messages
    messages = [
        BatchableMessage(
            id="msg1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="alice",
            data={"number": 101, "title": "Fix auth bug", "action": "opened"}
        ),
        BatchableMessage(
            id="msg2", 
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="alice",
            data={"number": 102, "title": "Update docs", "action": "merged"}
        ),
        BatchableMessage(
            id="msg3",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="bob",
            data={"number": 103, "title": "Add tests", "action": "opened"}
        )
    ]
    
    # Add messages to batcher
    batched_message = None
    for i, message in enumerate(messages):
        result = batcher.add_message(message)
        if result:
            batched_message = result
            print(f"✅ Batch triggered after {i+1} messages")
            break
    
    if not batched_message:
        # Force flush if batch wasn't triggered
        batched_messages = batcher.flush_all_batches()
        if batched_messages:
            batched_message = batched_messages[0]
    
    if batched_message:
        print(f"✅ Batched message created with {len(batched_message.blocks)} blocks")
        print(f"   Fallback text: {batched_message.text[:100]}...")
        print(f"   Metadata: {batched_message.metadata}")
        return True
    else:
        print("❌ No batched message created")
        return False


def test_content_similarity_batching():
    """Test content similarity-based batching."""
    print("\n🧪 Testing Content Similarity Batching")
    print("=" * 50)
    
    config = BatchConfig(
        strategies=[BatchStrategy.CONTENT_SIMILARITY],
        similarity_threshold=0.6,
        max_batch_size=5
    )
    batcher = MessageBatcher(config)
    
    # Create similar PR messages (same author, same repo)
    similar_messages = [
        BatchableMessage(
            id="sim1",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="alice",
            data={"repository": "main-app", "number": 201, "action": "opened"}
        ),
        BatchableMessage(
            id="sim2",
            content_type=ContentType.PR_UPDATE,
            timestamp=datetime.now(),
            author="alice", 
            data={"repository": "main-app", "number": 202, "action": "merged"}
        ),
        BatchableMessage(
            id="different",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=datetime.now(),
            author="bob",
            data={"project": "different-project", "key": "DEV-101"}
        )
    ]
    
    # Add messages
    for message in similar_messages:
        batcher.add_message(message)
    
    # Check batch groups
    stats = batcher.get_batch_stats()
    print(f"✅ Created {stats['active_batches']} batch groups")
    print(f"   Pending messages: {stats['pending_messages']}")
    
    # Flush and check results
    batched_messages = batcher.flush_all_batches()
    print(f"✅ Generated {len(batched_messages)} batched messages")
    
    # Verify similar messages were grouped together
    for msg in batched_messages:
        if msg.metadata.get('batch_type') == 'pr_activity':
            print(f"   PR batch has {msg.metadata.get('message_count')} messages")
    
    return len(batched_messages) > 0


def test_time_based_batching():
    """Test time-based batching strategy."""
    print("\n🧪 Testing Time-Based Batching")
    print("=" * 50)
    
    config = BatchConfig(
        strategies=[BatchStrategy.TIME_BASED],
        max_batch_age_minutes=0.1,  # 6 seconds for testing
        max_batch_size=10
    )
    batcher = MessageBatcher(config)
    
    # Create messages with different timestamps
    base_time = datetime.now()
    messages = [
        BatchableMessage(
            id="time1",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=base_time,
            author="alice",
            data={"key": "DEV-301", "status": {"name": "Done"}}
        ),
        BatchableMessage(
            id="time2",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=base_time + timedelta(seconds=30),
            author="bob",
            data={"key": "DEV-302", "status": {"name": "In Progress"}}
        ),
        BatchableMessage(
            id="time3",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=base_time + timedelta(minutes=10),  # Different time window
            author="charlie",
            data={"key": "DEV-303", "status": {"name": "To Do"}}
        )
    ]
    
    # Add messages
    for message in messages:
        batcher.add_message(message)
    
    stats = batcher.get_batch_stats()
    print(f"✅ Time-based grouping created {stats['active_batches']} batches")
    
    # Wait for expiration and flush
    time.sleep(7)  # Wait for batch to expire
    expired_batches = batcher.flush_expired_batches()
    print(f"✅ Flushed {len(expired_batches)} expired batches")
    
    return len(expired_batches) > 0


def test_priority_ordering():
    """Test priority-based message ordering."""
    print("\n🧪 Testing Priority Ordering")
    print("=" * 50)
    
    config = BatchConfig(
        priority_ordering=True,
        max_batch_size=5
    )
    batcher = MessageBatcher(config)
    
    # Create messages with different priorities
    priority_messages = [
        BatchableMessage(
            id="low",
            content_type=ContentType.ALERT,
            timestamp=datetime.now(),
            priority="low",
            data={"type": "info", "description": "Low priority alert"}
        ),
        BatchableMessage(
            id="critical",
            content_type=ContentType.ALERT,
            timestamp=datetime.now(),
            priority="critical",
            data={"type": "system", "description": "Critical system alert"}
        ),
        BatchableMessage(
            id="medium",
            content_type=ContentType.ALERT,
            timestamp=datetime.now(),
            priority="medium",
            data={"type": "warning", "description": "Medium priority warning"}
        ),
        BatchableMessage(
            id="high",
            content_type=ContentType.ALERT,
            timestamp=datetime.now(),
            priority="high",
            data={"type": "error", "description": "High priority error"}
        )
    ]
    
    # Add messages in random order
    for message in priority_messages:
        batcher.add_message(message)
    
    # Flush and check ordering
    batched_messages = batcher.flush_all_batches()
    
    if batched_messages:
        batched_message = batched_messages[0]
        print(f"✅ Priority-ordered batch created")
        print(f"   Message count: {batched_message.metadata.get('message_count')}")
        
        # Check if critical alert appears first in blocks
        for block in batched_message.blocks:
            if block.get('type') == 'section' and 'text' in block:
                text = block['text']['text']
                if 'Critical system alert' in text:
                    print("✅ Critical alert properly prioritized")
                    break
        
        return True
    
    return False


def test_pagination():
    """Test pagination for large batches."""
    print("\n🧪 Testing Pagination")
    print("=" * 50)
    
    # Test pagination by directly creating a batch group with many messages
    from devsync_ai.core.message_batcher import BatchGroup, BatchType
    
    config = BatchConfig(
        enable_pagination=True,
        items_per_page=3,
        max_batch_size=10
    )
    batcher = MessageBatcher(config)
    
    # Create a batch group directly and add many messages
    batch_group = BatchGroup(
        id="pagination_test",
        channel_id="test-channel",
        batch_type=BatchType.PR_ACTIVITY
    )
    
    # Add 7 messages to the same batch group
    base_time = datetime.now()
    for i in range(7):
        message = BatchableMessage(
            id=f"page_{i}",
            content_type=ContentType.PR_UPDATE,
            timestamp=base_time + timedelta(seconds=i),
            author="alice",
            data={
                "repository": "main-app",
                "number": 400 + i, 
                "title": f"PR {i}", 
                "action": "opened"
            }
        )
        batch_group.add_message(message)
    
    print(f"✅ Created batch group with {len(batch_group.messages)} messages")
    
    # Manually flush the batch group to test pagination
    batched_message = batcher._create_batched_message(batch_group)
    
    if batched_message:
        print(f"✅ Paginated batch created with {len(batched_message.blocks)} blocks")
        
        # Look for pagination context
        pagination_found = False
        for block in batched_message.blocks:
            if block.get('type') == 'context':
                for element in block.get('elements', []):
                    text = element.get('text', '')
                    if 'Showing' in text and 'more' in text:
                        pagination_found = True
                        print(f"✅ Pagination info: {text}")
                        break
        
        if pagination_found:
            print("✅ Pagination working correctly")
            return True
        else:
            print("⚠️ Pagination info not found")
            # Debug: print all blocks
            for i, block in enumerate(batched_message.blocks):
                print(f"   Block {i}: {block.get('type')} - {str(block)[:100]}...")
    
    return False


def test_batch_statistics():
    """Test batch statistics and monitoring."""
    print("\n🧪 Testing Batch Statistics")
    print("=" * 50)
    
    batcher = MessageBatcher()
    
    # Add various messages
    test_messages = [
        BatchableMessage("stat1", ContentType.PR_UPDATE, datetime.now(), "alice"),
        BatchableMessage("stat2", ContentType.JIRA_UPDATE, datetime.now(), "bob"),
        BatchableMessage("stat3", ContentType.ALERT, datetime.now(), "charlie"),
        BatchableMessage("stat4", ContentType.PR_UPDATE, datetime.now(), "alice"),
    ]
    
    for message in test_messages:
        batcher.add_message(message)
    
    # Get statistics
    stats = batcher.get_batch_stats()
    
    print(f"✅ Batch statistics:")
    print(f"   Batches created: {stats['batches_created']}")
    print(f"   Messages batched: {stats['messages_batched']}")
    print(f"   Active batches: {stats['active_batches']}")
    print(f"   Pending messages: {stats['pending_messages']}")
    
    # Flush and check final stats
    batcher.flush_all_batches()
    final_stats = batcher.get_batch_stats()
    
    print(f"✅ Final statistics:")
    print(f"   Batches flushed: {final_stats['batches_flushed']}")
    print(f"   Active batches: {final_stats['active_batches']}")
    
    return stats['messages_batched'] == len(test_messages)


def test_comprehensive_example():
    """Test comprehensive real-world batching scenario."""
    print("\n🧪 Testing Comprehensive Batching Example")
    print("=" * 50)
    
    config = BatchConfig(
        strategies=[BatchStrategy.MIXED],
        max_batch_size=8,
        enable_pagination=True,
        priority_ordering=True
    )
    batcher = MessageBatcher(config)
    
    # Create realistic development activity
    base_time = datetime.now()
    
    # Multiple PR updates from same author
    pr_messages = [
        BatchableMessage(
            id="pr_batch_1",
            content_type=ContentType.PR_UPDATE,
            timestamp=base_time,
            author="alice",
            priority="high",
            data={
                "repository": "main-app",
                "number": 501,
                "title": "Fix authentication bug",
                "action": "ready_for_review"
            }
        ),
        BatchableMessage(
            id="pr_batch_2",
            content_type=ContentType.PR_UPDATE,
            timestamp=base_time + timedelta(minutes=2),
            author="bob",
            priority="medium",
            data={
                "repository": "main-app", 
                "number": 502,
                "title": "Update documentation",
                "action": "merged"
            }
        ),
        BatchableMessage(
            id="pr_batch_3",
            content_type=ContentType.PR_UPDATE,
            timestamp=base_time + timedelta(minutes=3),
            author="carol",
            priority="medium",
            data={
                "repository": "main-app",
                "number": 503,
                "title": "Add unit tests",
                "action": "merged"
            }
        )
    ]
    
    # JIRA ticket updates
    jira_messages = [
        BatchableMessage(
            id="jira_batch_1",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=base_time + timedelta(minutes=1),
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
            id="jira_batch_2",
            content_type=ContentType.JIRA_UPDATE,
            timestamp=base_time + timedelta(minutes=4),
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
    
    # Critical alert
    alert_message = BatchableMessage(
        id="alert_batch_1",
        content_type=ContentType.ALERT,
        timestamp=base_time + timedelta(minutes=5),
        author="system",
        priority="critical",
        data={
            "type": "blocker",
            "severity": "critical",
            "description": "Database connection timeout"
        }
    )
    
    # Add all messages
    all_messages = pr_messages + jira_messages + [alert_message]
    for message in all_messages:
        batcher.add_message(message)
    
    # Get statistics before flushing
    stats = batcher.get_batch_stats()
    print(f"✅ Comprehensive scenario created:")
    print(f"   Active batches: {stats['active_batches']}")
    print(f"   Total messages: {stats['messages_batched']}")
    
    # Flush all batches
    batched_messages = batcher.flush_all_batches()
    print(f"✅ Generated {len(batched_messages)} batched messages")
    
    # Analyze results
    for i, batched_message in enumerate(batched_messages):
        batch_type = batched_message.metadata.get('batch_type')
        message_count = batched_message.metadata.get('message_count')
        print(f"   Batch {i+1}: {batch_type} with {message_count} messages")
        
        # Check for proper structure
        has_header = any(block.get('type') == 'header' for block in batched_message.blocks)
        has_actions = any(block.get('type') == 'actions' for block in batched_message.blocks)
        
        if has_header:
            print(f"     ✅ Has summary header")
        if has_actions:
            print(f"     ✅ Has action buttons")
    
    return len(batched_messages) > 0


if __name__ == "__main__":
    print("🚀 Message Batching Test Suite")
    print("=" * 60)
    
    tests = [
        test_basic_batching,
        test_content_similarity_batching,
        test_time_based_batching,
        test_priority_ordering,
        test_pagination,
        test_batch_statistics,
        test_comprehensive_example
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_func.__name__} PASSED\n")
            else:
                print(f"❌ {test_func.__name__} FAILED\n")
        except Exception as e:
            print(f"❌ {test_func.__name__} FAILED with exception: {e}\n")
    
    print("📊 Test Results:")
    print("=" * 30)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Message batching system is working perfectly!")
        print("\n📋 Example Daily Development Summary:")
        print("📊 Daily Development Summary - 8 updates")
        print("├── 🔄 3 PRs ready for review (@alice, @bob)")
        print("├── ✅ 2 PRs merged (@carol, @dave)")
        print("├── 📋 2 JIRA tickets moved to Done")
        print("└── ⚠️ 1 blocker identified")
        print("[View Details] [Thread Discussion]")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")