"""
Example usage of alert templates for DevSync AI.
Demonstrates how to create and format different types of urgent notifications.
"""

import json
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


def create_sample_config():
    """Create sample template configuration."""
    return TemplateConfig(
        team_id="engineering",
        branding={
            "primary_color": "#FF0000",
            "logo_emoji": "🚨",
            "team_name": "Engineering Team"
        },
        emoji_set={
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "info": "ℹ️"
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


def example_base_alert_template():
    """Example of base alert template usage."""
    print("=== Base Alert Template Example ===")
    
    config = create_sample_config()
    status_system = StatusIndicatorSystem()
    template = AlertTemplate(config, status_system)
    
    data = {
        "alert": {
            "id": "ALERT-001",
            "type": "critical_bug",
            "severity": "critical",
            "title": "Database Connection Pool Exhausted",
            "description": "All database connections are exhausted, causing application timeouts and user-facing errors.",
            "affected_systems": ["Database", "API Gateway", "User Service"],
            "impact": "Complete service unavailability for all users",
            "created_at": datetime.now().isoformat() + "Z",
            "assigned_to": "database-team",
            "escalation_contacts": ["dba-lead@company.com", "sre-team@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(minutes=30)).isoformat() + "Z"
        }
    }
    
    message = template.format_message(data)
    print(f"Generated message with {len(message.blocks)} blocks")
    print(f"Fallback text: {message.text}")
    
    return message


def example_build_failure_alert():
    """Example of build failure alert template."""
    print("\n=== Build Failure Alert Example ===")
    
    config = create_sample_config()
    template = BuildFailureTemplate(config)
    
    data = {
        "alert": {
            "id": "ALERT-BF-001",
            "type": "build_failure",
            "severity": "high",
            "title": "Production Build Pipeline Failing",
            "description": "Main branch build has been failing for 15 minutes due to unit test failures in the authentication module.",
            "affected_systems": ["CI/CD Pipeline", "Production Deployment"],
            "impact": "All deployments blocked, development team cannot merge PRs",
            "created_at": datetime.now().isoformat() + "Z",
            "assigned_to": "devops-team",
            "escalation_contacts": ["devops-lead@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(hours=1)).isoformat() + "Z"
        },
        "build_info": {
            "branch": "main",
            "commit": "a1b2c3d4e5f6789",
            "pipeline_url": "https://ci.company.com/pipeline/main/build/1247",
            "failed_stage": "unit-tests"
        }
    }
    
    message = template.format_message(data)
    print(f"Generated build failure message with {len(message.blocks)} blocks")
    
    # Print some key blocks for verification
    for i, block in enumerate(message.blocks):
        if block.get("type") == "header":
            print(f"Header: {block['text']['text']}")
        elif block.get("type") == "section" and "Build Information" in block.get("text", {}).get("text", ""):
            print(f"Build info found in block {i}")
    
    return message


def example_deployment_issue_alert():
    """Example of deployment issue alert template."""
    print("\n=== Deployment Issue Alert Example ===")
    
    config = create_sample_config()
    template = DeploymentIssueTemplate(config)
    
    data = {
        "alert": {
            "id": "ALERT-DI-002",
            "type": "deployment_issue",
            "severity": "critical",
            "title": "Production Deployment Failed - Service Degraded",
            "description": "Deployment of v2.3.1 to production failed during database migration step.",
            "affected_systems": ["Production Environment", "User Service", "Payment Processing"],
            "impact": "50% of users experiencing slow response times",
            "created_at": datetime.now().isoformat() + "Z",
            "assigned_to": "sre-team",
            "escalation_contacts": ["sre-lead@company.com", "cto@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(minutes=45)).isoformat() + "Z"
        },
        "deployment_info": {
            "environment": "production",
            "version": "v2.3.1",
            "previous_version": "v2.3.0",
            "rollback_available": True
        }
    }
    
    message = template.format_message(data)
    print(f"Generated deployment issue message with {len(message.blocks)} blocks")
    
    # Check for rollback button
    rollback_found = False
    for block in message.blocks:
        if block.get("type") == "actions":
            for element in block.get("elements", []):
                if "ROLLBACK NOW" in element.get("text", {}).get("text", ""):
                    rollback_found = True
                    print("Rollback button found")
    
    return message


def example_security_vulnerability_alert():
    """Example of security vulnerability alert template."""
    print("\n=== Security Vulnerability Alert Example ===")
    
    config = create_sample_config()
    template = SecurityVulnerabilityTemplate(config)
    
    data = {
        "alert": {
            "id": "ALERT-SV-003",
            "type": "security_vulnerability",
            "severity": "critical",
            "title": "Critical SQL Injection Vulnerability Detected",
            "description": "Automated security scan detected a critical SQL injection vulnerability in the user authentication endpoint.",
            "affected_systems": ["User Authentication API", "User Database"],
            "impact": "Potential unauthorized access to all user accounts",
            "created_at": datetime.now().isoformat() + "Z",
            "assigned_to": "security-team",
            "escalation_contacts": ["security-lead@company.com", "ciso@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(hours=2)).isoformat() + "Z"
        },
        "security_info": {
            "cve_id": "CVE-2025-12345",
            "cvss_score": 9.8,
            "attack_vector": "Network"
        }
    }
    
    message = template.format_message(data)
    print(f"Generated security vulnerability message with {len(message.blocks)} blocks")
    
    # Check for confidential warning
    confidential_found = False
    for block in message.blocks:
        if block.get("type") == "section" and block.get("text"):
            text = block["text"].get("text", "")
            if "CONFIDENTIAL" in text:
                confidential_found = True
                print("Confidential warning found")
    
    return message


def example_service_outage_alert():
    """Example of service outage alert template."""
    print("\n=== Service Outage Alert Example ===")
    
    config = create_sample_config()
    template = ServiceOutageTemplate(config)
    
    data = {
        "alert": {
            "id": "ALERT-SO-004",
            "type": "service_outage",
            "severity": "critical",
            "title": "Complete API Service Outage",
            "description": "All API services are completely down due to database connection failures.",
            "affected_systems": ["API Gateway", "User Service", "Payment Service"],
            "impact": "100% service unavailability - all 75,000 active users affected",
            "created_at": datetime.now().isoformat() + "Z",
            "assigned_to": "sre-team",
            "escalation_contacts": ["sre-lead@company.com", "cto@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(minutes=30)).isoformat() + "Z"
        },
        "outage_info": {
            "services": ["API Gateway", "User Authentication", "Payment Processing"],
            "users_affected": 75000,
            "status_page": "https://status.company.com"
        }
    }
    
    message = template.format_message(data)
    print(f"Generated service outage message with {len(message.blocks)} blocks")
    
    # Check for war room button
    war_room_found = False
    for block in message.blocks:
        if block.get("type") == "actions":
            for element in block.get("elements", []):
                if "Start War Room" in element.get("text", {}).get("text", ""):
                    war_room_found = True
                    print("War room button found")
    
    return message


def example_critical_bug_alert():
    """Example of critical bug alert template."""
    print("\n=== Critical Bug Alert Example ===")
    
    config = create_sample_config()
    template = CriticalBugTemplate(config)
    
    data = {
        "alert": {
            "id": "ALERT-CB-005",
            "type": "critical_bug",
            "severity": "critical",
            "title": "Data Corruption Bug in Payment Processing",
            "description": "Critical bug discovered in payment processing system causing transaction amounts to be incorrectly calculated.",
            "affected_systems": ["Payment Processing", "Transaction Database"],
            "impact": "Incorrect payment amounts affecting ~500 transactions",
            "created_at": datetime.now().isoformat() + "Z",
            "assigned_to": "payments-team",
            "escalation_contacts": ["payments-lead@company.com", "finance-director@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(hours=1)).isoformat() + "Z",
            "bug_info": {
                "data_affected": "~500 payment transactions in last 2 hours",
                "reproduction_steps": [
                    "Process payment with amount > $100",
                    "Check transaction record in database",
                    "Compare with actual charge amount"
                ]
            }
        }
    }
    
    message = template.format_message(data)
    print(f"Generated critical bug message with {len(message.blocks)} blocks")
    
    # Check for data integrity warning
    data_integrity_found = False
    for block in message.blocks:
        if block.get("type") == "section" and block.get("text"):
            text = block["text"].get("text", "")
            if "DATA INTEGRITY" in text:
                data_integrity_found = True
                print("Data integrity warning found")
    
    return message


def example_alert_escalation_scenario():
    """Example of alert escalation from medium to critical."""
    print("\n=== Alert Escalation Scenario Example ===")
    
    config = create_sample_config()
    
    # Initial medium severity alert
    initial_data = {
        "alert": {
            "id": "ALERT-ESC-001",
            "type": "service_outage",
            "severity": "medium",
            "title": "Intermittent API Timeouts",
            "description": "Some API endpoints experiencing occasional timeouts",
            "affected_systems": ["API Gateway"],
            "impact": "5% of requests timing out",
            "created_at": (datetime.now() - timedelta(minutes=30)).isoformat() + "Z",
            "assigned_to": "backend-team"
        }
    }
    
    # Escalated to critical
    critical_data = {
        "alert": {
            "id": "ALERT-ESC-001",
            "type": "service_outage",
            "severity": "critical",
            "title": "CRITICAL: Complete API Service Failure",
            "description": "API services have completely failed. 100% of requests are timing out.",
            "affected_systems": ["API Gateway", "All Backend Services"],
            "impact": "Complete service outage - all users affected",
            "created_at": (datetime.now() - timedelta(minutes=30)).isoformat() + "Z",
            "assigned_to": "sre-team",
            "escalation_contacts": ["sre-lead@company.com", "cto@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(minutes=15)).isoformat() + "Z"
        },
        "outage_info": {
            "services": ["All API Services"],
            "users_affected": 50000,
            "status_page": "https://status.company.com"
        }
    }
    
    # Create both messages
    base_template = AlertTemplate(config)
    outage_template = ServiceOutageTemplate(config)
    
    initial_message = base_template.format_message(initial_data)
    critical_message = outage_template.format_message(critical_data)
    
    print(f"Initial alert: {len(initial_message.blocks)} blocks")
    print(f"Escalated alert: {len(critical_message.blocks)} blocks")
    
    return [initial_message, critical_message]


def example_batch_alert_processing():
    """Example of processing multiple alerts in batch."""
    print("\n=== Batch Alert Processing Example ===")
    
    config = create_sample_config()
    
    # Create multiple alert scenarios
    alerts = [
        {
            "template": BuildFailureTemplate(config),
            "data": {
                "alert": {
                    "id": "BATCH-001",
                    "type": "build_failure",
                    "severity": "high",
                    "title": "Build Failure #1",
                    "description": "Unit tests failing"
                },
                "build_info": {
                    "branch": "feature/auth",
                    "commit": "abc123"
                }
            }
        },
        {
            "template": DeploymentIssueTemplate(config),
            "data": {
                "alert": {
                    "id": "BATCH-002",
                    "type": "deployment_issue",
                    "severity": "critical",
                    "title": "Deployment Failure #1",
                    "description": "Production deployment failed"
                },
                "deployment_info": {
                    "environment": "production",
                    "version": "v1.2.3",
                    "rollback_available": True
                }
            }
        },
        {
            "template": SecurityVulnerabilityTemplate(config),
            "data": {
                "alert": {
                    "id": "BATCH-003",
                    "type": "security_vulnerability",
                    "severity": "critical",
                    "title": "Security Issue #1",
                    "description": "XSS vulnerability detected"
                },
                "security_info": {
                    "cve_id": "CVE-2025-99999",
                    "cvss_score": 8.5
                }
            }
        }
    ]
    
    messages = []
    for alert_config in alerts:
        template = alert_config["template"]
        data = alert_config["data"]
        message = template.format_message(data)
        messages.append(message)
        print(f"Processed alert {data['alert']['id']}: {len(message.blocks)} blocks")
    
    print(f"Total alerts processed: {len(messages)}")
    return messages


if __name__ == "__main__":
    print("DevSync AI Alert Template Examples")
    print("=" * 50)
    
    # Run all examples
    example_base_alert_template()
    example_build_failure_alert()
    example_deployment_issue_alert()
    example_security_vulnerability_alert()
    example_service_outage_alert()
    example_critical_bug_alert()
    example_alert_escalation_scenario()
    example_batch_alert_processing()
    
    print("\n" + "=" * 50)
    print("All alert template examples completed successfully!")