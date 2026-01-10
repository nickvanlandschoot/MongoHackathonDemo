"""
PackageRelease repository implementation.
"""

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pymongo.database import Database

from models.package_release import PackageRelease
from repositories.base import BaseRepository


class PackageReleaseRepository(BaseRepository[PackageRelease]):
    """Repository for PackageRelease entities."""

    def __init__(self, database: Database):
        super().__init__(database, "package_releases", PackageRelease)

    def find_by_package(
        self, package_id: str | ObjectId, skip: int = 0, limit: int = 100
    ) -> List[PackageRelease]:
        """
        Find releases for a package.

        Args:
            package_id: Package ID
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of releases sorted by publish time (newest first)
        """
        if isinstance(package_id, str):
            package_id = ObjectId(package_id)

        return self.find_many(
            {"package_id": package_id},
            skip=skip,
            limit=limit,
            sort=[("publish_timestamp", -1)],
        )

    def find_by_version(
        self, package_id: str | ObjectId, version: str
    ) -> Optional[PackageRelease]:
        """
        Find specific version release.

        Args:
            package_id: Package ID
            version: Version string

        Returns:
            Release if found, None otherwise
        """
        if isinstance(package_id, str):
            package_id = ObjectId(package_id)

        return self.find_one({"package_id": package_id, "version": version})

    def find_by_publisher(
        self, identity_id: str | ObjectId, skip: int = 0, limit: int = 100
    ) -> List[PackageRelease]:
        """
        Find releases by publisher.

        Args:
            identity_id: Identity ID
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of releases sorted by publish time (newest first)
        """
        if isinstance(identity_id, str):
            identity_id = ObjectId(identity_id)

        return self.find_many(
            {"published_by": identity_id},
            skip=skip,
            limit=limit,
            sort=[("publish_timestamp", -1)],
        )

    def find_recent(
        self, hours: int = 24, skip: int = 0, limit: int = 100
    ) -> List[PackageRelease]:
        """
        Find recent releases.

        Args:
            hours: Look back period in hours
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of releases sorted by publish time (newest first)
        """
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = cutoff.replace(hour=cutoff.hour - hours)

        return self.find_many(
            {"publish_timestamp": {"$gte": cutoff}},
            skip=skip,
            limit=limit,
            sort=[("publish_timestamp", -1)],
        )

    def find_high_risk(
        self, threshold: float = 70.0, skip: int = 0, limit: int = 100
    ) -> List[PackageRelease]:
        """
        Find high-risk releases.

        Args:
            threshold: Minimum risk score
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of high-risk releases sorted by risk score
        """
        return self.find_many(
            {"risk_score": {"$gte": threshold}},
            skip=skip,
            limit=limit,
            sort=[("risk_score", -1)],
        )
