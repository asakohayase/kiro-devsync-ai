"""Standup message template for daily team updates."""

from typing import Dict, List, Any
from ..core.base_template import SlackMessageTemplate
from ..core.status_indicators import StatusType


class StandupTemplate(SlackMessageTemplate):
    """Template for daily standup summary messages."""
    
    REQUIRED_FIELDS = ['date', 'team', 'team_members']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create standup message blocks."""
        blocks = []
        
        # Header with team health
        team_health = data.get('team_health', 0.8)
        health_indicator = self.status_system.get_health_indicator(team_health)
        
        blocks.extend(self._create_header_section(
            f"Daily Standup - {data['team']}", 
            subtitle=f"{data['date']} • {health_indicator.emoji} Team Health: {health_indicator.text}"
        ))
        
        # Sprint progress if available
        if 'sprint_progress' in data:
            sprint = data['sprint_progress']
            progress_block = self.create_progress_section(
                completed=sprint.get('completed', 0),
                total=sprint.get('total', 1),
                label="Sprint Progress"
            )
            blocks.append(progress_block)
        
        # Team statistics
        if 'stats' in data:
            stats = data['stats']
            stats_fields = {
                'PRs Merged': str(stats.get('prs_merged', 0)),
                'PRs Open': str(stats.get('prs_open', 0)),
                'Tickets Closed': str(stats.get('tickets_closed', 0)),
                'Commits': str(stats.get('commits', 0))
            }
            blocks.append(self.create_fields_section(stats_fields))
        
        blocks.append(self.create_divider_block())
        
        # Team member updates
        team_members = data.get('team_members', [])
        for member in team_members[:5]:  # Limit to 5 members to avoid long messages
            member_block = self._create_member_section(member)
            if member_block:
                blocks.append(member_block)
        
        # Action items if present
        if data.get('action_items'):
            blocks.append(self.create_divider_block())
            blocks.append(self._create_action_items_section(data['action_items']))
        
        # Interactive buttons
        actions = [
            {'text': '📊 View Dashboard', 'action_id': 'view_dashboard', 'style': 'primary'},
            {'text': '📝 Add Update', 'action_id': 'add_update'},
            {'text': '🚫 Report Blocker', 'action_id': 'report_blocker', 'style': 'danger'}
        ]
        
        action_block = self._create_action_buttons(actions)
        if action_block:
            blocks.append(action_block)
        
        return blocks
    
    def _create_member_section(self, member: Dict[str, Any]) -> Dict[str, Any]:
        """Create section for individual team member update."""
        name = member.get('name', 'Unknown')
        yesterday = member.get('yesterday', 'No updates')
        today = member.get('today', 'No plans')
        blockers = member.get('blockers', [])
        
        # Status indicator based on blockers
        status_emoji = "🚫" if blockers else "✅"
        
        text_parts = [
            f"*{status_emoji} {name}*",
            f"*Yesterday:* {self._truncate_text(yesterday)}",
            f"*Today:* {self._truncate_text(today)}"
        ]
        
        if blockers:
            blocker_text = ", ".join(blockers[:2])  # Show max 2 blockers
            if len(blockers) > 2:
                blocker_text += f" (+{len(blockers)-2} more)"
            text_parts.append(f"*Blockers:* 🚨 {blocker_text}")
        
        return self.create_section_block("\n".join(text_parts))
    
    def _create_action_items_section(self, action_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create section for action items."""
        items_text = ["*🎯 Action Items:*"]
        
        for item in action_items[:3]:  # Show max 3 action items
            assignee = item.get('assignee', 'Unassigned')
            due_date = item.get('due_date', 'No due date')
            title = item.get('title', 'Untitled task')
            
            items_text.append(f"• {title} - {self._format_user_mention(assignee)} ({due_date})")
        
        if len(action_items) > 3:
            items_text.append(f"• ... and {len(action_items)-3} more items")
        
        return self.create_section_block("\n".join(items_text))