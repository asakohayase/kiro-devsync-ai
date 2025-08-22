"""
Test utilities and mock data generators for comprehensive testing.
"""

import json
import random
import string
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from unittest.mock import AsyncMock, MagicMock
import uuid

from devsync_ai.core.agent_hooks import EnrichedEvent, EventClassification, UrgencyLevel, SignificanceLevel
from devsync_ai.models.core import JiraTicket, TeamMember


@dataclass
class TestScenario:
    """Represents a test scenario configuration."""
    name: str
    description: str
    webhook_events: List[Dict[str, Any]]
    expected_hooks: List[str]
    expected_notifications: int
    team_configs: List[Dict[str, Any]]
    success_criteria: Dict[str, Any]


@dataclass
class Stakeholder:
    """Simple stakeholder model for testing."""
    user_id: str
    name: str
    email: str
    role: str


class MockDataFactory:
    """Factory for creating mock data for testing."""
    
    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate a random string."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def random_email() -> str:
        """Generate a random email address."""
        username = MockDataFactory.random_string(8).lower()
        domain = random.choice(['example.com', 'test.org', 'demo.net'])
        return f"{username}@{domain}"
    
    @staticmethod
    def random_jira_key(project: str = None) -> str:
        """Generate a random JIRA ticket key."""
        if not project:
            project = random.choice(['TEST', 'DEV', 'PROD', 'QA'])
        number = random.randint(1, 9999)
        return f"{project}-{number}"
    
    @staticmethod
    def create_jira_ticket(
        key: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_name: Optional[str] = None
    ) -> JiraTicket:
        """Create a mock JIRA ticket."""
        if not key:
            key = MockDataFactory.random_jira_key()
        
        if not status:
            status = random.choice(['To Do', 'In Progress', 'Done', 'Blocked', 'Ready for Testing'])
        
        if not priority:
            priority = random.choice(['Low', 'Medium', 'High', 'Critical'])
        
        if not assignee_name:
            assignee_name = f"{MockDataFactory.random_string(6)} {MockDataFactory.random_string(8)}"
        
        return JiraTicket(
            key=key,
            summary=f"Test issue: {MockDataFactory.random_string(20)}",
            status=status,
            assignee=assignee_name,
            priority=priority,
            story_points=random.randint(1, 8),
            sprint=f"Sprint {random.randint(1, 10)}",
            blocked=False,
            last_updated=datetime.now(timezone.utc),
            time_in_status=timedelta(hours=random.randint(1, 72))
        )
    
    @staticmethod
    def create_stakeholder(role: str = "assignee") -> Stakeholder:
        """Create a mock stakeholder."""
        name = f"{MockDataFactory.random_string(6)} {MockDataFactory.random_string(8)}"
        return Stakeholder(
            user_id=f"user{random.randint(100, 999)}",
            name=name,
            email=MockDataFactory.random_email(),
            role=role
        )
    
    @staticmethod
    def create_event_classification(
        category: str = "STATUS_CHANGE",
        urgency: UrgencyLevel = UrgencyLevel.MEDIUM,
        significance: SignificanceLevel = SignificanceLevel.MODERATE
    ) -> EventClassification:
        """Create a mock event classification."""
        return EventClassification(
            category=category,
            urgency=urgency,
            significance=significance,
            affected_teams=["default", "engineering"],
            routing_hints={
                "channels": ["#dev-updates"],
                "urgency_level": urgency.name.lower()
            }
        )
    
    @staticmethod
    def create_enriched_event(
        event_type: str = "issue_updated",
        ticket: Optional[JiraTicket] = None,
        classification: Optional[EventClassification] = None
    ) -> EnrichedEvent:
        """Create a mock enriched event."""
        if not ticket:
            ticket = MockDataFactory.create_jira_ticket()
        
        if not classification:
            classification = MockDataFactory.create_event_classification()
        
        stakeholders = [
            MockDataFactory.create_stakeholder("assignee"),
            MockDataFactory.create_stakeholder("reporter")
        ]
        
        return EnrichedEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            jira_event_data={"test": "data"},
            ticket_key=ticket.key,
            project_key=ticket.key.split('-')[0],
            raw_payload={"webhook": "data"},
            ticket_details=ticket,
            stakeholders=stakeholders,
            classification=classification,
            context_data={"test_context": True}
        )


