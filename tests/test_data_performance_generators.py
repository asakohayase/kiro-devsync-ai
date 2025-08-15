"""
Performance-focused test data generators for template benchmarking.
Extends the base test data generators with performance testing scenarios.
"""

import time
import random
from typing import Dict, List, Any, Generator
from dataclasses import dataclass
from tests.test_data_generators import (
    TestDataConfig, DataScenario, MockDataGenerator,
    StandupDataGenerator, PRDataGenerator, JIRADataGenerator, AlertDataGenerator
)


@dataclass
class PerformanceTestConfig(TestDataConfig):
    """Extended configuration for performance testing."""
    batch_size: int = 100
    memory_stress_multiplier: int = 10
    concurrent_threads: int = 5
    cache_test_iterations: int = 1000
    
    # Stress test parameters
    max_team_size: int = 200
    max_pr_count: int = 500
    max_ticket_count: int = 1000
    max_alert_count: int = 100
    
    # Memory test parameters
    large_text_size: int = 10000  # Characters
    deep_nesting_levels: int = 10


class PerformanceDataGenerator(MockDataGenerator):
    """Generator for performance testing scenarios."""
    
    def __init__(self, config: PerformanceTestConfig = None):
        super().__init__(config or PerformanceTestConfig())
        self.perf_config = self.config if isinstance(self.config, PerformanceTestConfig) else PerformanceTestConfig()
    
    def generate_stress_test_data(self, template_type: str) -> Dict[str, Any]:
        """Generate data designed to stress test template rendering."""
        if template_type == "standup":
            return self._generate_stress_standup_data()
        elif template_type == "pr":
            return self._generate_stress_pr_data()
        elif template_type == "jira":
            return self._generate_stress_jira_data()
        elif template_type == "alert":
            return self._generate_stress_alert_data()
        else:
            raise ValueError(f"Unknown template type: {template_type}")
    
    def _generate_stress_standup_data(self) -> Dict[str, Any]:
        """Generate stress test data for standup templates."""
        team_size = self.perf_config.max_team_size
        
        # Create very large team with lots of data
        team_members = []
        for i in range(team_size):
            member = {
                "name": f"StressTestUser{i:04d}",
                "status": self.random.choice(["active", "away", "blocked", "inactive"]),
                "yesterday": [
                    self._random_string(100) for _ in range(self.random.randint(5, 15))
                ],
                "today": [
                    self._random_string(100) for _ in range(self.random.randint(5, 15))
                ],
                "blockers": [
                    self._random_string(150) for _ in range(self.random.randint(0, 5))
                ],
                # Add extra metadata to increase memory usage
                "metadata": {
                    "last_active": self._random_date(7),
                    "productivity_score": self.random.uniform(0.5, 1.0),
                    "recent_commits": [
                        {
                            "sha": ''.join(self.random.choices("abcdef0123456789", k=40)),
                            "message": self._random_string(80),
                            "timestamp": self._random_date(7)
                        }
                        for _ in range(self.random.randint(0, 10))
                    ]
                }
            }
            team_members.append(member)
        
        return {
            "date": "2025-08-14",
            "team": f"StressTestTeam_{team_size}_members",
            "team_members": team_members,
            "stats": {
                "prs_merged": self.random.randint(50, 200),
                "prs_open": self.random.randint(30, 150),
                "tickets_completed": self.random.randint(100, 500),
                "tickets_in_progress": self.random.randint(50, 300),
                "commits": self.random.randint(500, 2000),
                "code_reviews": self.random.randint(100, 400),
                "bugs_fixed": self.random.randint(20, 100),
                "features_delivered": self.random.randint(5, 25)
            },
            "action_items": [
                {
                    "description": self._random_string(200),
                    "assignee": f"StressTestUser{self.random.randint(0, team_size-1):04d}",
                    "due_date": self._random_date(30),
                    "priority": self.random.choice(["low", "medium", "high", "critical"]),
                    "tags": [self._random_string(10) for _ in range(self.random.randint(1, 5))]
                }
                for _ in range(self.random.randint(20, 100))
            ],
            "sprint_info": {
                "name": f"Sprint {self.random.randint(1, 50)}",
                "progress": self.random.uniform(0.0, 1.0),
                "burndown_data": [
                    {"day": i, "remaining": self.random.randint(0, 100)}
                    for i in range(14)  # 2-week sprint
                ]
            }
        }
    
    def _generate_stress_pr_data(self) -> Dict[str, Any]:
        """Generate stress test data for PR templates."""
        # Create PR with lots of files, reviewers, and comments
        files_changed = self.random.randint(100, 500)
        reviewer_count = self.random.randint(10, 30)
        
        return {
            "pr": {
                "id": self.random.randint(10000, 99999),
                "title": self._random_string(200),
                "description": self._random_string(self.perf_config.large_text_size),
                "author": f"stress_test_author_{self.random.randint(1, 100)}",
                "status": "open",
                "draft": False,
                "reviewers": [
                    f"reviewer_{i:03d}" for i in range(reviewer_count)
                ],
                "approved_by": [
                    f"reviewer_{i:03d}" for i in range(self.random.randint(0, reviewer_count//2))
                ],
                "changes_requested_by": [
                    f"reviewer_{i:03d}" for i in range(self.random.randint(0, reviewer_count//3))
                ],
                "files_changed": files_changed,
                "additions": self.random.randint(1000, 10000),
                "deletions": self.random.randint(500, 5000),
                "created_at": self._random_date(30),
                "updated_at": self._random_date(1),
                "jira_tickets": [
                    f"STRESS-{self.random.randint(1000, 9999)}"
                    for _ in range(self.random.randint(5, 20))
                ],
                "ci_status": "passing",
                "file_changes": [
                    {
                        "filename": f"src/component_{i:04d}.py",
                        "additions": self.random.randint(1, 100),
                        "deletions": self.random.randint(0, 50),
                        "status": self.random.choice(["modified", "added", "deleted"])
                    }
                    for i in range(min(files_changed, 100))  # Limit for memory
                ],
                "comments": [
                    {
                        "author": f"reviewer_{self.random.randint(0, reviewer_count-1):03d}",
                        "text": self._random_string(500),
                        "created_at": self._random_date(7),
                        "line_number": self.random.randint(1, 1000),
                        "file": f"src/component_{self.random.randint(0, 99):04d}.py"
                    }
                    for _ in range(self.random.randint(20, 100))
                ]
            },
            "action": "ready_for_review"
        }
    
    def _generate_stress_jira_data(self) -> Dict[str, Any]:
        """Generate stress test data for JIRA templates."""
        comment_count = self.random.randint(50, 200)
        
        return {
            "ticket": {
                "key": f"STRESS-{self.random.randint(10000, 99999)}",
                "summary": self._random_string(300),
                "description": self._random_string(self.perf_config.large_text_size),
                "priority": "Critical",
                "assignee": f"stress_assignee_{self.random.randint(1, 50)}",
                "reporter": f"stress_reporter_{self.random.randint(1, 50)}",
                "sprint": f"Stress Sprint {self.random.randint(1, 20)}",
                "epic": self._random_string(100),
                "story_points": self.random.randint(1, 21),
                "time_spent": f"{self.random.randint(0, 200)}h {self.random.randint(0, 59)}m",
                "time_remaining": f"{self.random.randint(0, 300)}h {self.random.randint(0, 59)}m",
                "created": self._random_date(180),
                "updated": self._random_date(1),
                "comments": [
                    {
                        "author": f"user_{self.random.randint(1, 100):03d}",
                        "text": self._random_string(1000),
                        "created": self._random_date(30),
                        "updated": self._random_date(7) if self.random.random() < 0.3 else None
                    }
                    for _ in range(comment_count)
                ],
                "attachments": [
                    {
                        "filename": f"attachment_{i:03d}.{self.random.choice(['png', 'pdf', 'doc', 'xlsx'])}",
                        "size": self.random.randint(1024, 10*1024*1024),  # 1KB to 10MB
                        "uploaded_by": f"user_{self.random.randint(1, 100):03d}",
                        "uploaded_at": self._random_date(30)
                    }
                    for i in range(self.random.randint(0, 20))
                ],
                "subtasks": [
                    {
                        "key": f"STRESS-{self.random.randint(10000, 99999)}",
                        "summary": self._random_string(100),
                        "status": self.random.choice(["To Do", "In Progress", "Done"]),
                        "assignee": f"user_{self.random.randint(1, 50):03d}"
                    }
                    for _ in range(self.random.randint(0, 15))
                ],
                "linked_issues": [
                    {
                        "key": f"STRESS-{self.random.randint(10000, 99999)}",
                        "relationship": self.random.choice(["blocks", "is blocked by", "relates to", "duplicates"])
                    }
                    for _ in range(self.random.randint(0, 10))
                ]
            },
            "change_type": "comment_added"
        }
    
    def _generate_stress_alert_data(self) -> Dict[str, Any]:
        """Generate stress test data for alert templates."""
        system_count = self.random.randint(20, 50)
        
        return {
            "alert": {
                "id": f"STRESS-ALERT-{self.random.randint(100000, 999999)}",
                "type": "service_outage",
                "severity": "critical",
                "title": self._random_string(200),
                "description": self._random_string(self.perf_config.large_text_size),
                "affected_systems": [
                    f"system_{i:03d}.service.company.com"
                    for i in range(system_count)
                ],
                "impact": self._random_string(500),
                "created_at": self._random_date(1),
                "assigned_to": f"oncall_engineer_{self.random.randint(1, 10)}",
                "escalation_contacts": [
                    f"escalation_{i:02d}@company.com"
                    for i in range(self.random.randint(5, 15))
                ],
                "resolution_steps": [
                    self._random_string(200)
                    for _ in range(self.random.randint(10, 30))
                ],
                "related_tickets": [
                    f"INC-{self.random.randint(100000, 999999)}"
                    for _ in range(self.random.randint(5, 20))
                ],
                "metrics": {
                    "users_affected": self.random.randint(10000, 1000000),
                    "revenue_impact": self.random.randint(1000, 100000),
                    "downtime_minutes": self.random.randint(5, 240),
                    "error_rate": self.random.uniform(0.1, 1.0),
                    "response_time_p99": self.random.randint(1000, 30000)
                },
                "timeline": [
                    {
                        "timestamp": self._random_date(1),
                        "event": self._random_string(100),
                        "author": f"system_user_{self.random.randint(1, 20)}"
                    }
                    for _ in range(self.random.randint(20, 100))
                ]
            }
        }
    
    def generate_memory_stress_data(self, template_type: str) -> List[Dict[str, Any]]:
        """Generate data designed to stress test memory usage."""
        multiplier = self.perf_config.memory_stress_multiplier
        batch_size = self.perf_config.batch_size * multiplier
        
        return [
            self.generate_stress_test_data(template_type)
            for _ in range(batch_size)
        ]
    
    def generate_concurrent_test_data(self, template_type: str) -> Generator[Dict[str, Any], None, None]:
        """Generate data for concurrent testing scenarios."""
        while True:
            yield self.generate_stress_test_data(template_type)
    
    def generate_cache_test_data(self, template_type: str) -> List[Dict[str, Any]]:
        """Generate data for cache performance testing."""
        # Generate base data that will be repeated to test cache hits
        base_data = self.generate_stress_test_data(template_type)
        
        # Create variations for cache miss testing
        variations = []
        for i in range(10):  # 10 different variations
            variation = base_data.copy()
            if template_type == "standup":
                variation["date"] = f"2025-08-{14+i:02d}"
                variation["team"] = f"CacheTestTeam_{i}"
            elif template_type == "pr":
                variation["pr"]["id"] = base_data["pr"]["id"] + i
                variation["pr"]["title"] = f"Cache Test PR {i}"
            elif template_type == "jira":
                variation["ticket"]["key"] = f"CACHE-{1000+i}"
                variation["ticket"]["summary"] = f"Cache Test Ticket {i}"
            elif template_type == "alert":
                variation["alert"]["id"] = f"CACHE-ALERT-{1000+i}"
                variation["alert"]["title"] = f"Cache Test Alert {i}"
            
            variations.append(variation)
        
        # Return data that includes repeated items for cache hit testing
        cache_test_data = []
        for _ in range(self.perf_config.cache_test_iterations):
            # 70% cache hits, 30% cache misses
            if self.random.random() < 0.7:
                cache_test_data.append(self.random.choice(variations[:3]))  # Repeat common items
            else:
                cache_test_data.append(self.random.choice(variations))  # Less common items
        
        return cache_test_data


class BatchDataGenerator:
    """Generator for batch processing test scenarios."""
    
    def __init__(self, config: PerformanceTestConfig = None):
        self.config = config or PerformanceTestConfig()
        self.generators = {
            "standup": StandupDataGenerator(config),
            "pr": PRDataGenerator(config),
            "jira": JIRADataGenerator(config),
            "alert": AlertDataGenerator(config)
        }
    
    def generate_mixed_batch(self, batch_size: int = None) -> List[tuple[str, Dict[str, Any]]]:
        """Generate a mixed batch of different template types."""
        if batch_size is None:
            batch_size = self.config.batch_size
        
        template_types = list(self.generators.keys())
        batch = []
        
        for _ in range(batch_size):
            template_type = random.choice(template_types)
            generator = self.generators[template_type]
            
            if template_type == "standup":
                data = generator.generate_standup_data()
            elif template_type == "pr":
                data = generator.generate_pr_data()
            elif template_type == "jira":
                data = generator.generate_jira_data()
            elif template_type == "alert":
                data = generator.generate_alert_data()
            
            batch.append((template_type, data))
        
        return batch
    
    def generate_time_series_batch(self, template_type: str, days: int = 30) -> List[Dict[str, Any]]:
        """Generate time series data for performance testing."""
        generator = self.generators[template_type]
        time_series = []
        
        for day in range(days):
            date = f"2025-08-{1+day:02d}" if day < 31 else f"2025-09-{day-30:02d}"
            
            if template_type == "standup":
                data = generator.generate_standup_data()
                data["date"] = date
            elif template_type == "pr":
                data = generator.generate_pr_data()
                data["pr"]["created_at"] = f"{date}T10:00:00Z"
            elif template_type == "jira":
                data = generator.generate_jira_data()
                data["ticket"]["created"] = f"{date}T10:00:00Z"
            elif template_type == "alert":
                data = generator.generate_alert_data()
                data["alert"]["created_at"] = f"{date}T10:00:00Z"
            
            time_series.append(data)
        
        return time_series


# Convenience functions for performance testing
def generate_performance_test_suite() -> Dict[str, Dict[str, Any]]:
    """Generate a complete performance test suite."""
    config = PerformanceTestConfig()
    perf_gen = PerformanceDataGenerator(config)
    batch_gen = BatchDataGenerator(config)
    
    return {
        "stress_tests": {
            "standup": perf_gen.generate_stress_test_data("standup"),
            "pr": perf_gen.generate_stress_test_data("pr"),
            "jira": perf_gen.generate_stress_test_data("jira"),
            "alert": perf_gen.generate_stress_test_data("alert")
        },
        "memory_tests": {
            "standup": perf_gen.generate_memory_stress_data("standup"),
            "pr": perf_gen.generate_memory_stress_data("pr"),
            "jira": perf_gen.generate_memory_stress_data("jira"),
            "alert": perf_gen.generate_memory_stress_data("alert")
        },
        "cache_tests": {
            "standup": perf_gen.generate_cache_test_data("standup"),
            "pr": perf_gen.generate_cache_test_data("pr"),
            "jira": perf_gen.generate_cache_test_data("jira"),
            "alert": perf_gen.generate_cache_test_data("alert")
        },
        "batch_tests": {
            "mixed_batch": batch_gen.generate_mixed_batch(100),
            "time_series": {
                "standup": batch_gen.generate_time_series_batch("standup", 30),
                "pr": batch_gen.generate_time_series_batch("pr", 30),
                "jira": batch_gen.generate_time_series_batch("jira", 30),
                "alert": batch_gen.generate_time_series_batch("alert", 30)
            }
        }
    }


if __name__ == "__main__":
    print("Testing performance data generators...")
    
    config = PerformanceTestConfig()
    perf_gen = PerformanceDataGenerator(config)
    
    # Test stress data generation
    template_types = ["standup", "pr", "jira", "alert"]
    
    for template_type in template_types:
        try:
            start_time = time.time()
            stress_data = perf_gen.generate_stress_test_data(template_type)
            generation_time = time.time() - start_time
            
            data_size = len(str(stress_data))
            print(f"✅ {template_type.upper()} stress data: {data_size:,} chars in {generation_time*1000:.2f}ms")
            
            # Verify data structure
            assert isinstance(stress_data, dict)
            assert len(stress_data) > 0
            
        except Exception as e:
            print(f"❌ {template_type.upper()} stress data failed: {e}")
    
    # Test batch generation
    try:
        batch_gen = BatchDataGenerator(config)
        mixed_batch = batch_gen.generate_mixed_batch(10)
        print(f"✅ Mixed batch: Generated {len(mixed_batch)} items")
        
        # Verify batch structure
        assert len(mixed_batch) == 10
        for template_type, data in mixed_batch:
            assert template_type in template_types
            assert isinstance(data, dict)
        
    except Exception as e:
        print(f"❌ Batch generation failed: {e}")
    
    # Test performance suite
    try:
        start_time = time.time()
        test_suite = generate_performance_test_suite()
        suite_time = time.time() - start_time
        
        total_items = (
            len(test_suite["stress_tests"]) +
            sum(len(items) for items in test_suite["memory_tests"].values()) +
            sum(len(items) for items in test_suite["cache_tests"].values()) +
            len(test_suite["batch_tests"]["mixed_batch"]) +
            sum(len(items) for items in test_suite["batch_tests"]["time_series"].values())
        )
        
        print(f"✅ Performance test suite: {total_items:,} items in {suite_time:.2f}s")
        
    except Exception as e:
        print(f"❌ Performance test suite failed: {e}")
    
    print("Performance data generator testing completed!")