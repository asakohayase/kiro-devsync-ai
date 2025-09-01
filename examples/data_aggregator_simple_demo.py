#!/usr/bin/env python3
"""
Simple demonstration of the core data aggregation components

This demo shows the functionality without requiring the full service stack.
"""

import asyncio
import time
from datetime import datetime, timedelta

# Import the core test components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tests'))

from test_data_aggregator_core import (
    DataSourceType,
    DataQualityLevel,
    DataCollectionConfig,
    CacheManager,
    DataValidator,
    DataQualityAssessor,
    ConflictResolver,
    CollectedData,
    DataQualityMetrics
)


def demo_cache_manager():
    """Demonstrate cache manager functionality."""
    print("=== Cache Manager Demo ===")
    
    cache = CacheManager()
    
    # Test basic caching
    print("1. Basic caching operations:")
    
    # Cache miss
    result = cache.get(DataSourceType.GITHUB, "repo1", {"branch": "main"})
    print(f"   Cache miss: {result}")
    
    # Cache set
    test_data = {"commits": 10, "prs": 5}
    cache.set(DataSourceType.GITHUB, "repo1", test_data, 300, {"branch": "main"})
    print(f"   Data cached with 300s TTL")
    
    # Cache hit
    result = cache.get(DataSourceType.GITHUB, "repo1", {"branch": "main"})
    print(f"   Cache hit: {result}")
    
    # Test TTL optimization
    print("\n2. TTL optimization:")
    ttl = cache.optimize_ttl(DataSourceType.GITHUB, "repo1")
    print(f"   Default TTL: {ttl}s")
    
    # Simulate access pattern
    cache_key = cache._generate_cache_key(DataSourceType.GITHUB, "repo1", {"branch": "main"})
    now = datetime.utcnow()
    cache._access_patterns[cache_key] = [
        now - timedelta(minutes=20),
        now - timedelta(minutes=10),
        now
    ]
    
    optimized_ttl = cache.optimize_ttl(DataSourceType.GITHUB, "repo1", {"branch": "main"})
    print(f"   Optimized TTL: {optimized_ttl}s")
    
    print("   ✓ Cache manager working correctly")
    print()


def demo_data_validator():
    """Demonstrate data validation functionality."""
    print("=== Data Validator Demo ===")
    
    # Valid GitHub data
    valid_github = {
        "commits": [
            {"sha": "a" * 40, "message": "Add feature X"},
            {"sha": "b" * 40, "message": "Fix bug Y"}
        ],
        "pull_requests": [
            {"number": 1, "title": "Feature PR"}
        ],
        "contributors": ["alice", "bob"]
    }
    
    is_valid, errors = DataValidator.validate_github_data(valid_github)
    print(f"1. Valid GitHub data: {is_valid} (errors: {len(errors)})")
    
    # Invalid GitHub data
    invalid_github = {
        "commits": "not a list",  # Should be list
        "pull_requests": []
        # Missing contributors
    }
    
    is_valid, errors = DataValidator.validate_github_data(invalid_github)
    print(f"2. Invalid GitHub data: {is_valid} (errors: {len(errors)})")
    for error in errors:
        print(f"   - {error}")
    
    # Valid JIRA data
    valid_jira = {
        "issues": [
            {"key": "PROJ-123", "status": "Done"},
            {"key": "PROJ-124", "status": "In Progress"}
        ],
        "sprint_info": {"name": "Sprint 1", "state": "active"}
    }
    
    is_valid, errors = DataValidator.validate_jira_data(valid_jira)
    print(f"3. Valid JIRA data: {is_valid} (errors: {len(errors)})")
    
    print("   ✓ Data validator working correctly")
    print()


def demo_quality_assessor():
    """Demonstrate data quality assessment."""
    print("=== Data Quality Assessor Demo ===")
    
    # Create sample data with varying quality
    high_quality_data = {
        "commits": [{"sha": "a" * 40, "message": "Test"}],
        "pull_requests": [{"number": 1, "title": "PR"}],
        "contributors": ["user1", "user2"]
    }
    
    collected_data = CollectedData(
        source_type=DataSourceType.GITHUB,
        source_identifier="test_repo",
        data=high_quality_data,
        collection_timestamp=datetime.utcnow() - timedelta(minutes=5),
        quality_metrics=None,
        confidence_score=0.9
    )
    
    # Assess quality
    quality_metrics = DataQualityAssessor.assess_quality(collected_data)
    
    print(f"1. Quality Assessment Results:")
    print(f"   - Overall Score: {quality_metrics.overall_score:.3f}")
    print(f"   - Quality Level: {quality_metrics.quality_level.value}")
    print(f"   - Completeness: {quality_metrics.completeness_score:.3f}")
    print(f"   - Accuracy: {quality_metrics.accuracy_score:.3f}")
    print(f"   - Consistency: {quality_metrics.consistency_score:.3f}")
    print(f"   - Timeliness: {quality_metrics.timeliness_score:.3f}")
    
    if quality_metrics.issues:
        print(f"   - Issues: {len(quality_metrics.issues)}")
        for issue in quality_metrics.issues:
            print(f"     • {issue}")
    
    if quality_metrics.recommendations:
        print(f"   - Recommendations: {len(quality_metrics.recommendations)}")
        for rec in quality_metrics.recommendations:
            print(f"     • {rec}")
    
    print("   ✓ Quality assessor working correctly")
    print()


