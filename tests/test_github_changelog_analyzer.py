"""
Comprehensive tests for GitHubChangelogAnalyzer.

Tests cover data accuracy, edge case handling, ML-based classification,
impact scoring, contributor analysis, and performance regression detection.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass

from devsync_ai.services.github import (
    GitHubChangelogAnalyzer,
    GitHubService,
    CommitInfo,
    DateRange,
    RiskLevel,
    TrendDirection,
    GitHubWeeklyData,
    CategorizedCommits,
    ImpactScore,
    ContributorMetrics,
    ContributorActivity,
    RepositoryHealthMetrics,
    PerformanceMetrics,
    RegressionAlert,
    EnrichedPullRequest,
    PerformanceImpact
)
from devsync_ai.models.core import PullRequest, PRStatus


class TestGitHubChangelogAnalyzer:
    """Test suite for GitHubChangelogAnalyzer."""

    @pytest.fixture
    def mock_github_service(self):
        """Create a mock GitHub service."""
        service = Mock(spec=GitHubService)
        service.get_commits_since = AsyncMock()
        service.get_open_pull_requests = AsyncMock()
        service.get_repository = AsyncMock()
        service._execute_with_retry = AsyncMock()
        return service

    @pytest.fixture
    def analyzer(self, mock_github_service):
        """Create GitHubChangelogAnalyzer instance."""
        return GitHubChangelogAnalyzer(mock_github_service)

    @pytest.fixture
    def sample_commits(self):
        """Sample commits for testing."""
        return [
            CommitInfo(
                sha="abc123",
                message="feat: add new user authentication",
                author="john_doe",
                date=datetime.now() - timedelta(days=1),
                category="feat",
                description="add new user authentication",
                breaking_change=False,
                pr_number=123
            ),
            CommitInfo(
                sha="def456",
                message="fix: resolve login bug",
                author="jane_smith",
                date=datetime.now() - timedelta(days=2),
                category="fix",
                description="resolve login bug",
                breaking_change=False,
                pr_number=124
            ),
            CommitInfo(
                sha="ghi789",
                message="docs: update API documentation",
                author="bob_wilson",
                date=datetime.now() - timedelta(days=3),
                category="docs",
                description="update API documentation",
                breaking_change=False,
                pr_number=None
            ),
            CommitInfo(
                sha="jkl012",
                message="perf: optimize database queries",
                author="alice_brown",
                date=datetime.now() - timedelta(days=4),
                category="perf",
                description="optimize database queries",
                breaking_change=False,
                pr_number=125
            ),
            CommitInfo(
                sha="mno345",
                message="feat!: breaking change in API",
                author="charlie_davis",
                date=datetime.now() - timedelta(days=5),
                category="feat",
                description="breaking change in API",
                breaking_change=True,
                pr_number=126
            )
        ]

    @pytest.fixture
    def sample_prs(self):
        """Sample pull requests for testing."""
        return [
            PullRequest(
                id="123",
                repository="test/repo",
                title="Add user authentication",
                author="john_doe",
                status=PRStatus.READY_FOR_REVIEW,
                merge_conflicts=False,
                created_at=datetime.now() - timedelta(days=2),
                updated_at=datetime.now() - timedelta(days=1),
                reviewers=["jane_smith", "bob_wilson"],
                labels=["feature", "security"]
            ),
            PullRequest(
                id="124",
                repository="test/repo",
                title="Fix login bug",
                author="jane_smith",
                status=PRStatus.MERGED,
                merge_conflicts=False,
                created_at=datetime.now() - timedelta(days=3),
                updated_at=datetime.now() - timedelta(days=2),
                reviewers=["john_doe"],
                labels=["bugfix", "critical"]
            )
        ]

    @pytest.fixture
    def date_range(self):
        """Sample date range for testing."""
        return DateRange(
            start=datetime.now() - timedelta(days=7),
            end=datetime.now()
        )

    @pytest.mark.asyncio
    async def test_analyze_weekly_activity_success(self, analyzer, mock_github_service, 
                                                 sample_commits, sample_prs, date_range):
        """Test successful weekly activity analysis."""
        # Setup mocks
        mock_github_service.get_commits_since.return_value = sample_commits
        mock_github_service.get_open_pull_requests.return_value = sample_prs
        
        # Mock repository and PR details
        mock_repo = Mock()
        mock_github_service.get_repository.return_value = mock_repo
        
        mock_pr = Mock()
        mock_pr.changed_files = 5
        mock_pr.additions = 100
        mock_pr.deletions = 50
        mock_pr.get_files.return_value = [Mock(filename="src/auth.py")]
        mock_github_service._execute_with_retry.return_value = mock_pr
        
        # Execute
        result = await analyzer.analyze_weekly_activity("test/repo", date_range)
        
        # Assertions
        assert isinstance(result, GitHubWeeklyData)
        assert len(result.commits.features) >= 1
        assert len(result.commits.bug_fixes) >= 1
        assert len(result.pull_requests) == 2
        assert result.contributors.total_contributors > 0
        assert result.analysis_metadata["repository"] == "test/repo"
        
        # Verify service calls
        mock_github_service.get_commits_since.assert_called_once_with(
            "test/repo", date_range.start, date_range.end
        )
        mock_github_service.get_open_pull_requests.assert_called_once_with("test/repo")

    @pytest.mark.asyncio
    async def test_categorize_commits_accuracy(self, analyzer, sample_commits):
        """Test commit categorization accuracy (95% target)."""
        result = await analyzer.categorize_commits(sample_commits)
        
        # Verify categorization
        assert isinstance(result, CategorizedCommits)
        assert len(result.features) == 2  # feat commits
        assert len(result.bug_fixes) == 1  # fix commits
        assert len(result.documentation) == 1  # docs commits
        assert len(result.performance) == 1  # perf commits
        assert len(result.breaking_changes) == 1  # breaking change commit
        
        # Verify specific categorizations
        feature_shas = [c.sha for c in result.features]
        assert "abc123" in feature_shas  # feat: add new user authentication
        assert "mno345" in feature_shas  # feat!: breaking change in API
        
        bugfix_shas = [c.sha for c in result.bug_fixes]
        assert "def456" in bugfix_shas  # fix: resolve login bug

    @pytest.mark.asyncio
    async def test_categorize_commits_ml_classification(self, analyzer):
        """Test ML-based commit classification with various patterns."""
        test_commits = [
            CommitInfo("1", "implement new feature for users", "dev1", datetime.now(), 
                      "chore", "implement new feature", False),
            CommitInfo("2", "resolve critical security vulnerability", "dev2", datetime.now(), 
                      "chore", "resolve vulnerability", False),
            CommitInfo("3", "update documentation for API endpoints", "dev3", datetime.now(), 
                      "chore", "update docs", False),
            CommitInfo("4", "optimize performance of search algorithm", "dev4", datetime.now(), 
                      "chore", "optimize performance", False),
        ]
        
        result = await analyzer.categorize_commits(test_commits)
        
        # Verify ML-based reclassification
        assert len(result.features) >= 1  # "implement new feature"
        assert len(result.bug_fixes) >= 1  # "resolve critical security vulnerability"
        assert len(result.documentation) >= 1  # "update documentation"
        assert len(result.performance) >= 1  # "optimize performance"

    @pytest.mark.asyncio
    async def test_calculate_pr_impact_score(self, analyzer, mock_github_service, sample_prs):
        """Test PR impact score calculation."""
        # Setup mocks
        mock_repo = Mock()
        mock_github_service.get_repository.return_value = mock_repo
        
        mock_pr = Mock()
        mock_pr.changed_files = 10
        mock_pr.additions = 200
        mock_pr.deletions = 100
        mock_pr.get_files.return_value = [
            Mock(filename="src/api/auth.py"),
            Mock(filename="tests/test_auth.py"),
            Mock(filename="docs/api.md")
        ]
        mock_github_service._execute_with_retry.return_value = mock_pr
        
        # Execute
        result = await analyzer.calculate_pr_impact_score(sample_prs[0])
        
        # Assertions
        assert isinstance(result, ImpactScore)
        assert result.complexity_score > 0
        assert result.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert len(result.affected_systems) > 0
        assert result.files_changed == 10
        assert result.lines_added == 200
        assert result.lines_deleted == 100

    @pytest.mark.asyncio
    async def test_calculate_pr_impact_score_high_complexity(self, analyzer, mock_github_service, sample_prs):
        """Test PR impact score for high complexity changes."""
        # Setup mocks for high complexity PR
        mock_repo = Mock()
        mock_github_service.get_repository.return_value = mock_repo
        
        mock_pr = Mock()
        mock_pr.changed_files = 50  # High file count
        mock_pr.additions = 2000    # High additions
        mock_pr.deletions = 1000    # High deletions
        mock_pr.get_files.return_value = [Mock(filename=f"src/file_{i}.py") for i in range(50)]
        mock_github_service._execute_with_retry.return_value = mock_pr
        
        # Execute
        result = await analyzer.calculate_pr_impact_score(sample_prs[0])
        
        # Assertions for high complexity
        assert result.complexity_score >= 80  # Should be high complexity
        assert result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    @pytest.mark.asyncio
    async def test_analyze_contributor_activity(self, analyzer):
        """Test contributor activity analysis."""
        contributors = ["john_doe", "jane_smith", "bob_wilson", "alice_brown"]
        
        result = await analyzer.analyze_contributor_activity(contributors)
        
        # Assertions
        assert isinstance(result, ContributorMetrics)
        assert result.total_contributors == 4
        assert len(result.contributors) == 4
        assert len(result.top_contributors) > 0
        
        # Verify contributor details
        for contributor in result.contributors:
            assert isinstance(contributor, ContributorActivity)
            assert contributor.username in contributors
            assert contributor.productivity_score >= 0
            assert contributor.collaboration_score >= 0

    @pytest.mark.asyncio
    async def test_detect_performance_regressions(self, analyzer, sample_commits):
        """Test performance regression detection."""
        # Add performance-related commits
        perf_commits = sample_commits + [
            CommitInfo(
                sha="perf123",
                message="slow database query optimization",
                author="dev1",
                date=datetime.now(),
                category="perf",
                description="slow database query optimization",
                breaking_change=False
            ),
            CommitInfo(
                sha="mem456",
                message="fix memory leak in cache",
                author="dev2",
                date=datetime.now(),
                category="fix",
                description="fix memory leak in cache",
                breaking_change=False
            )
        ]
        
        result = await analyzer.detect_performance_regressions(perf_commits)
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) > 0  # Should detect some regressions
        
        for alert in result:
            assert isinstance(alert, RegressionAlert)
            assert alert.commit_sha in [c.sha for c in perf_commits]
            assert alert.confidence_score > 0
            assert alert.severity in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]

    @pytest.mark.asyncio
    async def test_analyze_weekly_activity_error_handling(self, analyzer, mock_github_service, date_range):
        """Test error handling in weekly activity analysis."""
        # Setup mock to raise exception
        mock_github_service.get_commits_since.side_effect = Exception("API Error")
        
        # Execute and verify exception
        with pytest.raises(Exception):
            await analyzer.analyze_weekly_activity("test/repo", date_range)

    @pytest.mark.asyncio
    async def test_calculate_pr_impact_score_error_handling(self, analyzer, mock_github_service, sample_prs):
        """Test error handling in PR impact score calculation."""
        # Setup mock to raise exception
        mock_github_service.get_repository.side_effect = Exception("API Error")
        
        # Execute - should return default impact score instead of raising
        result = await analyzer.calculate_pr_impact_score(sample_prs[0])
        
        # Should return default values
        assert isinstance(result, ImpactScore)
        assert result.complexity_score == 50.0
        assert result.risk_level == RiskLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_repository_health_metrics(self, analyzer, sample_commits, sample_prs):
        """Test repository health metrics calculation."""
        # Use private method directly for testing
        result = await analyzer._analyze_repository_health("test/repo", sample_commits, sample_prs)
        
        # Assertions
        assert isinstance(result, RepositoryHealthMetrics)
        assert 0 <= result.code_quality_score <= 100
        assert 0 <= result.technical_debt_score <= 100
        assert result.test_coverage_trend in [TrendDirection.IMPROVING, TrendDirection.STABLE, TrendDirection.DECLINING]
        assert result.bug_density >= 0
        assert isinstance(result.recommendations, list)

    @pytest.mark.asyncio
    async def test_performance_metrics_analysis(self, analyzer, sample_commits):
        """Test performance metrics analysis."""
        # Use private method directly for testing
        result = await analyzer._analyze_performance_metrics("test/repo", sample_commits)
        
        # Assertions
        assert isinstance(result, PerformanceMetrics)
        assert result.build_time_trend in [TrendDirection.IMPROVING, TrendDirection.STABLE, TrendDirection.DECLINING]
        assert result.test_execution_time > 0
        assert result.deployment_frequency >= 0
        assert isinstance(result.lead_time, timedelta)
        assert isinstance(result.recovery_time, timedelta)
        assert 0 <= result.change_failure_rate <= 1

    @pytest.mark.asyncio
    async def test_ml_commit_classification_accuracy(self, analyzer):
        """Test ML-based commit classification accuracy."""
        # Test various commit message patterns
        test_cases = [
            ("feat: add new login system", "feat"),
            ("fix: resolve authentication bug", "fix"),
            ("docs: update README file", "docs"),
            ("perf: optimize database queries", "perf"),
            ("refactor: cleanup user service", "refactor"),
            ("test: add unit tests for auth", "test"),
            ("style: format code with prettier", "style"),
            ("chore: update dependencies", "chore"),
        ]
        
        for message, expected_category in test_cases:
            commit = CommitInfo("test", message, "dev", datetime.now(), "unknown", message, False)
            result = await analyzer._classify_commit_with_ml(commit)
            assert result == expected_category, f"Failed to classify '{message}' as '{expected_category}', got '{result}'"

    @pytest.mark.asyncio
    async def test_affected_systems_identification(self, analyzer):
        """Test identification of affected systems from file changes."""
        # Mock PR with various file types
        mock_pr = Mock()
        mock_files = [
            Mock(filename="src/api/auth.py"),
            Mock(filename="frontend/components/Login.tsx"),
            Mock(filename="database/migrations/001_users.sql"),
            Mock(filename="tests/test_auth.py"),
            Mock(filename="src/core/utils.py")
        ]
        mock_pr.get_files.return_value = mock_files
        
        result = await analyzer._identify_affected_systems(mock_pr)
        
        # Should identify multiple systems
        assert "api" in result
        assert "frontend" in result
        assert "database" in result
        assert "testing" in result
        assert "core" in result

    @pytest.mark.asyncio
    async def test_test_coverage_impact_calculation(self, analyzer):
        """Test test coverage impact calculation."""
        # Mock PR with test files
        mock_pr = Mock()
        mock_pr.changed_files = 10
        mock_files = [
            Mock(filename="src/auth.py"),
            Mock(filename="tests/test_auth.py"),
            Mock(filename="tests/integration/test_login.py"),
            Mock(filename="src/utils.py")
        ]
        mock_pr.get_files.return_value = mock_files
        
        result = await analyzer._calculate_test_coverage_impact(mock_pr)
        
        # Should calculate percentage of test files
        assert result == 20.0  # 2 test files out of 10 total = 20%

    @pytest.mark.asyncio
    async def test_performance_impact_detection(self, analyzer):
        """Test performance impact detection in PRs."""
        # Mock PR with performance-related files
        mock_pr = Mock()
        mock_files = [
            Mock(filename="src/performance/optimizer.py"),
            Mock(filename="benchmarks/query_benchmark.py"),
            Mock(filename="src/cache/optimization.py")
        ]
        mock_pr.get_files.return_value = mock_files
        
        result = await analyzer._detect_pr_performance_impact(mock_pr)
        
        # Should detect performance impact
        assert result is not None
        assert isinstance(result, PerformanceImpact)
        assert len(result.affected_metrics) > 0
        assert result.confidence_score > 0

    @pytest.mark.asyncio
    async def test_large_repository_performance(self, analyzer, mock_github_service, date_range):
        """Test performance with large repository (1000+ commits)."""
        # Create large number of commits
        large_commit_list = []
        for i in range(1000):
            commit = CommitInfo(
                sha=f"commit_{i}",
                message=f"feat: feature {i}",
                author=f"dev_{i % 10}",  # 10 different developers
                date=datetime.now() - timedelta(days=i % 7),
                category="feat",
                description=f"feature {i}",
                breaking_change=False
            )
            large_commit_list.append(commit)
        
        # Setup mocks
        mock_github_service.get_commits_since.return_value = large_commit_list
        mock_github_service.get_open_pull_requests.return_value = []
        
        # Measure execution time
        start_time = datetime.now()
        result = await analyzer.analyze_weekly_activity("test/repo", date_range)
        execution_time = datetime.now() - start_time
        
        # Should complete within 3 minutes (requirement)
        assert execution_time.total_seconds() < 180  # 3 minutes
        assert isinstance(result, GitHubWeeklyData)
        assert len(result.commits.features) == 1000

    @pytest.mark.asyncio
    async def test_contributor_expertise_identification(self, analyzer):
        """Test contributor expertise area identification."""
        contributor = "test_dev"
        
        result = await analyzer._analyze_individual_contributor(contributor)
        
        # Assertions
        assert isinstance(result, ContributorActivity)
        assert result.username == contributor
        assert isinstance(result.expertise_areas, list)
        assert result.productivity_score >= 0
        assert result.collaboration_score >= 0

    @pytest.mark.asyncio
    async def test_breaking_change_detection(self, analyzer):
        """Test detection of breaking changes in commits."""
        breaking_commits = [
            CommitInfo("1", "feat!: breaking API change", "dev", datetime.now(), "feat", "breaking API change", True),
            CommitInfo("2", "fix: BREAKING CHANGE: remove deprecated method", "dev", datetime.now(), "fix", "remove method", False),
            CommitInfo("3", "feat: normal feature", "dev", datetime.now(), "feat", "normal feature", False)
        ]
        
        result = await analyzer.categorize_commits(breaking_commits)
        
        # Should detect breaking changes
        assert len(result.breaking_changes) == 2  # Two breaking changes
        breaking_shas = [c.sha for c in result.breaking_changes]
        assert "1" in breaking_shas
        assert "2" in breaking_shas

    @pytest.mark.asyncio
    async def test_edge_case_empty_data(self, analyzer, mock_github_service, date_range):
        """Test handling of empty data sets."""
        # Setup mocks to return empty data
        mock_github_service.get_commits_since.return_value = []
        mock_github_service.get_open_pull_requests.return_value = []
        
        result = await analyzer.analyze_weekly_activity("test/repo", date_range)
        
        # Should handle empty data gracefully
        assert isinstance(result, GitHubWeeklyData)
        assert len(result.commits.features) == 0
        assert len(result.pull_requests) == 0
        assert result.contributors.total_contributors == 0

    @pytest.mark.asyncio
    async def test_edge_case_malformed_commit_messages(self, analyzer):
        """Test handling of malformed commit messages."""
        malformed_commits = [
            CommitInfo("1", "", "dev", datetime.now(), "unknown", "", False),
            CommitInfo("2", "   ", "dev", datetime.now(), "unknown", "   ", False),
            CommitInfo("3", "no category or description", "dev", datetime.now(), "unknown", "no category", False),
            CommitInfo("4", "🎉 emoji commit message", "dev", datetime.now(), "unknown", "emoji commit", False)
        ]
        
        result = await analyzer.categorize_commits(malformed_commits)
        
        # Should handle malformed messages without crashing
        assert isinstance(result, CategorizedCommits)
        total_categorized = (
            len(result.features) + len(result.bug_fixes) + len(result.documentation) +
            len(result.performance) + len(result.refactoring) + len(result.tests) + len(result.chores)
        )
        assert total_categorized == len(malformed_commits)


class TestGitHubChangelogAnalyzerIntegration:
    """Integration tests for GitHubChangelogAnalyzer."""

    @pytest.fixture
    def real_github_service(self):
        """Create a real GitHub service for integration tests."""
        # Note: These tests would require actual GitHub API access
        # In practice, you'd use test repositories or mock the entire GitHub API
        return GitHubService(token="test_token", allowed_repository="test/repo")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_analysis_flow(self, real_github_service):
        """Test complete end-to-end analysis flow."""
        # This would be an integration test with actual GitHub API
        # Skipped in unit tests but important for full system validation
        pytest.skip("Integration test - requires actual GitHub API access")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, analyzer, mock_github_service):
        """Test performance benchmarks for various data sizes."""
        # Test with different data sizes to ensure scalability
        test_sizes = [10, 100, 500, 1000]
        
        for size in test_sizes:
            commits = [
                CommitInfo(f"commit_{i}", f"feat: feature {i}", f"dev_{i%5}", 
                          datetime.now(), "feat", f"feature {i}", False)
                for i in range(size)
            ]
            
            mock_github_service.get_commits_since.return_value = commits
            mock_github_service.get_open_pull_requests.return_value = []
            
            start_time = datetime.now()
            result = await analyzer.analyze_weekly_activity("test/repo", 
                DateRange(datetime.now() - timedelta(days=7), datetime.now()))
            execution_time = datetime.now() - start_time
            
            # Performance should scale reasonably
            assert execution_time.total_seconds() < (size * 0.1)  # Max 0.1s per commit
            assert isinstance(result, GitHubWeeklyData)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])