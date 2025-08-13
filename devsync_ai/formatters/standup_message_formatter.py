"""Standup message formatter for daily team summaries."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from ..core.base_template import SlackMessageTemplate
from ..core.block_kit_builders import BlockKitBuilder, HeaderConfig
from ..core.status_indicators import HealthStatus


class StandupMessageFormatter(SlackMessageTemplate):
    """Specialized formatter for daily standup summaries."""
    
    REQUIRED_FIELDS = ['date', 'team']
    
    def __init__(self, *args, **kwargs):
        """Initialize with Block Kit builder."""
        super().__init__(*args, **kwargs)
        self.builder = BlockKitBuilder(self.status_system)
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create standup summary message blocks."""
        blocks = []
        
        # Team health status
        team_health = data.get('team_health', 0.8)
        health_status = self._get_health_status(team_health)
        
        # Build header
        header_config = HeaderConfig(
            title=f"Daily Standup - {data['team']}",
            status=health_status,
            status_context="health",
            timestamp=datetime.now(),
            subtitle=f"{data['date']} • Team Health: {self._format_health_score(team_health)}",
            actions=self._get_header_actions(data)
        )
        
        blocks.extend(self.builder.build_header(header_config))
        
        # Team statistics overview
        if data.get('stats'):
            blocks.append(self._build_team_stats_section(data['stats']))
        
        # Sprint progress
        if data.get('sprint_progress'):
            blocks.append(self._build_sprint_progress_section(data['sprint_progress']))
        
        blocks.append(self.builder.build_divider())
        
        # Team member sections
        team_members = data.get('team_members', [])
        if team_members:
            blocks.extend(self._build_team_member_sections(team_members))
        
        # Action items
        if data.get('action_items'):
            blocks.append(self.builder.build_divider())
            blocks.append(self._build_action_items_section(data['action_items']))
        
        # Blockers highlight
        blockers = self._extract_blockers(team_members)
        if blockers:
            blocks.append(self._build_blockers_section(blockers))
        
        # Interactive elements
        blocks.append(self.builder.build_divider())
        main_actions = self._get_main_actions(data)
        if main_actions:
            blocks.append(self.builder.build_action_buttons(main_actions))
        
        return blocks
    
    def _get_health_status(self, health_score: float) -> str:
        """Convert health score to status string."""
        if health_score >= 0.8:
            return "healthy"
        elif health_score >= 0.6:
            return "warning"
        elif health_score >= 0.4:
            return "warning"
        else:
            return "critical"
    
    def _format_health_score(self, health_score: float) -> str:
        """Format health score for display."""
        percentage = int(health_score * 100)
        if health_score >= 0.8:
            return f"Healthy ({percentage}%)"
        elif health_score >= 0.6:
            return f"Fair ({percentage}%)"
        elif health_score >= 0.4:
            return f"Poor ({percentage}%)"
        else:
            return f"Critical ({percentage}%)"
    
    def _build_team_stats_section(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Build team statistics section."""
        stats_fields = {}
        
        # PR statistics
        prs_merged = stats.get('prs_merged', 0)
        prs_open = stats.get('prs_open', 0)
        if prs_merged or prs_open:
            stats_fields['Pull Requests'] = f"✅ {prs_merged} merged • 🔄 {prs_open} open"
        
        # Ticket statistics
        tickets_closed = stats.get('tickets_closed', 0)
        tickets_in_progress = stats.get('tickets_in_progress', 0)
        if tickets_closed or tickets_in_progress:
            stats_fields['JIRA Tickets'] = f"✅ {tickets_closed} closed • 🔄 {tickets_in_progress} in progress"
        
        # Code activity
        commits = stats.get('commits', 0)
        if commits:
            stats_fields['Commits'] = f"📝 {commits} commits"
        
        # Code review
        reviews_given = stats.get('reviews_given', 0)
        reviews_received = stats.get('reviews_received', 0)
        if reviews_given or reviews_received:
            stats_fields['Code Reviews'] = f"👀 {reviews_given} given • 📥 {reviews_received} received"
        
        # Deployment stats
        deployments = stats.get('deployments', 0)
        if deployments:
            deployment_success = stats.get('deployment_success_rate', 100)
            stats_fields['Deployments'] = f"🚀 {deployments} deployments ({deployment_success}% success)"
        
        return self.builder.build_field_group(stats_fields)
    
    def _build_sprint_progress_section(self, sprint_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build sprint progress section."""
        content_parts = ["*🏃 Sprint Progress:*"]
        
        # Sprint name and dates
        sprint_name = sprint_data.get('name', 'Current Sprint')
        start_date = sprint_data.get('start_date')
        end_date = sprint_data.get('end_date')
        
        content_parts.append(f"**{sprint_name}**")
        if start_date and end_date:
            content_parts.append(f"📅 {start_date} → {end_date}")
        
        # Progress visualization
        completed = sprint_data.get('completed', 0)
        total = sprint_data.get('total', 1)
        if total > 0:
            progress_indicator = self.status_system.create_progress_indicator(completed, total)
            content_parts.append(f"📊 {progress_indicator.emoji} {progress_indicator.text}")
            content_parts.append(f"`{progress_indicator.description}`")
        
        # Story points
        completed_points = sprint_data.get('completed_points', 0)
        total_points = sprint_data.get('total_points', 0)
        if total_points > 0:
            content_parts.append(f"📈 Story Points: {completed_points}/{total_points}")
        
        # Burndown info
        if sprint_data.get('burndown_trend'):
            trend = sprint_data['burndown_trend']
            trend_emoji = {'ahead': '📈', 'on_track': '➡️', 'behind': '📉'}.get(trend, '📊')
            content_parts.append(f"{trend_emoji} Burndown: {trend.replace('_', ' ').title()}")
        
        return self.builder.build_section({"text": "\n".join(content_parts)})
    
    def _build_team_member_sections(self, team_members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build individual team member sections."""
        blocks = []
        
        # Group members by status (blockers first)
        blocked_members = [m for m in team_members if m.get('blockers')]
        regular_members = [m for m in team_members if not m.get('blockers')]
        
        # Show blocked members first with warning
        for member in blocked_members:
            blocks.append(self._build_member_section(member, highlight_blockers=True))
        
        # Show regular members
        for member in regular_members[:8]:  # Limit to 8 total members
            blocks.append(self._build_member_section(member))
        
        # Show count if more members
        total_shown = len(blocked_members) + min(len(regular_members), 8)
        if len(team_members) > total_shown:
            remaining = len(team_members) - total_shown
            blocks.append(self.builder.build_section({
                "text": f"_... and {remaining} more team members_"
            }))
        
        return blocks
    
    def _build_member_section(self, member: Dict[str, Any], highlight_blockers: bool = False) -> Dict[str, Any]:
        """Build section for individual team member."""
        name = member.get('name', 'Unknown')
        yesterday = member.get('yesterday', 'No updates provided')
        today = member.get('today', 'No plans specified')
        blockers = member.get('blockers', [])
        
        # Status indicator
        if blockers:
            status_emoji = "🚫" if highlight_blockers else "⚠️"
            member_status = "BLOCKED" if highlight_blockers else "Has Blockers"
        else:
            status_emoji = "✅"
            member_status = "On Track"
        
        # Build content
        content_parts = [f"*{status_emoji} {name}* - {member_status}"]
        
        # Yesterday's work
        content_parts.append(f"*Yesterday:* {self._truncate_text(yesterday, 120)}")
        
        # Today's plan
        content_parts.append(f"*Today:* {self._truncate_text(today, 120)}")
        
        # Blockers (with emphasis if highlighting)
        if blockers:
            blocker_text = ", ".join(blockers[:2])  # Show max 2 blockers
            if len(blockers) > 2:
                blocker_text += f" (+{len(blockers)-2} more)"
            
            if highlight_blockers:
                content_parts.append(f"*🚨 BLOCKERS:* {blocker_text}")
            else:
                content_parts.append(f"*Blockers:* {blocker_text}")
        
        # Additional metrics if available
        metrics = []
        if member.get('commits'):
            metrics.append(f"📝 {member['commits']} commits")
        if member.get('prs_reviewed'):
            metrics.append(f"👀 {member['prs_reviewed']} reviews")
        if member.get('tickets_completed'):
            metrics.append(f"✅ {member['tickets_completed']} tickets")
        
        if metrics:
            content_parts.append(f"*Metrics:* {' • '.join(metrics)}")
        
        return self.builder.build_section({"text": "\n".join(content_parts)})
    
    def _build_action_items_section(self, action_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build action items section."""
        content_parts = ["*🎯 Action Items:*"]
        
        # Sort by priority and due date
        sorted_items = sorted(action_items, key=lambda x: (
            x.get('priority', 'medium') == 'high',
            x.get('due_date', '9999-12-31')
        ), reverse=True)
        
        for item in sorted_items[:5]:  # Show max 5 action items
            title = item.get('title', 'Untitled task')
            assignee = item.get('assignee', 'Unassigned')
            due_date = item.get('due_date', 'No due date')
            priority = item.get('priority', 'medium')
            
            # Priority indicator
            priority_emoji = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }.get(priority, '⚪')
            
            # Due date formatting
            if due_date != 'No due date':
                try:
                    due_dt = datetime.fromisoformat(due_date)
                    today = datetime.now().date()
                    due_date_obj = due_dt.date()
                    
                    if due_date_obj < today:
                        due_display = f"⚠️ Overdue ({due_date})"
                    elif due_date_obj == today:
                        due_display = "📅 Due today"
                    else:
                        due_display = f"📅 Due {due_date}"
                except (ValueError, AttributeError):
                    due_display = f"📅 {due_date}"
            else:
                due_display = due_date
            
            assignee_mention = self.builder.build_user_mention(assignee) if assignee != 'Unassigned' else 'Unassigned'
            content_parts.append(f"• {priority_emoji} {title} - {assignee_mention} ({due_display})")
        
        if len(action_items) > 5:
            content_parts.append(f"• ... and {len(action_items)-5} more action items")
        
        return self.builder.build_section({"text": "\n".join(content_parts)})
    
    def _extract_blockers(self, team_members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract all blockers from team members."""
        all_blockers = []
        
        for member in team_members:
            member_blockers = member.get('blockers', [])
            for blocker in member_blockers:
                all_blockers.append({
                    'blocker': blocker,
                    'member': member.get('name', 'Unknown'),
                    'severity': member.get('blocker_severity', 'medium')
                })
        
        return all_blockers
    
    def _build_blockers_section(self, blockers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build blockers highlight section."""
        content_parts = ["*🚨 Team Blockers Summary:*"]
        
        # Group by severity
        high_blockers = [b for b in blockers if b.get('severity') == 'high']
        medium_blockers = [b for b in blockers if b.get('severity') == 'medium']
        low_blockers = [b for b in blockers if b.get('severity') == 'low']
        
        # Show high priority blockers first
        for blocker_info in high_blockers[:3]:
            member = blocker_info['member']
            blocker = blocker_info['blocker']
            content_parts.append(f"• 🔴 **{member}**: {blocker}")
        
        # Show medium priority blockers
        for blocker_info in medium_blockers[:2]:
            member = blocker_info['member']
            blocker = blocker_info['blocker']
            content_parts.append(f"• 🟡 **{member}**: {blocker}")
        
        # Show count if more blockers
        total_shown = min(len(high_blockers), 3) + min(len(medium_blockers), 2)
        if len(blockers) > total_shown:
            remaining = len(blockers) - total_shown
            content_parts.append(f"• ... and {remaining} more blockers")
        
        content_parts.append("\n⚠️ *These blockers need immediate attention to maintain team velocity.*")
        
        return self.builder.build_section({"text": "\n".join(content_parts)})
    
    def _get_header_actions(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get header-level quick actions."""
        actions = []
        
        # Dashboard link
        if data.get('dashboard_url'):
            actions.append({
                "label": "📊 Dashboard",
                "url": data['dashboard_url']
            })
        
        return actions
    
    def _get_main_actions(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get main interactive actions."""
        actions = [
            {
                "label": "📝 Add Update",
                "action_id": "add_standup_update",
                "style": "primary"
            },
            {
                "label": "🚫 Report Blocker",
                "action_id": "report_blocker",
                "style": "danger"
            },
            {
                "label": "📈 View Metrics",
                "action_id": "view_team_metrics"
            },
            {
                "label": "🎯 Manage Actions",
                "action_id": "manage_action_items"
            }
        ]
        
        # Add sprint-specific actions
        if data.get('sprint_progress'):
            actions.append({
                "label": "🏃 Sprint Board",
                "action_id": "view_sprint_board"
            })
        
        return actions