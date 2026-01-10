from fastapi import APIRouter, HTTPException
from typing import Dict

from .schemas import FetchDepsRequest, FetchDepsResponse
from .service import fetch_npm_deps

router = APIRouter(
    prefix="/deps",
    tags=["dependencies"],
)


@router.post("/npm/fetch", response_model=FetchDepsResponse)
async def fetch_npm_dependencies(request: FetchDepsRequest) -> Dict[str, object]:
    """
    Fetch npm package dependencies recursively.

    This endpoint fetches the dependency tree for a given npm package
    at a specific version, up to the specified depth.

    Args:
        request: Package name, version, and recursion depth

    Returns:
        Nested dependency tree with all dependency types

    Raises:
        HTTPException: If the package cannot be fetched
    """
    result = await fetch_npm_deps(
        package=request.package, version=request.version, depth=request.depth
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Package {request.package}@{request.version} not found or depth limit reached",
        )

    if "error" in result:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch dependencies: {result['error']}"
        )

    return result

