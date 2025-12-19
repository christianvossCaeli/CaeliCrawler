"""Add source column to pysis_field_history table.

This migration adds the 'source' column which tracks where the value came from
(AI, MANUAL, or PYSIS).

Revision ID: u1234567909
Revises: t1234567908
Create Date: 2024-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "u1234567909"
down_revision: Union[str, None] = "t1234567908"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if column exists before adding (idempotent migration)
    conn = op.get_bind()

    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'pysis_field_history' AND column_name = 'source'
    """))
    source_exists = result.fetchone() is not None

    if not source_exists:
        # Add source column using the existing pysis_value_source enum
        op.add_column(
            "pysis_field_history",
            sa.Column(
                "source",
                sa.Enum("AI", "MANUAL", "PYSIS", name="pysis_value_source", create_type=False),
                nullable=False,
                server_default="MANUAL",
                comment="Source of this value: AI, MANUAL, or PYSIS",
            ),
        )

        # Remove the server default after populating existing rows
        op.alter_column(
            "pysis_field_history",
            "source",
            server_default=None,
        )


def downgrade() -> None:
    op.drop_column("pysis_field_history", "source")
