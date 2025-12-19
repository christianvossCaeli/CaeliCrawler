"""Add composite indexes for performance optimization

This migration adds composite indexes for frequently used query patterns
identified during the performance audit. These indexes significantly improve
query performance for:
- Export endpoints
- Smart query execution
- Document listing
- Source listing

Revision ID: p1234567904
Revises: o1234567903
Create Date: 2024-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'p1234567904'
down_revision: Union[str, None] = 'o1234567903'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # Composite indexes for facet_values table (Smart Query optimization)
    # ==========================================================================

    # Index for the most common Smart Query pattern:
    # SELECT * FROM facet_values WHERE entity_id = ? AND facet_type_id = ? AND is_active = true
    op.create_index(
        'ix_facet_values_entity_type_active',
        'facet_values',
        ['entity_id', 'facet_type_id', 'is_active'],
        postgresql_where=sa.text('is_active = true'),
    )

    # Index for time-based facet queries (future events)
    op.create_index(
        'ix_facet_values_entity_date_active',
        'facet_values',
        ['entity_id', 'event_date', 'is_active'],
        postgresql_where=sa.text('is_active = true AND event_date IS NOT NULL'),
    )

    # ==========================================================================
    # Composite indexes for documents table (Document listing optimization)
    # ==========================================================================

    # Index for common document listing pattern:
    # SELECT * FROM documents WHERE source_id = ? ORDER BY discovered_at DESC
    op.create_index(
        'ix_documents_source_discovered',
        'documents',
        ['source_id', 'discovered_at'],
    )

    # Index for document filtering by status:
    # SELECT * FROM documents WHERE source_id = ? AND processing_status = ?
    op.create_index(
        'ix_documents_source_status',
        'documents',
        ['source_id', 'processing_status'],
    )

    # Index for category + status filtering
    op.create_index(
        'ix_documents_category_status_discovered',
        'documents',
        ['category_id', 'processing_status', 'discovered_at'],
    )

    # ==========================================================================
    # Composite indexes for extracted_data table (Export optimization)
    # ==========================================================================

    # Index for export queries with confidence filter:
    # SELECT * FROM extracted_data WHERE category_id = ? AND confidence_score >= ?
    op.create_index(
        'ix_extracted_data_category_confidence',
        'extracted_data',
        ['category_id', 'confidence_score'],
    )

    # Index for document-based export joins
    op.create_index(
        'ix_extracted_data_document_category',
        'extracted_data',
        ['document_id', 'category_id'],
    )

    # ==========================================================================
    # Composite indexes for entities table (Entity listing optimization)
    # ==========================================================================

    # Index for entity listing by type with active filter
    op.create_index(
        'ix_entities_type_active_name',
        'entities',
        ['entity_type_id', 'is_active', 'name_normalized'],
    )

    # ==========================================================================
    # Composite indexes for entity_relations table
    # ==========================================================================

    # Index for relation lookups (used in Smart Query for "works_for" etc.)
    op.create_index(
        'ix_entity_relations_source_type',
        'entity_relations',
        ['source_entity_id', 'relation_type_id'],
    )

    # ==========================================================================
    # Drop redundant single-column indexes (replaced by composite)
    # ==========================================================================

    # Note: Only drop indexes that are fully covered by the new composite indexes
    # We keep single-column indexes that might still be useful for other queries


def downgrade() -> None:
    # Drop all composite indexes created in upgrade

    # Entity relations
    op.drop_index('ix_entity_relations_source_type', table_name='entity_relations')

    # Entities
    op.drop_index('ix_entities_type_active_name', table_name='entities')

    # Extracted data
    op.drop_index('ix_extracted_data_document_category', table_name='extracted_data')
    op.drop_index('ix_extracted_data_category_confidence', table_name='extracted_data')

    # Documents
    op.drop_index('ix_documents_category_status_discovered', table_name='documents')
    op.drop_index('ix_documents_source_status', table_name='documents')
    op.drop_index('ix_documents_source_discovered', table_name='documents')

    # Facet values
    op.drop_index('ix_facet_values_entity_date_active', table_name='facet_values')
    op.drop_index('ix_facet_values_entity_type_active', table_name='facet_values')
