"""
Write Operations Framework.

This module provides a command pattern implementation for Smart Query write operations.
It allows for modular, testable, and maintainable operation handlers.

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

Migration Status:
    - discover_sources: MIGRATED (discovery.py)
    - create_entity: legacy (write_executor.py)
    - create_facet: legacy (write_executor.py)
    - create_relation: legacy (write_executor.py)
    - create_entity_type: legacy (write_executor.py)
    - create_category_setup: legacy (write_executor.py)
    - ... (19 more operations in write_executor.py)
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
# Add new operation imports here as they are migrated
from . import discovery  # noqa: F401 - imported for registration side-effect

__all__ = [
    "WriteOperation",
    "OperationResult",
    "execute_operation",
    "register_operation",
    "get_operation",
    "OPERATIONS_REGISTRY",
]
