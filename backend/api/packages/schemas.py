"""
Package API request/response schemas.
"""

from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from models.package import Package


class CreatePackageRequest(BaseModel):
    """Request to create a package by npm name."""

    package_name: str = Field(..., min_length=1, description="npm package name")


class PackageWithLatestRelease(Package):
    """Package with additional latest release information."""

    latest_release_date: Optional[datetime] = Field(
        default=None, description="Timestamp of the most recent release"
    )
    latest_release_version: Optional[str] = Field(
        default=None, description="Version string of the most recent release"
    )


class ListPackagesResponse(BaseModel):
    """Response for listing packages with pagination."""

    packages: List[PackageWithLatestRelease]
    total: int
    skip: int
    limit: int
