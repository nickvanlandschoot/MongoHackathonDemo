"""
PackageRelease model - primary event stream for npm.
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from .analysis import Analysis
from .package import PyObjectId


class PackageRelease(BaseModel):
    """
    Core event stream for npm releases.
    Primary 'watcher' feed for monitoring packages.
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    package_id: PyObjectId = Field(..., description="Package reference")
    version: str = Field(..., description="Release version")
    previous_version: Optional[str] = Field(
        default=None, description="Previous version for comparison"
    )
    published_by: Optional[PyObjectId] = Field(
        default=None, description="Identity who published (if resolved)"
    )
    publish_timestamp: datetime = Field(..., description="When package was published")
    tarball_integrity: Optional[str] = Field(
        default=None, description="npm integrity / shasum"
    )
    dist_tags: Optional[dict[str, str]] = Field(
        default=None, description="Distribution tags like latest, next, etc."
    )
    risk_score: float = Field(default=0, ge=0, le=100, description="Risk score 0-100")

    analysis: Analysis

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "package_id": "507f1f77bcf86cd799439011",
                "version": "4.18.2",
                "previous_version": "4.18.1",
                "published_by": "507f1f77bcf86cd799439012",
                "publish_timestamp": "2024-01-10T12:00:00Z",
                "tarball_integrity": "sha512-abc123...",
                "dist_tags": {"latest": "4.18.2", "next": "5.0.0-beta.1"},
                "risk_score": 10.0,
                "analysis": {
                    "summary": "Routine patch release from verified maintainer",
                    "reasons": [
                        "Published by known maintainer",
                        "Follows semantic versioning",
                        "No suspicious changes detected",
                    ],
                    "confidence": 0.92,
                    "updated_at": "2024-01-10T12:00:00Z",
                    "source": "hybrid",
                },
            }
        }
