"""Delta API schemas."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class BackfillRequest(BaseModel):
    """Request schema for delta backfill."""

    num_releases: int = Field(
        default=5, ge=1, le=50, description="Number of recent releases to backfill per package (1-50)"
    )


class BackfillResponse(BaseModel):
    """Response schema for delta backfill - returns job ID for tracking."""

    job_id: str
    status: str
    message: str


class BackfillResult(BaseModel):
    """Result schema for completed backfill job."""

    packages_processed: int
    deltas_created: int
    errors: int
    num_releases: int


class JobStatusResponse(BaseModel):
    """Response schema for job status."""

    job_id: str
    type: str
    status: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    progress: Optional[Dict[str, Any]]
    result: Optional[Any]
    error: Optional[str]
