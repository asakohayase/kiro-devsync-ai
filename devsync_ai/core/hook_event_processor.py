"""
Hook Event Processor for JIRA event handling.

This module provides the HookEventProcessor class that handles event parsing,
enrichment, validation, and integration with existing JIRA services for
comprehensive event processing in the Agent Hook system.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from .agent_hooks import (
    ProcessedEvent,
    EnrichedEvent,
    EventCategory,
    UrgencyLevel,
    SignificanceLevel,
    EventClassification,
    Stakeholder
)
from .jira_event_processors import (
    EventProcessorRegistry,
    JiraEventProcessor,
    IssueUpdatedProcessor,
    IssueTransitionProcessor,
    IssueAssignedProcessor,
    CommentAddedProcessor
)
from ..services.jira import JiraService, JiraAPIError


logger = logging.getLogger(__name__)


@dataclass
class EventValidationResult:
    """Result of event validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    event_type: Optional[str] = None
    ticket_key: Optional[str] = None


@dataclass
class EventEnrichmentResult:
    """Result of event enrichment process."""
    success: bool
    enriched_event: Optional[EnrichedEvent] = None
    enrichment_data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


class EventTypeClassifier:
    """Classifies JIRA events into appropriate categories."""
    
    # Mapping of JIRA webhook events to our event categories
    EVENT_CATEGORY_MAPPING = {
        'jira:issue_created': EventCategory.CREATION,
        'jira:issue_updated': EventCategory.STATUS_CHANGE,
        'jira:issue_deleted': EventCategory.STATUS_CHANGE,
        'jira:issue_assigned': EventCategory.ASSIGNMENT,
        'jira:issue_commented': EventCategory.COMMENT,
        'jira:issue_transitioned': EventCategory.TRANSITION,
        'jira:issue_priority_changed': EventCategory.PRIORITY_CHANGE,
    }
    
    # Keywords that indicate blocking issues
    BLOCKER_KEYWORDS = {
        'blocked', 'blocker', 'impediment', 'stuck', 'cannot proceed',
        'waiting for', 'dependency', 'issue with', 'on hold', 'paused'
    }
    
    # Status values that indicate blocking
    BLOCKING_STATUSES = {
        'blocked', 'impediment', 'on hold', 'waiting', 'paused', 'suspended'
    }
    
    def classify_event_category(self, event_type: str, issue_data: Dict[str, Any]) -> EventCategory:
        """
        Classify the event into an appropriate category.
        
        Args:
            event_type: JIRA webhook event type
            issue_data: Issue data from webhook
            
        Returns:
            Classified event category
        """
        # Check for blocker conditions first (highest priority)
        if self._is_blocker_event(event_type, issue_data):
            return EventCategory.BLOCKER
        
        # Use direct mapping for known event types
        if event_type in self.EVENT_CATEGORY_MAPPING:
            return self.EVENT_CATEGORY_MAPPING[event_type]
        
        # For issue_updated events, determine more specific category
        if event_type == 'jira:issue_updated':
            return self._classify_update_event(issue_data)
        
        # Default fallback
        return EventCategory.STATUS_CHANGE
    
    def _is_blocker_event(self, event_type: str, issue_data: Dict[str, Any]) -> bool:
        """Check if this event indicates a blocking condition."""
        fields = issue_data.get('fields', {})
        
        # Check current status
        status = fields.get('status', {}).get('name', '').lower()
        if any(blocked in status for blocked in self.BLOCKING_STATUSES):
            return True
        
        # Check labels for blocker keywords
        labels = fields.get('labels', [])
        for label in labels:
            if any(keyword in str(label).lower() for keyword in self.BLOCKER_KEYWORDS):
                return True
        
        # Check summary and description for blocker keywords
        summary = fields.get('summary', '').lower()
        description = fields.get('description', '').lower()
        
        for keyword in self.BLOCKER_KEYWORDS:
            if keyword in summary or keyword in description:
                return True
        
        return False
    
    def _classify_update_event(self, issue_data: Dict[str, Any]) -> EventCategory:
        """Classify an issue_updated event into more specific category."""
        # This would typically analyze the changelog to determine what changed
        # For now, return STATUS_CHANGE as default
        return EventCategory.STATUS_CHANGE
    
    def determine_urgency(self, issue_data: Dict[str, Any], event_category: EventCategory) -> UrgencyLevel:
        """
        Determine urgency level based on issue data and event category.
        
        Args:
            issue_data: Issue data from webhook
            event_category: Classified event category
            
        Returns:
            Determined urgency level
        """
        fields = issue_data.get('fields', {})
        
        # Blocker events are always critical
        if event_category == EventCategory.BLOCKER:
            return UrgencyLevel.CRITICAL
        
        # Check priority field
        priority = fields.get('priority', {}).get('name', '').lower()
        if priority in ['critical', 'highest', 'blocker']:
            return UrgencyLevel.CRITICAL
        elif priority in ['high', 'major']:
            return UrgencyLevel.HIGH
        elif priority in ['medium', 'normal']:
            return UrgencyLevel.MEDIUM
        else:
            return UrgencyLevel.LOW
    
    def determine_significance(self, event_category: EventCategory, urgency: UrgencyLevel) -> SignificanceLevel:
        """
        Determine significance level based on category and urgency.
        
        Args:
            event_category: Event category
            urgency: Event urgency level
            
        Returns:
            Determined significance level
        """
        # Critical urgency always means critical significance
        if urgency == UrgencyLevel.CRITICAL:
            return SignificanceLevel.CRITICAL
        
        # Blocker events are always major or critical
        if event_category == EventCategory.BLOCKER:
            return SignificanceLevel.CRITICAL
        
        # Assignment and comment events can be major if high urgency
        if event_category in [EventCategory.ASSIGNMENT, EventCategory.COMMENT]:
            if urgency == UrgencyLevel.HIGH:
                return SignificanceLevel.MAJOR
            elif urgency == UrgencyLevel.MEDIUM:
                return SignificanceLevel.MODERATE
            else:
                return SignificanceLevel.MINOR
        
        # Status changes and transitions
        if event_category in [EventCategory.STATUS_CHANGE, EventCategory.TRANSITION]:
            if urgency == UrgencyLevel.HIGH:
                return SignificanceLevel.MAJOR
            else:
                return SignificanceLevel.MODERATE
        
        # Default mapping
        significance_mapping = {
            UrgencyLevel.HIGH: SignificanceLevel.MAJOR,
            UrgencyLevel.MEDIUM: SignificanceLevel.MODERATE,
            UrgencyLevel.LOW: SignificanceLevel.MINOR
        }
        
        return significance_mapping.get(urgency, SignificanceLevel.MINOR)


