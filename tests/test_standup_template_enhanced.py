"""Test enhanced StandupTemplate implementation."""

import pytest
from datetime import datetime
from devsync_ai.templates.standup_template import StandupTemplate
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.core.status_indicators import StatusIndicatorSystem


class TestEnhancedStandupTemplate:
    """Test the enhanced StandupTemplate with team health indicators."""
    
    @pytest.fixture
    def template_config(self):
        """Create test template configuration."""
        return TemplateConfig(
            team_id="test_team",
            branding={
                "team_name": "Test Engineering Team",
                "logo_emoji": "⚙️"
            },
            interactive_elements=True,
            accessibility_mode=False
        )
    
    @pytest.fixture
    def status_system(self):
        """Create test status indicator system."""
        return StatusIndicatorSystem()
    
    @pytest.fixture
    def standup_template(self, template_config, status_system):
        """Create StandupTemplate instance."""
        return StandupTemplate(config=template_config, status_system=status_system)
    
    @pytest.fixture
    def sample_standup_data(self):
        """Create sample standup data for testing."""
        return {
            'date': '2025-01-14',
            'team': 'Engineering Team',
            'team_health': 0.85,
            'velocity': 0.75,
            'sprint_progress': {
                'completed': 8,
                'total': 12,
                'story_points': {
                    'completed': 34,
                    'total': 50
                },
                'days_remaining': 3
            },
            'stats': {
                'prs_merged': 5,
                'prs_open': 3,
                'prs_draft': 2,
                'tickets_closed': 8,
                'tickets_open': 4,
                'tickets_in_progress': 6,
                'commits': 25,
                'reviews_given': 12,
                'tests_added': 8,
                'bugs_fixed': 3,
                'deployments': 2,
                'story_points_completed': 34,
                'story_points_total': 50,
                'velocity': 0.75
            },
            'team_members': [
                {
                    'name': 'Alice',
                    'yesterday': 'Completed user authentication feature',
                    'today': 'Working on API integration tests',
                    'blockers': [],
                    'on_track': True,
                    'completed_tasks': 3
                },
                {
                    'name': 'Bob',
                    'yesterday': 'Fixed database connection issues',
                    'today': 'Implementing new dashboard components',
                    'blockers': ['Waiting for design approval'],
                    'on_track': False,
                    'completed_tasks': 2
                },
                {
                    'name': 'Charlie',
                    'yesterday': 'Code review and testing',
                    'today': 'Deploying to staging environment',
                    'blockers': [],
                    'on_track': True,
                    'completed_tasks': 4
                }
            ],
            'action_items': [
                {
                    'title': 'Update deployment documentation',
                    'assignee': 'Alice',
                    'due_date': '2025-01-16',
                    'priority': 'high'
                },
                {
                    'title': 'Review security audit findings',
                    'assignee': 'Bob',
                    'due_date': '2025-01-15',
                    'priority': 'critical'
                }
            ]
        }
    
    def test_create_team_health_section(self, standup_template, sample_standup_data):
        """Test team health section creation with color-coded indicators."""
        health_section = standup_template.create_team_health_section(sample_standup_data)
        
        assert health_section is not None
        assert health_section['type'] == 'section'
        assert 'Team Health' in health_section['text']['text']
        assert 'Health Score: 85%' in health_section['text']['text']
        assert '✅ Active Members' in health_section['text']['text']
        assert '⚡ Team Velocity: 75%' in health_section['text']['text']
    
    def test_create_progress_bars(self, standup_template, sample_standup_data):
        """Test sprint progress visualization with progress bars."""
        progress_section = standup_template.create_progress_bars(sample_standup_data['sprint_progress'])
        
        assert progress_section is not None
        assert progress_section['type'] == 'section'
        assert 'Sprint Progress' in progress_section['text']['text']
        assert '66% (8/12)' in progress_section['text']['text']  # 8/12 = 66% (rounded)
        assert 'Story Points' in progress_section['text']['text']
        assert '68% (34/50)' in progress_section['text']['text']  # 34/50 = 68%
        assert 'Days Remaining: 3' in progress_section['text']['text']
    
    def test_create_member_sections(self, standup_template, sample_standup_data):
        """Test member sections with yesterday/today/blockers organization."""
        member_blocks = standup_template.create_member_sections(sample_standup_data['team_members'])
        
        assert len(member_blocks) == 3  # 3 team members
        
        # Test Alice (no blockers)
        alice_block = member_blocks[0]
        assert '✅ Alice' in alice_block['text']['text']
        assert 'Completed user authentication feature' in alice_block['text']['text']
        assert 'Working on API integration tests' in alice_block['text']['text']
        assert '✅ Completed:* 3 tasks' in alice_block['text']['text']
        
        # Test Bob (has blockers)
        bob_block = member_blocks[1]
        assert '🚫 Bob' in bob_block['text']['text']
        assert 'Fixed database connection issues' in bob_block['text']['text']
        assert 'Implementing new dashboard components' in bob_block['text']['text']
        assert '🚨 Blocker:* Waiting for design approval' in bob_block['text']['text']
    
    def test_create_summary_statistics_display(self, standup_template, sample_standup_data):
        """Test summary statistics display for PRs, tickets, and commits."""
        stats_blocks = standup_template.create_summary_statistics_display(sample_standup_data)
        
        assert len(stats_blocks) >= 1  # At least header block
        
        # Check for statistics header
        header_block = stats_blocks[0]
        assert 'Team Statistics Overview' in header_block['text']['text']
        
        # Verify development metrics are included
        dev_metrics_found = False
        for block in stats_blocks:
            if block.get('type') == 'section' and 'fields' in block:
                fields_text = str(block['fields'])
                if 'Pull Requests' in fields_text:
                    dev_metrics_found = True
                    assert '5 merged' in fields_text
                    assert '3 open' in fields_text
                    assert '2 draft' in fields_text
        
        assert dev_metrics_found, "Development metrics not found in statistics display"
    
    def test_interactive_dashboard_buttons(self, standup_template):
        """Test interactive dashboard buttons creation."""
        action_block = standup_template._create_interactive_dashboard_buttons()
        
        assert action_block is not None
        assert action_block['type'] == 'actions'
        assert len(action_block['elements']) <= 6  # Mobile-friendly limit
        
        # Check for expected buttons
        button_texts = [btn['text']['text'] for btn in action_block['elements']]
        assert '📊 Dashboard' in button_texts
        assert '📝 Update' in button_texts
        assert '🚫 Blocker' in button_texts
    
    def test_responsive_design_optimization(self, standup_template):
        """Test responsive design optimization for mobile and desktop."""
        # Create blocks with many fields to test splitting
        test_blocks = [
            {
                'type': 'section',
                'fields': [{'text': f'Field {i}', 'type': 'mrkdwn'} for i in range(8)]
            },
            {
                'type': 'actions',
                'elements': [{'text': {'text': f'Button {i}'}} for i in range(10)]
            }
        ]
        
        optimized_blocks = standup_template._ensure_mobile_responsive_design(test_blocks)
        
        # Should split fields section (8 fields -> 2 blocks of 4 each)
        field_blocks = [b for b in optimized_blocks if b.get('type') == 'section' and 'fields' in b]
        assert len(field_blocks) == 2
        assert all(len(b['fields']) <= 4 for b in field_blocks)
        
        # Should split actions (10 buttons -> 2 blocks of 6 and 4)
        action_blocks = [b for b in optimized_blocks if b.get('type') == 'actions']
        assert len(action_blocks) == 2
        assert all(len(b['elements']) <= 6 for b in action_blocks)
    
    def test_format_message_integration(self, standup_template, sample_standup_data):
        """Test complete message formatting integration."""
        message = standup_template.format_message(sample_standup_data)
        
        assert message is not None
        assert len(message.blocks) > 0
        assert message.text  # Fallback text should be generated
        assert message.metadata['template_type'] == 'StandupTemplate'
        
        # Verify key sections are present
        blocks_text = str(message.blocks)
        assert 'Daily Standup - Engineering Team' in blocks_text
        assert 'Team Health' in blocks_text
        assert 'Sprint Progress' in blocks_text
        assert 'Alice' in blocks_text
        assert 'Bob' in blocks_text
        assert 'Charlie' in blocks_text
    
    def test_accessibility_mode(self, template_config, status_system, sample_standup_data):
        """Test accessibility mode formatting."""
        template_config.accessibility_mode = True
        standup_template = StandupTemplate(config=template_config, status_system=status_system)
        
        # Test accessibility text formatting
        test_text = "✅ Completed 🚫 Blocked ⚠️ Warning"
        formatted_text = standup_template._format_for_accessibility(test_text)
        
        assert '[COMPLETED]' in formatted_text
        assert '[BLOCKED]' in formatted_text
        assert '[WARNING]' in formatted_text
        assert '✅' not in formatted_text
        assert '🚫' not in formatted_text
        assert '⚠️' not in formatted_text


if __name__ == '__main__':
    pytest.main([__file__, '-v'])