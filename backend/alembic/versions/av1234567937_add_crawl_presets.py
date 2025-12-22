"""Add crawl_presets table for saved filter configurations.

Stores crawl filter configurations that can be reused for deterministic
re-execution. Supports optional cron-based scheduling for automatic
recurring crawls.

Revision ID: av1234567937
Revises: au1234567936
Create Date: 2024-12-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "av1234567937"
down_revision: Union[str, None] = "au1234567936"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Skip if table already exists (idempotent)
    if table_exists("crawl_presets"):
        return

    # Create the preset status enum
    preset_status_enum = sa.Enum(
        "active",
        "archived",
        name="crawl_preset_status_enum",
    )

    # Create crawl_presets table
    op.create_table(
        "crawl_presets",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("filters", JSONB(), nullable=False, server_default="{}"),
        sa.Column("schedule_cron", sa.String(100), nullable=True),
        sa.Column("schedule_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_scheduled_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", preset_status_enum, nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )

    # Create indexes for efficient queries
    op.create_index(
        "ix_crawl_presets_user_id",
        "crawl_presets",
        ["user_id"],
    )
    op.create_index(
        "ix_crawl_presets_user_favorite",
        "crawl_presets",
        ["user_id", "is_favorite"],
    )
    op.create_index(
        "ix_crawl_presets_schedule",
        "crawl_presets",
        ["schedule_enabled", "next_run_at"],
        postgresql_where=sa.text("schedule_enabled = true"),
    )
    op.create_index(
        "ix_crawl_presets_status",
        "crawl_presets",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_crawl_presets_status", table_name="crawl_presets")
    op.drop_index("ix_crawl_presets_schedule", table_name="crawl_presets")
    op.drop_index("ix_crawl_presets_user_favorite", table_name="crawl_presets")
    op.drop_index("ix_crawl_presets_user_id", table_name="crawl_presets")
    op.drop_table("crawl_presets")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS crawl_preset_status_enum")
