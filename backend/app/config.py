"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List

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
    secret_key: str = Field(default="change-me-in-production")

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate critical settings for production environment."""
        if self.app_env == "production":
            # Ensure secret key is not a known insecure default
            if self.secret_key in INSECURE_SECRET_KEYS:
                raise ValueError(
                    "SECURITY ERROR: SECRET_KEY must be changed in production! "
                    "Generate a secure key with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )

            # Ensure secret key has minimum length (256 bits = 32 bytes)
            if len(self.secret_key) < 32:
                raise ValueError(
                    "SECURITY ERROR: SECRET_KEY must be at least 32 characters in production"
                )

            # Ensure debug is disabled in production
            if self.debug:
                raise ValueError(
                    "SECURITY ERROR: DEBUG must be False in production"
                )

        return self

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/caelichrawler"
    )
    database_sync_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/caelichrawler"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Azure OpenAI - Main Settings
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2025-04-01-preview"

    # Azure OpenAI - Model Deployments for different purposes
    azure_openai_deployment_name: str = "gpt-4.1-mini"  # Default chat deployment
    azure_openai_embeddings_deployment: str = "text-embedding-3-large"  # Embeddings

    # Task-specific deployments (can override default)
    azure_openai_deployment_chat: str = ""  # Chat/Summarization (default: deployment_name)
    azure_openai_deployment_extraction: str = ""  # Information extraction from text
    azure_openai_deployment_pdf: str = ""  # PDF document analysis
    azure_openai_deployment_web: str = ""  # Website content extraction
    azure_openai_deployment_classification: str = ""  # Document classification

    def get_deployment_for_task(self, task: str) -> str:
        """Get the appropriate deployment for a task type."""
        task_map = {
            "chat": self.azure_openai_deployment_chat,
            "extraction": self.azure_openai_deployment_extraction,
            "pdf": self.azure_openai_deployment_pdf,
            "web": self.azure_openai_deployment_web,
            "classification": self.azure_openai_deployment_classification,
            "embeddings": self.azure_openai_embeddings_deployment,
        }
        # Return task-specific deployment or fall back to default
        return task_map.get(task) or self.azure_openai_deployment_name

    # Azure Document Intelligence
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""

    # Crawler Settings
    crawler_user_agent: str = "CaeliCrawler/1.0 (Research)"
    crawler_default_delay: float = 2.0
    crawler_max_concurrent_requests: int = 5
    crawler_respect_robots_txt: bool = True

    # Storage
    document_storage_path: str = "./storage/documents"

    # PySis Integration
    pysis_api_base_url: str = "https://pisys.caeli-wind.de/api/pisys/v1"
    pysis_tenant_id: str = ""
    pysis_client_id: str = ""
    pysis_client_secret: str = ""
    pysis_scope: str = "api://7e32391f-a384-44b1-9850-d565b4a59ed0/.default"

    # API Settings
    api_v1_prefix: str = "/api/v1"
    admin_api_prefix: str = "/api/admin"
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

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
    feature_entity_level_facets: bool = False  # Allow assigning facets to individual entities (vs. only at type level)
    feature_pysis_field_templates: bool = False  # Enable PySis field templates functionality

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
