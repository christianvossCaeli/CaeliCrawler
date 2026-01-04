"""Application configuration using Pydantic Settings."""

import secrets
from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Known insecure default secret keys that must not be used in production
INSECURE_SECRET_KEYS = {
    "change-me-in-production",
    "your-secret-key-change-in-production",
    "secret",
    "changeme",
    "development-secret",
}


def _generate_dev_secret() -> str:
    """Generate a random secret key for development use.

    In development mode, if no SECRET_KEY is provided, we generate a random one.
    This is safer than using a static default that could accidentally be used.

    Note: This means sessions won't persist across restarts in development,
    which is generally acceptable for local development.
    """
    return f"dev-{secrets.token_urlsafe(32)}"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "CaeliCrawler"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = Field(default_factory=_generate_dev_secret)
    frontend_url: str = "https://app.caeli-wind.de"  # For email verification links
    schedule_timezone: str = "Europe/Berlin"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate critical settings for production environment."""
        if self.app_env == "production":
            # Ensure secret key is not a known insecure default
            if self.secret_key in INSECURE_SECRET_KEYS:
                raise ValueError(
                    "SECURITY ERROR: SECRET_KEY must be changed in production! "
                    'Generate a secure key with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )

            # Ensure auto-generated dev keys are not used in production
            if self.secret_key.startswith("dev-"):
                raise ValueError(
                    "SECURITY ERROR: Auto-generated development SECRET_KEY cannot be used in production! "
                    "Set a persistent SECRET_KEY in your environment."
                )

            # Ensure secret key has minimum length (256 bits = 32 bytes)
            if len(self.secret_key) < 32:
                raise ValueError("SECURITY ERROR: SECRET_KEY must be at least 32 characters in production")

            # Ensure debug is disabled in production
            if self.debug:
                raise ValueError("SECURITY ERROR: DEBUG must be False in production")

        return self

    # Database
    database_url: str = Field(default="postgresql+asyncpg://postgres:password@localhost:5432/caelichrawler")
    database_sync_url: str = Field(default="postgresql://postgres:password@localhost:5432/caelichrawler")

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Azure Document Intelligence (system-level, not per-user)
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""

    # Crawler Settings
    crawler_user_agent: str = "CaeliCrawler/1.0 (Research)"
    crawler_default_delay: float = 2.0
    crawler_max_concurrent_requests: int = 5
    crawler_respect_robots_txt: bool = True

    # Storage
    document_storage_path: str = "./storage/documents"
    attachment_storage_path: str = "./storage/attachments"
    attachment_max_size_mb: int = 20
    attachment_allowed_types: str = "image/png,image/jpeg,image/gif,image/webp,application/pdf"

    # PySis Integration
    pysis_api_base_url: str = "https://pisys.caeli-wind.de/api/pisys/v1"
    pysis_tenant_id: str = ""
    pysis_client_id: str = ""
    pysis_client_secret: str = ""
    pysis_scope: str = "api://7e32391f-a384-44b1-9850-d565b4a59ed0/.default"

    # Caeli Auction API Integration
    caeli_auction_marketplace_api_url: str = "https://auction.caeli-wind.de/api/auction-platform/v4/public-marketplace"
    caeli_auction_marketplace_api_auth: str = ""  # Base64-encoded Basic Auth credentials

    # SharePoint Online Integration (Microsoft Graph API)
    sharepoint_tenant_id: str = ""  # Azure AD Tenant ID
    sharepoint_client_id: str = ""  # Azure AD App Registration Client ID
    sharepoint_client_secret: str = ""  # Azure AD App Registration Client Secret
    sharepoint_default_site_url: str = ""  # Default site, e.g. "contoso.sharepoint.com:/sites/Documents"

    # External API Settings
    external_api_default_sync_interval: int = 4  # hours
    external_api_max_retries: int = 3

    # AI Source Discovery Settings
    ai_discovery_max_search_results: int = 20
    ai_discovery_max_extraction_pages: int = 10
    ai_discovery_timeout: int = 60

    # API Settings
    api_v1_prefix: str = "/api/v1"
    admin_api_prefix: str = "/api/admin"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # SMTP Configuration
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@caeli-wind.de"
    smtp_from_name: str = "CaeliCrawler"
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout: int = 30

    # Notification Settings
    notification_batch_size: int = 100
    notification_retry_max: int = 3
    notification_retry_delay: int = 300  # seconds

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Feature Flags
    feature_entity_level_facets: bool = True  # Allow assigning facets to individual entities (enabled by default)
    feature_pysis_field_templates: bool = False  # Enable PySis field templates functionality
    feature_entity_hierarchy: bool = True  # Enable parent-child relationships between entities
    feature_auto_entity_relations: bool = True  # Auto-create relations (located_in, member_of) for seed entities

    # AI Summary Settings
    ai_summary_max_tokens: int = 2500  # Max tokens for summary interpretation
    ai_summary_temperature: float = 0.3  # Temperature for summary AI calls

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
