from typing import Dict, Optional
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
    """Response with npm dependency tree."""
    name: Optional[str] = Field(None, description="Package name")
    version: Optional[str] = Field(None, description="Package version")
    description: Optional[str] = Field(None, description="Package description")
    dependencies: Dict[str, DependencyInfo] = Field(default_factory=dict)
    devDependencies: Dict[str, DependencyInfo] = Field(default_factory=dict)
    optionalDependencies: Dict[str, DependencyInfo] = Field(default_factory=dict)
    peerDependencies: Dict[str, DependencyInfo] = Field(default_factory=dict)
    error: Optional[str] = Field(None, description="Error message if fetch failed")