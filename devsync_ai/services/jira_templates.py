"""
JIRA ticket update templates for DevSync AI notifications.
Provides rich formatting for various JIRA ticket lifecycle events.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from .slack_templates import SlackTemplateBase


class JIRATemplateBase(SlackTemplateBase):
    """Base class for JIRA ticket templates."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
        self.ticket = data.get('ticket', {})
        self.change_type = data.get('change_type', 'updated')
        self.fallback_text = f"JIRA {self.change_type}: {self.ticket.get('key', 'Unknown')} - {self.ticket.get('summary', 'Unknown')}"
    
    def _get_priority_emoji(self, priority: str) -> str:
        """Get emoji for JIRA priority."""
        priority_map = {
            'blocker': '🚨',
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢',
            'lowest': '⚪'
        }
        return priority_map.get(priority.lower(), '🟡')
    
    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for JIRA status."""
        status_map = {
            'to do': '📋',
            'todo': '📋',
            'backlog': '📋',
            'in progress': '⏳',
            'in review': '👀',
            'code review': '👀',
            'testing': '🧪',
            'qa': '🧪',
            'done': '✅',
            'closed': '✅',
            'resolved': '✅',
            'blocked': '🚫',
            'cancelled': '❌',
            'rejected': '❌'
        }
        return status_map.get(status.lower(), '📄')
    
    def _format_time_duration(self, time_str: str) -> str:
        """Format time duration for display."""
        if not time_str or time_str == "0h":
            return "None"
        return time_str
    
    def _create_status_transition_visual(self, from_status: str, to_status: str) -> str:
        """Create visual representation of status transition."""
        from_emoji = self._get_status_emoji(from_status)
        to_emoji = self._get_status_emoji(to_status)
        return f"{from_emoji} {from_status} → {to_emoji} {to_status}"
    
    def _add_ticket_header(self, emoji: str = "🎫") -> None:
        """Add ticket header with key and summary."""
        key = self.ticket.get('key', 'Unknown')
        summary = self.ticket.get('summary', 'Unknown ticket')
        
        self.add_header(f"{key}: {summary}", emoji)
    
    def _add_ticket_details(self) -> None:
        """Add basic ticket details section."""
        assignee = self.ticket.get('assignee', 'Unassigned')
        reporter = self.ticket.get('reporter', 'Unknown')
        priority = self.ticket.get('priority', 'Medium')
        priority_emoji = self._get_priority_emoji(priority)
        
        # Basic details
        details_fields = [
            {
                "type": "mrkdwn",
                "text": f"*👤 Assignee:* {assignee}"
            },
            {
                "type": "mrkdwn",
                "text": f"*📝 Reporter:* {reporter}"
            },
            {
                "type": "mrkdwn",
                "text": f"*{priority_emoji} Priority:* {priority}"
            }
        ]
        
        # Add sprint and epic if available
        sprint = self.ticket.get('sprint')
        epic = self.ticket.get('epic')
        
        if sprint:
            details_fields.append({
                "type": "mrkdwn",
                "text": f"*🏃 Sprint:* {sprint}"
            })
        
        if epic:
            details_fields.append({
                "type": "mrkdwn",
                "text": f"*📚 Epic:* {epic}"
            })
        
        # Add story points if available
        story_points = self.ticket.get('story_points')
        if story_points:
            details_fields.append({
                "type": "mrkdwn",
                "text": f"*📊 Story Points:* {story_points}"
            })
        
        self.blocks.append({
            "type": "section",
            "fields": details_fields
        })
    
    def _add_time_tracking(self) -> None:
        """Add time tracking information if available."""
        time_spent = self.ticket.get('time_spent')
        time_remaining = self.ticket.get('time_remaining')
        
        if time_spent or time_remaining:
            time_text = "*⏱️ Time Tracking:*\n"
            
            if time_spent:
                time_text += f"• Spent: {self._format_time_duration(time_spent)}\n"
            
            if time_remaining:
                time_text += f"• Remaining: {self._format_time_duration(time_remaining)}\n"
            
            # Calculate progress if both values available
            if time_spent and time_remaining and time_spent != "0h" and time_remaining != "0h":
                try:
                    spent_hours = float(time_spent.replace('h', '').replace('m', '').split()[0])
                    remaining_hours = float(time_remaining.replace('h', '').replace('m', '').split()[0])
                    total_hours = spent_hours + remaining_hours
                    progress = (spent_hours / total_hours) * 100 if total_hours > 0 else 0
                    time_text += f"• Progress: {progress:.0f}%"
                except (ValueError, IndexError):
                    pass
            
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": time_text.strip()
                }
            })
    
    def _add_comments_preview(self) -> None:
        """Add recent comments preview."""
        comments = self.ticket.get('comments', [])
        
        if comments:
            # Show latest comment
            latest_comment = comments[-1]
            author = latest_comment.get('author', 'Unknown')
            text = latest_comment.get('text', '')[:150]
            if len(latest_comment.get('text', '')) > 150:
                text += '...'
            
            comment_text = f"*💬 Latest Comment by {author}:*\n> {text}"
            
            if len(comments) > 1:
                comment_text += f"\n_+{len(comments) - 1} more comments_"
            
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": comment_text
                }
            })
    
    def _add_action_buttons(self) -> None:
        """Add interactive action buttons."""
        key = self.ticket.get('key', '')
        
        buttons = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "👀 View Ticket",
                    "emoji": True
                },
                "url": f"https://jira.company.com/browse/{key}",
                "action_id": "view_ticket"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "💬 Add Comment",
                    "emoji": True
                },
                "value": f"comment_{key}",
                "action_id": "add_comment"
            }
        ]
        
        # Add status-specific buttons
        current_status = self.ticket.get('status', {})
        if isinstance(current_status, dict):
            status_name = current_status.get('to', current_status.get('name', ''))
        else:
            status_name = str(current_status)
        
        if status_name.lower() in ['to do', 'todo', 'backlog']:
            buttons.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "▶️ Start Work",
                    "emoji": True
                },
                "value": f"start_{key}",
                "action_id": "start_work",
                "style": "primary"
            })
        elif status_name.lower() in ['in progress']:
            buttons.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "✅ Mark Done",
                    "emoji": True
                },
                "value": f"done_{key}",
                "action_id": "mark_done",
                "style": "primary"
            })
        
        # Split buttons into groups of 5 (Slack limit)
        for i in range(0, len(buttons), 5):
            button_group = buttons[i:i+5]
            self.blocks.append({
                "type": "actions",
                "elements": button_group
            })
    
    def _add_footer(self) -> None:
        """Add footer with timestamp."""
        updated = self.ticket.get('updated', '')
        if updated:
            try:
                updated_date = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                timestamp = updated_date.strftime('%m/%d %I:%M %p')
            except (ValueError, AttributeError):
                timestamp = datetime.now().strftime('%I:%M %p')
        else:
            timestamp = datetime.now().strftime('%I:%M %p')
        
        self.add_context([
            f"Updated at {timestamp}",
            "DevSync AI"
        ])


class JIRAStatusChangeTemplate(JIRATemplateBase):
    """Template for JIRA status changes."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self._build_template()
    
    def _build_template(self) -> None:
        """Build status change template."""
        status = self.ticket.get('status', {})
        from_status = status.get('from', 'Unknown')
        to_status = status.get('to', 'Unknown')
        
        # Header with status transition
        self._add_ticket_header("🔄")
        
        # Status transition visualization
        transition_visual = self._create_status_transition_visual(from_status, to_status)
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Status Changed:* {transition_visual}"
            }
        })
        
        self.add_divider()
        self._add_ticket_details()
        self._add_time_tracking()
        
        # Add workflow context
        self._add_workflow_context(from_status, to_status)
        
        self._add_comments_preview()
        self._add_action_buttons()
        self._add_footer()
    
    def _add_workflow_context(self, from_status: str, to_status: str) -> None:
        """Add workflow context and next steps."""
        workflow_messages = {
            ('to do', 'in progress'): "🚀 Work has started on this ticket!",
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
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Workflow Update:* {message}"
                }
            })


