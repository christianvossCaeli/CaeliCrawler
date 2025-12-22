"""Add supports_pysis column to entity_types

Revision ID: an1234567930
Revises: am1234567929
Create Date: 2025-01-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ap1234567932'
down_revision: Union[str, None] = 'ao1234567931'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add supports_pysis column with default False
    op.add_column(
        'entity_types',
        sa.Column(
            'supports_pysis',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='Supports PySis data enrichment (German municipalities)'
        )
    )

    # Set supports_pysis=true for territorial_entity (formerly municipality)
    op.execute("""
        UPDATE entity_types
        SET supports_pysis = true
        WHERE slug IN ('territorial_entity', 'municipality')
    """)


def downgrade() -> None:
    op.drop_column('entity_types', 'supports_pysis')
