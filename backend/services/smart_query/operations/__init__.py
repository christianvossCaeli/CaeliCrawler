"""
Write Operations Framework.

This module provides a command pattern implementation for Smart Query write operations.
It allows for modular, testable, and maintainable operation handlers.

Modules:
- pysis_ops: PySis analyze, enrich, push operations
- entity_ops: Entity update, delete operations
- facet_ops: FacetType create, assign, delete, history operations
- batch_ops: Batch operations on multiple entities
- export_ops: Export, undo, history operations
- api_import_ops: API fetch and create operations
- category_ops: Category linking and relation type operations
- discovery: Source discovery operations

Usage:
    # Register operations
    from .base import register_operation

    @register_operation("create_entity")
    class CreateEntityOperation(WriteOperation):
        async def execute(self, session, data):
            ...

    # Execute operations
    from .base import execute_operation

    result = await execute_operation(session, command, user_id)
"""

from .base import (
    WriteOperation,
    OperationResult,
    execute_operation,
    register_operation,
    get_operation,
    OPERATIONS_REGISTRY,
)

# Import operations to trigger registration
# Each module uses @register_operation decorator
from . import discovery  # noqa: F401
from . import pysis_ops  # noqa: F401
from . import entity_ops  # noqa: F401
from . import facet_ops  # noqa: F401
from . import batch_ops  # noqa: F401
from . import export_ops  # noqa: F401
from . import api_import_ops  # noqa: F401
from . import category_ops  # noqa: F401

__all__ = [
    "WriteOperation",
    "OperationResult",
    "execute_operation",
    "register_operation",
    "get_operation",
    "OPERATIONS_REGISTRY",
]
