"""Tests for PR status notification templates."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from devsync_ai.templates.pr_templates import (
    PRTemplate, NewPRTemplate, ReadyForReviewTemplate, 
    ApprovedPRTemplate, ConflictsTemplate, MergedPRTemplate, ClosedPRTemplate
)
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.core.status_indicators import StatusIndicatorSystem, PRStatus


@pytest.fixture
def template_config():
    """Create test template configuration."""
    return TemplateConfig(
        team_id="test-team",
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
        interactive_elements=True,
        accessibility_mode=False
    )


@pytest.fixture
def status_system():
    """Create test status indicator system."""
    return StatusIndicatorSystem()


@pytest.fixture
def sample_pr_data():
    """Create sample PR data for testing."""
    return {
        'number': 123,
        'title': 'Add new feature for user authentication',
        'body': 'This PR adds comprehensive user authentication with OAuth support.',
        'html_url': 'https://github.com/test/repo/pull/123',
        'state': 'open',
        'draft': False,
        'merged': False,
        'user': {'login': 'testuser'},
        'head': {'ref': 'feature/auth'},
        'base': {'ref': 'main'},
        'reviewers': [
            {'login': 'reviewer1', 'review_status': 'pending'},
            {'login': 'reviewer2', 'review_status': 'approved'}
        ],
        'labels': [
            {'name': 'enhancement'},
            {'name': 'backend'}
        ],
        'milestone': {'title': 'v2.0'},
        'changed_files': 5,
        'additions': 150,
        'deletions': 25,
        'checks': {
            'passed': 3,
            'failed': 0,
            'pending': 1
        },
        'created_at': '2024-01-15T10:00:00Z',
        'updated_at': '2024-01-15T14:30:00Z'
    }


class TestPRTemplate:
    """Test base PRTemplate class."""
    
    def test_pr_template_is_abstract(self, template_config, status_system):
        """Test that PRTemplate cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PRTemplate(template_config, status_system)
    
    def test_get_pr_status_draft(self, sample_pr_data):
        """Test PR status detection for draft PR."""
        # Create a concrete subclass for testing
        class TestPRTemplate(PRTemplate):
            def _create_pr_content(self, pr_data, context_data):
                return []
        
        template = TestPRTemplate()
        pr_data = sample_pr_data.copy()
        pr_data['draft'] = True
        
        status = template._get_pr_status(pr_data)
        assert status == PRStatus.DRAFT
    
    def test_get_pr_status_merged(self, sample_pr_data):
        """Test PR status detection for merged PR."""
        class TestPRTemplate(PRTemplate):
            def _create_pr_content(self, pr_data, context_data):
                return []
        
        template = TestPRTemplate()
        pr_data = sample_pr_data.copy()
        pr_data['merged'] = True
        
        status = template._get_pr_status(pr_data)
        assert status == PRStatus.MERGED
    
    def test_get_pr_status_conflicts(self, sample_pr_data):
        """Test PR status detection for PR with conflicts."""
        class TestPRTemplate(PRTemplate):
            def _create_pr_content(self, pr_data, context_data):
                return []
        
        template = TestPRTemplate()
        pr_data = sample_pr_data.copy()
        pr_data['mergeable_state'] = 'dirty'
        
        status = template._get_pr_status(pr_data)
        assert status == PRStatus.CONFLICTS
    
    def test_build_pr_subtitle(self, sample_pr_data):
        """Test PR subtitle building."""
        class TestPRTemplate(PRTemplate):
            def _create_pr_content(self, pr_data, context_data):
                return []
        
        template = TestPRTemplate()
        subtitle = template._build_pr_subtitle(sample_pr_data)
        
        assert '`feature/auth` → `main`' in subtitle
        assert 'by <@testuser>' in subtitle


class TestNewPRTemplate:
    """Test NewPRTemplate class."""
    
    def test_new_pr_template_creation(self, template_config, status_system):
        """Test NewPRTemplate can be created."""
        template = NewPRTemplate(template_config, status_system)
        assert template is not None
        assert template.REQUIRED_FIELDS == ['pr']
    
    @patch.object(NewPRTemplate, 'create_section_block')
    @patch.object(NewPRTemplate, 'create_fields_section')
    def test_create_pr_content(self, mock_fields, mock_section, template_config, status_system, sample_pr_data):
        """Test new PR content creation."""
        template = NewPRTemplate(template_config, status_system)
        
        # Mock the methods to return test data
        mock_section.return_value = {'type': 'section', 'text': {'type': 'mrkdwn', 'text': 'test'}}
        mock_fields.return_value = {'type': 'section', 'fields': []}
        
        blocks = template._create_pr_content(sample_pr_data, {})
        
        assert len(blocks) >= 2  # Should have new PR message and description
        mock_section.assert_called()
    
    def test_get_state_specific_actions(self, template_config, status_system, sample_pr_data):
        """Test state-specific actions for new PR."""
        template = NewPRTemplate(template_config, status_system)
        actions = template._get_state_specific_actions(sample_pr_data, {})
        
        action_texts = [action['text'] for action in actions]
        assert '✅ Approve' in action_texts
        assert '❌ Request Changes' in action_texts


