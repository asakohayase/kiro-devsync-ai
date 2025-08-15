"""JIRA ticket notification templates for DevSync AI."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from ..core.base_template import SlackMessageTemplate
from ..core.status_indicators import StatusType


class JIRATemplate(SlackMessageTemplate):
    """Base template class for JIRA ticket notifications."""
    
    REQUIRED_FIELDS = ['ticket']
    
    def __init__(self, *args, **kwargs):
        """Initialize JIRA template."""
        super().__init__(*args, **kwargs)
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create JIRA message blocks. Override in subclasses."""
        blocks = []
        
        # Create ticket header
        header_blocks = self.create_ticket_header(data['ticket'])
        blocks.extend(header_blocks)
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Create ticket details
        details_block = self._create_summary_fields(
            data['ticket'], 
            self._get_ticket_field_mapping()
        )
        if details_block:
            blocks.append(details_block)
        
        return blocks
    
    def create_ticket_header(self, ticket_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create consistent ticket information display header."""
        blocks = []
        
        # Extract ticket information
        key = ticket_data.get('key', 'UNKNOWN')
        summary = ticket_data.get('summary', 'No summary available')
        status = ticket_data.get('status', 'Unknown')
        
        # Determine status type for header
        status_type = self._map_jira_status_to_type(status)
        
        # Create header with ticket key and summary
        title = f"{key}: {self._truncate_text(summary, 100)}"
        header_blocks = self._create_header_section(title, status_type)
        blocks.extend(header_blocks)
        
        return blocks
    
    def create_status_transition(self, from_status: str, to_status: str) -> Dict[str, Any]:
        """Create visual workflow context for status transitions."""
        from_indicator = self._get_status_indicator(from_status)
        to_indicator = self._get_status_indicator(to_status)
        
        transition_text = (
            f"*Status Transition:*\n"
            f"{from_indicator} {from_status} → {to_indicator} {to_status}"
        )
        
        return self.create_section_block(transition_text)
    
    def create_priority_indicators(self, priority: str, previous_priority: Optional[str] = None) -> Dict[str, Any]:
        """Create urgency visualization for priority levels."""
        priority_indicator = self._get_priority_indicator(priority)
        
        if previous_priority:
            prev_indicator = self._get_priority_indicator(previous_priority)
            priority_text = (
                f"*Priority Change:*\n"
                f"{prev_indicator} → {priority_indicator}"
            )
            
            # Add urgency context for high priorities
            if priority.lower() in ['critical', 'blocker', 'highest']:
                priority_text += "\n🚨 *Requires immediate attention*"
            elif priority.lower() == 'high':
                priority_text += "\n⚠️ *Should be prioritized*"
        else:
            priority_text = f"*Priority:* {priority_indicator}"
        
        return self.create_section_block(priority_text)
    
    def _get_ticket_field_mapping(self) -> Dict[str, str]:
        """Get field mapping for ticket details."""
        return {
            'assignee': 'Assignee',
            'reporter': 'Reporter', 
            'priority': 'Priority',
            'story_points': 'Story Points',
            'sprint': 'Sprint',
            'epic': 'Epic',
            'components': 'Components',
            'labels': 'Labels'
        }
    
    def _map_jira_status_to_type(self, status: str) -> StatusType:
        """Map JIRA status to StatusType enum."""
        status_lower = status.lower()
        
        if status_lower in ['done', 'closed', 'resolved']:
            return StatusType.SUCCESS
        elif status_lower in ['in progress', 'in development']:
            return StatusType.IN_PROGRESS
        elif status_lower in ['blocked', 'impediment']:
            return StatusType.ERROR
        elif status_lower in ['in review', 'code review']:
            return StatusType.WARNING
        else:
            return StatusType.INFO
    
    def _get_status_indicator(self, status: str) -> str:
        """Get emoji indicator for JIRA status."""
        status_indicators = {
            'to do': '📋',
            'todo': '📋',
            'backlog': '📋',
            'open': '📋',
            'in progress': '⏳',
            'in development': '⏳',
            'in review': '👀',
            'code review': '👀',
            'testing': '🧪',
            'qa': '🧪',
            'done': '✅',
            'closed': '✅',
            'resolved': '✅',
            'blocked': '🚫',
            'impediment': '🚫',
            'cancelled': '❌',
            'canceled': '❌'
        }
        return status_indicators.get(status.lower(), '📄')
    
    def _format_ticket_field_value(self, key: str, value: Any) -> str:
        """Format ticket field values for display."""
        if key == 'assignee' and value:
            return self._format_user_mention(str(value))
        elif key == 'reporter' and value:
            return self._format_user_mention(str(value))
        elif key == 'priority' and value:
            return self._get_priority_indicator(str(value))
        elif key == 'story_points' and value:
            return f"📊 {value} points"
        elif key == 'components' and isinstance(value, list):
            component_names = [str(comp) for comp in value[:3]]
            result = ", ".join([f"`{name}`" for name in component_names])
            if len(value) > 3:
                result += f" (+{len(value)-3} more)"
            return result
        elif key == 'labels' and isinstance(value, list):
            label_list = value[:3]
            result = ", ".join([f"`{label}`" for label in label_list])
            if len(value) > 3:
                result += f" (+{len(value)-3} more)"
            return result
        elif key == 'sprint' and value:
            return f"🏃 {value}"
        elif key == 'epic' and value:
            return f"📚 {value}"
        else:
            return str(value) if value is not None else "None"
    
    def _get_ticket_url(self, ticket_key: str) -> str:
        """Get JIRA ticket URL."""
        # This should be configurable based on JIRA instance
        base_url = getattr(self.config, 'jira_base_url', 'https://jira.company.com')
        return f"{base_url}/browse/{ticket_key}"
    
    def _create_summary_fields(self, data: Dict[str, Any], field_mapping: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Override to use JIRA-specific field formatting."""
        fields = {}
        for key, display_name in field_mapping.items():
            if key in data and data[key] is not None:
                formatted_value = self._format_ticket_field_value(key, data[key])
                fields[display_name] = formatted_value
        
        return self.create_fields_section(fields) if fields else None


class StatusChangeTemplate(JIRATemplate):
    """Template for JIRA status change notifications."""
    
    REQUIRED_FIELDS = ['ticket', 'from_status', 'to_status']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create status change message blocks."""
        blocks = []
        
        # Create ticket header
        header_blocks = self.create_ticket_header(data['ticket'])
        blocks.extend(header_blocks)
        
        # Add status transition
        transition_block = self.create_status_transition(
            data['from_status'], 
            data['to_status']
        )
        blocks.append(transition_block)
        
        # Add workflow context
        workflow_context = self._create_workflow_context(
            data['from_status'], 
            data['to_status']
        )
        if workflow_context:
            blocks.append(workflow_context)
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add ticket details
        details_block = self._create_summary_fields(
            data['ticket'], 
            self._get_ticket_field_mapping()
        )
        if details_block:
            blocks.append(details_block)
        
        # Add action buttons
        actions = self._create_status_actions(data['to_status'], data['ticket'])
        if actions:
            blocks.append(actions)
        
        return blocks
    
    def _create_workflow_context(self, from_status: str, to_status: str) -> Optional[Dict[str, Any]]:
        """Create workflow context message."""
        workflow_messages = {
            ('to do', 'in progress'): "🚀 Work has started on this ticket!",
            ('todo', 'in progress'): "🚀 Work has started on this ticket!",
            ('in progress', 'in review'): "👀 Ready for code review",
            ('in progress', 'testing'): "🧪 Ready for testing",
            ('in review', 'done'): "✅ Review approved and completed",
            ('testing', 'done'): "✅ Testing passed and completed",
            ('in progress', 'blocked'): "🚫 Work is blocked - needs attention",
            ('blocked', 'in progress'): "🎉 Blocker resolved - work resumed"
        }
        
        key = (from_status.lower(), to_status.lower())
        message = workflow_messages.get(key)
        
        if message:
            return self.create_section_block(f"*Workflow Update:* {message}")
        
        return None
    
    def _create_status_actions(self, status: str, ticket_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create status-specific action buttons."""
        if not self.config.interactive_elements:
            return None
        
        actions = []
        ticket_key = ticket_data.get('key', '')
        
        # Status-specific actions
        status_lower = status.lower()
        if status_lower in ['to do', 'todo', 'backlog']:
            actions.extend([
                {
                    'text': '▶️ Start Work',
                    'action_id': 'start_work',
                    'value': ticket_key,
                    'style': 'primary'
                },
                {
                    'text': '👤 Assign to Me',
                    'action_id': 'assign_to_me',
                    'value': ticket_key
                }
            ])
        elif status_lower in ['in progress', 'in development']:
            actions.extend([
                {
                    'text': '✅ Mark Done',
                    'action_id': 'mark_done',
                    'value': ticket_key,
                    'style': 'primary'
                },
                {
                    'text': '🚫 Block',
                    'action_id': 'block_ticket',
                    'value': ticket_key,
                    'style': 'danger'
                }
            ])
        elif status_lower in ['in review', 'code review']:
            actions.extend([
                {
                    'text': '✅ Approve',
                    'action_id': 'approve_ticket',
                    'value': ticket_key,
                    'style': 'primary'
                },
                {
                    'text': '🔄 Back to Progress',
                    'action_id': 'back_to_progress',
                    'value': ticket_key
                }
            ])
        
        # Common actions
        actions.extend([
            {
                'text': '💬 Comment',
                'action_id': 'add_comment',
                'value': ticket_key
            },
            {
                'text': '👀 View Ticket',
                'action_id': 'view_ticket',
                'url': self._get_ticket_url(ticket_key)
            }
        ])
        
        return self._create_action_buttons(actions)


class PriorityChangeTemplate(JIRATemplate):
    """Template for JIRA priority change notifications."""
    
    REQUIRED_FIELDS = ['ticket', 'from_priority', 'to_priority']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create priority change message blocks."""
        blocks = []
        
        # Create ticket header
        header_blocks = self.create_ticket_header(data['ticket'])
        blocks.extend(header_blocks)
        
        # Add priority change with escalation indicators
        priority_block = self.create_priority_indicators(
            data['to_priority'],
            data['from_priority']
        )
        blocks.append(priority_block)
        
        # Add escalation context
        escalation_context = self._create_escalation_context(
            data['from_priority'],
            data['to_priority']
        )
        if escalation_context:
            blocks.append(escalation_context)
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add ticket details
        details_block = self._create_summary_fields(
            data['ticket'], 
            self._get_ticket_field_mapping()
        )
        if details_block:
            blocks.append(details_block)
        
        # Add priority-specific actions
        actions = self._create_priority_actions(data['to_priority'], data['ticket'])
        if actions:
            blocks.append(actions)
        
        return blocks
    
    def _create_escalation_context(self, from_priority: str, to_priority: str) -> Optional[Dict[str, Any]]:
        """Create escalation context based on priority change."""
        to_lower = to_priority.lower()
        from_lower = from_priority.lower()
        
        # Define priority levels for comparison
        priority_levels = {
            'lowest': 1,
            'low': 2,
            'medium': 3,
            'high': 4,
            'highest': 5,
            'critical': 6,
            'blocker': 7
        }
        
        to_level = priority_levels.get(to_lower, 3)
        from_level = priority_levels.get(from_lower, 3)
        
        if to_level > from_level:
            # Priority increased
            if to_lower in ['blocker', 'critical']:
                message = "🚨 **URGENT ESCALATION** - This ticket now requires immediate attention!"
            elif to_lower == 'highest':
                message = "🔴 **HIGH PRIORITY ESCALATION** - This ticket should be prioritized immediately"
            elif to_lower == 'high':
                message = "🟠 **PRIORITY ESCALATION** - This ticket has been elevated in priority"
            else:
                message = "📈 Priority has been increased"
        elif to_level < from_level:
            # Priority decreased
            message = "📉 Priority has been reduced - can be scheduled with lower urgency"
        else:
            return None
        
        return self.create_section_block(f"*Escalation Impact:* {message}")
    
    def _create_priority_actions(self, priority: str, ticket_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create priority-specific action buttons."""
        if not self.config.interactive_elements:
            return None
        
        actions = []
        ticket_key = ticket_data.get('key', '')
        priority_lower = priority.lower()
        
        # High priority actions
        if priority_lower in ['blocker', 'critical', 'highest']:
            actions.extend([
                {
                    'text': '🚨 Escalate to Team Lead',
                    'action_id': 'escalate_priority',
                    'value': ticket_key,
                    'style': 'danger'
                },
                {
                    'text': '👥 Request Help',
                    'action_id': 'request_help',
                    'value': ticket_key
                }
            ])
        
        # Common actions
        actions.extend([
            {
                'text': '💬 Add Comment',
                'action_id': 'add_comment',
                'value': ticket_key
            },
            {
                'text': '👀 View Ticket',
                'action_id': 'view_ticket',
                'url': self._get_ticket_url(ticket_key)
            }
        ])
        
        return self._create_action_buttons(actions)


class AssignmentTemplate(JIRATemplate):
    """Template for JIRA assignment change notifications."""
    
    REQUIRED_FIELDS = ['ticket', 'from_assignee', 'to_assignee']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create assignment change message blocks."""
        blocks = []
        
        # Create ticket header
        header_blocks = self.create_ticket_header(data['ticket'])
        blocks.extend(header_blocks)
        
        # Add assignment transition
        assignment_block = self._create_assignment_transition(
            data['from_assignee'],
            data['to_assignee']
        )
        blocks.append(assignment_block)
        
        # Add notification for new assignee
        if data['to_assignee'] and data['to_assignee'] != 'Unassigned':
            notification_block = self._create_assignee_notification(data['to_assignee'])
            blocks.append(notification_block)
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add ticket details
        details_block = self._create_summary_fields(
            data['ticket'], 
            self._get_ticket_field_mapping()
        )
        if details_block:
            blocks.append(details_block)
        
        # Add assignment actions
        actions = self._create_assignment_actions(data['to_assignee'], data['ticket'])
        if actions:
            blocks.append(actions)
        
        return blocks
    
    def _create_assignment_transition(self, from_assignee: str, to_assignee: str) -> Dict[str, Any]:
        """Create assignment transition display."""
        from_mention = self._format_user_mention(from_assignee) if from_assignee and from_assignee != 'Unassigned' else 'Unassigned'
        to_mention = self._format_user_mention(to_assignee) if to_assignee and to_assignee != 'Unassigned' else 'Unassigned'
        
        if from_assignee == 'Unassigned' or not from_assignee:
            assignment_text = f"*👤 Assigned to:* {to_mention}"
        elif to_assignee == 'Unassigned' or not to_assignee:
            assignment_text = f"*👤 Unassigned from:* {from_mention}"
        else:
            assignment_text = f"*👤 Reassigned:* {from_mention} → {to_mention}"
        
        return self.create_section_block(assignment_text)
    
    def _create_assignee_notification(self, assignee: str) -> Dict[str, Any]:
        """Create notification for new assignee."""
        assignee_mention = self._format_user_mention(assignee)
        notification_text = f"👋 Hey {assignee_mention}, this ticket is now assigned to you!"
        
        return self.create_section_block(notification_text)
    
    def _create_assignment_actions(self, assignee: str, ticket_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create assignment-specific action buttons."""
        if not self.config.interactive_elements:
            return None
        
        actions = []
        ticket_key = ticket_data.get('key', '')
        
        # Actions for assigned tickets
        if assignee and assignee != 'Unassigned':
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
            # Actions for unassigned tickets
            actions.append({
                'text': '👤 Assign to Me',
                'action_id': 'assign_to_me',
                'value': ticket_key,
                'style': 'primary'
            })
        
        # Common actions
        actions.extend([
            {
                'text': '💬 Add Comment',
                'action_id': 'add_comment',
                'value': ticket_key
            },
            {
                'text': '👀 View Ticket',
                'action_id': 'view_ticket',
                'url': self._get_ticket_url(ticket_key)
            }
        ])
        
        return self._create_action_buttons(actions)


class CommentTemplate(JIRATemplate):
    """Template for JIRA comment notifications."""
    
    REQUIRED_FIELDS = ['ticket', 'comment']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create comment notification message blocks."""
        blocks = []
        
        # Create ticket header
        header_blocks = self.create_ticket_header(data['ticket'])
        blocks.extend(header_blocks)
        
        # Add comment content with author info
        comment_block = self._create_comment_display(data['comment'])
        blocks.append(comment_block)
        
        # Add comment history context if available
        comment_history = self._create_comment_history_context(data)
        if comment_history:
            blocks.append(comment_history)
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add ticket details
        details_block = self._create_summary_fields(
            data['ticket'], 
            self._get_ticket_field_mapping()
        )
        if details_block:
            blocks.append(details_block)
        
        # Add comment actions
        actions = self._create_comment_actions(data['ticket'])
        if actions:
            blocks.append(actions)
        
        return blocks
    
    def _create_comment_display(self, comment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create comment display with author info."""
        author = comment_data.get('author', 'Unknown')
        body = comment_data.get('body', 'No comment text')
        created = comment_data.get('created', '')
        
        # Format timestamp
        time_str = self._format_comment_timestamp(created)
        
        # Format comment content
        author_mention = self._format_user_mention(author)
        comment_text = (
            f"*💬 New comment by {author_mention}* _{time_str}_\n"
            f"> {self._truncate_text(body, 300)}"
        )
        
        return self.create_section_block(comment_text)
    
    def _create_comment_history_context(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create comment history context."""
        total_comments = data.get('total_comments')
        if total_comments and total_comments > 1:
            history_text = f"*📝 Comment History:* {total_comments} total comments"
            return self.create_section_block(history_text)
        return None
    
    def _create_comment_actions(self, ticket_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create comment-specific action buttons."""
        if not self.config.interactive_elements:
            return None
        
        actions = []
        ticket_key = ticket_data.get('key', '')
        
        actions.extend([
            {
                'text': '💬 Reply',
                'action_id': 'reply_comment',
                'value': ticket_key,
                'style': 'primary'
            },
            {
                'text': '📝 View All Comments',
                'action_id': 'view_comments',
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


class BlockerTemplate(JIRATemplate):
    """Template for JIRA blocker notifications."""
    
    REQUIRED_FIELDS = ['ticket', 'blocker_status']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create blocker notification message blocks."""
        blocks = []
        
        # Create ticket header
        header_blocks = self.create_ticket_header(data['ticket'])
        blocks.extend(header_blocks)
        
        # Add blocker status with escalation actions
        blocker_block = self._create_blocker_status_display(data)
        blocks.append(blocker_block)
        
        # Add blocker impact assessment
        impact_block = self._create_blocker_impact_assessment(data)
        if impact_block:
            blocks.append(impact_block)
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add ticket details
        details_block = self._create_summary_fields(
            data['ticket'], 
            self._get_ticket_field_mapping()
        )
        if details_block:
            blocks.append(details_block)
        
        # Add blocker-specific escalation actions
        actions = self._create_blocker_escalation_actions(data)
        if actions:
            blocks.append(actions)
        
        return blocks
    
    def _create_blocker_status_display(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create blocker status display with escalation context."""
        blocker_status = data['blocker_status']  # 'identified' or 'resolved'
        blocker_description = data.get('blocker_description', '')
        
        if blocker_status == 'identified':
            emoji = "🚫"
            title = "*🚫 Blocker Identified*"
            urgency_msg = "\n⚠️ **This ticket is now blocked and needs attention**"
        else:  # resolved
            emoji = "🎉"
            title = "*🎉 Blocker Resolved*"
            urgency_msg = "\n✅ **Work can now continue on this ticket**"
        
        blocker_text = title
        if blocker_description:
            blocker_text += f"\n{blocker_description}"
        blocker_text += urgency_msg
        
        return self.create_section_block(blocker_text)
    
    def _create_blocker_impact_assessment(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create blocker impact assessment."""
        blocker_status = data['blocker_status']
        ticket_data = data['ticket']
        
        # Assess impact based on ticket priority and sprint context
        priority = ticket_data.get('priority', 'Medium').lower()
        sprint = ticket_data.get('sprint')
        
        impact_parts = []
        
        if blocker_status == 'identified':
            if priority in ['critical', 'blocker', 'highest']:
                impact_parts.append("🚨 **HIGH IMPACT** - Critical priority ticket blocked")
            elif priority == 'high':
                impact_parts.append("🟠 **MEDIUM IMPACT** - High priority ticket blocked")
            
            if sprint:
                impact_parts.append(f"📅 **SPRINT IMPACT** - May affect sprint {sprint} delivery")
            
            # Add escalation timeline
            impact_parts.append("⏰ **ACTION REQUIRED** - Blocker should be resolved within 24 hours")
        
        if impact_parts:
            impact_text = "*🎯 Impact Assessment:*\n" + "\n".join([f"• {part}" for part in impact_parts])
            return self.create_section_block(impact_text)
        
        return None
    
    def _create_blocker_escalation_actions(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create blocker-specific escalation action buttons."""
        if not self.config.interactive_elements:
            return None
        
        actions = []
        ticket_key = data['ticket'].get('key', '')
        blocker_status = data['blocker_status']
        
        if blocker_status == 'identified':
            actions.extend([
                {
                    'text': '🆘 Escalate to Team Lead',
                    'action_id': 'escalate_blocker',
                    'value': ticket_key,
                    'style': 'danger'
                },
                {
                    'text': '👥 Request Help',
                    'action_id': 'request_help',
                    'value': ticket_key
                },
                {
                    'text': '📝 Update Blocker Status',
                    'action_id': 'update_blocker',
                    'value': ticket_key
                }
            ])
        else:  # resolved
            actions.extend([
                {
                    'text': '▶️ Resume Work',
                    'action_id': 'resume_work',
                    'value': ticket_key,
                    'style': 'primary'
                },
                {
                    'text': '📊 Update Progress',
                    'action_id': 'update_progress',
                    'value': ticket_key
                }
            ])
        
        # Common actions
        actions.extend([
            {
                'text': '💬 Add Comment',
                'action_id': 'add_comment',
                'value': ticket_key
            },
            {
                'text': '👀 View Ticket',
                'action_id': 'view_ticket',
                'url': self._get_ticket_url(ticket_key)
            }
        ])
        
        return self._create_action_buttons(actions)


class SprintChangeTemplate(JIRATemplate):
    """Template for JIRA sprint change notifications."""
    
    REQUIRED_FIELDS = ['ticket', 'sprint_change']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create sprint change message blocks."""
        blocks = []
        
        # Create ticket header
        header_blocks = self.create_ticket_header(data['ticket'])
        blocks.extend(header_blocks)
        
        # Add sprint transition with capacity context
        sprint_block = self._create_sprint_transition_display(data['sprint_change'])
        blocks.append(sprint_block)
        
        # Add sprint capacity context
        capacity_context = self._create_sprint_capacity_context(data)
        if capacity_context:
            blocks.append(capacity_context)
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add ticket details
        details_block = self._create_summary_fields(
            data['ticket'], 
            self._get_ticket_field_mapping()
        )
        if details_block:
            blocks.append(details_block)
        
        # Add sprint actions
        actions = self._create_sprint_actions(data)
        if actions:
            blocks.append(actions)
        
        return blocks
    
    def _create_sprint_transition_display(self, sprint_change: Dict[str, Any]) -> Dict[str, Any]:
        """Create sprint transition display."""
        from_sprint = sprint_change.get('from', 'Backlog')
        to_sprint = sprint_change.get('to', 'Unknown Sprint')
        change_type = sprint_change.get('type', 'moved')  # moved, added, removed
        
        if change_type == 'added':
            sprint_text = f"*🏃 Added to Sprint:* {to_sprint}"
        elif change_type == 'removed':
            sprint_text = f"*🏃 Removed from Sprint:* {from_sprint}"
        else:  # moved
            sprint_text = f"*🏃 Sprint Changed:* {from_sprint} → {to_sprint}"
        
        return self.create_section_block(sprint_text)
    
    def _create_sprint_capacity_context(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create sprint capacity context information."""
        sprint_info = data.get('sprint_info', {})
        if not sprint_info:
            return None
        
        context_parts = ["*📊 Sprint Context:*"]
        
        # Sprint dates
        start_date = sprint_info.get('start_date')
        end_date = sprint_info.get('end_date')
        if start_date and end_date:
            context_parts.append(f"📅 Duration: {start_date} - {end_date}")
        
        # Sprint capacity
        capacity = sprint_info.get('capacity')
        committed_points = sprint_info.get('committed_points')
        if capacity and committed_points:
            utilization = (committed_points / capacity) * 100 if capacity > 0 else 0
            context_parts.append(f"📊 Capacity: {committed_points}/{capacity} story points ({utilization:.0f}%)")
            
            # Add capacity warnings
            if utilization > 100:
                context_parts.append("⚠️ **OVER CAPACITY** - Sprint may be at risk")
            elif utilization > 90:
                context_parts.append("🟡 **NEAR CAPACITY** - Limited room for additional work")
        
        # Sprint progress
        completed_points = sprint_info.get('completed_points')
        if completed_points is not None and committed_points:
            progress = (completed_points / committed_points) * 100 if committed_points > 0 else 0
            context_parts.append(f"📈 Progress: {completed_points}/{committed_points} points ({progress:.0f}%)")
        
        # Team velocity context
        team_velocity = sprint_info.get('team_velocity')
        if team_velocity:
            context_parts.append(f"🏃 Team Velocity: {team_velocity} points/sprint average")
        
        if len(context_parts) > 1:
            context_text = "\n".join([f"• {part}" if i > 0 else part for i, part in enumerate(context_parts)])
            return self.create_section_block(context_text)
        
        return None
    
    def _create_sprint_actions(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create sprint-specific action buttons."""
        if not self.config.interactive_elements:
            return None
        
        actions = []
        ticket_key = data['ticket'].get('key', '')
        sprint_change = data['sprint_change']
        
        # Actions based on sprint change type
        if sprint_change.get('type') == 'added':
            actions.extend([
                {
                    'text': '📋 View Sprint Board',
                    'action_id': 'view_sprint_board',
                    'value': ticket_key
                },
                {
                    'text': '📊 Sprint Planning',
                    'action_id': 'sprint_planning',
                    'value': ticket_key
                }
            ])
        
        # Common actions
        actions.extend([
            {
                'text': '🏃 View Sprint',
                'action_id': 'view_sprint',
                'value': ticket_key
            },
            {
                'text': '💬 Add Comment',
                'action_id': 'add_comment',
                'value': ticket_key
            },
            {
                'text': '👀 View Ticket',
                'action_id': 'view_ticket',
                'url': self._get_ticket_url(ticket_key)
            }
        ])
        
        return self._create_action_buttons(actions)