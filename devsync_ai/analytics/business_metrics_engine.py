"""
Business Metrics Analytics Engine for JIRA Agent Hooks.

This module provides comprehensive business impact analysis, productivity tracking,
and team performance metrics for the hook system.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import json

from devsync_ai.analytics.monitoring_data_manager import (
    get_monitoring_data_manager,
    MonitoringDataManager,
    BusinessMetric
)


logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Business metric types."""
    NOTIFICATION_DELIVERY_RATE = "notification_delivery_rate"
    RESPONSE_TIME_IMPROVEMENT = "response_time_improvement"
    BLOCKED_TICKET_RESOLUTION_TIME = "blocked_ticket_resolution_time"
    TEAM_COLLABORATION_INDEX = "team_collaboration_index"
    SPRINT_VELOCITY_IMPROVEMENT = "sprint_velocity_improvement"
    ISSUE_ASSIGNMENT_EFFICIENCY = "issue_assignment_efficiency"
    STATUS_TRANSITION_VELOCITY = "status_transition_velocity"
    BOTTLENECK_DETECTION_RATE = "bottleneck_detection_rate"
    AUTOMATION_COVERAGE = "automation_coverage"
    USER_ENGAGEMENT_RATE = "user_engagement_rate"


class TrendDirection(Enum):
    """Trend direction indicators."""
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    UNKNOWN = "unknown"


@dataclass
class ProductivityMetrics:
    """Team productivity metrics."""
    team_id: str
    time_period: Tuple[datetime, datetime]
    
    # Core metrics
    total_notifications_sent: int
    notification_delivery_rate: float
    avg_response_time_hours: float
    blocked_tickets_resolved: int
    avg_blocked_resolution_time_hours: float
    
    # Collaboration metrics
    team_members_engaged: int
    cross_team_interactions: int
    collaboration_index: float
    
    # Velocity metrics
    sprint_velocity_points: float
    velocity_improvement_percent: float
    issue_throughput_per_day: float
    
    # Efficiency metrics
    automation_coverage_percent: float
    manual_intervention_rate: float
    bottleneck_detection_count: int
    
    # Engagement metrics
    user_interaction_rate: float
    hook_utilization_rate: float
    
    # Trend indicators
    productivity_trend: TrendDirection
    trend_strength: float  # 0-1


@dataclass
class BusinessImpactReport:
    """Comprehensive business impact report."""
    report_id: str
    generated_at: datetime
    time_period: Tuple[datetime, datetime]
    
    # Summary metrics
    total_teams: int
    total_hooks_active: int
    total_notifications_sent: int
    overall_productivity_score: float
    
    # Team-level metrics
    team_metrics: List[ProductivityMetrics]
    
    # System-wide improvements
    avg_response_time_improvement: float
    blocked_ticket_reduction_percent: float
    automation_efficiency_gain: float
    
    # ROI indicators
    estimated_time_saved_hours: float
    estimated_cost_savings: float
    developer_satisfaction_score: float
    
    # Recommendations
    optimization_recommendations: List[Dict[str, Any]]
    performance_insights: List[Dict[str, Any]]


@dataclass
class ChannelEffectivenessMetrics:
    """Channel routing effectiveness metrics."""
    channel: str
    time_period: Tuple[datetime, datetime]
    
    total_messages: int
    delivery_success_rate: float
    avg_response_time_ms: float
    user_engagement_rate: float
    
    # Routing analysis
    routing_reasons: Dict[str, int]
    urgency_distribution: Dict[str, int]
    team_distribution: Dict[str, int]
    
    # Effectiveness scores
    relevance_score: float  # How relevant messages are to recipients
    timeliness_score: float  # How timely the notifications are
    action_rate: float  # Rate of user actions taken on notifications
    
    effectiveness_trend: TrendDirection


@dataclass
class HookOptimizationInsight:
    """Hook optimization insight."""
    hook_id: str
    hook_type: str
    team_id: str
    
    insight_type: str  # "performance", "configuration", "usage"
    priority: str  # "high", "medium", "low"
    
    title: str
    description: str
    current_state: Dict[str, Any]
    recommended_action: str
    expected_improvement: Dict[str, float]
    
    confidence_score: float  # 0-1


