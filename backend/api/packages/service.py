"""
Package API service layer - business logic for package API operations.
"""

import asyncio
from fastapi import HTTPException

from repositories.package import PackageRepository
from services.npm_client import NpmRegistryClient
from services.priority_resource_manager import Priority
from services.package_service import get_or_create_package_with_enrichment, crawl_package_maintainers
from services.background_jobs import get_job_manager
from services.watcher import WatcherService
from models.package import Package
from database import get_database


async def create_package_from_npm(
    package_name: str,
    npm_client: NpmRegistryClient,
    repo: PackageRepository,
    priority: Priority = Priority.HIGH,
) -> Package:
    """
    Create a package by fetching metadata from npm registry with HIGH priority.
    Automatically triggers analysis for the newly created package.

    Args:
        package_name: npm package name (supports scoped packages)
        npm_client: NpmRegistryClient instance
        repo: PackageRepository instance
        priority: Priority level (HIGH for user requests, LOW for background jobs)

    Returns:
        Created Package

    Raises:
        HTTPException: 404 if package not found on npm, 409 if already exists
    """
    # Check if package already exists
    existing = await repo.find_by_name(package_name)
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Package '{package_name}' already exists"
        )

    # Use shared service to create with enrichment (HIGH priority for user request)
    package = await get_or_create_package_with_enrichment(
        package_name=package_name,
        npm_client=npm_client,
        repo=repo,
        priority=priority,
    )

    if not package:
        raise HTTPException(
            status_code=404,
            detail=f"Package '{package_name}' not found on npm registry",
        )

    # Trigger automatic analysis for newly created package (non-blocking)
    asyncio.create_task(_trigger_package_analysis(package))

    return package


async def _trigger_package_analysis(package: Package):
    """
    Background task to trigger initial analysis for a newly created package.

    Args:
        package: Package to analyze
    """
    try:
        db = get_database()
        watcher = WatcherService(db)
        result = await watcher.process_package(package)
        print(f"[package_service] Initial analysis completed for {package.name}: {result}")
    except Exception as e:
        print(f"[package_service] ERROR: Failed to trigger analysis for {package.name}: {e}")


async def fetch_package_maintainers(
    package_name: str,
    npm_client: NpmRegistryClient,
    repo: PackageRepository,
) -> str:
    """
    Trigger maintainer crawling as a background job.

    Args:
        package_name: npm package name
        npm_client: NpmRegistryClient instance
        repo: PackageRepository instance

    Returns:
        Job ID
    """
    job_manager = get_job_manager()

    # Create job
    job_id = job_manager.create_job(
        job_type="maintainer_fetch",
        metadata={"package": package_name}
    )

    # Start background task
    job_manager.start_job(
        job_id,
        crawl_package_maintainers(package_name, npm_client, repo)
    )

    return job_id
