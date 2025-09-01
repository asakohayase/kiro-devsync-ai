"""
Changelog Agent Hook for automated weekly changelog generation.

This hook integrates with the existing agent hook framework to provide
automated changelog generation and distribution capabilities.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from devsync_ai.core.agent_hooks import (
    AgentHook, 
    HookConfiguration, 
    EnrichedEvent, 
    HookExecutionResult,
    HookStatus,
    EventCategory
)


logger = logging.getLogger(__name__)


@dataclass
class ChangelogGenerationConfig:
    """Configuration for changelog generation."""
    enabled: bool = True
    schedule_day: str = "friday"  # Day of week to generate
    schedule_time: str = "17:00"  # Time to generate (24h format)
    timezone: str = "UTC"
    include_github: bool = True
    include_jira: bool = True
    include_team_metrics: bool = True
    distribution_channels: List[str] = None
    template_style: str = "professional"
    audience_type: str = "technical"
    
    def __post_init__(self):
        if self.distribution_channels is None:
            self.distribution_channels = []


class ChangelogAgentHook(AgentHook):
    """
    Agent Hook for automated weekly changelog generation and distribution.
    
    This hook integrates with the existing agent hook framework to provide:
    - Scheduled weekly changelog generation
    - Multi-channel distribution
    - Interactive Slack elements
    - Feedback collection and analysis
    """
    
    def __init__(self, hook_id: str, configuration: HookConfiguration):
        """Initialize the changelog agent hook."""
        super().__init__(hook_id, configuration)
        self.changelog_config = self._parse_changelog_config(configuration.metadata)
        self._last_generation: Optional[datetime] = None
        
    def _parse_changelog_config(self, metadata: Dict[str, Any]) -> ChangelogGenerationConfig:
        """Parse changelog-specific configuration from metadata."""
        changelog_meta = metadata.get("changelog", {})
        
        return ChangelogGenerationConfig(
            enabled=changelog_meta.get("enabled", True),
            schedule_day=changelog_meta.get("schedule_day", "friday"),
            schedule_time=changelog_meta.get("schedule_time", "17:00"),
            timezone=changelog_meta.get("timezone", "UTC"),
            include_github=changelog_meta.get("include_github", True),
            include_jira=changelog_meta.get("include_jira", True),
            include_team_metrics=changelog_meta.get("include_team_metrics", True),
            distribution_channels=changelog_meta.get("distribution_channels", []),
            template_style=changelog_meta.get("template_style", "professional"),
            audience_type=changelog_meta.get("audience_type", "technical")
        )
    
    async def can_handle(self, event: EnrichedEvent) -> bool:
        """
        Determine if this hook should handle the given event.
        
        This hook handles:
        - Scheduled changelog generation events
        - Manual changelog trigger events
        - Changelog feedback events
        """
        if not self.enabled or not self.changelog_config.enabled:
            return False
        
        # Handle scheduled generation events
        if event.event_type == "changelog.scheduled_generation":
            return True
        
        # Handle manual trigger events
        if event.event_type == "changelog.manual_trigger":
            team_id = event.context_data.get("team_id")
            return team_id == self.configuration.team_id
        
        # Handle feedback collection events
        if event.event_type == "changelog.feedback_request":
            return True
        
        return False
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """Execute the changelog hook logic."""
        execution_result = HookExecutionResult(
            hook_id=self.hook_id,
            execution_id="",  # Will be auto-generated
            hook_type=self.hook_type,
            event_id=event.event_id,
            status=HookStatus.RUNNING
        )
        
        try:
            if event.event_type == "changelog.scheduled_generation":
                result = await self._handle_scheduled_generation(event)
            elif event.event_type == "changelog.manual_trigger":
                result = await self._handle_manual_trigger(event)
            elif event.event_type == "changelog.feedback_request":
                result = await self._handle_feedback_request(event)
            else:
                raise ValueError(f"Unsupported event type: {event.event_type}")
            
            execution_result.status = HookStatus.SUCCESS
            execution_result.notification_sent = result.get("notification_sent", False)
            execution_result.notification_result = result.get("notification_result")
            execution_result.metadata = result.get("metadata", {})
            
        except Exception as e:
            logger.error(f"Changelog hook execution failed: {e}", exc_info=True)
            execution_result.add_error(str(e))
        
        execution_result.mark_completed()
        return execution_result
    
    async def _handle_scheduled_generation(self, event: EnrichedEvent) -> Dict[str, Any]:
        """Handle scheduled changelog generation."""
        logger.info(f"Starting scheduled changelog generation for team {self.configuration.team_id}")
        
        try:
            # Import here to avoid circular imports
            from devsync_ai.core.intelligent_scheduler import IntelligentScheduler
            from devsync_ai.core.intelligent_data_aggregator import IntelligentDataAggregator
            from devsync_ai.formatters.intelligent_changelog_formatter import IntelligentChangelogFormatter
            from devsync_ai.core.intelligent_distributor import IntelligentDistributor
            
            # Calculate week range
            now = datetime.now()
            week_start = now - timedelta(days=now.weekday() + 7)  # Previous Monday
            week_end = week_start + timedelta(days=6)  # Previous Sunday
            
            # Aggregate data from all sources
            aggregator = IntelligentDataAggregator()
            aggregated_data = await aggregator.aggregate_weekly_data(
                team_id=self.configuration.team_id,
                week_start=week_start,
                week_end=week_end,
                include_github=self.changelog_config.include_github,
                include_jira=self.changelog_config.include_jira,
                include_team_metrics=self.changelog_config.include_team_metrics
            )
            
            # Format the changelog
            formatter = IntelligentChangelogFormatter()
            formatted_changelog = await formatter.format_changelog(
                data=aggregated_data,
                team_id=self.configuration.team_id,
                template_style=self.changelog_config.template_style,
                audience_type=self.changelog_config.audience_type
            )
            
            # Distribute the changelog
            distributor = IntelligentDistributor()
            distribution_config = {
                "channels": self.changelog_config.distribution_channels or self.configuration.notification_channels,
                "team_id": self.configuration.team_id,
                "interactive_elements": True,
                "feedback_collection": True
            }
            
            distribution_result = await distributor.distribute_changelog(
                formatted_changelog, distribution_config
            )
            
            # Update last generation time
            self._last_generation = now
            
            return {
                "notification_sent": distribution_result.get("successful_deliveries", 0) > 0,
                "notification_result": distribution_result,
                "metadata": {
                    "week_start": week_start.isoformat(),
                    "week_end": week_end.isoformat(),
                    "data_sources": {
                        "github": self.changelog_config.include_github,
                        "jira": self.changelog_config.include_jira,
                        "team_metrics": self.changelog_config.include_team_metrics
                    },
                    "distribution_channels": len(distribution_config["channels"]),
                    "generation_time": now.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Scheduled changelog generation failed: {e}")
            raise
    
    async def _handle_manual_trigger(self, event: EnrichedEvent) -> Dict[str, Any]:
        """Handle manual changelog generation trigger."""
        logger.info(f"Starting manual changelog generation for team {self.configuration.team_id}")
        
        # Extract parameters from event
        week_start = event.context_data.get("week_start")
        week_end = event.context_data.get("week_end")
        channels = event.context_data.get("channels", self.configuration.notification_channels)
        
        if week_start:
            week_start = datetime.fromisoformat(week_start)
        if week_end:
            week_end = datetime.fromisoformat(week_end)
        
        # Use same logic as scheduled generation but with custom parameters
        return await self._generate_changelog(
            week_start=week_start,
            week_end=week_end,
            channels=channels,
            triggered_by="manual"
        )
    
    async def _handle_feedback_request(self, event: EnrichedEvent) -> Dict[str, Any]:
        """Handle changelog feedback collection request."""
        logger.info(f"Collecting changelog feedback for team {self.configuration.team_id}")
        
        try:
            from devsync_ai.services.slack import SlackService
            
            slack_service = SlackService()
            message_ts = event.context_data.get("message_ts")
            channel_id = event.context_data.get("channel_id")
            
            if not message_ts or not channel_id:
                raise ValueError("Missing message_ts or channel_id for feedback collection")
            
            feedback_result = await slack_service.collect_changelog_feedback(
                message_ts=message_ts,
                channel_id=channel_id,
                time_window_hours=24
            )
            
            return {
                "notification_sent": False,
                "notification_result": None,
                "metadata": {
                    "feedback_collected": feedback_result.get("success", False),
                    "feedback_data": feedback_result
                }
            }
            
        except Exception as e:
            logger.error(f"Feedback collection failed: {e}")
            raise
    
    async def _generate_changelog(
        self, 
        week_start: Optional[datetime] = None,
        week_end: Optional[datetime] = None,
        channels: Optional[List[str]] = None,
        triggered_by: str = "scheduled"
    ) -> Dict[str, Any]:
        """Generate and distribute changelog with custom parameters."""
        try:
            # Import here to avoid circular imports
            from devsync_ai.core.intelligent_data_aggregator import IntelligentDataAggregator
            from devsync_ai.formatters.intelligent_changelog_formatter import IntelligentChangelogFormatter
            from devsync_ai.core.intelligent_distributor import IntelligentDistributor
            
            # Default to previous week if not specified
            if not week_start or not week_end:
                now = datetime.now()
                week_start = now - timedelta(days=now.weekday() + 7)
                week_end = week_start + timedelta(days=6)
            
            # Aggregate data
            aggregator = IntelligentDataAggregator()
            aggregated_data = await aggregator.aggregate_weekly_data(
                team_id=self.configuration.team_id,
                week_start=week_start,
                week_end=week_end,
                include_github=self.changelog_config.include_github,
                include_jira=self.changelog_config.include_jira,
                include_team_metrics=self.changelog_config.include_team_metrics
            )
            
            # Format changelog
            formatter = IntelligentChangelogFormatter()
            formatted_changelog = await formatter.format_changelog(
                data=aggregated_data,
                team_id=self.configuration.team_id,
                template_style=self.changelog_config.template_style,
                audience_type=self.changelog_config.audience_type
            )
            
            # Distribute changelog
            distributor = IntelligentDistributor()
            distribution_config = {
                "channels": channels or self.configuration.notification_channels,
                "team_id": self.configuration.team_id,
                "interactive_elements": True,
                "feedback_collection": True,
                "triggered_by": triggered_by
            }
            
            distribution_result = await distributor.distribute_changelog(
                formatted_changelog, distribution_config
            )
            
            return {
                "notification_sent": distribution_result.get("successful_deliveries", 0) > 0,
                "notification_result": distribution_result,
                "metadata": {
                    "week_start": week_start.isoformat(),
                    "week_end": week_end.isoformat(),
                    "triggered_by": triggered_by,
                    "distribution_channels": len(distribution_config["channels"])
                }
            }
            
        except Exception as e:
            logger.error(f"Changelog generation failed: {e}")
            raise
    
    async def validate_configuration(self) -> List[str]:
        """Validate the changelog hook configuration."""
        errors = await super().validate_configuration()
        
        # Validate changelog-specific configuration
        if not self.changelog_config.distribution_channels and not self.configuration.notification_channels:
            errors.append("No distribution channels configured")
        
        if self.changelog_config.schedule_day not in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            errors.append(f"Invalid schedule_day: {self.changelog_config.schedule_day}")
        
        # Validate schedule time format
        try:
            datetime.strptime(self.changelog_config.schedule_time, "%H:%M")
        except ValueError:
            errors.append(f"Invalid schedule_time format: {self.changelog_config.schedule_time}")
        
        if self.changelog_config.template_style not in ["professional", "casual", "technical", "executive"]:
            errors.append(f"Invalid template_style: {self.changelog_config.template_style}")
        
        if self.changelog_config.audience_type not in ["technical", "business", "mixed"]:
            errors.append(f"Invalid audience_type: {self.changelog_config.audience_type}")
        
        return errors
    
    def get_next_scheduled_run(self) -> Optional[datetime]:
        """Get the next scheduled changelog generation time."""
        if not self.changelog_config.enabled:
            return None
        
        try:
            from devsync_ai.core.intelligent_scheduler import IntelligentScheduler
            scheduler = IntelligentScheduler()
            
            return scheduler.get_next_scheduled_time(
                day_of_week=self.changelog_config.schedule_day,
                time_of_day=self.changelog_config.schedule_time,
                timezone=self.changelog_config.timezone
            )
        except Exception as e:
            logger.error(f"Failed to calculate next scheduled run: {e}")
            return None
    
    def get_hook_status(self) -> Dict[str, Any]:
        """Get detailed status information for this hook."""
        base_status = {
            "hook_id": self.hook_id,
            "hook_type": self.hook_type,
            "team_id": self.configuration.team_id,
            "enabled": self.enabled,
            "last_generation": self._last_generation.isoformat() if self._last_generation else None,
            "next_scheduled_run": None,
            "configuration": {
                "schedule_day": self.changelog_config.schedule_day,
                "schedule_time": self.changelog_config.schedule_time,
                "timezone": self.changelog_config.timezone,
                "distribution_channels": len(self.changelog_config.distribution_channels),
                "data_sources": {
                    "github": self.changelog_config.include_github,
                    "jira": self.changelog_config.include_jira,
                    "team_metrics": self.changelog_config.include_team_metrics
                }
            }
        }
        
        next_run = self.get_next_scheduled_run()
        if next_run:
            base_status["next_scheduled_run"] = next_run.isoformat()
        
        return base_status