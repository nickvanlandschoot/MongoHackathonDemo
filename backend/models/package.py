"""
Package model - top-level npm packages.
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from .analysis import Analysis


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, _):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {"type": "string"}


class ScanState(BaseModel):
    """Scan state tracking for packages."""

    deps_crawled: bool = Field(default=False)
    releases_crawled: bool = Field(default=False)
    maintainers_crawled: bool = Field(default=False)
    last_full_scan: Optional[datetime] = Field(default=None)
    crawl_depth: int = Field(default=0)


class Package(BaseModel):
    """Top-level npm package representation."""

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str = Field(..., description="Package name")
    registry: str = Field(default="npm", description="Package registry")
    repo_url: Optional[str] = Field(default=None, description="GitHub URL when known")
    owner: Optional[str] = Field(default=None, description="Package owner")
    last_scanned: Optional[datetime] = Field(default=None)
    risk_score: float = Field(default=0, ge=0, le=100, description="Risk score 0-100")
    is_dependency: bool = Field(default=False, description="True if package was discovered as a dependency, not manually added")

    scan_state: ScanState = Field(default_factory=ScanState)
    analysis: Analysis

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "name": "express",
                "registry": "npm",
                "repo_url": "https://github.com/expressjs/express",
                "owner": "expressjs",
                "last_scanned": "2024-01-10T12:00:00Z",
                "risk_score": 15.5,
                "scan_state": {
                    "deps_crawled": True,
                    "releases_crawled": True,
                    "maintainers_crawled": True,
                    "last_full_scan": "2024-01-10T12:00:00Z",
                    "crawl_depth": 2,
                },
                "analysis": {
                    "summary": "Widely-used web framework with active maintenance",
                    "reasons": [
                        "Over 30M weekly downloads",
                        "Verified maintainers",
                        "Regular security updates",
                    ],
                    "confidence": 0.95,
                    "updated_at": "2024-01-10T12:00:00Z",
                    "source": "hybrid",
                },
            }
        }
