"""
Tests for Slack message templates.
"""

import pytest
from datetime import datetime
from devsync_ai.services.slack_templates import (
    DailyStandupTemplate,
    PRStatusTemplate,
    create_standup_message,
    create_pr_status_message
)
from devsync_ai.services.pr_status_templates import (
    NewPRTemplate,
    PRReadyForReviewTemplate,
    PRApprovedTemplate,
    PRConflictsTemplate,
    PRMergedTemplate,
    PRClosedTemplate,
    create_pr_message_by_action
)


class TestDailyStandupTemplate:
    """Test daily standup template functionality."""
    
    def test_basic_standup_template(self):
        """Test basic standup template creation."""
        data = {
            "date": "2025-08-12",
            "team": "DevSync Team",
            "stats": {
                "prs_merged": 3,
                "prs_open": 5,
                "tickets_completed": 7,
                "tickets_in_progress": 12,
                "commits": 23
            },
            "team_members": [
                {
                    "name": "Alice",
                    "status": "active",
                    "yesterday": ["Completed user auth", "Fixed bug #123"],
                    "today": ["Start payment integration", "Code review"],
                    "blockers": []
                }
            ],
            "action_items": ["Deploy staging environment"]
        }
        
        template = DailyStandupTemplate(data)
        message = template.get_message()
        
        assert "blocks" in message
        assert "text" in message
        assert len(message["blocks"]) > 0
        
        # Check for header
        header_block = message["blocks"][0]
        assert header_block["type"] == "header"
        assert "Daily Standup" in header_block["text"]["text"]
    
    def test_standup_with_empty_data(self):
        """Test standup template with minimal data."""
        data = {
            "team": "Test Team",
            "stats": {},
            "team_members": [],
            "action_items": []
        }
        
        template = DailyStandupTemplate(data)
        message = template.get_message()
        
        assert "blocks" in message
        assert len(message["blocks"]) > 0
    
    def test_team_health_calculation(self):
        """Test team health indicator calculation."""
        # All active, no blockers
        data = {
            "team_members": [
                {"name": "Alice", "status": "active", "blockers": []},
                {"name": "Bob", "status": "active", "blockers": []}
            ]
        }
        template = DailyStandupTemplate(data)
        health = template._calculate_team_health()
        assert "All systems go" in health
        
        # Some blockers
        data["team_members"][0]["blockers"] = ["Waiting for approval"]
        template = DailyStandupTemplate(data)
        health = template._calculate_team_health()
        assert "Some issues" in health or "Needs attention" in health
    
    def test_progress_bar_creation(self):
        """Test progress bar creation."""
        template = DailyStandupTemplate({})
        
        # Test with valid data
        progress = template._create_progress_bar(7, 10)
        assert "7/10" in progress
        assert "70%" in progress
        
        # Test with zero total
        progress = template._create_progress_bar(0, 0)
        assert "No tickets" in progress


class TestPRStatusTemplate:
    """Test PR status template functionality."""
    
    def test_basic_pr_template(self):
        """Test basic PR template creation."""
        data = {
            "pr": {
                "id": 123,
                "title": "Add user authentication",
                "description": "Implements OAuth2 login flow",
                "author": "alice",
                "status": "open",
                "reviewers": ["bob", "carol"],
                "approved_by": [],
                "files_changed": 12,
                "additions": 234,
                "deletions": 45,
                "created_at": "2025-08-12T10:00:00Z",
                "ci_status": "passing"
            },
            "action": "opened"
        }
        
        template = PRStatusTemplate(data)
        message = template.get_message()
        
        assert "blocks" in message
        assert len(message["blocks"]) > 0
        
        # Check for header
        header_block = message["blocks"][0]
        assert header_block["type"] == "header"
        assert "PR #123" in header_block["text"]["text"]
    
    def test_pr_with_jira_tickets(self):
        """Test PR template with JIRA tickets."""
        data = {
            "pr": {
                "id": 123,
                "title": "Test PR",
                "author": "alice",
                "jira_tickets": ["DP-123", "DP-124"]
            },
            "action": "opened"
        }
        
        template = PRStatusTemplate(data)
        message = template.get_message()
        
        # Find the JIRA tickets section
        jira_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Related Tickets" in text:
                    jira_found = True
                    assert "DP-123" in text
                    assert "DP-124" in text
        
        assert jira_found, "JIRA tickets section not found"
    
    def test_pr_with_conflicts(self):
        """Test PR template with merge conflicts."""
        data = {
            "pr": {
                "id": 123,
                "title": "Test PR",
                "author": "alice",
                "has_conflicts": True,
                "ci_status": "failing"
            },
            "action": "has_conflicts"
        }
        
        template = PRStatusTemplate(data)
        message = template.get_message()
        
        # Check for conflict indicators
        conflict_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "conflicts" in text.lower():
                    conflict_found = True
        
        assert conflict_found, "Conflict indicator not found"


