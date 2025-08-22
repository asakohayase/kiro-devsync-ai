# Comprehensive End-to-End Test Framework

This directory contains the comprehensive test framework for JIRA to Slack Agent Hooks, providing end-to-end testing capabilities from webhook simulation to notification delivery.

## Framework Components

### Core Components

#### `webhook_simulator.py`
- **JiraWebhookSimulator**: Generates realistic JIRA webhook events for testing
- **MockDataGenerator**: Creates mock data for enriched events and configurations
- **EndToEndTestRunner**: Orchestrates complete flow testing from webhook to notification
- **WebhookSimulationResult**: Data structure for test results

#### `performance_testing.py`
- **PerformanceTestRunner**: Executes performance and load tests
- **StressTestRunner**: Finds system breaking points and tests resilience
- **LoadTestConfig**: Configuration for load testing parameters
- **PerformanceMetrics**: Comprehensive performance measurement data

#### `test_utilities.py`
- **MockDataFactory**: Factory for creating realistic test data
- **TestScenarioGenerator**: Generates comprehensive test scenarios
- **MockServiceFactory**: Creates mock external services
- **TestDataValidator**: Validates test data integrity
- **TestReportGenerator**: Generates formatted test reports

#### `hook_test_suite.py`
- **HookTestSuite**: Base test suite for individual hook testing
- Provides utilities for testing hook execution, validation, and integration

## Test Types

### 1. Scenario-Based Tests
Tests predefined scenarios that cover common use cases:

- **Status Change Scenarios**: High priority changes, blocked tickets, critical transitions
- **Assignment Scenarios**: Normal assignments, overloaded users, workload warnings
- **Comment Scenarios**: High priority comments, blocker comments
- **Multi-Team Scenarios**: Cross-team notifications, team-specific filtering

### 2. Performance Tests
Measures system performance under various loads:

- **Webhook Processing**: Tests webhook event processing speed and throughput
- **Hook Execution**: Measures individual hook execution performance
- **Notification Delivery**: Tests notification formatting and delivery speed
- **End-to-End**: Complete flow performance from webhook to notification

### 3. Integration Tests
Validates integration with existing system components:

- **Enhanced Notification Handler**: Tests integration with notification processing
- **Slack Service**: Validates Slack API integration and message formatting
- **Database Integration**: Tests data persistence and retrieval
- **Analytics Engine**: Validates metrics collection and reporting

### 4. Stress Tests
Tests system limits and resilience:

- **Breaking Point Detection**: Finds maximum load capacity
- **Memory Leak Testing**: Detects memory usage issues over time
- **Sustained Load Testing**: Tests system stability under continuous load

## Usage

### Running All Tests
```bash
# Run comprehensive test suite
python scripts/run_comprehensive_tests.py --test-type all

# Run with verbose output
python scripts/run_comprehensive_tests.py --test-type all --verbose
```

### Running Specific Test Types
```bash
# Run only scenario tests
python scripts/run_comprehensive_tests.py --test-type scenarios

# Run only performance tests
python scripts/run_comprehensive_tests.py --test-type performance

# Run only integration tests
python scripts/run_comprehensive_tests.py --test-type integration

# Run only stress tests
python scripts/run_comprehensive_tests.py --test-type stress
```

### Quick Validation
```bash
# Run quick validation to ensure framework is working
python scripts/run_comprehensive_tests.py --quick-validation
```

### Using Pytest
```bash
# Run comprehensive tests with pytest
uv run pytest tests/test_comprehensive_end_to_end.py -v

# Run specific test classes
uv run pytest tests/test_end_to_end_comprehensive.py::TestEndToEndWebhookFlow -v
```

## Configuration

### Test Configuration File
The test framework uses `tests/config/comprehensive_test_config.yaml` for configuration:

```yaml
# Performance test settings
performance_tests:
  webhook_processing:
    total_requests: 100
    concurrent_users: 10
    expected_success_rate: 95.0

# Team configurations for testing
team_configurations:
  engineering:
    hooks:
      status_change:
        enabled: true
        channels: ["#eng-updates"]
```

### Environment Variables
Set these environment variables for testing:

```bash
export TEST_MODE=true
export MOCK_EXTERNAL_SERVICES=true
export LOG_LEVEL=INFO
```

## Test Data Generation

