"""
Secure Webhook Handler

Integrates all security components for webhook processing including
signature verification, access control, audit logging, and rate limiting.
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from fastapi import Request, HTTPException, Header
import asyncio

from devsync_ai.core.webhook_security import (
    WebhookSecurityManager,
    WebhookSecurityConfig,
    SecurityValidationResult
)
from devsync_ai.core.hook_access_control import (
    access_control_manager,
    AccessRequest
)
from devsync_ai.core.audit_logger import (
    audit_logger,
    security_audit_logger,
    AuditEventType
)
from devsync_ai.core.rate_limiter import (
    rate_limiter,
    ActionType,
    RateLimit,
    LimitType
)
from devsync_ai.config import settings

logger = logging.getLogger(__name__)


class SecureWebhookHandler:
    """Secure webhook handler with comprehensive security features."""
    
    def __init__(self):
        self.security_manager = self._initialize_security_manager()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Configure rate limits for different webhook sources
        self._configure_rate_limits()
        
        # Initialize access control
        access_control_manager.initialize_default_users_and_teams()
    
    def _initialize_security_manager(self) -> WebhookSecurityManager:
        """Initialize webhook security manager with configuration."""
        config = WebhookSecurityConfig(
            secret_key=getattr(settings, 'webhook_secret_key', 'default-secret'),
            signature_header="X-Hub-Signature-256",
            timestamp_tolerance_seconds=300,
            rate_limit_requests_per_minute=100,
            rate_limit_burst_size=20
        )
        return WebhookSecurityManager(config)
    
    def _configure_rate_limits(self):
        """Configure rate limits for different webhook sources."""
        # GitHub webhook limits
        github_limits = [
            RateLimit(LimitType.REQUESTS_PER_MINUTE, 100, 60, burst_allowance=20),
            RateLimit(LimitType.REQUESTS_PER_HOUR, 1000, 3600),
            RateLimit(LimitType.CONCURRENT_REQUESTS, 10, 0)
        ]
        rate_limiter.configure_limits("github", ActionType.WEBHOOK_REQUEST, github_limits)
        
        # JIRA webhook limits
        jira_limits = [
            RateLimit(LimitType.REQUESTS_PER_MINUTE, 200, 60, burst_allowance=50),
            RateLimit(LimitType.REQUESTS_PER_HOUR, 2000, 3600),
            RateLimit(LimitType.CONCURRENT_REQUESTS, 15, 0)
        ]
        rate_limiter.configure_limits("jira", ActionType.WEBHOOK_REQUEST, jira_limits)
        
        # Slack webhook limits
        slack_limits = [
            RateLimit(LimitType.REQUESTS_PER_MINUTE, 60, 60, burst_allowance=10),
            RateLimit(LimitType.REQUESTS_PER_HOUR, 600, 3600),
            RateLimit(LimitType.CONCURRENT_REQUESTS, 5, 0)
        ]
        rate_limiter.configure_limits("slack", ActionType.WEBHOOK_REQUEST, slack_limits)
    
    async def validate_webhook_security(
        self,
        request: Request,
        webhook_source: str,
        expected_headers: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Comprehensive webhook security validation.
        
        Args:
            request: FastAPI request object
            webhook_source: Source of webhook (github, jira, slack)
            expected_headers: Expected headers for validation
            
        Returns:
            Tuple of (is_valid, error_message, metadata)
        """
        try:
            # Get client identifier
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "")
            client_id = f"{webhook_source}:{client_ip}"
            
            # Get raw payload
            raw_payload = await request.body()
            headers = dict(request.headers)
            
            # Check rate limiting first
            rate_limit_result = await rate_limiter.check_rate_limit(
                client_id, webhook_source, ActionType.WEBHOOK_REQUEST,
                request_size=len(raw_payload),
                metadata={
                    "user_agent": user_agent,
                    "webhook_source": webhook_source
                }
            )
            
            if not rate_limit_result.allowed:
                # Log rate limit violation
                security_audit_logger.log_security_event(
                    event_type=AuditEventType.ACCESS_DENIED,
                    user_id=None,
                    action="webhook_request",
                    result="rate_limited",
                    details={
                        "webhook_source": webhook_source,
                        "client_id": client_id,
                        "rate_limit_exceeded": True,
                        "current_count": rate_limit_result.current_count,
                        "limit_value": rate_limit_result.limit_value
                    },
                    ip_address=client_ip,
                    user_agent=user_agent
                )
                
                return False, f"Rate limit exceeded: {rate_limit_result.error_message}", {
                    "retry_after": rate_limit_result.retry_after_seconds,
                    "reset_time": rate_limit_result.reset_time.isoformat()
                }
            
            # Validate webhook signature and security
            security_result = self.security_manager.validate_webhook_request(
                raw_payload, headers, client_id
            )
            
            if not security_result.is_valid:
                # Log security violation
                security_audit_logger.log_security_event(
                    event_type=AuditEventType.AUTH_FAILURE,
                    user_id=None,
                    action="webhook_signature_verification",
                    result="failure",
                    details={
                        "webhook_source": webhook_source,
                        "error_message": security_result.error_message,
                        "risk_level": security_result.risk_level
                    },
                    ip_address=client_ip,
                    user_agent=user_agent
                )
                
                return False, security_result.error_message, {
                    "risk_level": security_result.risk_level
                }
            
            # Log successful validation
            security_audit_logger.log_security_event(
                event_type=AuditEventType.AUTH_SUCCESS,
                user_id=None,
                action="webhook_validation",
                result="success",
                details={
                    "webhook_source": webhook_source,
                    "security_metadata": security_result.metadata
                },
                ip_address=client_ip,
                user_agent=user_agent
            )
            
            # Sanitize payload
            try:
                payload_dict = json.loads(raw_payload.decode())
                sanitized_payload = self.security_manager.sanitize_payload(payload_dict)
            except json.JSONDecodeError:
                sanitized_payload = {}
            
            return True, None, {
                "sanitized_payload": sanitized_payload,
                "security_metadata": security_result.metadata,
                "rate_limit_metadata": rate_limit_result.metadata,
                "client_id": client_id
            }
            
        except Exception as e:
            self.logger.error(f"Error in webhook security validation: {e}")
            
            # Log security error
            security_audit_logger.log_security_event(
                event_type=AuditEventType.SYSTEM_ERROR,
                user_id=None,
                action="webhook_security_validation",
                result="error",
                details={
                    "error_message": str(e),
                    "webhook_source": webhook_source
                },
                ip_address=request.client.host if request.client else "unknown"
            )
            
            return False, f"Security validation error: {str(e)}", {}
    
    async def process_webhook_with_security(
        self,
        request: Request,
        webhook_source: str,
        event_type: str,
        processor_func,
        team_id: str = "default",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process webhook with full security validation and audit logging.
        
        Args:
            request: FastAPI request object
            webhook_source: Source of webhook (github, jira, slack)
            event_type: Type of webhook event
            processor_func: Function to process the webhook payload
            team_id: Team ID for access control
            user_id: User ID if available
            
        Returns:
            Processing result dictionary
        """
        start_time = datetime.now()
        client_ip = request.client.host if request.client else "unknown"
        
        try:
            # Validate security
            is_valid, error_message, metadata = await self.validate_webhook_security(
                request, webhook_source
            )
            
            if not is_valid:
                # Log webhook processing failure
                audit_logger.log_webhook_event(
                    webhook_source=webhook_source,
                    event_type=event_type,
                    result="security_failure",
                    error_message=error_message,
                    ip_address=client_ip
                )
                
                raise HTTPException(
                    status_code=401 if "signature" in error_message.lower() else 429,
                    detail=error_message
                )
            
            # Check access control if user_id provided
            if user_id:
                access_result = access_control_manager.check_hook_access(
                    user_id, team_id, "execute"
                )
                
                if not access_result.granted:
                    # Log access denied
                    security_audit_logger.log_access_attempt(
                        user_id=user_id,
                        resource_type="webhook",
                        resource_id=f"{webhook_source}:{event_type}",
                        action="execute",
                        result="denied",
                        team_id=team_id,
                        ip_address=client_ip
                    )
                    
                    raise HTTPException(
                        status_code=403,
                        detail=f"Access denied: {access_result.reason}"
                    )
                
                # Log successful access
                security_audit_logger.log_access_attempt(
                    user_id=user_id,
                    resource_type="webhook",
                    resource_id=f"{webhook_source}:{event_type}",
                    action="execute",
                    result="granted",
                    team_id=team_id,
                    ip_address=client_ip
                )
            
            # Process webhook payload
            sanitized_payload = metadata.get("sanitized_payload", {})
            
            # Execute processor function
            if asyncio.iscoroutinefunction(processor_func):
                result = await processor_func(sanitized_payload, event_type)
            else:
                result = processor_func(sanitized_payload, event_type)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log successful webhook processing
            audit_logger.log_webhook_event(
                webhook_source=webhook_source,
                event_type=event_type,
                result="success",
                processing_time_ms=processing_time,
                ip_address=client_ip
            )
            
            # Release concurrent request count
            client_id = metadata.get("client_id")
            if client_id:
                rate_limiter.release_concurrent_request(client_id)
            
            return {
                "status": "success",
                "result": result,
                "processing_time_ms": processing_time,
                "security_metadata": metadata.get("security_metadata", {}),
                "timestamp": datetime.now().isoformat()
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Calculate processing time for error case
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log webhook processing error
            audit_logger.log_webhook_event(
                webhook_source=webhook_source,
                event_type=event_type,
                result="error",
                processing_time_ms=processing_time,
                error_message=str(e),
                ip_address=client_ip
            )
            
            self.logger.error(f"Error processing {webhook_source} webhook: {e}")
            
            # Return error response instead of raising exception to prevent retries
            return {
                "status": "error",
                "error": str(e),
                "processing_time_ms": processing_time,
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status."""
        try:
            # Get rate limiter status for different sources
            github_status = rate_limiter.get_client_status("github:unknown")
            jira_status = rate_limiter.get_client_status("jira:unknown")
            slack_status = rate_limiter.get_client_status("slack:unknown")
            
            return {
                "security_manager": {
                    "initialized": True,
                    "signature_verification": "enabled",
                    "rate_limiting": "enabled",
                    "abuse_detection": "enabled"
                },
                "access_control": {
                    "initialized": True,
                    "team_count": len(access_control_manager.team_controller.teams),
                    "user_count": len(access_control_manager.team_controller.users)
                },
                "rate_limiting": {
                    "github": github_status,
                    "jira": jira_status,
                    "slack": slack_status
                },
                "audit_logging": {
                    "enabled": True,
                    "log_file": audit_logger.log_file
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting security status: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Global secure webhook handler instance
secure_webhook_handler = SecureWebhookHandler()