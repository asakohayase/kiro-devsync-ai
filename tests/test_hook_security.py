"""
Comprehensive security tests for the hook system.

Tests webhook signature verification, access control, audit logging,
rate limiting, and abuse prevention mechanisms.
"""

import pytest
import asyncio
import time
import hmac
import hashlib
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from devsync_ai.core.webhook_security import (
    WebhookSecurityConfig,
    WebhookSignatureVerifier,
    RateLimiter,
    WebhookSecurityManager,
    SecurityValidationResult
)
from devsync_ai.core.hook_access_control import (
    HookAccessControlManager,
    User,
    Team,
    Role,
    Permission,
    AccessRequest,
    TeamAccessController
)
from devsync_ai.core.audit_logger import (
    AuditLogger,
    SecurityAuditLogger,
    AuditEvent,
    AuditEventType,
    AuditSeverity
)
from devsync_ai.core.rate_limiter import (
    AdvancedRateLimiter,
    RateLimit,
    LimitType,
    ActionType,
    TokenBucket,
    SlidingWindowCounter
)


class TestWebhookSecurity:
    """Test webhook security features."""
    
    @pytest.fixture
    def security_config(self):
        return WebhookSecurityConfig(
            secret_key="test-secret-key",
            signature_header="X-Hub-Signature-256",
            timestamp_tolerance_seconds=300,
            rate_limit_requests_per_minute=100,
            rate_limit_burst_size=20
        )
    
    @pytest.fixture
    def signature_verifier(self, security_config):
        return WebhookSignatureVerifier(security_config)
    
    @pytest.fixture
    def rate_limiter_instance(self, security_config):
        return RateLimiter(security_config)
    
    @pytest.fixture
    def security_manager(self, security_config):
        return WebhookSecurityManager(security_config)
    
    def test_valid_signature_verification(self, signature_verifier):
        """Test valid signature verification."""
        payload = b'{"test": "data"}'
        signature = hmac.new(
            b"test-secret-key",
            payload,
            hashlib.sha256
        ).hexdigest()
        
        result = signature_verifier.verify_signature(payload, f"sha256={signature}")
        
        assert result.is_valid
        assert result.error_message is None
        assert result.risk_level == "low"
        assert result.metadata["algorithm"] == "sha256"
    
    def test_invalid_signature_verification(self, signature_verifier):
        """Test invalid signature verification."""
        payload = b'{"test": "data"}'
        invalid_signature = "invalid_signature"
        
        result = signature_verifier.verify_signature(payload, f"sha256={invalid_signature}")
        
        assert not result.is_valid
        assert "Invalid signature" in result.error_message
        assert result.risk_level == "high"
    
    def test_missing_signature_verification(self, signature_verifier):
        """Test missing signature handling."""
        payload = b'{"test": "data"}'
        
        result = signature_verifier.verify_signature(payload, "")
        
        assert not result.is_valid
        assert "Missing signature header" in result.error_message
        assert result.risk_level == "high"
    
    def test_legacy_sha1_signature(self, signature_verifier):
        """Test legacy SHA1 signature support."""
        payload = b'{"test": "data"}'
        signature = hmac.new(
            b"test-secret-key",
            payload,
            hashlib.sha1
        ).hexdigest()
        
        result = signature_verifier.verify_signature(payload, f"sha1={signature}")
        
        assert result.is_valid
        assert result.risk_level == "medium"  # SHA1 is deprecated
        assert result.metadata["algorithm"] == "sha1"
        assert result.metadata["deprecated"] is True
    
    def test_valid_timestamp_verification(self, signature_verifier):
        """Test valid timestamp verification."""
        current_timestamp = str(int(time.time()))
        
        result = signature_verifier.verify_timestamp(current_timestamp)
        
        assert result.is_valid
        assert result.error_message is None
        assert result.metadata["time_diff_seconds"] < 5
    
    def test_expired_timestamp_verification(self, signature_verifier):
        """Test expired timestamp verification."""
        old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago
        
        result = signature_verifier.verify_timestamp(old_timestamp)
        
        assert not result.is_valid
        assert "Timestamp too old" in result.error_message
        assert result.risk_level == "high"
    
    def test_invalid_timestamp_format(self, signature_verifier):
        """Test invalid timestamp format."""
        invalid_timestamp = "not_a_timestamp"
        
        result = signature_verifier.verify_timestamp(invalid_timestamp)
        
        assert not result.is_valid
        assert "Invalid timestamp format" in result.error_message
        assert result.risk_level == "medium"
    
    def test_rate_limiting_within_limits(self, rate_limiter_instance):
        """Test rate limiting when within limits."""
        client_id = "test_client"
        
        result = rate_limiter_instance.check_rate_limit(client_id)
        
        assert result.is_valid
        assert result.metadata["recent_requests"] == 1
    
    def test_rate_limiting_exceeded(self, rate_limiter_instance):
        """Test rate limiting when limits are exceeded."""
        client_id = "test_client"
        
        # Make requests up to the limit
        for _ in range(100):
            rate_limiter_instance.check_rate_limit(client_id)
        
        # This should exceed the limit
        result = rate_limiter_instance.check_rate_limit(client_id)
        
        assert not result.is_valid
        assert ("Rate limit exceeded" in result.error_message or 
                "Burst rate limit exceeded" in result.error_message)
        assert result.risk_level == "high"
    
    def test_burst_rate_limiting(self, rate_limiter_instance):
        """Test burst rate limiting."""
        client_id = "test_client"
        
        # Make burst requests
        for _ in range(20):
            rate_limiter_instance.check_rate_limit(client_id)
        
        # This should exceed burst limit
        result = rate_limiter_instance.check_rate_limit(client_id)
        
        assert not result.is_valid
        assert "Burst rate limit exceeded" in result.error_message
        assert result.risk_level == "high"
    
    def test_comprehensive_security_validation(self, security_manager):
        """Test comprehensive security validation."""
        payload = b'{"test": "data"}'
        signature = hmac.new(
            b"test-secret-key",
            payload,
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "X-Hub-Signature-256": f"sha256={signature}",
            "X-Hub-Timestamp": str(int(time.time()))
        }
        
        result = security_manager.validate_webhook_request(
            payload, headers, "test_client"
        )
        
        assert result.is_valid
        assert result.error_message is None
        assert "rate_limit" in result.metadata
        assert "signature" in result.metadata
        assert result.metadata["timestamp_validated"] is True
    
    def test_payload_sanitization(self, security_manager):
        """Test payload sanitization."""
        dangerous_payload = {
            "data": "normal_data",
            "script": "<script>alert('xss')</script>",
            "javascript:": "dangerous_code",
            "__proto__": {"polluted": True},
            "nested": {
                "script": "more_dangerous_code",
                "normal": "safe_data"
            }
        }
        
        sanitized = security_manager.sanitize_payload(dangerous_payload)
        
        assert "script" not in sanitized
        assert "__proto__" not in sanitized
        # Check that javascript: values are cleaned
        assert all("javascript:" not in str(v) for v in sanitized.values() if isinstance(v, str))
        assert sanitized["data"] == "normal_data"
        assert sanitized["nested"]["normal"] == "safe_data"
        assert "script" not in sanitized["nested"]


