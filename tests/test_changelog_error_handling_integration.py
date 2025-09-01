"""
Integration tests for the complete Changelog Error Handling system.

Tests the full integration between error handler, monitoring, recovery workflows,
and the existing DevSync AI infrastructure.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from devsync_ai.core.changelog_error_handler import (
    ChangelogErrorHandler,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    RecoveryResult,
    RecoveryAction,
    CircuitBreakerState
)
from devsync_ai.core.changelog_monitoring_integration import (
    ChangelogMonitoringIntegration,
    ChangelogMonitoringConfig
)
from devsync_ai.core.changelog_recovery_workflows import (
    ChangelogRecoveryWorkflowManager,
    WorkflowStatus
)
from devsync_ai.core.exceptions import (
    DataCollectionError,
    FormattingError,
    DistributionError
)


class TestCompleteErrorHandlingIntegration:
    """Test complete error handling system integration"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_github_failure_recovery(self):
        """Test complete end-to-end GitHub failure and recovery"""
        # Setup monitoring callbacks
        monitoring_callback = AsyncMock()
        alerting_callback = AsyncMock()
        
        # Create integrated error handling system
        config = ChangelogMonitoringConfig(
            enable_real_time_monitoring=True,
            enable_alerting=True,
            enable_analytics=True,
            alert_channels=["#test-alerts"]
        )
        
        monitoring_integration = ChangelogMonitoringIntegration(
            config=config,
            monitoring_data_manager=Mock(),
            real_time_monitor=Mock(),
            alerting_system=Mock()
        )
        
        # Register fallback data source
        async def github_fallback():
            return {
                "commits": [
                    {"sha": "abc123", "message": "Test commit", "author": "test_user"}
                ],
                "pull_requests": [],
                "cached": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        monitoring_integration.error_handler.register_fallback_data_source("github", github_fallback)
        
        # Simulate GitHub API failure
        error = DataCollectionError("GitHub API rate limit exceeded: 5000 requests per hour")
        context = {
            "service": "github",
            "operation": "fetch_weekly_commits",
            "team_id": "engineering",
            "user_id": "changelog_bot",
            "request_id": "req_12345",
            "repository": "company/main-app",
            "date_range": "2024-01-01 to 2024-01-07"
        }
        
        # Handle the error
        recovery_result = await monitoring_integration.handle_changelog_error(error, context)
        
        # Verify recovery was successful
        assert recovery_result.success is True
        assert recovery_result.action_taken in [RecoveryAction.RETRY, RecoveryAction.FALLBACK]
        assert recovery_result.fallback_data is not None
        
        # Verify error was logged and tracked
        error_handler = monitoring_integration.error_handler
        assert len(error_handler.error_history) == 1
        
        logged_error = error_handler.error_history[0]
        assert logged_error.category == ErrorCategory.DATA_COLLECTION
        assert logged_error.service == "github"
        assert logged_error.team_id == "engineering"
        assert logged_error.severity == ErrorSeverity.HIGH
        
        # Verify monitoring callbacks were called
        assert monitoring_integration.error_handler.monitoring_callback is not None
        assert monitoring_integration.error_handler.alerting_callback is not None
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker integration with recovery workflows"""
        error_handler = ChangelogErrorHandler()
        workflow_manager = ChangelogRecoveryWorkflowManager()
        
        # Simulate multiple GitHub failures to trigger circuit breaker
        github_errors = [
            DataCollectionError(f"GitHub API error {i}")
            for i in range(6)  # Exceeds default threshold of 5
        ]
        
        context = {
            "service": "github",
            "operation": "fetch_commits",
            "team_id": "engineering"
        }
        
        results = []
        for error in github_errors:
            result = await error_handler.handle_error(error, context)
            results.append(result)
        
        # Verify circuit breaker is now open
        github_breaker = error_handler.get_circuit_breaker("github")
        assert github_breaker.state == CircuitBreakerState.OPEN
        
        # Try to execute recovery workflow - should be circuit broken
        error_context = ErrorContext(
            error=DataCollectionError("Another GitHub error"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.HIGH,
            service="github",
            operation="fetch_commits"
        )
        
        final_result = await error_handler.handle_error(
            DataCollectionError("Circuit breaker test"), 
            context
        )
        
        assert final_result.action_taken == RecoveryAction.CIRCUIT_BREAK
        assert final_result.escalation_required is True
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(self):
        """Test performance monitoring integration"""
        alerting_callback = AsyncMock()
        error_handler = ChangelogErrorHandler(alerting_callback=alerting_callback)
        
        # Test performance monitoring context manager
        async with error_handler.performance_monitor("changelog_generation", "changelog"):
            # Simulate changelog generation work
            await asyncio.sleep(0.01)
        
        # Verify performance metric was recorded
        assert len(error_handler.performance_metrics) == 1
        metric = error_handler.performance_metrics[0]
        assert metric.operation == "changelog_generation"
        assert metric.success is True
        assert metric.duration > 0
        
        # Test performance threshold alerting
        # Manually trigger a threshold violation
        from devsync_ai.core.changelog_error_handler import PerformanceMetrics
        
        slow_metric = PerformanceMetrics(
            operation="slow_changelog_generation",
            duration=200,  # Exceeds 180 second threshold
            success=True
        )
        
        await error_handler._check_performance_thresholds(slow_metric)
        
        # Should have triggered performance alert
        alerting_callback.assert_called_once()
        alert_data = alerting_callback.call_args[0][0]
        assert alert_data["type"] == "performance_threshold_exceeded"
        assert alert_data["metric"] == "generation_time"
    
    @pytest.mark.asyncio
    async def test_multi_service_failure_scenario(self):
        """Test handling multiple service failures simultaneously"""
        monitoring_integration = ChangelogMonitoringIntegration()
        
        # Register fallback sources
        async def github_fallback():
            return {"commits": [], "cached": True}
        
        async def jira_fallback():
            return {"issues": [], "cached": True}
        
        monitoring_integration.register_fallback_data_source("github", github_fallback)
        monitoring_integration.register_fallback_data_source("jira", jira_fallback)
        
        # Simulate multiple service failures
        errors_and_contexts = [
            (
                DataCollectionError("GitHub API failed"),
                {
                    "service": "github",
                    "operation": "fetch_commits",
                    "team_id": "engineering"
                }
            ),
            (
                DataCollectionError("JIRA API failed"),
                {
                    "service": "jira",
                    "operation": "fetch_issues",
                    "team_id": "engineering"
                }
            ),
            (
                DistributionError("Slack API failed"),
                {
                    "service": "slack",
                    "operation": "send_message",
                    "team_id": "engineering"
                }
            )
        ]
        
        # Handle all errors concurrently
        tasks = [
            monitoring_integration.handle_changelog_error(error, context)
            for error, context in errors_and_contexts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all errors were handled
        assert len(results) == 3
        
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Error handling failed: {result}")
            assert isinstance(result, RecoveryResult)
            # At least some should succeed due to fallbacks
        
        # Verify error statistics
        error_handler = monitoring_integration.error_handler
        stats = error_handler.get_error_statistics()
        
        assert stats["total_errors"] == 3
        assert "data_collection" in stats["errors_by_category"]
        assert "distribution" in stats["errors_by_category"]
    
    @pytest.mark.asyncio
    async def test_escalation_workflow_integration(self):
        """Test escalation workflow integration"""
        # Mock escalation notification
        with patch('devsync_ai.core.changelog_recovery_workflows.ChangelogRecoveryWorkflowManager._send_escalation_notification') as mock_escalation:
            workflow_manager = ChangelogRecoveryWorkflowManager()
            
            # Create critical error that should escalate
            error_context = ErrorContext(
                error=DataCollectionError("Critical system failure"),
                category=ErrorCategory.DATA_COLLECTION,
                severity=ErrorSeverity.CRITICAL,
                service="github",
                operation="fetch_commits",
                team_id="engineering"
            )
            
            # Mock workflow to force escalation
            original_workflows = workflow_manager.workflows.copy()
            
            # Create a workflow that will fail and escalate
            class FailingWorkflow:
                def __init__(self):
                    self.workflow_id = "failing_workflow"
                    self.name = "Failing Workflow"
                
                def can_handle(self, error_context):
                    return error_context.service == "github"
                
                async def execute(self, error_context):
                    from devsync_ai.core.changelog_recovery_workflows import WorkflowExecution, WorkflowStatus, EscalationLevel
                    
                    execution = WorkflowExecution(
                        workflow_id=self.workflow_id,
                        error_context=error_context,
                        status=WorkflowStatus.ESCALATED,
                        escalation_level=EscalationLevel.INCIDENT_RESPONSE,
                        started_at=datetime.utcnow(),
                        completed_at=datetime.utcnow()
                    )
                    return execution
            
            workflow_manager.workflows = [FailingWorkflow()]
            
            # Execute recovery
            execution = await workflow_manager.execute_recovery(error_context)
            
            # Verify escalation occurred
            assert execution.status == WorkflowStatus.ESCALATED
            assert execution.escalation_level.value == "incident_response"
            
            # Verify escalation notification was sent
            mock_escalation.assert_called_once()
            
            # Restore original workflows
            workflow_manager.workflows = original_workflows
    
    @pytest.mark.asyncio
    async def test_monitoring_dashboard_data_integration(self):
        """Test monitoring dashboard data integration"""
        monitoring_integration = ChangelogMonitoringIntegration()
        
        # Add some test data
        error_handler = monitoring_integration.error_handler
        
        # Add error history
        error_handler.error_history.append(
            ErrorContext(
                error=DataCollectionError("Test error"),
                category=ErrorCategory.DATA_COLLECTION,
                severity=ErrorSeverity.MEDIUM,
                service="github",
                operation="fetch_commits"
            )
        )
        
        # Add performance metrics
        from devsync_ai.core.changelog_error_handler import PerformanceMetrics
        error_handler.performance_metrics.append(
            PerformanceMetrics("test_operation", 1.5, success=True)
        )
        
        # Get dashboard data
        dashboard_data = await monitoring_integration.get_monitoring_dashboard_data()
        
        # Verify dashboard data structure
        assert "status" in dashboard_data
        assert "last_updated" in dashboard_data
        assert "health_data" in dashboard_data
        assert "optimization_recommendations" in dashboard_data
        assert "monitoring_config" in dashboard_data
        
        # Verify health data
        health_data = dashboard_data["health_data"]
        assert "error_statistics" in health_data
        assert "performance_statistics" in health_data
        assert "circuit_breakers" in health_data
        
        # Verify monitoring config
        config = dashboard_data["monitoring_config"]
        assert "error_threshold" in config
        assert "performance_threshold" in config
        assert "monitoring_interval" in config
    
    @pytest.mark.asyncio
    async def test_real_time_monitoring_loop(self):
        """Test real-time monitoring loop integration"""
        # Mock monitoring components
        monitoring_data_manager = AsyncMock()
        real_time_monitor = AsyncMock()
        alerting_system = AsyncMock()
        
        config = ChangelogMonitoringConfig(
            monitoring_interval_seconds=0.1,  # Very short for testing
            error_threshold_percentage=1.0,  # Low threshold for testing
            performance_threshold_seconds=0.1  # Low threshold for testing
        )
        
        monitoring_integration = ChangelogMonitoringIntegration(
            config=config,
            monitoring_data_manager=monitoring_data_manager,
            real_time_monitor=real_time_monitor,
            alerting_system=alerting_system
        )
        
        # Add test data that will trigger alerts
        error_handler = monitoring_integration.error_handler
        
        # Add high error rate
        for i in range(10):
            error_handler.error_history.append(
                ErrorContext(
                    error=Exception(f"Error {i}"),
                    category=ErrorCategory.DATA_COLLECTION,
                    severity=ErrorSeverity.HIGH,
                    service="test_service",
                    operation="test_operation"
                )
            )
        
        # Add performance metrics with high error rate
        from devsync_ai.core.changelog_error_handler import PerformanceMetrics
        for i in range(10):
            error_handler.performance_metrics.append(
                PerformanceMetrics("test_op", 1.0, success=False)
            )
        
        # Start monitoring briefly
        await monitoring_integration.start_monitoring()
        
        # Let it run for a short time
        await asyncio.sleep(0.2)
        
        # Stop monitoring
        await monitoring_integration.stop_monitoring()
        
        # Verify monitoring data was collected
        monitoring_data_manager.store_monitoring_data.assert_called()
        
        # Verify alerts were sent (due to high error rate)
        alerting_system.send_alert.assert_called()
    
    @pytest.mark.asyncio
    async def test_optimization_recommendations_integration(self):
        """Test optimization recommendations integration"""
        error_handler = ChangelogErrorHandler()
        
        # Create scenario that will generate recommendations
        
        # High error rate scenario
        for i in range(20):
            error_handler.error_history.append(
                ErrorContext(
                    error=Exception(f"Error {i}"),
                    category=ErrorCategory.DATA_COLLECTION,
                    severity=ErrorSeverity.HIGH,
                    service="github",
                    operation="fetch_commits"
                )
            )
        
        # Performance issues
        from devsync_ai.core.changelog_error_handler import PerformanceMetrics
        for i in range(10):
            error_handler.performance_metrics.append(
                PerformanceMetrics("slow_operation", 200, success=False)  # Slow and failing
            )
        
        # Open circuit breaker
        github_breaker = error_handler.get_circuit_breaker("github")
        github_breaker.state = CircuitBreakerState.OPEN
        github_breaker.failure_count = 10
        
        # Get recommendations
        recommendations = error_handler.get_optimization_recommendations()
        
        # Should have multiple recommendations
        assert len(recommendations) > 0
        
        # Should have high-priority recommendations
        high_priority = [r for r in recommendations if r["priority"] == "high"]
        assert len(high_priority) > 0
        
        # Should include error rate recommendation
        error_rate_rec = next(
            (r for r in recommendations if r["type"] == "error_rate"), 
            None
        )
        assert error_rate_rec is not None
        
        # Should include circuit breaker recommendation
        circuit_breaker_rec = next(
            (r for r in recommendations if r["type"] == "circuit_breaker"), 
            None
        )
        assert circuit_breaker_rec is not None
    
    @pytest.mark.asyncio
    async def test_health_check_comprehensive_integration(self):
        """Test comprehensive health check integration"""
        monitoring_integration = ChangelogMonitoringIntegration()
        error_handler = monitoring_integration.error_handler
        
        # Add comprehensive test data
        
        # Error history
        error_handler.error_history.extend([
            ErrorContext(
                error=DataCollectionError("GitHub error"),
                category=ErrorCategory.DATA_COLLECTION,
                severity=ErrorSeverity.HIGH,
                service="github",
                operation="fetch_commits"
            ),
            ErrorContext(
                error=DistributionError("Slack error"),
                category=ErrorCategory.DISTRIBUTION,
                severity=ErrorSeverity.MEDIUM,
                service="slack",
                operation="send_message"
            )
        ])
        
        # Performance metrics
        from devsync_ai.core.changelog_error_handler import PerformanceMetrics
        error_handler.performance_metrics.extend([
            PerformanceMetrics("operation1", 1.5, success=True),
            PerformanceMetrics("operation2", 2.0, success=False),
            PerformanceMetrics("operation3", 0.5, success=True)
        ])
        
        # Circuit breakers
        github_breaker = error_handler.get_circuit_breaker("github")
        slack_breaker = error_handler.get_circuit_breaker("slack")
        
        # Perform health check
        health = await error_handler.health_check()
        
        # Verify comprehensive health data
        assert health["status"] == "healthy"
        assert "timestamp" in health
        
        # Error statistics
        error_stats = health["error_statistics"]
        assert error_stats["total_errors"] == 2
        assert "data_collection" in error_stats["errors_by_category"]
        assert "distribution" in error_stats["errors_by_category"]
        assert "github" in error_stats["errors_by_service"]
        assert "slack" in error_stats["errors_by_service"]
        
        # Performance statistics
        perf_stats = health["performance_statistics"]
        assert perf_stats["total_operations"] == 3
        assert perf_stats["successful_operations"] == 2
        assert perf_stats["failed_operations"] == 1
        
        # Circuit breakers
        circuit_breakers = health["circuit_breakers"]
        assert "github" in circuit_breakers
        assert "slack" in circuit_breakers
        
        # System metrics
        sys_metrics = health["system_metrics"]
        assert sys_metrics["total_errors_tracked"] == 2
        assert sys_metrics["total_performance_metrics"] == 3
        assert sys_metrics["active_circuit_breakers"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])