"""
Release Impact Assessment and Risk Engine

This module provides comprehensive release impact analysis including semantic versioning,
deployment risk assessment, performance impact prediction, security analysis, rollback
risk assessment, and stakeholder impact analysis.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from pathlib import Path
import json
import hashlib

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VersionBumpType(Enum):
    """Semantic version bump types"""
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"


class ChangeType(Enum):
    """Types of changes in a release"""
    FEATURE = "feature"
    BUG_FIX = "bug_fix"
    BREAKING_CHANGE = "breaking_change"
    SECURITY_FIX = "security_fix"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    REFACTOR = "refactor"
    DEPENDENCY = "dependency"


class DeploymentEnvironment(Enum):
    """Deployment environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class Change:
    """Represents a single change in a release"""
    id: str
    type: ChangeType
    description: str
    files_changed: List[str]
    lines_added: int
    lines_removed: int
    complexity_score: float
    author: str
    timestamp: datetime
    breaking_change: bool = False
    security_impact: bool = False
    performance_impact: bool = False
    dependencies_affected: List[str] = field(default_factory=list)
    test_coverage_change: float = 0.0


@dataclass
class SemanticVersionAnalysis:
    """Results of semantic version analysis"""
    current_version: str
    recommended_version: str
    bump_type: VersionBumpType
    confidence_score: float
    reasoning: List[str]
    breaking_changes: List[Change]
    new_features: List[Change]
    bug_fixes: List[Change]


@dataclass
class PerformanceImpact:
    """Performance impact assessment"""
    overall_risk: RiskLevel
    affected_components: List[str]
    estimated_performance_change: float  # Percentage change
    benchmark_predictions: Dict[str, float]
    memory_impact: Optional[float]
    cpu_impact: Optional[float]
    io_impact: Optional[float]
    recommendations: List[str]


@dataclass
class SecurityAnalysis:
    """Security impact analysis results"""
    risk_level: RiskLevel
    vulnerabilities_introduced: List[Dict[str, Any]]
    vulnerabilities_fixed: List[Dict[str, Any]]
    dependency_vulnerabilities: List[Dict[str, Any]]
    security_score_change: float
    compliance_impact: List[str]
    recommendations: List[str]


@dataclass
class RollbackPlan:
    """Rollback risk assessment and plan"""
    rollback_risk: RiskLevel
    rollback_complexity: float
    estimated_rollback_time: timedelta
    rollback_steps: List[str]
    data_migration_required: bool
    rollback_testing_required: bool
    mitigation_strategies: List[str]
    dependencies_affected: List[str]


@dataclass
class StakeholderImpact:
    """Stakeholder impact analysis"""
    affected_stakeholders: List[str]
    impact_severity: Dict[str, RiskLevel]
    notification_priority: Dict[str, str]
    escalation_paths: Dict[str, List[str]]
    communication_templates: Dict[str, str]
    timeline_impact: Dict[str, timedelta]


@dataclass
class RiskAssessment:
    """Comprehensive risk assessment for a release"""
    overall_risk: RiskLevel
    deployment_risk: RiskLevel
    performance_impact: PerformanceImpact
    security_analysis: SecurityAnalysis
    rollback_plan: RollbackPlan
    stakeholder_impact: StakeholderImpact
    risk_factors: List[str]
    mitigation_strategies: List[str]
    go_no_go_recommendation: bool
    confidence_score: float


