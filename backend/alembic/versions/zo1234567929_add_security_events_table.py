"""Add security_events table for persistent security audit logging.

This table stores security-relevant events for compliance and incident
response purposes. Events are immutable (append-only).

Revision ID: zo1234567929
Revises: zn1234567928
Create Date: 2026-01-28
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "zo1234567929"
down_revision = "zn1234567928"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("endpoint", sa.String(length=500), nullable=True),
        sa.Column("method", sa.String(length=10), nullable=True),
        sa.Column("request_id", sa.String(length=36), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for efficient querying
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_severity", "security_events", ["severity"])
    op.create_index("ix_security_events_created_at", "security_events", ["created_at"])
    op.create_index("ix_security_events_user_id", "security_events", ["user_id"])
    op.create_index("ix_security_events_request_id", "security_events", ["request_id"])

    # Composite indexes for common queries
    op.create_index(
        "ix_security_events_type_created",
        "security_events",
        ["event_type", "created_at"],
    )
    op.create_index(
        "ix_security_events_severity_created",
        "security_events",
        ["severity", "created_at"],
    )
    op.create_index(
        "ix_security_events_user_created",
        "security_events",
        ["user_id", "created_at"],
    )

    # Partial index for failed events (most often queried for security analysis)
    op.execute(
        """
        CREATE INDEX ix_security_events_failures
        ON security_events (event_type, created_at)
        WHERE success = false
        """
    )


def downgrade() -> None:
    op.drop_index("ix_security_events_failures", table_name="security_events")
    op.drop_index("ix_security_events_user_created", table_name="security_events")
    op.drop_index("ix_security_events_severity_created", table_name="security_events")
    op.drop_index("ix_security_events_type_created", table_name="security_events")
    op.drop_index("ix_security_events_request_id", table_name="security_events")
    op.drop_index("ix_security_events_user_id", table_name="security_events")
    op.drop_index("ix_security_events_created_at", table_name="security_events")
    op.drop_index("ix_security_events_severity", table_name="security_events")
    op.drop_index("ix_security_events_event_type", table_name="security_events")
    op.drop_table("security_events")
