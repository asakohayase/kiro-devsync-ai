"""
MessageTemplateFactory for DevSync AI notifications.
Provides unified template creation, caching, versioning, and A/B testing.
"""

import json
import hashlib
import time
import threading
from typing import Dict, Any, Optional, Type, Callable, List, Union, Protocol
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Import base template system
from ..core.base_template import (
    SlackMessageTemplate, MessageMetadata, TeamBranding,
    ChannelConfig, UserPreferences, AccessibilityOptions,
    MessagePriority
)

# Import all template classes
from .slack_templates import DailyStandupTemplate, create_standup_message
from .pr_status_templates import (
    NewPRTemplate, PRReadyForReviewTemplate, PRApprovedTemplate,
    PRConflictsTemplate, PRMergedTemplate, PRClosedTemplate,
    create_pr_message_by_action
)
from .jira_templates import (
    JIRAStatusChangeTemplate, JIRAPriorityChangeTemplate,
    JIRAAssignmentChangeTemplate, JIRACommentTemplate,
    JIRABlockerTemplate, JIRASprintChangeTemplate,
    create_jira_message
)
from .alert_templates import (
    BuildFailureTemplate, DeploymentIssueTemplate,
    SecurityVulnerabilityTemplate, ServiceOutageTemplate,
    create_alert_message
)

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """Supported template types."""
    STANDUP = "standup"
    PR_UPDATE = "pr_update"
    JIRA_UPDATE = "jira_update"
    ALERT = "alert"


class TemplateVersion(Enum):
    """Template version types."""
    STABLE = "stable"
    BETA = "beta"
    EXPERIMENTAL = "experimental"


@dataclass
class TemplateConfig:
    """Configuration for a template."""
    name: str
    template_class: Optional[Type] = None
    factory_function: Optional[Callable] = None
    version: TemplateVersion = TemplateVersion.STABLE
    enabled: bool = True
    weight: int = 100  # For A/B testing (0-100)
    environment: Optional[str] = None
    feature_flags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # New fields for enhanced functionality
    priority: MessagePriority = MessagePriority.NORMAL
    team_branding: Optional[TeamBranding] = None
    accessibility_options: Optional[AccessibilityOptions] = None
    cache_ttl: int = 3600  # Cache TTL in seconds
    performance_threshold: float = 1.0  # Performance threshold in seconds


@dataclass
class TemplateMetrics:
    """Metrics for template performance."""
    render_count: int = 0
    total_render_time: float = 0.0
    error_count: int = 0
    warning_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    last_used: Optional[float] = None
    first_used: Optional[float] = None
    peak_render_time: float = 0.0
    min_render_time: float = float('inf')
    
    @property
    def average_render_time(self) -> float:
        """Calculate average render time."""
        return self.total_render_time / self.render_count if self.render_count > 0 else 0.0
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / total_requests if total_requests > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        return self.error_count / self.render_count if self.render_count > 0 else 0.0
    
    def update_render_time(self, render_time: float) -> None:
        """Update render time metrics."""
        self.total_render_time += render_time
        self.peak_render_time = max(self.peak_render_time, render_time)
        self.min_render_time = min(self.min_render_time, render_time)
        if self.first_used is None:
            self.first_used = time.time()
        self.last_used = time.time()


class TemplateInterface(Protocol):
    """Protocol for all templates."""
    
    def render(self) -> Dict[str, Any]:
        """Render the template to Slack message format."""
        ...
    
    def get_fallback_text(self) -> str:
        """Get fallback text for the template."""
        ...
    
    def get_analytics_data(self) -> Dict[str, Any]:
        """Get analytics data for the template."""
        ...
    
    def has_errors(self) -> bool:
        """Check if template has errors."""
        ...
    
    def get_errors(self) -> List[str]:
        """Get template errors."""
        ...


