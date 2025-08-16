"""
JIRA Event Data Processors for Agent Hooks.

This module provides specialized processors for different types of JIRA webhook events,
extracting relevant data and enriching events with context and analysis.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .agent_hooks import ProcessedEvent, EnrichedEvent, EventCategory, UrgencyLevel, SignificanceLevel


logger = logging.getLogger(__name__)


class ChangeSignificance(Enum):
    """Significance levels for field changes."""
    TRIVIAL = "trivial"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class FieldChange:
    """Represents a change to a JIRA field."""
    field_name: str
    old_value: Any
    new_value: Any
    significance: ChangeSignificance
    change_type: str  # 'added', 'removed', 'modified'


@dataclass
class WorkloadAnalysis:
    """Analysis of team member workload."""
    assignee: str
    current_ticket_count: int
    total_story_points: int
    overloaded: bool
    capacity_percentage: float
    recent_assignments: int  # Assignments in last 7 days


@dataclass
class StatusTransitionAnalysis:
    """Analysis of status transition patterns."""
    from_status: str
    to_status: str
    transition_time: Optional[timedelta]
    is_backward_transition: bool
    is_blocked_transition: bool
    bottleneck_indicator: bool
    typical_duration: Optional[timedelta]


@dataclass
class CommentAnalysis:
    """Analysis of JIRA comment content."""
    author: str
    content_preview: str
    mentions: List[str]
    contains_blocker_keywords: bool
    contains_decision_keywords: bool
    contains_question_keywords: bool
    urgency_indicators: List[str]
    significance: SignificanceLevel


class JiraEventProcessor(ABC):
    """Base class for JIRA event processors."""
    
    def __init__(self):
        """Initialize the processor."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def can_process(self, event: ProcessedEvent) -> bool:
        """
        Check if this processor can handle the given event.
        
        Args:
            event: The processed event to check
            
        Returns:
            True if this processor can handle the event
        """
        pass
    
    @abstractmethod
    async def process_event(self, event: ProcessedEvent) -> Dict[str, Any]:
        """
        Process the event and return enrichment data.
        
        Args:
            event: The processed event to enrich
            
        Returns:
            Dictionary containing enrichment data
        """
        pass
    
    def _extract_field_value(self, fields: Dict[str, Any], field_path: str, default: Any = None) -> Any:
        """
        Extract a field value using dot notation path.
        
        Args:
            fields: Fields dictionary from JIRA
            field_path: Dot-separated path to field (e.g., 'status.name')
            default: Default value if field not found
            
        Returns:
            Field value or default
        """
        try:
            value = fields
            for part in field_path.split('.'):
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return default
                if value is None:
                    return default
            return value
        except Exception:
            return default


