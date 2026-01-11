"""
One-time script to crawl maintainers for existing packages.
"""
import asyncio
from database import get_database, get_database_manager
from services.npm_client import NpmRegistryClient
from repositories.package import PackageRepository
from services.package_service import crawl_package_maintainers

async def main():
    # Connect to database
    db_manager = get_database_manager()
    db_manager.connect()

    db = get_database()
    repo = PackageRepository(db)
    npm_client = NpmRegistryClient()

    # Find all packages without maintainers crawled
    packages = await repo.find_many({"scan_state.maintainers_crawled": False})

    print(f"Found {len(packages)} packages needing maintainer crawl")

    for pkg in packages:
        print(f"\nCrawling maintainers for {pkg.name}...")
        count = await crawl_package_maintainers(pkg.name, npm_client, repo)
        print(f"✓ Processed {count} maintainers")

    print("\nDone!")

    # Disconnect from database
    db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
