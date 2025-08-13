"""JIRA message formatter for ticket status changes and updates."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from ..core.base_template import SlackMessageTemplate
from ..core.block_kit_builders import BlockKitBuilder, HeaderConfig
from ..core.status_indicators import JIRAStatus, Priority


class JIRAMessageFormatter(SlackMessageTemplate):
    """Specialized formatter for JIRA ticket notifications."""
    
    REQUIRED_FIELDS = ['ticket']
    
    def __init__(self, *args, **kwargs):
        """Initialize with Block Kit builder."""
        super().__init__(*args, **kwargs)
        self.builder = BlockKitBuilder(self.status_system)
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create JIRA notification message blocks."""
        blocks = []
        
        # Handle batch mode
        if 'tickets' in data:
            return self._create_batch_message(data)
        
        ticket_data = data['ticket']
        change_type = data.get('change_type', 'updated')
        
        # Determine JIRA status
        jira_status = self._get_jira_status(ticket_data)
        
        # Build header
        header_config = HeaderConfig(
            title=self._build_ticket_title(ticket_data),
            status=jira_status,
            status_context="jira",
            timestamp=self._parse_timestamp(ticket_data.get('updated')),
            subtitle=self._build_ticket_subtitle(ticket_data, change_type),
            actions=self._get_quick_actions(ticket_data)
        )
        
        blocks.extend(self.builder.build_header(header_config))
        
        # Ticket details
        ticket_fields = self._build_ticket_details(ticket_data)
        if ticket_fields:
            blocks.append(self.builder.build_field_group(ticket_fields))
        
        # Sprint context
        if ticket_data.get('sprint'):
            blocks.append(self._build_sprint_context(ticket_data['sprint']))
        
        # Change-specific content
        change_content = self._build_change_content(change_type, ticket_data, data)
        if change_content:
            blocks.extend(change_content)
        
        # Time tracking
        if ticket_data.get('time_tracking'):
            blocks.append(self._build_time_tracking_section(ticket_data['time_tracking']))
        
        # Related items
        related_content = self._build_related_items(ticket_data)
        if related_content:
            blocks.extend(related_content)
        
        # Main actions
        blocks.append(self.builder.build_divider())
        main_actions = self._get_main_actions(jira_status, ticket_data)
        if main_actions:
            blocks.append(self.builder.build_action_buttons(main_actions))
        
        return blocks
    
    def _create_batch_message(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create batch message for multiple tickets."""
        blocks = []
        tickets = data['tickets']
        batch_type = data.get('batch_type', 'sprint_update')
        
        # Batch header
        header_config = HeaderConfig(
            title=f"JIRA Update - {len(tickets)} Tickets",
            status="info",
            timestamp=datetime.now(),
            subtitle=f"Batch type: {batch_type.replace('_', ' ').title()}"
        )
        
        blocks.extend(self.builder.build_header(header_config))
        
        # Summary statistics
        stats = self._calculate_batch_stats(tickets)
        blocks.append(self.builder.build_field_group(stats))
        
        blocks.append(self.builder.build_divider())
        
        # Individual ticket summaries
        for i, ticket in enumerate(tickets[:8]):  # Show max 8 tickets
            ticket_summary = self._build_ticket_summary(ticket, i + 1)
            blocks.append(ticket_summary)
        
        if len(tickets) > 8:
            blocks.append(self.builder.build_section({
                "text": f"... and {len(tickets) - 8} more tickets"
            }))
        
        # Batch actions
        batch_actions = [
            {"label": "📊 JIRA Dashboard", "url": data.get('dashboard_url', '#')},
            {"label": "📈 Sprint Report", "action_id": "view_sprint_report"}
        ]
        blocks.append(self.builder.build_action_buttons(batch_actions))
        
        return blocks
    
    def _get_jira_status(self, ticket_data: Dict[str, Any]) -> str:
        """Determine JIRA status from ticket data."""
        status = ticket_data.get('status', {})
        if isinstance(status, dict):
            status_name = status.get('name', '').lower()
        else:
            status_name = str(status).lower()
        
        # Map common JIRA statuses
        status_mapping = {
            'to do': 'todo',
            'todo': 'todo',
            'open': 'todo',
            'in progress': 'in_progress',
            'in development': 'in_progress',
            'in review': 'in_review',
            'code review': 'in_review',
            'done': 'done',
            'closed': 'done',
            'resolved': 'done',
            'blocked': 'blocked',
            'cancelled': 'cancelled',
            'canceled': 'cancelled'
        }
        
        return status_mapping.get(status_name, 'todo')
    
    def _build_ticket_title(self, ticket_data: Dict[str, Any]) -> str:
        """Build ticket title with key and summary."""
        key = ticket_data.get('key', 'UNKNOWN')
        summary = ticket_data.get('summary', 'No summary')
        return f"{key}: {summary}"
    
    def _build_ticket_subtitle(self, ticket_data: Dict[str, Any], change_type: str) -> str:
        """Build ticket subtitle with change context."""
        parts = []
        
        # Issue type
        issue_type = ticket_data.get('issue_type', {})
        if isinstance(issue_type, dict):
            type_name = issue_type.get('name', 'Task')
        else:
            type_name = str(issue_type)
        parts.append(f"📋 {type_name}")
        
        # Change type
        change_descriptions = {
            'status_change': 'Status updated',
            'priority_change': 'Priority changed',
            'assignment_change': 'Assignment updated',
            'comment_added': 'New comment',
            'sprint_change': 'Sprint updated',
            'created': 'Created',
            'updated': 'Updated'
        }
        parts.append(change_descriptions.get(change_type, 'Updated'))
        
        return " • ".join(parts)
    
    def _build_ticket_details(self, ticket_data: Dict[str, Any]) -> Dict[str, str]:
        """Build ticket details fields."""
        fields = {}
        
        # Priority
        priority_data = ticket_data.get('priority', {})
        if isinstance(priority_data, dict):
            priority_name = priority_data.get('name', '').lower()
        else:
            priority_name = str(priority_data).lower()
        
        if priority_name:
            try:
                priority = Priority(priority_name)
                priority_indicator = self.status_system.get_priority_indicator(priority)
                fields['Priority'] = f"{priority_indicator.emoji} {priority_indicator.text}"
            except ValueError:
                fields['Priority'] = priority_name.title()
        
        # Assignee
        assignee = ticket_data.get('assignee')
        if assignee:
            if isinstance(assignee, dict):
                assignee_name = assignee.get('display_name', assignee.get('name', 'Unknown'))
            else:
                assignee_name = str(assignee)
            fields['Assignee'] = self.builder.build_user_mention(assignee_name)
        else:
            fields['Assignee'] = "Unassigned"
        
        # Reporter
        reporter = ticket_data.get('reporter')
        if reporter:
            if isinstance(reporter, dict):
                reporter_name = reporter.get('display_name', reporter.get('name', 'Unknown'))
            else:
                reporter_name = str(reporter)
            fields['Reporter'] = self.builder.build_user_mention(reporter_name)
        
        # Story points
        story_points = ticket_data.get('story_points')
        if story_points:
            fields['Story Points'] = f"📊 {story_points} points"
        
        # Components
        components = ticket_data.get('components', [])
        if components:
            component_names = []
            for comp in components[:3]:
                if isinstance(comp, dict):
                    component_names.append(comp.get('name', 'Unknown'))
                else:
                    component_names.append(str(comp))
            fields['Components'] = ", ".join([f"`{name}`" for name in component_names])
            if len(components) > 3:
                fields['Components'] += f" (+{len(components)-3} more)"
        
        # Labels
        labels = ticket_data.get('labels', [])
        if labels:
            label_list = labels[:3]
            fields['Labels'] = ", ".join([f"`{label}`" for label in label_list])
            if len(labels) > 3:
                fields['Labels'] += f" (+{len(labels)-3} more)"
        
        return fields
    
    def _build_sprint_context(self, sprint_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build sprint context section."""
        content_parts = ["*🏃 Sprint Context:*"]
        
        sprint_name = sprint_data.get('name', 'Unknown Sprint')
        sprint_state = sprint_data.get('state', 'active')
        
        state_emoji = {
            'active': '🟢',
            'closed': '✅',
            'future': '⏳'
        }.get(sprint_state, '📋')
        
        content_parts.append(f"{state_emoji} **{sprint_name}** ({sprint_state})")
        
        # Sprint dates
        start_date = sprint_data.get('start_date')
        end_date = sprint_data.get('end_date')
        if start_date and end_date:
            content_parts.append(f"📅 {start_date} → {end_date}")
        
        # Sprint progress
        if sprint_data.get('completed_issues') is not None and sprint_data.get('total_issues'):
            completed = sprint_data['completed_issues']
            total = sprint_data['total_issues']
            progress_indicator = self.status_system.create_progress_indicator(completed, total)
            content_parts.append(f"📊 Progress: {progress_indicator.emoji} {progress_indicator.text}")
        
        return self.builder.build_section({"text": "\n".join(content_parts)})
    
    def _build_change_content(self, change_type: str, ticket_data: Dict[str, Any], data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build content specific to the change type."""
        blocks = []
        
        if change_type == 'status_change':
            from_status = data.get('from_status', 'Unknown')
            to_status = data.get('to_status', 'Unknown')
            
            from_indicator = self.status_system.get_indicator_by_string(from_status, "jira")
            to_indicator = self.status_system.get_indicator_by_string(to_status, "jira")
            
            content = f"*Status Transition:*\n{from_indicator.emoji} {from_indicator.text} → {to_indicator.emoji} {to_indicator.text}"
            blocks.append(self.builder.build_section({"text": content}))
        
        elif change_type == 'priority_change':
            from_priority = data.get('from_priority', 'Unknown')
            to_priority = data.get('to_priority', 'Unknown')
            
            content = f"*Priority Change:*\n{from_priority} → {to_priority}"
            if to_priority.lower() in ['highest', 'blocker']:
                content += "\n⚠️ *High priority - requires immediate attention*"
            
            blocks.append(self.builder.build_section({"text": content}))
        
        elif change_type == 'assignment_change':
            from_assignee = data.get('from_assignee', 'Unassigned')
            to_assignee = data.get('to_assignee', 'Unassigned')
            
            from_mention = self.builder.build_user_mention(from_assignee) if from_assignee != 'Unassigned' else 'Unassigned'
            to_mention = self.builder.build_user_mention(to_assignee) if to_assignee != 'Unassigned' else 'Unassigned'
            
            content = f"*Assignment Change:*\n{from_mention} → {to_mention}"
            blocks.append(self.builder.build_section({"text": content}))
        
        elif change_type == 'comment_added':
            comment = data.get('comment', {})
            author = comment.get('author', 'Unknown')
            body = comment.get('body', 'No comment text')
            
            content = f"*💬 New Comment by {self.builder.build_user_mention(author)}:*\n{self._truncate_text(body, 300)}"
            blocks.append(self.builder.build_section({"text": content}))
        
        return blocks
    
    def _build_time_tracking_section(self, time_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build time tracking section."""
        content_parts = ["*⏱️ Time Tracking:*"]
        
        # Original estimate
        original_estimate = time_data.get('original_estimate')
        if original_estimate:
            content_parts.append(f"📋 Original: {self._format_time(original_estimate)}")
        
        # Time spent
        time_spent = time_data.get('time_spent')
        if time_spent:
            content_parts.append(f"✅ Logged: {self._format_time(time_spent)}")
        
        # Remaining estimate
        remaining_estimate = time_data.get('remaining_estimate')
        if remaining_estimate:
            content_parts.append(f"⏳ Remaining: {self._format_time(remaining_estimate)}")
        
        # Progress calculation
        if original_estimate and time_spent:
            try:
                progress = (time_spent / original_estimate) * 100
                if progress > 100:
                    content_parts.append("⚠️ *Over estimate*")
                elif progress > 80:
                    content_parts.append("🟡 *Near completion*")
            except (ZeroDivisionError, TypeError):
                pass
        
        return self.builder.build_section({"text": "\n".join(content_parts)})
    
    def _build_related_items(self, ticket_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build related items section."""
        blocks = []
        
        # Related PRs
        if ticket_data.get('pull_requests'):
            pr_content = ["*🔗 Related Pull Requests:*"]
            for pr in ticket_data['pull_requests'][:3]:
                pr_title = pr.get('title', 'No title')
                pr_url = pr.get('url', '#')
                pr_status = pr.get('status', 'open')
                status_emoji = {'open': '🔄', 'merged': '✅', 'closed': '⛔'}.get(pr_status, '📝')
                pr_content.append(f"• {status_emoji} {self.builder.build_url_link(pr_url, pr_title)}")
            
            blocks.append(self.builder.build_section({"text": "\n".join(pr_content)}))
        
        # Documentation links
        if ticket_data.get('documentation'):
            doc_content = ["*📚 Documentation:*"]
            for doc in ticket_data['documentation'][:2]:
                doc_title = doc.get('title', 'Documentation')
                doc_url = doc.get('url', '#')
                doc_content.append(f"• {self.builder.build_url_link(doc_url, doc_title)}")
            
            blocks.append(self.builder.build_section({"text": "\n".join(doc_content)}))
        
        # Linked issues
        if ticket_data.get('linked_issues'):
            linked_content = ["*🔗 Linked Issues:*"]
            for issue in ticket_data['linked_issues'][:3]:
                issue_key = issue.get('key', 'UNKNOWN')
                issue_summary = issue.get('summary', 'No summary')
                issue_url = issue.get('url', '#')
                link_type = issue.get('link_type', 'relates to')
                linked_content.append(f"• {link_type}: {self.builder.build_url_link(issue_url, f'{issue_key} - {issue_summary}')}")
            
            blocks.append(self.builder.build_section({"text": "\n".join(linked_content)}))
        
        return blocks
    
    def _get_quick_actions(self, ticket_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get quick actions for header."""
        actions = []
        
        # View ticket
        if ticket_data.get('url'):
            actions.append({
                "label": "👀 View",
                "url": ticket_data['url']
            })
        
        return actions
    
    def _get_main_actions(self, jira_status: str, ticket_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get main action buttons based on ticket status."""
        actions = []
        ticket_key = ticket_data.get('key', '')
        
        # Status-specific actions
        if jira_status == 'todo':
            actions.extend([
                {
                    "label": "▶️ Start Work",
                    "action_id": "start_work",
                    "value": ticket_key,
                    "style": "primary"
                },
                {
                    "label": "👤 Assign to Me",
                    "action_id": "assign_to_me",
                    "value": ticket_key
                }
            ])
        
        elif jira_status == 'in_progress':
            actions.extend([
                {
                    "label": "✅ Mark Done",
                    "action_id": "mark_done",
                    "value": ticket_key,
                    "style": "primary"
                },
                {
                    "label": "🚫 Block",
                    "action_id": "block_ticket",
                    "value": ticket_key,
                    "style": "danger"
                }
            ])
        
        elif jira_status == 'in_review':
            actions.extend([
                {
                    "label": "✅ Approve",
                    "action_id": "approve_ticket",
                    "value": ticket_key,
                    "style": "primary"
                },
                {
                    "label": "🔄 Back to Progress",
                    "action_id": "back_to_progress",
                    "value": ticket_key
                }
            ])
        
        # Common actions
        actions.extend([
            {
                "label": "💬 Comment",
                "action_id": "add_comment",
                "value": ticket_key
            },
            {
                "label": "⏱️ Log Time",
                "action_id": "log_time",
                "value": ticket_key
            }
        ])
        
        return actions
    
    def _calculate_batch_stats(self, tickets: List[Dict[str, Any]]) -> Dict[str, str]:
        """Calculate statistics for batch of tickets."""
        stats = {}
        
        # Status distribution
        status_counts = {}
        for ticket in tickets:
            status = self._get_jira_status(ticket)
            status_counts[status] = status_counts.get(status, 0) + 1
        
        status_parts = []
        for status, count in status_counts.items():
            indicator = self.status_system.get_indicator_by_string(status, "jira")
            status_parts.append(f"{indicator.emoji} {count}")
        
        stats['Status Distribution'] = " • ".join(status_parts)
        
        # Story points
        total_points = sum(ticket.get('story_points', 0) for ticket in tickets if ticket.get('story_points'))
        if total_points > 0:
            stats['Total Story Points'] = f"📊 {total_points} points"
        
        # Assignees
        assignees = set()
        for ticket in tickets:
            assignee = ticket.get('assignee')
            if assignee:
                if isinstance(assignee, dict):
                    assignees.add(assignee.get('name', 'Unknown'))
                else:
                    assignees.add(str(assignee))
        
        stats['Assignees'] = f"{len(assignees)} team members"
        
        return stats
    
    def _build_ticket_summary(self, ticket: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Build summary for individual ticket in batch."""
        key = ticket.get('key', 'UNKNOWN')
        summary = ticket.get('summary', 'No summary')
        status = self._get_jira_status(ticket)
        indicator = self.status_system.get_indicator_by_string(status, "jira")
        
        content = f"{indicator.emoji} *{index}. {key}*: {self._truncate_text(summary, 60)}"
        
        assignee = ticket.get('assignee')
        if assignee:
            if isinstance(assignee, dict):
                assignee_name = assignee.get('display_name', assignee.get('name', 'Unknown'))
            else:
                assignee_name = str(assignee)
            content += f" - {self.builder.build_user_mention(assignee_name)}"
        
        return self.builder.build_section({"text": content})
    
    def _format_time(self, seconds: int) -> str:
        """Format time in seconds to human readable format."""
        if seconds < 3600:  # Less than 1 hour
            minutes = seconds // 60
            return f"{minutes}m"
        elif seconds < 86400:  # Less than 1 day
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
        else:  # Days
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h" if hours > 0 else f"{days}d"
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime."""
        if not timestamp_str:
            return None
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None