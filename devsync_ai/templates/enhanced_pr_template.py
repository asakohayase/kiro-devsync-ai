"""Enhanced PR template using Block Kit builders."""

from typing import Dict, List, Any
from datetime import datetime
from ..core.base_template import SlackMessageTemplate
from ..core.block_kit_builders import BlockKitBuilder, HeaderConfig, ActionButton, ButtonStyle
from ..core.status_indicators import PRStatus, Priority


class EnhancedPRTemplate(SlackMessageTemplate):
    """Enhanced PR template using Block Kit component builders."""
    
    REQUIRED_FIELDS = ['pr', 'action']
    
    def __init__(self, *args, **kwargs):
        """Initialize with Block Kit builder."""
        super().__init__(*args, **kwargs)
        self.builder = BlockKitBuilder(self.status_system)
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create PR notification using Block Kit builders."""
        blocks = []
        
        pr_data = data['pr']
        action = data['action']
        
        # Map action to PR status
        status_mapping = {
            'opened': 'open',
            'draft': 'draft',
            'ready_for_review': 'ready_for_review',
            'approved': 'approved',
            'changes_requested': 'changes_requested',
            'merged': 'merged',
            'closed': 'closed',
            'conflicts': 'conflicts'
        }
        
        pr_status = status_mapping.get(action, 'open')
        
        # Build header with status and actions
        header_config = HeaderConfig(
            title=f"PR #{pr_data.get('number', 'N/A')}: {pr_data.get('title', 'Untitled PR')}",
            status=pr_status,
            status_context="pr",
            timestamp=datetime.fromisoformat(pr_data.get('created_at', datetime.now().isoformat())) if pr_data.get('created_at') else None,
            subtitle=self._get_pr_subtitle(pr_data, action),
            description=pr_data.get('description') if len(pr_data.get('description', '')) < 150 else None,
            actions=self._get_header_actions(pr_status, pr_data)
        )
        
        blocks.extend(self.builder.build_header(header_config))
        
        # Build main content section with fields
        content_fields = self._build_pr_fields(pr_data, pr_status)
        if content_fields:
            blocks.append(self.builder.build_field_group(content_fields))
        
        # Add status-specific content
        status_content = self._get_status_specific_content(pr_status, pr_data)
        if status_content:
            blocks.append(self.builder.build_rich_text_section(status_content))
        
        # Add description if too long for header
        if pr_data.get('description') and len(pr_data.get('description', '')) >= 150:
            description = self._truncate_text(pr_data['description'], 300)
            blocks.append(self.builder.build_section({
                "text": f"*Description:*\n{description}"
            }))
        
        # Add checks section if available
        if pr_data.get('checks'):
            blocks.append(self._build_checks_section(pr_data['checks']))
        
        # Add conditional divider before actions
        divider = self.builder.build_conditional_divider(len(blocks) > 2)
        if divider:
            blocks.append(divider)
        
        # Add main action buttons
        main_actions = self._get_main_actions(pr_status, pr_data)
        if main_actions:
            blocks.append(self.builder.build_action_buttons(main_actions))
        
        return blocks
    
    def _get_pr_subtitle(self, pr_data: Dict[str, Any], action: str) -> str:
        """Generate subtitle based on PR data and action."""
        parts = []
        
        # Branch info
        if pr_data.get('head_branch') and pr_data.get('base_branch'):
            parts.append(f"`{pr_data['head_branch']}` → `{pr_data['base_branch']}`")
        
        # Author
        if pr_data.get('author'):
            parts.append(f"by {self.builder.build_user_mention(pr_data['author'])}")
        
        return " • ".join(parts) if parts else None
    
    def _build_pr_fields(self, pr_data: Dict[str, Any], pr_status: str) -> Dict[str, str]:
        """Build PR information fields."""
        fields = {}
        
        # Priority with indicator
        if pr_data.get('priority'):
            try:
                priority = Priority(pr_data['priority'].lower())
                priority_indicator = self.status_system.get_priority_indicator(priority)
                fields['Priority'] = f"{priority_indicator.emoji} {priority_indicator.text}"
            except ValueError:
                fields['Priority'] = self._get_priority_indicator(pr_data['priority'])
        
        # Reviewers
        if pr_data.get('reviewers'):
            reviewers = pr_data['reviewers'][:3]
            reviewer_mentions = [self.builder.build_user_mention(r) for r in reviewers]
            fields['Reviewers'] = ", ".join(reviewer_mentions)
            if len(pr_data['reviewers']) > 3:
                fields['Reviewers'] += f" (+{len(pr_data['reviewers'])-3} more)"
        
        # Files changed
        if pr_data.get('files_changed'):
            fields['Files'] = f"{pr_data['files_changed']} files"
        
        # Lines changed
        if pr_data.get('additions') is not None and pr_data.get('deletions') is not None:
            additions = pr_data['additions']
            deletions = pr_data['deletions']
            fields['Changes'] = f"+{additions} -{deletions} lines"
        
        # Labels
        if pr_data.get('labels'):
            labels = pr_data['labels'][:3]
            fields['Labels'] = ", ".join([f"`{label}`" for label in labels])
            if len(pr_data['labels']) > 3:
                fields['Labels'] += f" (+{len(pr_data['labels'])-3} more)"
        
        return fields
    
    def _get_status_specific_content(self, pr_status: str, pr_data: Dict[str, Any]) -> str:
        """Get status-specific content text."""
        if pr_status == 'conflicts':
            return "⚠️ *This PR has merge conflicts that need to be resolved before it can be merged.*"
        elif pr_status == 'changes_requested':
            return "📝 *Changes have been requested by reviewers. Please address the feedback and push updates.*"
        elif pr_status == 'approved':
            return "🚀 *This PR has been approved and is ready to be merged!*"
        elif pr_status == 'merged':
            return "🎉 *This PR has been successfully merged into the base branch.*"
        elif pr_status == 'draft':
            return "📝 *This is a draft PR. Mark it as ready for review when you're done making changes.*"
        
        return None
    
    def _build_checks_section(self, checks: Dict[str, Any]) -> Dict[str, Any]:
        """Build checks status section."""
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
        
        if not check_parts:
            return None
        
        # Determine overall status
        if failed > 0:
            status_emoji = "❌"
            status_text = "Some checks failed"
        elif pending > 0:
            status_emoji = "⏳"
            status_text = "Checks in progress"
        else:
            status_emoji = "✅"
            status_text = "All checks passed"
        
        content = f"*Checks:* {status_emoji} {status_text}\n{' • '.join(check_parts)}"
        
        return self.builder.build_section({"text": content})
    
    def _get_header_actions(self, pr_status: str, pr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get header-level actions (always visible)."""
        actions = []
        
        # Always include view PR button
        if pr_data.get('url'):
            actions.append({
                "label": "👀 View PR",
                "url": pr_data['url'],
                "style": "primary"
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
                    "style": "danger",
                    "confirm": self.builder.create_confirmation_dialog(
                        title="Request Changes",
                        text="Are you sure you want to request changes to this PR?",
                        confirm_text="Request Changes",
                        deny_text="Cancel"
                    )
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
                        text=f"Are you sure you want to merge PR #{pr_number}?",
                        confirm_text="Merge",
                        deny_text="Cancel"
                    )
                },
                {
                    "label": "❌ Request Changes",
                    "action_id": "request_changes",
                    "value": pr_number,
                    "style": "danger"
                }
            ])
        
        elif pr_status == 'conflicts':
            actions.extend([
                {
                    "label": "🔧 Resolve Conflicts",
                    "action_id": "resolve_conflicts",
                    "value": pr_number,
                    "style": "danger"
                },
                {
                    "label": "📝 View Conflicts",
                    "url": f"{pr_data.get('url', '#')}/conflicts"
                }
            ])
        
        elif pr_status == 'changes_requested':
            actions.extend([
                {
                    "label": "🔄 Push Changes",
                    "action_id": "push_changes",
                    "value": pr_number,
                    "style": "primary"
                },
                {
                    "label": "💬 Respond",
                    "action_id": "respond_to_review",
                    "value": pr_number
                }
            ])
        
        elif pr_status == 'merged':
            actions.extend([
                {
                    "label": "🗑️ Delete Branch",
                    "action_id": "delete_branch",
                    "value": pr_data.get('head_branch', ''),
                    "style": "danger",
                    "confirm": self.builder.create_confirmation_dialog(
                        title="Delete Branch",
                        text=f"Delete the `{pr_data.get('head_branch', 'unknown')}` branch?",
                        confirm_text="Delete",
                        deny_text="Keep"
                    )
                },
                {
                    "label": "🚀 Deploy",
                    "action_id": "deploy",
                    "value": pr_number
                }
            ])
        
        return actions