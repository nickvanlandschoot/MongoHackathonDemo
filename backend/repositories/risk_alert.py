"""
RiskAlert repository implementation.
"""

from typing import List

from bson import ObjectId
from pymongo.database import Database

from models.risk_alert import RiskAlert
from repositories.base import BaseRepository


class RiskAlertRepository(BaseRepository[RiskAlert]):
    """Repository for RiskAlert entities."""

    def __init__(self, database: Database):
        super().__init__(database, "risk_alerts", RiskAlert)

    async def find_by_package(
        self, package_id: str | ObjectId, skip: int = 0, limit: int = 100
    ) -> List[RiskAlert]:
        """
        Find alerts for a package.

        Args:
            package_id: Package ID
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of alerts sorted by timestamp (newest first)
        """
        if isinstance(package_id, str):
            package_id = ObjectId(package_id)

        return await self.find_many(
            {"package_id": package_id},
            skip=skip,
            limit=limit,
            sort=[("timestamp", -1)],
        )

    async def find_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> List[RiskAlert]:
        """
        Find alerts by status.

        Args:
            status: Alert status (open, investigated, resolved)
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of alerts sorted by timestamp (newest first)
        """
        return await self.find_many(
            {"status": status}, skip=skip, limit=limit, sort=[("timestamp", -1)]
        )

    async def find_open_alerts(self, skip: int = 0, limit: int = 100) -> List[RiskAlert]:
        """
        Find open alerts.

        Args:
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of open alerts sorted by severity (highest first)
        """
        return await self.find_many(
            {"status": "open"},
            skip=skip,
            limit=limit,
            sort=[("severity", -1), ("timestamp", -1)],
        )

    async def find_by_release(
        self, release_id: str | ObjectId, skip: int = 0, limit: int = 100
    ) -> List[RiskAlert]:
        """
        Find alerts triggered by a release.

        Args:
            release_id: Release ID
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of alerts
        """
        if isinstance(release_id, str):
            release_id = ObjectId(release_id)

        return await self.find_many(
            {"release_id": release_id}, skip=skip, limit=limit, sort=[("timestamp", -1)]
        )

    async def find_by_delta(
        self, delta_id: str | ObjectId, skip: int = 0, limit: int = 100
    ) -> List[RiskAlert]:
        """
        Find alerts triggered by a delta.

        Args:
            delta_id: Delta ID
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of alerts
        """
        if isinstance(delta_id, str):
            delta_id = ObjectId(delta_id)

        return await self.find_many(
            {"delta_id": delta_id}, skip=skip, limit=limit, sort=[("timestamp", -1)]
        )

    async def find_high_severity(
        self, threshold: float = 70.0, skip: int = 0, limit: int = 100
    ) -> List[RiskAlert]:
        """
        Find high-severity alerts.

        Args:
            threshold: Minimum severity score
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of high-severity alerts sorted by severity
        """
        return await self.find_many(
            {"severity": {"$gte": threshold}},
            skip=skip,
            limit=limit,
            sort=[("severity", -1), ("timestamp", -1)],
        )