class TestAccessControl:
    """Test access control features."""
    
    @pytest.fixture
    def access_controller(self):
        controller = TeamAccessController()
        
        # Add test user
        user = User(
            user_id="test_user",
            username="testuser",
            email="test@example.com",
            teams=["team1"],
            global_roles=[Role.DEVELOPER],
            team_roles={"team1": [Role.TEAM_LEAD]},
            created_at=datetime.now()
        )
        controller.add_user(user)
        
        # Add test team
        team = Team(
            team_id="team1",
            name="Test Team",
            description="Test team for access control",
            members=["test_user"],
            admins=["test_user"],
            created_at=datetime.now()
        )
        controller.add_team(team)
        
        return controller
    
    @pytest.fixture
    def access_manager(self):
        manager = HookAccessControlManager()
        manager.initialize_default_users_and_teams()
        return manager
    
    def test_user_permissions(self, access_controller):
        """Test user permission calculation."""
        permissions = access_controller.get_user_permissions("test_user", "team1")
        
        # Should have developer permissions plus team lead permissions
        assert Permission.READ_HOOKS in permissions
        assert Permission.WRITE_HOOKS in permissions
        assert Permission.MANAGE_TEAM in permissions
        assert Permission.DELETE_HOOKS in permissions
    
    def test_team_membership_check(self, access_controller):
        """Test team membership verification."""
        assert access_controller.check_team_membership("test_user", "team1")
        assert not access_controller.check_team_membership("test_user", "nonexistent_team")
        assert not access_controller.check_team_membership("nonexistent_user", "team1")
    
    def test_team_admin_check(self, access_controller):
        """Test team admin verification."""
        assert access_controller.check_team_admin("test_user", "team1")
        assert not access_controller.check_team_admin("test_user", "nonexistent_team")
    
    def test_access_validation_success(self, access_controller):
        """Test successful access validation."""
        request = AccessRequest(
            user_id="test_user",
            team_id="team1",
            resource_type="hook",
            resource_id="test-hook",
            action="read"
        )
        
        result = access_controller.validate_access(request)
        
        assert result.granted
        assert result.reason == "Access granted"
        assert Permission.READ_HOOKS in result.user_permissions
    
    def test_access_validation_failure_no_membership(self, access_controller):
        """Test access validation failure due to no team membership."""
        request = AccessRequest(
            user_id="test_user",
            team_id="team2",  # User not member of this team
            resource_type="hook",
            resource_id="test-hook",
            action="read"
        )
        
        result = access_controller.validate_access(request)
        
        assert not result.granted
        assert "not member of team" in result.reason
    
    def test_access_validation_failure_insufficient_permissions(self, access_controller):
        """Test access validation failure due to insufficient permissions."""
        # Add user with limited permissions
        limited_user = User(
            user_id="limited_user",
            username="limited",
            email="limited@example.com",
            teams=["team1"],
            global_roles=[Role.VIEWER],
            team_roles={"team1": [Role.VIEWER]}
        )
        access_controller.add_user(limited_user)
        
        request = AccessRequest(
            user_id="limited_user",
            team_id="team1",
            resource_type="hook",
            resource_id="test-hook",
            action="write"  # Viewer doesn't have write permissions
        )
        
        result = access_controller.validate_access(request)
        
        assert not result.granted
        assert "Missing permissions" in result.reason
        assert Permission.WRITE_HOOKS in result.required_permissions
    
    def test_hook_access_check(self, access_manager):
        """Test hook access checking."""
        result = access_manager.check_hook_access("admin", "default", "read")
        
        assert result.granted
        assert result.reason == "Access granted"
    
    def test_configuration_access_check(self, access_manager):
        """Test configuration access checking."""
        result = access_manager.check_configuration_access("admin", "default", "write")
        
        assert result.granted
        assert result.reason == "Access granted"


