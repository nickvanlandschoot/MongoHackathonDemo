"""
NPM Registry API client.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

import requests

from services.priority_resource_manager import Priority, get_resource_manager


@dataclass
class NpmVersionInfo:
    """Information about a specific npm version."""

    version: str
    publish_time: datetime
    maintainer: Optional[str]  # npm username who published
    tarball_url: str
    integrity: Optional[str]
    repository_url: Optional[str]
    dist_tags: Dict[str, str]


@dataclass
class NpmPackageMetadata:
    """Full package metadata from npm registry."""

    name: str
    versions: Dict[str, NpmVersionInfo]
    time: Dict[str, datetime]  # version -> publish time
    repository_url: Optional[str]
    maintainers: List[str]


class NpmRegistryClient:
    """
    Client for interacting with npm registry API (singleton).

    This class implements the singleton pattern to ensure a single shared
    instance with one requests.Session for optimal connection pooling.
    All methods support priority-based resource management to ensure
    user requests are never blocked by background jobs.
    """

    BASE_URL = "https://registry.npmjs.org"
    TIMEOUT = 30

    _instance: Optional["NpmRegistryClient"] = None

    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the npm client (only runs once due to singleton)."""
        # Only initialize once (singleton pattern)
        if not hasattr(self, '_initialized'):
            self._session = requests.Session()
            self._session.headers.update(
                {"Accept": "application/json", "User-Agent": "IntraceSentinel/1.0"}
            )
            self._resource_manager = get_resource_manager()
            self._initialized = True

    async def get_package_metadata(
        self,
        package_name: str,
        priority: Priority = Priority.LOW
    ) -> Optional[NpmPackageMetadata]:
        """
        Fetch full package metadata with priority-based resource management.

        Args:
            package_name: npm package name (supports scoped packages)
            priority: Priority level (HIGH for user requests, LOW for background jobs)

        Returns:
            NpmPackageMetadata or None if not found
        """
        async with self._resource_manager.acquire(priority):
            return await asyncio.to_thread(
                self._get_package_metadata_sync, package_name
            )

    async def get_version_metadata(
        self,
        package_name: str,
        version: str,
        priority: Priority = Priority.LOW
    ) -> Optional[dict]:
        """
        Fetch version-specific metadata with priority-based resource management.

        This fetches the /{package}/{version} endpoint which includes
        dependencies, devDependencies, and other version-specific data.

        Args:
            package_name: npm package name (supports scoped packages)
            version: Specific version to fetch
            priority: Priority level (HIGH for user requests, LOW for background jobs)

        Returns:
            Raw version metadata dict or None if not found
        """
        async with self._resource_manager.acquire(priority):
            return await asyncio.to_thread(
                self._get_version_metadata_sync, package_name, version
            )

    def _get_package_metadata_sync(self, package_name: str) -> Optional[NpmPackageMetadata]:
        """Synchronous implementation of get_package_metadata."""
        # Handle scoped packages (@scope/name)
        encoded_name = package_name.replace("/", "%2F")
        url = f"{self.BASE_URL}/{encoded_name}"

        try:
            response = self._session.get(url, timeout=self.TIMEOUT)
            if response.status_code == 404:
                print(f"[npm_client] Package not found: {package_name}")
                return None
            response.raise_for_status()
            data = response.json()
            return self._parse_package_metadata(data)
        except requests.RequestException as e:
            print(f"[npm_client] ERROR: Failed to fetch package {package_name}: {e}")
            return None

    def _get_version_metadata_sync(self, package_name: str, version: str) -> Optional[dict]:
        """Synchronous implementation of get_version_metadata."""
        # Handle scoped packages (@scope/name)
        encoded_name = package_name.replace("/", "%2F")
        url = f"{self.BASE_URL}/{encoded_name}/{version}"

        try:
            response = self._session.get(url, timeout=self.TIMEOUT)
            if response.status_code == 404:
                print(f"[npm_client] Version not found: {package_name}@{version}")
                return None
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"[npm_client] ERROR: Failed to fetch version {package_name}@{version}: {e}")
            return None

    async def get_recent_versions(
        self,
        package_name: str,
        since: datetime,
        priority: Priority = Priority.LOW
    ) -> List[NpmVersionInfo]:
        """
        Get versions published since a given time with priority-based resource management.

        Args:
            package_name: npm package name
            since: Cutoff datetime (UTC)
            priority: Priority level (HIGH for user requests, LOW for background jobs)

        Returns:
            List of versions published after 'since'
        """
        metadata = await self.get_package_metadata(package_name, priority)
        if not metadata:
            return []

        recent = []
        for _version, info in metadata.versions.items():
            if info.publish_time > since:
                recent.append(info)

        # Sort by publish time ascending
        recent.sort(key=lambda v: v.publish_time)
        return recent

    async def get_latest_versions(
        self,
        package_name: str,
        max_count: int = 5,
        priority: Priority = Priority.LOW
    ) -> List[NpmVersionInfo]:
        """
        Get the N most recent versions of a package with priority-based resource management.

        Args:
            package_name: npm package name
            max_count: Maximum number of versions to return (default 5)
            priority: Priority level (HIGH for user requests, LOW for background jobs)

        Returns:
            List of most recent versions, sorted oldest to newest
        """
        metadata = await self.get_package_metadata(package_name, priority)
        if not metadata:
            return []

        # Get all versions and sort by publish time descending (newest first)
        all_versions = list(metadata.versions.values())
        all_versions.sort(key=lambda v: v.publish_time, reverse=True)

        # Take the N most recent
        recent = all_versions[:max_count]

        # Reverse to get chronological order (oldest to newest)
        recent.reverse()

        return recent

    async def download_tarball(
        self,
        tarball_url: str,
        priority: Priority = Priority.LOW
    ) -> Optional[bytes]:
        """
        Download package tarball with priority-based resource management.

        Args:
            tarball_url: URL to the .tgz file
            priority: Priority level (HIGH for user requests, LOW for background jobs)

        Returns:
            Raw tarball bytes or None
        """
        async with self._resource_manager.acquire(priority):
            return await asyncio.to_thread(
                self._download_tarball_sync, tarball_url
            )

    def _download_tarball_sync(self, tarball_url: str) -> Optional[bytes]:
        """Synchronous implementation of download_tarball."""
        try:
            response = self._session.get(tarball_url, timeout=60)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            print(f"[npm_client] ERROR: Failed to download tarball from {tarball_url}: {e}")
            return None

    def _parse_package_metadata(self, data: dict) -> NpmPackageMetadata:
        """Parse raw npm API response into structured metadata."""
        time_map = {}
        for version, timestamp in data.get("time", {}).items():
            if version not in ("created", "modified"):
                try:
                    time_map[version] = datetime.fromisoformat(
                        timestamp.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    continue

        versions = {}
        for version, version_data in data.get("versions", {}).items():
            dist = version_data.get("dist", {})

            # Extract maintainer who published this version
            # npm stores this in _npmUser field
            npm_user = version_data.get("_npmUser", {})
            maintainer = npm_user.get("name") if npm_user else None

            # Extract repository URL
            repo = version_data.get("repository", {})
            repo_url = repo.get("url") if isinstance(repo, dict) else repo

            versions[version] = NpmVersionInfo(
                version=version,
                publish_time=time_map.get(version, datetime.min),
                maintainer=maintainer,
                tarball_url=dist.get("tarball", ""),
                integrity=dist.get("integrity") or dist.get("shasum"),
                repository_url=repo_url,
                dist_tags=data.get("dist-tags", {}),
            )

        # Top-level repository
        repo = data.get("repository", {})
        top_repo_url = repo.get("url") if isinstance(repo, dict) else repo

        return NpmPackageMetadata(
            name=data.get("name", ""),
            versions=versions,
            time=time_map,
            repository_url=top_repo_url,
            maintainers=[m.get("name", "") for m in data.get("maintainers", [])],
        )