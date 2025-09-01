"""
Intelligent Data Aggregation and Quality Engine

This module provides advanced data collection, quality assessment, and aggregation
capabilities for the weekly changelog generation system. It implements parallel
data collection with intelligent retry patterns, circuit breakers, data conflict
resolution, quality scoring, and intelligent caching strategies.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from abc import ABC, abstractmethod

# Optional imports for services - will be imported only when needed
try:
    from ..services.github import GitHubService
    GITHUB_AVAILABLE = True
except ImportError:
    GitHubService = None
    GITHUB_AVAILABLE = False

try:
    from ..services.jira import JIRAService
    JIRA_AVAILABLE = True
except ImportError:
    JIRAService = None
    JIRA_AVAILABLE = False

try:
    from ..analytics.team_productivity_analyzer import TeamProductivityAnalyzer
    TEAM_ANALYTICS_AVAILABLE = True
except ImportError:
    TeamProductivityAnalyzer = None
    TEAM_ANALYTICS_AVAILABLE = False


logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """Types of data sources supported by the aggregator."""
    GITHUB = "github"
    JIRA = "jira"
    TEAM_METRICS = "team_metrics"
    CALENDAR = "calendar"
    CUSTOM = "custom"


class DataQualityLevel(Enum):
    """Data quality assessment levels."""
    EXCELLENT = "excellent"  # 90-100% quality score
    GOOD = "good"           # 70-89% quality score
    FAIR = "fair"           # 50-69% quality score
    POOR = "poor"           # Below 50% quality score


class CircuitBreakerState(Enum):
    """Circuit breaker states for service protection."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Service unavailable
    HALF_OPEN = "half_open" # Testing service recovery


@dataclass
class DataCollectionConfig:
    """Configuration for data collection operations."""
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff_factor: float = 2.0
    timeout_seconds: int = 30
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60
    parallel_workers: int = 4
    cache_ttl_seconds: int = 1800  # 30 minutes
    enable_cache_warming: bool = True


@dataclass
class DataSource:
    """Represents a data source with its configuration and state."""
    source_type: DataSourceType
    identifier: str
    service_instance: Any
    config: DataCollectionConfig = field(default_factory=DataCollectionConfig)
    circuit_breaker_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None


@dataclass
class DataQualityMetrics:
    """Metrics for assessing data quality."""
    completeness_score: float  # 0.0 to 1.0
    accuracy_score: float      # 0.0 to 1.0
    consistency_score: float   # 0.0 to 1.0
    timeliness_score: float    # 0.0 to 1.0
    overall_score: float       # 0.0 to 1.0
    quality_level: DataQualityLevel
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class CollectedData:
    """Container for collected data with metadata."""
    source_type: DataSourceType
    source_identifier: str
    data: Dict[str, Any]
    collection_timestamp: datetime
    quality_metrics: DataQualityMetrics
    confidence_score: float  # 0.0 to 1.0
    schema_version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedData:
    """Final aggregated data with conflict resolution applied."""
    github_data: Optional[Dict[str, Any]] = None
    jira_data: Optional[Dict[str, Any]] = None
    team_metrics: Optional[Dict[str, Any]] = None
    calendar_data: Optional[Dict[str, Any]] = None
    custom_data: Dict[str, Any] = field(default_factory=dict)
    overall_quality: DataQualityMetrics = None
    aggregation_timestamp: datetime = field(default_factory=datetime.utcnow)
    data_sources_used: List[str] = field(default_factory=list)
    conflicts_resolved: List[str] = field(default_factory=list)
    fallback_data_used: bool = False


class DataCollectionError(Exception):
    """Base exception for data collection errors."""
    pass


class CircuitBreakerOpenError(DataCollectionError):
    """Raised when circuit breaker is open."""
    pass


class DataQualityError(DataCollectionError):
    """Raised when data quality is below acceptable threshold."""
    pass


