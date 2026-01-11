"""
AI Threat Surface Service - generates comprehensive threat surface assessments.
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
from models.package_threat_assessment import PackageThreatAssessment
from repositories.package_threat_assessment import PackageThreatAssessmentRepository
from repositories.package import PackageRepository
from repositories.package_release import PackageReleaseRepository
from repositories.identity import IdentityRepository


class AIThreatSurfaceService:
    """
    Generates comprehensive threat surface assessments for packages.
    Uses agno with OpenRouter (Claude 3.5 Sonnet) for holistic analysis.
    """

    def __init__(self, database, openrouter_api_key: str):
        """
        Initialize AI Threat Surface Service.

        Args:
            database: MongoDB database instance
            openrouter_api_key: API key for OpenRouter
        """
        self.database = database
        self.assessment_repo = PackageThreatAssessmentRepository(database)

        # Initialize agno Agent with OpenRouter (separate from alerts agent)
        self.agent = Agent(
            name="ThreatSurfaceAnalyzer",
            model=OpenRouter(id="anthropic/claude-3.5-sonnet"),
            instructions="""You are a strategic security analyst specializing in comprehensive threat surface assessments.
Your task is to provide balanced, evolving assessments of npm packages that include:

1. Both strengths AND weaknesses (not just threats)
2. Specific package and maintainer names when discussing risks or strengths
3. Downstream supply chain risks from dependencies
4. Maintainer trustworthiness based on activity and reputation
5. How the threat picture has evolved over time
6. Realistic, measured tone - candid about risks but not alarmist

