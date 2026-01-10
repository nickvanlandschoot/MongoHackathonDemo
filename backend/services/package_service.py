"""
Package service - shared business logic for package operations.
"""

import asyncio
from typing import Optional
from datetime import datetime, timezone

from models.analysis import Analysis
from models.package import Package, ScanState
from models.identity import Identity
from repositories.package import PackageRepository
from repositories.identity import IdentityRepository
from services.npm_client import NpmRegistryClient
from services.github_client import GitHubApiClient
from database import get_database


async def get_or_create_package_with_enrichment(
    package_name: str,
    npm_client: NpmRegistryClient,
    repo: PackageRepository,
) -> Optional[Package]:
    """
    Get existing package or create new one with full metadata and GitHub enrichment.

    This is used by both the API and the watcher to ensure all packages
    (manually added or auto-discovered) get full enrichment.

    Args:
        package_name: npm package name (supports scoped packages)
        npm_client: NpmRegistryClient instance
        repo: PackageRepository instance

    Returns:
        Existing or newly created Package (None if npm fetch fails)
    """
    # Check if package already exists
    existing = repo.find_by_name(package_name)
    if existing:
        return existing

    # Fetch metadata from npm registry (offload HTTP call to thread)
    metadata = await asyncio.to_thread(
        npm_client.get_package_metadata, package_name
    )
    if not metadata:
        print(f"[package_service] Package '{package_name}' not found on npm registry")
        return None

    # Extract latest version
    if not metadata.versions:
        print(f"[package_service] Package '{package_name}' has no versions")
        return None

    # Get dist_tags from any version (they all have the same reference)
    first_version_info = next(iter(metadata.versions.values()))
    dist_tags = first_version_info.dist_tags

    # Get latest version tag
    latest_tag = dist_tags.get("latest")
    if not latest_tag:
        print(f"[package_service] Package '{package_name}' has no 'latest' dist-tag")
        return None

    # Get version info for latest version
    latest_version_info = metadata.versions.get(latest_tag)
    if not latest_version_info:
        print(f"[package_service] Package '{package_name}' latest version not found in metadata")
        return None

    # Extract package data
    repo_url = metadata.repository_url
    owner = metadata.maintainers[0] if metadata.maintainers else None

    # Create Package with initial state
    package = Package(
        name=package_name,
        registry="npm",
        repo_url=repo_url,
        owner=owner,
        risk_score=0.0,
        last_scanned=datetime.now(timezone.utc),
        scan_state=ScanState(),
        analysis=Analysis(
            summary=f"Package {package_name} added for monitoring",
            reasons=["Newly added package"],
            confidence=1.0,
            source="rule",
        ),
    )

    # Save to database
    created = repo.create(package)
    print(f"[package_service] Created Package: {package_name} (repo: {repo_url or 'none'})")

    # Crawl maintainers from npm
    maintainer_count = await crawl_package_maintainers(package_name, npm_client, repo)
    print(f"[package_service] Crawled {maintainer_count} maintainers for {package_name}")

    # Enrich with GitHub data if repo_url exists
    if repo_url:
        await enrich_github_data(repo_url)

    return created


async def crawl_package_maintainers(
    package_name: str,
    npm_client: NpmRegistryClient,
    repo: PackageRepository,
) -> int:
    """
    Crawl npm package maintainers and create Identity records.

    Fetches the current maintainers list from npm registry and creates
    Identity records for each maintainer if they don't already exist.

    Args:
        package_name: npm package name
        npm_client: NpmRegistryClient instance
        repo: PackageRepository instance

    Returns:
        Number of maintainers processed
    """
    try:
        # Fetch package metadata (offload HTTP call to thread)
        metadata = await asyncio.to_thread(
            npm_client.get_package_metadata, package_name
        )
        if not metadata or not metadata.maintainers:
            print(f"[package_service] No maintainers found for {package_name}")
            return 0

        db = get_database()
        identity_repo = IdentityRepository(db)
        maintainers_processed = 0

        for maintainer_handle in metadata.maintainers:
            if not maintainer_handle:
                continue

            # Check if identity already exists
            existing = identity_repo.find_by_handle(maintainer_handle, kind="npm")
            if existing:
                print(f"[package_service] npm identity already exists: {maintainer_handle}")
                maintainers_processed += 1
                continue

            # Create new Identity for npm maintainer
            identity = Identity(
                kind="npm",
                handle=maintainer_handle,
                affiliation_tag="unknown",
                first_seen=datetime.now(timezone.utc),
                risk_score=20.0,  # Base risk for unknown identity
                analysis=Analysis(
                    summary=f"npm maintainer: {maintainer_handle}",
                    reasons=["npm package maintainer"],
                    confidence=0.8,
                    source="rule",
                ),
            )

            identity_repo.create(identity)
            print(f"[package_service] Created npm identity: {maintainer_handle}")
            maintainers_processed += 1

        # Update package scan_state to mark maintainers as crawled
        package = repo.find_by_name(package_name)
        if package and package.id:
            repo.update(
                package.id,
                {
                    "scan_state.maintainers_crawled": True,
                }
            )
            print(f"[package_service] Marked maintainers as crawled for {package_name}")

        return maintainers_processed

    except Exception as e:
        print(f"[package_service] ERROR crawling maintainers for {package_name}: {e}")
        return 0


async def enrich_github_data(repo_url: str) -> None:
    """
    Fetch GitHub data for repo owner and store in Identity collection.

    Args:
        repo_url: GitHub repository URL
    """
    try:
        # Extract GitHub username
        github_client = GitHubApiClient()
        github_username = github_client.parse_github_username_from_repo_url(repo_url)

        if not github_username:
            print(f"[package_service] Could not parse GitHub username from: {repo_url}")
            return

        # Fetch GitHub user info (offload HTTP call to thread)
        github_info = await asyncio.to_thread(
            github_client.get_user, github_username
        )
        if not github_info:
            print(f"[package_service] Could not fetch GitHub user: {github_username}")
            return

        # Check if identity already exists
        db = get_database()
        identity_repo = IdentityRepository(db)
        existing = identity_repo.find_by_handle(github_username, kind="github")

        if existing:
            print(f"[package_service] GitHub identity already exists: {github_username}")
            return

        # Create new Identity for GitHub user
        identity = Identity(
            kind="github",
            handle=github_username,
            email_domain=github_info.email.split('@')[1] if github_info.email and '@' in github_info.email else None,
            affiliation_tag="unknown",  # Can be enriched later
            country=None,
            first_seen=datetime.now(timezone.utc),
            risk_score=25.0 if github_info.is_new_account else 10.0,  # Higher risk for new accounts
            analysis=Analysis(
                summary=f"GitHub user: {github_username}",
                reasons=[
                    f"Account created: {github_info.created_at.strftime('%Y-%m-%d')}",
                    f"{github_info.public_repos} public repos",
                    f"{github_info.followers} followers",
                    f"Organizations: {', '.join(github_info.organizations[:3]) if github_info.organizations else 'None'}",
                ],
                confidence=0.8,
                source="rule",
            ),
        )

        identity_repo.create(identity)
        print(f"[package_service] Created GitHub identity: {github_username}")

    except Exception as e:
        # Don't fail package creation if GitHub enrichment fails
        print(f"[package_service] ERROR during GitHub enrichment: {e}")