#!/usr/bin/env python3
"""
Demonstration of the Intelligent Data Aggregator

This script demonstrates the key features of the IntelligentDataAggregator
including data collection, quality assessment, caching, and conflict resolution.
"""

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

# Import the core components
from devsync_ai.core.intelligent_data_aggregator import (
    IntelligentDataAggregator,
    DataCollectionConfig,
    DataSourceType,
    DataQualityLevel,
    PerformanceBenchmark
)


async def demo_basic_aggregation():
    """Demonstrate basic data aggregation functionality."""
    print("=== Basic Data Aggregation Demo ===")
    
    # Create aggregator with custom configuration
    config = DataCollectionConfig(
        max_retries=2,
        retry_delay=0.1,
        timeout_seconds=10,
        parallel_workers=3,
        cache_ttl_seconds=300  # 5 minutes
    )
    
    aggregator = IntelligentDataAggregator(config)
    
    # Register mock services for demonstration
    mock_github = AsyncMock()
    mock_jira = AsyncMock()
    
    aggregator.register_data_source(DataSourceType.GITHUB, "demo", mock_github)
    aggregator.register_data_source(DataSourceType.JIRA, "demo", mock_jira)
    
    # Mock the collection methods with realistic data
    async def mock_github_collect(*args, **kwargs):
        await asyncio.sleep(0.1)  # Simulate API delay
        return {
            "commits": [
                {"sha": "a" * 40, "message": "feat: Add new user authentication"},
                {"sha": "b" * 40, "message": "fix: Resolve login timeout issue"},
                {"sha": "c" * 40, "message": "docs: Update API documentation"}
            ],
            "pull_requests": [
                {"number": 1, "title": "Feature: User Dashboard", "state": "merged"},
                {"number": 2, "title": "Fix: Memory leak in processor", "state": "open"}
            ],
            "contributors": ["alice", "bob", "charlie"],
            "repository_health": {
                "code_quality": 0.87,
                "test_coverage": 0.82,
                "technical_debt": 0.15
            }
        }
    
    async def mock_jira_collect(*args, **kwargs):
        await asyncio.sleep(0.15)  # Simulate API delay
        return {
            "issues": [
                {"key": "PROJ-123", "status": "Done", "type": "Story", "points": 5},
                {"key": "PROJ-124", "status": "In Progress", "type": "Bug", "points": 3},
                {"key": "PROJ-125", "status": "To Do", "type": "Task", "points": 2}
            ],
            "sprint_info": {
                "name": "Sprint 15",
                "state": "active",
                "velocity": 28,
                "capacity": 35,
                "completion_rate": 0.8
            },
            "velocity_metrics": {
                "average_velocity": 25.5,
                "velocity_trend": "increasing",
                "completion_rate": 0.87
            }
        }
    
    # Patch the collection methods
    aggregator._collect_github_data = mock_github_collect
    aggregator._collect_jira_data = mock_jira_collect
    
    # Perform data aggregation
    team_id = "engineering_team"
    date_range = (
        datetime.utcnow() - timedelta(days=7),
        datetime.utcnow()
    )
    
    print(f"Collecting data for team: {team_id}")
    print(f"Date range: {date_range[0].strftime('%Y-%m-%d')} to {date_range[1].strftime('%Y-%m-%d')}")
    
    start_time = asyncio.get_event_loop().time()
    result = await aggregator.aggregate_data(team_id, date_range)
    collection_time = asyncio.get_event_loop().time() - start_time
    
    print(f"\nCollection completed in {collection_time:.3f} seconds")
    print(f"Data quality: {result.overall_quality.quality_level.value}")
    print(f"Overall quality score: {result.overall_quality.overall_score:.3f}")
    print(f"Data sources used: {', '.join(result.data_sources_used)}")
    print(f"Fallback data used: {result.fallback_data_used}")
    
    # Display collected data summary
    if result.github_data:
        print(f"\nGitHub Data:")
        print(f"  - Commits: {len(result.github_data['commits'])}")
        print(f"  - Pull Requests: {len(result.github_data['pull_requests'])}")
        print(f"  - Contributors: {len(result.github_data['contributors'])}")
        print(f"  - Code Quality: {result.github_data['repository_health']['code_quality']:.2f}")
    
    if result.jira_data:
        print(f"\nJIRA Data:")
        print(f"  - Issues: {len(result.jira_data['issues'])}")
        print(f"  - Sprint: {result.jira_data['sprint_info']['name']}")
        print(f"  - Velocity: {result.jira_data['sprint_info']['velocity']}")
        print(f"  - Completion Rate: {result.jira_data['sprint_info']['completion_rate']:.2%}")
    
    # Show quality metrics details
    print(f"\nQuality Metrics:")
    print(f"  - Completeness: {result.overall_quality.completeness_score:.3f}")
    print(f"  - Accuracy: {result.overall_quality.accuracy_score:.3f}")
    print(f"  - Consistency: {result.overall_quality.consistency_score:.3f}")
    print(f"  - Timeliness: {result.overall_quality.timeliness_score:.3f}")
    
    if result.overall_quality.issues:
        print(f"\nQuality Issues:")
        for issue in result.overall_quality.issues:
            print(f"  - {issue}")
    
    if result.overall_quality.recommendations:
        print(f"\nRecommendations:")
        for rec in result.overall_quality.recommendations:
            print(f"  - {rec}")
    
    await aggregator.cleanup()
    print("\n" + "="*50)


