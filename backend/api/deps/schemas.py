from typing import Dict, Optional, Any
from pydantic import BaseModel, Field


class DependencyInfo(BaseModel):
    """Information about a specific dependency."""
    spec: str = Field(..., description="Version specifier like '^1.0.0'")
    resolved_version: str = Field(..., description="Resolved version without specifiers")
    children: Dict = Field(default_factory=dict, description="Nested dependencies")


class FetchDepsRequest(BaseModel):
    """Request to fetch npm dependencies."""
    package: str = Field(..., description="Package name", examples=["express"])
    version: str = Field(..., description="Package version", examples=["4.18.0"])
    depth: int = Field(default=2, ge=0, le=5, description="Maximum recursion depth")


class FetchDepsResponse(BaseModel):
    """Response for deps fetch - returns job ID for tracking (non-blocking)."""
    job_id: str
    status: str
    message: str


class DepsResult(BaseModel):
    """Result schema for completed deps fetch job."""
    name: Optional[str] = Field(None, description="Package name")
    version: Optional[str] = Field(None, description="Package version")
    description: Optional[str] = Field(None, description="Package description")
    dependencies: Dict[str, DependencyInfo] = Field(default_factory=dict)
    devDependencies: Dict[str, DependencyInfo] = Field(default_factory=dict)
    optionalDependencies: Dict[str, DependencyInfo] = Field(default_factory=dict)
    peerDependencies: Dict[str, DependencyInfo] = Field(default_factory=dict)
    error: Optional[str] = Field(None, description="Error message if fetch failed")


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