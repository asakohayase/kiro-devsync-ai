"""Template factory for creating and managing Slack message templates."""

import time
import logging
from typing import Dict, List, Any, Optional, Type, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from enum import Enum

from .base_template import SlackMessageTemplate
from .message_formatter import TemplateConfig
from .status_indicators import StatusIndicatorSystem
from .exceptions import TemplateError, DataValidationError


class TemplateType(Enum):
    """Supported template types."""
    STANDUP = "standup"
    PR_NEW = "pr_new"
    PR_READY = "pr_ready"
    PR_APPROVED = "pr_approved"
    PR_CONFLICTS = "pr_conflicts"
    PR_MERGED = "pr_merged"
    PR_CLOSED = "pr_closed"
    JIRA_STATUS = "jira_status"
    JIRA_PRIORITY = "jira_priority"
    JIRA_ASSIGNMENT = "jira_assignment"
    JIRA_COMMENT = "jira_comment"
    JIRA_BLOCKER = "jira_blocker"
    JIRA_SPRINT = "jira_sprint"
    ALERT_BUILD = "alert_build"
    ALERT_DEPLOYMENT = "alert_deployment"
    ALERT_SECURITY = "alert_security"
    ALERT_OUTAGE = "alert_outage"
    ALERT_BUG = "alert_bug"
    ALERT_BLOCKER = "alert_blocker"


