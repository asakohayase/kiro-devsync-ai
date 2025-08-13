"""
Urgent blocker/alert templates for DevSync AI notifications.
Provides high-visibility formatting for critical issues and emergencies.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .slack_templates import SlackTemplateBase


class AlertTemplateBase(SlackTemplateBase):
    """Base class for urgent alert templates."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
        self.alert = data.get('alert', {})
        self.alert_type = self.alert.get('type', 'unknown')
        self.severity = self.alert.get('severity', 'medium').lower()
        self.fallback_text = f"🚨 ALERT: {self.alert.get('title', 'Unknown Alert')} - {self.severity.upper()}"
        self._build_template()
    
    def _build_template(self) -> None:
        """Build basic alert template."""
        self._add_alert_header()
        self.add_divider()
        self._add_alert_details()
        self._add_sla_tracking()
        self._add_escalation_contacts()
        self._add_resolution_steps()
        self._add_related_items()
        self._add_urgent_actions()
        self._add_alert_footer()
    
    def _get_severity_emoji(self, severity: str) -> str:
        """Get emoji for alert severity."""
        severity_map = {
            'critical': '🔴',
            'high': '🟠', 
            'medium': '🟡',
            'low': '🟢'
        }
        return severity_map.get(severity.lower(), '🟡')
    
    def _get_alert_type_emoji(self, alert_type: str) -> str:
        """Get emoji for alert type."""
        type_map = {
            'build_failure': '🔨',
            'deployment_issue': '🚀',
            'critical_bug': '🐛',
            'security_vulnerability': '🔒',
            'service_outage': '⚡',
            'team_blocker': '🚫',
            'dependency_issue': '📦'
        }
        return type_map.get(alert_type, '⚠️')
    
    def _get_severity_color(self, severity: str) -> str:
        """Get color for severity level."""
        color_map = {
            'critical': '#FF0000',  # Red
            'high': '#FF8C00',      # Orange
            'medium': '#FFD700',    # Gold
            'low': '#32CD32'        # Green
        }
        return color_map.get(severity.lower(), '#FFD700')
    
    def _calculate_time_remaining(self, sla_breach_time: str) -> str:
        """Calculate time remaining until SLA breach."""
        if not sla_breach_time:
            return "No SLA defined"
        
        try:
            breach_time = datetime.fromisoformat(sla_breach_time.replace('Z', '+00:00'))
            now = datetime.now(breach_time.tzinfo)
            remaining = breach_time - now
            
            if remaining.total_seconds() <= 0:
                return "⚠️ SLA BREACHED"
            
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            
            if hours > 0:
                return f"⏰ {hours}h {minutes}m remaining"
            else:
                return f"⏰ {minutes}m remaining"
                
        except (ValueError, AttributeError):
            return "Invalid SLA time"
    
    def _add_alert_header(self) -> None:
        """Add urgent alert header with high visibility."""
        title = self.alert.get('title', 'Unknown Alert')
        severity = self.severity
        severity_emoji = self._get_severity_emoji(severity)
        alert_emoji = self._get_alert_type_emoji(self.alert_type)
        
        # Create urgent header
        header_text = f"🚨 {alert_emoji} {severity_emoji} {severity.upper()} ALERT"
        
        self.blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text,
                "emoji": True
            }
        })
        
        # Add title with description
        description = self.alert.get('description', '')
        alert_text = f"*{title}*"
        if description:
            alert_text += f"\n{description}"
        
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": alert_text
            }
        })
    
    def _add_alert_details(self) -> None:
        """Add alert details section."""
        alert_id = self.alert.get('id', 'N/A')
        affected_systems = self.alert.get('affected_systems', [])
        impact = self.alert.get('impact', 'Unknown impact')
        assigned_to = self.alert.get('assigned_to', 'Unassigned')
        
        # Alert details
        details_fields = [
            {
                "type": "mrkdwn",
                "text": f"*🆔 Alert ID:* {alert_id}"
            },
            {
                "type": "mrkdwn",
                "text": f"*👤 Assigned:* {assigned_to}"
            }
        ]
        
        if affected_systems:
            systems_text = ", ".join(affected_systems)
            details_fields.append({
                "type": "mrkdwn",
                "text": f"*🖥️ Affected Systems:* {systems_text}"
            })
        
        details_fields.append({
            "type": "mrkdwn",
            "text": f"*💥 Impact:* {impact}"
        })
        
        self.blocks.append({
            "type": "section",
            "fields": details_fields
        })
    
    def _add_sla_tracking(self) -> None:
        """Add SLA tracking and timeline information."""
        sla_breach_time = self.alert.get('sla_breach_time')
        created_at = self.alert.get('created_at')
        
        if sla_breach_time or created_at:
            timeline_text = "*⏱️ Timeline:*\n"
            
            if created_at:
                try:
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    timeline_text += f"• Created: {created_date.strftime('%m/%d %I:%M %p')}\n"
                except (ValueError, AttributeError):
                    timeline_text += f"• Created: {created_at}\n"
            
            if sla_breach_time:
                time_remaining = self._calculate_time_remaining(sla_breach_time)
                timeline_text += f"• SLA Status: {time_remaining}\n"
                
                # Add urgency indicator for critical timing
                if "BREACHED" in time_remaining:
                    timeline_text += "• 🚨 **IMMEDIATE ACTION REQUIRED**"
                elif "remaining" in time_remaining and ("m remaining" in time_remaining and not "h" in time_remaining):
                    timeline_text += "• ⚡ **URGENT - Less than 1 hour remaining**"
            
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": timeline_text.strip()
                }
            })
    
    def _add_escalation_contacts(self) -> None:
        """Add escalation contacts information."""
        escalation_contacts = self.alert.get('escalation_contacts', [])
        
        if escalation_contacts:
            contacts_text = "*📞 Escalation Contacts:*\n"
            for contact in escalation_contacts:
                if '@' in contact:  # Email
                    contacts_text += f"• 📧 {contact}\n"
                else:  # Assume username
                    contacts_text += f"• 👤 @{contact}\n"
            
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": contacts_text.strip()
                }
            })
    
    def _add_resolution_steps(self) -> None:
        """Add resolution steps if available."""
        resolution_steps = self.alert.get('resolution_steps', [])
        
        if resolution_steps:
            steps_text = "*🔧 Resolution Steps:*\n"
            for i, step in enumerate(resolution_steps, 1):
                steps_text += f"{i}. {step}\n"
            
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": steps_text.strip()
                }
            })
    
    def _add_related_items(self) -> None:
        """Add related PRs and tickets."""
        related_pr = self.alert.get('related_pr')
        related_tickets = self.alert.get('related_tickets', [])
        
        if related_pr or related_tickets:
            related_text = "*🔗 Related Items:*\n"
            
            if related_pr:
                related_text += f"• PR #{related_pr}\n"
            
            if related_tickets:
                tickets_str = ", ".join(related_tickets)
                related_text += f"• Tickets: {tickets_str}\n"
            
            self.blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": related_text.strip()
                }
            })
    
    def _add_urgent_actions(self) -> None:
        """Add urgent action buttons."""
        alert_id = self.alert.get('id', '')
        severity = self.severity
        
        buttons = []
        
        # Severity-specific primary actions
        if severity == 'critical':
            buttons.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 ESCALATE NOW",
                    "emoji": True
                },
                "value": f"escalate_{alert_id}",
                "action_id": "escalate_critical",
                "style": "danger"
            })
        
        # Common action buttons
        buttons.extend([
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "👤 Take Ownership",
                    "emoji": True
                },
                "value": f"assign_{alert_id}",
                "action_id": "take_ownership",
                "style": "primary"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📊 View Details",
                    "emoji": True
                },
                "value": f"details_{alert_id}",
                "action_id": "view_details"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "💬 Add Update",
                    "emoji": True
                },
                "value": f"update_{alert_id}",
                "action_id": "add_update"
            }
        ])
        
        # Add resolution button for non-critical alerts
        if severity != 'critical':
            buttons.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "✅ Mark Resolved",
                    "emoji": True
                },
                "value": f"resolve_{alert_id}",
                "action_id": "mark_resolved"
            })
        
        # Split buttons into groups of 5 (Slack limit)
        for i in range(0, len(buttons), 5):
            button_group = buttons[i:i+5]
            self.blocks.append({
                "type": "actions",
                "elements": button_group
            })
    
    def _add_alert_footer(self) -> None:
        """Add footer with timestamp and mentions."""
        created_at = self.alert.get('created_at', '')
        severity = self.severity
        
        if created_at:
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                timestamp = created_date.strftime('%m/%d %I:%M %p')
            except (ValueError, AttributeError):
                timestamp = datetime.now().strftime('%I:%M %p')
        else:
            timestamp = datetime.now().strftime('%I:%M %p')
        
        # Add appropriate mentions based on severity
        mentions = []
        if severity == 'critical':
            mentions.append("<!channel> Critical alert requires immediate attention")
        elif severity == 'high':
            mentions.append("<!here> High priority alert")
        
        context_elements = [f"Alert created at {timestamp}", "DevSync AI"]
        if mentions:
            context_elements.extend(mentions)
        
        self.add_context(context_elements)


