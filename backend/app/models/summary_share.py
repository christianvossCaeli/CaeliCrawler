"""Summary Share model for shareable links.

Enables sharing custom summaries via public links with optional
password protection and expiration.
"""

import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.custom_summary import CustomSummary


def generate_share_token() -> str:
    """Generate a URL-safe share token."""
    return secrets.token_urlsafe(32)


class SummaryShare(Base):
    """
    Shareable link for a custom summary.

    Features:
    - Unique URL-safe token for public access
    - Optional password protection (bcrypt hashed)
    - Optional expiration date
    - View count tracking
    - Export permission control
    """

    __tablename__ = "summary_shares"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    summary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("custom_summaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Share token (URL-friendly, unique)
    share_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        default=generate_share_token,
        comment="URL-safe unique token for sharing",
    )

    # Optional password (bcrypt hashed)
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="bcrypt hashed password for access",
    )

    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Optional expiration date",
    )

    # Permissions
    allow_export: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether recipient can export the summary",
    )

    # Statistics
    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times this link was viewed",
    )
    last_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last view timestamp",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this share link is active",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    summary: Mapped["CustomSummary"] = relationship(
        "CustomSummary",
        back_populates="shares",
    )

    # Indexes
    __table_args__ = (Index("ix_summary_shares_active_token", "is_active", "share_token"),)

    def is_expired(self) -> bool:
        """Check if this share link has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(self.expires_at.tzinfo) > self.expires_at

    def is_accessible(self) -> bool:
        """Check if this share link is accessible (active and not expired)."""
        return self.is_active and not self.is_expired()

    def __repr__(self) -> str:
        return f"<SummaryShare(id={self.id}, token={self.share_token[:8]}..., active={self.is_active})>"
