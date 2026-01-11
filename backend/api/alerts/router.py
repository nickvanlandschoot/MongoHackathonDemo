"""
Alert API router.
"""

import asyncio
from typing import Optional, Literal
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId

from api.alerts.schemas import (
    AlertResponse,
    ListAlertsResponse,
    UpdateAlertStatusRequest,
    AlertStatsResponse,
)
from database import get_database
from repositories.risk_alert import RiskAlertRepository
from repositories.package import PackageRepository

router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
)


def get_alert_repository() -> RiskAlertRepository:
    """Dependency injection for RiskAlertRepository."""
    return RiskAlertRepository(get_database())


def get_package_repository() -> PackageRepository:
    """Dependency injection for PackageRepository."""
    return PackageRepository(get_database())


async def enrich_alert_with_package_name(
    alert: dict, package_repo: PackageRepository
) -> AlertResponse:
    """
    Enrich alert with package name from packages collection.

    Args:
        alert: Alert document from database
        package_repo: Package repository instance

    Returns:
        AlertResponse with package_name populated
    """
    # Get package name
    package = await package_repo.find_by_id(alert["package_id"])
    package_name = package.name if package else "unknown"

    # Convert ObjectIds to strings
    alert_dict = {
        "id": str(alert["_id"]),
        "package_id": str(alert["package_id"]),
        "package_name": package_name,
        "identity_id": str(alert["identity_id"]) if alert.get("identity_id") else None,
        "release_id": str(alert["release_id"]) if alert.get("release_id") else None,
        "delta_id": str(alert["delta_id"]) if alert.get("delta_id") else None,
        "reason": alert["reason"],
        "severity": alert["severity"],
        "timestamp": alert["timestamp"],
        "status": alert["status"],
        "analysis": alert["analysis"],
    }

    return AlertResponse(**alert_dict)


@router.get("/", response_model=ListAlertsResponse)
async def list_alerts(
    skip: int = Query(0, ge=0, description="Number of alerts to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum alerts to return"),
    status: Optional[Literal["open", "investigated", "resolved"]] = Query(
        None, description="Filter by status"
    ),
    severity_min: Optional[float] = Query(
        None, ge=0, le=100, description="Minimum severity score"
    ),
    package_name: Optional[str] = Query(None, description="Filter by package name"),
    alert_repo: RiskAlertRepository = Depends(get_alert_repository),
    package_repo: PackageRepository = Depends(get_package_repository),
):
    """
    List alerts with filtering and pagination.

    Filters:
    - status: Filter by alert status (open, investigated, resolved)
    - severity_min: Filter by minimum severity score
    - package_name: Filter by package name

    Results are sorted by timestamp (newest first).
    """
    # Build filter query
    filter_query = {}

    if status:
        filter_query["status"] = status

    if severity_min is not None:
        filter_query["severity"] = {"$gte": severity_min}

    # If package_name filter is provided, resolve package_id first
    if package_name:
        package_name = unquote(package_name)
        package = await package_repo.find_by_name(package_name)
        if not package:
            # No alerts if package doesn't exist
            return ListAlertsResponse(alerts=[], total=0, skip=skip, limit=limit)
        filter_query["package_id"] = package.id

    # Get alerts
    alerts = await alert_repo.find_many(
        filter_query, skip=skip, limit=limit, sort=[("timestamp", -1)]
    )
    total = await alert_repo.count(filter_query)

    # Enrich with package names
    enriched_alerts = []
    for alert in alerts:
        alert_dict = alert.model_dump(by_alias=True)
        enriched_alert = await enrich_alert_with_package_name(alert_dict, package_repo)
        enriched_alerts.append(enriched_alert)

    return ListAlertsResponse(
        alerts=enriched_alerts,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    alert_repo: RiskAlertRepository = Depends(get_alert_repository),
    package_repo: PackageRepository = Depends(get_package_repository),
):
    """
    Get dashboard statistics for alerts.

    Returns summary counts by status, severity metrics, and recent alerts.
    """
    # Get counts by status
    total_alerts = await alert_repo.count()
    open_alerts = await alert_repo.count({"status": "open"})
    investigated_alerts = await alert_repo.count({"status": "investigated"})
    resolved_alerts = await alert_repo.count({"status": "resolved"})

    # Get high severity count
    high_severity_count = await alert_repo.count({"severity": {"$gte": 70.0}})

    # Calculate average severity using aggregation
    db = alert_repo.database
    pipeline = [
        {"$group": {"_id": None, "avg_severity": {"$avg": "$severity"}}},
    ]
    result = await asyncio.to_thread(
        lambda: list(db.risk_alerts.aggregate(pipeline))
    )
    average_severity = result[0]["avg_severity"] if result else 0.0

    # Get recent alerts (last 5)
    recent_alert_docs = await alert_repo.find_many(
        {}, skip=0, limit=5, sort=[("timestamp", -1)]
    )

    # Enrich recent alerts
    recent_alerts = []
    for alert in recent_alert_docs:
        alert_dict = alert.model_dump(by_alias=True)
        enriched_alert = await enrich_alert_with_package_name(alert_dict, package_repo)
        recent_alerts.append(enriched_alert)

    return AlertStatsResponse(
        total_alerts=total_alerts,
        open_alerts=open_alerts,
        investigated_alerts=investigated_alerts,
        resolved_alerts=resolved_alerts,
        high_severity_count=high_severity_count,
        average_severity=round(average_severity, 2) if average_severity else 0.0,
        recent_alerts=recent_alerts,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    alert_repo: RiskAlertRepository = Depends(get_alert_repository),
    package_repo: PackageRepository = Depends(get_package_repository),
):
    """
    Get a single alert by ID.

    Returns 404 if alert not found.
    """
    # Validate ObjectId format
    if not ObjectId.is_valid(alert_id):
        raise HTTPException(status_code=400, detail="Invalid alert ID format")

    # Find alert
    alert = await alert_repo.find_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

    # Enrich with package name
    alert_dict = alert.model_dump(by_alias=True)
    return await enrich_alert_with_package_name(alert_dict, package_repo)


