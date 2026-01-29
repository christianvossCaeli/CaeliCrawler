"""Cleanup invalid FacetTypes created from internal AI extraction fields.

Removes FacetTypes like 'suggested_additional_pages' that were incorrectly
created from internal AI extraction response fields.

Revision ID: zj1234567924
Revises: zi1234567923
Create Date: 2026-01-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "zj1234567924"
down_revision = "zi1234567923"
branch_labels = None
depends_on = None

# FacetType slugs that should never exist (internal AI extraction fields)
INVALID_SLUGS = [
    "suggested_additional_pages",
    "source_page",
    "source_pages",
    "page_numbers",
    "analyzed_pages",
    "total_pages",
]


def upgrade() -> None:
    """Remove invalid FacetTypes and their FacetValues."""
    conn = op.get_bind()

    for slug in INVALID_SLUGS:
        # First, get the FacetType ID
        result = conn.execute(
            text("SELECT id, name FROM facet_types WHERE slug = :slug"),
            {"slug": slug}
        )
        row = result.fetchone()

        if row:
            facet_type_id = row[0]
            facet_type_name = row[1]

            # Count FacetValues before deletion
            count_result = conn.execute(
                text("SELECT COUNT(*) FROM facet_values WHERE facet_type_id = :id"),
                {"id": facet_type_id}
            )
            value_count = count_result.scalar() or 0

            # Delete FacetValues first (foreign key constraint)
            conn.execute(
                text("DELETE FROM facet_values WHERE facet_type_id = :id"),
                {"id": facet_type_id}
            )

            # Delete the FacetType
            conn.execute(
                text("DELETE FROM facet_types WHERE id = :id"),
                {"id": facet_type_id}
            )

            print(f"  Deleted FacetType '{slug}' ({facet_type_name}) with {value_count} FacetValues")
        else:
            print(f"  FacetType '{slug}' not found (OK)")


def downgrade() -> None:
    """No downgrade - these FacetTypes should not be recreated."""
    pass
