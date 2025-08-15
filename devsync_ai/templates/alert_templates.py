"""
Alert and notification templates for DevSync AI.
Provides urgent alert formatting with escalation capabilities.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from ..core.base_template import SlackMessageTemplate
from ..core.status_indicators import StatusType
from ..core.exceptions import DataValidationError


class AlertTemplate(SlackMessageTemplate):
    """Base template for urgent alert notifications."""
    
    REQUIRED_FIELDS = ['alert']
    
    def __init__(self, config=None, status_system=None):
        """Initialize alert template."""
        super().__init__(config, status_system)
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create alert message blocks."""
        alert = data['alert']
        blocks = []
        
        # Create urgency header
        blocks.extend(self.create_urgency_header(alert))
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add alert details
        blocks.extend(self._create_alert_details(alert))
        
        # Add impact section
        impact_section = self.create_impact_section(alert)
        if impact_section:
            blocks.extend(impact_section)
        
        # Add escalation buttons
        escalation_buttons = self.create_escalation_buttons(alert)
        if escalation_buttons:
            blocks.append(escalation_buttons)
        
        return blocks
    
    def create_urgency_header(self, alert: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create urgency header for critical issue highlighting."""
        severity = alert.get('severity', 'medium').lower()
        alert_type = alert.get('type', 'unknown')
        title = alert.get('title', 'Unknown Alert')
        
        # Get severity indicators
        severity_emoji = self._get_severity_emoji(severity)
        alert_emoji = self._get_alert_type_emoji(alert_type)
        
        # Create urgent header text
        header_text = f"🚨 {alert_emoji} {severity_emoji} {severity.upper()} ALERT"
        
        blocks = []
        
        # Header block
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text,
                "emoji": True
            }
        })
        
        # Title and description
        description = alert.get('description', '')
        alert_text = f"*{title}*"
        if description:
            alert_text += f"\n{description}"
        
        blocks.append(self.create_section_block(alert_text))
        
        return blocks
    
    def create_escalation_buttons(self, alert: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create escalation buttons for immediate action options."""
        if not self.config.interactive_elements:
            return None
        
        alert_id = alert.get('id', 'unknown')
        severity = alert.get('severity', 'medium').lower()
        
        actions = []
        
        # Severity-specific primary actions
        if severity == 'critical':
            actions.append({
                'text': '🚨 ESCALATE NOW',
                'action_id': 'escalate_critical',
                'value': f'escalate_{alert_id}',
                'style': 'danger'
            })
        
        # Common actions
        actions.extend([
            {
                'text': '👤 Take Ownership',
                'action_id': 'take_ownership',
                'value': f'assign_{alert_id}',
                'style': 'primary'
            },
            {
                'text': '📊 View Details',
                'action_id': 'view_details',
                'value': f'details_{alert_id}'
            },
            {
                'text': '💬 Add Update',
                'action_id': 'add_update',
                'value': f'update_{alert_id}'
            }
        ])
        
        # Add resolution button for non-critical alerts
        if severity != 'critical':
            actions.append({
                'text': '✅ Mark Resolved',
                'action_id': 'mark_resolved',
                'value': f'resolve_{alert_id}'
            })
        
        return self._create_action_buttons(actions)
    
    def create_impact_section(self, alert: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Create impact section for affected systems display."""
        affected_systems = alert.get('affected_systems', [])
        impact = alert.get('impact', '')
        
        if not affected_systems and not impact:
            return None
        
        blocks = []
        
        # Impact details
        impact_text = "*💥 Impact Assessment:*\n"
        
        if impact:
            impact_text += f"• Impact: {impact}\n"
        
        if affected_systems:
            systems_text = ", ".join(affected_systems)
            impact_text += f"• Affected Systems: {systems_text}\n"
        
        # Add SLA information if available
        sla_info = self._get_sla_information(alert)
        if sla_info:
            impact_text += f"• SLA Status: {sla_info}\n"
        
        blocks.append(self.create_section_block(impact_text.strip()))
        
        return blocks
    
    def _create_alert_details(self, alert: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create alert details section."""
        blocks = []
        
        # Basic alert information
        alert_id = alert.get('id', 'N/A')
        assigned_to = alert.get('assigned_to', 'Unassigned')
        created_at = alert.get('created_at', '')
        
        # Create fields for alert details
        fields = {
            '🆔 Alert ID': alert_id,
            '👤 Assigned To': self._format_user_mention(assigned_to)
        }
        
        if created_at:
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                fields['⏰ Created'] = created_date.strftime('%m/%d %I:%M %p')
            except (ValueError, AttributeError):
                fields['⏰ Created'] = created_at
        
        fields_section = self._create_summary_fields({'fields': fields}, {'fields': 'Alert Details'})
        if fields_section:
            blocks.append(fields_section)
        
        # Add escalation contacts if available
        escalation_contacts = alert.get('escalation_contacts', [])
        if escalation_contacts:
            contacts_text = "*📞 Escalation Contacts:*\n"
            for contact in escalation_contacts:
                if '@' in contact:  # Email
                    contacts_text += f"• 📧 {contact}\n"
                else:  # Username
                    contacts_text += f"• 👤 {self._format_user_mention(contact)}\n"
            
            blocks.append(self.create_section_block(contacts_text.strip()))
        
        return blocks
    
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
    
    def _get_sla_information(self, alert: Dict[str, Any]) -> Optional[str]:
        """Get SLA information and time remaining."""
        sla_breach_time = alert.get('sla_breach_time')
        if not sla_breach_time:
            return None
        
        try:
            # Parse the breach time
            if sla_breach_time.endswith('Z'):
                breach_time = datetime.fromisoformat(sla_breach_time.replace('Z', '+00:00'))
            else:
                breach_time = datetime.fromisoformat(sla_breach_time)
            
            # Get current time in the same timezone as breach_time
            if breach_time.tzinfo:
                from datetime import timezone
                now = datetime.now(timezone.utc)
            else:
                now = datetime.now()
            
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


class BuildFailureTemplate(AlertTemplate):
    """Template for build failure alerts with retry and blocking actions."""
    
    REQUIRED_FIELDS = ['alert', 'build_info']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create build failure message blocks."""
        alert = data['alert']
        build_info = data.get('build_info', {})
        
        blocks = []
        
        # Create urgency header
        blocks.extend(self.create_urgency_header(alert))
        
        # Add build-specific information
        blocks.extend(self._create_build_details(build_info))
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add alert details
        blocks.extend(self._create_alert_details(alert))
        
        # Add impact section
        impact_section = self.create_impact_section(alert)
        if impact_section:
            blocks.extend(impact_section)
        
        # Add build-specific action buttons
        build_actions = self._create_build_actions(alert, build_info)
        if build_actions:
            blocks.append(build_actions)
        
        return blocks
    
    def _create_build_details(self, build_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create build-specific details section."""
        branch = build_info.get('branch', 'Unknown')
        commit = build_info.get('commit', 'Unknown')
        pipeline_url = build_info.get('pipeline_url', '')
        failed_stage = build_info.get('failed_stage', 'Unknown')
        
        build_text = "*🔨 Build Information:*\n"
        build_text += f"• Branch: `{branch}`\n"
        build_text += f"• Commit: `{commit[:8] if len(commit) > 8 else commit}`\n"
        build_text += f"• Failed Stage: `{failed_stage}`\n"
        
        if pipeline_url:
            build_text += f"• Pipeline: {self._format_url_link(pipeline_url, 'View Build Logs')}"
        
        return [self.create_section_block(build_text)]
    
    def _create_build_actions(self, alert: Dict[str, Any], build_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create build-specific action buttons."""
        if not self.config.interactive_elements:
            return None
        
        alert_id = alert.get('id', '')
        pipeline_url = build_info.get('pipeline_url', '')
        
        actions = [
            {
                'text': '🔄 Retry Build',
                'action_id': 'retry_build',
                'value': f'retry_{alert_id}',
                'style': 'primary'
            },
            {
                'text': '📋 View Logs',
                'action_id': 'view_logs',
                'url': pipeline_url if pipeline_url else f'https://ci.company.com/build/{alert_id}'
            },
            {
                'text': '🚫 Block Deployments',
                'action_id': 'block_deployments',
                'value': f'block_{alert_id}',
                'style': 'danger'
            }
        ]
        
        return self._create_action_buttons(actions)


class DeploymentIssueTemplate(AlertTemplate):
    """Template for deployment issue alerts with rollback capabilities."""
    
    REQUIRED_FIELDS = ['alert', 'deployment_info']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create deployment issue message blocks."""
        alert = data['alert']
        deployment_info = data.get('deployment_info', {})
        
        blocks = []
        
        # Create urgency header
        blocks.extend(self.create_urgency_header(alert))
        
        # Add deployment-specific information
        blocks.extend(self._create_deployment_details(deployment_info))
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add alert details
        blocks.extend(self._create_alert_details(alert))
        
        # Add impact section
        impact_section = self.create_impact_section(alert)
        if impact_section:
            blocks.extend(impact_section)
        
        # Add deployment-specific action buttons
        deployment_actions = self._create_deployment_actions(alert, deployment_info)
        if deployment_actions:
            blocks.append(deployment_actions)
        
        return blocks
    
    def _create_deployment_details(self, deployment_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create deployment-specific details section."""
        environment = deployment_info.get('environment', 'Unknown')
        version = deployment_info.get('version', 'Unknown')
        previous_version = deployment_info.get('previous_version', 'Unknown')
        rollback_available = deployment_info.get('rollback_available', False)
        
        deployment_text = "*🚀 Deployment Information:*\n"
        deployment_text += f"• Environment: `{environment}`\n"
        deployment_text += f"• Version: `{version}`\n"
        deployment_text += f"• Previous Version: `{previous_version}`\n"
        deployment_text += f"• Rollback Available: {'✅ Yes' if rollback_available else '❌ No'}\n"
        
        return [self.create_section_block(deployment_text)]
    
    def _create_deployment_actions(self, alert: Dict[str, Any], deployment_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create deployment-specific action buttons."""
        if not self.config.interactive_elements:
            return None
        
        alert_id = alert.get('id', '')
        rollback_available = deployment_info.get('rollback_available', False)
        
        actions = []
        
        # Add rollback button if available
        if rollback_available:
            actions.append({
                'text': '⏪ ROLLBACK NOW',
                'action_id': 'rollback_deployment',
                'value': f'rollback_{alert_id}',
                'style': 'danger'
            })
        
        # Common deployment actions
        actions.extend([
            {
                'text': '📊 Check Health',
                'action_id': 'check_health',
                'value': f'health_{alert_id}'
            },
            {
                'text': '📈 View Metrics',
                'action_id': 'view_metrics',
                'value': f'metrics_{alert_id}'
            },
            {
                'text': '🔄 Retry Deploy',
                'action_id': 'retry_deployment',
                'value': f'retry_deploy_{alert_id}'
            }
        ])
        
        return self._create_action_buttons(actions)


class SecurityVulnerabilityTemplate(AlertTemplate):
    """Template for security vulnerability alerts with CVE alerts and incident response."""
    
    REQUIRED_FIELDS = ['alert', 'security_info']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create security vulnerability message blocks."""
        alert = data['alert']
        security_info = data.get('security_info', {})
        
        blocks = []
        
        # Create urgency header
        blocks.extend(self.create_urgency_header(alert))
        
        # Add security-specific information
        blocks.extend(self._create_security_details(security_info))
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add alert details
        blocks.extend(self._create_alert_details(alert))
        
        # Add impact section
        impact_section = self.create_impact_section(alert)
        if impact_section:
            blocks.extend(impact_section)
        
        # Add security-specific action buttons
        security_actions = self._create_security_actions(alert)
        if security_actions:
            blocks.append(security_actions)
        
        return blocks
    
    def _create_security_details(self, security_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create security-specific details section."""
        cve_id = security_info.get('cve_id', '')
        cvss_score = security_info.get('cvss_score', 0)
        attack_vector = security_info.get('attack_vector', 'Unknown')
        
        security_text = "*🔒 Security Information:*\n"
        
        if cve_id:
            security_text += f"• CVE ID: `{cve_id}`\n"
        
        if cvss_score:
            security_text += f"• CVSS Score: `{cvss_score}/10`\n"
        
        security_text += f"• Attack Vector: `{attack_vector}`\n"
        security_text += "• **⚠️ SECURITY INCIDENT - CONFIDENTIAL**"
        
        return [self.create_section_block(security_text)]
    
    def _create_security_actions(self, alert: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create security-specific action buttons."""
        if not self.config.interactive_elements:
            return None
        
        alert_id = alert.get('id', '')
        
        actions = [
            {
                'text': '🚨 ESCALATE TO SECURITY',
                'action_id': 'escalate_security',
                'value': f'security_escalate_{alert_id}',
                'style': 'danger'
            },
            {
                'text': '🔒 Start Incident Response',
                'action_id': 'start_incident_response',
                'value': f'incident_{alert_id}',
                'style': 'primary'
            },
            {
                'text': '📋 Create Security Ticket',
                'action_id': 'create_security_ticket',
                'value': f'sec_ticket_{alert_id}'
            }
        ]
        
        return self._create_action_buttons(actions)


class ServiceOutageTemplate(AlertTemplate):
    """Template for service outage alerts with disruption alerts and war room activation."""
    
    REQUIRED_FIELDS = ['alert', 'outage_info']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create service outage message blocks."""
        alert = data['alert']
        outage_info = data.get('outage_info', {})
        
        blocks = []
        
        # Create urgency header
        blocks.extend(self.create_urgency_header(alert))
        
        # Add outage-specific information
        blocks.extend(self._create_outage_details(outage_info))
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add alert details
        blocks.extend(self._create_alert_details(alert))
        
        # Add impact section
        impact_section = self.create_impact_section(alert)
        if impact_section:
            blocks.extend(impact_section)
        
        # Add outage-specific action buttons
        outage_actions = self._create_outage_actions(alert, outage_info)
        if outage_actions:
            blocks.append(outage_actions)
        
        return blocks
    
    def _create_outage_details(self, outage_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create outage-specific details section."""
        services = outage_info.get('services', [])
        users_affected = outage_info.get('users_affected', 0)
        status_page = outage_info.get('status_page', '')
        
        outage_text = "*⚡ Outage Information:*\n"
        
        if services:
            services_str = ", ".join(services)
            outage_text += f"• Affected Services: `{services_str}`\n"
        
        if users_affected:
            outage_text += f"• Users Affected: `{users_affected:,}`\n"
        
        if status_page:
            outage_text += f"• Status Page: {self._format_url_link(status_page, 'View Status')}\n"
        
        outage_text += "• **🚨 SERVICE DISRUPTION IN PROGRESS**"
        
        return [self.create_section_block(outage_text)]
    
    def _create_outage_actions(self, alert: Dict[str, Any], outage_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create outage-specific action buttons."""
        if not self.config.interactive_elements:
            return None
        
        alert_id = alert.get('id', '')
        status_page = outage_info.get('status_page', 'https://status.company.com')
        
        actions = [
            {
                'text': '📢 Update Status Page',
                'action_id': 'update_status_page',
                'url': status_page,
                'style': 'primary'
            },
            {
                'text': '📞 Start War Room',
                'action_id': 'start_war_room',
                'value': f'war_room_{alert_id}',
                'style': 'danger'
            },
            {
                'text': '📊 Check Monitoring',
                'action_id': 'check_monitoring',
                'value': f'monitoring_{alert_id}'
            }
        ]
        
        return self._create_action_buttons(actions)


class CriticalBugTemplate(AlertTemplate):
    """Template for critical bug alerts highlighting data integrity issues."""
    
    REQUIRED_FIELDS = ['alert']
    
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create critical bug message blocks."""
        alert = data['alert']
        
        blocks = []
        
        # Create urgency header
        blocks.extend(self.create_urgency_header(alert))
        
        # Add bug-specific information
        blocks.extend(self._create_bug_details(alert))
        
        # Add divider
        blocks.append(self.create_divider_block())
        
        # Add alert details
        blocks.extend(self._create_alert_details(alert))
        
        # Add impact section
        impact_section = self.create_impact_section(alert)
        if impact_section:
            blocks.extend(impact_section)
        
        # Add bug-specific action buttons
        bug_actions = self._create_bug_actions(alert)
        if bug_actions:
            blocks.append(bug_actions)
        
        return blocks
    
    def _create_bug_details(self, alert: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create bug-specific details section."""
        bug_info = alert.get('bug_info', {})
        reproduction_steps = bug_info.get('reproduction_steps', [])
        data_affected = bug_info.get('data_affected', '')
        
        bug_text = "*🐛 Bug Information:*\n"
        
        if data_affected:
            bug_text += f"• Data Affected: {data_affected}\n"
        
        if reproduction_steps:
            bug_text += "• Reproduction Steps:\n"
            for i, step in enumerate(reproduction_steps, 1):
                bug_text += f"  {i}. {step}\n"
        
        bug_text += "• **⚠️ DATA INTEGRITY ISSUE - IMMEDIATE ATTENTION REQUIRED**"
        
        return [self.create_section_block(bug_text)]
    
    def _create_bug_actions(self, alert: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create bug-specific action buttons."""
        if not self.config.interactive_elements:
            return None
        
        alert_id = alert.get('id', '')
        
        actions = [
            {
                'text': '🚨 ESCALATE IMMEDIATELY',
                'action_id': 'escalate_bug',
                'value': f'escalate_bug_{alert_id}',
                'style': 'danger'
            },
            {
                'text': '🔍 Start Investigation',
                'action_id': 'start_investigation',
                'value': f'investigate_{alert_id}',
                'style': 'primary'
            },
            {
                'text': '📊 Check Data Impact',
                'action_id': 'check_data_impact',
                'value': f'data_impact_{alert_id}'
            },
            {
                'text': '🛠️ Create Hotfix',
                'action_id': 'create_hotfix',
                'value': f'hotfix_{alert_id}'
            }
        ]
        
        return self._create_action_buttons(actions)