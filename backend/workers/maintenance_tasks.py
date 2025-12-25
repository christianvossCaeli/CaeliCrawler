"""Celery tasks for database and system maintenance.

This module provides background tasks for:
- Cleaning up idle database connections
- Monitoring connection pool usage
- Logging connection statistics for alerting
"""

import structlog

from workers.celery_app import celery_app
from workers.async_runner import run_async

logger = structlog.get_logger(__name__)


@celery_app.task(name="workers.maintenance_tasks.cleanup_idle_connections")
def cleanup_idle_connections():
    """Clean up idle database connections.

    This task runs periodically (every 5 minutes) as a safety net to terminate
    connections that have been idle in a transaction for too long.

    PostgreSQL's idle_in_transaction_session_timeout is the primary protection,
    but this task provides an additional layer of defense and logging.
    """
    from app.database import cleanup_idle_connections as do_cleanup

    async def _cleanup():
        result = await do_cleanup()
        if result.get("terminated", 0) > 0:
            logger.warning(
                "idle_connections_cleaned",
                terminated=result["terminated"],
            )
        return result

    return run_async(_cleanup())


@celery_app.task(name="workers.maintenance_tasks.log_connection_stats")
def log_connection_stats():
    """Log current database connection statistics.

    This task runs periodically (every 15 minutes) to provide visibility
    into connection pool usage. The stats can be used for alerting when
    connection usage approaches the limit.
    """
    from app.database import get_connection_stats

    async def _stats():
        stats = await get_connection_stats()

        # Calculate usage percentage
        total = stats.get("total_current", 0)
        max_conn = stats.get("max_connections", 200)
        usage_pct = (total / max_conn * 100) if max_conn > 0 else 0

        # Log at different levels based on usage
        idle_in_transaction = stats.get("idle in transaction", 0)

        if usage_pct > 80 or idle_in_transaction > 10:
            logger.error(
                "connection_stats_critical",
                stats=stats,
                usage_percent=round(usage_pct, 1),
                idle_in_transaction=idle_in_transaction,
            )
        elif usage_pct > 50 or idle_in_transaction > 5:
            logger.warning(
                "connection_stats_elevated",
                stats=stats,
                usage_percent=round(usage_pct, 1),
                idle_in_transaction=idle_in_transaction,
            )
        else:
            logger.info(
                "connection_stats",
                total=total,
                max=max_conn,
                usage_percent=round(usage_pct, 1),
                idle=stats.get("idle", 0),
                active=stats.get("active", 0),
                idle_in_transaction=idle_in_transaction,
            )

        return stats

    return run_async(_stats())


@celery_app.task(name="workers.maintenance_tasks.force_cleanup_connections")
def force_cleanup_connections(max_idle_minutes: int = 2):
    """Force cleanup of idle connections with configurable threshold.

    This can be called manually via Celery to immediately clean up
    connections when issues are detected.

    Args:
        max_idle_minutes: Maximum minutes a connection can be idle before termination
    """
    from app.database import get_celery_session_context
    from sqlalchemy import text

    async def _force_cleanup():
        async with get_celery_session_context() as session:
            result = await session.execute(
                text("""
                    SELECT pg_terminate_backend(pid), pid, state,
                           EXTRACT(EPOCH FROM (clock_timestamp() - state_change))::int as idle_seconds
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                      AND pid != pg_backend_pid()
                      AND state IN ('idle', 'idle in transaction')
                      AND state_change < NOW() - make_interval(mins := :minutes)
                """),
                {"minutes": max_idle_minutes}
            )
            terminated = result.fetchall()

            if terminated:
                logger.warning(
                    "force_cleanup_completed",
                    terminated=len(terminated),
                    max_idle_minutes=max_idle_minutes,
                    connections=[{"pid": row[1], "state": row[2]} for row in terminated]
                )

            return {"terminated": len(terminated)}

    return run_async(_force_cleanup())
