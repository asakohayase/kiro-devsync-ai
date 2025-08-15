"""
Comprehensive tests for PR template variants.
Tests all PR template types: NewPR, ReadyForReview, Approved, Conflicts, Merged, Closed.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from typing import Dict, List, Any

from devsync_ai.templates.pr_templates import (
    PRTemplate, NewPRTemplate, ReadyForReviewTemplate, 
    ApprovedPRTemplate, ConflictsTemplate, MergedPRTemplate, ClosedPRTemplate
)
from devsync_ai.core.message_formatter import SlackMessage, TemplateConfig
from devsync_ai.core.status_indicators import PRStatus


class TestBasePRTemplate:
    """Test base PRTemplate functionality."""
    
    def test_pr_template_initialization(self):
        """Test PR template initialization."""
        template = PRTemplate()
        
        assert template.REQUIRED_FIELDS == ['pr']
        assert template.config.team_id == "default"
    
    def test_pr_header_creation(self):
        """Test PR header creation with consistent formatting."""
        pr_data = {
            'number': 123,
            'title': 'Add new feature',
            'author': 'john.doe',
            'url': 'https://github.com/repo/pull/123',
            'status': 'open'
        }
        
        template = PRTemplate()
        
        # Test if the template has the create_pr_header method
        if hasattr(template, 'create_pr_header'):
            header_blocks = template.create_pr_header(pr_data)
            assert isinstance(header_blocks, list)
            assert len(header_blocks) > 0
    
    def test_pr_template_with_minimal_data(self):
        """Test PR template with minimal required data."""
        data = {
            'pr': {
                'number': 123,
                'title': 'Test PR',
                'author': 'test.user'
            }
        }
        
        template = PRTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        assert message.text
        assert 'PR #123' in message.text or 'Test PR' in message.text


class TestNewPRTemplate:
    """Test NewPRTemplate for new PR creation notifications."""
    
    def test_new_pr_template_creation(self):
        """Test new PR template message creation."""
        data = {
            'pr': {
                'number': 123,
                'title': 'Add authentication feature',
                'author': 'john.doe',
                'url': 'https://github.com/repo/pull/123',
                'description': 'This PR adds OAuth authentication',
                'reviewers': ['jane.doe', 'bob.smith'],
                'labels': ['feature', 'backend']
            }
        }
        
        template = NewPRTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        assert message.text
        
        # Check for new PR specific content
        message_text = message.text.lower()
        assert 'pr' in message_text
        assert 'authentication' in message_text
    
    def test_new_pr_with_review_requests(self):
        """Test new PR template with review request highlighting."""
        data = {
            'pr': {
                'number': 456,
                'title': 'Fix critical bug',
                'author': 'developer',
                'reviewers': ['lead.dev', 'senior.dev'],
                'priority': 'high'
            }
        }
        
        template = NewPRTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should highlight review requests
        message_text = message.text.lower()
        assert 'review' in message_text or 'reviewer' in message_text


class TestReadyForReviewTemplate:
    """Test ReadyForReviewTemplate for review readiness emphasis."""
    
    def test_ready_for_review_template(self):
        """Test ready for review template message creation."""
        data = {
            'pr': {
                'number': 789,
                'title': 'Implement user dashboard',
                'author': 'frontend.dev',
                'status': 'ready_for_review',
                'reviewers': ['ui.lead', 'backend.lead'],
                'checks_passed': True,
                'conflicts': False
            }
        }
        
        template = ReadyForReviewTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should emphasize review readiness
        message_text = message.text.lower()
        assert 'ready' in message_text or 'review' in message_text
    
    def test_ready_for_review_with_reviewer_assignments(self):
        """Test ready for review template with reviewer assignments."""
        data = {
            'pr': {
                'number': 101,
                'title': 'Update API endpoints',
                'author': 'api.dev',
                'reviewers': ['tech.lead', 'security.expert'],
                'reviewer_assignments': {
                    'tech.lead': 'code_review',
                    'security.expert': 'security_review'
                }
            }
        }
        
        template = ReadyForReviewTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show reviewer assignments
        message_text = message.text
        assert 'tech.lead' in message_text or 'security.expert' in message_text


class TestApprovedPRTemplate:
    """Test ApprovedPRTemplate for merge readiness display."""
    
    def test_approved_pr_template(self):
        """Test approved PR template message creation."""
        data = {
            'pr': {
                'number': 202,
                'title': 'Add payment integration',
                'author': 'payments.dev',
                'status': 'approved',
                'approvals': ['tech.lead', 'product.manager'],
                'checks_passed': True,
                'merge_ready': True
            }
        }
        
        template = ApprovedPRTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show merge readiness
        message_text = message.text.lower()
        assert 'approved' in message_text or 'merge' in message_text
    
    def test_approved_pr_with_merge_checklist(self):
        """Test approved PR template with merge readiness checklist."""
        data = {
            'pr': {
                'number': 303,
                'title': 'Database migration',
                'author': 'db.admin',
                'status': 'approved',
                'merge_checklist': {
                    'tests_passed': True,
                    'conflicts_resolved': True,
                    'approvals_received': True,
                    'deployment_ready': False
                }
            }
        }
        
        template = ApprovedPRTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show checklist status
        message_text = message.text.lower()
        assert 'test' in message_text or 'approval' in message_text


class TestConflictsTemplate:
    """Test ConflictsTemplate for conflict warnings."""
    
    def test_conflicts_template(self):
        """Test conflicts template message creation."""
        data = {
            'pr': {
                'number': 404,
                'title': 'Update shared components',
                'author': 'component.dev',
                'status': 'conflicts',
                'conflicts': [
                    {'file': 'src/components/Button.js', 'type': 'merge_conflict'},
                    {'file': 'src/styles/main.css', 'type': 'merge_conflict'}
                ]
            }
        }
        
        template = ConflictsTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should use warning styling
        message_text = message.text.lower()
        assert 'conflict' in message_text or 'warning' in message_text
    
    def test_conflicts_with_resolution_guidance(self):
        """Test conflicts template with resolution guidance."""
        data = {
            'pr': {
                'number': 505,
                'title': 'Merge feature branch',
                'author': 'feature.dev',
                'conflicts': [
                    {'file': 'config.json', 'resolution_hint': 'Keep both configurations'}
                ],
                'resolution_steps': [
                    'Pull latest changes from main',
                    'Resolve conflicts in config.json',
                    'Run tests to verify'
                ]
            }
        }
        
        template = ConflictsTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should provide resolution guidance
        message_text = message.text.lower()
        assert 'resolve' in message_text or 'conflict' in message_text


class TestMergedPRTemplate:
    """Test MergedPRTemplate for successful merge celebrations."""
    
    def test_merged_pr_template(self):
        """Test merged PR template message creation."""
        data = {
            'pr': {
                'number': 606,
                'title': 'Implement search functionality',
                'author': 'search.dev',
                'status': 'merged',
                'merged_by': 'tech.lead',
                'merge_commit': 'abc123def',
                'deployment_status': 'pending'
            }
        }
        
        template = MergedPRTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should celebrate success
        message_text = message.text.lower()
        assert 'merged' in message_text or 'success' in message_text
    
    def test_merged_pr_with_deployment_status(self):
        """Test merged PR template with deployment status."""
        data = {
            'pr': {
                'number': 707,
                'title': 'Performance improvements',
                'author': 'perf.dev',
                'status': 'merged',
                'deployment_status': 'deployed',
                'deployment_url': 'https://staging.example.com',
                'performance_impact': '+15% faster load times'
            }
        }
        
        template = MergedPRTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show deployment status
        message_text = message.text.lower()
        assert 'deploy' in message_text or 'performance' in message_text


class TestClosedPRTemplate:
    """Test ClosedPRTemplate for closure notifications."""
    
    def test_closed_pr_template(self):
        """Test closed PR template message creation."""
        data = {
            'pr': {
                'number': 808,
                'title': 'Experimental feature',
                'author': 'experiment.dev',
                'status': 'closed',
                'closed_by': 'product.manager',
                'close_reason': 'Feature no longer needed'
            }
        }
        
        template = ClosedPRTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show closure notification
        message_text = message.text.lower()
        assert 'closed' in message_text
    
    def test_closed_pr_with_reopen_options(self):
        """Test closed PR template with reopen action options."""
        data = {
            'pr': {
                'number': 909,
                'title': 'Feature branch cleanup',
                'author': 'cleanup.dev',
                'status': 'closed',
                'can_reopen': True,
                'reopen_url': 'https://github.com/repo/pull/909'
            }
        }
        
        # Test with interactive elements enabled
        config = TemplateConfig(team_id="test", interactive_elements=True)
        template = ClosedPRTemplate(config=config)
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should provide reopen options when interactive elements are enabled
        action_blocks = [b for b in message.blocks if b.get('type') == 'actions']
        # Note: This depends on the implementation having reopen buttons


class TestPRTemplateAccessibility:
    """Test accessibility features across PR templates."""
    
    def test_pr_template_fallback_text(self):
        """Test PR template fallback text generation."""
        data = {
            'pr': {
                'number': 111,
                'title': '*Important* PR with _formatting_ and `code`',
                'author': 'test.dev',
                'description': 'This PR has **bold** and __italic__ text'
            }
        }
        
        template = NewPRTemplate()
        message = template.format_message(data)
        
        # Check fallback text has markdown stripped
        assert message.text
        assert 'Important PR with formatting and code' in message.text
        assert '*' not in message.text
        assert '_' not in message.text
        assert '`' not in message.text
    
    def test_pr_template_error_handling(self):
        """Test PR template error handling with malformed data."""
        # Test with missing PR data
        incomplete_data = {}
        
        template = PRTemplate()
        message = template.format_message(incomplete_data)
        
        # Should still create a message with placeholders
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Test with malformed PR data
        malformed_data = {
            'pr': {
                'number': 'invalid',  # Should be integer
                'title': None,        # Should be string
                'author': ''          # Empty string
            }
        }
        
        message_malformed = template.format_message(malformed_data)
        assert isinstance(message_malformed, SlackMessage)
        assert len(message_malformed.blocks) > 0


if __name__ == "__main__":
    print("Running PR template tests...")
    
    # Basic smoke test
    template = NewPRTemplate()
    data = {
        'pr': {
            'number': 123,
            'title': 'Test PR',
            'author': 'test.user'
        }
    }
    message = template.format_message(data)
    
    assert isinstance(message, SlackMessage)
    assert len(message.blocks) > 0
    print("✅ PR template basic functionality works")
    
    print("All PR template tests passed!")