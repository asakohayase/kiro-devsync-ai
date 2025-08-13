"""
Tests for JIRA message templates.
"""

import pytest
from datetime import datetime
from devsync_ai.services.jira_templates import (
    JIRAStatusChangeTemplate,
    JIRAPriorityChangeTemplate,
    JIRAAssignmentChangeTemplate,
    JIRACommentTemplate,
    JIRABlockerTemplate,
    JIRASprintChangeTemplate,
    create_jira_message,
    create_status_change_message,
    create_priority_change_message,
    create_assignment_change_message,
    create_comment_message,
    create_blocker_message,
    create_sprint_change_message
)


class TestJIRATemplateBase:
    """Test JIRA template base functionality."""
    
    def test_priority_emoji_mapping(self):
        """Test priority emoji mapping."""
        from devsync_ai.services.jira_templates import JIRATemplateBase
        
        template = JIRATemplateBase({})
        
        assert template._get_priority_emoji('blocker') == '🚨'
        assert template._get_priority_emoji('critical') == '🔴'
        assert template._get_priority_emoji('high') == '🟠'
        assert template._get_priority_emoji('medium') == '🟡'
        assert template._get_priority_emoji('low') == '🟢'
        assert template._get_priority_emoji('unknown') == '🟡'  # default
    
    def test_status_emoji_mapping(self):
        """Test status emoji mapping."""
        from devsync_ai.services.jira_templates import JIRATemplateBase
        
        template = JIRATemplateBase({})
        
        assert template._get_status_emoji('to do') == '📋'
        assert template._get_status_emoji('in progress') == '⏳'
        assert template._get_status_emoji('done') == '✅'
        assert template._get_status_emoji('blocked') == '🚫'
        assert template._get_status_emoji('unknown') == '📄'  # default
    
    def test_status_transition_visual(self):
        """Test status transition visualization."""
        from devsync_ai.services.jira_templates import JIRATemplateBase
        
        template = JIRATemplateBase({})
        visual = template._create_status_transition_visual('To Do', 'In Progress')
        
        assert '📋 To Do → ⏳ In Progress' == visual
    
    def test_time_duration_formatting(self):
        """Test time duration formatting."""
        from devsync_ai.services.jira_templates import JIRATemplateBase
        
        template = JIRATemplateBase({})
        
        assert template._format_time_duration('2h 30m') == '2h 30m'
        assert template._format_time_duration('0h') == 'None'
        assert template._format_time_duration('') == 'None'
        assert template._format_time_duration(None) == 'None'


class TestJIRAStatusChangeTemplate:
    """Test JIRA status change template."""
    
    def test_status_change_template(self):
        """Test basic status change template."""
        data = {
            "ticket": {
                "key": "DP-123",
                "summary": "Implement user dashboard",
                "status": {
                    "from": "To Do",
                    "to": "In Progress"
                },
                "assignee": "alice",
                "reporter": "bob",
                "priority": "High"
            },
            "change_type": "status_change"
        }
        
        template = JIRAStatusChangeTemplate(data)
        message = template.get_message()
        
        assert "blocks" in message
        assert len(message["blocks"]) > 0
        
        # Check for header
        header_found = False
        for block in message["blocks"]:
            if block.get("type") == "header":
                header_found = True
                assert "DP-123" in block["text"]["text"]
        
        assert header_found, "Header not found"
        
        # Check for status transition
        transition_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Status Changed" in text and "→" in text:
                    transition_found = True
        
        assert transition_found, "Status transition not found"
    
    def test_workflow_context_messages(self):
        """Test workflow context messages."""
        data = {
            "ticket": {
                "key": "DP-123",
                "summary": "Test ticket",
                "status": {
                    "from": "To Do",
                    "to": "In Progress"
                },
                "assignee": "alice"
            }
        }
        
        template = JIRAStatusChangeTemplate(data)
        message = template.get_message()
        
        # Check for workflow message
        workflow_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Work has started" in text:
                    workflow_found = True
        
        assert workflow_found, "Workflow context message not found"


