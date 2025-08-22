"""
JIRA Slack Agent Hooks - Implementation Examples

This module provides comprehensive examples of custom hook implementations
and common use cases for the JIRA Slack Agent Hooks system.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from devsync_ai.core.agent_hooks import AgentHook, EnrichedEvent, HookExecutionResult
from devsync_ai.core.event_classification_engine import EventCategory, UrgencyLevel
from devsync_ai.core.hook_notification_integration import HookNotificationIntegration
from devsync_ai.services.slack import SlackService
from devsync_ai.services.jira import JiraService


# =============================================================================
# Basic Hook Implementation Examples
# =============================================================================

class SimpleStatusChangeHook(AgentHook):
    """
    Simple example of a status change hook that sends basic notifications.
    
    This hook demonstrates:
    - Basic hook structure
    - Event filtering
    - Simple message formatting
    - Error handling
    """
    
    def __init__(self, team_id: str = "default"):
        super().__init__(
            hook_id=f"simple_status_change_{team_id}",
            hook_type="status_change",
            team_id=team_id
        )
        self.notification_integration = HookNotificationIntegration()
    
    def should_execute(self, event: EnrichedEvent) -> bool:
        """Determine if this hook should execute for the given event."""
        # Only execute for status change events
        if event.classification.category != EventCategory.STATUS_CHANGE:
            return False
        
        # Only execute for medium priority and above
        if event.classification.urgency == UrgencyLevel.LOW:
            return False
        
        # Check if ticket has required fields
        ticket = event.ticket_details
        if not ticket or not hasattr(ticket, 'status'):
            return False
        
        return True
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """Execute the hook logic."""
        try:
            # Extract event data
            ticket = event.ticket_details
            old_status = event.jira_event_data.get('changelog', {}).get('items', [{}])[0].get('fromString')
            new_status = ticket.status
            
            # Create notification message
            message = self._format_status_change_message(ticket, old_status, new_status)
            
            # Send notification
            notification_result = await self.notification_integration.send_notification(
                team_id=self.team_id,
                channel="#dev-updates",
                message=message,
                urgency=event.classification.urgency
            )
            
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id=f"exec_{datetime.now().isoformat()}",
                success=True,
                execution_time_ms=50,
                notification_sent=notification_result.success,
                notification_result=notification_result,
                errors=[],
                metadata={
                    "ticket_key": ticket.key,
                    "status_change": f"{old_status} -> {new_status}"
                }
            )
            
        except Exception as e:
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id=f"exec_{datetime.now().isoformat()}",
                success=False,
                execution_time_ms=0,
                notification_sent=False,
                errors=[str(e)],
                metadata={"error_type": type(e).__name__}
            )
    
    def _format_status_change_message(self, ticket, old_status: str, new_status: str) -> Dict[str, Any]:
        """Format a simple status change message."""
        return {
            "text": f"📋 Ticket {ticket.key} status changed: {old_status} → {new_status}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{ticket.key}*: {ticket.summary}\n"
                               f"Status: {old_status} → *{new_status}*\n"
                               f"Assignee: {getattr(ticket, 'assignee', 'Unassigned')}"
                    }
                }
            ]
        }


class AdvancedAssignmentHook(AgentHook):
    """
    Advanced assignment hook with workload analysis and smart routing.
    
    This hook demonstrates:
    - Complex business logic
    - Integration with external services
    - Workload analysis
    - Conditional notifications
    - Rich message formatting
    """
    
    def __init__(self, team_id: str, max_tickets_per_assignee: int = 5):
        super().__init__(
            hook_id=f"advanced_assignment_{team_id}",
            hook_type="assignment",
            team_id=team_id
        )
        self.max_tickets_per_assignee = max_tickets_per_assignee
        self.notification_integration = HookNotificationIntegration()
        self.jira_service = JiraService()
    
    def should_execute(self, event: EnrichedEvent) -> bool:
        """Execute for assignment events only."""
        return event.classification.category == EventCategory.ASSIGNMENT
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """Execute advanced assignment logic."""
        start_time = datetime.now()
        
        try:
            ticket = event.ticket_details
            assignee = getattr(ticket, 'assignee', None)
            
            if not assignee:
                return self._create_success_result(start_time, "No assignee found")
            
            # Analyze assignee workload
            workload_analysis = await self._analyze_assignee_workload(assignee)
            
            # Determine notification urgency based on workload
            urgency = self._determine_urgency(workload_analysis, ticket)
            
            # Create rich notification message
            message = await self._format_assignment_message(
                ticket, assignee, workload_analysis
            )
            
            # Determine notification channels based on urgency
            channels = self._get_notification_channels(urgency)
            
            # Send notifications to all relevant channels
            notification_results = []
            for channel in channels:
                result = await self.notification_integration.send_notification(
                    team_id=self.team_id,
                    channel=channel,
                    message=message,
                    urgency=urgency
                )
                notification_results.append(result)
            
            # Check if escalation is needed
            if workload_analysis['overloaded'] and urgency == UrgencyLevel.HIGH:
                await self._send_escalation_notification(ticket, assignee, workload_analysis)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id=f"exec_{datetime.now().isoformat()}",
                success=True,
                execution_time_ms=execution_time,
                notification_sent=any(r.success for r in notification_results),
                notification_result=notification_results[0] if notification_results else None,
                errors=[],
                metadata={
                    "ticket_key": ticket.key,
                    "assignee": assignee,
                    "workload_analysis": workload_analysis,
                    "channels_notified": len(channels),
                    "escalation_sent": workload_analysis['overloaded']
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id=f"exec_{datetime.now().isoformat()}",
                success=False,
                execution_time_ms=execution_time,
                notification_sent=False,
                errors=[str(e)],
                metadata={"error_type": type(e).__name__}
            )
    
    async def _analyze_assignee_workload(self, assignee: str) -> Dict[str, Any]:
        """Analyze the current workload of an assignee."""
        try:
            # Get current tickets assigned to user
            current_tickets = await self.jira_service.get_user_assigned_tickets(
                assignee=assignee,
                status_categories=["To Do", "In Progress"]
            )
            
            # Calculate workload metrics
            total_tickets = len(current_tickets)
            high_priority_tickets = len([t for t in current_tickets if t.priority in ["High", "Critical"]])
            overdue_tickets = len([t for t in current_tickets if self._is_overdue(t)])
            
            # Determine if overloaded
            overloaded = (
                total_tickets > self.max_tickets_per_assignee or
                high_priority_tickets > 3 or
                overdue_tickets > 1
            )
            
            return {
                "total_tickets": total_tickets,
                "high_priority_tickets": high_priority_tickets,
                "overdue_tickets": overdue_tickets,
                "overloaded": overloaded,
                "capacity_percentage": min(100, (total_tickets / self.max_tickets_per_assignee) * 100)
            }
            
        except Exception as e:
            # Return default analysis if service call fails
            return {
                "total_tickets": 0,
                "high_priority_tickets": 0,
                "overdue_tickets": 0,
                "overloaded": False,
                "capacity_percentage": 0,
                "error": str(e)
            }
    
    def _is_overdue(self, ticket) -> bool:
        """Check if a ticket is overdue."""
        if not hasattr(ticket, 'due_date') or not ticket.due_date:
            return False
        
        due_date = datetime.fromisoformat(ticket.due_date.replace('Z', '+00:00'))
        return due_date < datetime.now(due_date.tzinfo)
    
    def _determine_urgency(self, workload_analysis: Dict[str, Any], ticket) -> UrgencyLevel:
        """Determine notification urgency based on workload and ticket priority."""
        if workload_analysis['overloaded']:
            return UrgencyLevel.HIGH
        
        if hasattr(ticket, 'priority') and ticket.priority in ["High", "Critical"]:
            return UrgencyLevel.MEDIUM
        
        return UrgencyLevel.LOW
    
    def _get_notification_channels(self, urgency: UrgencyLevel) -> List[str]:
        """Get notification channels based on urgency."""
        channels = ["#team-assignments"]
        
        if urgency == UrgencyLevel.HIGH:
            channels.extend(["#team-leads", "#workload-alerts"])
        elif urgency == UrgencyLevel.MEDIUM:
            channels.append("#priority-assignments")
        
        return channels
    
    async def _format_assignment_message(
        self, 
        ticket, 
        assignee: str, 
        workload_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format rich assignment notification message."""
        # Determine emoji based on workload
        workload_emoji = "🔴" if workload_analysis['overloaded'] else "🟡" if workload_analysis['capacity_percentage'] > 75 else "🟢"
        
        # Create workload summary
        workload_text = (
            f"Current workload: {workload_analysis['total_tickets']} tickets "
            f"({workload_analysis['capacity_percentage']:.0f}% capacity)"
        )
        
        if workload_analysis['high_priority_tickets'] > 0:
            workload_text += f"\n• {workload_analysis['high_priority_tickets']} high priority tickets"
        
        if workload_analysis['overdue_tickets'] > 0:
            workload_text += f"\n• {workload_analysis['overdue_tickets']} overdue tickets"
        
        return {
            "text": f"👤 Ticket {ticket.key} assigned to {assignee}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"👤 New Assignment: {ticket.key}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Ticket:* {ticket.key}\n*Summary:* {ticket.summary}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Assignee:* {assignee}\n*Priority:* {getattr(ticket, 'priority', 'Medium')}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{workload_emoji} *Workload Analysis*\n{workload_text}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Ticket"
                            },
                            "url": f"https://jira.company.com/browse/{ticket.key}"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Assignee Workload"
                            },
                            "url": f"https://jira.company.com/issues/?jql=assignee={assignee}+AND+status+in+(\"To Do\",\"In Progress\")"
                        }
                    ]
                }
            ]
        }
    
    async def _send_escalation_notification(
        self, 
        ticket, 
        assignee: str, 
        workload_analysis: Dict[str, Any]
    ):
        """Send escalation notification for overloaded assignee."""
        escalation_message = {
            "text": f"⚠️ Workload Alert: {assignee} is overloaded",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"⚠️ *Workload Alert*\n"
                               f"{assignee} has been assigned {ticket.key} but is currently overloaded:\n"
                               f"• {workload_analysis['total_tickets']} active tickets\n"
                               f"• {workload_analysis['high_priority_tickets']} high priority\n"
                               f"• {workload_analysis['overdue_tickets']} overdue\n\n"
                               f"Consider redistributing workload or providing additional support."
                    }
                }
            ]
        }
        
        await self.notification_integration.send_notification(
            team_id=self.team_id,
            channel="#team-leads",
            message=escalation_message,
            urgency=UrgencyLevel.HIGH
        )
    
    def _create_success_result(self, start_time: datetime, message: str) -> HookExecutionResult:
        """Create a successful execution result."""
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        return HookExecutionResult(
            hook_id=self.hook_id,
            execution_id=f"exec_{datetime.now().isoformat()}",
            success=True,
            execution_time_ms=execution_time,
            notification_sent=False,
            errors=[],
            metadata={"message": message}
        )


