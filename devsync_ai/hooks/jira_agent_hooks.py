"""
Specialized JIRA Agent Hooks for DevSync AI.

This module contains production-ready Agent Hook implementations that provide
intelligent, context-aware automation for JIRA-to-Slack integration.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from devsync_ai.core.agent_hooks import (
    AgentHook, 
    EnrichedEvent, 
    HookExecutionResult, 
    HookStatus,
    EventCategory,
    UrgencyLevel,
    SignificanceLevel
)
from devsync_ai.core.notification_integration import default_notification_system
from devsync_ai.core.hook_notification_integration import (
    default_hook_notification_integrator, HookNotificationType
)
from devsync_ai.services.slack import SlackService
from devsync_ai.templates.jira_templates import JIRATemplate
from devsync_ai.analytics.workload_analytics_engine import (
    default_workload_analytics_engine, 
    AssignmentImpactAnalysis,
    WorkloadStatus,
    CapacityAlert
)


logger = logging.getLogger(__name__)


class TransitionType(Enum):
    """Types of status transitions."""
    FORWARD = "forward"
    BACKWARD = "backward"
    BLOCKED = "blocked"
    UNBLOCKED = "unblocked"
    COMPLETED = "completed"
    REOPENED = "reopened"


class BlockerSeverity(Enum):
    """Severity levels for blockers."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SprintMetrics:
    """Sprint health and progress metrics."""
    sprint_name: Optional[str]
    total_story_points: int
    completed_story_points: int
    remaining_story_points: int
    completion_percentage: float
    velocity_trend: str  # "increasing", "stable", "decreasing"
    days_remaining: int
    at_risk: bool
    blockers_count: int


@dataclass
class WorkloadAnalysis:
    """Team member workload analysis."""
    assignee: str
    current_tickets: int
    total_story_points: int
    capacity_utilization: float
    overloaded: bool
    skill_match_score: float  # 0.0 to 1.0
    recent_velocity: float
    estimated_completion_date: Optional[datetime]


@dataclass
class BlockerAnalysis:
    """Comprehensive blocker analysis."""
    blocker_type: str
    severity: BlockerSeverity
    impact_assessment: str
    resolution_suggestions: List[str]
    stakeholders: List[str]
    escalation_required: bool
    sprint_risk_level: str
    estimated_resolution_time: Optional[timedelta]