class BuildFailureTemplate(AlertTemplateBase):
    """Template for build failure alerts."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self._build_template()
    
    def _build_template(self) -> None:
        """Build build failure alert template."""
        self._add_alert_header()
        
        # Build-specific information
        self._add_build_details()
        
        self.add_divider()
        self._add_alert_details()
        self._add_sla_tracking()
        self._add_resolution_steps()
        self._add_related_items()
        self._add_build_actions()
        self._add_alert_footer()
    
    def _add_build_details(self) -> None:
        """Add build-specific details."""
        build_info = self.data.get('build_info', {})
        branch = build_info.get('branch', 'Unknown')
        commit = build_info.get('commit', 'Unknown')
        pipeline_url = build_info.get('pipeline_url', '')
        
        build_text = f"*🔨 Build Information:*\n"
        build_text += f"• Branch: `{branch}`\n"
        build_text += f"• Commit: `{commit[:8] if len(commit) > 8 else commit}`\n"
        
        if pipeline_url:
            build_text += f"• Pipeline: <{pipeline_url}|View Build Logs>"
        
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": build_text
            }
        })
    
    def _add_build_actions(self) -> None:
        """Add build-specific action buttons."""
        alert_id = self.alert.get('id', '')
        build_info = self.data.get('build_info', {})
        pipeline_url = build_info.get('pipeline_url', '')
        
        buttons = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🔄 Retry Build",
                    "emoji": True
                },
                "value": f"retry_{alert_id}",
                "action_id": "retry_build",
                "style": "primary"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📋 View Logs",
                    "emoji": True
                },
                "url": pipeline_url if pipeline_url else f"https://ci.company.com/build/{alert_id}",
                "action_id": "view_logs"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🚫 Block Deployments",
                    "emoji": True
                },
                "value": f"block_{alert_id}",
                "action_id": "block_deployments",
                "style": "danger"
            }
        ]
        
        self.blocks.append({
            "type": "actions",
            "elements": buttons
        })


class DeploymentIssueTemplate(AlertTemplateBase):
    """Template for deployment issue alerts."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self._build_template()
    
    def _build_template(self) -> None:
        """Build deployment issue alert template."""
        self._add_alert_header()
        
        # Deployment-specific information
        self._add_deployment_details()
        
        self.add_divider()
        self._add_alert_details()
        self._add_sla_tracking()
        self._add_resolution_steps()
        self._add_related_items()
        self._add_deployment_actions()
        self._add_alert_footer()
    
    def _add_deployment_details(self) -> None:
        """Add deployment-specific details."""
        deployment_info = self.data.get('deployment_info', {})
        environment = deployment_info.get('environment', 'Unknown')
        version = deployment_info.get('version', 'Unknown')
        rollback_available = deployment_info.get('rollback_available', False)
        
        deployment_text = f"*🚀 Deployment Information:*\n"
        deployment_text += f"• Environment: `{environment}`\n"
        deployment_text += f"• Version: `{version}`\n"
        deployment_text += f"• Rollback Available: {'✅ Yes' if rollback_available else '❌ No'}\n"
        
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": deployment_text
            }
        })
    
    def _add_deployment_actions(self) -> None:
        """Add deployment-specific action buttons."""
        alert_id = self.alert.get('id', '')
        deployment_info = self.data.get('deployment_info', {})
        rollback_available = deployment_info.get('rollback_available', False)
        
        buttons = []
        
        if rollback_available:
            buttons.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "⏪ ROLLBACK NOW",
                    "emoji": True
                },
                "value": f"rollback_{alert_id}",
                "action_id": "rollback_deployment",
                "style": "danger"
            })
        
        buttons.extend([
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Check Health",
                    "emoji": True
                },
                "value": f"health_{alert_id}",
                "action_id": "check_health"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📈 View Metrics",
                    "emoji": True
                },
                "value": f"metrics_{alert_id}",
                "action_id": "view_metrics"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🔄 Retry Deploy",
                    "emoji": True
                },
                "value": f"retry_deploy_{alert_id}",
                "action_id": "retry_deployment"
            }
        ])
        
        self.blocks.append({
            "type": "actions",
            "elements": buttons
        })