class JIRAPriorityChangeTemplate(JIRATemplateBase):
    """Template for JIRA priority changes."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self._build_template()
    
    def _build_template(self) -> None:
        """Build priority change template."""
        priority = self.ticket.get('priority_change', {})
        from_priority = priority.get('from', 'Unknown')
        to_priority = priority.get('to', 'Unknown')
        
        # Header
        self._add_ticket_header("⚡")
        
        # Priority change visualization
        from_emoji = self._get_priority_emoji(from_priority)
        to_emoji = self._get_priority_emoji(to_priority)
        
        priority_visual = f"{from_emoji} {from_priority} → {to_emoji} {to_priority}"
        
        # Determine urgency message
        urgency_messages = {
            'blocker': "🚨 **URGENT** - This is now a blocker!",
            'critical': "🔴 **HIGH PRIORITY** - Needs immediate attention",
            'high': "🟠 **ELEVATED** - Should be prioritized",
            'medium': "🟡 Standard priority level",
            'low': "🟢 Lower priority - can be scheduled later"
        }
        
        urgency_msg = urgency_messages.get(to_priority.lower(), "Priority updated")
        
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Priority Changed:* {priority_visual}\n{urgency_msg}"
            }
        })
        
        self.add_divider()
        self._add_ticket_details()
        self._add_time_tracking()
        self._add_comments_preview()
        self._add_action_buttons()
        self._add_footer()


class JIRAAssignmentChangeTemplate(JIRATemplateBase):
    """Template for JIRA assignment changes."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self._build_template()
    
    def _build_template(self) -> None:
        """Build assignment change template."""
        assignment = self.ticket.get('assignment_change', {})
        from_assignee = assignment.get('from', 'Unassigned')
        to_assignee = assignment.get('to', 'Unassigned')
        
        # Header
        self._add_ticket_header("👤")
        
        # Assignment change
        if from_assignee == 'Unassigned':
            assignment_msg = f"*Assigned to:* @{to_assignee}"
        elif to_assignee == 'Unassigned':
            assignment_msg = f"*Unassigned from:* @{from_assignee}"
        else:
            assignment_msg = f"*Reassigned:* @{from_assignee} → @{to_assignee}"
        
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": assignment_msg
            }
        })
        
        # Add notification for new assignee
        if to_assignee != 'Unassigned':
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"👋 Hey @{to_assignee}, this ticket is now assigned to you!"
                }
            })
        
        self.add_divider()
        self._add_ticket_details()
        self._add_time_tracking()
        self._add_comments_preview()
        self._add_action_buttons()
        self._add_footer()


