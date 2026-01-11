"""
Alert API request/response schemas.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from models.analysis import Analysis
from models.package import PyObjectId


class AlertResponse(BaseModel):
    """
    Alert response enriched with package name.
    """

    id: str = Field(..., description="Alert ID")
    package_id: str = Field(..., description="Package ID reference")
    package_name: str = Field(..., description="Package name (enriched from packages collection)")
    identity_id: Optional[str] = Field(default=None, description="Identity ID if relevant")
    release_id: Optional[str] = Field(default=None, description="Release ID that triggered alert")
    delta_id: Optional[str] = Field(default=None, description="Delta ID that triggered alert")

    reason: str = Field(..., description="Short human-readable reason for alert")
    severity: float = Field(..., ge=0, le=100, description="Severity score 0-100")
    timestamp: datetime = Field(..., description="When alert was created")
    status: Literal["open", "investigated", "resolved"] = Field(..., description="Alert status")

    analysis: Analysis = Field(..., description="Detailed analysis of the alert")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "package_id": "507f1f77bcf86cd799439012",
                "package_name": "express",
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


class ListAlertsResponse(BaseModel):
    """Response for listing alerts with pagination."""

    alerts: List[AlertResponse]
    total: int = Field(..., description="Total number of alerts matching filter")
    skip: int = Field(..., description="Number of alerts skipped")
    limit: int = Field(..., description="Maximum alerts per page")


class UpdateAlertStatusRequest(BaseModel):
    """Request to update alert status."""

    status: Literal["open", "investigated", "resolved"] = Field(
        ..., description="New status for the alert"
    )


class AlertStatsResponse(BaseModel):
    """Dashboard statistics for alerts."""

    total_alerts: int = Field(..., description="Total number of alerts")
    open_alerts: int = Field(..., description="Number of open alerts")
    investigated_alerts: int = Field(..., description="Number of investigated alerts")
    resolved_alerts: int = Field(..., description="Number of resolved alerts")
    high_severity_count: int = Field(
        ..., description="Number of high-severity alerts (>=70)"
    )
    average_severity: float = Field(..., description="Average severity score")
    recent_alerts: List[AlertResponse] = Field(
        ..., description="Most recent alerts (last 5)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_alerts": 42,
                "open_alerts": 15,
                "investigated_alerts": 10,
                "resolved_alerts": 17,
                "high_severity_count": 8,
                "average_severity": 62.5,
                "recent_alerts": [],
            }
        }
