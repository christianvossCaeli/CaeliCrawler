"""Add user_favorites table for entity bookmarking.

Users can save entities as favorites for quick access.

Revision ID: ag1234567922
Revises: af1234567921
Create Date: 2024-12-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "ag1234567922"
down_revision: Union[str, None] = "af1234567921"
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
    if table_exists("user_favorites"):
        return

    # Create user_favorites table
    op.create_table(
        "user_favorites",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
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
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id", "entity_id", name="uq_user_favorites_user_entity"
        ),
    )

    # Create indexes
    op.create_index(
        "ix_user_favorites_user_id",
        "user_favorites",
        ["user_id"],
    )
    op.create_index(
        "ix_user_favorites_entity_id",
        "user_favorites",
        ["entity_id"],
    )
    op.create_index(
        "ix_user_favorites_user_created",
        "user_favorites",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_favorites_user_created", table_name="user_favorites")
    op.drop_index("ix_user_favorites_entity_id", table_name="user_favorites")
    op.drop_index("ix_user_favorites_user_id", table_name="user_favorites")
    op.drop_table("user_favorites")