async def demo_caching_performance():
    """Demonstrate caching and performance optimization."""
    print("=== Caching Performance Demo ===")
    
    aggregator = IntelligentDataAggregator()
    
    # Register mock service
    mock_service = AsyncMock()
    aggregator.register_data_source(DataSourceType.CUSTOM, "cache_demo", mock_service)
    
    # Mock collection method with delay
    call_count = 0
    async def mock_collect_with_delay(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.2)  # Simulate slow API
        return {
            "data": f"response_{call_count}",
            "timestamp": datetime.utcnow().isoformat(),
            "call_number": call_count
        }
    
    async def mock_collect_single_source(*args):
        data = await mock_collect_with_delay()
        return type('CollectedData', (), {
            'source_type': DataSourceType.CUSTOM,
            'source_identifier': 'cache_demo',
            'data': data,
            'collection_timestamp': datetime.utcnow(),
            'quality_metrics': type('QualityMetrics', (), {
                'overall_score': 0.9,
                'quality_level': DataQualityLevel.EXCELLENT,
                'completeness_score': 0.9,
                'accuracy_score': 0.9,
                'consistency_score': 0.9,
                'timeliness_score': 0.9,
                'issues': [],
                'recommendations': []
            })(),
            'confidence_score': 0.9
        })()
    
    aggregator._collect_single_source = mock_collect_single_source
    
    team_id = "cache_test_team"
    date_range = (datetime.utcnow() - timedelta(days=1), datetime.utcnow())
    
    # First call (cold cache)
    print("First call (cold cache)...")
    start_time = asyncio.get_event_loop().time()
    result1 = await aggregator.aggregate_data(team_id, date_range)
    first_call_time = asyncio.get_event_loop().time() - start_time
    
    print(f"First call completed in {first_call_time:.3f} seconds")
    print(f"Call count: {call_count}")
    
    # Second call (warm cache)
    print("\nSecond call (warm cache)...")
    start_time = asyncio.get_event_loop().time()
    result2 = await aggregator.aggregate_data(team_id, date_range)
    second_call_time = asyncio.get_event_loop().time() - start_time
    
    print(f"Second call completed in {second_call_time:.3f} seconds")
    print(f"Call count: {call_count}")
    
    # Calculate cache efficiency
    if first_call_time > 0:
        speedup = first_call_time / second_call_time if second_call_time > 0 else float('inf')
        efficiency = (speedup - 1) / speedup if speedup > 1 else 0
        print(f"\nCache Performance:")
        print(f"  - Speedup: {speedup:.2f}x")
        print(f"  - Efficiency: {efficiency:.2%}")
    
    await aggregator.cleanup()
    print("\n" + "="*50)


