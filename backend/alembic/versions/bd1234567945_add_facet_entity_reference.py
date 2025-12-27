"""Add entity reference fields to FacetType and FacetValue.

Allows FacetValues to optionally reference another Entity (e.g., a contact
facet can reference a Person entity). FacetType gets configuration for
which entity types are allowed as references.

Revision ID: bd1234567945
Revises: bc1234567944
Create Date: 2025-12-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "bd1234567945"
down_revision = "bc1234567944"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # ==========================================================================
    # FacetType: Add entity reference configuration
    # ==========================================================================

    # allows_entity_reference - whether this facet type can reference entities
    if not column_exists("facet_types", "allows_entity_reference"):
        op.add_column(
            "facet_types",
            sa.Column(
                "allows_entity_reference",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="Can this FacetType reference another Entity?"
            )
        )

    # target_entity_type_slugs - which entity types are allowed as references
    if not column_exists("facet_types", "target_entity_type_slugs"):
        op.add_column(
            "facet_types",
            sa.Column(
                "target_entity_type_slugs",
                postgresql.ARRAY(sa.String(100)),
                nullable=False,
                server_default="{}",
                comment="Allowed entity type slugs for reference (empty = all)"
            )
        )

    # auto_create_entity - automatically create entity if not found
    if not column_exists("facet_types", "auto_create_entity"):
        op.add_column(
            "facet_types",
            sa.Column(
                "auto_create_entity",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="Automatically create Entity if none found during matching?"
            )
        )

    # ==========================================================================
    # FacetValue: Add target entity reference
    # ==========================================================================

    # target_entity_id - optional reference to another entity
    if not column_exists("facet_values", "target_entity_id"):
        op.add_column(
            "facet_values",
            sa.Column(
                "target_entity_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
                comment="Optional reference to another Entity"
            )
        )

        # Add foreign key constraint
        op.create_foreign_key(
            "fk_facet_values_target_entity",
            "facet_values",
            "entities",
            ["target_entity_id"],
            ["id"],
            ondelete="SET NULL"
        )

        # Add index for efficient lookups
        op.create_index(
            "ix_facet_values_target_entity_id",
            "facet_values",
            ["target_entity_id"],
            postgresql_where=sa.text("target_entity_id IS NOT NULL")
        )

    # ==========================================================================
    # Update existing 'contact' FacetType to allow entity references
    # ==========================================================================

    # This enables the new feature for the contact facet type
    op.execute("""
        UPDATE facet_types
        SET
            allows_entity_reference = true,
            target_entity_type_slugs = ARRAY['person', 'organization']::varchar[],
            auto_create_entity = true
        WHERE slug = 'contact'
    """)


def downgrade() -> None:
    # Reset contact facet type
    op.execute("""
        UPDATE facet_types
        SET
            allows_entity_reference = false,
            target_entity_type_slugs = '{}',
            auto_create_entity = false
        WHERE slug = 'contact'
    """)

    # Drop FacetValue target_entity_id
    op.drop_index("ix_facet_values_target_entity_id", table_name="facet_values")
    op.drop_constraint("fk_facet_values_target_entity", "facet_values", type_="foreignkey")
    op.drop_column("facet_values", "target_entity_id")

    # Drop FacetType columns
    op.drop_column("facet_types", "auto_create_entity")
    op.drop_column("facet_types", "target_entity_type_slugs")
    op.drop_column("facet_types", "allows_entity_reference")
