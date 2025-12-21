"""Add tags field to data_sources.

Tags are used for filtering/search purposes in Smart Query.
This is NOT entity coupling - tags help find relevant sources for categories.

Examples: ["nrw", "kommunal", "windkraft", "gemeinde"]

Revision ID: ag1234567923
Revises: ag1234567922
Create Date: 2024-12-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "ag1234567923"
down_revision: Union[str, None] = "ag1234567922"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tags column with empty array as default
    op.add_column(
        "data_sources",
        sa.Column(
            "tags",
            JSONB,
            nullable=False,
            server_default="[]",
            comment="Tags for filtering/categorization (not entity coupling)",
        ),
    )

    # Create GIN index for efficient tag queries
    op.create_index(
        "ix_data_sources_tags",
        "data_sources",
        ["tags"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_data_sources_tags", table_name="data_sources")
    op.drop_column("data_sources", "tags")
