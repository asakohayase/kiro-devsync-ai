"""
Advanced Rate Limiting and Abuse Prevention Module

Provides sophisticated rate limiting, abuse detection, and prevention
mechanisms for the hook system.
"""

import time
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class LimitType(Enum):
    """Types of rate limits."""
    REQUESTS_PER_SECOND = "requests_per_second"
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_HOUR = "requests_per_hour"
    REQUESTS_PER_DAY = "requests_per_day"
    CONCURRENT_REQUESTS = "concurrent_requests"
    BANDWIDTH_PER_SECOND = "bandwidth_per_second"


class ActionType(Enum):
    """Types of actions that can be rate limited."""
    WEBHOOK_REQUEST = "webhook_request"
    HOOK_EXECUTION = "hook_execution"
    CONFIG_CHANGE = "config_change"
    API_REQUEST = "api_request"
    LOGIN_ATTEMPT = "login_attempt"


@dataclass
class RateLimit:
    """Rate limit configuration."""
    limit_type: LimitType
    limit_value: int
    window_seconds: int
    burst_allowance: int = 0
    description: str = ""


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    limit_exceeded: bool
    current_count: int
    limit_value: int
    reset_time: datetime
    retry_after_seconds: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AbusePattern:
    """Detected abuse pattern."""
    pattern_type: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    evidence: Dict[str, Any]
    first_detected: datetime
    last_detected: datetime
    occurrence_count: int = 1


