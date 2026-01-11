from urllib.parse import unquote

from fastapi import APIRouter, HTTPException
from typing import Dict

from .schemas import FetchDepsRequest, FetchDepsResponse, JobStatusResponse
from .service import fetch_npm_deps, get_deps_job_status
from database import get_database

router = APIRouter(
    prefix="/deps",
    tags=["dependencies"],
)


@router.post("/npm/fetch", response_model=FetchDepsResponse)
async def fetch_npm_dependencies(request: FetchDepsRequest) -> Dict[str, object]:
    """
    Fetch npm package dependencies recursively (non-blocking).

    Returns immediately with a job ID. Poll /deps/jobs/{job_id} for status.

    Args:
        request: Package name, version, and recursion depth

    Returns:
        Job ID and status information

    Example:
        POST /api/deps/npm/fetch
        {
            "package": "express",
            "version": "4.18.2",
            "depth": 2
        }

        Response:
        {
            "job_id": "xyz-789",
            "status": "pending",
            "message": "Dependency fetch started"
        }
    """
    job_id = await fetch_npm_deps(
        package=request.package, version=request.version, depth=request.depth
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"Dependency fetch started. Poll /deps/jobs/{job_id} for status."
    }


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_deps_job_status_endpoint(job_id: str) -> Dict[str, object]:
    """
    Get status of a dependency fetch job.

    Args:
        job_id: Job ID from fetch response

    Returns:
        Job status with results if completed

    Example:
        GET /api/deps/jobs/xyz-789
    """
    job = get_deps_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return job


@router.get("/npm/{package:path}/{version}")
async def get_dependency_tree(package: str, version: str) -> Dict[str, object]:
    """
    Get dependency tree from database for a specific package version.

    This endpoint reads existing dependency data from the database.
    To trigger a new dependency fetch, use POST /deps/npm/fetch instead.

    Supports scoped npm packages (e.g., @scope/package).

    Args:
        package: Package name (supports scoped packages like @scope/package)
        version: Package version

    Returns:
        Dependency tree data

    Example:
        GET /api/deps/npm/express/4.18.2
        GET /api/deps/npm/@scope/package/1.0.0
    """
    # URL-decode package name to handle any encoding artifacts
    package = unquote(package)
    version = unquote(version)
    
    db = get_database()
    tree = db.dependency_trees.find_one(
        {"name": package, "version": version},
        {"_id": 0}  # Exclude MongoDB _id field
    )

    if not tree:
        raise HTTPException(
            status_code=404,
            detail=f"Dependency tree not found for {package}@{version}"
        )

    return tree

