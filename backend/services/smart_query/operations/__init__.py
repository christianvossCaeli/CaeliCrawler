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

# Import operations to trigger registration
# Each module uses @register_operation decorator
from . import (
    api_import_ops,  # noqa: F401
    batch_ops,  # noqa: F401
    category_ops,  # noqa: F401
    discovery,  # noqa: F401
    entity_ops,  # noqa: F401
    export_ops,  # noqa: F401
    facet_ops,  # noqa: F401
    pysis_ops,  # noqa: F401
)
from .base import (
    OPERATIONS_REGISTRY,
    OperationResult,
    WriteOperation,
    execute_operation,
    get_operation,
    register_operation,
)

__all__ = [
    "WriteOperation",
    "OperationResult",
    "execute_operation",
    "register_operation",
    "get_operation",
    "OPERATIONS_REGISTRY",
]
