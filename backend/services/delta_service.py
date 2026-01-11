"""
Delta computation service for package version comparison.
"""



import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from bson import ObjectId
from pymongo.database import Database

from models.package_delta import PackageDelta, Signals
from models.analysis import Analysis
from repositories import PackageDeltaRepository, PackageRepository, PackageReleaseRepository
from services.npm_client import NpmRegistryClient
from services.tarball_extractor import TarballExtractor, TarballContent


class DeltaService:
    """Service for computing deltas between package versions."""

    # Native file extensions to detect
    NATIVE_EXTENSIONS = {".node", ".so", ".dylib", ".dll", ".addon"}

    # Install script names
    INSTALL_SCRIPT_NAMES = {"preinstall", "install", "postinstall", "prepare"}

    def __init__(self, database: Database):
        """Initialize delta service with database."""
        self.db = database
        self.delta_repo = PackageDeltaRepository(database)
        self.package_repo = PackageRepository(database)
        self.release_repo = PackageReleaseRepository(database)
        self.npm_client = NpmRegistryClient()
        self.tarball_extractor = TarballExtractor()

    async def compute_delta(
        self, package_id: ObjectId, from_version: str, to_version: str
    ) -> Optional[PackageDelta]:
        """
        Compute delta between two versions.

        Args:
            package_id: Package ID
            from_version: Source version
            to_version: Target version

        Returns:
            PackageDelta or None if computation fails
        """
        # Edge case: same version
        if from_version == to_version:
            print(
                f"[delta_service] ERROR: Cannot compare version to itself: {from_version}"
            )
            return None

        # Check if delta already exists
        existing_delta = await self.delta_repo.find_delta(package_id, from_version, to_version)
        if existing_delta:
            print(
                f"[delta_service] Delta already exists: {from_version} -> {to_version}"
            )
            return existing_delta

        # Get package metadata
        package = await self.package_repo.find_by_id(package_id)
        if not package or not package.id:
            print(f"[delta_service] ERROR: Package not found: {package_id}")
            return None

        print(
            f"[delta_service] Computing delta for {package.name}: {from_version} -> {to_version}"
        )

        # Download and analyze both versions in parallel
        old_result, new_result = await asyncio.gather(
            self._download_and_analyze_version(package.name, from_version),
            self._download_and_analyze_version(package.name, to_version),
            return_exceptions=True,
        )

        # Handle errors from parallel execution
        if isinstance(old_result, Exception):
            print(f"[delta_service] ERROR: Failed to analyze old version: {old_result}")
            return None
        if isinstance(new_result, Exception):
            print(f"[delta_service] ERROR: Failed to analyze new version: {new_result}")
            return None

        # At this point old_result and new_result are TarballContent | None
        # Check if analyses succeeded
        if not old_result or not new_result:
            print(f"[delta_service] ERROR: One or both versions failed analysis")
            return None

        # Now we can safely assign to typed variables
        old_analysis: TarballContent = old_result
        new_analysis: TarballContent = new_result

        # Check if both analyses failed (empty files)
        if not old_analysis.files and not new_analysis.files:
            print(f"[delta_service] ERROR: Both versions failed analysis, cannot compute delta")
            return None

        # Compute file-level diff
        added_files, removed_files, changed_files = self._compute_file_diff(
            old_analysis.files, new_analysis.files
        )

        # Detect signals
        signals = self._detect_signals(
            old_analysis, new_analysis, added_files, removed_files, changed_files
        )

        # Calculate risk score
        risk_score = self._calculate_risk_score(signals, old_analysis, new_analysis)

        # Generate analysis
        analysis = self._generate_analysis(signals, risk_score, old_analysis, new_analysis)

        # Create PackageDelta record
        delta = PackageDelta(
            package_id=package.id,
            from_version=from_version,
            to_version=to_version,
            computed_at=datetime.now(timezone.utc),
            signals=signals,
            risk_score=risk_score,
            analysis=analysis,
        )

        # Save to database
        created_delta = await self.delta_repo.create(delta)

        print(
            f"[delta_service] Delta computed: {package.name} "
            f"{from_version} -> {to_version} (risk: {risk_score:.1f})"
        )

        return created_delta

    async def _download_and_analyze_version(
        self, package_name: str, version: str
    ) -> Optional[TarballContent]:
        """
        Download tarball and analyze it.

        Args:
            package_name: npm package name
            version: Version to analyze

        Returns:
            TarballContent or None on failure
        """
        # Get package metadata (LOW priority - background delta computation)
        from services.priority_resource_manager import Priority

        metadata = await self.npm_client.get_package_metadata(package_name, Priority.LOW)

        if not metadata or version not in metadata.versions:
            print(
                f"[delta_service] ERROR: Version {version} not found for {package_name}"
            )
            return None

        version_info = metadata.versions[version]

        # Download tarball (LOW priority - background delta computation)
        tarball_bytes = await self.npm_client.download_tarball(version_info.tarball_url, Priority.LOW)

        if not tarball_bytes:
            print(
                f"[delta_service] ERROR: Failed to download tarball for {package_name}@{version}"
            )
            return None

        # Extract tarball content
        content = await asyncio.to_thread(
            self.tarball_extractor.extract, tarball_bytes
        )

        return content

    def _compute_file_diff(
        self, old_files: List[str], new_files: List[str]
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Compute file-level diff.

        Args:
            old_files: Files in old version
            new_files: Files in new version

        Returns:
            Tuple of (added_files, removed_files, changed_files)
        """
        old_set = set(old_files)
        new_set = set(new_files)

        added_files = sorted(list(new_set - old_set))
        removed_files = sorted(list(old_set - new_set))
        changed_files = sorted(list(old_set & new_set))

        return added_files, removed_files, changed_files

    def _detect_signals(
        self,
        old_analysis: TarballContent,
        new_analysis: TarballContent,
        added_files: List[str],
        removed_files: List[str],
        changed_files: List[str],
    ) -> Signals:
        """
        Detect signals from the comparison (STUBBED - AI analysis will be added later).

        Args:
            old_analysis: Content of old version
            new_analysis: Content of new version
            added_files: Files added in new version
            removed_files: Files removed in new version
            changed_files: Files present in both versions

        Returns:
            Signals object with basic detected signals
        """
        # has_install_scripts: Check if new version has install scripts
        has_install_scripts = new_analysis.has_install_scripts

        # touched_install_scripts: Install scripts added or modified
        old_scripts = set(old_analysis.scripts.keys())
        new_scripts = set(new_analysis.scripts.keys())

        # Check for added install scripts
        added_install_scripts = (new_scripts & self.INSTALL_SCRIPT_NAMES) - (
            old_scripts & self.INSTALL_SCRIPT_NAMES
        )

        # Check for modified install scripts (script exists in both but content differs)
        modified_install_scripts = []
        for script_name in self.INSTALL_SCRIPT_NAMES:
            if script_name in old_scripts and script_name in new_scripts:
                if old_analysis.scripts[script_name] != new_analysis.scripts[script_name]:
                    modified_install_scripts.append(script_name)

        touched_install_scripts = bool(added_install_scripts or modified_install_scripts)

        # has_native_code: Check for native file extensions
        has_native_code = any(
            any(f.endswith(ext) for ext in self.NATIVE_EXTENSIONS)
            for f in new_analysis.files
        )

        # TODO: These signals require AI analysis - stubbed for now
        added_network_calls = False  # Will be analyzed by AI agent
        minified_or_obfuscated_delta = False  # Will be analyzed by AI agent

        return Signals(
            added_files=added_files,
            removed_files=removed_files,
            changed_files=changed_files,
            has_install_scripts=has_install_scripts,
            touched_install_scripts=touched_install_scripts,
            has_native_code=has_native_code,
            added_network_calls=added_network_calls,
            minified_or_obfuscated_delta=minified_or_obfuscated_delta,
        )

    def _calculate_risk_score(
        self,
        signals: Signals,
        old_analysis: TarballContent,
        new_analysis: TarballContent,
    ) -> float:
        """
        Calculate placeholder risk score (STUBBED - AI analysis will determine real risk).

        Args:
            signals: Detected signals
            old_analysis: Content of old version
            new_analysis: Content of new version

        Returns:
            Placeholder risk score (0-100)
        """
        # TODO: Real risk scoring will be done by AI agent
        # For now, return placeholder based on simple heuristics

        score = 0.0

        # Base score for any changes
        if signals.changed_files or signals.added_files:
            score += 5

        # Critical signal: install scripts modified
        if signals.touched_install_scripts:
            score += 40

        # Medium signals
        if signals.has_native_code:
            score += 15

        if signals.has_install_scripts and not signals.touched_install_scripts:
            score += 10

        # File count analysis
        old_file_count = len(old_analysis.files)
        new_file_count = len(new_analysis.files)
        if old_file_count > 0:
            growth_rate = (new_file_count - old_file_count) / old_file_count
            if growth_rate > 0.5:
                score += 15

        # Cap at 100
        return min(score, 100.0)

    def _generate_analysis(
        self,
        signals: Signals,
        risk_score: float,
        old_analysis: TarballContent,
        new_analysis: TarballContent,
    ) -> Analysis:
        """
        Generate placeholder analysis (STUBBED - AI agent will generate detailed analysis).

        Args:
            signals: Detected signals
            risk_score: Calculated risk score
            old_analysis: Content of old version
            new_analysis: Content of new version

        Returns:
            Placeholder Analysis object
        """
        # TODO: Real analysis will be generated by AI agent
        reasons: List[str] = []

        # Basic summary
        summary = f"Version delta computed: {len(signals.added_files)} files added, {len(signals.removed_files)} removed, {len(signals.changed_files)} modified"

        # File change statistics
        file_stats = (
            f"{len(signals.added_files)} added, "
            f"{len(signals.removed_files)} removed, "
            f"{len(signals.changed_files)} modified"
        )
        reasons.append(f"File changes: {file_stats}")

        # Signal-based reasons (only for the signals we can detect)
        if signals.touched_install_scripts:
            reasons.append("Install scripts were added or modified")

        if signals.has_native_code:
            reasons.append("Contains native compiled code")

        if signals.has_install_scripts and not signals.touched_install_scripts:
            reasons.append("Has install scripts (unchanged)")

        # Note about AI analysis
        reasons.append("Detailed risk analysis pending AI agent review")

        return Analysis(
            summary=summary,
            reasons=reasons,
            confidence=0.5,  # Low confidence - placeholder only
            source="rule",
        )

    async def backfill_deltas(self, num_releases: int = 5) -> dict:
        """
        Backfill deltas for the most recent N releases of each package.

        Args:
            num_releases: Number of recent releases to backfill (default 5)

        Returns:
            Summary dict with counts
        """
        print(f"[delta_service] Starting backfill for last {num_releases} releases per package")

        # Get all packages
        packages = await self.package_repo.find_many({})

        total_deltas = 0
        errors = 0

        for package in packages:
            if not package.id:
                continue  # Skip packages without ID

            # Get most recent N releases, sorted by publish_timestamp descending
            releases = await self.release_repo.find_by_package(
                package.id, skip=0, limit=num_releases
            )

            if len(releases) < 2:
                continue  # Need at least 2 releases to compare

            # Reverse to get chronological order (oldest to newest)
            releases.reverse()

            print(
                f"[delta_service] Backfilling {len(releases)-1} deltas for {package.name}"
            )

            # Compute deltas for consecutive versions
            for i in range(len(releases) - 1):
                from_version = releases[i].version
                to_version = releases[i + 1].version

                try:
                    delta = await self.compute_delta(
                        package.id, from_version, to_version
                    )
                    if delta:
                        total_deltas += 1
                except Exception as e:
                    errors += 1
                    print(
                        f"[delta_service] ERROR: Backfill failed for {package.name} "
                        f"{from_version}->{to_version}: {e}"
                    )

        summary = {
            "packages_processed": len(packages),
            "deltas_created": total_deltas,
            "errors": errors,
            "num_releases": num_releases,
        }

        print(f"[delta_service] Backfill complete: {summary}")
        return summary
