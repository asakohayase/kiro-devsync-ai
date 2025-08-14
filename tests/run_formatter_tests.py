#!/usr/bin/env python3
"""Test runner for comprehensive message formatter tests."""

import sys
import time
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append('.')

def run_test_suite():
    """Run the comprehensive test suite."""
    print("🚀 Message Formatter Comprehensive Test Suite")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Import and run the comprehensive tests
        from tests.test_message_formatter_comprehensive import run_comprehensive_tests
        
        start_time = time.time()
        success = run_comprehensive_tests()
        end_time = time.time()
        
        print(f"\n⏱️ Total execution time: {end_time - start_time:.2f} seconds")
        
        if success:
            print("\n🎉 All tests passed! Message formatter system is working perfectly!")
            print("\n💡 Key Features Tested:")
            print("  ✅ Unit tests for all formatter classes")
            print("  ✅ Integration tests with Slack Block Kit validation")
            print("  ✅ Error handling and fallback mechanisms")
            print("  ✅ Performance tests with large datasets")
            print("  ✅ Visual regression tests for message consistency")
            print("  ✅ Malformed data injection testing")
            print("  ✅ Memory usage and scalability testing")
            print("  ✅ Concurrent processing validation")
            print("  ✅ Caching system performance impact")
            print("  ✅ A/B testing functionality")
            
            return True
        else:
            print("\n⚠️ Some tests failed. Please review the output above.")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import test modules: {e}")
        print("Make sure all required dependencies are installed.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error running tests: {e}")
        return False


def run_quick_smoke_tests():
    """Run quick smoke tests to verify basic functionality."""
    print("🔥 Quick Smoke Tests")
    print("=" * 30)
    
    try:
        # Test basic imports
        from devsync_ai.core.formatter_factory import SlackMessageFormatterFactory, MessageType
        from devsync_ai.formatters.pr_message_formatter import PRMessageFormatter
        from devsync_ai.formatters.jira_message_formatter import JIRAMessageFormatter
        
        print("✅ All imports successful")
        
        # Test basic formatter creation
        factory = SlackMessageFormatterFactory()
        pr_formatter = PRMessageFormatter()
        jira_formatter = JIRAMessageFormatter()
        
        print("✅ Formatter instances created")
        
        # Test basic message formatting
        pr_data = {
            "pr": {
                "number": 123,
                "title": "Test PR",
                "author": "test-user"
            }
        }
        
        result = factory.format_message(MessageType.PR_UPDATE, pr_data)
        if result.success and result.message:
            print("✅ Basic PR message formatting works")
        else:
            print(f"❌ PR message formatting failed: {result.error}")
            return False
        
        # Test metrics
        metrics = factory.get_metrics()
        if 'total_messages' in metrics:
            print("✅ Metrics collection works")
        else:
            print("❌ Metrics collection failed")
            return False
        
        print("\n🎉 All smoke tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        return False


def generate_test_report():
    """Generate a detailed test report."""
    print("\n📊 Generating Test Report")
    print("=" * 30)
    
    try:
        from tests.test_message_formatter_comprehensive import TestDataBuilder
        from devsync_ai.core.formatter_factory import SlackMessageFormatterFactory, MessageType
        
        factory = SlackMessageFormatterFactory()
        
        # Test different message types
        test_cases = [
            ("PR Update", MessageType.PR_UPDATE, TestDataBuilder.complete_pr_data()),
            ("JIRA Update", MessageType.JIRA_UPDATE, TestDataBuilder.complete_jira_data()),
            ("Standup", MessageType.STANDUP, TestDataBuilder.complete_standup_data()),
            ("Blocker", MessageType.BLOCKER, TestDataBuilder.complete_blocker_data())
        ]
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_results": []
        }
        
        for name, message_type, data in test_cases:
            start_time = time.time()
            result = factory.format_message(message_type, data)
            end_time = time.time()
            
            test_result = {
                "name": name,
                "success": result.success,
                "processing_time_ms": (end_time - start_time) * 1000,
                "cache_hit": result.cache_hit,
                "block_count": len(result.message.blocks) if result.message else 0,
                "error": result.error
            }
            
            report["test_results"].append(test_result)
            
            status = "✅" if result.success else "❌"
            print(f"{status} {name}: {test_result['processing_time_ms']:.2f}ms, {test_result['block_count']} blocks")
        
        # Get overall metrics
        metrics = factory.get_metrics()
        report["metrics"] = metrics
        
        print(f"\n📈 Overall Metrics:")
        print(f"   Total messages: {metrics.get('total_messages', 0)}")
        print(f"   Cache hit rate: {metrics.get('cache_hit_rate', 0):.1f}%")
        print(f"   Average processing time: {metrics.get('avg_processing_time_ms', 0):.2f}ms")
        
        # Save report
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate report: {e}")
        return False


def main():
    """Main test runner."""
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = "full"
    
    if mode == "smoke":
        success = run_quick_smoke_tests()
    elif mode == "report":
        success = generate_test_report()
    elif mode == "full":
        # Run smoke tests first
        print("Running smoke tests first...\n")
        if not run_quick_smoke_tests():
            print("\n❌ Smoke tests failed. Skipping comprehensive tests.")
            return False
        
        print("\n" + "="*60)
        success = run_test_suite()
        
        if success:
            print("\nGenerating test report...")
            generate_test_report()
    else:
        print("Usage: python run_formatter_tests.py [smoke|report|full]")
        print("  smoke: Run quick smoke tests only")
        print("  report: Generate test report only")
        print("  full: Run all tests and generate report (default)")
        return False
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)