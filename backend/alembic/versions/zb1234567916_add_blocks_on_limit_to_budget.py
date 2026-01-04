"""Add blocks_on_limit to LLM budget configs.

Revision ID: zb1234567916
Revises: za1234567915
Create Date: 2026-01-04

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "zb1234567916"
down_revision = "za1234567915"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add blocks_on_limit column to llm_budget_configs."""
    op.add_column(
        "llm_budget_configs",
        sa.Column(
            "blocks_on_limit",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="If true, reaching 100% usage blocks LLM access for affected scope",
        ),
    )

    # Set blocks_on_limit to true for USER budgets (existing behavior)
    op.execute(
        """
        UPDATE llm_budget_configs
        SET blocks_on_limit = true
        WHERE budget_type = 'USER'
        """
    )


def downgrade() -> None:
    """Remove blocks_on_limit column."""
    op.drop_column("llm_budget_configs", "blocks_on_limit")
