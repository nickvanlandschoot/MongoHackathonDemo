"""Delta API router."""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List

from .schemas import BackfillRequest, BackfillResponse, JobStatusResponse
from .service import trigger_backfill, get_deltas_for_package, get_delta, get_job_status

router = APIRouter(
    prefix="/deltas",
    tags=["deltas"],
)


@router.post("/backfill", response_model=BackfillResponse)
async def backfill_deltas(request: BackfillRequest) -> Dict[str, Any]:
    """
    Trigger delta backfill for existing releases (non-blocking).

    Returns immediately with a job ID. Poll /deltas/jobs/{job_id} for status.

    Args:
        request: Backfill configuration with num_releases (default 5)

    Returns:
        Job ID and status information

    Example:
        POST /api/deltas/backfill
        {
            "num_releases": 5
        }

        Response:
        {
            "job_id": "abc-123",
            "status": "pending",
            "message": "Backfill job started"
        }
    """
    job_id = await trigger_backfill(request.num_releases)

    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"Backfill job started. Poll /deltas/jobs/{job_id} for status."
    }


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_backfill_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get status of a backfill job.

    Args:
        job_id: Job ID from backfill response

    Returns:
        Job status with results if completed

    Example:
        GET /api/deltas/jobs/abc-123
    """
    job = get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return job


@router.get("/package/{package_id}")
async def get_package_deltas(
    package_id: str,
    skip: int = Query(default=0, ge=0, description="Number of results to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results to return"),
) -> List[Dict[str, Any]]:
    """
    Get all deltas for a specific package.

    Args:
        package_id: Package ID
        skip: Number of results to skip (for pagination)
        limit: Maximum number of results to return

    Returns:
        List of deltas sorted by computation time (newest first)

    Example:
        GET /api/deltas/package/507f1f77bcf86cd799439011?skip=0&limit=10
    """
    deltas = get_deltas_for_package(package_id, skip, limit)

    return deltas


@router.get("/{delta_id}")
async def get_delta_by_id(delta_id: str) -> Dict[str, Any]:
    """
    Get a specific delta by ID.

    Args:
        delta_id: Delta ID

    Returns:
        Delta object

    Raises:
        HTTPException: If delta not found

    Example:
        GET /api/deltas/507f1f77bcf86cd799439012
    """
    delta = get_delta(delta_id)

    if not delta:
        raise HTTPException(status_code=404, detail=f"Delta {delta_id} not found")

    return delta
