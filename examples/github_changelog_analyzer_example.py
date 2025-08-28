"""
Example usage of GitHubChangelogAnalyzer for weekly changelog generation.

This example demonstrates how to use the advanced GitHub activity intelligence engine
to analyze repository activity and generate comprehensive weekly summaries.
"""

import asyncio
from datetime import datetime, timedelta
from devsync_ai.services.github import GitHubService, GitHubChangelogAnalyzer, DateRange


async def main():
    """Demonstrate GitHubChangelogAnalyzer usage."""
    
    # Initialize GitHub service
    github_service = GitHubService()
    
    # Initialize the changelog analyzer
    analyzer = GitHubChangelogAnalyzer(github_service)
    
    # Define date range for analysis (last 7 days)
    date_range = DateRange(
        start=datetime.now() - timedelta(days=7),
        end=datetime.now()
    )
    
    try:
        # Get the default repository
        repo = github_service.get_default_repository()
        print(f"Analyzing weekly activity for repository: {repo}")
        
        # Perform comprehensive weekly analysis
        weekly_data = await analyzer.analyze_weekly_activity(repo, date_range)
        
        # Display results
        print("\n" + "="*60)
        print("WEEKLY GITHUB ACTIVITY ANALYSIS")
        print("="*60)
        
        # Commit analysis
        print(f"\n📊 COMMIT ANALYSIS")
        print(f"Total commits: {len(weekly_data.commits.features + weekly_data.commits.bug_fixes + weekly_data.commits.improvements + weekly_data.commits.documentation + weekly_data.commits.refactoring + weekly_data.commits.performance + weekly_data.commits.tests + weekly_data.commits.chores)}")
        print(f"Features: {len(weekly_data.commits.features)}")
        print(f"Bug fixes: {len(weekly_data.commits.bug_fixes)}")
        print(f"Documentation: {len(weekly_data.commits.documentation)}")
        print(f"Performance: {len(weekly_data.commits.performance)}")
        print(f"Breaking changes: {len(weekly_data.commits.breaking_changes)}")
        
        # Pull request analysis
        print(f"\n🔄 PULL REQUEST ANALYSIS")
        print(f"Total PRs: {len(weekly_data.pull_requests)}")
        
        for pr in weekly_data.pull_requests[:3]:  # Show first 3 PRs
            print(f"\nPR #{pr.pr.id}: {pr.pr.title}")
            print(f"  Author: {pr.pr.author}")
            print(f"  Status: {pr.pr.status}")
            print(f"  Complexity Score: {pr.impact_score.complexity_score:.1f}")
            print(f"  Risk Level: {pr.impact_score.risk_level.value}")
            print(f"  Files Changed: {pr.impact_score.files_changed}")
            print(f"  Collaboration Score: {pr.collaboration_score:.1f}")
        
        # Contributor analysis
        print(f"\n👥 CONTRIBUTOR ANALYSIS")
        print(f"Total contributors: {weekly_data.contributors.total_contributors}")
        print(f"New contributors: {len(weekly_data.contributors.new_contributors)}")
        print(f"Top contributors: {', '.join(weekly_data.contributors.top_contributors[:5])}")
        
        # Repository health
        print(f"\n🏥 REPOSITORY HEALTH")
        print(f"Code Quality Score: {weekly_data.repository_health.code_quality_score:.1f}/100")
        print(f"Technical Debt Score: {weekly_data.repository_health.technical_debt_score:.1f}/100")
        print(f"Test Coverage Trend: {weekly_data.repository_health.test_coverage_trend.value}")
        print(f"Bug Density: {weekly_data.repository_health.bug_density:.3f}")
        
        if weekly_data.repository_health.recommendations:
            print("\n📋 RECOMMENDATIONS:")
            for rec in weekly_data.repository_health.recommendations:
                print(f"  • {rec}")
        
        # Performance indicators
        print(f"\n⚡ PERFORMANCE INDICATORS")
        print(f"Build Time Trend: {weekly_data.performance_indicators.build_time_trend.value}")
        print(f"Test Execution Time: {weekly_data.performance_indicators.test_execution_time:.1f}s")
        print(f"Deployment Frequency: {weekly_data.performance_indicators.deployment_frequency:.2f}")
        print(f"Change Failure Rate: {weekly_data.performance_indicators.change_failure_rate:.1%}")
        
        # Regression alerts
        if weekly_data.regression_alerts:
            print(f"\n🚨 PERFORMANCE REGRESSION ALERTS")
            for alert in weekly_data.regression_alerts[:3]:  # Show first 3 alerts
                print(f"  • {alert.metric_name} (Confidence: {alert.confidence_score:.1%})")
                print(f"    Commit: {alert.commit_sha[:8]}")
                print(f"    Severity: {alert.severity.value}")
                print(f"    Description: {alert.impact_description}")
        
        # Analysis metadata
        print(f"\n📈 ANALYSIS METADATA")
        metadata = weekly_data.analysis_metadata
        print(f"Analysis Date: {metadata['analysis_date']}")
        print(f"Date Range: {metadata['date_range']['start']} to {metadata['date_range']['end']}")
        print(f"Repository: {metadata['repository']}")
        
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        print("This might be due to API rate limits or repository access restrictions.")
        print("In a production environment, you would handle these gracefully.")


