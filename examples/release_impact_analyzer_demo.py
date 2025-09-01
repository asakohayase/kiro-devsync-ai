"""
Release Impact Analyzer Demo

This script demonstrates how to use the ReleaseImpactAnalyzer for comprehensive
release risk assessment and impact analysis.
"""

import asyncio
from datetime import datetime
from devsync_ai.analytics.release_impact_analyzer import (
    ReleaseImpactAnalyzer,
    Change,
    ChangeType,
    DeploymentEnvironment
)


async def demo_release_impact_analysis():
    """Demonstrate release impact analysis capabilities"""
    
    print("🚀 Release Impact Analyzer Demo")
    print("=" * 50)
    
    # Initialize the analyzer
    config = {
        'complexity_thresholds': {
            'low': 10.0,
            'medium': 25.0,
            'high': 50.0
        },
        'performance_thresholds': {
            'acceptable': 5.0,
            'concerning': 15.0,
            'critical': 30.0
        }
    }
    
    analyzer = ReleaseImpactAnalyzer(config)
    
    # Create sample changes for analysis
    changes = [
        Change(
            id="change-1",
            type=ChangeType.FEATURE,
            description="Add new user authentication with OAuth2",
            files_changed=["src/auth/oauth.py", "src/api/auth_routes.py", "src/models/user.py"],
            lines_added=250,
            lines_removed=30,
            complexity_score=35.0,
            author="security_team",
            timestamp=datetime.now(),
            breaking_change=False,
            security_impact=True,
            performance_impact=False,
            dependencies_affected=["authlib", "flask-login"],
            test_coverage_change=8.0
        ),
        Change(
            id="change-2",
            type=ChangeType.BREAKING_CHANGE,
            description="Remove deprecated API v1 endpoints",
            files_changed=["src/api/v1/", "docs/api_migration.md"],
            lines_added=50,
            lines_removed=400,
            complexity_score=45.0,
            author="api_team",
            timestamp=datetime.now(),
            breaking_change=True,
            security_impact=False,
            performance_impact=True,
            dependencies_affected=[],
            test_coverage_change=-5.0
        ),
        Change(
            id="change-3",
            type=ChangeType.SECURITY_FIX,
            description="Fix SQL injection vulnerability in search",
            files_changed=["src/api/search.py", "src/database/queries.py"],
            lines_added=40,
            lines_removed=25,
            complexity_score=15.0,
            author="security_team",
            timestamp=datetime.now(),
            breaking_change=False,
            security_impact=True,
            performance_impact=False,
            dependencies_affected=["sqlalchemy"],
            test_coverage_change=12.0
        ),
        Change(
            id="change-4",
            type=ChangeType.FEATURE,
            description="Add database migration for user preferences",
            files_changed=["migrations/001_user_preferences.sql", "src/models/preferences.py"],
            lines_added=120,
            lines_removed=0,
            complexity_score=25.0,
            author="backend_team",
            timestamp=datetime.now(),
            breaking_change=False,
            security_impact=False,
            performance_impact=True,
            dependencies_affected=["alembic"],
            test_coverage_change=6.0
        )
    ]
    
    print(f"📊 Analyzing {len(changes)} changes for release impact...")
    print()
    
    # 1. Semantic Version Analysis
    print("1️⃣ Semantic Version Analysis")
    print("-" * 30)
    
    version_analysis = await analyzer.analyze_semantic_versioning(changes, "2.1.5")
    
    print(f"Current Version: {version_analysis.current_version}")
    print(f"Recommended Version: {version_analysis.recommended_version}")
    print(f"Bump Type: {version_analysis.bump_type.value}")
    print(f"Confidence Score: {version_analysis.confidence_score:.2f}")
    print("Reasoning:")
    for reason in version_analysis.reasoning:
        print(f"  • {reason}")
    print(f"Breaking Changes: {len(version_analysis.breaking_changes)}")
    print(f"New Features: {len(version_analysis.new_features)}")
    print(f"Bug Fixes: {len(version_analysis.bug_fixes)}")
    print()
    
    # 2. Deployment Risk Assessment
    print("2️⃣ Deployment Risk Assessment")
    print("-" * 30)
    
    risk_assessment = await analyzer.assess_deployment_risk(changes, DeploymentEnvironment.PRODUCTION)
    
    print(f"Overall Risk: {risk_assessment.overall_risk.value.upper()}")
    print(f"Go/No-Go Recommendation: {'✅ GO' if risk_assessment.go_no_go_recommendation else '❌ NO-GO'}")
    print(f"Confidence Score: {risk_assessment.confidence_score:.2f}")
    print()
    print("Risk Factors:")
    for factor in risk_assessment.risk_factors:
        print(f"  ⚠️  {factor}")
    print()
    print("Mitigation Strategies:")
    for strategy in risk_assessment.mitigation_strategies[:5]:  # Show first 5
        print(f"  🛡️  {strategy}")
    print()
    
    # 3. Performance Impact Analysis
    print("3️⃣ Performance Impact Analysis")
    print("-" * 30)
    
    perf_impact = risk_assessment.performance_impact
    
    print(f"Performance Risk: {perf_impact.overall_risk.value.upper()}")
    print(f"Estimated Performance Change: {perf_impact.estimated_performance_change:.1f}%")
    print(f"Affected Components: {', '.join(perf_impact.affected_components)}")
    print()
    print("Benchmark Predictions:")
    for metric, value in perf_impact.benchmark_predictions.items():
        print(f"  📈 {metric}: {value:+.1f}%")
    print()
    print("Performance Recommendations:")
    for rec in perf_impact.recommendations[:3]:  # Show first 3
        print(f"  💡 {rec}")
    print()
    
    # 4. Security Impact Analysis
    print("4️⃣ Security Impact Analysis")
    print("-" * 30)
    
    security_analysis = risk_assessment.security_analysis
    
    print(f"Security Risk: {security_analysis.risk_level.value.upper()}")
    print(f"Security Score Change: {security_analysis.security_score_change:+.1f}")
    print(f"Vulnerabilities Fixed: {len(security_analysis.vulnerabilities_fixed)}")
    print(f"Vulnerabilities Introduced: {len(security_analysis.vulnerabilities_introduced)}")
    print(f"Dependency Vulnerabilities: {len(security_analysis.dependency_vulnerabilities)}")
    print()
    if security_analysis.vulnerabilities_fixed:
        print("Fixed Vulnerabilities:")
        for vuln in security_analysis.vulnerabilities_fixed:
            print(f"  🔒 {vuln['description']} (Severity: {vuln['severity']})")
    print()
    print("Security Recommendations:")
    for rec in security_analysis.recommendations:
        print(f"  🔐 {rec}")
    print()
    
    # 5. Rollback Risk Assessment
    print("5️⃣ Rollback Risk Assessment")
    print("-" * 30)
    
    rollback_plan = risk_assessment.rollback_plan
    
    print(f"Rollback Risk: {rollback_plan.rollback_risk.value.upper()}")
    print(f"Rollback Complexity: {rollback_plan.rollback_complexity:.1f}")
    print(f"Estimated Rollback Time: {rollback_plan.estimated_rollback_time}")
    print(f"Data Migration Required: {'Yes' if rollback_plan.data_migration_required else 'No'}")
    print(f"Rollback Testing Required: {'Yes' if rollback_plan.rollback_testing_required else 'No'}")
    print()
    print("Rollback Steps:")
    for i, step in enumerate(rollback_plan.rollback_steps[:5], 1):  # Show first 5
        print(f"  {i}. {step}")
    print()
    print("Mitigation Strategies:")
    for strategy in rollback_plan.mitigation_strategies[:3]:  # Show first 3
        print(f"  🛡️  {strategy}")
    print()
    
    # 6. Stakeholder Impact Analysis
    print("6️⃣ Stakeholder Impact Analysis")
    print("-" * 30)
    
    stakeholder_impact = risk_assessment.stakeholder_impact
    
    print(f"Affected Stakeholders: {len(stakeholder_impact.affected_stakeholders)}")
    print()
    for stakeholder in stakeholder_impact.affected_stakeholders:
        severity = stakeholder_impact.impact_severity[stakeholder]
        priority = stakeholder_impact.notification_priority[stakeholder]
        template = stakeholder_impact.communication_templates[stakeholder]
        
        print(f"👥 {stakeholder.replace('_', ' ').title()}:")
        print(f"   Impact Severity: {severity.value.upper()}")
        print(f"   Notification Priority: {priority.upper()}")
        print(f"   Communication Template: {template}")
        print()
    
    # 7. Summary and Recommendations
    print("7️⃣ Summary and Recommendations")
    print("-" * 30)
    
    print("📋 Release Summary:")
    print(f"   • Version: {version_analysis.current_version} → {version_analysis.recommended_version}")
    print(f"   • Overall Risk: {risk_assessment.overall_risk.value.upper()}")
    print(f"   • Changes: {len(changes)} total")
    print(f"   • Breaking Changes: {len([c for c in changes if c.breaking_change])}")
    print(f"   • Security Changes: {len([c for c in changes if c.security_impact])}")
    print()
    
    print("🎯 Key Recommendations:")
    if risk_assessment.overall_risk.value in ['high', 'critical']:
        print("   • Consider staged rollout with feature flags")
        print("   • Increase monitoring and alerting during deployment")
        print("   • Have rollback procedures ready and tested")
    
    if len([c for c in changes if c.breaking_change]) > 0:
        print("   • Coordinate with client teams for API changes")
        print("   • Update documentation and migration guides")
    
    if len([c for c in changes if c.security_impact]) > 0:
        print("   • Conduct security review before deployment")
        print("   • Monitor security metrics post-deployment")
    
    print("   • Deploy to staging environment first")
    print("   • Ensure team availability during deployment window")
    print()
    
    print("✅ Analysis Complete!")
    print(f"Recommendation: {'PROCEED WITH CAUTION' if risk_assessment.go_no_go_recommendation else 'CONSIDER DELAYING'}")


