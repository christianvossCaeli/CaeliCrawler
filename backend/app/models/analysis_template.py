"""AnalysisTemplate model for defining analysis configurations."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.entity_type import EntityType


class AnalysisTemplate(Base):
    """
    Defines an analysis template (combination of facets for a category).

    AnalysisTemplates configure how entities should be analyzed:
    - Which facets to extract
    - How to display them
    - How to aggregate results
    """

    __tablename__ = "analysis_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Identification
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name (e.g., 'Windkraft-Analyse', 'Event-Tracking')",
    )
    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Associations
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Category this template is for",
    )
    primary_entity_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Primary entity type for this analysis",
    )

    # Facet configuration
    facet_config: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment='[{"facet_type_slug": "pain_point", "enabled": true, "display_order": 1, "label": "Pain Points", "time_filter": "all"}]',
    )

    # Aggregation configuration
    aggregation_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment='{"group_by": "entity", "show_relations": ["works_for"]}',
    )

    # Display configuration
    display_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment='UI display settings {"columns": [...], "default_sort": "name"}',
    )

    # AI configuration
    extraction_prompt_template: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Combined AI prompt template for this analysis",
    )

    # Status
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Default template for this category",
    )
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
        comment="System-defined template (cannot be deleted)",
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
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
    category: Mapped[Optional["Category"]] = relationship("Category")
    primary_entity_type: Mapped["EntityType"] = relationship("EntityType")

    def get_enabled_facet_slugs(self) -> List[str]:
        """Get list of enabled facet type slugs."""
        return [
            fc["facet_type_slug"]
            for fc in self.facet_config
            if fc.get("enabled", True)
        ]

    def get_facet_config_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get facet configuration by slug."""
        for fc in self.facet_config:
            if fc.get("facet_type_slug") == slug:
                return fc
        return None

    def __repr__(self) -> str:
        return f"<AnalysisTemplate(slug='{self.slug}', name='{self.name}')>"
