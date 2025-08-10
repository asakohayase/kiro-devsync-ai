"""Tests for GitHub commit history analysis functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from devsync_ai.services.github import GitHubService, CommitInfo
from devsync_ai.models.core import PRStatus


@pytest.fixture
def github_service():
    """Create a GitHub service instance for testing."""
    with patch("devsync_ai.services.github.settings") as mock_settings:
        mock_settings.github_token = "test_token"
        mock_settings.github_repository = "asakohayase/kiro-devsync-ai"
        return GitHubService()


@pytest.fixture
def mock_commit():
    """Create a mock GitHub commit."""
    commit = Mock()
    commit.sha = "abc123def456"
    commit.commit.message = "feat: add new feature for testing"
    commit.commit.author.name = "Test Author"
    commit.commit.author.date = datetime.now() - timedelta(days=1)
    return commit


class TestCommitMessageParsing:
    """Test commit message parsing functionality."""

    def test_parse_conventional_commit_feat(self, github_service):
        """Test parsing conventional commit with feat type."""
        message = "feat: add user authentication"
        result = github_service._parse_commit_message(message)

        assert result["type"] == "feat"
        assert result["description"] == "add user authentication"
        assert result["breaking_change"] is False
        assert result["pr_number"] is None

    def test_parse_conventional_commit_fix(self, github_service):
        """Test parsing conventional commit with fix type."""
        message = "fix: resolve login issue"
        result = github_service._parse_commit_message(message)

        assert result["type"] == "fix"
        assert result["description"] == "resolve login issue"
        assert result["breaking_change"] is False

    def test_parse_conventional_commit_with_scope(self, github_service):
        """Test parsing conventional commit with scope."""
        message = "feat(auth): add OAuth integration"
        result = github_service._parse_commit_message(message)

        assert result["type"] == "feat"
        assert result["scope"] == "auth"
        assert result["description"] == "add OAuth integration"

    def test_parse_breaking_change_with_exclamation(self, github_service):
        """Test parsing breaking change with exclamation mark."""
        message = "feat!: change API response format"
        result = github_service._parse_commit_message(message)

        assert result["type"] == "feat"
        assert result["breaking_change"] is True
        assert result["description"] == "change API response format"

    def test_parse_breaking_change_with_footer(self, github_service):
        """Test parsing breaking change with BREAKING CHANGE footer."""
        message = "feat: update user model\n\nBREAKING CHANGE: removed deprecated fields"
        result = github_service._parse_commit_message(message)

        assert result["type"] == "feat"
        assert result["breaking_change"] is True

    def test_parse_commit_with_pr_number(self, github_service):
        """Test parsing commit with PR number."""
        message = "feat: add new feature (#123)"
        result = github_service._parse_commit_message(message)

        assert result["type"] == "feat"
        assert result["pr_number"] == 123

    def test_parse_non_conventional_commit_fix_keywords(self, github_service):
        """Test parsing non-conventional commit with fix keywords."""
        message = "Fix bug in user registration"
        result = github_service._parse_commit_message(message)

        assert result["type"] == "fix"
        assert result["description"] == "Fix bug in user registration"

    def test_parse_non_conventional_commit_feature_keywords(self, github_service):
        """Test parsing non-conventional commit with feature keywords."""
        message = "Add new dashboard feature"
        result = github_service._parse_commit_message(message)

        assert result["type"] == "feat"
        assert result["description"] == "Add new dashboard feature"

    def test_parse_non_conventional_commit_docs_keywords(self, github_service):
        """Test parsing non-conventional commit with docs keywords."""
        message = "Update README with installation instructions"
        result = github_service._parse_commit_message(message)

        assert result["type"] == "docs"
        assert result["description"] == "Update README with installation instructions"

    def test_parse_non_conventional_commit_fallback(self, github_service):
        """Test parsing non-conventional commit fallback to chore."""
        message = "Update dependencies"
        result = github_service._parse_commit_message(message)

        assert result["type"] == "chore"
        assert result["description"] == "Update dependencies"


class TestCommitRetrieval:
    """Test commit retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_commits_since_success(self, github_service, mock_commit):
        """Test successful commit retrieval since date."""
        since_date = datetime.now() - timedelta(days=7)

        with patch.object(github_service, "get_repository") as mock_get_repo:
            with patch.object(github_service, "_execute_with_retry") as mock_execute:
                mock_repo = Mock()
                mock_get_repo.return_value = mock_repo
                mock_execute.return_value = [mock_commit]

                commits = await github_service.get_commits_since(
                    "asakohayase/kiro-devsync-ai", since_date
                )

                assert len(commits) == 1
                assert isinstance(commits[0], CommitInfo)
                assert commits[0].sha == "abc123def456"
                assert commits[0].category == "feat"
                assert commits[0].author == "Test Author"

    @pytest.mark.asyncio
    async def test_get_commits_since_with_until_date(self, github_service, mock_commit):
        """Test commit retrieval with both since and until dates."""
        since_date = datetime.now() - timedelta(days=7)
        until_date = datetime.now() - timedelta(days=1)

        with patch.object(github_service, "get_repository") as mock_get_repo:
            with patch.object(github_service, "_execute_with_retry") as mock_execute:
                mock_repo = Mock()
                mock_get_repo.return_value = mock_repo
                mock_execute.return_value = [mock_commit]

                commits = await github_service.get_commits_since(
                    "asakohayase/kiro-devsync-ai", since_date, until_date
                )

                assert len(commits) == 1
                # Verify that both since and until dates were passed
                mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_commits_between_tags_success(self, github_service, mock_commit):
        """Test successful commit retrieval between tags."""
        with patch.object(github_service, "get_repository") as mock_get_repo:
            with patch.object(github_service, "_execute_with_retry") as mock_execute:
                mock_repo = Mock()
                mock_get_repo.return_value = mock_repo

                # Mock tag references
                mock_from_ref = Mock()
                mock_from_ref.object.sha = "from_sha"
                mock_to_ref = Mock()
                mock_to_ref.object.sha = "to_sha"

                # Mock comparison result
                mock_comparison = Mock()
                mock_comparison.commits = [mock_commit]

                mock_execute.side_effect = [mock_from_ref, mock_to_ref, mock_comparison]

                commits = await github_service.get_commits_between_tags(
                    "asakohayase/kiro-devsync-ai", "v1.0.0", "v1.1.0"
                )

                assert len(commits) == 1
                assert commits[0].sha == "abc123def456"

    @pytest.mark.asyncio
    async def test_get_commits_repository_access_denied(self, github_service):
        """Test commit retrieval with repository access denied."""
        since_date = datetime.now() - timedelta(days=7)

        with pytest.raises(Exception) as exc_info:
            await github_service.get_commits_since("other/repo", since_date)

        assert "Access denied" in str(exc_info.value)


