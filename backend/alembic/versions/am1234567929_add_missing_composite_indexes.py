"""Add missing composite indexes for performance

Revision ID: am1234567929
Revises: al1234567928
Create Date: 2025-12-21

This migration adds composite indexes identified during the code audit
to improve query performance for common access patterns.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'am1234567929'
down_revision = 'al1234567928'
branch_labels = None
depends_on = None


def upgrade():
    # Notification indexes for user filtering
    op.create_index(
        'ix_notifications_user_status',
        'notifications',
        ['user_id', 'status'],
        unique=False,
        if_not_exists=True
    )
    op.create_index(
        'ix_notifications_event_status',
        'notifications',
        ['event_type', 'status'],
        unique=False,
        if_not_exists=True
    )

    # Document indexes for processing status queries
    op.create_index(
        'ix_documents_status_discovered',
        'documents',
        ['processing_status', 'discovered_at'],
        unique=False,
        if_not_exists=True
    )

    # FacetValue indexes for confidence-based queries
    op.create_index(
        'ix_facet_values_entity_confidence',
        'facet_values',
        ['entity_id', 'confidence_score'],
        unique=False,
        if_not_exists=True
    )

    # ExportJob composite indexes (from model update)
    op.create_index(
        'ix_export_jobs_user_status',
        'export_jobs',
        ['user_id', 'status'],
        unique=False,
        if_not_exists=True
    )
    op.create_index(
        'ix_export_jobs_created_status',
        'export_jobs',
        ['created_at', 'status'],
        unique=False,
        if_not_exists=True
    )

    # CrawlJob indexes for monitoring queries
    op.create_index(
        'ix_crawl_jobs_status_started',
        'crawl_jobs',
        ['status', 'started_at'],
        unique=False,
        if_not_exists=True
    )


def downgrade():
    op.drop_index('ix_crawl_jobs_status_started', table_name='crawl_jobs')
    op.drop_index('ix_export_jobs_created_status', table_name='export_jobs')
    op.drop_index('ix_export_jobs_user_status', table_name='export_jobs')
    op.drop_index('ix_facet_values_entity_confidence', table_name='facet_values')
    op.drop_index('ix_documents_status_discovered', table_name='documents')
    op.drop_index('ix_notifications_event_status', table_name='notifications')
    op.drop_index('ix_notifications_user_status', table_name='notifications')