class SecurityVulnerabilityTemplate(AlertTemplateBase):
    """Template for security vulnerability alerts."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self._build_template()
    
    def _build_template(self) -> None:
        """Build security vulnerability alert template."""
        self._add_alert_header()
        
        # Security-specific information
        self._add_security_details()
        
        self.add_divider()
        self._add_alert_details()
        self._add_sla_tracking()
        self._add_resolution_steps()
        self._add_related_items()
        self._add_security_actions()
        self._add_alert_footer()
    
    def _add_security_details(self) -> None:
        """Add security-specific details."""
        security_info = self.data.get('security_info', {})
        cve_id = security_info.get('cve_id', '')
        cvss_score = security_info.get('cvss_score', 0)
        attack_vector = security_info.get('attack_vector', 'Unknown')
        
        security_text = f"*🔒 Security Information:*\n"
        
        if cve_id:
            security_text += f"• CVE ID: `{cve_id}`\n"
        
        if cvss_score:
            security_text += f"• CVSS Score: `{cvss_score}/10`\n"
        
        security_text += f"• Attack Vector: `{attack_vector}`\n"
        security_text += f"• **⚠️ SECURITY INCIDENT - CONFIDENTIAL**"
        
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": security_text
            }
        })
    
    def _add_security_actions(self) -> None:
        """Add security-specific action buttons."""
        alert_id = self.alert.get('id', '')
        
        buttons = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 ESCALATE TO SECURITY",
                    "emoji": True
                },
                "value": f"security_escalate_{alert_id}",
                "action_id": "escalate_security",
                "style": "danger"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🔒 Start Incident Response",
                    "emoji": True
                },
                "value": f"incident_{alert_id}",
                "action_id": "start_incident_response",
                "style": "primary"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📋 Create Security Ticket",
                    "emoji": True
                },
                "value": f"sec_ticket_{alert_id}",
                "action_id": "create_security_ticket"
            }
        ]
        
        self.blocks.append({
            "type": "actions",
            "elements": buttons
        })


class ServiceOutageTemplate(AlertTemplateBase):
    """Template for service outage alerts."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self._build_template()
    
    def _build_template(self) -> None:
        """Build service outage alert template."""
        self._add_alert_header()
        
        # Outage-specific information
        self._add_outage_details()
        
        self.add_divider()
        self._add_alert_details()
        self._add_sla_tracking()
        self._add_resolution_steps()
        self._add_related_items()
        self._add_outage_actions()
        self._add_alert_footer()
    
    def _add_outage_details(self) -> None:
        """Add outage-specific details."""
        outage_info = self.data.get('outage_info', {})
        services = outage_info.get('services', [])
        users_affected = outage_info.get('users_affected', 0)
        status_page = outage_info.get('status_page', '')
        
        outage_text = f"*⚡ Outage Information:*\n"
        
        if services:
            services_str = ", ".join(services)
            outage_text += f"• Affected Services: `{services_str}`\n"
        
        if users_affected:
            outage_text += f"• Users Affected: `{users_affected:,}`\n"
        
        if status_page:
            outage_text += f"• Status Page: <{status_page}|View Status>\n"
        
        outage_text += f"• **🚨 SERVICE DISRUPTION IN PROGRESS**"
        
        self.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": outage_text
            }
        })
    
    def _add_outage_actions(self) -> None:
        """Add outage-specific action buttons."""
        alert_id = self.alert.get('id', '')
        outage_info = self.data.get('outage_info', {})
        status_page = outage_info.get('status_page', '')
        
        buttons = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📢 Update Status Page",
                    "emoji": True
                },
                "url": status_page if status_page else "https://status.company.com",
                "action_id": "update_status_page",
                "style": "primary"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📞 Start War Room",
                    "emoji": True
                },
                "value": f"war_room_{alert_id}",
                "action_id": "start_war_room",
                "style": "danger"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Check Monitoring",
                    "emoji": True
                },
                "value": f"monitoring_{alert_id}",
                "action_id": "check_monitoring"
            }
        ]
        
        self.blocks.append({
            "type": "actions",
            "elements": buttons
        })


