"""Exception classes for the Slack message template system."""

from typing import Optional, Dict, Any, List
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    DATA_VALIDATION = "data_validation"
    FORMATTING = "formatting"
    BLOCK_KIT = "block_kit"
    SLACK_API = "slack_api"
    NETWORK = "network"
    TEMPLATE_RENDERING = "template_rendering"
    RATE_LIMITING = "rate_limiting"
    AUTHENTICATION = "authentication"
    CONFIGURATION = "configuration"


class TemplateError(Exception):
    """Base exception for template errors."""
    
    def __init__(self, 
                 message: str, 
                 template_type: Optional[str] = None,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 category: ErrorCategory = ErrorCategory.FORMATTING,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.template_type = template_type
        self.severity = severity
        self.category = category
        self.context = context or {}
        self.recoverable = True  # Most errors are recoverable by default


class DataValidationError(TemplateError):
    """Raised when input data is invalid or missing required fields."""
    
    def __init__(self, 
                 message: str, 
                 missing_fields: Optional[List[str]] = None,
                 invalid_fields: Optional[Dict[str, str]] = None,
                 template_type: Optional[str] = None):
        super().__init__(
            message, 
            template_type=template_type,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.DATA_VALIDATION
        )
        self.missing_fields = missing_fields or []
        self.invalid_fields = invalid_fields or {}
        self.recoverable = True


class FormattingError(TemplateError):
    """Raised when message formatting fails."""
    
    def __init__(self, 
                 message: str, 
                 template_type: Optional[str] = None,
                 block_type: Optional[str] = None,
                 original_error: Optional[Exception] = None):
        super().__init__(
            message,
            template_type=template_type,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.FORMATTING
        )
        self.block_type = block_type
        self.original_error = original_error
        self.recoverable = True


class BlockKitError(TemplateError):
    """Raised when Block Kit validation fails."""
    
    def __init__(self, 
                 message: str, 
                 block_data: Optional[Dict[str, Any]] = None,
                 validation_errors: Optional[List[str]] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.BLOCK_KIT
        )
        self.block_data = block_data
        self.validation_errors = validation_errors or []
        self.recoverable = True


class SlackAPIError(TemplateError):
    """Raised when Slack API calls fail."""
    
    def __init__(self, 
                 message: str, 
                 status_code: Optional[int] = None,
                 error_code: Optional[str] = None,
                 retry_after: Optional[int] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH if status_code and status_code >= 500 else ErrorSeverity.MEDIUM,
            category=ErrorCategory.SLACK_API
        )
        self.status_code = status_code
        self.error_code = error_code
        self.retry_after = retry_after
        self.recoverable = status_code != 401 if status_code else True  # Auth errors not recoverable


class NetworkError(TemplateError):
    """Raised when network connectivity issues occur."""
    
    def __init__(self, 
                 message: str, 
                 timeout: Optional[float] = None,
                 original_error: Optional[Exception] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.NETWORK
        )
        self.timeout = timeout
        self.original_error = original_error
        self.recoverable = True


class RateLimitError(SlackAPIError):
    """Raised when Slack API rate limits are exceeded."""
    
    def __init__(self, 
                 message: str, 
                 retry_after: int,
                 limit_type: str = "message"):
        super().__init__(
            message,
            status_code=429,
            error_code="rate_limited",
            retry_after=retry_after
        )
        self.limit_type = limit_type
        self.severity = ErrorSeverity.MEDIUM
        self.category = ErrorCategory.RATE_LIMITING
        self.recoverable = True


class TemplateRenderingError(TemplateError):
    """Raised when template rendering fails."""
    
    def __init__(self, 
                 message: str, 
                 template_type: Optional[str] = None,
                 render_stage: Optional[str] = None,
                 original_error: Optional[Exception] = None):
        super().__init__(
            message,
            template_type=template_type,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.TEMPLATE_RENDERING
        )
        self.render_stage = render_stage
        self.original_error = original_error
        self.recoverable = True


class ConfigurationError(TemplateError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, 
                 message: str, 
                 config_key: Optional[str] = None,
                 expected_type: Optional[str] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.CONFIGURATION
        )
        self.config_key = config_key
        self.expected_type = expected_type
        self.recoverable = False  # Config errors usually require manual intervention