"""
API endpoints for entity data enrichment.

Provides endpoints for:
- Getting available enrichment sources
- Starting analysis tasks
- Getting analysis previews
- Applying changes
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_session
from app.models import User
from app.models.audit_log import AuditAction
from app.services.audit_service import create_audit_log
from services.entity_data_facet_service import EntityDataFacetService

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class EnrichmentSourceInfo(BaseModel):
    """Information about a single enrichment source."""

    available: bool
    count: int
    last_updated: str | None
    label: str


class EnrichmentSourcesResponse(BaseModel):
    """Response for enrichment sources endpoint."""

    entity_id: str
    entity_name: str
    pysis: EnrichmentSourceInfo
    relations: EnrichmentSourceInfo
    documents: EnrichmentSourceInfo
    extractions: EnrichmentSourceInfo
    existing_facets: int


class StartAnalysisRequest(BaseModel):
    """Request to start an analysis task."""

    entity_id: UUID
    source_types: list[str] = Field(
        ...,
        description="Data sources to analyze: pysis, relations, documents, extractions",
        min_length=1,
    )
    target_facet_types: list[str] | None = Field(
        None,
        description="Specific facet types to generate (defaults to all AI-enabled types)",
    )


class StartAnalysisResponse(BaseModel):
    """Response after starting an analysis task."""

    task_id: str
    status: str
    message: str


class ApplyChangesRequest(BaseModel):
    """Request to apply selected changes from a preview."""

    task_id: UUID
    accepted_new_facets: list[int] = Field(
        default=[],
        description="Indices of accepted new facets from preview",
    )
    accepted_updates: list[str] = Field(
        default=[],
        description="IDs of accepted facet value updates",
    )


class ApplyChangesResponse(BaseModel):
    """Response after applying changes."""

    created: int
    updated: int
    errors: list[str] | None


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/enrichment-sources",
    response_model=EnrichmentSourcesResponse,
    summary="Get available enrichment sources",
    description="Returns all available data sources for an entity with counts and timestamps.",
)
async def get_enrichment_sources(
    entity_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EnrichmentSourcesResponse:
    """Get available data sources for entity enrichment."""
    service = EntityDataFacetService(session)

    try:
        result = await service.get_enrichment_sources(entity_id)
        return EnrichmentSourcesResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Laden der Quellen: {e}") from None


@router.post(
    "/analyze-for-facets",
    response_model=StartAnalysisResponse,
    summary="Start facet analysis",
    description="Starts an AI analysis task to generate facet suggestions from entity data.",
)
async def analyze_for_facets(
    request: StartAnalysisRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StartAnalysisResponse:
    """Start an AI analysis task for facet enrichment."""
    service = EntityDataFacetService(session)

    try:
        task = await service.start_analysis(
            entity_id=request.entity_id,
            source_types=request.source_types,
            target_facet_types=request.target_facet_types,
        )

        # Create audit log entry
        await create_audit_log(
            session=session,
            action=AuditAction.CREATE,
            entity_type="EntityDataAnalysis",
            entity_id=request.entity_id,
            entity_name=f"analysis for {len(request.source_types)} sources",
            user=current_user,
        )
        await session.commit()

        return StartAnalysisResponse(
            task_id=str(task.id),
            status=task.status.value,
            message=f"Analyse gestartet für {len(request.source_types)} Datenquellen",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Starten der Analyse: {e}") from None


@router.get(
    "/analysis-preview",
    summary="Get analysis preview",
    description="Returns the preview of proposed changes from a completed analysis task.",
)
async def get_analysis_preview(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get the preview of proposed changes."""
    service = EntityDataFacetService(session)

    try:
        return await service.get_analysis_preview(task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Laden der Vorschau: {e}") from None


@router.post(
    "/apply-changes",
    response_model=ApplyChangesResponse,
    summary="Apply selected changes",
    description="Applies the selected changes from an analysis preview.",
)
async def apply_changes(
    request: ApplyChangesRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ApplyChangesResponse:
    """Apply selected changes from analysis preview."""
    service = EntityDataFacetService(session)

    try:
        result = await service.apply_changes(
            task_id=request.task_id,
            accepted_new_facets=request.accepted_new_facets,
            accepted_updates=request.accepted_updates,
        )

        # Create audit log entry
        await create_audit_log(
            session=session,
            action=AuditAction.UPDATE,
            entity_type="EntityDataAnalysis",
            entity_id=request.task_id,
            entity_name=f"applied {result.get('created', 0)} new, {result.get('updated', 0)} updated",
            user=current_user,
        )
        await session.commit()

        return ApplyChangesResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Anwenden der Änderungen: {e}") from None