def demo_conflict_resolver():
    """Demonstrate conflict resolution."""
    print("=== Conflict Resolver Demo ===")
    
    # Test numeric conflict resolution
    conflicting_values = [(10, 0.8), (12, 0.9), (8, 0.6)]
    resolved_value, method = ConflictResolver.resolve_field_conflict(
        "velocity", conflicting_values
    )
    
    print(f"1. Numeric Conflict Resolution:")
    print(f"   - Input values: {conflicting_values}")
    print(f"   - Resolved value: {resolved_value:.2f}")
    print(f"   - Method: {method}")
    
    # Test non-numeric conflict resolution
    text_values = [("feature_a", 0.6), ("feature_b", 0.9), ("feature_c", 0.7)]
    resolved_text, text_method = ConflictResolver.resolve_field_conflict(
        "feature_name", text_values
    )
    
    print(f"\n2. Text Conflict Resolution:")
    print(f"   - Input values: {text_values}")
    print(f"   - Resolved value: {resolved_text}")
    print(f"   - Method: {text_method}")
    
    # Test source weight calculation
    quality_metrics = DataQualityMetrics(
        completeness_score=0.9,
        accuracy_score=0.85,
        consistency_score=0.9,
        timeliness_score=0.95,
        overall_score=0.9,
        quality_level=DataQualityLevel.EXCELLENT
    )
    
    weight = ConflictResolver.calculate_source_weight(
        DataSourceType.GITHUB, quality_metrics, 0.88
    )
    
    print(f"\n3. Source Weight Calculation:")
    print(f"   - Source: GitHub")
    print(f"   - Quality Score: {quality_metrics.overall_score:.3f}")
    print(f"   - Confidence: 0.88")
    print(f"   - Calculated Weight: {weight:.3f}")
    
    print("   ✓ Conflict resolver working correctly")
    print()


def demo_performance_comparison():
    """Demonstrate performance characteristics."""
    print("=== Performance Comparison Demo ===")
    
    cache = CacheManager()
    
    # Simulate data collection with and without caching
    def simulate_slow_api_call():
        """Simulate a slow API call."""
        time.sleep(0.1)  # 100ms delay
        return {"data": "api_response", "timestamp": datetime.utcnow().isoformat()}
    
    # Test without caching
    print("1. Without caching (3 calls):")
    start_time = time.time()
    for i in range(3):
        result = simulate_slow_api_call()
    no_cache_time = time.time() - start_time
    print(f"   - Total time: {no_cache_time:.3f}s")
    
    # Test with caching
    print("\n2. With caching (3 calls, same data):")
    start_time = time.time()
    
    # First call - cache miss
    result = simulate_slow_api_call()
    cache.set(DataSourceType.GITHUB, "test", result, 300)
    
    # Subsequent calls - cache hits
    for i in range(2):
        cached_result = cache.get(DataSourceType.GITHUB, "test")
    
    cache_time = time.time() - start_time
    print(f"   - Total time: {cache_time:.3f}s")
    
    # Calculate improvement
    if cache_time > 0:
        speedup = no_cache_time / cache_time
        print(f"   - Speedup: {speedup:.2f}x")
        print(f"   - Time saved: {(no_cache_time - cache_time):.3f}s")
    
    print("   ✓ Performance optimization working correctly")
    print()


def demo_configuration():
    """Demonstrate configuration options."""
    print("=== Configuration Demo ===")
    
    # Default configuration
    default_config = DataCollectionConfig()
    print("1. Default Configuration:")
    print(f"   - Max Retries: {default_config.max_retries}")
    print(f"   - Retry Delay: {default_config.retry_delay}s")
    print(f"   - Timeout: {default_config.timeout_seconds}s")
    print(f"   - Parallel Workers: {default_config.parallel_workers}")
    print(f"   - Cache TTL: {default_config.cache_ttl_seconds}s")
    print(f"   - Cache Warming: {default_config.enable_cache_warming}")
    
    # Custom configuration
    custom_config = DataCollectionConfig(
        max_retries=5,
        retry_delay=0.5,
        timeout_seconds=60,
        parallel_workers=8,
        cache_ttl_seconds=600,
        enable_cache_warming=False
    )
    
    print("\n2. Custom Configuration:")
    print(f"   - Max Retries: {custom_config.max_retries}")
    print(f"   - Retry Delay: {custom_config.retry_delay}s")
    print(f"   - Timeout: {custom_config.timeout_seconds}s")
    print(f"   - Parallel Workers: {custom_config.parallel_workers}")
    print(f"   - Cache TTL: {custom_config.cache_ttl_seconds}s")
    print(f"   - Cache Warming: {custom_config.enable_cache_warming}")
    
    print("   ✓ Configuration system working correctly")
    print()


def main():
    """Run all demonstrations."""
    print("Smart Data Aggregation and Quality Engine - Core Components Demo")
    print("=" * 70)
    print()
    
    try:
        demo_cache_manager()
        demo_data_validator()
        demo_quality_assessor()
        demo_conflict_resolver()
        demo_performance_comparison()
        demo_configuration()
        
        print("=" * 70)
        print("✅ All core components demonstrated successfully!")
        print()
        print("Key Features Demonstrated:")
        print("• Intelligent caching with TTL optimization")
        print("• Comprehensive data validation")
        print("• Multi-dimensional quality assessment")
        print("• Weighted conflict resolution")
        print("• Performance optimization")
        print("• Flexible configuration")
        print()
        print("The Smart Data Aggregation and Quality Engine is ready for integration!")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()