"""
GitHubEvent model - optional GitHub enrichment.
"""

from datetime import datetime
from typing import Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from .analysis import Analysis
from .package import PyObjectId


class GitHubEvent(BaseModel):
    """
    Optional GitHub enrichment data.
    Kept separate from core npm-based monitoring.
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    package_id: PyObjectId = Field(..., description="Package reference")
    type: Literal["pr", "commit", "release", "security_advisory"] = Field(
        ..., description="Event type"
    )
    url: str = Field(..., description="GitHub URL for the event")
    actor: Optional[str] = Field(default=None, description="GitHub actor/user")
    timestamp: datetime = Field(..., description="When event occurred")

    analysis: Analysis

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "package_id": "507f1f77bcf86cd799439011",
                "type": "security_advisory",
                "url": "https://github.com/expressjs/express/security/advisories/GHSA-xxxx",
                "actor": "expressjs-bot",
                "timestamp": "2024-01-10T12:00:00Z",
                "analysis": {
                    "summary": "Security advisory for prototype pollution vulnerability",
                    "reasons": [
                        "CVE assigned",
                        "Patch available in latest version",
                        "Low severity rating",
                    ],
                    "confidence": 1.0,
                    "updated_at": "2024-01-10T12:00:00Z",
                    "source": "rule",
                },
            }
        }
