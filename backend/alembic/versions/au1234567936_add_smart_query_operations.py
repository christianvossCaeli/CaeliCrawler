"""Add smart_query_operations table for history and favorites.

Users can save Smart Query operations as favorites for quick re-execution.
History tracks all executed write commands.

Revision ID: au1234567936
Revises: at1234567935
Create Date: 2024-12-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "au1234567936"
down_revision: Union[str, None] = "at1234567935"
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
    if table_exists("smart_query_operations"):
        return

    # Create the operation type enum
    operation_type_enum = sa.Enum(
        "start_crawl",
        "create_category_setup",
        "create_entity",
        "create_entity_type",
        "create_facet",
        "create_relation",
        "fetch_and_create_from_api",
        "discover_sources",
        "combined",
        "other",
        name="smart_query_operation_type",
    )

    # Create smart_query_operations table
    op.create_table(
        "smart_query_operations",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("command_text", sa.Text(), nullable=False),
        sa.Column("command_hash", sa.String(32), nullable=False),
        sa.Column("operation_type", operation_type_enum, nullable=False, server_default="other"),
        sa.Column("interpretation", JSONB(), nullable=False, server_default="{}"),
        sa.Column("result_summary", JSONB(), nullable=False, server_default="{}"),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("execution_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("was_successful", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_executed_at",
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

    # Create indexes
    op.create_index(
        "ix_smart_query_operations_user_id",
        "smart_query_operations",
        ["user_id"],
    )
    op.create_index(
        "ix_smart_query_operations_user_favorite",
        "smart_query_operations",
        ["user_id", "is_favorite"],
    )
    op.create_index(
        "ix_smart_query_operations_user_created",
        "smart_query_operations",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_smart_query_operations_operation_type",
        "smart_query_operations",
        ["operation_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_smart_query_operations_operation_type", table_name="smart_query_operations")
    op.drop_index("ix_smart_query_operations_user_created", table_name="smart_query_operations")
    op.drop_index("ix_smart_query_operations_user_favorite", table_name="smart_query_operations")
    op.drop_index("ix_smart_query_operations_user_id", table_name="smart_query_operations")
    op.drop_table("smart_query_operations")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS smart_query_operation_type")
