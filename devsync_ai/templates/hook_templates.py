"""
Hook-specific message templates for Agent Hook notifications.

This module provides specialized templates for different types of Agent Hook
events, integrating with the existing template system while providing
hook-specific formatting and context.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from ..core.base_template import SlackMessageTemplate
from ..core.status_indicators import StatusType
from ..core.agent_hooks import EventCategory, UrgencyLevel, SignificanceLevel
from .jira_templates import JIRATemplate


class HookEventType(Enum):
    """Types of hook events for template selection."""
    STATUS_CHANGE = "status_change"
    ASSIGNMENT = "assignment"
    COMMENT = "comment"
    BLOCKER_DETECTED = "blocker_detected"
    BLOCKER_RESOLVED = "blocker_resolved"
    PRIORITY_CHANGE = "priority_change"
    SPRINT_UPDATE = "sprint_update"
    WORKLOAD_ALERT = "workload_alert"


class HookStatusChangeTemplate(JIRATemplate):
    """Template for Agent Hook status change notifications."""
    
    REQUIRED_FIELDS = ['event', 'transition_analysis', 'ticket']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create status change message blocks with hook context."""
        blocks = []
        
        event = data['event']
        transition_analysis = data['transition_analysis']
        ticket = data['ticket']
        sprint_metrics = data.get('sprint_metrics')
        workload_analysis = data.get('workload_analysis')
        
        # Create enhanced header with hook context
        header_blocks = self._create_hook_header(event, transition_analysis, ticket)
        blocks.extend(header_blocks)
        
        # Add transition visualization
        transition_block = self._create_transition_visualization(transition_analysis)
        blocks.append(transition_block)
        
        # Add impact assessment
        impact_blocks = self._create_impact_assessment(
            transition_analysis, sprint_metrics, workload_analysis
        )
        blocks.extend(impact_blocks)
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add ticket details
        details_block = self._create_summary_fields(ticket, self._get_ticket_field_mapping())
        if details_block:
            blocks.append(details_block)
        
        # Add hook-specific actions
        actions = self._create_hook_actions(transition_analysis, ticket)
        if actions:
            blocks.append(actions)
        
        return blocks
    
    def _create_hook_header(self, event: Dict[str, Any], transition_analysis: Dict[str, Any], ticket: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create header with hook-specific context."""
        blocks = []
        
        # Get transition indicator
        transition_type = transition_analysis.get('type', {})
        transition_name = getattr(transition_type, 'value', 'forward') if hasattr(transition_type, 'value') else str(transition_type)
        
        # Map transition types to indicators
        transition_indicators = {
            'forward': '🟢',
            'backward': '🟡', 
            'blocked': '🔴',
            'unblocked': '✅',
            'completed': '🎉',
            'reopened': '🔄'
        }
        
        indicator = transition_indicators.get(transition_name, '🔄')
        
        # Create title with hook context
        ticket_key = ticket.get('key', 'UNKNOWN')
        ticket_summary = ticket.get('summary', 'No summary')
        title = f"{indicator} Agent Hook: Status Change - {ticket_key}"
        
        # Create header block
        header_block = self.create_header_block(title, StatusType.INFO)
        blocks.append(header_block)
        
        # Add subtitle with ticket summary
        subtitle_text = f"*{self._truncate_text(ticket_summary, 100)}*"
        subtitle_block = self.create_section_block(subtitle_text)
        blocks.append(subtitle_block)
        
        return blocks
    
    def _create_transition_visualization(self, transition_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create visual representation of the status transition."""
        from_status = transition_analysis.get('from_status', 'unknown')
        to_status = transition_analysis.get('to_status', 'unknown')
        urgency = transition_analysis.get('urgency', UrgencyLevel.MEDIUM)
        
        # Get status indicators
        from_indicator = self._get_status_indicator(from_status)
        to_indicator = self._get_status_indicator(to_status)
        
        # Create transition text
        transition_text = (
            f"*Status Transition:*\n"
            f"{from_indicator} {from_status.title()} → {to_indicator} {to_status.title()}"
        )
        
        # Add urgency context
        if hasattr(urgency, 'value'):
            urgency_value = urgency.value
        else:
            urgency_value = str(urgency)
            
        if urgency_value in ['high', 'critical']:
            urgency_indicators = {
                'high': '⚠️ High Priority',
                'critical': '🚨 Critical Priority'
            }
            transition_text += f"\n{urgency_indicators.get(urgency_value, '⚠️ High Priority')}"
        
        return self.create_section_block(transition_text)
    
    def _create_impact_assessment(self, transition_analysis: Dict[str, Any], 
                                 sprint_metrics: Optional[Dict[str, Any]], 
                                 workload_analysis: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create impact assessment blocks."""
        blocks = []
        
        # Sprint impact
        if sprint_metrics:
            sprint_block = self._create_sprint_impact_block(sprint_metrics)
            if sprint_block:
                blocks.append(sprint_block)
        
        # Workload impact
        if workload_analysis:
            workload_block = self._create_workload_impact_block(workload_analysis)
            if workload_block:
                blocks.append(workload_block)
        
        return blocks
    
    def _create_sprint_impact_block(self, sprint_metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create sprint impact assessment block."""
        sprint_name = sprint_metrics.get('sprint_name')
        completion_percentage = sprint_metrics.get('completion_percentage', 0)
        at_risk = sprint_metrics.get('at_risk', False)
        days_remaining = sprint_metrics.get('days_remaining', 0)
        
        if not sprint_name:
            return None
        
        sprint_text = f"*📊 Sprint Impact: {sprint_name}*\n"
        sprint_text += f"Progress: {completion_percentage:.1f}% complete\n"
        sprint_text += f"Days remaining: {days_remaining}"
        
        if at_risk:
            sprint_text += "\n⚠️ *Sprint at risk - may affect delivery*"
        
        return self.create_section_block(sprint_text)
    
    def _create_workload_impact_block(self, workload_analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create workload impact assessment block."""
        assignee = workload_analysis.get('assignee')
        capacity_utilization = workload_analysis.get('capacity_utilization', 0)
        overloaded = workload_analysis.get('overloaded', False)
        current_tickets = workload_analysis.get('current_tickets', 0)
        
        if not assignee:
            return None
        
        workload_text = f"*👤 Workload Impact: {assignee}*\n"
        workload_text += f"Capacity: {capacity_utilization:.0%}\n"
        workload_text += f"Current tickets: {current_tickets}"
        
        if overloaded:
            workload_text += "\n🚨 *Assignee overloaded - consider redistribution*"
        elif capacity_utilization > 0.9:
            workload_text += "\n⚠️ *High capacity utilization*"
        
        return self.create_section_block(workload_text)
    
    def _create_hook_actions(self, transition_analysis: Dict[str, Any], ticket: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create hook-specific action buttons."""
        if not self.config.interactive_elements:
            return None
        
        actions = []
        ticket_key = ticket.get('key', '')
        transition_type = transition_analysis.get('type', {})
        transition_name = getattr(transition_type, 'value', 'forward') if hasattr(transition_type, 'value') else str(transition_type)
        
        # Transition-specific actions
        if transition_name == 'blocked':
            actions.extend([
                {
                    'text': '🆘 Escalate Blocker',
                    'action_id': 'escalate_blocker',
                    'value': ticket_key,
                    'style': 'danger'
                },
                {
                    'text': '👥 Request Help',
                    'action_id': 'request_help',
                    'value': ticket_key
                }
            ])
        elif transition_name == 'completed':
            actions.extend([
                {
                    'text': '📊 Update Sprint',
                    'action_id': 'update_sprint',
                    'value': ticket_key,
                    'style': 'primary'
                },
                {
                    'text': '🎉 Celebrate',
                    'action_id': 'celebrate_completion',
                    'value': ticket_key
                }
            ])
        
        # Common actions
        actions.extend([
            {
                'text': '👀 View Ticket',
                'action_id': 'view_ticket',
                'url': self._get_ticket_url(ticket_key)
            },
            {
                'text': '💬 Add Comment',
                'action_id': 'add_comment',
                'value': ticket_key
            }
        ])
        
        return self._create_action_buttons(actions)


class HookBlockerTemplate(JIRATemplate):
    """Template for Agent Hook blocker notifications."""
    
    REQUIRED_FIELDS = ['event', 'blocker_analysis', 'ticket']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create blocker notification message blocks."""
        blocks = []
        
        event = data['event']
        blocker_analysis = data['blocker_analysis']
        ticket = data['ticket']
        sprint_risk = data.get('sprint_risk')
        
        # Create urgent header
        header_blocks = self._create_blocker_header(event, blocker_analysis, ticket)
        blocks.extend(header_blocks)
        
        # Add blocker analysis
        analysis_block = self._create_blocker_analysis_block(blocker_analysis)
        blocks.append(analysis_block)
        
        # Add sprint risk assessment
        if sprint_risk:
            risk_block = self._create_sprint_risk_block(sprint_risk)
            blocks.append(risk_block)
        
        # Add resolution suggestions
        suggestions_block = self._create_resolution_suggestions(blocker_analysis)
        if suggestions_block:
            blocks.append(suggestions_block)
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add ticket details
        details_block = self._create_summary_fields(ticket, self._get_ticket_field_mapping())
        if details_block:
            blocks.append(details_block)
        
        # Add escalation actions
        actions = self._create_escalation_actions(blocker_analysis, ticket)
        if actions:
            blocks.append(actions)
        
        return blocks
    
    def _create_blocker_header(self, event: Dict[str, Any], blocker_analysis: Dict[str, Any], ticket: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create urgent blocker header."""
        blocks = []
        
        ticket_key = ticket.get('key', 'UNKNOWN')
        severity = blocker_analysis.get('severity', {})
        severity_name = getattr(severity, 'value', 'medium') if hasattr(severity, 'value') else str(severity)
        
        # Severity indicators
        severity_indicators = {
            'low': '🟡',
            'medium': '🟠',
            'high': '🔴',
            'critical': '🚨'
        }
        
        indicator = severity_indicators.get(severity_name, '🔴')
        title = f"{indicator} BLOCKER DETECTED - {ticket_key}"
        
        # Create header with error status for visibility
        header_block = self.create_header_block(title, StatusType.ERROR)
        blocks.append(header_block)
        
        # Add urgency context
        urgency_text = f"*{severity_name.upper()} SEVERITY BLOCKER*"
        if severity_name in ['high', 'critical']:
            urgency_text += "\n⚠️ **IMMEDIATE ATTENTION REQUIRED**"
        
        urgency_block = self.create_section_block(urgency_text)
        blocks.append(urgency_block)
        
        return blocks
    
    def _create_blocker_analysis_block(self, blocker_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create blocker analysis block."""
        blocker_type = blocker_analysis.get('blocker_type', 'unknown')
        impact_assessment = blocker_analysis.get('impact_assessment', 'Impact assessment unavailable')
        escalation_required = blocker_analysis.get('escalation_required', False)
        
        analysis_text = f"*🔍 Blocker Analysis:*\n"
        analysis_text += f"Type: {blocker_type.title()}\n"
        analysis_text += f"Impact: {impact_assessment}"
        
        if escalation_required:
            analysis_text += "\n🚨 *Escalation Required*"
        
        return self.create_section_block(analysis_text)
    
    def _create_sprint_risk_block(self, sprint_risk: str) -> Dict[str, Any]:
        """Create sprint risk assessment block."""
        risk_indicators = {
            'low': '🟢 Low Risk',
            'medium': '🟡 Medium Risk', 
            'high': '🔴 High Risk',
            'critical': '🚨 Critical Risk'
        }
        
        risk_indicator = risk_indicators.get(sprint_risk, '🟡 Medium Risk')
        risk_text = f"*📅 Sprint Risk Assessment:*\n{risk_indicator}"
        
        if sprint_risk in ['high', 'critical']:
            risk_text += "\n⚠️ *May impact sprint delivery timeline*"
        
        return self.create_section_block(risk_text)
    
    def _create_resolution_suggestions(self, blocker_analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create resolution suggestions block."""
        suggestions = blocker_analysis.get('resolution_suggestions', [])
        
        if not suggestions:
            return None
        
        suggestions_text = "*💡 Resolution Suggestions:*\n"
        for i, suggestion in enumerate(suggestions[:3], 1):
            suggestions_text += f"{i}. {suggestion}\n"
        
        return self.create_section_block(suggestions_text)
    
    def _create_escalation_actions(self, blocker_analysis: Dict[str, Any], ticket: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create escalation action buttons."""
        if not self.config.interactive_elements:
            return None
        
        actions = []
        ticket_key = ticket.get('key', '')
        escalation_required = blocker_analysis.get('escalation_required', False)
        
        # Escalation actions
        if escalation_required:
            actions.extend([
                {
                    'text': '🆘 Escalate Now',
                    'action_id': 'escalate_blocker',
                    'value': ticket_key,
                    'style': 'danger'
                },
                {
                    'text': '👥 Request Team Help',
                    'action_id': 'request_team_help',
                    'value': ticket_key
                }
            ])
        
        # Resolution actions
        actions.extend([
            {
                'text': '🔧 Update Blocker Status',
                'action_id': 'update_blocker_status',
                'value': ticket_key,
                'style': 'primary'
            },
            {
                'text': '📝 Add Resolution Notes',
                'action_id': 'add_resolution_notes',
                'value': ticket_key
            },
            {
                'text': '👀 View Ticket',
                'action_id': 'view_ticket',
                'url': self._get_ticket_url(ticket_key)
            }
        ])
        
        return self._create_action_buttons(actions)


class HookAssignmentTemplate(JIRATemplate):
    """Template for Agent Hook assignment notifications."""
    
    REQUIRED_FIELDS = ['event', 'assignment_data', 'ticket']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create assignment notification message blocks."""
        blocks = []
        
        event = data['event']
        assignment_data = data['assignment_data']
        ticket = data['ticket']
        workload_analysis = data.get('workload_analysis')
        
        # Create header
        header_blocks = self._create_assignment_header(event, assignment_data, ticket)
        blocks.extend(header_blocks)
        
        # Add assignment details
        assignment_block = self._create_assignment_details(assignment_data)
        blocks.append(assignment_block)
        
        # Add workload impact
        if workload_analysis:
            workload_block = self._create_workload_analysis_block(workload_analysis)
            blocks.append(workload_block)
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add ticket details
        details_block = self._create_summary_fields(ticket, self._get_ticket_field_mapping())
        if details_block:
            blocks.append(details_block)
        
        # Add assignment actions
        actions = self._create_assignment_actions(assignment_data, ticket)
        if actions:
            blocks.append(actions)
        
        return blocks
    
    def _create_assignment_header(self, event: Dict[str, Any], assignment_data: Dict[str, Any], ticket: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create assignment header."""
        blocks = []
        
        ticket_key = ticket.get('key', 'UNKNOWN')
        to_assignee = assignment_data.get('to_assignee', 'Unassigned')
        
        title = f"👤 Agent Hook: Assignment Change - {ticket_key}"
        
        # Create header
        header_block = self.create_header_block(title, StatusType.INFO)
        blocks.append(header_block)
        
        # Add assignment context
        if to_assignee != 'Unassigned':
            context_text = f"*Assigned to: {self._format_user_mention(to_assignee)}*"
        else:
            context_text = "*Ticket unassigned*"
        
        context_block = self.create_section_block(context_text)
        blocks.append(context_block)
        
        return blocks
    
    def _create_assignment_details(self, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create assignment details block."""
        from_assignee = assignment_data.get('from_assignee', 'Unassigned')
        to_assignee = assignment_data.get('to_assignee', 'Unassigned')
        
        from_mention = self._format_user_mention(from_assignee) if from_assignee != 'Unassigned' else 'Unassigned'
        to_mention = self._format_user_mention(to_assignee) if to_assignee != 'Unassigned' else 'Unassigned'
        
        if from_assignee == 'Unassigned':
            assignment_text = f"*Assignment:* {to_mention}"
        elif to_assignee == 'Unassigned':
            assignment_text = f"*Unassigned from:* {from_mention}"
        else:
            assignment_text = f"*Reassigned:* {from_mention} → {to_mention}"
        
        return self.create_section_block(assignment_text)
    
    def _create_workload_analysis_block(self, workload_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create workload analysis block."""
        assignee = workload_analysis.get('assignee')
        current_tickets = workload_analysis.get('current_tickets', 0)
        capacity_utilization = workload_analysis.get('capacity_utilization', 0)
        overloaded = workload_analysis.get('overloaded', False)
        
        workload_text = f"*📊 Workload Analysis: {assignee}*\n"
        workload_text += f"Current tickets: {current_tickets}\n"
        workload_text += f"Capacity utilization: {capacity_utilization:.0%}"
        
        if overloaded:
            workload_text += "\n🚨 *Assignee overloaded - consider redistribution*"
        elif capacity_utilization > 0.85:
            workload_text += "\n⚠️ *High workload - monitor capacity*"
        
        return self.create_section_block(workload_text)
    
    def _create_assignment_actions(self, assignment_data: Dict[str, Any], ticket: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create assignment-specific actions."""
        if not self.config.interactive_elements:
            return None
        
        actions = []
        ticket_key = ticket.get('key', '')
        to_assignee = assignment_data.get('to_assignee', 'Unassigned')
        
        # Actions based on assignment status
        if to_assignee != 'Unassigned':
            actions.extend([
                {
                    'text': '▶️ Start Work',
                    'action_id': 'start_work',
                    'value': ticket_key,
                    'style': 'primary'
                },
                {
                    'text': '📋 Update Status',
                    'action_id': 'update_status',
                    'value': ticket_key
                }
            ])
        else:
            actions.append({
                'text': '👤 Assign to Me',
                'action_id': 'assign_to_me',
                'value': ticket_key,
                'style': 'primary'
            })
        
        # Common actions
        actions.extend([
            {
                'text': '👀 View Ticket',
                'action_id': 'view_ticket',
                'url': self._get_ticket_url(ticket_key)
            },
            {
                'text': '💬 Add Comment',
                'action_id': 'add_comment',
                'value': ticket_key
            }
        ])
        
        return self._create_action_buttons(actions)


class HookCommentTemplate(JIRATemplate):
    """Template for Agent Hook comment notifications."""
    
    REQUIRED_FIELDS = ['event', 'comment_data', 'ticket']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create comment notification message blocks."""
        blocks = []
        
        event = data['event']
        comment_data = data['comment_data']
        ticket = data['ticket']
        significance_analysis = data.get('significance_analysis')
        
        # Create header
        header_blocks = self._create_comment_header(event, comment_data, ticket)
        blocks.extend(header_blocks)
        
        # Add comment content
        comment_block = self._create_comment_content_block(comment_data)
        blocks.append(comment_block)
        
        # Add significance analysis
        if significance_analysis:
            significance_block = self._create_significance_block(significance_analysis)
            blocks.append(significance_block)
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add ticket details
        details_block = self._create_summary_fields(ticket, self._get_ticket_field_mapping())
        if details_block:
            blocks.append(details_block)
        
        # Add comment actions
        actions = self._create_comment_actions(comment_data, ticket)
        if actions:
            blocks.append(actions)
        
        return blocks
    
    def _create_comment_header(self, event: Dict[str, Any], comment_data: Dict[str, Any], ticket: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create comment header."""
        blocks = []
        
        ticket_key = ticket.get('key', 'UNKNOWN')
        author = comment_data.get('author', 'Unknown')
        
        title = f"💬 Agent Hook: New Comment - {ticket_key}"
        
        # Create header
        header_block = self.create_header_block(title, StatusType.INFO)
        blocks.append(header_block)
        
        # Add author context
        context_text = f"*Comment by: {self._format_user_mention(author)}*"
        context_block = self.create_section_block(context_text)
        blocks.append(context_block)
        
        return blocks
    
    def _create_comment_content_block(self, comment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create comment content block."""
        body = comment_data.get('body', 'No comment text')
        created = comment_data.get('created', '')
        
        # Format timestamp
        time_str = self._format_comment_timestamp(created)
        
        comment_text = f"*💬 Comment* _{time_str}_\n"
        comment_text += f"> {self._truncate_text(body, 400)}"
        
        return self.create_section_block(comment_text)
    
    def _create_significance_block(self, significance_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create comment significance analysis block."""
        significance_level = significance_analysis.get('significance_level', 'moderate')
        keywords_found = significance_analysis.get('keywords_found', [])
        requires_attention = significance_analysis.get('requires_attention', False)
        
        significance_text = f"*🎯 Comment Analysis:*\n"
        significance_text += f"Significance: {significance_level.title()}"
        
        if keywords_found:
            significance_text += f"\nKeywords: {', '.join(keywords_found[:3])}"
        
        if requires_attention:
            significance_text += "\n⚠️ *Requires team attention*"
        
        return self.create_section_block(significance_text)
    
    def _create_comment_actions(self, comment_data: Dict[str, Any], ticket: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create comment-specific actions."""
        if not self.config.interactive_elements:
            return None
        
        actions = []
        ticket_key = ticket.get('key', '')
        
        actions.extend([
            {
                'text': '💬 Reply',
                'action_id': 'reply_comment',
                'value': ticket_key,
                'style': 'primary'
            },
            {
                'text': '📝 View All Comments',
                'action_id': 'view_all_comments',
                'value': ticket_key
            },
            {
                'text': '👀 View Ticket',
                'action_id': 'view_ticket',
                'url': self._get_ticket_url(ticket_key)
            }
        ])
        
        return self._create_action_buttons(actions)
    
    def _format_comment_timestamp(self, timestamp_str: str) -> str:
        """Format comment timestamp for display."""
        if not timestamp_str:
            return 'just now'
        
        try:
            created_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return created_date.strftime('%I:%M %p')
        except (ValueError, AttributeError):
            return 'just now'