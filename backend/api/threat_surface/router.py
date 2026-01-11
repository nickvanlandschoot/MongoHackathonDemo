"""
Threat Surface API router.
"""

import asyncio
import os
from typing import List
from urllib.parse import unquote

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from api.threat_surface.schemas import (
    AssessmentHistoryResponse,
    CurrentAssessmentResponse,
    GenerateAssessmentResponse,
    ThreatAssessmentResponse,
    ThreatSurfaceStatsResponse,
)
from database import get_database
from repositories.package import PackageRepository
from repositories.package_threat_assessment import PackageThreatAssessmentRepository
from services.background_jobs import get_job_manager
from services.ai_threat_surface_service import AIThreatSurfaceService

router = APIRouter(
    prefix="/threat-surface",
    tags=["threat-surface"],
)


def get_package_repository() -> PackageRepository:
    """Dependency injection for PackageRepository."""
    return PackageRepository(get_database())


def get_threat_assessment_repository() -> PackageThreatAssessmentRepository:
    """Dependency injection for PackageThreatAssessmentRepository."""
    return PackageThreatAssessmentRepository(get_database())


@router.get("/package/{package_name}", response_model=CurrentAssessmentResponse)
async def get_current_assessment(
    package_name: str,
    package_repo: PackageRepository = Depends(get_package_repository),
    assessment_repo: PackageThreatAssessmentRepository = Depends(
        get_threat_assessment_repository
    ),
):
    """
    Get the most recent threat assessment for a package.

    Returns a wrapper response indicating whether an assessment is available,
    not generated yet, or currently being generated.

    Args:
        package_name: Package name (supports scoped packages like @scope/package)

    Returns:
        CurrentAssessmentResponse with status and optional assessment data

    Example:
        GET /api/threat-surface/package/express
        GET /api/threat-surface/package/@scope/package
    """
    # URL-decode to handle scoped packages
    package_name = unquote(package_name)

    # Get package
    package = await package_repo.find_by_name(package_name)
    if not package:
        raise HTTPException(
            status_code=404, detail=f"Package '{package_name}' not found"
        )

    if not package.id:
        raise HTTPException(status_code=500, detail="Package ID is missing")

    # Get most recent assessment
    assessment = await assessment_repo.find_current_by_package(package.id)

    if not assessment:
        # No assessment exists yet - return not_generated status
        return CurrentAssessmentResponse(
            status="not_generated",
            assessment=None,
            message=f"No threat assessment has been generated for '{package_name}' yet. "
                    f"Assessments are generated automatically when releases are detected, "
                    f"or you can trigger manual generation."
        )

    # Enrich response with package name
    assessment_dict = assessment.model_dump()
    assessment_dict["id"] = str(assessment.id)
    assessment_dict["package_id"] = str(assessment.package_id)
    assessment_dict["package_name"] = package.name
    if assessment.previous_assessment_id:
        assessment_dict["previous_assessment_id"] = str(
            assessment.previous_assessment_id
        )

    return CurrentAssessmentResponse(
        status="available",
        assessment=ThreatAssessmentResponse(**assessment_dict),
        message=None
    )


@router.get(
    "/package/{package_name}/history", response_model=AssessmentHistoryResponse
)
async def get_assessment_history(
    package_name: str,
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of assessments to return"
    ),
    package_repo: PackageRepository = Depends(get_package_repository),
    assessment_repo: PackageThreatAssessmentRepository = Depends(
        get_threat_assessment_repository
    ),
):
    """
    Get historical threat assessments for a package.

    Returns a list of assessments ordered by timestamp (newest first).

    Args:
        package_name: Package name (supports scoped packages)
        limit: Maximum number of assessments to return (default 10, max 100)

    Returns:
        AssessmentHistoryResponse with list of assessments

    Example:
        GET /api/threat-surface/package/express/history?limit=20
    """
    # URL-decode to handle scoped packages
    package_name = unquote(package_name)

    # Get package
    package = await package_repo.find_by_name(package_name)
    if not package:
        raise HTTPException(
            status_code=404, detail=f"Package '{package_name}' not found"
        )

    if not package.id:
        raise HTTPException(status_code=500, detail="Package ID is missing")

    # Get historical assessments
    assessments = await assessment_repo.find_by_package(package.id, limit=limit)

    # Enrich each assessment with package name
    enriched_assessments = []
    for assessment in assessments:
        assessment_dict = assessment.model_dump()
        assessment_dict["id"] = str(assessment.id)
        assessment_dict["package_id"] = str(assessment.package_id)
        assessment_dict["package_name"] = package.name
        if assessment.previous_assessment_id:
            assessment_dict["previous_assessment_id"] = str(
                assessment.previous_assessment_id
            )
        enriched_assessments.append(ThreatAssessmentResponse(**assessment_dict))

    return AssessmentHistoryResponse(
        assessments=enriched_assessments,
        total=len(enriched_assessments),
        package_name=package.name,
    )


