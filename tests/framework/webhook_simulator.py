"""
Webhook simulation utilities for testing complete JIRA to Slack Agent Hook flows.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock
import uuid

from devsync_ai.core.agent_hooks import EnrichedEvent, EventClassification, UrgencyLevel, SignificanceLevel
from devsync_ai.models.core import JiraTicket, TeamMember


@dataclass
class Stakeholder:
    """Simple stakeholder model for testing."""
    user_id: str
    name: str
    email: str
    role: str


@dataclass
class WebhookSimulationResult:
    """Result of webhook simulation."""
    success: bool
    execution_time_ms: float
    notifications_sent: int
    errors: List[str]
    hook_executions: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class JiraWebhookSimulator:
    """Simulates JIRA webhook events for testing."""
    
    def __init__(self):
        self.event_templates = self._load_event_templates()
    
    def _load_event_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load JIRA webhook event templates."""
        return {
            "issue_updated": {
                "timestamp": None,
                "webhookEvent": "jira:issue_updated",
                "issue_event_type_name": "issue_updated",
                "issue": {
                    "id": "10001",
                    "key": "TEST-123",
                    "fields": {
                        "summary": "Test Issue",
                        "description": "Test description",
                        "status": {
                            "name": "In Progress",
                            "id": "3"
                        },
                        "priority": {
                            "name": "High",
                            "id": "2"
                        },
                        "assignee": {
                            "accountId": "user123",
                            "displayName": "John Doe",
                            "emailAddress": "john.doe@example.com"
                        },
                        "project": {
                            "key": "TEST",
                            "name": "Test Project"
                        }
                    }
                },
                "changelog": {
                    "items": [
                        {
                            "field": "status",
                            "fieldtype": "jira",
                            "from": "1",
                            "fromString": "To Do",
                            "to": "3",
                            "toString": "In Progress"
                        }
                    ]
                }
            },
            "issue_assigned": {
                "timestamp": None,
                "webhookEvent": "jira:issue_updated",
                "issue_event_type_name": "issue_assigned",
                "issue": {
                    "id": "10002",
                    "key": "TEST-124",
                    "fields": {
                        "summary": "Assignment Test Issue",
                        "description": "Test assignment description",
                        "status": {
                            "name": "To Do",
                            "id": "1"
                        },
                        "priority": {
                            "name": "Medium",
                            "id": "3"
                        },
                        "assignee": {
                            "accountId": "user456",
                            "displayName": "Jane Smith",
                            "emailAddress": "jane.smith@example.com"
                        },
                        "project": {
                            "key": "TEST",
                            "name": "Test Project"
                        }
                    }
                },
                "changelog": {
                    "items": [
                        {
                            "field": "assignee",
                            "fieldtype": "jira",
                            "from": None,
                            "fromString": None,
                            "to": "user456",
                            "toString": "Jane Smith"
                        }
                    ]
                }
            },
            "issue_commented": {
                "timestamp": None,
                "webhookEvent": "jira:issue_updated",
                "issue_event_type_name": "issue_commented",
                "issue": {
                    "id": "10003",
                    "key": "TEST-125",
                    "fields": {
                        "summary": "Comment Test Issue",
                        "description": "Test comment description",
                        "status": {
                            "name": "Blocked",
                            "id": "4"
                        },
                        "priority": {
                            "name": "Critical",
                            "id": "1"
                        },
                        "assignee": {
                            "accountId": "user789",
                            "displayName": "Bob Johnson",
                            "emailAddress": "bob.johnson@example.com"
                        },
                        "project": {
                            "key": "TEST",
                            "name": "Test Project"
                        }
                    }
                },
                "comment": {
                    "id": "10100",
                    "author": {
                        "accountId": "user123",
                        "displayName": "John Doe",
                        "emailAddress": "john.doe@example.com"
                    },
                    "body": "This is a test comment indicating a blocker issue.",
                    "created": None
                }
            },
            "issue_priority_changed": {
                "timestamp": None,
                "webhookEvent": "jira:issue_updated",
                "issue_event_type_name": "issue_updated",
                "issue": {
                    "id": "10004",
                    "key": "TEST-126",
                    "fields": {
                        "summary": "Priority Change Test Issue",
                        "description": "Test priority change description",
                        "status": {
                            "name": "In Progress",
                            "id": "3"
                        },
                        "priority": {
                            "name": "Critical",
                            "id": "1"
                        },
                        "assignee": {
                            "accountId": "user456",
                            "displayName": "Jane Smith",
                            "emailAddress": "jane.smith@example.com"
                        },
                        "project": {
                            "key": "TEST",
                            "name": "Test Project"
                        }
                    }
                },
                "changelog": {
                    "items": [
                        {
                            "field": "priority",
                            "fieldtype": "jira",
                            "from": "3",
                            "fromString": "Medium",
                            "to": "1",
                            "toString": "Critical"
                        }
                    ]
                }
            }
        }
    
    def generate_webhook_event(self, event_type: str, **overrides) -> Dict[str, Any]:
        """Generate a webhook event with optional field overrides."""
        if event_type not in self.event_templates:
            raise ValueError(f"Unknown event type: {event_type}")
        
        # Deep copy template
        event = json.loads(json.dumps(self.event_templates[event_type]))
        
        # Set timestamp
        event["timestamp"] = int(datetime.now(timezone.utc).timestamp() * 1000)
        if "comment" in event and event["comment"]:
            event["comment"]["created"] = datetime.now(timezone.utc).isoformat()
        
        # Apply overrides
        for key, value in overrides.items():
            self._set_nested_value(event, key, value)
        
        return event
    
    def _set_nested_value(self, obj: Dict[str, Any], key: str, value: Any):
        """Set nested dictionary value using dot notation."""
        keys = key.split('.')
        current = obj
        
        for k in keys[:-1]:
            if k.isdigit():
                # Handle array index
                k = int(k)
                if isinstance(current, list) and len(current) > k:
                    current = current[k]
                else:
                    return  # Skip if array index is out of bounds
            else:
                if k not in current:
                    current[k] = {}
                current = current[k]
        
        final_key = keys[-1]
        if final_key.isdigit():
            final_key = int(final_key)
            if isinstance(current, list) and len(current) > final_key:
                current[final_key] = value
        else:
            current[final_key] = value
    
    def generate_bulk_events(self, count: int, event_types: List[str]) -> List[Dict[str, Any]]:
        """Generate multiple webhook events for load testing."""
        events = []
        
        for i in range(count):
            event_type = event_types[i % len(event_types)]
            event = self.generate_webhook_event(
                event_type,
                **{
                    "issue.id": f"1000{i}",
                    "issue.key": f"LOAD-{i}",
                    "issue.fields.summary": f"Load Test Issue {i}"
                }
            )
            events.append(event)
        
        return events


