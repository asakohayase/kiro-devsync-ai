"""Example usage of the enhanced StandupTemplate with team health indicators."""

import json
from datetime import datetime
from devsync_ai.templates.standup_template import StandupTemplate
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.core.status_indicators import StatusIndicatorSystem


def main():
    """Demonstrate enhanced StandupTemplate functionality."""
    
    # Configure template with team branding
    config = TemplateConfig(
        team_id="engineering_team",
        branding={
            "team_name": "Engineering Team Alpha",
            "logo_emoji": "⚙️"
        },
        interactive_elements=True,
        accessibility_mode=False
    )
    
    # Create status indicator system
    status_system = StatusIndicatorSystem()
    
    # Initialize template
    standup_template = StandupTemplate(config=config, status_system=status_system)
    
    # Sample standup data with comprehensive team information
    standup_data = {
        'date': '2025-01-14',
        'team': 'Engineering Team Alpha',
        'team_health': 0.85,  # 85% team health score
        'velocity': 0.78,     # 78% team velocity
        'sprint_progress': {
            'completed': 12,
            'total': 18,
            'story_points': {
                'completed': 45,
                'total': 65
            },
            'days_remaining': 4
        },
        'stats': {
            # PR Statistics
            'prs_merged': 8,
            'prs_open': 5,
            'prs_draft': 3,
            
            # Ticket Statistics
            'tickets_closed': 12,
            'tickets_open': 6,
            'tickets_in_progress': 8,
            
            # Development Metrics
            'commits': 34,
            'active_branches': 7,
            
            # Quality Metrics
            'reviews_given': 18,
            'tests_added': 15,
            'bugs_fixed': 4,
            'deployments': 3,
            
            # Productivity Metrics
            'story_points_completed': 45,
            'story_points_total': 65,
            'velocity': 0.78
        },
        'team_members': [
            {
                'name': 'Alice Johnson',
                'yesterday': 'Completed user authentication refactor and added comprehensive test coverage',
                'today': 'Working on API rate limiting implementation and performance optimization',
                'blockers': [],
                'on_track': True,
                'completed_tasks': 4
            },
            {
                'name': 'Bob Smith',
                'yesterday': 'Fixed critical database connection pooling issues affecting production',
                'today': 'Implementing new dashboard analytics components with real-time updates',
                'blockers': ['Waiting for design system approval from UX team'],
                'on_track': False,
                'completed_tasks': 3
            },
            {
                'name': 'Charlie Davis',
                'yesterday': 'Conducted thorough code reviews and deployed hotfix to staging environment',
                'today': 'Setting up CI/CD pipeline improvements and automated testing workflows',
                'blockers': [],
                'on_track': True,
                'completed_tasks': 5
            },
            {
                'name': 'Diana Wilson',
                'yesterday': 'Researched microservices architecture patterns and documented findings',
                'today': 'Implementing service mesh integration for better observability',
                'blockers': ['Infrastructure team needs to provision new environments', 'Security review pending'],
                'on_track': False,
                'completed_tasks': 2
            }
        ],
        'action_items': [
            {
                'title': 'Update deployment documentation with new procedures',
                'assignee': 'Alice Johnson',
                'due_date': '2025-01-16',
                'priority': 'high'
            },
            {
                'title': 'Complete security audit findings remediation',
                'assignee': 'Bob Smith',
                'due_date': '2025-01-15',
                'priority': 'critical'
            },
            {
                'title': 'Set up monitoring dashboards for new services',
                'assignee': 'Charlie Davis',
                'due_date': '2025-01-18',
                'priority': 'medium'
            },
            {
                'title': 'Review and approve architecture decision records',
                'assignee': 'Diana Wilson',
                'due_date': '2025-01-17',
                'priority': 'high'
            }
        ]
    }
    
    print("🚀 Enhanced StandupTemplate Example")
    print("=" * 50)
    
    # Generate the formatted message
    message = standup_template.format_message(standup_data)
    
    print("\n📋 Generated Slack Message Blocks:")
    print("-" * 30)
    print(json.dumps(message.blocks, indent=2))
    
    print(f"\n📱 Fallback Text (for accessibility):")
    print("-" * 30)
    print(message.text)
    
    print(f"\n📊 Message Metadata:")
    print("-" * 30)
    print(json.dumps(message.metadata, indent=2))
    
    # Demonstrate individual component methods
    print(f"\n🏥 Team Health Section:")
    print("-" * 30)
    health_section = standup_template.create_team_health_section(standup_data)
    print(json.dumps(health_section, indent=2))
    
    print(f"\n📈 Sprint Progress Section:")
    print("-" * 30)
    progress_section = standup_template.create_progress_bars(standup_data['sprint_progress'])
    print(json.dumps(progress_section, indent=2))
    
    print(f"\n👥 Member Sections (first 2):")
    print("-" * 30)
    member_sections = standup_template.create_member_sections(standup_data['team_members'][:2])
    for i, section in enumerate(member_sections):
        print(f"Member {i+1}:")
        print(json.dumps(section, indent=2))
        print()
    
    print(f"\n📊 Summary Statistics:")
    print("-" * 30)
    stats_blocks = standup_template.create_summary_statistics_display(standup_data)
    for i, block in enumerate(stats_blocks):
        print(f"Stats Block {i+1}:")
        print(json.dumps(block, indent=2))
        print()
    
    # Demonstrate accessibility mode
    print(f"\n♿ Accessibility Mode Example:")
    print("-" * 30)
    config.accessibility_mode = True
    accessible_template = StandupTemplate(config=config, status_system=status_system)
    
    test_text = "✅ Completed 🚫 Blocked ⚠️ Warning 📊 Statistics 🎯 Action Item"
    formatted_text = accessible_template._format_for_accessibility(test_text)
    print(f"Original: {test_text}")
    print(f"Accessible: {formatted_text}")
    
    print(f"\n✨ Enhanced StandupTemplate demonstration complete!")
    print("This template provides:")
    print("• 🏥 Color-coded team health indicators")
    print("• 📈 Visual sprint progress bars")
    print("• 👥 Structured member updates (yesterday/today/blockers)")
    print("• 📊 Comprehensive team statistics")
    print("• 🎮 Interactive dashboard buttons")
    print("• 📱 Responsive design for mobile and desktop")
    print("• ♿ Accessibility compliance features")


if __name__ == '__main__':
    main()