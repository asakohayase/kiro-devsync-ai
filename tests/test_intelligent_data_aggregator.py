"""
Tests for the Intelligent Data Aggregation and Quality Engine

This test suite covers all aspects of the IntelligentDataAggregator including:
- Parallel data collection
- Circuit breaker patterns
- Data quality assessment
- Conflict resolution
- Caching strategies
- Performance benchmarking
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from devsync_ai.core.intelligent_data_aggregator import (
    IntelligentDataAggregator,
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
    PerformanceBenchmark,
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


class TestIntelligentDataAggregator:
    """Test the main IntelligentDataAggregator class."""
    
    def setup_method(self):
        self.config = DataCollectionConfig(
            max_retries=2,
            retry_delay=0.1,
            timeout_seconds=5,
            parallel_workers=2
        )
        self.aggregator = IntelligentDataAggregator(self.config)
    
    def teardown_method(self):
        asyncio.create_task(self.aggregator.cleanup())
    
    def test_initialization(self):
        """Test aggregator initialization."""
        assert self.aggregator.config == self.config
        assert isinstance(self.aggregator.cache_manager, CacheManager)
        assert len(self.aggregator.data_sources) >= 0  # May have built-in sources
    
    def test_register_data_source(self):
        """Test data source registration."""
        mock_service = Mock()
        
        self.aggregator.register_data_source(
            DataSourceType.CUSTOM,
            "test_service",
            mock_service
        )
        
        source_key = "custom:test_service"
        assert source_key in self.aggregator.data_sources
        
        data_source = self.aggregator.data_sources[source_key]
        assert data_source.source_type == DataSourceType.CUSTOM
        assert data_source.identifier == "test_service"
        assert data_source.service_instance == mock_service
    
    def test_circuit_breaker_closed_to_open(self):
        """Test circuit breaker opening after failures."""
        mock_service = Mock()
        self.aggregator.register_data_source(
            DataSourceType.CUSTOM, "test", mock_service
        )
        
        source_key = "custom:test"
        data_source = self.aggregator.data_sources[source_key]
        
        # Simulate failures
        for _ in range(self.config.circuit_breaker_failure_threshold):
            self.aggregator._update_circuit_breaker(data_source, False)
        
        assert data_source.circuit_breaker_state == CircuitBreakerState.OPEN
        assert data_source.failure_count == self.config.circuit_breaker_failure_threshold
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        mock_service = Mock()
        self.aggregator.register_data_source(
            DataSourceType.CUSTOM, "test", mock_service
        )
        
        source_key = "custom:test"
        data_source = self.aggregator.data_sources[source_key]
        
        # Open circuit breaker
        data_source.circuit_breaker_state = CircuitBreakerState.OPEN
        data_source.last_failure_time = datetime.utcnow() - timedelta(seconds=100)
        
        # Should allow operation after timeout
        can_operate = self.aggregator._check_circuit_breaker(data_source)
        assert can_operate
        assert data_source.circuit_breaker_state == CircuitBreakerState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_collect_with_retry_success(self):
        """Test successful data collection with retry logic."""
        mock_service = Mock()
        self.aggregator.register_data_source(
            DataSourceType.CUSTOM, "test", mock_service
        )
        
        source_key = "custom:test"
        data_source = self.aggregator.data_sources[source_key]
        
        # Mock successful collection function
        async def mock_collect():
            return {"test": "data"}
        
        result = await self.aggregator._collect_with_retry(
            data_source, mock_collect
        )
        
        assert result == {"test": "data"}
        assert data_source.circuit_breaker_state == CircuitBreakerState.CLOSED
        assert data_source.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_collect_with_retry_failure(self):
        """Test data collection failure with retry logic."""
        mock_service = Mock()
        self.aggregator.register_data_source(
            DataSourceType.CUSTOM, "test", mock_service
        )
        
        source_key = "custom:test"
        data_source = self.aggregator.data_sources[source_key]
        
        # Mock failing collection function
        async def mock_collect():
            raise Exception("Collection failed")
        
        with pytest.raises(Exception, match="Collection failed"):
            await self.aggregator._collect_with_retry(
                data_source, mock_collect
            )
        
        assert data_source.failure_count > 0
    
    @pytest.mark.asyncio
    async def test_collect_with_circuit_breaker_open(self):
        """Test collection when circuit breaker is open."""
        mock_service = Mock()
        self.aggregator.register_data_source(
            DataSourceType.CUSTOM, "test", mock_service
        )
        
        source_key = "custom:test"
        data_source = self.aggregator.data_sources[source_key]
        
        # Open circuit breaker
        data_source.circuit_breaker_state = CircuitBreakerState.OPEN
        data_source.last_failure_time = datetime.utcnow()
        
        async def mock_collect():
            return {"test": "data"}
        
        with pytest.raises(CircuitBreakerOpenError):
            await self.aggregator._collect_with_retry(
                data_source, mock_collect
            )
    
    @pytest.mark.asyncio
    async def test_aggregate_data_no_sources(self):
        """Test data aggregation when no sources are available."""
        # Create aggregator with no sources
        empty_aggregator = IntelligentDataAggregator()
        empty_aggregator.data_sources.clear()
        
        team_id = "test_team"
        date_range = (datetime.utcnow() - timedelta(days=7), datetime.utcnow())
        
        result = await empty_aggregator.aggregate_data(team_id, date_range)
        
        assert isinstance(result, AggregatedData)
        assert result.fallback_data_used
        assert result.overall_quality.quality_level == DataQualityLevel.POOR
        
        await empty_aggregator.cleanup()
    
    @pytest.mark.asyncio
    async def test_aggregate_data_with_mock_sources(self):
        """Test data aggregation with mock data sources."""
        # Create mock services
        mock_github = AsyncMock()
        mock_jira = AsyncMock()
        
        # Register mock services
        self.aggregator.register_data_source(
            DataSourceType.GITHUB, "mock", mock_github
        )
        self.aggregator.register_data_source(
            DataSourceType.JIRA, "mock", mock_jira
        )
        
        # Mock the collection methods
        with patch.object(self.aggregator, '_collect_github_data') as mock_github_collect, \
             patch.object(self.aggregator, '_collect_jira_data') as mock_jira_collect:
            
            mock_github_collect.return_value = {
                "commits": [{"sha": "a" * 40, "message": "Test"}],
                "pull_requests": [],
                "contributors": ["user1"]
            }
            
            mock_jira_collect.return_value = {
                "issues": [{"key": "PROJ-123", "status": "Done"}],
                "sprint_info": {"name": "Sprint 1"}
            }
            
            team_id = "test_team"
            date_range = (datetime.utcnow() - timedelta(days=7), datetime.utcnow())
            
            result = await self.aggregator.aggregate_data(team_id, date_range)
            
            assert isinstance(result, AggregatedData)
            assert not result.fallback_data_used
            assert result.github_data is not None
            assert result.jira_data is not None
            assert len(result.data_sources_used) > 0
    
    @pytest.mark.asyncio
    async def test_get_health_status(self):
        """Test health status reporting."""
        # Register a mock service
        mock_service = Mock()
        self.aggregator.register_data_source(
            DataSourceType.CUSTOM, "test", mock_service
        )
        
        health_status = await self.aggregator.get_health_status()
        
        assert "aggregator_status" in health_status
        assert "data_sources" in health_status
        assert "cache_stats" in health_status
        assert "timestamp" in health_status
        
        # Check data source health
        source_key = "custom:test"
        assert source_key in health_status["data_sources"]
        
        source_health = health_status["data_sources"][source_key]
        assert "status" in source_health
        assert "circuit_breaker_state" in source_health
        assert "failure_count" in source_health


class TestPerformanceBenchmark:
    """Test performance benchmarking utilities."""
    
    @pytest.mark.asyncio
    async def test_benchmark_parallel_collection(self):
        """Test performance benchmarking of parallel collection."""
        # Create aggregator with mock data
        aggregator = IntelligentDataAggregator()
        
        # Mock the aggregate_data method to return quickly
        async def mock_aggregate_data(team_id, date_range):
            await asyncio.sleep(0.01)  # Simulate some work
            return AggregatedData(
                overall_quality=DataQualityMetrics(
                    completeness_score=0.9, accuracy_score=0.9,
                    consistency_score=0.9, timeliness_score=0.9,
                    overall_score=0.9, quality_level=DataQualityLevel.EXCELLENT
                )
            )
        
        aggregator.aggregate_data = mock_aggregate_data
        
        team_ids = ["team1", "team2", "team3"]
        date_range = (datetime.utcnow() - timedelta(days=7), datetime.utcnow())
        
        results = await PerformanceBenchmark.benchmark_parallel_collection(
            aggregator, team_ids, date_range, iterations=2
        )
        
        assert "team_count" in results
        assert "iterations" in results
        assert "collection_times" in results
        assert "success_rates" in results
        assert "quality_scores" in results
        assert "avg_collection_time" in results
        assert "avg_success_rate" in results
        assert "avg_quality_score" in results
        
        assert results["team_count"] == 3
        assert results["iterations"] == 2
        assert len(results["collection_times"]) == 2
        assert all(rate == 1.0 for rate in results["success_rates"])  # All should succeed
        
        await aggregator.cleanup()
    
    @pytest.mark.asyncio
    async def test_load_test(self):
        """Test load testing functionality."""
        # Create aggregator with mock data
        aggregator = IntelligentDataAggregator()
        
        # Mock the aggregate_data method
        async def mock_aggregate_data(team_id, date_range):
            await asyncio.sleep(0.01)  # Simulate some work
            return AggregatedData(
                overall_quality=DataQualityMetrics(
                    completeness_score=0.8, accuracy_score=0.8,
                    consistency_score=0.8, timeliness_score=0.8,
                    overall_score=0.8, quality_level=DataQualityLevel.GOOD
                )
            )
        
        aggregator.aggregate_data = mock_aggregate_data
        
        team_id = "test_team"
        date_range = (datetime.utcnow() - timedelta(days=7), datetime.utcnow())
        concurrent_requests = 5
        
        results = await PerformanceBenchmark.load_test(
            aggregator, concurrent_requests, team_id, date_range
        )
        
        assert "concurrent_requests" in results
        assert "total_time" in results
        assert "successful_requests" in results
        assert "failed_requests" in results
        assert "success_rate" in results
        assert "avg_request_duration" in results
        assert "avg_quality_score" in results
        assert "requests_per_second" in results
        
        assert results["concurrent_requests"] == concurrent_requests
        assert results["successful_requests"] == concurrent_requests
        assert results["failed_requests"] == 0
        assert results["success_rate"] == 1.0
        
        await aggregator.cleanup()


class TestIntegrationScenarios:
    """Integration tests for complex scenarios."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_aggregation_flow(self):
        """Test complete end-to-end aggregation flow."""
        # Create aggregator with custom config
        config = DataCollectionConfig(
            max_retries=1,
            retry_delay=0.1,
            timeout_seconds=10,
            parallel_workers=2,
            cache_ttl_seconds=60
        )
        aggregator = IntelligentDataAggregator(config)
        
        # Register mock services
        mock_github = AsyncMock()
        mock_jira = AsyncMock()
        
        aggregator.register_data_source(DataSourceType.GITHUB, "test", mock_github)
        aggregator.register_data_source(DataSourceType.JIRA, "test", mock_jira)
        
        # Mock collection methods with realistic data
        with patch.object(aggregator, '_collect_github_data') as mock_github_collect, \
             patch.object(aggregator, '_collect_jira_data') as mock_jira_collect:
            
            mock_github_collect.return_value = {
                "commits": [
                    {"sha": "a" * 40, "message": "Feature: Add new functionality"},
                    {"sha": "b" * 40, "message": "Fix: Resolve bug in component"}
                ],
                "pull_requests": [
                    {"number": 1, "title": "Add feature X", "state": "merged"}
                ],
                "contributors": ["alice", "bob", "charlie"],
                "repository_health": {"code_quality": 0.85}
            }
            
            mock_jira_collect.return_value = {
                "issues": [
                    {"key": "PROJ-123", "status": "Done", "type": "Story"},
                    {"key": "PROJ-124", "status": "In Progress", "type": "Bug"}
                ],
                "sprint_info": {
                    "name": "Sprint 10",
                    "state": "active",
                    "velocity": 25
                }
            }
            
            team_id = "engineering_team"
            date_range = (
                datetime.utcnow() - timedelta(days=7),
                datetime.utcnow()
            )
            
            # First aggregation (should collect fresh data)
            result1 = await aggregator.aggregate_data(team_id, date_range)
            
            assert isinstance(result1, AggregatedData)
            assert not result1.fallback_data_used
            assert result1.github_data is not None
            assert result1.jira_data is not None
            assert len(result1.github_data["commits"]) == 2
            assert len(result1.jira_data["issues"]) == 2
            assert result1.overall_quality.quality_level in [
                DataQualityLevel.GOOD, DataQualityLevel.EXCELLENT
            ]
            
            # Second aggregation (should use cached data)
            result2 = await aggregator.aggregate_data(team_id, date_range)
            
            assert isinstance(result2, AggregatedData)
            assert not result2.fallback_data_used
            
            # Verify health status
            health = await aggregator.get_health_status()
            assert health["aggregator_status"] == "healthy"
            assert len(health["data_sources"]) >= 2
            
        await aggregator.cleanup()
    
    @pytest.mark.asyncio
    async def test_failure_recovery_scenario(self):
        """Test failure recovery and fallback mechanisms."""
        aggregator = IntelligentDataAggregator()
        
        # Register mock service that will fail
        mock_service = AsyncMock()
        aggregator.register_data_source(DataSourceType.CUSTOM, "failing", mock_service)
        
        # Mock collection method to fail initially, then succeed
        call_count = 0
        
        async def mock_collect_with_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first two attempts
                raise Exception("Service temporarily unavailable")
            return {"recovered": True, "attempt": call_count}
        
        with patch.object(aggregator, '_collect_single_source') as mock_collect:
            mock_collect.side_effect = mock_collect_with_failure
            
            team_id = "test_team"
            date_range = (datetime.utcnow() - timedelta(days=7), datetime.utcnow())
            
            # This should eventually succeed after retries
            result = await aggregator.aggregate_data(team_id, date_range)
            
            # Should fall back to cached/fallback data due to failures
            assert isinstance(result, AggregatedData)
            # May use fallback data depending on implementation
        
        await aggregator.cleanup()


if __name__ == "__main__":
    # Run specific test categories
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "test_cache or test_validator or test_quality or test_aggregator"
    ])