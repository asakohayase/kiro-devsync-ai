"""
DevSync AI Intelligence Engine for JIRA Agent Hooks.

This module provides AI-powered insights, predictive analytics, and
intelligent automation recommendations for enhanced team productivity.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import random
from collections import defaultdict, Counter

from devsync_ai.hooks.hook_registry_manager import get_hook_registry_manager
from devsync_ai.analytics.productivity_analytics_engine import ProductivityAnalyticsEngine


logger = logging.getLogger(__name__)


class PredictionType(Enum):
    """Types of predictions the intelligence engine can make."""
    BLOCKER_RISK = "blocker_risk"
    ASSIGNMENT_SUCCESS = "assignment_success"
    SPRINT_COMPLETION = "sprint_completion"
    TEAM_BURNOUT = "team_burnout"
    COMMUNICATION_OVERLOAD = "communication_overload"


class InsightCategory(Enum):
    """Categories of AI insights."""
    PREDICTIVE = "predictive"
    DIAGNOSTIC = "diagnostic"
    PRESCRIPTIVE = "prescriptive"
    COMPARATIVE = "comparative"


@dataclass
class PredictiveInsight:
    """AI-generated predictive insight."""
    insight_id: str
    prediction_type: PredictionType
    team_id: str
    prediction_text: str
    probability: float
    confidence_score: float
    time_horizon: str
    risk_level: str
    early_warning_indicators: List[str]
    mitigation_strategies: List[str]
    supporting_data: Dict[str, Any]
    generated_at: datetime


@dataclass
class AssignmentRecommendation:
    """AI-powered assignment recommendation."""
    ticket_key: str
    recommended_assignee: str
    confidence_score: float
    skill_match_score: float
    workload_impact_score: float
    historical_success_rate: float
    estimated_completion_time: timedelta
    alternative_assignees: List[Dict[str, Any]]
    reasoning: List[str]


@dataclass
class SprintRiskAssessment:
    """Comprehensive sprint risk assessment."""
    sprint_id: str
    team_id: str
    overall_risk_score: float  # 0-100
    risk_level: str  # "low", "medium", "high", "critical"
    completion_probability: float
    risk_factors: List[Dict[str, Any]]
    early_warning_signals: List[str]
    mitigation_recommendations: List[str]
    automated_interventions: List[str]
    timeline_impact: Dict[str, Any]


@dataclass
class TeamHealthInsight:
    """Team health and communication analysis."""
    team_id: str
    health_score: float  # 0-100
    communication_efficiency: float
    collaboration_index: float
    burnout_risk: float
    productivity_trend: str
    communication_patterns: Dict[str, Any]
    recommendations: List[str]
    intervention_suggestions: List[str]


class IntelligenceEngine:
    """
    AI-powered intelligence engine for JIRA Agent Hooks.
    
    Provides predictive analytics, intelligent recommendations, and
    automated insights for enhanced team productivity and coordination.
    """
    
    def __init__(self):
        """Initialize the intelligence engine."""
        self.productivity_engine = ProductivityAnalyticsEngine()
        self.predictive_insights: List[PredictiveInsight] = []
        self.assignment_recommendations: Dict[str, AssignmentRecommendation] = {}
        self.sprint_risk_assessments: Dict[str, SprintRiskAssessment] = {}
        self.team_health_insights: Dict[str, TeamHealthInsight] = {}
        
        # Historical patterns for ML-based predictions
        self.blocker_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.assignment_success_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.team_performance_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Skill and expertise mapping
        self.team_expertise: Dict[str, Dict[str, float]] = {}
        self.historical_assignments: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    async def predict_blocker_risk(
        self,
        ticket_key: str,
        team_id: str,
        ticket_data: Dict[str, Any]
    ) -> PredictiveInsight:
        """
        Predict the likelihood of a ticket becoming blocked.
        
        Args:
            ticket_key: JIRA ticket key
            team_id: Team identifier
            ticket_data: Ticket information
            
        Returns:
            Predictive insight about blocker risk
        """
        # Analyze ticket characteristics for blocker risk
        risk_factors = []
        risk_score = 0.0
        
        # Check priority and complexity
        priority = ticket_data.get('priority', '').lower()
        if priority in ['critical', 'highest']:
            risk_score += 0.3
            risk_factors.append("High priority tickets have 30% higher blocker risk")
        
        # Check for dependency keywords
        summary = ticket_data.get('summary', '').lower()
        description = ticket_data.get('description', '').lower()
        text_content = f"{summary} {description}"
        
        dependency_keywords = ['depends on', 'requires', 'integration', 'external', 'api', 'third party']
        dependency_count = sum(1 for keyword in dependency_keywords if keyword in text_content)
        
        if dependency_count > 0:
            dependency_risk = min(0.4, dependency_count * 0.15)
            risk_score += dependency_risk
            risk_factors.append(f"Contains {dependency_count} dependency indicators")
        
        # Check assignee experience
        assignee = ticket_data.get('assignee')
        if assignee:
            assignee_name = assignee.get('displayName', '')
            # Mock experience analysis
            experience_score = random.uniform(0.6, 0.9)  # Would be calculated from historical data
            if experience_score < 0.7:
                risk_score += 0.2
                risk_factors.append("Assignee has limited experience with similar tickets")
        
        # Check team historical patterns
        team_blocker_history = self.blocker_patterns.get(team_id, [])
        if team_blocker_history:
            similar_tickets = [
                b for b in team_blocker_history
                if any(keyword in b.get('summary', '').lower() for keyword in text_content.split()[:5])
            ]
            if similar_tickets:
                historical_blocker_rate = len(similar_tickets) / len(team_blocker_history)
                risk_score += historical_blocker_rate * 0.3
                risk_factors.append(f"Similar tickets had {historical_blocker_rate:.1%} blocker rate")
        
        # Normalize risk score
        risk_score = min(1.0, risk_score)
        probability = risk_score
        
        # Determine risk level
        if probability > 0.7:
            risk_level = "high"
        elif probability > 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Generate early warning indicators
        early_warnings = []
        if dependency_count > 2:
            early_warnings.append("Multiple external dependencies detected")
        if priority in ['critical', 'highest']:
            early_warnings.append("High priority may create pressure and rushed decisions")
        if not assignee:
            early_warnings.append("Unassigned ticket may lead to delays")
        
        # Generate mitigation strategies
        mitigation_strategies = []
        if dependency_count > 0:
            mitigation_strategies.append("Identify and validate all dependencies early")
            mitigation_strategies.append("Create fallback plans for external dependencies")
        if risk_score > 0.5:
            mitigation_strategies.append("Schedule regular check-ins with assignee")
            mitigation_strategies.append("Prepare escalation path for quick resolution")
        
        insight = PredictiveInsight(
            insight_id=f"blocker_risk_{ticket_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            prediction_type=PredictionType.BLOCKER_RISK,
            team_id=team_id,
            prediction_text=f"Ticket {ticket_key} has a {probability:.1%} probability of becoming blocked based on content analysis and team patterns.",
            probability=probability,
            confidence_score=0.75 + (len(risk_factors) * 0.05),  # Higher confidence with more evidence
            time_horizon="next 3-5 days",
            risk_level=risk_level,
            early_warning_indicators=early_warnings,
            mitigation_strategies=mitigation_strategies,
            supporting_data={
                'risk_factors': risk_factors,
                'dependency_count': dependency_count,
                'priority': priority,
                'team_blocker_history_size': len(team_blocker_history)
            },
            generated_at=datetime.now(timezone.utc)
        )
        
        self.predictive_insights.append(insight)
        return insight
    
    async def recommend_optimal_assignment(
        self,
        ticket_key: str,
        team_id: str,
        ticket_data: Dict[str, Any],
        available_assignees: List[str]
    ) -> AssignmentRecommendation:
        """
        Recommend optimal assignment using AI analysis.
        
        Args:
            ticket_key: JIRA ticket key
            team_id: Team identifier
            ticket_data: Ticket information
            available_assignees: List of available team members
            
        Returns:
            AI-powered assignment recommendation
        """
        if not available_assignees:
            # Return default recommendation
            return AssignmentRecommendation(
                ticket_key=ticket_key,
                recommended_assignee="unassigned",
                confidence_score=0.0,
                skill_match_score=0.0,
                workload_impact_score=0.0,
                historical_success_rate=0.0,
                estimated_completion_time=timedelta(days=5),
                alternative_assignees=[],
                reasoning=["No available assignees"]
            )
        
        # Analyze each potential assignee
        assignee_scores = {}
        
        for assignee in available_assignees:
            # Calculate skill match score
            skill_score = await self._calculate_skill_match(assignee, ticket_data)
            
            # Calculate workload impact score
            workload_score = await self._calculate_workload_impact(assignee, team_id)
            
            # Calculate historical success rate
            success_rate = await self._calculate_historical_success_rate(assignee, ticket_data)
            
            # Calculate estimated completion time
            completion_time = await self._estimate_completion_time(assignee, ticket_data)
            
            # Overall score (weighted combination)
            overall_score = (
                skill_score * 0.4 +
                workload_score * 0.3 +
                success_rate * 0.3
            )
            
            assignee_scores[assignee] = {
                'overall_score': overall_score,
                'skill_match_score': skill_score,
                'workload_impact_score': workload_score,
                'historical_success_rate': success_rate,
                'estimated_completion_time': completion_time
            }
        
        # Find best assignee
        best_assignee = max(assignee_scores.keys(), key=lambda a: assignee_scores[a]['overall_score'])
        best_scores = assignee_scores[best_assignee]
        
        # Create alternative recommendations
        alternatives = []
        sorted_assignees = sorted(
            assignee_scores.items(),
            key=lambda x: x[1]['overall_score'],
            reverse=True
        )[1:4]  # Top 3 alternatives
        
        for assignee, scores in sorted_assignees:
            alternatives.append({
                'assignee': assignee,
                'overall_score': scores['overall_score'],
                'skill_match': scores['skill_match_score'],
                'workload_impact': scores['workload_impact_score'],
                'reasoning': self._generate_assignee_reasoning(assignee, scores)
            })
        
        # Generate reasoning for recommendation
        reasoning = self._generate_assignee_reasoning(best_assignee, best_scores)
        
        recommendation = AssignmentRecommendation(
            ticket_key=ticket_key,
            recommended_assignee=best_assignee,
            confidence_score=best_scores['overall_score'],
            skill_match_score=best_scores['skill_match_score'],
            workload_impact_score=best_scores['workload_impact_score'],
            historical_success_rate=best_scores['historical_success_rate'],
            estimated_completion_time=best_scores['estimated_completion_time'],
            alternative_assignees=alternatives,
            reasoning=reasoning
        )
        
        self.assignment_recommendations[ticket_key] = recommendation
        return recommendation
    
    async def assess_sprint_risk(
        self,
        sprint_id: str,
        team_id: str,
        sprint_data: Dict[str, Any]
    ) -> SprintRiskAssessment:
        """
        Assess comprehensive sprint risk with AI analysis.
        
        Args:
            sprint_id: Sprint identifier
            team_id: Team identifier
            sprint_data: Sprint information
            
        Returns:
            Comprehensive sprint risk assessment
        """
        # Analyze current sprint metrics
        planned_points = sprint_data.get('planned_story_points', 30)
        completed_points = sprint_data.get('completed_story_points', 15)
        days_remaining = sprint_data.get('days_remaining', 7)
        active_blockers = sprint_data.get('active_blockers', 1)
        
        # Calculate risk factors
        risk_factors = []
        risk_score = 0.0
        
        # Velocity risk
        completion_rate = completed_points / planned_points if planned_points > 0 else 0
        required_velocity = (planned_points - completed_points) / max(1, days_remaining)
        
        # Get team's historical velocity
        team_patterns = self.team_performance_patterns.get(team_id, [])
        if team_patterns:
            avg_daily_velocity = statistics.mean([p.get('daily_velocity', 3) for p in team_patterns])
        else:
            avg_daily_velocity = 3.0  # Default assumption
        
        if required_velocity > avg_daily_velocity * 1.2:
            risk_score += 0.3
            risk_factors.append({
                'factor': 'velocity_risk',
                'severity': 'high',
                'description': f'Required velocity ({required_velocity:.1f}) exceeds team average ({avg_daily_velocity:.1f})',
                'impact': 'May not complete all planned work'
            })
        
        # Blocker risk
        if active_blockers > 0:
            blocker_risk = min(0.4, active_blockers * 0.15)
            risk_score += blocker_risk
            risk_factors.append({
                'factor': 'active_blockers',
                'severity': 'high' if active_blockers > 2 else 'medium',
                'description': f'{active_blockers} active blockers may delay completion',
                'impact': 'Potential timeline delays and scope reduction'
            })
        
        # Time pressure risk
        if days_remaining < 3:
            risk_score += 0.2
            risk_factors.append({
                'factor': 'time_pressure',
                'severity': 'medium',
                'description': 'Limited time remaining increases delivery risk',
                'impact': 'Quality may be compromised to meet deadlines'
            })
        
        # Team capacity risk
        registry_manager = await get_hook_registry_manager()
        if registry_manager:
            team_hooks = await registry_manager.get_all_hook_statuses()
            team_hooks = [h for h in team_hooks if h['team_id'] == team_id]
            
            if team_hooks:
                avg_success_rate = statistics.mean([h['statistics']['success_rate'] for h in team_hooks])
                if avg_success_rate < 0.9:
                    risk_score += 0.15
                    risk_factors.append({
                        'factor': 'automation_performance',
                        'severity': 'medium',
                        'description': f'Hook system success rate ({avg_success_rate:.1%}) below optimal',
                        'impact': 'Reduced coordination efficiency'
                    })
        
        # Normalize risk score
        risk_score = min(1.0, risk_score)
        
        # Determine risk level
        if risk_score > 0.7:
            risk_level = "critical"
        elif risk_score > 0.5:
            risk_level = "high"
        elif risk_score > 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Calculate completion probability
        completion_probability = max(0.1, 1.0 - risk_score)
        
        # Generate early warning signals
        early_warnings = []
        if completion_rate < 0.5 and days_remaining < 5:
            early_warnings.append("Sprint completion rate significantly behind schedule")
        if active_blockers > 1:
            early_warnings.append("Multiple active blockers detected")
        if required_velocity > avg_daily_velocity * 1.5:
            early_warnings.append("Required velocity significantly exceeds team capacity")
        
        # Generate mitigation recommendations
        mitigation_recommendations = []
        if risk_score > 0.5:
            mitigation_recommendations.append("Consider scope reduction for non-critical items")
            mitigation_recommendations.append("Increase daily standup frequency for better coordination")
        if active_blockers > 0:
            mitigation_recommendations.append("Prioritize blocker resolution with dedicated resources")
        if days_remaining < 5:
            mitigation_recommendations.append("Focus on highest priority items only")
        
        # Generate automated intervention suggestions
        automated_interventions = []
        if risk_score > 0.6:
            automated_interventions.append("Enable high-frequency status monitoring")
            automated_interventions.append("Activate escalation alerts for management")
        if active_blockers > 1:
            automated_interventions.append("Auto-escalate blockers to team leads")
        
        # Analyze timeline impact
        timeline_impact = {
            'estimated_completion_date': datetime.now(timezone.utc) + timedelta(days=days_remaining),
            'risk_adjusted_date': datetime.now(timezone.utc) + timedelta(days=int(days_remaining * (1 + risk_score))),
            'buffer_days_needed': int(days_remaining * risk_score),
            'scope_reduction_percentage': max(0, (risk_score - 0.3) * 100) if risk_score > 0.3 else 0
        }
        
        assessment = SprintRiskAssessment(
            sprint_id=sprint_id,
            team_id=team_id,
            overall_risk_score=risk_score * 100,
            risk_level=risk_level,
            completion_probability=completion_probability,
            risk_factors=risk_factors,
            early_warning_signals=early_warnings,
            mitigation_recommendations=mitigation_recommendations,
            automated_interventions=automated_interventions,
            timeline_impact=timeline_impact
        )
        
        self.sprint_risk_assessments[f"{team_id}_{sprint_id}"] = assessment
        return assessment
    
    async def analyze_team_communication_health(
        self,
        team_id: str,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> TeamHealthInsight:
        """
        Analyze team communication patterns and health.
        
        Args:
            team_id: Team identifier
            time_range: Time range for analysis
            
        Returns:
            Team health insights and recommendations
        """
        if not time_range:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=14)
            time_range = (start_date, end_date)
        
        # Get team collaboration metrics
        collaboration_metrics = await self.productivity_engine.analyze_team_collaboration(team_id, time_range)
        
        # Calculate health scores
        communication_efficiency = collaboration_metrics.collaboration_efficiency_score / 100
        
        # Calculate collaboration index based on cross-team interactions
        collaboration_index = min(1.0, collaboration_metrics.cross_team_communications / 50)  # Normalize to 50 interactions
        
        # Analyze burnout risk indicators
        burnout_risk = await self._analyze_burnout_risk(team_id, collaboration_metrics)
        
        # Determine productivity trend
        productivity_trend = await self._analyze_productivity_trend(team_id)
        
        # Calculate overall health score
        health_score = (
            communication_efficiency * 0.3 +
            collaboration_index * 0.2 +
            (1.0 - burnout_risk) * 0.3 +
            self._trend_to_score(productivity_trend) * 0.2
        ) * 100
        
        # Analyze communication patterns
        communication_patterns = {
            'notification_frequency': collaboration_metrics.automated_notifications / 7,  # Per day
            'response_time_improvement': collaboration_metrics.response_time_improvement,
            'manual_vs_automated_ratio': collaboration_metrics.manual_status_updates / max(1, collaboration_metrics.automated_notifications),
            'peak_activity_hours': collaboration_metrics.communication_patterns.get('peak_hours', []),
            'cross_team_collaboration': collaboration_metrics.cross_team_communications
        }
        
        # Generate recommendations
        recommendations = []
        if communication_efficiency < 0.8:
            recommendations.append("Optimize notification timing and relevance")
        if collaboration_index < 0.6:
            recommendations.append("Encourage more cross-team collaboration")
        if burnout_risk > 0.6:
            recommendations.append("Reduce notification frequency during off-hours")
        if productivity_trend == "declining":
            recommendations.append("Review and adjust automation rules")
        
        # Generate intervention suggestions
        interventions = []
        if health_score < 70:
            interventions.append("Schedule team health check meeting")
            interventions.append("Review notification preferences with team")
        if burnout_risk > 0.7:
            interventions.append("Implement notification quiet hours")
            interventions.append("Reduce non-critical alert frequency")
        
        insight = TeamHealthInsight(
            team_id=team_id,
            health_score=health_score,
            communication_efficiency=communication_efficiency,
            collaboration_index=collaboration_index,
            burnout_risk=burnout_risk,
            productivity_trend=productivity_trend,
            communication_patterns=communication_patterns,
            recommendations=recommendations,
            intervention_suggestions=interventions
        )
        
        self.team_health_insights[team_id] = insight
        return insight
    
    async def generate_intelligent_scheduling_recommendations(
        self,
        team_id: str,
        notification_type: str
    ) -> Dict[str, Any]:
        """
        Generate intelligent notification scheduling recommendations.
        
        Args:
            team_id: Team identifier
            notification_type: Type of notification
            
        Returns:
            Scheduling recommendations with timezone awareness
        """
        # Mock team timezone and work patterns (would come from team configuration)
        team_timezone = "America/New_York"  # Would be configured per team
        work_hours = (9, 17)  # 9 AM to 5 PM
        
        # Analyze historical engagement patterns
        engagement_patterns = await self._analyze_engagement_patterns(team_id, notification_type)
        
        # Generate recommendations
        recommendations = {
            'optimal_send_times': engagement_patterns.get('peak_engagement_hours', [10, 14, 16]),
            'avoid_times': engagement_patterns.get('low_engagement_hours', [12, 18, 19]),  # Lunch and end of day
            'timezone': team_timezone,
            'work_hours': work_hours,
            'weekend_policy': 'emergency_only',
            'batching_recommendations': {
                'status_changes': 'batch_every_30_minutes',
                'assignments': 'send_immediately',
                'blockers': 'send_immediately',
                'comments': 'batch_every_hour'
            },
            'urgency_overrides': {
                'critical': 'send_immediately_always',
                'high': 'send_immediately_during_work_hours',
                'medium': 'respect_batching_rules',
                'low': 'batch_and_send_once_daily'
            }
        }
        
        return recommendations
    
    # Helper methods
    async def _calculate_skill_match(self, assignee: str, ticket_data: Dict[str, Any]) -> float:
        """Calculate skill match score for assignee and ticket."""
        # Mock skill analysis (would use actual skill tracking)
        summary = ticket_data.get('summary', '').lower()
        
        # Simple keyword-based skill matching
        skill_keywords = {
            'frontend': ['ui', 'frontend', 'react', 'css'],
            'backend': ['api', 'backend', 'database', 'server'],
            'devops': ['deployment', 'docker', 'kubernetes'],
            'mobile': ['mobile', 'ios', 'android']
        }
        
        # Mock assignee skills
        assignee_skills = random.choice(list(skill_keywords.keys()))
        keywords = skill_keywords[assignee_skills]
        
        match_count = sum(1 for keyword in keywords if keyword in summary)
        return min(1.0, match_count / len(keywords) + 0.5)  # Base score of 0.5
    
    async def _calculate_workload_impact(self, assignee: str, team_id: str) -> float:
        """Calculate workload impact score (higher is better)."""
        # Mock workload calculation (would query actual workload data)
        current_load = random.uniform(0.3, 0.9)  # 30-90% capacity
        return 1.0 - current_load  # Higher score for lower current load
    
    async def _calculate_historical_success_rate(self, assignee: str, ticket_data: Dict[str, Any]) -> float:
        """Calculate historical success rate for similar tickets."""
        # Mock historical analysis
        return random.uniform(0.7, 0.95)
    
    async def _estimate_completion_time(self, assignee: str, ticket_data: Dict[str, Any]) -> timedelta:
        """Estimate completion time for assignee and ticket."""
        # Mock estimation (would use historical data and ML models)
        story_points = ticket_data.get('story_points', 5)
        base_days = story_points * 0.5  # 0.5 days per story point
        
        # Add some variation based on complexity
        complexity_factor = random.uniform(0.8, 1.3)
        estimated_days = base_days * complexity_factor
        
        return timedelta(days=estimated_days)
    
    def _generate_assignee_reasoning(self, assignee: str, scores: Dict[str, Any]) -> List[str]:
        """Generate reasoning for assignee recommendation."""
        reasoning = []
        
        if scores['skill_match_score'] > 0.8:
            reasoning.append(f"Excellent skill match ({scores['skill_match_score']:.1%})")
        elif scores['skill_match_score'] > 0.6:
            reasoning.append(f"Good skill match ({scores['skill_match_score']:.1%})")
        
        if scores['workload_impact_score'] > 0.7:
            reasoning.append("Low current workload allows focus on this ticket")
        elif scores['workload_impact_score'] < 0.3:
            reasoning.append("High current workload may impact delivery timeline")
        
        if scores['historical_success_rate'] > 0.9:
            reasoning.append("Strong track record with similar tickets")
        
        completion_days = scores['estimated_completion_time'].days
        if completion_days <= 2:
            reasoning.append("Fast estimated completion time")
        elif completion_days > 5:
            reasoning.append("Longer completion time due to complexity")
        
        return reasoning
    
    async def _analyze_burnout_risk(self, team_id: str, collaboration_metrics) -> float:
        """Analyze team burnout risk based on communication patterns."""
        # Factors that indicate burnout risk
        risk_factors = 0.0
        
        # High notification frequency
        daily_notifications = collaboration_metrics.automated_notifications / 7
        if daily_notifications > 20:
            risk_factors += 0.3
        
        # Low response time improvement (indicates stress)
        if collaboration_metrics.response_time_improvement < 0.1:
            risk_factors += 0.2
        
        # High manual status updates (indicates automation not helping)
        manual_ratio = collaboration_metrics.manual_status_updates / max(1, collaboration_metrics.automated_notifications)
        if manual_ratio > 0.5:
            risk_factors += 0.2
        
        return min(1.0, risk_factors)
    
    async def _analyze_productivity_trend(self, team_id: str) -> str:
        """Analyze team productivity trend."""
        patterns = self.team_performance_patterns.get(team_id, [])
        if len(patterns) < 3:
            return "stable"
        
        recent_productivity = statistics.mean([p.get('productivity_score', 70) for p in patterns[-3:]])
        older_productivity = statistics.mean([p.get('productivity_score', 70) for p in patterns[:-3]])
        
        if recent_productivity > older_productivity * 1.1:
            return "improving"
        elif recent_productivity < older_productivity * 0.9:
            return "declining"
        else:
            return "stable"
    
    def _trend_to_score(self, trend: str) -> float:
        """Convert trend to numeric score."""
        trend_scores = {
            "improving": 1.0,
            "stable": 0.8,
            "declining": 0.4
        }
        return trend_scores.get(trend, 0.6)
    
    async def _analyze_engagement_patterns(self, team_id: str, notification_type: str) -> Dict[str, Any]:
        """Analyze historical engagement patterns for intelligent scheduling."""
        # Mock engagement pattern analysis
        return {
            'peak_engagement_hours': [10, 14, 16],  # 10 AM, 2 PM, 4 PM
            'low_engagement_hours': [12, 18, 19],   # Lunch and end of day
            'best_days': ['Tuesday', 'Wednesday', 'Thursday'],
            'response_time_by_hour': {
                str(h): max(15, 120 - h * 3) for h in range(9, 18)  # Faster response during work hours
            },
            'engagement_score_by_hour': {
                str(h): max(0.3, 0.9 - abs(h - 14) * 0.05) for h in range(24)  # Peak at 2 PM
            }
        }