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

    def find_by_name(self, name: str) -> Optional[Package]:
        """
        Find package by name.

        Args:
            name: Package name

        Returns:
            Package if found, None otherwise
        """
        return self.find_one({"name": name})

    def find_by_registry(self, registry: str, skip: int = 0, limit: int = 100) -> List[Package]:
        """
        Find packages by registry.

        Args:
            registry: Registry name (e.g., 'npm')
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of packages
        """
        return self.find_many({"registry": registry}, skip=skip, limit=limit)

    def find_by_owner(self, owner: str, skip: int = 0, limit: int = 100) -> List[Package]:
        """
        Find packages by owner.

        Args:
            owner: Owner handle
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of packages
        """
        return self.find_many({"owner": owner}, skip=skip, limit=limit)

    def find_high_risk(
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
        return self.find_many(
            {"risk_score": {"$gte": threshold}},
            skip=skip,
            limit=limit,
            sort=[("risk_score", -1)],
        )

    def find_needs_scan(self, skip: int = 0, limit: int = 100) -> List[Package]:
        """
        Find packages needing full scan.

        Args:
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of packages needing scan
        """
        return self.find_many(
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
