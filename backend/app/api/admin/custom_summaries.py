"""Admin API endpoints for custom summaries."""

import io
import math
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from passlib.hash import bcrypt
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import require_editor
from app.core.exceptions import NotFoundError, ValidationError
from app.core.rate_limit import check_rate_limit
from app.database import get_session
from app.models import (
    CustomSummary,
    SummaryExecution,
    SummaryShare,
    SummaryWidget,
    User,
)
from app.models.custom_summary import SummaryStatus, SummaryTriggerType
from app.models.summary_execution import ExecutionStatus
from app.models.summary_widget import SummaryWidgetType
from app.schemas.common import MessageResponse
from app.schemas.custom_summary import (
    SCHEDULE_PRESETS,
    CheckUpdatesProgressResponse,
    CheckUpdatesStatus,
    SummaryCheckUpdatesResponse,
    SummaryCreate,
    SummaryCreateFromPrompt,
    SummaryDetailResponse,
    SummaryExecuteRequest,
    SummaryExecuteResponse,
    SummaryExecutionDetailResponse,
    SummaryExecutionResponse,
    SummaryFavoriteToggleResponse,
    SummaryFromPromptResponse,
    SummaryListResponse,
    SummaryResponse,
    SummaryShareCreate,
    SummaryShareResponse,
    SummaryUpdate,
    SummaryWidgetCreate,
    SummaryWidgetResponse,
    SummaryWidgetUpdate,
    WidgetPosition,
)
from app.utils.cron import croniter_for_expression, get_schedule_timezone, is_valid_cron_expression
from services.summaries import (
    SummaryExecutor,
    SummaryExportService,
    get_schedule_suggestion,
    interpret_summary_prompt,
)
from services.summaries.export_service import sanitize_filename

logger = structlog.get_logger(__name__)

router = APIRouter()

# Maximum widgets per summary (prevent resource exhaustion)
MAX_WIDGETS_PER_SUMMARY = 20

# Cache TTL settings (in hours)
DEFAULT_CACHE_TTL_HOURS = 24  # Default: cache valid for 24 hours
MAX_CACHE_TTL_HOURS = 168  # Maximum: 1 week


# --- Helper Functions ---


def calculate_next_run(cron_expression: str, from_time: datetime = None) -> datetime:
    """Calculate the next run time from a cron expression.

    Args:
        cron_expression: The cron expression to use.
        from_time: The base time to calculate from. If None, uses current time.

    Returns:
        The next scheduled run time.
    """
    schedule_tz = get_schedule_timezone()
    base_time = from_time or datetime.now(schedule_tz)

    # Ensure base_time has timezone info
    if base_time.tzinfo is None:
        base_time = schedule_tz.localize(base_time)

    cron = croniter_for_expression(cron_expression, base_time)
    return cron.get_next(datetime)


def _summary_to_response(summary: CustomSummary) -> SummaryResponse:
    """Convert summary model to response schema."""
    return SummaryResponse(
        id=summary.id,
        user_id=summary.user_id,
        name=summary.name,
        description=summary.description,
        original_prompt=summary.original_prompt,
        interpreted_config=summary.interpreted_config,
        layout_config=summary.layout_config,
        status=summary.status.value,  # Pass string, Pydantic coerces to schema enum
        trigger_type=summary.trigger_type.value,  # Pass string, Pydantic coerces to schema enum
        schedule_cron=summary.schedule_cron,
        trigger_category_id=summary.trigger_category_id,
        trigger_preset_id=summary.trigger_preset_id,
        schedule_enabled=summary.schedule_enabled,
        next_run_at=summary.next_run_at,
        check_relevance=summary.check_relevance,
        relevance_threshold=summary.relevance_threshold,
        auto_expand=summary.auto_expand,
        is_favorite=summary.is_favorite,
        execution_count=summary.execution_count,
        last_executed_at=summary.last_executed_at,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
    )


def _widget_to_response(widget: SummaryWidget) -> SummaryWidgetResponse:
    """Convert widget model to response schema."""
    return SummaryWidgetResponse(
        id=widget.id,
        widget_type=widget.widget_type.value,  # Pass string, Pydantic coerces to schema enum
        title=widget.title,
        subtitle=widget.subtitle,
        position=WidgetPosition(
            x=widget.position_x,
            y=widget.position_y,
            w=widget.width,
            h=widget.height,
        ),
        query_config=widget.query_config,
        visualization_config=widget.visualization_config,
        display_order=widget.display_order,
        created_at=widget.created_at,
        updated_at=widget.updated_at,
    )


def _execution_to_response(execution: SummaryExecution) -> SummaryExecutionResponse:
    """Convert execution model to response schema."""
    return SummaryExecutionResponse(
        id=execution.id,
        status=execution.status.value,  # Pass string, Pydantic coerces to schema enum
        triggered_by=execution.triggered_by,
        trigger_details=execution.trigger_details,
        has_changes=execution.has_changes,
        relevance_score=execution.relevance_score,
        relevance_reason=execution.relevance_reason,
        duration_ms=execution.duration_ms,
        created_at=execution.created_at,
        completed_at=execution.completed_at,
    )


