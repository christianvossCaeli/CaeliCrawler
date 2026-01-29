"""Add composite performance indexes for frequent query patterns.

Based on performance audit findings, these composite indexes optimize:
1. CrawlJobs: source_id + status (filter by source, then by status)
2. DataSources: source_type + status (list sources by type and status)
3. Categories: created_by_id + is_public (user's visible categories)
4. Users: is_active + role (admin user queries)

Revision ID: zp1234567930
Revises: zo1234567929
Create Date: 2026-01-28
"""

from alembic import op

revision = "zp1234567930"
down_revision = "zo1234567929"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CrawlJobs: Common query pattern - filter by source, then filter/sort by status
    # Example: SELECT * FROM crawl_jobs WHERE source_id = ? AND status = ?
    op.create_index(
        "ix_crawl_jobs_source_status",
        "crawl_jobs",
        ["source_id", "status"],
    )

    # DataSources: Filter active sources by type (admin source list)
    # Example: SELECT * FROM data_sources WHERE source_type = ? AND status = ?
    op.create_index(
        "ix_data_sources_type_status",
        "data_sources",
        ["source_type", "status"],
    )

    # Categories: User's visible categories (own + public)
    # Example: SELECT * FROM categories WHERE created_by_id = ? OR is_public = true
    op.create_index(
        "ix_categories_creator_public",
        "categories",
        ["created_by_id", "is_public"],
    )

    # Users: Admin user queries (list active users by role)
    # Example: SELECT * FROM users WHERE is_active = true AND role = ?
    op.create_index(
        "ix_users_active_role",
        "users",
        ["is_active", "role"],
    )

    # Users: Timestamp for user listing/reporting with pagination
    op.create_index(
        "ix_users_created_at",
        "users",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_index("ix_users_active_role", table_name="users")
    op.drop_index("ix_categories_creator_public", table_name="categories")
    op.drop_index("ix_data_sources_type_status", table_name="data_sources")
    op.drop_index("ix_crawl_jobs_source_status", table_name="crawl_jobs")
