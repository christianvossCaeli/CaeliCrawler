"""Add AUTO trigger type and auto_trigger_entity_types to custom_summaries.

This enables automatic summary updates when crawls complete for matching entity types.
The AUTO trigger type allows summaries to be triggered based on the entity types
they reference, without manual configuration.

Revision ID: zf1234567920
Revises: ze1234567919
Create Date: 2026-01-05

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "zf1234567920"
down_revision: str | None = "ze1234567919"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add AUTO trigger type and related fields."""
    # 1. Add AUTO value to the summary_trigger_type_enum
    op.execute("ALTER TYPE summary_trigger_type_enum ADD VALUE IF NOT EXISTS 'AUTO'")

    # 2. Add auto_trigger_entity_types JSONB column
    op.add_column(
        "custom_summaries",
        sa.Column(
            "auto_trigger_entity_types",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
            comment="Entity type slugs that automatically trigger this summary",
        ),
    )

    # 3. Add last_auto_trigger_reason text column
    op.add_column(
        "custom_summaries",
        sa.Column(
            "last_auto_trigger_reason",
            sa.Text(),
            nullable=True,
            comment="Last reason why AUTO trigger was activated",
        ),
    )

    # 4. Create GIN index for fast entity type matching
    op.execute("""
        CREATE INDEX ix_custom_summaries_auto_entity_types
        ON custom_summaries USING GIN (auto_trigger_entity_types)
    """)


def downgrade() -> None:
    """Remove AUTO trigger type and related fields."""
    # Drop the GIN index
    op.drop_index("ix_custom_summaries_auto_entity_types", table_name="custom_summaries")

    # Drop columns
    op.drop_column("custom_summaries", "last_auto_trigger_reason")
    op.drop_column("custom_summaries", "auto_trigger_entity_types")

    # Note: Cannot remove enum value in PostgreSQL without recreating the type
    # Leaving AUTO value in place (safe to keep)
