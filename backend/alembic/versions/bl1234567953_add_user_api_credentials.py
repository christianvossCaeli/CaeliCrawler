"""Add user API credentials system.

This migration adds:
1. api_credential_type enum for credential types (serpapi, serper, azure_openai, anthropic)
2. user_api_credentials table for storing encrypted API credentials per user
3. user_id column to crawl_jobs for tracking which user initiated the crawl
4. schedule_owner_id column to categories for scheduled crawl API key resolution

Revision ID: bl1234567953
Revises: bk1234567952
Create Date: 2026-01-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "bl1234567953"
down_revision: Union[str, None] = "bk1234567952"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def enum_exists(enum_name: str) -> bool:
    """Check if a PostgreSQL enum type exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :enum_name"),
        {"enum_name": enum_name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    # 1. Create api_credential_type enum
    if not enum_exists("api_credential_type"):
        api_credential_type = postgresql.ENUM(
            "serpapi",
            "serper",
            "azure_openai",
            "anthropic",
            name="api_credential_type",
        )
        api_credential_type.create(op.get_bind())

    # 2. Create user_api_credentials table
    if not table_exists("user_api_credentials"):
        op.create_table(
            "user_api_credentials",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "credential_type",
                postgresql.ENUM(
                    "serpapi",
                    "serper",
                    "azure_openai",
                    "anthropic",
                    name="api_credential_type",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "encrypted_data",
                sa.Text(),
                nullable=False,
                comment="Fernet-encrypted JSON containing API credentials",
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "last_used_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "last_error",
                sa.Text(),
                nullable=True,
                comment="Last error message for debugging",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
        )

        # Add unique constraint: one credential type per user
        op.create_unique_constraint(
            "uq_user_credential_type",
            "user_api_credentials",
            ["user_id", "credential_type"],
        )

        # Add index on user_id (already created via ForeignKey, but explicit for clarity)
        op.create_index(
            "ix_user_api_credentials_user_id",
            "user_api_credentials",
            ["user_id"],
        )

    # 3. Add user_id to crawl_jobs
    if not column_exists("crawl_jobs", "user_id"):
        op.add_column(
            "crawl_jobs",
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
                comment="User who initiated this crawl (for API key resolution)",
            ),
        )
        op.create_index(
            "ix_crawl_jobs_user_id",
            "crawl_jobs",
            ["user_id"],
        )

    # 4. Add schedule_owner_id to categories
    if not column_exists("categories", "schedule_owner_id"):
        op.add_column(
            "categories",
            sa.Column(
                "schedule_owner_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
                comment="User whose API credentials are used for automatic scheduled crawls",
            ),
        )
        op.create_index(
            "ix_categories_schedule_owner_id",
            "categories",
            ["schedule_owner_id"],
        )


def downgrade() -> None:
    # Remove schedule_owner_id from categories
    if column_exists("categories", "schedule_owner_id"):
        op.drop_index("ix_categories_schedule_owner_id", table_name="categories")
        op.drop_column("categories", "schedule_owner_id")

    # Remove user_id from crawl_jobs
    if column_exists("crawl_jobs", "user_id"):
        op.drop_index("ix_crawl_jobs_user_id", table_name="crawl_jobs")
        op.drop_column("crawl_jobs", "user_id")

    # Drop user_api_credentials table
    if table_exists("user_api_credentials"):
        op.drop_table("user_api_credentials")

    # Drop api_credential_type enum
    if enum_exists("api_credential_type"):
        api_credential_type = postgresql.ENUM(
            "serpapi",
            "serper",
            "azure_openai",
            "anthropic",
            name="api_credential_type",
        )
        api_credential_type.drop(op.get_bind())
