"""
Check if tenant-mq dependencies exist as Package records with maintainers.
"""
from database import get_database, get_database_manager
from repositories.package import PackageRepository

def main():
    # Connect to database
    db_manager = get_database_manager()
    db_manager.connect()

    db = get_database()
    package_repo = PackageRepository(db)

    # Get tenant-mq dependency tree
    dep_tree = db.dependency_trees.find_one({"name": "tenant-mq"})

    if not dep_tree:
        print("❌ No dependency tree found for tenant-mq")
        return

    deps = dep_tree.get('dependencies', {})
    peer_deps = dep_tree.get('peerDependencies', {})

    all_deps = list(deps.keys()) + list(peer_deps.keys())

    print(f"\n{'='*60}")
    print(f"CHECKING DEPENDENCIES AS PACKAGE RECORDS")
    print(f"{'='*60}\n")
    print(f"Total dependencies to check: {len(all_deps)}\n")

    found_count = 0
    with_maintainers = 0

    for dep_name in all_deps:
        pkg = package_repo.find_by_name(dep_name)

        if pkg:
            found_count += 1
            status = "✓"
            maintainer_status = "✓ Maintainers" if pkg.scan_state.maintainers_crawled else "✗ No maintainers"
            if pkg.scan_state.maintainers_crawled:
                with_maintainers += 1

            # Get maintainer count
            if pkg.id and pkg.scan_state.maintainers_crawled:
                releases = list(db.package_releases.find({"package_id": pkg.id}))
                identity_ids = set()
                for release in releases:
                    if release.get('published_by'):
                        identity_ids.add(release['published_by'])

                maintainer_count = len(identity_ids)
                print(f"{status} {dep_name}")
                print(f"   Risk: {pkg.risk_score} | {maintainer_status} ({maintainer_count} maintainers)")
            else:
                print(f"{status} {dep_name}")
                print(f"   Risk: {pkg.risk_score} | {maintainer_status}")
        else:
            print(f"✗ {dep_name}")
            print(f"   NOT FOUND in packages collection")

        print()

    print(f"{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}\n")
    print(f"Dependencies tracked as packages: {found_count}/{len(all_deps)}")
    print(f"With maintainers crawled: {with_maintainers}/{len(all_deps)}")

    # Disconnect from database
    db_manager.disconnect()

if __name__ == "__main__":
    main()
