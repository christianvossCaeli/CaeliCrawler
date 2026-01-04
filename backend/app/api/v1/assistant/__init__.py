"""
AI Chat Assistant API Endpoints

This module provides all endpoints for the AI assistant feature,
organized into logical groups:

- Core: chat, chat-stream
- Attachments: upload, delete, save-to-entity
- Actions: execute-action, batch-action, create-facet-type
- Wizards: start, respond, back, cancel
- Reminders: CRUD operations for reminders
- Suggestions: commands, suggestions, insights

All endpoints are accessible via the main router which aggregates
all sub-routers.
"""

from fastapi import APIRouter

from ._core import router as core_router
from .actions import router as actions_router
from .attachments import router as attachments_router
from .reminders import router as reminders_router
from .suggestions import router as suggestions_router
from .wizards import router as wizards_router

# Create main router that includes all sub-routers
router = APIRouter()

# Include all sub-routers
router.include_router(core_router)
router.include_router(attachments_router)
router.include_router(actions_router)
router.include_router(suggestions_router)
router.include_router(wizards_router)
router.include_router(reminders_router)

# Re-export for backwards compatibility
from ._core import chat, chat_stream
from .actions import (
    batch_action,
    cancel_batch,
    create_facet_type_via_assistant,
    execute_action,
    get_batch_status,
)
from .attachments import (
    delete_attachment,
    get_attachment,
    save_temp_attachments_to_entity,
    upload_attachment,
)
from .reminders import (
    create_reminder,
    delete_reminder,
    dismiss_reminder,
    get_due_reminders,
    list_reminders,
    snooze_reminder,
)
from .suggestions import get_commands, get_insights, get_suggestions
from .wizards import (
    get_available_wizards,
    start_wizard,
    wizard_back,
    wizard_cancel,
    wizard_respond,
)

__all__ = [
    "router",
    # Core
    "chat",
    "chat_stream",
    # Attachments
    "upload_attachment",
    "delete_attachment",
    "get_attachment",
    "save_temp_attachments_to_entity",
    # Actions
    "create_facet_type_via_assistant",
    "execute_action",
    "batch_action",
    "get_batch_status",
    "cancel_batch",
    # Suggestions
    "get_commands",
    "get_suggestions",
    "get_insights",
    # Wizards
    "get_available_wizards",
    "start_wizard",
    "wizard_respond",
    "wizard_back",
    "wizard_cancel",
    # Reminders
    "list_reminders",
    "create_reminder",
    "delete_reminder",
    "dismiss_reminder",
    "snooze_reminder",
    "get_due_reminders",
]
