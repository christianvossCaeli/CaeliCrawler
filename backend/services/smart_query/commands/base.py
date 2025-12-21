"""Base Command class and result types for Smart Query write operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


@dataclass
class CommandResult:
    """Result of a command execution."""

    success: bool
    message: str
    operation: str = ""
    created_items: List[Dict[str, Any]] = field(default_factory=list)
    updated_items: List[Dict[str, Any]] = field(default_factory=list)
    deleted_items: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API response."""
        result = {
            "success": self.success,
            "message": self.message,
            "operation": self.operation,
            "created_items": self.created_items,
        }

        if self.updated_items:
            result["updated_items"] = self.updated_items
        if self.deleted_items:
            result["deleted_items"] = self.deleted_items
        if self.warnings:
            result["warnings"] = self.warnings

        # Merge extra fields
        result.update(self.extra)

        return result

    @classmethod
    def failure(cls, message: str, operation: str = "") -> "CommandResult":
        """Create a failure result."""
        return cls(success=False, message=message, operation=operation)

    @classmethod
    def success_result(
        cls,
        message: str,
        operation: str = "",
        created_items: Optional[List[Dict]] = None,
        **extra
    ) -> "CommandResult":
        """Create a success result."""
        return cls(
            success=True,
            message=message,
            operation=operation,
            created_items=created_items or [],
            extra=extra,
        )


class BaseCommand(ABC):
    """
    Base class for all Smart Query write commands.

    Commands encapsulate a single write operation with:
    - Input validation
    - Business logic execution
    - Result handling

    Subclasses must implement:
    - validate(): Check if input data is valid
    - execute(): Perform the actual operation
    """

    # Operation name for logging and result tracking
    operation_name: str = "unknown"

    def __init__(
        self,
        session: AsyncSession,
        data: Dict[str, Any],
        current_user_id: Optional[UUID] = None,
    ):
        """
        Initialize the command.

        Args:
            session: Database session for the operation
            data: Input data for the command
            current_user_id: Optional ID of the current user
        """
        self.session = session
        self.data = data
        self.current_user_id = current_user_id

    @abstractmethod
    async def validate(self) -> Optional[str]:
        """
        Validate the input data.

        Returns:
            None if validation passes, error message string if it fails
        """
        pass

    @abstractmethod
    async def execute(self) -> CommandResult:
        """
        Execute the command.

        This method should:
        1. Perform the database operations
        2. NOT commit the transaction (caller handles this)
        3. Return a CommandResult with success/failure info

        Returns:
            CommandResult with operation outcome
        """
        pass

    async def run(self) -> CommandResult:
        """
        Run the command with validation.

        This is the main entry point for command execution.
        It handles validation, execution, and error logging.

        Returns:
            CommandResult with operation outcome
        """
        # Validate input
        validation_error = await self.validate()
        if validation_error:
            return CommandResult.failure(
                message=validation_error,
                operation=self.operation_name,
            )

        # Execute the command
        try:
            result = await self.execute()
            result.operation = self.operation_name

            if result.success:
                logger.info(
                    "Command executed successfully",
                    operation=self.operation_name,
                    user_id=str(self.current_user_id) if self.current_user_id else None,
                    created_count=len(result.created_items),
                )
            else:
                logger.warning(
                    "Command failed",
                    operation=self.operation_name,
                    message=result.message,
                )

            return result

        except Exception as e:
            logger.error(
                "Command execution error",
                operation=self.operation_name,
                error=str(e),
                exc_info=True,
            )
            return CommandResult.failure(
                message=f"Fehler: {str(e)}",
                operation=self.operation_name,
            )