class TestAuditLogging:
    """Test audit logging features."""
    
    @pytest.fixture
    def audit_logger(self):
        return AuditLogger()
    
    @pytest.fixture
    def security_audit_logger(self, audit_logger):
        return SecurityAuditLogger(audit_logger)
    
    def test_audit_event_creation(self):
        """Test audit event creation and serialization."""
        event = AuditEvent(
            event_id="test-event-123",
            event_type=AuditEventType.CONFIG_UPDATE,
            severity=AuditSeverity.MEDIUM,
            timestamp=datetime.now(),
            user_id="test_user",
            team_id="test_team",
            resource_type="hook",
            resource_id="hook-123",
            action="update",
            result="success",
            details={"field": "value"},
            ip_address="192.168.1.1"
        )
        
        event_dict = event.to_dict()
        assert event_dict["event_type"] == "config_update"
        assert event_dict["severity"] == "medium"
        assert event_dict["user_id"] == "test_user"
        
        event_json = event.to_json()
        assert "test-event-123" in event_json
        assert "config_update" in event_json
    
    def test_configuration_change_logging(self, audit_logger):
        """Test configuration change logging."""
        with patch.object(audit_logger, 'log_event', return_value=True) as mock_log:
            result = audit_logger.log_configuration_change(
                user_id="test_user",
                team_id="test_team",
                action="update",
                config_type="hook_config",
                config_id="config-123",
                old_config={"enabled": False},
                new_config={"enabled": True}
            )
            
            assert result is True
            mock_log.assert_called_once()
            
            # Check the logged event
            logged_event = mock_log.call_args[0][0]
            assert logged_event.event_type == AuditEventType.CONFIG_UPDATE
            assert logged_event.user_id == "test_user"
            assert logged_event.details["old_config"] == {"enabled": False}
            assert logged_event.details["new_config"] == {"enabled": True}
    
    def test_hook_operation_logging(self, audit_logger):
        """Test hook operation logging."""
        with patch.object(audit_logger, 'log_event', return_value=True) as mock_log:
            result = audit_logger.log_hook_operation(
                user_id="test_user",
                team_id="test_team",
                action="execute",
                hook_type="status_change",
                hook_id="hook-123",
                execution_result={"success": True, "duration_ms": 150}
            )
            
            assert result is True
            mock_log.assert_called_once()
            
            logged_event = mock_log.call_args[0][0]
            assert logged_event.event_type == AuditEventType.HOOK_EXECUTE
            assert logged_event.severity == AuditSeverity.HIGH
            assert logged_event.details["hook_type"] == "status_change"
    
    def test_security_event_logging(self, security_audit_logger):
        """Test security event logging."""
        with patch.object(security_audit_logger.audit_logger, 'log_event', return_value=True) as mock_log:
            result = security_audit_logger.log_authentication_attempt(
                user_id="test_user",
                result="failure",
                method="password",
                ip_address="192.168.1.1",
                failure_reason="invalid_password"
            )
            
            assert result is True
            mock_log.assert_called_once()
            
            logged_event = mock_log.call_args[0][0]
            assert logged_event.event_type == AuditEventType.AUTH_FAILURE
            assert logged_event.severity == AuditSeverity.HIGH
            assert logged_event.details["failure_reason"] == "invalid_password"
    
    def test_access_attempt_logging(self, security_audit_logger):
        """Test access attempt logging."""
        with patch.object(security_audit_logger.audit_logger, 'log_event', return_value=True) as mock_log:
            result = security_audit_logger.log_access_attempt(
                user_id="test_user",
                resource_type="hook",
                resource_id="hook-123",
                action="read",
                result="success",
                team_id="test_team",
                required_permissions=["read_hooks"]
            )
            
            assert result is True
            mock_log.assert_called_once()
            
            logged_event = mock_log.call_args[0][0]
            assert logged_event.event_type == AuditEventType.ACCESS_GRANTED
            assert logged_event.severity == AuditSeverity.LOW


