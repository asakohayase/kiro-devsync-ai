"""
Tests for Changelog Recovery Workflows

Tests cover workflow execution, step coordination, escalation procedures,
and integration with the error handling system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from devsync_ai.core.changelog_recovery_workflows import (
    ChangelogRecoveryWorkflowManager,
    GitHubDataCollectionWorkflow,
    SlackDistributionWorkflow,
    WorkflowStep,
    WorkflowExecution,
    WorkflowStatus,
    EscalationLevel,
    RecoveryWorkflow
)
from devsync_ai.core.changelog_error_handler import (
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    RecoveryResult,
    RecoveryAction
)
from devsync_ai.core.exceptions import DataCollectionError, DistributionError


class TestWorkflowStep:
    """Test workflow step functionality"""
    
    def test_workflow_step_creation(self):
        """Test workflow step creation"""
        async def dummy_action(error_context, execution):
            return RecoveryResult(success=True, action_taken=RecoveryAction.RETRY, message="Success")
        
        step = WorkflowStep(
            step_id="test_step",
            name="Test Step",
            description="A test step",
            action=dummy_action,
            timeout=timedelta(minutes=1),
            retry_count=2,
            required=True,
            dependencies=["dep1", "dep2"]
        )
        
        assert step.step_id == "test_step"
        assert step.name == "Test Step"
        assert step.description == "A test step"
        assert step.timeout == timedelta(minutes=1)
        assert step.retry_count == 2
        assert step.required is True
        assert step.dependencies == ["dep1", "dep2"]


class TestGitHubDataCollectionWorkflow:
    """Test GitHub data collection recovery workflow"""
    
    def test_can_handle_github_errors(self):
        """Test workflow can handle GitHub data collection errors"""
        workflow = GitHubDataCollectionWorkflow()
        
        # Should handle GitHub data collection errors
        github_error = ErrorContext(
            error=DataCollectionError("GitHub API failed"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.HIGH,
            service="github",
            operation="fetch_commits"
        )
        
        assert workflow.can_handle(github_error) is True
        
        # Should not handle other errors
        slack_error = ErrorContext(
            error=DistributionError("Slack failed"),
            category=ErrorCategory.DISTRIBUTION,
            severity=ErrorSeverity.HIGH,
            service="slack",
            operation="send_message"
        )
        
        assert workflow.can_handle(slack_error) is False
    
    @pytest.mark.asyncio
    async def test_build_steps(self):
        """Test workflow step building"""
        workflow = GitHubDataCollectionWorkflow()
        
        error_context = ErrorContext(
            error=DataCollectionError("GitHub API failed"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.HIGH,
            service="github",
            operation="fetch_commits"
        )
        
        steps = await workflow.build_steps(error_context)
        
        assert len(steps) == 5
        assert steps[0].step_id == "check_github_status"
        assert steps[1].step_id == "retry_github_api"
        assert steps[2].step_id == "use_cached_github_data"
        assert steps[3].step_id == "partial_github_collection"
        assert steps[4].step_id == "alternative_github_sources"
        
        # Check dependencies
        assert "check_github_status" in steps[3].dependencies
    
    @pytest.mark.asyncio
    async def test_workflow_execution_success(self):
        """Test successful workflow execution"""
        workflow = GitHubDataCollectionWorkflow()
        
        error_context = ErrorContext(
            error=DataCollectionError("GitHub API failed"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.MEDIUM,
            service="github",
            operation="fetch_commits"
        )
        
        execution = await workflow.execute(error_context)
        
        assert execution.status == WorkflowStatus.SUCCESS
        assert execution.started_at is not None
        assert execution.completed_at is not None
        assert len(execution.completed_steps) > 0
        assert execution.escalation_level == EscalationLevel.NONE
    
    @pytest.mark.asyncio
    async def test_workflow_execution_with_failures(self):
        """Test workflow execution with step failures"""
        workflow = GitHubDataCollectionWorkflow()
        
        # Mock a step to fail
        original_retry = workflow._retry_github_api
        
        async def failing_retry(error_context, execution):
            return RecoveryResult(
                success=False,
                action_taken=RecoveryAction.RETRY,
                message="Retry failed"
            )
        
        workflow._retry_github_api = failing_retry
        
        error_context = ErrorContext(
            error=DataCollectionError("GitHub API failed"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.MEDIUM,
            service="github",
            operation="fetch_commits"
        )
        
        execution = await workflow.execute(error_context)
        
        # Should still succeed due to fallback steps
        assert execution.status in [WorkflowStatus.SUCCESS, WorkflowStatus.FAILED]
        assert "retry_github_api" in execution.failed_steps
        
        # Restore original method
        workflow._retry_github_api = original_retry


class TestSlackDistributionWorkflow:
    """Test Slack distribution recovery workflow"""
    
    def test_can_handle_slack_errors(self):
        """Test workflow can handle Slack distribution errors"""
        workflow = SlackDistributionWorkflow()
        
        # Should handle Slack distribution errors
        slack_error = ErrorContext(
            error=DistributionError("Slack API failed"),
            category=ErrorCategory.DISTRIBUTION,
            severity=ErrorSeverity.HIGH,
            service="slack",
            operation="send_message"
        )
        
        assert workflow.can_handle(slack_error) is True
        
        # Should not handle other errors
        github_error = ErrorContext(
            error=DataCollectionError("GitHub failed"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.HIGH,
            service="github",
            operation="fetch_commits"
        )
        
        assert workflow.can_handle(github_error) is False
    
    @pytest.mark.asyncio
    async def test_build_steps(self):
        """Test Slack workflow step building"""
        workflow = SlackDistributionWorkflow()
        
        error_context = ErrorContext(
            error=DistributionError("Slack API failed"),
            category=ErrorCategory.DISTRIBUTION,
            severity=ErrorSeverity.HIGH,
            service="slack",
            operation="send_message"
        )
        
        steps = await workflow.build_steps(error_context)
        
        assert len(steps) == 4
        assert steps[0].step_id == "retry_slack_delivery"
        assert steps[1].step_id == "alternative_slack_channels"
        assert steps[2].step_id == "email_fallback"
        assert steps[3].step_id == "queue_for_later"
    
    @pytest.mark.asyncio
    async def test_workflow_execution_success(self):
        """Test successful Slack workflow execution"""
        workflow = SlackDistributionWorkflow()
        
        error_context = ErrorContext(
            error=DistributionError("Slack API failed"),
            category=ErrorCategory.DISTRIBUTION,
            severity=ErrorSeverity.MEDIUM,
            service="slack",
            operation="send_message"
        )
        
        execution = await workflow.execute(error_context)
        
        assert execution.status == WorkflowStatus.SUCCESS
        assert execution.started_at is not None
        assert execution.completed_at is not None
        assert len(execution.completed_steps) > 0


class TestWorkflowManager:
    """Test workflow manager functionality"""
    
    def test_workflow_registration(self):
        """Test workflow registration"""
        manager = ChangelogRecoveryWorkflowManager()
        
        # Should have default workflows registered
        assert len(manager.workflows) >= 2
        
        # Register custom workflow
        class CustomWorkflow(RecoveryWorkflow):
            def __init__(self):
                super().__init__("custom", "Custom Workflow", "A custom workflow")
            
            def can_handle(self, error_context):
                return error_context.service == "custom"
            
            async def build_steps(self, error_context):
                return []
        
        custom_workflow = CustomWorkflow()
        manager.register_workflow(custom_workflow)
        
        assert len(manager.workflows) >= 3
        assert custom_workflow in manager.workflows
    
    @pytest.mark.asyncio
    async def test_execute_recovery_github(self):
        """Test recovery execution for GitHub errors"""
        manager = ChangelogRecoveryWorkflowManager()
        
        error_context = ErrorContext(
            error=DataCollectionError("GitHub API failed"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.MEDIUM,
            service="github",
            operation="fetch_commits"
        )
        
        execution = await manager.execute_recovery(error_context)
        
        assert execution is not None
        assert execution.workflow_id == "github_data_collection"
        assert execution.status in [WorkflowStatus.SUCCESS, WorkflowStatus.FAILED]
        
        # Should be stored in executions
        assert len(manager.executions) == 1
    
    @pytest.mark.asyncio
    async def test_execute_recovery_slack(self):
        """Test recovery execution for Slack errors"""
        manager = ChangelogRecoveryWorkflowManager()
        
        error_context = ErrorContext(
            error=DistributionError("Slack API failed"),
            category=ErrorCategory.DISTRIBUTION,
            severity=ErrorSeverity.MEDIUM,
            service="slack",
            operation="send_message"
        )
        
        execution = await manager.execute_recovery(error_context)
        
        assert execution is not None
        assert execution.workflow_id == "slack_distribution"
        assert execution.status in [WorkflowStatus.SUCCESS, WorkflowStatus.FAILED]
    
    @pytest.mark.asyncio
    async def test_execute_recovery_no_suitable_workflow(self):
        """Test recovery execution when no suitable workflow exists"""
        manager = ChangelogRecoveryWorkflowManager()
        
        error_context = ErrorContext(
            error=Exception("Unknown error"),
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            service="unknown",
            operation="unknown_operation"
        )
        
        execution = await manager.execute_recovery(error_context)
        
        assert execution is None
    
    @pytest.mark.asyncio
    async def test_escalation_handling(self):
        """Test escalation handling for critical errors"""
        manager = ChangelogRecoveryWorkflowManager()
        
        # Mock escalation notification
        with patch.object(manager, '_send_escalation_notification') as mock_escalation:
            # Create a workflow that will escalate
            class EscalatingWorkflow(RecoveryWorkflow):
                def __init__(self):
                    super().__init__("escalating", "Escalating Workflow", "Always escalates")
                
                def can_handle(self, error_context):
                    return error_context.service == "escalating"
                
                async def build_steps(self, error_context):
                    # Return steps that will fail
                    async def failing_action(error_context, execution):
                        return RecoveryResult(
                            success=False,
                            action_taken=RecoveryAction.ABORT,
                            message="Step failed"
                        )
                    
                    return [
                        WorkflowStep(
                            step_id="failing_step",
                            name="Failing Step",
                            description="This step always fails",
                            action=failing_action,
                            required=True
                        )
                    ]
            
            manager.register_workflow(EscalatingWorkflow())
            
            error_context = ErrorContext(
                error=Exception("Critical error"),
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                service="escalating",
                operation="critical_operation"
            )
            
            execution = await manager.execute_recovery(error_context)
            
            # Should escalate due to critical severity
            assert execution.status == WorkflowStatus.ESCALATED
            assert execution.escalation_level == EscalationLevel.INCIDENT_RESPONSE
            
            # Should have called escalation notification
            mock_escalation.assert_called_once()
    
    def test_workflow_statistics(self):
        """Test workflow statistics calculation"""
        manager = ChangelogRecoveryWorkflowManager()
        
        # Add some mock executions
        execution1 = WorkflowExecution(
            workflow_id="github_data_collection",
            error_context=ErrorContext(
                error=Exception("Test"),
                category=ErrorCategory.DATA_COLLECTION,
                severity=ErrorSeverity.MEDIUM,
                service="github",
                operation="test"
            ),
            status=WorkflowStatus.SUCCESS
        )
        
        execution2 = WorkflowExecution(
            workflow_id="slack_distribution",
            error_context=ErrorContext(
                error=Exception("Test"),
                category=ErrorCategory.DISTRIBUTION,
                severity=ErrorSeverity.MEDIUM,
                service="slack",
                operation="test"
            ),
            status=WorkflowStatus.FAILED
        )
        
        execution3 = WorkflowExecution(
            workflow_id="github_data_collection",
            error_context=ErrorContext(
                error=Exception("Test"),
                category=ErrorCategory.DATA_COLLECTION,
                severity=ErrorSeverity.CRITICAL,
                service="github",
                operation="test"
            ),
            status=WorkflowStatus.ESCALATED
        )
        
        manager.executions["exec1"] = execution1
        manager.executions["exec2"] = execution2
        manager.executions["exec3"] = execution3
        
        stats = manager.get_workflow_statistics()
        
        assert stats["total_executions"] == 3
        assert stats["status_distribution"]["success"] == 1
        assert stats["status_distribution"]["failed"] == 1
        assert stats["status_distribution"]["escalated"] == 1
        assert stats["workflow_distribution"]["github_data_collection"] == 2
        assert stats["workflow_distribution"]["slack_distribution"] == 1
        assert stats["success_rate"] == 33.33333333333333  # 1/3 * 100
        assert stats["escalation_rate"] == 33.33333333333333  # 1/3 * 100
        assert stats["registered_workflows"] >= 2
    
    def test_get_recent_executions(self):
        """Test getting recent executions"""
        manager = ChangelogRecoveryWorkflowManager()
        
        # Add executions with different timestamps
        now = datetime.utcnow()
        
        execution1 = WorkflowExecution(
            workflow_id="test1",
            error_context=ErrorContext(
                error=Exception("Test"),
                category=ErrorCategory.DATA_COLLECTION,
                severity=ErrorSeverity.MEDIUM,
                service="test",
                operation="test"
            ),
            started_at=now - timedelta(hours=2)
        )
        
        execution2 = WorkflowExecution(
            workflow_id="test2",
            error_context=ErrorContext(
                error=Exception("Test"),
                category=ErrorCategory.DATA_COLLECTION,
                severity=ErrorSeverity.MEDIUM,
                service="test",
                operation="test"
            ),
            started_at=now - timedelta(hours=1)
        )
        
        execution3 = WorkflowExecution(
            workflow_id="test3",
            error_context=ErrorContext(
                error=Exception("Test"),
                category=ErrorCategory.DATA_COLLECTION,
                severity=ErrorSeverity.MEDIUM,
                service="test",
                operation="test"
            ),
            started_at=now - timedelta(minutes=30)
        )
        
        manager.executions["exec1"] = execution1
        manager.executions["exec2"] = execution2
        manager.executions["exec3"] = execution3
        
        # Get recent executions (should be ordered by most recent first)
        recent = manager.get_recent_executions(limit=2)
        
        assert len(recent) == 2
        assert recent[0].workflow_id == "test3"  # Most recent
        assert recent[1].workflow_id == "test2"  # Second most recent
        
        # Get executions within time window
        recent_hour = manager.get_recent_executions(
            time_window=timedelta(hours=1.5)
        )
        
        assert len(recent_hour) == 2  # Should exclude execution1
        assert all(
            exec.started_at >= now - timedelta(hours=1.5)
            for exec in recent_hour
        )


class TestWorkflowStepExecution:
    """Test individual workflow step execution"""
    
    @pytest.mark.asyncio
    async def test_step_execution_success(self):
        """Test successful step execution"""
        async def successful_action(error_context, execution):
            return RecoveryResult(
                success=True,
                action_taken=RecoveryAction.RETRY,
                message="Step succeeded"
            )
        
        step = WorkflowStep(
            step_id="test_step",
            name="Test Step",
            description="A test step",
            action=successful_action
        )
        
        workflow = GitHubDataCollectionWorkflow()
        error_context = ErrorContext(
            error=Exception("Test"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.MEDIUM,
            service="github",
            operation="test"
        )
        execution = WorkflowExecution("test", error_context)
        
        result = await workflow._execute_step(step, error_context, execution)
        
        assert result.success is True
        assert result.action_taken == RecoveryAction.RETRY
        assert result.message == "Step succeeded"
    
    @pytest.mark.asyncio
    async def test_step_execution_with_retries(self):
        """Test step execution with retries"""
        call_count = 0
        
        async def failing_then_succeeding_action(error_context, execution):
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                return RecoveryResult(
                    success=False,
                    action_taken=RecoveryAction.RETRY,
                    message=f"Attempt {call_count} failed"
                )
            else:
                return RecoveryResult(
                    success=True,
                    action_taken=RecoveryAction.RETRY,
                    message="Finally succeeded"
                )
        
        step = WorkflowStep(
            step_id="test_step",
            name="Test Step",
            description="A test step",
            action=failing_then_succeeding_action,
            retry_count=3
        )
        
        workflow = GitHubDataCollectionWorkflow()
        error_context = ErrorContext(
            error=Exception("Test"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.MEDIUM,
            service="github",
            operation="test"
        )
        execution = WorkflowExecution("test", error_context)
        
        result = await workflow._execute_step(step, error_context, execution)
        
        assert result.success is True
        assert call_count == 3
        assert result.message == "Finally succeeded"
    
    @pytest.mark.asyncio
    async def test_step_execution_timeout(self):
        """Test step execution timeout"""
        async def slow_action(error_context, execution):
            await asyncio.sleep(2)  # Longer than timeout
            return RecoveryResult(
                success=True,
                action_taken=RecoveryAction.RETRY,
                message="Should not reach here"
            )
        
        step = WorkflowStep(
            step_id="test_step",
            name="Test Step",
            description="A slow test step",
            action=slow_action,
            timeout=timedelta(seconds=0.1),  # Very short timeout
            retry_count=1
        )
        
        workflow = GitHubDataCollectionWorkflow()
        error_context = ErrorContext(
            error=Exception("Test"),
            category=ErrorCategory.DATA_COLLECTION,
            severity=ErrorSeverity.MEDIUM,
            service="github",
            operation="test"
        )
        execution = WorkflowExecution("test", error_context)
        
        result = await workflow._execute_step(step, error_context, execution)
        
        assert result.success is False
        assert result.action_taken == RecoveryAction.ABORT
        assert "timed out" in result.message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])