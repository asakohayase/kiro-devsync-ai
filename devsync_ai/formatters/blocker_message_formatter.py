"""Blocker message formatter for high-urgency notifications."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from ..core.base_template import SlackMessageTemplate
from ..core.block_kit_builders import BlockKitBuilder, HeaderConfig
from ..core.status_indicators import UrgencyLevel, Priority


class BlockerMessageFormatter(SlackMessageTemplate):
    """Specialized formatter for high-urgency blocker notifications."""
    
    REQUIRED_FIELDS = ['blocker']
    
    def __init__(self, *args, **kwargs):
        """Initialize with Block Kit builder."""
        super().__init__(*args, **kwargs)
        self.builder = BlockKitBuilder(self.status_system)
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create blocker notification message blocks."""
        blocks = []
        
        blocker_data = data['blocker']
        blocker_type = data.get('blocker_type', 'general')
        
        # Determine urgency level
        urgency = self._get_urgency_level(blocker_data)
        
        # Build alert-style header
        header_config = HeaderConfig(
            title=self._build_blocker_title(blocker_data, blocker_type),
            status=urgency,
            status_context="general",
            timestamp=self._parse_timestamp(blocker_data.get('created_at')),
            subtitle=self._build_urgency_subtitle(blocker_data, urgency),
            description=self._build_alert_description(blocker_data),
            actions=self._get_emergency_actions(blocker_data)
        )
        
        blocks.extend(self.builder.build_header(header_config))
        
        # Problem description with high visibility
        blocks.append(self._build_problem_description(blocker_data))
        
        # Impact assessment
        if blocker_data.get('impact'):
            blocks.append(self._build_impact_section(blocker_data['impact']))
        
        # Affected systems/people
        affected_info = self._build_affected_section(blocker_data)
        if affected_info:
            blocks.extend(affected_info)
        
        # Escalation path
        blocks.append(self._build_escalation_section(blocker_data))
        
        # Resolution timeline and steps
        if blocker_data.get('resolution_steps') or blocker_data.get('timeline'):
            blocks.append(self._build_resolution_section(blocker_data))
        
        # Real-time status updates
        if blocker_data.get('status_updates'):
            blocks.append(self._build_status_updates_section(blocker_data['status_updates']))
        
        # Emergency actions
        blocks.append(self.builder.build_divider())
        emergency_actions = self._get_emergency_response_actions(blocker_data, urgency)
        if emergency_actions:
            blocks.append(self.builder.build_action_buttons(emergency_actions))
        
        return blocks
    
    def _get_urgency_level(self, blocker_data: Dict[str, Any]) -> str:
        """Determine urgency level from blocker data."""
        severity = blocker_data.get('severity', 'medium').lower()
        priority = blocker_data.get('priority', 'medium').lower()
        
        # Map to urgency levels
        if severity in ['critical', 'blocker'] or priority in ['critical', 'blocker']:
            return 'critical'
        elif severity == 'high' or priority == 'high':
            return 'high'
        elif severity == 'medium' or priority == 'medium':
            return 'medium'
        else:
            return 'low'
    
    def _build_blocker_title(self, blocker_data: Dict[str, Any], blocker_type: str) -> str:
        """Build blocker title with alert indicators."""
        title = blocker_data.get('title', 'Critical Blocker')
        blocker_id = blocker_data.get('id', 'BLOCK-001')
        
        # Add type prefix
        type_prefixes = {
            'production': '🚨 PRODUCTION',
            'security': '🔒 SECURITY',
            'deployment': '🚀 DEPLOYMENT',
            'infrastructure': '⚙️ INFRASTRUCTURE',
            'team': '👥 TEAM',
            'general': '🚫 BLOCKER'
        }
        
        prefix = type_prefixes.get(blocker_type, '🚫 BLOCKER')
        return f"{prefix} {blocker_id}: {title}"
    
    def _build_urgency_subtitle(self, blocker_data: Dict[str, Any], urgency: str) -> str:
        """Build urgency-focused subtitle."""
        parts = []
        
        # Urgency indicator
        urgency_indicator = self.status_system.get_urgency_indicator(UrgencyLevel(urgency))
        parts.append(f"{urgency_indicator.emoji} {urgency_indicator.text} Priority")
        
        # Time since creation
        created_at = blocker_data.get('created_at')
        if created_at:
            created_dt = self._parse_timestamp(created_at)
            if created_dt:
                time_diff = datetime.now() - created_dt
                if time_diff.total_seconds() < 3600:  # Less than 1 hour
                    minutes = int(time_diff.total_seconds() / 60)
                    parts.append(f"Active for {minutes} minutes")
                else:
                    hours = int(time_diff.total_seconds() / 3600)
                    parts.append(f"Active for {hours} hours")
        
        # Reporter
        reporter = blocker_data.get('reporter')
        if reporter:
            parts.append(f"Reported by {self.builder.build_user_mention(reporter)}")
        
        return " • ".join(parts)
    
    def _build_alert_description(self, blocker_data: Dict[str, Any]) -> str:
        """Build alert-style description."""
        description = blocker_data.get('description', '')
        if not description:
            return None
        
        # Truncate and add urgency formatting
        truncated = self._truncate_text(description, 200)
        return f"⚠️ **ALERT**: {truncated}"
    
    def _build_problem_description(self, blocker_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build detailed problem description with high visibility."""
        content_parts = ["*🚨 PROBLEM DESCRIPTION:*"]
        
        # Main description
        description = blocker_data.get('description', 'No description provided')
        content_parts.append(f"```{description}```")
        
        # Error details if available
        if blocker_data.get('error_message'):
            content_parts.append("*Error Message:*")
            content_parts.append(f"```{blocker_data['error_message']}```")
        
        # Steps to reproduce
        if blocker_data.get('steps_to_reproduce'):
            content_parts.append("*Steps to Reproduce:*")
            for i, step in enumerate(blocker_data['steps_to_reproduce'][:5], 1):
                content_parts.append(f"{i}. {step}")
        
        # Environment details
        if blocker_data.get('environment'):
            env = blocker_data['environment']
            env_parts = []
            if env.get('system'):
                env_parts.append(f"System: {env['system']}")
            if env.get('version'):
                env_parts.append(f"Version: {env['version']}")
            if env.get('browser'):
                env_parts.append(f"Browser: {env['browser']}")
            
            if env_parts:
                content_parts.append(f"*Environment:* {' • '.join(env_parts)}")
        
        return self.builder.build_section({"text": "\n".join(content_parts)})
    
    def _build_impact_section(self, impact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build impact assessment section."""
        content_parts = ["*💥 IMPACT ASSESSMENT:*"]
        
        # Severity level
        severity = impact_data.get('severity', 'Unknown')
        severity_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }.get(severity.lower(), '⚪')
        content_parts.append(f"**Severity:** {severity_emoji} {severity.upper()}")
        
        # Affected users
        affected_users = impact_data.get('affected_users')
        if affected_users:
            if isinstance(affected_users, int):
                content_parts.append(f"**Affected Users:** 👥 {affected_users:,} users")
            else:
                content_parts.append(f"**Affected Users:** {affected_users}")
        
        # Business impact
        business_impact = impact_data.get('business_impact')
        if business_impact:
            content_parts.append(f"**Business Impact:** 💼 {business_impact}")
        
        # Financial impact
        financial_impact = impact_data.get('financial_impact')
        if financial_impact:
            content_parts.append(f"**Financial Impact:** 💰 {financial_impact}")
        
        # SLA impact
        sla_impact = impact_data.get('sla_impact')
        if sla_impact:
            content_parts.append(f"**SLA Impact:** ⏱️ {sla_impact}")
        
        return self.builder.build_section({"text": "\n".join(content_parts)})
    
    def _build_affected_section(self, blocker_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build affected systems and people sections."""
        blocks = []
        
        # Affected systems
        affected_systems = blocker_data.get('affected_systems', [])
        if affected_systems:
            systems_content = ["*⚙️ AFFECTED SYSTEMS:*"]
            for system in affected_systems[:5]:
                if isinstance(system, dict):
                    name = system.get('name', 'Unknown')
                    status = system.get('status', 'unknown')
                    status_emoji = {
                        'down': '🔴',
                        'degraded': '🟡',
                        'operational': '🟢'
                    }.get(status, '❓')
                    systems_content.append(f"• {status_emoji} **{name}** ({status})")
                else:
                    systems_content.append(f"• 🔴 {system}")
            
            if len(affected_systems) > 5:
                systems_content.append(f"• ... and {len(affected_systems)-5} more systems")
            
            blocks.append(self.builder.build_section({"text": "\n".join(systems_content)}))
        
        # Affected team members
        affected_people = blocker_data.get('affected_people', [])
        if affected_people:
            people_content = ["*👥 AFFECTED TEAM MEMBERS:*"]
            for person in affected_people[:8]:
                if isinstance(person, dict):
                    name = person.get('name', 'Unknown')
                    role = person.get('role', '')
                    impact = person.get('impact', 'blocked')
                    person_mention = self.builder.build_user_mention(name)
                    role_text = f" ({role})" if role else ""
                    people_content.append(f"• 🚫 {person_mention}{role_text} - {impact}")
                else:
                    people_content.append(f"• 🚫 {self.builder.build_user_mention(person)}")
            
            if len(affected_people) > 8:
                people_content.append(f"• ... and {len(affected_people)-8} more people")
            
            blocks.append(self.builder.build_section({"text": "\n".join(people_content)}))
        
        return blocks
    
    def _build_escalation_section(self, blocker_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build escalation path section."""
        content_parts = ["*📞 ESCALATION PATH:*"]
        
        escalation_path = blocker_data.get('escalation_path', [])
        if escalation_path:
            for i, contact in enumerate(escalation_path[:4], 1):
                if isinstance(contact, dict):
                    name = contact.get('name', 'Unknown')
                    role = contact.get('role', 'Contact')
                    phone = contact.get('phone', '')
                    email = contact.get('email', '')
                    
                    contact_mention = self.builder.build_user_mention(name)
                    contact_info = f"**Level {i}:** {contact_mention} - {role}"
                    
                    if phone:
                        contact_info += f" 📞 {phone}"
                    if email:
                        contact_info += f" 📧 {email}"
                    
                    content_parts.append(contact_info)
                else:
                    content_parts.append(f"**Level {i}:** {self.builder.build_user_mention(contact)}")
        else:
            # Default escalation
            content_parts.extend([
                "**Level 1:** Team Lead - Immediate response required",
                "**Level 2:** Engineering Manager - If no response in 15 minutes",
                "**Level 3:** Director of Engineering - If no response in 30 minutes"
            ])
        
        # Emergency contacts
        emergency_contacts = blocker_data.get('emergency_contacts', [])
        if emergency_contacts:
            content_parts.append("\n*🚨 EMERGENCY CONTACTS:*")
            for contact in emergency_contacts[:2]:
                if isinstance(contact, dict):
                    name = contact.get('name', 'Unknown')
                    phone = contact.get('phone', 'No phone')
                    content_parts.append(f"• {self.builder.build_user_mention(name)} - 📞 {phone}")
                else:
                    content_parts.append(f"• {self.builder.build_user_mention(contact)}")
        
        return self.builder.build_section({"text": "\n".join(content_parts)})
    
    def _build_resolution_section(self, blocker_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build resolution timeline and steps section."""
        content_parts = ["*🔧 RESOLUTION PLAN:*"]
        
        # Timeline
        timeline = blocker_data.get('timeline', {})
        if timeline:
            eta = timeline.get('eta')
            if eta:
                content_parts.append(f"**ETA:** ⏰ {eta}")
            
            target_resolution = timeline.get('target_resolution')
            if target_resolution:
                content_parts.append(f"**Target Resolution:** 🎯 {target_resolution}")
        
        # Resolution steps
        resolution_steps = blocker_data.get('resolution_steps', [])
        if resolution_steps:
            content_parts.append("\n**Resolution Steps:**")
            for i, step in enumerate(resolution_steps[:6], 1):
                if isinstance(step, dict):
                    description = step.get('description', 'Unknown step')
                    status = step.get('status', 'pending')
                    assignee = step.get('assignee')
                    
                    status_emoji = {
                        'completed': '✅',
                        'in_progress': '🔄',
                        'pending': '⏳',
                        'blocked': '🚫'
                    }.get(status, '📝')
                    
                    step_text = f"{i}. {status_emoji} {description}"
                    if assignee:
                        step_text += f" - {self.builder.build_user_mention(assignee)}"
                    
                    content_parts.append(step_text)
                else:
                    content_parts.append(f"{i}. ⏳ {step}")
        
        # Workarounds
        workarounds = blocker_data.get('workarounds', [])
        if workarounds:
            content_parts.append("\n**Available Workarounds:**")
            for workaround in workarounds[:3]:
                content_parts.append(f"• 🔄 {workaround}")
        
        return self.builder.build_section({"text": "\n".join(content_parts)})
    
    def _build_status_updates_section(self, status_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build real-time status updates section."""
        content_parts = ["*📊 RECENT STATUS UPDATES:*"]
        
        # Sort by timestamp (most recent first)
        sorted_updates = sorted(
            status_updates,
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )
        
        for update in sorted_updates[:3]:  # Show last 3 updates
            timestamp = update.get('timestamp', 'Unknown time')
            author = update.get('author', 'Unknown')
            message = update.get('message', 'No message')
            status = update.get('status', 'info')
            
            status_emoji = {
                'progress': '🔄',
                'success': '✅',
                'warning': '⚠️',
                'error': '❌',
                'info': 'ℹ️'
            }.get(status, '📝')
            
            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%H:%M")
            except (ValueError, AttributeError):
                time_str = timestamp
            
            author_mention = self.builder.build_user_mention(author)
            content_parts.append(f"• {status_emoji} **{time_str}** - {author_mention}: {message}")
        
        return self.builder.build_section({"text": "\n".join(content_parts)})
    
    def _get_emergency_actions(self, blocker_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get emergency header actions."""
        actions = []
        
        # View details link
        if blocker_data.get('url'):
            actions.append({
                "label": "🔍 Details",
                "url": blocker_data['url']
            })
        
        return actions
    
    def _get_emergency_response_actions(self, blocker_data: Dict[str, Any], urgency: str) -> List[Dict[str, Any]]:
        """Get emergency response action buttons."""
        actions = []
        blocker_id = blocker_data.get('id', 'unknown')
        
        # Critical actions for high urgency
        if urgency in ['critical', 'high']:
            actions.extend([
                {
                    "label": "🚨 Escalate Now",
                    "action_id": "escalate_blocker",
                    "value": blocker_id,
                    "style": "danger"
                },
                {
                    "label": "📞 Call War Room",
                    "action_id": "start_war_room",
                    "value": blocker_id,
                    "style": "primary",
                    "confirm": self.builder.create_confirmation_dialog(
                        title="Start War Room",
                        text="This will immediately notify all escalation contacts and start an emergency response session.",
                        confirm_text="Start War Room",
                        deny_text="Cancel"
                    )
                }
            ])
        
        # Standard response actions
        actions.extend([
            {
                "label": "🔧 I'm Working On It",
                "action_id": "claim_blocker",
                "value": blocker_id,
                "style": "primary"
            },
            {
                "label": "📝 Add Update",
                "action_id": "add_status_update",
                "value": blocker_id
            },
            {
                "label": "✅ Mark Resolved",
                "action_id": "resolve_blocker",
                "value": blocker_id,
                "confirm": self.builder.create_confirmation_dialog(
                    title="Resolve Blocker",
                    text="Are you sure this blocker is fully resolved?",
                    confirm_text="Mark Resolved",
                    deny_text="Cancel"
                )
            }
        ])
        
        # Communication actions
        actions.extend([
            {
                "label": "📢 Broadcast Update",
                "action_id": "broadcast_update",
                "value": blocker_id
            }
        ])
        
        return actions
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime."""
        if not timestamp_str:
            return None
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None