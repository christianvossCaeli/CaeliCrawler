"""Database configuration and session management.

This module provides:
- Async SQLAlchemy engine and session factory for the FastAPI backend
- Separate engine and session factory for Celery workers
- Connection pool management with proper timeouts
- Automatic cleanup of idle connections

Connection Pool Strategy:
- Each service (backend, celery workers) has its own connection pool
- Pools are sized conservatively to avoid connection exhaustion
- PostgreSQL-side timeouts ensure orphaned connections are cleaned up
- pool_pre_ping validates connections before use
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

import structlog
from sqlalchemy import MetaData, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = structlog.get_logger(__name__)

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    metadata = metadata


# Async engine for application use
# Performance optimized pool settings:
# - pool_size=5: Conservative base connections per service
# - max_overflow=10: Limited overflow to prevent connection exhaustion
# - pool_recycle=300: Recycle connections every 5 min to prevent stale connections
# - pool_pre_ping=True: Verify connection health before use
# - pool_timeout=30: Fail fast if no connection available
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    pool_timeout=30,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions.

    Note: This dependency does NOT auto-commit. Endpoints that modify data
    must explicitly call session.commit(). This prevents unnecessary commits
    on read-only operations.

    For read operations: No commit needed, we rollback any implicit transaction.
    For write operations: Call session.commit() explicitly after modifications.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            # Always rollback any uncommitted transaction to prevent
            # "idle in transaction" connections. This is a no-op if the
            # endpoint already committed or if no transaction was started.
            with suppress(Exception):
                await session.rollback()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for getting async database sessions.

    Ensures transactions are always properly closed, preventing
    'idle in transaction' connections.
    """
    session = async_session_factory()
    try:
        yield session
        # ALWAYS try to commit
        try:
            await session.commit()
        except Exception:
            with suppress(Exception):
                await session.rollback()
    except Exception:
        with suppress(Exception):
            await session.rollback()
        raise
    finally:
        with suppress(Exception):
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


# ============================================================================
# Celery Worker Database Support
# ============================================================================
# Celery workers need separate engine/session management because they run in
# forked processes with their own event loops.

_celery_engine = None
_celery_session_factory = None


def get_celery_engine():
    """Get or create an engine for Celery workers.

    This creates a separate engine instance for each worker process to avoid
    sharing connections across event loops.
    """
    global _celery_engine
    if _celery_engine is None:
        # Celery workers have their own connection pools
        # - pool_size=3: Minimal per-worker pool
        # - max_overflow=5: Limited overflow to prevent connection exhaustion
        # - pool_recycle=300: Recycle every 5 min
        # - pool_timeout=30: Fail fast
        _celery_engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=3,
            max_overflow=5,
            pool_recycle=300,
            pool_timeout=30,
        )
    return _celery_engine


def get_celery_session_factory():
    """Get or create a session factory for Celery workers."""
    global _celery_session_factory
    if _celery_session_factory is None:
        _celery_session_factory = async_sessionmaker(
            get_celery_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _celery_session_factory


@asynccontextmanager
async def get_celery_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for getting async database sessions in Celery workers.

    This uses a separate engine/session factory that is initialized lazily
    in each worker process, avoiding event loop conflicts.

    Important: This context manager always commits/rollbacks and closes,
    regardless of what SQLAlchemy thinks the transaction state is.
    asyncpg auto-begins transactions, but SQLAlchemy may not track this correctly.
    """
    factory = get_celery_session_factory()
    session = factory()
    try:
        yield session
        # ALWAYS try to commit - asyncpg may have started a transaction
        # that SQLAlchemy doesn't know about
        try:
            await session.commit()
        except Exception:
            # If commit fails, try rollback
            with suppress(Exception):
                await session.rollback()
    except Exception:
        # On exception, always rollback
        with suppress(Exception):
            await session.rollback()
        raise
    finally:
        # ALWAYS close the session
        with suppress(Exception):
            await session.close()


def reset_celery_engine():
    """Reset the Celery engine (call on worker process init if needed)."""
    global _celery_engine, _celery_session_factory
    if _celery_engine is not None:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_celery_engine.dispose())
            else:
                loop.run_until_complete(_celery_engine.dispose())
        except Exception:  # noqa: S110
            pass
    _celery_engine = None
    _celery_session_factory = None


async def dispose_celery_engine_async():
    """Async disposal of Celery engine - call during worker shutdown."""
    global _celery_engine, _celery_session_factory
    if _celery_engine is not None:
        try:
            await _celery_engine.dispose()
            logger.info("celery_engine_disposed")
        except Exception as e:
            logger.warning("celery_engine_dispose_error", error=str(e))
    _celery_engine = None
    _celery_session_factory = None


async def cleanup_idle_connections() -> dict:
    """Terminate idle-in-transaction connections that have been open too long.

    This is a safety net for cases where PostgreSQL's idle_in_transaction_session_timeout
    hasn't kicked in yet, or for manual cleanup.

    Returns:
        dict with count of terminated connections
    """
    # Use celery session context since this is called from Celery workers
    async with get_celery_session_context() as session:
        try:
            # Find and terminate connections that are:
            # - idle in transaction for more than 2 minutes
            # - OR idle (not in transaction) for more than 10 minutes
            result = await session.execute(
                text("""
                    SELECT pg_terminate_backend(pid), pid, state,
                           EXTRACT(EPOCH FROM (clock_timestamp() - state_change))::int as idle_seconds
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                      AND pid != pg_backend_pid()
                      AND (
                          (state = 'idle in transaction' AND state_change < NOW() - INTERVAL '2 minutes')
                          OR (state = 'idle' AND state_change < NOW() - INTERVAL '10 minutes')
                      )
                """)
            )
            terminated = result.fetchall()

            if terminated:
                logger.warning(
                    "terminated_idle_connections",
                    count=len(terminated),
                    connections=[{"pid": row[1], "state": row[2], "idle_seconds": row[3]} for row in terminated]
                )

            return {"terminated": len(terminated)}
        except SQLAlchemyError as e:
            logger.error("cleanup_idle_connections_failed", error=str(e))
            return {"terminated": 0, "error": str(e)}


async def get_connection_stats() -> dict:
    """Get current database connection statistics.

    Returns:
        dict with connection counts by state
    """
    # Use celery session context since this is called from Celery workers
    async with get_celery_session_context() as session:
        try:
            result = await session.execute(
                text("""
                    SELECT state, COUNT(*) as count
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    GROUP BY state
                """)
            )
            stats = {row[0] or 'unknown': row[1] for row in result.fetchall()}

            # Also get total and max connections
            result2 = await session.execute(
                text("""
                    SELECT
                        (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()) as current,
                        (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max
                """)
            )
            row = result2.fetchone()
            stats['total_current'] = row[0]
            stats['max_connections'] = row[1]

            return stats
        except SQLAlchemyError as e:
            logger.error("get_connection_stats_failed", error=str(e))
            return {"error": str(e)}