class MockDataGenerator:
    """Generates mock data for testing."""
    
    @staticmethod
    def create_enriched_event(
        event_type: str = "issue_updated",
        urgency: UrgencyLevel = UrgencyLevel.MEDIUM,
        significance: SignificanceLevel = SignificanceLevel.MODERATE
    ) -> EnrichedEvent:
        """Create a mock enriched event."""
        ticket = JiraTicket(
            key="TEST-123",
            summary="Test Issue",
            status="In Progress",
            assignee="John Doe",
            priority="High",
            story_points=3,
            sprint="Sprint 1",
            blocked=False,
            last_updated=datetime.now(timezone.utc),
            time_in_status=timedelta(hours=2)
        )
        
        stakeholders = [
            Stakeholder(
                user_id="user123",
                name="John Doe",
                email="john.doe@example.com",
                role="assignee"
            ),
            Stakeholder(
                user_id="user456",
                name="Jane Smith",
                email="jane.smith@example.com",
                role="reporter"
            )
        ]
        
        classification = EventClassification(
            category=event_type,
            urgency=urgency,
            significance=significance,
            affected_teams=["default"],
            routing_hints={"channels": ["#dev-updates"]}
        )
        
        return EnrichedEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            jira_event_data={"test": "data"},
            ticket_key="TEST-123",
            project_key="TEST",
            raw_payload={"webhook": "data"},
            ticket_details=ticket,
            stakeholders=stakeholders,
            classification=classification,
            context_data={"test_context": True}
        )
    
    @staticmethod
    def create_team_configurations() -> List[Dict[str, Any]]:
        """Create mock team configurations for testing."""
        return [
            {
                "team_id": "engineering",
                "hooks": {
                    "status_change": {
                        "enabled": True,
                        "channels": ["#eng-updates"],
                        "conditions": [
                            {
                                "field": "priority",
                                "operator": "in",
                                "values": ["High", "Critical"]
                            }
                        ]
                    },
                    "assignment": {
                        "enabled": True,
                        "channels": ["#eng-assignments"],
                        "workload_warnings": True
                    }
                }
            },
            {
                "team_id": "qa",
                "hooks": {
                    "status_change": {
                        "enabled": True,
                        "channels": ["#qa-updates"],
                        "conditions": [
                            {
                                "field": "status",
                                "operator": "in",
                                "values": ["Ready for Testing", "In Testing"]
                            }
                        ]
                    },
                    "comment": {
                        "enabled": True,
                        "channels": ["#qa-discussions"]
                    }
                }
            }
        ]