@dataclass
class TemplateRegistration:
    """Template registration information."""
    template_class: Type[SlackMessageTemplate]
    template_type: TemplateType
    version: str = "1.0.0"
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    last_used: Optional[datetime] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class CacheEntry:
    """Cache entry for template instances."""
    template: SlackMessageTemplate
    created_at: datetime
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cache entry is expired."""
        return (datetime.now() - self.created_at).total_seconds() > ttl_seconds


@dataclass
class FactoryConfig:
    """Configuration for template factory."""
    cache_ttl_seconds: int = 3600  # 1 hour
    max_cache_size: int = 100
    enable_metrics: bool = True
    enable_ab_testing: bool = False
    default_template_config: Optional[TemplateConfig] = None
    performance_threshold_ms: float = 100.0  # Performance warning threshold


class MessageTemplateFactory:
    """Factory for creating and managing Slack message templates."""
    
    def __init__(self, config: Optional[FactoryConfig] = None):
        """Initialize template factory."""
        self.config = config or FactoryConfig()
        self.logger = logging.getLogger(__name__)
        
        # Template registry
        self._registry: Dict[str, TemplateRegistration] = {}
        self._type_mapping: Dict[TemplateType, str] = {}
        
        # Template instance cache
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_lock = Lock()
        
        # Performance metrics
        self._metrics: Dict[str, Dict[str, Any]] = {}
        
        # A/B testing configurations
        self._ab_tests: Dict[str, Dict[str, Any]] = {}
        
        # Status indicator system (shared across templates)
        self._status_system = StatusIndicatorSystem()
        
        self.logger.info("MessageTemplateFactory initialized")
    
    def register_template(self, 
                         name: str,
                         template_class: Type[SlackMessageTemplate],
                         template_type: TemplateType,
                         version: str = "1.0.0",
                         description: str = "") -> None:
        """Register a template class with the factory."""
        
        if not issubclass(template_class, SlackMessageTemplate):
            raise TemplateError(f"Template class {template_class.__name__} must inherit from SlackMessageTemplate")
        
        if name in self._registry:
            self.logger.warning(f"Overriding existing template registration: {name}")
        
        registration = TemplateRegistration(
            template_class=template_class,
            template_type=template_type,
            version=version,
            description=description
        )
        
        self._registry[name] = registration
        self._type_mapping[template_type] = name
        
        self.logger.info(f"Registered template: {name} ({template_type.value}) v{version}")
    
    def create_template(self, 
                       template_type: Union[str, TemplateType],
                       config: Optional[TemplateConfig] = None,
                       use_cache: bool = True) -> SlackMessageTemplate:
        """Create template instance with caching support."""
        
        # Normalize template type and get registration
        registration = None
        
        if isinstance(template_type, str):
            try:
                # Try to convert string to TemplateType enum
                template_type_enum = TemplateType(template_type)
                if template_type_enum not in self._type_mapping:
                    raise TemplateError(f"Template type {template_type_enum.value} not registered")
                template_name = self._type_mapping[template_type_enum]
                registration = self._registry[template_name]
            except ValueError:
                # Try to find by registered name
                if template_type not in self._registry:
                    raise TemplateError(f"Unknown template type: {template_type}")
                registration = self._registry[template_type]
        else:
            # Get registration by template type
            if template_type not in self._type_mapping:
                raise TemplateError(f"Template type {template_type.value} not registered")
            
            template_name = self._type_mapping[template_type]
            registration = self._registry[template_name]
        
        # Create cache key
        config_hash = self._hash_config(config) if config else "default"
        cache_key = f"{registration.template_type.value}:{config_hash}"
        
        # Try to get from cache first
        if use_cache:
            cached_template = self._get_cached_template(cache_key)
            if cached_template:
                self._update_usage_metrics(registration)
                return cached_template
        
        # Create new template instance
        start_time = time.time()
        
        try:
            # Use provided config or default
            template_config = config or self.config.default_template_config or TemplateConfig(team_id="default")
            
            # Create template instance
            template = registration.template_class(
                config=template_config,
                status_system=self._status_system
            )
            
            # Cache the instance if caching is enabled
            if use_cache:
                self._cache_template(cache_key, template)
            
            # Record performance metrics
            creation_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            self._record_performance_metric(registration, "creation_time_ms", creation_time)
            
            # Update usage metrics
            self._update_usage_metrics(registration)
            
            # Log performance warning if needed
            if creation_time > self.config.performance_threshold_ms:
                self.logger.warning(
                    f"Template creation took {creation_time:.2f}ms "
                    f"(threshold: {self.config.performance_threshold_ms}ms) "
                    f"for {registration.template_type.value}"
                )
            
            self.logger.debug(f"Created template: {registration.template_type.value} in {creation_time:.2f}ms")
            return template
            
        except Exception as e:
            self.logger.error(f"Failed to create template {registration.template_type.value}: {e}")
            raise TemplateError(f"Template creation failed: {e}") from e
    
    def get_template_by_event_type(self, 
                                  event_type: str,
                                  event_data: Dict[str, Any],
                                  config: Optional[TemplateConfig] = None) -> SlackMessageTemplate:
        """Get appropriate template based on event type and data."""
        
        # Map event types to template types
        event_mapping = {
            # Standup events
            "standup.daily": TemplateType.STANDUP,
            
            # PR events
            "pull_request.opened": TemplateType.PR_NEW,
            "pull_request.ready_for_review": TemplateType.PR_READY,
            "pull_request.approved": TemplateType.PR_APPROVED,
            "pull_request.conflicts": TemplateType.PR_CONFLICTS,
            "pull_request.merged": TemplateType.PR_MERGED,
            "pull_request.closed": TemplateType.PR_CLOSED,
            
            # JIRA events
            "jira.status_changed": TemplateType.JIRA_STATUS,
            "jira.priority_changed": TemplateType.JIRA_PRIORITY,
            "jira.assigned": TemplateType.JIRA_ASSIGNMENT,
            "jira.commented": TemplateType.JIRA_COMMENT,
            "jira.blocked": TemplateType.JIRA_BLOCKER,
            "jira.sprint_changed": TemplateType.JIRA_SPRINT,
            
            # Alert events
            "alert.build_failure": TemplateType.ALERT_BUILD,
            "alert.deployment_issue": TemplateType.ALERT_DEPLOYMENT,
            "alert.security_vulnerability": TemplateType.ALERT_SECURITY,
            "alert.service_outage": TemplateType.ALERT_OUTAGE,
            "alert.critical_bug": TemplateType.ALERT_BUG,
            "alert.team_blocker": TemplateType.ALERT_BLOCKER,
        }
        
        # Get template type from event
        template_type = event_mapping.get(event_type)
        if not template_type:
            raise TemplateError(f"No template mapping found for event type: {event_type}")
        
        # Handle A/B testing if enabled
        if self.config.enable_ab_testing:
            template_type = self._select_ab_test_variant(template_type, event_data)
        
        return self.create_template(template_type, config)
    
    def get_registered_templates(self) -> Dict[str, TemplateRegistration]:
        """Get all registered templates."""
        return self._registry.copy()
    
    def get_template_metrics(self, template_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics for templates."""
        if not self.config.enable_metrics:
            return {}
        
        if template_name:
            return self._metrics.get(template_name, {})
        
        return self._metrics.copy()
    
    def clear_cache(self, template_type: Optional[TemplateType] = None) -> int:
        """Clear template cache. Returns number of entries cleared."""
        with self._cache_lock:
            if template_type:
                # Clear specific template type
                keys_to_remove = [
                    key for key in self._cache.keys()
                    if key.startswith(f"{template_type.value}:")
                ]
                for key in keys_to_remove:
                    del self._cache[key]
                cleared_count = len(keys_to_remove)
            else:
                # Clear all cache
                cleared_count = len(self._cache)
                self._cache.clear()
        
        self.logger.info(f"Cleared {cleared_count} template cache entries")
        return cleared_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            total_entries = len(self._cache)
            expired_entries = sum(
                1 for entry in self._cache.values()
                if entry.is_expired(self.config.cache_ttl_seconds)
            )
            
            total_access_count = sum(entry.access_count for entry in self._cache.values())
            
            return {
                "total_entries": total_entries,
                "expired_entries": expired_entries,
                "active_entries": total_entries - expired_entries,
                "total_access_count": total_access_count,
                "cache_hit_rate": self._calculate_cache_hit_rate(),
                "max_cache_size": self.config.max_cache_size,
                "cache_utilization": total_entries / self.config.max_cache_size if self.config.max_cache_size > 0 else 0
            }
    
    def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries. Returns number of entries removed."""
        with self._cache_lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired(self.config.cache_ttl_seconds)
            ]
            
            for key in expired_keys:
                del self._cache[key]
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def _get_cached_template(self, cache_key: str) -> Optional[SlackMessageTemplate]:
        """Get template from cache if available and not expired."""
        with self._cache_lock:
            entry = self._cache.get(cache_key)
            if not entry:
                return None
            
            if entry.is_expired(self.config.cache_ttl_seconds):
                del self._cache[cache_key]
                return None
            
            # Update access statistics
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            
            return entry.template
    
    def _cache_template(self, cache_key: str, template: SlackMessageTemplate) -> None:
        """Cache template instance."""
        with self._cache_lock:
            # Check cache size limit
            if len(self._cache) >= self.config.max_cache_size:
                self._evict_oldest_cache_entry()
            
            # Add to cache
            self._cache[cache_key] = CacheEntry(template=template, created_at=datetime.now())
    
    def _evict_oldest_cache_entry(self) -> None:
        """Evict the oldest cache entry to make room."""
        if not self._cache:
            return
        
        # Find oldest entry by creation time
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]
        
        self.logger.debug(f"Evicted oldest cache entry: {oldest_key}")
    
    def _hash_config(self, config: TemplateConfig) -> str:
        """Create hash of template configuration for caching."""
        import hashlib
        
        config_str = f"{config.team_id}:{config.interactive_elements}:{config.accessibility_mode}"
        return hashlib.md5(config_str.encode()).hexdigest()[:8]
    
    def _update_usage_metrics(self, registration: TemplateRegistration) -> None:
        """Update usage metrics for template."""
        registration.usage_count += 1
        registration.last_used = datetime.now()
    
    def _record_performance_metric(self, registration: TemplateRegistration, 
                                 metric_name: str, value: float) -> None:
        """Record performance metric for template."""
        if not self.config.enable_metrics:
            return
        
        template_name = registration.template_type.value
        
        if template_name not in self._metrics:
            self._metrics[template_name] = {
                "creation_times": [],
                "usage_count": 0,
                "average_creation_time": 0.0,
                "min_creation_time": float('inf'),
                "max_creation_time": 0.0
            }
        
        metrics = self._metrics[template_name]
        
        if metric_name == "creation_time_ms":
            metrics["creation_times"].append(value)
            metrics["usage_count"] += 1
            
            # Keep only last 100 measurements for rolling average
            if len(metrics["creation_times"]) > 100:
                metrics["creation_times"] = metrics["creation_times"][-100:]
            
            # Update statistics
            metrics["average_creation_time"] = sum(metrics["creation_times"]) / len(metrics["creation_times"])
            metrics["min_creation_time"] = min(metrics["min_creation_time"], value)
            metrics["max_creation_time"] = max(metrics["max_creation_time"], value)
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        # This is a simplified calculation - in production you'd want more sophisticated tracking
        total_accesses = sum(entry.access_count for entry in self._cache.values())
        if total_accesses == 0:
            return 0.0
        
        # Estimate hit rate based on access patterns
        cache_entries = len(self._cache)
        if cache_entries == 0:
            return 0.0
        
        # Simple heuristic: higher access counts indicate better cache utilization
        average_access = total_accesses / cache_entries
        return min(average_access / 10.0, 1.0)  # Cap at 100%
    
    def _select_ab_test_variant(self, template_type: TemplateType, 
                               event_data: Dict[str, Any]) -> TemplateType:
        """Select A/B test variant if configured."""
        # This is a placeholder for A/B testing logic
        # In production, you'd implement proper A/B testing with user segmentation
        return template_type


# Global factory instance
default_template_factory = MessageTemplateFactory()