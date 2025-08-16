"""
Background scheduler service for processing scheduled notifications.
Runs as a background task checking for scheduled notifications and processing them.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import signal
import sys

from .enhanced_notification_handler import EnhancedNotificationHandler


class SchedulerStatus(Enum):
    """Status of the notification scheduler."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class SchedulerConfig:
    """Configuration for the notification scheduler."""
    check_interval_seconds: int = 60  # Check every minute
    batch_size: int = 50  # Process up to 50 notifications per batch
    max_retries: int = 3
    retry_delay_seconds: int = 300  # 5 minutes
    health_check_interval_seconds: int = 300  # 5 minutes
    cleanup_interval_hours: int = 24  # Clean up old records daily
    enable_metrics: bool = True
    enable_health_checks: bool = True


@dataclass
class SchedulerMetrics:
    """Metrics for scheduler performance."""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    notifications_processed: int = 0
    notifications_sent: int = 0
    notifications_failed: int = 0
    average_run_time_ms: float = 0.0
    last_run_time: Optional[datetime] = None
    last_successful_run: Optional[datetime] = None
    last_error: Optional[str] = None
    uptime_start: datetime = field(default_factory=datetime.now)


class NotificationScheduler:
    """Background scheduler for processing scheduled notifications."""
    
    def __init__(self, 
                 handler: Optional[EnhancedNotificationHandler] = None,
                 config: Optional[SchedulerConfig] = None,
                 supabase_client=None):
        """Initialize notification scheduler."""
        
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.handler = handler or EnhancedNotificationHandler(supabase_client=supabase_client)
        self.config = config or SchedulerConfig()
        self.supabase = supabase_client
        
        # Scheduler state
        self.status = SchedulerStatus.STOPPED
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        
        # Metrics and monitoring
        self.metrics = SchedulerMetrics()
        self._health_check_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Error tracking
        self._recent_errors: List[Dict[str, Any]] = []
        
        # Callbacks
        self._on_notification_processed: Optional[Callable] = None
        self._on_error: Optional[Callable] = None
        self._on_health_check: Optional[Callable] = None
        
        self.logger.info("NotificationScheduler initialized")
    
    async def start(self) -> bool:
        """Start the scheduler."""
        
        if self.status != SchedulerStatus.STOPPED:
            self.logger.warning(f"Scheduler already running with status: {self.status}")
            return False
        
        try:
            self.status = SchedulerStatus.STARTING
            self.logger.info("Starting notification scheduler...")
            
            # Reset stop event
            self._stop_event.clear()
            
            # Start main scheduler task
            self._task = asyncio.create_task(self._scheduler_loop())
            
            # Start health check task if enabled
            if self.config.enable_health_checks:
                self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            # Set up signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            self.status = SchedulerStatus.RUNNING
            self.metrics.uptime_start = datetime.now()
            
            self.logger.info("Notification scheduler started successfully")
            return True
            
        except Exception as e:
            self.status = SchedulerStatus.ERROR
            self.logger.error(f"Failed to start scheduler: {e}")
            return False
    
    async def stop(self, timeout: int = 30) -> bool:
        """Stop the scheduler gracefully."""
        
        if self.status == SchedulerStatus.STOPPED:
            return True
        
        try:
            self.status = SchedulerStatus.STOPPING
            self.logger.info("Stopping notification scheduler...")
            
            # Signal stop to all tasks
            self._stop_event.set()
            
            # Wait for tasks to complete
            tasks_to_wait = []
            if self._task:
                tasks_to_wait.append(self._task)
            if self._health_check_task:
                tasks_to_wait.append(self._health_check_task)
            if self._cleanup_task:
                tasks_to_wait.append(self._cleanup_task)
            
            if tasks_to_wait:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks_to_wait, return_exceptions=True),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Scheduler tasks did not complete within timeout, cancelling...")
                    for task in tasks_to_wait:
                        if not task.done():
                            task.cancel()
            
            self.status = SchedulerStatus.STOPPED
            self.logger.info("Notification scheduler stopped")
            return True
            
        except Exception as e:
            self.status = SchedulerStatus.ERROR
            self.logger.error(f"Error stopping scheduler: {e}")
            return False
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        
        self.logger.info("Scheduler loop started")
        
        while not self._stop_event.is_set():
            try:
                run_start_time = datetime.now()
                self.metrics.total_runs += 1
                
                # Process scheduled notifications
                result = await self.handler.process_scheduled_notifications()
                
                # Update metrics
                self.metrics.notifications_processed += result.get("processed", 0)
                self.metrics.notifications_sent += result.get("sent", 0)
                self.metrics.notifications_failed += result.get("errors", 0)
                
                # Calculate run time
                run_time = (datetime.now() - run_start_time).total_seconds() * 1000
                self._update_average_run_time(run_time)
                
                self.metrics.last_run_time = datetime.now()
                
                if result.get("errors", 0) == 0:
                    self.metrics.successful_runs += 1
                    self.metrics.last_successful_run = datetime.now()
                else:
                    self.metrics.failed_runs += 1
                    error_msg = f"Processed {result.get('processed', 0)} notifications with {result.get('errors', 0)} errors"
                    self.metrics.last_error = error_msg
                    self._track_error("scheduler_run_errors", error_msg)
                
                # Log results
                if result.get("processed", 0) > 0:
                    self.logger.info(
                        f"Scheduler run completed: {result.get('processed', 0)} processed, "
                        f"{result.get('sent', 0)} sent, {result.get('errors', 0)} errors "
                        f"({run_time:.1f}ms)"
                    )
                
                # Call callback if set
                if self._on_notification_processed:
                    try:
                        await self._on_notification_processed(result)
                    except Exception as e:
                        self.logger.error(f"Error in notification processed callback: {e}")
                
            except Exception as e:
                self.metrics.failed_runs += 1
                self.metrics.last_error = str(e)
                self._track_error("scheduler_loop_error", str(e))
                self.logger.error(f"Error in scheduler loop: {e}")
                
                # Call error callback if set
                if self._on_error:
                    try:
                        await self._on_error(e)
                    except Exception as callback_error:
                        self.logger.error(f"Error in error callback: {callback_error}")
            
            # Wait for next check interval
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.config.check_interval_seconds
                )
                # If we get here, stop was requested
                break
            except asyncio.TimeoutError:
                # Normal timeout, continue loop
                continue
        
        self.logger.info("Scheduler loop stopped")
    
    async def _health_check_loop(self) -> None:
        """Health check loop."""
        
        self.logger.info("Health check loop started")
        
        while not self._stop_event.is_set():
            try:
                # Perform health check
                health_status = self.get_health_status()
                
                # Log health status if there are issues
                if health_status["status"] != "healthy":
                    self.logger.warning(f"Health check: {health_status['status']} - {health_status.get('issues', [])}")
                
                # Call health check callback if set
                if self._on_health_check:
                    try:
                        await self._on_health_check(health_status)
                    except Exception as e:
                        self.logger.error(f"Error in health check callback: {e}")
                
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
            
            # Wait for next health check interval
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.config.health_check_interval_seconds
                )
                break
            except asyncio.TimeoutError:
                continue
        
        self.logger.info("Health check loop stopped")
    
    async def _cleanup_loop(self) -> None:
        """Cleanup loop for old records."""
        
        self.logger.info("Cleanup loop started")
        
        while not self._stop_event.is_set():
            try:
                # Clean up old scheduled notifications
                if self.supabase:
                    cutoff_time = datetime.now() - timedelta(days=7)  # Keep 1 week
                    
                    try:
                        # Clean up sent notifications older than cutoff
                        response = self.supabase.table("scheduled_notifications").delete().eq(
                            "sent", True
                        ).lt(
                            "sent_at", cutoff_time.isoformat()
                        ).execute()
                        
                        if hasattr(response, 'count') and response.count:
                            self.logger.info(f"Cleaned up {response.count} old scheduled notifications")
                        
                        # Clean up old notification logs
                        await self.handler.deduplicator.cleanup_old_records(days_to_keep=7)
                        
                    except Exception as e:
                        self.logger.error(f"Error during database cleanup: {e}")
                
                # Clean up in-memory error tracking
                cutoff_time = datetime.now() - timedelta(hours=24)
                self._recent_errors = [
                    error for error in self._recent_errors
                    if error["timestamp"] > cutoff_time
                ]
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
            
            # Wait for next cleanup interval
            cleanup_interval_seconds = self.config.cleanup_interval_hours * 3600
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=cleanup_interval_seconds
                )
                break
            except asyncio.TimeoutError:
                continue
        
        self.logger.info("Cleanup loop stopped")
    
    def _update_average_run_time(self, run_time_ms: float) -> None:
        """Update average run time with new measurement."""
        if self.metrics.average_run_time_ms == 0:
            self.metrics.average_run_time_ms = run_time_ms
        else:
            # Use exponential moving average
            alpha = 0.1
            self.metrics.average_run_time_ms = (
                alpha * run_time_ms + (1 - alpha) * self.metrics.average_run_time_ms
            )
    
    def _track_error(self, error_type: str, error_message: str) -> None:
        """Track error for monitoring."""
        error_record = {
            "timestamp": datetime.now(),
            "type": error_type,
            "message": error_message
        }
        
        self._recent_errors.append(error_record)
        
        # Keep only recent errors (last 100)
        if len(self._recent_errors) > 100:
            self._recent_errors = self._recent_errors[-100:]
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())
        
        # Set up signal handlers if running in main thread
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except ValueError:
            # Not in main thread, skip signal handlers
            pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        
        uptime = datetime.now() - self.metrics.uptime_start
        
        return {
            "status": self.status.value,
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": str(uptime),
            "config": {
                "check_interval_seconds": self.config.check_interval_seconds,
                "batch_size": self.config.batch_size,
                "max_retries": self.config.max_retries
            },
            "tasks": {
                "main_task_running": self._task is not None and not self._task.done(),
                "health_check_running": self._health_check_task is not None and not self._health_check_task.done(),
                "cleanup_task_running": self._cleanup_task is not None and not self._cleanup_task.done()
            }
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get scheduler metrics."""
        
        success_rate = (
            self.metrics.successful_runs / self.metrics.total_runs * 100
            if self.metrics.total_runs > 0 else 0
        )
        
        return {
            "total_runs": self.metrics.total_runs,
            "successful_runs": self.metrics.successful_runs,
            "failed_runs": self.metrics.failed_runs,
            "success_rate_percent": success_rate,
            "notifications_processed": self.metrics.notifications_processed,
            "notifications_sent": self.metrics.notifications_sent,
            "notifications_failed": self.metrics.notifications_failed,
            "average_run_time_ms": self.metrics.average_run_time_ms,
            "last_run_time": self.metrics.last_run_time.isoformat() if self.metrics.last_run_time else None,
            "last_successful_run": self.metrics.last_successful_run.isoformat() if self.metrics.last_successful_run else None,
            "last_error": self.metrics.last_error,
            "recent_errors_count": len(self._recent_errors)
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the scheduler."""
        
        issues = []
        
        # Check if scheduler is running
        if self.status != SchedulerStatus.RUNNING:
            issues.append(f"Scheduler not running (status: {self.status.value})")
        
        # Check recent errors
        recent_errors = [
            error for error in self._recent_errors
            if error["timestamp"] > datetime.now() - timedelta(minutes=30)
        ]
        
        if len(recent_errors) > 5:
            issues.append(f"High error rate: {len(recent_errors)} errors in last 30 minutes")
        
        # Check last successful run
        if self.metrics.last_successful_run:
            time_since_success = datetime.now() - self.metrics.last_successful_run
            if time_since_success > timedelta(minutes=self.config.check_interval_seconds / 60 * 3):
                issues.append(f"No successful run in {time_since_success}")
        
        # Check average run time
        if self.metrics.average_run_time_ms > 30000:  # 30 seconds
            issues.append(f"High average run time: {self.metrics.average_run_time_ms:.1f}ms")
        
        # Check database connectivity
        if not self.supabase:
            issues.append("No database connection available")
        
        # Determine overall health
        if not issues:
            status = "healthy"
        elif len(issues) == 1 and "No database connection" in issues[0]:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "issues": issues,
            "checks_performed": {
                "scheduler_running": self.status == SchedulerStatus.RUNNING,
                "recent_errors_acceptable": len(recent_errors) <= 5,
                "recent_successful_run": self.metrics.last_successful_run is not None,
                "acceptable_run_time": self.metrics.average_run_time_ms <= 30000,
                "database_available": self.supabase is not None
            },
            "last_check": datetime.now().isoformat()
        }
    
    def set_callbacks(self,
                     on_notification_processed: Optional[Callable] = None,
                     on_error: Optional[Callable] = None,
                     on_health_check: Optional[Callable] = None) -> None:
        """Set callback functions for scheduler events."""
        
        self._on_notification_processed = on_notification_processed
        self._on_error = on_error
        self._on_health_check = on_health_check
        
        self.logger.info("Scheduler callbacks configured")
    
    async def force_run(self) -> Dict[str, Any]:
        """Force an immediate scheduler run (for testing/debugging)."""
        
        if self.status != SchedulerStatus.RUNNING:
            return {"error": "Scheduler not running"}
        
        try:
            self.logger.info("Forcing immediate scheduler run...")
            result = await self.handler.process_scheduled_notifications()
            self.logger.info(f"Forced run completed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in forced run: {e}")
            return {"error": str(e)}
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors for debugging."""
        
        return sorted(
            self._recent_errors[-limit:],
            key=lambda x: x["timestamp"],
            reverse=True
        )


# Global scheduler instance
default_scheduler = NotificationScheduler()