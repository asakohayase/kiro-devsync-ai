"""PR status notification templates with specialized formatting for different PR states."""

from typing import Dict, List, Any, Optional
from abc import abstractmethod
from ..core.base_template import SlackMessageTemplate
from ..core.status_indicators import PRStatus, Priority


class PRTemplate(SlackMessageTemplate):
    """Base template class for PR status notifications with common PR formatting."""
    
    REQUIRED_FIELDS = ['pr']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create PR notification message blocks using template method pattern."""
        blocks = []
        
        pr_data = data['pr']
        
        # Create PR header with consistent formatting
        header_blocks = self.create_pr_header(pr_data)
        blocks.extend(header_blocks)
        
        # Add PR-specific content (implemented by subclasses)
        content_blocks = self._create_pr_content(pr_data, data)
        blocks.extend(content_blocks)
        
        # Create review section if reviewers exist
        review_section = self.create_review_section(pr_data)
        if review_section:
            blocks.append(review_section)
        
        # Add action buttons
        action_buttons = self.create_action_buttons(pr_data, data)
        if action_buttons:
            blocks.append(action_buttons)
        
        return blocks
    
    def create_pr_header(self, pr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create consistent PR header with title, status, and basic info."""
        blocks = []
        
        # Main title
        pr_number = pr_data.get('number', 'N/A')
        pr_title = pr_data.get('title', 'Untitled PR')
        title = f"PR #{pr_number}: {pr_title}"
        
        # Get PR status for header styling
        pr_status = self._get_pr_status(pr_data)
        status_indicator = self.status_system.get_pr_status_indicator(pr_status)
        
        # Create header with status
        blocks.extend(self._create_header_section(
            title=title,
            status=pr_status,
            subtitle=self._build_pr_subtitle(pr_data)
        ))
        
        # Status line with emoji and context
        status_text = f"*Status:* {status_indicator.emoji} {status_indicator.text}"
        blocks.append(self.create_section_block(status_text))
        
        return blocks
    
    def create_review_section(self, pr_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create reviewer assignment display section."""
        if not pr_data.get('reviewers'):
            return None
        
        reviewers = pr_data['reviewers']
        review_content = ["*👥 Reviewers:*"]
        
        # Show up to 5 reviewers with their status
        for reviewer in reviewers[:5]:
            if isinstance(reviewer, dict):
                username = reviewer.get('login', reviewer.get('username', 'Unknown'))
                status = reviewer.get('review_status', 'pending')
                status_emoji = {
                    'approved': '✅',
                    'changes_requested': '❌', 
                    'commented': '💬',
                    'pending': '⏳'
                }.get(status, '⏳')
                review_content.append(f"• {status_emoji} {self._format_user_mention(username)}")
            else:
                # Simple string username
                review_content.append(f"• ⏳ {self._format_user_mention(reviewer)}")
        
        if len(reviewers) > 5:
            review_content.append(f"• ... and {len(reviewers) - 5} more reviewers")
        
        return self.create_section_block("\n".join(review_content))
    
    def create_action_buttons(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create interactive PR action buttons based on PR state."""
        actions = []
        pr_url = pr_data.get('html_url', pr_data.get('url', '#'))
        pr_number = str(pr_data.get('number', ''))
        
        # Always include view PR button
        actions.append({
            'text': '👀 View PR',
            'action_id': 'view_pr',
            'url': pr_url,
            'style': 'primary'
        })
        
        # Get state-specific actions
        state_actions = self._get_state_specific_actions(pr_data, context_data)
        actions.extend(state_actions)
        
        # Common actions
        actions.extend([
            {'text': '💬 Comment', 'action_id': 'comment_pr', 'value': pr_number},
            {'text': '📊 Details', 'action_id': 'pr_details', 'value': pr_number}
        ])
        
        return self._create_action_buttons(actions)
    
    @abstractmethod
    def _create_pr_content(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create PR-specific content blocks. Must be implemented by subclasses."""
        pass
    
    def _get_state_specific_actions(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get actions specific to PR state. Can be overridden by subclasses."""
        return []
    
    def _get_pr_status(self, pr_data: Dict[str, Any]) -> PRStatus:
        """Determine PR status from PR data."""
        if pr_data.get('draft', False):
            return PRStatus.DRAFT
        elif pr_data.get('merged', False):
            return PRStatus.MERGED
        elif pr_data.get('state') == 'closed':
            return PRStatus.CLOSED
        elif pr_data.get('mergeable_state') == 'dirty':
            return PRStatus.CONFLICTS
        elif pr_data.get('review_decision') == 'APPROVED':
            return PRStatus.APPROVED
        elif pr_data.get('review_decision') == 'CHANGES_REQUESTED':
            return PRStatus.CHANGES_REQUESTED
        else:
            return PRStatus.OPEN
    
    def _build_pr_subtitle(self, pr_data: Dict[str, Any]) -> Optional[str]:
        """Build PR subtitle with branch and author info."""
        parts = []
        
        # Branch info
        head_ref = pr_data.get('head', {}).get('ref') or pr_data.get('head_ref')
        base_ref = pr_data.get('base', {}).get('ref') or pr_data.get('base_ref')
        if head_ref and base_ref:
            parts.append(f"`{head_ref}` → `{base_ref}`")
        
        # Author
        author = pr_data.get('user', {}).get('login') or pr_data.get('author')
        if author:
            parts.append(f"by {self._format_user_mention(author)}")
        
        return " • ".join(parts) if parts else None
    
    def _build_pr_details_fields(self, pr_data: Dict[str, Any]) -> Dict[str, str]:
        """Build common PR details fields."""
        fields = {}
        
        # Priority
        if pr_data.get('priority'):
            fields['Priority'] = self._get_priority_indicator(pr_data['priority'])
        
        # Labels
        if pr_data.get('labels'):
            labels = pr_data['labels'][:3]
            if isinstance(labels[0], dict):
                label_names = [label.get('name', str(label)) for label in labels]
            else:
                label_names = labels
            fields['Labels'] = ", ".join([f"`{label}`" for label in label_names])
            if len(pr_data['labels']) > 3:
                fields['Labels'] += f" (+{len(pr_data['labels'])-3} more)"
        
        # Milestone
        if pr_data.get('milestone'):
            milestone = pr_data['milestone']
            if isinstance(milestone, dict):
                fields['Milestone'] = milestone.get('title', str(milestone))
            else:
                fields['Milestone'] = str(milestone)
        
        # File changes
        if pr_data.get('changed_files') or pr_data.get('additions') is not None:
            changes = []
            if pr_data.get('changed_files'):
                changes.append(f"{pr_data['changed_files']} files")
            if pr_data.get('additions') is not None or pr_data.get('deletions') is not None:
                additions = pr_data.get('additions', 0)
                deletions = pr_data.get('deletions', 0)
                changes.append(f"+{additions} -{deletions}")
            fields['Changes'] = ", ".join(changes)
        
        return fields


class NewPRTemplate(PRTemplate):
    """Template for highlighting new PR creation with review requests."""
    
    def _create_pr_content(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create content for new PR notifications."""
        blocks = []
        
        # Highlight that this is a new PR
        blocks.append(self.create_section_block(
            "🆕 *New Pull Request Created*\n"
            "This PR is ready for review and feedback from the team."
        ))
        
        # PR details
        pr_fields = self._build_pr_details_fields(pr_data)
        if pr_fields:
            blocks.append(self.create_fields_section(pr_fields))
        
        # Description if provided
        if pr_data.get('body') or pr_data.get('description'):
            description = pr_data.get('body') or pr_data.get('description')
            description = self._truncate_text(description, 200)
            blocks.append(self.create_section_block(f"*Description:*\n{description}"))
        
        return blocks
    
    def _get_state_specific_actions(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get actions for new PR."""
        pr_number = str(pr_data.get('number', ''))
        return [
            {'text': '✅ Approve', 'action_id': 'approve_pr', 'value': pr_number, 'style': 'primary'},
            {'text': '❌ Request Changes', 'action_id': 'request_changes', 'value': pr_number, 'style': 'danger'}
        ]


class ReadyForReviewTemplate(PRTemplate):
    """Template emphasizing review readiness with reviewer assignments."""
    
    def _create_pr_content(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create content emphasizing review readiness."""
        blocks = []
        
        # Emphasize review readiness
        blocks.append(self.create_section_block(
            "🔍 *Ready for Review*\n"
            "This PR has been marked as ready for review. Please review and provide feedback."
        ))
        
        # Show CI/CD status if available
        if pr_data.get('checks') or pr_data.get('status_checks'):
            blocks.append(self._create_checks_section(pr_data))
        
        # PR details
        pr_fields = self._build_pr_details_fields(pr_data)
        if pr_fields:
            blocks.append(self.create_fields_section(pr_fields))
        
        return blocks
    
    def _create_checks_section(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create CI/CD checks status section."""
        content = ["*🔧 CI/CD Status:*"]
        
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
                content.append(" • ".join(check_parts))
        
        return self.create_section_block("\n".join(content))
    
    def _get_state_specific_actions(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get actions for ready for review PR."""
        pr_number = str(pr_data.get('number', ''))
        return [
            {'text': '✅ Approve', 'action_id': 'approve_pr', 'value': pr_number, 'style': 'primary'},
            {'text': '❌ Request Changes', 'action_id': 'request_changes', 'value': pr_number, 'style': 'danger'},
            {'text': '👀 Start Review', 'action_id': 'start_review', 'value': pr_number}
        ]


class ApprovedPRTemplate(PRTemplate):
    """Template showing merge readiness checklist with merge action buttons."""
    
    def _create_pr_content(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create content for approved PR with merge readiness."""
        blocks = []
        
        # Celebrate approval
        blocks.append(self.create_section_block(
            "🎉 *Pull Request Approved!*\n"
            "This PR has been approved and is ready for merge."
        ))
        
        # Merge readiness checklist
        checklist = self._create_merge_checklist(pr_data)
        blocks.append(checklist)
        
        # PR details
        pr_fields = self._build_pr_details_fields(pr_data)
        if pr_fields:
            blocks.append(self.create_fields_section(pr_fields))
        
        return blocks
    
    def _create_merge_checklist(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create merge readiness checklist."""
        checklist_items = []
        
        # Check CI status
        checks = pr_data.get('checks', {})
        if checks.get('failed', 0) == 0 and checks.get('pending', 0) == 0:
            checklist_items.append("✅ All CI checks passing")
        elif checks.get('pending', 0) > 0:
            checklist_items.append("⏳ CI checks still running")
        else:
            checklist_items.append("❌ Some CI checks failing")
        
        # Check conflicts
        if pr_data.get('mergeable_state') != 'dirty':
            checklist_items.append("✅ No merge conflicts")
        else:
            checklist_items.append("❌ Merge conflicts need resolution")
        
        # Check approvals
        if pr_data.get('review_decision') == 'APPROVED':
            checklist_items.append("✅ Required approvals received")
        else:
            checklist_items.append("⏳ Waiting for required approvals")
        
        # Branch protection
        if pr_data.get('mergeable', True):
            checklist_items.append("✅ Branch protection requirements met")
        else:
            checklist_items.append("❌ Branch protection requirements not met")
        
        content = "*🚀 Merge Readiness Checklist:*\n" + "\n".join(checklist_items)
        return self.create_section_block(content)
    
    def _get_state_specific_actions(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get actions for approved PR."""
        pr_number = str(pr_data.get('number', ''))
        base_branch = pr_data.get('base', {}).get('ref') or pr_data.get('base_ref', 'main')
        
        actions = [
            {'text': '🚀 Merge', 'action_id': 'merge_pr', 'value': pr_number, 'style': 'primary'}
        ]
        
        # Add merge options if available
        if pr_data.get('allow_squash_merge', True):
            actions.append({'text': '🔄 Squash & Merge', 'action_id': 'squash_merge', 'value': pr_number})
        
        return actions


class ConflictsTemplate(PRTemplate):
    """Template with warning styling and resolution guidance for PR conflicts."""
    
    def _create_pr_content(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create content for PR with conflicts."""
        blocks = []
        
        # Warning about conflicts
        blocks.append(self.create_section_block(
            "⚠️ *Merge Conflicts Detected*\n"
            "This PR has merge conflicts that must be resolved before it can be merged."
        ))
        
        # Resolution guidance
        resolution_guide = self._create_resolution_guidance(pr_data)
        blocks.append(resolution_guide)
        
        # Show conflicted files if available
        if pr_data.get('conflicted_files'):
            conflicts_section = self._create_conflicts_section(pr_data)
            blocks.append(conflicts_section)
        
        # PR details
        pr_fields = self._build_pr_details_fields(pr_data)
        if pr_fields:
            blocks.append(self.create_fields_section(pr_fields))
        
        return blocks
    
    def _create_resolution_guidance(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create conflict resolution guidance."""
        head_branch = pr_data.get('head', {}).get('ref') or pr_data.get('head_ref', 'feature-branch')
        base_branch = pr_data.get('base', {}).get('ref') or pr_data.get('base_ref', 'main')
        
        guidance = [
            "*🔧 Resolution Steps:*",
            f"1. `git checkout {head_branch}`",
            f"2. `git merge {base_branch}`",
            "3. Resolve conflicts in your editor",
            "4. `git add .` and `git commit`",
            "5. `git push` to update the PR"
        ]
        
        return self.create_section_block("\n".join(guidance))
    
    def _create_conflicts_section(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create section showing conflicted files."""
        conflicted_files = pr_data.get('conflicted_files', [])
        content = ["*📁 Conflicted Files:*"]
        
        for file_path in conflicted_files[:5]:  # Show max 5 files
            content.append(f"• `{file_path}`")
        
        if len(conflicted_files) > 5:
            content.append(f"• ... and {len(conflicted_files) - 5} more files")
        
        return self.create_section_block("\n".join(content))
    
    def _get_state_specific_actions(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get actions for PR with conflicts."""
        pr_number = str(pr_data.get('number', ''))
        pr_url = pr_data.get('html_url', pr_data.get('url', '#'))
        
        return [
            {'text': '🔧 Resolve Conflicts', 'action_id': 'resolve_conflicts', 'value': pr_number, 'style': 'danger'},
            {'text': '📝 View Conflicts', 'action_id': 'view_conflicts', 'url': f"{pr_url}/conflicts"},
            {'text': '📚 Help Guide', 'action_id': 'conflict_help', 'value': pr_number}
        ]


class MergedPRTemplate(PRTemplate):
    """Template with success celebration and deployment status for merged PRs."""
    
    def _create_pr_content(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create content for merged PR with celebration."""
        blocks = []
        
        # Celebration message
        merger = pr_data.get('merged_by', {}).get('login') or pr_data.get('merged_by') or 'Unknown'
        merge_time = pr_data.get('merged_at')
        
        celebration_text = f"🎉 *Pull Request Merged Successfully!*\n"
        celebration_text += f"Merged by {self._format_user_mention(merger)}"
        if merge_time:
            celebration_text += f" at {self._format_merge_time(merge_time)}"
        
        blocks.append(self.create_section_block(celebration_text))
        
        # Deployment status if available
        if pr_data.get('deployments') or context_data.get('deployment_status'):
            deployment_section = self._create_deployment_section(pr_data, context_data)
            blocks.append(deployment_section)
        
        # Merge statistics
        merge_stats = self._create_merge_statistics(pr_data)
        if merge_stats:
            blocks.append(merge_stats)
        
        # PR details
        pr_fields = self._build_pr_details_fields(pr_data)
        if pr_fields:
            blocks.append(self.create_fields_section(pr_fields))
        
        return blocks
    
    def _create_deployment_section(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create deployment status section."""
        content = ["*🚀 Deployment Status:*"]
        
        # Check for deployment info in PR data
        if pr_data.get('deployments'):
            for deployment in pr_data['deployments'][:3]:  # Show max 3 deployments
                env = deployment.get('environment', 'unknown')
                status = deployment.get('status', 'unknown')
                status_emoji = {
                    'success': '✅',
                    'failure': '❌',
                    'pending': '⏳',
                    'in_progress': '🔄'
                }.get(status, '❓')
                content.append(f"• {status_emoji} {env.title()}: {status}")
        
        # Check context data for deployment status
        elif context_data.get('deployment_status'):
            deployment_status = context_data['deployment_status']
            content.append(f"• {deployment_status}")
        else:
            content.append("• 🔄 Deployment pipeline triggered")
        
        return self.create_section_block("\n".join(content))
    
    def _create_merge_statistics(self, pr_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Create merge statistics fields."""
        fields = {}
        
        # Merge method
        if pr_data.get('merge_commit_sha'):
            fields['Merge Type'] = 'Merge commit'
        elif pr_data.get('squashed', False):
            fields['Merge Type'] = 'Squash and merge'
        else:
            fields['Merge Type'] = 'Standard merge'
        
        # Time to merge (if available)
        if pr_data.get('created_at') and pr_data.get('merged_at'):
            created = self._parse_timestamp(pr_data['created_at'])
            merged = self._parse_timestamp(pr_data['merged_at'])
            if created and merged:
                duration = merged - created
                if duration.days > 0:
                    fields['Time to Merge'] = f"{duration.days} days"
                else:
                    hours = duration.seconds // 3600
                    fields['Time to Merge'] = f"{hours} hours"
        
        return fields if fields else None
    
    def _format_merge_time(self, merge_time: str) -> str:
        """Format merge timestamp for display."""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(merge_time.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, AttributeError):
            return merge_time
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[object]:
        """Parse timestamp string to datetime."""
        try:
            from datetime import datetime
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    def _get_state_specific_actions(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get actions for merged PR."""
        head_branch = pr_data.get('head', {}).get('ref') or pr_data.get('head_ref')
        pr_number = str(pr_data.get('number', ''))
        
        actions = []
        
        # Delete branch option
        if head_branch and head_branch not in ['main', 'master', 'develop']:
            actions.append({
                'text': '🗑️ Delete Branch',
                'action_id': 'delete_branch',
                'value': head_branch,
                'style': 'danger'
            })
        
        # Deploy option
        actions.extend([
            {'text': '🚀 Deploy', 'action_id': 'deploy', 'value': pr_number, 'style': 'primary'},
            {'text': '📊 View Deployment', 'action_id': 'view_deployment', 'value': pr_number}
        ])
        
        return actions


class ClosedPRTemplate(PRTemplate):
    """Template with closure notification and reopen options for closed PRs."""
    
    def _create_pr_content(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create content for closed PR."""
        blocks = []
        
        # Closure notification
        closer = pr_data.get('closed_by', {}).get('login') or pr_data.get('closed_by') or 'Unknown'
        close_time = pr_data.get('closed_at')
        
        closure_text = f"🚫 *Pull Request Closed*\n"
        closure_text += f"Closed by {self._format_user_mention(closer)}"
        if close_time:
            closure_text += f" at {self._format_close_time(close_time)}"
        
        blocks.append(self.create_section_block(closure_text))
        
        # Closure reason if available
        if context_data.get('close_reason') or pr_data.get('close_reason'):
            reason = context_data.get('close_reason') or pr_data.get('close_reason')
            blocks.append(self.create_section_block(f"*Reason:* {reason}"))
        
        # PR summary
        summary_fields = self._create_closure_summary(pr_data)
        if summary_fields:
            blocks.append(self.create_fields_section(summary_fields))
        
        # PR details
        pr_fields = self._build_pr_details_fields(pr_data)
        if pr_fields:
            blocks.append(self.create_fields_section(pr_fields))
        
        return blocks
    
    def _create_closure_summary(self, pr_data: Dict[str, Any]) -> Dict[str, str]:
        """Create summary of closed PR."""
        fields = {}
        
        # Duration
        if pr_data.get('created_at') and pr_data.get('closed_at'):
            created = self._parse_timestamp(pr_data['created_at'])
            closed = self._parse_timestamp(pr_data['closed_at'])
            if created and closed:
                duration = closed - created
                if duration.days > 0:
                    fields['Duration'] = f"{duration.days} days"
                else:
                    hours = duration.seconds // 3600
                    fields['Duration'] = f"{hours} hours"
        
        # Review status
        if pr_data.get('review_decision'):
            decision = pr_data['review_decision']
            decision_emoji = {
                'APPROVED': '✅',
                'CHANGES_REQUESTED': '❌',
                'REVIEW_REQUIRED': '⏳'
            }.get(decision, '❓')
            fields['Final Review Status'] = f"{decision_emoji} {decision.replace('_', ' ').title()}"
        
        # Comments count
        if pr_data.get('comments'):
            fields['Comments'] = str(pr_data['comments'])
        
        return fields
    
    def _format_close_time(self, close_time: str) -> str:
        """Format close timestamp for display."""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, AttributeError):
            return close_time
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[object]:
        """Parse timestamp string to datetime."""
        try:
            from datetime import datetime
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    def _get_state_specific_actions(self, pr_data: Dict[str, Any], context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get actions for closed PR."""
        pr_number = str(pr_data.get('number', ''))
        
        return [
            {'text': '🔄 Reopen', 'action_id': 'reopen_pr', 'value': pr_number, 'style': 'primary'},
            {'text': '📋 Create New PR', 'action_id': 'create_new_pr', 'value': pr_number},
            {'text': '📊 View History', 'action_id': 'pr_history', 'value': pr_number}
        ]