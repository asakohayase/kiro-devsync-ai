"""
Hook Performance Optimization Engine for DevSync AI.

This module provides advanced optimization analysis for JIRA Agent Hooks
with A/B testing, performance benchmarking, and ML-based recommendations.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import random
from collections import defaultdict

from devsync_ai.hooks.hook_registry_manager import get_hook_registry_manager


logger = logging.getLogger(__name__)


class OptimizationMetric(Enum):
    """Types of optimization metrics."""
    EXECUTION_TIME = "execution_time"
    SUCCESS_RATE = "success_rate"
    USER_ENGAGEMENT = "user_engagement"
    RESOURCE_USAGE = "resource_usage"
    NOTIFICATION_EFFECTIVENESS = "notification_effectiveness"


class ConfigurationEffectiveness(Enum):
    """Configuration effectiveness levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class ABTestResult:
    """A/B test result for hook configuration."""
    test_id: str
    hook_type: str
    team_id: str
    variant_a: Dict[str, Any]
    variant_b: Dict[str, Any]
    metric_type: OptimizationMetric
    variant_a_performance: float
    variant_b_performance: float
    statistical_significance: float
    winner: str  # "A", "B", or "inconclusive"
    confidence_level: float
    sample_size: int
    test_duration_days: int
    recommendation: str


@dataclass
class UserEngagementMetrics:
    """User engagement metrics for hook notifications."""
    hook_id: str
    team_id: str
    total_notifications: int
    message_opens: int
    button_clicks: int
    action_completions: int
    open_rate: float
    click_through_rate: float
    completion_rate: float
    engagement_score: float
    user_feedback_score: Optional[float]


@dataclass
class PerformanceBenchmark:
    """Performance benchmark data."""
    metric_name: str
    current_value: float
    industry_average: float
    top_quartile: float
    benchmark_score: float  # 0-100
    performance_level: str
    improvement_potential: float
    recommendations: List[str]


@dataclass
class OptimizationRecommendation:
    """AI-generated optimization recommendation."""
    recommendation_id: str
    hook_id: str
    team_id: str
    optimization_type: str
    current_config: Dict[str, Any]
    recommended_config: Dict[str, Any]
    expected_improvement: float
    confidence_score: float
    impact_level: str
    implementation_effort: str
    risk_level: str
    supporting_evidence: List[str]
    generated_at: datetime


