"""Add user_sessions table for refresh tokens and session management.

Revision ID: q1234567905
Revises: p1234567904
Create Date: 2025-01-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "q1234567905"
down_revision = "p1234567904"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create device_type enum
    device_type_enum = postgresql.ENUM(
        "DESKTOP", "MOBILE", "TABLET", "API", "UNKNOWN",
        name="device_type",
        create_type=False,
    )
    device_type_enum.create(op.get_bind(), checkfirst=True)

    # Create user_sessions table
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refresh_token_hash", sa.String(255), nullable=False),
        sa.Column("token_family", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(255), nullable=True),
        sa.Column(
            "device_type",
            postgresql.ENUM(
                "DESKTOP", "MOBILE", "TABLET", "API", "UNKNOWN",
                name="device_type",
                create_type=False,
            ),
            nullable=False,
            default="UNKNOWN",
        ),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )

    # Create indexes
    op.create_index(
        "ix_user_sessions_user_id",
        "user_sessions",
        ["user_id"],
    )
    op.create_index(
        "ix_user_sessions_refresh_token_hash",
        "user_sessions",
        ["refresh_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_user_sessions_user_active",
        "user_sessions",
        ["user_id", "is_active"],
    )
    op.create_index(
        "ix_user_sessions_expires",
        "user_sessions",
        ["expires_at"],
    )

    # Add new audit actions to enum (if they don't exist)
    # Note: PostgreSQL enums can't be easily modified, so we handle this gracefully
    try:
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'PASSWORD_CHANGE'")
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'PASSWORD_RESET'")
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'SESSION_REVOKE'")
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'SESSION_REVOKE_ALL'")
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'TOKEN_REFRESH'")
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'CRAWLER_START'")
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'CRAWLER_STOP'")
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'USER_CREATE'")
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'USER_UPDATE'")
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'USER_DELETE'")
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'ROLE_CHANGE'")
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'SECURITY_ALERT'")
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'RATE_LIMIT_EXCEEDED'")
    except Exception:
        # Ignore errors if values already exist
        pass


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_user_sessions_expires", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_active", table_name="user_sessions")
    op.drop_index("ix_user_sessions_refresh_token_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")

    # Drop table
    op.drop_table("user_sessions")

    # Drop enum (optional, may fail if other tables use it)
    try:
        op.execute("DROP TYPE IF EXISTS device_type")
    except Exception:
        pass
