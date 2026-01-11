"""
PR Watcher Service - npm registry polling agent.
"""

import asyncio
from datetime import datetime, timezone
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
from repositories.package_threat_assessment import PackageThreatAssessmentRepository
from services.npm_client import NpmRegistryClient, NpmVersionInfo
from services.github_client import GitHubApiClient
from services.tarball_extractor import TarballExtractor, TarballContent
from services.risk_scorer import RiskScorer
from services.delta_service import DeltaService
from services.package_service import get_or_create_package_with_enrichment, crawl_package_maintainers
from services.ai_alert_service import AIAlertService
from services.ai_threat_surface_service import AIThreatSurfaceService
from services.ai_analysis_queue import AIAnalysisQueue
from services.package_risk_aggregator import PackageRiskAggregator
from env import OPENROUTER_API_KEY, AI_ANALYSIS_DELAY, AI_PRIORITY_THRESHOLD


class WatcherService:
    """
    Main watcher service that polls npm registry for new releases.

    Flow per package:
    1. Fetch package metadata from npm
    2. Find the N most recent versions (max 5 by default)
    3. For each new version not in our database:
       a. Identify the publisher (npm maintainer)
       b. Check if maintainer is known (in Identity collection)
       c. Resolve GitHub username from repo URL
       d. Fetch GitHub user info
       e. Download and analyze tarball
       f. Calculate risk score
       g. Create PackageRelease record
       h. Queue AI analysis (rate-limited, high-risk releases prioritized)
       i. Compute deltas between consecutive versions
       j. If risky, create rule-based RiskAlerts
    4. Update package scan status

    AI Analysis Queue:
    - High-risk releases (>= threshold) are analyzed immediately
    - Low-risk releases are queued and processed with delays
    - Prevents API rate limits and reduces costs
    """

    MAX_RELEASES_TO_TRACK = 5
    MAX_CONCURRENT_PACKAGES = 8  # Limit concurrent package polls to fit in 30s window

    def __init__(self, database: Database):
        self.db = database

        # Repositories
        self.package_repo = PackageRepository(database)
        self.release_repo = PackageReleaseRepository(database)
        self.alert_repo = RiskAlertRepository(database)
        self.identity_repo = IdentityRepository(database)
        self.threat_surface_repo = PackageThreatAssessmentRepository(database)

        # Clients and analyzers
        self.npm_client = NpmRegistryClient()
        self.github_client = GitHubApiClient()
        self.tarball_extractor = TarballExtractor()
        self.risk_scorer = RiskScorer()
        self.delta_service = DeltaService(database)
        self.risk_aggregator = PackageRiskAggregator(database)

        # AI analysis queue (only initialize if API key is available)
        if OPENROUTER_API_KEY:
            ai_alert_service = AIAlertService(database, OPENROUTER_API_KEY)
            ai_threat_surface_service = AIThreatSurfaceService(database, OPENROUTER_API_KEY)
            self.ai_queue = AIAnalysisQueue(
                database=database,
                ai_alert_service=ai_alert_service,
                ai_threat_surface_service=ai_threat_surface_service,
                delay_between_calls=AI_ANALYSIS_DELAY,
                high_priority_threshold=AI_PRIORITY_THRESHOLD,
            )
            self.ai_queue.start_worker()
            print(f"[watcher] AI analysis queue initialized (delay: {AI_ANALYSIS_DELAY}s, priority threshold: {AI_PRIORITY_THRESHOLD})")
        else:
            self.ai_queue = None
            print("[watcher] WARNING: AI services disabled - OPENROUTER_API_KEY not found")

        # Concurrency control for background polling
        self._package_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_PACKAGES)

    async def poll_all_packages(self) -> dict:
        """
        Poll all tracked packages for new releases.

        Returns:
            Summary dict with stats
        """
        print("[watcher] Starting poll cycle for all packages")

        # Get all packages from packages collection
        all_packages = await self.package_repo.find_many({})

        if not all_packages:
            print("[watcher] No packages to poll")
            return {"packages_checked": 0, "new_releases": 0, "alerts_created": 0}

        print(f"[watcher] Found {len(all_packages)} packages to poll")

        # Enrich any packages missing metadata (from old dependency_trees flow)
        packages = []
        for pkg in all_packages:
            # If package has no repo_url, try to enrich it
            if not pkg.repo_url:
                print(f"[watcher] Enriching package metadata for {pkg.name}")
                enriched = await get_or_create_package_with_enrichment(
                    package_name=pkg.name,
                    npm_client=self.npm_client,
                    repo=self.package_repo,
                )
                if enriched:
                    pkg = enriched

            packages.append(pkg)

        if not packages:
            print("[watcher] No packages to poll")
            return {"packages_checked": 0, "new_releases": 0, "alerts_created": 0}

        # Process packages with controlled concurrency (max 8 concurrent)
        results = await asyncio.gather(
            *[self._poll_package_limited(pkg) for pkg in packages],
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

    async def process_package(self, package: Package) -> dict:
        """
        Process a single package immediately (for newly added packages).

        Args:
            package: Package to process

        Returns:
            Processing results with counts of releases and alerts created
        """
        return await self._poll_package(package)

    async def _poll_package_limited(self, package: Package) -> dict:
        """
        Poll package with concurrency control.

        This wrapper ensures that only MAX_CONCURRENT_PACKAGES packages
        are processed simultaneously, preventing resource exhaustion.

        Args:
            package: Package to poll

        Returns:
            Dict with counts of releases and alerts created
        """
        async with self._package_semaphore:
            return await self._poll_package(package)

    async def _poll_package(self, package: Package) -> dict:
        """
        Poll a single package for new releases.

        Args:
            package: Package to poll

        Returns:
            Dict with counts
        """
        print(f"[watcher] Polling package: {package.name}")

        # Fetch the N most recent versions from npm (with LOW priority - background job)
        recent_versions = await self.npm_client.get_latest_versions(
            package.name,
            self.MAX_RELEASES_TO_TRACK,
            # priority defaults to LOW, which is correct for background jobs
        )

        if not recent_versions:
            return {"releases": 0, "alerts": 0}

        releases_created = 0
        alerts_created = 0

        for version_info in recent_versions:
            # Check if we already have this release
            existing = await self.release_repo.find_by_version(package.id, version_info.version)
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

        # If we processed any releases, crawl maintainers to ensure we have the full list
        if releases_created > 0 and not package.scan_state.maintainers_crawled:
            maintainer_count = await crawl_package_maintainers(
                package.name,
                self.npm_client,
                self.package_repo,
            )
            print(f"[watcher] Crawled {maintainer_count} maintainers for {package.name}")

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
        # Ensure package has an ID (required for all operations below)
        if not package.id:
            print(f"[watcher] ERROR: Package has no ID: {package.name}")
            return {"alert_created": False, "delta_created": False, "alert_from_delta": False}

        # After this point, package.id is guaranteed to be non-None
        package_id = package.id  # Type narrowing for clarity

        print(f"[watcher] Processing release: {package.name}@{version_info.version}")

        # 1. Resolve maintainer identity
        maintainer_handle = version_info.maintainer
        identity: Optional[Identity] = None
        is_first_time = False

        if maintainer_handle:
            identity = await self.identity_repo.find_by_handle(maintainer_handle, kind="npm")
            if not identity:
                is_first_time = True
                # Create new identity
                identity = await self._create_identity(maintainer_handle)

        # 2. Resolve GitHub username and fetch info
        github_info = None
        repo_url = version_info.repository_url or package.repo_url
        github_username = GitHubApiClient.parse_github_username_from_repo_url(repo_url)

        if github_username:
            github_info = await asyncio.to_thread(
                self.github_client.get_user, github_username
            )

        # 3. Download and analyze tarball (with LOW priority - background job)
        tarball_bytes = await self.npm_client.download_tarball(
            version_info.tarball_url
            # priority defaults to LOW, which is correct for background jobs
        )

        if tarball_bytes:
            tarball_analysis = await asyncio.to_thread(
                self.tarball_extractor.extract, tarball_bytes
            )
        else:
            tarball_analysis = TarballContent(
                files=[],
                package_json=None,
                scripts={},
            )

        # 4. Calculate risk score
        risk_assessment = self.risk_scorer.assess_release(
            is_first_time_maintainer=is_first_time,
            github_info=github_info,
            tarball_analysis=tarball_analysis,
            maintainer_handle=maintainer_handle,
        )

        # 5. Create PackageRelease record
        previous_version = await self._get_previous_version(package_id)
        release = PackageRelease(
            package_id=package_id,
            version=version_info.version,
            previous_version=previous_version,
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

        created_release = await self.release_repo.create(release)

        # 6. Queue AI analysis (with rate limiting and prioritization)
        if self.ai_queue:
            self.ai_queue.queue_analysis(
                package=package,
                package_id=package_id,
                release=created_release,
                identity=identity,
                github_info=github_info,
                tarball_analysis=tarball_analysis,
                delta=None,  # Delta not computed yet
            )

        # 7. Compute delta if there's a previous version
        delta_created = False
        alert_from_delta = False
        delta = None

        if created_release.previous_version:
            try:
                delta = await self.delta_service.compute_delta(
                    package_id,
                    from_version=created_release.previous_version,
                    to_version=created_release.version,
                )
                if delta:
                    delta_created = True
                    print(
                        f"[watcher] Delta computed: {package.name} "
                        f"{delta.from_version} -> {delta.to_version} "
                        f"(risk: {delta.risk_score:.1f})"
                    )

                    # Create alert if high-risk delta (>= 70)
                    if delta.risk_score >= 70 and delta.id:
                        alert = RiskAlert(
                            package_id=package_id,
                            identity_id=identity.id if identity else None,
                            release_id=created_release.id,
                            delta_id=delta.id,
                            reason=f"High-risk version delta detected: {delta.analysis.summary}",
                            severity=delta.risk_score,
                            status="open",
                            analysis=delta.analysis,
                        )
                        await self.alert_repo.create(alert)
                        alert_from_delta = True
                        print(f"[watcher] ALERT: High-risk delta alert created")
            except Exception as e:
                print(f"[watcher] ERROR: Failed to compute delta: {e}")

        # 8. Create alert if needed (from release risk assessment)
        alert_created = False
        if risk_assessment.should_alert:
            alert = RiskAlert(
                package_id=package_id,
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
            await self.alert_repo.create(alert)
            alert_created = True
            print(
                f"[watcher] ALERT: Alert created for {package.name}@{version_info.version}: "
                f"{risk_assessment.alert_reason}"
            )

        # 10. Update package last_scanned
        await self.package_repo.update(package_id, {"last_scanned": datetime.now(timezone.utc)})

        # 11. Recalculate aggregate package risk score
        try:
            updated_risk_score = await self.risk_aggregator.update_package_risk_score(package_id)
            print(f"[watcher] Updated package risk score for {package.name}: {updated_risk_score:.1f}")
        except Exception as e:
            print(f"[watcher] WARNING: Failed to update package risk score: {e}")

        return {
            "alert_created": alert_created,
            "delta_created": delta_created,
            "alert_from_delta": alert_from_delta,
        }

    async def _create_identity(self, npm_handle: str) -> Identity:
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
        return await self.identity_repo.create(identity)

    async def _get_previous_version(self, package_id: ObjectId) -> Optional[str]:
        """Get the most recent version before this one."""
        releases = await self.release_repo.find_by_package(package_id, limit=1)
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