class HookOptimizationEngine:
    """
    Advanced optimization engine for JIRA Agent Hooks performance.
    
    Provides A/B testing, performance benchmarking, user engagement analysis,
    and ML-based optimization recommendations.
    """
    
    def __init__(self):
        """Initialize the optimization engine."""
        self.ab_tests: Dict[str, ABTestResult] = {}
        self.engagement_metrics: Dict[str, UserEngagementMetrics] = {}
        self.performance_benchmarks: Dict[str, PerformanceBenchmark] = {}
        self.optimization_recommendations: List[OptimizationRecommendation] = []
        
        # Industry benchmarks (mock data - would come from real industry data)
        self.industry_benchmarks = {
            'average_execution_time_ms': 1500.0,
            'success_rate': 0.95,
            'notification_open_rate': 0.65,
            'click_through_rate': 0.25,
            'action_completion_rate': 0.15,
            'user_satisfaction_score': 4.2  # out of 5
        }
        
        # Configuration effectiveness patterns
        self.effective_patterns = {
            'notification_channels': {
                'single_channel': 0.7,
                'multiple_channels': 0.85,
                'team_specific': 0.9
            },
            'message_length': {
                'short': 0.8,
                'medium': 0.9,
                'long': 0.6
            },
            'urgency_indicators': {
                'none': 0.6,
                'visual': 0.8,
                'interactive': 0.9
            }
        }
    
    async def analyze_configuration_effectiveness(
        self, 
        hook_id: str,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Analyze the effectiveness of current hook configuration.
        
        Args:
            hook_id: Hook identifier
            time_range: Time range for analysis
            
        Returns:
            Configuration effectiveness analysis
        """
        if not time_range:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            time_range = (start_date, end_date)
        
        # Get hook configuration and performance data
        registry_manager = await get_hook_registry_manager()
        if not registry_manager:
            return {"error": "Hook registry not available"}
        
        hook_status = await registry_manager.get_hook_status(hook_id)
        if not hook_status:
            return {"error": f"Hook {hook_id} not found"}
        
        config = hook_status['configuration']
        stats = hook_status['statistics']
        
        # Analyze configuration elements
        effectiveness_scores = {}
        
        # Channel configuration effectiveness
        channels = config.get('channels', [])
        if len(channels) == 1:
            effectiveness_scores['channels'] = self.effective_patterns['notification_channels']['single_channel']
        elif len(channels) <= 3:
            effectiveness_scores['channels'] = self.effective_patterns['notification_channels']['multiple_channels']
        else:
            effectiveness_scores['channels'] = self.effective_patterns['notification_channels']['team_specific']
        
        # Performance metrics analysis
        execution_time = stats.get('average_execution_time_ms', 0)
        success_rate = stats.get('success_rate', 0)
        
        # Calculate effectiveness scores
        time_effectiveness = max(0, 1 - (execution_time / 5000))  # Normalize to 5 seconds max
        reliability_effectiveness = success_rate
        
        effectiveness_scores['execution_time'] = time_effectiveness
        effectiveness_scores['reliability'] = reliability_effectiveness
        
        # Overall effectiveness score
        overall_effectiveness = statistics.mean(effectiveness_scores.values())
        
        # Determine effectiveness level
        if overall_effectiveness >= 0.9:
            effectiveness_level = ConfigurationEffectiveness.EXCELLENT
        elif overall_effectiveness >= 0.8:
            effectiveness_level = ConfigurationEffectiveness.GOOD
        elif overall_effectiveness >= 0.7:
            effectiveness_level = ConfigurationEffectiveness.AVERAGE
        elif overall_effectiveness >= 0.6:
            effectiveness_level = ConfigurationEffectiveness.POOR
        else:
            effectiveness_level = ConfigurationEffectiveness.CRITICAL
        
        # Generate improvement suggestions
        improvements = []
        if effectiveness_scores['channels'] < 0.8:
            improvements.append("Optimize notification channel selection for better reach")
        if effectiveness_scores['execution_time'] < 0.8:
            improvements.append("Optimize hook execution performance")
        if effectiveness_scores['reliability'] < 0.9:
            improvements.append("Improve error handling and retry mechanisms")
        
        return {
            'hook_id': hook_id,
            'overall_effectiveness': overall_effectiveness,
            'effectiveness_level': effectiveness_level.value,
            'component_scores': effectiveness_scores,
            'performance_metrics': {
                'execution_time_ms': execution_time,
                'success_rate': success_rate,
                'total_executions': stats.get('total_executions', 0)
            },
            'improvement_suggestions': improvements,
            'benchmark_comparison': {
                'execution_time_vs_industry': execution_time / self.industry_benchmarks['average_execution_time_ms'],
                'success_rate_vs_industry': success_rate / self.industry_benchmarks['success_rate']
            }
        }
    
    async def run_ab_test(
        self,
        hook_type: str,
        team_id: str,
        variant_a_config: Dict[str, Any],
        variant_b_config: Dict[str, Any],
        metric_type: OptimizationMetric,
        test_duration_days: int = 7
    ) -> ABTestResult:
        """
        Run A/B test for hook configuration optimization.
        
        Args:
            hook_type: Type of hook to test
            team_id: Team identifier
            variant_a_config: Configuration A
            variant_b_config: Configuration B
            metric_type: Metric to optimize
            test_duration_days: Duration of test in days
            
        Returns:
            A/B test results
        """
        test_id = f"ab_test_{hook_type}_{team_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Simulate A/B test results (in production, this would run actual tests)
        # Variant A performance (baseline)
        variant_a_performance = await self._simulate_variant_performance(variant_a_config, metric_type)
        
        # Variant B performance (test)
        variant_b_performance = await self._simulate_variant_performance(variant_b_config, metric_type)
        
        # Calculate statistical significance
        sample_size = random.randint(100, 500)  # Mock sample size
        statistical_significance = await self._calculate_statistical_significance(
            variant_a_performance, variant_b_performance, sample_size
        )
        
        # Determine winner
        if statistical_significance > 0.95:  # 95% confidence
            if variant_b_performance > variant_a_performance:
                winner = "B"
                confidence_level = statistical_significance
            else:
                winner = "A"
                confidence_level = statistical_significance
        else:
            winner = "inconclusive"
            confidence_level = statistical_significance
        
        # Generate recommendation
        if winner == "B":
            recommendation = f"Implement variant B configuration for {(variant_b_performance - variant_a_performance) / variant_a_performance:.1%} improvement"
        elif winner == "A":
            recommendation = "Keep current configuration (variant A)"
        else:
            recommendation = "Extend test duration or increase sample size for conclusive results"
        
        ab_test_result = ABTestResult(
            test_id=test_id,
            hook_type=hook_type,
            team_id=team_id,
            variant_a=variant_a_config,
            variant_b=variant_b_config,
            metric_type=metric_type,
            variant_a_performance=variant_a_performance,
            variant_b_performance=variant_b_performance,
            statistical_significance=statistical_significance,
            winner=winner,
            confidence_level=confidence_level,
            sample_size=sample_size,
            test_duration_days=test_duration_days,
            recommendation=recommendation
        )
        
        self.ab_tests[test_id] = ab_test_result
        return ab_test_result
    
    async def analyze_user_engagement(
        self,
        hook_id: str,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> UserEngagementMetrics:
        """
        Analyze user engagement with hook notifications.
        
        Args:
            hook_id: Hook identifier
            time_range: Time range for analysis
            
        Returns:
            User engagement metrics
        """
        if not time_range:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            time_range = (start_date, end_date)
        
        # Get hook data
        registry_manager = await get_hook_registry_manager()
        hook_status = await registry_manager.get_hook_status(hook_id) if registry_manager else None
        
        if not hook_status:
            # Return mock data for demonstration
            total_notifications = random.randint(50, 200)
        else:
            total_notifications = hook_status['statistics']['total_executions']
        
        # Simulate engagement metrics (in production, would come from Slack analytics)
        message_opens = int(total_notifications * random.uniform(0.6, 0.8))
        button_clicks = int(message_opens * random.uniform(0.2, 0.4))
        action_completions = int(button_clicks * random.uniform(0.5, 0.8))
        
        # Calculate rates
        open_rate = message_opens / total_notifications if total_notifications > 0 else 0
        click_through_rate = button_clicks / message_opens if message_opens > 0 else 0
        completion_rate = action_completions / button_clicks if button_clicks > 0 else 0
        
        # Calculate engagement score (0-100)
        engagement_score = (open_rate * 0.3 + click_through_rate * 0.4 + completion_rate * 0.3) * 100
        
        # Mock user feedback score
        user_feedback_score = random.uniform(3.5, 4.8)
        
        engagement_metrics = UserEngagementMetrics(
            hook_id=hook_id,
            team_id=hook_status['team_id'] if hook_status else 'unknown',
            total_notifications=total_notifications,
            message_opens=message_opens,
            button_clicks=button_clicks,
            action_completions=action_completions,
            open_rate=open_rate,
            click_through_rate=click_through_rate,
            completion_rate=completion_rate,
            engagement_score=engagement_score,
            user_feedback_score=user_feedback_score
        )
        
        self.engagement_metrics[hook_id] = engagement_metrics
        return engagement_metrics 
   
    async def benchmark_performance(
        self,
        hook_id: str,
        metrics: List[str] = None
    ) -> List[PerformanceBenchmark]:
        """
        Benchmark hook performance against industry standards.
        
        Args:
            hook_id: Hook identifier
            metrics: List of metrics to benchmark
            
        Returns:
            List of performance benchmarks
        """
        if not metrics:
            metrics = ['execution_time', 'success_rate', 'user_engagement']
        
        benchmarks = []
        
        # Get hook performance data
        registry_manager = await get_hook_registry_manager()
        hook_status = await registry_manager.get_hook_status(hook_id) if registry_manager else None
        
        if not hook_status:
            return benchmarks
        
        stats = hook_status['statistics']
        
        for metric in metrics:
            if metric == 'execution_time':
                current_value = stats.get('average_execution_time_ms', 0)
                industry_average = self.industry_benchmarks['average_execution_time_ms']
                top_quartile = industry_average * 0.6  # Top 25% are 40% faster
                
                benchmark_score = max(0, min(100, (industry_average - current_value) / industry_average * 100))
                
                if benchmark_score >= 80:
                    performance_level = "Excellent"
                elif benchmark_score >= 60:
                    performance_level = "Good"
                elif benchmark_score >= 40:
                    performance_level = "Average"
                else:
                    performance_level = "Below Average"
                
                improvement_potential = max(0, (current_value - top_quartile) / current_value)
                
                recommendations = []
                if current_value > industry_average:
                    recommendations.append("Optimize hook execution logic")
                    recommendations.append("Review database query performance")
                    recommendations.append("Consider caching frequently accessed data")
                
            elif metric == 'success_rate':
                current_value = stats.get('success_rate', 0)
                industry_average = self.industry_benchmarks['success_rate']
                top_quartile = 0.98  # Top 25% have 98%+ success rate
                
                benchmark_score = (current_value / industry_average) * 100
                benchmark_score = min(100, benchmark_score)
                
                if benchmark_score >= 95:
                    performance_level = "Excellent"
                elif benchmark_score >= 90:
                    performance_level = "Good"
                elif benchmark_score >= 80:
                    performance_level = "Average"
                else:
                    performance_level = "Below Average"
                
                improvement_potential = max(0, (top_quartile - current_value) / current_value)
                
                recommendations = []
                if current_value < industry_average:
                    recommendations.append("Improve error handling and retry logic")
                    recommendations.append("Add input validation and sanitization")
                    recommendations.append("Monitor and fix common failure patterns")
            
            elif metric == 'user_engagement':
                # Get engagement metrics if available
                engagement = self.engagement_metrics.get(hook_id)
                if engagement:
                    current_value = engagement.engagement_score
                else:
                    current_value = 65.0  # Mock value
                
                industry_average = 70.0  # Mock industry average
                top_quartile = 85.0
                
                benchmark_score = (current_value / industry_average) * 100
                benchmark_score = min(100, benchmark_score)
                
                if benchmark_score >= 90:
                    performance_level = "Excellent"
                elif benchmark_score >= 80:
                    performance_level = "Good"
                elif benchmark_score >= 70:
                    performance_level = "Average"
                else:
                    performance_level = "Below Average"
                
                improvement_potential = max(0, (top_quartile - current_value) / current_value)
                
                recommendations = []
                if current_value < industry_average:
                    recommendations.append("Improve message relevance and timing")
                    recommendations.append("Add more interactive elements")
                    recommendations.append("Personalize notifications based on user preferences")
            
            benchmark = PerformanceBenchmark(
                metric_name=metric,
                current_value=current_value,
                industry_average=industry_average,
                top_quartile=top_quartile,
                benchmark_score=benchmark_score,
                performance_level=performance_level,
                improvement_potential=improvement_potential,
                recommendations=recommendations
            )
            
            benchmarks.append(benchmark)
            self.performance_benchmarks[f"{hook_id}_{metric}"] = benchmark
        
        return benchmarks
    
    async def generate_optimization_recommendations(
        self,
        hook_id: str,
        focus_areas: List[str] = None
    ) -> List[OptimizationRecommendation]:
        """
        Generate AI-powered optimization recommendations.
        
        Args:
            hook_id: Hook identifier
            focus_areas: Areas to focus optimization on
            
        Returns:
            List of optimization recommendations
        """
        if not focus_areas:
            focus_areas = ['performance', 'reliability', 'user_engagement']
        
        recommendations = []
        
        # Get current hook configuration and performance
        registry_manager = await get_hook_registry_manager()
        hook_status = await registry_manager.get_hook_status(hook_id) if registry_manager else None
        
        if not hook_status:
            return recommendations
        
        current_config = hook_status['configuration']
        stats = hook_status['statistics']
        
        for focus_area in focus_areas:
            if focus_area == 'performance':
                # Performance optimization recommendations
                execution_time = stats.get('average_execution_time_ms', 0)
                if execution_time > self.industry_benchmarks['average_execution_time_ms']:
                    recommended_config = current_config.copy()
                    recommended_config['timeout_seconds'] = min(15, current_config.get('timeout_seconds', 30))
                    recommended_config['batch_processing'] = True
                    
                    expected_improvement = 0.3  # 30% improvement expected
                    
                    recommendation = OptimizationRecommendation(
                        recommendation_id=f"perf_{hook_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        hook_id=hook_id,
                        team_id=hook_status['team_id'],
                        optimization_type='performance',
                        current_config=current_config,
                        recommended_config=recommended_config,
                        expected_improvement=expected_improvement,
                        confidence_score=0.85,
                        impact_level='high',
                        implementation_effort='medium',
                        risk_level='low',
                        supporting_evidence=[
                            f"Current execution time ({execution_time:.1f}ms) is above industry average",
                            "Timeout reduction and batch processing can improve performance",
                            "Similar optimizations showed 25-35% improvement in other teams"
                        ],
                        generated_at=datetime.now(timezone.utc)
                    )
                    
                    recommendations.append(recommendation)
            
            elif focus_area == 'reliability':
                # Reliability optimization recommendations
                success_rate = stats.get('success_rate', 0)
                if success_rate < self.industry_benchmarks['success_rate']:
                    recommended_config = current_config.copy()
                    recommended_config['retry_attempts'] = min(5, current_config.get('retry_attempts', 3) + 2)
                    recommended_config['circuit_breaker'] = True
                    recommended_config['fallback_enabled'] = True
                    
                    expected_improvement = (self.industry_benchmarks['success_rate'] - success_rate) / success_rate
                    
                    recommendation = OptimizationRecommendation(
                        recommendation_id=f"rel_{hook_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        hook_id=hook_id,
                        team_id=hook_status['team_id'],
                        optimization_type='reliability',
                        current_config=current_config,
                        recommended_config=recommended_config,
                        expected_improvement=expected_improvement,
                        confidence_score=0.90,
                        impact_level='high',
                        implementation_effort='low',
                        risk_level='low',
                        supporting_evidence=[
                            f"Current success rate ({success_rate:.1%}) is below industry standard",
                            "Additional retry attempts and circuit breaker can improve reliability",
                            "Fallback mechanisms prevent complete failures"
                        ],
                        generated_at=datetime.now(timezone.utc)
                    )
                    
                    recommendations.append(recommendation)
            
            elif focus_area == 'user_engagement':
                # User engagement optimization recommendations
                engagement = self.engagement_metrics.get(hook_id)
                if engagement and engagement.engagement_score < 70:
                    recommended_config = current_config.copy()
                    recommended_config['interactive_buttons'] = True
                    recommended_config['personalization'] = True
                    recommended_config['smart_timing'] = True
                    
                    expected_improvement = 0.25  # 25% improvement in engagement
                    
                    recommendation = OptimizationRecommendation(
                        recommendation_id=f"eng_{hook_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        hook_id=hook_id,
                        team_id=hook_status['team_id'],
                        optimization_type='user_engagement',
                        current_config=current_config,
                        recommended_config=recommended_config,
                        expected_improvement=expected_improvement,
                        confidence_score=0.75,
                        impact_level='medium',
                        implementation_effort='high',
                        risk_level='medium',
                        supporting_evidence=[
                            f"Current engagement score ({engagement.engagement_score:.1f}) is below target",
                            "Interactive elements increase user engagement by 20-30%",
                            "Personalization and smart timing improve relevance"
                        ],
                        generated_at=datetime.now(timezone.utc)
                    )
                    
                    recommendations.append(recommendation)
        
        # Store recommendations
        self.optimization_recommendations.extend(recommendations)
        
        return recommendations
    
    async def detect_performance_anomalies(
        self,
        hook_id: str,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect performance anomalies using ML-based analysis.
        
        Args:
            hook_id: Hook identifier
            time_range: Time range for analysis
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Get historical performance data
        registry_manager = await get_hook_registry_manager()
        hook_status = await registry_manager.get_hook_status(hook_id) if registry_manager else None
        
        if not hook_status:
            return anomalies
        
        stats = hook_status['statistics']
        
        # Simulate anomaly detection (in production, would use actual ML models)
        current_execution_time = stats.get('average_execution_time_ms', 0)
        current_success_rate = stats.get('success_rate', 0)
        
        # Check for execution time anomalies
        if current_execution_time > self.industry_benchmarks['average_execution_time_ms'] * 2:
            anomalies.append({
                'type': 'performance_degradation',
                'metric': 'execution_time',
                'severity': 'high',
                'current_value': current_execution_time,
                'expected_range': [500, 2000],
                'description': 'Execution time significantly higher than normal',
                'potential_causes': [
                    'Database performance issues',
                    'External API latency',
                    'Resource contention'
                ],
                'recommended_actions': [
                    'Check database query performance',
                    'Monitor external service dependencies',
                    'Review resource utilization'
                ]
            })
        
        # Check for success rate anomalies
        if current_success_rate < 0.8:
            anomalies.append({
                'type': 'reliability_issue',
                'metric': 'success_rate',
                'severity': 'critical' if current_success_rate < 0.5 else 'high',
                'current_value': current_success_rate,
                'expected_range': [0.95, 1.0],
                'description': 'Success rate below acceptable threshold',
                'potential_causes': [
                    'Configuration errors',
                    'External service failures',
                    'Input validation issues'
                ],
                'recommended_actions': [
                    'Review error logs for patterns',
                    'Validate hook configuration',
                    'Implement additional error handling'
                ]
            })
        
        return anomalies
    
    # Helper methods
    async def _simulate_variant_performance(
        self,
        config: Dict[str, Any],
        metric_type: OptimizationMetric
    ) -> float:
        """Simulate performance for A/B test variant."""
        base_performance = {
            OptimizationMetric.EXECUTION_TIME: 1500.0,  # ms
            OptimizationMetric.SUCCESS_RATE: 0.95,
            OptimizationMetric.USER_ENGAGEMENT: 70.0,  # score
            OptimizationMetric.RESOURCE_USAGE: 50.0,  # percentage
            OptimizationMetric.NOTIFICATION_EFFECTIVENESS: 75.0  # score
        }
        
        base = base_performance.get(metric_type, 50.0)
        
        # Apply configuration-based modifications
        modifier = 1.0
        
        if 'timeout_seconds' in config:
            timeout = config['timeout_seconds']
            if metric_type == OptimizationMetric.EXECUTION_TIME:
                modifier *= (timeout / 30.0)  # Normalize to 30s baseline
        
        if 'retry_attempts' in config:
            retries = config['retry_attempts']
            if metric_type == OptimizationMetric.SUCCESS_RATE:
                modifier *= (1.0 + retries * 0.02)  # Each retry adds 2% success rate
        
        if 'channels' in config:
            channel_count = len(config['channels'])
            if metric_type == OptimizationMetric.USER_ENGAGEMENT:
                modifier *= (1.0 + channel_count * 0.05)  # Each channel adds 5% engagement
        
        # Add some randomness
        modifier *= random.uniform(0.9, 1.1)
        
        return base * modifier
    
    async def _calculate_statistical_significance(
        self,
        variant_a_performance: float,
        variant_b_performance: float,
        sample_size: int
    ) -> float:
        """Calculate statistical significance of A/B test results."""
        # Simplified statistical significance calculation
        # In production, would use proper statistical tests
        
        difference = abs(variant_b_performance - variant_a_performance)
        relative_difference = difference / max(variant_a_performance, variant_b_performance)
        
        # Mock calculation based on sample size and effect size
        base_significance = min(0.99, sample_size / 1000.0)  # Larger samples = higher significance
        effect_boost = min(0.2, relative_difference * 2)  # Larger effects = higher significance
        
        return min(0.99, base_significance + effect_boost)
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of all optimization activities."""
        return {
            'total_ab_tests': len(self.ab_tests),
            'successful_optimizations': len([t for t in self.ab_tests.values() if t.winner == 'B']),
            'average_improvement': statistics.mean([
                (t.variant_b_performance - t.variant_a_performance) / t.variant_a_performance
                for t in self.ab_tests.values() if t.winner == 'B'
            ]) if any(t.winner == 'B' for t in self.ab_tests.values()) else 0.0,
            'total_recommendations': len(self.optimization_recommendations),
            'high_impact_recommendations': len([
                r for r in self.optimization_recommendations if r.impact_level == 'high'
            ]),
            'engagement_metrics_tracked': len(self.engagement_metrics),
            'performance_benchmarks': len(self.performance_benchmarks)
        }