class TestReadyForReviewTemplate:
    """Test ReadyForReviewTemplate class."""
    
    def test_ready_for_review_template_creation(self, template_config, status_system):
        """Test ReadyForReviewTemplate can be created."""
        template = ReadyForReviewTemplate(template_config, status_system)
        assert template is not None
    
    @patch.object(ReadyForReviewTemplate, 'create_section_block')
    def test_create_checks_section(self, mock_section, template_config, status_system, sample_pr_data):
        """Test CI/CD checks section creation."""
        template = ReadyForReviewTemplate(template_config, status_system)
        mock_section.return_value = {'type': 'section'}
        
        result = template._create_checks_section(sample_pr_data)
        
        mock_section.assert_called_once()
        call_args = mock_section.call_args[0][0]
        assert '3 passed' in call_args
        assert '1 pending' in call_args
    
    def test_get_state_specific_actions(self, template_config, status_system, sample_pr_data):
        """Test state-specific actions for ready for review PR."""
        template = ReadyForReviewTemplate(template_config, status_system)
        actions = template._get_state_specific_actions(sample_pr_data, {})
        
        action_texts = [action['text'] for action in actions]
        assert '✅ Approve' in action_texts
        assert '👀 Start Review' in action_texts


class TestApprovedPRTemplate:
    """Test ApprovedPRTemplate class."""
    
    def test_approved_pr_template_creation(self, template_config, status_system):
        """Test ApprovedPRTemplate can be created."""
        template = ApprovedPRTemplate(template_config, status_system)
        assert template is not None
    
    @patch.object(ApprovedPRTemplate, 'create_section_block')
    def test_create_merge_checklist(self, mock_section, template_config, status_system, sample_pr_data):
        """Test merge readiness checklist creation."""
        template = ApprovedPRTemplate(template_config, status_system)
        mock_section.return_value = {'type': 'section'}
        
        # Set up PR data for successful merge readiness
        pr_data = sample_pr_data.copy()
        pr_data['review_decision'] = 'APPROVED'
        pr_data['mergeable'] = True
        pr_data['mergeable_state'] = 'clean'
        
        result = template._create_merge_checklist(pr_data)
        
        mock_section.assert_called_once()
        call_args = mock_section.call_args[0][0]
        assert 'Merge Readiness Checklist' in call_args
        assert '✅' in call_args  # Should have some passing checks
    
    def test_get_state_specific_actions(self, template_config, status_system, sample_pr_data):
        """Test state-specific actions for approved PR."""
        template = ApprovedPRTemplate(template_config, status_system)
        actions = template._get_state_specific_actions(sample_pr_data, {})
        
        action_texts = [action['text'] for action in actions]
        assert '🚀 Merge' in action_texts


class TestConflictsTemplate:
    """Test ConflictsTemplate class."""
    
    def test_conflicts_template_creation(self, template_config, status_system):
        """Test ConflictsTemplate can be created."""
        template = ConflictsTemplate(template_config, status_system)
        assert template is not None
    
    @patch.object(ConflictsTemplate, 'create_section_block')
    def test_create_resolution_guidance(self, mock_section, template_config, status_system, sample_pr_data):
        """Test conflict resolution guidance creation."""
        template = ConflictsTemplate(template_config, status_system)
        mock_section.return_value = {'type': 'section'}
        
        result = template._create_resolution_guidance(sample_pr_data)
        
        mock_section.assert_called_once()
        call_args = mock_section.call_args[0][0]
        assert 'git checkout feature/auth' in call_args
        assert 'git merge main' in call_args
    
    def test_get_state_specific_actions(self, template_config, status_system, sample_pr_data):
        """Test state-specific actions for PR with conflicts."""
        template = ConflictsTemplate(template_config, status_system)
        actions = template._get_state_specific_actions(sample_pr_data, {})
        
        action_texts = [action['text'] for action in actions]
        assert '🔧 Resolve Conflicts' in action_texts
        assert '📝 View Conflicts' in action_texts


