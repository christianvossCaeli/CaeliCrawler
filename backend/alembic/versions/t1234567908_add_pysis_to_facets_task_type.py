"""Add PYSIS_TO_FACETS to ai_task_type enum.

This migration adds a new AI task type for analyzing PySis fields
and converting them to FacetValues.

Revision ID: t1234567908
Revises: s1234567907
Create Date: 2024-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "t1234567908"
down_revision: Union[str, None] = "s1234567907"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum value to ai_task_type
    # PostgreSQL allows adding values to enums with ALTER TYPE
    op.execute("ALTER TYPE ai_task_type ADD VALUE IF NOT EXISTS 'PYSIS_TO_FACETS'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums directly
    # The safest approach is to leave the value (it won't cause issues)
    # If removal is absolutely necessary, one would need to:
    # 1. Create a new enum type without the value
    # 2. Update the column to use the new type
    # 3. Drop the old type
    # 4. Rename the new type
    # This is complex and risky, so we skip it for this migration
    pass
