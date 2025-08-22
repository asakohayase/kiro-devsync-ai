#!/usr/bin/env python3
"""
Script to run comprehensive end-to-end tests for JIRA to Slack Agent Hooks.
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.test_comprehensive_end_to_end import ComprehensiveEndToEndTestSuite
from tests.framework.performance_testing import LoadTestConfig


async def run_comprehensive_tests(args):
    """Run comprehensive tests based on command line arguments."""
    print("🚀 Starting Comprehensive End-to-End Test Suite")
    print("=" * 60)
    
    test_suite = ComprehensiveEndToEndTestSuite()
    
    if args.test_type == "all":
        print("Running all comprehensive tests...")
        results = await test_suite.run_all_tests()
        
    elif args.test_type == "scenarios":
        print("Running scenario-based tests only...")
        results = {
            "scenario_tests": await test_suite._run_scenario_tests(),
            "summary": {"test_type": "scenarios_only"}
        }
        
    elif args.test_type == "performance":
        print("Running performance tests only...")
        results = {
            "performance_tests": await test_suite._run_performance_tests(),
            "summary": {"test_type": "performance_only"}
        }
        
    elif args.test_type == "integration":
        print("Running integration tests only...")
        results = {
            "integration_tests": await test_suite._run_integration_tests(),
            "summary": {"test_type": "integration_only"}
        }
        
    elif args.test_type == "stress":
        print("Running stress tests only...")
        results = {
            "stress_tests": await test_suite._run_stress_tests(),
            "summary": {"test_type": "stress_only"}
        }
    
    else:
        print(f"Unknown test type: {args.test_type}")
        return 1
    
    # Print summary
    print_test_summary(results)
    
    # Determine exit code based on results
    if args.test_type == "all":
        summary = results.get("summary", {})
        success_rate = summary.get("overall_success_rate", 0)
        return 0 if success_rate >= args.min_success_rate else 1
    else:
        # For individual test types, just check if any tests ran successfully
        return 0


def print_test_summary(results):
    """Print a formatted test summary."""
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    if "scenario_tests" in results:
        scenario_tests = results["scenario_tests"]
        successful = sum(1 for t in scenario_tests if t.get("success", False))
        total = len(scenario_tests)
        print(f"Scenario Tests: {successful}/{total} passed ({successful/total*100:.1f}%)")
    
    if "performance_tests" in results:
        perf_tests = results["performance_tests"]
        print(f"Performance Tests: {len(perf_tests)} completed")
        
        for test_name, metrics in perf_tests.items():
            if hasattr(metrics, 'success_rate'):
                print(f"  - {test_name}: {metrics.success_rate:.1f}% success rate, "
                      f"{metrics.avg_response_time_ms:.1f}ms avg response time")
    
    if "integration_tests" in results:
        integration_tests = results["integration_tests"]
        successful = sum(1 for t in integration_tests if t.get("success", False))
        total = len(integration_tests)
        print(f"Integration Tests: {successful}/{total} passed ({successful/total*100:.1f}%)")
    
    if "stress_tests" in results:
        stress_tests = results["stress_tests"]
        print(f"Stress Tests: {len(stress_tests)} completed")
        
        if "webhook_breaking_point" in stress_tests:
            bp = stress_tests["webhook_breaking_point"]
            breaking_point = bp.get("breaking_point", "Not found")
            print(f"  - Webhook Breaking Point: {breaking_point}")
        
        if "memory_leak_test" in stress_tests:
            ml = stress_tests["memory_leak_test"]
            leak_detected = ml.get("potential_memory_leak", False)
            print(f"  - Memory Leak Detected: {'Yes' if leak_detected else 'No'}")
    
    if "summary" in results and "overall_success_rate" in results["summary"]:
        overall_rate = results["summary"]["overall_success_rate"]
        status = "✅ PASSED" if overall_rate >= 80 else "❌ FAILED"
        print(f"\nOverall Success Rate: {overall_rate:.1f}% {status}")


def run_quick_validation():
    """Run a quick validation test to ensure the system is working."""
    print("🔍 Running quick validation test...")
    
    try:
        from tests.framework.webhook_simulator import JiraWebhookSimulator
        from tests.framework.test_utilities import MockDataFactory, TestDataValidator
        
        # Test webhook simulation
        simulator = JiraWebhookSimulator()
        webhook_event = simulator.generate_webhook_event("issue_updated")
        
        if not TestDataValidator.validate_webhook_event(webhook_event):
            print("❌ Webhook simulation validation failed")
            return False
        
        # Test mock data generation
        mock_event = MockDataFactory.create_enriched_event()
        
        if not TestDataValidator.validate_enriched_event(mock_event):
            print("❌ Mock data generation validation failed")
            return False
        
        print("✅ Quick validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Quick validation failed: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive end-to-end tests for JIRA to Slack Agent Hooks"
    )
    
    parser.add_argument(
        "--test-type",
        choices=["all", "scenarios", "performance", "integration", "stress"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    
    parser.add_argument(
        "--min-success-rate",
        type=float,
        default=80.0,
        help="Minimum success rate for tests to pass (default: 80.0)"
    )
    
    parser.add_argument(
        "--quick-validation",
        action="store_true",
        help="Run quick validation test only"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    # Run quick validation if requested
    if args.quick_validation:
        success = run_quick_validation()
        return 0 if success else 1
    
    # Run comprehensive tests
    try:
        exit_code = asyncio.run(run_comprehensive_tests(args))
        return exit_code
        
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 130
        
    except Exception as e:
        print(f"❌ Test suite failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)