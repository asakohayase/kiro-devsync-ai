#!/usr/bin/env python3
"""
Startup script for DevSync AI Analytics Dashboard.

This script starts the comprehensive monitoring and analytics system
with all components properly initialized.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn
from devsync_ai.analytics.dashboard_api import analytics_app
from devsync_ai.analytics.hook_monitoring_dashboard import get_dashboard, shutdown_dashboard
from devsync_ai.analytics.analytics_data_manager import get_analytics_data_manager, shutdown_analytics_data_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('analytics_dashboard.log')
    ]
)

logger = logging.getLogger(__name__)


class AnalyticsDashboardServer:
    """Analytics dashboard server with proper lifecycle management."""
    
    def __init__(self):
        self.dashboard = None
        self.data_manager = None
        self.server = None
        self.shutdown_event = asyncio.Event()
    
    async def startup(self):
        """Initialize all analytics components."""
        try:
            logger.info("Starting DevSync AI Analytics Dashboard...")
            
            # Initialize data manager
            logger.info("Initializing analytics data manager...")
            self.data_manager = await get_analytics_data_manager()
            
            # Initialize monitoring dashboard
            logger.info("Initializing monitoring dashboard...")
            self.dashboard = await get_dashboard()
            
            # Add startup event to FastAPI app
            @analytics_app.on_event("startup")
            async def startup_event():
                logger.info("FastAPI application started")
            
            @analytics_app.on_event("shutdown")
            async def shutdown_event():
                logger.info("FastAPI application shutting down")
                await self.shutdown()
            
            logger.info("Analytics dashboard components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize analytics dashboard: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown all analytics components."""
        try:
            logger.info("Shutting down analytics dashboard...")
            
            # Shutdown monitoring dashboard
            if self.dashboard:
                await shutdown_dashboard()
            
            # Shutdown data manager
            if self.data_manager:
                await shutdown_analytics_data_manager()
            
            logger.info("Analytics dashboard shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self, host: str = "0.0.0.0", port: int = 8001):
        """Run the analytics dashboard server."""
        try:
            # Initialize components
            await self.startup()
            
            # Setup signal handlers
            self.setup_signal_handlers()
            
            # Create server configuration
            config = uvicorn.Config(
                app=analytics_app,
                host=host,
                port=port,
                log_level="info",
                access_log=True,
                reload=False  # Disable reload in production
            )
            
            # Create and start server
            server = uvicorn.Server(config)
            
            logger.info(f"Starting analytics dashboard server on {host}:{port}")
            logger.info(f"Dashboard URL: http://{host}:{port}")
            logger.info(f"API Documentation: http://{host}:{port}/docs")
            
            # Run server with graceful shutdown
            await self._run_with_shutdown(server)
            
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def _run_with_shutdown(self, server):
        """Run server with graceful shutdown handling."""
        # Start server in background
        server_task = asyncio.create_task(server.serve())
        
        # Wait for shutdown signal or server completion
        done, pending = await asyncio.wait(
            [server_task, asyncio.create_task(self.shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # If shutdown was requested, stop the server
        if self.shutdown_event.is_set():
            logger.info("Shutdown requested, stopping server...")
            server.should_exit = True
            
            # Wait for server to stop gracefully
            try:
                await asyncio.wait_for(server_task, timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("Server shutdown timeout, forcing exit")
        
        # Cancel any remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DevSync AI Analytics Dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Create and run server
    dashboard_server = AnalyticsDashboardServer()
    
    try:
        await dashboard_server.run(host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)