@router.get(
    "/package/{package_name}/version/{version}",
    response_model=ThreatAssessmentResponse,
)
async def get_assessment_by_version(
    package_name: str,
    version: str,
    package_repo: PackageRepository = Depends(get_package_repository),
    assessment_repo: PackageThreatAssessmentRepository = Depends(
        get_threat_assessment_repository
    ),
):
    """
    Get threat assessment for a specific package version.

    Retrieves the assessment for a particular version of the package.

    Args:
        package_name: Package name (supports scoped packages)
        version: Specific version string

    Returns:
        ThreatAssessmentResponse for the specified version

    Example:
        GET /api/threat-surface/package/express/version/4.18.2
    """
    # URL-decode to handle scoped packages and version strings
    package_name = unquote(package_name)
    version = unquote(version)

    # Get package
    package = await package_repo.find_by_name(package_name)
    if not package:
        raise HTTPException(
            status_code=404, detail=f"Package '{package_name}' not found"
        )

    if not package.id:
        raise HTTPException(status_code=500, detail="Package ID is missing")

    # Get assessment for specific version
    assessment = await assessment_repo.find_by_version(package.id, version)
    if not assessment:
        raise HTTPException(
            status_code=404,
            detail=f"No threat assessment found for {package_name}@{version}",
        )

    # Enrich response with package name
    assessment_dict = assessment.model_dump()
    assessment_dict["id"] = str(assessment.id)
    assessment_dict["package_id"] = str(assessment.package_id)
    assessment_dict["package_name"] = package.name
    if assessment.previous_assessment_id:
        assessment_dict["previous_assessment_id"] = str(
            assessment.previous_assessment_id
        )

    return ThreatAssessmentResponse(**assessment_dict)


@router.post(
    "/generate/{package_name}", response_model=GenerateAssessmentResponse
)
async def generate_assessment(
    package_name: str,
    package_repo: PackageRepository = Depends(get_package_repository),
):
    """
    Trigger manual threat assessment generation (non-blocking).

    Queues a background job to generate a comprehensive threat surface assessment
    for the specified package. Returns immediately with a job ID for polling.

    Note: This endpoint creates a job but does not implement the actual assessment
    generation logic. The assessment service integration should be added separately.

    Args:
        package_name: Package name (supports scoped packages)

    Returns:
        GenerateAssessmentResponse with job ID for polling status

    Example:
        POST /api/threat-surface/generate/express

        Response:
        {
            "job_id": "abc-123-def-456",
            "status": "pending",
            "message": "Threat assessment generation started...",
            "package_name": "express"
        }
    """
    # URL-decode to handle scoped packages
    package_name = unquote(package_name)

    # Verify package exists
    package = await package_repo.find_by_name(package_name)
    if not package:
        raise HTTPException(
            status_code=404, detail=f"Package '{package_name}' not found"
        )

    # Create background job
    job_manager = get_job_manager()
    job_id = job_manager.create_job(
        job_type="threat_assessment",
        metadata={"package_name": package_name, "package_id": str(package.id)},
    )

    # Define the assessment coroutine
    async def run_assessment():
        """Background task to generate threat assessment."""
        # Check if OpenRouter API key is available
        OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
        if not OPENROUTER_API_KEY:
            raise ValueError("OpenRouter API key not configured")

        # Initialize service and generate assessment
        db = get_database()
        threat_service = AIThreatSurfaceService(db, OPENROUTER_API_KEY)
        assessment = await threat_service.generate_assessment_for_package(package_name)

        if not assessment:
            raise ValueError("Failed to generate threat assessment - no release found")

        # Return result
        return {
            "assessment_id": str(assessment.id),
            "package_name": package_name,
            "version": assessment.version,
            "risk_level": assessment.overall_risk_level,
        }

    # Start the background job (it will manage status internally)
    job_manager.start_job(job_id, run_assessment())

    return GenerateAssessmentResponse(
        job_id=job_id,
        status="pending",
        message=f"Threat assessment generation started. This may take several minutes. Poll /deps/jobs/{job_id} for status.",
        package_name=package_name,
    )


@router.get("/stats", response_model=ThreatSurfaceStatsResponse)
async def get_threat_surface_stats(
    assessment_repo: PackageThreatAssessmentRepository = Depends(
        get_threat_assessment_repository
    ),
):
    """
    Get system-wide threat surface statistics.

    Returns aggregate statistics about all threat assessments in the system,
    including counts by risk level and total packages assessed.

    Returns:
        ThreatSurfaceStatsResponse with system-wide statistics

    Example:
        GET /api/threat-surface/stats

        Response:
        {
            "total_assessments": 150,
            "by_risk_level": {
                "low": 80,
                "medium": 50,
                "high": 15,
                "critical": 5
            },
            "packages_assessed": 120
        }
    """
    # Get statistics from repository
    stats = await assessment_repo.get_stats()

    # Calculate unique packages assessed by counting distinct package_ids
    db = get_database()
    packages_assessed = len(
        await db.package_threat_assessments.distinct("package_id")
    )

    return ThreatSurfaceStatsResponse(
        total_assessments=stats.get("total", 0),
        by_risk_level=stats.get("by_risk_level", {}),
        packages_assessed=packages_assessed,
    )
