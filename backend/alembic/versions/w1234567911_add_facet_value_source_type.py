"""Add source_type field to facet_values table.

This migration adds a source_type enum field to track how each facet value
was created (document extraction, manual entry, PySis, Smart Query, AI Assistant, or import).

Revision ID: w1234567911
Revises: v1234567910
Create Date: 2024-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "w1234567911"
down_revision: Union[str, None] = "v1234567910"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The enum type facetvaluesourcetype is created automatically by SQLAlchemy
    # when the model is loaded. We just need to add the column.
    # Check if column already exists to make migration idempotent
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'facet_values' AND column_name = 'source_type'
    """))
    if result.fetchone() is None:
        # Add the source_type column with default 'DOCUMENT' for existing records
        op.execute("""
            ALTER TABLE facet_values
            ADD COLUMN source_type facetvaluesourcetype
            NOT NULL
            DEFAULT 'DOCUMENT'
        """)

        # Add comment
        op.execute("""
            COMMENT ON COLUMN facet_values.source_type IS
            'How this value was created (DOCUMENT, MANUAL, PYSIS, etc.)'
        """)

    # Create an index on source_type for efficient filtering (if not exists)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_facet_values_source_type
        ON facet_values (source_type)
    """)


def downgrade() -> None:
    # Drop the index
    op.drop_index('ix_facet_values_source_type', table_name='facet_values')

    # Drop the column
    op.drop_column('facet_values', 'source_type')

    # Drop the enum type
    sa.Enum(name='facetvaluesourcetype').drop(op.get_bind(), checkfirst=True)