Always provide comprehensive narrative assessments (2-4 paragraphs) that give the full security picture.""",
            markdown=True,
        )

        # Configure API key
        if openrouter_api_key:
            self.agent.model.api_key = openrouter_api_key

    async def generate_assessment_for_package(
        self, package_name: str
    ) -> Optional[PackageThreatAssessment]:
        """
        Generate threat assessment for a package by name.

        This is a convenience method that fetches all required data and generates
        an assessment. It can be called from package creation, dependency scanning,
        or manual triggers.

        Args:
            package_name: npm package name

        Returns:
            Generated PackageThreatAssessment or None if package/release not found
        """
        try:
            # Initialize repositories
            package_repo = PackageRepository(self.database)
            release_repo = PackageReleaseRepository(self.database)
            identity_repo = IdentityRepository(self.database)

            # 1. Get package
            package = await package_repo.find_by_name(package_name)
            if not package or not package.id:
                print(
                    f"[ai_threat_surface_service] Package not found: {package_name}"
                )
                return None

            # 2. Get latest release
            releases = await release_repo.find_by_package(package.id, limit=1)
            if not releases:
                print(
                    f"[ai_threat_surface_service] No releases found for {package_name}"
                )
                return None

            latest_release = releases[0]

            # 3. Get dependencies from database
            dependencies = []
            try:
                # Try to fetch dependency tree from database
                dep_tree = self.database.dependency_trees.find_one(
                    {"name": package_name, "version": latest_release.version}
                )
                if dep_tree:
                    # Flatten dependencies for analysis
                    dependencies = self._flatten_dependencies(dep_tree, package_name)
                    print(
                        f"[ai_threat_surface_service] Found {len(dependencies)} dependencies"
                    )
            except Exception as e:
                print(
                    f"[ai_threat_surface_service] WARNING: Could not fetch dependencies: {e}"
                )

            # 4. Get maintainers
            maintainers = []
            try:
                # Get all identities who have published releases for this package
                all_releases = await release_repo.find_by_package(package.id, limit=50)
                identity_ids = set()
                for release in all_releases:
                    if release.published_by:
                        identity_ids.add(release.published_by)

                # Fetch identities by ID
                for identity_id in identity_ids:
                    identity = await identity_repo.find_by_id(identity_id)
                    if identity:
                        maintainers.append(identity)

                print(
                    f"[ai_threat_surface_service] Found {len(maintainers)} maintainers"
                )
            except Exception as e:
                print(
                    f"[ai_threat_surface_service] WARNING: Could not fetch maintainers: {e}"
                )

            # 5. Get previous assessment for context
            previous_assessment = await self.assessment_repo.find_current_by_package(
                package.id
            )

            # 6. Generate assessment
            print(
                f"[ai_threat_surface_service] Generating assessment for {package_name}@{latest_release.version}"
            )
            assessment = await self.generate_assessment(
                package=package,
                release=latest_release,
                dependencies=dependencies,
                maintainers=maintainers,
                previous_assessment=previous_assessment,
            )

            # 7. Save assessment to database
            if assessment:
                await self.assessment_repo.create(assessment)
                print(
                    f"[ai_threat_surface_service] Threat assessment saved for {package_name}@{latest_release.version}"
                )

            return assessment

        except Exception as e:
            print(
                f"[ai_threat_surface_service] ERROR generating assessment for {package_name}: {e}"
            )
            import traceback

            traceback.print_exc()
            return None

    def _flatten_dependencies(
        self, dep_tree: Dict[str, Any], root_package: str
    ) -> List[Dict[str, Any]]:
        """
        Flatten dependency tree for AI analysis.

        Args:
            dep_tree: Dependency tree from database
            root_package: Root package name

        Returns:
            List of dependency dicts with name, version, and depth
        """
        dependencies = []

        def traverse(node: Dict[str, Any], depth: int = 0):
            """Recursively traverse dependency tree."""
            if depth > 2:  # Limit to 2 levels
                return

            # Process each dependency type
            for dep_type in ["dependencies", "devDependencies", "optionalDependencies", "peerDependencies"]:
                deps_dict = node.get(dep_type, {})
                if not isinstance(deps_dict, dict):
                    continue

                for dep_name, dep_info in deps_dict.items():
                    if not isinstance(dep_info, dict):
                        continue

                    dependencies.append(
                        {
                            "name": dep_name,
                            "version": dep_info.get("resolved_version", "unknown"),
                            "depth": depth + 1,
                            "type": dep_type,
                        }
                    )

                    # Traverse children
                    children = dep_info.get("children", {})
                    if children:
                        traverse(children, depth + 1)

        # Start traversal from root
        traverse(dep_tree, depth=0)
        return dependencies

    async def generate_assessment(
        self,
        package: Package,
        release: PackageRelease,
        dependencies: List[Dict[str, Any]],
        maintainers: List[Identity],
        previous_assessment: Optional[PackageThreatAssessment] = None,
    ) -> PackageThreatAssessment:
        """
        Generate comprehensive threat surface assessment.

        Args:
            package: Package being analyzed
            release: Latest release
            dependencies: Dependency tree (2 levels deep)
            maintainers: Package maintainers
            previous_assessment: Previous assessment for evolution comparison

        Returns:
            PackageThreatAssessment with full narrative and structured findings
        """
        try:
            # Create comprehensive prompt
            prompt = self._create_assessment_prompt(
                package=package,
                release=release,
                dependencies=dependencies,
                maintainers=maintainers,
                previous_assessment=previous_assessment,
            )

            # Run AI analysis with timeout (longer for comprehensive analysis)
            response = await asyncio.wait_for(
                self._run_agent_analysis(prompt), timeout=45.0
            )

            # Parse structured response
            assessment_data = self._parse_assessment_response(response)

            # Create PackageThreatAssessment model
            assessment = PackageThreatAssessment(
                package_id=package.id,
                version=release.version,
                assessment_narrative=assessment_data["assessment_narrative"],
                evolution_narrative=assessment_data.get("evolution_narrative", ""),
                overall_risk_level=assessment_data["overall_risk_level"],
                confidence=assessment_data["confidence"],
                key_strengths=assessment_data.get("key_strengths", []),
                key_risks=assessment_data.get("key_risks", []),
                notable_dependencies=assessment_data.get("notable_dependencies", []),
                maintainer_assessment=assessment_data.get("maintainer_assessment", {}),
                dependency_depth_analyzed=2,
                previous_assessment_id=previous_assessment.id
                if previous_assessment
                else None,
            )

            return assessment

        except asyncio.TimeoutError:
            print(
                f"[ai_threat_surface_service] TIMEOUT: Assessment timed out for {package.name}"
            )
            # Return a fallback assessment
            return self._create_fallback_assessment(package, release)
        except Exception as e:
            print(
                f"[ai_threat_surface_service] ERROR: Assessment failed for {package.name}: {e}"
            )
            return self._create_fallback_assessment(package, release)

    async def _run_agent_analysis(self, prompt: str) -> Dict[str, Any]:
        """
        Run agno agent analysis.

        Args:
            prompt: Structured prompt for assessment

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
            print(
                f"[ai_threat_surface_service] WARNING: Failed to parse JSON response: {e}"
            )
            print(f"[ai_threat_surface_service] Response text: {response_text[:500]}")
            raise

    def _create_assessment_prompt(
        self,
        package: Package,
        release: PackageRelease,
        dependencies: List[Dict[str, Any]],
        maintainers: List[Identity],
        previous_assessment: Optional[PackageThreatAssessment],
    ) -> str:
        """
        Create comprehensive assessment prompt.

        Args:
            package: Package information
            release: Release information
            dependencies: Dependency tree
            maintainers: Maintainer list
            previous_assessment: Previous assessment for comparison

        Returns:
            Formatted prompt string
        """
        # Build maintainers section
        maintainers_section = f"MAINTAINERS ({len(maintainers)}):\n"
        for m in maintainers[:5]:  # Top 5 maintainers
            maintainers_section += (
                f"- {m.handle} ({m.kind}): Risk Score {m.risk_score:.1f}, "
            )
            maintainers_section += f"First Seen {m.first_seen}\n"
            if m.affiliation_tag:
                maintainers_section += f"  Affiliation: {m.affiliation_tag}\n"

        # Build dependencies section (separate direct and transitive)
        direct_deps = [d for d in dependencies if d.get("depth", 0) == 1]
        transitive_deps = [d for d in dependencies if d.get("depth", 0) == 2]

        deps_section = f"\nDIRECT DEPENDENCIES ({len(direct_deps)}):\n"
        for dep in direct_deps[:10]:  # Top 10
            deps_section += (
                f"- {dep.get('name', 'Unknown')}@{dep.get('version', 'Unknown')}\n"
            )

        deps_section += (
            f"\nTRANSITIVE DEPENDENCIES (Level 2, {len(transitive_deps)}):\n"
        )
        for dep in transitive_deps[:15]:  # Top 15
            deps_section += f"- {dep.get('name', 'Unknown')}\n"

        # Build recent releases section
        releases_section = f"\nRECENT RELEASE:\n"
        releases_section += (
            f"- {release.version} (published {release.publish_timestamp})\n"
        )
        releases_section += f"  Risk Score: {release.risk_score:.1f}\n"
        if release.previous_version:
            releases_section += f"  Previous: {release.previous_version}\n"

        # Build previous assessment section
        previous_section = ""
        if previous_assessment:
            previous_section = (
                f"\nPREVIOUS ASSESSMENT (from {previous_assessment.timestamp}):\n"
            )
            previous_section += f"- Version: {previous_assessment.version}\n"
            previous_section += (
                f"- Overall Risk: {previous_assessment.overall_risk_level}\n"
            )
            previous_section += f"- Key Findings:\n"
            for strength in previous_assessment.key_strengths[:2]:
                previous_section += f"  + {strength}\n"
            for risk in previous_assessment.key_risks[:2]:
                previous_section += f"  - {risk}\n"
            previous_section += f"\nPrevious Narrative (excerpt):\n{previous_assessment.assessment_narrative[:300]}...\n"

        # Construct full prompt
        prompt = f"""Generate a comprehensive threat surface assessment for this npm package.

PACKAGE: {package.name}
VERSION: {release.version}
REGISTRY: {package.registry}
REPOSITORY: {package.repo_url or "N/A"}

{maintainers_section}

{deps_section}

{releases_section}

{previous_section}

INSTRUCTIONS:
Provide a comprehensive, balanced threat surface assessment that:

1. Names specific dependencies and maintainers when discussing risks or strengths
2. Includes BOTH positive indicators AND concerns (not just threats)
3. Discusses downstream supply chain risks from transitive dependencies
4. Assesses maintainer trustworthiness based on activity, reputation, and community standing
5. Explains HOW the threat picture has evolved since the previous assessment (if applicable)
6. Adopts a realistic, measured tone - not alarmist, but candid about risks

Output ONLY valid JSON in this exact format:
{{
  "assessment_narrative": "2-4 paragraph comprehensive assessment that provides the full security picture...",
  "evolution_narrative": "How this assessment compares to the previous one (if applicable)...",
  "overall_risk_level": "low|medium|high|critical",
  "confidence": 0.0-1.0,
  "key_strengths": [
    "Specific strength 1",
    "Specific strength 2"
  ],
  "key_risks": [
    "Specific risk 1",
    "Specific risk 2"
  ],
  "notable_dependencies": [
    {{
      "name": "package-name",
      "risk": "low|medium|high",
      "reason": "Brief explanation"
    }}
  ],
  "maintainer_assessment": {{
    "overall": "trustworthy|moderate|concerning",
    "details": "Assessment of maintainer activity, reputation, etc."
  }}
}}

IMPORTANT:
- assessment_narrative should be 2-4 paragraphs providing comprehensive analysis
- evolution_narrative should compare current state to previous assessment
- Be specific with package and maintainer names
- Balance strengths and risks
- Focus on realistic assessment, not fear-mongering
"""
        return prompt

    def _parse_assessment_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate assessment response.

        Args:
            response: Raw AI response

        Returns:
            Validated assessment data
        """
        # Validate required fields
        required_fields = ["assessment_narrative", "overall_risk_level", "confidence"]
        for field in required_fields:
            if field not in response:
                raise ValueError(f"Missing required field: {field}")

        # Validate risk level
        valid_risk_levels = ["low", "medium", "high", "critical"]
        if response["overall_risk_level"] not in valid_risk_levels:
            response["overall_risk_level"] = "medium"  # Default

        # Validate confidence
        response["confidence"] = max(0.0, min(1.0, response["confidence"]))

        # Ensure lists exist
        response.setdefault("key_strengths", [])
        response.setdefault("key_risks", [])
        response.setdefault("notable_dependencies", [])
        response.setdefault(
            "maintainer_assessment",
            {
                "overall": "moderate",
                "details": "Insufficient data for detailed assessment",
            },
        )
        response.setdefault("evolution_narrative", "")

        return response

    def _create_fallback_assessment(
        self, package: Package, release: PackageRelease
    ) -> PackageThreatAssessment:
        """
        Create a fallback assessment when AI analysis fails.

        Args:
            package: Package information
            release: Release information

        Returns:
            Basic PackageThreatAssessment
        """
        return PackageThreatAssessment(
            package_id=package.id,
            version=release.version,
            assessment_narrative=f"Automated assessment unavailable for {package.name} {release.version}. "
            f"Manual review recommended. Package has risk score of {package.risk_score:.1f}.",
            evolution_narrative="",
            overall_risk_level="medium" if package.risk_score >= 50 else "low",
            confidence=0.5,
            key_strengths=[],
            key_risks=["Automated assessment failed - manual review needed"],
            notable_dependencies=[],
            maintainer_assessment={
                "overall": "moderate",
                "details": "Insufficient data",
            },
            dependency_depth_analyzed=0,
        )
