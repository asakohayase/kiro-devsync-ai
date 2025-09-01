"""
Template Validation Tests for Intelligent Changelog Formatter

Tests to ensure template consistency, validation, and proper fallback handling.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

from devsync_ai.formatters.intelligent_changelog_formatter import (
    IntelligentChangelogFormatter,
    TemplateSelector,
    ChangeCategory,
    AudienceType,
    FormatType,
    ImpactLevel,
    ChangeItem,
    CategorizedChanges
)


class TestTemplateValidation:
    """Test template validation and consistency"""
    
    @pytest.fixture
    def selector(self):
        return TemplateSelector()
    
    @pytest.fixture
    def formatter(self):
        return IntelligentChangelogFormatter()
    
    def test_all_templates_have_required_fields(self, selector):
        """Test that all templates have required fields"""
        required_fields = ["audience", "sections"]
        
        for template_name, template in selector.templates.items():
            for field in required_fields:
                assert field in template, f"Template {template_name} missing {field}"
            
            assert isinstance(template["sections"], list), f"Template {template_name} sections must be a list"
            assert len(template["sections"]) > 0, f"Template {template_name} must have at least one section"
    
    @pytest.mark.asyncio
    async def test_template_audience_mapping(self, selector):
        """Test that all audience types have corresponding templates"""
        audience_types = [AudienceType.TECHNICAL, AudienceType.BUSINESS, AudienceType.EXECUTIVE, AudienceType.END_USER]
        
        for audience in audience_types:
            changes = CategorizedChanges()
            template = await selector.select_template(changes, audience)
            assert template is not None, f"No template found for audience {audience}"
    
    @pytest.mark.asyncio
    async def test_template_section_validation(self, selector):
        """Test that template sections are valid"""
        valid_sections = {
            "executive_summary", "breaking_changes", "features", "bug_fixes", 
            "improvements", "security", "performance", "documentation", 
            "refactoring", "dependencies", "configuration", "key_metrics", 
            "risk_assessment"
        }
        
        changes = CategorizedChanges()
        
        for audience in AudienceType:
            template = await selector.select_template(changes, audience)
            for section in template["sections"]:
                assert section in valid_sections, f"Invalid section {section} in template for {audience}"
    
    @pytest.mark.asyncio
    async def test_breaking_changes_template_adjustment(self, selector):
        """Test that templates are adjusted when breaking changes are present"""
        changes = CategorizedChanges()
        changes.breaking_changes.append(ChangeItem(
            id="1", title="Breaking change", description="", category=ChangeCategory.BREAKING_CHANGE,
            impact_level=ImpactLevel.CRITICAL, confidence_score=0.9, author="dev1",
            timestamp=datetime.now()
        ))
        
        # Test with audience that normally doesn't include breaking changes
        template = await selector.select_template(changes, AudienceType.END_USER)
        
        # Should now include breaking changes section
        assert "breaking_changes" in template["sections"]
    
    @pytest.mark.asyncio
    async def test_security_template_adjustment(self, selector):
        """Test that templates are adjusted when security changes are present"""
        changes = CategorizedChanges()
        changes.security.append(ChangeItem(
            id="1", title="Security fix", description="", category=ChangeCategory.SECURITY,
            impact_level=ImpactLevel.HIGH, confidence_score=0.95, author="dev1",
            timestamp=datetime.now()
        ))
        
        # Test with business audience
        template = await selector.select_template(changes, AudienceType.BUSINESS)
        
        # Should include security section
        assert "security" in template["sections"]


class TestFormatValidation:
    """Test format-specific validation"""
    
    @pytest.fixture
    def formatter(self):
        return IntelligentChangelogFormatter()
    
    @pytest.fixture
    def sample_changes(self):
        return [
            {
                'id': '1',
                'title': 'feat: add new feature',
                'description': 'Added awesome new functionality',
                'author': 'developer',
                'timestamp': datetime.now().isoformat(),
                'files_changed': 5,
                'lines_added': 100,
                'affected_components': ['core']
            }
        ]
    
    @pytest.mark.asyncio
    async def test_markdown_format_validation(self, formatter, sample_changes):
        """Test Markdown format produces valid markdown"""
        changelog = await formatter.format_changelog(
            changes=sample_changes,
            format_type=FormatType.MARKDOWN
        )
        
        content = changelog.content
        
        # Should have proper markdown headers
        assert "# Weekly Development Changelog" in content
        assert "## " in content  # Should have section headers
        
        # Should have proper list formatting
        assert "- " in content or "* " in content
        
        # Should not have HTML tags
        assert "<" not in content or ">" not in content
    
    @pytest.mark.asyncio
    async def test_html_format_validation(self, formatter, sample_changes):
        """Test HTML format produces valid HTML"""
        changelog = await formatter.format_changelog(
            changes=sample_changes,
            format_type=FormatType.HTML
        )
        
        content = changelog.content
        
        # Should have proper HTML structure
        assert "<!DOCTYPE html>" in content
        assert "<html" in content and "</html>" in content
        assert "<head>" in content and "</head>" in content
        assert "<body>" in content and "</body>" in content
        
        # Should have proper CSS classes
        assert 'class="' in content
        
        # Should have proper meta tags
        assert '<meta charset="UTF-8">' in content
    
    @pytest.mark.asyncio
    async def test_slack_blocks_format_validation(self, formatter, sample_changes):
        """Test Slack blocks format produces valid JSON"""
        changelog = await formatter.format_changelog(
            changes=sample_changes,
            format_type=FormatType.SLACK_BLOCKS
        )
        
        # Should be valid JSON
        blocks = json.loads(changelog.content)
        assert isinstance(blocks, list)
        
        # Should have proper block structure
        for block in blocks:
            assert "type" in block
            assert block["type"] in ["header", "section", "divider", "actions"]
            
            if block["type"] == "section":
                assert "text" in block
                assert "type" in block["text"]
                assert block["text"]["type"] in ["mrkdwn", "plain_text"]
    
    @pytest.mark.asyncio
    async def test_plain_text_format_validation(self, formatter, sample_changes):
        """Test plain text format produces clean text"""
        changelog = await formatter.format_changelog(
            changes=sample_changes,
            format_type=FormatType.PLAIN_TEXT
        )
        
        content = changelog.content
        
        # Should not have HTML tags or markdown syntax
        assert "<" not in content
        assert ">" not in content
        assert "**" not in content
        assert "##" not in content
        
        # Should have proper text formatting
        assert "WEEKLY DEVELOPMENT CHANGELOG" in content
        assert "=" in content  # Should have text dividers
        assert "-" in content  # Should have section dividers
    
    @pytest.mark.asyncio
    async def test_pdf_format_validation(self, formatter, sample_changes):
        """Test PDF format produces HTML suitable for PDF conversion"""
        changelog = await formatter.format_changelog(
            changes=sample_changes,
            format_type=FormatType.PDF
        )
        
        content = changelog.content
        
        # Should be HTML with PDF-specific styles
        assert "<!DOCTYPE html>" in content
        assert "@media print" in content
        assert "page-break" in content
        assert "-webkit-print-color-adjust: exact" in content


class TestContentValidation:
    """Test content validation and consistency"""
    
    @pytest.fixture
    def formatter(self):
        return IntelligentChangelogFormatter()
    
    @pytest.mark.asyncio
    async def test_required_content_sections(self, formatter):
        """Test that required content sections are present"""
        changes = [
            {
                'id': '1',
                'title': 'BREAKING CHANGE: remove API',
                'description': 'Removed old API',
                'author': 'dev',
                'timestamp': datetime.now().isoformat(),
                'files_changed': 5
            },
            {
                'id': '2',
                'title': 'feat: add feature',
                'description': 'New feature',
                'author': 'dev',
                'timestamp': datetime.now().isoformat(),
                'files_changed': 3
            }
        ]
        
        changelog = await formatter.format_changelog(
            changes=changes,
            audience=AudienceType.TECHNICAL,
            format_type=FormatType.MARKDOWN
        )
        
        content = changelog.content.lower()
        
        # Should have breaking changes section
        assert "breaking" in content
        
        # Should have features section
        assert "feature" in content
        
        # Should have executive summary data in the changelog object
        assert changelog.executive_summary.total_changes == 2
        assert changelog.executive_summary.breaking_changes == 1
    
    @pytest.mark.asyncio
    async def test_author_attribution(self, formatter):
        """Test that author attribution is properly included"""
        changes = [
            {
                'id': '1',
                'title': 'feat: add feature',
                'description': 'New feature',
                'author': 'john.doe',
                'timestamp': datetime.now().isoformat(),
                'files_changed': 3
            }
        ]
        
        changelog = await formatter.format_changelog(
            changes=changes,
            format_type=FormatType.MARKDOWN
        )
        
        # Author should be mentioned
        assert "john.doe" in changelog.content
    
    @pytest.mark.asyncio
    async def test_timestamp_formatting(self, formatter):
        """Test that timestamps are properly formatted"""
        test_time = datetime(2024, 1, 15, 14, 30, 0)
        changes = [
            {
                'id': '1',
                'title': 'feat: add feature',
                'description': 'New feature',
                'author': 'dev',
                'timestamp': test_time.isoformat(),
                'files_changed': 3
            }
        ]
        
        changelog = await formatter.format_changelog(
            changes=changes,
            format_type=FormatType.HTML
        )
        
        # Should contain formatted date
        assert "2024" in changelog.content
        assert "01" in changelog.content or "Jan" in changelog.content
    
    @pytest.mark.asyncio
    async def test_pull_request_links(self, formatter):
        """Test that PR links are properly included"""
        changes = [
            {
                'id': '1',
                'title': 'feat: add feature',
                'description': 'New feature',
                'author': 'dev',
                'timestamp': datetime.now().isoformat(),
                'pull_request_url': 'https://github.com/repo/pull/123',
                'files_changed': 3
            }
        ]
        
        for format_type in [FormatType.MARKDOWN, FormatType.HTML]:
            changelog = await formatter.format_changelog(
                changes=changes,
                format_type=format_type
            )
            
            # Should contain PR link
            assert "https://github.com/repo/pull/123" in changelog.content
            
            if format_type == FormatType.MARKDOWN:
                assert "[View PR]" in changelog.content
            elif format_type == FormatType.HTML:
                assert '<a href=' in changelog.content


class TestErrorHandling:
    """Test error handling and fallback mechanisms"""
    
    @pytest.fixture
    def formatter(self):
        return IntelligentChangelogFormatter()
    
    @pytest.mark.asyncio
    async def test_invalid_timestamp_handling(self, formatter):
        """Test handling of invalid timestamps"""
        changes = [
            {
                'id': '1',
                'title': 'feat: add feature',
                'description': 'New feature',
                'author': 'dev',
                'timestamp': 'invalid-timestamp',
                'files_changed': 3
            }
        ]
        
        # Should not raise exception
        changelog = await formatter.format_changelog(
            changes=changes,
            format_type=FormatType.MARKDOWN
        )
        
        assert changelog is not None
        assert changelog.executive_summary.total_changes >= 0
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, formatter):
        """Test handling of changes with missing required fields"""
        changes = [
            {'id': '1'},  # Missing title, author, etc.
            {
                'id': '2',
                'title': 'valid change',
                'author': 'dev',
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        changelog = await formatter.format_changelog(
            changes=changes,
            format_type=FormatType.MARKDOWN
        )
        
        # Should process valid changes and skip invalid ones
        assert changelog.executive_summary.total_changes >= 1
    
    @pytest.mark.asyncio
    async def test_empty_changes_list(self, formatter):
        """Test handling of empty changes list"""
        changelog = await formatter.format_changelog(
            changes=[],
            format_type=FormatType.MARKDOWN
        )
        
        assert changelog is not None
        assert changelog.executive_summary.total_changes == 0
        assert changelog.content is not None
        assert len(changelog.content) > 0  # Should still generate basic structure
    
    @pytest.mark.asyncio
    async def test_unsupported_format_fallback(self, formatter):
        """Test fallback for unsupported format types"""
        changes = [
            {
                'id': '1',
                'title': 'feat: add feature',
                'author': 'dev',
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        # Test with a format that might not be fully implemented
        changelog = await formatter.format_changelog(
            changes=changes,
            format_type=FormatType.PLAIN_TEXT  # Should fall back gracefully
        )
        
        assert changelog is not None
        assert changelog.content is not None


class TestPerformanceValidation:
    """Test performance characteristics of formatting"""
    
    @pytest.fixture
    def formatter(self):
        return IntelligentChangelogFormatter()
    
    @pytest.mark.asyncio
    async def test_large_changeset_performance(self, formatter):
        """Test performance with large number of changes"""
        # Generate 100 changes
        changes = []
        for i in range(100):
            changes.append({
                'id': str(i),
                'title': f'feat: add feature {i}',
                'description': f'Description for feature {i}',
                'author': f'dev{i % 10}',
                'timestamp': datetime.now().isoformat(),
                'files_changed': i % 20 + 1,
                'lines_added': i * 10,
                'affected_components': [f'component{i % 5}']
            })
        
        import time
        start_time = time.time()
        
        changelog = await formatter.format_changelog(
            changes=changes,
            format_type=FormatType.MARKDOWN
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 10.0, f"Processing took {processing_time:.2f} seconds"
        assert changelog.executive_summary.total_changes == 100
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_large_descriptions(self, formatter):
        """Test memory usage with large change descriptions"""
        # Create changes with large descriptions
        large_description = "This is a very long description. " * 1000  # ~30KB description
        
        changes = [
            {
                'id': '1',
                'title': 'feat: add feature with large description',
                'description': large_description,
                'author': 'dev',
                'timestamp': datetime.now().isoformat(),
                'files_changed': 5
            }
        ]
        
        # Should handle large descriptions without issues
        changelog = await formatter.format_changelog(
            changes=changes,
            format_type=FormatType.MARKDOWN
        )
        
        assert changelog is not None
        # Description should be summarized, not included in full
        assert len(changelog.content) < len(large_description)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])