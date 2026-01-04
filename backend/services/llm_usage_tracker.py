"""
Centralized LLM usage tracking service.

Provides:
- Context manager for automatic tracking
- Async batch writing for performance
- Cost calculation based on model pricing (from database or fallback)
- Integration with Prometheus metrics

Usage:
    async with track_llm_usage(
        provider=LLMProvider.AZURE_OPENAI,
        model="gpt-4.1-mini",
        task_type=LLMTaskType.SUMMARIZE,
        document_id=doc.id,
    ) as ctx:
        response = await client.chat.completions.create(...)
        ctx.prompt_tokens = response.usage.prompt_tokens
        ctx.completion_tokens = response.usage.completion_tokens
        ctx.total_tokens = response.usage.total_tokens
"""

import asyncio
import threading
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional

import structlog

from app.models.llm_usage import LLMProvider, LLMTaskType, LLMUsageRecord

logger = structlog.get_logger(__name__)

# ============================================================================
# Pricing Cache - Database-backed with in-memory cache
# ============================================================================

# In-memory cache for model pricing (populated from database)
_pricing_cache: dict[str, dict[str, float]] = {}
_pricing_cache_lock = threading.RLock()
_pricing_cache_timestamp: float = 0.0
_PRICING_CACHE_TTL_SECONDS = 300.0  # 5 minutes


# Model pricing in USD per 1M tokens (as of January 2025)
# Update these values when pricing changes
# Source: https://openai.com/pricing, https://anthropic.com/pricing
MODEL_PRICING: dict[str, dict[str, float]] = {
    # Azure OpenAI / OpenAI Standard
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 1.10, "output": 4.40},
    "o1-pro": {"input": 150.00, "output": 600.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    # Embeddings
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-ada-002": {"input": 0.10, "output": 0.0},
    # Anthropic Claude
    "claude-opus-4-5": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    # Fallback for unknown models
    "default": {"input": 1.00, "output": 3.00},
}


def _load_pricing_from_database() -> dict[str, dict[str, float]]:
    """Load pricing from database synchronously.

    Uses a new database connection since we can't use async in sync context.
    Falls back to empty dict on errors (caller handles fallback to defaults).
    """
    try:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        from app.config import settings
        from app.models.model_pricing import ModelPricing

        # Create sync engine for one-off query
        sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_url, pool_pre_ping=True)

        result: dict[str, dict[str, float]] = {}
        with Session(engine) as session:
            stmt = select(ModelPricing).where(
                ModelPricing.is_active.is_(True),
                ModelPricing.is_deprecated.is_(False),
            )
            for row in session.execute(stmt).scalars():
                # Store both with and without provider prefix for matching
                result[row.model_name.lower()] = {
                    "input": row.input_price_per_1m,
                    "output": row.output_price_per_1m,
                }
                # Also store with display name for matching
                if row.display_name:
                    result[row.display_name.lower()] = {
                        "input": row.input_price_per_1m,
                        "output": row.output_price_per_1m,
                    }

        engine.dispose()
        logger.debug("pricing_cache_loaded_from_db", count=len(result))
        return result

    except Exception as e:
        logger.warning("pricing_cache_load_failed", error=str(e))
        return {}


def _get_cached_pricing() -> dict[str, dict[str, float]]:
    """Get pricing from cache, refreshing if stale."""
    global _pricing_cache, _pricing_cache_timestamp

    current_time = time.time()

    with _pricing_cache_lock:
        # Check if cache is fresh
        if _pricing_cache and (current_time - _pricing_cache_timestamp) < _PRICING_CACHE_TTL_SECONDS:
            return _pricing_cache

        # Try to refresh from database
        db_pricing = _load_pricing_from_database()
        if db_pricing:
            _pricing_cache = db_pricing
            _pricing_cache_timestamp = current_time
            return _pricing_cache

        # If database failed but we have stale cache, use it
        if _pricing_cache:
            logger.debug("pricing_cache_using_stale")
            return _pricing_cache

        # No cache at all, will fall back to hardcoded defaults
        return {}


