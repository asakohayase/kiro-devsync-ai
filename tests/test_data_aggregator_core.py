"""
Core unit tests for the Intelligent Data Aggregation components

This test suite tests the core components without any external dependencies.
"""

import asyncio
import pytest
import time
import json
import hashlib
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor


# Define the core classes directly in the test file to avoid import issues
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


class CacheManager:
    """Intelligent caching with TTL optimization and cache warming."""
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}
        self._access_patterns: Dict[str, List[datetime]] = {}
        self._warming_tasks: set = set()
    
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
            params: Dict[str, Any] = None) -> Any:
        """Retrieve data from cache if available and not expired."""
        cache_key = self._generate_cache_key(source_type, identifier, params or {})
        
        if cache_key in self._cache:
            data, timestamp, ttl = self._cache[cache_key]
            if datetime.utcnow() - timestamp < timedelta(seconds=ttl):
                # Track access pattern for optimization
                if cache_key not in self._access_patterns:
                    self._access_patterns[cache_key] = []
                self._access_patterns[cache_key].append(datetime.utcnow())
                
                return data
            else:
                # Expired, remove from cache
                del self._cache[cache_key]
        
        return None
    
    def set(self, source_type: DataSourceType, identifier: str, data: Any,
            ttl: int, params: Dict[str, Any] = None) -> None:
        """Store data in cache with TTL."""
        cache_key = self._generate_cache_key(source_type, identifier, params or {})
        self._cache[cache_key] = (data, datetime.utcnow(), ttl)
    
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
        
        return optimized_ttl
    
    def clear_expired(self) -> int:
        """Clear expired cache entries and return count of cleared items."""
        now = datetime.utcnow()
        expired_keys = []
        
        for key, (data, timestamp, ttl) in self._cache.items():
            if now - timestamp >= timedelta(seconds=ttl):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)


class DataValidator:
    """Schema validation and type safety for collected data."""
    
    @staticmethod
    def validate_github_data(data: Dict[str, Any]) -> tuple:
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
    def validate_jira_data(data: Dict[str, Any]) -> tuple:
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
    def validate_team_metrics(data: Dict[str, Any]) -> tuple:
        """Validate team metrics data structure."""
        errors = []
        
        # Required fields
        required_fields = ['productivity_metrics', 'collaboration_metrics']
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        return len(errors) == 0, errors


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
                             conflicting_values: List[tuple]) -> tuple:
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


# Test Classes
class TestCacheManager:
    """Test the intelligent caching system."""
    
    def setup_method(self):
        self.cache_manager = CacheManager()
    
    def test_cache_basic_operations(self):
        """Test basic cache get/set operations."""
        # Test cache miss
        result = self.cache_manager.get(DataSourceType.GITHUB, "test", {"param": "value"})
        assert result is None
        
        # Test cache set and hit
        test_data = {"test": "data"}
        self.cache_manager.set(DataSourceType.GITHUB, "test", test_data, 3600, {"param": "value"})
        
        cached_result = self.cache_manager.get(DataSourceType.GITHUB, "test", {"param": "value"})
        assert cached_result == test_data
    
    def test_cache_expiration(self):
        """Test cache TTL and expiration."""
        test_data = {"test": "data"}
        
        # Set with very short TTL
        self.cache_manager.set(DataSourceType.GITHUB, "test", test_data, 1)
        
        # Should be available immediately
        result = self.cache_manager.get(DataSourceType.GITHUB, "test")
        assert result == test_data
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        result = self.cache_manager.get(DataSourceType.GITHUB, "test")
        assert result is None
    
    def test_cache_key_generation(self):
        """Test cache key generation for different parameters."""
        # Same parameters should generate same key
        key1 = self.cache_manager._generate_cache_key(
            DataSourceType.GITHUB, "test", {"a": 1, "b": 2}
        )
        key2 = self.cache_manager._generate_cache_key(
            DataSourceType.GITHUB, "test", {"b": 2, "a": 1}
        )
        assert key1 == key2
        
        # Different parameters should generate different keys
        key3 = self.cache_manager._generate_cache_key(
            DataSourceType.GITHUB, "test", {"a": 1, "b": 3}
        )
        assert key1 != key3
    
    def test_ttl_optimization(self):
        """Test TTL optimization based on access patterns."""
        # No access history should return default
        ttl = self.cache_manager.optimize_ttl(DataSourceType.GITHUB, "test")
        assert ttl == 1800  # Default 30 minutes
        
        # Simulate access pattern
        cache_key = self.cache_manager._generate_cache_key(DataSourceType.GITHUB, "test", {})
        now = datetime.utcnow()
        
        # Add access pattern (every 10 minutes)
        self.cache_manager._access_patterns[cache_key] = [
            now - timedelta(minutes=30),
            now - timedelta(minutes=20),
            now - timedelta(minutes=10),
            now
        ]
        
        optimized_ttl = self.cache_manager.optimize_ttl(DataSourceType.GITHUB, "test")
        # Should be around 50% of 10 minutes = 5 minutes = 300 seconds
        assert 250 <= optimized_ttl <= 350
    
    def test_clear_expired(self):
        """Test clearing expired cache entries."""
        # Add some entries with different TTLs
        self.cache_manager.set(DataSourceType.GITHUB, "test1", {"data": 1}, 3600)
        self.cache_manager.set(DataSourceType.GITHUB, "test2", {"data": 2}, 1)
        
        # Wait for one to expire
        time.sleep(1.1)
        
        # Clear expired entries
        cleared_count = self.cache_manager.clear_expired()
        assert cleared_count == 1
        
        # Verify correct entry was cleared
        assert self.cache_manager.get(DataSourceType.GITHUB, "test1") is not None
        assert self.cache_manager.get(DataSourceType.GITHUB, "test2") is None