class TemplateWrapper:
    """Wrapper for existing template classes to provide unified interface."""
    
    def __init__(self, template_instance: Any, factory_function: Optional[Callable] = None):
        self.template_instance = template_instance
        self.factory_function = factory_function
        self._cached_result: Optional[Dict[str, Any]] = None
    
    def render(self) -> Dict[str, Any]:
        """Render the template."""
        if self._cached_result:
            return self._cached_result
        
        if isinstance(self.template_instance, SlackMessageTemplate):
            # New base template system
            result = self.template_instance.get_message()
        elif hasattr(self.template_instance, 'get_message'):
            # Legacy template system
            result = self.template_instance.get_message()
        elif self.factory_function:
            # Factory function approach
            result = self.factory_function(getattr(self.template_instance, 'data', {}))
        else:
            raise NotImplementedError("Template must implement get_message() or have factory_function")
        
        self._cached_result = result
        return result
    
    def get_fallback_text(self) -> str:
        """Get fallback text."""
        if isinstance(self.template_instance, SlackMessageTemplate):
            return self.template_instance.fallback_text
        elif hasattr(self.template_instance, 'fallback_text'):
            return self.template_instance.fallback_text
        else:
            message = self.render()
            return message.get('text', 'DevSync AI Notification')
    
    def get_analytics_data(self) -> Dict[str, Any]:
        """Get analytics data."""
        if isinstance(self.template_instance, SlackMessageTemplate):
            return self.template_instance.get_analytics_data()
        else:
            # Basic analytics for legacy templates
            return {
                "template_type": type(self.template_instance).__name__,
                "created_at": datetime.now().isoformat(),
                "has_errors": self.has_errors(),
                "block_count": len(self.render().get('blocks', []))
            }
    
    def has_errors(self) -> bool:
        """Check if template has errors."""
        if isinstance(self.template_instance, SlackMessageTemplate):
            return self.template_instance.has_errors()
        else:
            try:
                self.render()
                return False
            except Exception:
                return True
    
    def get_errors(self) -> List[str]:
        """Get template errors."""
        if isinstance(self.template_instance, SlackMessageTemplate):
            return self.template_instance.get_errors()
        else:
            try:
                self.render()
                return []
            except Exception as e:
                return [str(e)]


