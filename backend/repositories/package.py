"""
Package repository implementation.
"""

from typing import List, Optional

from pymongo.database import Database

from models.package import Package
from repositories.base import BaseRepository


class PackageRepository(BaseRepository[Package]):
    """Repository for Package entities."""

    def __init__(self, database: Database):
        super().__init__(database, "packages", Package)

    async def find_by_name(self, name: str) -> Optional[Package]:
        """
        Find package by name.

        Args:
            name: Package name

        Returns:
            Package if found, None otherwise
        """
        return await self.find_one({"name": name})

    async def find_by_registry(self, registry: str, skip: int = 0, limit: int = 100) -> List[Package]:
        """
        Find packages by registry.

        Args:
            registry: Registry name (e.g., 'npm')
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of packages
        """
        return await self.find_many({"registry": registry}, skip=skip, limit=limit)

    async def find_by_owner(self, owner: str, skip: int = 0, limit: int = 100) -> List[Package]:
        """
        Find packages by owner.

        Args:
            owner: Owner handle
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of packages
        """
        return await self.find_many({"owner": owner}, skip=skip, limit=limit)

    async def find_high_risk(
        self, threshold: float = 70.0, skip: int = 0, limit: int = 100
    ) -> List[Package]:
        """
        Find high-risk packages.

        Args:
            threshold: Minimum risk score
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of high-risk packages
        """
        return await self.find_many(
            {"risk_score": {"$gte": threshold}},
            skip=skip,
            limit=limit,
            sort=[("risk_score", -1)],
        )

    async def find_needs_scan(self, skip: int = 0, limit: int = 100) -> List[Package]:
        """
        Find packages needing full scan.

        Args:
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of packages needing scan
        """
        return await self.find_many(
            {
                "$or": [
                    {"scan_state.deps_crawled": False},
                    {"scan_state.releases_crawled": False},
                    {"scan_state.maintainers_crawled": False},
                ]
            },
            skip=skip,
            limit=limit,
        )

    async def search_by_name(self, search_term: str, skip: int = 0, limit: int = 100) -> List[Package]:
        """
        Search packages by name (case-insensitive).

        Args:
            search_term: Search term to match against package names
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of matching packages
        """
        return await self.find_many(
            {"name": {"$regex": search_term, "$options": "i"}},
            skip=skip,
            limit=limit,
            sort=[("name", 1)],
        )
