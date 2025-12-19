"""Database configuration and session management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

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
# - pool_size=20: Base number of connections (increased from 10)
# - max_overflow=30: Additional connections under load
# - pool_recycle=1800: Recycle connections after 30 min to prevent stale connections
# - pool_pre_ping=True: Verify connection health before use
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
    pool_recycle=1800,
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
    """Dependency for getting async database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for getting async database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
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
        # - pool_size=10: Per-worker pool (multiple workers share total load)
        # - max_overflow=5: Limited overflow to prevent connection exhaustion
        # - pool_recycle=1800: Same as main app
        _celery_engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=5,
            pool_recycle=1800,
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
    """
    factory = get_celery_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
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
        except Exception:
            pass
    _celery_engine = None
    _celery_session_factory = None