async def demonstrate_individual_features():
    """Demonstrate individual analyzer features."""
    
    github_service = GitHubService()
    analyzer = GitHubChangelogAnalyzer(github_service)
    
    print("\n" + "="*60)
    print("INDIVIDUAL FEATURE DEMONSTRATIONS")
    print("="*60)
    
    # Example commits for demonstration
    from devsync_ai.services.github import CommitInfo
    
    sample_commits = [
        CommitInfo(
            sha="abc123",
            message="feat: implement advanced user authentication system",
            author="john_doe",
            date=datetime.now() - timedelta(days=1),
            category="feat",
            description="implement advanced user authentication system",
            breaking_change=False,
            pr_number=123
        ),
        CommitInfo(
            sha="def456", 
            message="fix: resolve critical memory leak in cache layer",
            author="jane_smith",
            date=datetime.now() - timedelta(days=2),
            category="fix",
            description="resolve critical memory leak in cache layer",
            breaking_change=False,
            pr_number=124
        ),
        CommitInfo(
            sha="ghi789",
            message="perf: optimize database query performance by 40%",
            author="bob_wilson",
            date=datetime.now() - timedelta(days=3),
            category="perf",
            description="optimize database query performance by 40%",
            breaking_change=False,
            pr_number=125
        )
    ]
    
    # Demonstrate commit categorization
    print("\n🏷️  COMMIT CATEGORIZATION DEMO")
    categorized = await analyzer.categorize_commits(sample_commits)
    
    print(f"Features: {len(categorized.features)}")
    for commit in categorized.features:
        print(f"  • {commit.sha[:8]}: {commit.description}")
    
    print(f"Bug Fixes: {len(categorized.bug_fixes)}")
    for commit in categorized.bug_fixes:
        print(f"  • {commit.sha[:8]}: {commit.description}")
    
    print(f"Performance: {len(categorized.performance)}")
    for commit in categorized.performance:
        print(f"  • {commit.sha[:8]}: {commit.description}")
    
    # Demonstrate performance regression detection
    print("\n🔍 PERFORMANCE REGRESSION DETECTION DEMO")
    regressions = await analyzer.detect_performance_regressions(sample_commits)
    
    if regressions:
        for regression in regressions:
            print(f"  • Alert: {regression.metric_name}")
            print(f"    Commit: {regression.commit_sha[:8]}")
            print(f"    Confidence: {regression.confidence_score:.1%}")
            print(f"    Severity: {regression.severity.value}")
            print(f"    Actions: {', '.join(regression.suggested_actions)}")
    else:
        print("  No performance regressions detected")
    
    # Demonstrate contributor analysis
    print("\n👤 CONTRIBUTOR ANALYSIS DEMO")
    contributors = ["john_doe", "jane_smith", "bob_wilson"]
    contributor_metrics = await analyzer.analyze_contributor_activity(contributors)
    
    print(f"Total Contributors: {contributor_metrics.total_contributors}")
    print(f"Top Contributors: {', '.join(contributor_metrics.top_contributors)}")
    
    for contributor in contributor_metrics.contributors[:3]:
        print(f"\n  {contributor.username}:")
        print(f"    Productivity Score: {contributor.productivity_score:.1f}")
        print(f"    Collaboration Score: {contributor.collaboration_score:.1f}")
        print(f"    Commits: {contributor.commits_count}")
        print(f"    Lines Added: {contributor.lines_added}")
        print(f"    PRs Created: {contributor.prs_created}")
        print(f"    PRs Reviewed: {contributor.prs_reviewed}")
        print(f"    Expertise Areas: {', '.join(contributor.expertise_areas)}")


if __name__ == "__main__":
    print("GitHub Changelog Analyzer Example")
    print("This example demonstrates the advanced GitHub activity intelligence engine.")
    print("\nNote: This example requires proper GitHub API credentials and repository access.")
    print("Set GITHUB_TOKEN and GITHUB_REPOSITORY environment variables.")
    
    # Run the main demonstration
    asyncio.run(main())
    
    # Run individual feature demonstrations
    asyncio.run(demonstrate_individual_features())