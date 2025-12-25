"""Async runner utility for Celery tasks.

This module provides a consistent way to run async code in Celery tasks,
avoiding event loop conflicts.

The run_async function creates a fresh event loop for each task execution,
ensuring proper cleanup and preventing "Event loop is closed" or
"Task got Future attached to a different loop" errors.

IMPORTANT: We do NOT use nest_asyncio because it causes connection pool
issues with asyncpg. Instead, each task gets its own event loop.
"""

import asyncio
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run async coroutine in Celery task safely.

    Creates a new event loop for each task execution to avoid conflicts
    with existing loops. This is the recommended pattern for running
    async code in synchronous Celery tasks.

    This function also resets the database engine before each execution
    to ensure connections are fresh and not bound to a stale event loop.

    Args:
        coro: The coroutine to execute

    Returns:
        The result of the coroutine

    Example:
        @celery_app.task
        def my_task():
            async def _work():
                async with get_celery_session_context() as session:
                    # Do async work
                    pass

            return run_async(_work())
    """
    # Reset the database engine to ensure we get fresh connections
    # bound to the new event loop we're about to create
    from app.database import reset_celery_engine
    reset_celery_engine()

    # Create a fresh event loop for this execution
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        # Ensure the loop is properly closed, running any pending cleanup
        try:
            # Cancel all pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()

            # Run the loop briefly to let cancellations propagate
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

            # Shutdown async generators
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        finally:
            loop.close()

        # Clean up the database engine after task completion
        reset_celery_engine()