class JIRACommentTemplate(JIRATemplateBase):
    """Template for new JIRA comments."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self._build_template()
    
    def _build_template(self) -> None:
        """Build comment template."""
        # Header
        self._add_ticket_header("💬")
        
        # New comment details
        comments = self.ticket.get('comments', [])
        if comments:
            latest_comment = comments[-1]
            author = latest_comment.get('author', 'Unknown')
            text = latest_comment.get('text', '')
            created = latest_comment.get('created', '')
            
            # Format timestamp
            if created:
                try:
                    created_date = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    time_str = created_date.strftime('%I:%M %p')
                except (ValueError, AttributeError):
                    time_str = 'just now'
            else:
                time_str = 'just now'
            
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*💬 New comment by @{author}* _{time_str}_\n> {text}"
                }
            })
        
        self.add_divider()
        self._add_ticket_details()
        
        # Show comment history if multiple comments
        if len(comments) > 1:
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📝 Comment History:* {len(comments)} total comments"
                }
            })
        
        self._add_action_buttons()
        self._add_footer()


class JIRABlockerTemplate(JIRATemplateBase):
    """Template for JIRA blockers identified/resolved."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self._build_template()
    
    def _build_template(self) -> None:
        """Build blocker template."""
        blocker_info = self.data.get('blocker', {})
        blocker_type = blocker_info.get('type', 'identified')  # identified or resolved
        blocker_description = blocker_info.get('description', '')
        
        # Header with appropriate emoji
        emoji = "🚫" if blocker_type == 'identified' else "🎉"
        self._add_ticket_header(emoji)
        
        # Blocker message
        if blocker_type == 'identified':
            blocker_msg = f"*🚫 Blocker Identified*\n{blocker_description}"
            urgency_msg = "\n⚠️ **This ticket is now blocked and needs attention**"
        else:
            blocker_msg = f"*🎉 Blocker Resolved*\n{blocker_description}"
            urgency_msg = "\n✅ **Work can now continue on this ticket**"
        
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": blocker_msg + urgency_msg
            }
        })
        
        self.add_divider()
        self._add_ticket_details()
        self._add_time_tracking()
        
        # Add blocker-specific actions
        self._add_blocker_actions(blocker_type)
        
        self._add_comments_preview()
        self._add_footer()
    
    def _add_blocker_actions(self, blocker_type: str) -> None:
        """Add blocker-specific action buttons."""
        key = self.ticket.get('key', '')
        
        if blocker_type == 'identified':
            buttons = [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🆘 Escalate",
                        "emoji": True
                    },
                    "value": f"escalate_{key}",
                    "action_id": "escalate_blocker",
                    "style": "danger"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "👥 Assign Help",
                        "emoji": True
                    },
                    "value": f"assign_help_{key}",
                    "action_id": "assign_help"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📝 Update Status",
                        "emoji": True
                    },
                    "value": f"update_status_{key}",
                    "action_id": "update_status"
                }
            ]
        else:  # resolved
            buttons = [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "▶️ Resume Work",
                        "emoji": True
                    },
                    "value": f"resume_{key}",
                    "action_id": "resume_work",
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Update Progress",
                        "emoji": True
                    },
                    "value": f"update_progress_{key}",
                    "action_id": "update_progress"
                }
            ]
        
        # Add common buttons
        buttons.extend([
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "👀 View Ticket",
                    "emoji": True
                },
                "url": f"https://jira.company.com/browse/{key}",
                "action_id": "view_ticket"
            }
        ])
        
        self.blocks.append({
            "type": "actions",
            "elements": buttons
        })


