"""
Specialized PR status templates for different scenarios.
Extends the base PR template with scenario-specific formatting.
"""

from typing import Dict, Any
from .slack_templates import PRStatusTemplate, SlackTemplateBase


class NewPRTemplate(PRStatusTemplate):
    """Template for newly opened PRs."""
    
    def _build_template(self) -> None:
        """Build template for new PR."""
        pr = self.data.get('pr', {})
        
        self.add_header(f"New PR #{pr.get('id', 'N/A')}: {pr.get('title', 'Unknown')}", "🆕")
        
        # Highlight that this is a new PR
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🎉 New pull request opened by {pr.get('author', 'Unknown')}*\n{pr.get('description', '')[:150]}{'...' if len(pr.get('description', '')) > 150 else ''}"
            }
        })
        
        self._add_pr_details()
        self._add_changes_summary()
        
        if pr.get('jira_tickets'):
            self._add_related_tickets()
        
        # Special actions for new PRs
        self._add_new_pr_actions()
        self._add_pr_footer()
    
    def _add_new_pr_actions(self) -> None:
        """Add actions specific to new PRs."""
        pr = self.data.get('pr', {})
        pr_id = pr.get('id', '')
        
        buttons = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "👀 Review Now",
                    "emoji": True
                },
                "url": f"https://github.com/repo/pull/{pr_id}",
                "action_id": "review_pr",
                "style": "primary"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📋 Add to Review Queue",
                    "emoji": True
                },
                "value": f"queue_{pr_id}",
                "action_id": "add_to_queue"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🏷️ Add Labels",
                    "emoji": True
                },
                "value": f"labels_{pr_id}",
                "action_id": "add_labels"
            }
        ]
        
        self.blocks.append({
            "type": "actions",
            "elements": buttons
        })


class PRReadyForReviewTemplate(PRStatusTemplate):
    """Template for PRs ready for review."""
    
    def _build_template(self) -> None:
        """Build template for PR ready for review."""
        pr = self.data.get('pr', {})
        
        self.add_header(f"PR #{pr.get('id', 'N/A')} Ready for Review", "👀")
        
        # Emphasize review readiness
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🚀 {pr.get('title', 'Unknown')} is ready for review!*\n{pr.get('author', 'Unknown')} has marked this PR as ready."
            }
        })
        
        self._add_pr_details()
        self._add_status_section()
        self._add_changes_summary()
        
        # Review assignment section
        self._add_review_assignment()
        
        if pr.get('jira_tickets'):
            self._add_related_tickets()
        
        self._add_review_actions()
        self._add_pr_footer()
    
    def _add_review_assignment(self) -> None:
        """Add review assignment information."""
        pr = self.data.get('pr', {})
        reviewers = pr.get('reviewers', [])
        
        if reviewers:
            reviewer_list = ", ".join([f"@{reviewer}" for reviewer in reviewers])
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*👥 Assigned Reviewers:* {reviewer_list}\n_Please review when you have a chance!_"
                }
            })
    
    def _add_review_actions(self) -> None:
        """Add review-specific actions."""
        pr = self.data.get('pr', {})
        pr_id = pr.get('id', '')
        
        buttons = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "✅ Start Review",
                    "emoji": True
                },
                "url": f"https://github.com/repo/pull/{pr_id}/files",
                "action_id": "start_review",
                "style": "primary"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "⏰ Remind Me Later",
                    "emoji": True
                },
                "value": f"remind_{pr_id}",
                "action_id": "remind_later"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "👤 Reassign",
                    "emoji": True
                },
                "value": f"reassign_{pr_id}",
                "action_id": "reassign_reviewer"
            }
        ]
        
        self.blocks.append({
            "type": "actions",
            "elements": buttons
        })


