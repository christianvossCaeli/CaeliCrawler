"""Add export_jobs table for async exports

Revision ID: ab1234567917
Revises: ab1234567916
Create Date: 2025-12-20 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ab1234567917'
down_revision: Union[str, None] = 'ab1234567916'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'export_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('export_config', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('export_format', sa.String(20), nullable=False, server_default='json'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('total_records', sa.Integer(), nullable=True),
        sa.Column('processed_records', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('progress_percent', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('progress_message', sa.String(255), nullable=True),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('download_url', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_export_jobs_celery_task_id', 'export_jobs', ['celery_task_id'], unique=False)
    op.create_index('ix_export_jobs_status', 'export_jobs', ['status'], unique=False)
    op.create_index('ix_export_jobs_user_id', 'export_jobs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_export_jobs_user_id', table_name='export_jobs')
    op.drop_index('ix_export_jobs_status', table_name='export_jobs')
    op.drop_index('ix_export_jobs_celery_task_id', table_name='export_jobs')
    op.drop_table('export_jobs')
