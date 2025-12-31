"""Add page-based analysis tracking fields to documents.

Enables efficient document processing by tracking which pages
have been analyzed, allowing incremental analysis of only
relevant pages instead of the entire document.

Revision ID: bj1234567951
Revises: bi1234567950
Create Date: 2025-12-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "bj1234567951"
down_revision = "bi1234567950"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add page_analysis_status column
    if not column_exists("documents", "page_analysis_status"):
        op.add_column(
            "documents",
            sa.Column(
                "page_analysis_status",
                sa.String(20),
                nullable=True,
                comment="Status: pending, partial, complete, needs_review",
            ),
        )

    # Add relevant_pages column (pages with keyword matches, sorted by score)
    if not column_exists("documents", "relevant_pages"):
        op.add_column(
            "documents",
            sa.Column(
                "relevant_pages",
                JSONB,
                nullable=True,
                comment="List of page numbers with keyword matches",
            ),
        )

    # Add analyzed_pages column (pages already sent to LLM)
    if not column_exists("documents", "analyzed_pages"):
        op.add_column(
            "documents",
            sa.Column(
                "analyzed_pages",
                JSONB,
                nullable=True,
                comment="List of page numbers already analyzed by LLM",
            ),
        )

    # Add total_relevant_pages column (for UI hint)
    if not column_exists("documents", "total_relevant_pages"):
        op.add_column(
            "documents",
            sa.Column(
                "total_relevant_pages",
                sa.Integer,
                nullable=True,
                comment="Total count of pages with keyword matches",
            ),
        )

    # Add page_analysis_note column (user-facing message)
    if not column_exists("documents", "page_analysis_note"):
        op.add_column(
            "documents",
            sa.Column(
                "page_analysis_note",
                sa.Text,
                nullable=True,
                comment="User-facing note about page analysis status",
            ),
        )

    # Add NEEDS_REVIEW to processing_status enum if not exists
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumlabel = 'NEEDS_REVIEW'
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'processing_status')
            ) THEN
                ALTER TYPE processing_status ADD VALUE 'NEEDS_REVIEW';
            END IF;
        END$$;
    """)


def downgrade() -> None:
    op.drop_column("documents", "page_analysis_note")
    op.drop_column("documents", "total_relevant_pages")
    op.drop_column("documents", "analyzed_pages")
    op.drop_column("documents", "relevant_pages")
    op.drop_column("documents", "page_analysis_status")
    # Note: Cannot remove enum value in PostgreSQL, would need to recreate type
