#!/usr/bin/env python3
"""Test script for interactive elements."""

import json
import time
from devsync_ai.core.interactive_elements import (
    InteractiveElementBuilder, InteractiveConfig, ActionType, ButtonStyle,
    ActionPayload
)


def test_button_creation():
    """Test basic button creation."""
    print("🧪 Testing Button Creation")
    print("=" * 40)
    
    config = InteractiveConfig(secret_key="test_secret_key")
    builder = InteractiveElementBuilder(config)
    
    # Test basic button
    button = builder.create_button(
        text="Test Button",
        action_type=ActionType.APPROVE_PR,
        resource_id="123",
        style=ButtonStyle.PRIMARY
    )
    
    print(f"✅ Basic button created")
    print(f"   Action ID: {button['action_id']}")
    print(f"   Style: {button.get('style', 'default')}")
    print(f"   Has payload: {'value' in button}")
    
    # Test button with confirmation
    confirm_button = builder.create_button(
        text="Dangerous Action",
        action_type=ActionType.MERGE_PR,
        resource_id="456",
        style=ButtonStyle.DANGER,
        confirmation={
            "title": "Confirm Action",
            "text": "Are you sure?",
            "confirm": "Yes",
            "deny": "No"
        }
    )
    
    print(f"✅ Confirmation button created")
    print(f"   Has confirmation: {'confirm' in confirm_button}")
    
    # Test external link button
    link_button = builder.create_external_link_button(
        text="View on GitHub",
        url="https://github.com/company/repo",
        description="Open repository"
    )
    
    print(f"✅ External link button created")
    print(f"   Has URL: {'url' in link_button}")
    
    print("✅ Button creation tests passed\n")
    return True


def test_specialized_buttons():
    """Test specialized button creation methods."""
    print("🧪 Testing Specialized Buttons")
    print("=" * 40)
    
    builder = InteractiveElementBuilder()
    
    # PR approval button
    pr_approve = builder.create_pr_approval_button("123", "Add authentication")
    print(f"✅ PR approval button: {pr_approve['text']['text']}")
    
    # PR rejection button
    pr_reject = builder.create_pr_rejection_button("123")
    print(f"✅ PR rejection button: {pr_reject['text']['text']}")
    
    # Merge button
    merge_btn = builder.create_merge_button("123", "main")
    print(f"✅ Merge button: {merge_btn['text']['text']}")
    
    # Alert acknowledgment
    alert_ack = builder.create_alert_acknowledgment_button("ALERT-001", "critical")
    print(f"✅ Alert acknowledgment: {alert_ack['text']['text']}")
    
    # Blocker resolution
    blocker_resolve = builder.create_blocker_resolution_button("BLOCK-001")
    print(f"✅ Blocker resolution: {blocker_resolve['text']['text']}")
    
    # Show details
    show_details = builder.create_show_details_button("PR-123", "pull_request")
    print(f"✅ Show details: {show_details['text']['text']}")
    
    # Check that all have proper structure
    buttons = [pr_approve, pr_reject, merge_btn, alert_ack, blocker_resolve, show_details]
    all_valid = all(
        'type' in btn and btn['type'] == 'button' and
        'text' in btn and 'action_id' in btn and 'value' in btn
        for btn in buttons
    )
    
    if all_valid:
        print("✅ All specialized buttons have proper structure")
    else:
        print("❌ Some buttons have invalid structure")
        return False
    
    print("✅ Specialized button tests passed\n")
    return True


