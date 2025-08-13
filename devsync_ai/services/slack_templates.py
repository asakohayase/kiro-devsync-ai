"""
Slack message templates for DevSync AI notifications.
Provides rich formatting using Slack Block Kit for various notification types.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
from ..core.base_template import SlackMessageTemplate, EmojiConstants


class StatusIndicator(Enum):
    """Status indicators with emoji representations."""
    ACTIVE = "🟢"
    WARNING = "🟡"
    BLOCKED = "🔴"
    INACTIVE = "⚪"
    SUCCESS = "✅"
    PENDING = "⏳"
    FAILED = "❌"


# Keep the old base class for backward compatibility
class SlackTemplateBase:
    """Base class for Slack message templates."""
    
    def __init__(self):
        self.blocks = []
        self.fallback_text = ""
    
    def add_header(self, text: str, emoji: str = "📊") -> None:
        """Add a header block to the message."""
        self.blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} {text}",
                "emoji": True
            }
        })
    
    def add_divider(self) -> None:
        """Add a divider block."""
        self.blocks.append({"type": "divider"})
    
    def add_context(self, elements: List[str]) -> None:
        """Add context elements."""
        context_elements = []
        for element in elements:
            context_elements.append({
                "type": "mrkdwn",
                "text": element
            })
        
        self.blocks.append({
            "type": "context",
            "elements": context_elements
        })
    
    def get_message(self) -> Dict[str, Any]:
        """Get the complete Slack message payload."""
        return {
            "blocks": self.blocks,
            "text": self.fallback_text
        }


class DailyStandupTemplate(SlackMessageTemplate):
    """Template for daily standup summaries."""
    
    def _validate_data(self) -> None:
        """Validate standup data."""
        # Standup data is flexible, no strict requirements
        pass
    
    def _build_message_content(self) -> None:
        """Build standup message content."""
        self._build_template()
    
    def _get_header_text(self) -> str:
        """Get header text."""
        date_str = self.data.get('date', datetime.now().strftime('%Y-%m-%d'))
        team_name = self.data.get('team', 'DevSync Team')
        return f"Daily Standup - {team_name}"
    
    def _get_header_emoji(self) -> str:
        """Get header emoji."""
        return "🚀"
    
    def _build_template(self) -> None:
        """Build the complete standup template."""
        # Date and overall status
        self._add_date_and_status()
        self.add_divider_block()
        
        # Summary statistics
        self._add_summary_stats()
        self.add_divider_block()
        
        # Team members
        self._add_team_members()
        
        # Action items
        if self.data.get('action_items'):
            self.add_divider_block()
            self._add_action_items()
        
        # Action buttons
        self._add_standup_actions()
    
    def _add_date_and_status(self) -> None:
        """Add date and overall team status."""
        date_str = self.data.get('date', datetime.now().strftime('%Y-%m-%d'))
        team_health = self._calculate_team_health()
        
        fields = [
            {"type": "mrkdwn", "text": f"*Date:* {date_str}"},
            {"type": "mrkdwn", "text": f"*Team Health:* {team_health}"}
        ]
        self.add_fields_block(fields)
    
    def _add_summary_stats(self) -> None:
        """Add summary statistics section."""
        stats = self.data.get('stats', {})
        
        # Create progress bar for sprint completion
        sprint_progress = self._create_progress_bar(
            stats.get('tickets_completed', 0),
            stats.get('tickets_completed', 0) + stats.get('tickets_in_progress', 0)
        )
        
        self.add_section_block(f"*📈 Sprint Progress*\n{sprint_progress}")
        
        # Statistics grid
        fields = [
            {"type": "mrkdwn", "text": f"*🔀 PRs Merged:* {stats.get('prs_merged', 0)}"},
            {"type": "mrkdwn", "text": f"*📝 PRs Open:* {stats.get('prs_open', 0)}"},
            {"type": "mrkdwn", "text": f"*✅ Tickets Done:* {stats.get('tickets_completed', 0)}"},
            {"type": "mrkdwn", "text": f"*⏳ In Progress:* {stats.get('tickets_in_progress', 0)}"},
            {"type": "mrkdwn", "text": f"*💻 Commits:* {stats.get('commits', 0)}"},
            {"type": "mrkdwn", "text": f"*👥 Active Members:* {len([m for m in self.data.get('team_members', []) if m.get('status') == 'active'])}"}
        ]
        self.add_fields_block(fields)
    
    def _add_team_members(self) -> None:
        """Add individual team member sections."""
        team_members = self.data.get('team_members', [])
        
        if not team_members:
            return
        
        self.add_section_block("*👥 Team Updates*")
        
        for member in team_members:
            self._add_member_section(member)
    
    def _add_member_section(self, member: Dict[str, Any]) -> None:
        """Add a section for an individual team member."""
        name = member.get('name', 'Unknown')
        status = member.get('status', 'active')
        status_emoji = self._get_status_emoji(status)
        
        # Member header
        member_text = f"*{status_emoji} {name}*\n"
        
        # Yesterday's work
        yesterday = member.get('yesterday', [])
        if yesterday:
            member_text += "*Yesterday:*\n"
            for item in yesterday:
                member_text += f"• {item}\n"
        
        # Today's plans
        today = member.get('today', [])
        if today:
            member_text += "*Today:*\n"
            for item in today:
                member_text += f"• {item}\n"
        
        # Blockers
        blockers = member.get('blockers', [])
        if blockers:
            member_text += "*🚫 Blockers:*\n"
            for blocker in blockers:
                member_text += f"• {blocker}\n"
        
        self.add_section_block(member_text.strip())
    
    def _add_action_items(self) -> None:
        """Add action items section."""
        action_items = self.data.get('action_items', [])
        
        action_text = "*📋 Action Items*\n"
        for i, item in enumerate(action_items, 1):
            action_text += f"{i}. {item}\n"
        
        self.add_section_block(action_text.strip())
    
    def _add_standup_actions(self) -> None:
        """Add standup action buttons."""
        buttons = [
            self.create_button("View Dashboard", "view_dashboard", emoji="📊"),
            self.create_button("Add Update", "add_update", emoji="📝")
        ]
        self.add_actions_block(buttons)
    
    def _calculate_team_health(self) -> str:
        """Calculate overall team health indicator."""
        team_members = self.data.get('team_members', [])
        if not team_members:
            return f"{StatusIndicator.INACTIVE.value} No data"
        
        active_count = len([m for m in team_members if m.get('status') == 'active'])
        blocked_count = len([m for m in team_members if m.get('blockers')])
        
        if blocked_count > len(team_members) * 0.3:  # More than 30% blocked
            return f"{StatusIndicator.BLOCKED.value} Needs attention"
        elif active_count == len(team_members):
            return f"{StatusIndicator.SUCCESS.value} All systems go"
        else:
            return f"{StatusIndicator.WARNING.value} Some issues"
    
    def _create_progress_bar(self, completed: int, total: int) -> str:
        """Create a text-based progress bar."""
        if total == 0:
            return "No tickets in sprint"
        
        percentage = (completed / total) * 100
        filled = int(percentage / 10)
        empty = 10 - filled
        
        bar = "█" * filled + "░" * empty
        return f"{bar} {completed}/{total} ({percentage:.0f}%)"
    
    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for member status."""
        status_map = {
            'active': '🟢',
            'away': '🟡',
            'blocked': '🔴',
            'inactive': '⚪'
        }
        return status_map.get(status, '⚪')


