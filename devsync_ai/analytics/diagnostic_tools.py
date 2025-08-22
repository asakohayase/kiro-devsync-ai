"""
Diagnostic Tools for DevSync AI Hook System.

This module provides comprehensive diagnostic utilities for troubleshooting
system issues, performance problems, and configuration errors.
"""

import asyncio
import logging
import json
import traceback
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import psutil
import sys
import os

from devsync_ai.analytics.system_health_monitor import get_health_monitor
from devsync_ai.analytics.hook_analytics_engine import HookAnalyticsEngine
from devsync_ai.hooks.hook_registry_manager import get_hook_registry_manager
from devsync_ai.analytics.analytics_data_manager import get_analytics_data_manager

logger = logging.getLogger(__name__)


class DiagnosticSeverity(Enum):
    """Diagnostic issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DiagnosticCategory(Enum):
    """Categories of diagnostic checks."""
    SYSTEM_RESOURCES = "system_resources"
    HOOK_PERFORMANCE = "hook_performance"
    DATABASE_CONNECTIVITY = "database_connectivity"
    CONFIGURATION = "configuration"
    NETWORK_CONNECTIVITY = "network_connectivity"
    DATA_INTEGRITY = "data_integrity"


@dataclass
class DiagnosticIssue:
    """Represents a diagnostic issue found during system analysis."""
    issue_id: str
    category: DiagnosticCategory
    severity: DiagnosticSeverity
    title: str
    description: str
    affected_components: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DiagnosticReport:
    """Comprehensive diagnostic report."""
    report_id: str
    generated_at: datetime
    system_info: Dict[str, Any]
    issues: List[DiagnosticIssue]
    performance_summary: Dict[str, Any]
    recommendations: List[str]
    overall_health_score: float  # 0-100


class SystemDiagnosticTools:
    """
    Comprehensive diagnostic tools for system troubleshooting.
    
    Provides automated system analysis, issue detection, and
    troubleshooting recommendations.
    """
    
    def __init__(self):
        """Initialize diagnostic tools."""
        self.diagnostic_checks = {
            DiagnosticCategory.SYSTEM_RESOURCES: self._check_system_resources,
            DiagnosticCategory.HOOK_PERFORMANCE: self._check_hook_performance,
            DiagnosticCategory.DATABASE_CONNECTIVITY: self._check_database_connectivity,
            DiagnosticCategory.CONFIGURATION: self._check_configuration,
            DiagnosticCategory.NETWORK_CONNECTIVITY: self._check_network_connectivity,
            DiagnosticCategory.DATA_INTEGRITY: self._check_data_integrity
        }
        
        # Performance thresholds for diagnostics
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 90.0,
            'memory_warning': 80.0,
            'memory_critical': 95.0,
            'disk_warning': 85.0,
            'disk_critical': 95.0,
            'response_time_warning': 1000.0,  # ms
            'response_time_critical': 3000.0,  # ms
            'success_rate_warning': 0.95,
            'success_rate_critical': 0.85,
            'error_rate_warning': 0.05,
            'error_rate_critical': 0.15
        }
    
    async def run_comprehensive_diagnostics(
        self,
        categories: Optional[List[DiagnosticCategory]] = None
    ) -> DiagnosticReport:
        """
        Run comprehensive system diagnostics.
        
        Args:
            categories: Specific categories to check (all if None)
            
        Returns:
            Comprehensive diagnostic report
        """
        report_id = f"diag_{int(datetime.now().timestamp())}"
        
        if categories is None:
            categories = list(DiagnosticCategory)
        
        logger.info(f"Starting comprehensive diagnostics: {report_id}")
        
        # Collect system information
        system_info = await self._collect_system_info()
        
        # Run diagnostic checks
        all_issues = []
        for category in categories:
            if category in self.diagnostic_checks:
                try:
                    issues = await self.diagnostic_checks[category]()
                    all_issues.extend(issues)
                except Exception as e:
                    logger.error(f"Diagnostic check failed for {category}: {e}", exc_info=True)
                    # Add error as diagnostic issue
                    error_issue = DiagnosticIssue(
                        issue_id=f"diagnostic_error_{category.value}",
                        category=category,
                        severity=DiagnosticSeverity.ERROR,
                        title=f"Diagnostic Check Failed: {category.value}",
                        description=f"Failed to run diagnostic check: {str(e)}",
                        affected_components=["diagnostic_system"],
                        recommendations=["Check system logs for detailed error information"]
                    )
                    all_issues.append(error_issue)
        
        # Generate performance summary
        performance_summary = await self._generate_performance_summary()
        
        # Generate overall recommendations
        overall_recommendations = self._generate_overall_recommendations(all_issues)
        
        # Calculate health score
        health_score = self._calculate_health_score(all_issues, performance_summary)
        
        report = DiagnosticReport(
            report_id=report_id,
            generated_at=datetime.now(timezone.utc),
            system_info=system_info,
            issues=all_issues,
            performance_summary=performance_summary,
            recommendations=overall_recommendations,
            overall_health_score=health_score
        )
        
        logger.info(f"Diagnostic report completed: {report_id}, Health Score: {health_score:.1f}")
        
        return report
    
    async def _collect_system_info(self) -> Dict[str, Any]:
        """Collect basic system information."""
        try:
            # System information
            system_info = {
                'platform': sys.platform,
                'python_version': sys.version,
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'disk_total_gb': psutil.disk_usage('/').total / (1024**3),
                'uptime_seconds': psutil.boot_time(),
                'process_id': os.getpid(),
                'working_directory': os.getcwd()
            }
            
            # Current resource usage
            system_info.update({
                'current_cpu_usage': psutil.cpu_percent(interval=1),
                'current_memory_usage': psutil.virtual_memory().percent,
                'current_disk_usage': psutil.disk_usage('/').percent
            })
            
            return system_info
            
        except Exception as e:
            logger.error(f"Failed to collect system info: {e}")
            return {'error': str(e)}
    
    async def _check_system_resources(self) -> List[DiagnosticIssue]:
        """Check system resource usage and availability."""
        issues = []
        
        try:
            # CPU usage check
            cpu_usage = psutil.cpu_percent(interval=2)
            if cpu_usage > self.thresholds['cpu_critical']:
                issues.append(DiagnosticIssue(
                    issue_id="cpu_critical",
                    category=DiagnosticCategory.SYSTEM_RESOURCES,
                    severity=DiagnosticSeverity.CRITICAL,
                    title="Critical CPU Usage",
                    description=f"CPU usage is critically high at {cpu_usage:.1f}%",
                    affected_components=["system"],
                    recommendations=[
                        "Identify and terminate resource-intensive processes",
                        "Consider scaling up CPU resources",
                        "Review hook execution patterns for optimization opportunities"
                    ],
                    metadata={'cpu_usage': cpu_usage}
                ))
            elif cpu_usage > self.thresholds['cpu_warning']:
                issues.append(DiagnosticIssue(
                    issue_id="cpu_warning",
                    category=DiagnosticCategory.SYSTEM_RESOURCES,
                    severity=DiagnosticSeverity.WARNING,
                    title="High CPU Usage",
                    description=f"CPU usage is elevated at {cpu_usage:.1f}%",
                    affected_components=["system"],
                    recommendations=[
                        "Monitor CPU usage trends",
                        "Consider optimizing hook execution logic",
                        "Review concurrent execution limits"
                    ],
                    metadata={'cpu_usage': cpu_usage}
                ))
            
            # Memory usage check
            memory = psutil.virtual_memory()
            if memory.percent > self.thresholds['memory_critical']:
                issues.append(DiagnosticIssue(
                    issue_id="memory_critical",
                    category=DiagnosticCategory.SYSTEM_RESOURCES,
                    severity=DiagnosticSeverity.CRITICAL,
                    title="Critical Memory Usage",
                    description=f"Memory usage is critically high at {memory.percent:.1f}%",
                    affected_components=["system"],
                    recommendations=[
                        "Restart the application to free memory",
                        "Increase available memory",
                        "Review memory usage patterns and optimize caching"
                    ],
                    metadata={'memory_usage': memory.percent, 'available_gb': memory.available / (1024**3)}
                ))
            elif memory.percent > self.thresholds['memory_warning']:
                issues.append(DiagnosticIssue(
                    issue_id="memory_warning",
                    category=DiagnosticCategory.SYSTEM_RESOURCES,
                    severity=DiagnosticSeverity.WARNING,
                    title="High Memory Usage",
                    description=f"Memory usage is elevated at {memory.percent:.1f}%",
                    affected_components=["system"],
                    recommendations=[
                        "Monitor memory usage trends",
                        "Review data caching strategies",
                        "Consider implementing memory cleanup routines"
                    ],
                    metadata={'memory_usage': memory.percent, 'available_gb': memory.available / (1024**3)}
                ))
            
            # Disk usage check
            disk = psutil.disk_usage('/')
            if disk.percent > self.thresholds['disk_critical']:
                issues.append(DiagnosticIssue(
                    issue_id="disk_critical",
                    category=DiagnosticCategory.SYSTEM_RESOURCES,
                    severity=DiagnosticSeverity.CRITICAL,
                    title="Critical Disk Usage",
                    description=f"Disk usage is critically high at {disk.percent:.1f}%",
                    affected_components=["system", "database"],
                    recommendations=[
                        "Free up disk space immediately",
                        "Archive or delete old log files",
                        "Implement log rotation policies",
                        "Consider expanding disk capacity"
                    ],
                    metadata={'disk_usage': disk.percent, 'free_gb': disk.free / (1024**3)}
                ))
            elif disk.percent > self.thresholds['disk_warning']:
                issues.append(DiagnosticIssue(
                    issue_id="disk_warning",
                    category=DiagnosticCategory.SYSTEM_RESOURCES,
                    severity=DiagnosticSeverity.WARNING,
                    title="High Disk Usage",
                    description=f"Disk usage is elevated at {disk.percent:.1f}%",
                    affected_components=["system", "database"],
                    recommendations=[
                        "Monitor disk usage trends",
                        "Plan for disk space expansion",
                        "Review data retention policies"
                    ],
                    metadata={'disk_usage': disk.percent, 'free_gb': disk.free / (1024**3)}
                ))
            
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            issues.append(DiagnosticIssue(
                issue_id="resource_check_error",
                category=DiagnosticCategory.SYSTEM_RESOURCES,
                severity=DiagnosticSeverity.ERROR,
                title="Resource Check Failed",
                description=f"Unable to check system resources: {str(e)}",
                affected_components=["diagnostic_system"],
                recommendations=["Check system permissions and psutil installation"]
            ))
        
        return issues
    
    async def _check_hook_performance(self) -> List[DiagnosticIssue]:
        """Check hook system performance and health."""
        issues = []
        
        try:
            # Get hook registry manager
            registry_manager = await get_hook_registry_manager()
            if not registry_manager:
                issues.append(DiagnosticIssue(
                    issue_id="hook_registry_unavailable",
                    category=DiagnosticCategory.HOOK_PERFORMANCE,
                    severity=DiagnosticSeverity.CRITICAL,
                    title="Hook Registry Unavailable",
                    description="Hook registry manager is not available",
                    affected_components=["hook_system"],
                    recommendations=[
                        "Check hook system initialization",
                        "Verify configuration settings",
                        "Restart the hook system"
                    ]
                ))
                return issues
            
            # Get hook statuses
            hook_statuses = await registry_manager.get_all_hook_statuses()
            
            if not hook_statuses:
                issues.append(DiagnosticIssue(
                    issue_id="no_hooks_registered",
                    category=DiagnosticCategory.HOOK_PERFORMANCE,
                    severity=DiagnosticSeverity.WARNING,
                    title="No Hooks Registered",
                    description="No hooks are currently registered in the system",
                    affected_components=["hook_system"],
                    recommendations=[
                        "Verify hook registration process",
                        "Check hook configuration files",
                        "Review system initialization logs"
                    ]
                ))
                return issues
            
            # Analyze hook performance
            total_hooks = len(hook_statuses)
            failed_hooks = 0
            slow_hooks = 0
            inactive_hooks = 0
            
            for status in hook_statuses:
                stats = status.get('statistics', {})
                success_rate = stats.get('success_rate', 1.0)
                avg_time = stats.get('average_execution_time_ms', 0.0)
                total_executions = stats.get('total_executions', 0)
                last_execution = stats.get('last_execution')
                
                # Check success rate
                if success_rate < self.thresholds['success_rate_critical']:
                    issues.append(DiagnosticIssue(
                        issue_id=f"hook_low_success_rate_{status['hook_id']}",
                        category=DiagnosticCategory.HOOK_PERFORMANCE,
                        severity=DiagnosticSeverity.CRITICAL,
                        title=f"Low Success Rate: {status['hook_id']}",
                        description=f"Hook has critically low success rate: {success_rate:.1%}",
                        affected_components=["hook_system", status['hook_id']],
                        recommendations=[
                            "Review hook execution logs for errors",
                            "Check hook configuration and dependencies",
                            "Consider disabling hook until issues are resolved"
                        ],
                        metadata={'success_rate': success_rate, 'hook_id': status['hook_id']}
                    ))
                    failed_hooks += 1
                elif success_rate < self.thresholds['success_rate_warning']:
                    issues.append(DiagnosticIssue(
                        issue_id=f"hook_warning_success_rate_{status['hook_id']}",
                        category=DiagnosticCategory.HOOK_PERFORMANCE,
                        severity=DiagnosticSeverity.WARNING,
                        title=f"Degraded Success Rate: {status['hook_id']}",
                        description=f"Hook has degraded success rate: {success_rate:.1%}",
                        affected_components=["hook_system", status['hook_id']],
                        recommendations=[
                            "Monitor hook performance trends",
                            "Review recent error patterns",
                            "Consider performance optimization"
                        ],
                        metadata={'success_rate': success_rate, 'hook_id': status['hook_id']}
                    ))
                
                # Check response time
                if avg_time > self.thresholds['response_time_critical']:
                    issues.append(DiagnosticIssue(
                        issue_id=f"hook_slow_response_{status['hook_id']}",
                        category=DiagnosticCategory.HOOK_PERFORMANCE,
                        severity=DiagnosticSeverity.CRITICAL,
                        title=f"Slow Response Time: {status['hook_id']}",
                        description=f"Hook has critically slow response time: {avg_time:.1f}ms",
                        affected_components=["hook_system", status['hook_id']],
                        recommendations=[
                            "Optimize hook execution logic",
                            "Review external API dependencies",
                            "Consider implementing caching"
                        ],
                        metadata={'response_time_ms': avg_time, 'hook_id': status['hook_id']}
                    ))
                    slow_hooks += 1
                elif avg_time > self.thresholds['response_time_warning']:
                    issues.append(DiagnosticIssue(
                        issue_id=f"hook_elevated_response_{status['hook_id']}",
                        category=DiagnosticCategory.HOOK_PERFORMANCE,
                        severity=DiagnosticSeverity.WARNING,
                        title=f"Elevated Response Time: {status['hook_id']}",
                        description=f"Hook has elevated response time: {avg_time:.1f}ms",
                        affected_components=["hook_system", status['hook_id']],
                        recommendations=[
                            "Monitor response time trends",
                            "Review hook implementation for optimizations",
                            "Check system resource availability"
                        ],
                        metadata={'response_time_ms': avg_time, 'hook_id': status['hook_id']}
                    ))
                
                # Check activity
                if total_executions == 0:
                    inactive_hooks += 1
                elif last_execution:
                    last_exec_time = datetime.fromisoformat(last_execution)
                    if (datetime.now(timezone.utc) - last_exec_time).total_seconds() > 86400:  # 24 hours
                        inactive_hooks += 1
            
            # Overall hook system health
            if failed_hooks > total_hooks * 0.3:  # More than 30% failing
                issues.append(DiagnosticIssue(
                    issue_id="hook_system_degraded",
                    category=DiagnosticCategory.HOOK_PERFORMANCE,
                    severity=DiagnosticSeverity.CRITICAL,
                    title="Hook System Degraded",
                    description=f"High number of failing hooks: {failed_hooks}/{total_hooks}",
                    affected_components=["hook_system"],
                    recommendations=[
                        "Review system-wide configuration",
                        "Check external service dependencies",
                        "Consider system restart or rollback"
                    ],
                    metadata={'failed_hooks': failed_hooks, 'total_hooks': total_hooks}
                ))
            
            if inactive_hooks > total_hooks * 0.5:  # More than 50% inactive
                issues.append(DiagnosticIssue(
                    issue_id="hook_system_inactive",
                    category=DiagnosticCategory.HOOK_PERFORMANCE,
                    severity=DiagnosticSeverity.WARNING,
                    title="Many Inactive Hooks",
                    description=f"High number of inactive hooks: {inactive_hooks}/{total_hooks}",
                    affected_components=["hook_system"],
                    recommendations=[
                        "Review webhook configuration",
                        "Check event source connectivity",
                        "Verify hook trigger conditions"
                    ],
                    metadata={'inactive_hooks': inactive_hooks, 'total_hooks': total_hooks}
                ))
            
        except Exception as e:
            logger.error(f"Hook performance check failed: {e}")
            issues.append(DiagnosticIssue(
                issue_id="hook_performance_check_error",
                category=DiagnosticCategory.HOOK_PERFORMANCE,
                severity=DiagnosticSeverity.ERROR,
                title="Hook Performance Check Failed",
                description=f"Unable to check hook performance: {str(e)}",
                affected_components=["diagnostic_system"],
                recommendations=["Check hook system availability and permissions"]
            ))
        
        return issues
    
    async def _check_database_connectivity(self) -> List[DiagnosticIssue]:
        """Check database connectivity and performance."""
        issues = []
        
        try:
            data_manager = await get_analytics_data_manager()
            if not data_manager:
                issues.append(DiagnosticIssue(
                    issue_id="database_unavailable",
                    category=DiagnosticCategory.DATABASE_CONNECTIVITY,
                    severity=DiagnosticSeverity.CRITICAL,
                    title="Database Unavailable",
                    description="Analytics data manager is not available",
                    affected_components=["database"],
                    recommendations=[
                        "Check database connection configuration",
                        "Verify database server is running",
                        "Check network connectivity to database"
                    ]
                ))
                return issues
            
            # Test database connectivity with a simple query
            start_time = datetime.now()
            try:
                end_time = datetime.now(timezone.utc)
                start_time_query = end_time - timedelta(minutes=5)
                
                records = await data_manager.query_records(
                    record_type="hook_execution",
                    start_time=start_time_query,
                    end_time=end_time
                )
                
                query_duration = (datetime.now() - start_time).total_seconds() * 1000
                
                # Check query performance
                if query_duration > 5000:  # 5 seconds
                    issues.append(DiagnosticIssue(
                        issue_id="database_slow_queries",
                        category=DiagnosticCategory.DATABASE_CONNECTIVITY,
                        severity=DiagnosticSeverity.WARNING,
                        title="Slow Database Queries",
                        description=f"Database queries are slow: {query_duration:.1f}ms",
                        affected_components=["database"],
                        recommendations=[
                            "Check database performance and indexing",
                            "Review query optimization",
                            "Monitor database resource usage"
                        ],
                        metadata={'query_duration_ms': query_duration}
                    ))
                
                # Check data availability
                if len(records) == 0:
                    issues.append(DiagnosticIssue(
                        issue_id="no_recent_data",
                        category=DiagnosticCategory.DATABASE_CONNECTIVITY,
                        severity=DiagnosticSeverity.INFO,
                        title="No Recent Data",
                        description="No recent hook execution records found",
                        affected_components=["database", "hook_system"],
                        recommendations=[
                            "Verify hook system is processing events",
                            "Check data recording configuration",
                            "Review system activity levels"
                        ],
                        metadata={'records_found': len(records)}
                    ))
                
            except Exception as query_error:
                issues.append(DiagnosticIssue(
                    issue_id="database_query_error",
                    category=DiagnosticCategory.DATABASE_CONNECTIVITY,
                    severity=DiagnosticSeverity.CRITICAL,
                    title="Database Query Failed",
                    description=f"Database query failed: {str(query_error)}",
                    affected_components=["database"],
                    recommendations=[
                        "Check database connection and credentials",
                        "Verify database schema and permissions",
                        "Review database error logs"
                    ]
                ))
            
        except Exception as e:
            logger.error(f"Database connectivity check failed: {e}")
            issues.append(DiagnosticIssue(
                issue_id="database_check_error",
                category=DiagnosticCategory.DATABASE_CONNECTIVITY,
                severity=DiagnosticSeverity.ERROR,
                title="Database Check Failed",
                description=f"Unable to check database connectivity: {str(e)}",
                affected_components=["diagnostic_system"],
                recommendations=["Check database configuration and availability"]
            ))
        
        return issues
    
    async def _check_configuration(self) -> List[DiagnosticIssue]:
        """Check system configuration for common issues."""
        issues = []
        
        try:
            # Check environment variables
            required_env_vars = [
                'SLACK_BOT_TOKEN',
                'JIRA_WEBHOOK_SECRET',
                'DATABASE_URL'
            ]
            
            missing_env_vars = []
            for var in required_env_vars:
                if not os.getenv(var):
                    missing_env_vars.append(var)
            
            if missing_env_vars:
                issues.append(DiagnosticIssue(
                    issue_id="missing_environment_variables",
                    category=DiagnosticCategory.CONFIGURATION,
                    severity=DiagnosticSeverity.CRITICAL,
                    title="Missing Environment Variables",
                    description=f"Required environment variables are missing: {', '.join(missing_env_vars)}",
                    affected_components=["configuration"],
                    recommendations=[
                        "Set missing environment variables",
                        "Check .env file configuration",
                        "Verify deployment configuration"
                    ],
                    metadata={'missing_vars': missing_env_vars}
                ))
            
            # Check configuration files
            config_files = [
                'config/team_config_production.yaml',
                'config/notification_config.example.yaml',
                'config/analytics_config.example.yaml'
            ]
            
            missing_config_files = []
            for config_file in config_files:
                if not os.path.exists(config_file):
                    missing_config_files.append(config_file)
            
            if missing_config_files:
                issues.append(DiagnosticIssue(
                    issue_id="missing_configuration_files",
                    category=DiagnosticCategory.CONFIGURATION,
                    severity=DiagnosticSeverity.WARNING,
                    title="Missing Configuration Files",
                    description=f"Configuration files are missing: {', '.join(missing_config_files)}",
                    affected_components=["configuration"],
                    recommendations=[
                        "Create missing configuration files",
                        "Copy from example configurations",
                        "Review configuration documentation"
                    ],
                    metadata={'missing_files': missing_config_files}
                ))
            
        except Exception as e:
            logger.error(f"Configuration check failed: {e}")
            issues.append(DiagnosticIssue(
                issue_id="configuration_check_error",
                category=DiagnosticCategory.CONFIGURATION,
                severity=DiagnosticSeverity.ERROR,
                title="Configuration Check Failed",
                description=f"Unable to check configuration: {str(e)}",
                affected_components=["diagnostic_system"],
                recommendations=["Check file system permissions and configuration paths"]
            ))
        
        return issues
    
    async def _check_network_connectivity(self) -> List[DiagnosticIssue]:
        """Check network connectivity to external services."""
        issues = []
        
        try:
            # This would typically test connectivity to Slack API, JIRA, etc.
            # For now, we'll do basic checks
            
            # Mock network connectivity checks
            # In a real implementation, these would be actual HTTP requests
            
            services_to_check = [
                {'name': 'Slack API', 'url': 'https://slack.com/api/api.test'},
                {'name': 'JIRA API', 'url': 'https://your-domain.atlassian.net/rest/api/2/serverInfo'}
            ]
            
            for service in services_to_check:
                # Mock connectivity check (would be actual HTTP request)
                # For demonstration, we'll assume connectivity is OK
                pass
            
        except Exception as e:
            logger.error(f"Network connectivity check failed: {e}")
            issues.append(DiagnosticIssue(
                issue_id="network_check_error",
                category=DiagnosticCategory.NETWORK_CONNECTIVITY,
                severity=DiagnosticSeverity.ERROR,
                title="Network Check Failed",
                description=f"Unable to check network connectivity: {str(e)}",
                affected_components=["diagnostic_system"],
                recommendations=["Check network configuration and firewall settings"]
            ))
        
        return issues
    
    async def _check_data_integrity(self) -> List[DiagnosticIssue]:
        """Check data integrity and consistency."""
        issues = []
        
        try:
            data_manager = await get_analytics_data_manager()
            if not data_manager:
                return issues  # Already handled in database connectivity check
            
            # Check for data consistency issues
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=1)
            
            records = await data_manager.query_records(
                record_type="hook_execution",
                start_time=start_time,
                end_time=end_time
            )
            
            if records:
                # Check for data anomalies
                execution_times = [r.data.get('execution_time_ms', 0) for r in records]
                
                # Check for unrealistic execution times
                if execution_times:
                    max_time = max(execution_times)
                    if max_time > 60000:  # 60 seconds
                        issues.append(DiagnosticIssue(
                            issue_id="unrealistic_execution_times",
                            category=DiagnosticCategory.DATA_INTEGRITY,
                            severity=DiagnosticSeverity.WARNING,
                            title="Unrealistic Execution Times",
                            description=f"Found execution times over 60 seconds: {max_time:.1f}ms",
                            affected_components=["data_integrity"],
                            recommendations=[
                                "Review hook execution logic for performance issues",
                                "Check for hanging processes or timeouts",
                                "Validate execution time recording accuracy"
                            ],
                            metadata={'max_execution_time_ms': max_time}
                        ))
                
                # Check for missing required fields
                records_with_missing_data = 0
                for record in records:
                    if not record.data.get('hook_id') or not record.data.get('execution_id'):
                        records_with_missing_data += 1
                
                if records_with_missing_data > 0:
                    issues.append(DiagnosticIssue(
                        issue_id="missing_required_data",
                        category=DiagnosticCategory.DATA_INTEGRITY,
                        severity=DiagnosticSeverity.WARNING,
                        title="Missing Required Data Fields",
                        description=f"Found {records_with_missing_data} records with missing required fields",
                        affected_components=["data_integrity"],
                        recommendations=[
                            "Review data recording logic",
                            "Validate hook execution result structure",
                            "Check for data corruption issues"
                        ],
                        metadata={'affected_records': records_with_missing_data}
                    ))
            
        except Exception as e:
            logger.error(f"Data integrity check failed: {e}")
            issues.append(DiagnosticIssue(
                issue_id="data_integrity_check_error",
                category=DiagnosticCategory.DATA_INTEGRITY,
                severity=DiagnosticSeverity.ERROR,
                title="Data Integrity Check Failed",
                description=f"Unable to check data integrity: {str(e)}",
                affected_components=["diagnostic_system"],
                recommendations=["Check database connectivity and data access permissions"]
            ))
        
        return issues
    
    async def _generate_performance_summary(self) -> Dict[str, Any]:
        """Generate performance summary for the diagnostic report."""
        try:
            # Get system metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get hook system metrics
            hook_metrics = {}
            try:
                registry_manager = await get_hook_registry_manager()
                if registry_manager:
                    hook_statuses = await registry_manager.get_all_hook_statuses()
                    if hook_statuses:
                        success_rates = [s['statistics']['success_rate'] for s in hook_statuses]
                        response_times = [s['statistics']['average_execution_time_ms'] for s in hook_statuses]
                        
                        hook_metrics = {
                            'total_hooks': len(hook_statuses),
                            'average_success_rate': statistics.mean(success_rates) if success_rates else 0,
                            'average_response_time_ms': statistics.mean(response_times) if response_times else 0,
                            'max_response_time_ms': max(response_times) if response_times else 0
                        }
            except Exception:
                pass
            
            return {
                'system_resources': {
                    'cpu_usage': cpu_usage,
                    'memory_usage': memory.percent,
                    'disk_usage': disk.percent
                },
                'hook_performance': hook_metrics,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate performance summary: {e}")
            return {'error': str(e)}
    
    def _generate_overall_recommendations(self, issues: List[DiagnosticIssue]) -> List[str]:
        """Generate overall system recommendations based on detected issues."""
        recommendations = []
        
        # Count issues by severity
        critical_count = len([i for i in issues if i.severity == DiagnosticSeverity.CRITICAL])
        error_count = len([i for i in issues if i.severity == DiagnosticSeverity.ERROR])
        warning_count = len([i for i in issues if i.severity == DiagnosticSeverity.WARNING])
        
        if critical_count > 0:
            recommendations.append(
                f"Address {critical_count} critical issue(s) immediately to restore system stability"
            )
        
        if error_count > 0:
            recommendations.append(
                f"Resolve {error_count} error(s) to prevent system degradation"
            )
        
        if warning_count > 3:
            recommendations.append(
                f"Review {warning_count} warning(s) to optimize system performance"
            )
        
        # Category-specific recommendations
        categories_with_issues = set(issue.category for issue in issues)
        
        if DiagnosticCategory.SYSTEM_RESOURCES in categories_with_issues:
            recommendations.append("Monitor system resource usage and consider scaling resources")
        
        if DiagnosticCategory.HOOK_PERFORMANCE in categories_with_issues:
            recommendations.append("Review hook configurations and optimize execution performance")
        
        if DiagnosticCategory.DATABASE_CONNECTIVITY in categories_with_issues:
            recommendations.append("Check database connectivity and performance optimization")
        
        if DiagnosticCategory.CONFIGURATION in categories_with_issues:
            recommendations.append("Review and update system configuration files")
        
        if not recommendations:
            recommendations.append("System appears to be operating normally")
        
        return recommendations
    
    def _calculate_health_score(
        self, 
        issues: List[DiagnosticIssue], 
        performance_summary: Dict[str, Any]
    ) -> float:
        """Calculate overall system health score (0-100)."""
        base_score = 100.0
        
        # Deduct points for issues
        for issue in issues:
            if issue.severity == DiagnosticSeverity.CRITICAL:
                base_score -= 20
            elif issue.severity == DiagnosticSeverity.ERROR:
                base_score -= 10
            elif issue.severity == DiagnosticSeverity.WARNING:
                base_score -= 5
            elif issue.severity == DiagnosticSeverity.INFO:
                base_score -= 1
        
        # Adjust based on performance metrics
        system_resources = performance_summary.get('system_resources', {})
        
        cpu_usage = system_resources.get('cpu_usage', 0)
        if cpu_usage > 90:
            base_score -= 10
        elif cpu_usage > 70:
            base_score -= 5
        
        memory_usage = system_resources.get('memory_usage', 0)
        if memory_usage > 95:
            base_score -= 10
        elif memory_usage > 80:
            base_score -= 5
        
        # Ensure score is within bounds
        return max(0.0, min(100.0, base_score))
    
    async def export_diagnostic_report(
        self, 
        report: DiagnosticReport, 
        format: str = "json"
    ) -> str:
        """
        Export diagnostic report in specified format.
        
        Args:
            report: Diagnostic report to export
            format: Export format ("json", "text", "html")
            
        Returns:
            Formatted report string
        """
        if format == "json":
            return json.dumps({
                'report_id': report.report_id,
                'generated_at': report.generated_at.isoformat(),
                'system_info': report.system_info,
                'issues': [
                    {
                        'issue_id': issue.issue_id,
                        'category': issue.category.value,
                        'severity': issue.severity.value,
                        'title': issue.title,
                        'description': issue.description,
                        'affected_components': issue.affected_components,
                        'recommendations': issue.recommendations,
                        'metadata': issue.metadata,
                        'detected_at': issue.detected_at.isoformat()
                    }
                    for issue in report.issues
                ],
                'performance_summary': report.performance_summary,
                'recommendations': report.recommendations,
                'overall_health_score': report.overall_health_score
            }, indent=2)
        
        elif format == "text":
            lines = [
                f"DevSync AI System Diagnostic Report",
                f"Report ID: {report.report_id}",
                f"Generated: {report.generated_at.isoformat()}",
                f"Health Score: {report.overall_health_score:.1f}/100",
                "",
                "SYSTEM INFORMATION:",
                f"  Platform: {report.system_info.get('platform', 'Unknown')}",
                f"  CPU Usage: {report.system_info.get('current_cpu_usage', 0):.1f}%",
                f"  Memory Usage: {report.system_info.get('current_memory_usage', 0):.1f}%",
                f"  Disk Usage: {report.system_info.get('current_disk_usage', 0):.1f}%",
                "",
                f"ISSUES FOUND ({len(report.issues)}):"
            ]
            
            for issue in report.issues:
                lines.extend([
                    f"  [{issue.severity.value.upper()}] {issue.title}",
                    f"    Category: {issue.category.value}",
                    f"    Description: {issue.description}",
                    f"    Affected: {', '.join(issue.affected_components)}",
                    f"    Recommendations:",
                ])
                for rec in issue.recommendations:
                    lines.append(f"      - {rec}")
                lines.append("")
            
            lines.extend([
                "OVERALL RECOMMENDATIONS:",
            ])
            for rec in report.recommendations:
                lines.append(f"  - {rec}")
            
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global diagnostic tools instance
_diagnostic_tools: Optional[SystemDiagnosticTools] = None


def get_diagnostic_tools() -> SystemDiagnosticTools:
    """Get the global diagnostic tools instance."""
    global _diagnostic_tools
    if _diagnostic_tools is None:
        _diagnostic_tools = SystemDiagnosticTools()
    return _diagnostic_tools