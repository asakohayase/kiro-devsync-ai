"""
Configuration Templates and Guided Setup for Changelog System.

This module provides pre-built configuration templates and guided setup wizards
for different team types and use cases, making it easy to get started with
the changelog system.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from devsync_ai.core.changelog_configuration_manager import (
    TeamChangelogConfig,
    ScheduleConfig,
    DataSourceConfig,
    ContentConfig,
    DistributionConfig,
    InteractiveConfig,
    NotificationConfig,
    ConfigurationTemplate,
    TemplateStyle,
    AudienceType,
    AnalysisDepth,
    ValidationResult
)


logger = logging.getLogger(__name__)


class TeamCategory(Enum):
    """Team category types for template selection."""
    ENGINEERING = "engineering"
    PRODUCT = "product"
    QA = "qa"
    DESIGN = "design"
    DEVOPS = "devops"
    MANAGEMENT = "management"
    CUSTOM = "custom"


class SetupComplexity(Enum):
    """Setup complexity levels."""
    SIMPLE = "simple"
    STANDARD = "standard"
    ADVANCED = "advanced"


@dataclass
class WizardStep:
    """Configuration wizard step."""
    step_number: int
    title: str
    description: str
    fields: List[str]
    validation_rules: List[Dict[str, Any]] = field(default_factory=list)
    conditional_logic: Optional[Dict[str, Any]] = None
    help_text: Optional[str] = None
    examples: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemplateRecommendation:
    """Template recommendation based on team characteristics."""
    template_id: str
    confidence_score: float
    reasoning: str
    customizations: Dict[str, Any] = field(default_factory=dict)


class ChangelogConfigurationTemplates:
    """
    Configuration templates and guided setup for changelog system.
    
    Provides pre-built templates for different team types and guided
    setup wizards to help teams configure their changelog system.
    """
    
    def __init__(self):
        """Initialize configuration templates."""
        self.logger = logging.getLogger(__name__)
        self._templates: Dict[str, ConfigurationTemplate] = {}
        self._wizard_steps: Dict[str, List[WizardStep]] = {}
        self._setup_templates()
    
    def _setup_templates(self):
        """Setup built-in configuration templates."""
        # Engineering team template
        self._templates["engineering_default"] = self._create_engineering_template()
        self._templates["engineering_advanced"] = self._create_engineering_advanced_template()
        
        # Product team template
        self._templates["product_default"] = self._create_product_template()
        self._templates["product_stakeholder"] = self._create_product_stakeholder_template()
        
        # QA team template
        self._templates["qa_default"] = self._create_qa_template()
        self._templates["qa_comprehensive"] = self._create_qa_comprehensive_template()
        
        # Design team template
        self._templates["design_default"] = self._create_design_template()
        
        # DevOps team template
        self._templates["devops_default"] = self._create_devops_template()
        
        # Management template
        self._templates["management_executive"] = self._create_management_template()
        
        # Minimal template for quick start
        self._templates["minimal_start"] = self._create_minimal_template()
        
        # Setup wizard steps
        self._setup_wizard_steps()
    
    def _create_engineering_template(self) -> ConfigurationTemplate:
        """Create default engineering team template."""
        config = TeamChangelogConfig(
            team_id="engineering",
            team_name="Engineering Team",
            enabled=True,
            version="1.0.0",
            schedule=ScheduleConfig(
                enabled=True,
                day="friday",
                time="16:00",
                timezone="UTC",
                manual_trigger_enabled=True
            ),
            data_sources={
                "github": DataSourceConfig(
                    enabled=True,
                    analysis_depth=AnalysisDepth.COMPREHENSIVE,
                    rate_limit_buffer=150,
                    cache_ttl_minutes=30
                ),
                "jira": DataSourceConfig(
                    enabled=True,
                    analysis_depth=AnalysisDepth.COMPREHENSIVE,
                    cache_ttl_minutes=60
                ),
                "team_metrics": DataSourceConfig(
                    enabled=True,
                    analysis_depth=AnalysisDepth.STANDARD
                )
            },
            content=ContentConfig(
                template_style=TemplateStyle.TECHNICAL,
                audience_type=AudienceType.TECHNICAL,
                include_metrics=True,
                include_contributor_recognition=True,
                include_risk_analysis=True,
                include_performance_analysis=True,
                max_commits_displayed=25,
                max_tickets_displayed=20,
                max_contributors_highlighted=10,
                focus_areas=["code_quality", "performance", "technical_debt"]
            ),
            distribution=DistributionConfig(
                primary_channel="#engineering-updates",
                secondary_channels=["#general", "#tech-leads"],
                channel_specific_formatting={
                    "#general": {
                        "template_style": "professional",
                        "hide_technical_details": True
                    },
                    "#tech-leads": {
                        "template_style": "technical",
                        "include_detailed_metrics": True
                    }
                },
                export_formats=["slack", "markdown", "email"],
                delivery_confirmation=True
            ),
            interactive=InteractiveConfig(
                enable_feedback_buttons=True,
                enable_drill_down=True,
                enable_export_options=True,
                enable_threading=True,
                quick_actions_enabled=True,
                custom_actions=[
                    {
                        "action_id": "view_pr_details",
                        "label": "View PR Details",
                        "type": "button"
                    },
                    {
                        "action_id": "export_technical_report",
                        "label": "Export Technical Report",
                        "type": "button"
                    }
                ]
            ),
            notifications=NotificationConfig(
                notify_on_generation=True,
                notify_on_failure=True,
                notify_on_success=False,
                escalation_channels=["#engineering-alerts"],
                quiet_hours_enabled=True,
                quiet_hours_start="22:00",
                quiet_hours_end="08:00",
                weekend_notifications=False
            )
        )
        
        return ConfigurationTemplate(
            template_id="engineering_default",
            name="Engineering Team - Default",
            description="Comprehensive configuration for engineering teams with technical focus and detailed metrics",
            category="engineering",
            template_config=config,
            setup_wizard_steps=[
                {
                    "step": 1,
                    "title": "Team Information",
                    "description": "Configure basic team information and identification",
                    "fields": ["team_id", "team_name"],
                    "required": True
                },
                {
                    "step": 2,
                    "title": "Schedule Configuration",
                    "description": "Set when your changelogs will be generated and distributed",
                    "fields": ["schedule.day", "schedule.time", "schedule.timezone"],
                    "examples": {
                        "schedule.day": "friday",
                        "schedule.time": "16:00",
                        "schedule.timezone": "America/New_York"
                    }
                },
                {
                    "step": 3,
                    "title": "Data Sources",
                    "description": "Choose which data sources to include in your changelogs",
                    "fields": [
                        "data_sources.github.enabled",
                        "data_sources.jira.enabled",
                        "data_sources.team_metrics.enabled"
                    ]
                },
                {
                    "step": 4,
                    "title": "Content Preferences",
                    "description": "Configure what information to include and how to present it",
                    "fields": [
                        "content.template_style",
                        "content.include_metrics",
                        "content.include_contributor_recognition",
                        "content.max_commits_displayed"
                    ]
                },
                {
                    "step": 5,
                    "title": "Distribution Channels",
                    "description": "Configure where your changelogs will be sent",
                    "fields": [
                        "distribution.primary_channel",
                        "distribution.secondary_channels"
                    ],
                    "validation": [
                        {
                            "field": "distribution.primary_channel",
                            "rule": "required",
                            "message": "Primary channel is required"
                        },
                        {
                            "field": "distribution.primary_channel",
                            "rule": "starts_with",
                            "value": "#",
                            "message": "Channel must start with #"
                        }
                    ]
                }
            ],
            validation_rules=[
                {
                    "rule": "required_fields",
                    "fields": ["team_id", "team_name", "distribution.primary_channel"]
                },
                {
                    "rule": "channel_format",
                    "fields": ["distribution.primary_channel", "distribution.secondary_channels"],
                    "pattern": "^#.*"
                }
            ]
        )
    
    def _create_engineering_advanced_template(self) -> ConfigurationTemplate:
        """Create advanced engineering team template with all features enabled."""
        base_template = self._create_engineering_template()
        config = base_template.template_config
        
        # Enhanced configuration for advanced users
        config.content.include_performance_analysis = True
        config.content.max_commits_displayed = 50
        config.content.max_tickets_displayed = 30
        config.content.focus_areas.extend(["security", "architecture", "dependencies"])
        
        config.distribution.export_formats.extend(["pdf", "rss"])
        config.distribution.webhook_urls = ["https://example.com/webhook"]
        config.distribution.email_distribution = True
        
        config.interactive.custom_actions.extend([
            {
                "action_id": "generate_architecture_report",
                "label": "Generate Architecture Report",
                "type": "button"
            },
            {
                "action_id": "analyze_dependencies",
                "label": "Analyze Dependencies",
                "type": "button"
            }
        ])
        
        return ConfigurationTemplate(
            template_id="engineering_advanced",
            name="Engineering Team - Advanced",
            description="Advanced configuration with all features enabled for experienced engineering teams",
            category="engineering",
            template_config=config,
            setup_wizard_steps=base_template.setup_wizard_steps + [
                {
                    "step": 6,
                    "title": "Advanced Features",
                    "description": "Configure advanced features and integrations",
                    "fields": [
                        "distribution.webhook_urls",
                        "distribution.email_distribution",
                        "interactive.custom_actions"
                    ]
                }
            ],
            validation_rules=base_template.validation_rules
        )
    
    def _create_product_template(self) -> ConfigurationTemplate:
        """Create product team template."""
        config = TeamChangelogConfig(
            team_id="product",
            team_name="Product Team",
            enabled=True,
            schedule=ScheduleConfig(
                day="thursday",
                time="15:00",
                timezone="UTC"
            ),
            data_sources={
                "github": DataSourceConfig(enabled=False),  # Product teams typically don't need GitHub details
                "jira": DataSourceConfig(
                    enabled=True,
                    analysis_depth=AnalysisDepth.STANDARD
                ),
                "team_metrics": DataSourceConfig(
                    enabled=True,
                    analysis_depth=AnalysisDepth.BASIC
                )
            },
            content=ContentConfig(
                template_style=TemplateStyle.PROFESSIONAL,
                audience_type=AudienceType.BUSINESS,
                include_metrics=False,
                include_contributor_recognition=False,
                include_risk_analysis=True,
                include_performance_analysis=False,
                max_tickets_displayed=15,
                focus_areas=["deliverables", "milestones", "user_impact"]
            ),
            distribution=DistributionConfig(
                primary_channel="#product-updates",
                secondary_channels=["#stakeholders"],
                export_formats=["slack", "email"]
            ),
            interactive=InteractiveConfig(
                enable_feedback_buttons=True,
                enable_drill_down=False,  # Simplified for business audience
                enable_export_options=True
            ),
            notifications=NotificationConfig(
                notify_on_generation=True,
                notify_on_failure=True,
                weekend_notifications=False
            )
        )
        
        return ConfigurationTemplate(
            template_id="product_default",
            name="Product Team - Default",
            description="Business-focused configuration for product teams with stakeholder communication",
            category="product",
            template_config=config
        )
    
    def _create_product_stakeholder_template(self) -> ConfigurationTemplate:
        """Create product team template optimized for stakeholder communication."""
        base_template = self._create_product_template()
        config = base_template.template_config
        
        # Optimize for stakeholder communication
        config.content.template_style = TemplateStyle.EXECUTIVE
        config.content.audience_type = AudienceType.BUSINESS
        config.content.focus_areas = ["business_impact", "user_value", "roadmap_progress"]
        
        config.distribution.secondary_channels.extend(["#executives", "#board-updates"])
        config.distribution.channel_specific_formatting = {
            "#executives": {
                "template_style": "executive",
                "high_level_summary": True,
                "hide_technical_details": True
            },
            "#stakeholders": {
                "template_style": "professional",
                "include_business_metrics": True
            }
        }
        
        return ConfigurationTemplate(
            template_id="product_stakeholder",
            name="Product Team - Stakeholder Focus",
            description="Executive-level configuration optimized for stakeholder and leadership communication",
            category="product",
            template_config=config
        )
    
    def _create_qa_template(self) -> ConfigurationTemplate:
        """Create QA team template."""
        config = TeamChangelogConfig(
            team_id="qa",
            team_name="QA Team",
            enabled=True,
            schedule=ScheduleConfig(
                day="friday",
                time="14:00",
                timezone="UTC"
            ),
            data_sources={
                "github": DataSourceConfig(
                    enabled=True,
                    analysis_depth=AnalysisDepth.STANDARD
                ),
                "jira": DataSourceConfig(
                    enabled=True,
                    analysis_depth=AnalysisDepth.COMPREHENSIVE
                ),
                "team_metrics": DataSourceConfig(enabled=True)
            },
            content=ContentConfig(
                template_style=TemplateStyle.PROFESSIONAL,
                audience_type=AudienceType.TECHNICAL,
                include_metrics=True,
                include_contributor_recognition=True,
                include_risk_analysis=True,
                max_commits_displayed=15,
                max_tickets_displayed=25,
                focus_areas=["quality", "testing", "bug_analysis", "coverage"]
            ),
            distribution=DistributionConfig(
                primary_channel="#qa-updates",
                secondary_channels=["#engineering-updates"],
                export_formats=["slack", "markdown"]
            ),
            interactive=InteractiveConfig(
                enable_feedback_buttons=True,
                enable_drill_down=True,
                custom_actions=[
                    {
                        "action_id": "view_test_coverage",
                        "label": "View Test Coverage",
                        "type": "button"
                    },
                    {
                        "action_id": "bug_analysis_report",
                        "label": "Bug Analysis Report",
                        "type": "button"
                    }
                ]
            ),
            notifications=NotificationConfig(
                notify_on_generation=True,
                notify_on_failure=True,
                escalation_channels=["#qa-alerts"]
            )
        )
        
        return ConfigurationTemplate(
            template_id="qa_default",
            name="QA Team - Default",
            description="Quality-focused configuration for QA teams with testing and bug analysis emphasis",
            category="qa",
            template_config=config
        )
    
    def _create_qa_comprehensive_template(self) -> ConfigurationTemplate:
        """Create comprehensive QA template with advanced quality metrics."""
        base_template = self._create_qa_template()
        config = base_template.template_config
        
        # Enhanced for comprehensive quality analysis
        config.content.focus_areas.extend(["performance_testing", "security_testing", "automation"])
        config.content.max_tickets_displayed = 40
        
        config.interactive.custom_actions.extend([
            {
                "action_id": "performance_metrics",
                "label": "Performance Metrics",
                "type": "button"
            },
            {
                "action_id": "security_scan_results",
                "label": "Security Scan Results",
                "type": "button"
            }
        ])
        
        return ConfigurationTemplate(
            template_id="qa_comprehensive",
            name="QA Team - Comprehensive",
            description="Advanced QA configuration with comprehensive quality metrics and analysis",
            category="qa",
            template_config=config
        )
    
    def _create_design_template(self) -> ConfigurationTemplate:
        """Create design team template."""
        config = TeamChangelogConfig(
            team_id="design",
            team_name="Design Team",
            enabled=True,
            schedule=ScheduleConfig(
                day="wednesday",
                time="16:00",
                timezone="UTC"
            ),
            data_sources={
                "github": DataSourceConfig(enabled=False),
                "jira": DataSourceConfig(
                    enabled=True,
                    analysis_depth=AnalysisDepth.BASIC
                ),
                "team_metrics": DataSourceConfig(enabled=True)
            },
            content=ContentConfig(
                template_style=TemplateStyle.CASUAL,
                audience_type=AudienceType.MIXED,
                include_metrics=False,
                include_contributor_recognition=True,
                include_risk_analysis=False,
                max_tickets_displayed=10,
                focus_areas=["user_experience", "design_system", "prototypes"]
            ),
            distribution=DistributionConfig(
                primary_channel="#design-updates",
                secondary_channels=["#product-updates"],
                export_formats=["slack"]
            ),
            interactive=InteractiveConfig(
                enable_feedback_buttons=True,
                enable_drill_down=False
            ),
            notifications=NotificationConfig(
                notify_on_generation=True,
                notify_on_failure=True
            )
        )
        
        return ConfigurationTemplate(
            template_id="design_default",
            name="Design Team - Default",
            description="Creative-focused configuration for design teams with UX and design system emphasis",
            category="design",
            template_config=config
        )
    
    def _create_devops_template(self) -> ConfigurationTemplate:
        """Create DevOps team template."""
        config = TeamChangelogConfig(
            team_id="devops",
            team_name="DevOps Team",
            enabled=True,
            schedule=ScheduleConfig(
                day="friday",
                time="17:00",
                timezone="UTC"
            ),
            data_sources={
                "github": DataSourceConfig(
                    enabled=True,
                    analysis_depth=AnalysisDepth.COMPREHENSIVE
                ),
                "jira": DataSourceConfig(
                    enabled=True,
                    analysis_depth=AnalysisDepth.STANDARD
                ),
                "team_metrics": DataSourceConfig(enabled=True)
            },
            content=ContentConfig(
                template_style=TemplateStyle.TECHNICAL,
                audience_type=AudienceType.TECHNICAL,
                include_metrics=True,
                include_contributor_recognition=True,
                include_risk_analysis=True,
                include_performance_analysis=True,
                max_commits_displayed=20,
                max_tickets_displayed=15,
                focus_areas=["infrastructure", "deployment", "monitoring", "security"]
            ),
            distribution=DistributionConfig(
                primary_channel="#devops-updates",
                secondary_channels=["#engineering-updates", "#ops-alerts"],
                export_formats=["slack", "markdown", "email"]
            ),
            interactive=InteractiveConfig(
                enable_feedback_buttons=True,
                enable_drill_down=True,
                custom_actions=[
                    {
                        "action_id": "deployment_status",
                        "label": "Deployment Status",
                        "type": "button"
                    },
                    {
                        "action_id": "infrastructure_health",
                        "label": "Infrastructure Health",
                        "type": "button"
                    }
                ]
            ),
            notifications=NotificationConfig(
                notify_on_generation=True,
                notify_on_failure=True,
                escalation_channels=["#ops-alerts", "#engineering-alerts"]
            )
        )
        
        return ConfigurationTemplate(
            template_id="devops_default",
            name="DevOps Team - Default",
            description="Infrastructure-focused configuration for DevOps teams with deployment and monitoring emphasis",
            category="devops",
            template_config=config
        )
    
    def _create_management_template(self) -> ConfigurationTemplate:
        """Create management/executive template."""
        config = TeamChangelogConfig(
            team_id="management",
            team_name="Management Team",
            enabled=True,
            schedule=ScheduleConfig(
                day="monday",
                time="09:00",
                timezone="UTC"
            ),
            data_sources={
                "github": DataSourceConfig(enabled=False),
                "jira": DataSourceConfig(
                    enabled=True,
                    analysis_depth=AnalysisDepth.BASIC
                ),
                "team_metrics": DataSourceConfig(
                    enabled=True,
                    analysis_depth=AnalysisDepth.STANDARD
                )
            },
            content=ContentConfig(
                template_style=TemplateStyle.EXECUTIVE,
                audience_type=AudienceType.BUSINESS,
                include_metrics=True,
                include_contributor_recognition=False,
                include_risk_analysis=True,
                include_performance_analysis=False,
                max_tickets_displayed=10,
                focus_areas=["business_impact", "team_productivity", "roadmap_progress"]
            ),
            distribution=DistributionConfig(
                primary_channel="#management-updates",
                secondary_channels=["#executives"],
                export_formats=["slack", "email", "pdf"]
            ),
            interactive=InteractiveConfig(
                enable_feedback_buttons=False,
                enable_drill_down=False,
                enable_export_options=True
            ),
            notifications=NotificationConfig(
                notify_on_generation=True,
                notify_on_failure=True,
                quiet_hours_enabled=False  # Management may want updates anytime
            )
        )
        
        return ConfigurationTemplate(
            template_id="management_executive",
            name="Management - Executive Summary",
            description="Executive-level configuration focused on business impact and high-level metrics",
            category="management",
            template_config=config
        )
    
    def _create_minimal_template(self) -> ConfigurationTemplate:
        """Create minimal template for quick start."""
        config = TeamChangelogConfig(
            team_id="quickstart",
            team_name="Quick Start Team",
            enabled=True,
            schedule=ScheduleConfig(
                day="friday",
                time="17:00",
                timezone="UTC"
            ),
            data_sources={
                "github": DataSourceConfig(enabled=True),
                "jira": DataSourceConfig(enabled=True),
                "team_metrics": DataSourceConfig(enabled=False)
            },
            content=ContentConfig(
                template_style=TemplateStyle.PROFESSIONAL,
                audience_type=AudienceType.MIXED,
                include_metrics=False,
                include_contributor_recognition=False,
                include_risk_analysis=False,
                max_commits_displayed=10,
                max_tickets_displayed=10
            ),
            distribution=DistributionConfig(
                primary_channel="#updates",
                export_formats=["slack"]
            ),
            interactive=InteractiveConfig(
                enable_feedback_buttons=False,
                enable_drill_down=False
            ),
            notifications=NotificationConfig(
                notify_on_generation=True,
                notify_on_failure=True
            )
        )
        
        return ConfigurationTemplate(
            template_id="minimal_start",
            name="Minimal Quick Start",
            description="Minimal configuration to get started quickly with basic changelog features",
            category="custom",
            template_config=config,
            setup_wizard_steps=[
                {
                    "step": 1,
                    "title": "Basic Setup",
                    "description": "Configure essential settings to get started",
                    "fields": ["team_id", "team_name", "distribution.primary_channel"]
                }
            ]
        )
    
    def _setup_wizard_steps(self):
        """Setup wizard steps for different complexity levels."""
        # Simple wizard (3 steps)
        self._wizard_steps["simple"] = [
            WizardStep(
                step_number=1,
                title="Team Information",
                description="Tell us about your team",
                fields=["team_id", "team_name"],
                help_text="Choose a unique team identifier and display name",
                examples={
                    "team_id": "engineering",
                    "team_name": "Engineering Team"
                }
            ),
            WizardStep(
                step_number=2,
                title="Schedule",
                description="When should changelogs be generated?",
                fields=["schedule.day", "schedule.time", "schedule.timezone"],
                help_text="Choose when your team would like to receive weekly changelogs",
                examples={
                    "schedule.day": "friday",
                    "schedule.time": "16:00",
                    "schedule.timezone": "America/New_York"
                }
            ),
            WizardStep(
                step_number=3,
                title="Distribution",
                description="Where should changelogs be sent?",
                fields=["distribution.primary_channel"],
                validation_rules=[
                    {
                        "field": "distribution.primary_channel",
                        "rule": "required",
                        "message": "Primary channel is required"
                    },
                    {
                        "field": "distribution.primary_channel",
                        "rule": "starts_with",
                        "value": "#",
                        "message": "Channel must start with #"
                    }
                ],
                help_text="Specify the main Slack channel for changelog distribution",
                examples={
                    "distribution.primary_channel": "#team-updates"
                }
            )
        ]
        
        # Standard wizard (5 steps)
        self._wizard_steps["standard"] = self._wizard_steps["simple"] + [
            WizardStep(
                step_number=4,
                title="Data Sources",
                description="What information should be included?",
                fields=[
                    "data_sources.github.enabled",
                    "data_sources.jira.enabled",
                    "data_sources.team_metrics.enabled"
                ],
                help_text="Choose which data sources to include in your changelogs"
            ),
            WizardStep(
                step_number=5,
                title="Content Style",
                description="How should changelogs be formatted?",
                fields=[
                    "content.template_style",
                    "content.audience_type",
                    "content.include_metrics"
                ],
                help_text="Configure the style and content of your changelogs"
            )
        ]
        
        # Advanced wizard (8 steps)
        self._wizard_steps["advanced"] = self._wizard_steps["standard"] + [
            WizardStep(
                step_number=6,
                title="Advanced Content",
                description="Configure advanced content options",
                fields=[
                    "content.include_contributor_recognition",
                    "content.include_risk_analysis",
                    "content.max_commits_displayed",
                    "content.focus_areas"
                ]
            ),
            WizardStep(
                step_number=7,
                title="Interactive Features",
                description="Configure interactive elements",
                fields=[
                    "interactive.enable_feedback_buttons",
                    "interactive.enable_drill_down",
                    "interactive.enable_export_options"
                ]
            ),
            WizardStep(
                step_number=8,
                title="Notifications",
                description="Configure notification preferences",
                fields=[
                    "notifications.notify_on_generation",
                    "notifications.notify_on_failure",
                    "notifications.escalation_channels",
                    "notifications.quiet_hours_enabled"
                ]
            )
        ]
    
    def get_template(self, template_id: str) -> Optional[ConfigurationTemplate]:
        """Get configuration template by ID."""
        return self._templates.get(template_id)
    
    def list_templates(self, category: Optional[str] = None) -> List[ConfigurationTemplate]:
        """List available templates, optionally filtered by category."""
        templates = list(self._templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        return templates
    
    def get_wizard_steps(self, complexity: str = "standard") -> List[WizardStep]:
        """Get wizard steps for specified complexity level."""
        return self._wizard_steps.get(complexity, self._wizard_steps["standard"])
    
    def recommend_template(self, team_characteristics: Dict[str, Any]) -> List[TemplateRecommendation]:
        """
        Recommend templates based on team characteristics.
        
        Args:
            team_characteristics: Dictionary with team info like:
                - team_type: engineering, product, qa, etc.
                - team_size: small, medium, large
                - technical_level: basic, intermediate, advanced
                - primary_tools: list of tools used
                - communication_style: formal, casual, technical
        
        Returns:
            List of template recommendations sorted by confidence score
        """
        recommendations = []
        
        team_type = team_characteristics.get("team_type", "").lower()
        technical_level = team_characteristics.get("technical_level", "intermediate").lower()
        team_size = team_characteristics.get("team_size", "medium").lower()
        primary_tools = team_characteristics.get("primary_tools", [])
        communication_style = team_characteristics.get("communication_style", "professional").lower()
        
        # Engineering team recommendations
        if team_type in ["engineering", "development", "dev"]:
            if technical_level == "advanced" or team_size == "large":
                recommendations.append(TemplateRecommendation(
                    template_id="engineering_advanced",
                    confidence_score=0.95,
                    reasoning="Advanced engineering team with comprehensive needs",
                    customizations={"content.max_commits_displayed": 40 if team_size == "large" else 25}
                ))
            else:
                recommendations.append(TemplateRecommendation(
                    template_id="engineering_default",
                    confidence_score=0.90,
                    reasoning="Standard engineering team configuration",
                    customizations={}
                ))
        
        # Product team recommendations
        elif team_type in ["product", "pm", "product_management"]:
            if "stakeholder" in team_characteristics.get("focus_areas", []) or communication_style == "executive":
                recommendations.append(TemplateRecommendation(
                    template_id="product_stakeholder",
                    confidence_score=0.92,
                    reasoning="Product team with stakeholder communication focus",
                    customizations={}
                ))
            else:
                recommendations.append(TemplateRecommendation(
                    template_id="product_default",
                    confidence_score=0.88,
                    reasoning="Standard product team configuration",
                    customizations={}
                ))
        
        # QA team recommendations
        elif team_type in ["qa", "quality", "testing"]:
            if technical_level == "advanced" or "automation" in primary_tools:
                recommendations.append(TemplateRecommendation(
                    template_id="qa_comprehensive",
                    confidence_score=0.93,
                    reasoning="Advanced QA team with comprehensive testing focus",
                    customizations={}
                ))
            else:
                recommendations.append(TemplateRecommendation(
                    template_id="qa_default",
                    confidence_score=0.87,
                    reasoning="Standard QA team configuration",
                    customizations={}
                ))
        
        # Design team recommendations
        elif team_type in ["design", "ux", "ui"]:
            recommendations.append(TemplateRecommendation(
                template_id="design_default",
                confidence_score=0.85,
                reasoning="Design team with creative focus",
                customizations={}
            ))
        
        # DevOps team recommendations
        elif team_type in ["devops", "ops", "infrastructure", "sre"]:
            recommendations.append(TemplateRecommendation(
                template_id="devops_default",
                confidence_score=0.90,
                reasoning="DevOps team with infrastructure focus",
                customizations={}
            ))
        
        # Management recommendations
        elif team_type in ["management", "executive", "leadership"]:
            recommendations.append(TemplateRecommendation(
                template_id="management_executive",
                confidence_score=0.88,
                reasoning="Management team with executive summary focus",
                customizations={}
            ))
        
        # Fallback recommendations
        if not recommendations:
            if technical_level == "basic" or team_size == "small":
                recommendations.append(TemplateRecommendation(
                    template_id="minimal_start",
                    confidence_score=0.70,
                    reasoning="Simple configuration for getting started quickly",
                    customizations={}
                ))
            else:
                recommendations.append(TemplateRecommendation(
                    template_id="engineering_default",
                    confidence_score=0.60,
                    reasoning="Default configuration as fallback",
                    customizations={}
                ))
        
        # Sort by confidence score
        recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return recommendations
    
    def validate_template_customizations(
        self, 
        template_id: str, 
        customizations: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate template customizations.
        
        Args:
            template_id: Template identifier
            customizations: Customizations to apply
            
        Returns:
            ValidationResult
        """
        template = self.get_template(template_id)
        if not template:
            return ValidationResult(
                valid=False,
                errors=[f"Template {template_id} not found"]
            )
        
        errors = []
        warnings = []
        suggestions = []
        
        # Validate customization fields exist in template
        for key, value in customizations.items():
            if not self._is_valid_customization_field(key, template):
                errors.append(f"Invalid customization field: {key}")
        
        # Apply template-specific validation rules
        for rule in template.validation_rules:
            rule_result = self._apply_validation_rule(rule, customizations)
            if not rule_result.valid:
                errors.extend(rule_result.errors)
                warnings.extend(rule_result.warnings)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _is_valid_customization_field(self, field_path: str, template: ConfigurationTemplate) -> bool:
        """Check if customization field is valid for template."""
        # This would implement field path validation
        # For now, return True as a placeholder
        return True
    
    def _apply_validation_rule(self, rule: Dict[str, Any], customizations: Dict[str, Any]) -> ValidationResult:
        """Apply a validation rule to customizations."""
        # This would implement rule validation logic
        # For now, return valid as a placeholder
        return ValidationResult(valid=True)


# Global templates instance
default_templates = ChangelogConfigurationTemplates()