# =============================================================================
# Specialized Hook Examples
# =============================================================================

class CriticalBugAlertHook(AgentHook):
    """
    Specialized hook for critical bug alerts with immediate escalation.
    
    This hook demonstrates:
    - Event filtering based on multiple criteria
    - Immediate escalation logic
    - Integration with external alerting systems
    - Rich contextual information
    """
    
    def __init__(self, team_id: str):
        super().__init__(
            hook_id=f"critical_bug_alert_{team_id}",
            hook_type="critical_bug",
            team_id=team_id
        )
        self.notification_integration = HookNotificationIntegration()
    
    def should_execute(self, event: EnrichedEvent) -> bool:
        """Execute only for critical bugs."""
        ticket = event.ticket_details
        
        # Check if it's a bug
        if not hasattr(ticket, 'issue_type') or ticket.issue_type.lower() != 'bug':
            return False
        
        # Check if it's critical priority
        if not hasattr(ticket, 'priority') or ticket.priority != 'Critical':
            return False
        
        # Check for production impact labels
        production_labels = ['production', 'prod-impact', 'customer-impact']
        if hasattr(ticket, 'labels'):
            ticket_labels = [label.lower() for label in ticket.labels]
            if not any(label in ticket_labels for label in production_labels):
                return False
        
        return True
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """Execute critical bug alert logic."""
        start_time = datetime.now()
        
        try:
            ticket = event.ticket_details
            
            # Create immediate alert message
            alert_message = await self._format_critical_bug_alert(ticket, event)
            
            # Send to multiple channels immediately
            channels = ["#critical-bugs", "#on-call", "#product-team", "#engineering-leads"]
            notification_results = []
            
            for channel in channels:
                result = await self.notification_integration.send_notification(
                    team_id=self.team_id,
                    channel=channel,
                    message=alert_message,
                    urgency=UrgencyLevel.CRITICAL
                )
                notification_results.append(result)
            
            # Trigger external alerting (PagerDuty, etc.)
            await self._trigger_external_alerts(ticket)
            
            # Schedule follow-up reminders
            await self._schedule_followup_reminders(ticket)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id=f"exec_{datetime.now().isoformat()}",
                success=True,
                execution_time_ms=execution_time,
                notification_sent=any(r.success for r in notification_results),
                notification_result=notification_results[0] if notification_results else None,
                errors=[],
                metadata={
                    "ticket_key": ticket.key,
                    "channels_alerted": len(channels),
                    "external_alerts_sent": True,
                    "followup_scheduled": True
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id=f"exec_{datetime.now().isoformat()}",
                success=False,
                execution_time_ms=execution_time,
                notification_sent=False,
                errors=[str(e)],
                metadata={"error_type": type(e).__name__}
            )
    
    async def _format_critical_bug_alert(self, ticket, event: EnrichedEvent) -> Dict[str, Any]:
        """Format critical bug alert message."""
        # Extract additional context
        reporter = getattr(ticket, 'reporter', 'Unknown')
        assignee = getattr(ticket, 'assignee', 'Unassigned')
        created = getattr(ticket, 'created', datetime.now().isoformat())
        
        # Determine customer impact
        customer_impact = self._assess_customer_impact(ticket)
        
        return {
            "text": f"🚨 CRITICAL BUG ALERT: {ticket.key}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 CRITICAL BUG ALERT"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Ticket:* {ticket.key}\n*Priority:* Critical"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Reporter:* {reporter}\n*Assignee:* {assignee}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Summary:* {ticket.summary}\n\n"
                               f"*Customer Impact:* {customer_impact}\n"
                               f"*Created:* {created}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⚡ *Immediate Actions Required:*\n"
                               "• Assign to on-call engineer\n"
                               "• Assess production impact\n"
                               "• Create incident if needed\n"
                               "• Update stakeholders"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Ticket"
                            },
                            "url": f"https://jira.company.com/browse/{ticket.key}",
                            "style": "danger"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Create Incident"
                            },
                            "url": f"https://incident.company.com/create?ticket={ticket.key}"
                        }
                    ]
                }
            ]
        }
    
    def _assess_customer_impact(self, ticket) -> str:
        """Assess customer impact based on ticket information."""
        if hasattr(ticket, 'labels'):
            labels = [label.lower() for label in ticket.labels]
            
            if 'customer-facing' in labels or 'ui-bug' in labels:
                return "High - Customer-facing issue"
            elif 'api-bug' in labels or 'integration' in labels:
                return "Medium - API/Integration issue"
            elif 'internal-tool' in labels:
                return "Low - Internal tool issue"
        
        return "Unknown - Needs assessment"
    
    async def _trigger_external_alerts(self, ticket):
        """Trigger external alerting systems."""
        # This would integrate with PagerDuty, Datadog, etc.
        # Implementation depends on your alerting infrastructure
        pass
    
    async def _schedule_followup_reminders(self, ticket):
        """Schedule follow-up reminders for critical bug."""
        # This would schedule reminders at 30 min, 1 hour, 2 hours, etc.
        # Implementation depends on your scheduling system
        pass


