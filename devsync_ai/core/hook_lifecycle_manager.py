"""
Hook Lifecycle Manager for Agent Hooks.

This module manages the lifecycle of Agent Hooks including initialization,
execution, monitoring, and cleanup.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set
from contextlib import asynccontextmanager

from .agent_hooks import (
    AgentHook, 
    HookExecutionResult, 
    HookStatus, 
    EnrichedEvent,
    HookRegistry
)


logger = logging.getLogger(__name__)


class HookExecutionContext:
    """Context for hook execution with timeout and cancellation support."""
    
    def __init__(self, hook: AgentHook, event: EnrichedEvent, timeout_seconds: int = 30):
        """
        Initialize execution context.
        
        Args:
            hook: The hook to execute
            event: The event to process
            timeout_seconds: Execution timeout in seconds
        """
        self.hook = hook
        self.event = event
        self.timeout_seconds = timeout_seconds
        self.start_time = datetime.now(timezone.utc)
        self._task: Optional[asyncio.Task] = None
        self._cancelled = False
    
    @property
    def execution_time_ms(self) -> float:
        """Get current execution time in milliseconds."""
        delta = datetime.now(timezone.utc) - self.start_time
        return delta.total_seconds() * 1000
    
    def cancel(self):
        """Cancel the execution."""
        self._cancelled = True
        if self._task and not self._task.done():
            self._task.cancel()
    
    @property
    def is_cancelled(self) -> bool:
        """Check if execution was cancelled."""
        return self._cancelled


class HookLifecycleManager:
    """
    Manages the lifecycle of Agent Hooks including execution, monitoring, and cleanup.
    """
    
    def __init__(self, hook_registry: HookRegistry):
        """
        Initialize the lifecycle manager.
        
        Args:
            hook_registry: Registry containing all hooks
        """
        self.hook_registry = hook_registry
        self._active_executions: Dict[str, HookExecutionContext] = {}
        self._execution_history: List[HookExecutionResult] = []
        self._max_history_size = 1000
        self._cleanup_interval = 300  # 5 minutes
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the lifecycle manager."""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Hook lifecycle manager started")
    
    async def stop(self):
        """Stop the lifecycle manager and cancel all active executions."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all active executions
        await self._cancel_all_executions()
        
        logger.info("Hook lifecycle manager stopped")
    
    async def execute_hook(self, hook: AgentHook, event: EnrichedEvent) -> HookExecutionResult:
        """
        Execute a single hook with the given event.
        
        Args:
            hook: The hook to execute
            event: The event to process
            
        Returns:
            Result of the hook execution
        """
        if not hook.enabled:
            return HookExecutionResult(
                hook_id=hook.hook_id,
                execution_id="",
                hook_type=hook.hook_type,
                event_id=event.event_id,
                status=HookStatus.CANCELLED,
                execution_time_ms=0.0,
                errors=["Hook is disabled"]
            )
        
        # Create execution context
        context = HookExecutionContext(
            hook=hook,
            event=event,
            timeout_seconds=hook.configuration.timeout_seconds
        )
        
        # Create initial execution result
        result = HookExecutionResult(
            hook_id=hook.hook_id,
            execution_id="",
            hook_type=hook.hook_type,
            event_id=event.event_id,
            status=HookStatus.PENDING,
            execution_time_ms=0.0
        )
        
        try:
            # Check if hook can handle the event
            if not await hook.can_handle(event):
                result.status = HookStatus.CANCELLED
                result.add_error("Hook cannot handle this event type")
                return result
            
            # Register active execution
            self._active_executions[result.execution_id] = context
            result.status = HookStatus.RUNNING
            
            # Execute hook with timeout
            context._task = asyncio.create_task(hook.execute(event))
            
            try:
                execution_result = await asyncio.wait_for(
                    context._task,
                    timeout=context.timeout_seconds
                )
                
                # Update result with execution outcome
                result = execution_result
                result.execution_time_ms = context.execution_time_ms
                
                if result.status == HookStatus.PENDING:
                    result.status = HookStatus.SUCCESS
                
            except asyncio.TimeoutError:
                result.add_error(f"Hook execution timed out after {context.timeout_seconds} seconds")
                result.status = HookStatus.FAILED
                context.cancel()
                
            except asyncio.CancelledError:
                result.add_error("Hook execution was cancelled")
                result.status = HookStatus.CANCELLED
                
            except Exception as e:
                result.add_error(f"Hook execution failed: {str(e)}")
                result.status = HookStatus.FAILED
                logger.exception(f"Hook {hook.hook_id} execution failed")
        
        finally:
            # Clean up execution context
            result.execution_time_ms = context.execution_time_ms
            result.mark_completed(result.status)
            
            if result.execution_id in self._active_executions:
                del self._active_executions[result.execution_id]
            
            # Add to execution history
            self._add_to_history(result)
        
        return result
    
    async def execute_hooks_for_event(self, event: EnrichedEvent) -> List[HookExecutionResult]:
        """
        Execute all applicable hooks for the given event.
        
        Args:
            event: The event to process
            
        Returns:
            List of execution results for all applicable hooks
        """
        applicable_hooks = []
        enabled_hooks = self.hook_registry.get_enabled_hooks()
        
        # Find hooks that can handle this event
        for hook in enabled_hooks:
            try:
                if await hook.can_handle(event):
                    applicable_hooks.append(hook)
            except Exception as e:
                logger.warning(f"Error checking if hook {hook.hook_id} can handle event: {e}")
        
        if not applicable_hooks:
            logger.debug(f"No hooks found for event {event.event_id}")
            return []
        
        logger.info(f"Executing {len(applicable_hooks)} hooks for event {event.event_id}")
        
        # Execute all applicable hooks concurrently
        tasks = [
            self.execute_hook(hook, event)
            for hook in applicable_hooks
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions from concurrent execution
        execution_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                hook = applicable_hooks[i]
                error_result = HookExecutionResult(
                    hook_id=hook.hook_id,
                    execution_id="",
                    hook_type=hook.hook_type,
                    event_id=event.event_id,
                    status=HookStatus.FAILED,
                    execution_time_ms=0.0,
                    errors=[f"Concurrent execution error: {str(result)}"]
                )
                execution_results.append(error_result)
                logger.exception(f"Concurrent execution error for hook {hook.hook_id}")
            else:
                execution_results.append(result)
        
        return execution_results
    
    async def retry_failed_execution(self, execution_result: HookExecutionResult) -> Optional[HookExecutionResult]:
        """
        Retry a failed hook execution.
        
        Args:
            execution_result: The failed execution result to retry
            
        Returns:
            New execution result or None if retry is not applicable
        """
        hook = self.hook_registry.get_hook(execution_result.hook_id)
        if not hook:
            logger.warning(f"Cannot retry execution: hook {execution_result.hook_id} not found")
            return None
        
        if not hook.should_retry(execution_result):
            logger.debug(f"Hook {execution_result.hook_id} should not be retried")
            return None
        
        # Get retry count and calculate delay
        retry_count = execution_result.metadata.get('retry_count', 0)
        delay = hook.get_retry_delay(retry_count)
        
        logger.info(f"Retrying hook {execution_result.hook_id} after {delay} seconds (attempt {retry_count + 1})")
        
        # Wait for retry delay
        await asyncio.sleep(delay)
        
        # Create event from original execution (this would need to be stored)
        # For now, we'll return None as we don't have the original event
        logger.warning("Cannot retry execution: original event not available")
        return None
    
    def get_active_executions(self) -> Dict[str, HookExecutionContext]:
        """
        Get all currently active hook executions.
        
        Returns:
            Dictionary of execution ID to execution context
        """
        return self._active_executions.copy()
    
    def get_execution_history(self, limit: Optional[int] = None) -> List[HookExecutionResult]:
        """
        Get execution history.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of execution results, most recent first
        """
        history = sorted(self._execution_history, key=lambda x: x.started_at, reverse=True)
        if limit:
            history = history[:limit]
        return history
    
    def get_hook_statistics(self, hook_id: str) -> Dict[str, any]:
        """
        Get statistics for a specific hook.
        
        Args:
            hook_id: ID of the hook to get statistics for
            
        Returns:
            Dictionary containing hook statistics
        """
        hook_executions = [
            result for result in self._execution_history
            if result.hook_id == hook_id
        ]
        
        if not hook_executions:
            return {
                'total_executions': 0,
                'success_rate': 0.0,
                'average_execution_time_ms': 0.0,
                'last_execution': None
            }
        
        successful = len([r for r in hook_executions if r.status == HookStatus.SUCCESS])
        total = len(hook_executions)
        
        avg_time = sum(r.execution_time_ms for r in hook_executions) / total
        last_execution = max(hook_executions, key=lambda x: x.started_at)
        
        return {
            'total_executions': total,
            'success_rate': successful / total if total > 0 else 0.0,
            'average_execution_time_ms': avg_time,
            'last_execution': last_execution.started_at,
            'recent_errors': [
                r.errors for r in hook_executions[-5:]
                if r.errors
            ]
        }
    
    async def _cancel_all_executions(self):
        """Cancel all active executions."""
        if not self._active_executions:
            return
        
        logger.info(f"Cancelling {len(self._active_executions)} active executions")
        
        for context in self._active_executions.values():
            context.cancel()
        
        # Wait for all executions to complete or timeout
        timeout = 10  # 10 seconds to clean up
        start_time = datetime.utcnow()
        
        while self._active_executions and (datetime.utcnow() - start_time).total_seconds() < timeout:
            await asyncio.sleep(0.1)
        
        if self._active_executions:
            logger.warning(f"{len(self._active_executions)} executions did not complete during shutdown")
    
    async def _cleanup_loop(self):
        """Background task for periodic cleanup."""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_execution_history()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in cleanup loop: {e}")
    
    async def _cleanup_execution_history(self):
        """Clean up old execution history entries."""
        if len(self._execution_history) <= self._max_history_size:
            return
        
        # Keep only the most recent entries
        self._execution_history.sort(key=lambda x: x.started_at, reverse=True)
        removed_count = len(self._execution_history) - self._max_history_size
        self._execution_history = self._execution_history[:self._max_history_size]
        
        logger.debug(f"Cleaned up {removed_count} old execution history entries")
    
    def _add_to_history(self, result: HookExecutionResult):
        """Add execution result to history."""
        self._execution_history.append(result)
        
        # Immediate cleanup if we're over the limit
        if len(self._execution_history) > self._max_history_size * 1.1:
            asyncio.create_task(self._cleanup_execution_history())


@asynccontextmanager
async def hook_lifecycle_manager(hook_registry: HookRegistry):
    """
    Context manager for hook lifecycle manager.
    
    Args:
        hook_registry: Registry containing all hooks
        
    Yields:
        Initialized and started lifecycle manager
    """
    manager = HookLifecycleManager(hook_registry)
    await manager.start()
    try:
        yield manager
    finally:
        await manager.stop()