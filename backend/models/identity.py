"""
Identity model - contributors/maintainers (npm-first).
"""

from datetime import datetime
from typing import Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from .analysis import Analysis
from .package import PyObjectId


class Identity(BaseModel):
    """
    Identity representing npm maintainers, GitHub contributors, etc.
    Renamed from 'contributor' to better reflect npm-centric model.
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    kind: Literal["npm", "github", "email_domain"] = Field(
        ..., description="Type of identity"
    )
    handle: str = Field(..., description="npm username or GitHub username")
    email_domain: Optional[str] = Field(default=None)
    affiliation_tag: str = Field(
        ..., description="Affiliation type: corporate, academic, anonymous, etc."
    )
    country: Optional[str] = Field(default=None)
    first_seen: datetime = Field(
        default_factory=datetime.utcnow, description="First time identity was observed"
    )
    risk_score: float = Field(default=0, ge=0, le=100, description="Risk score 0-100")

    analysis: Analysis

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "kind": "npm",
                "handle": "sindresorhus",
                "email_domain": "sindresorhus.com",
                "affiliation_tag": "corporate",
                "country": "NO",
                "first_seen": "2020-01-01T00:00:00Z",
                "risk_score": 5.0,
                "analysis": {
                    "summary": "Highly trusted prolific open source maintainer",
                    "reasons": [
                        "Maintains 1000+ packages",
                        "Verified identity",
                        "Long history of quality contributions",
                    ],
                    "confidence": 0.98,
                    "updated_at": "2024-01-10T12:00:00Z",
                    "source": "hybrid",
                },
            }
        }
