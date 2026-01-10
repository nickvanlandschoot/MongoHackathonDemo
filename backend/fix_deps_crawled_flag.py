"""
One-time script to fix deps_crawled flag for packages that have dependency trees.

Run this script to update the scan_state.deps_crawled flag for packages
that already have dependency trees in the database but the flag wasn't set.
"""

from database import get_database


def fix_deps_crawled_flags():
    """Update deps_crawled flag for packages with existing dependency trees."""
    db = get_database()

    # Get all packages
    packages = list(db.packages.find({}))
    print(f"Found {len(packages)} packages")

    updated_count = 0

    for pkg in packages:
        package_name = pkg.get("name")

        # Check if dependency tree exists for this package
        dep_tree = db.dependency_trees.find_one({"name": package_name})

        if dep_tree and not pkg.get("scan_state", {}).get("deps_crawled", False):
            # Dependency tree exists but flag is not set
            print(f"Updating {package_name}...")
            db.packages.update_one(
                {"name": package_name},
                {
                    "$set": {
                        "scan_state.deps_crawled": True,
                    }
                }
            )
            updated_count += 1
            print(f"  ✓ Updated {package_name}")

    print(f"\nUpdated {updated_count} packages")


if __name__ == "__main__":
    fix_deps_crawled_flags()
