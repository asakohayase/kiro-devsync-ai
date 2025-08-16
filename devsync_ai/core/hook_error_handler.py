"""
Comprehensive error handling and retry mechanisms for Agent Hooks.

This module provides specialized error handling for JIRA-Slack Agent Hooks,
including error categorization, exponential backoff retry logic, circuit breaker
patterns, and fallback notification mechanisms.
"""

import asyncio
import time
import random
import logging
import json
import uuid
from typing import Dict, List, Any, Optional, Callable, Union, Tuple, Type
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque

from .agent_hooks import (
    HookExecutionResult, HookStatus, EnrichedEvent, AgentHook,
    EventCategory, UrgencyLevel
)
from .exceptions import (
    TemplateError, DataValidationError, FormattingError, BlockKitError,
    SlackAPIError, NetworkError, RateLimitError, TemplateRenderingError,
    ConfigurationError, ErrorSeverity, ErrorCategory
)


class HookErrorCategory(Enum):
    """Specific error categories for Agent Hooks."""
    WEBHOOK_PROCESSING = "webhook_processing"
    EVENT_CLASSIFICATION = "event_classification"
    RULE_EVALUATION = "rule_evaluation"
    HOOK_EXECUTION = "hook_execution"
    NOTIFICATION_DELIVERY = "notification_delivery"
    CONFIGURATION_ERROR = "configuration_error"
    EXTERNAL_SERVICE = "external_service"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"


class HookErrorSeverity(Enum):
    """Severity levels for hook errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RetryStrategy(Enum):
    """Retry strategies for different error types."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"
    NO_RETRY = "no_retry"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class HookError(Exception):
    """Base exception for Agent Hook errors."""
    message: str
    category: HookErrorCategory
    severity: HookErrorSeverity = HookErrorSeverity.MEDIUM
    hook_id: Optional[str] = None
    event_id: Optional[str] = None
    execution_id: Optional[str] = None
    recoverable: bool = True
    retry_after: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)
    original_error: Optional[Exception] = None
    
    def __str__(self) -> str:
        return f"[{self.category.value}] {self.message}"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 300.0  # seconds (5 minutes)
    backoff_multiplier: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    timeout_seconds: float = 30.0


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    success_threshold: int = 3  # For half-open state
    timeout_seconds: int = 60
    half_open_max_calls: int = 3


@dataclass
class FallbackConfig:
    """Configuration for fallback mechanisms."""
    enable_fallbacks: bool = True
    fallback_channels: List[str] = field(default_factory=list)
    notify_admins: bool = True
    admin_channels: List[str] = field(default_factory=list)
    include_error_details: bool = False
    max_fallback_attempts: int = 2


@dataclass
class NotificationQueueConfig:
    """Configuration for notification queuing when services are unavailable."""
    enable_queuing: bool = True
    max_queue_size: int = 1000
    queue_retention_hours: int = 24
    retry_interval_minutes: int = 5
    max_retry_attempts: int = 10


@dataclass
class WebhookValidationConfig:
    """Configuration for webhook payload validation."""
    enable_validation: bool = True
    required_fields: List[str] = field(default_factory=lambda: [
        'webhookEvent', 'issue', 'timestamp'
    ])
    max_payload_size_mb: float = 10.0
    sanitize_html: bool = True
    validate_json_structure: bool = True


@dataclass
class QueuedNotification:
    """Represents a queued notification for later delivery."""
    id: str
    hook_id: str
    event_id: str
    notification_data: Dict[str, Any]
    created_at: datetime
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    max_retries: int = 10
    
    def should_retry(self, retry_interval_minutes: int) -> bool:
        """Check if notification should be retried."""
        if self.retry_count >= self.max_retries:
            return False
        
        if self.last_retry_at is None:
            return True
        
        time_since_retry = datetime.now() - self.last_retry_at
        return time_since_retry >= timedelta(minutes=retry_interval_minutes)


