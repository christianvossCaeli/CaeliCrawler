"""Command Pattern implementation for Smart Query write operations.

This module provides a clean, extensible Command Pattern for executing
write operations. Each command encapsulates a single operation with its
validation, execution, and result handling.

Usage:
    from services.smart_query.commands import CommandRegistry

    registry = CommandRegistry()
    result = await registry.execute("create_entity", session, data, user_id)

Adding new commands:
    1. Create a new class inheriting from BaseCommand
    2. Implement validate() and execute() methods
    3. Register with @registry.register("operation_name")
"""

from .api_sync_commands import (
    SetupAPIFacetSyncCommand,
    TriggerAPISyncCommand,
)
from .base import BaseCommand, CommandResult
from .entity_commands import (
    CreateEntityCommand,
    DeleteEntityCommand,
    UpdateEntityCommand,
)
from .facet_commands import (
    CreateFacetCommand,
    CreateFacetTypeCommand,
    DeleteFacetCommand,
)
from .query_commands import (
    QueryDataCommand,
    QueryExternalCommand,
    QueryFacetHistoryCommand,
)
from .registry import CommandRegistry

__all__ = [
    "BaseCommand",
    "CommandResult",
    "CommandRegistry",
    "CreateEntityCommand",
    "UpdateEntityCommand",
    "DeleteEntityCommand",
    "CreateFacetCommand",
    "CreateFacetTypeCommand",
    "DeleteFacetCommand",
    "SetupAPIFacetSyncCommand",
    "TriggerAPISyncCommand",
    "QueryDataCommand",
    "QueryExternalCommand",
    "QueryFacetHistoryCommand",
]
