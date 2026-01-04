"""Reminder API endpoints for the AI Chat Assistant."""

from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_session
from app.models.entity import Entity
from app.models.reminder import Reminder, ReminderRepeat, ReminderStatus
from app.models.user import User

router = APIRouter(prefix="/reminders", tags=["assistant-reminders"])


@router.get("")
async def list_reminders(
    status: str | None = Query(None, description="Filter by status: pending, sent, dismissed"),
    include_past: bool = Query(False, description="Include past reminders"),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    List reminders for the current user.

    Returns upcoming and recent reminders.
    """
    from datetime import datetime, timedelta

    # Build query
    query = select(Reminder).where(Reminder.user_id == current_user.id)

    # Filter by status
    if status:
        try:
            status_enum = ReminderStatus(status)
            query = query.where(Reminder.status == status_enum)
        except ValueError:
            pass

    # Filter out past reminders unless requested
    if not include_past:
        # Show pending reminders or recently sent/dismissed (within 24h)
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        query = query.where(
            or_(
                Reminder.status == ReminderStatus.PENDING,
                Reminder.sent_at >= cutoff,
                Reminder.dismissed_at >= cutoff,
            )
        )

    query = query.order_by(Reminder.remind_at.asc()).limit(limit)

    result = await session.execute(query)
    reminders = result.scalars().all()

    return {
        "items": [
            {
                "id": str(r.id),
                "message": r.message,
                "title": r.title,
                "remind_at": r.remind_at.isoformat(),
                "repeat": r.repeat.value,
                "status": r.status.value,
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "entity_type": r.entity_type,
                "entity_name": r.entity_name,
                "created_at": r.created_at.isoformat(),
            }
            for r in reminders
        ],
        "total": len(reminders),
    }


@router.post("")
async def create_reminder(
    data: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create a new reminder.

    ## Request Body
    - `message`: The reminder message (required)
    - `remind_at`: ISO datetime when to trigger (required)
    - `title`: Optional title
    - `entity_id`: Optional entity to link
    - `entity_type`: Entity type if entity_id provided
    - `repeat`: Repeat interval: none, daily, weekly, monthly

    Returns the created reminder.
    """
    from datetime import datetime

    # Parse remind_at
    remind_at_str = data.get("remind_at")
    if not remind_at_str:
        raise HTTPException(status_code=400, detail="remind_at ist erforderlich")

    try:
        if isinstance(remind_at_str, str):
            remind_at = datetime.fromisoformat(remind_at_str.replace("Z", "+00:00"))
        else:
            remind_at = remind_at_str
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Ungültiges Datumsformat für remind_at") from None

    # Parse repeat
    repeat_str = data.get("repeat", "none")
    try:
        repeat = ReminderRepeat(repeat_str)
    except ValueError:
        repeat = ReminderRepeat.NONE

    # Get entity info if provided
    entity_id = data.get("entity_id")
    entity_type = data.get("entity_type")
    entity_name = None

    if entity_id:
        try:
            entity_uuid = UUID(entity_id)
            result = await session.execute(
                select(Entity).where(Entity.id == entity_uuid)
            )
            entity = result.scalar_one_or_none()
            if entity:
                entity_name = entity.name
                entity_type = entity_type or entity.entity_type.slug if entity.entity_type else None
        except (ValueError, TypeError):
            pass

    # Create reminder
    reminder = Reminder(
        user_id=current_user.id,
        message=data.get("message", "Erinnerung"),
        title=data.get("title"),
        remind_at=remind_at,
        repeat=repeat,
        status=ReminderStatus.PENDING,
        entity_id=entity_id if entity_id else None,
        entity_type=entity_type,
        entity_name=entity_name,
    )

    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)

    return {
        "success": True,
        "reminder": {
            "id": str(reminder.id),
            "message": reminder.message,
            "title": reminder.title,
            "remind_at": reminder.remind_at.isoformat(),
            "repeat": reminder.repeat.value,
            "status": reminder.status.value,
            "entity_id": str(reminder.entity_id) if reminder.entity_id else None,
            "entity_type": reminder.entity_type,
            "entity_name": reminder.entity_name,
            "created_at": reminder.created_at.isoformat(),
        },
        "message": f"Erinnerung erstellt für {reminder.remind_at.strftime('%d.%m.%Y %H:%M')}",
    }


@router.delete("/{reminder_id}")
async def delete_reminder(
    reminder_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete/cancel a reminder."""
    try:
        reminder_uuid = UUID(reminder_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungültige Reminder-ID") from None

    result = await session.execute(
        select(Reminder).where(
            Reminder.id == reminder_uuid,
            Reminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()

    if not reminder:
        raise HTTPException(status_code=404, detail="Erinnerung nicht gefunden")

    reminder.cancel()
    await session.commit()

    return {"success": True, "message": "Erinnerung gelöscht"}


@router.post("/{reminder_id}/dismiss")
async def dismiss_reminder(
    reminder_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Dismiss a reminder (mark as acknowledged)."""
    try:
        reminder_uuid = UUID(reminder_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungültige Reminder-ID") from None

    result = await session.execute(
        select(Reminder).where(
            Reminder.id == reminder_uuid,
            Reminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()

    if not reminder:
        raise HTTPException(status_code=404, detail="Erinnerung nicht gefunden")

    reminder.dismiss()
    await session.commit()

    return {"success": True, "message": "Erinnerung bestätigt"}


@router.post("/{reminder_id}/snooze")
async def snooze_reminder(
    reminder_id: str,
    data: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Snooze a reminder to a new time.

    Request body:
    - `remind_at`: New datetime to remind (ISO format)
    """
    from datetime import datetime

    try:
        reminder_uuid = UUID(reminder_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungültige Reminder-ID") from None

    if "remind_at" not in data:
        raise HTTPException(status_code=400, detail="remind_at ist erforderlich")

    try:
        new_remind_at = datetime.fromisoformat(data["remind_at"].replace("Z", "+00:00"))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Ungültiges Datumsformat") from None

    result = await session.execute(
        select(Reminder).where(
            Reminder.id == reminder_uuid,
            Reminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()

    if not reminder:
        raise HTTPException(status_code=404, detail="Erinnerung nicht gefunden")

    # Update remind_at and ensure status is pending
    reminder.remind_at = new_remind_at
    reminder.status = ReminderStatus.PENDING
    await session.commit()

    return {
        "success": True,
        "message": f"Erinnerung verschoben auf {new_remind_at.strftime('%d.%m.%Y %H:%M')}",
        "remind_at": new_remind_at.isoformat(),
    }


@router.get("/due")
async def get_due_reminders(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get all due (pending and past remind_at) reminders for the current user.

    Used for displaying reminder notifications in the UI.
    """
    from datetime import datetime

    result = await session.execute(
        select(Reminder).where(
            and_(
                Reminder.user_id == current_user.id,
                Reminder.status == ReminderStatus.PENDING,
                Reminder.remind_at <= datetime.now(UTC),
            )
        ).order_by(Reminder.remind_at.asc())
    )
    reminders = result.scalars().all()

    return {
        "items": [
            {
                "id": str(r.id),
                "message": r.message,
                "title": r.title,
                "remind_at": r.remind_at.isoformat(),
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "entity_type": r.entity_type,
                "entity_name": r.entity_name,
            }
            for r in reminders
        ],
        "count": len(reminders),
    }
