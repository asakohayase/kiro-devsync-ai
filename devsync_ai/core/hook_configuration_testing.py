"""
Hook Configuration Testing and Validation Tools.

This module provides comprehensive testing utilities for hook configurations,
including syntax validation, rule testing, and configuration verification.
"""

import json
import yaml
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from copy import deepcopy

from devsync_ai.core.hook_configuration_validator import HookConfigurationValidator
from devsync_ai.core.hook_configuration_manager import ValidationResult
from devsync_ai.core.hook_rule_engine import HookRuleEngine
from devsync_ai.core.event_classification_engine import EventClassification, UrgencyLevel


logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Represents a configuration test case."""
    name: str
    description: str
    input_data: Dict[str, Any]
    expected_result: bool
    expected_errors: List[str]
    expected_warnings: List[str]
    test_type: str  # 'validation', 'rule_evaluation', 'integration'


@dataclass
class TestResult:
    """Result of a configuration test."""
    test_name: str
    passed: bool
    errors: List[str]
    warnings: List[str]
    details: Dict[str, Any]
    execution_time_ms: float


@dataclass
class TestSuiteResult:
    """Result of a complete test suite."""
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    test_results: List[TestResult]
    execution_time_ms: float
    summary: Dict[str, Any]


class ConfigurationTester:
    """
    Comprehensive testing framework for hook configurations.
    
    Provides validation testing, rule evaluation testing, and integration testing.
    """
    
    def __init__(self):
        """Initialize the configuration tester."""
        self.validator = HookConfigurationValidator()
        self.rule_engine = HookRuleEngine()
        self._test_cases = self._load_default_test_cases()
    
    def _load_default_test_cases(self) -> List[TestCase]:
        """Load default test cases for configuration validation."""
        return [
            # Basic validation tests
            TestCase(
                name="valid_basic_config",
                description="Test valid basic configuration",
                input_data={
                    "team_id": "test-team",
                    "team_name": "Test Team",
                    "enabled": True,
                    "version": "1.2.0",
                    "default_channels": {
                        "status_change": "#dev-updates",
                        "assignment": "#assignments",
                        "comment": "#discussions"
                    },
                    "rules": [
                        {
                            "rule_id": "high_priority_rule",
                            "name": "High Priority Notifications",
                            "hook_types": ["StatusChangeHook", "AssignmentHook"],
                            "enabled": True,
                            "priority": 10,
                            "conditions": {
                                "logic": "and",
                                "conditions": [
                                    {
                                        "field": "ticket.priority.name",
                                        "operator": "in",
                                        "value": ["High", "Critical"]
                                    }
                                ]
                            },
                            "metadata": {
                                "channels": ["#critical-alerts"],
                                "urgency_override": "high"
                            }
                        }
                    ]
                },
                expected_result=True,
                expected_errors=[],
                expected_warnings=[],
                test_type="validation"
            ),
            
            TestCase(
                name="missing_required_fields",
                description="Test configuration with missing required fields",
                input_data={
                    "team_name": "Test Team",
                    "enabled": True
                    # Missing team_id, default_channels, rules
                },
                expected_result=False,
                expected_errors=[
                    "Missing required field: team_id",
                    "Missing required field: default_channels",
                    "Missing required field: rules"
                ],
                expected_warnings=[],
                test_type="validation"
            ),
            
            TestCase(
                name="invalid_rule_syntax",
                description="Test configuration with invalid rule syntax",
                input_data={
                    "team_id": "test-team",
                    "team_name": "Test Team",
                    "enabled": True,
                    "default_channels": {"general": "#general"},
                    "rules": [
                        {
                            "rule_id": "invalid_rule",
                            "name": "Invalid Rule",
                            "hook_types": ["InvalidHookType"],  # Invalid hook type
                            "conditions": {
                                "logic": "invalid_logic",  # Invalid logic
                                "conditions": [
                                    {
                                        "field": "invalid.field",  # Invalid field
                                        "operator": "invalid_operator",  # Invalid operator
                                        "value": "test"
                                    }
                                ]
                            }
                        }
                    ]
                },
                expected_result=False,
                expected_errors=[
                    "Invalid hook type 'InvalidHookType'",
                    "Logic must be 'and' or 'or', got 'invalid_logic'",
                    "Invalid operator 'invalid_operator'"
                ],
                expected_warnings=[
                    "Unknown field 'invalid.field'"
                ],
                test_type="validation"
            ),
            
            TestCase(
                name="regex_validation",
                description="Test regex pattern validation",
                input_data={
                    "team_id": "test-team",
                    "team_name": "Test Team",
                    "enabled": True,
                    "default_channels": {"general": "#general"},
                    "rules": [
                        {
                            "rule_id": "regex_rule",
                            "name": "Regex Rule",
                            "hook_types": ["StatusChangeHook"],
                            "conditions": {
                                "logic": "and",
                                "conditions": [
                                    {
                                        "field": "ticket.summary",
                                        "operator": "regex",
                                        "value": "[invalid regex pattern"  # Invalid regex
                                    }
                                ]
                            }
                        }
                    ]
                },
                expected_result=False,
                expected_errors=["Invalid regex pattern"],
                expected_warnings=[],
                test_type="validation"
            )
        ]
    
    async def run_validation_tests(
        self, 
        config_data: Dict[str, Any],
        custom_test_cases: Optional[List[TestCase]] = None
    ) -> TestSuiteResult:
        """
        Run validation tests on configuration data.
        
        Args:
            config_data: Configuration to test
            custom_test_cases: Optional custom test cases
            
        Returns:
            TestSuiteResult with validation test results
        """
        start_time = datetime.utcnow()
        test_cases = custom_test_cases or [tc for tc in self._test_cases if tc.test_type == "validation"]
        test_results = []
        
        for test_case in test_cases:
            test_start = datetime.utcnow()
            
            try:
                # Run validation
                validation_result = await self.validator.validate_team_configuration_schema(
                    test_case.input_data
                )
                
                # Check results
                passed = self._check_validation_result(
                    validation_result, 
                    test_case.expected_result,
                    test_case.expected_errors,
                    test_case.expected_warnings
                )
                
                test_end = datetime.utcnow()
                execution_time = (test_end - test_start).total_seconds() * 1000
                
                test_results.append(TestResult(
                    test_name=test_case.name,
                    passed=passed,
                    errors=validation_result.errors if not passed else [],
                    warnings=validation_result.warnings,
                    details={
                        "description": test_case.description,
                        "expected_result": test_case.expected_result,
                        "actual_result": validation_result.valid,
                        "validation_result": {
                            "valid": validation_result.valid,
                            "errors": validation_result.errors,
                            "warnings": validation_result.warnings,
                            "suggestions": validation_result.suggestions
                        }
                    },
                    execution_time_ms=execution_time
                ))
                
            except Exception as e:
                test_end = datetime.utcnow()
                execution_time = (test_end - test_start).total_seconds() * 1000
                
                test_results.append(TestResult(
                    test_name=test_case.name,
                    passed=False,
                    errors=[f"Test execution failed: {e}"],
                    warnings=[],
                    details={"description": test_case.description, "exception": str(e)},
                    execution_time_ms=execution_time
                ))
        
        end_time = datetime.utcnow()
        total_execution_time = (end_time - start_time).total_seconds() * 1000
        
        passed_tests = sum(1 for result in test_results if result.passed)
        failed_tests = len(test_results) - passed_tests
        
        return TestSuiteResult(
            suite_name="Configuration Validation Tests",
            total_tests=len(test_results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            test_results=test_results,
            execution_time_ms=total_execution_time,
            summary={
                "pass_rate": (passed_tests / len(test_results)) * 100 if test_results else 0,
                "average_execution_time": total_execution_time / len(test_results) if test_results else 0,
                "test_categories": {"validation": len(test_results)}
            }
        )
    
    def _check_validation_result(
        self,
        result: ValidationResult,
        expected_valid: bool,
        expected_errors: List[str],
        expected_warnings: List[str]
    ) -> bool:
        """Check if validation result matches expectations."""
        # Check validity
        if result.valid != expected_valid:
            return False
        
        # Check errors (partial matching)
        for expected_error in expected_errors:
            if not any(expected_error in error for error in result.errors):
                return False
        
        # Check warnings (partial matching)
        for expected_warning in expected_warnings:
            if not any(expected_warning in warning for warning in result.warnings):
                return False
        
        return True
    
    async def run_rule_evaluation_tests(
        self, 
        config_data: Dict[str, Any]
    ) -> TestSuiteResult:
        """
        Run rule evaluation tests.
        
        Args:
            config_data: Configuration with rules to test
            
        Returns:
            TestSuiteResult with rule evaluation results
        """
        start_time = datetime.utcnow()
        test_results = []
        
        # Create test events
        test_events = self._create_test_events()
        
        rules = config_data.get("rules", [])
        team_id = config_data.get("team_id", "test")
        
        for i, rule in enumerate(rules):
            for j, test_event in enumerate(test_events):
                test_name = f"rule_{i+1}_event_{j+1}"
                test_start = datetime.utcnow()
                
                try:
                    # Evaluate rule against test event
                    evaluation_result = await self.rule_engine.evaluate_rules(
                        test_event, team_id
                    )
                    
                    test_end = datetime.utcnow()
                    execution_time = (test_end - test_start).total_seconds() * 1000
                    
                    test_results.append(TestResult(
                        test_name=test_name,
                        passed=True,  # Rule evaluation tests are informational
                        errors=[],
                        warnings=[],
                        details={
                            "rule_id": rule.get("rule_id", f"rule_{i+1}"),
                            "rule_name": rule.get("name", "Unnamed Rule"),
                            "event_type": test_event.category,
                            "evaluation_result": {
                                "matched": evaluation_result.matched,
                                "actions": evaluation_result.actions,
                                "metadata": evaluation_result.metadata
                            }
                        },
                        execution_time_ms=execution_time
                    ))
                    
                except Exception as e:
                    test_end = datetime.utcnow()
                    execution_time = (test_end - test_start).total_seconds() * 1000
                    
                    test_results.append(TestResult(
                        test_name=test_name,
                        passed=False,
                        errors=[f"Rule evaluation failed: {e}"],
                        warnings=[],
                        details={
                            "rule_id": rule.get("rule_id", f"rule_{i+1}"),
                            "exception": str(e)
                        },
                        execution_time_ms=execution_time
                    ))
        
        end_time = datetime.utcnow()
        total_execution_time = (end_time - start_time).total_seconds() * 1000
        
        passed_tests = sum(1 for result in test_results if result.passed)
        failed_tests = len(test_results) - passed_tests
        
        return TestSuiteResult(
            suite_name="Rule Evaluation Tests",
            total_tests=len(test_results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            test_results=test_results,
            execution_time_ms=total_execution_time,
            summary={
                "pass_rate": (passed_tests / len(test_results)) * 100 if test_results else 0,
                "average_execution_time": total_execution_time / len(test_results) if test_results else 0,
                "rules_tested": len(rules),
                "events_tested": len(test_events)
            }
        )
    
    def _create_test_events(self) -> List[EventClassification]:
        """Create test events for rule evaluation."""
        return [
            EventClassification(
                category="status_change",
                urgency=UrgencyLevel.HIGH,
                significance="major",
                affected_teams=["engineering"],
                routing_hints={"priority": "High", "status_change": "To Do -> In Progress"}
            ),
            EventClassification(
                category="blocker",
                urgency=UrgencyLevel.CRITICAL,
                significance="critical",
                affected_teams=["engineering", "qa"],
                routing_hints={"priority": "Critical", "blocked": True}
            ),
            EventClassification(
                category="assignment",
                urgency=UrgencyLevel.MEDIUM,
                significance="moderate",
                affected_teams=["engineering"],
                routing_hints={"assignee": "john.doe", "workload": "high"}
            ),
            EventClassification(
                category="comment",
                urgency=UrgencyLevel.LOW,
                significance="minor",
                affected_teams=["engineering"],
                routing_hints={"comment_type": "general", "priority": "Low"}
            )
        ]
    
    async def run_comprehensive_test_suite(
        self, 
        config_data: Dict[str, Any]
    ) -> Dict[str, TestSuiteResult]:
        """
        Run comprehensive test suite including all test types.
        
        Args:
            config_data: Configuration to test
            
        Returns:
            Dictionary of test suite results by type
        """
        results = {}
        
        # Run validation tests
        validation_results = await self.run_validation_tests(config_data)
        results["validation"] = validation_results
        
        # Run rule evaluation tests (only if validation passes)
        if validation_results.failed_tests == 0:
            rule_results = await self.run_rule_evaluation_tests(config_data)
            results["rule_evaluation"] = rule_results
        
        return results
    
    def generate_test_report(
        self, 
        test_results: Dict[str, TestSuiteResult],
        output_format: str = "yaml"
    ) -> str:
        """
        Generate a comprehensive test report.
        
        Args:
            test_results: Test results to include in report
            output_format: Output format ('yaml', 'json', 'markdown')
            
        Returns:
            Formatted test report
        """
        report_data = {
            "test_report": {
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_suites": len(test_results),
                    "total_tests": sum(suite.total_tests for suite in test_results.values()),
                    "total_passed": sum(suite.passed_tests for suite in test_results.values()),
                    "total_failed": sum(suite.failed_tests for suite in test_results.values()),
                    "overall_pass_rate": 0
                },
                "suites": {}
            }
        }
        
        # Calculate overall pass rate
        total_tests = report_data["test_report"]["summary"]["total_tests"]
        total_passed = report_data["test_report"]["summary"]["total_passed"]
        if total_tests > 0:
            report_data["test_report"]["summary"]["overall_pass_rate"] = (total_passed / total_tests) * 100
        
        # Add suite details
        for suite_name, suite_result in test_results.items():
            report_data["test_report"]["suites"][suite_name] = {
                "total_tests": suite_result.total_tests,
                "passed_tests": suite_result.passed_tests,
                "failed_tests": suite_result.failed_tests,
                "execution_time_ms": suite_result.execution_time_ms,
                "summary": suite_result.summary,
                "test_results": [
                    {
                        "test_name": result.test_name,
                        "passed": result.passed,
                        "errors": result.errors,
                        "warnings": result.warnings,
                        "execution_time_ms": result.execution_time_ms,
                        "details": result.details
                    }
                    for result in suite_result.test_results
                ]
            }
        
        # Format output
        if output_format == "json":
            return json.dumps(report_data, indent=2, default=str)
        elif output_format == "markdown":
            return self._format_markdown_report(report_data)
        else:  # yaml
            return yaml.dump(report_data, default_flow_style=False, sort_keys=False)
    
    def _format_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """Format test report as Markdown."""
        report = report_data["test_report"]
        summary = report["summary"]
        
        md = f"""# Hook Configuration Test Report