class TemplateCache:
    """Advanced template caching system with LRU eviction and statistics."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_order: List[str] = []  # For LRU eviction
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired': 0
        }
    
    def _generate_key(self, template_type: str, data: Dict[str, Any], 
                     user_id: Optional[str] = None) -> str:
        """Generate cache key from template type, data, and user context."""
        # Include user_id for personalized caching
        cache_data = {
            'template_type': template_type,
            'data': data,
            'user_id': user_id
        }
        data_str = json.dumps(cache_data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]  # Shorter key
    
    def get(self, template_type: str, data: Dict[str, Any], 
           user_id: Optional[str] = None, ttl: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get cached template result."""
        key = self._generate_key(template_type, data, user_id)
        
        with self._lock:
            if key in self._cache:
                cached_item = self._cache[key]
                cache_ttl = ttl or cached_item.get('ttl', self.default_ttl)
                
                if time.time() - cached_item['timestamp'] < cache_ttl:
                    # Move to end for LRU
                    if key in self._access_order:
                        self._access_order.remove(key)
                    self._access_order.append(key)
                    
                    self._stats['hits'] += 1
                    logger.debug(f"Cache hit for template {template_type}")
                    return cached_item['result']
                else:
                    # Expired
                    del self._cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)
                    self._stats['expired'] += 1
            
            self._stats['misses'] += 1
            return None
    
    def set(self, template_type: str, data: Dict[str, Any], result: Dict[str, Any],
           user_id: Optional[str] = None, ttl: Optional[int] = None) -> None:
        """Cache template result."""
        key = self._generate_key(template_type, data, user_id)
        
        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            # Remove from access order if already exists
            if key in self._access_order:
                self._access_order.remove(key)
            
            # Add to cache and access order
            self._cache[key] = {
                'result': result,
                'timestamp': time.time(),
                'ttl': ttl or self.default_ttl,
                'template_type': template_type
            }
            self._access_order.append(key)
            
            logger.debug(f"Cached template result for {template_type}")
    
    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if self._access_order:
            lru_key = self._access_order.pop(0)
            if lru_key in self._cache:
                del self._cache[lru_key]
                self._stats['evictions'] += 1
    
    def clear(self) -> None:
        """Clear all cached items."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            logger.info("Template cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0.0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': hit_rate,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'expired': self._stats['expired']
            }
    
    def cleanup_expired(self) -> int:
        """Clean up expired entries and return count of removed items."""
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, cached_item in self._cache.items():
                ttl = cached_item.get('ttl', self.default_ttl)
                if current_time - cached_item['timestamp'] >= ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._stats['expired'] += 1
        
        return len(expired_keys)


class ABTestManager:
    """A/B testing manager for templates."""
    
    def __init__(self):
        self._user_assignments: Dict[str, str] = {}
    
    def get_template_variant(self, user_id: str, template_configs: List[TemplateConfig]) -> TemplateConfig:
        """Get template variant for A/B testing."""
        if not template_configs:
            raise ValueError("No template configurations provided")
        
        # If only one config, return it
        if len(template_configs) == 1:
            return template_configs[0]
        
        # Check if user already has assignment
        cache_key = f"{user_id}:{':'.join(c.name for c in template_configs)}"
        if cache_key in self._user_assignments:
            variant_name = self._user_assignments[cache_key]
            for config in template_configs:
                if config.name == variant_name:
                    return config
        
        # Assign based on weights
        total_weight = sum(c.weight for c in template_configs if c.enabled)
        if total_weight == 0:
            return template_configs[0]
        
        # Use user_id hash for consistent assignment
        user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        selection_point = (user_hash % total_weight)
        
        current_weight = 0
        for config in template_configs:
            if not config.enabled:
                continue
            current_weight += config.weight
            if selection_point < current_weight:
                self._user_assignments[cache_key] = config.name
                logger.debug(f"Assigned user {user_id} to template variant {config.name}")
                return config
        
        # Fallback to first enabled config
        for config in template_configs:
            if config.enabled:
                return config
        
        return template_configs[0]


class MessageTemplateFactory:
    """Advanced factory for creating message templates with caching, A/B testing, and monitoring."""
    
    def __init__(self, config_path: Optional[str] = None, cache_config: Optional[Dict[str, Any]] = None):
        self._templates: Dict[str, List[TemplateConfig]] = {}
        self._metrics: Dict[str, TemplateMetrics] = {}
        self._cache = TemplateCache(**(cache_config or {}))
        self._ab_test_manager = ABTestManager()
        self._feature_flags: Dict[str, bool] = {}
        self._environment = "production"
        self._lock = threading.RLock()
        
        # Performance monitoring
        self._performance_alerts: List[Dict[str, Any]] = []
        self._slow_template_threshold = 1.0  # seconds
        
        # Global configuration
        self._global_team_branding: Optional[TeamBranding] = None
        self._global_accessibility: Optional[AccessibilityOptions] = None
        
        # Register default templates
        self._register_default_templates()
        
        # Load configuration if provided
        if config_path:
            self.load_config(config_path)
        
        # Start background cleanup task
        self._start_cleanup_task()
    
    def _register_default_templates(self) -> None:
        """Register all default templates."""
        # Standup templates
        self.register_template(
            "standup",
            TemplateConfig(
                name="default_standup",
                template_class=DailyStandupTemplate,
                factory_function=create_standup_message
            )
        )
        
        # PR templates
        pr_templates = [
            ("opened", NewPRTemplate),
            ("ready_for_review", PRReadyForReviewTemplate),
            ("approved", PRApprovedTemplate),
            ("has_conflicts", PRConflictsTemplate),
            ("merged", PRMergedTemplate),
            ("closed", PRClosedTemplate)
        ]
        
        for action, template_class in pr_templates:
            self.register_template(
                f"pr_update_{action}",
                TemplateConfig(
                    name=f"default_pr_{action}",
                    template_class=template_class,
                    factory_function=create_pr_message_by_action
                )
            )
        
        # Generic PR template
        self.register_template(
            "pr_update",
            TemplateConfig(
                name="default_pr",
                template_class=None,  # Will use factory function
                factory_function=create_pr_message_by_action
            )
        )
        
        # JIRA templates
        jira_templates = [
            ("status_change", JIRAStatusChangeTemplate),
            ("priority_change", JIRAPriorityChangeTemplate),
            ("assignment_change", JIRAAssignmentChangeTemplate),
            ("comment_added", JIRACommentTemplate),
            ("blocker_identified", JIRABlockerTemplate),
            ("blocker_resolved", JIRABlockerTemplate),
            ("sprint_change", JIRASprintChangeTemplate)
        ]
        
        for change_type, template_class in jira_templates:
            self.register_template(
                f"jira_update_{change_type}",
                TemplateConfig(
                    name=f"default_jira_{change_type}",
                    template_class=template_class,
                    factory_function=create_jira_message
                )
            )
        
        # Generic JIRA template
        self.register_template(
            "jira_update",
            TemplateConfig(
                name="default_jira",
                template_class=None,
                factory_function=create_jira_message
            )
        )
        
        # Alert templates
        alert_templates = [
            ("build_failure", BuildFailureTemplate),
            ("deployment_issue", DeploymentIssueTemplate),
            ("security_vulnerability", SecurityVulnerabilityTemplate),
            ("service_outage", ServiceOutageTemplate)
        ]
        
        for alert_type, template_class in alert_templates:
            self.register_template(
                f"alert_{alert_type}",
                TemplateConfig(
                    name=f"default_alert_{alert_type}",
                    template_class=template_class,
                    factory_function=create_alert_message
                )
            )
        
        # Generic alert template
        self.register_template(
            "alert",
            TemplateConfig(
                name="default_alert",
                template_class=None,
                factory_function=create_alert_message
            )
        )
    
    def register_template(self, template_type: str, config: TemplateConfig) -> None:
        """Register a new template configuration."""
        if template_type not in self._templates:
            self._templates[template_type] = []
        
        # Check if template with same name already exists
        existing_configs = self._templates[template_type]
        for i, existing_config in enumerate(existing_configs):
            if existing_config.name == config.name:
                existing_configs[i] = config
                logger.info(f"Updated template {config.name} for type {template_type}")
                return
        
        # Add new template
        self._templates[template_type].append(config)
        logger.info(f"Registered template {config.name} for type {template_type}")
    
    def unregister_template(self, template_type: str, template_name: str) -> bool:
        """Unregister a template."""
        if template_type not in self._templates:
            return False
        
        configs = self._templates[template_type]
        for i, config in enumerate(configs):
            if config.name == template_name:
                del configs[i]
                logger.info(f"Unregistered template {template_name} for type {template_type}")
                return True
        
        return False
    
    def get_template(self, template_type: str, data: Dict[str, Any], 
                    user_id: Optional[str] = None, 
                    channel_config: Optional[ChannelConfig] = None,
                    user_preferences: Optional[UserPreferences] = None,
                    use_cache: bool = True) -> TemplateInterface:
        """Get template instance for given type and data with enhanced context."""
        start_time = time.time()
        template_key = f"{template_type}_{user_id or 'anonymous'}"
        
        try:
            # Check cache first
            if use_cache:
                cached_result = self._cache.get(template_type, data, user_id)
                if cached_result:
                    self._update_cache_metrics(template_key, hit=True)
                    return self._create_cached_template(cached_result)
                else:
                    self._update_cache_metrics(template_key, hit=False)
            
            # Get template configurations
            configs = self._get_available_configs(template_type, data)
            if not configs:
                raise ValueError(f"No templates registered for type: {template_type}")
            
            # Select template variant (A/B testing)
            selected_config = self._select_template_config(configs, user_id, data)
            
            # Create template instance with enhanced context
            template = self._create_template_instance(
                selected_config, data, user_id, channel_config, user_preferences
            )
            
            # Cache result if enabled
            if use_cache:
                result = template.render()
                cache_ttl = selected_config.cache_ttl
                self._cache.set(template_type, data, result, user_id, cache_ttl)
                template = self._create_cached_template(result, template)
            
            # Update metrics
            render_time = time.time() - start_time
            self._update_metrics(template_key, render_time, template, success=True)
            
            # Check for performance alerts
            self._check_performance_alert(template_key, render_time, selected_config)
            
            return template
            
        except Exception as e:
            render_time = time.time() - start_time
            self._update_metrics(template_key, render_time, None, success=False)
            logger.error(f"Error creating template {template_type}: {e}")
            raise
    
    def _create_cached_template(self, result: Dict[str, Any], 
                               original_template: Optional[TemplateInterface] = None) -> TemplateInterface:
        """Create a cached template wrapper."""
        class CachedTemplate:
            def __init__(self, cached_result: Dict[str, Any], original: Optional[TemplateInterface] = None):
                self.result = cached_result
                self.original = original
            
            def render(self) -> Dict[str, Any]:
                return self.result
            
            def get_fallback_text(self) -> str:
                return self.result.get('text', 'DevSync AI Notification')
            
            def get_analytics_data(self) -> Dict[str, Any]:
                if self.original:
                    return self.original.get_analytics_data()
                return {
                    "cached": True,
                    "created_at": datetime.now().isoformat(),
                    "block_count": len(self.result.get('blocks', []))
                }
            
            def has_errors(self) -> bool:
                return self.original.has_errors() if self.original else False
            
            def get_errors(self) -> List[str]:
                return self.original.get_errors() if self.original else []
        
        return CachedTemplate(result, original_template)
    
    def _get_available_configs(self, template_type: str, data: Dict[str, Any]) -> List[TemplateConfig]:
        """Get available template configurations for given type and data."""
        if template_type not in self._templates:
            return []
        
        available_configs = []
        
        for config in self._templates[template_type]:
            # Check if template is enabled
            if not config.enabled:
                continue
            
            # Check environment
            if config.environment and config.environment != self._environment:
                continue
            
            # Check feature flags
            if config.feature_flags:
                if not all(self._feature_flags.get(flag, False) for flag in config.feature_flags):
                    continue
            
            available_configs.append(config)
        
        return available_configs
    
    def _select_template_config(self, configs: List[TemplateConfig], 
                              user_id: Optional[str], data: Dict[str, Any]) -> TemplateConfig:
        """Select template configuration using A/B testing."""
        if not configs:
            raise ValueError("No available template configurations")
        
        # If no user_id provided, use first available config
        if not user_id:
            return configs[0]
        
        # Use A/B testing to select variant
        return self._ab_test_manager.get_template_variant(user_id, configs)
    
    def _create_template_instance(self, config: TemplateConfig, data: Dict[str, Any],
                                 user_id: Optional[str] = None,
                                 channel_config: Optional[ChannelConfig] = None,
                                 user_preferences: Optional[UserPreferences] = None) -> TemplateInterface:
        """Create template instance from configuration with enhanced context."""
        
        # Prepare metadata
        metadata = MessageMetadata(
            template_name=config.name,
            template_version=config.version.value,
            user_id=user_id,
            channel_id=channel_config.channel_id if channel_config else None,
            priority=config.priority
        )
        
        # Use config-specific or global branding
        team_branding = config.team_branding or self._global_team_branding
        accessibility_options = config.accessibility_options or self._global_accessibility
        
        if config.template_class:
            # Check if it's a new base template class
            if issubclass(config.template_class, SlackMessageTemplate):
                template_instance = config.template_class(
                    data=data,
                    metadata=metadata,
                    team_branding=team_branding,
                    channel_config=channel_config,
                    user_preferences=user_preferences,
                    accessibility_options=accessibility_options
                )
            else:
                # Legacy template class
                template_instance = config.template_class(data)
            
            return TemplateWrapper(template_instance, config.factory_function)
        
        elif config.factory_function:
            # Use factory function
            result = config.factory_function(data)
            
            class FactoryTemplate:
                def __init__(self, result: Dict[str, Any]):
                    self.result = result
                    self.metadata = metadata
                
                def render(self) -> Dict[str, Any]:
                    return self.result
                
                def get_fallback_text(self) -> str:
                    return self.result.get('text', 'DevSync AI Notification')
                
                def get_analytics_data(self) -> Dict[str, Any]:
                    return {
                        "template_name": self.metadata.template_name,
                        "template_version": self.metadata.template_version,
                        "created_at": self.metadata.created_at.isoformat(),
                        "user_id": self.metadata.user_id,
                        "priority": self.metadata.priority.value,
                        "block_count": len(self.result.get('blocks', [])),
                        "factory_function": True
                    }
                
                def has_errors(self) -> bool:
                    return False  # Factory functions don't typically have error states
                
                def get_errors(self) -> List[str]:
                    return []
            
            return FactoryTemplate(result)
        
        else:
            raise ValueError(f"Template config {config.name} has no template_class or factory_function")
    
    def _update_metrics(self, template_key: str, render_time: float, 
                       template: Optional[TemplateInterface], success: bool) -> None:
        """Update comprehensive template metrics."""
        with self._lock:
            if template_key not in self._metrics:
                self._metrics[template_key] = TemplateMetrics()
            
            metrics = self._metrics[template_key]
            metrics.render_count += 1
            metrics.update_render_time(render_time)
            
            if not success:
                metrics.error_count += 1
            elif template:
                # Check for warnings in new base templates
                if hasattr(template, 'has_warnings') and template.has_warnings():
                    metrics.warning_count += 1
    
    def _update_cache_metrics(self, template_key: str, hit: bool) -> None:
        """Update cache-specific metrics."""
        with self._lock:
            if template_key not in self._metrics:
                self._metrics[template_key] = TemplateMetrics()
            
            metrics = self._metrics[template_key]
            if hit:
                metrics.cache_hits += 1
            else:
                metrics.cache_misses += 1
    
    def _check_performance_alert(self, template_key: str, render_time: float, 
                                config: TemplateConfig) -> None:
        """Check for performance alerts."""
        threshold = config.performance_threshold
        if render_time > threshold:
            alert = {
                "template_key": template_key,
                "render_time": render_time,
                "threshold": threshold,
                "timestamp": datetime.now().isoformat(),
                "config_name": config.name
            }
            self._performance_alerts.append(alert)
            
            # Keep only recent alerts (last 100)
            if len(self._performance_alerts) > 100:
                self._performance_alerts = self._performance_alerts[-100:]
            
            logger.warning(f"Slow template render: {template_key} took {render_time:.2f}s (threshold: {threshold}s)")
    
    def _start_cleanup_task(self) -> None:
        """Start background cleanup task for cache maintenance."""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(300)  # Run every 5 minutes
                    expired_count = self._cache.cleanup_expired()
                    if expired_count > 0:
                        logger.debug(f"Cleaned up {expired_count} expired cache entries")
                except Exception as e:
                    logger.error(f"Error in cache cleanup: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def set_environment(self, environment: str) -> None:
        """Set current environment."""
        self._environment = environment
        logger.info(f"Environment set to: {environment}")
    
    def set_feature_flag(self, flag: str, enabled: bool) -> None:
        """Set feature flag."""
        self._feature_flags[flag] = enabled
        logger.info(f"Feature flag {flag} set to: {enabled}")
    
    def load_config(self, config_path: str) -> None:
        """Load configuration from file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_path}")
            return
        
        try:
            with open(config_file, 'r') as f:
                if config_file.suffix.lower() in ['.yml', '.yaml']:
                    try:
                        import yaml
                        config_data = yaml.safe_load(f)
                    except ImportError:
                        logger.error("PyYAML not installed, cannot load YAML config files")
                        return
                else:
                    config_data = json.load(f)
            
            # Load environment
            if 'environment' in config_data:
                self.set_environment(config_data['environment'])
            
            # Load feature flags
            if 'feature_flags' in config_data:
                for flag, enabled in config_data['feature_flags'].items():
                    self.set_feature_flag(flag, enabled)
            
            # Load template configurations
            if 'templates' in config_data:
                for template_type, template_configs in config_data['templates'].items():
                    for config_dict in template_configs:
                        # Convert dict to TemplateConfig
                        # Note: This is simplified - in practice you'd need more sophisticated
                        # deserialization to handle template_class references
                        config = TemplateConfig(
                            name=config_dict['name'],
                            template_class=None,  # Would need class resolution
                            version=TemplateVersion(config_dict.get('version', 'stable')),
                            enabled=config_dict.get('enabled', True),
                            weight=config_dict.get('weight', 100),
                            environment=config_dict.get('environment'),
                            feature_flags=config_dict.get('feature_flags', []),
                            metadata=config_dict.get('metadata', {})
                        )
                        self.register_template(template_type, config)
            
            logger.info(f"Loaded configuration from {config_path}")
            
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive template metrics."""
        with self._lock:
            template_metrics = {}
            for key, metrics in self._metrics.items():
                template_metrics[key] = {
                    "render_count": metrics.render_count,
                    "average_render_time": metrics.average_render_time,
                    "peak_render_time": metrics.peak_render_time,
                    "min_render_time": metrics.min_render_time if metrics.min_render_time != float('inf') else 0,
                    "error_count": metrics.error_count,
                    "warning_count": metrics.warning_count,
                    "error_rate": metrics.error_rate,
                    "cache_hit_rate": metrics.cache_hit_rate,
                    "last_used": metrics.last_used,
                    "first_used": metrics.first_used
                }
            
            return {
                "templates": template_metrics,
                "cache": self._cache.get_stats(),
                "performance_alerts": self._performance_alerts[-10:],  # Last 10 alerts
                "environment": self._environment,
                "feature_flags": self._feature_flags
            }
    
    def get_registered_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get detailed list of registered templates by type."""
        result = {}
        for template_type, configs in self._templates.items():
            result[template_type] = []
            for config in configs:
                result[template_type].append({
                    "name": config.name,
                    "version": config.version.value,
                    "enabled": config.enabled,
                    "weight": config.weight,
                    "environment": config.environment,
                    "feature_flags": config.feature_flags,
                    "priority": config.priority.value,
                    "cache_ttl": config.cache_ttl,
                    "performance_threshold": config.performance_threshold
                })
        return result
    
    def clear_cache(self) -> None:
        """Clear template cache."""
        self._cache.clear()
        logger.info("Template cache cleared manually")
    
    def set_global_branding(self, branding: TeamBranding) -> None:
        """Set global team branding."""
        self._global_team_branding = branding
        logger.info(f"Global team branding set for {branding.team_name}")
    
    def set_global_accessibility(self, accessibility: AccessibilityOptions) -> None:
        """Set global accessibility options."""
        self._global_accessibility = accessibility
        logger.info("Global accessibility options updated")
    
    def get_performance_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent performance alerts."""
        return self._performance_alerts[-limit:]
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._performance_alerts.clear()
            logger.info("All metrics reset")
    
    def render_template(self, template_type: str, data: Dict[str, Any], 
                       user_id: Optional[str] = None, 
                       channel_config: Optional[ChannelConfig] = None,
                       user_preferences: Optional[UserPreferences] = None,
                       use_cache: bool = True) -> Dict[str, Any]:
        """Convenience method to get template and render in one call."""
        template = self.get_template(
            template_type, data, user_id, channel_config, user_preferences, use_cache
        )
        return template.render()
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the factory."""
        cache_stats = self._cache.get_stats()
        metrics = self.get_metrics()
        
        # Calculate overall health score
        health_score = 100
        issues = []
        
        # Check cache hit rate
        if cache_stats['hit_rate'] < 0.5:
            health_score -= 10
            issues.append("Low cache hit rate")
        
        # Check for high error rates
        for template_key, template_metrics in metrics['templates'].items():
            if template_metrics['error_rate'] > 0.1:  # 10% error rate
                health_score -= 20
                issues.append(f"High error rate for {template_key}")
        
        # Check for performance issues
        recent_alerts = len([a for a in self._performance_alerts 
                           if datetime.fromisoformat(a['timestamp']) > 
                           datetime.now() - timedelta(hours=1)])
        if recent_alerts > 10:
            health_score -= 15
            issues.append("Multiple performance alerts in last hour")
        
        return {
            "health_score": max(0, health_score),
            "status": "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "unhealthy",
            "issues": issues,
            "cache_stats": cache_stats,
            "template_count": len(self._templates),
            "total_renders": sum(m.render_count for m in self._metrics.values()),
            "timestamp": datetime.now().isoformat()
        }


# Global factory instance
_factory_instance: Optional[MessageTemplateFactory] = None


def get_factory() -> MessageTemplateFactory:
    """Get global factory instance."""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = MessageTemplateFactory()
    return _factory_instance


def set_factory(factory: MessageTemplateFactory) -> None:
    """Set global factory instance."""
    global _factory_instance
    _factory_instance = factory


# Convenience functions using global factory
def create_message(template_type: str, data: Dict[str, Any], 
                  user_id: Optional[str] = None, use_cache: bool = True) -> Dict[str, Any]:
    """Create message using global factory."""
    return get_factory().render_template(template_type, data, user_id, use_cache)


def register_custom_template(template_type: str, config: TemplateConfig) -> None:
    """Register custom template using global factory."""
    get_factory().register_template(template_type, config)