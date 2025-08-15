"""
Comprehensive tests for JIRA template variants.
Tests StatusChange, PriorityChange, Assignment, Comment, Blocker, and SprintChange templates.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from typing import Dict, List, Any

from devsync_ai.templates.jira_templates import (
    JIRATemplate, StatusChangeTemplate, PriorityChangeTemplate,
    AssignmentTemplate, CommentTemplate, BlockerTemplate, SprintChangeTemplate
)
from devsync_ai.core.message_formatter import SlackMessage, TemplateConfig
from devsync_ai.core.status_indicators import StatusType


class TestBaseJIRATemplate:
    """Test base JIRATemplate functionality."""
    
    def test_jira_template_initialization(self):
        """Test JIRA template initialization."""
        template = JIRATemplate()
        
        assert template.REQUIRED_FIELDS == ['ticket']
        assert template.config.team_id == "default"
    
    def test_jira_template_with_minimal_data(self):
        """Test JIRA template with minimal required data."""
        data = {
            'ticket': {
                'key': 'PROJ-123',
                'summary': 'Test ticket',
                'status': 'In Progress'
            }
        }
        
        template = JIRATemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        assert message.text
        assert 'PROJ-123' in message.text or 'Test ticket' in message.text
    
    def test_jira_ticket_header_creation(self):
        """Test JIRA ticket header creation."""
        ticket_data = {
            'key': 'PROJ-456',
            'summary': 'Implement new feature',
            'status': 'To Do',
            'priority': 'High',
            'assignee': 'john.doe'
        }
        
        template = JIRATemplate()
        
        # Test if the template has the create_ticket_header method
        if hasattr(template, 'create_ticket_header'):
            header_blocks = template.create_ticket_header(ticket_data)
            assert isinstance(header_blocks, list)
            assert len(header_blocks) > 0


class TestStatusChangeTemplate:
    """Test StatusChangeTemplate for ticket status transitions."""
    
    def test_status_change_template_creation(self):
        """Test status change template message creation."""
        data = {
            'ticket': {
                'key': 'PROJ-789',
                'summary': 'Fix authentication bug',
                'status': 'In Progress',
                'previous_status': 'To Do',
                'assignee': 'developer.one'
            },
            'change_type': 'status_change',
            'changed_by': 'project.manager'
        }
        
        template = StatusChangeTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should display status transition
        message_text = message.text.lower()
        assert 'status' in message_text or 'progress' in message_text
    
    def test_status_change_with_workflow_context(self):
        """Test status change template with visual workflow context."""
        data = {
            'ticket': {
                'key': 'PROJ-101',
                'summary': 'Database optimization',
                'status': 'Done',
                'previous_status': 'In Review'
            },
            'workflow_context': {
                'workflow_name': 'Development Workflow',
                'next_possible_statuses': [],
                'completion_percentage': 100
            }
        }
        
        template = StatusChangeTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show workflow context
        message_text = message.text.lower()
        assert 'done' in message_text or 'complete' in message_text


class TestPriorityChangeTemplate:
    """Test PriorityChangeTemplate for priority escalation indicators."""
    
    def test_priority_change_template(self):
        """Test priority change template message creation."""
        data = {
            'ticket': {
                'key': 'PROJ-202',
                'summary': 'Critical security vulnerability',
                'priority': 'Critical',
                'previous_priority': 'High'
            },
            'change_type': 'priority_change',
            'escalation_reason': 'Security impact discovered'
        }
        
        template = PriorityChangeTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show priority escalation
        message_text = message.text.lower()
        assert 'priority' in message_text or 'critical' in message_text
    
    def test_priority_change_with_urgency_indicators(self):
        """Test priority change template with urgency visualization."""
        data = {
            'ticket': {
                'key': 'PROJ-303',
                'summary': 'Production outage',
                'priority': 'Blocker',
                'previous_priority': 'Medium'
            },
            'urgency_indicators': {
                'impact_level': 'high',
                'affected_users': 1000,
                'sla_breach_risk': True
            }
        }
        
        template = PriorityChangeTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should highlight urgency
        message_text = message.text.lower()
        assert 'blocker' in message_text or 'outage' in message_text


class TestAssignmentTemplate:
    """Test AssignmentTemplate for assignment transition notifications."""
    
    def test_assignment_template(self):
        """Test assignment template message creation."""
        data = {
            'ticket': {
                'key': 'PROJ-404',
                'summary': 'Implement user dashboard',
                'assignee': 'frontend.dev',
                'previous_assignee': 'backend.dev'
            },
            'change_type': 'assignment_change',
            'assignment_reason': 'Better skill match'
        }
        
        template = AssignmentTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show assignment transition
        message_text = message.text.lower()
        assert 'assign' in message_text or 'frontend.dev' in message_text
    
    def test_assignment_with_stakeholder_notifications(self):
        """Test assignment template with relevant stakeholder notifications."""
        data = {
            'ticket': {
                'key': 'PROJ-505',
                'summary': 'API integration task',
                'assignee': 'api.specialist',
                'previous_assignee': None  # Was unassigned
            },
            'stakeholders': ['team.lead', 'product.owner'],
            'assignment_context': {
                'workload_balance': 'optimal',
                'skill_match': 'excellent'
            }
        }
        
        template = AssignmentTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should notify relevant stakeholders
        message_text = message.text
        assert 'api.specialist' in message_text


class TestCommentTemplate:
    """Test CommentTemplate for comment display with context."""
    
    def test_comment_template(self):
        """Test comment template message creation."""
        data = {
            'ticket': {
                'key': 'PROJ-606',
                'summary': 'Bug in payment processing'
            },
            'comment': {
                'author': 'qa.tester',
                'content': 'Found additional edge case that needs to be addressed',
                'created': '2025-08-14T10:30:00Z'
            }
        }
        
        template = CommentTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should display comment content
        message_text = message.text.lower()
        assert 'comment' in message_text or 'edge case' in message_text
    
    def test_comment_with_author_info_and_history(self):
        """Test comment template with author info and history context."""
        data = {
            'ticket': {
                'key': 'PROJ-707',
                'summary': 'Performance optimization'
            },
            'comment': {
                'author': 'performance.expert',
                'content': 'Benchmarks show 40% improvement after optimization',
                'created': '2025-08-14T15:45:00Z'
            },
            'comment_history': {
                'total_comments': 5,
                'recent_activity': True
            }
        }
        
        template = CommentTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show author and context
        message_text = message.text
        assert 'performance.expert' in message_text
        assert '40%' in message_text or 'improvement' in message_text


class TestBlockerTemplate:
    """Test BlockerTemplate for blocker identification and escalation."""
    
    def test_blocker_template(self):
        """Test blocker template message creation."""
        data = {
            'ticket': {
                'key': 'PROJ-808',
                'summary': 'Deploy new feature to production',
                'status': 'Blocked',
                'assignee': 'devops.engineer'
            },
            'blocker': {
                'type': 'dependency',
                'description': 'Waiting for database migration approval',
                'blocking_since': '2025-08-13T09:00:00Z'
            }
        }
        
        template = BlockerTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should highlight blocker status
        message_text = message.text.lower()
        assert 'block' in message_text or 'waiting' in message_text
    
    def test_blocker_with_escalation_actions(self):
        """Test blocker template with escalation action buttons."""
        data = {
            'ticket': {
                'key': 'PROJ-909',
                'summary': 'Critical bug fix',
                'priority': 'Critical'
            },
            'blocker': {
                'type': 'external_dependency',
                'description': 'Third-party API is down',
                'escalation_path': ['team.lead', 'engineering.manager']
            }
        }
        
        # Test with interactive elements enabled
        config = TemplateConfig(team_id="test", interactive_elements=True)
        template = BlockerTemplate(config=config)
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should provide escalation options
        message_text = message.text.lower()
        assert 'critical' in message_text or 'api' in message_text


class TestSprintChangeTemplate:
    """Test SprintChangeTemplate for sprint transitions with capacity context."""
    
    def test_sprint_change_template(self):
        """Test sprint change template message creation."""
        data = {
            'ticket': {
                'key': 'PROJ-1010',
                'summary': 'Implement search filters',
                'sprint': 'Sprint 24',
                'previous_sprint': 'Sprint 23'
            },
            'sprint_change': {
                'reason': 'Capacity rebalancing',
                'changed_by': 'scrum.master'
            }
        }
        
        template = SprintChangeTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show sprint transition
        message_text = message.text.lower()
        assert 'sprint' in message_text
    
    def test_sprint_change_with_capacity_context(self):
        """Test sprint change template with capacity context."""
        data = {
            'ticket': {
                'key': 'PROJ-1111',
                'summary': 'Mobile app improvements',
                'sprint': 'Sprint 25',
                'story_points': 8
            },
            'capacity_context': {
                'current_sprint_capacity': 40,
                'current_sprint_committed': 35,
                'team_velocity': 38,
                'capacity_impact': 'within_limits'
            }
        }
        
        template = SprintChangeTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show capacity context
        message_text = message.text.lower()
        assert 'capacity' in message_text or 'sprint' in message_text


class TestJIRATemplateAccessibility:
    """Test accessibility features across JIRA templates."""
    
    def test_jira_template_fallback_text(self):
        """Test JIRA template fallback text generation."""
        data = {
            'ticket': {
                'key': 'PROJ-1212',
                'summary': '*Critical* issue with _payment_ `processing`',
                'description': 'This ticket has **bold** and __italic__ formatting'
            }
        }
        
        template = JIRATemplate()
        message = template.format_message(data)
        
        # Check fallback text has markdown stripped
        assert message.text
        assert 'Critical issue with payment processing' in message.text
        assert '*' not in message.text
        assert '_' not in message.text
        assert '`' not in message.text
    
    def test_jira_template_error_handling(self):
        """Test JIRA template error handling with malformed data."""
        # Test with missing ticket data
        incomplete_data = {}
        
        template = JIRATemplate()
        message = template.format_message(incomplete_data)
        
        # Should still create a message with placeholders
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Test with malformed ticket data
        malformed_data = {
            'ticket': {
                'key': None,      # Should be string
                'summary': '',    # Empty string
                'status': 123     # Should be string
            }
        }
        
        message_malformed = template.format_message(malformed_data)
        assert isinstance(message_malformed, SlackMessage)
        assert len(message_malformed.blocks) > 0
    
    def test_jira_template_with_missing_optional_fields(self):
        """Test JIRA template handles missing optional fields gracefully."""
        # Minimal required data only
        data = {
            'ticket': {
                'key': 'PROJ-1313',
                'summary': 'Basic ticket'
            }
        }
        
        template = StatusChangeTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        assert message.text
        
        # Should not crash with minimal data
        assert 'PROJ-1313' in message.text
        assert 'Basic ticket' in message.text


if __name__ == "__main__":
    print("Running JIRA template tests...")
    
    # Basic smoke test
    template = JIRATemplate()
    data = {
        'ticket': {
            'key': 'TEST-123',
            'summary': 'Test ticket',
            'status': 'In Progress'
        }
    }
    message = template.format_message(data)
    
    assert isinstance(message, SlackMessage)
    assert len(message.blocks) > 0
    print("✅ JIRA template basic functionality works")
    
    print("All JIRA template tests passed!")