@dataclass
class HookErrorMetrics:
    """Metrics for hook error tracking."""
    total_errors: int = 0
    errors_by_category: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors_by_severity: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors_by_hook_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    recovery_success_rate: float = 0.0
    average_recovery_time: float = 0.0
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=100))
    circuit_breaker_trips: int = 0
    fallback_activations: int = 0
    payload_validation_failures: int = 0
    queued_notifications: int = 0
    successful_queue_deliveries: int = 0
    
    def add_error(self, error: HookError, recovery_time: Optional[float] = None):
        """Add error to metrics."""
        self.total_errors += 1
        self.errors_by_category[error.category.value] += 1
        self.errors_by_severity[error.severity.value] += 1
        if error.hook_id:
            self.errors_by_hook_type[error.hook_id] += 1
        
        error_record = {
            'timestamp': datetime.now(),
            'category': error.category.value,
            'severity': error.severity.value,
            'hook_id': error.hook_id,
            'event_id': error.event_id,
            'message': str(error),
            'recovery_time': recovery_time,
            'recovered': recovery_time is not None
        }
        self.recent_errors.append(error_record)
        
        # Update recovery metrics
        if recovery_time is not None:
            recovered_errors = [e for e in self.recent_errors if e['recovered']]
            if recovered_errors:
                self.recovery_success_rate = len(recovered_errors) / len(self.recent_errors)
                self.average_recovery_time = sum(e['recovery_time'] for e in recovered_errors) / len(recovered_errors)


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self.half_open_calls = 0
        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker")
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if (self.last_failure_time and 
                time.time() - self.last_failure_time > self.config.timeout_seconds):
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise HookError(
                    "Circuit breaker is OPEN - service unavailable",
                    category=HookErrorCategory.EXTERNAL_SERVICE,
                    severity=HookErrorSeverity.HIGH,
                    recoverable=False
                )
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            if self.half_open_calls >= self.config.half_open_max_calls:
                raise HookError(
                    "Circuit breaker HALF_OPEN call limit exceeded",
                    category=HookErrorCategory.EXTERNAL_SERVICE,
                    severity=HookErrorSeverity.HIGH,
                    recoverable=False
                )
            self.half_open_calls += 1
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.logger.info("Circuit breaker transitioning to CLOSED")
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning("Circuit breaker transitioning to OPEN from HALF_OPEN")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")
    
    def reset(self):
        """Reset circuit breaker to closed state."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        self.last_failure_time = None


class HookErrorHandler:
    """Comprehensive error handler for Agent Hooks."""
    
    def __init__(self, 
                 retry_config: Optional[RetryConfig] = None,
                 circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
                 fallback_config: Optional[FallbackConfig] = None,
                 notification_queue_config: Optional[NotificationQueueConfig] = None,
                 webhook_validation_config: Optional[WebhookValidationConfig] = None):
        """Initialize the hook error handler."""
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        self.fallback_config = fallback_config or FallbackConfig()
        self.notification_queue_config = notification_queue_config or NotificationQueueConfig()
        self.webhook_validation_config = webhook_validation_config or WebhookValidationConfig()
        
        self.logger = logging.getLogger(__name__)
        self.metrics = HookErrorMetrics()
        
        # Circuit breakers for different services
        self.circuit_breakers = {
            'jira_api': CircuitBreaker(self.circuit_breaker_config),
            'slack_api': CircuitBreaker(self.circuit_breaker_config),
            'database': CircuitBreaker(self.circuit_breaker_config),
            'webhook_processing': CircuitBreaker(self.circuit_breaker_config)
        }
        
        # Notification queue for when services are unavailable
        self.notification_queue: Dict[str, QueuedNotification] = {}
        self._queue_cleanup_task: Optional[asyncio.Task] = None
        
        # Background task will be started lazily when needed
        
        self.logger.info("HookErrorHandler initialized")
    
    async def execute_with_retry(self,
                               operation: Callable,
                               hook: AgentHook,
                               event: EnrichedEvent,
                               *args, **kwargs) -> HookExecutionResult:
        """Execute hook operation with comprehensive error handling and retry logic."""
        start_time = time.time()
        last_error = None
        execution_result = None
        all_errors = []
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                # Create execution result for this attempt
                execution_result = HookExecutionResult(
                    hook_id=hook.hook_id,
                    execution_id=f"{hook.hook_id}_{int(time.time() * 1000)}_{attempt}",
                    hook_type=hook.hook_type,
                    event_id=event.event_id,
                    status=HookStatus.RUNNING,
                    execution_time_ms=0.0
                )
                execution_result.metadata['attempt'] = attempt + 1
                execution_result.metadata['max_attempts'] = self.retry_config.max_attempts
                
                # Execute with circuit breaker protection
                circuit_breaker = self._get_circuit_breaker(operation)
                if circuit_breaker:
                    result = await circuit_breaker.call(operation, event, *args, **kwargs)
                else:
                    if asyncio.iscoroutinefunction(operation):
                        result = await operation(event, *args, **kwargs)
                    else:
                        result = operation(event, *args, **kwargs)
                
                # Success - update execution result
                execution_time = (time.time() - start_time) * 1000
                execution_result.execution_time_ms = execution_time
                execution_result.status = HookStatus.SUCCESS
                execution_result.mark_completed(HookStatus.SUCCESS)
                
                # Add all previous errors to the successful result
                execution_result.errors = [str(e) for e in all_errors]
                
                # Record recovery if this wasn't the first attempt
                if attempt > 0 and last_error:
                    recovery_time = time.time() - start_time
                    self.metrics.add_error(last_error, recovery_time)
                    self.logger.info(
                        f"Hook {hook.hook_id} recovered after {attempt} attempts "
                        f"in {recovery_time:.2f}s"
                    )
                
                return execution_result
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                last_error = self._classify_hook_error(e, hook, event)
                all_errors.append(last_error)
                
                if execution_result:
                    execution_result.execution_time_ms = execution_time
                    execution_result.add_error(str(last_error))
                    execution_result.metadata['last_error_category'] = last_error.category.value
                    execution_result.metadata['last_error_severity'] = last_error.severity.value
                
                self.logger.warning(
                    f"Hook {hook.hook_id} attempt {attempt + 1} failed: {last_error}"
                )
                
                # Check if error is recoverable
                if not last_error.recoverable:
                    self.logger.error(f"Non-recoverable error in hook {hook.hook_id}: {last_error}")
                    if execution_result:
                        execution_result.status = HookStatus.FAILED
                        execution_result.mark_completed(HookStatus.FAILED)
                    break
                
                # Apply retry delay if not the last attempt
                if attempt < self.retry_config.max_attempts - 1:
                    delay = self._calculate_retry_delay(attempt, last_error)
                    if delay > 0:
                        if execution_result:
                            execution_result.status = HookStatus.RETRYING
                            execution_result.metadata['retry_delay'] = delay
                        self.logger.debug(f"Retrying hook {hook.hook_id} in {delay:.2f} seconds...")
                        await asyncio.sleep(delay)
        
        # All retries failed - create final execution result if needed
        if not execution_result:
            execution_result = HookExecutionResult(
                hook_id=hook.hook_id,
                execution_id=f"{hook.hook_id}_{int(time.time() * 1000)}_final",
                hook_type=hook.hook_type,
                event_id=event.event_id,
                status=HookStatus.FAILED,
                execution_time_ms=(time.time() - start_time) * 1000
            )
            execution_result.metadata['attempt'] = self.retry_config.max_attempts
            execution_result.metadata['max_attempts'] = self.retry_config.max_attempts
        
        # Add all errors to the final result
        execution_result.errors = [str(e) for e in all_errors]
        if last_error:
            execution_result.metadata['last_error_category'] = last_error.category.value
            execution_result.metadata['last_error_severity'] = last_error.severity.value
        
        execution_result.status = HookStatus.FAILED
        execution_result.mark_completed(HookStatus.FAILED)
        
        self.logger.error(f"Hook {hook.hook_id} failed after all retry attempts")
        if last_error:
            self.metrics.add_error(last_error)
        
        # Apply fallback mechanisms
        if self.fallback_config.enable_fallbacks:
            await self._apply_fallback_mechanisms(hook, event, last_error, execution_result)
        
        # If Slack API is unavailable and we have notification data, queue it for later delivery
        # Check for both notification delivery errors and external service errors that might be Slack-related
        should_queue = (last_error and self.notification_queue_config.enable_queuing and
                       (last_error.category == HookErrorCategory.NOTIFICATION_DELIVERY or
                        (last_error.category == HookErrorCategory.EXTERNAL_SERVICE and 
                         'slack' in str(last_error).lower()) or
                        'circuit breaker' in str(last_error).lower()))
        
        if should_queue:
            try:
                # Extract notification data from execution result if available
                notification_data = {
                    "hook_id": hook.hook_id,
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "timestamp": event.timestamp.isoformat(),
                    "error": str(last_error)
                }
                
                queue_id = await self.queue_notification_for_later_delivery(
                    hook.hook_id, event.event_id, notification_data
                )
                execution_result.metadata['queued_notification_id'] = queue_id
                self.logger.info(f"Notification queued for later delivery: {queue_id}")
                
            except Exception as queue_error:
                self.logger.error(f"Failed to queue notification: {queue_error}")
                execution_result.metadata['queue_error'] = str(queue_error)
        
        return execution_result
    
    def _classify_hook_error(self, 
                           error: Exception, 
                           hook: AgentHook, 
                           event: EnrichedEvent) -> HookError:
        """Classify and enhance error with hook-specific context."""
        if isinstance(error, HookError):
            return error
        
        error_message = str(error)
        error_type = type(error).__name__
        
        # Classify based on error type and message
        if isinstance(error, ConnectionError):
            return HookError(
                f"Network error in hook {hook.hook_id}: {error_message}",
                category=HookErrorCategory.EXTERNAL_SERVICE,
                severity=HookErrorSeverity.HIGH,
                hook_id=hook.hook_id,
                event_id=event.event_id,
                recoverable=True,
                retry_after=30.0,
                original_error=error
            )
        elif isinstance(error, TimeoutError):
            return HookError(
                f"Timeout error in hook {hook.hook_id}: {error_message}",
                category=HookErrorCategory.TIMEOUT,
                severity=HookErrorSeverity.HIGH,
                hook_id=hook.hook_id,
                event_id=event.event_id,
                recoverable=True,
                retry_after=60.0,
                original_error=error
            )
        elif isinstance(error, RateLimitError):
            return HookError(
                f"Rate limit exceeded in hook {hook.hook_id}: {error_message}",
                category=HookErrorCategory.RATE_LIMIT,
                severity=HookErrorSeverity.MEDIUM,
                hook_id=hook.hook_id,
                event_id=event.event_id,
                recoverable=True,
                retry_after=float(error.retry_after) if error.retry_after else None,
                original_error=error
            )
        elif isinstance(error, SlackAPIError):
            severity = HookErrorSeverity.CRITICAL if error.status_code == 401 else HookErrorSeverity.HIGH
            return HookError(
                f"Slack API error in hook {hook.hook_id}: {error_message}",
                category=HookErrorCategory.NOTIFICATION_DELIVERY,
                severity=severity,
                hook_id=hook.hook_id,
                event_id=event.event_id,
                recoverable=error.status_code != 401,
                retry_after=error.retry_after,
                original_error=error
            )
        elif isinstance(error, ConfigurationError):
            return HookError(
                f"Configuration error in hook {hook.hook_id}: {error_message}",
                category=HookErrorCategory.CONFIGURATION_ERROR,
                severity=HookErrorSeverity.HIGH,
                hook_id=hook.hook_id,
                event_id=event.event_id,
                recoverable=False,
                original_error=error
            )
        elif isinstance(error, NetworkError):
            return HookError(
                f"Network error in hook {hook.hook_id}: {error_message}",
                category=HookErrorCategory.EXTERNAL_SERVICE,
                severity=HookErrorSeverity.HIGH,
                hook_id=hook.hook_id,
                event_id=event.event_id,
                recoverable=True,
                retry_after=30.0,
                original_error=error
            )
        elif isinstance(error, (DataValidationError, FormattingError)):
            return HookError(
                f"Data processing error in hook {hook.hook_id}: {error_message}",
                category=HookErrorCategory.HOOK_EXECUTION,
                severity=HookErrorSeverity.MEDIUM,
                hook_id=hook.hook_id,
                event_id=event.event_id,
                recoverable=True,
                original_error=error
            )
        elif 'timeout' in error_message.lower():
            return HookError(
                f"Timeout error in hook {hook.hook_id}: {error_message}",
                category=HookErrorCategory.TIMEOUT,
                severity=HookErrorSeverity.HIGH,
                hook_id=hook.hook_id,
                event_id=event.event_id,
                recoverable=True,
                retry_after=60.0,
                original_error=error
            )
        elif 'webhook' in error_message.lower():
            return HookError(
                f"Webhook processing error: {error_message}",
                category=HookErrorCategory.WEBHOOK_PROCESSING,
                severity=HookErrorSeverity.MEDIUM,
                hook_id=hook.hook_id,
                event_id=event.event_id,
                recoverable=True,
                original_error=error
            )
        else:
            return HookError(
                f"Unknown error in hook {hook.hook_id} ({error_type}): {error_message}",
                category=HookErrorCategory.HOOK_EXECUTION,
                severity=HookErrorSeverity.MEDIUM,
                hook_id=hook.hook_id,
                event_id=event.event_id,
                recoverable=True,
                original_error=error
            )
    
    def _get_circuit_breaker(self, operation: Callable) -> Optional[CircuitBreaker]:
        """Get appropriate circuit breaker for operation."""
        operation_name = getattr(operation, '__name__', str(operation))
        
        if 'slack' in operation_name.lower() or 'notification' in operation_name.lower():
            return self.circuit_breakers['slack_api']
        elif 'jira' in operation_name.lower():
            return self.circuit_breakers['jira_api']
        elif 'database' in operation_name.lower() or 'db' in operation_name.lower():
            return self.circuit_breakers['database']
        elif 'webhook' in operation_name.lower():
            return self.circuit_breakers['webhook_processing']
        
        return None
    
    def _calculate_retry_delay(self, attempt: int, error: HookError) -> float:
        """Calculate retry delay based on strategy and error type."""
        # Use error-specific retry delay if available
        if error.retry_after is not None and error.retry_after > 0:
            return min(error.retry_after, self.retry_config.max_delay)
        
        # Calculate base delay based on strategy
        if self.retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.retry_config.base_delay * (self.retry_config.backoff_multiplier ** attempt)
        elif self.retry_config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.retry_config.base_delay * (attempt + 1)
        elif self.retry_config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.retry_config.base_delay
        elif self.retry_config.strategy == RetryStrategy.IMMEDIATE:
            delay = 0
        else:  # NO_RETRY
            return 0
        
        # Apply jitter to avoid thundering herd
        if self.retry_config.jitter:
            delay *= (0.5 + random.random() * 0.5)
        
        # Respect max delay
        return min(delay, self.retry_config.max_delay)
    
    async def _apply_fallback_mechanisms(self,
                                       hook: AgentHook,
                                       event: EnrichedEvent,
                                       error: HookError,
                                       execution_result: HookExecutionResult):
        """Apply fallback mechanisms when hook execution fails."""
        self.metrics.fallback_activations += 1
        
        try:
            # Try to send a simplified notification to fallback channels
            if self.fallback_config.fallback_channels:
                await self._send_fallback_notification(hook, event, error)
            
            # Notify administrators if configured
            if self.fallback_config.notify_admins and self.fallback_config.admin_channels:
                await self._send_admin_notification(hook, event, error)
            
            execution_result.metadata['fallback_applied'] = True
            self.logger.info(f"Fallback mechanisms applied for hook {hook.hook_id}")
            
        except Exception as fallback_error:
            self.logger.error(f"Fallback mechanisms failed for hook {hook.hook_id}: {fallback_error}")
            execution_result.metadata['fallback_failed'] = True
    
    async def _send_fallback_notification(self,
                                        hook: AgentHook,
                                        event: EnrichedEvent,
                                        error: HookError):
        """Send simplified fallback notification."""
        # This would integrate with the notification system
        # For now, we'll log the fallback notification
        message = f"⚠️ Hook {hook.hook_id} failed to process event {event.event_id}"
        if self.fallback_config.include_error_details:
            message += f"\nError: {error.message}"
        
        self.logger.warning(f"Fallback notification: {message}")
        # TODO: Integrate with actual notification system
    
    async def _send_admin_notification(self,
                                     hook: AgentHook,
                                     event: EnrichedEvent,
                                     error: HookError):
        """Send notification to administrators about hook failure."""
        message = (
            f"🚨 Agent Hook Failure Alert\n"
            f"Hook: {hook.hook_id} ({hook.hook_type})\n"
            f"Event: {event.event_id}\n"
            f"Error: {error.category.value} - {error.message}\n"
            f"Severity: {error.severity.value}\n"
            f"Recoverable: {error.recoverable}"
        )
        
        self.logger.error(f"Admin notification: {message}")
        # TODO: Integrate with actual notification system
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get comprehensive error metrics."""
        return {
            "total_errors": self.metrics.total_errors,
            "errors_by_category": dict(self.metrics.errors_by_category),
            "errors_by_severity": dict(self.metrics.errors_by_severity),
            "errors_by_hook_type": dict(self.metrics.errors_by_hook_type),
            "recovery_success_rate": self.metrics.recovery_success_rate,
            "average_recovery_time": self.metrics.average_recovery_time,
            "recent_errors_count": len(self.metrics.recent_errors),
            "circuit_breaker_trips": self.metrics.circuit_breaker_trips,
            "fallback_activations": self.metrics.fallback_activations,
            "payload_validation_failures": self.metrics.payload_validation_failures,
            "queued_notifications": self.metrics.queued_notifications,
            "successful_queue_deliveries": self.metrics.successful_queue_deliveries,
            "circuit_breaker_states": {
                name: breaker.state.value 
                for name, breaker in self.circuit_breakers.items()
            },
            "queue_status": self.get_queue_status()
        }
    
    def get_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: {
                "state": breaker.state.value,
                "failure_count": breaker.failure_count,
                "success_count": breaker.success_count,
                "last_failure_time": breaker.last_failure_time
            }
            for name, breaker in self.circuit_breakers.items()
        }
    
    def reset_circuit_breaker(self, service_name: str) -> bool:
        """Reset a specific circuit breaker."""
        if service_name in self.circuit_breakers:
            self.circuit_breakers[service_name].reset()
            self.logger.info(f"Circuit breaker {service_name} reset")
            return True
        return False
    
    def reset_all_circuit_breakers(self):
        """Reset all circuit breakers."""
        for name, breaker in self.circuit_breakers.items():
            breaker.reset()
        self.logger.info("All circuit breakers reset")
    
    def reset_metrics(self):
        """Reset error metrics (useful for testing)."""
        self.metrics = HookErrorMetrics()
        self.logger.info("Error metrics reset")
    
    def validate_webhook_payload(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate and sanitize webhook payload according to requirement 8.3.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.webhook_validation_config.enable_validation:
            return True, None
        
        try:
            # Check payload size
            payload_size_mb = len(json.dumps(payload).encode('utf-8')) / (1024 * 1024)
            if payload_size_mb > self.webhook_validation_config.max_payload_size_mb:
                self.metrics.payload_validation_failures += 1
                return False, f"Payload size {payload_size_mb:.2f}MB exceeds limit of {self.webhook_validation_config.max_payload_size_mb}MB"
            
            # Check required fields
            for field in self.webhook_validation_config.required_fields:
                if not self._check_nested_field(payload, field):
                    self.metrics.payload_validation_failures += 1
                    return False, f"Required field '{field}' is missing from payload"
            
            # Validate JSON structure if enabled
            if self.webhook_validation_config.validate_json_structure:
                if not self._validate_json_structure(payload):
                    self.metrics.payload_validation_failures += 1
                    return False, "Invalid JSON structure in payload"
            
            return True, None
            
        except Exception as e:
            self.metrics.payload_validation_failures += 1
            self.logger.error(f"Error validating webhook payload: {e}")
            return False, f"Payload validation error: {str(e)}"
    
    def sanitize_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize webhook payload to remove potentially harmful content.
        
        Args:
            payload: Raw webhook payload
            
        Returns:
            Sanitized payload
        """
        if not self.webhook_validation_config.sanitize_html:
            return payload
        
        try:
            sanitized = self._deep_sanitize(payload)
            self.logger.debug("Webhook payload sanitized")
            return sanitized
        except Exception as e:
            self.logger.error(f"Error sanitizing webhook payload: {e}")
            # Return original payload if sanitization fails
            return payload
    
    def _check_nested_field(self, data: Dict[str, Any], field_path: str) -> bool:
        """Check if a nested field exists in the data."""
        parts = field_path.split('.')
        current = data
        
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        
        return True
    
    def _validate_json_structure(self, payload: Dict[str, Any]) -> bool:
        """Validate basic JSON structure requirements."""
        try:
            # Check for common JIRA webhook structure
            if 'webhookEvent' in payload:
                # JIRA webhook validation
                if 'issue' in payload:
                    issue = payload['issue']
                    if not isinstance(issue, dict):
                        return False
                    
                    # Check for required issue fields
                    required_issue_fields = ['key', 'fields']
                    for field in required_issue_fields:
                        if field not in issue:
                            return False
            
            return True
        except Exception:
            return False
    
    def _deep_sanitize(self, obj: Any) -> Any:
        """Recursively sanitize an object."""
        if isinstance(obj, dict):
            return {key: self._deep_sanitize(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_sanitize(item) for item in obj]
        elif isinstance(obj, str):
            return self._sanitize_string(obj)
        else:
            return obj
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize a string by removing potentially harmful content."""
        if not text:
            return text
        
        # Remove HTML tags if sanitization is enabled
        if self.webhook_validation_config.sanitize_html:
            import re
            
            # Remove potentially dangerous characters/sequences first
            dangerous_patterns = [
                r'javascript:',
                r'vbscript:',
                r'onload\s*=',
                r'onerror\s*=',
                r'onclick\s*=',
                r'onmouseover\s*=',
                r'onfocus\s*=',
                r'onblur\s*=',
                r'alert\s*\(',
                r'eval\s*\(',
                r'document\.',
                r'window\.',
                r'<script[^>]*>.*?</script>',
                r'<iframe[^>]*>.*?</iframe>',
                r'<object[^>]*>.*?</object>',
                r'<embed[^>]*>.*?</embed>'
            ]
            
            for pattern in dangerous_patterns:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
            
            # Simple HTML tag removal (for production, consider using a proper HTML sanitizer)
            text = re.sub(r'<[^>]+>', '', text)
        
        return text
    
    async def queue_notification_for_later_delivery(self, 
                                                  hook_id: str, 
                                                  event_id: str, 
                                                  notification_data: Dict[str, Any]) -> str:
        """
        Queue notification for later delivery when Slack API is unavailable (requirement 8.4).
        
        Args:
            hook_id: ID of the hook that generated the notification
            event_id: ID of the event being processed
            notification_data: Notification data to be delivered later
            
        Returns:
            Queue ID for the notification
        """
        if not self.notification_queue_config.enable_queuing:
            raise HookError(
                "Notification queuing is disabled",
                category=HookErrorCategory.CONFIGURATION_ERROR,
                severity=HookErrorSeverity.MEDIUM
            )
        
        # Start queue processing if not already started
        if self._queue_cleanup_task is None and self.notification_queue_config.enable_queuing:
            self._start_queue_processing()
        
        # Check queue size limit
        if len(self.notification_queue) >= self.notification_queue_config.max_queue_size:
            # Remove oldest notifications to make space
            oldest_id = min(self.notification_queue.keys(), 
                          key=lambda k: self.notification_queue[k].created_at)
            del self.notification_queue[oldest_id]
            self.logger.warning(f"Queue full, removed oldest notification {oldest_id}")
        
        # Create queued notification
        queue_id = str(uuid.uuid4())
        queued_notification = QueuedNotification(
            id=queue_id,
            hook_id=hook_id,
            event_id=event_id,
            notification_data=notification_data,
            created_at=datetime.now(),
            max_retries=self.notification_queue_config.max_retry_attempts
        )
        
        self.notification_queue[queue_id] = queued_notification
        self.metrics.queued_notifications += 1
        
        self.logger.info(f"Notification queued for later delivery: {queue_id}")
        return queue_id
    
    async def process_notification_queue(self) -> int:
        """
        Process queued notifications and attempt delivery.
        
        Returns:
            Number of notifications successfully delivered
        """
        if not self.notification_queue_config.enable_queuing:
            return 0
        
        delivered_count = 0
        failed_notifications = []
        
        for queue_id, notification in list(self.notification_queue.items()):
            try:
                # Check if notification should be retried
                if not notification.should_retry(self.notification_queue_config.retry_interval_minutes):
                    continue
                
                # Check if notification has expired
                age = datetime.now() - notification.created_at
                if age > timedelta(hours=self.notification_queue_config.queue_retention_hours):
                    failed_notifications.append(queue_id)
                    self.logger.warning(f"Notification {queue_id} expired after {age}")
                    continue
                
                # Attempt to deliver notification
                success = await self._attempt_queued_notification_delivery(notification)
                
                if success:
                    delivered_count += 1
                    self.metrics.successful_queue_deliveries += 1
                    del self.notification_queue[queue_id]
                    self.logger.info(f"Successfully delivered queued notification {queue_id}")
                else:
                    # Update retry information
                    notification.retry_count += 1
                    notification.last_retry_at = datetime.now()
                    
                    if notification.retry_count >= notification.max_retries:
                        failed_notifications.append(queue_id)
                        self.logger.error(f"Notification {queue_id} failed after {notification.retry_count} retries")
                
            except Exception as e:
                self.logger.error(f"Error processing queued notification {queue_id}: {e}")
                failed_notifications.append(queue_id)
        
        # Remove failed notifications
        for queue_id in failed_notifications:
            if queue_id in self.notification_queue:
                del self.notification_queue[queue_id]
        
        if delivered_count > 0:
            self.logger.info(f"Processed notification queue: {delivered_count} delivered, {len(failed_notifications)} failed")
        
        return delivered_count
    
    async def _attempt_queued_notification_delivery(self, notification: QueuedNotification) -> bool:
        """
        Attempt to deliver a queued notification.
        
        Args:
            notification: The queued notification to deliver
            
        Returns:
            True if delivery was successful, False otherwise
        """
        try:
            # This would integrate with the actual notification system
            # For now, we'll simulate the delivery attempt
            
            # Check if Slack API is available by testing circuit breaker
            slack_cb = self.circuit_breakers.get('slack_api')
            if slack_cb and slack_cb.state == CircuitBreakerState.OPEN:
                self.logger.debug(f"Slack API circuit breaker is open, skipping delivery of {notification.id}")
                return False
            
            # TODO: Integrate with actual Slack notification delivery
            # This would call the actual notification delivery service
            self.logger.debug(f"Attempting delivery of queued notification {notification.id}")
            
            # Simulate successful delivery for now
            # In real implementation, this would call the notification service
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deliver queued notification {notification.id}: {e}")
            return False
    
    def _start_queue_processing(self):
        """Start background task for processing notification queue."""
        if self._queue_cleanup_task is not None:
            return  # Already started
        
        async def queue_processor():
            while True:
                try:
                    await self.process_notification_queue()
                    await asyncio.sleep(self.notification_queue_config.retry_interval_minutes * 60)
                except Exception as e:
                    self.logger.error(f"Error in queue processor: {e}")
                    await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        try:
            self._queue_cleanup_task = asyncio.create_task(queue_processor())
            self.logger.info("Notification queue processor started")
        except RuntimeError:
            # No event loop running, will start later when needed
            self.logger.debug("No event loop available, queue processor will start when needed")
    
    def stop_queue_processing(self):
        """Stop background queue processing task."""
        if self._queue_cleanup_task:
            self._queue_cleanup_task.cancel()
            self._queue_cleanup_task = None
            self.logger.info("Notification queue processor stopped")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current status of the notification queue."""
        return {
            "queue_size": len(self.notification_queue),
            "max_queue_size": self.notification_queue_config.max_queue_size,
            "queued_notifications": self.metrics.queued_notifications,
            "successful_deliveries": self.metrics.successful_queue_deliveries,
            "queue_enabled": self.notification_queue_config.enable_queuing,
            "oldest_notification": min(
                (n.created_at for n in self.notification_queue.values()),
                default=None
            ),
            "notifications_by_retry_count": {
                str(i): sum(1 for n in self.notification_queue.values() if n.retry_count == i)
                for i in range(self.notification_queue_config.max_retry_attempts + 1)
            }
        }


# Global error handler instance for hooks
default_hook_error_handler = HookErrorHandler()