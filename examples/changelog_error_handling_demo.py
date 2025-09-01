"""
Demonstration of the Changelog Error Handling and Recovery System

This script shows how to use the comprehensive error handling system
for changelog generation, including circuit breakers, recovery workflows,
monitoring integration, and automated remediation.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from devsync_ai.core.changelog_error_handler import (
    ChangelogErrorHandler,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity
)
from devsync_ai.core.changelog_monitoring_integration import (
    ChangelogMonitoringIntegration,
    ChangelogMonitoringConfig
)
from devsync_ai.core.changelog_recovery_workflows import (
    ChangelogRecoveryWorkflowManager
)
from devsync_ai.core.exceptions import (
    DataCollectionError,
    FormattingError,
    DistributionError
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_basic_error_handling():
    """Demonstrate basic error handling capabilities"""
    print("\n=== Basic Error Handling Demo ===")
    
    # Create error handler
    error_handler = ChangelogErrorHandler()
    
    # Register fallback data source
    async def github_fallback():
        return {
            "commits": [
                {"sha": "abc123", "message": "Fallback commit", "author": "system"}
            ],
            "cached": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    error_handler.register_fallback_data_source("github", github_fallback)
    
    # Simulate GitHub API failure
    error = DataCollectionError("GitHub API rate limit exceeded")
    context = {
        "service": "github",
        "operation": "fetch_commits",
        "team_id": "demo_team",
        "repository": "demo/repo"
    }
    
    print(f"Simulating error: {error}")
    
    # Handle the error
    result = await error_handler.handle_error(error, context)
    
    print(f"Recovery result: {result.success}")
    print(f"Action taken: {result.action_taken.value}")
    print(f"Message: {result.message}")
    
    if result.fallback_data:
        print(f"Fallback data available: {result.fallback_data}")
    
    # Show error statistics
    stats = error_handler.get_error_statistics()
    print(f"\nError Statistics:")
    print(f"Total errors: {stats['total_errors']}")
    print(f"Errors by category: {stats['errors_by_category']}")


async def demo_circuit_breaker():
    """Demonstrate circuit breaker functionality"""
    print("\n=== Circuit Breaker Demo ===")
    
    error_handler = ChangelogErrorHandler()
    
    # Simulate multiple failures to trigger circuit breaker
    print("Simulating multiple GitHub API failures...")
    
    for i in range(6):  # Exceeds default threshold of 5
        error = DataCollectionError(f"GitHub API error {i + 1}")
        context = {
            "service": "github",
            "operation": "fetch_data",
            "team_id": "demo_team"
        }
        
        result = await error_handler.handle_error(error, context)
        print(f"Attempt {i + 1}: {result.action_taken.value}")
        
        # Check circuit breaker state
        breaker = error_handler.get_circuit_breaker("github")
        print(f"Circuit breaker state: {breaker.state.value}")
        
        if breaker.state.value == "open":
            print("Circuit breaker opened!")
            break
    
    # Try one more request - should be circuit broken
    print("\nTrying request with open circuit breaker...")
    final_error = DataCollectionError("Another GitHub error")
    final_result = await error_handler.handle_error(final_error, context)
    print(f"Final result: {final_result.action_taken.value}")
    print(f"Message: {final_result.message}")


async def demo_performance_monitoring():
    """Demonstrate performance monitoring"""
    print("\n=== Performance Monitoring Demo ===")
    
    error_handler = ChangelogErrorHandler()
    
    # Monitor a fast operation
    print("Monitoring fast operation...")
    async with error_handler.performance_monitor("fast_operation", "demo"):
        await asyncio.sleep(0.1)
    
    # Monitor a slow operation
    print("Monitoring slow operation...")
    async with error_handler.performance_monitor("slow_operation", "demo"):
        await asyncio.sleep(0.5)
    
    # Get performance statistics
    perf_stats = error_handler.get_performance_statistics()
    print(f"\nPerformance Statistics:")
    print(f"Total operations: {perf_stats['total_operations']}")
    print(f"Average duration: {perf_stats['average_duration']:.3f}s")
    print(f"Max duration: {perf_stats['max_duration']:.3f}s")
    print(f"Operations by type: {perf_stats['operations_by_type']}")


async def demo_recovery_workflows():
    """Demonstrate recovery workflows"""
    print("\n=== Recovery Workflows Demo ===")
    
    workflow_manager = ChangelogRecoveryWorkflowManager()
    
    # Test GitHub data collection workflow
    print("Testing GitHub data collection recovery workflow...")
    
    github_error = ErrorContext(
        error=DataCollectionError("GitHub API failed"),
        category=ErrorCategory.DATA_COLLECTION,
        severity=ErrorSeverity.HIGH,
        service="github",
        operation="fetch_commits",
        team_id="demo_team"
    )
    
    execution = await workflow_manager.execute_recovery(github_error)
    
    if execution:
        print(f"Workflow executed: {execution.workflow_id}")
        print(f"Status: {execution.status.value}")
        print(f"Completed steps: {len(execution.completed_steps)}")
        print(f"Failed steps: {len(execution.failed_steps)}")
        
        if execution.completed_steps:
            print(f"Successful steps: {execution.completed_steps}")
    else:
        print("No suitable workflow found")
    
    # Test Slack distribution workflow
    print("\nTesting Slack distribution recovery workflow...")
    
    slack_error = ErrorContext(
        error=DistributionError("Slack API failed"),
        category=ErrorCategory.DISTRIBUTION,
        severity=ErrorSeverity.HIGH,
        service="slack",
        operation="send_message",
        team_id="demo_team"
    )
    
    execution = await workflow_manager.execute_recovery(slack_error)
    
    if execution:
        print(f"Workflow executed: {execution.workflow_id}")
        print(f"Status: {execution.status.value}")
        print(f"Completed steps: {len(execution.completed_steps)}")
    
    # Show workflow statistics
    stats = workflow_manager.get_workflow_statistics()
    print(f"\nWorkflow Statistics:")
    print(f"Total executions: {stats['total_executions']}")
    print(f"Success rate: {stats['success_rate']:.1f}%")
    print(f"Registered workflows: {stats['registered_workflows']}")


async def demo_monitoring_integration():
    """Demonstrate monitoring integration"""
    print("\n=== Monitoring Integration Demo ===")
    
    # Create monitoring configuration
    config = ChangelogMonitoringConfig(
        enable_real_time_monitoring=True,
        enable_alerting=True,
        enable_analytics=True,
        alert_channels=["#demo-alerts"],
        monitoring_interval_seconds=1,  # Short interval for demo
        error_threshold_percentage=10.0
    )
    
    # Create monitoring integration
    monitoring = ChangelogMonitoringIntegration(config=config)
    
    # Register fallback data source
    async def demo_fallback():
        return {"demo": True, "cached_data": "fallback"}
    
    monitoring.register_fallback_data_source("demo_service", demo_fallback)
    
    # Simulate some errors
    print("Simulating errors with monitoring...")
    
    errors = [
        (DataCollectionError("Demo error 1"), {"service": "demo_service", "operation": "test1"}),
        (FormattingError("Demo error 2"), {"service": "formatter", "operation": "test2"}),
        (DistributionError("Demo error 3"), {"service": "slack", "operation": "test3"})
    ]
    
    for error, context in errors:
        result = await monitoring.handle_changelog_error(error, context)
        print(f"Handled {type(error).__name__}: {result.success}")
    
    # Get dashboard data
    dashboard_data = await monitoring.get_monitoring_dashboard_data()
    print(f"\nDashboard Status: {dashboard_data['status']}")
    
    health_data = dashboard_data.get('health_data', {})
    error_stats = health_data.get('error_statistics', {})
    print(f"Total errors tracked: {error_stats.get('total_errors', 0)}")
    
    if error_stats.get('errors_by_category'):
        print(f"Errors by category: {error_stats['errors_by_category']}")


async def demo_optimization_recommendations():
    """Demonstrate optimization recommendations"""
    print("\n=== Optimization Recommendations Demo ===")
    
    error_handler = ChangelogErrorHandler()
    
    # Create scenario that will generate recommendations
    print("Creating high error rate scenario...")
    
    # Add many errors to trigger recommendations
    for i in range(15):
        error_context = ErrorContext(
            error=DataCollectionError(f"Simulated error {i}"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.HIGH,
            service="github",
            operation="fetch_commits"
        )
        error_handler.error_history.append(error_context)
    
    # Add performance metrics with failures
    from devsync_ai.core.changelog_error_handler import PerformanceMetrics
    for i in range(10):
        metric = PerformanceMetrics(
            operation="slow_operation",
            duration=200 if i % 2 == 0 else 1,  # Some slow operations
            success=i % 3 != 0  # Some failures
        )
        error_handler.performance_metrics.append(metric)
    
    # Get recommendations
    recommendations = error_handler.get_optimization_recommendations()
    
    print(f"\nGenerated {len(recommendations)} optimization recommendations:")
    
    for rec in recommendations:
        print(f"\n- Type: {rec['type']}")
        print(f"  Priority: {rec['priority']}")
        print(f"  Description: {rec['description']}")
        print(f"  Recommendation: {rec['recommendation']}")


async def demo_health_check():
    """Demonstrate comprehensive health check"""
    print("\n=== Health Check Demo ===")
    
    error_handler = ChangelogErrorHandler()
    
    # Add some test data
    error_handler.error_history.append(
        ErrorContext(
            error=DataCollectionError("Test error"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.MEDIUM,
            service="github",
            operation="test"
        )
    )
    
    from devsync_ai.core.changelog_error_handler import PerformanceMetrics
    error_handler.performance_metrics.append(
        PerformanceMetrics("test_operation", 1.5, success=True)
    )
    
    # Create circuit breaker
    error_handler.get_circuit_breaker("test_service")
    
    # Perform health check
    health = await error_handler.health_check()
    
    print(f"System Status: {health['status']}")
    print(f"Last Updated: {health['timestamp']}")
    
    # Error statistics
    error_stats = health['error_statistics']
    print(f"\nError Statistics:")
    print(f"  Total errors: {error_stats['total_errors']}")
    print(f"  Error rate: {error_stats.get('error_rate', 0):.1f}%")
    
    # Performance statistics
    perf_stats = health['performance_statistics']
    print(f"\nPerformance Statistics:")
    print(f"  Total operations: {perf_stats['total_operations']}")
    print(f"  Success rate: {perf_stats['successful_operations'] / perf_stats['total_operations'] * 100:.1f}%")
    
    # Circuit breakers
    circuit_breakers = health['circuit_breakers']
    print(f"\nCircuit Breakers:")
    for service, state in circuit_breakers.items():
        print(f"  {service}: {state['state']}")
    
    # System metrics
    sys_metrics = health['system_metrics']
    print(f"\nSystem Metrics:")
    print(f"  Errors tracked: {sys_metrics['total_errors_tracked']}")
    print(f"  Performance metrics: {sys_metrics['total_performance_metrics']}")
    print(f"  Active circuit breakers: {sys_metrics['active_circuit_breakers']}")
    
    # Recommendations
    recommendations = health['optimization_recommendations']
    if recommendations:
        print(f"\nOptimization Recommendations: {len(recommendations)}")
        for rec in recommendations[:3]:  # Show first 3
            print(f"  - {rec['type']}: {rec['description']}")


async def main():
    """Run all demonstrations"""
    print("Changelog Error Handling and Recovery System Demo")
    print("=" * 50)
    
    try:
        await demo_basic_error_handling()
        await demo_circuit_breaker()
        await demo_performance_monitoring()
        await demo_recovery_workflows()
        await demo_monitoring_integration()
        await demo_optimization_recommendations()
        await demo_health_check()
        
        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())