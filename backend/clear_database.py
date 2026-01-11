"""
Clear all data from MongoDB database.

WARNING: This will delete ALL data from the database.
Use with caution!
"""

from database import DatabaseManager
from env import MONGODB_URI, MONGODB_DATABASE_NAME


def clear_database():
    """Clear all collections in the database."""

    # Collection names from repositories
    collections = [
        "packages",
        "package_releases",
        "github_events",
        "identities",
        "package_identities",
        "risk_alerts",
        "dependencies",
        "package_deltas",
    ]

    print(f"Connecting to MongoDB...")
    print(f"Database: {MONGODB_DATABASE_NAME}")

    # Connect to database
    db_manager = DatabaseManager()
    db_manager.connect(MONGODB_URI, MONGODB_DATABASE_NAME)
    db = db_manager.database

    print("\nClearing all collections...")
    print("=" * 50)

    total_deleted = 0

    for collection_name in collections:
        collection = db[collection_name]
        count = collection.count_documents({})

        if count > 0:
            result = collection.delete_many({})
            deleted = result.deleted_count
            total_deleted += deleted
            print(f"✓ {collection_name}: deleted {deleted} documents")
        else:
            print(f"○ {collection_name}: already empty")

    print("=" * 50)
    print(f"\nTotal documents deleted: {total_deleted}")
    print("\nDatabase cleared successfully!")

    # Disconnect
    db_manager.disconnect()


if __name__ == "__main__":
    # Confirm before proceeding
    print("⚠️  WARNING: This will delete ALL data from the database!")
    print(f"Database: {MONGODB_DATABASE_NAME}")
    response = input("\nAre you sure you want to continue? (yes/no): ")

    if response.lower() == "yes":
        clear_database()
    else:
        print("Operation cancelled.")
