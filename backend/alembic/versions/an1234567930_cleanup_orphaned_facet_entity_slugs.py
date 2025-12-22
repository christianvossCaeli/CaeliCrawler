"""Cleanup orphaned entity type slugs from facet_types

Revision ID: an1234567930
Revises: am1234567929
Create Date: 2025-12-21

This migration removes orphaned entity type slugs from the
applicable_entity_type_slugs array in facet_types table.
These orphaned references occur when an entity_type is deleted
but the FacetType references were not cleaned up.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'an1234567930'
down_revision = 'am1234567929'
branch_labels = None
depends_on = None


def upgrade():
    # Get connection for raw SQL execution
    conn = op.get_bind()

    # Get all valid entity type slugs
    valid_slugs_result = conn.execute(
        sa.text("SELECT slug FROM entity_types")
    )
    valid_slugs = {row[0] for row in valid_slugs_result}

    # Get all facet types with their applicable_entity_type_slugs
    facet_types_result = conn.execute(
        sa.text("""
            SELECT id, applicable_entity_type_slugs
            FROM facet_types
            WHERE array_length(applicable_entity_type_slugs, 1) > 0
        """)
    )

    # Process each facet type and remove orphaned slugs
    for row in facet_types_result:
        facet_id = row[0]
        current_slugs = row[1] or []

        # Filter out orphaned slugs
        cleaned_slugs = [s for s in current_slugs if s in valid_slugs]

        # Only update if there were orphaned slugs
        if len(cleaned_slugs) != len(current_slugs):
            orphaned = set(current_slugs) - set(cleaned_slugs)
            print(f"Facet {facet_id}: Removing orphaned slugs: {orphaned}")

            conn.execute(
                sa.text("""
                    UPDATE facet_types
                    SET applicable_entity_type_slugs = :slugs,
                        updated_at = NOW()
                    WHERE id = :facet_id
                """),
                {"slugs": cleaned_slugs, "facet_id": facet_id}
            )


def downgrade():
    # Data migration - cannot be reversed
    # Orphaned slugs are intentionally removed and cannot be restored
    pass
