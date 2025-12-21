"""Command registry for Smart Query operations."""

from typing import Any, Callable, Dict, Optional, Type
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseCommand, CommandResult

logger = structlog.get_logger()


class CommandRegistry:
    """
    Registry for Smart Query write commands.

    Provides a centralized way to register and execute commands,
    supporting gradual migration from the monolithic executor.

    Usage:
        registry = CommandRegistry()

        @registry.register("create_entity")
        class CreateEntityCommand(BaseCommand):
            ...

        # Or register manually:
        registry.register_command("create_entity", CreateEntityCommand)

        # Execute:
        result = await registry.execute("create_entity", session, data, user_id)
    """

    def __init__(self):
        self._commands: Dict[str, Type[BaseCommand]] = {}

    def register(self, operation_name: str) -> Callable:
        """
        Decorator to register a command class.

        Usage:
            @registry.register("create_entity")
            class CreateEntityCommand(BaseCommand):
                ...
        """
        def decorator(cls: Type[BaseCommand]) -> Type[BaseCommand]:
            cls.operation_name = operation_name
            self._commands[operation_name] = cls
            logger.debug("Registered command", operation=operation_name, cls=cls.__name__)
            return cls
        return decorator

    def register_command(self, operation_name: str, command_class: Type[BaseCommand]) -> None:
        """
        Manually register a command class.

        Args:
            operation_name: The operation identifier
            command_class: The command class to register
        """
        command_class.operation_name = operation_name
        self._commands[operation_name] = command_class

    def has_command(self, operation_name: str) -> bool:
        """Check if a command is registered for the given operation."""
        return operation_name in self._commands

    def get_command_class(self, operation_name: str) -> Optional[Type[BaseCommand]]:
        """Get the command class for an operation."""
        return self._commands.get(operation_name)

    async def execute(
        self,
        operation_name: str,
        session: AsyncSession,
        data: Dict[str, Any],
        current_user_id: Optional[UUID] = None,
    ) -> CommandResult:
        """
        Execute a registered command.

        Args:
            operation_name: The operation to execute
            session: Database session
            data: Command input data
            current_user_id: Optional user ID

        Returns:
            CommandResult with operation outcome
        """
        command_class = self._commands.get(operation_name)

        if not command_class:
            return CommandResult.failure(
                message=f"Unbekannte Operation: {operation_name}",
                operation=operation_name,
            )

        # Instantiate and run the command
        command = command_class(
            session=session,
            data=data,
            current_user_id=current_user_id,
        )

        return await command.run()

    @property
    def registered_operations(self) -> list:
        """Get list of registered operation names."""
        return list(self._commands.keys())


# Global registry instance
default_registry = CommandRegistry()
