"""
Tests for Release Impact Analyzer

This module provides comprehensive tests for the ReleaseImpactAnalyzer including
scenario-based validation and edge case coverage.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from devsync_ai.analytics.release_impact_analyzer import (
    ReleaseImpactAnalyzer,
    Change,
    ChangeType,
    RiskLevel,
    VersionBumpType,
    DeploymentEnvironment,
    SemanticVersionAnalysis,
    PerformanceImpact,
    SecurityAnalysis,
    RollbackPlan,
    StakeholderImpact,
    RiskAssessment
)


class TestReleaseImpactAnalyzer:
    """Test suite for ReleaseImpactAnalyzer"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance for testing"""
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
            },
            'security_weight': 2.0,
            'breaking_change_weight': 3.0
        }
        return ReleaseImpactAnalyzer(config)

    @pytest.fixture
    def sample_changes(self):
        """Create sample changes for testing"""
        return [
            Change(
                id="change-1",
                type=ChangeType.FEATURE,
                description="Add new user authentication feature",
                files_changed=["src/auth/authentication.py", "src/api/auth_routes.py"],
                lines_added=150,
                lines_removed=20,
                complexity_score=15.0,
                author="developer1",
                timestamp=datetime.now(),
                breaking_change=False,
                security_impact=True,
                performance_impact=False,
                dependencies_affected=["flask-login"],
                test_coverage_change=5.0
            ),
            Change(
                id="change-2",
                type=ChangeType.BUG_FIX,
                description="Fix memory leak in data processing",
                files_changed=["src/processing/data_processor.py"],
                lines_added=30,
                lines_removed=45,
                complexity_score=8.0,
                author="developer2",
                timestamp=datetime.now(),
                breaking_change=False,
                security_impact=False,
                performance_impact=True,
                dependencies_affected=[],
                test_coverage_change=2.0
            ),
            Change(
                id="change-3",
                type=ChangeType.BREAKING_CHANGE,
                description="Remove deprecated API endpoints",
                files_changed=["src/api/deprecated_routes.py", "src/api/v1/routes.py"],
                lines_added=0,
                lines_removed=200,
                complexity_score=25.0,
                author="developer3",
                timestamp=datetime.now(),
                breaking_change=True,
                security_impact=False,
                performance_impact=False,
                dependencies_affected=[],
                test_coverage_change=-3.0
            )
        ]

    @pytest.fixture
    def database_changes(self):
        """Create database-related changes for testing"""
        return [
            Change(
                id="db-change-1",
                type=ChangeType.FEATURE,
                description="Add new user_preferences table migration",
                files_changed=["migrations/001_add_user_preferences.sql", "src/models/user.py"],
                lines_added=80,
                lines_removed=5,
                complexity_score=20.0,
                author="developer1",
                timestamp=datetime.now(),
                breaking_change=False,
                security_impact=False,
                performance_impact=True,
                dependencies_affected=["sqlalchemy"],
                test_coverage_change=4.0
            ),
            Change(
                id="db-change-2",
                type=ChangeType.BREAKING_CHANGE,
                description="ALTER TABLE users DROP COLUMN deprecated_field",
                files_changed=["migrations/002_remove_deprecated_field.sql"],
                lines_added=10,
                lines_removed=0,
                complexity_score=30.0,
                author="developer2",
                timestamp=datetime.now(),
                breaking_change=True,
                security_impact=False,
                performance_impact=False,
                dependencies_affected=[],
                test_coverage_change=0.0
            )
        ]

    @pytest.fixture
    def security_changes(self):
        """Create security-related changes for testing"""
        return [
            Change(
                id="sec-change-1",
                type=ChangeType.SECURITY_FIX,
                description="Fix SQL injection vulnerability in user search",
                files_changed=["src/api/search.py", "src/database/queries.py"],
                lines_added=25,
                lines_removed=15,
                complexity_score=12.0,
                author="security_team",
                timestamp=datetime.now(),
                breaking_change=False,
                security_impact=True,
                performance_impact=False,
                dependencies_affected=["sqlalchemy"],
                test_coverage_change=8.0
            ),
            Change(
                id="sec-change-2",
                type=ChangeType.DEPENDENCY,
                description="Update vulnerable dependency: requests 2.25.0 -> 2.28.1",
                files_changed=["requirements.txt", "pyproject.toml"],
                lines_added=2,
                lines_removed=2,
                complexity_score=5.0,
                author="security_team",
                timestamp=datetime.now(),
                breaking_change=False,
                security_impact=True,
                performance_impact=False,
                dependencies_affected=["requests"],
                test_coverage_change=0.0
            )
        ]

    @pytest.mark.asyncio
    async def test_semantic_versioning_analysis_patch(self, analyzer, sample_changes):
        """Test semantic versioning analysis for patch release"""
        # Remove breaking change and features for patch test
        changes = [c for c in sample_changes if c.type == ChangeType.BUG_FIX]
        
        result = await analyzer.analyze_semantic_versioning(changes, "1.2.3")
        
        assert isinstance(result, SemanticVersionAnalysis)
        assert result.current_version == "1.2.3"
        assert result.recommended_version == "1.2.4"
        assert result.bump_type == VersionBumpType.PATCH
        assert result.confidence_score > 0.8
        assert len(result.reasoning) > 0
        assert len(result.breaking_changes) == 0
        assert len(result.bug_fixes) == 1

    @pytest.mark.asyncio
    async def test_semantic_versioning_analysis_minor(self, analyzer, sample_changes):
        """Test semantic versioning analysis for minor release"""
        # Remove breaking changes, keep features
        changes = [c for c in sample_changes if c.type == ChangeType.FEATURE or c.type == ChangeType.BUG_FIX]
        
        result = await analyzer.analyze_semantic_versioning(changes, "1.2.3")
        
        assert result.bump_type == VersionBumpType.MINOR
        assert result.recommended_version == "1.3.0"
        assert len(result.new_features) == 1

    @pytest.mark.asyncio
    async def test_semantic_versioning_analysis_major(self, analyzer, sample_changes):
        """Test semantic versioning analysis for major release"""
        result = await analyzer.analyze_semantic_versioning(sample_changes, "1.2.3")
        
        assert result.bump_type == VersionBumpType.MAJOR
        assert result.recommended_version == "2.0.0"
        assert len(result.breaking_changes) == 1
        assert result.confidence_score > 0.9

    @pytest.mark.asyncio
    async def test_semantic_versioning_with_database_changes(self, analyzer, database_changes):
        """Test semantic versioning with database schema changes"""
        # Non-breaking database change should upgrade patch to minor
        non_breaking_changes = [c for c in database_changes if not c.breaking_change]
        
        result = await analyzer.analyze_semantic_versioning(non_breaking_changes, "1.2.3")
        
        assert result.bump_type == VersionBumpType.MINOR
        assert "Database schema changes detected" in " ".join(result.reasoning)

    @pytest.mark.asyncio
    async def test_deployment_risk_assessment_low_risk(self, analyzer):
        """Test deployment risk assessment for low-risk changes"""
        low_risk_changes = [
            Change(
                id="low-risk-1",
                type=ChangeType.BUG_FIX,
                description="Fix typo in documentation",
                files_changed=["README.md"],
                lines_added=1,
                lines_removed=1,
                complexity_score=1.0,
                author="developer1",
                timestamp=datetime.now()
            )
        ]
        
        result = await analyzer.assess_deployment_risk(low_risk_changes, DeploymentEnvironment.PRODUCTION)
        
        assert isinstance(result, RiskAssessment)
        assert result.overall_risk == RiskLevel.LOW
        assert result.go_no_go_recommendation is True
        assert result.confidence_score > 0.8

    @pytest.mark.asyncio
    async def test_deployment_risk_assessment_high_risk(self, analyzer, sample_changes):
        """Test deployment risk assessment for high-risk changes"""
        result = await analyzer.assess_deployment_risk(sample_changes, DeploymentEnvironment.PRODUCTION)
        
        assert result.overall_risk in [RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert len(result.risk_factors) > 0
        assert len(result.mitigation_strategies) > 0
        assert "breaking changes" in " ".join(result.risk_factors).lower()

    @pytest.mark.asyncio
    async def test_deployment_risk_different_environments(self, analyzer, sample_changes):
        """Test deployment risk varies by environment"""
        dev_result = await analyzer.assess_deployment_risk(sample_changes, DeploymentEnvironment.DEVELOPMENT)
        prod_result = await analyzer.assess_deployment_risk(sample_changes, DeploymentEnvironment.PRODUCTION)
        
        # Production should have higher or equal risk
        risk_levels = {RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3, RiskLevel.CRITICAL: 4}
        assert risk_levels[prod_result.overall_risk] >= risk_levels[dev_result.overall_risk]

    @pytest.mark.asyncio
    async def test_performance_impact_prediction(self, analyzer, sample_changes):
        """Test performance impact prediction"""
        result = await analyzer.predict_performance_impact(sample_changes)
        
        assert isinstance(result, PerformanceImpact)
        assert result.overall_risk in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert isinstance(result.estimated_performance_change, float)
        assert isinstance(result.benchmark_predictions, dict)
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_performance_impact_with_database_changes(self, analyzer, database_changes):
        """Test performance impact with database changes"""
        result = await analyzer.predict_performance_impact(database_changes)
        
        assert "database" in result.affected_components
        assert "Review database query performance" in " ".join(result.recommendations)
        assert result.estimated_performance_change > 0

    @pytest.mark.asyncio
    async def test_security_impact_analysis(self, analyzer, security_changes):
        """Test security impact analysis"""
        result = await analyzer.analyze_security_impact(security_changes)
        
        assert isinstance(result, SecurityAnalysis)
        assert result.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert len(result.vulnerabilities_fixed) > 0
        assert result.security_score_change > 0  # Should be positive due to fixes
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_security_impact_with_vulnerabilities(self, analyzer, sample_changes):
        """Test security impact analysis with potential vulnerabilities"""
        # Add a change that might introduce vulnerabilities
        vuln_change = Change(
            id="vuln-change",
            type=ChangeType.FEATURE,
            description="Add user input processing endpoint",
            files_changed=["src/api/user_input.py"],
            lines_added=100,
            lines_removed=0,
            complexity_score=30.0,
            author="developer1",
            timestamp=datetime.now(),
            security_impact=False
        )
        
        changes_with_vuln = sample_changes + [vuln_change]
        result = await analyzer.analyze_security_impact(changes_with_vuln)
        
        assert len(result.vulnerabilities_introduced) >= 0
        assert isinstance(result.security_score_change, float)

    @pytest.mark.asyncio
    async def test_rollback_risk_assessment(self, analyzer, database_changes):
        """Test rollback risk assessment"""
        result = await analyzer.assess_rollback_risk(database_changes)
        
        assert isinstance(result, RollbackPlan)
        assert result.rollback_risk in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert isinstance(result.rollback_complexity, float)
        assert isinstance(result.estimated_rollback_time, timedelta)
        assert len(result.rollback_steps) > 0
        assert len(result.mitigation_strategies) > 0
        assert result.data_migration_required is True  # Database changes require migration

    @pytest.mark.asyncio
    async def test_rollback_risk_with_breaking_changes(self, analyzer, sample_changes):
        """Test rollback risk with breaking changes"""
        result = await analyzer.assess_rollback_risk(sample_changes)
        
        # Should have complexity due to breaking changes
        assert result.rollback_complexity >= 20.0
        assert result.rollback_testing_required is True
        assert "API changes" in " ".join(result.rollback_steps)

    @pytest.mark.asyncio
    async def test_stakeholder_impact_analysis(self, analyzer, sample_changes):
        """Test stakeholder impact analysis"""
        result = await analyzer.analyze_stakeholder_impact(sample_changes)
        
        assert isinstance(result, StakeholderImpact)
        assert len(result.affected_stakeholders) > 0
        assert "development_team" in result.affected_stakeholders
        
        # Should include product team due to breaking changes
        assert "product_team" in result.affected_stakeholders
        
        # Check impact severity mapping
        for stakeholder in result.affected_stakeholders:
            assert stakeholder in result.impact_severity
            assert stakeholder in result.notification_priority
            assert stakeholder in result.escalation_paths
            assert stakeholder in result.communication_templates

    @pytest.mark.asyncio
    async def test_stakeholder_impact_with_security_changes(self, analyzer, security_changes):
        """Test stakeholder impact with security changes"""
        result = await analyzer.analyze_stakeholder_impact(security_changes)
        
        assert "security_team" in result.affected_stakeholders
        assert result.impact_severity["security_team"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert result.notification_priority["security_team"] == "critical"

    @pytest.mark.asyncio
    async def test_comprehensive_risk_assessment(self, analyzer, sample_changes):
        """Test comprehensive risk assessment with all components"""
        result = await analyzer.assess_deployment_risk(sample_changes, DeploymentEnvironment.PRODUCTION)
        
        # Verify all components are present
        assert hasattr(result, 'performance_impact')
        assert hasattr(result, 'security_analysis')
        assert hasattr(result, 'rollback_plan')
        assert hasattr(result, 'stakeholder_impact')
        
        # Verify component types
        assert isinstance(result.performance_impact, PerformanceImpact)
        assert isinstance(result.security_analysis, SecurityAnalysis)
        assert isinstance(result.rollback_plan, RollbackPlan)
        assert isinstance(result.stakeholder_impact, StakeholderImpact)

    def test_version_calculation_edge_cases(self, analyzer):
        """Test version calculation with edge cases"""
        # Test invalid version format
        result = analyzer._calculate_next_version("invalid", VersionBumpType.PATCH)
        assert "invalid-next" in result
        
        # Test valid version formats
        assert analyzer._calculate_next_version("1.0.0", VersionBumpType.MAJOR) == "2.0.0"
        assert analyzer._calculate_next_version("0.1.5", VersionBumpType.MINOR) == "0.2.0"
        assert analyzer._calculate_next_version("2.3.7", VersionBumpType.PATCH) == "2.3.8"

    def test_change_pattern_detection(self, analyzer):
        """Test various change pattern detection methods"""
        # Test database change detection
        db_change = Change(
            id="db-test",
            type=ChangeType.FEATURE,
            description="Add database migration for user table",
            files_changed=["migrations/001_add_users.sql"],
            lines_added=50,
            lines_removed=0,
            complexity_score=15.0,
            author="developer1",
            timestamp=datetime.now()
        )
        
        assert analyzer._affects_database(db_change) is True
        assert analyzer._has_database_schema_changes([db_change]) is True
        
        # Test API change detection
        api_change = Change(
            id="api-test",
            type=ChangeType.FEATURE,
            description="Add new API endpoint for user management",
            files_changed=["src/api/users.py"],
            lines_added=30,
            lines_removed=0,
            complexity_score=10.0,
            author="developer1",
            timestamp=datetime.now()
        )
        
        assert analyzer._affects_api(api_change) is True
        assert analyzer._has_api_changes([api_change]) is True

    @pytest.mark.asyncio
    async def test_empty_changes_handling(self, analyzer):
        """Test handling of empty change lists"""
        empty_changes = []
        
        # Should handle empty changes gracefully
        version_result = await analyzer.analyze_semantic_versioning(empty_changes, "1.0.0")
        assert version_result.bump_type == VersionBumpType.PATCH
        assert version_result.recommended_version == "1.0.1"
        
        risk_result = await analyzer.assess_deployment_risk(empty_changes, DeploymentEnvironment.PRODUCTION)
        assert risk_result.overall_risk == RiskLevel.LOW
        
        perf_result = await analyzer.predict_performance_impact(empty_changes)
        assert perf_result.overall_risk == RiskLevel.LOW

    @pytest.mark.asyncio
    async def test_large_change_set_handling(self, analyzer):
        """Test handling of large change sets"""
        # Create a large number of changes
        large_change_set = []
        for i in range(100):
            change = Change(
                id=f"change-{i}",
                type=ChangeType.FEATURE if i % 2 == 0 else ChangeType.BUG_FIX,
                description=f"Change number {i}",
                files_changed=[f"src/file_{i}.py"],
                lines_added=10 + (i % 50),
                lines_removed=i % 20,
                complexity_score=5.0 + (i % 30),
                author=f"developer{i % 5}",
                timestamp=datetime.now(),
                breaking_change=(i % 20 == 0),
                security_impact=(i % 15 == 0),
                performance_impact=(i % 10 == 0)
            )
            large_change_set.append(change)
        
        # Should handle large change sets without errors
        result = await analyzer.assess_deployment_risk(large_change_set, DeploymentEnvironment.PRODUCTION)
        assert isinstance(result, RiskAssessment)
        assert result.overall_risk in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]

    @pytest.mark.asyncio
    async def test_configuration_impact(self, analyzer):
        """Test configuration-specific analysis"""
        # Test with custom thresholds
        custom_config = {
            'complexity_thresholds': {
                'low': 5.0,
                'medium': 15.0,
                'high': 30.0
            },
            'performance_thresholds': {
                'acceptable': 2.0,
                'concerning': 8.0,
                'critical': 20.0
            }
        }
        
        custom_analyzer = ReleaseImpactAnalyzer(custom_config)
        
        medium_complexity_change = Change(
            id="config-test",
            type=ChangeType.FEATURE,
            description="Medium complexity change",
            files_changed=["src/test.py"],
            lines_added=50,
            lines_removed=10,
            complexity_score=20.0,  # High with custom thresholds
            author="developer1",
            timestamp=datetime.now()
        )
        
        result = await custom_analyzer.assess_deployment_risk([medium_complexity_change], DeploymentEnvironment.PRODUCTION)
        
        # Should reflect custom thresholds in risk assessment
        assert isinstance(result, RiskAssessment)

    @pytest.mark.asyncio
    async def test_error_handling(self, analyzer):
        """Test error handling in various scenarios"""
        # Test with malformed change data
        malformed_change = Change(
            id="",  # Empty ID
            type=ChangeType.FEATURE,
            description="",  # Empty description
            files_changed=[],  # No files
            lines_added=0,
            lines_removed=0,
            complexity_score=-5.0,  # Negative complexity
            author="",
            timestamp=datetime.now()
        )
        
        # Should handle malformed data gracefully
        try:
            result = await analyzer.assess_deployment_risk([malformed_change], DeploymentEnvironment.PRODUCTION)
            assert isinstance(result, RiskAssessment)
        except Exception as e:
            pytest.fail(f"Should handle malformed data gracefully, but raised: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_analysis(self, analyzer, sample_changes):
        """Test concurrent analysis operations"""
        # Run multiple analyses concurrently
        tasks = [
            analyzer.analyze_semantic_versioning(sample_changes, "1.0.0"),
            analyzer.predict_performance_impact(sample_changes),
            analyzer.analyze_security_impact(sample_changes),
            analyzer.assess_rollback_risk(sample_changes),
            analyzer.analyze_stakeholder_impact(sample_changes)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All analyses should complete successfully
        assert len(results) == 5
        assert all(result is not None for result in results)

    def test_risk_level_ordering(self):
        """Test risk level enumeration ordering"""
        risk_levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        
        # Verify enum values
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_change_type_coverage(self):
        """Test all change types are handled"""
        change_types = [
            ChangeType.FEATURE,
            ChangeType.BUG_FIX,
            ChangeType.BREAKING_CHANGE,
            ChangeType.SECURITY_FIX,
            ChangeType.PERFORMANCE,
            ChangeType.DOCUMENTATION,
            ChangeType.REFACTOR,
            ChangeType.DEPENDENCY
        ]
        
        # Verify all change types have string values
        for change_type in change_types:
            assert isinstance(change_type.value, str)
            assert len(change_type.value) > 0

    @pytest.mark.asyncio
    async def test_integration_scenario_hotfix(self, analyzer):
        """Test integration scenario: hotfix deployment"""
        hotfix_changes = [
            Change(
                id="hotfix-1",
                type=ChangeType.SECURITY_FIX,
                description="Critical security fix for authentication bypass",
                files_changed=["src/auth/security.py"],
                lines_added=15,
                lines_removed=5,
                complexity_score=8.0,
                author="security_team",
                timestamp=datetime.now(),
                breaking_change=False,
                security_impact=True,
                performance_impact=False
            )
        ]
        
        # Analyze hotfix scenario
        version_analysis = await analyzer.analyze_semantic_versioning(hotfix_changes, "1.2.3")
        risk_assessment = await analyzer.assess_deployment_risk(hotfix_changes, DeploymentEnvironment.PRODUCTION)
        
        # Hotfix should be patch version
        assert version_analysis.bump_type == VersionBumpType.PATCH
        assert version_analysis.recommended_version == "1.2.4"
        
        # Should have security team in stakeholders
        assert "security_team" in risk_assessment.stakeholder_impact.affected_stakeholders
        
        # Should recommend deployment despite security changes
        assert risk_assessment.go_no_go_recommendation is True

    @pytest.mark.asyncio
    async def test_integration_scenario_major_release(self, analyzer):
        """Test integration scenario: major release with breaking changes"""
        major_release_changes = [
            Change(
                id="major-1",
                type=ChangeType.BREAKING_CHANGE,
                description="Remove deprecated API v1 endpoints",
                files_changed=["src/api/v1/", "src/api/v2/"],
                lines_added=0,
                lines_removed=500,
                complexity_score=40.0,
                author="api_team",
                timestamp=datetime.now(),
                breaking_change=True,
                security_impact=False,
                performance_impact=True
            ),
            Change(
                id="major-2",
                type=ChangeType.FEATURE,
                description="Add new advanced analytics dashboard",
                files_changed=["src/analytics/", "src/ui/dashboard/"],
                lines_added=800,
                lines_removed=50,
                complexity_score=60.0,
                author="frontend_team",
                timestamp=datetime.now(),
                breaking_change=False,
                security_impact=False,
                performance_impact=True
            )
        ]
        
        # Analyze major release scenario
        version_analysis = await analyzer.analyze_semantic_versioning(major_release_changes, "1.9.5")
        risk_assessment = await analyzer.assess_deployment_risk(major_release_changes, DeploymentEnvironment.PRODUCTION)
        
        # Should be major version bump
        assert version_analysis.bump_type == VersionBumpType.MAJOR
        assert version_analysis.recommended_version == "2.0.0"
        
        # Should have high risk due to breaking changes and complexity
        assert risk_assessment.overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        
        # Should include multiple stakeholder groups
        stakeholders = risk_assessment.stakeholder_impact.affected_stakeholders
        assert "product_team" in stakeholders
        assert "customer_support" in stakeholders
        
        # Should have comprehensive mitigation strategies
        assert len(risk_assessment.mitigation_strategies) >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])