### Webhook Events
```python
from tests.framework.webhook_simulator import JiraWebhookSimulator

simulator = JiraWebhookSimulator()
webhook_event = simulator.generate_webhook_event(
    "issue_updated",
    **{"issue.fields.priority.name": "High"}
)
```

### Mock Data
```python
from tests.framework.test_utilities import MockDataFactory

# Create mock JIRA ticket
ticket = MockDataFactory.create_jira_ticket(
    status="In Progress",
    priority="High"
)

# Create mock enriched event
event = MockDataFactory.create_enriched_event(
    event_type="STATUS_CHANGE"
)
```

### Test Scenarios
```python
from tests.framework.test_utilities import TestScenarioGenerator

# Get all predefined scenarios
scenarios = TestScenarioGenerator.get_all_scenarios()

# Get specific scenario types
status_scenarios = TestScenarioGenerator.create_status_change_scenarios()
```

## Performance Testing

### Load Testing
```python
from tests.framework.performance_testing import PerformanceTestRunner, LoadTestConfig

runner = PerformanceTestRunner()
config = LoadTestConfig(
    total_requests=100,
    concurrent_users=10,
    ramp_up_time_seconds=5
)

metrics = await runner.webhook_processing_load_test(config)
```

### Stress Testing
```python
from tests.framework.performance_testing import StressTestRunner

stress_runner = StressTestRunner()

# Find breaking point
breaking_point = await stress_runner.find_breaking_point(
    test_function,
    initial_load=10,
    max_load=1000
)

# Test for memory leaks
memory_test = await stress_runner.memory_leak_test(
    test_function,
    iterations=10
)
```

## Results and Reporting

### Test Results
Test results are automatically saved to `tests/results/` with timestamps:

```
tests/results/
├── comprehensive_test_results_20240816_143022.json
├── performance_metrics_20240816_143022.json
└── test_report_20240816_143022.html
```

### Result Structure
```json
{
  "start_time": "2024-08-16T14:30:22",
  "scenario_tests": [...],
  "performance_tests": {...},
  "integration_tests": [...],
  "stress_tests": {...},
  "summary": {
    "overall_success_rate": 85.5,
    "total_scenarios": 12,
    "successful_scenarios": 10
  }
}
```

## Extending the Framework

### Adding New Test Scenarios
1. Create scenario in `TestScenarioGenerator`
2. Define webhook events and expected results
3. Add team configurations if needed
4. Include success criteria

### Adding New Performance Tests
1. Create test function in `PerformanceTestRunner`
2. Define load test configuration
3. Add metrics collection
4. Include in comprehensive test suite

### Adding New Mock Services
1. Create mock in `MockServiceFactory`
2. Configure realistic responses and delays
3. Add error simulation if needed
4. Integrate with test scenarios

## Best Practices

### Test Design
- Use realistic data that matches production patterns
- Include edge cases and error scenarios
- Test both success and failure paths
- Validate integration points thoroughly

### Performance Testing
- Start with light loads and gradually increase
- Monitor system resources during tests
- Include realistic delays and error rates
- Test sustained load over time

### Mock Services
- Simulate realistic response times
- Include appropriate error rates
- Test timeout and retry scenarios
- Validate service interactions

### Result Analysis
- Set appropriate success criteria
- Monitor trends over time
- Investigate performance regressions
- Document known issues and limitations

## Troubleshooting

### Common Issues

#### Test Failures
- Check mock service configurations
- Verify test data validity
- Review error logs for details
- Ensure proper cleanup between tests

#### Performance Issues
- Monitor system resources
- Check for memory leaks
- Verify concurrent execution limits
- Review database connection pooling

#### Integration Problems
- Validate service mocking
- Check API compatibility
- Verify configuration settings
- Test service dependencies

### Debug Mode
Enable debug logging for detailed troubleshooting:

```bash
python scripts/run_comprehensive_tests.py --verbose
```

### Manual Testing
For manual testing and debugging:

```python
# Create test suite instance
from tests.test_comprehensive_end_to_end import ComprehensiveEndToEndTestSuite

suite = ComprehensiveEndToEndTestSuite()

# Run specific test type
results = await suite._run_scenario_tests()
```

## Contributing

When adding new tests or extending the framework:

1. Follow existing patterns and conventions
2. Add comprehensive documentation
3. Include both positive and negative test cases
4. Validate with the existing test suite
5. Update configuration files as needed
6. Add appropriate error handling and logging