class PRStatusTemplate(SlackTemplateBase):
    """Template for PR status updates."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
        pr = data.get('pr', {})
        action = data.get('action', 'updated')
        self.fallback_text = f"PR {action}: {pr.get('title', 'Unknown PR')}"
        self._build_template()
    
    def _build_template(self) -> None:
        """Build the complete PR status template."""
        pr = self.data.get('pr', {})
        action = self.data.get('action', 'updated')
        
        # Header with action-specific emoji
        self._add_pr_header(action)
        
        # PR details
        self._add_pr_details()
        
        # Status indicators
        self._add_status_section()
        
        # File changes summary
        self._add_changes_summary()
        
        # Related tickets
        if pr.get('jira_tickets'):
            self._add_related_tickets()
        
        # Action buttons
        self._add_action_buttons()
        
        # Footer
        self._add_pr_footer()
    
    def _add_pr_header(self, action: str) -> None:
        """Add PR header with action-specific styling."""
        pr = self.data.get('pr', {})
        title = pr.get('title', 'Unknown PR')
        pr_id = pr.get('id', 'N/A')
        
        action_emojis = {
            'opened': '🆕',
            'ready_for_review': '👀',
            'approved': '✅',
            'has_conflicts': '⚠️',
            'merged': '🎉',
            'closed': '❌',
            'review_requested': '🔍',
            'changes_requested': '📝'
        }
        
        emoji = action_emojis.get(action, '📄')
        action_text = action.replace('_', ' ').title()
        
        self.add_header(f"PR #{pr_id}: {action_text}", emoji)
        
        # PR title and description
        description = pr.get('description', '')[:100]
        if len(pr.get('description', '')) > 100:
            description += '...'
        
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{title}*\n{description}" if description else f"*{title}*"
            }
        })
    
    def _add_pr_details(self) -> None:
        """Add PR details section."""
        pr = self.data.get('pr', {})
        
        # Author and reviewers
        author = pr.get('author', 'Unknown')
        reviewers = pr.get('reviewers', [])
        approved_by = pr.get('approved_by', [])
        changes_requested_by = pr.get('changes_requested_by', [])
        
        details_text = f"*👤 Author:* {author}\n"
        
        if reviewers:
            reviewer_status = []
            for reviewer in reviewers:
                if reviewer in approved_by:
                    reviewer_status.append(f"✅ {reviewer}")
                elif reviewer in changes_requested_by:
                    reviewer_status.append(f"📝 {reviewer}")
                else:
                    reviewer_status.append(f"⏳ {reviewer}")
            
            details_text += f"*👥 Reviewers:* {', '.join(reviewer_status)}\n"
        
        # Status and timing
        status = pr.get('status', 'unknown')
        created_at = pr.get('created_at', '')
        updated_at = pr.get('updated_at', '')
        
        if created_at:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            details_text += f"*📅 Created:* {created_date.strftime('%m/%d %I:%M %p')}\n"
        
        if updated_at and updated_at != created_at:
            updated_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            details_text += f"*🔄 Updated:* {updated_date.strftime('%m/%d %I:%M %p')}\n"
        
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": details_text.strip()
            }
        })
    
    def _add_status_section(self) -> None:
        """Add status indicators section."""
        pr = self.data.get('pr', {})
        
        # Status indicators
        status_items = []
        
        # Draft status
        if pr.get('draft', False):
            status_items.append("🚧 Draft")
        
        # Conflicts
        if pr.get('has_conflicts', False):
            status_items.append("⚠️ Has conflicts")
        
        # CI status
        ci_status = pr.get('ci_status', 'unknown')
        ci_emojis = {
            'passing': '✅ CI Passing',
            'failing': '❌ CI Failing',
            'pending': '⏳ CI Running',
            'unknown': '❓ CI Unknown'
        }
        status_items.append(ci_emojis.get(ci_status, '❓ CI Unknown'))
        
        if status_items:
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🔍 Status:* " + " • ".join(status_items)
                }
            })
    
    def _add_changes_summary(self) -> None:
        """Add file changes summary."""
        pr = self.data.get('pr', {})
        
        files_changed = pr.get('files_changed', 0)
        additions = pr.get('additions', 0)
        deletions = pr.get('deletions', 0)
        
        if files_changed > 0:
            changes_text = f"*📁 Files:* {files_changed} • "
            changes_text += f"*➕ Additions:* {additions} • "
            changes_text += f"*➖ Deletions:* {deletions}"
            
            # Size indicator
            total_changes = additions + deletions
            if total_changes > 1000:
                size_indicator = "🔴 Large PR"
            elif total_changes > 300:
                size_indicator = "🟡 Medium PR"
            else:
                size_indicator = "🟢 Small PR"
            
            changes_text += f" • {size_indicator}"
            
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": changes_text
                }
            })
    
    def _add_related_tickets(self) -> None:
        """Add related JIRA tickets section."""
        pr = self.data.get('pr', {})
        jira_tickets = pr.get('jira_tickets', [])
        
        if jira_tickets:
            tickets_text = "*🎫 Related Tickets:* " + ", ".join(jira_tickets)
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": tickets_text
                }
            })
    
    def _add_action_buttons(self) -> None:
        """Add interactive action buttons."""
        pr = self.data.get('pr', {})
        pr_id = pr.get('id', '')
        status = pr.get('status', 'open')
        
        buttons = []
        
        # View PR button (always available)
        buttons.append({
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "👀 View PR",
                "emoji": True
            },
            "url": f"https://github.com/repo/pull/{pr_id}",
            "action_id": "view_pr"
        })
        
        # Status-specific buttons
        if status == 'open' and not pr.get('draft', False):
            if not pr.get('approved_by'):
                buttons.append({
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Approve",
                        "emoji": True
                    },
                    "value": f"approve_{pr_id}",
                    "action_id": "approve_pr",
                    "style": "primary"
                })
            
            buttons.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📝 Request Changes",
                    "emoji": True
                },
                "value": f"request_changes_{pr_id}",
                "action_id": "request_changes"
            })
        
        # Merge button for approved PRs
        if pr.get('approved_by') and not pr.get('has_conflicts', False):
            buttons.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🚀 Merge",
                    "emoji": True
                },
                "value": f"merge_{pr_id}",
                "action_id": "merge_pr",
                "style": "primary"
            })
        
        if buttons:
            # Split buttons into groups of 5 (Slack limit)
            for i in range(0, len(buttons), 5):
                button_group = buttons[i:i+5]
                self.blocks.append({
                    "type": "actions",
                    "elements": button_group
                })
    
    def _add_pr_footer(self) -> None:
        """Add footer with timestamp."""
        timestamp = datetime.now().strftime('%I:%M %p')
        
        self.add_context([
            f"Updated at {timestamp}",
            "DevSync AI"
        ])


def create_standup_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a daily standup message."""
    template = DailyStandupTemplate(data)
    return template.get_message()


