"""
Comprehensive integration tests for the complete template system.
Tests end-to-end message creation workflows and validates configuration loading.
"""

import pytest
import json
from datetime import datetime
from typing import Dict, Any

from devsync_ai.core.template_registry import (
    TemplateRegistry, initialize_template_system, create_end_to_end_message,
    load_template_configuration
)
from devsync_ai.core.template_factory import MessageTemplateFactory, TemplateType
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.core.exceptions import TemplateError


class TestTemplateIntegration:
    """Test complete template system integration."""
    
    @pytest.fixture
    def factory(self):
        """Create a fresh factory for testing."""
        return MessageTemplateFactory()
    
    @pytest.fixture
    def registry(self, factory):
        """Create a registry with the test factory."""
        return TemplateRegistry(factory)
    
    @pytest.fixture
    def sample_config(self):
        """Create sample template configuration."""
        return TemplateConfig(
            team_id="test_team",
            branding={"primary_color": "#1f77b4", "logo_emoji": ":gear:"},
            emoji_set={"success": ":white_check_mark:", "warning": ":warning:"},
            interactive_elements=True,
            accessibility_mode=False
        )
    
    def test_register_all_templates(self, registry):
        """Test that all templates are registered successfully."""
        # Initially no templates registered
        assert len(registry.registered_templates) == 0
        
        # Register all templates
        registry.register_all_templates()
        
        # Verify all template types are covered
        expected_templates = [
            "standup_daily",
            "pr_new", "pr_ready", "pr_approved", "pr_conflicts", "pr_merged", "pr_closed",
            "jira_status", "jira_priority", "jira_assignment", "jira_comment", "jira_blocker", "jira_sprint",
            "alert_build", "alert_deployment", "alert_security", "alert_outage", "alert_bug"
        ]
        
        assert len(registry.registered_templates) == len(expected_templates)
        for template_name in expected_templates:
            assert template_name in registry.registered_templates
        
        # Verify factory has all templates
        factory_templates = registry.factory.get_registered_templates()
        assert len(factory_templates) == len(expected_templates)
    
    def test_template_validation(self, registry):
        """Test template registration validation."""
        # Register templates
        registry.register_all_templates()
        
        # Validate registration
        validation_results = registry.validate_template_registration()
        
        assert validation_results["total_registered"] > 0
        assert validation_results["factory_registered"] == validation_results["total_registered"]
        assert len(validation_results["validation_errors"]) == 0
        assert len(validation_results["template_types_covered"]) > 0
    
    def test_standup_end_to_end_workflow(self, registry, sample_config):
        """Test complete standup message creation workflow."""
        registry.register_all_templates()
        
        # Sample standup data
        standup_data = {
            "date": "2024-01-15",
            "team": "Engineering Team",
            "team_members": [
                {
                    "name": "alice",
                    "yesterday": "Completed user authentication feature",
                    "today": "Working on API integration",
                    "blockers": []
                },
                {
                    "name": "bob", 
                    "yesterday": "Fixed database performance issues",
                    "today": "Code review and testing",
                    "blockers": ["Waiting for staging environment"]
                }
            ],
            "stats": {
                "prs_merged": 3,
                "prs_open": 2,
                "tickets_closed": 5,
                "commits": 15
            },
            "sprint_progress": {
                "completed": 7,
                "total": 10,
                "story_points": {"completed": 21, "total": 30}
            },
            "action_items": [
                {
                    "title": "Set up staging environment",
                    "assignee": "devops_team",
                    "due_date": "2024-01-16"
                }
            ]
        }
        
        # Create template and format message
        template = registry.factory.create_template(TemplateType.STANDUP, sample_config)
        message = template.format_message(standup_data)
        
        # Validate message structure
        assert message.blocks is not None
        assert len(message.blocks) > 0
        assert message.text is not None  # Fallback text
        assert message.metadata is not None
        assert message.metadata["template_type"] == "StandupTemplate"
        
        # Validate content includes key elements
        message_json = json.dumps(message.blocks)
        assert "Engineering Team" in message_json
        assert "alice" in message_json
        assert "bob" in message_json
        assert "Sprint Progress" in message_json
    
    def test_pr_templates_end_to_end_workflow(self, registry, sample_config):
        """Test complete PR template workflows for all states."""
        registry.register_all_templates()
        
        # Base PR data
        base_pr_data = {
            "pr": {
                "number": 123,
                "title": "Add user authentication feature",
                "html_url": "https://github.com/company/repo/pull/123",
                "user": {"login": "alice"},
                "head": {"ref": "feature/auth"},
                "base": {"ref": "main"},
                "reviewers": [
                    {"login": "bob", "review_status": "pending"},
                    {"login": "charlie", "review_status": "approved"}
                ],
                "labels": [{"name": "feature"}, {"name": "backend"}],
                "priority": "high"
            }
        }
        
        # Test different PR states
        pr_test_cases = [
            (TemplateType.PR_NEW, "NewPRTemplate"),
            (TemplateType.PR_READY, "ReadyForReviewTemplate"),
            (TemplateType.PR_APPROVED, "ApprovedPRTemplate"),
            (TemplateType.PR_CONFLICTS, "ConflictsTemplate"),
            (TemplateType.PR_MERGED, "MergedPRTemplate"),
            (TemplateType.PR_CLOSED, "ClosedPRTemplate")
        ]
        
        for template_type, expected_class_name in pr_test_cases:
            template = registry.factory.create_template(template_type, sample_config)
            message = template.format_message(base_pr_data)
            
            # Validate message structure
            assert message.blocks is not None
            assert len(message.blocks) > 0
            assert message.metadata["template_type"] == expected_class_name
            
            # Validate PR content
            message_json = json.dumps(message.blocks)
            assert "PR #123" in message_json
            assert "Add user authentication feature" in message_json
    
    def test_jira_templates_end_to_end_workflow(self, registry, sample_config):
        """Test complete JIRA template workflows."""
        registry.register_all_templates()
        
        # Base JIRA data
        base_jira_data = {
            "ticket": {
                "key": "DEV-456",
                "summary": "Implement user dashboard",
                "status": "In Progress",
                "priority": "High",
                "assignee": "alice",
                "reporter": "product_manager"
            }
        }
        
        # Test different JIRA events
        jira_test_cases = [
            (TemplateType.JIRA_STATUS, {"from_status": "To Do", "to_status": "In Progress"}, "StatusChangeTemplate"),
            (TemplateType.JIRA_PRIORITY, {"from_priority": "Medium", "to_priority": "High"}, "PriorityChangeTemplate"),
            (TemplateType.JIRA_ASSIGNMENT, {"from_assignee": "Unassigned", "to_assignee": "alice"}, "AssignmentTemplate"),
            (TemplateType.JIRA_COMMENT, {"comment": {"author": "bob", "body": "Great progress!", "created": "2024-01-15T10:00:00Z"}}, "CommentTemplate"),
            (TemplateType.JIRA_BLOCKER, {"blocker_status": "identified", "blocker_description": "API dependency unavailable"}, "BlockerTemplate")
        ]
        
        for template_type, extra_data, expected_class_name in jira_test_cases:
            test_data = {**base_jira_data, **extra_data}
            template = registry.factory.create_template(template_type, sample_config)
            message = template.format_message(test_data)
            
            # Validate message structure
            assert message.blocks is not None
            assert len(message.blocks) > 0
            assert message.metadata["template_type"] == expected_class_name
            
            # Validate JIRA content
            message_json = json.dumps(message.blocks)
            assert "DEV-456" in message_json
            assert "Implement user dashboard" in message_json
    
    def test_alert_templates_end_to_end_workflow(self, registry, sample_config):
        """Test complete alert template workflows."""
        registry.register_all_templates()
        
        # Base alert data
        base_alert_data = {
            "alert": {
                "id": "alert_789",
                "title": "Critical System Issue",
                "description": "Database connection failure",
                "severity": "critical",
                "type": "service_outage",
                "affected_systems": ["user-service", "payment-service"],
                "created_at": "2024-01-15T10:00:00Z"
            }
        }
        
        # Test different alert types
        alert_test_cases = [
            (TemplateType.ALERT_BUILD, {"build_info": {"branch": "main", "commit": "abc123", "failed_stage": "tests"}}, "BuildFailureTemplate"),
            (TemplateType.ALERT_DEPLOYMENT, {"deployment_info": {"environment": "production", "version": "v1.2.3", "rollback_available": True}}, "DeploymentIssueTemplate"),
            (TemplateType.ALERT_SECURITY, {"security_info": {"cve_id": "CVE-2024-0001", "cvss_score": 9.8}}, "SecurityVulnerabilityTemplate"),
            (TemplateType.ALERT_OUTAGE, {"outage_info": {"services": ["api", "web"], "users_affected": 1000}}, "ServiceOutageTemplate"),
            (TemplateType.ALERT_BUG, {}, "CriticalBugTemplate")
        ]
        
        for template_type, extra_data, expected_class_name in alert_test_cases:
            test_data = {**base_alert_data, **extra_data}
            template = registry.factory.create_template(template_type, sample_config)
            message = template.format_message(test_data)
            
            # Validate message structure
            assert message.blocks is not None
            assert len(message.blocks) > 0
            assert message.metadata["template_type"] == expected_class_name
            
            # Validate alert content
            message_json = json.dumps(message.blocks)
            assert "Critical System Issue" in message_json
            assert "ALERT" in message_json
    
    def test_event_type_mapping(self, registry, sample_config):
        """Test event type to template mapping."""
        registry.register_all_templates()
        
        # Test event mappings
        event_test_cases = [
            ("standup.daily", {"date": "2024-01-15", "team": "Test Team", "team_members": []}),
            ("pull_request.opened", {"pr": {"number": 1, "title": "Test PR"}}),
            ("jira.status_changed", {"ticket": {"key": "TEST-1", "summary": "Test"}, "from_status": "To Do", "to_status": "Done"}),
            ("alert.build_failure", {"alert": {"id": "1", "title": "Build Failed", "severity": "high"}, "build_info": {}})
        ]
        
        for event_type, event_data in event_test_cases:
            template = registry.factory.get_template_by_event_type(event_type, event_data, sample_config)
            message = template.format_message(event_data)
            
            assert message.blocks is not None
            assert len(message.blocks) > 0
    
    def test_configuration_loading_and_customization(self, registry, tmp_path):
        """Test configuration loading and template customization."""
        # Create test configuration file
        config_data = {
            "template_config": {
                "team_id": "custom_team",
                "branding": {
                    "primary_color": "#ff0000",
                    "logo_emoji": ":rocket:"
                },
                "emoji_set": {
                    "success": ":tada:",
                    "warning": ":exclamation:"
                },
                "interactive_elements": False,
                "accessibility_mode": True
            }
        }
        
        config_file = tmp_path / "test_config.yaml"
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Load configuration
        loaded_config = load_template_configuration(str(config_file))
        
        assert loaded_config is not None
        assert loaded_config.team_id == "custom_team"
        assert loaded_config.branding["primary_color"] == "#ff0000"
        assert loaded_config.interactive_elements is False
        assert loaded_config.accessibility_mode is True
        
        # Test template with custom configuration
        registry.register_all_templates()
        template = registry.factory.create_template(TemplateType.STANDUP, loaded_config)
        
        # Verify configuration is applied
        assert template.config.team_id == "custom_team"
        assert template.config.accessibility_mode is True
    
    def test_initialize_template_system(self):
        """Test complete template system initialization."""
        factory = initialize_template_system()
        
        # Verify factory is properly configured
        assert factory is not None
        
        # Verify all templates are registered
        registered_templates = factory.get_registered_templates()
        assert len(registered_templates) > 0
        
        # Test creating templates
        template = factory.create_template(TemplateType.STANDUP)
        assert template is not None
    
    def test_create_end_to_end_message_function(self):
        """Test the end-to-end message creation function."""
        # Initialize system first
        initialize_template_system()
        
        # Test standup message creation
        event_data = {
            "date": "2024-01-15",
            "team": "Test Team",
            "team_members": [
                {"name": "alice", "yesterday": "Worked on feature", "today": "Continue work", "blockers": []}
            ],
            "stats": {"prs_merged": 1, "commits": 5}
        }
        
        message_dict = create_end_to_end_message("standup.daily", event_data)
        
        # Validate message dictionary
        assert "blocks" in message_dict
        assert "text" in message_dict
        assert "metadata" in message_dict
        assert len(message_dict["blocks"]) > 0
    
    def test_error_handling_in_integration(self, registry):
        """Test error handling in integration workflows."""
        registry.register_all_templates()
        
        # Test with invalid event type
        with pytest.raises(TemplateError):
            registry.factory.get_template_by_event_type("invalid.event", {})
        
        # Test with missing required data - should handle gracefully with placeholders
        template = registry.factory.create_template(TemplateType.STANDUP)
        message = template.format_message({})  # Missing required fields
        
        # Should create message with placeholder values instead of raising exception
        assert message.blocks is not None
        assert len(message.blocks) > 0
        assert message.text is not None
    
    def test_caching_in_integration(self, registry, sample_config):
        """Test template caching in integration workflows."""
        registry.register_all_templates()
        
        # Create same template multiple times
        template1 = registry.factory.create_template(TemplateType.STANDUP, sample_config, use_cache=True)
        template2 = registry.factory.create_template(TemplateType.STANDUP, sample_config, use_cache=True)
        
        # Should be same instance due to caching
        assert template1 is template2
        
        # Check cache stats
        cache_stats = registry.factory.get_cache_stats()
        assert cache_stats["total_entries"] > 0
    
    def test_performance_metrics_in_integration(self, registry, sample_config):
        """Test performance metrics collection in integration."""
        registry.register_all_templates()
        
        # Create templates and measure performance
        for _ in range(5):
            template = registry.factory.create_template(TemplateType.STANDUP, sample_config)
            message = template.format_message({
                "date": "2024-01-15",
                "team": "Test Team", 
                "team_members": []
            })
        
        # Check metrics
        metrics = registry.factory.get_template_metrics()
        assert len(metrics) > 0
        
        standup_metrics = metrics.get("standup")
        if standup_metrics:
            assert "usage_count" in standup_metrics
            assert standup_metrics["usage_count"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])