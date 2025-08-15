"""
Tests for new alert templates in the templates directory.
"""

import pytest
from datetime import datetime, timedelta
from devsync_ai.templates.alert_templates import (
    AlertTemplate,
    BuildFailureTemplate,
    DeploymentIssueTemplate,
    SecurityVulnerabilityTemplate,
    ServiceOutageTemplate,
    CriticalBugTemplate
)
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.core.status_indicators import StatusIndicatorSystem


@pytest.fixture
def sample_config():
    """Create sample template configuration for testing."""
    return TemplateConfig(
        team_id="test-team",
        branding={
            "primary_color": "#FF0000",
            "logo_emoji": "🚨",
            "team_name": "Test Team"
        },
        emoji_set={
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        },
        color_scheme={
            "critical": "#FF0000",
            "high": "#FF8C00",
            "medium": "#FFD700",
            "low": "#32CD32"
        },
        interactive_elements=True,
        accessibility_mode=False
    )


@pytest.fixture
def status_system():
    """Create status indicator system for testing."""
    return StatusIndicatorSystem()


class TestAlertTemplate:
    """Test base AlertTemplate functionality."""
    
    def test_alert_template_initialization(self, sample_config, status_system):
        """Test alert template initialization."""
        template = AlertTemplate(sample_config, status_system)
        assert template.config == sample_config
        assert template.status_system == status_system
        assert template.REQUIRED_FIELDS == ['alert']
    
    def test_basic_alert_message_creation(self, sample_config):
        """Test basic alert message creation."""
        template = AlertTemplate(sample_config)
        
        data = {
            "alert": {
                "id": "TEST-001",
                "type": "critical_bug",
                "severity": "critical",
                "title": "Test Alert",
                "description": "Test alert description",
                "affected_systems": ["System A", "System B"],
                "impact": "Test impact",
                "created_at": datetime.now().isoformat() + "Z",
                "assigned_to": "test-team"
            }
        }
        
        message = template.format_message(data)
        
        assert message is not None
        assert len(message.blocks) > 0
        assert message.text is not None
        assert message.metadata['template_type'] == 'AlertTemplate'
    
    def test_urgency_header_creation(self, sample_config):
        """Test urgency header creation."""
        template = AlertTemplate(sample_config)
        
        alert = {
            "severity": "critical",
            "type": "security_vulnerability",
            "title": "Critical Security Issue",
            "description": "Security vulnerability detected"
        }
        
        header_blocks = template.create_urgency_header(alert)
        
        assert len(header_blocks) >= 2
        assert header_blocks[0]["type"] == "header"
        assert "CRITICAL ALERT" in header_blocks[0]["text"]["text"]
        assert "🔒" in header_blocks[0]["text"]["text"]  # Security emoji
        assert "🔴" in header_blocks[0]["text"]["text"]  # Critical emoji
    
    def test_escalation_buttons_creation(self, sample_config):
        """Test escalation buttons creation."""
        template = AlertTemplate(sample_config)
        
        alert = {
            "id": "TEST-002",
            "severity": "critical"
        }
        
        buttons = template.create_escalation_buttons(alert)
        
        assert buttons is not None
        assert buttons["type"] == "actions"
        assert len(buttons["elements"]) > 0
        
        # Check for escalate button in critical alerts
        escalate_found = False
        for element in buttons["elements"]:
            if "ESCALATE NOW" in element["text"]["text"]:
                escalate_found = True
                assert element["style"] == "danger"
        
        assert escalate_found
    
    def test_impact_section_creation(self, sample_config):
        """Test impact section creation."""
        template = AlertTemplate(sample_config)
        
        alert = {
            "affected_systems": ["Database", "API Gateway"],
            "impact": "Service unavailable",
            "sla_breach_time": (datetime.now() + timedelta(hours=1)).isoformat() + "Z"
        }
        
        impact_blocks = template.create_impact_section(alert)
        
        assert impact_blocks is not None
        assert len(impact_blocks) > 0
        assert impact_blocks[0]["type"] == "section"
        
        text = impact_blocks[0]["text"]["text"]
        assert "Impact Assessment" in text
        assert "Database" in text
        assert "API Gateway" in text
        assert "Service unavailable" in text
        assert ("remaining" in text or "BREACHED" in text)  # SLA info
    
    def test_severity_emoji_mapping(self, sample_config):
        """Test severity emoji mapping."""
        template = AlertTemplate(sample_config)
        
        assert template._get_severity_emoji('critical') == '🔴'
        assert template._get_severity_emoji('high') == '🟠'
        assert template._get_severity_emoji('medium') == '🟡'
        assert template._get_severity_emoji('low') == '🟢'
        assert template._get_severity_emoji('unknown') == '🟡'
    
    def test_alert_type_emoji_mapping(self, sample_config):
        """Test alert type emoji mapping."""
        template = AlertTemplate(sample_config)
        
        assert template._get_alert_type_emoji('build_failure') == '🔨'
        assert template._get_alert_type_emoji('deployment_issue') == '🚀'
        assert template._get_alert_type_emoji('security_vulnerability') == '🔒'
        assert template._get_alert_type_emoji('service_outage') == '⚡'
        assert template._get_alert_type_emoji('critical_bug') == '🐛'
        assert template._get_alert_type_emoji('team_blocker') == '🚫'
        assert template._get_alert_type_emoji('unknown') == '⚠️'
    
    def test_sla_information_calculation(self, sample_config):
        """Test SLA information calculation."""
        template = AlertTemplate(sample_config)
        
        # Future time - use UTC timezone for consistency
        from datetime import timezone
        future_time = (datetime.now(timezone.utc) + timedelta(hours=2, minutes=30)).isoformat()
        alert_future = {"sla_breach_time": future_time}
        result = template._get_sla_information(alert_future)
        assert result is not None
        # Should show remaining time for future dates
        assert ("remaining" in result and ("h" in result or "m" in result))
        
        # Past time (breached)
        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        alert_past = {"sla_breach_time": past_time}
        result = template._get_sla_information(alert_past)
        assert result is not None and "BREACHED" in result
        
        # No SLA
        alert_no_sla = {}
        result = template._get_sla_information(alert_no_sla)
        assert result is None


