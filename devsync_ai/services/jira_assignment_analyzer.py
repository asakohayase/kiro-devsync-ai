"""
JIRA Assignment Change Analyzer - Comprehensive Workload Management

This module provides intelligent analysis of JIRA assignment changes with:
- Assignment data parsing from webhook payloads
- Workload impact analysis and capacity tracking
- Contextual notification generation
- Targeted Slack notifications with actionable information
- Integration with existing services and notification systems
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from devsync_ai.services.jira import JiraService, DateRange
from devsync_ai.services.slack import SlackService
from devsync_ai.analytics.workload_analytics_engine import WorkloadAnalyticsEngine, WorkloadStatus
from devsync_ai.core.notification_integration import default_notification_system
from devsync_ai.templates.jira_templates import JiraAssignmentTemplate


logger = logging.getLogger(__name__)


class AssignmentChangeType(Enum):
    """Types of assignment changes detected."""
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
class AssignmentData:
    """Structured assignment change data parsed from webhook."""
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
    jira_url: Optional[str] = None


@dataclass
class WorkloadImpact:
    """Workload impact analysis for an assignee."""
    assignee: str
    current_ticket_count: int
    current_story_points: int
    high_priority_count: int
    overdue_count: int
    capacity_utilization: float
    risk_level: WorkloadRiskLevel
    recommendations: List[str]
    conflicts: List[str]
    workload_trend: str


@dataclass
class NotificationContext:
    """Context for generating targeted notifications."""
    assignment_data: AssignmentData
    workload_impacts: Dict[str, WorkloadImpact]
    team_channel: Optional[str]
    project_manager: Optional[str]
    urgency_level: str


class JiraAssignmentAnalyzer:
    """
    Comprehensive JIRA assignment change analyzer with intelligent workload management.
    
    Features:
    - Parse assignment data from JIRA webhook payloads
    - Analyze workload impact and capacity utilization
    - Generate contextual notifications based on scenarios
    - Send targeted Slack notifications with actionable information
    - Integrate with existing notification and analytics systems
    """
    
    def __init__(self):
        """Initialize the JIRA assignment analyzer."""
        self.jira_service = JiraService()
        self.slack_service = SlackService()
        self.workload_engine = WorkloadAnalyticsEngine()
        self.template = JiraAssignmentTemplate()
        
    async def analyze_assignment_change(self, webhook_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a JIRA assignment change from webhook payload.
        
        Args:
            webhook_payload: Raw JIRA webhook payload
            
        Returns:
            Analysis results with notification status
        """
        try:
            logger.info("🎯 Analyzing JIRA assignment change")
            
            # 1. Parse assignment data
            assignment_data = await self._parse_assignment_data(webhook_payload)
            if not assignment_data:
                return {"success": False, "error": "Failed to parse assignment data"}
            
            logger.info(f"📋 Assignment change: {assignment_data.change_type.value} for {assignment_data.ticket_key}")
            
            # 2. Analyze workload impact
            workload_impacts = await self._analyze_workload_impact(assignment_data)
            
            # 3. Generate contextual notifications
            notification_context = await self._build_notification_context(
                assignment_data, workload_impacts
            )
            
            # 4. Send targeted notifications
            notification_results = await self._send_targeted_notifications(notification_context)
            
            # 5. Store analytics data
            await self._store_assignment_analytics(assignment_data, workload_impacts)
            
            return {
                "success": True,
                "assignment_change": assignment_data.change_type.value,
                "ticket_key": assignment_data.ticket_key,
                "notifications_sent": len([r for r in notification_results if r.get("success")]),
                "workload_risks": [impact.risk_level.value for impact in workload_impacts.values()],
                "recommendations": self._aggregate_recommendations(workload_impacts)
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing assignment change: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _parse_assignment_data(self, payload: Dict[str, Any]) -> Optional[AssignmentData]:
        """
        Parse JIRA webhook payload to extract assignment change data.
        
        Args:
            payload: JIRA webhook payload
            
        Returns:
            Structured assignment data or None if parsing fails
        """
        try:
            # Extract issue data
            issue_data = payload.get("issue", {})
            if not issue_data:
                logger.warning("No issue data found in webhook payload")
                return None
            
            fields = issue_data.get("fields", {})
            
            # Basic ticket information
            ticket_key = issue_data.get("key", "")
            title = fields.get("summary", "")
            priority = fields.get("priority", {}).get("name", "Medium")
            status = fields.get("status", {}).get("name", "Unknown")
            story_points = fields.get("customfield_10016")  # Common story points field
            reporter = fields.get("reporter", {}).get("displayName", "Unknown")
            project_key = ticket_key.split("-")[0] if ticket_key else ""
            issue_type = fields.get("issuetype", {}).get("name", "Task")
            
            # Extract assignee information from changelog
            previous_assignee = None
            new_assignee = None
            
            # Current assignee
            current_assignee_data = fields.get("assignee")
            if current_assignee_data:
                new_assignee = (current_assignee_data.get("displayName") or 
                              current_assignee_data.get("name"))
            
            # Previous assignee from changelog
            changelog = payload.get("changelog", {})
            if "items" in changelog:
                for item in changelog["items"]:
                    if item.get("field") == "assignee":
                        previous_assignee = item.get("fromString")
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
            
            labels = []
            if fields.get("labels"):
                labels = [label.get("name", str(label)) for label in fields["labels"]]
            
            components = []
            if fields.get("components"):
                components = [comp.get("name", str(comp)) for comp in fields["components"]]
            
            # Extract sprint information
            sprint = self._extract_sprint_name(fields)
            
            # Build JIRA URL
            jira_url = f"{self.jira_service.server_url}/browse/{ticket_key}" if ticket_key else None
            
            return AssignmentData(
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
                labels=labels or [],
                components=components or [],
                jira_url=jira_url
            )
            
        except Exception as e:
            logger.error(f"❌ Error parsing assignment data: {e}", exc_info=True)
            return None
    
    def _determine_change_type(self, previous: Optional[str], new: Optional[str]) -> AssignmentChangeType:
        """Determine the type of assignment change."""
        if not previous and new:
            return AssignmentChangeType.NEW_ASSIGNMENT
        elif previous and not new:
            return AssignmentChangeType.UNASSIGNMENT
        elif previous and new and previous != new:
            return AssignmentChangeType.REASSIGNMENT
        elif previous == new:
            return AssignmentChangeType.SELF_ASSIGNMENT
        else:
            return AssignmentChangeType.NEW_ASSIGNMENT
    
    def _extract_sprint_name(self, fields: Dict[str, Any]) -> Optional[str]:
        """Extract sprint name from JIRA fields."""
        try:
            # Try common sprint field names
            sprint_fields = ["customfield_10020", "customfield_10010", "sprint"]
            
            for field_name in sprint_fields:
                sprint_data = fields.get(field_name)
                if sprint_data:
                    if isinstance(sprint_data, list) and sprint_data:
                        sprint_obj = sprint_data[-1]  # Most recent sprint
                        if isinstance(sprint_obj, dict):
                            return sprint_obj.get("name")
                        elif isinstance(sprint_obj, str):
                            # Parse sprint string format
                            import re
                            match = re.search(r'name=([^,\]]+)', sprint_obj)
                            if match:
                                return match.group(1)
                    elif isinstance(sprint_data, dict):
                        return sprint_data.get("name")
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not extract sprint name: {e}")
            return None
    
    async def _analyze_workload_impact(self, assignment_data: AssignmentData) -> Dict[str, WorkloadImpact]:
        """
        Analyze workload impact for affected assignees.
        
        Args:
            assignment_data: Assignment change data
            
        Returns:
            Dictionary mapping assignee names to workload impacts
        """
        impacts = {}
        
        try:
            # Analyze new assignee workload
            if assignment_data.new_assignee:
                impact = await self._analyze_assignee_workload(
                    assignment_data.new_assignee, assignment_data
                )
                if impact:
                    impacts[assignment_data.new_assignee] = impact
            
            # Analyze previous assignee workload (for context)
            if (assignment_data.previous_assignee and 
                assignment_data.previous_assignee != assignment_data.new_assignee):
                impact = await self._analyze_assignee_workload(
                    assignment_data.previous_assignee, assignment_data, is_previous=True
                )
                if impact:
                    impacts[assignment_data.previous_assignee] = impact
            
        except Exception as e:
            logger.error(f"❌ Error analyzing workload impact: {e}")
        
        return impacts
    
    async def _analyze_assignee_workload(
        self, 
        assignee: str, 
        assignment_data: AssignmentData,
        is_previous: bool = False
    ) -> Optional[WorkloadImpact]:
        """
        Analyze workload for a specific assignee.
        
        Args:
            assignee: Assignee name
            assignment_data: Assignment change data
            is_previous: Whether this is the previous assignee
            
        Returns:
            Workload impact analysis
        """
        try:
            # Get current tickets for assignee
            current_tickets = await self._get_assignee_tickets(assignee)
            
            # Calculate workload metrics
            ticket_count = len(current_tickets)
            story_points = sum(getattr(ticket, 'story_points', 0) or 0 for ticket in current_tickets)
            high_priority_count = sum(
                1 for ticket in current_tickets 
                if getattr(ticket, 'priority', '') in ["Highest", "High", "Critical"]
            )
            
            # Count overdue tickets
            now = datetime.utcnow()
            overdue_count = 0
            for ticket in current_tickets:
                if hasattr(ticket, 'due_date') and ticket.due_date and ticket.due_date < now:
                    overdue_count += 1
            
            # Calculate capacity utilization (simplified)
            base_capacity = 8  # Assume 8 tickets as base capacity
            capacity_utilization = ticket_count / base_capacity
            
            # Adjust for new assignment
            if not is_previous and assignment_data.new_assignee == assignee:
                ticket_count += 1
                story_points += assignment_data.story_points or 0
                capacity_utilization = ticket_count / base_capacity
                
                if assignment_data.priority in ["Highest", "High", "Critical"]:
                    high_priority_count += 1
            
            # Determine risk level
            risk_level = self._calculate_workload_risk(
                ticket_count, story_points, high_priority_count, 
                overdue_count, capacity_utilization
            )
            
            # Generate recommendations
            recommendations = self._generate_workload_recommendations(
                assignee, ticket_count, story_points, high_priority_count,
                overdue_count, capacity_utilization, risk_level
            )
            
            # Identify conflicts
            conflicts = await self._identify_workload_conflicts(
                assignee, assignment_data, current_tickets
            )
            
            # Determine workload trend (simplified)
            workload_trend = "stable"  # Would be calculated from historical data
            
            return WorkloadImpact(
                assignee=assignee,
                current_ticket_count=ticket_count,
                current_story_points=story_points,
                high_priority_count=high_priority_count,
                overdue_count=overdue_count,
                capacity_utilization=capacity_utilization,
                risk_level=risk_level,
                recommendations=recommendations,
                conflicts=conflicts,
                workload_trend=workload_trend
            )
            
        except Exception as e:
            logger.error(f"❌ Error analyzing workload for {assignee}: {e}")
            return None
    
    async def _get_assignee_tickets(self, assignee: str) -> List[Any]:
        """Get current active tickets for an assignee."""
        try:
            return await self.jira_service.get_active_tickets(assignee=assignee)
        except Exception as e:
            logger.warning(f"Could not get tickets for {assignee}: {e}")
            return []
    
    def _calculate_workload_risk(
        self,
        ticket_count: int,
        story_points: int,
        high_priority_count: int,
        overdue_count: int,
        capacity_utilization: float
    ) -> WorkloadRiskLevel:
        """Calculate workload risk level based on various factors."""
        risk_score = 0
        
        # Ticket count risk
        if ticket_count > 12:
            risk_score += 3
        elif ticket_count > 8:
            risk_score += 2
        elif ticket_count > 6:
            risk_score += 1
        
        # Story points risk
        if story_points > 30:
            risk_score += 3
        elif story_points > 20:
            risk_score += 2
        elif story_points > 15:
            risk_score += 1
        
        # High priority risk
        if high_priority_count > 4:
            risk_score += 3
        elif high_priority_count > 2:
            risk_score += 2
        elif high_priority_count > 1:
            risk_score += 1
        
        # Overdue risk
        if overdue_count > 2:
            risk_score += 4
        elif overdue_count > 0:
            risk_score += 2
        
        # Capacity utilization risk
        if capacity_utilization > 1.5:
            risk_score += 4
        elif capacity_utilization > 1.2:
            risk_score += 2
        elif capacity_utilization > 1.0:
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 8:
            return WorkloadRiskLevel.CRITICAL
        elif risk_score >= 5:
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
        capacity_utilization: float,
        risk_level: WorkloadRiskLevel
    ) -> List[str]:
        """Generate workload management recommendations."""
        recommendations = []
        
        if risk_level == WorkloadRiskLevel.CRITICAL:
            recommendations.append("🚨 CRITICAL: Immediate workload redistribution needed")
            recommendations.append("Consider reassigning lower-priority tickets")
            recommendations.append("Schedule urgent discussion with team lead")
        
        elif risk_level == WorkloadRiskLevel.HIGH:
            recommendations.append("⚠️ HIGH RISK: Monitor workload closely")
            recommendations.append("Consider deferring non-critical tasks")
        
        if overdue_count > 0:
            recommendations.append(f"📅 {overdue_count} overdue tickets need immediate attention")
        
        if high_priority_count > 2:
            recommendations.append(f"🔥 {high_priority_count} high-priority tickets - review prioritization")
        
        if capacity_utilization > 1.2:
            recommendations.append(f"📊 Over-capacity ({capacity_utilization:.1%}) - review commitments")
        
        if ticket_count > 8:
            recommendations.append("📋 High ticket count - consider breaking down large tasks")
        
        return recommendations
    
    async def _identify_workload_conflicts(
        self,
        assignee: str,
        assignment_data: AssignmentData,
        current_tickets: List[Any]
    ) -> List[str]:
        """Identify potential workload conflicts."""
        conflicts = []
        
        try:
            # Check for conflicting priorities
            if assignment_data.priority in ["Highest", "High", "Critical"]:
                high_priority_tickets = [
                    ticket for ticket in current_tickets
                    if getattr(ticket, 'priority', '') in ["Highest", "High", "Critical"]
                ]
                if len(high_priority_tickets) > 1:
                    conflicts.append("Multiple high-priority tickets competing for attention")
            
            # Check for sprint conflicts
            if assignment_data.sprint:
                sprint_tickets = [
                    ticket for ticket in current_tickets
                    if getattr(ticket, 'sprint', '') == assignment_data.sprint
                ]
                total_sprint_points = sum(
                    getattr(ticket, 'story_points', 0) or 0 for ticket in sprint_tickets
                )
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
            logger.error(f"❌ Error identifying conflicts: {e}")
        
        return conflicts
    
    async def _build_notification_context(
        self,
        assignment_data: AssignmentData,
        workload_impacts: Dict[str, WorkloadImpact]
    ) -> NotificationContext:
        """Build context for generating notifications."""
        try:
            # Determine team channel
            team_channel = await self._get_team_channel(assignment_data.project_key)
            
            # Determine project manager
            project_manager = await self._get_project_manager(assignment_data.project_key)
            
            # Determine urgency level
            urgency_level = "low"
            if assignment_data.new_assignee:
                impact = workload_impacts.get(assignment_data.new_assignee)
                if impact:
                    if impact.risk_level == WorkloadRiskLevel.CRITICAL:
                        urgency_level = "critical"
                    elif impact.risk_level == WorkloadRiskLevel.HIGH:
                        urgency_level = "high"
                    elif impact.risk_level == WorkloadRiskLevel.MODERATE:
                        urgency_level = "medium"
            
            return NotificationContext(
                assignment_data=assignment_data,
                workload_impacts=workload_impacts,
                team_channel=team_channel,
                project_manager=project_manager,
                urgency_level=urgency_level
            )
            
        except Exception as e:
            logger.error(f"❌ Error building notification context: {e}")
            return NotificationContext(
                assignment_data=assignment_data,
                workload_impacts=workload_impacts,
                team_channel=None,
                project_manager=None,
                urgency_level="low"
            )
    
    async def _get_team_channel(self, project_key: str) -> Optional[str]:
        """Get team channel for a project."""
        # This would typically look up team configuration
        # For now, return a default pattern
        return f"#{project_key.lower()}-team"
    
    async def _get_project_manager(self, project_key: str) -> Optional[str]:
        """Get project manager for a project."""
        # This would typically look up team configuration
        # For now, return None (no PM notification)
        return None
    
    async def _send_targeted_notifications(self, context: NotificationContext) -> List[Dict[str, Any]]:
        """
        Send targeted Slack notifications based on assignment scenario.
        
        Args:
            context: Notification context with assignment and workload data
            
        Returns:
            List of notification results
        """
        results = []
        assignment = context.assignment_data
        
        try:
            # 1. New assignee notification
            if assignment.new_assignee:
                result = await self._send_assignee_notification(context, assignment.new_assignee)
                results.append(result)
            
            # 2. Previous assignee notification (for handoff context)
            if (assignment.previous_assignee and 
                assignment.change_type == AssignmentChangeType.REASSIGNMENT):
                result = await self._send_handoff_notification(context, assignment.previous_assignee)
                results.append(result)
            
            # 3. Team channel notification
            if context.team_channel:
                result = await self._send_team_notification(context)
                results.append(result)
            
            # 4. Project manager notification for workload concerns
            if (context.project_manager and context.urgency_level in ["high", "critical"]):
                result = await self._send_pm_notification(context)
                results.append(result)
            
            # 5. Unassignment notification
            if assignment.change_type == AssignmentChangeType.UNASSIGNMENT:
                result = await self._send_unassignment_notification(context)
                results.append(result)
            
        except Exception as e:
            logger.error(f"❌ Error sending notifications: {e}")
            results.append({"success": False, "error": str(e)})
        
        return results
    
    async def _send_assignee_notification(self, context: NotificationContext, assignee: str) -> Dict[str, Any]:
        """Send notification to new assignee."""
        try:
            assignment = context.assignment_data
            impact = context.workload_impacts.get(assignee)
            
            # Generate message based on scenario
            if assignment.change_type == AssignmentChangeType.NEW_ASSIGNMENT:
                emoji = "🎯"
                action = "assigned"
            else:
                emoji = "🔄"
                action = "reassigned"
            
            # Build message
            message_parts = [
                f"{emoji} @{assignee} you've been {action} **{assignment.ticket_key}**: {assignment.title}"
            ]
            
            # Add priority and status info
            if assignment.priority != "Medium":
                message_parts.append(f"Priority: **{assignment.priority}**")
            
            if assignment.status:
                message_parts.append(f"Status: {assignment.status}")
            
            # Add effort estimate
            if assignment.story_points:
                message_parts.append(f"Effort: {assignment.story_points} story points")
            
            # Add sprint info
            if assignment.sprint:
                message_parts.append(f"Sprint: {assignment.sprint}")
            
            # Add due date
            if assignment.due_date:
                due_str = assignment.due_date.strftime("%Y-%m-%d")
                message_parts.append(f"Due: {due_str}")
            
            # Add workload warning if needed
            if impact and impact.risk_level in [WorkloadRiskLevel.HIGH, WorkloadRiskLevel.CRITICAL]:
                message_parts.append(f"\n⚠️ **Workload Alert**: You now have {impact.current_ticket_count} active tickets")
                if impact.recommendations:
                    message_parts.append("Recommendations:")
                    for rec in impact.recommendations[:2]:  # Limit to top 2
                        message_parts.append(f"• {rec}")
            
            # Add JIRA link
            if assignment.jira_url:
                message_parts.append(f"\n🔗 [View in JIRA]({assignment.jira_url})")
            
            message = "\n".join(message_parts)
            
            # Send via Slack
            result = await self.slack_service.send_message(
                channel=f"@{assignee}",  # Direct message
                text=message
            )
            
            return {"success": result.get("ok", False), "target": assignee, "type": "assignee"}
            
        except Exception as e:
            logger.error(f"❌ Error sending assignee notification: {e}")
            return {"success": False, "error": str(e), "target": assignee}
    
    async def _send_handoff_notification(self, context: NotificationContext, previous_assignee: str) -> Dict[str, Any]:
        """Send handoff notification to previous assignee."""
        try:
            assignment = context.assignment_data
            
            message = (
                f"🔄 **{assignment.ticket_key}** has been reassigned from you to @{assignment.new_assignee}\n"
                f"Title: {assignment.title}\n"
                f"Please coordinate any handoff details if needed."
            )
            
            if assignment.jira_url:
                message += f"\n🔗 [View in JIRA]({assignment.jira_url})"
            
            result = await self.slack_service.send_message(
                channel=f"@{previous_assignee}",
                text=message
            )
            
            return {"success": result.get("ok", False), "target": previous_assignee, "type": "handoff"}
            
        except Exception as e:
            logger.error(f"❌ Error sending handoff notification: {e}")
            return {"success": False, "error": str(e), "target": previous_assignee}
    
    async def _send_team_notification(self, context: NotificationContext) -> Dict[str, Any]:
        """Send team visibility notification."""
        try:
            assignment = context.assignment_data
            
            # Generate team message
            if assignment.change_type == AssignmentChangeType.NEW_ASSIGNMENT:
                message = f"📋 **{assignment.ticket_key}** assigned to @{assignment.new_assignee}"
            elif assignment.change_type == AssignmentChangeType.REASSIGNMENT:
                message = f"🔄 **{assignment.ticket_key}** reassigned from @{assignment.previous_assignee} to @{assignment.new_assignee}"
            elif assignment.change_type == AssignmentChangeType.UNASSIGNMENT:
                message = f"❓ **{assignment.ticket_key}** is now unassigned and needs an owner"
            else:
                message = f"📋 **{assignment.ticket_key}** assignment updated"
            
            message += f"\nTitle: {assignment.title}"
            
            if assignment.priority != "Medium":
                message += f"\nPriority: **{assignment.priority}**"
            
            # Add workload warning for team visibility
            if assignment.new_assignee:
                impact = context.workload_impacts.get(assignment.new_assignee)
                if impact and impact.risk_level == WorkloadRiskLevel.CRITICAL:
                    message += f"\n🚨 **Critical Workload**: @{assignment.new_assignee} now has {impact.current_ticket_count} active tickets"
                elif impact and impact.risk_level == WorkloadRiskLevel.HIGH:
                    message += f"\n⚠️ **High Workload**: @{assignment.new_assignee} now has {impact.current_ticket_count} active tickets"
            
            if assignment.jira_url:
                message += f"\n🔗 [View in JIRA]({assignment.jira_url})"
            
            # Determine mention type based on urgency
            mention_channel = context.urgency_level == "critical"
            
            result = await self.slack_service.send_message(
                channel=context.team_channel,
                text=f"<!channel> {message}" if mention_channel else message
            )
            
            return {"success": result.get("ok", False), "target": context.team_channel, "type": "team"}
            
        except Exception as e:
            logger.error(f"❌ Error sending team notification: {e}")
            return {"success": False, "error": str(e), "target": context.team_channel}
    
    async def _send_pm_notification(self, context: NotificationContext) -> Dict[str, Any]:
        """Send project manager notification for workload concerns."""
        try:
            assignment = context.assignment_data
            impact = context.workload_impacts.get(assignment.new_assignee)
            
            message = (
                f"🚨 **Workload Concern**: {assignment.ticket_key} assignment\n"
                f"Assignee: @{assignment.new_assignee}\n"
                f"Current workload: {impact.current_ticket_count} tickets, {impact.current_story_points} story points\n"
                f"Risk level: **{impact.risk_level.value.upper()}**\n"
            )
            
            if impact.recommendations:
                message += "\nRecommendations:\n"
                for rec in impact.recommendations[:3]:
                    message += f"• {rec}\n"
            
            if assignment.jira_url:
                message += f"\n🔗 [View in JIRA]({assignment.jira_url})"
            
            result = await self.slack_service.send_message(
                channel=f"@{context.project_manager}",
                text=message
            )
            
            return {"success": result.get("ok", False), "target": context.project_manager, "type": "pm"}
            
        except Exception as e:
            logger.error(f"❌ Error sending PM notification: {e}")
            return {"success": False, "error": str(e), "target": context.project_manager}
    
    async def _send_unassignment_notification(self, context: NotificationContext) -> Dict[str, Any]:
        """Send unassignment notification to team."""
        try:
            assignment = context.assignment_data
            
            message = (
                f"❓ **{assignment.ticket_key}** is now unassigned and needs an owner\n"
                f"Title: {assignment.title}\n"
                f"Priority: **{assignment.priority}**\n"
                f"Who can take this ticket?"
            )
            
            if assignment.jira_url:
                message += f"\n🔗 [View in JIRA]({assignment.jira_url})"
            
            result = await self.slack_service.send_message(
                channel=context.team_channel or "#general",
                text=message
            )
            
            return {"success": result.get("ok", False), "target": context.team_channel, "type": "unassignment"}
            
        except Exception as e:
            logger.error(f"❌ Error sending unassignment notification: {e}")
            return {"success": False, "error": str(e)}
    
    async def _store_assignment_analytics(
        self, 
        assignment_data: AssignmentData, 
        workload_impacts: Dict[str, WorkloadImpact]
    ) -> None:
        """Store assignment analytics data."""
        try:
            # This would store analytics data for reporting and trend analysis
            # For now, just log the key metrics
            logger.info(f"📊 Assignment analytics: {assignment_data.ticket_key}")
            logger.info(f"   Change type: {assignment_data.change_type.value}")
            logger.info(f"   Workload risks: {[impact.risk_level.value for impact in workload_impacts.values()]}")
            
        except Exception as e:
            logger.error(f"❌ Error storing assignment analytics: {e}")
    
    def _aggregate_recommendations(self, workload_impacts: Dict[str, WorkloadImpact]) -> List[str]:
        """Aggregate recommendations from all workload impacts."""
        all_recommendations = []
        for impact in workload_impacts.values():
            all_recommendations.extend(impact.recommendations)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in all_recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations[:5]  # Return top 5 recommendations