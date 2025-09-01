"""
Unit tests for the Intelligent Data Aggregation and Quality Engine

This test suite focuses on unit testing individual components without
requiring the full service stack or external dependencies.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Import only the core components we need to test
from devsync_ai.core.intelligent_data_aggregator import (
    DataCollectionConfig,
    DataSource,
    DataSourceType,
    CircuitBreakerState,
    DataQualityLevel,
    DataQualityMetrics,
    CollectedData,
    AggregatedData,
    CacheManager,
    DataValidator,
    DataQualityAssessor,
    ConflictResolver,
    DataCollectionError,
    CircuitBreakerOpenError
)


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
        assert any("commits" in error for error in errors)
    
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
    
    def test_resolve_conflicts_no_conflicts(self):
        """Test conflict resolution when no conflicts exist."""
        # Single data source
        collected_data = CollectedData(
            source_type=DataSourceType.GITHUB,
            source_identifier="test",
            data={"field1": "value1"},
            collection_timestamp=datetime.utcnow(),
            quality_metrics=DataQualityMetrics(
                completeness_score=1.0, accuracy_score=1.0,
                consistency_score=1.0, timeliness_score=1.0,
                overall_score=1.0, quality_level=DataQualityLevel.EXCELLENT
            ),
            confidence_score=0.9
        )
        
        resolved_data, conflicts = ConflictResolver.resolve_conflicts([collected_data])
        
        assert resolved_data == {"github": {"field1": "value1"}}
        assert len(conflicts) == 0
    
    def test_resolve_conflicts_different_sources(self):
        """Test conflict resolution across different source types."""
        github_data = CollectedData(
            source_type=DataSourceType.GITHUB,
            source_identifier="test",
            data={"commits": 10},
            collection_timestamp=datetime.utcnow(),
            quality_metrics=DataQualityMetrics(
                completeness_score=1.0, accuracy_score=1.0,
                consistency_score=1.0, timeliness_score=1.0,
                overall_score=1.0, quality_level=DataQualityLevel.EXCELLENT
            ),
            confidence_score=0.9
        )
        
        jira_data = CollectedData(
            source_type=DataSourceType.JIRA,
            source_identifier="test",
            data={"issues": 5},
            collection_timestamp=datetime.utcnow(),
            quality_metrics=DataQualityMetrics(
                completeness_score=1.0, accuracy_score=1.0,
                consistency_score=1.0, timeliness_score=1.0,
                overall_score=1.0, quality_level=DataQualityLevel.EXCELLENT
            ),
            confidence_score=0.8
        )
        
        resolved_data, conflicts = ConflictResolver.resolve_conflicts([github_data, jira_data])
        
        # Should have both source types with no conflicts
        assert "github" in resolved_data
        assert "jira" in resolved_data
        assert resolved_data["github"]["commits"] == 10
        assert resolved_data["jira"]["issues"] == 5
        assert len(conflicts) == 0


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


class TestDataSource:
    """Test data source configuration."""
    
    def test_data_source_creation(self):
        """Test data source creation with default values."""
        mock_service = Mock()
        
        data_source = DataSource(
            source_type=DataSourceType.GITHUB,
            identifier="test_github",
            service_instance=mock_service
        )
        
        assert data_source.source_type == DataSourceType.GITHUB
        assert data_source.identifier == "test_github"
        assert data_source.service_instance == mock_service
        assert data_source.circuit_breaker_state == CircuitBreakerState.CLOSED
        assert data_source.failure_count == 0
        assert data_source.last_failure_time is None
        assert data_source.last_success_time is None
    
    def test_data_source_with_custom_config(self):
        """Test data source with custom configuration."""
        mock_service = Mock()
        custom_config = DataCollectionConfig(max_retries=10)
        
        data_source = DataSource(
            source_type=DataSourceType.JIRA,
            identifier="test_jira",
            service_instance=mock_service,
            config=custom_config
        )
        
        assert data_source.config.max_retries == 10


class TestCollectedData:
    """Test collected data structure."""
    
    def test_collected_data_creation(self):
        """Test collected data creation."""
        quality_metrics = DataQualityMetrics(
            completeness_score=0.9,
            accuracy_score=0.8,
            consistency_score=0.9,
            timeliness_score=0.95,
            overall_score=0.89,
            quality_level=DataQualityLevel.GOOD
        )
        
        collected_data = CollectedData(
            source_type=DataSourceType.GITHUB,
            source_identifier="test",
            data={"test": "data"},
            collection_timestamp=datetime.utcnow(),
            quality_metrics=quality_metrics,
            confidence_score=0.85
        )
        
        assert collected_data.source_type == DataSourceType.GITHUB
        assert collected_data.source_identifier == "test"
        assert collected_data.data == {"test": "data"}
        assert collected_data.quality_metrics == quality_metrics
        assert collected_data.confidence_score == 0.85
        assert collected_data.schema_version == "1.0"


class TestAggregatedData:
    """Test aggregated data structure."""
    
    def test_aggregated_data_creation(self):
        """Test aggregated data creation with defaults."""
        aggregated_data = AggregatedData()
        
        assert aggregated_data.github_data is None
        assert aggregated_data.jira_data is None
        assert aggregated_data.team_metrics is None
        assert aggregated_data.calendar_data is None
        assert aggregated_data.custom_data == {}
        assert aggregated_data.overall_quality is None
        assert isinstance(aggregated_data.aggregation_timestamp, datetime)
        assert aggregated_data.data_sources_used == []
        assert aggregated_data.conflicts_resolved == []
        assert aggregated_data.fallback_data_used is False
    
    def test_aggregated_data_with_data(self):
        """Test aggregated data with actual data."""
        quality_metrics = DataQualityMetrics(
            completeness_score=0.9,
            accuracy_score=0.8,
            consistency_score=0.9,
            timeliness_score=0.95,
            overall_score=0.89,
            quality_level=DataQualityLevel.GOOD
        )
        
        aggregated_data = AggregatedData(
            github_data={"commits": 10},
            jira_data={"issues": 5},
            overall_quality=quality_metrics,
            data_sources_used=["github", "jira"],
            conflicts_resolved=["Field 'count': Weighted average of 2 sources"]
        )
        
        assert aggregated_data.github_data == {"commits": 10}
        assert aggregated_data.jira_data == {"issues": 5}
        assert aggregated_data.overall_quality == quality_metrics
        assert "github" in aggregated_data.data_sources_used
        assert "jira" in aggregated_data.data_sources_used
        assert len(aggregated_data.conflicts_resolved) == 1


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])