async def demo_hotfix_scenario():
    """Demonstrate hotfix scenario analysis"""
    
    print("\n" + "=" * 50)
    print("🚨 Hotfix Scenario Analysis")
    print("=" * 50)
    
    analyzer = ReleaseImpactAnalyzer()
    
    # Critical security hotfix
    hotfix_changes = [
        Change(
            id="hotfix-1",
            type=ChangeType.SECURITY_FIX,
            description="Critical authentication bypass vulnerability fix",
            files_changed=["src/auth/middleware.py"],
            lines_added=20,
            lines_removed=5,
            complexity_score=12.0,
            author="security_team",
            timestamp=datetime.now(),
            breaking_change=False,
            security_impact=True,
            performance_impact=False
        )
    ]
    
    print("🔥 Analyzing critical security hotfix...")
    
    version_analysis = await analyzer.analyze_semantic_versioning(hotfix_changes, "2.1.5")
    risk_assessment = await analyzer.assess_deployment_risk(hotfix_changes, DeploymentEnvironment.PRODUCTION)
    
    print(f"Version: {version_analysis.current_version} → {version_analysis.recommended_version}")
    print(f"Risk Level: {risk_assessment.overall_risk.value.upper()}")
    print(f"Recommendation: {'✅ DEPLOY IMMEDIATELY' if risk_assessment.go_no_go_recommendation else '❌ NEEDS REVIEW'}")
    print(f"Security Score Change: {risk_assessment.security_analysis.security_score_change:+.1f}")
    
    print("\nHotfix Deployment Strategy:")
    print("  1. Deploy to staging for smoke testing")
    print("  2. Prepare rollback procedures")
    print("  3. Deploy to production with monitoring")
    print("  4. Verify security fix effectiveness")
    print("  5. Communicate fix to stakeholders")


if __name__ == "__main__":
    asyncio.run(demo_release_impact_analysis())
    asyncio.run(demo_hotfix_scenario())