"""
Base classes for Smart Query write operations.

This module implements the Command Pattern for handling write operations,
making them modular, testable, and maintainable.

Architecture:
    - WriteOperation: Abstract base class for all operations
    - OperationResult: Standardized result container
    - OPERATIONS_REGISTRY: Central registry for operation handlers
    - execute_operation: Main entry point for executing operations
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


@dataclass
class OperationResult:
    """Standardized result container for write operations."""

    success: bool = False
    message: str = ""
    operation: str = ""
    created_items: list[dict[str, Any]] = field(default_factory=list)
    data: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "success": self.success,
            "message": self.message,
            "operation": self.operation,
            "created_items": self.created_items,
        }
        if self.data:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        return result


class WriteOperation(ABC):
    """
    Abstract base class for write operations.

    Subclasses must implement the execute method to perform
    the actual operation logic.

    Example:
        @register_operation("create_entity")
        class CreateEntityOperation(WriteOperation):
            async def execute(
                self,
                session: AsyncSession,
                command: Dict[str, Any],
                user_id: Optional[UUID] = None,
            ) -> OperationResult:
                entity_type = command.get("entity_type", "territorial_entity")
                entity_data = command.get("entity_data", {})
                # ... implementation ...
                return OperationResult(
                    success=True,
                    message="Entity created",
                    operation="create_entity",
                    created_items=[{"type": "entity", "id": str(entity.id)}]
                )
    """

    # Operation name (set by @register_operation decorator)
    operation_name: str = ""

    @abstractmethod
    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        """
        Execute the write operation.

        Args:
            session: Database session
            command: Command data containing operation parameters
            user_id: Optional user ID for ownership tracking

        Returns:
            OperationResult with success status and created items
        """
        pass

    def validate(self, command: dict[str, Any]) -> str | None:
        """
        Validate command data before execution.

        Override in subclasses to add operation-specific validation.

        Args:
            command: Command data to validate

        Returns:
            Error message if validation fails, None if valid
        """
        return None


# Global registry of operation handlers
OPERATIONS_REGISTRY: dict[str, type[WriteOperation]] = {}


def register_operation(name: str) -> Callable[[type[WriteOperation]], type[WriteOperation]]:
    """
    Decorator to register an operation handler.

    Usage:
        @register_operation("create_entity")
        class CreateEntityOperation(WriteOperation):
            ...

    Args:
        name: Operation name (e.g., "create_entity", "update_facet")

    Returns:
        Decorator function
    """
    def decorator(cls: type[WriteOperation]) -> type[WriteOperation]:
        cls.operation_name = name
        OPERATIONS_REGISTRY[name] = cls
        logger.debug("Registered write operation", operation=name, handler=cls.__name__)
        return cls
    return decorator


def get_operation(name: str) -> type[WriteOperation] | None:
    """
    Get an operation handler by name.

    Args:
        name: Operation name

    Returns:
        Operation class or None if not found
    """
    return OPERATIONS_REGISTRY.get(name)


async def execute_operation(
    session: AsyncSession,
    command: dict[str, Any],
    user_id: UUID | None = None,
) -> OperationResult:
    """
    Execute a write operation using the registered handler.

    This function only handles operations that have registered handlers.
    For unregistered operations, the caller (write_executor) handles them directly.

    Args:
        session: Database session
        command: Command data with "operation" key
        user_id: Optional user ID for ownership

    Returns:
        OperationResult with success status
    """
    operation_name = command.get("operation", "none")

    if operation_name == "none":
        return OperationResult(
            success=False,
            message="Keine Schreib-Operation erkannt",
            operation="none",
        )

    # Check if operation has a registered handler
    operation_class = OPERATIONS_REGISTRY.get(operation_name)

    if not operation_class:
        return OperationResult(
            success=False,
            message=f"Keine registrierte Operation: {operation_name}",
            operation=operation_name,
        )

    # Use command pattern handler
    handler = operation_class()

    # Validate command
    validation_error = handler.validate(command)
    if validation_error:
        return OperationResult(
            success=False,
            message=validation_error,
            operation=operation_name,
        )

    try:
        result = await handler.execute(session, command, user_id)
        result.operation = operation_name
        return result
    except Exception as e:
        logger.error(
            "Write operation failed",
            operation=operation_name,
            error=str(e),
            exc_info=True,
        )
        return OperationResult(
            success=False,
            message=f"Operation fehlgeschlagen: {str(e)}",
            operation=operation_name,
            error=str(e),
        )
