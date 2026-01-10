"""
Check tenant-mq details in the database.
"""
from database import get_database, get_database_manager
from repositories.package import PackageRepository
from repositories.identity import IdentityRepository

def main():
    # Connect to database
    db_manager = get_database_manager()
    db_manager.connect()

    db = get_database()
    package_repo = PackageRepository(db)
    identity_repo = IdentityRepository(db)

    # Get tenant-mq package
    pkg = package_repo.find_by_name("tenant-mq")

    if not pkg:
        print("❌ tenant-mq not found in database")
        return

    print(f"\n{'='*60}")
    print(f"PACKAGE: {pkg.name}")
    print(f"{'='*60}\n")

    print(f"Registry: {pkg.registry}")
    print(f"Repo URL: {pkg.repo_url}")
    print(f"Owner: {pkg.owner}")
    print(f"Risk Score: {pkg.risk_score}")
    print(f"\nScan State:")
    print(f"  - Dependencies Crawled: {pkg.scan_state.deps_crawled}")
    print(f"  - Releases Crawled: {pkg.scan_state.releases_crawled}")
    print(f"  - Maintainers Crawled: {pkg.scan_state.maintainers_crawled}")
    print(f"  - Crawl Depth: {pkg.scan_state.crawl_depth}")

    # Check for dependency tree
    dep_tree = db.dependency_trees.find_one({"name": "tenant-mq"})
    if dep_tree:
        print(f"\n✓ Dependency tree exists for version {dep_tree.get('version')}")

        # Count dependencies
        deps = dep_tree.get('dependencies', {})
        dev_deps = dep_tree.get('devDependencies', {})
        opt_deps = dep_tree.get('optionalDependencies', {})
        peer_deps = dep_tree.get('peerDependencies', {})

        print(f"  - Production dependencies: {len(deps)}")
        print(f"  - Dev dependencies: {len(dev_deps)}")
        print(f"  - Optional dependencies: {len(opt_deps)}")
        print(f"  - Peer dependencies: {len(peer_deps)}")

        # List production dependencies
        if deps:
            print(f"\n  Production Dependencies:")
            for dep_name, dep_info in deps.items():
                print(f"    • {dep_name}@{dep_info.get('resolved_version')} ({dep_info.get('spec')})")
    else:
        print("\n✗ No dependency tree found")

    # Check for maintainers
    if pkg.id:
        # Find releases for this package
        releases = list(db.package_releases.find({"package_id": pkg.id}))
        print(f"\n{'='*60}")
        print(f"RELEASES: {len(releases)} found")
        print(f"{'='*60}\n")

        if releases:
            for release in releases[:5]:  # Show first 5
                pub_by = release.get('published_by')
                if pub_by:
                    identity = identity_repo.find_by_id(str(pub_by))
                    pub_name = identity.handle if identity else "Unknown"
                else:
                    pub_name = "Unknown"

                print(f"  v{release.get('version')} - Published by: {pub_name} - Risk: {release.get('risk_score', 0)}")

        # Get all unique identities who published releases
        identity_ids = set()
        for release in releases:
            if release.get('published_by'):
                identity_ids.add(release['published_by'])

        print(f"\n{'='*60}")
        print(f"MAINTAINERS: {len(identity_ids)} unique publishers")
        print(f"{'='*60}\n")

        for identity_id in identity_ids:
            identity = identity_repo.find_by_id(str(identity_id))
            if identity:
                print(f"  • {identity.handle} ({identity.kind})")
                print(f"    - Risk Score: {identity.risk_score}")
                print(f"    - Affiliation: {identity.affiliation_tag}")
                if identity.email_domain:
                    print(f"    - Email Domain: {identity.email_domain}")
                print(f"    - Summary: {identity.analysis.summary}")
                print()

    # Disconnect from database
    db_manager.disconnect()

if __name__ == "__main__":
    main()
