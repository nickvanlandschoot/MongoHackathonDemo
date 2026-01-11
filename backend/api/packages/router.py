"""
Package API router.
"""

from typing import Optional, List
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query

from api.packages.schemas import CreatePackageRequest, ListPackagesResponse, PackageWithLatestRelease, FetchMaintainersResponse
from api.packages.service import create_package_from_npm, fetch_package_maintainers
from database import get_database
from models.package import Package
from models.identity import Identity
from repositories.package import PackageRepository
from repositories.package_release import PackageReleaseRepository
from repositories.identity import IdentityRepository
from services.npm_client import NpmRegistryClient
from services.priority_resource_manager import Priority

router = APIRouter(
    prefix="/packages",
    tags=["packages"],
)


def get_npm_client() -> NpmRegistryClient:
    """
    Dependency injection for NpmRegistryClient.

    Returns the singleton NpmRegistryClient instance.
    """
    return NpmRegistryClient()  # Singleton pattern handles single instance


def get_package_repository() -> PackageRepository:
    """Dependency injection for PackageRepository."""
    return PackageRepository(get_database())


def get_package_release_repository() -> PackageReleaseRepository:
    """Dependency injection for PackageReleaseRepository."""
    return PackageReleaseRepository(get_database())


def get_identity_repository() -> IdentityRepository:
    """Dependency injection for IdentityRepository."""
    return IdentityRepository(get_database())


@router.post("/", response_model=Package, status_code=201)
async def create_package(
    request: CreatePackageRequest,
    npm_client: NpmRegistryClient = Depends(get_npm_client),
    repo: PackageRepository = Depends(get_package_repository),
):
    """
    Create a new package by fetching metadata from npm registry.

    Only requires the package name - version and metadata are fetched automatically.
    User request - uses HIGH priority to ensure fast response.
    """
    package = await create_package_from_npm(
        package_name=request.package_name,
        npm_client=npm_client,
        repo=repo,
        priority=Priority.HIGH,  # User request - HIGH priority
    )
    return package


