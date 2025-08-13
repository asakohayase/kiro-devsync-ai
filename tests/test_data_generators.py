"""
Test data generators for DevSync AI template testing.
Provides mock data for all template types with various scenarios.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class DataScenario(Enum):
    """Test data scenarios."""
    MINIMAL = "minimal"
    COMPLETE = "complete"
    EDGE_CASE = "edge_case"
    LARGE_DATASET = "large_dataset"
    MALFORMED = "malformed"


@dataclass
class TestDataConfig:
    """Configuration for test data generation."""
    scenario: DataScenario = DataScenario.COMPLETE
    team_size: int = 5
    pr_count: int = 10
    ticket_count: int = 15
    include_nulls: bool = False
    include_empty_strings: bool = False
    include_unicode: bool = False
    include_long_text: bool = False


class MockDataGenerator:
    """Base class for generating mock test data."""
    
    def __init__(self, config: TestDataConfig = None):
        self.config = config or TestDataConfig()
        self.random = random.Random(42)  # Fixed seed for reproducible tests
    
    def _random_string(self, length: int = 10, include_unicode: bool = False) -> str:
        """Generate random string."""
        if include_unicode:
            chars = string.ascii_letters + string.digits + "αβγδεζηθικλμνξοπρστυφχψω"
        else:
            chars = string.ascii_letters + string.digits + " "
        return ''.join(self.random.choices(chars, k=length))
    
    def _random_email(self) -> str:
        """Generate random email."""
        username = self._random_string(8).replace(' ', '')
        domain = self._random_string(6).replace(' ', '')
        return f"{username}@{domain}.com"
    
    def _random_date(self, days_ago: int = 30) -> str:
        """Generate random date."""
        base_date = datetime.now() - timedelta(days=self.random.randint(0, days_ago))
        return base_date.isoformat() + "Z"
    
    def _maybe_null(self, value: Any) -> Any:
        """Maybe return null based on config."""
        if self.config.include_nulls and self.random.random() < 0.1:
            return None
        return value
    
    def _maybe_empty_string(self, value: str) -> str:
        """Maybe return empty string based on config."""
        if self.config.include_empty_strings and self.random.random() < 0.1:
            return ""
        return value


class StandupDataGenerator(MockDataGenerator):
    """Generator for standup template test data."""
    
    def generate_team_member(self) -> Dict[str, Any]:
        """Generate a single team member."""
        statuses = ["active", "away", "blocked", "inactive"]
        
        member = {
            "name": self._maybe_null(self._random_string(12)),
            "status": self.random.choice(statuses),
            "yesterday": [],
            "today": [],
            "blockers": []
        }
        
        # Add work items
        if self.config.scenario != DataScenario.MINIMAL:
            yesterday_count = self.random.randint(0, 4)
            today_count = self.random.randint(0, 4)
            blocker_count = self.random.randint(0, 2)
            
            member["yesterday"] = [
                self._maybe_empty_string(self._random_string(30))
                for _ in range(yesterday_count)
            ]
            
            member["today"] = [
                self._maybe_empty_string(self._random_string(30))
                for _ in range(today_count)
            ]
            
            if blocker_count > 0:
                member["blockers"] = [
                    self._maybe_empty_string(self._random_string(40))
                    for _ in range(blocker_count)
                ]
        
        return member
    
    def generate_stats(self) -> Dict[str, int]:
        """Generate team statistics."""
        if self.config.scenario == DataScenario.MINIMAL:
            return {}
        
        stats = {
            "prs_merged": self.random.randint(0, 20),
            "prs_open": self.random.randint(0, 15),
            "tickets_completed": self.random.randint(0, 25),
            "tickets_in_progress": self.random.randint(0, 20),
            "commits": self.random.randint(0, 100)
        }
        
        if self.config.scenario == DataScenario.LARGE_DATASET:
            # Scale up for large dataset testing
            for key in stats:
                stats[key] *= 10
        
        return stats
    
    def generate_standup_data(self) -> Dict[str, Any]:
        """Generate complete standup data."""
        data = {
            "date": self._maybe_null(datetime.now().strftime('%Y-%m-%d')),
            "team": self._maybe_empty_string(self._random_string(15)),
            "stats": self.generate_stats(),
            "team_members": [],
            "action_items": []
        }
        
        # Generate team members
        member_count = self.config.team_size
        if self.config.scenario == DataScenario.LARGE_DATASET:
            member_count = min(member_count * 3, 50)  # Cap at 50 for performance
        
        data["team_members"] = [
            self.generate_team_member() for _ in range(member_count)
        ]
        
        # Generate action items
        if self.config.scenario != DataScenario.MINIMAL:
            action_count = self.random.randint(0, 8)
            data["action_items"] = [
                self._maybe_empty_string(self._random_string(50))
                for _ in range(action_count)
            ]
        
        # Malformed data scenario
        if self.config.scenario == DataScenario.MALFORMED:
            # Introduce various malformations
            if self.random.random() < 0.3:
                data["date"] = "invalid-date"
            if self.random.random() < 0.3:
                data["stats"] = "not-a-dict"
            if self.random.random() < 0.3:
                data["team_members"] = None
        
        return data


class PRDataGenerator(MockDataGenerator):
    """Generator for PR template test data."""
    
    def generate_pr_data(self) -> Dict[str, Any]:
        """Generate PR data."""
        actions = ["opened", "closed", "merged", "ready_for_review", "approved", "has_conflicts"]
        statuses = ["open", "closed", "merged"]
        
        pr_data = {
            "pr": {
                "id": self._maybe_null(self.random.randint(1, 10000)),
                "title": self._maybe_empty_string(self._random_string(50)),
                "description": self._maybe_empty_string(self._random_string(200)),
                "author": self._maybe_empty_string(self._random_string(12)),
                "status": self.random.choice(statuses),
                "draft": self.random.choice([True, False]),
                "reviewers": [],
                "approved_by": [],
                "changes_requested_by": [],
                "has_conflicts": self.random.choice([True, False]),
                "files_changed": self.random.randint(1, 50),
                "additions": self.random.randint(10, 1000),
                "deletions": self.random.randint(5, 500),
                "created_at": self._random_date(30),
                "updated_at": self._random_date(7),
                "jira_tickets": [],
                "ci_status": self.random.choice(["passing", "failing", "pending", "unknown"])
            },
            "action": self.random.choice(actions)
        }
        
        # Add reviewers
        if self.config.scenario != DataScenario.MINIMAL:
            reviewer_count = self.random.randint(1, 5)
            reviewers = [self._random_string(10) for _ in range(reviewer_count)]
            pr_data["pr"]["reviewers"] = reviewers
            
            # Some approved
            approved_count = self.random.randint(0, len(reviewers))
            pr_data["pr"]["approved_by"] = reviewers[:approved_count]
            
            # Some requested changes
            if approved_count < len(reviewers):
                changes_count = self.random.randint(0, len(reviewers) - approved_count)
                pr_data["pr"]["changes_requested_by"] = reviewers[approved_count:approved_count + changes_count]
            
            # Add JIRA tickets
            ticket_count = self.random.randint(0, 3)
            pr_data["pr"]["jira_tickets"] = [
                f"PROJ-{self.random.randint(100, 999)}" for _ in range(ticket_count)
            ]
        
        # Large dataset scenario
        if self.config.scenario == DataScenario.LARGE_DATASET:
            pr_data["pr"]["files_changed"] = self.random.randint(50, 500)
            pr_data["pr"]["additions"] = self.random.randint(1000, 10000)
            pr_data["pr"]["deletions"] = self.random.randint(500, 5000)
        
        # Malformed data scenario
        if self.config.scenario == DataScenario.MALFORMED:
            if self.random.random() < 0.3:
                pr_data["pr"]["id"] = "not-a-number"
            if self.random.random() < 0.3:
                pr_data["pr"]["created_at"] = "invalid-date"
            if self.random.random() < 0.3:
                pr_data["pr"]["reviewers"] = "not-a-list"
        
        return pr_data
    
    def generate_multiple_prs(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate multiple PR data sets."""
        if count is None:
            count = self.config.pr_count
        
        return [self.generate_pr_data() for _ in range(count)]