# --- Summary CRUD Endpoints ---


@router.post("/from-prompt", response_model=SummaryFromPromptResponse)
async def create_from_prompt(
    data: SummaryCreateFromPrompt,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Create a summary from a natural language prompt.

    The KI interprets the prompt and suggests widgets/layout.
    """
    await check_rate_limit(request, "summary_create", identifier=str(current_user.id))

    try:
        # Call AI interpreter to parse the prompt
        interpretation = await interpret_summary_prompt(
            prompt=data.prompt,
            session=session,
            user_name=current_user.email,
        )
    except ValueError as e:
        raise ValidationError(str(e)) from None
    except RuntimeError as e:
        logger.warning("AI interpretation failed, using fallback", error=str(e))
        # Fallback to basic interpretation
        interpretation = {
            "name": data.name or "Neue Zusammenfassung",
            "description": data.prompt[:200] + "..." if len(data.prompt) > 200 else data.prompt,
            "theme": {"primary_entity_type": None, "context": "custom"},
            "widgets": [],
            "suggested_schedule": get_schedule_suggestion(data.prompt),
            "overall_reasoning": f"Fallback-Modus: {str(e)}",
        }

    # Use user-provided name or AI-suggested name
    summary_name = data.name or interpretation.get("name", "Neue Zusammenfassung")

    # Check for duplicate name
    from app.utils.similarity import find_duplicate_custom_summary

    duplicate = await find_duplicate_custom_summary(
        session,
        user_id=current_user.id,
        name=summary_name,
    )
    if duplicate:
        existing, reason = duplicate
        raise ValidationError(f"Ähnliche Zusammenfassung existiert bereits: {reason}")

    # Determine trigger type and cron from AI suggestion
    schedule = interpretation.get("suggested_schedule", {})
    trigger_type = SummaryTriggerType.MANUAL
    schedule_cron = None

    if schedule.get("type") == "daily":
        trigger_type = SummaryTriggerType.CRON
        schedule_cron = schedule.get("cron", "0 8 * * *")
    elif schedule.get("type") == "weekly":
        trigger_type = SummaryTriggerType.CRON
        schedule_cron = schedule.get("cron", "0 9 * * 1")

    # Create the summary
    summary = CustomSummary(
        user_id=current_user.id,
        name=summary_name,
        description=interpretation.get("description"),
        original_prompt=data.prompt,
        interpreted_config=interpretation,
        layout_config={"columns": 4, "row_height": 100},
        status=SummaryStatus.DRAFT,
        trigger_type=trigger_type,
        schedule_cron=schedule_cron,
        check_relevance=True,
        auto_expand=interpretation.get("auto_expand_suggestion", {}).get("enabled", False),
    )
    session.add(summary)
    await session.flush()  # Get the ID before creating widgets

    # Create widgets from AI interpretation
    widgets_created = 0
    ai_widgets = interpretation.get("widgets", [])

    # Enforce maximum widget count to prevent resource exhaustion
    if len(ai_widgets) > MAX_WIDGETS_PER_SUMMARY:
        await session.rollback()
        raise ValidationError(f"Zu viele Widgets ({len(ai_widgets)}). Maximum: {MAX_WIDGETS_PER_SUMMARY}")

    try:
        for i, widget_data in enumerate(ai_widgets):
            position = widget_data.get("position", {})
            widget_type_str = widget_data.get("widget_type", "table")

            # Map string to enum
            try:
                widget_type = SummaryWidgetType(widget_type_str)
            except ValueError:
                widget_type = SummaryWidgetType.TABLE

            widget = SummaryWidget(
                summary_id=summary.id,
                widget_type=widget_type,
                title=widget_data.get("title", f"Widget {i + 1}"),
                subtitle=widget_data.get("subtitle"),
                position_x=position.get("x", 0),
                position_y=position.get("y", 0),
                width=position.get("w", 2),
                height=position.get("h", 2),
                query_config=widget_data.get("query_config", {}),
                visualization_config=widget_data.get("visualization_config", {}),
                display_order=i,
            )
            session.add(widget)
            widgets_created += 1

        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error("widget_creation_failed", error=str(e), summary_id=str(summary.id))
        raise ValidationError(f"Fehler beim Erstellen der Widgets: {str(e)}") from None
    await session.refresh(summary)

    logger.info(
        "summary_created_from_prompt",
        summary_id=str(summary.id),
        user_id=str(current_user.id),
        widgets_created=widgets_created,
        ai_name=interpretation.get("name"),
    )

    return SummaryFromPromptResponse(
        id=summary.id,
        name=summary.name,
        interpretation=interpretation,
        widgets_created=widgets_created,
        message=f"Zusammenfassung mit {widgets_created} Widgets erstellt",
    )


@router.post("", response_model=SummaryResponse)
async def create_summary(
    data: SummaryCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Create a summary with manual configuration."""
    await check_rate_limit(request, "summary_create", identifier=str(current_user.id))

    # Check for duplicate name
    from app.utils.similarity import find_duplicate_custom_summary

    duplicate = await find_duplicate_custom_summary(
        session,
        user_id=current_user.id,
        name=data.name,
    )
    if duplicate:
        existing, reason = duplicate
        raise ValidationError(f"Ähnliche Zusammenfassung existiert bereits: {reason}")

    # Validate cron if provided
    if data.schedule_cron and not is_valid_cron_expression(data.schedule_cron):
        raise ValidationError("Invalid cron expression")

    summary = CustomSummary(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        original_prompt=data.original_prompt,
        interpreted_config=data.interpreted_config,
        layout_config=data.layout_config,
        trigger_type=SummaryTriggerType(data.trigger_type.value),
        schedule_cron=data.schedule_cron,
        trigger_category_id=data.trigger_category_id,
        trigger_preset_id=data.trigger_preset_id,
        status=SummaryStatus.DRAFT,
    )
    session.add(summary)
    await session.commit()
    await session.refresh(summary)

    return _summary_to_response(summary)


@router.get("", response_model=SummaryListResponse)
async def list_summaries(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = None,
    favorites_only: bool = False,
    search: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """List all summaries for the current user."""
    await check_rate_limit(request, "summary_list", identifier=str(current_user.id))

    query = select(CustomSummary).where(CustomSummary.user_id == current_user.id)

    # Apply filters
    if status:
        query = query.where(CustomSummary.status == SummaryStatus(status))
    if favorites_only:
        query = query.where(CustomSummary.is_favorite)
    if search:
        # Escape LIKE special characters to prevent SQL injection
        safe_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(CustomSummary.name.ilike(f"%{safe_search}%", escape="\\"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Apply pagination and ordering
    query = (
        query.order_by(CustomSummary.is_favorite.desc(), CustomSummary.updated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    result = await session.execute(query)
    summaries = result.scalars().all()

    return SummaryListResponse(
        items=[_summary_to_response(s) for s in summaries],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 1,
    )


# --- Schedule Presets (must be before /{summary_id} routes) ---


@router.get("/schedule-presets", response_model=list[dict])
async def get_schedule_presets(
    current_user: User = Depends(require_editor),
):
    """Get predefined schedule presets for UI convenience."""
    return [p.model_dump() for p in SCHEDULE_PRESETS]


@router.get("/{summary_id}", response_model=SummaryDetailResponse)
async def get_summary(
    summary_id: UUID,
    request: Request,
    include_widgets: bool = True,
    include_last_execution: bool = True,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Get details of a summary."""
    await check_rate_limit(request, "summary_read", identifier=str(current_user.id))

    query = select(CustomSummary).where(
        CustomSummary.id == summary_id,
        CustomSummary.user_id == current_user.id,
    )

    if include_widgets:
        query = query.options(selectinload(CustomSummary.widgets))

    result = await session.execute(query)
    summary = result.scalar_one_or_none()

    if not summary:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    # Build base response
    response_data = _summary_to_response(summary).model_dump()

    # Add widgets
    if include_widgets:
        response_data["widgets"] = [_widget_to_response(w) for w in summary.widgets]
    else:
        response_data["widgets"] = []

    # Add last execution with cache expiration check
    if include_last_execution:
        exec_result = await session.execute(
            select(SummaryExecution)
            .where(
                SummaryExecution.summary_id == summary_id,
                SummaryExecution.status == ExecutionStatus.COMPLETED,
            )
            .order_by(SummaryExecution.created_at.desc())
            .limit(1)
        )
        last_exec = exec_result.scalar_one_or_none()
        if last_exec:
            # Check cache expiration
            cache_age = datetime.now(UTC) - last_exec.created_at
            cache_ttl = timedelta(hours=DEFAULT_CACHE_TTL_HOURS)
            cache_expired = cache_age > cache_ttl

            response_data["last_execution"] = SummaryExecutionDetailResponse(
                id=last_exec.id,
                status=last_exec.status.value,  # Pass string, Pydantic coerces to schema enum
                triggered_by=last_exec.triggered_by,
                trigger_details=last_exec.trigger_details,
                has_changes=last_exec.has_changes,
                relevance_score=last_exec.relevance_score,
                relevance_reason=last_exec.relevance_reason,
                duration_ms=last_exec.duration_ms,
                created_at=last_exec.created_at,
                completed_at=last_exec.completed_at,
                cached_data=last_exec.cached_data,
                error_message=last_exec.error_message,
            )
            # Add cache metadata
            response_data["cache_expired"] = cache_expired
            response_data["cache_age_hours"] = cache_age.total_seconds() / 3600
        else:
            response_data["last_execution"] = None
            response_data["cache_expired"] = True
            response_data["cache_age_hours"] = None
    else:
        response_data["last_execution"] = None
        response_data["cache_expired"] = None
        response_data["cache_age_hours"] = None

    return SummaryDetailResponse(**response_data)


@router.put("/{summary_id}", response_model=SummaryResponse)
async def update_summary(
    summary_id: UUID,
    data: SummaryUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Update a summary's properties."""
    await check_rate_limit(request, "summary_update", identifier=str(current_user.id))

    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    # Update fields
    update_data = data.model_dump(exclude_none=True)

    # Validate and handle schedule changes
    if "schedule_cron" in update_data:
        cron = update_data["schedule_cron"]
        if cron and not is_valid_cron_expression(cron):
            raise ValidationError("Invalid cron expression")

    for key, value in update_data.items():
        if key == "trigger_type" and value:
            setattr(summary, key, SummaryTriggerType(value.value))
        elif key == "status" and value:
            setattr(summary, key, SummaryStatus(value.value))
        else:
            setattr(summary, key, value)

    # Recalculate next_run if schedule changed
    if summary.schedule_enabled and summary.schedule_cron:
        summary.next_run_at = calculate_next_run(summary.schedule_cron)
    elif not summary.schedule_enabled:
        summary.next_run_at = None

    await session.commit()
    await session.refresh(summary)

    return _summary_to_response(summary)


@router.delete("/{summary_id}", response_model=MessageResponse)
async def delete_summary(
    summary_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Delete a summary."""
    await check_rate_limit(request, "summary_delete", identifier=str(current_user.id))

    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    await session.delete(summary)
    await session.commit()

    logger.info(
        "summary_deleted",
        summary_id=str(summary_id),
        user_id=str(current_user.id),
    )

    return MessageResponse(message="Zusammenfassung gelöscht")


# --- Execution Endpoints ---


@router.post("/{summary_id}/execute", response_model=SummaryExecuteResponse)
async def execute_summary(
    summary_id: UUID,
    data: SummaryExecuteRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Execute a summary (manual trigger)."""
    await check_rate_limit(request, "summary_execute", identifier=str(current_user.id))

    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    executor = SummaryExecutor(session)
    execution = await executor.execute_summary(
        summary_id=summary_id,
        triggered_by="manual",
        force=data.force,
    )

    return SummaryExecuteResponse(
        execution_id=execution.id,
        status=execution.status.value,  # Pass string, Pydantic coerces to schema enum
        has_changes=execution.has_changes,
        cached_data=execution.cached_data if execution.status == ExecutionStatus.COMPLETED else None,
        message="Ausführung abgeschlossen"
        if execution.status == ExecutionStatus.COMPLETED
        else "Keine relevanten Änderungen",
    )


@router.post("/{summary_id}/check-updates", response_model=SummaryCheckUpdatesResponse)
async def check_summary_updates(
    summary_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Start checking for updates by crawling relevant data sources and syncing external APIs.

    This endpoint:
    1. Resolves all relevant data sources and external APIs for the summary
    2. Starts crawl jobs for data sources and sync jobs for external APIs
    3. Returns a task ID for progress polling
    4. After all jobs complete, automatically updates the summary
    """
    await check_rate_limit(request, "summary_check_updates", identifier=str(current_user.id))

    # Load summary with widgets for source resolution
    result = await session.execute(
        select(CustomSummary).options(selectinload(CustomSummary.widgets)).where(CustomSummary.id == summary_id)
    )
    summary = result.scalar_one_or_none()

    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    # Resolve all relevant sources (DataSources + ExternalAPIs)
    from services.summaries.source_resolver import resolve_all_sources_for_summary

    resolved = await resolve_all_sources_for_summary(session, summary)

    if resolved.is_empty:
        raise ValidationError(
            "Keine Datenquellen für diese Zusammenfassung gefunden. "
            "Verknüpfen Sie eine Kategorie oder ein Preset, oder fügen Sie Widgets mit Entity-Typen hinzu."
        )

    # Get source names for progress display
    source_names = resolved.get_all_names()
    source_ids = [str(s.id) for s in resolved.data_sources]
    external_api_ids = [str(api.id) for api in resolved.external_apis]

    # Start background task
    from workers.summary_tasks import check_summary_updates as check_updates_task

    task = check_updates_task.delay(
        summary_id=str(summary_id),
        source_ids=source_ids,
        external_api_ids=external_api_ids,
        source_names=source_names,
        user_id=str(current_user.id),
    )

    logger.info(
        "check_updates_started",
        summary_id=str(summary_id),
        data_source_count=len(resolved.data_sources),
        external_api_count=len(resolved.external_apis),
        task_id=task.id,
    )

    return SummaryCheckUpdatesResponse(
        task_id=task.id,
        source_count=resolved.total_count,
        message=f"Prüfe {resolved.total_count} Quellen auf Änderungen...",
    )


@router.get("/{summary_id}/check-updates/{task_id}/status", response_model=CheckUpdatesProgressResponse)
async def get_check_updates_status(
    summary_id: UUID,
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Get progress status for a check-updates task."""
    await check_rate_limit(request, "summary_read", identifier=str(current_user.id))

    # Verify ownership
    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    # Get progress from Redis
    from workers.summary_tasks import get_check_progress

    progress = get_check_progress(task_id)

    if not progress:
        # Task might not have started yet or expired
        return CheckUpdatesProgressResponse(
            status=CheckUpdatesStatus.PENDING,
            total_sources=0,
            completed_sources=0,
            message="Task wird gestartet...",
        )

    return CheckUpdatesProgressResponse(
        status=CheckUpdatesStatus(progress.get("status", "pending")),
        total_sources=progress.get("total_sources", 0),
        completed_sources=progress.get("completed_sources", 0),
        current_source=progress.get("current_source"),
        message=progress.get("message", ""),
        error=progress.get("error"),
    )


@router.get("/{summary_id}/executions", response_model=list[SummaryExecutionResponse])
async def list_executions(
    summary_id: UUID,
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """List execution history for a summary with pagination."""
    await check_rate_limit(request, "summary_read", identifier=str(current_user.id))

    # Verify ownership
    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    result = await session.execute(
        select(SummaryExecution)
        .where(SummaryExecution.summary_id == summary_id)
        .order_by(SummaryExecution.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    executions = result.scalars().all()

    logger.debug(
        "executions_listed",
        summary_id=str(summary_id),
        count=len(executions),
        limit=limit,
        offset=offset,
    )

    return [_execution_to_response(e) for e in executions]


# --- Widget Endpoints ---


@router.post("/{summary_id}/widgets", response_model=SummaryWidgetResponse)
async def add_widget(
    summary_id: UUID,
    data: SummaryWidgetCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Add a widget to a summary."""
    await check_rate_limit(request, "summary_update", identifier=str(current_user.id))

    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    # Check widget count limit to prevent resource exhaustion
    count_result = await session.execute(
        select(func.count(SummaryWidget.id)).where(SummaryWidget.summary_id == summary_id)
    )
    widget_count = count_result.scalar() or 0

    if widget_count >= MAX_WIDGETS_PER_SUMMARY:
        raise ValidationError(
            f"Widget-Limit erreicht ({MAX_WIDGETS_PER_SUMMARY}). "
            "Bitte entfernen Sie bestehende Widgets, bevor Sie neue hinzufügen."
        )

    # Get max display_order
    result = await session.execute(
        select(func.max(SummaryWidget.display_order)).where(SummaryWidget.summary_id == summary_id)
    )
    max_order = result.scalar() or 0

    widget = SummaryWidget(
        summary_id=summary_id,
        widget_type=SummaryWidgetType(data.widget_type.value),
        title=data.title,
        subtitle=data.subtitle,
        position_x=data.position_x,
        position_y=data.position_y,
        width=data.width,
        height=data.height,
        query_config=data.query_config.model_dump() if data.query_config else {},
        visualization_config=data.visualization_config.model_dump() if data.visualization_config else {},
        display_order=max_order + 1,
    )
    session.add(widget)
    await session.commit()
    await session.refresh(widget)

    return _widget_to_response(widget)


@router.put("/{summary_id}/widgets/{widget_id}", response_model=SummaryWidgetResponse)
async def update_widget(
    summary_id: UUID,
    widget_id: UUID,
    data: SummaryWidgetUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Update a widget."""
    await check_rate_limit(request, "summary_update", identifier=str(current_user.id))

    # Verify ownership via summary
    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    widget = await session.get(SummaryWidget, widget_id)
    if not widget or widget.summary_id != summary_id:
        raise NotFoundError("Widget", str(widget_id))

    # Update fields
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(widget, key, value)

    await session.commit()
    await session.refresh(widget)

    return _widget_to_response(widget)


@router.delete("/{summary_id}/widgets/{widget_id}", response_model=MessageResponse)
async def delete_widget(
    summary_id: UUID,
    widget_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Delete a widget."""
    await check_rate_limit(request, "summary_update", identifier=str(current_user.id))

    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    widget = await session.get(SummaryWidget, widget_id)
    if not widget or widget.summary_id != summary_id:
        raise NotFoundError("Widget", str(widget_id))

    await session.delete(widget)
    await session.commit()

    return MessageResponse(message="Widget gelöscht")


# --- Share Endpoints ---


@router.post("/{summary_id}/share", response_model=SummaryShareResponse)
async def create_share_link(
    summary_id: UUID,
    data: SummaryShareCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Create a shareable link for a summary."""
    await check_rate_limit(request, "summary_share", identifier=str(current_user.id))

    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    # Create share
    share = SummaryShare(
        summary_id=summary_id,
        password_hash=bcrypt.hash(data.password) if data.password else None,
        expires_at=(datetime.now(UTC) + timedelta(days=data.expires_days) if data.expires_days else None),
        allow_export=data.allow_export,
    )
    session.add(share)
    await session.commit()
    await session.refresh(share)

    return SummaryShareResponse(
        id=share.id,
        share_token=share.share_token,
        share_url=f"/shared/summary/{share.share_token}",
        has_password=share.password_hash is not None,
        expires_at=share.expires_at,
        allow_export=share.allow_export,
        view_count=share.view_count,
        last_viewed_at=share.last_viewed_at,
        is_active=share.is_active,
        created_at=share.created_at,
    )


@router.get("/{summary_id}/shares", response_model=list[SummaryShareResponse])
async def list_shares(
    summary_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """List all share links for a summary."""
    await check_rate_limit(request, "summary_read", identifier=str(current_user.id))

    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    result = await session.execute(
        select(SummaryShare).where(SummaryShare.summary_id == summary_id).order_by(SummaryShare.created_at.desc())
    )
    shares = result.scalars().all()

    return [
        SummaryShareResponse(
            id=s.id,
            share_token=s.share_token,
            share_url=f"/shared/summary/{s.share_token}",
            has_password=s.password_hash is not None,
            expires_at=s.expires_at,
            allow_export=s.allow_export,
            view_count=s.view_count,
            last_viewed_at=s.last_viewed_at,
            is_active=s.is_active,
            created_at=s.created_at,
        )
        for s in shares
    ]


@router.delete("/{summary_id}/shares/{share_id}", response_model=MessageResponse)
async def deactivate_share(
    summary_id: UUID,
    share_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Deactivate a share link."""
    await check_rate_limit(request, "summary_update", identifier=str(current_user.id))

    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    share = await session.get(SummaryShare, share_id)
    if not share or share.summary_id != summary_id:
        raise NotFoundError("Share-Link", str(share_id))

    share.is_active = False
    await session.commit()

    return MessageResponse(message="Share-Link deaktiviert")


# --- Favorite Toggle ---


@router.post("/{summary_id}/toggle-favorite", response_model=SummaryFavoriteToggleResponse)
async def toggle_favorite(
    summary_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Toggle favorite status for a summary."""
    await check_rate_limit(request, "summary_update", identifier=str(current_user.id))

    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    summary.is_favorite = not summary.is_favorite
    await session.commit()

    return SummaryFavoriteToggleResponse(
        id=summary.id,
        is_favorite=summary.is_favorite,
        message="Als Favorit markiert" if summary.is_favorite else "Favorit entfernt",
    )


# --- Export Endpoints ---


@router.get("/{summary_id}/export/{format}")
async def export_summary(
    summary_id: UUID,
    format: str,
    request: Request,
    execution_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Export a summary to PDF or Excel format.

    Args:
        summary_id: ID of the summary to export
        format: Export format ('pdf' or 'excel')
        execution_id: Optional specific execution to export
    """
    await check_rate_limit(request, "summary_export", identifier=str(current_user.id))

    # Verify ownership
    summary = await session.get(CustomSummary, summary_id)
    if not summary or summary.user_id != current_user.id:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    export_service = SummaryExportService(session)

    # Sanitize filename to prevent path traversal and header injection
    safe_filename = sanitize_filename(summary.name)

    if format.lower() == "pdf":
        try:
            pdf_bytes = await export_service.export_to_pdf(summary_id, execution_id)
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{safe_filename}.pdf"'},
            )
        except ImportError as e:
            raise ValidationError(str(e)) from None

    elif format.lower() == "excel":
        excel_bytes = await export_service.export_to_excel(summary_id, execution_id)
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{safe_filename}.xlsx"'},
        )

    else:
        raise ValidationError(f"Unbekanntes Export-Format: {format}. Erlaubt: pdf, excel")


# --- Smart Query Integration ---


class SmartQueryToSummaryRequest(BaseModel):
    """Request to create summary from smart query result."""

    query_text: str = Field(..., min_length=3, description="Original Smart Query text")
    query_result: dict[str, Any] = Field(..., description="Smart Query result with data and visualization")
    name: str | None = Field(None, max_length=255, description="Custom name (auto-generated if not provided)")
    description: str | None = Field(None, description="Optional description")


class AddToSummaryRequest(BaseModel):
    """Request to add smart query result to existing summary."""

    query_text: str = Field(..., min_length=3, description="Smart Query text")
    query_result: dict[str, Any] = Field(..., description="Smart Query result")


class DuplicateCheckRequest(BaseModel):
    """Request to check for duplicate summaries."""

    prompt: str = Field(..., min_length=3, description="Prompt to check")
    entity_types: list[str] | None = Field(None, description="Entity types in the query")


class DuplicateCandidateResponse(BaseModel):
    """Response for duplicate candidate."""

    summary_id: str
    name: str
    description: str | None
    status: str
    similarity_score: float
    match_reasons: list[str]
    original_prompt: str


from pydantic import BaseModel, Field  # noqa: E402


@router.post("/from-smart-query", response_model=SummaryResponse)
async def create_from_smart_query(
    data: SmartQueryToSummaryRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Create a new summary from a Smart Query result.

    This endpoint allows saving Smart Query Plan Mode results
    as persistent dashboard summaries.
    """
    await check_rate_limit(request, "summary_create", identifier=str(current_user.id))

    from services.summaries.query_to_summary import create_summary_from_smart_query

    summary = await create_summary_from_smart_query(
        session=session,
        user_id=current_user.id,
        query_text=data.query_text,
        query_result=data.query_result,
        name=data.name,
        description=data.description,
    )

    logger.info(
        "summary_created_from_smart_query",
        summary_id=str(summary.id),
        user_id=str(current_user.id),
    )

    return _summary_to_response(summary)


@router.post("/{summary_id}/add-from-smart-query", response_model=SummaryWidgetResponse)
async def add_widget_from_smart_query(
    summary_id: UUID,
    data: AddToSummaryRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Add a Smart Query result as a new widget to an existing summary.

    This enables building complex dashboards from multiple queries.
    """
    await check_rate_limit(request, "summary_update", identifier=str(current_user.id))

    from services.summaries.query_to_summary import add_smart_query_to_existing_summary

    try:
        widget = await add_smart_query_to_existing_summary(
            session=session,
            summary_id=summary_id,
            user_id=current_user.id,
            query_text=data.query_text,
            query_result=data.query_result,
        )
    except ValueError:
        raise NotFoundError("Zusammenfassung", str(summary_id)) from None

    return _widget_to_response(widget)


@router.post("/check-duplicates", response_model=list[DuplicateCandidateResponse])
async def check_duplicates(
    data: DuplicateCheckRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Check for potentially duplicate summaries before creating a new one.

    Returns a list of similar existing summaries with similarity scores.
    """
    await check_rate_limit(request, "summary_read", identifier=str(current_user.id))

    from services.summaries.duplicate_detector import find_duplicate_summaries

    candidates = await find_duplicate_summaries(
        session=session,
        user_id=current_user.id,
        prompt=data.prompt,
        entity_types=data.entity_types,
        threshold=0.4,  # Lower threshold to catch more potential duplicates
        limit=5,
    )

    return [DuplicateCandidateResponse(**c.to_dict()) for c in candidates]


# --- Category/Analysis Theme Integration ---


class CreateFromCategoryRequest(BaseModel):
    """Request to create summary from a category/analysis theme."""

    category_id: UUID = Field(..., description="Category/Analysis Theme ID")
    name: str | None = Field(None, max_length=255, description="Custom name")
    description: str | None = Field(None, description="Optional description")
    auto_trigger: bool = Field(True, description="Automatically trigger on category crawl")


@router.post("/from-category", response_model=SummaryFromPromptResponse)
async def create_from_category(
    data: CreateFromCategoryRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Create a summary from an Analysis Theme/Category.

    This endpoint:
    1. Checks for existing summaries for this category
    2. If found, returns duplicates for user decision
    3. If not, creates a new summary with category trigger
    """
    await check_rate_limit(request, "summary_create", identifier=str(current_user.id))

    from app.models import Category
    from services.summaries.duplicate_detector import check_summary_exists_for_category

    # Get category
    category = await session.get(Category, data.category_id)
    if not category:
        raise NotFoundError("Analysethema", str(data.category_id))

    # Check for existing summary
    existing = await check_summary_exists_for_category(
        session=session,
        user_id=current_user.id,
        category_id=data.category_id,
    )

    if existing:
        # Return existing summary info
        return SummaryFromPromptResponse(
            summary=_summary_to_response(existing),
            widgets=[],
            message=f"Für dieses Analysethema existiert bereits eine Zusammenfassung: '{existing.name}'",
            duplicate_found=True,
        )

    # Generate prompt from category
    prompt = f"Zeige alle Daten und Ergebnisse für das Analysethema '{category.name}'"
    if category.description:
        prompt += f": {category.description}"

    # Use AI interpreter to create summary
    result = await interpret_summary_prompt(
        prompt=prompt,
        session=session,
    )

    if not result:
        raise ValidationError("KI-Interpretation fehlgeschlagen")

    # Create summary with category trigger
    summary = CustomSummary(
        user_id=current_user.id,
        name=data.name or f"Zusammenfassung: {category.name}",
        description=data.description or category.description,
        original_prompt=prompt,
        interpreted_config=result.get("interpreted_config", {}),
        layout_config={"columns": 4, "row_height": 150},
        status=SummaryStatus.ACTIVE,
        trigger_type=SummaryTriggerType.CRAWL_CATEGORY if data.auto_trigger else SummaryTriggerType.MANUAL,
        trigger_category_id=data.category_id if data.auto_trigger else None,
        schedule_enabled=data.auto_trigger,
        check_relevance=True,
        relevance_threshold=0.3,
        auto_expand=False,
        is_favorite=False,
    )
    session.add(summary)
    await session.flush()

    # Create widgets
    widgets = []
    for widget_config in result.get("widgets", []):
        widget = SummaryWidget(
            summary_id=summary.id,
            widget_type=SummaryWidgetType(widget_config.get("widget_type", "table")),
            title=widget_config.get("title", "Widget"),
            subtitle=widget_config.get("subtitle"),
            position_x=widget_config.get("position", {}).get("x", 0),
            position_y=widget_config.get("position", {}).get("y", 0),
            width=widget_config.get("position", {}).get("w", 2),
            height=widget_config.get("position", {}).get("h", 2),
            query_config=widget_config.get("query_config", {}),
            visualization_config=widget_config.get("visualization_config", {}),
            display_order=widget_config.get("display_order", 0),
        )
        session.add(widget)
        widgets.append(widget)

    await session.commit()
    await session.refresh(summary)

    logger.info(
        "summary_created_from_category",
        summary_id=str(summary.id),
        category_id=str(data.category_id),
        user_id=str(current_user.id),
    )

    return SummaryFromPromptResponse(
        summary=_summary_to_response(summary),
        widgets=[_widget_to_response(w) for w in widgets],
        message=f"Zusammenfassung für '{category.name}' erstellt",
        duplicate_found=False,
    )


# =============================================================================
# Auto-Expand Endpoints
# =============================================================================


class ApplyExpansionRequest(BaseModel):
    """Request to apply auto-expansion suggestions."""

    suggestion_indices: list[int] = Field(
        ...,
        description="Indices of suggestions to apply from expansion_suggestions array",
    )


class ApplyExpansionResponse(BaseModel):
    """Response after applying expansion suggestions."""

    widgets_created: int
    widgets: list[SummaryWidgetResponse]
    message: str


@router.post(
    "/{summary_id}/apply-expansion",
    response_model=ApplyExpansionResponse,
    summary="Apply auto-expand suggestions",
    description="Apply selected auto-expand widget suggestions from the latest execution.",
)
async def apply_expansion_suggestions(
    summary_id: UUID,
    data: ApplyExpansionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Apply auto-expansion suggestions from the latest execution.

    Takes a list of suggestion indices and creates the corresponding widgets.
    """
    await check_rate_limit(request, "summary_update", identifier=str(current_user.id))

    from services.summaries.auto_expand import WidgetSuggestion, apply_expansion

    # Get summary
    result = await session.execute(
        select(CustomSummary)
        .options(selectinload(CustomSummary.executions))
        .where(
            CustomSummary.id == summary_id,
            CustomSummary.user_id == current_user.id,
        )
    )
    summary = result.scalar_one_or_none()

    if not summary:
        raise NotFoundError("Zusammenfassung", str(summary_id))

    # Get latest execution with suggestions
    latest_exec = await session.execute(
        select(SummaryExecution)
        .where(
            SummaryExecution.summary_id == summary_id,
            SummaryExecution.expansion_suggestions.isnot(None),
        )
        .order_by(SummaryExecution.created_at.desc())
        .limit(1)
    )
    execution = latest_exec.scalar_one_or_none()

    if not execution or not execution.expansion_suggestions:
        raise ValidationError("Keine Erweiterungs-Vorschläge gefunden")

    # Filter selected suggestions
    all_suggestions = execution.expansion_suggestions
    selected = []
    for idx in data.suggestion_indices:
        if 0 <= idx < len(all_suggestions):
            sugg_dict = all_suggestions[idx]
            selected.append(
                WidgetSuggestion(
                    widget_type=SummaryWidgetType(sugg_dict["widget_type"]),
                    title=sugg_dict["title"],
                    subtitle=sugg_dict.get("subtitle"),
                    query_config=sugg_dict.get("query_config", {}),
                    reason=sugg_dict.get("reason", ""),
                    confidence=sugg_dict.get("confidence", 0.5),
                )
            )

    if not selected:
        raise ValidationError("Keine gültigen Vorschläge ausgewählt")

    # Apply expansion
    created_widgets = await apply_expansion(
        session=session,
        summary_id=summary_id,
        suggestions=selected,
        max_widgets=len(selected),
    )

    return ApplyExpansionResponse(
        widgets_created=len(created_widgets),
        widgets=[_widget_to_response(w) for w in created_widgets],
        message=f"{len(created_widgets)} Widget(s) hinzugefügt",
    )
