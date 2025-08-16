"""
Notification deduplication system to prevent duplicate notifications.
Uses content hashing and database storage for duplicate detection and prevention.
"""

import hashlib
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from .channel_router import NotificationType


class DeduplicationStrategy(Enum):
    """Strategies for deduplication."""
    CONTENT_HASH = "content_hash"
    TYPE_AND_ID = "type_and_id"
    AUTHOR_AND_CONTENT = "author_and_content"
    CUSTOM_KEY = "custom_key"


@dataclass
class DeduplicationRule:
    """Rule for deduplication behavior."""
    notification_type: NotificationType
    strategy: DeduplicationStrategy
    timeframe_minutes: int = 60  # Default 1 hour
    custom_key_fields: List[str] = field(default_factory=list)
    ignore_fields: Set[str] = field(default_factory=set)
    enabled: bool = True


@dataclass
class NotificationRecord:
    """Record of a processed notification for deduplication."""
    id: str
    notification_hash: str
    notification_type: str
    channel: str
    team_id: str
    author: Optional[str]
    data: Dict[str, Any]
    sent_at: datetime
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DeduplicationResult:
    """Result of deduplication check."""
    is_duplicate: bool
    original_record: Optional[NotificationRecord] = None
    hash_value: str = ""
    reason: str = ""
    time_since_original: Optional[timedelta] = None