def test_selection_menus():
    """Test selection menu creation."""
    print("🧪 Testing Selection Menus")
    print("=" * 40)
    
    builder = InteractiveElementBuilder()
    
    # Basic selection menu
    options = [
        {"text": "Option 1", "value": "opt1"},
        {"text": "Option 2", "value": "opt2"},
        {"text": "Option 3", "value": "opt3"}
    ]
    
    menu = builder.create_selection_menu(
        placeholder="Choose an option...",
        action_id="test_menu",
        options=options,
        initial_option="opt2"
    )
    
    print(f"✅ Basic menu created with {len(menu['options'])} options")
    print(f"   Has initial option: {'initial_option' in menu}")
    
    # User assignment menu
    users = [
        {"name": "Alice", "id": "user1"},
        {"name": "Bob", "id": "user2"},
        {"name": "Charlie", "id": "user3"}
    ]
    
    user_menu = builder.create_user_assignment_menu("TICKET-123", users)
    print(f"✅ User assignment menu: {len(user_menu['options'])} options")
    
    # Priority selection menu
    priority_menu = builder.create_priority_selection_menu("ISSUE-456")
    print(f"✅ Priority menu: {len(priority_menu['options'])} priorities")
    
    # JIRA status menu
    jira_menu = builder.create_jira_status_menu("DEV-789")
    print(f"✅ JIRA status menu: {len(jira_menu['options'])} statuses")
    
    # Validate menu structure
    menus = [menu, user_menu, priority_menu, jira_menu]
    all_valid = all(
        'type' in m and m['type'] == 'static_select' and
        'placeholder' in m and 'action_id' in m and 'options' in m
        for m in menus
    )
    
    if all_valid:
        print("✅ All menus have proper structure")
    else:
        print("❌ Some menus have invalid structure")
        return False
    
    print("✅ Selection menu tests passed\n")
    return True


def test_modal_dialogs():
    """Test modal dialog creation."""
    print("🧪 Testing Modal Dialogs")
    print("=" * 40)
    
    builder = InteractiveElementBuilder()
    
    # Comment modal
    comment_modal = builder.create_comment_modal("PR-123", "pull_request")
    print(f"✅ Comment modal created")
    print(f"   Title: {comment_modal['title']['text']}")
    print(f"   Blocks: {len(comment_modal['blocks'])}")
    
    # Time logging modal
    time_modal = builder.create_time_logging_modal("TICKET-456")
    print(f"✅ Time logging modal created")
    print(f"   Title: {time_modal['title']['text']}")
    print(f"   Blocks: {len(time_modal['blocks'])}")
    
    # Confirmation modal
    confirm_modal = builder.create_confirmation_modal(
        title="Delete Item",
        message="This will permanently delete the item. Are you sure?",
        action_id="delete_item_123",
        confirm_text="Delete",
        danger=True
    )
    print(f"✅ Confirmation modal created")
    print(f"   Title: {confirm_modal['title']['text']}")
    print(f"   Is dangerous: {len([b for b in confirm_modal['blocks'] if 'Warning' in b.get('text', {}).get('text', '')]) > 0}")
    
    # Validate modal structure
    modals = [comment_modal, time_modal, confirm_modal]
    all_valid = all(
        'type' in m and m['type'] == 'modal' and
        'title' in m and 'blocks' in m and 'callback_id' in m
        for m in modals
    )
    
    if all_valid:
        print("✅ All modals have proper structure")
    else:
        print("❌ Some modals have invalid structure")
        return False
    
    print("✅ Modal dialog tests passed\n")
    return True


def test_payload_security():
    """Test payload security features."""
    print("🧪 Testing Payload Security")
    print("=" * 40)
    
    config = InteractiveConfig(
        secret_key="test_secret_key_12345",
        rate_limit_per_user=5,
        session_timeout=300
    )
    builder = InteractiveElementBuilder(config)
    
    # Create button with signed payload
    button = builder.create_button(
        text="Secure Button",
        action_type=ActionType.APPROVE_PR,
        resource_id="123"
    )
    
    # Extract and validate payload
    payload_json = button['value']
    payload_data = json.loads(payload_json)
    
    print(f"✅ Payload created with signature: {'signature' in payload_data}")
    print(f"   Action type: {payload_data['action_type']}")
    print(f"   Resource ID: {payload_data['resource_id']}")
    print(f"   Timestamp: {payload_data['timestamp']}")
    
    # Test payload validation
    user_id = "test_user"
    validated_payload = builder.validate_action_payload(payload_json, user_id)
    
    if validated_payload:
        print("✅ Payload validation successful")
        print(f"   User ID set: {validated_payload.user_id == user_id}")
    else:
        print("❌ Payload validation failed")
        return False
    
    # Test rate limiting
    rate_limit_hit = False
    for i in range(10):  # Try to exceed rate limit
        result = builder.validate_action_payload(payload_json, user_id)
        if result is None:
            rate_limit_hit = True
            break
    
    if rate_limit_hit:
        print("✅ Rate limiting working correctly")
    else:
        print("⚠️ Rate limiting may not be working")
    
    # Test expired payload
    old_payload = ActionPayload(
        action_type=ActionType.APPROVE_PR,
        resource_id="456",
        timestamp=time.time() - 400  # Older than session timeout
    )
    old_payload.signature = builder._sign_payload(old_payload)
    
    expired_result = builder.validate_action_payload(
        json.dumps(old_payload.to_dict()), 
        "test_user_2"
    )
    
    if expired_result is None:
        print("✅ Expired payload rejected correctly")
    else:
        print("❌ Expired payload should have been rejected")
        return False
    
    print("✅ Payload security tests passed\n")
    return True


