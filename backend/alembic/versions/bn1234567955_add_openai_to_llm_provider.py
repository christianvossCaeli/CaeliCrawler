"""Add openai to llm_provider enum for usage tracking.

This migration adds the 'openai' value to the llm_provider enum
to support tracking usage from the standard OpenAI API (not just Azure).

Revision ID: bn1234567955
Revises: bm1234567954
Create Date: 2026-01-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bn1234567955"
down_revision: Union[str, None] = "bm1234567954"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def enum_value_exists(enum_name: str, value: str) -> bool:
    """Check if a value exists in a PostgreSQL enum."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            SELECT 1 FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = :enum_name AND e.enumlabel = :value
        """),
        {"enum_name": enum_name, "value": value},
    )
    return result.scalar() is not None


def upgrade() -> None:
    # Add 'openai' to llm_provider enum if not exists
    if not enum_value_exists("llm_provider", "openai"):
        op.execute("ALTER TYPE llm_provider ADD VALUE IF NOT EXISTS 'openai'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values easily
    # The value will remain in the enum but won't be used
    pass
