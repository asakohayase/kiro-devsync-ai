"""
JIRA ticket synchronization scheduler.
Automatically syncs tickets and detects blockers on a regular schedule.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from ..services.jira import JiraService
from ..config import settings


logger = logging.getLogger(__name__)


class JiraSyncScheduler:
    """Scheduler for automatic JIRA ticket synchronization."""

    def __init__(self, sync_interval_hours: int = 4):
        """
        Initialize the JIRA sync scheduler.

        Args:
            sync_interval_hours: How often to sync tickets (default: every 4 hours)
        """
        self.sync_interval_hours = sync_interval_hours
        self.jira_service = JiraService()
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the automatic sync scheduler."""
        if self.is_running:
            logger.warning("JIRA sync scheduler is already running")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info(f"JIRA sync scheduler started (interval: {self.sync_interval_hours}h)")

    async def stop(self):
        """Stop the automatic sync scheduler."""
        if not self.is_running:
            return

        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("JIRA sync scheduler stopped")

    async def _sync_loop(self):
        """Main sync loop that runs periodically."""
        while self.is_running:
            try:
                await self._perform_sync()

                # Wait for next sync interval
                await asyncio.sleep(self.sync_interval_hours * 3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in JIRA sync loop: {e}", exc_info=True)
                # Wait 30 minutes before retrying on error
                await asyncio.sleep(1800)

    async def _perform_sync(self):
        """Perform a single sync operation."""
        try:
            logger.info("Starting scheduled JIRA ticket sync")

            # Sync tickets updated in the last 24 hours
            updated_since = datetime.now() - timedelta(hours=24)

            # Get project key from settings or sync all projects
            project_key = getattr(settings, "jira_project_key", None)

            # Perform sync with blocker detection
            result = await self.jira_service.sync_and_store_tickets(
                project_key=project_key, updated_since=updated_since
            )

            logger.info(
                f"JIRA sync completed: {result.get('total_tickets_synced', 0)} tickets, "
                f"{result.get('blocked_tickets_detected', 0)} blockers detected"
            )

            # Log any high-severity blockers for immediate attention
            if result.get("high_severity_blockers", 0) > 0:
                logger.warning(
                    f"⚠️ {result['high_severity_blockers']} high-severity blockers detected! "
                    "Manual review recommended."
                )

        except Exception as e:
            logger.error(f"JIRA sync failed: {e}", exc_info=True)

    async def sync_now(self) -> dict:
        """Trigger an immediate sync (for manual/API calls)."""
        logger.info("Manual JIRA sync triggered")

        try:
            # Sync tickets updated in the last 7 days for manual sync
            updated_since = datetime.now() - timedelta(days=7)
            project_key = getattr(settings, "jira_project_key", None)

            result = await self.jira_service.sync_and_store_tickets(
                project_key=project_key, updated_since=updated_since
            )

            logger.info("Manual JIRA sync completed successfully")
            return result

        except Exception as e:
            logger.error(f"Manual JIRA sync failed: {e}", exc_info=True)
            raise


# Global scheduler instance
_scheduler: Optional[JiraSyncScheduler] = None


def get_scheduler() -> JiraSyncScheduler:
    """Get the global JIRA sync scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = JiraSyncScheduler()
    return _scheduler


async def start_scheduler():
    """Start the global JIRA sync scheduler."""
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_scheduler():
    """Stop the global JIRA sync scheduler."""
    scheduler = get_scheduler()
    await scheduler.stop()
