"""
PackageDelta repository implementation.
"""

from typing import List, Optional

from bson import ObjectId
from pymongo.database import Database

from models.package_delta import PackageDelta
from repositories.base import BaseRepository


class PackageDeltaRepository(BaseRepository[PackageDelta]):
    """Repository for PackageDelta entities."""

    def __init__(self, database: Database):
        super().__init__(database, "package_deltas", PackageDelta)

    async def find_by_package(
        self, package_id: str | ObjectId, skip: int = 0, limit: int = 100
    ) -> List[PackageDelta]:
        """
        Find deltas for a package.

        Args:
            package_id: Package ID
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of deltas sorted by computation time (newest first)
        """
        if isinstance(package_id, str):
            package_id = ObjectId(package_id)

        return await self.find_many(
            {"package_id": package_id},
            skip=skip,
            limit=limit,
            sort=[("computed_at", -1)],
        )

    async def find_delta(
        self, package_id: str | ObjectId, from_version: str, to_version: str
    ) -> Optional[PackageDelta]:
        """
        Find specific version delta.

        Args:
            package_id: Package ID
            from_version: Source version
            to_version: Target version

        Returns:
            Delta if found, None otherwise
        """
        if isinstance(package_id, str):
            package_id = ObjectId(package_id)

        return await self.find_one(
            {"package_id": package_id, "from_version": from_version, "to_version": to_version}
        )

    async def find_with_install_scripts(
        self, skip: int = 0, limit: int = 100
    ) -> List[PackageDelta]:
        """
        Find deltas that touched install scripts.

        Args:
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of deltas with install script changes
        """
        return await self.find_many(
            {"signals.touched_install_scripts": True},
            skip=skip,
            limit=limit,
            sort=[("computed_at", -1)],
        )

    async def find_with_network_calls(
        self, skip: int = 0, limit: int = 100
    ) -> List[PackageDelta]:
        """
        Find deltas that added network calls.

        Args:
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of deltas with network calls added
        """
        return await self.find_many(
            {"signals.added_network_calls": True},
            skip=skip,
            limit=limit,
            sort=[("computed_at", -1)],
        )

    async def find_obfuscated(
        self, skip: int = 0, limit: int = 100
    ) -> List[PackageDelta]:
        """
        Find deltas with obfuscated code.

        Args:
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of deltas with obfuscated code
        """
        return await self.find_many(
            {"signals.minified_or_obfuscated_delta": True},
            skip=skip,
            limit=limit,
            sort=[("computed_at", -1)],
        )

    async def find_high_risk(
        self, threshold: float = 70.0, skip: int = 0, limit: int = 100
    ) -> List[PackageDelta]:
        """
        Find high-risk deltas.

        Args:
            threshold: Minimum risk score
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of high-risk deltas sorted by risk score
        """
        return await self.find_many(
            {"risk_score": {"$gte": threshold}},
            skip=skip,
            limit=limit,
            sort=[("risk_score", -1)],
        )
