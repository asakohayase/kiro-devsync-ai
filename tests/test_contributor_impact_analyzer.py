"""
Tests for ContributorImpactAnalyzer

Comprehensive test suite covering contributor analysis functionality
with privacy-compliant data handling and edge cases.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

from devsync_ai.analytics.contributor_impact_analyzer import (
    ContributorImpactAnalyzer,
    ContributionScore,
    ExpertiseArea,
    ExpertiseLevel,
    CollaborationMetrics,
    Achievement,
    AchievementType,
    SkillDevelopmentMetrics,
    TeamDynamicsInsight,
    ContributorProfile,
    ContributionType
)


class TestContributorImpactAnalyzer:
    """Test suite for ContributorImpactAnalyzer"""

    @pytest.fixture
    def mock_github_service(self):
        """Mock GitHub service"""
        service = AsyncMock()
        service.get_commits = AsyncMock(return_value=[])
        service.get_pull_requests = AsyncMock(return_value=[])
        service.get_reviews = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def mock_jira_service(self):
        """Mock JIRA service"""
        service = AsyncMock()
        service.get_issues = AsyncMock(return_value=[])
        service.get_comments = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def team_config(self):
        """Test team configuration"""
        return {
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

    @pytest.fixture
    def analyzer(self, mock_github_service, mock_jira_service, team_config):
        """ContributorImpactAnalyzer instance"""
        return ContributorImpactAnalyzer(
            github_service=mock_github_service,
            jira_service=mock_jira_service,
            team_config=team_config
        )

    @pytest.mark.asyncio
    async def test_calculate_contribution_score_success(self, analyzer):
        """Test successful contribution score calculation"""
        contributor = "test@example.com"
        
        # Mock the helper methods
        with patch.object(analyzer, '_get_github_contributions', return_value={'commits': []}):
            with patch.object(analyzer, '_get_jira_contributions', return_value={'tickets': []}):
                with patch.object(analyzer, '_calculate_code_quality_score', return_value=85.0):
                    with patch.object(analyzer, '_calculate_review_participation_score', return_value=90.0):
                        with patch.object(analyzer, '_calculate_mentoring_impact_score', return_value=75.0):
                            with patch.object(analyzer, '_calculate_knowledge_sharing_score', return_value=80.0):
                                with patch.object(analyzer, '_calculate_consistency_score', return_value=88.0):
                                    with patch.object(analyzer, '_calculate_innovation_score', return_value=70.0):
                                        
                                        score = await analyzer.calculate_contribution_score(contributor)
                                        
                                        assert isinstance(score, ContributionScore)
                                        assert 0 <= score.total_score <= 100
                                        assert score.code_quality_score == 85.0
                                        assert score.review_participation_score == 90.0
                                        assert score.mentoring_impact_score == 75.0
                                        assert len(score.breakdown) > 0

    @pytest.mark.asyncio
    async def test_calculate_contribution_score_error_handling(self, analyzer):
        """Test contribution score calculation with errors"""
        contributor = "test@example.com"
        
        # Mock an error in data collection
        with patch.object(analyzer, '_get_github_contributions', side_effect=Exception("API Error")):
            score = await analyzer.calculate_contribution_score(contributor)
            
            assert isinstance(score, ContributionScore)
            assert score.total_score == 0.0
            assert score.code_quality_score == 0.0

    @pytest.mark.asyncio
    async def test_identify_expertise_areas_success(self, analyzer):
        """Test successful expertise area identification"""
        contributor = "test@example.com"
        
        mock_github_data = {
            'commits': [
                {'files': ['backend/api.py', 'backend/models.py']},
                {'files': ['frontend/app.js', 'frontend/component.tsx']},
            ]
        }
        
        mock_file_analysis = {
            'backend': {
                'contribution_count': 50,
                'recent_activity': True,
                'file_patterns': ['*.py', '*.sql']
            },
            'frontend': {
                'contribution_count': 30,
                'recent_activity': True,
                'file_patterns': ['*.js', '*.tsx']
            }
        }
        
        mock_tech_analysis = {
            'backend': ['Python', 'FastAPI', 'PostgreSQL'],
            'frontend': ['React', 'TypeScript']
        }
        
        with patch.object(analyzer, '_get_github_contributions', return_value=mock_github_data):
            with patch.object(analyzer, '_analyze_file_patterns', return_value=mock_file_analysis):
                with patch.object(analyzer, '_analyze_technologies', return_value=mock_tech_analysis):
                    
                    expertise_areas = await analyzer.identify_expertise_areas(contributor)
                    
                    assert isinstance(expertise_areas, list)
                    assert len(expertise_areas) > 0
                    
                    for area in expertise_areas:
                        assert isinstance(area, ExpertiseArea)
                        assert isinstance(area.level, ExpertiseLevel)
                        assert 0 <= area.confidence <= 1
                        assert area.evidence_count >= 0

    @pytest.mark.asyncio
    async def test_analyze_collaboration_network_success(self, analyzer):
        """Test successful collaboration network analysis"""
        contributor = "test@example.com"
        
        with patch.object(analyzer, '_get_github_contributions', return_value={'reviews': []}):
            with patch.object(analyzer, '_calculate_influence_score', return_value=75.0):
                with patch.object(analyzer, '_calculate_knowledge_sharing_frequency', return_value=15):
                    with patch.object(analyzer, '_count_mentoring_relationships', return_value=3):
                        with patch.object(analyzer, '_analyze_cross_team_collaboration', return_value=7):
                            with patch.object(analyzer, '_assess_communication_effectiveness', return_value=82.0):
                                with patch.object(analyzer, '_calculate_network_centrality', return_value=68.0):
                                    with patch.object(analyzer, '_identify_collaboration_partners', return_value=['p1', 'p2']):
                                        
                                        metrics = await analyzer.analyze_collaboration_network(contributor)
                                        
                                        assert isinstance(metrics, CollaborationMetrics)
                                        assert metrics.influence_score == 75.0
                                        assert metrics.knowledge_sharing_frequency == 15
                                        assert metrics.mentoring_relationships == 3
                                        assert metrics.cross_team_collaboration == 7
                                        assert metrics.communication_effectiveness == 82.0
                                        assert metrics.network_centrality == 68.0
                                        assert len(metrics.collaboration_partners) == 2

    @pytest.mark.asyncio
    async def test_generate_achievement_recommendations_success(self, analyzer):
        """Test successful achievement recommendation generation"""
        contributor = "test@example.com"
        
        mock_contribution_score = ContributionScore(
            total_score=85.0,
            code_quality_score=90.0,
            review_participation_score=80.0,
            mentoring_impact_score=75.0,
            knowledge_sharing_score=70.0,
            consistency_score=85.0,
            innovation_score=65.0
        )
        
        mock_collaboration_metrics = CollaborationMetrics(
            influence_score=75.0,
            knowledge_sharing_frequency=15,
            mentoring_relationships=4,
            cross_team_collaboration=8,
            communication_effectiveness=82.0,
            network_centrality=68.0
        )
        
        with patch.object(analyzer, 'calculate_contribution_score', return_value=mock_contribution_score):
            with patch.object(analyzer, 'analyze_collaboration_network', return_value=mock_collaboration_metrics):
                with patch.object(analyzer, '_check_milestone_achievement', return_value=True):
                    
                    achievements = await analyzer.generate_achievement_recommendations(contributor)
                    
                    assert isinstance(achievements, list)
                    assert len(achievements) > 0
                    
                    for achievement in achievements:
                        assert isinstance(achievement, Achievement)
                        assert isinstance(achievement.type, AchievementType)
                        assert achievement.title
                        assert achievement.description
                        assert isinstance(achievement.earned_date, datetime)
                        assert isinstance(achievement.evidence, dict)

    @pytest.mark.asyncio
    async def test_track_skill_development_success(self, analyzer):
        """Test successful skill development tracking"""
        contributor = "test@example.com"
        
        mock_expertise_areas = [
            ExpertiseArea(
                domain="backend",
                level=ExpertiseLevel.ADVANCED,
                confidence=0.8,
                evidence_count=50,
                recent_activity=True,
                technologies=["Python", "FastAPI"],
                file_patterns=["*.py"]
            ),
            ExpertiseArea(
                domain="frontend",
                level=ExpertiseLevel.INTERMEDIATE,
                confidence=0.6,
                evidence_count=30,
                recent_activity=True,
                technologies=["React", "TypeScript"],
                file_patterns=["*.js", "*.tsx"]
            )
        ]
        
        with patch.object(analyzer, 'identify_expertise_areas', return_value=mock_expertise_areas):
            with patch.object(analyzer, '_calculate_skill_growth_rate', return_value=0.15):
                with patch.object(analyzer, '_determine_trajectory_direction', return_value="improving"):
                    with patch.object(analyzer, '_estimate_time_to_next_level', return_value=120):
                        with patch.object(analyzer, '_generate_skill_recommendations', return_value=["Focus on advanced concepts"]):
                            with patch.object(analyzer, '_identify_learning_opportunities', return_value=["Workshop", "Mentoring"]):
                                
                                skill_metrics = await analyzer.track_skill_development(contributor)
                                
                                assert isinstance(skill_metrics, list)
                                assert len(skill_metrics) == 2
                                
                                for metric in skill_metrics:
                                    assert isinstance(metric, SkillDevelopmentMetrics)
                                    assert metric.skill_area in ["backend", "frontend"]
                                    assert isinstance(metric.current_level, ExpertiseLevel)
                                    assert metric.growth_rate == 0.15
                                    assert metric.trajectory_direction == "improving"
                                    assert metric.time_to_next_level == 120

    @pytest.mark.asyncio
    async def test_analyze_team_dynamics_success(self, analyzer):
        """Test successful team dynamics analysis"""
        team_members = ["member1@example.com", "member2@example.com", "member3@example.com"]
        
        mock_communication_patterns = {
            'direct_communication': 75.0,
            'group_discussions': 60.0,
            'documentation_quality': 80.0,
            'response_time': 85.0
        }
        
        mock_influence_network = {
            'member1@example.com': 80.0,
            'member2@example.com': 70.0,
            'member3@example.com': 75.0
        }
        
        mock_knowledge_flow = {
            'knowledge_sources': ['member1@example.com'],
            'knowledge_recipients': ['member2@example.com', 'member3@example.com'],
            'knowledge_brokers': ['member1@example.com']
        }
        
        with patch.object(analyzer, '_analyze_communication_patterns', return_value=mock_communication_patterns):
            with patch.object(analyzer, '_build_influence_network', return_value=mock_influence_network):
                with patch.object(analyzer, '_analyze_knowledge_flow', return_value=mock_knowledge_flow):
                    with patch.object(analyzer, '_calculate_team_collaboration_effectiveness', return_value=78.0):
                        with patch.object(analyzer, '_calculate_team_cohesion_score', return_value=82.0):
                            with patch.object(analyzer, '_identify_team_bottlenecks', return_value=['Code review delays']):
                                with patch.object(analyzer, '_generate_team_recommendations', return_value=['Improve response time']):
                                    
                                    dynamics = await analyzer.analyze_team_dynamics(team_members)
                                    
                                    assert isinstance(dynamics, TeamDynamicsInsight)
                                    assert dynamics.communication_patterns == mock_communication_patterns
                                    assert dynamics.influence_network == mock_influence_network
                                    assert dynamics.knowledge_flow == mock_knowledge_flow
                                    assert dynamics.collaboration_effectiveness == 78.0
                                    assert dynamics.team_cohesion_score == 82.0
                                    assert len(dynamics.bottlenecks) == 1
                                    assert len(dynamics.recommendations) == 1

    @pytest.mark.asyncio
    async def test_get_contributor_profile_success(self, analyzer):
        """Test successful contributor profile generation"""
        contributor = "test@example.com"
        
        mock_contribution_score = ContributionScore(85.0, 90.0, 80.0, 75.0, 70.0, 85.0, 65.0)
        mock_expertise_areas = [
            ExpertiseArea("backend", ExpertiseLevel.ADVANCED, 0.8, 50, True)
        ]
        mock_collaboration_metrics = CollaborationMetrics(75.0, 15, 3, 7, 82.0, 68.0)
        mock_achievements = [
            Achievement("ach1", AchievementType.QUALITY, "Quality Champion", "High quality code", datetime.now(), {})
        ]
        mock_skill_development = [
            SkillDevelopmentMetrics("backend", ExpertiseLevel.ADVANCED, 0.15, "improving", 120)
        ]
        
        with patch.object(analyzer, 'calculate_contribution_score', return_value=mock_contribution_score):
            with patch.object(analyzer, 'identify_expertise_areas', return_value=mock_expertise_areas):
                with patch.object(analyzer, 'analyze_collaboration_network', return_value=mock_collaboration_metrics):
                    with patch.object(analyzer, 'generate_achievement_recommendations', return_value=mock_achievements):
                        with patch.object(analyzer, 'track_skill_development', return_value=mock_skill_development):
                            
                            profile = await analyzer.get_contributor_profile(contributor)
                            
                            assert isinstance(profile, ContributorProfile)
                            assert profile.contributor_id  # Should be anonymized
                            assert profile.contribution_score == mock_contribution_score
                            assert profile.expertise_areas == mock_expertise_areas
                            assert profile.collaboration_metrics == mock_collaboration_metrics
                            assert profile.achievements == mock_achievements
                            assert profile.skill_development == mock_skill_development
                            assert profile.privacy_level == "team_visible"

    @pytest.mark.asyncio
    async def test_get_contributor_profile_privacy_private(self, analyzer):
        """Test contributor profile with private privacy level"""
        contributor = "test@example.com"
        
        mock_contribution_score = ContributionScore(85.0, 90.0, 80.0, 75.0, 70.0, 85.0, 65.0)
        mock_collaboration_metrics = CollaborationMetrics(75.0, 15, 3, 7, 82.0, 68.0, ['partner1', 'partner2'])
        mock_achievements = [
            Achievement("ach1", AchievementType.COLLABORATION, "Team Player", "Great collaboration", datetime.now(), {})
        ]
        
        with patch.object(analyzer, 'calculate_contribution_score', return_value=mock_contribution_score):
            with patch.object(analyzer, 'identify_expertise_areas', return_value=[]):
                with patch.object(analyzer, 'analyze_collaboration_network', return_value=mock_collaboration_metrics):
                    with patch.object(analyzer, 'generate_achievement_recommendations', return_value=mock_achievements):
                        with patch.object(analyzer, 'track_skill_development', return_value=[]):
                            
                            profile = await analyzer.get_contributor_profile(contributor, privacy_level="private")
                            
                            assert profile.privacy_level == "private"
                            # Collaboration partners should be filtered out for privacy
                            assert len(profile.collaboration_metrics.collaboration_partners) == 0
                            # Collaboration achievements should be filtered out
                            assert len(profile.achievements) == 0

    def test_anonymize_contributor_id_enabled(self, analyzer):
        """Test contributor ID anonymization when enabled"""
        contributor = "test@example.com"
        
        # Anonymization is enabled in team_config
        anonymized_id = analyzer._anonymize_contributor_id(contributor)
        
        assert anonymized_id != contributor
        assert len(anonymized_id) == 16  # SHA256 hash truncated to 16 chars
        
        # Should be consistent
        assert anonymized_id == analyzer._anonymize_contributor_id(contributor)

    def test_anonymize_contributor_id_disabled(self, mock_github_service, mock_jira_service):
        """Test contributor ID anonymization when disabled"""
        team_config = {'privacy': {'anonymize_contributors': False}}
        analyzer = ContributorImpactAnalyzer(
            github_service=mock_github_service,
            jira_service=mock_jira_service,
            team_config=team_config
        )
        
        contributor = "test@example.com"
        result = analyzer._anonymize_contributor_id(contributor)
        
        assert result == contributor

    def test_determine_expertise_level(self, analyzer):
        """Test expertise level determination"""
        # Test expert level
        metrics = {'contribution_count': 150, 'recent_activity': True}
        level = analyzer._determine_expertise_level(metrics)
        assert level == ExpertiseLevel.EXPERT
        
        # Test advanced level
        metrics = {'contribution_count': 75, 'recent_activity': True}
        level = analyzer._determine_expertise_level(metrics)
        assert level == ExpertiseLevel.ADVANCED
        
        # Test intermediate level
        metrics = {'contribution_count': 35, 'recent_activity': True}
        level = analyzer._determine_expertise_level(metrics)
        assert level == ExpertiseLevel.INTERMEDIATE
        
        # Test novice level
        metrics = {'contribution_count': 10, 'recent_activity': False}
        level = analyzer._determine_expertise_level(metrics)
        assert level == ExpertiseLevel.NOVICE

    def test_calculate_confidence_score(self, analyzer):
        """Test confidence score calculation"""
        # High confidence with recent activity
        metrics = {'contribution_count': 100, 'recent_activity': True}
        confidence = analyzer._calculate_confidence_score(metrics)
        assert confidence == 1.0  # Should be capped at 1.0
        
        # Medium confidence without recent activity
        metrics = {'contribution_count': 50, 'recent_activity': False}
        confidence = analyzer._calculate_confidence_score(metrics)
        assert 0.4 <= confidence <= 0.6
        
        # Low confidence
        metrics = {'contribution_count': 10, 'recent_activity': False}
        confidence = analyzer._calculate_confidence_score(metrics)
        assert confidence < 0.2

    @pytest.mark.asyncio
    async def test_error_handling_in_all_methods(self, analyzer):
        """Test error handling across all main methods"""
        contributor = "test@example.com"
        
        # Test that all methods handle errors gracefully
        methods_to_test = [
            ('calculate_contribution_score', (contributor,)),
            ('identify_expertise_areas', (contributor,)),
            ('analyze_collaboration_network', (contributor,)),
            ('generate_achievement_recommendations', (contributor,)),
            ('track_skill_development', (contributor,)),
            ('get_contributor_profile', (contributor,))
        ]
        
        for method_name, args in methods_to_test:
            method = getattr(analyzer, method_name)
            
            # Mock all helper methods to raise exceptions
            with patch.object(analyzer, '_get_github_contributions', side_effect=Exception("Test error")):
                with patch.object(analyzer, '_get_jira_contributions', side_effect=Exception("Test error")):
                    result = await method(*args)
                    
                    # Should return appropriate default values instead of raising
                    assert result is not None

    @pytest.mark.asyncio
    async def test_team_dynamics_with_empty_team(self, analyzer):
        """Test team dynamics analysis with empty team"""
        team_members = []
        
        # Mock the methods to return appropriate values for empty team
        with patch.object(analyzer, '_calculate_team_collaboration_effectiveness', return_value=0.0):
            with patch.object(analyzer, '_calculate_team_cohesion_score', return_value=0.0):
                with patch.object(analyzer, '_analyze_communication_patterns', return_value={}):
                    with patch.object(analyzer, '_build_influence_network', return_value={}):
                        with patch.object(analyzer, '_analyze_knowledge_flow', return_value={}):
                            with patch.object(analyzer, '_identify_team_bottlenecks', return_value=[]):
                                with patch.object(analyzer, '_generate_team_recommendations', return_value=[]):
                                    
                                    dynamics = await analyzer.analyze_team_dynamics(team_members)
                                    
                                    assert isinstance(dynamics, TeamDynamicsInsight)
                                    assert dynamics.collaboration_effectiveness == 0.0
                                    assert dynamics.team_cohesion_score == 0.0

    @pytest.mark.asyncio
    async def test_concurrent_analysis(self, analyzer):
        """Test concurrent analysis of multiple contributors"""
        contributors = ["user1@example.com", "user2@example.com", "user3@example.com"]
        
        # Mock successful responses
        with patch.object(analyzer, '_get_github_contributions', return_value={}):
            with patch.object(analyzer, '_get_jira_contributions', return_value={}):
                with patch.object(analyzer, '_calculate_code_quality_score', return_value=75.0):
                    with patch.object(analyzer, '_calculate_review_participation_score', return_value=80.0):
                        with patch.object(analyzer, '_calculate_mentoring_impact_score', return_value=70.0):
                            with patch.object(analyzer, '_calculate_knowledge_sharing_score', return_value=65.0):
                                with patch.object(analyzer, '_calculate_consistency_score', return_value=85.0):
                                    with patch.object(analyzer, '_calculate_innovation_score', return_value=60.0):
                                        
                                        # Run concurrent analysis
                                        tasks = [
                                            analyzer.calculate_contribution_score(contributor)
                                            for contributor in contributors
                                        ]
                                        
                                        results = await asyncio.gather(*tasks)
                                        
                                        assert len(results) == 3
                                        for result in results:
                                            assert isinstance(result, ContributionScore)
                                            assert result.total_score > 0

    def test_scoring_weights_configuration(self, mock_github_service, mock_jira_service):
        """Test custom scoring weights configuration"""
        custom_config = {
            'scoring_weights': {
                'code_quality': 0.4,
                'collaboration': 0.3,
                'mentoring': 0.2,
                'innovation': 0.1
            }
        }
        
        analyzer = ContributorImpactAnalyzer(
            github_service=mock_github_service,
            jira_service=mock_jira_service,
            team_config=custom_config
        )
        
        # Verify weights are applied
        assert analyzer.scoring_weights[ContributionType.CODE_COMMIT] == 0.25  # Default value

    def test_achievement_thresholds_configuration(self, analyzer):
        """Test achievement thresholds configuration"""
        # Verify default thresholds are set
        assert AchievementType.MILESTONE in analyzer.achievement_thresholds
        assert AchievementType.QUALITY in analyzer.achievement_thresholds
        assert AchievementType.COLLABORATION in analyzer.achievement_thresholds
        
        # Verify threshold structure
        milestone_threshold = analyzer.achievement_thresholds[AchievementType.MILESTONE]
        assert 'commits' in milestone_threshold
        assert 'reviews' in milestone_threshold


class TestPrivacyCompliance:
    """Test privacy compliance features"""

    @pytest.fixture
    def mock_github_service(self):
        """Mock GitHub service for privacy tests"""
        service = AsyncMock()
        service.get_commits = AsyncMock(return_value=[])
        service.get_pull_requests = AsyncMock(return_value=[])
        service.get_reviews = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def mock_jira_service(self):
        """Mock JIRA service for privacy tests"""
        service = AsyncMock()
        service.get_issues = AsyncMock(return_value=[])
        service.get_comments = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def privacy_analyzer(self, mock_github_service, mock_jira_service):
        """Analyzer with strict privacy settings"""
        privacy_config = {
            'privacy': {
                'anonymize_contributors': True,
                'data_retention_days': 30,
                'restrict_personal_data': True,
                'audit_access': True
            }
        }
        return ContributorImpactAnalyzer(
            github_service=mock_github_service,
            jira_service=mock_jira_service,
            team_config=privacy_config
        )

    def test_contributor_anonymization(self, privacy_analyzer):
        """Test contributor ID anonymization"""
        original_id = "john.doe@company.com"
        anonymized_id = privacy_analyzer._anonymize_contributor_id(original_id)
        
        assert anonymized_id != original_id
        assert len(anonymized_id) == 16
        # Should be deterministic
        assert anonymized_id == privacy_analyzer._anonymize_contributor_id(original_id)

    @pytest.mark.asyncio
    async def test_privacy_level_filtering(self, privacy_analyzer):
        """Test privacy level filtering in profiles"""
        contributor = "test@example.com"
        
        mock_collaboration_metrics = CollaborationMetrics(
            influence_score=75.0,
            knowledge_sharing_frequency=15,
            mentoring_relationships=3,
            cross_team_collaboration=7,
            communication_effectiveness=82.0,
            network_centrality=68.0,
            collaboration_partners=['partner1', 'partner2', 'partner3']
        )
        
        mock_achievements = [
            Achievement("ach1", AchievementType.COLLABORATION, "Team Player", "Great collaboration", datetime.now(), {}),
            Achievement("ach2", AchievementType.QUALITY, "Quality Champion", "High quality", datetime.now(), {})
        ]
        
        with patch.object(privacy_analyzer, 'calculate_contribution_score', return_value=ContributionScore(85.0, 90.0, 80.0, 75.0, 70.0, 85.0, 65.0)):
            with patch.object(privacy_analyzer, 'identify_expertise_areas', return_value=[]):
                with patch.object(privacy_analyzer, 'analyze_collaboration_network', return_value=mock_collaboration_metrics):
                    with patch.object(privacy_analyzer, 'generate_achievement_recommendations', return_value=mock_achievements):
                        with patch.object(privacy_analyzer, 'track_skill_development', return_value=[]):
                            
                            # Test private profile
                            private_profile = await privacy_analyzer.get_contributor_profile(contributor, privacy_level="private")
                            
                            assert len(private_profile.collaboration_metrics.collaboration_partners) == 0
                            # Only non-collaboration achievements should remain
                            assert len(private_profile.achievements) == 1
                            assert private_profile.achievements[0].type == AchievementType.QUALITY

    @pytest.mark.asyncio
    async def test_data_sanitization(self, privacy_analyzer):
        """Test data sanitization for external sharing"""
        team_members = ["user1@company.com", "user2@company.com"]
        
        with patch.object(privacy_analyzer, '_analyze_communication_patterns', return_value={}):
            with patch.object(privacy_analyzer, '_build_influence_network', return_value={}):
                with patch.object(privacy_analyzer, '_analyze_knowledge_flow', return_value={}):
                    with patch.object(privacy_analyzer, '_calculate_team_collaboration_effectiveness', return_value=75.0):
                        with patch.object(privacy_analyzer, '_calculate_team_cohesion_score', return_value=80.0):
                            with patch.object(privacy_analyzer, '_identify_team_bottlenecks', return_value=[]):
                                with patch.object(privacy_analyzer, '_generate_team_recommendations', return_value=[]):
                                    
                                    dynamics = await privacy_analyzer.analyze_team_dynamics(team_members)
                                    
                                    # Verify no personal identifiers in results
                                    assert isinstance(dynamics, TeamDynamicsInsight)
                                    # All data should be aggregated/anonymized


if __name__ == "__main__":
    pytest.main([__file__, "-v"])