@router.get("/", response_model=ListPackagesResponse)
async def list_packages(
    skip: int = Query(0, ge=0, description="Number of packages to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum packages to return"),
    search: Optional[str] = Query(None, description="Search by package name"),
    repo: PackageRepository = Depends(get_package_repository),
    release_repo: PackageReleaseRepository = Depends(get_package_release_repository),
):
    """
    List packages with pagination and optional search.

    Search is case-insensitive and matches package names.
    """
    # Filter out dependency packages - only show manually added packages
    base_filter = {"is_dependency": {"$ne": True}}
    
    if search:
        # Search by name, excluding dependencies
        search_filter = {**base_filter, "name": {"$regex": search, "$options": "i"}}
        packages = await repo.find_many(search_filter, skip=skip, limit=limit)
        total = await repo.count(search_filter)
    else:
        # List all manually added packages
        packages = await repo.find_many(base_filter, skip=skip, limit=limit)
        total = await repo.count(base_filter)

    # Enrich packages with latest release info
    enriched_packages = []
    for package in packages:
        package_dict = package.model_dump()

        if package.id:
            releases = await release_repo.find_by_package(package.id, skip=0, limit=1)
            latest_release = releases[0] if releases else None
            package_dict["latest_release_date"] = latest_release.publish_timestamp if latest_release else None
            package_dict["latest_release_version"] = latest_release.version if latest_release else None
        else:
            package_dict["latest_release_date"] = None
            package_dict["latest_release_version"] = None
        
        enriched_packages.append(package_dict)

    return ListPackagesResponse(
        packages=enriched_packages,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{name:path}/maintainers", response_model=List[Identity])
async def get_package_maintainers(
    name: str,
    package_repo: PackageRepository = Depends(get_package_repository),
    release_repo: PackageReleaseRepository = Depends(get_package_release_repository),
    identity_repo: IdentityRepository = Depends(get_identity_repository),
):
    """
    Get all maintainers who published releases for this package.

    Returns unique Identity records for all publishers of this package's releases.
    """
    # URL-decode to handle scoped packages
    name = unquote(name)
    
    # Get package
    package = await package_repo.find_by_name(name)
    if not package:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")

    if not package.id:
        raise HTTPException(status_code=500, detail="Package ID is missing")

    # Get all releases for this package
    releases = await release_repo.find_by_package(package.id, skip=0, limit=1000)

    # Collect unique identity IDs
    identity_ids = set()
    for release in releases:
        if release.published_by:
            identity_ids.add(release.published_by)

    # Fetch identities
    identities = []
    for identity_id in identity_ids:
        identity = await identity_repo.find_by_id(str(identity_id))
        if identity:
            identities.append(identity)

    return identities


@router.post("/{name:path}/fetch-maintainers", response_model=FetchMaintainersResponse)
async def fetch_maintainers(
    name: str,
    package_repo: PackageRepository = Depends(get_package_repository),
    npm_client: NpmRegistryClient = Depends(get_npm_client),
):
    """
    Trigger maintainer crawling for a package (non-blocking).

    Returns immediately with a job ID. Poll /deps/jobs/{job_id} for status.

    If maintainers are already crawled, returns immediately with status "completed".

    Returns:
        Job ID and status information

    Example:
        POST /api/packages/express/fetch-maintainers

        Response:
        {
            "job_id": "abc-123",
            "status": "pending",
            "message": "Maintainer fetch started"
        }
    """
    # URL-decode to handle scoped packages
    name = unquote(name)
    
    # Check if package exists
    package = await package_repo.find_by_name(name)
    if not package:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")

    # Check if maintainers are already crawled
    if package.scan_state.maintainers_crawled:
        return {
            "job_id": None,
            "status": "completed",
            "message": "Maintainers already crawled"
        }

    # Trigger maintainer fetch as background job
    job_id = await fetch_package_maintainers(
        package_name=name,
        npm_client=npm_client,
        repo=package_repo,
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"Maintainer fetch started. Poll /deps/jobs/{job_id} for status."
    }


@router.delete("/{name:path}", status_code=204)
async def delete_package(
    name: str,
    package_repo: PackageRepository = Depends(get_package_repository),
    release_repo: PackageReleaseRepository = Depends(get_package_release_repository),
):
    """
    Delete a package and all associated releases.

    This is a destructive operation that cannot be undone.
    """
    # URL-decode to handle scoped packages
    name = unquote(name)
    
    # Find package
    package = await package_repo.find_by_name(name)
    if not package:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")

    if not package.id:
        raise HTTPException(status_code=500, detail="Package ID is missing")

    # Delete all releases for this package
    await release_repo.delete_many({"package_id": package.id})

    # Delete the package itself
    deleted = await package_repo.delete(package.id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete package")

    return None


@router.get("/{name:path}", response_model=PackageWithLatestRelease)
async def get_package(
    name: str,
    repo: PackageRepository = Depends(get_package_repository),
    release_repo: PackageReleaseRepository = Depends(get_package_release_repository),
):
    """
    Get package details by name with latest release information.
    
    Supports scoped npm packages (e.g., @scope/package).
    """
    # URL-decode to handle scoped packages
    name = unquote(name)
    
    package = await repo.find_by_name(name)
    if not package:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")

    # Get the most recent release for this package
    latest_release = None
    if package.id:
        releases = await release_repo.find_by_package(package.id, skip=0, limit=1)
        if releases:
            latest_release = releases[0]

    # Create response with latest release info
    package_dict = package.model_dump()
    package_dict["latest_release_date"] = latest_release.publish_timestamp if latest_release else None
    package_dict["latest_release_version"] = latest_release.version if latest_release else None

    return PackageWithLatestRelease(**package_dict)
