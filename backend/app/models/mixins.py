"""Model mixins for common functionality."""

from datetime import datetime
from typing import Any, Dict, Set
from uuid import UUID

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column


class VersionedMixin:
    """
    Mixin for models that should be versioned.

    Adds version tracking capability to any model.
    Models using this mixin will have their changes tracked
    in the entity_versions table.

    Usage:
        class MyModel(Base, VersionedMixin):
            __tablename__ = "my_models"
            # ... other columns
    """

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Current version number",
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert entity to dict for versioning.

        Override in subclasses to customize serialization.

        Returns:
            Dict representation of the entity
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            result[column.name] = self._serialize_value(value)
        return result

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for JSON storage."""
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        if hasattr(value, "value"):  # Enum
            return value.value
        if isinstance(value, (list, dict)):
            return value
        return str(value)

    def get_versionable_fields(self) -> Set[str]:
        """
        Return set of field names that should be versioned.

        Override to exclude certain fields from versioning.

        Returns:
            Set of field names to track
        """
        # Fields that should never be versioned
        excluded = {
            "id",
            "created_at",
            "updated_at",
            "version",
            "password_hash",
        }
        return {c.name for c in self.__table__.columns} - excluded


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamps.

    Note: Most models already have these fields defined directly.
    This mixin is provided for consistency in new models.
    """

    from sqlalchemy import DateTime, func

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
