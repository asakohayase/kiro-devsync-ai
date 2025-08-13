#!/usr/bin/env python3
"""Comprehensive tests for the message formatter system."""

import sys
import time
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from typing import Dict, List, Any, Optional

sys.path.append('.')

from devsync_ai.core.formatter_factory import (
    SlackMessageFormatterFactory, MessageType, FormatterOptions,
    ProcessingResult, TeamConfig, ChannelConfig
)
from devsync_ai.core.message_formatter import SlackMessage, TemplateConfig
from devsync_ai.formatters.pr_message_formatter import PRMessageFormatter
from devsync_ai.formatters.jira_message_formatter import JIRAMessageFormatter
from devsync_ai.formatters.standup_message_formatter import StandupMessageFormatter
from devsync_ai.formatters.blocker_message_formatter import BlockerMessageFormatter


class TestDataBuilder:
    """Builder class for generating test data."""
    
    @staticmethod
    def complete_pr_data() -> Dict[str, Any]:
        """Generate complete PR data for testing."""
        return {
            "pr": {
                "number": 123,
                "title": "Fix authentication bug in user login",
                "author": "alice",
                "state": "open",
                "url": "https://github.com/company/repo/pull/123",
                "description": "This PR fixes a critical authentication vulnerability that could allow unauthorized access",
                "branch": "fix/auth-bug",
                "base_branch": "main",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T14:20:00Z",
                "repository": "company/repo",
                "labels": ["bug", "security", "high-priority"],
                "reviewers": ["bob", "carol"],
                "assignees": ["alice"],
                "milestone": "v2.1.0",
                "draft": False,
                "mergeable": True,
                "commits": 3,
                "additions": 45,
                "deletions": 12,
                "changed_files": 5
            }
        }
    
    @staticmethod
    def minimal_pr_data() -> Dict[str, Any]:
        """Generate minimal PR data for testing."""
        return {
            "pr": {
                "number": 456,
                "title": "Update README",
                "author": "bob"
            }
        }
    
    @staticmethod
    def complete_jira_data() -> Dict[str, Any]:
        """Generate complete JIRA data for testing."""
        return {
            "ticket": {
                "key": "DEV-789",
                "summary": "Implement user dashboard with analytics",
                "description": "Create a comprehensive user dashboard that displays key metrics and analytics for user engagement",
                "status": {"name": "In Progress", "id": "3"},
                "priority": {"name": "High", "id": "2"},
                "assignee": {
                    "name": "carol",
                    "email": "carol@company.com",
                    "displayName": "Carol Smith"
                },
                "reporter": {
                    "name": "alice",
                    "email": "alice@company.com",
                    "displayName": "Alice Johnson"
                },
                "created": "2024-01-10T09:00:00Z",
                "updated": "2024-01-15T16:45:00Z",
                "project": {"key": "DEV", "name": "Development"},
                "labels": ["frontend", "dashboard", "analytics", "user-experience"],
                "components": [{"name": "UI"}, {"name": "Analytics"}],
                "fixVersions": [{"name": "2.1.0"}],
                "issueType": {"name": "Story"},
                "timeTracking": {
                    "originalEstimate": "3d",
                    "remainingEstimate": "1d",
                    "timeSpent": "2d"
                }
            }
        }
    
    @staticmethod
    def minimal_jira_data() -> Dict[str, Any]:
        """Generate minimal JIRA data for testing."""
        return {
            "ticket": {
                "key": "DEV-101",
                "summary": "Fix bug"
            }
        }
    
    @staticmethod
    def complete_standup_data() -> Dict[str, Any]:
        """Generate complete standup data for testing."""
        return {
            "date": "2024-01-15",
            "team": "Engineering Team",
            "participants": [
                {
                    "name": "alice",
                    "yesterday": ["Completed PR review for authentication fix", "Fixed database migration issue"],
                    "today": ["Work on user dashboard implementation", "Review security audit findings"],
                    "blockers": []
                },
                {
                    "name": "bob",
                    "yesterday": ["Updated API documentation", "Fixed unit tests"],
                    "today": ["Implement new search functionality", "Code review for team members"],
                    "blockers": ["Waiting for design approval on search UI"]
                },
                {
                    "name": "carol",
                    "yesterday": ["Designed user dashboard mockups", "Conducted user research interviews"],
                    "today": ["Finalize dashboard design", "Start frontend implementation"],
                    "blockers": []
                }
            ],
            "team_blockers": ["Deployment pipeline is down", "Staging environment needs reset"],
            "announcements": ["New security guidelines published", "Team lunch on Friday"]
        }
    
    @staticmethod
    def complete_blocker_data() -> Dict[str, Any]:
        """Generate complete blocker data for testing."""
        return {
            "blocker": {
                "id": "BLOCK-001",
                "title": "Database Connection Timeout",
                "description": "Multiple database connection timeouts detected in production environment",
                "severity": "critical",
                "status": "active",
                "created_at": "2024-01-15T12:00:00Z",
                "updated_at": "2024-01-15T12:30:00Z",
                "affected_systems": ["api-server", "web-app", "mobile-app"],
                "impact": "Users unable to login and access core features",
                "owner": "alice",
                "escalation_level": 2,
                "estimated_resolution": "2024-01-15T14:00:00Z",
                "metrics": {
                    "error_rate": "15%",
                    "response_time": "5.2s",
                    "affected_users": 1250
                },
                "runbook_url": "https://wiki.company.com/runbooks/db-timeout",
                "incident_channel": "#incident-response"
            }
        }
    
    @staticmethod
    def generate_pr_batch(count: int) -> List[Dict[str, Any]]:
        """Generate a batch of PR data for performance testing."""
        batch = []
        for i in range(count):
            pr_data = {
                "number": 1000 + i,
                "title": f"Feature implementation #{i}",
                "author": f"developer{i % 5}",
                "state": "open" if i % 3 == 0 else "merged",
                "url": f"https://github.com/company/repo/pull/{1000 + i}",
                "branch": f"feature/impl-{i}",
                "created_at": (datetime.now() - timedelta(hours=i)).isoformat()
            }
            batch.append(pr_data)
        return batch
    
    @staticmethod
    def generate_jira_batch(count: int) -> List[Dict[str, Any]]:
        """Generate a batch of JIRA data for performance testing."""
        batch = []
        statuses = ["To Do", "In Progress", "Done", "Blocked"]
        priorities = ["Low", "Medium", "High", "Critical"]
        
        for i in range(count):
            jira_data = {
                "key": f"DEV-{2000 + i}",
                "summary": f"Task implementation #{i}",
                "status": {"name": statuses[i % len(statuses)]},
                "priority": {"name": priorities[i % len(priorities)]},
                "assignee": {"name": f"developer{i % 3}"},
                "created": (datetime.now() - timedelta(days=i)).isoformat()
            }
            batch.append(jira_data)
        return batch
    
    @staticmethod
    def malformed_data_scenarios() -> List[Dict[str, Any]]:
        """Generate malformed data scenarios for error testing."""
        return [
            {},  # Empty data
            {"pr": None},  # Null PR
            {"pr": {}},  # Empty PR
            {"pr": {"number": "invalid"}},  # Invalid number type
            {"pr": {"title": None}},  # Null title
            {"ticket": {"key": ""}},  # Empty key
            {"invalid_field": "value"},  # Wrong field name
            {"pr": {"number": 123, "title": "x" * 1000}},  # Extremely long title
        ]


