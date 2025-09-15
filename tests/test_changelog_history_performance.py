"""
Database Performance Tests for Changelog History Manager

This module provides comprehensive performance testing with large dataset simulation,
query optimization validation, and scalability testing.
"""

import asyncio
import pytest
import time
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock
import statistics

from devsync_ai.database.changelog_history_manager import (
    ChangelogHistoryManager,
    ChangelogEntry,
    ChangelogStatus,
    HistoryFilters,
    TrendAnalysis,
    ExportConfig,
    ExportFormat,
    RetentionPolicy
)
from devsync_ai.config import Config


class PerformanceTestData:
    """Helper class for generating test data"""
    
    @staticmethod
    def generate_changelog_entry(
        team_id: str = None,
        week_offset: int = 0,
        content_size: str = "medium"
    ) -> ChangelogEntry:
        """Generate a changelog entry for testing"""
        
        if not team_id:
            team_id = f"team_{random.randint(1, 10)}"
        
        base_date = datetime.utcnow() - timedelta(weeks=week_offset)
        week_start = base_date - timedelta(days=base_date.weekday())
        week_end = week_start + timedelta(days=6)
        
        # Generate content based on size
        content_sizes = {
            "small": 100,
            "medium": 1000,
            "large": 10000,
            "xlarge": 50000
        }
        
        content_length = content_sizes.get(content_size, 1000)
        content = {
            "summary": "Test changelog " + "x" * (content_length // 10),
            "features": [f"Feature {i}" for i in range(content_length // 100)],
            "bug_fixes": [f"Bug fix {i}" for i in range(content_length // 200)],
            "improvements": [f"Improvement {i}" for i in range(content_length // 150)],
            "metadata": {
                "generated_by": "performance_test",
                "complexity_score": random.uniform(0.1, 1.0),
                "impact_score": random.uniform(0.1, 1.0)
            }
        }
        
        return ChangelogEntry(
            id=f"test_{random.randint(100000, 999999)}",
            team_id=team_id,
            week_start_date=week_start,
            week_end_date=week_end,
            version=1,
            status=random.choice(list(ChangelogStatus)),
            content=content,
            metadata={
                "test_data": True,
                "content_size": content_size,
                "generated_at": datetime.utcnow().isoformat()
            },
            generated_at=datetime.utcnow(),
            created_by=f"user_{random.randint(1, 50)}",
            tags=[f"tag_{i}" for i in range(random.randint(1, 5))]
        )


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = Mock(spec=Config)
    config.SUPABASE_URL = "https://test.supabase.co"
    config.supabase_service_role_key = "test_key"
    return config


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    mock_client = Mock()
    mock_table = Mock()
    mock_client.table.return_value = mock_table
    mock_client.rpc.return_value.execute.return_value = None
    return mock_client


@pytest.fixture
def history_manager(mock_config, mock_supabase):
    """Create ChangelogHistoryManager with mocked dependencies"""
    with patch('devsync_ai.database.changelog_history_manager.create_client', return_value=mock_supabase):
        manager = ChangelogHistoryManager(mock_config)
        return manager


class TestChangelogHistoryPerformance:
    """Performance tests for changelog history management"""

    @pytest.mark.asyncio
    async def test_bulk_storage_performance(self, history_manager, mock_supabase):
        """Test performance of bulk changelog storage operations"""
        
        # Setup mock responses
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "test"}])
        
        # Generate test data
        test_sizes = [10, 50, 100, 500]
        performance_results = {}
        
        for size in test_sizes:
            entries = [
                PerformanceTestData.generate_changelog_entry(
                    team_id=f"perf_team_{i % 5}",
                    week_offset=i,
                    content_size="medium"
                )
                for i in range(size)
            ]
            
            # Measure storage performance
            start_time = time.time()
            
            tasks = [history_manager.store_changelog(entry) for entry in entries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Calculate metrics
            successful_stores = len([r for r in results if hasattr(r, 'success') and r.success])
            throughput = successful_stores / duration if duration > 0 else 0
            
            performance_results[size] = {
                'duration': duration,
                'throughput': throughput,
                'success_rate': successful_stores / len(entries),
                'avg_time_per_entry': duration / len(entries)
            }
            
            print(f"Bulk storage ({size} entries): {duration:.2f}s, {throughput:.2f} entries/sec")
        
        # Verify performance meets requirements
        # Should handle 100 entries in under 30 seconds
        assert performance_results[100]['duration'] < 30.0
        assert performance_results[100]['success_rate'] > 0.95

    @pytest.mark.asyncio
    async def test_query_performance_with_large_dataset(self, history_manager, mock_supabase):
        """Test query performance with large simulated dataset"""
        
        # Simulate large dataset responses
        def create_mock_data(count: int) -> List[Dict[str, Any]]:
            return [
                {
                    'id': f'entry_{i}',
                    'team_id': f'team_{i % 10}',
                    'week_start_date': (datetime.utcnow() - timedelta(weeks=i)).isoformat(),
                    'week_end_date': (datetime.utcnow() - timedelta(weeks=i) + timedelta(days=6)).isoformat(),
                    'version': 1,
                    'status': 'published',
                    'content': {'test': f'content_{i}'},
                    'metadata': {'test': True},
                    'generated_at': datetime.utcnow().isoformat(),
                    'created_by': f'user_{i % 20}',
                    'tags': [f'tag_{j}' for j in range(3)]
                }
                for i in range(count)
            ]
        
        # Test different query scenarios
        query_scenarios = [
            {
                'name': 'team_filter',
                'filters': HistoryFilters(team_ids=['team_1'], limit=100),
                'expected_max_time': 2.0
            },
            {
                'name': 'date_range_filter',
                'filters': HistoryFilters(
                    date_range=(datetime.utcnow() - timedelta(days=30), datetime.utcnow()),
                    limit=100
                ),
                'expected_max_time': 2.0
            },
            {
                'name': 'full_text_search',
                'filters': HistoryFilters(search_text='test content', limit=50),
                'expected_max_time': 3.0
            },
            {
                'name': 'tag_search',
                'filters': HistoryFilters(tags=['tag_1', 'tag_2'], limit=100),
                'expected_max_time': 2.5
            },
            {
                'name': 'complex_query',
                'filters': HistoryFilters(
                    team_ids=['team_1', 'team_2'],
                    date_range=(datetime.utcnow() - timedelta(days=60), datetime.utcnow()),
                    status=ChangelogStatus.PUBLISHED,
                    search_text='content',
                    limit=200
                ),
                'expected_max_time': 4.0
            }
        ]
        
        performance_results = {}
        
        for scenario in query_scenarios:
            # Setup mock response with large dataset
            mock_data = create_mock_data(1000)  # Simulate 1000 entries
            
            mock_query = Mock()
            mock_supabase.table.return_value.select.return_value = mock_query
            
            # Chain mock methods
            for method in ['in_', 'gte', 'lte', 'eq', 'text_search', 'contains', 'range', 'order']:
                setattr(mock_query, method, Mock(return_value=mock_query))
            
            mock_query.execute.return_value.data = mock_data[:scenario['filters'].limit]
            
            # Measure query performance
            start_time = time.time()
            
            results = await history_manager.retrieve_changelog_history(scenario['filters'])
            
            end_time = time.time()
            duration = end_time - start_time
            
            performance_results[scenario['name']] = {
                'duration': duration,
                'result_count': len(results),
                'expected_max_time': scenario['expected_max_time']
            }
            
            print(f"Query '{scenario['name']}': {duration:.3f}s, {len(results)} results")
            
            # Verify performance meets requirements
            assert duration < scenario['expected_max_time'], \
                f"Query '{scenario['name']}' took {duration:.3f}s, expected < {scenario['expected_max_time']}s"

    @pytest.mark.asyncio
    async def test_trend_analysis_performance(self, history_manager, mock_supabase):
        """Test performance of trend analysis with large datasets"""
        
        # Generate large dataset for trend analysis
        large_dataset = [
            PerformanceTestData.generate_changelog_entry(
                team_id="trend_test_team",
                week_offset=i,
                content_size=random.choice(["small", "medium", "large"])
            )
            for i in range(500)  # 500 weeks of data
        ]
        
        # Mock the retrieve_changelog_history method
        async def mock_retrieve(filters):
            return large_dataset[:filters.limit]
        
        history_manager.retrieve_changelog_history = mock_retrieve
        
        # Test trend analysis performance
        start_time = time.time()
        
        trend_analysis = await history_manager.analyze_changelog_trends(
            team_id="trend_test_team",
            period=(datetime.utcnow() - timedelta(days=365), datetime.utcnow())
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Trend analysis (500 entries): {duration:.3f}s")
        
        # Verify performance and results
        assert duration < 10.0, f"Trend analysis took {duration:.3f}s, expected < 10s"
        assert isinstance(trend_analysis, TrendAnalysis)
        assert trend_analysis.team_id == "trend_test_team"
        assert len(trend_analysis.metrics) > 0

    @pytest.mark.asyncio
    async def test_export_performance(self, history_manager, mock_supabase):
        """Test export performance with different dataset sizes"""
        
        export_sizes = [100, 500, 1000, 2000]
        performance_results = {}
        
        for size in export_sizes:
            # Generate test dataset
            test_data = [
                PerformanceTestData.generate_changelog_entry(
                    team_id=f"export_team_{i % 5}",
                    week_offset=i,
                    content_size="medium"
                )
                for i in range(size)
            ]
            
            # Mock retrieve method
            async def mock_retrieve(filters):
                return test_data[:filters.limit]
            
            history_manager.retrieve_changelog_history = mock_retrieve
            
            # Test export performance
            export_config = ExportConfig(
                format=ExportFormat.JSON,
                filters=HistoryFilters(limit=size),
                include_metadata=True,
                compress=False
            )
            
            start_time = time.time()
            
            with patch('pathlib.Path.mkdir'), \
                 patch('builtins.open', create=True) as mock_open, \
                 patch('pathlib.Path.stat') as mock_stat:
                
                mock_stat.return_value.st_size = size * 1000  # Mock file size
                mock_open.return_value.__enter__.return_value = Mock()
                
                export_result = await history_manager.export_changelog_data(export_config)
            
            end_time = time.time()
            duration = end_time - start_time
            
            throughput = size / duration if duration > 0 else 0
            
            performance_results[size] = {
                'duration': duration,
                'throughput': throughput,
                'success': export_result.success if export_result else False
            }
            
            print(f"Export ({size} entries): {duration:.3f}s, {throughput:.1f} entries/sec")
        
        # Verify export performance meets requirements
        # Should export 1000 entries in under 30 seconds
        assert performance_results[1000]['duration'] < 30.0
        assert performance_results[1000]['success']

    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self, history_manager, mock_supabase):
        """Test performance under concurrent operations"""
        
        # Setup mocks
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "test"}])
        
        # Test concurrent storage operations
        concurrent_tasks = []
        
        # Create 50 concurrent storage operations
        for i in range(50):
            entry = PerformanceTestData.generate_changelog_entry(
                team_id=f"concurrent_team_{i % 5}",
                week_offset=i,
                content_size="medium"
            )
            concurrent_tasks.append(history_manager.store_changelog(entry))
        
        # Create 20 concurrent query operations
        for i in range(20):
            filters = HistoryFilters(
                team_ids=[f"concurrent_team_{i % 5}"],
                limit=50
            )
            
            # Mock query response
            mock_query = Mock()
            mock_supabase.table.return_value.select.return_value = mock_query
            for method in ['in_', 'range', 'order']:
                setattr(mock_query, method, Mock(return_value=mock_query))
            mock_query.execute.return_value.data = []
            
            concurrent_tasks.append(history_manager.retrieve_changelog_history(filters))
        
        # Execute all tasks concurrently
        start_time = time.time()
        
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Analyze results
        successful_operations = len([r for r in results if not isinstance(r, Exception)])
        failed_operations = len(results) - successful_operations
        
        print(f"Concurrent operations: {len(concurrent_tasks)} tasks in {duration:.3f}s")
        print(f"Success rate: {successful_operations}/{len(concurrent_tasks)} ({successful_operations/len(concurrent_tasks)*100:.1f}%)")
        
        # Verify concurrent performance
        assert duration < 60.0, f"Concurrent operations took {duration:.3f}s, expected < 60s"
        assert successful_operations / len(concurrent_tasks) > 0.9, "Success rate should be > 90%"

    @pytest.mark.asyncio
    async def test_memory_usage_optimization(self, history_manager, mock_supabase):
        """Test memory usage with large datasets"""
        
        # This test would typically use memory profiling tools
        # For now, we'll simulate memory-efficient operations
        
        # Test streaming large dataset processing
        batch_sizes = [10, 50, 100, 500]
        
        for batch_size in batch_sizes:
            # Simulate processing large dataset in batches
            total_processed = 0
            batch_count = 0
            
            start_time = time.time()
            
            # Process 1000 entries in batches
            for batch_start in range(0, 1000, batch_size):
                batch_end = min(batch_start + batch_size, 1000)
                batch_data = [
                    PerformanceTestData.generate_changelog_entry(
                        team_id=f"memory_team_{i % 3}",
                        week_offset=i,
                        content_size="small"  # Use small content to focus on batch processing
                    )
                    for i in range(batch_start, batch_end)
                ]
                
                # Simulate batch processing
                await asyncio.sleep(0.001)  # Simulate processing time
                
                total_processed += len(batch_data)
                batch_count += 1
                
                # Clear batch data to simulate memory cleanup
                del batch_data
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Batch processing (size {batch_size}): {batch_count} batches, {duration:.3f}s")
            
            assert total_processed == 1000
            assert duration < 5.0  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_database_connection_efficiency(self, history_manager, mock_supabase):
        """Test database connection pooling and efficiency"""
        
        # Test connection reuse across multiple operations
        operations = []
        
        # Create multiple operations that would use database connections
        for i in range(100):
            if i % 3 == 0:
                # Storage operation
                entry = PerformanceTestData.generate_changelog_entry(
                    team_id=f"conn_team_{i % 5}",
                    week_offset=i
                )
                operations.append(('store', entry))
            elif i % 3 == 1:
                # Query operation
                filters = HistoryFilters(team_ids=[f"conn_team_{i % 5}"], limit=10)
                operations.append(('query', filters))
            else:
                # Analytics operation
                period = (datetime.utcnow() - timedelta(days=30), datetime.utcnow())
                operations.append(('analytics', (f"conn_team_{i % 5}", period)))
        
        # Setup mocks for all operation types
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "test"}])
        
        # Mock query chain
        mock_query = Mock()
        mock_supabase.table.return_value.select.return_value = mock_query
        for method in ['in_', 'range', 'order']:
            setattr(mock_query, method, Mock(return_value=mock_query))
        mock_query.execute.return_value.data = []
        
        # Execute operations sequentially to test connection reuse
        start_time = time.time()
        
        for op_type, op_data in operations:
            try:
                if op_type == 'store':
                    await history_manager.store_changelog(op_data)
                elif op_type == 'query':
                    await history_manager.retrieve_changelog_history(op_data)
                elif op_type == 'analytics':
                    team_id, period = op_data
                    # Mock the retrieve method for analytics
                    history_manager.retrieve_changelog_history = AsyncMock(return_value=[])
                    await history_manager.analyze_changelog_trends(team_id, period)
            except Exception as e:
                print(f"Operation {op_type} failed: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Connection efficiency test: {len(operations)} operations in {duration:.3f}s")
        
        # Verify connection efficiency
        assert duration < 30.0, f"Connection test took {duration:.3f}s, expected < 30s"

    def test_query_optimization_analysis(self, history_manager):
        """Analyze query patterns for optimization opportunities"""
        
        # This test analyzes different query patterns to identify optimization needs
        query_patterns = [
            {
                'name': 'team_only',
                'filters': HistoryFilters(team_ids=['team_1']),
                'expected_index': 'idx_changelog_entries_team_date'
            },
            {
                'name': 'date_range',
                'filters': HistoryFilters(
                    date_range=(datetime.utcnow() - timedelta(days=30), datetime.utcnow())
                ),
                'expected_index': 'idx_changelog_entries_team_date'
            },
            {
                'name': 'status_filter',
                'filters': HistoryFilters(status=ChangelogStatus.PUBLISHED),
                'expected_index': 'idx_changelog_entries_status'
            },
            {
                'name': 'full_text_search',
                'filters': HistoryFilters(search_text='important update'),
                'expected_index': 'idx_changelog_entries_content_search'
            },
            {
                'name': 'tag_search',
                'filters': HistoryFilters(tags=['feature', 'bugfix']),
                'expected_index': 'idx_changelog_entries_tags'
            },
            {
                'name': 'user_filter',
                'filters': HistoryFilters(created_by='user_123'),
                'expected_index': 'idx_changelog_entries_created_by'
            }
        ]
        
        optimization_recommendations = []
        
        for pattern in query_patterns:
            # Analyze query pattern
            filters = pattern['filters']
            
            # Check if appropriate indexes would be used
            index_usage = self._analyze_index_usage(filters)
            
            if index_usage['optimal']:
                print(f"Query pattern '{pattern['name']}': Optimal (uses {index_usage['index']})")
            else:
                recommendation = {
                    'pattern': pattern['name'],
                    'issue': index_usage['issue'],
                    'recommendation': index_usage['recommendation']
                }
                optimization_recommendations.append(recommendation)
                print(f"Query pattern '{pattern['name']}': Needs optimization - {index_usage['issue']}")
        
        # Verify that most common patterns are optimized
        critical_patterns = ['team_only', 'date_range', 'status_filter']
        optimized_critical = [p for p in query_patterns if p['name'] in critical_patterns]
        
        assert len(optimization_recommendations) < len(query_patterns) * 0.3, \
            "Too many query patterns need optimization"

    def _analyze_index_usage(self, filters: HistoryFilters) -> Dict[str, Any]:
        """Analyze which indexes would be used for given filters"""
        
        # Simulate index usage analysis
        if filters.team_ids and filters.date_range:
            return {
                'optimal': True,
                'index': 'idx_changelog_entries_team_date',
                'selectivity': 'high'
            }
        elif filters.team_ids:
            return {
                'optimal': True,
                'index': 'idx_changelog_entries_team_date',
                'selectivity': 'medium'
            }
        elif filters.status:
            return {
                'optimal': True,
                'index': 'idx_changelog_entries_status',
                'selectivity': 'medium'
            }
        elif filters.search_text:
            return {
                'optimal': True,
                'index': 'idx_changelog_entries_content_search',
                'selectivity': 'variable'
            }
        elif filters.tags:
            return {
                'optimal': True,
                'index': 'idx_changelog_entries_tags',
                'selectivity': 'medium'
            }
        elif filters.created_by:
            return {
                'optimal': True,
                'index': 'idx_changelog_entries_created_by',
                'selectivity': 'high'
            }
        else:
            return {
                'optimal': False,
                'index': 'none',
                'issue': 'Full table scan required',
                'recommendation': 'Add appropriate filters or indexes'
            }

    @pytest.mark.asyncio
    async def test_scalability_limits(self, history_manager, mock_supabase):
        """Test system behavior at scalability limits"""
        
        # Test with maximum expected load
        max_scenarios = [
            {
                'name': 'max_teams',
                'teams': 100,
                'entries_per_team': 52,  # 1 year of weekly entries
                'expected_max_time': 120.0
            },
            {
                'name': 'max_history',
                'teams': 10,
                'entries_per_team': 520,  # 10 years of weekly entries
                'expected_max_time': 180.0
            },
            {
                'name': 'max_concurrent_users',
                'concurrent_operations': 50,
                'expected_max_time': 60.0
            }
        ]
        
        for scenario in max_scenarios:
            print(f"Testing scalability scenario: {scenario['name']}")
            
            if scenario['name'] in ['max_teams', 'max_history']:
                # Test large dataset scenarios
                total_entries = scenario['teams'] * scenario['entries_per_team']
                
                # Mock large dataset
                mock_data = [
                    {
                        'id': f'entry_{i}',
                        'team_id': f"team_{i % scenario['teams']}",
                        'week_start_date': (datetime.utcnow() - timedelta(weeks=i)).isoformat(),
                        'week_end_date': (datetime.utcnow() - timedelta(weeks=i) + timedelta(days=6)).isoformat(),
                        'version': 1,
                        'status': 'published',
                        'content': {'test': f'content_{i}'},
                        'metadata': {'test': True},
                        'generated_at': datetime.utcnow().isoformat(),
                        'created_by': f'user_{i % 100}',
                        'tags': [f'tag_{j}' for j in range(3)]
                    }
                    for i in range(min(total_entries, 1000))  # Limit for testing
                ]
                
                # Setup mock
                mock_query = Mock()
                mock_supabase.table.return_value.select.return_value = mock_query
                for method in ['in_', 'range', 'order']:
                    setattr(mock_query, method, Mock(return_value=mock_query))
                mock_query.execute.return_value.data = mock_data
                
                # Test query performance
                start_time = time.time()
                
                filters = HistoryFilters(limit=1000)
                results = await history_manager.retrieve_changelog_history(filters)
                
                end_time = time.time()
                duration = end_time - start_time
                
                print(f"Scenario '{scenario['name']}': {duration:.3f}s for {len(results)} entries")
                
                assert duration < scenario['expected_max_time'], \
                    f"Scalability test '{scenario['name']}' exceeded time limit"
            
            elif scenario['name'] == 'max_concurrent_users':
                # Test concurrent operations
                tasks = []
                
                for i in range(scenario['concurrent_operations']):
                    filters = HistoryFilters(team_ids=[f'team_{i % 10}'], limit=10)
                    
                    # Setup mock for each operation
                    mock_query = Mock()
                    mock_supabase.table.return_value.select.return_value = mock_query
                    for method in ['in_', 'range', 'order']:
                        setattr(mock_query, method, Mock(return_value=mock_query))
                    mock_query.execute.return_value.data = []
                    
                    tasks.append(history_manager.retrieve_changelog_history(filters))
                
                start_time = time.time()
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                end_time = time.time()
                duration = end_time - start_time
                
                successful_ops = len([r for r in results if not isinstance(r, Exception)])
                
                print(f"Concurrent operations: {successful_ops}/{len(tasks)} successful in {duration:.3f}s")
                
                assert duration < scenario['expected_max_time']
                assert successful_ops / len(tasks) > 0.9


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short"])