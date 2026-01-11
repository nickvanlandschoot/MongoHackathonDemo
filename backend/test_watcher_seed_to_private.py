"""
Test the updated watcher on seed-to-private package.
"""
import asyncio
from database import get_database, get_database_manager
from services.watcher import WatcherService
from repositories.package import PackageRepository

async def main():
    # Connect to database
    db_manager = get_database_manager()
    db_manager.connect()

    db = get_database()
    package_repo = PackageRepository(db)
    watcher = WatcherService(db)

    package_name = "seed-to-private"

    print(f"\n{'='*80}")
    print(f"TESTING WATCHER ON: {package_name}")
    print(f"{'='*80}\n")

    # Get the package
    package = await package_repo.find_by_name(package_name)
    if not package:
        print(f"❌ Package '{package_name}' not found in database")
        db_manager.disconnect()
        return

    print(f"Found package: {package.name} (ID: {package.id})")
    print(f"Current scan state:")
    print(f"   - Deps Crawled: {package.scan_state.deps_crawled}")
    print(f"   - Releases Crawled: {package.scan_state.releases_crawled}")
    print(f"   - Maintainers Crawled: {package.scan_state.maintainers_crawled}")

    print(f"\n{'='*80}")
    print(f"RUNNING WATCHER._poll_package()...")
    print(f"{'='*80}\n")

    # Run the watcher on this specific package
    result = await watcher._poll_package(package)

    print(f"\n{'='*80}")
    print(f"WATCHER RESULTS:")
    print(f"{'='*80}\n")
    print(f"   Releases Created: {result.get('releases', 0)}")
    print(f"   Alerts Created: {result.get('alerts', 0)}")

    # Check what got created
    print(f"\n{'='*80}")
    print(f"VERIFYING DATABASE...")
    print(f"{'='*80}\n")

    from repositories.package_release import PackageReleaseRepository
    from repositories.risk_alert import RiskAlertRepository

    release_repo = PackageReleaseRepository(db)
    alert_repo = RiskAlertRepository(db)

    releases = await release_repo.find_by_package(package.id, limit=10)
    print(f"Releases in database: {len(releases)}")
    for release in releases:
        print(f"   - {release.version} (Published: {release.publish_timestamp}, Risk: {release.risk_score})")

    alerts = await alert_repo.find_by_package(package.id, limit=10)
    print(f"\nAlerts in database: {len(alerts)}")
    for alert in alerts:
        print(f"   - {alert.reason} (Severity: {alert.severity}, Status: {alert.status})")

    print(f"\n{'='*80}")
    print(f"TEST COMPLETE")
    print(f"{'='*80}\n")

    # Disconnect from database
    db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