class CacheManager:
    """Intelligent caching with TTL optimization and cache warming."""
    
    def __init__(self):
        self._cache: Dict[str, Tuple[Any, datetime, int]] = {}
        self._access_patterns: Dict[str, List[datetime]] = {}
        self._warming_tasks: Set[str] = set()
    
    def _generate_cache_key(self, source_type: DataSourceType, identifier: str, 
                          params: Dict[str, Any]) -> str:
        """Generate a unique cache key for the data request."""
        key_data = {
            'source_type': source_type.value,
            'identifier': identifier,
            'params': sorted(params.items()) if params else []
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def get(self, source_type: DataSourceType, identifier: str, 
            params: Dict[str, Any] = None) -> Optional[Any]:
        """Retrieve data from cache if available and not expired."""
        cache_key = self._generate_cache_key(source_type, identifier, params or {})
        
        if cache_key in self._cache:
            data, timestamp, ttl = self._cache[cache_key]
            if datetime.utcnow() - timestamp < timedelta(seconds=ttl):
                # Track access pattern for optimization
                if cache_key not in self._access_patterns:
                    self._access_patterns[cache_key] = []
                self._access_patterns[cache_key].append(datetime.utcnow())
                
                logger.debug(f"Cache hit for {source_type.value}:{identifier}")
                return data
            else:
                # Expired, remove from cache
                del self._cache[cache_key]
                logger.debug(f"Cache expired for {source_type.value}:{identifier}")
        
        return None
    
    def set(self, source_type: DataSourceType, identifier: str, data: Any,
            ttl: int, params: Dict[str, Any] = None) -> None:
        """Store data in cache with TTL."""
        cache_key = self._generate_cache_key(source_type, identifier, params or {})
        self._cache[cache_key] = (data, datetime.utcnow(), ttl)
        logger.debug(f"Cached data for {source_type.value}:{identifier} (TTL: {ttl}s)")
    
    def optimize_ttl(self, source_type: DataSourceType, identifier: str,
                     params: Dict[str, Any] = None) -> int:
        """Optimize TTL based on access patterns."""
        cache_key = self._generate_cache_key(source_type, identifier, params or {})
        
        if cache_key not in self._access_patterns:
            return 1800  # Default 30 minutes
        
        accesses = self._access_patterns[cache_key]
        if len(accesses) < 2:
            return 1800
        
        # Calculate average access interval
        intervals = []
        for i in range(1, len(accesses)):
            interval = (accesses[i] - accesses[i-1]).total_seconds()
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals)
        
        # Set TTL to 50% of average access interval, with bounds
        optimized_ttl = max(300, min(3600, int(avg_interval * 0.5)))
        
        logger.debug(f"Optimized TTL for {cache_key}: {optimized_ttl}s")
        return optimized_ttl
    
    async def warm_cache(self, source_type: DataSourceType, identifier: str,
                        data_collector: Callable, params: Dict[str, Any] = None) -> None:
        """Proactively warm cache for frequently accessed data."""
        cache_key = self._generate_cache_key(source_type, identifier, params or {})
        
        if cache_key in self._warming_tasks:
            return  # Already warming
        
        self._warming_tasks.add(cache_key)
        
        try:
            logger.debug(f"Warming cache for {source_type.value}:{identifier}")
            data = await data_collector()
            ttl = self.optimize_ttl(source_type, identifier, params)
            self.set(source_type, identifier, data, ttl, params)
        except Exception as e:
            logger.warning(f"Cache warming failed for {cache_key}: {e}")
        finally:
            self._warming_tasks.discard(cache_key)
    
    def clear_expired(self) -> int:
        """Clear expired cache entries and return count of cleared items."""
        now = datetime.utcnow()
        expired_keys = []
        
        for key, (data, timestamp, ttl) in self._cache.items():
            if now - timestamp >= timedelta(seconds=ttl):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        logger.debug(f"Cleared {len(expired_keys)} expired cache entries")
        return len(expired_keys)


