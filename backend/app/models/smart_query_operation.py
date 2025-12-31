"""Smart Query Operation model for tracking history and favorites."""

import enum
import hashlib
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class OperationType(str, enum.Enum):
    """Type of Smart Query operation."""

    START_CRAWL = "start_crawl"
    CREATE_CATEGORY_SETUP = "create_category_setup"
    CREATE_ENTITY = "create_entity"
    CREATE_ENTITY_TYPE = "create_entity_type"
    CREATE_FACET = "create_facet"
    CREATE_RELATION = "create_relation"
    FETCH_AND_CREATE_FROM_API = "fetch_and_create_from_api"
    DISCOVER_SOURCES = "discover_sources"
    COMBINED = "combined"
    OTHER = "other"


class SmartQueryOperation(Base):
    """
    Track Smart Query write operations for history and favorites.

    This enables:
    - History of executed commands
    - Favorites for frequently used commands
    - Quick re-execution without re-typing
    """

    __tablename__ = "smart_query_operations"

    __table_args__ = (
        # Index for user history lookup
        Index("ix_smart_query_operations_user_id", "user_id"),
        # Index for favorites filtering
        Index("ix_smart_query_operations_user_favorite", "user_id", "is_favorite"),
        # Index for history sorting (newest first)
        Index("ix_smart_query_operations_user_created", "user_id", "created_at"),
        # Index for operation type filtering
        Index("ix_smart_query_operations_operation_type", "operation_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # The natural language command text
    command_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Hash for deduplication (MD5 of normalized command_text)
    command_hash: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    # Operation type for filtering/categorization
    operation_type: Mapped[OperationType] = mapped_column(
        Enum(OperationType, name="smart_query_operation_type"),
        default=OperationType.OTHER,
        nullable=False,
    )

    # Parsed interpretation from AI (for display and re-execution)
    interpretation: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Execution result summary
    result_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # User-friendly display name (auto-generated or user-edited)
    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Favorite flag
    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Execution statistics
    execution_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    # Success tracking
    was_successful: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="smart_query_operations")

    @staticmethod
    def compute_hash(command_text: str) -> str:
        """Compute MD5 hash of normalized command text for deduplication."""
        normalized = command_text.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()  # noqa: S324

    def __repr__(self) -> str:
        return f"<SmartQueryOperation(id={self.id}, type={self.operation_type}, favorite={self.is_favorite})>"