class PRApprovedTemplate(PRStatusTemplate):
    """Template for approved PRs."""
    
    def _build_template(self) -> None:
        """Build template for approved PR."""
        pr = self.data.get('pr', {})
        approved_by = pr.get('approved_by', [])
        
        self.add_header(f"PR #{pr.get('id', 'N/A')} Approved!", "✅")
        
        # Celebration message
        approver_list = ", ".join([f"@{approver}" for approver in approved_by])
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🎉 {pr.get('title', 'Unknown')} has been approved!*\nApproved by: {approver_list}"
            }
        })
        
        self._add_pr_details()
        self._add_changes_summary()
        
        # Merge readiness check
        self._add_merge_readiness()
        
        if pr.get('jira_tickets'):
            self._add_related_tickets()
        
        self._add_merge_actions()
        self._add_pr_footer()
    
    def _add_merge_readiness(self) -> None:
        """Add merge readiness indicators."""
        pr = self.data.get('pr', {})
        
        checks = []
        
        # CI status
        ci_status = pr.get('ci_status', 'unknown')
        if ci_status == 'passing':
            checks.append("✅ CI passing")
        elif ci_status == 'failing':
            checks.append("❌ CI failing")
        else:
            checks.append("⏳ CI running")
        
        # Conflicts
        if pr.get('has_conflicts', False):
            checks.append("❌ Has merge conflicts")
        else:
            checks.append("✅ No conflicts")
        
        # Required approvals
        required_approvals = pr.get('required_approvals', 1)
        current_approvals = len(pr.get('approved_by', []))
        if current_approvals >= required_approvals:
            checks.append(f"✅ Approvals ({current_approvals}/{required_approvals})")
        else:
            checks.append(f"⏳ Approvals ({current_approvals}/{required_approvals})")
        
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🔍 Merge Readiness:*\n" + "\n".join([f"• {check}" for check in checks])
            }
        })
    
    def _add_merge_actions(self) -> None:
        """Add merge-specific actions."""
        pr = self.data.get('pr', {})
        pr_id = pr.get('id', '')
        
        # Check if ready to merge
        can_merge = (
            pr.get('ci_status') == 'passing' and
            not pr.get('has_conflicts', False) and
            len(pr.get('approved_by', [])) >= pr.get('required_approvals', 1)
        )
        
        buttons = []
        
        if can_merge:
            buttons.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🚀 Merge Now",
                    "emoji": True
                },
                "value": f"merge_{pr_id}",
                "action_id": "merge_pr",
                "style": "primary"
            })
        
        buttons.extend([
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "👀 View Changes",
                    "emoji": True
                },
                "url": f"https://github.com/repo/pull/{pr_id}/files",
                "action_id": "view_changes"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📝 Add Comment",
                    "emoji": True
                },
                "value": f"comment_{pr_id}",
                "action_id": "add_comment"
            }
        ])
        
        self.blocks.append({
            "type": "actions",
            "elements": buttons
        })


class PRConflictsTemplate(PRStatusTemplate):
    """Template for PRs with merge conflicts."""
    
    def _build_template(self) -> None:
        """Build template for PR with conflicts."""
        pr = self.data.get('pr', {})
        
        self.add_header(f"PR #{pr.get('id', 'N/A')} Has Conflicts", "⚠️")
        
        # Warning message
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*⚠️ {pr.get('title', 'Unknown')} has merge conflicts*\n{pr.get('author', 'Unknown')} needs to resolve conflicts before this can be merged."
            }
        })
        
        self._add_pr_details()
        
        # Conflict resolution guidance
        self._add_conflict_guidance()
        
        self._add_changes_summary()
        
        if pr.get('jira_tickets'):
            self._add_related_tickets()
        
        self._add_conflict_actions()
        self._add_pr_footer()
    
    def _add_conflict_guidance(self) -> None:
        """Add conflict resolution guidance."""
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🔧 To resolve conflicts:*\n1. Pull the latest changes from main\n2. Resolve conflicts in your IDE\n3. Commit the resolution\n4. Push to update this PR"
            }
        })
    
    def _add_conflict_actions(self) -> None:
        """Add conflict resolution actions."""
        pr = self.data.get('pr', {})
        pr_id = pr.get('id', '')
        
        buttons = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🔧 Resolve Conflicts",
                    "emoji": True
                },
                "url": f"https://github.com/repo/pull/{pr_id}/conflicts",
                "action_id": "resolve_conflicts",
                "style": "primary"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📞 Get Help",
                    "emoji": True
                },
                "value": f"help_{pr_id}",
                "action_id": "get_help"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "⏸️ Pause Review",
                    "emoji": True
                },
                "value": f"pause_{pr_id}",
                "action_id": "pause_review"
            }
        ]
        
        self.blocks.append({
            "type": "actions",
            "elements": buttons
        })


