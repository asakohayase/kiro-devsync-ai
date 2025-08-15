"""
Integration Examples
Demonstrates how to integrate the Slack Message Templates system with various services.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from devsync_ai.core.template_factory import MessageTemplateFactory
from devsync_ai.core.message_formatter import TemplateConfig, SlackMessage
from devsync_ai.services.slack import SlackClient


@dataclass
class WebhookEvent:
    """Represents an incoming webhook event."""
    source: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class GitHubIntegrationExample:
    """Example integration with GitHub webhooks."""
    
    def __init__(self, template_factory: MessageTemplateFactory):
        self.factory = template_factory
        self.event_mappings = {
            "pull_request.opened": "pr_opened",
            "pull_request.closed": "pr_closed",
            "pull_request.merged": "pr_merged",
            "pull_request.ready_for_review": "pr_ready_for_review",
            "pull_request.review_requested": "pr_review_requested",
            "pull_request.approved": "pr_approved",
            "pull_request.changes_requested": "pr_changes_requested",
            "push": "push_notification",
            "release.published": "release_notification"
        }
    
    def process_webhook(self, webhook_data: Dict[str, Any]) -> Optional[SlackMessage]:
        """Process GitHub webhook and generate Slack message."""
        action = webhook_data.get("action")
        event_type = f"pull_request.{action}" if "pull_request" in webhook_data else webhook_data.get("ref_type", "push")
        
        template_type = self.event_mappings.get(event_type)
        if not template_type:
            print(f"No template mapping for event: {event_type}")
            return None
        
        # Transform GitHub data to template format
        template_data = self._transform_github_data(webhook_data, event_type)
        
        try:
            template = self.factory.create_template(template_type)
            return template.format_message(template_data)
        except Exception as e:
            print(f"Failed to process GitHub webhook: {e}")
            return None
    
    def _transform_github_data(self, webhook_data: Dict[str, Any], event_type: str) -> Dict[str, Any]:
        """Transform GitHub webhook data to template format."""
        if event_type.startswith("pull_request"):
            pr_data = webhook_data.get("pull_request", {})
            return {
                "pr": {
                    "number": pr_data.get("number"),
                    "title": pr_data.get("title"),
                    "description": pr_data.get("body", ""),
                    "author": pr_data.get("user", {}).get("login"),
                    "url": pr_data.get("html_url"),
                    "status": pr_data.get("state"),
                    "draft": pr_data.get("draft", False),
                    "reviewers": [r["login"] for r in pr_data.get("requested_reviewers", [])],
                    "files_changed": pr_data.get("changed_files", 0),
                    "additions": pr_data.get("additions", 0),
                    "deletions": pr_data.get("deletions", 0),
                    "created_at": pr_data.get("created_at"),
                    "updated_at": pr_data.get("updated_at"),
                    "mergeable": pr_data.get("mergeable"),
                    "base_branch": pr_data.get("base", {}).get("ref"),
                    "head_branch": pr_data.get("head", {}).get("ref")
                },
                "action": webhook_data.get("action"),
                "repository": {
                    "name": webhook_data.get("repository", {}).get("name"),
                    "url": webhook_data.get("repository", {}).get("html_url")
                }
            }
        
        return webhook_data


class JiraIntegrationExample:
    """Example integration with Jira webhooks."""
    
    def __init__(self, template_factory: MessageTemplateFactory):
        self.factory = template_factory
        self.event_mappings = {
            "jira:issue_created": "jira_created",
            "jira:issue_updated": "jira_updated",
            "jira:issue_deleted": "jira_deleted",
            "comment_created": "jira_comment_added",
            "comment_updated": "jira_comment_updated"
        }
    
    def process_webhook(self, webhook_data: Dict[str, Any]) -> Optional[SlackMessage]:
        """Process Jira webhook and generate Slack message."""
        webhook_event = webhook_data.get("webhookEvent")
        
        template_type = self.event_mappings.get(webhook_event)
        if not template_type:
            print(f"No template mapping for Jira event: {webhook_event}")
            return None
        
        # Transform Jira data to template format
        template_data = self._transform_jira_data(webhook_data, webhook_event)
        
        try:
            # Determine specific template based on change type
            if webhook_event == "jira:issue_updated":
                change_type = self._determine_change_type(webhook_data)
                template_type = f"jira_{change_type}"
            
            template = self.factory.create_template(template_type)
            return template.format_message(template_data)
        except Exception as e:
            print(f"Failed to process Jira webhook: {e}")
            return None
    
    def _transform_jira_data(self, webhook_data: Dict[str, Any], event_type: str) -> Dict[str, Any]:
        """Transform Jira webhook data to template format."""
        issue = webhook_data.get("issue", {})
        fields = issue.get("fields", {})
        
        template_data = {
            "ticket": {
                "key": issue.get("key"),
                "summary": fields.get("summary"),
                "description": fields.get("description"),
                "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
                "status": fields.get("status", {}).get("name") if fields.get("status") else None,
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                "reporter": fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None,
                "created": fields.get("created"),
                "updated": fields.get("updated"),
                "url": f"{webhook_data.get('issue', {}).get('self', '').split('/rest')[0]}/browse/{issue.get('key')}"
            },
            "change_type": self._determine_change_type(webhook_data),
            "changed_by": webhook_data.get("user", {}).get("displayName")
        }
        
        # Add change-specific data
        if event_type == "comment_created":
            comment = webhook_data.get("comment", {})
            template_data["ticket"]["comments"] = [{
                "author": comment.get("author", {}).get("displayName"),
                "text": comment.get("body"),
                "created": comment.get("created")
            }]
        
        return template_data
    
    def _determine_change_type(self, webhook_data: Dict[str, Any]) -> str:
        """Determine the type of change from Jira webhook data."""
        changelog = webhook_data.get("changelog", {})
        items = changelog.get("items", [])
        
        for item in items:
            field = item.get("field")
            if field == "status":
                return "status_change"
            elif field == "priority":
                return "priority_change"
            elif field == "assignee":
                return "assignment_change"
        
        return "updated"


class CIIntegrationExample:
    """Example integration with CI/CD systems."""
    
    def __init__(self, template_factory: MessageTemplateFactory):
        self.factory = template_factory
        self.event_mappings = {
            "build.started": "build_started",
            "build.completed": "build_completed",
            "build.failed": "build_failure",
            "deployment.started": "deployment_started",
            "deployment.completed": "deployment_completed",
            "deployment.failed": "deployment_issue",
            "test.failed": "test_failure"
        }
    
    def process_ci_event(self, ci_data: Dict[str, Any]) -> Optional[SlackMessage]:
        """Process CI/CD event and generate Slack message."""
        event_type = ci_data.get("event_type")
        
        template_type = self.event_mappings.get(event_type)
        if not template_type:
            print(f"No template mapping for CI event: {event_type}")
            return None
        
        # Transform CI data to template format
        template_data = self._transform_ci_data(ci_data, event_type)
        
        try:
            template = self.factory.create_template(template_type)
            return template.format_message(template_data)
        except Exception as e:
            print(f"Failed to process CI event: {e}")
            return None
    
    def _transform_ci_data(self, ci_data: Dict[str, Any], event_type: str) -> Dict[str, Any]:
        """Transform CI data to template format."""
        if event_type.startswith("build"):
            return {
                "alert": {
                    "id": ci_data.get("build_id"),
                    "type": "build_failure" if "failed" in event_type else "build_info",
                    "severity": "high" if "failed" in event_type else "info",
                    "title": f"Build {ci_data.get('status', 'unknown')}",
                    "description": ci_data.get("message", ""),
                    "created_at": ci_data.get("timestamp")
                },
                "build_info": {
                    "branch": ci_data.get("branch"),
                    "commit": ci_data.get("commit_sha"),
                    "pipeline_url": ci_data.get("build_url"),
                    "duration": ci_data.get("duration"),
                    "failed_tests": ci_data.get("failed_tests", [])
                }
            }
        
        elif event_type.startswith("deployment"):
            return {
                "alert": {
                    "id": ci_data.get("deployment_id"),
                    "type": "deployment_issue" if "failed" in event_type else "deployment_info",
                    "severity": "critical" if "failed" in event_type else "info",
                    "title": f"Deployment {ci_data.get('status', 'unknown')}",
                    "description": ci_data.get("message", ""),
                    "created_at": ci_data.get("timestamp")
                },
                "deployment_info": {
                    "environment": ci_data.get("environment"),
                    "version": ci_data.get("version"),
                    "rollback_available": ci_data.get("rollback_available", False),
                    "deployment_url": ci_data.get("deployment_url")
                }
            }
        
        return ci_data


class MonitoringIntegrationExample:
    """Example integration with monitoring systems."""
    
    def __init__(self, template_factory: MessageTemplateFactory):
        self.factory = template_factory
        self.severity_mapping = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
            "warning": "medium",
            "error": "high"
        }
    
    def process_alert(self, alert_data: Dict[str, Any]) -> Optional[SlackMessage]:
        """Process monitoring alert and generate Slack message."""
        alert_type = self._determine_alert_type(alert_data)
        
        # Transform monitoring data to template format
        template_data = self._transform_monitoring_data(alert_data, alert_type)
        
        try:
            template = self.factory.create_template(alert_type)
            return template.format_message(template_data)
        except Exception as e:
            print(f"Failed to process monitoring alert: {e}")
            return None
    
    def _determine_alert_type(self, alert_data: Dict[str, Any]) -> str:
        """Determine alert template type from monitoring data."""
        alert_name = alert_data.get("alertname", "").lower()
        
        if "service" in alert_name and "down" in alert_name:
            return "service_outage"
        elif "high_error_rate" in alert_name:
            return "error_rate_alert"
        elif "disk" in alert_name or "memory" in alert_name or "cpu" in alert_name:
            return "resource_alert"
        elif "security" in alert_name or "vulnerability" in alert_name:
            return "security_vulnerability"
        else:
            return "generic_alert"
    
    def _transform_monitoring_data(self, alert_data: Dict[str, Any], alert_type: str) -> Dict[str, Any]:
        """Transform monitoring data to template format."""
        return {
            "alert": {
                "id": alert_data.get("fingerprint", f"ALERT-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                "type": alert_type,
                "severity": self.severity_mapping.get(alert_data.get("severity", "medium").lower(), "medium"),
                "title": alert_data.get("alertname", "Unknown Alert"),
                "description": alert_data.get("description", alert_data.get("summary", "")),
                "created_at": alert_data.get("startsAt", datetime.now().isoformat()),
                "affected_systems": [alert_data.get("instance", "unknown")],
                "labels": alert_data.get("labels", {}),
                "annotations": alert_data.get("annotations", {})
            }
        }


class SlackIntegrationOrchestrator:
    """Orchestrates all integrations and manages Slack message delivery."""
    
    def __init__(self, slack_client: SlackClient, template_factory: MessageTemplateFactory):
        self.slack_client = slack_client
        self.factory = template_factory
        
        # Initialize integration handlers
        self.github_integration = GitHubIntegrationExample(template_factory)
        self.jira_integration = JiraIntegrationExample(template_factory)
        self.ci_integration = CIIntegrationExample(template_factory)
        self.monitoring_integration = MonitoringIntegrationExample(template_factory)
        
        # Channel routing configuration
        self.channel_routing = {
            "github": "#dev-notifications",
            "jira": "#project-updates",
            "ci": "#build-notifications",
            "monitoring": "#alerts",
            "default": "#general"
        }
        
        # Message batching configuration
        self.batch_config = {
            "enabled": True,
            "batch_size": 10,
            "batch_timeout": 300,  # 5 minutes
            "batch_by_channel": True
        }
        
        self.message_queue = []
        self.last_batch_time = datetime.now()
    
    async def process_webhook_event(self, event: WebhookEvent) -> bool:
        """Process incoming webhook event and route to appropriate handler."""
        message = None
        
        try:
            if event.source == "github":
                message = self.github_integration.process_webhook(event.data)
            elif event.source == "jira":
                message = self.jira_integration.process_webhook(event.data)
            elif event.source == "ci":
                message = self.ci_integration.process_ci_event(event.data)
            elif event.source == "monitoring":
                message = self.monitoring_integration.process_alert(event.data)
            else:
                print(f"Unknown event source: {event.source}")
                return False
            
            if message:
                channel = self.channel_routing.get(event.source, self.channel_routing["default"])
                await self._queue_message(message, channel, event)
                return True
            
        except Exception as e:
            print(f"Failed to process webhook event: {e}")
            return False
        
        return False
    
    async def _queue_message(self, message: SlackMessage, channel: str, event: WebhookEvent):
        """Queue message for batching or send immediately."""
        if self.batch_config["enabled"]:
            self.message_queue.append({
                "message": message,
                "channel": channel,
                "event": event,
                "timestamp": datetime.now()
            })
            
            # Check if we should send batch
            if (len(self.message_queue) >= self.batch_config["batch_size"] or
                (datetime.now() - self.last_batch_time).seconds >= self.batch_config["batch_timeout"]):
                await self._send_batched_messages()
        else:
            await self._send_message(message, channel)
    
    async def _send_batched_messages(self):
        """Send queued messages in batches."""
        if not self.message_queue:
            return
        
        # Group by channel if configured
        if self.batch_config["batch_by_channel"]:
            channel_groups = {}
            for item in self.message_queue:
                channel = item["channel"]
                if channel not in channel_groups:
                    channel_groups[channel] = []
                channel_groups[channel].append(item)
            
            # Send each channel's messages
            for channel, items in channel_groups.items():
                for item in items:
                    await self._send_message(item["message"], channel)
        else:
            # Send all messages
            for item in self.message_queue:
                await self._send_message(item["message"], item["channel"])
        
        # Clear queue and update timestamp
        self.message_queue.clear()
        self.last_batch_time = datetime.now()
    
    async def _send_message(self, message: SlackMessage, channel: str):
        """Send message to Slack."""
        try:
            response = await self.slack_client.send_message(
                channel=channel,
                blocks=message.blocks,
                text=message.text,
                thread_ts=message.thread_ts
            )
            print(f"✅ Message sent to {channel}: {response.get('ts')}")
        except Exception as e:
            print(f"❌ Failed to send message to {channel}: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all integrations."""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "integrations": {},
            "queue_size": len(self.message_queue),
            "last_batch_time": self.last_batch_time.isoformat()
        }
        
        # Check each integration
        integrations = {
            "github": self.github_integration,
            "jira": self.jira_integration,
            "ci": self.ci_integration,
            "monitoring": self.monitoring_integration
        }
        
        for name, integration in integrations.items():
            try:
                # Simple health check - try to create a template
                template = self.factory.create_template("generic_alert")
                health_status["integrations"][name] = {
                    "status": "healthy",
                    "last_check": datetime.now().isoformat()
                }
            except Exception as e:
                health_status["integrations"][name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "last_check": datetime.now().isoformat()
                }
                health_status["overall_status"] = "degraded"
        
        return health_status


