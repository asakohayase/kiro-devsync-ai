"""
JIRA Assignment Change Hook - Intelligent Workload Management and Notifications

This hook detects JIRA assignment changes and provides intelligent workload analysis,
contextual notifications, and proactive workload balancing recommendations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from devsync_ai.core.agent_hooks import AgentHook, EnrichedEvent, HookExecutionResult
from devsync_ai.core.event_classification_engine import EventCategory, UrgencyLevel, SignificanceLevel
from devsync_ai.analytics.workload_analytics_engine import WorkloadAnalyticsEngine
from devsync_ai.services.jira import JiraService
from devsync_ai.services.slack import SlackService
from devsync_ai.templates.jira_templates import JiraAssignmentTemplate
from devsync_ai.core.hook_notification_integration import HookNotificationIntegration


logger = logging.getLogger(__name__)


class AssignmentChangeType(Enum):
    """Types of assignment changes."""
    NEW_ASSIGNMENT = "new_assignment"
    REASSIGNMENT = "reassignment"
    UNASSIGNMENT = "unassignment"
    SELF_ASSIGNMENT = "self_assignment"


class WorkloadRiskLevel(Enum):
    """Workload risk assessment levels."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AssignmentChangeData:
    """Structured data for assignment changes."""
    ticket_key: str
    title: str
    previous_assignee: Optional[str]
    new_assignee: Optional[str]
    priority: str
    status: str
    story_points: Optional[int]
    sprint: Optional[str]
    reporter: str
    timestamp: datetime
    change_type: AssignmentChangeType
    project_key: str
    issue_type: str
    due_date: Optional[datetime] = None
    labels: List[str] = None
    components: List[str] = None


@dataclass
class WorkloadAnalysis:
    """Workload impact analysis results."""
    assignee: str
    current_ticket_count: int
    current_story_points: int
    high_priority_count: int
    overdue_count: int
    sprint_capacity_utilization: float
    risk_level: WorkloadRiskLevel
    recommendations: List[str]
    conflicts: List[str]
    workload_trend: str  # "increasing", "stable", "decreasing"


@dataclass
class NotificationTarget:
    """Target for notifications."""
    user_id: str
    channel: str
    mention_type: str  # "direct", "channel", "here"
    urgency: UrgencyLevel
    context: Dict[str, Any]


