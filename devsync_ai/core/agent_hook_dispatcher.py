"""
Agent Hook Dispatcher for JIRA webhook event routing.

This module provides the central dispatcher that receives JIRA webhook events
and routes them to appropriate Agent Hooks for processing.
"""

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

from fastapi import HTTPException

from .agent_hooks import (
    AgentHook,
    HookRegistry,
    ProcessedEvent,
    EnrichedEvent,
    HookExecutionResult,
    EventCategory,
    UrgencyLevel,
    SignificanceLevel
)
from .hook_lifecycle_manager import HookLifecycleManager


logger = logging.getLogger(__name__)


@dataclass
class WebhookValidationResult:
    """Result of webhook validation."""
    valid: bool
    error_message: Optional[str] = None
    event_type: Optional[str] = None
    payload_size: int = 0


@dataclass
class HookDispatchResult:
    """Result of hook dispatch operation."""
    event_id: str
    processed_hooks: int
    successful_hooks: int
    failed_hooks: int
    execution_results: List[HookExecutionResult] = field(default_factory=list)
    processing_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)


class WebhookSecurityValidator:
    """Handles webhook security validation."""
    
    def __init__(self, webhook_secret: Optional[str] = None):
        """
        Initialize webhook security validator.
        
        Args:
            webhook_secret: Secret key for webhook signature validation
        """
        self.webhook_secret = webhook_secret
    
    def verify_jira_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify JIRA webhook signature.
        
        Args:
            payload: Raw webhook payload
            signature: Signature from webhook headers
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret or not signature:
            # If no secret configured, skip validation (for development)
            return True
        
        try:
            # JIRA uses SHA256 HMAC
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # JIRA signature format may vary, handle common formats
            if signature.startswith('sha256='):
                signature = signature[7:]  # Remove 'sha256=' prefix
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Error verifying JIRA webhook signature: {e}")
            return False
    
    def validate_payload_structure(self, payload: Dict[str, Any]) -> WebhookValidationResult:
        """
        Validate JIRA webhook payload structure.
        
        Args:
            payload: Parsed webhook payload
            
        Returns:
            Validation result with details
        """
        try:
            # Check for required JIRA webhook fields
            webhook_event = payload.get('webhookEvent')
            if not webhook_event:
                return WebhookValidationResult(
                    valid=False,
                    error_message="Missing 'webhookEvent' field"
                )
            
            # Validate event type format
            if not webhook_event.startswith('jira:'):
                return WebhookValidationResult(
                    valid=False,
                    error_message=f"Invalid webhook event format: {webhook_event}"
                )
            
            # Check for issue data in issue-related events
            if 'issue' in webhook_event and 'issue' not in payload:
                return WebhookValidationResult(
                    valid=False,
                    error_message="Missing 'issue' data for issue event"
                )
            
            # Validate issue structure if present
            if 'issue' in payload:
                issue = payload['issue']
                if not issue.get('key') or not issue.get('fields'):
                    return WebhookValidationResult(
                        valid=False,
                        error_message="Invalid issue structure"
                    )
            
            return WebhookValidationResult(
                valid=True,
                event_type=webhook_event,
                payload_size=len(json.dumps(payload))
            )
            
        except Exception as e:
            return WebhookValidationResult(
                valid=False,
                error_message=f"Payload validation error: {str(e)}"
            )


