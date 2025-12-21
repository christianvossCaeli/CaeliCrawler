"""Add device_tokens table for push notification registration.

Stores device tokens for iOS (APNS), Android (FCM), and Web push notifications.
Each user can have multiple devices registered.

Revision ID: ai1234567925
Revises: ah1234567924
Create Date: 2024-12-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "ai1234567925"
down_revision: Union[str, None] = "ah1234567924"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def enum_exists(enum_name: str) -> bool:
    """Check if an enum type exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": enum_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    # Skip if table already exists (idempotent)
    if table_exists("device_tokens"):
        return

    # Create device_platform enum if it doesn't exist
    if not enum_exists("device_platform"):
        device_platform = sa.Enum("ios", "android", "web", name="device_platform")
        device_platform.create(op.get_bind(), checkfirst=True)

    # Create device_tokens table
    op.create_table(
        "device_tokens",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(500), nullable=False),
        sa.Column(
            "platform",
            sa.Enum("ios", "android", "web", name="device_platform", create_type=False),
            nullable=False,
        ),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("app_version", sa.String(50), nullable=True),
        sa.Column("os_version", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("token", name="uq_device_tokens_token"),
    )

    # Create indexes
    op.create_index(
        "ix_device_tokens_user_id",
        "device_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_device_tokens_token",
        "device_tokens",
        ["token"],
    )
    op.create_index(
        "ix_device_tokens_user_active",
        "device_tokens",
        ["user_id", "is_active"],
    )
    op.create_index(
        "ix_device_tokens_platform",
        "device_tokens",
        ["platform"],
    )


def downgrade() -> None:
    op.drop_index("ix_device_tokens_platform", table_name="device_tokens")
    op.drop_index("ix_device_tokens_user_active", table_name="device_tokens")
    op.drop_index("ix_device_tokens_token", table_name="device_tokens")
    op.drop_index("ix_device_tokens_user_id", table_name="device_tokens")
    op.drop_table("device_tokens")

    # Drop enum type
    sa.Enum(name="device_platform").drop(op.get_bind(), checkfirst=True)
