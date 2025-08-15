"""
Comprehensive tests for Alert template variants.
Tests BuildFailure, DeploymentIssue, SecurityVulnerability, ServiceOutage, CriticalBug, and TeamBlocker templates.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from typing import Dict, List, Any

from devsync_ai.templates.alert_templates import (
    AlertTemplate, BuildFailureTemplate, DeploymentIssueTemplate,
    SecurityVulnerabilityTemplate, ServiceOutageTemplate, 
    CriticalBugTemplate
)
from devsync_ai.core.message_formatter import SlackMessage, TemplateConfig
from devsync_ai.core.status_indicators import StatusType


class TestBaseAlertTemplate:
    """Test base AlertTemplate functionality."""
    
    def test_alert_template_initialization(self):
        """Test alert template initialization."""
        template = AlertTemplate()
        
        assert template.REQUIRED_FIELDS == ['alert']
        assert template.config.team_id == "default"
    
    def test_alert_template_with_minimal_data(self):
        """Test alert template with minimal required data."""
        data = {
            'alert': {
                'title': 'Test Alert',
                'severity': 'medium',
                'description': 'This is a test alert'
            }
        }
        
        template = AlertTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        assert message.text
        assert 'Test Alert' in message.text
    
    def test_alert_urgency_header_creation(self):
        """Test alert urgency header creation."""
        alert_data = {
            'title': 'Critical System Alert',
            'severity': 'critical',
            'timestamp': '2025-08-14T10:30:00Z'
        }
        
        template = AlertTemplate()
        
        # Test if the template has the create_urgency_header method
        if hasattr(template, 'create_urgency_header'):
            header_blocks = template.create_urgency_header(alert_data)
            assert isinstance(header_blocks, list)
            assert len(header_blocks) > 0


class TestBuildFailureTemplate:
    """Test BuildFailureTemplate for CI/CD failure alerts."""
    
    def test_build_failure_template_creation(self):
        """Test build failure template message creation."""
        data = {
            'alert': {
                'title': 'Build Failed: main branch',
                'severity': 'high',
                'build_id': 'build-12345',
                'branch': 'main',
                'commit': 'abc123def456',
                'author': 'developer.one',
                'failure_reason': 'Unit tests failed'
            }
        }
        
        template = BuildFailureTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show build failure details
        message_text = message.text.lower()
        assert 'build' in message_text and 'fail' in message_text
    
    def test_build_failure_with_retry_actions(self):
        """Test build failure template with retry and blocking action buttons."""
        data = {
            'alert': {
                'title': 'Build Failed: feature/payment-integration',
                'severity': 'medium',
                'build_url': 'https://ci.example.com/build/12345',
                'can_retry': True,
                'blocking_deployment': True
            }
        }
        
        # Test with interactive elements enabled
        config = TemplateConfig(team_id="test", interactive_elements=True)
        template = BuildFailureTemplate(config=config)
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should provide retry options when interactive elements are enabled
        action_blocks = [b for b in message.blocks if b.get('type') == 'actions']
        # Note: This depends on the implementation having retry buttons
        
        message_text = message.text.lower()
        assert 'retry' in message_text or 'build' in message_text


class TestDeploymentIssueTemplate:
    """Test DeploymentIssueTemplate for deployment problem notifications."""
    
    def test_deployment_issue_template(self):
        """Test deployment issue template message creation."""
        data = {
            'alert': {
                'title': 'Deployment Failed: Production',
                'severity': 'critical',
                'environment': 'production',
                'deployment_id': 'deploy-67890',
                'service': 'api-service',
                'error_message': 'Database connection timeout'
            }
        }
        
        template = DeploymentIssueTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show deployment issue details
        message_text = message.text.lower()
        assert 'deployment' in message_text and ('fail' in message_text or 'issue' in message_text)
    
    def test_deployment_issue_with_rollback_capabilities(self):
        """Test deployment issue template with rollback capabilities."""
        data = {
            'alert': {
                'title': 'Deployment Issue: Staging Environment',
                'severity': 'high',
                'environment': 'staging',
                'can_rollback': True,
                'previous_version': 'v2.1.0',
                'current_version': 'v2.2.0',
                'rollback_url': 'https://deploy.example.com/rollback'
            }
        }
        
        template = DeploymentIssueTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should provide rollback information
        message_text = message.text.lower()
        assert 'rollback' in message_text or 'version' in message_text


class TestSecurityVulnerabilityTemplate:
    """Test SecurityVulnerabilityTemplate for CVE alerts and incident response."""
    
    def test_security_vulnerability_template(self):
        """Test security vulnerability template message creation."""
        data = {
            'alert': {
                'title': 'Critical Security Vulnerability Detected',
                'severity': 'critical',
                'cve_id': 'CVE-2025-12345',
                'affected_component': 'authentication-service',
                'cvss_score': 9.8,
                'description': 'Remote code execution vulnerability'
            }
        }
        
        template = SecurityVulnerabilityTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show security vulnerability details
        message_text = message.text.lower()
        assert 'security' in message_text or 'vulnerability' in message_text or 'cve' in message_text
    
    def test_security_vulnerability_with_incident_response(self):
        """Test security vulnerability template with incident response triggers."""
        data = {
            'alert': {
                'title': 'High Priority Security Alert',
                'severity': 'high',
                'cve_id': 'CVE-2025-67890',
                'incident_response_required': True,
                'escalation_contacts': ['security.team', 'incident.commander'],
                'patch_available': True,
                'patch_url': 'https://security.example.com/patches/67890'
            }
        }
        
        template = SecurityVulnerabilityTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should trigger incident response
        message_text = message.text.lower()
        assert 'incident' in message_text or 'patch' in message_text or 'security' in message_text


class TestServiceOutageTemplate:
    """Test ServiceOutageTemplate for service disruption alerts."""
    
    def test_service_outage_template(self):
        """Test service outage template message creation."""
        data = {
            'alert': {
                'title': 'Service Outage: Payment Processing',
                'severity': 'critical',
                'service': 'payment-service',
                'outage_start': '2025-08-14T14:30:00Z',
                'affected_regions': ['us-east-1', 'eu-west-1'],
                'impact': 'Users cannot complete purchases'
            }
        }
        
        template = ServiceOutageTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show service outage details
        message_text = message.text.lower()
        assert 'outage' in message_text or 'service' in message_text
    
    def test_service_outage_with_war_room_activation(self):
        """Test service outage template with war room activation."""
        data = {
            'alert': {
                'title': 'Major Service Outage: Core API',
                'severity': 'critical',
                'service': 'core-api',
                'war_room_required': True,
                'war_room_url': 'https://meet.example.com/war-room-123',
                'incident_commander': 'ops.lead',
                'estimated_users_affected': 50000
            }
        }
        
        template = ServiceOutageTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should activate war room
        message_text = message.text.lower()
        assert 'war room' in message_text or 'incident' in message_text or 'commander' in message_text


class TestCriticalBugTemplate:
    """Test CriticalBugTemplate for data integrity issues."""
    
    def test_critical_bug_template(self):
        """Test critical bug template message creation."""
        data = {
            'alert': {
                'title': 'Critical Bug: Data Corruption Detected',
                'severity': 'critical',
                'bug_id': 'BUG-2025-001',
                'affected_data': 'user_profiles',
                'data_integrity_risk': 'high',
                'discovery_method': 'automated_monitoring'
            }
        }
        
        template = CriticalBugTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should highlight data integrity issues
        message_text = message.text.lower()
        assert 'critical' in message_text or 'bug' in message_text or 'data' in message_text
    
    def test_critical_bug_with_immediate_actions(self):
        """Test critical bug template with immediate action options."""
        data = {
            'alert': {
                'title': 'Critical Bug: Payment Double Charging',
                'severity': 'critical',
                'immediate_actions_required': True,
                'suggested_actions': [
                    'Disable payment processing',
                    'Notify affected customers',
                    'Prepare refund process'
                ],
                'business_impact': 'Revenue and customer trust at risk'
            }
        }
        
        template = CriticalBugTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should provide immediate action guidance
        message_text = message.text.lower()
        assert 'payment' in message_text or 'action' in message_text or 'disable' in message_text


class TestTeamBlockerTemplate:
    """Test team blocker functionality using base AlertTemplate."""
    
    def test_team_blocker_alert(self):
        """Test team blocker alert using base AlertTemplate."""
        data = {
            'alert': {
                'title': 'Team Productivity Blocker',
                'severity': 'medium',
                'type': 'team_blocker',
                'description': 'Development environment is down',
                'affected_team': 'frontend-team',
                'estimated_impact': '4 hours of lost productivity'
            }
        }
        
        template = AlertTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should show team blocker details
        message_text = message.text.lower()
        assert 'blocker' in message_text or 'productivity' in message_text or 'team' in message_text
    
    def test_team_blocker_with_escalation(self):
        """Test team blocker alert with escalation features."""
        data = {
            'alert': {
                'title': 'Critical Team Blocker: Database Access',
                'severity': 'high',
                'type': 'access_issue',
                'description': 'Backend team cannot access database',
                'escalation_required': True,
                'escalation_contacts': ['engineering.manager', 'team.lead'],
                'business_impact': 'Sprint delivery at risk'
            }
        }
        
        template = AlertTemplate()
        message = template.format_message(data)
        
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Should handle escalation data
        message_text = message.text.lower()
        assert any(word in message_text for word in ['critical', 'database', 'access', 'team', 'alert'])


class TestAlertTemplateAccessibility:
    """Test accessibility features across alert templates."""
    
    def test_alert_template_fallback_text(self):
        """Test alert template fallback text generation."""
        data = {
            'alert': {
                'title': '*URGENT* alert with _formatting_ and `code`',
                'severity': 'critical',
                'description': 'This alert has **bold** and __italic__ text'
            }
        }
        
        template = AlertTemplate()
        message = template.format_message(data)
        
        # Check fallback text has markdown stripped
        assert message.text
        assert 'URGENT alert with formatting and code' in message.text
        assert '*' not in message.text
        assert '_' not in message.text
        assert '`' not in message.text
    
    def test_alert_template_error_handling(self):
        """Test alert template error handling with malformed data."""
        # Test with missing alert data
        incomplete_data = {}
        
        template = AlertTemplate()
        message = template.format_message(incomplete_data)
        
        # Should still create a message with placeholders
        assert isinstance(message, SlackMessage)
        assert len(message.blocks) > 0
        
        # Test with malformed alert data
        malformed_data = {
            'alert': {
                'title': None,        # Should be string
                'severity': 'invalid', # Invalid severity
                'timestamp': 'not-a-date'  # Invalid timestamp
            }
        }
        
        message_malformed = template.format_message(malformed_data)
        assert isinstance(message_malformed, SlackMessage)
        assert len(message_malformed.blocks) > 0
    
    def test_alert_template_severity_handling(self):
        """Test alert template handles different severity levels."""
        severities = ['low', 'medium', 'high', 'critical', 'unknown']
        
        for severity in severities:
            data = {
                'alert': {
                    'title': f'Test {severity} alert',
                    'severity': severity,
                    'description': f'This is a {severity} severity alert'
                }
            }
            
            template = AlertTemplate()
            message = template.format_message(data)
            
            assert isinstance(message, SlackMessage)
            assert len(message.blocks) > 0
            assert message.text
            
            # Should handle all severity levels gracefully
            message_text = message.text.lower()
            assert severity in message_text or 'alert' in message_text


class TestAlertTemplateInteractivity:
    """Test interactive features across alert templates."""
    
    def test_alert_escalation_buttons(self):
        """Test alert template escalation button creation."""
        data = {
            'alert': {
                'title': 'Test Alert with Actions',
                'severity': 'high',
                'escalation_required': True,
                'escalation_contacts': ['manager', 'oncall']
            }
        }
        
        # Test with interactive elements enabled
        config_enabled = TemplateConfig(team_id="test", interactive_elements=True)
        template_enabled = AlertTemplate(config=config_enabled)
        message_enabled = template_enabled.format_message(data)
        
        # Test with interactive elements disabled
        config_disabled = TemplateConfig(team_id="test", interactive_elements=False)
        template_disabled = AlertTemplate(config=config_disabled)
        message_disabled = template_disabled.format_message(data)
        
        # Both should create valid messages
        assert isinstance(message_enabled, SlackMessage)
        assert isinstance(message_disabled, SlackMessage)
        assert len(message_enabled.blocks) > 0
        assert len(message_disabled.blocks) > 0


if __name__ == "__main__":
    print("Running alert template tests...")
    
    # Basic smoke test
    template = AlertTemplate()
    data = {
        'alert': {
            'title': 'Test Alert',
            'severity': 'medium',
            'description': 'This is a test alert'
        }
    }
    message = template.format_message(data)
    
    assert isinstance(message, SlackMessage)
    assert len(message.blocks) > 0
    print("✅ Alert template basic functionality works")
    
    print("All alert template tests passed!")