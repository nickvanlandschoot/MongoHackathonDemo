"""
GitHubEvent repository implementation.
"""

from typing import List

from bson import ObjectId
from pymongo.database import Database

from models.github_event import GitHubEvent
from repositories.base import BaseRepository


class GitHubEventRepository(BaseRepository[GitHubEvent]):
    """Repository for GitHubEvent entities."""

    def __init__(self, database: Database):
        super().__init__(database, "github_events", GitHubEvent)

    def find_by_package(
        self, package_id: str | ObjectId, skip: int = 0, limit: int = 100
    ) -> List[GitHubEvent]:
        """
        Find GitHub events for a package.

        Args:
            package_id: Package ID
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of events sorted by timestamp (newest first)
        """
        if isinstance(package_id, str):
            package_id = ObjectId(package_id)

        return self.find_many(
            {"package_id": package_id},
            skip=skip,
            limit=limit,
            sort=[("timestamp", -1)],
        )

    def find_by_type(
        self, event_type: str, skip: int = 0, limit: int = 100
    ) -> List[GitHubEvent]:
        """
        Find events by type.

        Args:
            event_type: Event type (pr, commit, release, security_advisory)
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of events sorted by timestamp (newest first)
        """
        return self.find_many(
            {"type": event_type}, skip=skip, limit=limit, sort=[("timestamp", -1)]
        )

    def find_security_advisories(
        self, package_id: str | ObjectId | None = None, skip: int = 0, limit: int = 100
    ) -> List[GitHubEvent]:
        """
        Find security advisory events.

        Args:
            package_id: Optional package ID filter
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of security advisories sorted by timestamp (newest first)
        """
        filter_dict = {"type": "security_advisory"}

        if package_id:
            if isinstance(package_id, str):
                package_id = ObjectId(package_id)
            filter_dict["package_id"] = package_id

        return self.find_many(filter_dict, skip=skip, limit=limit, sort=[("timestamp", -1)])

    def find_by_actor(
        self, actor: str, skip: int = 0, limit: int = 100
    ) -> List[GitHubEvent]:
        """
        Find events by actor.

        Args:
            actor: GitHub actor/username
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of events sorted by timestamp (newest first)
        """
        return self.find_many(
            {"actor": actor}, skip=skip, limit=limit, sort=[("timestamp", -1)]
        )
