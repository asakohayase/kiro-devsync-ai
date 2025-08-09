"""Basic tests for GitHub service repository restrictions."""

import pytest
from unittest.mock import Mock, patch

from devsync_ai.services.github import GitHubService, GitHubAPIError


@pytest.fixture
def github_service():
    """Create a GitHub service instance for testing."""
    with patch("devsync_ai.services.github.settings") as mock_settings:
        mock_settings.github_token = "test_token"
        mock_settings.github_repository = "asakohayase/kiro-devsync-ai"
        return GitHubService()


class TestGitHubServiceBasic:
    """Basic test cases for GitHubService repository restrictions."""

    def test_init_with_default_repository(self, github_service):
        """Test initialization with default repository setting."""
        assert github_service.allowed_repository == "asakohayase/kiro-devsync-ai"

    def test_init_with_custom_repository(self):
        """Test initialization with custom repository setting."""
        with patch("devsync_ai.services.github.settings") as mock_settings:
            mock_settings.github_token = "test_token"
            mock_settings.github_repository = "default/repo"

            service = GitHubService(allowed_repository="custom/repo")
            assert service.allowed_repository == "custom/repo"

    def test_get_default_repository(self, github_service):
        """Test getting the default repository."""
        assert github_service.get_default_repository() == "asakohayase/kiro-devsync-ai"

    def test_validate_repository_access_allowed(self, github_service):
        """Test repository validation with allowed repository."""
        # Should not raise an exception
        github_service._validate_repository_access("asakohayase/kiro-devsync-ai")

    def test_validate_repository_access_denied(self, github_service):
        """Test repository validation with denied repository."""
        with pytest.raises(GitHubAPIError) as exc_info:
            github_service._validate_repository_access("other/repo")

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value)
        assert "asakohayase/kiro-devsync-ai" in str(exc_info.value)
        assert "other/repo" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_repository_allowed(self, github_service):
        """Test getting repository with allowed repository name."""
        mock_repo = Mock()

        with patch.object(github_service, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = mock_repo

            repo = await github_service.get_repository("asakohayase/kiro-devsync-ai")

            assert repo == mock_repo
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_repository_denied(self, github_service):
        """Test getting repository with denied repository name."""
        with pytest.raises(GitHubAPIError) as exc_info:
            await github_service.get_repository("other/repo")

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_open_pull_requests_allowed(self, github_service):
        """Test getting PRs with allowed repository name."""
        with patch.object(github_service, "get_repository") as mock_get_repo:
            with patch.object(github_service, "_execute_with_retry") as mock_execute:
                mock_repo = Mock()
                mock_get_repo.return_value = mock_repo
                mock_execute.return_value = []

                prs = await github_service.get_open_pull_requests("asakohayase/kiro-devsync-ai")

                assert prs == []
                mock_get_repo.assert_called_once_with("asakohayase/kiro-devsync-ai")

    @pytest.mark.asyncio
    async def test_get_open_pull_requests_denied(self, github_service):
        """Test getting PRs with denied repository name."""
        with pytest.raises(GitHubAPIError) as exc_info:
            await github_service.get_open_pull_requests("other/repo")

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_check_merge_conflicts_allowed(self, github_service):
        """Test checking merge conflicts with allowed repository name."""
        with patch.object(github_service, "get_repository") as mock_get_repo:
            with patch.object(github_service, "_execute_with_retry") as mock_execute:
                mock_repo = Mock()
                mock_pr = Mock()
                mock_pr.mergeable = True
                mock_get_repo.return_value = mock_repo
                mock_execute.return_value = mock_pr

                has_conflicts = await github_service.check_merge_conflicts(
                    "asakohayase/kiro-devsync-ai", 123
                )

                assert has_conflicts is False
                mock_get_repo.assert_called_once_with("asakohayase/kiro-devsync-ai")

    @pytest.mark.asyncio
    async def test_check_merge_conflicts_denied(self, github_service):
        """Test checking merge conflicts with denied repository name."""
        with pytest.raises(GitHubAPIError) as exc_info:
            await github_service.check_merge_conflicts("other/repo", 123)

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_default_pr_summary(self, github_service):
        """Test getting PR summary for default repository."""
        mock_summary = {"repository": "asakohayase/kiro-devsync-ai", "total_prs": 0}

        with patch.object(github_service, "get_pr_summary_with_analysis") as mock_get_summary:
            mock_get_summary.return_value = mock_summary

            summary = await github_service.get_default_pr_summary()

            assert summary == mock_summary
            mock_get_summary.assert_called_once_with("asakohayase/kiro-devsync-ai")
