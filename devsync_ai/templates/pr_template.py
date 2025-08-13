"""PR notification template with comprehensive status indicators."""

from typing import Dict, List, Any
from ..core.base_template import SlackMessageTemplate
from ..core.status_indicators import PRStatus, Priority


class PRTemplate(SlackMessageTemplate):
    """Template for PR status notification messages."""
    
    REQUIRED_FIELDS = ['pr', 'action']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create PR notification message blocks."""
        blocks = []
        
        pr_data = data['pr']
        action = data['action']
        
        # Map action to PR status
        status_mapping = {
            'opened': PRStatus.OPEN,
            'draft': PRStatus.DRAFT,
            'ready_for_review': PRStatus.READY_FOR_REVIEW,
            'approved': PRStatus.APPROVED,
            'changes_requested': PRStatus.CHANGES_REQUESTED,
            'merged': PRStatus.MERGED,
            'closed': PRStatus.CLOSED,
            'conflicts': PRStatus.CONFLICTS
        }
        
        pr_status = status_mapping.get(action, PRStatus.OPEN)
        status_indicator = self.status_system.get_pr_status_indicator(pr_status)
        
        # Header with PR status
        title = f"PR #{pr_data.get('number', 'N/A')}: {pr_data.get('title', 'Untitled PR')}"
        blocks.extend(self._create_header_section(title))
        
        # Status section with visual indicator
        status_text = f"*Status:* {status_indicator.emoji} {status_indicator.text}"
        if action == 'conflicts':
            status_text += "\n⚠️ *This PR has merge conflicts that need to be resolved*"
        elif action == 'changes_requested':
            status_text += "\n📝 *Changes have been requested by reviewers*"
        elif action == 'approved':
            status_text += "\n🚀 *This PR is ready to be merged*"
        
        blocks.append(self.create_section_block(status_text))
        
        # PR details
        pr_fields = {}
        
        # Author
        if 'author' in pr_data:
            pr_fields['Author'] = self._format_user_mention(pr_data['author'])
        
        # Branch info
        if 'head_branch' in pr_data and 'base_branch' in pr_data:
            pr_fields['Branch'] = f"`{pr_data['head_branch']}` → `{pr_data['base_branch']}`"
        
        # Priority if specified
        if 'priority' in pr_data:
            priority_str = pr_data['priority'].lower()
            try:
                priority = Priority(priority_str)
                priority_indicator = self.status_system.get_priority_indicator(priority)
                pr_fields['Priority'] = f"{priority_indicator.emoji} {priority_indicator.text}"
            except ValueError:
                pr_fields['Priority'] = self._get_priority_indicator(pr_data['priority'])
        
        # Reviewers
        if 'reviewers' in pr_data and pr_data['reviewers']:
            reviewers = pr_data['reviewers'][:3]  # Show max 3 reviewers
            reviewer_mentions = [self._format_user_mention(r) for r in reviewers]
            pr_fields['Reviewers'] = ", ".join(reviewer_mentions)
            if len(pr_data['reviewers']) > 3:
                pr_fields['Reviewers'] += f" (+{len(pr_data['reviewers'])-3} more)"
        
        # Checks status
        if 'checks' in pr_data:
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
                pr_fields['Checks'] = " • ".join(check_parts)
        
        if pr_fields:
            blocks.append(self.create_fields_section(pr_fields))
        
        # Description if provided
        if pr_data.get('description'):
            description = self._truncate_text(pr_data['description'], 200)
            blocks.append(self.create_section_block(f"*Description:*\n{description}"))
        
        # Action buttons based on PR status
        actions = self._get_pr_actions(pr_status, pr_data)
        action_block = self._create_action_buttons(actions)
        if action_block:
            blocks.append(action_block)
        
        return blocks
    
    def _get_pr_actions(self, status: PRStatus, pr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get appropriate action buttons based on PR status."""
        actions = []
        pr_url = pr_data.get('url', '#')
        
        # Always include view PR button
        actions.append({
            'text': '👀 View PR',
            'action_id': 'view_pr',
            'url': pr_url,
            'style': 'primary'
        })
        
        if status == PRStatus.OPEN or status == PRStatus.READY_FOR_REVIEW:
            actions.extend([
                {'text': '✅ Approve', 'action_id': 'approve_pr', 'value': str(pr_data.get('number', ''))},
                {'text': '💬 Comment', 'action_id': 'comment_pr', 'value': str(pr_data.get('number', ''))}
            ])
        
        elif status == PRStatus.APPROVED:
            actions.extend([
                {'text': '🚀 Merge', 'action_id': 'merge_pr', 'value': str(pr_data.get('number', '')), 'style': 'primary'},
                {'text': '❌ Request Changes', 'action_id': 'request_changes', 'value': str(pr_data.get('number', ''))}
            ])
        
        elif status == PRStatus.CONFLICTS:
            actions.extend([
                {'text': '🔧 Resolve Conflicts', 'action_id': 'resolve_conflicts', 'value': str(pr_data.get('number', '')), 'style': 'danger'},
                {'text': '📝 View Conflicts', 'action_id': 'view_conflicts', 'url': f"{pr_url}/conflicts"}
            ])
        
        elif status == PRStatus.CHANGES_REQUESTED:
            actions.extend([
                {'text': '🔄 Push Changes', 'action_id': 'push_changes', 'value': str(pr_data.get('number', ''))},
                {'text': '💬 Respond', 'action_id': 'respond_to_review', 'value': str(pr_data.get('number', ''))}
            ])
        
        elif status == PRStatus.MERGED:
            actions.extend([
                {'text': '🗑️ Delete Branch', 'action_id': 'delete_branch', 'value': pr_data.get('head_branch', '')},
                {'text': '🚀 Deploy', 'action_id': 'deploy', 'value': str(pr_data.get('number', ''))}
            ])
        
        return actions