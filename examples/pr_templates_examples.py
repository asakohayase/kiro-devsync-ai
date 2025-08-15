"""Examples demonstrating PR template usage."""

from devsync_ai.templates.pr_templates import (
    NewPRTemplate, ReadyForReviewTemplate, ApprovedPRTemplate,
    ConflictsTemplate, MergedPRTemplate, ClosedPRTemplate
)
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.core.status_indicators import StatusIndicatorSystem


def create_template_config():
    """Create example template configuration."""
    return TemplateConfig(
        team_id="engineering-team",
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
        interactive_elements=True,
        accessibility_mode=False
    )


def example_new_pr():
    """Example of new PR template usage."""
    print("=== New PR Template Example ===")
    
    config = create_template_config()
    status_system = StatusIndicatorSystem()
    template = NewPRTemplate(config, status_system)
    
    pr_data = {
        'number': 123,
        'title': 'Add user authentication system',
        'body': 'This PR implements OAuth 2.0 authentication with JWT tokens.',
        'html_url': 'https://github.com/company/repo/pull/123',
        'user': {'login': 'developer1'},
        'head': {'ref': 'feature/auth'},
        'base': {'ref': 'main'},
        'reviewers': [
            {'login': 'reviewer1', 'review_status': 'pending'},
            {'login': 'reviewer2', 'review_status': 'pending'}
        ],
        'labels': [{'name': 'enhancement'}, {'name': 'backend'}],
        'changed_files': 8,
        'additions': 245,
        'deletions': 12
    }
    
    message = template.format_message({'pr': pr_data})
    print(f"Blocks: {len(message.blocks)}")
    print(f"Fallback text: {message.text}")
    print()


def example_ready_for_review():
    """Example of ready for review template usage."""
    print("=== Ready for Review Template Example ===")
    
    config = create_template_config()
    status_system = StatusIndicatorSystem()
    template = ReadyForReviewTemplate(config, status_system)
    
    pr_data = {
        'number': 124,
        'title': 'Implement payment processing',
        'html_url': 'https://github.com/company/repo/pull/124',
        'user': {'login': 'developer2'},
        'head': {'ref': 'feature/payments'},
        'base': {'ref': 'main'},
        'reviewers': [
            {'login': 'tech-lead', 'review_status': 'pending'},
            {'login': 'security-reviewer', 'review_status': 'pending'}
        ],
        'checks': {
            'passed': 4,
            'failed': 0,
            'pending': 1
        },
        'labels': [{'name': 'critical'}, {'name': 'security'}],
        'changed_files': 12,
        'additions': 380,
        'deletions': 25
    }
    
    message = template.format_message({'pr': pr_data})
    print(f"Blocks: {len(message.blocks)}")
    print(f"Fallback text: {message.text}")
    print()


def example_approved_pr():
    """Example of approved PR template usage."""
    print("=== Approved PR Template Example ===")
    
    config = create_template_config()
    status_system = StatusIndicatorSystem()
    template = ApprovedPRTemplate(config, status_system)
    
    pr_data = {
        'number': 125,
        'title': 'Fix critical security vulnerability',
        'html_url': 'https://github.com/company/repo/pull/125',
        'user': {'login': 'security-team'},
        'head': {'ref': 'hotfix/security-patch'},
        'base': {'ref': 'main'},
        'review_decision': 'APPROVED',
        'mergeable': True,
        'mergeable_state': 'clean',
        'checks': {
            'passed': 5,
            'failed': 0,
            'pending': 0
        },
        'reviewers': [
            {'login': 'tech-lead', 'review_status': 'approved'},
            {'login': 'security-lead', 'review_status': 'approved'}
        ],
        'priority': 'critical',
        'changed_files': 3,
        'additions': 45,
        'deletions': 8
    }
    
    message = template.format_message({'pr': pr_data})
    print(f"Blocks: {len(message.blocks)}")
    print(f"Fallback text: {message.text}")
    print()


def example_conflicts_pr():
    """Example of conflicts template usage."""
    print("=== Conflicts Template Example ===")
    
    config = create_template_config()
    status_system = StatusIndicatorSystem()
    template = ConflictsTemplate(config, status_system)
    
    pr_data = {
        'number': 126,
        'title': 'Update database schema',
        'html_url': 'https://github.com/company/repo/pull/126',
        'user': {'login': 'database-admin'},
        'head': {'ref': 'feature/schema-update'},
        'base': {'ref': 'main'},
        'mergeable_state': 'dirty',
        'conflicted_files': [
            'migrations/001_initial.sql',
            'models/user.py',
            'config/database.yaml'
        ],
        'changed_files': 6,
        'additions': 120,
        'deletions': 35
    }
    
    message = template.format_message({'pr': pr_data})
    print(f"Blocks: {len(message.blocks)}")
    print(f"Fallback text: {message.text}")
    print()