class JIRADataGenerator(MockDataGenerator):
    """Generator for JIRA template test data."""
    
    def generate_jira_data(self) -> Dict[str, Any]:
        """Generate JIRA ticket data."""
        change_types = [
            "status_change", "priority_change", "assignment_change",
            "comment_added", "blocker_identified", "blocker_resolved", "sprint_change"
        ]
        
        priorities = ["Blocker", "Critical", "High", "Medium", "Low"]
        statuses = ["To Do", "In Progress", "In Review", "Done", "Blocked"]
        
        data = {
            "ticket": {
                "key": f"PROJ-{self.random.randint(100, 9999)}",
                "summary": self._maybe_empty_string(self._random_string(60)),
                "description": self._maybe_empty_string(self._random_string(200)),
                "priority": self.random.choice(priorities),
                "assignee": self._maybe_empty_string(self._random_string(12)),
                "reporter": self._maybe_empty_string(self._random_string(12)),
                "sprint": self._maybe_empty_string(f"Sprint {self.random.randint(1, 20)}"),
                "epic": self._maybe_empty_string(self._random_string(30)),
                "story_points": self._maybe_null(self.random.randint(1, 21)),
                "time_spent": f"{self.random.randint(0, 40)}h {self.random.randint(0, 59)}m",
                "time_remaining": f"{self.random.randint(0, 80)}h {self.random.randint(0, 59)}m",
                "created": self._random_date(60),
                "updated": self._random_date(7),
                "comments": []
            },
            "change_type": self.random.choice(change_types)
        }
        
        # Add change-specific data
        change_type = data["change_type"]
        
        if change_type == "status_change":
            from_status = self.random.choice(statuses)
            to_status = self.random.choice([s for s in statuses if s != from_status])
            data["ticket"]["status"] = {"from": from_status, "to": to_status}
        
        elif change_type == "priority_change":
            from_priority = self.random.choice(priorities)
            to_priority = self.random.choice([p for p in priorities if p != from_priority])
            data["ticket"]["priority_change"] = {"from": from_priority, "to": to_priority}
        
        elif change_type == "assignment_change":
            from_assignee = self._random_string(10)
            to_assignee = self._random_string(10)
            data["ticket"]["assignment_change"] = {"from": from_assignee, "to": to_assignee}
        
        elif change_type == "comment_added":
            comment_count = self.random.randint(1, 5)
            data["ticket"]["comments"] = [
                {
                    "author": self._random_string(10),
                    "text": self._random_string(100),
                    "created": self._random_date(7)
                }
                for _ in range(comment_count)
            ]
        
        elif change_type in ["blocker_identified", "blocker_resolved"]:
            data["blocker"] = {
                "type": change_type.split("_")[1],  # identified or resolved
                "description": self._random_string(80)
            }
        
        elif change_type == "sprint_change":
            data["ticket"]["sprint_change"] = {
                "from": f"Sprint {self.random.randint(1, 10)}",
                "to": f"Sprint {self.random.randint(11, 20)}",
                "type": self.random.choice(["moved", "added", "removed"])
            }
        
        # Malformed data scenario
        if self.config.scenario == DataScenario.MALFORMED:
            if self.random.random() < 0.3:
                data["ticket"]["story_points"] = "not-a-number"
            if self.random.random() < 0.3:
                data["ticket"]["created"] = "invalid-date"
            if self.random.random() < 0.3:
                data["change_type"] = "invalid_change_type"
        
        return data
    
    def generate_multiple_tickets(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate multiple JIRA ticket data sets."""
        if count is None:
            count = self.config.ticket_count
        
        return [self.generate_jira_data() for _ in range(count)]


class AlertDataGenerator(MockDataGenerator):
    """Generator for alert template test data."""
    
    def generate_alert_data(self) -> Dict[str, Any]:
        """Generate alert data."""
        alert_types = [
            "build_failure", "deployment_issue", "security_vulnerability",
            "service_outage", "critical_bug", "team_blocker", "dependency_issue"
        ]
        
        severities = ["critical", "high", "medium", "low"]
        
        data = {
            "alert": {
                "id": f"ALERT-{self.random.randint(1000, 9999)}",
                "type": self.random.choice(alert_types),
                "severity": self.random.choice(severities),
                "title": self._maybe_empty_string(self._random_string(60)),
                "description": self._maybe_empty_string(self._random_string(200)),
                "affected_systems": [],
                "impact": self._maybe_empty_string(self._random_string(80)),
                "created_at": self._random_date(1),
                "assigned_to": self._maybe_empty_string(self._random_string(15)),
                "escalation_contacts": [],
                "sla_breach_time": (datetime.now() + timedelta(hours=self.random.randint(1, 24))).isoformat() + "Z",
                "resolution_steps": [],
                "related_pr": self._maybe_null(self.random.randint(1, 1000)),
                "related_tickets": []
            }
        }
        
        # Add affected systems
        if self.config.scenario != DataScenario.MINIMAL:
            system_count = self.random.randint(1, 5)
            systems = ["API", "Database", "Frontend", "CI/CD", "Monitoring", "Auth Service"]
            data["alert"]["affected_systems"] = self.random.sample(systems, min(system_count, len(systems)))
            
            # Add escalation contacts
            contact_count = self.random.randint(1, 3)
            data["alert"]["escalation_contacts"] = [
                self._random_email() for _ in range(contact_count)
            ]
            
            # Add resolution steps
            step_count = self.random.randint(2, 6)
            data["alert"]["resolution_steps"] = [
                self._random_string(50) for _ in range(step_count)
            ]
            
            # Add related tickets
            ticket_count = self.random.randint(0, 3)
            data["alert"]["related_tickets"] = [
                f"PROJ-{self.random.randint(100, 999)}" for _ in range(ticket_count)
            ]
        
        # Add type-specific data
        alert_type = data["alert"]["type"]
        
        if alert_type == "build_failure":
            data["build_info"] = {
                "branch": self.random.choice(["main", "develop", "feature/auth", "hotfix/critical"]),
                "commit": ''.join(self.random.choices(string.ascii_lowercase + string.digits, k=8)),
                "pipeline_url": f"https://ci.company.com/build/{self.random.randint(1000, 9999)}"
            }
        
        elif alert_type == "deployment_issue":
            data["deployment_info"] = {
                "environment": self.random.choice(["production", "staging", "development"]),
                "version": f"v{self.random.randint(1, 5)}.{self.random.randint(0, 20)}.{self.random.randint(0, 10)}",
                "rollback_available": self.random.choice([True, False])
            }
        
        elif alert_type == "security_vulnerability":
            data["security_info"] = {
                "cve_id": f"CVE-2025-{self.random.randint(10000, 99999)}",
                "cvss_score": round(self.random.uniform(1.0, 10.0), 1),
                "attack_vector": self.random.choice(["Network", "Local", "Physical"])
            }
        
        elif alert_type == "service_outage":
            data["outage_info"] = {
                "services": self.random.sample(
                    ["API Gateway", "User Service", "Payment Service", "Notification Service"],
                    self.random.randint(1, 3)
                ),
                "users_affected": self.random.randint(100, 100000),
                "status_page": "https://status.company.com"
            }
        
        # Malformed data scenario
        if self.config.scenario == DataScenario.MALFORMED:
            if self.random.random() < 0.3:
                data["alert"]["severity"] = "invalid_severity"
            if self.random.random() < 0.3:
                data["alert"]["created_at"] = "not-a-date"
            if self.random.random() < 0.3:
                data["alert"]["affected_systems"] = "not-a-list"
        
        return data


class TestDataFactory:
    """Factory for creating test data generators."""
    
    @staticmethod
    def create_generator(template_type: str, config: TestDataConfig = None) -> MockDataGenerator:
        """Create appropriate data generator for template type."""
        generators = {
            "standup": StandupDataGenerator,
            "pr": PRDataGenerator,
            "jira": JIRADataGenerator,
            "alert": AlertDataGenerator
        }
        
        generator_class = generators.get(template_type, MockDataGenerator)
        return generator_class(config)
    
    @staticmethod
    def generate_edge_cases() -> Dict[str, List[Dict[str, Any]]]:
        """Generate edge case test data for all template types."""
        edge_config = TestDataConfig(
            scenario=DataScenario.EDGE_CASE,
            include_nulls=True,
            include_empty_strings=True,
            include_unicode=True
        )
        
        edge_cases = {}
        
        # Standup edge cases
        standup_gen = StandupDataGenerator(edge_config)
        edge_cases["standup"] = [
            standup_gen.generate_standup_data() for _ in range(5)
        ]
        
        # PR edge cases
        pr_gen = PRDataGenerator(edge_config)
        edge_cases["pr"] = [
            pr_gen.generate_pr_data() for _ in range(5)
        ]
        
        # JIRA edge cases
        jira_gen = JIRADataGenerator(edge_config)
        edge_cases["jira"] = [
            jira_gen.generate_jira_data() for _ in range(5)
        ]
        
        # Alert edge cases
        alert_gen = AlertDataGenerator(edge_config)
        edge_cases["alert"] = [
            alert_gen.generate_alert_data() for _ in range(5)
        ]
        
        return edge_cases
    
    @staticmethod
    def generate_large_datasets() -> Dict[str, List[Dict[str, Any]]]:
        """Generate large datasets for performance testing."""
        large_config = TestDataConfig(
            scenario=DataScenario.LARGE_DATASET,
            team_size=20,
            pr_count=100,
            ticket_count=150
        )
        
        datasets = {}
        
        # Large standup dataset
        standup_gen = StandupDataGenerator(large_config)
        datasets["standup"] = [standup_gen.generate_standup_data()]
        
        # Large PR dataset
        pr_gen = PRDataGenerator(large_config)
        datasets["pr"] = pr_gen.generate_multiple_prs(100)
        
        # Large JIRA dataset
        jira_gen = JIRADataGenerator(large_config)
        datasets["jira"] = jira_gen.generate_multiple_tickets(150)
        
        # Large alert dataset
        alert_gen = AlertDataGenerator(large_config)
        datasets["alert"] = [alert_gen.generate_alert_data() for _ in range(50)]
        
        return datasets
    
    @staticmethod
    def generate_malformed_data() -> Dict[str, List[Dict[str, Any]]]:
        """Generate malformed data for error handling tests."""
        malformed_config = TestDataConfig(
            scenario=DataScenario.MALFORMED,
            include_nulls=True,
            include_empty_strings=True
        )
        
        malformed_data = {}
        
        # Malformed standup data
        standup_gen = StandupDataGenerator(malformed_config)
        malformed_data["standup"] = [
            standup_gen.generate_standup_data() for _ in range(10)
        ]
        
        # Malformed PR data
        pr_gen = PRDataGenerator(malformed_config)
        malformed_data["pr"] = [
            pr_gen.generate_pr_data() for _ in range(10)
        ]
        
        # Malformed JIRA data
        jira_gen = JIRADataGenerator(malformed_config)
        malformed_data["jira"] = [
            jira_gen.generate_jira_data() for _ in range(10)
        ]
        
        # Malformed alert data
        alert_gen = AlertDataGenerator(malformed_config)
        malformed_data["alert"] = [
            alert_gen.generate_alert_data() for _ in range(10)
        ]
        
        return malformed_data


# Convenience functions for quick data generation
def generate_standup_data(scenario: DataScenario = DataScenario.COMPLETE) -> Dict[str, Any]:
    """Quick standup data generation."""
    config = TestDataConfig(scenario=scenario)
    generator = StandupDataGenerator(config)
    return generator.generate_standup_data()


def generate_pr_data(scenario: DataScenario = DataScenario.COMPLETE) -> Dict[str, Any]:
    """Quick PR data generation."""
    config = TestDataConfig(scenario=scenario)
    generator = PRDataGenerator(config)
    return generator.generate_pr_data()


def generate_jira_data(scenario: DataScenario = DataScenario.COMPLETE) -> Dict[str, Any]:
    """Quick JIRA data generation."""
    config = TestDataConfig(scenario=scenario)
    generator = JIRADataGenerator(config)
    return generator.generate_jira_data()


def generate_alert_data(scenario: DataScenario = DataScenario.COMPLETE) -> Dict[str, Any]:
    """Quick alert data generation."""
    config = TestDataConfig(scenario=scenario)
    generator = AlertDataGenerator(config)
    return generator.generate_alert_data()


if __name__ == "__main__":
    # Test the generators
    print("Testing data generators...")
    
    # Test each generator
    generators = [
        ("Standup", generate_standup_data),
        ("PR", generate_pr_data),
        ("JIRA", generate_jira_data),
        ("Alert", generate_alert_data)
    ]
    
    for name, generator_func in generators:
        try:
            data = generator_func()
            print(f"✅ {name} generator: Generated data with {len(str(data))} characters")
        except Exception as e:
            print(f"❌ {name} generator failed: {e}")
    
    # Test edge cases
    try:
        edge_cases = TestDataFactory.generate_edge_cases()
        total_cases = sum(len(cases) for cases in edge_cases.values())
        print(f"✅ Edge cases: Generated {total_cases} test cases")
    except Exception as e:
        print(f"❌ Edge cases failed: {e}")
    
    # Test large datasets
    try:
        large_datasets = TestDataFactory.generate_large_datasets()
        total_items = sum(len(items) for items in large_datasets.values())
        print(f"✅ Large datasets: Generated {total_items} items")
    except Exception as e:
        print(f"❌ Large datasets failed: {e}")
    
    print("Data generator testing completed!")