class TokenBucket:
    """Token bucket algorithm implementation for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens from the bucket."""
        async with self.lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + (elapsed * self.refill_rate)
            )
            self.last_refill = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bucket status."""
        return {
            "capacity": self.capacity,
            "current_tokens": self.tokens,
            "refill_rate": self.refill_rate,
            "last_refill": self.last_refill
        }


class SlidingWindowCounter:
    """Sliding window counter for rate limiting."""
    
    def __init__(self, window_seconds: int, max_requests: int):
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.requests = deque()
        self.lock = asyncio.Lock()
    
    async def is_allowed(self) -> Tuple[bool, int]:
        """Check if request is allowed and return current count."""
        async with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            # Remove old requests
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()
            
            current_count = len(self.requests)
            
            if current_count < self.max_requests:
                self.requests.append(now)
                return True, current_count + 1
            
            return False, current_count
    
    def get_reset_time(self) -> datetime:
        """Get time when the oldest request will expire."""
        if not self.requests:
            return datetime.now()
        
        oldest_request = self.requests[0]
        reset_time = oldest_request + self.window_seconds
        return datetime.fromtimestamp(reset_time)


class AbuseDetector:
    """Detects abuse patterns in request behavior."""
    
    def __init__(self):
        self.request_patterns: Dict[str, List[float]] = defaultdict(list)
        self.detected_patterns: Dict[str, List[AbusePattern]] = defaultdict(list)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def record_request(self, client_id: str, action_type: ActionType, metadata: Dict[str, Any] = None):
        """Record a request for abuse pattern analysis."""
        if metadata is None:
            metadata = {}
        
        now = time.time()
        self.request_patterns[client_id].append(now)
        
        # Keep only last hour of requests
        cutoff = now - 3600
        self.request_patterns[client_id] = [
            req_time for req_time in self.request_patterns[client_id]
            if req_time > cutoff
        ]
        
        # Analyze patterns
        self._analyze_patterns(client_id, action_type, metadata)
    
    def _analyze_patterns(self, client_id: str, action_type: ActionType, metadata: Dict[str, Any]):
        """Analyze request patterns for abuse detection."""
        requests = self.request_patterns[client_id]
        if len(requests) < 10:  # Need minimum requests for pattern analysis
            return
        
        now = time.time()
        
        # Check for rapid fire requests (potential DoS)
        recent_requests = [req for req in requests if req > now - 60]  # Last minute
        if len(recent_requests) > 100:
            self._record_abuse_pattern(
                client_id,
                "rapid_fire",
                "high",
                f"Excessive requests: {len(recent_requests)} in last minute",
                {"request_count": len(recent_requests), "time_window": 60}
            )
        
        # Check for consistent timing (potential bot behavior)
        if len(requests) >= 20:
            intervals = [requests[i] - requests[i-1] for i in range(1, len(requests))]
            avg_interval = sum(intervals) / len(intervals)
            variance = sum((interval - avg_interval) ** 2 for interval in intervals) / len(intervals)
            
            if variance < 0.1 and avg_interval < 5:  # Very consistent timing
                self._record_abuse_pattern(
                    client_id,
                    "bot_behavior",
                    "medium",
                    f"Consistent request timing detected (variance: {variance:.3f})",
                    {"average_interval": avg_interval, "variance": variance}
                )
        
        # Check for unusual request patterns
        if action_type == ActionType.LOGIN_ATTEMPT:
            failed_logins = metadata.get("failed_attempts", 0)
            if failed_logins > 10:
                self._record_abuse_pattern(
                    client_id,
                    "brute_force",
                    "critical",
                    f"Multiple failed login attempts: {failed_logins}",
                    {"failed_attempts": failed_logins}
                )
    
    def _record_abuse_pattern(
        self, 
        client_id: str, 
        pattern_type: str, 
        severity: str, 
        description: str, 
        evidence: Dict[str, Any]
    ):
        """Record a detected abuse pattern."""
        now = datetime.now()
        
        # Check if we already have this pattern type for this client
        existing_patterns = [
            p for p in self.detected_patterns[client_id]
            if p.pattern_type == pattern_type and p.last_detected > now - timedelta(hours=1)
        ]
        
        if existing_patterns:
            # Update existing pattern
            pattern = existing_patterns[0]
            pattern.last_detected = now
            pattern.occurrence_count += 1
            pattern.evidence.update(evidence)
        else:
            # Create new pattern
            pattern = AbusePattern(
                pattern_type=pattern_type,
                severity=severity,
                description=description,
                evidence=evidence,
                first_detected=now,
                last_detected=now
            )
            self.detected_patterns[client_id].append(pattern)
        
        self.logger.warning(f"Abuse pattern detected for {client_id}: {description}")
    
    def get_abuse_score(self, client_id: str) -> float:
        """Calculate abuse score for a client (0.0 to 1.0)."""
        patterns = self.detected_patterns.get(client_id, [])
        if not patterns:
            return 0.0
        
        # Filter recent patterns (last 24 hours)
        now = datetime.now()
        recent_patterns = [
            p for p in patterns
            if p.last_detected > now - timedelta(hours=24)
        ]
        
        if not recent_patterns:
            return 0.0
        
        # Calculate score based on severity and frequency
        severity_weights = {
            "low": 0.1,
            "medium": 0.3,
            "high": 0.6,
            "critical": 1.0
        }
        
        total_score = 0.0
        for pattern in recent_patterns:
            base_score = severity_weights.get(pattern.severity, 0.1)
            frequency_multiplier = min(pattern.occurrence_count / 10, 2.0)
            total_score += base_score * frequency_multiplier
        
        return min(total_score, 1.0)
    
    def is_suspicious(self, client_id: str, threshold: float = 0.5) -> bool:
        """Check if client behavior is suspicious."""
        return self.get_abuse_score(client_id) >= threshold


class AdvancedRateLimiter:
    """Advanced rate limiter with multiple algorithms and abuse detection."""
    
    def __init__(self):
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.sliding_windows: Dict[str, SlidingWindowCounter] = {}
        self.concurrent_requests: Dict[str, int] = defaultdict(int)
        self.abuse_detector = AbuseDetector()
        self.blocked_clients: Dict[str, datetime] = {}
        self.rate_limits: Dict[Tuple[str, ActionType], List[RateLimit]] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def configure_limits(self, client_type: str, action_type: ActionType, limits: List[RateLimit]):
        """Configure rate limits for a client type and action."""
        self.rate_limits[(client_type, action_type)] = limits
        self.logger.info(f"Configured {len(limits)} rate limits for {client_type}:{action_type.value}")
    
    async def check_rate_limit(
        self,
        client_id: str,
        client_type: str,
        action_type: ActionType,
        request_size: int = 1,
        metadata: Dict[str, Any] = None
    ) -> RateLimitResult:
        """Check if request is within rate limits."""
        if metadata is None:
            metadata = {}
        
        try:
            # Check if client is blocked
            if client_id in self.blocked_clients:
                block_until = self.blocked_clients[client_id]
                if datetime.now() < block_until:
                    return RateLimitResult(
                        allowed=False,
                        limit_exceeded=True,
                        current_count=0,
                        limit_value=0,
                        reset_time=block_until,
                        retry_after_seconds=int((block_until - datetime.now()).total_seconds()),
                        metadata={"reason": "client_blocked", "blocked_until": block_until.isoformat()}
                    )
                else:
                    # Unblock client
                    del self.blocked_clients[client_id]
            
            # Record request for abuse detection
            self.abuse_detector.record_request(client_id, action_type, metadata)
            
            # Check abuse score
            abuse_score = self.abuse_detector.get_abuse_score(client_id)
            if abuse_score > 0.8:  # High abuse score
                self._block_client(client_id, timedelta(hours=1))
                return RateLimitResult(
                    allowed=False,
                    limit_exceeded=True,
                    current_count=0,
                    limit_value=0,
                    reset_time=datetime.now() + timedelta(hours=1),
                    retry_after_seconds=3600,
                    metadata={"reason": "abuse_detected", "abuse_score": abuse_score}
                )
            
            # Get configured limits
            limits = self.rate_limits.get((client_type, action_type), [])
            if not limits:
                # No limits configured, allow request
                return RateLimitResult(
                    allowed=True,
                    limit_exceeded=False,
                    current_count=1,
                    limit_value=float('inf'),
                    reset_time=datetime.now() + timedelta(days=1)
                )
            
            # Check each configured limit
            for limit in limits:
                result = await self._check_individual_limit(client_id, limit, request_size)
                if not result.allowed:
                    return result
            
            # All limits passed
            return RateLimitResult(
                allowed=True,
                limit_exceeded=False,
                current_count=request_size,
                limit_value=min(limit.limit_value for limit in limits),
                reset_time=datetime.now() + timedelta(seconds=min(limit.window_seconds for limit in limits)),
                metadata={"abuse_score": abuse_score}
            )
            
        except Exception as e:
            self.logger.error(f"Error checking rate limit: {e}")
            # Fail open - allow request but log error
            return RateLimitResult(
                allowed=True,
                limit_exceeded=False,
                current_count=1,
                limit_value=1,
                reset_time=datetime.now() + timedelta(minutes=1),
                metadata={"error": str(e)}
            )
    
    async def _check_individual_limit(
        self,
        client_id: str,
        limit: RateLimit,
        request_size: int
    ) -> RateLimitResult:
        """Check an individual rate limit."""
        limit_key = f"{client_id}:{limit.limit_type.value}:{limit.window_seconds}"
        
        if limit.limit_type == LimitType.CONCURRENT_REQUESTS:
            return await self._check_concurrent_limit(client_id, limit, request_size)
        elif limit.limit_type in [
            LimitType.REQUESTS_PER_SECOND,
            LimitType.REQUESTS_PER_MINUTE,
            LimitType.REQUESTS_PER_HOUR,
            LimitType.REQUESTS_PER_DAY
        ]:
            return await self._check_sliding_window_limit(limit_key, limit, request_size)
        elif limit.limit_type == LimitType.BANDWIDTH_PER_SECOND:
            return await self._check_token_bucket_limit(limit_key, limit, request_size)
        else:
            # Unknown limit type, allow request
            return RateLimitResult(
                allowed=True,
                limit_exceeded=False,
                current_count=request_size,
                limit_value=limit.limit_value,
                reset_time=datetime.now() + timedelta(seconds=limit.window_seconds)
            )
    
    async def _check_concurrent_limit(
        self,
        client_id: str,
        limit: RateLimit,
        request_size: int
    ) -> RateLimitResult:
        """Check concurrent request limit."""
        current_count = self.concurrent_requests[client_id]
        
        if current_count + request_size > limit.limit_value:
            return RateLimitResult(
                allowed=False,
                limit_exceeded=True,
                current_count=current_count,
                limit_value=limit.limit_value,
                reset_time=datetime.now() + timedelta(seconds=30),  # Estimate
                retry_after_seconds=30
            )
        
        self.concurrent_requests[client_id] += request_size
        
        return RateLimitResult(
            allowed=True,
            limit_exceeded=False,
            current_count=current_count + request_size,
            limit_value=limit.limit_value,
            reset_time=datetime.now() + timedelta(seconds=30)
        )
    
    async def _check_sliding_window_limit(
        self,
        limit_key: str,
        limit: RateLimit,
        request_size: int
    ) -> RateLimitResult:
        """Check sliding window rate limit."""
        if limit_key not in self.sliding_windows:
            self.sliding_windows[limit_key] = SlidingWindowCounter(
                limit.window_seconds,
                limit.limit_value
            )
        
        window = self.sliding_windows[limit_key]
        allowed, current_count = await window.is_allowed()
        
        return RateLimitResult(
            allowed=allowed,
            limit_exceeded=not allowed,
            current_count=current_count,
            limit_value=limit.limit_value,
            reset_time=window.get_reset_time(),
            retry_after_seconds=limit.window_seconds if not allowed else None
        )
    
    async def _check_token_bucket_limit(
        self,
        limit_key: str,
        limit: RateLimit,
        request_size: int
    ) -> RateLimitResult:
        """Check token bucket rate limit."""
        if limit_key not in self.token_buckets:
            refill_rate = limit.limit_value / limit.window_seconds
            self.token_buckets[limit_key] = TokenBucket(
                limit.limit_value + limit.burst_allowance,
                refill_rate
            )
        
        bucket = self.token_buckets[limit_key]
        allowed = await bucket.consume(request_size)
        
        return RateLimitResult(
            allowed=allowed,
            limit_exceeded=not allowed,
            current_count=request_size,
            limit_value=limit.limit_value,
            reset_time=datetime.now() + timedelta(seconds=limit.window_seconds),
            retry_after_seconds=limit.window_seconds if not allowed else None,
            metadata=bucket.get_status()
        )
    
    def _block_client(self, client_id: str, duration: timedelta):
        """Block a client for a specified duration."""
        block_until = datetime.now() + duration
        self.blocked_clients[client_id] = block_until
        self.logger.warning(f"Blocked client {client_id} until {block_until}")
    
    def release_concurrent_request(self, client_id: str, request_size: int = 1):
        """Release concurrent request count for a client."""
        if client_id in self.concurrent_requests:
            self.concurrent_requests[client_id] = max(
                0,
                self.concurrent_requests[client_id] - request_size
            )
    
    def get_client_status(self, client_id: str) -> Dict[str, Any]:
        """Get comprehensive status for a client."""
        return {
            "concurrent_requests": self.concurrent_requests.get(client_id, 0),
            "abuse_score": self.abuse_detector.get_abuse_score(client_id),
            "is_blocked": client_id in self.blocked_clients,
            "blocked_until": self.blocked_clients.get(client_id),
            "detected_patterns": len(self.abuse_detector.detected_patterns.get(client_id, []))
        }


# Global rate limiter instance
rate_limiter = AdvancedRateLimiter()

# Configure default rate limits
default_webhook_limits = [
    RateLimit(LimitType.REQUESTS_PER_MINUTE, 100, 60, burst_allowance=20),
    RateLimit(LimitType.REQUESTS_PER_HOUR, 1000, 3600),
    RateLimit(LimitType.CONCURRENT_REQUESTS, 10, 0)
]

default_api_limits = [
    RateLimit(LimitType.REQUESTS_PER_MINUTE, 60, 60, burst_allowance=10),
    RateLimit(LimitType.REQUESTS_PER_HOUR, 1000, 3600),
    RateLimit(LimitType.CONCURRENT_REQUESTS, 5, 0)
]

rate_limiter.configure_limits("webhook", ActionType.WEBHOOK_REQUEST, default_webhook_limits)
rate_limiter.configure_limits("api", ActionType.API_REQUEST, default_api_limits)