class TestSpecializedPRTemplates:
    """Test specialized PR templates for different scenarios."""
    
    def test_new_pr_template(self):
        """Test new PR template."""
        data = {
            "pr": {
                "id": 123,
                "title": "New Feature",
                "description": "Adding new functionality",
                "author": "alice",
                "status": "open"
            },
            "action": "opened"
        }
        
        template = NewPRTemplate(data)
        message = template.get_message()
        
        # Check for new PR specific elements
        header_block = message["blocks"][0]
        assert "New PR" in header_block["text"]["text"]
        
        # Check for new PR actions
        action_found = False
        for block in message["blocks"]:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "Review Now" in element.get("text", {}).get("text", ""):
                        action_found = True
        
        assert action_found, "Review Now button not found"
    
    def test_ready_for_review_template(self):
        """Test ready for review template."""
        data = {
            "pr": {
                "id": 123,
                "title": "Ready PR",
                "author": "alice",
                "reviewers": ["bob", "carol"],
                "status": "open"
            },
            "action": "ready_for_review"
        }
        
        template = PRReadyForReviewTemplate(data)
        message = template.get_message()
        
        # Check for ready for review elements
        ready_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "ready for review" in text.lower():
                    ready_found = True
        
        assert ready_found, "Ready for review message not found"
    
    def test_approved_template(self):
        """Test approved PR template."""
        data = {
            "pr": {
                "id": 123,
                "title": "Approved PR",
                "author": "alice",
                "approved_by": ["bob"],
                "ci_status": "passing",
                "has_conflicts": False,
                "required_approvals": 1
            },
            "action": "approved"
        }
        
        template = PRApprovedTemplate(data)
        message = template.get_message()
        
        # Check for approval elements
        approved_found = False
        for block in message["blocks"]:
            if block.get("type") == "header":
                text = block["text"].get("text", "")
                if "Approved" in text:
                    approved_found = True
        
        assert approved_found, "Approved header not found"
        
        # Check for merge button
        merge_found = False
        for block in message["blocks"]:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "Merge Now" in element.get("text", {}).get("text", ""):
                        merge_found = True
        
        assert merge_found, "Merge button not found"
    
    def test_conflicts_template(self):
        """Test conflicts PR template."""
        data = {
            "pr": {
                "id": 123,
                "title": "Conflicted PR",
                "author": "alice",
                "has_conflicts": True
            },
            "action": "has_conflicts"
        }
        
        template = PRConflictsTemplate(data)
        message = template.get_message()
        
        # Check for conflict guidance
        guidance_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "resolve conflicts" in text.lower():
                    guidance_found = True
        
        assert guidance_found, "Conflict resolution guidance not found"
    
    def test_merged_template(self):
        """Test merged PR template."""
        data = {
            "pr": {
                "id": 123,
                "title": "Merged PR",
                "author": "alice",
                "jira_tickets": ["DP-123"]
            },
            "action": "merged",
            "deployment_status": "deployed"
        }
        
        template = PRMergedTemplate(data)
        message = template.get_message()
        
        # Check for merge celebration
        merged_found = False
        for block in message["blocks"]:
            if block.get("type") == "header":
                text = block["text"].get("text", "")
                if "Merged" in text:
                    merged_found = True
        
        assert merged_found, "Merged header not found"
        
        # Check for deployment status
        deployment_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Deployment" in text:
                    deployment_found = True
        
        assert deployment_found, "Deployment status not found"
    
    def test_closed_template(self):
        """Test closed PR template."""
        data = {
            "pr": {
                "id": 123,
                "title": "Closed PR",
                "author": "alice"
            },
            "action": "closed",
            "close_reason": "Superseded by another PR"
        }
        
        template = PRClosedTemplate(data)
        message = template.get_message()
        
        # Check for closure message
        closed_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "closed" in text.lower() and "Superseded" in text:
                    closed_found = True
        
        assert closed_found, "Closure message not found"


