"""
Comprehensive system validation tests for the complete template system.
Tests full test suite, accessibility compliance, and performance under realistic load conditions.
"""

import pytest
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any
from datetime import datetime

from devsync_ai.core.template_registry import initialize_template_system, create_end_to_end_message
from devsync_ai.core.template_factory import MessageTemplateFactory, TemplateType
from devsync_ai.core.message_formatter import TemplateConfig
from devsync_ai.templates.standup_template import StandupTemplate
from devsync_ai.templates.pr_templates import NewPRTemplate, ApprovedPRTemplate
from devsync_ai.templates.jira_templates import StatusChangeTemplate
from devsync_ai.templates.alert_templates import BuildFailureTemplate


class TestComprehensiveSystemValidation:
    """Comprehensive system validation tests."""
    
    @pytest.fixture(scope="class")
    def initialized_factory(self):
        """Initialize the template system once for all tests."""
        return initialize_template_system()
    
    @pytest.fixture
    def accessibility_config(self):
        """Configuration with accessibility mode enabled."""
        return TemplateConfig(
            team_id="accessibility_test",
            accessibility_mode=True,
            interactive_elements=False,
            emoji_set={
                "success": "[COMPLETED]",
                "warning": "[WARNING]",
                "error": "[ERROR]",
                "info": "[INFO]"
            }
        )
    
    @pytest.fixture
    def performance_config(self):
        """Configuration optimized for performance testing."""
        return TemplateConfig(
            team_id="performance_test",
            interactive_elements=True,
            accessibility_mode=False
        )
    
    def test_full_template_suite_validation(self, initialized_factory):
        """Run validation across all template types and scenarios."""
        # Test data for each template type
        test_scenarios = {
            TemplateType.STANDUP: {
                "date": "2024-01-15",
                "team": "Engineering Team",
                "team_members": [
                    {"name": "alice", "yesterday": "Completed feature", "today": "Working on tests", "blockers": []},
                    {"name": "bob", "yesterday": "Fixed bugs", "today": "Code review", "blockers": ["Waiting for API"]}
                ],
                "stats": {"prs_merged": 3, "prs_open": 2, "tickets_closed": 5, "commits": 15},
                "sprint_progress": {"completed": 7, "total": 10}
            },
            TemplateType.PR_NEW: {
                "pr": {
                    "number": 123,
                    "title": "Add user authentication feature",
                    "html_url": "https://github.com/company/repo/pull/123",
                    "user": {"login": "alice"},
                    "head": {"ref": "feature/auth"},
                    "base": {"ref": "main"},
                    "reviewers": [{"login": "bob", "review_status": "pending"}]
                }
            },
            TemplateType.JIRA_STATUS: {
                "ticket": {
                    "key": "DEV-456",
                    "summary": "Implement user dashboard",
                    "status": "In Progress",
                    "priority": "High",
                    "assignee": "alice"
                },
                "from_status": "To Do",
                "to_status": "In Progress"
            },
            TemplateType.ALERT_BUILD: {
                "alert": {
                    "id": "alert_789",
                    "title": "Build Failure",
                    "description": "Unit tests failed",
                    "severity": "high",
                    "type": "build_failure"
                },
                "build_info": {
                    "branch": "main",
                    "commit": "abc123",
                    "failed_stage": "tests"
                }
            }
        }
        
        validation_results = {
            "total_templates_tested": 0,
            "successful_validations": 0,
            "failed_validations": [],
            "performance_metrics": {}
        }
        
        # Test each template type
        for template_type, test_data in test_scenarios.items():
            try:
                start_time = time.time()
                
                # Create template
                template = initialized_factory.create_template(template_type)
                
                # Format message
                message = template.format_message(test_data)
                
                # Validate message structure
                assert message.blocks is not None
                assert len(message.blocks) > 0
                assert message.text is not None
                assert message.metadata is not None
                
                # Validate content is not empty
                message_json = json.dumps(message.blocks)
                assert len(message_json) > 100  # Reasonable content size
                
                # Record performance
                execution_time = time.time() - start_time
                validation_results["performance_metrics"][template_type.value] = execution_time
                
                validation_results["successful_validations"] += 1
                
            except Exception as e:
                validation_results["failed_validations"].append({
                    "template_type": template_type.value,
                    "error": str(e)
                })
            
            validation_results["total_templates_tested"] += 1
        
        # Assert overall validation success
        assert len(validation_results["failed_validations"]) == 0, f"Failed validations: {validation_results['failed_validations']}"
        assert validation_results["successful_validations"] == validation_results["total_templates_tested"]
        
        # Assert reasonable performance (all templates should complete within 1 second)
        for template_type, execution_time in validation_results["performance_metrics"].items():
            assert execution_time < 1.0, f"Template {template_type} took {execution_time:.2f}s (too slow)"
    
    def test_accessibility_compliance_validation(self, initialized_factory, accessibility_config):
        """Validate accessibility compliance across all message formats."""
        accessibility_test_cases = [
            (TemplateType.STANDUP, {
                "date": "2024-01-15",
                "team": "Accessible Team",
                "team_members": [{"name": "alice", "yesterday": "Work", "today": "More work", "blockers": []}],
                "stats": {"prs_merged": 1}
            }),
            (TemplateType.PR_NEW, {
                "pr": {"number": 1, "title": "Accessible PR", "user": {"login": "alice"}}
            }),
            (TemplateType.JIRA_STATUS, {
                "ticket": {"key": "ACC-1", "summary": "Accessible ticket", "status": "Done"},
                "from_status": "To Do",
                "to_status": "Done"
            }),
            (TemplateType.ALERT_BUILD, {
                "alert": {"id": "1", "title": "Accessible Alert", "severity": "medium", "type": "build_failure"},
                "build_info": {"branch": "main", "commit": "abc123"}
            })
        ]
        
        accessibility_results = {
            "total_tested": 0,
            "accessibility_compliant": 0,
            "compliance_issues": []
        }
        
        for template_type, test_data in accessibility_test_cases:
            try:
                # Create template with accessibility configuration
                template = initialized_factory.create_template(template_type, accessibility_config)
                message = template.format_message(test_data)
                
                # Validate accessibility features
                accessibility_checks = self._validate_accessibility_compliance(message)
                
                if accessibility_checks["is_compliant"]:
                    accessibility_results["accessibility_compliant"] += 1
                else:
                    accessibility_results["compliance_issues"].append({
                        "template_type": template_type.value,
                        "issues": accessibility_checks["issues"]
                    })
                
            except Exception as e:
                accessibility_results["compliance_issues"].append({
                    "template_type": template_type.value,
                    "issues": [f"Exception during accessibility validation: {e}"]
                })
            
            accessibility_results["total_tested"] += 1
        
        # Assert accessibility compliance
        assert len(accessibility_results["compliance_issues"]) == 0, f"Accessibility issues: {accessibility_results['compliance_issues']}"
        assert accessibility_results["accessibility_compliant"] == accessibility_results["total_tested"]
    
    def test_performance_under_realistic_load(self, initialized_factory, performance_config):
        """Test performance under realistic load conditions."""
        # Define realistic load scenarios
        load_scenarios = [
            {
                "name": "High Volume Standup Messages",
                "template_type": TemplateType.STANDUP,
                "concurrent_requests": 50,
                "data_generator": self._generate_standup_data
            },
            {
                "name": "PR Notification Burst",
                "template_type": TemplateType.PR_NEW,
                "concurrent_requests": 30,
                "data_generator": self._generate_pr_data
            },
            {
                "name": "Alert Storm Simulation",
                "template_type": TemplateType.ALERT_BUILD,
                "concurrent_requests": 20,
                "data_generator": self._generate_alert_data
            }
        ]
        
        performance_results = {
            "scenarios_tested": 0,
            "scenarios_passed": 0,
            "performance_metrics": {},
            "failures": []
        }
        
        for scenario in load_scenarios:
            try:
                scenario_results = self._run_load_test_scenario(
                    initialized_factory,
                    performance_config,
                    scenario
                )
                
                performance_results["performance_metrics"][scenario["name"]] = scenario_results
                
                # Validate performance requirements
                assert scenario_results["average_response_time"] < 0.5, f"Average response time too high: {scenario_results['average_response_time']:.3f}s"
                assert scenario_results["success_rate"] > 0.95, f"Success rate too low: {scenario_results['success_rate']:.2%}"
                assert scenario_results["max_response_time"] < 2.0, f"Max response time too high: {scenario_results['max_response_time']:.3f}s"
                
                performance_results["scenarios_passed"] += 1
                
            except Exception as e:
                performance_results["failures"].append({
                    "scenario": scenario["name"],
                    "error": str(e)
                })
            
            performance_results["scenarios_tested"] += 1
        
        # Assert overall performance requirements
        assert len(performance_results["failures"]) == 0, f"Performance test failures: {performance_results['failures']}"
        assert performance_results["scenarios_passed"] == performance_results["scenarios_tested"]
    
    def test_memory_usage_validation(self, initialized_factory):
        """Test memory usage patterns and validate no memory leaks."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            pytest.skip("psutil not available, skipping memory usage test")
        
        # Create and format many messages to test memory usage
        for i in range(100):
            template = initialized_factory.create_template(TemplateType.STANDUP)
            message = template.format_message({
                "date": f"2024-01-{i % 30 + 1:02d}",
                "team": f"Team {i}",
                "team_members": [
                    {"name": f"user_{j}", "yesterday": f"Task {j}", "today": f"Task {j+1}", "blockers": []}
                    for j in range(i % 5 + 1)
                ],
                "stats": {"prs_merged": i % 10, "commits": i % 20}
            })
            
            # Validate message was created
            assert len(message.blocks) > 0
        
        # Check memory usage after operations
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for 100 messages)
        assert memory_increase < 50, f"Memory usage increased by {memory_increase:.2f}MB (too high)"
    
    def test_concurrent_template_creation(self, initialized_factory):
        """Test concurrent template creation and usage."""
        def create_and_format_message(template_type, test_data):
            """Helper function for concurrent execution."""
            try:
                template = initialized_factory.create_template(template_type)
                message = template.format_message(test_data)
                return {"success": True, "message_size": len(json.dumps(message.blocks))}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Prepare test data for concurrent execution
        concurrent_tasks = []
        for i in range(20):
            concurrent_tasks.append((
                TemplateType.STANDUP,
                {
                    "date": f"2024-01-{i % 30 + 1:02d}",
                    "team": f"Concurrent Team {i}",
                    "team_members": [{"name": f"user_{i}", "yesterday": "Work", "today": "More work", "blockers": []}],
                    "stats": {"prs_merged": i % 5}
                }
            ))
        
        # Execute concurrently
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_task = {
                executor.submit(create_and_format_message, template_type, test_data): i
                for i, (template_type, test_data) in enumerate(concurrent_tasks)
            }
            
            for future in as_completed(future_to_task):
                result = future.result()
                results.append(result)
        
        # Validate all concurrent operations succeeded
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        assert len(failed_results) == 0, f"Concurrent execution failures: {failed_results}"
        assert len(successful_results) == len(concurrent_tasks)
        
        # Validate message sizes are reasonable
        for result in successful_results:
            assert result["message_size"] > 100, "Message too small"
            assert result["message_size"] < 50000, "Message too large"
    
    def test_error_recovery_and_resilience(self, initialized_factory):
        """Test system resilience and error recovery capabilities."""
        error_scenarios = [
            {
                "name": "Malformed Data",
                "template_type": TemplateType.STANDUP,
                "data": {"invalid": "data", "structure": None}
            },
            {
                "name": "Missing Required Fields",
                "template_type": TemplateType.PR_NEW,
                "data": {}
            },
            {
                "name": "Extremely Large Data",
                "template_type": TemplateType.JIRA_STATUS,
                "data": {
                    "ticket": {
                        "key": "LARGE-1",
                        "summary": "x" * 10000,  # Very long summary
                        "status": "In Progress"
                    },
                    "from_status": "To Do",
                    "to_status": "In Progress"
                }
            }
        ]
        
        resilience_results = {
            "scenarios_tested": 0,
            "graceful_failures": 0,
            "unexpected_failures": []
        }
        
        for scenario in error_scenarios:
            try:
                template = initialized_factory.create_template(scenario["template_type"])
                message = template.format_message(scenario["data"])
                
                # Should handle gracefully and produce a valid message
                assert message.blocks is not None
                assert len(message.blocks) > 0
                assert message.text is not None
                
                resilience_results["graceful_failures"] += 1
                
            except Exception as e:
                # Unexpected failure
                resilience_results["unexpected_failures"].append({
                    "scenario": scenario["name"],
                    "error": str(e)
                })
            
            resilience_results["scenarios_tested"] += 1
        
        # System should handle all error scenarios gracefully
        assert len(resilience_results["unexpected_failures"]) == 0, f"Unexpected failures: {resilience_results['unexpected_failures']}"
        assert resilience_results["graceful_failures"] == resilience_results["scenarios_tested"]
    
    def _validate_accessibility_compliance(self, message: Any) -> Dict[str, Any]:
        """Validate accessibility compliance of a message."""
        issues = []
        
        # Check for fallback text
        if not message.text or len(message.text.strip()) == 0:
            issues.append("Missing or empty fallback text")
        
        # Check for reasonable text length
        if message.text and len(message.text) < 10:
            issues.append("Fallback text too short")
        
        # Check blocks structure
        if not message.blocks or len(message.blocks) == 0:
            issues.append("Missing message blocks")
        
        # Check for accessibility-friendly content
        message_json = json.dumps(message.blocks)
        
        # Should not have excessive emoji in accessibility mode
        emoji_count = sum(1 for char in message_json if ord(char) > 127)
        if emoji_count > 50:  # Reasonable threshold
            issues.append(f"Too many emoji/special characters: {emoji_count}")
        
        return {
            "is_compliant": len(issues) == 0,
            "issues": issues
        }
    
    def _run_load_test_scenario(self, factory, config, scenario):
        """Run a load test scenario and return performance metrics."""
        def execute_template_operation():
            """Execute a single template operation."""
            start_time = time.time()
            try:
                test_data = scenario["data_generator"]()
                template = factory.create_template(scenario["template_type"], config)
                message = template.format_message(test_data)
                
                execution_time = time.time() - start_time
                return {"success": True, "execution_time": execution_time, "message_size": len(json.dumps(message.blocks))}
            except Exception as e:
                execution_time = time.time() - start_time
                return {"success": False, "execution_time": execution_time, "error": str(e)}
        
        # Execute concurrent operations
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=min(scenario["concurrent_requests"], 20)) as executor:
            futures = [executor.submit(execute_template_operation) for _ in range(scenario["concurrent_requests"])]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        total_time = time.time() - start_time
        
        # Calculate metrics
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        execution_times = [r["execution_time"] for r in successful_results]
        
        return {
            "total_requests": len(results),
            "successful_requests": len(successful_results),
            "failed_requests": len(failed_results),
            "success_rate": len(successful_results) / len(results) if results else 0,
            "total_time": total_time,
            "average_response_time": sum(execution_times) / len(execution_times) if execution_times else 0,
            "min_response_time": min(execution_times) if execution_times else 0,
            "max_response_time": max(execution_times) if execution_times else 0,
            "requests_per_second": len(results) / total_time if total_time > 0 else 0
        }
    
    def _generate_standup_data(self):
        """Generate realistic standup data for load testing."""
        import random
        
        team_members = []
        for i in range(random.randint(3, 8)):
            member = {
                "name": f"user_{random.randint(1, 100)}",
                "yesterday": f"Completed task {random.randint(1, 50)}",
                "today": f"Working on task {random.randint(1, 50)}",
                "blockers": []
            }
            
            if random.random() < 0.2:  # 20% chance of blocker
                member["blockers"] = [f"Blocked by issue {random.randint(1, 20)}"]
            
            team_members.append(member)
        
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "team": f"Team {random.randint(1, 10)}",
            "team_members": team_members,
            "stats": {
                "prs_merged": random.randint(0, 10),
                "prs_open": random.randint(0, 15),
                "tickets_closed": random.randint(0, 20),
                "commits": random.randint(0, 50)
            },
            "sprint_progress": {
                "completed": random.randint(1, 15),
                "total": random.randint(10, 20)
            }
        }
    
    def _generate_pr_data(self):
        """Generate realistic PR data for load testing."""
        import random
        
        return {
            "pr": {
                "number": random.randint(1, 1000),
                "title": f"Feature implementation {random.randint(1, 100)}",
                "html_url": f"https://github.com/company/repo/pull/{random.randint(1, 1000)}",
                "user": {"login": f"user_{random.randint(1, 50)}"},
                "head": {"ref": f"feature/branch_{random.randint(1, 100)}"},
                "base": {"ref": "main"},
                "reviewers": [
                    {"login": f"reviewer_{random.randint(1, 20)}", "review_status": "pending"}
                    for _ in range(random.randint(1, 3))
                ]
            }
        }
    
    def _generate_alert_data(self):
        """Generate realistic alert data for load testing."""
        import random
        
        severities = ["low", "medium", "high", "critical"]
        alert_types = ["build_failure", "deployment_issue", "service_outage", "critical_bug"]
        
        return {
            "alert": {
                "id": f"alert_{random.randint(1, 10000)}",
                "title": f"System Alert {random.randint(1, 100)}",
                "description": f"Alert description {random.randint(1, 100)}",
                "severity": random.choice(severities),
                "type": random.choice(alert_types),
                "affected_systems": [f"system_{i}" for i in range(random.randint(1, 5))]
            },
            "build_info": {
                "branch": random.choice(["main", "develop", f"feature/branch_{random.randint(1, 50)}"]),
                "commit": f"{''.join(random.choices('abcdef0123456789', k=7))}",
                "failed_stage": random.choice(["build", "test", "deploy", "lint"])
            }
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])