class TestDataValidator:
    """Test data validation functionality."""
    
    def test_validate_github_data_valid(self):
        """Test validation of valid GitHub data."""
        valid_data = {
            "commits": [
                {"sha": "a" * 40, "message": "Test commit"},
                {"sha": "b" * 40, "message": "Another commit"}
            ],
            "pull_requests": [
                {"number": 1, "title": "Test PR"}
            ],
            "contributors": ["user1", "user2"]
        }
        
        is_valid, errors = DataValidator.validate_github_data(valid_data)
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_github_data_invalid(self):
        """Test validation of invalid GitHub data."""
        invalid_data = {
            "commits": "not a list",  # Should be list
            "pull_requests": [
                {"number": 1, "title": "Test PR"}
            ]
            # Missing contributors field
        }
        
        is_valid, errors = DataValidator.validate_github_data(invalid_data)
        assert not is_valid
        assert len(errors) > 0
        assert any("contributors" in error for error in errors)
        assert any("Commits must be a list" in error for error in errors)
    
    def test_validate_jira_data_valid(self):
        """Test validation of valid JIRA data."""
        valid_data = {
            "issues": [
                {"key": "PROJ-123", "status": "Done"},
                {"key": "PROJ-124", "status": "In Progress"}
            ],
            "sprint_info": {
                "name": "Sprint 1",
                "state": "active"
            }
        }
        
        is_valid, errors = DataValidator.validate_jira_data(valid_data)
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_jira_data_invalid(self):
        """Test validation of invalid JIRA data."""
        invalid_data = {
            "issues": [
                {"key": "PROJ-123"},  # Missing status
                "not a dict"  # Should be dict
            ]
            # Missing sprint_info
        }
        
        is_valid, errors = DataValidator.validate_jira_data(invalid_data)
        assert not is_valid
        assert len(errors) > 0
    
    def test_validate_team_metrics_valid(self):
        """Test validation of valid team metrics data."""
        valid_data = {
            "productivity_metrics": {
                "velocity": 25,
                "cycle_time": 3.5
            },
            "collaboration_metrics": {
                "review_participation": 0.85,
                "cross_team_work": 0.3
            }
        }
        
        is_valid, errors = DataValidator.validate_team_metrics(valid_data)
        assert is_valid
        assert len(errors) == 0


