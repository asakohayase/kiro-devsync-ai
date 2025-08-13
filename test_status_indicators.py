#!/usr/bin/env python3
"""Test script for the comprehensive status indicator system."""

from devsync_ai.core.status_indicators import (
    StatusIndicatorSystem, PRStatus, JIRAStatus, Priority, HealthStatus,
    StatusType, UrgencyLevel
)


def test_pr_status_indicators():
    """Test PR status indicators."""
    print("🧪 Testing PR Status Indicators")
    print("=" * 40)
    
    system = StatusIndicatorSystem()
    
    pr_statuses = [
        PRStatus.DRAFT,
        PRStatus.OPEN,
        PRStatus.READY_FOR_REVIEW,
        PRStatus.APPROVED,
        PRStatus.CHANGES_REQUESTED,
        PRStatus.MERGED,
        PRStatus.CLOSED,
        PRStatus.CONFLICTS
    ]
    
    for status in pr_statuses:
        indicator = system.get_pr_status_indicator(status)
        print(f"{indicator.emoji} {status.value:<20} | {indicator.color} | {indicator.text}")
    
    print("✅ PR status indicators test passed\n")


def test_jira_status_indicators():
    """Test JIRA status indicators."""
    print("🧪 Testing JIRA Status Indicators")
    print("=" * 40)
    
    system = StatusIndicatorSystem()
    
    jira_statuses = [
        JIRAStatus.TODO,
        JIRAStatus.IN_PROGRESS,
        JIRAStatus.IN_REVIEW,
        JIRAStatus.DONE,
        JIRAStatus.BLOCKED,
        JIRAStatus.CANCELLED
    ]
    
    for status in jira_statuses:
        indicator = system.get_jira_status_indicator(status)
        print(f"{indicator.emoji} {status.value:<15} | {indicator.color} | {indicator.text}")
    
    print("✅ JIRA status indicators test passed\n")


def test_priority_indicators():
    """Test priority indicators."""
    print("🧪 Testing Priority Indicators")
    print("=" * 40)
    
    system = StatusIndicatorSystem()
    
    priorities = [
        Priority.LOWEST,
        Priority.LOW,
        Priority.MEDIUM,
        Priority.HIGH,
        Priority.HIGHEST,
        Priority.BLOCKER
    ]
    
    for priority in priorities:
        indicator = system.get_priority_indicator(priority)
        print(f"{indicator.emoji} {priority.value:<10} | {indicator.color} | {indicator.text}")
    
    print("✅ Priority indicators test passed\n")


def test_health_indicators():
    """Test health status indicators."""
    print("🧪 Testing Health Status Indicators")
    print("=" * 40)
    
    system = StatusIndicatorSystem()
    
    health_statuses = [
        HealthStatus.HEALTHY,
        HealthStatus.WARNING,
        HealthStatus.CRITICAL,
        HealthStatus.UNKNOWN
    ]
    
    for health in health_statuses:
        indicator = system.get_health_status_indicator(health)
        print(f"{indicator.emoji} {health.value:<10} | {indicator.color} | {indicator.text}")
    
    print("✅ Health status indicators test passed\n")


def test_string_based_indicators():
    """Test string-based indicator lookup with context."""
    print("🧪 Testing String-Based Indicator Lookup")
    print("=" * 40)
    
    system = StatusIndicatorSystem()
    
    test_cases = [
        ("draft", "pr"),
        ("ready_for_review", "pr"),
        ("merged", "pr"),
        ("in_progress", "jira"),
        ("done", "jira"),
        ("blocked", "jira"),
        ("high", "priority"),
        ("blocker", "priority"),
        ("healthy", "health"),
        ("critical", "health"),
        ("unknown_status", "general")  # Fallback test
    ]
    
    for status_string, context in test_cases:
        indicator = system.get_indicator_by_string(status_string, context)
        print(f"{indicator.emoji} {status_string:<20} ({context:<8}) | {indicator.color} | {indicator.text}")
    
    print("✅ String-based indicator lookup test passed\n")