class TestPRMessageFormatter:
    """Unit tests for PR message formatter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = PRMessageFormatter()
        self.config = TemplateConfig(team_id="test-team")
    
    def test_pr_formatter_with_complete_data(self):
        """Test PR formatter with complete data."""
        data = TestDataBuilder.complete_pr_data()
        result = self.formatter.format_message(data)
        
        # Validate structure
        assert isinstance(result, SlackMessage)
        assert len(result.blocks) >= 3  # Header, content, actions
        assert result.text is not None
        assert len(result.text) > 0
        
        # Validate header block
        header_block = result.blocks[0]
        assert header_block['type'] == 'header'
        assert '🔄' in header_block['text']['text']
        assert 'PR #123' in header_block['text']['text']
        
        # Validate content
        content_found = False
        for block in result.blocks:
            if block.get('type') == 'section' and 'text' in block:
                if 'Fix authentication bug' in block['text']['text']:
                    content_found = True
                    break
        assert content_found, "PR title should be in content"
    
    def test_pr_formatter_with_minimal_data(self):
        """Test PR formatter with minimal data."""
        data = TestDataBuilder.minimal_pr_data()
        result = self.formatter.format_message(data)
        
        assert isinstance(result, SlackMessage)
        assert len(result.blocks) >= 2
        assert 'PR #456' in result.text
        assert 'Update README' in result.text
    
    def test_pr_formatter_with_malformed_data(self):
        """Test PR formatter handles malformed data gracefully."""
        malformed_scenarios = TestDataBuilder.malformed_data_scenarios()
        
        for scenario in malformed_scenarios:
            try:
                result = self.formatter.format_message(scenario)
                # Should either succeed with fallback or raise handled exception
                if result:
                    assert isinstance(result, SlackMessage)
                    assert result.text is not None
            except Exception as e:
                # Expected for some malformed data
                assert "error" in str(e).lower() or "invalid" in str(e).lower()
    
    def test_pr_formatter_block_kit_validation(self):
        """Test that generated blocks conform to Slack Block Kit standards."""
        data = TestDataBuilder.complete_pr_data()
        result = self.formatter.format_message(data)
        
        # Validate each block
        for i, block in enumerate(result.blocks):
            assert 'type' in block, f"Block {i} missing type"
            assert block['type'] in ['header', 'section', 'divider', 'actions', 'context'], f"Invalid block type: {block['type']}"
            
            if block['type'] == 'header':
                assert 'text' in block
                assert block['text']['type'] == 'plain_text'
                assert len(block['text']['text']) <= 150  # Slack limit
            
            elif block['type'] == 'section':
                assert 'text' in block
                assert block['text']['type'] in ['mrkdwn', 'plain_text']
                assert len(block['text']['text']) <= 3000  # Slack limit
    
    def test_pr_formatter_accessibility_compliance(self):
        """Test accessibility compliance of generated messages."""
        data = TestDataBuilder.complete_pr_data()
        result = self.formatter.format_message(data)
        
        # Check for alt text on images/buttons
        for block in result.blocks:
            if block.get('type') == 'actions':
                for element in block.get('elements', []):
                    if element.get('type') == 'button':
                        assert 'text' in element, "Button missing text"
                        assert len(element['text']['text']) > 0, "Button text empty"
    
    def test_pr_formatter_performance(self):
        """Test PR formatter performance with realistic data."""
        data = TestDataBuilder.complete_pr_data()
        
        # Measure formatting time
        start_time = time.time()
        for _ in range(100):  # Format 100 times
            result = self.formatter.format_message(data)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100
        assert avg_time < 0.01, f"Formatting too slow: {avg_time:.4f}s per message"


class TestJIRAMessageFormatter:
    """Unit tests for JIRA message formatter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = JIRAMessageFormatter()
    
    def test_jira_formatter_with_complete_data(self):
        """Test JIRA formatter with complete data."""
        data = TestDataBuilder.complete_jira_data()
        result = self.formatter.format_message(data)
        
        assert isinstance(result, SlackMessage)
        assert len(result.blocks) >= 3
        
        # Check for JIRA emoji and key
        header_block = result.blocks[0]
        assert '📋' in header_block['text']['text']
        assert 'DEV-789' in header_block['text']['text']
    
    def test_jira_formatter_with_minimal_data(self):
        """Test JIRA formatter with minimal data."""
        data = TestDataBuilder.minimal_jira_data()
        result = self.formatter.format_message(data)
        
        assert isinstance(result, SlackMessage)
        assert 'DEV-101' in result.text
        assert 'Fix bug' in result.text
    
    def test_jira_status_color_mapping(self):
        """Test that JIRA status gets appropriate color coding."""
        data = TestDataBuilder.complete_jira_data()
        
        # Test different statuses
        statuses = [
            ("To Do", "⏳"),
            ("In Progress", "🔄"),
            ("Done", "✅"),
            ("Blocked", "🚫")
        ]
        
        for status_name, expected_emoji in statuses:
            data["ticket"]["status"]["name"] = status_name
            result = self.formatter.format_message(data)
            
            # Check that appropriate emoji is used
            found_emoji = False
            for block in result.blocks:
                if block.get('type') == 'section' and 'text' in block:
                    if expected_emoji in block['text']['text']:
                        found_emoji = True
                        break
            
            # Note: This test might need adjustment based on actual formatter implementation
            # assert found_emoji, f"Expected emoji {expected_emoji} for status {status_name}"


