"""Add languages field to categories.

Revision ID: j1234567898
Revises: i1234567897
Create Date: 2024-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "j1234567898"
down_revision: Union[str, None] = "i1234567897"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add languages column to categories
    op.add_column(
        "categories",
        sa.Column(
            "languages",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='["de"]',
            comment="Language codes (ISO 639-1) for this category, e.g. ['de', 'en']",
        ),
    )

    # Set German as default language for existing categories
    op.execute("""
        UPDATE categories
        SET languages = '["de"]'::jsonb
        WHERE languages IS NULL OR languages = '[]'::jsonb
    """)


def downgrade() -> None:
    op.drop_column("categories", "languages")
