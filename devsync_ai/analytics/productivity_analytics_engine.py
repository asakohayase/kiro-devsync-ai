"""
Team Productivity Analytics Engine for DevSync AI.

This module provides comprehensive analytics on team productivity,
sprint performance, and collaboration patterns with AI-powered insights.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import numpy as np
from collections import defaultdict

from devsync_ai.hooks.hook_registry_manager import get_hook_registry_manager


logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    """Direction of trend analysis."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    UNKNOWN = "unknown"


class ProductivityMetric(Enum):
    """Types of productivity metrics."""
    SPRINT_VELOCITY = "sprint_velocity"
    BLOCKER_RESOLUTION = "blocker_resolution"
    RESPONSE_TIME = "response_time"
    COLLABORATION = "collaboration"
    AUTOMATION_EFFICIENCY = "automation_efficiency"
    COMMUNICATION_REDUCTION = "communication_reduction"


@dataclass
class SprintAnalytics:
    """Sprint performance analytics."""
    sprint_id: str
    team_id: str
    start_date: datetime
    end_date: datetime
    planned_story_points: int
    completed_story_points: int
    velocity: float
    completion_rate: float
    blocker_count: int
    average_blocker_resolution_time: float
    automation_impact_score: float
    predictive_success_probability: float
    risk_factors: List[str]
    improvement_suggestions: List[str]


@dataclass
class BlockerAnalytics:
    """Blocker resolution analytics."""
    blocker_id: str
    ticket_key: str
    team_id: str
    blocker_type: str
    severity: str
    detected_at: datetime
    resolved_at: Optional[datetime]
    resolution_time_hours: Optional[float]
    automated_detection: bool
    escalation_count: int
    root_cause: Optional[str]
    prevention_suggestions: List[str]


@dataclass
class TeamCollaborationMetrics:
    """Team collaboration and communication metrics."""
    team_id: str
    period_start: datetime
    period_end: datetime
    total_interactions: int
    automated_notifications: int
    manual_status_updates: int
    cross_team_communications: int
    response_time_improvement: float
    collaboration_efficiency_score: float
    communication_patterns: Dict[str, Any]
    productivity_heatmap: Dict[str, float]


@dataclass
class ProductivityInsight:
    """AI-generated productivity insight."""
    insight_id: str
    team_id: str
    metric_type: ProductivityMetric
    insight_text: str
    confidence_score: float
    impact_level: str  # "low", "medium", "high"
    actionable_recommendations: List[str]
    supporting_data: Dict[str, Any]
    generated_at: datetime


