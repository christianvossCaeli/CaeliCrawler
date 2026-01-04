"""Core chat API endpoints for the AI Chat Assistant."""

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_optional
from app.core.rate_limit import check_rate_limit
from app.database import get_session
from app.models.user import User
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from services.assistant_service import AssistantService

from .attachments import get_attachment

router = APIRouter(tags=["assistant-chat"])


@router.post("/chat", response_model=AssistantChatResponse)
async def chat(
    http_request: Request,
    request: AssistantChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> AssistantChatResponse:
    """
    Send a message to the AI assistant and get a response.

    The assistant can:
    - Answer questions about entities, facets, and relations
    - Execute searches using natural language
    - Suggest navigation to specific entities
    - Preview and execute inline edits (in write mode)
    - Provide contextual help

    ## Context
    The `context` object tells the assistant about the current app state:
    - `current_route`: The current page URL
    - `current_entity_id`: ID of the entity being viewed (if on detail page)
    - `current_entity_type`: Type of the current entity
    - `view_mode`: Current view mode (dashboard, list, detail, edit)

    ## Modes
    - `read`: Default mode, only allows queries and navigation
    - `write`: Allows inline edits with preview/confirmation flow

    ## Slash Commands
    - `/help [topic]` - Get help
    - `/search <query>` - Search entities
    - `/create <details>` - Create new data (redirects to Smart Query)
    - `/summary` - Summarize current entity
    - `/navigate <entity>` - Navigate to an entity

    ## Response Types
    The response contains different data based on the intent:
    - `query_result`: Search results
    - `action_preview`: Preview of an edit operation (requires confirmation)
    - `navigation`: Suggested navigation target
    - `redirect_to_smart_query`: Redirect for complex operations
    - `help`: Help information
    - `error`: Error message
    """
    # Rate limiting
    user_id = str(current_user.id) if current_user else None
    await check_rate_limit(http_request, "assistant_chat", identifier=user_id)

    # Load attachments if provided
    attachments = []
    for attachment_id in request.attachment_ids:
        attachment_data = get_attachment(attachment_id)
        if attachment_data:
            attachments.append({
                "id": attachment_id,
                "content": attachment_data["content"],
                "filename": attachment_data["filename"],
                "content_type": attachment_data["content_type"],
                "size": attachment_data["size"],
            })

    assistant = AssistantService(session)
    return await assistant.process_message(
        message=request.message,
        context=request.context,
        conversation_history=request.conversation_history,
        mode=request.mode,
        language=request.language,
        attachments=attachments
    )


@router.post("/chat-stream")
async def chat_stream(
    http_request: Request,
    request: AssistantChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> StreamingResponse:
    """
    Send a message to the AI assistant and receive a streaming response.

    This endpoint uses Server-Sent Events (SSE) to stream the response
    in real-time as it's generated.

    ## Event Types
    The stream sends JSON events with the following types:
    - `status`: Processing status updates (e.g., "Searching...", "Analyzing...")
    - `intent`: The classified intent type
    - `token`: Individual tokens from LLM response (for real-time text display)
    - `item`: Individual result items (streamed one by one)
    - `complete`: Final response data
    - `error`: Error information

    ## Example Event Format
    ```
    data: {"type": "status", "message": "Searching..."}

    data: {"type": "token", "content": "I "}

    data: {"type": "complete", "data": {...}}

    data: [DONE]
    ```
    """
    # Rate limiting
    user_id = str(current_user.id) if current_user else None
    await check_rate_limit(http_request, "assistant_stream", identifier=user_id)

    # Load attachments if provided
    attachments = []
    for attachment_id in request.attachment_ids:
        attachment_data = get_attachment(attachment_id)
        if attachment_data:
            attachments.append({
                "id": attachment_id,
                "content": attachment_data["content"],
                "filename": attachment_data["filename"],
                "content_type": attachment_data["content_type"],
                "size": attachment_data["size"],
            })

    assistant = AssistantService(session)

    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for chunk in assistant.process_message_stream(
                message=request.message,
                context=request.context,
                conversation_history=request.conversation_history,
                mode=request.mode,
                language=request.language,
                attachments=attachments
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
