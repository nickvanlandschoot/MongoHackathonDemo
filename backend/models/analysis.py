"""
Analysis block model used across all entities.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Analysis(BaseModel):
    """
    Standard analysis block embedded in all documents.
    Keeps semantics consistent and UI-friendly.
    """

    summary: str = Field(..., description="Always present summary of analysis")
    reasons: list[str] = Field(
        default_factory=list, description="Short bullet facts the model relied on"
    )
    confidence: float = Field(..., ge=0, le=1, description="Confidence score 0-1")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When analysis was last updated"
    )
    source: Literal["ai", "rule", "hybrid"] = Field(
        ..., description="Source of the analysis"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "summary": "Package shows low risk with stable maintainer history",
                "reasons": [
                    "Maintained by verified organization",
                    "No recent security advisories",
                    "Consistent release cadence",
                ],
                "confidence": 0.85,
                "updated_at": "2024-01-10T12:00:00Z",
                "source": "hybrid",
            }
        }
