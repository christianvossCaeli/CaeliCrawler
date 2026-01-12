"""Admin API endpoints for crawl presets."""

import math
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_editor
from app.core.exceptions import NotFoundError, ValidationError
from app.core.rate_limit import check_rate_limit
from app.database import get_session
from app.models import CrawlPreset, DataSource, User
from app.models.audit_log import AuditAction
from app.schemas.common import MessageResponse
from app.schemas.crawl_preset import (
    SCHEDULE_PRESETS,
    CrawlPresetCreate,
    CrawlPresetExecuteRequest,
    CrawlPresetExecuteResponse,
    CrawlPresetFavoriteToggleResponse,
    CrawlPresetFilters,
    CrawlPresetFromFiltersRequest,
    CrawlPresetListResponse,
    CrawlPresetResponse,
    CrawlPresetUpdate,
    EntityCrawlPreviewRequest,
    EntityCrawlPreviewResponse,
    EntityCrawlRequest,
    EntitySourcePreviewItem,
)
from app.services.audit_service import create_audit_log
from app.utils.cron import croniter_for_expression, get_schedule_timezone, is_valid_cron_expression

# Import crawl operations at module level to avoid repeated imports
from services.smart_query.crawl_operations import find_sources_for_crawl, find_sources_for_entities, start_crawl_jobs

router = APIRouter()


# --- Response Schemas for Preview Endpoints ---


class SourcePreviewItem(BaseModel):
    """Single source in preview response."""

    id: str
    name: str
    url: str


class PresetPreviewResponse(BaseModel):
    """Response for preset preview endpoint."""

    preset_id: UUID
    sources_count: int
    sources_preview: list[SourcePreviewItem]
    has_more: bool


class FiltersPreviewResponse(BaseModel):
    """Response for filters preview endpoint."""

    sources_count: int
    sources_preview: list[SourcePreviewItem]
    has_more: bool


def calculate_next_run(cron_expression: str) -> datetime:
    """Calculate the next run time from a cron expression."""
    schedule_tz = get_schedule_timezone()
    cron = croniter_for_expression(cron_expression, datetime.now(schedule_tz))
    return cron.get_next(datetime)


def validate_cron_expression(cron_expression: str) -> bool:
    """Validate a cron expression."""
    return is_valid_cron_expression(cron_expression)


def sanitize_search_input(search: str) -> str:
    """Sanitize search input to prevent SQL LIKE injection.

    Escapes \\, %, and _ which are special characters in SQL LIKE patterns.
    The backslash must be escaped first to avoid double-escaping.
    """
    if not search:
        return search
    # Escape SQL LIKE special characters (backslash first!)
    return search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_filter_summary(preset: CrawlPreset) -> str:
    """Generate a human-readable summary of the preset filters."""
    return preset.get_filter_summary()


async def _create_preset_internal(
    session: AsyncSession,
    user_id: UUID,
    name: str,
    filters: CrawlPresetFilters,
    description: str | None = None,
    schedule_cron: str | None = None,
    schedule_enabled: bool = False,
) -> CrawlPreset:
    """Internal helper to create a preset. Reduces code duplication.

    Args:
        session: Database session
        user_id: Owner user ID
        name: Preset name
        filters: Filter configuration
        description: Optional description
        schedule_cron: Optional cron expression
        schedule_enabled: Whether scheduling is enabled

    Returns:
        Created CrawlPreset instance

    Raises:
        ValidationError: If cron expression is invalid
    """
    # Use mode='json' to properly serialize UUIDs to strings for JSONB storage
    filters_dict = filters.model_dump(mode="json", exclude_none=True)

    # Check for duplicate by filter configuration
    from app.utils.similarity import find_duplicate_crawl_preset

    duplicate = await find_duplicate_crawl_preset(
        session,
        user_id=user_id,
        filters=filters_dict,
    )
    if duplicate:
        existing_preset, reason = duplicate
        raise ValidationError(f"Ähnliches Preset existiert bereits: {reason}")

    # Validate cron expression if provided
    if schedule_cron and not validate_cron_expression(schedule_cron):
        raise ValidationError("Invalid cron expression")

    # Calculate next run if scheduling is enabled
    next_run = None
    if schedule_enabled and schedule_cron:
        next_run = calculate_next_run(schedule_cron)

    preset = CrawlPreset(
        user_id=user_id,
        name=name,
        description=description,
        filters=filters_dict,
        schedule_cron=schedule_cron,
        schedule_enabled=schedule_enabled,
        next_run_at=next_run,
    )

    session.add(preset)
    await session.commit()
    await session.refresh(preset)

    return preset


