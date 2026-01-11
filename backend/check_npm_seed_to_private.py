"""
Check seed-to-private package on npm registry.
"""
import asyncio
from services.npm_client import NpmRegistryClient
from services.priority_resource_manager import Priority
from datetime import datetime, timedelta, timezone

async def main():
    npm_client = NpmRegistryClient()

    package_name = "seed-to-private"

    print(f"\n{'='*80}")
    print(f"CHECKING NPM REGISTRY: {package_name}")
    print(f"{'='*80}\n")

    # Get package metadata
    metadata = await npm_client.get_package_metadata(package_name, Priority.HIGH)

    if not metadata:
        print(f"❌ Package not found on npm registry")
        return

    print(f"📦 PACKAGE METADATA:")
    print(f"   Name: {metadata.name}")
    print(f"   Repository URL: {metadata.repository_url}")
    print(f"   Maintainers: {metadata.maintainers}")
    print(f"   Total Versions: {len(metadata.versions)}")

    # Get dist-tags
    if metadata.versions:
        first_version = next(iter(metadata.versions.values()))
        print(f"   Dist Tags: {first_version.dist_tags}")

    print(f"\n📋 ALL VERSIONS:")
    for version, version_info in sorted(metadata.versions.items()):
        print(f"   {version}:")
        print(f"      Published: {version_info.publish_time}")
        print(f"      Maintainer: {version_info.maintainer}")
        print(f"      Tarball: {version_info.tarball_url}")

    # Check for recent versions (last 7 days)
    print(f"\n🕐 RECENT VERSIONS (last 7 days):")
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_versions = await npm_client.get_recent_versions(package_name, cutoff, Priority.HIGH)

    if recent_versions:
        print(f"Found {len(recent_versions)} recent versions:")
        for v in recent_versions:
            print(f"   {v.version} - Published: {v.publish_time} by {v.maintainer}")
    else:
        print(f"   No versions published in the last 7 days")

    print(f"\n{'='*80}")

if __name__ == "__main__":
    asyncio.run(main())
