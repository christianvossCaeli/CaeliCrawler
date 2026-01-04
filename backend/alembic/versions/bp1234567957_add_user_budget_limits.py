"""Add user budget type and limit increase requests.

This migration adds:
- 'user' value to the budget_type enum for per-user LLM budgets
- limit_increase_request_status enum
- llm_budget_limit_requests table for tracking user limit increase requests

Revision ID: bp1234567957
Revises: bo1234567956
Create Date: 2026-01-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "bp1234567957"
down_revision: Union[str, None] = "bo1234567956"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'user' to budget_type enum
    # Note: PostgreSQL requires special handling for adding enum values
    op.execute("ALTER TYPE budget_type ADD VALUE IF NOT EXISTS 'user'")

    # Create limit_increase_request_status enum
    limit_request_status = postgresql.ENUM(
        "pending",
        "approved",
        "denied",
        name="limit_increase_request_status",
        create_type=False,
    )
    limit_request_status.create(op.get_bind(), checkfirst=True)

    # Create llm_budget_limit_requests table
    op.create_table(
        "llm_budget_limit_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "budget_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("llm_budget_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_limit_cents",
            sa.Integer,
            nullable=False,
            comment="Requested new monthly limit in USD cents",
        ),
        sa.Column(
            "current_limit_cents",
            sa.Integer,
            nullable=False,
            comment="Limit at time of request in USD cents",
        ),
        sa.Column(
            "reason",
            sa.Text,
            nullable=False,
            comment="User's reason for requesting increase",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "approved",
                "denied",
                name="limit_increase_request_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "admin_notes",
            sa.Text,
            nullable=True,
            comment="Admin notes on approval/denial",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create index for budget_id lookups
    op.create_index(
        "ix_llm_budget_limit_requests_budget_id",
        "llm_budget_limit_requests",
        ["budget_id"],
    )


def downgrade() -> None:
    # Drop table
    op.drop_index("ix_llm_budget_limit_requests_budget_id")
    op.drop_table("llm_budget_limit_requests")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS limit_increase_request_status")

    # Note: Cannot remove enum value from budget_type in PostgreSQL
    # The 'user' value will remain but be unused
