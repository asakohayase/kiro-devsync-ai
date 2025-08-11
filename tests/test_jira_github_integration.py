"""Tests for GitHub to JIRA integration functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from devsync_ai.services.jira import JiraService, JiraAPIError


class TestJiraGitHubIntegration:
    """Test cases for GitHub to JIRA integration."""

    @pytest.fixture
    def jira_service(self):
        """Create JiraService instance for testing."""
        return JiraService(
            server_url="https://test.atlassian.net", username="test@example.com", token="test_token"
        )

    @pytest.fixture
    def sample_pr_data(self):
        """Sample GitHub PR data for testing."""
        return {
            "number": 123,
            "title": "Fix login bug",
            "body": "This PR fixes the login issue by updating authentication logic.",
            "user": {"login": "johndoe"},
            "html_url": "https://github.com/test/repo/pull/123",
            "state": "open",
            "merged": False,
        }

    @pytest.fixture
    def sample_review_data(self):
        """Sample GitHub PR review data for testing."""
        return {"state": "approved", "body": "Looks good to me!", "user": {"login": "reviewer1"}}

    @pytest.fixture
    def mock_jira_client(self):
        """Mock JIRA client for testing."""
        with patch("devsync_ai.services.jira.JIRA") as mock_jira:
            mock_instance = Mock()
            mock_jira.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_database(self):
        """Mock database connection for testing."""
        mock_db = AsyncMock()
        mock_db.execute_query = AsyncMock()
        return mock_db

    @pytest.mark.asyncio
    async def test_create_ticket_from_pr_success(
        self, jira_service, sample_pr_data, mock_jira_client, mock_database
    ):
        """Test successful creation of JIRA ticket from PR."""
        # Mock JIRA issue creation
        mock_issue = Mock()
        mock_issue.key = "TEST-456"
        mock_jira_client.create_issue.return_value = mock_issue

        # Mock database storage
        mock_database.execute_query.return_value = {"success": True, "data": []}

        with patch("devsync_ai.database.connection.get_database", return_value=mock_database):
            with patch.object(jira_service, "_execute_with_retry") as mock_execute:
                mock_execute.return_value = mock_issue

                ticket_key = await jira_service.create_ticket_from_pr(
                    sample_pr_data, project_key="TEST"
                )

        assert ticket_key == "TEST-456"

        # Verify JIRA client was called with correct data
        mock_execute.assert_called()

        # Verify database storage was called
        mock_database.execute_query.assert_called_once()
        call_args = mock_database.execute_query.call_args
        assert call_args[1]["table"] == "pr_ticket_mappings"
        assert call_args[1]["operation"] == "insert"
        assert call_args[1]["data"]["pr_number"] == 123
        assert call_args[1]["data"]["ticket_key"] == "TEST-456"

    @pytest.mark.asyncio
    async def test_create_ticket_from_pr_jira_error(
        self, jira_service, sample_pr_data, mock_jira_client
    ):
        """Test handling JIRA errors when creating ticket from PR."""
        with patch.object(jira_service, "_execute_with_retry") as mock_execute:
            mock_execute.side_effect = JiraAPIError("JIRA connection failed")

            with pytest.raises(JiraAPIError):
                await jira_service.create_ticket_from_pr(sample_pr_data, project_key="TEST")

    @pytest.mark.asyncio
    async def test_update_ticket_from_pr_status_merged(
        self, jira_service, sample_pr_data, mock_database
    ):
        """Test updating JIRA ticket when PR is merged."""
        # Modify PR data to be merged
        sample_pr_data["merged"] = True

        # Mock database lookup
        mock_database.execute_query.return_value = {
            "success": True,
            "data": [{"ticket_key": "TEST-456"}],
        }

        with patch("devsync_ai.database.connection.get_database", return_value=mock_database):
            with patch.object(jira_service, "_transition_ticket_status") as mock_transition:
                mock_transition.return_value = True

                success = await jira_service.update_ticket_from_pr_status(
                    sample_pr_data, action="closed"
                )

        assert success is True
        mock_transition.assert_called_once_with("TEST-456", "Done")

    @pytest.mark.asyncio
    async def test_update_ticket_from_pr_status_closed_not_merged(
        self, jira_service, sample_pr_data, mock_database
    ):
        """Test updating JIRA ticket when PR is closed without merging."""
        # Mock database lookup
        mock_database.execute_query.return_value = {
            "success": True,
            "data": [{"ticket_key": "TEST-456"}],
        }

        with patch("devsync_ai.database.connection.get_database", return_value=mock_database):
            with patch.object(jira_service, "_transition_ticket_status") as mock_transition:
                mock_transition.return_value = True

                success = await jira_service.update_ticket_from_pr_status(
                    sample_pr_data, action="closed"
                )

        assert success is True
        mock_transition.assert_called_once_with("TEST-456", "Cancelled")

    @pytest.mark.asyncio
    async def test_update_ticket_from_pr_status_reopened(
        self, jira_service, sample_pr_data, mock_database
    ):
        """Test updating JIRA ticket when PR is reopened."""
        # Mock database lookup
        mock_database.execute_query.return_value = {
            "success": True,
            "data": [{"ticket_key": "TEST-456"}],
        }

        with patch("devsync_ai.database.connection.get_database", return_value=mock_database):
            with patch.object(jira_service, "_transition_ticket_status") as mock_transition:
                mock_transition.return_value = True

                success = await jira_service.update_ticket_from_pr_status(
                    sample_pr_data, action="reopened"
                )

        assert success is True
        mock_transition.assert_called_once_with("TEST-456", "In Progress")

    @pytest.mark.asyncio
    async def test_update_ticket_from_pr_status_no_ticket_found(
        self, jira_service, sample_pr_data, mock_database
    ):
        """Test handling case where no JIRA ticket is found for PR."""
        # Mock database lookup - no ticket found
        mock_database.execute_query.return_value = {"success": True, "data": []}

        with patch("devsync_ai.database.connection.get_database", return_value=mock_database):
            success = await jira_service.update_ticket_from_pr_status(
                sample_pr_data, action="closed"
            )

        assert success is False

    @pytest.mark.asyncio
    async def test_update_ticket_from_pr_review_approved(
        self, jira_service, sample_pr_data, sample_review_data, mock_database
    ):
        """Test updating JIRA ticket when PR review is approved."""
        # Mock database lookup
        mock_database.execute_query.return_value = {
            "success": True,
            "data": [{"ticket_key": "TEST-456"}],
        }

        with patch("devsync_ai.database.connection.get_database", return_value=mock_database):
            with patch.object(jira_service, "_add_comment_to_ticket") as mock_comment:
                with patch.object(jira_service, "_transition_ticket_status") as mock_transition:
                    mock_comment.return_value = True
                    mock_transition.return_value = True

                    success = await jira_service.update_ticket_from_pr_review(
                        sample_pr_data, sample_review_data
                    )

        assert success is True
        mock_comment.assert_called_once()
        mock_transition.assert_called_once_with("TEST-456", "Ready for Merge")

    @pytest.mark.asyncio
    async def test_update_ticket_from_pr_review_changes_requested(
        self, jira_service, sample_pr_data, sample_review_data, mock_database
    ):
        """Test updating JIRA ticket when PR review requests changes."""
        # Modify review data to request changes
        sample_review_data["state"] = "changes_requested"
        sample_review_data["body"] = "Please fix the formatting issues."

        # Mock database lookup
        mock_database.execute_query.return_value = {
            "success": True,
            "data": [{"ticket_key": "TEST-456"}],
        }

        with patch("devsync_ai.database.connection.get_database", return_value=mock_database):
            with patch.object(jira_service, "_add_comment_to_ticket") as mock_comment:
                with patch.object(jira_service, "_transition_ticket_status") as mock_transition:
                    mock_comment.return_value = True
                    mock_transition.return_value = True

                    success = await jira_service.update_ticket_from_pr_review(
                        sample_pr_data, sample_review_data
                    )

        assert success is True
        mock_comment.assert_called_once()
        mock_transition.assert_called_once_with("TEST-456", "Changes Requested")

    @pytest.mark.asyncio
    async def test_get_ticket_for_pr_found(self, jira_service, mock_database):
        """Test getting JIRA ticket key for a PR number."""
        # Mock database lookup
        mock_database.execute_query.return_value = {
            "success": True,
            "data": [{"ticket_key": "TEST-456"}],
        }

        with patch("devsync_ai.database.connection.get_database", return_value=mock_database):
            ticket_key = await jira_service._get_ticket_for_pr(123)

        assert ticket_key == "TEST-456"

        # Verify database query
        mock_database.execute_query.assert_called_once_with(
            table="pr_ticket_mappings",
            operation="select",
            filters={"pr_number": 123},
            select_fields="ticket_key",
        )

    @pytest.mark.asyncio
    async def test_get_ticket_for_pr_not_found(self, jira_service, mock_database):
        """Test getting JIRA ticket key when PR mapping doesn't exist."""
        # Mock database lookup - no results
        mock_database.execute_query.return_value = {"success": True, "data": []}

        with patch("devsync_ai.database.connection.get_database", return_value=mock_database):
            ticket_key = await jira_service._get_ticket_for_pr(123)

        assert ticket_key is None

    @pytest.mark.asyncio
    async def test_transition_ticket_status_success(self, jira_service, mock_jira_client):
        """Test successful JIRA ticket status transition."""
        # Mock JIRA issue and transitions
        mock_issue = Mock()
        mock_transitions = [
            {"id": "21", "to": {"name": "Done"}},
            {"id": "31", "to": {"name": "In Progress"}},
        ]

        with patch.object(jira_service, "_execute_with_retry") as mock_execute:
            mock_execute.side_effect = [mock_issue, mock_transitions, None]

            success = await jira_service._transition_ticket_status("TEST-456", "Done")

        assert success is True
        assert mock_execute.call_count == 3

    @pytest.mark.asyncio
    async def test_transition_ticket_status_no_transition_found(
        self, jira_service, mock_jira_client
    ):
        """Test JIRA ticket transition when target status is not available."""
        # Mock JIRA issue and transitions (no matching transition)
        mock_issue = Mock()
        mock_transitions = [{"id": "31", "to": {"name": "In Progress"}}]

        with patch.object(jira_service, "_execute_with_retry") as mock_execute:
            mock_execute.side_effect = [mock_issue, mock_transitions]

            success = await jira_service._transition_ticket_status("TEST-456", "Done")

        assert success is False

    @pytest.mark.asyncio
    async def test_add_comment_to_ticket_success(self, jira_service):
        """Test successfully adding comment to JIRA ticket."""
        with patch.object(jira_service, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = None

            success = await jira_service._add_comment_to_ticket(
                "TEST-456", "GitHub PR Review: Approved"
            )

        assert success is True
        mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pr_ticket_mappings_success(self, jira_service, mock_database):
        """Test getting all PR-ticket mappings."""
        # Mock database response
        mock_database.execute_query.return_value = {
            "success": True,
            "data": [
                {
                    "pr_number": 123,
                    "ticket_key": "TEST-456",
                    "pr_url": "https://github.com/test/repo/pull/123",
                    "created_at": "2024-01-01T10:00:00",
                },
                {
                    "pr_number": 124,
                    "ticket_key": "TEST-457",
                    "pr_url": "https://github.com/test/repo/pull/124",
                    "created_at": "2024-01-01T11:00:00",
                },
            ],
        }

        with patch("devsync_ai.database.connection.get_database", return_value=mock_database):
            mappings = await jira_service.get_pr_ticket_mappings()

        assert len(mappings) == 2
        assert mappings[0]["pr_number"] == 123
        assert mappings[0]["ticket_key"] == "TEST-456"
        assert mappings[1]["pr_number"] == 124
        assert mappings[1]["ticket_key"] == "TEST-457"

    @pytest.mark.asyncio
    async def test_get_pr_ticket_mappings_filtered(self, jira_service, mock_database):
        """Test getting PR-ticket mappings filtered by PR numbers."""
        # Mock database response
        mock_database.execute_query.return_value = {
            "success": True,
            "data": [
                {
                    "pr_number": 123,
                    "ticket_key": "TEST-456",
                    "pr_url": "https://github.com/test/repo/pull/123",
                    "created_at": "2024-01-01T10:00:00",
                },
                {
                    "pr_number": 124,
                    "ticket_key": "TEST-457",
                    "pr_url": "https://github.com/test/repo/pull/124",
                    "created_at": "2024-01-01T11:00:00",
                },
            ],
        }

        with patch("devsync_ai.database.connection.get_database", return_value=mock_database):
            mappings = await jira_service.get_pr_ticket_mappings(pr_numbers=[123])

        assert len(mappings) == 1
        assert mappings[0]["pr_number"] == 123
        assert mappings[0]["ticket_key"] == "TEST-456"

    @pytest.mark.asyncio
    async def test_store_pr_ticket_mapping_success(self, jira_service, mock_database):
        """Test storing PR-ticket mapping in database."""
        mock_database.execute_query.return_value = {"success": True, "data": []}

        with patch("devsync_ai.database.connection.get_database", return_value=mock_database):
            await jira_service._store_pr_ticket_mapping(
                pr_number=123, ticket_key="TEST-456", pr_url="https://github.com/test/repo/pull/123"
            )

        # Verify database insert was called
        mock_database.execute_query.assert_called_once()
        call_args = mock_database.execute_query.call_args
        assert call_args[1]["table"] == "pr_ticket_mappings"
        assert call_args[1]["operation"] == "insert"
        assert call_args[1]["data"]["pr_number"] == 123
        assert call_args[1]["data"]["ticket_key"] == "TEST-456"
        assert call_args[1]["data"]["pr_url"] == "https://github.com/test/repo/pull/123"
