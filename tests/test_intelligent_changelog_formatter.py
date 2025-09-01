"""
Tests for IntelligentChangelogFormatter

Comprehensive test suite covering ML-based categorization, content summarization,
template selection, and multi-format output generation.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from devsync_ai.formatters.intelligent_changelog_formatter import (
    IntelligentChangelogFormatter,
    MLCategorizer,
    ContentSummarizer,
    TemplateSelector,
    ImpactScorer,
    ChangeCategory,
    AudienceType,
    FormatType,
    ImpactLevel,
    ChangeItem,
    CategorizedChanges,
    ExecutiveSummary,
    FormattedChangelog
)


class TestMLCategorizer:
    """Test ML-based categorization engine"""
    
    @pytest.fixture
    def categorizer(self):
        return MLCategorizer()
    
    @pytest.mark.asyncio
    async def test_categorize_feature_change(self, categorizer):
        """Test feature categorization"""
        title = "feat: add user authentication system"
        description = "Implement new OAuth2 authentication with JWT tokens"
        
        category, confidence = await categorizer.categorize_change(title, description)
        
        assert category == ChangeCategory.FEATURE
        assert confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_categorize_bug_fix(self, categorizer):
        """Test bug fix categorization"""
        title = "fix: resolve memory leak in data processor"
        description = "Fixed issue where objects weren't being garbage collected"
        
        category, confidence = await categorizer.categorize_change(title, description)
        
        assert category == ChangeCategory.BUG_FIX
        assert confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_categorize_breaking_change(self, categorizer):
        """Test breaking change detection"""
        title = "BREAKING CHANGE: remove deprecated API endpoints"
        description = "Removed v1 API endpoints that were deprecated in v2.0"
        
        category, confidence = await categorizer.categorize_change(title, description)
        
        assert category == ChangeCategory.BREAKING_CHANGE
        assert confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_categorize_security_change(self, categorizer):
        """Test security categorization"""
        title = "sec: patch SQL injection vulnerability"
        description = "Fixed security issue in user input validation"
        
        category, confidence = await categorizer.categorize_change(title, description)
        
        assert category == ChangeCategory.SECURITY
        assert confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_detect_breaking_change_with_migration(self, categorizer):
        """Test breaking change detection with migration path"""
        title = "remove deprecated getUserInfo method"
        description = "The getUserInfo method has been removed in favor of getUser"
        
        is_breaking, migration_path = await categorizer.detect_breaking_change(title, description)
        
        assert is_breaking is True
        assert migration_path is not None
        assert "update your code" in migration_path.lower()
    
    @pytest.mark.asyncio
    async def test_categorize_low_confidence_change(self, categorizer):
        """Test handling of ambiguous changes"""
        title = "update stuff"
        description = "made some changes"
        
        category, confidence = await categorizer.categorize_change(title, description)
        
        assert category == ChangeCategory.IMPROVEMENT  # Default fallback
        assert confidence <= 0.2


class TestContentSummarizer:
    """Test content summarization engine"""
    
    @pytest.fixture
    def summarizer(self):
        return ContentSummarizer()
    
    @pytest.mark.asyncio
    async def test_summarize_short_commit_message(self, summarizer):
        """Test summarization of short commit messages"""
        message = "fix: resolve login issue"
        
        result = await summarizer.summarize_commit_message(message, 100)
        
        assert result == message
    
    @pytest.mark.asyncio
    async def test_summarize_long_commit_message(self, summarizer):
        """Test summarization of long commit messages"""
        message = "feat: implement comprehensive user authentication system with OAuth2, JWT tokens, and multi-factor authentication support"
        
        result = await summarizer.summarize_commit_message(message, 50)
        
        assert len(result) <= 50
        assert result.endswith("...")
    
    @pytest.mark.asyncio
    async def test_summarize_pr_description(self, summarizer):
        """Test PR description summarization"""
        description = """
        This PR implements a new user authentication system. It includes OAuth2 integration,
        JWT token management, and multi-factor authentication. The system is designed to be
        secure and scalable. It also includes comprehensive tests and documentation.
        """
        
        result = await summarizer.summarize_pr_description(description, 100)
        
        assert len(result) <= 100
        assert "authentication" in result.lower()
    
    @pytest.mark.asyncio
    async def test_generate_executive_summary(self, summarizer):
        """Test executive summary generation"""
        changes = CategorizedChanges()
        
        # Add sample changes
        changes.features.append(ChangeItem(
            id="1", title="New feature", description="", category=ChangeCategory.FEATURE,
            impact_level=ImpactLevel.HIGH, confidence_score=0.9, author="dev1",
            timestamp=datetime.now()
        ))
        changes.security.append(ChangeItem(
            id="2", title="Security fix", description="", category=ChangeCategory.SECURITY,
            impact_level=ImpactLevel.CRITICAL, confidence_score=0.95, author="dev2",
            timestamp=datetime.now()
        ))
        
        summary = await summarizer.generate_executive_summary(changes)
        
        assert isinstance(summary, ExecutiveSummary)
        assert summary.total_changes == 2
        assert summary.security_fixes == 1
        assert len(summary.key_highlights) > 0
        assert summary.business_impact
        assert summary.risk_assessment


class TestTemplateSelector:
    """Test dynamic template selection"""
    
    @pytest.fixture
    def selector(self):
        return TemplateSelector()
    
    @pytest.mark.asyncio
    async def test_select_technical_template(self, selector):
        """Test technical audience template selection"""
        changes = CategorizedChanges()
        
        template = await selector.select_template(changes, AudienceType.TECHNICAL)
        
        assert template["audience"] == AudienceType.TECHNICAL
        assert template["include_technical_details"] is True
        assert "breaking_changes" in template["sections"]
    
    @pytest.mark.asyncio
    async def test_select_executive_template(self, selector):
        """Test executive audience template selection"""
        changes = CategorizedChanges()
        
        template = await selector.select_template(changes, AudienceType.EXECUTIVE)
        
        assert template["audience"] == AudienceType.EXECUTIVE
        assert template["include_technical_details"] is False
        assert "executive_summary" in template["sections"]
    
    @pytest.mark.asyncio
    async def test_template_adjustment_for_breaking_changes(self, selector):
        """Test template adjustment when breaking changes are present"""
        changes = CategorizedChanges()
        changes.breaking_changes.append(ChangeItem(
            id="1", title="Breaking change", description="", category=ChangeCategory.BREAKING_CHANGE,
            impact_level=ImpactLevel.CRITICAL, confidence_score=0.9, author="dev1",
            timestamp=datetime.now()
        ))
        
        template = await selector.select_template(changes, AudienceType.BUSINESS)
        
        assert "breaking_changes" in template["sections"]
        assert template["sections"][0] == "breaking_changes"  # Should be first


class TestImpactScorer:
    """Test impact scoring engine"""
    
    @pytest.fixture
    def scorer(self):
        return ImpactScorer()
    
    @pytest.mark.asyncio
    async def test_calculate_critical_impact(self, scorer):
        """Test critical impact calculation"""
        change_data = {
            'files_changed': 25,
            'lines_added': 800,
            'lines_deleted': 200,
            'affected_components': ['auth', 'database'],
            'test_coverage_change': -10,
            'review_comments': 25
        }
        
        impact = await scorer.calculate_impact_level(change_data)
        
        assert impact == ImpactLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_calculate_low_impact(self, scorer):
        """Test low impact calculation"""
        change_data = {
            'files_changed': 2,
            'lines_added': 20,
            'lines_deleted': 5,
            'affected_components': ['docs'],
            'test_coverage_change': 5,
            'review_comments': 2
        }
        
        impact = await scorer.calculate_impact_level(change_data)
        
        assert impact == ImpactLevel.LOW
    
    @pytest.mark.asyncio
    async def test_calculate_high_impact_with_critical_components(self, scorer):
        """Test high impact due to critical component changes"""
        change_data = {
            'files_changed': 5,
            'lines_added': 100,
            'lines_deleted': 50,
            'affected_components': ['security', 'core'],
            'test_coverage_change': 0,
            'review_comments': 8
        }
        
        impact = await scorer.calculate_impact_level(change_data)
        
        assert impact in [ImpactLevel.HIGH, ImpactLevel.MEDIUM]


class TestIntelligentChangelogFormatter:
    """Test main formatter class"""
    
    @pytest.fixture
    def formatter(self):
        return IntelligentChangelogFormatter()
    
    @pytest.fixture
    def sample_changes(self):
        """Sample change data for testing"""
        return [
            {
                'id': '1',
                'title': 'feat: add user authentication',
                'description': 'Implement OAuth2 authentication system',
                'author': 'john.doe',
                'timestamp': datetime.now().isoformat(),
                'pull_request_url': 'https://github.com/repo/pull/123',
                'commit_hash': 'abc123',
                'files_changed': 15,
                'lines_added': 500,
                'lines_deleted': 50,
                'affected_components': ['auth', 'api'],
                'tags': ['authentication', 'security']
            },
            {
                'id': '2',
                'title': 'fix: resolve memory leak in processor',
                'description': 'Fixed garbage collection issue',
                'author': 'jane.smith',
                'timestamp': datetime.now().isoformat(),
                'files_changed': 3,
                'lines_added': 25,
                'lines_deleted': 10,
                'affected_components': ['core'],
                'review_comments': 5
            },
            {
                'id': '3',
                'title': 'BREAKING CHANGE: remove deprecated API',
                'description': 'Removed v1 endpoints',
                'author': 'bob.wilson',
                'timestamp': datetime.now().isoformat(),
                'files_changed': 8,
                'lines_added': 0,
                'lines_deleted': 200,
                'affected_components': ['api'],
                'breaking_change_details': {'removed_endpoints': ['/v1/users']}
            }
        ]
    
    @pytest.mark.asyncio
    async def test_format_changelog_markdown(self, formatter, sample_changes):
        """Test complete changelog formatting in Markdown"""
        changelog = await formatter.format_changelog(
            changes=sample_changes,
            audience=AudienceType.TECHNICAL,
            format_type=FormatType.MARKDOWN,
            period="Week of Jan 15-21, 2024"
        )
        
        assert isinstance(changelog, FormattedChangelog)
        assert changelog.format_type == FormatType.MARKDOWN
        assert changelog.audience_type == AudienceType.TECHNICAL
        assert "# Weekly Development Changelog" in changelog.content
        assert "Breaking Changes" in changelog.content
        assert changelog.executive_summary.total_changes == 3
        assert changelog.executive_summary.breaking_changes == 1
    
    @pytest.mark.asyncio
    async def test_format_changelog_slack_blocks(self, formatter, sample_changes):
        """Test Slack Block Kit formatting"""
        changelog = await formatter.format_changelog(
            changes=sample_changes,
            audience=AudienceType.BUSINESS,
            format_type=FormatType.SLACK_BLOCKS
        )
        
        assert changelog.format_type == FormatType.SLACK_BLOCKS
        
        # Parse the JSON content
        blocks = json.loads(changelog.content)
        assert isinstance(blocks, list)
        assert len(blocks) > 0
        assert blocks[0]["type"] == "header"
        assert "Weekly Development Changelog" in blocks[0]["text"]["text"]
    
    @pytest.mark.asyncio
    async def test_format_changelog_html(self, formatter, sample_changes):
        """Test HTML formatting"""
        changelog = await formatter.format_changelog(
            changes=sample_changes,
            audience=AudienceType.MIXED,
            format_type=FormatType.HTML
        )
        
        assert changelog.format_type == FormatType.HTML
        assert "<!DOCTYPE html>" in changelog.content
        assert "Weekly Development Changelog" in changelog.content
        assert "breaking-change" in changelog.content  # CSS class for breaking changes
    
    @pytest.mark.asyncio
    async def test_format_changelog_plain_text(self, formatter, sample_changes):
        """Test plain text formatting"""
        changelog = await formatter.format_changelog(
            changes=sample_changes,
            audience=AudienceType.END_USER,
            format_type=FormatType.PLAIN_TEXT
        )
        
        assert changelog.format_type == FormatType.PLAIN_TEXT
        assert "WEEKLY DEVELOPMENT CHANGELOG" in changelog.content
        assert "BREAKING CHANGES" in changelog.content
        assert "[CRITICAL]" in changelog.content or "[HIGH]" in changelog.content
    
    @pytest.mark.asyncio
    async def test_categorized_changes_processing(self, formatter, sample_changes):
        """Test that changes are properly categorized"""
        changelog = await formatter.format_changelog(
            changes=sample_changes,
            audience=AudienceType.TECHNICAL,
            format_type=FormatType.MARKDOWN
        )
        
        categorized = changelog.categorized_changes
        
        # Should have at least one feature, one bug fix, and one breaking change
        assert len(categorized.features) >= 1
        assert len(categorized.bug_fixes) >= 1
        assert len(categorized.breaking_changes) >= 1
        
        # Check that breaking change has migration path
        breaking_change = categorized.breaking_changes[0]
        assert breaking_change.migration_path is not None
    
    @pytest.mark.asyncio
    async def test_executive_summary_generation(self, formatter, sample_changes):
        """Test executive summary generation"""
        changelog = await formatter.format_changelog(
            changes=sample_changes,
            audience=AudienceType.EXECUTIVE,
            format_type=FormatType.MARKDOWN
        )
        
        summary = changelog.executive_summary
        
        assert summary.total_changes == 3
        assert summary.breaking_changes == 1
        assert len(summary.key_highlights) > 0
        assert summary.business_impact
        assert summary.risk_assessment
        assert len(summary.recommended_actions) > 0
    
    @pytest.mark.asyncio
    async def test_metadata_generation(self, formatter, sample_changes):
        """Test metadata generation"""
        changelog = await formatter.format_changelog(
            changes=sample_changes,
            audience=AudienceType.TECHNICAL,
            format_type=FormatType.MARKDOWN
        )
        
        metadata = changelog.metadata
        
        assert "generated_at" in metadata
        assert "total_changes" in metadata
        assert "template_used" in metadata
        assert "processing_stats" in metadata
        
        stats = metadata["processing_stats"]
        assert "categorization_confidence" in stats
        assert "breaking_changes_detected" in stats
        assert "high_impact_changes" in stats
    
    @pytest.mark.asyncio
    async def test_empty_changes_handling(self, formatter):
        """Test handling of empty changes list"""
        changelog = await formatter.format_changelog(
            changes=[],
            audience=AudienceType.TECHNICAL,
            format_type=FormatType.MARKDOWN
        )
        
        assert changelog.executive_summary.total_changes == 0
        assert "No changes" in changelog.content or changelog.content.strip() != ""
    
    @pytest.mark.asyncio
    async def test_malformed_change_handling(self, formatter):
        """Test handling of malformed change data"""
        malformed_changes = [
            {'id': '1'},  # Missing required fields
            {'title': 'test'},  # Missing ID
            {
                'id': '2',
                'title': 'valid change',
                'author': 'test',
                'timestamp': datetime.now().isoformat()
            }  # Valid change
        ]
        
        changelog = await formatter.format_changelog(
            changes=malformed_changes,
            audience=AudienceType.TECHNICAL,
            format_type=FormatType.MARKDOWN
        )
        
        # Should process at least the valid change
        assert changelog.executive_summary.total_changes >= 1
    
    @pytest.mark.asyncio
    async def test_audience_specific_content(self, formatter, sample_changes):
        """Test that content is adapted for different audiences"""
        # Technical audience
        tech_changelog = await formatter.format_changelog(
            changes=sample_changes,
            audience=AudienceType.TECHNICAL,
            format_type=FormatType.MARKDOWN
        )
        
        # Executive audience
        exec_changelog = await formatter.format_changelog(
            changes=sample_changes,
            audience=AudienceType.EXECUTIVE,
            format_type=FormatType.MARKDOWN
        )
        
        # Technical should have technical details enabled in template
        assert tech_changelog.metadata["template_used"]["include_technical_details"] is True
        
        # Executive should focus on high-level summary
        assert "Executive Summary" in exec_changelog.content
        assert exec_changelog.metadata["template_used"]["include_technical_details"] is False


class TestCategorizedChanges:
    """Test CategorizedChanges data structure"""
    
    def test_add_change_to_category(self):
        """Test adding changes to appropriate categories"""
        changes = CategorizedChanges()
        
        feature_change = ChangeItem(
            id="1", title="New feature", description="", category=ChangeCategory.FEATURE,
            impact_level=ImpactLevel.MEDIUM, confidence_score=0.8, author="dev1",
            timestamp=datetime.now()
        )
        
        changes.add_change(feature_change)
        
        assert len(changes.features) == 1
        assert changes.features[0] == feature_change
    
    def test_get_by_category(self):
        """Test retrieving changes by category"""
        changes = CategorizedChanges()
        
        bug_fix = ChangeItem(
            id="1", title="Bug fix", description="", category=ChangeCategory.BUG_FIX,
            impact_level=ImpactLevel.LOW, confidence_score=0.9, author="dev1",
            timestamp=datetime.now()
        )
        
        changes.add_change(bug_fix)
        
        bug_fixes = changes.get_by_category(ChangeCategory.BUG_FIX)
        assert len(bug_fixes) == 1
        assert bug_fixes[0] == bug_fix


class TestFormattingConsistency:
    """Test formatting consistency across different formats"""
    
    @pytest.fixture
    def formatter(self):
        return IntelligentChangelogFormatter()
    
    @pytest.fixture
    def consistent_changes(self):
        """Changes designed to test consistency"""
        return [
            {
                'id': '1',
                'title': 'feat: add search functionality',
                'description': 'Implement full-text search with filters',
                'author': 'developer',
                'timestamp': datetime.now().isoformat(),
                'files_changed': 10,
                'lines_added': 300,
                'affected_components': ['search', 'api']
            }
        ]
    
    @pytest.mark.asyncio
    async def test_content_consistency_across_formats(self, formatter, consistent_changes):
        """Test that core content is consistent across formats"""
        formats = [FormatType.MARKDOWN, FormatType.HTML, FormatType.PLAIN_TEXT, FormatType.SLACK_BLOCKS]
        changelogs = {}
        
        for format_type in formats:
            changelog = await formatter.format_changelog(
                changes=consistent_changes,
                audience=AudienceType.TECHNICAL,
                format_type=format_type
            )
            changelogs[format_type] = changelog
        
        # All should have the same executive summary data
        base_summary = changelogs[FormatType.MARKDOWN].executive_summary
        for format_type, changelog in changelogs.items():
            assert changelog.executive_summary.total_changes == base_summary.total_changes
            assert changelog.executive_summary.breaking_changes == base_summary.breaking_changes
            assert len(changelog.executive_summary.key_highlights) == len(base_summary.key_highlights)
    
    @pytest.mark.asyncio
    async def test_breaking_change_prominence(self, formatter):
        """Test that breaking changes are prominently displayed in all formats"""
        breaking_changes = [
            {
                'id': '1',
                'title': 'BREAKING CHANGE: remove old API',
                'description': 'Removed deprecated endpoints',
                'author': 'developer',
                'timestamp': datetime.now().isoformat(),
                'files_changed': 5,
                'lines_deleted': 100,
                'affected_components': ['api']
            }
        ]
        
        formats = [FormatType.MARKDOWN, FormatType.HTML, FormatType.PLAIN_TEXT]
        
        for format_type in formats:
            changelog = await formatter.format_changelog(
                changes=breaking_changes,
                audience=AudienceType.TECHNICAL,
                format_type=format_type
            )
            
            # Breaking changes should be mentioned prominently
            content_lower = changelog.content.lower()
            assert "breaking" in content_lower
            
            # Breaking changes should be present and categorized correctly
            assert changelog.executive_summary.breaking_changes == 1
            assert len(changelog.categorized_changes.breaking_changes) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])