class TestRateLimiting:
    """Test advanced rate limiting features."""
    
    @pytest.fixture
    def rate_limiter(self):
        return AdvancedRateLimiter()
    
    @pytest.fixture
    def token_bucket(self):
        return TokenBucket(capacity=10, refill_rate=1.0)
    
    @pytest.fixture
    def sliding_window(self):
        return SlidingWindowCounter(window_seconds=60, max_requests=100)
    
    @pytest.mark.asyncio
    async def test_token_bucket_consume_success(self, token_bucket):
        """Test successful token consumption."""
        result = await token_bucket.consume(5)
        assert result is True
        
        status = token_bucket.get_status()
        assert status["current_tokens"] == 5
    
    @pytest.mark.asyncio
    async def test_token_bucket_consume_failure(self, token_bucket):
        """Test token consumption failure when insufficient tokens."""
        # Consume all tokens
        await token_bucket.consume(10)
        
        # This should fail
        result = await token_bucket.consume(1)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_token_bucket_refill(self, token_bucket):
        """Test token bucket refill mechanism."""
        # Consume all tokens
        await token_bucket.consume(10)
        
        # Wait for refill (simulate time passage)
        token_bucket.last_refill = time.time() - 5  # 5 seconds ago
        
        # Should have refilled 5 tokens
        result = await token_bucket.consume(5)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_sliding_window_within_limit(self, sliding_window):
        """Test sliding window when within limits."""
        allowed, count = await sliding_window.is_allowed()
        assert allowed is True
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_sliding_window_exceed_limit(self, sliding_window):
        """Test sliding window when exceeding limits."""
        # Fill up to limit
        for _ in range(100):
            await sliding_window.is_allowed()
        
        # This should be rejected
        allowed, count = await sliding_window.is_allowed()
        assert allowed is False
        assert count == 100
    
    @pytest.mark.asyncio
    async def test_rate_limiter_configuration(self, rate_limiter):
        """Test rate limiter configuration."""
        limits = [
            RateLimit(LimitType.REQUESTS_PER_MINUTE, 60, 60),
            RateLimit(LimitType.CONCURRENT_REQUESTS, 5, 0)
        ]
        
        rate_limiter.configure_limits("test", ActionType.API_REQUEST, limits)
        
        # Check that limits are stored
        assert ("test", ActionType.API_REQUEST) in rate_limiter.rate_limits
        assert len(rate_limiter.rate_limits[("test", ActionType.API_REQUEST)]) == 2
    
    @pytest.mark.asyncio
    async def test_rate_limiter_check_success(self, rate_limiter):
        """Test successful rate limit check."""
        # Configure limits
        limits = [RateLimit(LimitType.REQUESTS_PER_MINUTE, 60, 60)]
        rate_limiter.configure_limits("test", ActionType.API_REQUEST, limits)
        
        result = await rate_limiter.check_rate_limit(
            "test_client", "test", ActionType.API_REQUEST
        )
        
        assert result.allowed is True
        assert result.limit_exceeded is False
    
    @pytest.mark.asyncio
    async def test_abuse_detection(self, rate_limiter):
        """Test abuse pattern detection."""
        client_id = "suspicious_client"
        
        # Simulate rapid requests to trigger abuse detection
        for _ in range(150):
            await rate_limiter.check_rate_limit(
                client_id, "test", ActionType.API_REQUEST
            )
        
        # Check abuse score
        status = rate_limiter.get_client_status(client_id)
        assert status["abuse_score"] > 0
    
    @pytest.mark.asyncio
    async def test_client_blocking(self, rate_limiter):
        """Test client blocking mechanism."""
        client_id = "blocked_client"
        
        # Manually trigger high abuse score
        rate_limiter.abuse_detector.detected_patterns[client_id] = [
            type('Pattern', (), {
                'pattern_type': 'rapid_fire',
                'severity': 'critical',
                'last_detected': datetime.now(),
                'occurrence_count': 10
            })()
        ]
        
        result = await rate_limiter.check_rate_limit(
            client_id, "test", ActionType.API_REQUEST
        )
        
        assert result.allowed is False
        assert "abuse_detected" in result.metadata["reason"]
    
    def test_concurrent_request_tracking(self, rate_limiter):
        """Test concurrent request tracking."""
        client_id = "concurrent_client"
        
        # Track concurrent requests
        rate_limiter.concurrent_requests[client_id] = 5
        
        # Release some requests
        rate_limiter.release_concurrent_request(client_id, 2)
        
        assert rate_limiter.concurrent_requests[client_id] == 3
        
        # Release more than available (should not go negative)
        rate_limiter.release_concurrent_request(client_id, 10)
        
        assert rate_limiter.concurrent_requests[client_id] == 0