class DeploymentNotificationHook(AgentHook):
    """
    Hook for deployment-related notifications with environment-specific logic.
    
    This hook demonstrates:
    - Environment-specific processing
    - Integration with deployment systems
    - Conditional notification logic
    - Rich deployment information
    """
    
    def __init__(self, team_id: str):
        super().__init__(
            hook_id=f"deployment_notification_{team_id}",
            hook_type="deployment",
            team_id=team_id
        )
        self.notification_integration = HookNotificationIntegration()
    
    def should_execute(self, event: EnrichedEvent) -> bool:
        """Execute for deployment-related status changes."""
        ticket = event.ticket_details
        
        # Check for deployment-related status
        deployment_statuses = [
            'Ready for Deployment',
            'Deployed to Staging',
            'Deployed to Production',
            'Deployment Failed'
        ]
        
        if not hasattr(ticket, 'status') or ticket.status not in deployment_statuses:
            return False
        
        # Check for deployment labels
        if hasattr(ticket, 'labels'):
            deployment_labels = ['deployment', 'release', 'hotfix']
            ticket_labels = [label.lower() for label in ticket.labels]
            if not any(label in ticket_labels for label in deployment_labels):
                return False
        
        return True
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """Execute deployment notification logic."""
        start_time = datetime.now()
        
        try:
            ticket = event.ticket_details
            status = ticket.status
            
            # Determine deployment environment and type
            deployment_info = self._analyze_deployment(ticket, event)
            
            # Create environment-specific message
            message = await self._format_deployment_message(ticket, deployment_info)
            
            # Determine notification channels based on environment
            channels = self._get_deployment_channels(deployment_info['environment'])
            
            # Send notifications
            notification_results = []
            for channel in channels:
                result = await self.notification_integration.send_notification(
                    team_id=self.team_id,
                    channel=channel,
                    message=message,
                    urgency=deployment_info['urgency']
                )
                notification_results.append(result)
            
            # Handle special cases
            if deployment_info['environment'] == 'production':
                await self._handle_production_deployment(ticket, deployment_info)
            
            if deployment_info['failed']:
                await self._handle_deployment_failure(ticket, deployment_info)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id=f"exec_{datetime.now().isoformat()}",
                success=True,
                execution_time_ms=execution_time,
                notification_sent=any(r.success for r in notification_results),
                notification_result=notification_results[0] if notification_results else None,
                errors=[],
                metadata={
                    "ticket_key": ticket.key,
                    "deployment_info": deployment_info,
                    "channels_notified": len(channels)
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id=f"exec_{datetime.now().isoformat()}",
                success=False,
                execution_time_ms=execution_time,
                notification_sent=False,
                errors=[str(e)],
                metadata={"error_type": type(e).__name__}
            )
    
    def _analyze_deployment(self, ticket, event: EnrichedEvent) -> Dict[str, Any]:
        """Analyze deployment information from ticket and event."""
        status = ticket.status
        
        # Determine environment
        environment = 'unknown'
        if 'staging' in status.lower():
            environment = 'staging'
        elif 'production' in status.lower():
            environment = 'production'
        elif 'ready for deployment' in status.lower():
            environment = 'pending'
        
        # Determine if deployment failed
        failed = 'failed' in status.lower()
        
        # Determine deployment type
        deployment_type = 'regular'
        if hasattr(ticket, 'labels'):
            labels = [label.lower() for label in ticket.labels]
            if 'hotfix' in labels:
                deployment_type = 'hotfix'
            elif 'rollback' in labels:
                deployment_type = 'rollback'
            elif 'emergency' in labels:
                deployment_type = 'emergency'
        
        # Determine urgency
        urgency = UrgencyLevel.LOW
        if failed or deployment_type in ['hotfix', 'emergency']:
            urgency = UrgencyLevel.HIGH
        elif environment == 'production':
            urgency = UrgencyLevel.MEDIUM
        
        return {
            'environment': environment,
            'failed': failed,
            'deployment_type': deployment_type,
            'urgency': urgency,
            'status': status
        }
    
    def _get_deployment_channels(self, environment: str) -> List[str]:
        """Get notification channels based on deployment environment."""
        base_channels = ["#deployments"]
        
        if environment == 'production':
            base_channels.extend(["#production-deployments", "#stakeholder-updates"])
        elif environment == 'staging':
            base_channels.append("#staging-deployments")
        
        return base_channels
    
    async def _format_deployment_message(self, ticket, deployment_info: Dict[str, Any]) -> Dict[str, Any]:
        """Format deployment notification message."""
        # Determine emoji based on deployment status
        if deployment_info['failed']:
            emoji = "❌"
            color = "danger"
        elif deployment_info['environment'] == 'production':
            emoji = "🚀"
            color = "good"
        else:
            emoji = "📦"
            color = "warning"
        
        # Create deployment summary
        summary = f"{emoji} {deployment_info['deployment_type'].title()} deployment"
        if deployment_info['failed']:
            summary += " failed"
        else:
            summary += f" to {deployment_info['environment']}"
        
        return {
            "text": f"{summary}: {ticket.key}",
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Ticket:* {ticket.key}\n*Type:* {deployment_info['deployment_type'].title()}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Environment:* {deployment_info['environment'].title()}\n*Status:* {deployment_info['status']}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Summary:* {ticket.summary}"
                            }
                        }
                    ]
                }
            ]
        }
    
    async def _handle_production_deployment(self, ticket, deployment_info: Dict[str, Any]):
        """Handle special logic for production deployments."""
        # Send additional notifications to stakeholders
        stakeholder_message = {
            "text": f"🚀 Production deployment completed: {ticket.key}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Production deployment of {ticket.key} has been completed successfully.\n\n"
                               f"*Summary:* {ticket.summary}\n"
                               f"*Deployed by:* {getattr(ticket, 'assignee', 'Unknown')}\n"
                               f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    }
                }
            ]
        }
        
        await self.notification_integration.send_notification(
            team_id=self.team_id,
            channel="#stakeholder-updates",
            message=stakeholder_message,
            urgency=UrgencyLevel.MEDIUM
        )
    
    async def _handle_deployment_failure(self, ticket, deployment_info: Dict[str, Any]):
        """Handle deployment failure notifications."""
        failure_message = {
            "text": f"❌ Deployment failed: {ticket.key}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"⚠️ *Deployment Failure Alert*\n\n"
                               f"Deployment of {ticket.key} to {deployment_info['environment']} has failed.\n\n"
                               f"*Immediate actions required:*\n"
                               f"• Check deployment logs\n"
                               f"• Assess impact on {deployment_info['environment']}\n"
                               f"• Consider rollback if necessary\n"
                               f"• Update stakeholders"
                    }
                }
            ]
        }
        
        await self.notification_integration.send_notification(
            team_id=self.team_id,
            channel="#deployment-failures",
            message=failure_message,
            urgency=UrgencyLevel.HIGH
        )