class JIRASprintChangeTemplate(JIRATemplateBase):
    """Template for JIRA sprint changes."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self._build_template()
    
    def _build_template(self) -> None:
        """Build sprint change template."""
        sprint_change = self.ticket.get('sprint_change', {})
        from_sprint = sprint_change.get('from', 'Backlog')
        to_sprint = sprint_change.get('to', 'Unknown Sprint')
        change_type = sprint_change.get('type', 'moved')  # moved, added, removed
        
        # Header
        self._add_ticket_header("🏃")
        
        # Sprint change message
        if change_type == 'added':
            sprint_msg = f"*🏃 Added to Sprint:* {to_sprint}"
        elif change_type == 'removed':
            sprint_msg = f"*🏃 Removed from Sprint:* {from_sprint}"
        else:  # moved
            sprint_msg = f"*🏃 Sprint Changed:* {from_sprint} → {to_sprint}"
        
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": sprint_msg
            }
        })
        
        # Add sprint context if available
        sprint_info = self.data.get('sprint_info', {})
        if sprint_info:
            self._add_sprint_context(sprint_info)
        
        self.add_divider()
        self._add_ticket_details()
        self._add_time_tracking()
        self._add_comments_preview()
        self._add_action_buttons()
        self._add_footer()
    
    def _add_sprint_context(self, sprint_info: Dict[str, Any]) -> None:
        """Add sprint context information."""
        sprint_name = sprint_info.get('name', '')
        start_date = sprint_info.get('start_date', '')
        end_date = sprint_info.get('end_date', '')
        capacity = sprint_info.get('capacity', 0)
        committed_points = sprint_info.get('committed_points', 0)
        
        context_text = f"*📊 Sprint Context:*\n"
        
        if start_date and end_date:
            context_text += f"• Duration: {start_date} - {end_date}\n"
        
        if capacity and committed_points:
            context_text += f"• Capacity: {committed_points}/{capacity} story points\n"
        
        if context_text != "*📊 Sprint Context:*\n":
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": context_text.strip()
                }
            })


# Template factory function
def create_jira_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create appropriate JIRA message based on change type."""
    change_type = data.get('change_type', 'updated')
    
    template_map = {
        'status_change': JIRAStatusChangeTemplate,
        'priority_change': JIRAPriorityChangeTemplate,
        'assignment_change': JIRAAssignmentChangeTemplate,
        'comment_added': JIRACommentTemplate,
        'blocker_identified': JIRABlockerTemplate,
        'blocker_resolved': JIRABlockerTemplate,
        'sprint_change': JIRASprintChangeTemplate,
    }
    
    template_class = template_map.get(change_type, JIRATemplateBase)
    template = template_class(data)
    return template.get_message()


# Convenience functions for specific change types
def create_status_change_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create status change message."""
    data['change_type'] = 'status_change'
    return create_jira_message(data)


def create_priority_change_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create priority change message."""
    data['change_type'] = 'priority_change'
    return create_jira_message(data)


def create_assignment_change_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create assignment change message."""
    data['change_type'] = 'assignment_change'
    return create_jira_message(data)


def create_comment_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create comment added message."""
    data['change_type'] = 'comment_added'
    return create_jira_message(data)


def create_blocker_message(data: Dict[str, Any], blocker_type: str = 'identified') -> Dict[str, Any]:
    """Create blocker message."""
    data['change_type'] = f'blocker_{blocker_type}'
    return create_jira_message(data)


def create_sprint_change_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create sprint change message."""
    data['change_type'] = 'sprint_change'
    return create_jira_message(data)