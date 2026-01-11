"""
Threat Surface API request/response schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ThreatAssessmentResponse(BaseModel):
    """
    Threat assessment response enriched with package name.
    """

    id: str = Field(..., description="Assessment ID")
    package_id: str = Field(..., description="Package reference")
    package_name: str = Field(..., description="Package name (enriched)")
    version: str = Field(..., description="Package version analyzed")
    timestamp: datetime = Field(..., description="When assessment was generated")

    # Core Assessment Narrative
    assessment_narrative: str = Field(
        ..., description="Comprehensive narrative assessment (2-4 paragraphs)"
    )
    evolution_narrative: str = Field(
        default="", description="How the threat surface has evolved since last assessment"
    )
    overall_risk_level: Literal["low", "medium", "high", "critical"] = Field(
        ..., description="Overall risk level"
    )
    confidence: float = Field(..., ge=0, le=1, description="Confidence score 0-1")

    # Structured Findings
    key_strengths: List[str] = Field(
        default_factory=list, description="Positive security indicators"
    )
    key_risks: List[str] = Field(default_factory=list, description="Identified risks")
    notable_dependencies: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Notable downstream packages with risk assessment",
    )
    maintainer_assessment: Dict[str, Any] = Field(
        default_factory=dict, description="Assessment of maintainer trustworthiness"
    )

    # Metadata
    dependency_depth_analyzed: int = Field(
        default=2, description="How deep dependency analysis went"
    )
    previous_assessment_id: Optional[str] = Field(
        default=None, description="Reference to previous assessment for comparison"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "package_id": "507f1f77bcf86cd799439010",
                "package_name": "express",
                "version": "4.18.2",
                "timestamp": "2024-01-10T12:00:00Z",
                "assessment_narrative": "Express 4.18.2 represents a mature and well-maintained package with strong security posture.",
                "evolution_narrative": "Since the last assessment, the threat surface has improved.",
                "overall_risk_level": "low",
                "confidence": 0.88,
                "key_strengths": [
                    "Maintained by OpenJS Foundation",
                    "Regular security audits",
                ],
                "key_risks": ["Large dependency tree"],
                "notable_dependencies": [
                    {
                        "name": "body-parser",
                        "risk": "medium",
                        "reason": "Known performance issues",
                    }
                ],
                "maintainer_assessment": {"overall": "trustworthy"},
                "dependency_depth_analyzed": 2,
                "previous_assessment_id": None,
            }
        }


class AssessmentHistoryResponse(BaseModel):
    """
    Response for assessment history endpoint.
    """

    assessments: List[ThreatAssessmentResponse] = Field(
        ..., description="List of historical assessments"
    )
    total: int = Field(..., description="Total number of assessments")
    package_name: str = Field(..., description="Package name")

    class Config:
        json_schema_extra = {
            "example": {
                "assessments": [],
                "total": 5,
                "package_name": "express",
            }
        }


class ThreatSurfaceStatsResponse(BaseModel):
    """
    System-wide threat surface statistics.
    """

    total_assessments: int = Field(..., description="Total number of assessments")
    by_risk_level: Dict[str, int] = Field(
        ..., description="Breakdown by risk level (low/medium/high/critical)"
    )
    packages_assessed: int = Field(
        ..., description="Number of unique packages assessed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_assessments": 150,
                "by_risk_level": {"low": 80, "medium": 50, "high": 15, "critical": 5},
                "packages_assessed": 120,
            }
        }


class CurrentAssessmentResponse(BaseModel):
    """
    Wrapper response for current assessment endpoint.
    Distinguishes between 'not generated yet' vs 'error'.
    """

    status: Literal["available", "not_generated", "generating"] = Field(
        ..., description="Assessment availability status"
    )
    assessment: Optional[ThreatAssessmentResponse] = Field(
        default=None, description="Assessment data if available"
    )
    message: Optional[str] = Field(
        default=None, description="Human-readable message"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "available",
                "assessment": {
                    "id": "507f1f77bcf86cd799439011",
                    "package_name": "express",
                    "version": "4.18.2",
                    "overall_risk_level": "low",
                },
                "message": None,
            }
        }


class GenerateAssessmentResponse(BaseModel):
    """
    Response for triggering manual assessment generation.
    """

    job_id: str = Field(..., description="Job ID for polling status")
    status: str = Field(..., description="Job status (pending, running, etc.)")
    message: str = Field(..., description="Human-readable message")
    package_name: str = Field(..., description="Package name")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "abc-123-def-456",
                "status": "pending",
                "message": "Threat assessment generation started. This may take several minutes.",
                "package_name": "express",
            }
        }
