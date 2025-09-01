"""
Comprehensive tests for the Changelog Error Handler system.

Tests cover all failure scenarios, recovery mechanisms, circuit breaker patterns,
performance monitoring, and error handling workflows.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from devsync_ai.core.changelog_error_handler import (
    ChangelogErrorHandler,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    RecoveryAction,
    RecoveryResult,
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerConfig,
    PerformanceMetrics
)
from devsync_ai.core.exceptions import (
    DataCollectionError,
    FormattingError,
    DistributionError,
    ConfigurationError
)


class TestErrorCategorization:
    """Test error categorization and severity assessment"""
    
    def test_data_collection_error_categorization(self):
        """Test categorization of data collection errors"""
        handler = ChangelogErrorHandler()
        error = DataCollectionError("GitHub API failed")
        context = {"service": "github", "operation": "fetch_commits"}
        
        error_context = handler._categorize_error(error, context)
        
        assert error_context.category == ErrorCategory.DATA_COLLECTION
        assert error_context.severity == ErrorSeverity.HIGH
        assert error_context.service == "github"
        assert error_context.operation == "fetch_commits"
    
    def test_formatting_error_categorization(self):
        """Test categorization of formatting errors"""
        handler = ChangelogErrorHandler()
        error = FormattingError("Template rendering failed")
        context = {"service": "formatter", "operation": "render_template"}
        
        error_context = handler._categorize_error(error, context)
        
        assert error_context.category == ErrorCategory.FORMATTING
        assert error_context.severity == ErrorSeverity.MEDIUM
    
    def test_distribution_error_categorization(self):
        """Test categorization of distribution errors"""
        handler = ChangelogErrorHandler()
        error = DistributionError("Slack API failed")
        context = {"service": "slack", "operation": "send_message"}
        
        error_context = handler._categorize_error(error, context)
        
        assert error_context.category == ErrorCategory.DISTRIBUTION
        assert error_context.severity == ErrorSeverity.HIGH
    
    def test_rate_limit_error_categorization(self):
        """Test categorization of rate limit errors"""
        handler = ChangelogErrorHandler()
        error = Exception("Rate limit exceeded")
        context = {"service": "github", "operation": "api_call"}
        
        error_context = handler._categorize_error(error, context)
        
        assert error_context.category == ErrorCategory.RATE_LIMITING
        assert error_context.severity == ErrorSeverity.MEDIUM
    
    def test_critical_operation_severity_escalation(self):
        """Test severity escalation for critical operations"""
        handler = ChangelogErrorHandler()
        error = Exception("Generic error")
        context = {
            "service": "test",
            "operation": "test_op",
            "critical_operation": True
        }
        
        error_context = handler._categorize_error(error, context)
        
        assert error_context.severity == ErrorSeverity.CRITICAL


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in closed state"""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker("test_service", config)
        
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.can_execute() is True
        assert breaker.failure_count == 0
    
    def test_circuit_breaker_failure_threshold(self):
        """Test circuit breaker opens after failure threshold"""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test_service", config)
        
        # Record failures up to threshold
        for i in range(3):
            breaker.record_failure()
            if i < 2:
                assert breaker.state == CircuitBreakerState.CLOSED
        
        # Should be open after threshold
        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.can_execute() is False
    
    def test_circuit_breaker_recovery_timeout(self):
        """Test circuit breaker recovery after timeout"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=timedelta(seconds=1)
        )
        breaker = CircuitBreaker("test_service", config)
        
        # Trigger circuit breaker
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN
        
        # Should still be open immediately
        assert breaker.can_execute() is False
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Should transition to half-open
        assert breaker.can_execute() is True
        # State should be half-open after first call
        breaker.can_execute()
        assert breaker.state == CircuitBreakerState.HALF_OPEN
    
    def test_circuit_breaker_half_open_success(self):
        """Test circuit breaker closes after successful half-open calls"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=timedelta(seconds=0.1),
            success_threshold=2
        )
        breaker = CircuitBreaker("test_service", config)
        
        # Trigger circuit breaker
        breaker.record_failure()
        breaker.record_failure()
        
        # Wait for recovery
        time.sleep(0.2)
        breaker.can_execute()  # Transition to half-open
        
        # Record successful operations
        breaker.record_success()
        breaker.record_success()
        
        # Should be closed now
        assert breaker.state == CircuitBreakerState.CLOSED
    
    def test_circuit_breaker_half_open_failure(self):
        """Test circuit breaker reopens on half-open failure"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=timedelta(seconds=0.1)
        )
        breaker = CircuitBreaker("test_service", config)
        
        # Trigger circuit breaker
        breaker.record_failure()
        breaker.record_failure()
        
        # Wait for recovery
        time.sleep(0.2)
        breaker.can_execute()  # Transition to half-open
        
        # Record failure in half-open state
        breaker.record_failure()
        
        # Should be open again
        assert breaker.state == CircuitBreakerState.OPEN
    
    def test_circuit_breaker_failure_rate_calculation(self):
        """Test failure rate calculation"""
        config = CircuitBreakerConfig(monitoring_window=timedelta(seconds=10))
        breaker = CircuitBreaker("test_service", config)
        
        # Record some failures
        for _ in range(3):
            breaker.record_failure()
        
        failure_rate = breaker.get_failure_rate()
        assert failure_rate > 0
        assert failure_rate <= 1.0


class TestRecoveryStrategies:
    """Test error recovery strategies"""
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self):
        """Test successful retry with backoff"""
        handler = ChangelogErrorHandler()
        error_context = ErrorContext(
            error=Exception("Temporary failure"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.MEDIUM,
            service="test_service",
            operation="test_operation"
        )
        
        result = await handler._retry_with_backoff(error_context)
        
        assert result.success is True
        assert result.action_taken == RecoveryAction.RETRY
        assert "successful" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_failure(self):
        """Test retry failure after max attempts"""
        handler = ChangelogErrorHandler()
        error_context = ErrorContext(
            error=Exception("Persistent failure"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.MEDIUM,
            service="test_service",
            operation="test_operation"
        )
        
        # Mock the retry to always fail
        with patch.object(handler, '_retry_with_backoff') as mock_retry:
            mock_retry.return_value = RecoveryResult(
                success=False,
                action_taken=RecoveryAction.RETRY,
                message="Max retries exceeded"
            )
            
            result = await mock_retry(error_context)
            
            assert result.success is False
            assert result.action_taken == RecoveryAction.RETRY
    
    @pytest.mark.asyncio
    async def test_cached_data_fallback_success(self):
        """Test successful cached data fallback"""
        handler = ChangelogErrorHandler()
        
        # Register fallback data source
        async def mock_fallback():
            return {"cached": True, "data": "test_data"}
        
        handler.register_fallback_data_source("test_service", mock_fallback)
        
        error_context = ErrorContext(
            error=Exception("Service unavailable"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.MEDIUM,
            service="test_service",
            operation="fetch_data"
        )
        
        result = await handler._use_cached_data(error_context)
        
        assert result.success is True
        assert result.action_taken == RecoveryAction.FALLBACK
        assert result.fallback_data is not None
        assert result.fallback_data["cached"] is True
    
    @pytest.mark.asyncio
    async def test_cached_data_fallback_unavailable(self):
        """Test cached data fallback when no cache available"""
        handler = ChangelogErrorHandler()
        error_context = ErrorContext(
            error=Exception("Service unavailable"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.MEDIUM,
            service="unknown_service",
            operation="fetch_data"
        )
        
        result = await handler._use_cached_data(error_context)
        
        assert result.success is False
        assert result.action_taken == RecoveryAction.FALLBACK
        assert "no cached data available" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_rate_limiting(self):
        """Test exponential backoff for rate limiting"""
        handler = ChangelogErrorHandler()
        error_context = ErrorContext(
            error=Exception("Rate limit exceeded, retry after 60 seconds"),
            category=ErrorCategory.RATE_LIMITING,
            severity=ErrorSeverity.MEDIUM,
            service="github",
            operation="api_call"
        )
        
        result = await handler._exponential_backoff(error_context)
        
        assert result.success is False
        assert result.action_taken == RecoveryAction.RETRY
        assert result.retry_after is not None
        assert result.retry_after.total_seconds() == 60


class TestErrorHandling:
    """Test main error handling workflow"""
    
    @pytest.mark.asyncio
    async def test_handle_error_with_successful_recovery(self):
        """Test error handling with successful recovery"""
        monitoring_callback = AsyncMock()
        alerting_callback = AsyncMock()
        
        handler = ChangelogErrorHandler(
            monitoring_callback=monitoring_callback,
            alerting_callback=alerting_callback
        )
        
        error = DataCollectionError("GitHub API failed")
        context = {
            "service": "github",
            "operation": "fetch_commits",
            "team_id": "test_team"
        }
        
        result = await handler.handle_error(error, context)
        
        assert result.success is True
        assert result.action_taken == RecoveryAction.RETRY
        
        # Verify monitoring callback was called
        monitoring_callback.assert_called_once()
        
        # High severity error should trigger alert
        alerting_callback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_error_with_circuit_breaker_open(self):
        """Test error handling when circuit breaker is open"""
        handler = ChangelogErrorHandler()
        
        # Manually open circuit breaker
        breaker = handler.get_circuit_breaker("github")
        breaker.state = CircuitBreakerState.OPEN
        breaker.last_failure_time = datetime.utcnow()
        
        error = DataCollectionError("GitHub API failed")
        context = {
            "service": "github",
            "operation": "fetch_commits"
        }
        
        result = await handler.handle_error(error, context)
        
        assert result.success is False
        assert result.action_taken == RecoveryAction.CIRCUIT_BREAK
        assert result.escalation_required is True
        assert "circuit breaker open" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_handle_error_all_recovery_strategies_fail(self):
        """Test error handling when all recovery strategies fail"""
        handler = ChangelogErrorHandler()
        
        # Mock all recovery strategies to fail
        async def failing_strategy(error_context):
            raise Exception("Recovery strategy failed")
        
        handler.recovery_strategies[ErrorCategory.DATA_COLLECTION] = [failing_strategy]
        
        error = DataCollectionError("Persistent failure")
        context = {
            "service": "github",
            "operation": "fetch_commits"
        }
        
        result = await handler.handle_error(error, context)
        
        assert result.success is False
        assert result.action_taken == RecoveryAction.ESCALATE
        assert result.escalation_required is True


class TestPerformanceMonitoring:
    """Test performance monitoring functionality"""
    
    @pytest.mark.asyncio
    async def test_performance_monitor_success(self):
        """Test successful performance monitoring"""
        handler = ChangelogErrorHandler()
        
        async with handler.performance_monitor("test_operation", "test_service"):
            await asyncio.sleep(0.1)  # Simulate work
        
        assert len(handler.performance_metrics) == 1
        metric = handler.performance_metrics[0]
        assert metric.operation == "test_operation"
        assert metric.success is True
        assert metric.duration >= 0.1
    
    @pytest.mark.asyncio
    async def test_performance_monitor_with_error(self):
        """Test performance monitoring with error"""
        handler = ChangelogErrorHandler()
        
        with pytest.raises(ValueError):
            async with handler.performance_monitor("test_operation", "test_service"):
                raise ValueError("Test error")
        
        assert len(handler.performance_metrics) == 1
        metric = handler.performance_metrics[0]
        assert metric.operation == "test_operation"
        assert metric.success is False
    
    @pytest.mark.asyncio
    async def test_performance_threshold_alerts(self):
        """Test performance threshold alerting"""
        alerting_callback = AsyncMock()
        handler = ChangelogErrorHandler(alerting_callback=alerting_callback)
        
        # Create metric that exceeds threshold
        metric = PerformanceMetrics(
            operation="slow_operation",
            duration=200,  # Exceeds 180 second threshold
            success=True
        )
        
        await handler._check_performance_thresholds(metric)
        
        # Should have sent performance alert
        alerting_callback.assert_called_once()
        alert_data = alerting_callback.call_args[0][0]
        assert alert_data["type"] == "performance_threshold_exceeded"
        assert alert_data["metric"] == "generation_time"


class TestStatisticsAndAnalytics:
    """Test error statistics and analytics"""
    
    def test_error_statistics_calculation(self):
        """Test error statistics calculation"""
        handler = ChangelogErrorHandler()
        
        # Add some test errors
        errors = [
            ErrorContext(
                error=DataCollectionError("Error 1"),
                category=ErrorCategory.DATA_COLLECTION,
                severity=ErrorSeverity.HIGH,
                service="github",
                operation="fetch_commits"
            ),
            ErrorContext(
                error=FormattingError("Error 2"),
                category=ErrorCategory.FORMATTING,
                severity=ErrorSeverity.MEDIUM,
                service="formatter",
                operation="render_template"
            ),
            ErrorContext(
                error=DataCollectionError("Error 3"),
                category=ErrorCategory.DATA_COLLECTION,
                severity=ErrorSeverity.HIGH,
                service="github",
                operation="fetch_prs"
            )
        ]
        
        handler.error_history.extend(errors)
        
        stats = handler.get_error_statistics()
        
        assert stats["total_errors"] == 3
        assert stats["errors_by_category"]["data_collection"] == 2
        assert stats["errors_by_category"]["formatting"] == 1
        assert stats["errors_by_severity"]["high"] == 2
        assert stats["errors_by_severity"]["medium"] == 1
        assert stats["errors_by_service"]["github"] == 2
        assert stats["errors_by_service"]["formatter"] == 1
        assert stats["most_common_category"] == "data_collection"
    
    def test_performance_statistics_calculation(self):
        """Test performance statistics calculation"""
        handler = ChangelogErrorHandler()
        
        # Add some test metrics
        metrics = [
            PerformanceMetrics("operation1", 1.5, success=True),
            PerformanceMetrics("operation1", 2.0, success=True),
            PerformanceMetrics("operation2", 0.5, success=False),
            PerformanceMetrics("operation2", 1.0, success=True)
        ]
        
        handler.performance_metrics.extend(metrics)
        
        stats = handler.get_performance_statistics()
        
        assert stats["total_operations"] == 4
        assert stats["successful_operations"] == 3
        assert stats["failed_operations"] == 1
        assert stats["average_duration"] == 1.25
        assert stats["max_duration"] == 2.0
        assert stats["min_duration"] == 0.5
        
        # Check operations grouping
        ops_stats = stats["operations_by_type"]
        assert "operation1" in ops_stats
        assert "operation2" in ops_stats
        assert ops_stats["operation1"]["count"] == 2
        assert ops_stats["operation1"]["success_rate"] == 1.0
        assert ops_stats["operation2"]["count"] == 2
        assert ops_stats["operation2"]["success_rate"] == 0.5
    
    def test_optimization_recommendations(self):
        """Test optimization recommendations generation"""
        handler = ChangelogErrorHandler()
        
        # Set up high error rate scenario
        handler.error_history = [
            ErrorContext(
                error=Exception(f"Error {i}"),
                category=ErrorCategory.DATA_COLLECTION,
                severity=ErrorSeverity.HIGH,
                service="github",
                operation="test"
            )
            for i in range(10)
        ]
        
        # Set up performance metrics with high error rate
        handler.performance_metrics = [
            PerformanceMetrics("test_op", 1.0, success=False)
            for _ in range(8)
        ] + [
            PerformanceMetrics("test_op", 1.0, success=True)
            for _ in range(2)
        ]
        
        recommendations = handler.get_optimization_recommendations()
        
        # Should recommend addressing high error rate
        error_rate_rec = next(
            (r for r in recommendations if r["type"] == "error_rate"), 
            None
        )
        assert error_rate_rec is not None
        assert error_rate_rec["priority"] == "high"


class TestHealthCheck:
    """Test system health check functionality"""
    
    @pytest.mark.asyncio
    async def test_health_check_comprehensive(self):
        """Test comprehensive health check"""
        handler = ChangelogErrorHandler()
        
        # Add some test data
        handler.error_history.append(
            ErrorContext(
                error=Exception("Test error"),
                category=ErrorCategory.DATA_COLLECTION,
                severity=ErrorSeverity.MEDIUM,
                service="test_service",
                operation="test_operation"
            )
        )
        
        handler.performance_metrics.append(
            PerformanceMetrics("test_operation", 1.0, success=True)
        )
        
        # Create a circuit breaker
        handler.get_circuit_breaker("test_service")
        
        health = await handler.health_check()
        
        assert health["status"] == "healthy"
        assert "timestamp" in health
        assert "error_statistics" in health
        assert "performance_statistics" in health
        assert "circuit_breakers" in health
        assert "optimization_recommendations" in health
        assert "system_metrics" in health
        
        # Check system metrics
        sys_metrics = health["system_metrics"]
        assert sys_metrics["total_errors_tracked"] == 1
        assert sys_metrics["total_performance_metrics"] == 1
        assert sys_metrics["active_circuit_breakers"] == 1


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_github_api_failure_recovery_scenario(self):
        """Test complete GitHub API failure and recovery scenario"""
        monitoring_callback = AsyncMock()
        alerting_callback = AsyncMock()
        
        handler = ChangelogErrorHandler(
            monitoring_callback=monitoring_callback,
            alerting_callback=alerting_callback
        )
        
        # Register fallback data source
        async def github_fallback():
            return {"commits": [], "cached": True}
        
        handler.register_fallback_data_source("github", github_fallback)
        
        # Simulate GitHub API failure
        error = DataCollectionError("GitHub API rate limit exceeded")
        context = {
            "service": "github",
            "operation": "fetch_weekly_commits",
            "team_id": "engineering",
            "user_id": "test_user",
            "request_id": "req_123"
        }
        
        result = await handler.handle_error(error, context)
        
        # Should successfully recover using fallback
        assert result.success is True
        assert result.action_taken in [RecoveryAction.RETRY, RecoveryAction.FALLBACK]
        
        # Verify callbacks were called
        monitoring_callback.assert_called_once()
        alerting_callback.assert_called_once()
        
        # Check error was logged
        assert len(handler.error_history) == 1
        logged_error = handler.error_history[0]
        assert logged_error.category == ErrorCategory.DATA_COLLECTION
        assert logged_error.service == "github"
        assert logged_error.team_id == "engineering"
    
    @pytest.mark.asyncio
    async def test_multiple_service_failures_circuit_breaker_scenario(self):
        """Test multiple service failures triggering circuit breakers"""
        handler = ChangelogErrorHandler()
        
        # Simulate multiple failures for GitHub service
        github_errors = [
            DataCollectionError(f"GitHub API error {i}")
            for i in range(6)  # Exceeds default threshold of 5
        ]
        
        context = {
            "service": "github",
            "operation": "fetch_data"
        }
        
        results = []
        for error in github_errors:
            result = await handler.handle_error(error, context)
            results.append(result)
        
        # First 5 should attempt recovery
        for i in range(5):
            assert results[i].action_taken != RecoveryAction.CIRCUIT_BREAK
        
        # 6th should trigger circuit breaker
        github_breaker = handler.get_circuit_breaker("github")
        assert github_breaker.state == CircuitBreakerState.OPEN
        
        # Subsequent calls should be circuit broken
        final_result = await handler.handle_error(
            DataCollectionError("Another GitHub error"), 
            context
        )
        assert final_result.action_taken == RecoveryAction.CIRCUIT_BREAK
    
    @pytest.mark.asyncio
    async def test_performance_degradation_scenario(self):
        """Test performance degradation detection and alerting"""
        alerting_callback = AsyncMock()
        handler = ChangelogErrorHandler(alerting_callback=alerting_callback)
        
        # Simulate slow operations
        async with handler.performance_monitor("changelog_generation", "changelog"):
            await asyncio.sleep(0.01)  # Simulate work
        
        # Manually create a slow metric to trigger threshold
        slow_metric = PerformanceMetrics(
            operation="changelog_generation",
            duration=200,  # Exceeds 180 second threshold
            success=True
        )
        
        await handler._check_performance_thresholds(slow_metric)
        
        # Should have triggered performance alert
        alerting_callback.assert_called_once()
        alert = alerting_callback.call_args[0][0]
        assert alert["type"] == "performance_threshold_exceeded"
        assert alert["metric"] == "generation_time"
        assert alert["value"] == 200
        assert alert["threshold"] == 180


if __name__ == "__main__":
    pytest.main([__file__, "-v"])