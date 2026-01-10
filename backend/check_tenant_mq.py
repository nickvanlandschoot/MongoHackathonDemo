"""
Check the database for tenant-mq package and its dependencies.
"""

from database import DatabaseManager


def check_tenant_mq():
    """Check tenant-mq package in database."""
    # Initialize database connection
    db_manager = DatabaseManager()
    db_manager.connect()
    db = db_manager.database

    print("=" * 80)
    print("CHECKING TENANT-MQ PACKAGE")
    print("=" * 80)

    # Check packages collection
    print("\n1. Checking packages collection...")
    pkg = db.packages.find_one({"name": "tenant-mq"})

    if not pkg:
        print("   ❌ Package 'tenant-mq' NOT FOUND in packages collection")
        return

    print(f"   ✓ Package found: {pkg.get('name')}")
    print(f"   - Registry: {pkg.get('registry')}")
    print(f"   - Latest version: {pkg.get('latest_release_version')}")
    print(f"   - Risk score: {pkg.get('risk_score')}")

    scan_state = pkg.get('scan_state', {})
    print(f"\n   Scan State:")
    print(f"   - deps_crawled: {scan_state.get('deps_crawled', False)}")
    print(f"   - releases_crawled: {scan_state.get('releases_crawled', False)}")
    print(f"   - maintainers_crawled: {scan_state.get('maintainers_crawled', False)}")
    print(f"   - crawl_depth: {scan_state.get('crawl_depth', 0)}")

    # Check dependency_trees collection
    print("\n2. Checking dependency_trees collection...")
    dep_trees = list(db.dependency_trees.find({"name": "tenant-mq"}))

    if not dep_trees:
        print("   ❌ NO dependency trees found for 'tenant-mq'")
    else:
        print(f"   ✓ Found {len(dep_trees)} dependency tree(s)")
        for i, tree in enumerate(dep_trees):
            print(f"\n   Tree {i + 1}:")
            print(f"   - Version: {tree.get('version')}")
            print(f"   - Fetched at: {tree.get('fetched_at')}")

            deps_count = len(tree.get('dependencies', {}))
            dev_deps_count = len(tree.get('devDependencies', {}))
            opt_deps_count = len(tree.get('optionalDependencies', {}))
            peer_deps_count = len(tree.get('peerDependencies', {}))

            print(f"   - Production dependencies: {deps_count}")
            print(f"   - Dev dependencies: {dev_deps_count}")
            print(f"   - Optional dependencies: {opt_deps_count}")
            print(f"   - Peer dependencies: {peer_deps_count}")
            print(f"   - Total: {deps_count + dev_deps_count + opt_deps_count + peer_deps_count}")

            if deps_count > 0:
                print(f"\n   Production dependencies:")
                for dep_name, dep_info in list(tree.get('dependencies', {}).items())[:5]:
                    print(f"      • {dep_name} @ {dep_info.get('spec')}")
                if deps_count > 5:
                    print(f"      ... and {deps_count - 5} more")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if pkg and dep_trees:
        if scan_state.get('deps_crawled'):
            print("✓ Package exists AND dependencies are fetched AND flag is set")
            print("  → Dependencies should be visible in the UI")
        else:
            print("⚠️  Package exists AND dependencies are fetched BUT flag is NOT set")
            print("  → Run fix_deps_crawled_flag.py to update the flag")
    elif pkg and not dep_trees:
        print("⚠️  Package exists BUT dependencies are NOT fetched")
        print("  → Run the fetch dependencies API call")
    else:
        print("❌ Package not found in database")


if __name__ == "__main__":
    check_tenant_mq()
