"""
Test script to verify dependencies are being tracked as Package records.
"""
from database import get_database, get_database_manager
from repositories.package import PackageRepository

def main():
    # Connect to database
    db_manager = get_database_manager()
    db_manager.connect()

    db = get_database()
    repo = PackageRepository(db)

    # Get all packages
    all_packages = repo.find_many({})

    print(f"\n{'='*60}")
    print("PACKAGE INVENTORY")
    print(f"{'='*60}\n")
    print(f"Total packages tracked: {len(all_packages)}\n")

    for pkg in all_packages:
        status_symbols = []
        if pkg.scan_state.deps_crawled:
            status_symbols.append("✓ Deps")
        if pkg.scan_state.maintainers_crawled:
            status_symbols.append("✓ Maintainers")
        if pkg.scan_state.releases_crawled:
            status_symbols.append("✓ Releases")

        status = " | ".join(status_symbols) if status_symbols else "No scans"

        print(f"📦 {pkg.name}")
        print(f"   Registry: {pkg.registry}")
        print(f"   Status: {status}")
        print(f"   Risk Score: {pkg.risk_score}")
        print()

    # Check for dependencies in dependency_trees
    dep_trees = list(db.dependency_trees.find({}, {"_id": 0, "name": 1, "version": 1}))
    print(f"\n{'='*60}")
    print("DEPENDENCY TREES")
    print(f"{'='*60}\n")
    print(f"Total dependency trees stored: {len(dep_trees)}\n")

    for tree in dep_trees:
        print(f"  {tree['name']}@{tree['version']}")

    print("\n")

    # Disconnect from database
    db_manager.disconnect()

if __name__ == "__main__":
    main()