# Template factory function
def create_alert_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create appropriate alert message based on alert type."""
    alert_type = data.get('alert', {}).get('type', 'unknown')
    
    template_map = {
        'build_failure': BuildFailureTemplate,
        'deployment_issue': DeploymentIssueTemplate,
        'critical_bug': AlertTemplateBase,  # Use base template
        'security_vulnerability': SecurityVulnerabilityTemplate,
        'service_outage': ServiceOutageTemplate,
        'team_blocker': AlertTemplateBase,  # Use base template
        'dependency_issue': AlertTemplateBase,  # Use base template
    }
    
    template_class = template_map.get(alert_type, AlertTemplateBase)
    template = template_class(data)
    return template.get_message()


# Convenience functions for specific alert types
def create_build_failure_alert(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create build failure alert message."""
    data['alert']['type'] = 'build_failure'
    return create_alert_message(data)


def create_deployment_issue_alert(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create deployment issue alert message."""
    data['alert']['type'] = 'deployment_issue'
    return create_alert_message(data)


def create_security_vulnerability_alert(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create security vulnerability alert message."""
    data['alert']['type'] = 'security_vulnerability'
    return create_alert_message(data)


def create_service_outage_alert(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create service outage alert message."""
    data['alert']['type'] = 'service_outage'
    return create_alert_message(data)


def create_critical_bug_alert(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create critical bug alert message."""
    data['alert']['type'] = 'critical_bug'
    return create_alert_message(data)


def create_team_blocker_alert(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create team blocker alert message."""
    data['alert']['type'] = 'team_blocker'
    return create_alert_message(data)


def create_dependency_issue_alert(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create dependency issue alert message."""
    data['alert']['type'] = 'dependency_issue'
    return create_alert_message(data)