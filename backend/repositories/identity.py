"""
Identity repository implementation.
"""

from typing import List, Optional

from pymongo.database import Database

from models.identity import Identity
from repositories.base import BaseRepository


class IdentityRepository(BaseRepository[Identity]):
    """Repository for Identity entities."""

    def __init__(self, database: Database):
        super().__init__(database, "identities", Identity)

    async def find_by_handle(self, handle: str, kind: Optional[str] = None) -> Optional[Identity]:
        """
        Find identity by handle.

        Args:
            handle: Identity handle (username)
            kind: Optional identity kind filter (npm, github, email_domain)

        Returns:
            Identity if found, None otherwise
        """
        filter_dict = {"handle": handle}
        if kind:
            filter_dict["kind"] = kind

        return await self.find_one(filter_dict)

    async def find_by_kind(self, kind: str, skip: int = 0, limit: int = 100) -> List[Identity]:
        """
        Find identities by kind.

        Args:
            kind: Identity kind (npm, github, email_domain)
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of identities
        """
        return await self.find_many({"kind": kind}, skip=skip, limit=limit)

    async def find_by_affiliation(
        self, affiliation_tag: str, skip: int = 0, limit: int = 100
    ) -> List[Identity]:
        """
        Find identities by affiliation.

        Args:
            affiliation_tag: Affiliation tag (corporate, academic, anonymous)
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of identities
        """
        return await self.find_many({"affiliation_tag": affiliation_tag}, skip=skip, limit=limit)

    async def find_high_risk(
        self, threshold: float = 70.0, skip: int = 0, limit: int = 100
    ) -> List[Identity]:
        """
        Find high-risk identities.

        Args:
            threshold: Minimum risk score
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of high-risk identities
        """
        return await self.find_many(
            {"risk_score": {"$gte": threshold}},
            skip=skip,
            limit=limit,
            sort=[("risk_score", -1)],
        )
