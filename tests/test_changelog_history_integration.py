"""
Integration Tests for Changelog History Manager

This module provides integration tests that demonstrate the complete
changelog history management workflow.
"""

import pytest
import asyncio
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, mock_open
from pathlib import Path


class MockSupabaseClient:
    """Mock Supabase client for testing"""
    
    def __init__(self):
        self.data_store = {}
        self.call_log = []
    
    def table(self, table_name):
        self.call_log.append(f"table({table_name})")
        return MockSupabaseTable(table_name, self.data_store, self.call_log)
    
    def rpc(self, function_name):
        self.call_log.append(f"rpc({function_name})")
        return MockSupabaseRPC(function_name, self.call_log)


class MockSupabaseTable:
    """Mock Supabase table operations"""
    
    def __init__(self, table_name, data_store, call_log):
        self.table_name = table_name
        self.data_store = data_store
        self.call_log = call_log
        self.query_filters = {}
    
    def select(self, columns):
        self.call_log.append(f"select({columns})")
        return self
    
    def insert(self, data):
        self.call_log.append(f"insert({type(data).__name__})")
        return MockSupabaseInsert(self.table_name, data, self.data_store, self.call_log)
    
    def update(self, data):
        self.call_log.append(f"update({type(data).__name__})")
        return MockSupabaseUpdate(self.table_name, data, self.data_store, self.call_log)
    
    def delete(self):
        self.call_log.append("delete()")
        return MockSupabaseDelete(self.table_name, self.data_store, self.call_log)
    
    def eq(self, column, value):
        self.call_log.append(f"eq({column}, {value})")
        self.query_filters[column] = value
        return self
    
    def in_(self, column, values):
        self.call_log.append(f"in_({column}, {values})")
        self.query_filters[column] = values
        return self
    
    def gte(self, column, value):
        self.call_log.append(f"gte({column}, {value})")
        return self
    
    def lte(self, column, value):
        self.call_log.append(f"lte({column}, {value})")
        return self
    
    def text_search(self, column, query):
        self.call_log.append(f"text_search({column}, {query})")
        return self
    
    def contains(self, column, values):
        self.call_log.append(f"contains({column}, {values})")
        return self
    
    def range(self, start, end):
        self.call_log.append(f"range({start}, {end})")
        return self
    
    def order(self, column, desc=False):
        self.call_log.append(f"order({column}, desc={desc})")
        return self
    
    def limit(self, count):
        self.call_log.append(f"limit({count})")
        return self
    
    def execute(self):
        self.call_log.append("execute()")
        # Return mock data based on table and filters
        if self.table_name == 'changelog_entries':
            return MockSupabaseResponse(self._get_changelog_data())
        return MockSupabaseResponse([])
    
    def _get_changelog_data(self):
        """Generate mock changelog data"""
        return [
            {
                'id': 'test_entry_1',
                'team_id': 'test_team',
                'week_start_date': '2024-01-01T00:00:00+00:00',
                'week_end_date': '2024-01-07T00:00:00+00:00',
                'version': 1,
                'status': 'published',
                'content': {'summary': 'Test changelog 1'},
                'metadata': {'test': True},
                'generated_at': '2024-01-01T10:00:00+00:00',
                'created_by': 'test_user',
                'tags': ['test', 'feature']
            },
            {
                'id': 'test_entry_2',
                'team_id': 'test_team',
                'week_start_date': '2024-01-08T00:00:00+00:00',
                'week_end_date': '2024-01-14T00:00:00+00:00',
                'version': 1,
                'status': 'draft',
                'content': {'summary': 'Test changelog 2'},
                'generated_at': '2024-01-08T10:00:00+00:00',
                'created_by': 'test_user',
                'tags': ['test', 'bugfix']
            }
        ]


