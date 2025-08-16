"""
Tests for JIRA webhook processing system.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from devsync_ai.core.agent_hook_dispatcher import (
    AgentHookDispatcher,
    WebhookSecurityValidator,
    WebhookRateLimiter,
    WebhookValidationResult,
    HookDispatchResult
)
from devsync_ai.core.jira_event_processors import (
    IssueUpdatedProcessor,
    IssueTransitionProcessor,
    IssueAssignedProcessor,
    CommentAddedProcessor,
    EventProcessorRegistry,
    FieldChange,
    ChangeSignificance,
    CommentAnalysis
)
from devsync_ai.core.agent_hooks import (
    HookRegistry,
    ProcessedEvent,
    EnrichedEvent,
    EventCategory,
    UrgencyLevel,
    SignificanceLevel
)
from devsync_ai.core.hook_lifecycle_manager import HookLifecycleManager

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def sample_jira_issue_data():
    """Create sample JIRA issue data."""
    return {
        "key": "TEST-123",
        "fields": {
            "summary": "Test issue summary",
            "description": "Test issue description",
            "status": {"name": "In Progress"},
            "priority": {"name": "High"},
            "issuetype": {"name": "Task"},
            "assignee": {
                "accountId": "user123",
                "displayName": "John Doe",
                "emailAddress": "john@example.com"
            },
            "reporter": {
                "accountId": "user456",
                "displayName": "Jane Smith",
                "emailAddress": "jane@example.com"
            },
            "created": "2024-01-01T10:00:00.000Z",
            "updated": "2024-01-01T12:00:00.000Z",
            "labels": ["backend", "api"],
            "components": [{"name": "API"}],
            "fixVersions": [{"name": "v1.0.0", "releaseDate": "2024-02-01"}]
        }
    }


@pytest.fixture
def sample_webhook_payload(sample_jira_issue_data):
    """Create sample JIRA webhook payload."""
    return {
        "webhookEvent": "jira:issue_updated",
        "issue": sample_jira_issue_data,
        "changelog": {
            "items": [
                {
                    "field": "status",
                    "fromString": "To Do",
                    "toString": "In Progress"
                }
            ]
        },
        "user": {
            "accountId": "user123",
            "displayName": "John Doe"
        }
    }


@pytest.fixture
def processed_event(sample_jira_issue_data):
    """Create a sample processed event."""
    return ProcessedEvent(
        event_id="test-event-123",
        event_type="jira:issue_updated",
        timestamp=datetime.now(timezone.utc),
        jira_event_data=sample_jira_issue_data,
        ticket_key="TEST-123",
        project_key="TEST",
        raw_payload={"webhookEvent": "jira:issue_updated", "issue": sample_jira_issue_data}
    )


class TestWebhookSecurityValidator:
    """Test webhook security validation."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = WebhookSecurityValidator("test-secret")
        assert validator.webhook_secret == "test-secret"
    
    def test_verify_jira_signature_valid(self):
        """Test valid JIRA signature verification."""
        validator = WebhookSecurityValidator("test-secret")
        payload = b'{"test": "data"}'
        
        # Generate expected signature
        import hmac
        import hashlib
        expected_sig = hmac.new(
            "test-secret".encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert validator.verify_jira_signature(payload, expected_sig)
        assert validator.verify_jira_signature(payload, f"sha256={expected_sig}")
    
    def test_verify_jira_signature_invalid(self):
        """Test invalid JIRA signature verification."""
        validator = WebhookSecurityValidator("test-secret")
        payload = b'{"test": "data"}'
        
        assert not validator.verify_jira_signature(payload, "invalid-signature")
    
    def test_verify_jira_signature_no_secret(self):
        """Test signature verification with no secret configured."""
        validator = WebhookSecurityValidator(None)
        payload = b'{"test": "data"}'
        
        # Should return True when no secret is configured
        assert validator.verify_jira_signature(payload, "any-signature")
    
    def test_validate_payload_structure_valid(self, sample_webhook_payload):
        """Test valid payload structure validation."""
        validator = WebhookSecurityValidator()
        result = validator.validate_payload_structure(sample_webhook_payload)
        
        assert result.valid
        assert result.event_type == "jira:issue_updated"
        assert result.payload_size > 0
        assert result.error_message is None
    
    def test_validate_payload_structure_missing_webhook_event(self):
        """Test payload validation with missing webhookEvent."""
        validator = WebhookSecurityValidator()
        payload = {"issue": {"key": "TEST-123"}}
        
        result = validator.validate_payload_structure(payload)
        
        assert not result.valid
        assert "Missing 'webhookEvent' field" in result.error_message
    
    def test_validate_payload_structure_invalid_event_format(self):
        """Test payload validation with invalid event format."""
        validator = WebhookSecurityValidator()
        payload = {"webhookEvent": "invalid-event"}
        
        result = validator.validate_payload_structure(payload)
        
        assert not result.valid
        assert "Invalid webhook event format" in result.error_message
    
    def test_validate_payload_structure_missing_issue_data(self):
        """Test payload validation with missing issue data."""
        validator = WebhookSecurityValidator()
        payload = {"webhookEvent": "jira:issue_updated"}
        
        result = validator.validate_payload_structure(payload)
        
        assert not result.valid
        assert "Missing 'issue' data" in result.error_message


class TestWebhookRateLimiter:
    """Test webhook rate limiting."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = WebhookRateLimiter(max_requests_per_minute=50)
        assert limiter.max_requests_per_minute == 50
        assert len(limiter.request_timestamps) == 0
    
    def test_rate_limiter_allows_requests_under_limit(self):
        """Test that requests under limit are allowed."""
        limiter = WebhookRateLimiter(max_requests_per_minute=10)
        
        # Make 5 requests - should all be allowed
        for i in range(5):
            assert not limiter.is_rate_limited("test-client")
        
        assert len(limiter.request_timestamps) == 5
    
    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = WebhookRateLimiter(max_requests_per_minute=3)
        
        # Make 3 requests - should be allowed
        for i in range(3):
            assert not limiter.is_rate_limited("test-client")
        
        # 4th request should be blocked
        assert limiter.is_rate_limited("test-client")
    
    def test_rate_limiter_cleanup_old_timestamps(self):
        """Test that old timestamps are cleaned up."""
        limiter = WebhookRateLimiter(max_requests_per_minute=10)
        
        # Add old timestamp
        old_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        limiter.request_timestamps.append(old_time)
        
        # Make new request
        assert not limiter.is_rate_limited("test-client")
        
        # Old timestamp should be removed
        assert len(limiter.request_timestamps) == 1
        assert limiter.request_timestamps[0] != old_time


class TestAgentHookDispatcher:
    """Test Agent Hook Dispatcher."""
    
    async def create_dispatcher(self):
        """Create a test dispatcher."""
        hook_registry = HookRegistry()
        lifecycle_manager = HookLifecycleManager(hook_registry)
        await lifecycle_manager.start()
        
        dispatcher = AgentHookDispatcher(
            hook_registry=hook_registry,
            lifecycle_manager=lifecycle_manager,
            webhook_secret="test-secret",
            max_requests_per_minute=100
        )
        
        return dispatcher, lifecycle_manager
    
    async def test_dispatcher_initialization(self):
        """Test dispatcher initialization."""
        dispatcher, lifecycle_manager = await self.create_dispatcher()
        
        try:
            assert dispatcher.hook_registry is not None
            assert dispatcher.lifecycle_manager is not None
            assert dispatcher.security_validator is not None
            assert dispatcher.rate_limiter is not None
        finally:
            await lifecycle_manager.stop()
    
    async def test_dispatch_webhook_event_success(self, sample_webhook_payload):
        """Test successful webhook event dispatch."""
        dispatcher, lifecycle_manager = await self.create_dispatcher()
        
        try:
            result = await dispatcher.dispatch_webhook_event(
                webhook_data=sample_webhook_payload,
                client_ip="127.0.0.1"
            )
            
            assert isinstance(result, HookDispatchResult)
            assert result.event_id is not None
            assert result.processing_time_ms > 0
            assert len(result.errors) == 0
        finally:
            await lifecycle_manager.stop()
    
    async def test_dispatch_webhook_event_invalid_payload(self):
        """Test webhook dispatch with invalid payload."""
        dispatcher, lifecycle_manager = await self.create_dispatcher()
        
        try:
            invalid_payload = {"invalid": "payload"}
            
            # Should raise HTTPException for invalid payload
            with pytest.raises(Exception):  # HTTPException
                await dispatcher.dispatch_webhook_event(
                    webhook_data=invalid_payload,
                    client_ip="127.0.0.1"
                )
        finally:
            await lifecycle_manager.stop()
    
    async def test_dispatch_webhook_event_rate_limited(self, sample_webhook_payload):
        """Test webhook dispatch with rate limiting."""
        dispatcher, lifecycle_manager = await self.create_dispatcher()
        
        try:
            # Set very low rate limit
            dispatcher.rate_limiter.max_requests_per_minute = 1
            
            # First request should succeed
            result1 = await dispatcher.dispatch_webhook_event(
                webhook_data=sample_webhook_payload,
                client_ip="127.0.0.1"
            )
            assert len(result1.errors) == 0
            
            # Second request should be rate limited
            with pytest.raises(Exception):  # Should raise HTTPException
                await dispatcher.dispatch_webhook_event(
                    webhook_data=sample_webhook_payload,
                    client_ip="127.0.0.1"
                )
        finally:
            await lifecycle_manager.stop()
    
    async def test_get_metrics(self, sample_webhook_payload):
        """Test getting dispatcher metrics."""
        dispatcher, lifecycle_manager = await self.create_dispatcher()
        
        try:
            # Process a webhook to generate metrics
            await dispatcher.dispatch_webhook_event(
                webhook_data=sample_webhook_payload,
                client_ip="127.0.0.1"
            )
            
            metrics = dispatcher.get_metrics()
            
            assert metrics['total_webhooks_received'] >= 1
            assert metrics['total_webhooks_processed'] >= 1
            assert 'success_rate' in metrics
            assert 'last_webhook_time' in metrics
        finally:
            await lifecycle_manager.stop()
    
    async def test_health_check(self):
        """Test dispatcher health check."""
        dispatcher, lifecycle_manager = await self.create_dispatcher()
        
        try:
            health = await dispatcher.health_check()
            
            assert 'status' in health
            assert 'timestamp' in health
            assert 'components' in health
            assert 'metrics' in health
        finally:
            await lifecycle_manager.stop()


class TestIssueUpdatedProcessor:
    """Test Issue Updated Processor."""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return IssueUpdatedProcessor()
    
    async def test_can_process_issue_updated(self, processor, processed_event):
        """Test processor can handle issue updated events."""
        processed_event.event_type = "jira:issue_updated"
        assert await processor.can_process(processed_event)
    
    async def test_cannot_process_other_events(self, processor, processed_event):
        """Test processor cannot handle other event types."""
        processed_event.event_type = "jira:issue_created"
        assert not await processor.can_process(processed_event)
    
    async def test_process_event_with_status_change(self, processor, processed_event):
        """Test processing event with status change."""
        # Add changelog to raw payload
        processed_event.raw_payload['changelog'] = {
            'items': [
                {
                    'field': 'status',
                    'fromString': 'To Do',
                    'toString': 'In Progress'
                }
            ]
        }
        
        result = await processor.process_event(processed_event)
        
        assert result['processor_type'] == 'issue_updated'
        assert 'field_changes' in result
        assert 'significance' in result
        assert len(result['field_changes']) == 1
        
        change = result['field_changes'][0]
        assert change.field_name == 'status'
        assert change.old_value == 'To Do'
        assert change.new_value == 'In Progress'
    
    async def test_process_event_blocked_status(self, processor, processed_event):
        """Test processing event with blocked status change."""
        processed_event.raw_payload['changelog'] = {
            'items': [
                {
                    'field': 'status',
                    'fromString': 'In Progress',
                    'toString': 'Blocked'
                }
            ]
        }
        
        result = await processor.process_event(processed_event)
        
        assert result['is_blocked'] is True
        assert result['significance'] == SignificanceLevel.CRITICAL


class TestIssueAssignedProcessor:
    """Test Issue Assigned Processor."""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return IssueAssignedProcessor()
    
    async def test_can_process_assignment_event(self, processor, processed_event):
        """Test processor can handle assignment events."""
        processed_event.event_type = "jira:issue_updated"
        processed_event.raw_payload['changelog'] = {
            'items': [
                {
                    'field': 'assignee',
                    'from': 'user123',
                    'to': 'user456'
                }
            ]
        }
        
        assert await processor.can_process(processed_event)
    
    async def test_cannot_process_non_assignment_event(self, processor, processed_event):
        """Test processor cannot handle non-assignment events."""
        processed_event.event_type = "jira:issue_updated"
        processed_event.raw_payload['changelog'] = {
            'items': [
                {
                    'field': 'status',
                    'fromString': 'To Do',
                    'toString': 'In Progress'
                }
            ]
        }
        
        assert not await processor.can_process(processed_event)
    
    async def test_process_assignment_event(self, processor, processed_event):
        """Test processing assignment event."""
        processed_event.raw_payload['changelog'] = {
            'items': [
                {
                    'field': 'assignee',
                    'from': 'user123',
                    'to': 'user456'
                }
            ]
        }
        
        result = await processor.process_event(processed_event)
        
        assert result['processor_type'] == 'issue_assigned'
        assert 'assignment_info' in result
        assert 'workload_analysis' in result
        assert 'effort_info' in result
        assert 'deadline_info' in result


class TestCommentAddedProcessor:
    """Test Comment Added Processor."""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return CommentAddedProcessor()
    
    async def test_can_process_comment_event(self, processor, processed_event):
        """Test processor can handle comment events."""
        processed_event.event_type = "jira:issue_commented"
        assert await processor.can_process(processed_event)
    
    async def test_cannot_process_other_events(self, processor, processed_event):
        """Test processor cannot handle other event types."""
        processed_event.event_type = "jira:issue_updated"
        assert not await processor.can_process(processed_event)
    
    async def test_process_comment_with_blocker_keywords(self, processor, processed_event):
        """Test processing comment with blocker keywords."""
        processed_event.event_type = "jira:issue_commented"
        processed_event.raw_payload['comment'] = {
            'id': 'comment123',
            'body': 'This issue is blocked by a dependency problem',
            'author': {
                'displayName': 'John Doe',
                'accountId': 'user123'
            },
            'created': '2024-01-01T12:00:00.000Z'
        }
        
        result = await processor.process_event(processed_event)
        
        assert result['processor_type'] == 'comment_added'
        assert result['is_significant'] is True
        
        analysis = result['comment_analysis']
        assert analysis.contains_blocker_keywords is True
        assert analysis.significance == SignificanceLevel.CRITICAL
    
    async def test_process_comment_with_mentions(self, processor, processed_event):
        """Test processing comment with user mentions."""
        processed_event.event_type = "jira:issue_commented"
        processed_event.raw_payload['comment'] = {
            'id': 'comment123',
            'body': 'Hey @john, can you help with this? Also [~user456] should review.',
            'author': {
                'displayName': 'Jane Smith',
                'accountId': 'user789'
            },
            'created': '2024-01-01T12:00:00.000Z'
        }
        
        result = await processor.process_event(processed_event)
        
        analysis = result['comment_analysis']
        assert len(analysis.mentions) == 2
        assert 'john' in analysis.mentions
        assert 'user456' in analysis.mentions
        assert result['is_significant'] is True
    
    async def test_process_comment_with_decision_keywords(self, processor, processed_event):
        """Test processing comment with decision keywords."""
        processed_event.event_type = "jira:issue_commented"
        processed_event.raw_payload['comment'] = {
            'id': 'comment123',
            'body': 'We have decided to go with approach A for this implementation.',
            'author': {
                'displayName': 'Tech Lead',
                'accountId': 'user999'
            },
            'created': '2024-01-01T12:00:00.000Z'
        }
        
        result = await processor.process_event(processed_event)
        
        analysis = result['comment_analysis']
        assert analysis.contains_decision_keywords is True
        assert analysis.significance == SignificanceLevel.MAJOR
        assert result['is_significant'] is True


class TestEventProcessorRegistry:
    """Test Event Processor Registry."""
    
    @pytest.fixture
    def registry(self):
        """Create processor registry."""
        return EventProcessorRegistry()
    
    def test_registry_initialization(self, registry):
        """Test registry initialization with default processors."""
        processors = registry.get_processors()
        
        assert len(processors) == 4  # Default processors
        processor_types = [type(p).__name__ for p in processors]
        assert 'IssueUpdatedProcessor' in processor_types
        assert 'IssueTransitionProcessor' in processor_types
        assert 'IssueAssignedProcessor' in processor_types
        assert 'CommentAddedProcessor' in processor_types
    
    async def test_process_event_multiple_processors(self, registry, processed_event):
        """Test processing event through multiple processors."""
        # Set up event that can be processed by IssueUpdatedProcessor
        processed_event.event_type = "jira:issue_updated"
        processed_event.raw_payload['changelog'] = {
            'items': [
                {
                    'field': 'status',
                    'fromString': 'To Do',
                    'toString': 'In Progress'
                }
            ]
        }
        
        result = await registry.process_event(processed_event)
        
        # Should have data from processors (multiple processors may run)
        assert len(result) > 0
        # Check that at least one processor ran
        assert any(key.endswith('_type') for key in result.keys())
    
    def test_register_custom_processor(self, registry):
        """Test registering custom processor."""
        class CustomProcessor(IssueUpdatedProcessor):
            pass
        
        custom_processor = CustomProcessor()
        initial_count = len(registry.get_processors())
        
        registry.register_processor(custom_processor)
        
        assert len(registry.get_processors()) == initial_count + 1
        assert custom_processor in registry.get_processors()


class TestFieldChange:
    """Test FieldChange data class."""
    
    def test_field_change_creation(self):
        """Test creating FieldChange instance."""
        change = FieldChange(
            field_name="status",
            old_value="To Do",
            new_value="In Progress",
            significance=ChangeSignificance.MAJOR,
            change_type="modified"
        )
        
        assert change.field_name == "status"
        assert change.old_value == "To Do"
        assert change.new_value == "In Progress"
        assert change.significance == ChangeSignificance.MAJOR
        assert change.change_type == "modified"


class TestCommentAnalysis:
    """Test CommentAnalysis data class."""
    
    def test_comment_analysis_creation(self):
        """Test creating CommentAnalysis instance."""
        analysis = CommentAnalysis(
            author="John Doe",
            content_preview="This is a test comment...",
            mentions=["user123", "user456"],
            contains_blocker_keywords=True,
            contains_decision_keywords=False,
            contains_question_keywords=False,
            urgency_indicators=["urgent"],
            significance=SignificanceLevel.CRITICAL
        )
        
        assert analysis.author == "John Doe"
        assert analysis.content_preview == "This is a test comment..."
        assert len(analysis.mentions) == 2
        assert analysis.contains_blocker_keywords is True
        assert analysis.significance == SignificanceLevel.CRITICAL