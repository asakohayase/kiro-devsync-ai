"""Integration tests for GitHub service pull request tracking."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

# Mock the database connection before importing the service
with patch("devsync_ai.database.connection.create_client"):
    with patch("devsync_ai.database.connection.Client"):
        from devsync_ai.services.github import GitHubService
        from devsync_ai.models.core import PullRequest, PRStatus


@pytest.fixture
def github_service():
    """Create a GitHub service instance for testing."""
    with patch("devsync_ai.services.github.settings") as mock_settings:
        mock_settings.github_token = "test_token"
        return GitHubService()


@pytest.fixture
def mock_database():
    """Create a mock database connection."""
    mock_db = Mock()
    mock_db.execute_query = AsyncMock()
    return mock_db


@pytest.fixture
def sample_pr():
    """Create a sample pull request for testing."""
    return PullRequest(
        id="123",
        repository="owner/test-repo",
        title="Test PR",
        author="test_user",
        status=PRStatus.OPEN,
        merge_conflicts=False,
        created_at=datetime.now() - timedelta(days=2),
        updated_at=datetime.now() - timedelta(hours=1),
        reviewers=["reviewer1"],
        labels=["bug", "enhancement"],
    )


class TestGitHubPRTracking:
    """Test cases for GitHub PR tracking functionality."""

    @pytest.mark.asyncio
    async def test_store_pull_request_success(self, github_service, mock_database, sample_pr):
        """Test successful storage of pull request."""
        mock_database.execute_query.return_value = {
            "success": True,
            "data": [{"id": "123"}],
            "count": 1,
        }

        with patch("devsync_ai.services.github.get_database", return_value=mock_database):
            result = await github_service.store_pull_request(sample_pr)

            assert result is True
            mock_database.execute_query.assert_called()

            # Check that the call was made with correct data structure
            call_args = mock_database.execute_query.call_args
            assert call_args[1]["table"] == "pull_requests"
            assert call_args[1]["operation"] == "update"
            assert call_args[1]["data"]["id"] == "123"
            assert call_args[1]["data"]["repository"] == "owner/test-repo"
            assert call_args[1]["data"]["title"] == "Test PR"

    @pytest.mark.asyncio
    async def test_store_pull_request_insert_on_update_failure(
        self, github_service, mock_database, sample_pr
    ):
        """Test PR storage falls back to insert when update fails."""
        # Mock update returning no rows affected (PR doesn't exist)
        mock_database.execute_query.side_effect = [
            {"success": True, "data": [], "count": 0},  # Update returns 0 rows
            {"success": True, "data": [{"id": "123"}], "count": 1},  # Insert succeeds
        ]

        with patch("devsync_ai.services.github.get_database", return_value=mock_database):
            result = await github_service.store_pull_request(sample_pr)

            assert result is True
            assert mock_database.execute_query.call_count == 2

            # First call should be update
            first_call = mock_database.execute_query.call_args_list[0]
            assert first_call[1]["operation"] == "update"

            # Second call should be insert
            second_call = mock_database.execute_query.call_args_list[1]
            assert second_call[1]["operation"] == "insert"

    @pytest.mark.asyncio
    async def test_store_pull_request_failure(self, github_service, mock_database, sample_pr):
        """Test PR storage failure handling."""
        mock_database.execute_query.return_value = {
            "success": False,
            "error": "Database error",
            "data": None,
            "count": 0,
        }

        with patch("devsync_ai.services.github.get_database", return_value=mock_database):
            result = await github_service.store_pull_request(sample_pr)

            assert result is False

    @pytest.mark.asyncio
    async def test_get_stored_pull_requests_success(self, github_service, mock_database):
        """Test successful retrieval of stored pull requests."""
        mock_database.execute_query.return_value = {
            "success": True,
            "data": [
                {
                    "id": "123",
                    "repository": "owner/test-repo",
                    "title": "Test PR",
                    "author": "test_user",
                    "status": "open",
                    "merge_conflicts": False,
                    "created_at": "2024-01-01T10:00:00",
                    "updated_at": "2024-01-01T11:00:00",
                    "data": {"reviewers": ["reviewer1"], "labels": ["bug"]},
                }
            ],
            "count": 1,
        }

        with patch("devsync_ai.services.github.get_database", return_value=mock_database):
            prs = await github_service.get_stored_pull_requests("owner/test-repo")

            assert len(prs) == 1
            pr = prs[0]
            assert pr.id == "123"
            assert pr.repository == "owner/test-repo"
            assert pr.title == "Test PR"
            assert pr.author == "test_user"
            assert pr.status == PRStatus.OPEN
            assert pr.merge_conflicts is False
            assert pr.reviewers == ["reviewer1"]
            assert pr.labels == ["bug"]

    @pytest.mark.asyncio
    async def test_get_stored_pull_requests_with_status_filter(self, github_service, mock_database):
        """Test retrieval of stored pull requests with status filter."""
        mock_database.execute_query.return_value = {"success": True, "data": [], "count": 0}

        with patch("devsync_ai.services.github.get_database", return_value=mock_database):
            await github_service.get_stored_pull_requests("owner/test-repo", "ready_for_review")

            # Check that status filter was applied
            call_args = mock_database.execute_query.call_args
            assert call_args[1]["filters"]["status"] == "ready_for_review"

    @pytest.mark.asyncio
    async def test_get_stored_pull_requests_database_error(self, github_service, mock_database):
        """Test handling of database errors when retrieving PRs."""
        mock_database.execute_query.return_value = {
            "success": False,
            "error": "Connection failed",
            "data": None,
            "count": 0,
        }

        with patch("devsync_ai.services.github.get_database", return_value=mock_database):
            prs = await github_service.get_stored_pull_requests("owner/test-repo")

            assert prs == []

    @pytest.mark.asyncio
    async def test_sync_pull_requests_success(self, github_service, sample_pr):
        """Test successful PR synchronization."""
        # Mock GitHub API calls
        with patch.object(github_service, "get_open_pull_requests") as mock_get_prs:
            with patch.object(github_service, "store_pull_request") as mock_store:
                with patch.object(github_service, "check_merge_conflicts") as mock_check_conflicts:
                    mock_get_prs.return_value = [sample_pr]
                    mock_store.return_value = True
                    mock_check_conflicts.return_value = False

                    result = await github_service.sync_pull_requests("owner/test-repo")

                    assert result["repository"] == "owner/test-repo"
                    assert result["total_prs"] == 1
                    assert result["stored_successfully"] == 1
                    assert result["storage_failures"] == 0
                    assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_sync_pull_requests_with_conflicts_update(self, github_service, sample_pr):
        """Test PR sync with merge conflicts detection and update."""
        # Set initial PR as having no conflicts
        sample_pr.merge_conflicts = False

        with patch.object(github_service, "get_open_pull_requests") as mock_get_prs:
            with patch.object(github_service, "store_pull_request") as mock_store:
                with patch.object(github_service, "check_merge_conflicts") as mock_check_conflicts:
                    mock_get_prs.return_value = [sample_pr]
                    mock_store.return_value = True
                    mock_check_conflicts.return_value = True  # Conflicts detected

                    result = await github_service.sync_pull_requests("owner/test-repo")

                    assert result["conflict_updates"] == 1
                    # Verify that store_pull_request was called twice (initial + conflict update)
                    assert mock_store.call_count == 2

    @pytest.mark.asyncio
    async def test_sync_pull_requests_storage_failures(self, github_service, sample_pr):
        """Test PR sync with storage failures."""
        with patch.object(github_service, "get_open_pull_requests") as mock_get_prs:
            with patch.object(github_service, "store_pull_request") as mock_store:
                with patch.object(github_service, "check_merge_conflicts") as mock_check_conflicts:
                    mock_get_prs.return_value = [sample_pr]
                    mock_store.return_value = False  # Storage fails
                    mock_check_conflicts.return_value = False

                    result = await github_service.sync_pull_requests("owner/test-repo")

                    assert result["stored_successfully"] == 0
                    assert result["storage_failures"] == 1

    @pytest.mark.asyncio
    async def test_analyze_pr_readiness_comprehensive(self, github_service):
        """Test comprehensive PR readiness analysis."""
        # Create test PRs with different characteristics
        now = datetime.now()
        test_prs = [
            PullRequest(
                id="1",
                repository="owner/test-repo",
                title="Ready PR",
                author="user1",
                status=PRStatus.READY_FOR_REVIEW,
                merge_conflicts=False,
                created_at=now - timedelta(days=1),
                updated_at=now - timedelta(hours=1),
                reviewers=["reviewer1"],
                labels=["feature"],
            ),
            PullRequest(
                id="2",
                repository="owner/test-repo",
                title="Draft PR",
                author="user2",
                status=PRStatus.DRAFT,
                merge_conflicts=False,
                created_at=now - timedelta(days=3),
                updated_at=now - timedelta(days=2),
                reviewers=[],
                labels=["wip"],
            ),
            PullRequest(
                id="3",
                repository="owner/test-repo",
                title="Conflicted PR",
                author="user1",
                status=PRStatus.OPEN,
                merge_conflicts=True,
                created_at=now - timedelta(days=10),
                updated_at=now - timedelta(days=8),
                reviewers=["reviewer2"],
                labels=["bug"],
            ),
        ]

        with patch.object(github_service, "get_stored_pull_requests") as mock_get_stored:
            mock_get_stored.return_value = test_prs

            analysis = await github_service.analyze_pr_readiness("owner/test-repo")

            assert analysis["repository"] == "owner/test-repo"
            assert analysis["total_prs"] == 3
            assert analysis["ready_for_review"] == 1
            assert analysis["draft_prs"] == 1
            assert analysis["conflicted_prs"] == 1
            assert analysis["stale_prs"] == 2  # PRs 2 and 3 are stale (>7 days old or not updated)
            assert analysis["prs_by_author"]["user1"] == 2
            assert analysis["prs_by_author"]["user2"] == 1
            assert analysis["oldest_pr"]["id"] == "3"
            assert analysis["newest_pr"]["id"] == "1"
            assert analysis["average_age_days"] > 0

    @pytest.mark.asyncio
    async def test_analyze_pr_readiness_empty_repository(self, github_service):
        """Test PR readiness analysis for repository with no PRs."""
        with patch.object(github_service, "get_stored_pull_requests") as mock_get_stored:
            mock_get_stored.return_value = []

            analysis = await github_service.analyze_pr_readiness("owner/empty-repo")

            assert analysis["repository"] == "owner/empty-repo"
            assert analysis["total_prs"] == 0
            assert analysis["ready_for_review"] == 0
            assert analysis["draft_prs"] == 0
            assert analysis["conflicted_prs"] == 0
            assert analysis["stale_prs"] == 0
            assert analysis["prs_by_author"] == {}
            assert analysis["average_age_days"] == 0
            assert analysis["oldest_pr"] is None
            assert analysis["newest_pr"] is None

    @pytest.mark.asyncio
    async def test_get_pr_summary_complete_workflow(self, github_service, sample_pr):
        """Test complete PR summary workflow."""
        mock_sync_result = {
            "repository": "owner/test-repo",
            "total_prs": 1,
            "stored_successfully": 1,
            "storage_failures": 0,
            "conflict_updates": 0,
            "timestamp": datetime.now().isoformat(),
        }

        mock_analysis = {
            "repository": "owner/test-repo",
            "total_prs": 1,
            "ready_for_review": 0,
            "draft_prs": 0,
            "conflicted_prs": 0,
            "stale_prs": 0,
            "prs_by_author": {"test_user": 1},
            "average_age_days": 2.0,
        }

        with patch.object(github_service, "sync_pull_requests") as mock_sync:
            with patch.object(github_service, "analyze_pr_readiness") as mock_analyze:
                with patch.object(github_service, "get_stored_pull_requests") as mock_get_stored:
                    mock_sync.return_value = mock_sync_result
                    mock_analyze.return_value = mock_analysis
                    mock_get_stored.return_value = [sample_pr]

                    summary = await github_service.get_pr_summary("owner/test-repo")

                    assert summary["repository"] == "owner/test-repo"
                    assert "sync_info" in summary
                    assert "analysis" in summary
                    assert "pull_requests" in summary
                    assert "generated_at" in summary

                    # Check PR details format
                    pr_details = summary["pull_requests"][0]
                    assert pr_details["id"] == "123"
                    assert pr_details["title"] == "Test PR"
                    assert pr_details["author"] == "test_user"
                    assert pr_details["status"] == "open"
                    assert "age_days" in pr_details

    @pytest.mark.asyncio
    async def test_get_pr_summary_error_handling(self, github_service):
        """Test PR summary error handling."""
        with patch.object(github_service, "sync_pull_requests") as mock_sync:
            mock_sync.side_effect = Exception("Sync failed")

            summary = await github_service.get_pr_summary("owner/test-repo")

            assert summary["repository"] == "owner/test-repo"
            assert "error" in summary
            assert "generated_at" in summary
            assert "Sync failed" in summary["error"]
