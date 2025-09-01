#!/usr/bin/env python3
"""
Changelog History Manager Demonstration Script

This script demonstrates the key functionality of the ChangelogHistoryManager
without requiring complex dependencies or configuration.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum


# Simplified data models for demonstration
class ChangelogStatus(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class ChangelogEntry:
    id: str
    team_id: str
    week_start_date: datetime
    week_end_date: datetime
    version: int
    status: ChangelogStatus
    content: Dict[str, Any]
    metadata: Dict[str, Any] = None
    generated_at: datetime = None
    published_at: datetime = None
    created_by: str = None
    tags: List[str] = None


@dataclass
class HistoryFilters:
    team_ids: List[str] = None
    date_range: tuple = None
    status: ChangelogStatus = None
    search_text: str = None
    tags: List[str] = None
    created_by: str = None
    limit: int = 50
    offset: int = 0


@dataclass
class TrendAnalysis:
    team_id: str
    period: tuple
    metrics: Dict[str, Any]
    patterns: List[Dict[str, Any]]
    predictions: Dict[str, Any]
    anomalies: List[Dict[str, Any]]


class ChangelogHistoryManagerDemo:
    """Demonstration version of ChangelogHistoryManager"""
    
    def __init__(self):
        self.data_store = []
        self.audit_trail = []
    
    async def store_changelog(self, changelog: ChangelogEntry) -> Dict[str, Any]:
        """Store a changelog entry"""
        try:
            # Set defaults
            if not changelog.generated_at:
                changelog.generated_at = datetime.utcnow()
            
            # Check for existing versions
            existing_versions = [
                entry for entry in self.data_store
                if entry.team_id == changelog.team_id and 
                   entry.week_start_date == changelog.week_start_date
            ]
            
            if existing_versions:
                changelog.version = max(entry.version for entry in existing_versions) + 1
            else:
                changelog.version = 1
            
            # Store the entry
            self.data_store.append(changelog)
            
            # Create audit trail
            self.audit_trail.append({
                'changelog_id': changelog.id,
                'action': 'CREATE',
                'timestamp': datetime.utcnow(),
                'user_id': changelog.created_by,
                'details': {'version': changelog.version}
            })
            
            return {
                'success': True,
                'changelog_id': changelog.id,
                'version': changelog.version,
                'message': f'Changelog stored successfully (version {changelog.version})'
            }
            
        except Exception as e:
            return {
                'success': False,
                'changelog_id': changelog.id,
                'version': 0,
                'message': 'Failed to store changelog',
                'errors': [str(e)]
            }
    
    async def retrieve_changelog_history(self, filters: HistoryFilters) -> List[ChangelogEntry]:
        """Retrieve changelog history with filtering"""
        results = self.data_store.copy()
        
        # Apply filters
        if filters.team_ids:
            results = [entry for entry in results if entry.team_id in filters.team_ids]
        
        if filters.date_range:
            start_date, end_date = filters.date_range
            results = [
                entry for entry in results
                if start_date <= entry.week_start_date <= end_date
            ]
        
        if filters.status:
            results = [entry for entry in results if entry.status == filters.status]
        
        if filters.search_text:
            results = [
                entry for entry in results
                if filters.search_text.lower() in json.dumps(entry.content).lower()
            ]
        
        if filters.tags:
            results = [
                entry for entry in results
                if entry.tags and any(tag in entry.tags for tag in filters.tags)
            ]
        
        if filters.created_by:
            results = [entry for entry in results if entry.created_by == filters.created_by]
        
        # Apply pagination
        start_idx = filters.offset
        end_idx = start_idx + filters.limit
        results = results[start_idx:end_idx]
        
        # Sort by date descending
        results.sort(key=lambda x: x.week_start_date, reverse=True)
        
        return results
    
    async def analyze_changelog_trends(self, team_id: str, period: tuple) -> TrendAnalysis:
        """Analyze changelog trends"""
        start_date, end_date = period
        
        # Get entries for the period
        entries = [
            entry for entry in self.data_store
            if entry.team_id == team_id and start_date <= entry.week_start_date <= end_date
        ]
        
        # Calculate metrics
        total_entries = len(entries)
        published_entries = len([e for e in entries if e.status == ChangelogStatus.PUBLISHED])
        publication_rate = published_entries / total_entries if total_entries > 0 else 0
        
        content_lengths = [len(json.dumps(e.content)) for e in entries]
        avg_content_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0
        
        metrics = {
            'total_entries': total_entries,
            'published_entries': published_entries,
            'publication_rate': publication_rate,
            'avg_content_length': avg_content_length,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
        
        # Identify patterns
        patterns = []
        if entries:
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
        
        # Generate predictions
        predictions = {}
        if len(entries) >= 4:
            recent_entries = sorted(entries, key=lambda x: x.week_start_date)[-4:]
            recent_count = len(recent_entries)
            predictions['next_week_entries'] = {
                'predicted_count': recent_count,
                'confidence': 0.6,
                'reasoning': 'Based on recent 4-week average'
            }
        
        # Detect anomalies
        anomalies = []
        if len(entries) > 1:
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
        
        return TrendAnalysis(
            team_id=team_id,
            period=period,
            metrics=metrics,
            patterns=patterns,
            predictions=predictions,
            anomalies=anomalies
        )
    
    async def export_changelog_data(self, format_type: str, filters: HistoryFilters) -> Dict[str, Any]:
        """Export changelog data"""
        try:
            entries = await self.retrieve_changelog_history(filters)
            
            if not entries:
                return {
                    'success': False,
                    'message': 'No data found for export',
                    'record_count': 0
                }
            
            # Generate export data
            export_data = []
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
                export_data.append(entry_data)
            
            # Simulate file creation
            export_content = json.dumps(export_data, indent=2)
            file_size = len(export_content.encode('utf-8'))
            
            return {
                'success': True,
                'export_id': f'export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}',
                'record_count': len(entries),
                'file_size': file_size,
                'format': format_type,
                'message': f'Export completed successfully ({format_type})'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': 'Export failed',
                'errors': [str(e)]
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics"""
        total_entries = len(self.data_store)
        teams = set(entry.team_id for entry in self.data_store)
        statuses = {}
        for entry in self.data_store:
            status = entry.status.value
            statuses[status] = statuses.get(status, 0) + 1
        
        return {
            'total_entries': total_entries,
            'unique_teams': len(teams),
            'teams': list(teams),
            'status_distribution': statuses,
            'audit_trail_entries': len(self.audit_trail)
        }


