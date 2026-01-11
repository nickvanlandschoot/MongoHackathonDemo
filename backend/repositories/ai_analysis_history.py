"""
AI Analysis History repository.
"""

import asyncio
from bson import ObjectId
from typing import List, Optional

from models.ai_analysis_history import AIAnalysisHistory
from repositories.base import BaseRepository


class AIAnalysisHistoryRepository(BaseRepository[AIAnalysisHistory]):
    """Repository for AI analysis history records."""

    def __init__(self, database):
        super().__init__(database, "ai_analysis_history", AIAnalysisHistory)

    async def find_by_package(
        self, package_id: ObjectId, limit: int = 10
    ) -> List[AIAnalysisHistory]:
        """
        Get last N analyses for a package, sorted by timestamp descending.
        Used for building context for new analyses.

        Args:
            package_id: Package ID
            limit: Number of analyses to retrieve (default: 10)

        Returns:
            List of AIAnalysisHistory records
        """
        def _find():
            cursor = (
                self.collection.find({"package_id": package_id})
                .sort("timestamp", -1)
                .limit(limit)
            )
            return [self.model_class(**doc) for doc in cursor]

        return await asyncio.to_thread(_find)

    async def find_recent_analyses(
        self, package_id: ObjectId, days: int = 30
    ) -> List[AIAnalysisHistory]:
        """
        Get all analyses for a package within the last N days.

        Args:
            package_id: Package ID
            days: Number of days to look back

        Returns:
            List of AIAnalysisHistory records
        """
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        def _find():
            cursor = self.collection.find(
                {"package_id": package_id, "timestamp": {"$gte": cutoff}}
            ).sort("timestamp", -1)
            return [self.model_class(**doc) for doc in cursor]

        return await asyncio.to_thread(_find)

    async def cleanup_old_analyses(
        self, package_id: ObjectId, keep_last: int = 50
    ) -> int:
        """
        Delete old analysis records for a package, keeping only the last N.
        Prevents unbounded growth of analysis history.

        Args:
            package_id: Package ID
            keep_last: Number of most recent analyses to keep (default: 50)

        Returns:
            Number of records deleted
        """
        def _get_ids_to_keep():
            cursor = (
                self.collection.find({"package_id": package_id}, {"_id": 1})
                .sort("timestamp", -1)
                .limit(keep_last)
            )
            return [doc["_id"] for doc in cursor]

        # Get IDs of records to keep
        ids_to_keep = await asyncio.to_thread(_get_ids_to_keep)

        # Delete all records not in the keep list
        if ids_to_keep:
            result = await asyncio.to_thread(
                self.collection.delete_many,
                {"package_id": package_id, "_id": {"$nin": ids_to_keep}}
            )
            return result.deleted_count
        else:
            # If no records to keep, delete all for this package
            result = await asyncio.to_thread(
                self.collection.delete_many,
                {"package_id": package_id}
            )
            return result.deleted_count

    async def count(self, filter_dict: Optional[dict] = None) -> int:
        """Count documents matching filter."""
        if filter_dict is None:
            filter_dict = {}
        return await asyncio.to_thread(self.collection.count_documents, filter_dict)