class TestJIRAPriorityChangeTemplate:
    """Test JIRA priority change template."""
    
    def test_priority_change_template(self):
        """Test priority change template."""
        data = {
            "ticket": {
                "key": "DP-124",
                "summary": "Fix critical bug",
                "priority_change": {
                    "from": "Medium",
                    "to": "Critical"
                },
                "assignee": "bob"
            },
            "change_type": "priority_change"
        }
        
        template = JIRAPriorityChangeTemplate(data)
        message = template.get_message()
        
        assert "blocks" in message
        
        # Check for priority change visualization
        priority_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Priority Changed" in text and "🟡 Medium → 🔴 Critical" in text:
                    priority_found = True
        
        assert priority_found, "Priority change visualization not found"
        
        # Check for urgency message
        urgency_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "HIGH PRIORITY" in text:
                    urgency_found = True
        
        assert urgency_found, "Urgency message not found"


class TestJIRAAssignmentChangeTemplate:
    """Test JIRA assignment change template."""
    
    def test_assignment_change_template(self):
        """Test assignment change template."""
        data = {
            "ticket": {
                "key": "DP-125",
                "summary": "Update documentation",
                "assignment_change": {
                    "from": "alice",
                    "to": "bob"
                },
                "assignee": "bob"
            },
            "change_type": "assignment_change"
        }
        
        template = JIRAAssignmentChangeTemplate(data)
        message = template.get_message()
        
        assert "blocks" in message
        
        # Check for assignment change
        assignment_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Reassigned" in text and "@alice → @bob" in text:
                    assignment_found = True
        
        assert assignment_found, "Assignment change not found"
        
        # Check for new assignee notification
        notification_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Hey @bob" in text:
                    notification_found = True
        
        assert notification_found, "New assignee notification not found"
    
    def test_unassignment(self):
        """Test unassignment scenario."""
        data = {
            "ticket": {
                "key": "DP-126",
                "summary": "Test unassignment",
                "assignment_change": {
                    "from": "alice",
                    "to": "Unassigned"
                }
            }
        }
        
        template = JIRAAssignmentChangeTemplate(data)
        message = template.get_message()
        
        # Check for unassignment message
        unassign_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Unassigned from" in text:
                    unassign_found = True
        
        assert unassign_found, "Unassignment message not found"


class TestJIRACommentTemplate:
    """Test JIRA comment template."""
    
    def test_comment_template(self):
        """Test comment template."""
        data = {
            "ticket": {
                "key": "DP-127",
                "summary": "Test comment",
                "assignee": "alice",
                "comments": [
                    {
                        "author": "bob",
                        "text": "This looks good to me, ready for testing",
                        "created": "2025-08-12T15:30:00Z"
                    }
                ]
            },
            "change_type": "comment_added"
        }
        
        template = JIRACommentTemplate(data)
        message = template.get_message()
        
        assert "blocks" in message
        
        # Check for comment content
        comment_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "New comment by @bob" in text and "ready for testing" in text:
                    comment_found = True
        
        assert comment_found, "Comment content not found"
    
    def test_multiple_comments(self):
        """Test template with multiple comments."""
        data = {
            "ticket": {
                "key": "DP-128",
                "summary": "Test multiple comments",
                "comments": [
                    {
                        "author": "alice",
                        "text": "First comment",
                        "created": "2025-08-12T14:00:00Z"
                    },
                    {
                        "author": "bob",
                        "text": "Second comment",
                        "created": "2025-08-12T15:00:00Z"
                    }
                ]
            }
        }
        
        template = JIRACommentTemplate(data)
        message = template.get_message()
        
        # Check for comment history
        history_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Comment History" in text and "2 total comments" in text:
                    history_found = True
        
        assert history_found, "Comment history not found"


