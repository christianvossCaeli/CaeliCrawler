"""Remove status column from crawl_presets table.

The status field (ACTIVE/ARCHIVED) was redundant with schedule_enabled.
Now schedule_enabled is the only activation check for presets.

Revision ID: zd1234567918
Revises: zc1234567917
Create Date: 2026-01-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "zd1234567918"
down_revision: Union[str, None] = "zc1234567917"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Skip if column already removed (idempotent)
    if not column_exists("crawl_presets", "status"):
        return

    # Drop the status column
    op.drop_column("crawl_presets", "status")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS crawl_preset_status_enum")


def downgrade() -> None:
    # Recreate the enum type
    preset_status_enum = sa.Enum(
        "ACTIVE",
        "ARCHIVED",
        name="crawl_preset_status_enum",
    )
    preset_status_enum.create(op.get_bind(), checkfirst=True)

    # Add the status column back with default ACTIVE
    op.add_column(
        "crawl_presets",
        sa.Column(
            "status",
            preset_status_enum,
            nullable=False,
            server_default="ACTIVE",
        ),
    )
