"""
Test script to trigger dependency fetch and verify Package creation.
"""
import asyncio
from database import get_database, get_database_manager
from repositories.package import PackageRepository
from api.deps.service import _fetch_npm_deps_internal

async def main():
    # Connect to database
    db_manager = get_database_manager()
    db_manager.connect()

    db = get_database()
    repo = PackageRepository(db)

    # Get count before
    packages_before = len(repo.find_many({}))
    print(f"Packages before: {packages_before}\n")

    # Trigger dependency fetch for axios (depth=2 to ensure deps are fetched)
    print("Fetching dependencies for axios (depth=2 for production deps only)...")
    result = await _fetch_npm_deps_internal(
        package="axios",
        version="1.7.9",
        depth=2,
    )

    print(f"\n✓ Dependency fetch complete")
    print(f"✓ Fetched {len(result.get('dependencies', {}))} production dependencies")

    # Get count after
    packages_after = len(repo.find_many({}))
    print(f"\nPackages after: {packages_after}")
    print(f"New packages created: {packages_after - packages_before}")

    if packages_after > packages_before:
        print("\n✓ SUCCESS: Dependencies were automatically tracked as Package records!")

        # Show the new packages
        all_packages = repo.find_many({})
        print("\nAll tracked packages:")
        for pkg in all_packages:
            status = "✓ Maintainers" if pkg.scan_state.maintainers_crawled else ""
            print(f"  - {pkg.name} {status}")
    else:
        print("\n✗ No new packages were created from dependencies")

    # Disconnect from database
    db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