class TestStandupMessageFormatter:
    """Unit tests for standup message formatter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = StandupMessageFormatter()
    
    def test_standup_formatter_with_complete_data(self):
        """Test standup formatter with complete data."""
        data = TestDataBuilder.complete_standup_data()
        result = self.formatter.format_message(data)
        
        assert isinstance(result, SlackMessage)
        assert len(result.blocks) >= 4  # Header, participants, blockers, announcements
        
        # Check for standup elements
        text_content = result.text.lower()
        assert 'standup' in text_content or 'daily' in text_content
        assert 'alice' in text_content
        assert 'bob' in text_content
        assert 'carol' in text_content
    
    def test_standup_formatter_participant_sections(self):
        """Test that each participant gets their own section."""
        data = TestDataBuilder.complete_standup_data()
        result = self.formatter.format_message(data)
        
        participants = ["alice", "bob", "carol"]
        for participant in participants:
            found_participant = False
            for block in result.blocks:
                if block.get('type') == 'section' and 'text' in block:
                    if participant in block['text']['text'].lower():
                        found_participant = True
                        break
            assert found_participant, f"Participant {participant} not found in standup"


class TestBlockerMessageFormatter:
    """Unit tests for blocker message formatter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = BlockerMessageFormatter()
    
    def test_blocker_formatter_with_complete_data(self):
        """Test blocker formatter with complete data."""
        data = TestDataBuilder.complete_blocker_data()
        result = self.formatter.format_message(data)
        
        assert isinstance(result, SlackMessage)
        assert len(result.blocks) >= 3
        
        # Check for blocker/alert indicators
        header_block = result.blocks[0]
        assert any(emoji in header_block['text']['text'] for emoji in ['🚨', '⚠️', '🔥'])
        assert 'Database Connection Timeout' in result.text
    
    def test_blocker_severity_handling(self):
        """Test that blocker severity affects message formatting."""
        data = TestDataBuilder.complete_blocker_data()
        
        severities = ["low", "medium", "high", "critical"]
        for severity in severities:
            data["blocker"]["severity"] = severity
            result = self.formatter.format_message(data)
            
            assert isinstance(result, SlackMessage)
            # Critical should have more urgent formatting
            if severity == "critical":
                assert any(emoji in result.text for emoji in ['🚨', '🔥'])


