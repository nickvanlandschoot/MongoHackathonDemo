"""
PackageIdentity repository implementation.
"""

from typing import List

from bson import ObjectId
from pymongo.database import Database

from models.package_identity import PackageIdentity
from repositories.base import BaseRepository


class PackageIdentityRepository(BaseRepository[PackageIdentity]):
    """Repository for PackageIdentity entities."""

    def __init__(self, database: Database):
        super().__init__(database, "package_identities", PackageIdentity)

    def find_by_package(
        self, package_id: str | ObjectId, skip: int = 0, limit: int = 100
    ) -> List[PackageIdentity]:
        """
        Find identities linked to a package.

        Args:
            package_id: Package ID
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of package-identity relationships
        """
        if isinstance(package_id, str):
            package_id = ObjectId(package_id)

        return self.find_many({"package_id": package_id}, skip=skip, limit=limit)

    def find_by_identity(
        self, identity_id: str | ObjectId, skip: int = 0, limit: int = 100
    ) -> List[PackageIdentity]:
        """
        Find packages linked to an identity.

        Args:
            identity_id: Identity ID
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of package-identity relationships
        """
        if isinstance(identity_id, str):
            identity_id = ObjectId(identity_id)

        return self.find_many({"identity_id": identity_id}, skip=skip, limit=limit)

    def find_publishers(
        self, package_id: str | ObjectId, skip: int = 0, limit: int = 100
    ) -> List[PackageIdentity]:
        """
        Find identities with publish permissions for a package.

        Args:
            package_id: Package ID
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of package-identity relationships with publish permissions
        """
        if isinstance(package_id, str):
            package_id = ObjectId(package_id)

        return self.find_many(
            {"package_id": package_id, "permission_level": "publish"},
            skip=skip,
            limit=limit,
        )

    def find_by_role(
        self, package_id: str | ObjectId, role: str, skip: int = 0, limit: int = 100
    ) -> List[PackageIdentity]:
        """
        Find identities by role for a package.

        Args:
            package_id: Package ID
            role: Role (owner, maintainer, contributor)
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of package-identity relationships
        """
        if isinstance(package_id, str):
            package_id = ObjectId(package_id)

        return self.find_many(
            {"package_id": package_id, "role": role}, skip=skip, limit=limit
        )
