"""
Background scheduler for the watcher service.
"""

from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from pymongo.database import Database

from services.watcher import WatcherService
from services.pause_manager import get_pause_manager


class WatcherScheduler:
    """
    Scheduler for the PR Watcher agent.

    Manages the background polling job with start/stop/status controls.
    """

    JOB_ID = "npm_watcher_poll"
    DEFAULT_INTERVAL_SECONDS = 30

    def __init__(self, database: Database):
        self.database = database
        self.watcher_service = WatcherService(database)
        self.scheduler = AsyncIOScheduler()
        self._last_run: Optional[datetime] = None
        self._last_result: Optional[dict] = None
        self._is_running = False
        self._error_count = 0

        # Add event listeners
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED,
        )
        self.scheduler.add_listener(
            self._on_job_error,
            EVENT_JOB_ERROR,
        )

    def start(self, interval_seconds: int = DEFAULT_INTERVAL_SECONDS) -> bool:
        """
        Start the scheduler.

        Args:
            interval_seconds: Polling interval

        Returns:
            True if started, False if already running
        """
        if self._is_running:
            print("[scheduler] WARNING: Scheduler already running")
            return False

        # Add the polling job
        self.scheduler.add_job(
            self._run_poll,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id=self.JOB_ID,
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
            coalesce=True,  # Combine missed runs
        )

        self.scheduler.start()
        self._is_running = True
        print(f"[scheduler] Watcher scheduler started with {interval_seconds}s interval")
        return True

    def stop(self) -> bool:
        """
        Stop the scheduler.

        Returns:
            True if stopped, False if not running
        """
        if not self._is_running:
            print("[scheduler] WARNING: Scheduler not running")
            return False

        self.scheduler.remove_job(self.JOB_ID)
        self.scheduler.shutdown(wait=False)
        self._is_running = False
        print("[scheduler] Watcher scheduler stopped")
        return True

    def pause(self) -> bool:
        """Pause the scheduler and all background processes."""
        if not self._is_running:
            return False

        # Pause the scheduler job
        self.scheduler.pause_job(self.JOB_ID)

        # Set global pause flag to stop background AI tasks
        pause_manager = get_pause_manager()
        pause_manager.pause()

        print("[scheduler] Watcher scheduler and all background processes paused")
        return True

    def resume(self) -> bool:
        """Resume the scheduler and all background processes."""
        if not self._is_running:
            return False

        # Resume the scheduler job
        self.scheduler.resume_job(self.JOB_ID)

        # Clear global pause flag to allow background AI tasks
        pause_manager = get_pause_manager()
        pause_manager.resume()

        print("[scheduler] Watcher scheduler and all background processes resumed")
        return True

    async def trigger_now(self) -> dict:
        """
        Trigger an immediate poll (outside normal schedule).

        Returns:
            Poll results
        """
        print("[scheduler] Triggering immediate poll")
        return await self._run_poll()

    def get_status(self) -> dict:
        """
        Get current scheduler status.

        Returns:
            Status dict with runtime information
        """
        job = self.scheduler.get_job(self.JOB_ID) if self._is_running else None

        next_run = None
        is_paused = False
        if job:
            if job.next_run_time:
                next_run = job.next_run_time.isoformat()
            else:
                is_paused = True

        return {
            "is_running": self._is_running,
            "is_paused": is_paused,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "next_run": next_run,
            "last_result": self._last_result,
            "error_count": self._error_count,
        }

    async def _run_poll(self) -> dict:
        """Execute the poll cycle."""
        self._last_run = datetime.now(timezone.utc)

        try:
            result = await self.watcher_service.poll_all_packages()
            self._last_result = result
            return result
        except Exception as e:
            print(f"[scheduler] ERROR: Poll cycle failed: {e}")
            self._error_count += 1
            self._last_result = {"error": str(e)}
            raise

    def _on_job_executed(self, _event):
        """Handler for successful job execution."""
        pass

    def _on_job_error(self, event):
        """Handler for job errors."""
        print(f"[scheduler] ERROR: Job error: {event.job_id} - {event.exception}")
        self._error_count += 1
