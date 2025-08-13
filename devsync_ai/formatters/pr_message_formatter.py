"""PR message formatter for all PR-related notifications."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from ..core.base_template import SlackMessageTemplate
from ..core.block_kit_builders import BlockKitBuilder, HeaderConfig, ActionButton, ButtonStyle
from ..core.status_indicators import PRStatus, Priority


class PRMessageFormatter(SlackMessageTemplate):
    """Specialized formatter for PR-related notifications."""
    
    REQUIRED_FIELDS = ['pr']
    
    def __init__(self, *args, **kwargs):
        """Initialize with Block Kit builder."""
        super().__init__(*args, **kwargs)
        self.builder = BlockKitBuilder(self.status_system)
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create PR notification message blocks."""
        blocks = []
        
        # Handle batch mode
        if 'prs' in data:
            return self._create_batch_message(data)
        
        pr_data = data['pr']
        action = data.get('action', 'updated')
        
        # Determine PR status
        pr_status = self._get_pr_status(pr_data, action)
        
        # Build header with comprehensive info
        header_config = HeaderConfig(
            title=self._build_pr_title(pr_data),
            status=pr_status,
            status_context="pr",
            timestamp=self._parse_timestamp(pr_data.get('updated_at')),
            subtitle=self._build_pr_subtitle(pr_data),
            actions=self._get_quick_actions(pr_data, pr_status)
        )
        
        blocks.extend(self.builder.build_header(header_config))
        
        # PR details section
        pr_fields = self._build_pr_details(pr_data)
        if pr_fields:
            blocks.append(self.builder.build_field_group(pr_fields))
        
        # File changes section
        if pr_data.get('files') or pr_data.get('additions') is not None:
            blocks.append(self._build_file_changes_section(pr_data))
        
        # CI/CD results section
        if pr_data.get('checks') or pr_data.get('ci_results'):
            blocks.append(self._build_ci_results_section(pr_data))
        
        # Related items section
        related_content = self._build_related_items(pr_data)
        if related_content:
            blocks.extend(related_content)
        
        # Action-specific content
        action_content = self._build_action_specific_content(action, pr_data)
        if action_content:
            blocks.extend(action_content)
        
        # Main actions
        blocks.append(self.builder.build_divider())
        main_actions = self._get_main_actions(pr_status, pr_data)
        if main_actions:
            blocks.append(self.builder.build_action_buttons(main_actions))
        
        return blocks
    
    def _create_batch_message(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create batch message for multiple PRs."""
        blocks = []
        prs = data['prs']
        batch_type = data.get('batch_type', 'summary')
        
        # Batch header
        header_config = HeaderConfig(
            title=f"PR Summary - {len(prs)} Pull Requests",
            status="info",
            timestamp=datetime.now(),
            subtitle=f"Batch update: {batch_type}"
        )
        
        blocks.extend(self.builder.build_header(header_config))
        
        # Summary statistics
        stats = self._calculate_batch_stats(prs)
        blocks.append(self.builder.build_field_group(stats))
        
        blocks.append(self.builder.build_divider())
        
        # Individual PR summaries (limited)
        for i, pr in enumerate(prs[:5]):  # Show max 5 PRs
            pr_summary = self._build_pr_summary(pr, i + 1)
            blocks.append(pr_summary)
        
        if len(prs) > 5:
            blocks.append(self.builder.build_section({
                "text": f"... and {len(prs) - 5} more PRs"
            }))
        
        # Batch actions
        batch_actions = [
            {"label": "📊 View All PRs", "url": data.get('dashboard_url', '#')},
            {"label": "📈 PR Analytics", "action_id": "view_pr_analytics"}
        ]
        blocks.append(self.builder.build_action_buttons(batch_actions))
        
        return blocks
    
    def _get_pr_status(self, pr_data: Dict[str, Any], action: str) -> str:
        """Determine PR status from data and action."""
        # Direct status mapping
        status_mapping = {
            'opened': 'open',
            'draft': 'draft',
            'ready_for_review': 'ready_for_review',
            'approved': 'approved',
            'changes_requested': 'changes_requested',
            'merged': 'merged',
            'closed': 'closed'
        }
        
        if action in status_mapping:
            return status_mapping[action]
        
        # Infer from PR data
        if pr_data.get('draft', False):
            return 'draft'
        elif pr_data.get('merged', False):
            return 'merged'
        elif pr_data.get('state') == 'closed':
            return 'closed'
        elif pr_data.get('mergeable_state') == 'dirty':
            return 'conflicts'
        elif pr_data.get('review_decision') == 'APPROVED':
            return 'approved'
        elif pr_data.get('review_decision') == 'CHANGES_REQUESTED':
            return 'changes_requested'
        
        return 'open'
    
    def _build_pr_title(self, pr_data: Dict[str, Any]) -> str:
        """Build PR title with number and title."""
        number = pr_data.get('number', 'N/A')
        title = pr_data.get('title', 'Untitled PR')
        return f"PR #{number}: {title}"
    
    def _build_pr_subtitle(self, pr_data: Dict[str, Any]) -> str:
        """Build PR subtitle with branch and author info."""
        parts = []
        
        # Branch info
        if pr_data.get('head_ref') and pr_data.get('base_ref'):
            parts.append(f"`{pr_data['head_ref']}` → `{pr_data['base_ref']}`")
        
        # Author
        if pr_data.get('author'):
            author_mention = self.builder.build_user_mention(pr_data['author'])
            parts.append(f"by {author_mention}")
        
        return " • ".join(parts) if parts else None
    
    def _build_pr_details(self, pr_data: Dict[str, Any]) -> Dict[str, str]:
        """Build PR details fields."""
        fields = {}
        
        # Priority
        if pr_data.get('priority'):
            try:
                priority = Priority(pr_data['priority'].lower())
                priority_indicator = self.status_system.get_priority_indicator(priority)
                fields['Priority'] = f"{priority_indicator.emoji} {priority_indicator.text}"
            except ValueError:
                fields['Priority'] = pr_data['priority'].title()
        
        # Reviewers
        if pr_data.get('reviewers'):
            reviewers = pr_data['reviewers'][:3]
            reviewer_mentions = [self.builder.build_user_mention(r) for r in reviewers]
            fields['Reviewers'] = ", ".join(reviewer_mentions)
            if len(pr_data['reviewers']) > 3:
                fields['Reviewers'] += f" (+{len(pr_data['reviewers'])-3} more)"
        
        # Assignees
        if pr_data.get('assignees'):
            assignees = pr_data['assignees'][:2]
            assignee_mentions = [self.builder.build_user_mention(a) for a in assignees]
            fields['Assignees'] = ", ".join(assignee_mentions)
        
        # Labels
        if pr_data.get('labels'):
            labels = pr_data['labels'][:3]
            fields['Labels'] = ", ".join([f"`{label}`" for label in labels])
            if len(pr_data['labels']) > 3:
                fields['Labels'] += f" (+{len(pr_data['labels'])-3} more)"
        
        # Milestone
        if pr_data.get('milestone'):
            fields['Milestone'] = pr_data['milestone']
        
        return fields
    
    def _build_file_changes_section(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build file changes section."""
        content_parts = ["*📁 File Changes:*"]
        
        # File count
        if pr_data.get('changed_files'):
            content_parts.append(f"📄 {pr_data['changed_files']} files changed")
        
        # Line changes
        additions = pr_data.get('additions', 0)
        deletions = pr_data.get('deletions', 0)
        if additions or deletions:
            content_parts.append(f"📈 +{additions} -{deletions} lines")
        
        # File list (if provided and not too long)
        if pr_data.get('files') and len(pr_data['files']) <= 5:
            content_parts.append("\n*Modified files:*")
            for file_info in pr_data['files']:
                filename = file_info.get('filename', 'unknown')
                status = file_info.get('status', 'modified')
                status_emoji = {'added': '🆕', 'modified': '✏️', 'deleted': '🗑️'}.get(status, '📝')
                content_parts.append(f"• {status_emoji} `{filename}`")
        elif pr_data.get('files') and len(pr_data['files']) > 5:
            content_parts.append(f"\n*{len(pr_data['files'])} files modified* (too many to list)")
        
        return self.builder.build_section({"text": "\n".join(content_parts)})
    
    def _build_ci_results_section(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build CI/CD results section."""
        content_parts = ["*🔧 CI/CD Status:*"]
        
        # Check results
        if pr_data.get('checks'):
            checks = pr_data['checks']
            passed = checks.get('passed', 0)
            failed = checks.get('failed', 0)
            pending = checks.get('pending', 0)
            
            check_parts = []
            if passed > 0:
                check_parts.append(f"✅ {passed} passed")
            if failed > 0:
                check_parts.append(f"❌ {failed} failed")
            if pending > 0:
                check_parts.append(f"⏳ {pending} pending")
            
            if check_parts:
                content_parts.append(" • ".join(check_parts))
        
        # CI results details
        if pr_data.get('ci_results'):
            ci_results = pr_data['ci_results']
            for result in ci_results[:3]:  # Show max 3 CI results
                name = result.get('name', 'Unknown')
                status = result.get('status', 'unknown')
                status_emoji = {
                    'success': '✅',
                    'failure': '❌',
                    'pending': '⏳',
                    'cancelled': '⏹️'
                }.get(status, '❓')
                content_parts.append(f"• {status_emoji} {name}")
        
        return self.builder.build_section({"text": "\n".join(content_parts)})
    
    def _build_related_items(self, pr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build related items section (JIRA tickets, deployments)."""
        blocks = []
        
        # Related JIRA tickets
        if pr_data.get('jira_tickets'):
            jira_content = ["*🎫 Related JIRA Tickets:*"]
            for ticket in pr_data['jira_tickets'][:3]:
                ticket_key = ticket.get('key', 'UNKNOWN')
                ticket_title = ticket.get('title', 'No title')
                ticket_url = ticket.get('url', '#')
                jira_content.append(f"• {self.builder.build_url_link(ticket_url, ticket_key)}: {ticket_title}")
            
            blocks.append(self.builder.build_section({"text": "\n".join(jira_content)}))
        
        # Deployment info
        if pr_data.get('deployments'):
            deploy_content = ["*🚀 Deployments:*"]
            for deployment in pr_data['deployments'][:2]:
                env = deployment.get('environment', 'unknown')
                status = deployment.get('status', 'unknown')
                status_emoji = {
                    'success': '✅',
                    'failure': '❌',
                    'pending': '⏳',
                    'in_progress': '🔄'
                }.get(status, '❓')
                deploy_content.append(f"• {status_emoji} {env.title()}: {status}")
            
            blocks.append(self.builder.build_section({"text": "\n".join(deploy_content)}))
        
        return blocks
    
    def _build_action_specific_content(self, action: str, pr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build content specific to the action type."""
        blocks = []
        
        if action == 'review_submitted':
            review_data = pr_data.get('review', {})
            reviewer = review_data.get('user', 'Unknown')
            state = review_data.get('state', 'commented')
            
            state_emoji = {
                'approved': '✅',
                'changes_requested': '❌',
                'commented': '💬'
            }.get(state, '📝')
            
            content = f"*{state_emoji} Review by {self.builder.build_user_mention(reviewer)}:*"
            if review_data.get('body'):
                content += f"\n{self._truncate_text(review_data['body'], 200)}"
            
            blocks.append(self.builder.build_section({"text": content}))
        
        elif action == 'merged':
            merger = pr_data.get('merged_by', 'Unknown')
            merge_time = pr_data.get('merged_at')
            content = f"🎉 *Merged by {self.builder.build_user_mention(merger)}*"
            if merge_time:
                content += f" at {self._format_timestamp(merge_time)}"
            
            blocks.append(self.builder.build_section({"text": content}))
        
        return blocks
    
    def _get_quick_actions(self, pr_data: Dict[str, Any], pr_status: str) -> List[Dict[str, Any]]:
        """Get quick actions for header."""
        actions = []
        
        # Always include view PR
        if pr_data.get('html_url'):
            actions.append({
                "label": "👀 View",
                "url": pr_data['html_url']
            })
        
        return actions
    
    def _get_main_actions(self, pr_status: str, pr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get main action buttons based on PR status."""
        actions = []
        pr_number = str(pr_data.get('number', ''))
        
        if pr_status in ['open', 'ready_for_review']:
            actions.extend([
                {
                    "label": "✅ Approve",
                    "action_id": "approve_pr",
                    "value": pr_number,
                    "style": "primary"
                },
                {
                    "label": "💬 Comment",
                    "action_id": "comment_pr",
                    "value": pr_number
                },
                {
                    "label": "❌ Request Changes",
                    "action_id": "request_changes",
                    "value": pr_number,
                    "style": "danger"
                }
            ])
        
        elif pr_status == 'approved':
            actions.extend([
                {
                    "label": "🚀 Merge",
                    "action_id": "merge_pr",
                    "value": pr_number,
                    "style": "primary",
                    "confirm": self.builder.create_confirmation_dialog(
                        title="Merge PR",
                        text=f"Merge PR #{pr_number} into {pr_data.get('base_ref', 'main')}?",
                        confirm_text="Merge",
                        deny_text="Cancel"
                    )
                }
            ])
        
        elif pr_status == 'conflicts':
            actions.extend([
                {
                    "label": "🔧 Resolve",
                    "action_id": "resolve_conflicts",
                    "value": pr_number,
                    "style": "danger"
                }
            ])
        
        # Common actions
        actions.extend([
            {
                "label": "📊 Details",
                "action_id": "pr_details",
                "value": pr_number
            }
        ])
        
        return actions
    
    def _calculate_batch_stats(self, prs: List[Dict[str, Any]]) -> Dict[str, str]:
        """Calculate statistics for batch of PRs."""
        stats = {}
        
        # Status counts
        status_counts = {}
        for pr in prs:
            status = self._get_pr_status(pr, pr.get('action', 'updated'))
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Format status counts
        status_parts = []
        for status, count in status_counts.items():
            indicator = self.status_system.get_indicator_by_string(status, "pr")
            status_parts.append(f"{indicator.emoji} {count}")
        
        stats['Status Distribution'] = " • ".join(status_parts)
        
        # Total changes
        total_additions = sum(pr.get('additions', 0) for pr in prs)
        total_deletions = sum(pr.get('deletions', 0) for pr in prs)
        stats['Total Changes'] = f"+{total_additions} -{total_deletions} lines"
        
        # Authors
        authors = set(pr.get('author') for pr in prs if pr.get('author'))
        stats['Contributors'] = f"{len(authors)} developers"
        
        return stats
    
    def _build_pr_summary(self, pr: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Build summary for individual PR in batch."""
        title = f"{index}. {self._build_pr_title(pr)}"
        status = self._get_pr_status(pr, pr.get('action', 'updated'))
        indicator = self.status_system.get_indicator_by_string(status, "pr")
        
        content = f"{indicator.emoji} *{title}*"
        if pr.get('author'):
            content += f" by {self.builder.build_user_mention(pr['author'])}"
        
        return self.builder.build_section({"text": content})
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime."""
        if not timestamp_str:
            return None
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    def _format_timestamp(self, timestamp_str: str) -> str:
        """Format timestamp for display."""
        dt = self._parse_timestamp(timestamp_str)
        return dt.strftime("%Y-%m-%d %H:%M UTC") if dt else timestamp_str