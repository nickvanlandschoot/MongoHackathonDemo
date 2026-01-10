"""
Database connection management for MongoDB.
"""

from functools import lru_cache
from typing import Optional

import certifi
from pymongo import MongoClient
from pymongo.database import Database

from env import MONGODB_URI, MONGODB_DATABASE_NAME


class DatabaseManager:
    """
    Singleton database connection manager.
    Provides connection pooling and lifecycle management.
    """

    _instance: Optional["DatabaseManager"] = None
    _client: Optional[MongoClient] = None
    _database: Optional[Database] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self, uri: Optional[str] = None, database_name: Optional[str] = None) -> None:
        """
        Establish connection to MongoDB.

        Args:
            uri: MongoDB connection URI. Uses MONGODB_URI from env if not provided.
            database_name: Database name. Uses MONGODB_DATABASE_NAME from env if not provided.
        """
        if self._client is None:
            connection_uri = uri or MONGODB_URI
            if not connection_uri:
                raise ValueError("MongoDB URI not provided and MONGODB_URI not set")

            db_name = database_name or MONGODB_DATABASE_NAME
            if not db_name:
                raise ValueError("Database name not provided and MONGODB_DATABASE_NAME not set")

            # Ensure connection string has required parameters for Atlas
            # mongodb+srv:// automatically uses TLS/SSL
            if "mongodb+srv://" in connection_uri:
                # Add retryWrites and w=majority if not present
                if "retryWrites" not in connection_uri:
                    separator = "&" if "?" in connection_uri else "?"
                    connection_uri = f"{connection_uri}{separator}retryWrites=true&w=majority"
            
            # Configure MongoDB client with connection options
            # Use certifi for SSL certificate validation (helps on macOS)
            self._client = MongoClient(
                connection_uri,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
            )
            self._database = self._client[db_name]

    def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None

    @property
    def client(self) -> MongoClient:
        """Get MongoDB client instance."""
        if self._client is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._client

    @property
    def database(self) -> Database:
        """Get database instance."""
        if self._database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._database

    def get_collection(self, name: str):
        """
        Get a collection by name.

        Args:
            name: Collection name

        Returns:
            MongoDB collection
        """
        return self.database[name]


@lru_cache
def get_database_manager() -> DatabaseManager:
    """
    Get singleton DatabaseManager instance.
    Cached for dependency injection.

    Returns:
        DatabaseManager instance
    """
    return DatabaseManager()


def get_database() -> Database:
    """
    Get database instance for dependency injection.

    Returns:
        MongoDB database instance
    """
    manager = get_database_manager()
    return manager.database
