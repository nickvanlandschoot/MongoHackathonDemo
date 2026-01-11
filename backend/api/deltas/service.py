"""Delta service layer for API."""

from typing import Optional, Dict, Any, List
from bson import ObjectId

from database import get_database
from services.delta_service import DeltaService
from services.background_jobs import get_job_manager
from repositories import PackageDeltaRepository


async def trigger_backfill(num_releases: int) -> str:
    """
    Trigger delta backfill as a background job.

    Args:
        num_releases: Number of recent releases to backfill per package

    Returns:
        Job ID
    """
    job_manager = get_job_manager()

    # Create job
    job_id = job_manager.create_job(
        job_type="backfill",
        metadata={"num_releases": num_releases}
    )

    # Start background task
    db = get_database()
    delta_service = DeltaService(db)

    job_manager.start_job(
        job_id,
        delta_service.backfill_deltas(num_releases)
    )

    return job_id


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get status of a background job.

    Args:
        job_id: Job ID

    Returns:
        Job status dict or None
    """
    job_manager = get_job_manager()
    job = job_manager.get_job(job_id)

    if not job:
        return None

    return {
        "job_id": job.id,
        "type": job.type,
        "status": job.status.value,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "progress": job.progress,
        "result": job.result,
        "error": job.error,
    }


async def get_deltas_for_package(package_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get all deltas for a package.

    Args:
        package_id: Package ID
        skip: Number to skip
        limit: Maximum results

    Returns:
        List of deltas
    """
    db = get_database()
    delta_repo = PackageDeltaRepository(db)

    deltas = await delta_repo.find_by_package(package_id, skip=skip, limit=limit)

    return [delta.model_dump(by_alias=True, mode="json") for delta in deltas]


async def get_delta(delta_id: str) -> Optional[Dict[str, Any]]:
    """
    Get specific delta.

    Args:
        delta_id: Delta ID

    Returns:
        Delta dict or None
    """
    db = get_database()
    delta_repo = PackageDeltaRepository(db)

    delta = await delta_repo.find_by_id(ObjectId(delta_id))

    if delta:
        return delta.model_dump(by_alias=True, mode="json")

    return None
