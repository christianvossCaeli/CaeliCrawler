"""
AI Tasks API - Endpunkte für AI-Task Status und Verwaltung.

Bietet:
- Task-Status-Abfragen für Polling
- Task-Ergebnisse abrufen
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.ai_task import AITask, AITaskStatus, AITaskType
from app.models.user import User
from app.core.deps import get_current_user

router = APIRouter(tags=["AI Tasks"])


# Response Schemas


class AITaskStatusResponse(BaseModel):
    """Status eines AI-Tasks für Polling."""

    task_id: str
    task_type: str
    status: str
    name: str
    description: Optional[str] = None

    # Progress
    progress_current: int = 0
    progress_total: int = 0
    progress_percent: float = 0.0
    current_item: Optional[str] = None

    # Timing
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None

    # Results
    fields_extracted: int = 0
    avg_confidence: Optional[float] = None

    # Error
    error_message: Optional[str] = None

    # Entity reference (if applicable)
    entity_id: Optional[str] = None


class AITaskResultResponse(BaseModel):
    """Task-Ergebnis mit Preview-Daten."""

    task_id: str
    status: str
    result_data: Dict[str, Any] = Field(default_factory=dict)


# Endpoints


@router.get("/status", response_model=AITaskStatusResponse)
async def get_ai_task_status(
    task_id: UUID = Query(..., description="AI-Task ID"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Gibt den aktuellen Status eines AI-Tasks zurück.

    Wird für Polling verwendet um den Fortschritt von Hintergrund-Tasks zu verfolgen.
    """
    task = await session.get(AITask, task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task nicht gefunden: {task_id}")

    return AITaskStatusResponse(
        task_id=str(task.id),
        task_type=task.task_type.value,
        status=task.status.value,
        name=task.name,
        description=task.description,
        progress_current=task.progress_current,
        progress_total=task.progress_total,
        progress_percent=task.progress_percent,
        current_item=task.current_item,
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        duration_seconds=task.duration_seconds,
        fields_extracted=task.fields_extracted,
        avg_confidence=task.avg_confidence,
        error_message=task.error_message,
        entity_id=str(task.entity_id) if task.entity_id else None,
    )


@router.get("/result", response_model=AITaskResultResponse)
async def get_ai_task_result(
    task_id: UUID = Query(..., description="AI-Task ID"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Gibt die Ergebnis-Daten eines abgeschlossenen AI-Tasks zurück.

    Enthält Preview-Daten für Review (z.B. vorgeschlagene Facet-Änderungen).
    """
    task = await session.get(AITask, task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task nicht gefunden: {task_id}")

    if task.status not in [AITaskStatus.COMPLETED, AITaskStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Task noch nicht abgeschlossen. Status: {task.status.value}",
        )

    return AITaskResultResponse(
        task_id=str(task.id),
        status=task.status.value,
        result_data=task.result_data or {},
    )


@router.get("/by-entity", response_model=List[AITaskStatusResponse])
async def get_entity_tasks(
    entity_id: UUID = Query(..., description="Entity-ID"),
    task_type: Optional[str] = Query(None, description="Filter nach Task-Typ"),
    status: Optional[str] = Query(None, description="Filter nach Status"),
    limit: int = Query(10, ge=1, le=50, description="Max. Anzahl"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Listet AI-Tasks für eine Entity auf.

    Nützlich um laufende oder kürzlich abgeschlossene Tasks zu sehen.
    """
    query = select(AITask).where(AITask.entity_id == entity_id)

    if task_type:
        try:
            task_type_enum = AITaskType(task_type)
            query = query.where(AITask.task_type == task_type_enum)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Ungültiger Task-Typ: {task_type}"
            )

    if status:
        try:
            status_enum = AITaskStatus(status)
            query = query.where(AITask.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Ungültiger Status: {status}")

    query = query.order_by(AITask.scheduled_at.desc()).limit(limit)

    result = await session.execute(query)
    tasks = result.scalars().all()

    return [
        AITaskStatusResponse(
            task_id=str(task.id),
            task_type=task.task_type.value,
            status=task.status.value,
            name=task.name,
            description=task.description,
            progress_current=task.progress_current,
            progress_total=task.progress_total,
            progress_percent=task.progress_percent,
            current_item=task.current_item,
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            duration_seconds=task.duration_seconds,
            fields_extracted=task.fields_extracted,
            avg_confidence=task.avg_confidence,
            error_message=task.error_message,
            entity_id=str(task.entity_id) if task.entity_id else None,
        )
        for task in tasks
    ]
