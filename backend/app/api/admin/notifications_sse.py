"""Server-Sent Events (SSE) endpoint for real-time notification updates.

SSE provides push-based updates from server to client, eliminating the need
for polling and reducing server load while improving user experience.
"""

import asyncio
import json
from collections.abc import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_sse
from app.database import get_session
from app.models import User
from app.services.notification_broadcast import notification_broadcaster
from services.notifications import NotificationService

router = APIRouter()
logger = structlog.get_logger()

# Update interval for initial state
SSE_INITIAL_DELAY = 0.5


async def _generate_notification_events(
    user: User,
    session: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for notification updates.

    Yields events in SSE format:
    - event: init - Initial unread count
    - event: new_notification - New notification received
    - event: notification_read - Notification marked as read
    - event: all_read - All notifications marked as read
    - event: count_update - Unread count updated
    - event: heartbeat - Keep-alive (as comment)
    """
    # Send initial state
    try:
        service = NotificationService(session, None)
        unread_count = await service.get_unread_count(user.id)

        init_data = {
            "unread_count": unread_count,
        }
        yield f"event: init\ndata: {json.dumps(init_data)}\n\n"

        # Subscribe to user's notification channel
        async for event in notification_broadcaster.subscribe(user.id):
            event_type = event.get("type", "unknown")
            event_data = event.get("data", {})

            if event_type == "heartbeat":
                # Heartbeat as SSE comment to keep connection alive
                yield ": heartbeat\n\n"
            else:
                # Regular event
                yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

    except asyncio.CancelledError:
        logger.debug(f"SSE connection cancelled for user {user.id}")
        raise
    except Exception as e:
        logger.error(f"Error in notification SSE stream: {e}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@router.get("/events")
async def notification_events(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_sse),
):
    """
    Server-Sent Events stream for real-time notification updates.

    Requires SSE ticket authentication (get ticket from /api/auth/sse-ticket).

    Events:
    - `init`: Initial state with unread count
    - `new_notification`: New notification data
    - `notification_read`: Notification ID that was read
    - `all_read`: All notifications marked as read
    - `count_update`: Updated unread count
    - `error`: Error messages

    Usage:
    ```javascript
    // First get SSE ticket
    const ticketRes = await fetch('/api/auth/sse-ticket');
    const { ticket } = await ticketRes.json();

    // Then connect to SSE
    const eventSource = new EventSource(
        `/api/admin/notifications/events?ticket=${ticket}`
    );

    eventSource.addEventListener('init', (e) => {
        const data = JSON.parse(e.data);
        console.log('Initial count:', data.unread_count);
    });

    eventSource.addEventListener('new_notification', (e) => {
        const notification = JSON.parse(e.data);
        console.log('New notification:', notification);
    });

    eventSource.addEventListener('count_update', (e) => {
        const data = JSON.parse(e.data);
        console.log('New count:', data.unread_count);
    });
    ```
    """
    return StreamingResponse(
        _generate_notification_events(user, session),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
