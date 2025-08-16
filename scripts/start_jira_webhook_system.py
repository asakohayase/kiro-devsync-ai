#!/usr/bin/env python3
"""
Startup script for JIRA Webhook Agent Hook System.

This script initializes and starts the JIRA webhook processing system
with Agent Hooks for intelligent Slack notifications.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from devsync_ai.webhooks.jira_webhook_handler import initialize_dispatcher, shutdown_dispatcher
from devsync_ai.core.agent_hooks import HookConfiguration
from devsync_ai.config import settings


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_sample_hooks(dispatcher):
    """Create sample Agent Hooks for demonstration."""
    from devsync_ai.core.agent_hooks import AgentHook, EnrichedEvent, HookExecutionResult, HookStatus
    
    class SampleStatusChangeHook(AgentHook):
        """Sample hook for status changes."""
        
        async def can_handle(self, event: EnrichedEvent) -> bool:
            return (event.classification and 
                    event.classification.category.value == "status_change")
        
        async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
            logger.info(f"Processing status change for {event.ticket_key}")
            
            # Simulate processing
            await asyncio.sleep(0.1)
            
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.SUCCESS,
                execution_time_ms=100.0,
                notification_sent=True,
                metadata={"processed_by": "sample_hook"}
            )
    
    class SampleAssignmentHook(AgentHook):
        """Sample hook for assignments."""
        
        async def can_handle(self, event: EnrichedEvent) -> bool:
            return (event.classification and 
                    event.classification.category.value == "assignment")
        
        async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
            logger.info(f"Processing assignment for {event.ticket_key}")
            
            # Simulate processing
            await asyncio.sleep(0.1)
            
            return HookExecutionResult(
                hook_id=self.hook_id,
                execution_id="",
                hook_type=self.hook_type,
                event_id=event.event_id,
                status=HookStatus.SUCCESS,
                execution_time_ms=150.0,
                notification_sent=True,
                metadata={"processed_by": "sample_hook"}
            )
    
    # Create hook configurations
    status_config = HookConfiguration(
        hook_id="sample-status-hook",
        hook_type="StatusChangeHook",
        team_id="default",
        enabled=True,
        notification_channels=["#dev-updates"],
        rate_limit_per_hour=50,
        retry_attempts=2,
        timeout_seconds=30
    )
    
    assignment_config = HookConfiguration(
        hook_id="sample-assignment-hook",
        hook_type="AssignmentHook",
        team_id="default",
        enabled=True,
        notification_channels=["#team-assignments"],
        rate_limit_per_hour=30,
        retry_attempts=2,
        timeout_seconds=30
    )
    
    # Create and register hooks
    status_hook = SampleStatusChangeHook("sample-status-hook", status_config)
    assignment_hook = SampleAssignmentHook("sample-assignment-hook", assignment_config)
    
    await dispatcher.register_hook(status_hook)
    await dispatcher.register_hook(assignment_hook)
    
    logger.info("Sample hooks registered successfully")


async def main():
    """Main startup function."""
    logger.info("🚀 Starting JIRA Webhook Agent Hook System")
    
    try:
        # Initialize the dispatcher
        logger.info("Initializing Agent Hook Dispatcher...")
        dispatcher = await initialize_dispatcher()
        
        # Create sample hooks for demonstration
        logger.info("Creating sample Agent Hooks...")
        await create_sample_hooks(dispatcher)
        
        # Display system status
        health = await dispatcher.health_check()
        logger.info(f"System Health: {health['status']}")
        logger.info(f"Active Hooks: {health['enabled_hooks']}")
        
        # Display metrics
        metrics = dispatcher.get_metrics()
        logger.info(f"System Metrics: {metrics}")
        
        # Display webhook endpoint information
        logger.info("📡 JIRA Webhook Endpoints:")
        logger.info("  - Main webhook: POST /webhooks/jira/events")
        logger.info("  - Health check: GET /webhooks/jira/health")
        logger.info("  - Metrics: GET /webhooks/jira/metrics")
        logger.info("  - Hook management: GET /webhooks/jira/hooks")
        logger.info("  - Simulation: POST /webhooks/jira/simulate")
        
        logger.info("✅ JIRA Webhook Agent Hook System started successfully!")
        logger.info("System is ready to process JIRA webhook events")
        
        # Keep the system running
        logger.info("Press Ctrl+C to stop the system")
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute
                
                # Display periodic status
                current_metrics = dispatcher.get_metrics()
                if current_metrics['total_webhooks_received'] > metrics['total_webhooks_received']:
                    logger.info(f"📊 Processed {current_metrics['total_webhooks_received']} webhooks total")
                    metrics = current_metrics
                    
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested by user")
            
    except Exception as e:
        logger.error(f"❌ Failed to start JIRA Webhook system: {e}", exc_info=True)
        return 1
        
    finally:
        # Cleanup
        logger.info("🧹 Shutting down JIRA Webhook system...")
        try:
            await shutdown_dispatcher()
            logger.info("✅ System shutdown completed")
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
    
    return 0


def test_webhook_simulation():
    """Test the webhook system with a simulated event."""
    import json
    import requests
    
    # Sample JIRA webhook payload
    test_payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "TEST-123",
            "fields": {
                "summary": "Test issue for webhook simulation",
                "status": {"name": "In Progress"},
                "priority": {"name": "High"},
                "issuetype": {"name": "Task"},
                "assignee": {
                    "displayName": "Test User",
                    "accountId": "test-user-123"
                }
            }
        },
        "changelog": {
            "items": [
                {
                    "field": "status",
                    "fromString": "To Do",
                    "toString": "In Progress"
                }
            ]
        }
    }
    
    try:
        # Send test webhook (assumes server is running on localhost:8000)
        response = requests.post(
            "http://localhost:8000/webhooks/jira/simulate",
            json=test_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Webhook simulation successful!")
            print(f"Event ID: {result.get('event_id')}")
            print(f"Hooks processed: {result.get('hooks_processed')}")
            print(f"Processing time: {result.get('processing_time_ms')}ms")
        else:
            print(f"❌ Webhook simulation failed: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to webhook endpoint: {e}")
        print("Make sure the server is running on localhost:8000")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="JIRA Webhook Agent Hook System")
    parser.add_argument("--test", action="store_true", help="Run webhook simulation test")
    parser.add_argument("--config", help="Path to configuration file")
    
    args = parser.parse_args()
    
    if args.test:
        test_webhook_simulation()
    else:
        # Run the main system
        exit_code = asyncio.run(main())
        sys.exit(exit_code)