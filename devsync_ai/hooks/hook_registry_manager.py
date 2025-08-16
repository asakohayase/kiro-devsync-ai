"""
Hook Registry Manager for automatic registration and lifecycle management.

This module provides comprehensive hook management including registration,
configuration, monitoring, and error handling.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass, field
import yaml
import os

from devsync_ai.core.agent_hooks import (
    AgentHook, 
    HookRegistry, 
    HookConfiguration,
    HookExecutionResult
)
from devsync_ai.core.agent_hook_dispatcher import AgentHookDispatcher
from devsync_ai.core.hook_lifecycle_manager import HookLifecycleManager
from devsync_ai.hooks.jira_agent_hooks import AVAILABLE_HOOKS
from devsync_ai.config import settings


logger = logging.getLogger(__name__)


@dataclass
class HookRegistrationResult:
    """Result of hook registration operation."""
    hook_id: str
    hook_type: str
    success: bool
    error_message: Optional[str] = None
    configuration_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class HookSystemHealth:
    """Overall health status of the hook system."""
    total_hooks: int
    enabled_hooks: int
    disabled_hooks: int
    failed_hooks: int
    average_execution_time_ms: float
    success_rate: float
    last_health_check: datetime
    component_health: Dict[str, str] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)


class HookConfigurationManager:
    """Manages hook configurations from files and environment."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or "config/jira_webhook_config.yaml"
        self._config_cache: Optional[Dict[str, Any]] = None
        self._last_reload = datetime.min
    
    async def load_configuration(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load configuration from file with caching."""
        now = datetime.now(timezone.utc)
        
        # Check if we need to reload
        if (not force_reload and 
            self._config_cache and 
            (now - self._last_reload).total_seconds() < 300):  # 5 minute cache
            return self._config_cache
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Merge with environment variables
                config = self._merge_environment_config(config)
                
                self._config_cache = config
                self._last_reload = now
                
                logger.info(f"Configuration loaded from {self.config_path}")
                return config
            else:
                logger.warning(f"Configuration file not found: {self.config_path}")
                return self._get_default_configuration()
                
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return self._get_default_configuration()
    
    def _merge_environment_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configuration with environment variables."""
        # Override with environment variables
        env_overrides = {
            'jira_webhook.webhook_secret': os.getenv('JIRA_WEBHOOK_SECRET'),
            'jira_webhook.rate_limiting.max_requests_per_minute': os.getenv('JIRA_WEBHOOK_RATE_LIMIT'),
            'agent_hooks.global.default_timeout_seconds': os.getenv('HOOK_EXECUTION_TIMEOUT'),
        }
        
        for key_path, value in env_overrides.items():
            if value is not None:
                self._set_nested_value(config, key_path, value)
        
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], key_path: str, value: Any):
        """Set nested configuration value using dot notation."""
        keys = key_path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Convert string values to appropriate types
        if isinstance(value, str):
            if value.isdigit():
                value = int(value)
            elif value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
        
        current[keys[-1]] = value
    
    def _get_default_configuration(self) -> Dict[str, Any]:
        """Get default configuration when file is not available."""
        return {
            'agent_hooks': {
                'global': {
                    'enabled': True,
                    'default_timeout_seconds': 30,
                    'default_retry_attempts': 3
                },
                'teams': {
                    'default': {
                        'status_change': {'enabled': True, 'channels': ['#dev-updates']},
                        'blocker_detection': {'enabled': True, 'channels': ['#blockers']},
                        'assignment_change': {'enabled': True, 'channels': ['#team-assignments']},
                        'critical_update': {'enabled': True, 'channels': ['#critical-alerts']},
                        'comment_activity': {'enabled': True, 'channels': ['#ticket-discussions']}
                    }
                }
            }
        }
    
    async def get_team_configuration(self, team_id: str) -> Dict[str, Any]:
        """Get configuration for a specific team."""
        config = await self.load_configuration()
        teams_config = config.get('agent_hooks', {}).get('teams', {})
        
        # Return team-specific config or default
        return teams_config.get(team_id, teams_config.get('default', {}))
    
    async def validate_configuration(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration structure and values."""
        errors = []
        
        # Validate required sections
        if 'agent_hooks' not in config:
            errors.append("Missing 'agent_hooks' section")
            return errors
        
        agent_hooks = config['agent_hooks']
        
        if 'teams' not in agent_hooks:
            errors.append("Missing 'teams' section in agent_hooks")
            return errors
        
        # Validate team configurations
        teams = agent_hooks['teams']
        for team_id, team_config in teams.items():
            if not isinstance(team_config, dict):
                errors.append(f"Team '{team_id}' configuration must be a dictionary")
                continue
            
            # Validate hook configurations
            for hook_type, hook_config in team_config.items():
                if hook_type not in AVAILABLE_HOOKS:
                    errors.append(f"Unknown hook type '{hook_type}' in team '{team_id}'")
                    continue
                
                if not isinstance(hook_config, dict):
                    errors.append(f"Hook '{hook_type}' configuration must be a dictionary")
                    continue
                
                # Validate required fields
                if 'enabled' not in hook_config:
                    errors.append(f"Missing 'enabled' field for hook '{hook_type}' in team '{team_id}'")
                
                if 'channels' not in hook_config:
                    errors.append(f"Missing 'channels' field for hook '{hook_type}' in team '{team_id}'")
                elif not isinstance(hook_config['channels'], list):
                    errors.append(f"'channels' must be a list for hook '{hook_type}' in team '{team_id}'")
        
        return errors


class HookRegistryManager:
    """
    Comprehensive hook registry manager with automatic registration,
    lifecycle management, and monitoring.
    """
    
    def __init__(self, dispatcher: AgentHookDispatcher):
        """
        Initialize hook registry manager.
        
        Args:
            dispatcher: Agent hook dispatcher instance
        """
        self.dispatcher = dispatcher
        self.config_manager = HookConfigurationManager()
        self._registered_hooks: Dict[str, AgentHook] = {}
        self._hook_health: Dict[str, HookSystemHealth] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the hook registry manager."""
        if self._running:
            return
        
        self._running = True
        
        # Load configuration and register hooks
        await self.register_all_hooks()
        
        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Hook registry manager started")
    
    async def stop(self):
        """Stop the hook registry manager."""
        if not self._running:
            return
        
        self._running = False
        
        # Stop monitoring
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Unregister all hooks
        await self.unregister_all_hooks()
        
        logger.info("Hook registry manager stopped")
    
    async def register_all_hooks(self) -> List[HookRegistrationResult]:
        """Register all available hooks based on configuration."""
        config = await self.config_manager.load_configuration()
        
        # Validate configuration
        validation_errors = await self.config_manager.validate_configuration(config)
        if validation_errors:
            logger.error(f"Configuration validation failed: {validation_errors}")
        
        results = []
        teams_config = config.get('agent_hooks', {}).get('teams', {})
        global_config = config.get('agent_hooks', {}).get('global', {})
        
        for team_id, team_config in teams_config.items():
            for hook_type, hook_config in team_config.items():
                if hook_type not in AVAILABLE_HOOKS:
                    continue
                
                result = await self._register_hook(
                    team_id, hook_type, hook_config, global_config
                )
                results.append(result)
        
        successful_registrations = len([r for r in results if r.success])
        logger.info(f"Registered {successful_registrations}/{len(results)} hooks")
        
        return results
    
    async def _register_hook(
        self, 
        team_id: str, 
        hook_type: str, 
        hook_config: Dict[str, Any],
        global_config: Dict[str, Any]
    ) -> HookRegistrationResult:
        """Register a single hook."""
        hook_id = f"{team_id}_{hook_type}"
        
        try:
            # Get hook class
            hook_class = AVAILABLE_HOOKS[hook_type]
            
            # Create hook configuration
            configuration = HookConfiguration(
                hook_id=hook_id,
                hook_type=hook_type,
                team_id=team_id,
                enabled=hook_config.get('enabled', True),
                notification_channels=hook_config.get('channels', []),
                rate_limit_per_hour=hook_config.get('rate_limit_per_hour', 50),
                retry_attempts=global_config.get('default_retry_attempts', 3),
                timeout_seconds=global_config.get('default_timeout_seconds', 30),
                metadata=hook_config
            )
            
            # Validate configuration
            validation_errors = []
            if not configuration.notification_channels:
                validation_errors.append("No notification channels specified")
            
            # Create hook instance
            hook_instance = hook_class(hook_id, configuration)
            
            # Validate hook configuration
            hook_validation_errors = await hook_instance.validate_configuration()
            validation_errors.extend(hook_validation_errors)
            
            if validation_errors:
                return HookRegistrationResult(
                    hook_id=hook_id,
                    hook_type=hook_type,
                    success=False,
                    configuration_valid=False,
                    validation_errors=validation_errors
                )
            
            # Register with dispatcher
            success = await self.dispatcher.register_hook(hook_instance)
            
            if success:
                self._registered_hooks[hook_id] = hook_instance
                logger.info(f"Successfully registered hook: {hook_id}")
            
            return HookRegistrationResult(
                hook_id=hook_id,
                hook_type=hook_type,
                success=success,
                configuration_valid=True
            )
            
        except Exception as e:
            logger.error(f"Failed to register hook {hook_id}: {e}", exc_info=True)
            return HookRegistrationResult(
                hook_id=hook_id,
                hook_type=hook_type,
                success=False,
                error_message=str(e)
            )
    
    async def unregister_all_hooks(self):
        """Unregister all hooks."""
        for hook_id in list(self._registered_hooks.keys()):
            await self.unregister_hook(hook_id)
    
    async def unregister_hook(self, hook_id: str) -> bool:
        """Unregister a specific hook."""
        try:
            success = await self.dispatcher.unregister_hook(hook_id)
            if success and hook_id in self._registered_hooks:
                del self._registered_hooks[hook_id]
                logger.info(f"Unregistered hook: {hook_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to unregister hook {hook_id}: {e}")
            return False
    
    async def reload_configuration(self) -> List[HookRegistrationResult]:
        """Reload configuration and re-register hooks."""
        logger.info("Reloading hook configuration")
        
        # Unregister existing hooks
        await self.unregister_all_hooks()
        
        # Force reload configuration
        await self.config_manager.load_configuration(force_reload=True)
        
        # Re-register hooks
        return await self.register_all_hooks()
    
    async def enable_hook(self, hook_id: str) -> bool:
        """Enable a specific hook."""
        if hook_id in self._registered_hooks:
            hook = self._registered_hooks[hook_id]
            hook.enable()
            logger.info(f"Enabled hook: {hook_id}")
            return True
        return False
    
    async def disable_hook(self, hook_id: str) -> bool:
        """Disable a specific hook."""
        if hook_id in self._registered_hooks:
            hook = self._registered_hooks[hook_id]
            hook.disable()
            logger.info(f"Disabled hook: {hook_id}")
            return True
        return False
    
    async def get_hook_status(self, hook_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a specific hook."""
        if hook_id not in self._registered_hooks:
            return None
        
        hook = self._registered_hooks[hook_id]
        stats = self.dispatcher.lifecycle_manager.get_hook_statistics(hook_id)
        
        return {
            'hook_id': hook_id,
            'hook_type': hook.hook_type,
            'team_id': hook.configuration.team_id,
            'enabled': hook.enabled,
            'configuration': {
                'channels': hook.configuration.notification_channels,
                'rate_limit_per_hour': hook.configuration.rate_limit_per_hour,
                'retry_attempts': hook.configuration.retry_attempts,
                'timeout_seconds': hook.configuration.timeout_seconds
            },
            'statistics': stats
        }
    
    async def get_system_health(self) -> HookSystemHealth:
        """Get overall system health status."""
        total_hooks = len(self._registered_hooks)
        enabled_hooks = len([h for h in self._registered_hooks.values() if h.enabled])
        disabled_hooks = total_hooks - enabled_hooks
        
        # Get execution statistics
        all_stats = []
        failed_hooks = 0
        
        for hook_id in self._registered_hooks:
            stats = self.dispatcher.lifecycle_manager.get_hook_statistics(hook_id)
            all_stats.append(stats)
            
            if stats['success_rate'] < 0.8:  # Consider < 80% success rate as failed
                failed_hooks += 1
        
        # Calculate averages
        avg_execution_time = 0.0
        overall_success_rate = 0.0
        
        if all_stats:
            avg_execution_time = sum(s['average_execution_time_ms'] for s in all_stats) / len(all_stats)
            overall_success_rate = sum(s['success_rate'] for s in all_stats) / len(all_stats)
        
        # Check component health
        component_health = {
            'dispatcher': 'healthy',
            'lifecycle_manager': 'healthy',
            'configuration': 'healthy'
        }
        
        # Identify issues
        issues = []
        if failed_hooks > 0:
            issues.append(f"{failed_hooks} hooks have low success rates")
        if overall_success_rate < 0.9:
            issues.append("Overall success rate below 90%")
        if avg_execution_time > 5000:  # 5 seconds
            issues.append("Average execution time is high")
        
        return HookSystemHealth(
            total_hooks=total_hooks,
            enabled_hooks=enabled_hooks,
            disabled_hooks=disabled_hooks,
            failed_hooks=failed_hooks,
            average_execution_time_ms=avg_execution_time,
            success_rate=overall_success_rate,
            last_health_check=datetime.now(timezone.utc),
            component_health=component_health,
            issues=issues
        )
    
    async def get_all_hook_statuses(self) -> List[Dict[str, Any]]:
        """Get status for all registered hooks."""
        statuses = []
        for hook_id in self._registered_hooks:
            status = await self.get_hook_status(hook_id)
            if status:
                statuses.append(status)
        return statuses
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Perform health check
                health = await self.get_system_health()
                
                # Log issues
                if health.issues:
                    logger.warning(f"Hook system issues detected: {health.issues}")
                
                # Store health data
                self._hook_health[datetime.now(timezone.utc).isoformat()] = health
                
                # Clean up old health data (keep last 24 hours)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                self._hook_health = {
                    k: v for k, v in self._hook_health.items()
                    if datetime.fromisoformat(k) > cutoff_time
                }
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    def get_registered_hooks(self) -> Dict[str, AgentHook]:
        """Get all registered hooks."""
        return self._registered_hooks.copy()
    
    def get_available_hook_types(self) -> List[str]:
        """Get list of available hook types."""
        return list(AVAILABLE_HOOKS.keys())


# Global registry manager instance
_registry_manager: Optional[HookRegistryManager] = None


async def initialize_hook_registry(dispatcher: AgentHookDispatcher) -> HookRegistryManager:
    """Initialize the global hook registry manager."""
    global _registry_manager
    
    if _registry_manager is None:
        _registry_manager = HookRegistryManager(dispatcher)
        await _registry_manager.start()
    
    return _registry_manager


async def get_hook_registry_manager() -> Optional[HookRegistryManager]:
    """Get the global hook registry manager."""
    return _registry_manager


async def shutdown_hook_registry():
    """Shutdown the global hook registry manager."""
    global _registry_manager
    
    if _registry_manager:
        await _registry_manager.stop()
        _registry_manager = None