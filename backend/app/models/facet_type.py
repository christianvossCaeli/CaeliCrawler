"""FacetType model for defining types of facets/attributes."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.facet_value import FacetValue


class ValueType(str, enum.Enum):
    """Type of value stored in a facet."""

    TEXT = "text"  # Simple text value
    STRUCTURED = "structured"  # Complex JSON structure
    OBJECT = "object"  # Alias for structured (backwards compatibility)
    LIST = "list"  # List of values
    REFERENCE = "reference"  # Reference to another entity
    NUMBER = "number"  # Numeric value (integer or float)
    BOOLEAN = "boolean"  # Boolean value (true/false)


class AggregationMethod(str, enum.Enum):
    """How to aggregate multiple facet values."""

    COUNT = "count"  # Just count occurrences
    SUM = "sum"  # Sum numeric values
    AVG = "avg"  # Average numeric values
    LIST = "list"  # List all values
    DEDUPE = "dedupe"  # Deduplicate by specified fields
    LATEST = "latest"  # Keep only the latest value
    MIN = "min"  # Minimum numeric value
    MAX = "max"  # Maximum numeric value


class TimeFilter(str, enum.Enum):
    """Default time filter for time-based facets."""

    ALL = "all"  # Show all
    FUTURE_ONLY = "future_only"  # Only future events
    PAST_ONLY = "past_only"  # Only past events


class FacetType(Base):
    """
    Defines a type of facet/attribute (e.g., Pain Point, Contact, Event Attendance).

    FacetTypes define what kind of information can be extracted and attached
    to entities, including the schema for values and how to aggregate them.
    """

    __tablename__ = "facet_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Identification
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-safe identifier (e.g., 'pain_point', 'contact')",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name (e.g., 'Pain Point', 'Kontakt')",
    )
    name_plural: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Plural form",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Value configuration
    value_type: Mapped[str] = mapped_column(
        String(50),
        default=ValueType.STRUCTURED.value,
        nullable=False,
        comment="Type of value: text, structured, list, reference",
    )
    value_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="JSON Schema defining the value structure",
    )

    # Applicable entity types (if empty, applies to all)
    applicable_entity_type_slugs: Mapped[List[str]] = mapped_column(
        ARRAY(String(100)),
        default=list,
        nullable=False,
        comment="Entity type slugs this facet applies to (empty = all)",
    )

    # UI Configuration
    icon: Mapped[str] = mapped_column(
        String(100),
        default="mdi-tag",
        nullable=False,
    )
    color: Mapped[str] = mapped_column(
        String(20),
        default="#607D8B",
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Aggregation configuration
    aggregation_method: Mapped[str] = mapped_column(
        String(50),
        default=AggregationMethod.DEDUPE.value,
        nullable=False,
    )
    deduplication_fields: Mapped[List[str]] = mapped_column(
        ARRAY(String(100)),
        default=list,
        nullable=False,
        comment="Fields to use for deduplication",
    )

    # Time-based configuration
    is_time_based: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Does this facet have a date/time component?",
    )
    time_field_path: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="JSON path to date field in value (e.g., 'event_date')",
    )
    default_time_filter: Mapped[str] = mapped_column(
        String(50),
        default=TimeFilter.ALL.value,
        nullable=False,
        comment="Default time filter: all, future_only, past_only",
    )

    # AI extraction configuration
    ai_extraction_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    ai_extraction_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="AI prompt template for extracting this facet",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="System-defined type (cannot be deleted)",
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
    facet_values: Mapped[List["FacetValue"]] = relationship(
        "FacetValue",
        back_populates="facet_type",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<FacetType(slug='{self.slug}', name='{self.name}')>"