class TestBuildFailureTemplate:
    """Test BuildFailureTemplate functionality."""
    
    def test_build_failure_template_creation(self, sample_config):
        """Test build failure template creation."""
        template = BuildFailureTemplate(sample_config)
        
        data = {
            "alert": {
                "id": "BUILD-001",
                "type": "build_failure",
                "severity": "high",
                "title": "Production Build Failing",
                "description": "Unit tests failing in authentication module",
                "affected_systems": ["CI/CD Pipeline"],
                "impact": "Deployments blocked"
            },
            "build_info": {
                "branch": "main",
                "commit": "abc123def456",
                "pipeline_url": "https://ci.company.com/build/123",
                "failed_stage": "unit-tests"
            }
        }
        
        message = template.format_message(data)
        
        assert message is not None
        assert len(message.blocks) > 0
        
        # Check for build information
        build_info_found = False
        for block in message.blocks:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Build Information" in text and "main" in text:
                    build_info_found = True
        
        assert build_info_found
        
        # Check for retry build button
        retry_found = False
        for block in message.blocks:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "Retry Build" in element.get("text", {}).get("text", ""):
                        retry_found = True
        
        assert retry_found
    
    def test_build_details_section(self, sample_config):
        """Test build details section creation."""
        template = BuildFailureTemplate(sample_config)
        
        build_info = {
            "branch": "feature/auth",
            "commit": "1234567890abcdef",
            "pipeline_url": "https://ci.example.com/build/456",
            "failed_stage": "integration-tests"
        }
        
        build_blocks = template._create_build_details(build_info)
        
        assert len(build_blocks) == 1
        assert build_blocks[0]["type"] == "section"
        
        text = build_blocks[0]["text"]["text"]
        assert "Build Information" in text
        assert "feature/auth" in text
        assert "12345678" in text  # Truncated commit
        assert "integration-tests" in text
        assert "View Build Logs" in text


class TestDeploymentIssueTemplate:
    """Test DeploymentIssueTemplate functionality."""
    
    def test_deployment_issue_template_creation(self, sample_config):
        """Test deployment issue template creation."""
        template = DeploymentIssueTemplate(sample_config)
        
        data = {
            "alert": {
                "id": "DEPLOY-001",
                "type": "deployment_issue",
                "severity": "critical",
                "title": "Production Deployment Failed",
                "description": "Database migration failed during deployment",
                "affected_systems": ["Production Environment"],
                "impact": "Service degraded"
            },
            "deployment_info": {
                "environment": "production",
                "version": "v2.1.0",
                "previous_version": "v2.0.9",
                "rollback_available": True
            }
        }
        
        message = template.format_message(data)
        
        assert message is not None
        assert len(message.blocks) > 0
        
        # Check for deployment information
        deployment_info_found = False
        for block in message.blocks:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Deployment Information" in text and "production" in text:
                    deployment_info_found = True
        
        assert deployment_info_found
        
        # Check for rollback button
        rollback_found = False
        for block in message.blocks:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "ROLLBACK NOW" in element.get("text", {}).get("text", ""):
                        rollback_found = True
        
        assert rollback_found