async def refresh_pricing_cache() -> int:
    """Async function to refresh the pricing cache from database.

    Returns the number of models cached.
    """
    global _pricing_cache, _pricing_cache_timestamp

    try:
        from sqlalchemy import select

        from app.database import async_session_maker
        from app.models.model_pricing import ModelPricing

        result: dict[str, dict[str, float]] = {}
        async with async_session_maker() as session:
            stmt = select(ModelPricing).where(
                ModelPricing.is_active.is_(True),
                ModelPricing.is_deprecated.is_(False),
            )
            async_result = await session.execute(stmt)
            for row in async_result.scalars():
                result[row.model_name.lower()] = {
                    "input": row.input_price_per_1m,
                    "output": row.output_price_per_1m,
                }
                if row.display_name:
                    result[row.display_name.lower()] = {
                        "input": row.input_price_per_1m,
                        "output": row.output_price_per_1m,
                    }

        with _pricing_cache_lock:
            _pricing_cache = result
            _pricing_cache_timestamp = time.time()

        logger.info("pricing_cache_refreshed", count=len(result))
        return len(result)

    except Exception as e:
        logger.error("pricing_cache_refresh_failed", error=str(e))
        return 0


def get_model_pricing(model: str) -> dict[str, float]:
    """Get pricing for a model, with fuzzy matching for deployment names.

    Checks database-backed cache first, falls back to hardcoded defaults.

    Args:
        model: Model name or deployment name

    Returns:
        Dict with 'input' and 'output' pricing per 1M tokens
    """
    if not model:
        return MODEL_PRICING["default"]

    model_lower = model.lower()

    # Try database cache first
    cached = _get_cached_pricing()
    if cached:
        # Exact match in cache
        if model_lower in cached:
            return cached[model_lower]

        # Fuzzy match in cache (for deployment names like "my-gpt-4o-deployment")
        for known_model, pricing in cached.items():
            if known_model in model_lower or model_lower in known_model:
                return pricing

    # Fall back to hardcoded pricing
    # Exact match first
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]

    # Try partial match (for deployment names like "my-gpt-4o-deployment")
    for known_model in MODEL_PRICING:
        if known_model in model_lower or model_lower in known_model:
            return MODEL_PRICING[known_model]

    return MODEL_PRICING["default"]


@dataclass
class LLMUsageContext:
    """Context for a single LLM call."""

    provider: LLMProvider
    model: str
    task_type: LLMTaskType
    task_name: str | None = None
    document_id: uuid.UUID | None = None
    entity_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Filled during execution
    start_time: float = field(default_factory=time.time)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    is_error: bool = False
    error_message: str | None = None


