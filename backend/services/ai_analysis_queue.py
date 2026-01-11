"""
AI Analysis Queue Service - Rate-limited AI analysis processing.

This service manages a queue of AI analysis requests, processing them
with configurable delays to avoid overwhelming the API and reduce costs.
High-priority items (high-risk releases) can be processed immediately.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from collections import deque

from bson import ObjectId
from pymongo.database import Database

from models.package import Package
from models.package_release import PackageRelease
from models.package_delta import PackageDelta
from models.identity import Identity
from models.risk_alert import RiskAlert
from models.analysis import Analysis
from repositories.risk_alert import RiskAlertRepository
from repositories.package_threat_assessment import PackageThreatAssessmentRepository
from services.ai_alert_service import AIAlertService
from services.ai_threat_surface_service import AIThreatSurfaceService
from services.tarball_extractor import TarballContent
from services.github_client import GitHubUserInfo
from services.pause_manager import get_pause_manager


@dataclass
class AIAnalysisRequest:
    """Represents a queued AI analysis request."""
    package: Package
    package_id: ObjectId
    release: PackageRelease
    identity: Optional[Identity]
    github_info: Optional[GitHubUserInfo]
    tarball_analysis: Optional[TarballContent]
    delta: Optional[PackageDelta]
    priority: int  # Higher = more urgent
    queued_at: datetime


class AIAnalysisQueue:
    """
    Queue-based AI analysis processor with rate limiting.

    Features:
    - Processes AI analysis requests sequentially with delays
    - High-priority requests (risk >= threshold) are processed immediately
    - Low-priority requests are queued and processed with delays
    - Non-blocking queue worker runs in background
    """

    def __init__(
        self,
        database: Database,
        ai_alert_service: AIAlertService,
        ai_threat_surface_service: AIThreatSurfaceService,
        delay_between_calls: float = 5.0,
        high_priority_threshold: float = 70.0,
    ):
        """
        Initialize AI analysis queue.

        Args:
            database: MongoDB database
            ai_alert_service: AI alert service instance
            ai_threat_surface_service: AI threat surface service instance
            delay_between_calls: Seconds to wait between processing queued items
            high_priority_threshold: Risk score threshold for immediate processing
        """
        self.db = database
        self.ai_alert_service = ai_alert_service
        self.ai_threat_surface_service = ai_threat_surface_service
        self.delay_between_calls = delay_between_calls
        self.high_priority_threshold = high_priority_threshold

        # Repositories
        self.alert_repo = RiskAlertRepository(database)
        self.threat_surface_repo = PackageThreatAssessmentRepository(database)

        # Queue management
        self._queue: deque[AIAnalysisRequest] = deque()
        self._processing = False
        self._worker_task: Optional[asyncio.Task] = None
        self._shutdown = False

        print(f"[ai_queue] Initialized with {delay_between_calls}s delay, priority threshold: {high_priority_threshold}")

    def start_worker(self):
        """Start the background queue worker."""
        if self._worker_task is None or self._worker_task.done():
            self._shutdown = False
            self._worker_task = asyncio.create_task(self._process_queue_worker())
            print("[ai_queue] Worker started")

    async def stop_worker(self):
        """Stop the background queue worker gracefully."""
        self._shutdown = True
        if self._worker_task and not self._worker_task.done():
            await self._worker_task
            print("[ai_queue] Worker stopped")

    def queue_analysis(
        self,
        package: Package,
        package_id: ObjectId,
        release: PackageRelease,
        identity: Optional[Identity],
        github_info: Optional[GitHubUserInfo],
        tarball_analysis: Optional[TarballContent],
        delta: Optional[PackageDelta],
    ):
        """
        Queue an AI analysis request.

        High-priority requests (risk >= threshold) are processed immediately.
        Low-priority requests are added to queue for delayed processing.

        Args:
            package: Package being analyzed
            package_id: Package ObjectId
            release: PackageRelease record
            identity: Maintainer identity (if known)
            github_info: GitHub user info
            tarball_analysis: Tarball content analysis
            delta: Delta from previous version (if available)
        """
        # Determine priority based on risk score
        risk_score = release.risk_score or 0.0
        priority = int(risk_score)

        request = AIAnalysisRequest(
            package=package,
            package_id=package_id,
            release=release,
            identity=identity,
            github_info=github_info,
            tarball_analysis=tarball_analysis,
            delta=delta,
            priority=priority,
            queued_at=datetime.now(timezone.utc),
        )

        # High-priority: process immediately (non-blocking)
        if risk_score >= self.high_priority_threshold:
            asyncio.create_task(self._process_request(request))
            print(f"[ai_queue] HIGH PRIORITY: Immediate analysis for {package.name}@{release.version} (risk: {risk_score:.1f})")
        else:
            # Low-priority: add to queue
            self._queue.append(request)
            print(f"[ai_queue] Queued: {package.name}@{release.version} (risk: {risk_score:.1f}, queue size: {len(self._queue)})")

    async def _process_queue_worker(self):
        """Background worker that processes queued items with delays."""
        print("[ai_queue] Queue worker running")

        while not self._shutdown:
            # Check if background processes are paused
            pause_manager = get_pause_manager()
            if pause_manager.is_paused():
                # Background processes paused, wait and check again
                await asyncio.sleep(1.0)
                continue

            if not self._queue:
                # No items in queue, wait a bit
                await asyncio.sleep(1.0)
                continue

            # Get next item from queue
            request = self._queue.popleft()

            # Process the request
            await self._process_request(request)

            # Wait before processing next item (rate limiting)
            if self._queue:  # Only delay if there are more items
                await asyncio.sleep(self.delay_between_calls)

        print("[ai_queue] Queue worker stopped")

    async def _process_request(self, request: AIAnalysisRequest):
        """
        Process a single AI analysis request.

        Args:
            request: Analysis request to process
        """
        package = request.package
        package_id = request.package_id
        release = request.release
        identity = request.identity
        delta = request.delta

        try:
            # Get previous threat assessment for context
            previous_assessment = await self.threat_surface_repo.find_current_by_package(package_id)

            # Get maintainers for threat surface analysis
            maintainers = []
            if identity:
                maintainers = [identity]

            # Start both AI tasks in parallel
            alert_task = asyncio.create_task(
                self.ai_alert_service.analyze_release(
                    package=package,
                    release=release,
                    maintainer_identity=identity,
                    github_info=request.github_info,
                    tarball_analysis=request.tarball_analysis.__dict__ if request.tarball_analysis else None,
                    delta_signals=delta.signals.__dict__ if delta else None,
                    previous_analyses=None,  # Built internally
                )
            )

            threat_surface_task = asyncio.create_task(
                self.ai_threat_surface_service.generate_assessment(
                    package=package,
                    release=release,
                    dependencies=[],  # Simplified for now
                    maintainers=maintainers,
                    previous_assessment=previous_assessment,
                )
            )

            # Wait for both with timeout
            results = await asyncio.gather(
                asyncio.wait_for(alert_task, timeout=30.0),
                asyncio.wait_for(threat_surface_task, timeout=45.0),
                return_exceptions=True
            )

            # Process AI alert results
            ai_alerts = []
            if not isinstance(results[0], Exception):
                ai_alerts = results[0]
                print(f"[ai_queue] AI alert analysis completed: {len(ai_alerts)} alerts for {package.name}@{release.version}")
            else:
                print(f"[ai_queue] WARNING: AI alert analysis failed for {package.name}@{release.version}: {results[0]}")

            # Process threat surface assessment results
            if not isinstance(results[1], Exception):
                threat_assessment = results[1]
                await self.threat_surface_repo.create(threat_assessment)
                print(f"[ai_queue] Threat surface assessment generated for {package.name}@{release.version}")
            else:
                print(f"[ai_queue] WARNING: Threat surface analysis failed for {package.name}@{release.version}: {results[1]}")

            # Create RiskAlert records from AI alerts
            for ai_alert in ai_alerts:
                alert = RiskAlert(
                    package_id=package_id,
                    identity_id=identity.id if identity else None,
                    release_id=release.id,
                    delta_id=delta.id if delta else None,
                    reason=ai_alert['reason'],
                    severity=ai_alert['severity'],
                    status="open",
                    analysis=Analysis(
                        summary=ai_alert['reason'],
                        reasons=ai_alert['evidence'],
                        confidence=ai_alert['confidence'],
                        source="ai",
                    )
                )
                await self.alert_repo.create(alert)
                print(f"[ai_queue] ALERT: AI-generated alert created: {ai_alert['reason'][:80]}...")

        except Exception as e:
            print(f"[ai_queue] ERROR: AI analysis failed for {package.name}@{release.version}: {e}")

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self._queue)
