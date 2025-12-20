"""Add unique index for facet value deduplication.

This migration adds a functional unique index on facet_values to prevent
duplicate entries at the database level. The index uses MD5 hash of
text_representation to handle potentially long text values.

This eliminates race conditions in check_duplicate_facet() by letting
the database enforce uniqueness.

Revision ID: aa1234567915
Revises: z1234567914
Create Date: 2024-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "aa1234567915"
down_revision: Union[str, None] = ("z1234567914", "f32928f1d25f")  # Merge multiple heads
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique index for facet value deduplication."""
    # Create a functional unique index using MD5 hash of text_representation.
    # This allows us to have a unique constraint on (entity_id, facet_type_id, text)
    # without hitting PostgreSQL's index size limits for large text values.
    #
    # The index is partial (WHERE is_active = true) to allow "soft deleted"
    # duplicates and to improve index performance.
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_facet_values_dedup
        ON facet_values (entity_id, facet_type_id, md5(text_representation))
        WHERE is_active = true;
    """)

    # Add a comment to document the index purpose
    op.execute("""
        COMMENT ON INDEX ix_facet_values_dedup IS
        'Prevents duplicate facet values for the same entity and facet type. Uses MD5 hash for efficient comparison of long text.';
    """)


def downgrade() -> None:
    """Remove the deduplication index."""
    op.execute("DROP INDEX IF EXISTS ix_facet_values_dedup;")
