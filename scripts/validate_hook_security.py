#!/usr/bin/env python3
"""
Validation script for hook security system.

This script validates that all security components are working correctly
including webhook signature verification, access control, audit logging,
and rate limiting.
"""

import asyncio
import json
import hmac
import hashlib
import time
from datetime import datetime
from typing import Dict, Any

from devsync_ai.core.webhook_security import (
    WebhookSecurityManager,
    WebhookSecurityConfig
)
from devsync_ai.core.hook_access_control import (
    HookAccessControlManager,
    User,
    Team,
    Role
)
from devsync_ai.core.audit_logger import (
    AuditLogger,
    SecurityAuditLogger
)
from devsync_ai.core.rate_limiter import (
    AdvancedRateLimiter,
    RateLimit,
    LimitType,
    ActionType
)


async def test_webhook_security():
    """Test webhook security components."""
    print("🔒 Testing Webhook Security...")
    
    # Initialize security manager
    config = WebhookSecurityConfig(
        secret_key="test-secret-key",
        signature_header="X-Hub-Signature-256"
    )
    security_manager = WebhookSecurityManager(config)
    
    # Test valid signature
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
    
    result = security_manager.validate_webhook_request(payload, headers, "test_client")
    
    if result.is_valid:
        print("  ✅ Webhook signature verification: PASSED")
    else:
        print(f"  ❌ Webhook signature verification: FAILED - {result.error_message}")
        return False
    
    # Test payload sanitization
    dangerous_payload = {
        "data": "safe_data",
        "script": "<script>alert('xss')</script>",
        "__proto__": {"polluted": True}
    }
    
    sanitized = security_manager.sanitize_payload(dangerous_payload)
    
    if "script" not in sanitized and "__proto__" not in sanitized:
        print("  ✅ Payload sanitization: PASSED")
    else:
        print("  ❌ Payload sanitization: FAILED")
        return False
    
    return True


async def test_access_control():
    """Test access control components."""
    print("🔐 Testing Access Control...")
    
    # Initialize access control manager
    access_manager = HookAccessControlManager()
    access_manager.initialize_default_users_and_teams()
    
    # Test admin access
    result = access_manager.check_hook_access("admin", "default", "read")
    
    if result.granted:
        print("  ✅ Admin access control: PASSED")
    else:
        print(f"  ❌ Admin access control: FAILED - {result.reason}")
        return False
    
    # Test non-existent user access
    result = access_manager.check_hook_access("nonexistent", "default", "read")
    
    if not result.granted:
        print("  ✅ Non-existent user access denial: PASSED")
    else:
        print("  ❌ Non-existent user access denial: FAILED")
        return False
    
    return True


async def test_audit_logging():
    """Test audit logging components."""
    print("📝 Testing Audit Logging...")
    
    # Initialize audit logger
    audit_logger = AuditLogger()
    security_audit = SecurityAuditLogger(audit_logger)
    
    # Test configuration change logging
    result = audit_logger.log_configuration_change(
        user_id="test_user",
        team_id="test_team",
        action="update",
        config_type="hook_config",
        old_config={"enabled": False},
        new_config={"enabled": True}
    )
    
    if result:
        print("  ✅ Configuration change logging: PASSED")
    else:
        print("  ❌ Configuration change logging: FAILED")
        return False
    
    # Test security event logging
    result = security_audit.log_authentication_attempt(
        user_id="test_user",
        result="success",
        method="webhook"
    )
    
    if result:
        print("  ✅ Security event logging: PASSED")
    else:
        print("  ❌ Security event logging: FAILED")
        return False
    
    return True


async def test_rate_limiting():
    """Test rate limiting components."""
    print("⏱️ Testing Rate Limiting...")
    
    # Initialize rate limiter
    rate_limiter = AdvancedRateLimiter()
    
    # Configure test limits
    limits = [
        RateLimit(LimitType.REQUESTS_PER_MINUTE, 5, 60),
        RateLimit(LimitType.CONCURRENT_REQUESTS, 2, 0)
    ]
    rate_limiter.configure_limits("test", ActionType.API_REQUEST, limits)
    
    # Test within limits
    result = await rate_limiter.check_rate_limit("test_client", "test", ActionType.API_REQUEST)
    
    if result.allowed:
        print("  ✅ Rate limiting (within limits): PASSED")
    else:
        print(f"  ❌ Rate limiting (within limits): FAILED - {result.error_message}")
        return False
    
    # Test rate limit exceeded
    for _ in range(10):  # Exceed the limit
        await rate_limiter.check_rate_limit("test_client", "test", ActionType.API_REQUEST)
    
    result = await rate_limiter.check_rate_limit("test_client", "test", ActionType.API_REQUEST)
    
    if not result.allowed:
        print("  ✅ Rate limiting (exceeded): PASSED")
    else:
        print("  ❌ Rate limiting (exceeded): FAILED")
        return False
    
    return True


async def test_integration():
    """Test integration of all security components."""
    print("🔗 Testing Security Integration...")
    
    # This would test the secure webhook handler in a real scenario
    # For now, we'll just verify all components are initialized
    
    try:
        from devsync_ai.webhooks.secure_webhook_handler import secure_webhook_handler
        
        status = await secure_webhook_handler.get_security_status()
        
        if status.get("security_manager", {}).get("initialized"):
            print("  ✅ Security integration: PASSED")
            return True
        else:
            print("  ❌ Security integration: FAILED")
            return False
            
    except Exception as e:
        print(f"  ❌ Security integration: FAILED - {str(e)}")
        return False


async def main():
    """Run all security validation tests."""
    print("🚀 Starting Hook Security System Validation")
    print("=" * 50)
    
    tests = [
        ("Webhook Security", test_webhook_security),
        ("Access Control", test_access_control),
        ("Audit Logging", test_audit_logging),
        ("Rate Limiting", test_rate_limiting),
        ("Integration", test_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
            print()
        except Exception as e:
            print(f"  ❌ {test_name}: ERROR - {str(e)}")
            print()
    
    print("=" * 50)
    print(f"🎯 Security Validation Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All security components are working correctly!")
        return True
    else:
        print("❌ Some security components need attention.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)