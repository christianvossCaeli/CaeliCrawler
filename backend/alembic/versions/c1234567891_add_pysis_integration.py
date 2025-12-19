"""Add PySis integration tables

Revision ID: c1234567891
Revises: b1234567890
Create Date: 2025-12-18 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c1234567891'
down_revision: Union[str, None] = 'b1234567890'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE pysis_sync_status AS ENUM ('SYNCED', 'PENDING', 'ERROR', 'NEVER')")
    op.execute("CREATE TYPE pysis_value_source AS ENUM ('AI', 'MANUAL', 'PYSIS')")

    # Create pysis_field_templates table
    op.create_table(
        'pysis_field_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('fields', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create pysis_processes table
    op.create_table(
        'pysis_processes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('municipality', sa.String(255), nullable=False, index=True),
        sa.Column('pysis_process_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('pysis_field_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_status', postgresql.ENUM('SYNCED', 'PENDING', 'ERROR', 'NEVER',
                                                  name='pysis_sync_status', create_type=False),
                  nullable=False, server_default='NEVER'),
        sa.Column('sync_error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('municipality', 'pysis_process_id', name='uq_municipality_pysis_process'),
    )

    # Create pysis_process_fields table
    op.create_table(
        'pysis_process_fields',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('process_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('pysis_processes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('internal_name', sa.String(255), nullable=False),
        sa.Column('pysis_field_name', sa.String(255), nullable=False),
        sa.Column('field_type', sa.String(50), nullable=False, server_default='text'),
        sa.Column('ai_extraction_enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('ai_extraction_prompt', sa.Text, nullable=True),
        sa.Column('current_value', sa.Text, nullable=True),
        sa.Column('ai_extracted_value', sa.Text, nullable=True),
        sa.Column('manual_value', sa.Text, nullable=True),
        sa.Column('value_source', postgresql.ENUM('AI', 'MANUAL', 'PYSIS',
                                                   name='pysis_value_source', create_type=False),
                  nullable=False, server_default='AI'),
        sa.Column('pysis_value', sa.Text, nullable=True),
        sa.Column('last_pushed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_pulled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('needs_push', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('confidence_score', sa.Float, nullable=True),
        sa.Column('extraction_document_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('process_id', 'pysis_field_name', name='uq_process_pysis_field'),
    )


def downgrade() -> None:
    op.drop_table('pysis_process_fields')
    op.drop_table('pysis_processes')
    op.drop_table('pysis_field_templates')
    op.execute('DROP TYPE pysis_value_source')
    op.execute('DROP TYPE pysis_sync_status')
