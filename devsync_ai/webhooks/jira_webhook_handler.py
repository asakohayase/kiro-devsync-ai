"""
JIRA Webhook Handler for Agent Hooks integration.

This module provides FastAPI endpoints and handlers for processing JIRA webhook events
through the Agent Hook system.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse

from devsync_ai.core.agent_hook_dispatcher import AgentHookDispatcher, HookDispatchResult
from devsync_ai.core.agent_hooks import HookRegistry
from devsync_ai.core.hook_lifecycle_manager import HookLifecycleManager
from devsync_ai.config import settings


logger = logging.getLogger(__name__)

# Create router for JIRA webhook endpoints
jira_webhook_router = APIRouter(prefix="/webhooks/jira", tags=["jira-webhooks"])

# Global dispatcher instance (will be initialized on startup)
_dispatcher: Optional[AgentHookDispatcher] = None


async def get_dispatcher() -> AgentHookDispatcher:
    """Get the global dispatcher instance."""
    global _dispatcher
    if _dispatcher is None:
        raise HTTPException(
            status_code=503,
            detail="Agent Hook Dispatcher not initialized"
        )
    return _dispatcher


async def initialize_dispatcher():
    """Initialize the global dispatcher instance."""
    global _dispatcher
    
    if _dispatcher is not None:
        return _dispatcher
    
    try:
        # Create hook registry and lifecycle manager
        hook_registry = HookRegistry()
        lifecycle_manager = HookLifecycleManager(hook_registry)
        
        # Start lifecycle manager
        await lifecycle_manager.start()
        
        # Create dispatcher with configuration
        webhook_secret = getattr(settings, 'jira_webhook_secret', None)
        max_requests_per_minute = getattr(settings, 'jira_webhook_rate_limit', 100)
        
        _dispatcher = AgentHookDispatcher(
            hook_registry=hook_registry,
            lifecycle_manager=lifecycle_manager,
            webhook_secret=webhook_secret,
            max_requests_per_minute=max_requests_per_minute
        )
        
        logger.info("Agent Hook Dispatcher initialized successfully")
        return _dispatcher
        
    except Exception as e:
        logger.error(f"Failed to initialize Agent Hook Dispatcher: {e}")
        raise


async def shutdown_dispatcher():
    """Shutdown the global dispatcher instance."""
    global _dispatcher
    
    if _dispatcher is not None:
        try:
            await _dispatcher.lifecycle_manager.stop()
            _dispatcher = None
            logger.info("Agent Hook Dispatcher shutdown successfully")
        except Exception as e:
            logger.error(f"Error shutting down Agent Hook Dispatcher: {e}")


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    # Check for forwarded headers first (for load balancers/proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    if hasattr(request, "client") and request.client:
        return request.client.host
    
    return "unknown"


@jira_webhook_router.post("/events")
async def handle_jira_webhook(
    request: Request,
    dispatcher: AgentHookDispatcher = Depends(get_dispatcher),
    x_atlassian_webhook_identifier: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None)
) -> JSONResponse:
    """
    Handle JIRA webhook events and route them to Agent Hooks.
    
    This endpoint receives JIRA webhook events, validates them, and dispatches
    them to appropriate Agent Hooks for processing.
    """
    start_time = datetime.now(timezone.utc)
    client_ip = get_client_ip(request)
    
    logger.info(
        f"🚀 Received JIRA webhook from {client_ip} "
        f"(identifier: {x_atlassian_webhook_identifier})"
    )
    
    try:
        # Get raw payload for signature verification
        raw_payload = await request.body()
        payload_size = len(raw_payload)
        
        logger.debug(f"📦 Webhook payload size: {payload_size} bytes")
        
        # Parse JSON payload
        try:
            webhook_data = json.loads(raw_payload.decode('utf-8'))
            logger.debug("✅ Successfully parsed JIRA webhook JSON")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in JIRA webhook: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON payload: {str(e)}"
            )
        
        # Extract event information for logging
        webhook_event = webhook_data.get('webhookEvent', 'unknown')
        issue_key = webhook_data.get('issue', {}).get('key', 'unknown')
        
        logger.info(f"📋 JIRA Event: {webhook_event} for issue {issue_key}")
        
        # Dispatch to Agent Hooks
        dispatch_result = await dispatcher.dispatch_webhook_event(
            webhook_data=webhook_data,
            signature=x_hub_signature_256,
            client_ip=client_ip
        )
        
        # Calculate total processing time
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        # Log results
        if dispatch_result.errors:
            logger.warning(
                f"⚠️ JIRA webhook processed with errors: {len(dispatch_result.errors)} errors, "
                f"{dispatch_result.successful_hooks}/{dispatch_result.processed_hooks} hooks successful"
            )
        else:
            logger.info(
                f"✅ JIRA webhook processed successfully: "
                f"{dispatch_result.successful_hooks}/{dispatch_result.processed_hooks} hooks executed "
                f"in {processing_time:.2f}ms"
            )
        
        # Prepare response
        response_data = {
            "status": "success" if not dispatch_result.errors else "partial_success",
            "message": f"Processed {webhook_event} for {issue_key}",
            "event_id": dispatch_result.event_id,
            "webhook_event": webhook_event,
            "issue_key": issue_key,
            "processing": {
                "total_time_ms": processing_time,
                "hooks_processed": dispatch_result.processed_hooks,
                "hooks_successful": dispatch_result.successful_hooks,
                "hooks_failed": dispatch_result.failed_hooks
            },
            "timestamp": start_time.isoformat()
        }
        
        # Add errors if any
        if dispatch_result.errors:
            response_data["errors"] = dispatch_result.errors
        
        # Add hook execution details in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            response_data["hook_executions"] = [
                {
                    "hook_id": result.hook_id,
                    "hook_type": result.hook_type,
                    "status": result.status.value,
                    "execution_time_ms": result.execution_time_ms,
                    "notification_sent": result.notification_sent,
                    "errors": result.errors
                }
                for result in dispatch_result.execution_results
            ]
        
        return JSONResponse(
            content=response_data,
            status_code=200
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (rate limiting, validation errors)
        raise
        
    except Exception as e:
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        logger.error(
            f"❌ JIRA webhook processing failed: {str(e)} "
            f"(processed in {processing_time:.2f}ms)",
            exc_info=True
        )
        
        # Return error response but don't raise exception to prevent webhook retries
        return JSONResponse(
            content={
                "status": "error",
                "message": f"Webhook processing failed: {str(e)}",
                "error_type": type(e).__name__,
                "processing_time_ms": processing_time,
                "timestamp": start_time.isoformat()
            },
            status_code=200  # Return 200 to prevent JIRA retries
        )


@jira_webhook_router.get("/health")
async def jira_webhook_health(
    dispatcher: AgentHookDispatcher = Depends(get_dispatcher)
) -> JSONResponse:
    """
    Health check endpoint for JIRA webhook system.
    
    Returns detailed health information about the Agent Hook system.
    """
    try:
        health_status = await dispatcher.health_check()
        
        # Add additional system information
        health_status.update({
            "webhook_endpoint": "operational",
            "jira_integration": "enabled",
            "agent_hooks": "enabled"
        })
        
        # Determine HTTP status code based on health
        status_code = 200
        if health_status.get("status") == "error":
            status_code = 503
        elif health_status.get("status") in ["degraded", "warning"]:
            status_code = 200  # Still operational but with issues
        
        return JSONResponse(
            content=health_status,
            status_code=status_code
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "message": f"Health check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            status_code=503
        )


@jira_webhook_router.get("/metrics")
async def jira_webhook_metrics(
    dispatcher: AgentHookDispatcher = Depends(get_dispatcher)
) -> JSONResponse:
    """
    Get metrics for JIRA webhook processing.
    
    Returns detailed metrics about webhook processing and hook execution.
    """
    try:
        metrics = dispatcher.get_metrics()
        
        # Add timestamp
        metrics["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return JSONResponse(content=metrics)
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return JSONResponse(
            content={
                "error": f"Failed to get metrics: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            status_code=500
        )


@jira_webhook_router.get("/hooks")
async def list_active_hooks(
    dispatcher: AgentHookDispatcher = Depends(get_dispatcher)
) -> JSONResponse:
    """
    List all active Agent Hooks.
    
    Returns information about all registered and enabled hooks.
    """
    try:
        active_hooks = await dispatcher.get_active_hooks()
        
        hooks_info = []
        for hook in active_hooks:
            hook_info = {
                "hook_id": hook.hook_id,
                "hook_type": hook.hook_type,
                "enabled": hook.enabled,
                "team_id": hook.configuration.team_id,
                "notification_channels": hook.configuration.notification_channels,
                "rate_limit_per_hour": hook.configuration.rate_limit_per_hour,
                "retry_attempts": hook.configuration.retry_attempts,
                "timeout_seconds": hook.configuration.timeout_seconds
            }
            hooks_info.append(hook_info)
        
        return JSONResponse(
            content={
                "total_hooks": len(hooks_info),
                "hooks": hooks_info,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to list hooks: {e}")
        return JSONResponse(
            content={
                "error": f"Failed to list hooks: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            status_code=500
        )


@jira_webhook_router.post("/hooks/{hook_id}/enable")
async def enable_hook(
    hook_id: str,
    dispatcher: AgentHookDispatcher = Depends(get_dispatcher)
) -> JSONResponse:
    """Enable a specific Agent Hook."""
    try:
        hook = dispatcher.hook_registry.get_hook(hook_id)
        if not hook:
            raise HTTPException(status_code=404, detail=f"Hook {hook_id} not found")
        
        hook.enable()
        
        return JSONResponse(
            content={
                "message": f"Hook {hook_id} enabled successfully",
                "hook_id": hook_id,
                "enabled": hook.enabled,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable hook {hook_id}: {e}")
        return JSONResponse(
            content={
                "error": f"Failed to enable hook: {str(e)}",
                "hook_id": hook_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            status_code=500
        )


@jira_webhook_router.post("/hooks/{hook_id}/disable")
async def disable_hook(
    hook_id: str,
    dispatcher: AgentHookDispatcher = Depends(get_dispatcher)
) -> JSONResponse:
    """Disable a specific Agent Hook."""
    try:
        hook = dispatcher.hook_registry.get_hook(hook_id)
        if not hook:
            raise HTTPException(status_code=404, detail=f"Hook {hook_id} not found")
        
        hook.disable()
        
        return JSONResponse(
            content={
                "message": f"Hook {hook_id} disabled successfully",
                "hook_id": hook_id,
                "enabled": hook.enabled,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable hook {hook_id}: {e}")
        return JSONResponse(
            content={
                "error": f"Failed to disable hook: {str(e)}",
                "hook_id": hook_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            status_code=500
        )


@jira_webhook_router.get("/hooks/{hook_id}/stats")
async def get_hook_statistics(
    hook_id: str,
    dispatcher: AgentHookDispatcher = Depends(get_dispatcher)
) -> JSONResponse:
    """Get statistics for a specific Agent Hook."""
    try:
        hook = dispatcher.hook_registry.get_hook(hook_id)
        if not hook:
            raise HTTPException(status_code=404, detail=f"Hook {hook_id} not found")
        
        stats = dispatcher.lifecycle_manager.get_hook_statistics(hook_id)
        stats["hook_id"] = hook_id
        stats["hook_type"] = hook.hook_type
        stats["enabled"] = hook.enabled
        stats["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return JSONResponse(content=stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get hook statistics for {hook_id}: {e}")
        return JSONResponse(
            content={
                "error": f"Failed to get hook statistics: {str(e)}",
                "hook_id": hook_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            status_code=500
        )


# Event simulation endpoint for testing
@jira_webhook_router.post("/simulate")
async def simulate_jira_event(
    request: Request,
    dispatcher: AgentHookDispatcher = Depends(get_dispatcher)
) -> JSONResponse:
    """
    Simulate a JIRA webhook event for testing purposes.
    
    This endpoint allows testing the Agent Hook system with mock JIRA events.
    """
    try:
        # Parse the simulated event data
        event_data = await request.json()
        
        # Add required JIRA webhook structure if missing
        if "webhookEvent" not in event_data:
            event_data["webhookEvent"] = "jira:issue_updated"
        
        if "issue" not in event_data and "webhookEvent" in event_data and "issue" in event_data["webhookEvent"]:
            # Create minimal issue structure for testing
            event_data["issue"] = {
                "key": "TEST-123",
                "fields": {
                    "summary": "Test Issue",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "Medium"},
                    "issuetype": {"name": "Task"}
                }
            }
        
        logger.info(f"🧪 Simulating JIRA event: {event_data.get('webhookEvent')}")
        
        # Process through dispatcher
        dispatch_result = await dispatcher.dispatch_webhook_event(
            webhook_data=event_data,
            client_ip="127.0.0.1"  # Localhost for simulation
        )
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Simulated event processed successfully",
                "event_id": dispatch_result.event_id,
                "hooks_processed": dispatch_result.processed_hooks,
                "hooks_successful": dispatch_result.successful_hooks,
                "hooks_failed": dispatch_result.failed_hooks,
                "processing_time_ms": dispatch_result.processing_time_ms,
                "errors": dispatch_result.errors,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to simulate JIRA event: {e}")
        return JSONResponse(
            content={
                "error": f"Failed to simulate event: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            status_code=500
        )