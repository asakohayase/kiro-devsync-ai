"""Interactive element builders for user engagement in Slack messages."""

import json
import hashlib
import hmac
import time
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging


class ActionType(Enum):
    """Types of interactive actions."""
    APPROVE_PR = "approve_pr"
    REJECT_PR = "reject_pr"
    MERGE_PR = "merge_pr"
    ACKNOWLEDGE_ALERT = "acknowledge_alert"
    RESOLVE_BLOCKER = "resolve_blocker"
    UPDATE_JIRA_STATUS = "update_jira_status"
    ASSIGN_TICKET = "assign_ticket"
    CHANGE_PRIORITY = "change_priority"
    ADD_COMMENT = "add_comment"
    LOG_TIME = "log_time"
    SHOW_DETAILS = "show_details"
    EXTERNAL_LINK = "external_link"
    CUSTOM_ACTION = "custom_action"


class ButtonStyle(Enum):
    """Button styling options."""
    PRIMARY = "primary"
    DANGER = "danger"
    DEFAULT = "default"


class ConfirmationLevel(Enum):
    """Levels of confirmation required."""
    NONE = "none"
    SIMPLE = "simple"
    DETAILED = "detailed"
    MULTI_STEP = "multi_step"


@dataclass
class ActionPayload:
    """Secure payload for interactive actions."""
    action_type: ActionType
    resource_id: str
    user_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    signature: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'action_type': self.action_type.value,
            'resource_id': self.resource_id,
            'user_id': self.user_id,
            'timestamp': self.timestamp,
            'metadata': self.metadata,
            'signature': self.signature
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionPayload':
        """Create from dictionary."""
        return cls(
            action_type=ActionType(data['action_type']),
            resource_id=data['resource_id'],
            user_id=data.get('user_id'),
            timestamp=data.get('timestamp', time.time()),
            metadata=data.get('metadata', {}),
            signature=data.get('signature')
        )


@dataclass
class InteractiveConfig:
    """Configuration for interactive elements."""
    enable_confirmations: bool = True
    enable_audit_logging: bool = True
    rate_limit_per_user: int = 100  # actions per hour
    session_timeout: int = 3600  # seconds
    require_authorization: bool = True
    allowed_domains: List[str] = field(default_factory=list)
    secret_key: Optional[str] = None


