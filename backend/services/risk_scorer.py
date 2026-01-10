"""
Risk scoring logic for releases and identities.
"""

from datetime import datetime, timezone
from typing import Optional, List
from dataclasses import dataclass

from services.github_client import GitHubUserInfo
from services.tarball_analyzer import TarballAnalysisResult


@dataclass
class RiskAssessment:
    """Complete risk assessment with score and reasoning."""

    score: float  # 0-100
    severity: float  # 0-100 (for alerts)
    reasons: List[str]
    should_alert: bool
    alert_reason: Optional[str]


class RiskScorer:
    """
    Risk scoring engine.

    Scoring weights:
    - New maintainer (first-time in our system): +30
    - GitHub account < 90 days old: +25
    - No GitHub account found: +15
    - Has postinstall/preinstall scripts: +15
    - Suspicious file patterns: +20
    - Suspicious content patterns: +10 per unique pattern (max +50)
    - Low followers/repos on GitHub: +10
    - No email on GitHub: +5

    Alert threshold: score >= 60
    """

    ALERT_THRESHOLD = 60

    def assess_release(
        self,
        *,
        is_first_time_maintainer: bool,
        github_info: Optional[GitHubUserInfo],
        tarball_analysis: TarballAnalysisResult,
        maintainer_handle: Optional[str] = None,
    ) -> RiskAssessment:
        """
        Assess risk for a package release.

        Args:
            is_first_time_maintainer: True if maintainer not previously seen
            github_info: GitHub user info (if resolved)
            tarball_analysis: Results from tarball analysis
            maintainer_handle: npm username of publisher

        Returns:
            RiskAssessment with score and details
        """
        score = 0.0
        reasons: List[str] = []

        # Maintainer risk factors
        if is_first_time_maintainer:
            score += 30
            reasons.append("First-time maintainer (not previously tracked)")

        # GitHub account risk factors
        if github_info:
            if github_info.is_new_account:
                score += 25
                now = datetime.now(timezone.utc)
                account_age = (now - github_info.created_at).days
                reasons.append(f"GitHub account only {account_age} days old")

            if github_info.followers < 5 and github_info.public_repos < 3:
                score += 10
                reasons.append("Low GitHub activity (few followers/repos)")

            if not github_info.email:
                score += 5
                reasons.append("No public email on GitHub")
        else:
            if maintainer_handle:
                score += 15
                reasons.append("GitHub account not found or not linked")

        # Tarball content risk factors
        if tarball_analysis.has_postinstall:
            score += 15
            reasons.append("Contains postinstall script")
        elif tarball_analysis.has_preinstall:
            score += 15
            reasons.append("Contains preinstall script")
        elif tarball_analysis.has_install_scripts:
            score += 10
            reasons.append("Contains install scripts")

        if tarball_analysis.suspicious_files:
            score += 20
            reasons.append(
                f"Suspicious filenames: {', '.join(tarball_analysis.suspicious_files[:3])}"
            )

        # Score for suspicious content patterns
        if tarball_analysis.suspicious_content_matches:
            unique_patterns = set()
            for matches in tarball_analysis.suspicious_content_matches.values():
                unique_patterns.update(matches)

            pattern_score = min(len(unique_patterns) * 10, 50)
            score += pattern_score
            reasons.append(
                f"Suspicious code patterns: {', '.join(list(unique_patterns)[:3])}"
            )

        # Cap score at 100
        score = min(score, 100.0)

        # Determine if alert should be raised
        should_alert = score >= self.ALERT_THRESHOLD
        alert_reason = None

        if should_alert:
            if is_first_time_maintainer and tarball_analysis.suspicious_content_matches:
                alert_reason = "New maintainer with suspicious code patterns"
            elif is_first_time_maintainer and tarball_analysis.has_install_scripts:
                alert_reason = "New maintainer added install scripts"
            elif github_info and github_info.is_new_account:
                alert_reason = "Publisher has newly created GitHub account"
            else:
                alert_reason = "Multiple risk indicators detected"

        return RiskAssessment(
            score=score,
            severity=score,  # Use same value for severity
            reasons=reasons,
            should_alert=should_alert,
            alert_reason=alert_reason,
        )