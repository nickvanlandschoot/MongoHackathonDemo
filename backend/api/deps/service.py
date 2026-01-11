import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any

from database import get_database
from services.background_jobs import get_job_manager
from services.npm_client import NpmRegistryClient
from services.priority_resource_manager import Priority
from services.package_service import get_or_create_package_with_enrichment
from repositories.package import PackageRepository


async def _fetch_npm_deps_internal(
    package: str,
    version: str,
    depth: int = 2,
    priority: Priority = Priority.HIGH,  # User-initiated dependency fetch
    _visited: Optional[Set[str]] = None,
    _current_depth: int = 0,
    _db=None,
    _npm_client: Optional[NpmRegistryClient] = None,
    _package_repo: Optional[PackageRepository] = None
) -> Dict:
    """
    Recursively fetch npm package dependencies.

    Args:
        package: Package name
        version: Package version
        depth: Maximum recursion depth
        _visited: Internal set to track visited packages (prevents circular deps)
        _current_depth: Internal counter for current depth

    Returns:
        Dictionary with package info and nested dependencies
    """
    if _visited is None:
        _visited = set()

    # Initialize services at root level
    if _npm_client is None:
        _npm_client = NpmRegistryClient()
    if _package_repo is None:
        if _db is None:
            _db = get_database()
        _package_repo = PackageRepository(_db)

    indent = "  " * _current_depth
    print(f"{indent}→ Fetching {package}@{version} (depth {_current_depth}/{depth})")

    # Check depth limit
    if _current_depth >= depth:
        print(f"{indent}↳ Depth limit reached, skipping")
        return {}

    # Create unique identifier for this package version
    pkg_id = f"{package}@{version}"

    # Prevent circular dependencies
    if pkg_id in _visited:
        print(f"{indent}↳ Already visited {pkg_id}, skipping")
        return {}

    _visited.add(pkg_id)
    print(f"{indent}↳ Marked {pkg_id} as visited")

    # Fetch version-specific metadata from npm registry using NpmRegistryClient with priority
    try:
        print(f"{indent}↳ Requesting {package}@{version} via NpmRegistryClient (priority: {priority.name})")
        data = await _npm_client.get_version_metadata(package, version, priority)

        if not data:
            raise ValueError(f"Package '{package}@{version}' not found on npm registry")

        print(f"{indent}✓ Successfully fetched {package}@{version}")
    except Exception as e:
        print(f"{indent}✗ Failed to fetch {package}@{version}: {e}")
        return {
            "error": str(e),
            "package": package,
            "version": version
        }

    # Create Package record for this dependency (if not exists) - marked as dependency
    # This allows releases, maintainers, and deltas to be tracked
    if _current_depth > 0:  # Only create packages for dependencies, not the root package
        try:
            await get_or_create_package_with_enrichment(
                package_name=package,
                npm_client=_npm_client,
                repo=_package_repo,
                priority=priority,  # Pass through priority
                is_dependency=True,  # Mark as dependency so it's filtered from list view
            )
            print(f"{indent}✓ Package record ensured for dependency {package}")
        except Exception as e:
            # Don't fail the dependency tree fetch if package creation fails
            print(f"{indent}⚠ Warning: Failed to create package record for {package}: {e}")

    # Extract maintainers from npm data
    maintainers = []
    if "maintainers" in data and isinstance(data["maintainers"], list):
        maintainers = [m.get("name") for m in data["maintainers"] if m.get("name")]

    # Extract dependency information
    result = {
        "name": data.get("name"),
        "version": data.get("version"),
        "description": data.get("description"),
        "maintainers": maintainers,  # Store maintainer handles
        "dependencies": {},
        "devDependencies": {},
        "optionalDependencies": {},
        "peerDependencies": {}
    }

    # Collect all dependency fetch tasks
    fetch_tasks = []
    dep_info = []  # Store metadata about each dependency

    # Process production dependencies
    prod_deps = data.get("dependencies", {})
    if prod_deps:
        print(f"{indent}  → Processing {len(prod_deps)} production dependencies concurrently")
    for dep_name, dep_version in prod_deps.items():
        clean_version = dep_version.lstrip("^~>=<")
        print(f"{indent}    • {dep_name}@{dep_version}")
        fetch_tasks.append(
            _fetch_npm_deps_internal(dep_name, clean_version, depth, priority, _visited, _current_depth + 1, _db, _npm_client, _package_repo)
        )
        dep_info.append(("dependencies", dep_name, dep_version, clean_version))

    # Process dev dependencies
    dev_deps = data.get("devDependencies", {})
    if dev_deps:
        print(f"{indent}  → Processing {len(dev_deps)} dev dependencies concurrently")
    for dep_name, dep_version in dev_deps.items():
        clean_version = dep_version.lstrip("^~>=<")
        print(f"{indent}    • {dep_name}@{dep_version}")
        fetch_tasks.append(
            _fetch_npm_deps_internal(dep_name, clean_version, depth, priority, _visited, _current_depth + 1, _db, _npm_client, _package_repo)
        )
        dep_info.append(("devDependencies", dep_name, dep_version, clean_version))

    # Process optional dependencies
    opt_deps = data.get("optionalDependencies", {})
    if opt_deps:
        print(f"{indent}  → Processing {len(opt_deps)} optional dependencies concurrently")
    for dep_name, dep_version in opt_deps.items():
        clean_version = dep_version.lstrip("^~>=<")
        print(f"{indent}    • {dep_name}@{dep_version}")
        fetch_tasks.append(
            _fetch_npm_deps_internal(dep_name, clean_version, depth, priority, _visited, _current_depth + 1, _db, _npm_client, _package_repo)
        )
        dep_info.append(("optionalDependencies", dep_name, dep_version, clean_version))

    # Process peer dependencies
    peer_deps = data.get("peerDependencies", {})
    if peer_deps:
        print(f"{indent}  → Processing {len(peer_deps)} peer dependencies concurrently")
    for dep_name, dep_version in peer_deps.items():
        clean_version = dep_version.lstrip("^~>=<")
        print(f"{indent}    • {dep_name}@{dep_version}")
        fetch_tasks.append(
            _fetch_npm_deps_internal(dep_name, clean_version, depth, priority, _visited, _current_depth + 1, _db, _npm_client, _package_repo)
        )
        dep_info.append(("peerDependencies", dep_name, dep_version, clean_version))

    # Fetch all dependencies concurrently
    if fetch_tasks:
        print(f"{indent}  → Fetching {len(fetch_tasks)} dependencies concurrently...")
        children_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # Map results back to the correct dependency types
        for i, (dep_type, dep_name, dep_version, clean_version) in enumerate(dep_info):
            child_result = children_results[i]
            if isinstance(child_result, Exception):
                print(f"{indent}    ✗ Error fetching {dep_name}: {child_result}")
                child_result = {"error": str(child_result)}

            result[dep_type][dep_name] = {
                "spec": dep_version,
                "resolved_version": clean_version,
                "children": child_result
            }

    # Store in database (only at root level)
    if _current_depth == 0:
        if _db is None:
            _db = get_database()

        result["fetched_at"] = datetime.now(timezone.utc)

        # Upsert based on name and version
        print(f"{indent}💾 Storing {package}@{version} in database...")
        _db.dependency_trees.update_one(
            {"name": package, "version": version},
            {"$set": result},
            upsert=True
        )
        print(f"{indent}✓ Stored in database")

        # Update package scan_state to mark dependencies as crawled
        print(f"{indent}💾 Updating package scan_state for {package}...")
        _db.packages.update_one(
            {"name": package},
            {
                "$set": {
                    "scan_state.deps_crawled": True,
                    "scan_state.crawl_depth": depth,
                }
            }
        )
        print(f"{indent}✓ Updated package scan_state")

        # Trigger threat assessment generation after dependencies are scanned
        try:
            # Import here to avoid circular imports
            from services.ai_threat_surface_service import AIThreatSurfaceService

            # Check if OpenRouter API key is available
            OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
            if OPENROUTER_API_KEY:
                print(f"{indent}🔍 Triggering threat assessment for {package}...")
                threat_service = AIThreatSurfaceService(_db, OPENROUTER_API_KEY)
                asyncio.create_task(threat_service.generate_assessment_for_package(package))
                print(f"{indent}✓ Threat assessment task started")
            else:
                print(f"{indent}⚠️  OpenRouter API key not found, skipping threat assessment")
        except Exception as e:
            print(f"{indent}⚠️  Failed to trigger threat assessment: {e}")

    print(f"{indent}✓ Completed {package}@{version}")
    return result


async def fetch_npm_deps(package: str, version: str, depth: int = 2) -> str:
    """
    Trigger dependency fetch as a background job.

    Args:
        package: Package name
        version: Package version
        depth: Maximum recursion depth

    Returns:
        Job ID
    """
    job_manager = get_job_manager()

    # Create job
    job_id = job_manager.create_job(
        job_type="deps_fetch",
        metadata={"package": package, "version": version, "depth": depth}
    )

    # Start background task
    job_manager.start_job(
        job_id,
        _fetch_npm_deps_internal(package, version, depth)
    )

    return job_id


def get_deps_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get status of a dependency fetch job.

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
