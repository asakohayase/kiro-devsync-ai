"""Comprehensive error handling system for message formatting."""

import time
import random
import logging
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque

from .exceptions import (
    TemplateError, DataValidationError, FormattingError, BlockKitError,
    SlackAPIError, NetworkError, RateLimitError, TemplateRenderingError,
    ConfigurationError, ErrorSeverity, ErrorCategory
)
from .message_formatter import SlackMessage, TemplateConfig


class FallbackLevel(Enum):
    """Levels of fallback strategies."""
    RICH_FORMATTING = "rich_formatting"
    SIMPLE_BLOCKS = "simple_blocks"
    PLAIN_TEXT = "plain_text"
    MINIMAL_MESSAGE = "minimal_message"
    ERROR_MESSAGE = "error_message"


class RetryStrategy(Enum):
    """Retry strategies for different error types."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    backoff_multiplier: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior."""
    enable_fallbacks: bool = True
    max_fallback_level: FallbackLevel = FallbackLevel.PLAIN_TEXT
    preserve_interactive_elements: bool = False
    include_error_details: bool = False
    notify_users_of_degradation: bool = True


@dataclass
class ErrorMetrics:
    """Error metrics for monitoring."""
    total_errors: int = 0
    errors_by_category: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors_by_severity: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    recovery_success_rate: float = 0.0
    average_recovery_time: float = 0.0
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def add_error(self, error: TemplateError, recovery_time: Optional[float] = None):
        """Add error to metrics."""
        self.total_errors += 1
        self.errors_by_category[error.category.value] += 1
        self.errors_by_severity[error.severity.value] += 1
        
        error_record = {
            'timestamp': datetime.now(),
            'category': error.category.value,
            'severity': error.severity.value,
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


@dataclass
class ErrorHandlerConfig:
    """Configuration for error handler."""
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    fallback_config: FallbackConfig = field(default_factory=FallbackConfig)
    enable_monitoring: bool = True
    enable_alerting: bool = True
    alert_threshold_errors_per_minute: int = 10
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 60  # seconds


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for error handling."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time and time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise SlackAPIError("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class ComprehensiveErrorHandler:
    """Comprehensive error handling system for message formatting."""
    
    def __init__(self, config: Optional[ErrorHandlerConfig] = None):
        """Initialize error handler."""
        self.config = config or ErrorHandlerConfig()
        self.logger = logging.getLogger(__name__)
        
        # Error metrics
        self.metrics = ErrorMetrics()
        
        # Circuit breakers for different services
        self.circuit_breakers = {
            'slack_api': CircuitBreaker(
                self.config.circuit_breaker_failure_threshold,
                self.config.circuit_breaker_timeout
            ),
            'template_rendering': CircuitBreaker(3, 30),
            'data_validation': CircuitBreaker(10, 10)
        }
        
        # Alert tracking
        self._alert_window = deque(maxlen=100)
        
        self.logger.info("ComprehensiveErrorHandler initialized")
    
    def handle_with_recovery(self, 
                           operation: Callable,
                           data: Dict[str, Any],
                           template_type: Optional[str] = None,
                           *args, **kwargs) -> SlackMessage:
        """Handle operation with comprehensive error recovery."""
        start_time = time.time()
        last_error = None
        
        # Try the operation with retries
        for attempt in range(self.config.retry_config.max_attempts):
            try:
                # Use circuit breaker if applicable
                circuit_breaker = self._get_circuit_breaker(operation)
                if circuit_breaker:
                    result = circuit_breaker.call(operation, data, *args, **kwargs)
                else:
                    result = operation(data, *args, **kwargs)
                
                # Success - record recovery time if this wasn't the first attempt
                if attempt > 0 and last_error:
                    recovery_time = time.time() - start_time
                    self.metrics.add_error(last_error, recovery_time)
                    self.logger.info(f"Recovered from error after {attempt} attempts in {recovery_time:.2f}s")
                
                return result
                
            except Exception as e:
                last_error = self._classify_error(e, template_type)
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                # Check if error is recoverable
                if not getattr(last_error, 'recoverable', True):
                    self.logger.error(f"Non-recoverable error: {last_error}")
                    break
                
                # Apply retry delay if not the last attempt
                if attempt < self.config.retry_config.max_attempts - 1:
                    delay = self._calculate_retry_delay(attempt, last_error)
                    if delay > 0:
                        self.logger.debug(f"Retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
        
        # All retries failed - apply fallback strategies
        self.logger.error(f"All retry attempts failed, applying fallback strategies")
        self.metrics.add_error(last_error)
        
        return self._apply_fallback_strategies(last_error, data, template_type)
    
    def _classify_error(self, error: Exception, template_type: Optional[str] = None) -> TemplateError:
        """Classify and enhance error with context."""
        if isinstance(error, TemplateError):
            return error
        
        # Classify common error types
        error_message = str(error)
        error_type = type(error).__name__
        
        if 'validation' in error_message.lower() or 'required' in error_message.lower():
            return DataValidationError(
                f"Data validation failed: {error_message}",
                template_type=template_type
            )
        elif 'block' in error_message.lower() or 'slack' in error_message.lower():
            return BlockKitError(
                f"Block Kit validation failed: {error_message}"
            )
        elif 'network' in error_message.lower() or 'timeout' in error_message.lower():
            return NetworkError(
                f"Network error: {error_message}",
                original_error=error
            )
        elif 'rate' in error_message.lower() and 'limit' in error_message.lower():
            return RateLimitError(
                f"Rate limit exceeded: {error_message}",
                retry_after=60  # Default retry after
            )
        else:
            return FormattingError(
                f"Formatting error ({error_type}): {error_message}",
                template_type=template_type,
                original_error=error
            )
    
    def _get_circuit_breaker(self, operation: Callable) -> Optional[CircuitBreaker]:
        """Get appropriate circuit breaker for operation."""
        operation_name = getattr(operation, '__name__', str(operation))
        
        if 'slack' in operation_name.lower() or 'api' in operation_name.lower():
            return self.circuit_breakers['slack_api']
        elif 'template' in operation_name.lower() or 'render' in operation_name.lower():
            return self.circuit_breakers['template_rendering']
        elif 'validate' in operation_name.lower():
            return self.circuit_breakers['data_validation']
        
        return None
    
    def _calculate_retry_delay(self, attempt: int, error: TemplateError) -> float:
        """Calculate retry delay based on strategy and error type."""
        config = self.config.retry_config
        
        # Special handling for rate limit errors
        if isinstance(error, RateLimitError) and error.retry_after:
            return min(error.retry_after, config.max_delay)
        
        # Calculate base delay
        if config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.backoff_multiplier ** attempt)
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * (attempt + 1)
        elif config.strategy == RetryStrategy.FIXED_DELAY:
            delay = config.base_delay
        else:  # NO_RETRY
            return 0
        
        # Apply jitter to avoid thundering herd
        if config.jitter:
            delay *= (0.5 + random.random() * 0.5)
        
        # Respect max delay
        return min(delay, config.max_delay)
    
    def _apply_fallback_strategies(self, 
                                 error: TemplateError, 
                                 data: Dict[str, Any],
                                 template_type: Optional[str] = None) -> SlackMessage:
        """Apply progressive fallback strategies."""
        
        if not self.config.fallback_config.enable_fallbacks:
            return self._create_error_message(error, data)
        
        # Try fallback levels in order
        fallback_levels = [
            FallbackLevel.SIMPLE_BLOCKS,
            FallbackLevel.PLAIN_TEXT,
            FallbackLevel.MINIMAL_MESSAGE,
            FallbackLevel.ERROR_MESSAGE
        ]
        
        for level in fallback_levels:
            if level.value > self.config.fallback_config.max_fallback_level.value:
                break
            
            try:
                self.logger.info(f"Attempting fallback level: {level.value}")
                return self._create_fallback_message(level, error, data, template_type)
            except Exception as fallback_error:
                self.logger.warning(f"Fallback level {level.value} failed: {fallback_error}")
                continue
        
        # Last resort - create minimal error message
        return self._create_minimal_error_message(error, data)
    
    def _create_fallback_message(self, 
                               level: FallbackLevel,
                               error: TemplateError,
                               data: Dict[str, Any],
                               template_type: Optional[str] = None) -> SlackMessage:
        """Create fallback message at specified level."""
        
        if level == FallbackLevel.SIMPLE_BLOCKS:
            return self._create_simple_blocks_message(data, template_type)
        elif level == FallbackLevel.PLAIN_TEXT:
            return self._create_plain_text_message(data, template_type)
        elif level == FallbackLevel.MINIMAL_MESSAGE:
            return self._create_minimal_message(data, template_type)
        else:  # ERROR_MESSAGE
            return self._create_error_message(error, data)
    
    def _create_simple_blocks_message(self, 
                                    data: Dict[str, Any], 
                                    template_type: Optional[str] = None) -> SlackMessage:
        """Create simple blocks message without rich formatting."""
        
        # Extract basic information
        title = data.get('title', data.get('summary', 'Update'))
        description = data.get('description', data.get('body', ''))
        author = data.get('author', data.get('user', {}).get('name', 'Unknown'))
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📄 {title}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Author:* {author}\n{description[:500]}"
                }
            }
        ]
        
        # Add degradation notice if configured
        if self.config.fallback_config.notify_users_of_degradation:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "⚠️ _Simplified formatting due to technical issues_"
                    }
                ]
            })
        
        return SlackMessage(
            blocks=blocks,
            text=f"{title} by {author}: {description[:200]}",
            metadata={
                "fallback_level": "simple_blocks",
                "template_type": template_type,
                "degraded": True
            }
        )
    
    def _create_plain_text_message(self, 
                                 data: Dict[str, Any], 
                                 template_type: Optional[str] = None) -> SlackMessage:
        """Create plain text message."""
        
        title = data.get('title', data.get('summary', 'Update'))
        description = data.get('description', data.get('body', ''))
        author = data.get('author', data.get('user', {}).get('name', 'Unknown'))
        
        text_content = f"{title}\n\nBy: {author}\n\n{description[:300]}"
        
        if self.config.fallback_config.notify_users_of_degradation:
            text_content += "\n\n⚠️ Note: Rich formatting unavailable due to technical issues"
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": text_content,
                    "emoji": True
                }
            }
        ]
        
        return SlackMessage(
            blocks=blocks,
            text=text_content,
            metadata={
                "fallback_level": "plain_text",
                "template_type": template_type,
                "degraded": True
            }
        )
    
    def _create_minimal_message(self, 
                              data: Dict[str, Any], 
                              template_type: Optional[str] = None) -> SlackMessage:
        """Create minimal message with just essential information."""
        
        title = data.get('title', data.get('summary', 'System Update'))
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": f"📄 {title}",
                    "emoji": True
                }
            }
        ]
        
        return SlackMessage(
            blocks=blocks,
            text=title,
            metadata={
                "fallback_level": "minimal_message",
                "template_type": template_type,
                "degraded": True
            }
        )
    
    def _create_error_message(self, error: TemplateError, data: Dict[str, Any]) -> SlackMessage:
        """Create error message for display."""
        
        error_title = "⚠️ Message Formatting Error"
        error_text = "Unable to format message properly."
        
        if self.config.fallback_config.include_error_details:
            error_text += f"\n\nError: {str(error)}"
            if hasattr(error, 'category'):
                error_text += f"\nCategory: {error.category.value}"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": error_title,
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": error_text
                }
            }
        ]
        
        return SlackMessage(
            blocks=blocks,
            text=f"{error_title}: {str(error)}",
            metadata={
                "error": True,
                "error_category": error.category.value if hasattr(error, 'category') else 'unknown',
                "original_data": data
            }
        )
    
    def _create_minimal_error_message(self, error: TemplateError, data: Dict[str, Any]) -> SlackMessage:
        """Create minimal error message as last resort."""
        
        text = "⚠️ System notification unavailable"
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": text,
                    "emoji": True
                }
            }
        ]
        
        return SlackMessage(
            blocks=blocks,
            text=text,
            metadata={"error": True, "minimal_fallback": True}
        )
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get comprehensive error metrics."""
        return {
            "total_errors": self.metrics.total_errors,
            "errors_by_category": dict(self.metrics.errors_by_category),
            "errors_by_severity": dict(self.metrics.errors_by_severity),
            "recovery_success_rate": self.metrics.recovery_success_rate,
            "average_recovery_time": self.metrics.average_recovery_time,
            "recent_errors_count": len(self.metrics.recent_errors),
            "circuit_breaker_states": {
                name: breaker.state.value 
                for name, breaker in self.circuit_breakers.items()
            }
        }
    
    def should_alert(self) -> bool:
        """Check if error rate exceeds alert threshold."""
        if not self.config.enable_alerting:
            return False
        
        # Check error rate in last minute
        one_minute_ago = datetime.now() - timedelta(minutes=1)
        recent_errors = [
            e for e in self.metrics.recent_errors 
            if e['timestamp'] > one_minute_ago
        ]
        
        return len(recent_errors) >= self.config.alert_threshold_errors_per_minute
    
    def reset_metrics(self):
        """Reset error metrics (useful for testing)."""
        self.metrics = ErrorMetrics()
        for breaker in self.circuit_breakers.values():
            breaker.failure_count = 0
            breaker.state = CircuitBreakerState.CLOSED


# Global error handler instance
default_error_handler = ComprehensiveErrorHandler()