"""
Package Threat Assessment model - comprehensive threat surface analysis.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .package import PyObjectId


class PackageThreatAssessment(BaseModel):
    """
    Comprehensive threat surface assessment for a top-level package.
    Evolves over time with each new release and dependency scan.

    Stores both narrative assessment and structured findings.
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    package_id: PyObjectId = Field(..., description="Package reference")
    version: str = Field(..., description="Package version analyzed")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When assessment was generated"
    )

    # Core Assessment Narrative
    assessment_narrative: str = Field(
        ...,
        description="Comprehensive narrative assessment (2-4 paragraphs)"
    )
    evolution_narrative: str = Field(
        default="",
        description="How the threat surface has evolved since last assessment"
    )
    overall_risk_level: Literal["low", "medium", "high", "critical"] = Field(
        ..., description="Overall risk level"
    )
    confidence: float = Field(
        ..., ge=0, le=1, description="Confidence score 0-1"
    )

    # Structured Findings
    key_strengths: List[str] = Field(
        default_factory=list,
        description="Positive security indicators"
    )
    key_risks: List[str] = Field(
        default_factory=list,
        description="Identified risks"
    )
    notable_dependencies: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Notable downstream packages with risk assessment"
    )
    maintainer_assessment: Dict[str, Any] = Field(
        default_factory=dict,
        description="Assessment of maintainer trustworthiness"
    )

    # Metadata
    dependency_depth_analyzed: int = Field(
        default=2,
        description="How deep dependency analysis went"
    )
    previous_assessment_id: Optional[PyObjectId] = Field(
        default=None,
        description="Reference to previous assessment for comparison"
    )

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        json_schema_extra = {
            "example": {
                "package_id": "507f1f77bcf86cd799439011",
                "version": "2.5.0",
                "timestamp": "2024-01-10T12:00:00Z",
                "assessment_narrative": "Express 2.5.0 represents a mature and well-maintained package with strong security posture. The core team, led by Doug Wilson and maintained by the OpenJS Foundation, has demonstrated consistent commitment to security best practices. The package benefits from extensive community review with over 50,000 weekly downloads and regular security audits. However, the extensive dependency tree (15 direct dependencies, 45 transitive) introduces supply chain risks that require ongoing monitoring.",
                "evolution_narrative": "Since the last assessment (v2.4.0), the threat surface has improved with the resolution of 2 medium-severity vulnerabilities and the addition of automated dependency scanning. The maintainer team expanded by one contributor with strong credentials.",
                "overall_risk_level": "low",
                "confidence": 0.88,
                "key_strengths": [
                    "Maintained by OpenJS Foundation with transparent governance",
                    "Regular security audits and prompt vulnerability patching",
                    "Extensive test coverage and CI/CD pipeline",
                    "Active community with rapid response to security issues"
                ],
                "key_risks": [
                    "Large dependency tree with 45 transitive dependencies",
                    "Dependency 'body-parser' has known performance issues",
                    "No cryptographic signing of releases"
                ],
                "notable_dependencies": [
                    {
                        "name": "body-parser",
                        "risk": "medium",
                        "reason": "Known performance issues, actively maintained but high complexity"
                    },
                    {
                        "name": "cookie-parser",
                        "risk": "low",
                        "reason": "Well-maintained, stable release history"
                    }
                ],
                "maintainer_assessment": {
                    "overall": "trustworthy",
                    "details": "Core maintainer Doug Wilson has 10+ years of consistent contributions with strong community reputation. Package backed by OpenJS Foundation governance structure."
                },
                "dependency_depth_analyzed": 2,
                "previous_assessment_id": "507f1f77bcf86cd799439010"
            }
        }
