"""
PackageDelta model - diff between versions.
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from .analysis import Analysis
from .package import PyObjectId


class Signals(BaseModel):
    """Signals extracted from comparing package versions."""

    added_files: list[str] = Field(default_factory=list)
    removed_files: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    has_install_scripts: bool = Field(default=False)
    touched_install_scripts: bool = Field(default=False)
    has_native_code: bool = Field(default=False)
    added_network_calls: bool = Field(default=False)
    minified_or_obfuscated_delta: bool = Field(default=False)


class PackageDelta(BaseModel):
    """
    Diff between package versions.
    Replaces PRs for MVP - lets you see 'what changed' without GitHub.
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    package_id: PyObjectId = Field(..., description="Package reference")
    from_version: str = Field(..., description="Source version")
    to_version: str = Field(..., description="Target version")
    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="When delta was computed"
    )

    signals: Signals = Field(default_factory=Signals)
    risk_score: float = Field(default=0, ge=0, le=100, description="Risk score 0-100")

    analysis: Analysis

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "package_id": "507f1f77bcf86cd799439011",
                "from_version": "4.18.1",
                "to_version": "4.18.2",
                "computed_at": "2024-01-10T12:00:00Z",
                "signals": {
                    "added_files": ["lib/new-feature.js"],
                    "removed_files": [],
                    "changed_files": ["lib/router.js", "package.json"],
                    "has_install_scripts": False,
                    "touched_install_scripts": False,
                    "has_native_code": False,
                    "added_network_calls": False,
                    "minified_or_obfuscated_delta": False,
                },
                "risk_score": 8.0,
                "analysis": {
                    "summary": "Minor changes to router with new feature addition",
                    "reasons": [
                        "Only production code modified",
                        "No install scripts touched",
                        "Changes align with changelog",
                    ],
                    "confidence": 0.88,
                    "updated_at": "2024-01-10T12:00:00Z",
                    "source": "ai",
                },
            }
        }
