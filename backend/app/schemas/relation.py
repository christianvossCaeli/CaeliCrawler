"""Relation schemas for API validation."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.relation_type import Cardinality
from app.utils.text import create_slug as generate_slug

# Regex pattern for valid slugs: lowercase letters, numbers, and hyphens only
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_MAX_LENGTH = 100


# ============================================================================
# RelationType Schemas
# ============================================================================


class RelationTypeBase(BaseModel):
    """Base relation type schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    name_inverse: str = Field(..., min_length=1, max_length=255, description="Inverse display name")
    description: Optional[str] = Field(None, description="Description")

    # Entity type constraints
    source_entity_type_id: UUID = Field(..., description="Source entity type ID")
    target_entity_type_id: UUID = Field(..., description="Target entity type ID")

    # Cardinality with enum validation
    cardinality: Cardinality = Field(
        default=Cardinality.MANY_TO_MANY,
        description="Cardinality: 1:1, 1:n, n:1, n:m"
    )

    # Attribute schema
    attribute_schema: Optional[Dict[str, Any]] = Field(
        None,
        description='Schema for relation attributes {"role": "string", "since": "date"}',
    )

    # UI Configuration
    icon: str = Field(default="mdi-link", description="Material Design Icon name")
    color: str = Field(default="#607D8B", description="Hex color for UI")
    display_order: int = Field(default=0, description="Order in UI lists")

    is_active: bool = Field(default=True, description="Whether relation type is active")


class RelationTypeCreate(RelationTypeBase):
    """Schema for creating a new relation type."""

    slug: Optional[str] = Field(
        None,
        max_length=SLUG_MAX_LENGTH,
        description="URL-friendly slug (auto-generated if not provided)"
    )

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug_if_empty(cls, v, info):
        if not v and "name" in info.data:
            return generate_slug(info.data["name"])
        return v

    @field_validator("slug", mode="after")
    @classmethod
    def validate_slug_format(cls, v):
        if v is not None:
            if len(v) > SLUG_MAX_LENGTH:
                raise ValueError(f"Slug must be at most {SLUG_MAX_LENGTH} characters")
            if not SLUG_PATTERN.match(v):
                raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


class RelationTypeUpdate(BaseModel):
    """Schema for updating a relation type."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    name_inverse: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    cardinality: Optional[str] = None
    attribute_schema: Optional[Dict[str, Any]] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class RelationTypeResponse(RelationTypeBase):
    """Schema for relation type response."""

    id: UUID
    slug: str
    is_system: bool
    created_at: datetime
    updated_at: datetime

    # Nested info
    source_entity_type_name: Optional[str] = Field(None, description="Source entity type name")
    source_entity_type_slug: Optional[str] = Field(None, description="Source entity type slug")
    target_entity_type_name: Optional[str] = Field(None, description="Target entity type name")
    target_entity_type_slug: Optional[str] = Field(None, description="Target entity type slug")

    # Computed fields
    relation_count: int = Field(default=0, description="Number of relations of this type")

    model_config = {"from_attributes": True}


class RelationTypeListResponse(BaseModel):
    """Schema for relation type list response."""

    items: List[RelationTypeResponse]
    total: int
    page: int = Field(default=1, description="Current page number")
    per_page: int = Field(default=50, description="Items per page")
    pages: int = Field(default=1, description="Total number of pages")


# ============================================================================
# EntityRelation Schemas
# ============================================================================


class EntityRelationBase(BaseModel):
    """Base entity relation schema with common fields."""

    # Relationship attributes
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Relation-specific attributes")

    # Validity period
    valid_from: Optional[datetime] = Field(None, description="When this relationship starts")
    valid_until: Optional[datetime] = Field(None, description="When this relationship ends")

    # Source tracking
    source_url: Optional[str] = Field(None, description="Original URL")

    # AI metadata
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="AI confidence")

    is_active: bool = Field(default=True, description="Whether relation is active")


class EntityRelationCreate(EntityRelationBase):
    """Schema for creating a new entity relation."""

    relation_type_id: UUID = Field(..., description="Relation type ID")
    source_entity_id: UUID = Field(..., description="Source entity ID")
    target_entity_id: UUID = Field(..., description="Target entity ID")
    source_document_id: Optional[UUID] = Field(None, description="Source document ID")
    ai_model_used: Optional[str] = Field(None, description="AI model used")


class EntityRelationUpdate(BaseModel):
    """Schema for updating an entity relation."""

    attributes: Optional[Dict[str, Any]] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    source_url: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    human_verified: Optional[bool] = None
    is_active: Optional[bool] = None


class EntityRelationResponse(EntityRelationBase):
    """Schema for entity relation response."""

    id: UUID
    relation_type_id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    source_document_id: Optional[UUID]
    ai_model_used: Optional[str]

    # Verification
    human_verified: bool
    verified_by: Optional[str]
    verified_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime

    # Nested info
    relation_type_slug: Optional[str] = Field(None, description="Relation type slug")
    relation_type_name: Optional[str] = Field(None, description="Relation type name")
    source_entity_name: Optional[str] = Field(None, description="Source entity name")
    source_entity_slug: Optional[str] = Field(None, description="Source entity slug")
    source_entity_type_slug: Optional[str] = Field(None, description="Source entity type slug")
    target_entity_name: Optional[str] = Field(None, description="Target entity name")
    target_entity_slug: Optional[str] = Field(None, description="Target entity slug")
    target_entity_type_slug: Optional[str] = Field(None, description="Target entity type slug")

    model_config = {"from_attributes": True}


class EntityRelationListResponse(BaseModel):
    """Schema for entity relation list response."""

    items: List[EntityRelationResponse]
    total: int
    page: int
    per_page: int
    pages: int


class EntityRelationsGraph(BaseModel):
    """Graph representation of entity relations."""

    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Entity nodes")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="Relation edges")
