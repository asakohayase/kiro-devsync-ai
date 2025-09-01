"""
Unit Tests for Changelog History Manager

This module provides comprehensive unit tests for the ChangelogHistoryManager
including all functionality: storage, retrieval, analytics, export, retention, and backup.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, mock_open
from typing import List, Dict, Any

from devsync_ai.database.changelog_history_manager import (
    ChangelogHistoryManager,
    ChangelogEntry,
    ChangelogStatus,
    HistoryFilters,
    StorageResult,
    TrendAnalysis,
    ExportConfig,
    ExportFormat,
    ExportResult,
    RetentionPolicy,
    RetentionResult
)
from devsync_ai.config import Config


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = Mock(spec=Config)
    config.SUPABASE_URL = "https://test.supabase.co"
    config.SUPABASE_KEY = "test_key"
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


@pytest.fixture
def sample_changelog_entry():
    """Create a sample changelog entry for testing"""
    return ChangelogEntry(
        id="test_id_123",
        team_id="test_team",
        week_start_date=datetime(2024, 1, 1),
        week_end_date=datetime(2024, 1, 7),
        version=1,
        status=ChangelogStatus.DRAFT,
        content={
            "summary": "Test changelog",
            "features": ["Feature 1", "Feature 2"],
            "bug_fixes": ["Bug fix 1"],
            "improvements": ["Improvement 1"]
        },
        metadata={"test": True},
        generated_at=datetime.utcnow(),
        created_by="test_user",
        tags=["test", "feature"]
    )


class TestChangelogHistoryManager:
    """Test cases for ChangelogHistoryManager"""

    def test_initialization(self, mock_config, mock_supabase):
        """Test proper initialization of ChangelogHistoryManager"""
        with patch('devsync_ai.database.changelog_history_manager.create_client', return_value=mock_supabase):
            manager = ChangelogHistoryManager(mock_config)
            
            assert manager.config == mock_config
            assert manager.supabase == mock_supabase
            mock_supabase.rpc.assert_called_once_with('create_changelog_tables')

    @pytest.mark.asyncio
    async def test_store_changelog_new_entry(self, history_manager, mock_supabase, sample_changelog_entry):
        """Test storing a new changelog entry"""
        # Setup mocks
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "test_id_123"}])
        
        # Test storage
        result = await history_manager.store_changelog(sample_changelog_entry)
        
        # Verify result
        assert isinstance(result, StorageResult)
        assert result.success is True
        assert result.changelog_id == "test_id_123"
        assert result.version == 1
        assert "successfully" in result.message.lower()
        
        # Verify database calls
        mock_supabase.table.assert_called()
        mock_supabase.table.return_value.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_changelog_version_increment(self, history_manager, mock_supabase, sample_changelog_entry):
        """Test version increment for existing changelog"""
        # Setup mock for existing entry
        existing_data = {
            'id': 'existing_id',
            'team_id': 'test_team',
            'week_start_date': '2024-01-01T00:00:00+00:00',
            'week_end_date': '2024-01-07T00:00:00+00:00',
            'version': 2,
            'status': 'published',
            'content': {'test': 'existing'},
            'generated_at': '2024-01-01T10:00:00+00:00'
        }
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [existing_data]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "test_id_123"}])
        
        # Test storage
        result = await history_manager.store_changelog(sample_changelog_entry)
        
        # Verify version increment
        assert result.success is True
        assert result.version == 3  # Should increment from existing version 2

    @pytest.mark.asyncio
    async def test_store_changelog_error_handling(self, history_manager, mock_supabase, sample_changelog_entry):
        """Test error handling during changelog storage"""
        # Setup mock to raise exception
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")
        
        # Test storage
        result = await history_manager.store_changelog(sample_changelog_entry)
        
        # Verify error handling
        assert isinstance(result, StorageResult)
        assert result.success is False
        assert result.errors is not None
        assert len(result.errors) > 0
        assert "Database error" in result.errors[0]

    @pytest.mark.asyncio
    async def test_retrieve_changelog_history_basic(self, history_manager, mock_supabase):
        """Test basic changelog history retrieval"""
        # Setup mock data
        mock_data = [
            {
                'id': 'entry_1',
                'team_id': 'test_team',
                'week_start_date': '2024-01-01T00:00:00+00:00',
                'week_end_date': '2024-01-07T00:00:00+00:00',
                'version': 1,
                'status': 'published',
                'content': {'test': 'content1'},
                'metadata': {'test': True},
                'generated_at': '2024-01-01T10:00:00+00:00',
                'created_by': 'user1',
                'tags': ['tag1']
            },
            {
                'id': 'entry_2',
                'team_id': 'test_team',
                'week_start_date': '2024-01-08T00:00:00+00:00',
                'week_end_date': '2024-01-14T00:00:00+00:00',
                'version': 1,
                'status': 'draft',
                'content': {'test': 'content2'},
                'generated_at': '2024-01-08T10:00:00+00:00',
                'created_by': 'user2',
                'tags': ['tag2']
            }
        ]
        
        # Setup mock query chain
        mock_query = Mock()
        mock_supabase.table.return_value.select.return_value = mock_query
        
        # Chain all possible filter methods
        for method in ['in_', 'gte', 'lte', 'eq', 'text_search', 'contains', 'range', 'order']:
            setattr(mock_query, method, Mock(return_value=mock_query))
        
        mock_query.execute.return_value.data = mock_data
        
        # Test retrieval
        filters = HistoryFilters(team_ids=['test_team'], limit=10)
        results = await history_manager.retrieve_changelog_history(filters)
        
        # Verify results
        assert len(results) == 2
        assert all(isinstance(entry, ChangelogEntry) for entry in results)
        assert results[0].id == 'entry_1'
        assert results[0].team_id == 'test_team'
        assert results[0].status == ChangelogStatus.PUBLISHED
        assert results[1].id == 'entry_2'
        assert results[1].status == ChangelogStatus.DRAFT

    @pytest.mark.asyncio
    async def test_retrieve_changelog_history_with_filters(self, history_manager, mock_supabase):
        """Test changelog history retrieval with various filters"""
        # Setup mock query chain
        mock_query = Mock()
        mock_supabase.table.return_value.select.return_value = mock_query
        
        for method in ['in_', 'gte', 'lte', 'eq', 'text_search', 'contains', 'range', 'order']:
            setattr(mock_query, method, Mock(return_value=mock_query))
        
        mock_query.execute.return_value.data = []
        
        # Test with comprehensive filters
        filters = HistoryFilters(
            team_ids=['team1', 'team2'],
            date_range=(datetime(2024, 1, 1), datetime(2024, 1, 31)),
            status=ChangelogStatus.PUBLISHED,
            search_text='important update',
            tags=['feature', 'bugfix'],
            created_by='user123',
            limit=50,
            offset=10
        )
        
        results = await history_manager.retrieve_changelog_history(filters)
        
        # Verify filter methods were called
        mock_query.in_.assert_called()
        mock_query.gte.assert_called()
        mock_query.lte.assert_called()
        mock_query.eq.assert_called()
        mock_query.text_search.assert_called()
        mock_query.contains.assert_called()
        mock_query.range.assert_called()
        mock_query.order.assert_called()

    @pytest.mark.asyncio
    async def test_analyze_changelog_trends(self, history_manager):
        """Test changelog trend analysis"""
        # Mock data for trend analysis
        mock_entries = [
            ChangelogEntry(
                id=f"entry_{i}",
                team_id="trend_team",
                week_start_date=datetime(2024, 1, 1) + timedelta(weeks=i),
                week_end_date=datetime(2024, 1, 7) + timedelta(weeks=i),
                version=1,
                status=ChangelogStatus.PUBLISHED if i % 2 == 0 else ChangelogStatus.DRAFT,
                content={"summary": f"Content {i}", "features": [f"Feature {i}"]},
                generated_at=datetime.utcnow(),
                created_by=f"user_{i % 3}"
            )
            for i in range(10)
        ]
        
        # Mock the retrieve method
        async def mock_retrieve(filters):
            return mock_entries
        
        history_manager.retrieve_changelog_history = mock_retrieve
        
        # Test trend analysis
        period = (datetime(2024, 1, 1), datetime(2024, 3, 31))
        result = await history_manager.analyze_changelog_trends("trend_team", period)
        
        # Verify result
        assert isinstance(result, TrendAnalysis)
        assert result.team_id == "trend_team"
        assert result.period == period
        assert 'total_entries' in result.metrics
        assert 'published_entries' in result.metrics
        assert 'publication_rate' in result.metrics
        assert result.metrics['total_entries'] == 10
        assert result.metrics['published_entries'] == 5  # Half are published
        assert result.metrics['publication_rate'] == 0.5

    @pytest.mark.asyncio
    async def test_export_changelog_data_json(self, history_manager):
        """Test changelog data export in JSON format"""
        # Mock data for export
        mock_entries = [
            ChangelogEntry(
                id="export_1",
                team_id="export_team",
                week_start_date=datetime(2024, 1, 1),
                week_end_date=datetime(2024, 1, 7),
                version=1,
                status=ChangelogStatus.PUBLISHED,
                content={"summary": "Export test"},
                generated_at=datetime.utcnow(),
                created_by="export_user"
            )
        ]
        
        # Mock the retrieve method
        async def mock_retrieve(filters):
            return mock_entries
        
        history_manager.retrieve_changelog_history = mock_retrieve
        
        # Test export
        export_config = ExportConfig(
            format=ExportFormat.JSON,
            filters=HistoryFilters(team_ids=['export_team']),
            include_metadata=True,
            compress=False
        )
        
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('pathlib.Path.stat') as mock_stat:
            
            mock_stat.return_value.st_size = 1024
            
            result = await history_manager.export_changelog_data(export_config)
        
        # Verify export result
        assert isinstance(result, ExportResult)
        assert result.success is True
        assert result.record_count == 1
        assert result.file_size == 1024
        assert "json" in result.export_id or "successfully" in result.message.lower()

    @pytest.mark.asyncio
    async def test_export_changelog_data_csv(self, history_manager):
        """Test changelog data export in CSV format"""
        mock_entries = [
            ChangelogEntry(
                id="csv_1",
                team_id="csv_team",
                week_start_date=datetime(2024, 1, 1),
                week_end_date=datetime(2024, 1, 7),
                version=1,
                status=ChangelogStatus.PUBLISHED,
                content={"summary": "CSV test"},
                generated_at=datetime.utcnow()
            )
        ]
        
        history_manager.retrieve_changelog_history = AsyncMock(return_value=mock_entries)
        
        export_config = ExportConfig(
            format=ExportFormat.CSV,
            filters=HistoryFilters(team_ids=['csv_team'])
        )
        
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('csv.DictWriter') as mock_csv_writer:
            
            mock_stat.return_value.st_size = 512
            mock_writer = Mock()
            mock_csv_writer.return_value = mock_writer
            
            result = await history_manager.export_changelog_data(export_config)
        
        assert result.success is True
        mock_writer.writeheader.assert_called_once()
        mock_writer.writerow.assert_called()

    @pytest.mark.asyncio
    async def test_manage_data_retention(self, history_manager, mock_supabase):
        """Test data retention management"""
        # Setup mock data with different ages
        old_date = datetime.utcnow() - timedelta(days=400)
        archive_date = datetime.utcnow() - timedelta(days=200)
        recent_date = datetime.utcnow() - timedelta(days=30)
        
        mock_data = [
            {
                'id': 'old_entry',
                'team_id': 'retention_team',
                'week_start_date': old_date.isoformat(),
                'week_end_date': (old_date + timedelta(days=6)).isoformat(),
                'version': 1,
                'status': 'published',
                'content': {'test': 'old'},
                'generated_at': old_date.isoformat()
            },
            {
                'id': 'archive_entry',
                'team_id': 'retention_team',
                'week_start_date': archive_date.isoformat(),
                'week_end_date': (archive_date + timedelta(days=6)).isoformat(),
                'version': 1,
                'status': 'published',
                'content': {'test': 'archive'},
                'generated_at': archive_date.isoformat()
            },
            {
                'id': 'recent_entry',
                'team_id': 'retention_team',
                'week_start_date': recent_date.isoformat(),
                'week_end_date': (recent_date + timedelta(days=6)).isoformat(),
                'version': 1,
                'status': 'published',
                'content': {'test': 'recent'},
                'generated_at': recent_date.isoformat()
            }
        ]
        
        # Setup mocks
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_data
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = Mock()
        
        # Test retention policy
        retention_policy = RetentionPolicy(
            team_id="retention_team",
            archive_after_days=180,
            delete_after_days=365,
            compress_after_days=90
        )
        
        result = await history_manager.manage_data_retention(retention_policy)
        
        # Verify result
        assert isinstance(result, RetentionResult)
        assert result.success is True
        assert result.processed_count == 3
        assert result.archived_count >= 1  # archive_entry should be archived
        assert result.deleted_count >= 1   # old_entry should be deleted

    @pytest.mark.asyncio
    async def test_create_backup(self, history_manager):
        """Test backup creation"""
        # Mock export functionality
        mock_export_result = ExportResult(
            success=True,
            export_id="backup_export",
            file_path="/tmp/backup.json",
            file_size=2048,
            record_count=10,
            message="Export successful"
        )
        
        history_manager.export_changelog_data = AsyncMock(return_value=mock_export_result)
        
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('hashlib.md5') as mock_md5:
            
            mock_hash = Mock()
            mock_hash.hexdigest.return_value = "abc123def456"
            mock_md5.return_value = mock_hash
            
            # Mock validation
            history_manager._validate_backup = AsyncMock(return_value=True)
            
            result = await history_manager.create_backup("test_team")
        
        # Verify backup result
        assert result['success'] is True
        assert 'backup_id' in result
        assert result['record_count'] == 10
        assert result['file_size'] == 2048
        assert result['validation_passed'] is True

    @pytest.mark.asyncio
    async def test_restore_from_backup(self, history_manager):
        """Test backup restoration"""
        backup_id = "test_backup_123"
        
        # Mock backup metadata
        backup_metadata = {
            'backup_id': backup_id,
            'timestamp': datetime.utcnow().isoformat(),
            'record_count': 5,
            'validation_hash': 'abc123'
        }
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(backup_metadata))):
            
            # Mock validation
            history_manager._validate_backup = AsyncMock(return_value=True)
            
            result = await history_manager.restore_from_backup(backup_id)
        
        # Verify restoration result
        assert result['success'] is True
        assert result['backup_id'] == backup_id
        assert result['restored_records'] == 5

    @pytest.mark.asyncio
    async def test_restore_from_backup_not_found(self, history_manager):
        """Test backup restoration when backup doesn't exist"""
        backup_id = "nonexistent_backup"
        
        with patch('pathlib.Path.exists', return_value=False):
            result = await history_manager.restore_from_backup(backup_id)
        
        # Verify error handling
        assert result['success'] is False
        assert 'not found' in result['error'].lower()

    def test_dict_to_changelog_entry_conversion(self, history_manager):
        """Test conversion from dictionary to ChangelogEntry object"""
        data = {
            'id': 'test_id',
            'team_id': 'test_team',
            'week_start_date': '2024-01-01T00:00:00+00:00',
            'week_end_date': '2024-01-07T00:00:00+00:00',
            'version': 1,
            'status': 'published',
            'content': {'test': 'content'},
            'metadata': {'test': True},
            'generated_at': '2024-01-01T10:00:00+00:00',
            'published_at': '2024-01-01T12:00:00+00:00',
            'created_by': 'test_user',
            'tags': ['tag1', 'tag2']
        }
        
        entry = history_manager._dict_to_changelog_entry(data)
        
        # Verify conversion
        assert isinstance(entry, ChangelogEntry)
        assert entry.id == 'test_id'
        assert entry.team_id == 'test_team'
        assert entry.version == 1
        assert entry.status == ChangelogStatus.PUBLISHED
        assert entry.content == {'test': 'content'}
        assert entry.metadata == {'test': True}
        assert entry.created_by == 'test_user'
        assert entry.tags == ['tag1', 'tag2']
        assert isinstance(entry.week_start_date, datetime)
        assert isinstance(entry.generated_at, datetime)

    @pytest.mark.asyncio
    async def test_calculate_trend_metrics(self, history_manager):
        """Test trend metrics calculation"""
        entries = [
            ChangelogEntry(
                id=f"metric_{i}",
                team_id="metrics_team",
                week_start_date=datetime(2024, 1, 1) + timedelta(weeks=i),
                week_end_date=datetime(2024, 1, 7) + timedelta(weeks=i),
                version=1,
                status=ChangelogStatus.PUBLISHED if i < 3 else ChangelogStatus.DRAFT,
                content={"summary": "x" * (100 * (i + 1))},  # Varying content length
                generated_at=datetime.utcnow()
            )
            for i in range(5)
        ]
        
        metrics = await history_manager._calculate_trend_metrics(entries)
        
        # Verify metrics
        assert metrics['total_entries'] == 5
        assert metrics['published_entries'] == 3
        assert metrics['publication_rate'] == 0.6
        assert 'avg_content_length' in metrics
        assert 'date_range' in metrics
        assert metrics['avg_content_length'] > 0

    @pytest.mark.asyncio
    async def test_identify_patterns(self, history_manager):
        """Test pattern identification in changelog data"""
        entries = [
            ChangelogEntry(
                id=f"pattern_{i}",
                team_id="pattern_team",
                week_start_date=datetime(2024, 1, 1) + timedelta(weeks=i),
                week_end_date=datetime(2024, 1, 7) + timedelta(weeks=i),
                version=1,
                status=ChangelogStatus.PUBLISHED,
                content={"summary": f"Pattern {i}"},
                generated_at=datetime.utcnow()
            )
            for i in range(8)  # 8 weeks of consistent data
        ]
        
        patterns = await history_manager._identify_patterns(entries)
        
        # Verify patterns
        assert len(patterns) > 0
        assert any(p['type'] == 'weekly_consistency' for p in patterns)
        
        weekly_pattern = next(p for p in patterns if p['type'] == 'weekly_consistency')
        assert 'description' in weekly_pattern
        assert 'confidence' in weekly_pattern
        assert weekly_pattern['confidence'] > 0

    @pytest.mark.asyncio
    async def test_detect_anomalies(self, history_manager):
        """Test anomaly detection in changelog data"""
        # Create entries with a gap
        entries = [
            ChangelogEntry(
                id="anomaly_1",
                team_id="anomaly_team",
                week_start_date=datetime(2024, 1, 1),
                week_end_date=datetime(2024, 1, 7),
                version=1,
                status=ChangelogStatus.PUBLISHED,
                content={"summary": "Before gap"},
                generated_at=datetime.utcnow()
            ),
            ChangelogEntry(
                id="anomaly_2",
                team_id="anomaly_team",
                week_start_date=datetime(2024, 2, 1),  # 3+ week gap
                week_end_date=datetime(2024, 2, 7),
                version=1,
                status=ChangelogStatus.PUBLISHED,
                content={"summary": "After gap"},
                generated_at=datetime.utcnow()
            )
        ]
        
        anomalies = await history_manager._detect_anomalies(entries, {})
        
        # Verify anomaly detection
        assert len(anomalies) > 0
        gap_anomaly = next((a for a in anomalies if a['type'] == 'publication_gap'), None)
        assert gap_anomaly is not None
        assert gap_anomaly['severity'] == 'medium'
        assert 'date_range' in gap_anomaly

    @pytest.mark.asyncio
    async def test_error_handling_in_trend_analysis(self, history_manager):
        """Test error handling in trend analysis"""
        # Mock retrieve method to raise exception
        async def mock_retrieve_error(filters):
            raise Exception("Database connection failed")
        
        history_manager.retrieve_changelog_history = mock_retrieve_error
        
        # Test trend analysis with error
        period = (datetime(2024, 1, 1), datetime(2024, 1, 31))
        result = await history_manager.analyze_changelog_trends("error_team", period)
        
        # Verify graceful error handling
        assert isinstance(result, TrendAnalysis)
        assert result.team_id == "error_team"
        assert result.period == period
        assert result.metrics == {}
        assert result.patterns == []
        assert result.predictions == {}
        assert result.anomalies == []

    @pytest.mark.asyncio
    async def test_export_with_no_data(self, history_manager):
        """Test export behavior when no data is found"""
        # Mock empty retrieve result
        history_manager.retrieve_changelog_history = AsyncMock(return_value=[])
        
        export_config = ExportConfig(
            format=ExportFormat.JSON,
            filters=HistoryFilters(team_ids=['empty_team'])
        )
        
        result = await history_manager.export_changelog_data(export_config)
        
        # Verify handling of empty dataset
        assert isinstance(result, ExportResult)
        assert result.success is False
        assert result.record_count == 0
        assert "no data found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_retention_with_legal_hold(self, history_manager, mock_supabase):
        """Test retention policy with legal hold"""
        mock_data = [
            {
                'id': 'legal_hold_entry',
                'team_id': 'legal_team',
                'week_start_date': (datetime.utcnow() - timedelta(days=500)).isoformat(),
                'week_end_date': (datetime.utcnow() - timedelta(days=494)).isoformat(),
                'version': 1,
                'status': 'published',
                'content': {'test': 'legal'},
                'generated_at': (datetime.utcnow() - timedelta(days=500)).isoformat()
            }
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_data
        
        # Test retention with legal hold
        retention_policy = RetentionPolicy(
            team_id="legal_team",
            archive_after_days=180,
            delete_after_days=365,
            legal_hold=True  # Should prevent any retention actions
        )
        
        result = await history_manager.manage_data_retention(retention_policy)
        
        # Verify legal hold prevents retention actions
        assert result.success is True
        assert result.processed_count == 1
        assert result.archived_count == 0  # Should be 0 due to legal hold
        assert result.deleted_count == 0   # Should be 0 due to legal hold


if __name__ == "__main__":
    pytest.main([__file__, "-v"])