class ReleaseImpactAnalyzer:
    """
    Comprehensive release impact analysis engine that provides semantic versioning,
    risk assessment, performance prediction, security analysis, and stakeholder impact.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the release impact analyzer"""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuration defaults
        self.complexity_thresholds = self.config.get('complexity_thresholds', {
            'low': 10.0,
            'medium': 25.0,
            'high': 50.0
        })
        
        self.performance_thresholds = self.config.get('performance_thresholds', {
            'acceptable': 5.0,  # 5% performance degradation
            'concerning': 15.0,  # 15% performance degradation
            'critical': 30.0  # 30% performance degradation
        })
        
        self.security_weight = self.config.get('security_weight', 2.0)
        self.breaking_change_weight = self.config.get('breaking_change_weight', 3.0)
        
        # Historical data cache
        self._historical_data: Dict[str, Any] = {}
        self._benchmark_data: Dict[str, Any] = {}

    async def analyze_semantic_versioning(self, changes: List[Change], current_version: str) -> SemanticVersionAnalysis:
        """
        Analyze changes and recommend semantic version bump
        
        Args:
            changes: List of changes in the release
            current_version: Current version string
            
        Returns:
            SemanticVersionAnalysis with version recommendations
        """
        try:
            self.logger.info(f"Analyzing semantic versioning for {len(changes)} changes")
            
            # Categorize changes
            breaking_changes = [c for c in changes if c.breaking_change]
            new_features = [c for c in changes if c.type == ChangeType.FEATURE and not c.breaking_change]
            bug_fixes = [c for c in changes if c.type == ChangeType.BUG_FIX]
            security_fixes = [c for c in changes if c.type == ChangeType.SECURITY_FIX]
            
            # Determine version bump type
            bump_type = VersionBumpType.PATCH
            reasoning = []
            confidence_score = 0.8
            
            if breaking_changes:
                bump_type = VersionBumpType.MAJOR
                reasoning.append(f"Found {len(breaking_changes)} breaking changes requiring major version bump")
                confidence_score = 0.95
            elif new_features:
                bump_type = VersionBumpType.MINOR
                reasoning.append(f"Found {len(new_features)} new features requiring minor version bump")
                confidence_score = 0.9
            elif bug_fixes or security_fixes:
                bump_type = VersionBumpType.PATCH
                reasoning.append(f"Found {len(bug_fixes)} bug fixes and {len(security_fixes)} security fixes")
                confidence_score = 0.85
            
            # Calculate recommended version
            recommended_version = self._calculate_next_version(current_version, bump_type)
            
            # Additional analysis for confidence scoring
            if self._has_database_schema_changes(changes):
                if bump_type == VersionBumpType.PATCH:
                    bump_type = VersionBumpType.MINOR
                    recommended_version = self._calculate_next_version(current_version, bump_type)
                    reasoning.append("Database schema changes detected, upgrading to minor version")
                elif bump_type == VersionBumpType.MINOR:
                    reasoning.append("Database schema changes detected in analysis")
                confidence_score *= 0.9
            
            if self._has_api_changes(changes):
                reasoning.append("API changes detected in analysis")
                if bump_type == VersionBumpType.PATCH:
                    confidence_score *= 0.8
            
            return SemanticVersionAnalysis(
                current_version=current_version,
                recommended_version=recommended_version,
                bump_type=bump_type,
                confidence_score=confidence_score,
                reasoning=reasoning,
                breaking_changes=breaking_changes,
                new_features=new_features,
                bug_fixes=bug_fixes
            )
            
        except Exception as e:
            self.logger.error(f"Error in semantic versioning analysis: {e}")
            raise

    async def assess_deployment_risk(self, changes: List[Change], target_environment: DeploymentEnvironment) -> RiskAssessment:
        """
        Assess deployment risk using historical data and change complexity
        
        Args:
            changes: List of changes in the release
            target_environment: Target deployment environment
            
        Returns:
            Comprehensive risk assessment
        """
        try:
            self.logger.info(f"Assessing deployment risk for {target_environment.value} environment")
            
            # Calculate base risk from changes
            complexity_risk = await self._assess_complexity_risk(changes)
            historical_risk = await self._assess_historical_risk(changes, target_environment)
            dependency_risk = await self._assess_dependency_risk(changes)
            
            # Combine risk factors
            risk_factors = []
            overall_risk_score = 0.0
            
            # Complexity risk
            if complexity_risk >= self.complexity_thresholds['high']:
                risk_factors.append(f"High complexity changes detected (score: {complexity_risk:.1f})")
                overall_risk_score += 0.4
            elif complexity_risk >= self.complexity_thresholds['medium']:
                risk_factors.append(f"Medium complexity changes detected (score: {complexity_risk:.1f})")
                overall_risk_score += 0.2
            
            # Historical risk
            if historical_risk > 0.7:
                risk_factors.append("Similar changes have high historical failure rate")
                overall_risk_score += 0.3
            elif historical_risk > 0.4:
                risk_factors.append("Similar changes have moderate historical failure rate")
                overall_risk_score += 0.15
            
            # Breaking changes
            breaking_changes = [c for c in changes if c.breaking_change]
            if breaking_changes:
                risk_factors.append(f"{len(breaking_changes)} breaking changes require careful deployment")
                overall_risk_score += len(breaking_changes) * 0.1
            
            # Security changes
            security_changes = [c for c in changes if c.security_impact]
            if security_changes:
                risk_factors.append(f"{len(security_changes)} security-related changes")
                overall_risk_score += len(security_changes) * 0.05
            
            # Environment-specific risk adjustments
            if target_environment == DeploymentEnvironment.PRODUCTION:
                overall_risk_score *= 1.5
                risk_factors.append("Production deployment increases risk")
            elif target_environment == DeploymentEnvironment.STAGING:
                overall_risk_score *= 1.2
            
            # Determine overall risk level
            if overall_risk_score >= 0.8:
                overall_risk = RiskLevel.CRITICAL
            elif overall_risk_score >= 0.6:
                overall_risk = RiskLevel.HIGH
            elif overall_risk_score >= 0.3:
                overall_risk = RiskLevel.MEDIUM
            else:
                overall_risk = RiskLevel.LOW
            
            # Generate mitigation strategies
            mitigation_strategies = await self._generate_mitigation_strategies(
                changes, overall_risk, risk_factors
            )
            
            # Perform detailed analysis
            performance_impact = await self.predict_performance_impact(changes)
            security_analysis = await self.analyze_security_impact(changes)
            rollback_plan = await self.assess_rollback_risk(changes)
            stakeholder_impact = await self.analyze_stakeholder_impact(changes)
            
            # Calculate confidence score
            confidence_score = min(0.95, 1.0 - (overall_risk_score * 0.2))
            
            # Go/No-Go recommendation
            go_no_go = overall_risk != RiskLevel.CRITICAL and len([r for r in risk_factors if "critical" in r.lower()]) == 0
            
            return RiskAssessment(
                overall_risk=overall_risk,
                deployment_risk=overall_risk,
                performance_impact=performance_impact,
                security_analysis=security_analysis,
                rollback_plan=rollback_plan,
                stakeholder_impact=stakeholder_impact,
                risk_factors=risk_factors,
                mitigation_strategies=mitigation_strategies,
                go_no_go_recommendation=go_no_go,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            self.logger.error(f"Error in deployment risk assessment: {e}")
            raise

    async def predict_performance_impact(self, changes: List[Change]) -> PerformanceImpact:
        """
        Predict performance impact through benchmark analysis and code profiling
        
        Args:
            changes: List of changes in the release
            
        Returns:
            Performance impact prediction
        """
        try:
            self.logger.info("Predicting performance impact")
            
            # Analyze performance-related changes
            performance_changes = [c for c in changes if c.performance_impact]
            database_changes = [c for c in changes if self._affects_database(c)]
            algorithm_changes = [c for c in changes if self._affects_algorithms(c)]
            
            # Calculate performance impact score
            performance_score = 0.0
            affected_components = []
            recommendations = []
            
            # Database performance impact
            if database_changes:
                db_impact = len(database_changes) * 2.5
                performance_score += db_impact
                affected_components.append("database")
                recommendations.append("Review database query performance and indexing")
            
            # Algorithm performance impact
            if algorithm_changes:
                algo_impact = sum(c.complexity_score for c in algorithm_changes) * 0.1
                performance_score += algo_impact
                affected_components.append("algorithms")
                recommendations.append("Profile algorithm performance with representative data")
            
            # Memory impact analysis
            memory_impact = await self._analyze_memory_impact(changes)
            if memory_impact > 10.0:  # 10% memory increase
                performance_score += memory_impact * 0.1
                affected_components.append("memory")
                recommendations.append("Monitor memory usage and optimize allocations")
            
            # CPU impact analysis
            cpu_impact = await self._analyze_cpu_impact(changes)
            if cpu_impact > 5.0:  # 5% CPU increase
                performance_score += cpu_impact * 0.2
                affected_components.append("cpu")
                recommendations.append("Profile CPU usage and optimize hot paths")
            
            # I/O impact analysis
            io_impact = await self._analyze_io_impact(changes)
            if io_impact > 15.0:  # 15% I/O increase
                performance_score += io_impact * 0.15
                affected_components.append("io")
                recommendations.append("Optimize I/O operations and consider caching")
            
            # Determine risk level
            if performance_score >= self.performance_thresholds['critical']:
                risk_level = RiskLevel.CRITICAL
                recommendations.append("Consider performance testing before deployment")
            elif performance_score >= self.performance_thresholds['concerning']:
                risk_level = RiskLevel.HIGH
                recommendations.append("Conduct thorough performance testing")
            elif performance_score >= self.performance_thresholds['acceptable']:
                risk_level = RiskLevel.MEDIUM
                recommendations.append("Monitor performance metrics post-deployment")
            else:
                risk_level = RiskLevel.LOW
            
            # Generate benchmark predictions
            benchmark_predictions = await self._generate_benchmark_predictions(changes)
            
            return PerformanceImpact(
                overall_risk=risk_level,
                affected_components=affected_components,
                estimated_performance_change=performance_score,
                benchmark_predictions=benchmark_predictions,
                memory_impact=memory_impact if memory_impact > 0 else None,
                cpu_impact=cpu_impact if cpu_impact > 0 else None,
                io_impact=io_impact if io_impact > 0 else None,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error in performance impact prediction: {e}")
            raise

    async def analyze_security_impact(self, changes: List[Change]) -> SecurityAnalysis:
        """
        Analyze security impact with dependency vulnerability scanning
        
        Args:
            changes: List of changes in the release
            
        Returns:
            Security analysis results
        """
        try:
            self.logger.info("Analyzing security impact")
            
            # Identify security-related changes
            security_changes = [c for c in changes if c.security_impact or c.type == ChangeType.SECURITY_FIX]
            dependency_changes = [c for c in changes if c.type == ChangeType.DEPENDENCY]
            
            # Analyze vulnerabilities
            vulnerabilities_introduced = await self._scan_for_new_vulnerabilities(changes)
            vulnerabilities_fixed = await self._identify_fixed_vulnerabilities(security_changes)
            dependency_vulnerabilities = await self._scan_dependency_vulnerabilities(dependency_changes)
            
            # Calculate security score change
            security_score_change = 0.0
            
            # Positive impact from fixes
            security_score_change += len(vulnerabilities_fixed) * 10.0
            
            # Negative impact from new vulnerabilities
            for vuln in vulnerabilities_introduced:
                severity_multiplier = {
                    'critical': -50.0,
                    'high': -25.0,
                    'medium': -10.0,
                    'low': -2.0
                }.get(vuln.get('severity', 'medium'), -10.0)
                security_score_change += severity_multiplier
            
            # Dependency vulnerability impact
            for vuln in dependency_vulnerabilities:
                severity_multiplier = {
                    'critical': -30.0,
                    'high': -15.0,
                    'medium': -5.0,
                    'low': -1.0
                }.get(vuln.get('severity', 'medium'), -5.0)
                security_score_change += severity_multiplier
            
            # Determine risk level
            critical_vulns = len([v for v in vulnerabilities_introduced + dependency_vulnerabilities 
                                if v.get('severity') == 'critical'])
            high_vulns = len([v for v in vulnerabilities_introduced + dependency_vulnerabilities 
                            if v.get('severity') == 'high'])
            
            if critical_vulns > 0:
                risk_level = RiskLevel.CRITICAL
            elif high_vulns > 2:
                risk_level = RiskLevel.HIGH
            elif high_vulns > 0 or len(vulnerabilities_introduced) > 3:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
            
            # Generate compliance impact
            compliance_impact = await self._assess_compliance_impact(changes, vulnerabilities_introduced)
            
            # Generate recommendations
            recommendations = []
            if vulnerabilities_introduced:
                recommendations.append("Address newly introduced vulnerabilities before deployment")
            if dependency_vulnerabilities:
                recommendations.append("Update vulnerable dependencies to secure versions")
            if critical_vulns > 0:
                recommendations.append("Critical vulnerabilities require immediate attention")
            if security_score_change < -20:
                recommendations.append("Consider security review before deployment")
            if len(security_changes) > 0:
                recommendations.append("Monitor security metrics post-deployment")
            if not recommendations:  # Ensure we always have at least one recommendation
                recommendations.append("Continue following security best practices")
            
            return SecurityAnalysis(
                risk_level=risk_level,
                vulnerabilities_introduced=vulnerabilities_introduced,
                vulnerabilities_fixed=vulnerabilities_fixed,
                dependency_vulnerabilities=dependency_vulnerabilities,
                security_score_change=security_score_change,
                compliance_impact=compliance_impact,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error in security impact analysis: {e}")
            raise

    async def assess_rollback_risk(self, changes: List[Change]) -> RollbackPlan:
        """
        Assess rollback risk and generate automated mitigation strategies
        
        Args:
            changes: List of changes in the release
            
        Returns:
            Rollback plan with risk assessment
        """
        try:
            self.logger.info("Assessing rollback risk")
            
            # Analyze rollback complexity factors
            database_changes = [c for c in changes if self._affects_database(c)]
            breaking_changes = [c for c in changes if c.breaking_change]
            dependency_changes = [c for c in changes if c.type == ChangeType.DEPENDENCY]
            
            # Calculate rollback complexity
            complexity_score = 0.0
            rollback_steps = []
            mitigation_strategies = []
            dependencies_affected = []
            
            # Database rollback complexity
            if database_changes:
                complexity_score += len(database_changes) * 15.0
                rollback_steps.append("Restore database schema to previous version")
                rollback_steps.append("Migrate data back to previous format")
                mitigation_strategies.append("Create database backup before deployment")
                mitigation_strategies.append("Test rollback procedures in staging environment")
            
            # Breaking changes rollback complexity
            if breaking_changes:
                complexity_score += len(breaking_changes) * 20.0
                rollback_steps.append("Revert API changes and restore backward compatibility")
                rollback_steps.append("Update client applications to use previous API version")
                mitigation_strategies.append("Implement feature flags for gradual rollout")
                mitigation_strategies.append("Maintain API versioning for smooth transitions")
            
            # Dependency rollback complexity
            if dependency_changes:
                complexity_score += len(dependency_changes) * 5.0
                rollback_steps.append("Revert dependency versions to previous state")
                rollback_steps.append("Rebuild and redeploy with previous dependencies")
                dependencies_affected.extend([dep for c in dependency_changes for dep in c.dependencies_affected])
                mitigation_strategies.append("Test with previous dependency versions")
            
            # Configuration changes
            config_changes = [c for c in changes if self._affects_configuration(c)]
            if config_changes:
                complexity_score += len(config_changes) * 8.0
                rollback_steps.append("Restore previous configuration files")
                rollback_steps.append("Restart services with previous configuration")
                mitigation_strategies.append("Backup configuration files before deployment")
            
            # Determine rollback risk level
            if complexity_score >= 80.0:
                rollback_risk = RiskLevel.CRITICAL
                estimated_time = timedelta(hours=4)
            elif complexity_score >= 50.0:
                rollback_risk = RiskLevel.HIGH
                estimated_time = timedelta(hours=2)
            elif complexity_score >= 20.0:
                rollback_risk = RiskLevel.MEDIUM
                estimated_time = timedelta(hours=1)
            else:
                rollback_risk = RiskLevel.LOW
                estimated_time = timedelta(minutes=30)
            
            # Determine if data migration is required
            data_migration_required = any(self._requires_data_migration(c) for c in changes)
            
            # Determine if rollback testing is required
            rollback_testing_required = (
                rollback_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL] or
                data_migration_required or
                len(breaking_changes) > 0
            )
            
            # Add general rollback steps
            rollback_steps.extend([
                "Stop application services",
                "Deploy previous application version",
                "Verify system functionality",
                "Monitor system health post-rollback"
            ])
            
            # Add general mitigation strategies
            mitigation_strategies.extend([
                "Implement comprehensive monitoring and alerting",
                "Prepare rollback procedures and test them",
                "Have rollback decision criteria defined",
                "Ensure team availability during deployment window"
            ])
            
            return RollbackPlan(
                rollback_risk=rollback_risk,
                rollback_complexity=complexity_score,
                estimated_rollback_time=estimated_time,
                rollback_steps=rollback_steps,
                data_migration_required=data_migration_required,
                rollback_testing_required=rollback_testing_required,
                mitigation_strategies=mitigation_strategies,
                dependencies_affected=list(set(dependencies_affected))
            )
            
        except Exception as e:
            self.logger.error(f"Error in rollback risk assessment: {e}")
            raise

    async def analyze_stakeholder_impact(self, changes: List[Change]) -> StakeholderImpact:
        """
        Analyze stakeholder impact with notification targeting and escalation paths
        
        Args:
            changes: List of changes in the release
            
        Returns:
            Stakeholder impact analysis
        """
        try:
            self.logger.info("Analyzing stakeholder impact")
            
            # Identify affected stakeholders based on change types
            affected_stakeholders = set()
            impact_severity = {}
            notification_priority = {}
            escalation_paths = {}
            communication_templates = {}
            timeline_impact = {}
            
            # Analyze different types of changes
            breaking_changes = [c for c in changes if c.breaking_change]
            security_changes = [c for c in changes if c.security_impact]
            performance_changes = [c for c in changes if c.performance_impact]
            api_changes = [c for c in changes if self._affects_api(c)]
            ui_changes = [c for c in changes if self._affects_ui(c)]
            
            # Development team impact
            affected_stakeholders.add("development_team")
            impact_severity["development_team"] = RiskLevel.MEDIUM
            notification_priority["development_team"] = "immediate"
            escalation_paths["development_team"] = ["tech_lead", "engineering_manager"]
            communication_templates["development_team"] = "technical_detailed"
            timeline_impact["development_team"] = timedelta(hours=2)
            
            # QA team impact
            if len(changes) > 10 or any(c.complexity_score > 20 for c in changes):
                affected_stakeholders.add("qa_team")
                impact_severity["qa_team"] = RiskLevel.HIGH if len(changes) > 20 else RiskLevel.MEDIUM
                notification_priority["qa_team"] = "high"
                escalation_paths["qa_team"] = ["qa_lead", "engineering_manager"]
                communication_templates["qa_team"] = "testing_focused"
                timeline_impact["qa_team"] = timedelta(hours=4)
            
            # Product team impact
            if breaking_changes or api_changes or ui_changes:
                affected_stakeholders.add("product_team")
                severity = RiskLevel.HIGH if breaking_changes else RiskLevel.MEDIUM
                impact_severity["product_team"] = severity
                notification_priority["product_team"] = "high" if breaking_changes else "medium"
                escalation_paths["product_team"] = ["product_manager", "product_director"]
                communication_templates["product_team"] = "business_impact"
                timeline_impact["product_team"] = timedelta(days=1)
            
            # Customer support impact
            if breaking_changes or ui_changes or len(changes) > 15:
                affected_stakeholders.add("customer_support")
                severity = RiskLevel.HIGH if breaking_changes else RiskLevel.MEDIUM
                impact_severity["customer_support"] = severity
                notification_priority["customer_support"] = "high" if breaking_changes else "medium"
                escalation_paths["customer_support"] = ["support_manager", "customer_success"]
                communication_templates["customer_support"] = "customer_facing"
                timeline_impact["customer_support"] = timedelta(hours=8)
            
            # Security team impact
            if security_changes:
                affected_stakeholders.add("security_team")
                impact_severity["security_team"] = RiskLevel.CRITICAL if len(security_changes) > 3 else RiskLevel.HIGH
                notification_priority["security_team"] = "critical"
                escalation_paths["security_team"] = ["security_lead", "ciso"]
                communication_templates["security_team"] = "security_focused"
                timeline_impact["security_team"] = timedelta(hours=1)
            
            # DevOps/SRE team impact
            if performance_changes or len(changes) > 25:
                affected_stakeholders.add("devops_team")
                severity = RiskLevel.HIGH if performance_changes else RiskLevel.MEDIUM
                impact_severity["devops_team"] = severity
                notification_priority["devops_team"] = "high"
                escalation_paths["devops_team"] = ["devops_lead", "infrastructure_manager"]
                communication_templates["devops_team"] = "operational_impact"
                timeline_impact["devops_team"] = timedelta(hours=6)
            
            # Executive team impact
            critical_changes = breaking_changes + security_changes
            if len(critical_changes) > 2 or any(c.type == ChangeType.SECURITY_FIX for c in changes):
                affected_stakeholders.add("executive_team")
                impact_severity["executive_team"] = RiskLevel.HIGH
                notification_priority["executive_team"] = "high"
                escalation_paths["executive_team"] = ["cto", "ceo"]
                communication_templates["executive_team"] = "executive_summary"
                timeline_impact["executive_team"] = timedelta(hours=12)
            
            # External partners impact
            if breaking_changes and any(self._affects_external_api(c) for c in changes):
                affected_stakeholders.add("external_partners")
                impact_severity["external_partners"] = RiskLevel.CRITICAL
                notification_priority["external_partners"] = "critical"
                escalation_paths["external_partners"] = ["partner_manager", "business_development"]
                communication_templates["external_partners"] = "partner_notification"
                timeline_impact["external_partners"] = timedelta(days=3)
            
            return StakeholderImpact(
                affected_stakeholders=list(affected_stakeholders),
                impact_severity=impact_severity,
                notification_priority=notification_priority,
                escalation_paths=escalation_paths,
                communication_templates=communication_templates,
                timeline_impact=timeline_impact
            )
            
        except Exception as e:
            self.logger.error(f"Error in stakeholder impact analysis: {e}")
            raise

    # Helper methods for analysis
    
    def _calculate_next_version(self, current_version: str, bump_type: VersionBumpType) -> str:
        """Calculate the next semantic version"""
        try:
            # Parse current version (assuming semver format)
            version_parts = current_version.split('.')
            if len(version_parts) != 3:
                raise ValueError(f"Invalid version format: {current_version}")
            
            major, minor, patch = map(int, version_parts)
            
            if bump_type == VersionBumpType.MAJOR:
                return f"{major + 1}.0.0"
            elif bump_type == VersionBumpType.MINOR:
                return f"{major}.{minor + 1}.0"
            else:  # PATCH
                return f"{major}.{minor}.{patch + 1}"
                
        except Exception as e:
            self.logger.error(f"Error calculating next version: {e}")
            return f"{current_version}-next"

    def _has_database_schema_changes(self, changes: List[Change]) -> bool:
        """Check if changes include database schema modifications"""
        schema_patterns = [
            r'\.sql$',
            r'migration',
            r'schema',
            r'database',
            r'CREATE TABLE',
            r'ALTER TABLE',
            r'DROP TABLE'
        ]
        
        for change in changes:
            for file_path in change.files_changed:
                for pattern in schema_patterns:
                    if re.search(pattern, file_path, re.IGNORECASE):
                        return True
            
            # Check description for schema-related keywords
            for pattern in schema_patterns[2:]:  # Skip file extensions
                if re.search(pattern, change.description, re.IGNORECASE):
                    return True
        
        return False

    def _has_api_changes(self, changes: List[Change]) -> bool:
        """Check if changes include API modifications"""
        api_patterns = [
            r'api/',
            r'endpoint',
            r'route',
            r'controller',
            r'@app\.route',
            r'@api\.',
            r'swagger',
            r'openapi'
        ]
        
        for change in changes:
            for file_path in change.files_changed:
                for pattern in api_patterns:
                    if re.search(pattern, file_path, re.IGNORECASE):
                        return True
            
            for pattern in api_patterns[1:]:  # Skip path patterns
                if re.search(pattern, change.description, re.IGNORECASE):
                    return True
        
        return False

    async def _assess_complexity_risk(self, changes: List[Change]) -> float:
        """Assess risk based on change complexity"""
        if not changes:
            return 0.0
        
        total_complexity = sum(c.complexity_score for c in changes)
        avg_complexity = total_complexity / len(changes)
        
        # Weight by number of files changed
        file_factor = sum(len(c.files_changed) for c in changes) / len(changes)
        
        # Weight by lines changed
        lines_factor = sum(c.lines_added + c.lines_removed for c in changes) / len(changes) / 100
        
        return avg_complexity + (file_factor * 2) + lines_factor

    async def _assess_historical_risk(self, changes: List[Change], environment: DeploymentEnvironment) -> float:
        """Assess risk based on historical deployment data"""
        # This would typically query historical deployment data
        # For now, return a simulated risk based on change characteristics
        
        risk_score = 0.0
        
        # Simulate historical risk based on change types
        breaking_changes = len([c for c in changes if c.breaking_change])
        security_changes = len([c for c in changes if c.security_impact])
        
        if breaking_changes > 0:
            risk_score += 0.3 * breaking_changes
        
        if security_changes > 0:
            risk_score += 0.2 * security_changes
        
        # Environment factor
        env_multiplier = {
            DeploymentEnvironment.DEVELOPMENT: 0.5,
            DeploymentEnvironment.STAGING: 0.8,
            DeploymentEnvironment.PRODUCTION: 1.2
        }.get(environment, 1.0)
        
        return min(1.0, risk_score * env_multiplier)

    async def _assess_dependency_risk(self, changes: List[Change]) -> float:
        """Assess risk from dependency changes"""
        dependency_changes = [c for c in changes if c.type == ChangeType.DEPENDENCY]
        
        if not dependency_changes:
            return 0.0
        
        # Simulate dependency risk assessment
        risk_score = len(dependency_changes) * 0.1
        
        # Check for major version bumps in dependencies
        for change in dependency_changes:
            if "major" in change.description.lower() or "breaking" in change.description.lower():
                risk_score += 0.2
        
        return min(1.0, risk_score)

    async def _generate_mitigation_strategies(self, changes: List[Change], risk_level: RiskLevel, risk_factors: List[str]) -> List[str]:
        """Generate mitigation strategies based on risk assessment"""
        strategies = []
        
        # Base strategies
        strategies.append("Implement comprehensive monitoring and alerting")
        strategies.append("Prepare rollback procedures and test them")
        
        # Risk-specific strategies
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            strategies.append("Deploy to staging environment first for thorough testing")
            strategies.append("Implement feature flags for gradual rollout")
            strategies.append("Have dedicated team available during deployment")
        
        if "breaking" in " ".join(risk_factors).lower():
            strategies.append("Coordinate with client teams for API changes")
            strategies.append("Implement API versioning strategy")
        
        if "security" in " ".join(risk_factors).lower():
            strategies.append("Conduct security review before deployment")
            strategies.append("Implement additional security monitoring")
        
        if "complexity" in " ".join(risk_factors).lower():
            strategies.append("Break deployment into smaller, incremental releases")
            strategies.append("Increase testing coverage for complex changes")
        
        return strategies

    def _affects_database(self, change: Change) -> bool:
        """Check if a change affects the database"""
        db_patterns = [
            r'\.sql$',
            r'migration',
            r'database',
            r'db/',
            r'models/',
            r'schema'
        ]
        
        for file_path in change.files_changed:
            for pattern in db_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    return True
        
        return any(keyword in change.description.lower() 
                  for keyword in ['database', 'migration', 'schema', 'sql'])

    def _affects_algorithms(self, change: Change) -> bool:
        """Check if a change affects core algorithms"""
        algo_patterns = [
            r'algorithm',
            r'sort',
            r'search',
            r'optimization',
            r'performance',
            r'complexity'
        ]
        
        for pattern in algo_patterns:
            if re.search(pattern, change.description, re.IGNORECASE):
                return True
        
        return change.complexity_score > 25.0

    async def _analyze_memory_impact(self, changes: List[Change]) -> float:
        """Analyze potential memory impact of changes"""
        # Simulate memory impact analysis
        memory_impact = 0.0
        
        for change in changes:
            # Check for memory-intensive patterns
            if any(keyword in change.description.lower() 
                   for keyword in ['cache', 'memory', 'buffer', 'allocation']):
                memory_impact += change.complexity_score * 0.5
            
            # Large file changes might indicate memory impact
            if change.lines_added > 500:
                memory_impact += (change.lines_added / 100) * 0.2
        
        return memory_impact

    async def _analyze_cpu_impact(self, changes: List[Change]) -> float:
        """Analyze potential CPU impact of changes"""
        # Simulate CPU impact analysis
        cpu_impact = 0.0
        
        for change in changes:
            # Check for CPU-intensive patterns
            if any(keyword in change.description.lower() 
                   for keyword in ['algorithm', 'computation', 'processing', 'cpu']):
                cpu_impact += change.complexity_score * 0.3
            
            # Performance-related changes
            if change.performance_impact:
                cpu_impact += 5.0
        
        return cpu_impact

    async def _analyze_io_impact(self, changes: List[Change]) -> float:
        """Analyze potential I/O impact of changes"""
        # Simulate I/O impact analysis
        io_impact = 0.0
        
        for change in changes:
            # Check for I/O-intensive patterns
            if any(keyword in change.description.lower() 
                   for keyword in ['file', 'disk', 'network', 'io', 'api']):
                io_impact += change.complexity_score * 0.4
            
            # Database changes affect I/O
            if self._affects_database(change):
                io_impact += 10.0
        
        return io_impact

    async def _generate_benchmark_predictions(self, changes: List[Change]) -> Dict[str, float]:
        """Generate benchmark predictions for performance impact"""
        # Simulate benchmark predictions
        predictions = {
            "response_time": 0.0,
            "throughput": 0.0,
            "memory_usage": 0.0,
            "cpu_usage": 0.0
        }
        
        for change in changes:
            if change.performance_impact:
                predictions["response_time"] += change.complexity_score * 0.1
                predictions["throughput"] -= change.complexity_score * 0.05
                predictions["memory_usage"] += change.complexity_score * 0.2
                predictions["cpu_usage"] += change.complexity_score * 0.15
        
        return predictions

    async def _scan_for_new_vulnerabilities(self, changes: List[Change]) -> List[Dict[str, Any]]:
        """Scan for newly introduced vulnerabilities"""
        # Simulate vulnerability scanning
        vulnerabilities = []
        
        for change in changes:
            # Check for common vulnerability patterns
            if any(keyword in change.description.lower() 
                   for keyword in ['input', 'user', 'external', 'api']):
                if change.complexity_score > 15:
                    vulnerabilities.append({
                        "id": f"VULN-{change.id}",
                        "severity": "medium",
                        "description": f"Potential input validation vulnerability in {change.description}",
                        "file": change.files_changed[0] if change.files_changed else "unknown",
                        "recommendation": "Review input validation and sanitization"
                    })
        
        return vulnerabilities

    async def _identify_fixed_vulnerabilities(self, security_changes: List[Change]) -> List[Dict[str, Any]]:
        """Identify vulnerabilities fixed by security changes"""
        fixed_vulnerabilities = []
        
        for change in security_changes:
            if change.type == ChangeType.SECURITY_FIX:
                fixed_vulnerabilities.append({
                    "id": f"FIXED-{change.id}",
                    "severity": "high" if "critical" in change.description.lower() else "medium",
                    "description": f"Security fix: {change.description}",
                    "fix_description": change.description
                })
        
        return fixed_vulnerabilities

    async def _scan_dependency_vulnerabilities(self, dependency_changes: List[Change]) -> List[Dict[str, Any]]:
        """Scan dependencies for known vulnerabilities"""
        # Simulate dependency vulnerability scanning
        vulnerabilities = []
        
        for change in dependency_changes:
            # Simulate finding vulnerabilities in dependencies
            if "update" in change.description.lower() or "upgrade" in change.description.lower():
                # Assume updates fix vulnerabilities
                continue
            
            # Simulate vulnerability in new dependencies
            if len(change.dependencies_affected) > 0:
                vulnerabilities.append({
                    "id": f"DEP-VULN-{change.id}",
                    "severity": "medium",
                    "description": f"Potential vulnerability in dependency: {change.dependencies_affected[0]}",
                    "dependency": change.dependencies_affected[0],
                    "recommendation": "Update to latest secure version"
                })
        
        return vulnerabilities

    async def _assess_compliance_impact(self, changes: List[Change], vulnerabilities: List[Dict[str, Any]]) -> List[str]:
        """Assess impact on compliance requirements"""
        compliance_impact = []
        
        # Check for data handling changes
        data_changes = [c for c in changes if any(keyword in c.description.lower() 
                                                 for keyword in ['data', 'personal', 'privacy', 'gdpr'])]
        if data_changes:
            compliance_impact.append("GDPR compliance review required for data handling changes")
        
        # Check for security vulnerabilities
        critical_vulns = [v for v in vulnerabilities if v.get('severity') == 'critical']
        if critical_vulns:
            compliance_impact.append("SOC2 compliance impact due to critical security vulnerabilities")
        
        # Check for audit trail changes
        audit_changes = [c for c in changes if any(keyword in c.description.lower() 
                                                  for keyword in ['audit', 'log', 'tracking'])]
        if audit_changes:
            compliance_impact.append("Audit trail compliance review required")
        
        return compliance_impact

    def _requires_data_migration(self, change: Change) -> bool:
        """Check if a change requires data migration"""
        migration_keywords = ['migration', 'schema', 'alter table', 'data migration']
        
        return (
            self._affects_database(change) and
            any(keyword in change.description.lower() for keyword in migration_keywords)
        )

    def _affects_configuration(self, change: Change) -> bool:
        """Check if a change affects configuration"""
        config_patterns = [
            r'config',
            r'\.yaml$',
            r'\.yml$',
            r'\.json$',
            r'\.env',
            r'settings'
        ]
        
        for file_path in change.files_changed:
            for pattern in config_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    return True
        
        return 'config' in change.description.lower()

    def _affects_api(self, change: Change) -> bool:
        """Check if a change affects API"""
        return self._has_api_changes([change])

    def _affects_ui(self, change: Change) -> bool:
        """Check if a change affects UI"""
        ui_patterns = [
            r'ui/',
            r'frontend/',
            r'components/',
            r'\.html$',
            r'\.css$',
            r'\.js$',
            r'\.tsx?$',
            r'\.vue$'
        ]
        
        for file_path in change.files_changed:
            for pattern in ui_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    return True
        
        return any(keyword in change.description.lower() 
                  for keyword in ['ui', 'frontend', 'interface', 'component'])

    def _affects_external_api(self, change: Change) -> bool:
        """Check if a change affects external-facing API"""
        external_patterns = [
            r'public',
            r'external',
            r'api/v\d+',
            r'webhook',
            r'integration'
        ]
        
        for file_path in change.files_changed:
            for pattern in external_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    return True
        
        return any(keyword in change.description.lower() 
                  for keyword in ['public api', 'external', 'webhook', 'integration'])