# =============================================================================
# Usage Examples and Testing
# =============================================================================

async def example_usage():
    """
    Example usage of the custom hooks.
    
    This demonstrates how to:
    - Instantiate hooks
    - Create test events
    - Execute hooks
    - Handle results
    """
    
    # Create hook instances
    simple_hook = SimpleStatusChangeHook(team_id="engineering")
    advanced_hook = AdvancedAssignmentHook(team_id="engineering", max_tickets_per_assignee=5)
    bug_hook = CriticalBugAlertHook(team_id="engineering")
    deployment_hook = DeploymentNotificationHook(team_id="devops")
    
    # Create a test event (this would normally come from JIRA webhook)
    test_event = EnrichedEvent(
        event_id="test_123",
        event_type="jira:issue_updated",
        timestamp=datetime.now(),
        jira_event_data={
            "changelog": {
                "items": [
                    {
                        "field": "status",
                        "fromString": "In Progress",
                        "toString": "Done"
                    }
                ]
            }
        },
        ticket_key="PROJ-123",
        project_key="PROJ",
        raw_payload={},
        ticket_details=type('Ticket', (), {
            'key': 'PROJ-123',
            'summary': 'Fix critical bug in user authentication',
            'status': 'Done',
            'priority': 'High',
            'assignee': 'john.doe@company.com',
            'issue_type': 'Bug',
            'labels': ['backend', 'security']
        })(),
        stakeholders=[],
        classification=type('Classification', (), {
            'category': EventCategory.STATUS_CHANGE,
            'urgency': UrgencyLevel.MEDIUM,
            'significance': 'MODERATE',
            'affected_teams': ['engineering']
        })(),
        context_data={}
    )
    
    # Test simple hook
    if simple_hook.should_execute(test_event):
        result = await simple_hook.execute(test_event)
        print(f"Simple hook result: {result.success}, notifications sent: {result.notification_sent}")
    
    # Test advanced hook (modify event for assignment)
    test_event.classification.category = EventCategory.ASSIGNMENT
    if advanced_hook.should_execute(test_event):
        result = await advanced_hook.execute(test_event)
        print(f"Advanced hook result: {result.success}, metadata: {result.metadata}")
    
    # Test critical bug hook (modify event for critical bug)
    test_event.ticket_details.issue_type = 'Bug'
    test_event.ticket_details.priority = 'Critical'
    test_event.ticket_details.labels = ['production', 'customer-impact']
    
    if bug_hook.should_execute(test_event):
        result = await bug_hook.execute(test_event)
        print(f"Bug hook result: {result.success}, channels alerted: {result.metadata.get('channels_alerted', 0)}")


def create_test_hook_suite() -> List[AgentHook]:
    """
    Create a suite of test hooks for different scenarios.
    
    Returns:
        List of configured hook instances for testing
    """
    return [
        SimpleStatusChangeHook(team_id="test"),
        AdvancedAssignmentHook(team_id="test", max_tickets_per_assignee=3),
        CriticalBugAlertHook(team_id="test"),
        DeploymentNotificationHook(team_id="test")
    ]


if __name__ == "__main__":
    # Run example usage
    asyncio.run(example_usage())