class TestTemplateFactory:
    """Test template factory functions."""
    
    def test_create_standup_message(self):
        """Test standup message creation function."""
        data = {
            "team": "Test Team",
            "stats": {"prs_merged": 1},
            "team_members": [],
            "action_items": []
        }
        
        message = create_standup_message(data)
        assert "blocks" in message
        assert "text" in message
    
    def test_create_pr_status_message(self):
        """Test PR status message creation function."""
        data = {
            "pr": {
                "id": 123,
                "title": "Test PR",
                "author": "alice"
            },
            "action": "opened"
        }
        
        message = create_pr_status_message(data)
        assert "blocks" in message
        assert "text" in message
    
    def test_create_pr_message_by_action(self):
        """Test PR message creation by action type."""
        base_data = {
            "pr": {
                "id": 123,
                "title": "Test PR",
                "author": "alice"
            }
        }
        
        actions = [
            "opened",
            "ready_for_review",
            "approved",
            "has_conflicts",
            "merged",
            "closed"
        ]
        
        for action in actions:
            data = {**base_data, "action": action}
            message = create_pr_message_by_action(data)
            
            assert "blocks" in message
            assert "text" in message
            assert len(message["blocks"]) > 0


class TestTemplateValidation:
    """Test template validation and error handling."""
    
    def test_empty_data_handling(self):
        """Test templates handle empty data gracefully."""
        # Empty standup data
        standup_message = create_standup_message({})
        assert "blocks" in standup_message
        
        # Empty PR data
        pr_message = create_pr_status_message({"pr": {}, "action": "opened"})
        assert "blocks" in pr_message
    
    def test_missing_required_fields(self):
        """Test templates handle missing required fields."""
        # PR without ID
        data = {
            "pr": {
                "title": "Test PR",
                "author": "alice"
            },
            "action": "opened"
        }
        
        message = create_pr_status_message(data)
        assert "blocks" in message
        
        # Should handle missing ID gracefully
        header_found = False
        for block in message["blocks"]:
            if block.get("type") == "header":
                text = block["text"].get("text", "")
                if "PR #N/A" in text or "PR #" in text:
                    header_found = True
        
        assert header_found, "Header not found or doesn't handle missing ID"
    
    def test_malformed_timestamps(self):
        """Test templates handle malformed timestamps."""
        data = {
            "pr": {
                "id": 123,
                "title": "Test PR",
                "author": "alice",
                "created_at": "invalid-timestamp",
                "updated_at": "also-invalid"
            },
            "action": "opened"
        }
        
        # Should not raise exception
        message = create_pr_status_message(data)
        assert "blocks" in message


if __name__ == "__main__":
    # Run some basic tests
    print("Testing Slack Templates...")
    
    # Test standup template
    standup_data = {
        "date": "2025-08-12",
        "team": "DevSync Team",
        "stats": {
            "prs_merged": 3,
            "prs_open": 5,
            "tickets_completed": 7,
            "tickets_in_progress": 12,
            "commits": 23
        },
        "team_members": [
            {
                "name": "Alice",
                "status": "active",
                "yesterday": ["Completed user auth", "Fixed bug #123"],
                "today": ["Start payment integration", "Code review"],
                "blockers": []
            },
            {
                "name": "Bob",
                "status": "active",
                "yesterday": ["Database optimization"],
                "today": ["API documentation"],
                "blockers": ["Waiting for design approval"]
            }
        ],
        "action_items": ["Deploy staging environment", "Update documentation"]
    }
    
    standup_message = create_standup_message(standup_data)
    print(f"Standup template created with {len(standup_message['blocks'])} blocks")
    
    # Test different PR scenarios
    pr_scenarios = [
        ("opened", "New PR opened"),
        ("ready_for_review", "PR ready for review"),
        ("approved", "PR approved"),
        ("has_conflicts", "PR has conflicts"),
        ("merged", "PR merged"),
        ("closed", "PR closed")
    ]
    
    for action, description in pr_scenarios:
        pr_data = {
            "pr": {
                "id": 123,
                "title": f"Test PR - {description}",
                "description": f"This is a test PR for {description}",
                "author": "alice",
                "status": "open" if action != "merged" else "merged",
                "reviewers": ["bob", "carol"],
                "approved_by": ["bob"] if action in ["approved", "merged"] else [],
                "has_conflicts": action == "has_conflicts",
                "files_changed": 12,
                "additions": 234,
                "deletions": 45,
                "created_at": "2025-08-12T10:00:00Z",
                "updated_at": "2025-08-12T14:30:00Z",
                "jira_tickets": ["DP-123", "DP-124"],
                "ci_status": "passing" if action != "has_conflicts" else "failing"
            },
            "action": action
        }
        
        if action == "closed":
            pr_data["close_reason"] = "Superseded by another PR"
        elif action == "merged":
            pr_data["deployment_status"] = "deployed"
        
        message = create_pr_message_by_action(pr_data)
        print(f"{description} template created with {len(message['blocks'])} blocks")
    
    print("All templates created successfully!")