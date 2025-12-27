"""Remove legacy category_id from data_sources

This migration removes the legacy category_id field from data_sources table
and updates the unique constraint to only use base_url.

Categories are now exclusively managed via the N:M data_source_categories table.

Revision ID: bc1234567944
Revises: bb1234567943
Create Date: 2025-12-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'bc1234567944'
# Merge multiple heads into single chain
down_revision = ('bb1234567943', 'az1234567941')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Drop the old unique constraint that includes category_id
    op.drop_constraint('uq_source_category_url', 'data_sources', type_='unique')

    # Step 2: Drop the foreign key constraint on category_id
    op.drop_constraint(
        'fk_data_sources_category_id_categories',
        'data_sources',
        type_='foreignkey'
    )

    # Step 3: Drop the index on category_id
    op.drop_index('ix_data_sources_category_id', table_name='data_sources')

    # Step 4: Drop the category_id column
    op.drop_column('data_sources', 'category_id')

    # Step 5: Create new unique constraint on base_url only
    op.create_unique_constraint('uq_source_base_url', 'data_sources', ['base_url'])


def downgrade() -> None:
    # Step 1: Drop the new unique constraint
    op.drop_constraint('uq_source_base_url', 'data_sources', type_='unique')

    # Step 2: Re-add the category_id column
    op.add_column(
        'data_sources',
        sa.Column(
            'category_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='Legacy primary category - use categories relationship for N:M'
        )
    )

    # Step 3: Re-create the index on category_id
    op.create_index('ix_data_sources_category_id', 'data_sources', ['category_id'])

    # Step 4: Re-add the foreign key constraint
    op.create_foreign_key(
        'fk_data_sources_category_id_categories',
        'data_sources',
        'categories',
        ['category_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Step 5: Re-create the old unique constraint
    op.create_unique_constraint(
        'uq_source_category_url',
        'data_sources',
        ['category_id', 'base_url']
    )