Generated: {report['generated_at']}

## Summary

- **Total Test Suites**: {summary['total_suites']}
- **Total Tests**: {summary['total_tests']}
- **Passed**: {summary['total_passed']}
- **Failed**: {summary['total_failed']}
- **Pass Rate**: {summary['overall_pass_rate']:.1f}%

"""
        
        # Add suite details
        for suite_name, suite_data in report["suites"].items():
            md += f"""## {suite_name.replace('_', ' ').title()}

- **Tests**: {suite_data['total_tests']}
- **Passed**: {suite_data['passed_tests']}
- **Failed**: {suite_data['failed_tests']}
- **Execution Time**: {suite_data['execution_time_ms']:.1f}ms

"""
            
            # Add failed tests details
            failed_tests = [t for t in suite_data["test_results"] if not t["passed"]]
            if failed_tests:
                md += "### Failed Tests\n\n"
                for test in failed_tests:
                    md += f"#### {test['test_name']}\n\n"
                    if test["errors"]:
                        md += "**Errors:**\n"
                        for error in test["errors"]:
                            md += f"- {error}\n"
                        md += "\n"
                    if test["warnings"]:
                        md += "**Warnings:**\n"
                        for warning in test["warnings"]:
                            md += f"- {warning}\n"
                        md += "\n"
        
        return md


class ConfigurationValidator:
    """High-level configuration validation interface."""
    
    def __init__(self):
        """Initialize the validator."""
        self.tester = ConfigurationTester()
        self.validator = HookConfigurationValidator()
    
    async def validate_configuration_file(
        self, 
        config_path: str,
        output_format: str = "yaml"
    ) -> Tuple[bool, str]:
        """
        Validate a configuration file and return results.
        
        Args:
            config_path: Path to configuration file
            output_format: Output format for results
            
        Returns:
            Tuple of (is_valid, report)
        """
        try:
            # Load configuration
            config_file = Path(config_path)
            if not config_file.exists():
                return False, f"Configuration file not found: {config_path}"
            
            with open(config_file, 'r') as f:
                if config_path.endswith('.json'):
                    config_data = json.load(f)
                else:
                    config_data = yaml.safe_load(f)
            
            # Run comprehensive tests
            test_results = await self.tester.run_comprehensive_test_suite(config_data)
            
            # Generate report
            report = self.tester.generate_test_report(test_results, output_format)
            
            # Determine overall validity
            is_valid = all(suite.failed_tests == 0 for suite in test_results.values())
            
            return is_valid, report
            
        except Exception as e:
            return False, f"Validation failed: {e}"
    
    async def validate_configuration_syntax(
        self, 
        config_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate configuration syntax only.
        
        Args:
            config_data: Configuration data to validate
            
        Returns:
            ValidationResult with syntax validation details
        """
        return await self.validator.validate_team_configuration_schema(config_data)
    
    def get_validation_help(self) -> Dict[str, Any]:
        """Get validation help and documentation."""
        return self.validator.get_validation_help()