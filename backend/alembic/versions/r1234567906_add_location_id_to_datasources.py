"""Add location_id FK to data_sources table.

This migration adds a proper foreign key relationship from data_sources to locations,
enabling efficient geographic filtering and clustering.

Changes:
- Add location_id column (UUID, nullable)
- Add foreign key constraint to locations table
- Create index for efficient filtering

Revision ID: r1234567906
Revises: q1234567905
Create Date: 2024-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "r1234567906"
down_revision: Union[str, None] = "q1234567905"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Note: The location_id column, FK, and index already exist in the database.
    # This migration only ensures the alembic version is updated and syncs
    # any sources with locations that haven't been linked yet.
    # =========================================================================

    # Check if column exists before adding (safe migration)
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'data_sources' AND column_name = 'location_id'
    """))
    column_exists = result.fetchone() is not None

    if not column_exists:
        # Step 1: Add location_id column
        op.add_column(
            "data_sources",
            sa.Column(
                "location_id",
                UUID(as_uuid=True),
                nullable=True,
                comment="FK to location for geographic clustering",
            ),
        )

        # Step 2: Add foreign key constraint
        op.create_foreign_key(
            "fk_data_sources_location_id",
            "data_sources",
            "locations",
            ["location_id"],
            ["id"],
            ondelete="SET NULL",
        )

        # Step 3: Create index for efficient filtering
        op.create_index(
            "ix_data_sources_location_id",
            "data_sources",
            ["location_id"],
        )

    # =========================================================================
    # Always run: Migrate existing data - link sources to locations by name match
    # =========================================================================

    op.execute("""
        UPDATE data_sources ds
        SET location_id = l.id
        FROM locations l
        WHERE ds.location_name IS NOT NULL
          AND ds.location_id IS NULL
          AND LOWER(ds.location_name) = LOWER(l.name)
          AND (ds.country IS NULL OR ds.country = l.country)
    """)


def downgrade() -> None:
    # =========================================================================
    # Step 1: Drop index
    # =========================================================================

    op.drop_index("ix_data_sources_location_id", table_name="data_sources")

    # =========================================================================
    # Step 2: Drop foreign key constraint
    # =========================================================================

    op.drop_constraint("fk_data_sources_location_id", "data_sources", type_="foreignkey")

    # =========================================================================
    # Step 3: Drop column
    # =========================================================================

    op.drop_column("data_sources", "location_id")
