"""ApiExport model for configuring data export endpoints."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.category import Category


class ExportType(str, enum.Enum):
    """Type of export endpoint."""

    INTERNAL_API = "INTERNAL_API"  # Exposed via our API
    WEBHOOK = "WEBHOOK"  # Push to webhook URL on changes
    PUSH_TO_EXTERNAL = "PUSH_TO_EXTERNAL"  # Push to external API


class ApiExport(Base):
    """
    API export configuration.

    Defines how and where extracted data should be exported.
    """

    __tablename__ = "api_exports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Optional category filter (NULL = all categories)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Export type
    endpoint_type: Mapped[ExportType] = mapped_column(
        Enum(ExportType, name="export_type"),
        nullable=False,
    )

    # Configuration
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    # Example config for WEBHOOK:
    # {
    #     "url": "https://example.com/webhook",
    #     "events": ["new_document", "data_extracted"],
    #     "auth": {"type": "bearer", "token": "xxx"},
    #     "filter": {"min_confidence": 0.8}
    # }

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Statistics
    last_export: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    export_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(nullable=True)

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
    category: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="api_exports",
    )

    def __repr__(self) -> str:
        return f"<ApiExport(id={self.id}, name='{self.name}', type={self.endpoint_type})>"