class PRMergedTemplate(PRStatusTemplate):
    """Template for merged PRs."""
    
    def _build_template(self) -> None:
        """Build template for merged PR."""
        pr = self.data.get('pr', {})
        
        self.add_header(f"PR #{pr.get('id', 'N/A')} Merged!", "🎉")
        
        # Success message
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🎉 {pr.get('title', 'Unknown')} has been merged!*\nGreat work {pr.get('author', 'Unknown')}! Your changes are now in main."
            }
        })
        
        self._add_pr_details()
        self._add_changes_summary()
        
        # Deployment status
        self._add_deployment_status()
        
        if pr.get('jira_tickets'):
            self._add_ticket_updates()
        
        self._add_post_merge_actions()
        self._add_pr_footer()
    
    def _add_deployment_status(self) -> None:
        """Add deployment status information."""
        deployment_status = self.data.get('deployment_status', 'pending')
        
        status_messages = {
            'pending': "⏳ Deployment pending",
            'deploying': "🚀 Deploying to staging",
            'deployed': "✅ Deployed successfully",
            'failed': "❌ Deployment failed"
        }
        
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🚀 Deployment:* {status_messages.get(deployment_status, 'Unknown status')}"
            }
        })
    
    def _add_ticket_updates(self) -> None:
        """Add JIRA ticket update information."""
        pr = self.data.get('pr', {})
        jira_tickets = pr.get('jira_tickets', [])
        
        if jira_tickets:
            tickets_text = "*🎫 JIRA Updates:* "
            ticket_links = []
            for ticket in jira_tickets:
                ticket_links.append(f"<https://jira.company.com/browse/{ticket}|{ticket}>")
            
            tickets_text += ", ".join(ticket_links)
            tickets_text += "\n_Tickets will be automatically updated with merge information._"
            
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": tickets_text
                }
            })
    
    def _add_post_merge_actions(self) -> None:
        """Add post-merge actions."""
        pr = self.data.get('pr', {})
        pr_id = pr.get('id', '')
        
        buttons = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🚀 View Deployment",
                    "emoji": True
                },
                "url": "https://staging.company.com",
                "action_id": "view_deployment"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📊 View Metrics",
                    "emoji": True
                },
                "value": f"metrics_{pr_id}",
                "action_id": "view_metrics"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🗑️ Delete Branch",
                    "emoji": True
                },
                "value": f"delete_branch_{pr_id}",
                "action_id": "delete_branch"
            }
        ]
        
        self.blocks.append({
            "type": "actions",
            "elements": buttons
        })


class PRClosedTemplate(PRStatusTemplate):
    """Template for closed PRs (without merging)."""
    
    def _build_template(self) -> None:
        """Build template for closed PR."""
        pr = self.data.get('pr', {})
        
        self.add_header(f"PR #{pr.get('id', 'N/A')} Closed", "❌")
        
        # Closure message
        close_reason = self.data.get('close_reason', 'No reason provided')
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*❌ {pr.get('title', 'Unknown')} has been closed*\nReason: {close_reason}"
            }
        })
        
        self._add_pr_details()
        self._add_changes_summary()
        
        if pr.get('jira_tickets'):
            self._add_related_tickets()
        
        self._add_closure_actions()
        self._add_pr_footer()
    
    def _add_closure_actions(self) -> None:
        """Add closure-related actions."""
        pr = self.data.get('pr', {})
        pr_id = pr.get('id', '')
        
        buttons = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🔄 Reopen",
                    "emoji": True
                },
                "value": f"reopen_{pr_id}",
                "action_id": "reopen_pr"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📝 Add Comment",
                    "emoji": True
                },
                "value": f"comment_{pr_id}",
                "action_id": "add_comment"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🗑️ Delete Branch",
                    "emoji": True
                },
                "value": f"delete_branch_{pr_id}",
                "action_id": "delete_branch"
            }
        ]
        
        self.blocks.append({
            "type": "actions",
            "elements": buttons
        })


# Template factory function
def create_pr_message_by_action(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create appropriate PR message based on action type."""
    action = data.get('action', 'updated')
    
    template_map = {
        'opened': NewPRTemplate,
        'ready_for_review': PRReadyForReviewTemplate,
        'approved': PRApprovedTemplate,
        'has_conflicts': PRConflictsTemplate,
        'merged': PRMergedTemplate,
        'closed': PRClosedTemplate,
        'review_requested': PRReadyForReviewTemplate,
        'changes_requested': PRStatusTemplate,  # Use base template
    }
    
    template_class = template_map.get(action, PRStatusTemplate)
    template = template_class(data)
    return template.get_message()