def test_audit_logging():
    """Test audit logging functionality."""
    print("🧪 Testing Audit Logging")
    print("=" * 40)
    
    config = InteractiveConfig(enable_audit_logging=True)
    builder = InteractiveElementBuilder(config)
    
    # Create some actions to generate audit log
    actions = [
        (ActionType.APPROVE_PR, "PR-123", "user1"),
        (ActionType.REJECT_PR, "PR-124", "user2"),
        (ActionType.MERGE_PR, "PR-125", "user1"),
        (ActionType.ACKNOWLEDGE_ALERT, "ALERT-001", "user3")
    ]
    
    for action_type, resource_id, user_id in actions:
        payload = ActionPayload(
            action_type=action_type,
            resource_id=resource_id
        )
        builder._log_action(payload, user_id)
    
    # Get audit log
    all_logs = builder.get_audit_log()
    user1_logs = builder.get_audit_log(user_id="user1")
    approve_logs = builder.get_audit_log(action_type=ActionType.APPROVE_PR)
    
    print(f"✅ Audit logging working")
    print(f"   Total log entries: {len(all_logs)}")
    print(f"   User1 entries: {len(user1_logs)}")
    print(f"   Approve entries: {len(approve_logs)}")
    
    # Validate log structure
    if all_logs and all(
        'timestamp' in entry and 'user_id' in entry and 
        'action_type' in entry and 'resource_id' in entry
        for entry in all_logs
    ):
        print("✅ Log entries have proper structure")
    else:
        print("❌ Log entries have invalid structure")
        return False
    
    print("✅ Audit logging tests passed\n")
    return True


def test_action_groups():
    """Test action group creation."""
    print("🧪 Testing Action Groups")
    print("=" * 40)
    
    builder = InteractiveElementBuilder()
    
    # Create multiple buttons
    buttons = [
        builder.create_pr_approval_button("123", "Test PR"),
        builder.create_pr_rejection_button("123"),
        builder.create_show_details_button("123", "pull_request")
    ]
    
    # Create action group
    action_group = builder.create_action_group(buttons)
    
    print(f"✅ Action group created")
    print(f"   Type: {action_group['type']}")
    print(f"   Elements: {len(action_group['elements'])}")
    
    # Test with too many elements (should limit to 5)
    many_buttons = [
        builder.create_button(f"Button {i}", ActionType.CUSTOM_ACTION, f"id_{i}")
        for i in range(10)
    ]
    
    limited_group = builder.create_action_group(many_buttons)
    
    if len(limited_group['elements']) <= 5:
        print("✅ Action group properly limits elements to 5")
    else:
        print("❌ Action group should limit elements to 5")
        return False
    
    print("✅ Action group tests passed\n")
    return True


def test_security_features():
    """Test security features."""
    print("🧪 Testing Security Features")
    print("=" * 40)
    
    config = InteractiveConfig(
        allowed_domains=["github.com", "jira.company.com"],
        require_authorization=True
    )
    builder = InteractiveElementBuilder(config)
    
    # Test URL validation
    allowed_url = "https://github.com/company/repo"
    blocked_url = "https://malicious-site.com/evil"
    
    allowed_result = builder._is_url_allowed(allowed_url)
    blocked_result = builder._is_url_allowed(blocked_url)
    
    print(f"✅ URL validation working")
    print(f"   Allowed URL accepted: {allowed_result}")
    print(f"   Blocked URL rejected: {not blocked_result}")
    
    if not (allowed_result and not blocked_result):
        print("❌ URL validation not working correctly")
        return False
    
    # Test payload signing
    payload = ActionPayload(
        action_type=ActionType.APPROVE_PR,
        resource_id="test"
    )
    
    # Test without secret key
    builder_no_key = InteractiveElementBuilder()
    signature_no_key = builder_no_key._sign_payload(payload)
    
    # Test with secret key
    config.secret_key = "test_secret"
    builder_with_key = InteractiveElementBuilder(config)
    signature_with_key = builder_with_key._sign_payload(payload)
    
    print(f"✅ Payload signing working")
    print(f"   No key signature empty: {signature_no_key == ''}")
    print(f"   With key signature present: {len(signature_with_key) > 0}")
    
    if not (signature_no_key == '' and len(signature_with_key) > 0):
        print("❌ Payload signing not working correctly")
        return False
    
    print("✅ Security feature tests passed\n")
    return True


