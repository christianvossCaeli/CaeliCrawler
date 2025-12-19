"""Add entity_id and entity_name to pysis_processes table.

This migration adds entity support to PySis processes:
- entity_id: FK to entities table for proper entity linking
- entity_name: String field for display/legacy compatibility

The location_id and location_name columns are kept for backwards compatibility
but entity_id/entity_name should be used going forward.

Revision ID: s1234567907
Revises: r1234567906
Create Date: 2024-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "s1234567907"
down_revision: Union[str, None] = "r1234567906"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if columns exist before adding (idempotent migration)
    conn = op.get_bind()

    # Check entity_id column
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'pysis_processes' AND column_name = 'entity_id'
    """))
    entity_id_exists = result.fetchone() is not None

    # Check entity_name column
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'pysis_processes' AND column_name = 'entity_name'
    """))
    entity_name_exists = result.fetchone() is not None

    if not entity_id_exists:
        # Add entity_id column
        op.add_column(
            "pysis_processes",
            sa.Column(
                "entity_id",
                UUID(as_uuid=True),
                nullable=True,
                comment="FK to entity (municipality/organization)",
            ),
        )

        # Add foreign key constraint
        op.create_foreign_key(
            "fk_pysis_processes_entity_id",
            "pysis_processes",
            "entities",
            ["entity_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # Create index for efficient lookups
        op.create_index(
            "ix_pysis_processes_entity_id",
            "pysis_processes",
            ["entity_id"],
        )

    if not entity_name_exists:
        # Add entity_name column
        op.add_column(
            "pysis_processes",
            sa.Column(
                "entity_name",
                sa.String(255),
                nullable=True,
                comment="Entity name for display and string matching",
            ),
        )

        # Create index for efficient lookups by name
        op.create_index(
            "ix_pysis_processes_entity_name",
            "pysis_processes",
            ["entity_name"],
        )

        # Migrate data from location_name to entity_name if location_name exists
        result = conn.execute(sa.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'pysis_processes' AND column_name = 'location_name'
        """))
        location_name_exists = result.fetchone() is not None

        if location_name_exists:
            op.execute("""
                UPDATE pysis_processes
                SET entity_name = location_name
                WHERE entity_name IS NULL AND location_name IS NOT NULL
            """)

    # Update unique constraint if old one exists
    # First check if old constraint exists
    result = conn.execute(sa.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'pysis_processes'
        AND constraint_name = 'uq_municipality_pysis_process'
    """))
    old_constraint_exists = result.fetchone() is not None

    if old_constraint_exists:
        op.drop_constraint("uq_municipality_pysis_process", "pysis_processes", type_="unique")

    # Check if new constraint exists before creating
    result = conn.execute(sa.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'pysis_processes'
        AND constraint_name = 'uq_entity_pysis_process'
    """))
    new_constraint_exists = result.fetchone() is not None

    if not new_constraint_exists:
        op.create_unique_constraint(
            "uq_entity_pysis_process",
            "pysis_processes",
            ["entity_id", "pysis_process_id"],
        )


def downgrade() -> None:
    # Drop new constraint
    op.drop_constraint("uq_entity_pysis_process", "pysis_processes", type_="unique")

    # Drop indexes
    op.drop_index("ix_pysis_processes_entity_name", table_name="pysis_processes")
    op.drop_index("ix_pysis_processes_entity_id", table_name="pysis_processes")

    # Drop foreign key
    op.drop_constraint("fk_pysis_processes_entity_id", "pysis_processes", type_="foreignkey")

    # Drop columns
    op.drop_column("pysis_processes", "entity_name")
    op.drop_column("pysis_processes", "entity_id")

    # Recreate old constraint if location_name column exists
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'pysis_processes' AND column_name = 'location_name'
    """))
    if result.fetchone() is not None:
        op.create_unique_constraint(
            "uq_municipality_pysis_process",
            "pysis_processes",
            ["location_name", "pysis_process_id"],
        )