class HookEventProcessor:
    """
    Main event processor for JIRA webhook events in the Agent Hook system.
    
    Handles event parsing, validation, classification, and enrichment with
    integration to existing JIRA services and event processors.
    """
    
    def __init__(self, jira_service: Optional[JiraService] = None):
        """
        Initialize the Hook Event Processor.
        
        Args:
            jira_service: Optional JIRA service for ticket data enrichment
        """
        self.jira_service = jira_service
        self.event_classifier = EventTypeClassifier()
        self.processor_registry = EventProcessorRegistry()
        
        # Metrics tracking
        self._events_processed = 0
        self._events_enriched = 0
        self._validation_failures = 0
        self._enrichment_failures = 0
        
        logger.info("HookEventProcessor initialized")
    
    async def process_webhook_event(
        self,
        webhook_data: Dict[str, Any],
        validate_structure: bool = True
    ) -> Tuple[ProcessedEvent, EventValidationResult]:
        """
        Process a raw JIRA webhook event into a ProcessedEvent.
        
        Args:
            webhook_data: Raw webhook payload from JIRA
            validate_structure: Whether to validate event structure
            
        Returns:
            Tuple of (ProcessedEvent, ValidationResult)
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Validate event structure if requested
            validation_result = EventValidationResult(valid=True)
            if validate_structure:
                validation_result = await self.validate_event_structure(webhook_data)
                if not validation_result.valid:
                    self._validation_failures += 1
                    # Return a minimal processed event even if validation fails
                    processed_event = ProcessedEvent(
                        event_id="",
                        event_type=validation_result.event_type or "unknown",
                        timestamp=start_time,
                        jira_event_data={},
                        ticket_key=validation_result.ticket_key or "UNKNOWN",
                        project_key="UNKNOWN",
                        raw_payload=webhook_data
                    )
                    return processed_event, validation_result
            
            # Extract basic event information
            event_type = webhook_data.get('webhookEvent', 'unknown')
            issue_data = webhook_data.get('issue', {})
            ticket_key = issue_data.get('key', 'UNKNOWN')
            project_key = ticket_key.split('-')[0] if '-' in ticket_key else 'UNKNOWN'
            
            # Create processed event
            processed_event = ProcessedEvent(
                event_id="",  # Will be auto-generated in __post_init__
                event_type=event_type,
                timestamp=start_time,
                jira_event_data=issue_data,
                ticket_key=ticket_key,
                project_key=project_key,
                raw_payload=webhook_data
            )
            
            self._events_processed += 1
            
            logger.debug(
                f"Processed webhook event: {event_type} for ticket {ticket_key} "
                f"(event_id: {processed_event.event_id})"
            )
            
            return processed_event, validation_result
            
        except Exception as e:
            logger.error(f"Error processing webhook event: {e}", exc_info=True)
            self._validation_failures += 1
            
            # Return error in validation result
            validation_result = EventValidationResult(
                valid=False,
                errors=[f"Processing error: {str(e)}"]
            )
            
            # Create minimal processed event
            processed_event = ProcessedEvent(
                event_id="",
                event_type="error",
                timestamp=start_time,
                jira_event_data={},
                ticket_key="ERROR",
                project_key="ERROR",
                raw_payload=webhook_data
            )
            
            return processed_event, validation_result
    
    async def validate_event_structure(self, webhook_data: Dict[str, Any]) -> EventValidationResult:
        """
        Validate the structure and content of a JIRA webhook event.
        
        Args:
            webhook_data: Raw webhook payload
            
        Returns:
            Validation result with details
        """
        errors = []
        warnings = []
        event_type = None
        ticket_key = None
        
        try:
            # Check for required top-level fields
            if not isinstance(webhook_data, dict):
                errors.append("Webhook data must be a dictionary")
                return EventValidationResult(valid=False, errors=errors)
            
            # Validate webhook event type
            event_type = webhook_data.get('webhookEvent')
            if not event_type:
                errors.append("Missing required field: 'webhookEvent'")
            elif not isinstance(event_type, str):
                errors.append("Field 'webhookEvent' must be a string")
            elif not event_type.startswith('jira:'):
                warnings.append(f"Unexpected webhook event format: {event_type}")
            
            # Validate issue data for issue-related events or if issue data is present
            if (event_type and 'issue' in event_type) or 'issue' in webhook_data:
                issue_data = webhook_data.get('issue')
                if not issue_data:
                    errors.append("Missing 'issue' data for issue-related event")
                elif not isinstance(issue_data, dict):
                    errors.append("Field 'issue' must be a dictionary")
                else:
                    # Validate issue structure
                    ticket_key = issue_data.get('key')
                    if not ticket_key:
                        errors.append("Missing required field: 'issue.key'")
                    elif not isinstance(ticket_key, str):
                        errors.append("Field 'issue.key' must be a string")
                    elif '-' not in ticket_key:
                        warnings.append(f"Unusual ticket key format: {ticket_key}")
                    
                    # Check for fields object
                    fields = issue_data.get('fields')
                    if fields is None:
                        errors.append("Missing required field: 'issue.fields'")
                    elif not isinstance(fields, dict):
                        errors.append("Field 'issue.fields' must be a dictionary")
                    else:
                        # Validate essential fields (only warnings for missing optional fields)
                        if not fields.get('summary'):
                            warnings.append("Missing issue summary")
                        if not fields.get('status'):
                            warnings.append("Missing issue status")
                        if not fields.get('issuetype'):
                            warnings.append("Missing issue type")
            
            # Validate timestamp if present
            timestamp = webhook_data.get('timestamp')
            if timestamp and not isinstance(timestamp, (str, int)):
                warnings.append("Invalid timestamp format")
            
            # Check for changelog in update events
            if event_type == 'jira:issue_updated':
                changelog = webhook_data.get('changelog')
                if not changelog:
                    warnings.append("Missing changelog for issue update event")
                elif not isinstance(changelog, dict):
                    warnings.append("Changelog must be a dictionary")
                elif not changelog.get('items'):
                    warnings.append("Empty changelog items")
            
            # Check for comment data in comment events
            if event_type == 'jira:issue_commented':
                comment = webhook_data.get('comment')
                if not comment:
                    errors.append("Missing comment data for comment event")
                elif not isinstance(comment, dict):
                    errors.append("Comment data must be a dictionary")
                elif not comment.get('body'):
                    warnings.append("Empty comment body")
            
            is_valid = len(errors) == 0
            
            logger.debug(
                f"Event validation completed: valid={is_valid}, "
                f"errors={len(errors)}, warnings={len(warnings)}"
            )
            
            return EventValidationResult(
                valid=is_valid,
                errors=errors,
                warnings=warnings,
                event_type=event_type,
                ticket_key=ticket_key
            )
            
        except Exception as e:
            logger.error(f"Error during event validation: {e}", exc_info=True)
            return EventValidationResult(
                valid=False,
                errors=[f"Validation error: {str(e)}"],
                event_type=event_type,
                ticket_key=ticket_key
            )
    
    async def enrich_event(self, processed_event: ProcessedEvent) -> EventEnrichmentResult:
        """
        Enrich a processed event with additional context and classification.
        
        Args:
            processed_event: Basic processed event to enrich
            
        Returns:
            Enrichment result with enriched event or error details
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Classify the event
            event_category = self.event_classifier.classify_event_category(
                processed_event.event_type,
                processed_event.jira_event_data
            )
            
            # Determine urgency and significance
            urgency = self.event_classifier.determine_urgency(
                processed_event.jira_event_data,
                event_category
            )
            
            significance = self.event_classifier.determine_significance(
                event_category,
                urgency
            )
            
            # Extract stakeholders
            stakeholders = await self._extract_stakeholders(processed_event)
            
            # Determine affected teams
            affected_teams = await self._determine_affected_teams(processed_event)
            
            # Create event classification
            classification = EventClassification(
                category=event_category,
                urgency=urgency,
                significance=significance,
                affected_teams=affected_teams,
                routing_hints=await self._generate_routing_hints(processed_event),
                keywords=await self._extract_keywords(processed_event)
            )
            
            # Get detailed ticket information
            ticket_details = await self._get_enhanced_ticket_details(processed_event)
            
            # Process through specialized processors for additional enrichment
            processor_enrichment = await self._process_with_specialized_processors(processed_event)
            
            # Gather additional context data
            context_data = await self._gather_context_data(processed_event)
            context_data.update(processor_enrichment)
            
            # Create enriched event
            enriched_event = EnrichedEvent(
                **processed_event.__dict__,
                ticket_details=ticket_details,
                stakeholders=stakeholders,
                classification=classification,
                context_data=context_data
            )
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self._events_enriched += 1
            
            logger.debug(
                f"Event enriched successfully: {enriched_event.event_id} "
                f"(category={event_category.value}, urgency={urgency.value}, "
                f"significance={significance.value}) in {processing_time:.2f}ms"
            )
            
            return EventEnrichmentResult(
                success=True,
                enriched_event=enriched_event,
                enrichment_data=context_data,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self._enrichment_failures += 1
            
            logger.error(
                f"Error enriching event {processed_event.event_id}: {e}",
                exc_info=True
            )
            
            return EventEnrichmentResult(
                success=False,
                errors=[f"Enrichment error: {str(e)}"],
                processing_time_ms=processing_time
            )
    
    async def _extract_stakeholders(self, event: ProcessedEvent) -> List[Stakeholder]:
        """Extract stakeholders from event data."""
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
        
        return stakeholders
    
    async def _determine_affected_teams(self, event: ProcessedEvent) -> List[str]:
        """Determine which teams are affected by this event."""
        teams = set()
        
        # Primary team based on project
        teams.add(event.project_key.lower())
        
        # Add teams based on components
        fields = event.jira_event_data.get('fields', {})
        components = fields.get('components', [])
        for component in components:
            if isinstance(component, dict) and component.get('name'):
                # Use component name as potential team identifier
                teams.add(component['name'].lower().replace(' ', '-'))
        
        # Add teams based on labels
        labels = fields.get('labels', [])
        for label in labels:
            label_str = str(label).lower()
            if label_str.startswith('team-'):
                teams.add(label_str[5:])  # Remove 'team-' prefix
        
        return list(teams)
    
    async def _generate_routing_hints(self, event: ProcessedEvent) -> Dict[str, Any]:
        """Generate routing hints for the event."""
        fields = event.jira_event_data.get('fields', {})
        
        hints = {
            'project': event.project_key,
            'ticket_key': event.ticket_key,
            'event_type': event.event_type
        }
        
        # Add issue type
        issue_type = fields.get('issuetype', {})
        if isinstance(issue_type, dict):
            hints['issue_type'] = issue_type.get('name')
        
        # Add priority
        priority = fields.get('priority', {})
        if isinstance(priority, dict):
            hints['priority'] = priority.get('name')
        
        # Add status
        status = fields.get('status', {})
        if isinstance(status, dict):
            hints['status'] = status.get('name')
        
        # Add assignee
        assignee = fields.get('assignee', {})
        if isinstance(assignee, dict):
            hints['assignee'] = assignee.get('displayName')
        
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
        
        return hints
    
    async def _extract_keywords(self, event: ProcessedEvent) -> List[str]:
        """Extract relevant keywords from the event."""
        keywords = set()
        fields = event.jira_event_data.get('fields', {})
        
        # Add keywords from summary
        summary = fields.get('summary', '')
        if summary:
            # Simple keyword extraction (can be enhanced with NLP)
            summary_words = summary.lower().split()
            keywords.update(word for word in summary_words if len(word) > 3)
        
        # Add keywords from labels
        labels = fields.get('labels', [])
        keywords.update(str(label).lower() for label in labels)
        
        # Add status and priority as keywords
        status = fields.get('status', {})
        if isinstance(status, dict) and status.get('name'):
            keywords.add(status['name'].lower())
        
        priority = fields.get('priority', {})
        if isinstance(priority, dict) and priority.get('name'):
            keywords.add(priority['name'].lower())
        
        # Add issue type as keyword
        issue_type = fields.get('issuetype', {})
        if isinstance(issue_type, dict) and issue_type.get('name'):
            keywords.add(issue_type['name'].lower())
        
        return list(keywords)
    
    async def _get_enhanced_ticket_details(self, event: ProcessedEvent) -> Dict[str, Any]:
        """Get enhanced ticket details, optionally from JIRA service."""
        fields = event.jira_event_data.get('fields', {})
        
        # Basic details from webhook
        details = {
            'key': event.ticket_key,
            'summary': fields.get('summary', ''),
            'description': fields.get('description', ''),
            'created': fields.get('created'),
            'updated': fields.get('updated'),
            'labels': fields.get('labels', []),
            'components': [
                comp.get('name') for comp in fields.get('components', [])
                if isinstance(comp, dict) and comp.get('name')
            ],
            'fix_versions': [
                ver.get('name') for ver in fields.get('fixVersions', [])
                if isinstance(ver, dict) and ver.get('name')
            ]
        }
        
        # Add status information
        status = fields.get('status', {})
        if isinstance(status, dict):
            details['status'] = {
                'name': status.get('name'),
                'category': status.get('statusCategory', {}).get('name'),
                'id': status.get('id')
            }
        
        # Add priority information
        priority = fields.get('priority', {})
        if isinstance(priority, dict):
            details['priority'] = {
                'name': priority.get('name'),
                'id': priority.get('id')
            }
        
        # Add issue type information
        issue_type = fields.get('issuetype', {})
        if isinstance(issue_type, dict):
            details['issue_type'] = {
                'name': issue_type.get('name'),
                'subtask': issue_type.get('subtask', False),
                'id': issue_type.get('id')
            }
        
        # Try to get additional details from JIRA service if available
        if self.jira_service:
            try:
                enhanced_ticket = await self.jira_service.get_ticket_details(event.ticket_key)
                if enhanced_ticket:
                    details.update({
                        'story_points': enhanced_ticket.story_points,
                        'sprint': enhanced_ticket.sprint,
                        'blocked': enhanced_ticket.blocked,
                        'time_in_status': enhanced_ticket.time_in_status.total_seconds()
                    })
            except JiraAPIError as e:
                logger.warning(f"Could not fetch enhanced ticket details: {e}")
            except Exception as e:
                logger.error(f"Error fetching enhanced ticket details: {e}")
        
        return details
    
    async def _process_with_specialized_processors(self, event: ProcessedEvent) -> Dict[str, Any]:
        """Process event through specialized processors for additional enrichment."""
        try:
            enrichment_data = await self.processor_registry.process_event(event)
            return enrichment_data
        except Exception as e:
            logger.error(f"Error in specialized processor: {e}")
            return {}
    
    async def _gather_context_data(self, event: ProcessedEvent) -> Dict[str, Any]:
        """Gather additional context data for the event."""
        return {
            'processed_at': datetime.now(timezone.utc).isoformat(),
            'processor_version': '1.0.0',
            'event_source': 'jira_webhook',
            'payload_size': len(str(event.raw_payload)),
            'project_key': event.project_key,
            'ticket_key': event.ticket_key,
            'event_type': event.event_type
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processor metrics."""
        return {
            'events_processed': self._events_processed,
            'events_enriched': self._events_enriched,
            'validation_failures': self._validation_failures,
            'enrichment_failures': self._enrichment_failures,
            'success_rate': (
                self._events_enriched / self._events_processed
                if self._events_processed > 0 else 0.0
            ),
            'validation_success_rate': (
                (self._events_processed - self._validation_failures) / self._events_processed
                if self._events_processed > 0 else 0.0
            ),
            'enrichment_success_rate': (
                self._events_enriched / (self._events_processed - self._validation_failures)
                if (self._events_processed - self._validation_failures) > 0 else 0.0
            )
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the event processor."""
        try:
            metrics = self.get_metrics()
            
            # Check if JIRA service is available
            jira_service_healthy = True
            if self.jira_service:
                try:
                    await self.jira_service.test_authentication()
                except Exception:
                    jira_service_healthy = False
            
            # Determine overall health status
            status = "healthy"
            if not jira_service_healthy:
                status = "degraded"
            elif metrics['validation_success_rate'] < 0.9:
                status = "warning"
            
            return {
                'status': status,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'jira_service_available': jira_service_healthy,
                'metrics': metrics,
                'components': {
                    'event_classifier': 'ok',
                    'processor_registry': 'ok',
                    'jira_service': 'ok' if jira_service_healthy else 'degraded'
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'error',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }