"""Add performance indexes for sources page.

Adds indexes for columns that are sorted/filtered but lack indexes:
- data_sources.last_crawl (default sort order in sources list)
- crawl_jobs.completed_at (ORDER BY for last completed job query)

Revision ID: zm1234567927
Revises: zl1234567926
Create Date: 2026-01-28
"""

from alembic import op

revision = "zm1234567927"
down_revision = "zl1234567926"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # DataSources: last_crawl is the default sort column (ORDER BY last_crawl DESC)
    op.create_index(
        "ix_data_sources_last_crawl",
        "data_sources",
        ["last_crawl"],
    )

    # CrawlJobs: completed_at for "last completed job" query (ORDER BY + LIMIT 1)
    op.create_index(
        "ix_crawl_jobs_completed_at",
        "crawl_jobs",
        ["completed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_crawl_jobs_completed_at", table_name="crawl_jobs")
    op.drop_index("ix_data_sources_last_crawl", table_name="data_sources")