class BusinessMetricsEngine:
    """
    Comprehensive business metrics analytics engine.
    
    Provides business impact analysis, productivity tracking, ROI calculation,
    and optimization recommendations for the JIRA Agent Hook system.
    """
    
    def __init__(self):
        """Initialize the business metrics engine."""
        self.data_manager: Optional[MonitoringDataManager] = None
        self._initialized = False
        
        # Metric calculation cache
        self._metrics_cache: Dict[str, Any] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_ttl_minutes = 15
        
        # Business constants for ROI calculation
        self.avg_developer_hourly_cost = 75.0  # USD
        self.avg_response_time_baseline_hours = 4.0
        self.productivity_baseline_score = 70.0
    
    async def initialize(self):
        """Initialize the business metrics engine."""
        if self._initialized:
            return
        
        self.data_manager = await get_monitoring_data_manager()
        self._initialized = True
        
        logger.info("Business Metrics Engine initialized")
    
    async def calculate_team_productivity_metrics(
        self,
        team_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[ProductivityMetrics]:
        """
        Calculate comprehensive productivity metrics for a team.
        
        Args:
            team_id: Team identifier
            start_time: Start time for analysis
            end_time: End time for analysis
            
        Returns:
            Team productivity metrics
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Check cache first
            cache_key = f"team_productivity_{team_id}_{start_time.isoformat()}_{end_time.isoformat()}"
            if self._is_cache_valid(cache_key):
                return self._metrics_cache[cache_key]
            
            # Get team productivity data from data manager
            team_data = await self.data_manager.get_team_productivity_metrics(
                team_id, start_time, end_time
            )
            
            if not team_data:
                return None
            
            # Calculate additional metrics
            time_span_hours = (end_time - start_time).total_seconds() / 3600
            
            # Get notification delivery metrics
            notification_metrics = await self._calculate_notification_metrics(
                team_id, start_time, end_time
            )
            
            # Get collaboration metrics
            collaboration_metrics = await self._calculate_collaboration_metrics(
                team_id, start_time, end_time
            )
            
            # Get velocity metrics
            velocity_metrics = await self._calculate_velocity_metrics(
                team_id, start_time, end_time
            )
            
            # Calculate trend
            trend_data = await self._calculate_productivity_trend(
                team_id, start_time, end_time
            )
            
            metrics = ProductivityMetrics(
                team_id=team_id,
                time_period=(start_time, end_time),
                
                # Core metrics
                total_notifications_sent=notification_metrics.get('total_sent', 0),
                notification_delivery_rate=team_data.get('notification_delivery_rate', 0.0),
                avg_response_time_hours=team_data.get('average_response_time', 0.0) / 1000 / 3600,  # ms to hours
                blocked_tickets_resolved=velocity_metrics.get('blocked_resolved', 0),
                avg_blocked_resolution_time_hours=team_data.get('blocked_ticket_resolution_improvement', 24.0),
                
                # Collaboration metrics
                team_members_engaged=collaboration_metrics.get('members_engaged', 1),
                cross_team_interactions=collaboration_metrics.get('cross_team_interactions', 0),
                collaboration_index=collaboration_metrics.get('collaboration_index', 50.0),
                
                # Velocity metrics
                sprint_velocity_points=velocity_metrics.get('velocity_points', 0.0),
                velocity_improvement_percent=team_data.get('sprint_velocity_improvement', 0.0),
                issue_throughput_per_day=velocity_metrics.get('throughput_per_day', 0.0),
                
                # Efficiency metrics
                automation_coverage_percent=velocity_metrics.get('automation_coverage', 0.0),
                manual_intervention_rate=1.0 - (velocity_metrics.get('automation_coverage', 0.0) / 100.0),
                bottleneck_detection_count=velocity_metrics.get('bottlenecks_detected', 0),
                
                # Engagement metrics
                user_interaction_rate=notification_metrics.get('interaction_rate', 0.0),
                hook_utilization_rate=min(100.0, team_data.get('active_hooks', 0) / max(team_data.get('total_hooks', 1), 1) * 100),
                
                # Trend indicators
                productivity_trend=trend_data.get('direction', TrendDirection.STABLE),
                trend_strength=trend_data.get('strength', 0.0)
            )
            
            # Cache the result
            self._cache_result(cache_key, metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate team productivity metrics: {e}", exc_info=True)
            return None
    
    async def _calculate_notification_metrics(
        self,
        team_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate notification-related metrics."""
        try:
            # This would typically query notification analytics tables
            # For now, we'll use mock data based on hook executions
            
            # Get hook executions for the team
            # In a real implementation, this would query the database directly
            
            return {
                'total_sent': 150,  # Mock data
                'delivery_rate': 0.95,
                'interaction_rate': 0.35,
                'response_time_improvement': 2.5  # hours
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate notification metrics: {e}")
            return {}
    
    async def _calculate_collaboration_metrics(
        self,
        team_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate collaboration-related metrics."""
        try:
            # Mock collaboration metrics
            # In a real implementation, this would analyze:
            # - Cross-team hook triggers
            # - Shared channel notifications
            # - Multi-team issue assignments
            
            return {
                'members_engaged': 8,
                'cross_team_interactions': 25,
                'collaboration_index': 78.5,
                'shared_notifications': 45
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate collaboration metrics: {e}")
            return {}
    
    async def _calculate_velocity_metrics(
        self,
        team_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate velocity and efficiency metrics."""
        try:
            # Mock velocity metrics
            # In a real implementation, this would analyze:
            # - JIRA issue transitions
            # - Sprint completion rates
            # - Blocked ticket resolution times
            # - Automation vs manual interventions
            
            return {
                'velocity_points': 85.0,
                'throughput_per_day': 12.5,
                'blocked_resolved': 8,
                'automation_coverage': 65.0,
                'bottlenecks_detected': 3
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate velocity metrics: {e}")
            return {}
    
    async def _calculate_productivity_trend(
        self,
        team_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate productivity trend analysis."""
        try:
            # Get historical data for trend analysis
            # Compare current period with previous period
            
            previous_start = start_time - (end_time - start_time)
            previous_end = start_time
            
            current_productivity = 75.0  # Mock current score
            previous_productivity = 70.0  # Mock previous score
            
            if current_productivity > previous_productivity * 1.05:
                direction = TrendDirection.IMPROVING
                strength = min(1.0, (current_productivity - previous_productivity) / previous_productivity)
            elif current_productivity < previous_productivity * 0.95:
                direction = TrendDirection.DECLINING
                strength = min(1.0, (previous_productivity - current_productivity) / previous_productivity)
            else:
                direction = TrendDirection.STABLE
                strength = 0.1
            
            return {
                'direction': direction,
                'strength': strength,
                'current_score': current_productivity,
                'previous_score': previous_productivity
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate productivity trend: {e}")
            return {'direction': TrendDirection.UNKNOWN, 'strength': 0.0}
    
    async def generate_business_impact_report(
        self,
        start_time: datetime,
        end_time: datetime,
        team_filter: Optional[str] = None
    ) -> BusinessImpactReport:
        """
        Generate comprehensive business impact report.
        
        Args:
            start_time: Start time for report
            end_time: End time for report
            team_filter: Optional team filter
            
        Returns:
            Business impact report
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            report_id = f"business_impact_{int(datetime.now().timestamp())}"
            
            # Get system health metrics
            system_health = await self.data_manager.get_system_health_metrics()
            
            # Get team metrics
            team_metrics = []
            teams_to_analyze = [team_filter] if team_filter else await self._get_active_teams(start_time, end_time)
            
            for team_id in teams_to_analyze:
                team_productivity = await self.calculate_team_productivity_metrics(
                    team_id, start_time, end_time
                )
                if team_productivity:
                    team_metrics.append(team_productivity)
            
            # Calculate system-wide improvements
            system_improvements = await self._calculate_system_improvements(
                team_metrics, start_time, end_time
            )
            
            # Calculate ROI metrics
            roi_metrics = await self._calculate_roi_metrics(team_metrics, start_time, end_time)
            
            # Generate optimization recommendations
            recommendations = await self._generate_optimization_recommendations(team_metrics)
            
            # Generate performance insights
            insights = await self._generate_performance_insights(team_metrics, system_health)
            
            # Calculate overall productivity score
            overall_score = statistics.mean([
                tm.collaboration_index for tm in team_metrics
            ]) if team_metrics else 0.0
            
            report = BusinessImpactReport(
                report_id=report_id,
                generated_at=datetime.now(timezone.utc),
                time_period=(start_time, end_time),
                
                # Summary metrics
                total_teams=len(team_metrics),
                total_hooks_active=system_health.active_hooks,
                total_notifications_sent=sum(tm.total_notifications_sent for tm in team_metrics),
                overall_productivity_score=overall_score,
                
                # Team-level metrics
                team_metrics=team_metrics,
                
                # System-wide improvements
                avg_response_time_improvement=system_improvements.get('response_time_improvement', 0.0),
                blocked_ticket_reduction_percent=system_improvements.get('blocked_ticket_reduction', 0.0),
                automation_efficiency_gain=system_improvements.get('automation_gain', 0.0),
                
                # ROI indicators
                estimated_time_saved_hours=roi_metrics.get('time_saved_hours', 0.0),
                estimated_cost_savings=roi_metrics.get('cost_savings', 0.0),
                developer_satisfaction_score=roi_metrics.get('satisfaction_score', 0.0),
                
                # Recommendations
                optimization_recommendations=recommendations,
                performance_insights=insights
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate business impact report: {e}", exc_info=True)
            return self._create_empty_report(start_time, end_time)
    
    async def _get_active_teams(self, start_time: datetime, end_time: datetime) -> List[str]:
        """Get list of active teams in the time period."""
        try:
            # This would query the database for teams with hook activity
            # For now, return mock team IDs
            return ["team-alpha", "team-beta", "team-gamma", "team-delta"]
            
        except Exception as e:
            logger.error(f"Failed to get active teams: {e}")
            return []
    
    async def _calculate_system_improvements(
        self,
        team_metrics: List[ProductivityMetrics],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, float]:
        """Calculate system-wide improvements."""
        try:
            if not team_metrics:
                return {}
            
            # Calculate averages across teams
            avg_response_time = statistics.mean([tm.avg_response_time_hours for tm in team_metrics])
            avg_blocked_resolution = statistics.mean([tm.avg_blocked_resolution_time_hours for tm in team_metrics])
            avg_automation_coverage = statistics.mean([tm.automation_coverage_percent for tm in team_metrics])
            
            # Calculate improvements (mock baseline comparison)
            baseline_response_time = self.avg_response_time_baseline_hours
            response_time_improvement = max(0, (baseline_response_time - avg_response_time) / baseline_response_time * 100)
            
            baseline_blocked_time = 48.0  # hours
            blocked_ticket_reduction = max(0, (baseline_blocked_time - avg_blocked_resolution) / baseline_blocked_time * 100)
            
            baseline_automation = 30.0  # percent
            automation_gain = max(0, avg_automation_coverage - baseline_automation)
            
            return {
                'response_time_improvement': response_time_improvement,
                'blocked_ticket_reduction': blocked_ticket_reduction,
                'automation_gain': automation_gain
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate system improvements: {e}")
            return {}
    
    async def _calculate_roi_metrics(
        self,
        team_metrics: List[ProductivityMetrics],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, float]:
        """Calculate ROI metrics."""
        try:
            if not team_metrics:
                return {}
            
            # Calculate time saved
            total_time_saved_hours = 0.0
            total_developers = 0
            
            for team_metric in team_metrics:
                # Time saved from faster response times
                response_time_saved = max(0, self.avg_response_time_baseline_hours - team_metric.avg_response_time_hours)
                notifications_count = team_metric.total_notifications_sent
                time_saved_per_notification = response_time_saved * 0.1  # Assume 10% of response time saved
                
                team_time_saved = notifications_count * time_saved_per_notification
                total_time_saved_hours += team_time_saved
                total_developers += team_metric.team_members_engaged
            
            # Calculate cost savings
            cost_savings = total_time_saved_hours * self.avg_developer_hourly_cost
            
            # Calculate satisfaction score (based on productivity improvements)
            avg_productivity = statistics.mean([
                tm.collaboration_index for tm in team_metrics
            ])
            satisfaction_score = min(100.0, avg_productivity * 1.2)  # Scale productivity to satisfaction
            
            return {
                'time_saved_hours': total_time_saved_hours,
                'cost_savings': cost_savings,
                'satisfaction_score': satisfaction_score,
                'developers_impacted': total_developers
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate ROI metrics: {e}")
            return {}
    
    async def _generate_optimization_recommendations(
        self,
        team_metrics: List[ProductivityMetrics]
    ) -> List[Dict[str, Any]]:
        """Generate optimization recommendations."""
        try:
            recommendations = []
            
            for team_metric in team_metrics:
                # Low notification delivery rate
                if team_metric.notification_delivery_rate < 0.9:
                    recommendations.append({
                        'type': 'notification_delivery',
                        'priority': 'high',
                        'team_id': team_metric.team_id,
                        'title': 'Improve Notification Delivery Rate',
                        'description': f'Team {team_metric.team_id} has a notification delivery rate of {team_metric.notification_delivery_rate:.1%}. Consider reviewing channel configurations and user preferences.',
                        'expected_improvement': '15% increase in team responsiveness',
                        'action_items': [
                            'Review Slack channel permissions',
                            'Verify webhook configurations',
                            'Check user notification preferences'
                        ]
                    })
                
                # High response time
                if team_metric.avg_response_time_hours > 6.0:
                    recommendations.append({
                        'type': 'response_time',
                        'priority': 'medium',
                        'team_id': team_metric.team_id,
                        'title': 'Reduce Response Time',
                        'description': f'Team {team_metric.team_id} has an average response time of {team_metric.avg_response_time_hours:.1f} hours. Consider implementing urgency-based routing.',
                        'expected_improvement': '30% faster issue resolution',
                        'action_items': [
                            'Implement priority-based notifications',
                            'Set up escalation rules',
                            'Configure work hours scheduling'
                        ]
                    })
                
                # Low automation coverage
                if team_metric.automation_coverage_percent < 50.0:
                    recommendations.append({
                        'type': 'automation',
                        'priority': 'medium',
                        'team_id': team_metric.team_id,
                        'title': 'Increase Automation Coverage',
                        'description': f'Team {team_metric.team_id} has {team_metric.automation_coverage_percent:.1f}% automation coverage. More hooks could be automated.',
                        'expected_improvement': '25% reduction in manual work',
                        'action_items': [
                            'Identify repetitive manual tasks',
                            'Create additional hook configurations',
                            'Implement smart assignment rules'
                        ]
                    })
                
                # Low collaboration index
                if team_metric.collaboration_index < 60.0:
                    recommendations.append({
                        'type': 'collaboration',
                        'priority': 'low',
                        'team_id': team_metric.team_id,
                        'title': 'Enhance Team Collaboration',
                        'description': f'Team {team_metric.team_id} has a collaboration index of {team_metric.collaboration_index:.1f}. Consider cross-team notification sharing.',
                        'expected_improvement': '20% better cross-team coordination',
                        'action_items': [
                            'Set up shared notification channels',
                            'Configure cross-team hook triggers',
                            'Implement team mention features'
                        ]
                    })
            
            # Sort by priority
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))
            
            return recommendations[:10]  # Return top 10 recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate optimization recommendations: {e}")
            return []
    
    async def _generate_performance_insights(
        self,
        team_metrics: List[ProductivityMetrics],
        system_health: Any
    ) -> List[Dict[str, Any]]:
        """Generate performance insights."""
        try:
            insights = []
            
            if team_metrics:
                # Top performing team
                top_team = max(team_metrics, key=lambda x: x.collaboration_index)
                insights.append({
                    'type': 'top_performer',
                    'title': 'Top Performing Team',
                    'description': f'Team {top_team.team_id} has the highest collaboration index at {top_team.collaboration_index:.1f}%',
                    'data': {
                        'team_id': top_team.team_id,
                        'collaboration_index': top_team.collaboration_index,
                        'notification_delivery_rate': top_team.notification_delivery_rate,
                        'automation_coverage': top_team.automation_coverage_percent
                    }
                })
                
                # Productivity trend analysis
                improving_teams = [tm for tm in team_metrics if tm.productivity_trend == TrendDirection.IMPROVING]
                if improving_teams:
                    insights.append({
                        'type': 'productivity_trend',
                        'title': 'Productivity Improvements',
                        'description': f'{len(improving_teams)} teams are showing productivity improvements',
                        'data': {
                            'improving_teams': len(improving_teams),
                            'total_teams': len(team_metrics),
                            'improvement_rate': len(improving_teams) / len(team_metrics)
                        }
                    })
                
                # Automation success
                high_automation_teams = [tm for tm in team_metrics if tm.automation_coverage_percent > 70.0]
                if high_automation_teams:
                    avg_response_time = statistics.mean([tm.avg_response_time_hours for tm in high_automation_teams])
                    insights.append({
                        'type': 'automation_impact',
                        'title': 'Automation Impact',
                        'description': f'Teams with >70% automation coverage have {avg_response_time:.1f}h average response time',
                        'data': {
                            'high_automation_teams': len(high_automation_teams),
                            'avg_response_time': avg_response_time,
                            'automation_threshold': 70.0
                        }
                    })
            
            # System health insights
            if system_health:
                if system_health.overall_success_rate > 0.95:
                    insights.append({
                        'type': 'system_reliability',
                        'title': 'High System Reliability',
                        'description': f'System maintains {system_health.overall_success_rate:.1%} success rate with {system_health.active_hooks} active hooks',
                        'data': {
                            'success_rate': system_health.overall_success_rate,
                            'active_hooks': system_health.active_hooks,
                            'total_executions': system_health.total_executions
                        }
                    })
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate performance insights: {e}")
            return []
    
    def _create_empty_report(self, start_time: datetime, end_time: datetime) -> BusinessImpactReport:
        """Create an empty report for error cases."""
        return BusinessImpactReport(
            report_id=f"error_report_{int(datetime.now().timestamp())}",
            generated_at=datetime.now(timezone.utc),
            time_period=(start_time, end_time),
            total_teams=0,
            total_hooks_active=0,
            total_notifications_sent=0,
            overall_productivity_score=0.0,
            team_metrics=[],
            avg_response_time_improvement=0.0,
            blocked_ticket_reduction_percent=0.0,
            automation_efficiency_gain=0.0,
            estimated_time_saved_hours=0.0,
            estimated_cost_savings=0.0,
            developer_satisfaction_score=0.0,
            optimization_recommendations=[],
            performance_insights=[]
        )
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid."""
        if cache_key not in self._cache_expiry:
            return False
        
        return datetime.now(timezone.utc) < self._cache_expiry[cache_key]
    
    def _cache_result(self, cache_key: str, result: Any):
        """Cache a result with expiry."""
        self._metrics_cache[cache_key] = result
        self._cache_expiry[cache_key] = datetime.now(timezone.utc) + timedelta(minutes=self._cache_ttl_minutes)
    
    async def calculate_channel_effectiveness(
        self,
        start_time: datetime,
        end_time: datetime,
        channel_filter: Optional[str] = None
    ) -> List[ChannelEffectivenessMetrics]:
        """
        Calculate channel routing effectiveness metrics.
        
        Args:
            start_time: Start time for analysis
            end_time: End time for analysis
            channel_filter: Optional channel filter
            
        Returns:
            List of channel effectiveness metrics
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Get webhook performance metrics (which include channel data)
            webhook_metrics = await self.data_manager.get_webhook_performance_metrics(
                start_time, end_time
            )
            
            channel_metrics = []
            
            # Mock channel effectiveness data
            # In a real implementation, this would analyze actual channel routing data
            channels = ['#general', '#dev-alerts', '#critical-issues', '#team-alpha'] if not channel_filter else [channel_filter]
            
            for channel in channels:
                metrics = ChannelEffectivenessMetrics(
                    channel=channel,
                    time_period=(start_time, end_time),
                    total_messages=150 + hash(channel) % 100,  # Mock data
                    delivery_success_rate=0.95 + (hash(channel) % 5) / 100,
                    avg_response_time_ms=1500 + (hash(channel) % 1000),
                    user_engagement_rate=0.35 + (hash(channel) % 20) / 100,
                    routing_reasons={
                        'urgency_high': 45,
                        'team_assignment': 78,
                        'keyword_match': 23,
                        'escalation': 12
                    },
                    urgency_distribution={
                        'critical': 15,
                        'high': 45,
                        'medium': 78,
                        'low': 32
                    },
                    team_distribution={
                        'team-alpha': 65,
                        'team-beta': 45,
                        'team-gamma': 32,
                        'cross-team': 18
                    },
                    relevance_score=0.85 + (hash(channel) % 10) / 100,
                    timeliness_score=0.78 + (hash(channel) % 15) / 100,
                    action_rate=0.42 + (hash(channel) % 12) / 100,
                    effectiveness_trend=TrendDirection.IMPROVING if hash(channel) % 2 else TrendDirection.STABLE
                )
                
                channel_metrics.append(metrics)
            
            return channel_metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate channel effectiveness: {e}", exc_info=True)
            return []
    
    async def generate_hook_optimization_insights(
        self,
        start_time: datetime,
        end_time: datetime,
        team_filter: Optional[str] = None
    ) -> List[HookOptimizationInsight]:
        """
        Generate hook optimization insights and recommendations.
        
        Args:
            start_time: Start time for analysis
            end_time: End time for analysis
            team_filter: Optional team filter
            
        Returns:
            List of optimization insights
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            insights = []
            
            # Mock optimization insights
            # In a real implementation, this would analyze hook performance data
            
            hook_configs = [
                {
                    'hook_id': 'jira-issue-created-001',
                    'hook_type': 'issue_created',
                    'team_id': 'team-alpha',
                    'performance': {'avg_time': 1200, 'success_rate': 0.98, 'usage': 'high'}
                },
                {
                    'hook_id': 'jira-status-changed-002',
                    'hook_type': 'status_transition',
                    'team_id': 'team-beta',
                    'performance': {'avg_time': 3500, 'success_rate': 0.85, 'usage': 'medium'}
                },
                {
                    'hook_id': 'jira-assignment-003',
                    'hook_type': 'assignment_changed',
                    'team_id': 'team-gamma',
                    'performance': {'avg_time': 800, 'success_rate': 0.99, 'usage': 'low'}
                }
            ]
            
            for config in hook_configs:
                if team_filter and config['team_id'] != team_filter:
                    continue
                
                perf = config['performance']
                
                # Performance optimization insight
                if perf['avg_time'] > 2000:
                    insights.append(HookOptimizationInsight(
                        hook_id=config['hook_id'],
                        hook_type=config['hook_type'],
                        team_id=config['team_id'],
                        insight_type='performance',
                        priority='high',
                        title='Slow Hook Execution',
                        description=f'Hook {config["hook_id"]} has high execution time of {perf["avg_time"]}ms',
                        current_state={
                            'avg_execution_time_ms': perf['avg_time'],
                            'success_rate': perf['success_rate']
                        },
                        recommended_action='Optimize hook logic and reduce external API calls',
                        expected_improvement={
                            'execution_time_reduction_percent': 40.0,
                            'reliability_improvement_percent': 5.0
                        },
                        confidence_score=0.85
                    ))
                
                # Success rate optimization
                if perf['success_rate'] < 0.9:
                    insights.append(HookOptimizationInsight(
                        hook_id=config['hook_id'],
                        hook_type=config['hook_type'],
                        team_id=config['team_id'],
                        insight_type='configuration',
                        priority='high',
                        title='Low Success Rate',
                        description=f'Hook {config["hook_id"]} has success rate of {perf["success_rate"]:.1%}',
                        current_state={
                            'success_rate': perf['success_rate'],
                            'error_patterns': ['timeout', 'api_limit', 'auth_failure']
                        },
                        recommended_action='Review error handling and implement retry logic',
                        expected_improvement={
                            'success_rate_improvement_percent': 10.0,
                            'error_reduction_percent': 60.0
                        },
                        confidence_score=0.92
                    ))
                
                # Usage optimization
                if perf['usage'] == 'low':
                    insights.append(HookOptimizationInsight(
                        hook_id=config['hook_id'],
                        hook_type=config['hook_type'],
                        team_id=config['team_id'],
                        insight_type='usage',
                        priority='low',
                        title='Underutilized Hook',
                        description=f'Hook {config["hook_id"]} has low usage despite good performance',
                        current_state={
                            'usage_level': perf['usage'],
                            'triggers_per_day': 2.5
                        },
                        recommended_action='Review hook configuration and expand trigger conditions',
                        expected_improvement={
                            'usage_increase_percent': 150.0,
                            'team_productivity_improvement_percent': 8.0
                        },
                        confidence_score=0.65
                    ))
            
            # Sort by priority and confidence
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            insights.sort(key=lambda x: (priority_order.get(x.priority, 3), -x.confidence_score))
            
            return insights[:15]  # Return top 15 insights
            
        except Exception as e:
            logger.error(f"Failed to generate hook optimization insights: {e}", exc_info=True)
            return []


# Global business metrics engine instance
_business_metrics_engine: Optional[BusinessMetricsEngine] = None


async def get_business_metrics_engine() -> BusinessMetricsEngine:
    """Get the global business metrics engine instance."""
    global _business_metrics_engine
    if _business_metrics_engine is None:
        _business_metrics_engine = BusinessMetricsEngine()
        await _business_metrics_engine.initialize()
    return _business_metrics_engine


async def close_business_metrics_engine():
    """Close the global business metrics engine instance."""
    global _business_metrics_engine
    if _business_metrics_engine:
        _business_metrics_engine = None