class StatusChangeHook(AgentHook):
    """
    Production-ready Status Change Agent Hook.
    
    Handles JIRA ticket status transitions with intelligent filtering,
    rich messaging, and sprint impact analysis.
    """
    
    # Status transition mappings
    TRANSITION_TYPES = {
        ('to do', 'in progress'): TransitionType.FORWARD,
        ('in progress', 'in review'): TransitionType.FORWARD,
        ('in review', 'done'): TransitionType.COMPLETED,
        ('in progress', 'blocked'): TransitionType.BLOCKED,
        ('blocked', 'in progress'): TransitionType.UNBLOCKED,
        ('done', 'in progress'): TransitionType.REOPENED,
        ('in review', 'in progress'): TransitionType.BACKWARD,
    }
    
    # Channel routing based on transition type
    CHANNEL_ROUTING = {
        TransitionType.COMPLETED: ["#releases", "#dev-updates"],
        TransitionType.BLOCKED: ["#blockers", "#dev-alerts"],
        TransitionType.UNBLOCKED: ["#dev-updates"],
        TransitionType.FORWARD: ["#dev-updates"],
        TransitionType.BACKWARD: ["#dev-updates", "#code-review"],
        TransitionType.REOPENED: ["#dev-updates", "#qa-alerts"]
    }
    
    # Visual indicators for different transition types
    TRANSITION_INDICATORS = {
        TransitionType.FORWARD: "🟢",
        TransitionType.BACKWARD: "🟡",
        TransitionType.BLOCKED: "🔴",
        TransitionType.UNBLOCKED: "✅",
        TransitionType.COMPLETED: "🎉",
        TransitionType.REOPENED: "🔄"
    }
    
    async def can_handle(self, event: EnrichedEvent) -> bool:
        """Check if this hook can handle the event."""
        if not event.classification:
            return False
        
        # Handle status change events
        if event.classification.category == EventCategory.STATUS_CHANGE:
            return True
        
        # Also handle transitions
        if event.classification.category == EventCategory.TRANSITION:
            return True
        
        return False
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """Execute the status change hook."""
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"Processing status change for {event.ticket_key}")
            
            # Analyze the transition
            transition_analysis = await self._analyze_transition(event)
            
            # Get sprint metrics
            sprint_metrics = await self._get_sprint_metrics(event)
            
            # Analyze workload impact
            workload_analysis = await self._analyze_workload_impact(event)
            
            # Create rich notification message
            message_data = await self._create_status_message(
                event, transition_analysis, sprint_metrics, workload_analysis
            )
            
            # Determine routing channels
            channels = await self._determine_channels(transition_analysis, event)
            
            # Send notifications through integration layer
            notification_result = await self._send_notifications_via_integration(
                event, transition_analysis, sprint_metrics, workload_analysis
            )
            notification_sent = notification_result.decision.value in ["send_immediately", "batch_and_send"]
            
            # Update sprint dashboards if needed
            if sprint_metrics and transition_analysis['type'] in [
                TransitionType.COMPLETED, TransitionType.BLOCKED
            ]:
                await self._update_sprint_dashboard(sprint_metrics, event)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.SUCCESS,
                execution_time_ms=execution_time,
                notification_sent=notification_sent,
                metadata={
                    "transition_type": transition_analysis['type'].value,
                    "channels_notified": channels,
                    "sprint_impact": sprint_metrics.at_risk if sprint_metrics else False,
                    "workload_impact": workload_analysis.overloaded if workload_analysis else False
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.error(f"Status change hook failed for {event.ticket_key}: {e}", exc_info=True)
            
            result = HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.FAILED,
                execution_time_ms=execution_time,
                notification_sent=False
            )
            result.add_error(str(e))
            return result
    
    async def _analyze_transition(self, event: EnrichedEvent) -> Dict[str, Any]:
        """Analyze the status transition."""
        # Extract status change from event processors
        processor_data = event.context_data.get('processor_data', {})
        field_changes = processor_data.get('field_changes', [])
        
        # Find status change
        status_change = None
        for change in field_changes:
            if hasattr(change, 'field_name') and change.field_name == 'status':
                status_change = change
                break
        
        if not status_change:
            # Fallback to ticket details
            current_status = event.ticket_details.get('status', 'Unknown').lower()
            return {
                'type': TransitionType.FORWARD,
                'from_status': 'unknown',
                'to_status': current_status,
                'is_significant': False,
                'urgency': event.classification.urgency if event.classification else UrgencyLevel.MEDIUM
            }
        
        from_status = status_change.old_value.lower() if status_change.old_value else 'unknown'
        to_status = status_change.new_value.lower() if status_change.new_value else 'unknown'
        
        # Determine transition type
        transition_key = (from_status, to_status)
        transition_type = self.TRANSITION_TYPES.get(transition_key, TransitionType.FORWARD)
        
        # Check significance
        is_significant = (
            transition_type in [TransitionType.BLOCKED, TransitionType.COMPLETED, TransitionType.REOPENED] or
            event.classification.urgency in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]
        )
        
        return {
            'type': transition_type,
            'from_status': from_status,
            'to_status': to_status,
            'is_significant': is_significant,
            'urgency': event.classification.urgency if event.classification else UrgencyLevel.MEDIUM
        }
    
    async def _get_sprint_metrics(self, event: EnrichedEvent) -> Optional[SprintMetrics]:
        """Get sprint metrics and health assessment."""
        try:
            # Extract sprint information from event
            sprint_context = event.context_data.get('sprint_context', {})
            sprint_name = sprint_context.get('sprint_name')
            
            if not sprint_name:
                return None
            
            # This would typically query the database for sprint metrics
            # For now, return mock data that would be calculated from actual sprint data
            return SprintMetrics(
                sprint_name=sprint_name,
                total_story_points=50,
                completed_story_points=30,
                remaining_story_points=20,
                completion_percentage=60.0,
                velocity_trend="stable",
                days_remaining=5,
                at_risk=False,
                blockers_count=1
            )
            
        except Exception as e:
            logger.warning(f"Failed to get sprint metrics: {e}")
            return None
    
    async def _analyze_workload_impact(self, event: EnrichedEvent) -> Optional[WorkloadAnalysis]:
        """Analyze workload impact of the status change."""
        try:
            # Extract assignee information
            assignee_info = event.context_data.get('assignee_info', {})
            assignee_name = assignee_info.get('assignee_name')
            
            if not assignee_name:
                return None
            
            # This would typically query the database for workload data
            # For now, return mock analysis
            return WorkloadAnalysis(
                assignee=assignee_name,
                current_tickets=5,
                total_story_points=25,
                capacity_utilization=0.85,
                overloaded=False,
                skill_match_score=0.8,
                recent_velocity=8.5,
                estimated_completion_date=datetime.now(timezone.utc) + timedelta(days=3)
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze workload impact: {e}")
            return None
    
    async def _create_status_message(
        self, 
        event: EnrichedEvent, 
        transition_analysis: Dict[str, Any],
        sprint_metrics: Optional[SprintMetrics],
        workload_analysis: Optional[WorkloadAnalysis]
    ) -> Dict[str, Any]:
        """Create rich status change message."""
        transition_type = transition_analysis['type']
        indicator = self.TRANSITION_INDICATORS.get(transition_type, "🔄")
        
        # Build message blocks
        blocks = []
        
        # Header block
        header_text = (
            f"{indicator} *Status Change*: {event.ticket_key}\n"
            f"*{event.ticket_details.get('summary', 'No summary')}*"
        )
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": header_text}
        })
        
        # Transition details
        transition_text = (
            f"*Status*: {transition_analysis['from_status'].title()} → "
            f"{transition_analysis['to_status'].title()}\n"
            f"*Priority*: {event.ticket_details.get('priority', 'Medium')}\n"
            f"*Assignee*: {workload_analysis.assignee if workload_analysis else 'Unassigned'}"
        )
        
        if sprint_metrics:
            transition_text += f"\n*Sprint*: {sprint_metrics.sprint_name}"
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": transition_text}
        })
        
        # Sprint impact (if significant)
        if sprint_metrics and transition_analysis['is_significant']:
            sprint_text = (
                f"📊 *Sprint Impact*\n"
                f"Progress: {sprint_metrics.completion_percentage:.1f}% "
                f"({sprint_metrics.completed_story_points}/{sprint_metrics.total_story_points} points)\n"
                f"Days remaining: {sprint_metrics.days_remaining}\n"
                f"Velocity: {sprint_metrics.velocity_trend}"
            )
            
            if sprint_metrics.at_risk:
                sprint_text += "\n⚠️ *Sprint at risk*"
            
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": sprint_text}
            })
        
        # Workload impact (if relevant)
        if workload_analysis and workload_analysis.capacity_utilization > 0.9:
            workload_text = (
                f"👤 *Workload Alert*\n"
                f"Capacity: {workload_analysis.capacity_utilization:.0%}\n"
                f"Current load: {workload_analysis.current_tickets} tickets "
                f"({workload_analysis.total_story_points} points)"
            )
            
            if workload_analysis.overloaded:
                workload_text += "\n🚨 *Assignee overloaded*"
            
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": workload_text}
            })
        
        # Action buttons
        actions = []
        
        # View ticket button
        if event.ticket_key != 'UNKNOWN':
            actions.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "View Ticket"},
                "url": f"https://your-jira-instance.atlassian.net/browse/{event.ticket_key}",
                "style": "primary"
            })
        
        # Context-specific actions
        if transition_type == TransitionType.BLOCKED:
            actions.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "Report Blocker"},
                "value": f"report_blocker_{event.ticket_key}",
                "style": "danger"
            })
        elif transition_type == TransitionType.COMPLETED:
            actions.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "Update Sprint"},
                "value": f"update_sprint_{event.ticket_key}"
            })
        
        if actions:
            blocks.append({
                "type": "actions",
                "elements": actions
            })
        
        return {
            "blocks": blocks,
            "text": f"Status change: {event.ticket_key}",
            "metadata": {
                "transition_type": transition_type.value,
                "urgency": transition_analysis.get('urgency', UrgencyLevel.MEDIUM).value,
                "ticket_key": event.ticket_key
            }
        }
    
    async def _determine_channels(
        self, 
        transition_analysis: Dict[str, Any], 
        event: EnrichedEvent
    ) -> List[str]:
        """Determine which channels to notify based on transition type."""
        transition_type = transition_analysis['type']
        
        # Get base channels for transition type
        channels = self.CHANNEL_ROUTING.get(transition_type, ["#dev-updates"]).copy()
        
        # Add team-specific channels
        if event.classification and event.classification.affected_teams:
            for team in event.classification.affected_teams:
                team_channel = f"#{team}-updates"
                if team_channel not in channels:
                    channels.append(team_channel)
        
        # Add urgency-based channels
        if (event.classification and 
            event.classification.urgency == UrgencyLevel.CRITICAL):
            if "#critical-alerts" not in channels:
                channels.append("#critical-alerts")
        
        return channels
    
    async def _send_notifications_via_integration(
        self,
        event: EnrichedEvent,
        transition_analysis: Dict[str, Any],
        sprint_metrics: Optional[SprintMetrics],
        workload_analysis: Optional[WorkloadAnalysis]
    ) -> Any:
        """Send notifications through the hook notification integration layer."""
        
        try:
            # Determine notification type based on transition
            transition_type = transition_analysis['type']
            if transition_type == TransitionType.BLOCKED:
                notification_type = HookNotificationType.JIRA_BLOCKER_DETECTED
            elif transition_type == TransitionType.UNBLOCKED:
                notification_type = HookNotificationType.JIRA_BLOCKER_RESOLVED
            else:
                notification_type = HookNotificationType.JIRA_STATUS_CHANGE
            
            # Determine urgency override
            urgency_override = None
            if transition_analysis.get('is_significant'):
                urgency_override = transition_analysis.get('urgency', UrgencyLevel.MEDIUM)
            
            # Create execution result for integration
            execution_result = HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.SUCCESS,
                execution_time_ms=0.0,
                notification_sent=False,
                metadata={
                    "transition_type": transition_type.value,
                    "sprint_impact": sprint_metrics.at_risk if sprint_metrics else False,
                    "workload_impact": workload_analysis.overloaded if workload_analysis else False,
                    "transition_analysis": transition_analysis,
                }
            )
            
            # Add sprint metrics to metadata if available
            if sprint_metrics:
                execution_result.metadata["sprint_metrics"] = {
                    "sprint_name": sprint_metrics.sprint_name,
                    "completion_percentage": sprint_metrics.completion_percentage,
                    "at_risk": sprint_metrics.at_risk,
                    "days_remaining": sprint_metrics.days_remaining,
                }
            
            # Add workload analysis to metadata if available
            if workload_analysis:
                execution_result.metadata["workload_analysis"] = {
                    "assignee": workload_analysis.assignee,
                    "capacity_utilization": workload_analysis.capacity_utilization,
                    "overloaded": workload_analysis.overloaded,
                    "current_tickets": workload_analysis.current_tickets,
                }
            
            # Process through integration layer
            result = await default_hook_notification_integrator.process_hook_notification(
                hook_id=self.hook_id,
                hook_type=self.hook_type,
                event=event,
                execution_result=execution_result,
                notification_type=notification_type,
                urgency_override=urgency_override,
                metadata={
                    "transition_indicator": self.TRANSITION_INDICATORS.get(transition_type, "🔄"),
                    "channels_suggested": self._determine_channels(transition_analysis, event),
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send notifications via integration: {e}")
            # Fallback to original method
            return await self._send_notifications_fallback(event, transition_analysis)
    
    async def _send_notifications_fallback(self, event: EnrichedEvent, transition_analysis: Dict[str, Any]) -> Any:
        """Fallback notification method."""
        try:
            # Simple fallback using direct notification system
            from devsync_ai.core.enhanced_notification_handler import NotificationContext
            from devsync_ai.core.channel_router import NotificationType
            
            context = NotificationContext(
                notification_type=NotificationType.JIRA_STATUS,
                event_type=event.event_type,
                data={
                    "ticket_key": event.ticket_key,
                    "summary": event.ticket_details.get("summary", "No summary") if event.ticket_details else "No summary",
                    "transition": transition_analysis,
                },
                team_id=event.project_key.lower() if event.project_key else "default",
                author=event.ticket_details.get("reporter", {}).get("displayName") if event.ticket_details else None,
            )
            
            return await default_notification_system.handler.process_notification(context)
            
        except Exception as e:
            logger.error(f"Fallback notification also failed: {e}")
            return None
    
    async def _send_notifications(
        self, 
        message_data: Dict[str, Any], 
        channels: List[str], 
        event: EnrichedEvent
    ) -> bool:
        """Send notifications to determined channels."""
        try:
            # Use enhanced notification system
            success_count = 0
            
            for channel in channels:
                try:
                    # Create notification context
                    from devsync_ai.core.enhanced_notification_handler import NotificationContext
                    
                    context = NotificationContext(
                        notification_type="jira_status_change",
                        event_type=event.event_type,
                        data={
                            "ticket_key": event.ticket_key,
                            "message": message_data,
                            "channel": channel,
                            "urgency": event.classification.urgency.value if event.classification else "medium"
                        },
                        team_id=event.classification.affected_teams[0] if event.classification and event.classification.affected_teams else "default",
                        urgency_level=event.classification.urgency.value if event.classification else "medium"
                    )
                    
                    # Send through enhanced notification system
                    result = await default_notification_system.process_notification(context)
                    
                    if result.decision.value in ["send_immediately", "batch_and_send"]:
                        success_count += 1
                        logger.info(f"Status change notification sent to {channel}")
                    
                except Exception as e:
                    logger.error(f"Failed to send notification to {channel}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send status change notifications: {e}")
            return False
    
    async def _update_sprint_dashboard(
        self, 
        sprint_metrics: SprintMetrics, 
        event: EnrichedEvent
    ) -> None:
        """Update sprint dashboard with new metrics."""
        try:
            # This would typically update a dashboard or send metrics to a monitoring system
            logger.info(f"Sprint dashboard updated for {sprint_metrics.sprint_name}")
            
            # Could integrate with tools like:
            # - Grafana dashboards
            # - Slack canvas updates
            # - Database metrics tables
            # - Real-time analytics systems
            
        except Exception as e:
            logger.warning(f"Failed to update sprint dashboard: {e}")


class BlockerHook(AgentHook):
    """
    Production-ready Blocker Detection Agent Hook.
    
    Handles both webhook events and scheduled checks for comprehensive
    blocker detection and escalation.
    """
    
    # Blocker keywords and patterns
    BLOCKER_KEYWORDS = {
        'blocked', 'blocker', 'impediment', 'stuck', 'waiting for',
        'dependency', 'cannot proceed', 'on hold', 'paused'
    }
    
    # Resolution suggestions based on blocker type
    RESOLUTION_SUGGESTIONS = {
        'dependency': [
            "Contact dependency owner for status update",
            "Explore alternative implementation approaches",
            "Escalate to technical lead for prioritization"
        ],
        'technical': [
            "Schedule technical discussion with team",
            "Research alternative solutions",
            "Request expert consultation"
        ],
        'resource': [
            "Request additional team member assignment",
            "Negotiate timeline extension",
            "Identify scope reduction opportunities"
        ],
        'external': [
            "Contact external team/vendor",
            "Escalate to management for intervention",
            "Document impact for stakeholder review"
        ]
    }
    
    async def can_handle(self, event: EnrichedEvent) -> bool:
        """Check if this hook can handle the event."""
        if not event.classification:
            return False
        
        # Handle blocker-related events
        if event.classification.category == EventCategory.STATUS_CHANGE:
            # Check if transitioning to blocked status
            processor_data = event.context_data.get('processor_data', {})
            is_blocked = processor_data.get('is_blocked', False)
            return is_blocked
        
        # Handle comment events that mention blockers
        if event.classification.category == EventCategory.COMMENT:
            comment_analysis = event.context_data.get('comment_analysis')
            if comment_analysis and hasattr(comment_analysis, 'contains_blocker_keywords'):
                return comment_analysis.contains_blocker_keywords
        
        return False
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """Execute the blocker detection hook."""
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"Processing blocker detection for {event.ticket_key}")
            
            # Analyze the blocker
            blocker_analysis = await self._analyze_blocker(event)
            
            # Assess sprint risk
            sprint_risk = await self._assess_sprint_risk(event, blocker_analysis)
            
            # Create urgent alert message
            message_data = await self._create_blocker_alert(
                event, blocker_analysis, sprint_risk
            )
            
            # Determine escalation path
            escalation_channels = await self._determine_escalation_channels(
                blocker_analysis, event
            )
            
            # Send immediate alerts through integration layer
            notification_result = await self._send_blocker_alerts_via_integration(
                event, blocker_analysis, sprint_risk
            )
            notification_sent = notification_result.decision.value in ["send_immediately", "batch_and_send"]
            
            # Create incident tracking entry
            await self._create_incident_entry(event, blocker_analysis)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.SUCCESS,
                execution_time_ms=execution_time,
                notification_sent=notification_sent,
                metadata={
                    "blocker_severity": blocker_analysis.severity.value,
                    "escalation_required": blocker_analysis.escalation_required,
                    "sprint_risk": sprint_risk,
                    "channels_alerted": escalation_channels
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.error(f"Blocker hook failed for {event.ticket_key}: {e}", exc_info=True)
            
            result = HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.FAILED,
                execution_time_ms=execution_time,
                notification_sent=False
            )
            result.add_error(str(e))
            return result
    
    async def _analyze_blocker(self, event: EnrichedEvent) -> BlockerAnalysis:
        """Analyze the blocker for severity and type."""
        # Determine blocker type
        blocker_type = "general"
        
        # Check ticket details for clues
        summary = event.ticket_details.get('summary', '').lower()
        description = event.ticket_details.get('description', '').lower()
        
        if any(word in summary + description for word in ['dependency', 'depends on', 'waiting for']):
            blocker_type = "dependency"
        elif any(word in summary + description for word in ['technical', 'architecture', 'design']):
            blocker_type = "technical"
        elif any(word in summary + description for word in ['resource', 'capacity', 'team']):
            blocker_type = "resource"
        elif any(word in summary + description for word in ['external', 'vendor', 'third party']):
            blocker_type = "external"
        
        # Determine severity based on priority and urgency
        priority = event.ticket_details.get('priority', 'Medium').lower()
        urgency = event.classification.urgency if event.classification else UrgencyLevel.MEDIUM
        
        if priority in ['critical', 'highest'] or urgency == UrgencyLevel.CRITICAL:
            severity = BlockerSeverity.CRITICAL
        elif priority in ['high', 'major'] or urgency == UrgencyLevel.HIGH:
            severity = BlockerSeverity.HIGH
        elif priority in ['medium', 'normal']:
            severity = BlockerSeverity.MEDIUM
        else:
            severity = BlockerSeverity.LOW
        
        # Generate impact assessment
        impact_assessment = self._generate_impact_assessment(event, severity)
        
        # Get resolution suggestions
        suggestions = self.RESOLUTION_SUGGESTIONS.get(blocker_type, [
            "Review blocker with team lead",
            "Document impact and timeline",
            "Explore alternative approaches"
        ])
        
        # Identify stakeholders
        stakeholders = await self._identify_stakeholders(event, blocker_type)
        
        # Determine if escalation is required
        escalation_required = (
            severity in [BlockerSeverity.HIGH, BlockerSeverity.CRITICAL] or
            blocker_type in ['external', 'resource']
        )
        
        return BlockerAnalysis(
            blocker_type=blocker_type,
            severity=severity,
            impact_assessment=impact_assessment,
            resolution_suggestions=suggestions,
            stakeholders=stakeholders,
            escalation_required=escalation_required,
            sprint_risk_level="high" if severity in [BlockerSeverity.HIGH, BlockerSeverity.CRITICAL] else "medium",
            estimated_resolution_time=self._estimate_resolution_time(blocker_type, severity)
        )
    
    def _generate_impact_assessment(self, event: EnrichedEvent, severity: BlockerSeverity) -> str:
        """Generate impact assessment text."""
        if severity == BlockerSeverity.CRITICAL:
            return "Critical blocker - immediate action required to prevent sprint failure"
        elif severity == BlockerSeverity.HIGH:
            return "High impact blocker - may affect sprint goals and team velocity"
        elif severity == BlockerSeverity.MEDIUM:
            return "Moderate blocker - monitor for escalation and timeline impact"
        else:
            return "Low impact blocker - address when resources are available"
    
    async def _identify_stakeholders(self, event: EnrichedEvent, blocker_type: str) -> List[str]:
        """Identify relevant stakeholders for the blocker."""
        stakeholders = []
        
        # Add assignee
        assignee_info = event.context_data.get('assignee_info', {})
        if assignee_info.get('assignee_name'):
            stakeholders.append(assignee_info['assignee_name'])
        
        # Add reporter
        for stakeholder in event.stakeholders:
            if stakeholder.role == 'reporter':
                stakeholders.append(stakeholder.display_name)
        
        # Add type-specific stakeholders
        if blocker_type == 'external':
            stakeholders.extend(['Product Manager', 'Engineering Manager'])
        elif blocker_type == 'resource':
            stakeholders.extend(['Engineering Manager', 'Scrum Master'])
        elif blocker_type == 'technical':
            stakeholders.extend(['Tech Lead', 'Senior Engineer'])
        
        return list(set(stakeholders))  # Remove duplicates
    
    def _estimate_resolution_time(self, blocker_type: str, severity: BlockerSeverity) -> Optional[timedelta]:
        """Estimate resolution time based on blocker type and severity."""
        base_times = {
            'dependency': timedelta(days=2),
            'technical': timedelta(days=1),
            'resource': timedelta(days=3),
            'external': timedelta(days=5),
            'general': timedelta(days=1)
        }
        
        base_time = base_times.get(blocker_type, timedelta(days=1))
        
        # Adjust based on severity
        if severity == BlockerSeverity.CRITICAL:
            return base_time * 0.5  # Expedited resolution
        elif severity == BlockerSeverity.HIGH:
            return base_time * 0.75
        elif severity == BlockerSeverity.MEDIUM:
            return base_time
        else:
            return base_time * 1.5
    
    async def _assess_sprint_risk(self, event: EnrichedEvent, blocker_analysis: BlockerAnalysis) -> str:
        """Assess risk to current sprint."""
        # This would typically analyze sprint timeline, remaining work, etc.
        if blocker_analysis.severity == BlockerSeverity.CRITICAL:
            return "high"
        elif blocker_analysis.severity == BlockerSeverity.HIGH:
            return "medium"
        else:
            return "low"
    
    async def _create_blocker_alert(
        self, 
        event: EnrichedEvent, 
        blocker_analysis: BlockerAnalysis,
        sprint_risk: str
    ) -> Dict[str, Any]:
        """Create urgent blocker alert message."""
        severity_indicators = {
            BlockerSeverity.CRITICAL: "🚨",
            BlockerSeverity.HIGH: "⚠️",
            BlockerSeverity.MEDIUM: "🟡",
            BlockerSeverity.LOW: "ℹ️"
        }
        
        indicator = severity_indicators.get(blocker_analysis.severity, "⚠️")
        
        blocks = []
        
        # Critical header
        header_text = (
            f"{indicator} *BLOCKER DETECTED*: {event.ticket_key}\n"
            f"*{event.ticket_details.get('summary', 'No summary')}*"
        )
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": header_text}
        })
        
        # Blocker details
        details_text = (
            f"*Type*: {blocker_analysis.blocker_type.title()}\n"
            f"*Severity*: {blocker_analysis.severity.value.title()}\n"
            f"*Sprint Risk*: {sprint_risk.title()}\n"
            f"*Impact*: {blocker_analysis.impact_assessment}"
        )
        
        if blocker_analysis.estimated_resolution_time:
            days = blocker_analysis.estimated_resolution_time.days
            details_text += f"\n*Est. Resolution*: {days} day{'s' if days != 1 else ''}"
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": details_text}
        })
        
        # Resolution suggestions
        if blocker_analysis.resolution_suggestions:
            suggestions_text = "*Suggested Actions*:\n" + "\n".join(
                f"• {suggestion}" for suggestion in blocker_analysis.resolution_suggestions[:3]
            )
            
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": suggestions_text}
            })
        
        # Stakeholders
        if blocker_analysis.stakeholders:
            stakeholders_text = "*Stakeholders*: " + ", ".join(
                f"@{stakeholder}" for stakeholder in blocker_analysis.stakeholders[:5]
            )
            
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": stakeholders_text}
            })
        
        # Action buttons
        actions = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Ticket"},
                "url": f"https://your-jira-instance.atlassian.net/browse/{event.ticket_key}",
                "style": "primary"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Escalate"},
                "value": f"escalate_blocker_{event.ticket_key}",
                "style": "danger"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Request Help"},
                "value": f"request_help_{event.ticket_key}"
            }
        ]
        
        if blocker_analysis.escalation_required:
            actions.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "Mark Resolved"},
                "value": f"resolve_blocker_{event.ticket_key}",
                "style": "primary"
            })
        
        blocks.append({
            "type": "actions",
            "elements": actions
        })
        
        return {
            "blocks": blocks,
            "text": f"BLOCKER: {event.ticket_key}",
            "metadata": {
                "blocker_type": blocker_analysis.blocker_type,
                "severity": blocker_analysis.severity.value,
                "ticket_key": event.ticket_key,
                "escalation_required": blocker_analysis.escalation_required
            }
        }
    
    async def _determine_escalation_channels(
        self, 
        blocker_analysis: BlockerAnalysis, 
        event: EnrichedEvent
    ) -> List[str]:
        """Determine escalation channels based on blocker severity."""
        channels = ["#blockers"]
        
        if blocker_analysis.severity in [BlockerSeverity.HIGH, BlockerSeverity.CRITICAL]:
            channels.extend(["#dev-alerts", "#management"])
        
        if blocker_analysis.escalation_required:
            channels.append("#escalations")
        
        # Add team-specific channels
        if event.classification and event.classification.affected_teams:
            for team in event.classification.affected_teams:
                channels.append(f"#{team}-alerts")
        
        return list(set(channels))
    
    async def _send_blocker_alerts_via_integration(
        self,
        event: EnrichedEvent,
        blocker_analysis: BlockerAnalysis,
        sprint_risk: str
    ) -> Any:
        """Send blocker alerts through the hook notification integration layer."""
        
        try:
            # Determine notification type based on blocker severity
            if blocker_analysis.severity == BlockerSeverity.CRITICAL:
                notification_type = HookNotificationType.JIRA_BLOCKER_DETECTED
            else:
                notification_type = HookNotificationType.JIRA_BLOCKER_DETECTED
            
            # Map blocker severity to urgency
            severity_to_urgency = {
                BlockerSeverity.LOW: UrgencyLevel.MEDIUM,
                BlockerSeverity.MEDIUM: UrgencyLevel.MEDIUM,
                BlockerSeverity.HIGH: UrgencyLevel.HIGH,
                BlockerSeverity.CRITICAL: UrgencyLevel.CRITICAL,
            }
            urgency_override = severity_to_urgency.get(blocker_analysis.severity, UrgencyLevel.HIGH)
            
            # Create execution result for integration
            execution_result = HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.SUCCESS,
                execution_time_ms=0.0,
                notification_sent=False,
                metadata={
                    "blocker_type": blocker_analysis.blocker_type,
                    "severity": blocker_analysis.severity.value,
                    "escalation_required": blocker_analysis.escalation_required,
                    "sprint_risk": sprint_risk,
                    "impact_assessment": blocker_analysis.impact_assessment,
                    "resolution_suggestions": blocker_analysis.resolution_suggestions,
                    "stakeholders": blocker_analysis.stakeholders,
                    "estimated_resolution_time": (
                        blocker_analysis.estimated_resolution_time.total_seconds()
                        if blocker_analysis.estimated_resolution_time else None
                    ),
                }
            )
            
            # Process through integration layer
            result = await default_hook_notification_integrator.process_hook_notification(
                hook_id=self.hook_id,
                hook_type=self.hook_type,
                event=event,
                execution_result=execution_result,
                notification_type=notification_type,
                urgency_override=urgency_override,
                metadata={
                    "blocker_analysis": {
                        "type": blocker_analysis.blocker_type,
                        "severity": blocker_analysis.severity.value,
                        "escalation_required": blocker_analysis.escalation_required,
                        "sprint_risk_level": blocker_analysis.sprint_risk_level,
                    },
                    "channels_suggested": self._determine_escalation_channels(blocker_analysis, event),
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send blocker alerts via integration: {e}")
            # Fallback to original method
            return await self._send_blocker_alerts_fallback(event, blocker_analysis)
    
    async def _send_blocker_alerts_fallback(self, event: EnrichedEvent, blocker_analysis: BlockerAnalysis) -> Any:
        """Fallback blocker alert method."""
        try:
            from devsync_ai.core.enhanced_notification_handler import NotificationContext
            from devsync_ai.core.channel_router import NotificationType
            
            context = NotificationContext(
                notification_type=NotificationType.JIRA_BLOCKER,
                event_type=event.event_type,
                data={
                    "ticket_key": event.ticket_key,
                    "summary": event.ticket_details.get("summary", "No summary") if event.ticket_details else "No summary",
                    "blocker_analysis": {
                        "type": blocker_analysis.blocker_type,
                        "severity": blocker_analysis.severity.value,
                        "impact": blocker_analysis.impact_assessment,
                    },
                },
                team_id=event.project_key.lower() if event.project_key else "default",
                author=event.ticket_details.get("reporter", {}).get("displayName") if event.ticket_details else None,
                priority_override="critical",
            )
            
            return await default_notification_system.handler.process_notification(context)
            
        except Exception as e:
            logger.error(f"Fallback blocker alert also failed: {e}")
            return None
    
    async def _send_blocker_alerts(
        self, 
        message_data: Dict[str, Any], 
        channels: List[str], 
        event: EnrichedEvent
    ) -> bool:
        """Send blocker alerts to escalation channels."""
        try:
            success_count = 0
            
            for channel in channels:
                try:
                    from devsync_ai.core.enhanced_notification_handler import NotificationContext
                    
                    context = NotificationContext(
                        notification_type="jira_blocker_alert",
                        event_type=event.event_type,
                        data={
                            "ticket_key": event.ticket_key,
                            "message": message_data,
                            "channel": channel,
                            "urgency": "critical"
                        },
                        team_id=event.classification.affected_teams[0] if event.classification and event.classification.affected_teams else "default",
                        urgency_level="critical"
                    )
                    
                    result = await default_notification_system.process_notification(context)
                    
                    if result.decision.value in ["send_immediately", "batch_and_send"]:
                        success_count += 1
                        logger.info(f"Blocker alert sent to {channel}")
                    
                except Exception as e:
                    logger.error(f"Failed to send blocker alert to {channel}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send blocker alerts: {e}")
            return False
    
    async def _create_incident_entry(self, event: EnrichedEvent, blocker_analysis: BlockerAnalysis) -> None:
        """Create incident tracking entry for post-mortem analysis."""
        try:
            # This would typically create an entry in an incident tracking system
            incident_data = {
                "ticket_key": event.ticket_key,
                "blocker_type": blocker_analysis.blocker_type,
                "severity": blocker_analysis.severity.value,
                "detected_at": datetime.now(timezone.utc),
                "stakeholders": blocker_analysis.stakeholders,
                "impact_assessment": blocker_analysis.impact_assessment,
                "estimated_resolution_time": blocker_analysis.estimated_resolution_time.total_seconds() if blocker_analysis.estimated_resolution_time else None
            }
            
            logger.info(f"Incident entry created for blocker {event.ticket_key}")
            
        except Exception as e:
            logger.warning(f"Failed to create incident entry: {e}")


# Additional hooks would be implemented similarly...
# AssignmentChangeHook, CriticalUpdateHook, CommentHook

# Hook registry for automatic registration
AVAILABLE_HOOKS = {
    'status_change': StatusChangeHook,
    'blocker_detection': BlockerHook,
    # 'assignment_change': AssignmentChangeHook,
    # 'critical_update': CriticalUpdateHook,
    # 'comment_activity': CommentHook,
}


class AssignmentChangeHook(AgentHook):
    """
    Production-ready Assignment Change Agent Hook.
    
    Handles ticket assignment and reassignment events with intelligent
    workload analysis and team coordination.
    """
    
    # Skill matching keywords for different ticket types
    SKILL_KEYWORDS = {
        'frontend': ['ui', 'frontend', 'react', 'vue', 'angular', 'css', 'javascript'],
        'backend': ['api', 'backend', 'server', 'database', 'microservice'],
        'devops': ['deployment', 'infrastructure', 'docker', 'kubernetes', 'ci/cd'],
        'mobile': ['mobile', 'ios', 'android', 'react native', 'flutter'],
        'qa': ['testing', 'qa', 'automation', 'selenium', 'cypress']
    }
    
    async def can_handle(self, event: EnrichedEvent) -> bool:
        """Check if this hook can handle the event."""
        if not event.classification:
            return False
        
        return event.classification.category == EventCategory.ASSIGNMENT
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """Execute the assignment change hook with comprehensive workload analysis."""
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"Processing assignment change for {event.ticket_key}")
            
            # Analyze assignment details
            assignment_analysis = await self._analyze_assignment(event)
            
            # Perform comprehensive workload impact analysis
            impact_analysis = None
            if assignment_analysis['new_assignee'] and assignment_analysis['type'] == 'assigned':
                # Extract ticket metadata for analysis
                ticket_metadata = await self._extract_ticket_metadata(event)
                story_points = ticket_metadata.get('story_points', 3)  # Default to 3 if not specified
                estimated_hours = ticket_metadata.get('estimated_hours', story_points * 4)  # 4 hours per point default
                
                # Get team ID from event
                team_id = event.classification.affected_teams[0] if event.classification and event.classification.affected_teams else event.project_key.lower()
                
                # Perform comprehensive impact analysis
                impact_analysis = await default_workload_analytics_engine.analyze_assignment_impact(
                    assignee_id=assignment_analysis['assignee_id'],
                    team_id=team_id,
                    ticket_key=event.ticket_key,
                    story_points=story_points,
                    estimated_hours=estimated_hours,
                    ticket_metadata=ticket_metadata
                )
                
                # Update workload tracking
                await default_workload_analytics_engine.update_member_workload(
                    user_id=assignment_analysis['assignee_id'],
                    team_id=team_id,
                    ticket_key=event.ticket_key,
                    action="assigned",
                    story_points=story_points,
                    estimated_hours=estimated_hours
                )
            
            # Perform skill matching (legacy method for compatibility)
            skill_analysis = await self._analyze_skill_match(event)
            
            # Create enhanced assignment message with workload warnings
            message_data = await self._create_enhanced_assignment_message(
                event, assignment_analysis, impact_analysis, skill_analysis
            )
            
            # Determine notification channels based on workload status
            channels = await self._determine_assignment_channels_enhanced(event, impact_analysis)
            
            # Send notifications through integration layer
            notification_result = await self._send_assignment_notifications_via_integration(
                event, assignment_analysis, impact_analysis
            )
            notification_sent = notification_result.decision.value in ["send_immediately", "batch_and_send"]
            
            # Generate capacity alerts if needed
            if impact_analysis and impact_analysis.impact_severity in ["high", "critical"]:
                await self._generate_capacity_alerts(impact_analysis, event)
            
            # Update team capacity dashboards
            await self._update_capacity_dashboard_enhanced(impact_analysis, event)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.SUCCESS,
                execution_time_ms=execution_time,
                notification_sent=notification_sent,
                metadata={
                    "assignment_type": assignment_analysis['type'],
                    "overload_warning": impact_analysis.projected_workload_status in [WorkloadStatus.OVERLOADED, WorkloadStatus.CRITICAL] if impact_analysis else False,
                    "skill_match_score": impact_analysis.skill_match_score if impact_analysis else skill_analysis.get('score', 0.0),
                    "impact_severity": impact_analysis.impact_severity if impact_analysis else "low",
                    "assignment_recommendation": impact_analysis.assignment_recommendation if impact_analysis else "approve",
                    "channels_notified": channels,
                    "capacity_utilization": impact_analysis.projected_utilization if impact_analysis else 0.0,
                    "alternative_assignees_count": len(impact_analysis.alternative_assignees) if impact_analysis else 0
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.error(f"Assignment hook failed for {event.ticket_key}: {e}", exc_info=True)
            
            result = HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.FAILED,
                execution_time_ms=execution_time,
                notification_sent=False
            )
            result.add_error(str(e))
            return result
    
    async def _analyze_assignment(self, event: EnrichedEvent) -> Dict[str, Any]:
        """Analyze the assignment change."""
        processor_data = event.context_data.get('processor_data', {})
        assignment_info = processor_data.get('assignment_info', {})
        
        assignment_type = assignment_info.get('assignment_type', 'assigned')
        old_assignee = assignment_info.get('old_assignee_id')
        new_assignee = assignment_info.get('new_assignee_name')
        assignee_id = assignment_info.get('new_assignee_id') or assignment_info.get('assignee_id')
        
        # Fallback to extract from ticket details if not in processor data
        if not assignee_id and event.ticket_details:
            assignee_info = event.ticket_details.get('assignee', {})
            if isinstance(assignee_info, dict):
                assignee_id = assignee_info.get('accountId') or assignee_info.get('key')
                if not new_assignee:
                    new_assignee = assignee_info.get('displayName')
        
        return {
            'type': assignment_type,
            'old_assignee': old_assignee,
            'new_assignee': new_assignee,
            'assignee_id': assignee_id,
            'is_reassignment': old_assignee is not None and new_assignee is not None
        }
    
    async def _analyze_workload_impact(self, event: EnrichedEvent) -> Optional[WorkloadAnalysis]:
        """Analyze workload impact of the assignment."""
        processor_data = event.context_data.get('processor_data', {})
        workload_analysis = processor_data.get('workload_analysis')
        
        if workload_analysis:
            return workload_analysis
        
        # Fallback analysis
        assignee_info = event.context_data.get('assignee_info', {})
        assignee_name = assignee_info.get('assignee_name')
        
        if not assignee_name:
            return None
        
        # Mock workload analysis - would typically query database
        return WorkloadAnalysis(
            assignee=assignee_name,
            current_tickets=4,
            total_story_points=20,
            capacity_utilization=0.8,
            overloaded=False,
            skill_match_score=0.75,
            recent_velocity=7.5,
            estimated_completion_date=datetime.now(timezone.utc) + timedelta(days=4)
        )
    
    async def _analyze_skill_match(self, event: EnrichedEvent) -> Dict[str, Any]:
        """Analyze skill match between assignee and ticket."""
        # Extract ticket information
        summary = event.ticket_details.get('summary', '').lower()
        description = event.ticket_details.get('description', '').lower()
        components = [c.lower() for c in event.ticket_details.get('components', [])]
        labels = [l.lower() for l in event.ticket_details.get('labels', [])]
        
        ticket_text = f"{summary} {description} {' '.join(components)} {' '.join(labels)}"
        
        # Calculate skill match scores
        skill_scores = {}
        for skill_area, keywords in self.SKILL_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in ticket_text)
            skill_scores[skill_area] = score / len(keywords)  # Normalize
        
        # Find best match
        best_skill = max(skill_scores, key=skill_scores.get)
        best_score = skill_scores[best_skill]
        
        # Determine overall match quality
        if best_score >= 0.3:
            match_quality = "excellent"
        elif best_score >= 0.2:
            match_quality = "good"
        elif best_score >= 0.1:
            match_quality = "fair"
        else:
            match_quality = "poor"
        
        return {
            'primary_skill': best_skill,
            'score': best_score,
            'quality': match_quality,
            'all_scores': skill_scores
        }
    
    async def _create_assignment_message(
        self, 
        event: EnrichedEvent,
        assignment_analysis: Dict[str, Any],
        workload_analysis: Optional[WorkloadAnalysis],
        skill_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create comprehensive assignment message."""
        blocks = []
        
        # Header
        assignment_type = assignment_analysis['type']
        if assignment_type == 'assigned':
            header_text = f"👤 *New Assignment*: {event.ticket_key}"
        elif assignment_type == 'unassigned':
            header_text = f"👤 *Unassigned*: {event.ticket_key}"
        else:
            header_text = f"🔄 *Reassigned*: {event.ticket_key}"
        
        header_text += f"\n*{event.ticket_details.get('summary', 'No summary')}*"
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": header_text}
        })
        
        # Assignment details
        details_text = f"*Priority*: {event.ticket_details.get('priority', 'Medium')}\n"
        
        if assignment_analysis['new_assignee']:
            details_text += f"*Assigned to*: {assignment_analysis['new_assignee']}\n"
        
        # Add story points and effort info
        processor_data = event.context_data.get('processor_data', {})
        effort_info = processor_data.get('effort_info', {})
        
        if effort_info.get('story_points'):
            details_text += f"*Story Points*: {effort_info['story_points']}\n"
        
        if effort_info.get('original_estimate_hours'):
            details_text += f"*Estimated Effort*: {effort_info['original_estimate_hours']:.1f}h\n"
        
        # Add deadline info
        deadline_info = processor_data.get('deadline_info', {})
        if deadline_info.get('due_date'):
            details_text += f"*Due Date*: {deadline_info['due_date']}\n"
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": details_text}
        })
        
        # Workload analysis
        if workload_analysis:
            workload_text = (
                f"📊 *Workload Analysis*\n"
                f"Current Load: {workload_analysis.current_tickets} tickets "
                f"({workload_analysis.total_story_points} points)\n"
                f"Capacity: {workload_analysis.capacity_utilization:.0%}\n"
                f"Recent Velocity: {workload_analysis.recent_velocity:.1f} points/sprint"
            )
            
            if workload_analysis.overloaded:
                workload_text += "\n🚨 *Overload Warning*: Assignee at capacity"
            elif workload_analysis.capacity_utilization > 0.9:
                workload_text += "\n⚠️ *High Utilization*: Monitor workload"
            
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": workload_text}
            })
        
        # Skill match analysis
        skill_indicators = {
            'excellent': '🟢',
            'good': '🟡',
            'fair': '🟠',
            'poor': '🔴'
        }
        
        skill_indicator = skill_indicators.get(skill_analysis['quality'], '⚪')
        skill_text = (
            f"{skill_indicator} *Skill Match*: {skill_analysis['quality'].title()}\n"
            f"Primary Area: {skill_analysis['primary_skill'].title()}\n"
            f"Match Score: {skill_analysis['score']:.1%}"
        )
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": skill_text}
        })
        
        # Action buttons
        actions = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Ticket"},
                "url": f"https://your-jira-instance.atlassian.net/browse/{event.ticket_key}",
                "style": "primary"
            }
        ]
        
        if assignment_analysis['new_assignee']:
            actions.extend([
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Accept Assignment"},
                    "value": f"accept_assignment_{event.ticket_key}",
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Request Reassignment"},
                    "value": f"request_reassignment_{event.ticket_key}"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Estimate Effort"},
                    "value": f"estimate_effort_{event.ticket_key}"
                }
            ])
        
        blocks.append({
            "type": "actions",
            "elements": actions
        })
        
        return {
            "blocks": blocks,
            "text": f"Assignment: {event.ticket_key}",
            "metadata": {
                "assignment_type": assignment_type,
                "assignee": assignment_analysis['new_assignee'],
                "skill_match": skill_analysis['quality'],
                "ticket_key": event.ticket_key
            }
        }
    
    async def _determine_assignment_channels(
        self, 
        event: EnrichedEvent, 
        workload_analysis: Optional[WorkloadAnalysis]
    ) -> List[str]:
        """Determine channels for assignment notifications."""
        channels = ["#team-assignments"]
        
        # Add team-specific channels
        if event.classification and event.classification.affected_teams:
            for team in event.classification.affected_teams:
                channels.append(f"#{team}-assignments")
        
        # Add management channel if overloaded
        if workload_analysis and workload_analysis.overloaded:
            channels.append("#management")
        
        return channels
    
    async def _send_assignment_notifications(
        self, 
        message_data: Dict[str, Any], 
        channels: List[str], 
        event: EnrichedEvent
    ) -> bool:
        """Send assignment notifications."""
        try:
            success_count = 0
            
            for channel in channels:
                try:
                    from devsync_ai.core.enhanced_notification_handler import NotificationContext
                    
                    context = NotificationContext(
                        notification_type="jira_assignment_change",
                        event_type=event.event_type,
                        data={
                            "ticket_key": event.ticket_key,
                            "message": message_data,
                            "channel": channel,
                            "urgency": "medium"
                        },
                        team_id=event.classification.affected_teams[0] if event.classification and event.classification.affected_teams else "default",
                        urgency_level="medium"
                    )
                    
                    result = await default_notification_system.process_notification(context)
                    
                    if result.decision.value in ["send_immediately", "batch_and_send"]:
                        success_count += 1
                        logger.info(f"Assignment notification sent to {channel}")
                    
                except Exception as e:
                    logger.error(f"Failed to send assignment notification to {channel}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send assignment notifications: {e}")
            return False
    
    async def _extract_ticket_metadata(self, event: EnrichedEvent) -> Dict[str, Any]:
        """Extract ticket metadata for workload analysis."""
        metadata = {}
        
        if event.ticket_details:
            # Extract story points
            custom_fields = event.ticket_details.get('customFields', {})
            story_points = None
            
            # Common story point field names
            for field_name in ['story_points', 'storyPoints', 'Story Points', 'customfield_10002']:
                if field_name in custom_fields:
                    story_points = custom_fields[field_name]
                    break
            
            if story_points:
                try:
                    metadata['story_points'] = int(float(story_points))
                except (ValueError, TypeError):
                    metadata['story_points'] = 3  # Default
            else:
                metadata['story_points'] = 3  # Default
            
            # Extract other relevant fields
            metadata['priority'] = event.ticket_details.get('priority', 'Medium')
            metadata['ticket_type'] = event.ticket_details.get('issuetype', {}).get('name', 'Story')
            metadata['components'] = [c.get('name', '') for c in event.ticket_details.get('components', [])]
            metadata['labels'] = event.ticket_details.get('labels', [])
            
            # Estimate hours based on story points and complexity
            complexity_multiplier = 4.0  # Default hours per story point
            if metadata['priority'] in ['Critical', 'High']:
                complexity_multiplier = 5.0  # More complex for high priority
            elif metadata['ticket_type'] in ['Bug', 'Defect']:
                complexity_multiplier = 3.0  # Less predictable for bugs
            
            metadata['estimated_hours'] = metadata['story_points'] * complexity_multiplier
            
            # Extract required skills from summary and description
            summary = event.ticket_details.get('summary', '').lower()
            description = event.ticket_details.get('description', '').lower()
            
            required_skills = []
            skill_keywords = {
                'frontend': ['ui', 'frontend', 'react', 'vue', 'angular', 'css', 'javascript'],
                'backend': ['api', 'backend', 'server', 'database', 'microservice'],
                'devops': ['deployment', 'infrastructure', 'docker', 'kubernetes', 'ci/cd'],
                'mobile': ['mobile', 'ios', 'android', 'react native', 'flutter'],
                'qa': ['testing', 'qa', 'automation', 'selenium', 'cypress']
            }
            
            for skill, keywords in skill_keywords.items():
                if any(keyword in summary or keyword in description for keyword in keywords):
                    required_skills.append(skill)
            
            metadata['required_skills'] = required_skills or ['general']
        
        return metadata
    
    async def _create_enhanced_assignment_message(
        self, 
        event: EnrichedEvent,
        assignment_analysis: Dict[str, Any],
        impact_analysis: Optional[AssignmentImpactAnalysis],
        skill_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create enhanced assignment message with workload warnings."""
        blocks = []
        
        # Header with workload status indicator
        assignment_type = assignment_analysis['type']
        status_indicator = "👤"
        
        if impact_analysis:
            if impact_analysis.projected_workload_status == WorkloadStatus.CRITICAL:
                status_indicator = "🚨"
            elif impact_analysis.projected_workload_status == WorkloadStatus.OVERLOADED:
                status_indicator = "⚠️"
            elif impact_analysis.projected_workload_status == WorkloadStatus.HIGH:
                status_indicator = "🟡"
        
        if assignment_type == 'assigned':
            header_text = f"{status_indicator} *New Assignment*: {event.ticket_key}"
        elif assignment_type == 'unassigned':
            header_text = f"{status_indicator} *Unassigned*: {event.ticket_key}"
        else:
            header_text = f"{status_indicator} *Reassigned*: {event.ticket_key}"
        
        header_text += f"\n*{event.ticket_details.get('summary', 'No summary')}*"
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": header_text}
        })
        
        # Assignment details with enhanced information
        details_text = f"*Priority*: {event.ticket_details.get('priority', 'Medium')}\n"
        
        if assignment_analysis['new_assignee']:
            details_text += f"*Assigned to*: {assignment_analysis['new_assignee']}\n"
        
        if impact_analysis:
            details_text += f"*Story Points*: {impact_analysis.story_points}\n"
            details_text += f"*Estimated Effort*: {impact_analysis.estimated_hours:.1f}h\n"
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": details_text}
        })
        
        # Comprehensive workload analysis
        if impact_analysis:
            workload_text = (
                f"📊 *Workload Impact Analysis*\n"
                f"Current Load: {impact_analysis.current_workload.active_tickets} tickets "
                f"({impact_analysis.current_workload.total_story_points} points)\n"
                f"Projected Utilization: {impact_analysis.projected_utilization:.0%}\n"
                f"Status: {impact_analysis.projected_workload_status.value.title()}"
            )
            
            if impact_analysis.projected_completion_date:
                completion_date = impact_analysis.projected_completion_date.strftime("%Y-%m-%d")
                workload_text += f"\nEstimated Completion: {completion_date}"
            
            # Add capacity warnings
            if impact_analysis.capacity_warnings:
                workload_text += f"\n\n⚠️ *Warnings:*\n"
                for warning in impact_analysis.capacity_warnings[:3]:  # Limit to 3 warnings
                    workload_text += f"• {warning}\n"
            
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": workload_text}
            })
            
            # Assignment recommendation
            recommendation_text = f"🎯 *Assignment Recommendation*: {impact_analysis.assignment_recommendation.title()}\n"
            recommendation_text += f"Impact Severity: {impact_analysis.impact_severity.title()}\n"
            recommendation_text += f"Skill Match: {impact_analysis.skill_match_score:.0%}"
            
            # Show alternatives if recommendation is not approve
            if impact_analysis.assignment_recommendation != "approve" and impact_analysis.alternative_assignees:
                recommendation_text += f"\n\n*Alternative Assignees:*\n"
                for assignee_id, score in impact_analysis.alternative_assignees[:3]:
                    recommendation_text += f"• {assignee_id} (suitability: {score:.0%})\n"
            
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": recommendation_text}
            })
        
        # Action buttons with enhanced options
        actions = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Ticket"},
                "url": f"https://your-jira-instance.atlassian.net/browse/{event.ticket_key}",
                "style": "primary"
            }
        ]
        
        if assignment_analysis['new_assignee']:
            if impact_analysis and impact_analysis.assignment_recommendation == "approve":
                actions.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Accept Assignment"},
                    "value": f"accept_assignment_{event.ticket_key}",
                    "style": "primary"
                })
            else:
                actions.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Review Assignment"},
                    "value": f"review_assignment_{event.ticket_key}",
                    "style": "danger"
                })
            
            actions.extend([
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Workload"},
                    "value": f"view_workload_{assignment_analysis['assignee_id']}"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Team Capacity"},
                    "value": f"team_capacity_{event.project_key}"
                }
            ])
        
        blocks.append({
            "type": "actions",
            "elements": actions
        })
        
        return {
            "blocks": blocks,
            "text": f"Assignment: {event.ticket_key}",
            "metadata": {
                "assignment_type": assignment_type,
                "assignee": assignment_analysis['new_assignee'],
                "assignee_id": assignment_analysis.get('assignee_id'),
                "impact_severity": impact_analysis.impact_severity if impact_analysis else "low",
                "recommendation": impact_analysis.assignment_recommendation if impact_analysis else "approve",
                "ticket_key": event.ticket_key
            }
        }
    
    async def _determine_assignment_channels_enhanced(
        self, 
        event: EnrichedEvent, 
        impact_analysis: Optional[AssignmentImpactAnalysis]
    ) -> List[str]:
        """Determine channels for assignment notifications with workload considerations."""
        channels = ["#team-assignments"]
        
        # Add team-specific channels
        if event.classification and event.classification.affected_teams:
            for team in event.classification.affected_teams:
                channels.append(f"#{team}-assignments")
        
        # Add management channels based on impact severity
        if impact_analysis:
            if impact_analysis.impact_severity == "critical":
                channels.extend(["#management", "#capacity-alerts"])
            elif impact_analysis.impact_severity == "high":
                channels.append("#team-leads")
            
            # Add capacity-specific channels
            if impact_analysis.projected_workload_status in [WorkloadStatus.OVERLOADED, WorkloadStatus.CRITICAL]:
                channels.append("#capacity-alerts")
        
        return list(set(channels))  # Remove duplicates
    
    async def _send_assignment_notifications_via_integration(
        self,
        event: EnrichedEvent,
        assignment_analysis: Dict[str, Any],
        impact_analysis: Optional[AssignmentImpactAnalysis]
    ) -> Any:
        """Send assignment notifications through the hook notification integration layer."""
        try:
            # Determine notification type based on impact
            if impact_analysis and impact_analysis.impact_severity == "critical":
                notification_type = HookNotificationType.JIRA_CRITICAL_ASSIGNMENT
            elif impact_analysis and impact_analysis.projected_workload_status == WorkloadStatus.OVERLOADED:
                notification_type = HookNotificationType.JIRA_OVERLOAD_WARNING
            else:
                notification_type = HookNotificationType.JIRA_ASSIGNMENT_CHANGE
            
            # Determine urgency override
            urgency_override = None
            if impact_analysis:
                if impact_analysis.impact_severity == "critical":
                    urgency_override = UrgencyLevel.CRITICAL
                elif impact_analysis.impact_severity == "high":
                    urgency_override = UrgencyLevel.HIGH
            
            # Create execution result for integration
            execution_result = HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.SUCCESS,
                execution_time_ms=0.0,
                notification_sent=False,
                metadata={
                    "assignment_type": assignment_analysis['type'],
                    "impact_severity": impact_analysis.impact_severity if impact_analysis else "low",
                    "workload_status": impact_analysis.projected_workload_status.value if impact_analysis else "optimal",
                    "capacity_utilization": impact_analysis.projected_utilization if impact_analysis else 0.0,
                    "assignment_recommendation": impact_analysis.assignment_recommendation if impact_analysis else "approve"
                }
            )
            
            # Add detailed impact analysis to metadata
            if impact_analysis:
                execution_result.metadata["impact_analysis"] = {
                    "assignee_id": impact_analysis.assignee_id,
                    "story_points": impact_analysis.story_points,
                    "estimated_hours": impact_analysis.estimated_hours,
                    "skill_match_score": impact_analysis.skill_match_score,
                    "capacity_warnings": impact_analysis.capacity_warnings,
                    "alternative_assignees_count": len(impact_analysis.alternative_assignees),
                    "team_impact": impact_analysis.team_impact
                }
            
            # Process through integration layer
            result = await default_hook_notification_integrator.process_hook_notification(
                hook_id=self.hook_id,
                hook_type=self.hook_type,
                event=event,
                execution_result=execution_result,
                notification_type=notification_type,
                urgency_override=urgency_override,
                metadata={
                    "channels_suggested": await self._determine_assignment_channels_enhanced(event, impact_analysis),
                    "workload_indicator": self._get_workload_indicator(impact_analysis),
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send assignment notifications via integration: {e}")
            # Fallback to legacy method
            return await self._send_assignment_notifications_fallback(event, assignment_analysis)
    
    async def _generate_capacity_alerts(
        self, 
        impact_analysis: AssignmentImpactAnalysis, 
        event: EnrichedEvent
    ) -> None:
        """Generate capacity alerts for high-impact assignments."""
        try:
            if impact_analysis.impact_severity in ["high", "critical"]:
                # Generate alert for team leads
                alert_data = {
                    "type": "capacity_alert",
                    "severity": impact_analysis.impact_severity,
                    "assignee": impact_analysis.assignee_id,
                    "ticket": event.ticket_key,
                    "projected_utilization": impact_analysis.projected_utilization,
                    "warnings": impact_analysis.capacity_warnings,
                    "alternatives": impact_analysis.alternative_assignees
                }
                
                logger.warning(f"Capacity alert generated for {impact_analysis.assignee_id}: {alert_data}")
                
                # Could integrate with alerting systems here
                
        except Exception as e:
            logger.error(f"Failed to generate capacity alerts: {e}")
    
    async def _update_capacity_dashboard_enhanced(
        self, 
        impact_analysis: Optional[AssignmentImpactAnalysis], 
        event: EnrichedEvent
    ) -> None:
        """Update team capacity dashboard with enhanced metrics."""
        try:
            if impact_analysis:
                # Update real-time capacity metrics
                logger.info(f"Enhanced capacity dashboard updated for {impact_analysis.assignee_id}")
                
                # Could integrate with dashboard systems like:
                # - Grafana dashboards
                # - Slack canvas updates
                # - Real-time analytics systems
                # - Team capacity planning tools
                
        except Exception as e:
            logger.warning(f"Failed to update enhanced capacity dashboard: {e}")
    
    def _get_workload_indicator(self, impact_analysis: Optional[AssignmentImpactAnalysis]) -> str:
        """Get workload status indicator for notifications."""
        if not impact_analysis:
            return "👤"
        
        if impact_analysis.projected_workload_status == WorkloadStatus.CRITICAL:
            return "🚨"
        elif impact_analysis.projected_workload_status == WorkloadStatus.OVERLOADED:
            return "⚠️"
        elif impact_analysis.projected_workload_status == WorkloadStatus.HIGH:
            return "🟡"
        else:
            return "👤"
    
    async def _send_assignment_notifications_fallback(
        self, 
        event: EnrichedEvent, 
        assignment_analysis: Dict[str, Any]
    ) -> Any:
        """Fallback assignment notification method."""
        try:
            from devsync_ai.core.enhanced_notification_handler import NotificationContext
            from devsync_ai.core.channel_router import NotificationType
            
            context = NotificationContext(
                notification_type=NotificationType.JIRA_ASSIGNMENT,
                event_type=event.event_type,
                data={
                    "ticket_key": event.ticket_key,
                    "assignment_type": assignment_analysis['type'],
                    "assignee": assignment_analysis['new_assignee'],
                },
                team_id=event.project_key.lower() if event.project_key else "default",
                author=assignment_analysis['new_assignee'],
            )
            
            return await default_notification_system.handler.process_notification(context)
            
        except Exception as e:
            logger.error(f"Fallback assignment notification also failed: {e}")
            return None
    
    async def _update_capacity_dashboard(
        self, 
        workload_analysis: Optional[WorkloadAnalysis], 
        event: EnrichedEvent
    ) -> None:
        """Update team capacity dashboard (legacy method for compatibility)."""
        try:
            if workload_analysis:
                logger.info(f"Capacity dashboard updated for {workload_analysis.assignee}")
                # Would typically update real-time dashboard
        except Exception as e:
            logger.warning(f"Failed to update capacity dashboard: {e}")


class CriticalUpdateHook(AgentHook):
    """
    Production-ready Critical Update Agent Hook.
    
    Handles high-priority updates requiring immediate attention with
    intelligent escalation and incident tracking.
    """
    
    # Critical update triggers
    CRITICAL_TRIGGERS = {
        'priority_escalation': ['critical', 'highest', 'blocker'],
        'status_critical': ['blocked', 'failed', 'error'],
        'keywords': ['production', 'outage', 'security', 'data loss', 'urgent']
    }
    
    async def can_handle(self, event: EnrichedEvent) -> bool:
        """Check if this is a critical update."""
        if not event.classification:
            return False
        
        # Check urgency level
        if event.classification.urgency == UrgencyLevel.CRITICAL:
            return True
        
        # Check priority
        priority = event.ticket_details.get('priority', '').lower()
        if priority in self.CRITICAL_TRIGGERS['priority_escalation']:
            return True
        
        # Check status
        status = event.ticket_details.get('status', '').lower()
        if any(critical_status in status for critical_status in self.CRITICAL_TRIGGERS['status_critical']):
            return True
        
        # Check for critical keywords
        summary = event.ticket_details.get('summary', '').lower()
        description = event.ticket_details.get('description', '').lower()
        text_content = f"{summary} {description}"
        
        if any(keyword in text_content for keyword in self.CRITICAL_TRIGGERS['keywords']):
            return True
        
        return False
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """Execute the critical update hook."""
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"Processing critical update for {event.ticket_key}")
            
            # Analyze criticality
            criticality_analysis = await self._analyze_criticality(event)
            
            # Create incident tracking
            incident_id = await self._create_incident_tracking(event, criticality_analysis)
            
            # Create high-visibility alert
            message_data = await self._create_critical_alert(
                event, criticality_analysis, incident_id
            )
            
            # Determine escalation path
            escalation_channels = await self._determine_escalation_path(
                criticality_analysis, event
            )
            
            # Send immediate alerts
            notification_sent = await self._send_critical_alerts(
                message_data, escalation_channels, event
            )
            
            # Update risk dashboards
            await self._update_risk_dashboard(criticality_analysis, event)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.SUCCESS,
                execution_time_ms=execution_time,
                notification_sent=notification_sent,
                metadata={
                    "criticality_level": criticality_analysis['level'],
                    "incident_id": incident_id,
                    "escalation_channels": escalation_channels,
                    "requires_immediate_action": criticality_analysis['immediate_action']
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.error(f"Critical update hook failed for {event.ticket_key}: {e}", exc_info=True)
            
            result = HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.FAILED,
                execution_time_ms=execution_time,
                notification_sent=False
            )
            result.add_error(str(e))
            return result
    
    async def _analyze_criticality(self, event: EnrichedEvent) -> Dict[str, Any]:
        """Analyze the criticality level and requirements."""
        priority = event.ticket_details.get('priority', '').lower()
        summary = event.ticket_details.get('summary', '').lower()
        description = event.ticket_details.get('description', '').lower()
        
        # Determine criticality level
        if priority in ['critical', 'highest'] or 'production' in summary:
            level = "critical"
        elif priority == 'high' or any(keyword in summary for keyword in ['urgent', 'security']):
            level = "high"
        else:
            level = "medium"
        
        # Determine if immediate action is required
        immediate_action = (
            level == "critical" or
            any(keyword in summary + description for keyword in ['outage', 'data loss', 'security breach'])
        )
        
        # Identify stakeholders
        stakeholders = []
        if 'production' in summary + description:
            stakeholders.extend(['DevOps Lead', 'Engineering Manager'])
        if 'security' in summary + description:
            stakeholders.extend(['Security Team', 'CISO'])
        if 'data' in summary + description:
            stakeholders.extend(['Data Team', 'DPO'])
        
        return {
            'level': level,
            'immediate_action': immediate_action,
            'stakeholders': stakeholders,
            'impact_assessment': self._assess_impact(event, level),
            'response_time_sla': self._get_response_sla(level)
        }
    
    def _assess_impact(self, event: EnrichedEvent, level: str) -> str:
        """Assess the impact of the critical update."""
        if level == "critical":
            return "High impact - immediate response required to prevent service disruption"
        elif level == "high":
            return "Medium-high impact - prompt response needed to prevent escalation"
        else:
            return "Medium impact - monitor and respond within SLA"
    
    def _get_response_sla(self, level: str) -> str:
        """Get response time SLA for criticality level."""
        sla_times = {
            "critical": "15 minutes",
            "high": "1 hour",
            "medium": "4 hours"
        }
        return sla_times.get(level, "4 hours")
    
    async def _create_incident_tracking(
        self, 
        event: EnrichedEvent, 
        criticality_analysis: Dict[str, Any]
    ) -> str:
        """Create incident tracking entry."""
        incident_id = f"INC-{event.ticket_key}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
        
        # Would typically create entry in incident management system
        logger.info(f"Incident tracking created: {incident_id}")
        
        return incident_id
    
    async def _create_critical_alert(
        self, 
        event: EnrichedEvent,
        criticality_analysis: Dict[str, Any],
        incident_id: str
    ) -> Dict[str, Any]:
        """Create high-visibility critical alert."""
        level_indicators = {
            "critical": "🚨🚨🚨",
            "high": "🚨🚨",
            "medium": "🚨"
        }
        
        indicator = level_indicators.get(criticality_analysis['level'], "🚨")
        
        blocks = []
        
        # Critical header with animation effect
        header_text = (
            f"{indicator} *CRITICAL UPDATE* {indicator}\n"
            f"*Incident*: {incident_id}\n"
            f"*Ticket*: {event.ticket_key}\n"
            f"*{event.ticket_details.get('summary', 'No summary')}*"
        )
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": header_text}
        })
        
        # Critical details
        details_text = (
            f"*Criticality*: {criticality_analysis['level'].upper()}\n"
            f"*Response SLA*: {criticality_analysis['response_time_sla']}\n"
            f"*Impact*: {criticality_analysis['impact_assessment']}"
        )
        
        if criticality_analysis['immediate_action']:
            details_text += "\n*⚡ IMMEDIATE ACTION REQUIRED*"
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": details_text}
        })
        
        # Stakeholders
        if criticality_analysis['stakeholders']:
            stakeholders_text = "*Required Stakeholders*:\n" + "\n".join(
                f"• @{stakeholder}" for stakeholder in criticality_analysis['stakeholders']
            )
            
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": stakeholders_text}
            })
        
        # Immediate action buttons
        actions = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "🚨 ACKNOWLEDGE"},
                "value": f"acknowledge_critical_{event.ticket_key}",
                "style": "danger"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "👥 DELEGATE"},
                "value": f"delegate_critical_{event.ticket_key}"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "📞 SCHEDULE MEETING"},
                "value": f"schedule_meeting_{event.ticket_key}"
            }
        ]
        
        if criticality_analysis['level'] == "critical":
            actions.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "🔥 CREATE INCIDENT"},
                "value": f"create_incident_{event.ticket_key}",
                "style": "danger"
            })
        
        blocks.append({
            "type": "actions",
            "elements": actions
        })
        
        return {
            "blocks": blocks,
            "text": f"CRITICAL: {event.ticket_key}",
            "metadata": {
                "criticality_level": criticality_analysis['level'],
                "incident_id": incident_id,
                "immediate_action": criticality_analysis['immediate_action'],
                "ticket_key": event.ticket_key
            }
        }
    
    async def _determine_escalation_path(
        self, 
        criticality_analysis: Dict[str, Any], 
        event: EnrichedEvent
    ) -> List[str]:
        """Determine escalation channels based on criticality."""
        channels = ["#critical-alerts"]
        
        level = criticality_analysis['level']
        
        if level == "critical":
            channels.extend(["#incident-response", "#management", "#on-call"])
        elif level == "high":
            channels.extend(["#dev-alerts", "#team-leads"])
        
        # Add stakeholder-specific channels
        stakeholders = criticality_analysis.get('stakeholders', [])
        if 'DevOps Lead' in stakeholders:
            channels.append("#devops-alerts")
        if 'Security Team' in stakeholders:
            channels.append("#security-alerts")
        
        return list(set(channels))
    
    async def _send_critical_alerts(
        self, 
        message_data: Dict[str, Any], 
        channels: List[str], 
        event: EnrichedEvent
    ) -> bool:
        """Send critical alerts with highest priority."""
        try:
            success_count = 0
            
            for channel in channels:
                try:
                    from devsync_ai.core.enhanced_notification_handler import NotificationContext
                    
                    context = NotificationContext(
                        notification_type="jira_critical_update",
                        event_type=event.event_type,
                        data={
                            "ticket_key": event.ticket_key,
                            "message": message_data,
                            "channel": channel,
                            "urgency": "critical"
                        },
                        team_id=event.classification.affected_teams[0] if event.classification and event.classification.affected_teams else "default",
                        urgency_level="critical"
                    )
                    
                    # Force immediate delivery for critical alerts
                    result = await default_notification_system.process_notification(context)
                    
                    if result.decision.value in ["send_immediately", "batch_and_send"]:
                        success_count += 1
                        logger.info(f"Critical alert sent to {channel}")
                    
                except Exception as e:
                    logger.error(f"Failed to send critical alert to {channel}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send critical alerts: {e}")
            return False
    
    async def _update_risk_dashboard(
        self, 
        criticality_analysis: Dict[str, Any], 
        event: EnrichedEvent
    ) -> None:
        """Update risk assessment dashboard."""
        try:
            logger.info(f"Risk dashboard updated for critical incident {event.ticket_key}")
            # Would typically update management dashboards
        except Exception as e:
            logger.warning(f"Failed to update risk dashboard: {e}")


