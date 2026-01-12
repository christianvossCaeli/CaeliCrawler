"""Remove is_active column from categories table.

The is_active field was redundant with schedule_enabled.
Categories are now always considered active; scheduling is controlled via schedule_enabled.

Revision ID: ze1234567919
Revises: zd1234567918
Create Date: 2026-01-05

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ze1234567919"
down_revision: str | None = "zd1234567918"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove is_active column from categories table."""
    op.drop_column("categories", "is_active")


def downgrade() -> None:
    """Add is_active column back to categories table."""
    op.add_column(
        "categories",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