class TestSecurityIntegration:
    """Test integration of all security components."""
    
    @pytest.fixture
    def integrated_security_system(self):
        """Set up integrated security system for testing."""
        # Security manager
        security_config = WebhookSecurityConfig(
            secret_key="integration-test-key",
            rate_limit_requests_per_minute=50
        )
        security_manager = WebhookSecurityManager(security_config)
        
        # Access control
        access_manager = HookAccessControlManager()
        access_manager.initialize_default_users_and_teams()
        
        # Audit logging
        audit_logger = AuditLogger()
        security_audit = SecurityAuditLogger(audit_logger)
        
        # Rate limiting
        rate_limiter = AdvancedRateLimiter()
        
        return {
            "security_manager": security_manager,
            "access_manager": access_manager,
            "audit_logger": audit_logger,
            "security_audit": security_audit,
            "rate_limiter": rate_limiter
        }
    
    def test_end_to_end_security_validation(self, integrated_security_system):
        """Test end-to-end security validation flow."""
        security_manager = integrated_security_system["security_manager"]
        access_manager = integrated_security_system["access_manager"]
        security_audit = integrated_security_system["security_audit"]
        
        # 1. Validate webhook security
        payload = b'{"event": "test"}'
        signature = hmac.new(
            b"integration-test-key",
            payload,
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "X-Hub-Signature-256": f"sha256={signature}",
            "X-Hub-Timestamp": str(int(time.time()))
        }
        
        security_result = security_manager.validate_webhook_request(
            payload, headers, "test_client"
        )
        assert security_result.is_valid
        
        # 2. Check access control
        access_result = access_manager.check_hook_access("admin", "default", "execute")
        assert access_result.granted
        
        # 3. Log security events
        with patch.object(security_audit.audit_logger, 'log_event', return_value=True) as mock_log:
            security_audit.log_access_attempt(
                user_id="admin",
                resource_type="hook",
                resource_id="test-hook",
                action="execute",
                result="success"
            )
            mock_log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_security_failure_scenarios(self, integrated_security_system):
        """Test various security failure scenarios."""
        security_manager = integrated_security_system["security_manager"]
        access_manager = integrated_security_system["access_manager"]
        rate_limiter = integrated_security_system["rate_limiter"]
        
        # 1. Invalid signature
        payload = b'{"event": "test"}'
        headers = {"X-Hub-Signature-256": "sha256=invalid_signature"}
        
        security_result = security_manager.validate_webhook_request(
            payload, headers, "test_client"
        )
        assert not security_result.is_valid
        
        # 2. Access denied
        access_result = access_manager.check_hook_access("nonexistent_user", "default", "execute")
        assert not access_result.granted
        
        # 3. Rate limit exceeded
        limits = [RateLimit(LimitType.REQUESTS_PER_MINUTE, 1, 60)]
        rate_limiter.configure_limits("test", ActionType.API_REQUEST, limits)
        
        # First request should succeed
        result1 = await rate_limiter.check_rate_limit("test_client", "test", ActionType.API_REQUEST)
        assert result1.allowed
        
        # Second request should be rate limited
        result2 = await rate_limiter.check_rate_limit("test_client", "test", ActionType.API_REQUEST)
        assert not result2.allowed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])