"""
Dependency model - package graph edges.
"""

from datetime import datetime
from typing import Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from .analysis import Analysis
from .package import PyObjectId


class ScanState(BaseModel):
    """Scan state for dependencies."""

    child_scanned: bool = Field(default=False)
    last_scanned: Optional[datetime] = Field(default=None)


class Dependency(BaseModel):
    """Package graph edge representing a dependency relationship."""

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    package_id: PyObjectId = Field(..., description="Dependent package")
    depends_on_id: PyObjectId = Field(..., description="Dependency package")
    spec: str = Field(..., description="Version spec like '^4.0.0' or '>=1 <2'")
    dep_type: Literal["prod", "dev", "optional", "peer"] = Field(
        ..., description="Dependency type"
    )
    depth: int = Field(..., ge=0, description="Dependency depth in graph")
    last_analyzed: Optional[datetime] = Field(default=None)

    scan_state: ScanState = Field(default_factory=ScanState)
    analysis: Analysis

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "package_id": "507f1f77bcf86cd799439011",
                "depends_on_id": "507f1f77bcf86cd799439012",
                "spec": "^4.18.0",
                "dep_type": "prod",
                "depth": 1,
                "last_analyzed": "2024-01-10T12:00:00Z",
                "scan_state": {
                    "child_scanned": True,
                    "last_scanned": "2024-01-10T12:00:00Z",
                },
                "analysis": {
                    "summary": "Production dependency with high runtime relevance",
                    "reasons": [
                        "Core framework dependency",
                        "Used in main application path",
                        "No known vulnerabilities",
                    ],
                    "confidence": 0.9,
                    "updated_at": "2024-01-10T12:00:00Z",
                    "source": "hybrid",
                    "usage_likelihood": 0.95,
                    "runtime_relevance": True,
                },
            }
        }