async def demonstrate_integration_examples():
    """Demonstrate the integration examples."""
    print("=== INTEGRATION EXAMPLES ===\n")
    
    # Setup
    config = TemplateConfig(
        team_id="integration_demo",
        branding={"team_name": "Integration Demo Team", "logo_emoji": "🔗"},
        interactive_elements=True
    )
    
    factory = MessageTemplateFactory(config=config)
    slack_client = SlackClient()  # Mock client for demo
    orchestrator = SlackIntegrationOrchestrator(slack_client, factory)
    
    # Example webhook events
    events = [
        WebhookEvent(
            source="github",
            event_type="pull_request.opened",
            timestamp=datetime.now(),
            data={
                "action": "opened",
                "pull_request": {
                    "number": 123,
                    "title": "Add new feature",
                    "body": "This PR adds a new feature to the application.",
                    "user": {"login": "developer1"},
                    "html_url": "https://github.com/company/repo/pull/123",
                    "state": "open",
                    "draft": False,
                    "changed_files": 5,
                    "additions": 150,
                    "deletions": 20,
                    "created_at": "2025-08-14T10:00:00Z",
                    "base": {"ref": "main"},
                    "head": {"ref": "feature/new-feature"}
                },
                "repository": {
                    "name": "company-repo",
                    "html_url": "https://github.com/company/repo"
                }
            }
        ),
        
        WebhookEvent(
            source="jira",
            event_type="jira:issue_updated",
            timestamp=datetime.now(),
            data={
                "webhookEvent": "jira:issue_updated",
                "issue": {
                    "key": "PROJ-456",
                    "fields": {
                        "summary": "Fix critical bug",
                        "description": "This bug is causing issues in production.",
                        "priority": {"name": "High"},
                        "status": {"name": "In Progress"},
                        "assignee": {"displayName": "Alice Johnson"},
                        "reporter": {"displayName": "Bob Smith"},
                        "created": "2025-08-14T09:00:00Z",
                        "updated": "2025-08-14T10:30:00Z"
                    }
                },
                "changelog": {
                    "items": [
                        {
                            "field": "status",
                            "fromString": "To Do",
                            "toString": "In Progress"
                        }
                    ]
                },
                "user": {"displayName": "Alice Johnson"}
            }
        ),
        
        WebhookEvent(
            source="ci",
            event_type="build.failed",
            timestamp=datetime.now(),
            data={
                "event_type": "build.failed",
                "build_id": "BUILD-789",
                "status": "failed",
                "message": "Build failed due to test failures",
                "branch": "main",
                "commit_sha": "a1b2c3d4e5f6",
                "build_url": "https://ci.company.com/build/789",
                "duration": "5m 32s",
                "failed_tests": ["test_authentication", "test_payment_processing"],
                "timestamp": "2025-08-14T11:00:00Z"
            }
        ),
        
        WebhookEvent(
            source="monitoring",
            event_type="alert.triggered",
            timestamp=datetime.now(),
            data={
                "alertname": "ServiceDown",
                "severity": "critical",
                "description": "API service is not responding",
                "summary": "API service health check failed",
                "instance": "api-server-01",
                "startsAt": "2025-08-14T11:15:00Z",
                "labels": {
                    "service": "api",
                    "environment": "production",
                    "team": "backend"
                },
                "annotations": {
                    "runbook_url": "https://runbooks.company.com/api-down",
                    "dashboard_url": "https://grafana.company.com/api-dashboard"
                }
            }
        )
    ]
    
    # Process events
    print("Processing webhook events:")
    for i, event in enumerate(events, 1):
        print(f"\n{i}. Processing {event.source} event: {event.event_type}")
        success = await orchestrator.process_webhook_event(event)
        if success:
            print(f"   ✅ Event processed successfully")
        else:
            print(f"   ❌ Event processing failed")
    
    # Send any remaining batched messages
    await orchestrator._send_batched_messages()
    
    # Health check
    print("\n" + "="*50)
    print("HEALTH CHECK:")
    health_status = await orchestrator.health_check()
    print(f"Overall Status: {health_status['overall_status']}")
    print(f"Queue Size: {health_status['queue_size']}")
    
    for integration, status in health_status['integrations'].items():
        print(f"{integration}: {status['status']}")
    
    print("\n" + "="*50)
    print("✅ Integration examples completed successfully!")


if __name__ == "__main__":
    asyncio.run(demonstrate_integration_examples())