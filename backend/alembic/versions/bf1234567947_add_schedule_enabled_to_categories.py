"""Add schedule_enabled column to categories table.

This column must be explicitly set to True to enable automatic
scheduled crawling based on the category's schedule_cron.

Also merges existing heads into single lineage.

Revision ID: bf1234567947
Revises: bd1234567945, be1234567946
Create Date: 2025-12-30
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "bf1234567947"
down_revision = ("bd1234567945", "be1234567946")
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
    # Skip if column already exists (idempotent)
    if column_exists("categories", "schedule_enabled"):
        return

    # Add schedule_enabled column with default False
    # This ensures no automatic crawls happen until explicitly enabled
    op.add_column(
        "categories",
        sa.Column(
            "schedule_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="If true, automatic crawls are enabled based on schedule_cron",
        ),
    )


def downgrade() -> None:
    op.drop_column("categories", "schedule_enabled")
