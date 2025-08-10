"""GitHub API service for repository and pull request management."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import re

import httpx
from github import Github, GithubException, RateLimitExceededException
from github.PullRequest import PullRequest as GithubPR
from github.Repository import Repository
from github.Commit import Commit as GithubCommit

from ..config import settings
from ..models.core import PullRequest, PRStatus


logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Rate limit information from GitHub API."""

    limit: int
    remaining: int
    reset_time: datetime


@dataclass
class CommitInfo:
    """Information about a commit for changelog generation."""

    sha: str
    message: str
    author: str
    date: datetime
    category: str  # feat, fix, docs, etc.
    description: str
    breaking_change: bool = False
    pr_number: Optional[int] = None


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""

    def __init__(
        self, message: str, status_code: Optional[int] = None, retry_after: Optional[int] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class GitHubService:
    """Service for interacting with GitHub API."""

    def __init__(self, token: Optional[str] = None, allowed_repository: Optional[str] = None):
        """Initialize GitHub service with authentication token."""
        self.token = token or settings.github_token
        self.allowed_repository = allowed_repository or settings.github_repository
        self._github_client = None
        self._rate_limit_info: Optional[RateLimitInfo] = None

    @property
    def github_client(self) -> Github:
        """Lazy initialization of GitHub client."""
        if self._github_client is None:
            self._github_client = Github(self.token)
        return self._github_client

    def _validate_repository_access(self, repository: str) -> None:
        """Validate that the requested repository is allowed."""
        if repository != self.allowed_repository:
            raise GitHubAPIError(
                f"Access denied: This service is configured to only access '{self.allowed_repository}', "
                f"but '{repository}' was requested.",
                status_code=403,
            )

    def get_default_repository(self) -> str:
        """Get the default repository that this service is configured to track."""
        return self.allowed_repository

    async def get_default_pr_summary(self) -> Dict[str, Any]:
        """Get PR summary for the default configured repository."""
        return await self.get_pr_summary_with_analysis(self.allowed_repository)

    async def check_rate_limit(self) -> RateLimitInfo:
        """Check current rate limit status."""
        try:
            rate_limit = self.github_client.get_rate_limit()
            core_limit = rate_limit.core

            self._rate_limit_info = RateLimitInfo(
                limit=core_limit.limit, remaining=core_limit.remaining, reset_time=core_limit.reset
            )

            logger.debug(
                f"Rate limit: {core_limit.remaining}/{core_limit.limit}, resets at {core_limit.reset}"
            )
            return self._rate_limit_info

        except GithubException as e:
            logger.error(f"Failed to check rate limit: {e}")
            raise GitHubAPIError(f"Rate limit check failed: {e}", status_code=e.status)

    async def _handle_rate_limit(self) -> None:
        """Handle rate limit by waiting if necessary."""
        if self._rate_limit_info and self._rate_limit_info.remaining < 10:
            wait_time = (self._rate_limit_info.reset_time - datetime.now()).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit low, waiting {wait_time} seconds")
                await asyncio.sleep(wait_time)

    async def _execute_with_retry(self, func, *args, max_retries: int = 3, **kwargs) -> Any:
        """Execute GitHub API call with retry logic and rate limit handling."""
        last_exception = None

        for attempt in range(max_retries):
            try:
                # Check rate limit before making request
                await self.check_rate_limit()
                await self._handle_rate_limit()

                # Execute the function
                result = func(*args, **kwargs)
                return result

            except RateLimitExceededException as e:
                logger.warning(f"Rate limit exceeded, attempt {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    raise GitHubAPIError(
                        "Rate limit exceeded after retries", status_code=403, retry_after=3600
                    )

                # Wait for rate limit reset
                await asyncio.sleep(60 * (attempt + 1))  # Exponential backoff
                last_exception = e

            except GithubException as e:
                logger.error(f"GitHub API error on attempt {attempt + 1}/{max_retries}: {e}")

                # Don't retry on authentication or not found errors
                if e.status in [401, 403, 404]:
                    raise GitHubAPIError(f"GitHub API error: {e}", status_code=e.status)

                if attempt == max_retries - 1:
                    raise GitHubAPIError(
                        f"GitHub API error after retries: {e}", status_code=e.status
                    )

                # Exponential backoff for retryable errors
                await asyncio.sleep(2**attempt)
                last_exception = e

            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:
                    raise GitHubAPIError(f"Unexpected error: {e}")

                await asyncio.sleep(2**attempt)
                last_exception = e

        # This should never be reached, but just in case
        if last_exception:
            raise GitHubAPIError(f"Failed after {max_retries} attempts: {last_exception}")

    async def get_repository(self, repo_name: str) -> Repository:
        """Get repository object by name."""
        self._validate_repository_access(repo_name)
        try:
            return await self._execute_with_retry(self.github_client.get_repo, repo_name)
        except GitHubAPIError:
            raise
        except Exception as e:
            raise GitHubAPIError(f"Failed to get repository {repo_name}: {e}")

    async def test_authentication(self) -> Dict[str, Any]:
        """Test GitHub authentication and return user info."""
        try:
            user = await self._execute_with_retry(self.github_client.get_user)
            rate_limit = await self.check_rate_limit()

            return {
                "authenticated": True,
                "user": {
                    "login": user.login,
                    "name": user.name,
                    "email": user.email,
                    "id": user.id,
                },
                "rate_limit": {
                    "limit": rate_limit.limit,
                    "remaining": rate_limit.remaining,
                    "reset_time": rate_limit.reset_time.isoformat(),
                },
            }
        except GitHubAPIError:
            raise
        except Exception as e:
            raise GitHubAPIError(f"Authentication test failed: {e}")

    def _convert_github_pr_to_model(self, github_pr: GithubPR, repository: str) -> PullRequest:
        """Convert GitHub PR object to our PullRequest model."""
        # Determine PR status
        if github_pr.draft:
            status = PRStatus.DRAFT
        elif github_pr.state == "closed":
            if github_pr.merged:
                status = PRStatus.MERGED
            else:
                status = PRStatus.CLOSED
        else:
            # Check if PR is ready for review (has reviewers or review requests)
            if github_pr.requested_reviewers or github_pr.requested_teams:
                status = PRStatus.READY_FOR_REVIEW
            else:
                status = PRStatus.OPEN

        # Extract reviewer information
        reviewers = []
        if github_pr.requested_reviewers:
            reviewers.extend([reviewer.login for reviewer in github_pr.requested_reviewers])
        if github_pr.requested_teams:
            reviewers.extend([team.name for team in github_pr.requested_teams])

        # Extract labels
        labels = [label.name for label in github_pr.labels]

        return PullRequest(
            id=str(github_pr.number),
            repository=repository,
            title=github_pr.title,
            author=github_pr.user.login,
            status=status,
            merge_conflicts=github_pr.mergeable
            is False,  # None means unknown, False means conflicts
            created_at=github_pr.created_at,
            updated_at=github_pr.updated_at,
            reviewers=reviewers,
            labels=labels,
        )

    async def get_open_pull_requests(self, repository: str) -> List[PullRequest]:
        """Get all open pull requests for a repository."""
        self._validate_repository_access(repository)
        try:
            repo = await self.get_repository(repository)

            # Get open PRs
            github_prs = await self._execute_with_retry(lambda: list(repo.get_pulls(state="open")))

            # Convert to our model
            pull_requests = []
            for github_pr in github_prs:
                try:
                    pr = self._convert_github_pr_to_model(github_pr, repository)
                    pull_requests.append(pr)
                except Exception as e:
                    logger.error(f"Failed to convert PR #{github_pr.number}: {e}")
                    continue

            logger.info(f"Retrieved {len(pull_requests)} open PRs from {repository}")
            return pull_requests

        except GitHubAPIError:
            raise
        except Exception as e:
            raise GitHubAPIError(f"Failed to get open PRs for {repository}: {e}")

    async def check_merge_conflicts(self, repository: str, pr_number: int) -> bool:
        """Check if a specific PR has merge conflicts."""
        self._validate_repository_access(repository)
        try:
            repo = await self.get_repository(repository)
            pr = await self._execute_with_retry(repo.get_pull, pr_number)

            # GitHub's mergeable field: True = no conflicts, False = conflicts, None = unknown
            if pr.mergeable is None:
                # If mergeable status is unknown, we need to trigger a merge check
                # This happens by accessing the mergeable_state property
                mergeable_state = pr.mergeable_state
                logger.debug(f"PR #{pr_number} mergeable_state: {mergeable_state}")

                # After accessing mergeable_state, mergeable should be updated
                # If it's still None, assume no conflicts for now
                return pr.mergeable is False

            return pr.mergeable is False

        except GitHubAPIError:
            raise
        except Exception as e:
            raise GitHubAPIError(f"Failed to check merge conflicts for PR #{pr_number}: {e}")

    async def get_pull_request_details(
        self, repository: str, pr_number: int
    ) -> Optional[PullRequest]:
        """Get detailed information about a specific pull request."""
        self._validate_repository_access(repository)
        try:
            repo = await self.get_repository(repository)
            github_pr = await self._execute_with_retry(repo.get_pull, pr_number)

            return self._convert_github_pr_to_model(github_pr, repository)

        except GitHubAPIError as e:
            if e.status_code == 404:
                logger.warning(f"PR #{pr_number} not found in {repository}")
                return None
            raise
        except Exception as e:
            raise GitHubAPIError(f"Failed to get PR #{pr_number} details: {e}")

    async def analyze_pr_readiness(self, prs: List[PullRequest]) -> Dict[str, Any]:
        """Analyze PR readiness and provide insights."""
        try:
            analysis = {
                "total_prs": len(prs),
                "ready_for_review": 0,
                "draft_prs": 0,
                "conflicted_prs": 0,
                "stale_prs": 0,
                "prs_by_author": {},
                "average_age_days": 0,
                "oldest_pr": None,
                "newest_pr": None,
            }

            if not prs:
                return analysis

            now = datetime.now()
            total_age_days = 0
            oldest_pr_age = timedelta(0)
            newest_pr_age = timedelta(days=365)  # Start with a large value

            for pr in prs:
                # Count by status
                if pr.status == PRStatus.READY_FOR_REVIEW:
                    analysis["ready_for_review"] += 1
                elif pr.status == PRStatus.DRAFT:
                    analysis["draft_prs"] += 1

                # Count conflicts
                if pr.merge_conflicts:
                    analysis["conflicted_prs"] += 1

                # Calculate age
                pr_age = now - pr.created_at
                total_age_days += pr_age.days

                # Check if stale (older than 7 days without updates)
                if (now - pr.updated_at).days > 7:
                    analysis["stale_prs"] += 1

                # Track oldest and newest
                if pr_age > oldest_pr_age:
                    oldest_pr_age = pr_age
                    analysis["oldest_pr"] = {
                        "id": pr.id,
                        "title": pr.title,
                        "author": pr.author,
                        "age_days": pr_age.days,
                    }

                if pr_age < newest_pr_age:
                    newest_pr_age = pr_age
                    analysis["newest_pr"] = {
                        "id": pr.id,
                        "title": pr.title,
                        "author": pr.author,
                        "age_days": pr_age.days,
                    }

                # Count by author
                if pr.author not in analysis["prs_by_author"]:
                    analysis["prs_by_author"][pr.author] = 0
                analysis["prs_by_author"][pr.author] += 1

            # Calculate average age
            analysis["average_age_days"] = total_age_days / len(prs) if prs else 0

            logger.info(f"PR readiness analysis completed for {len(prs)} PRs")
            return analysis

        except Exception as e:
            logger.error(f"PR readiness analysis failed: {e}")
            return {"error": str(e)}

    async def get_pr_summary_with_analysis(self, repository: str) -> Dict[str, Any]:
        """Get comprehensive PR summary with current status and analysis."""
        self._validate_repository_access(repository)
        try:
            # Get current PRs from GitHub
            github_prs = await self.get_open_pull_requests(repository)

            # Update merge conflict status for all PRs
            conflict_updates = 0
            for pr in github_prs:
                try:
                    has_conflicts = await self.check_merge_conflicts(repository, int(pr.id))
                    if has_conflicts != pr.merge_conflicts:
                        pr.merge_conflicts = has_conflicts
                        conflict_updates += 1
                except Exception as e:
                    logger.error(f"Failed to update conflicts for PR #{pr.id}: {e}")

            # Get readiness analysis
            analysis = await self.analyze_pr_readiness(github_prs)

            # Format PR details for summary
            pr_details = []
            for pr in github_prs:
                pr_details.append(
                    {
                        "id": pr.id,
                        "title": pr.title,
                        "author": pr.author,
                        "status": (
                            pr.status.value if hasattr(pr.status, "value") else str(pr.status)
                        ),
                        "merge_conflicts": pr.merge_conflicts,
                        "reviewers": pr.reviewers,
                        "labels": pr.labels,
                        "created_at": pr.created_at.isoformat(),
                        "updated_at": pr.updated_at.isoformat(),
                        "age_days": (datetime.now() - pr.created_at).days,
                    }
                )

            summary = {
                "repository": repository,
                "total_prs": len(github_prs),
                "conflict_updates": conflict_updates,
                "analysis": analysis,
                "pull_requests": pr_details,
                "generated_at": datetime.now().isoformat(),
            }

            return summary

        except Exception as e:
            logger.error(f"Failed to generate PR summary for {repository}: {e}")
            return {
                "repository": repository,
                "error": str(e),
                "generated_at": datetime.now().isoformat(),
            }

    def _parse_commit_message(self, commit_message: str) -> Dict[str, Any]:
        """Parse commit message using conventional commits format."""
        # Conventional commits pattern: type(scope): description
        conventional_pattern = (
            r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)!?(\([^)]+\))?: (.+)$"
        )

        # Check for breaking changes
        breaking_change = "!" in commit_message or "BREAKING CHANGE" in commit_message.upper()

        # Try to match conventional commits format
        match = re.match(conventional_pattern, commit_message.split("\n")[0], re.IGNORECASE)

        if match:
            commit_type = match.group(1).lower()
            scope = match.group(2)[1:-1] if match.group(2) else None
            description = match.group(3)
        else:
            # Fallback: try to categorize based on keywords
            first_line = commit_message.split("\n")[0].lower()
            if any(word in first_line for word in ["fix", "bug", "patch", "hotfix"]):
                commit_type = "fix"
            elif any(word in first_line for word in ["feat", "feature", "add", "new"]):
                commit_type = "feat"
            elif any(word in first_line for word in ["doc", "readme", "comment"]):
                commit_type = "docs"
            elif any(word in first_line for word in ["test", "spec"]):
                commit_type = "test"
            elif any(word in first_line for word in ["refactor", "cleanup", "improve"]):
                commit_type = "refactor"
            elif any(word in first_line for word in ["style", "format", "lint"]):
                commit_type = "style"
            else:
                commit_type = "chore"

            description = commit_message.split("\n")[0]
            scope = None

        # Extract PR number if present
        pr_pattern = r"#(\d+)"
        pr_match = re.search(pr_pattern, commit_message)
        pr_number = int(pr_match.group(1)) if pr_match else None

        return {
            "type": commit_type,
            "scope": scope,
            "description": description,
            "breaking_change": breaking_change,
            "pr_number": pr_number,
            "full_message": commit_message,
        }

    async def get_commits_since(
        self, repository: str, since_date: datetime, until_date: Optional[datetime] = None
    ) -> List[CommitInfo]:
        """Get commits from repository since a specific date."""
        self._validate_repository_access(repository)
        try:
            repo = await self.get_repository(repository)

            # Get commits since the specified date
            if until_date:
                commits = await self._execute_with_retry(
                    lambda: list(repo.get_commits(since=since_date, until=until_date))
                )
            else:
                commits = await self._execute_with_retry(
                    lambda: list(repo.get_commits(since=since_date))
                )

            commit_infos = []
            for commit in commits:
                try:
                    parsed = self._parse_commit_message(commit.commit.message)

                    commit_info = CommitInfo(
                        sha=commit.sha,
                        message=commit.commit.message,
                        author=commit.commit.author.name if commit.commit.author else "Unknown",
                        date=commit.commit.author.date if commit.commit.author else datetime.now(),
                        category=parsed["type"],
                        description=parsed["description"],
                        breaking_change=parsed["breaking_change"],
                        pr_number=parsed["pr_number"],
                    )
                    commit_infos.append(commit_info)
                except Exception as e:
                    logger.error(f"Failed to parse commit {commit.sha}: {e}")
                    continue

            logger.info(
                f"Retrieved {len(commit_infos)} commits from {repository} since {since_date}"
            )
            return commit_infos

        except GitHubAPIError:
            raise
        except Exception as e:
            raise GitHubAPIError(f"Failed to get commits for {repository}: {e}")

    async def get_commits_between_tags(
        self, repository: str, from_tag: str, to_tag: str
    ) -> List[CommitInfo]:
        """Get commits between two tags for changelog generation."""
        self._validate_repository_access(repository)
        try:
            repo = await self.get_repository(repository)

            # Get the commit SHAs for the tags
            from_ref = await self._execute_with_retry(repo.get_git_ref, f"tags/{from_tag}")
            to_ref = await self._execute_with_retry(repo.get_git_ref, f"tags/{to_tag}")

            # Get commits between the tags
            comparison = await self._execute_with_retry(
                repo.compare, from_ref.object.sha, to_ref.object.sha
            )

            commit_infos = []
            for commit in comparison.commits:
                try:
                    parsed = self._parse_commit_message(commit.commit.message)

                    commit_info = CommitInfo(
                        sha=commit.sha,
                        message=commit.commit.message,
                        author=commit.commit.author.name if commit.commit.author else "Unknown",
                        date=commit.commit.author.date if commit.commit.author else datetime.now(),
                        category=parsed["type"],
                        description=parsed["description"],
                        breaking_change=parsed["breaking_change"],
                        pr_number=parsed["pr_number"],
                    )
                    commit_infos.append(commit_info)
                except Exception as e:
                    logger.error(f"Failed to parse commit {commit.sha}: {e}")
                    continue

            logger.info(f"Retrieved {len(commit_infos)} commits between {from_tag} and {to_tag}")
            return commit_infos

        except GitHubAPIError:
            raise
        except Exception as e:
            raise GitHubAPIError(f"Failed to get commits between tags: {e}")

    async def generate_changelog_data(
        self, repository: str, since_date: datetime, until_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate structured changelog data from commits."""
        self._validate_repository_access(repository)
        try:
            commits = await self.get_commits_since(repository, since_date, until_date)

            # Group commits by category
            changelog_data = {
                "repository": repository,
                "period": {
                    "from": since_date.isoformat(),
                    "to": (until_date or datetime.now()).isoformat(),
                },
                "total_commits": len(commits),
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

            # Process each commit
            for commit in commits:
                # Add to appropriate category
                if commit.category == "feat":
                    changelog_data["categories"]["features"].append(
                        {
                            "sha": commit.sha[:8],
                            "description": commit.description,
                            "author": commit.author,
                            "pr_number": commit.pr_number,
                        }
                    )
                elif commit.category == "fix":
                    changelog_data["categories"]["bug_fixes"].append(
                        {
                            "sha": commit.sha[:8],
                            "description": commit.description,
                            "author": commit.author,
                            "pr_number": commit.pr_number,
                        }
                    )
                elif commit.category == "docs":
                    changelog_data["categories"]["documentation"].append(
                        {
                            "sha": commit.sha[:8],
                            "description": commit.description,
                            "author": commit.author,
                            "pr_number": commit.pr_number,
                        }
                    )
                elif commit.category == "perf":
                    changelog_data["categories"]["performance"].append(
                        {
                            "sha": commit.sha[:8],
                            "description": commit.description,
                            "author": commit.author,
                            "pr_number": commit.pr_number,
                        }
                    )
                elif commit.category == "refactor":
                    changelog_data["categories"]["refactoring"].append(
                        {
                            "sha": commit.sha[:8],
                            "description": commit.description,
                            "author": commit.author,
                            "pr_number": commit.pr_number,
                        }
                    )
                elif commit.category == "test":
                    changelog_data["categories"]["testing"].append(
                        {
                            "sha": commit.sha[:8],
                            "description": commit.description,
                            "author": commit.author,
                            "pr_number": commit.pr_number,
                        }
                    )
                else:  # chore, style, ci, build, etc.
                    changelog_data["categories"]["chores"].append(
                        {
                            "sha": commit.sha[:8],
                            "description": commit.description,
                            "author": commit.author,
                            "pr_number": commit.pr_number,
                        }
                    )

                # Track breaking changes separately
                if commit.breaking_change:
                    changelog_data["categories"]["breaking_changes"].append(
                        {
                            "sha": commit.sha[:8],
                            "description": commit.description,
                            "author": commit.author,
                            "pr_number": commit.pr_number,
                            "category": commit.category,
                        }
                    )

                # Count contributors
                if commit.author not in changelog_data["contributors"]:
                    changelog_data["contributors"][commit.author] = 0
                changelog_data["contributors"][commit.author] += 1

                # Track unique PR numbers
                if commit.pr_number and commit.pr_number not in changelog_data["pull_requests"]:
                    changelog_data["pull_requests"].append(commit.pr_number)

            # Sort contributors by contribution count
            changelog_data["contributors"] = dict(
                sorted(changelog_data["contributors"].items(), key=lambda x: x[1], reverse=True)
            )

            logger.info(f"Generated changelog data for {repository} with {len(commits)} commits")
            return changelog_data

        except GitHubAPIError:
            raise
        except Exception as e:
            raise GitHubAPIError(f"Failed to generate changelog data: {e}")

    async def format_changelog_markdown(self, changelog_data: Dict[str, Any]) -> str:
        """Format changelog data as markdown."""
        try:
            md_lines = []

            # Header
            period_from = datetime.fromisoformat(changelog_data["period"]["from"]).strftime(
                "%Y-%m-%d"
            )
            period_to = datetime.fromisoformat(changelog_data["period"]["to"]).strftime("%Y-%m-%d")

            md_lines.append(f"# Changelog")
            md_lines.append(f"")
            md_lines.append(f"**Period:** {period_from} to {period_to}")
            md_lines.append(f"**Repository:** {changelog_data['repository']}")
            md_lines.append(f"**Total Commits:** {changelog_data['total_commits']}")
            md_lines.append(f"")

            # Breaking changes (if any)
            if changelog_data["categories"]["breaking_changes"]:
                md_lines.append("## ⚠️ Breaking Changes")
                md_lines.append("")
                for change in changelog_data["categories"]["breaking_changes"]:
                    pr_link = f" ([#{change['pr_number']}])" if change["pr_number"] else ""
                    md_lines.append(
                        f"- **{change['category'].upper()}**: {change['description']} by {change['author']}{pr_link}"
                    )
                md_lines.append("")

            # Features
            if changelog_data["categories"]["features"]:
                md_lines.append("## ✨ New Features")
                md_lines.append("")
                for feature in changelog_data["categories"]["features"]:
                    pr_link = f" ([#{feature['pr_number']}])" if feature["pr_number"] else ""
                    md_lines.append(f"- {feature['description']} by {feature['author']}{pr_link}")
                md_lines.append("")

            # Bug fixes
            if changelog_data["categories"]["bug_fixes"]:
                md_lines.append("## 🐛 Bug Fixes")
                md_lines.append("")
                for fix in changelog_data["categories"]["bug_fixes"]:
                    pr_link = f" ([#{fix['pr_number']}])" if fix["pr_number"] else ""
                    md_lines.append(f"- {fix['description']} by {fix['author']}{pr_link}")
                md_lines.append("")

            # Performance improvements
            if changelog_data["categories"]["performance"]:
                md_lines.append("## ⚡ Performance Improvements")
                md_lines.append("")
                for perf in changelog_data["categories"]["performance"]:
                    pr_link = f" ([#{perf['pr_number']}])" if perf["pr_number"] else ""
                    md_lines.append(f"- {perf['description']} by {perf['author']}{pr_link}")
                md_lines.append("")

            # Documentation
            if changelog_data["categories"]["documentation"]:
                md_lines.append("## 📚 Documentation")
                md_lines.append("")
                for doc in changelog_data["categories"]["documentation"]:
                    pr_link = f" ([#{doc['pr_number']}])" if doc["pr_number"] else ""
                    md_lines.append(f"- {doc['description']} by {doc['author']}{pr_link}")
                md_lines.append("")

            # Refactoring
            if changelog_data["categories"]["refactoring"]:
                md_lines.append("## 🔧 Code Refactoring")
                md_lines.append("")
                for refactor in changelog_data["categories"]["refactoring"]:
                    pr_link = f" ([#{refactor['pr_number']}])" if refactor["pr_number"] else ""
                    md_lines.append(f"- {refactor['description']} by {refactor['author']}{pr_link}")
                md_lines.append("")

            # Testing
            if changelog_data["categories"]["testing"]:
                md_lines.append("## 🧪 Testing")
                md_lines.append("")
                for test in changelog_data["categories"]["testing"]:
                    pr_link = f" ([#{test['pr_number']}])" if test["pr_number"] else ""
                    md_lines.append(f"- {test['description']} by {test['author']}{pr_link}")
                md_lines.append("")

            # Contributors
            if changelog_data["contributors"]:
                md_lines.append("## 👥 Contributors")
                md_lines.append("")
                for contributor, count in changelog_data["contributors"].items():
                    md_lines.append(f"- {contributor} ({count} commit{'s' if count > 1 else ''})")
                md_lines.append("")

            # Pull requests
            if changelog_data["pull_requests"]:
                md_lines.append("## 🔗 Pull Requests")
                md_lines.append("")
                pr_list = ", ".join([f"#{pr}" for pr in sorted(changelog_data["pull_requests"])])
                md_lines.append(f"This release includes changes from: {pr_list}")
                md_lines.append("")

            return "\n".join(md_lines)

        except Exception as e:
            logger.error(f"Failed to format changelog markdown: {e}")
            return f"# Changelog\n\nError generating changelog: {e}"

    async def close(self) -> None:
        """Clean up resources."""
        if self._github_client:
            # PyGithub doesn't have explicit cleanup, but we can clear the reference
            self._github_client = None
        logger.debug("GitHub service closed")
