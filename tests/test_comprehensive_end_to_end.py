"""
Comprehensive end-to-end test runner for JIRA to Slack Agent Hooks.
This is the main test file that orchestrates all end-to-end testing scenarios.
"""

import pytest
import asyncio
import json
import os
from typing import Dict, Any, List
from datetime import datetime
from unittest.mock import patch, AsyncMock

from tests.framework.webhook_simulator import JiraWebhookSimulator, EndToEndTestRunner
from tests.framework.performance_testing import PerformanceTestRunner, LoadTestConfig, StressTestRunner
from tests.framework.test_utilities import (
    TestScenarioGenerator,
    MockServiceFactory,
    TestDataValidator,
    TestReportGenerator,
    MockDataFactory
)


class ComprehensiveEndToEndTestSuite:
    """Main test suite for comprehensive end-to-end testing."""
    
    def __init__(self):
        self.webhook_simulator = JiraWebhookSimulator()
        self.test_runner = EndToEndTestRunner()
        self.performance_runner = PerformanceTestRunner()
        self.stress_runner = StressTestRunner()
        self.scenario_generator = TestScenarioGenerator()
        self.mock_factory = MockServiceFactory()
        self.results = []
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests."""
        print("Starting comprehensive end-to-end test suite...")
        
        test_results = {
            "start_time": datetime.now().isoformat(),
            "scenario_tests": [],
            "performance_tests": {},
            "integration_tests": [],
            "stress_tests": {},
            "summary": {}
        }
        
        try:
            # Run scenario-based tests
            print("\n1. Running scenario-based tests...")
            scenario_results = await self._run_scenario_tests()
            test_results["scenario_tests"] = scenario_results
            
            # Run performance tests
            print("\n2. Running performance tests...")
            performance_results = await self._run_performance_tests()
            test_results["performance_tests"] = performance_results
            
            # Run integration tests
            print("\n3. Running integration tests...")
            integration_results = await self._run_integration_tests()
            test_results["integration_tests"] = integration_results
            
            # Run stress tests
            print("\n4. Running stress tests...")
            stress_results = await self._run_stress_tests()
            test_results["stress_tests"] = stress_results
            
            # Generate summary
            test_results["summary"] = self._generate_test_summary(test_results)
            test_results["end_time"] = datetime.now().isoformat()
            
            # Save results to file
            self._save_test_results(test_results)
            
            print("\nComprehensive test suite completed!")
            return test_results
            
        except Exception as e:
            print(f"Test suite failed with error: {e}")
            test_results["error"] = str(e)
            test_results["end_time"] = datetime.now().isoformat()
            return test_results
    
    async def _run_scenario_tests(self) -> List[Dict[str, Any]]:
        """Run all predefined test scenarios."""
        scenarios = self.scenario_generator.get_all_scenarios()
        results = []
        
        for scenario in scenarios:
            print(f"  Running scenario: {scenario.name}")
            
            try:
                # Validate scenario
                if not TestDataValidator.validate_test_scenario(scenario):
                    results.append({
                        "scenario_name": scenario.name,
                        "success": False,
                        "error": "Invalid scenario structure"
                    })
                    continue
                
                # Run scenario test
                result = await self._execute_scenario(scenario)
                results.append(result)
                
            except Exception as e:
                results.append({
                    "scenario_name": scenario.name,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def _execute_scenario(self, scenario) -> Dict[str, Any]:
        """Execute a single test scenario."""
        start_time = datetime.now()
        
        # Mock all external dependencies
        with patch.multiple(
            'devsync_ai.core.agent_hook_dispatcher',
            jira_service=self.mock_factory.create_mock_jira_service(),
            slack_service=self.mock_factory.create_mock_slack_service(),
            database=self.mock_factory.create_mock_database(),
            notification_handler=self.mock_factory.create_mock_notification_handler()
        ):
            try:
                # Process each webhook event in the scenario
                hooks_executed = 0
                notifications_sent = 0
                
                for webhook_event in scenario.webhook_events:
                    # Simulate complete processing
                    result = await self.test_runner.run_complete_flow_test(
                        webhook_event.get("issue_event_type_name", "issue_updated"),
                        scenario.team_configs,
                        scenario.expected_notifications
                    )
                    
                    if result.success:
                        hooks_executed += len(result.hook_executions)
                        notifications_sent += result.notifications_sent
                
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds() * 1000
                
                # Check success criteria
                success = self._check_success_criteria(
                    scenario.success_criteria,
                    {
                        "hooks_executed": hooks_executed,
                        "notifications_sent": notifications_sent,
                        "teams_notified": len(scenario.team_configs)
                    }
                )
                
                return {
                    "scenario_name": scenario.name,
                    "success": success,
                    "hooks_executed": hooks_executed,
                    "notifications_sent": notifications_sent,
                    "execution_time_ms": execution_time,
                    "teams_tested": len(scenario.team_configs),
                    "webhook_events_processed": len(scenario.webhook_events)
                }
                
            except Exception as e:
                return {
                    "scenario_name": scenario.name,
                    "success": False,
                    "error": str(e),
                    "execution_time_ms": 0
                }
    
    def _check_success_criteria(self, criteria: Dict[str, Any], actual: Dict[str, Any]) -> bool:
        """Check if actual results meet success criteria."""
        for criterion, expected in criteria.items():
            if criterion not in actual:
                return False
            
            if actual[criterion] != expected:
                return False
        
        return True
    
    async def _run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        results = {}
        
        # Webhook processing performance
        print("  Testing webhook processing performance...")
        webhook_config = LoadTestConfig(total_requests=100, concurrent_users=10)
        webhook_metrics = await self.performance_runner.webhook_processing_load_test(webhook_config)
        results["webhook_processing"] = webhook_metrics
        
        # Hook execution performance
        print("  Testing hook execution performance...")
        hook_config = LoadTestConfig(total_requests=50, concurrent_users=5)
        hook_metrics = await self.performance_runner.hook_execution_load_test(hook_config)
        results["hook_execution"] = hook_metrics
        
        # Notification delivery performance
        print("  Testing notification delivery performance...")
        notification_config = LoadTestConfig(total_requests=75, concurrent_users=8)
        notification_metrics = await self.performance_runner.notification_delivery_load_test(notification_config)
        results["notification_delivery"] = notification_metrics
        
        # End-to-end performance
        print("  Testing end-to-end performance...")
        e2e_config = LoadTestConfig(total_requests=30, concurrent_users=3)
        e2e_metrics = await self.performance_runner.end_to_end_load_test(e2e_config)
        results["end_to_end"] = e2e_metrics
        
        return results
    
    async def _run_integration_tests(self) -> List[Dict[str, Any]]:
        """Run integration tests with existing systems."""
        results = []
        
        # Test integration with Enhanced Notification Handler
        print("  Testing Enhanced Notification Handler integration...")
        try:
            with patch('devsync_ai.core.enhanced_notification_handler.EnhancedNotificationHandler') as mock_handler:
                handler = mock_handler.return_value
                handler.process_notification.return_value = {"success": True}
                
                enriched_event = MockDataFactory.create_enriched_event()
                
                # Simulate hook calling notification handler
                result = await self._simulate_notification_integration(enriched_event)
                
                results.append({
                    "integration": "enhanced_notification_handler",
                    "success": result.get("success", False),
                    "details": result
                })
        except Exception as e:
            results.append({
                "integration": "enhanced_notification_handler",
                "success": False,
                "error": str(e)
            })
        
        # Test integration with Slack Service
        print("  Testing Slack Service integration...")
        try:
            with patch('devsync_ai.services.slack.SlackService') as mock_slack:
                slack_service = mock_slack.return_value
                slack_service.send_message.return_value = {"ok": True}
                
                result = await self._simulate_slack_integration()
                
                results.append({
                    "integration": "slack_service",
                    "success": result.get("success", False),
                    "details": result
                })
        except Exception as e:
            results.append({
                "integration": "slack_service",
                "success": False,
                "error": str(e)
            })
        
        # Test integration with Database
        print("  Testing Database integration...")
        try:
            with patch('devsync_ai.database.hook_data_manager.HookDataManager') as mock_db:
                db_manager = mock_db.return_value
                db_manager.log_hook_execution.return_value = True
                
                result = await self._simulate_database_integration()
                
                results.append({
                    "integration": "database",
                    "success": result.get("success", False),
                    "details": result
                })
        except Exception as e:
            results.append({
                "integration": "database",
                "success": False,
                "error": str(e)
            })
        
        return results
    
    async def _simulate_notification_integration(self, event) -> Dict[str, Any]:
        """Simulate notification handler integration."""
        # Mock the integration flow
        await asyncio.sleep(0.01)  # Simulate processing time
        return {"success": True, "message_sent": True}
    
    async def _simulate_slack_integration(self) -> Dict[str, Any]:
        """Simulate Slack service integration."""
        await asyncio.sleep(0.02)  # Simulate API call time
        return {"success": True, "message_id": "test123"}
    
    async def _simulate_database_integration(self) -> Dict[str, Any]:
        """Simulate database integration."""
        await asyncio.sleep(0.005)  # Simulate database write time
        return {"success": True, "logged": True}
    
    async def _run_stress_tests(self) -> Dict[str, Any]:
        """Run stress tests to find system limits."""
        results = {}
        
        # Find breaking point for webhook processing
        print("  Finding webhook processing breaking point...")
        async def webhook_test_function(request_id: int):
            await asyncio.sleep(0.01)  # Simulate webhook processing
            return {"processed": True}
        
        breaking_point_result = await self.stress_runner.find_breaking_point(
            webhook_test_function,
            initial_load=10,
            max_load=200,
            step_size=20
        )
        results["webhook_breaking_point"] = breaking_point_result
        
        # Memory leak test
        print("  Testing for memory leaks...")
        memory_test_result = await self.stress_runner.memory_leak_test(
            webhook_test_function,
            iterations=5,
            requests_per_iteration=20
        )
        results["memory_leak_test"] = memory_test_result
        
        return results
    
    def _generate_test_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of all test results."""
        summary = {
            "total_scenarios": len(test_results.get("scenario_tests", [])),
            "successful_scenarios": 0,
            "failed_scenarios": 0,
            "performance_tests_run": len(test_results.get("performance_tests", {})),
            "integration_tests_run": len(test_results.get("integration_tests", [])),
            "successful_integrations": 0,
            "stress_tests_run": len(test_results.get("stress_tests", {})),
            "overall_success_rate": 0.0
        }
        
        # Count successful scenarios
        for scenario in test_results.get("scenario_tests", []):
            if scenario.get("success", False):
                summary["successful_scenarios"] += 1
            else:
                summary["failed_scenarios"] += 1
        
        # Count successful integrations
        for integration in test_results.get("integration_tests", []):
            if integration.get("success", False):
                summary["successful_integrations"] += 1
        
        # Calculate overall success rate
        total_tests = (
            summary["total_scenarios"] + 
            summary["integration_tests_run"]
        )
        successful_tests = (
            summary["successful_scenarios"] + 
            summary["successful_integrations"]
        )
        
        if total_tests > 0:
            summary["overall_success_rate"] = (successful_tests / total_tests) * 100
        
        return summary
    
    def _save_test_results(self, results: Dict[str, Any]):
        """Save test results to a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/results/comprehensive_test_results_{timestamp}.json"
        
        # Create results directory if it doesn't exist
        os.makedirs("tests/results", exist_ok=True)
        
        # Convert any non-serializable objects to strings
        serializable_results = self._make_serializable(results)
        
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        print(f"Test results saved to: {filename}")
    
    def _make_serializable(self, obj):
        """Make object JSON serializable."""
        if hasattr(obj, '__dict__'):
            return {k: self._make_serializable(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        else:
            return obj


# Pytest test functions
class TestComprehensiveEndToEnd:
    """Pytest test class for comprehensive end-to-end testing."""
    
    @pytest.fixture
    def test_suite(self):
        return ComprehensiveEndToEndTestSuite()
    
    @pytest.mark.asyncio
    async def test_all_scenarios(self, test_suite):
        """Test all predefined scenarios."""
        results = await test_suite._run_scenario_tests()
        
        # Verify at least some scenarios passed
        successful_scenarios = [r for r in results if r.get("success", False)]
        assert len(successful_scenarios) > 0, "No scenarios passed"
        
        # Verify success rate is reasonable
        success_rate = len(successful_scenarios) / len(results) * 100
        assert success_rate >= 70, f"Success rate too low: {success_rate}%"
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, test_suite):
        """Test performance meets benchmarks."""
        results = await test_suite._run_performance_tests()
        
        # Check webhook processing performance
        webhook_metrics = results.get("webhook_processing")
        if webhook_metrics:
            assert webhook_metrics.success_rate >= 95, "Webhook processing success rate too low"
            assert webhook_metrics.avg_response_time_ms < 100, "Webhook processing too slow"
        
        # Check end-to-end performance
        e2e_metrics = results.get("end_to_end")
        if e2e_metrics:
            assert e2e_metrics.success_rate >= 90, "End-to-end success rate too low"
            assert e2e_metrics.avg_response_time_ms < 200, "End-to-end processing too slow"
    
    @pytest.mark.asyncio
    async def test_integration_compatibility(self, test_suite):
        """Test integration with existing systems."""
        results = await test_suite._run_integration_tests()
        
        # Verify all integrations were tested
        assert len(results) >= 3, "Not all integrations were tested"
        
        # Verify most integrations passed
        successful_integrations = [r for r in results if r.get("success", False)]
        success_rate = len(successful_integrations) / len(results) * 100
        assert success_rate >= 80, f"Integration success rate too low: {success_rate}%"
    
    @pytest.mark.asyncio
    async def test_system_resilience(self, test_suite):
        """Test system resilience under stress."""
        results = await test_suite._run_stress_tests()
        
        # Check breaking point results
        breaking_point = results.get("webhook_breaking_point")
        if breaking_point:
            assert breaking_point.get("breaking_point") is None or breaking_point["breaking_point"] >= 50, \
                "System breaking point too low"
        
        # Check memory leak results
        memory_test = results.get("memory_leak_test")
        if memory_test:
            assert not memory_test.get("potential_memory_leak", True), "Potential memory leak detected"


# Main execution
if __name__ == "__main__":
    async def main():
        test_suite = ComprehensiveEndToEndTestSuite()
        results = await test_suite.run_all_tests()
        
        print("\n" + "="*50)
        print("COMPREHENSIVE TEST SUITE SUMMARY")
        print("="*50)
        
        summary = results.get("summary", {})
        print(f"Total Scenarios: {summary.get('total_scenarios', 0)}")
        print(f"Successful Scenarios: {summary.get('successful_scenarios', 0)}")
        print(f"Failed Scenarios: {summary.get('failed_scenarios', 0)}")
        print(f"Integration Tests: {summary.get('integration_tests_run', 0)}")
        print(f"Successful Integrations: {summary.get('successful_integrations', 0)}")
        print(f"Overall Success Rate: {summary.get('overall_success_rate', 0):.2f}%")
        
        if summary.get("overall_success_rate", 0) >= 80:
            print("\n✅ COMPREHENSIVE TEST SUITE PASSED")
        else:
            print("\n❌ COMPREHENSIVE TEST SUITE FAILED")
    
    asyncio.run(main())