class InteractiveElementBuilder:
    """Builder for interactive Slack elements with security features."""
    
    def __init__(self, config: Optional[InteractiveConfig] = None):
        """Initialize with configuration."""
        self.config = config or InteractiveConfig()
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting storage (in production, use Redis or similar)
        self._rate_limits: Dict[str, List[float]] = {}
        
        # Action registry for validation
        self._registered_actions: Dict[str, Dict[str, Any]] = {}
        
        # Audit log storage
        self._audit_log: List[Dict[str, Any]] = []
    
    def create_button(self,
                     text: str,
                     action_type: ActionType,
                     resource_id: str,
                     style: ButtonStyle = ButtonStyle.DEFAULT,
                     confirmation: Optional[Dict[str, str]] = None,
                     url: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create an interactive button with security features."""
        
        # Create secure payload
        payload = ActionPayload(
            action_type=action_type,
            resource_id=resource_id,
            metadata=metadata or {}
        )
        
        # Sign the payload for security
        if self.config.secret_key:
            payload.signature = self._sign_payload(payload)
        
        # Create button element
        button = {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": text,
                "emoji": True
            },
            "action_id": f"{action_type.value}_{resource_id}_{int(time.time())}",
            "value": json.dumps(payload.to_dict())
        }
        
        # Add styling
        if style != ButtonStyle.DEFAULT:
            button["style"] = style.value
        
        # Add URL for external links
        if url:
            if self._is_url_allowed(url):
                button["url"] = url
            else:
                self.logger.warning(f"URL not allowed: {url}")
        
        # Add confirmation dialog
        if confirmation:
            button["confirm"] = self._create_confirmation_dialog(confirmation)
        
        # Register action for validation
        self._register_action(button["action_id"], {
            "action_type": action_type,
            "resource_id": resource_id,
            "created_at": time.time(),
            "requires_auth": self.config.require_authorization
        })
        
        return button
    
    def create_pr_approval_button(self, pr_number: str, pr_title: str) -> Dict[str, Any]:
        """Create PR approval button with confirmation."""
        return self.create_button(
            text="✅ Approve PR",
            action_type=ActionType.APPROVE_PR,
            resource_id=pr_number,
            style=ButtonStyle.PRIMARY,
            confirmation={
                "title": "Approve Pull Request",
                "text": f"Are you sure you want to approve PR #{pr_number}: {pr_title}?",
                "confirm": "Yes, Approve",
                "deny": "Cancel"
            },
            metadata={"pr_title": pr_title}
        )
    
    def create_pr_rejection_button(self, pr_number: str) -> Dict[str, Any]:
        """Create PR rejection button with confirmation."""
        return self.create_button(
            text="❌ Request Changes",
            action_type=ActionType.REJECT_PR,
            resource_id=pr_number,
            style=ButtonStyle.DANGER,
            confirmation={
                "title": "Request Changes",
                "text": f"Request changes for PR #{pr_number}? This will require the author to make updates.",
                "confirm": "Request Changes",
                "deny": "Cancel"
            }
        )
    
    def create_merge_button(self, pr_number: str, branch_name: str) -> Dict[str, Any]:
        """Create merge button with detailed confirmation."""
        return self.create_button(
            text="🚀 Merge PR",
            action_type=ActionType.MERGE_PR,
            resource_id=pr_number,
            style=ButtonStyle.PRIMARY,
            confirmation={
                "title": "Merge Pull Request",
                "text": f"⚠️ **This action cannot be undone**\n\nMerge PR #{pr_number} into `{branch_name}`?\n\nThis will:\n• Close the pull request\n• Merge changes into the target branch\n• Trigger deployment workflows",
                "confirm": "Yes, Merge",
                "deny": "Cancel"
            },
            metadata={"branch_name": branch_name}
        )
    
    def create_alert_acknowledgment_button(self, alert_id: str, severity: str) -> Dict[str, Any]:
        """Create alert acknowledgment button."""
        confirmation = None
        if severity.lower() in ['critical', 'high']:
            confirmation = {
                "title": "Acknowledge Alert",
                "text": f"Acknowledge this {severity} severity alert? You will be responsible for resolution.",
                "confirm": "I'll Handle It",
                "deny": "Cancel"
            }
        
        return self.create_button(
            text="👤 Acknowledge",
            action_type=ActionType.ACKNOWLEDGE_ALERT,
            resource_id=alert_id,
            style=ButtonStyle.PRIMARY,
            confirmation=confirmation,
            metadata={"severity": severity}
        )
    
    def create_blocker_resolution_button(self, blocker_id: str) -> Dict[str, Any]:
        """Create blocker resolution button."""
        return self.create_button(
            text="✅ Mark Resolved",
            action_type=ActionType.RESOLVE_BLOCKER,
            resource_id=blocker_id,
            style=ButtonStyle.PRIMARY,
            confirmation={
                "title": "Resolve Blocker",
                "text": "Mark this blocker as resolved? This will notify all affected team members.",
                "confirm": "Mark Resolved",
                "deny": "Cancel"
            }
        )
    
    def create_show_details_button(self, resource_id: str, resource_type: str) -> Dict[str, Any]:
        """Create expandable details button."""
        return self.create_button(
            text="📋 Show Details",
            action_type=ActionType.SHOW_DETAILS,
            resource_id=resource_id,
            metadata={"resource_type": resource_type}
        )
    
    def create_external_link_button(self, text: str, url: str, description: str = "") -> Dict[str, Any]:
        """Create external link button with security validation."""
        return self.create_button(
            text=text,
            action_type=ActionType.EXTERNAL_LINK,
            resource_id=hashlib.md5(url.encode()).hexdigest()[:8],
            url=url,
            metadata={"description": description, "url": url}
        )
    
    def create_selection_menu(self,
                            placeholder: str,
                            action_id: str,
                            options: List[Dict[str, str]],
                            initial_option: Optional[str] = None) -> Dict[str, Any]:
        """Create selection menu for user choices."""
        
        # Validate options
        validated_options = []
        for option in options[:100]:  # Limit to 100 options
            if isinstance(option, dict) and 'text' in option and 'value' in option:
                validated_options.append({
                    "text": {
                        "type": "plain_text",
                        "text": str(option['text'])[:75],  # Slack limit
                        "emoji": True
                    },
                    "value": str(option['value'])[:75]  # Slack limit
                })
        
        menu = {
            "type": "static_select",
            "placeholder": {
                "type": "plain_text",
                "text": placeholder[:150],  # Slack limit
                "emoji": True
            },
            "action_id": action_id,
            "options": validated_options
        }
        
        # Set initial option if provided
        if initial_option:
            for option in validated_options:
                if option["value"] == initial_option:
                    menu["initial_option"] = option
                    break
        
        return menu
    
    def create_user_assignment_menu(self, ticket_id: str, users: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create user assignment selection menu."""
        options = [{"text": "Unassigned", "value": "unassigned"}]
        options.extend([
            {"text": f"👤 {user['name']}", "value": user['id']}
            for user in users[:25]  # Limit to 25 users
        ])
        
        return self.create_selection_menu(
            placeholder="Assign to user...",
            action_id=f"assign_ticket_{ticket_id}",
            options=options
        )
    
    def create_priority_selection_menu(self, resource_id: str) -> Dict[str, Any]:
        """Create priority selection menu."""
        priorities = [
            {"text": "🔴 Critical", "value": "critical"},
            {"text": "🟠 High", "value": "high"},
            {"text": "🟡 Medium", "value": "medium"},
            {"text": "🟢 Low", "value": "low"},
            {"text": "⬇️ Lowest", "value": "lowest"}
        ]
        
        return self.create_selection_menu(
            placeholder="Change priority...",
            action_id=f"change_priority_{resource_id}",
            options=priorities
        )
    
    def create_jira_status_menu(self, ticket_id: str) -> Dict[str, Any]:
        """Create JIRA status update menu."""
        statuses = [
            {"text": "📋 To Do", "value": "todo"},
            {"text": "🔄 In Progress", "value": "in_progress"},
            {"text": "👀 In Review", "value": "in_review"},
            {"text": "✅ Done", "value": "done"},
            {"text": "🚫 Blocked", "value": "blocked"}
        ]
        
        return self.create_selection_menu(
            placeholder="Update status...",
            action_id=f"update_jira_status_{ticket_id}",
            options=statuses
        )
    
    def create_modal_dialog(self,
                          title: str,
                          callback_id: str,
                          blocks: List[Dict[str, Any]],
                          submit_text: str = "Submit",
                          close_text: str = "Cancel") -> Dict[str, Any]:
        """Create modal dialog for complex interactions."""
        
        return {
            "type": "modal",
            "callback_id": callback_id,
            "title": {
                "type": "plain_text",
                "text": title[:24],  # Slack limit
                "emoji": True
            },
            "submit": {
                "type": "plain_text",
                "text": submit_text[:24],
                "emoji": True
            },
            "close": {
                "type": "plain_text",
                "text": close_text[:24],
                "emoji": True
            },
            "blocks": blocks[:100]  # Slack limit
        }
    
    def create_comment_modal(self, resource_id: str, resource_type: str) -> Dict[str, Any]:
        """Create comment input modal."""
        blocks = [
            {
                "type": "input",
                "block_id": "comment_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "comment_text",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter your comment..."
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "Comment",
                    "emoji": True
                }
            }
        ]
        
        return self.create_modal_dialog(
            title="Add Comment",
            callback_id=f"add_comment_{resource_type}_{resource_id}",
            blocks=blocks,
            submit_text="Post Comment"
        )
    
    def create_time_logging_modal(self, ticket_id: str) -> Dict[str, Any]:
        """Create time logging modal."""
        blocks = [
            {
                "type": "input",
                "block_id": "time_spent",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "time_value",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g., 2h 30m or 150m"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "Time Spent",
                    "emoji": True
                }
            },
            {
                "type": "input",
                "block_id": "work_description",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "work_text",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Describe the work done..."
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "Work Description",
                    "emoji": True
                },
                "optional": True
            }
        ]
        
        return self.create_modal_dialog(
            title="Log Time",
            callback_id=f"log_time_{ticket_id}",
            blocks=blocks,
            submit_text="Log Time"
        )
    
    def create_confirmation_modal(self,
                                title: str,
                                message: str,
                                action_id: str,
                                confirm_text: str = "Confirm",
                                danger: bool = False) -> Dict[str, Any]:
        """Create confirmation modal for destructive actions."""
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]
        
        if danger:
            blocks.insert(0, {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "⚠️ *Warning: This action cannot be undone*"
                }
            })
        
        return self.create_modal_dialog(
            title=title,
            callback_id=action_id,
            blocks=blocks,
            submit_text=confirm_text,
            close_text="Cancel"
        )
    
    def validate_action_payload(self, payload_json: str, user_id: str) -> Optional[ActionPayload]:
        """Validate and parse action payload with security checks."""
        try:
            # Parse JSON
            payload_data = json.loads(payload_json)
            payload = ActionPayload.from_dict(payload_data)
            
            # Check rate limiting
            if not self._check_rate_limit(user_id):
                self.logger.warning(f"Rate limit exceeded for user {user_id}")
                return None
            
            # Verify signature if configured
            if self.config.secret_key and not self._verify_payload_signature(payload):
                self.logger.warning(f"Invalid payload signature for user {user_id}")
                return None
            
            # Check payload age (prevent replay attacks)
            if time.time() - payload.timestamp > self.config.session_timeout:
                self.logger.warning(f"Expired payload for user {user_id}")
                return None
            
            # Set user ID
            payload.user_id = user_id
            
            # Log action for audit
            if self.config.enable_audit_logging:
                self._log_action(payload, user_id)
            
            return payload
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Invalid payload format: {e}")
            return None
    
    def _create_confirmation_dialog(self, confirmation: Dict[str, str]) -> Dict[str, Any]:
        """Create confirmation dialog structure."""
        return {
            "title": {
                "type": "plain_text",
                "text": confirmation.get("title", "Confirm Action")[:24]
            },
            "text": {
                "type": "mrkdwn",
                "text": confirmation.get("text", "Are you sure?")[:300]
            },
            "confirm": {
                "type": "plain_text",
                "text": confirmation.get("confirm", "Yes")[:24]
            },
            "deny": {
                "type": "plain_text",
                "text": confirmation.get("deny", "Cancel")[:24]
            }
        }
    
    def _sign_payload(self, payload: ActionPayload) -> str:
        """Create signature for payload security."""
        if not self.config.secret_key:
            return ""
        
        # Create signature from payload data
        payload_str = f"{payload.action_type.value}:{payload.resource_id}:{payload.timestamp}"
        signature = hmac.new(
            self.config.secret_key.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _verify_payload_signature(self, payload: ActionPayload) -> bool:
        """Verify payload signature."""
        if not self.config.secret_key or not payload.signature:
            return False
        
        expected_signature = self._sign_payload(payload)
        return hmac.compare_digest(expected_signature, payload.signature)
    
    def _is_url_allowed(self, url: str) -> bool:
        """Check if URL is allowed based on domain whitelist."""
        if not self.config.allowed_domains:
            return True  # No restrictions
        
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc.lower()
            return any(domain.endswith(allowed) for allowed in self.config.allowed_domains)
        except Exception:
            return False
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limits."""
        current_time = time.time()
        hour_ago = current_time - 3600
        
        # Clean old entries
        if user_id in self._rate_limits:
            self._rate_limits[user_id] = [
                timestamp for timestamp in self._rate_limits[user_id]
                if timestamp > hour_ago
            ]
        else:
            self._rate_limits[user_id] = []
        
        # Check limit
        if len(self._rate_limits[user_id]) >= self.config.rate_limit_per_user:
            return False
        
        # Add current action
        self._rate_limits[user_id].append(current_time)
        return True
    
    def _register_action(self, action_id: str, action_data: Dict[str, Any]):
        """Register action for validation."""
        self._registered_actions[action_id] = action_data
    
    def _log_action(self, payload: ActionPayload, user_id: str):
        """Log action for audit purposes."""
        log_entry = {
            "timestamp": time.time(),
            "user_id": user_id,
            "action_type": payload.action_type.value,
            "resource_id": payload.resource_id,
            "metadata": payload.metadata
        }
        
        self._audit_log.append(log_entry)
        
        # Keep only last 10000 entries (in production, use proper logging)
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-10000:]
        
        self.logger.info(f"Action logged: {log_entry}")
    
    def get_audit_log(self, user_id: Optional[str] = None, 
                     action_type: Optional[ActionType] = None,
                     limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit log entries with optional filtering."""
        filtered_log = self._audit_log
        
        if user_id:
            filtered_log = [entry for entry in filtered_log if entry['user_id'] == user_id]
        
        if action_type:
            filtered_log = [entry for entry in filtered_log if entry['action_type'] == action_type.value]
        
        return filtered_log[-limit:]
    
    def create_action_group(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create action block with multiple elements."""
        return {
            "type": "actions",
            "elements": actions[:5]  # Slack limit is 5 elements per action block
        }


# Global default instance
default_interactive_builder = InteractiveElementBuilder()