class JiraAssignmentHook(AgentHook):
    """
    Intelligent JIRA assignment change hook with workload analysis and notifications.
    
    Features:
    - Parses JIRA assignment webhook payloads
    - Analyzes workload impact and capacity
    - Generates contextual notifications
    - Provides workload balancing recommendations
    - Sends targeted Slack notifications
    """
    
    def __init__(self):
        """Initialize the JIRA assignment hook."""
        super().__init__()
        self.jira_service = None
        self.slack_service = None
        self.workload_engine = None
        self.notification_integration = None
        self.template = JiraAssignmentTemplate()
        
    async def initialize(self):
        """Initialize services and dependencies."""
        try:
            self.jira_service = JiraService()
            self.slack_service = SlackService()
            self.workload_engine = WorkloadAnalyticsEngine()
            self.notification_integration = HookNotificationIntegration()
            
            logger.info("✅ JIRA Assignment Hook initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize JIRA Assignment Hook: {e}")
            raise
    
    def should_execute(self, event: EnrichedEvent) -> bool:
        """
        Determine if this hook should execute for the given event.
        
        Args:
            event: The enriched event to evaluate
            
        Returns:
            True if the hook should execute
        """
        # Check if this is a JIRA assignment change event
        if not event.source == "jira":
            return False
            
        # Check for assignment-related events
        assignment_indicators = [
            "assignee",
            "assigned",
            "assignment",
            "owner",
            "responsible"
        ]
        
        event_data = event.data or {}
        
        # Check if assignee field changed in the webhook
        if "changelog" in event_data:
            changelog = event_data["changelog"]
            if "items" in changelog:
                for item in changelog["items"]:
                    if item.get("field") == "assignee":
                        return True
        
        # Check event type and category
        if (event.event_type in ["jira:issue_updated", "jira:issue_assigned"] or
            event.category == EventCategory.ASSIGNMENT):
            return True
            
        # Check for assignment keywords in event description
        event_text = str(event_data).lower()
        return any(indicator in event_text for indicator in assignment_indicators)
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """
        Execute the assignment change analysis and notifications.
        
        Args:
            event: The enriched event containing assignment change data
            
        Returns:
            Hook execution result with status and details
        """
        try:
            logger.info(f"🎯 Processing JIRA assignment change: {event.event_id}")
            
            # Ensure services are initialized
            if not self.jira_service:
                await self.initialize()
            
            # Parse assignment change data
            assignment_data = await self._parse_assignment_change(event)
            if not assignment_data:
                return HookExecutionResult(
                    success=False,
                    message="Failed to parse assignment change data",
                    execution_time=0.0
                )
            
            logger.info(f"📋 Assignment change: {assignment_data.change_type.value} for {assignment_data.ticket_key}")
            
            # Analyze workload impact
            workload_analyses = await self._analyze_workload_impact(assignment_data)
            
            # Generate notification targets
            notification_targets = await self._determine_notification_targets(
                assignment_data, workload_analyses
            )
            
            # Send notifications
            notification_results = await self._send_notifications(
                assignment_data, workload_analyses, notification_targets
            )
            
            # Store analytics data
            await self._store_assignment_analytics(assignment_data, workload_analyses)
            
            success_count = sum(1 for result in notification_results if result.get("success"))
            total_count = len(notification_results)
            
            return HookExecutionResult(
                success=True,
                message=f"Assignment change processed: {success_count}/{total_count} notifications sent",
                execution_time=0.0,
                metadata={
                    "assignment_change": assignment_data.change_type.value,
                    "ticket_key": assignment_data.ticket_key,
                    "notifications_sent": success_count,
                    "workload_risks": [analysis.risk_level.value for analysis in workload_analyses.values()]
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Error executing JIRA assignment hook: {e}", exc_info=True)
            return HookExecutionResult(
                success=False,
                message=f"Assignment hook execution failed: {str(e)}",
                execution_time=0.0
            )
    
    async def _parse_assignment_change(self, event: EnrichedEvent) -> Optional[AssignmentChangeData]:
        """
        Parse JIRA webhook payload to extract assignment change data.
        
        Args:
            event: The enriched event containing webhook data
            
        Returns:
            Structured assignment change data or None if parsing fails
        """
        try:
            event_data = event.data or {}
            
            # Extract issue data
            issue_data = event_data.get("issue", {})
            if not issue_data:
                logger.warning("No issue data found in webhook payload")
                return None
            
            fields = issue_data.get("fields", {})
            
            # Extract basic ticket information
            ticket_key = issue_data.get("key")
            title = fields.get("summary", "")
            priority = fields.get("priority", {}).get("name", "Medium")
            status = fields.get("status", {}).get("name", "Unknown")
            story_points = fields.get("customfield_10016")  # Common story points field
            reporter = fields.get("reporter", {}).get("displayName", "Unknown")
            project_key = issue_data.get("key", "").split("-")[0] if issue_data.get("key") else ""
            issue_type = fields.get("issuetype", {}).get("name", "Task")
            
            # Extract assignee information from changelog
            previous_assignee = None
            new_assignee = None
            
            # Current assignee
            current_assignee_data = fields.get("assignee")
            if current_assignee_data:
                new_assignee = current_assignee_data.get("displayName") or current_assignee_data.get("name")
            
            # Previous assignee from changelog
            changelog = event_data.get("changelog", {})
            if "items" in changelog:
                for item in changelog["items"]:
                    if item.get("field") == "assignee":
                        previous_assignee = item.get("fromString")
                        # If new_assignee is None, get it from changelog
                        if not new_assignee:
                            new_assignee = item.get("toString")
                        break
            
            # Determine change type
            change_type = self._determine_change_type(previous_assignee, new_assignee)
            
            # Extract additional fields
            due_date = None
            if fields.get("duedate"):
                try:
                    due_date = datetime.fromisoformat(fields["duedate"].replace("Z", "+00:00"))
                except:
                    pass
            
            labels = [label["name"] for label in fields.get("labels", [])]
            components = [comp["name"] for comp in fields.get("components", [])]
            
            # Extract sprint information
            sprint = None
            sprint_field = fields.get("customfield_10020")  # Common sprint field
            if sprint_field and isinstance(sprint_field, list) and sprint_field:
                sprint_data = sprint_field[0]
                if isinstance(sprint_data, dict):
                    sprint = sprint_data.get("name")
                elif isinstance(sprint_data, str):
                    # Parse sprint string format
                    import re
                    match = re.search(r'name=([^,\]]+)', sprint_data)
                    if match:
                        sprint = match.group(1)
            
            return AssignmentChangeData(
                ticket_key=ticket_key,
                title=title,
                previous_assignee=previous_assignee,
                new_assignee=new_assignee,
                priority=priority,
                status=status,
                story_points=story_points,
                sprint=sprint,
                reporter=reporter,
                timestamp=datetime.utcnow(),
                change_type=change_type,
                project_key=project_key,
                issue_type=issue_type,
                due_date=due_date,
                labels=labels,
                components=components
            )
            
        except Exception as e:
            logger.error(f"❌ Error parsing assignment change: {e}", exc_info=True)
            return None
    
    def _determine_change_type(self, previous_assignee: Optional[str], new_assignee: Optional[str]) -> AssignmentChangeType:
        """
        Determine the type of assignment change.
        
        Args:
            previous_assignee: Previous assignee name
            new_assignee: New assignee name
            
        Returns:
            Assignment change type
        """
        if not previous_assignee and new_assignee:
            return AssignmentChangeType.NEW_ASSIGNMENT
        elif previous_assignee and not new_assignee:
            return AssignmentChangeType.UNASSIGNMENT
        elif previous_assignee and new_assignee and previous_assignee != new_assignee:
            return AssignmentChangeType.REASSIGNMENT
        elif previous_assignee == new_assignee:
            return AssignmentChangeType.SELF_ASSIGNMENT
        else:
            return AssignmentChangeType.NEW_ASSIGNMENT
    
    async def _analyze_workload_impact(self, assignment_data: AssignmentChangeData) -> Dict[str, WorkloadAnalysis]:
        """
        Analyze workload impact for affected assignees.
        
        Args:
            assignment_data: Assignment change data
            
        Returns:
            Dictionary mapping assignee names to workload analyses
        """
        analyses = {}
        
        try:
            # Analyze workload for new assignee
            if assignment_data.new_assignee:
                analysis = await self._analyze_assignee_workload(
                    assignment_data.new_assignee, assignment_data
                )
                if analysis:
                    analyses[assignment_data.new_assignee] = analysis
            
            # Analyze workload for previous assignee (for context)
            if (assignment_data.previous_assignee and 
                assignment_data.previous_assignee != assignment_data.new_assignee):
                analysis = await self._analyze_assignee_workload(
                    assignment_data.previous_assignee, assignment_data, is_previous=True
                )
                if analysis:
                    analyses[assignment_data.previous_assignee] = analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing workload impact: {e}")
        
        return analyses
    
    async def _analyze_assignee_workload(
        self, 
        assignee: str, 
        assignment_data: AssignmentChangeData,
        is_previous: bool = False
    ) -> Optional[WorkloadAnalysis]:
        """
        Analyze workload for a specific assignee.
        
        Args:
            assignee: Assignee name
            assignment_data: Assignment change data
            is_previous: Whether this is the previous assignee
            
        Returns:
            Workload analysis or None if analysis fails
        """
        try:
            # Get current tickets for assignee
            current_tickets = await self.jira_service.get_assignee_tickets(assignee)
            
            # Calculate workload metrics
            ticket_count = len(current_tickets)
            story_points = sum(ticket.story_points or 0 for ticket in current_tickets)
            high_priority_count = sum(
                1 for ticket in current_tickets 
                if ticket.priority in ["Highest", "High", "Critical"]
            )
            
            # Count overdue tickets
            now = datetime.utcnow()
            overdue_count = 0
            for ticket in current_tickets:
                if hasattr(ticket, 'due_date') and ticket.due_date and ticket.due_date < now:
                    overdue_count += 1
            
            # Calculate sprint capacity utilization
            sprint_capacity_utilization = 0.0
            if assignment_data.sprint:
                try:
                    sprint_capacity = await self.workload_engine.get_sprint_capacity(
                        assignee, assignment_data.sprint
                    )
                    if sprint_capacity and sprint_capacity.total_capacity > 0:
                        sprint_capacity_utilization = (
                            sprint_capacity.allocated_points / sprint_capacity.total_capacity
                        )
                except Exception as e:
                    logger.warning(f"Could not calculate sprint capacity for {assignee}: {e}")
            
            # Determine risk level
            risk_level = self._calculate_workload_risk(
                ticket_count, story_points, high_priority_count, 
                overdue_count, sprint_capacity_utilization
            )
            
            # Generate recommendations
            recommendations = self._generate_workload_recommendations(
                assignee, ticket_count, story_points, high_priority_count,
                overdue_count, sprint_capacity_utilization, risk_level
            )
            
            # Identify conflicts
            conflicts = await self._identify_workload_conflicts(
                assignee, assignment_data, current_tickets
            )
            
            # Determine workload trend
            workload_trend = await self._calculate_workload_trend(assignee)
            
            return WorkloadAnalysis(
                assignee=assignee,
                current_ticket_count=ticket_count,
                current_story_points=story_points,
                high_priority_count=high_priority_count,
                overdue_count=overdue_count,
                sprint_capacity_utilization=sprint_capacity_utilization,
                risk_level=risk_level,
                recommendations=recommendations,
                conflicts=conflicts,
                workload_trend=workload_trend
            )
            
        except Exception as e:
            logger.error(f"❌ Error analyzing workload for {assignee}: {e}")
            return None
    
    def _calculate_workload_risk(
        self,
        ticket_count: int,
        story_points: int,
        high_priority_count: int,
        overdue_count: int,
        sprint_capacity_utilization: float
    ) -> WorkloadRiskLevel:
        """
        Calculate workload risk level based on various factors.
        
        Args:
            ticket_count: Number of assigned tickets
            story_points: Total story points
            high_priority_count: Number of high-priority tickets
            overdue_count: Number of overdue tickets
            sprint_capacity_utilization: Sprint capacity utilization percentage
            
        Returns:
            Workload risk level
        """
        risk_score = 0
        
        # Ticket count risk
        if ticket_count > 15:
            risk_score += 3
        elif ticket_count > 10:
            risk_score += 2
        elif ticket_count > 7:
            risk_score += 1
        
        # Story points risk
        if story_points > 40:
            risk_score += 3
        elif story_points > 25:
            risk_score += 2
        elif story_points > 15:
            risk_score += 1
        
        # High priority risk
        if high_priority_count > 5:
            risk_score += 3
        elif high_priority_count > 3:
            risk_score += 2
        elif high_priority_count > 1:
            risk_score += 1
        
        # Overdue risk
        if overdue_count > 3:
            risk_score += 4
        elif overdue_count > 1:
            risk_score += 2
        elif overdue_count > 0:
            risk_score += 1
        
        # Sprint capacity risk
        if sprint_capacity_utilization > 1.2:
            risk_score += 4
        elif sprint_capacity_utilization > 1.0:
            risk_score += 2
        elif sprint_capacity_utilization > 0.9:
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 10:
            return WorkloadRiskLevel.CRITICAL
        elif risk_score >= 6:
            return WorkloadRiskLevel.HIGH
        elif risk_score >= 3:
            return WorkloadRiskLevel.MODERATE
        else:
            return WorkloadRiskLevel.LOW
    
    def _generate_workload_recommendations(
        self,
        assignee: str,
        ticket_count: int,
        story_points: int,
        high_priority_count: int,
        overdue_count: int,
        sprint_capacity_utilization: float,
        risk_level: WorkloadRiskLevel
    ) -> List[str]:
        """
        Generate workload management recommendations.
        
        Args:
            assignee: Assignee name
            ticket_count: Number of assigned tickets
            story_points: Total story points
            high_priority_count: Number of high-priority tickets
            overdue_count: Number of overdue tickets
            sprint_capacity_utilization: Sprint capacity utilization
            risk_level: Calculated risk level
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if risk_level == WorkloadRiskLevel.CRITICAL:
            recommendations.append("🚨 CRITICAL: Immediate workload redistribution needed")
            recommendations.append("Consider reassigning lower-priority tickets to other team members")
            recommendations.append("Schedule urgent discussion with team lead about capacity")
        
        elif risk_level == WorkloadRiskLevel.HIGH:
            recommendations.append("⚠️ HIGH RISK: Monitor workload closely")
            recommendations.append("Consider deferring non-critical tasks to next sprint")
        
        if overdue_count > 0:
            recommendations.append(f"📅 {overdue_count} overdue tickets need immediate attention")
        
        if high_priority_count > 3:
            recommendations.append(f"🔥 {high_priority_count} high-priority tickets - consider prioritization review")
        
        if sprint_capacity_utilization > 1.0:
            recommendations.append(f"📊 Sprint over-capacity ({sprint_capacity_utilization:.1%}) - review commitments")
        
        if ticket_count > 10:
            recommendations.append("📋 High ticket count - consider breaking down large tasks")
        
        return recommendations
    
    async def _identify_workload_conflicts(
        self,
        assignee: str,
        assignment_data: AssignmentChangeData,
        current_tickets: List[Any]
    ) -> List[str]:
        """
        Identify potential workload conflicts.
        
        Args:
            assignee: Assignee name
            assignment_data: Assignment change data
            current_tickets: Current assigned tickets
            
        Returns:
            List of identified conflicts
        """
        conflicts = []
        
        try:
            # Check for conflicting priorities
            if assignment_data.priority in ["Highest", "High", "Critical"]:
                high_priority_tickets = [
                    ticket for ticket in current_tickets
                    if ticket.priority in ["Highest", "High", "Critical"]
                ]
                if len(high_priority_tickets) > 2:
                    conflicts.append(f"Multiple high-priority tickets competing for attention")
            
            # Check for sprint conflicts
            if assignment_data.sprint:
                sprint_tickets = [
                    ticket for ticket in current_tickets
                    if hasattr(ticket, 'sprint') and ticket.sprint == assignment_data.sprint
                ]
                total_sprint_points = sum(ticket.story_points or 0 for ticket in sprint_tickets)
                if assignment_data.story_points:
                    total_sprint_points += assignment_data.story_points
                
                if total_sprint_points > 20:  # Typical sprint capacity
                    conflicts.append(f"Sprint capacity may be exceeded ({total_sprint_points} points)")
            
            # Check for due date conflicts
            if assignment_data.due_date:
                conflicting_due_dates = [
                    ticket for ticket in current_tickets
                    if (hasattr(ticket, 'due_date') and ticket.due_date and
                        abs((ticket.due_date - assignment_data.due_date).days) <= 2)
                ]
                if conflicting_due_dates:
                    conflicts.append(f"Multiple tickets due around {assignment_data.due_date.strftime('%Y-%m-%d')}")
            
        except Exception as e:
            logger.error(f"❌ Error identifying workload conflicts: {e}")
        
        return conflicts
    
    async def _calculate_workload_trend(self, assignee: str) -> str:
        """
        Calculate workload trend for assignee.
        
        Args:
            assignee: Assignee name
            
        Returns:
            Workload trend: "increasing", "stable", or "decreasing"
        """
        try:
            # Get historical workload data (simplified implementation)
            # In a real implementation, this would query historical data
            return "stable"  # Default to stable
            
        except Exception as e:
            logger.error(f"❌ Error calculating workload trend for {assignee}: {e}")
            return "unknown"
    
    async def _determine_notification_targets(
        self,
        assignment_data: AssignmentChangeData,
        workload_analyses: Dict[str, WorkloadAnalysis]
    ) -> List[NotificationTarget]:
        """
        Determine who should receive notifications and how.
        
        Args:
            assignment_data: Assignment change data
            workload_analyses: Workload analysis results
            
        Returns:
            List of notification targets
        """
        targets = []
        
        try:
            # New assignee notification
            if assignment_data.new_assignee:
                urgency = UrgencyLevel.MEDIUM
                analysis = workload_analyses.get(assignment_data.new_assignee)
                
                if analysis and analysis.risk_level in [WorkloadRiskLevel.HIGH, WorkloadRiskLevel.CRITICAL]:
                    urgency = UrgencyLevel.HIGH
                
                targets.append(NotificationTarget(
                    user_id=assignment_data.new_assignee,
                    channel="direct",
                    mention_type="direct",
                    urgency=urgency,
                    context={
                        "type": "new_assignment",
                        "workload_analysis": analysis
                    }
                ))
            
            # Previous assignee notification (for handoff context)
            if (assignment_data.previous_assignee and 
                assignment_data.change_type == AssignmentChangeType.REASSIGNMENT):
                targets.append(NotificationTarget(
                    user_id=assignment_data.previous_assignee,
                    channel="direct",
                    mention_type="direct",
                    urgency=UrgencyLevel.LOW,
                    context={
                        "type": "handoff_notification",
                        "new_assignee": assignment_data.new_assignee
                    }
                ))
            
            # Team channel notification
            team_channel = await self._get_team_channel(assignment_data.project_key)
            if team_channel:
                urgency = UrgencyLevel.LOW
                
                # Increase urgency for high-risk assignments
                if assignment_data.new_assignee:
                    analysis = workload_analyses.get(assignment_data.new_assignee)
                    if analysis and analysis.risk_level == WorkloadRiskLevel.CRITICAL:
                        urgency = UrgencyLevel.HIGH
                
                targets.append(NotificationTarget(
                    user_id="team",
                    channel=team_channel,
                    mention_type="channel" if urgency == UrgencyLevel.HIGH else "none",
                    urgency=urgency,
                    context={
                        "type": "team_visibility",
                        "workload_analyses": workload_analyses
                    }
                ))
            
            # Project manager notification for workload concerns
            if assignment_data.new_assignee:
                analysis = workload_analyses.get(assignment_data.new_assignee)
                if analysis and analysis.risk_level in [WorkloadRiskLevel.HIGH, WorkloadRiskLevel.CRITICAL]:
                    pm_user = await self._get_project_manager(assignment_data.project_key)
                    if pm_user:
                        targets.append(NotificationTarget(
                            user_id=pm_user,
                            channel="direct",
                            mention_type="direct",
                            urgency=UrgencyLevel.HIGH,
                            context={
                                "type": "workload_concern",
                                "workload_analysis": analysis
                            }
                        ))
            
        except Exception as e:
            logger.error(f"❌ Error determining notification targets: {e}")
        
        return targets
    
    async def _get_team_channel(self, project_key: str) -> Optional[str]:
        """
        Get the team channel for a project.
        
        Args:
            project_key: JIRA project key
            
        Returns:
            Slack channel name or None
        """
        try:
            # This would typically look up team configuration
            # For now, use a simple mapping
            channel_mapping = {
                "ENG": "#engineering",
                "QA": "#qa-team",
                "PROD": "#product-team",
                "DEV": "#development"
            }
            return channel_mapping.get(project_key, "#general")
            
        except Exception as e:
            logger.error(f"❌ Error getting team channel for {project_key}: {e}")
            return None
    
    async def _get_project_manager(self, project_key: str) -> Optional[str]:
        """
        Get the project manager for a project.
        
        Args:
            project_key: JIRA project key
            
        Returns:
            Project manager username or None
        """
        try:
            # This would typically look up project configuration
            # For now, return None to skip PM notifications
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting project manager for {project_key}: {e}")
            return None
    
    async def _send_notifications(
        self,
        assignment_data: AssignmentChangeData,
        workload_analyses: Dict[str, WorkloadAnalysis],
        targets: List[NotificationTarget]
    ) -> List[Dict[str, Any]]:
        """
        Send notifications to all targets.
        
        Args:
            assignment_data: Assignment change data
            workload_analyses: Workload analysis results
            targets: Notification targets
            
        Returns:
            List of notification results
        """
        results = []
        
        for target in targets:
            try:
                # Generate message content
                message_content = await self._generate_notification_message(
                    assignment_data, workload_analyses, target
                )
                
                # Send notification
                if target.channel == "direct":
                    # Send direct message
                    result = await self.slack_service.send_message(
                        channel=f"@{target.user_id}",
                        **message_content
                    )
                else:
                    # Send to channel
                    result = await self.slack_service.send_message(
                        channel=target.channel,
                        **message_content
                    )
                
                results.append({
                    "target": target.user_id,
                    "channel": target.channel,
                    "success": result.get("ok", False),
                    "error": result.get("error")
                })
                
            except Exception as e:
                logger.error(f"❌ Error sending notification to {target.user_id}: {e}")
                results.append({
                    "target": target.user_id,
                    "channel": target.channel,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def _generate_notification_message(
        self,
        assignment_data: AssignmentChangeData,
        workload_analyses: Dict[str, WorkloadAnalysis],
        target: NotificationTarget
    ) -> Dict[str, Any]:
        """
        Generate notification message content.
        
        Args:
            assignment_data: Assignment change data
            workload_analyses: Workload analysis results
            target: Notification target
            
        Returns:
            Message content dictionary
        """
        try:
            context_type = target.context.get("type", "general")
            
            if context_type == "new_assignment":
                return await self._generate_new_assignment_message(
                    assignment_data, workload_analyses, target
                )
            elif context_type == "handoff_notification":
                return await self._generate_handoff_message(
                    assignment_data, target
                )
            elif context_type == "team_visibility":
                return await self._generate_team_message(
                    assignment_data, workload_analyses, target
                )
            elif context_type == "workload_concern":
                return await self._generate_workload_concern_message(
                    assignment_data, workload_analyses, target
                )
            else:
                return await self._generate_general_message(
                    assignment_data, workload_analyses, target
                )
                
        except Exception as e:
            logger.error(f"❌ Error generating notification message: {e}")
            return {
                "text": f"Assignment change for {assignment_data.ticket_key}: {assignment_data.title}",
                "blocks": []
            }
    
    async def _generate_new_assignment_message(
        self,
        assignment_data: AssignmentChangeData,
        workload_analyses: Dict[str, WorkloadAnalysis],
        target: NotificationTarget
    ) -> Dict[str, Any]:
        """Generate message for new assignment notification."""
        analysis = workload_analyses.get(assignment_data.new_assignee)
        
        # Determine emoji based on priority and workload risk
        emoji = "🎯"
        if assignment_data.priority in ["Highest", "Critical"]:
            emoji = "🚨"
        elif analysis and analysis.risk_level == WorkloadRiskLevel.HIGH:
            emoji = "⚠️"
        elif analysis and analysis.risk_level == WorkloadRiskLevel.CRITICAL:
            emoji = "🔴"
        
        # Build message text
        text = f"{emoji} <@{target.user_id}> you've been assigned {assignment_data.ticket_key}: {assignment_data.title}"
        
        # Build blocks for rich formatting
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Priority:* {assignment_data.priority}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:* {assignment_data.status}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Story Points:* {assignment_data.story_points or 'Not set'}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Sprint:* {assignment_data.sprint or 'Not assigned'}"
                    }
                ]
            }
        ]
        
        # Add workload analysis if available
        if analysis:
            workload_text = f"*Current Workload:* {analysis.current_ticket_count} tickets, {analysis.current_story_points} points"
            if analysis.risk_level != WorkloadRiskLevel.LOW:
                workload_text += f" ⚠️ *Risk Level:* {analysis.risk_level.value.upper()}"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": workload_text
                }
            })
            
            # Add recommendations if any
            if analysis.recommendations:
                rec_text = "*Recommendations:*\n" + "\n".join(f"• {rec}" for rec in analysis.recommendations[:3])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": rec_text
                    }
                })
        
        # Add action buttons
        jira_url = f"https://your-jira-instance.atlassian.net/browse/{assignment_data.ticket_key}"
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View in JIRA"
                    },
                    "url": jira_url,
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Workload"
                    },
                    "value": f"workload_{assignment_data.new_assignee}"
                }
            ]
        })
        
        return {
            "text": text,
            "blocks": blocks
        }
    
    async def _generate_handoff_message(
        self,
        assignment_data: AssignmentChangeData,
        target: NotificationTarget
    ) -> Dict[str, Any]:
        """Generate message for assignment handoff notification."""
        new_assignee = target.context.get("new_assignee")
        
        text = f"🔄 {assignment_data.ticket_key} has been reassigned from you to {new_assignee}"
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Ticket:* {assignment_data.title}\n*New Assignee:* {new_assignee}"
                }
            }
        ]
        
        return {
            "text": text,
            "blocks": blocks
        }
    
    async def _generate_team_message(
        self,
        assignment_data: AssignmentChangeData,
        workload_analyses: Dict[str, WorkloadAnalysis],
        target: NotificationTarget
    ) -> Dict[str, Any]:
        """Generate message for team visibility notification."""
        if assignment_data.change_type == AssignmentChangeType.NEW_ASSIGNMENT:
            text = f"🎯 {assignment_data.ticket_key} assigned to {assignment_data.new_assignee}"
        elif assignment_data.change_type == AssignmentChangeType.REASSIGNMENT:
            text = f"🔄 {assignment_data.ticket_key} reassigned from {assignment_data.previous_assignee} to {assignment_data.new_assignee}"
        elif assignment_data.change_type == AssignmentChangeType.UNASSIGNMENT:
            text = f"❓ {assignment_data.ticket_key} is now unassigned and needs an owner"
        else:
            text = f"📋 Assignment change for {assignment_data.ticket_key}"
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            }
        ]
        
        # Add workload warning if needed
        if assignment_data.new_assignee:
            analysis = workload_analyses.get(assignment_data.new_assignee)
            if analysis and analysis.risk_level in [WorkloadRiskLevel.HIGH, WorkloadRiskLevel.CRITICAL]:
                mention = "@channel" if target.mention_type == "channel" else ""
                warning_text = f"⚠️ {mention} {assignment_data.new_assignee} now has {analysis.current_ticket_count} tickets ({analysis.risk_level.value} workload)"
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": warning_text
                    }
                })
        
        return {
            "text": text,
            "blocks": blocks
        }
    
    async def _generate_workload_concern_message(
        self,
        assignment_data: AssignmentChangeData,
        workload_analyses: Dict[str, WorkloadAnalysis],
        target: NotificationTarget
    ) -> Dict[str, Any]:
        """Generate message for workload concern notification."""
        analysis = workload_analyses.get(assignment_data.new_assignee)
        
        text = f"🚨 Workload Alert: {assignment_data.new_assignee} may be overloaded"
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            }
        ]
        
        if analysis:
            workload_details = f"*Current Workload:*\n"
            workload_details += f"• {analysis.current_ticket_count} tickets\n"
            workload_details += f"• {analysis.current_story_points} story points\n"
            workload_details += f"• {analysis.high_priority_count} high-priority items\n"
            workload_details += f"• Risk Level: {analysis.risk_level.value.upper()}"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": workload_details
                }
            })
            
            if analysis.recommendations:
                rec_text = "*Recommendations:*\n" + "\n".join(f"• {rec}" for rec in analysis.recommendations)
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": rec_text
                    }
                })
        
        return {
            "text": text,
            "blocks": blocks
        }
    
    async def _generate_general_message(
        self,
        assignment_data: AssignmentChangeData,
        workload_analyses: Dict[str, WorkloadAnalysis],
        target: NotificationTarget
    ) -> Dict[str, Any]:
        """Generate general assignment change message."""
        text = f"📋 Assignment change for {assignment_data.ticket_key}: {assignment_data.title}"
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            }
        ]
        
        return {
            "text": text,
            "blocks": blocks
        }
    
    async def _store_assignment_analytics(
        self,
        assignment_data: AssignmentChangeData,
        workload_analyses: Dict[str, WorkloadAnalysis]
    ) -> None:
        """
        Store assignment change analytics data.
        
        Args:
            assignment_data: Assignment change data
            workload_analyses: Workload analysis results
        """
        try:
            # This would store analytics data for reporting and insights
            # Implementation would depend on your analytics system
            logger.info(f"📊 Stored assignment analytics for {assignment_data.ticket_key}")
            
        except Exception as e:
            logger.error(f"❌ Error storing assignment analytics: {e}")