class TestSecurityVulnerabilityTemplate:
    """Test SecurityVulnerabilityTemplate functionality."""
    
    def test_security_vulnerability_template_creation(self, sample_config):
        """Test security vulnerability template creation."""
        template = SecurityVulnerabilityTemplate(sample_config)
        
        data = {
            "alert": {
                "id": "SEC-001",
                "type": "security_vulnerability",
                "severity": "critical",
                "title": "SQL Injection Vulnerability",
                "description": "Critical SQL injection found in user authentication",
                "affected_systems": ["Authentication API"],
                "impact": "Potential data breach"
            },
            "security_info": {
                "cve_id": "CVE-2025-12345",
                "cvss_score": 9.8,
                "attack_vector": "Network"
            }
        }
        
        message = template.format_message(data)
        
        assert message is not None
        assert len(message.blocks) > 0
        
        # Check for security information
        security_info_found = False
        confidential_found = False
        for block in message.blocks:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Security Information" in text and "CVE-2025-12345" in text:
                    security_info_found = True
                if "CONFIDENTIAL" in text:
                    confidential_found = True
        
        assert security_info_found
        assert confidential_found
        
        # Check for security escalation button
        escalate_found = False
        for block in message.blocks:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "ESCALATE TO SECURITY" in element.get("text", {}).get("text", ""):
                        escalate_found = True
        
        assert escalate_found


class TestServiceOutageTemplate:
    """Test ServiceOutageTemplate functionality."""
    
    def test_service_outage_template_creation(self, sample_config):
        """Test service outage template creation."""
        template = ServiceOutageTemplate(sample_config)
        
        data = {
            "alert": {
                "id": "OUTAGE-001",
                "type": "service_outage",
                "severity": "critical",
                "title": "Complete API Service Outage",
                "description": "All API services are down",
                "affected_systems": ["API Gateway", "User Service"],
                "impact": "Complete service unavailability"
            },
            "outage_info": {
                "services": ["API Gateway", "User Service", "Payment Service"],
                "users_affected": 50000,
                "status_page": "https://status.company.com"
            }
        }
        
        message = template.format_message(data)
        
        assert message is not None
        assert len(message.blocks) > 0
        
        # Check for outage information
        outage_info_found = False
        disruption_found = False
        for block in message.blocks:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Outage Information" in text and "50,000" in text:
                    outage_info_found = True
                if "SERVICE DISRUPTION" in text:
                    disruption_found = True
        
        assert outage_info_found
        assert disruption_found
        
        # Check for war room button
        war_room_found = False
        for block in message.blocks:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "Start War Room" in element.get("text", {}).get("text", ""):
                        war_room_found = True
        
        assert war_room_found


class TestCriticalBugTemplate:
    """Test CriticalBugTemplate functionality."""
    
    def test_critical_bug_template_creation(self, sample_config):
        """Test critical bug template creation."""
        template = CriticalBugTemplate(sample_config)
        
        data = {
            "alert": {
                "id": "BUG-001",
                "type": "critical_bug",
                "severity": "critical",
                "title": "Data Corruption in Payment Processing",
                "description": "Payment amounts being calculated incorrectly",
                "affected_systems": ["Payment Processing"],
                "impact": "Incorrect charges to customers",
                "bug_info": {
                    "data_affected": "500 transactions in last 2 hours",
                    "reproduction_steps": [
                        "Process payment > $100",
                        "Check transaction record",
                        "Compare with actual charge"
                    ]
                }
            }
        }
        
        message = template.format_message(data)
        
        assert message is not None
        assert len(message.blocks) > 0
        
        # Check for bug information and data integrity warning
        bug_info_found = False
        data_integrity_found = False
        for block in message.blocks:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Bug Information" in text and "500 transactions" in text:
                    bug_info_found = True
                if "DATA INTEGRITY" in text:
                    data_integrity_found = True
        
        assert bug_info_found
        assert data_integrity_found
        
        # Check for escalation button
        escalate_found = False
        for block in message.blocks:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "ESCALATE IMMEDIATELY" in element.get("text", {}).get("text", ""):
                        escalate_found = True
        
        assert escalate_found


