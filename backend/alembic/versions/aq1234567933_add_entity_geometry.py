"""Add geometry column to entities for GeoJSON boundaries/regions

Revision ID: aq1234567933
Revises: ap1234567932
Create Date: 2025-01-06 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'aq1234567933'
down_revision: Union[str, None] = 'ap1234567932'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add geometry column for GeoJSON shapes (Polygon, MultiPolygon, LineString, etc.)
    op.add_column(
        'entities',
        sa.Column(
            'geometry',
            JSONB,
            nullable=True,
            comment='GeoJSON geometry for boundaries, regions, routes etc.'
        )
    )


def downgrade() -> None:
    op.drop_column('entities', 'geometry')