class MockSupabaseInsert:
    """Mock Supabase insert operation"""
    
    def __init__(self, table_name, data, data_store, call_log):
        self.table_name = table_name
        self.data = data
        self.data_store = data_store
        self.call_log = call_log
    
    def execute(self):
        self.call_log.append("insert.execute()")
        # Store the data
        if self.table_name not in self.data_store:
            self.data_store[self.table_name] = []
        self.data_store[self.table_name].append(self.data)
        return MockSupabaseResponse([{'id': self.data.get('id', 'generated_id')}])


class MockSupabaseUpdate:
    """Mock Supabase update operation"""
    
    def __init__(self, table_name, data, data_store, call_log):
        self.table_name = table_name
        self.data = data
        self.data_store = data_store
        self.call_log = call_log
    
    def eq(self, column, value):
        self.call_log.append(f"update.eq({column}, {value})")
        return self
    
    def execute(self):
        self.call_log.append("update.execute()")
        return MockSupabaseResponse([])


class MockSupabaseDelete:
    """Mock Supabase delete operation"""
    
    def __init__(self, table_name, data_store, call_log):
        self.table_name = table_name
        self.data_store = data_store
        self.call_log = call_log
    
    def eq(self, column, value):
        self.call_log.append(f"delete.eq({column}, {value})")
        return self
    
    def execute(self):
        self.call_log.append("delete.execute()")
        return MockSupabaseResponse([])


class MockSupabaseRPC:
    """Mock Supabase RPC operation"""
    
    def __init__(self, function_name, call_log):
        self.function_name = function_name
        self.call_log = call_log
    
    def execute(self):
        self.call_log.append(f"rpc.execute({self.function_name})")
        return MockSupabaseResponse([])


class MockSupabaseResponse:
    """Mock Supabase response"""
    
    def __init__(self, data):
        self.data = data


@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = Mock()
    config.SUPABASE_URL = "https://test.supabase.co"
    config.supabase_service_role_key = "test_key"
    return config


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    return MockSupabaseClient()


