"""
Dependency repository implementation.
"""

from typing import List

from bson import ObjectId
from pymongo.database import Database

from models.dependency import Dependency
from repositories.base import BaseRepository


class DependencyRepository(BaseRepository[Dependency]):
    """Repository for Dependency entities."""

    def __init__(self, database: Database):
        super().__init__(database, "dependencies", Dependency)

    def find_by_package(self, package_id: str | ObjectId, skip: int = 0, limit: int = 100) -> List[Dependency]:
        """
        Find dependencies for a package.

        Args:
            package_id: Package ID
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of dependencies
        """
        if isinstance(package_id, str):
            package_id = ObjectId(package_id)

        return self.find_many({"package_id": package_id}, skip=skip, limit=limit)

    def find_dependents(self, package_id: str | ObjectId, skip: int = 0, limit: int = 100) -> List[Dependency]:
        """
        Find packages that depend on this package.

        Args:
            package_id: Package ID
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of dependency edges where this package is the dependency
        """
        if isinstance(package_id, str):
            package_id = ObjectId(package_id)

        return self.find_many({"depends_on_id": package_id}, skip=skip, limit=limit)

    def find_by_type(
        self, package_id: str | ObjectId, dep_type: str, skip: int = 0, limit: int = 100
    ) -> List[Dependency]:
        """
        Find dependencies of specific type.

        Args:
            package_id: Package ID
            dep_type: Dependency type (prod, dev, optional, peer)
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of dependencies
        """
        if isinstance(package_id, str):
            package_id = ObjectId(package_id)

        return self.find_many(
            {"package_id": package_id, "dep_type": dep_type}, skip=skip, limit=limit
        )

    def find_production_deps(
        self, package_id: str | ObjectId, skip: int = 0, limit: int = 100
    ) -> List[Dependency]:
        """
        Find production dependencies.

        Args:
            package_id: Package ID
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of production dependencies
        """
        return self.find_by_type(package_id, "prod", skip, limit)
