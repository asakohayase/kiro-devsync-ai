"""Tests for JIRA ticket notification templates."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from devsync_ai.templates.jira_templates import (
    JIRATemplate,
    StatusChangeTemplate,
    PriorityChangeTemplate,
    AssignmentTemplate,
    CommentTemplate,
    BlockerTemplate,
    SprintChangeTemplate
)
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.core.status_indicators import StatusIndicatorSystem


@pytest.fixture
def template_config():
    """Create test template configuration."""
    return TemplateConfig(
        team_id="test_team",
        branding={
            "primary_color": "#1f77b4",
            "logo_emoji": ":gear:",
            "team_name": "Test Team"
        },
        emoji_set={
            "success": ":white_check_mark:",
            "warning": ":warning:",
            "error": ":x:"
        },
        color_scheme={
            "primary": "#1f77b4",
            "success": "#28a745",
            "warning": "#ffc107",
            "danger": "#dc3545"
        },
        interactive_elements=True,
        accessibility_mode=False
    )


@pytest.fixture
def status_system():
    """Create test status indicator system."""
    return StatusIndicatorSystem()


@pytest.fixture
def sample_ticket_data():
    """Create sample ticket data for testing."""
    return {
        'key': 'TEST-123',
        'summary': 'Implement user authentication system',
        'status': 'In Progress',
        'assignee': 'john.doe',
        'reporter': 'jane.smith',
        'priority': 'High',
        'story_points': 8,
        'sprint': 'Sprint 2024-01',
        'epic': 'User Management Epic',
        'components': ['Authentication', 'Security'],
        'labels': ['backend', 'security', 'api'],
        'updated': '2024-01-15T10:30:00Z'
    }


class TestJIRATemplate:
    """Test base JIRA template functionality."""
    
    def test_create_ticket_header(self, template_config, status_system, sample_ticket_data):
        """Test ticket header creation."""
        template = JIRATemplate(template_config, status_system)
        
        header_blocks = template.create_ticket_header(sample_ticket_data)
        
        assert len(header_blocks) >= 1
        assert 'TEST-123' in str(header_blocks)
        assert 'Implement user authentication system' in str(header_blocks)
    
    def test_create_status_transition(self, template_config, status_system):
        """Test status transition display."""
        template = JIRATemplate(template_config, status_system)
        
        transition_block = template.create_status_transition('To Do', 'In Progress')
        
        assert transition_block['type'] == 'section'
        assert 'Status Transition' in transition_block['text']['text']
        assert 'To Do' in transition_block['text']['text']
        assert 'In Progress' in transition_block['text']['text']
    
    def test_create_priority_indicators(self, template_config, status_system):
        """Test priority indicators creation."""
        template = JIRATemplate(template_config, status_system)
        
        # Test single priority
        priority_block = template.create_priority_indicators('High')
        assert 'Priority' in priority_block['text']['text']
        assert 'High' in priority_block['text']['text']
        
        # Test priority change
        priority_change_block = template.create_priority_indicators('Critical', 'Medium')
        assert 'Priority Change' in priority_change_block['text']['text']
        assert 'immediate attention' in priority_change_block['text']['text']
    
    def test_map_jira_status_to_type(self, template_config, status_system):
        """Test JIRA status mapping."""
        template = JIRATemplate(template_config, status_system)
        
        # Test various status mappings
        assert template._map_jira_status_to_type('Done').name == 'SUCCESS'
        assert template._map_jira_status_to_type('In Progress').name == 'IN_PROGRESS'
        assert template._map_jira_status_to_type('Blocked').name == 'ERROR'
        assert template._map_jira_status_to_type('In Review').name == 'WARNING'
        assert template._map_jira_status_to_type('To Do').name == 'INFO'
    
    def test_format_ticket_field_value(self, template_config, status_system):
        """Test ticket field value formatting."""
        template = JIRATemplate(template_config, status_system)
        
        # Test assignee formatting
        assert '<@john.doe>' in template._format_ticket_field_value('assignee', 'john.doe')
        
        # Test story points formatting
        assert '📊 8 points' == template._format_ticket_field_value('story_points', 8)
        
        # Test components formatting
        components = ['Auth', 'Security', 'API', 'Extra']
        result = template._format_ticket_field_value('components', components)
        assert '`Auth`' in result
        assert '(+1 more)' in result
        
        # Test labels formatting
        labels = ['backend', 'security']
        result = template._format_ticket_field_value('labels', labels)
        assert '`backend`' in result
        assert '`security`' in result


class TestStatusChangeTemplate:
    """Test status change template."""
    
    def test_status_change_message_creation(self, template_config, status_system, sample_ticket_data):
        """Test status change message creation."""
        template = StatusChangeTemplate(template_config, status_system)
        
        data = {
            'ticket': sample_ticket_data,
            'from_status': 'To Do',
            'to_status': 'In Progress'
        }
        
        message = template.format_message(data)
        
        assert message.blocks is not None
        assert len(message.blocks) > 0
        assert 'TEST-123' in message.text
        assert message.metadata['template_type'] == 'StatusChangeTemplate'
    
    def test_workflow_context_creation(self, template_config, status_system):
        """Test workflow context messages."""
        template = StatusChangeTemplate(template_config, status_system)
        
        # Test work started context
        context = template._create_workflow_context('To Do', 'In Progress')
        assert context is not None
        assert 'Work has started' in context['text']['text']
        
        # Test blocker resolved context
        context = template._create_workflow_context('Blocked', 'In Progress')
        assert context is not None
        assert 'Blocker resolved' in context['text']['text']
        
        # Test no context for unknown transition
        context = template._create_workflow_context('Unknown', 'Other')
        assert context is None
    
    def test_status_specific_actions(self, template_config, status_system, sample_ticket_data):
        """Test status-specific action buttons."""
        template = StatusChangeTemplate(template_config, status_system)
        
        # Test actions for 'To Do' status
        actions = template._create_status_actions('To Do', sample_ticket_data)
        assert actions is not None
        action_texts = [elem['text']['text'] for elem in actions['elements']]
        assert any('Start Work' in text for text in action_texts)
        assert any('Assign to Me' in text for text in action_texts)
        
        # Test actions for 'In Progress' status
        actions = template._create_status_actions('In Progress', sample_ticket_data)
        assert actions is not None
        action_texts = [elem['text']['text'] for elem in actions['elements']]
        assert any('Mark Done' in text for text in action_texts)
        assert any('Block' in text for text in action_texts)


class TestPriorityChangeTemplate:
    """Test priority change template."""
    
    def test_priority_change_message_creation(self, template_config, status_system, sample_ticket_data):
        """Test priority change message creation."""
        template = PriorityChangeTemplate(template_config, status_system)
        
        data = {
            'ticket': sample_ticket_data,
            'from_priority': 'Medium',
            'to_priority': 'Critical'
        }
        
        message = template.format_message(data)
        
        assert message.blocks is not None
        assert len(message.blocks) > 0
        assert 'TEST-123' in message.text
        assert message.metadata['template_type'] == 'PriorityChangeTemplate'
    
    def test_escalation_context_creation(self, template_config, status_system):
        """Test escalation context messages."""
        template = PriorityChangeTemplate(template_config, status_system)
        
        # Test escalation to critical
        context = template._create_escalation_context('Medium', 'Critical')
        assert context is not None
        assert 'URGENT ESCALATION' in context['text']['text']
        
        # Test escalation to high
        context = template._create_escalation_context('Low', 'High')
        assert context is not None
        assert 'PRIORITY ESCALATION' in context['text']['text']
        
        # Test de-escalation
        context = template._create_escalation_context('High', 'Low')
        assert context is not None
        assert 'reduced' in context['text']['text']
    
    def test_priority_specific_actions(self, template_config, status_system, sample_ticket_data):
        """Test priority-specific action buttons."""
        template = PriorityChangeTemplate(template_config, status_system)
        
        # Test actions for critical priority
        actions = template._create_priority_actions('Critical', sample_ticket_data)
        assert actions is not None
        action_texts = [elem['text']['text'] for elem in actions['elements']]
        assert any('Escalate to Team Lead' in text for text in action_texts)
        assert any('Request Help' in text for text in action_texts)


class TestAssignmentTemplate:
    """Test assignment change template."""
    
    def test_assignment_change_message_creation(self, template_config, status_system, sample_ticket_data):
        """Test assignment change message creation."""
        template = AssignmentTemplate(template_config, status_system)
        
        data = {
            'ticket': sample_ticket_data,
            'from_assignee': 'Unassigned',
            'to_assignee': 'john.doe'
        }
        
        message = template.format_message(data)
        
        assert message.blocks is not None
        assert len(message.blocks) > 0
        assert 'TEST-123' in message.text
        assert message.metadata['template_type'] == 'AssignmentTemplate'
    
    def test_assignment_transition_display(self, template_config, status_system):
        """Test assignment transition display."""
        template = AssignmentTemplate(template_config, status_system)
        
        # Test assignment from unassigned
        transition = template._create_assignment_transition('Unassigned', 'john.doe')
        assert 'Assigned to' in transition['text']['text']
        assert '<@john.doe>' in transition['text']['text']
        
        # Test reassignment
        transition = template._create_assignment_transition('jane.smith', 'john.doe')
        assert 'Reassigned' in transition['text']['text']
        assert '<@jane.smith>' in transition['text']['text']
        assert '<@john.doe>' in transition['text']['text']
        
        # Test unassignment
        transition = template._create_assignment_transition('john.doe', 'Unassigned')
        assert 'Unassigned from' in transition['text']['text']
        assert '<@john.doe>' in transition['text']['text']
    
    def test_assignee_notification(self, template_config, status_system):
        """Test assignee notification creation."""
        template = AssignmentTemplate(template_config, status_system)
        
        notification = template._create_assignee_notification('john.doe')
        assert 'Hey <@john.doe>' in notification['text']['text']
        assert 'assigned to you' in notification['text']['text']


class TestCommentTemplate:
    """Test comment template."""
    
    def test_comment_message_creation(self, template_config, status_system, sample_ticket_data):
        """Test comment message creation."""
        template = CommentTemplate(template_config, status_system)
        
        comment_data = {
            'author': 'jane.smith',
            'body': 'This looks good to me. Ready for testing.',
            'created': '2024-01-15T14:30:00Z'
        }
        
        data = {
            'ticket': sample_ticket_data,
            'comment': comment_data,
            'total_comments': 3
        }
        
        message = template.format_message(data)
        
        assert message.blocks is not None
        assert len(message.blocks) > 0
        assert 'TEST-123' in message.text
        assert message.metadata['template_type'] == 'CommentTemplate'
    
    def test_comment_display_creation(self, template_config, status_system):
        """Test comment display formatting."""
        template = CommentTemplate(template_config, status_system)
        
        comment_data = {
            'author': 'jane.smith',
            'body': 'This is a test comment with some details.',
            'created': '2024-01-15T14:30:00Z'
        }
        
        display = template._create_comment_display(comment_data)
        assert 'New comment by <@jane.smith>' in display['text']['text']
        assert 'This is a test comment' in display['text']['text']
    
    def test_comment_history_context(self, template_config, status_system):
        """Test comment history context."""
        template = CommentTemplate(template_config, status_system)
        
        # Test with multiple comments
        data = {'total_comments': 5}
        context = template._create_comment_history_context(data)
        assert context is not None
        assert '5 total comments' in context['text']['text']
        
        # Test with single comment
        data = {'total_comments': 1}
        context = template._create_comment_history_context(data)
        assert context is None


class TestBlockerTemplate:
    """Test blocker template."""
    
    def test_blocker_identified_message_creation(self, template_config, status_system, sample_ticket_data):
        """Test blocker identified message creation."""
        template = BlockerTemplate(template_config, status_system)
        
        data = {
            'ticket': sample_ticket_data,
            'blocker_status': 'identified',
            'blocker_description': 'Waiting for API endpoint to be deployed'
        }
        
        message = template.format_message(data)
        
        assert message.blocks is not None
        assert len(message.blocks) > 0
        assert 'TEST-123' in message.text
        assert message.metadata['template_type'] == 'BlockerTemplate'
    
    def test_blocker_resolved_message_creation(self, template_config, status_system, sample_ticket_data):
        """Test blocker resolved message creation."""
        template = BlockerTemplate(template_config, status_system)
        
        data = {
            'ticket': sample_ticket_data,
            'blocker_status': 'resolved',
            'blocker_description': 'API endpoint is now available'
        }
        
        message = template.format_message(data)
        
        assert message.blocks is not None
        assert 'Blocker Resolved' in str(message.blocks)
        assert 'Work can now continue' in str(message.blocks)
    
    def test_blocker_impact_assessment(self, template_config, status_system):
        """Test blocker impact assessment."""
        template = BlockerTemplate(template_config, status_system)
        
        # Test high priority blocker
        ticket_data = {
            'key': 'TEST-123',
            'priority': 'Critical',
            'sprint': 'Sprint 2024-01'
        }
        
        data = {
            'ticket': ticket_data,
            'blocker_status': 'identified'
        }
        
        impact = template._create_blocker_impact_assessment(data)
        assert impact is not None
        assert 'HIGH IMPACT' in impact['text']['text']
        assert 'SPRINT IMPACT' in impact['text']['text']
        assert 'ACTION REQUIRED' in impact['text']['text']
    
    def test_blocker_escalation_actions(self, template_config, status_system, sample_ticket_data):
        """Test blocker escalation actions."""
        template = BlockerTemplate(template_config, status_system)
        
        # Test identified blocker actions
        data = {
            'ticket': sample_ticket_data,
            'blocker_status': 'identified'
        }
        
        actions = template._create_blocker_escalation_actions(data)
        assert actions is not None
        action_texts = [elem['text']['text'] for elem in actions['elements']]
        assert any('Escalate to Team Lead' in text for text in action_texts)
        assert any('Request Help' in text for text in action_texts)
        
        # Test resolved blocker actions
        data['blocker_status'] = 'resolved'
        actions = template._create_blocker_escalation_actions(data)
        assert actions is not None
        action_texts = [elem['text']['text'] for elem in actions['elements']]
        assert any('Resume Work' in text for text in action_texts)


class TestSprintChangeTemplate:
    """Test sprint change template."""
    
    def test_sprint_change_message_creation(self, template_config, status_system, sample_ticket_data):
        """Test sprint change message creation."""
        template = SprintChangeTemplate(template_config, status_system)
        
        sprint_change = {
            'from': 'Backlog',
            'to': 'Sprint 2024-02',
            'type': 'added'
        }
        
        sprint_info = {
            'name': 'Sprint 2024-02',
            'start_date': '2024-01-15',
            'end_date': '2024-01-29',
            'capacity': 40,
            'committed_points': 35,
            'completed_points': 10,
            'team_velocity': 38
        }
        
        data = {
            'ticket': sample_ticket_data,
            'sprint_change': sprint_change,
            'sprint_info': sprint_info
        }
        
        message = template.format_message(data)
        
        assert message.blocks is not None
        assert len(message.blocks) > 0
        assert 'TEST-123' in message.text
        assert message.metadata['template_type'] == 'SprintChangeTemplate'
    
    def test_sprint_transition_display(self, template_config, status_system):
        """Test sprint transition display."""
        template = SprintChangeTemplate(template_config, status_system)
        
        # Test added to sprint
        sprint_change = {'from': 'Backlog', 'to': 'Sprint 2024-02', 'type': 'added'}
        display = template._create_sprint_transition_display(sprint_change)
        assert 'Added to Sprint' in display['text']['text']
        assert 'Sprint 2024-02' in display['text']['text']
        
        # Test moved between sprints
        sprint_change = {'from': 'Sprint 2024-01', 'to': 'Sprint 2024-02', 'type': 'moved'}
        display = template._create_sprint_transition_display(sprint_change)
        assert 'Sprint Changed' in display['text']['text']
        assert 'Sprint 2024-01' in display['text']['text']
        assert 'Sprint 2024-02' in display['text']['text']
        
        # Test removed from sprint
        sprint_change = {'from': 'Sprint 2024-01', 'to': 'Backlog', 'type': 'removed'}
        display = template._create_sprint_transition_display(sprint_change)
        assert 'Removed from Sprint' in display['text']['text']
    
    def test_sprint_capacity_context(self, template_config, status_system):
        """Test sprint capacity context."""
        template = SprintChangeTemplate(template_config, status_system)
        
        sprint_info = {
            'start_date': '2024-01-15',
            'end_date': '2024-01-29',
            'capacity': 40,
            'committed_points': 45,  # Over capacity
            'completed_points': 15,
            'team_velocity': 38
        }
        
        data = {'sprint_info': sprint_info}
        context = template._create_sprint_capacity_context(data)
        
        assert context is not None
        assert 'Sprint Context' in context['text']['text']
        assert '2024-01-15 - 2024-01-29' in context['text']['text']
        assert '45/40 story points' in context['text']['text']
        assert 'OVER CAPACITY' in context['text']['text']
        assert '15/45 points' in context['text']['text']
        assert '38 points/sprint' in context['text']['text']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])