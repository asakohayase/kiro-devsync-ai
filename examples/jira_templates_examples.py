"""Examples demonstrating JIRA template usage."""

from datetime import datetime
from devsync_ai.templates.jira_templates import (
    StatusChangeTemplate,
    PriorityChangeTemplate,
    AssignmentTemplate,
    CommentTemplate,
    BlockerTemplate,
    SprintChangeTemplate
)
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.core.status_indicators import StatusIndicatorSystem


def create_sample_config():
    """Create sample template configuration."""
    return TemplateConfig(
        team_id="engineering_team",
        branding={
            "primary_color": "#1f77b4",
            "logo_emoji": ":gear:",
            "team_name": "Engineering Team"
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


def create_sample_ticket_data():
    """Create sample ticket data."""
    return {
        'key': 'ENG-456',
        'summary': 'Implement OAuth 2.0 authentication flow',
        'status': 'In Progress',
        'assignee': 'alice.developer',
        'reporter': 'bob.manager',
        'priority': 'High',
        'story_points': 13,
        'sprint': 'Sprint 2024-03',
        'epic': 'Authentication System',
        'components': ['Authentication', 'Security', 'API'],
        'labels': ['backend', 'security', 'oauth'],
        'updated': '2024-01-15T15:30:00Z'
    }


def example_status_change_notification():
    """Example of status change notification."""
    print("=== Status Change Notification Example ===")
    
    config = create_sample_config()
    status_system = StatusIndicatorSystem()
    template = StatusChangeTemplate(config, status_system)
    
    data = {
        'ticket': create_sample_ticket_data(),
        'from_status': 'To Do',
        'to_status': 'In Progress',
        'channel': '#engineering',
        'thread_ts': None
    }
    
    message = template.format_message(data)
    print(f"Blocks: {len(message.blocks)} blocks created")
    print(f"Fallback text: {message.text}")
    print(f"Template type: {message.metadata['template_type']}")
    print()


def example_priority_change_notification():
    """Example of priority change notification."""
    print("=== Priority Change Notification Example ===")
    
    config = create_sample_config()
    status_system = StatusIndicatorSystem()
    template = PriorityChangeTemplate(config, status_system)
    
    data = {
        'ticket': create_sample_ticket_data(),
        'from_priority': 'Medium',
        'to_priority': 'Critical',
        'channel': '#engineering',
        'thread_ts': None
    }
    
    message = template.format_message(data)
    print(f"Blocks: {len(message.blocks)} blocks created")
    print(f"Fallback text: {message.text}")
    print(f"Template type: {message.metadata['template_type']}")
    print()


def example_assignment_change_notification():
    """Example of assignment change notification."""
    print("=== Assignment Change Notification Example ===")
    
    config = create_sample_config()
    status_system = StatusIndicatorSystem()
    template = AssignmentTemplate(config, status_system)
    
    data = {
        'ticket': create_sample_ticket_data(),
        'from_assignee': 'Unassigned',
        'to_assignee': 'alice.developer',
        'channel': '#engineering',
        'thread_ts': None
    }
    
    message = template.format_message(data)
    print(f"Blocks: {len(message.blocks)} blocks created")
    print(f"Fallback text: {message.text}")
    print(f"Template type: {message.metadata['template_type']}")
    print()


def example_comment_notification():
    """Example of comment notification."""
    print("=== Comment Notification Example ===")
    
    config = create_sample_config()
    status_system = StatusIndicatorSystem()
    template = CommentTemplate(config, status_system)
    
    comment_data = {
        'author': 'charlie.reviewer',
        'body': 'The OAuth implementation looks good, but we should add rate limiting to prevent abuse. Also, make sure to validate the redirect URI properly.',
        'created': '2024-01-15T16:45:00Z'
    }
    
    data = {
        'ticket': create_sample_ticket_data(),
        'comment': comment_data,
        'total_comments': 7,
        'channel': '#engineering',
        'thread_ts': None
    }
    
    message = template.format_message(data)
    print(f"Blocks: {len(message.blocks)} blocks created")
    print(f"Fallback text: {message.text}")
    print(f"Template type: {message.metadata['template_type']}")
    print()


def example_blocker_notification():
    """Example of blocker notification."""
    print("=== Blocker Notification Example ===")
    
    config = create_sample_config()
    status_system = StatusIndicatorSystem()
    template = BlockerTemplate(config, status_system)
    
    data = {
        'ticket': create_sample_ticket_data(),
        'blocker_status': 'identified',
        'blocker_description': 'Waiting for security team approval on OAuth scopes and permissions model',
        'channel': '#engineering',
        'thread_ts': None
    }
    
    message = template.format_message(data)
    print(f"Blocks: {len(message.blocks)} blocks created")
    print(f"Fallback text: {message.text}")
    print(f"Template type: {message.metadata['template_type']}")
    print()


def example_sprint_change_notification():
    """Example of sprint change notification."""
    print("=== Sprint Change Notification Example ===")
    
    config = create_sample_config()
    status_system = StatusIndicatorSystem()
    template = SprintChangeTemplate(config, status_system)
    
    sprint_change = {
        'from': 'Sprint 2024-02',
        'to': 'Sprint 2024-03',
        'type': 'moved'
    }
    
    sprint_info = {
        'name': 'Sprint 2024-03',
        'start_date': '2024-01-29',
        'end_date': '2024-02-12',
        'capacity': 45,
        'committed_points': 42,
        'completed_points': 8,
        'team_velocity': 41
    }
    
    data = {
        'ticket': create_sample_ticket_data(),
        'sprint_change': sprint_change,
        'sprint_info': sprint_info,
        'channel': '#engineering',
        'thread_ts': None
    }
    
    message = template.format_message(data)
    print(f"Blocks: {len(message.blocks)} blocks created")
    print(f"Fallback text: {message.text}")
    print(f"Template type: {message.metadata['template_type']}")
    print()


def example_batch_processing():
    """Example of processing multiple JIRA events."""
    print("=== Batch Processing Example ===")
    
    config = create_sample_config()
    status_system = StatusIndicatorSystem()
    
    # Process multiple different types of JIRA events
    events = [
        {
            'type': 'status_change',
            'template': StatusChangeTemplate(config, status_system),
            'data': {
                'ticket': create_sample_ticket_data(),
                'from_status': 'In Progress',
                'to_status': 'Done',
                'channel': '#engineering'
            }
        },
        {
            'type': 'comment_added',
            'template': CommentTemplate(config, status_system),
            'data': {
                'ticket': create_sample_ticket_data(),
                'comment': {
                    'author': 'dave.tester',
                    'body': 'Testing completed successfully. All OAuth flows working as expected.',
                    'created': '2024-01-15T17:30:00Z'
                },
                'total_comments': 8,
                'channel': '#engineering'
            }
        }
    ]
    
    for event in events:
        message = event['template'].format_message(event['data'])
        print(f"{event['type']}: {len(message.blocks)} blocks, fallback: {message.text[:50]}...")
    
    print()


if __name__ == '__main__':
    """Run all examples."""
    print("JIRA Templates Examples")
    print("=" * 50)
    print()
    
    example_status_change_notification()
    example_priority_change_notification()
    example_assignment_change_notification()
    example_comment_notification()
    example_blocker_notification()
    example_sprint_change_notification()
    example_batch_processing()
    
    print("All examples completed successfully!")