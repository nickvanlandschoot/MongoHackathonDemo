"""
API endpoints for watcher status.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.scheduler import WatcherScheduler

router = APIRouter(
    prefix="/watcher",
    tags=["watcher"],
)

# Singleton scheduler instance (initialized on app startup)
_scheduler: Optional[WatcherScheduler] = None


def get_scheduler() -> WatcherScheduler:
    """Get the scheduler instance."""
    if _scheduler is None:
        raise HTTPException(status_code=503, detail="Watcher scheduler not initialized")
    return _scheduler


def init_scheduler(database) -> WatcherScheduler:
    """Initialize the scheduler (called from main.py startup)."""
    global _scheduler
    _scheduler = WatcherScheduler(database)
    return _scheduler


def get_scheduler_instance() -> Optional[WatcherScheduler]:
    """Get raw scheduler instance (for shutdown)."""
    return _scheduler


class StatusResponse(BaseModel):
    """Scheduler status response."""

    is_running: bool
    is_paused: bool
    last_run: Optional[str]
    next_run: Optional[str]
    last_result: Optional[dict]
    error_count: int


class PauseResponse(BaseModel):
    """Pause/resume response."""

    success: bool
    message: str
    is_paused: bool


@router.get("/status", response_model=StatusResponse)
async def get_status(scheduler: WatcherScheduler = Depends(get_scheduler)):
    """Get current watcher status."""
    return scheduler.get_status()


@router.post("/pause", response_model=PauseResponse)
async def pause_watcher(scheduler: WatcherScheduler = Depends(get_scheduler)):
    """
    Pause all background processes including:
    - Scheduled watcher polls
    - Background AI analysis tasks
    - Delta computation jobs

    This stops all background npm API calls and AI processing.
    User-initiated operations will continue to work normally.
    """
    success = scheduler.pause()

    if success:
        return PauseResponse(
            success=True,
            message="All background processes paused",
            is_paused=True
        )
    else:
        return PauseResponse(
            success=False,
            message="Watcher is not running",
            is_paused=False
        )


@router.post("/resume", response_model=PauseResponse)
async def resume_watcher(scheduler: WatcherScheduler = Depends(get_scheduler)):
    """
    Resume all background processes.

    This restarts:
    - Scheduled watcher polls
    - Background AI analysis tasks
    - Delta computation jobs
    """
    success = scheduler.resume()

    if success:
        return PauseResponse(
            success=True,
            message="All background processes resumed",
            is_paused=False
        )
    else:
        return PauseResponse(
            success=False,
            message="Watcher is not running",
            is_paused=False
        )


@router.post("/trigger")
async def trigger_poll(scheduler: WatcherScheduler = Depends(get_scheduler)):
    """
    Trigger an immediate poll cycle (bypasses schedule).

    This runs a single poll cycle immediately, regardless of pause state.
    Useful for testing or forcing an update.
    """
    result = await scheduler.trigger_now()
    return {
        "success": True,
        "message": "Poll triggered successfully",
        "result": result
    }
