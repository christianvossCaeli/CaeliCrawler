"""
Circuit Breaker Pattern Implementation.

Prevents cascading failures by temporarily blocking requests to failing services.

States:
- CLOSED: Normal operation, requests flow through
- OPEN: Service is failing, requests are blocked
- HALF_OPEN: Testing if service has recovered

Usage:
    @circuit_breaker(name="openai", failure_threshold=5, recovery_timeout=60)
    async def call_openai_api(...):
        ...

Or manually:
    breaker = CircuitBreaker("external_api")

    async with breaker:
        response = await external_api.call()
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Optional, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Raised when circuit is open and request is blocked."""

    def __init__(self, name: str, state: CircuitState, retry_after: float):
        self.name = name
        self.state = state
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker '{name}' is {state.value}. Retry after {retry_after:.1f}s")


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""

    # Thresholds
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes in half-open to close

    # Timeouts
    recovery_timeout: float = 60.0  # Seconds before trying half-open
    call_timeout: float = 30.0  # Timeout for individual calls

    # Exceptions to count as failures
    exception_types: tuple = (Exception,)

    # Exceptions to NOT count as failures (e.g., validation errors)
    exclude_exceptions: tuple = ()


@dataclass
class CircuitBreakerState:
    """State tracking for a circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0
    last_state_change: float = field(default_factory=time.time)
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting external service calls.

    Example:
        breaker = CircuitBreaker("openai", failure_threshold=3)

        try:
            async with breaker:
                result = await openai_client.complete(...)
        except CircuitBreakerError as e:
            # Circuit is open, use fallback
            result = await use_fallback()
    """

    # Global registry of circuit breakers
    _registry: dict[str, "CircuitBreaker"] = {}

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
        **config_kwargs: Any,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Unique name for this breaker
            config: Optional configuration object
            **config_kwargs: Override config values
        """
        self.name = name
        self.config = config or CircuitBreakerConfig(**config_kwargs)
        self._state = CircuitBreakerState()
        self._lock = asyncio.Lock()

        # Register globally
        CircuitBreaker._registry[name] = self

        logger.info(
            "Circuit breaker initialized",
            name=name,
            failure_threshold=self.config.failure_threshold,
            recovery_timeout=self.config.recovery_timeout,
        )

    @classmethod
    def get(cls, name: str) -> Optional["CircuitBreaker"]:
        """Get a circuit breaker by name."""
        return cls._registry.get(name)

    @classmethod
    def get_all_stats(cls) -> dict[str, dict[str, Any]]:
        """Get stats for all circuit breakers."""
        return {name: breaker.stats for name, breaker in cls._registry.items()}

    @property
    def state(self) -> CircuitState:
        """Current state of the circuit breaker."""
        return self._state.state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self._state.state == CircuitState.OPEN

    @property
    def stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._state.state.value,
            "failure_count": self._state.failure_count,
            "success_count": self._state.success_count,
            "total_calls": self._state.total_calls,
            "total_failures": self._state.total_failures,
            "total_successes": self._state.total_successes,
            "failure_threshold": self.config.failure_threshold,
            "recovery_timeout": self.config.recovery_timeout,
            "time_since_last_failure": (
                time.time() - self._state.last_failure_time if self._state.last_failure_time > 0 else None
            ),
        }

    async def __aenter__(self) -> "CircuitBreaker":
        """Context manager entry - checks if request is allowed."""
        await self._before_call()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        """Context manager exit - records success or failure."""
        if exc_val is None:
            await self._on_success()
        elif self._should_count_as_failure(exc_val):
            await self._on_failure(exc_val)
        # Don't suppress exceptions
        return False

    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of the function

        Raises:
            CircuitBreakerError: If circuit is open
        """
        async with self:
            if asyncio.iscoroutinefunction(func):
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.call_timeout,
                )
            else:
                return func(*args, **kwargs)

    async def _before_call(self) -> None:
        """Check state and allow/block the call."""
        async with self._lock:
            self._state.total_calls += 1

            if self._state.state == CircuitState.CLOSED:
                return  # Allow

            if self._state.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                time_since_open = time.time() - self._state.last_state_change

                if time_since_open >= self.config.recovery_timeout:
                    # Transition to half-open
                    self._transition_to(CircuitState.HALF_OPEN)
                    return  # Allow (test request)
                else:
                    # Still open, block
                    retry_after = self.config.recovery_timeout - time_since_open
                    raise CircuitBreakerError(self.name, self._state.state, retry_after)

            # Half-open: allow request through (test)
            return

    async def _on_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self._state.total_successes += 1

            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1

                if self._state.success_count >= self.config.success_threshold:
                    # Recovered! Close the circuit
                    self._transition_to(CircuitState.CLOSED)

            elif self._state.state == CircuitState.CLOSED:
                # Reset failure count on success
                self._state.failure_count = 0

    async def _on_failure(self, exc: BaseException) -> None:
        """Record a failed call."""
        async with self._lock:
            self._state.total_failures += 1
            self._state.failure_count += 1
            self._state.last_failure_time = time.time()

            logger.warning(
                "Circuit breaker recorded failure",
                name=self.name,
                failure_count=self._state.failure_count,
                error=str(exc),
            )

            if self._state.state == CircuitState.HALF_OPEN:
                # Failed during recovery test, reopen
                self._transition_to(CircuitState.OPEN)

            elif self._state.state == CircuitState.CLOSED:  # noqa: SIM102
                if self._state.failure_count >= self.config.failure_threshold:
                    # Too many failures, open the circuit
                    self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state.state
        self._state.state = new_state
        self._state.last_state_change = time.time()

        # Reset counters for the new state
        if new_state == CircuitState.CLOSED:
            self._state.failure_count = 0
            self._state.success_count = 0
        elif new_state == CircuitState.HALF_OPEN or new_state == CircuitState.OPEN:
            self._state.success_count = 0

        logger.info(
            "Circuit breaker state change",
            name=self.name,
            old_state=old_state.value,
            new_state=new_state.value,
        )

    def _should_count_as_failure(self, exc: BaseException) -> bool:
        """Check if an exception should count as a failure."""
        # Check exclusions first
        if isinstance(exc, self.config.exclude_exceptions):
            return False
        # Check inclusions
        return isinstance(exc, self.config.exception_types)

    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        self._state = CircuitBreakerState()
        logger.info("Circuit breaker reset", name=self.name)


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    call_timeout: float = 30.0,
    exception_types: tuple = (Exception,),
    exclude_exceptions: tuple = (),
) -> Callable:
    """
    Decorator to wrap a function with circuit breaker protection.

    Args:
        name: Unique name for this circuit breaker
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds before attempting recovery
        call_timeout: Timeout for individual calls
        exception_types: Exceptions to count as failures
        exclude_exceptions: Exceptions to NOT count as failures

    Example:
        @circuit_breaker("openai", failure_threshold=3, recovery_timeout=30)
        async def call_openai(prompt: str) -> str:
            return await openai_client.complete(prompt)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Create or get the circuit breaker
        breaker = CircuitBreaker.get(name)
        if breaker is None:
            breaker = CircuitBreaker(
                name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                call_timeout=call_timeout,
                exception_types=exception_types,
                exclude_exceptions=exclude_exceptions,
            )

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await breaker.call(func, *args, **kwargs)

        # Attach breaker reference for inspection
        wrapper.circuit_breaker = breaker  # type: ignore

        return wrapper

    return decorator


# =============================================================================
# Pre-configured Circuit Breakers for External Services
# =============================================================================

# OpenAI/LLM API circuit breaker
llm_circuit_breaker = CircuitBreaker(
    "llm",
    failure_threshold=3,
    recovery_timeout=60.0,
    call_timeout=120.0,  # LLM calls can be slow
)

# External web API circuit breaker (e.g., OParl)
external_api_circuit_breaker = CircuitBreaker(
    "external_api",
    failure_threshold=5,
    recovery_timeout=30.0,
    call_timeout=30.0,
)

# SharePoint API circuit breaker
sharepoint_circuit_breaker = CircuitBreaker(
    "sharepoint",
    failure_threshold=3,
    recovery_timeout=120.0,  # SharePoint might need longer to recover
    call_timeout=60.0,
)
