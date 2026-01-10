"""
Backfill Package records for all dependencies in existing dependency trees.
"""
import asyncio
from database import get_database, get_database_manager
from services.npm_client import NpmRegistryClient
from repositories.package import PackageRepository
from services.package_service import get_or_create_package_with_enrichment

async def main():
    # Connect to database
    db_manager = get_database_manager()
    db_manager.connect()

    db = get_database()
    package_repo = PackageRepository(db)
    npm_client = NpmRegistryClient()

    # Get all dependency trees
    dep_trees = list(db.dependency_trees.find({}))

    print(f"\n{'='*60}")
    print(f"BACKFILLING PACKAGE RECORDS FROM DEPENDENCY TREES")
    print(f"{'='*60}\n")
    print(f"Found {len(dep_trees)} dependency trees to process\n")

    # Collect all unique package names from all trees
    all_dep_names = set()

    for tree in dep_trees:
        print(f"Processing tree: {tree.get('name')}@{tree.get('version')}")

        # Extract all dependency names
        for dep_type in ['dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies']:
            deps = tree.get(dep_type, {})
            for dep_name in deps.keys():
                all_dep_names.add(dep_name)

    print(f"\n✓ Found {len(all_dep_names)} unique dependencies across all trees\n")

    # Process each unique dependency
    created_count = 0
    skipped_count = 0
    error_count = 0

    for dep_name in sorted(all_dep_names):
        # Check if package already exists
        existing = package_repo.find_by_name(dep_name)
        if existing:
            print(f"⊘ {dep_name} - Already exists")
            skipped_count += 1
            continue

        # Create package with enrichment
        try:
            print(f"→ Creating package for {dep_name}...")
            pkg = await get_or_create_package_with_enrichment(
                package_name=dep_name,
                npm_client=npm_client,
                repo=package_repo,
            )

            if pkg:
                print(f"✓ {dep_name} - Created with maintainers")
                created_count += 1
            else:
                print(f"✗ {dep_name} - Not found on npm")
                error_count += 1
        except Exception as e:
            print(f"✗ {dep_name} - Error: {e}")
            error_count += 1

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}\n")
    print(f"Total dependencies: {len(all_dep_names)}")
    print(f"Created: {created_count}")
    print(f"Skipped (already exist): {skipped_count}")
    print(f"Errors: {error_count}")

    # Disconnect from database
    db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