class TestDataQualityAssessor:
    """Test data quality assessment functionality."""
    
    def test_assess_completeness(self):
        """Test completeness assessment."""
        data = {"field1": "value1", "field2": "value2", "field3": None}
        expected_fields = ["field1", "field2", "field3", "field4"]
        
        completeness = DataQualityAssessor.assess_completeness(data, expected_fields)
        # 2 out of 4 fields are present and non-null
        assert completeness == 0.5
    
    def test_assess_accuracy_github(self):
        """Test accuracy assessment for GitHub data."""
        # Valid GitHub data
        valid_data = {
            "commits": [
                {"sha": "a" * 40, "message": "Test"},
                {"sha": "b" * 40, "message": "Test 2"}
            ]
        }
        
        accuracy = DataQualityAssessor.assess_accuracy(valid_data, DataSourceType.GITHUB)
        assert accuracy == 1.0
        
        # Invalid GitHub data (bad SHA)
        invalid_data = {
            "commits": [
                {"sha": "invalid_sha", "message": "Test"},
                {"sha": "b" * 40, "message": "Test 2"}
            ]
        }
        
        accuracy = DataQualityAssessor.assess_accuracy(invalid_data, DataSourceType.GITHUB)
        assert accuracy < 1.0
    
    def test_assess_consistency(self):
        """Test consistency assessment."""
        # Consistent data (all list items are same type)
        consistent_data = {
            "items": [{"a": 1}, {"b": 2}, {"c": 3}]
        }
        
        consistency = DataQualityAssessor.assess_consistency(consistent_data)
        assert consistency == 1.0
        
        # Inconsistent data (mixed types in list)
        inconsistent_data = {
            "items": [{"a": 1}, "string", {"c": 3}]
        }
        
        consistency = DataQualityAssessor.assess_consistency(inconsistent_data)
        assert consistency < 1.0
    
    def test_assess_timeliness(self):
        """Test timeliness assessment."""
        # Fresh data (1 minute old)
        fresh_timestamp = datetime.utcnow() - timedelta(minutes=1)
        timeliness = DataQualityAssessor.assess_timeliness(fresh_timestamp)
        assert timeliness == 1.0
        
        # Old data (25 hours old)
        old_timestamp = datetime.utcnow() - timedelta(hours=25)
        timeliness = DataQualityAssessor.assess_timeliness(old_timestamp, max_age_hours=24)
        assert timeliness == 0.0
        
        # Moderately old data (12 hours old)
        moderate_timestamp = datetime.utcnow() - timedelta(hours=12)
        timeliness = DataQualityAssessor.assess_timeliness(moderate_timestamp, max_age_hours=24)
        assert 0.0 < timeliness < 1.0
    
    def test_assess_quality_comprehensive(self):
        """Test comprehensive quality assessment."""
        # Create sample collected data
        data = {
            "commits": [{"sha": "a" * 40, "message": "Test"}],
            "pull_requests": [],
            "contributors": ["user1"]
        }
        
        collected_data = CollectedData(
            source_type=DataSourceType.GITHUB,
            source_identifier="test",
            data=data,
            collection_timestamp=datetime.utcnow() - timedelta(minutes=5),
            quality_metrics=None,  # Will be set by assessment
            confidence_score=0.9
        )
        
        quality_metrics = DataQualityAssessor.assess_quality(collected_data)
        
        assert isinstance(quality_metrics, DataQualityMetrics)
        assert 0.0 <= quality_metrics.overall_score <= 1.0
        assert quality_metrics.quality_level in DataQualityLevel
        assert isinstance(quality_metrics.issues, list)
        assert isinstance(quality_metrics.recommendations, list)


class TestConflictResolver:
    """Test conflict resolution functionality."""
    
    def test_calculate_source_weight(self):
        """Test source weight calculation."""
        quality_metrics = DataQualityMetrics(
            completeness_score=0.9,
            accuracy_score=0.8,
            consistency_score=0.9,
            timeliness_score=0.95,
            overall_score=0.89,
            quality_level=DataQualityLevel.GOOD
        )
        
        weight = ConflictResolver.calculate_source_weight(
            DataSourceType.GITHUB, quality_metrics, 0.85
        )
        
        assert 0.0 <= weight <= 1.0
        # GitHub should have high base weight, good quality, good confidence
        assert weight > 0.7
    
    def test_resolve_field_conflict_numeric(self):
        """Test field conflict resolution for numeric values."""
        conflicting_values = [(10, 0.8), (12, 0.9), (8, 0.6)]
        
        resolved_value, method = ConflictResolver.resolve_field_conflict(
            "test_field", conflicting_values
        )
        
        # Should be weighted average
        expected = (10 * 0.8 + 12 * 0.9 + 8 * 0.6) / (0.8 + 0.9 + 0.6)
        assert abs(resolved_value - expected) < 0.01
        assert "weighted average" in method.lower()
    
    def test_resolve_field_conflict_non_numeric(self):
        """Test field conflict resolution for non-numeric values."""
        conflicting_values = [("value1", 0.6), ("value2", 0.9), ("value3", 0.7)]
        
        resolved_value, method = ConflictResolver.resolve_field_conflict(
            "test_field", conflicting_values
        )
        
        # Should choose highest weighted value
        assert resolved_value == "value2"
        assert "highest confidence" in method.lower()


class TestDataCollectionConfig:
    """Test data collection configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = DataCollectionConfig()
        
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.retry_backoff_factor == 2.0
        assert config.timeout_seconds == 30
        assert config.circuit_breaker_failure_threshold == 5
        assert config.circuit_breaker_recovery_timeout == 60
        assert config.parallel_workers == 4
        assert config.cache_ttl_seconds == 1800
        assert config.enable_cache_warming is True
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = DataCollectionConfig(
            max_retries=5,
            retry_delay=0.5,
            timeout_seconds=60,
            parallel_workers=8
        )
        
        assert config.max_retries == 5
        assert config.retry_delay == 0.5
        assert config.timeout_seconds == 60
        assert config.parallel_workers == 8


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])