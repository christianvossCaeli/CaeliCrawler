"""Add category_entity_types junction table for multi-entitytype support.

Revision ID: ah1234567924
Revises: ag1234567923
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ah1234567924'
down_revision: Union[str, None] = 'ag1234567923'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create category_entity_types junction table
    op.create_table(
        'category_entity_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('extraction_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('extraction_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('relation_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_type_id'], ['entity_types.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category_id', 'entity_type_id', name='uq_category_entity_type'),
    )

    # Add indexes for efficient queries
    op.create_index('ix_category_entity_types_category_id', 'category_entity_types', ['category_id'])
    op.create_index('ix_category_entity_types_entity_type_id', 'category_entity_types', ['entity_type_id'])
    op.create_index('ix_category_entity_types_is_primary', 'category_entity_types', ['category_id', 'is_primary'])


def downgrade() -> None:
    op.drop_index('ix_category_entity_types_is_primary', table_name='category_entity_types')
    op.drop_index('ix_category_entity_types_entity_type_id', table_name='category_entity_types')
    op.drop_index('ix_category_entity_types_category_id', table_name='category_entity_types')
    op.drop_table('category_entity_types')
