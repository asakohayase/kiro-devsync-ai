"""Standup message template for daily team updates."""

from typing import Dict, List, Any
from ..core.base_template import SlackMessageTemplate
from ..core.status_indicators import StatusType, HealthStatus


class StandupTemplate(SlackMessageTemplate):
    """Template for daily standup summary messages with enhanced team health indicators."""
    
    REQUIRED_FIELDS = ['date', 'team', 'team_members']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create standup message blocks with enhanced team health visualization."""
        blocks = []
        
        # Enhanced header with team health section
        blocks.extend(self._create_header_section(
            f"Daily Standup - {data['team']}", 
            subtitle=f"{data['date']}"
        ))
        
        # Team health section with color-coded indicators
        team_health_block = self.create_team_health_section(data)
        if team_health_block:
            blocks.append(team_health_block)
        
        # Sprint progress visualization
        if 'sprint_progress' in data:
            progress_block = self.create_progress_bars(data['sprint_progress'])
            if progress_block:
                blocks.append(progress_block)
        
        # Enhanced team summary statistics with responsive design
        summary_stats_blocks = self.create_summary_statistics_display(data)
        blocks.extend(summary_stats_blocks)
        
        blocks.append(self.create_divider_block())
        
        # Team member sections with yesterday/today/blockers
        member_blocks = self.create_member_sections(data.get('team_members', []))
        blocks.extend(member_blocks)
        
        # Action items if present
        if data.get('action_items'):
            blocks.append(self.create_divider_block())
            blocks.append(self._create_action_items_section(data['action_items']))
        
        # Interactive dashboard buttons
        action_block = self._create_interactive_dashboard_buttons()
        if action_block:
            blocks.append(action_block)
        
        # Apply responsive design optimizations for mobile and desktop
        blocks = self._ensure_mobile_responsive_design(blocks)
        
        return blocks
    
    def create_team_health_section(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create team health section with color-coded status indicators and emoji visualization.
        
        Requirements: 1.1, 5.2 - Team health indicators with color-coded status and emoji-based visualization
        """
        team_health_score = data.get('team_health', 0.8)
        health_indicator = self.status_system.get_health_indicator(team_health_score)
        
        # Calculate health metrics
        total_members = len(data.get('team_members', []))
        blocked_members = len([m for m in data.get('team_members', []) if m.get('blockers')])
        active_members = total_members - blocked_members
        
        # Create health status text with consistent emoji indicators
        health_text_parts = [
            f"*{health_indicator.emoji} Team Health: {health_indicator.text}*",
            f"📊 Health Score: {int(team_health_score * 100)}%"
        ]
        
        # Add member status breakdown with emoji indicators
        if total_members > 0:
            health_text_parts.extend([
                f"✅ Active Members: {active_members}/{total_members}",
                f"🚫 Blocked Members: {blocked_members}/{total_members}" if blocked_members > 0 else "🚫 No Blockers"
            ])
        
        # Add velocity indicators if available
        if 'velocity' in data:
            velocity = data['velocity']
            velocity_emoji = "🚀" if velocity > 0.8 else "⚡" if velocity > 0.6 else "🐌"
            health_text_parts.append(f"{velocity_emoji} Team Velocity: {int(velocity * 100)}%")
        
        return self.create_section_block("\n".join(health_text_parts))
    
    def create_progress_bars(self, sprint_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create sprint progress visualization with progress bars.
        
        Requirements: 1.2 - Sprint progress visualization with progress bars
        """
        completed = sprint_data.get('completed', 0)
        total = sprint_data.get('total', 1)
        
        # Create main sprint progress indicator
        progress_indicator = self.status_system.create_progress_indicator(completed, total)
        
        progress_text_parts = [
            f"*🏃‍♂️ Sprint Progress*",
            f"{progress_indicator.emoji} {progress_indicator.text}",
            f"`{progress_indicator.description}`"
        ]
        
        # Add breakdown by story points if available
        if 'story_points' in sprint_data:
            sp_completed = sprint_data['story_points'].get('completed', 0)
            sp_total = sprint_data['story_points'].get('total', 1)
            sp_indicator = self.status_system.create_progress_indicator(sp_completed, sp_total)
            progress_text_parts.extend([
                "",
                f"📊 Story Points: {sp_indicator.emoji} {sp_indicator.text}",
                f"`{sp_indicator.description}`"
            ])
        
        # Add days remaining if available
        if 'days_remaining' in sprint_data:
            days = sprint_data['days_remaining']
            days_emoji = "⏰" if days > 3 else "🚨" if days > 0 else "🏁"
            progress_text_parts.append(f"{days_emoji} Days Remaining: {days}")
        
        return self.create_section_block("\n".join(progress_text_parts))
    
    def create_member_sections(self, team_members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create sections for team members with yesterday/today/blockers organization.
        
        Requirements: 1.3, 1.4 - Member sections with yesterday/today/blockers and action items
        """
        member_blocks = []
        
        # Limit to 5 members to avoid overly long messages
        for member in team_members[:5]:
            member_block = self._create_enhanced_member_section(member)
            if member_block:
                member_blocks.append(member_block)
        
        # Add summary if there are more members
        if len(team_members) > 5:
            remaining_count = len(team_members) - 5
            summary_block = self.create_context_block([
                f"📋 ... and {remaining_count} more team members"
            ])
            member_blocks.append(summary_block)
        
        return member_blocks
    
    def _create_enhanced_member_section(self, member: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced section for individual team member with structured updates."""
        name = member.get('name', 'Unknown')
        yesterday = member.get('yesterday', 'No updates')
        today = member.get('today', 'No plans')
        blockers = member.get('blockers', [])
        
        # Enhanced status indicator based on member status
        if blockers:
            status_emoji = "🚫"
            status_color = "danger"
        elif member.get('on_track', True):
            status_emoji = "✅"
            status_color = "good"
        else:
            status_emoji = "⚠️"
            status_color = "warning"
        
        # Structure the member update with clear sections
        text_parts = [
            f"*{status_emoji} {name}*"
        ]
        
        # Yesterday section with truncation
        if yesterday and yesterday != 'No updates':
            text_parts.append(f"*📅 Yesterday:* {self._truncate_text(yesterday, 100)}")
        
        # Today section with truncation
        if today and today != 'No plans':
            text_parts.append(f"*🎯 Today:* {self._truncate_text(today, 100)}")
        
        # Blockers section with priority indicators
        if blockers:
            if len(blockers) == 1:
                text_parts.append(f"*🚨 Blocker:* {self._truncate_text(blockers[0], 80)}")
            else:
                blocker_text = ", ".join(blockers[:2])
                if len(blockers) > 2:
                    blocker_text += f" (+{len(blockers)-2} more)"
                text_parts.append(f"*🚨 Blockers:* {self._truncate_text(blocker_text, 80)}")
        
        # Add completion metrics if available
        if 'completed_tasks' in member:
            completed = member['completed_tasks']
            text_parts.append(f"*✅ Completed:* {completed} tasks")
        
        return self.create_section_block("\n".join(text_parts))
    
    def _create_team_summary_statistics(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Create team summary statistics display with consistent formatting."""
        if not stats:
            return None
        
        # Enhanced statistics with emoji indicators
        stats_fields = {}
        
        # PR statistics
        if 'prs_merged' in stats or 'prs_open' in stats:
            prs_merged = stats.get('prs_merged', 0)
            prs_open = stats.get('prs_open', 0)
            stats_fields['🔀 PRs'] = f"✅ {prs_merged} merged, 🔄 {prs_open} open"
        
        # Ticket statistics
        if 'tickets_closed' in stats or 'tickets_open' in stats:
            tickets_closed = stats.get('tickets_closed', 0)
            tickets_open = stats.get('tickets_open', 0)
            stats_fields['🎫 Tickets'] = f"✅ {tickets_closed} closed, 🔄 {tickets_open} open"
        
        # Commit statistics
        if 'commits' in stats:
            commits = stats.get('commits', 0)
            commit_emoji = "🚀" if commits > 20 else "📝" if commits > 5 else "💤"
            stats_fields['📊 Commits'] = f"{commit_emoji} {commits} commits"
        
        # Code review statistics
        if 'reviews_given' in stats:
            reviews = stats.get('reviews_given', 0)
            stats_fields['👀 Reviews'] = f"✅ {reviews} reviews given"
        
        # Deployment statistics
        if 'deployments' in stats:
            deployments = stats.get('deployments', 0)
            deploy_emoji = "🚀" if deployments > 0 else "⏸️"
            stats_fields['🚀 Deployments'] = f"{deploy_emoji} {deployments} deployments"
        
        return self.create_fields_section(stats_fields) if stats_fields else None
    
    def _create_interactive_dashboard_buttons(self) -> Dict[str, Any]:
        """Create interactive dashboard buttons for common standup actions with responsive design.
        
        Requirements: 1.5, 1.6, 5.4 - Interactive dashboard buttons, summary statistics, responsive design
        """
        # Primary action buttons for common standup workflows
        primary_actions = [
            {
                'text': '📊 Dashboard', 
                'action_id': 'view_team_dashboard', 
                'style': 'primary',
                'value': 'dashboard'
            },
            {
                'text': '📝 Update', 
                'action_id': 'add_standup_update',
                'value': 'add_update'
            },
            {
                'text': '🚫 Blocker', 
                'action_id': 'report_team_blocker', 
                'style': 'danger',
                'value': 'report_blocker'
            }
        ]
        
        # Secondary action buttons for additional functionality
        secondary_actions = [
            {
                'text': '📈 Metrics', 
                'action_id': 'view_sprint_metrics',
                'value': 'sprint_metrics'
            },
            {
                'text': '🎯 Goals', 
                'action_id': 'view_sprint_goals',
                'value': 'sprint_goals'
            },
            {
                'text': '⚡ Retro', 
                'action_id': 'start_retrospective',
                'value': 'retrospective'
            }
        ]
        
        # Create responsive button layout - primary buttons first
        return self._create_responsive_action_buttons(primary_actions, secondary_actions)
    
    def _create_responsive_action_buttons(self, primary_actions: List[Dict], secondary_actions: List[Dict]) -> Dict[str, Any]:
        """Create responsive action button layout that works on mobile and desktop."""
        # For mobile responsiveness, we limit to 3 buttons per row
        # Primary actions get priority placement
        all_buttons = []
        
        # Add primary buttons
        for action in primary_actions:
            button = self.create_button_element(
                text=action['text'],
                action_id=action['action_id'],
                value=action.get('value', ''),
                style=action.get('style'),
                url=action.get('url')
            )
            all_buttons.append(button)
        
        # Add secondary buttons if there's space (max 6 total for good mobile UX)
        remaining_slots = 6 - len(all_buttons)
        for action in secondary_actions[:remaining_slots]:
            button = self.create_button_element(
                text=action['text'],
                action_id=action['action_id'],
                value=action.get('value', ''),
                style=action.get('style'),
                url=action.get('url')
            )
            all_buttons.append(button)
        
        return self.create_actions_block(all_buttons)
    
    def create_summary_statistics_display(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create summary statistics display for PRs, tickets, and commits with responsive layout.
        
        Requirements: 1.5, 1.6 - Summary statistics for PRs, tickets, commits with responsive design
        """
        blocks = []
        stats = data.get('stats', {})
        
        if not stats:
            return blocks
        
        # Create comprehensive statistics section
        stats_header = self.create_section_block("*📊 Team Statistics Overview*")
        blocks.append(stats_header)
        
        # Development metrics
        dev_stats = self._create_development_metrics(stats)
        if dev_stats:
            blocks.append(dev_stats)
        
        # Productivity metrics
        productivity_stats = self._create_productivity_metrics(stats)
        if productivity_stats:
            blocks.append(productivity_stats)
        
        # Quality metrics
        quality_stats = self._create_quality_metrics(stats)
        if quality_stats:
            blocks.append(quality_stats)
        
        return blocks
    
    def _create_development_metrics(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Create development-focused metrics display."""
        dev_fields = {}
        
        # Pull Request metrics
        if any(key in stats for key in ['prs_merged', 'prs_open', 'prs_draft']):
            prs_merged = stats.get('prs_merged', 0)
            prs_open = stats.get('prs_open', 0)
            prs_draft = stats.get('prs_draft', 0)
            
            pr_summary = []
            if prs_merged > 0:
                pr_summary.append(f"✅ {prs_merged} merged")
            if prs_open > 0:
                pr_summary.append(f"🔄 {prs_open} open")
            if prs_draft > 0:
                pr_summary.append(f"📝 {prs_draft} draft")
            
            dev_fields['🔀 Pull Requests'] = " • ".join(pr_summary) if pr_summary else "No PRs"
        
        # Commit metrics
        if 'commits' in stats:
            commits = stats['commits']
            commit_emoji = "🚀" if commits > 20 else "📝" if commits > 5 else "💤"
            dev_fields['📊 Commits'] = f"{commit_emoji} {commits} commits"
        
        # Branch metrics
        if 'active_branches' in stats:
            branches = stats['active_branches']
            dev_fields['🌿 Active Branches'] = f"🔄 {branches} branches"
        
        return self.create_fields_section(dev_fields) if dev_fields else None
    
    def _create_productivity_metrics(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Create productivity-focused metrics display."""
        prod_fields = {}
        
        # Ticket metrics
        if any(key in stats for key in ['tickets_closed', 'tickets_open', 'tickets_in_progress']):
            tickets_closed = stats.get('tickets_closed', 0)
            tickets_open = stats.get('tickets_open', 0)
            tickets_in_progress = stats.get('tickets_in_progress', 0)
            
            ticket_summary = []
            if tickets_closed > 0:
                ticket_summary.append(f"✅ {tickets_closed} closed")
            if tickets_in_progress > 0:
                ticket_summary.append(f"⏳ {tickets_in_progress} in progress")
            if tickets_open > 0:
                ticket_summary.append(f"📋 {tickets_open} open")
            
            prod_fields['🎫 Tickets'] = " • ".join(ticket_summary) if ticket_summary else "No tickets"
        
        # Story points
        if 'story_points_completed' in stats:
            sp_completed = stats['story_points_completed']
            sp_total = stats.get('story_points_total', sp_completed)
            prod_fields['📈 Story Points'] = f"✅ {sp_completed}/{sp_total} completed"
        
        # Velocity metrics
        if 'velocity' in stats:
            velocity = stats['velocity']
            velocity_emoji = "🚀" if velocity > 0.8 else "⚡" if velocity > 0.6 else "🐌"
            prod_fields['⚡ Velocity'] = f"{velocity_emoji} {int(velocity * 100)}%"
        
        return self.create_fields_section(prod_fields) if prod_fields else None
    
    def _create_quality_metrics(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Create quality-focused metrics display."""
        quality_fields = {}
        
        # Code review metrics
        if 'reviews_given' in stats:
            reviews = stats['reviews_given']
            quality_fields['👀 Reviews Given'] = f"✅ {reviews} reviews"
        
        # Test metrics
        if 'tests_added' in stats:
            tests = stats['tests_added']
            test_emoji = "🧪" if tests > 0 else "⚠️"
            quality_fields['🧪 Tests Added'] = f"{test_emoji} {tests} tests"
        
        # Bug metrics
        if 'bugs_fixed' in stats:
            bugs = stats['bugs_fixed']
            bug_emoji = "🐛" if bugs > 0 else "✨"
            quality_fields['🐛 Bugs Fixed'] = f"{bug_emoji} {bugs} bugs"
        
        # Deployment metrics
        if 'deployments' in stats:
            deployments = stats['deployments']
            deploy_emoji = "🚀" if deployments > 0 else "⏸️"
            quality_fields['🚀 Deployments'] = f"{deploy_emoji} {deployments} deployments"
        
        return self.create_fields_section(quality_fields) if quality_fields else None
    
    def _create_action_items_section(self, action_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create enhanced action items section with assignees and due dates."""
        items_text = ["*🎯 Action Items:*"]
        
        for item in action_items[:3]:  # Show max 3 action items
            assignee = item.get('assignee', 'Unassigned')
            due_date = item.get('due_date', 'No due date')
            title = item.get('title', 'Untitled task')
            priority = item.get('priority', 'medium')
            
            # Add priority indicator
            priority_emoji = self._get_priority_indicator(priority).split()[0]
            
            # Format with enhanced information
            item_text = f"• {priority_emoji} {self._truncate_text(title, 60)}"
            item_text += f" - {self._format_user_mention(assignee)}"
            
            # Add due date with urgency indicator
            if due_date and due_date != 'No due date':
                due_emoji = "🚨" if "overdue" in due_date.lower() else "📅"
                item_text += f" ({due_emoji} {due_date})"
            
            items_text.append(item_text)
        
        if len(action_items) > 3:
            items_text.append(f"• ... and {len(action_items)-3} more items")
        
        return self.create_section_block("\n".join(items_text))
    
    def _ensure_mobile_responsive_design(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure message blocks are optimized for mobile and desktop viewing.
        
        Requirements: 5.4 - Responsive design elements for mobile and desktop viewing
        """
        # Mobile optimization strategies:
        # 1. Limit field sections to 2 columns max
        # 2. Truncate long text appropriately
        # 3. Use context blocks for secondary information
        # 4. Limit action buttons to 6 per block
        
        optimized_blocks = []
        
        for block in blocks:
            if block.get('type') == 'section' and 'fields' in block:
                # Limit fields to 4 items (2x2 grid) for mobile readability
                fields = block['fields']
                if len(fields) > 4:
                    # Split into multiple blocks
                    for i in range(0, len(fields), 4):
                        chunk_fields = fields[i:i+4]
                        optimized_blocks.append({
                            **block,
                            'fields': chunk_fields
                        })
                else:
                    optimized_blocks.append(block)
            elif block.get('type') == 'actions':
                # Ensure action buttons don't exceed mobile limits
                elements = block.get('elements', [])
                if len(elements) > 6:
                    # Split into multiple action blocks
                    for i in range(0, len(elements), 6):
                        chunk_elements = elements[i:i+6]
                        optimized_blocks.append({
                            **block,
                            'elements': chunk_elements
                        })
                else:
                    optimized_blocks.append(block)
            else:
                optimized_blocks.append(block)
        
        return optimized_blocks
    
    def _format_for_accessibility(self, text: str) -> str:
        """Format text with accessibility considerations for screen readers."""
        # Add proper spacing and structure for screen readers
        # Replace emoji-heavy content with descriptive text when needed
        if self.config.accessibility_mode:
            # Replace common emojis with descriptive text
            accessibility_replacements = {
                '✅': '[COMPLETED]',
                '🚫': '[BLOCKED]',
                '⚠️': '[WARNING]',
                '🔄': '[IN PROGRESS]',
                '📊': '[STATISTICS]',
                '🎯': '[ACTION ITEM]',
                '📝': '[NOTE]',
                '🚀': '[HIGH ACTIVITY]',
                '💤': '[LOW ACTIVITY]'
            }
            
            for emoji, replacement in accessibility_replacements.items():
                text = text.replace(emoji, replacement)
        
        return text