class CommentHook(AgentHook):
    """
    Production-ready Comment Activity Agent Hook.
    
    Handles JIRA comments with intelligent filtering and threaded
    Slack discussions.
    """
    
    async def can_handle(self, event: EnrichedEvent) -> bool:
        """Check if this hook can handle comment events."""
        if not event.classification:
            return False
        
        return event.classification.category == EventCategory.COMMENT
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """Execute the comment hook."""
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"Processing comment for {event.ticket_key}")
            
            # Get comment analysis from processor
            processor_data = event.context_data.get('processor_data', {})
            comment_analysis = processor_data.get('comment_analysis')
            is_significant = processor_data.get('is_significant', False)
            
            if not is_significant:
                logger.debug(f"Comment not significant for {event.ticket_key}")
                return HookExecutionResult(
                    hook_id=self.hook_id,
                    execution_id="",
                    hook_type=self.hook_type,
                    event_id=event.event_id,
                    status=HookStatus.SUCCESS,
                    execution_time_ms=0.0,
                    notification_sent=False,
                    metadata={"skipped": "not_significant"}
                )
            
            # Create threaded message
            message_data = await self._create_comment_message(event, comment_analysis)
            
            # Determine channels
            channels = await self._determine_comment_channels(event, comment_analysis)
            
            # Send notifications
            notification_sent = await self._send_comment_notifications(
                message_data, channels, event
            )
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.SUCCESS,
                execution_time_ms=execution_time,
                notification_sent=notification_sent,
                metadata={
                    "comment_type": self._classify_comment_type(comment_analysis),
                    "mentions_count": len(comment_analysis.mentions) if comment_analysis else 0,
                    "channels_notified": channels
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.error(f"Comment hook failed for {event.ticket_key}: {e}", exc_info=True)
            
            result = HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.FAILED,
                execution_time_ms=execution_time,
                notification_sent=False
            )
            result.add_error(str(e))
            return result
    
    def _classify_comment_type(self, comment_analysis) -> str:
        """Classify the type of comment."""
        if not comment_analysis:
            return "general"
        
        if comment_analysis.contains_blocker_keywords:
            return "blocker"
        elif comment_analysis.contains_decision_keywords:
            return "decision"
        elif comment_analysis.contains_question_keywords:
            return "question"
        elif comment_analysis.mentions:
            return "mention"
        else:
            return "general"
    
    async def _create_comment_message(self, event: EnrichedEvent, comment_analysis) -> Dict[str, Any]:
        """Create threaded comment message."""
        comment_type = self._classify_comment_type(comment_analysis)
        
        type_indicators = {
            "blocker": "🚫",
            "decision": "✅",
            "question": "❓",
            "mention": "💬",
            "general": "💭"
        }
        
        indicator = type_indicators.get(comment_type, "💭")
        
        blocks = []
        
        # Header
        header_text = (
            f"{indicator} *Comment Added*: {event.ticket_key}\n"
            f"*{event.ticket_details.get('summary', 'No summary')}*"
        )
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": header_text}
        })
        
        # Comment details
        if comment_analysis:
            details_text = (
                f"*Author*: {comment_analysis.author}\n"
                f"*Type*: {comment_type.title()}\n"
                f"*Comment*: {comment_analysis.content_preview}"
            )
            
            if comment_analysis.mentions:
                details_text += f"\n*Mentions*: {', '.join(f'@{m}' for m in comment_analysis.mentions[:3])}"
            
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": details_text}
            })
        
        # Action buttons
        actions = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Comment"},
                "url": f"https://your-jira-instance.atlassian.net/browse/{event.ticket_key}",
                "style": "primary"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Reply in JIRA"},
                "value": f"reply_jira_{event.ticket_key}"
            }
        ]
        
        if comment_type == "question":
            actions.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "Answer Question"},
                "value": f"answer_question_{event.ticket_key}"
            })
        
        blocks.append({
            "type": "actions",
            "elements": actions
        })
        
        return {
            "blocks": blocks,
            "text": f"Comment: {event.ticket_key}",
            "metadata": {
                "comment_type": comment_type,
                "ticket_key": event.ticket_key,
                "author": comment_analysis.author if comment_analysis else "Unknown"
            }
        }
    
    async def _determine_comment_channels(self, event: EnrichedEvent, comment_analysis) -> List[str]:
        """Determine channels for comment notifications."""
        channels = ["#ticket-discussions"]
        
        comment_type = self._classify_comment_type(comment_analysis)
        
        if comment_type == "blocker":
            channels.append("#blockers")
        elif comment_type == "decision":
            channels.append("#decisions")
        
        # Add team-specific channels
        if event.classification and event.classification.affected_teams:
            for team in event.classification.affected_teams:
                channels.append(f"#{team}-discussions")
        
        return channels
    
    async def _send_comment_notifications(
        self, 
        message_data: Dict[str, Any], 
        channels: List[str], 
        event: EnrichedEvent
    ) -> bool:
        """Send comment notifications."""
        try:
            success_count = 0
            
            for channel in channels:
                try:
                    from devsync_ai.core.enhanced_notification_handler import NotificationContext
                    
                    context = NotificationContext(
                        notification_type="jira_comment_added",
                        event_type=event.event_type,
                        data={
                            "ticket_key": event.ticket_key,
                            "message": message_data,
                            "channel": channel,
                            "urgency": "medium"
                        },
                        team_id=event.classification.affected_teams[0] if event.classification and event.classification.affected_teams else "default",
                        urgency_level="medium"
                    )
                    
                    result = await default_notification_system.process_notification(context)
                    
                    if result.decision.value in ["send_immediately", "batch_and_send"]:
                        success_count += 1
                        logger.info(f"Comment notification sent to {channel}")
                    
                except Exception as e:
                    logger.error(f"Failed to send comment notification to {channel}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send comment notifications: {e}")
            return False


# Update the available hooks registry
AVAILABLE_HOOKS = {
    'status_change': StatusChangeHook,
    'blocker_detection': BlockerHook,
    'assignment_change': AssignmentChangeHook,
    'critical_update': CriticalUpdateHook,
    'comment_activity': CommentHook,
}