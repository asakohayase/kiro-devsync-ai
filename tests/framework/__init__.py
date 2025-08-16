"""
Comprehensive Testing Framework for JIRA Agent Hooks.

This package provides production-ready testing infrastructure with:
- Hook behavior testing suite
- Integration testing framework
- Performance and load testing
- Mock testing environment
- Development tools and debugging
- Automated testing pipeline
- Security and compliance testing
- Production readiness validation
"""

from .hook_test_suite import HookTestSuite
from .integration_test_framework import IntegrationTestFramework
from .load_test_runner import LoadTestRunner
from .mock_services import MockJIRAService, MockSlackService, MockDatabaseService
from .demo_testing_dashboard import DemoTestingDashboard
from .security_test_suite import SecurityTestSuite
from .production_readiness_validator import ProductionReadinessValidator

__all__ = [
    'HookTestSuite',
    'IntegrationTestFramework', 
    'LoadTestRunner',
    'MockJIRAService',
    'MockSlackService',
    'MockDatabaseService',
    'DemoTestingDashboard',
    'SecurityTestSuite',
    'ProductionReadinessValidator'
]