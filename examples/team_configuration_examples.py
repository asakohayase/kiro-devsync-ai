"""
Team Configuration Examples
Demonstrates how to configure templates for different teams and use cases.
"""

import yaml
from typing import Dict, Any, List
from pathlib import Path

from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.core.template_factory import MessageTemplateFactory
from devsync_ai.templates.standup_template import StandupTemplate


class TeamConfigurationExamples:
    """Examples of team-specific template configurations."""
    
    def __init__(self):
        """Initialize with example configurations."""
        self.configurations = self._create_example_configurations()
    
    def _create_example_configurations(self) -> Dict[str, TemplateConfig]:
        """Create example configurations for different teams."""
        return {
            "engineering": TemplateConfig(
                team_id="engineering",
                branding={
                    "team_name": "⚙️ Engineering Team",
                    "logo_emoji": "⚙️",
                    "primary_color": "#2E86AB",
                    "accent_color": "#A23B72",
                    "footer_text": "Built with ❤️ by Engineering"
                },
                emoji_set={
                    "success": "✅",
                    "warning": "⚠️",
                    "error": "❌",
                    "info": "ℹ️",
                    "in_progress": "🔄",
                    "blocked": "🚫",
                    "review": "👀",
                    "approved": "✅",
                    "merged": "🎉"
                },
                interactive_elements=True,
                accessibility_mode=False,
                caching_enabled=True,
                cache_ttl=1800,  # 30 minutes
                threading_enabled=True,
                batching_enabled=True,
                custom_fields={
                    "show_commit_stats": True,
                    "show_pr_metrics": True,
                    "show_code_review_stats": True,
                    "highlight_blockers": True
                }
            ),
            
            "design": TemplateConfig(
                team_id="design",
                branding={
                    "team_name": "🎨 Design Team",
                    "logo_emoji": "🎨",
                    "primary_color": "#FF6B35",
                    "accent_color": "#004E89",
                    "footer_text": "Designing the future ✨"
                },
                emoji_set={
                    "success": "🎉",
                    "warning": "⚡",
                    "error": "🚨",
                    "info": "💡",
                    "in_progress": "🎯",
                    "blocked": "🛑",
                    "review": "🔍",
                    "approved": "🌟",
                    "merged": "🚀"
                },
                interactive_elements=True,
                accessibility_mode=False,
                caching_enabled=True,
                cache_ttl=3600,  # 1 hour
                custom_fields={
                    "show_design_reviews": True,
                    "show_prototype_links": True,
                    "show_user_feedback": True,
                    "highlight_design_system_updates": True
                }
            ),
            
            "qa": TemplateConfig(
                team_id="qa",
                branding={
                    "team_name": "🔍 QA Team",
                    "logo_emoji": "🔍",
                    "primary_color": "#F18F01",
                    "accent_color": "#C73E1D",
                    "footer_text": "Quality is our priority 🛡️"
                },
                emoji_set={
                    "success": "✅",
                    "warning": "⚠️",
                    "error": "❌",
                    "info": "📋",
                    "in_progress": "🧪",
                    "blocked": "🚫",
                    "review": "🔬",
                    "approved": "✅",
                    "merged": "📦"
                },
                interactive_elements=False,  # QA prefers simpler interface
                accessibility_mode=True,     # Better for screen readers
                caching_enabled=True,
                cache_ttl=900,  # 15 minutes
                custom_fields={
                    "show_test_coverage": True,
                    "show_bug_metrics": True,
                    "show_automation_status": True,
                    "highlight_regression_tests": True,
                    "show_performance_metrics": True
                }
            ),
            
            "product": TemplateConfig(
                team_id="product",
                branding={
                    "team_name": "📊 Product Team",
                    "logo_emoji": "📊",
                    "primary_color": "#7209B7",
                    "accent_color": "#F72585",
                    "footer_text": "Driving product excellence 🎯"
                },
                emoji_set={
                    "success": "🎯",
                    "warning": "📈",
                    "error": "📉",
                    "info": "📋",
                    "in_progress": "⏳",
                    "blocked": "🚧",
                    "review": "📝",
                    "approved": "✅",
                    "merged": "🚀"
                },
                interactive_elements=True,
                accessibility_mode=False,
                caching_enabled=True,
                cache_ttl=7200,  # 2 hours
                custom_fields={
                    "show_user_metrics": True,
                    "show_feature_adoption": True,
                    "show_ab_test_results": True,
                    "highlight_user_feedback": True,
                    "show_roadmap_updates": True
                }
            ),
            
            "devops": TemplateConfig(
                team_id="devops",
                branding={
                    "team_name": "🚀 DevOps Team",
                    "logo_emoji": "🚀",
                    "primary_color": "#0077B6",
                    "accent_color": "#00B4D8",
                    "footer_text": "Automating the world 🤖"
                },
                emoji_set={
                    "success": "🟢",
                    "warning": "🟡",
                    "error": "🔴",
                    "info": "🔵",
                    "in_progress": "🔄",
                    "blocked": "⛔",
                    "review": "👁️",
                    "approved": "✅",
                    "merged": "🎉"
                },
                interactive_elements=True,
                accessibility_mode=False,
                caching_enabled=True,
                cache_ttl=600,  # 10 minutes (faster updates for ops)
                threading_enabled=True,
                batching_enabled=True,
                custom_fields={
                    "show_deployment_metrics": True,
                    "show_infrastructure_status": True,
                    "show_monitoring_alerts": True,
                    "highlight_security_updates": True,
                    "show_performance_metrics": True,
                    "show_cost_optimization": True
                }
            ),
            
            "security": TemplateConfig(
                team_id="security",
                branding={
                    "team_name": "🛡️ Security Team",
                    "logo_emoji": "🛡️",
                    "primary_color": "#8B0000",
                    "accent_color": "#DC143C",
                    "footer_text": "Securing the digital frontier 🔒"
                },
                emoji_set={
                    "success": "🔒",
                    "warning": "⚠️",
                    "error": "🚨",
                    "info": "🛡️",
                    "in_progress": "🔍",
                    "blocked": "🚫",
                    "review": "🔬",
                    "approved": "✅",
                    "merged": "🔐"
                },
                interactive_elements=True,
                accessibility_mode=False,
                caching_enabled=False,  # Security updates need to be real-time
                custom_fields={
                    "show_vulnerability_scans": True,
                    "show_compliance_status": True,
                    "show_incident_response": True,
                    "highlight_critical_alerts": True,
                    "show_audit_logs": True,
                    "show_threat_intelligence": True
                }
            ),
            
            "mobile": TemplateConfig(
                team_id="mobile",
                branding={
                    "team_name": "📱 Mobile Team",
                    "logo_emoji": "📱",
                    "primary_color": "#6A4C93",
                    "accent_color": "#C06C84",
                    "footer_text": "Mobile-first development 📲"
                },
                emoji_set={
                    "success": "📱",
                    "warning": "⚡",
                    "error": "💥",
                    "info": "💡",
                    "in_progress": "🔄",
                    "blocked": "🚫",
                    "review": "👀",
                    "approved": "✅",
                    "merged": "🚀"
                },
                interactive_elements=True,
                accessibility_mode=False,
                caching_enabled=True,
                cache_ttl=1800,
                custom_fields={
                    "show_app_store_metrics": True,
                    "show_crash_reports": True,
                    "show_performance_metrics": True,
                    "highlight_platform_updates": True,
                    "show_user_ratings": True,
                    "show_device_compatibility": True
                }
            ),
            
            "data": TemplateConfig(
                team_id="data",
                branding={
                    "team_name": "📈 Data Team",
                    "logo_emoji": "📈",
                    "primary_color": "#2E8B57",
                    "accent_color": "#20B2AA",
                    "footer_text": "Data-driven decisions 📊"
                },
                emoji_set={
                    "success": "📊",
                    "warning": "📈",
                    "error": "📉",
                    "info": "💾",
                    "in_progress": "⚙️",
                    "blocked": "🚫",
                    "review": "🔍",
                    "approved": "✅",
                    "merged": "📈"
                },
                interactive_elements=True,
                accessibility_mode=False,
                caching_enabled=True,
                cache_ttl=3600,
                custom_fields={
                    "show_pipeline_status": True,
                    "show_data_quality_metrics": True,
                    "show_model_performance": True,
                    "highlight_anomalies": True,
                    "show_usage_analytics": True,
                    "show_cost_metrics": True
                }
            )
        }
    
    def demonstrate_team_configurations(self):
        """Demonstrate different team configurations."""
        print("=== TEAM CONFIGURATION EXAMPLES ===\n")
        
        # Sample data for testing
        test_data = {
            "date": "2025-08-14",
            "team": "Test Team",
            "team_members": [
                {
                    "name": "Team Member",
                    "status": "active",
                    "yesterday": ["Completed task A"],
                    "today": ["Working on task B"],
                    "blockers": []
                }
            ],
            "stats": {
                "prs_merged": 5,
                "prs_open": 3,
                "tickets_completed": 8,
                "tickets_in_progress": 12,
                "commits": 25
            }
        }
        
        for team_name, config in self.configurations.items():
            print(f"{team_name.upper()} TEAM CONFIGURATION:")
            print(f"  Team Name: {config.branding['team_name']}")
            print(f"  Primary Color: {config.branding['primary_color']}")
            print(f"  Interactive Elements: {config.interactive_elements}")
            print(f"  Accessibility Mode: {config.accessibility_mode}")
            print(f"  Caching: {config.caching_enabled}")
            
            if hasattr(config, 'custom_fields'):
                print(f"  Custom Features: {len(config.custom_fields)} enabled")
            
            # Test template creation
            try:
                template = StandupTemplate(config=config)
                message = template.format_message(test_data)
                print(f"  ✅ Template test: {len(message.blocks)} blocks generated")
            except Exception as e:
                print(f"  ❌ Template test failed: {e}")
            
            print()
    
    def demonstrate_environment_configurations(self):
        """Demonstrate environment-specific configurations."""
        print("=== ENVIRONMENT-SPECIFIC CONFIGURATIONS ===\n")
        
        environments = {
            "development": {
                "caching_enabled": False,
                "debug_mode": True,
                "interactive_elements": True,
                "cache_ttl": 0,
                "performance_logging": True
            },
            "staging": {
                "caching_enabled": True,
                "debug_mode": False,
                "interactive_elements": True,
                "cache_ttl": 300,  # 5 minutes
                "performance_logging": True
            },
            "production": {
                "caching_enabled": True,
                "debug_mode": False,
                "interactive_elements": True,
                "cache_ttl": 3600,  # 1 hour
                "performance_logging": False,
                "error_reporting": True
            }
        }
        
        base_config = self.configurations["engineering"]
        
        for env_name, env_settings in environments.items():
            print(f"{env_name.upper()} ENVIRONMENT:")
            
            # Create environment-specific config
            env_config = TemplateConfig(
                team_id=f"{base_config.team_id}_{env_name}",
                branding=base_config.branding,
                emoji_set=base_config.emoji_set,
                **env_settings
            )
            
            for setting, value in env_settings.items():
                print(f"  {setting}: {value}")
            
            print()
    
    def demonstrate_accessibility_configurations(self):
        """Demonstrate accessibility-focused configurations."""
        print("=== ACCESSIBILITY CONFIGURATIONS ===\n")
        
        accessibility_configs = {
            "high_contrast": TemplateConfig(
                team_id="accessible_high_contrast",
                branding={
                    "team_name": "High Contrast Team",
                    "primary_color": "#000000",
                    "accent_color": "#FFFFFF"
                },
                emoji_set={
                    "success": "[SUCCESS]",
                    "warning": "[WARNING]",
                    "error": "[ERROR]",
                    "info": "[INFO]"
                },
                accessibility_mode=True,
                interactive_elements=False
            ),
            
            "screen_reader": TemplateConfig(
                team_id="accessible_screen_reader",
                branding={
                    "team_name": "Screen Reader Optimized Team"
                },
                emoji_set={
                    "success": "SUCCESS:",
                    "warning": "WARNING:",
                    "error": "ERROR:",
                    "info": "INFO:"
                },
                accessibility_mode=True,
                interactive_elements=False,
                fallback_text_detailed=True
            ),
            
            "simple_interface": TemplateConfig(
                team_id="accessible_simple",
                branding={
                    "team_name": "Simple Interface Team"
                },
                emoji_set={
                    "success": "✓",
                    "warning": "!",
                    "error": "✗",
                    "info": "i"
                },
                accessibility_mode=True,
                interactive_elements=False,
                minimal_formatting=True
            )
        }
        
        test_data = {
            "date": "2025-08-14",
            "team": "Accessibility Test",
            "team_members": []
        }
        
        for config_name, config in accessibility_configs.items():
            print(f"{config_name.upper()} CONFIGURATION:")
            
            template = StandupTemplate(config=config)
            message = template.format_message(test_data)
            
            print(f"  Accessibility Mode: {config.accessibility_mode}")
            print(f"  Interactive Elements: {config.interactive_elements}")
            print(f"  Fallback Text: '{message.text}'")
            print()
    
    def save_configurations_to_yaml(self, output_dir: str = "config/teams"):
        """Save team configurations to YAML files."""
        print("=== SAVING CONFIGURATIONS TO YAML ===\n")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for team_name, config in self.configurations.items():
            # Convert config to dictionary
            config_dict = {
                "team_id": config.team_id,
                "branding": config.branding,
                "emoji_set": config.emoji_set,
                "interactive_elements": config.interactive_elements,
                "accessibility_mode": config.accessibility_mode,
                "caching_enabled": config.caching_enabled,
            }
            
            if hasattr(config, 'cache_ttl'):
                config_dict["cache_ttl"] = config.cache_ttl
            
            if hasattr(config, 'custom_fields'):
                config_dict["custom_fields"] = config.custom_fields
            
            # Save to YAML file
            yaml_file = output_path / f"{team_name}_config.yaml"
            
            with open(yaml_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            print(f"✅ Saved {team_name} configuration to {yaml_file}")
        
        print()
    
    def load_configuration_from_yaml(self, yaml_file: str) -> TemplateConfig:
        """Load configuration from YAML file."""
        print(f"=== LOADING CONFIGURATION FROM {yaml_file} ===\n")
        
        try:
            with open(yaml_file, 'r') as f:
                config_dict = yaml.safe_load(f)
            
            config = TemplateConfig(**config_dict)
            print(f"✅ Successfully loaded configuration for team: {config.team_id}")
            return config
            
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            return None
    
    def demonstrate_dynamic_configuration(self):
        """Demonstrate dynamic configuration based on context."""
        print("=== DYNAMIC CONFIGURATION ===\n")
        
        def get_config_for_context(team: str, environment: str, time_of_day: int) -> TemplateConfig:
            """Get configuration based on context."""
            base_config = self.configurations.get(team, self.configurations["engineering"])
            
            # Modify based on environment
            if environment == "production":
                base_config.caching_enabled = True
                base_config.cache_ttl = 3600
            elif environment == "development":
                base_config.caching_enabled = False
                base_config.debug_mode = True
            
            # Modify based on time (e.g., night mode)
            if time_of_day < 6 or time_of_day > 22:  # Night hours
                base_config.branding["primary_color"] = "#2C3E50"  # Darker colors
                base_config.branding["accent_color"] = "#34495E"
            
            return base_config
        
        # Test different contexts
        contexts = [
            ("engineering", "production", 14),  # Engineering team, production, 2 PM
            ("design", "staging", 22),          # Design team, staging, 10 PM
            ("qa", "development", 9),           # QA team, development, 9 AM
        ]
        
        for team, env, hour in contexts:
            config = get_config_for_context(team, env, hour)
            print(f"Context: {team} team, {env} environment, {hour}:00")
            print(f"  Team: {config.branding['team_name']}")
            print(f"  Caching: {config.caching_enabled}")
            print(f"  Primary Color: {config.branding['primary_color']}")
            print()


def main():
    """Run team configuration examples."""
    print("TEAM CONFIGURATION EXAMPLES")
    print("=" * 50)
    print()
    
    examples = TeamConfigurationExamples()
    
    try:
        examples.demonstrate_team_configurations()
        examples.demonstrate_environment_configurations()
        examples.demonstrate_accessibility_configurations()
        examples.demonstrate_dynamic_configuration()
        
        # Save configurations to files
        examples.save_configurations_to_yaml()
        
        print("=" * 50)
        print("✅ Team Configuration Examples completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Configuration examples failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()