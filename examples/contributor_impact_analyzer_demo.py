"""
Contributor Impact Analyzer Demo

This example demonstrates how to use the ContributorImpactAnalyzer
for comprehensive contributor analysis and recognition.
"""

import asyncio
from datetime import datetime, timedelta
from devsync_ai.analytics.contributor_impact_analyzer import (
    ContributorImpactAnalyzer,
    ExpertiseLevel,
    AchievementType
)


async def demo_contributor_analysis():
    """Demonstrate contributor impact analysis capabilities"""
    
    print("🔍 Contributor Impact Analyzer Demo")
    print("=" * 50)
    
    # Initialize analyzer with team configuration
    team_config = {
        'privacy': {
            'anonymize_contributors': True,
            'data_retention_days': 90
        },
        'scoring_weights': {
            'code_quality': 0.3,
            'collaboration': 0.25,
            'mentoring': 0.2,
            'innovation': 0.15,
            'consistency': 0.1
        }
    }
    
    analyzer = ContributorImpactAnalyzer(
        github_service=None,  # Would be actual service in production
        jira_service=None,    # Would be actual service in production
        team_config=team_config
    )
    
    # Demo contributor
    contributor = "john.doe@company.com"
    
    print(f"\n📊 Analyzing contributor: {contributor}")
    print("-" * 30)
    
    # 1. Calculate contribution score
    print("\n1. Contribution Score Analysis")
    contribution_score = await analyzer.calculate_contribution_score(contributor)
    
    print(f"   Total Score: {contribution_score.total_score:.1f}/100")
    print(f"   Code Quality: {contribution_score.code_quality_score:.1f}")
    print(f"   Review Participation: {contribution_score.review_participation_score:.1f}")
    print(f"   Mentoring Impact: {contribution_score.mentoring_impact_score:.1f}")
    print(f"   Knowledge Sharing: {contribution_score.knowledge_sharing_score:.1f}")
    print(f"   Consistency: {contribution_score.consistency_score:.1f}")
    print(f"   Innovation: {contribution_score.innovation_score:.1f}")
    
    # 2. Identify expertise areas
    print("\n2. Expertise Areas")
    expertise_areas = await analyzer.identify_expertise_areas(contributor)
    
    for area in expertise_areas:
        level_emoji = {
            ExpertiseLevel.EXPERT: "🏆",
            ExpertiseLevel.ADVANCED: "⭐",
            ExpertiseLevel.INTERMEDIATE: "📈",
            ExpertiseLevel.NOVICE: "🌱"
        }
        
        print(f"   {level_emoji[area.level]} {area.domain}: {area.level.value}")
        print(f"      Confidence: {area.confidence:.1%}")
        print(f"      Evidence: {area.evidence_count} contributions")
        print(f"      Technologies: {', '.join(area.technologies)}")
    
    # 3. Collaboration network analysis
    print("\n3. Collaboration Network")
    collaboration_metrics = await analyzer.analyze_collaboration_network(contributor)
    
    print(f"   Influence Score: {collaboration_metrics.influence_score:.1f}")
    print(f"   Knowledge Sharing Frequency: {collaboration_metrics.knowledge_sharing_frequency}")
    print(f"   Mentoring Relationships: {collaboration_metrics.mentoring_relationships}")
    print(f"   Cross-Team Collaboration: {collaboration_metrics.cross_team_collaboration}")
    print(f"   Communication Effectiveness: {collaboration_metrics.communication_effectiveness:.1f}%")
    print(f"   Network Centrality: {collaboration_metrics.network_centrality:.1f}")
    
    # 4. Achievement recommendations
    print("\n4. Achievement Recommendations")
    achievements = await analyzer.generate_achievement_recommendations(contributor)
    
    achievement_emojis = {
        AchievementType.MILESTONE: "🎯",
        AchievementType.QUALITY: "💎",
        AchievementType.COLLABORATION: "🤝",
        AchievementType.INNOVATION: "💡",
        AchievementType.MENTORSHIP: "👨‍🏫",
        AchievementType.CONSISTENCY: "📅"
    }
    
    for achievement in achievements:
        emoji = achievement_emojis.get(achievement.type, "🏅")
        print(f"   {emoji} {achievement.title}")
        print(f"      {achievement.description}")
        print(f"      Earned: {achievement.earned_date.strftime('%Y-%m-%d')}")
    
    # 5. Skill development tracking
    print("\n5. Skill Development Tracking")
    skill_metrics = await analyzer.track_skill_development(contributor)
    
    for skill in skill_metrics:
        trajectory_emoji = {
            "improving": "📈",
            "stable": "➡️",
            "declining": "📉"
        }
        
        print(f"   {trajectory_emoji[skill.trajectory_direction]} {skill.skill_area}")
        print(f"      Current Level: {skill.current_level.value}")
        print(f"      Growth Rate: {skill.growth_rate:.1%}")
        print(f"      Trajectory: {skill.trajectory_direction}")
        if skill.time_to_next_level:
            print(f"      Time to Next Level: {skill.time_to_next_level} days")
        
        if skill.recommended_actions:
            print(f"      Recommendations:")
            for action in skill.recommended_actions:
                print(f"        • {action}")
    
    # 6. Get comprehensive profile
    print("\n6. Comprehensive Profile")
    profile = await analyzer.get_contributor_profile(contributor, privacy_level="team_visible")
    
    print(f"   Contributor ID: {profile.contributor_id}")
    print(f"   Privacy Level: {profile.privacy_level}")
    print(f"   Total Expertise Areas: {len(profile.expertise_areas)}")
    print(f"   Total Achievements: {len(profile.achievements)}")
    print(f"   Skill Development Areas: {len(profile.skill_development)}")