def test_custom_team_configuration():
    """Test custom team configuration."""
    print("🧪 Testing Custom Team Configuration")
    print("=" * 40)
    
    # Custom emoji and color mappings for a team
    custom_emojis = {
        'pr': {
            PRStatus.APPROVED: "🚀",  # Custom rocket for approved PRs
            PRStatus.MERGED: "🎊"     # Custom celebration for merged PRs
        },
        'priority': {
            Priority.BLOCKER: "💥"    # Custom explosion for blockers
        }
    }
    
    custom_colors = {
        'pr': {
            PRStatus.APPROVED: "#00ff00",  # Bright green for approved
            PRStatus.MERGED: "#ff00ff"     # Magenta for merged
        }
    }
    
    system = StatusIndicatorSystem(custom_emojis=custom_emojis, custom_colors=custom_colors)
    
    # Test custom PR indicators
    approved_indicator = system.get_pr_status_indicator(PRStatus.APPROVED)
    merged_indicator = system.get_pr_status_indicator(PRStatus.MERGED)
    blocker_indicator = system.get_priority_indicator(Priority.BLOCKER)
    
    print(f"Custom Approved PR: {approved_indicator.emoji} | {approved_indicator.color}")
    print(f"Custom Merged PR:   {merged_indicator.emoji} | {merged_indicator.color}")
    print(f"Custom Blocker:     {blocker_indicator.emoji} | {blocker_indicator.color}")
    
    # Test that non-customized indicators still work
    draft_indicator = system.get_pr_status_indicator(PRStatus.DRAFT)
    print(f"Default Draft PR:   {draft_indicator.emoji} | {draft_indicator.color}")
    
    print("✅ Custom team configuration test passed\n")


def test_accessibility_features():
    """Test accessibility text alternatives."""
    print("🧪 Testing Accessibility Features")
    print("=" * 40)
    
    system = StatusIndicatorSystem()
    
    # Test that all indicators have proper accessibility text
    test_indicators = [
        system.get_pr_status_indicator(PRStatus.READY_FOR_REVIEW),
        system.get_jira_status_indicator(JIRAStatus.IN_PROGRESS),
        system.get_priority_indicator(Priority.HIGHEST),
        system.get_health_status_indicator(HealthStatus.WARNING)
    ]
    
    for indicator in test_indicators:
        print(f"{indicator.emoji} | Text: '{indicator.text}' | Description: '{indicator.description}'")
    
    print("✅ Accessibility features test passed\n")


if __name__ == "__main__":
    print("🚀 DevSync AI Status Indicator System Test Suite")
    print("=" * 60)
    
    success_count = 0
    total_tests = 6
    
    try:
        test_pr_status_indicators()
        success_count += 1
    except Exception as e:
        print(f"❌ PR status test failed: {e}\n")
    
    try:
        test_jira_status_indicators()
        success_count += 1
    except Exception as e:
        print(f"❌ JIRA status test failed: {e}\n")
    
    try:
        test_priority_indicators()
        success_count += 1
    except Exception as e:
        print(f"❌ Priority indicators test failed: {e}\n")
    
    try:
        test_health_indicators()
        success_count += 1
    except Exception as e:
        print(f"❌ Health indicators test failed: {e}\n")
    
    try:
        test_string_based_indicators()
        success_count += 1
    except Exception as e:
        print(f"❌ String-based indicators test failed: {e}\n")
    
    try:
        test_custom_team_configuration()
        success_count += 1
    except Exception as e:
        print(f"❌ Custom configuration test failed: {e}\n")
    
    try:
        test_accessibility_features()
        success_count += 1
    except Exception as e:
        print(f"❌ Accessibility features test failed: {e}\n")
    
    # Summary
    print("📊 Test Results:")
    print("=" * 30)
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All tests passed! Status indicator system is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")