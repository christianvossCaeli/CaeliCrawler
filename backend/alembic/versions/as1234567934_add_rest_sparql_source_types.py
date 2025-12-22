"""Add REST_API and SPARQL_API source types.

Revision ID: as1234567934
Revises: aq1234567933
Create Date: 2024-12-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "as1234567934"
down_revision: Union[str, None] = "aq1234567933"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add REST_API and SPARQL_API to source_type enum."""
    # Add new enum values to source_type
    # PostgreSQL requires ALTER TYPE for enum modification
    op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'REST_API'")
    op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'SPARQL_API'")


def downgrade() -> None:
    """Remove REST_API and SPARQL_API from source_type enum.

    Note: PostgreSQL doesn't support removing enum values directly.
    This downgrade will only work if no data uses these values.
    """
    # Cannot easily remove enum values in PostgreSQL
    # Would need to recreate the type and update all references
    pass