class LLMUsageTracker:
    """
    Singleton service for tracking LLM usage.

    Features:
    - Async batch writing to reduce DB overhead
    - Thread-safe queue for collecting records
    - Automatic cost calculation
    - Integration with Prometheus metrics
    """

    _instance: Optional["LLMUsageTracker"] = None
    _batch_queue: deque[LLMUsageRecord]
    _batch_size: int = 50
    _flush_interval: float = 5.0  # seconds
    _flush_task: asyncio.Task | None = None
    _lock: asyncio.Lock
    _initialized: bool = False

    def __new__(cls) -> "LLMUsageTracker":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            self._batch_queue = deque()
            self._lock = asyncio.Lock()
            self._initialized = True

    @classmethod
    def get_instance(cls) -> "LLMUsageTracker":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None

    def start_background_flush(self) -> None:
        """Start background task for periodic batch flushing."""
        try:
            loop = asyncio.get_running_loop()
            if self._flush_task is None or self._flush_task.done():
                self._flush_task = loop.create_task(self._background_flush_loop())
                logger.debug("llm_usage_tracker_background_flush_started")
        except RuntimeError:
            # No running event loop
            logger.debug("llm_usage_tracker_no_event_loop")

    async def _background_flush_loop(self) -> None:
        """Periodically flush the batch queue."""
        while True:
            try:
                await asyncio.sleep(self._flush_interval)
                await self._flush_batch()
            except asyncio.CancelledError:
                # Final flush on cancellation
                await self._flush_batch()
                break
            except Exception as e:
                logger.error("llm_usage_tracker_flush_error", error=str(e))

    def calculate_cost_cents(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> int:
        """
        Calculate estimated cost in USD cents.

        Args:
            model: Model name/deployment
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens

        Returns:
            Estimated cost in USD cents (rounded up)
        """
        # Get pricing for model with fuzzy matching
        pricing = get_model_pricing(model)

        # Calculate costs per million tokens
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        # Convert to cents and round up
        total_cents = (input_cost + output_cost) * 100
        return int(total_cents + 0.5)

    async def record(self, ctx: LLMUsageContext) -> None:
        """
        Record an LLM usage event.

        Adds to batch queue for efficient batch writes.
        Also updates Prometheus metrics immediately.

        Args:
            ctx: The usage context with all details
        """
        duration_ms = int((time.time() - ctx.start_time) * 1000)
        cost_cents = self.calculate_cost_cents(
            ctx.model,
            ctx.prompt_tokens,
            ctx.completion_tokens,
        )

        record = LLMUsageRecord(
            provider=ctx.provider,
            model=ctx.model,
            task_type=ctx.task_type,
            task_name=ctx.task_name,
            prompt_tokens=ctx.prompt_tokens,
            completion_tokens=ctx.completion_tokens,
            total_tokens=ctx.total_tokens or (ctx.prompt_tokens + ctx.completion_tokens),
            estimated_cost_cents=cost_cents,
            duration_ms=duration_ms,
            request_id=ctx.request_id,
            document_id=ctx.document_id,
            entity_id=ctx.entity_id,
            category_id=ctx.category_id,
            user_id=ctx.user_id,
            extra_metadata=ctx.metadata,
            is_error=ctx.is_error,
            error_message=ctx.error_message[:500] if ctx.error_message else None,
            created_at=datetime.now(UTC),
        )

        # Update Prometheus metrics immediately (if available)
        try:
            from app.monitoring.metrics import ai_tokens_used

            if ctx.prompt_tokens > 0:
                ai_tokens_used.labels(model=ctx.model, token_type="prompt").inc(
                    ctx.prompt_tokens
                )
            if ctx.completion_tokens > 0:
                ai_tokens_used.labels(model=ctx.model, token_type="completion").inc(
                    ctx.completion_tokens
                )
        except ImportError:
            pass  # Metrics not available

        # Log usage
        logger.debug(
            "llm_usage_recorded",
            provider=ctx.provider.value,
            model=ctx.model,
            task_type=ctx.task_type.value,
            task_name=ctx.task_name,
            prompt_tokens=ctx.prompt_tokens,
            completion_tokens=ctx.completion_tokens,
            total_tokens=record.total_tokens,
            cost_cents=cost_cents,
            duration_ms=duration_ms,
            is_error=ctx.is_error,
        )

        # Add to batch queue
        async with self._lock:
            self._batch_queue.append(record)

            # Flush if batch is full
            if len(self._batch_queue) >= self._batch_size:
                await self._flush_batch_internal()

    async def _flush_batch(self) -> None:
        """Write pending records to database (with lock)."""
        async with self._lock:
            await self._flush_batch_internal()

    async def _flush_batch_internal(self) -> None:
        """Write pending records to database (assumes lock is held)."""
        if not self._batch_queue:
            return

        records = list(self._batch_queue)
        self._batch_queue.clear()

        try:
            from app.database import get_session_context

            async with get_session_context() as session:
                session.add_all(records)
                await session.commit()

            logger.debug("llm_usage_batch_flushed", count=len(records))
        except Exception as e:
            logger.error("llm_usage_flush_failed", error=str(e), count=len(records))
            # Re-queue records on failure (prepend to maintain order)
            for record in reversed(records):
                self._batch_queue.appendleft(record)

    async def force_flush(self) -> None:
        """Force immediate flush of all pending records."""
        await self._flush_batch()

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self._batch_queue)