async def demonstrate_changelog_history_management():
    """Demonstrate the changelog history management functionality"""
    
    print("🚀 Changelog History Management Demonstration")
    print("=" * 60)
    
    # Initialize the manager
    manager = ChangelogHistoryManagerDemo()
    
    # Create sample changelog entries
    sample_entries = [
        ChangelogEntry(
            id="demo_1",
            team_id="engineering",
            week_start_date=datetime(2024, 1, 1),
            week_end_date=datetime(2024, 1, 7),
            version=1,
            status=ChangelogStatus.PUBLISHED,
            content={
                "summary": "Weekly engineering update",
                "features": ["New authentication system", "API rate limiting"],
                "bug_fixes": ["Fixed memory leak in data processor"],
                "improvements": ["Optimized database queries"]
            },
            metadata={"priority": "high", "complexity": 0.8},
            created_by="alice",
            tags=["feature", "security", "performance"]
        ),
        ChangelogEntry(
            id="demo_2",
            team_id="engineering",
            week_start_date=datetime(2024, 1, 8),
            week_end_date=datetime(2024, 1, 14),
            version=1,
            status=ChangelogStatus.PUBLISHED,
            content={
                "summary": "Bug fixes and improvements",
                "features": [],
                "bug_fixes": ["Fixed login redirect issue", "Resolved data sync problems"],
                "improvements": ["Enhanced error messages", "Updated documentation"]
            },
            metadata={"priority": "medium", "complexity": 0.4},
            created_by="bob",
            tags=["bugfix", "documentation"]
        ),
        ChangelogEntry(
            id="demo_3",
            team_id="product",
            week_start_date=datetime(2024, 1, 1),
            week_end_date=datetime(2024, 1, 7),
            version=1,
            status=ChangelogStatus.DRAFT,
            content={
                "summary": "Product roadmap updates",
                "features": ["New user onboarding flow", "Advanced analytics dashboard"],
                "bug_fixes": [],
                "improvements": ["Improved user experience"]
            },
            metadata={"priority": "high", "complexity": 0.9},
            created_by="carol",
            tags=["product", "ux", "analytics"]
        ),
        ChangelogEntry(
            id="demo_4",
            team_id="engineering",
            week_start_date=datetime(2024, 2, 1),  # Gap to test anomaly detection
            week_end_date=datetime(2024, 2, 7),
            version=1,
            status=ChangelogStatus.PUBLISHED,
            content={
                "summary": "Major feature release",
                "features": ["Real-time collaboration", "Advanced search"],
                "bug_fixes": ["Critical security fix"],
                "improvements": ["Performance optimizations"]
            },
            metadata={"priority": "critical", "complexity": 1.0},
            created_by="alice",
            tags=["feature", "security", "performance", "collaboration"]
        )
    ]
    
    # Store changelog entries
    print("\n📝 Storing Changelog Entries")
    print("-" * 30)
    
    for entry in sample_entries:
        result = await manager.store_changelog(entry)
        status = "✅" if result['success'] else "❌"
        print(f"{status} {entry.id}: {result['message']}")
    
    # Display current statistics
    print("\n📊 Current Statistics")
    print("-" * 20)
    stats = manager.get_statistics()
    print(f"Total entries: {stats['total_entries']}")
    print(f"Unique teams: {stats['unique_teams']}")
    print(f"Teams: {', '.join(stats['teams'])}")
    print(f"Status distribution: {stats['status_distribution']}")
    print(f"Audit trail entries: {stats['audit_trail_entries']}")
    
    # Test filtering and retrieval
    print("\n🔍 Testing Filters and Retrieval")
    print("-" * 35)
    
    # Filter by team
    engineering_filters = HistoryFilters(team_ids=["engineering"])
    engineering_entries = await manager.retrieve_changelog_history(engineering_filters)
    print(f"Engineering team entries: {len(engineering_entries)}")
    
    # Filter by status
    published_filters = HistoryFilters(status=ChangelogStatus.PUBLISHED)
    published_entries = await manager.retrieve_changelog_history(published_filters)
    print(f"Published entries: {len(published_entries)}")
    
    # Filter by tags
    security_filters = HistoryFilters(tags=["security"])
    security_entries = await manager.retrieve_changelog_history(security_filters)
    print(f"Security-related entries: {len(security_entries)}")
    
    # Text search
    search_filters = HistoryFilters(search_text="authentication")
    search_entries = await manager.retrieve_changelog_history(search_filters)
    print(f"Entries mentioning 'authentication': {len(search_entries)}")
    
    # Test trend analysis
    print("\n📈 Trend Analysis")
    print("-" * 17)
    
    period = (datetime(2024, 1, 1), datetime(2024, 2, 28))
    trend_analysis = await manager.analyze_changelog_trends("engineering", period)
    
    print(f"Team: {trend_analysis.team_id}")
    print(f"Period: {trend_analysis.period[0].strftime('%Y-%m-%d')} to {trend_analysis.period[1].strftime('%Y-%m-%d')}")
    print(f"Total entries: {trend_analysis.metrics['total_entries']}")
    print(f"Published entries: {trend_analysis.metrics['published_entries']}")
    print(f"Publication rate: {trend_analysis.metrics['publication_rate']:.1%}")
    print(f"Average content length: {trend_analysis.metrics['avg_content_length']:.0f} characters")
    
    if trend_analysis.patterns:
        print(f"\nPatterns identified:")
        for pattern in trend_analysis.patterns:
            print(f"  • {pattern['description']} (confidence: {pattern['confidence']:.1%})")
    
    if trend_analysis.predictions:
        print(f"\nPredictions:")
        for key, prediction in trend_analysis.predictions.items():
            print(f"  • {key}: {prediction['predicted_count']} (confidence: {prediction['confidence']:.1%})")
    
    if trend_analysis.anomalies:
        print(f"\nAnomalies detected:")
        for anomaly in trend_analysis.anomalies:
            print(f"  • {anomaly['description']} (severity: {anomaly['severity']})")
    
    # Test export functionality
    print("\n📤 Export Functionality")
    print("-" * 22)
    
    export_filters = HistoryFilters(team_ids=["engineering"], limit=10)
    export_result = await manager.export_changelog_data("json", export_filters)
    
    if export_result['success']:
        print(f"✅ Export successful:")
        print(f"   Export ID: {export_result['export_id']}")
        print(f"   Records: {export_result['record_count']}")
        print(f"   File size: {export_result['file_size']} bytes")
        print(f"   Format: {export_result['format']}")
    else:
        print(f"❌ Export failed: {export_result['message']}")
    
    # Test version management
    print("\n🔄 Version Management")
    print("-" * 21)
    
    # Create a new version of an existing changelog
    updated_entry = ChangelogEntry(
        id="demo_1_v2",
        team_id="engineering",
        week_start_date=datetime(2024, 1, 1),  # Same week as demo_1
        week_end_date=datetime(2024, 1, 7),
        version=1,  # Will be incremented automatically
        status=ChangelogStatus.PUBLISHED,
        content={
            "summary": "Updated weekly engineering update",
            "features": ["New authentication system", "API rate limiting", "Enhanced security"],
            "bug_fixes": ["Fixed memory leak in data processor", "Resolved edge case in auth"],
            "improvements": ["Optimized database queries", "Improved error handling"]
        },
        metadata={"priority": "high", "complexity": 0.9, "updated": True},
        created_by="alice",
        tags=["feature", "security", "performance", "update"]
    )
    
    version_result = await manager.store_changelog(updated_entry)
    print(f"✅ Updated entry stored as version {version_result['version']}")
    
    # Show final statistics
    print("\n📊 Final Statistics")
    print("-" * 18)
    final_stats = manager.get_statistics()
    print(f"Total entries: {final_stats['total_entries']}")
    print(f"Status distribution: {final_stats['status_distribution']}")
    print(f"Audit trail entries: {final_stats['audit_trail_entries']}")
    
    print("\n✨ Demonstration completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demonstrate_changelog_history_management())