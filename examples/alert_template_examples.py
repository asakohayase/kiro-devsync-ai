"""
Example usage of alert message templates for DevSync AI.
Demonstrates how to create and send different types of urgent notifications.
"""

import json
from datetime import datetime, timedelta
from devsync_ai.services.alert_templates import (
    create_alert_message,
    create_build_failure_alert,
    create_deployment_issue_alert,
    create_security_vulnerability_alert,
    create_service_outage_alert,
    create_critical_bug_alert,
    create_team_blocker_alert,
    create_dependency_issue_alert
)


def example_build_failure_alert():
    """Example build failure alert notification."""
    print("=== Build Failure Alert Example ===")
    
    data = {
        "alert": {
            "id": "ALERT-BF-001",
            "type": "build_failure",
            "severity": "high",
            "title": "Production Build Pipeline Failing",
            "description": "Main branch build has been failing for 15 minutes due to unit test failures in the authentication module. This is blocking all deployments to production.",
            "affected_systems": ["CI/CD Pipeline", "Production Deployment", "Staging Environment"],
            "impact": "All deployments blocked, development team cannot merge PRs",
            "created_at": datetime.now().isoformat() + "Z",
            "assigned_to": "devops-team",
            "escalation_contacts": ["devops-lead@company.com", "engineering-manager@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(hours=1, minutes=30)).isoformat() + "Z",
            "resolution_steps": [
                "Check CI/CD logs for specific test failures",
                "Identify failing tests in authentication module",
                "Fix failing tests or temporarily skip if non-critical",
                "Re-run pipeline to verify fix",
                "Monitor subsequent builds for stability"
            ],
            "related_pr": 1247,
            "related_tickets": ["DEVSYNC-789", "DEVSYNC-790"]
        },
        "build_info": {
            "branch": "main",
            "commit": "a1b2c3d4e5f6",
            "pipeline_url": "https://ci.company.com/pipeline/main/build/1247",
            "failed_stage": "unit-tests",
            "failure_count": 3
        }
    }
    
    message = create_build_failure_alert(data)
    print(json.dumps(message, indent=2))
    return message


def example_deployment_issue_alert():
    """Example deployment issue alert notification."""
    print("\n=== Deployment Issue Alert Example ===")
    
    data = {
        "alert": {
            "id": "ALERT-DI-002",
            "type": "deployment_issue",
            "severity": "critical",
            "title": "Production Deployment Failed - Service Degraded",
            "description": "Deployment of v2.3.1 to production failed during database migration step. Some services are experiencing degraded performance and new features are unavailable.",
            "affected_systems": ["Production Environment", "User Service", "Payment Processing", "Database"],
            "impact": "50% of users experiencing slow response times, new payment features unavailable",
            "created_at": datetime.now().isoformat() + "Z",
            "assigned_to": "sre-team",
            "escalation_contacts": ["sre-lead@company.com", "cto@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(minutes=45)).isoformat() + "Z",
            "resolution_steps": [
                "Assess current system health and user impact",
                "Determine if rollback is safe and necessary",
                "Execute rollback to previous stable version",
                "Verify all services are functioning normally",
                "Investigate migration failure for future fix"
            ],
            "related_pr": 1248,
            "related_tickets": ["DEVSYNC-801", "DEVSYNC-802"]
        },
        "deployment_info": {
            "environment": "production",
            "version": "v2.3.1",
            "previous_version": "v2.3.0",
            "rollback_available": True,
            "deployment_url": "https://deploy.company.com/production/v2.3.1",
            "health_check_url": "https://health.company.com/production"
        }
    }
    
    message = create_deployment_issue_alert(data)
    print(json.dumps(message, indent=2))
    return message


def example_security_vulnerability_alert():
    """Example security vulnerability alert notification."""
    print("\n=== Security Vulnerability Alert Example ===")
    
    data = {
        "alert": {
            "id": "ALERT-SV-003",
            "type": "security_vulnerability",
            "severity": "critical",
            "title": "Critical SQL Injection Vulnerability Detected",
            "description": "Automated security scan detected a critical SQL injection vulnerability in the user authentication endpoint. This could allow attackers to access sensitive user data including passwords and personal information.",
            "affected_systems": ["User Authentication API", "User Database", "Session Management"],
            "impact": "Potential unauthorized access to all user accounts and sensitive data",
            "created_at": datetime.now().isoformat() + "Z",
            "assigned_to": "security-team",
            "escalation_contacts": ["security-lead@company.com", "ciso@company.com", "cto@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(hours=2)).isoformat() + "Z",
            "resolution_steps": [
                "Immediately disable affected authentication endpoint",
                "Implement emergency patch for SQL injection vulnerability",
                "Conduct security audit of related code",
                "Review access logs for potential exploitation",
                "Implement additional input validation and parameterized queries"
            ],
            "related_pr": 1249,
            "related_tickets": ["SEC-101", "SEC-102"]
        },
        "security_info": {
            "cve_id": "CVE-2025-12345",
            "cvss_score": 9.8,
            "attack_vector": "Network",
            "attack_complexity": "Low",
            "privileges_required": "None",
            "user_interaction": "None",
            "scope": "Changed",
            "confidentiality_impact": "High",
            "integrity_impact": "High",
            "availability_impact": "High"
        }
    }
    
    message = create_security_vulnerability_alert(data)
    print(json.dumps(message, indent=2))
    return message


def example_service_outage_alert():
    """Example service outage alert notification."""
    print("\n=== Service Outage Alert Example ===")
    
    data = {
        "alert": {
            "id": "ALERT-SO-004",
            "type": "service_outage",
            "severity": "critical",
            "title": "Complete API Service Outage",
            "description": "All API services are completely down due to database connection failures. Users cannot access the application, make payments, or perform any actions. This is a complete service outage affecting all customers.",
            "affected_systems": ["API Gateway", "User Service", "Payment Service", "Notification Service", "Database Cluster"],
            "impact": "100% service unavailability - all 75,000 active users affected",
            "created_at": datetime.now().isoformat() + "Z",
            "assigned_to": "sre-team",
            "escalation_contacts": ["sre-lead@company.com", "cto@company.com", "ceo@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(minutes=30)).isoformat() + "Z",
            "resolution_steps": [
                "Activate incident response team and war room",
                "Investigate database cluster connectivity issues",
                "Attempt database cluster restart if safe",
                "Failover to backup database cluster if necessary",
                "Update status page and notify customers",
                "Monitor service restoration and user traffic"
            ],
            "related_tickets": ["INC-501", "INC-502"]
        },
        "outage_info": {
            "services": ["API Gateway", "User Authentication", "Payment Processing", "Mobile App Backend", "Web Application"],
            "users_affected": 75000,
            "status_page": "https://status.company.com",
            "monitoring_dashboard": "https://monitoring.company.com/outage",
            "estimated_revenue_impact": "$50,000/hour"
        }
    }
    
    message = create_service_outage_alert(data)
    print(json.dumps(message, indent=2))
    return message


def example_critical_bug_alert():
    """Example critical bug alert notification."""
    print("\n=== Critical Bug Alert Example ===")
    
    data = {
        "alert": {
            "id": "ALERT-CB-005",
            "type": "critical_bug",
            "severity": "critical",
            "title": "Data Corruption Bug in Payment Processing",
            "description": "Critical bug discovered in payment processing system causing transaction amounts to be incorrectly calculated. Some customers have been overcharged while others have been undercharged. Financial reconciliation is required.",
            "affected_systems": ["Payment Processing", "Transaction Database", "Billing System", "Financial Reporting"],
            "impact": "Incorrect payment amounts affecting ~500 transactions in the last 2 hours",
            "created_at": datetime.now().isoformat() + "Z",
            "assigned_to": "payments-team",
            "escalation_contacts": ["payments-lead@company.com", "finance-director@company.com", "cto@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(hours=1)).isoformat() + "Z",
            "resolution_steps": [
                "Immediately disable payment processing to prevent further issues",
                "Identify all affected transactions in the last 24 hours",
                "Calculate correct amounts for each affected transaction",
                "Prepare refund/charge adjustments for affected customers",
                "Fix the calculation bug in payment processing code",
                "Implement additional validation before re-enabling payments"
            ],
            "related_pr": 1250,
            "related_tickets": ["PAY-301", "PAY-302", "FIN-101"]
        }
    }
    
    message = create_critical_bug_alert(data)
    print(json.dumps(message, indent=2))
    return message


def example_team_blocker_alert():
    """Example team blocker alert notification."""
    print("\n=== Team Blocker Alert Example ===")
    
    data = {
        "alert": {
            "id": "ALERT-TB-006",
            "type": "team_blocker",
            "severity": "high",
            "title": "Development Team Blocked - Critical Infrastructure Down",
            "description": "The entire development team is blocked due to critical development infrastructure being down. Docker registry, CI/CD systems, and development databases are all inaccessible. No development work can proceed.",
            "affected_systems": ["Docker Registry", "CI/CD Pipeline", "Development Databases", "Code Repository Access", "Development Environment"],
            "impact": "15 developers unable to work, all development and testing halted",
            "created_at": datetime.now().isoformat() + "Z",
            "assigned_to": "devops-team",
            "escalation_contacts": ["devops-lead@company.com", "engineering-manager@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(hours=2)).isoformat() + "Z",
            "resolution_steps": [
                "Assess status of all development infrastructure components",
                "Prioritize restoration of most critical systems first",
                "Restore Docker registry and container access",
                "Bring CI/CD systems back online",
                "Verify development database connectivity",
                "Test full development workflow before declaring resolved"
            ],
            "related_tickets": ["INFRA-201", "INFRA-202"]
        }
    }
    
    message = create_team_blocker_alert(data)
    print(json.dumps(message, indent=2))
    return message


def example_dependency_issue_alert():
    """Example dependency issue alert notification."""
    print("\n=== Dependency Issue Alert Example ===")
    
    data = {
        "alert": {
            "id": "ALERT-DI-007",
            "type": "dependency_issue",
            "severity": "high",
            "title": "Critical Third-Party Service Outage",
            "description": "Our primary email service provider (SendGrid) is experiencing a complete outage. All transactional emails including user registrations, password resets, and payment confirmations are failing. Customer support is receiving complaints about missing emails.",
            "affected_systems": ["Email Service", "User Registration", "Password Reset", "Payment Notifications", "Marketing Emails"],
            "impact": "All email functionality down, affecting user onboarding and critical notifications",
            "created_at": datetime.now().isoformat() + "Z",
            "assigned_to": "backend-team",
            "escalation_contacts": ["backend-lead@company.com", "customer-success@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(hours=3)).isoformat() + "Z",
            "resolution_steps": [
                "Check SendGrid status page for outage information",
                "Activate backup email service provider (AWS SES)",
                "Update email service configuration to use backup provider",
                "Test critical email flows with backup service",
                "Queue failed emails for retry once service is restored",
                "Monitor email delivery rates and customer complaints"
            ],
            "related_tickets": ["EMAIL-101", "EMAIL-102"]
        }
    }
    
    message = create_dependency_issue_alert(data)
    print(json.dumps(message, indent=2))
    return message


def example_escalation_scenario():
    """Example of alert escalation scenario."""
    print("\n=== Alert Escalation Scenario Example ===")
    
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
    
    # Escalated to high severity
    escalated_data = {
        "alert": {
            "id": "ALERT-ESC-001",
            "type": "service_outage", 
            "severity": "high",
            "title": "API Timeouts Increasing - Service Degradation",
            "description": "API timeout rate has increased to 25% and is continuing to climb. Multiple customer complaints received.",
            "affected_systems": ["API Gateway", "User Service", "Payment Service"],
            "impact": "25% of requests failing, customer complaints increasing",
            "created_at": (datetime.now() - timedelta(minutes=30)).isoformat() + "Z",
            "assigned_to": "sre-team",
            "escalation_contacts": ["sre-lead@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(minutes=30)).isoformat() + "Z"
        }
    }
    
    # Final escalation to critical
    critical_data = {
        "alert": {
            "id": "ALERT-ESC-001",
            "type": "service_outage",
            "severity": "critical", 
            "title": "CRITICAL: Complete API Service Failure",
            "description": "API services have completely failed. 100% of requests are timing out or returning errors. This is now a complete service outage.",
            "affected_systems": ["API Gateway", "All Backend Services", "Database Connections"],
            "impact": "Complete service outage - all users affected",
            "created_at": (datetime.now() - timedelta(minutes=30)).isoformat() + "Z",
            "assigned_to": "sre-team",
            "escalation_contacts": ["sre-lead@company.com", "cto@company.com", "ceo@company.com"],
            "sla_breach_time": (datetime.now() + timedelta(minutes=15)).isoformat() + "Z"
        },
        "outage_info": {
            "services": ["All API Services"],
            "users_affected": 50000,
            "status_page": "https://status.company.com"
        }
    }
    
    print("Initial Alert (Medium Severity):")
    initial_message = create_alert_message(initial_data)
    print(f"Blocks: {len(initial_message['blocks'])}")
    
    print("\nEscalated Alert (High Severity):")
    escalated_message = create_alert_message(escalated_data)
    print(f"Blocks: {len(escalated_message['blocks'])}")
    
    print("\nCritical Escalation:")
    critical_message = create_alert_message(critical_data)
    print(f"Blocks: {len(critical_message['blocks'])}")
    
    return [initial_message, escalated_message, critical_message]


def example_batch_alert_notifications():
    """Example of creating multiple alert notifications."""
    print("\n=== Batch Alert Notifications Example ===")
    
    notifications = []
    
    # Build failure
    build_failure = example_build_failure_alert()
    notifications.append(("build_failure", build_failure))
    
    # Deployment issue
    deployment_issue = example_deployment_issue_alert()
    notifications.append(("deployment_issue", deployment_issue))
    
    # Security vulnerability
    security_vuln = example_security_vulnerability_alert()
    notifications.append(("security_vulnerability", security_vuln))
    
    # Service outage
    service_outage = example_service_outage_alert()
    notifications.append(("service_outage", service_outage))
    
    # Critical bug
    critical_bug = example_critical_bug_alert()
    notifications.append(("critical_bug", critical_bug))
    
    # Team blocker
    team_blocker = example_team_blocker_alert()
    notifications.append(("team_blocker", team_blocker))
    
    # Dependency issue
    dependency_issue = example_dependency_issue_alert()
    notifications.append(("dependency_issue", dependency_issue))
    
    print(f"\nGenerated {len(notifications)} alert notifications")
    return notifications


def example_webhook_integration():
    """Example of webhook integration for monitoring alerts."""
    print("\n=== Alert Webhook Integration Example ===")
    
    # Simulate monitoring system webhook payload
    webhook_payload = {
        "alert_name": "High CPU Usage",
        "status": "firing",
        "severity": "high",
        "instance": "web-server-01",
        "value": "95%",
        "threshold": "80%",
        "duration": "5m",
        "timestamp": datetime.now().isoformat() + "Z",
        "runbook_url": "https://runbooks.company.com/high-cpu",
        "dashboard_url": "https://monitoring.company.com/cpu"
    }
    
    # Convert monitoring webhook to alert template format
    def convert_monitoring_webhook_to_alert(payload):
        """Convert monitoring webhook to alert template format."""
        severity_map = {
            "critical": "critical",
            "warning": "high", 
            "info": "medium"
        }
        
        alert_data = {
            "alert": {
                "id": f"MON-{hash(payload['alert_name']) % 10000}",
                "type": "service_outage" if "outage" in payload['alert_name'].lower() else "critical_bug",
                "severity": severity_map.get(payload.get('severity', 'medium'), 'medium'),
                "title": f"Monitoring Alert: {payload['alert_name']}",
                "description": f"Alert triggered on {payload.get('instance', 'unknown')} - {payload['alert_name']} is {payload.get('value', 'unknown')} (threshold: {payload.get('threshold', 'unknown')})",
                "affected_systems": [payload.get('instance', 'Unknown System')],
                "impact": f"System performance degraded - {payload['alert_name']} at {payload.get('value', 'unknown')}",
                "created_at": payload.get('timestamp', datetime.now().isoformat() + "Z"),
                "assigned_to": "sre-team",
                "resolution_steps": [
                    f"Check {payload.get('instance', 'system')} resource usage",
                    f"Review {payload['alert_name']} metrics in monitoring dashboard",
                    "Identify root cause of resource spike",
                    "Take corrective action to reduce resource usage"
                ]
            }
        }
        
        return alert_data
    
    # Convert and create alert
    alert_data = convert_monitoring_webhook_to_alert(webhook_payload)
    message = create_alert_message(alert_data)
    
    print("Monitoring webhook payload:")
    print(json.dumps(webhook_payload, indent=2))
    print("\nConverted to alert template:")
    print(json.dumps(alert_data, indent=2))
    print(f"\nGenerated alert message with {len(message['blocks'])} blocks")
    
    return message


if __name__ == "__main__":
    print("DevSync AI Alert Template Examples")
    print("=" * 50)
    
    # Run all examples
    example_build_failure_alert()
    example_deployment_issue_alert()
    example_security_vulnerability_alert()
    example_service_outage_alert()
    example_critical_bug_alert()
    example_team_blocker_alert()
    example_dependency_issue_alert()
    example_webhook_integration()
    
    # Generate escalation scenario
    escalation = example_escalation_scenario()
    
    # Generate batch notifications
    batch = example_batch_alert_notifications()
    
    print("\n" + "=" * 50)
    print("All alert examples completed successfully!")
    print(f"Total messages generated: {len(batch) + len(escalation) + 1}")  # +1 for webhook example