class NotificationDeduplicator:
    """System for preventing duplicate notifications."""
    
    def __init__(self, supabase_client=None):
        """Initialize notification deduplicator."""
        self.logger = logging.getLogger(__name__)
        self.supabase = supabase_client
        
        # In-memory cache for recent notifications (fallback if DB unavailable)
        self._memory_cache: Dict[str, NotificationRecord] = {}
        
        # Deduplication rules per notification type
        self._deduplication_rules: Dict[NotificationType, DeduplicationRule] = {}
        
        # Analytics
        self._stats = {
            "total_checks": 0,
            "duplicates_found": 0,
            "duplicates_prevented": 0,
            "cache_hits": 0,
            "db_hits": 0,
            "errors": 0
        }
        
        # Setup default rules
        self._setup_default_rules()
        
        self.logger.info("NotificationDeduplicator initialized")
    
    def _setup_default_rules(self) -> None:
        """Set up default deduplication rules for different notification types."""
        
        # PR notifications - deduplicate by PR number and action
        pr_types = [
            NotificationType.PR_NEW, NotificationType.PR_READY, NotificationType.PR_APPROVED,
            NotificationType.PR_CONFLICTS, NotificationType.PR_MERGED, NotificationType.PR_CLOSED
        ]
        
        for pr_type in pr_types:
            self._deduplication_rules[pr_type] = DeduplicationRule(
                notification_type=pr_type,
                strategy=DeduplicationStrategy.TYPE_AND_ID,
                timeframe_minutes=60,
                custom_key_fields=["number", "repository"],
                ignore_fields={"timestamp", "updated_at", "created_at"}
            )
        
        # JIRA notifications - deduplicate by ticket key and action
        jira_types = [
            NotificationType.JIRA_STATUS, NotificationType.JIRA_PRIORITY,
            NotificationType.JIRA_ASSIGNMENT, NotificationType.JIRA_COMMENT,
            NotificationType.JIRA_BLOCKER, NotificationType.JIRA_SPRINT
        ]
        
        for jira_type in jira_types:
            self._deduplication_rules[jira_type] = DeduplicationRule(
                notification_type=jira_type,
                strategy=DeduplicationStrategy.TYPE_AND_ID,
                timeframe_minutes=30,  # Shorter for JIRA as updates are more frequent
                custom_key_fields=["key", "project"],
                ignore_fields={"timestamp", "updated_at", "created_at", "comment_id"}
            )
        
        # Alert notifications - deduplicate by alert content
        alert_types = [
            NotificationType.ALERT_BUILD, NotificationType.ALERT_DEPLOYMENT,
            NotificationType.ALERT_SECURITY, NotificationType.ALERT_OUTAGE,
            NotificationType.ALERT_BUG
        ]
        
        for alert_type in alert_types:
            self._deduplication_rules[alert_type] = DeduplicationRule(
                notification_type=alert_type,
                strategy=DeduplicationStrategy.CONTENT_HASH,
                timeframe_minutes=120,  # Longer for alerts as they're less frequent
                ignore_fields={"timestamp", "created_at", "alert_id"}
            )
        
        # Standup notifications - deduplicate by date and team
        standup_types = [NotificationType.STANDUP_DAILY, NotificationType.STANDUP_SUMMARY]
        
        for standup_type in standup_types:
            self._deduplication_rules[standup_type] = DeduplicationRule(
                notification_type=standup_type,
                strategy=DeduplicationStrategy.CUSTOM_KEY,
                timeframe_minutes=1440,  # 24 hours for daily standups
                custom_key_fields=["date", "team"],
                ignore_fields={"timestamp", "created_at"}
            )
    
    async def check_duplicate(self, 
                            notification_type: NotificationType,
                            data: Dict[str, Any],
                            channel: str,
                            team_id: str,
                            author: Optional[str] = None) -> DeduplicationResult:
        """Check if notification is a duplicate."""
        
        self._stats["total_checks"] += 1
        
        try:
            # Get deduplication rule
            rule = self._deduplication_rules.get(notification_type)
            if not rule or not rule.enabled:
                return DeduplicationResult(is_duplicate=False, reason="no_rule_or_disabled")
            
            # Generate hash based on strategy
            notification_hash = self._generate_hash(data, rule, notification_type, author)
            
            # Check for duplicate
            duplicate_record = await self._find_duplicate(
                notification_hash, 
                notification_type, 
                rule.timeframe_minutes
            )
            
            if duplicate_record:
                self._stats["duplicates_found"] += 1
                time_diff = datetime.now() - duplicate_record.sent_at
                
                return DeduplicationResult(
                    is_duplicate=True,
                    original_record=duplicate_record,
                    hash_value=notification_hash,
                    reason=f"duplicate_found_within_{rule.timeframe_minutes}min",
                    time_since_original=time_diff
                )
            
            return DeduplicationResult(
                is_duplicate=False,
                hash_value=notification_hash,
                reason="no_duplicate_found"
            )
            
        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"Error checking duplicate: {e}")
            # Fail open - don't block notifications on deduplication errors
            return DeduplicationResult(is_duplicate=False, reason=f"error: {e}")
    
    def _generate_hash(self, 
                      data: Dict[str, Any], 
                      rule: DeduplicationRule,
                      notification_type: NotificationType,
                      author: Optional[str] = None) -> str:
        """Generate hash for deduplication based on strategy."""
        
        if rule.strategy == DeduplicationStrategy.CONTENT_HASH:
            return self._generate_content_hash(data, rule.ignore_fields)
        
        elif rule.strategy == DeduplicationStrategy.TYPE_AND_ID:
            return self._generate_type_id_hash(data, notification_type, rule.custom_key_fields)
        
        elif rule.strategy == DeduplicationStrategy.AUTHOR_AND_CONTENT:
            return self._generate_author_content_hash(data, author, rule.ignore_fields)
        
        elif rule.strategy == DeduplicationStrategy.CUSTOM_KEY:
            return self._generate_custom_key_hash(data, rule.custom_key_fields)
        
        else:
            # Fallback to content hash
            return self._generate_content_hash(data, rule.ignore_fields)
    
    def _generate_content_hash(self, data: Dict[str, Any], ignore_fields: Set[str]) -> str:
        """Generate hash based on content, ignoring specified fields."""
        # Create a clean copy without ignored fields
        clean_data = {k: v for k, v in data.items() if k not in ignore_fields}
        
        # Sort keys for consistent hashing
        content_string = json.dumps(clean_data, sort_keys=True, default=str)
        
        return hashlib.sha256(content_string.encode()).hexdigest()
    
    def _generate_type_id_hash(self, 
                              data: Dict[str, Any], 
                              notification_type: NotificationType,
                              key_fields: List[str]) -> str:
        """Generate hash based on notification type and key identifying fields."""
        hash_components = [notification_type.value]
        
        for field in key_fields:
            value = data.get(field, "")
            hash_components.append(str(value))
        
        content_string = "|".join(hash_components)
        return hashlib.sha256(content_string.encode()).hexdigest()
    
    def _generate_author_content_hash(self, 
                                    data: Dict[str, Any], 
                                    author: Optional[str],
                                    ignore_fields: Set[str]) -> str:
        """Generate hash based on author and content."""
        # Include author in hash
        hash_components = [str(author or "unknown")]
        
        # Add content hash
        content_hash = self._generate_content_hash(data, ignore_fields)
        hash_components.append(content_hash)
        
        content_string = "|".join(hash_components)
        return hashlib.sha256(content_string.encode()).hexdigest()
    
    def _generate_custom_key_hash(self, data: Dict[str, Any], key_fields: List[str]) -> str:
        """Generate hash based on custom key fields."""
        hash_components = []
        
        for field in key_fields:
            value = data.get(field, "")
            hash_components.append(str(value))
        
        content_string = "|".join(hash_components)
        return hashlib.sha256(content_string.encode()).hexdigest()
    
    async def _find_duplicate(self, 
                            notification_hash: str,
                            notification_type: NotificationType,
                            timeframe_minutes: int) -> Optional[NotificationRecord]:
        """Find duplicate notification in database or cache."""
        
        # Check memory cache first
        if notification_hash in self._memory_cache:
            cached_record = self._memory_cache[notification_hash]
            time_diff = datetime.now() - cached_record.sent_at
            
            if time_diff.total_seconds() / 60 <= timeframe_minutes:
                self._stats["cache_hits"] += 1
                return cached_record
            else:
                # Remove expired entry
                del self._memory_cache[notification_hash]
        
        # Check database if available
        if self.supabase:
            try:
                cutoff_time = datetime.now() - timedelta(minutes=timeframe_minutes)
                
                response = self.supabase.table("notification_log").select("*").eq(
                    "notification_hash", notification_hash
                ).eq(
                    "notification_type", notification_type.value
                ).gte(
                    "sent_at", cutoff_time.isoformat()
                ).order("sent_at", desc=True).limit(1).execute()
                
                if response.data:
                    record_data = response.data[0]
                    self._stats["db_hits"] += 1
                    
                    return NotificationRecord(
                        id=record_data["id"],
                        notification_hash=record_data["notification_hash"],
                        notification_type=record_data["notification_type"],
                        channel=record_data.get("channel", ""),
                        team_id=record_data.get("team_id", ""),
                        author=record_data.get("author"),
                        data=record_data.get("data", {}),
                        sent_at=datetime.fromisoformat(record_data["sent_at"]),
                        created_at=datetime.fromisoformat(record_data["created_at"])
                    )
                
            except Exception as e:
                self.logger.error(f"Error querying database for duplicates: {e}")
        
        return None
    
    async def record_notification(self,
                                notification_type: NotificationType,
                                data: Dict[str, Any],
                                channel: str,
                                team_id: str,
                                notification_hash: str,
                                author: Optional[str] = None) -> bool:
        """Record notification to prevent future duplicates."""
        
        try:
            current_time = datetime.now()
            
            # Create record
            record = NotificationRecord(
                id="",  # Will be set by database
                notification_hash=notification_hash,
                notification_type=notification_type.value,
                channel=channel,
                team_id=team_id,
                author=author,
                data=data,
                sent_at=current_time,
                created_at=current_time
            )
            
            # Store in memory cache
            self._memory_cache[notification_hash] = record
            
            # Store in database if available
            if self.supabase:
                try:
                    self.supabase.table("notification_log").insert({
                        "notification_hash": notification_hash,
                        "notification_type": notification_type.value,
                        "channel": channel,
                        "team_id": team_id,
                        "author": author,
                        "data": data,
                        "sent_at": current_time.isoformat(),
                        "created_at": current_time.isoformat()
                    }).execute()
                    
                except Exception as e:
                    self.logger.error(f"Error storing notification record in database: {e}")
                    # Continue with memory cache only
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error recording notification: {e}")
            return False
    
    async def cleanup_old_records(self, days_to_keep: int = 7) -> int:
        """Clean up old notification records."""
        
        try:
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            removed_count = 0
            
            # Clean memory cache
            expired_hashes = [
                hash_val for hash_val, record in self._memory_cache.items()
                if record.created_at < cutoff_time
            ]
            
            for hash_val in expired_hashes:
                del self._memory_cache[hash_val]
                removed_count += 1
            
            # Clean database if available
            if self.supabase:
                try:
                    response = self.supabase.table("notification_log").delete().lt(
                        "created_at", cutoff_time.isoformat()
                    ).execute()
                    
                    if hasattr(response, 'count') and response.count:
                        removed_count += response.count
                        
                except Exception as e:
                    self.logger.error(f"Error cleaning database records: {e}")
            
            self.logger.info(f"Cleaned up {removed_count} old notification records")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            return 0
    
    def add_deduplication_rule(self, rule: DeduplicationRule) -> None:
        """Add or update deduplication rule."""
        self._deduplication_rules[rule.notification_type] = rule
        self.logger.info(f"Added deduplication rule for {rule.notification_type.value}")
    
    def get_deduplication_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics and analytics."""
        total_checks = self._stats["total_checks"]
        
        return {
            **self._stats,
            "duplicate_rate": (self._stats["duplicates_found"] / total_checks * 100) if total_checks > 0 else 0,
            "prevention_effectiveness": (self._stats["duplicates_prevented"] / self._stats["duplicates_found"] * 100) if self._stats["duplicates_found"] > 0 else 0,
            "cache_hit_rate": (self._stats["cache_hits"] / total_checks * 100) if total_checks > 0 else 0,
            "memory_cache_size": len(self._memory_cache),
            "active_rules": len([r for r in self._deduplication_rules.values() if r.enabled]),
            "total_rules": len(self._deduplication_rules)
        }
    
    def get_rule_effectiveness(self) -> Dict[str, Dict[str, Any]]:
        """Get effectiveness statistics per rule."""
        # This would require more detailed tracking in a production system
        # For now, return basic rule information
        
        rule_stats = {}
        for notification_type, rule in self._deduplication_rules.items():
            rule_stats[notification_type.value] = {
                "strategy": rule.strategy.value,
                "timeframe_minutes": rule.timeframe_minutes,
                "enabled": rule.enabled,
                "custom_key_fields": rule.custom_key_fields,
                "ignore_fields": list(rule.ignore_fields)
            }
        
        return rule_stats
    
    async def test_deduplication(self, 
                               notification_type: NotificationType,
                               test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test deduplication with sample data."""
        
        results = {
            "total_tests": len(test_data),
            "duplicates_detected": 0,
            "unique_hashes": set(),
            "test_results": []
        }
        
        for i, data in enumerate(test_data):
            result = await self.check_duplicate(
                notification_type=notification_type,
                data=data,
                channel="#test",
                team_id="test_team"
            )
            
            test_result = {
                "test_index": i,
                "is_duplicate": result.is_duplicate,
                "hash": result.hash_value,
                "reason": result.reason
            }
            
            results["test_results"].append(test_result)
            results["unique_hashes"].add(result.hash_value)
            
            if result.is_duplicate:
                results["duplicates_detected"] += 1
        
        results["unique_hash_count"] = len(results["unique_hashes"])
        results["unique_hashes"] = list(results["unique_hashes"])  # Convert set to list for JSON
        
        return results


# Global deduplicator instance
default_deduplicator = NotificationDeduplicator()