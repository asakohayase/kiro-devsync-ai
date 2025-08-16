#!/usr/bin/env python3
"""
Startup script for the enhanced notification system.
Initializes and starts all components of the notification system.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from devsync_ai.core.notification_integration import NotificationSystem, NotificationSystemConfig
from devsync_ai.notification.config import NotificationConfigManager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('notification_system.log')
    ]
)

logger = logging.getLogger(__name__)


class NotificationSystemRunner:
    """Runner for the enhanced notification system."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize the runner."""
        self.config_file = config_file
        self.system: Optional[NotificationSystem] = None
        self.running = False
        
    async def start(self) -> bool:
        """Start the notification system."""
        try:
            logger.info("🚀 Starting Enhanced Notification System")
            
            # Load configuration
            config_manager = NotificationConfigManager(self.config_file)
            system_config = config_manager.load_config()
            
            logger.info(f"📋 Configuration loaded:")
            logger.info(f"  - System enabled: {system_config.enabled}")
            logger.info(f"  - Debug mode: {system_config.debug_mode}")
            logger.info(f"  - Analytics enabled: {system_config.analytics_enabled}")
            logger.info(f"  - Work hours: {system_config.work_hours.start_hour}:00 - {system_config.work_hours.end_hour}:00")
            logger.info(f"  - Timezone: {system_config.work_hours.timezone}")
            
            # Create notification system
            self.system = NotificationSystem(system_config)
            
            # Initialize system
            logger.info("🔧 Initializing notification system...")
            if not await self.system.initialize():
                logger.error("❌ Failed to initialize notification system")
                return False
            
            # Start system
            logger.info("▶️ Starting notification system...")
            if not await self.system.start():
                logger.error("❌ Failed to start notification system")
                return False
            
            self.running = True
            
            # Display system status
            await self._display_system_status()
            
            logger.info("✅ Enhanced Notification System started successfully!")
            logger.info("📊 System is now processing notifications...")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start notification system: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the notification system."""
        if not self.system or not self.running:
            return True
        
        try:
            logger.info("🛑 Stopping Enhanced Notification System...")
            
            # Stop the system
            if not await self.system.stop():
                logger.warning("⚠️ System did not stop cleanly")
            
            self.running = False
            logger.info("✅ Enhanced Notification System stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping notification system: {e}")
            return False
    
    async def _display_system_status(self) -> None:
        """Display current system status."""
        try:
            if not self.system:
                return
            
            # Get health status
            health = await self.system.get_health_status()
            
            logger.info("📊 System Status:")
            logger.info(f"  - Overall Health: {health['status']}")
            
            for component, status in health['components'].items():
                logger.info(f"  - {component.title()}: {status}")
            
            if health['issues']:
                logger.warning("⚠️ Issues detected:")
                for issue in health['issues']:
                    logger.warning(f"    - {issue}")
            
            # Get basic statistics
            stats = await self.system.get_system_stats()
            handler_stats = stats.get('handler', {})
            
            logger.info("📈 Processing Statistics:")
            logger.info(f"  - Total processed: {handler_stats.get('total_processed', 0)}")
            logger.info(f"  - Sent immediately: {handler_stats.get('sent_immediately', 0)}")
            logger.info(f"  - Batched: {handler_stats.get('batched', 0)}")
            logger.info(f"  - Scheduled: {handler_stats.get('scheduled', 0)}")
            logger.info(f"  - Filtered out: {handler_stats.get('filtered_out', 0)}")
            logger.info(f"  - Duplicates skipped: {handler_stats.get('duplicates_skipped', 0)}")
            
        except Exception as e:
            logger.error(f"Error displaying system status: {e}")
    
    async def run_forever(self) -> None:
        """Run the system until interrupted."""
        if not self.running:
            logger.error("System not started")
            return
        
        try:
            logger.info("🔄 Running notification system (Ctrl+C to stop)...")
            
            # Set up signal handlers
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, initiating shutdown...")
                asyncio.create_task(self.stop())
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Run periodic status updates
            while self.running:
                await asyncio.sleep(300)  # 5 minutes
                
                if self.running:  # Check again in case we're shutting down
                    logger.info("📊 Periodic status update:")
                    await self._display_system_status()
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            await self.stop()
    
    async def test_system(self) -> bool:
        """Run system tests."""
        try:
            logger.info("🧪 Running system tests...")
            
            if not self.system or not self.running:
                logger.error("System not running")
                return False
            
            # Test 1: Send a test notification
            logger.info("Test 1: Sending test notification...")
            result = await self.system.send_notification(
                notification_type="pr_new",
                event_type="pull_request.opened",
                data={
                    "pr": {
                        "number": 999,
                        "title": "Test PR for system validation",
                        "user": {"login": "system-test"},
                        "html_url": "https://github.com/test/repo/pull/999"
                    }
                },
                team_id="test_team"
            )
            
            logger.info(f"✅ Test notification result: {result.decision.value} - {result.reason}")
            
            # Test 2: Check system health
            logger.info("Test 2: Checking system health...")
            health = await self.system.get_health_status()
            logger.info(f"✅ System health: {health['status']}")
            
            # Test 3: Get system statistics
            logger.info("Test 3: Getting system statistics...")
            stats = await self.system.get_system_stats()
            logger.info(f"✅ System stats retrieved: {len(stats)} categories")
            
            # Test 4: Force scheduler run
            logger.info("Test 4: Testing scheduler...")
            scheduler_result = await self.system.force_scheduler_run()
            logger.info(f"✅ Scheduler test: {scheduler_result}")
            
            logger.info("✅ All system tests passed!")
            return True
            
        except Exception as e:
            logger.error(f"❌ System test failed: {e}")
            return False


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Notification System")
    parser.add_argument(
        "--config", 
        type=str, 
        help="Path to configuration file"
    )
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="Run system tests and exit"
    )
    parser.add_argument(
        "--create-config", 
        type=str, 
        help="Create example configuration file at specified path"
    )
    parser.add_argument(
        "--validate-config", 
        type=str, 
        help="Validate configuration file"
    )
    
    args = parser.parse_args()
    
    # Handle configuration creation
    if args.create_config:
        from devsync_ai.notification.config import NotificationConfigManager
        config_manager = NotificationConfigManager()
        
        if config_manager.create_example_config(args.create_config):
            logger.info(f"✅ Example configuration created at {args.create_config}")
            return 0
        else:
            logger.error(f"❌ Failed to create configuration at {args.create_config}")
            return 1
    
    # Handle configuration validation
    if args.validate_config:
        from devsync_ai.notification.config import NotificationConfigManager
        config_manager = NotificationConfigManager()
        
        try:
            config = config_manager.load_config(args.validate_config)
            logger.info(f"✅ Configuration file {args.validate_config} is valid")
            logger.info(f"📋 System enabled: {config.enabled}")
            logger.info(f"📋 Analytics enabled: {config.analytics_enabled}")
            return 0
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            return 1
    
    # Start the notification system
    runner = NotificationSystemRunner(args.config)
    
    if not await runner.start():
        logger.error("❌ Failed to start notification system")
        return 1
    
    # Run tests if requested
    if args.test:
        if await runner.test_system():
            logger.info("✅ All tests passed")
            await runner.stop()
            return 0
        else:
            logger.error("❌ Tests failed")
            await runner.stop()
            return 1
    
    # Run forever
    try:
        await runner.run_forever()
        return 0
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)