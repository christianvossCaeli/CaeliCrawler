"""User favorites model for bookmarking entities."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.entity import Entity
    from app.models.user import User


class UserFavorite(Base):
    """User's favorite/bookmarked entities."""

    __tablename__ = "user_favorites"

    __table_args__ = (
        # Ensure a user can only favorite an entity once
        UniqueConstraint("user_id", "entity_id", name="uq_user_favorites_user_entity"),
        # Index for quick lookups by user
        Index("ix_user_favorites_user_id", "user_id"),
        # Index for entity lookups
        Index("ix_user_favorites_entity_id", "entity_id"),
        # Composite index for user + created_at (sorting favorites)
        Index("ix_user_favorites_user_created", "user_id", "created_at"),
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

    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="favorites",
    )
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="favorited_by",
    )

    def __repr__(self) -> str:
        return f"<UserFavorite user_id={self.user_id} entity_id={self.entity_id}>"