async def demo_health_monitoring():
    """Demonstrate health monitoring and circuit breaker functionality."""
    print("=== Health Monitoring Demo ===")
    
    aggregator = IntelligentDataAggregator()
    
    # Register multiple mock services
    for i in range(3):
        mock_service = AsyncMock()
        aggregator.register_data_source(
            DataSourceType.CUSTOM, 
            f"service_{i}", 
            mock_service
        )
    
    # Get initial health status
    health_status = await aggregator.get_health_status()
    
    print("System Health Status:")
    print(f"  - Aggregator Status: {health_status['aggregator_status']}")
    print(f"  - Total Data Sources: {len(health_status['data_sources'])}")
    print(f"  - Cache Entries: {health_status['cache_stats']['total_entries']}")
    
    print("\nData Source Health:")
    for source_key, source_health in health_status['data_sources'].items():
        print(f"  - {source_key}:")
        print(f"    Status: {source_health['status']}")
        print(f"    Circuit Breaker: {source_health['circuit_breaker_state']}")
        print(f"    Failure Count: {source_health['failure_count']}")
    
    await aggregator.cleanup()
    print("\n" + "="*50)


async def demo_performance_benchmark():
    """Demonstrate performance benchmarking capabilities."""
    print("=== Performance Benchmark Demo ===")
    
    # Create aggregator with optimized config
    config = DataCollectionConfig(
        parallel_workers=4,
        cache_ttl_seconds=60,
        max_retries=1
    )
    
    aggregator = IntelligentDataAggregator(config)
    
    # Register mock service
    mock_service = AsyncMock()
    aggregator.register_data_source(DataSourceType.CUSTOM, "benchmark", mock_service)
    
    # Mock fast collection method
    async def mock_fast_collect(*args, **kwargs):
        await asyncio.sleep(0.01)  # Very fast response
        return {"benchmark": True, "timestamp": datetime.utcnow().isoformat()}
    
    # Patch aggregation method
    async def mock_aggregate_data(team_id, date_range):
        await asyncio.sleep(0.02)  # Simulate processing
        return type('AggregatedData', (), {
            'overall_quality': type('QualityMetrics', (), {
                'overall_score': 0.95,
                'quality_level': DataQualityLevel.EXCELLENT
            })(),
            'fallback_data_used': False
        })()
    
    aggregator.aggregate_data = mock_aggregate_data
    
    # Run benchmark with multiple teams
    team_ids = [f"team_{i}" for i in range(5)]
    date_range = (datetime.utcnow() - timedelta(days=7), datetime.utcnow())
    
    print(f"Running benchmark with {len(team_ids)} teams...")
    
    benchmark_results = await PerformanceBenchmark.benchmark_parallel_collection(
        aggregator, team_ids, date_range, iterations=3
    )
    
    print(f"\nBenchmark Results:")
    print(f"  - Teams: {benchmark_results['team_count']}")
    print(f"  - Iterations: {benchmark_results['iterations']}")
    print(f"  - Average Collection Time: {benchmark_results['avg_collection_time']:.3f}s")
    print(f"  - Average Success Rate: {benchmark_results['avg_success_rate']:.2%}")
    print(f"  - Average Quality Score: {benchmark_results['avg_quality_score']:.3f}")
    
    print(f"\nCollection Times per Iteration:")
    for i, time_taken in enumerate(benchmark_results['collection_times']):
        print(f"  - Iteration {i+1}: {time_taken:.3f}s")
    
    await aggregator.cleanup()
    print("\n" + "="*50)


async def main():
    """Run all demonstrations."""
    print("Intelligent Data Aggregator Demonstration")
    print("=" * 50)
    
    try:
        await demo_basic_aggregation()
        await demo_caching_performance()
        await demo_health_monitoring()
        await demo_performance_benchmark()
        
        print("\nAll demonstrations completed successfully!")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())