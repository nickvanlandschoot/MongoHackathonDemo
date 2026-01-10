"""
RiskAlert model - security decisions and alerts.
"""

from datetime import datetime
from typing import Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from .analysis import Analysis
from .package import PyObjectId


class RiskAlert(BaseModel):
    """
    Risk alerts always point to the specific event that triggered them
    (release and/or delta), plus the package.
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    package_id: PyObjectId = Field(..., description="Package reference")
    identity_id: Optional[PyObjectId] = Field(
        default=None, description="Identity reference if relevant"
    )
    release_id: Optional[PyObjectId] = Field(
        default=None, description="Release that triggered alert"
    )
    delta_id: Optional[PyObjectId] = Field(
        default=None, description="Delta that triggered alert"
    )

    reason: str = Field(..., description="Short human-readable reason")
    severity: float = Field(..., ge=0, le=100, description="Severity score 0-100")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When alert was created"
    )
    status: Literal["open", "investigated", "resolved"] = Field(
        default="open", description="Alert status"
    )

    analysis: Analysis

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "package_id": "507f1f77bcf86cd799439011",
                "identity_id": None,
                "release_id": "507f1f77bcf86cd799439013",
                "delta_id": "507f1f77bcf86cd799439014",
                "reason": "Obfuscated code added in patch release",
                "severity": 85.0,
                "timestamp": "2024-01-10T12:00:00Z",
                "status": "open",
                "analysis": {
                    "summary": "High-risk obfuscated code introduced without explanation",
                    "reasons": [
                        "Minified code added to non-minified package",
                        "No corresponding changelog entry",
                        "Published outside normal release schedule",
                    ],
                    "confidence": 0.91,
                    "updated_at": "2024-01-10T12:00:00Z",
                    "source": "hybrid",
                },
            }
        }
