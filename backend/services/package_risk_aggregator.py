"""
Package Risk Aggregator - calculates aggregate risk scores for packages.
"""

import asyncio
from bson import ObjectId
from typing import Optional

from repositories.package import PackageRepository
from repositories.package_release import PackageReleaseRepository
from repositories.risk_alert import RiskAlertRepository
from repositories.package_threat_assessment import PackageThreatAssessmentRepository


class PackageRiskAggregator:
    """
    Aggregates multiple risk signals into a single package-level risk score.

    Risk score is calculated from:
    - Latest release risk score (weighted 40%)
    - Open alert count and severity (weighted 30%)
    - Threat assessment overall risk level (weighted 30%)
    """

    def __init__(self, database):
        self.package_repo = PackageRepository(database)
        self.release_repo = PackageReleaseRepository(database)
        self.alert_repo = RiskAlertRepository(database)
        self.threat_assessment_repo = PackageThreatAssessmentRepository(database)

    async def calculate_package_risk(self, package_id: ObjectId) -> float:
        """
        Calculate aggregate risk score for a package.

        Args:
            package_id: Package ID

        Returns:
            Risk score between 0-100
        """
        # Run all queries in parallel
        latest_release_task = asyncio.create_task(
            self.release_repo.find_by_package(package_id, skip=0, limit=1)
        )
        open_alerts_task = asyncio.create_task(
            self.alert_repo.find_many(
                {"package_id": package_id, "status": "open"}, limit=100
            )
        )
        threat_assessment_task = asyncio.create_task(
            self.threat_assessment_repo.find_current_by_package(package_id)
        )

        latest_releases = await latest_release_task
        latest_release = latest_releases[0] if latest_releases else None
        open_alerts = await open_alerts_task
        threat_assessment = await threat_assessment_task

        # Calculate component scores
        release_score = self._calculate_release_score(latest_release)
        alert_score = self._calculate_alert_score(open_alerts)
        assessment_score = self._calculate_assessment_score(threat_assessment)

        # Weighted average
        # If component is missing, redistribute weight to others
        total_weight = 0
        weighted_sum = 0

        if release_score is not None:
            weighted_sum += release_score * 0.4
            total_weight += 0.4

        if alert_score is not None:
            weighted_sum += alert_score * 0.3
            total_weight += 0.3

        if assessment_score is not None:
            weighted_sum += assessment_score * 0.3
            total_weight += 0.3

        # If no signals at all, return 0
        if total_weight == 0:
            return 0.0

        # Normalize to available weight
        final_score = weighted_sum / total_weight

        return round(final_score, 1)

    def _calculate_release_score(self, release) -> Optional[float]:
        """Calculate risk contribution from latest release."""
        if not release:
            return None
        return float(release.risk_score)

    def _calculate_alert_score(self, alerts) -> Optional[float]:
        """Calculate risk contribution from open alerts."""
        if not alerts:
            return 0.0  # No alerts = 0 risk from this component

        # Count alerts by severity range
        critical_count = sum(1 for a in alerts if a.severity >= 80)
        high_count = sum(1 for a in alerts if 60 <= a.severity < 80)
        medium_count = sum(1 for a in alerts if 40 <= a.severity < 60)
        low_count = sum(1 for a in alerts if a.severity < 40)

        # Calculate weighted score based on alert counts
        # Critical alerts: 80-100 range
        # High alerts: 60-80 range
        # Medium alerts: 40-60 range
        # Low alerts: 20-40 range

        score = 0.0

        if critical_count > 0:
            # 1 critical = 80, 2+ = 100
            score = min(100, 80 + (critical_count - 1) * 10)
        elif high_count > 0:
            # 1 high = 60, 2 = 70, 3+ = 80
            score = min(80, 60 + (high_count - 1) * 5)
        elif medium_count > 0:
            # 1 medium = 40, 2 = 50, 3+ = 60
            score = min(60, 40 + (medium_count - 1) * 5)
        elif low_count > 0:
            # 1+ low = 20-30
            score = min(30, 20 + low_count * 2)

        return score

    def _calculate_assessment_score(self, assessment) -> Optional[float]:
        """Calculate risk contribution from threat assessment."""
        if not assessment:
            return None

        # Map risk levels to numeric scores
        risk_level_map = {
            "low": 20.0,
            "medium": 50.0,
            "high": 75.0,
            "critical": 95.0,
        }

        base_score = risk_level_map.get(assessment.overall_risk_level, 50.0)

        # Adjust by confidence (lower confidence = reduce impact)
        confidence_factor = assessment.confidence
        adjusted_score = base_score * confidence_factor

        return adjusted_score

    async def update_package_risk_score(self, package_id: ObjectId) -> float:
        """
        Calculate and update package risk score in database.

        Args:
            package_id: Package ID

        Returns:
            Updated risk score
        """
        risk_score = await self.calculate_package_risk(package_id)

        # Update package in database
        await self.package_repo.update(
            package_id,
            {"risk_score": risk_score}
        )

        return risk_score

    async def recalculate_all_package_risks(self) -> int:
        """
        Recalculate risk scores for all packages.

        Use for batch recalculation or fixing scores.

        Returns:
            Number of packages updated
        """
        packages = await self.package_repo.find_many({}, limit=10000)

        count = 0
        for package in packages:
            if package.id:
                await self.update_package_risk_score(package.id)
                count += 1

        return count
