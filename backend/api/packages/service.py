"""
Package API service layer - business logic for package API operations.
"""

from fastapi import HTTPException

from repositories.package import PackageRepository
from services.npm_client import NpmRegistryClient
from services.package_service import get_or_create_package_with_enrichment
from models.package import Package


async def create_package_from_npm(
    package_name: str,
    npm_client: NpmRegistryClient,
    repo: PackageRepository,
) -> Package:
    """
    Create a package by fetching metadata from npm registry.

    Args:
        package_name: npm package name (supports scoped packages)
        npm_client: NpmRegistryClient instance
        repo: PackageRepository instance

    Returns:
        Created Package

    Raises:
        HTTPException: 404 if package not found on npm, 409 if already exists
    """
    # Check if package already exists
    existing = repo.find_by_name(package_name)
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Package '{package_name}' already exists"
        )

    # Use shared service to create with enrichment
    package = await get_or_create_package_with_enrichment(
        package_name=package_name,
        npm_client=npm_client,
        repo=repo,
    )

    if not package:
        raise HTTPException(
            status_code=404,
            detail=f"Package '{package_name}' not found on npm registry",
        )

    return package
