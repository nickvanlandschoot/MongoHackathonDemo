"""
PR Watcher Service - npm registry polling agent.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from pymongo.database import Database

from models.analysis import Analysis
from models.package import Package
from models.package_release import PackageRelease
from models.risk_alert import RiskAlert
from models.identity import Identity
from repositories import (
    PackageRepository,
    PackageReleaseRepository,
    RiskAlertRepository,
    IdentityRepository,
)
from services.npm_client import NpmRegistryClient, NpmVersionInfo
from services.github_client import GitHubApiClient
from services.tarball_analyzer import TarballAnalyzer, TarballAnalysisResult
from services.risk_scorer import RiskScorer


class WatcherService:
    """
    Main watcher service that polls npm registry for new releases.

    Flow per package:
    1. Fetch package metadata from npm
    2. Find versions published in last 7 days
    3. For each new version not in our database:
       a. Identify the publisher (npm maintainer)
       b. Check if maintainer is known (in Identity collection)
       c. Resolve GitHub username from repo URL
       d. Fetch GitHub user info
       e. Download and analyze tarball
       f. Calculate risk score
       g. Create PackageRelease record
       h. If risky, create RiskAlert
    """

    LOOKBACK_DAYS = 7

    def __init__(self, database: Database):
        self.db = database

        # Repositories
        self.package_repo = PackageRepository(database)
        self.release_repo = PackageReleaseRepository(database)
        self.alert_repo = RiskAlertRepository(database)
        self.identity_repo = IdentityRepository(database)

        # Clients and analyzers
        self.npm_client = NpmRegistryClient()
        self.github_client = GitHubApiClient()
        self.tarball_analyzer = TarballAnalyzer()
        self.risk_scorer = RiskScorer()

    async def poll_all_packages(self) -> dict:
        """
        Poll all tracked packages for new releases.

        Returns:
            Summary dict with stats
        """
        print("[watcher] Starting poll cycle for all packages")

        # Get unique package names from dependency_trees collection
        dependency_trees = self.db.dependency_trees.find({}, {"name": 1})
        unique_packages = set()
        for doc in dependency_trees:
            if "name" in doc:
                unique_packages.add(doc["name"])

        if not unique_packages:
            print("[watcher] No packages to poll from dependency_trees")
            return {"packages_checked": 0, "new_releases": 0, "alerts_created": 0}

        print(f"[watcher] Found {len(unique_packages)} unique packages in dependency_trees")

        # Get or create Package records for each
        packages = []
        for pkg_name in unique_packages:
            pkg = self.package_repo.find_by_name(pkg_name)
            if not pkg:
                # Create Package record for this dependency
                pkg = Package(
                    name=pkg_name,
                    registry="npm",
                    analysis=Analysis(
                        summary=f"Package discovered from dependency scan",
                        reasons=["Auto-discovered from dependency tree"],
                        confidence=1.0,
                        source="rule",
                    ),
                )
                pkg = self.package_repo.create(pkg)
                print(f"[watcher] Created Package record for {pkg_name}")
            packages.append(pkg)

        if not packages:
            print("[watcher] No packages to poll")
            return {"packages_checked": 0, "new_releases": 0, "alerts_created": 0}

        # Process packages concurrently (with rate limiting)
        results = await asyncio.gather(
            *[self._poll_package(pkg) for pkg in packages],
            return_exceptions=True,
        )

        # Aggregate results
        total_releases = 0
        total_alerts = 0
        errors = 0

        for result in results:
            if isinstance(result, Exception):
                errors += 1
                print(f"[watcher] ERROR: Error polling package: {result}")
            elif result:
                total_releases += result.get("releases", 0)
                total_alerts += result.get("alerts", 0)

        summary = {
            "packages_checked": len(packages),
            "new_releases": total_releases,
            "alerts_created": total_alerts,
            "errors": errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        print(f"[watcher] Poll cycle complete: {summary}")
        return summary

    async def _poll_package(self, package: Package) -> dict:
        """
        Poll a single package for new releases.

        Args:
            package: Package to poll

        Returns:
            Dict with counts
        """
        print(f"[watcher] Polling package: {package.name}")

        # Calculate cutoff time
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.LOOKBACK_DAYS)

        # Fetch recent versions from npm
        recent_versions = await asyncio.to_thread(
            self.npm_client.get_recent_versions,
            package.name,
            cutoff,
        )

        if not recent_versions:
            return {"releases": 0, "alerts": 0}

        releases_created = 0
        alerts_created = 0

        for version_info in recent_versions:
            # Check if we already have this release
            existing = self.release_repo.find_by_version(package.id, version_info.version)
            if existing:
                continue

            # Process the new release
            try:
                result = await self._process_release(package, version_info)
                releases_created += 1
                if result.get("alert_created"):
                    alerts_created += 1
            except Exception as e:
                print(
                    f"[watcher] ERROR: Error processing {package.name}@{version_info.version}: {e}"
                )

        return {"releases": releases_created, "alerts": alerts_created}

    async def _process_release(
        self, package: Package, version_info: NpmVersionInfo
    ) -> dict:
        """
        Process a single new release.

        Args:
            package: Parent package
            version_info: Version metadata from npm

        Returns:
            Dict with processing results
        """
        print(f"[watcher] Processing release: {package.name}@{version_info.version}")

        # 1. Resolve maintainer identity
        maintainer_handle = version_info.maintainer
        identity: Optional[Identity] = None
        is_first_time = False

        if maintainer_handle:
            identity = self.identity_repo.find_by_handle(maintainer_handle, kind="npm")
            if not identity:
                is_first_time = True
                # Create new identity
                identity = self._create_identity(maintainer_handle)

        # 2. Resolve GitHub username and fetch info
        github_info = None
        repo_url = version_info.repository_url or package.repo_url
        github_username = GitHubApiClient.parse_github_username_from_repo_url(repo_url)

        if github_username:
            github_info = await asyncio.to_thread(
                self.github_client.get_user, github_username
            )

        # 3. Download and analyze tarball
        tarball_bytes = await asyncio.to_thread(
            self.npm_client.download_tarball, version_info.tarball_url
        )

        if tarball_bytes:
            tarball_analysis = self.tarball_analyzer.analyze(tarball_bytes)
        else:
            tarball_analysis = TarballAnalysisResult(
                files=[],
                suspicious_files=[],
                suspicious_content_matches={},
                package_json=None,
                scripts={},
                risk_indicators=["Failed to download tarball"],
            )

        # 4. Calculate risk score
        risk_assessment = self.risk_scorer.assess_release(
            is_first_time_maintainer=is_first_time,
            github_info=github_info,
            tarball_analysis=tarball_analysis,
            maintainer_handle=maintainer_handle,
        )

        # 5. Create PackageRelease record
        release = PackageRelease(
            package_id=package.id,
            version=version_info.version,
            previous_version=self._get_previous_version(package.id),
            published_by=identity.id if identity else None,
            publish_timestamp=version_info.publish_time,
            tarball_integrity=version_info.integrity,
            dist_tags=version_info.dist_tags,
            risk_score=risk_assessment.score,
            analysis=Analysis(
                summary=self._generate_summary(risk_assessment, is_first_time),
                reasons=risk_assessment.reasons,
                confidence=0.85,
                source="rule",
            ),
        )

        created_release = self.release_repo.create(release)

        # 6. Create alert if needed
        alert_created = False
        if risk_assessment.should_alert:
            alert = RiskAlert(
                package_id=package.id,
                identity_id=identity.id if identity else None,
                release_id=created_release.id,
                reason=risk_assessment.alert_reason or "High risk release detected",
                severity=risk_assessment.severity,
                status="open",
                analysis=Analysis(
                    summary=risk_assessment.alert_reason or "High risk release",
                    reasons=risk_assessment.reasons,
                    confidence=0.85,
                    source="rule",
                ),
            )
            self.alert_repo.create(alert)
            alert_created = True
            print(
                f"[watcher] ALERT: Alert created for {package.name}@{version_info.version}: "
                f"{risk_assessment.alert_reason}"
            )

        # 7. Update package last_scanned
        self.package_repo.update(package.id, {"last_scanned": datetime.now(timezone.utc)})

        return {"alert_created": alert_created}

    def _create_identity(self, npm_handle: str) -> Identity:
        """Create a new Identity for a first-time maintainer."""
        identity = Identity(
            kind="npm",
            handle=npm_handle,
            affiliation_tag="unknown",
            first_seen=datetime.now(timezone.utc),
            risk_score=20.0,  # Base risk for unknown identity
            analysis=Analysis(
                summary=f"Newly observed npm maintainer: {npm_handle}",
                reasons=["First time appearing in monitored packages"],
                confidence=1.0,
                source="rule",
            ),
        )
        return self.identity_repo.create(identity)

    def _get_previous_version(self, package_id: ObjectId) -> Optional[str]:
        """Get the most recent version before this one."""
        releases = self.release_repo.find_by_package(package_id, limit=1)
        if releases:
            return releases[0].version
        return None

    def _generate_summary(self, assessment, is_first_time: bool) -> str:
        """Generate human-readable summary for release."""
        if assessment.score >= 70:
            prefix = "High-risk release"
        elif assessment.score >= 40:
            prefix = "Moderate-risk release"
        else:
            prefix = "Low-risk release"

        if is_first_time:
            return f"{prefix} from first-time maintainer"

        return f"{prefix} - {len(assessment.reasons)} risk factors identified"