async def demo_team_dynamics():
    """Demonstrate team dynamics analysis"""
    
    print("\n\n🏢 Team Dynamics Analysis Demo")
    print("=" * 50)
    
    analyzer = ContributorImpactAnalyzer()
    
    # Demo team members
    team_members = [
        "alice@company.com",
        "bob@company.com", 
        "charlie@company.com",
        "diana@company.com"
    ]
    
    print(f"\n📈 Analyzing team dynamics for {len(team_members)} members")
    print("-" * 40)
    
    # Analyze team dynamics
    dynamics = await analyzer.analyze_team_dynamics(team_members)
    
    print("\n📊 Communication Patterns:")
    for pattern, score in dynamics.communication_patterns.items():
        print(f"   {pattern.replace('_', ' ').title()}: {score:.1f}%")
    
    print("\n🌐 Influence Network:")
    for member, influence in dynamics.influence_network.items():
        print(f"   {member}: {influence:.1f}")
    
    print("\n🔄 Knowledge Flow:")
    for flow_type, members in dynamics.knowledge_flow.items():
        print(f"   {flow_type.replace('_', ' ').title()}: {len(members)} members")
    
    print(f"\n🤝 Team Metrics:")
    print(f"   Collaboration Effectiveness: {dynamics.collaboration_effectiveness:.1f}%")
    print(f"   Team Cohesion Score: {dynamics.team_cohesion_score:.1f}%")
    
    if dynamics.bottlenecks:
        print(f"\n⚠️  Identified Bottlenecks:")
        for bottleneck in dynamics.bottlenecks:
            print(f"   • {bottleneck}")
    
    if dynamics.recommendations:
        print(f"\n💡 Recommendations:")
        for recommendation in dynamics.recommendations:
            print(f"   • {recommendation}")


async def demo_privacy_features():
    """Demonstrate privacy compliance features"""
    
    print("\n\n🔒 Privacy Compliance Demo")
    print("=" * 50)
    
    # Privacy-focused configuration
    privacy_config = {
        'privacy': {
            'anonymize_contributors': True,
            'data_retention_days': 30,
            'restrict_personal_data': True,
            'audit_access': True
        }
    }
    
    analyzer = ContributorImpactAnalyzer(team_config=privacy_config)
    
    contributor = "sensitive.user@company.com"
    
    print(f"\n🔐 Privacy-compliant analysis for: {contributor}")
    print("-" * 40)
    
    # Test anonymization
    anonymized_id = analyzer._anonymize_contributor_id(contributor)
    print(f"   Original ID: {contributor}")
    print(f"   Anonymized ID: {anonymized_id}")
    
    # Get profile with different privacy levels
    privacy_levels = ["private", "team_visible", "public"]
    
    for level in privacy_levels:
        print(f"\n   Privacy Level: {level}")
        profile = await analyzer.get_contributor_profile(contributor, privacy_level=level)
        
        print(f"     Contributor ID: {profile.contributor_id}")
        print(f"     Collaboration Partners: {len(profile.collaboration_metrics.collaboration_partners)}")
        print(f"     Achievements: {len(profile.achievements)}")
        
        if level == "private":
            print("     ✅ Personal data filtered for privacy")


async def main():
    """Run all demos"""
    try:
        await demo_contributor_analysis()
        await demo_team_dynamics()
        await demo_privacy_features()
        
        print("\n\n✅ Demo completed successfully!")
        print("\nKey Features Demonstrated:")
        print("• Comprehensive contribution scoring")
        print("• Expertise area identification")
        print("• Collaboration network analysis")
        print("• Achievement recognition system")
        print("• Skill development tracking")
        print("• Team dynamics analysis")
        print("• Privacy-compliant data handling")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(main())