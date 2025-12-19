"""Add municipality, region, bundesland to data_sources

Revision ID: b1234567890
Revises: a9844496194e
Create Date: 2025-01-18 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1234567890'
down_revision: Union[str, None] = 'a9844496194e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add municipality, region, bundesland columns to data_sources
    op.add_column('data_sources', sa.Column('municipality', sa.String(255), nullable=True))
    op.add_column('data_sources', sa.Column('region', sa.String(255), nullable=True))
    op.add_column('data_sources', sa.Column('bundesland', sa.String(100), nullable=True))

    # Create indexes for clustering queries
    op.create_index('ix_data_sources_municipality', 'data_sources', ['municipality'])
    op.create_index('ix_data_sources_region', 'data_sources', ['region'])
    op.create_index('ix_data_sources_bundesland', 'data_sources', ['bundesland'])


def downgrade() -> None:
    op.drop_index('ix_data_sources_bundesland', table_name='data_sources')
    op.drop_index('ix_data_sources_region', table_name='data_sources')
    op.drop_index('ix_data_sources_municipality', table_name='data_sources')
    op.drop_column('data_sources', 'bundesland')
    op.drop_column('data_sources', 'region')
    op.drop_column('data_sources', 'municipality')
