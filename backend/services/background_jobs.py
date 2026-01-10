"""
Background job management for long-running tasks.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, Coroutine
from dataclasses import dataclass, field


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """Background job representation."""
    id: str
    type: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BackgroundJobManager:
    """
    Manages background jobs with status tracking and result storage.

    Jobs are stored in memory. For production, consider using Redis or a database.
    """

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    def create_job(self, job_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new job and return its ID.

        Args:
            job_type: Type of job (e.g., "backfill", "deps_fetch")
            metadata: Optional metadata about the job

        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())

        job = Job(
            id=job_id,
            type=job_type,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {}
        )

        self._jobs[job_id] = job

        return job_id

    def start_job(
        self,
        job_id: str,
        coro: Coroutine,
    ) -> None:
        """
        Start executing a job in the background.

        Args:
            job_id: Job ID
            coro: Coroutine to execute
        """
        if job_id not in self._jobs:
            raise ValueError(f"Job {job_id} not found")

        job = self._jobs[job_id]
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)

        # Create background task
        task = asyncio.create_task(self._execute_job(job_id, coro))
        self._tasks[job_id] = task

    async def _execute_job(self, job_id: str, coro: Coroutine) -> None:
        """
        Execute a job and update its status.

        Args:
            job_id: Job ID
            coro: Coroutine to execute
        """
        job = self._jobs[job_id]

        try:
            result = await coro
            job.status = JobStatus.COMPLETED
            job.result = result
            job.completed_at = datetime.now(timezone.utc)
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            print(f"[background_jobs] Job {job_id} failed: {e}")
        finally:
            # Clean up task reference
            if job_id in self._tasks:
                del self._tasks[job_id]

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job or None if not found
        """
        return self._jobs.get(job_id)

    def update_progress(self, job_id: str, progress: Dict[str, Any]) -> None:
        """
        Update job progress.

        Args:
            job_id: Job ID
            progress: Progress information
        """
        if job_id in self._jobs:
            self._jobs[job_id].progress = progress

    def list_jobs(self, job_type: Optional[str] = None) -> list[Job]:
        """
        List all jobs, optionally filtered by type.

        Args:
            job_type: Optional job type filter

        Returns:
            List of jobs
        """
        jobs = list(self._jobs.values())

        if job_type:
            jobs = [j for j in jobs if j.type == job_type]

        # Sort by creation time, newest first
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return jobs

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Remove old completed/failed jobs.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of jobs removed
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        removed = 0

        for job_id, job in list(self._jobs.items()):
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                if job.created_at.timestamp() < cutoff:
                    del self._jobs[job_id]
                    removed += 1

        return removed


# Global singleton instance
_job_manager: Optional[BackgroundJobManager] = None


def get_job_manager() -> BackgroundJobManager:
    """Get the global job manager instance."""
    global _job_manager
    if _job_manager is None:
        _job_manager = BackgroundJobManager()
    return _job_manager