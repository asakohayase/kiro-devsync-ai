"""
Tests for alert message templates.
"""

import pytest
from datetime import datetime, timedelta
from devsync_ai.services.alert_templates import (
    AlertTemplateBase,
    BuildFailureTemplate,
    DeploymentIssueTemplate,
    SecurityVulnerabilityTemplate,
    ServiceOutageTemplate,
    create_alert_message,
    create_build_failure_alert,
    create_deployment_issue_alert,
    create_security_vulnerability_alert,
    create_service_outage_alert,
    create_critical_bug_alert,
    create_team_blocker_alert,
    create_dependency_issue_alert
)


class TestAlertTemplateBase:
    """Test alert template base functionality."""
    
    def test_severity_emoji_mapping(self):
        """Test severity emoji mapping."""
        template = AlertTemplateBase({})
        
        assert template._get_severity_emoji('critical') == '🔴'
        assert template._get_severity_emoji('high') == '🟠'
        assert template._get_severity_emoji('medium') == '🟡'
        assert template._get_severity_emoji('low') == '🟢'
        assert template._get_severity_emoji('unknown') == '🟡'  # default
    
    def test_alert_type_emoji_mapping(self):
        """Test alert type emoji mapping."""
        template = AlertTemplateBase({})
        
        assert template._get_alert_type_emoji('build_failure') == '🔨'
        assert template._get_alert_type_emoji('deployment_issue') == '🚀'
        assert template._get_alert_type_emoji('security_vulnerability') == '🔒'
        assert template._get_alert_type_emoji('service_outage') == '⚡'
        assert template._get_alert_type_emoji('unknown') == '⚠️'  # default
    
    def test_severity_color_mapping(self):
        """Test severity color mapping."""
        template = AlertTemplateBase({})
        
        assert template._get_severity_color('critical') == '#FF0000'
        assert template._get_severity_color('high') == '#FF8C00'
        assert template._get_severity_color('medium') == '#FFD700'
        assert template._get_severity_color('low') == '#32CD32'
        assert template._get_severity_color('unknown') == '#FFD700'  # default
    
    def test_sla_time_calculation(self):
        """Test SLA time remaining calculation."""
        template = AlertTemplateBase({})
        
        # Future time
        future_time = (datetime.now() + timedelta(hours=2, minutes=30)).isoformat() + "Z"
        result = template._calculate_time_remaining(future_time)
        assert "2h 30m remaining" in result or "2h 29m remaining" in result  # Account for test execution time
        
        # Past time (breached)
        past_time = (datetime.now() - timedelta(hours=1)).isoformat() + "Z"
        result = template._calculate_time_remaining(past_time)
        assert "SLA BREACHED" in result
        
        # No SLA
        result = template._calculate_time_remaining("")
        assert "No SLA defined" in result
        
        # Invalid time
        result = template._calculate_time_remaining("invalid-time")
        assert "Invalid SLA time" in result


class TestBuildFailureTemplate:
    """Test build failure alert template."""
    
    def test_build_failure_template(self):
        """Test basic build failure template."""
        data = {
            "alert": {
                "id": "ALERT-001",
                "type": "build_failure",
                "severity": "high",
                "title": "Production Build Failing",
                "description": "Main branch build failing due to test failures",
                "affected_systems": ["CI/CD", "Production Deployment"],
                "impact": "Blocks all deployments",
                "created_at": datetime.now().isoformat() + "Z",
                "assigned_to": "devops-team",
                "sla_breach_time": (datetime.now() + timedelta(hours=2)).isoformat() + "Z"
            },
            "build_info": {
                "branch": "main",
                "commit": "abc123def456",
                "pipeline_url": "https://ci.company.com/build/123"
            }
        }
        
        template = BuildFailureTemplate(data)
        message = template.get_message()
        
        assert "blocks" in message
        assert len(message["blocks"]) > 0
        
        # Check for alert header
        header_found = False
        for block in message["blocks"]:
            if block.get("type") == "header":
                header_found = True
                assert "HIGH ALERT" in block["text"]["text"]
        
        assert header_found, "Alert header not found"
        
        # Check for build information
        build_info_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Build Information" in text and "main" in text:
                    build_info_found = True
        
        assert build_info_found, "Build information not found"
        
        # Check for retry build button
        retry_found = False
        for block in message["blocks"]:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "Retry Build" in element.get("text", {}).get("text", ""):
                        retry_found = True
        
        assert retry_found, "Retry build button not found"


