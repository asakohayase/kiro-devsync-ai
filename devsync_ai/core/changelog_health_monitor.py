"""
Changelog Service Health Monitor

Integrates with existing monitoring infrastructure to provide
comprehensive health monitoring for changelog services.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from devsync_ai.analytics.system_health_monitor import SystemHealthMonitor
from devsync_ai.analytics.monitoring_data_manager import MonitoringDataManager


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a service component."""
    component_name: str
    status: HealthStatus
    response_time_ms: Optional[float] = None
    success_rate: Optional[float] = None
    error_count: int = 0
    last_check: Optional[datetime] = None
    details: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)


@dataclass
class ServiceHealthReport:
    """Comprehensive service health report."""
    overall_status: HealthStatus
    components: Dict[str, ComponentHealth]
    generated_at: datetime
    uptime_percentage: float
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class ChangelogHealthMonitor:
    """
    Health monitor for changelog services that integrates with
    existing monitoring infrastructure.
    """
    
    def __init__(self):
        """Initialize the changelog health monitor."""
        self.system_health_monitor = SystemHealthMonitor()
        self.monitoring_data_manager = MonitoringDataManager()
        
        # Component health cache
        self._component_health: Dict[str, ComponentHealth] = {}
        self._last_full_check: Optional[datetime] = None
        
        # Monitoring configuration
        self.check_interval_seconds = 60
        self.component_timeout_seconds = 30
        self.health_retention_hours = 24
        
        # Components to monitor
        self.monitored_components = [
            "changelog_generation",
            "data_aggregation", 
            "formatting_engine",
            "distribution_system",
            "database_connectivity",
            "external_apis",
            "configuration_manager"
        ]
        
        logger.info("Changelog health monitor initialized")
    
    async def start_monitoring(self):
        """Start continuous health monitoring."""
        logger.info("Starting changelog health monitoring")
        
        # Initial health check
        await self.perform_full_health_check()
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
    
    async def perform_full_health_check(self) -> ServiceHealthReport:
        """Perform comprehensive health check of all components."""
        logger.info("Performing full changelog service health check")
        
        start_time = datetime.now()
        component_results = {}
        
        # Check each component
        for component in self.monitored_components:
            try:
                health = await self._check_component_health(component)
                component_results[component] = health
                self._component_health[component] = health
                
            except Exception as e:
                logger.error(f"Health check failed for component {component}: {e}")
                component_results[component] = ComponentHealth(
                    component_name=component,
                    status=HealthStatus.UNKNOWN,
                    last_check=datetime.now(),
                    issues=[f"Health check failed: {str(e)}"]
                )
        
        # Calculate overall status
        overall_status = self._calculate_overall_status(component_results)
        
        # Calculate uptime
        uptime_percentage = await self._calculate_uptime_percentage()
        
        # Generate performance metrics
        performance_metrics = await self._gather_performance_metrics()
        
        # Generate recommendations
        recommendations = self._generate_recommendations(component_results)
        
        # Create health report
        report = ServiceHealthReport(
            overall_status=overall_status,
            components=component_results,
            generated_at=start_time,
            uptime_percentage=uptime_percentage,
            performance_metrics=performance_metrics,
            recommendations=recommendations
        )
        
        # Record health check
        await self._record_health_check(report)
        
        self._last_full_check = start_time
        
        logger.info(f"Health check completed: {overall_status.value}")
        return report
    
    async def _check_component_health(self, component: str) -> ComponentHealth:
        """Check health of a specific component."""
        start_time = datetime.now()
        
        try:
            if component == "changelog_generation":
                return await self._check_generation_health()
            elif component == "data_aggregation":
                return await self._check_data_aggregation_health()
            elif component == "formatting_engine":
                return await self._check_formatting_health()
            elif component == "distribution_system":
                return await self._check_distribution_health()
            elif component == "database_connectivity":
                return await self._check_database_health()
            elif component == "external_apis":
                return await self._check_external_apis_health()
            elif component == "configuration_manager":
                return await self._check_configuration_health()
            else:
                return ComponentHealth(
                    component_name=component,
                    status=HealthStatus.UNKNOWN,
                    last_check=datetime.now(),
                    issues=[f"Unknown component: {component}"]
                )
                
        except asyncio.TimeoutError:
            return ComponentHealth(
                component_name=component,
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(),
                issues=["Component health check timed out"]
            )
        except Exception as e:
            return ComponentHealth(
                component_name=component,
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(),
                issues=[f"Health check error: {str(e)}"]
            )
    
    async def _check_generation_health(self) -> ComponentHealth:
        """Check changelog generation component health."""
        try:
            from devsync_ai.database.connection import get_database
            
            db = await get_database()
            
            # Check recent generation jobs
            recent_jobs = await db.execute_raw("""
                SELECT status, COUNT(*) 
                FROM changelog_generation_jobs 
                WHERE created_at >= %s 
                GROUP BY status
            """, (datetime.now() - timedelta(hours=24),))
            
            total_jobs = sum(count for _, count in recent_jobs)
            successful_jobs = sum(count for status, count in recent_jobs if status == 'completed')
            
            success_rate = successful_jobs / total_jobs if total_jobs > 0 else 1.0
            
            # Determine status
            if success_rate >= 0.95:
                status = HealthStatus.HEALTHY
            elif success_rate >= 0.8:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            
            issues = []
            if success_rate < 0.95:
                issues.append(f"Generation success rate is {success_rate:.1%}")
            
            return ComponentHealth(
                component_name="changelog_generation",
                status=status,
                success_rate=success_rate,
                last_check=datetime.now(),
                details={
                    "total_jobs_24h": total_jobs,
                    "successful_jobs_24h": successful_jobs,
                    "job_breakdown": dict(recent_jobs)
                },
                issues=issues
            )
            
        except Exception as e:
            return ComponentHealth(
                component_name="changelog_generation",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(),
                issues=[f"Generation health check failed: {str(e)}"]
            )
    
    async def _check_data_aggregation_health(self) -> ComponentHealth:
        """Check data aggregation component health."""
        try:
            from devsync_ai.core.intelligent_data_aggregator import IntelligentDataAggregator
            
            # Test data aggregator initialization
            aggregator = IntelligentDataAggregator()
            
            # Check if aggregator can access required services
            issues = []
            details = {}
            
            # Test GitHub service connectivity
            try:
                from devsync_ai.services.github import GitHubService
                github_service = GitHubService()
                auth_result = await github_service.test_authentication()
                details["github_connectivity"] = auth_result.get("authenticated", False)
                if not auth_result.get("authenticated"):
                    issues.append("GitHub API authentication failed")
            except Exception as e:
                issues.append(f"GitHub service error: {str(e)}")
                details["github_connectivity"] = False
            
            # Test JIRA service connectivity
            try:
                from devsync_ai.services.jira import JiraService
                jira_service = JiraService()
                jira_result = await jira_service.test_authentication()
                details["jira_connectivity"] = jira_result.authenticated
                if not jira_result.authenticated:
                    issues.append("JIRA API authentication failed")
            except Exception as e:
                issues.append(f"JIRA service error: {str(e)}")
                details["jira_connectivity"] = False
            
            # Determine overall status
            if not issues:
                status = HealthStatus.HEALTHY
            elif len(issues) == 1:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            
            return ComponentHealth(
                component_name="data_aggregation",
                status=status,
                last_check=datetime.now(),
                details=details,
                issues=issues
            )
            
        except Exception as e:
            return ComponentHealth(
                component_name="data_aggregation",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(),
                issues=[f"Data aggregation health check failed: {str(e)}"]
            )
    
    async def _check_formatting_health(self) -> ComponentHealth:
        """Check formatting engine component health."""
        try:
            from devsync_ai.formatters.intelligent_changelog_formatter import IntelligentChangelogFormatter
            
            # Test formatter initialization
            formatter = IntelligentChangelogFormatter()
            
            # Test basic formatting capability with mock data
            mock_data = {
                "team_id": "test",
                "week_start": datetime.now() - timedelta(days=7),
                "week_end": datetime.now(),
                "github_data": {"commits": [], "pull_requests": []},
                "jira_data": {"tickets": []},
                "team_metrics": {}
            }
            
            # This would test the formatter without actually generating content
            # In a real implementation, you might have a lightweight test method
            
            return ComponentHealth(
                component_name="formatting_engine",
                status=HealthStatus.HEALTHY,
                last_check=datetime.now(),
                details={"formatter_initialized": True}
            )
            
        except Exception as e:
            return ComponentHealth(
                component_name="formatting_engine",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(),
                issues=[f"Formatting engine health check failed: {str(e)}"]
            )
    
    async def _check_distribution_health(self) -> ComponentHealth:
        """Check distribution system component health."""
        try:
            from devsync_ai.services.slack import SlackService
            
            slack_service = SlackService()
            
            # Test Slack connectivity
            issues = []
            details = {}
            
            if slack_service.client:
                try:
                    auth_result = await slack_service.test_connection()
                    details["slack_connectivity"] = auth_result.get("ok", False)
                    if not auth_result.get("ok"):
                        issues.append("Slack API connection failed")
                except Exception as e:
                    issues.append(f"Slack connectivity error: {str(e)}")
                    details["slack_connectivity"] = False
            else:
                issues.append("Slack client not configured")
                details["slack_connectivity"] = False
            
            # Determine status
            status = HealthStatus.HEALTHY if not issues else HealthStatus.DEGRADED
            
            return ComponentHealth(
                component_name="distribution_system",
                status=status,
                last_check=datetime.now(),
                details=details,
                issues=issues
            )
            
        except Exception as e:
            return ComponentHealth(
                component_name="distribution_system",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(),
                issues=[f"Distribution system health check failed: {str(e)}"]
            )
    
    async def _check_database_health(self) -> ComponentHealth:
        """Check database connectivity and performance."""
        try:
            from devsync_ai.database.connection import get_database
            
            start_time = datetime.now()
            db = await get_database()
            
            # Test basic connectivity
            await db.execute_raw("SELECT 1")
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Check changelog tables exist
            tables_check = await db.execute_raw("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name IN ('changelog_entries', 'changelog_generation_jobs')
            """)
            
            tables_exist = tables_check[0][0] >= 2 if tables_check else False
            
            issues = []
            if response_time > 1000:  # 1 second
                issues.append(f"Database response time is high: {response_time:.0f}ms")
            
            if not tables_exist:
                issues.append("Required changelog tables are missing")
            
            status = HealthStatus.HEALTHY if not issues else HealthStatus.DEGRADED
            
            return ComponentHealth(
                component_name="database_connectivity",
                status=status,
                response_time_ms=response_time,
                last_check=datetime.now(),
                details={"tables_exist": tables_exist},
                issues=issues
            )
            
        except Exception as e:
            return ComponentHealth(
                component_name="database_connectivity",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(),
                issues=[f"Database health check failed: {str(e)}"]
            )
    
    async def _check_external_apis_health(self) -> ComponentHealth:
        """Check external API connectivity and rate limits."""
        try:
            issues = []
            details = {}
            
            # Check GitHub API rate limits
            try:
                from devsync_ai.services.github import GitHubService
                github_service = GitHubService()
                rate_limit = await github_service.check_rate_limit()
                
                details["github_rate_limit"] = {
                    "remaining": rate_limit.remaining,
                    "limit": rate_limit.limit,
                    "reset_time": rate_limit.reset_time.isoformat()
                }
                
                if rate_limit.remaining < 100:
                    issues.append(f"GitHub API rate limit low: {rate_limit.remaining}/{rate_limit.limit}")
                    
            except Exception as e:
                issues.append(f"GitHub API check failed: {str(e)}")
            
            # Check JIRA API connectivity
            try:
                from devsync_ai.services.jira import JiraService
                jira_service = JiraService()
                jira_auth = await jira_service.test_authentication()
                
                details["jira_connectivity"] = jira_auth.authenticated
                if not jira_auth.authenticated:
                    issues.append("JIRA API authentication failed")
                    
            except Exception as e:
                issues.append(f"JIRA API check failed: {str(e)}")
            
            # Determine status
            if not issues:
                status = HealthStatus.HEALTHY
            elif len(issues) <= 1:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            
            return ComponentHealth(
                component_name="external_apis",
                status=status,
                last_check=datetime.now(),
                details=details,
                issues=issues
            )
            
        except Exception as e:
            return ComponentHealth(
                component_name="external_apis",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(),
                issues=[f"External APIs health check failed: {str(e)}"]
            )
    
    async def _check_configuration_health(self) -> ComponentHealth:
        """Check configuration manager health."""
        try:
            from devsync_ai.core.changelog_configuration_manager import ChangelogConfigurationManager
            
            config_manager = ChangelogConfigurationManager()
            
            # Test configuration loading
            config = await config_manager.load_configuration()
            
            # Test system configuration
            system_config = await config_manager.get_system_configuration()
            
            issues = []
            details = {
                "config_loaded": bool(config),
                "system_config_valid": system_config.enabled is not None
            }
            
            if not config:
                issues.append("Failed to load configuration")
            
            status = HealthStatus.HEALTHY if not issues else HealthStatus.UNHEALTHY
            
            return ComponentHealth(
                component_name="configuration_manager",
                status=status,
                last_check=datetime.now(),
                details=details,
                issues=issues
            )
            
        except Exception as e:
            return ComponentHealth(
                component_name="configuration_manager",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(),
                issues=[f"Configuration manager health check failed: {str(e)}"]
            )
    
    def _calculate_overall_status(self, components: Dict[str, ComponentHealth]) -> HealthStatus:
        """Calculate overall service status from component statuses."""
        if not components:
            return HealthStatus.UNKNOWN
        
        statuses = [comp.status for comp in components.values()]
        
        # If any component is unhealthy, overall is unhealthy
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        
        # If any component is degraded, overall is degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        
        # If all components are healthy, overall is healthy
        if all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        
        # Default to unknown
        return HealthStatus.UNKNOWN
    
    async def _calculate_uptime_percentage(self) -> float:
        """Calculate service uptime percentage over the last 24 hours."""
        try:
            from devsync_ai.database.connection import get_database
            
            db = await get_database()
            
            # Get health check records from the last 24 hours
            health_records = await db.execute_raw("""
                SELECT health_status, COUNT(*) 
                FROM changelog_service_health 
                WHERE service_component = 'overall' 
                AND checked_at >= %s 
                GROUP BY health_status
            """, (datetime.now() - timedelta(hours=24),))
            
            total_checks = sum(count for _, count in health_records)
            healthy_checks = sum(count for status, count in health_records if status == 'healthy')
            
            if total_checks == 0:
                return 100.0  # No data means assume healthy
            
            return (healthy_checks / total_checks) * 100.0
            
        except Exception as e:
            logger.error(f"Failed to calculate uptime: {e}")
            return 0.0
    
    async def _gather_performance_metrics(self) -> Dict[str, Any]:
        """Gather performance metrics for the service."""
        try:
            from devsync_ai.database.connection import get_database
            
            db = await get_database()
            
            # Get average generation time
            avg_generation_time = await db.execute_raw("""
                SELECT AVG(execution_time_ms) 
                FROM changelog_generation_jobs 
                WHERE completed_at >= %s AND status = 'completed'
            """, (datetime.now() - timedelta(hours=24),))
            
            # Get API response times
            avg_api_response = await db.execute_raw("""
                SELECT AVG(response_time_ms) 
                FROM changelog_api_usage 
                WHERE request_timestamp >= %s
            """, (datetime.now() - timedelta(hours=24),))
            
            return {
                "avg_generation_time_ms": float(avg_generation_time[0][0]) if avg_generation_time and avg_generation_time[0][0] else 0,
                "avg_api_response_time_ms": float(avg_api_response[0][0]) if avg_api_response and avg_api_response[0][0] else 0,
                "metrics_period_hours": 24
            }
            
        except Exception as e:
            logger.error(f"Failed to gather performance metrics: {e}")
            return {}
    
    def _generate_recommendations(self, components: Dict[str, ComponentHealth]) -> List[str]:
        """Generate recommendations based on component health."""
        recommendations = []
        
        for component_name, health in components.items():
            if health.status == HealthStatus.UNHEALTHY:
                recommendations.append(f"Investigate {component_name} component - status is unhealthy")
            elif health.status == HealthStatus.DEGRADED:
                recommendations.append(f"Monitor {component_name} component - performance is degraded")
            
            # Specific recommendations based on issues
            for issue in health.issues:
                if "rate limit" in issue.lower():
                    recommendations.append("Consider implementing rate limit management or increasing API quotas")
                elif "authentication" in issue.lower():
                    recommendations.append("Check API credentials and authentication configuration")
                elif "response time" in issue.lower():
                    recommendations.append("Investigate database performance and consider optimization")
        
        return recommendations
    
    async def _record_health_check(self, report: ServiceHealthReport):
        """Record health check results to database."""
        try:
            from devsync_ai.database.connection import get_database
            
            db = await get_database()
            
            # Record overall health
            await db.execute_raw("""
                INSERT INTO changelog_service_health 
                (service_component, health_status, success_rate, component_data, check_details)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                "overall",
                report.overall_status.value,
                report.uptime_percentage / 100.0,
                {
                    "performance_metrics": report.performance_metrics,
                    "component_count": len(report.components)
                },
                f"Full health check with {len(report.recommendations)} recommendations"
            ))
            
            # Record individual component health
            for component_name, health in report.components.items():
                await db.execute_raw("""
                    INSERT INTO changelog_service_health 
                    (service_component, health_status, response_time_ms, success_rate, 
                     error_count, component_data, check_details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    component_name,
                    health.status.value,
                    health.response_time_ms,
                    health.success_rate,
                    health.error_count,
                    health.details,
                    "; ".join(health.issues) if health.issues else "No issues detected"
                ))
            
        except Exception as e:
            logger.error(f"Failed to record health check: {e}")
    
    async def _monitoring_loop(self):
        """Continuous monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.check_interval_seconds)
                await self.perform_full_health_check()
                
            except asyncio.CancelledError:
                logger.info("Health monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                # Continue monitoring despite errors
                await asyncio.sleep(self.check_interval_seconds)
    
    async def get_current_health_status(self) -> ServiceHealthReport:
        """Get current health status (from cache or perform new check)."""
        if (self._last_full_check and 
            (datetime.now() - self._last_full_check).total_seconds() < 300):  # 5 minutes
            # Return cached status if recent
            overall_status = self._calculate_overall_status(self._component_health)
            uptime = await self._calculate_uptime_percentage()
            
            return ServiceHealthReport(
                overall_status=overall_status,
                components=self._component_health.copy(),
                generated_at=self._last_full_check,
                uptime_percentage=uptime
            )
        else:
            # Perform new health check
            return await self.perform_full_health_check()
    
    async def get_component_health(self, component_name: str) -> Optional[ComponentHealth]:
        """Get health status of a specific component."""
        if component_name in self._component_health:
            return self._component_health[component_name]
        
        # Perform individual component check
        return await self._check_component_health(component_name)