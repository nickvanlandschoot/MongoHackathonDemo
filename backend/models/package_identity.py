"""
PackageIdentity model - who can ship what.
"""

from datetime import datetime
from typing import Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from .analysis import Analysis
from .package import PyObjectId


class PackageIdentity(BaseModel):
    """
    Links identities to packages with permissions.
    Replaces package_contributors with npm-accurate model.
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    package_id: PyObjectId = Field(..., description="Package reference")
    identity_id: PyObjectId = Field(..., description="Identity reference")
    role: str = Field(..., description="Role: owner, maintainer, contributor")
    permission_level: Literal["publish", "triage", "unknown"] = Field(
        ..., description="Permission level"
    )
    first_seen: datetime = Field(
        default_factory=datetime.utcnow, description="When this relationship was first observed"
    )
    last_seen: datetime = Field(
        default_factory=datetime.utcnow, description="When this relationship was last confirmed"
    )
    trust_score: float = Field(
        default=50, ge=0, le=100, description="Trust score 0-100"
    )

    analysis: Analysis

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "package_id": "507f1f77bcf86cd799439011",
                "identity_id": "507f1f77bcf86cd799439012",
                "role": "owner",
                "permission_level": "publish",
                "first_seen": "2020-01-01T00:00:00Z",
                "last_seen": "2024-01-10T12:00:00Z",
                "trust_score": 95.0,
                "analysis": {
                    "summary": "Original package creator with full publish rights",
                    "reasons": [
                        "Package creator",
                        "Consistent maintenance history",
                        "No suspicious activity",
                    ],
                    "confidence": 0.95,
                    "updated_at": "2024-01-10T12:00:00Z",
                    "source": "rule",
                },
            }
        }