# Global tracker instance
_tracker: LLMUsageTracker | None = None


def get_tracker() -> LLMUsageTracker:
    """Get the global tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = LLMUsageTracker.get_instance()
    return _tracker


@asynccontextmanager
async def track_llm_usage(
    provider: LLMProvider,
    model: str,
    task_type: LLMTaskType,
    task_name: str | None = None,
    document_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
):
    """
    Context manager for tracking LLM usage.

    Usage:
        async with track_llm_usage(
            provider=LLMProvider.AZURE_OPENAI,
            model="gpt-4.1-mini",
            task_type=LLMTaskType.SUMMARIZE,
        ) as ctx:
            response = await client.chat.completions.create(...)
            ctx.prompt_tokens = response.usage.prompt_tokens
            ctx.completion_tokens = response.usage.completion_tokens
            ctx.total_tokens = response.usage.total_tokens

    Args:
        provider: LLM provider (AZURE_OPENAI, ANTHROPIC)
        model: Model name/deployment
        task_type: Type of task being performed
        task_name: Optional human-readable task name
        document_id: Optional related document ID
        entity_id: Optional related entity ID
        category_id: Optional related category ID
        user_id: Optional user ID who triggered the call
        metadata: Optional additional metadata

    Yields:
        LLMUsageContext that should be populated with token counts
    """
    ctx = LLMUsageContext(
        provider=provider,
        model=model,
        task_type=task_type,
        task_name=task_name,
        document_id=document_id,
        entity_id=entity_id,
        category_id=category_id,
        user_id=user_id,
        metadata=metadata or {},
    )

    try:
        yield ctx
    except Exception as e:
        ctx.is_error = True
        ctx.error_message = str(e)
        raise
    finally:
        tracker = get_tracker()
        try:
            await tracker.record(ctx)
        except Exception as e:
            # Don't let tracking errors break the main flow
            logger.error("llm_usage_tracking_failed", error=str(e))


async def record_llm_usage(
    provider: LLMProvider,
    model: str,
    task_type: LLMTaskType,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int | None = None,
    task_name: str | None = None,
    document_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    duration_ms: int | None = None,
    is_error: bool = False,
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Record LLM usage directly without context manager.

    Useful for cases where the context manager pattern doesn't fit,
    such as streaming responses or manual tracking.

    Args:
        provider: LLM provider
        model: Model name
        task_type: Type of task
        prompt_tokens: Input tokens
        completion_tokens: Output tokens
        total_tokens: Total tokens (computed if not provided)
        task_name: Optional task name
        document_id: Optional document ID
        entity_id: Optional entity ID
        category_id: Optional category ID
        user_id: Optional user ID
        duration_ms: Optional duration in milliseconds
        is_error: Whether the request failed
        error_message: Optional error message
        metadata: Optional additional metadata
    """
    ctx = LLMUsageContext(
        provider=provider,
        model=model,
        task_type=task_type,
        task_name=task_name,
        document_id=document_id,
        entity_id=entity_id,
        category_id=category_id,
        user_id=user_id,
        metadata=metadata or {},
    )

    # Set token counts
    ctx.prompt_tokens = prompt_tokens
    ctx.completion_tokens = completion_tokens
    ctx.total_tokens = total_tokens or (prompt_tokens + completion_tokens)

    # Set error info
    ctx.is_error = is_error
    ctx.error_message = error_message

    # Override start time if duration is provided
    if duration_ms is not None:
        ctx.start_time = time.time() - (duration_ms / 1000)

    tracker = get_tracker()
    try:
        await tracker.record(ctx)
    except Exception as e:
        logger.error("llm_usage_direct_recording_failed", error=str(e))


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for a text string.

    Uses a rough approximation of ~4 characters per token for English text.
    For more accurate counting, use tiktoken library.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    # Rough estimate: ~4 chars per token for English
    # This is a simple heuristic; for accurate counts, use tiktoken
    return len(text) // 4 + 1
