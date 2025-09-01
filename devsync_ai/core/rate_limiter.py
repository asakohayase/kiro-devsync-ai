"""
Intelligent rate limiting with throttling and priority queuing for changelog generation.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict, deque

from ..analytics.performance_monitor import performance_monitor, MetricType


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    ADAPTIVE = "adaptive"


class RequestPriority(Enum):
    """Request priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""
    name: str
    requests_per_second: float
    burst_capacity: int
    window_size_seconds: int = 60
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    priority_multiplier: Dict[RequestPriority, float] = field(default_factory=lambda: {
        RequestPriority.LOW: 0.5,
        RequestPriority.NORMAL: 1.0,
        RequestPriority.HIGH: 1.5,
        RequestPriority.CRITICAL: 2.0
    })


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float
    last_refill: float
    refill_rate: float  # tokens per second


@dataclass
class RequestContext:
    """Context information for a rate-limited request."""
    request_id: str
    client_id: str
    endpoint: str
    priority: RequestPriority
    team_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    retry_after: Optional[float] = None
    remaining_quota: Optional[int] = None
    reset_time: Optional[float] = None
    reason: Optional[str] = None


class IntelligentRateLimiter:
    """
    Intelligent rate limiter with adaptive throttling and priority queuing.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting buckets per client/endpoint
        self.buckets: Dict[str, RateLimitBucket] = {}
        
        # Sliding window counters
        self.sliding_windows: Dict[str, deque] = defaultdict(lambda: deque())
        
        # Priority queues for throttled requests
        self.priority_queues: Dict[RequestPriority, deque] = {
            priority: deque() for priority in RequestPriority
        }
        
        # Rate limiting rules
        self.rules: Dict[str, RateLimitRule] = {}
        
        # Adaptive rate limiting state
        self.adaptive_state: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Request statistics
        self.request_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_requests": 0,
            "allowed_requests": 0,
            "throttled_requests": 0,
            "avg_response_time": 0.0,
            "error_rate": 0.0
        })
        
        # Background task for processing throttled requests
        self._processor_task: Optional[asyncio.Task] = None
        
        # Default rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default rate limiting rules."""
        # GitHub API rate limiting
        self.add_rule(RateLimitRule(
            name="github_api",
            requests_per_second=1.0,  # Conservative for GitHub API
            burst_capacity=10,
            window_size_seconds=3600,  # GitHub has hourly limits
            strategy=RateLimitStrategy.TOKEN_BUCKET
        ))
        
        # JIRA API rate limiting
        self.add_rule(RateLimitRule(
            name="jira_api",
            requests_per_second=2.0,
            burst_capacity=20,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        ))
        
        # Slack API rate limiting
        self.add_rule(RateLimitRule(
            name="slack_api",
            requests_per_second=1.0,
            burst_capacity=5,
            window_size_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        ))
        
        # Changelog generation rate limiting
        self.add_rule(RateLimitRule(
            name="changelog_generation",
            requests_per_second=0.1,  # 1 per 10 seconds
            burst_capacity=3,
            window_size_seconds=300,  # 5 minutes
            strategy=RateLimitStrategy.ADAPTIVE
        ))
        
        # Database query rate limiting
        self.add_rule(RateLimitRule(
            name="database_query",
            requests_per_second=10.0,
            burst_capacity=50,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        ))
    
    async def start(self):
        """Start the rate limiter and background processing."""
        self._processor_task = asyncio.create_task(self._process_throttled_requests())
        self.logger.info("Rate limiter started")
    
    async def stop(self):
        """Stop the rate limiter."""
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Rate limiter stopped")
    
    def add_rule(self, rule: RateLimitRule):
        """Add a rate limiting rule."""
        self.rules[rule.name] = rule
        self.logger.info(f"Added rate limiting rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove a rate limiting rule."""
        if rule_name in self.rules:
            del self.rules[rule_name]
            self.logger.info(f"Removed rate limiting rule: {rule_name}")
    
    async def check_rate_limit(
        self,
        client_id: str,
        endpoint: str,
        priority: RequestPriority = RequestPriority.NORMAL,
        team_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RateLimitResult:
        """
        Check if a request should be rate limited.
        """
        request_ctx = RequestContext(
            request_id=f"{client_id}_{endpoint}_{int(time.time() * 1000)}",
            client_id=client_id,
            endpoint=endpoint,
            priority=priority,
            team_id=team_id,
            metadata=metadata or {}
        )
        
        # Find applicable rule
        rule = self._find_applicable_rule(endpoint)
        if not rule:
            return RateLimitResult(allowed=True)
        
        # Apply rate limiting based on strategy
        if rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
            result = await self._check_token_bucket(request_ctx, rule)
        elif rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
            result = await self._check_sliding_window(request_ctx, rule)
        elif rule.strategy == RateLimitStrategy.FIXED_WINDOW:
            result = await self._check_fixed_window(request_ctx, rule)
        elif rule.strategy == RateLimitStrategy.ADAPTIVE:
            result = await self._check_adaptive(request_ctx, rule)
        else:
            result = RateLimitResult(allowed=True)
        
        # Update statistics
        await self._update_request_stats(request_ctx, result)
        
        # If throttled, add to priority queue
        if not result.allowed:
            self.priority_queues[priority].append(request_ctx)
            self.logger.debug(f"Request {request_ctx.request_id} throttled, added to {priority.name} queue")
        
        return result
    
    def _find_applicable_rule(self, endpoint: str) -> Optional[RateLimitRule]:
        """Find the most specific rule that applies to the endpoint."""
        # Direct match first
        if endpoint in self.rules:
            return self.rules[endpoint]
        
        # Pattern matching (simple prefix matching)
        for rule_name, rule in self.rules.items():
            if endpoint.startswith(rule_name):
                return rule
        
        # Default rule if no specific match
        return self.rules.get("default")
    
    async def _check_token_bucket(
        self,
        request_ctx: RequestContext,
        rule: RateLimitRule
    ) -> RateLimitResult:
        """Check rate limit using token bucket algorithm."""
        bucket_key = f"{rule.name}_{request_ctx.client_id}"
        current_time = time.time()
        
        # Get or create bucket
        if bucket_key not in self.buckets:
            self.buckets[bucket_key] = RateLimitBucket(
                capacity=rule.burst_capacity,
                tokens=rule.burst_capacity,
                last_refill=current_time,
                refill_rate=rule.requests_per_second
            )
        
        bucket = self.buckets[bucket_key]
        
        # Refill tokens based on time elapsed
        time_elapsed = current_time - bucket.last_refill
        tokens_to_add = time_elapsed * bucket.refill_rate
        bucket.tokens = min(bucket.capacity, bucket.tokens + tokens_to_add)
        bucket.last_refill = current_time
        
        # Apply priority multiplier
        priority_multiplier = rule.priority_multiplier.get(request_ctx.priority, 1.0)
        tokens_needed = 1.0 / priority_multiplier
        
        # Check if request can be allowed
        if bucket.tokens >= tokens_needed:
            bucket.tokens -= tokens_needed
            return RateLimitResult(
                allowed=True,
                remaining_quota=int(bucket.tokens),
                reset_time=current_time + (bucket.capacity - bucket.tokens) / bucket.refill_rate
            )
        else:
            # Calculate retry after time
            tokens_needed_for_request = tokens_needed - bucket.tokens
            retry_after = tokens_needed_for_request / bucket.refill_rate
            
            return RateLimitResult(
                allowed=False,
                retry_after=retry_after,
                remaining_quota=0,
                reset_time=current_time + retry_after,
                reason="Token bucket exhausted"
            )
    
    async def _check_sliding_window(
        self,
        request_ctx: RequestContext,
        rule: RateLimitRule
    ) -> RateLimitResult:
        """Check rate limit using sliding window algorithm."""
        window_key = f"{rule.name}_{request_ctx.client_id}"
        current_time = time.time()
        window_start = current_time - rule.window_size_seconds
        
        # Get window for this client/endpoint
        window = self.sliding_windows[window_key]
        
        # Remove old entries
        while window and window[0] < window_start:
            window.popleft()
        
        # Apply priority multiplier to determine effective limit
        priority_multiplier = rule.priority_multiplier.get(request_ctx.priority, 1.0)
        effective_limit = int(rule.requests_per_second * rule.window_size_seconds * priority_multiplier)
        
        # Check if within limit
        if len(window) < effective_limit:
            window.append(current_time)
            return RateLimitResult(
                allowed=True,
                remaining_quota=effective_limit - len(window),
                reset_time=window[0] + rule.window_size_seconds if window else current_time
            )
        else:
            # Calculate retry after time (when oldest request will expire)
            retry_after = window[0] + rule.window_size_seconds - current_time
            
            return RateLimitResult(
                allowed=False,
                retry_after=max(0, retry_after),
                remaining_quota=0,
                reset_time=window[0] + rule.window_size_seconds,
                reason="Sliding window limit exceeded"
            )
    
    async def _check_fixed_window(
        self,
        request_ctx: RequestContext,
        rule: RateLimitRule
    ) -> RateLimitResult:
        """Check rate limit using fixed window algorithm."""
        current_time = time.time()
        window_start = int(current_time // rule.window_size_seconds) * rule.window_size_seconds
        window_key = f"{rule.name}_{request_ctx.client_id}_{window_start}"
        
        # Get current window count
        if window_key not in self.request_stats:
            self.request_stats[window_key] = {"count": 0}
        
        current_count = self.request_stats[window_key]["count"]
        
        # Apply priority multiplier
        priority_multiplier = rule.priority_multiplier.get(request_ctx.priority, 1.0)
        effective_limit = int(rule.requests_per_second * rule.window_size_seconds * priority_multiplier)
        
        if current_count < effective_limit:
            self.request_stats[window_key]["count"] += 1
            return RateLimitResult(
                allowed=True,
                remaining_quota=effective_limit - current_count - 1,
                reset_time=window_start + rule.window_size_seconds
            )
        else:
            retry_after = window_start + rule.window_size_seconds - current_time
            return RateLimitResult(
                allowed=False,
                retry_after=retry_after,
                remaining_quota=0,
                reset_time=window_start + rule.window_size_seconds,
                reason="Fixed window limit exceeded"
            )
    
    async def _check_adaptive(
        self,
        request_ctx: RequestContext,
        rule: RateLimitRule
    ) -> RateLimitResult:
        """Check rate limit using adaptive algorithm based on system performance."""
        adaptive_key = f"{rule.name}_{request_ctx.client_id}"
        
        # Get current system performance metrics
        system_health = await performance_monitor.get_system_health()
        
        # Adjust rate limit based on system health
        base_rate = rule.requests_per_second
        
        if system_health.status == "critical":
            adjusted_rate = base_rate * 0.2  # Reduce to 20% of normal rate
        elif system_health.status == "degraded":
            adjusted_rate = base_rate * 0.5  # Reduce to 50% of normal rate
        else:
            # Healthy system - potentially increase rate for high priority requests
            priority_boost = {
                RequestPriority.LOW: 0.8,
                RequestPriority.NORMAL: 1.0,
                RequestPriority.HIGH: 1.2,
                RequestPriority.CRITICAL: 1.5
            }.get(request_ctx.priority, 1.0)
            
            adjusted_rate = base_rate * priority_boost
        
        # Store adaptive state
        if adaptive_key not in self.adaptive_state:
            self.adaptive_state[adaptive_key] = {
                "last_request": 0,
                "current_rate": adjusted_rate
            }
        
        state = self.adaptive_state[adaptive_key]
        current_time = time.time()
        
        # Calculate minimum interval between requests
        min_interval = 1.0 / adjusted_rate if adjusted_rate > 0 else float('inf')
        time_since_last = current_time - state["last_request"]
        
        if time_since_last >= min_interval:
            state["last_request"] = current_time
            state["current_rate"] = adjusted_rate
            
            return RateLimitResult(
                allowed=True,
                remaining_quota=None,  # Adaptive doesn't have fixed quota
                reset_time=None
            )
        else:
            retry_after = min_interval - time_since_last
            return RateLimitResult(
                allowed=False,
                retry_after=retry_after,
                remaining_quota=None,
                reset_time=current_time + retry_after,
                reason=f"Adaptive rate limit (system: {system_health.status})"
            )
    
    async def _update_request_stats(self, request_ctx: RequestContext, result: RateLimitResult):
        """Update request statistics for monitoring."""
        stats_key = f"{request_ctx.endpoint}_{request_ctx.client_id}"
        stats = self.request_stats[stats_key]
        
        stats["total_requests"] += 1
        
        if result.allowed:
            stats["allowed_requests"] += 1
        else:
            stats["throttled_requests"] += 1
        
        # Record metrics
        await performance_monitor.record_metric(
            MetricType.THROUGHPUT,
            1.0,
            team_id=request_ctx.team_id,
            metadata={
                "endpoint": request_ctx.endpoint,
                "client_id": request_ctx.client_id,
                "priority": request_ctx.priority.name,
                "allowed": result.allowed
            }
        )
    
    async def _process_throttled_requests(self):
        """Background task to process throttled requests when capacity becomes available."""
        try:
            while True:
                # Process requests by priority (highest first)
                for priority in sorted(RequestPriority, key=lambda p: p.value, reverse=True):
                    queue = self.priority_queues[priority]
                    
                    # Process up to 10 requests per iteration
                    processed = 0
                    while queue and processed < 10:
                        request_ctx = queue.popleft()
                        
                        # Re-check rate limit
                        result = await self.check_rate_limit(
                            request_ctx.client_id,
                            request_ctx.endpoint,
                            request_ctx.priority,
                            request_ctx.team_id,
                            request_ctx.metadata
                        )
                        
                        if result.allowed:
                            # Request can now proceed - notify waiting coroutine
                            self.logger.debug(f"Throttled request {request_ctx.request_id} now allowed")
                        else:
                            # Still throttled - put back in queue
                            queue.appendleft(request_ctx)
                            break
                        
                        processed += 1
                
                await asyncio.sleep(1)  # Check every second
                
        except asyncio.CancelledError:
            self.logger.info("Throttled request processor cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in throttled request processor: {e}")
            await asyncio.sleep(5)
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get comprehensive rate limiting statistics."""
        total_requests = sum(stats["total_requests"] for stats in self.request_stats.values())
        total_allowed = sum(stats["allowed_requests"] for stats in self.request_stats.values())
        total_throttled = sum(stats["throttled_requests"] for stats in self.request_stats.values())
        
        throttle_rate = (total_throttled / total_requests * 100) if total_requests > 0 else 0
        
        # Queue statistics
        queue_stats = {}
        for priority, queue in self.priority_queues.items():
            queue_stats[priority.name] = len(queue)
        
        # Bucket statistics
        bucket_stats = {}
        for bucket_key, bucket in self.buckets.items():
            bucket_stats[bucket_key] = {
                "tokens": round(bucket.tokens, 2),
                "capacity": bucket.capacity,
                "utilization_percent": round((1 - bucket.tokens / bucket.capacity) * 100, 2)
            }
        
        return {
            "overall": {
                "total_requests": total_requests,
                "allowed_requests": total_allowed,
                "throttled_requests": total_throttled,
                "throttle_rate_percent": round(throttle_rate, 2)
            },
            "queues": queue_stats,
            "buckets": bucket_stats,
            "rules": {
                name: {
                    "requests_per_second": rule.requests_per_second,
                    "burst_capacity": rule.burst_capacity,
                    "strategy": rule.strategy.value
                }
                for name, rule in self.rules.items()
            },
            "adaptive_state": {
                key: {
                    "current_rate": round(state.get("current_rate", 0), 2),
                    "last_request_ago": round(time.time() - state.get("last_request", 0), 2)
                }
                for key, state in self.adaptive_state.items()
            }
        }
    
    async def wait_for_capacity(
        self,
        client_id: str,
        endpoint: str,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Wait for rate limit capacity to become available.
        Returns True if capacity is available, False if timeout occurred.
        """
        start_time = time.time()
        
        while True:
            result = await self.check_rate_limit(client_id, endpoint, priority)
            
            if result.allowed:
                return True
            
            if timeout and (time.time() - start_time) >= timeout:
                return False
            
            # Wait for the suggested retry time or a minimum of 0.1 seconds
            wait_time = max(0.1, result.retry_after or 1.0)
            await asyncio.sleep(min(wait_time, 5.0))  # Cap wait time at 5 seconds


# Global rate limiter instance
rate_limiter = IntelligentRateLimiter()