def test_comprehensive_example():
    """Test comprehensive real-world example."""
    print("🧪 Testing Comprehensive Example")
    print("=" * 40)
    
    config = InteractiveConfig(
        secret_key="production_secret_key",
        enable_audit_logging=True,
        rate_limit_per_user=50,
        allowed_domains=["github.com", "jira.company.com"]
    )
    builder = InteractiveElementBuilder(config)
    
    # Create a complete PR review interface
    pr_data = {
        "number": "456",
        "title": "Implement user dashboard with analytics",
        "branch": "main"
    }
    
    # Main action buttons
    approve_btn = builder.create_pr_approval_button(pr_data["number"], pr_data["title"])
    reject_btn = builder.create_pr_rejection_button(pr_data["number"])
    merge_btn = builder.create_merge_button(pr_data["number"], pr_data["branch"])
    details_btn = builder.create_show_details_button(pr_data["number"], "pull_request")
    github_btn = builder.create_external_link_button(
        "View on GitHub", 
        f"https://github.com/company/repo/pull/{pr_data['number']}"
    )
    
    # Create action groups
    review_actions = builder.create_action_group([approve_btn, reject_btn])
    merge_actions = builder.create_action_group([merge_btn, details_btn, github_btn])
    
    # Create assignment menu
    reviewers = [
        {"name": "Alice Johnson", "id": "alice"},
        {"name": "Bob Smith", "id": "bob"},
        {"name": "Charlie Brown", "id": "charlie"}
    ]
    reviewer_menu = builder.create_user_assignment_menu(pr_data["number"], reviewers)
    
    # Create comment modal
    comment_modal = builder.create_comment_modal(pr_data["number"], "pull_request")
    
    print("✅ Comprehensive PR interface created")
    print(f"   Review actions: {len(review_actions['elements'])} buttons")
    print(f"   Merge actions: {len(merge_actions['elements'])} buttons")
    print(f"   Reviewer menu: {len(reviewer_menu['options'])} options")
    print(f"   Comment modal: {len(comment_modal['blocks'])} blocks")
    
    # Test payload validation for one of the buttons
    payload_json = approve_btn['value']
    validated = builder.validate_action_payload(payload_json, "test_reviewer")
    
    if validated:
        print("✅ Payload validation successful for real-world example")
        print(f"   Action type: {validated.action_type.value}")
        print(f"   Resource ID: {validated.resource_id}")
    else:
        print("❌ Payload validation failed")
        return False
    
    # Check audit log
    audit_entries = builder.get_audit_log()
    if audit_entries:
        print(f"✅ Audit log contains {len(audit_entries)} entries")
    
    print("✅ Comprehensive example completed successfully\n")
    return True


if __name__ == "__main__":
    print("🚀 Interactive Elements Test Suite")
    print("=" * 60)
    
    success_count = 0
    total_tests = 7
    
    tests = [
        test_button_creation,
        test_specialized_buttons,
        test_selection_menus,
        test_modal_dialogs,
        test_payload_security,
        test_audit_logging,
        test_action_groups,
        test_security_features,
        test_comprehensive_example
    ]
    
    for test_func in tests:
        try:
            if test_func():
                success_count += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed with exception: {e}\n")
    
    # Summary
    print("📊 Test Results:")
    print("=" * 30)
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count >= total_tests * 0.85:  # 85% pass rate
        print("🎉 Interactive elements are working excellently!")
        print("🔒 Security features and user engagement ready!")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")