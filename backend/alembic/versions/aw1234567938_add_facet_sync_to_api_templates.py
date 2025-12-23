"""Add facet sync fields to api_templates.

Adds support for scheduled API-to-Facet synchronization:
- facet_mapping: Maps API fields to Facet types
- entity_matching: Configuration for matching API records to entities
- schedule_*: Cron-based scheduling for automated sync

Revision ID: aw1234567938
Revises: av1234567937
Create Date: 2024-12-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "aw1234567938"
down_revision: Union[str, None] = "av1234567937"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the table."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add facet_mapping column
    if not column_exists("api_templates", "facet_mapping"):
        op.add_column(
            "api_templates",
            sa.Column(
                "facet_mapping",
                JSONB,
                nullable=False,
                server_default="{}",
                comment="Mapping from API fields to Facet types",
            ),
        )

    # Add entity_matching column
    if not column_exists("api_templates", "entity_matching"):
        op.add_column(
            "api_templates",
            sa.Column(
                "entity_matching",
                JSONB,
                nullable=False,
                server_default="{}",
                comment="How to match API records to entities",
            ),
        )

    # Add scheduling columns
    if not column_exists("api_templates", "schedule_enabled"):
        op.add_column(
            "api_templates",
            sa.Column(
                "schedule_enabled",
                sa.Boolean,
                nullable=False,
                server_default="false",
                comment="Whether scheduled syncing is enabled",
            ),
        )

    if not column_exists("api_templates", "schedule_cron"):
        op.add_column(
            "api_templates",
            sa.Column(
                "schedule_cron",
                sa.String(100),
                nullable=True,
                comment="Cron expression for scheduled sync",
            ),
        )

    if not column_exists("api_templates", "next_run_at"):
        op.add_column(
            "api_templates",
            sa.Column(
                "next_run_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="Next scheduled sync execution time",
            ),
        )

    if not column_exists("api_templates", "last_sync_at"):
        op.add_column(
            "api_templates",
            sa.Column(
                "last_sync_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="Last successful facet sync timestamp",
            ),
        )

    if not column_exists("api_templates", "last_sync_status"):
        op.add_column(
            "api_templates",
            sa.Column(
                "last_sync_status",
                sa.String(50),
                nullable=True,
                comment="Status of last sync: success, partial, failed",
            ),
        )

    if not column_exists("api_templates", "last_sync_stats"):
        op.add_column(
            "api_templates",
            sa.Column(
                "last_sync_stats",
                JSONB,
                nullable=True,
                comment="Statistics from last sync",
            ),
        )

    # Create index for scheduled templates
    op.create_index(
        "ix_api_templates_schedule_enabled",
        "api_templates",
        ["schedule_enabled"],
        postgresql_where=sa.text("schedule_enabled = true"),
    )

    op.create_index(
        "ix_api_templates_next_run_at",
        "api_templates",
        ["next_run_at"],
        postgresql_where=sa.text("next_run_at IS NOT NULL"),
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_api_templates_next_run_at", table_name="api_templates")
    op.drop_index("ix_api_templates_schedule_enabled", table_name="api_templates")

    # Drop columns
    op.drop_column("api_templates", "last_sync_stats")
    op.drop_column("api_templates", "last_sync_status")
    op.drop_column("api_templates", "last_sync_at")
    op.drop_column("api_templates", "next_run_at")
    op.drop_column("api_templates", "schedule_cron")
    op.drop_column("api_templates", "schedule_enabled")
    op.drop_column("api_templates", "entity_matching")
    op.drop_column("api_templates", "facet_mapping")