class TestScenarioGenerator:
    """Generates comprehensive test scenarios."""
    
    @staticmethod
    def create_status_change_scenarios() -> List[TestScenario]:
        """Create status change test scenarios."""
        scenarios = []
        
        # High priority status change
        scenarios.append(TestScenario(
            name="high_priority_status_change",
            description="High priority ticket status change should trigger notifications",
            webhook_events=[{
                "webhookEvent": "jira:issue_updated",
                "issue": {
                    "key": "TEST-123",
                    "fields": {
                        "priority": {"name": "High"},
                        "status": {"name": "In Progress"}
                    }
                },
                "changelog": {
                    "items": [{
                        "field": "status",
                        "fromString": "To Do",
                        "toString": "In Progress"
                    }]
                }
            }],
            expected_hooks=["StatusChangeHook"],
            expected_notifications=1,
            team_configs=[{
                "team_id": "engineering",
                "hooks": {
                    "status_change": {
                        "enabled": True,
                        "conditions": [{"field": "priority", "operator": "in", "values": ["High", "Critical"]}]
                    }
                }
            }],
            success_criteria={"notifications_sent": 1, "hooks_executed": 1}
        ))
        
        # Blocked status change
        scenarios.append(TestScenario(
            name="blocked_status_change",
            description="Ticket becoming blocked should trigger high-priority notifications",
            webhook_events=[{
                "webhookEvent": "jira:issue_updated",
                "issue": {
                    "key": "TEST-124",
                    "fields": {
                        "priority": {"name": "Medium"},
                        "status": {"name": "Blocked"}
                    }
                },
                "changelog": {
                    "items": [{
                        "field": "status",
                        "fromString": "In Progress",
                        "toString": "Blocked"
                    }]
                }
            }],
            expected_hooks=["StatusChangeHook", "BlockerHook"],
            expected_notifications=2,
            team_configs=[{
                "team_id": "engineering",
                "hooks": {
                    "status_change": {"enabled": True},
                    "blocker": {"enabled": True}
                }
            }],
            success_criteria={"notifications_sent": 2, "hooks_executed": 2}
        ))
        
        return scenarios
    
    @staticmethod
    def create_assignment_scenarios() -> List[TestScenario]:
        """Create assignment test scenarios."""
        scenarios = []
        
        # Normal assignment
        scenarios.append(TestScenario(
            name="normal_assignment",
            description="Normal ticket assignment should trigger assignment notifications",
            webhook_events=[{
                "webhookEvent": "jira:issue_updated",
                "issue": {
                    "key": "TEST-125",
                    "fields": {
                        "assignee": {"displayName": "John Doe", "accountId": "user123"}
                    }
                },
                "changelog": {
                    "items": [{
                        "field": "assignee",
                        "fromString": None,
                        "toString": "John Doe"
                    }]
                }
            }],
            expected_hooks=["AssignmentChangeHook"],
            expected_notifications=1,
            team_configs=[{
                "team_id": "engineering",
                "hooks": {
                    "assignment": {"enabled": True, "workload_warnings": True}
                }
            }],
            success_criteria={"notifications_sent": 1, "hooks_executed": 1}
        ))
        
        # Overloaded assignee
        scenarios.append(TestScenario(
            name="overloaded_assignment",
            description="Assignment to overloaded user should include workload warnings",
            webhook_events=[{
                "webhookEvent": "jira:issue_updated",
                "issue": {
                    "key": "TEST-126",
                    "fields": {
                        "assignee": {"displayName": "Overloaded User", "accountId": "user999"}
                    }
                },
                "changelog": {
                    "items": [{
                        "field": "assignee",
                        "fromString": "Previous User",
                        "toString": "Overloaded User"
                    }]
                }
            }],
            expected_hooks=["AssignmentChangeHook"],
            expected_notifications=1,
            team_configs=[{
                "team_id": "engineering",
                "hooks": {
                    "assignment": {"enabled": True, "workload_warnings": True}
                }
            }],
            success_criteria={"notifications_sent": 1, "workload_warning": True}
        ))
        
        return scenarios
    
    @staticmethod
    def create_comment_scenarios() -> List[TestScenario]:
        """Create comment test scenarios."""
        scenarios = []
        
        # High priority comment
        scenarios.append(TestScenario(
            name="high_priority_comment",
            description="Comment on high priority ticket should trigger notifications",
            webhook_events=[{
                "webhookEvent": "jira:issue_updated",
                "issue": {
                    "key": "TEST-127",
                    "fields": {
                        "priority": {"name": "High"}
                    }
                },
                "comment": {
                    "body": "This needs immediate attention!",
                    "author": {"displayName": "Commenter", "accountId": "user456"}
                }
            }],
            expected_hooks=["CommentHook"],
            expected_notifications=1,
            team_configs=[{
                "team_id": "engineering",
                "hooks": {
                    "comment": {
                        "enabled": True,
                        "conditions": [{"field": "ticket_priority", "operator": "in", "values": ["High", "Critical"]}]
                    }
                }
            }],
            success_criteria={"notifications_sent": 1, "hooks_executed": 1}
        ))
        
        return scenarios
    
    @staticmethod
    def create_multi_team_scenarios() -> List[TestScenario]:
        """Create multi-team test scenarios."""
        scenarios = []
        
        # Cross-team notification
        scenarios.append(TestScenario(
            name="cross_team_notification",
            description="Event should trigger notifications for multiple teams",
            webhook_events=[{
                "webhookEvent": "jira:issue_updated",
                "issue": {
                    "key": "SHARED-100",
                    "fields": {
                        "priority": {"name": "Critical"},
                        "status": {"name": "Ready for Testing"}
                    }
                },
                "changelog": {
                    "items": [{
                        "field": "status",
                        "fromString": "In Progress",
                        "toString": "Ready for Testing"
                    }]
                }
            }],
            expected_hooks=["StatusChangeHook"],
            expected_notifications=2,  # One for each team
            team_configs=[
                {
                    "team_id": "engineering",
                    "hooks": {
                        "status_change": {
                            "enabled": True,
                            "conditions": [{"field": "priority", "operator": "in", "values": ["Critical"]}]
                        }
                    }
                },
                {
                    "team_id": "qa",
                    "hooks": {
                        "status_change": {
                            "enabled": True,
                            "conditions": [{"field": "status", "operator": "in", "values": ["Ready for Testing"]}]
                        }
                    }
                }
            ],
            success_criteria={"notifications_sent": 2, "teams_notified": 2}
        ))
        
        return scenarios
    
    @staticmethod
    def get_all_scenarios() -> List[TestScenario]:
        """Get all test scenarios."""
        scenarios = []
        scenarios.extend(TestScenarioGenerator.create_status_change_scenarios())
        scenarios.extend(TestScenarioGenerator.create_assignment_scenarios())
        scenarios.extend(TestScenarioGenerator.create_comment_scenarios())
        scenarios.extend(TestScenarioGenerator.create_multi_team_scenarios())
        return scenarios


