import asyncio
import requests
from datetime import datetime
from typing import Dict, Set, Optional

from database import get_database


async def fetch_npm_deps(
    package: str,
    version: str,
    depth: int = 2,
    _visited: Optional[Set[str]] = None,
    _current_depth: int = 0,
    _db=None
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

    # Fetch package metadata from npm registry
    try:
        url = f"https://registry.npmjs.org/{package}/{version}"
        print(f"{indent}↳ Requesting {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"{indent}✓ Successfully fetched {package}@{version}")
    except requests.RequestException as e:
        print(f"{indent}✗ Failed to fetch {package}@{version}: {e}")
        return {
            "error": str(e),
            "package": package,
            "version": version
        }

    # Extract dependency information
    result = {
        "name": data.get("name"),
        "version": data.get("version"),
        "description": data.get("description"),
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
            fetch_npm_deps(dep_name, clean_version, depth, _visited, _current_depth + 1, _db)
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
            fetch_npm_deps(dep_name, clean_version, depth, _visited, _current_depth + 1, _db)
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
            fetch_npm_deps(dep_name, clean_version, depth, _visited, _current_depth + 1, _db)
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
            fetch_npm_deps(dep_name, clean_version, depth, _visited, _current_depth + 1, _db)
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

        result["fetched_at"] = datetime.utcnow()

        # Upsert based on name and version
        print(f"{indent}💾 Storing {package}@{version} in database...")
        _db.dependency_trees.update_one(
            {"name": package, "version": version},
            {"$set": result},
            upsert=True
        )
        print(f"{indent}✓ Stored in database")

    print(f"{indent}✓ Completed {package}@{version}")
    return result