class TestJIRABlockerTemplate:
    """Test JIRA blocker template."""
    
    def test_blocker_identified_template(self):
        """Test blocker identified template."""
        data = {
            "ticket": {
                "key": "DP-129",
                "summary": "Blocked ticket",
                "assignee": "alice"
            },
            "blocker": {
                "type": "identified",
                "description": "Waiting for API access from external team"
            },
            "change_type": "blocker_identified"
        }
        
        template = JIRABlockerTemplate(data)
        message = template.get_message()
        
        assert "blocks" in message
        
        # Check for blocker message
        blocker_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Blocker Identified" in text and "API access" in text:
                    blocker_found = True
        
        assert blocker_found, "Blocker message not found"
        
        # Check for escalate button
        escalate_found = False
        for block in message["blocks"]:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "Escalate" in element.get("text", {}).get("text", ""):
                        escalate_found = True
        
        assert escalate_found, "Escalate button not found"
    
    def test_blocker_resolved_template(self):
        """Test blocker resolved template."""
        data = {
            "ticket": {
                "key": "DP-130",
                "summary": "Unblocked ticket",
                "assignee": "alice"
            },
            "blocker": {
                "type": "resolved",
                "description": "API access has been granted"
            },
            "change_type": "blocker_resolved"
        }
        
        template = JIRABlockerTemplate(data)
        message = template.get_message()
        
        # Check for resolution message
        resolved_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Blocker Resolved" in text and "Work can now continue" in text:
                    resolved_found = True
        
        assert resolved_found, "Blocker resolved message not found"
        
        # Check for resume work button
        resume_found = False
        for block in message["blocks"]:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "Resume Work" in element.get("text", {}).get("text", ""):
                        resume_found = True
        
        assert resume_found, "Resume work button not found"


class TestJIRASprintChangeTemplate:
    """Test JIRA sprint change template."""
    
    def test_sprint_change_template(self):
        """Test sprint change template."""
        data = {
            "ticket": {
                "key": "DP-131",
                "summary": "Sprint moved ticket",
                "assignee": "alice",
                "sprint_change": {
                    "from": "Sprint 4",
                    "to": "Sprint 5",
                    "type": "moved"
                }
            },
            "sprint_info": {
                "name": "Sprint 5",
                "start_date": "2025-08-12",
                "end_date": "2025-08-26",
                "capacity": 40,
                "committed_points": 32
            },
            "change_type": "sprint_change"
        }
        
        template = JIRASprintChangeTemplate(data)
        message = template.get_message()
        
        assert "blocks" in message
        
        # Check for sprint change message
        sprint_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Sprint Changed" in text and "Sprint 4 → Sprint 5" in text:
                    sprint_found = True
        
        assert sprint_found, "Sprint change message not found"
        
        # Check for sprint context
        context_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Sprint Context" in text and "32/40 story points" in text:
                    context_found = True
        
        assert context_found, "Sprint context not found"


class TestJIRATemplateFactory:
    """Test JIRA template factory functions."""
    
    def test_create_jira_message_factory(self):
        """Test main factory function."""
        data = {
            "ticket": {
                "key": "DP-132",
                "summary": "Factory test",
                "status": {"from": "To Do", "to": "Done"}
            },
            "change_type": "status_change"
        }
        
        message = create_jira_message(data)
        assert "blocks" in message
        assert "text" in message
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        base_data = {
            "ticket": {
                "key": "DP-133",
                "summary": "Convenience test",
                "assignee": "alice"
            }
        }
        
        # Test all convenience functions
        functions_to_test = [
            (create_status_change_message, {"status": {"from": "To Do", "to": "Done"}}),
            (create_priority_change_message, {"priority_change": {"from": "Low", "to": "High"}}),
            (create_assignment_change_message, {"assignment_change": {"from": "alice", "to": "bob"}}),
            (create_comment_message, {"comments": [{"author": "alice", "text": "Test comment"}]}),
            (create_sprint_change_message, {"sprint_change": {"from": "Sprint 1", "to": "Sprint 2"}})
        ]
        
        for func, extra_data in functions_to_test:
            test_data = {**base_data}
            test_data["ticket"].update(extra_data)
            
            message = func(test_data)
            assert "blocks" in message
            assert "text" in message
    
    def test_blocker_convenience_function(self):
        """Test blocker convenience function."""
        data = {
            "ticket": {
                "key": "DP-134",
                "summary": "Blocker test",
                "assignee": "alice"
            },
            "blocker": {
                "description": "Test blocker"
            }
        }
        
        # Test both blocker types
        identified_msg = create_blocker_message(data, "identified")
        resolved_msg = create_blocker_message(data, "resolved")
        
        assert "blocks" in identified_msg
        assert "blocks" in resolved_msg