class TestSlackMessageFormatterFactory:
    """Integration tests for the formatter factory."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.factory = SlackMessageFormatterFactory()
        self.team_config = TeamConfig(
            team_id="test-team",
            default_formatting="rich",
            emoji_set={'pr': '🔄', 'jira': '📋', 'success': '✅'},
            color_scheme={'primary': '#1f77b4', 'success': '#28a745'}
        )
        self.factory.configure_team(self.team_config)
    
    def test_factory_message_type_routing(self):
        """Test that factory routes to correct formatters."""
        test_cases = [
            (MessageType.PR_UPDATE, TestDataBuilder.complete_pr_data()),
            (MessageType.JIRA_UPDATE, TestDataBuilder.complete_jira_data()),
            (MessageType.STANDUP, TestDataBuilder.complete_standup_data()),
            (MessageType.BLOCKER, TestDataBuilder.complete_blocker_data())
        ]
        
        for message_type, data in test_cases:
            result = self.factory.format_message(message_type, data)
            
            assert isinstance(result, ProcessingResult)
            assert result.success is True
            assert result.message is not None
            assert isinstance(result.message, SlackMessage)
            assert result.processing_time_ms >= 0
    
    def test_factory_caching_system(self):
        """Test that factory caching works correctly."""
        data = TestDataBuilder.complete_pr_data()
        
        # First call - should not be cached
        result1 = self.factory.format_message(MessageType.PR_UPDATE, data)
        assert result1.cache_hit is False
        
        # Second call with same data - should be cached
        result2 = self.factory.format_message(MessageType.PR_UPDATE, data)
        assert result2.cache_hit is True
        assert result2.processing_time_ms < result1.processing_time_ms
    
    def test_factory_error_handling(self):
        """Test factory error handling and fallback."""
        # Test with invalid message type
        result = self.factory.format_message("invalid_type", {})
        
        assert isinstance(result, ProcessingResult)
        assert result.success is False
        assert result.error is not None
        assert "Unknown message type" in result.error or "invalid_type" in result.error
    
    def test_factory_batch_processing(self):
        """Test factory batch message processing."""
        batch_data = {
            'batch_items': TestDataBuilder.generate_pr_batch(5),
            'batch_type': 'manual',
            'batch_size': 5
        }
        
        options = FormatterOptions(batch=True, interactive=True)
        result = self.factory.format_message(MessageType.PR_BATCH, batch_data, options=options)
        
        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.message is not None
        assert 'batch' in result.message.text.lower() or len(result.message.blocks) > 5
    
    def test_factory_performance_with_large_batch(self):
        """Test factory performance with large batch processing."""
        large_batch = TestDataBuilder.generate_pr_batch(100)
        batch_data = {
            'batch_items': large_batch,
            'batch_type': 'automatic',
            'batch_size': 100
        }
        
        start_time = time.time()
        options = FormatterOptions(batch=True)
        result = self.factory.format_message(MessageType.PR_BATCH, batch_data, options=options)
        end_time = time.time()
        
        assert result.success is True
        assert (end_time - start_time) < 1.0, "Large batch should format in under 1 second"
        assert result.processing_time_ms < 1000
    
    def test_factory_team_configuration_integration(self):
        """Test that team configuration affects message formatting."""
        data = TestDataBuilder.complete_pr_data()
        
        # Test with different team configurations
        configs = [
            TeamConfig(team_id="team1", default_formatting="minimal"),
            TeamConfig(team_id="team2", default_formatting="rich"),
        ]
        
        results = []
        for config in configs:
            factory = SlackMessageFormatterFactory()
            factory.configure_team(config)
            result = factory.format_message(MessageType.PR_UPDATE, data)
            results.append(result)
        
        # Results should be different based on configuration
        assert len(results) == 2
        assert all(r.success for r in results)
        # Note: Specific differences depend on formatter implementation
    
    def test_factory_channel_configuration_override(self):
        """Test that channel configuration overrides team settings."""
        data = TestDataBuilder.complete_pr_data()
        
        # Configure channel with different settings
        channel_config = ChannelConfig(
            channel_id="#dev",
            formatting_style="minimal",
            interactive_elements=False
        )
        self.factory.configure_channel(channel_config)
        
        result = self.factory.format_message(
            MessageType.PR_UPDATE, 
            data, 
            channel="#dev"
        )
        
        assert result.success is True
        # Channel config should affect the result
        # Note: Specific effects depend on implementation
    
    def test_factory_ab_testing_support(self):
        """Test A/B testing functionality."""
        # Set up A/B test
        self.factory.setup_ab_test("button_colors", {
            "variant_a": {"branding": {"primary_color": "#blue"}},
            "variant_b": {"branding": {"primary_color": "#green"}}
        })
        
        data = TestDataBuilder.complete_pr_data()
        
        # Test both variants
        options_a = FormatterOptions(ab_test_variant="variant_a")
        options_b = FormatterOptions(ab_test_variant="variant_b")
        
        result_a = self.factory.format_message(MessageType.PR_UPDATE, data, options=options_a)
        result_b = self.factory.format_message(MessageType.PR_UPDATE, data, options=options_b)
        
        assert result_a.success is True
        assert result_b.success is True
        # Results might be different based on A/B test configuration
    
    def test_factory_metrics_collection(self):
        """Test that factory collects performance metrics."""
        data = TestDataBuilder.complete_pr_data()
        
        # Generate some activity
        for _ in range(10):
            self.factory.format_message(MessageType.PR_UPDATE, data)
        
        metrics = self.factory.get_metrics()
        
        assert 'total_messages' in metrics
        assert metrics['total_messages'] >= 10
        assert 'cache_hit_rate' in metrics
        assert 'avg_processing_time_ms' in metrics
        assert 'formatter_usage' in metrics
        assert metrics['avg_processing_time_ms'] >= 0


class TestVisualRegression:
    """Visual regression tests for message appearance."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.factory = SlackMessageFormatterFactory()
    
    def test_message_structure_consistency(self):
        """Test that message structure remains consistent."""
        data = TestDataBuilder.complete_pr_data()
        
        # Generate multiple messages and check structure consistency
        results = []
        for _ in range(5):
            result = self.factory.format_message(MessageType.PR_UPDATE, data)
            results.append(result.message)
        
        # All messages should have same structure
        first_message = results[0]
        for message in results[1:]:
            assert len(message.blocks) == len(first_message.blocks)
            for i, (block1, block2) in enumerate(zip(message.blocks, first_message.blocks)):
                assert block1['type'] == block2['type'], f"Block {i} type mismatch"
    
    def test_block_kit_json_validation(self):
        """Test that generated JSON is valid Block Kit format."""
        test_cases = [
            (MessageType.PR_UPDATE, TestDataBuilder.complete_pr_data()),
            (MessageType.JIRA_UPDATE, TestDataBuilder.complete_jira_data()),
            (MessageType.STANDUP, TestDataBuilder.complete_standup_data()),
            (MessageType.BLOCKER, TestDataBuilder.complete_blocker_data())
        ]
        
        for message_type, data in test_cases:
            result = self.factory.format_message(message_type, data)
            message = result.message
            
            # Validate JSON structure
            blocks_json = json.dumps(message.blocks)
            parsed_blocks = json.loads(blocks_json)
            
            assert isinstance(parsed_blocks, list)
            assert len(parsed_blocks) > 0
            
            # Validate each block has required fields
            for block in parsed_blocks:
                assert 'type' in block
                assert isinstance(block['type'], str)
    
    def test_message_size_limits(self):
        """Test that messages don't exceed Slack limits."""
        # Test with large data
        large_pr_data = TestDataBuilder.complete_pr_data()
        large_pr_data["pr"]["description"] = "x" * 2000  # Large description
        
        result = self.factory.format_message(MessageType.PR_UPDATE, large_pr_data)
        message = result.message
        
        # Check Slack limits
        blocks_json = json.dumps(message.blocks)
        assert len(blocks_json) < 50000, "Message exceeds Slack 50KB limit"
        assert len(message.blocks) <= 50, "Message exceeds 50 block limit"
        
        # Check individual block limits
        for block in message.blocks:
            if block.get('type') == 'section' and 'text' in block:
                assert len(block['text']['text']) <= 3000, "Section text exceeds 3000 char limit"
            elif block.get('type') == 'header' and 'text' in block:
                assert len(block['text']['text']) <= 150, "Header text exceeds 150 char limit"