class TestDeploymentIssueTemplate:
    """Test deployment issue alert template."""
    
    def test_deployment_issue_template(self):
        """Test deployment issue template."""
        data = {
            "alert": {
                "id": "ALERT-002",
                "type": "deployment_issue",
                "severity": "critical",
                "title": "Production Deployment Failed",
                "description": "Deployment to production environment failed",
                "affected_systems": ["Production", "API"],
                "impact": "Service unavailable",
                "created_at": datetime.now().isoformat() + "Z",
                "assigned_to": "sre-team"
            },
            "deployment_info": {
                "environment": "production",
                "version": "v2.1.0",
                "rollback_available": True
            }
        }
        
        template = DeploymentIssueTemplate(data)
        message = template.get_message()
        
        assert "blocks" in message
        
        # Check for critical alert header
        header_found = False
        for block in message["blocks"]:
            if block.get("type") == "header":
                header_found = True
                assert "CRITICAL ALERT" in block["text"]["text"]
        
        assert header_found, "Critical alert header not found"
        
        # Check for deployment information
        deployment_info_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Deployment Information" in text and "production" in text:
                    deployment_info_found = True
        
        assert deployment_info_found, "Deployment information not found"
        
        # Check for rollback button
        rollback_found = False
        for block in message["blocks"]:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "ROLLBACK NOW" in element.get("text", {}).get("text", ""):
                        rollback_found = True
        
        assert rollback_found, "Rollback button not found"


class TestSecurityVulnerabilityTemplate:
    """Test security vulnerability alert template."""
    
    def test_security_vulnerability_template(self):
        """Test security vulnerability template."""
        data = {
            "alert": {
                "id": "ALERT-003",
                "type": "security_vulnerability",
                "severity": "critical",
                "title": "Critical Security Vulnerability Detected",
                "description": "SQL injection vulnerability in user authentication",
                "affected_systems": ["Authentication", "User Database"],
                "impact": "Potential data breach",
                "created_at": datetime.now().isoformat() + "Z",
                "assigned_to": "security-team"
            },
            "security_info": {
                "cve_id": "CVE-2025-12345",
                "cvss_score": 9.8,
                "attack_vector": "Network"
            }
        }
        
        template = SecurityVulnerabilityTemplate(data)
        message = template.get_message()
        
        assert "blocks" in message
        
        # Check for security information
        security_info_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Security Information" in text and "CVE-2025-12345" in text:
                    security_info_found = True
        
        assert security_info_found, "Security information not found"
        
        # Check for confidential warning
        confidential_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "CONFIDENTIAL" in text:
                    confidential_found = True
        
        assert confidential_found, "Confidential warning not found"
        
        # Check for security escalation button
        escalate_found = False
        for block in message["blocks"]:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "ESCALATE TO SECURITY" in element.get("text", {}).get("text", ""):
                        escalate_found = True
        
        assert escalate_found, "Security escalation button not found"


class TestServiceOutageTemplate:
    """Test service outage alert template."""
    
    def test_service_outage_template(self):
        """Test service outage template."""
        data = {
            "alert": {
                "id": "ALERT-004",
                "type": "service_outage",
                "severity": "critical",
                "title": "API Service Outage",
                "description": "Main API service is completely down",
                "affected_systems": ["API", "Mobile App", "Web App"],
                "impact": "All user-facing services unavailable",
                "created_at": datetime.now().isoformat() + "Z",
                "assigned_to": "sre-team"
            },
            "outage_info": {
                "services": ["API Gateway", "User Service", "Payment Service"],
                "users_affected": 50000,
                "status_page": "https://status.company.com"
            }
        }
        
        template = ServiceOutageTemplate(data)
        message = template.get_message()
        
        assert "blocks" in message
        
        # Check for outage information
        outage_info_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "Outage Information" in text and "50,000" in text:
                    outage_info_found = True
        
        assert outage_info_found, "Outage information not found"
        
        # Check for service disruption warning
        disruption_found = False
        for block in message["blocks"]:
            if block.get("type") == "section" and block.get("text"):
                text = block["text"].get("text", "")
                if "SERVICE DISRUPTION" in text:
                    disruption_found = True
        
        assert disruption_found, "Service disruption warning not found"
        
        # Check for war room button
        war_room_found = False
        for block in message["blocks"]:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "Start War Room" in element.get("text", {}).get("text", ""):
                        war_room_found = True
        
        assert war_room_found, "War room button not found"


class TestAlertTemplateFactory:
    """Test alert template factory functions."""
    
    def test_create_alert_message_factory(self):
        """Test main factory function."""
        data = {
            "alert": {
                "id": "ALERT-005",
                "type": "build_failure",
                "severity": "medium",
                "title": "Test Build Alert",
                "description": "Test description"
            }
        }
        
        message = create_alert_message(data)
        assert "blocks" in message
        assert "text" in message
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        base_data = {
            "alert": {
                "id": "ALERT-006",
                "title": "Test Alert",
                "description": "Test description",
                "severity": "medium"
            }
        }
        
        # Test all convenience functions
        functions_to_test = [
            create_build_failure_alert,
            create_deployment_issue_alert,
            create_security_vulnerability_alert,
            create_service_outage_alert,
            create_critical_bug_alert,
            create_team_blocker_alert,
            create_dependency_issue_alert
        ]
        
        for func in functions_to_test:
            test_data = {**base_data}
            message = func(test_data)
            
            assert "blocks" in message
            assert "text" in message
            assert len(message["blocks"]) > 0


