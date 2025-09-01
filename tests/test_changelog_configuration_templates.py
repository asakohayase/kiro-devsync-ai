"""
Tests for Changelog Configuration Templates and Guided Setup.

Tests cover template creation, recommendation system, wizard steps, and validation.
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import asdict

from devsync_ai.core.changelog_configuration_templates import (
    ChangelogConfigurationTemplates,
    TeamCategory,
    SetupComplexity,
    WizardStep,
    TemplateRecommendation,
    default_templates
)
from devsync_ai.core.changelog_configuration_manager import (
    TeamChangelogConfig,
    TemplateStyle,
    AudienceType,
    AnalysisDepth,
    ValidationResult
)


class TestChangelogConfigurationTemplates:
    """Test suite for ChangelogConfigurationTemplates."""
    
    @pytest.fixture
    def templates(self):
        """Create templates instance."""
        return ChangelogConfigurationTemplates()
    
    def test_template_initialization(self, templates):
        """Test that templates are properly initialized."""
        assert len(templates._templates) > 0
        assert "engineering_default" in templates._templates
        assert "product_default" in templates._templates
        assert "qa_default" in templates._templates
        assert "minimal_start" in templates._templates
    
    def test_get_template_success(self, templates):
        """Test getting existing template."""
        template = templates.get_template("engineering_default")
        
        assert template is not None
        assert template.template_id == "engineering_default"
        assert template.name == "Engineering Team - Default"
        assert template.category == "engineering"
        assert template.template_config.team_id == "engineering"
    
    def test_get_template_not_found(self, templates):
        """Test getting non-existent template."""
        template = templates.get_template("nonexistent_template")
        assert template is None
    
    def test_list_templates_all(self, templates):
        """Test listing all templates."""
        all_templates = templates.list_templates()
        
        assert len(all_templates) > 0
        template_ids = [t.template_id for t in all_templates]
        assert "engineering_default" in template_ids
        assert "product_default" in template_ids
        assert "qa_default" in template_ids
    
    def test_list_templates_by_category(self, templates):
        """Test listing templates filtered by category."""
        engineering_templates = templates.list_templates(category="engineering")
        
        assert len(engineering_templates) >= 1
        for template in engineering_templates:
            assert template.category == "engineering"
    
    def test_get_wizard_steps_standard(self, templates):
        """Test getting standard wizard steps."""
        steps = templates.get_wizard_steps("standard")
        
        assert len(steps) >= 3
        assert all(isinstance(step, WizardStep) for step in steps)
        assert steps[0].step_number == 1
        assert steps[0].title == "Team Information"
    
    def test_get_wizard_steps_simple(self, templates):
        """Test getting simple wizard steps."""
        steps = templates.get_wizard_steps("simple")
        
        assert len(steps) == 3
        assert steps[0].title == "Team Information"
        assert steps[1].title == "Schedule"
        assert steps[2].title == "Distribution"
    
    def test_get_wizard_steps_advanced(self, templates):
        """Test getting advanced wizard steps."""
        steps = templates.get_wizard_steps("advanced")
        
        assert len(steps) >= 5
        # Advanced should have all standard steps plus more
        titles = [step.title for step in steps]
        assert "Advanced Content" in titles
        assert "Interactive Features" in titles
        assert "Notifications" in titles
    
    def test_recommend_template_engineering(self, templates):
        """Test template recommendation for engineering team."""
        characteristics = {
            "team_type": "engineering",
            "technical_level": "advanced",
            "team_size": "large",
            "primary_tools": ["github", "jira"],
            "communication_style": "technical"
        }
        
        recommendations = templates.recommend_template(characteristics)
        
        assert len(recommendations) > 0
        assert recommendations[0].template_id == "engineering_advanced"
        assert recommendations[0].confidence_score > 0.9
        assert "advanced engineering" in recommendations[0].reasoning.lower()
    
    def test_recommend_template_product(self, templates):
        """Test template recommendation for product team."""
        characteristics = {
            "team_type": "product",
            "technical_level": "basic",
            "team_size": "medium",
            "focus_areas": ["stakeholder"],
            "communication_style": "executive"
        }
        
        recommendations = templates.recommend_template(characteristics)
        
        assert len(recommendations) > 0
        assert recommendations[0].template_id == "product_stakeholder"
        assert recommendations[0].confidence_score > 0.9
    
    def test_recommend_template_qa(self, templates):
        """Test template recommendation for QA team."""
        characteristics = {
            "team_type": "qa",
            "technical_level": "advanced",
            "primary_tools": ["automation", "testing"]
        }
        
        recommendations = templates.recommend_template(characteristics)
        
        assert len(recommendations) > 0
        assert recommendations[0].template_id == "qa_comprehensive"
        assert recommendations[0].confidence_score > 0.9
    
    def test_recommend_template_fallback(self, templates):
        """Test template recommendation fallback for unknown team type."""
        characteristics = {
            "team_type": "unknown",
            "technical_level": "basic",
            "team_size": "small"
        }
        
        recommendations = templates.recommend_template(characteristics)
        
        assert len(recommendations) > 0
        assert recommendations[0].template_id == "minimal_start"
        assert recommendations[0].confidence_score == 0.7
    
    def test_validate_template_customizations_valid(self, templates):
        """Test validation of valid template customizations."""
        customizations = {
            "team_name": "Custom Team Name",
            "schedule.day": "thursday",
            "content.max_commits_displayed": 25
        }
        
        with patch.object(templates, '_is_valid_customization_field', return_value=True):
            with patch.object(templates, '_apply_validation_rule') as mock_rule:
                mock_rule.return_value = ValidationResult(valid=True)
                
                result = templates.validate_template_customizations(
                    "engineering_default",
                    customizations
                )
                
                assert result.valid is True
                assert len(result.errors) == 0
    
    def test_validate_template_customizations_invalid_template(self, templates):
        """Test validation with invalid template ID."""
        result = templates.validate_template_customizations(
            "nonexistent_template",
            {"test": "value"}
        )
        
        assert result.valid is False
        assert "not found" in result.errors[0].lower()
    
    def test_validate_template_customizations_invalid_field(self, templates):
        """Test validation with invalid customization field."""
        customizations = {
            "invalid_field": "value"
        }
        
        with patch.object(templates, '_is_valid_customization_field', return_value=False):
            result = templates.validate_template_customizations(
                "engineering_default",
                customizations
            )
            
            assert result.valid is False
            assert any("invalid customization field" in error.lower() for error in result.errors)
    
    def test_engineering_template_configuration(self, templates):
        """Test engineering template configuration details."""
        template = templates.get_template("engineering_default")
        config = template.template_config
        
        assert config.team_id == "engineering"
        assert config.content.template_style == TemplateStyle.TECHNICAL
        assert config.content.audience_type == AudienceType.TECHNICAL
        assert config.content.include_metrics is True
        assert config.content.include_contributor_recognition is True
        assert config.data_sources["github"].enabled is True
        assert config.data_sources["github"].analysis_depth == AnalysisDepth.COMPREHENSIVE
        assert config.distribution.primary_channel == "#engineering-updates"
        assert "#general" in config.distribution.secondary_channels
    
    def test_product_template_configuration(self, templates):
        """Test product template configuration details."""
        template = templates.get_template("product_default")
        config = template.template_config
        
        assert config.team_id == "product"
        assert config.content.template_style == TemplateStyle.PROFESSIONAL
        assert config.content.audience_type == AudienceType.BUSINESS
        assert config.content.include_metrics is False
        assert config.content.include_contributor_recognition is False
        assert config.data_sources["github"].enabled is False
        assert config.data_sources["jira"].enabled is True
        assert config.distribution.primary_channel == "#product-updates"
    
    def test_qa_template_configuration(self, templates):
        """Test QA template configuration details."""
        template = templates.get_template("qa_default")
        config = template.template_config
        
        assert config.team_id == "qa"
        assert config.content.template_style == TemplateStyle.PROFESSIONAL
        assert config.content.audience_type == AudienceType.TECHNICAL
        assert config.content.include_metrics is True
        assert "quality" in config.content.focus_areas
        assert "testing" in config.content.focus_areas
        assert config.distribution.primary_channel == "#qa-updates"
    
    def test_minimal_template_configuration(self, templates):
        """Test minimal template configuration details."""
        template = templates.get_template("minimal_start")
        config = template.template_config
        
        assert config.team_id == "quickstart"
        assert config.content.template_style == TemplateStyle.PROFESSIONAL
        assert config.content.audience_type == AudienceType.MIXED
        assert config.content.include_metrics is False
        assert config.content.include_contributor_recognition is False
        assert config.data_sources["team_metrics"].enabled is False
        assert config.interactive.enable_feedback_buttons is False
        assert config.interactive.enable_drill_down is False
    
    def test_advanced_engineering_template(self, templates):
        """Test advanced engineering template has enhanced features."""
        template = templates.get_template("engineering_advanced")
        config = template.template_config
        
        assert config.content.include_performance_analysis is True
        assert config.content.max_commits_displayed == 50
        assert "security" in config.content.focus_areas
        assert "architecture" in config.content.focus_areas
        assert "pdf" in config.distribution.export_formats
        assert "rss" in config.distribution.export_formats
        assert len(config.interactive.custom_actions) > 2
    
    def test_product_stakeholder_template(self, templates):
        """Test product stakeholder template configuration."""
        template = templates.get_template("product_stakeholder")
        config = template.template_config
        
        assert config.content.template_style == TemplateStyle.EXECUTIVE
        assert config.content.audience_type == AudienceType.BUSINESS
        assert "business_impact" in config.content.focus_areas
        assert "#executives" in config.distribution.secondary_channels
        assert "#board-updates" in config.distribution.secondary_channels
        
        # Check channel-specific formatting
        formatting = config.distribution.channel_specific_formatting
        assert "#executives" in formatting
        assert formatting["#executives"]["template_style"] == "executive"
        assert formatting["#executives"]["high_level_summary"] is True
    
    def test_qa_comprehensive_template(self, templates):
        """Test QA comprehensive template has advanced features."""
        template = templates.get_template("qa_comprehensive")
        config = template.template_config
        
        assert "performance_testing" in config.content.focus_areas
        assert "security_testing" in config.content.focus_areas
        assert "automation" in config.content.focus_areas
        assert config.content.max_tickets_displayed == 40
        
        # Check for advanced custom actions
        action_labels = [action["label"] for action in config.interactive.custom_actions]
        assert "Performance Metrics" in action_labels
        assert "Security Scan Results" in action_labels
    
    def test_devops_template_configuration(self, templates):
        """Test DevOps template configuration."""
        template = templates.get_template("devops_default")
        config = template.template_config
        
        assert config.team_id == "devops"
        assert config.content.template_style == TemplateStyle.TECHNICAL
        assert config.content.include_performance_analysis is True
        assert "infrastructure" in config.content.focus_areas
        assert "deployment" in config.content.focus_areas
        assert "monitoring" in config.content.focus_areas
        assert "#ops-alerts" in config.distribution.secondary_channels
        assert "#ops-alerts" in config.notifications.escalation_channels
    
    def test_management_template_configuration(self, templates):
        """Test management template configuration."""
        template = templates.get_template("management_executive")
        config = template.template_config
        
        assert config.team_id == "management"
        assert config.content.template_style == TemplateStyle.EXECUTIVE
        assert config.content.audience_type == AudienceType.BUSINESS
        assert config.content.include_contributor_recognition is False
        assert "business_impact" in config.content.focus_areas
        assert "team_productivity" in config.content.focus_areas
        assert config.data_sources["github"].enabled is False
        assert config.interactive.enable_feedback_buttons is False
        assert config.notifications.quiet_hours_enabled is False
    
    def test_design_template_configuration(self, templates):
        """Test design template configuration."""
        template = templates.get_template("design_default")
        config = template.template_config
        
        assert config.team_id == "design"
        assert config.content.template_style == TemplateStyle.CASUAL
        assert config.content.audience_type == AudienceType.MIXED
        assert config.content.include_metrics is False
        assert "user_experience" in config.content.focus_areas
        assert "design_system" in config.content.focus_areas
        assert config.data_sources["github"].enabled is False
        assert config.interactive.enable_drill_down is False
    
    def test_wizard_step_validation_rules(self, templates):
        """Test wizard steps have proper validation rules."""
        steps = templates.get_wizard_steps("simple")
        
        # Find distribution step
        distribution_step = next(step for step in steps if step.title == "Distribution")
        
        assert len(distribution_step.validation_rules) > 0
        
        # Check for required field validation
        required_rule = next(
            rule for rule in distribution_step.validation_rules
            if rule.get("rule") == "required"
        )
        assert required_rule["field"] == "distribution.primary_channel"
        
        # Check for format validation
        format_rule = next(
            rule for rule in distribution_step.validation_rules
            if rule.get("rule") == "starts_with"
        )
        assert format_rule["value"] == "#"
    
    def test_wizard_step_examples(self, templates):
        """Test wizard steps have helpful examples."""
        steps = templates.get_wizard_steps("simple")
        
        # Check team information step has examples
        team_step = steps[0]
        assert "team_id" in team_step.examples
        assert "team_name" in team_step.examples
        assert team_step.examples["team_id"] == "engineering"
        
        # Check schedule step has examples
        schedule_step = steps[1]
        assert "schedule.day" in schedule_step.examples
        assert "schedule.time" in schedule_step.examples
        assert "schedule.timezone" in schedule_step.examples
    
    def test_template_setup_wizard_steps(self, templates):
        """Test that templates have proper setup wizard steps."""
        template = templates.get_template("engineering_default")
        
        assert len(template.setup_wizard_steps) >= 4
        
        # Check step structure
        step = template.setup_wizard_steps[0]
        assert step["step"] == 1
        assert step["title"] == "Team Information"
        assert "fields" in step
        assert "team_id" in step["fields"]
        assert "team_name" in step["fields"]
    
    def test_template_validation_rules(self, templates):
        """Test that templates have validation rules."""
        template = templates.get_template("engineering_default")
        
        assert len(template.validation_rules) > 0
        
        # Check for required fields rule
        required_rule = next(
            rule for rule in template.validation_rules
            if rule.get("rule") == "required_fields"
        )
        assert "team_id" in required_rule["fields"]
        assert "team_name" in required_rule["fields"]
        
        # Check for channel format rule
        channel_rule = next(
            rule for rule in template.validation_rules
            if rule.get("rule") == "channel_format"
        )
        assert channel_rule["pattern"] == "^#.*"
    
    def test_recommendation_confidence_scores(self, templates):
        """Test that recommendations have appropriate confidence scores."""
        # Perfect match should have high confidence
        perfect_match = {
            "team_type": "engineering",
            "technical_level": "advanced",
            "team_size": "large"
        }
        
        recommendations = templates.recommend_template(perfect_match)
        assert recommendations[0].confidence_score >= 0.9
        
        # Partial match should have lower confidence
        partial_match = {
            "team_type": "unknown",
            "technical_level": "basic"
        }
        
        recommendations = templates.recommend_template(partial_match)
        assert recommendations[0].confidence_score <= 0.8
    
    def test_recommendation_customizations(self, templates):
        """Test that recommendations include appropriate customizations."""
        characteristics = {
            "team_type": "engineering",
            "team_size": "large"
        }
        
        recommendations = templates.recommend_template(characteristics)
        
        # Should have customizations for large team
        customizations = recommendations[0].customizations
        assert "content.max_commits_displayed" in customizations
        assert customizations["content.max_commits_displayed"] == 40
    
    def test_default_templates_instance(self):
        """Test that default templates instance is properly initialized."""
        assert default_templates is not None
        assert isinstance(default_templates, ChangelogConfigurationTemplates)
        assert len(default_templates._templates) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])