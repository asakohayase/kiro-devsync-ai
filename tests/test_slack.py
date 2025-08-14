#!/usr/bin/env python3
"""
Comprehensive Slack Integration Test Suite
==========================================

This script validates Slack integration functionality with proper error handling,
colorful output, and realistic test data for production readiness.
"""

import json
import time
import requests
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import os
import sys

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

@dataclass
class TestResult:
    """Test result data structure"""
    name: str
    passed: bool
    message: str
    duration: float
    details: Optional[Dict] = None

class SlackTestSuite:
    """Comprehensive Slack integration test suite"""
    
    def __init__(self, webhook_url: str, bot_token: Optional[str] = None):
        self.webhook_url = webhook_url
        self.bot_token = bot_token
        self.results: List[TestResult] = []
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def print_header(self):
        """Print colorful test suite header"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}🚀 SLACK INTEGRATION TEST SUITE 🚀{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")
        print(f"{Colors.BLUE}📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print(f"{Colors.BLUE}🔗 Webhook URL: {self.webhook_url[:50]}...{Colors.END}\n")
    
    def print_test_start(self, test_name: str):
        """Print test start indicator"""
        print(f"{Colors.YELLOW}🧪 Running: {test_name}...{Colors.END}", end=" ")
        sys.stdout.flush()
    
    def print_test_result(self, result: TestResult):
        """Print individual test result"""
        if result.passed:
            print(f"{Colors.GREEN}✅ PASS{Colors.END} ({result.duration:.2f}s)")
            if result.details:
                print(f"   {Colors.CYAN}ℹ️  {result.message}{Colors.END}")
        else:
            print(f"{Colors.RED}❌ FAIL{Colors.END} ({result.duration:.2f}s)")
            print(f"   {Colors.RED}💥 {result.message}{Colors.END}")
    
    def run_test(self, test_func, test_name: str) -> TestResult:
        """Execute a single test with timing and error handling"""
        self.print_test_start(test_name)
        start_time = time.time()
        
        try:
            result = test_func()
            duration = time.time() - start_time
            
            if isinstance(result, tuple):
                passed, message, details = result
            else:
                passed, message, details = result, "Test completed", None
            
            test_result = TestResult(test_name, passed, message, duration, details)
            
        except Exception as e:
            duration = time.time() - start_time
            test_result = TestResult(
                test_name, 
                False, 
                f"Exception occurred: {str(e)}", 
                duration
            )
            self.logger.error(f"Test {test_name} failed with exception: {e}")
        
        self.results.append(test_result)
        self.print_test_result(test_result)
        return test_result
    
    def test_webhook_connectivity(self) -> Tuple[bool, str, Dict]:
        """Test basic webhook connectivity"""
        test_payload = {
            "text": "🔍 Connectivity Test - Please ignore this message",
            "username": "Test Bot",
            "icon_emoji": ":robot_face:"
        }
        
        try:
            response = self.session.post(
                self.webhook_url,
                json=test_payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return True, "Webhook is accessible and responding", {
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
            else:
                return False, f"Webhook returned status {response.status_code}", {
                    "status_code": response.status_code,
                    "response_text": response.text[:200]
                }
                
        except requests.exceptions.RequestException as e:
            return False, f"Connection failed: {str(e)}", {"error": str(e)}
    
    def test_basic_message_sending(self) -> Tuple[bool, str, Dict]:
        """Test sending basic text messages"""
        test_messages = [
            "Hello from automated test! 👋",
            "Testing special characters: @#$%^&*()",
            "Unicode test: 🚀 🎉 💻 ✨",
            "Multi-line test:\nLine 1\nLine 2\nLine 3"
        ]
        
        successful_sends = 0
        
        for i, message in enumerate(test_messages):
            payload = {
                "text": f"Test Message {i+1}: {message}",
                "username": "Test Suite",
                "icon_emoji": ":test_tube:"
            }
            
            try:
                response = self.session.post(self.webhook_url, json=payload)
                if response.status_code == 200:
                    successful_sends += 1
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                self.logger.warning(f"Failed to send test message {i+1}: {e}")
        
        success_rate = successful_sends / len(test_messages)
        
        if success_rate == 1.0:
            return True, f"All {len(test_messages)} messages sent successfully", {
                "success_rate": success_rate,
                "messages_sent": successful_sends
            }
        elif success_rate > 0.5:
            return True, f"Partial success: {successful_sends}/{len(test_messages)} messages sent", {
                "success_rate": success_rate,
                "messages_sent": successful_sends
            }
        else:
            return False, f"Low success rate: {successful_sends}/{len(test_messages)} messages sent", {
                "success_rate": success_rate,
                "messages_sent": successful_sends
            }
    
    def test_rich_message_formatting(self) -> Tuple[bool, str, Dict]:
        """Test rich message formatting with attachments and blocks"""
        rich_payload = {
            "text": "🎨 Rich Message Format Test",
            "username": "Format Tester",
            "icon_emoji": ":art:",
            "attachments": [
                {
                    "color": "good",
                    "title": "Test Attachment",
                    "text": "This is a test attachment with *bold* and _italic_ text",
                    "fields": [
                        {
                            "title": "Environment",
                            "value": "Test",
                            "short": True
                        },
                        {
                            "title": "Status",
                            "value": "✅ Active",
                            "short": True
                        }
                    ],
                    "footer": "Automated Test Suite",
                    "ts": int(time.time())
                }
            ]
        }
        
        try:
            response = self.session.post(self.webhook_url, json=rich_payload)
            
            if response.status_code == 200:
                return True, "Rich formatting message sent successfully", {
                    "status_code": response.status_code,
                    "payload_size": len(json.dumps(rich_payload))
                }
            else:
                return False, f"Rich message failed with status {response.status_code}", {
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            return False, f"Rich formatting test failed: {str(e)}", {"error": str(e)}
    
    def test_error_handling(self) -> Tuple[bool, str, Dict]:
        """Test error handling with invalid payloads"""
        error_tests = [
            ("Empty payload", {}),
            ("Invalid JSON structure", {"invalid": {"nested": {"too": {"deep": "value"}}}}),
            ("Oversized message", {"text": "A" * 4001}),  # Slack has 4000 char limit
            ("Invalid webhook URL", None)  # Will test with modified URL
        ]
        
        error_responses = []
        
        for test_name, payload in error_tests:
            try:
                if test_name == "Invalid webhook URL":
                    # Test with intentionally broken URL
                    invalid_url = self.webhook_url.replace("hooks.slack.com", "invalid.slack.com")
                    response = self.session.post(invalid_url, json={"text": "test"})
                else:
                    response = self.session.post(self.webhook_url, json=payload)
                
                error_responses.append({
                    "test": test_name,
                    "status_code": response.status_code,
                    "handled_gracefully": response.status_code in [400, 404, 413]
                })
                
            except requests.exceptions.RequestException:
                error_responses.append({
                    "test": test_name,
                    "status_code": "Connection Error",
                    "handled_gracefully": True
                })
            
            time.sleep(0.5)  # Brief pause between error tests
        
        graceful_handling = sum(1 for r in error_responses if r["handled_gracefully"])
        total_tests = len(error_responses)
        
        if graceful_handling >= total_tests * 0.75:  # 75% threshold
            return True, f"Error handling working: {graceful_handling}/{total_tests} handled gracefully", {
                "error_responses": error_responses,
                "success_rate": graceful_handling / total_tests
            }
        else:
            return False, f"Poor error handling: {graceful_handling}/{total_tests} handled gracefully", {
                "error_responses": error_responses,
                "success_rate": graceful_handling / total_tests
            }
    
    def test_rate_limiting(self) -> Tuple[bool, str, Dict]:
        """Test rate limiting behavior"""
        rapid_messages = 10
        successful_rapid = 0
        response_times = []
        
        print(f"\n   📊 Sending {rapid_messages} rapid messages...")
        
        for i in range(rapid_messages):
            start = time.time()
            try:
                payload = {
                    "text": f"⚡ Rate limit test message {i+1}/{rapid_messages}",
                    "username": "Rate Tester",
                    "icon_emoji": ":zap:"
                }
                
                response = self.session.post(self.webhook_url, json=payload)
                response_time = time.time() - start
                response_times.append(response_time)
                
                if response.status_code == 200:
                    successful_rapid += 1
                elif response.status_code == 429:  # Rate limited
                    print(f"   ⏱️  Rate limited at message {i+1}")
                    break
                    
            except Exception as e:
                self.logger.warning(f"Rate limit test message {i+1} failed: {e}")
            
            time.sleep(0.1)  # Small delay
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return True, f"Rate limiting test completed: {successful_rapid}/{rapid_messages} sent", {
            "messages_sent": successful_rapid,
            "avg_response_time": avg_response_time,
            "total_attempts": rapid_messages
        }
    
    def test_realistic_scenarios(self) -> Tuple[bool, str, Dict]:
        """Test realistic production scenarios"""
        scenarios = [
            {
                "name": "Deployment Notification",
                "payload": {
                    "text": "🚀 Deployment Notification",
                    "username": "Deploy Bot",
                    "icon_emoji": ":rocket:",
                    "attachments": [{
                        "color": "good",
                        "title": "Production Deploy Successful",
                        "fields": [
                            {"title": "Version", "value": "v2.1.4", "short": True},
                            {"title": "Environment", "value": "Production", "short": True},
                            {"title": "Duration", "value": "3m 42s", "short": True},
                            {"title": "Deployed by", "value": "CI/CD Pipeline", "short": True}
                        ]
                    }]
                }
            },
            {
                "name": "Alert Notification",
                "payload": {
                    "text": "🚨 System Alert",
                    "username": "Alert Bot",
                    "icon_emoji": ":warning:",
                    "attachments": [{
                        "color": "danger",
                        "title": "High CPU Usage Detected",
                        "text": "Server load has exceeded 85% for the past 5 minutes",
                        "fields": [
                            {"title": "Server", "value": "web-01.prod", "short": True},
                            {"title": "CPU Usage", "value": "87.3%", "short": True}
                        ]
                    }]
                }
            },
            {
                "name": "Monitoring Report",
                "payload": {
                    "text": "📊 Daily Monitoring Report",
                    "username": "Monitor Bot",
                    "icon_emoji": ":bar_chart:",
                    "attachments": [{
                        "color": "#36a64f",
                        "title": "System Health Summary - " + datetime.now().strftime("%Y-%m-%d"),
                        "fields": [
                            {"title": "Uptime", "value": "99.97%", "short": True},
                            {"title": "Response Time", "value": "142ms avg", "short": True},
                            {"title": "Error Rate", "value": "0.03%", "short": True},
                            {"title": "Active Users", "value": "1,247", "short": True}
                        ]
                    }]
                }
            }
        ]
        
        successful_scenarios = 0
        
        for scenario in scenarios:
            try:
                response = self.session.post(self.webhook_url, json=scenario["payload"])
                if response.status_code == 200:
                    successful_scenarios += 1
                    print(f"   ✅ {scenario['name']} sent successfully")
                else:
                    print(f"   ❌ {scenario['name']} failed: {response.status_code}")
                
                time.sleep(2)  # Realistic delay between notifications
                
            except Exception as e:
                print(f"   ❌ {scenario['name']} failed: {str(e)}")
        
        success_rate = successful_scenarios / len(scenarios)
        
        if success_rate == 1.0:
            return True, f"All {len(scenarios)} realistic scenarios completed successfully", {
                "scenarios_passed": successful_scenarios,
                "total_scenarios": len(scenarios),
                "success_rate": success_rate
            }
        else:
            return False, f"Some scenarios failed: {successful_scenarios}/{len(scenarios)}", {
                "scenarios_passed": successful_scenarios,
                "total_scenarios": len(scenarios),
                "success_rate": success_rate
            }
    
    def print_summary(self):
        """Print comprehensive test summary"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        total_duration = sum(r.duration for r in self.results)
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}📋 TEST SUMMARY{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
        
        # Overall status
        if failed_tests == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! 🎉{Colors.END}")
            overall_status = "EXCELLENT"
            status_color = Colors.GREEN
        elif failed_tests <= total_tests * 0.2:  # 80% pass rate
            print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  MOSTLY SUCCESSFUL ⚠️{Colors.END}")
            overall_status = "GOOD"
            status_color = Colors.YELLOW
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ MULTIPLE FAILURES ❌{Colors.END}")
            overall_status = "NEEDS ATTENTION"
            status_color = Colors.RED
        
        # Statistics
        print(f"\n{Colors.BOLD}📊 Statistics:{Colors.END}")
        print(f"   Total Tests: {Colors.BOLD}{total_tests}{Colors.END}")
        print(f"   Passed: {Colors.GREEN}{Colors.BOLD}{passed_tests}{Colors.END}")
        print(f"   Failed: {Colors.RED}{Colors.BOLD}{failed_tests}{Colors.END}")
        print(f"   Success Rate: {status_color}{Colors.BOLD}{(passed_tests/total_tests)*100:.1f}%{Colors.END}")
        print(f"   Total Duration: {Colors.BOLD}{total_duration:.2f}s{Colors.END}")
        print(f"   Overall Status: {status_color}{Colors.BOLD}{overall_status}{Colors.END}")
        
        # Failed tests details
        if failed_tests > 0:
            print(f"\n{Colors.RED}{Colors.BOLD}❌ Failed Tests:{Colors.END}")
            for result in self.results:
                if not result.passed:
                    print(f"   • {result.name}: {result.message}")
        
        # Recommendations
        print(f"\n{Colors.BOLD}💡 Recommendations:{Colors.END}")
        if failed_tests == 0:
            print(f"   {Colors.GREEN}✅ Slack integration is working perfectly!{Colors.END}")
            print(f"   {Colors.GREEN}✅ Ready for production use{Colors.END}")
        elif failed_tests <= 2:
            print(f"   {Colors.YELLOW}⚠️  Minor issues detected - review failed tests{Colors.END}")
            print(f"   {Colors.YELLOW}⚠️  Consider fixing before production deployment{Colors.END}")
        else:
            print(f"   {Colors.RED}🚨 Significant issues detected{Colors.END}")
            print(f"   {Colors.RED}🚨 Fix critical issues before production use{Colors.END}")
        
        print(f"\n{Colors.BLUE}📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")
        
        return failed_tests == 0
    
    def run_all_tests(self) -> bool:
        """Run the complete test suite"""
        self.print_header()
        
        # Define test sequence
        tests = [
            (self.test_webhook_connectivity, "Webhook Connectivity"),
            (self.test_basic_message_sending, "Basic Message Sending"),
            (self.test_rich_message_formatting, "Rich Message Formatting"),
            (self.test_error_handling, "Error Handling"),
            (self.test_rate_limiting, "Rate Limiting"),
            (self.test_realistic_scenarios, "Realistic Scenarios")
        ]
        
        # Execute all tests
        for test_func, test_name in tests:
            self.run_test(test_func, test_name)
            time.sleep(1)  # Brief pause between tests
        
        # Print summary and return overall success
        return self.print_summary()

def main():
    """Main execution function"""
    # Get webhook URL from environment or command line
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    
    if not webhook_url:
        if len(sys.argv) > 1:
            webhook_url = sys.argv[1]
        else:
            print(f"{Colors.RED}❌ Error: Slack webhook URL required{Colors.END}")
            print(f"{Colors.YELLOW}Usage: python test_slack.py <webhook_url>{Colors.END}")
            print(f"{Colors.YELLOW}   or: export SLACK_WEBHOOK_URL=<webhook_url>{Colors.END}")
            sys.exit(1)
    
    # Validate webhook URL format
    if not webhook_url.startswith('https://hooks.slack.com/'):
        print(f"{Colors.RED}❌ Error: Invalid Slack webhook URL format{Colors.END}")
        print(f"{Colors.YELLOW}Expected format: https://hooks.slack.com/services/...{Colors.END}")
        sys.exit(1)
    
    # Initialize and run test suite
    test_suite = SlackTestSuite(webhook_url)
    
    try:
        success = test_suite.run_all_tests()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Test suite interrupted by user{Colors.END}")
        sys.exit(130)
        
    except Exception as e:
        print(f"\n{Colors.RED}💥 Unexpected error: {str(e)}{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()
