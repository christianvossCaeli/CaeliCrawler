"""Add missing performance indexes.

Revision ID: bh1234567949
Revises: bg1234567948
Create Date: 2024-12-30

Adds indexes for columns that are frequently filtered, sorted, or grouped but lack indexes:
- documents.processing_status (heavily filtered in document lists)
- data_sources.source_type (grouped in stats queries)
- data_sources.created_at (sorted in lists)
- crawl_jobs.created_at (sorted in job lists)
- crawl_jobs.started_at (filtered for "today" queries)
- extracted_data.extraction_type (filtered in extractions)
"""

from alembic import op

revision = "bh1234567949"
down_revision = "bg1234567948"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Documents: processing_status is heavily filtered but only has composite indexes
    op.create_index(
        "ix_documents_processing_status",
        "documents",
        ["processing_status"],
    )

    # DataSources: source_type is grouped/filtered in stats queries
    op.create_index(
        "ix_data_sources_source_type",
        "data_sources",
        ["source_type"],
    )

    # DataSources: created_at for sorting
    op.create_index(
        "ix_data_sources_created_at",
        "data_sources",
        ["created_at"],
    )

    # CrawlJobs: scheduled_at for sorting and "today" filters
    op.create_index(
        "ix_crawl_jobs_scheduled_at",
        "crawl_jobs",
        ["scheduled_at"],
    )

    # CrawlJobs: started_at for "runs today" queries
    op.create_index(
        "ix_crawl_jobs_started_at",
        "crawl_jobs",
        ["started_at"],
    )

    # ExtractedData: extraction_type is filtered but no index
    op.create_index(
        "ix_extracted_data_extraction_type",
        "extracted_data",
        ["extraction_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_extracted_data_extraction_type", table_name="extracted_data")
    op.drop_index("ix_crawl_jobs_started_at", table_name="crawl_jobs")
    op.drop_index("ix_crawl_jobs_scheduled_at", table_name="crawl_jobs")
    op.drop_index("ix_data_sources_created_at", table_name="data_sources")
    op.drop_index("ix_data_sources_source_type", table_name="data_sources")
    op.drop_index("ix_documents_processing_status", table_name="documents")