class TestChangelogHistoryIntegration:
    """Integration tests for changelog history management"""

    @pytest.mark.asyncio
    async def test_complete_changelog_lifecycle(self, mock_config, mock_supabase_client):
        """Test complete changelog lifecycle: create, store, retrieve, analyze"""
        
        # Import here to avoid config issues
        with patch('devsync_ai.database.changelog_history_manager.create_client', return_value=mock_supabase_client):
            from devsync_ai.database.changelog_history_manager import (
                ChangelogHistoryManager, ChangelogEntry, ChangelogStatus, HistoryFilters
            )
            
            # Initialize manager
            manager = ChangelogHistoryManager(mock_config)
            
            # Create a changelog entry
            changelog = ChangelogEntry(
                id="integration_test_1",
                team_id="integration_team",
                week_start_date=datetime(2024, 1, 1),
                week_end_date=datetime(2024, 1, 7),
                version=1,
                status=ChangelogStatus.DRAFT,
                content={
                    "summary": "Integration test changelog",
                    "features": ["Feature A", "Feature B"],
                    "bug_fixes": ["Bug fix 1"],
                    "improvements": ["Performance improvement"]
                },
                metadata={"integration_test": True},
                generated_at=datetime.utcnow(),
                created_by="integration_user",
                tags=["integration", "test", "feature"]
            )
            
            # Store the changelog
            storage_result = await manager.store_changelog(changelog)
            
            # Verify storage
            assert storage_result.success is True
            assert storage_result.changelog_id == "integration_test_1"
            assert storage_result.version == 1
            
            # Retrieve changelog history
            filters = HistoryFilters(
                team_ids=["integration_team"],
                limit=10
            )
            
            history = await manager.retrieve_changelog_history(filters)
            
            # Verify retrieval
            assert len(history) >= 1
            assert any(entry.id == "integration_test_1" for entry in history)
            
            # Analyze trends
            period = (datetime(2024, 1, 1), datetime(2024, 1, 31))
            trend_analysis = await manager.analyze_changelog_trends("integration_team", period)
            
            # Verify trend analysis
            assert trend_analysis.team_id == "integration_team"
            assert trend_analysis.period == period
            assert isinstance(trend_analysis.metrics, dict)
            assert isinstance(trend_analysis.patterns, list)
            assert isinstance(trend_analysis.predictions, dict)
            assert isinstance(trend_analysis.anomalies, list)

    @pytest.mark.asyncio
    async def test_export_and_backup_workflow(self, mock_config, mock_supabase_client):
        """Test export and backup workflow"""
        
        with patch('devsync_ai.database.changelog_history_manager.create_client', return_value=mock_supabase_client):
            from devsync_ai.database.changelog_history_manager import (
                ChangelogHistoryManager, ExportConfig, ExportFormat, HistoryFilters
            )
            
            manager = ChangelogHistoryManager(mock_config)
            
            # Test export functionality
            export_config = ExportConfig(
                format=ExportFormat.JSON,
                filters=HistoryFilters(team_ids=["export_team"], limit=100),
                include_metadata=True,
                compress=False
            )
            
            with patch('pathlib.Path.mkdir'), \
                 patch('builtins.open', mock_open()) as mock_file, \
                 patch('pathlib.Path.stat') as mock_stat:
                
                mock_stat.return_value.st_size = 2048
                
                export_result = await manager.export_changelog_data(export_config)
            
            # Verify export
            assert export_result.success is True
            assert export_result.record_count >= 0
            assert export_result.file_size == 2048
            
            # Test backup creation
            with patch('pathlib.Path.mkdir'), \
                 patch('builtins.open', mock_open()) as mock_file, \
                 patch('hashlib.md5') as mock_md5:
                
                mock_hash = Mock()
                mock_hash.hexdigest.return_value = "test_hash_123"
                mock_md5.return_value = mock_hash
                
                # Mock validation
                manager._validate_backup = AsyncMock(return_value=True)
                
                backup_result = await manager.create_backup("backup_team")
            
            # Verify backup
            assert backup_result['success'] is True
            assert 'backup_id' in backup_result
            assert backup_result['validation_passed'] is True

    @pytest.mark.asyncio
    async def test_retention_policy_workflow(self, mock_config, mock_supabase_client):
        """Test data retention policy workflow"""
        
        with patch('devsync_ai.database.changelog_history_manager.create_client', return_value=mock_supabase_client):
            from devsync_ai.database.changelog_history_manager import (
                ChangelogHistoryManager, RetentionPolicy
            )
            
            manager = ChangelogHistoryManager(mock_config)
            
            # Create retention policy
            retention_policy = RetentionPolicy(
                team_id="retention_team",
                archive_after_days=180,
                delete_after_days=365,
                compress_after_days=90,
                legal_hold=False,
                compliance_requirements=["GDPR", "SOX"]
            )
            
            # Apply retention policy
            retention_result = await manager.manage_data_retention(retention_policy)
            
            # Verify retention
            assert retention_result.success is True
            assert retention_result.processed_count >= 0
            assert isinstance(retention_result.archived_count, int)
            assert isinstance(retention_result.deleted_count, int)

    @pytest.mark.asyncio
    async def test_search_and_filtering_capabilities(self, mock_config, mock_supabase_client):
        """Test advanced search and filtering capabilities"""
        
        with patch('devsync_ai.database.changelog_history_manager.create_client', return_value=mock_supabase_client):
            from devsync_ai.database.changelog_history_manager import (
                ChangelogHistoryManager, HistoryFilters, ChangelogStatus
            )
            
            manager = ChangelogHistoryManager(mock_config)
            
            # Test various filter combinations
            filter_scenarios = [
                {
                    'name': 'team_filter',
                    'filters': HistoryFilters(team_ids=['search_team'])
                },
                {
                    'name': 'date_range_filter',
                    'filters': HistoryFilters(
                        date_range=(datetime(2024, 1, 1), datetime(2024, 1, 31))
                    )
                },
                {
                    'name': 'status_filter',
                    'filters': HistoryFilters(status=ChangelogStatus.PUBLISHED)
                },
                {
                    'name': 'text_search',
                    'filters': HistoryFilters(search_text='important feature')
                },
                {
                    'name': 'tag_search',
                    'filters': HistoryFilters(tags=['feature', 'bugfix'])
                },
                {
                    'name': 'user_filter',
                    'filters': HistoryFilters(created_by='search_user')
                },
                {
                    'name': 'complex_filter',
                    'filters': HistoryFilters(
                        team_ids=['search_team'],
                        date_range=(datetime(2024, 1, 1), datetime(2024, 1, 31)),
                        status=ChangelogStatus.PUBLISHED,
                        search_text='feature',
                        tags=['important'],
                        limit=50
                    )
                }
            ]
            
            # Test each filter scenario
            for scenario in filter_scenarios:
                results = await manager.retrieve_changelog_history(scenario['filters'])
                
                # Verify results structure
                assert isinstance(results, list)
                # Results can be empty, but should be a valid list
                
                print(f"Filter scenario '{scenario['name']}': {len(results)} results")

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, mock_config):
        """Test error handling and recovery scenarios"""
        
        # Test with failing Supabase client
        failing_client = Mock()
        failing_client.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")
        failing_client.rpc.return_value.execute.return_value = None
        
        with patch('devsync_ai.database.changelog_history_manager.create_client', return_value=failing_client):
            from devsync_ai.database.changelog_history_manager import (
                ChangelogHistoryManager, ChangelogEntry, ChangelogStatus
            )
            
            manager = ChangelogHistoryManager(mock_config)
            
            # Test storage error handling
            changelog = ChangelogEntry(
                id="error_test",
                team_id="error_team",
                week_start_date=datetime(2024, 1, 1),
                week_end_date=datetime(2024, 1, 7),
                version=1,
                status=ChangelogStatus.DRAFT,
                content={"summary": "Error test"},
                generated_at=datetime.utcnow()
            )
            
            storage_result = await manager.store_changelog(changelog)
            
            # Verify error handling
            assert storage_result.success is False
            assert storage_result.errors is not None
            assert len(storage_result.errors) > 0
            assert "Database error" in storage_result.errors[0]

    def test_database_schema_validation(self):
        """Test database schema validation"""
        
        # Read the migration file
        migration_file = Path("devsync_ai/database/migrations/003_changelog_history_schema.sql")
        
        if migration_file.exists():
            with open(migration_file, 'r') as f:
                schema_sql = f.read()
            
            # Verify key schema elements
            assert "CREATE TABLE IF NOT EXISTS changelog_entries" in schema_sql
            assert "CREATE TABLE IF NOT EXISTS changelog_audit_trail" in schema_sql
            assert "CREATE TABLE IF NOT EXISTS changelog_distributions" in schema_sql
            assert "CREATE TABLE IF NOT EXISTS changelog_analytics" in schema_sql
            assert "CREATE TABLE IF NOT EXISTS changelog_export_jobs" in schema_sql
            assert "CREATE TABLE IF NOT EXISTS changelog_retention_policies" in schema_sql
            assert "CREATE TABLE IF NOT EXISTS changelog_backups" in schema_sql
            
            # Verify indexes
            assert "idx_changelog_entries_team_date" in schema_sql
            assert "idx_changelog_entries_content_search" in schema_sql
            assert "idx_changelog_entries_tags" in schema_sql
            
            # Verify RLS policies
            assert "ENABLE ROW LEVEL SECURITY" in schema_sql
            assert "CREATE POLICY" in schema_sql
            
            # Verify views
            assert "CREATE OR REPLACE VIEW changelog_entries_with_stats" in schema_sql
            assert "CREATE OR REPLACE VIEW team_changelog_analytics" in schema_sql
            
            print("Database schema validation passed")
        else:
            print("Migration file not found, skipping schema validation")

    @pytest.mark.asyncio
    async def test_performance_simulation(self, mock_config, mock_supabase_client):
        """Test performance with simulated load"""
        
        with patch('devsync_ai.database.changelog_history_manager.create_client', return_value=mock_supabase_client):
            from devsync_ai.database.changelog_history_manager import (
                ChangelogHistoryManager, ChangelogEntry, ChangelogStatus, HistoryFilters
            )
            
            manager = ChangelogHistoryManager(mock_config)
            
            # Simulate concurrent operations
            tasks = []
            
            # Create multiple storage tasks
            for i in range(10):
                changelog = ChangelogEntry(
                    id=f"perf_test_{i}",
                    team_id=f"perf_team_{i % 3}",
                    week_start_date=datetime(2024, 1, 1) + timedelta(weeks=i),
                    week_end_date=datetime(2024, 1, 7) + timedelta(weeks=i),
                    version=1,
                    status=ChangelogStatus.DRAFT,
                    content={"summary": f"Performance test {i}"},
                    generated_at=datetime.utcnow()
                )
                tasks.append(manager.store_changelog(changelog))
            
            # Create multiple query tasks
            for i in range(5):
                filters = HistoryFilters(
                    team_ids=[f"perf_team_{i % 3}"],
                    limit=20
                )
                tasks.append(manager.retrieve_changelog_history(filters))
            
            # Execute all tasks concurrently
            import time
            start_time = time.time()
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify performance
            successful_operations = len([r for r in results if not isinstance(r, Exception)])
            print(f"Performance test: {successful_operations}/{len(tasks)} operations in {duration:.3f}s")
            
            assert duration < 10.0  # Should complete within 10 seconds
            assert successful_operations > len(tasks) * 0.8  # At least 80% success rate

    def test_data_model_serialization(self):
        """Test data model serialization and deserialization"""
        
        from devsync_ai.database.changelog_history_manager import (
            ChangelogEntry, ChangelogStatus
        )
        
        # Create a changelog entry
        original_entry = ChangelogEntry(
            id="serialization_test",
            team_id="test_team",
            week_start_date=datetime(2024, 1, 1),
            week_end_date=datetime(2024, 1, 7),
            version=1,
            status=ChangelogStatus.PUBLISHED,
            content={
                "summary": "Serialization test",
                "features": ["Feature 1", "Feature 2"],
                "metadata": {"complexity": 0.8}
            },
            metadata={"test": True, "priority": "high"},
            generated_at=datetime.utcnow(),
            published_at=datetime.utcnow(),
            created_by="test_user",
            tags=["test", "serialization"]
        )
        
        # Test serialization to dict
        from dataclasses import asdict
        entry_dict = asdict(original_entry)
        
        # Verify serialization
        assert entry_dict['id'] == "serialization_test"
        assert entry_dict['team_id'] == "test_team"
        assert entry_dict['version'] == 1
        assert entry_dict['status'] == ChangelogStatus.PUBLISHED
        assert isinstance(entry_dict['content'], dict)
        assert isinstance(entry_dict['metadata'], dict)
        assert isinstance(entry_dict['tags'], list)
        
        # Test JSON serialization (with datetime handling)
        json_data = {
            **entry_dict,
            'week_start_date': original_entry.week_start_date.isoformat(),
            'week_end_date': original_entry.week_end_date.isoformat(),
            'generated_at': original_entry.generated_at.isoformat(),
            'published_at': original_entry.published_at.isoformat(),
            'status': original_entry.status.value
        }
        
        json_string = json.dumps(json_data, indent=2)
        
        # Verify JSON serialization
        assert "serialization_test" in json_string
        assert "test_team" in json_string
        assert "published" in json_string
        
        # Test deserialization
        parsed_data = json.loads(json_string)
        assert parsed_data['id'] == "serialization_test"
        assert parsed_data['status'] == "published"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])