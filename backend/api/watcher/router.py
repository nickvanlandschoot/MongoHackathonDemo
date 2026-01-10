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


@router.get("/status", response_model=StatusResponse)
async def get_status(scheduler: WatcherScheduler = Depends(get_scheduler)):
    """Get current watcher status."""
    return scheduler.get_status()