class MockServiceFactory:
    """Factory for creating mock services."""
    
    @staticmethod
    def create_mock_jira_service() -> AsyncMock:
        """Create a mock JIRA service."""
        mock_service = AsyncMock()
        
        # Configure common methods
        mock_service.get_ticket_details.return_value = MockDataFactory.create_jira_ticket()
        mock_service.get_user_workload.return_value = {"assigned_tickets": 3, "in_progress": 2}
        mock_service.validate_webhook_signature.return_value = True
        
        return mock_service
    
    @staticmethod
    def create_mock_slack_service() -> AsyncMock:
        """Create a mock Slack service."""
        mock_service = AsyncMock()
        
        # Configure common methods
        mock_service.send_message.return_value = {"ok": True, "ts": "1234567890.123456"}
        mock_service.format_message.return_value = {
            "text": "Test notification",
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}]
        }
        
        return mock_service
    
    @staticmethod
    def create_mock_database() -> AsyncMock:
        """Create a mock database."""
        mock_db = AsyncMock()
        
        # Configure common methods
        mock_db.log_hook_execution.return_value = True
        mock_db.get_team_configuration.return_value = {"team_id": "default", "hooks": {}}
        mock_db.save_analytics_data.return_value = True
        
        return mock_db
    
    @staticmethod
    def create_mock_notification_handler() -> AsyncMock:
        """Create a mock notification handler."""
        mock_handler = AsyncMock()
        
        # Configure common methods
        mock_handler.process_notification.return_value = {"success": True, "message_id": "test123"}
        mock_handler.batch_notifications.return_value = {"batched": True, "count": 1}
        
        return mock_handler