def create_pr_status_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a PR status update message."""
    template = PRStatusTemplate(data)
    return template.get_message()


# Example usage and test data
if __name__ == "__main__":
    # Test standup template
    standup_data = {
        "date": "2025-08-12",
        "team": "DevSync Team",
        "stats": {
            "prs_merged": 3,
            "prs_open": 5,
            "tickets_completed": 7,
            "tickets_in_progress": 12,
            "commits": 23
        },
        "team_members": [
            {
                "name": "Alice",
                "status": "active",
                "yesterday": ["Completed user auth", "Fixed bug #123"],
                "today": ["Start payment integration", "Code review"],
                "blockers": []
            },
            {
                "name": "Bob",
                "status": "active",
                "yesterday": ["Database optimization"],
                "today": ["API documentation", "Testing"],
                "blockers": ["Waiting for design approval"]
            }
        ],
        "action_items": ["Deploy staging environment", "Update documentation"]
    }
    
    # Test PR template
    pr_data = {
        "pr": {
            "id": 123,
            "title": "Add user authentication",
            "description": "Implements OAuth2 login flow with proper error handling",
            "author": "alice",
            "status": "open",
            "draft": False,
            "reviewers": ["bob", "carol"],
            "approved_by": ["bob"],
            "changes_requested_by": [],
            "has_conflicts": False,
            "files_changed": 12,
            "additions": 234,
            "deletions": 45,
            "created_at": "2025-08-12T10:00:00Z",
            "updated_at": "2025-08-12T14:30:00Z",
            "jira_tickets": ["DP-123", "DP-124"],
            "ci_status": "passing"
        },
        "action": "ready_for_review"
    }
    
    print("Standup Message:")
    print(create_standup_message(standup_data))
    print("\nPR Status Message:")
    print(create_pr_status_message(pr_data))