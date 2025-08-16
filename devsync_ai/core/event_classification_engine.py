"""
Event Classification Engine for intelligent JIRA event analysis.

This module provides the EventClassificationEngine that analyzes JIRA events
to determine their urgency, significance, stakeholders, and classification
categories for intelligent routing and notification handling.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from .agent_hooks import (
    ProcessedEvent,
    EventCategory,
    UrgencyLevel,
    SignificanceLevel,
    EventClassification,
    Stakeholder
)


logger = logging.getLogger(__name__)


@dataclass
class ClassificationMetrics:
    """Metrics for classification performance tracking."""
    events_classified: int = 0
    classification_time_ms: float = 0.0
    urgency_distribution: Dict[str, int] = field(default_factory=dict)
    category_distribution: Dict[str, int] = field(default_factory=dict)
    stakeholder_extraction_count: int = 0


@dataclass
class BlockerPattern:
    """Represents a detected blocker pattern in an event."""
    pattern_type: str
    confidence: float
    evidence: List[str]
    location: str  # where the pattern was found (summary, description, etc.)


class EventClassificationEngine:
    """
    Intelligent engine for classifying JIRA events and determining their
    urgency, significance, stakeholders, and routing requirements.
    """
    
    # Event type to category mapping
    EVENT_CATEGORY_MAPPING = {
        'jira:issue_created': EventCategory.CREATION,
        'jira:issue_updated': EventCategory.STATUS_CHANGE,
        'jira:issue_deleted': EventCategory.STATUS_CHANGE,
        'jira:issue_assigned': EventCategory.ASSIGNMENT,
        'jira:issue_commented': EventCategory.COMMENT,
        'jira:issue_transitioned': EventCategory.TRANSITION,
        'jira:issue_priority_changed': EventCategory.PRIORITY_CHANGE,
    }
    
    # Blocker detection patterns
    BLOCKER_KEYWORDS = {
        'blocked', 'blocker', 'impediment', 'stuck', 'cannot proceed',
        'waiting for', 'dependency', 'issue with', 'on hold', 'paused',
        'blocked by', 'depends on', 'waiting on', 'need help', 'escalate',
        'urgent help', 'critical issue', 'production down', 'system down'
    }
    
    BLOCKING_STATUSES = {
        'blocked', 'impediment', 'on hold', 'waiting', 'paused', 'suspended',
        'blocked - waiting', 'waiting for approval', 'waiting for info'
    }
    
    # Priority mappings
    CRITICAL_PRIORITIES = {'critical', 'highest', 'blocker', 'p0', 'sev1'}
    HIGH_PRIORITIES = {'high', 'major', 'p1', 'sev2'}
    MEDIUM_PRIORITIES = {'medium', 'normal', 'p2', 'sev3'}
    LOW_PRIORITIES = {'low', 'minor', 'trivial', 'p3', 'p4', 'sev4', 'sev5'}
    
    # Assignment workload thresholds
    WORKLOAD_THRESHOLDS = {
        'overloaded': 8,
        'high_load': 5,
        'normal_load': 3
    }
    
    # Comment significance patterns
    URGENT_COMMENT_PATTERNS = [
        r'\b(urgent|asap|immediately|critical|emergency)\b',
        r'\b(production\s+down|system\s+down|outage)\b',
        r'\b(escalat|priorit|rush)\w*\b',
        r'\b(help\s+needed|need\s+help|assistance\s+required)\b',
        r'\b(blocked|stuck|cannot\s+proceed)\b'
    ]
    
    def __init__(self):
        """Initialize the Event Classification Engine."""
        self.metrics = ClassificationMetrics()
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.URGENT_COMMENT_PATTERNS
        ]
        logger.info("EventClassificationEngine initialized")
    
    async def classify_event(self, event: ProcessedEvent) -> EventClassification:
        """
        Classify a JIRA event with comprehensive analysis.
        
        Args:
            event: The processed JIRA event to classify
            
        Returns:
            Complete event classification with category, urgency, and significance
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Determine event category
            category = await self._classify_event_category(event)
            
            # Determine urgency level
            urgency = await self._determine_urgency(event, category)
            
            # Determine significance level
            significance = await self._determine_significance(event, category, urgency)
            
            # Extract stakeholders
            stakeholders = await self._extract_stakeholders(event)
            
            # Determine affected teams
            affected_teams = await self._determine_affected_teams(event)
            
            # Generate routing hints
            routing_hints = await self._generate_routing_hints(event, category, urgency)
            
            # Extract keywords
            keywords = await self._extract_keywords(event)
            
            # Create classification
            classification = EventClassification(
                category=category,
                urgency=urgency,
                significance=significance,
                affected_teams=affected_teams,
                routing_hints=routing_hints,
                keywords=keywords
            )
            
            # Update metrics
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self._update_metrics(classification, processing_time, len(stakeholders))
            
            logger.debug(
                f"Event classified: {event.event_id} -> "
                f"category={category.value}, urgency={urgency.value}, "
                f"significance={significance.value}, teams={len(affected_teams)}"
            )
            
            return classification
            
        except Exception as e:
            logger.error(f"Error classifying event {event.event_id}: {e}", exc_info=True)
            # Return default classification on error
            return EventClassification(
                category=EventCategory.STATUS_CHANGE,
                urgency=UrgencyLevel.LOW,
                significance=SignificanceLevel.MINOR,
                affected_teams=[event.project_key.lower()],
                routing_hints={'error': str(e)},
                keywords=['error']
            )
    
    async def _classify_event_category(self, event: ProcessedEvent) -> EventCategory:
        """
        Classify the event into an appropriate category.
        
        Args:
            event: The processed event to classify
            
        Returns:
            The determined event category
        """
        # Check for blocker conditions first (highest priority)
        if await self._is_blocker_event(event):
            return EventCategory.BLOCKER
        
        # Use direct mapping for known event types
        if event.event_type in self.EVENT_CATEGORY_MAPPING:
            base_category = self.EVENT_CATEGORY_MAPPING[event.event_type]
            
            # For issue_updated events, determine more specific category
            if event.event_type == 'jira:issue_updated':
                return await self._classify_update_event(event)
            
            return base_category
        
        # Default fallback
        return EventCategory.STATUS_CHANGE
    
    async def _is_blocker_event(self, event: ProcessedEvent) -> bool:
        """
        Check if this event indicates a blocking condition.
        
        Args:
            event: The event to check for blocker patterns
            
        Returns:
            True if the event indicates a blocker, False otherwise
        """
        fields = event.jira_event_data.get('fields', {})
        
        # Check current status
        status = fields.get('status', {})
        if isinstance(status, dict):
            status_name = status.get('name', '').lower()
            if any(blocked in status_name for blocked in self.BLOCKING_STATUSES):
                return True
        
        # Check labels for blocker keywords
        labels = fields.get('labels', [])
        for label in labels:
            label_str = str(label).lower()
            if any(keyword in label_str for keyword in self.BLOCKER_KEYWORDS):
                return True
        
        # Check summary for blocker keywords
        summary = fields.get('summary', '').lower()
        if any(keyword in summary for keyword in self.BLOCKER_KEYWORDS):
            return True
        
        # Check description for blocker keywords
        description = fields.get('description', '').lower()
        if any(keyword in description for keyword in self.BLOCKER_KEYWORDS):
            return True
        
        # Check for specific blocker patterns in comments (for comment events)
        if event.event_type == 'jira:issue_commented':
            comment = event.raw_payload.get('comment', {})
            comment_body = comment.get('body', '').lower()
            if any(keyword in comment_body for keyword in self.BLOCKER_KEYWORDS):
                return True
        
        # Check for transition to blocked status
        if event.event_type == 'jira:issue_transitioned':
            changelog = event.raw_payload.get('changelog', {})
            items = changelog.get('items', [])
            for item in items:
                if item.get('field') == 'status':
                    to_status = item.get('toString', '').lower()
                    if any(blocked in to_status for blocked in self.BLOCKING_STATUSES):
                        return True
        
        return False
    
    async def _classify_update_event(self, event: ProcessedEvent) -> EventCategory:
        """
        Classify an issue_updated event into more specific category.
        
        Args:
            event: The update event to classify
            
        Returns:
            More specific event category based on what was updated
        """
        changelog = event.raw_payload.get('changelog', {})
        items = changelog.get('items', [])
        
        for item in items:
            field = item.get('field', '').lower()
            
            if field == 'assignee':
                return EventCategory.ASSIGNMENT
            elif field == 'status':
                return EventCategory.TRANSITION
            elif field == 'priority':
                return EventCategory.PRIORITY_CHANGE
        
        # Default for updates
        return EventCategory.STATUS_CHANGE
    
    async def _determine_urgency(self, event: ProcessedEvent, category: EventCategory) -> UrgencyLevel:
        """
        Determine urgency level based on event data and category.
        
        Args:
            event: The event to analyze
            category: The event category
            
        Returns:
            Determined urgency level
        """
        fields = event.jira_event_data.get('fields', {})
        
        # Blocker events are always critical
        if category == EventCategory.BLOCKER:
            return UrgencyLevel.CRITICAL
        
        # Comment events with urgent patterns (check first for comments)
        if category == EventCategory.COMMENT:
            urgency = await self._analyze_comment_urgency(event)
            if urgency:
                return urgency
        
        # Check for urgent keywords in summary or description first (can override priority)
        summary = fields.get('summary', '').lower()
        description = fields.get('description', '').lower()
        
        urgent_keywords = {'urgent', 'critical', 'emergency', 'asap', 'immediately'}
        if any(keyword in summary or keyword in description for keyword in urgent_keywords):
            return UrgencyLevel.HIGH
        
        # Check for production-related keywords
        prod_keywords = {'production', 'prod', 'live', 'customer-facing'}
        if any(keyword in summary or keyword in description for keyword in prod_keywords):
            return UrgencyLevel.HIGH
        
        # Check priority field
        priority = fields.get('priority', {})
        if isinstance(priority, dict):
            priority_name = priority.get('name', '').lower()
            
            if priority_name in self.CRITICAL_PRIORITIES:
                return UrgencyLevel.CRITICAL
            elif priority_name in self.HIGH_PRIORITIES:
                return UrgencyLevel.HIGH
            elif priority_name in self.MEDIUM_PRIORITIES:
                return UrgencyLevel.MEDIUM
            elif priority_name in self.LOW_PRIORITIES:
                return UrgencyLevel.LOW
        
        # Assignment events - check workload
        if category == EventCategory.ASSIGNMENT:
            assignee = fields.get('assignee')
            if assignee and isinstance(assignee, dict):
                # This would typically check current workload from database
                # For now, return medium urgency for assignments
                return UrgencyLevel.MEDIUM
        
        # Default urgency based on category
        category_urgency_mapping = {
            EventCategory.CREATION: UrgencyLevel.LOW,
            EventCategory.STATUS_CHANGE: UrgencyLevel.LOW,
            EventCategory.TRANSITION: UrgencyLevel.MEDIUM,
            EventCategory.ASSIGNMENT: UrgencyLevel.MEDIUM,
            EventCategory.COMMENT: UrgencyLevel.LOW,
            EventCategory.PRIORITY_CHANGE: UrgencyLevel.MEDIUM,
        }
        
        return category_urgency_mapping.get(category, UrgencyLevel.LOW)
    
    async def _analyze_comment_urgency(self, event: ProcessedEvent) -> Optional[UrgencyLevel]:
        """
        Analyze comment content for urgency indicators.
        
        Args:
            event: The comment event to analyze
            
        Returns:
            Urgency level if urgent patterns found, None otherwise
        """
        if event.event_type != 'jira:issue_commented':
            return None
        
        comment = event.raw_payload.get('comment', {})
        comment_body = comment.get('body', '').lower()
        
        # Check for urgent patterns
        for pattern in self._compiled_patterns:
            if pattern.search(comment_body):
                return UrgencyLevel.HIGH
        
        return None
    
    async def _determine_significance(
        self, 
        event: ProcessedEvent, 
        category: EventCategory, 
        urgency: UrgencyLevel
    ) -> SignificanceLevel:
        """
        Determine significance level based on category and urgency.
        
        Args:
            event: The event to analyze
            category: Event category
            urgency: Event urgency level
            
        Returns:
            Determined significance level
        """
        # Critical urgency always means critical significance
        if urgency == UrgencyLevel.CRITICAL:
            return SignificanceLevel.CRITICAL
        
        # Blocker events are always major or critical
        if category == EventCategory.BLOCKER:
            return SignificanceLevel.CRITICAL
        
        # Check for high-impact combinations
        high_impact_categories = {
            EventCategory.ASSIGNMENT,
            EventCategory.COMMENT,
            EventCategory.PRIORITY_CHANGE
        }
        
        if category in high_impact_categories:
            if urgency == UrgencyLevel.HIGH:
                return SignificanceLevel.MAJOR
            elif urgency == UrgencyLevel.MEDIUM:
                return SignificanceLevel.MODERATE
            else:
                return SignificanceLevel.MINOR
        
        # Status changes and transitions
        if category in {EventCategory.STATUS_CHANGE, EventCategory.TRANSITION}:
            if urgency == UrgencyLevel.HIGH:
                return SignificanceLevel.MAJOR
            elif urgency == UrgencyLevel.LOW:
                return SignificanceLevel.MINOR
            else:
                return SignificanceLevel.MODERATE
        
        # Creation events
        if category == EventCategory.CREATION:
            if urgency == UrgencyLevel.HIGH:
                return SignificanceLevel.MAJOR
            else:
                return SignificanceLevel.MINOR
        
        # Default mapping based on urgency
        urgency_significance_mapping = {
            UrgencyLevel.HIGH: SignificanceLevel.MAJOR,
            UrgencyLevel.MEDIUM: SignificanceLevel.MODERATE,
            UrgencyLevel.LOW: SignificanceLevel.MINOR
        }
        
        return urgency_significance_mapping.get(urgency, SignificanceLevel.MINOR)
    
    async def _extract_stakeholders(self, event: ProcessedEvent) -> List[Stakeholder]:
        """
        Extract stakeholders from event data.
        
        Args:
            event: The event to extract stakeholders from
            
        Returns:
            List of identified stakeholders
        """
        stakeholders = []
        fields = event.jira_event_data.get('fields', {})
        
        # Add assignee
        assignee = fields.get('assignee')
        if assignee and isinstance(assignee, dict):
            stakeholders.append(Stakeholder(
                user_id=assignee.get('accountId', ''),
                display_name=assignee.get('displayName', ''),
                email=assignee.get('emailAddress'),
                role='assignee',
                team_id=event.project_key.lower()
            ))
        
        # Add reporter
        reporter = fields.get('reporter')
        if reporter and isinstance(reporter, dict):
            stakeholders.append(Stakeholder(
                user_id=reporter.get('accountId', ''),
                display_name=reporter.get('displayName', ''),
                email=reporter.get('emailAddress'),
                role='reporter',
                team_id=event.project_key.lower()
            ))
        
        # Add comment author for comment events
        if event.event_type == 'jira:issue_commented':
            comment = event.raw_payload.get('comment', {})
            author = comment.get('author')
            if author and isinstance(author, dict):
                stakeholders.append(Stakeholder(
                    user_id=author.get('accountId', ''),
                    display_name=author.get('displayName', ''),
                    email=author.get('emailAddress'),
                    role='commenter',
                    team_id=event.project_key.lower()
                ))
        
        # Add watchers if available
        watchers = fields.get('watches', {})
        if isinstance(watchers, dict) and watchers.get('watchCount', 0) > 0:
            # Note: Actual watcher details would need additional API call
            # For now, we just note that there are watchers
            pass
        
        # Add previous assignee for assignment changes
        if event.event_type == 'jira:issue_assigned':
            changelog = event.raw_payload.get('changelog', {})
            items = changelog.get('items', [])
            for item in items:
                if item.get('field') == 'assignee':
                    from_user = item.get('from')
                    if from_user:
                        stakeholders.append(Stakeholder(
                            user_id=from_user,
                            display_name=item.get('fromString', ''),
                            role='previous_assignee',
                            team_id=event.project_key.lower()
                        ))
        
        return stakeholders
    
    async def _determine_affected_teams(self, event: ProcessedEvent) -> List[str]:
        """
        Determine which teams are affected by this event.
        
        Args:
            event: The event to analyze
            
        Returns:
            List of affected team identifiers
        """
        teams = set()
        fields = event.jira_event_data.get('fields', {})
        
        # Primary team based on project
        teams.add(event.project_key.lower())
        
        # Add teams based on components
        components = fields.get('components', [])
        for component in components:
            if isinstance(component, dict) and component.get('name'):
                # Use component name as potential team identifier
                component_name = component['name'].lower().replace(' ', '-')
                teams.add(component_name)
        
        # Add teams based on labels
        labels = fields.get('labels', [])
        for label in labels:
            label_str = str(label).lower()
            if label_str.startswith('team-'):
                teams.add(label_str[5:])  # Remove 'team-' prefix
            elif label_str.startswith('squad-'):
                teams.add(label_str[6:])  # Remove 'squad-' prefix
        
        # Add teams based on fix versions (if they contain team info)
        fix_versions = fields.get('fixVersions', [])
        for version in fix_versions:
            if isinstance(version, dict) and version.get('name'):
                version_name = version['name'].lower()
                if 'team-' in version_name:
                    team_part = version_name.split('team-')[1].split('-')[0]
                    teams.add(team_part)
        
        return list(teams)
    
    async def _generate_routing_hints(
        self, 
        event: ProcessedEvent, 
        category: EventCategory, 
        urgency: UrgencyLevel
    ) -> Dict[str, Any]:
        """
        Generate routing hints for the event.
        
        Args:
            event: The event to generate hints for
            category: Event category
            urgency: Event urgency level
            
        Returns:
            Dictionary of routing hints
        """
        fields = event.jira_event_data.get('fields', {})
        
        hints = {
            'project': event.project_key,
            'ticket_key': event.ticket_key,
            'event_type': event.event_type,
            'category': category.value,
            'urgency': urgency.value
        }
        
        # Add issue type
        issue_type = fields.get('issuetype', {})
        if isinstance(issue_type, dict):
            hints['issue_type'] = issue_type.get('name')
            hints['is_subtask'] = issue_type.get('subtask', False)
        
        # Add priority
        priority = fields.get('priority', {})
        if isinstance(priority, dict):
            hints['priority'] = priority.get('name')
        
        # Add status
        status = fields.get('status', {})
        if isinstance(status, dict):
            hints['status'] = status.get('name')
            hints['status_category'] = status.get('statusCategory', {}).get('name')
        
        # Add assignee
        assignee = fields.get('assignee', {})
        if isinstance(assignee, dict):
            hints['assignee'] = assignee.get('displayName')
            hints['assignee_id'] = assignee.get('accountId')
        
        # Add components
        components = fields.get('components', [])
        if components:
            hints['components'] = [
                comp.get('name') for comp in components 
                if isinstance(comp, dict) and comp.get('name')
            ]
        
        # Add labels
        labels = fields.get('labels', [])
        if labels:
            hints['labels'] = [str(label) for label in labels]
        
        # Add special routing hints based on category
        if category == EventCategory.BLOCKER:
            hints['requires_immediate_attention'] = True
            hints['escalation_required'] = True
        
        if category == EventCategory.ASSIGNMENT:
            hints['workload_check_required'] = True
        
        if category == EventCategory.COMMENT:
            comment = event.raw_payload.get('comment', {})
            if comment:
                hints['comment_author'] = comment.get('author', {}).get('displayName')
                hints['comment_length'] = len(comment.get('body', ''))
        
        return hints
    
    async def _extract_keywords(self, event: ProcessedEvent) -> List[str]:
        """
        Extract relevant keywords from the event.
        
        Args:
            event: The event to extract keywords from
            
        Returns:
            List of extracted keywords
        """
        keywords = set()
        fields = event.jira_event_data.get('fields', {})
        
        # Add keywords from summary
        summary = fields.get('summary', '')
        if summary:
            # Simple keyword extraction (can be enhanced with NLP)
            summary_words = re.findall(r'\b\w{4,}\b', summary.lower())
            keywords.update(summary_words)
        
        # Add keywords from labels
        labels = fields.get('labels', [])
        keywords.update(str(label).lower() for label in labels)
        
        # Add status and priority as keywords
        status = fields.get('status', {})
        if isinstance(status, dict) and status.get('name'):
            keywords.add(status['name'].lower().replace(' ', '_'))
        
        priority = fields.get('priority', {})
        if isinstance(priority, dict) and priority.get('name'):
            keywords.add(priority['name'].lower())
        
        # Add issue type as keyword
        issue_type = fields.get('issuetype', {})
        if isinstance(issue_type, dict) and issue_type.get('name'):
            keywords.add(issue_type['name'].lower().replace(' ', '_'))
        
        # Add component keywords
        components = fields.get('components', [])
        for component in components:
            if isinstance(component, dict) and component.get('name'):
                comp_words = re.findall(r'\b\w{3,}\b', component['name'].lower())
                keywords.update(comp_words)
        
        # Add keywords from comment for comment events
        if event.event_type == 'jira:issue_commented':
            comment = event.raw_payload.get('comment', {})
            comment_body = comment.get('body', '')
            if comment_body:
                comment_words = re.findall(r'\b\w{4,}\b', comment_body.lower())
                keywords.update(comment_words[:10])  # Limit to first 10 words
        
        # Filter out common stop words
        stop_words = {
            'this', 'that', 'with', 'have', 'will', 'from', 'they', 'know',
            'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when',
            'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over',
            'such', 'take', 'than', 'them', 'well', 'were', 'should'
        }
        
        keywords = keywords - stop_words
        
        return list(keywords)[:20]  # Limit to 20 keywords
    
    def _update_metrics(
        self, 
        classification: EventClassification, 
        processing_time_ms: float,
        stakeholder_count: int
    ):
        """Update classification metrics."""
        self.metrics.events_classified += 1
        self.metrics.classification_time_ms += processing_time_ms
        self.metrics.stakeholder_extraction_count += stakeholder_count
        
        # Update urgency distribution
        urgency_key = classification.urgency.value
        self.metrics.urgency_distribution[urgency_key] = (
            self.metrics.urgency_distribution.get(urgency_key, 0) + 1
        )
        
        # Update category distribution
        category_key = classification.category.value
        self.metrics.category_distribution[category_key] = (
            self.metrics.category_distribution.get(category_key, 0) + 1
        )
    
    def get_metrics(self) -> ClassificationMetrics:
        """Get current classification metrics."""
        return self.metrics
    
    def reset_metrics(self):
        """Reset classification metrics."""
        self.metrics = ClassificationMetrics()
    
    async def detect_blocker_patterns(self, event: ProcessedEvent) -> List[BlockerPattern]:
        """
        Detect specific blocker patterns in an event.
        
        Args:
            event: The event to analyze for blocker patterns
            
        Returns:
            List of detected blocker patterns with confidence scores
        """
        patterns = []
        fields = event.jira_event_data.get('fields', {})
        
        # Check status-based blockers
        status = fields.get('status', {})
        if isinstance(status, dict):
            status_name = status.get('name', '').lower()
            for blocked_status in self.BLOCKING_STATUSES:
                if blocked_status in status_name:
                    patterns.append(BlockerPattern(
                        pattern_type='status_blocker',
                        confidence=0.9,
                        evidence=[f"Status: {status.get('name')}"],
                        location='status'
                    ))
        
        # Check keyword-based blockers in summary
        summary = fields.get('summary', '')
        for keyword in self.BLOCKER_KEYWORDS:
            if keyword in summary.lower():
                patterns.append(BlockerPattern(
                    pattern_type='keyword_blocker',
                    confidence=0.7,
                    evidence=[f"Keyword '{keyword}' in summary"],
                    location='summary'
                ))
        
        # Check keyword-based blockers in description
        description = fields.get('description', '')
        for keyword in self.BLOCKER_KEYWORDS:
            if keyword in description.lower():
                patterns.append(BlockerPattern(
                    pattern_type='keyword_blocker',
                    confidence=0.6,
                    evidence=[f"Keyword '{keyword}' in description"],
                    location='description'
                ))
        
        # Check label-based blockers
        labels = fields.get('labels', [])
        for label in labels:
            label_str = str(label).lower()
            if any(keyword in label_str for keyword in self.BLOCKER_KEYWORDS):
                patterns.append(BlockerPattern(
                    pattern_type='label_blocker',
                    confidence=0.8,
                    evidence=[f"Blocker keyword in label: {label}"],
                    location='labels'
                ))
        
        return patterns
    
    async def analyze_workload_impact(self, event: ProcessedEvent) -> Dict[str, Any]:
        """
        Analyze workload impact for assignment events.
        
        Args:
            event: The assignment event to analyze
            
        Returns:
            Workload impact analysis
        """
        if event.event_type != 'jira:issue_assigned':
            return {}
        
        fields = event.jira_event_data.get('fields', {})
        assignee = fields.get('assignee')
        
        if not assignee or not isinstance(assignee, dict):
            return {}
        
        assignee_id = assignee.get('accountId')
        assignee_name = assignee.get('displayName')
        
        # This would typically query the database for current workload
        # For now, return a placeholder analysis
        analysis = {
            'assignee_id': assignee_id,
            'assignee_name': assignee_name,
            'current_ticket_count': 0,  # Would be fetched from database
            'workload_level': 'unknown',
            'recommendation': 'Monitor workload',
            'team_capacity_impact': 'minimal'
        }
        
        return analysis