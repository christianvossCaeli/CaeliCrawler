"""
Retry utility with exponential backoff.

Provides a decorator and context manager for retrying operations
that may fail due to transient errors (network issues, rate limits, etc.)
"""

import asyncio
import functools
import random
from collections.abc import Callable
from typing import (
    Any,
    TypeVar,
)

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class RetryError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, message: str, last_exception: Exception | None = None):
        super().__init__(message)
        self.last_exception = last_exception


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        jitter_factor: float = 0.1,
        retryable_exceptions: tuple[type[Exception], ...] | None = None,
        non_retryable_exceptions: tuple[type[Exception], ...] | None = None,
        on_retry: Callable[[Exception, int], None] | None = None,
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of attempts (including first try)
            base_delay: Base delay in seconds between retries
            max_delay: Maximum delay in seconds (caps exponential growth)
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
            jitter_factor: Factor for jitter (0.1 = +/- 10%)
            retryable_exceptions: Exceptions that should trigger retry
            non_retryable_exceptions: Exceptions that should NOT retry
            on_retry: Callback called on each retry (exc, attempt_number)
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        self.retryable_exceptions = retryable_exceptions or (Exception,)
        self.non_retryable_exceptions = non_retryable_exceptions or ()
        self.on_retry = on_retry

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.

        Uses exponential backoff: delay = base_delay * (exponential_base ^ attempt)
        With optional jitter to prevent thundering herd.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add +/- jitter_factor random variation
            jitter_range = delay * self.jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)  # noqa: S311

        return max(0, delay)

    def should_retry(self, exception: Exception) -> bool:
        """
        Determine if an exception should trigger a retry.

        Args:
            exception: The exception that was raised

        Returns:
            True if should retry, False otherwise
        """
        # Never retry if it's a non-retryable exception
        if isinstance(exception, self.non_retryable_exceptions):
            return False

        # Retry if it's a retryable exception
        return isinstance(exception, self.retryable_exceptions)


# Default configurations for common scenarios

NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
        OSError,
    ),
)

API_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
    ),
    non_retryable_exceptions=(
        ValueError,
        KeyError,
        TypeError,
    ),
)

LLM_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=5.0,
    max_delay=120.0,
    exponential_base=2.0,
    jitter=True,
)


async def retry_async[T](
    func: Callable[..., T],
    *args: Any,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> T:
    """
    Execute an async function with retry logic.

    Args:
        func: Async function to execute
        *args: Positional arguments to pass to func
        config: Retry configuration (defaults to NETWORK_RETRY_CONFIG)
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result of the function

    Raises:
        RetryError: If all attempts fail
    """
    config = config or NETWORK_RETRY_CONFIG
    last_exception: Exception | None = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            # Check if we should retry
            if not config.should_retry(e):
                logger.warning(
                    "Non-retryable exception",
                    func=func.__name__,
                    error=str(e),
                    exception_type=type(e).__name__,
                )
                raise

            # Check if we have attempts left
            if attempt >= config.max_attempts - 1:
                logger.error(
                    "All retry attempts exhausted",
                    func=func.__name__,
                    attempts=config.max_attempts,
                    last_error=str(e),
                )
                raise RetryError(
                    f"Failed after {config.max_attempts} attempts: {str(e)}",
                    last_exception=e,
                ) from None

            # Calculate delay and wait
            delay = config.calculate_delay(attempt)
            logger.warning(
                "Retrying after error",
                func=func.__name__,
                attempt=attempt + 1,
                max_attempts=config.max_attempts,
                delay=delay,
                error=str(e),
            )

            # Call retry callback if provided
            if config.on_retry:
                config.on_retry(e, attempt + 1)

            await asyncio.sleep(delay)

    # Should never reach here, but just in case
    raise RetryError(
        f"Unexpected retry loop exit after {config.max_attempts} attempts",
        last_exception=last_exception,
    )


def with_retry(
    config: RetryConfig | None = None,
    max_attempts: int | None = None,
    base_delay: float | None = None,
):
    """
    Decorator to add retry logic to an async function.

    Can be used with default config or custom config.

    Usage:
        @with_retry()
        async def fetch_data():
            ...

        @with_retry(max_attempts=5, base_delay=2.0)
        async def fetch_with_custom_retry():
            ...

        @with_retry(config=LLM_RETRY_CONFIG)
        async def call_llm():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Build config from parameters or use provided config
            retry_config = config
            if retry_config is None:
                retry_config = RetryConfig(
                    max_attempts=max_attempts or 3,
                    base_delay=base_delay or 1.0,
                )

            return await retry_async(func, *args, config=retry_config, **kwargs)

        return wrapper
    return decorator


class RetryContext:
    """
    Context manager for retry logic.

    Usage:
        async with RetryContext(max_attempts=3) as retry:
            while retry.should_continue():
                try:
                    result = await risky_operation()
                    break
                except Exception as e:
                    await retry.handle_error(e)
    """

    def __init__(self, config: RetryConfig | None = None, **kwargs):
        """
        Initialize retry context.

        Args:
            config: Retry configuration, or pass individual params as kwargs
            **kwargs: Individual config parameters (max_attempts, base_delay, etc.)
        """
        if config:
            self.config = config
        else:
            self.config = RetryConfig(**kwargs) if kwargs else NETWORK_RETRY_CONFIG

        self._attempt = 0
        self._exhausted = False

    async def __aenter__(self) -> "RetryContext":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def should_continue(self) -> bool:
        """Check if we should continue trying."""
        return not self._exhausted and self._attempt < self.config.max_attempts

    async def handle_error(self, exception: Exception) -> None:
        """
        Handle an error, wait if appropriate, or raise if exhausted.

        Args:
            exception: The exception that occurred

        Raises:
            RetryError: If all attempts are exhausted
            The original exception: If it's non-retryable
        """
        if not self.config.should_retry(exception):
            raise exception

        self._attempt += 1

        if self._attempt >= self.config.max_attempts:
            self._exhausted = True
            raise RetryError(
                f"Failed after {self.config.max_attempts} attempts",
                last_exception=exception,
            )

        delay = self.config.calculate_delay(self._attempt - 1)
        logger.warning(
            "Retry context handling error",
            attempt=self._attempt,
            max_attempts=self.config.max_attempts,
            delay=delay,
            error=str(exception),
        )

        if self.config.on_retry:
            self.config.on_retry(exception, self._attempt)

        await asyncio.sleep(delay)

    @property
    def current_attempt(self) -> int:
        """Get the current attempt number (1-indexed)."""
        return self._attempt + 1