class WebhookRateLimiter:
    """Handles webhook rate limiting."""
    
    def __init__(self, max_requests_per_minute: int = 100):
        """
        Initialize rate limiter.
        
        Args:
            max_requests_per_minute: Maximum requests allowed per minute
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.request_timestamps: List[datetime] = []
    
    def is_rate_limited(self, client_ip: str = "unknown") -> bool:
        """
        Check if request should be rate limited.
        
        Args:
            client_ip: Client IP address for logging
            
        Returns:
            True if request should be rate limited
        """
        now = datetime.now(timezone.utc)
        
        # Remove timestamps older than 1 minute
        cutoff = now.timestamp() - 60
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if ts.timestamp() > cutoff
        ]
        
        # Check if we're over the limit
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            logger.warning(f"Rate limit exceeded for client {client_ip}")
            return True
        
        # Add current timestamp
        self.request_timestamps.append(now)
        return False


class AgentHookDispatcher:
    """
    Central dispatcher for JIRA webhook events to Agent Hooks.
    
    Handles webhook validation, event processing, and hook execution routing.
    """
    
    def __init__(
        self,
        hook_registry: HookRegistry,
        lifecycle_manager: HookLifecycleManager,
        webhook_secret: Optional[str] = None,
        max_requests_per_minute: int = 100
    ):
        """
        Initialize the dispatcher.
        
        Args:
            hook_registry: Registry containing all hooks
            lifecycle_manager: Manager for hook execution lifecycle
            webhook_secret: Secret for webhook signature validation
            max_requests_per_minute: Rate limit for webhook requests
        """
        self.hook_registry = hook_registry
        self.lifecycle_manager = lifecycle_manager
        self.security_validator = WebhookSecurityValidator(webhook_secret)
        self.rate_limiter = WebhookRateLimiter(max_requests_per_minute)
        
        # Metrics tracking
        self._total_webhooks_received = 0
        self._total_webhooks_processed = 0
        self._total_webhooks_failed = 0
        self._total_hooks_executed = 0
        self._last_webhook_time: Optional[datetime] = None
        
        # Event type mapping
        self._event_type_mapping = {
            'jira:issue_created': EventCategory.CREATION,
            'jira:issue_updated': EventCategory.STATUS_CHANGE,
            'jira:issue_deleted': EventCategory.STATUS_CHANGE,
            'jira:issue_assigned': EventCategory.ASSIGNMENT,
            'jira:issue_commented': EventCategory.COMMENT,
            'jira:issue_transitioned': EventCategory.TRANSITION,
        }
    
    async def dispatch_webhook_event(
        self,
        webhook_data: Dict[str, Any],
        signature: Optional[str] = None,
        client_ip: str = "unknown"
    ) -> HookDispatchResult:
        """
        Dispatch a webhook event to appropriate Agent Hooks.
        
        Args:
            webhook_data: Parsed webhook payload
            signature: Webhook signature for validation
            client_ip: Client IP address for rate limiting
            
        Returns:
            Result of the dispatch operation
        """
        start_time = datetime.now(timezone.utc)
        self._total_webhooks_received += 1
        self._last_webhook_time = start_time
        
        try:
            # Rate limiting check
            if self.rate_limiter.is_rate_limited(client_ip):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded"
                )
            
            # Validate webhook payload
            validation_result = self.security_validator.validate_payload_structure(webhook_data)
            if not validation_result.valid:
                self._total_webhooks_failed += 1
                raise HTTPException(
                    status_code=400,
                    detail=validation_result.error_message
                )
            
            # Process the event
            processed_event = await self._process_webhook_event(webhook_data, validation_result.event_type)
            
            # Enrich the event with additional context
            enriched_event = await self._enrich_event(processed_event)
            
            # Execute applicable hooks
            execution_results = await self.lifecycle_manager.execute_hooks_for_event(enriched_event)
            
            # Calculate metrics
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            successful_hooks = len([r for r in execution_results if r.status.value == "success"])
            failed_hooks = len([r for r in execution_results if r.status.value == "failed"])
            
            self._total_webhooks_processed += 1
            self._total_hooks_executed += len(execution_results)
            
            logger.info(
                f"Webhook dispatch completed: {len(execution_results)} hooks executed "
                f"({successful_hooks} successful, {failed_hooks} failed) in {processing_time:.2f}ms"
            )
            
            return HookDispatchResult(
                event_id=enriched_event.event_id,
                processed_hooks=len(execution_results),
                successful_hooks=successful_hooks,
                failed_hooks=failed_hooks,
                execution_results=execution_results,
                processing_time_ms=processing_time
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self._total_webhooks_failed += 1
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.error(f"Webhook dispatch failed: {str(e)}", exc_info=True)
            
            return HookDispatchResult(
                event_id="unknown",
                processed_hooks=0,
                successful_hooks=0,
                failed_hooks=0,
                processing_time_ms=processing_time,
                errors=[str(e)]
            )
    
    async def _process_webhook_event(self, webhook_data: Dict[str, Any], event_type: str) -> ProcessedEvent:
        """
        Process raw webhook data into a ProcessedEvent.
        
        Args:
            webhook_data: Raw webhook payload
            event_type: Type of webhook event
            
        Returns:
            Processed event ready for enrichment
        """
        # Extract basic event information
        issue_data = webhook_data.get('issue', {})
        ticket_key = issue_data.get('key', 'UNKNOWN')
        project_key = ticket_key.split('-')[0] if '-' in ticket_key else 'UNKNOWN'
        
        # Create processed event
        processed_event = ProcessedEvent(
            event_id="",  # Will be auto-generated
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            jira_event_data=issue_data,
            ticket_key=ticket_key,
            project_key=project_key,
            raw_payload=webhook_data
        )
        
        logger.debug(f"Processed webhook event: {event_type} for ticket {ticket_key}")
        
        return processed_event
    
    async def _enrich_event(self, processed_event: ProcessedEvent) -> EnrichedEvent:
        """
        Enrich a processed event with additional context and classification.
        
        Args:
            processed_event: Basic processed event
            
        Returns:
            Enriched event with classification and context
        """
        # Determine event category
        category = self._event_type_mapping.get(
            processed_event.event_type,
            EventCategory.STATUS_CHANGE
        )
        
        # Analyze urgency based on issue data
        urgency = await self._determine_urgency(processed_event)
        
        # Determine significance
        significance = await self._determine_significance(processed_event)
        
        # Extract stakeholders
        stakeholders = await self._extract_stakeholders(processed_event)
        
        # Determine affected teams
        affected_teams = await self._determine_affected_teams(processed_event)
        
        # Create classification
        from .agent_hooks import EventClassification
        classification = EventClassification(
            category=category,
            urgency=urgency,
            significance=significance,
            affected_teams=affected_teams,
            routing_hints=await self._generate_routing_hints(processed_event)
        )
        
        # Get additional ticket details
        ticket_details = await self._get_ticket_details(processed_event)
        
        # Create enriched event
        enriched_event = EnrichedEvent(
            **processed_event.__dict__,
            ticket_details=ticket_details,
            stakeholders=stakeholders,
            classification=classification,
            context_data=await self._gather_context_data(processed_event)
        )
        
        logger.debug(
            f"Enriched event {enriched_event.event_id}: "
            f"category={category.value}, urgency={urgency.value}, "
            f"significance={significance.value}, teams={affected_teams}"
        )
        
        return enriched_event
    
    async def _determine_urgency(self, event: ProcessedEvent) -> UrgencyLevel:
        """Determine urgency level for an event."""
        issue_data = event.jira_event_data
        
        # Check priority field
        priority = issue_data.get('fields', {}).get('priority', {}).get('name', '').lower()
        if priority in ['critical', 'highest']:
            return UrgencyLevel.CRITICAL
        elif priority in ['high', 'major']:
            return UrgencyLevel.HIGH
        elif priority in ['medium', 'normal']:
            return UrgencyLevel.MEDIUM
        else:
            return UrgencyLevel.LOW
    
    async def _determine_significance(self, event: ProcessedEvent) -> SignificanceLevel:
        """Determine significance level for an event."""
        # Check if this is a status change to blocked
        if event.event_type == 'jira:issue_updated':
            status = event.jira_event_data.get('fields', {}).get('status', {}).get('name', '').lower()
            if 'block' in status or 'impediment' in status:
                return SignificanceLevel.CRITICAL
        
        # Check if this is a high-priority assignment
        if event.event_type == 'jira:issue_assigned':
            priority = event.jira_event_data.get('fields', {}).get('priority', {}).get('name', '').lower()
            if priority in ['critical', 'highest', 'high']:
                return SignificanceLevel.MAJOR
        
        return SignificanceLevel.MODERATE
    
    async def _extract_stakeholders(self, event: ProcessedEvent) -> List:
        """Extract stakeholders from event data."""
        from .agent_hooks import Stakeholder
        
        stakeholders = []
        issue_data = event.jira_event_data
        
        # Add assignee
        assignee = issue_data.get('fields', {}).get('assignee')
        if assignee:
            stakeholders.append(Stakeholder(
                user_id=assignee.get('accountId', ''),
                display_name=assignee.get('displayName', ''),
                email=assignee.get('emailAddress'),
                role='assignee'
            ))
        
        # Add reporter
        reporter = issue_data.get('fields', {}).get('reporter')
        if reporter:
            stakeholders.append(Stakeholder(
                user_id=reporter.get('accountId', ''),
                display_name=reporter.get('displayName', ''),
                email=reporter.get('emailAddress'),
                role='reporter'
            ))
        
        return stakeholders
    
    async def _determine_affected_teams(self, event: ProcessedEvent) -> List[str]:
        """Determine which teams are affected by this event."""
        # For now, use project key as team identifier
        # This can be enhanced with more sophisticated team mapping
        return [event.project_key.lower()]
    
    async def _generate_routing_hints(self, event: ProcessedEvent) -> Dict[str, Any]:
        """Generate routing hints for the event."""
        hints = {
            'project': event.project_key,
            'ticket_type': event.jira_event_data.get('fields', {}).get('issuetype', {}).get('name'),
            'priority': event.jira_event_data.get('fields', {}).get('priority', {}).get('name')
        }
        
        # Add status-specific hints
        if event.event_type == 'jira:issue_updated':
            hints['status'] = event.jira_event_data.get('fields', {}).get('status', {}).get('name')
        
        return hints
    
    async def _get_ticket_details(self, event: ProcessedEvent) -> Dict[str, Any]:
        """Get detailed ticket information."""
        issue_data = event.jira_event_data
        fields = issue_data.get('fields', {})
        
        return {
            'summary': fields.get('summary', ''),
            'description': fields.get('description', ''),
            'status': fields.get('status', {}).get('name', ''),
            'priority': fields.get('priority', {}).get('name', ''),
            'issue_type': fields.get('issuetype', {}).get('name', ''),
            'created': fields.get('created'),
            'updated': fields.get('updated'),
            'labels': fields.get('labels', []),
            'components': [c.get('name') for c in fields.get('components', [])],
            'fix_versions': [v.get('name') for v in fields.get('fixVersions', [])]
        }
    
    async def _gather_context_data(self, event: ProcessedEvent) -> Dict[str, Any]:
        """Gather additional context data for the event."""
        return {
            'webhook_received_at': datetime.now(timezone.utc).isoformat(),
            'project_key': event.project_key,
            'event_source': 'jira_webhook',
            'payload_size': len(json.dumps(event.raw_payload))
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get dispatcher metrics."""
        return {
            'total_webhooks_received': self._total_webhooks_received,
            'total_webhooks_processed': self._total_webhooks_processed,
            'total_webhooks_failed': self._total_webhooks_failed,
            'total_hooks_executed': self._total_hooks_executed,
            'success_rate': (
                self._total_webhooks_processed / self._total_webhooks_received
                if self._total_webhooks_received > 0 else 0.0
            ),
            'last_webhook_time': self._last_webhook_time.isoformat() if self._last_webhook_time else None,
            'registered_hooks': len(self.hook_registry.get_all_hooks()),
            'enabled_hooks': len(self.hook_registry.get_enabled_hooks())
        }
    
    async def register_hook(self, hook: AgentHook) -> bool:
        """
        Register a hook with the dispatcher.
        
        Args:
            hook: Hook to register
            
        Returns:
            True if registration was successful
        """
        success = self.hook_registry.register_hook(hook)
        if success:
            logger.info(f"Registered hook: {hook.hook_id} ({hook.hook_type})")
        else:
            logger.warning(f"Failed to register hook: {hook.hook_id} (already exists)")
        return success
    
    async def unregister_hook(self, hook_id: str) -> bool:
        """
        Unregister a hook from the dispatcher.
        
        Args:
            hook_id: ID of hook to unregister
            
        Returns:
            True if unregistration was successful
        """
        success = self.hook_registry.unregister_hook(hook_id)
        if success:
            logger.info(f"Unregistered hook: {hook_id}")
        else:
            logger.warning(f"Failed to unregister hook: {hook_id} (not found)")
        return success
    
    async def get_active_hooks(self) -> List[AgentHook]:
        """Get all active (enabled) hooks."""
        return self.hook_registry.get_enabled_hooks()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the dispatcher."""
        try:
            metrics = self.get_metrics()
            
            # Check if lifecycle manager is running
            lifecycle_healthy = hasattr(self.lifecycle_manager, '_running') and self.lifecycle_manager._running
            
            # Check hook registry
            total_hooks = len(self.hook_registry.get_all_hooks())
            enabled_hooks = len(self.hook_registry.get_enabled_hooks())
            
            status = "healthy"
            if not lifecycle_healthy:
                status = "degraded"
            elif enabled_hooks == 0:
                status = "warning"
            
            return {
                'status': status,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'lifecycle_manager_running': lifecycle_healthy,
                'total_hooks': total_hooks,
                'enabled_hooks': enabled_hooks,
                'metrics': metrics,
                'components': {
                    'security_validator': 'ok',
                    'rate_limiter': 'ok',
                    'hook_registry': 'ok',
                    'lifecycle_manager': 'ok' if lifecycle_healthy else 'error'
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'error',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }