"""Add needs_review field to FacetType for auto-created types.

Revision ID: bk1234567952
Revises: bj1234567951
Create Date: 2024-12-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bk1234567952'
down_revision: Union[str, None] = 'bj1234567951'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add needs_review column to facet_types
    op.add_column(
        'facet_types',
        sa.Column(
            'needs_review',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='Auto-created FacetType that needs admin review',
        )
    )

    # Create index for filtering needs_review FacetTypes
    op.create_index(
        'ix_facet_types_needs_review',
        'facet_types',
        ['needs_review'],
        unique=False,
        postgresql_where=sa.text('needs_review = true'),
    )


def downgrade() -> None:
    op.drop_index('ix_facet_types_needs_review', table_name='facet_types')
    op.drop_column('facet_types', 'needs_review')
