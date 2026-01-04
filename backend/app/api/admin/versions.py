"""Admin API endpoints for version history."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_viewer
from app.database import get_session
from app.models.user import User
from app.services.versioning_service import (
    get_version,
    get_version_count,
    get_version_history,
    reconstruct_at_version,
)

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class VersionResponse(BaseModel):
    """Single version response."""

    id: UUID
    entity_type: str
    entity_id: UUID
    version_number: int
    diff: dict[str, Any]
    has_snapshot: bool
    user_id: UUID | None = None
    user_email: str | None = None
    change_reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VersionListResponse(BaseModel):
    """Paginated version list."""

    items: list[VersionResponse]
    total: int
    entity_type: str
    entity_id: UUID


class EntityStateResponse(BaseModel):
    """Reconstructed entity state at a version."""

    entity_type: str
    entity_id: UUID
    version_number: int
    state: dict[str, Any]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/{entity_type}/{entity_id}", response_model=VersionListResponse)
async def list_versions(
    entity_type: str,
    entity_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_viewer),
):
    """
    Get version history for an entity.

    Returns versions in reverse chronological order (newest first).

    Supported entity types:
    - Category
    - DataSource
    - Entity
    - FacetValue
    - And all other versioned models...
    """
    versions = await get_version_history(
        session=session,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )

    total = await get_version_count(
        session=session,
        entity_type=entity_type,
        entity_id=entity_id,
    )

    return VersionListResponse(
        items=[
            VersionResponse(
                id=v.id,
                entity_type=v.entity_type,
                entity_id=v.entity_id,
                version_number=v.version_number,
                diff=v.diff,
                has_snapshot=v.snapshot is not None,
                user_id=v.user_id,
                user_email=v.user_email,
                change_reason=v.change_reason,
                created_at=v.created_at,
            )
            for v in versions
        ],
        total=total,
        entity_type=entity_type,
        entity_id=entity_id,
    )


@router.get(
    "/{entity_type}/{entity_id}/{version_number}",
    response_model=VersionResponse,
)
async def get_version_detail(
    entity_type: str,
    entity_id: UUID,
    version_number: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_viewer),
):
    """
    Get details of a specific version.
    """
    version = await get_version(
        session=session,
        entity_type=entity_type,
        entity_id=entity_id,
        version_number=version_number,
    )

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found for {entity_type}:{entity_id}",
        )

    return VersionResponse(
        id=version.id,
        entity_type=version.entity_type,
        entity_id=version.entity_id,
        version_number=version.version_number,
        diff=version.diff,
        has_snapshot=version.snapshot is not None,
        user_id=version.user_id,
        user_email=version.user_email,
        change_reason=version.change_reason,
        created_at=version.created_at,
    )


@router.get(
    "/{entity_type}/{entity_id}/{version_number}/state",
    response_model=EntityStateResponse,
)
async def get_entity_state_at_version(
    entity_type: str,
    entity_id: UUID,
    version_number: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_viewer),
):
    """
    Reconstruct entity state at a specific version.

    This rebuilds the complete entity state by applying all diffs
    from the nearest snapshot up to the requested version.
    """
    state = await reconstruct_at_version(
        session=session,
        entity_type=entity_type,
        entity_id=entity_id,
        target_version=version_number,
    )

    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot reconstruct state for {entity_type}:{entity_id} at v{version_number}",
        )

    return EntityStateResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        version_number=version_number,
        state=state,
    )
