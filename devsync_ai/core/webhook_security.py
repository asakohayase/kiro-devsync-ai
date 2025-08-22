"""
Webhook Security Module

Provides security features for webhook processing including signature verification,
rate limiting, and authentication for the JIRA webhook system.
"""

import hashlib
import hmac
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class WebhookSecurityConfig:
    """Configuration for webhook security settings."""
    secret_key: str
    signature_header: str = "X-Hub-Signature-256"
    timestamp_tolerance_seconds: int = 300  # 5 minutes
    rate_limit_requests_per_minute: int = 100
    rate_limit_burst_size: int = 20


@dataclass
class SecurityValidationResult:
    """Result of security validation."""
    is_valid: bool
    error_message: Optional[str] = None
    risk_level: str = "low"  # low, medium, high, critical
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class WebhookSignatureVerifier:
    """Handles webhook signature verification for JIRA events."""
    
    def __init__(self, config: WebhookSecurityConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def verify_signature(self, payload: bytes, signature: str) -> SecurityValidationResult:
        """
        Verify webhook signature using HMAC-SHA256.
        
        Args:
            payload: Raw webhook payload bytes
            signature: Signature from webhook header
            
        Returns:
            SecurityValidationResult indicating if signature is valid
        """
        try:
            if not signature:
                return SecurityValidationResult(
                    is_valid=False,
                    error_message="Missing signature header",
                    risk_level="high"
                )
            
            # Remove algorithm prefix if present (e.g., "sha256=")
            if signature.startswith("sha256="):
                signature = signature[7:]
            elif signature.startswith("sha1="):
                # Support legacy SHA1 but mark as medium risk
                signature = signature[5:]
                expected_signature = hmac.new(
                    self.config.secret_key.encode(),
                    payload,
                    hashlib.sha1
                ).hexdigest()
                
                if hmac.compare_digest(signature, expected_signature):
                    return SecurityValidationResult(
                        is_valid=True,
                        risk_level="medium",
                        metadata={"algorithm": "sha1", "deprecated": True}
                    )
                else:
                    return SecurityValidationResult(
                        is_valid=False,
                        error_message="Invalid SHA1 signature",
                        risk_level="high"
                    )
            
            # Calculate expected signature using SHA256
            expected_signature = hmac.new(
                self.config.secret_key.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Use constant-time comparison to prevent timing attacks
            if hmac.compare_digest(signature, expected_signature):
                return SecurityValidationResult(
                    is_valid=True,
                    metadata={"algorithm": "sha256"}
                )
            else:
                return SecurityValidationResult(
                    is_valid=False,
                    error_message="Invalid signature",
                    risk_level="high"
                )
                
        except Exception as e:
            self.logger.error(f"Error verifying webhook signature: {e}")
            return SecurityValidationResult(
                is_valid=False,
                error_message=f"Signature verification error: {str(e)}",
                risk_level="critical"
            )
    
    def verify_timestamp(self, timestamp_header: Optional[str]) -> SecurityValidationResult:
        """
        Verify webhook timestamp to prevent replay attacks.
        
        Args:
            timestamp_header: Timestamp from webhook header
            
        Returns:
            SecurityValidationResult indicating if timestamp is valid
        """
        try:
            if not timestamp_header:
                return SecurityValidationResult(
                    is_valid=False,
                    error_message="Missing timestamp header",
                    risk_level="medium"
                )
            
            webhook_timestamp = int(timestamp_header)
            current_timestamp = int(time.time())
            time_diff = abs(current_timestamp - webhook_timestamp)
            
            if time_diff > self.config.timestamp_tolerance_seconds:
                return SecurityValidationResult(
                    is_valid=False,
                    error_message=f"Timestamp too old: {time_diff}s",
                    risk_level="high",
                    metadata={"time_diff_seconds": time_diff}
                )
            
            return SecurityValidationResult(
                is_valid=True,
                metadata={"time_diff_seconds": time_diff}
            )
            
        except (ValueError, TypeError) as e:
            return SecurityValidationResult(
                is_valid=False,
                error_message=f"Invalid timestamp format: {str(e)}",
                risk_level="medium"
            )


class RateLimiter:
    """Rate limiting for webhook requests to prevent abuse."""
    
    def __init__(self, config: WebhookSecurityConfig):
        self.config = config
        self.request_history: Dict[str, list] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def check_rate_limit(self, client_id: str) -> SecurityValidationResult:
        """
        Check if client has exceeded rate limits.
        
        Args:
            client_id: Identifier for the client (IP, user, etc.)
            
        Returns:
            SecurityValidationResult indicating if request is within limits
        """
        try:
            current_time = time.time()
            minute_ago = current_time - 60
            
            # Initialize or clean old requests
            if client_id not in self.request_history:
                self.request_history[client_id] = []
            
            # Remove requests older than 1 minute
            self.request_history[client_id] = [
                req_time for req_time in self.request_history[client_id]
                if req_time > minute_ago
            ]
            
            recent_requests = len(self.request_history[client_id])
            
            # Check burst limit (last 10 seconds)
            ten_seconds_ago = current_time - 10
            burst_requests = len([
                req_time for req_time in self.request_history[client_id]
                if req_time > ten_seconds_ago
            ])
            
            if burst_requests >= self.config.rate_limit_burst_size:
                return SecurityValidationResult(
                    is_valid=False,
                    error_message=f"Burst rate limit exceeded: {burst_requests}/{self.config.rate_limit_burst_size}",
                    risk_level="high",
                    metadata={
                        "burst_requests": burst_requests,
                        "recent_requests": recent_requests
                    }
                )
            
            if recent_requests >= self.config.rate_limit_requests_per_minute:
                return SecurityValidationResult(
                    is_valid=False,
                    error_message=f"Rate limit exceeded: {recent_requests}/{self.config.rate_limit_requests_per_minute}",
                    risk_level="high",
                    metadata={
                        "recent_requests": recent_requests,
                        "burst_requests": burst_requests
                    }
                )
            
            # Record this request
            self.request_history[client_id].append(current_time)
            
            return SecurityValidationResult(
                is_valid=True,
                metadata={
                    "recent_requests": recent_requests + 1,
                    "burst_requests": burst_requests + 1
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error checking rate limit: {e}")
            return SecurityValidationResult(
                is_valid=False,
                error_message=f"Rate limit check error: {str(e)}",
                risk_level="critical"
            )


class WebhookSecurityManager:
    """Main security manager for webhook processing."""
    
    def __init__(self, config: WebhookSecurityConfig):
        self.config = config
        self.signature_verifier = WebhookSignatureVerifier(config)
        self.rate_limiter = RateLimiter(config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def validate_webhook_request(
        self,
        payload: bytes,
        headers: Dict[str, str],
        client_id: str
    ) -> SecurityValidationResult:
        """
        Comprehensive security validation for webhook requests.
        
        Args:
            payload: Raw webhook payload
            headers: Request headers
            client_id: Client identifier for rate limiting
            
        Returns:
            SecurityValidationResult with overall validation status
        """
        try:
            # Check rate limiting first
            rate_limit_result = self.rate_limiter.check_rate_limit(client_id)
            if not rate_limit_result.is_valid:
                self.logger.warning(f"Rate limit exceeded for client {client_id}")
                return rate_limit_result
            
            # Verify signature
            signature = headers.get(self.config.signature_header, "")
            signature_result = self.signature_verifier.verify_signature(payload, signature)
            if not signature_result.is_valid:
                self.logger.warning(f"Invalid signature for client {client_id}")
                return signature_result
            
            # Verify timestamp if present
            timestamp = headers.get("X-Hub-Timestamp") or headers.get("X-Timestamp")
            if timestamp:
                timestamp_result = self.signature_verifier.verify_timestamp(timestamp)
                if not timestamp_result.is_valid:
                    self.logger.warning(f"Invalid timestamp for client {client_id}")
                    return timestamp_result
            
            # All validations passed
            return SecurityValidationResult(
                is_valid=True,
                metadata={
                    "rate_limit": rate_limit_result.metadata,
                    "signature": signature_result.metadata,
                    "timestamp_validated": timestamp is not None
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error validating webhook request: {e}")
            return SecurityValidationResult(
                is_valid=False,
                error_message=f"Security validation error: {str(e)}",
                risk_level="critical"
            )
    
    def sanitize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize webhook payload to prevent injection attacks.
        
        Args:
            payload: Webhook payload dictionary
            
        Returns:
            Sanitized payload dictionary
        """
        try:
            # Create a deep copy to avoid modifying original
            sanitized = json.loads(json.dumps(payload))
            
            # Remove potentially dangerous fields
            dangerous_fields = [
                "script", "javascript", "eval", "exec", 
                "__proto__", "constructor", "prototype"
            ]
            
            def clean_dict(obj):
                if isinstance(obj, dict):
                    return {
                        k: clean_dict(v) for k, v in obj.items()
                        if k not in dangerous_fields
                    }
                elif isinstance(obj, list):
                    return [clean_dict(item) for item in obj]
                elif isinstance(obj, str):
                    # Basic XSS prevention
                    return obj.replace("<script", "&lt;script").replace("javascript:", "")
                else:
                    return obj
            
            return clean_dict(sanitized)
            
        except Exception as e:
            self.logger.error(f"Error sanitizing payload: {e}")
            return {}