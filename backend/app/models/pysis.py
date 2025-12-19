"""PySis integration models for field mapping and synchronization."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.entity import Entity


class SyncStatus(str, enum.Enum):
    """Synchronization status with PySis."""

    SYNCED = "SYNCED"
    PENDING = "PENDING"
    ERROR = "ERROR"
    NEVER = "NEVER"


class ValueSource(str, enum.Enum):
    """Source of field value."""

    AI = "AI"
    MANUAL = "MANUAL"
    PYSIS = "PYSIS"


class PySisFieldTemplate(Base):
    """
    Global field template definitions.

    Templates define reusable field configurations that can be applied
    to any municipality's PySis process, avoiding repetitive field setup.
    """

    __tablename__ = "pysis_field_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Template info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="Template name, e.g., 'Standard Windenergie Felder'",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Description of what this template is for",
    )

    # Field definitions as JSON array
    # [{internal_name, pysis_field_name, field_type, ai_extraction_prompt}]
    fields: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Array of field definitions",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PySisFieldTemplate(id={self.id}, name='{self.name}')>"


class PySisProcess(Base):
    """
    Links an entity to a PySis process.

    One entity can have multiple PySis processes (1:n relationship).
    """

    __tablename__ = "pysis_processes"
    __table_args__ = (
        UniqueConstraint(
            "entity_id", "pysis_process_id",
            name="uq_entity_pysis_process"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Entity FK (primary)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="FK to entity (municipality/organization)",
    )

    # Entity name (for display/legacy compatibility)
    entity_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Entity name for display and string matching",
    )

    # PySis process reference
    pysis_process_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="External PySis process ID (UUID from PySis system)",
    )

    # Display info
    name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Optional display name for this process",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notes about this process",
    )

    # Template reference (optional)
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pysis_field_templates.id", ondelete="SET NULL"),
        nullable=True,
        comment="Template used to create fields (for reference)",
    )

    # Sync metadata
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful sync with PySis",
    )
    sync_status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, name="pysis_sync_status"),
        default=SyncStatus.NEVER,
        nullable=False,
    )
    sync_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Last sync error message if any",
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
    entity: Mapped[Optional["Entity"]] = relationship(
        "Entity",
    )
    template: Mapped[Optional["PySisFieldTemplate"]] = relationship(
        "PySisFieldTemplate",
        lazy="selectin",
    )
    fields: Mapped[List["PySisProcessField"]] = relationship(
        "PySisProcessField",
        back_populates="process",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PySisProcess(id={self.id}, entity='{self.entity_name}', pysis_id='{self.pysis_process_id}')>"


class PySisProcessField(Base):
    """
    Individual field within a PySis process.

    Contains the field mapping between internal name and PySis field name,
    the current value, AI extraction configuration, and sync state.
    """

    __tablename__ = "pysis_process_fields"
    __table_args__ = (
        UniqueConstraint(
            "process_id", "pysis_field_name",
            name="uq_process_pysis_field"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Process reference
    process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pysis_processes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Field definition
    internal_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name, e.g., 'Ansprechpartner Gemeinde'",
    )
    pysis_field_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="PySis API field name, e.g., 'municipality_contact'",
    )
    field_type: Mapped[str] = mapped_column(
        String(50),
        default="text",
        nullable=False,
        comment="Field type: text, number, date, boolean, list",
    )

    # AI extraction configuration
    ai_extraction_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether to auto-extract this field via AI",
    )
    ai_extraction_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Custom AI prompt for extracting this field",
    )

    # Value storage
    current_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Current value (JSON string for complex types)",
    )
    ai_extracted_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Last AI-extracted value",
    )
    manual_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Manual override value",
    )
    value_source: Mapped[ValueSource] = mapped_column(
        Enum(ValueSource, name="pysis_value_source"),
        default=ValueSource.AI,
        nullable=False,
        comment="Source of current value: AI, MANUAL, or PYSIS",
    )

    # PySis sync state
    pysis_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Last value fetched from PySis API",
    )
    last_pushed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When value was last pushed to PySis",
    )
    last_pulled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When value was last pulled from PySis",
    )
    needs_push: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flag indicating value changed and needs sync to PySis",
    )

    # AI extraction metadata
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="AI confidence score if AI-extracted (0.0-1.0)",
    )
    extraction_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        comment="Primary source document for AI extraction",
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
    process: Mapped["PySisProcess"] = relationship(
        "PySisProcess",
        back_populates="fields",
    )
    extraction_document: Mapped[Optional["Document"]] = relationship(
        "Document",
        lazy="selectin",
    )

    @property
    def effective_value(self) -> Optional[str]:
        """
        Get the effective value based on source priority.
        Priority: MANUAL > AI > PYSIS
        """
        if self.value_source == ValueSource.MANUAL and self.manual_value is not None:
            return self.manual_value
        if self.ai_extracted_value is not None:
            return self.ai_extracted_value
        return self.pysis_value

    def __repr__(self) -> str:
        return f"<PySisProcessField(id={self.id}, internal='{self.internal_name}', pysis='{self.pysis_field_name}')>"

    # Relationship to history
    history: Mapped[List["PySisFieldHistory"]] = relationship(
        "PySisFieldHistory",
        back_populates="field",
        cascade="all, delete-orphan",
        order_by="desc(PySisFieldHistory.created_at)",
        lazy="dynamic",
    )


class PySisFieldHistory(Base):
    """
    History of field value changes.

    Tracks all changes to a field's value, including AI suggestions,
    manual edits, and PySis syncs.
    """

    __tablename__ = "pysis_field_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Field reference
    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pysis_process_fields.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Value snapshot
    value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="The value at this point in history",
    )
    source: Mapped[ValueSource] = mapped_column(
        Enum(ValueSource, name="pysis_value_source", create_type=False),
        nullable=False,
        comment="Source of this value: AI, MANUAL, or PYSIS",
    )

    # AI metadata (if AI-generated)
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="AI confidence score if AI-generated",
    )

    # Action that created this entry
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Action: 'generated', 'accepted', 'rejected', 'manual_edit', 'pulled', 'pushed'",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship
    field: Mapped["PySisProcessField"] = relationship(
        "PySisProcessField",
        back_populates="history",
    )

    def __repr__(self) -> str:
        return f"<PySisFieldHistory(id={self.id}, field_id={self.field_id}, action='{self.action}')>"
