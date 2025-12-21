"""Add ENTITY_DATA_ANALYSIS task type and new AITask fields.

This migration adds:
1. New AI task type ENTITY_DATA_ANALYSIS for analyzing entity data to create facets
2. result_data JSONB field for storing preview/staged results
3. entity_id foreign key for entity-based tasks

Revision ID: ac1234567918
Revises: ab1234567917
Create Date: 2024-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ac1234567918"
down_revision: Union[str, None] = "ab1234567917"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum value to ai_task_type
    op.execute("ALTER TYPE ai_task_type ADD VALUE IF NOT EXISTS 'ENTITY_DATA_ANALYSIS'")

    # Add result_data JSONB column for preview/staged results
    op.add_column(
        "ai_tasks",
        sa.Column(
            "result_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
            comment="Structured result data (e.g., preview of proposed changes)",
        ),
    )

    # Add entity_id foreign key for entity-based tasks
    op.add_column(
        "ai_tasks",
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Entity ID for entity-based tasks",
        ),
    )

    # Create foreign key constraint
    op.create_foreign_key(
        "fk_ai_tasks_entity_id",
        "ai_tasks",
        "entities",
        ["entity_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Create index on entity_id for faster lookups
    op.create_index(
        "ix_ai_tasks_entity_id",
        "ai_tasks",
        ["entity_id"],
    )


def downgrade() -> None:
    # Drop index
    op.drop_index("ix_ai_tasks_entity_id", table_name="ai_tasks")

    # Drop foreign key
    op.drop_constraint("fk_ai_tasks_entity_id", "ai_tasks", type_="foreignkey")

    # Drop columns
    op.drop_column("ai_tasks", "entity_id")
    op.drop_column("ai_tasks", "result_data")

    # Note: PostgreSQL does not support removing enum values
    # The ENTITY_DATA_ANALYSIS value will remain in the enum