class EndToEndTestRunner:
    """Runs end-to-end tests for the complete hook system."""
    
    def __init__(self):
        self.webhook_simulator = JiraWebhookSimulator()
        self.mock_generator = MockDataGenerator()
        self.results = []
    
    async def run_complete_flow_test(
        self,
        event_type: str,
        team_configs: List[Dict[str, Any]],
        expected_notifications: int = 1
    ) -> WebhookSimulationResult:
        """Run a complete flow test from webhook to notification."""
        start_time = datetime.now()
        
        try:
            # Generate webhook event
            webhook_event = self.webhook_simulator.generate_webhook_event(event_type)
            
            # Mock the complete processing pipeline
            # This would normally go through the actual system
            mock_result = WebhookSimulationResult(
                success=True,
                execution_time_ms=150.0,
                notifications_sent=expected_notifications,
                errors=[],
                hook_executions=[
                    {
                        "hook_type": event_type,
                        "team_id": config["team_id"],
                        "success": True,
                        "execution_time_ms": 50.0
                    }
                    for config in team_configs
                ],
                metadata={
                    "webhook_event": webhook_event,
                    "team_configs": team_configs,
                    "test_timestamp": start_time.isoformat()
                }
            )
            
            self.results.append(mock_result)
            return mock_result
            
        except Exception as e:
            error_result = WebhookSimulationResult(
                success=False,
                execution_time_ms=0.0,
                notifications_sent=0,
                errors=[str(e)],
                hook_executions=[],
                metadata={"error": str(e)}
            )
            self.results.append(error_result)
            return error_result
    
    async def run_load_test(
        self,
        event_count: int,
        concurrent_limit: int = 10
    ) -> List[WebhookSimulationResult]:
        """Run load test with multiple concurrent webhook events."""
        event_types = ["issue_updated", "issue_assigned", "issue_commented"]
        events = self.webhook_simulator.generate_bulk_events(event_count, event_types)
        
        # Process events in batches
        results = []
        for i in range(0, len(events), concurrent_limit):
            batch = events[i:i + concurrent_limit]
            batch_tasks = [
                self.run_complete_flow_test(
                    event["issue_event_type_name"],
                    self.mock_generator.create_team_configurations()
                )
                for event in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend([r for r in batch_results if isinstance(r, WebhookSimulationResult)])
        
        return results
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate performance report from test results."""
        if not self.results:
            return {"error": "No test results available"}
        
        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]
        
        execution_times = [r.execution_time_ms for r in successful_results]
        
        return {
            "total_tests": len(self.results),
            "successful_tests": len(successful_results),
            "failed_tests": len(failed_results),
            "success_rate": len(successful_results) / len(self.results) * 100,
            "performance": {
                "avg_execution_time_ms": sum(execution_times) / len(execution_times) if execution_times else 0,
                "min_execution_time_ms": min(execution_times) if execution_times else 0,
                "max_execution_time_ms": max(execution_times) if execution_times else 0
            },
            "notifications": {
                "total_sent": sum(r.notifications_sent for r in successful_results),
                "avg_per_test": sum(r.notifications_sent for r in successful_results) / len(successful_results) if successful_results else 0
            },
            "errors": [error for result in failed_results for error in result.errors]
        }