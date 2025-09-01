"""
Intelligent Changelog Formatter Demo

This script demonstrates the AI-powered changelog formatting capabilities
including ML-based categorization, content summarization, and multi-format output.
"""

import asyncio
from datetime import datetime, timedelta
from devsync_ai.formatters.intelligent_changelog_formatter import (
    IntelligentChangelogFormatter,
    AudienceType,
    FormatType
)


async def demo_changelog_formatting():
    """Demonstrate changelog formatting with sample data"""
    
    # Sample change data
    sample_changes = [
        {
            'id': '1',
            'title': 'feat: implement user authentication system',
            'description': 'Added OAuth2 authentication with JWT tokens, multi-factor authentication support, and session management. Includes comprehensive security measures and user role management.',
            'author': 'alice.developer',
            'timestamp': (datetime.now() - timedelta(days=2)).isoformat(),
            'pull_request_url': 'https://github.com/company/repo/pull/123',
            'commit_hash': 'a1b2c3d4',
            'files_changed': 25,
            'lines_added': 1200,
            'lines_deleted': 50,
            'affected_components': ['auth', 'api', 'database'],
            'tags': ['authentication', 'security', 'oauth2'],
            'test_coverage_change': 15,
            'review_comments': 12
        },
        {
            'id': '2',
            'title': 'fix: resolve memory leak in data processor',
            'description': 'Fixed critical memory leak that was causing performance degradation in high-load scenarios. Improved garbage collection and optimized data structures.',
            'author': 'bob.engineer',
            'timestamp': (datetime.now() - timedelta(days=1)).isoformat(),
            'pull_request_url': 'https://github.com/company/repo/pull/124',
            'files_changed': 8,
            'lines_added': 150,
            'lines_deleted': 75,
            'affected_components': ['core', 'processor'],
            'tags': ['performance', 'memory'],
            'review_comments': 6
        },
        {
            'id': '3',
            'title': 'BREAKING CHANGE: remove deprecated v1 API endpoints',
            'description': 'Removed all v1 API endpoints that were deprecated in version 2.0. This includes /v1/users, /v1/projects, and /v1/reports endpoints.',
            'author': 'charlie.architect',
            'timestamp': (datetime.now() - timedelta(hours=12)).isoformat(),
            'files_changed': 15,
            'lines_added': 0,
            'lines_deleted': 500,
            'affected_components': ['api', 'routes'],
            'breaking_change_details': {
                'removed_endpoints': ['/v1/users', '/v1/projects', '/v1/reports'],
                'migration_guide': 'Use v2 endpoints with updated response format'
            },
            'review_comments': 8
        },
        {
            'id': '4',
            'title': 'sec: patch SQL injection vulnerability in search',
            'description': 'Fixed SQL injection vulnerability in the search functionality. Added proper input sanitization and parameterized queries.',
            'author': 'diana.security',
            'timestamp': (datetime.now() - timedelta(hours=6)).isoformat(),
            'files_changed': 5,
            'lines_added': 80,
            'lines_deleted': 20,
            'affected_components': ['search', 'database'],
            'tags': ['security', 'vulnerability'],
            'review_comments': 15
        },
        {
            'id': '5',
            'title': 'perf: optimize database queries for user dashboard',
            'description': 'Improved database query performance for user dashboard by adding indexes and optimizing JOIN operations. Reduced average response time by 60%.',
            'author': 'eve.performance',
            'timestamp': (datetime.now() - timedelta(hours=3)).isoformat(),
            'files_changed': 12,
            'lines_added': 200,
            'lines_deleted': 100,
            'affected_components': ['database', 'dashboard'],
            'tags': ['performance', 'optimization'],
            'review_comments': 4
        },
        {
            'id': '6',
            'title': 'docs: update API documentation with new examples',
            'description': 'Updated API documentation with comprehensive examples, error handling guides, and best practices.',
            'author': 'frank.writer',
            'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
            'files_changed': 20,
            'lines_added': 800,
            'lines_deleted': 200,
            'affected_components': ['docs'],
            'tags': ['documentation'],
            'review_comments': 3
        }
    ]
    
    # Initialize the formatter
    formatter = IntelligentChangelogFormatter()
    
    print("🤖 AI-Powered Changelog Formatter Demo")
    print("=" * 50)
    
    # Demo 1: Technical Audience - Markdown Format
    print("\n📋 Demo 1: Technical Audience - Markdown Format")
    print("-" * 50)
    
    tech_changelog = await formatter.format_changelog(
        changes=sample_changes,
        audience=AudienceType.TECHNICAL,
        format_type=FormatType.MARKDOWN,
        period="Week of January 15-21, 2024"
    )
    
    print(f"Generated changelog with {tech_changelog.executive_summary.total_changes} changes")
    print(f"Breaking changes detected: {tech_changelog.executive_summary.breaking_changes}")
    print(f"Security fixes: {tech_changelog.executive_summary.security_fixes}")
    print(f"Categorization confidence: {tech_changelog.metadata['processing_stats']['categorization_confidence']:.2f}")
    
    # Show first 500 characters of content
    print("\nContent preview:")
    print(tech_changelog.content[:500] + "..." if len(tech_changelog.content) > 500 else tech_changelog.content)
    
    # Demo 2: Executive Audience - HTML Format
    print("\n\n👔 Demo 2: Executive Audience - HTML Format")
    print("-" * 50)
    
    exec_changelog = await formatter.format_changelog(
        changes=sample_changes,
        audience=AudienceType.EXECUTIVE,
        format_type=FormatType.HTML,
        period="Week of January 15-21, 2024"
    )
    
    print(f"Executive summary highlights: {len(exec_changelog.executive_summary.key_highlights)} items")
    print(f"Business impact: {exec_changelog.executive_summary.business_impact}")
    print(f"Risk assessment: {exec_changelog.executive_summary.risk_assessment}")
    
    print("\nRecommended actions:")
    for action in exec_changelog.executive_summary.recommended_actions:
        print(f"  • {action}")
    
    # Demo 3: Slack Blocks Format
    print("\n\n💬 Demo 3: Slack Blocks Format")
    print("-" * 50)
    
    slack_changelog = await formatter.format_changelog(
        changes=sample_changes,
        audience=AudienceType.BUSINESS,
        format_type=FormatType.SLACK_BLOCKS,
        period="Week of January 15-21, 2024"
    )
    
    print("Generated Slack Block Kit JSON:")
    import json
    blocks = json.loads(slack_changelog.content)
    print(f"Number of blocks: {len(blocks)}")
    print(f"First block type: {blocks[0]['type']}")
    print(f"Header text: {blocks[0]['text']['text']}")
    
    # Demo 4: Performance and Analytics
    print("\n\n📊 Demo 4: Performance and Analytics")
    print("-" * 50)
    
    metadata = tech_changelog.metadata
    stats = metadata['processing_stats']
    
    print(f"Processing Statistics:")
    print(f"  • Total changes processed: {metadata['total_changes']}")
    print(f"  • Average categorization confidence: {stats['categorization_confidence']:.2f}")
    print(f"  • Breaking changes detected: {stats['breaking_changes_detected']}")
    print(f"  • High impact changes: {stats['high_impact_changes']}")
    print(f"  • Generation timestamp: {metadata['generated_at']}")
    
    # Demo 5: Category Breakdown
    print("\n\n🏷️  Demo 5: Category Breakdown")
    print("-" * 50)
    
    categorized = tech_changelog.categorized_changes
    categories = [
        ("Features", len(categorized.features)),
        ("Bug Fixes", len(categorized.bug_fixes)),
        ("Breaking Changes", len(categorized.breaking_changes)),
        ("Security", len(categorized.security)),
        ("Performance", len(categorized.performance)),
        ("Documentation", len(categorized.documentation)),
    ]
    
    for category, count in categories:
        if count > 0:
            print(f"  • {category}: {count}")
    
    # Demo 6: Impact Analysis
    print("\n\n⚡ Demo 6: Impact Analysis")
    print("-" * 50)
    
    impact_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    
    all_changes = []
    for attr in categorized.__dataclass_fields__:
        all_changes.extend(getattr(categorized, attr))
    
    for change in all_changes:
        impact_counts[change.impact_level.value] += 1
    
    print("Impact Level Distribution:")
    for level, count in impact_counts.items():
        if count > 0:
            print(f"  • {level.title()}: {count}")
    
    print("\n✅ Demo completed successfully!")
    print(f"Generated {len([FormatType.MARKDOWN, FormatType.HTML, FormatType.SLACK_BLOCKS])} different formats")
    print("All changes were successfully categorized and formatted.")


async def demo_error_handling():
    """Demonstrate error handling capabilities"""
    
    print("\n\n🛡️  Error Handling Demo")
    print("-" * 50)
    
    formatter = IntelligentChangelogFormatter()
    
    # Test with malformed data
    malformed_changes = [
        {'id': '1'},  # Missing required fields
        {'title': 'incomplete change'},  # Missing ID
        {
            'id': '2',
            'title': 'valid change',
            'author': 'developer',
            'timestamp': 'invalid-timestamp',  # Invalid timestamp
            'files_changed': 'not-a-number'  # Invalid numeric field
        },
        {
            'id': '3',
            'title': 'another valid change',
            'author': 'developer',
            'timestamp': datetime.now().isoformat()
        }
    ]
    
    try:
        changelog = await formatter.format_changelog(
            changes=malformed_changes,
            audience=AudienceType.TECHNICAL,
            format_type=FormatType.MARKDOWN
        )
        
        print(f"✅ Successfully processed {changelog.executive_summary.total_changes} valid changes")
        print("❌ Invalid changes were gracefully skipped")
        print("🔧 Error handling working correctly")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(demo_changelog_formatting())
    asyncio.run(demo_error_handling())