"""CaeliCrawler FastAPI Application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from redis.asyncio import Redis

from app import __version__
from app.config import settings
from app.database import close_db, init_db
from app.api.admin import categories, sources, crawler, pysis, locations, users, versions, audit, notifications, external_apis, api_import, ai_discovery, api_templates, crawl_presets, api_facet_sync, sharepoint
from app.api.v1 import export, entity_types, entities, facets, relations, assistant, pysis_facets, dashboard, ai_tasks, entity_data, attachments, favorites, smart_query_history
from app.api.v1.data_api import router as data_router
from app.api.v1.analysis_api import router as analysis_router
from app.api import auth
from app.core.exceptions import AppException
from app.core.rate_limit import RateLimiter, set_rate_limiter
from app.core.token_blacklist import TokenBlacklist, set_token_blacklist
from app.core.security_headers import SecurityHeadersMiddleware, TrustedHostMiddleware
from app.core.i18n_middleware import I18nMiddleware
from app.i18n import load_translations
from app.monitoring.metrics import get_metrics_router, set_app_info

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Global Redis connection for cleanup
_redis_client: Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler."""
    global _redis_client

    # Startup
    logger.info("Starting CaeliCrawler", version=__version__, env=settings.app_env)

    # Load i18n translations
    load_translations()
    logger.info("Translations loaded")

    # Initialize database (create tables if they don't exist)
    if settings.is_development:
        await init_db()
        logger.info("Database initialized")

    # Initialize Redis for rate limiting and token blacklist
    try:
        _redis_client = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test connection
        await _redis_client.ping()

        # Initialize rate limiter
        rate_limiter = RateLimiter(_redis_client)
        set_rate_limiter(rate_limiter)
        logger.info("Rate limiter initialized")

        # Initialize token blacklist
        token_blacklist = TokenBlacklist(_redis_client)
        set_token_blacklist(token_blacklist)
        logger.info("Token blacklist initialized")

    except Exception as e:
        logger.warning(
            "Redis not available, security features degraded",
            error=str(e),
        )
        _redis_client = None

    yield

    # Shutdown
    logger.info("Shutting down CaeliCrawler")

    # Close Redis connection
    if _redis_client:
        await _redis_client.close()
        logger.info("Redis connection closed")

    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="""
# CaeliCrawler API

Datensammlungsplattform für kommunale Informationen.

## Authentifizierung

Diese API verwendet JWT (JSON Web Tokens) für die Authentifizierung.

1. Login über `/auth/login` mit Email und Passwort
2. Token im Authorization Header senden: `Authorization: Bearer <token>`
3. Logout über `/auth/logout` (invalidiert den Token)

## Rollen

- **ADMIN**: Vollzugriff auf alle Funktionen
- **EDITOR**: Kann Daten bearbeiten und neue erstellen
- **VIEWER**: Nur Lesezugriff

## Sicherheitsfeatures

- **Rate Limiting**: Schutz vor Brute-Force-Angriffen
  - Login: 5 Versuche/Minute, 10 Fehlversuche/15 Min
  - Passwort-Änderung: 3 Versuche/5 Min
  - API allgemein: 100 Anfragen/Minute

- **Token Blacklist**: Logout invalidiert Tokens sofort
- **Passwort-Policy**: Min. 8 Zeichen, Groß-/Kleinbuchstaben, Ziffern
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc. (Production)
- **Audit Logging**: Alle Änderungen werden protokolliert
- **Versionierung**: Diff-basierte Änderungshistorie
        """,
        version=__version__,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Security headers middleware (add first, executes last)
    # Enable HSTS only in production with HTTPS
    enable_hsts = settings.app_env == "production"
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=enable_hsts)

    # Trusted hosts middleware in production
    if settings.app_env == "production":
        allowed_hosts = ["api.caeli-wind.de", "localhost"]
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # i18n middleware - sets locale based on request headers
    app.add_middleware(I18nMiddleware)

    # Exception handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "detail": exc.detail,
                "code": exc.code,
            },
        )

    # Health check
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "version": __version__,
            "environment": settings.app_env,
        }

    # Prometheus metrics endpoint
    app.include_router(get_metrics_router())

    # Set application info for metrics
    set_app_info(version=__version__, environment=settings.app_env)

    # Feature flags endpoint
    @app.get("/api/config/features", tags=["Config"])
    async def get_feature_flags():
        """Get feature flags for the frontend."""
        return {
            "entityLevelFacets": settings.feature_entity_level_facets,
            "pysisFieldTemplates": settings.feature_pysis_field_templates,
            "entityHierarchyEnabled": True,  # Enable entity hierarchy features
        }

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.app_name,
            "version": __version__,
            "docs": "/docs" if settings.debug else None,
        }

    # Include routers
    # Authentication API (public)
    app.include_router(
        auth.router,
        prefix="/api/auth",
        tags=["Authentication"],
    )

    # Admin API
    app.include_router(
        users.router,
        prefix=f"{settings.admin_api_prefix}/users",
        tags=["Admin - Users"],
    )
    app.include_router(
        audit.router,
        prefix=f"{settings.admin_api_prefix}/audit",
        tags=["Admin - Audit Log"],
    )
    app.include_router(
        versions.router,
        prefix=f"{settings.admin_api_prefix}/versions",
        tags=["Admin - Version History"],
    )
    app.include_router(
        categories.router,
        prefix=f"{settings.admin_api_prefix}/categories",
        tags=["Admin - Categories"],
    )
    app.include_router(
        sources.router,
        prefix=f"{settings.admin_api_prefix}/sources",
        tags=["Admin - Data Sources"],
    )
    app.include_router(
        crawler.router,
        prefix=f"{settings.admin_api_prefix}/crawler",
        tags=["Admin - Crawler"],
    )
    app.include_router(
        pysis.router,
        prefix=f"{settings.admin_api_prefix}/pysis",
        tags=["Admin - PySis"],
    )
    app.include_router(
        locations.router,
        prefix=f"{settings.admin_api_prefix}/locations",
        tags=["Admin - Locations"],
    )
    app.include_router(
        notifications.router,
        prefix=f"{settings.admin_api_prefix}/notifications",
        tags=["Admin - Notifications"],
    )
    app.include_router(
        external_apis.router,
        prefix=f"{settings.admin_api_prefix}/external-apis",
        tags=["Admin - External APIs"],
    )
    app.include_router(
        api_import.router,
        prefix=f"{settings.admin_api_prefix}/api-import",
        tags=["Admin - API Import"],
    )
    app.include_router(
        ai_discovery.router,
        prefix=f"{settings.admin_api_prefix}/ai-discovery",
        tags=["Admin - AI Discovery"],
    )
    app.include_router(
        api_templates.router,
        prefix=f"{settings.admin_api_prefix}/api-templates",
        tags=["Admin - API Templates"],
    )
    app.include_router(
        crawl_presets.router,
        prefix=f"{settings.admin_api_prefix}/crawl-presets",
        tags=["Admin - Crawl Presets"],
    )
    app.include_router(
        api_facet_sync.router,
        prefix=f"{settings.admin_api_prefix}/api-facet-syncs",
        tags=["Admin - API Facet Syncs"],
    )
    app.include_router(
        sharepoint.router,
        prefix=f"{settings.admin_api_prefix}/sharepoint",
        tags=["Admin - SharePoint"],
    )

    # Public API v1 (Legacy)
    app.include_router(
        data_router,
        prefix=f"{settings.api_v1_prefix}/data",
        tags=["API v1 - Data (Legacy)"],
    )
    app.include_router(
        export.router,
        prefix=f"{settings.api_v1_prefix}/export",
        tags=["API v1 - Export"],
    )

    # Entity-Facet System API v1
    app.include_router(
        entity_types.router,
        prefix=f"{settings.api_v1_prefix}/entity-types",
        tags=["API v1 - Entity Types"],
    )
    app.include_router(
        entities.router,
        prefix=f"{settings.api_v1_prefix}/entities",
        tags=["API v1 - Entities"],
    )
    app.include_router(
        facets.router,
        prefix=f"{settings.api_v1_prefix}/facets",
        tags=["API v1 - Facets"],
    )
    app.include_router(
        pysis_facets.router,
        prefix=f"{settings.api_v1_prefix}/pysis-facets",
        tags=["API v1 - PySis Facets"],
    )
    app.include_router(
        relations.router,
        prefix=f"{settings.api_v1_prefix}/relations",
        tags=["API v1 - Relations"],
    )
    app.include_router(
        analysis_router,
        prefix=f"{settings.api_v1_prefix}/analysis",
        tags=["API v1 - Analysis"],
    )
    app.include_router(
        assistant.router,
        prefix=f"{settings.api_v1_prefix}/assistant",
        tags=["API v1 - AI Assistant"],
    )
    app.include_router(
        dashboard.router,
        prefix=f"{settings.api_v1_prefix}/dashboard",
        tags=["API v1 - Dashboard"],
    )
    app.include_router(
        favorites.router,
        prefix=f"{settings.api_v1_prefix}/favorites",
        tags=["API v1 - Favorites"],
    )
    app.include_router(
        smart_query_history.router,
        prefix=f"{settings.api_v1_prefix}/smart-query/history",
        tags=["API v1 - Smart Query History"],
    )
    app.include_router(
        ai_tasks.router,
        prefix=f"{settings.api_v1_prefix}/ai-tasks",
        tags=["API v1 - AI Tasks"],
    )
    app.include_router(
        entity_data.router,
        prefix=f"{settings.api_v1_prefix}/entity-data",
        tags=["API v1 - Entity Data Enrichment"],
    )
    app.include_router(
        attachments.router,
        prefix=settings.api_v1_prefix,
        tags=["API v1 - Entity Attachments"],
    )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
    )