class ProductivityAnalyticsEngine:
    """
    Advanced analytics engine for team productivity and performance insights.
    
    Provides comprehensive analysis of team performance, sprint success,
    blocker patterns, and automation impact with AI-powered recommendations.
    """
    
    def __init__(self):
        """Initialize the productivity analytics engine."""
        self.sprint_analytics: Dict[str, SprintAnalytics] = {}
        self.blocker_analytics: Dict[str, BlockerAnalytics] = {}
        self.team_collaboration_metrics: Dict[str, TeamCollaborationMetrics] = {}
        self.productivity_insights: List[ProductivityInsight] = []
        
        # Historical data for trend analysis
        self.historical_velocity: Dict[str, List[float]] = defaultdict(list)
        self.historical_blocker_times: Dict[str, List[float]] = defaultdict(list)
        self.historical_response_times: Dict[str, List[float]] = defaultdict(list)
        
        # Baseline metrics (before automation)
        self.baseline_metrics = {
            'average_sprint_velocity': 25.0,
            'average_blocker_resolution_hours': 48.0,
            'average_response_time_minutes': 120.0,
            'manual_status_updates_per_sprint': 150,
            'cross_team_communication_overhead': 0.25
        }
    
    async def analyze_sprint_performance(
        self, 
        team_id: str, 
        sprint_id: str,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> SprintAnalytics:
        """
        Analyze sprint performance with automation impact assessment.
        
        Args:
            team_id: Team identifier
            sprint_id: Sprint identifier
            time_range: Optional time range for analysis
            
        Returns:
            Comprehensive sprint analytics
        """
        if not time_range:
            # Default to last 2 weeks
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=14)
            time_range = (start_date, end_date)
        
        start_date, end_date = time_range
        
        # Get hook execution data for the sprint period
        registry_manager = await get_hook_registry_manager()
        hook_metrics = []
        
        if registry_manager:
            all_hooks = await registry_manager.get_all_hook_statuses()
            team_hooks = [h for h in all_hooks if h['team_id'] == team_id]
            hook_metrics = team_hooks
        
        # Calculate sprint metrics
        planned_story_points = 30  # Mock data - would come from JIRA
        completed_story_points = 28  # Mock data - would come from JIRA
        velocity = completed_story_points
        completion_rate = completed_story_points / planned_story_points if planned_story_points > 0 else 0.0
        
        # Analyze blocker impact
        blocker_count = len([h for h in hook_metrics if 'blocker' in h['hook_type'].lower()])
        average_blocker_resolution_time = await self._calculate_average_blocker_resolution_time(team_id, time_range)
        
        # Calculate automation impact
        automation_impact_score = await self._calculate_automation_impact(team_id, hook_metrics)
        
        # Predictive analysis
        predictive_success_probability = await self._predict_sprint_success(
            team_id, velocity, blocker_count, automation_impact_score
        )
        
        # Identify risk factors
        risk_factors = await self._identify_sprint_risk_factors(
            team_id, velocity, blocker_count, completion_rate
        )
        
        # Generate improvement suggestions
        improvement_suggestions = await self._generate_sprint_improvements(
            team_id, velocity, blocker_count, automation_impact_score
        )
        
        sprint_analytics = SprintAnalytics(
            sprint_id=sprint_id,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
            planned_story_points=planned_story_points,
            completed_story_points=completed_story_points,
            velocity=velocity,
            completion_rate=completion_rate,
            blocker_count=blocker_count,
            average_blocker_resolution_time=average_blocker_resolution_time,
            automation_impact_score=automation_impact_score,
            predictive_success_probability=predictive_success_probability,
            risk_factors=risk_factors,
            improvement_suggestions=improvement_suggestions
        )
        
        # Store for historical analysis
        self.sprint_analytics[f"{team_id}_{sprint_id}"] = sprint_analytics
        self.historical_velocity[team_id].append(velocity)
        
        return sprint_analytics
    
    async def analyze_blocker_patterns(
        self, 
        team_id: str,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> List[BlockerAnalytics]:
        """
        Analyze blocker patterns and resolution effectiveness.
        
        Args:
            team_id: Team identifier
            time_range: Time range for analysis
            
        Returns:
            List of blocker analytics
        """
        if not time_range:
            # Default to last 30 days
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            time_range = (start_date, end_date)
        
        # Mock blocker data - would come from actual hook execution logs
        mock_blockers = [
            {
                'blocker_id': 'BLK-001',
                'ticket_key': 'PROJ-123',
                'blocker_type': 'dependency',
                'severity': 'high',
                'detected_at': datetime.now(timezone.utc) - timedelta(hours=48),
                'resolved_at': datetime.now(timezone.utc) - timedelta(hours=24),
                'automated_detection': True,
                'escalation_count': 1
            },
            {
                'blocker_id': 'BLK-002',
                'ticket_key': 'PROJ-124',
                'blocker_type': 'technical',
                'severity': 'medium',
                'detected_at': datetime.now(timezone.utc) - timedelta(hours=72),
                'resolved_at': datetime.now(timezone.utc) - timedelta(hours=12),
                'automated_detection': True,
                'escalation_count': 0
            }
        ]
        
        blocker_analytics = []
        
        for blocker_data in mock_blockers:
            resolution_time = None
            if blocker_data['resolved_at']:
                resolution_time = (blocker_data['resolved_at'] - blocker_data['detected_at']).total_seconds() / 3600
            
            # Analyze root cause
            root_cause = await self._analyze_blocker_root_cause(blocker_data)
            
            # Generate prevention suggestions
            prevention_suggestions = await self._generate_blocker_prevention_suggestions(blocker_data)
            
            analytics = BlockerAnalytics(
                blocker_id=blocker_data['blocker_id'],
                ticket_key=blocker_data['ticket_key'],
                team_id=team_id,
                blocker_type=blocker_data['blocker_type'],
                severity=blocker_data['severity'],
                detected_at=blocker_data['detected_at'],
                resolved_at=blocker_data['resolved_at'],
                resolution_time_hours=resolution_time,
                automated_detection=blocker_data['automated_detection'],
                escalation_count=blocker_data['escalation_count'],
                root_cause=root_cause,
                prevention_suggestions=prevention_suggestions
            )
            
            blocker_analytics.append(analytics)
            self.blocker_analytics[blocker_data['blocker_id']] = analytics
            
            if resolution_time:
                self.historical_blocker_times[team_id].append(resolution_time)
        
        return blocker_analytics
    
    async def analyze_team_collaboration(
        self, 
        team_id: str,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> TeamCollaborationMetrics:
        """
        Analyze team collaboration patterns and communication efficiency.
        
        Args:
            team_id: Team identifier
            time_range: Time range for analysis
            
        Returns:
            Team collaboration metrics
        """
        if not time_range:
            # Default to last 7 days
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=7)
            time_range = (start_date, end_date)
        
        start_date, end_date = time_range
        
        # Get hook execution data
        registry_manager = await get_hook_registry_manager()
        total_interactions = 0
        automated_notifications = 0
        
        if registry_manager:
            team_hooks = await registry_manager.get_all_hook_statuses()
            team_hooks = [h for h in team_hooks if h['team_id'] == team_id]
            
            for hook in team_hooks:
                stats = hook['statistics']
                total_interactions += stats['total_executions']
                automated_notifications += stats['total_executions']
        
        # Calculate metrics
        manual_status_updates = max(0, self.baseline_metrics['manual_status_updates_per_sprint'] - automated_notifications)
        cross_team_communications = int(total_interactions * 0.3)  # Mock calculation
        
        # Calculate improvements
        baseline_response_time = self.baseline_metrics['average_response_time_minutes']
        current_response_time = max(15, baseline_response_time - (automated_notifications * 0.5))
        response_time_improvement = (baseline_response_time - current_response_time) / baseline_response_time
        
        # Collaboration efficiency score (0-100)
        automation_factor = min(1.0, automated_notifications / 100)
        manual_reduction_factor = 1.0 - (manual_status_updates / self.baseline_metrics['manual_status_updates_per_sprint'])
        collaboration_efficiency_score = (automation_factor * 0.6 + manual_reduction_factor * 0.4) * 100
        
        # Generate communication patterns
        communication_patterns = {
            'peak_hours': [9, 10, 11, 14, 15, 16],  # Mock data
            'notification_distribution': {
                'status_changes': 0.4,
                'blockers': 0.2,
                'assignments': 0.25,
                'comments': 0.15
            },
            'response_time_by_hour': {str(h): max(10, 60 - h * 2) for h in range(24)}
        }
        
        # Generate productivity heatmap (hour of day -> productivity score)
        productivity_heatmap = {}
        for hour in range(24):
            if 9 <= hour <= 17:  # Work hours
                base_productivity = 0.8
                automation_boost = min(0.2, automated_notifications / 500)
                productivity_heatmap[str(hour)] = min(1.0, base_productivity + automation_boost)
            else:
                productivity_heatmap[str(hour)] = 0.1
        
        collaboration_metrics = TeamCollaborationMetrics(
            team_id=team_id,
            period_start=start_date,
            period_end=end_date,
            total_interactions=total_interactions,
            automated_notifications=automated_notifications,
            manual_status_updates=manual_status_updates,
            cross_team_communications=cross_team_communications,
            response_time_improvement=response_time_improvement,
            collaboration_efficiency_score=collaboration_efficiency_score,
            communication_patterns=communication_patterns,
            productivity_heatmap=productivity_heatmap
        )
        
        self.team_collaboration_metrics[team_id] = collaboration_metrics
        return collaboration_metrics
    
    async def generate_productivity_insights(self, team_id: str) -> List[ProductivityInsight]:
        """
        Generate AI-powered productivity insights for a team.
        
        Args:
            team_id: Team identifier
            
        Returns:
            List of productivity insights with recommendations
        """
        insights = []
        
        # Analyze sprint velocity trends
        if team_id in self.historical_velocity and len(self.historical_velocity[team_id]) >= 3:
            velocity_trend = await self._analyze_velocity_trend(team_id)
            if velocity_trend['direction'] == TrendDirection.IMPROVING:
                insights.append(ProductivityInsight(
                    insight_id=f"velocity_improvement_{team_id}",
                    team_id=team_id,
                    metric_type=ProductivityMetric.SPRINT_VELOCITY,
                    insight_text=f"Sprint velocity has improved by {velocity_trend['improvement']:.1%} over the last 3 sprints, likely due to automated coordination reducing manual overhead.",
                    confidence_score=0.85,
                    impact_level="high",
                    actionable_recommendations=[
                        "Continue current automation practices",
                        "Consider expanding hook coverage to more ticket types",
                        "Share successful patterns with other teams"
                    ],
                    supporting_data=velocity_trend,
                    generated_at=datetime.now(timezone.utc)
                ))
        
        # Analyze blocker resolution improvements
        if team_id in self.historical_blocker_times and len(self.historical_blocker_times[team_id]) >= 5:
            blocker_trend = await self._analyze_blocker_resolution_trend(team_id)
            if blocker_trend['average_time'] < self.baseline_metrics['average_blocker_resolution_hours']:
                improvement = (self.baseline_metrics['average_blocker_resolution_hours'] - blocker_trend['average_time']) / self.baseline_metrics['average_blocker_resolution_hours']
                insights.append(ProductivityInsight(
                    insight_id=f"blocker_resolution_{team_id}",
                    team_id=team_id,
                    metric_type=ProductivityMetric.BLOCKER_RESOLUTION,
                    insight_text=f"Blocker resolution time has improved by {improvement:.1%} with automated detection and escalation, reducing from {self.baseline_metrics['average_blocker_resolution_hours']:.1f}h to {blocker_trend['average_time']:.1f}h average.",
                    confidence_score=0.90,
                    impact_level="high",
                    actionable_recommendations=[
                        "Implement proactive blocker detection patterns",
                        "Enhance escalation rules for critical blockers",
                        "Create blocker prevention playbooks"
                    ],
                    supporting_data=blocker_trend,
                    generated_at=datetime.now(timezone.utc)
                ))
        
        # Analyze collaboration efficiency
        if team_id in self.team_collaboration_metrics:
            collab_metrics = self.team_collaboration_metrics[team_id]
            if collab_metrics.collaboration_efficiency_score > 75:
                insights.append(ProductivityInsight(
                    insight_id=f"collaboration_efficiency_{team_id}",
                    team_id=team_id,
                    metric_type=ProductivityMetric.COLLABORATION,
                    insight_text=f"Team collaboration efficiency is excellent at {collab_metrics.collaboration_efficiency_score:.1f}/100, with {collab_metrics.response_time_improvement:.1%} improvement in response times due to automated notifications.",
                    confidence_score=0.80,
                    impact_level="medium",
                    actionable_recommendations=[
                        "Maintain current notification cadence",
                        "Consider cross-team collaboration patterns",
                        "Optimize notification timing for peak productivity hours"
                    ],
                    supporting_data={
                        'efficiency_score': collab_metrics.collaboration_efficiency_score,
                        'response_improvement': collab_metrics.response_time_improvement,
                        'automation_ratio': collab_metrics.automated_notifications / max(1, collab_metrics.total_interactions)
                    },
                    generated_at=datetime.now(timezone.utc)
                ))
        
        # Store insights
        self.productivity_insights.extend(insights)
        
        return insights
    
    async def predict_sprint_success(
        self, 
        team_id: str, 
        current_velocity: float,
        current_blockers: int,
        days_remaining: int
    ) -> Dict[str, Any]:
        """
        Predict sprint success probability using historical data and current metrics.
        
        Args:
            team_id: Team identifier
            current_velocity: Current sprint velocity
            current_blockers: Number of active blockers
            days_remaining: Days remaining in sprint
            
        Returns:
            Sprint success prediction with confidence and risk factors
        """
        # Get historical performance
        historical_velocities = self.historical_velocity.get(team_id, [])
        if not historical_velocities:
            historical_velocities = [self.baseline_metrics['average_sprint_velocity']]
        
        avg_historical_velocity = statistics.mean(historical_velocities)
        velocity_variance = statistics.variance(historical_velocities) if len(historical_velocities) > 1 else 0
        
        # Calculate success probability factors
        velocity_factor = min(1.0, current_velocity / avg_historical_velocity)
        blocker_factor = max(0.1, 1.0 - (current_blockers * 0.15))  # Each blocker reduces probability by 15%
        time_factor = max(0.2, days_remaining / 14.0)  # Assuming 2-week sprints
        
        # Automation impact factor
        registry_manager = await get_hook_registry_manager()
        automation_factor = 1.0
        if registry_manager:
            team_hooks = await registry_manager.get_all_hook_statuses()
            team_hooks = [h for h in team_hooks if h['team_id'] == team_id]
            if team_hooks:
                avg_success_rate = statistics.mean([h['statistics']['success_rate'] for h in team_hooks])
                automation_factor = 0.8 + (avg_success_rate * 0.2)  # 80% base + 20% from automation
        
        # Calculate overall success probability
        success_probability = velocity_factor * blocker_factor * time_factor * automation_factor
        success_probability = max(0.1, min(0.95, success_probability))  # Clamp between 10% and 95%
        
        # Determine confidence level
        confidence = 1.0 - (velocity_variance / max(1, avg_historical_velocity))
        confidence = max(0.5, min(0.95, confidence))
        
        # Identify risk factors
        risk_factors = []
        if velocity_factor < 0.8:
            risk_factors.append("Below average velocity")
        if current_blockers > 2:
            risk_factors.append("High number of active blockers")
        if days_remaining < 3:
            risk_factors.append("Limited time remaining")
        if automation_factor < 0.9:
            risk_factors.append("Automation system performance issues")
        
        # Generate recommendations
        recommendations = []
        if velocity_factor < 0.8:
            recommendations.append("Focus on completing high-priority items")
        if current_blockers > 0:
            recommendations.append("Prioritize blocker resolution")
        if days_remaining < 5:
            recommendations.append("Consider scope reduction for non-critical items")
        
        return {
            'success_probability': success_probability,
            'confidence_level': confidence,
            'risk_factors': risk_factors,
            'recommendations': recommendations,
            'contributing_factors': {
                'velocity_factor': velocity_factor,
                'blocker_factor': blocker_factor,
                'time_factor': time_factor,
                'automation_factor': automation_factor
            },
            'historical_context': {
                'average_velocity': avg_historical_velocity,
                'velocity_variance': velocity_variance,
                'sprint_count': len(historical_velocities)
            }
        }
    
    # Helper methods
    async def _calculate_average_blocker_resolution_time(
        self, 
        team_id: str, 
        time_range: Tuple[datetime, datetime]
    ) -> float:
        """Calculate average blocker resolution time for the team."""
        if team_id in self.historical_blocker_times and self.historical_blocker_times[team_id]:
            return statistics.mean(self.historical_blocker_times[team_id])
        return self.baseline_metrics['average_blocker_resolution_hours']
    
    async def _calculate_automation_impact(self, team_id: str, hook_metrics: List[Dict[str, Any]]) -> float:
        """Calculate automation impact score (0-100)."""
        if not hook_metrics:
            return 0.0
        
        total_executions = sum(h['statistics']['total_executions'] for h in hook_metrics)
        avg_success_rate = statistics.mean([h['statistics']['success_rate'] for h in hook_metrics])
        
        # Impact score based on execution volume and success rate
        volume_factor = min(1.0, total_executions / 100)  # Normalize to 100 executions
        quality_factor = avg_success_rate
        
        return (volume_factor * 0.6 + quality_factor * 0.4) * 100
    
    async def _predict_sprint_success(
        self, 
        team_id: str, 
        velocity: float, 
        blocker_count: int, 
        automation_score: float
    ) -> float:
        """Predict sprint success probability."""
        base_probability = 0.7  # 70% base success rate
        
        # Adjust based on velocity
        velocity_adjustment = (velocity - self.baseline_metrics['average_sprint_velocity']) / self.baseline_metrics['average_sprint_velocity'] * 0.2
        
        # Adjust based on blockers
        blocker_adjustment = -blocker_count * 0.1
        
        # Adjust based on automation
        automation_adjustment = (automation_score - 50) / 100 * 0.1
        
        probability = base_probability + velocity_adjustment + blocker_adjustment + automation_adjustment
        return max(0.1, min(0.95, probability))
    
    async def _identify_sprint_risk_factors(
        self, 
        team_id: str, 
        velocity: float, 
        blocker_count: int, 
        completion_rate: float
    ) -> List[str]:
        """Identify risk factors for sprint success."""
        risk_factors = []
        
        if velocity < self.baseline_metrics['average_sprint_velocity'] * 0.8:
            risk_factors.append("Below average velocity")
        
        if blocker_count > 3:
            risk_factors.append("High number of blockers")
        
        if completion_rate < 0.8:
            risk_factors.append("Low completion rate")
        
        # Check for declining trends
        if team_id in self.historical_velocity and len(self.historical_velocity[team_id]) >= 3:
            recent_velocities = self.historical_velocity[team_id][-3:]
            if len(recent_velocities) >= 2 and recent_velocities[-1] < recent_velocities[-2]:
                risk_factors.append("Declining velocity trend")
        
        return risk_factors
    
    async def _generate_sprint_improvements(
        self, 
        team_id: str, 
        velocity: float, 
        blocker_count: int, 
        automation_score: float
    ) -> List[str]:
        """Generate improvement suggestions for sprint performance."""
        suggestions = []
        
        if velocity < self.baseline_metrics['average_sprint_velocity']:
            suggestions.append("Increase automation coverage to reduce manual overhead")
        
        if blocker_count > 2:
            suggestions.append("Implement proactive blocker detection and early escalation")
        
        if automation_score < 70:
            suggestions.append("Optimize hook configurations for better performance")
            suggestions.append("Review and update notification channels for faster response")
        
        suggestions.append("Conduct retrospective to identify process improvements")
        suggestions.append("Consider pair programming for complex tasks")
        
        return suggestions
    
    async def _analyze_blocker_root_cause(self, blocker_data: Dict[str, Any]) -> Optional[str]:
        """Analyze root cause of blocker."""
        blocker_type = blocker_data.get('blocker_type', '')
        
        root_causes = {
            'dependency': 'External team dependency not properly coordinated',
            'technical': 'Technical complexity underestimated during planning',
            'resource': 'Insufficient team capacity or expertise',
            'external': 'Third-party service or vendor issue'
        }
        
        return root_causes.get(blocker_type, 'Unknown root cause')
    
    async def _generate_blocker_prevention_suggestions(self, blocker_data: Dict[str, Any]) -> List[str]:
        """Generate suggestions to prevent similar blockers."""
        blocker_type = blocker_data.get('blocker_type', '')
        
        suggestions_map = {
            'dependency': [
                "Improve cross-team communication and planning",
                "Create dependency tracking dashboard",
                "Implement early dependency identification in planning"
            ],
            'technical': [
                "Conduct technical spike before implementation",
                "Improve code review process",
                "Create technical documentation and knowledge sharing"
            ],
            'resource': [
                "Better capacity planning and workload distribution",
                "Cross-training team members on critical skills",
                "Implement workload monitoring and alerts"
            ],
            'external': [
                "Create fallback plans for external dependencies",
                "Improve vendor communication and SLA monitoring",
                "Implement circuit breaker patterns for external services"
            ]
        }
        
        return suggestions_map.get(blocker_type, ["Improve planning and risk assessment"])
    
    async def _analyze_velocity_trend(self, team_id: str) -> Dict[str, Any]:
        """Analyze velocity trend for a team."""
        velocities = self.historical_velocity[team_id]
        if len(velocities) < 3:
            return {'direction': TrendDirection.UNKNOWN, 'improvement': 0.0}
        
        recent_avg = statistics.mean(velocities[-3:])
        older_avg = statistics.mean(velocities[:-3]) if len(velocities) > 3 else velocities[0]
        
        improvement = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0.0
        
        if improvement > 0.1:
            direction = TrendDirection.IMPROVING
        elif improvement < -0.1:
            direction = TrendDirection.DECLINING
        else:
            direction = TrendDirection.STABLE
        
        return {
            'direction': direction,
            'improvement': improvement,
            'recent_average': recent_avg,
            'historical_average': older_avg,
            'data_points': len(velocities)
        }
    
    async def _analyze_blocker_resolution_trend(self, team_id: str) -> Dict[str, Any]:
        """Analyze blocker resolution time trend."""
        resolution_times = self.historical_blocker_times[team_id]
        
        return {
            'average_time': statistics.mean(resolution_times),
            'median_time': statistics.median(resolution_times),
            'min_time': min(resolution_times),
            'max_time': max(resolution_times),
            'improvement_vs_baseline': (self.baseline_metrics['average_blocker_resolution_hours'] - statistics.mean(resolution_times)) / self.baseline_metrics['average_blocker_resolution_hours']
        }