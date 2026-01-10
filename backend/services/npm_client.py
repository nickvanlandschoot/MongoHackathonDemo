"""
NPM Registry API client.
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

import requests


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
    """Client for interacting with npm registry API."""

    BASE_URL = "https://registry.npmjs.org"
    TIMEOUT = 30

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(
            {"Accept": "application/json", "User-Agent": "IntraceSentinel/1.0"}
        )

    def get_package_metadata(self, package_name: str) -> Optional[NpmPackageMetadata]:
        """
        Fetch full package metadata.

        Args:
            package_name: npm package name (supports scoped packages)

        Returns:
            NpmPackageMetadata or None if not found
        """
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

    def get_recent_versions(
        self, package_name: str, since: datetime
    ) -> List[NpmVersionInfo]:
        """
        Get versions published since a given time.

        Args:
            package_name: npm package name
            since: Cutoff datetime (UTC)

        Returns:
            List of versions published after 'since'
        """
        metadata = self.get_package_metadata(package_name)
        if not metadata:
            return []

        recent = []
        for _version, info in metadata.versions.items():
            if info.publish_time > since:
                recent.append(info)

        # Sort by publish time ascending
        recent.sort(key=lambda v: v.publish_time)
        return recent

    def download_tarball(self, tarball_url: str) -> Optional[bytes]:
        """
        Download package tarball.

        Args:
            tarball_url: URL to the .tgz file

        Returns:
            Raw tarball bytes or None
        """
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