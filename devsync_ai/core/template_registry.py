"""
Template registry for integrating all template components with the factory system.
This module wires all specialized templates into the factory registry and provides
configuration loading and template customization capabilities.
"""

import logging
from typing import Dict, Any, Optional, Type
from pathlib import Path

from .template_factory import MessageTemplateFactory, TemplateType, default_template_factory
from .message_formatter import TemplateConfig
from .exceptions import TemplateError

# Import all template classes
from ..templates.standup_template import StandupTemplate
from ..templates.pr_templates import (
    NewPRTemplate, ReadyForReviewTemplate, ApprovedPRTemplate,
    ConflictsTemplate, MergedPRTemplate, ClosedPRTemplate
)
from ..templates.jira_templates import (
    StatusChangeTemplate, PriorityChangeTemplate, AssignmentTemplate,
    CommentTemplate, BlockerTemplate, SprintChangeTemplate
)
from ..templates.alert_templates import (
    BuildFailureTemplate, DeploymentIssueTemplate, SecurityVulnerabilityTemplate,
    ServiceOutageTemplate, CriticalBugTemplate
)


logger = logging.getLogger(__name__)


class TemplateRegistry:
    """Registry for managing template integration with the factory system."""
    
    def __init__(self, factory: Optional[MessageTemplateFactory] = None):
        """Initialize template registry."""
        self.factory = factory or default_template_factory
        self.registered_templates: Dict[str, Type] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_all_templates(self) -> None:
        """Register all specialized templates with the factory system."""
        self.logger.info("Starting template registration process")
        
        try:
            # Register standup templates
            self._register_standup_templates()
            
            # Register PR templates
            self._register_pr_templates()
            
            # Register JIRA templates
            self._register_jira_templates()
            
            # Register alert templates
            self._register_alert_templates()
            
            self.logger.info(f"Successfully registered {len(self.registered_templates)} templates")
            
        except Exception as e:
            self.logger.error(f"Failed to register templates: {e}")
            raise TemplateError(f"Template registration failed: {e}") from e
    
    def _register_standup_templates(self) -> None:
        """Register standup-related templates."""
        self.factory.register_template(
            name="standup_daily",
            template_class=StandupTemplate,
            template_type=TemplateType.STANDUP,
            version="1.0.0",
            description="Daily standup summary with team health indicators"
        )
        self.registered_templates["standup_daily"] = StandupTemplate
        self.logger.debug("Registered standup templates")
    
    def _register_pr_templates(self) -> None:
        """Register PR-related templates."""
        pr_templates = [
            ("pr_new", NewPRTemplate, TemplateType.PR_NEW, "New PR creation notifications"),
            ("pr_ready", ReadyForReviewTemplate, TemplateType.PR_READY, "PR ready for review notifications"),
            ("pr_approved", ApprovedPRTemplate, TemplateType.PR_APPROVED, "PR approval notifications"),
            ("pr_conflicts", ConflictsTemplate, TemplateType.PR_CONFLICTS, "PR merge conflict notifications"),
            ("pr_merged", MergedPRTemplate, TemplateType.PR_MERGED, "PR merge success notifications"),
            ("pr_closed", ClosedPRTemplate, TemplateType.PR_CLOSED, "PR closure notifications")
        ]
        
        for name, template_class, template_type, description in pr_templates:
            self.factory.register_template(
                name=name,
                template_class=template_class,
                template_type=template_type,
                version="1.0.0",
                description=description
            )
            self.registered_templates[name] = template_class
        
        self.logger.debug(f"Registered {len(pr_templates)} PR templates")
    
    def _register_jira_templates(self) -> None:
        """Register JIRA-related templates."""
        jira_templates = [
            ("jira_status", StatusChangeTemplate, TemplateType.JIRA_STATUS, "JIRA status change notifications"),
            ("jira_priority", PriorityChangeTemplate, TemplateType.JIRA_PRIORITY, "JIRA priority change notifications"),
            ("jira_assignment", AssignmentTemplate, TemplateType.JIRA_ASSIGNMENT, "JIRA assignment notifications"),
            ("jira_comment", CommentTemplate, TemplateType.JIRA_COMMENT, "JIRA comment notifications"),
            ("jira_blocker", BlockerTemplate, TemplateType.JIRA_BLOCKER, "JIRA blocker notifications"),
            ("jira_sprint", SprintChangeTemplate, TemplateType.JIRA_SPRINT, "JIRA sprint change notifications")
        ]
        
        for name, template_class, template_type, description in jira_templates:
            self.factory.register_template(
                name=name,
                template_class=template_class,
                template_type=template_type,
                version="1.0.0",
                description=description
            )
            self.registered_templates[name] = template_class
        
        self.logger.debug(f"Registered {len(jira_templates)} JIRA templates")
    
    def _register_alert_templates(self) -> None:
        """Register alert-related templates."""
        alert_templates = [
            ("alert_build", BuildFailureTemplate, TemplateType.ALERT_BUILD, "Build failure alert notifications"),
            ("alert_deployment", DeploymentIssueTemplate, TemplateType.ALERT_DEPLOYMENT, "Deployment issue alert notifications"),
            ("alert_security", SecurityVulnerabilityTemplate, TemplateType.ALERT_SECURITY, "Security vulnerability alert notifications"),
            ("alert_outage", ServiceOutageTemplate, TemplateType.ALERT_OUTAGE, "Service outage alert notifications"),
            ("alert_bug", CriticalBugTemplate, TemplateType.ALERT_BUG, "Critical bug alert notifications")
        ]
        
        for name, template_class, template_type, description in alert_templates:
            self.factory.register_template(
                name=name,
                template_class=template_class,
                template_type=template_type,
                version="1.0.0",
                description=description
            )
            self.registered_templates[name] = template_class
        
        self.logger.debug(f"Registered {len(alert_templates)} alert templates")
    
    def get_registered_templates(self) -> Dict[str, Type]:
        """Get all registered template classes."""
        return self.registered_templates.copy()
    
    def validate_template_registration(self) -> Dict[str, Any]:
        """Validate that all templates are properly registered."""
        validation_results = {
            "total_registered": len(self.registered_templates),
            "factory_registered": len(self.factory.get_registered_templates()),
            "validation_errors": [],
            "template_types_covered": set(),
            "missing_template_types": []
        }
        
        # Check that factory has all our registered templates
        factory_templates = self.factory.get_registered_templates()
        for name, template_class in self.registered_templates.items():
            if name not in factory_templates:
                validation_results["validation_errors"].append(
                    f"Template {name} ({template_class.__name__}) not found in factory"
                )
            else:
                # Track template types covered
                factory_registration = factory_templates[name]
                validation_results["template_types_covered"].add(factory_registration.template_type)
        
        # Check for missing template types
        all_template_types = set(TemplateType)
        covered_types = validation_results["template_types_covered"]
        validation_results["missing_template_types"] = list(all_template_types - covered_types)
        
        # Log validation results
        if validation_results["validation_errors"]:
            self.logger.error(f"Template validation failed: {validation_results['validation_errors']}")
        else:
            self.logger.info(f"Template validation passed: {validation_results['total_registered']} templates registered")
        
        return validation_results