class TestMergedPRTemplate:
    """Test MergedPRTemplate class."""
    
    def test_merged_pr_template_creation(self, template_config, status_system):
        """Test MergedPRTemplate can be created."""
        template = MergedPRTemplate(template_config, status_system)
        assert template is not None
    
    @patch.object(MergedPRTemplate, 'create_section_block')
    def test_create_deployment_section(self, mock_section, template_config, status_system, sample_pr_data):
        """Test deployment status section creation."""
        template = MergedPRTemplate(template_config, status_system)
        mock_section.return_value = {'type': 'section'}
        
        # Add deployment data
        pr_data = sample_pr_data.copy()
        pr_data['deployments'] = [
            {'environment': 'staging', 'status': 'success'},
            {'environment': 'production', 'status': 'pending'}
        ]
        
        result = template._create_deployment_section(pr_data, {})
        
        mock_section.assert_called_once()
        call_args = mock_section.call_args[0][0]
        assert 'Deployment Status' in call_args
        assert 'Staging: success' in call_args
    
    def test_get_state_specific_actions(self, template_config, status_system, sample_pr_data):
        """Test state-specific actions for merged PR."""
        template = MergedPRTemplate(template_config, status_system)
        actions = template._get_state_specific_actions(sample_pr_data, {})
        
        action_texts = [action['text'] for action in actions]
        assert '🗑️ Delete Branch' in action_texts
        assert '🚀 Deploy' in action_texts


class TestClosedPRTemplate:
    """Test ClosedPRTemplate class."""
    
    def test_closed_pr_template_creation(self, template_config, status_system):
        """Test ClosedPRTemplate can be created."""
        template = ClosedPRTemplate(template_config, status_system)
        assert template is not None
    
    def test_create_closure_summary(self, template_config, status_system, sample_pr_data):
        """Test closure summary creation."""
        template = ClosedPRTemplate(template_config, status_system)
        
        # Add closure data
        pr_data = sample_pr_data.copy()
        pr_data['closed_at'] = '2024-01-16T10:00:00Z'
        pr_data['review_decision'] = 'CHANGES_REQUESTED'
        pr_data['comments'] = 5
        
        fields = template._create_closure_summary(pr_data)
        
        assert 'Duration' in fields
        assert 'Final Review Status' in fields
        assert 'Comments' in fields
        assert fields['Comments'] == '5'
    
    def test_get_state_specific_actions(self, template_config, status_system, sample_pr_data):
        """Test state-specific actions for closed PR."""
        template = ClosedPRTemplate(template_config, status_system)
        actions = template._get_state_specific_actions(sample_pr_data, {})
        
        action_texts = [action['text'] for action in actions]
        assert '🔄 Reopen' in action_texts
        assert '📋 Create New PR' in action_texts


class TestPRTemplateIntegration:
    """Integration tests for PR templates."""
    
    @patch.object(PRTemplate, 'create_section_block')
    @patch.object(PRTemplate, 'create_fields_section')
    @patch.object(PRTemplate, '_create_header_section')
    @patch.object(PRTemplate, '_create_action_buttons')
    def test_format_message_integration(self, mock_actions, mock_header, mock_fields, mock_section, 
                                      template_config, status_system, sample_pr_data):
        """Test complete message formatting integration."""
        template = NewPRTemplate(template_config, status_system)
        
        # Mock all the methods to return test data
        mock_header.return_value = [{'type': 'header'}]
        mock_section.return_value = {'type': 'section'}
        mock_fields.return_value = {'type': 'section', 'fields': []}
        mock_actions.return_value = {'type': 'actions'}
        
        # Mock the parent class methods
        with patch.object(template, 'create_review_section', return_value={'type': 'section'}):
            with patch.object(template, 'add_branding', side_effect=lambda x: x):
                with patch.object(template, 'create_timestamp_context', return_value={'type': 'context'}):
                    with patch.object(template, 'ensure_accessibility', return_value='fallback text'):
                        message = template.format_message({'pr': sample_pr_data})
        
        assert message is not None
        assert message.blocks is not None
        assert len(message.blocks) > 0
        assert message.text == 'fallback text'
    
    def test_all_templates_have_required_methods(self):
        """Test that all PR template classes implement required methods."""
        template_classes = [
            NewPRTemplate, ReadyForReviewTemplate, ApprovedPRTemplate,
            ConflictsTemplate, MergedPRTemplate, ClosedPRTemplate
        ]
        
        for template_class in template_classes:
            # Check that the class has the required abstract method
            assert hasattr(template_class, '_create_pr_content')
            assert callable(getattr(template_class, '_create_pr_content'))
            
            # Check that it can be instantiated
            template = template_class()
            assert template is not None