class TestAlertSeverityHandling:
    """Test alert severity-specific handling."""
    
    def test_critical_alert_mentions(self):
        """Test critical alerts include channel mentions."""
        data = {
            "alert": {
                "id": "ALERT-007",
                "type": "service_outage",
                "severity": "critical",
                "title": "Critical Test Alert",
                "description": "Critical alert test"
            }
        }
        
        message = create_alert_message(data)
        
        # Check for channel mention in context
        mention_found = False
        for block in message["blocks"]:
            if block.get("type") == "context":
                for element in block.get("elements", []):
                    text = element.get("text", "")
                    if "<!channel>" in text:
                        mention_found = True
        
        assert mention_found, "Channel mention not found for critical alert"
    
    def test_high_alert_mentions(self):
        """Test high alerts include here mentions."""
        data = {
            "alert": {
                "id": "ALERT-008",
                "type": "build_failure",
                "severity": "high",
                "title": "High Priority Test Alert",
                "description": "High priority alert test"
            }
        }
        
        message = create_alert_message(data)
        
        # Check for here mention in context
        mention_found = False
        for block in message["blocks"]:
            if block.get("type") == "context":
                for element in block.get("elements", []):
                    text = element.get("text", "")
                    if "<!here>" in text:
                        mention_found = True
        
        assert mention_found, "Here mention not found for high alert"
    
    def test_critical_alert_escalation_button(self):
        """Test critical alerts have escalation buttons."""
        data = {
            "alert": {
                "id": "ALERT-009",
                "type": "critical_bug",
                "severity": "critical",
                "title": "Critical Bug Alert",
                "description": "Critical bug found"
            }
        }
        
        message = create_alert_message(data)
        
        # Check for escalation button
        escalate_found = False
        for block in message["blocks"]:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    if "ESCALATE NOW" in element.get("text", {}).get("text", ""):
                        escalate_found = True
        
        assert escalate_found, "Escalation button not found for critical alert"


class TestAlertTemplateValidation:
    """Test alert template validation and error handling."""
    
    def test_empty_data_handling(self):
        """Test templates handle empty data gracefully."""
        empty_data = {"alert": {}}
        
        message = create_alert_message(empty_data)
        assert "blocks" in message
        assert "text" in message
    
    def test_missing_required_fields(self):
        """Test templates handle missing required fields."""
        minimal_data = {
            "alert": {
                "title": "Test Alert"
                # Missing id, type, severity, etc.
            }
        }
        
        message = create_alert_message(minimal_data)
        assert "blocks" in message
        
        # Should handle missing fields gracefully
        header_found = False
        for block in message["blocks"]:
            if block.get("type") == "header":
                header_found = True
        
        assert header_found, "Header not found or doesn't handle missing fields"
    
    def test_malformed_timestamps(self):
        """Test templates handle malformed timestamps."""
        data = {
            "alert": {
                "id": "ALERT-010",
                "title": "Timestamp Test",
                "created_at": "invalid-timestamp",
                "sla_breach_time": "also-invalid"
            }
        }
        
        # Should not raise exception
        message = create_alert_message(data)
        assert "blocks" in message
    
    def test_unknown_alert_type(self):
        """Test handling of unknown alert types."""
        data = {
            "alert": {
                "id": "ALERT-011",
                "type": "unknown_type",
                "title": "Unknown Alert Type",
                "severity": "medium"
            }
        }
        
        message = create_alert_message(data)
        assert "blocks" in message
        
        # Should use base template for unknown types
        header_found = False
        for block in message["blocks"]:
            if block.get("type") == "header":
                header_found = True
        
        assert header_found, "Base template not used for unknown alert type"


if __name__ == "__main__":
    # Run some basic tests
    print("Testing Alert Templates...")
    
    # Test build failure
    build_data = {
        "alert": {
            "id": "ALERT-001",
            "type": "build_failure",
            "severity": "high",
            "title": "Production Build Failing",
            "description": "Main branch build failing due to test failures",
            "affected_systems": ["CI/CD"],
            "impact": "Blocks deployments"
        },
        "build_info": {
            "branch": "main",
            "commit": "abc123"
        }
    }
    
    build_message = create_build_failure_alert(build_data)
    print(f"Build failure template created with {len(build_message['blocks'])} blocks")
    
    # Test all alert types
    alert_types = [
        ("build_failure", "Build Failure"),
        ("deployment_issue", "Deployment Issue"),
        ("security_vulnerability", "Security Vulnerability"),
        ("service_outage", "Service Outage"),
        ("critical_bug", "Critical Bug"),
        ("team_blocker", "Team Blocker"),
        ("dependency_issue", "Dependency Issue")
    ]
    
    for alert_type, description in alert_types:
        test_data = {
            "alert": {
                "id": f"ALERT-{hash(alert_type) % 1000}",
                "type": alert_type,
                "severity": "high",
                "title": f"Test {description}",
                "description": f"Test {description} alert",
                "affected_systems": ["Test System"],
                "impact": "Test impact"
            }
        }
        
        message = create_alert_message(test_data)
        print(f"{description} template created with {len(message['blocks'])} blocks")
    
    print("All alert templates created successfully!")