class TestAlertTemplateErrorHandling:
    """Test error handling in alert templates."""
    
    def test_missing_required_fields(self, sample_config):
        """Test handling of missing required fields."""
        template = AlertTemplate(sample_config)
        
        # Missing alert field - should handle gracefully with placeholder
        message = template.format_message({})
        assert message is not None  # Should handle gracefully
    
    def test_empty_alert_data(self, sample_config):
        """Test handling of empty alert data."""
        template = AlertTemplate(sample_config)
        
        data = {"alert": {}}
        message = template.format_message(data)
        
        # Should handle gracefully
        assert message is not None
        assert len(message.blocks) > 0
    
    def test_malformed_timestamps(self, sample_config):
        """Test handling of malformed timestamps."""
        template = AlertTemplate(sample_config)
        
        data = {
            "alert": {
                "id": "TEST-001",
                "created_at": "invalid-timestamp",
                "sla_breach_time": "also-invalid"
            }
        }
        
        # Should not raise exception
        message = template.format_message(data)
        assert message is not None
    
    def test_interactive_elements_disabled(self, sample_config):
        """Test behavior when interactive elements are disabled."""
        sample_config.interactive_elements = False
        template = AlertTemplate(sample_config)
        
        alert = {"id": "TEST-001", "severity": "critical"}
        buttons = template.create_escalation_buttons(alert)
        
        assert buttons is None


class TestAlertTemplateAccessibility:
    """Test accessibility features in alert templates."""
    
    def test_fallback_text_generation(self, sample_config):
        """Test fallback text generation for accessibility."""
        template = AlertTemplate(sample_config)
        
        data = {
            "alert": {
                "id": "ACCESS-001",
                "type": "critical_bug",
                "severity": "critical",
                "title": "Accessibility Test Alert",
                "description": "Testing fallback text generation"
            }
        }
        
        message = template.format_message(data)
        
        assert message.text is not None
        assert len(message.text) > 0
        assert "Accessibility Test Alert" in message.text
    
    def test_accessibility_mode_enabled(self, sample_config):
        """Test behavior when accessibility mode is enabled."""
        sample_config.accessibility_mode = True
        template = AlertTemplate(sample_config)
        
        data = {
            "alert": {
                "id": "ACCESS-002",
                "title": "Accessibility Mode Test",
                "description": "Testing accessibility mode"
            }
        }
        
        message = template.format_message(data)
        
        # Should still generate valid message
        assert message is not None
        assert len(message.blocks) > 0


if __name__ == "__main__":
    # Run basic tests
    print("Testing Alert Templates...")
    
    config = TemplateConfig(
        team_id="test",
        branding={},
        emoji_set={},
        color_scheme={},
        interactive_elements=True,
        accessibility_mode=False
    )
    
    # Test each template type
    templates = [
        (AlertTemplate, "alert"),
        (BuildFailureTemplate, "build_failure"),
        (DeploymentIssueTemplate, "deployment_issue"),
        (SecurityVulnerabilityTemplate, "security_vulnerability"),
        (ServiceOutageTemplate, "service_outage"),
        (CriticalBugTemplate, "critical_bug")
    ]
    
    for template_class, alert_type in templates:
        template = template_class(config)
        
        data = {
            "alert": {
                "id": f"TEST-{alert_type.upper()}",
                "type": alert_type,
                "severity": "high",
                "title": f"Test {alert_type.replace('_', ' ').title()}",
                "description": f"Test {alert_type} description"
            }
        }
        
        # Add type-specific data
        if alert_type == "build_failure":
            data["build_info"] = {"branch": "main", "commit": "abc123"}
        elif alert_type == "deployment_issue":
            data["deployment_info"] = {"environment": "test", "version": "v1.0.0", "rollback_available": True}
        elif alert_type == "security_vulnerability":
            data["security_info"] = {"cve_id": "CVE-2025-TEST", "cvss_score": 7.5}
        elif alert_type == "service_outage":
            data["outage_info"] = {"services": ["Test Service"], "users_affected": 100}
        
        try:
            message = template.format_message(data)
            print(f"✅ {template_class.__name__}: {len(message.blocks)} blocks generated")
        except Exception as e:
            print(f"❌ {template_class.__name__}: Error - {e}")
    
    print("Alert template tests completed!")