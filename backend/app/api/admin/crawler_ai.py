"""Admin API endpoints for AI task management."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditContext
from app.core.deps import require_editor
from app.core.exceptions import NotFoundError, ValidationError
from app.core.query_helpers import batch_fetch_by_ids
from app.database import get_session
from app.models import AITask, AITaskStatus, AITaskType, User
from app.models.audit_log import AuditAction
from app.schemas.common import MessageResponse
from app.schemas.crawl_job import (
    AITaskInfo,
    AITaskListResponse,
    RunningAITasksResponse,
)

router = APIRouter()


@router.get("/ai-tasks", response_model=AITaskListResponse)
async def list_ai_tasks(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: AITaskStatus | None = Query(default=None),
    task_type: AITaskType | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """List all AI tasks with pagination."""
    from app.models.pysis import PySisProcess

    query = select(AITask)

    if status:
        query = query.where(AITask.status == status)
    if task_type:
        query = query.where(AITask.task_type == task_type)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate (newest first)
    query = query.order_by(AITask.scheduled_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    tasks = result.scalars().all()

    # Batch fetch processes to avoid N+1 queries
    process_ids = {task.process_id for task in tasks if task.process_id}
    processes_dict = await batch_fetch_by_ids(session, PySisProcess, process_ids)

    # Enrich with process info
    items = []
    for task in tasks:
        source_name = None
        category_name = None
        if task.process_id:
            process = processes_dict.get(task.process_id)
            if process:
                source_name = process.name
                category_name = process.entity_name

        items.append(
            AITaskInfo(
                id=task.id,
                task_type=task.task_type.value,
                status=task.status.value,
                source_name=source_name,
                category_name=category_name,
                created_at=task.scheduled_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                error_message=task.error_message,
                progress_percent=task.progress_percent,
                celery_task_id=task.celery_task_id,
            )
        )

    return AITaskListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.get("/ai-tasks/running", response_model=RunningAITasksResponse)
async def get_running_ai_tasks(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Get all currently running AI tasks."""
    from app.models.pysis import PySisProcess

    result = await session.execute(select(AITask).where(AITask.status == AITaskStatus.RUNNING))
    running_tasks = result.scalars().all()

    # Batch fetch processes to avoid N+1 queries
    process_ids = {task.process_id for task in running_tasks if task.process_id}
    processes_dict = await batch_fetch_by_ids(session, PySisProcess, process_ids)

    tasks = []
    for task in running_tasks:
        source_name = None
        category_name = None
        if task.process_id:
            process = processes_dict.get(task.process_id)
            if process:
                source_name = process.name
                category_name = process.entity_name

        tasks.append(
            AITaskInfo(
                id=task.id,
                task_type=task.task_type.value,
                status=task.status.value,
                source_name=source_name,
                category_name=category_name,
                created_at=task.scheduled_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                error_message=task.error_message,
                progress_percent=task.progress_percent,
                celery_task_id=task.celery_task_id,
            )
        )

    return RunningAITasksResponse(
        tasks=tasks,
        total=len(tasks),
    )


@router.post("/ai-tasks/{task_id}/cancel", response_model=MessageResponse)
async def cancel_ai_task(
    task_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Cancel a running AI task."""
    from app.models.pysis import PySisProcess

    task = await session.get(AITask, task_id)
    if not task:
        raise NotFoundError("AI Task", str(task_id))

    if task.status != AITaskStatus.RUNNING:
        raise ValidationError("Can only cancel running tasks")

    # Get process info for audit
    process_name = None
    if task.process_id:
        process = await session.get(PySisProcess, task.process_id)
        process_name = process.name if process else None

    async with AuditContext(session, current_user, request) as audit:
        # Revoke Celery task - import here to avoid issues when Celery isn't running
        if task.celery_task_id:
            from workers.celery_app import celery_app

            celery_app.control.revoke(task.celery_task_id, terminate=True)

        task.status = AITaskStatus.CANCELLED

        audit.track_action(
            action=AuditAction.CRAWLER_STOP,
            entity_type="AITask",
            entity_id=task.id,
            entity_name=process_name or str(task_id),
            changes={
                "cancelled": True,
                "task_type": task.task_type.value,
                "process_name": process_name,
                "progress_percent": task.progress_percent,
            },
        )

        await session.commit()

    return MessageResponse(message="AI Task cancelled")
