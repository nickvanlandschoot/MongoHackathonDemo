"""
Package Threat Assessment repository.
"""

import asyncio
from bson import ObjectId
from typing import List, Optional

from models.package_threat_assessment import PackageThreatAssessment
from repositories.base import BaseRepository


class PackageThreatAssessmentRepository(BaseRepository[PackageThreatAssessment]):
    """Repository for package threat assessments."""

    def __init__(self, database):
        super().__init__(
            database, "package_threat_assessments", PackageThreatAssessment
        )

    async def find_current_by_package(
        self, package_id: ObjectId
    ) -> Optional[PackageThreatAssessment]:
        """
        Get the most recent threat assessment for a package.

        Args:
            package_id: Package ID

        Returns:
            Most recent PackageThreatAssessment or None
        """
        def _find():
            return self.collection.find_one(
                {"package_id": package_id},
                sort=[("timestamp", -1)]
            )

        doc = await asyncio.to_thread(_find)

        if doc:
            return self.model_class(**doc)
        return None

    async def find_by_package(
        self, package_id: ObjectId, limit: int = 10
    ) -> List[PackageThreatAssessment]:
        """
        Get historical assessments for a package.

        Args:
            package_id: Package ID
            limit: Number of assessments to retrieve

        Returns:
            List of PackageThreatAssessment records, newest first
        """
        def _find():
            cursor = (
                self.collection.find({"package_id": package_id})
                .sort("timestamp", -1)
                .limit(limit)
            )
            return [self.model_class(**doc) for doc in cursor]

        return await asyncio.to_thread(_find)

    async def find_by_version(
        self, package_id: ObjectId, version: str
    ) -> Optional[PackageThreatAssessment]:
        """
        Get assessment for a specific package version.

        Args:
            package_id: Package ID
            version: Package version

        Returns:
            PackageThreatAssessment or None
        """
        doc = await asyncio.to_thread(
            self.collection.find_one,
            {"package_id": package_id, "version": version}
        )

        if doc:
            return self.model_class(**doc)
        return None

    async def find_by_risk_level(
        self, risk_level: str, limit: int = 100
    ) -> List[PackageThreatAssessment]:
        """
        Get assessments by risk level.

        Args:
            risk_level: Risk level (low/medium/high/critical)
            limit: Maximum number of results

        Returns:
            List of PackageThreatAssessment records
        """
        def _find():
            cursor = (
                self.collection.find({"overall_risk_level": risk_level})
                .sort("timestamp", -1)
                .limit(limit)
            )
            return [self.model_class(**doc) for doc in cursor]

        return await asyncio.to_thread(_find)

    async def get_stats(self) -> dict:
        """
        Get statistics about threat assessments.

        Returns:
            Dictionary with statistics
        """
        def _aggregate():
            pipeline = [{"$group": {"_id": "$overall_risk_level", "count": {"$sum": 1}}}]
            result = {"total": 0, "by_risk_level": {}}
            for doc in self.collection.aggregate(pipeline):
                risk_level = doc["_id"]
                count = doc["count"]
                result["by_risk_level"][risk_level] = count
                result["total"] += count
            return result

        return await asyncio.to_thread(_aggregate)
