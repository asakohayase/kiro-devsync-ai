"""Tests for GitHub service."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from github import GithubException, RateLimitExceededException
from github.PullRequest import PullRequest as GithubPR
from github.Repository import Repository
from github.NamedUser import NamedUser
from github.Label import Label

from devsync_ai.services.github import GitHubService, GitHubAPIError, RateLimitInfo
from devsync_ai.models.core import PullRequest, PRStatus


@pytest.fixture
def github_service():
    """Create a GitHub service instance for testing."""
    with patch("devsync_ai.services.github.settings") as mock_settings:
        mock_settings.github_token = "test_token"
        return GitHubService()


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    return Mock()


@pytest.fixture
def mock_repository():
    """Create a mock GitHub repository."""
    repo = Mock(spec=Repository)
    repo.name = "test-repo"
    repo.full_name = "owner/test-repo"
    return repo


@pytest.fixture
def mock_github_pr():
    """Create a mock GitHub pull request."""
    pr = Mock(spec=GithubPR)
    pr.number = 123
    pr.title = "Test PR"
    pr.state = "open"
    pr.draft = False
    pr.merged = False
    pr.mergeable = True
    pr.mergeable_state = "clean"
    pr.created_at = datetime.now() - timedelta(days=1)
    pr.updated_at = datetime.now()

    # Mock user
    user = Mock(spec=NamedUser)
    user.login = "test_user"
    pr.user = user

    # Mock reviewers and teams
    pr.requested_reviewers = []
    pr.requested_teams = []

    # Mock labels
    pr.labels = []

    return pr


class TestGitHubService:
    """Test cases for GitHubService."""

    def test_init_with_token(self):
        """Test initialization with custom token."""
        service = GitHubService(token="custom_token")
        assert service.token == "custom_token"

    def test_init_with_settings_token(self, github_service):
        """Test initialization with settings token."""
        assert github_service.token == "test_token"

    @patch("devsync_ai.services.github.Github")
    def test_github_client_lazy_initialization(self, mock_github_class, github_service):
        """Test that GitHub client is lazily initialized."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # First access should create the client
        client1 = github_service.github_client
        assert client1 == mock_client
        mock_github_class.assert_called_once_with("test_token")

        # Second access should return the same client
        client2 = github_service.github_client
        assert client2 == mock_client
        assert mock_github_class.call_count == 1

    @pytest.mark.asyncio
    async def test_check_rate_limit_success(self, github_service, mock_github_client):
        """Test successful rate limit check."""
        # Mock rate limit response
        mock_rate_limit = Mock()
        mock_core_limit = Mock()
        mock_core_limit.limit = 5000
        mock_core_limit.remaining = 4500
        mock_core_limit.reset = datetime.now() + timedelta(hours=1)
        mock_rate_limit.core = mock_core_limit

        mock_github_client.get_rate_limit.return_value = mock_rate_limit
        github_service._github_client = mock_github_client

        rate_limit_info = await github_service.check_rate_limit()

        assert rate_limit_info.limit == 5000
        assert rate_limit_info.remaining == 4500
        assert isinstance(rate_limit_info.reset_time, datetime)

    @pytest.mark.asyncio
    async def test_check_rate_limit_error(self, github_service, mock_github_client):
        """Test rate limit check with GitHub API error."""
        mock_github_client.get_rate_limit.side_effect = GithubException(403, "Forbidden")
        github_service._github_client = mock_github_client

        with pytest.raises(GitHubAPIError) as exc_info:
            await github_service.check_rate_limit()

        assert exc_info.value.status_code == 403
        assert "Rate limit check failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_rate_limit_wait(self, github_service):
        """Test rate limit handling when remaining requests are low."""
        # Set up low rate limit
        github_service._rate_limit_info = RateLimitInfo(
            limit=5000,
            remaining=5,  # Low remaining requests
            reset_time=datetime.now() + timedelta(seconds=2),
        )

        with patch("asyncio.sleep") as mock_sleep:
            await github_service._handle_rate_limit()
            mock_sleep.assert_called_once()
            # Should wait approximately 2 seconds
            assert 1 <= mock_sleep.call_args[0][0] <= 3

    @pytest.mark.asyncio
    async def test_handle_rate_limit_no_wait(self, github_service):
        """Test rate limit handling when remaining requests are sufficient."""
        # Set up sufficient rate limit
        github_service._rate_limit_info = RateLimitInfo(
            limit=5000,
            remaining=1000,  # Sufficient remaining requests
            reset_time=datetime.now() + timedelta(hours=1),
        )

        with patch("asyncio.sleep") as mock_sleep:
            await github_service._handle_rate_limit()
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, github_service):
        """Test successful execution with retry mechanism."""
        mock_func = Mock(return_value="success")

        with patch.object(github_service, "check_rate_limit") as mock_check_rate:
            with patch.object(github_service, "_handle_rate_limit") as mock_handle_rate:
                mock_check_rate.return_value = RateLimitInfo(5000, 1000, datetime.now())

                result = await github_service._execute_with_retry(
                    mock_func, "arg1", kwarg1="value1"
                )

                assert result == "success"
                mock_func.assert_called_once_with("arg1", kwarg1="value1")
                mock_check_rate.assert_called_once()
                mock_handle_rate.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_retry_rate_limit_exceeded(self, github_service):
        """Test retry mechanism with rate limit exceeded."""
        mock_func = Mock(side_effect=RateLimitExceededException(403, "Rate limit exceeded"))

        with patch.object(github_service, "check_rate_limit"):
            with patch.object(github_service, "_handle_rate_limit"):
                with patch("asyncio.sleep"):
                    with pytest.raises(GitHubAPIError) as exc_info:
                        await github_service._execute_with_retry(mock_func, max_retries=2)

                    assert exc_info.value.status_code == 403
                    assert "Rate limit exceeded after retries" in str(exc_info.value)
                    assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_retry_github_exception_non_retryable(self, github_service):
        """Test retry mechanism with non-retryable GitHub exception."""
        mock_func = Mock(side_effect=GithubException(404, "Not found"))

        with patch.object(github_service, "check_rate_limit"):
            with patch.object(github_service, "_handle_rate_limit"):
                with pytest.raises(GitHubAPIError) as exc_info:
                    await github_service._execute_with_retry(mock_func)

                assert exc_info.value.status_code == 404
                assert "GitHub API error" in str(exc_info.value)
                mock_func.assert_called_once()  # Should not retry

    @pytest.mark.asyncio
    async def test_execute_with_retry_github_exception_retryable(self, github_service):
        """Test retry mechanism with retryable GitHub exception."""
        mock_func = Mock(side_effect=GithubException(500, "Internal server error"))

        with patch.object(github_service, "check_rate_limit"):
            with patch.object(github_service, "_handle_rate_limit"):
                with patch("asyncio.sleep"):
                    with pytest.raises(GitHubAPIError) as exc_info:
                        await github_service._execute_with_retry(mock_func, max_retries=2)

                    assert exc_info.value.status_code == 500
                    assert "GitHub API error after retries" in str(exc_info.value)
                    assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_get_repository_success(
        self, github_service, mock_github_client, mock_repository
    ):
        """Test successful repository retrieval."""
        mock_github_client.get_repo.return_value = mock_repository
        github_service._github_client = mock_github_client

        with patch.object(github_service, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = mock_repository

            repo = await github_service.get_repository("owner/test-repo")

            assert repo == mock_repository
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_repository_error(self, github_service):
        """Test repository retrieval with error."""
        with patch.object(github_service, "_execute_with_retry") as mock_execute:
            mock_execute.side_effect = GitHubAPIError("Repository not found", status_code=404)

            with pytest.raises(GitHubAPIError) as exc_info:
                await github_service.get_repository("owner/nonexistent-repo")

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_test_authentication_success(self, github_service, mock_github_client):
        """Test successful authentication test."""
        # Mock user
        mock_user = Mock()
        mock_user.login = "test_user"
        mock_user.name = "Test User"
        mock_user.email = "test@example.com"
        mock_user.id = 12345

        # Mock rate limit
        mock_rate_limit = RateLimitInfo(
            limit=5000, remaining=4500, reset_time=datetime.now() + timedelta(hours=1)
        )

        with patch.object(github_service, "_execute_with_retry") as mock_execute:
            with patch.object(github_service, "check_rate_limit") as mock_check_rate:
                mock_execute.return_value = mock_user
                mock_check_rate.return_value = mock_rate_limit

                result = await github_service.test_authentication()

                assert result["authenticated"] is True
                assert result["user"]["login"] == "test_user"
                assert result["user"]["name"] == "Test User"
                assert result["user"]["email"] == "test@example.com"
                assert result["user"]["id"] == 12345
                assert result["rate_limit"]["limit"] == 5000
                assert result["rate_limit"]["remaining"] == 4500

    def test_convert_github_pr_to_model_open(self, github_service, mock_github_pr):
        """Test conversion of open GitHub PR to model."""
        mock_github_pr.state = "open"
        mock_github_pr.draft = False
        mock_github_pr.merged = False

        pr = github_service._convert_github_pr_to_model(mock_github_pr, "owner/test-repo")

        assert pr.id == "123"
        assert pr.repository == "owner/test-repo"
        assert pr.title == "Test PR"
        assert pr.author == "test_user"
        assert pr.status == PRStatus.OPEN
        assert pr.merge_conflicts is False

    def test_convert_github_pr_to_model_draft(self, github_service, mock_github_pr):
        """Test conversion of draft GitHub PR to model."""
        mock_github_pr.state = "open"
        mock_github_pr.draft = True

        pr = github_service._convert_github_pr_to_model(mock_github_pr, "owner/test-repo")

        assert pr.status == PRStatus.DRAFT

    def test_convert_github_pr_to_model_ready_for_review(self, github_service, mock_github_pr):
        """Test conversion of PR ready for review to model."""
        mock_github_pr.state = "open"
        mock_github_pr.draft = False

        # Add requested reviewers
        mock_reviewer = Mock()
        mock_reviewer.login = "reviewer1"
        mock_github_pr.requested_reviewers = [mock_reviewer]

        pr = github_service._convert_github_pr_to_model(mock_github_pr, "owner/test-repo")

        assert pr.status == PRStatus.READY_FOR_REVIEW
        assert "reviewer1" in pr.reviewers

    def test_convert_github_pr_to_model_merged(self, github_service, mock_github_pr):
        """Test conversion of merged GitHub PR to model."""
        mock_github_pr.state = "closed"
        mock_github_pr.merged = True

        pr = github_service._convert_github_pr_to_model(mock_github_pr, "owner/test-repo")

        assert pr.status == PRStatus.MERGED

    def test_convert_github_pr_to_model_closed(self, github_service, mock_github_pr):
        """Test conversion of closed GitHub PR to model."""
        mock_github_pr.state = "closed"
        mock_github_pr.merged = False

        pr = github_service._convert_github_pr_to_model(mock_github_pr, "owner/test-repo")

        assert pr.status == PRStatus.CLOSED

    def test_convert_github_pr_to_model_with_conflicts(self, github_service, mock_github_pr):
        """Test conversion of PR with merge conflicts to model."""
        mock_github_pr.mergeable = False

        pr = github_service._convert_github_pr_to_model(mock_github_pr, "owner/test-repo")

        assert pr.merge_conflicts is True

    def test_convert_github_pr_to_model_with_labels(self, github_service, mock_github_pr):
        """Test conversion of PR with labels to model."""
        mock_label1 = Mock(spec=Label)
        mock_label1.name = "bug"
        mock_label2 = Mock(spec=Label)
        mock_label2.name = "enhancement"
        mock_github_pr.labels = [mock_label1, mock_label2]

        pr = github_service._convert_github_pr_to_model(mock_github_pr, "owner/test-repo")

        assert "bug" in pr.labels
        assert "enhancement" in pr.labels

    @pytest.mark.asyncio
    async def test_get_open_pull_requests_success(
        self, github_service, mock_repository, mock_github_pr
    ):
        """Test successful retrieval of open pull requests."""
        mock_prs = [mock_github_pr]
        mock_repository.get_pulls.return_value = mock_prs

        with patch.object(github_service, "get_repository") as mock_get_repo:
            with patch.object(github_service, "_execute_with_retry") as mock_execute:
                mock_get_repo.return_value = mock_repository
                mock_execute.return_value = mock_prs

                prs = await github_service.get_open_pull_requests("owner/test-repo")

                assert len(prs) == 1
                assert isinstance(prs[0], PullRequest)
                assert prs[0].id == "123"
                assert prs[0].title == "Test PR"

    @pytest.mark.asyncio
    async def test_get_open_pull_requests_empty(self, github_service, mock_repository):
        """Test retrieval of open pull requests when none exist."""
        with patch.object(github_service, "get_repository") as mock_get_repo:
            with patch.object(github_service, "_execute_with_retry") as mock_execute:
                mock_get_repo.return_value = mock_repository
                mock_execute.return_value = []

                prs = await github_service.get_open_pull_requests("owner/test-repo")

                assert len(prs) == 0

    @pytest.mark.asyncio
    async def test_check_merge_conflicts_no_conflicts(
        self, github_service, mock_repository, mock_github_pr
    ):
        """Test checking merge conflicts when there are none."""
        mock_github_pr.mergeable = True
        mock_repository.get_pull.return_value = mock_github_pr

        with patch.object(github_service, "get_repository") as mock_get_repo:
            with patch.object(github_service, "_execute_with_retry") as mock_execute:
                mock_get_repo.return_value = mock_repository
                mock_execute.return_value = mock_github_pr

                has_conflicts = await github_service.check_merge_conflicts("owner/test-repo", 123)

                assert has_conflicts is False

    @pytest.mark.asyncio
    async def test_check_merge_conflicts_with_conflicts(
        self, github_service, mock_repository, mock_github_pr
    ):
        """Test checking merge conflicts when there are conflicts."""
        mock_github_pr.mergeable = False
        mock_repository.get_pull.return_value = mock_github_pr

        with patch.object(github_service, "get_repository") as mock_get_repo:
            with patch.object(github_service, "_execute_with_retry") as mock_execute:
                mock_get_repo.return_value = mock_repository
                mock_execute.return_value = mock_github_pr

                has_conflicts = await github_service.check_merge_conflicts("owner/test-repo", 123)

                assert has_conflicts is True

    @pytest.mark.asyncio
    async def test_check_merge_conflicts_unknown_status(
        self, github_service, mock_repository, mock_github_pr
    ):
        """Test checking merge conflicts when status is unknown."""
        mock_github_pr.mergeable = None
        mock_github_pr.mergeable_state = "unknown"
        mock_repository.get_pull.return_value = mock_github_pr

        with patch.object(github_service, "get_repository") as mock_get_repo:
            with patch.object(github_service, "_execute_with_retry") as mock_execute:
                mock_get_repo.return_value = mock_repository
                mock_execute.return_value = mock_github_pr

                has_conflicts = await github_service.check_merge_conflicts("owner/test-repo", 123)

                # Should return False when status is unknown
                assert has_conflicts is False

    @pytest.mark.asyncio
    async def test_get_pull_request_details_success(
        self, github_service, mock_repository, mock_github_pr
    ):
        """Test successful retrieval of pull request details."""
        mock_repository.get_pull.return_value = mock_github_pr

        with patch.object(github_service, "get_repository") as mock_get_repo:
            with patch.object(github_service, "_execute_with_retry") as mock_execute:
                mock_get_repo.return_value = mock_repository
                mock_execute.return_value = mock_github_pr

                pr = await github_service.get_pull_request_details("owner/test-repo", 123)

                assert pr is not None
                assert isinstance(pr, PullRequest)
                assert pr.id == "123"
                assert pr.title == "Test PR"

    @pytest.mark.asyncio
    async def test_get_pull_request_details_not_found(self, github_service):
        """Test retrieval of pull request details when PR doesn't exist."""
        with patch.object(github_service, "get_repository"):
            with patch.object(github_service, "_execute_with_retry") as mock_execute:
                mock_execute.side_effect = GitHubAPIError("Not found", status_code=404)

                pr = await github_service.get_pull_request_details("owner/test-repo", 999)

                assert pr is None

    @pytest.mark.asyncio
    async def test_close(self, github_service, mock_github_client):
        """Test service cleanup."""
        github_service._github_client = mock_github_client

        await github_service.close()

        assert github_service._github_client is None