class TestJIRATemplateValidation:
    """Test JIRA template validation and error handling."""
    
    def test_empty_data_handling(self):
        """Test templates handle empty data gracefully."""
        empty_data = {"ticket": {}, "change_type": "status_change"}
        
        message = create_jira_message(empty_data)
        assert "blocks" in message
        assert "text" in message
    
    def test_missing_required_fields(self):
        """Test templates handle missing required fields."""
        minimal_data = {
            "ticket": {
                "summary": "Test ticket"
                # Missing key, assignee, etc.
            },
            "change_type": "status_change"
        }
        
        message = create_jira_message(minimal_data)
        assert "blocks" in message
        
        # Should handle missing key gracefully
        header_found = False
        for block in message["blocks"]:
            if block.get("type") == "header":
                text = block["text"].get("text", "")
                if "Unknown:" in text or "Test ticket" in text:
                    header_found = True
        
        assert header_found, "Header not found or doesn't handle missing key"
    
    def test_malformed_timestamps(self):
        """Test templates handle malformed timestamps."""
        data = {
            "ticket": {
                "key": "DP-135",
                "summary": "Timestamp test",
                "updated": "invalid-timestamp",
                "comments": [
                    {
                        "author": "alice",
                        "text": "Test comment",
                        "created": "also-invalid"
                    }
                ]
            },
            "change_type": "comment_added"
        }
        
        # Should not raise exception
        message = create_jira_message(data)
        assert "blocks" in message


if __name__ == "__main__":
    # Run some basic tests
    print("Testing JIRA Templates...")
    
    # Test status change
    status_data = {
        "ticket": {
            "key": "DP-123",
            "summary": "Implement user dashboard",
            "status": {"from": "To Do", "to": "In Progress"},
            "assignee": "alice",
            "priority": "High"
        },
        "change_type": "status_change"
    }
    
    status_message = create_jira_message(status_data)
    print(f"Status change template created with {len(status_message['blocks'])} blocks")
    
    # Test priority change
    priority_data = {
        "ticket": {
            "key": "DP-124",
            "summary": "Fix critical bug",
            "priority_change": {"from": "Medium", "to": "Critical"},
            "assignee": "bob"
        },
        "change_type": "priority_change"
    }
    
    priority_message = create_jira_message(priority_data)
    print(f"Priority change template created with {len(priority_message['blocks'])} blocks")
    
    # Test all change types
    change_types = [
        "status_change",
        "priority_change", 
        "assignment_change",
        "comment_added",
        "blocker_identified",
        "blocker_resolved",
        "sprint_change"
    ]
    
    for change_type in change_types:
        test_data = {
            "ticket": {
                "key": f"DP-{hash(change_type) % 1000}",
                "summary": f"Test {change_type}",
                "assignee": "alice"
            },
            "change_type": change_type
        }
        
        # Add specific data for each type
        if change_type == "status_change":
            test_data["ticket"]["status"] = {"from": "To Do", "to": "Done"}
        elif change_type == "priority_change":
            test_data["ticket"]["priority_change"] = {"from": "Low", "to": "High"}
        elif change_type == "assignment_change":
            test_data["ticket"]["assignment_change"] = {"from": "alice", "to": "bob"}
        elif change_type == "comment_added":
            test_data["ticket"]["comments"] = [{"author": "alice", "text": "Test comment"}]
        elif "blocker" in change_type:
            test_data["blocker"] = {"type": change_type.split("_")[1], "description": "Test blocker"}
        elif change_type == "sprint_change":
            test_data["ticket"]["sprint_change"] = {"from": "Sprint 1", "to": "Sprint 2"}
        
        message = create_jira_message(test_data)
        print(f"{change_type} template created with {len(message['blocks'])} blocks")
    
    print("All JIRA templates created successfully!")