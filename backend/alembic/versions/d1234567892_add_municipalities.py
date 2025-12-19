"""Add municipalities table and FK relationships

Revision ID: d1234567892
Revises: c1234567891
Create Date: 2025-12-18 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd1234567892'
down_revision: Union[str, None] = 'c1234567891'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Note: municipalities table already exists (created manually or in previous session)
    # Only add the FK columns to data_sources and pysis_processes

    # Add municipality_id FK to data_sources
    op.add_column(
        'data_sources',
        sa.Column('municipality_id', postgresql.UUID(as_uuid=True), nullable=True, index=True,
                  comment='FK to pre-defined municipality')
    )
    op.create_foreign_key(
        'fk_data_sources_municipality_id',
        'data_sources', 'municipalities',
        ['municipality_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add municipality_id FK to pysis_processes
    op.add_column(
        'pysis_processes',
        sa.Column('municipality_id', postgresql.UUID(as_uuid=True), nullable=True, index=True,
                  comment='FK to municipality')
    )
    op.create_foreign_key(
        'fk_pysis_processes_municipality_id',
        'pysis_processes', 'municipalities',
        ['municipality_id'], ['id'],
        ondelete='CASCADE'
    )

    # Make pysis_processes.municipality nullable (was required before)
    op.alter_column('pysis_processes', 'municipality',
                    existing_type=sa.String(255),
                    nullable=True)


def downgrade() -> None:
    # Make pysis_processes.municipality required again
    op.alter_column('pysis_processes', 'municipality',
                    existing_type=sa.String(255),
                    nullable=False)

    # Remove FK from pysis_processes
    op.drop_constraint('fk_pysis_processes_municipality_id', 'pysis_processes', type_='foreignkey')
    op.drop_column('pysis_processes', 'municipality_id')

    # Remove FK from data_sources
    op.drop_constraint('fk_data_sources_municipality_id', 'data_sources', type_='foreignkey')
    op.drop_column('data_sources', 'municipality_id')

    # Note: not dropping municipalities table as it may have been created manually
    # op.drop_table('municipalities')
