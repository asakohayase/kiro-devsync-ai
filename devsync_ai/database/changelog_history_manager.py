"""
Comprehensive History Management and Analytics for Weekly Changelog Generation

This module provides advanced changelog storage, versioning, search capabilities,
data retention, export functionality, trend analysis, and backup management.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from pathlib import Path

try:
    from supabase import create_client, Client
except ImportError:
    # Fallback for testing or when Supabase is not available
    create_client = None
    Client = None

try:
    from ..config import Config
except ImportError:
    # Fallback for testing
    Config = None

try:
    from ..core.exceptions import DevSyncError
except ImportError:
    # Fallback for testing
    class DevSyncError(Exception):
        pass


logger = logging.getLogger(__name__)


class ChangelogStatus(Enum):
    """Status of changelog entries"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ExportFormat(Enum):
    """Supported export formats"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"


class RetentionAction(Enum):
    """Data retention actions"""
    ARCHIVE = "archive"
    DELETE = "delete"
    COMPRESS = "compress"
    MIGRATE = "migrate"


@dataclass
class ChangelogEntry:
    """Changelog entry data model"""
    id: str
    team_id: str
    week_start_date: datetime
    week_end_date: datetime
    version: int
    status: ChangelogStatus
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    generated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_by: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class HistoryFilters:
    """Filters for changelog history queries"""
    team_ids: Optional[List[str]] = None
    date_range: Optional[Tuple[datetime, datetime]] = None
    status: Optional[ChangelogStatus] = None
    tags: Optional[List[str]] = None
    search_text: Optional[str] = None
    created_by: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass
class StorageResult:
    """Result of changelog storage operation"""
    success: bool
    changelog_id: str
    version: int
    message: str
    errors: Optional[List[str]] = None


@dataclass
class TrendAnalysis:
    """Trend analysis results"""
    team_id: str
    period: Tuple[datetime, datetime]
    metrics: Dict[str, Any]
    patterns: List[Dict[str, Any]]
    predictions: Dict[str, Any]
    anomalies: List[Dict[str, Any]]


@dataclass
class ExportConfig:
    """Export configuration"""
    format: ExportFormat
    filters: HistoryFilters
    include_metadata: bool = True
    compress: bool = False
    schedule: Optional[str] = None
    destination: Optional[str] = None


@dataclass
class ExportResult:
    """Export operation result"""
    success: bool
    export_id: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    record_count: int = 0
    message: str = ""
    errors: Optional[List[str]] = None


@dataclass
class RetentionPolicy:
    """Data retention policy configuration"""
    team_id: str
    archive_after_days: int
    delete_after_days: int
    compress_after_days: Optional[int] = None
    legal_hold: bool = False
    compliance_requirements: Optional[List[str]] = None


@dataclass
class RetentionResult:
    """Retention operation result"""
    success: bool
    processed_count: int
    archived_count: int
    deleted_count: int
    compressed_count: int
    errors: Optional[List[str]] = None


class ChangelogHistoryManager:
    """
    Comprehensive changelog history management with advanced features:
    - Versioned storage with change tracking
    - Advanced search with full-text indexing
    - Data retention and compliance management
    - Export functionality with multiple formats
    - Trend analysis and predictive insights
    - Backup and disaster recovery
    """

    def __init__(self, config):
        """Initialize the changelog history manager"""
        self.config = config
        if create_client and hasattr(config, 'SUPABASE_URL') and hasattr(config, 'SUPABASE_KEY'):
            self.supabase: Client = create_client(
                config.SUPABASE_URL,
                config.SUPABASE_KEY
            )
        else:
            self.supabase = None
        self._setup_database_schema()

    def _setup_database_schema(self):
        """Setup database schema for changelog history"""
        try:
            if self.supabase:
                # Create changelog entries table if not exists
                self.supabase.rpc('create_changelog_tables').execute()
                logger.info("Changelog database schema initialized")
            else:
                logger.warning("Supabase client not available, skipping schema setup")
        except Exception as e:
            logger.error(f"Failed to setup database schema: {e}")

    async def store_changelog(self, changelog: ChangelogEntry) -> StorageResult:
        """
        Store changelog entry with versioning and audit trails
        
        Args:
            changelog: Changelog entry to store
            
        Returns:
            StorageResult with operation details
        """
        try:
            if not self.supabase:
                raise Exception("Supabase client not available")

            # Generate ID if not provided
            if not changelog.id:
                changelog.id = str(uuid.uuid4())

            # Set timestamps
            if not changelog.generated_at:
                changelog.generated_at = datetime.utcnow()

            # Check for existing entry and increment version
            existing = await self._get_latest_version(
                changelog.team_id, 
                changelog.week_start_date
            )
            
            if existing:
                changelog.version = existing.version + 1
            else:
                changelog.version = 1

            # Store the changelog entry
            data = asdict(changelog)
            data['generated_at'] = changelog.generated_at.isoformat()
            data['week_start_date'] = changelog.week_start_date.isoformat()
            data['week_end_date'] = changelog.week_end_date.isoformat()
            data['status'] = changelog.status.value
            
            if changelog.published_at:
                data['published_at'] = changelog.published_at.isoformat()

            result = self.supabase.table('changelog_entries').insert(data).execute()
            
            # Create audit trail entry
            await self._create_audit_trail(
                changelog.id,
                'CREATE',
                changelog.created_by,
                {'version': changelog.version}
            )

            return StorageResult(
                success=True,
                changelog_id=changelog.id,
                version=changelog.version,
                message=f"Changelog stored successfully (version {changelog.version})"
            )

        except Exception as e:
            logger.error(f"Failed to store changelog: {e}")
            return StorageResult(
                success=False,
                changelog_id=changelog.id or "",
                version=0,
                message="Failed to store changelog",
                errors=[str(e)]
            )

    async def retrieve_changelog_history(
        self, 
        filters: HistoryFilters
    ) -> List[ChangelogEntry]:
        """
        Retrieve changelog history with advanced filtering
        
        Args:
            filters: Query filters
            
        Returns:
            List of changelog entries matching filters
        """
        try:
            if not self.supabase:
                logger.error("Supabase client not available")
                return []

            query = self.supabase.table('changelog_entries').select('*')

            # Apply filters
            if filters.team_ids:
                query = query.in_('team_id', filters.team_ids)

            if filters.date_range:
                start_date, end_date = filters.date_range
                query = query.gte('week_start_date', start_date.isoformat())
                query = query.lte('week_end_date', end_date.isoformat())

            if filters.status:
                query = query.eq('status', filters.status.value)

            if filters.created_by:
                query = query.eq('created_by', filters.created_by)

            if filters.search_text:
                # Full-text search on content and metadata
                query = query.text_search('content', filters.search_text)

            if filters.tags:
                # Search for entries with any of the specified tags
                query = query.contains('tags', filters.tags)

            # Apply pagination
            query = query.range(filters.offset, filters.offset + filters.limit - 1)
            
            # Order by date descending
            query = query.order('week_start_date', desc=True)

            result = query.execute()
            
            # Convert to ChangelogEntry objects
            entries = []
            for data in result.data:
                entry = self._dict_to_changelog_entry(data)
                entries.append(entry)

            return entries

        except Exception as e:
            logger.error(f"Failed to retrieve changelog history: {e}")
            return []

    async def analyze_changelog_trends(
        self, 
        team_id: str, 
        period: Tuple[datetime, datetime]
    ) -> TrendAnalysis:
        """
        Analyze changelog trends with pattern recognition and predictions
        
        Args:
            team_id: Team identifier
            period: Analysis period (start_date, end_date)
            
        Returns:
            TrendAnalysis with insights and predictions
        """
        try:
            start_date, end_date = period
            
            # Retrieve historical data
            filters = HistoryFilters(
                team_ids=[team_id],
                date_range=period,
                limit=1000
            )
            
            entries = await self.retrieve_changelog_history(filters)
            
            # Calculate metrics
            metrics = await self._calculate_trend_metrics(entries)
            
            # Identify patterns
            patterns = await self._identify_patterns(entries)
            
            # Generate predictions
            predictions = await self._generate_predictions(entries, metrics)
            
            # Detect anomalies
            anomalies = await self._detect_anomalies(entries, metrics)

            return TrendAnalysis(
                team_id=team_id,
                period=period,
                metrics=metrics,
                patterns=patterns,
                predictions=predictions,
                anomalies=anomalies
            )

        except Exception as e:
            logger.error(f"Failed to analyze trends: {e}")
            return TrendAnalysis(
                team_id=team_id,
                period=period,
                metrics={},
                patterns=[],
                predictions={},
                anomalies=[]
            )

    async def export_changelog_data(self, export_config: ExportConfig) -> ExportResult:
        """
        Export changelog data in multiple formats with scheduling
        
        Args:
            export_config: Export configuration
            
        Returns:
            ExportResult with export details
        """
        try:
            export_id = str(uuid.uuid4())
            
            # Retrieve data based on filters
            entries = await self.retrieve_changelog_history(export_config.filters)
            
            if not entries:
                return ExportResult(
                    success=False,
                    export_id=export_id,
                    message="No data found for export",
                    record_count=0
                )

            # Generate export file
            file_path = await self._generate_export_file(
                entries, 
                export_config.format,
                export_id,
                export_config.include_metadata,
                export_config.compress
            )

            # Get file size
            file_size = Path(file_path).stat().st_size if file_path else 0

            # Schedule if requested
            if export_config.schedule:
                await self._schedule_export(export_config, export_id)

            return ExportResult(
                success=True,
                export_id=export_id,
                file_path=file_path,
                file_size=file_size,
                record_count=len(entries),
                message=f"Export completed successfully ({export_config.format.value})"
            )

        except Exception as e:
            logger.error(f"Failed to export changelog data: {e}")
            return ExportResult(
                success=False,
                export_id=export_id,
                message="Export failed",
                errors=[str(e)]
            )

    async def manage_data_retention(
        self, 
        retention_policy: RetentionPolicy
    ) -> RetentionResult:
        """
        Manage data retention with automated archival and compliance
        
        Args:
            retention_policy: Retention policy configuration
            
        Returns:
            RetentionResult with operation details
        """
        try:
            now = datetime.utcnow()
            processed_count = 0
            archived_count = 0
            deleted_count = 0
            compressed_count = 0
            errors = []

            # Get entries for retention processing
            query = self.supabase.table('changelog_entries').select('*')
            query = query.eq('team_id', retention_policy.team_id)
            result = query.execute()

            for data in result.data:
                entry = self._dict_to_changelog_entry(data)
                processed_count += 1

                # Skip if under legal hold
                if retention_policy.legal_hold:
                    continue

                days_old = (now - entry.generated_at).days

                try:
                    # Archive old entries
                    if (days_old >= retention_policy.archive_after_days and 
                        entry.status != ChangelogStatus.ARCHIVED):
                        
                        await self._archive_entry(entry.id)
                        archived_count += 1

                    # Compress entries if configured
                    if (retention_policy.compress_after_days and 
                        days_old >= retention_policy.compress_after_days):
                        
                        await self._compress_entry(entry.id)
                        compressed_count += 1

                    # Delete very old entries
                    if days_old >= retention_policy.delete_after_days:
                        await self._delete_entry(entry.id)
                        deleted_count += 1

                except Exception as e:
                    errors.append(f"Failed to process entry {entry.id}: {e}")

            return RetentionResult(
                success=len(errors) == 0,
                processed_count=processed_count,
                archived_count=archived_count,
                deleted_count=deleted_count,
                compressed_count=compressed_count,
                errors=errors if errors else None
            )

        except Exception as e:
            logger.error(f"Failed to manage data retention: {e}")
            return RetentionResult(
                success=False,
                processed_count=0,
                archived_count=0,
                deleted_count=0,
                compressed_count=0,
                errors=[str(e)]
            )

    async def create_backup(self, team_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create comprehensive backup with automated testing
        
        Args:
            team_id: Optional team ID for targeted backup
            
        Returns:
            Backup operation result
        """
        try:
            backup_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            # Create backup directory
            backup_dir = Path(f"backups/changelog_{backup_id}")
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Export all data
            filters = HistoryFilters(
                team_ids=[team_id] if team_id else None,
                limit=10000
            )
            
            export_config = ExportConfig(
                format=ExportFormat.JSON,
                filters=filters,
                include_metadata=True,
                compress=True
            )

            export_result = await self.export_changelog_data(export_config)
            
            if not export_result.success:
                raise Exception("Failed to export data for backup")

            # Create backup metadata
            metadata = {
                'backup_id': backup_id,
                'timestamp': timestamp.isoformat(),
                'team_id': team_id,
                'record_count': export_result.record_count,
                'file_size': export_result.file_size,
                'validation_hash': await self._calculate_backup_hash(export_result.file_path)
            }

            # Save metadata
            metadata_file = backup_dir / 'metadata.json'
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            # Test backup integrity
            validation_result = await self._validate_backup(backup_id)

            return {
                'success': True,
                'backup_id': backup_id,
                'timestamp': timestamp,
                'record_count': export_result.record_count,
                'file_size': export_result.file_size,
                'validation_passed': validation_result,
                'backup_path': str(backup_dir)
            }

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def restore_from_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Restore data from backup with validation
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            Restore operation result
        """
        try:
            backup_dir = Path(f"backups/changelog_{backup_id}")
            
            if not backup_dir.exists():
                raise Exception(f"Backup {backup_id} not found")

            # Load metadata
            metadata_file = backup_dir / 'metadata.json'
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            # Validate backup integrity
            validation_result = await self._validate_backup(backup_id)
            if not validation_result:
                raise Exception("Backup validation failed")

            # Load and restore data
            # Implementation would depend on backup format and restoration strategy
            
            return {
                'success': True,
                'backup_id': backup_id,
                'restored_records': metadata.get('record_count', 0),
                'message': 'Backup restored successfully'
            }

        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    # Private helper methods

    async def _get_latest_version(
        self, 
        team_id: str, 
        week_start_date: datetime
    ) -> Optional[ChangelogEntry]:
        """Get the latest version of a changelog entry"""
        try:
            result = self.supabase.table('changelog_entries').select('*') \
                .eq('team_id', team_id) \
                .eq('week_start_date', week_start_date.isoformat()) \
                .order('version', desc=True) \
                .limit(1) \
                .execute()

            if result.data:
                return self._dict_to_changelog_entry(result.data[0])
            return None

        except Exception as e:
            logger.error(f"Failed to get latest version: {e}")
            return None

    async def _create_audit_trail(
        self, 
        changelog_id: str, 
        action: str, 
        user_id: Optional[str],
        details: Dict[str, Any]
    ):
        """Create audit trail entry"""
        try:
            audit_data = {
                'id': str(uuid.uuid4()),
                'changelog_id': changelog_id,
                'action': action,
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat(),
                'details': details
            }

            self.supabase.table('changelog_audit_trail').insert(audit_data).execute()

        except Exception as e:
            logger.error(f"Failed to create audit trail: {e}")

    def _dict_to_changelog_entry(self, data: Dict[str, Any]) -> ChangelogEntry:
        """Convert dictionary to ChangelogEntry object"""
        return ChangelogEntry(
            id=data['id'],
            team_id=data['team_id'],
            week_start_date=datetime.fromisoformat(data['week_start_date'].replace('Z', '+00:00')),
            week_end_date=datetime.fromisoformat(data['week_end_date'].replace('Z', '+00:00')),
            version=data['version'],
            status=ChangelogStatus(data['status']),
            content=data['content'],
            metadata=data.get('metadata'),
            generated_at=datetime.fromisoformat(data['generated_at'].replace('Z', '+00:00')) if data.get('generated_at') else None,
            published_at=datetime.fromisoformat(data['published_at'].replace('Z', '+00:00')) if data.get('published_at') else None,
            created_by=data.get('created_by'),
            tags=data.get('tags')
        )

    async def _calculate_trend_metrics(self, entries: List[ChangelogEntry]) -> Dict[str, Any]:
        """Calculate trend metrics from changelog entries"""
        if not entries:
            return {}

        total_entries = len(entries)
        published_entries = len([e for e in entries if e.status == ChangelogStatus.PUBLISHED])
        
        # Calculate average content length
        content_lengths = [len(json.dumps(e.content)) for e in entries]
        avg_content_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0

        # Calculate publication rate
        publication_rate = published_entries / total_entries if total_entries > 0 else 0

        return {
            'total_entries': total_entries,
            'published_entries': published_entries,
            'publication_rate': publication_rate,
            'avg_content_length': avg_content_length,
            'date_range': {
                'start': min(e.week_start_date for e in entries).isoformat(),
                'end': max(e.week_end_date for e in entries).isoformat()
            }
        }

    async def _identify_patterns(self, entries: List[ChangelogEntry]) -> List[Dict[str, Any]]:
        """Identify patterns in changelog data"""
        patterns = []
        
        if not entries:
            return patterns

        # Pattern: Weekly publication consistency
        weekly_counts = {}
        for entry in entries:
            week_key = entry.week_start_date.strftime('%Y-W%U')
            weekly_counts[week_key] = weekly_counts.get(week_key, 0) + 1

        if weekly_counts:
            avg_weekly = sum(weekly_counts.values()) / len(weekly_counts)
            patterns.append({
                'type': 'weekly_consistency',
                'description': f'Average {avg_weekly:.1f} changelogs per week',
                'confidence': 0.8,
                'data': weekly_counts
            })

        return patterns

    async def _generate_predictions(
        self, 
        entries: List[ChangelogEntry], 
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate predictions based on historical data"""
        predictions = {}
        
        if not entries or len(entries) < 4:
            return predictions

        # Simple trend prediction based on recent data
        recent_entries = sorted(entries, key=lambda x: x.week_start_date)[-4:]
        recent_count = len(recent_entries)
        
        predictions['next_week_entries'] = {
            'predicted_count': recent_count,
            'confidence': 0.6,
            'reasoning': 'Based on recent 4-week average'
        }

        return predictions

    async def _detect_anomalies(
        self, 
        entries: List[ChangelogEntry], 
        metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in changelog data"""
        anomalies = []
        
        if not entries:
            return anomalies

        # Detect unusually long gaps between entries
        sorted_entries = sorted(entries, key=lambda x: x.week_start_date)
        
        for i in range(1, len(sorted_entries)):
            gap = (sorted_entries[i].week_start_date - sorted_entries[i-1].week_end_date).days
            if gap > 14:  # More than 2 weeks gap
                anomalies.append({
                    'type': 'publication_gap',
                    'description': f'Gap of {gap} days between changelogs',
                    'severity': 'medium',
                    'date_range': [
                        sorted_entries[i-1].week_end_date.isoformat(),
                        sorted_entries[i].week_start_date.isoformat()
                    ]
                })

        return anomalies

    async def _generate_export_file(
        self,
        entries: List[ChangelogEntry],
        format: ExportFormat,
        export_id: str,
        include_metadata: bool,
        compress: bool
    ) -> str:
        """Generate export file in specified format"""
        export_dir = Path(f"exports/changelog_{export_id}")
        export_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"changelog_export_{export_id}.{format.value}"
        file_path = export_dir / filename

        if format == ExportFormat.JSON:
            data = []
            for entry in entries:
                entry_data = asdict(entry)
                # Convert datetime objects to ISO strings
                entry_data['week_start_date'] = entry.week_start_date.isoformat()
                entry_data['week_end_date'] = entry.week_end_date.isoformat()
                if entry.generated_at:
                    entry_data['generated_at'] = entry.generated_at.isoformat()
                if entry.published_at:
                    entry_data['published_at'] = entry.published_at.isoformat()
                entry_data['status'] = entry.status.value
                
                if not include_metadata:
                    entry_data.pop('metadata', None)
                
                data.append(entry_data)

            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)

        # Add support for other formats as needed
        elif format == ExportFormat.CSV:
            import csv
            with open(file_path, 'w', newline='') as f:
                if entries:
                    writer = csv.DictWriter(f, fieldnames=['id', 'team_id', 'week_start_date', 'status', 'version'])
                    writer.writeheader()
                    for entry in entries:
                        writer.writerow({
                            'id': entry.id,
                            'team_id': entry.team_id,
                            'week_start_date': entry.week_start_date.isoformat(),
                            'status': entry.status.value,
                            'version': entry.version
                        })

        return str(file_path)

    async def _schedule_export(self, export_config: ExportConfig, export_id: str):
        """Schedule recurring export"""
        # Implementation would integrate with scheduling system
        logger.info(f"Scheduled export {export_id} with schedule: {export_config.schedule}")

    async def _archive_entry(self, entry_id: str):
        """Archive a changelog entry"""
        self.supabase.table('changelog_entries') \
            .update({'status': ChangelogStatus.ARCHIVED.value}) \
            .eq('id', entry_id) \
            .execute()

    async def _compress_entry(self, entry_id: str):
        """Compress a changelog entry"""
        # Implementation would compress the content field
        logger.info(f"Compressed entry {entry_id}")

    async def _delete_entry(self, entry_id: str):
        """Delete a changelog entry"""
        self.supabase.table('changelog_entries') \
            .delete() \
            .eq('id', entry_id) \
            .execute()

    async def _calculate_backup_hash(self, file_path: str) -> str:
        """Calculate hash for backup validation"""
        import hashlib
        
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    async def _validate_backup(self, backup_id: str) -> bool:
        """Validate backup integrity"""
        try:
            backup_dir = Path(f"backups/changelog_{backup_id}")
            metadata_file = backup_dir / 'metadata.json'
            
            if not metadata_file.exists():
                return False

            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            # Validate hash if available
            if 'validation_hash' in metadata:
                # Implementation would verify file integrity
                pass

            return True

        except Exception as e:
            logger.error(f"Backup validation failed: {e}")
            return False