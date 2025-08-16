"""
Configuration system for the enhanced notification logic.
Supports both environment variables and YAML config files with validation.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml
from datetime import time

from ..core.notification_integration import NotificationSystemConfig
from ..core.enhanced_notification_handler import WorkHoursConfig, FilterConfig
from ..core.smart_message_batcher import SpamPreventionConfig, TimingConfig, TimingMode, SpamPreventionStrategy
from ..core.notification_scheduler import SchedulerConfig
from ..core.message_formatter import TemplateConfig
from ..core.channel_router import NotificationType


@dataclass
class DatabaseConfig:
    """Database configuration."""
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_key: Optional[str] = None
    connection_timeout: int = 30
    max_retries: int = 3


@dataclass
class SlackConfig:
    """Slack API configuration."""
    bot_token: Optional[str] = None
    app_token: Optional[str] = None
    signing_secret: Optional[str] = None
    webhook_url: Optional[str] = None
    default_channel: str = "#general"
    rate_limit_per_minute: int = 50


@dataclass
class MonitoringConfig:
    """Monitoring and alerting configuration."""
    enabled: bool = True
    health_check_interval_seconds: int = 300
    metrics_retention_days: int = 90
    alert_on_errors: bool = True
    alert_error_threshold: int = 10
    alert_webhook_url: Optional[str] = None
    log_level: str = "INFO"


@dataclass
class TeamConfig:
    """Team-specific configuration."""
    team_id: str
    name: str
    channels: Dict[str, str] = field(default_factory=dict)  # notification_type -> channel
    work_hours: Optional[WorkHoursConfig] = None
    filters: Optional[FilterConfig] = None
    template_overrides: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class NotificationConfigManager:
    """Manager for notification system configuration."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager."""
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file
        self._config: Optional[NotificationSystemConfig] = None
        self._teams: Dict[str, TeamConfig] = {}
        
    def load_config(self, config_file: Optional[str] = None) -> NotificationSystemConfig:
        """Load configuration from file and environment variables."""
        
        config_file = config_file or self.config_file
        
        # Start with default configuration
        config = NotificationSystemConfig()
        
        # Load from YAML file if provided
        if config_file:
            file_config = self._load_yaml_config(config_file)
            if file_config:
                config = self._merge_config(config, file_config)
        
        # Override with environment variables
        config = self._apply_env_overrides(config)
        
        # Validate configuration
        self._validate_config(config)
        
        self._config = config
        return config
    
    def _load_yaml_config(self, config_file: str) -> Optional[Dict[str, Any]]:
        """Load configuration from YAML file."""
        
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                self.logger.warning(f"Configuration file not found: {config_file}")
                return None
            
            with open(config_path, 'r') as f:
                yaml_data = yaml.safe_load(f)
            
            self.logger.info(f"Loaded configuration from {config_file}")
            return yaml_data
            
        except Exception as e:
            self.logger.error(f"Error loading configuration file {config_file}: {e}")
            return None
    
    def _merge_config(self, base_config: NotificationSystemConfig, 
                     file_config: Dict[str, Any]) -> NotificationSystemConfig:
        """Merge file configuration with base configuration."""
        
        try:
            # Core system settings
            if "system" in file_config:
                system = file_config["system"]
                base_config.enabled = system.get("enabled", base_config.enabled)
                base_config.debug_mode = system.get("debug_mode", base_config.debug_mode)
                base_config.analytics_enabled = system.get("analytics_enabled", base_config.analytics_enabled)
                base_config.health_check_enabled = system.get("health_check_enabled", base_config.health_check_enabled)
                base_config.health_check_interval_seconds = system.get("health_check_interval_seconds", base_config.health_check_interval_seconds)
                base_config.metrics_retention_days = system.get("metrics_retention_days", base_config.metrics_retention_days)
            
            # Database configuration
            if "database" in file_config:
                db = file_config["database"]
                base_config.supabase_url = db.get("supabase_url", base_config.supabase_url)
                base_config.supabase_key = db.get("supabase_key", base_config.supabase_key)
            
            # Slack configuration
            if "slack" in file_config:
                slack = file_config["slack"]
                base_config.slack_bot_token = slack.get("bot_token", base_config.slack_bot_token)
                base_config.slack_app_token = slack.get("app_token", base_config.slack_app_token)
            
            # Work hours configuration
            if "work_hours" in file_config:
                wh = file_config["work_hours"]
                base_config.work_hours = WorkHoursConfig(
                    enabled=wh.get("enabled", True),
                    start_hour=wh.get("start_hour", 9),
                    end_hour=wh.get("end_hour", 17),
                    timezone=wh.get("timezone", "UTC"),
                    work_days=wh.get("work_days", [0, 1, 2, 3, 4]),
                    urgent_bypass=wh.get("urgent_bypass", True)
                )
            
            # Filtering configuration
            if "filtering" in file_config:
                filt = file_config["filtering"]
                base_config.filtering = FilterConfig(
                    enabled=filt.get("enabled", True),
                    min_priority_level=filt.get("min_priority_level", "low"),
                    blocked_authors=filt.get("blocked_authors", []),
                    blocked_repositories=filt.get("blocked_repositories", []),
                    blocked_projects=filt.get("blocked_projects", []),
                    allowed_notification_types=self._parse_notification_types(filt.get("allowed_notification_types")),
                    custom_filters=filt.get("custom_filters", {})
                )
            
            # Template configuration
            if "template" in file_config:
                tmpl = file_config["template"]
                base_config.template = TemplateConfig(
                    team_id=tmpl.get("team_id", "default"),
                    branding=tmpl.get("branding", {}),
                    emoji_set=tmpl.get("emoji_set", {}),
                    color_scheme=tmpl.get("color_scheme", {}),
                    interactive_elements=tmpl.get("interactive_elements", True),
                    accessibility_mode=tmpl.get("accessibility_mode", False),
                    threading_enabled=tmpl.get("threading_enabled", True)
                )
            
            # Scheduler configuration
            if "scheduler" in file_config:
                sched = file_config["scheduler"]
                base_config.scheduler = SchedulerConfig(
                    check_interval_seconds=sched.get("check_interval_seconds", 60),
                    batch_size=sched.get("batch_size", 50),
                    max_retries=sched.get("max_retries", 3),
                    retry_delay_seconds=sched.get("retry_delay_seconds", 300),
                    health_check_interval_seconds=sched.get("health_check_interval_seconds", 300),
                    cleanup_interval_hours=sched.get("cleanup_interval_hours", 24),
                    enable_metrics=sched.get("enable_metrics", True),
                    enable_health_checks=sched.get("enable_health_checks", True)
                )
            
            # Spam prevention configuration
            if "spam_prevention" in file_config:
                spam = file_config["spam_prevention"]
                base_config.spam_prevention = SpamPreventionConfig(
                    enabled=spam.get("enabled", True),
                    max_messages_per_minute=spam.get("max_messages_per_minute", 10),
                    max_messages_per_hour=spam.get("max_messages_per_hour", 100),
                    burst_threshold=spam.get("burst_threshold", 5),
                    burst_window_seconds=spam.get("burst_window_seconds", 30),
                    cooldown_after_burst_minutes=spam.get("cooldown_after_burst_minutes", 5),
                    duplicate_content_window_minutes=spam.get("duplicate_content_window_minutes", 15),
                    priority_rate_limits=spam.get("priority_rate_limits", {}),
                    quiet_hours_start=spam.get("quiet_hours_start", 22),
                    quiet_hours_end=spam.get("quiet_hours_end", 8),
                    quiet_hours_enabled=spam.get("quiet_hours_enabled", True),
                    strategies=self._parse_spam_strategies(spam.get("strategies", []))
                )
            
            # Timing configuration
            if "timing" in file_config:
                timing = file_config["timing"]
                base_config.timing = TimingConfig(
                    mode=TimingMode(timing.get("mode", "adaptive")),
                    base_interval_minutes=timing.get("base_interval_minutes", 5),
                    max_interval_minutes=timing.get("max_interval_minutes", 30),
                    min_interval_minutes=timing.get("min_interval_minutes", 1),
                    adaptive_factor=timing.get("adaptive_factor", 1.5),
                    burst_detection_enabled=timing.get("burst_detection_enabled", True),
                    user_activity_tracking=timing.get("user_activity_tracking", True),
                    priority_timing_overrides=timing.get("priority_timing_overrides", {})
                )
            
            # Load team configurations
            if "teams" in file_config:
                self._load_team_configs(file_config["teams"])
            
            return base_config
            
        except Exception as e:
            self.logger.error(f"Error merging configuration: {e}")
            return base_config
    
    def _apply_env_overrides(self, config: NotificationSystemConfig) -> NotificationSystemConfig:
        """Apply environment variable overrides."""
        
        # System settings
        config.enabled = self._get_env_bool("NOTIFICATION_ENABLED", config.enabled)
        config.debug_mode = self._get_env_bool("NOTIFICATION_DEBUG", config.debug_mode)
        config.analytics_enabled = self._get_env_bool("NOTIFICATION_ANALYTICS_ENABLED", config.analytics_enabled)
        
        # Database settings
        config.supabase_url = os.getenv("SUPABASE_URL", config.supabase_url)
        config.supabase_key = os.getenv("SUPABASE_ANON_KEY", config.supabase_key)
        
        # Slack settings
        config.slack_bot_token = os.getenv("SLACK_BOT_TOKEN", config.slack_bot_token)
        config.slack_app_token = os.getenv("SLACK_APP_TOKEN", config.slack_app_token)
        
        # Work hours settings
        if os.getenv("WORK_HOURS_START"):
            config.work_hours.start_hour = int(os.getenv("WORK_HOURS_START"))
        if os.getenv("WORK_HOURS_END"):
            config.work_hours.end_hour = int(os.getenv("WORK_HOURS_END"))
        if os.getenv("WORK_HOURS_TIMEZONE"):
            config.work_hours.timezone = os.getenv("WORK_HOURS_TIMEZONE")
        
        # Filtering settings
        if os.getenv("FILTER_MIN_PRIORITY"):
            config.filtering.min_priority_level = os.getenv("FILTER_MIN_PRIORITY")
        
        # Template settings
        if os.getenv("TEMPLATE_TEAM_ID"):
            config.template.team_id = os.getenv("TEMPLATE_TEAM_ID")
        
        return config
    
    def _parse_notification_types(self, types_list: Optional[List[str]]) -> Optional[List[NotificationType]]:
        """Parse notification types from string list."""
        
        if not types_list:
            return None
        
        parsed_types = []
        for type_str in types_list:
            try:
                parsed_types.append(NotificationType(type_str))
            except ValueError:
                self.logger.warning(f"Unknown notification type: {type_str}")
        
        return parsed_types if parsed_types else None
    
    def _parse_spam_strategies(self, strategies_list: List[str]) -> List[SpamPreventionStrategy]:
        """Parse spam prevention strategies from string list."""
        
        parsed_strategies = []
        for strategy_str in strategies_list:
            try:
                parsed_strategies.append(SpamPreventionStrategy(strategy_str))
            except ValueError:
                self.logger.warning(f"Unknown spam prevention strategy: {strategy_str}")
        
        return parsed_strategies if parsed_strategies else [SpamPreventionStrategy.RATE_LIMITING]
    
    def _load_team_configs(self, teams_config: Dict[str, Any]) -> None:
        """Load team-specific configurations."""
        
        for team_id, team_data in teams_config.items():
            try:
                team_config = TeamConfig(
                    team_id=team_id,
                    name=team_data.get("name", team_id),
                    channels=team_data.get("channels", {}),
                    enabled=team_data.get("enabled", True),
                    template_overrides=team_data.get("template_overrides", {})
                )
                
                # Load team-specific work hours if provided
                if "work_hours" in team_data:
                    wh = team_data["work_hours"]
                    team_config.work_hours = WorkHoursConfig(
                        enabled=wh.get("enabled", True),
                        start_hour=wh.get("start_hour", 9),
                        end_hour=wh.get("end_hour", 17),
                        timezone=wh.get("timezone", "UTC"),
                        work_days=wh.get("work_days", [0, 1, 2, 3, 4]),
                        urgent_bypass=wh.get("urgent_bypass", True)
                    )
                
                # Load team-specific filters if provided
                if "filters" in team_data:
                    filt = team_data["filters"]
                    team_config.filters = FilterConfig(
                        enabled=filt.get("enabled", True),
                        min_priority_level=filt.get("min_priority_level", "low"),
                        blocked_authors=filt.get("blocked_authors", []),
                        blocked_repositories=filt.get("blocked_repositories", []),
                        blocked_projects=filt.get("blocked_projects", []),
                        allowed_notification_types=self._parse_notification_types(filt.get("allowed_notification_types")),
                        custom_filters=filt.get("custom_filters", {})
                    )
                
                self._teams[team_id] = team_config
                
            except Exception as e:
                self.logger.error(f"Error loading team config for {team_id}: {e}")
    
    def _validate_config(self, config: NotificationSystemConfig) -> None:
        """Validate configuration values."""
        
        errors = []
        
        # Validate work hours
        if config.work_hours.start_hour < 0 or config.work_hours.start_hour > 23:
            errors.append("work_hours.start_hour must be between 0 and 23")
        
        if config.work_hours.end_hour < 0 or config.work_hours.end_hour > 23:
            errors.append("work_hours.end_hour must be between 0 and 23")
        
        if config.work_hours.start_hour >= config.work_hours.end_hour:
            errors.append("work_hours.start_hour must be less than end_hour")
        
        # Validate work days
        if not all(0 <= day <= 6 for day in config.work_hours.work_days):
            errors.append("work_hours.work_days must contain values between 0 and 6")
        
        # Validate priority level
        valid_priorities = ["low", "medium", "high", "critical"]
        if config.filtering.min_priority_level not in valid_priorities:
            errors.append(f"filtering.min_priority_level must be one of: {valid_priorities}")
        
        # Validate scheduler intervals
        if config.scheduler.check_interval_seconds < 1:
            errors.append("scheduler.check_interval_seconds must be at least 1")
        
        if config.scheduler.batch_size < 1:
            errors.append("scheduler.batch_size must be at least 1")
        
        # Validate spam prevention
        if config.spam_prevention.max_messages_per_minute < 1:
            errors.append("spam_prevention.max_messages_per_minute must be at least 1")
        
        if config.spam_prevention.max_messages_per_hour < config.spam_prevention.max_messages_per_minute:
            errors.append("spam_prevention.max_messages_per_hour must be >= max_messages_per_minute")
        
        # Validate timing
        if config.timing.base_interval_minutes < 1:
            errors.append("timing.base_interval_minutes must be at least 1")
        
        if config.timing.max_interval_minutes < config.timing.base_interval_minutes:
            errors.append("timing.max_interval_minutes must be >= base_interval_minutes")
        
        if errors:
            error_msg = "Configuration validation errors:\n" + "\n".join(f"  - {error}" for error in errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.logger.info("Configuration validation passed")
    
    def _get_env_bool(self, env_var: str, default: bool) -> bool:
        """Get boolean value from environment variable."""
        value = os.getenv(env_var)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")
    
    def get_team_config(self, team_id: str) -> Optional[TeamConfig]:
        """Get configuration for a specific team."""
        return self._teams.get(team_id)
    
    def get_all_teams(self) -> Dict[str, TeamConfig]:
        """Get all team configurations."""
        return self._teams.copy()
    
    def save_config(self, output_file: str) -> bool:
        """Save current configuration to YAML file."""
        
        if not self._config:
            self.logger.error("No configuration loaded to save")
            return False
        
        try:
            # Convert config to dictionary
            config_dict = {
                "system": {
                    "enabled": self._config.enabled,
                    "debug_mode": self._config.debug_mode,
                    "analytics_enabled": self._config.analytics_enabled,
                    "health_check_enabled": self._config.health_check_enabled,
                    "health_check_interval_seconds": self._config.health_check_interval_seconds,
                    "metrics_retention_days": self._config.metrics_retention_days
                },
                "database": {
                    "supabase_url": self._config.supabase_url,
                    "supabase_key": self._config.supabase_key
                },
                "slack": {
                    "bot_token": self._config.slack_bot_token,
                    "app_token": self._config.slack_app_token
                },
                "work_hours": asdict(self._config.work_hours),
                "filtering": asdict(self._config.filtering),
                "template": asdict(self._config.template),
                "scheduler": asdict(self._config.scheduler),
                "spam_prevention": asdict(self._config.spam_prevention),
                "timing": asdict(self._config.timing)
            }
            
            # Add team configurations
            if self._teams:
                config_dict["teams"] = {}
                for team_id, team_config in self._teams.items():
                    config_dict["teams"][team_id] = asdict(team_config)
            
            # Write to file
            with open(output_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def create_example_config(self, output_file: str) -> bool:
        """Create an example configuration file."""
        
        example_config = {
            "system": {
                "enabled": True,
                "debug_mode": False,
                "analytics_enabled": True,
                "health_check_enabled": True,
                "health_check_interval_seconds": 300,
                "metrics_retention_days": 90
            },
            "database": {
                "supabase_url": "${SUPABASE_URL}",
                "supabase_key": "${SUPABASE_ANON_KEY}"
            },
            "slack": {
                "bot_token": "${SLACK_BOT_TOKEN}",
                "app_token": "${SLACK_APP_TOKEN}"
            },
            "work_hours": {
                "enabled": True,
                "start_hour": 9,
                "end_hour": 17,
                "timezone": "UTC",
                "work_days": [0, 1, 2, 3, 4],
                "urgent_bypass": True
            },
            "filtering": {
                "enabled": True,
                "min_priority_level": "low",
                "blocked_authors": ["bot-user", "automated-system"],
                "blocked_repositories": ["test-repo", "sandbox"],
                "blocked_projects": ["TEST", "SANDBOX"],
                "allowed_notification_types": None,
                "custom_filters": {
                    "spam_filter": {
                        "blocked_keywords": ["spam", "test", "ignore"]
                    }
                }
            },
            "template": {
                "team_id": "default",
                "branding": {
                    "primary_color": "#1f77b4",
                    "logo_emoji": ":gear:",
                    "team_name": "DevSync Team"
                },
                "emoji_set": {
                    "success": ":white_check_mark:",
                    "warning": ":warning:",
                    "error": ":x:",
                    "info": ":information_source:"
                },
                "color_scheme": {
                    "success": "#28a745",
                    "warning": "#ffc107",
                    "danger": "#dc3545",
                    "info": "#17a2b8"
                },
                "interactive_elements": True,
                "accessibility_mode": False,
                "threading_enabled": True
            },
            "scheduler": {
                "check_interval_seconds": 60,
                "batch_size": 50,
                "max_retries": 3,
                "retry_delay_seconds": 300,
                "health_check_interval_seconds": 300,
                "cleanup_interval_hours": 24,
                "enable_metrics": True,
                "enable_health_checks": True
            },
            "spam_prevention": {
                "enabled": True,
                "max_messages_per_minute": 10,
                "max_messages_per_hour": 100,
                "burst_threshold": 5,
                "burst_window_seconds": 30,
                "cooldown_after_burst_minutes": 5,
                "duplicate_content_window_minutes": 15,
                "priority_rate_limits": {
                    "critical": 20,
                    "high": 15,
                    "medium": 10,
                    "low": 5,
                    "lowest": 2
                },
                "quiet_hours_start": 22,
                "quiet_hours_end": 8,
                "quiet_hours_enabled": True,
                "strategies": ["rate_limiting", "adaptive_timing", "content_deduplication"]
            },
            "timing": {
                "mode": "adaptive",
                "base_interval_minutes": 5,
                "max_interval_minutes": 30,
                "min_interval_minutes": 1,
                "adaptive_factor": 1.5,
                "burst_detection_enabled": True,
                "user_activity_tracking": True,
                "priority_timing_overrides": {
                    "critical": 0,
                    "high": 1,
                    "medium": 5,
                    "low": 15,
                    "lowest": 30
                }
            },
            "teams": {
                "frontend_team": {
                    "name": "Frontend Team",
                    "enabled": True,
                    "channels": {
                        "pr_new": "#frontend-prs",
                        "pr_ready": "#frontend-reviews",
                        "jira_status": "#frontend-tickets",
                        "alert_build": "#frontend-alerts"
                    },
                    "work_hours": {
                        "enabled": True,
                        "start_hour": 10,
                        "end_hour": 18,
                        "timezone": "America/New_York",
                        "work_days": [0, 1, 2, 3, 4],
                        "urgent_bypass": True
                    },
                    "filters": {
                        "enabled": True,
                        "min_priority_level": "medium",
                        "blocked_repositories": ["legacy-frontend"],
                        "custom_filters": {}
                    },
                    "template_overrides": {
                        "branding": {
                            "primary_color": "#61dafb",
                            "logo_emoji": ":atom_symbol:",
                            "team_name": "Frontend Team"
                        }
                    }
                },
                "backend_team": {
                    "name": "Backend Team",
                    "enabled": True,
                    "channels": {
                        "pr_new": "#backend-prs",
                        "pr_ready": "#backend-reviews",
                        "jira_status": "#backend-tickets",
                        "alert_build": "#backend-alerts",
                        "alert_deployment": "#backend-deployments"
                    },
                    "work_hours": {
                        "enabled": True,
                        "start_hour": 9,
                        "end_hour": 17,
                        "timezone": "UTC",
                        "work_days": [0, 1, 2, 3, 4],
                        "urgent_bypass": True
                    },
                    "template_overrides": {
                        "branding": {
                            "primary_color": "#339933",
                            "logo_emoji": ":gear:",
                            "team_name": "Backend Team"
                        }
                    }
                }
            }
        }
        
        try:
            with open(output_file, 'w') as f:
                yaml.dump(example_config, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Example configuration created at {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating example configuration: {e}")
            return False


# Global configuration manager
default_config_manager = NotificationConfigManager()