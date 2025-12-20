"""ExternalAPIConfig model for external API integration configuration."""

import enum
import os
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.data_source import DataSource
    from app.models.entity import Entity
    from external_apis.models.sync_record import SyncRecord


class AuthType(str, enum.Enum):
    """Authentication types supported by external APIs."""

    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"


class SyncStatus(str, enum.Enum):
    """Status of the last sync operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ExternalAPIConfig(Base):
    """Configuration for external API integration.

    This model stores all configuration needed to connect to an external API,
    map its data to entities, and manage the sync lifecycle.
    """

    __tablename__ = "external_api_configs"

    __table_args__ = (
        Index("ix_external_api_configs_sync_due", "sync_enabled", "last_sync_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Optional link to DataSource
    data_source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )

    # Basic identification
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # API Configuration
    api_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Type identifier for client selection (e.g., auction, weather)",
    )
    api_base_url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )
    api_endpoint: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    # Authentication
    auth_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AuthType.NONE.value,
    )
    auth_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Authentication config (env var references, not actual secrets)",
    )

    # Sync Configuration
    sync_interval_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=4,
    )
    sync_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_sync_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    last_sync_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    last_sync_stats: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Entity Mapping Configuration
    entity_type_slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Target EntityType slug (e.g., wind_project)",
    )
    id_field: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="id",
    )
    name_field: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="name",
    )
    field_mappings: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    location_fields: Mapped[List[str]] = mapped_column(
        ARRAY(String(255)),
        nullable=False,
        default=list,
    )

    # Facet Mapping Configuration
    facet_mappings: Mapped[Dict[str, str]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Maps API fields to FacetType slugs for automatic FacetValue creation",
    )

    # Request Configuration
    request_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Additional request config (headers, params, pagination)",
    )

    # Lifecycle Management
    mark_missing_inactive: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    inactive_after_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=7,
    )

    # AI Entity Linking
    ai_linking_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    link_to_entity_types: Mapped[List[str]] = mapped_column(
        ARRAY(String(100)),
        nullable=False,
        default=list,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    data_source: Mapped[Optional["DataSource"]] = relationship(
        "DataSource",
        back_populates="external_api_config",
    )
    sync_records: Mapped[List["SyncRecord"]] = relationship(
        "SyncRecord",
        back_populates="external_api_config",
        cascade="all, delete-orphan",
    )
    managed_entities: Mapped[List["Entity"]] = relationship(
        "Entity",
        back_populates="external_source",
        foreign_keys="Entity.external_source_id",
    )

    def get_auth_token(self) -> Optional[str]:
        """Get the authentication token from environment variable.

        The auth_config should contain a reference to an environment variable,
        not the actual secret. This method resolves that reference.

        Returns:
            The authentication token, or None if not configured.
        """
        if self.auth_type == AuthType.NONE.value:
            return None

        env_var = self.auth_config.get("token_env_var")
        if env_var:
            return os.environ.get(env_var)

        # For basic auth, might have separate username/password env vars
        username_var = self.auth_config.get("username_env_var")
        password_var = self.auth_config.get("password_env_var")
        if username_var and password_var:
            username = os.environ.get(username_var)
            password = os.environ.get(password_var)
            if username and password:
                import base64

                return base64.b64encode(f"{username}:{password}".encode()).decode()

        return None

    def is_due_for_sync(self) -> bool:
        """Check if this config is due for synchronization.

        Returns:
            True if sync should be performed, False otherwise.
        """
        if not self.sync_enabled or not self.is_active:
            return False

        if self.last_sync_at is None:
            return True

        from datetime import timedelta

        now = datetime.now(timezone.utc)
        next_sync = self.last_sync_at + timedelta(hours=self.sync_interval_hours)
        return now >= next_sync

    def __repr__(self) -> str:
        return f"<ExternalAPIConfig(id={self.id}, name='{self.name}', api_type='{self.api_type}')>"
