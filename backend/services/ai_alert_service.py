"""
AI Alert Service - generates specific threat alerts using agno + OpenRouter.
"""

import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId

from agno.agent import Agent
from agno.models.openrouter import OpenRouter

from models.package import Package
from models.package_release import PackageRelease
from models.identity import Identity
from models.ai_analysis_history import AIAnalysisHistory
from repositories.ai_analysis_history import AIAnalysisHistoryRepository
from services.github_client import GitHubUserInfo


class AIAlertService:
    """
    Generates specific threat alerts for suspicious activities.
    Uses agno with OpenRouter (Claude 3.5 Sonnet) for analysis.
    """

    def __init__(self, database, openrouter_api_key: str):
        """
        Initialize AI Alert Service.

        Args:
            database: MongoDB database instance
            openrouter_api_key: API key for OpenRouter
        """
        self.database = database
        self.history_repo = AIAnalysisHistoryRepository(database)

        # Initialize agno Agent with OpenRouter
        self.agent = Agent(
            name="ThreatDetector",
            model=OpenRouter(id="anthropic/claude-3.5-sonnet"),
            instructions="""You are a security analyst specializing in supply chain attacks and malicious npm packages.
Your task is to analyze npm package releases and detect suspicious activities that could indicate security threats.

You should look for:
- Code obfuscation or minification in unexpected files
- Network calls to external domains (especially suspicious ones)
- Cryptocurrency mining indicators
- Data exfiltration patterns
- Permission escalation attempts
- Maintainer behavior anomalies
- Release pattern deviations

Always provide specific evidence for your findings and assign appropriate severity scores.""",
            markdown=True,
        )

        # Configure API key
        if openrouter_api_key:
            self.agent.model.api_key = openrouter_api_key

    async def analyze_release(
        self,
        package: Package,
        release: PackageRelease,
        maintainer_identity: Optional[Identity],
        github_info: Optional[GitHubUserInfo],
        tarball_analysis: Optional[Dict[str, Any]],
        delta_signals: Optional[Dict[str, Any]],
        previous_analyses: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Analyze a package release for security threats and generate alerts.

        Args:
            package: Package being analyzed
            release: Release being analyzed
            maintainer_identity: Identity of the maintainer who published
            github_info: GitHub profile information
            tarball_analysis: Analysis of tarball contents
            delta_signals: Signals from delta analysis
            previous_analyses: Previous analysis context for this package

        Returns:
            List of alert dictionaries with reason, severity, confidence, category, evidence
        """
        try:
            # Build analysis context from previous analyses
            if previous_analyses is None:
                previous_analyses = await self._build_analysis_context(
                    package.id, limit=10
                )

            # Create comprehensive prompt
            prompt = self._create_analysis_prompt(
                package=package,
                release=release,
                maintainer_identity=maintainer_identity,
                github_info=github_info,
                tarball_analysis=tarball_analysis,
                delta_signals=delta_signals,
                previous_analyses=previous_analyses,
            )

            # Run AI analysis with timeout
            response = await asyncio.wait_for(
                self._run_agent_analysis(prompt), timeout=30.0
            )

            # Parse structured response
            alerts = self._parse_ai_response(response)

            # Store analysis history for future context
            await self._store_analysis_memory(
                package_id=package.id,
                release_id=release.id,
                summary=response.get("summary", "AI analysis completed"),
                alerts=alerts,
                confidence=sum(a["confidence"] for a in alerts) / len(alerts)
                if alerts
                else 0.0,
            )

            return alerts

        except asyncio.TimeoutError:
            print(f"[ai_alert_service] TIMEOUT: Analysis timed out for {package.name}")
            return []
        except Exception as e:
            print(f"[ai_alert_service] ERROR: Analysis failed for {package.name}: {e}")
            return []

    async def _run_agent_analysis(self, prompt: str) -> Dict[str, Any]:
        """
        Run agno agent analysis.

        Args:
            prompt: Structured prompt for analysis

        Returns:
            Parsed JSON response from agent
        """
        # Run agent (agno handles async execution internally)
        response = self.agent.run(prompt)

        # Extract text content
        if hasattr(response, "content"):
            response_text = response.content
        else:
            response_text = str(response)

        # Try to extract JSON from markdown code blocks
        try:
            # Look for JSON in code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text

            # Parse JSON
            result = json.loads(json_text)
            return result

        except json.JSONDecodeError as e:
            print(f"[ai_alert_service] WARNING: Failed to parse JSON response: {e}")
            print(f"[ai_alert_service] Response text: {response_text[:500]}")
            return {"alerts": [], "summary": "Failed to parse AI response"}

    def _create_analysis_prompt(
        self,
        package: Package,
        release: PackageRelease,
        maintainer_identity: Optional[Identity],
        github_info: Optional[GitHubUserInfo],
        tarball_analysis: Optional[Dict[str, Any]],
        delta_signals: Optional[Dict[str, Any]],
        previous_analyses: List[Dict[str, Any]],
    ) -> str:
        """
        Create comprehensive analysis prompt.

        Args:
            package: Package information
            release: Release information
            maintainer_identity: Maintainer identity
            github_info: GitHub profile data
            tarball_analysis: Tarball analysis results
            delta_signals: Delta signals
            previous_analyses: Previous analysis summaries

        Returns:
            Formatted prompt string
        """
        # Build maintainer section
        maintainer_section = "MAINTAINER:\n"
        if maintainer_identity:
            maintainer_section += f"- Handle: {maintainer_identity.handle}\n"
            maintainer_section += f"- Kind: {maintainer_identity.kind}\n"
            maintainer_section += (
                f"- Risk Score: {maintainer_identity.risk_score:.1f}\n"
            )
            maintainer_section += f"- First Seen: {maintainer_identity.first_seen}\n"
        else:
            maintainer_section += "- UNKNOWN MAINTAINER\n"

        # Build GitHub info section
        if github_info:
            maintainer_section += (
                f"- GitHub Profile: {github_info.username}\n"
            )
            maintainer_section += (
                f"- GitHub Followers: {github_info.followers}\n"
            )
            maintainer_section += (
                f"- Public Repos: {github_info.public_repos}\n"
            )
            maintainer_section += (
                f"- Account Age: {github_info.created_at.isoformat()}\n"
            )

        # Build code changes section
        code_changes_section = "CODE CHANGES:\n"
        if delta_signals:
            code_changes_section += (
                f"- Files added: {len(delta_signals.get('added_files', []))}\n"
            )
            code_changes_section += (
                f"- Files removed: {len(delta_signals.get('removed_files', []))}\n"
            )
            code_changes_section += (
                f"- Files modified: {len(delta_signals.get('changed_files', []))}\n"
            )
            code_changes_section += f"- Install scripts touched: {delta_signals.get('touched_install_scripts', False)}\n"
            code_changes_section += (
                f"- Has native code: {delta_signals.get('has_native_code', False)}\n"
            )

            if delta_signals.get("added_files"):
                sample_files = delta_signals["added_files"][:5]
                code_changes_section += (
                    f"- Sample added files: {', '.join(sample_files)}\n"
                )
        else:
            code_changes_section += "- No delta information available\n"

        # Build tarball analysis section
        tarball_section = ""
        if tarball_analysis:
            tarball_section = f"\nTARBALL ANALYSIS:\n"
            tarball_section += f"- Has install scripts: {tarball_analysis.get('has_install_scripts', False)}\n"
            tarball_section += (
                f"- Has binary files: {tarball_analysis.get('has_binaries', False)}\n"
            )

        # Build historical context section
        historical_section = "\nHISTORICAL CONTEXT (Last 10 analyses):\n"
        if previous_analyses:
            for i, analysis in enumerate(previous_analyses[:5], 1):  # Show top 5
                historical_section += f"{i}. {analysis.get('timestamp', 'Unknown')}: "
                historical_section += f"{analysis.get('summary', 'No summary')} "
                historical_section += f"({analysis.get('alerts_count', 0)} alerts)\n"
                if analysis.get("key_findings"):
                    for finding in analysis["key_findings"][:2]:  # Top 2 findings
                        historical_section += f"   - {finding}\n"
        else:
            historical_section += "- No previous analyses for this package\n"

        # Construct full prompt
        prompt = f"""Analyze this npm package release for security risks:

PACKAGE: {package.name}
VERSION: {release.version}
PREVIOUS VERSION: {release.previous_version or "N/A"}

{maintainer_section}

{code_changes_section}

{tarball_section}

{historical_section}

INSTRUCTIONS:
Analyze for:
1. Code obfuscation/minification patterns in unexpected files
2. Network calls to external/suspicious domains
3. Cryptocurrency mining indicators (crypto libraries, mining pools)
4. Data exfiltration patterns (environment variable access, file uploads)
5. Permission escalation attempts (sudo, setuid)
6. Maintainer behavior anomalies (new maintainer, suspicious activity)
7. Release pattern deviations (unusual timing, version jumps)

Output ONLY valid JSON in this exact format:
{{
  "alerts": [
    {{
      "reason": "Brief description of the threat",
      "severity": 0-100,
      "confidence": 0.0-1.0,
      "category": "obfuscation|network|crypto|exfiltration|permissions|maintainer|pattern",
      "evidence": ["specific evidence item 1", "specific evidence item 2"]
    }}
  ],
  "summary": "Overall assessment summary"
}}

IMPORTANT:
- Only generate alerts with confidence >= 0.6
- Severity ranges: 0-30 (low), 31-60 (medium), 61-80 (high), 81-100 (critical)
- Be specific with evidence
- If no threats found, return empty alerts array
"""
        return prompt

    def _parse_ai_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse and validate AI response.

        Args:
            response: Raw AI response

        Returns:
            List of validated alert dictionaries
        """
        alerts = response.get("alerts", [])
        validated_alerts = []

        for alert in alerts:
            # Validate required fields
            if not all(
                k in alert for k in ["reason", "severity", "confidence", "evidence"]
            ):
                print(f"[ai_alert_service] WARNING: Skipping invalid alert: {alert}")
                continue

            # Validate ranges
            severity = max(0, min(100, alert["severity"]))
            confidence = max(0.0, min(1.0, alert["confidence"]))

            # Filter by confidence threshold
            if confidence < 0.6:
                continue

            validated_alerts.append(
                {
                    "reason": alert["reason"],
                    "severity": severity,
                    "confidence": confidence,
                    "category": alert.get("category", "unknown"),
                    "evidence": alert.get("evidence", [])[
                        :10
                    ],  # Limit to 10 evidence items
                }
            )

        return validated_alerts

    async def _build_analysis_context(
        self, package_id: ObjectId, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve previous analyses for context building.

        Args:
            package_id: Package ID
            limit: Number of analyses to retrieve

        Returns:
            List of analysis summaries
        """
        history = await self.history_repo.find_by_package(package_id, limit=limit)

        context = []
        for h in history:
            context.append(
                {
                    "timestamp": h.timestamp.isoformat(),
                    "summary": h.analysis_summary,
                    "alerts_count": h.alerts_generated,
                    "key_findings": h.key_findings[:3],  # Top 3 only
                }
            )

        return context

    async def _store_analysis_memory(
        self,
        package_id: ObjectId,
        release_id: ObjectId,
        summary: str,
        alerts: List[Dict[str, Any]],
        confidence: float,
    ):
        """
        Store analysis history for future context.

        Args:
            package_id: Package ID
            release_id: Release ID
            summary: Analysis summary
            alerts: Generated alerts
            confidence: Average confidence score
        """
        # Extract key findings from alerts
        key_findings = [alert["reason"] for alert in alerts[:5]]  # Top 5 alerts

        history_record = AIAnalysisHistory(
            package_id=package_id,
            release_id=release_id,
            analysis_summary=summary,
            alerts_generated=len(alerts),
            key_findings=key_findings,
            confidence=confidence,
        )

        await self.history_repo.create(history_record)

        # Cleanup old analyses (keep last 50)
        await self.history_repo.cleanup_old_analyses(package_id, keep_last=50)
