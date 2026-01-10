"""
Package API router.
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query

from api.packages.schemas import CreatePackageRequest, ListPackagesResponse, PackageWithLatestRelease
from api.packages.service import create_package_from_npm
from database import get_database
from models.package import Package
from models.identity import Identity
from repositories.package import PackageRepository
from repositories.package_release import PackageReleaseRepository
from repositories.identity import IdentityRepository
from services.npm_client import NpmRegistryClient

# Singleton instance for NpmRegistryClient
_npm_client_instance: Optional[NpmRegistryClient] = None

router = APIRouter(
    prefix="/packages",
    tags=["packages"],
)


def get_npm_client() -> NpmRegistryClient:
    """Dependency injection for NpmRegistryClient."""
    global _npm_client_instance
    if _npm_client_instance is None:
        _npm_client_instance = NpmRegistryClient()
    return _npm_client_instance


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
    """
    package = await create_package_from_npm(
        package_name=request.package_name,
        npm_client=npm_client,
        repo=repo,
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
    if search:
        # Search by name
        packages = repo.search_by_name(search, skip=skip, limit=limit)
        total = repo.count({"name": {"$regex": search, "$options": "i"}})
    else:
        # List all
        packages = repo.find_all(skip=skip, limit=limit)
        total = repo.count({})

    # Enrich packages with latest release info
    enriched_packages = []
    for package in packages:
        package_dict = package.model_dump()
        
        if package.id:
            releases = release_repo.find_by_package(package.id, skip=0, limit=1)
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


@router.get("/{name}", response_model=PackageWithLatestRelease)
async def get_package(
    name: str,
    repo: PackageRepository = Depends(get_package_repository),
    release_repo: PackageReleaseRepository = Depends(get_package_release_repository),
):
    """
    Get package details by name with latest release information.
    """
    package = repo.find_by_name(name)
    if not package:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")

    # Get the most recent release for this package
    latest_release = None
    if package.id:
        releases = release_repo.find_by_package(package.id, skip=0, limit=1)
        if releases:
            latest_release = releases[0]

    # Create response with latest release info
    package_dict = package.model_dump()
    package_dict["latest_release_date"] = latest_release.publish_timestamp if latest_release else None
    package_dict["latest_release_version"] = latest_release.version if latest_release else None

    return PackageWithLatestRelease(**package_dict)


@router.get("/{name}/maintainers", response_model=List[Identity])
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
    # Get package
    package = package_repo.find_by_name(name)
    if not package:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")

    if not package.id:
        raise HTTPException(status_code=500, detail="Package ID is missing")

    # Get all releases for this package
    releases = release_repo.find_by_package(package.id, skip=0, limit=1000)

    # Collect unique identity IDs
    identity_ids = set()
    for release in releases:
        if release.published_by:
            identity_ids.add(release.published_by)

    # Fetch identities
    identities = []
    for identity_id in identity_ids:
        identity = identity_repo.find_by_id(str(identity_id))
        if identity:
            identities.append(identity)

    return identities


@router.delete("/{name}", status_code=204)
async def delete_package(
    name: str,
    package_repo: PackageRepository = Depends(get_package_repository),
    release_repo: PackageReleaseRepository = Depends(get_package_release_repository),
):
    """
    Delete a package and all associated releases.

    This is a destructive operation that cannot be undone.
    """
    # Find package
    package = package_repo.find_by_name(name)
    if not package:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")

    if not package.id:
        raise HTTPException(status_code=500, detail="Package ID is missing")

    # Delete all releases for this package
    release_repo.delete_many({"package_id": package.id})

    # Delete the package itself
    deleted = package_repo.delete(package.id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete package")

    return None
