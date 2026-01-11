"""
Base repository with common CRUD operations.
"""

import asyncio
from typing import Generic, List, Optional, Type, TypeVar

from bson import ObjectId
from pydantic import BaseModel
from pymongo.collection import Collection
from pymongo.database import Database

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """
    Base repository providing common CRUD operations.

    Type parameter T should be a Pydantic model.
    """

    def __init__(self, database: Database, collection_name: str, model_class: Type[T]):
        """
        Initialize repository.

        Args:
            database: MongoDB database instance
            collection_name: Name of the collection
            model_class: Pydantic model class for this repository
        """
        self.database = database
        self.collection: Collection = database[collection_name]
        self.model_class = model_class

    async def create(self, entity: T) -> T:
        """
        Create a new document.

        Args:
            entity: Entity to create

        Returns:
            Created entity with _id populated
        """
        entity_dict = entity.model_dump(by_alias=True, exclude={"id"})
        result = await asyncio.to_thread(self.collection.insert_one, entity_dict)
        entity_dict["_id"] = result.inserted_id
        return self.model_class(**entity_dict)

    async def find_by_id(self, entity_id: str | ObjectId) -> Optional[T]:
        """
        Find document by ID.

        Args:
            entity_id: Document ID (string or ObjectId)

        Returns:
            Entity if found, None otherwise
        """
        if isinstance(entity_id, str):
            entity_id = ObjectId(entity_id)

        doc = await asyncio.to_thread(self.collection.find_one, {"_id": entity_id})
        return self.model_class(**doc) if doc else None

    async def find_one(self, filter_dict: dict) -> Optional[T]:
        """
        Find single document matching filter.

        Args:
            filter_dict: MongoDB filter query

        Returns:
            Entity if found, None otherwise
        """
        doc = await asyncio.to_thread(self.collection.find_one, filter_dict)
        return self.model_class(**doc) if doc else None

    async def find_many(
        self,
        filter_dict: dict,
        skip: int = 0,
        limit: int = 100,
        sort: Optional[List[tuple]] = None,
    ) -> List[T]:
        """
        Find multiple documents matching filter.

        Args:
            filter_dict: MongoDB filter query
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort: List of (field, direction) tuples for sorting

        Returns:
            List of entities
        """
        def _find():
            cursor = self.collection.find(filter_dict).skip(skip).limit(limit)
            if sort:
                cursor = cursor.sort(sort)
            return [self.model_class(**doc) for doc in cursor]

        return await asyncio.to_thread(_find)

    async def find_all(
        self, skip: int = 0, limit: int = 100, sort: Optional[List[tuple]] = None
    ) -> List[T]:
        """
        Find all documents in collection.

        Args:
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort: List of (field, direction) tuples for sorting

        Returns:
            List of entities
        """
        return await self.find_many({}, skip=skip, limit=limit, sort=sort)

    async def update(self, entity_id: str | ObjectId, update_dict: dict) -> Optional[T]:
        """
        Update document by ID.

        Args:
            entity_id: Document ID
            update_dict: Fields to update (uses $set operator)

        Returns:
            Updated entity if found, None otherwise
        """
        if isinstance(entity_id, str):
            entity_id = ObjectId(entity_id)

        def _update():
            return self.collection.find_one_and_update(
                {"_id": entity_id},
                {"$set": update_dict},
                return_document=True,
            )

        result = await asyncio.to_thread(_update)
        return self.model_class(**result) if result else None

    async def update_one(self, filter_dict: dict, update_dict: dict) -> Optional[T]:
        """
        Update single document matching filter.

        Args:
            filter_dict: MongoDB filter query
            update_dict: Fields to update (uses $set operator)

        Returns:
            Updated entity if found, None otherwise
        """
        def _update():
            return self.collection.find_one_and_update(
                filter_dict,
                {"$set": update_dict},
                return_document=True,
            )

        result = await asyncio.to_thread(_update)
        return self.model_class(**result) if result else None

    async def delete(self, entity_id: str | ObjectId) -> bool:
        """
        Delete document by ID.

        Args:
            entity_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        if isinstance(entity_id, str):
            entity_id = ObjectId(entity_id)

        result = await asyncio.to_thread(self.collection.delete_one, {"_id": entity_id})
        return result.deleted_count > 0

    async def delete_one(self, filter_dict: dict) -> bool:
        """
        Delete single document matching filter.

        Args:
            filter_dict: MongoDB filter query

        Returns:
            True if deleted, False if not found
        """
        result = await asyncio.to_thread(self.collection.delete_one, filter_dict)
        return result.deleted_count > 0

    async def delete_many(self, filter_dict: dict) -> int:
        """
        Delete multiple documents matching filter.

        Args:
            filter_dict: MongoDB filter query

        Returns:
            Number of documents deleted
        """
        result = await asyncio.to_thread(self.collection.delete_many, filter_dict)
        return result.deleted_count

    async def count(self, filter_dict: Optional[dict] = None) -> int:
        """
        Count documents matching filter.

        Args:
            filter_dict: MongoDB filter query (counts all if None)

        Returns:
            Document count
        """
        return await asyncio.to_thread(self.collection.count_documents, filter_dict or {})

    async def exists(self, filter_dict: dict) -> bool:
        """
        Check if document exists matching filter.

        Args:
            filter_dict: MongoDB filter query

        Returns:
            True if exists, False otherwise
        """
        count = await asyncio.to_thread(self.collection.count_documents, filter_dict, limit=1)
        return count > 0