class IssueUpdatedProcessor(JiraEventProcessor):
    """Processor for JIRA issue updated events."""
    
    # Fields that indicate significant changes
    SIGNIFICANT_FIELDS = {
        'status': ChangeSignificance.MAJOR,
        'priority': ChangeSignificance.MAJOR,
        'assignee': ChangeSignificance.MODERATE,
        'summary': ChangeSignificance.MODERATE,
        'description': ChangeSignificance.MINOR,
        'labels': ChangeSignificance.MINOR,
        'fixVersions': ChangeSignificance.MODERATE,
        'components': ChangeSignificance.MINOR
    }
    
    # Status values that indicate blocking
    BLOCKING_STATUSES = {
        'blocked', 'impediment', 'on hold', 'waiting', 'paused'
    }
    
    async def can_process(self, event: ProcessedEvent) -> bool:
        """Check if this is an issue updated event."""
        return event.event_type == 'jira:issue_updated'
    
    async def process_event(self, event: ProcessedEvent) -> Dict[str, Any]:
        """Process issue updated event."""
        self.logger.debug(f"Processing issue updated event for {event.ticket_key}")
        
        # Extract change information
        changelog = event.raw_payload.get('changelog', {})
        field_changes = await self._analyze_field_changes(changelog)
        
        # Determine if this is a significant update
        significance = await self._determine_update_significance(field_changes)
        
        # Check for blocking status
        is_blocked = await self._check_blocking_status(event.jira_event_data, field_changes)
        
        # Extract sprint context
        sprint_context = await self._extract_sprint_context(event.jira_event_data)
        
        # Analyze assignee information
        assignee_info = await self._extract_assignee_info(event.jira_event_data)
        
        return {
            'processor_type': 'issue_updated',
            'field_changes': field_changes,
            'significance': significance,
            'is_blocked': is_blocked,
            'sprint_context': sprint_context,
            'assignee_info': assignee_info,
            'change_summary': await self._generate_change_summary(field_changes)
        }
    
    async def _analyze_field_changes(self, changelog: Dict[str, Any]) -> List[FieldChange]:
        """Analyze field changes from changelog."""
        changes = []
        
        for item in changelog.get('items', []):
            field_name = item.get('field', '')
            old_value = item.get('fromString', item.get('from'))
            new_value = item.get('toString', item.get('to'))
            
            # Determine significance
            significance = self.SIGNIFICANT_FIELDS.get(field_name, ChangeSignificance.TRIVIAL)
            
            # Determine change type
            if old_value is None:
                change_type = 'added'
            elif new_value is None:
                change_type = 'removed'
            else:
                change_type = 'modified'
            
            # Special handling for status changes to blocked states
            if field_name == 'status' and new_value and any(
                blocked in new_value.lower() for blocked in self.BLOCKING_STATUSES
            ):
                significance = ChangeSignificance.CRITICAL
            
            changes.append(FieldChange(
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                significance=significance,
                change_type=change_type
            ))
        
        return changes
    
    async def _determine_update_significance(self, field_changes: List[FieldChange]) -> SignificanceLevel:
        """Determine overall significance of the update."""
        if not field_changes:
            return SignificanceLevel.MINOR
        
        max_significance = max(change.significance for change in field_changes)
        
        significance_mapping = {
            ChangeSignificance.CRITICAL: SignificanceLevel.CRITICAL,
            ChangeSignificance.MAJOR: SignificanceLevel.MAJOR,
            ChangeSignificance.MODERATE: SignificanceLevel.MODERATE,
            ChangeSignificance.MINOR: SignificanceLevel.MINOR,
            ChangeSignificance.TRIVIAL: SignificanceLevel.MINOR
        }
        
        return significance_mapping.get(max_significance, SignificanceLevel.MINOR)
    
    async def _check_blocking_status(self, issue_data: Dict[str, Any], field_changes: List[FieldChange]) -> bool:
        """Check if the issue is in a blocking status."""
        # Check current status
        current_status = self._extract_field_value(issue_data, 'fields.status.name', '').lower()
        if any(blocked in current_status for blocked in self.BLOCKING_STATUSES):
            return True
        
        # Check if status changed to a blocking state
        for change in field_changes:
            if (change.field_name == 'status' and 
                change.new_value and 
                any(blocked in change.new_value.lower() for blocked in self.BLOCKING_STATUSES)):
                return True
        
        return False
    
    async def _extract_sprint_context(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract sprint context information."""
        fields = issue_data.get('fields', {})
        
        # Try to extract sprint information (custom field varies by instance)
        sprint_fields = ['customfield_10020', 'customfield_10010', 'sprint']
        sprint_info = None
        
        for field in sprint_fields:
            sprint_data = fields.get(field)
            if sprint_data:
                if isinstance(sprint_data, list) and sprint_data:
                    sprint_info = sprint_data[0]  # Current sprint
                else:
                    sprint_info = sprint_data
                break
        
        if sprint_info and isinstance(sprint_info, dict):
            return {
                'sprint_id': sprint_info.get('id'),
                'sprint_name': sprint_info.get('name'),
                'sprint_state': sprint_info.get('state'),
                'sprint_start_date': sprint_info.get('startDate'),
                'sprint_end_date': sprint_info.get('endDate')
            }
        
        return {'sprint_id': None, 'sprint_name': None}
    
    async def _extract_assignee_info(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract assignee information."""
        assignee = self._extract_field_value(issue_data, 'fields.assignee')
        
        if assignee:
            return {
                'assignee_id': assignee.get('accountId'),
                'assignee_name': assignee.get('displayName'),
                'assignee_email': assignee.get('emailAddress'),
                'assignee_active': assignee.get('active', True)
            }
        
        return {'assignee_id': None, 'assignee_name': None}
    
    async def _generate_change_summary(self, field_changes: List[FieldChange]) -> str:
        """Generate a human-readable summary of changes."""
        if not field_changes:
            return "No significant changes"
        
        summaries = []
        for change in field_changes:
            if change.significance in [ChangeSignificance.MAJOR, ChangeSignificance.CRITICAL]:
                if change.change_type == 'modified':
                    summaries.append(f"{change.field_name}: {change.old_value} → {change.new_value}")
                elif change.change_type == 'added':
                    summaries.append(f"{change.field_name}: added {change.new_value}")
                elif change.change_type == 'removed':
                    summaries.append(f"{change.field_name}: removed {change.old_value}")
        
        return "; ".join(summaries) if summaries else "Minor field updates"


class IssueTransitionProcessor(JiraEventProcessor):
    """Processor for JIRA issue transition events."""
    
    # Typical durations for different transitions (in hours)
    TYPICAL_TRANSITION_DURATIONS = {
        ('to do', 'in progress'): 24,
        ('in progress', 'in review'): 72,
        ('in review', 'done'): 48,
        ('in progress', 'blocked'): 1,  # Should be quick
    }
    
    async def can_process(self, event: ProcessedEvent) -> bool:
        """Check if this is an issue transition event."""
        return event.event_type in ['jira:issue_transitioned', 'jira:issue_updated']
    
    async def process_event(self, event: ProcessedEvent) -> Dict[str, Any]:
        """Process issue transition event."""
        self.logger.debug(f"Processing issue transition event for {event.ticket_key}")
        
        # Extract transition information
        transition_analysis = await self._analyze_status_transition(event)
        
        # Calculate time in previous status
        time_in_status = await self._calculate_time_in_status(event)
        
        # Detect bottlenecks
        bottleneck_analysis = await self._detect_bottlenecks(transition_analysis, time_in_status)
        
        # Check for unusual patterns
        unusual_patterns = await self._detect_unusual_patterns(transition_analysis)
        
        return {
            'processor_type': 'issue_transition',
            'transition_analysis': transition_analysis,
            'time_in_status': time_in_status,
            'bottleneck_analysis': bottleneck_analysis,
            'unusual_patterns': unusual_patterns
        }
    
    async def _analyze_status_transition(self, event: ProcessedEvent) -> Optional[StatusTransitionAnalysis]:
        """Analyze the status transition."""
        changelog = event.raw_payload.get('changelog', {})
        
        # Find status change in changelog
        status_change = None
        for item in changelog.get('items', []):
            if item.get('field') == 'status':
                status_change = item
                break
        
        if not status_change:
            return None
        
        from_status = status_change.get('fromString', '').lower()
        to_status = status_change.get('toString', '').lower()
        
        # Determine if this is a backward transition
        is_backward = await self._is_backward_transition(from_status, to_status)
        
        # Check if transitioning to blocked state
        is_blocked = any(blocked in to_status for blocked in ['blocked', 'impediment', 'on hold'])
        
        # Check for bottleneck indicators
        bottleneck_indicator = await self._is_bottleneck_transition(from_status, to_status)
        
        return StatusTransitionAnalysis(
            from_status=from_status,
            to_status=to_status,
            transition_time=None,  # Will be calculated separately
            is_backward_transition=is_backward,
            is_blocked_transition=is_blocked,
            bottleneck_indicator=bottleneck_indicator,
            typical_duration=await self._get_typical_duration(from_status, to_status)
        )
    
    async def _is_backward_transition(self, from_status: str, to_status: str) -> bool:
        """Check if this is a backward transition in the workflow."""
        # Define typical workflow order
        workflow_order = [
            'to do', 'open', 'new',
            'in progress', 'development', 'working',
            'in review', 'review', 'testing',
            'done', 'closed', 'resolved'
        ]
        
        from_index = -1
        to_index = -1
        
        for i, status in enumerate(workflow_order):
            if status in from_status:
                from_index = i
            if status in to_status:
                to_index = i
        
        return from_index > to_index and from_index != -1 and to_index != -1
    
    async def _is_bottleneck_transition(self, from_status: str, to_status: str) -> bool:
        """Check if this transition indicates a bottleneck."""
        # Transitions that often indicate bottlenecks
        bottleneck_transitions = [
            ('in progress', 'blocked'),
            ('in review', 'in progress'),  # Back to development
            ('testing', 'in progress'),    # Failed testing
        ]
        
        return (from_status, to_status) in bottleneck_transitions
    
    async def _get_typical_duration(self, from_status: str, to_status: str) -> Optional[timedelta]:
        """Get typical duration for this transition."""
        duration_hours = self.TYPICAL_TRANSITION_DURATIONS.get((from_status, to_status))
        return timedelta(hours=duration_hours) if duration_hours else None
    
    async def _calculate_time_in_status(self, event: ProcessedEvent) -> Optional[timedelta]:
        """Calculate time spent in the previous status."""
        # This would typically require historical data
        # For now, return None - can be enhanced with database queries
        return None
    
    async def _detect_bottlenecks(self, transition: Optional[StatusTransitionAnalysis], time_in_status: Optional[timedelta]) -> Dict[str, Any]:
        """Detect bottleneck indicators."""
        if not transition:
            return {'bottleneck_detected': False}
        
        bottleneck_indicators = []
        
        if transition.is_blocked_transition:
            bottleneck_indicators.append('transitioned_to_blocked')
        
        if transition.is_backward_transition:
            bottleneck_indicators.append('backward_transition')
        
        if transition.bottleneck_indicator:
            bottleneck_indicators.append('known_bottleneck_pattern')
        
        return {
            'bottleneck_detected': len(bottleneck_indicators) > 0,
            'indicators': bottleneck_indicators,
            'severity': 'high' if len(bottleneck_indicators) > 1 else 'medium'
        }
    
    async def _detect_unusual_patterns(self, transition: Optional[StatusTransitionAnalysis]) -> List[str]:
        """Detect unusual transition patterns."""
        if not transition:
            return []
        
        patterns = []
        
        if transition.is_backward_transition:
            patterns.append('backward_workflow_movement')
        
        if transition.is_blocked_transition:
            patterns.append('blocked_status_transition')
        
        # Add more pattern detection logic here
        
        return patterns


class IssueAssignedProcessor(JiraEventProcessor):
    """Processor for JIRA issue assignment events."""
    
    async def can_process(self, event: ProcessedEvent) -> bool:
        """Check if this is an assignment event."""
        if event.event_type != 'jira:issue_updated':
            return False
        
        # Check if assignee field changed
        changelog = event.raw_payload.get('changelog', {})
        for item in changelog.get('items', []):
            if item.get('field') == 'assignee':
                return True
        
        return False
    
    async def process_event(self, event: ProcessedEvent) -> Dict[str, Any]:
        """Process issue assignment event."""
        self.logger.debug(f"Processing issue assignment event for {event.ticket_key}")
        
        # Extract assignment information
        assignment_info = await self._extract_assignment_info(event)
        
        # Analyze workload impact
        workload_analysis = await self._analyze_workload_impact(assignment_info)
        
        # Extract effort estimation
        effort_info = await self._extract_effort_info(event.jira_event_data)
        
        # Extract deadline information
        deadline_info = await self._extract_deadline_info(event.jira_event_data)
        
        return {
            'processor_type': 'issue_assigned',
            'assignment_info': assignment_info,
            'workload_analysis': workload_analysis,
            'effort_info': effort_info,
            'deadline_info': deadline_info
        }
    
    async def _extract_assignment_info(self, event: ProcessedEvent) -> Dict[str, Any]:
        """Extract assignment change information."""
        changelog = event.raw_payload.get('changelog', {})
        
        assignment_change = None
        for item in changelog.get('items', []):
            if item.get('field') == 'assignee':
                assignment_change = item
                break
        
        if not assignment_change:
            return {}
        
        old_assignee = assignment_change.get('from')
        new_assignee = assignment_change.get('to')
        
        # Get current assignee details
        current_assignee = self._extract_field_value(event.jira_event_data, 'fields.assignee')
        
        return {
            'old_assignee_id': old_assignee,
            'new_assignee_id': new_assignee,
            'new_assignee_name': current_assignee.get('displayName') if current_assignee else None,
            'new_assignee_email': current_assignee.get('emailAddress') if current_assignee else None,
            'assignment_type': 'assigned' if new_assignee else 'unassigned'
        }
    
    async def _analyze_workload_impact(self, assignment_info: Dict[str, Any]) -> Optional[WorkloadAnalysis]:
        """Analyze workload impact of the assignment."""
        new_assignee_id = assignment_info.get('new_assignee_id')
        if not new_assignee_id:
            return None
        
        # This would typically query the database for current workload
        # For now, return a placeholder analysis
        return WorkloadAnalysis(
            assignee=assignment_info.get('new_assignee_name', 'Unknown'),
            current_ticket_count=0,  # Would be calculated from database
            total_story_points=0,    # Would be calculated from database
            overloaded=False,        # Would be determined by business rules
            capacity_percentage=0.0, # Would be calculated
            recent_assignments=0     # Would be calculated from recent history
        )
    
    async def _extract_effort_info(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract effort estimation information."""
        fields = issue_data.get('fields', {})
        
        # Common story points fields
        story_points_fields = ['customfield_10016', 'customfield_10002', 'storyPoints']
        story_points = None
        
        for field in story_points_fields:
            story_points = fields.get(field)
            if story_points is not None:
                break
        
        # Extract time estimates
        original_estimate = fields.get('timeoriginalestimate')  # in seconds
        remaining_estimate = fields.get('timeestimate')         # in seconds
        
        return {
            'story_points': story_points,
            'original_estimate_hours': original_estimate / 3600 if original_estimate else None,
            'remaining_estimate_hours': remaining_estimate / 3600 if remaining_estimate else None
        }
    
    async def _extract_deadline_info(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract deadline and due date information."""
        fields = issue_data.get('fields', {})
        
        due_date = fields.get('duedate')
        
        # Extract fix version dates (often used as release deadlines)
        fix_versions = fields.get('fixVersions', [])
        release_dates = []
        
        for version in fix_versions:
            if version.get('releaseDate'):
                release_dates.append({
                    'version': version.get('name'),
                    'release_date': version.get('releaseDate')
                })
        
        return {
            'due_date': due_date,
            'release_dates': release_dates,
            'has_deadline': bool(due_date or release_dates)
        }


class CommentAddedProcessor(JiraEventProcessor):
    """Processor for JIRA comment events."""
    
    # Keywords that indicate different types of comments
    BLOCKER_KEYWORDS = [
        'blocked', 'blocker', 'impediment', 'stuck', 'cannot proceed',
        'waiting for', 'dependency', 'issue with'
    ]
    
    DECISION_KEYWORDS = [
        'decided', 'decision', 'agreed', 'approved', 'rejected',
        'go with', 'chosen', 'selected'
    ]
    
    QUESTION_KEYWORDS = [
        '?', 'question', 'clarification', 'help', 'how to',
        'what should', 'which way', 'unsure'
    ]
    
    URGENCY_KEYWORDS = [
        'urgent', 'asap', 'immediately', 'critical', 'emergency',
        'high priority', 'needs attention'
    ]
    
    async def can_process(self, event: ProcessedEvent) -> bool:
        """Check if this is a comment event."""
        return event.event_type == 'jira:issue_commented'
    
    async def process_event(self, event: ProcessedEvent) -> Dict[str, Any]:
        """Process comment added event."""
        self.logger.debug(f"Processing comment event for {event.ticket_key}")
        
        # Extract comment information
        comment_data = event.raw_payload.get('comment', {})
        
        # Analyze comment content
        comment_analysis = await self._analyze_comment_content(comment_data)
        
        # Determine if this is a significant comment
        is_significant = await self._is_significant_comment(comment_analysis, event.jira_event_data)
        
        # Extract mention information
        mentions = await self._extract_mentions(comment_data)
        
        return {
            'processor_type': 'comment_added',
            'comment_analysis': comment_analysis,
            'is_significant': is_significant,
            'mentions': mentions,
            'comment_metadata': {
                'comment_id': comment_data.get('id'),
                'created': comment_data.get('created'),
                'updated': comment_data.get('updated')
            }
        }
    
    async def _analyze_comment_content(self, comment_data: Dict[str, Any]) -> CommentAnalysis:
        """Analyze comment content for significance and keywords."""
        body = comment_data.get('body', '')
        author_info = comment_data.get('author', {})
        
        # Create content preview (first 200 characters)
        content_preview = body[:200] + '...' if len(body) > 200 else body
        
        # Analyze for different keyword types
        body_lower = body.lower()
        
        contains_blocker = any(keyword in body_lower for keyword in self.BLOCKER_KEYWORDS)
        contains_decision = any(keyword in body_lower for keyword in self.DECISION_KEYWORDS)
        contains_question = any(keyword in body_lower for keyword in self.QUESTION_KEYWORDS)
        
        # Find urgency indicators
        urgency_indicators = [
            keyword for keyword in self.URGENCY_KEYWORDS
            if keyword in body_lower
        ]
        
        # Extract mentions (users tagged with @)
        mentions = await self._extract_mentions_from_text(body)
        
        # Determine significance
        if contains_blocker or urgency_indicators:
            significance = SignificanceLevel.CRITICAL
        elif contains_decision:
            significance = SignificanceLevel.MAJOR
        elif contains_question or mentions:
            significance = SignificanceLevel.MODERATE
        else:
            significance = SignificanceLevel.MINOR
        
        return CommentAnalysis(
            author=author_info.get('displayName', 'Unknown'),
            content_preview=content_preview,
            mentions=mentions,
            contains_blocker_keywords=contains_blocker,
            contains_decision_keywords=contains_decision,
            contains_question_keywords=contains_question,
            urgency_indicators=urgency_indicators,
            significance=significance
        )
    
    async def _is_significant_comment(self, analysis: CommentAnalysis, issue_data: Dict[str, Any]) -> bool:
        """Determine if this comment is significant enough to trigger notifications."""
        # Always significant if contains blockers or urgency indicators
        if analysis.contains_blocker_keywords or analysis.urgency_indicators:
            return True
        
        # Significant if contains decisions
        if analysis.contains_decision_keywords:
            return True
        
        # Significant if on high-priority tickets
        priority = self._extract_field_value(issue_data, 'fields.priority.name', '').lower()
        if priority in ['critical', 'highest', 'high'] and analysis.significance != SignificanceLevel.MINOR:
            return True
        
        # Significant if mentions people
        if analysis.mentions:
            return True
        
        return False
    
    async def _extract_mentions(self, comment_data: Dict[str, Any]) -> List[str]:
        """Extract user mentions from comment."""
        body = comment_data.get('body', '')
        return await self._extract_mentions_from_text(body)
    
    async def _extract_mentions_from_text(self, text: str) -> List[str]:
        """Extract mentions from text content."""
        import re
        
        # Look for @username patterns
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, text)
        
        # Also look for [~accountId] patterns (JIRA format)
        jira_mention_pattern = r'\[~([^\]]+)\]'
        jira_mentions = re.findall(jira_mention_pattern, text)
        
        return list(set(mentions + jira_mentions))


class EventProcessorRegistry:
    """Registry for managing event processors."""
    
    def __init__(self):
        """Initialize the processor registry."""
        self.processors: List[JiraEventProcessor] = []
        self._initialize_default_processors()
    
    def _initialize_default_processors(self):
        """Initialize default processors."""
        self.processors = [
            IssueUpdatedProcessor(),
            IssueTransitionProcessor(),
            IssueAssignedProcessor(),
            CommentAddedProcessor()
        ]
    
    async def process_event(self, event: ProcessedEvent) -> Dict[str, Any]:
        """
        Process an event through all applicable processors.
        
        Args:
            event: The processed event to enrich
            
        Returns:
            Combined enrichment data from all processors
        """
        enrichment_data = {}
        
        for processor in self.processors:
            try:
                if await processor.can_process(event):
                    processor_data = await processor.process_event(event)
                    enrichment_data.update(processor_data)
                    
                    logger.debug(
                        f"Processor {processor.__class__.__name__} "
                        f"enriched event {event.event_id}"
                    )
                    
            except Exception as e:
                logger.error(
                    f"Error in processor {processor.__class__.__name__} "
                    f"for event {event.event_id}: {e}",
                    exc_info=True
                )
        
        return enrichment_data
    
    def register_processor(self, processor: JiraEventProcessor):
        """Register a custom processor."""
        self.processors.append(processor)
        logger.info(f"Registered processor: {processor.__class__.__name__}")
    
    def get_processors(self) -> List[JiraEventProcessor]:
        """Get all registered processors."""
        return self.processors.copy()