def _build_preview_response(
    sources: list[DataSource],
    preset_id: UUID | None = None,
    max_preview: int = 10,
) -> dict[str, Any]:
    """Build standardized preview response from sources list."""
    preview_items = [SourcePreviewItem(id=str(s.id), name=s.name, url=s.base_url) for s in sources[:max_preview]]

    response = {
        "sources_count": len(sources),
        "sources_preview": preview_items,
        "has_more": len(sources) > max_preview,
    }

    if preset_id:
        response["preset_id"] = preset_id

    return response


@router.get("", response_model=CrawlPresetListResponse)
async def list_presets(
    http_request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    favorites_only: bool = Query(default=False, description="Only return favorites"),
    scheduled_only: bool = Query(default=False, description="Only return presets with active schedule"),
    search: str | None = Query(default=None, description="Search by name"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """List all crawl presets for the current user."""
    await check_rate_limit(http_request, "crawl_presets_list", identifier=str(current_user.id))

    query = select(CrawlPreset).where(CrawlPreset.user_id == current_user.id)

    if favorites_only:
        query = query.where(CrawlPreset.is_favorite)

    if scheduled_only:
        query = query.where(CrawlPreset.schedule_enabled.is_(True))

    if search:
        # Sanitize search input to prevent SQL LIKE injection
        safe_search = sanitize_search_input(search)
        query = query.where(CrawlPreset.name.ilike(f"%{safe_search}%", escape="\\"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Order by favorites first, then by last used/created
    query = (
        query.order_by(
            CrawlPreset.is_favorite.desc(), CrawlPreset.last_used_at.desc().nullsfirst(), CrawlPreset.created_at.desc()
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    result = await session.execute(query)
    presets = result.scalars().all()

    # Build response items - filter_summary is computed synchronously from model
    # (no N+1 query as it uses already loaded data)
    items = [
        CrawlPresetResponse(
            **preset.__dict__,
            filter_summary=get_filter_summary(preset),
        )
        for preset in presets
    ]

    return CrawlPresetListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page > 0 else 0,
    )


@router.post("", response_model=CrawlPresetResponse)
async def create_preset(
    preset_data: CrawlPresetCreate,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Create a new crawl preset."""
    await check_rate_limit(http_request, "crawl_presets_create", identifier=str(current_user.id))

    preset = await _create_preset_internal(
        session=session,
        user_id=current_user.id,
        name=preset_data.name,
        filters=preset_data.filters,
        description=preset_data.description,
        schedule_cron=preset_data.schedule_cron,
        schedule_enabled=preset_data.schedule_enabled,
    )

    # Create audit log entry
    await create_audit_log(
        session=session,
        action=AuditAction.CREATE,
        entity_type="CrawlPreset",
        entity_id=preset.id,
        entity_name=preset.name,
        user=current_user,
    )
    await session.commit()

    return CrawlPresetResponse(
        **preset.__dict__,
        filter_summary=get_filter_summary(preset),
    )


@router.get("/schedule-presets")
async def get_schedule_presets(
    _: User = Depends(require_editor),
):
    """Get predefined schedule presets for UI convenience."""
    return [p.model_dump() for p in SCHEDULE_PRESETS]


@router.get("/{preset_id}", response_model=CrawlPresetResponse)
async def get_preset(
    preset_id: UUID,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Get a specific crawl preset."""
    await check_rate_limit(http_request, "crawl_presets_read", identifier=str(current_user.id))

    preset = await session.get(CrawlPreset, preset_id)
    if not preset or preset.user_id != current_user.id:
        raise NotFoundError("Crawl Preset", str(preset_id))

    return CrawlPresetResponse(
        **preset.__dict__,
        filter_summary=get_filter_summary(preset),
    )


@router.put("/{preset_id}", response_model=CrawlPresetResponse)
async def update_preset(
    preset_id: UUID,
    update_data: CrawlPresetUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Update a crawl preset."""
    preset = await session.get(CrawlPreset, preset_id)
    if not preset or preset.user_id != current_user.id:
        raise NotFoundError("Crawl Preset", str(preset_id))

    # Update fields
    if update_data.name is not None:
        preset.name = update_data.name
    if update_data.description is not None:
        preset.description = update_data.description
    if update_data.filters is not None:
        # Use mode='json' to properly serialize UUIDs to strings for JSONB storage
        preset.filters = update_data.filters.model_dump(mode="json", exclude_none=True)
    if update_data.schedule_cron is not None:
        if update_data.schedule_cron and not validate_cron_expression(update_data.schedule_cron):
            raise ValidationError("Invalid cron expression")
        preset.schedule_cron = update_data.schedule_cron
    if update_data.schedule_enabled is not None:
        preset.schedule_enabled = update_data.schedule_enabled
    if update_data.is_favorite is not None:
        preset.is_favorite = update_data.is_favorite

    # Recalculate next run if schedule changed
    if preset.schedule_enabled and preset.schedule_cron:
        preset.next_run_at = calculate_next_run(preset.schedule_cron)
    elif not preset.schedule_enabled:
        preset.next_run_at = None

    # Create audit log entry
    await create_audit_log(
        session=session,
        action=AuditAction.UPDATE,
        entity_type="CrawlPreset",
        entity_id=preset.id,
        entity_name=preset.name,
        user=current_user,
    )

    await session.commit()
    await session.refresh(preset)

    return CrawlPresetResponse(
        **preset.__dict__,
        filter_summary=get_filter_summary(preset),
    )


@router.delete("/{preset_id}", response_model=MessageResponse)
async def delete_preset(
    preset_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Delete a crawl preset."""
    preset = await session.get(CrawlPreset, preset_id)
    if not preset or preset.user_id != current_user.id:
        raise NotFoundError("Crawl Preset", str(preset_id))

    preset_name = preset.name

    # Create audit log entry
    await create_audit_log(
        session=session,
        action=AuditAction.DELETE,
        entity_type="CrawlPreset",
        entity_id=preset_id,
        entity_name=preset_name,
        user=current_user,
    )

    await session.delete(preset)
    await session.commit()

    return MessageResponse(message="Crawl preset deleted successfully")


@router.post("/{preset_id}/execute", response_model=CrawlPresetExecuteResponse)
async def execute_preset(
    preset_id: UUID,
    execute_request: CrawlPresetExecuteRequest = CrawlPresetExecuteRequest(),
    http_request: Request = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Execute a crawl preset (start crawl with preset filters)."""
    if http_request:
        await check_rate_limit(http_request, "crawl_presets_execute", identifier=str(current_user.id))

    preset = await session.get(CrawlPreset, preset_id)
    if not preset or preset.user_id != current_user.id:
        raise NotFoundError("Crawl Preset", str(preset_id))

    # Find matching sources
    sources = await find_sources_for_crawl(session, preset.filters, limit=10000)

    if not sources:
        return CrawlPresetExecuteResponse(
            preset_id=preset_id,
            jobs_created=0,
            job_ids=[],
            sources_matched=0,
            message="No sources match the preset filters",
        )

    # Extract category_id from preset filters (required field)
    category_id = preset.filters.get("category_id")
    if category_id and isinstance(category_id, str):
        category_id = UUID(category_id)

    # Start crawl jobs for the preset's specific category
    job_ids = await start_crawl_jobs(
        session,
        sources,
        force=execute_request.force,
        category_id=category_id,
    )

    # Update statistics
    preset.usage_count += 1
    preset.last_used_at = datetime.now(UTC)
    await session.commit()

    return CrawlPresetExecuteResponse(
        preset_id=preset_id,
        jobs_created=len(job_ids),
        job_ids=job_ids,
        sources_matched=len(sources),
        message=f"Started {len(job_ids)} crawl jobs for {len(sources)} sources",
    )


@router.post("/{preset_id}/toggle-favorite", response_model=CrawlPresetFavoriteToggleResponse)
async def toggle_favorite(
    preset_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Toggle favorite status of a crawl preset."""
    preset = await session.get(CrawlPreset, preset_id)
    if not preset or preset.user_id != current_user.id:
        raise NotFoundError("Crawl Preset", str(preset_id))

    preset.is_favorite = not preset.is_favorite

    # Create audit log entry
    await create_audit_log(
        session=session,
        action=AuditAction.FAVORITE_ADD if preset.is_favorite else AuditAction.FAVORITE_REMOVE,
        entity_type="CrawlPreset",
        entity_id=preset.id,
        entity_name=preset.name,
        user=current_user,
    )

    await session.commit()

    return CrawlPresetFavoriteToggleResponse(
        id=preset_id,
        is_favorite=preset.is_favorite,
        message="Added to favorites" if preset.is_favorite else "Removed from favorites",
    )


@router.post("/from-filters", response_model=CrawlPresetResponse)
async def create_preset_from_filters(
    preset_data: CrawlPresetFromFiltersRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Create a preset from current filter selection (used by UI)."""
    await check_rate_limit(http_request, "crawl_presets_create", identifier=str(current_user.id))

    # Reuse the internal helper to avoid code duplication
    preset = await _create_preset_internal(
        session=session,
        user_id=current_user.id,
        name=preset_data.name,
        filters=preset_data.filters,
        description=preset_data.description,
        schedule_cron=preset_data.schedule_cron,
        schedule_enabled=preset_data.schedule_enabled,
    )

    # Create audit log entry
    await create_audit_log(
        session=session,
        action=AuditAction.CREATE,
        entity_type="CrawlPreset",
        entity_id=preset.id,
        entity_name=preset.name,
        user=current_user,
    )
    await session.commit()

    return CrawlPresetResponse(
        **preset.__dict__,
        filter_summary=get_filter_summary(preset),
    )


@router.get("/{preset_id}/preview", response_model=PresetPreviewResponse)
async def preview_preset(
    preset_id: UUID,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Preview how many sources would be crawled by a preset."""
    await check_rate_limit(http_request, "crawl_presets_preview", identifier=str(current_user.id))

    preset = await session.get(CrawlPreset, preset_id)
    if not preset or preset.user_id != current_user.id:
        raise NotFoundError("Crawl Preset", str(preset_id))

    sources = await find_sources_for_crawl(session, preset.filters, limit=10000)

    return PresetPreviewResponse(
        preset_id=preset_id,
        **_build_preview_response(sources),
    )


@router.post("/preview-filters", response_model=FiltersPreviewResponse)
async def preview_filters(
    filters: CrawlPresetFilters,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Preview how many sources would be crawled by given filters.

    This endpoint allows previewing filter results before saving a preset.
    Useful for validating filter configuration in the editor.
    """
    await check_rate_limit(http_request, "crawl_presets_preview", identifier=str(current_user.id))

    # Convert filters to dict, excluding None values
    filter_dict = filters.model_dump(exclude_none=True)

    sources = await find_sources_for_crawl(session, filter_dict, limit=10000)

    return FiltersPreviewResponse(**_build_preview_response(sources))


# --- Entity-based Crawl Endpoints ---


@router.post("/preview-entities", response_model=EntityCrawlPreviewResponse)
async def preview_entity_sources(
    request: EntityCrawlPreviewRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Preview how many DataSources would be crawled for selected entities.

    This endpoint shows which DataSources are associated with the given entities
    via their ExtractedData connections.
    """
    await check_rate_limit(http_request, "crawl_presets_preview", identifier=str(current_user.id))

    sources, entities_without_sources = await find_sources_for_entities(
        session,
        entity_ids=request.entity_ids,
        category_id=request.category_id,
    )

    # Build preview items using typed schema
    max_preview = 10
    preview_items = [EntitySourcePreviewItem(id=str(s.id), name=s.name, url=s.base_url) for s in sources[:max_preview]]

    return EntityCrawlPreviewResponse(
        entity_count=len(request.entity_ids),
        sources_count=len(sources),
        sources_preview=preview_items,
        entities_without_sources=entities_without_sources,
        has_more=len(sources) > max_preview,
    )


@router.post("/entity-crawl", response_model=CrawlPresetExecuteResponse)
async def start_entity_crawl(
    request: EntityCrawlRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Start a crawl for DataSources associated with selected entities.

    This endpoint:
    1. Finds DataSources connected to the given entities (via ExtractedData)
    2. Starts crawl jobs for these sources
    3. Optionally saves the selection as a preset

    Args:
        request: Entity crawl request with entity_ids and category_id

    Returns:
        CrawlPresetExecuteResponse with created job information
    """
    await check_rate_limit(http_request, "crawl_presets_execute", identifier=str(current_user.id))

    # Validate preset name if saving
    if request.save_as_preset and not request.preset_name:
        raise ValidationError("preset_name is required when save_as_preset is True")

    # Find sources for the selected entities
    sources, entities_without_sources = await find_sources_for_entities(
        session,
        entity_ids=request.entity_ids,
        category_id=request.category_id,
    )

    preset_id = None

    # Optionally create a preset
    if request.save_as_preset and request.preset_name:
        # Build filters based on selection mode
        filters = CrawlPresetFilters(
            category_id=request.category_id,
            entity_ids=request.entity_ids if request.selection_mode == "fixed" else None,
            entity_selection_mode=request.selection_mode,
        )

        preset = await _create_preset_internal(
            session=session,
            user_id=current_user.id,
            name=request.preset_name,
            filters=filters,
            description=f"Entity-basiertes Preset ({len(request.entity_ids)} Entities)",
        )
        preset_id = preset.id

    if not sources:
        return CrawlPresetExecuteResponse(
            preset_id=preset_id,
            jobs_created=0,
            job_ids=[],
            sources_matched=0,
            message=f"Keine DataSources für die {len(request.entity_ids)} ausgewählten Entities gefunden. "
            f"{entities_without_sources} Entities haben keine zugeordneten Quellen.",
        )

    # Start crawl jobs
    job_ids = await start_crawl_jobs(
        session,
        sources,
        force=request.force,
        category_id=request.category_id,
    )

    message = f"{len(job_ids)} Crawl-Jobs für {len(sources)} DataSources gestartet"
    if entities_without_sources > 0:
        message += f" ({entities_without_sources} Entities ohne Quellen übersprungen)"
    if request.save_as_preset:
        message += f". Preset '{request.preset_name}' wurde erstellt."

    return CrawlPresetExecuteResponse(
        preset_id=preset_id,
        jobs_created=len(job_ids),
        job_ids=[UUID(jid) for jid in job_ids],
        sources_matched=len(sources),
        message=message,
    )