@router.get("/package/{package_name:path}", response_model=ListAlertsResponse)
async def get_alerts_for_package(
    package_name: str,
    skip: int = Query(0, ge=0, description="Number of alerts to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum alerts to return"),
    status: Optional[Literal["open", "investigated", "resolved"]] = Query(
        None, description="Filter by status"
    ),
    alert_repo: RiskAlertRepository = Depends(get_alert_repository),
    package_repo: PackageRepository = Depends(get_package_repository),
):
    """
    Get all alerts for a specific package.

    Supports filtering by status and pagination.
    Results are sorted by timestamp (newest first).
    """
    # URL-decode to handle scoped packages
    package_name = unquote(package_name)

    # Find package
    package = await package_repo.find_by_name(package_name)
    if not package:
        raise HTTPException(status_code=404, detail=f"Package '{package_name}' not found")

    if not package.id:
        raise HTTPException(status_code=500, detail="Package ID is missing")

    # Build filter
    filter_query = {"package_id": package.id}
    if status:
        filter_query["status"] = status

    # Get alerts
    alerts = await alert_repo.find_many(
        filter_query, skip=skip, limit=limit, sort=[("timestamp", -1)]
    )
    total = await alert_repo.count(filter_query)

    # Enrich with package names (will all be the same package_name)
    enriched_alerts = []
    for alert in alerts:
        alert_dict = alert.model_dump(by_alias=True)
        enriched_alert = await enrich_alert_with_package_name(alert_dict, package_repo)
        enriched_alerts.append(enriched_alert)

    return ListAlertsResponse(
        alerts=enriched_alerts,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.patch("/{alert_id}/status", response_model=AlertResponse)
async def update_alert_status(
    alert_id: str,
    request: UpdateAlertStatusRequest,
    alert_repo: RiskAlertRepository = Depends(get_alert_repository),
    package_repo: PackageRepository = Depends(get_package_repository),
):
    """
    Update the status of an alert.

    Valid status transitions:
    - open -> investigated
    - open -> resolved
    - investigated -> resolved
    - investigated -> open (reopen)
    - resolved -> open (reopen)
    """
    # Validate ObjectId format
    if not ObjectId.is_valid(alert_id):
        raise HTTPException(status_code=400, detail="Invalid alert ID format")

    # Find alert
    alert = await alert_repo.find_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

    # Update status
    updated_alert = await alert_repo.update(alert_id, {"status": request.status})
    if not updated_alert:
        raise HTTPException(status_code=500, detail="Failed to update alert status")

    # Enrich with package name
    alert_dict = updated_alert.model_dump(by_alias=True)
    return await enrich_alert_with_package_name(alert_dict, package_repo)