class TestChangelogGeneration:
    """Test changelog generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_changelog_data_success(self, github_service):
        """Test successful changelog data generation."""
        since_date = datetime.now() - timedelta(days=7)

        # Mock commits with different types
        mock_commits = [
            CommitInfo(
                sha="abc123",
                message="feat: add login",
                author="Alice",
                date=datetime.now(),
                category="feat",
                description="add login",
            ),
            CommitInfo(
                sha="def456",
                message="fix: resolve bug",
                author="Bob",
                date=datetime.now(),
                category="fix",
                description="resolve bug",
            ),
            CommitInfo(
                sha="ghi789",
                message="docs: update README",
                author="Alice",
                date=datetime.now(),
                category="docs",
                description="update README",
            ),
        ]

        with patch.object(github_service, "get_commits_since") as mock_get_commits:
            mock_get_commits.return_value = mock_commits

            changelog_data = await github_service.generate_changelog_data(
                "asakohayase/kiro-devsync-ai", since_date
            )

            assert changelog_data["repository"] == "asakohayase/kiro-devsync-ai"
            assert changelog_data["total_commits"] == 3
            assert len(changelog_data["categories"]["features"]) == 1
            assert len(changelog_data["categories"]["bug_fixes"]) == 1
            assert len(changelog_data["categories"]["documentation"]) == 1
            assert changelog_data["contributors"]["Alice"] == 2
            assert changelog_data["contributors"]["Bob"] == 1

    @pytest.mark.asyncio
    async def test_generate_changelog_data_with_breaking_changes(self, github_service):
        """Test changelog data generation with breaking changes."""
        since_date = datetime.now() - timedelta(days=7)

        mock_commits = [
            CommitInfo(
                sha="abc123",
                message="feat!: breaking change",
                author="Alice",
                date=datetime.now(),
                category="feat",
                description="breaking change",
                breaking_change=True,
            )
        ]

        with patch.object(github_service, "get_commits_since") as mock_get_commits:
            mock_get_commits.return_value = mock_commits

            changelog_data = await github_service.generate_changelog_data(
                "asakohayase/kiro-devsync-ai", since_date
            )

            assert len(changelog_data["categories"]["breaking_changes"]) == 1
            assert (
                changelog_data["categories"]["breaking_changes"][0]["description"]
                == "breaking change"
            )

    @pytest.mark.asyncio
    async def test_generate_changelog_data_with_pr_numbers(self, github_service):
        """Test changelog data generation with PR numbers."""
        since_date = datetime.now() - timedelta(days=7)

        mock_commits = [
            CommitInfo(
                sha="abc123",
                message="feat: add feature (#123)",
                author="Alice",
                date=datetime.now(),
                category="feat",
                description="add feature",
                pr_number=123,
            ),
            CommitInfo(
                sha="def456",
                message="fix: fix bug (#124)",
                author="Bob",
                date=datetime.now(),
                category="fix",
                description="fix bug",
                pr_number=124,
            ),
        ]

        with patch.object(github_service, "get_commits_since") as mock_get_commits:
            mock_get_commits.return_value = mock_commits

            changelog_data = await github_service.generate_changelog_data(
                "asakohayase/kiro-devsync-ai", since_date
            )

            assert 123 in changelog_data["pull_requests"]
            assert 124 in changelog_data["pull_requests"]
            assert changelog_data["categories"]["features"][0]["pr_number"] == 123
            assert changelog_data["categories"]["bug_fixes"][0]["pr_number"] == 124

    @pytest.mark.asyncio
    async def test_format_changelog_markdown(self, github_service):
        """Test changelog markdown formatting."""
        changelog_data = {
            "repository": "asakohayase/kiro-devsync-ai",
            "period": {"from": "2024-01-01T00:00:00", "to": "2024-01-07T00:00:00"},
            "total_commits": 3,
            "categories": {
                "features": [
                    {
                        "sha": "abc123",
                        "description": "add login",
                        "author": "Alice",
                        "pr_number": 123,
                    }
                ],
                "bug_fixes": [
                    {"sha": "def456", "description": "fix bug", "author": "Bob", "pr_number": None}
                ],
                "documentation": [],
                "performance": [],
                "refactoring": [],
                "testing": [],
                "chores": [],
                "breaking_changes": [],
            },
            "contributors": {"Alice": 2, "Bob": 1},
            "pull_requests": [123],
        }

        markdown = await github_service.format_changelog_markdown(changelog_data)

        assert "# Changelog" in markdown
        assert "asakohayase/kiro-devsync-ai" in markdown
        assert "## ✨ New Features" in markdown
        assert "## 🐛 Bug Fixes" in markdown
        assert "## 👥 Contributors" in markdown
        assert "add login by Alice ([#123])" in markdown
        assert "fix bug by Bob" in markdown
        assert "Alice (2 commits)" in markdown
        assert "Bob (1 commit)" in markdown

    @pytest.mark.asyncio
    async def test_format_changelog_markdown_with_breaking_changes(self, github_service):
        """Test changelog markdown formatting with breaking changes."""
        changelog_data = {
            "repository": "test/repo",
            "period": {"from": "2024-01-01T00:00:00", "to": "2024-01-07T00:00:00"},
            "total_commits": 1,
            "categories": {
                "features": [],
                "bug_fixes": [],
                "documentation": [],
                "performance": [],
                "refactoring": [],
                "testing": [],
                "chores": [],
                "breaking_changes": [
                    {
                        "sha": "abc123",
                        "description": "breaking change",
                        "author": "Alice",
                        "pr_number": 123,
                        "category": "feat",
                    }
                ],
            },
            "contributors": {"Alice": 1},
            "pull_requests": [123],
        }

        markdown = await github_service.format_changelog_markdown(changelog_data)

        assert "## ⚠️ Breaking Changes" in markdown
        assert "**FEAT**: breaking change by Alice ([#123])" in markdown

    @pytest.mark.asyncio
    async def test_format_changelog_markdown_empty_categories(self, github_service):
        """Test changelog markdown formatting with empty categories."""
        changelog_data = {
            "repository": "test/repo",
            "period": {"from": "2024-01-01T00:00:00", "to": "2024-01-07T00:00:00"},
            "total_commits": 0,
            "categories": {
                "features": [],
                "bug_fixes": [],
                "documentation": [],
                "performance": [],
                "refactoring": [],
                "testing": [],
                "chores": [],
                "breaking_changes": [],
            },
            "contributors": {},
            "pull_requests": [],
        }

        markdown = await github_service.format_changelog_markdown(changelog_data)

        assert "# Changelog" in markdown
        assert "**Total Commits:** 0" in markdown
        # Should not contain empty sections
        assert "## ✨ New Features" not in markdown
        assert "## 🐛 Bug Fixes" not in markdown
