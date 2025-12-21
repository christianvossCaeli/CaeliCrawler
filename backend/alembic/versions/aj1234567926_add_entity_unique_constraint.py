"""Add unique constraint for entity deduplication.

Adds a partial unique constraint on (entity_type_id, name_normalized) for active entities.
This prevents duplicate entities from being created when the same name is normalized
consistently across all creation paths.

IMPORTANT: Before running this migration, check for existing duplicates:

SELECT entity_type_id, name_normalized, COUNT(*) as count
FROM entities
WHERE deleted_at IS NULL AND name_normalized IS NOT NULL
GROUP BY entity_type_id, name_normalized
HAVING COUNT(*) > 1;

Revision ID: aj1234567926
Revises: ai1234567925
Create Date: 2024-12-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "aj1234567926"
down_revision: Union[str, None] = "ai1234567925"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def index_exists(index_name: str) -> bool:
    """Check if an index exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname = :name"
        ),
        {"name": index_name},
    )
    return result.fetchone() is not None


def constraint_exists(constraint_name: str) -> bool:
    """Check if a constraint exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_constraint WHERE conname = :name"
        ),
        {"name": constraint_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    # First, ensure all entities have name_normalized filled
    # (backfill any NULL values using the name column)
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE entities
            SET name_normalized = LOWER(REGEXP_REPLACE(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(name, 'ä', 'ae', 'g'),
                        'ö', 'oe', 'g'
                    ),
                    'ü', 'ue', 'g'
                ),
                'ß', 'ss', 'g'
            ))
            WHERE name_normalized IS NULL AND name IS NOT NULL
        """)
    )

    # Create partial unique index (only for active entities)
    # This is more flexible than a constraint and allows us to use WHERE clause
    if not index_exists("uq_entity_type_name_normalized"):
        op.execute(
            sa.text("""
                CREATE UNIQUE INDEX uq_entity_type_name_normalized
                ON entities (entity_type_id, name_normalized)
                WHERE is_active = true AND name_normalized IS NOT NULL
            """)
        )


def downgrade() -> None:
    # Drop the unique index
    if index_exists("uq_entity_type_name_normalized"):
        op.execute(
            sa.text("DROP INDEX IF EXISTS uq_entity_type_name_normalized")
        )
