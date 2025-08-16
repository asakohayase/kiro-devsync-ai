"""
Unit tests for Agent Hook infrastructure.
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio

from devsync_ai.core.agent_hooks import (
    AgentHook,
    HookRegistry,
    HookConfiguration,
    HookExecutionResult,
    HookStatus,
    ProcessedEvent,
    EnrichedEvent,
    EventClassification,
    EventCategory,
    UrgencyLevel,
    SignificanceLevel,
    Stakeholder
)
from devsync_ai.core.hook_lifecycle_manager import (
    HookLifecycleManager,
    HookExecutionContext
)


class TestAgentHook(AgentHook):
    """Test implementation of AgentHook for testing."""
    
    def __init__(self, hook_id: str, configuration: HookConfiguration, can_handle_result: bool = True):
        super().__init__(hook_id, configuration)
        self.can_handle_result = can_handle_result
        self.execute_called = False
        self.execute_result = None
        self.execute_exception = None
    
    async def can_handle(self, event: EnrichedEvent) -> bool:
        return self.can_handle_result
    
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        self.execute_called = True
        
        if self.execute_exception:
            raise self.execute_exception
        
        if self.execute_result:
            return self.execute_result
        
        return HookExecutionResult(
            hook_id=self.hook_id,
            execution_id="test-execution",
            hook_type=self.hook_type,
            event_id=event.event_id,
            status=HookStatus.SUCCESS,
            execution_time_ms=100.0
        )


@pytest.fixture
def sample_configuration():
    """Create a sample hook configuration."""
    return HookConfiguration(
        hook_id="test-hook",
        hook_type="TestHook",
        team_id="test-team",
        enabled=True,
        notification_channels=["#test-channel"],
        rate_limit_per_hour=50,
        retry_attempts=2,
        timeout_seconds=15
    )


@pytest.fixture
def sample_event():
    """Create a sample enriched event."""
    processed_event = ProcessedEvent(
        event_id="test-event-123",
        event_type="jira:issue_updated",
        timestamp=datetime.now(timezone.utc),
        jira_event_data={"issue": {"key": "TEST-123"}},
        ticket_key="TEST-123",
        project_key="TEST",
        raw_payload={"webhookEvent": "jira:issue_updated"}
    )
    
    classification = EventClassification(
        category=EventCategory.STATUS_CHANGE,
        urgency=UrgencyLevel.MEDIUM,
        significance=SignificanceLevel.MODERATE,
        affected_teams=["test-team"],
        routing_hints={"channel": "#test-channel"}
    )
    
    stakeholder = Stakeholder(
        user_id="user123",
        display_name="Test User",
        email="test@example.com",
        role="developer",
        team_id="test-team"
    )
    
    return EnrichedEvent(
        **processed_event.__dict__,
        ticket_details={"summary": "Test ticket", "priority": "Medium"},
        stakeholders=[stakeholder],
        classification=classification,
        context_data={"additional": "context"}
    )


class TestAgentHookBase:
    """Test the base AgentHook functionality."""
    
    def test_hook_initialization(self, sample_configuration):
        """Test hook initialization."""
        hook = TestAgentHook("test-hook", sample_configuration)
        
        assert hook.hook_id == "test-hook"
        assert hook.hook_type == "TestAgentHook"
        assert hook.enabled is True
        assert hook.configuration == sample_configuration
    
    def test_hook_enable_disable(self, sample_configuration):
        """Test hook enable/disable functionality."""
        hook = TestAgentHook("test-hook", sample_configuration)
        
        assert hook.enabled is True
        
        hook.disable()
        assert hook.enabled is False
        
        hook.enable()
        assert hook.enabled is True
    
    def test_hook_configuration_disabled(self, sample_configuration):
        """Test hook behavior when configuration is disabled."""
        sample_configuration.enabled = False
        hook = TestAgentHook("test-hook", sample_configuration)
        
        assert hook.enabled is False
    
    async def test_validate_configuration_valid(self, sample_configuration):
        """Test configuration validation with valid configuration."""
        hook = TestAgentHook("test-hook", sample_configuration)
        errors = await hook.validate_configuration()
        
        assert errors == []
    
    async def test_validate_configuration_invalid(self):
        """Test configuration validation with invalid configuration."""
        invalid_config = HookConfiguration(
            hook_id="",  # Invalid: empty hook_id
            hook_type="TestHook",
            team_id="",  # Invalid: empty team_id
            rate_limit_per_hour=-1,  # Invalid: negative rate limit
            retry_attempts=-1,  # Invalid: negative retry attempts
            timeout_seconds=0  # Invalid: zero timeout
        )
        
        hook = TestAgentHook("test-hook", invalid_config)
        errors = await hook.validate_configuration()
        
        assert len(errors) == 5
        assert "Hook ID is required" in errors
        assert "Team ID is required" in errors
        assert "Rate limit must be positive" in errors
        assert "Retry attempts cannot be negative" in errors
        assert "Timeout must be positive" in errors
    
    def test_should_retry_logic(self, sample_configuration):
        """Test retry logic."""
        hook = TestAgentHook("test-hook", sample_configuration)
        
        # Test successful execution - should not retry
        success_result = HookExecutionResult(
            hook_id="test-hook",
            execution_id="test-exec",
            hook_type="TestHook",
            event_id="test-event",
            status=HookStatus.SUCCESS,
            execution_time_ms=100.0
        )
        assert hook.should_retry(success_result) is False
        
        # Test failed execution within retry limit - should retry
        failed_result = HookExecutionResult(
            hook_id="test-hook",
            execution_id="test-exec",
            hook_type="TestHook",
            event_id="test-event",
            status=HookStatus.FAILED,
            execution_time_ms=100.0,
            metadata={"retry_count": 1}
        )
        assert hook.should_retry(failed_result) is True
        
        # Test failed execution exceeding retry limit - should not retry
        failed_result.metadata["retry_count"] = 3
        assert hook.should_retry(failed_result) is False
    
    def test_get_retry_delay(self, sample_configuration):
        """Test retry delay calculation."""
        hook = TestAgentHook("test-hook", sample_configuration)
        
        # Test exponential backoff
        assert hook.get_retry_delay(0) == 1.0  # 2^0
        assert hook.get_retry_delay(1) == 2.0  # 2^1
        assert hook.get_retry_delay(2) == 4.0  # 2^2
        assert hook.get_retry_delay(3) == 8.0  # 2^3
        
        # Test maximum delay cap
        assert hook.get_retry_delay(10) == 300.0  # Capped at 300 seconds


class TestHookRegistry:
    """Test the HookRegistry functionality."""
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = HookRegistry()
        
        assert len(registry.get_all_hooks()) == 0
        assert len(registry.get_enabled_hooks()) == 0
    
    def test_register_hook(self, sample_configuration):
        """Test hook registration."""
        registry = HookRegistry()
        hook = TestAgentHook("test-hook", sample_configuration)
        
        # Test successful registration
        assert registry.register_hook(hook) is True
        assert len(registry.get_all_hooks()) == 1
        assert registry.get_hook("test-hook") == hook
    
    def test_register_duplicate_hook(self, sample_configuration):
        """Test registering duplicate hook."""
        registry = HookRegistry()
        hook1 = TestAgentHook("test-hook", sample_configuration)
        hook2 = TestAgentHook("test-hook", sample_configuration)
        
        assert registry.register_hook(hook1) is True
        assert registry.register_hook(hook2) is False  # Should fail
        assert len(registry.get_all_hooks()) == 1
    
    def test_unregister_hook(self, sample_configuration):
        """Test hook unregistration."""
        registry = HookRegistry()
        hook = TestAgentHook("test-hook", sample_configuration)
        
        registry.register_hook(hook)
        assert len(registry.get_all_hooks()) == 1
        
        # Test successful unregistration
        assert registry.unregister_hook("test-hook") is True
        assert len(registry.get_all_hooks()) == 0
        assert registry.get_hook("test-hook") is None
    
    def test_unregister_nonexistent_hook(self):
        """Test unregistering non-existent hook."""
        registry = HookRegistry()
        
        assert registry.unregister_hook("nonexistent") is False
    
    def test_get_hooks_by_type(self, sample_configuration):
        """Test getting hooks by type."""
        registry = HookRegistry()
        
        hook1 = TestAgentHook("hook1", sample_configuration)
        hook2 = TestAgentHook("hook2", sample_configuration)
        
        registry.register_hook(hook1)
        registry.register_hook(hook2)
        
        hooks_by_type = registry.get_hooks_by_type("TestAgentHook")
        assert len(hooks_by_type) == 2
        assert hook1 in hooks_by_type
        assert hook2 in hooks_by_type
    
    def test_get_enabled_hooks(self, sample_configuration):
        """Test getting enabled hooks."""
        registry = HookRegistry()
        
        enabled_hook = TestAgentHook("enabled", sample_configuration)
        disabled_hook = TestAgentHook("disabled", sample_configuration)
        disabled_hook.disable()
        
        registry.register_hook(enabled_hook)
        registry.register_hook(disabled_hook)
        
        enabled_hooks = registry.get_enabled_hooks()
        assert len(enabled_hooks) == 1
        assert enabled_hook in enabled_hooks
        assert disabled_hook not in enabled_hooks
    
    def test_clear_registry(self, sample_configuration):
        """Test clearing the registry."""
        registry = HookRegistry()
        
        hook1 = TestAgentHook("hook1", sample_configuration)
        hook2 = TestAgentHook("hook2", sample_configuration)
        
        registry.register_hook(hook1)
        registry.register_hook(hook2)
        
        assert len(registry.get_all_hooks()) == 2
        
        registry.clear()
        assert len(registry.get_all_hooks()) == 0


class TestHookExecutionResult:
    """Test HookExecutionResult functionality."""
    
    def test_execution_result_initialization(self):
        """Test execution result initialization."""
        result = HookExecutionResult(
            hook_id="test-hook",
            execution_id="test-exec",
            hook_type="TestHook",
            event_id="test-event",
            status=HookStatus.PENDING,
            execution_time_ms=0.0
        )
        
        assert result.hook_id == "test-hook"
        assert result.execution_id == "test-exec"
        assert result.hook_type == "TestHook"
        assert result.event_id == "test-event"
        assert result.status == HookStatus.PENDING
        assert result.execution_time_ms == 0.0
        assert result.notification_sent is False
        assert result.errors == []
        assert result.completed_at is None
    
    def test_mark_completed(self):
        """Test marking execution as completed."""
        result = HookExecutionResult(
            hook_id="test-hook",
            execution_id="test-exec",
            hook_type="TestHook",
            event_id="test-event",
            status=HookStatus.RUNNING,
            execution_time_ms=100.0
        )
        
        assert result.completed_at is None
        
        result.mark_completed(HookStatus.SUCCESS)
        
        assert result.status == HookStatus.SUCCESS
        assert result.completed_at is not None
    
    def test_add_error(self):
        """Test adding errors to execution result."""
        result = HookExecutionResult(
            hook_id="test-hook",
            execution_id="test-exec",
            hook_type="TestHook",
            event_id="test-event",
            status=HookStatus.RUNNING,
            execution_time_ms=100.0
        )
        
        result.add_error("Test error")
        
        assert "Test error" in result.errors
        assert result.status == HookStatus.FAILED


class TestHookLifecycleManager:
    """Test HookLifecycleManager functionality."""
    
    @pytest.fixture
    def registry_with_hooks(self, sample_configuration):
        """Create a registry with test hooks."""
        registry = HookRegistry()
        
        hook1 = TestAgentHook("hook1", sample_configuration)
        hook2 = TestAgentHook("hook2", sample_configuration)
        
        registry.register_hook(hook1)
        registry.register_hook(hook2)
        
        return registry
    
    async def test_lifecycle_manager_start_stop(self, registry_with_hooks):
        """Test lifecycle manager start and stop."""
        manager = HookLifecycleManager(registry_with_hooks)
        
        assert manager._running is False
        
        await manager.start()
        assert manager._running is True
        
        await manager.stop()
        assert manager._running is False
    
    async def test_execute_hook_success(self, registry_with_hooks, sample_event):
        """Test successful hook execution."""
        manager = HookLifecycleManager(registry_with_hooks)
        hook = registry_with_hooks.get_hook("hook1")
        
        result = await manager.execute_hook(hook, sample_event)
        
        assert result.status == HookStatus.SUCCESS
        assert result.hook_id == "hook1"
        assert result.event_id == sample_event.event_id
        assert hook.execute_called is True
    
    async def test_execute_hook_disabled(self, registry_with_hooks, sample_event):
        """Test executing disabled hook."""
        manager = HookLifecycleManager(registry_with_hooks)
        hook = registry_with_hooks.get_hook("hook1")
        hook.disable()
        
        result = await manager.execute_hook(hook, sample_event)
        
        assert result.status == HookStatus.CANCELLED
        assert "Hook is disabled" in result.errors
        assert hook.execute_called is False
    
    async def test_execute_hook_cannot_handle(self, registry_with_hooks, sample_event):
        """Test executing hook that cannot handle event."""
        manager = HookLifecycleManager(registry_with_hooks)
        hook = registry_with_hooks.get_hook("hook1")
        hook.can_handle_result = False
        
        result = await manager.execute_hook(hook, sample_event)
        
        assert result.status == HookStatus.CANCELLED
        assert "Hook cannot handle this event type" in result.errors
        assert hook.execute_called is False
    
    async def test_execute_hook_timeout(self, registry_with_hooks, sample_event):
        """Test hook execution timeout."""
        manager = HookLifecycleManager(registry_with_hooks)
        hook = registry_with_hooks.get_hook("hook1")
        
        # Make hook execution take longer than timeout
        async def slow_execute(event):
            await asyncio.sleep(1.0)  # Longer than 15ms timeout
            return HookExecutionResult(
                hook_id=hook.hook_id,
                execution_id="test",
                hook_type=hook.hook_type,
                event_id=event.event_id,
                status=HookStatus.SUCCESS,
                execution_time_ms=1000.0
            )
        
        hook.execute = slow_execute
        hook.configuration.timeout_seconds = 0.01  # Very short timeout
        
        result = await manager.execute_hook(hook, sample_event)
        
        assert result.status == HookStatus.FAILED
        assert any("timed out" in error for error in result.errors)
    
    async def test_execute_hook_exception(self, registry_with_hooks, sample_event):
        """Test hook execution with exception."""
        manager = HookLifecycleManager(registry_with_hooks)
        hook = registry_with_hooks.get_hook("hook1")
        hook.execute_exception = ValueError("Test exception")
        
        result = await manager.execute_hook(hook, sample_event)
        
        assert result.status == HookStatus.FAILED
        assert any("Test exception" in error for error in result.errors)
    
    async def test_execute_hooks_for_event(self, registry_with_hooks, sample_event):
        """Test executing multiple hooks for an event."""
        manager = HookLifecycleManager(registry_with_hooks)
        
        results = await manager.execute_hooks_for_event(sample_event)
        
        assert len(results) == 2
        assert all(result.status == HookStatus.SUCCESS for result in results)
        assert {result.hook_id for result in results} == {"hook1", "hook2"}
    
    async def test_execute_hooks_no_applicable_hooks(self, registry_with_hooks, sample_event):
        """Test executing hooks when no hooks can handle the event."""
        manager = HookLifecycleManager(registry_with_hooks)
        
        # Make all hooks unable to handle the event
        for hook in registry_with_hooks.get_all_hooks():
            hook.can_handle_result = False
        
        results = await manager.execute_hooks_for_event(sample_event)
        
        assert len(results) == 0
    
    def test_get_hook_statistics_no_executions(self, registry_with_hooks):
        """Test getting statistics for hook with no executions."""
        manager = HookLifecycleManager(registry_with_hooks)
        
        stats = manager.get_hook_statistics("hook1")
        
        assert stats['total_executions'] == 0
        assert stats['success_rate'] == 0.0
        assert stats['average_execution_time_ms'] == 0.0
        assert stats['last_execution'] is None
    
    def test_get_hook_statistics_with_executions(self, registry_with_hooks):
        """Test getting statistics for hook with executions."""
        manager = HookLifecycleManager(registry_with_hooks)
        
        # Add some mock execution results
        successful_result = HookExecutionResult(
            hook_id="hook1",
            execution_id="exec1",
            hook_type="TestHook",
            event_id="event1",
            status=HookStatus.SUCCESS,
            execution_time_ms=100.0
        )
        
        failed_result = HookExecutionResult(
            hook_id="hook1",
            execution_id="exec2",
            hook_type="TestHook",
            event_id="event2",
            status=HookStatus.FAILED,
            execution_time_ms=200.0,
            errors=["Test error"]
        )
        
        manager._execution_history = [successful_result, failed_result]
        
        stats = manager.get_hook_statistics("hook1")
        
        assert stats['total_executions'] == 2
        assert stats['success_rate'] == 0.5  # 1 success out of 2
        assert stats['average_execution_time_ms'] == 150.0  # (100 + 200) / 2
        assert stats['last_execution'] is not None


class TestHookExecutionContext:
    """Test HookExecutionContext functionality."""
    
    def test_execution_context_initialization(self, sample_configuration, sample_event):
        """Test execution context initialization."""
        hook = TestAgentHook("test-hook", sample_configuration)
        context = HookExecutionContext(hook, sample_event, timeout_seconds=30)
        
        assert context.hook == hook
        assert context.event == sample_event
        assert context.timeout_seconds == 30
        assert context.is_cancelled is False
        assert context.execution_time_ms >= 0
    
    def test_execution_context_cancel(self, sample_configuration, sample_event):
        """Test execution context cancellation."""
        hook = TestAgentHook("test-hook", sample_configuration)
        context = HookExecutionContext(hook, sample_event)
        
        assert context.is_cancelled is False
        
        context.cancel()
        
        assert context.is_cancelled is True