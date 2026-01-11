"""
Investigate seed-to-private package in the database.
"""
import asyncio
from database import get_database, get_database_manager
from repositories.package import PackageRepository
from repositories.package_release import PackageReleaseRepository
from repositories.identity import IdentityRepository
from repositories.risk_alert import RiskAlertRepository
from repositories.package_delta import PackageDeltaRepository
from bson import ObjectId

async def main():
    # Connect to database
    db_manager = get_database_manager()
    db_manager.connect()

    db = get_database()
    package_repo = PackageRepository(db)
    release_repo = PackageReleaseRepository(db)
    identity_repo = IdentityRepository(db)
    alert_repo = RiskAlertRepository(db)
    delta_repo = PackageDeltaRepository(db)

    package_name = "seed-to-private"

    print(f"\n{'='*80}")
    print(f"INVESTIGATING PACKAGE: {package_name}")
    print(f"{'='*80}\n")

    # 1. Find the package
    package = await package_repo.find_by_name(package_name)
    if not package:
        print(f"❌ Package '{package_name}' not found in database")
        db_manager.disconnect()
        return

    print(f"📦 PACKAGE INFORMATION:")
    print(f"   ID: {package.id}")
    print(f"   Name: {package.name}")
    print(f"   Registry: {package.registry}")
    print(f"   Repo URL: {package.repo_url}")
    print(f"   Owner: {package.owner}")
    print(f"   Risk Score: {package.risk_score}")
    print(f"   Last Scanned: {package.last_scanned}")
    print(f"   Scan State:")
    print(f"      - Deps Crawled: {package.scan_state.deps_crawled}")
    print(f"      - Releases Crawled: {package.scan_state.releases_crawled}")
    print(f"      - Maintainers Crawled: {package.scan_state.maintainers_crawled}")
    if package.analysis:
        print(f"   Analysis: {package.analysis.summary}")
        print(f"   Reasons: {package.analysis.reasons}")

    # 2. Find all releases
    print(f"\n{'='*80}")
    print(f"📋 RELEASES:")
    print(f"{'='*80}\n")

    releases = await release_repo.find_by_package(package.id, limit=100)
    print(f"Found {len(releases)} releases\n")

    for release in releases:
        print(f"   Version: {release.version}")
        print(f"      Published: {release.publish_timestamp}")
        print(f"      Published By: {release.published_by}")
        print(f"      Previous Version: {release.previous_version}")
        print(f"      Risk Score: {release.risk_score}")
        print(f"      Dist Tags: {release.dist_tags}")
        if release.analysis:
            print(f"      Analysis: {release.analysis.summary}")
            print(f"      Reasons: {release.analysis.reasons[:3]}")  # First 3 reasons
        print()

    # 3. Find all maintainers/identities
    print(f"\n{'='*80}")
    print(f"👤 IDENTITIES (MAINTAINERS/PUBLISHERS):")
    print(f"{'='*80}\n")

    identity_ids = set()
    for release in releases:
        if release.published_by:
            identity_ids.add(release.published_by)

    print(f"Found {len(identity_ids)} unique identities\n")

    for identity_id in identity_ids:
        identity = await identity_repo.find_by_id(identity_id)
        if identity:
            print(f"   Handle: {identity.handle} ({identity.kind})")
            print(f"      ID: {identity.id}")
            print(f"      Affiliation: {identity.affiliation_tag}")
            print(f"      Email Domain: {identity.email_domain}")
            print(f"      Country: {identity.country}")
            print(f"      Risk Score: {identity.risk_score}")
            print(f"      First Seen: {identity.first_seen}")
            if identity.analysis:
                print(f"      Analysis: {identity.analysis.summary}")
            print()

    # 4. Find all risk alerts
    print(f"\n{'='*80}")
    print(f"⚠️  RISK ALERTS:")
    print(f"{'='*80}\n")

    alerts = await alert_repo.find_by_package(package.id, limit=100)
    print(f"Found {len(alerts)} alerts\n")

    for alert in alerts:
        print(f"   Alert ID: {alert.id}")
        print(f"      Status: {alert.status}")
        print(f"      Severity: {alert.severity}")
        print(f"      Reason: {alert.reason}")
        print(f"      Timestamp: {alert.timestamp}")
        print(f"      Release ID: {alert.release_id}")
        print(f"      Delta ID: {alert.delta_id}")
        print(f"      Identity ID: {alert.identity_id}")
        if alert.analysis:
            print(f"      Analysis: {alert.analysis.summary}")
        print()

    # 5. Find all deltas
    print(f"\n{'='*80}")
    print(f"📊 VERSION DELTAS:")
    print(f"{'='*80}\n")

    deltas = await delta_repo.find_by_package(package.id, limit=100)
    print(f"Found {len(deltas)} deltas\n")

    for delta in deltas:
        print(f"   {delta.from_version} → {delta.to_version}")
        print(f"      Delta ID: {delta.id}")
        print(f"      Risk Score: {delta.risk_score}")
        print(f"      Computed At: {delta.computed_at}")
        print(f"      Files Added: {delta.files_added}")
        print(f"      Files Removed: {delta.files_removed}")
        print(f"      Files Modified: {delta.files_modified}")
        if delta.signals:
            print(f"      Signals:")
            print(f"         - Touched Install Scripts: {delta.signals.touched_install_scripts}")
            print(f"         - Added Network Calls: {delta.signals.added_network_calls}")
            print(f"         - Added Binaries: {delta.signals.added_binaries}")
            print(f"         - Obfuscated: {delta.signals.minified_or_obfuscated_delta}")
        if delta.analysis:
            print(f"      Analysis: {delta.analysis.summary}")
        print()

    # 6. Check raw collections for any other data
    print(f"\n{'='*80}")
    print(f"🔍 RAW COLLECTION CHECKS:")
    print(f"{'='*80}\n")

    # Check dependency trees
    dep_trees = list(db.dependency_trees.find({"name": package_name}))
    print(f"Dependency Trees: {len(dep_trees)}")
    if dep_trees:
        for tree in dep_trees[:3]:  # First 3
            print(f"   - Version: {tree.get('version')}, Dependencies: {len(tree.get('dependencies', {}))}")

    # Check dependencies collection
    deps = list(db.dependencies.find({"package_name": package_name}))
    print(f"Dependencies Records: {len(deps)}")
    if deps:
        for dep in deps[:3]:  # First 3
            print(f"   - Parent: {dep.get('parent_package')}, Version: {dep.get('version')}")

    print(f"\n{'='*80}")
    print(f"INVESTIGATION COMPLETE")
    print(f"{'='*80}\n")

    # Disconnect from database
    db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
