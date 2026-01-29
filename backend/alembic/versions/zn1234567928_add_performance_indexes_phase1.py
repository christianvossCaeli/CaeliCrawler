"""Add performance indexes for Phase 1 optimization.

Adds composite/GIN indexes identified in performance audit:
- facet_values: entity_id + source_type (filter by source)
- entities: core_attributes GIN (fast JSONB searches)

Revision ID: zn1234567928
Revises: zm1234567927
Create Date: 2026-01-28
"""

from alembic import op

revision = "zn1234567928"
down_revision = "zm1234567927"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # FacetValues: composite index for filtering by entity and source type
    op.create_index(
        "ix_facet_values_entity_source",
        "facet_values",
        ["entity_id", "source_type"],
    )

    # Entities: GIN index for fast JSONB queries on core_attributes
    op.create_index(
        "ix_entities_core_attributes_gin",
        "entities",
        ["core_attributes"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_entities_core_attributes_gin", table_name="entities")
    op.drop_index("ix_facet_values_entity_source", table_name="facet_values")
