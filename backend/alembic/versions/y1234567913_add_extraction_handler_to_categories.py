"""Add extraction_handler to categories.

This migration adds the extraction_handler field to the categories table,
which determines how AI extractions are processed:
- 'default': Uses entity_facet_service for Pain Points, Positive Signals, etc.
- 'event': Uses event_extraction_service for Event entities and attendee relations.

Revision ID: y1234567913
Revises: x1234567912
Create Date: 2024-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "y1234567913"
down_revision: Union[str, None] = "x1234567912"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table_name AND column_name = :column_name
            )
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar()


def upgrade() -> None:
    """Add extraction_handler column to categories table."""
    if not column_exists("categories", "extraction_handler"):
        op.add_column(
            "categories",
            sa.Column(
                "extraction_handler",
                sa.String(50),
                nullable=False,
                server_default="default",
                comment="Handler for processing extractions: 'default' or 'event'",
            ),
        )


def downgrade() -> None:
    """Remove extraction_handler column from categories table."""
    if column_exists("categories", "extraction_handler"):
        op.drop_column("categories", "extraction_handler")