class DataValidator:
    """Schema validation and type safety for collected data."""
    
    @staticmethod
    def validate_github_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate GitHub data structure and content."""
        errors = []
        
        # Required fields
        required_fields = ['commits', 'pull_requests', 'contributors']
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate commits structure
        if 'commits' in data:
            if not isinstance(data['commits'], list):
                errors.append("Commits must be a list")
            else:
                for i, commit in enumerate(data['commits']):
                    if not isinstance(commit, dict):
                        errors.append(f"Commit {i} must be a dictionary")
                    elif 'sha' not in commit or 'message' not in commit:
                        errors.append(f"Commit {i} missing required fields")
        
        # Validate pull requests
        if 'pull_requests' in data:
            if not isinstance(data['pull_requests'], list):
                errors.append("Pull requests must be a list")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_jira_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate JIRA data structure and content."""
        errors = []
        
        # Required fields
        required_fields = ['issues', 'sprint_info']
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate issues structure
        if 'issues' in data:
            if not isinstance(data['issues'], list):
                errors.append("Issues must be a list")
            else:
                for i, issue in enumerate(data['issues']):
                    if not isinstance(issue, dict):
                        errors.append(f"Issue {i} must be a dictionary")
                    elif 'key' not in issue or 'status' not in issue:
                        errors.append(f"Issue {i} missing required fields")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_team_metrics(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate team metrics data structure."""
        errors = []
        
        # Required fields
        required_fields = ['productivity_metrics', 'collaboration_metrics']
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_data(cls, source_type: DataSourceType, 
                     data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate data based on source type."""
        if source_type == DataSourceType.GITHUB:
            return cls.validate_github_data(data)
        elif source_type == DataSourceType.JIRA:
            return cls.validate_jira_data(data)
        elif source_type == DataSourceType.TEAM_METRICS:
            return cls.validate_team_metrics(data)
        else:
            # For custom sources, basic validation
            if not isinstance(data, dict):
                return False, ["Data must be a dictionary"]
            return True, []


class DataQualityAssessor:
    """Assess data quality with completeness and accuracy metrics."""
    
    @staticmethod
    def assess_completeness(data: Dict[str, Any], 
                          expected_fields: List[str]) -> float:
        """Assess data completeness based on expected fields."""
        if not expected_fields:
            return 1.0
        
        present_fields = sum(1 for field in expected_fields if field in data and data[field] is not None)
        return present_fields / len(expected_fields)
    
    @staticmethod
    def assess_accuracy(data: Dict[str, Any], source_type: DataSourceType) -> float:
        """Assess data accuracy based on data type and content validation."""
        accuracy_score = 1.0
        
        # Type checking and format validation
        if source_type == DataSourceType.GITHUB:
            # Check for valid GitHub data patterns
            if 'commits' in data:
                commits = data['commits']
                if isinstance(commits, list):
                    for commit in commits:
                        if isinstance(commit, dict) and 'sha' in commit:
                            # Validate SHA format (40 character hex)
                            sha = commit['sha']
                            if not (isinstance(sha, str) and len(sha) == 40 and 
                                   all(c in '0123456789abcdef' for c in sha.lower())):
                                accuracy_score -= 0.1
                        else:
                            accuracy_score -= 0.1
        
        elif source_type == DataSourceType.JIRA:
            # Check for valid JIRA data patterns
            if 'issues' in data:
                issues = data['issues']
                if isinstance(issues, list):
                    for issue in issues:
                        if isinstance(issue, dict) and 'key' in issue:
                            # Validate JIRA key format (PROJECT-123)
                            key = issue['key']
                            if not (isinstance(key, str) and '-' in key):
                                accuracy_score -= 0.1
                        else:
                            accuracy_score -= 0.1
        
        return max(0.0, accuracy_score)
    
    @staticmethod
    def assess_consistency(data: Dict[str, Any]) -> float:
        """Assess internal data consistency."""
        consistency_score = 1.0
        
        # Check for data type consistency
        for key, value in data.items():
            if isinstance(value, list):
                if value:  # Non-empty list
                    first_type = type(value[0])
                    for item in value[1:]:
                        if type(item) != first_type:
                            consistency_score -= 0.1
                            break
        
        return max(0.0, consistency_score)
    
    @staticmethod
    def assess_timeliness(collection_timestamp: datetime, 
                         max_age_hours: int = 24) -> float:
        """Assess data timeliness based on collection timestamp."""
        age_hours = (datetime.utcnow() - collection_timestamp).total_seconds() / 3600
        
        if age_hours <= 1:
            return 1.0
        elif age_hours <= max_age_hours:
            return max(0.0, 1.0 - (age_hours - 1) / (max_age_hours - 1))
        else:
            return 0.0
    
    @classmethod
    def assess_quality(cls, collected_data: CollectedData) -> DataQualityMetrics:
        """Comprehensive data quality assessment."""
        # Define expected fields based on source type
        expected_fields = {
            DataSourceType.GITHUB: ['commits', 'pull_requests', 'contributors'],
            DataSourceType.JIRA: ['issues', 'sprint_info'],
            DataSourceType.TEAM_METRICS: ['productivity_metrics', 'collaboration_metrics'],
        }
        
        source_expected = expected_fields.get(collected_data.source_type, [])
        
        # Calculate individual scores
        completeness = cls.assess_completeness(collected_data.data, source_expected)
        accuracy = cls.assess_accuracy(collected_data.data, collected_data.source_type)
        consistency = cls.assess_consistency(collected_data.data)
        timeliness = cls.assess_timeliness(collected_data.collection_timestamp)
        
        # Calculate overall score (weighted average)
        overall = (completeness * 0.3 + accuracy * 0.3 + 
                  consistency * 0.2 + timeliness * 0.2)
        
        # Determine quality level
        if overall >= 0.9:
            quality_level = DataQualityLevel.EXCELLENT
        elif overall >= 0.7:
            quality_level = DataQualityLevel.GOOD
        elif overall >= 0.5:
            quality_level = DataQualityLevel.FAIR
        else:
            quality_level = DataQualityLevel.POOR
        
        # Generate issues and recommendations
        issues = []
        recommendations = []
        
        if completeness < 0.8:
            issues.append(f"Data completeness below threshold: {completeness:.2f}")
            recommendations.append("Verify data source connectivity and permissions")
        
        if accuracy < 0.8:
            issues.append(f"Data accuracy concerns: {accuracy:.2f}")
            recommendations.append("Review data validation rules and source data quality")
        
        if consistency < 0.8:
            issues.append(f"Data consistency issues: {consistency:.2f}")
            recommendations.append("Implement stricter data type validation")
        
        if timeliness < 0.8:
            issues.append(f"Data freshness concerns: {timeliness:.2f}")
            recommendations.append("Increase data collection frequency or check source delays")
        
        return DataQualityMetrics(
            completeness_score=completeness,
            accuracy_score=accuracy,
            consistency_score=consistency,
            timeliness_score=timeliness,
            overall_score=overall,
            quality_level=quality_level,
            issues=issues,
            recommendations=recommendations
        )


class ConflictResolver:
    """Resolve data conflicts using weighted scoring and confidence algorithms."""
    
    @staticmethod
    def calculate_source_weight(source_type: DataSourceType, 
                              quality_metrics: DataQualityMetrics,
                              confidence_score: float) -> float:
        """Calculate weight for a data source based on quality and confidence."""
        # Base weights by source type
        base_weights = {
            DataSourceType.GITHUB: 0.9,
            DataSourceType.JIRA: 0.9,
            DataSourceType.TEAM_METRICS: 0.8,
            DataSourceType.CALENDAR: 0.7,
            DataSourceType.CUSTOM: 0.6
        }
        
        base_weight = base_weights.get(source_type, 0.5)
        quality_weight = quality_metrics.overall_score
        
        # Combined weight
        return (base_weight * 0.4 + quality_weight * 0.4 + confidence_score * 0.2)
    
    @staticmethod
    def resolve_field_conflict(field_name: str, 
                             conflicting_values: List[Tuple[Any, float]]) -> Tuple[Any, str]:
        """Resolve conflict for a specific field using weighted voting."""
        if not conflicting_values:
            return None, "No values provided"
        
        if len(conflicting_values) == 1:
            return conflicting_values[0][0], "Single source"
        
        # For numeric values, use weighted average
        if all(isinstance(value, (int, float)) for value, _ in conflicting_values):
            total_weight = sum(weight for _, weight in conflicting_values)
            if total_weight > 0:
                weighted_sum = sum(value * weight for value, weight in conflicting_values)
                resolved_value = weighted_sum / total_weight
                return resolved_value, f"Weighted average of {len(conflicting_values)} sources"
        
        # For other types, choose highest weighted value
        best_value, best_weight = max(conflicting_values, key=lambda x: x[1])
        return best_value, f"Highest confidence source (weight: {best_weight:.3f})"
    
    @classmethod
    def resolve_conflicts(cls, collected_data_list: List[CollectedData]) -> Tuple[Dict[str, Any], List[str]]:
        """Resolve conflicts across multiple data sources."""
        if not collected_data_list:
            return {}, []
        
        if len(collected_data_list) == 1:
            return collected_data_list[0].data, []
        
        # Group data by source type
        data_by_source = {}
        for collected_data in collected_data_list:
            source_key = collected_data.source_type.value
            if source_key not in data_by_source:
                data_by_source[source_key] = []
            data_by_source[source_key].append(collected_data)
        
        resolved_data = {}
        conflicts_resolved = []
        
        # Process each source type separately (no conflicts within same type)
        for source_type, data_list in data_by_source.items():
            if len(data_list) == 1:
                # No conflicts within this source type
                resolved_data[source_type] = data_list[0].data
            else:
                # Multiple instances of same source type - resolve conflicts
                source_resolved, source_conflicts = cls._resolve_same_source_conflicts(data_list)
                resolved_data[source_type] = source_resolved
                conflicts_resolved.extend(source_conflicts)
        
        return resolved_data, conflicts_resolved
    
    @classmethod
    def _resolve_same_source_conflicts(cls, data_list: List[CollectedData]) -> Tuple[Dict[str, Any], List[str]]:
        """Resolve conflicts within the same source type."""
        if len(data_list) == 1:
            return data_list[0].data, []
        
        # Calculate weights for each data instance
        weighted_data = []
        for collected_data in data_list:
            weight = cls.calculate_source_weight(
                collected_data.source_type,
                collected_data.quality_metrics,
                collected_data.confidence_score
            )
            weighted_data.append((collected_data.data, weight))
        
        # Find all unique fields across all instances
        all_fields = set()
        for data, _ in weighted_data:
            all_fields.update(data.keys())
        
        resolved_data = {}
        conflicts_resolved = []
        
        # Resolve each field
        for field in all_fields:
            field_values = []
            for data, weight in weighted_data:
                if field in data:
                    field_values.append((data[field], weight))
            
            if len(field_values) > 1:
                # Conflict exists
                resolved_value, resolution_method = cls.resolve_field_conflict(field, field_values)
                resolved_data[field] = resolved_value
                conflicts_resolved.append(f"Field '{field}': {resolution_method}")
            elif len(field_values) == 1:
                # No conflict
                resolved_data[field] = field_values[0][0]
        
        return resolved_data, conflicts_resolved


class IntelligentDataAggregator:
    """
    Advanced data aggregation system with parallel collection, intelligent retry,
    circuit breakers, quality assessment, and conflict resolution.
    """
    
    def __init__(self, config: DataCollectionConfig = None):
        self.config = config or DataCollectionConfig()
        self.cache_manager = CacheManager()
        self.data_sources: Dict[str, DataSource] = {}
        self.executor = ThreadPoolExecutor(max_workers=self.config.parallel_workers)
        
        # Initialize built-in services
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize built-in data source services."""
        if GITHUB_AVAILABLE:
            try:
                # GitHub service
                github_service = GitHubService()
                self.register_data_source(
                    DataSourceType.GITHUB,
                    "default",
                    github_service
                )
            except Exception as e:
                logger.warning(f"Failed to initialize GitHub service: {e}")
        else:
            logger.info("GitHub service not available - skipping initialization")
        
        if JIRA_AVAILABLE:
            try:
                # JIRA service
                jira_service = JIRAService()
                self.register_data_source(
                    DataSourceType.JIRA,
                    "default",
                    jira_service
                )
            except Exception as e:
                logger.warning(f"Failed to initialize JIRA service: {e}")
        else:
            logger.info("JIRA service not available - skipping initialization")
        
        if TEAM_ANALYTICS_AVAILABLE:
            try:
                # Team productivity analyzer
                team_analyzer = TeamProductivityAnalyzer()
                self.register_data_source(
                    DataSourceType.TEAM_METRICS,
                    "default",
                    team_analyzer
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Team Productivity Analyzer: {e}")
        else:
            logger.info("Team Productivity Analyzer not available - skipping initialization")
    
    def register_data_source(self, source_type: DataSourceType, 
                           identifier: str, service_instance: Any,
                           config: DataCollectionConfig = None) -> None:
        """Register a data source with the aggregator."""
        source_key = f"{source_type.value}:{identifier}"
        
        self.data_sources[source_key] = DataSource(
            source_type=source_type,
            identifier=identifier,
            service_instance=service_instance,
            config=config or self.config
        )
        
        logger.info(f"Registered data source: {source_key}")
    
    def _check_circuit_breaker(self, data_source: DataSource) -> bool:
        """Check if circuit breaker allows operation."""
        if data_source.circuit_breaker_state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (data_source.last_failure_time and 
                datetime.utcnow() - data_source.last_failure_time > 
                timedelta(seconds=data_source.config.circuit_breaker_recovery_timeout)):
                
                data_source.circuit_breaker_state = CircuitBreakerState.HALF_OPEN
                logger.info(f"Circuit breaker half-open for {data_source.identifier}")
                return True
            else:
                return False
        
        return True
    
    def _update_circuit_breaker(self, data_source: DataSource, success: bool) -> None:
        """Update circuit breaker state based on operation result."""
        if success:
            data_source.failure_count = 0
            data_source.last_success_time = datetime.utcnow()
            
            if data_source.circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
                data_source.circuit_breaker_state = CircuitBreakerState.CLOSED
                logger.info(f"Circuit breaker closed for {data_source.identifier}")
        else:
            data_source.failure_count += 1
            data_source.last_failure_time = datetime.utcnow()
            
            if data_source.failure_count >= data_source.config.circuit_breaker_failure_threshold:
                data_source.circuit_breaker_state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker opened for {data_source.identifier}")
    
    async def _collect_with_retry(self, data_source: DataSource,
                                collection_func: Callable,
                                *args, **kwargs) -> Dict[str, Any]:
        """Collect data with intelligent retry logic."""
        last_exception = None
        
        for attempt in range(data_source.config.max_retries + 1):
            try:
                # Check circuit breaker
                if not self._check_circuit_breaker(data_source):
                    raise CircuitBreakerOpenError(f"Circuit breaker open for {data_source.identifier}")
                
                # Attempt data collection with timeout
                result = await asyncio.wait_for(
                    collection_func(*args, **kwargs),
                    timeout=data_source.config.timeout_seconds
                )
                
                # Success - update circuit breaker
                self._update_circuit_breaker(data_source, True)
                
                if attempt > 0:
                    logger.info(f"Data collection succeeded on attempt {attempt + 1} for {data_source.identifier}")
                
                return result
                
            except Exception as e:
                last_exception = e
                self._update_circuit_breaker(data_source, False)
                
                if attempt < data_source.config.max_retries:
                    delay = (data_source.config.retry_delay * 
                            (data_source.config.retry_backoff_factor ** attempt))
                    
                    logger.warning(f"Data collection attempt {attempt + 1} failed for {data_source.identifier}: {e}. "
                                 f"Retrying in {delay:.2f}s")
                    
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Data collection failed after {attempt + 1} attempts for {data_source.identifier}: {e}")
        
        raise last_exception
    
    async def _collect_github_data(self, data_source: DataSource, 
                                 team_id: str, date_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Collect GitHub data for the specified team and date range."""
        github_service = data_source.service_instance
        
        # Check cache first
        cache_params = {'team_id': team_id, 'date_range': date_range}
        cached_data = self.cache_manager.get(DataSourceType.GITHUB, data_source.identifier, cache_params)
        if cached_data:
            return cached_data
        
        # Collect fresh data
        start_date, end_date = date_range
        
        # This would be implemented based on the actual GitHub service interface
        # For now, we'll simulate the data collection
        data = {
            'commits': [],
            'pull_requests': [],
            'contributors': [],
            'repository_health': {},
            'collection_metadata': {
                'team_id': team_id,
                'date_range': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
                'collected_at': datetime.utcnow().isoformat()
            }
        }
        
        # Cache the result
        ttl = self.cache_manager.optimize_ttl(DataSourceType.GITHUB, data_source.identifier, cache_params)
        self.cache_manager.set(DataSourceType.GITHUB, data_source.identifier, data, ttl, cache_params)
        
        return data
    
    async def _collect_jira_data(self, data_source: DataSource,
                               team_id: str, date_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Collect JIRA data for the specified team and date range."""
        jira_service = data_source.service_instance
        
        # Check cache first
        cache_params = {'team_id': team_id, 'date_range': date_range}
        cached_data = self.cache_manager.get(DataSourceType.JIRA, data_source.identifier, cache_params)
        if cached_data:
            return cached_data
        
        # Collect fresh data
        start_date, end_date = date_range
        
        # This would be implemented based on the actual JIRA service interface
        data = {
            'issues': [],
            'sprint_info': {},
            'velocity_metrics': {},
            'collection_metadata': {
                'team_id': team_id,
                'date_range': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
                'collected_at': datetime.utcnow().isoformat()
            }
        }
        
        # Cache the result
        ttl = self.cache_manager.optimize_ttl(DataSourceType.JIRA, data_source.identifier, cache_params)
        self.cache_manager.set(DataSourceType.JIRA, data_source.identifier, data, ttl, cache_params)
        
        return data
    
    async def _collect_team_metrics(self, data_source: DataSource,
                                  team_id: str, date_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Collect team productivity metrics."""
        team_analyzer = data_source.service_instance
        
        # Check cache first
        cache_params = {'team_id': team_id, 'date_range': date_range}
        cached_data = self.cache_manager.get(DataSourceType.TEAM_METRICS, data_source.identifier, cache_params)
        if cached_data:
            return cached_data
        
        # Collect fresh data
        start_date, end_date = date_range
        
        # This would be implemented based on the actual team analyzer interface
        data = {
            'productivity_metrics': {},
            'collaboration_metrics': {},
            'deployment_metrics': {},
            'collection_metadata': {
                'team_id': team_id,
                'date_range': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
                'collected_at': datetime.utcnow().isoformat()
            }
        }
        
        # Cache the result
        ttl = self.cache_manager.optimize_ttl(DataSourceType.TEAM_METRICS, data_source.identifier, cache_params)
        self.cache_manager.set(DataSourceType.TEAM_METRICS, data_source.identifier, data, ttl, cache_params)
        
        return data
    
    async def _collect_single_source(self, source_key: str, team_id: str,
                                   date_range: Tuple[datetime, datetime]) -> Optional[CollectedData]:
        """Collect data from a single source with error handling."""
        if source_key not in self.data_sources:
            logger.error(f"Data source not found: {source_key}")
            return None
        
        data_source = self.data_sources[source_key]
        
        try:
            # Select appropriate collection method
            if data_source.source_type == DataSourceType.GITHUB:
                collection_func = self._collect_github_data
            elif data_source.source_type == DataSourceType.JIRA:
                collection_func = self._collect_jira_data
            elif data_source.source_type == DataSourceType.TEAM_METRICS:
                collection_func = self._collect_team_metrics
            else:
                logger.warning(f"No collection method for source type: {data_source.source_type}")
                return None
            
            # Collect data with retry logic
            raw_data = await self._collect_with_retry(
                data_source, collection_func, data_source, team_id, date_range
            )
            
            # Validate data
            is_valid, validation_errors = DataValidator.validate_data(
                data_source.source_type, raw_data
            )
            
            if not is_valid:
                logger.warning(f"Data validation failed for {source_key}: {validation_errors}")
                # Continue with invalid data but lower confidence
                confidence_score = 0.3
            else:
                confidence_score = 0.9
            
            # Create collected data object
            collected_data = CollectedData(
                source_type=data_source.source_type,
                source_identifier=data_source.identifier,
                data=raw_data,
                collection_timestamp=datetime.utcnow(),
                quality_metrics=None,  # Will be assessed next
                confidence_score=confidence_score
            )
            
            # Assess data quality
            collected_data.quality_metrics = DataQualityAssessor.assess_quality(collected_data)
            
            logger.info(f"Successfully collected data from {source_key} "
                       f"(Quality: {collected_data.quality_metrics.quality_level.value})")
            
            return collected_data
            
        except Exception as e:
            logger.error(f"Failed to collect data from {source_key}: {e}")
            return None
    
    async def collect_parallel(self, team_id: str, 
                             date_range: Tuple[datetime, datetime],
                             source_types: Optional[List[DataSourceType]] = None) -> List[CollectedData]:
        """Collect data from multiple sources in parallel."""
        # Determine which sources to collect from
        if source_types is None:
            source_keys = list(self.data_sources.keys())
        else:
            source_keys = [key for key in self.data_sources.keys() 
                          if any(source_type.value in key for source_type in source_types)]
        
        if not source_keys:
            logger.warning("No data sources available for collection")
            return []
        
        logger.info(f"Starting parallel data collection from {len(source_keys)} sources for team {team_id}")
        
        # Create collection tasks
        tasks = []
        for source_key in source_keys:
            task = asyncio.create_task(
                self._collect_single_source(source_key, team_id, date_range),
                name=f"collect_{source_key}"
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        collected_data_list = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Collection task {source_keys[i]} failed: {result}")
            elif result is not None:
                collected_data_list.append(result)
        
        logger.info(f"Parallel collection completed: {len(collected_data_list)}/{len(source_keys)} sources successful")
        
        return collected_data_list
    
    def _create_fallback_data(self, team_id: str, 
                            date_range: Tuple[datetime, datetime]) -> AggregatedData:
        """Create fallback data when primary collection fails."""
        logger.warning(f"Creating fallback data for team {team_id}")
        
        # Try to get cached data from any available source
        fallback_data = {}
        
        for source_key, data_source in self.data_sources.items():
            cache_params = {'team_id': team_id, 'date_range': date_range}
            cached_data = self.cache_manager.get(
                data_source.source_type, 
                data_source.identifier, 
                cache_params
            )
            
            if cached_data:
                fallback_data[data_source.source_type.value] = cached_data
                logger.info(f"Using cached fallback data from {source_key}")
        
        # Create minimal quality metrics
        fallback_quality = DataQualityMetrics(
            completeness_score=0.3,
            accuracy_score=0.5,
            consistency_score=0.5,
            timeliness_score=0.1,
            overall_score=0.35,
            quality_level=DataQualityLevel.POOR,
            issues=["Using fallback/cached data due to collection failures"],
            recommendations=["Investigate data source connectivity issues"]
        )
        
        return AggregatedData(
            github_data=fallback_data.get('github'),
            jira_data=fallback_data.get('jira'),
            team_metrics=fallback_data.get('team_metrics'),
            overall_quality=fallback_quality,
            fallback_data_used=True,
            data_sources_used=list(fallback_data.keys())
        )
    
    async def aggregate_data(self, team_id: str,
                           date_range: Tuple[datetime, datetime],
                           source_types: Optional[List[DataSourceType]] = None,
                           min_quality_threshold: float = 0.5) -> AggregatedData:
        """
        Main aggregation method that orchestrates parallel collection,
        quality assessment, and conflict resolution.
        """
        start_time = time.time()
        
        try:
            # Warm cache for frequently accessed data
            if self.config.enable_cache_warming:
                await self._warm_cache_for_team(team_id, date_range)
            
            # Collect data from all sources in parallel
            collected_data_list = await self.collect_parallel(team_id, date_range, source_types)
            
            if not collected_data_list:
                logger.warning(f"No data collected for team {team_id}")
                return self._create_fallback_data(team_id, date_range)
            
            # Filter data by quality threshold
            quality_filtered_data = [
                data for data in collected_data_list
                if data.quality_metrics.overall_score >= min_quality_threshold
            ]
            
            if not quality_filtered_data:
                logger.warning(f"No data meets quality threshold {min_quality_threshold} for team {team_id}")
                # Use best available data even if below threshold
                quality_filtered_data = sorted(
                    collected_data_list,
                    key=lambda x: x.quality_metrics.overall_score,
                    reverse=True
                )[:1]  # Use only the best quality data
            
            # Resolve conflicts across data sources
            resolved_data, conflicts_resolved = ConflictResolver.resolve_conflicts(quality_filtered_data)
            
            # Calculate overall quality metrics
            overall_quality = self._calculate_overall_quality(quality_filtered_data)
            
            # Create aggregated data object
            aggregated_data = AggregatedData(
                github_data=resolved_data.get('github'),
                jira_data=resolved_data.get('jira'),
                team_metrics=resolved_data.get('team_metrics'),
                calendar_data=resolved_data.get('calendar'),
                custom_data={k: v for k, v in resolved_data.items() 
                           if k not in ['github', 'jira', 'team_metrics', 'calendar']},
                overall_quality=overall_quality,
                data_sources_used=[data.source_identifier for data in quality_filtered_data],
                conflicts_resolved=conflicts_resolved,
                fallback_data_used=False
            )
            
            collection_time = time.time() - start_time
            logger.info(f"Data aggregation completed for team {team_id} in {collection_time:.2f}s "
                       f"(Quality: {overall_quality.quality_level.value})")
            
            return aggregated_data
            
        except Exception as e:
            logger.error(f"Data aggregation failed for team {team_id}: {e}")
            return self._create_fallback_data(team_id, date_range)
    
    def _calculate_overall_quality(self, collected_data_list: List[CollectedData]) -> DataQualityMetrics:
        """Calculate overall quality metrics from multiple data sources."""
        if not collected_data_list:
            return DataQualityMetrics(
                completeness_score=0.0,
                accuracy_score=0.0,
                consistency_score=0.0,
                timeliness_score=0.0,
                overall_score=0.0,
                quality_level=DataQualityLevel.POOR
            )
        
        # Calculate weighted averages based on confidence scores
        total_weight = sum(data.confidence_score for data in collected_data_list)
        
        if total_weight == 0:
            # Equal weights if no confidence scores
            weights = [1.0 / len(collected_data_list)] * len(collected_data_list)
        else:
            weights = [data.confidence_score / total_weight for data in collected_data_list]
        
        # Weighted averages
        completeness = sum(data.quality_metrics.completeness_score * weight 
                          for data, weight in zip(collected_data_list, weights))
        accuracy = sum(data.quality_metrics.accuracy_score * weight 
                      for data, weight in zip(collected_data_list, weights))
        consistency = sum(data.quality_metrics.consistency_score * weight 
                         for data, weight in zip(collected_data_list, weights))
        timeliness = sum(data.quality_metrics.timeliness_score * weight 
                        for data, weight in zip(collected_data_list, weights))
        
        overall = (completeness * 0.3 + accuracy * 0.3 + 
                  consistency * 0.2 + timeliness * 0.2)
        
        # Determine quality level
        if overall >= 0.9:
            quality_level = DataQualityLevel.EXCELLENT
        elif overall >= 0.7:
            quality_level = DataQualityLevel.GOOD
        elif overall >= 0.5:
            quality_level = DataQualityLevel.FAIR
        else:
            quality_level = DataQualityLevel.POOR
        
        # Aggregate issues and recommendations
        all_issues = []
        all_recommendations = []
        for data in collected_data_list:
            all_issues.extend(data.quality_metrics.issues)
            all_recommendations.extend(data.quality_metrics.recommendations)
        
        # Remove duplicates while preserving order
        unique_issues = list(dict.fromkeys(all_issues))
        unique_recommendations = list(dict.fromkeys(all_recommendations))
        
        return DataQualityMetrics(
            completeness_score=completeness,
            accuracy_score=accuracy,
            consistency_score=consistency,
            timeliness_score=timeliness,
            overall_score=overall,
            quality_level=quality_level,
            issues=unique_issues,
            recommendations=unique_recommendations
        )
    
    async def _warm_cache_for_team(self, team_id: str, 
                                 date_range: Tuple[datetime, datetime]) -> None:
        """Warm cache for frequently accessed team data."""
        logger.debug(f"Warming cache for team {team_id}")
        
        # Create warming tasks for each data source
        warming_tasks = []
        
        for source_key, data_source in self.data_sources.items():
            cache_params = {'team_id': team_id, 'date_range': date_range}
            
            # Create data collector function
            if data_source.source_type == DataSourceType.GITHUB:
                collector = lambda: self._collect_github_data(data_source, team_id, date_range)
            elif data_source.source_type == DataSourceType.JIRA:
                collector = lambda: self._collect_jira_data(data_source, team_id, date_range)
            elif data_source.source_type == DataSourceType.TEAM_METRICS:
                collector = lambda: self._collect_team_metrics(data_source, team_id, date_range)
            else:
                continue
            
            # Create warming task
            task = asyncio.create_task(
                self.cache_manager.warm_cache(
                    data_source.source_type,
                    data_source.identifier,
                    collector,
                    cache_params
                )
            )
            warming_tasks.append(task)
        
        # Wait for all warming tasks (but don't fail if some fail)
        if warming_tasks:
            await asyncio.gather(*warming_tasks, return_exceptions=True)
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all data sources and the aggregator."""
        health_status = {
            'aggregator_status': 'healthy',
            'data_sources': {},
            'cache_stats': {
                'total_entries': len(self.cache_manager._cache),
                'expired_entries_cleared': self.cache_manager.clear_expired()
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Check each data source
        for source_key, data_source in self.data_sources.items():
            source_health = {
                'circuit_breaker_state': data_source.circuit_breaker_state.value,
                'failure_count': data_source.failure_count,
                'last_success': data_source.last_success_time.isoformat() if data_source.last_success_time else None,
                'last_failure': data_source.last_failure_time.isoformat() if data_source.last_failure_time else None
            }
            
            # Determine overall health
            if data_source.circuit_breaker_state == CircuitBreakerState.OPEN:
                source_health['status'] = 'unhealthy'
            elif data_source.circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
                source_health['status'] = 'recovering'
            else:
                source_health['status'] = 'healthy'
            
            health_status['data_sources'][source_key] = source_health
        
        return health_status
    
    async def cleanup(self) -> None:
        """Cleanup resources and connections."""
        logger.info("Cleaning up IntelligentDataAggregator")
        
        # Clear expired cache entries
        self.cache_manager.clear_expired()
        
        # Shutdown thread pool executor
        self.executor.shutdown(wait=True)
        
        logger.info("IntelligentDataAggregator cleanup completed")


# Performance testing and benchmarking utilities
class PerformanceBenchmark:
    """Performance benchmarking utilities for the data aggregator."""
    
    @staticmethod
    async def benchmark_parallel_collection(aggregator: IntelligentDataAggregator,
                                          team_ids: List[str],
                                          date_range: Tuple[datetime, datetime],
                                          iterations: int = 5) -> Dict[str, Any]:
        """Benchmark parallel data collection performance."""
        logger.info(f"Starting performance benchmark with {len(team_ids)} teams, {iterations} iterations")
        
        results = {
            'team_count': len(team_ids),
            'iterations': iterations,
            'collection_times': [],
            'success_rates': [],
            'quality_scores': [],
            'cache_hit_rates': []
        }
        
        for iteration in range(iterations):
            start_time = time.time()
            successful_collections = 0
            total_quality_score = 0.0
            
            # Collect data for all teams
            for team_id in team_ids:
                try:
                    aggregated_data = await aggregator.aggregate_data(team_id, date_range)
                    successful_collections += 1
                    total_quality_score += aggregated_data.overall_quality.overall_score
                except Exception as e:
                    logger.warning(f"Collection failed for team {team_id}: {e}")
            
            collection_time = time.time() - start_time
            success_rate = successful_collections / len(team_ids)
            avg_quality = total_quality_score / max(successful_collections, 1)
            
            results['collection_times'].append(collection_time)
            results['success_rates'].append(success_rate)
            results['quality_scores'].append(avg_quality)
            
            logger.info(f"Iteration {iteration + 1}: {collection_time:.2f}s, "
                       f"Success: {success_rate:.2%}, Quality: {avg_quality:.3f}")
        
        # Calculate summary statistics
        results['avg_collection_time'] = sum(results['collection_times']) / iterations
        results['avg_success_rate'] = sum(results['success_rates']) / iterations
        results['avg_quality_score'] = sum(results['quality_scores']) / iterations
        
        logger.info(f"Benchmark completed - Avg time: {results['avg_collection_time']:.2f}s, "
                   f"Avg success: {results['avg_success_rate']:.2%}, "
                   f"Avg quality: {results['avg_quality_score']:.3f}")
        
        return results
    
    @staticmethod
    async def load_test(aggregator: IntelligentDataAggregator,
                       concurrent_requests: int,
                       team_id: str,
                       date_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Perform load testing with concurrent requests."""
        logger.info(f"Starting load test with {concurrent_requests} concurrent requests")
        
        async def single_request():
            start_time = time.time()
            try:
                result = await aggregator.aggregate_data(team_id, date_range)
                return {
                    'success': True,
                    'duration': time.time() - start_time,
                    'quality_score': result.overall_quality.overall_score
                }
            except Exception as e:
                return {
                    'success': False,
                    'duration': time.time() - start_time,
                    'error': str(e)
                }
        
        # Create concurrent tasks
        tasks = [single_request() for _ in range(concurrent_requests)]
        
        # Execute all tasks
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_requests = sum(1 for r in results if r['success'])
        failed_requests = concurrent_requests - successful_requests
        avg_duration = sum(r['duration'] for r in results) / len(results)
        avg_quality = sum(r.get('quality_score', 0) for r in results if r['success']) / max(successful_requests, 1)
        
        load_test_results = {
            'concurrent_requests': concurrent_requests,
            'total_time': total_time,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': successful_requests / concurrent_requests,
            'avg_request_duration': avg_duration,
            'avg_quality_score': avg_quality,
            'requests_per_second': concurrent_requests / total_time,
            'errors': [r.get('error') for r in results if not r['success']]
        }
        
        logger.info(f"Load test completed - Success rate: {load_test_results['success_rate']:.2%}, "
                   f"RPS: {load_test_results['requests_per_second']:.2f}, "
                   f"Avg duration: {avg_duration:.3f}s")
        
        return load_test_results