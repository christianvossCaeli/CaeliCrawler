"""User dashboard preferences model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserDashboardPreference(Base):
    """User's dashboard widget configuration and preferences."""

    __tablename__ = "user_dashboard_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Widget configuration stored as JSONB
    # Structure:
    # {
    #   "widgets": [
    #     {
    #       "id": "stats-entities",
    #       "type": "stats-entities",
    #       "enabled": true,
    #       "position": { "x": 0, "y": 0, "w": 1, "h": 1 },
    #       "config": { "refreshInterval": 60000 }
    #     },
    #     ...
    #   ],
    #   "version": 1
    # }
    widget_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
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
    user: Mapped["User"] = relationship(
        "User",
        back_populates="dashboard_preferences",
    )

    def __repr__(self) -> str:
        return f"<UserDashboardPreference user_id={self.user_id}>"

    @property
    def widgets(self) -> list[dict[str, Any]]:
        """Get the list of widget configurations."""
        return self.widget_config.get("widgets", [])

    @property
    def enabled_widgets(self) -> list[dict[str, Any]]:
        """Get only enabled widgets."""
        return [w for w in self.widgets if w.get("enabled", True)]

    def get_widget(self, widget_id: str) -> dict[str, Any] | None:
        """Get a specific widget by ID."""
        for widget in self.widgets:
            if widget.get("id") == widget_id:
                return widget
        return None

    def set_widget_enabled(self, widget_id: str, enabled: bool) -> bool:
        """Enable or disable a widget. Returns True if widget was found."""
        widgets = self.widget_config.get("widgets", [])
        for widget in widgets:
            if widget.get("id") == widget_id:
                widget["enabled"] = enabled
                return True
        return False