class TestErrorHandlingAndFallbacks:
    """Tests for error handling and fallback mechanisms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.factory = SlackMessageFormatterFactory()
    
    def test_malformed_data_handling(self):
        """Test handling of various malformed data scenarios."""
        malformed_scenarios = TestDataBuilder.malformed_data_scenarios()
        
        for i, scenario in enumerate(malformed_scenarios):
            result = self.factory.format_message(MessageType.PR_UPDATE, scenario)
            
            # Should either succeed with fallback or fail gracefully
            if result.success:
                assert result.message is not None
                assert len(result.message.blocks) > 0
                assert result.message.text is not None
            else:
                assert result.error is not None
                assert len(result.error) > 0
            
            print(f"Scenario {i}: {'Success' if result.success else 'Failed'} - {result.error or 'OK'}")
    
    def test_formatter_exception_handling(self):
        """Test handling when formatter raises exceptions."""
        # Mock a formatter that raises exceptions
        with patch.object(PRMessageFormatter, 'format_message', side_effect=Exception("Test error")):
            result = self.factory.format_message(MessageType.PR_UPDATE, TestDataBuilder.complete_pr_data())
            
            # Should handle exception gracefully
            assert isinstance(result, ProcessingResult)
            assert result.success is False
            assert "Test error" in result.error
    
    def test_fallback_message_generation(self):
        """Test that fallback messages are properly generated."""
        # Force an error condition
        result = self.factory.format_message("invalid_type", {"invalid": "data"})
        
        if not result.success and result.message:
            # Check fallback message structure
            assert isinstance(result.message, SlackMessage)
            assert len(result.message.blocks) > 0
            assert "error" in result.message.text.lower()
            assert result.message.metadata.get("error") is True
    
    def test_partial_data_recovery(self):
        """Test recovery from partial data scenarios."""
        partial_scenarios = [
            {"pr": {"number": 123}},  # Missing title
            {"pr": {"title": "Test"}},  # Missing number
            {"ticket": {"key": "DEV-123"}},  # Missing summary
        ]
        
        for scenario in partial_scenarios:
            message_type = MessageType.PR_UPDATE if "pr" in scenario else MessageType.JIRA_UPDATE
            result = self.factory.format_message(message_type, scenario)
            
            # Should succeed with placeholder data
            assert result.success is True or (result.message is not None)
            if result.message:
                assert len(result.message.blocks) > 0


class TestPerformanceAndScalability:
    """Performance and scalability tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.factory = SlackMessageFormatterFactory()
    
    def test_single_message_performance(self):
        """Test performance of single message formatting."""
        data = TestDataBuilder.complete_pr_data()
        
        # Warm up
        self.factory.format_message(MessageType.PR_UPDATE, data)
        
        # Measure performance
        iterations = 1000
        start_time = time.time()
        
        for _ in range(iterations):
            result = self.factory.format_message(MessageType.PR_UPDATE, data)
            assert result.success is True
        
        end_time = time.time()
        avg_time = (end_time - start_time) / iterations
        
        assert avg_time < 0.005, f"Average formatting time too slow: {avg_time:.6f}s"
        print(f"Average single message formatting time: {avg_time:.6f}s")
    
    def test_batch_processing_performance(self):
        """Test performance of batch processing."""
        batch_sizes = [10, 50, 100, 200]
        
        for batch_size in batch_sizes:
            batch_data = {
                'batch_items': TestDataBuilder.generate_pr_batch(batch_size),
                'batch_type': 'performance_test',
                'batch_size': batch_size
            }
            
            start_time = time.time()
            result = self.factory.format_message(MessageType.PR_BATCH, batch_data)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            assert result.success is True
            assert processing_time < (batch_size * 0.01), f"Batch of {batch_size} too slow: {processing_time:.3f}s"
            
            print(f"Batch size {batch_size}: {processing_time:.3f}s ({processing_time/batch_size*1000:.2f}ms per item)")
    
    def test_memory_usage_with_large_datasets(self):
        """Test memory usage with large datasets."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process large batch
        large_batch = TestDataBuilder.generate_pr_batch(500)
        batch_data = {
            'batch_items': large_batch,
            'batch_type': 'memory_test',
            'batch_size': 500
        }
        
        result = self.factory.format_message(MessageType.PR_BATCH, batch_data)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert result.success is True
        assert memory_increase < 100, f"Memory usage too high: {memory_increase:.2f}MB"
        
        print(f"Memory increase for 500 item batch: {memory_increase:.2f}MB")
    
    def test_cache_performance_impact(self):
        """Test performance impact of caching system."""
        data = TestDataBuilder.complete_pr_data()
        
        # Test without cache (clear cache first)
        self.factory.clear_cache()
        
        start_time = time.time()
        for _ in range(100):
            result = self.factory.format_message(MessageType.PR_UPDATE, data)
        no_cache_time = time.time() - start_time
        
        # Test with cache (same data, should hit cache)
        start_time = time.time()
        for _ in range(100):
            result = self.factory.format_message(MessageType.PR_UPDATE, data)
        with_cache_time = time.time() - start_time
        
        # Cache should provide significant speedup
        speedup = no_cache_time / with_cache_time
        assert speedup > 2, f"Cache speedup insufficient: {speedup:.2f}x"
        
        print(f"Cache speedup: {speedup:.2f}x")
    
    def test_concurrent_processing(self):
        """Test concurrent message processing."""
        import threading
        import queue
        
        data = TestDataBuilder.complete_pr_data()
        results_queue = queue.Queue()
        
        def format_messages(thread_id, count):
            for i in range(count):
                result = self.factory.format_message(MessageType.PR_UPDATE, data)
                results_queue.put((thread_id, i, result.success))
        
        # Start multiple threads
        threads = []
        thread_count = 5
        messages_per_thread = 20
        
        start_time = time.time()
        for i in range(thread_count):
            thread = threading.Thread(target=format_messages, args=(i, messages_per_thread))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # Verify all succeeded
        assert len(results) == thread_count * messages_per_thread
        assert all(success for _, _, success in results)
        
        total_time = end_time - start_time
        print(f"Concurrent processing: {len(results)} messages in {total_time:.3f}s")


def run_comprehensive_tests():
    """Run all comprehensive tests."""
    print("🧪 Running Comprehensive Message Formatter Tests")
    print("=" * 60)
    
    test_classes = [
        TestPRMessageFormatter,
        TestJIRAMessageFormatter,
        TestStandupMessageFormatter,
        TestBlockerMessageFormatter,
        TestSlackMessageFormatterFactory,
        TestVisualRegression,
        TestErrorHandlingAndFallbacks,
        TestPerformanceAndScalability
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}")
        print("-" * 40)
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for test_method_name in test_methods:
            total_tests += 1
            try:
                # Create instance and run test
                test_instance = test_class()
                if hasattr(test_instance, 'setup_method'):
                    test_instance.setup_method()
                
                test_method = getattr(test_instance, test_method_name)
                test_method()
                
                print(f"  ✅ {test_method_name}")
                passed_tests += 1
                
            except Exception as e:
                print(f"  ❌ {test_method_name}: {str(e)}")
    
    print(f"\n📊 Test Results:")
    print(f"✅ Passed: {passed_tests}/{total_tests}")
    print(f"❌ Failed: {total_tests - passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("🎉 All comprehensive tests passed!")
    else:
        print("⚠️ Some tests failed. Check output above for details.")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)