class TestDataValidator:
    """Validates test data and results."""
    
    @staticmethod
    def validate_webhook_event(event: Dict[str, Any]) -> bool:
        """Validate webhook event structure."""
        required_fields = ["webhookEvent", "issue"]
        
        for field in required_fields:
            if field not in event:
                return False
        
        # Validate issue structure
        issue = event["issue"]
        if "key" not in issue or "fields" not in issue:
            return False
        
        return True
    
    @staticmethod
    def validate_enriched_event(event: EnrichedEvent) -> bool:
        """Validate enriched event structure."""
        if not event.event_id or not event.event_type:
            return False
        
        if not event.ticket_key or not event.project_key:
            return False
        
        if not event.ticket_details or not event.classification:
            return False
        
        return True
    
    @staticmethod
    def validate_test_scenario(scenario: TestScenario) -> bool:
        """Validate test scenario structure."""
        if not scenario.name or not scenario.description:
            return False
        
        if not scenario.webhook_events or not scenario.expected_hooks:
            return False
        
        if scenario.expected_notifications < 0:
            return False
        
        # Validate webhook events
        for event in scenario.webhook_events:
            if not TestDataValidator.validate_webhook_event(event):
                return False
        
        return True
    
    @staticmethod
    def validate_performance_metrics(metrics: Dict[str, Any]) -> bool:
        """Validate performance metrics structure."""
        required_fields = [
            "total_requests", "successful_requests", "failed_requests",
            "success_rate", "avg_response_time_ms", "requests_per_second"
        ]
        
        for field in required_fields:
            if field not in metrics:
                return False
        
        # Validate numeric values
        if metrics["success_rate"] < 0 or metrics["success_rate"] > 100:
            return False
        
        if metrics["avg_response_time_ms"] < 0:
            return False
        
        return True


class TestReportGenerator:
    """Generates test reports and summaries."""
    
    @staticmethod
    def generate_scenario_report(
        scenario: TestScenario,
        results: Dict[str, Any]
    ) -> str:
        """Generate a report for a test scenario."""
        report = f"""
Test Scenario Report: {scenario.name}
{'=' * (len(scenario.name) + 22)}

Description: {scenario.description}

Expected Results:
- Hooks: {', '.join(scenario.expected_hooks)}
- Notifications: {scenario.expected_notifications}
- Teams: {len(scenario.team_configs)}

Actual Results:
- Success: {results.get('success', False)}
- Hooks Executed: {results.get('hooks_executed', 0)}
- Notifications Sent: {results.get('notifications_sent', 0)}
- Execution Time: {results.get('execution_time_ms', 0):.2f}ms

Success Criteria:
"""
        
        for criterion, expected in scenario.success_criteria.items():
            actual = results.get(criterion, "N/A")
            status = "✓" if actual == expected else "✗"
            report += f"- {criterion}: {expected} (actual: {actual}) {status}\n"
        
        if results.get('errors'):
            report += f"\nErrors:\n"
            for error in results['errors']:
                report += f"- {error}\n"
        
        return report
    
    @staticmethod
    def generate_summary_report(all_results: List[Dict[str, Any]]) -> str:
        """Generate a summary report for all tests."""
        total_tests = len(all_results)
        successful_tests = sum(1 for r in all_results if r.get('success', False))
        failed_tests = total_tests - successful_tests
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = f"""
End-to-End Test Summary
=======================

Overall Results:
- Total Tests: {total_tests}
- Successful: {successful_tests}
- Failed: {failed_tests}
- Success Rate: {success_rate:.2f}%

Performance Summary:
- Average Execution Time: {sum(r.get('execution_time_ms', 0) for r in all_results) / total_tests:.2f}ms
- Total Notifications Sent: {sum(r.get('notifications_sent', 0) for r in all_results)}
- Total Hooks Executed: {sum(r.get('hooks_executed', 0) for r in all_results)}

Failed Tests:
"""
        
        failed_results = [r for r in all_results if not r.get('success', False)]
        for result in failed_results:
            report += f"- {result.get('scenario_name', 'Unknown')}: {result.get('error', 'Unknown error')}\n"
        
        return report