def initialize_template_system(config_path: Optional[str] = None) -> MessageTemplateFactory:
    """
    Initialize the complete template system with all components integrated.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Configured MessageTemplateFactory with all templates registered
    """
    logger.info("Initializing template system")
    
    try:
        # Load configuration if provided
        template_config = None
        if config_path:
            template_config = load_template_configuration(config_path)
        
        # Create factory with configuration
        factory = MessageTemplateFactory(config=template_config)
        
        # Create registry and register all templates
        registry = TemplateRegistry(factory)
        registry.register_all_templates()
        
        # Validate registration
        validation_results = registry.validate_template_registration()
        if validation_results["validation_errors"]:
            raise TemplateError(f"Template validation failed: {validation_results['validation_errors']}")
        
        logger.info("Template system initialization completed successfully")
        return factory
        
    except Exception as e:
        logger.error(f"Failed to initialize template system: {e}")
        raise TemplateError(f"Template system initialization failed: {e}") from e


def load_template_configuration(config_path: str) -> Optional[TemplateConfig]:
    """
    Load template configuration from file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        TemplateConfig object or None if loading fails
    """
    try:
        import yaml
        
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"Configuration file not found: {config_path}")
            return None
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Extract template configuration
        template_config_data = config_data.get('template_config', {})
        
        return TemplateConfig(
            team_id=template_config_data.get('team_id') or 'default',
            branding=template_config_data.get('branding') or {},
            emoji_set=template_config_data.get('emoji_set') or {},
            color_scheme=template_config_data.get('color_scheme') or {},
            interactive_elements=template_config_data.get('interactive_elements', True) if template_config_data.get('interactive_elements') is not None else True,
            accessibility_mode=template_config_data.get('accessibility_mode', False) if template_config_data.get('accessibility_mode') is not None else False
        )
        
    except Exception as e:
        logger.error(f"Failed to load configuration from {config_path}: {e}")
        return None


def create_end_to_end_message(event_type: str, event_data: Dict[str, Any], 
                             config: Optional[TemplateConfig] = None) -> Dict[str, Any]:
    """
    Create a complete end-to-end message using the integrated template system.
    
    Args:
        event_type: Type of event (e.g., 'pull_request.opened')
        event_data: Event data dictionary
        config: Optional template configuration
        
    Returns:
        Complete Slack message dictionary
    """
    try:
        # Get the default factory (should be initialized)
        factory = default_template_factory
        
        # Get appropriate template for event type
        template = factory.get_template_by_event_type(event_type, event_data, config)
        
        # Format the message
        message = template.format_message(event_data)
        
        logger.info(f"Successfully created end-to-end message for {event_type}")
        return message.to_dict()
        
    except Exception as e:
        logger.error(f"Failed to create end-to-end message for {event_type}: {e}")
        raise TemplateError(f"End-to-end message creation failed: {e}") from e


# Initialize the default template system on module import
try:
    default_registry = TemplateRegistry(default_template_factory)
    default_registry.register_all_templates()
    logger.info("Default template system initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize default template system: {e}")