def example_merged_pr():
    """Example of merged PR template usage."""
    print("=== Merged PR Template Example ===")
    
    config = create_template_config()
    status_system = StatusIndicatorSystem()
    template = MergedPRTemplate(config, status_system)
    
    pr_data = {
        'number': 127,
        'title': 'Add real-time notifications',
        'html_url': 'https://github.com/company/repo/pull/127',
        'user': {'login': 'frontend-dev'},
        'head': {'ref': 'feature/notifications'},
        'base': {'ref': 'main'},
        'merged': True,
        'merged_by': {'login': 'tech-lead'},
        'merged_at': '2024-01-15T16:30:00Z',
        'merge_commit_sha': 'abc123def456',
        'deployments': [
            {'environment': 'staging', 'status': 'success'},
            {'environment': 'production', 'status': 'pending'}
        ],
        'created_at': '2024-01-14T09:00:00Z',
        'changed_files': 15,
        'additions': 450,
        'deletions': 80
    }
    
    message = template.format_message({'pr': pr_data})
    print(f"Blocks: {len(message.blocks)}")
    print(f"Fallback text: {message.text}")
    print()


def example_closed_pr():
    """Example of closed PR template usage."""
    print("=== Closed PR Template Example ===")
    
    config = create_template_config()
    status_system = StatusIndicatorSystem()
    template = ClosedPRTemplate(config, status_system)
    
    pr_data = {
        'number': 128,
        'title': 'Experimental feature prototype',
        'html_url': 'https://github.com/company/repo/pull/128',
        'user': {'login': 'researcher'},
        'head': {'ref': 'experiment/new-algorithm'},
        'base': {'ref': 'main'},
        'state': 'closed',
        'closed_by': {'login': 'product-manager'},
        'closed_at': '2024-01-15T14:00:00Z',
        'created_at': '2024-01-10T10:00:00Z',
        'review_decision': 'CHANGES_REQUESTED',
        'comments': 8,
        'changed_files': 20,
        'additions': 600,
        'deletions': 150
    }
    
    context_data = {
        'close_reason': 'Feature postponed to next quarter due to resource constraints'
    }
    
    message = template.format_message({'pr': pr_data, **context_data})
    print(f"Blocks: {len(message.blocks)}")
    print(f"Fallback text: {message.text}")
    print()


def example_template_factory_integration():
    """Example of using PR templates with a factory pattern."""
    print("=== Template Factory Integration Example ===")
    
    config = create_template_config()
    status_system = StatusIndicatorSystem()
    
    # Template registry
    templates = {
        'new_pr': NewPRTemplate(config, status_system),
        'ready_for_review': ReadyForReviewTemplate(config, status_system),
        'approved': ApprovedPRTemplate(config, status_system),
        'conflicts': ConflictsTemplate(config, status_system),
        'merged': MergedPRTemplate(config, status_system),
        'closed': ClosedPRTemplate(config, status_system)
    }
    
    # Example PR event data
    pr_events = [
        {
            'event_type': 'new_pr',
            'pr': {
                'number': 200,
                'title': 'Factory pattern example',
                'user': {'login': 'developer'},
                'head': {'ref': 'feature/factory'},
                'base': {'ref': 'main'}
            }
        },
        {
            'event_type': 'approved',
            'pr': {
                'number': 201,
                'title': 'Ready to merge',
                'user': {'login': 'developer'},
                'review_decision': 'APPROVED',
                'mergeable': True,
                'checks': {'passed': 3, 'failed': 0, 'pending': 0}
            }
        }
    ]
    
    # Process events with appropriate templates
    for event in pr_events:
        event_type = event['event_type']
        if event_type in templates:
            template = templates[event_type]
            message = template.format_message(event)
            print(f"Event: {event_type}")
            print(f"PR #{event['pr']['number']}: {len(message.blocks)} blocks generated")
        else:
            print(f"No template found for event type: {event_type}")
    
    print()


if __name__ == "__main__":
    """Run all PR template examples."""
    print("PR Templates Examples")
    print("=" * 50)
    
    example_new_pr()
    example_ready_for_review()
    example_approved_pr()
    example_conflicts_pr()
    example_merged_pr()
    example_closed_pr()
    example_template_factory_integration()
    
    print("All examples completed successfully!")