"""Add Entity-Facet system for flexible analysis.

This migration introduces the new Entity-Facet architecture:
- EntityType: Defines types of entities (municipality, person, event, etc.)
- Entity: Generic entity instances (replaces hardcoded Location)
- FacetType: Defines types of facets (pain_point, contact, event_attendance, etc.)
- FacetValue: Concrete facet values for entities
- RelationType: Defines relationship types between entities
- EntityRelation: Concrete relationships between entities
- AnalysisTemplate: Configures which facets to use for analysis

This is a CLEAN START migration - it assumes existing data will be deleted
and re-seeded with the new structure.

Revision ID: k1234567899
Revises: j1234567898
Create Date: 2024-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "k1234567899"
down_revision: Union[str, None] = "j1234567898"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Step 1: Create new Entity-Facet tables
    # =========================================================================

    # EntityType table
    op.create_table(
        "entity_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_plural", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(100), nullable=False, server_default="mdi-help-circle"),
        sa.Column("color", sa.String(20), nullable=False, server_default="#607D8B"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("supports_hierarchy", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("hierarchy_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attribute_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", index=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Entity table
    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity_types.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("name", sa.String(500), nullable=False, index=True),
        sa.Column("name_normalized", sa.String(500), nullable=False, index=True),
        sa.Column("slug", sa.String(500), nullable=False, index=True),
        sa.Column("external_id", sa.String(255), nullable=True, index=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("hierarchy_path", sa.Text(), nullable=True, index=True),
        sa.Column("hierarchy_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("core_attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # FacetType table
    op.create_table(
        "facet_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_plural", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("value_type", sa.String(50), nullable=False, server_default="structured"),
        sa.Column("value_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("applicable_entity_type_slugs", postgresql.ARRAY(sa.String(100)), nullable=False, server_default="{}"),
        sa.Column("icon", sa.String(100), nullable=False, server_default="mdi-tag"),
        sa.Column("color", sa.String(20), nullable=False, server_default="#607D8B"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("aggregation_method", sa.String(50), nullable=False, server_default="dedupe"),
        sa.Column("deduplication_fields", postgresql.ARRAY(sa.String(100)), nullable=False, server_default="{}"),
        sa.Column("is_time_based", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("time_field_path", sa.String(255), nullable=True),
        sa.Column("default_time_filter", sa.String(50), nullable=False, server_default="all"),
        sa.Column("ai_extraction_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("ai_extraction_prompt", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", index=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # FacetValue table
    op.create_table(
        "facet_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("facet_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facet_types.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("text_representation", sa.Text(), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0", index=True),
        sa.Column("ai_model_used", sa.String(100), nullable=True),
        sa.Column("human_verified", sa.Boolean(), nullable=False, server_default="false", index=True),
        sa.Column("verified_by", sa.String(255), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("human_corrections", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # RelationType table
    op.create_table(
        "relation_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_inverse", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_entity_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity_types.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("target_entity_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity_types.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("cardinality", sa.String(10), nullable=False, server_default="n:m"),
        sa.Column("attribute_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("icon", sa.String(100), nullable=False, server_default="mdi-link"),
        sa.Column("color", sa.String(20), nullable=False, server_default="#607D8B"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", index=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # EntityRelation table
    op.create_table(
        "entity_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("relation_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("relation_types.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0", index=True),
        sa.Column("ai_model_used", sa.String(100), nullable=True),
        sa.Column("human_verified", sa.Boolean(), nullable=False, server_default="false", index=True),
        sa.Column("verified_by", sa.String(255), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("relation_type_id", "source_entity_id", "target_entity_id", name="uq_entity_relation_type_source_target"),
    )

    # AnalysisTemplate table
    op.create_table(
        "analysis_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("primary_entity_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity_types.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("facet_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("aggregation_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("display_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("extraction_prompt_template", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", index=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # =========================================================================
    # Step 2: Modify existing tables to use entity_id instead of location_id
    # =========================================================================

    # data_sources: Add entity_id, keep location_id for now (will be removed later)
    op.add_column(
        "data_sources",
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            index=True,
        ),
    )
    op.create_foreign_key(
        "fk_data_sources_entity_id_entities",
        "data_sources",
        "entities",
        ["entity_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # pysis_processes: Rename location_id to entity_id, update constraint
    # First, drop the old constraint
    op.drop_constraint("uq_location_pysis_process", "pysis_processes", type_="unique")

    # Rename column
    op.alter_column("pysis_processes", "location_id", new_column_name="entity_id")
    op.alter_column("pysis_processes", "location_name", new_column_name="entity_name")

    # Drop old FK and create new one
    op.drop_constraint("fk_pysis_processes_location_id_locations", "pysis_processes", type_="foreignkey")
    op.create_foreign_key(
        "fk_pysis_processes_entity_id_entities",
        "pysis_processes",
        "entities",
        ["entity_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Create new unique constraint
    op.create_unique_constraint(
        "uq_entity_pysis_process",
        "pysis_processes",
        ["entity_id", "pysis_process_id"],
    )


def downgrade() -> None:
    # =========================================================================
    # Reverse Step 2: Restore location_id in existing tables
    # =========================================================================

    # pysis_processes: Rename back
    op.drop_constraint("uq_entity_pysis_process", "pysis_processes", type_="unique")
    op.drop_constraint("fk_pysis_processes_entity_id_entities", "pysis_processes", type_="foreignkey")

    op.alter_column("pysis_processes", "entity_id", new_column_name="location_id")
    op.alter_column("pysis_processes", "entity_name", new_column_name="location_name")

    op.create_foreign_key(
        "fk_pysis_processes_location_id_locations",
        "pysis_processes",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_location_pysis_process",
        "pysis_processes",
        ["location_name", "pysis_process_id"],
    )

    # data_sources: Remove entity_id
    op.drop_constraint("fk_data_sources_entity_id_entities", "data_sources", type_="foreignkey")
    op.drop_column("data_sources", "entity_id")

    # =========================================================================
    # Reverse Step 1: Drop new tables
    # =========================================================================
    op.drop_table("analysis_templates")
    op.drop_table("entity_relations")
    op.drop_table("relation_types")
    op.drop_table("facet_values")
    op.drop_table("facet_types")
    op.drop_table("entities")
    op.drop_table("entity_types")
