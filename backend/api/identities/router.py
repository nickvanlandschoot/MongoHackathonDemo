"""
Identity API router - expose maintainer/GitHub data.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from database import get_database
from models.identity import Identity
from repositories.identity import IdentityRepository

router = APIRouter(
    prefix="/identities",
    tags=["identities"],
)


def get_identity_repository() -> IdentityRepository:
    """Dependency injection for IdentityRepository."""
    return IdentityRepository(get_database())


@router.get("/", response_model=List[Identity])
async def list_identities(
    skip: int = Query(0, ge=0, description="Number to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum to return"),
    kind: Optional[str] = Query(None, description="Filter by kind (npm, github, email_domain)"),
    repo: IdentityRepository = Depends(get_identity_repository),
):
    """
    List identities (maintainers, GitHub users).

    Useful for frontend to display all known maintainers and their GitHub info.
    """
    if kind:
        identities = repo.find_many({"kind": kind}, skip=skip, limit=limit)
    else:
        identities = repo.find_many({}, skip=skip, limit=limit)

    return identities


@router.get("/{identity_id}", response_model=Identity)
async def get_identity(
    identity_id: str,
    repo: IdentityRepository = Depends(get_identity_repository),
):
    """
    Get specific identity by ID.
    """
    identity = repo.find_by_id(identity_id)
    if not identity:
        raise HTTPException(status_code=404, detail=f"Identity {identity_id} not found")

    return identity


@router.get("/by-handle/{handle}", response_model=Identity)
async def get_identity_by_handle(
    handle: str,
    kind: str = Query(..., description="Identity kind (npm or github)"),
    repo: IdentityRepository = Depends(get_identity_repository),
):
    """
    Get identity by handle (username).

    Useful for looking up npm maintainer or GitHub user by username.
    """
    identity = repo.find_by_handle(handle, kind=kind)
    if not identity:
        raise HTTPException(
            status_code=404,
            detail=f"Identity with handle '{handle}' and kind '{kind}' not found"
        )

    return identity
