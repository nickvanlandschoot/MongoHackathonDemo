"""
AI Analysis History model - stores analysis memory for context building.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .package import PyObjectId


class AIAnalysisHistory(BaseModel):
    """
    Stores historical analysis data for per-package memory/context.
    Used by AI services to build evolving understanding over time.
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    package_id: PyObjectId = Field(..., description="Package reference")
    release_id: Optional[PyObjectId] = Field(
        default=None, description="Release that triggered this analysis"
    )
    delta_id: Optional[PyObjectId] = Field(
        default=None, description="Delta analyzed (if applicable)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When analysis was performed"
    )

    # Analysis summary
    analysis_summary: str = Field(
        ..., description="Brief summary of the analysis findings"
    )
    alerts_generated: int = Field(
        default=0, description="Number of alerts created from this analysis"
    )
    key_findings: List[str] = Field(
        default_factory=list,
        description="Key findings from this analysis (max 5)",
    )
    confidence: float = Field(
        ..., ge=0, le=1, description="Average confidence score of analysis"
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
                "release_id": "507f1f77bcf86cd799439012",
                "timestamp": "2024-01-10T12:00:00Z",
                "analysis_summary": "High-risk release with obfuscated code patterns detected",
                "alerts_generated": 2,
                "key_findings": [
                    "Obfuscated code in new install script",
                    "First-time maintainer with low reputation",
                    "Unusual network call patterns"
                ],
                "confidence": 0.85,
            }
        }
