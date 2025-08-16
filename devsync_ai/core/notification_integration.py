"""
Integration layer for the enhanced notification system.
Connects all components and provides a unified interface for the application.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import os

from .enhanced_notification_handler import (
    EnhancedNotificationHandler, NotificationContext, ProcessingResult,
    WorkHoursConfig, FilterConfig
)
from .notification_scheduler import NotificationScheduler, SchedulerConfig
from .channel_router import ChannelRouter, NotificationType, RoutingRule, ChannelConfig
from .notification_deduplicator import NotificationDeduplicator, DeduplicationRule
from .smart_message_batcher import SmartMessageBatcher, SpamPreventionConfig, TimingConfig
from .template_registry import initialize_template_system
from .message_formatter import TemplateConfig


@dataclass
class NotificationSystemConfig:
    """Complete configuration for the notification system."""
    
    # Core system settings
    enabled: bool = True
    debug_mode: bool = False
    
    # Database settings
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    
    # Work hours configuration
    work_hours: WorkHoursConfig = field(default_factory=WorkHoursConfig)
    
    # Filtering configuration
    filtering: FilterConfig = field(default_factory=FilterConfig)
    
    # Template configuration
    template: TemplateConfig = field(default_factory=lambda: TemplateConfig(team_id="default"))
    
    # Scheduler configuration
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    
    # Spam prevention configuration
    spam_prevention: SpamPreventionConfig = field(default_factory=SpamPreventionConfig)
    
    # Timing configuration
    timing: TimingConfig = field(default_factory=TimingConfig)
    
    # Slack configuration
    slack_bot_token: Optional[str] = None
    slack_app_token: Optional[str] = None
    
    # Health check settings
    health_check_enabled: bool = True
    health_check_interval_seconds: int = 300
    
    # Analytics settings
    analytics_enabled: bool = True
    metrics_retention_days: int = 90


class NotificationSystem:
    """Integrated notification system that orchestrates all components."""
    
    def __init__(self, config: Optional[NotificationSystemConfig] = None):
        """Initialize the complete notification system."""
        
        self.logger = logging.getLogger(__name__)
        self.config = config or NotificationSystemConfig()
        
        # Initialize database client
        self.supabase = self._initialize_supabase()
        
        # Initialize template system
        self.template_factory = initialize_template_system()
        
        # Initialize core components
        self.router = ChannelRouter()
        self.deduplicator = NotificationDeduplicator(self.supabase)
        self.batcher = SmartMessageBatcher(
            spam_config=self.config.spam_prevention,
            timing_config=self.config.timing,
            formatter_factory=self.template_factory
        )
        
        # Initialize main handler
        self.handler = EnhancedNotificationHandler(
            router=self.router,
            deduplicator=self.deduplicator,
            batcher=self.batcher,
            work_hours_config=self.config.work_hours,
            filter_config=self.config.filtering,
            template_config=self.config.template,
            supabase_client=self.supabase
        )
        
        # Initialize scheduler
        self.scheduler = NotificationScheduler(
            handler=self.handler,
            config=self.config.scheduler,
            supabase_client=self.supabase
        )
        
        # System state
        self._initialized = False
        self._running = False
        
        self.logger.info("NotificationSystem initialized")
    
    def _initialize_supabase(self):
        """Initialize Supabase client if credentials are available."""
        
        try:
            # Try to get credentials from config or environment
            url = self.config.supabase_url or os.getenv('SUPABASE_URL')
            key = self.config.supabase_key or os.getenv('SUPABASE_ANON_KEY')
            
            if url and key:
                try:
                    from supabase import create_client
                    client = create_client(url, key)
                    self.logger.info("Supabase client initialized successfully")
                    return client
                except ImportError:
                    self.logger.warning("Supabase library not available, running without database")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Supabase client: {e}")
            else:
                self.logger.info("Supabase credentials not provided, running without database")
            
        except Exception as e:
            self.logger.error(f"Error initializing Supabase: {e}")
        
        return None
    
    async def initialize(self) -> bool:
        """Initialize the notification system."""
        
        if self._initialized:
            self.logger.warning("System already initialized")
            return True
        
        try:
            self.logger.info("Initializing notification system...")
            
            # Apply configuration to components
            self._apply_configuration()
            
            # Set up component callbacks
            self._setup_callbacks()
            
            # Validate system health
            health_status = await self.get_health_status()
            if health_status["status"] == "unhealthy":
                self.logger.error(f"System health check failed: {health_status['issues']}")
                return False
            
            self._initialized = True
            self.logger.info("Notification system initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize notification system: {e}")
            return False
    
    async def start(self) -> bool:
        """Start the notification system."""
        
        if not self._initialized:
            if not await self.initialize():
                return False
        
        if self._running:
            self.logger.warning("System already running")
            return True
        
        try:
            self.logger.info("Starting notification system...")
            
            # Start scheduler
            if not await self.scheduler.start():
                self.logger.error("Failed to start scheduler")
                return False
            
            self._running = True
            self.logger.info("Notification system started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start notification system: {e}")
            return False
    
    async def stop(self, timeout: int = 30) -> bool:
        """Stop the notification system gracefully."""
        
        if not self._running:
            return True
        
        try:
            self.logger.info("Stopping notification system...")
            
            # Stop scheduler
            if not await self.scheduler.stop(timeout):
                self.logger.warning("Scheduler did not stop cleanly")
            
            # Flush any remaining batches
            await self.handler.flush_batches()
            
            self._running = False
            self.logger.info("Notification system stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping notification system: {e}")
            return False
    
    def _apply_configuration(self) -> None:
        """Apply configuration to all components."""
        
        # Update handler configuration
        self.handler.update_configuration(
            work_hours_config=self.config.work_hours,
            filter_config=self.config.filtering,
            template_config=self.config.template
        )
        
        # Update batcher configuration
        self.batcher.update_spam_config(self.config.spam_prevention)
        self.batcher.update_timing_config(self.config.timing)
        
        self.logger.info("Configuration applied to all components")
    
    def _setup_callbacks(self) -> None:
        """Set up callbacks between components."""
        
        async def on_notification_processed(result):
            """Callback for when notifications are processed."""
            if self.config.analytics_enabled and self.supabase:
                try:
                    # Record analytics
                    await self._record_analytics(result)
                except Exception as e:
                    self.logger.error(f"Error recording analytics: {e}")
        
        async def on_scheduler_error(error):
            """Callback for scheduler errors."""
            self.logger.error(f"Scheduler error: {error}")
            # Could implement alerting here
        
        async def on_health_check(health_status):
            """Callback for health check results."""
            if health_status["status"] != "healthy":
                self.logger.warning(f"Health check warning: {health_status}")
                # Could implement alerting here
        
        # Set scheduler callbacks
        self.scheduler.set_callbacks(
            on_notification_processed=on_notification_processed,
            on_error=on_scheduler_error,
            on_health_check=on_health_check
        )
    
    async def _record_analytics(self, result: Dict[str, Any]) -> None:
        """Record analytics data to database."""
        
        if not self.supabase:
            return
        
        try:
            for notification in result.get("notifications", []):
                self.supabase.table("notification_analytics").insert({
                    "notification_type": notification.get("notification_type", "unknown"),
                    "channel": notification.get("channel", "unknown"),
                    "team_id": notification.get("team_id", "unknown"),
                    "urgency": notification.get("urgency", "medium"),
                    "filtered": notification.get("filtered", False),
                    "batched": notification.get("batched", False),
                    "delayed": notification.get("delayed", False),
                    "duplicate_prevented": notification.get("duplicate_prevented", False),
                    "processing_time_ms": notification.get("processing_time_ms", 0),
                    "sent_at": datetime.now().isoformat(),
                    "metadata": notification.get("metadata", {})
                }).execute()
                
        except Exception as e:
            self.logger.error(f"Error recording analytics: {e}")
    
    # Public API methods
    
    async def send_notification(self, 
                              notification_type: Union[str, NotificationType],
                              event_type: str,
                              data: Dict[str, Any],
                              team_id: str,
                              author: Optional[str] = None,
                              channel_override: Optional[str] = None,
                              priority_override: Optional[str] = None) -> ProcessingResult:
        """Send a notification through the system."""
        
        if not self._running:
            raise RuntimeError("Notification system is not running")
        
        # Convert string to enum if needed
        if isinstance(notification_type, str):
            try:
                notification_type = NotificationType(notification_type)
            except ValueError:
                raise ValueError(f"Unknown notification type: {notification_type}")
        
        # Create notification context
        context = NotificationContext(
            notification_type=notification_type,
            event_type=event_type,
            data=data,
            team_id=team_id,
            author=author,
            channel_override=channel_override,
            priority_override=priority_override
        )
        
        # Process notification
        return await self.handler.process_notification(context)
    
    async def send_github_notification(self, 
                                     event_type: str,
                                     payload: Dict[str, Any],
                                     team_id: str) -> ProcessingResult:
        """Send GitHub webhook notification."""
        
        # Map GitHub event types to notification types
        github_event_mapping = {
            "pull_request.opened": NotificationType.PR_NEW,
            "pull_request.ready_for_review": NotificationType.PR_READY,
            "pull_request.approved": NotificationType.PR_APPROVED,
            "pull_request.merged": NotificationType.PR_MERGED,
            "pull_request.closed": NotificationType.PR_CLOSED,
            "pull_request.conflicts": NotificationType.PR_CONFLICTS,
        }
        
        notification_type = github_event_mapping.get(event_type)
        if not notification_type:
            raise ValueError(f"Unsupported GitHub event type: {event_type}")
        
        # Extract author from payload
        author = None
        if "pull_request" in payload:
            author = payload["pull_request"].get("user", {}).get("login")
        elif "sender" in payload:
            author = payload["sender"].get("login")
        
        return await self.send_notification(
            notification_type=notification_type,
            event_type=event_type,
            data=payload,
            team_id=team_id,
            author=author
        )
    
    async def send_jira_notification(self,
                                   event_type: str,
                                   payload: Dict[str, Any],
                                   team_id: str) -> ProcessingResult:
        """Send JIRA webhook notification."""
        
        # Map JIRA event types to notification types
        jira_event_mapping = {
            "jira:issue_updated": NotificationType.JIRA_STATUS,
            "jira:issue_created": NotificationType.JIRA_STATUS,
            "jira:issue_assigned": NotificationType.JIRA_ASSIGNMENT,
            "jira:issue_commented": NotificationType.JIRA_COMMENT,
            "jira:issue_priority_changed": NotificationType.JIRA_PRIORITY,
            "jira:issue_blocked": NotificationType.JIRA_BLOCKER,
            "jira:sprint_updated": NotificationType.JIRA_SPRINT,
        }
        
        notification_type = jira_event_mapping.get(event_type)
        if not notification_type:
            raise ValueError(f"Unsupported JIRA event type: {event_type}")
        
        # Extract author from payload
        author = None
        if "user" in payload:
            author = payload["user"].get("displayName") or payload["user"].get("name")
        
        return await self.send_notification(
            notification_type=notification_type,
            event_type=event_type,
            data=payload,
            team_id=team_id,
            author=author
        )
    
    async def send_standup_notification(self,
                                      standup_data: Dict[str, Any],
                                      team_id: str) -> ProcessingResult:
        """Send daily standup notification."""
        
        return await self.send_notification(
            notification_type=NotificationType.STANDUP_DAILY,
            event_type="standup.daily",
            data=standup_data,
            team_id=team_id
        )
    
    async def send_alert_notification(self,
                                    alert_type: str,
                                    alert_data: Dict[str, Any],
                                    team_id: str) -> ProcessingResult:
        """Send alert notification."""
        
        # Map alert types to notification types
        alert_type_mapping = {
            "build_failure": NotificationType.ALERT_BUILD,
            "deployment_issue": NotificationType.ALERT_DEPLOYMENT,
            "security_vulnerability": NotificationType.ALERT_SECURITY,
            "service_outage": NotificationType.ALERT_OUTAGE,
            "critical_bug": NotificationType.ALERT_BUG,
        }
        
        notification_type = alert_type_mapping.get(alert_type)
        if not notification_type:
            raise ValueError(f"Unsupported alert type: {alert_type}")
        
        return await self.send_notification(
            notification_type=notification_type,
            event_type=f"alert.{alert_type}",
            data=alert_data,
            team_id=team_id
        )
    
    # Configuration management
    
    def add_team_channels(self, team_id: str, channel_mappings: Dict[str, str]) -> None:
        """Add team-specific channel mappings."""
        self.router.add_team_channel_mapping(team_id, channel_mappings)
    
    def add_routing_rule(self, rule: RoutingRule) -> None:
        """Add custom routing rule."""
        self.router.add_routing_rule(rule)
    
    def add_channel_config(self, config: ChannelConfig) -> None:
        """Add channel configuration."""
        self.router.add_channel_config(config)
    
    def add_deduplication_rule(self, rule: DeduplicationRule) -> None:
        """Add deduplication rule."""
        self.deduplicator.add_deduplication_rule(rule)
    
    # Monitoring and analytics
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        
        return {
            "system": {
                "initialized": self._initialized,
                "running": self._running,
                "config": {
                    "enabled": self.config.enabled,
                    "debug_mode": self.config.debug_mode,
                    "analytics_enabled": self.config.analytics_enabled
                }
            },
            "handler": self.handler.get_processing_stats(),
            "scheduler": self.scheduler.get_metrics(),
            "router": self.router.get_routing_stats(),
            "deduplicator": self.deduplicator.get_deduplication_stats(),
            "batcher": {
                **self.batcher.get_batch_stats(),
                "spam_prevention": self.batcher.get_spam_prevention_stats()
            }
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get system health status."""
        
        issues = []
        
        # Check system state
        if not self._initialized:
            issues.append("System not initialized")
        
        if not self._running:
            issues.append("System not running")
        
        # Check database connectivity
        if not self.supabase:
            issues.append("No database connection")
        
        # Check scheduler health
        scheduler_health = self.scheduler.get_health_status()
        if scheduler_health["status"] != "healthy":
            issues.extend([f"Scheduler: {issue}" for issue in scheduler_health["issues"]])
        
        # Check handler health
        handler_health = self.handler.get_health_status()
        if handler_health["status"] != "healthy":
            issues.extend([f"Handler: {error['error']}" for error in handler_health["recent_errors"]])
        
        # Determine overall health
        if not issues:
            status = "healthy"
        elif len(issues) == 1 and "No database connection" in issues[0]:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "issues": issues,
            "components": {
                "system": "healthy" if self._initialized and self._running else "unhealthy",
                "database": "healthy" if self.supabase else "unavailable",
                "scheduler": scheduler_health["status"],
                "handler": handler_health["status"],
                "router": "healthy",
                "deduplicator": "healthy",
                "batcher": "healthy"
            },
            "last_check": datetime.now().isoformat()
        }
    
    async def get_analytics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get analytics summary for the specified time period."""
        
        if not self.supabase:
            return {"error": "No database connection available"}
        
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            end_time = datetime.now()
            
            # Get notification statistics
            response = self.supabase.rpc(
                "get_notification_stats_by_hour",
                {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()}
            ).execute()
            
            stats_by_hour = response.data if response.data else []
            
            # Get channel routing effectiveness
            response = self.supabase.rpc(
                "get_channel_routing_effectiveness",
                {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()}
            ).execute()
            
            routing_effectiveness = response.data if response.data else []
            
            return {
                "time_period_hours": hours,
                "stats_by_hour": stats_by_hour,
                "routing_effectiveness": routing_effectiveness,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting analytics summary: {e}")
            return {"error": str(e)}
    
    # Utility methods
    
    async def flush_all_batches(self) -> Dict[str, List]:
        """Flush all pending batches immediately."""
        return await self.handler.flush_batches()
    
    async def force_scheduler_run(self) -> Dict[str, Any]:
        """Force an immediate scheduler run."""
        return await self.scheduler.force_run()
    
    async def cleanup_old_data(self) -> Dict[str, Any]:
        """Clean up old data from all components."""
        
        results = {}
        
        # Clean up deduplicator
        try:
            dedup_cleaned = await self.deduplicator.cleanup_old_records()
            results["deduplicator"] = {"records_cleaned": dedup_cleaned}
        except Exception as e:
            results["deduplicator"] = {"error": str(e)}
        
        # Clean up router stats
        try:
            router_cleaned = self.router.cleanup_old_stats()
            results["router"] = {"records_cleaned": router_cleaned}
        except Exception as e:
            results["router"] = {"error": str(e)}
        
        # Clean up database if available
        if self.supabase:
            try:
                response = self.supabase.rpc("cleanup_old_notification_records").execute()
                results["database"] = {"tables_cleaned": response.data}
            except Exception as e:
                results["database"] = {"error": str(e)}
        
        return results


# Global notification system instance
default_notification_system = NotificationSystem()