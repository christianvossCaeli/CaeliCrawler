"""
OpenTelemetry configuration for distributed tracing.

Provides automatic instrumentation for:
- FastAPI HTTP requests
- SQLAlchemy database queries
- Redis operations

Traces can be exported to Jaeger, Zipkin, or any OTLP-compatible backend.

Configuration:
    Set OTEL_EXPORTER_OTLP_ENDPOINT in environment for trace export.
    If not set, tracing is disabled (no-op).

Usage:
    from app.core.telemetry import setup_telemetry

    # In app startup
    setup_telemetry(app, settings)
"""

import structlog
from fastapi import FastAPI

from app.config import Settings

logger = structlog.get_logger(__name__)


def setup_telemetry(app: FastAPI, settings: Settings) -> bool:
    """
    Configure OpenTelemetry tracing for the application.

    Only enables tracing if OTEL_EXPORTER_OTLP_ENDPOINT is configured.
    This allows development environments to run without a trace collector.

    Args:
        app: FastAPI application instance
        settings: Application settings

    Returns:
        True if telemetry was enabled, False otherwise
    """
    # Check if OTLP endpoint is configured
    import os

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    if not otlp_endpoint:
        logger.info("OpenTelemetry disabled (OTEL_EXPORTER_OTLP_ENDPOINT not set)")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Create resource with service information
        resource = Resource.create(
            {
                "service.name": settings.app_name,
                "service.version": "1.0.0",
                "deployment.environment": settings.app_env,
            }
        )

        # Setup tracer provider
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="health,metrics,docs,openapi.json",
        )

        # Instrument SQLAlchemy (captures DB queries)
        SQLAlchemyInstrumentor().instrument()

        # Instrument Redis
        RedisInstrumentor().instrument()

        logger.info(
            "OpenTelemetry enabled",
            endpoint=otlp_endpoint,
            service_name=settings.app_name,
        )
        return True

    except ImportError as e:
        logger.warning(
            "OpenTelemetry packages not installed",
            error=str(e),
        )
        return False
    except Exception as e:
        logger.error(
            "OpenTelemetry setup failed",
            error=str(e),
            exc_info=True,
        )
        return False


def shutdown_telemetry() -> None:
    """
    Shutdown OpenTelemetry and flush pending traces.

    Call this during application shutdown to ensure all traces are exported.
    """
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        if hasattr(provider, "shutdown"):
            provider.shutdown()
            logger.info("OpenTelemetry shutdown complete")
    except Exception as e:
        logger.warning("OpenTelemetry shutdown error", error=str(e))
